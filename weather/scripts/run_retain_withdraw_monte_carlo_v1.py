from pathlib import Path
import hashlib
import json

import numpy as np
import pandas as pd


# ============================================================
# INPUTS
# ============================================================

UNCERTAINTY_ROWS_FILE = Path(
    "weather/output/"
    "repeat_performance_uncertainty_rows_v1.csv"
)

RECOVERY_PROBABILITY_FILE = Path(
    "weather/output/"
    "repeat_performance_recovery_probability_v1.csv"
)

WAIT_SCENARIOS_FILE = Path(
    "weather/output/"
    "queue_wait_sensitivity_scenarios_v1.csv"
)

ATTEMPTS_FILE = Path(
    "data/canonical/v1/attempts.csv"
)


# ============================================================
# OUTPUTS
# ============================================================

SCENARIO_RESULTS_FILE = Path(
    "weather/output/"
    "retain_withdraw_monte_carlo_scenario_results_v1.csv"
)

DRAW_SUMMARY_FILE = Path(
    "weather/output/"
    "retain_withdraw_monte_carlo_draw_summary_v1.csv"
)

QA_FILE = Path(
    "weather/output/"
    "retain_withdraw_monte_carlo_v1_qa.csv"
)

REPORT_FILE = Path(
    "weather/output/"
    "retain_withdraw_monte_carlo_v1.md"
)


# ============================================================
# DESIGN
# ============================================================

POLICY_VERSION = (
    "RETAIN_WITHDRAW_MONTE_CARLO_V1"
)

RANDOM_SEED = 500

DRAWS_PER_SCENARIO = 100000

CURRENT_RETAINED_SPEEDS_MPH = [
    229.0,
    231.0,
    233.0,
]

BASELINE_GROUPS = [
    "LOW_BASELINE",
    "AT_OR_ABOVE_BASELINE_MEDIAN",
]

TIME_REMAINING_MINUTES = [
    10,
    20,
    30,
    45,
    60,
]

EXPECTED_WAIT_SCENARIOS = [
    "WAIT_05MIN",
    "WAIT_15MIN",
    "WAIT_30MIN",
    "WAIT_45MIN",
]

TARGET_DELTA_COLUMN = (
    "target_speed_delta_vs_best_prior_mph"
)

RECOVERY_BRANCH_COLUMN = (
    "diagnostic_recovery_like"
)


# ============================================================
# HELPERS
# ============================================================

def read_required(path):

    if not path.exists():
        raise FileNotFoundError(
            f"Missing required file: {path}"
        )

    return pd.read_csv(
        path,
        low_memory=False,
    )


def numeric(series):

    return pd.to_numeric(
        series,
        errors="coerce",
    )


def as_bool(series):

    return (
        series
        .astype(str)
        .str.lower()
        .isin(
            [
                "true",
                "1",
                "yes",
            ]
        )
    )


def stable_hash(payload):

    text = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )

    return hashlib.sha256(
        text.encode("utf-8")
    ).hexdigest()


def empirical_quantiles(values):

    x = np.asarray(
        values,
        dtype=float,
    )

    return {
        "q05":
            float(
                np.quantile(
                    x,
                    0.05,
                )
            ),

        "q10":
            float(
                np.quantile(
                    x,
                    0.10,
                )
            ),

        "q25":
            float(
                np.quantile(
                    x,
                    0.25,
                )
            ),

        "q50":
            float(
                np.quantile(
                    x,
                    0.50,
                )
            ),

        "q75":
            float(
                np.quantile(
                    x,
                    0.75,
                )
            ),

        "q90":
            float(
                np.quantile(
                    x,
                    0.90,
                )
            ),

        "q95":
            float(
                np.quantile(
                    x,
                    0.95,
                )
            ),
    }


# ============================================================
# MAIN
# ============================================================

def main():

    uncertainty_rows = read_required(
        UNCERTAINTY_ROWS_FILE
    )

    recovery_probability = read_required(
        RECOVERY_PROBABILITY_FILE
    )

    wait_scenarios = read_required(
        WAIT_SCENARIOS_FILE
    )

    attempts = read_required(
        ATTEMPTS_FILE
    )

    print()
    print("=" * 100)
    print(
        "PHASE 6C — RETAIN / WITHDRAW "
        "MONTE CARLO PROTOTYPE V1"
    )
    print("=" * 100)

    # ========================================================
    # Validate uncertainty rows
    # ========================================================

    required_uncertainty = [
        "current_attempt_id",
        TARGET_DELTA_COLUMN,
        RECOVERY_BRANCH_COLUMN,
    ]

    missing = [
        col
        for col
        in required_uncertainty
        if col
        not in uncertainty_rows.columns
    ]

    if missing:
        raise RuntimeError(
            "Missing uncertainty-row columns: "
            + ", ".join(
                missing
            )
        )

    uncertainty_rows = (
        uncertainty_rows.copy()
    )

    uncertainty_rows[
        TARGET_DELTA_COLUMN
    ] = numeric(
        uncertainty_rows[
            TARGET_DELTA_COLUMN
        ]
    )

    uncertainty_rows[
        "_recovery"
    ] = as_bool(
        uncertainty_rows[
            RECOVERY_BRANCH_COLUMN
        ]
    )

    normal_deltas = (
        uncertainty_rows.loc[
            ~uncertainty_rows[
                "_recovery"
            ],
            TARGET_DELTA_COLUMN,
        ]
        .dropna()
        .to_numpy(
            dtype=float
        )
    )

    recovery_deltas = (
        uncertainty_rows.loc[
            uncertainty_rows[
                "_recovery"
            ],
            TARGET_DELTA_COLUMN,
        ]
        .dropna()
        .to_numpy(
            dtype=float
        )
    )

    if len(
        normal_deltas
    ) != 35:
        raise RuntimeError(
            f"Expected 35 normal deltas, got {len(normal_deltas)}"
        )

    if len(
        recovery_deltas
    ) != 4:
        raise RuntimeError(
            f"Expected 4 recovery deltas, got {len(recovery_deltas)}"
        )

    # ========================================================
    # Recovery probability lookup
    # ========================================================

    required_probability_columns = [
        "eligibility_group",
        "posterior_alpha",
        "posterior_beta",
        "posterior_mean_probability",
    ]

    missing = [
        col
        for col
        in required_probability_columns
        if col
        not in recovery_probability.columns
    ]

    if missing:
        raise RuntimeError(
            "Missing recovery-probability columns: "
            + ", ".join(
                missing
            )
        )

    probability_lookup = {}

    for _, row in (
        recovery_probability.iterrows()
    ):

        group = str(
            row[
                "eligibility_group"
            ]
        )

        probability_lookup[
            group
        ] = {
            "alpha":
                float(
                    row[
                        "posterior_alpha"
                    ]
                ),

            "beta":
                float(
                    row[
                        "posterior_beta"
                    ]
                ),

            "mean":
                float(
                    row[
                        "posterior_mean_probability"
                    ]
                ),
        }

    for group in BASELINE_GROUPS:

        if group not in probability_lookup:
            raise RuntimeError(
                f"Missing recovery probability group: {group}"
            )

    # ========================================================
    # Wait scenario validation
    # ========================================================

    required_wait_columns = [
        "scenario_id",
        "latent_pre_run_delay_seconds",
        "historically_observed_queue_wait",
    ]

    missing = [
        col
        for col
        in required_wait_columns
        if col
        not in wait_scenarios.columns
    ]

    if missing:
        raise RuntimeError(
            "Missing wait-scenario columns: "
            + ", ".join(
                missing
            )
        )

    actual_wait_ids = set(
        wait_scenarios[
            "scenario_id"
        ].astype(str)
    )

    if actual_wait_ids != set(
        EXPECTED_WAIT_SCENARIOS
    ):
        raise RuntimeError(
            "Unexpected wait scenario IDs: "
            f"{sorted(actual_wait_ids)}"
        )

    if (
        wait_scenarios[
            "historically_observed_queue_wait"
        ]
        .apply(
            lambda x:
                str(x)
                .lower()
                in [
                    "true",
                    "1",
                    "yes",
                ]
        )
        .any()
    ):
        raise RuntimeError(
            "A wait scenario is incorrectly marked "
            "historically observed."
        )

    # ========================================================
    # Run duration empirical distribution
    # ========================================================

    if (
        "four_lap_total_seconds"
        not in attempts.columns
    ):
        raise RuntimeError(
            "four_lap_total_seconds missing from attempts."
        )

    run_durations = (
        numeric(
            attempts[
                "four_lap_total_seconds"
            ]
        )
        .dropna()
    )

    run_durations = (
        run_durations[
            run_durations
            > 0
        ]
        .to_numpy(
            dtype=float
        )
    )

    if len(
        run_durations
    ) != 260:
        raise RuntimeError(
            f"Expected 260 complete run durations, "
            f"got {len(run_durations)}"
        )

    # ========================================================
    # Policy hash
    # ========================================================

    policy_payload = {
        "phase":
            "6C",

        "policy_version":
            POLICY_VERSION,

        "draws_per_scenario":
            DRAWS_PER_SCENARIO,

        "random_seed":
            RANDOM_SEED,

        "retained_speeds_mph":
            CURRENT_RETAINED_SPEEDS_MPH,

        "baseline_groups":
            BASELINE_GROUPS,

        "time_remaining_minutes":
            TIME_REMAINING_MINUTES,

        "wait_scenarios":
            EXPECTED_WAIT_SCENARIOS,

        "performance_sampling":
            (
                "empirical_normal_or_recovery_delta_resampling"
            ),

        "recovery_probability_sampling":
            (
                "draw_probability_from_beta_posterior_"
                "once_per_monte_carlo_draw"
            ),

        "run_duration_sampling":
            "empirical_complete_four_lap_resampling",

        "wait_model":
            "fixed_outer_sensitivity_scenario",
    }

    policy_hash = stable_hash(
        policy_payload
    )

    # ========================================================
    # Monte Carlo
    # ========================================================

    rng = np.random.default_rng(
        RANDOM_SEED
    )

    result_rows = []

    draw_summary_rows = []

    scenario_counter = 0

    total_expected_scenarios = (
        len(
            CURRENT_RETAINED_SPEEDS_MPH
        )
        * len(
            BASELINE_GROUPS
        )
        * len(
            TIME_REMAINING_MINUTES
        )
        * len(
            EXPECTED_WAIT_SCENARIOS
        )
    )

    for retained_speed in (
        CURRENT_RETAINED_SPEEDS_MPH
    ):

        for baseline_group in (
            BASELINE_GROUPS
        ):

            beta_alpha = (
                probability_lookup[
                    baseline_group
                ][
                    "alpha"
                ]
            )

            beta_beta = (
                probability_lookup[
                    baseline_group
                ][
                    "beta"
                ]
            )

            posterior_mean = (
                probability_lookup[
                    baseline_group
                ][
                    "mean"
                ]
            )

            for time_remaining in (
                TIME_REMAINING_MINUTES
            ):

                available_seconds = (
                    float(
                        time_remaining
                    )
                    * 60.0
                )

                for _, wait_row in (
                    wait_scenarios.iterrows()
                ):

                    scenario_counter += 1

                    scenario_id = str(
                        wait_row[
                            "scenario_id"
                        ]
                    )

                    wait_seconds = float(
                        wait_row[
                            "latent_pre_run_delay_seconds"
                        ]
                    )

                    # ----------------------------------------
                    # Recovery probability uncertainty
                    #
                    # Each MC draw samples a probability from
                    # the Beta posterior, then samples branch.
                    # ----------------------------------------

                    recovery_probability_draws = (
                        rng.beta(
                            beta_alpha,
                            beta_beta,
                            size=DRAWS_PER_SCENARIO,
                        )
                    )

                    recovery_branch = (
                        rng.random(
                            DRAWS_PER_SCENARIO
                        )
                        < recovery_probability_draws
                    )

                    # ----------------------------------------
                    # Performance delta
                    # ----------------------------------------

                    performance_delta = np.empty(
                        DRAWS_PER_SCENARIO,
                        dtype=float,
                    )

                    normal_count = int(
                        (
                            ~recovery_branch
                        ).sum()
                    )

                    recovery_count = int(
                        recovery_branch.sum()
                    )

                    if normal_count > 0:

                        performance_delta[
                            ~recovery_branch
                        ] = rng.choice(
                            normal_deltas,
                            size=normal_count,
                            replace=True,
                        )

                    if recovery_count > 0:

                        performance_delta[
                            recovery_branch
                        ] = rng.choice(
                            recovery_deltas,
                            size=recovery_count,
                            replace=True,
                        )

                    new_speed = (
                        retained_speed
                        + performance_delta
                    )

                    # ----------------------------------------
                    # Run duration
                    # ----------------------------------------

                    sampled_run_duration = (
                        rng.choice(
                            run_durations,
                            size=DRAWS_PER_SCENARIO,
                            replace=True,
                        )
                    )

                    withdraw_to_completion = (
                        wait_seconds
                        + sampled_run_duration
                    )

                    completed = (
                        withdraw_to_completion
                        <= available_seconds
                    )

                    no_completed_rerun = (
                        ~completed
                    )

                    # ----------------------------------------
                    # Outcome metrics
                    # ----------------------------------------

                    improved = (
                        completed
                        &
                        (
                            new_speed
                            > retained_speed
                        )
                    )

                    slower_or_equal = (
                        completed
                        &
                        (
                            new_speed
                            <= retained_speed
                        )
                    )

                    strictly_slower = (
                        completed
                        &
                        (
                            new_speed
                            < retained_speed
                        )
                    )

                    completed_count = int(
                        completed.sum()
                    )

                    if completed_count > 0:

                        completed_new_speed = (
                            new_speed[
                                completed
                            ]
                        )

                        completed_delta = (
                            performance_delta[
                                completed
                            ]
                        )

                        speed_quantiles = (
                            empirical_quantiles(
                                completed_new_speed
                            )
                        )

                        delta_quantiles = (
                            empirical_quantiles(
                                completed_delta
                            )
                        )

                        expected_new_speed_completed = (
                            float(
                                completed_new_speed.mean()
                            )
                        )

                        expected_delta_completed = (
                            float(
                                completed_delta.mean()
                            )
                        )

                        prob_improve_given_completed = (
                            float(
                                np.mean(
                                    completed_new_speed
                                    > retained_speed
                                )
                            )
                        )

                        prob_slower_given_completed = (
                            float(
                                np.mean(
                                    completed_new_speed
                                    < retained_speed
                                )
                            )
                        )

                    else:

                        speed_quantiles = {
                            key:
                                np.nan
                            for key in [
                                "q05",
                                "q10",
                                "q25",
                                "q50",
                                "q75",
                                "q90",
                                "q95",
                            ]
                        }

                        delta_quantiles = (
                            speed_quantiles.copy()
                        )

                        expected_new_speed_completed = (
                            np.nan
                        )

                        expected_delta_completed = (
                            np.nan
                        )

                        prob_improve_given_completed = (
                            np.nan
                        )

                        prob_slower_given_completed = (
                            np.nan
                        )

                    # ----------------------------------------
                    # Utility-neutral outcome probabilities
                    #
                    # We deliberately DO NOT assign a numeric
                    # utility to no-completion yet.
                    # ----------------------------------------

                    p_completed = float(
                        completed.mean()
                    )

                    p_no_completion = float(
                        no_completed_rerun.mean()
                    )

                    p_improve_unconditional = float(
                        improved.mean()
                    )

                    p_slower_or_equal_unconditional = (
                        float(
                            slower_or_equal.mean()
                        )
                    )

                    p_strictly_slower_unconditional = (
                        float(
                            strictly_slower.mean()
                        )
                    )

                    result_rows.append(
                        {
                            "scenario_index":
                                scenario_counter,

                            "current_retained_speed_mph":
                                float(
                                    retained_speed
                                ),

                            "baseline_group":
                                baseline_group,

                            "time_remaining_minutes":
                                float(
                                    time_remaining
                                ),

                            "wait_scenario_id":
                                scenario_id,

                            "latent_pre_run_delay_minutes":
                                wait_seconds
                                / 60.0,

                            "monte_carlo_draws":
                                DRAWS_PER_SCENARIO,

                            "recovery_beta_alpha":
                                beta_alpha,

                            "recovery_beta_beta":
                                beta_beta,

                            "recovery_posterior_mean":
                                posterior_mean,

                            "simulated_recovery_branch_rate":
                                float(
                                    recovery_branch.mean()
                                ),

                            "p_completed_rerun":
                                p_completed,

                            "p_no_completed_rerun":
                                p_no_completion,

                            "p_improve_unconditional":
                                p_improve_unconditional,

                            "p_slower_or_equal_unconditional":
                                p_slower_or_equal_unconditional,

                            "p_strictly_slower_unconditional":
                                p_strictly_slower_unconditional,

                            "p_improve_given_completed":
                                prob_improve_given_completed,

                            "p_slower_given_completed":
                                prob_slower_given_completed,

                            "expected_new_speed_given_completed_mph":
                                expected_new_speed_completed,

                            "expected_delta_given_completed_mph":
                                expected_delta_completed,

                            "new_speed_q05_mph":
                                speed_quantiles[
                                    "q05"
                                ],

                            "new_speed_q10_mph":
                                speed_quantiles[
                                    "q10"
                                ],

                            "new_speed_q25_mph":
                                speed_quantiles[
                                    "q25"
                                ],

                            "new_speed_q50_mph":
                                speed_quantiles[
                                    "q50"
                                ],

                            "new_speed_q75_mph":
                                speed_quantiles[
                                    "q75"
                                ],

                            "new_speed_q90_mph":
                                speed_quantiles[
                                    "q90"
                                ],

                            "new_speed_q95_mph":
                                speed_quantiles[
                                    "q95"
                                ],

                            "delta_q05_mph":
                                delta_quantiles[
                                    "q05"
                                ],

                            "delta_q50_mph":
                                delta_quantiles[
                                    "q50"
                                ],

                            "delta_q95_mph":
                                delta_quantiles[
                                    "q95"
                                ],

                            "retain_speed_mph":
                                float(
                                    retained_speed
                                ),

                            "retain_completion_probability":
                                1.0,

                            "retain_speed_variance":
                                0.0,

                            "utility_function_applied":
                                False,

                            "leaderboard_target_applied":
                                False,

                            "queue_wait_historical_claim":
                                False,

                            "policy_hash":
                                policy_hash,
                        }
                    )

                    draw_summary_rows.append(
                        {
                            "scenario_index":
                                scenario_counter,

                            "current_retained_speed_mph":
                                float(
                                    retained_speed
                                ),

                            "baseline_group":
                                baseline_group,

                            "time_remaining_minutes":
                                float(
                                    time_remaining
                                ),

                            "wait_scenario_id":
                                scenario_id,

                            "draws":
                                DRAWS_PER_SCENARIO,

                            "completed_draws":
                                completed_count,

                            "no_completion_draws":
                                int(
                                    no_completed_rerun.sum()
                                ),

                            "recovery_draws":
                                recovery_count,

                            "normal_draws":
                                normal_count,

                            "improved_draws":
                                int(
                                    improved.sum()
                                ),

                            "strictly_slower_draws":
                                int(
                                    strictly_slower.sum()
                                ),

                            "policy_hash":
                                policy_hash,
                        }
                    )

    results = pd.DataFrame(
        result_rows
    )

    draw_summary = pd.DataFrame(
        draw_summary_rows
    )

    # ========================================================
    # QA
    # ========================================================

    expected_rows = (
        total_expected_scenarios
    )

    probability_columns = [
        "p_completed_rerun",
        "p_no_completed_rerun",
        "p_improve_unconditional",
        "p_slower_or_equal_unconditional",
        "p_strictly_slower_unconditional",
    ]

    checks = {
        "scenario_rows_match_expected":
            len(
                results
            )
            == expected_rows,

        "draw_summary_rows_match_expected":
            len(
                draw_summary
            )
            == expected_rows,

        "normal_delta_rows_equal_35":
            len(
                normal_deltas
            )
            == 35,

        "recovery_delta_rows_equal_4":
            len(
                recovery_deltas
            )
            == 4,

        "run_duration_rows_equal_260":
            len(
                run_durations
            )
            == 260,

        "all_probability_values_in_0_1":
            (
                (
                    results[
                        probability_columns
                    ]
                    >= 0
                )
                &
                (
                    results[
                        probability_columns
                    ]
                    <= 1
                )
            ).all().all(),

        "completion_and_failure_sum_to_one":
            np.allclose(
                (
                    results[
                        "p_completed_rerun"
                    ]
                    +
                    results[
                        "p_no_completed_rerun"
                    ]
                ),
                1.0,
                atol=1e-12,
                rtol=0.0,
            ),

        "retain_completion_probability_all_one":
            np.allclose(
                results[
                    "retain_completion_probability"
                ],
                1.0,
                atol=0.0,
                rtol=0.0,
            ),

        "no_utility_function_applied":
            not results[
                "utility_function_applied"
            ].any(),

        "no_leaderboard_target_applied":
            not results[
                "leaderboard_target_applied"
            ].any(),

        "no_queue_wait_historical_claim":
            not results[
                "queue_wait_historical_claim"
            ].any(),

        "all_policy_hashes_present":
            (
                results[
                    "policy_hash"
                ].notna().all()
                and
                draw_summary[
                    "policy_hash"
                ].notna().all()
            ),
    }

    qa_rows = []

    for metric, passed in (
        checks.items()
    ):

        qa_rows.append(
            {
                "metric":
                    metric,

                "value":
                    int(
                        bool(
                            passed
                        )
                    ),

                "status":
                    (
                        "PASS"
                        if passed
                        else "FAIL"
                    ),
            }
        )

    qa_rows.extend(
        [
            {
                "metric":
                    "scenario_rows",

                "value":
                    len(
                        results
                    ),

                "status":
                    "INFO",
            },

            {
                "metric":
                    "draws_per_scenario",

                "value":
                    DRAWS_PER_SCENARIO,

                "status":
                    "INFO",
            },

            {
                "metric":
                    "total_monte_carlo_draws",

                "value":
                    int(
                        len(
                            results
                        )
                        * DRAWS_PER_SCENARIO
                    ),

                "status":
                    "INFO",
            },

            {
                "metric":
                    "policy_hash",

                "value":
                    policy_hash,

                "status":
                    "INFO",
            },
        ]
    )

    qa = pd.DataFrame(
        qa_rows
    )

    all_pass = all(
        checks.values()
    )

    # ========================================================
    # PRINT COMPACT RESULTS
    # ========================================================

    print()
    print("SIMULATION DESIGN")
    print("-" * 100)

    print(
        "Retained speeds:",
        CURRENT_RETAINED_SPEEDS_MPH
    )

    print(
        "Baseline groups:",
        BASELINE_GROUPS
    )

    print(
        "Time remaining:",
        TIME_REMAINING_MINUTES
    )

    print(
        "Wait scenarios:",
        EXPECTED_WAIT_SCENARIOS
    )

    print(
        "Draws per scenario:",
        DRAWS_PER_SCENARIO
    )

    print(
        "Total scenarios:",
        len(
            results
        )
    )

    print(
        "Total draws:",
        len(
            results
        )
        * DRAWS_PER_SCENARIO
    )

    print()
    print("RECOVERY BRANCH CALIBRATION")
    print("-" * 110)

    calibration = (
        results[
            [
                "baseline_group",
                "recovery_posterior_mean",
                "simulated_recovery_branch_rate",
            ]
        ]
        .groupby(
            "baseline_group",
            as_index=False,
        )
        .mean()
    )

    print(
        calibration.to_string(
            index=False
        )
    )

    print()
    print(
        "RETAIN/WITHDRAW OUTCOME GRID "
        "FOR RETAINED SPEED = 231 MPH"
    )
    print("-" * 180)

    example = results[
        results[
            "current_retained_speed_mph"
        ]
        == 231.0
    ].copy()

    print(
        example[
            [
                "baseline_group",
                "time_remaining_minutes",
                "wait_scenario_id",
                "p_completed_rerun",
                "p_no_completed_rerun",
                "p_improve_unconditional",
                "p_improve_given_completed",
                "p_slower_given_completed",
                "expected_new_speed_given_completed_mph",
                "new_speed_q05_mph",
                "new_speed_q50_mph",
                "new_speed_q95_mph",
            ]
        ]
        .sort_values(
            [
                "baseline_group",
                "time_remaining_minutes",
                "wait_scenario_id",
            ]
        )
        .to_string(
            index=False
        )
    )

    print()
    print(
        "EARLY-SESSION EXAMPLE: "
        "60 MIN REMAINING"
    )
    print("-" * 150)

    early = results[
        (
            results[
                "current_retained_speed_mph"
            ]
            == 231.0
        )
        &
        (
            results[
                "time_remaining_minutes"
            ]
            == 60
        )
    ].copy()

    print(
        early[
            [
                "baseline_group",
                "wait_scenario_id",
                "p_completed_rerun",
                "p_improve_given_completed",
                "expected_delta_given_completed_mph",
                "delta_q05_mph",
                "delta_q50_mph",
                "delta_q95_mph",
            ]
        ]
        .to_string(
            index=False
        )
    )

    print()
    print("QA")
    print("-" * 130)

    print(
        qa.to_string(
            index=False
        )
    )

    # ========================================================
    # WRITE
    # ========================================================

    SCENARIO_RESULTS_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    results.to_csv(
        SCENARIO_RESULTS_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    draw_summary.to_csv(
        DRAW_SUMMARY_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    qa.to_csv(
        QA_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    # ========================================================
    # REPORT
    # ========================================================

    report = []

    report.append(
        "# Retain / Withdraw Monte Carlo Prototype V1"
    )

    report.append("")

    report.append(
        f"Policy version: `{POLICY_VERSION}`"
    )

    report.append(
        f"Policy hash: `{policy_hash}`"
    )

    report.append("")

    report.append(
        "## Purpose"
    )

    report.append("")

    report.append(
        "Combine frozen repeat-performance uncertainty "
        "with explicit queue/wait sensitivity scenarios."
    )

    report.append("")

    report.append(
        "This is the first Monte Carlo retain/withdraw "
        "prototype, but it does not yet apply leaderboard "
        "or utility semantics."
    )

    report.append("")

    report.append(
        "## Retain branch"
    )

    report.append("")

    report.append(
        "Retain deterministically preserves the current "
        "retained speed."
    )

    report.append("")

    report.append(
        "## Withdraw branch"
    )

    report.append("")

    report.append(
        "Each draw samples:"
    )

    report.append("")

    report.append(
        "- recovery probability uncertainty from the "
        "frozen Beta posterior;"
    )

    report.append(
        "- normal or recovery-like empirical performance delta;"
    )

    report.append(
        "- empirical complete four-lap run duration;"
    )

    report.append(
        "- a fixed outer latent pre-run-delay sensitivity scenario."
    )

    report.append("")

    report.append(
        "If wait plus sampled run duration exceeds time "
        "remaining, the outcome is "
        "`NO_COMPLETED_RERUN_BEFORE_CUTOFF`."
    )

    report.append("")

    report.append(
        "## Important boundary"
    )

    report.append("")

    report.append(
        "- Wait values are sensitivity assumptions."
    )

    report.append(
        "- No historical queue-wait distribution is claimed."
    )

    report.append(
        "- No numeric utility function is applied."
    )

    report.append(
        "- No leaderboard / Top-12 / bump threshold is applied."
    )

    report.append(
        "- No recommendation is issued yet."
    )

    report.append("")

    report.append(
        "## Next phase"
    )

    report.append("")

    report.append(
        "Phase 6D should define explicit decision utility "
        "and threshold semantics before a recommendation "
        "engine is allowed to compare retain versus withdraw."
    )

    report.append("")

    report.append(
        "## Status"
    )

    report.append("")

    if all_pass:

        report.append(
            "**RETAIN_WITHDRAW_MONTE_CARLO_V1_COMPLETE**"
        )

    else:

        report.append(
            "**REVIEW_REQUIRED**"
        )

    REPORT_FILE.write_text(
        "\n".join(
            report
        ),
        encoding="utf-8",
    )

    # ========================================================
    # FINAL
    # ========================================================

    print()
    print("=" * 100)

    if all_pass:

        print(
            "FINAL STATUS: "
            "RETAIN_WITHDRAW_MONTE_CARLO_V1_COMPLETE"
        )

    else:

        print(
            "FINAL STATUS: REVIEW_REQUIRED"
        )

    print("=" * 100)

    print()
    print(
        "NO RECOMMENDATION WAS ISSUED."
    )

    print(
        "NO LEADERBOARD THRESHOLD WAS APPLIED."
    )

    print(
        "NO QUEUE-WAIT HISTORICAL CLAIM WAS MADE."
    )

    print()
    print("OUTPUTS")

    print(
        SCENARIO_RESULTS_FILE
    )

    print(
        DRAW_SUMMARY_FILE
    )

    print(
        QA_FILE
    )

    print(
        REPORT_FILE
    )


if __name__ == "__main__":
    main()
