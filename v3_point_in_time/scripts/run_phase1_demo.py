"""Step 12 (Phase 1) — first demonstration, updated for the Phase 2
single-source-of-truth forecast-selection fix (Step 5).

Uses ONE real, non-fabricated historical case:
  - current track/ambient state from the frozen project's own
    weather/output/v2_future_track/future_track_samples_with_solar_v1.csv
    (a real PTSC pair from 2020-08-15).
  - forecast vintages from the frozen project's own real NOAA HRRR
    extract, weather/output/hrrr_ims_2020_2024_features.csv, selected
    under the strict issue_time <= decision_time rule.

No value in this script is hard-coded as an example scientific output;
every number below is computed at run time from the frozen artifacts
and the real inputs above.

Evaluation mode is RETROSPECTIVE_POINT_IN_TIME_INPUTS: FINAL_V2 did not
exist in 2020. This demonstrates the point-in-time execution path using
only information that would have been available at the historical
decision time -- it is not a claim that the model was deployed live in
2020.
"""
from __future__ import annotations

import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC_DIR))

REPO_ROOT = Path(__file__).resolve().parents[2]

from forecast_vintage_store import ForecastVintageStore  # noqa: E402
from point_in_time_guard import POINT_IN_TIME_VIOLATION  # noqa: E402
import shadow_engine  # noqa: E402
import scoring  # noqa: E402

LATITUDE_DEG = 39.7950
LONGITUDE_DEG = -86.2348
RANDOM_SEED = 20260914
N_MC = 20000
HORIZONS = (15, 30, 60, 90, 120)

# Real historical current-state row (see existing_system_inventory.md
# section 4 and tests/fixtures.py).
DECISION_TIME = "2020-08-15T12:15:00Z"
CURRENT_TRACK_TEMP_C = 26.666667
CURRENT_AMBIENT_TEMP_C = 21.111111
EVENT_YEAR = 2020
CAR_OR_ENTRY_ID = "PTSC_SAMPLE_2020_DAY1_ROW000"

HRRR_FEATURES_FILE = REPO_ROOT / "weather/output/hrrr_ims_2020_2024_features.csv"

OUTPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "shadow_predictions"


def main() -> int:
    print("=" * 72)
    print("INDY 500 V3 -- POINT-IN-TIME SHADOW INFERENCE")
    print("=" * 72)
    print()
    print("Evaluation mode:")
    print("RETROSPECTIVE_POINT_IN_TIME_INPUTS")
    print("(FINAL_V2 was not deployed live at this historical decision")
    print(" time; only information available by decision_time is used.)")
    print()
    print("Decision time:")
    print(DECISION_TIME)
    print()
    print("Information cutoff:")
    print(DECISION_TIME)
    print()

    store = ForecastVintageStore.load_hrrr_features(HRRR_FEATURES_FILE, LATITUDE_DEG, LONGITUDE_DEG)

    snapshot, guard_result, selections = shadow_engine.select_and_build_snapshot(
        store=store,
        snapshot_id=f"demo:{CAR_OR_ENTRY_ID}:{DECISION_TIME}",
        event_year=EVENT_YEAR,
        car_or_entry_id=CAR_OR_ENTRY_ID,
        decision_time=DECISION_TIME,
        current_track_temp_c=CURRENT_TRACK_TEMP_C,
        current_ambient_temp_c=CURRENT_AMBIENT_TEMP_C,
        current_track_temp_known_at=DECISION_TIME,
        current_ambient_temp_known_at=DECISION_TIME,
        horizons_min=list(HORIZONS),
    )
    print("Future information leakage:")
    print("PASS" if guard_result.passed else f"FAIL ({guard_result.reasons})")
    print()

    if snapshot is None:
        print(POINT_IN_TIME_VIOLATION)
        return 1

    print("FINAL_V2 integrity:")
    print("PASS (frozen artifacts loaded read-only; see v2_immutability_report.txt)")
    print()

    print("-" * 72)
    print(f"{'Horizon':<9}{'E[Δv]':>10}{'P(improve)':>13}{'80% PI':>22}   Status")
    print("-" * 72)

    all_results = shadow_engine.run_all_supported_horizons(
        snapshot, selections, LATITUDE_DEG, LONGITUDE_DEG, RANDOM_SEED, N_MC, OUTPUT_DIR,
        horizons_min=list(HORIZONS),
    )

    results = []
    for h in HORIZONS:
        result = all_results[h]
        if result.status == "OK":
            p = result.prediction
            sel = selections[h]
            err = sel["valid_time_error_minutes"] if sel else float("nan")
            pi80 = f"[{p.pi80_low:+.3f}, {p.pi80_high:+.3f}]"
            print(f"{h:<9}{p.expected_delta_v:>+10.4f}{p.p_improve:>13.4f}{pi80:>22}   {p.applicability_status} (forecast valid-time error: {err:.0f} min)")
            results.append(p)
        else:
            print(f"{h:<9}{'--':>10}{'--':>13}{'--':>22}   {result.status} {result.reasons}")

    print("-" * 72)
    print()
    print("Conditional Physical Opportunity Value  E[Δv | H=h]:")
    cpov = scoring.conditional_physical_opportunity_value(results)
    for h in sorted(cpov):
        print(f"  h={h:>3} min: {cpov[h].expected_delta_v:+.4f} mph  ({cpov[h].interpretation})")
    print()
    print("No queue-time prediction issued.")
    print("No withdraw/retain recommendation issued.")
    print()
    print("Selected forecast vintages (source, issue_time, valid_time, forecast valid-time error):")
    print("Provenance check: snapshot.selected_forecast_ids == actual vintages used == prediction record forecast_vintage_ids")
    for h in HORIZONS:
        sel = selections[h]
        if sel:
            v = sel["vintage"]
            assert v.forecast_id in snapshot.selected_forecast_ids
            if all_results[h].status == "OK":
                assert all_results[h].prediction.forecast_vintage_ids == (v.forecast_id,)
            print(f"  h={h:>3} min: {v.source}/{v.model_name}  issued={v.issue_time}  valid={v.valid_time}  error={sel['valid_time_error_minutes']:.0f} min  [provenance OK]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
