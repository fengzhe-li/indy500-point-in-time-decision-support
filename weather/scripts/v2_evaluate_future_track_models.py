from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


INPUT_FILE = Path(
    "weather/output/v2_future_track/"
    "future_track_samples_v1.csv"
)

OUTPUT_DIR = Path(
    "weather/output/v2_future_track"
)

PREDICTIONS_FILE = (
    OUTPUT_DIR
    / "future_track_model_predictions_v1.csv"
)

METRICS_FILE = (
    OUTPUT_DIR
    / "future_track_model_metrics_v1.csv"
)

SUMMARY_FILE = (
    OUTPUT_DIR
    / "future_track_model_summary_v1.txt"
)


TARGET = "delta_track_temp_c"

MODELS = {
    "M0": [
        "requested_horizon_min",
        "delta_ambient_temp_c",
    ],

    "M1": [
        "requested_horizon_min",
        "delta_ambient_temp_c",
        "thermal_gap_0_c",
    ],

    "M2a": [
        "requested_horizon_min",
        "delta_ambient_temp_c",
        "thermal_gap_0_c",
        "track_rate_0_c_per_min",
    ],
}


def build_model(feature_cols):

    categorical = [
        "requested_horizon_min"
    ]

    numeric = [
        col
        for col in feature_cols
        if col not in categorical
    ]

    prep = ColumnTransformer(
        transformers=[
            (
                "horizon",
                OneHotEncoder(
                    handle_unknown="ignore",
                    drop=None,
                ),
                categorical,
            ),
            (
                "numeric",
                StandardScaler(),
                numeric,
            ),
        ]
    )

    model = Pipeline(
        steps=[
            ("prep", prep),
            (
                "regression",
                LinearRegression(),
            ),
        ]
    )

    return model


def metric_row(
    model_name,
    eval_scope,
    held_out_year,
    horizon,
    y_true,
    y_pred,
):

    error = y_pred - y_true

    return {
        "model": model_name,
        "eval_scope": eval_scope,
        "held_out_year": held_out_year,
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


def evaluate_predictions(
    pred_df,
):

    rows = []

    for (
        model_name,
        model_df,
    ) in pred_df.groupby("model"):

        # ---------------------------------------
        # Overall
        # ---------------------------------------

        rows.append(
            metric_row(
                model_name=model_name,
                eval_scope="overall",
                held_out_year="ALL",
                horizon="ALL",
                y_true=model_df[
                    "actual"
                ].to_numpy(),
                y_pred=model_df[
                    "predicted"
                ].to_numpy(),
            )
        )

        # ---------------------------------------
        # By held-out year
        # ---------------------------------------

        for (
            year,
            g,
        ) in model_df.groupby(
            "held_out_year"
        ):

            rows.append(
                metric_row(
                    model_name=model_name,
                    eval_scope="year",
                    held_out_year=year,
                    horizon="ALL",
                    y_true=g[
                        "actual"
                    ].to_numpy(),
                    y_pred=g[
                        "predicted"
                    ].to_numpy(),
                )
            )

        # ---------------------------------------
        # By horizon
        # ---------------------------------------

        for (
            horizon,
            g,
        ) in model_df.groupby(
            "requested_horizon_min"
        ):

            rows.append(
                metric_row(
                    model_name=model_name,
                    eval_scope="horizon",
                    held_out_year="ALL",
                    horizon=horizon,
                    y_true=g[
                        "actual"
                    ].to_numpy(),
                    y_pred=g[
                        "predicted"
                    ].to_numpy(),
                )
            )

        # ---------------------------------------
        # Year × horizon
        # ---------------------------------------

        for (
            year,
            horizon,
        ), g in model_df.groupby(
            [
                "held_out_year",
                "requested_horizon_min",
            ]
        ):

            rows.append(
                metric_row(
                    model_name=model_name,
                    eval_scope="year_horizon",
                    held_out_year=year,
                    horizon=horizon,
                    y_true=g[
                        "actual"
                    ].to_numpy(),
                    y_pred=g[
                        "predicted"
                    ].to_numpy(),
                )
            )

    return pd.DataFrame(rows)


def main():

    print("=" * 72)
    print(
        "INDY 500 V2-A FUTURE TRACK MODEL EVALUATION"
    )
    print("=" * 72)

    df = pd.read_csv(INPUT_FILE)

    print(
        f"\nInput rows: {len(df)}"
    )

    print(
        "Years:",
        sorted(df["year"].unique())
    )

    # ========================================================
    # COMMON SUBSET
    # ========================================================

    common = df[
        df[
            "track_rate_0_c_per_min"
        ].notna()
    ].copy()

    print(
        f"\nCommon subset rows: "
        f"{len(common)}"
    )

    print(
        f"Rows removed because current "
        f"thermal rate unavailable: "
        f"{len(df) - len(common)}"
    )

    print(
        "\nCommon subset by year / horizon:"
    )

    print(
        common.groupby(
            [
                "year",
                "requested_horizon_min",
            ]
        )
        .size()
        .unstack(
            fill_value=0
        )
    )

    # ========================================================
    # LOYO PREDICTIONS
    # ========================================================

    predictions = []

    years = sorted(
        common["year"].unique()
    )

    for test_year in years:

        train = common[
            common["year"]
            != test_year
        ].copy()

        test = common[
            common["year"]
            == test_year
        ].copy()

        print(
            f"\nHeld out {test_year}: "
            f"train={len(train)}, "
            f"test={len(test)}"
        )

        # ----------------------------------------------------
        # B0: persistence
        # ----------------------------------------------------

        pred = np.zeros(
            len(test)
        )

        for row_idx, (
            source_idx,
            row,
        ) in enumerate(test.iterrows()):

            predictions.append(
                {
                    "pair_id":
                        row["pair_id"],

                    "held_out_year":
                        test_year,

                    "requested_horizon_min":
                        row[
                            "requested_horizon_min"
                        ],

                    "model":
                        "B0_persistence",

                    "actual":
                        row[TARGET],

                    "predicted":
                        pred[row_idx],
                }
            )

        # ----------------------------------------------------
        # B1: track follows ambient 1:1
        # ----------------------------------------------------

        pred = test[
            "delta_ambient_temp_c"
        ].to_numpy()

        for row_idx, (
            source_idx,
            row,
        ) in enumerate(test.iterrows()):

            predictions.append(
                {
                    "pair_id":
                        row["pair_id"],

                    "held_out_year":
                        test_year,

                    "requested_horizon_min":
                        row[
                            "requested_horizon_min"
                        ],

                    "model":
                        "B1_ambient_1to1",

                    "actual":
                        row[TARGET],

                    "predicted":
                        pred[row_idx],
                }
            )

        # ----------------------------------------------------
        # Learned models
        # ----------------------------------------------------

        for (
            model_name,
            feature_cols,
        ) in MODELS.items():

            model = build_model(
                feature_cols
            )

            model.fit(
                train[
                    feature_cols
                ],
                train[TARGET],
            )

            pred = model.predict(
                test[
                    feature_cols
                ]
            )

            for row_idx, (
                source_idx,
                row,
            ) in enumerate(
                test.iterrows()
            ):

                predictions.append(
                    {
                        "pair_id":
                            row["pair_id"],

                        "held_out_year":
                            test_year,

                        "requested_horizon_min":
                            row[
                                "requested_horizon_min"
                            ],

                        "model":
                            model_name,

                        "actual":
                            row[TARGET],

                        "predicted":
                            pred[
                                row_idx
                            ],
                    }
                )

    predictions_df = pd.DataFrame(
        predictions
    )

    metrics_df = evaluate_predictions(
        predictions_df
    )

    # ========================================================
    # MACRO YEAR METRICS
    # ========================================================

    year_metrics = metrics_df[
        metrics_df[
            "eval_scope"
        ]
        == "year"
    ].copy()

    macro_rows = []

    for (
        model_name,
        g,
    ) in year_metrics.groupby(
        "model"
    ):

        macro_rows.append(
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

    macro_df = pd.DataFrame(
        macro_rows
    ).sort_values(
        "macro_year_mae_c"
    )

    # ========================================================
    # SAVE
    # ========================================================

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

    # ========================================================
    # PRINT SUMMARY
    # ========================================================

    lines = []

    def add(x=""):
        lines.append(str(x))

    add("=" * 72)
    add("COMMON-SUBSET LOYO MODEL COMPARISON")
    add("=" * 72)

    add()
    add(
        macro_df
        .round(4)
        .to_string(
            index=False
        )
    )

    add()
    add("=" * 72)
    add("OVERALL MICRO METRICS")
    add("=" * 72)

    overall = (
        metrics_df[
            metrics_df[
                "eval_scope"
            ]
            == "overall"
        ]
        [
            [
                "model",
                "n",
                "mae_c",
                "rmse_c",
                "bias_c",
                "median_abs_error_c",
            ]
        ]
        .sort_values(
            "mae_c"
        )
    )

    add()
    add(
        overall
        .round(4)
        .to_string(
            index=False
        )
    )

    add()
    add("=" * 72)
    add("MAE BY HORIZON")
    add("=" * 72)

    horizon_mae = (
        metrics_df[
            metrics_df[
                "eval_scope"
            ]
            == "horizon"
        ]
        .pivot(
            index="model",
            columns="horizon_min",
            values="mae_c",
        )
    )

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

    year_mae = (
        metrics_df[
            metrics_df[
                "eval_scope"
            ]
            == "year"
        ]
        .pivot(
            index="model",
            columns="held_out_year",
            values="mae_c",
        )
    )

    add()
    add(
        year_mae
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
        SUMMARY_FILE
    )

    print(
        "\nDONE"
    )


if __name__ == "__main__":
    main()
    