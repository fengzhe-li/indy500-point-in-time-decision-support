from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression

# ============================================================
# FILES / CONFIG
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
    "weather/output/v2e_scenario_stress_test"
)

OUTDIR.mkdir(
    parents=True,
    exist_ok=True,
)

SCENARIO_FILE = (
    OUTDIR
    / "v2e_scenario_grid_v1.csv"
)

RESULT_FILE = (
    OUTDIR
    / "v2e_scenario_stress_test_results_v1.csv"
)

PROFILE_FILE = (
    OUTDIR
    / "v2e_scenario_horizon_profiles_v1.csv"
)

SUMMARY_FILE = (
    OUTDIR
    / "v2e_scenario_stress_test_summary_v1.txt"
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

N_MC = 50000

RANDOM_SEED = 20260914


# ============================================================
# HELPERS
# ============================================================

def symmetrized_draws(
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

    magnitudes = np.abs(
        values
    )

    sampled = rng.choice(
        magnitudes,
        size=n,
        replace=True,
    )

    signs = rng.choice(
        np.array(
            [-1.0, 1.0]
        ),
        size=n,
        replace=True,
    )

    return sampled * signs


def summarize(draws):

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
        "expected_delta_speed_mph":
            float(np.mean(draws)),

        "median_delta_speed_mph":
            float(q50),

        "lower_80_mph":
            float(q10),

        "upper_80_mph":
            float(q90),

        "lower_90_mph":
            float(q05),

        "upper_90_mph":
            float(q95),

        "pi80_width_mph":
            float(q90 - q10),

        "pi90_width_mph":
            float(q95 - q05),

        "p_improve":
            float(
                np.mean(
                    draws > 0.0
                )
            ),

        "mc_sd_mph":
            float(
                np.std(
                    draws,
                    ddof=1,
                )
            ),
    }


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 100)
    print(
        "INDY 500 V2-E SYSTEMATIC SCENARIO STRESS TEST"
    )
    print("=" * 100)

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

    # ========================================================
    # BUILD FROZEN-STYLE FULL-SAMPLE M2b TRACK MODELS
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
                + [
                    "delta_track_temp_c"
                ]
            )
        )

        model = LinearRegression()

        model.fit(
            d[TRACK_FEATURES],
            d["delta_track_temp_c"],
        )

        track_models[
            horizon
        ] = model

    # ========================================================
    # TRACK RESIDUAL POOLS
    # ========================================================

    tr = track_resid[
        track_resid[
            "model"
        ]
        == TRACK_MODEL
    ].copy()

    track_resid_pools = {}

    for horizon in HORIZONS:

        vals = tr.loc[
            tr[
                "horizon_min"
            ]
            == horizon,
            "residual_c",
        ].dropna().to_numpy()

        if len(vals) == 0:
            raise ValueError(
                f"No residual pool for {horizon}"
            )

        track_resid_pools[
            horizon
        ] = vals

    # ========================================================
    # PERFORMANCE UNCERTAINTY INPUTS
    # ========================================================

    bootstrap_pairs = (
        perf_boot[
            [
                "beta_track_temp",
                "beta_ambient_temp",
            ]
        ]
        .dropna()
        .reset_index(
            drop=True
        )
    )

    perf_resid_pool = (
        perf_resid[
            "residual_loyo_centered"
        ]
        .dropna()
        .to_numpy()
    )

    # ========================================================
    # DEFINE EMPIRICALLY GROUNDED SCENARIO LEVELS
    # ========================================================

    gap_values = {
        "LOW_GAP":
            float(
                samples[
                    "thermal_gap_0_c"
                ].quantile(0.25)
            ),

        "MEDIAN_GAP":
            float(
                samples[
                    "thermal_gap_0_c"
                ].quantile(0.50)
            ),

        "HIGH_GAP":
            float(
                samples[
                    "thermal_gap_0_c"
                ].quantile(0.75)
            ),
    }

    # ========================================================
    # HORIZON-SPECIFIC AMBIENT TRAJECTORIES
    #
    # For each supported horizon:
    #
    # COOLING = median observed negative hourly rate
    # NEUTRAL = 0 C/hour
    # WARMING = median observed positive hourly rate
    #
    # This avoids the earlier q25=0 degeneracy and keeps
    # each trajectory empirically supported within horizon.
    # ========================================================

    ambient_rates_by_horizon = {}

    for horizon in HORIZONS:

        d_h = samples[
            samples[
                "requested_horizon_min"
            ]
            == horizon
        ].copy()

        rate_h = (
            d_h[
                "delta_ambient_temp_c"
            ]
            /
            (
                horizon
                / 60.0
            )
        ).dropna()

        neg = rate_h[
            rate_h < 0
        ]

        pos = rate_h[
            rate_h > 0
        ]

        if len(neg) == 0:
            raise ValueError(
                f"No negative ambient-rate observations "
                f"for {horizon} min"
            )

        if len(pos) == 0:
            raise ValueError(
                f"No positive ambient-rate observations "
                f"for {horizon} min"
            )

        ambient_rates_by_horizon[
            horizon
        ] = {
            "COOLING":
                float(
                    neg.median()
                ),

            "NEUTRAL":
                0.0,

            "WARMING":
                float(
                    pos.median()
                ),
        }

    print()
    print("THERMAL GAP LEVELS")
    print("-" * 100)

    for k, v in gap_values.items():
        print(
            f"{k:14s}: {v:.4f} C"
        )

    print()
    print("AMBIENT TRAJECTORY RATES BY HORIZON")
    print("-" * 100)

    for horizon in HORIZONS:

        rates = (
            ambient_rates_by_horizon[
                horizon
            ]
        )

        print(
            f"{horizon:>3} min | "
            f"COOLING={rates['COOLING']:+.4f} | "
            f"NEUTRAL={rates['NEUTRAL']:+.4f} | "
            f"WARMING={rates['WARMING']:+.4f} C/hour"
        )

    # ========================================================
    # BUILD GRID
    #
    # Solar states use q25/q50/q75 separately at each horizon
    # to stay close to the empirical support of that horizon.
    # ========================================================

    scenario_rows = []

    scenario_id = 0

    for horizon in HORIZONS:

        d_h = samples[
            samples[
                "requested_horizon_min"
            ]
            == horizon
        ]

        solar_values = {
            "LOW_SOLAR":
                float(
                    d_h[
                        "solar_elevation_mean_deg"
                    ].quantile(0.25)
                ),

            "MEDIAN_SOLAR":
                float(
                    d_h[
                        "solar_elevation_mean_deg"
                    ].quantile(0.50)
                ),

            "HIGH_SOLAR":
                float(
                    d_h[
                        "solar_elevation_mean_deg"
                    ].quantile(0.75)
                ),
        }

        ambient_observed_min = float(
            d_h[
                "delta_ambient_temp_c"
            ].min()
        )

        ambient_observed_max = float(
            d_h[
                "delta_ambient_temp_c"
            ].max()
        )

        horizon_ambient_rates = (
            ambient_rates_by_horizon[
                horizon
            ]
        )

        for gap_name, gap in gap_values.items():

            for ambient_name, rate in horizon_ambient_rates.items():

                delta_ambient = (
                    rate
                    * horizon
                    / 60.0
                )

                for solar_name, solar in solar_values.items():

                    scenario_id += 1

                    scenario_rows.append(
                        {
                            "scenario_id":
                                scenario_id,

                            "horizon_min":
                                horizon,

                            "thermal_gap_state":
                                gap_name,

                            "thermal_gap_0_c":
                                gap,

                            "ambient_trajectory":
                                ambient_name,

                            "ambient_rate_c_per_hour":
                                rate,

                            "delta_ambient_temp_c":
                                delta_ambient,

                            "solar_state":
                                solar_name,

                            "solar_elevation_mean_deg":
                                solar,

                            "ambient_delta_observed_min_c":
                                ambient_observed_min,

                            "ambient_delta_observed_max_c":
                                ambient_observed_max,

                            "ambient_delta_inside_observed_range":
                                (
                                    ambient_observed_min
                                    <= delta_ambient
                                    <= ambient_observed_max
                                ),
                        }
                    )

    scenarios = pd.DataFrame(
        scenario_rows
    )

    scenarios.to_csv(
        SCENARIO_FILE,
        index=False,
    )

    print()
    print(
        "Scenario rows:",
        len(scenarios),
    )

    print(
        "Ambient scenarios inside horizon-specific observed range:",
        f"{scenarios['ambient_delta_inside_observed_range'].mean():.3f}"
    )

    # ========================================================
    # MONTE CARLO STRESS TEST
    # ========================================================

    result_rows = []

    for _, row in scenarios.iterrows():

        scenario_id = int(
            row[
                "scenario_id"
            ]
        )

        horizon = int(
            row[
                "horizon_min"
            ]
        )

        delta_ambient = float(
            row[
                "delta_ambient_temp_c"
            ]
        )

        X = pd.DataFrame(
            [
                {
                    "delta_ambient_temp_c":
                        delta_ambient,

                    "thermal_gap_0_c":
                        float(
                            row[
                                "thermal_gap_0_c"
                            ]
                        ),

                    "solar_elevation_mean_deg":
                        float(
                            row[
                                "solar_elevation_mean_deg"
                            ]
                        ),
                }
            ]
        )

        point_delta_track = float(
            track_models[
                horizon
            ].predict(X)[0]
        )

        rng = np.random.default_rng(
            RANDOM_SEED
            + scenario_id * 10007
        )

        # ----------------------------------------------------
        # Future track-state uncertainty
        # ----------------------------------------------------

        track_noise = (
            symmetrized_draws(
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
        # Paired coefficient uncertainty
        # ----------------------------------------------------

        coef_idx = rng.integers(
            0,
            len(
                bootstrap_pairs
            ),
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
        # Empirical performance residual uncertainty
        # ----------------------------------------------------

        perf_noise = (
            symmetrized_draws(
                perf_resid_pool,
                N_MC,
                rng,
            )
        )

        # ----------------------------------------------------
        # Final full probabilistic outlook
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

        s = summarize(
            delta_speed_draws
        )

        result_rows.append(
            {
                **row.to_dict(),

                "model_expected_delta_track_temp_c":
                    point_delta_track,

                **s,

                "n_mc":
                    N_MC,
            }
        )

    results = pd.DataFrame(
        result_rows
    )

    results.to_csv(
        RESULT_FILE,
        index=False,
    )

    # ========================================================
    # HORIZON PROFILES
    #
    # One profile = fixed thermal-gap / ambient / solar state
    # traced across the five supported horizons.
    # ========================================================

    profiles = (
        results[
            [
                "thermal_gap_state",
                "ambient_trajectory",
                "solar_state",
                "horizon_min",
                "expected_delta_speed_mph",
                "median_delta_speed_mph",
                "p_improve",
                "lower_80_mph",
                "upper_80_mph",
                "lower_90_mph",
                "upper_90_mph",
                "pi80_width_mph",
                "pi90_width_mph",
                "model_expected_delta_track_temp_c",
            ]
        ]
        .sort_values(
            [
                "thermal_gap_state",
                "ambient_trajectory",
                "solar_state",
                "horizon_min",
            ]
        )
    )

    profiles.to_csv(
        PROFILE_FILE,
        index=False,
    )

    # ========================================================
    # SUMMARY
    # ========================================================

    lines = []

    def add(x=""):
        lines.append(
            str(x)
        )

    add("=" * 110)
    add(
        "INDY 500 V2-E SYSTEMATIC SCENARIO STRESS TEST"
    )
    add("=" * 110)

    add()
    add("SCENARIO DESIGN")
    add("-" * 110)
    add(
        f"Total scenarios: {len(results)}"
    )
    add(
        "3 thermal-gap states × 3 ambient trajectories × "
        "3 solar states × 5 supported horizons"
    )

    add()
    add(
        "Thermal-gap and solar states are empirical "
        "q25/q50/q75 values from the V2-A historical sample."
    )

    add(
        "Cooling and warming trajectories are defined separately "
        "at each supported horizon using the median observed "
        "negative and positive hourly ambient-change rates. "
        "Neutral is fixed at 0 C/hour."
    )

    add()
    add("THERMAL GAP LEVELS")
    add("-" * 110)

    for k, v in gap_values.items():
        add(
            f"{k:14s}: {v:.4f} C"
        )

    add()
    add("AMBIENT TRAJECTORY LEVELS BY HORIZON")
    add("-" * 110)

    for horizon in HORIZONS:

        rates = (
            ambient_rates_by_horizon[
                horizon
            ]
        )

        add(
            f"{horizon:>3} min | "
            f"COOLING={rates['COOLING']:+.4f} | "
            f"NEUTRAL={rates['NEUTRAL']:+.4f} | "
            f"WARMING={rates['WARMING']:+.4f} C/hour"
        )

    add()
    add("SUPPORT CHECK")
    add("-" * 110)

    support_share = (
        results[
            "ambient_delta_inside_observed_range"
        ].mean()
    )

    add(
        "Ambient-delta scenarios within horizon-specific "
        f"historical observed range: {support_share:.3f}"
    )

    add()
    add("EXTREME EXPECTED OUTLOOKS")
    add("-" * 110)

    cols = [
        "horizon_min",
        "thermal_gap_state",
        "ambient_trajectory",
        "solar_state",
        "expected_delta_speed_mph",
        "p_improve",
        "lower_80_mph",
        "upper_80_mph",
    ]

    best = (
        results
        .sort_values(
            "expected_delta_speed_mph",
            ascending=False,
        )
        .head(10)[cols]
    )

    worst = (
        results
        .sort_values(
            "expected_delta_speed_mph",
            ascending=True,
        )
        .head(10)[cols]
    )

    add()
    add("TOP 10 EXPECTED DELTA-SPEED SCENARIOS")
    add(
        best
        .round(5)
        .to_string(
            index=False
        )
    )

    add()
    add("BOTTOM 10 EXPECTED DELTA-SPEED SCENARIOS")
    add(
        worst
        .round(5)
        .to_string(
            index=False
        )
    )

    add()
    add("P(IMPROVEMENT) RANGE BY HORIZON")
    add("-" * 110)

    p_summary = (
        results
        .groupby(
            "horizon_min"
        )
        .agg(
            min_p_improve=(
                "p_improve",
                "min",
            ),

            median_p_improve=(
                "p_improve",
                "median",
            ),

            max_p_improve=(
                "p_improve",
                "max",
            ),

            min_expected_delta=(
                "expected_delta_speed_mph",
                "min",
            ),

            median_expected_delta=(
                "expected_delta_speed_mph",
                "median",
            ),

            max_expected_delta=(
                "expected_delta_speed_mph",
                "max",
            ),
        )
        .reset_index()
    )

    add(
        p_summary
        .round(5)
        .to_string(
            index=False
        )
    )

    add()
    add("INTERPRETATION BOUNDARY")
    add("-" * 110)

    add(
        "This stress test evaluates the behavior of the frozen "
        "conditional physical-performance system."
    )

    add(
        "It does NOT estimate queue waiting time, opportunity "
        "probability, or retain/withdraw expected utility."
    )

    add(
        "A scenario with higher P(improvement) therefore means "
        "that, conditional on receiving another on-track "
        "opportunity at that horizon and physical state, "
        "improvement is more probable under the model."
    )

    add(
        "It must NOT be interpreted as a recommendation to "
        "withdraw an existing qualifying result."
    )

    text = "\n".join(
        lines
    )

    SUMMARY_FILE.write_text(
        text + "\n",
        encoding="utf-8",
    )

    print()
    print(text)

    print()
    print("=" * 110)
    print("OUTPUTS")
    print("=" * 110)

    print(SCENARIO_FILE)
    print(RESULT_FILE)
    print(PROFILE_FILE)
    print(SUMMARY_FILE)

    print()
    print("DONE")


if __name__ == "__main__":
    main()
