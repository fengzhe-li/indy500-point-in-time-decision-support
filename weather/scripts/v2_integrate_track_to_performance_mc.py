from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression


# ============================================================
# FILES
# ============================================================

SAMPLE_FILE = Path(
    "weather/output/v2_future_track/"
    "future_track_samples_with_solar_v1.csv"
)

TRACK_RESID_FILE = Path(
    "weather/output/v2_future_track/"
    "future_track_residuals_v1.csv"
)

PERF_BOOT_FILE = Path(
    "r5_2/manual/"
    "probabilistic_physics_coefficient_bootstrap_v1.csv"
)

PERF_RESID_FILE = Path(
    "r5_2/manual/"
    "probabilistic_physics_loyo_residuals_v1.csv"
)

OUTPUT_DIR = Path(
    "weather/output/v2_future_track"
)

RESULT_FILE = (
    OUTPUT_DIR
    / "v2a_performance_mc_integration_v1.csv"
)

TRACK_COEF_FILE = (
    OUTPUT_DIR
    / "v2a_full_sample_track_model_coefficients_v1.csv"
)

QA_FILE = (
    OUTPUT_DIR
    / "v2a_performance_mc_integration_v1_qa.txt"
)


# ============================================================
# SETTINGS
# ============================================================

RANDOM_SEED = 20260914

N_MC = 20000

TRACK_MODEL = "M2b_mean_solar"

TRACK_FEATURES = [
    "delta_ambient_temp_c",
    "thermal_gap_0_c",
    "solar_elevation_mean_deg",
]

HORIZONS = [
    15,
    30,
    60,
    90,
    120,
]


# ============================================================
# HELPERS
# ============================================================

def symmetrized_draws_from_values(
    values,
    n,
    rng,
):
    """
    Draw magnitudes from empirical values,
    then assign random +/- sign.

    This enforces zero directional effect
    while retaining empirical residual magnitude.
    """

    values = np.asarray(
        values,
        dtype=float,
    )

    values = values[
        np.isfinite(values)
    ]

    magnitudes = np.abs(values)

    sampled_mag = rng.choice(
        magnitudes,
        size=n,
        replace=True,
    )

    signs = rng.choice(
        np.array([-1.0, 1.0]),
        size=n,
        replace=True,
    )

    return sampled_mag * signs


def summarize_draws(draws):

    return {
        "expected_delta_speed_mph":
            float(np.mean(draws)),

        "median_delta_speed_mph":
            float(np.median(draws)),

        "lower_80_mph":
            float(np.quantile(draws, 0.10)),

        "upper_80_mph":
            float(np.quantile(draws, 0.90)),

        "lower_90_mph":
            float(np.quantile(draws, 0.05)),

        "upper_90_mph":
            float(np.quantile(draws, 0.95)),

        "p_improve":
            float(np.mean(draws > 0.0)),

        "mc_sd_mph":
            float(np.std(draws, ddof=1)),
    }


# ============================================================
# LOAD
# ============================================================

def main():

    print("=" * 80)
    print(
        "INDY 500 V2-A FUTURE TRACK -> PERFORMANCE MONTE CARLO"
    )
    print("=" * 80)

    rng = np.random.default_rng(
        RANDOM_SEED
    )

    samples = pd.read_csv(
        SAMPLE_FILE
    )

    track_resid = pd.read_csv(
        TRACK_RESID_FILE
    )

    perf_boot = pd.read_csv(
        PERF_BOOT_FILE
    )

    perf_resid = pd.read_csv(
        PERF_RESID_FILE
    )

    print()
    print("INPUT")
    print(
        f"future-track scenarios: {len(samples)}"
    )
    print(
        f"track residual rows: {len(track_resid)}"
    )
    print(
        f"performance bootstrap rows: {len(perf_boot)}"
    )
    print(
        f"performance residual rows: {len(perf_resid)}"
    )

    # ========================================================
    # SAFETY CHECKS
    # ========================================================

    required_sample_cols = (
        TRACK_FEATURES
        + [
            "pair_id",
            "year",
            "requested_horizon_min",
            "delta_track_temp_c",
            "delta_ambient_temp_c",
        ]
    )

    missing = [
        c
        for c in required_sample_cols
        if c not in samples.columns
    ]

    if missing:
        raise ValueError(
            f"Missing sample columns: {missing}"
        )

    for col in [
        "beta_track_temp",
        "beta_ambient_temp",
    ]:
        if col not in perf_boot.columns:
            raise ValueError(
                f"Missing bootstrap column: {col}"
            )

    if (
        "residual_loyo_centered"
        not in perf_resid.columns
    ):
        raise ValueError(
            "Missing residual_loyo_centered"
        )

    # ========================================================
    # IMPORTANT:
    # coefficient pairs stay paired.
    # Do NOT sample beta_track and beta_ambient separately.
    # ========================================================

    bootstrap_pairs = (
        perf_boot[
            [
                "beta_track_temp",
                "beta_ambient_temp",
            ]
        ]
        .dropna()
        .reset_index(drop=True)
    )

    print()
    print(
        "Performance bootstrap correlation:"
    )
    print(
        bootstrap_pairs.corr().round(4)
    )

    # ========================================================
    # BUILD FULL-SAMPLE M2b TRACK MODELS
    #
    # Validation already happened using LOYO.
    # This is production-style refit after model choice.
    # One model per horizon.
    # ========================================================

    track_models = {}
    coef_rows = []

    for horizon in HORIZONS:

        d = samples[
            samples[
                "requested_horizon_min"
            ]
            == horizon
        ].dropna(
            subset=TRACK_FEATURES
            + ["delta_track_temp_c"]
        )

        model = LinearRegression()

        model.fit(
            d[TRACK_FEATURES],
            d["delta_track_temp_c"],
        )

        track_models[
            horizon
        ] = model

        row = {
            "horizon_min":
                horizon,

            "n":
                len(d),

            "intercept_c":
                float(
                    model.intercept_
                ),
        }

        for feature, coef in zip(
            TRACK_FEATURES,
            model.coef_,
        ):
            row[
                f"beta_{feature}"
            ] = float(coef)

        coef_rows.append(row)

    coef_df = pd.DataFrame(
        coef_rows
    )

    coef_df.to_csv(
        TRACK_COEF_FILE,
        index=False,
    )

    print()
    print("=" * 80)
    print(
        "FULL-SAMPLE M2b TRACK MODEL"
    )
    print("=" * 80)
    print()
    print(
        coef_df
        .round(6)
        .to_string(index=False)
    )

    # ========================================================
    # TRACK RESIDUAL POOLS
    #
    # IMPORTANT:
    # use LOYO residuals, not in-sample residuals.
    #
    # Residual definition in file:
    # actual - predicted
    #
    # Symmetrize magnitude to keep physical
    # point model direction-neutral.
    # ========================================================

    tr = track_resid[
        track_resid["model"]
        == TRACK_MODEL
    ].copy()

    track_resid_pools = {}

    for horizon in HORIZONS:

        vals = tr.loc[
            tr["horizon_min"]
            == horizon,
            "residual_c",
        ].dropna().to_numpy()

        if len(vals) == 0:
            raise ValueError(
                f"No track residuals for {horizon} min"
            )

        track_resid_pools[
            horizon
        ] = vals

    # ========================================================
    # PERFORMANCE RESIDUAL POOL
    #
    # residual_loyo_centered has median zero,
    # but empirical mean is not zero.
    #
    # Therefore sample |residual|,
    # then random +/- sign.
    # ========================================================

    perf_resid_pool = (
        perf_resid[
            "residual_loyo_centered"
        ]
        .dropna()
        .to_numpy()
    )

    # ========================================================
    # MONTE CARLO
    # ========================================================

    output_rows = []

    for idx, row in samples.iterrows():

        horizon = int(
            row[
                "requested_horizon_min"
            ]
        )

        if horizon not in track_models:
            continue

        model = track_models[
            horizon
        ]

        X = pd.DataFrame(
            [
                {
                    feature:
                        row[feature]
                    for feature
                    in TRACK_FEATURES
                }
            ]
        )

        point_delta_track = float(
            model.predict(X)[0]
        )

        # ----------------------------------------------------
        # Future-track uncertainty
        # ----------------------------------------------------

        track_noise = (
            symmetrized_draws_from_values(
                track_resid_pools[
                    horizon
                ],
                N_MC,
                rng,
            )
        )

        delta_track_draws = (
            point_delta_track
            + track_noise
        )

        # ----------------------------------------------------
        # Bootstrap coefficient uncertainty
        #
        # Draw ROWS so correlation between coefficients
        # is preserved.
        # ----------------------------------------------------

        coef_idx = rng.integers(
            0,
            len(bootstrap_pairs),
            size=N_MC,
        )

        beta_track = (
            bootstrap_pairs[
                "beta_track_temp"
            ]
            .to_numpy()[
                coef_idx
            ]
        )

        beta_ambient = (
            bootstrap_pairs[
                "beta_ambient_temp"
            ]
            .to_numpy()[
                coef_idx
            ]
        )

        # ----------------------------------------------------
        # Performance residual uncertainty
        # ----------------------------------------------------

        perf_noise = (
            symmetrized_draws_from_values(
                perf_resid_pool,
                N_MC,
                rng,
            )
        )

        delta_ambient = float(
            row[
                "delta_ambient_temp_c"
            ]
        )

        # ----------------------------------------------------
        # Final physical performance draw
        #
        # Δv =
        # beta_track * ΔTtrack
        # + beta_ambient * ΔTambient
        # + empirical residual
        # ----------------------------------------------------

        delta_speed_draws = (
            beta_track
            * delta_track_draws
            +
            beta_ambient
            * delta_ambient
            +
            perf_noise
        )

        summary = summarize_draws(
            delta_speed_draws
        )

        # deterministic point using bootstrap means
        deterministic_physical = (
            bootstrap_pairs[
                "beta_track_temp"
            ].mean()
            * point_delta_track
            +
            bootstrap_pairs[
                "beta_ambient_temp"
            ].mean()
            * delta_ambient
        )

        output_rows.append(
            {
                "pair_id":
                    row["pair_id"],

                "year":
                    int(row["year"]),

                "horizon_min":
                    horizon,

                "current_track_temp_c":
                    row[
                        "track_temp_0_c"
                    ],

                "current_ambient_temp_c":
                    row[
                        "ambient_temp_0_c"
                    ],

                "thermal_gap_0_c":
                    row[
                        "thermal_gap_0_c"
                    ],

                "delta_ambient_temp_c":
                    delta_ambient,

                "solar_elevation_mean_deg":
                    row[
                        "solar_elevation_mean_deg"
                    ],

                "actual_delta_track_temp_c":
                    row[
                        "delta_track_temp_c"
                    ],

                "model_expected_delta_track_temp_c":
                    point_delta_track,

                "deterministic_physical_delta_speed_mph":
                    deterministic_physical,

                **summary,

                "n_mc":
                    N_MC,

                "track_model":
                    TRACK_MODEL,

                "track_uncertainty":
                    (
                        "horizon_specific_"
                        "symmetrized_LOYO_residual"
                    ),

                "coefficient_uncertainty":
                    (
                        "paired_bootstrap_draw"
                    ),

                "performance_uncertainty":
                    (
                        "symmetrized_centered_"
                        "LOYO_residual"
                    ),

                "ambient_input_semantic":
                    (
                        "realized_future_ambient_"
                        "conditional_replay"
                    ),
            }
        )

        if (
            (idx + 1) % 100
            == 0
        ):
            print(
                f"Processed {idx + 1}"
                f"/{len(samples)} scenarios"
            )

    out = pd.DataFrame(
        output_rows
    )

    out.to_csv(
        RESULT_FILE,
        index=False,
    )

    # ========================================================
    # QA
    # ========================================================

    lines = []

    def add(x=""):
        lines.append(str(x))

    add("=" * 80)
    add(
        "INDY 500 V2-A PERFORMANCE MC INTEGRATION QA"
    )
    add("=" * 80)

    add()
    add("ROWS")
    add(len(out))

    add()
    add("=" * 80)
    add("PERFORMANCE BOOTSTRAP")
    add("=" * 80)

    add()
    add(
        f"draw rows available: "
        f"{len(bootstrap_pairs)}"
    )

    add(
        "beta correlation: "
        f"{bootstrap_pairs.corr().iloc[0,1]:.6f}"
    )

    add()
    add("=" * 80)
    add("PERFORMANCE RESIDUAL")
    add("=" * 80)

    add()
    add(
        f"source residual n: "
        f"{len(perf_resid_pool)}"
    )

    add(
        f"source residual mean: "
        f"{np.mean(perf_resid_pool):.6f}"
    )

    add(
        f"source residual median: "
        f"{np.median(perf_resid_pool):.6f}"
    )

    add(
        "MC treatment: "
        "sample absolute magnitude + random sign"
    )

    add()
    add("=" * 80)
    add("TRACK POINT ERROR BY HORIZON")
    add("=" * 80)

    out[
        "track_point_error_c"
    ] = (
        out[
            "actual_delta_track_temp_c"
        ]
        -
        out[
            "model_expected_delta_track_temp_c"
        ]
    )

    track_summary = (
        out.groupby(
            "horizon_min"
        )
        .agg(
            n=(
                "pair_id",
                "size",
            ),

            track_mae_c=(
                "track_point_error_c",
                lambda s:
                    np.mean(
                        np.abs(s)
                    ),
            ),

            track_bias_c=(
                "track_point_error_c",
                "mean",
            ),
        )
    )

    add()
    add(
        track_summary
        .round(4)
        .to_string()
    )

    add()
    add("=" * 80)
    add("PERFORMANCE OUTLOOK BY HORIZON")
    add("=" * 80)

    perf_summary = (
        out.groupby(
            "horizon_min"
        )
        .agg(
            n=(
                "pair_id",
                "size",
            ),

            mean_expected_delta_speed_mph=(
                "expected_delta_speed_mph",
                "mean",
            ),

            mean_p_improve=(
                "p_improve",
                "mean",
            ),

            mean_pi80_width_mph=(
                "upper_80_mph",
                lambda x:
                    np.nan,
            ),
        )
    )

    # calculate interval widths explicitly
    width_summary = (
        out.assign(
            width80=(
                out["upper_80_mph"]
                - out["lower_80_mph"]
            ),
            width90=(
                out["upper_90_mph"]
                - out["lower_90_mph"]
            ),
        )
        .groupby(
            "horizon_min"
        )
        .agg(
            mean_width80_mph=(
                "width80",
                "mean",
            ),
            mean_width90_mph=(
                "width90",
                "mean",
            ),
            mean_mc_sd_mph=(
                "mc_sd_mph",
                "mean",
            ),
        )
    )

    perf_summary = (
        perf_summary
        .drop(
            columns=[
                "mean_pi80_width_mph"
            ]
        )
        .join(
            width_summary
        )
    )

    add()
    add(
        perf_summary
        .round(4)
        .to_string()
    )

    add()
    add("=" * 80)
    add("P(IMPROVE) DISTRIBUTION")
    add("=" * 80)

    add()
    add(
        out["p_improve"]
        .describe(
            percentiles=[
                .05,
                .10,
                .25,
                .50,
                .75,
                .90,
                .95,
            ]
        )
        .round(4)
        .to_string()
    )

    add()
    add("=" * 80)
    add("EXPECTED DELTA SPEED DISTRIBUTION")
    add("=" * 80)

    add()
    add(
        out[
            "expected_delta_speed_mph"
        ]
        .describe(
            percentiles=[
                .05,
                .10,
                .25,
                .50,
                .75,
                .90,
                .95,
            ]
        )
        .round(4)
        .to_string()
    )

    add()
    add("=" * 80)
    add("EXTREME POSITIVE OUTLOOKS")
    add("=" * 80)

    cols = [
        "year",
        "horizon_min",
        "delta_ambient_temp_c",
        "model_expected_delta_track_temp_c",
        "expected_delta_speed_mph",
        "p_improve",
        "lower_80_mph",
        "upper_80_mph",
    ]

    add()
    add(
        out.nlargest(
            10,
            "expected_delta_speed_mph",
        )[cols]
        .round(4)
        .to_string(
            index=False
        )
    )

    add()
    add("=" * 80)
    add("EXTREME NEGATIVE OUTLOOKS")
    add("=" * 80)

    add()
    add(
        out.nsmallest(
            10,
            "expected_delta_speed_mph",
        )[cols]
        .round(4)
        .to_string(
            index=False
        )
    )

    add()
    add("=" * 80)
    add("SEMANTIC WARNING")
    add("=" * 80)

    add()
    add(
        "This integration uses REALIZED future ambient "
        "temperature change from historical PTSC pairs."
    )

    add(
        "Therefore this is conditional physical-state "
        "integration QA, NOT an end-to-end operational "
        "weather forecast evaluation."
    )

    add(
        "Operational inference must replace "
        "delta_ambient_temp_c with a future ambient "
        "forecast or explicit ambient scenario."
    )

    summary = "\n".join(
        lines
    )

    QA_FILE.write_text(
        summary,
        encoding="utf-8",
    )

    print()
    print(summary)

    print()
    print("=" * 80)
    print("OUTPUT")
    print("=" * 80)

    print(RESULT_FILE)
    print(TRACK_COEF_FILE)
    print(QA_FILE)

    print()
    print("DONE")


if __name__ == "__main__":
    main()
