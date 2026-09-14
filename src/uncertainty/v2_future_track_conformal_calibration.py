from pathlib import Path

import math
import numpy as np
import pandas as pd

INPUT_FILE = Path("weather/output/v2_future_track/solar_model_predictions_v1.csv")
OUTPUT_DIR = Path("weather/output/v2_future_track")
OUTPUT_FILE = OUTPUT_DIR / "future_track_conformal_calibration_v1.csv"
SUMMARY_FILE = OUTPUT_DIR / "future_track_conformal_calibration_v1.txt"

MODELS = ["M1_no_solar", "M2b_mean_solar"]


def conformal_quantile(abs_residuals, coverage):
    x = np.sort(np.asarray(abs_residuals))
    n = len(x)
    rank = math.ceil((n + 1) * coverage)
    rank = min(max(rank, 1), n)
    return x[rank - 1]


def summarize(g):
    actual = g["actual"]
    c80 = (actual >= g["lower80"]) & (actual <= g["upper80"])
    c90 = (actual >= g["lower90"]) & (actual <= g["upper90"])
    return pd.Series({
        "n": len(g),
        "coverage80": c80.mean(),
        "coverage90": c90.mean(),
        "width80_c": (g["upper80"] - g["lower80"]).mean(),
        "width90_c": (g["upper90"] - g["lower90"]).mean(),
        "mae_c": np.mean(np.abs(g["actual"] - g["predicted"])),
    })


def main():
    print("=" * 72)
    print("INDY 500 V2-A HORIZON-SPECIFIC CONFORMAL CALIBRATION")
    print("=" * 72)

    df = pd.read_csv(INPUT_FILE)
    df = df[df["model"].isin(MODELS)].copy()
    df["residual"] = df["actual"] - df["predicted"]
    df["abs_residual"] = df["residual"].abs()
    years = sorted(df["held_out_year"].unique())
    rows = []

    for model_name in MODELS:
        model_df = df[df["model"] == model_name].copy()
        for test_year in years:
            test = model_df[model_df["held_out_year"] == test_year].copy()
            for _, row in test.iterrows():
                horizon = row["horizon_min"]
                calibration = model_df[
                    (model_df["held_out_year"] != test_year)
                    & (model_df["horizon_min"] == horizon)
                ].copy()
                abs_res = calibration["abs_residual"].to_numpy()
                q80 = conformal_quantile(abs_res, 0.80)
                q90 = conformal_quantile(abs_res, 0.90)
                rows.append({
                    "pair_id": row["pair_id"],
                    "model": model_name,
                    "held_out_year": test_year,
                    "horizon_min": horizon,
                    "actual": row["actual"],
                    "predicted": row["predicted"],
                    "q80": q80,
                    "q90": q90,
                    "lower80": row["predicted"] - q80,
                    "upper80": row["predicted"] + q80,
                    "lower90": row["predicted"] - q90,
                    "upper90": row["predicted"] + q90,
                    "calibration_n": len(calibration),
                })

    out = pd.DataFrame(rows)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUTPUT_FILE, index=False)

    overall = out.groupby("model").apply(summarize, include_groups=False)
    horizon = out.groupby(["model", "horizon_min"]).apply(summarize, include_groups=False)
    year = out.groupby(["model", "held_out_year"]).apply(summarize, include_groups=False)

    lines = []
    def add(x=""):
        lines.append(str(x))

    add("=" * 72); add("OVERALL CONFORMAL COVERAGE"); add("=" * 72); add()
    add(overall.round(4).to_string())
    add(); add("=" * 72); add("80% COVERAGE BY HORIZON"); add("=" * 72); add()
    add(horizon["coverage80"].unstack().round(4).to_string())
    add(); add("=" * 72); add("90% COVERAGE BY HORIZON"); add("=" * 72); add()
    add(horizon["coverage90"].unstack().round(4).to_string())
    add(); add("=" * 72); add("80% WIDTH BY HORIZON"); add("=" * 72); add()
    add(horizon["width80_c"].unstack().round(4).to_string())
    add(); add("=" * 72); add("90% WIDTH BY HORIZON"); add("=" * 72); add()
    add(horizon["width90_c"].unstack().round(4).to_string())
    add(); add("=" * 72); add("80% COVERAGE BY YEAR"); add("=" * 72); add()
    add(year["coverage80"].unstack().round(4).to_string())
    add(); add("=" * 72); add("90% COVERAGE BY YEAR"); add("=" * 72); add()
    add(year["coverage90"].unstack().round(4).to_string())

    summary = "\n".join(lines)
    SUMMARY_FILE.write_text(summary, encoding="utf-8")
    print(); print(summary); print(); print("OUTPUT"); print(OUTPUT_FILE); print(SUMMARY_FILE); print(); print("DONE")


if __name__ == "__main__":
    main()
