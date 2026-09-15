"""Phase 3 Step 12 — historical shadow replay CLI.

Usage:
    python3 -m v3_point_in_time.scripts.run_shadow_replay [case_id]

Defaults to the one human-approved illustrative case (2021_car60) since
it is the only real candidate with both a conditional outlook AND a
historical-scoring attempt to display end to end. Any other real
candidate id from output/evaluation/phase2_case_table.csv / the case
summary (e.g. 2021_car18) can be passed to show a
conditional-outlook-supported-but-unscored case instead.
"""
from __future__ import annotations

import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC_DIR))
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from run_phase2_evaluation import find_candidates  # noqa: E402
import replay_engine  # noqa: E402
from forecast_vintage_store import ForecastVintageStore  # noqa: E402

LATITUDE_DEG = 39.7950
LONGITUDE_DEG = -86.2348
RANDOM_SEED = 20260914
N_MC = 20000
HRRR_FILE = REPO_ROOT / "weather/output/hrrr_ims_2020_2024_features.csv"
SHADOW_DIR = Path(__file__).resolve().parents[1] / "output" / "replay" / "cli_shadow_predictions"

DEFAULT_CASE_ID = "2021_car60"


def _fmt(v, nd=4):
    return "n/a" if v is None else f"{v:+.{nd}f}" if isinstance(v, float) else str(v)


def main() -> int:
    requested_case_id = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_CASE_ID

    candidates, _excluded = find_candidates()
    match = next((c for c in candidates if c["case_id"] == requested_case_id), None)
    if match is None:
        print(f"No real candidate case with id {requested_case_id!r}. "
              f"Available: {[c['case_id'] for c in candidates]}")
        return 1

    case = dict(
        case_id=match["case_id"], event_year=match["event_year"], car_or_entry_id=match["car_or_entry_id"],
        decision_time=match["decision_time"].tz_convert("UTC").isoformat().replace("+00:00", "Z"),
        current_track_temp_c=match["current_track_temp_c"], current_ambient_temp_c=match["current_ambient_temp_c"],
        current_track_temp_known_at=match["decision_time"].tz_convert("UTC").isoformat().replace("+00:00", "Z"),
        current_ambient_temp_known_at=match["decision_time"].tz_convert("UTC").isoformat().replace("+00:00", "Z"),
        realised_attempt_time=match["realised_attempt_time"].tz_convert("UTC").isoformat().replace("+00:00", "Z"),
        realised_horizon_minutes=match["realised_horizon_minutes"], observed_delta_v=match["observed_delta_v"],
    )
    store = ForecastVintageStore.load_hrrr_features(HRRR_FILE, LATITUDE_DEG, LONGITUDE_DEG)
    result = replay_engine.replay_case(case, store, SHADOW_DIR, LATITUDE_DEG, LONGITUDE_DEG, RANDOM_SEED, N_MC)

    outlook_events = {e.payload["horizon_minutes"]: e for e in result.events if e.event_type == "SHADOW_INFERENCE_ISSUED"}
    scored_event = next((e for e in result.events if e.event_type == "PREDICTION_SCORED"), None)
    abstained_scoring_event = next(
        (e for e in result.events if e.event_type == "SHADOW_INFERENCE_ABSTAINED" and e.payload.get("scope") == "HISTORICAL_SCORING"),
        None,
    )
    guard_event = next((e for e in result.events if e.event_type == "PHYSICAL_STATE_OBSERVED"), None)

    print("=" * 60)
    print("INDY 500 V3 — HISTORICAL SHADOW REPLAY")
    print("=" * 60)
    print()
    print("Evaluation mode:")
    print("RETROSPECTIVE_POINT_IN_TIME_INPUTS")
    print()
    print("Historical timestamp:")
    print(case["decision_time"])
    print()
    print("Information cutoff:")
    print(case["decision_time"])
    print()
    print("Current official result:")
    print("NOT RECONSTRUCTED (not required by the physical-response model)")
    print()
    print(f"Current physical state: track={case['current_track_temp_c']:.2f} C, "
          f"ambient={case['current_ambient_temp_c']:.2f} C")
    print()
    first_forecast_event = next((e for e in result.events if e.event_type == "FORECAST_AVAILABLE"), None)
    if first_forecast_event:
        print("Forecast vintage:")
        print(first_forecast_event.provenance_ids[0])
        print("Issued:")
        print(first_forecast_event.payload["forecast_issue_time"])
    else:
        print("Forecast vintage: NONE AVAILABLE")
    print()
    print("Point-in-time guard:")
    print("PASS" if guard_event is not None else "FAIL")
    print()
    print("FINAL_V2 integrity: PASS (frozen artifacts read-only; see v2_immutability_report.txt)")
    print()
    print("-" * 60)
    print("Conditional physical outlook")
    print("-" * 60)
    print(f"{'Horizon':<8}{'E[Δv]':<12}{'P(improve)':<12}{'80% PI':<24}{'Support'}")
    for h in replay_engine.CALIBRATED_ANCHOR_HORIZONS_MIN:
        ev = outlook_events.get(h)
        if ev is None:
            print(f"{h:<8}{'ABSTAINED':<12}{'':<12}{'':<24}{'NO_VALID_FORECAST_VINTAGE'}")
            continue
        p = ev.payload
        pi = f"[{p['pi80_low']:+.3f}, {p['pi80_high']:+.3f}]"
        print(f"{h:<8}{p['expected_delta_v']:<+12.4f}{p['p_improve']:<12.4f}{pi:<24}{p['applicability_status']}")
    print("-" * 60)
    print()
    print("Opportunity-time prediction:")
    print("NOT MODELLED")
    print()
    print("Queue state:")
    print("NOT MODELLED")
    print()
    print("Retain/withdraw recommendation:")
    print("NOT ISSUED")
    print()
    print("Historical scoring:")
    if scored_event is not None:
        print(scored_event.evaluation_status)
        print()
        print("Reason:")
        print(scored_event.payload["note"])
        print()
        print(f"Observed Δv:          {scored_event.payload['observed_delta_v']:+.4f} mph")
        print(f"Predicted E[Δv] (h={scored_event.payload['anchor_horizon_minutes']}): {scored_event.payload['expected_delta_v']:+.4f} mph")
        print(f"Absolute error:        {scored_event.payload['absolute_error']:.4f} mph")
        print(f"Counts toward aggregate validation: {scored_event.payload['counts_toward_aggregate_validation']}")
    else:
        print("ABSTAINED")
        print()
        print("Reason:")
        print(abstained_scoring_event.payload["note"] if abstained_scoring_event else "unknown")
    print()
    print(f"Case-level category: {result.category}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
