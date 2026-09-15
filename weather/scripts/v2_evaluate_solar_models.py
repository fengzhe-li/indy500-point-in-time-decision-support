from pathlib import Path

import numpy as np
import pandas as pd

from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error


INPUT_FILE = Path(
    "weather/output/v2_future_track/"
    "future_track_samples_with_solar_v1.csv"
)

OUTPUT_DIR = Path(
    "weather/output/v2_future_track"
)

PREDICTIONS_FILE = OUTPUT_DIR / "solar_model_predictions_v1.csv"
METRICS_FILE = OUTPUT_DIR / "solar_model_metrics_v1.csv"
COEFFICIENTS_FILE = OUTPUT_DIR / "solar_model_coefficients_v1.csv"
SUMMARY_FILE = OUTPUT_DIR / "solar_model_summary_v1.txt"


TARGET = "delta_track_temp_c"

MODELS = {
    "M1_no_solar": [
        "delta_ambient_temp_c",
        "thermal_gap_0_c",
    ],

    "M2a_delta_solar": [
        "delta_ambient_temp_c",
        "thermal_gap_0_c",
        "delta_solar_elevation_deg",
    ],

    "M2b_mean_solar": [
        "delta_ambient_temp_c",
        "thermal_gap_0_c",
        "solar_elevation_mean_deg",
    ],

    "M2c_both_solar": [
        "delta_ambient_temp_c",
        "thermal_gap_0_c",
        "delta_solar_elevation_deg",
        "solar_elevation_mean_deg",
    ],
}


def metric_row(
    model_name,
    year,
    horizon,
    y_true,
    y_pred,
):
    err = y_pred - y_true

    return {
        "model": model_name,
        "held_out_year": year,
        "horizon_min": horizon,
        "n": len(y_true),

        "mae_c": mean_absolute_error(
            y_true,
            y_pred,
        ),

        "rmse_c": np.sqrt(
            mean_squared_error(
                y_true,
                y_pred,
            )
        ),

        "bias_c": np.mean(err),

        "median_abs_error_c": np.median(
            np.abs(err)
        ),
    }


def main():

    print("=" * 72)
    print("INDY 500 V2-A SOLAR MODEL TEST")
    print("=" * 72)

    df = pd.read_csv(INPUT_FILE)

    years = sorted(
        df["year"].unique()
    )

    horizons = sorted(
        df["requested_horizon_min"].unique()
    )

    print(f"\nRows: {len(df)}")
    print(f"Years: {years}")
    print(f"Horizons: {horizons}")

    predictions = []
    metrics = []
    coefficients = []

    for test_year in years:

        print(
            f"\nHeld out year: {test_year}"
        )

        for horizon in horizons:

            train = df[
                (df["year"] != test_year)
                &
                (
                    df["requested_horizon_min"]
                    == horizon
                )
            ].copy()

            test = df[
                (df["year"] == test_year)
                &
                (
                    df["requested_horizon_min"]
                    == horizon
                )
            ].copy()

            if len(train) == 0 or len(test) == 0:
                continue

            for model_name, features in MODELS.items():

                model = LinearRegression()

                model.fit(
                    train[features],
                    train[TARGET],
                )

                pred = model.predict(
                    test[features]
                )

                metrics.append(
                    metric_row(
                        model_name,
                        test_year,
                        horizon,
                        test[TARGET].to_numpy(),
                        pred,
                    )
                )

                coef_record = {
                    "model": model_name,
                    "held_out_year": test_year,
                    "horizon_min": horizon,
                    "intercept": model.intercept_,
                    "train_n": len(train),
                    "test_n": len(test),
                }

                for feature, coef in zip(
                    features,
                    model.coef_,
                ):
                    coef_record[
                        f"beta_{feature}"
                    ] = coef

                coefficients.append(
                    coef_record
                )

                for i, (_, row) in enumerate(
                    test.iterrows()
                ):
                    predictions.append(
                        {
                            "pair_id":
                                row["pair_id"],

                            "held_out_year":
                                test_year,

                            "horizon_min":
                                horizon,

                            "model":
                                model_name,

                            "actual":
                                row[TARGET],

                            "predicted":
                                pred[i],
                        }
                    )

    metrics_df = pd.DataFrame(
        metrics
    )

    predictions_df = pd.DataFrame(
        predictions
    )

    coef_df = pd.DataFrame(
        coefficients
    )

    # =========================================================
    # Macro year x horizon average
    # =========================================================

    overall = (
        metrics_df
        .groupby("model")
        .agg(
            macro_mae_c=(
                "mae_c",
                "mean",
            ),
            macro_rmse_c=(
                "rmse_c",
                "mean",
            ),
            macro_abs_bias_c=(
                "bias_c",
                lambda s:
                np.mean(np.abs(s)),
            ),
        )
        .sort_values(
            "macro_mae_c"
        )
    )

    # =========================================================
    # Horizon table
    # =========================================================

    horizon_mae = (
        metrics_df
        .groupby(
            [
                "model",
                "horizon_min",
            ]
        )["mae_c"]
        .mean()
        .unstack()
    )

    # =========================================================
    # Year table
    # =========================================================

    year_mae = (
        metrics_df
        .groupby(
            [
                "model",
                "held_out_year",
            ]
        )["mae_c"]
        .mean()
        .unstack()
    )

    # =========================================================
    # Solar gain vs M1
    # Positive = solar model is better
    # =========================================================

    base = (
        metrics_df[
            metrics_df["model"]
            == "M1_no_solar"
        ][
            [
                "held_out_year",
                "horizon_min",
                "mae_c",
            ]
        ]
        .rename(
            columns={
                "mae_c":
                    "m1_mae_c"
            }
        )
    )

    gain = metrics_df.merge(
        base,
        on=[
            "held_out_year",
            "horizon_min",
        ],
        how="left",
    )

    gain["mae_gain_vs_m1_c"] = (
        gain["m1_mae_c"]
        - gain["mae_c"]
    )

    gain_summary = (
        gain[
            gain["model"]
            != "M1_no_solar"
        ]
        .groupby("model")
        .agg(
            mean_gain_c=(
                "mae_gain_vs_m1_c",
                "mean",
            ),
            improved_folds=(
                "mae_gain_vs_m1_c",
                lambda s:
                int((s > 0).sum()),
            ),
            total_folds=(
                "mae_gain_vs_m1_c",
                "size",
            ),
        )
        .sort_values(
            "mean_gain_c",
            ascending=False,
        )
    )

    # =========================================================
    # Solar gain by horizon
    # =========================================================

    gain_by_horizon = (
        gain[
            gain["model"]
            != "M1_no_solar"
        ]
        .groupby(
            [
                "model",
                "horizon_min",
            ]
        )[
            "mae_gain_vs_m1_c"
        ]
        .mean()
        .unstack()
    )

    # =========================================================
    # Save
    # =========================================================

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    predictions_df.to_csv(
        PREDICTIONS_FILE,
        index=False,
    )

    metrics_df.to_csv(
        METRICS_FILE,
        index=False,
    )

    coef_df.to_csv(
        COEFFICIENTS_FILE,
        index=False,
    )

    # =========================================================
    # Summary
    # =========================================================

    lines = []

    def add(x=""):
        lines.append(str(x))

    add("=" * 72)
    add("OVERALL MACRO COMPARISON")
    add("=" * 72)
    add()
    add(
        overall
        .round(4)
        .to_string()
    )

    add()
    add("=" * 72)
    add("MAE BY HORIZON")
    add("=" * 72)
    add()
    add(
        horizon_mae
        .round(4)
        .to_string()
    )

    add()
    add("=" * 72)
    add("MAE BY HELD-OUT YEAR")
    add("=" * 72)
    add()
    add(
        year_mae
        .round(4)
        .to_string()
    )

    add()
    add("=" * 72)
    add("SOLAR GAIN VS M1")
    add("positive = solar model better")
    add("=" * 72)
    add()
    add(
        gain_summary
        .round(4)
        .to_string()
    )

    add()
    add("=" * 72)
    add("SOLAR GAIN BY HORIZON")
    add("positive = solar model better")
    add("=" * 72)
    add()
    add(
        gain_by_horizon
        .round(4)
        .to_string()
    )

    add()
    add("=" * 72)
    add("2022 MAE")
    add("=" * 72)
    add()

    y2022 = (
        metrics_df[
            metrics_df[
                "held_out_year"
            ]
            == 2022
        ]
        .pivot(
            index="model",
            columns="horizon_min",
            values="mae_c",
        )
    )

    add(
        y2022
        .round(4)
        .to_string()
    )

    summary = "\n".join(
        lines
    )

    SUMMARY_FILE.write_text(
        summary,
        encoding="utf-8",
    )

    print()
    print(summary)

    print()
    print("OUTPUT FILES")
    print(PREDICTIONS_FILE)
    print(METRICS_FILE)
    print(COEFFICIENTS_FILE)
    print(SUMMARY_FILE)

    print()
    print("DONE")


if __name__ == "__main__":
    main()
