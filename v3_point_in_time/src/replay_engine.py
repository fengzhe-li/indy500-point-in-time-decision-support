"""Phase 3 — historical shadow replay engine.

This module does not add any new scientific model. It orchestrates the
existing, frozen-behind-it Phase 1/2 pieces (point_in_time_guard,
forecast_vintage_store, shadow_engine, applicability_gate,
final_v2_adapter) into an auditable, time-ordered replay of what the
system could defensibly have said at each historical decision time, and
makes explicit abstention a first-class, machine-readable output rather
than a silently dropped row.

Central distinction (Phase 3 Step 6), enforced structurally here:

  INFERENCE SUPPORT
      Can FINAL_V2 produce a conditional outlook at a calibrated anchor
      horizon (15/30/60/90/120 min), given the current physical state
      and an available point-in-time forecast? This does NOT depend on
      when (or whether) a real future attempt actually occurred.

  HISTORICAL EVALUATION SUPPORT
      Can a realised historical future attempt be defensibly paired
      with one of those anchor outlooks and scored? This DOES depend on
      the realised horizon actually landing on (or, for the one
      pre-approved illustrative case, very near) a calibrated anchor.

These are computed independently and never conflated: a case can have
full inference support at all five anchors while having zero historical
evaluation support (this is, in fact, the status of 9 of the 10 real
2021 candidates).

STRATEGY IDENTIFIABILITY (whether the next opportunity's *timing* can be
predicted, or a retain/withdraw recommendation issued) is not modelled
anywhere in this project and is reported as such, never inferred.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

SRC_DIR = Path(__file__).resolve().parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import applicability_gate
import final_v2_adapter
import shadow_engine
from schemas import (
    ABSTENTION_REASON_CODES,
    REPLAY_CASE_CATEGORIES,
    REPLAY_EVENT_TYPES,
    ReplayEvent,
)
from hashing import sha256_obj
from forecast_vintage_store import ForecastVintageStore

CALIBRATED_ANCHOR_HORIZONS_MIN = applicability_gate.CALIBRATED_ANCHOR_HORIZONS_MIN

# Phase 3 "HUMAN DECISION — LOCK THIS NOW": the ONLY case approved to
# evaluate historical scoring at a non-exact anchor. This is a specific,
# pre-declared, human-approved exception recorded once here -- it is
# NOT a general nearest-anchor substitution rule, and no other case may
# use it (see phase2_qa_report.md design decision 2 and
# phase2_interpretation_addendum.md).
ILLUSTRATIVE_APPROVED_CASES = {
    ("2021", "60"): {
        "anchor_horizon_min": 60,
        "approval_label": "ILLUSTRATIVE_POINT_IN_TIME_SHADOW_CASE",
        "note": (
            "Approved ONLY as an illustrative diagnostic (realised horizon "
            "~64.1 min vs. the 60-min calibrated anchor, ~4.1-min mismatch). "
            "NOT approved as POINT_IN_TIME_EXTERNAL_VALIDATION and must not "
            "contribute to aggregate validation metrics."
        ),
    }
}


def _parse(ts: str) -> datetime:
    dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


# ---------------------------------------------------------------------------
# Step 4 — information state
# ---------------------------------------------------------------------------

def build_information_state(
    decision_time: str,
    candidate_items: Sequence[dict],
) -> Tuple[Dict[str, object], List[str]]:
    """Answer: "what could the retrospective shadow system defensibly
    know at time t?"

    `candidate_items`: list of {"name": str, "known_at": Optional[str],
    "value": Any}. An item enters the returned state only if it has a
    known_at timestamp that is at or before decision_time. Anything
    with known_at is None, unparsable, or strictly after decision_time
    is excluded -- it can never silently enter the state. This is the
    single choke point Phase 3's leakage tests (items 2-3) exercise
    directly, independent of the point-in-time guard used later for the
    inference call itself (defense in depth, not a replacement for it).
    """
    t_decision = _parse(decision_time)
    state: Dict[str, object] = {}
    excluded: List[str] = []
    for item in candidate_items:
        known_at = item.get("known_at")
        if known_at is None:
            excluded.append(item["name"])
            continue
        if _parse(known_at) <= t_decision:
            state[item["name"]] = item["value"]
        else:
            excluded.append(item["name"])
    return state, excluded


# ---------------------------------------------------------------------------
# Historical evaluation support (Step 6 concept #2)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class HistoricalScoringSupport:
    status: str  # "SUPPORTED" | "ILLUSTRATIVE_ONLY" | "ABSTAINED"
    anchor_horizon_min: Optional[int]
    reason_codes: tuple
    note: str


def historical_scoring_support(
    event_year: int, car_or_entry_id: str, realised_horizon_minutes: float,
) -> HistoricalScoringSupport:
    """Whether the realised future attempt can be defensibly paired with
    a calibrated-anchor outlook and scored. Exact match against one of
    the five calibrated anchors is the only *general* rule (no invented
    tolerance threshold); the single pre-approved illustrative exception
    is looked up by (year, car), never re-derived from a distance
    calculation applied to other cases.
    """
    key = (str(event_year), str(car_or_entry_id))
    if key in ILLUSTRATIVE_APPROVED_CASES:
        approved = ILLUSTRATIVE_APPROVED_CASES[key]
        return HistoricalScoringSupport(
            status="ILLUSTRATIVE_ONLY",
            anchor_horizon_min=approved["anchor_horizon_min"],
            reason_codes=("NON_ANCHOR_EVALUATION_NOT_APPROVED",),
            note=approved["note"],
        )

    for anchor in CALIBRATED_ANCHOR_HORIZONS_MIN:
        if realised_horizon_minutes == anchor:
            return HistoricalScoringSupport(
                status="SUPPORTED",
                anchor_horizon_min=anchor,
                reason_codes=(),
                note="Realised horizon exactly matches a calibrated anchor.",
            )

    return HistoricalScoringSupport(
        status="ABSTAINED",
        anchor_horizon_min=None,
        reason_codes=("HORIZON_OUT_OF_SUPPORT",),
        note=(
            f"Realised horizon {realised_horizon_minutes:.1f} min does not exactly "
            f"match any calibrated anchor {CALIBRATED_ANCHOR_HORIZONS_MIN} and is not "
            "the pre-approved illustrative exception; historical scoring abstained "
            "rather than extrapolated or nearest-anchor-substituted."
        ),
    )


# ---------------------------------------------------------------------------
# Event construction helper
# ---------------------------------------------------------------------------

_event_counter = {"n": 0}


def _make_event(
    event_year: int,
    event_time: str,
    event_type: str,
    car_or_entry_id: str,
    information_cutoff: str,
    payload: dict,
    decision_snapshot_id: Optional[str] = None,
    prediction_id: Optional[str] = None,
    provenance_ids: tuple = (),
    input_hash: str = "",
    evaluation_status: str = "OK",
    abstention_reason_codes: tuple = (),
) -> ReplayEvent:
    assert event_type in REPLAY_EVENT_TYPES, event_type
    for code in abstention_reason_codes:
        assert code in ABSTENTION_REASON_CODES, code

    _event_counter["n"] += 1
    event_id = f"{car_or_entry_id}:{event_year}:{event_type}:{_event_counter['n']:06d}"

    hashable = {
        "event_id": event_id,
        "event_year": event_year,
        "event_time": event_time,
        "event_type": event_type,
        "car_or_entry_id": car_or_entry_id,
        "decision_snapshot_id": decision_snapshot_id,
        "prediction_id": prediction_id,
        "information_cutoff": information_cutoff,
        "payload": payload,
        "provenance_ids": list(provenance_ids),
        "input_hash": input_hash,
        "evaluation_status": evaluation_status,
        "abstention_reason_codes": list(abstention_reason_codes),
    }
    event_hash = sha256_obj(hashable)

    return ReplayEvent(
        event_id=event_id,
        event_year=event_year,
        event_time=event_time,
        event_type=event_type,
        car_or_entry_id=car_or_entry_id,
        decision_snapshot_id=decision_snapshot_id,
        prediction_id=prediction_id,
        information_cutoff=information_cutoff,
        payload=payload,
        provenance_ids=tuple(provenance_ids),
        input_hash=input_hash,
        event_hash=event_hash,
        evaluation_status=evaluation_status,
        abstention_reason_codes=tuple(abstention_reason_codes),
    )


# ---------------------------------------------------------------------------
# Explanation / decomposition data (Step 16) — display-only, reuses the
# exact frozen closed-form terms already computed inside
# final_v2_adapter.infer(); does not modify that function or invent any
# new decomposition.
# ---------------------------------------------------------------------------

def explanation_terms(
    current_track_temp_c: float,
    current_ambient_temp_c: float,
    forecast_future_ambient_temp_c: float,
    decision_time: str,
    target_time: str,
    horizon_min: int,
    latitude_deg: float,
    longitude_deg: float,
) -> dict:
    artifacts = final_v2_adapter.load_frozen_artifacts()
    coef = artifacts.track_coefficients[horizon_min]
    thermal_gap_0_c = current_track_temp_c - current_ambient_temp_c
    delta_ambient_temp_c = forecast_future_ambient_temp_c - current_ambient_temp_c
    t0, t1 = _parse(decision_time), _parse(target_time)
    solar_elevation_mean_deg = (
        final_v2_adapter.solar_elevation_deg(t0, latitude_deg, longitude_deg)
        + final_v2_adapter.solar_elevation_deg(t1, latitude_deg, longitude_deg)
    ) / 2.0
    point_delta_track_c = (
        coef["intercept_c"]
        + coef["beta_delta_ambient_temp_c"] * delta_ambient_temp_c
        + coef["beta_thermal_gap_0_c"] * thermal_gap_0_c
        + coef["beta_solar_elevation_mean_deg"] * solar_elevation_mean_deg
    )
    return {
        "current_track_to_ambient_thermal_gap_c": thermal_gap_0_c,
        "forecast_ambient_trajectory_c": {
            "current_ambient_temp_c": current_ambient_temp_c,
            "forecast_future_ambient_temp_c": forecast_future_ambient_temp_c,
            "delta_ambient_temp_c": delta_ambient_temp_c,
        },
        "predicted_future_track_temperature_change_c": point_delta_track_c,
        "solar_elevation_mean_deg": solar_elevation_mean_deg,
        "note": (
            "These are the exact closed-form M2b_mean_solar terms FINAL_V2's "
            "adapter already evaluates for this horizon (see final_v2_adapter.py); "
            "shown here for display only, not a separate model or decomposition."
        ),
        "uncertainty_source_reference": _uncertainty_source_reference(horizon_min),
    }


_V2D_WIDTH_REDUCTION_CACHE: Optional[Dict[int, dict]] = None


def _uncertainty_source_reference(horizon_min: int) -> dict:
    """Static, frozen V2-D ablation reference for this horizon (Phase 3
    Step 16: "reuse existing V2-D evidence... do not recompute or
    reinterpret V2-D as formal causal variance decomposition"). Read-only;
    this is a fixed frozen reference table, not case-specific."""
    global _V2D_WIDTH_REDUCTION_CACHE
    if _V2D_WIDTH_REDUCTION_CACHE is None:
        import csv

        repo_root = Path(__file__).resolve().parents[2]
        path = repo_root / "weather/output/v2d_uncertainty_ablation/v2d_uncertainty_ablation_width_reduction_v1.csv"
        cache: Dict[int, dict] = {}
        if path.is_file():
            with path.open(newline="", encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    if row["variant"] != "NO_RESIDUAL":
                        continue
                    cache[int(row["horizon_min"])] = {
                        "source": str(path.relative_to(repo_root)),
                        "variant": "NO_RESIDUAL",
                        "pi80_width_reduction_vs_full_removing_empirical_residual": float(
                            row["pi80_width_reduction_vs_full"]
                        ),
                        "interpretation": (
                            "Frozen V2-D sensitivity ablation: fraction of this horizon's "
                            "80% predictive-interval width attributable to removing empirical "
                            "attempt-level performance residual uncertainty. This is a global, "
                            "frozen reference for the horizon, not a decomposition specific to "
                            "this one prediction."
                        ),
                    }
        _V2D_WIDTH_REDUCTION_CACHE = cache
    return _V2D_WIDTH_REDUCTION_CACHE.get(
        horizon_min,
        {"note": "No frozen V2-D reference available for this horizon; REGIME_APPLICABILITY_UNRESOLVED."},
    )


# ---------------------------------------------------------------------------
# Step 17 — provenance view data
# ---------------------------------------------------------------------------

def provenance_view(
    snapshot,
    vintage,
    prediction,
    historical_support: HistoricalScoringSupport,
) -> dict:
    return {
        "decision_snapshot_id": snapshot.snapshot_id,
        "information_cutoff": snapshot.information_cutoff,
        "forecast_source": vintage.source,
        "forecast_model": vintage.model_name,
        "forecast_run": vintage.model_run,
        "forecast_issue_time": vintage.issue_time,
        "final_v2_model_hash": prediction.model_hash,
        "input_hash": prediction.input_hash,
        "prediction_hash": prediction.prediction_hash,
        "scientific_support": prediction.applicability_status,
        "historical_scoring_support": historical_support.status,
    }


# ---------------------------------------------------------------------------
# Step 3/7/8/9/10 — per-case replay
# ---------------------------------------------------------------------------

@dataclass
class CaseReplayResult:
    case_id: str
    events: List[ReplayEvent]
    category: str
    inference_supported_horizons: List[int]
    inference_abstained_horizons: List[int]
    historical_support: HistoricalScoringSupport


def replay_case(
    case: dict,
    store: ForecastVintageStore,
    output_dir: Path,
    latitude_deg: float,
    longitude_deg: float,
    random_seed: int,
    n_mc: int,
) -> CaseReplayResult:
    """Replay one real, non-fabricated candidate case (must already have
    passed Phase 2's timestamp-defensibility screen -- this function
    does not itself decide whether a decision_time is usable).

    Required `case` fields: case_id, event_year, car_or_entry_id,
    decision_time (ISO), current_track_temp_c, current_ambient_temp_c,
    current_track_temp_known_at, current_ambient_temp_known_at,
    realised_attempt_time (ISO), realised_horizon_minutes, observed_delta_v.
    """
    events: List[ReplayEvent] = []
    decision_time = case["decision_time"]
    event_year = case["event_year"]
    car = case["car_or_entry_id"]

    # Step 4 — information state at decision_time, built from an
    # explicit known-at manifest (defense in depth ahead of the guard).
    state, excluded_from_state = build_information_state(
        decision_time,
        [
            {"name": "current_track_temp_c", "known_at": case["current_track_temp_known_at"], "value": case["current_track_temp_c"]},
            {"name": "current_ambient_temp_c", "known_at": case["current_ambient_temp_known_at"], "value": case["current_ambient_temp_c"]},
        ],
    )
    if excluded_from_state:
        events.append(_make_event(
            event_year=event_year, event_time=decision_time, event_type="SHADOW_INFERENCE_ABSTAINED",
            car_or_entry_id=car, information_cutoff=decision_time,
            payload={"excluded_items": excluded_from_state, "scope": "CURRENT_STATE"},
            evaluation_status="ABSTAINED", abstention_reason_codes=("INSUFFICIENT_CURRENT_STATE",),
        ))
        return CaseReplayResult(case["case_id"], events, "ABSTAINED_INSUFFICIENT_TIMESTAMP", [], list(CALIBRATED_ANCHOR_HORIZONS_MIN),
                                 HistoricalScoringSupport("ABSTAINED", None, ("INSUFFICIENT_CURRENT_STATE",), "current state insufficient"))

    events.append(_make_event(
        event_year=event_year, event_time=decision_time, event_type="PHYSICAL_STATE_OBSERVED",
        car_or_entry_id=car, information_cutoff=decision_time,
        payload={"current_track_temp_c": state["current_track_temp_c"], "current_ambient_temp_c": state["current_ambient_temp_c"]},
        evaluation_status="OK",
    ))

    snapshot, guard, selections = shadow_engine.select_and_build_snapshot(
        store=store, snapshot_id=f"phase3:{case['case_id']}", event_year=event_year, car_or_entry_id=car,
        decision_time=decision_time, current_track_temp_c=case["current_track_temp_c"],
        current_ambient_temp_c=case["current_ambient_temp_c"],
        current_track_temp_known_at=case["current_track_temp_known_at"],
        current_ambient_temp_known_at=case["current_ambient_temp_known_at"],
        horizons_min=list(CALIBRATED_ANCHOR_HORIZONS_MIN),
    )
    if not guard.passed:
        events.append(_make_event(
            event_year=event_year, event_time=decision_time, event_type="SHADOW_INFERENCE_ABSTAINED",
            car_or_entry_id=car, information_cutoff=decision_time,
            payload={"scope": "SNAPSHOT_GUARD", "guard_reasons": list(guard.reasons)},
            evaluation_status="ABSTAINED", abstention_reason_codes=("POINT_IN_TIME_VIOLATION",),
        ))
        return CaseReplayResult(case["case_id"], events, "ABSTAINED_INSUFFICIENT_TIMESTAMP", [], list(CALIBRATED_ANCHOR_HORIZONS_MIN),
                                 HistoricalScoringSupport("ABSTAINED", None, ("POINT_IN_TIME_VIOLATION",), "guard failed"))

    inference_supported: List[int] = []
    inference_abstained: List[int] = []
    outlook_by_horizon = {}

    for h in CALIBRATED_ANCHOR_HORIZONS_MIN:
        sel = selections.get(h)
        if sel is None:
            inference_abstained.append(h)
            events.append(_make_event(
                event_year=event_year, event_time=decision_time, event_type="SHADOW_INFERENCE_ABSTAINED",
                car_or_entry_id=car, information_cutoff=decision_time, decision_snapshot_id=snapshot.snapshot_id,
                payload={"horizon_minutes": h, "scope": "INFERENCE"},
                evaluation_status="ABSTAINED", abstention_reason_codes=("NO_VALID_FORECAST_VINTAGE",),
            ))
            continue

        vintage = sel["vintage"]
        events.append(_make_event(
            event_year=event_year, event_time=decision_time, event_type="FORECAST_AVAILABLE",
            car_or_entry_id=car, information_cutoff=decision_time, decision_snapshot_id=snapshot.snapshot_id,
            payload={"horizon_minutes": h, "forecast_issue_time": vintage.issue_time,
                     "forecast_valid_time": vintage.valid_time, "valid_time_error_minutes": sel["valid_time_error_minutes"],
                     "forecast_ambient_temp_c": vintage.ambient_temp_c},
            provenance_ids=(vintage.forecast_id,), evaluation_status="OK",
        ))

        result = shadow_engine.run_single_horizon(
            snapshot, h, vintage, latitude_deg, longitude_deg, random_seed, n_mc, output_dir,
            valid_time_error_minutes=sel["valid_time_error_minutes"],
        )
        if result.status != "OK":
            inference_abstained.append(h)
            reason = "HORIZON_OUT_OF_SUPPORT" if result.status == "OUT_OF_SUPPORT" else "MISSING_REQUIRED_FORECAST_INPUT"
            events.append(_make_event(
                event_year=event_year, event_time=decision_time, event_type="SHADOW_INFERENCE_ABSTAINED",
                car_or_entry_id=car, information_cutoff=decision_time, decision_snapshot_id=snapshot.snapshot_id,
                payload={"horizon_minutes": h, "scope": "INFERENCE", "gate_status": result.status, "gate_reasons": list(result.reasons)},
                evaluation_status="ABSTAINED", abstention_reason_codes=(reason,),
            ))
            continue

        inference_supported.append(h)
        pred = result.prediction
        target_time = shadow_engine.target_time_for(decision_time, h)
        explanation = explanation_terms(
            current_track_temp_c=case["current_track_temp_c"], current_ambient_temp_c=case["current_ambient_temp_c"],
            forecast_future_ambient_temp_c=vintage.ambient_temp_c, decision_time=decision_time,
            target_time=target_time, horizon_min=h, latitude_deg=latitude_deg, longitude_deg=longitude_deg,
        )
        outlook_by_horizon[h] = pred
        events.append(_make_event(
            event_year=event_year, event_time=decision_time, event_type="SHADOW_INFERENCE_ISSUED",
            car_or_entry_id=car, information_cutoff=decision_time, decision_snapshot_id=snapshot.snapshot_id,
            prediction_id=pred.prediction_id,
            payload={
                "horizon_minutes": h, "expected_delta_v": pred.expected_delta_v, "median_delta_v": pred.median_delta_v,
                "p_improve": pred.p_improve, "pi80_low": pred.pi80_low, "pi80_high": pred.pi80_high,
                "pi90_low": pred.pi90_low, "pi90_high": pred.pi90_high,
                "conditional_physical_opportunity_value": pred.expected_delta_v,
                "applicability_status": pred.applicability_status,
                "explanation": explanation,
                "queue_time_prediction": "NOT MODELLED",
                "retain_withdraw_recommendation": "NOT ISSUED",
            },
            provenance_ids=(vintage.forecast_id, pred.model_hash), input_hash=pred.input_hash,
            evaluation_status=pred.applicability_status,
        ))

    # Step 10 — case-level category, computed and emitted here (still at
    # decision_time) BEFORE anything timestamped at the later
    # realised_attempt_time is appended, so the event list stays in
    # strict, non-decreasing event_time order (Phase 3 test 1).
    hist = historical_scoring_support(event_year, car, case["realised_horizon_minutes"])
    if hist.status == "ILLUSTRATIVE_ONLY":
        category = "ILLUSTRATIVE_ONLY"
    elif hist.status == "SUPPORTED" and inference_supported:
        category = "FULL_SHADOW_INFERENCE_SUPPORTED"
    elif inference_supported:
        category = "CONDITIONAL_OUTLOOK_SUPPORTED_BUT_HISTORICAL_SCORING_UNSUPPORTED"
    else:
        category = "ABSTAINED_FORECAST_UNAVAILABLE"

    events.append(_make_event(
        event_year=event_year, event_time=decision_time, event_type="APPLICABILITY_CHANGED",
        car_or_entry_id=car, information_cutoff=decision_time, decision_snapshot_id=snapshot.snapshot_id,
        payload={
            "category": category,
            "inference_support": {"supported_horizons_min": inference_supported, "abstained_horizons_min": inference_abstained},
            "historical_evaluation_support": {"status": hist.status, "anchor_horizon_min": hist.anchor_horizon_min},
            "strategy_identifiability": {"status": "NOT_MODELLED", "note": "This project does not model opportunity timing and never issues a strategy recommendation."},
        },
        evaluation_status=category,
    ))

    # Step 9 / Step 8 — the realised future attempt, and (if
    # historically scorable) pairing it against an issued anchor outlook.
    events.append(_make_event(
        event_year=event_year, event_time=case["realised_attempt_time"], event_type="FUTURE_ATTEMPT_OBSERVED",
        car_or_entry_id=car, information_cutoff=case["realised_attempt_time"],
        payload={"observed_delta_v": case["observed_delta_v"], "realised_horizon_minutes": case["realised_horizon_minutes"]},
        evaluation_status="OK",
    ))

    if hist.status in ("SUPPORTED", "ILLUSTRATIVE_ONLY") and hist.anchor_horizon_min in outlook_by_horizon:
        pred = outlook_by_horizon[hist.anchor_horizon_min]
        vintage = selections[hist.anchor_horizon_min]["vintage"]
        prov = provenance_view(snapshot, vintage, pred, hist)
        abs_err = abs(pred.expected_delta_v - case["observed_delta_v"])
        events.append(_make_event(
            event_year=event_year, event_time=case["realised_attempt_time"], event_type="PREDICTION_SCORED",
            car_or_entry_id=car, information_cutoff=case["realised_attempt_time"],
            decision_snapshot_id=snapshot.snapshot_id, prediction_id=pred.prediction_id,
            payload={
                "anchor_horizon_minutes": hist.anchor_horizon_min, "realised_horizon_minutes": case["realised_horizon_minutes"],
                "observed_delta_v": case["observed_delta_v"], "expected_delta_v": pred.expected_delta_v,
                "absolute_error": abs_err, "provenance": prov, "note": hist.note,
                "counts_toward_aggregate_validation": hist.status == "SUPPORTED",
            },
            provenance_ids=(vintage.forecast_id, pred.model_hash), input_hash=pred.input_hash,
            evaluation_status=hist.status, abstention_reason_codes=hist.reason_codes,
        ))
    else:
        events.append(_make_event(
            event_year=event_year, event_time=case["realised_attempt_time"], event_type="SHADOW_INFERENCE_ABSTAINED",
            car_or_entry_id=car, information_cutoff=case["realised_attempt_time"],
            decision_snapshot_id=snapshot.snapshot_id,
            payload={
                "scope": "HISTORICAL_SCORING", "realised_horizon_minutes": case["realised_horizon_minutes"],
                "note": hist.note,
            },
            evaluation_status="ABSTAINED", abstention_reason_codes=hist.reason_codes or ("HORIZON_OUT_OF_SUPPORT",),
        ))

    return CaseReplayResult(
        case_id=case["case_id"], events=events, category=category,
        inference_supported_horizons=inference_supported, inference_abstained_horizons=inference_abstained,
        historical_support=hist,
    )
