from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression

# ============================================================
# CONFIG
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

OUTDIR = Path(
    "weather/output/v2d_uncertainty_ablation"
)

OUTDIR.mkdir(
    parents=True,
    exist_ok=True,
)

DETAIL_FILE = (
    OUTDIR
    / "v2d_uncertainty_ablation_detail_v1.csv"
)

SUMMARY_FILE = (
    OUTDIR
    / "v2d_uncertainty_ablation_summary_v1.csv"
)

REDUCTION_FILE = (
    OUTDIR
    / "v2d_uncertainty_ablation_width_reduction_v1.csv"
)

TXT_FILE = (
    OUTDIR
    / "v2d_uncertainty_ablation_summary_v1.txt"
)

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

N_MC = 20000
RANDOM_SEED = 20260914

VARIANTS = {
    "FULL": {
        "track": True,
        "coef": True,
        "resid": True,
    },

    "TRACK_ONLY": {
        "track": True,
        "coef": False,
        "resid": False,
    },

    "COEFFICIENT_ONLY": {
        "track": False,
        "coef": True,
        "resid": False,
    },

    "RESIDUAL_ONLY": {
        "track": False,
        "coef": False,
        "resid": True,
    },

    "NO_TRACK": {
        "track": False,
        "coef": True,
        "resid": True,
    },

    "NO_COEFFICIENT": {
        "track": True,
        "coef": False,
        "resid": True,
    },

    "NO_RESIDUAL": {
        "track": True,
        "coef": True,
        "resid": False,
    },
}


# ============================================================
# HELPERS
# ============================================================

def symmetrized_draws_from_values(
    values,
    n,
    rng,
):
    values = np.asarray(
        values,
        dtype=float,
    )

    values = values[
        np.isfinite(values)
    ]

    if len(values) == 0:
        raise ValueError(
            "Empty residual pool"
        )

    magnitudes = np.abs(values)

    idx = rng.integers(
        0,
        len(magnitudes),
        size=n,
    )

    signs = rng.choice(
        np.array([-1.0, 1.0]),
        size=n,
    )

    return (
        magnitudes[idx]
        * signs
    )


def summarize_draws(draws):
    draws = np.asarray(
        draws,
        dtype=float,
    )

    q05, q10, q50, q90, q95 = (
        np.quantile(
            draws,
            [
                0.05,
                0.10,
                0.50,
                0.90,
                0.95,
            ],
        )
    )

    return {
        "mc_mean_mph":
            float(np.mean(draws)),

        "mc_median_mph":
            float(q50),

        "mc_sd_mph":
            float(
                np.std(
                    draws,
                    ddof=1,
                )
            ),

        "pi80_low_mph":
            float(q10),

        "pi80_high_mph":
            float(q90),

        "pi90_low_mph":
            float(q05),

        "pi90_high_mph":
            float(q95),

        "pi80_width_mph":
            float(q90 - q10),

        "pi90_width_mph":
            float(q95 - q05),
    }


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 90)
    print(
        "INDY 500 V2-D UNCERTAINTY-SOURCE ABLATION"
    )
    print("=" * 90)

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

    beta_track_mean = float(
        bootstrap_pairs[
            "beta_track_temp"
        ].mean()
    )

    beta_ambient_mean = float(
        bootstrap_pairs[
            "beta_ambient_temp"
        ].mean()
    )

    print()
    print(
        "Bootstrap rows:",
        len(bootstrap_pairs),
    )

    print(
        "Bootstrap correlation:",
        round(
            bootstrap_pairs.corr().iloc[0, 1],
            6,
        ),
    )

    print(
        "Mean beta_track:",
        beta_track_mean,
    )

    print(
        "Mean beta_ambient:",
        beta_ambient_mean,
    )

    # ========================================================
    # FULL-SAMPLE M2b TRACK MODELS
    # ========================================================

    track_models = {}

    for horizon in HORIZONS:

        d = samples[
            samples[
                "requested_horizon_min"
            ]
            == horizon
        ].dropna(
            subset=(
                TRACK_FEATURES
                + ["delta_track_temp_c"]
            )
        )

        model = LinearRegression()

        model.fit(
            d[TRACK_FEATURES],
            d["delta_track_temp_c"],
        )

        track_models[horizon] = model

    # ========================================================
    # HORIZON-SPECIFIC LOYO TRACK RESIDUAL POOLS
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
                f"No track residuals for horizon {horizon}"
            )

        track_resid_pools[
            horizon
        ] = vals

    # ========================================================
    # PERFORMANCE RESIDUAL POOL
    # ========================================================

    perf_resid_pool = (
        perf_resid[
            "residual_loyo_centered"
        ]
        .dropna()
        .to_numpy()
    )

    # ========================================================
    # ABLATION
    #
    # Important design:
    #
    # For every scenario we create ONE set of random latent
    # draws, then reuse those draws across all seven variants.
    #
    # This common-random-number design means differences
    # between variants reflect the uncertainty source being
    # switched on/off rather than unrelated Monte Carlo noise.
    # ========================================================

    output_rows = []

    valid_samples = samples.dropna(
        subset=(
            TRACK_FEATURES
            + [
                "delta_ambient_temp_c",
                "requested_horizon_min",
            ]
        )
    ).copy()

    for counter, (_, row) in enumerate(
        valid_samples.iterrows(),
        start=1,
    ):

        horizon = int(
            row[
                "requested_horizon_min"
            ]
        )

        if horizon not in track_models:
            continue

        # ----------------------------------------------------
        # Deterministic future-track point prediction
        # ----------------------------------------------------

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
            track_models[
                horizon
            ].predict(X)[0]
        )

        delta_ambient = float(
            row[
                "delta_ambient_temp_c"
            ]
        )

        # ----------------------------------------------------
        # Stable scenario-specific seed
        #
        # Allows reproducibility independent of dataframe
        # iteration implementation.
        # ----------------------------------------------------

        scenario_seed = (
            RANDOM_SEED
            + counter * 1009
            + horizon * 9176
        )

        rng = np.random.default_rng(
            scenario_seed
        )

        # ----------------------------------------------------
        # Generate the three stochastic sources ONCE.
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

        coef_idx = rng.integers(
            0,
            len(bootstrap_pairs),
            size=N_MC,
        )

        beta_track_draws = (
            bootstrap_pairs[
                "beta_track_temp"
            ]
            .to_numpy()[
                coef_idx
            ]
        )

        beta_ambient_draws = (
            bootstrap_pairs[
                "beta_ambient_temp"
            ]
            .to_numpy()[
                coef_idx
            ]
        )

        perf_noise = (
            symmetrized_draws_from_values(
                perf_resid_pool,
                N_MC,
                rng,
            )
        )

        # ----------------------------------------------------
        # Run all uncertainty variants using the SAME latent
        # draws.
        # ----------------------------------------------------

        for variant, switches in VARIANTS.items():

            if switches["track"]:

                delta_track_draws = (
                    point_delta_track
                    + track_noise
                )

            else:

                delta_track_draws = (
                    np.full(
                        N_MC,
                        point_delta_track,
                    )
                )

            if switches["coef"]:

                beta_track = (
                    beta_track_draws
                )

                beta_ambient = (
                    beta_ambient_draws
                )

            else:

                beta_track = (
                    np.full(
                        N_MC,
                        beta_track_mean,
                    )
                )

                beta_ambient = (
                    np.full(
                        N_MC,
                        beta_ambient_mean,
                    )
                )

            if switches["resid"]:

                residual_draws = (
                    perf_noise
                )

            else:

                residual_draws = (
                    np.zeros(
                        N_MC
                    )
                )

            delta_speed_draws = (
                beta_track
                * delta_track_draws
                +
                beta_ambient
                * delta_ambient
                +
                residual_draws
            )

            summary = summarize_draws(
                delta_speed_draws
            )

            output_rows.append(
                {
                    "pair_id":
                        row["pair_id"],

                    "year":
                        int(row["year"]),

                    "horizon_min":
                        horizon,

                    "variant":
                        variant,

                    "track_uncertainty_on":
                        switches["track"],

                    "coefficient_uncertainty_on":
                        switches["coef"],

                    "performance_residual_on":
                        switches["resid"],

                    "point_delta_track_c":
                        point_delta_track,

                    "delta_ambient_temp_c":
                        delta_ambient,

                    **summary,

                    "n_mc":
                        N_MC,
                }
            )

        if counter % 100 == 0:
            print(
                f"processed {counter} scenarios"
            )

    detail = pd.DataFrame(
        output_rows
    )

    detail.to_csv(
        DETAIL_FILE,
        index=False,
    )

    # ========================================================
    # HORIZON × VARIANT SUMMARY
    # ========================================================

    summary = (
        detail
        .groupby(
            [
                "horizon_min",
                "variant",
            ],
            as_index=False,
        )
        .agg(
            n_scenarios=(
                "pair_id",
                "size",
            ),

            mean_mc_sd_mph=(
                "mc_sd_mph",
                "mean",
            ),

            median_mc_sd_mph=(
                "mc_sd_mph",
                "median",
            ),

            mean_pi80_width_mph=(
                "pi80_width_mph",
                "mean",
            ),

            median_pi80_width_mph=(
                "pi80_width_mph",
                "median",
            ),

            mean_pi90_width_mph=(
                "pi90_width_mph",
                "mean",
            ),

            median_pi90_width_mph=(
                "pi90_width_mph",
                "median",
            ),
        )
    )

    summary.to_csv(
        SUMMARY_FILE,
        index=False,
    )

    # ========================================================
    # WIDTH REDUCTION RELATIVE TO FULL
    #
    # This is an ablation sensitivity measure.
    # It is NOT interpreted as an additive variance share.
    # ========================================================

    reduction_rows = []

    for horizon in HORIZONS:

        s = summary[
            summary[
                "horizon_min"
            ]
            == horizon
        ].copy()

        full = s[
            s["variant"]
            == "FULL"
        ]

        if len(full) != 1:
            raise ValueError(
                f"Missing FULL summary for {horizon}"
            )

        full = full.iloc[0]

        for _, r in s.iterrows():

            reduction_rows.append(
                {
                    "horizon_min":
                        horizon,

                    "variant":
                        r["variant"],

                    "mean_pi80_width_mph":
                        r[
                            "mean_pi80_width_mph"
                        ],

                    "mean_pi90_width_mph":
                        r[
                            "mean_pi90_width_mph"
                        ],

                    "pi80_width_reduction_vs_full":
                        (
                            1.0
                            -
                            r[
                                "mean_pi80_width_mph"
                            ]
                            /
                            full[
                                "mean_pi80_width_mph"
                            ]
                        ),

                    "pi90_width_reduction_vs_full":
                        (
                            1.0
                            -
                            r[
                                "mean_pi90_width_mph"
                            ]
                            /
                            full[
                                "mean_pi90_width_mph"
                            ]
                        ),
                }
            )

    reduction = pd.DataFrame(
        reduction_rows
    )

    reduction.to_csv(
        REDUCTION_FILE,
        index=False,
    )

    # ========================================================
    # TEXT REPORT
    # ========================================================

    lines = []

    def add(x=""):
        lines.append(str(x))

    add("=" * 100)
    add(
        "INDY 500 V2-D UNCERTAINTY-SOURCE ABLATION"
    )
    add("=" * 100)

    add()
    add("PURPOSE")
    add("-" * 100)
    add(
        "Quantify how final predictive spread changes when "
        "future-track uncertainty, paired coefficient uncertainty, "
        "and empirical performance-residual uncertainty are "
        "individually enabled or removed."
    )

    add()
    add(
        "This is an uncertainty-source ablation / sensitivity "
        "analysis, NOT a strict additive variance decomposition."
    )

    add()
    add("VARIANTS")
    add("-" * 100)

    for variant, switches in VARIANTS.items():

        add(
            f"{variant:18s} "
            f"track={switches['track']}  "
            f"coef={switches['coef']}  "
            f"residual={switches['resid']}"
        )

    add()
    add("MEAN INTERVAL WIDTHS")
    add("-" * 100)

    display = summary[
        [
            "horizon_min",
            "variant",
            "n_scenarios",
            "mean_mc_sd_mph",
            "mean_pi80_width_mph",
            "mean_pi90_width_mph",
        ]
    ].copy()

    add(
        display
        .round(6)
        .to_string(index=False)
    )

    add()
    add("WIDTH REDUCTION RELATIVE TO FULL")
    add("-" * 100)

    display_red = reduction[
        [
            "horizon_min",
            "variant",
            "pi80_width_reduction_vs_full",
            "pi90_width_reduction_vs_full",
        ]
    ].copy()

    add(
        display_red
        .round(6)
        .to_string(index=False)
    )

    add()
    add("INTERPRETATION RULE")
    add("-" * 100)

    add(
        "A larger positive width reduction after removing a "
        "source indicates that the source materially contributes "
        "to final predictive spread under this ablation design."
    )

    add(
        "Because quantile widths are nonlinear and uncertainty "
        "sources interact, reductions must NOT be interpreted as "
        "additive percentages summing to 100%."
    )

    add()
    add(
        "Single-source variants describe the predictive spread "
        "generated when only that uncertainty source is active."
    )

    text = "\n".join(
        lines
    )

    TXT_FILE.write_text(
        text + "\n",
        encoding="utf-8",
    )

    print()
    print(text)

    print()
    print("=" * 100)
    print("OUTPUTS")
    print("=" * 100)

    for p in [
        DETAIL_FILE,
        SUMMARY_FILE,
        REDUCTION_FILE,
        TXT_FILE,
    ]:
        print(p)

    print()
    print("DONE")


if __name__ == "__main__":
    main()
