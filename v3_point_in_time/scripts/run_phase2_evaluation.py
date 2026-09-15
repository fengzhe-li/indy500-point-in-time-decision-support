"""Phase 2 Steps 7-13 — real point-in-time evaluation set.

Builds the 10-case table identified in phase2_minimum_data_plan.md from
real, non-fabricated evidence only:
  - decision/realised timestamps: pipeline.reconcile.build() (unmodified)
  - current physical state: weather/evidence/ptsc/... raw observations
  - observed outcome: r5_2/manual/probabilistic_physics_loyo_residuals_v1.csv
  - point-in-time forecast: weather/output/hrrr_ims_2020_2024_features.csv,
    selected through the Phase 1 ForecastVintageStore under the strict
    issue_time <= decision_time rule (Step 5 single-source-of-truth path)

Only ONE case (2021 car 60) has a realised horizon close enough to a
calibrated anchor (60 min, predeclared rule -- see
phase2_minimum_data_plan.md) to receive FINAL_V2 scientific inference.
The other 9 have realised horizons above the 120-minute production
boundary and are recorded as OUT_OF_SUPPORT, not extrapolated.

For the one in-support case, two comparison inferences are run at the
SAME target_time (t0 + 60 min):
  A. REALISED-ENVIRONMENT: ambient input = the real observed ambient
     reading nearest that target_time (what a perfect forecast would
     have said).
  B. POINT-IN-TIME FORECAST: ambient input = the real HRRR forecast
     vintage selected under issue_time <= decision_time.
This isolates the forecast-error contribution while holding horizon,
current state, and target_time fixed.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC_DIR))
REPO_ROOT = Path(__file__).resolve().parents[2]

sys.path.insert(0, str(REPO_ROOT))
from pipeline.reconcile import build as pipeline_build  # noqa: E402

import applicability_gate  # noqa: E402
import final_v2_adapter  # noqa: E402
import shadow_engine  # noqa: E402
from forecast_vintage_store import ForecastVintageStore  # noqa: E402

LATITUDE_DEG = 39.7950
LONGITUDE_DEG = -86.2348
RANDOM_SEED = 20260914
N_MC = 20000

QA_DIR = Path(__file__).resolve().parents[1] / "output" / "qa"
EVAL_DIR = Path(__file__).resolve().parents[1] / "output" / "evaluation"
SHADOW_DIR = Path(__file__).resolve().parents[1] / "data" / "shadow_predictions"
REPLAY_DIR = Path(__file__).resolve().parents[1] / "output" / "evaluation"

HRRR_FILE = REPO_ROOT / "weather/output/hrrr_ims_2020_2024_features.csv"
LOYO_FILE = REPO_ROOT / "r5_2/manual/probabilistic_physics_loyo_residuals_v1.csv"
RAW_TRACK_FILE = REPO_ROOT / "weather/evidence/ptsc/indy500_day1_track_temp_2020_2024_time_normalized.csv"

ANCHOR_HORIZON_FOR_CAR60 = 60  # predeclared rule; see phase2_minimum_data_plan.md


def _nearest_reading(raw: pd.DataFrame, year: int, at_or_before: pd.Timestamp | None, target: pd.Timestamp):
    day = raw[raw["year"] == year]
    if at_or_before is not None:
        day = day[day["utc_datetime"] <= at_or_before]
    idx = (target - day["utc_datetime"]).abs().idxmin()
    row = day.loc[idx]
    gap_min = abs((target - row["utc_datetime"]).total_seconds()) / 60.0
    return row, gap_min


def find_candidates():
    tables, _, _ = pipeline_build()
    attempts = tables["attempts"]
    by_key = {}
    for a in attempts:
        sid = a["session_id"]
        year = int(sid[-4:]) if sid[-4:].isdigit() else None
        by_key.setdefault((year, a["car_number"]), []).append(a)

    loyo = pd.read_csv(LOYO_FILE)
    raw = pd.read_csv(RAW_TRACK_FILE)
    raw["utc_datetime"] = pd.to_datetime(raw["utc_datetime"], utc=True)

    candidates = []
    excluded = []
    for _, r in loyo.iterrows():
        year, car = int(r["year"]), str(r["car_number"])
        atts = sorted(by_key.get((year, car), []), key=lambda a: (a["car_attempt_index"] is None, a["car_attempt_index"]))
        n = len(atts)
        if n != 2:
            excluded.append(dict(year=year, car=car, reason=f"AMBIGUOUS_MULTI_ATTEMPT_n={n}"))
            continue
        if not (atts[0]["start_time_utc"] and atts[1]["start_time_utc"]):
            excluded.append(dict(year=year, car=car, reason="NO_USABLE_TIMESTAMP"))
            continue
        t0 = pd.Timestamp(atts[0]["start_time_utc"])
        t1 = pd.Timestamp(atts[1]["start_time_utc"])
        horizon_min = (t1 - t0).total_seconds() / 60.0
        cur_row, cur_gap = _nearest_reading(raw, year, t0, t0)
        candidates.append(dict(
            case_id=f"{year}_car{car}",
            event_year=year, car_or_entry_id=car,
            decision_time=t0, realised_attempt_time=t1, realised_horizon_minutes=horizon_min,
            current_track_temp_c=float(cur_row["track_c"]), current_ambient_temp_c=float(cur_row["ambient_c"]),
            current_reading_gap_minutes=cur_gap,
            observed_delta_v=float(r["delta_four_lap_average_speed_mph"]),
            quality=atts[0]["event_time_quality"],
        ))
    return candidates, excluded


def main() -> int:
    candidates, excluded = find_candidates()
    store = ForecastVintageStore.load_hrrr_features(HRRR_FILE, LATITUDE_DEG, LONGITUDE_DEG)
    raw = pd.read_csv(RAW_TRACK_FILE)
    raw["utc_datetime"] = pd.to_datetime(raw["utc_datetime"], utc=True)

    case_rows = []
    replay_events = []

    for c in candidates:
        decision_time_iso = c["decision_time"].tz_convert("UTC").isoformat().replace("+00:00", "Z")
        is_car60 = c["car_or_entry_id"] == "60" and c["event_year"] == 2021
        eval_horizon = ANCHOR_HORIZON_FOR_CAR60 if is_car60 else int(round(c["realised_horizon_minutes"]))

        gate_probe = applicability_gate.evaluate(
            horizon_min=eval_horizon,
            current_track_temp_c=c["current_track_temp_c"],
            current_ambient_temp_c=c["current_ambient_temp_c"],
            forecast_future_ambient_temp_c=0.0,  # probe only; not used for OUT_OF_SUPPORT cases
        )

        row = dict(
            case_id=c["case_id"], event_year=c["event_year"], car_or_entry_id=c["car_or_entry_id"],
            decision_time=decision_time_iso,
            current_official_speed=None,  # not reconstructed: not required by the physical-response model itself
            realised_attempt_time=c["realised_attempt_time"].tz_convert("UTC").isoformat().replace("+00:00", "Z"),
            realised_horizon_minutes=round(c["realised_horizon_minutes"], 2),
            observed_delta_v=c["observed_delta_v"],
            current_track_temp_c=c["current_track_temp_c"], current_ambient_temp_c=c["current_ambient_temp_c"],
            forecast_source=None, forecast_model=None, forecast_run=None, forecast_issue_time=None,
            target_horizon_minutes=eval_horizon, target_time=None,
            forecast_ambient_temp_c=None, forecast_solar_state=None,
            forecast_valid_time=None, forecast_target_time_error_minutes=None,
            expected_delta_v=None, median_delta_v=None, p_improve=None,
            pi80_low=None, pi80_high=None, pi90_low=None, pi90_high=None,
            absolute_error=None, squared_error=None, direction_correct=None,
            covered_80=None, covered_90=None,
            applicability_status=gate_probe.status,
            input_hash=None, prediction_hash=None,
            realised_env_expected_delta_v=None, realised_env_absolute_error=None,
            forecast_ambient_error_c=None,
            horizon_treatment=("EVALUATED_AT_NEAREST_ANCHOR_60MIN_PREDECLARED_RULE" if is_car60
                                else "REALISED_HORIZON_EXCEEDS_120MIN_NOT_EVALUATED"),
        )

        if gate_probe.status == "OUT_OF_SUPPORT":
            case_rows.append(row)
            replay_events.append(dict(case_id=c["case_id"], decision_time=decision_time_iso,
                                       applicability_status="OUT_OF_SUPPORT", note="realised horizon exceeds 120 min production boundary"))
            continue

        # -------- only car 60 reaches here --------
        target_time_iso = shadow_engine.target_time_for(decision_time_iso, eval_horizon)
        target_time = pd.Timestamp(target_time_iso)

        # Comparison A: realised-environment ambient at the anchor target_time.
        real_row, real_gap = _nearest_reading(raw, c["event_year"], None, target_time)
        realised_future_ambient_c = float(real_row["ambient_c"])

        # Comparison B: point-in-time forecast vintage.
        selection = store.select(decision_time_iso, target_time_iso)

        snapshot, guard, selections = shadow_engine.select_and_build_snapshot(
            store=store, snapshot_id=f"phase2:{c['case_id']}", event_year=c["event_year"],
            car_or_entry_id=c["car_or_entry_id"], decision_time=decision_time_iso,
            current_track_temp_c=c["current_track_temp_c"], current_ambient_temp_c=c["current_ambient_temp_c"],
            current_track_temp_known_at=decision_time_iso, current_ambient_temp_known_at=decision_time_iso,
            horizons_min=[eval_horizon],
        )
        assert guard.passed, guard.reasons
        vintage = selections[eval_horizon]["vintage"]
        vt_error = selections[eval_horizon]["valid_time_error_minutes"]

        result_b = shadow_engine.run_single_horizon(
            snapshot, eval_horizon, vintage, LATITUDE_DEG, LONGITUDE_DEG, RANDOM_SEED, N_MC, SHADOW_DIR,
        )
        assert result_b.status == "OK", (result_b.status, result_b.reasons)
        pred = result_b.prediction

        # Comparison A run through the SAME adapter, same seed, differing only in
        # the ambient input (realised vs. forecast) -- isolates forecast error.
        output_a = final_v2_adapter.infer(
            current_track_temp_c=c["current_track_temp_c"], current_ambient_temp_c=c["current_ambient_temp_c"],
            forecast_future_ambient_temp_c=realised_future_ambient_c,
            decision_time=decision_time_iso, target_time=target_time_iso, horizon_min=eval_horizon,
            latitude_deg=LATITUDE_DEG, longitude_deg=LONGITUDE_DEG, random_seed=RANDOM_SEED, n_mc=N_MC,
        )

        abs_err_b = abs(pred.expected_delta_v - c["observed_delta_v"])
        abs_err_a = abs(output_a.expected_delta_v - c["observed_delta_v"])

        row.update(dict(
            forecast_source=vintage.source, forecast_model=vintage.model_name, forecast_run=vintage.model_run,
            forecast_issue_time=vintage.issue_time, target_time=target_time_iso,
            forecast_ambient_temp_c=vintage.ambient_temp_c, forecast_solar_state=None,
            forecast_valid_time=vintage.valid_time, forecast_target_time_error_minutes=round(vt_error, 2),
            expected_delta_v=pred.expected_delta_v, median_delta_v=pred.median_delta_v, p_improve=pred.p_improve,
            pi80_low=pred.pi80_low, pi80_high=pred.pi80_high, pi90_low=pred.pi90_low, pi90_high=pred.pi90_high,
            absolute_error=abs_err_b, squared_error=abs_err_b ** 2,
            direction_correct=bool(np.sign(pred.expected_delta_v) == np.sign(c["observed_delta_v"])),
            covered_80=bool(pred.pi80_low <= c["observed_delta_v"] <= pred.pi80_high),
            covered_90=bool(pred.pi90_low <= c["observed_delta_v"] <= pred.pi90_high),
            applicability_status=pred.applicability_status,
            input_hash=pred.input_hash, prediction_hash=pred.prediction_hash,
            realised_env_expected_delta_v=output_a.expected_delta_v,
            realised_env_absolute_error=abs_err_a,
            forecast_ambient_error_c=vintage.ambient_temp_c - realised_future_ambient_c,
        ))
        case_rows.append(row)
        replay_events.append(dict(
            case_id=c["case_id"], decision_time=decision_time_iso,
            current_official_speed=None, current_track_temp_c=c["current_track_temp_c"],
            current_ambient_temp_c=c["current_ambient_temp_c"],
            forecast_vintage_id=vintage.forecast_id, forecast_issue_time=vintage.issue_time,
            outlook_60min=dict(expected_delta_v=pred.expected_delta_v, p_improve=pred.p_improve,
                                pi80=[pred.pi80_low, pred.pi80_high]),
            applicability_status=pred.applicability_status, input_hash=pred.input_hash,
            prediction_hash=pred.prediction_hash,
        ))

    case_df = pd.DataFrame(case_rows)
    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    case_df.to_csv(EVAL_DIR / "phase2_case_table.csv", index=False)

    with open(EVAL_DIR / "phase2_replay_events.json", "w", encoding="utf-8") as f:
        json.dump(replay_events, f, indent=2, sort_keys=True, default=str)

    excluded_df = pd.DataFrame(excluded)
    excluded_df.to_csv(EVAL_DIR / "phase2_excluded_transitions.csv", index=False)

    n_supported = int((case_df["applicability_status"] == "SUPPORTED").sum())
    n_out = int((case_df["applicability_status"] == "OUT_OF_SUPPORT").sum())
    print(f"Cases: {len(case_df)}  SUPPORTED: {n_supported}  OUT_OF_SUPPORT: {n_out}")
    print(case_df[["case_id", "realised_horizon_minutes", "applicability_status", "expected_delta_v",
                    "realised_env_expected_delta_v", "observed_delta_v"]].to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
