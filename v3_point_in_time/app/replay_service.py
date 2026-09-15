"""Phase 4 application layer — read-only query service over Phase 3's
already-frozen, already-verified replay outputs.

CRITICAL DESIGN DECISION: this service never calls final_v2_adapter,
shadow_engine, or any Monte Carlo code. It reads exactly the same
output/replay/*.{jsonl,csv} files output/qa/phase3_qa_report.md already
cites as authoritative, produced by
`scripts/run_phase3_replay.py`. This means the API can literally never
diverge from what Phase 3 froze and tested -- there is no code path by
which the application layer could recompute, and therefore no code path
by which it could silently recompute *differently*. If the underlying
replay evidence changes, it changes because someone re-ran Phase 3's own
frozen pipeline, not because a web request triggered new inference.
"""
from __future__ import annotations

import csv
import json
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional

V3_ROOT = Path(__file__).resolve().parents[1]
REPLAY_DIR = V3_ROOT / "output" / "replay"
EVALUATION_DIR = V3_ROOT / "output" / "evaluation"

EVENTS_JSONL = REPLAY_DIR / "replay_events.jsonl"
CASE_SUMMARY_CSV = REPLAY_DIR / "replay_case_summary.csv"
ABSTENTION_SUMMARY_CSV = REPLAY_DIR / "replay_abstention_summary.csv"

INFERENCE_HORIZONS = (15, 30, 60, 90, 120)


class NotFoundError(Exception):
    """A requested case/prediction id does not exist in the frozen
    replay evidence. Routes translate this to HTTP 404 -- never a 500,
    and never a fabricated result."""


def _cache_key(path: Path) -> tuple:
    """Bust the lru_cache automatically if a Phase 3 script re-runs and
    rewrites these files (mtime changes), without needing a server
    restart during local development."""
    try:
        return (str(path), path.stat().st_mtime_ns)
    except FileNotFoundError:
        return (str(path), -1)


@lru_cache(maxsize=4)
def _load_events_cached(cache_key: tuple) -> List[dict]:
    events = []
    if not EVENTS_JSONL.exists():
        return events
    with EVENTS_JSONL.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                events.append(json.loads(line))
    return events


def load_events() -> List[dict]:
    return _load_events_cached(_cache_key(EVENTS_JSONL))


@lru_cache(maxsize=4)
def _load_case_summary_cached(cache_key: tuple) -> List[dict]:
    if not CASE_SUMMARY_CSV.exists():
        return []
    with CASE_SUMMARY_CSV.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_case_summary() -> List[dict]:
    return _load_case_summary_cached(_cache_key(CASE_SUMMARY_CSV))


@lru_cache(maxsize=4)
def _load_abstention_summary_cached(cache_key: tuple) -> List[dict]:
    if not ABSTENTION_SUMMARY_CSV.exists():
        return []
    with ABSTENTION_SUMMARY_CSV.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_abstention_summary() -> List[dict]:
    return _load_abstention_summary_cached(_cache_key(ABSTENTION_SUMMARY_CSV))


def _has_events(row: dict) -> bool:
    return row.get("category") != "ABSTAINED_INSUFFICIENT_TIMESTAMP"


def list_cases() -> List[dict]:
    """Real candidate cases only (i.e. cases with an actual replay
    timeline) -- the 31 excluded pre-candidates have no decision_time
    to build a timeline from and appear only in the abstention/validation
    views, never as a selectable replay case (see phase3_qa_report.md)."""
    rows = [r for r in load_case_summary() if _has_events(r)]
    out = []
    for r in rows:
        events = _events_for(r["event_year"], r["car_or_entry_id"])
        decision_events = [e for e in events if e["event_type"] == "PHYSICAL_STATE_OBSERVED"]
        out.append({
            "case_id": r["case_id"],
            "event_year": int(r["event_year"]),
            "car_or_entry_id": r["car_or_entry_id"],
            "category": r["category"],
            "historical_scoring_status": r["historical_scoring_status"],
            "historical_scoring_anchor_horizon_min": _int_or_none(r.get("historical_scoring_anchor_horizon_min")),
            "realised_horizon_minutes": _float_or_none(r.get("realised_horizon_minutes")),
            "observed_delta_v": _float_or_none(r.get("observed_delta_v")),
            "decision_time": decision_events[0]["event_time"] if decision_events else None,
            "event_count": len(events),
        })
    return sorted(out, key=lambda c: c["case_id"])


def _events_for(event_year, car_or_entry_id) -> List[dict]:
    ey, car = str(event_year), str(car_or_entry_id)
    return [
        e for e in load_events()
        if str(e["event_year"]) == ey and str(e["car_or_entry_id"]) == car
    ]


def _find_case_row(case_id: str) -> dict:
    for r in load_case_summary():
        if r["case_id"] == case_id:
            return r
    raise NotFoundError(f"No replay case with id {case_id!r}")


def get_case(case_id: str) -> dict:
    row = _find_case_row(case_id)
    if not _has_events(row):
        raise NotFoundError(
            f"Case {case_id!r} was excluded before a decision timestamp could be "
            "constructed (INSUFFICIENT_ATTEMPT_TIMESTAMP) and has no replay timeline; "
            "see /api/replay/abstentions."
        )
    cases = {c["case_id"]: c for c in list_cases()}
    return cases[case_id]


def get_case_events(case_id: str) -> List[dict]:
    row = _find_case_row(case_id)
    if not _has_events(row):
        raise NotFoundError(f"Case {case_id!r} has no replay events (insufficient timestamp).")
    events = _events_for(row["event_year"], row["car_or_entry_id"])
    return sorted(events, key=lambda e: (e["event_time"], e["event_type"]))


def get_case_outlook(case_id: str) -> dict:
    """Per-horizon conditional physical outlook for a case: either the
    already-issued FINAL_V2 output (read verbatim from the frozen
    SHADOW_INFERENCE_ISSUED event) or the abstention reason -- never a
    recomputed or interpolated value."""
    events = get_case_events(case_id)
    by_horizon: Dict[int, dict] = {}
    for e in events:
        if e["event_type"] == "SHADOW_INFERENCE_ISSUED":
            h = e["payload"]["horizon_minutes"]
            by_horizon[h] = {
                "horizon_minutes": h,
                "status": "SUPPORTED",
                "prediction_id": e["prediction_id"],
                "expected_delta_v": e["payload"]["expected_delta_v"],
                "median_delta_v": e["payload"]["median_delta_v"],
                "p_improve": e["payload"]["p_improve"],
                "pi80_low": e["payload"]["pi80_low"],
                "pi80_high": e["payload"]["pi80_high"],
                "pi90_low": e["payload"]["pi90_low"],
                "pi90_high": e["payload"]["pi90_high"],
                "applicability_status": e["payload"]["applicability_status"],
                "queue_time_prediction": e["payload"]["queue_time_prediction"],
                "retain_withdraw_recommendation": e["payload"]["retain_withdraw_recommendation"],
            }
        elif e["event_type"] == "SHADOW_INFERENCE_ABSTAINED" and e["payload"].get("scope") == "INFERENCE":
            h = e["payload"]["horizon_minutes"]
            by_horizon.setdefault(h, {
                "horizon_minutes": h,
                "status": "ABSTAINED",
                "abstention_reason_codes": list(e["abstention_reason_codes"]),
            })
    for h in INFERENCE_HORIZONS:
        by_horizon.setdefault(h, {"horizon_minutes": h, "status": "NOT_EVALUATED"})
    return {
        "case_id": case_id,
        "horizons": [by_horizon[h] for h in INFERENCE_HORIZONS],
        "note": "If another opportunity occurs at horizon h -- this is a conditional physical outlook, not a prediction of when a future opportunity will occur.",
    }


def get_case_scoring(case_id: str) -> dict:
    """Historical scoring result for a case, or the abstention detail if
    scoring was not approved/possible. Distinct from inference support
    (get_case_outlook) by design -- see phase3_qa_report.md Step 6."""
    events = get_case_events(case_id)
    scored = next((e for e in events if e["event_type"] == "PREDICTION_SCORED"), None)
    if scored is not None:
        return {
            "case_id": case_id,
            "status": scored["evaluation_status"],
            "counts_toward_aggregate_validation": scored["payload"]["counts_toward_aggregate_validation"],
            "anchor_horizon_minutes": scored["payload"]["anchor_horizon_minutes"],
            "realised_horizon_minutes": scored["payload"]["realised_horizon_minutes"],
            "observed_delta_v": scored["payload"]["observed_delta_v"],
            "expected_delta_v": scored["payload"]["expected_delta_v"],
            "absolute_error": scored["payload"]["absolute_error"],
            "note": scored["payload"]["note"],
            "prediction_id": scored["prediction_id"],
            "abstention_reason_codes": list(scored["abstention_reason_codes"]),
        }
    abstained = next(
        (e for e in events if e["event_type"] == "SHADOW_INFERENCE_ABSTAINED" and e["payload"].get("scope") == "HISTORICAL_SCORING"),
        None,
    )
    if abstained is not None:
        return {
            "case_id": case_id,
            "status": "ABSTAINED",
            "counts_toward_aggregate_validation": False,
            "realised_horizon_minutes": abstained["payload"].get("realised_horizon_minutes"),
            "note": abstained["payload"].get("note"),
            "abstention_reason_codes": list(abstained["abstention_reason_codes"]),
        }
    return {"case_id": case_id, "status": "UNKNOWN", "counts_toward_aggregate_validation": False}


REPRESENTATIVE_CASE_CATEGORY = "CONDITIONAL_OUTLOOK_SUPPORTED_BUT_HISTORICAL_SCORING_UNSUPPORTED"


def select_representative_case() -> dict:
    """Phase 5 Step 11 -- deterministic, defensible selection of the
    default landing case among the 9 CONDITIONAL_OUTLOOK_SUPPORTED_BUT_
    HISTORICAL_SCORING_UNSUPPORTED cases (never the illustrative-only
    car 60 case).

    Selection criteria, in order, NONE of which look at the model's
    predicted or observed outcome (no cherry-picking by favourable
    result):
      1. complete forecast provenance: a FORECAST_AVAILABLE event at
         all 5 calibrated anchors (all 9 candidates satisfy this).
      2. complete five-horizon outlook: a SHADOW_INFERENCE_ISSUED event
         at all 5 calibrated anchors (all 9 candidates satisfy this).
      3. tie-break: smallest total forecast target-time mismatch summed
         across the 5 horizons (`valid_time_error_minutes`) -- a data
         *alignment quality* metric, not an outcome-favorability one.
      4. final tie-break: lexicographically smallest case_id, for full
         determinism.

    As of the real Phase 3 evidence, this selects `2021_car4`
    (total mismatch 60.07 min, the smallest among the 9 candidates;
    next closest is `2021_car21` at 61.73 min).
    """
    candidates = [c for c in list_cases() if c["category"] == REPRESENTATIVE_CASE_CATEGORY]

    def _score(case: dict):
        events = get_case_events(case["case_id"])
        forecasts = [e for e in events if e["event_type"] == "FORECAST_AVAILABLE"]
        issued = [e for e in events if e["event_type"] == "SHADOW_INFERENCE_ISSUED"]
        complete = len(forecasts) == len(INFERENCE_HORIZONS) and len(issued) == len(INFERENCE_HORIZONS)
        mismatch_sum = sum(e["payload"]["valid_time_error_minutes"] for e in forecasts) if forecasts else float("inf")
        return (0 if complete else 1, mismatch_sum, case["case_id"])

    if not candidates:
        raise NotFoundError("No CONDITIONAL_OUTLOOK_SUPPORTED_BUT_HISTORICAL_SCORING_UNSUPPORTED case available.")
    best = min(candidates, key=_score)
    return {
        **best,
        "selection_reason": (
            "Deterministic selection among 9 CONDITIONAL_OUTLOOK_SUPPORTED_BUT_HISTORICAL_SCORING_UNSUPPORTED "
            "cases: complete 5-horizon forecast provenance and issued outlook, smallest total forecast "
            "target-time mismatch across horizons. Not selected by predicted or observed outcome."
        ),
    }


def find_prediction_event(prediction_id: str) -> dict:
    for e in load_events():
        if e.get("prediction_id") == prediction_id and e["event_type"] == "SHADOW_INFERENCE_ISSUED":
            return e
    raise NotFoundError(f"No issued prediction with id {prediction_id!r}")


def find_forecast_event_for(event_year, car_or_entry_id, horizon_minutes: int) -> Optional[dict]:
    for e in _events_for(event_year, car_or_entry_id):
        if e["event_type"] == "FORECAST_AVAILABLE" and e["payload"]["horizon_minutes"] == horizon_minutes:
            return e
    return None


def _int_or_none(v):
    if v is None or v == "" or v == "None":
        return None
    return int(float(v))


def _float_or_none(v):
    if v is None or v == "" or v == "None":
        return None
    return float(v)
