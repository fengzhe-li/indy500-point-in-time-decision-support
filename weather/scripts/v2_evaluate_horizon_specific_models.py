from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error


INPUT_FILE = Path(
    "weather/output/v2_future_track/"
    "future_track_samples_v1.csv"
)

OUTPUT_DIR = Path(
    "weather/output/v2_future_track"
)

PREDICTIONS_FILE = (
    OUTPUT_DIR
    / "horizon_specific_predictions_v1.csv"
)

METRICS_FILE = (
    OUTPUT_DIR
    / "horizon_specific_metrics_v1.csv"
)

SUMMARY_FILE = (
    OUTPUT_DIR
    / "horizon_specific_summary_v1.txt"
)


TARGET = "delta_track_temp_c"

FEATURES = [
    "delta_ambient_temp_c",
    "thermal_gap_0_c",
]


def calculate_metrics(
    model_name,
    year,
    horizon,
    y_true,
    y_pred,
):
    error = y_pred - y_true

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
        "bias_c": np.mean(error),
        "median_abs_error_c": np.median(
            np.abs(error)
        ),
    }


def main():

    print("=" * 72)
    print(
        "INDY 500 V2-A HORIZON-SPECIFIC MODEL TEST"
    )
    print("=" * 72)

    df = pd.read_csv(INPUT_FILE)

    years = sorted(
        df["year"].unique()
    )

    horizons = sorted(
        df[
            "requested_horizon_min"
        ].unique()
    )

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
                    df[
                        "requested_horizon_min"
                    ]
                    == horizon
                )
            ].copy()

            test = df[
                (df["year"] == test_year)
                &
                (
                    df[
                        "requested_horizon_min"
                    ]
                    == horizon
                )
            ].copy()

            if len(train) == 0 or len(test) == 0:
                continue

            # ==================================================
            # Baseline M0:
            # delta track ~ delta ambient
            # ==================================================

            m0 = LinearRegression()

            m0.fit(
                train[
                    [
                        "delta_ambient_temp_c",
                    ]
                ],
                train[TARGET],
            )

            pred_m0 = m0.predict(
                test[
                    [
                        "delta_ambient_temp_c",
                    ]
                ]
            )

            metrics.append(
                calculate_metrics(
                    model_name="M0_per_horizon",
                    year=test_year,
                    horizon=horizon,
                    y_true=test[
                        TARGET
                    ].to_numpy(),
                    y_pred=pred_m0,
                )
            )

            # ==================================================
            # M1 horizon-specific:
            # delta track ~ delta ambient + thermal gap
            # ==================================================

            m1 = LinearRegression()

            m1.fit(
                train[FEATURES],
                train[TARGET],
            )

            pred_m1 = m1.predict(
                test[FEATURES]
            )

            metrics.append(
                calculate_metrics(
                    model_name="M1_per_horizon",
                    year=test_year,
                    horizon=horizon,
                    y_true=test[
                        TARGET
                    ].to_numpy(),
                    y_pred=pred_m1,
                )
            )

            coefficients.append(
                {
                    "held_out_year":
                        test_year,

                    "horizon_min":
                        horizon,

                    "intercept":
                        m1.intercept_,

                    "beta_delta_ambient":
                        m1.coef_[0],

                    "beta_thermal_gap":
                        m1.coef_[1],

                    "train_n":
                        len(train),

                    "test_n":
                        len(test),
                }
            )

            for i, (_, row) in enumerate(
                test.iterrows()
            ):

                predictions.append(
                    {
                        "pair_id":
                            row[
                                "pair_id"
                            ],

                        "held_out_year":
                            test_year,

                        "horizon_min":
                            horizon,

                        "actual":
                            row[TARGET],

                        "pred_M0":
                            pred_m0[i],

                        "pred_M1":
                            pred_m1[i],
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

    # ==========================================================
    # Aggregate metrics by model + horizon
    # ==========================================================

    agg_rows = []

    for (
        model_name,
        horizon,
    ), g in metrics_df.groupby(
        [
            "model",
            "horizon_min",
        ]
    ):

        agg_rows.append(
            {
                "model":
                    model_name,

                "horizon_min":
                    horizon,

                "macro_year_mae_c":
                    g[
                        "mae_c"
                    ].mean(),

                "macro_year_rmse_c":
                    g[
                        "rmse_c"
                    ].mean(),

                "macro_year_abs_bias_c":
                    g[
                        "bias_c"
                    ].abs().mean(),
            }
        )

    agg_df = pd.DataFrame(
        agg_rows
    )

    # ==========================================================
    # Overall macro-year comparison
    # ==========================================================

    overall_rows = []

    for model_name, g in (
        metrics_df.groupby(
            "model"
        )
    ):

        overall_rows.append(
            {
                "model":
                    model_name,

                "macro_year_mae_c":
                    g[
                        "mae_c"
                    ].mean(),

                "macro_year_rmse_c":
                    g[
                        "rmse_c"
                    ].mean(),

                "macro_year_abs_bias_c":
                    g[
                        "bias_c"
                    ].abs().mean(),
            }
        )

    overall_df = pd.DataFrame(
        overall_rows
    ).sort_values(
        "macro_year_mae_c"
    )

    # ==========================================================
    # Save
    # ==========================================================

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

    coef_file = (
        OUTPUT_DIR
        / "horizon_specific_coefficients_v1.csv"
    )

    coef_df.to_csv(
        coef_file,
        index=False,
    )

    # ==========================================================
    # Summary
    # ==========================================================

    lines = []

    def add(x=""):
        lines.append(str(x))

    add("=" * 72)
    add("OVERALL MACRO-YEAR COMPARISON")
    add("=" * 72)

    add()
    add(
        overall_df
        .round(4)
        .to_string(
            index=False
        )
    )

    add()
    add("=" * 72)
    add("MAE BY HORIZON")
    add("=" * 72)

    mae_table = (
        agg_df.pivot(
            index="model",
            columns="horizon_min",
            values="macro_year_mae_c",
        )
    )

    add()
    add(
        mae_table
        .round(4)
        .to_string()
    )

    add()
    add("=" * 72)
    add("M1 THERMAL-GAP COEFFICIENT BY HORIZON")
    add("=" * 72)

    coef_summary = (
        coef_df.groupby(
            "horizon_min"
        )[
            "beta_thermal_gap"
        ]
        .agg(
            [
                "mean",
                "std",
                "min",
                "max",
            ]
        )
    )

    add()
    add(
        coef_summary
        .round(5)
        .to_string()
    )

    add()
    add("=" * 72)
    add("M1 AMBIENT-CHANGE COEFFICIENT BY HORIZON")
    add("=" * 72)

    ambient_summary = (
        coef_df.groupby(
            "horizon_min"
        )[
            "beta_delta_ambient"
        ]
        .agg(
            [
                "mean",
                "std",
                "min",
                "max",
            ]
        )
    )

    add()
    add(
        ambient_summary
        .round(5)
        .to_string()
    )

    add()
    add("=" * 72)
    add("YEAR × HORIZON M1 MAE")
    add("=" * 72)

    m1_year_h = (
        metrics_df[
            metrics_df["model"]
            == "M1_per_horizon"
        ]
        .pivot(
            index="held_out_year",
            columns="horizon_min",
            values="mae_c",
        )
    )

    add()
    add(
        m1_year_h
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

    print(
        "\nOUTPUT FILES"
    )

    print(
        PREDICTIONS_FILE
    )

    print(
        METRICS_FILE
    )

    print(
        coef_file
    )

    print(
        SUMMARY_FILE
    )

    print(
        "\nDONE"
    )


if __name__ == "__main__":
    main()