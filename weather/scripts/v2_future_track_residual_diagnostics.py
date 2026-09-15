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

SUMMARY_FILE = (
    OUTPUT_DIR
    / "future_track_residual_diagnostics_v1.txt"
)

RESIDUAL_FILE = (
    OUTPUT_DIR
    / "future_track_residuals_v1.csv"
)


KEEP_MODELS = [
    "M1_no_solar",
    "M2b_mean_solar",
]


def main():

    print("=" * 72)
    print("INDY 500 V2-A FUTURE TRACK RESIDUAL DIAGNOSTICS")
    print("=" * 72)

    df = pd.read_csv(INPUT_FILE)

    df = df[
        df["model"].isin(KEEP_MODELS)
    ].copy()

    df["residual_c"] = (
        df["actual"]
        - df["predicted"]
    )

    df["abs_residual_c"] = (
        df["residual_c"].abs()
    )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    df.to_csv(
        RESIDUAL_FILE,
        index=False,
    )

    lines = []

    def add(x=""):
        lines.append(str(x))

    add("=" * 72)
    add("OVERALL RESIDUAL SUMMARY")
    add("=" * 72)

    overall = (
        df.groupby("model")
        .agg(
            n=("residual_c", "size"),
            mean_residual_c=("residual_c", "mean"),
            std_residual_c=("residual_c", "std"),
            mae_c=("abs_residual_c", "mean"),
            median_abs_residual_c=("abs_residual_c", "median"),
            p80_abs_residual_c=(
                "abs_residual_c",
                lambda s: np.quantile(s, 0.80)
            ),
            p90_abs_residual_c=(
                "abs_residual_c",
                lambda s: np.quantile(s, 0.90)
            ),
            p95_abs_residual_c=(
                "abs_residual_c",
                lambda s: np.quantile(s, 0.95)
            ),
        )
    )

    add()
    add(overall.round(4).to_string())

    add()
    add("=" * 72)
    add("RESIDUAL SPREAD BY HORIZON")
    add("=" * 72)

    by_horizon = (
        df.groupby(
            [
                "model",
                "horizon_min",
            ]
        )
        .agg(
            n=("residual_c", "size"),
            bias_c=("residual_c", "mean"),
            std_c=("residual_c", "std"),
            mae_c=("abs_residual_c", "mean"),
            p80_abs_c=(
                "abs_residual_c",
                lambda s: np.quantile(s, 0.80)
            ),
            p90_abs_c=(
                "abs_residual_c",
                lambda s: np.quantile(s, 0.90)
            ),
        )
    )

    add()
    add(by_horizon.round(4).to_string())

    add()
    add("=" * 72)
    add("MAE BY YEAR")
    add("=" * 72)

    year_mae = (
        df.groupby(
            [
                "model",
                "held_out_year",
            ]
        )["abs_residual_c"]
        .mean()
        .unstack()
    )

    add()
    add(year_mae.round(4).to_string())

    add()
    add("=" * 72)
    add("RESIDUAL STD BY YEAR")
    add("=" * 72)

    year_std = (
        df.groupby(
            [
                "model",
                "held_out_year",
            ]
        )["residual_c"]
        .std()
        .unstack()
    )

    add()
    add(year_std.round(4).to_string())

    add()
    add("=" * 72)
    add("M2b: YEAR × HORIZON MAE")
    add("=" * 72)

    m2 = df[
        df["model"]
        == "M2b_mean_solar"
    ]

    m2_yh = (
        m2.groupby(
            [
                "held_out_year",
                "horizon_min",
            ]
        )["abs_residual_c"]
        .mean()
        .unstack()
    )

    add()
    add(m2_yh.round(4).to_string())

    add()
    add("=" * 72)
    add("M2b: HORIZON-SPECIFIC EMPIRICAL ERROR QUANTILES")
    add("=" * 72)

    qrows = []

    for horizon, g in m2.groupby(
        "horizon_min"
    ):

        residual = g[
            "residual_c"
        ].to_numpy()

        abs_res = np.abs(
            residual
        )

        qrows.append(
            {
                "horizon_min":
                    horizon,

                "n":
                    len(g),

                "residual_q05":
                    np.quantile(
                        residual,
                        0.05,
                    ),

                "residual_q10":
                    np.quantile(
                        residual,
                        0.10,
                    ),

                "residual_q50":
                    np.quantile(
                        residual,
                        0.50,
                    ),

                "residual_q90":
                    np.quantile(
                        residual,
                        0.90,
                    ),

                "residual_q95":
                    np.quantile(
                        residual,
                        0.95,
                    ),

                "abs_q80":
                    np.quantile(
                        abs_res,
                        0.80,
                    ),

                "abs_q90":
                    np.quantile(
                        abs_res,
                        0.90,
                    ),
            }
        )

    quantiles = pd.DataFrame(
        qrows
    ).set_index(
        "horizon_min"
    )

    add()
    add(
        quantiles
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
    print(RESIDUAL_FILE)
    print(SUMMARY_FILE)
    print()
    print("DONE")


if __name__ == "__main__":
    main()
