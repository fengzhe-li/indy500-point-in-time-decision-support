"""Phase 2 Step 17 — freeze package.

Status: V3_PHASE2_POINT_IN_TIME_EVALUATION_FROZEN (NOT "FINAL_V3").

This freeze is honest about scale: it freezes a real, fully-instrumented
point-in-time execution over 10 real historical transitions, of which
exactly 1 falls within FINAL_V2's calibrated <=120-minute production
boundary. N=1 is not a statistically meaningful sample; it is frozen as
a validated demonstration that the point-in-time execution path
(POINT-IN-TIME -> FROZEN FINAL_V2 -> IMMUTABLE PREDICTION) works
end-to-end on genuine (non-synthetic) evidence, not as a performance
claim about the frozen model under forecast uncertainty in general.
"""
from __future__ import annotations

import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC_DIR))
REPO_ROOT = Path(__file__).resolve().parents[2]

from hashing import sha256_file  # noqa: E402

V3_ROOT = Path(__file__).resolve().parents[1]
EVAL_DIR = V3_ROOT / "output" / "evaluation"
QA_DIR = V3_ROOT / "output" / "qa"
FREEZE_DIR = V3_ROOT / "output" / "phase2_freeze"

STATUS = "V3_PHASE2_POINT_IN_TIME_EVALUATION_FROZEN"


def main() -> int:
    FREEZE_DIR.mkdir(parents=True, exist_ok=True)

    case_table_src = EVAL_DIR / "phase2_case_table.csv"
    with open(case_table_src, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    n_total = len(rows)
    n_supported = sum(1 for r in rows if r["applicability_status"] == "SUPPORTED")
    n_out = sum(1 for r in rows if r["applicability_status"] == "OUT_OF_SUPPORT")

    # phase2_case_table.csv (copy, byte for byte)
    case_table_dst = FREEZE_DIR / "phase2_case_table.csv"
    case_table_dst.write_bytes(case_table_src.read_bytes())

    # phase2_metrics.csv -- deliberately minimal given N=1; no fabricated
    # aggregate MAE/RMSE/coverage over a single point.
    supported_row = next((r for r in rows if r["applicability_status"] == "SUPPORTED"), None)
    metrics_path = FREEZE_DIR / "phase2_metrics.csv"
    with open(metrics_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["metric", "value", "note"])
        w.writerow(["n_total_candidate_cases", n_total, "real transitions with unambiguous pair + usable timestamps"])
        w.writerow(["n_supported_le_120min", n_supported, "evaluated with FINAL_V2 scientific inference"])
        w.writerow(["n_out_of_support_gt_120min", n_out, "realised horizon exceeds production boundary; not evaluated"])
        if supported_row:
            w.writerow(["single_case_id", supported_row["case_id"], ""])
            w.writerow(["single_case_observed_delta_v", supported_row["observed_delta_v"], ""])
            w.writerow(["single_case_forecast_expected_delta_v", supported_row["expected_delta_v"], ""])
            w.writerow(["single_case_realised_env_expected_delta_v", supported_row["realised_env_expected_delta_v"], ""])
            w.writerow(["single_case_absolute_error_forecast", supported_row["absolute_error"], ""])
            w.writerow(["single_case_absolute_error_realised_env", supported_row["realised_env_absolute_error"], ""])
            w.writerow(["single_case_forecast_target_time_error_minutes", supported_row["forecast_target_time_error_minutes"], ""])
        w.writerow(["MAE_RMSE_coverage_aggregate", "NOT_COMPUTED", "N=1 is statistically meaningless for aggregate error/coverage statistics"])

    # phase2_source_manifest.csv -- every real evidence source used.
    sources = [
        ("pipeline.reconcile.build() -> attempts table", "chronology reconstruction (unmodified pipeline code)"),
        ("r5_2/manual/probabilistic_physics_loyo_residuals_v1.csv", "observed outcome (delta_four_lap_average_speed_mph)"),
        ("weather/evidence/ptsc/indy500_day1_track_temp_2020_2024_time_normalized.csv", "real observed track/ambient readings"),
        ("weather/output/hrrr_ims_2020_2024_features.csv", "real NOAA HRRR forecast vintages"),
        ("weather/output/v2_future_track/v2a_full_sample_track_model_coefficients_v1.csv", "frozen M2b coefficients (read-only)"),
        ("weather/output/v2_future_track/future_track_residuals_v1.csv", "frozen track-residual pool (read-only)"),
        ("r5_2/manual/probabilistic_physics_coefficient_bootstrap_v1.csv", "frozen performance bootstrap draws (read-only)"),
    ]
    manifest_path = FREEZE_DIR / "phase2_source_manifest.csv"
    with open(manifest_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["source", "role"])
        for s, role in sources:
            w.writerow([s, role])

    # phase2_hashes.csv -- hash every real evidence source that is an actual
    # file (the pipeline.reconcile.build() entry is code, not a data file,
    # so it is excluded here and covered instead by the Phase 1/2
    # immutability checks, which hash pipeline.parsers.weather etc.).
    hash_targets = [REPO_ROOT / s for s, _ in sources if (REPO_ROOT / s).is_file()]
    hashes_path = FREEZE_DIR / "phase2_hashes.csv"
    with open(hashes_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["path", "sha256"])
        for p in hash_targets:
            w.writerow([str(p.relative_to(REPO_ROOT)), sha256_file(p)])
        w.writerow(["phase2_case_table.csv (frozen copy)", sha256_file(case_table_dst)])

    summary_lines = [
        "=" * 72,
        "INDY 500 V3 PHASE 2 -- FREEZE SUMMARY",
        "=" * 72,
        "",
        f"Status: {STATUS}",
        "This is explicitly NOT FINAL_V3 and NOT a general performance claim.",
        "",
        f"Real candidate point-in-time cases (unambiguous transition, usable timestamps): {n_total}",
        f"Supported (<=120 min production boundary): {n_supported}",
        f"Out of support (realised horizon > 120 min): {n_out}",
        "",
        "*** N=1 IS THE ENTIRE SCIENTIFICALLY EVALUABLE SAMPLE ***",
        "No aggregate MAE/RMSE/coverage/directional-accuracy statistic is computed",
        "or claimed, because a single case cannot support one. See",
        "phase2_qa_report.md and phase2_minimum_data_plan.md for the full",
        "reasoning and the 9 excluded (out-of-support) real cases, which are",
        "not hidden -- they are in phase2_case_table.csv with their real",
        "realised horizons (125.8-288.0 minutes) and OUT_OF_SUPPORT status.",
        "",
        "The single evaluated case (2021, car 60) showed a large observed",
        "improvement (+4.695 mph) that BOTH the point-in-time-forecast",
        "inference (+0.024 mph) and the realised-environment inference",
        "(+0.045 mph) substantially under-predicted. This is consistent with",
        "the frozen system's own documented position that latent setup,",
        "tyre, and execution factors dominate much of the predictive spread",
        "-- it is reported here, not concealed, per specification Step 13.",
        "",
        f"Frozen at: {datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')}",
    ]
    (FREEZE_DIR / "phase2_summary.txt").write_text("\n".join(summary_lines), encoding="utf-8")

    manifest = {
        "phase": 2,
        "status": STATUS,
        "not_to_be_called": "FINAL_V3",
        "n_total_candidate_cases": n_total,
        "n_supported": n_supported,
        "n_out_of_support": n_out,
        "sample_size_caveat": (
            "N=1 supported case. No aggregate error/coverage statistics are "
            "computed or claimed. This freeze demonstrates the point-in-time "
            "execution path end-to-end on real evidence, not a validated "
            "performance benchmark."
        ),
        "files": ["phase2_summary.txt", "phase2_metrics.csv", "phase2_case_table.csv",
                  "phase2_source_manifest.csv", "phase2_hashes.csv"],
        "frozen_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    (FREEZE_DIR / "phase2_freeze_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
    )

    print(f"Froze Phase 2 package to {FREEZE_DIR} with status {STATUS}")
    print(f"n_total={n_total} n_supported={n_supported} n_out_of_support={n_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
