"""Phase 3 Steps 11-14 — batch historical shadow replay over the full
real, non-fabricated Phase 2 evidence set (10 defensible candidates +
31 excluded pre-candidates). No new data is acquired; no timestamp or
forecast is invented. Candidate reconstruction reuses the exact same
pipeline.reconcile.build() + loyo + raw-track-observation logic already
used and reported in run_phase2_evaluation.py / phase2_minimum_data_plan.md
(not re-derived independently, to avoid two silently-diverging
definitions of "candidate case").
"""
from __future__ import annotations

import csv
import json
import shutil
import sys
from pathlib import Path

import pandas as pd

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC_DIR))
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

# Reuse Phase 2's own candidate-finding logic verbatim (single source of truth).
sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_phase2_evaluation import find_candidates  # noqa: E402

import replay_engine  # noqa: E402
from forecast_vintage_store import ForecastVintageStore  # noqa: E402
from schemas import REPLAY_CASE_CATEGORIES  # noqa: E402

LATITUDE_DEG = 39.7950
LONGITUDE_DEG = -86.2348
RANDOM_SEED = 20260914
N_MC = 20000

HRRR_FILE = REPO_ROOT / "weather/output/hrrr_ims_2020_2024_features.csv"

V3_ROOT = Path(__file__).resolve().parents[1]
REPLAY_DIR = V3_ROOT / "output" / "replay"
SHADOW_DIR = REPLAY_DIR / "shadow_predictions"


def main() -> int:
    if SHADOW_DIR.exists():
        shutil.rmtree(SHADOW_DIR)
    REPLAY_DIR.mkdir(parents=True, exist_ok=True)

    candidates, excluded = find_candidates()
    store = ForecastVintageStore.load_hrrr_features(HRRR_FILE, LATITUDE_DEG, LONGITUDE_DEG)

    all_events = []
    case_summary_rows = []

    for c in candidates:
        case = dict(
            case_id=c["case_id"], event_year=c["event_year"], car_or_entry_id=c["car_or_entry_id"],
            decision_time=c["decision_time"].tz_convert("UTC").isoformat().replace("+00:00", "Z"),
            current_track_temp_c=c["current_track_temp_c"], current_ambient_temp_c=c["current_ambient_temp_c"],
            current_track_temp_known_at=c["decision_time"].tz_convert("UTC").isoformat().replace("+00:00", "Z"),
            current_ambient_temp_known_at=c["decision_time"].tz_convert("UTC").isoformat().replace("+00:00", "Z"),
            realised_attempt_time=c["realised_attempt_time"].tz_convert("UTC").isoformat().replace("+00:00", "Z"),
            realised_horizon_minutes=c["realised_horizon_minutes"], observed_delta_v=c["observed_delta_v"],
        )
        result = replay_engine.replay_case(case, store, SHADOW_DIR, LATITUDE_DEG, LONGITUDE_DEG, RANDOM_SEED, N_MC)
        all_events.extend(result.events)
        case_summary_rows.append(dict(
            case_id=result.case_id, event_year=case["event_year"], car_or_entry_id=case["car_or_entry_id"],
            category=result.category,
            inference_supported_horizons_min=";".join(map(str, result.inference_supported_horizons)),
            inference_abstained_horizons_min=";".join(map(str, result.inference_abstained_horizons)),
            historical_scoring_status=result.historical_support.status,
            historical_scoring_anchor_horizon_min=result.historical_support.anchor_horizon_min,
            realised_horizon_minutes=case["realised_horizon_minutes"],
            observed_delta_v=case["observed_delta_v"],
            abstention_reason_codes=";".join(result.historical_support.reason_codes),
        ))

    # The 31 pre-candidates excluded before a decision_time could even be
    # constructed: no defensible timestamp to place them in a time-ordered
    # replay, so they get a summary/abstention row but no ReplayEvent
    # (inventing a timestamp for them is explicitly forbidden).
    for e in excluded:
        case_summary_rows.append(dict(
            case_id=f"{e['year']}_car{e['car']}_excluded", event_year=e["year"], car_or_entry_id=e["car"],
            category="ABSTAINED_INSUFFICIENT_TIMESTAMP",
            inference_supported_horizons_min="", inference_abstained_horizons_min="",
            historical_scoring_status="ABSTAINED", historical_scoring_anchor_horizon_min=None,
            realised_horizon_minutes=None, observed_delta_v=None,
            abstention_reason_codes="INSUFFICIENT_ATTEMPT_TIMESTAMP",
        ))

    all_events.sort(key=lambda ev: (ev.event_time, ev.car_or_entry_id, ev.event_type))

    with open(REPLAY_DIR / "replay_events.jsonl", "w", encoding="utf-8") as f:
        for ev in all_events:
            f.write(json.dumps(ev.to_dict(), sort_keys=True, default=str) + "\n")

    event_field_names = list(all_events[0].to_dict().keys()) if all_events else []
    with open(REPLAY_DIR / "replay_events.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=event_field_names)
        w.writeheader()
        for ev in all_events:
            row = ev.to_dict()
            row["payload"] = json.dumps(row["payload"], sort_keys=True, default=str)
            row["provenance_ids"] = ";".join(row["provenance_ids"])
            row["abstention_reason_codes"] = ";".join(row["abstention_reason_codes"])
            w.writerow(row)

    case_df = pd.DataFrame(case_summary_rows)
    case_df.to_csv(REPLAY_DIR / "replay_case_summary.csv", index=False)

    abstention_rows = []
    for category in REPLAY_CASE_CATEGORIES:
        n = int((case_df["category"] == category).sum())
        abstention_rows.append(dict(category=category, count=n))
    reason_counts = {}
    for codes in case_df["abstention_reason_codes"]:
        for code in str(codes).split(";"):
            if code:
                reason_counts[code] = reason_counts.get(code, 0) + 1
    for code, n in sorted(reason_counts.items()):
        abstention_rows.append(dict(category=f"REASON:{code}", count=n))
    pd.DataFrame(abstention_rows).to_csv(REPLAY_DIR / "replay_abstention_summary.csv", index=False)

    print(f"Total transitions considered: {len(case_summary_rows)} (10 candidates + {len(excluded)} excluded pre-candidates)")
    print(case_df["category"].value_counts().to_string())
    print(f"Total replay events: {len(all_events)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
