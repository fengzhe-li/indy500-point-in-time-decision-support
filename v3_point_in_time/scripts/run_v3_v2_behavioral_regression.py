"""Phase 2 Step 6 — V3-vs-frozen-V2 behavioural regression check.

Phase 1 proved byte-level immutability of frozen files. This proves the
V3 adapter's *behaviour* matches the frozen batch script's own recorded
output for identical scientific inputs, at all five calibrated
horizons.

Method: for one real row per horizon from the frozen
`v2a_performance_mc_integration_v1.csv` (the original script's own
output), reconstruct the exact real decision_time/target_time for that
row from `future_track_samples_with_solar_v1.csv` (joined by
`pair_id`), and a `forecast_future_ambient_temp_c` that reproduces the
frozen row's own `delta_ambient_temp_c` exactly
(current_ambient_temp_c + delta_ambient_temp_c). This is NOT a claim
about forecast realism -- it is a controlled input-identity check: "if
V3 is given the same physical scenario, does it produce the same
scientific answer?"

Because V3 seeds a fresh RNG per (snapshot, horizon) call rather than
advancing one shared stream across ~656 rows the way the original batch
script does (documented in v3_config.yaml and
existing_system_inventory.md), the two runs use DIFFERENT random
draws from the SAME frozen residual/bootstrap pools. Exact numerical
equality is therefore not expected or required. What IS required: with
a large enough n_mc, both runs are independent Monte Carlo estimates of
the SAME underlying analytic distribution, so they must agree within
Monte Carlo sampling error. This script uses a large n_mc (50,000) and
a tolerance derived from the frozen run's own reported mc_sd_mph
(standard deviation of the underlying draws), not an arbitrarily chosen
number.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC_DIR))

REPO_ROOT = Path(__file__).resolve().parents[2]
QA_DIR = Path(__file__).resolve().parents[1] / "output" / "qa"
REPORT_FILE = QA_DIR / "v3_v2_behavioural_regression_report.md"

import final_v2_adapter  # noqa: E402

REF_FILE = REPO_ROOT / "weather/output/v2_future_track/v2a_performance_mc_integration_v1.csv"
SAMPLES_FILE = REPO_ROOT / "weather/output/v2_future_track/future_track_samples_with_solar_v1.csv"

LATITUDE_DEG = 39.7950
LONGITUDE_DEG = -86.2348
N_MC = 50000
RANDOM_SEED = 20260914 + 1  # deliberately DIFFERENT from the reference run's seed/stream position

# Approximate combined MC standard error tolerance multiplier. Two
# independent MC estimates of the same mean, each with standard
# deviation ~mc_sd over n_mc draws, differ by more than
# k * mc_sd * sqrt(2/n_mc) with probability roughly 2*(1-Phi(k)).
# k=5 is a deliberately generous tolerance (chance of a false failure
# under correct behaviour is astronomically small), chosen because this
# is a regression *safety* check, not a precision benchmark.
TOLERANCE_K = 5.0


def main() -> int:
    ref = pd.read_csv(REF_FILE)
    samples = pd.read_csv(SAMPLES_FILE).set_index("pair_id")

    rows = []
    for horizon in (15, 30, 60, 90, 120):
        ref_row = ref[ref["horizon_min"] == horizon].iloc[0]
        pair_id = ref_row["pair_id"]
        sample = samples.loc[pair_id]

        decision_time = pd.Timestamp(sample["t0_utc"]).tz_convert("UTC").isoformat().replace("+00:00", "Z")
        target_time = pd.Timestamp(sample["future_utc"]).tz_convert("UTC").isoformat().replace("+00:00", "Z")

        current_track_temp_c = float(ref_row["current_track_temp_c"])
        current_ambient_temp_c = float(ref_row["current_ambient_temp_c"])
        forecast_future_ambient_temp_c = current_ambient_temp_c + float(ref_row["delta_ambient_temp_c"])

        output = final_v2_adapter.infer(
            current_track_temp_c=current_track_temp_c,
            current_ambient_temp_c=current_ambient_temp_c,
            forecast_future_ambient_temp_c=forecast_future_ambient_temp_c,
            decision_time=decision_time,
            target_time=target_time,
            horizon_min=horizon,
            latitude_deg=LATITUDE_DEG,
            longitude_deg=LONGITUDE_DEG,
            random_seed=RANDOM_SEED,
            n_mc=N_MC,
        )

        ref_mc_sd = float(ref_row["mc_sd_mph"])
        tolerance = TOLERANCE_K * ref_mc_sd * np.sqrt(2.0 / N_MC)

        diff_expected = output.expected_delta_v - float(ref_row["expected_delta_speed_mph"])
        diff_median = output.median_delta_v - float(ref_row["median_delta_speed_mph"])
        pass_expected = abs(diff_expected) <= tolerance
        pass_median = abs(diff_median) <= tolerance

        rows.append(dict(
            horizon_min=horizon,
            pair_id=pair_id,
            ref_expected_delta_v=float(ref_row["expected_delta_speed_mph"]),
            v3_expected_delta_v=output.expected_delta_v,
            diff_expected_delta_v=diff_expected,
            ref_median_delta_v=float(ref_row["median_delta_speed_mph"]),
            v3_median_delta_v=output.median_delta_v,
            diff_median_delta_v=diff_median,
            ref_p_improve=float(ref_row["p_improve"]),
            v3_p_improve=output.p_improve,
            ref_pi80=(float(ref_row["lower_80_mph"]), float(ref_row["upper_80_mph"])),
            v3_pi80=(output.pi80_low, output.pi80_high),
            ref_mc_sd=ref_mc_sd,
            v3_mc_sd=output.mc_sd,
            tolerance=tolerance,
            pass_expected=pass_expected,
            pass_median=pass_median,
        ))

    all_pass = all(r["pass_expected"] and r["pass_median"] for r in rows)

    lines = []
    lines.append("# Phase 2 Step 6 — V3 vs Frozen V2 Behavioural Regression Report")
    lines.append("")
    lines.append(f"n_mc={N_MC}, tolerance = {TOLERANCE_K} x mc_sd_reference x sqrt(2/n_mc) (Monte Carlo sampling-error bound, not an arbitrary number).")
    lines.append("")
    lines.append("V3 intentionally uses a different RNG seed/stream than the frozen batch script")
    lines.append("(documented design decision, see existing_system_inventory.md). This checks")
    lines.append("statistical agreement of two independent Monte Carlo estimates of the same")
    lines.append("frozen analytic model, not bitwise equality.")
    lines.append("")
    lines.append("| Horizon | Ref E[Δv] | V3 E[Δv] | Diff | Tolerance | Pass | Ref median | V3 median | Pass | Ref P(imp) | V3 P(imp) |")
    lines.append("|---|---:|---:|---:|---:|---|---:|---:|---|---:|---:|")
    for r in rows:
        lines.append(
            f"| {r['horizon_min']} | {r['ref_expected_delta_v']:+.4f} | {r['v3_expected_delta_v']:+.4f} | "
            f"{r['diff_expected_delta_v']:+.4f} | {r['tolerance']:.4f} | {'PASS' if r['pass_expected'] else 'FAIL'} | "
            f"{r['ref_median_delta_v']:+.4f} | {r['v3_median_delta_v']:+.4f} | {'PASS' if r['pass_median'] else 'FAIL'} | "
            f"{r['ref_p_improve']:.4f} | {r['v3_p_improve']:.4f} |"
        )
    lines.append("")
    lines.append("80% predictive interval comparison (illustrative; PI bounds are quantiles, not")
    lines.append("means, so no formal tolerance is applied -- shown for qualitative agreement only):")
    lines.append("")
    lines.append("| Horizon | Ref 80% PI | V3 80% PI |")
    lines.append("|---|---|---|")
    for r in rows:
        lines.append(f"| {r['horizon_min']} | [{r['ref_pi80'][0]:+.3f}, {r['ref_pi80'][1]:+.3f}] | [{r['v3_pi80'][0]:+.3f}, {r['v3_pi80'][1]:+.3f}] |")
    lines.append("")
    lines.append(f"## Overall result: {'PASS' if all_pass else 'FAIL'}")
    lines.append("")
    if not all_pass:
        lines.append("STOP: at least one horizon shows a mean/median difference exceeding the Monte")
        lines.append("Carlo sampling-error tolerance. This would indicate the V3 adapter diverges")
        lines.append("scientifically from the frozen implementation and must be investigated before")
        lines.append("any Phase 2 scientific evaluation proceeds.")
    else:
        lines.append("V3's adapter reproduces the frozen FINAL_V2 physical-response Monte Carlo")
        lines.append("integration within Monte Carlo sampling error at all five calibrated horizons,")
        lines.append("using a different (intentionally independent) random stream. The observed")
        lines.append("differences are consistent with sampling noise, not a change in the underlying")
        lines.append("model, coefficients, or residual pools.")

    report = "\n".join(lines)
    REPORT_FILE.write_text(report, encoding="utf-8")
    print(report)
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
