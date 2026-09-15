from pathlib import Path

import numpy as np
import pandas as pd


INPUT_FILE = Path(
    "weather/output/v2_future_track/"
    "solar_model_predictions_v1.csv"
)

OUTPUT_DIR = Path(
    "weather/output/v2_future_track"
)

OUTPUT_FILE = (
    OUTPUT_DIR
    / "future_track_interval_calibration_v1.csv"
)

SUMMARY_FILE = (
    OUTPUT_DIR
    / "future_track_interval_calibration_v1.txt"
)


MODELS = [
    "M1_no_solar",
    "M2b_mean_solar",
]


def interval_metrics(g):

    actual = g["actual"].to_numpy()

    covered80 = (
        (actual >= g["lower80"])
        &
        (actual <= g["upper80"])
    )

    covered90 = (
        (actual >= g["lower90"])
        &
        (actual <= g["upper90"])
    )

    return pd.Series(
        {
            "n": len(g),

            "coverage80":
                covered80.mean(),

            "coverage90":
                covered90.mean(),

            "mean_width80_c":
                (
                    g["upper80"]
                    - g["lower80"]
                ).mean(),

            "mean_width90_c":
                (
                    g["upper90"]
                    - g["lower90"]
                ).mean(),

            "mae_c":
                np.mean(
                    np.abs(
                        g["actual"]
                        - g["predicted"]
                    )
                ),
        }
    )


def main():

    print("=" * 72)
    print(
        "INDY 500 V2-A FUTURE TRACK INTERVAL CALIBRATION"
    )
    print("=" * 72)

    df = pd.read_csv(INPUT_FILE)

    df = df[
        df["model"].isin(MODELS)
    ].copy()

    df["residual"] = (
        df["actual"]
        - df["predicted"]
    )

    calibrated = []

    years = sorted(
        df["held_out_year"].unique()
    )

    for model_name in MODELS:

        model_df = df[
            df["model"] == model_name
        ].copy()

        for test_year in years:

            test_year_df = model_df[
                model_df["held_out_year"]
                == test_year
            ].copy()

            # ============================================
            # Two calibration strategies:
            #
            # 1. pooled:
            #    one residual distribution for all horizons
            #
            # 2. horizon:
            #    separate residual distribution by horizon
            # ============================================

            for mode in [
                "pooled",
                "horizon_specific",
            ]:

                for _, row in (
                    test_year_df.iterrows()
                ):

                    if mode == "pooled":

                        calibration = model_df[
                            model_df[
                                "held_out_year"
                            ]
                            != test_year
                        ]

                    else:

                        calibration = model_df[
                            (
                                model_df[
                                    "held_out_year"
                                ]
                                != test_year
                            )
                            &
                            (
                                model_df[
                                    "horizon_min"
                                ]
                                == row[
                                    "horizon_min"
                                ]
                            )
                        ]

                    residuals = calibration[
                        "residual"
                    ].to_numpy()

                    q05 = np.quantile(
                        residuals,
                        0.05,
                    )

                    q10 = np.quantile(
                        residuals,
                        0.10,
                    )

                    q90 = np.quantile(
                        residuals,
                        0.90,
                    )

                    q95 = np.quantile(
                        residuals,
                        0.95,
                    )

                    calibrated.append(
                        {
                            "pair_id":
                                row["pair_id"],

                            "model":
                                model_name,

                            "calibration":
                                mode,

                            "held_out_year":
                                test_year,

                            "horizon_min":
                                row["horizon_min"],

                            "actual":
                                row["actual"],

                            "predicted":
                                row["predicted"],

                            "lower80":
                                row["predicted"]
                                + q10,

                            "upper80":
                                row["predicted"]
                                + q90,

                            "lower90":
                                row["predicted"]
                                + q05,

                            "upper90":
                                row["predicted"]
                                + q95,

                            "calibration_n":
                                len(residuals),
                        }
                    )

    out = pd.DataFrame(
        calibrated
    )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    out.to_csv(
        OUTPUT_FILE,
        index=False,
    )

    # ==============================================
    # Overall metrics
    # ==============================================

    overall = (
        out.groupby(
            [
                "model",
                "calibration",
            ]
        )
        .apply(
            interval_metrics,
            include_groups=False,
        )
    )

    # ==============================================
    # Horizon metrics
    # ==============================================

    by_horizon = (
        out.groupby(
            [
                "model",
                "calibration",
                "horizon_min",
            ]
        )
        .apply(
            interval_metrics,
            include_groups=False,
        )
    )

    # ==============================================
    # Year metrics
    # ==============================================

    by_year = (
        out.groupby(
            [
                "model",
                "calibration",
                "held_out_year",
            ]
        )
        .apply(
            interval_metrics,
            include_groups=False,
        )
    )

    lines = []

    def add(x=""):
        lines.append(str(x))

    add("=" * 72)
    add("OVERALL COVERAGE")
    add("=" * 72)
    add()
    add(
        overall
        .round(4)
        .to_string()
    )

    add()
    add("=" * 72)
    add("80% COVERAGE BY HORIZON")
    add("=" * 72)

    table80 = (
        by_horizon[
            "coverage80"
        ]
        .unstack(
            "horizon_min"
        )
    )

    add()
    add(
        table80
        .round(4)
        .to_string()
    )

    add()
    add("=" * 72)
    add("90% COVERAGE BY HORIZON")
    add("=" * 72)

    table90 = (
        by_horizon[
            "coverage90"
        ]
        .unstack(
            "horizon_min"
        )
    )

    add()
    add(
        table90
        .round(4)
        .to_string()
    )

    add()
    add("=" * 72)
    add("80% INTERVAL WIDTH BY HORIZON")
    add("=" * 72)

    width80 = (
        by_horizon[
            "mean_width80_c"
        ]
        .unstack(
            "horizon_min"
        )
    )

    add()
    add(
        width80
        .round(4)
        .to_string()
    )

    add()
    add("=" * 72)
    add("90% INTERVAL WIDTH BY HORIZON")
    add("=" * 72)

    width90 = (
        by_horizon[
            "mean_width90_c"
        ]
        .unstack(
            "horizon_min"
        )
    )

    add()
    add(
        width90
        .round(4)
        .to_string()
    )

    add()
    add("=" * 72)
    add("80% COVERAGE BY YEAR")
    add("=" * 72)

    year80 = (
        by_year[
            "coverage80"
        ]
        .unstack(
            "held_out_year"
        )
    )

    add()
    add(
        year80
        .round(4)
        .to_string()
    )

    add()
    add("=" * 72)
    add("90% COVERAGE BY YEAR")
    add("=" * 72)

    year90 = (
        by_year[
            "coverage90"
        ]
        .unstack(
            "held_out_year"
        )
    )

    add()
    add(
        year90
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
    print("OUTPUT")
    print(OUTPUT_FILE)
    print(SUMMARY_FILE)

    print()
    print("DONE")


if __name__ == "__main__":
    main()
