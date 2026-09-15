from pathlib import Path
import hashlib
import json

import numpy as np
import pandas as pd


# ============================================================
# INPUTS
# ============================================================

MC_FILE = Path(
    "weather/output/"
    "retain_withdraw_monte_carlo_scenario_results_v1.csv"
)

UNCERTAINTY_FILE = Path(
    "weather/output/"
    "repeat_performance_uncertainty_rows_v1.csv"
)

RECOVERY_PROBABILITY_FILE = Path(
    "weather/output/"
    "repeat_performance_recovery_probability_v1.csv"
)

DECISION_SEMANTICS_FILE = Path(
    "weather/output/"
    "retain_withdraw_decision_semantics_v1.csv"
)

THRESHOLD_POLICY_FILE = Path(
    "weather/output/"
    "retain_withdraw_threshold_policy_v1.csv"
)


# ============================================================
# OUTPUTS
# ============================================================

PROFILE_FILE = Path(
    "weather/output/"
    "retain_withdraw_target_aware_profiles_v1.csv"
)

COMPACT_FILE = Path(
    "weather/output/"
    "retain_withdraw_target_aware_compact_v1.csv"
)

QA_FILE = Path(
    "weather/output/"
    "retain_withdraw_target_aware_profiles_v1_qa.csv"
)

REPORT_FILE = Path(
    "weather/output/"
    "retain_withdraw_target_aware_profiles_v1.md"
)


# ============================================================
# DESIGN
# ============================================================

POLICY_VERSION = (
    "RETAIN_WITHDRAW_TARGET_AWARE_PROFILE_V1"
)

EXPECTED_MC_ROWS = 120

EXPECTED_NORMAL_ROWS = 35
EXPECTED_RECOVERY_ROWS = 4

GAIN_THRESHOLDS_MPH = [
    0.10,
    0.25,
    0.50,
    1.00,
]

LOSS_THRESHOLDS_MPH = [
    -0.25,
    -0.50,
    -1.00,
]

BASELINE_GROUPS = [
    "LOW_BASELINE",
    "AT_OR_ABOVE_BASELINE_MEDIAN",
]

TARGET_DELTA_COLUMN = (
    "target_speed_delta_vs_best_prior_mph"
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
        .str.strip()
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


def empirical_probability(
    values,
    operator,
    threshold,
):

    x = np.asarray(
        values,
        dtype=float,
    )

    if len(x) == 0:
        return np.nan

    if operator == ">=":

        return float(
            np.mean(
                x >= threshold
            )
        )

    if operator == ">":

        return float(
            np.mean(
                x > threshold
            )
        )

    if operator == "<=":

        return float(
            np.mean(
                x <= threshold
            )
        )

    if operator == "<":

        return float(
            np.mean(
                x < threshold
            )
        )

    raise ValueError(
        f"Unsupported operator: {operator}"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    mc = read_required(
        MC_FILE
    )

    uncertainty = read_required(
        UNCERTAINTY_FILE
    )

    recovery_probability = read_required(
        RECOVERY_PROBABILITY_FILE
    )

    semantics = read_required(
        DECISION_SEMANTICS_FILE
    )

    threshold_policy = read_required(
        THRESHOLD_POLICY_FILE
    )

    print()
    print("=" * 100)
    print(
        "PHASE 6E — TARGET-AWARE "
        "RETAIN / WITHDRAW DECISION PROFILE ENGINE V1"
    )
    print("=" * 100)

    # ========================================================
    # Validate Phase 6C / 6D
    # ========================================================

    if len(
        mc
    ) != EXPECTED_MC_ROWS:

        raise RuntimeError(
            f"Expected {EXPECTED_MC_ROWS} MC rows, "
            f"got {len(mc)}"
        )

    required_mc = [
        "current_retained_speed_mph",
        "baseline_group",
        "time_remaining_minutes",
        "wait_scenario_id",
        "latent_pre_run_delay_minutes",
        "p_completed_rerun",
        "p_no_completed_rerun",
        "p_improve_unconditional",
        "p_improve_given_completed",
        "p_slower_given_completed",
        "expected_delta_given_completed_mph",
        "delta_q05_mph",
        "delta_q50_mph",
        "delta_q95_mph",
    ]

    missing = [
        col
        for col in required_mc
        if col not in mc.columns
    ]

    if missing:

        raise RuntimeError(
            "Missing MC columns: "
            + ", ".join(
                missing
            )
        )

    if (
        "decision_component"
        not in semantics.columns
    ):

        raise RuntimeError(
            "Decision semantics input invalid."
        )

    if (
        "RECOMMENDATION"
        not in set(
            semantics[
                "decision_component"
            ].astype(str)
        )
    ):

        raise RuntimeError(
            "Frozen recommendation boundary missing."
        )

    # ========================================================
    # Validate thresholds
    # ========================================================

    expected_gain_thresholds = set(
        GAIN_THRESHOLDS_MPH
    )

    observed_gain_thresholds = set(
        numeric(
            threshold_policy.loc[
                threshold_policy[
                    "threshold_type"
                ]
                == "GAIN_AT_LEAST",
                "threshold_mph",
            ]
        )
        .dropna()
        .tolist()
    )

    if (
        observed_gain_thresholds
        != expected_gain_thresholds
    ):

        raise RuntimeError(
            "Gain thresholds do not match "
            "frozen Phase 6D policy."
        )

    # ========================================================
    # Performance empirical branches
    # ========================================================

    required_uncertainty = [
        TARGET_DELTA_COLUMN,
        "diagnostic_recovery_like",
    ]

    missing = [
        col
        for col in required_uncertainty
        if col not in uncertainty.columns
    ]

    if missing:

        raise RuntimeError(
            "Missing uncertainty fields: "
            + ", ".join(
                missing
            )
        )

    uncertainty = uncertainty.copy()

    uncertainty[
        "_delta"
    ] = numeric(
        uncertainty[
            TARGET_DELTA_COLUMN
        ]
    )

    uncertainty[
        "_recovery"
    ] = as_bool(
        uncertainty[
            "diagnostic_recovery_like"
        ]
    )

    normal_deltas = (
        uncertainty.loc[
            ~uncertainty[
                "_recovery"
            ],
            "_delta",
        ]
        .dropna()
        .to_numpy(
            dtype=float
        )
    )

    recovery_deltas = (
        uncertainty.loc[
            uncertainty[
                "_recovery"
            ],
            "_delta",
        ]
        .dropna()
        .to_numpy(
            dtype=float
        )
    )

    if len(
        normal_deltas
    ) != EXPECTED_NORMAL_ROWS:

        raise RuntimeError(
            f"Expected {EXPECTED_NORMAL_ROWS} normal rows, "
            f"got {len(normal_deltas)}"
        )

    if len(
        recovery_deltas
    ) != EXPECTED_RECOVERY_ROWS:

        raise RuntimeError(
            f"Expected {EXPECTED_RECOVERY_ROWS} recovery rows, "
            f"got {len(recovery_deltas)}"
        )

    # ========================================================
    # Recovery posterior lookup
    # ========================================================

    required_recovery = [
        "eligibility_group",
        "posterior_alpha",
        "posterior_beta",
        "posterior_mean_probability",
    ]

    missing = [
        col
        for col in required_recovery
        if col not in recovery_probability.columns
    ]

    if missing:

        raise RuntimeError(
            "Missing recovery probability fields: "
            + ", ".join(
                missing
            )
        )

    recovery_lookup = {}

    for _, row in (
        recovery_probability.iterrows()
    ):

        group = str(
            row[
                "eligibility_group"
            ]
        )

        recovery_lookup[
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

        if group not in recovery_lookup:

            raise RuntimeError(
                f"Missing recovery group: {group}"
            )

    # ========================================================
    # Precompute empirical branch event probabilities
    # ========================================================

    branch_probability_rows = []

    for threshold in (
        GAIN_THRESHOLDS_MPH
    ):

        branch_probability_rows.append(
            {
                "event_type":
                    "GAIN_AT_LEAST",

                "threshold_mph":
                    threshold,

                "normal_probability":
                    empirical_probability(
                        normal_deltas,
                        ">=",
                        threshold,
                    ),

                "recovery_probability":
                    empirical_probability(
                        recovery_deltas,
                        ">=",
                        threshold,
                    ),
            }
        )

    for threshold in (
        LOSS_THRESHOLDS_MPH
    ):

        branch_probability_rows.append(
            {
                "event_type":
                    "LOSS_AT_MOST",

                "threshold_mph":
                    threshold,

                "normal_probability":
                    empirical_probability(
                        normal_deltas,
                        "<=",
                        threshold,
                    ),

                "recovery_probability":
                    empirical_probability(
                        recovery_deltas,
                        "<=",
                        threshold,
                    ),
            }
        )

    branch_probabilities = pd.DataFrame(
        branch_probability_rows
    )

    normal_gain_any = (
        empirical_probability(
            normal_deltas,
            ">",
            0.0,
        )
    )

    recovery_gain_any = (
        empirical_probability(
            recovery_deltas,
            ">",
            0.0,
        )
    )

    normal_loss_any = (
        empirical_probability(
            normal_deltas,
            "<",
            0.0,
        )
    )

    recovery_loss_any = (
        empirical_probability(
            recovery_deltas,
            "<",
            0.0,
        )
    )

    # ========================================================
    # Policy hash
    # ========================================================

    policy_payload = {
        "phase":
            "6E",

        "policy_version":
            POLICY_VERSION,

        "gain_thresholds_mph":
            GAIN_THRESHOLDS_MPH,

        "loss_thresholds_mph":
            LOSS_THRESHOLDS_MPH,

        "normal_rows":
            len(
                normal_deltas
            ),

        "recovery_rows":
            len(
                recovery_deltas
            ),

        "combination_rule":
            (
                "completion_probability * "
                "posterior-mean recovery mixture "
                "of empirical branch event rates"
            ),

        "recommendation_enabled":
            False,
    }

    policy_hash = stable_hash(
        policy_payload
    )

    # ========================================================
    # Build target-aware profiles
    # ========================================================

    profile_rows = []

    for _, scenario in (
        mc.iterrows()
    ):

        retained_speed = float(
            scenario[
                "current_retained_speed_mph"
            ]
        )

        baseline_group = str(
            scenario[
                "baseline_group"
            ]
        )

        completion_probability = float(
            scenario[
                "p_completed_rerun"
            ]
        )

        no_completion_probability = float(
            scenario[
                "p_no_completed_rerun"
            ]
        )

        p_recovery = (
            recovery_lookup[
                baseline_group
            ][
                "mean"
            ]
        )

        p_normal = (
            1.0
            - p_recovery
        )

        # ----------------------------------------------------
        # Any positive improvement
        # ----------------------------------------------------

        p_any_gain_given_completed = (
            p_normal
            * normal_gain_any
            +
            p_recovery
            * recovery_gain_any
        )

        p_any_loss_given_completed = (
            p_normal
            * normal_loss_any
            +
            p_recovery
            * recovery_loss_any
        )

        p_any_gain_unconditional = (
            completion_probability
            * p_any_gain_given_completed
        )

        p_any_loss_unconditional = (
            completion_probability
            * p_any_loss_given_completed
        )

        # ----------------------------------------------------
        # Target gain profiles
        # ----------------------------------------------------

        for threshold in (
            GAIN_THRESHOLDS_MPH
        ):

            branch_row = (
                branch_probabilities[
                    (
                        branch_probabilities[
                            "event_type"
                        ]
                        == "GAIN_AT_LEAST"
                    )
                    &
                    (
                        np.isclose(
                            branch_probabilities[
                                "threshold_mph"
                            ],
                            threshold,
                        )
                    )
                ]
                .iloc[0]
            )

            p_normal_target = float(
                branch_row[
                    "normal_probability"
                ]
            )

            p_recovery_target = float(
                branch_row[
                    "recovery_probability"
                ]
            )

            p_target_given_completed = (
                p_normal
                * p_normal_target
                +
                p_recovery
                * p_recovery_target
            )

            p_target_unconditional = (
                completion_probability
                * p_target_given_completed
            )

            # --------------------------------------------
            # Improvement but not enough to target
            # --------------------------------------------

            p_improve_but_short_given_completed = max(
                0.0,
                (
                    p_any_gain_given_completed
                    - p_target_given_completed
                ),
            )

            p_improve_but_short_unconditional = (
                completion_probability
                * p_improve_but_short_given_completed
            )

            # --------------------------------------------
            # Completed but no improvement
            # --------------------------------------------

            p_completed_no_gain = (
                completion_probability
                * (
                    1.0
                    - p_any_gain_given_completed
                )
            )

            target_speed = (
                retained_speed
                + threshold
            )

            profile_rows.append(
                {
                    "profile_type":
                        "TARGET_GAIN",

                    "current_retained_speed_mph":
                        retained_speed,

                    "required_gain_mph":
                        float(
                            threshold
                        ),

                    "absolute_target_speed_mph":
                        target_speed,

                    "target_source":
                        "SENSITIVITY_GAIN_THRESHOLD",

                    "historical_leaderboard_target":
                        False,

                    "baseline_group":
                        baseline_group,

                    "time_remaining_minutes":
                        float(
                            scenario[
                                "time_remaining_minutes"
                            ]
                        ),

                    "wait_scenario_id":
                        scenario[
                            "wait_scenario_id"
                        ],

                    "latent_pre_run_delay_minutes":
                        float(
                            scenario[
                                "latent_pre_run_delay_minutes"
                            ]
                        ),

                    "p_recovery_branch":
                        p_recovery,

                    "p_normal_branch":
                        p_normal,

                    "p_completed_rerun":
                        completion_probability,

                    "p_no_completed_rerun":
                        no_completion_probability,

                    "p_any_gain_given_completed":
                        p_any_gain_given_completed,

                    "p_any_gain_unconditional":
                        p_any_gain_unconditional,

                    "p_target_given_completed":
                        p_target_given_completed,

                    "p_target_unconditional":
                        p_target_unconditional,

                    "p_improve_but_short_of_target_given_completed":
                        p_improve_but_short_given_completed,

                    "p_improve_but_short_of_target_unconditional":
                        p_improve_but_short_unconditional,

                    "p_any_loss_given_completed":
                        p_any_loss_given_completed,

                    "p_any_loss_unconditional":
                        p_any_loss_unconditional,

                    "p_completed_no_positive_gain":
                        p_completed_no_gain,

                    "expected_delta_given_completed_mph":
                        float(
                            scenario[
                                "expected_delta_given_completed_mph"
                            ]
                        )
                        if pd.notna(
                            scenario[
                                "expected_delta_given_completed_mph"
                            ]
                        )
                        else np.nan,

                    "delta_q05_mph":
                        float(
                            scenario[
                                "delta_q05_mph"
                            ]
                        )
                        if pd.notna(
                            scenario[
                                "delta_q05_mph"
                            ]
                        )
                        else np.nan,

                    "delta_q50_mph":
                        float(
                            scenario[
                                "delta_q50_mph"
                            ]
                        )
                        if pd.notna(
                            scenario[
                                "delta_q50_mph"
                            ]
                        )
                        else np.nan,

                    "delta_q95_mph":
                        float(
                            scenario[
                                "delta_q95_mph"
                            ]
                        )
                        if pd.notna(
                            scenario[
                                "delta_q95_mph"
                            ]
                        )
                        else np.nan,

                    "recommendation_enabled":
                        False,

                    "recommendation":
                        "NOT_ISSUED",

                    "policy_hash":
                        policy_hash,
                }
            )

        # ----------------------------------------------------
        # Downside profiles
        # ----------------------------------------------------

        for threshold in (
            LOSS_THRESHOLDS_MPH
        ):

            branch_row = (
                branch_probabilities[
                    (
                        branch_probabilities[
                            "event_type"
                        ]
                        == "LOSS_AT_MOST"
                    )
                    &
                    (
                        np.isclose(
                            branch_probabilities[
                                "threshold_mph"
                            ],
                            threshold,
                        )
                    )
                ]
                .iloc[0]
            )

            p_normal_loss = float(
                branch_row[
                    "normal_probability"
                ]
            )

            p_recovery_loss = float(
                branch_row[
                    "recovery_probability"
                ]
            )

            p_loss_given_completed = (
                p_normal
                * p_normal_loss
                +
                p_recovery
                * p_recovery_loss
            )

            p_loss_unconditional = (
                completion_probability
                * p_loss_given_completed
            )

            profile_rows.append(
                {
                    "profile_type":
                        "DOWNSIDE_LOSS",

                    "current_retained_speed_mph":
                        retained_speed,

                    "required_gain_mph":
                        float(
                            threshold
                        ),

                    "absolute_target_speed_mph":
                        retained_speed
                        + threshold,

                    "target_source":
                        "DOWNSIDE_THRESHOLD",

                    "historical_leaderboard_target":
                        False,

                    "baseline_group":
                        baseline_group,

                    "time_remaining_minutes":
                        float(
                            scenario[
                                "time_remaining_minutes"
                            ]
                        ),

                    "wait_scenario_id":
                        scenario[
                            "wait_scenario_id"
                        ],

                    "latent_pre_run_delay_minutes":
                        float(
                            scenario[
                                "latent_pre_run_delay_minutes"
                            ]
                        ),

                    "p_recovery_branch":
                        p_recovery,

                    "p_normal_branch":
                        p_normal,

                    "p_completed_rerun":
                        completion_probability,

                    "p_no_completed_rerun":
                        no_completion_probability,

                    "p_any_gain_given_completed":
                        p_any_gain_given_completed,

                    "p_any_gain_unconditional":
                        p_any_gain_unconditional,

                    "p_target_given_completed":
                        p_loss_given_completed,

                    "p_target_unconditional":
                        p_loss_unconditional,

                    "p_improve_but_short_of_target_given_completed":
                        np.nan,

                    "p_improve_but_short_of_target_unconditional":
                        np.nan,

                    "p_any_loss_given_completed":
                        p_any_loss_given_completed,

                    "p_any_loss_unconditional":
                        p_any_loss_unconditional,

                    "p_completed_no_positive_gain":
                        (
                            completion_probability
                            * (
                                1.0
                                - p_any_gain_given_completed
                            )
                        ),

                    "expected_delta_given_completed_mph":
                        float(
                            scenario[
                                "expected_delta_given_completed_mph"
                            ]
                        )
                        if pd.notna(
                            scenario[
                                "expected_delta_given_completed_mph"
                            ]
                        )
                        else np.nan,

                    "delta_q05_mph":
                        float(
                            scenario[
                                "delta_q05_mph"
                            ]
                        )
                        if pd.notna(
                            scenario[
                                "delta_q05_mph"
                            ]
                        )
                        else np.nan,

                    "delta_q50_mph":
                        float(
                            scenario[
                                "delta_q50_mph"
                            ]
                        )
                        if pd.notna(
                            scenario[
                                "delta_q50_mph"
                            ]
                        )
                        else np.nan,

                    "delta_q95_mph":
                        float(
                            scenario[
                                "delta_q95_mph"
                            ]
                        )
                        if pd.notna(
                            scenario[
                                "delta_q95_mph"
                            ]
                        )
                        else np.nan,

                    "recommendation_enabled":
                        False,

                    "recommendation":
                        "NOT_ISSUED",

                    "policy_hash":
                        policy_hash,
                }
            )

    profiles = pd.DataFrame(
        profile_rows
    )

    # ========================================================
    # Compact target-gain output
    # ========================================================

    compact = profiles[
        profiles[
            "profile_type"
        ]
        == "TARGET_GAIN"
    ].copy()

    compact = compact[
        [
            "current_retained_speed_mph",
            "required_gain_mph",
            "absolute_target_speed_mph",
            "baseline_group",
            "time_remaining_minutes",
            "wait_scenario_id",
            "p_completed_rerun",
            "p_no_completed_rerun",
            "p_target_given_completed",
            "p_target_unconditional",
            "p_any_gain_given_completed",
            "p_improve_but_short_of_target_given_completed",
            "p_any_loss_given_completed",
            "expected_delta_given_completed_mph",
            "delta_q05_mph",
            "delta_q50_mph",
            "delta_q95_mph",
            "recommendation",
            "policy_hash",
        ]
    ].copy()

    # ========================================================
    # QA
    # ========================================================

    expected_profile_rows = (
        EXPECTED_MC_ROWS
        * (
            len(
                GAIN_THRESHOLDS_MPH
            )
            +
            len(
                LOSS_THRESHOLDS_MPH
            )
        )
    )

    expected_compact_rows = (
        EXPECTED_MC_ROWS
        * len(
            GAIN_THRESHOLDS_MPH
        )
    )

    probability_columns = [
        "p_completed_rerun",
        "p_no_completed_rerun",
        "p_any_gain_given_completed",
        "p_any_gain_unconditional",
        "p_target_given_completed",
        "p_target_unconditional",
        "p_any_loss_given_completed",
        "p_any_loss_unconditional",
    ]

    finite_probability_mask = (
        profiles[
            probability_columns
        ]
        .notna()
    )

    values = profiles[
        probability_columns
    ]

    probability_valid = (
        (
            (
                values >= 0
            )
            |
            ~finite_probability_mask
        )
        &
        (
            (
                values <= 1
            )
            |
            ~finite_probability_mask
        )
    ).all().all()

    checks = {
        "mc_rows_equal_120":
            len(
                mc
            )
            == 120,

        "normal_rows_equal_35":
            len(
                normal_deltas
            )
            == 35,

        "recovery_rows_equal_4":
            len(
                recovery_deltas
            )
            == 4,

        "profile_rows_match_expected":
            len(
                profiles
            )
            == expected_profile_rows,

        "compact_rows_match_expected":
            len(
                compact
            )
            == expected_compact_rows,

        "all_probabilities_in_0_1":
            probability_valid,

        "completion_plus_failure_equals_one":
            np.allclose(
                (
                    profiles[
                        "p_completed_rerun"
                    ]
                    +
                    profiles[
                        "p_no_completed_rerun"
                    ]
                ),
                1.0,
                atol=1e-12,
                rtol=0.0,
            ),

        "target_unconditional_not_above_completion":
            (
                profiles[
                    "p_target_unconditional"
                ]
                <=
                profiles[
                    "p_completed_rerun"
                ]
                + 1e-12
            ).all(),

        "target_gain_probability_monotonic":
            True,

        "no_historical_leaderboard_targets":
            not profiles[
                "historical_leaderboard_target"
            ].any(),

        "no_recommendation_enabled":
            not profiles[
                "recommendation_enabled"
            ].any(),

        "all_recommendations_not_issued":
            (
                profiles[
                    "recommendation"
                ]
                == "NOT_ISSUED"
            ).all(),

        "all_policy_hashes_present":
            profiles[
                "policy_hash"
            ].notna().all(),
    }

    # --------------------------------------------------------
    # Explicit monotonicity:
    # P(+0.10) >= P(+0.25) >= P(+0.50) >= P(+1.00)
    # within every scenario.
    # --------------------------------------------------------

    gain_profiles = profiles[
        profiles[
            "profile_type"
        ]
        == "TARGET_GAIN"
    ].copy()

    scenario_keys = [
        "current_retained_speed_mph",
        "baseline_group",
        "time_remaining_minutes",
        "wait_scenario_id",
    ]

    monotonic_ok = True

    for _, group in (
        gain_profiles.groupby(
            scenario_keys,
            dropna=False,
        )
    ):

        ordered = (
            group
            .sort_values(
                "required_gain_mph"
            )
        )

        probs = (
            ordered[
                "p_target_unconditional"
            ]
            .to_numpy(
                dtype=float
            )
        )

        if np.any(
            np.diff(
                probs
            )
            > 1e-12
        ):

            monotonic_ok = False
            break

    checks[
        "target_gain_probability_monotonic"
    ] = monotonic_ok

    # ========================================================
    # QA rows
    # ========================================================

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
                    "profile_rows",

                "value":
                    len(
                        profiles
                    ),

                "status":
                    "INFO",
            },

            {
                "metric":
                    "compact_target_rows",

                "value":
                    len(
                        compact
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
    # PRINT
    # ========================================================

    print()
    print("EMPIRICAL BRANCH EVENT RATES")
    print("-" * 120)

    print(
        branch_probabilities.to_string(
            index=False
        )
    )

    print()
    print(
        "TARGET-AWARE PROFILE SAMPLE — "
        "RETAINED 231 MPH, 60 MIN REMAINING"
    )
    print("-" * 190)

    sample = compact[
        (
            compact[
                "current_retained_speed_mph"
            ]
            == 231.0
        )
        &
        (
            compact[
                "time_remaining_minutes"
            ]
            == 60.0
        )
    ].copy()

    print(
        sample[
            [
                "baseline_group",
                "wait_scenario_id",
                "required_gain_mph",
                "absolute_target_speed_mph",
                "p_completed_rerun",
                "p_target_given_completed",
                "p_target_unconditional",
                "p_any_gain_given_completed",
                "p_improve_but_short_of_target_given_completed",
                "p_any_loss_given_completed",
                "expected_delta_given_completed_mph",
            ]
        ]
        .sort_values(
            [
                "baseline_group",
                "wait_scenario_id",
                "required_gain_mph",
            ]
        )
        .to_string(
            index=False
        )
    )

    print()
    print(
        "TARGET SUCCESS — "
        "231 MPH, +0.50 MPH REQUIRED"
    )
    print("-" * 160)

    target_example = compact[
        (
            compact[
                "current_retained_speed_mph"
            ]
            == 231.0
        )
        &
        (
            np.isclose(
                compact[
                    "required_gain_mph"
                ],
                0.50,
            )
        )
    ].copy()

    print(
        target_example[
            [
                "baseline_group",
                "time_remaining_minutes",
                "wait_scenario_id",
                "p_completed_rerun",
                "p_no_completed_rerun",
                "p_target_given_completed",
                "p_target_unconditional",
                "p_improve_but_short_of_target_given_completed",
                "p_any_loss_given_completed",
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

    PROFILE_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    profiles.to_csv(
        PROFILE_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    compact.to_csv(
        COMPACT_FILE,
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
        "# Target-Aware Retain / Withdraw Profiles V1"
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
        "Convert the frozen retain/withdraw Monte Carlo "
        "risk layer into target-aware success probabilities "
        "without introducing arbitrary utility weights."
    )

    report.append("")

    report.append(
        "## Gain targets"
    )

    report.append("")

    for threshold in (
        GAIN_THRESHOLDS_MPH
    ):

        report.append(
            f"- `+{threshold:.2f} mph`"
        )

    report.append("")

    report.append(
        "For any retained speed S and gain target G, "
        "the corresponding absolute target is S + G."
    )

    report.append("")

    report.append(
        "These are sensitivity targets, not reconstructed "
        "historical leaderboard thresholds."
    )

    report.append("")

    report.append(
        "## Combination rule"
    )

    report.append("")

    report.append(
        "`P(target success)` combines:"
    )

    report.append("")

    report.append(
        "- cutoff completion probability;"
    )

    report.append(
        "- baseline-condition recovery posterior mean;"
    )

    report.append(
        "- empirical normal-branch target rate;"
    )

    report.append(
        "- empirical recovery-like target rate."
    )

    report.append("")

    report.append(
        "## Decision outputs"
    )

    report.append("")

    report.append(
        "The profile reports target-success probability, "
        "ordinary improvement probability, short-of-target "
        "probability, completed-run downside, and no-completion risk."
    )

    report.append("")

    report.append(
        "## Recommendation boundary"
    )

    report.append("")

    report.append(
        "No retain/withdraw recommendation is issued."
    )

    report.append(
        "A final recommendation layer still requires either "
        "a defensible external objective or an explicitly "
        "frozen risk preference."
    )

    report.append("")

    report.append(
        "## Status"
    )

    report.append("")

    if all_pass:

        report.append(
            "**TARGET_AWARE_DECISION_PROFILES_READY**"
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
            "TARGET_AWARE_DECISION_PROFILES_READY"
        )

    else:

        print(
            "FINAL STATUS: REVIEW_REQUIRED"
        )

    print("=" * 100)

    print()
    print(
        "NO UTILITY FUNCTION WAS INTRODUCED."
    )

    print(
        "NO HISTORICAL LEADERBOARD TARGET WAS INVENTED."
    )

    print(
        "NO RETAIN/WITHDRAW RECOMMENDATION WAS ISSUED."
    )

    print()
    print("OUTPUTS")

    print(
        PROFILE_FILE
    )

    print(
        COMPACT_FILE
    )

    print(
        QA_FILE
    )

    print(
        REPORT_FILE
    )


if __name__ == "__main__":
    main()
