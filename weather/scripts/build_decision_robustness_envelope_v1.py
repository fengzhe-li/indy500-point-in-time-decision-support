from pathlib import Path
import hashlib
import json

import numpy as np
import pandas as pd


# ============================================================
# INPUTS
# ============================================================

UNCERTAINTY_FILE = Path(
    "weather/output/"
    "repeat_performance_uncertainty_rows_v1.csv"
)

TARGET_PROFILE_FILE = Path(
    "weather/output/"
    "retain_withdraw_target_aware_compact_v1.csv"
)

LOYO_PROFILE_FILE = Path(
    "weather/output/"
    "target_aware_loyo_profiles_v1.csv"
)

MC_FILE = Path(
    "weather/output/"
    "retain_withdraw_monte_carlo_scenario_results_v1.csv"
)


# ============================================================
# OUTPUTS
# ============================================================

PRIOR_SENSITIVITY_FILE = Path(
    "weather/output/"
    "decision_recovery_prior_sensitivity_v1.csv"
)

ROBUSTNESS_ENVELOPE_FILE = Path(
    "weather/output/"
    "decision_robustness_envelope_v1.csv"
)

ROBUSTNESS_SUMMARY_FILE = Path(
    "weather/output/"
    "decision_robustness_summary_v1.csv"
)

QA_FILE = Path(
    "weather/output/"
    "decision_robustness_envelope_v1_qa.csv"
)

REPORT_FILE = Path(
    "weather/output/"
    "decision_robustness_envelope_v1.md"
)


# ============================================================
# DESIGN
# ============================================================

POLICY_VERSION = (
    "DECISION_ROBUSTNESS_ENVELOPE_V1"
)

EXPECTED_UNCERTAINTY_ROWS = 39
EXPECTED_TARGET_PROFILE_ROWS = 480
EXPECTED_LOYO_PROFILE_ROWS = 24
EXPECTED_MC_ROWS = 120

PRIMARY_YEARS = [
    2020,
    2021,
    2023,
]

GAIN_THRESHOLDS_MPH = [
    0.10,
    0.25,
    0.50,
    1.00,
]

BASELINE_GROUPS = [
    "LOW_BASELINE",
    "AT_OR_ABOVE_BASELINE_MEDIAN",
]

# ------------------------------------------------------------
# Prior sensitivity only.
#
# V1 central policy remains Beta(1,1).
# These alternatives do not replace the frozen central prior.
# ------------------------------------------------------------

RECOVERY_PRIORS = [
    {
        "prior_id":
            "JEFFREYS_LIKE",

        "alpha":
            0.5,

        "beta":
            0.5,

        "central_policy":
            False,
    },
    {
        "prior_id":
            "UNIFORM_V1",

        "alpha":
            1.0,

        "beta":
            1.0,

        "central_policy":
            True,
    },
    {
        "prior_id":
            "MILD_SHRINKAGE",

        "alpha":
            2.0,

        "beta":
            2.0,

        "central_policy":
            False,
    },
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
    threshold,
):

    x = np.asarray(
        values,
        dtype=float,
    )

    if len(x) == 0:
        return np.nan

    return float(
        np.mean(
            x >= threshold
        )
    )


def beta_posterior_mean(
    successes,
    trials,
    alpha_prior,
    beta_prior,
):

    return float(
        (
            alpha_prior
            + successes
        )
        /
        (
            alpha_prior
            + beta_prior
            + trials
        )
    )


# ============================================================
# MAIN
# ============================================================

def main():

    uncertainty = read_required(
        UNCERTAINTY_FILE
    )

    target_profiles = read_required(
        TARGET_PROFILE_FILE
    )

    loyo_profiles = read_required(
        LOYO_PROFILE_FILE
    )

    mc = read_required(
        MC_FILE
    )

    print()
    print("=" * 100)
    print(
        "PHASE 7B — DECISION ROBUSTNESS / "
        "SENSITIVITY ENVELOPE V1"
    )
    print("=" * 100)

    # ========================================================
    # Validate inputs
    # ========================================================

    if len(
        uncertainty
    ) != EXPECTED_UNCERTAINTY_ROWS:

        raise RuntimeError(
            f"Expected {EXPECTED_UNCERTAINTY_ROWS} uncertainty rows, "
            f"got {len(uncertainty)}"
        )

    if len(
        target_profiles
    ) != EXPECTED_TARGET_PROFILE_ROWS:

        raise RuntimeError(
            f"Expected {EXPECTED_TARGET_PROFILE_ROWS} target rows, "
            f"got {len(target_profiles)}"
        )

    if len(
        loyo_profiles
    ) != EXPECTED_LOYO_PROFILE_ROWS:

        raise RuntimeError(
            f"Expected {EXPECTED_LOYO_PROFILE_ROWS} LOYO rows, "
            f"got {len(loyo_profiles)}"
        )

    if len(
        mc
    ) != EXPECTED_MC_ROWS:

        raise RuntimeError(
            f"Expected {EXPECTED_MC_ROWS} MC rows, "
            f"got {len(mc)}"
        )

    required_uncertainty = [
        "year",
        TARGET_DELTA_COLUMN,
        "diagnostic_recovery_like",
        "baseline_below_year_median",
    ]

    missing = [
        col
        for col in required_uncertainty
        if col not in uncertainty.columns
    ]

    if missing:

        raise RuntimeError(
            "Missing uncertainty columns: "
            + ", ".join(
                missing
            )
        )

    uncertainty = uncertainty.copy()

    uncertainty[
        "year"
    ] = numeric(
        uncertainty[
            "year"
        ]
    ).astype(int)

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

    uncertainty[
        "_low_baseline"
    ] = as_bool(
        uncertainty[
            "baseline_below_year_median"
        ]
    )

    normal = uncertainty[
        ~uncertainty[
            "_recovery"
        ]
    ].copy()

    recovery = uncertainty[
        uncertainty[
            "_recovery"
        ]
    ].copy()

    if len(
        normal
    ) != 35:

        raise RuntimeError(
            f"Expected 35 normal rows, got {len(normal)}"
        )

    if len(
        recovery
    ) != 4:

        raise RuntimeError(
            f"Expected 4 recovery rows, got {len(recovery)}"
        )

    # ========================================================
    # Branch target rates
    # ========================================================

    normal_target_rates = {}

    recovery_target_rates = {}

    for threshold in (
        GAIN_THRESHOLDS_MPH
    ):

        normal_target_rates[
            threshold
        ] = empirical_probability(
            normal[
                "_delta"
            ],
            threshold,
        )

        recovery_target_rates[
            threshold
        ] = empirical_probability(
            recovery[
                "_delta"
            ],
            threshold,
        )

    # ========================================================
    # Prior sensitivity
    # ========================================================

    prior_rows = []

    for baseline_group in (
        BASELINE_GROUPS
    ):

        if baseline_group == (
            "LOW_BASELINE"
        ):

            group_rows = uncertainty[
                uncertainty[
                    "_low_baseline"
                ]
            ]

        else:

            group_rows = uncertainty[
                ~uncertainty[
                    "_low_baseline"
                ]
            ]

        successes = int(
            group_rows[
                "_recovery"
            ].sum()
        )

        trials = len(
            group_rows
        )

        for prior in (
            RECOVERY_PRIORS
        ):

            p_recovery = (
                beta_posterior_mean(
                    successes=successes,
                    trials=trials,
                    alpha_prior=prior[
                        "alpha"
                    ],
                    beta_prior=prior[
                        "beta"
                    ],
                )
            )

            p_normal = (
                1.0
                - p_recovery
            )

            for threshold in (
                GAIN_THRESHOLDS_MPH
            ):

                p_target = (
                    p_normal
                    * normal_target_rates[
                        threshold
                    ]
                    +
                    p_recovery
                    * recovery_target_rates[
                        threshold
                    ]
                )

                prior_rows.append(
                    {
                        "baseline_group":
                            baseline_group,

                        "prior_id":
                            prior[
                                "prior_id"
                            ],

                        "prior_alpha":
                            prior[
                                "alpha"
                            ],

                        "prior_beta":
                            prior[
                                "beta"
                            ],

                        "central_policy":
                            prior[
                                "central_policy"
                            ],

                        "recovery_successes":
                            successes,

                        "recovery_trials":
                            trials,

                        "posterior_mean_recovery_probability":
                            p_recovery,

                        "required_gain_mph":
                            threshold,

                        "normal_branch_target_rate":
                            normal_target_rates[
                                threshold
                            ],

                        "recovery_branch_target_rate":
                            recovery_target_rates[
                                threshold
                            ],

                        "p_target_given_completed":
                            p_target,
                    }
                )

    prior_sensitivity = pd.DataFrame(
        prior_rows
    )

    # ========================================================
    # Prior envelope by baseline group + threshold
    # ========================================================

    prior_envelope_rows = []

    for (
        baseline_group,
        threshold,
    ), group in (
        prior_sensitivity.groupby(
            [
                "baseline_group",
                "required_gain_mph",
            ]
        )
    ):

        central = group[
            group[
                "central_policy"
            ]
        ]

        if len(
            central
        ) != 1:

            raise RuntimeError(
                "Expected exactly one central prior row."
            )

        central_probability = float(
            central[
                "p_target_given_completed"
            ].iloc[0]
        )

        values = group[
            "p_target_given_completed"
        ].to_numpy(
            dtype=float
        )

        prior_envelope_rows.append(
            {
                "baseline_group":
                    baseline_group,

                "required_gain_mph":
                    float(
                        threshold
                    ),

                "central_probability":
                    central_probability,

                "prior_sensitivity_min_probability":
                    float(
                        values.min()
                    ),

                "prior_sensitivity_max_probability":
                    float(
                        values.max()
                    ),

                "prior_sensitivity_range":
                    float(
                        values.max()
                        - values.min()
                    ),
            }
        )

    prior_envelope = pd.DataFrame(
        prior_envelope_rows
    )

    # ========================================================
    # LOYO envelope
    # ========================================================

    loyo_envelope_rows = []

    for (
        baseline_group,
        threshold,
    ), group in (
        loyo_profiles.groupby(
            [
                "baseline_group",
                "required_gain_mph",
            ]
        )
    ):

        values = numeric(
            group[
                "loyo_p_target_given_completed"
            ]
        ).dropna().to_numpy(
            dtype=float
        )

        full_values = numeric(
            group[
                "full_data_p_target_given_completed"
            ]
        ).dropna().unique()

        if len(
            full_values
        ) != 1:

            raise RuntimeError(
                "Unexpected full-data LOYO reference count."
            )

        loyo_envelope_rows.append(
            {
                "baseline_group":
                    baseline_group,

                "required_gain_mph":
                    float(
                        threshold
                    ),

                "full_data_probability":
                    float(
                        full_values[0]
                    ),

                "loyo_min_probability":
                    float(
                        values.min()
                    ),

                "loyo_max_probability":
                    float(
                        values.max()
                    ),

                "loyo_range":
                    float(
                        values.max()
                        - values.min()
                    ),
            }
        )

    loyo_envelope = pd.DataFrame(
        loyo_envelope_rows
    )

    # ========================================================
    # Combined robustness envelope
    #
    # Central = current V1 Beta(1,1) full-data probability
    #
    # Robust lower/upper here are descriptive sensitivity
    # bounds formed from:
    #
    # - full-data central
    # - LOYO min/max
    # - prior-sensitivity min/max
    #
    # This is NOT a confidence interval.
    # ========================================================

    envelope_base = (
        prior_envelope
        .merge(
            loyo_envelope,
            on=[
                "baseline_group",
                "required_gain_mph",
            ],
            how="inner",
            validate="one_to_one",
        )
    )

    if len(
        envelope_base
    ) != (
        len(
            BASELINE_GROUPS
        )
        * len(
            GAIN_THRESHOLDS_MPH
        )
    ):

        raise RuntimeError(
            "Unexpected envelope base row count."
        )

    envelope_base[
        "robustness_lower_given_completed"
    ] = envelope_base[
        [
            "central_probability",
            "loyo_min_probability",
            "prior_sensitivity_min_probability",
        ]
    ].min(
        axis=1
    )

    envelope_base[
        "robustness_upper_given_completed"
    ] = envelope_base[
        [
            "central_probability",
            "loyo_max_probability",
            "prior_sensitivity_max_probability",
        ]
    ].max(
        axis=1
    )

    envelope_base[
        "robustness_width_given_completed"
    ] = (
        envelope_base[
            "robustness_upper_given_completed"
        ]
        -
        envelope_base[
            "robustness_lower_given_completed"
        ]
    )

    envelope_base[
        "largest_sensitivity_source"
    ] = np.where(
        envelope_base[
            "loyo_range"
        ]
        >=
        envelope_base[
            "prior_sensitivity_range"
        ],
        "CROSS_YEAR_LOYO",
        "RECOVERY_PRIOR",
    )

    # ========================================================
    # Attach scenario completion / cutoff
    #
    # This transforms conditional target probability envelope
    # into unconditional decision-state envelope.
    # ========================================================

    required_profile = [
        "current_retained_speed_mph",
        "required_gain_mph",
        "baseline_group",
        "time_remaining_minutes",
        "wait_scenario_id",
        "p_completed_rerun",
        "p_no_completed_rerun",
        "p_target_given_completed",
        "p_target_unconditional",
        "p_any_gain_given_completed",
        "p_any_loss_given_completed",
        "expected_delta_given_completed_mph",
        "delta_q05_mph",
        "delta_q50_mph",
        "delta_q95_mph",
    ]

    missing = [
        col
        for col in required_profile
        if col not in target_profiles.columns
    ]

    if missing:

        raise RuntimeError(
            "Missing target profile fields: "
            + ", ".join(
                missing
            )
        )

    envelope = (
        target_profiles
        .merge(
            envelope_base,
            on=[
                "baseline_group",
                "required_gain_mph",
            ],
            how="left",
            validate="many_to_one",
        )
    )

    envelope[
        "robustness_lower_unconditional"
    ] = (
        numeric(
            envelope[
                "p_completed_rerun"
            ]
        )
        *
        numeric(
            envelope[
                "robustness_lower_given_completed"
            ]
        )
    )

    envelope[
        "robustness_upper_unconditional"
    ] = (
        numeric(
            envelope[
                "p_completed_rerun"
            ]
        )
        *
        numeric(
            envelope[
                "robustness_upper_given_completed"
            ]
        )
    )

    envelope[
        "central_unconditional_probability"
    ] = numeric(
        envelope[
            "p_target_unconditional"
        ]
    )

    envelope[
        "cutoff_state"
    ] = np.where(
        numeric(
            envelope[
                "p_completed_rerun"
            ]
        )
        == 0.0,
        "CUTOFF_BLOCKED",
        np.where(
            numeric(
                envelope[
                    "p_completed_rerun"
                ]
            )
            == 1.0,
            "COMPLETION_FEASIBLE_UNDER_SCENARIO",
            "PARTIAL_COMPLETION_PROBABILITY",
        ),
    )

    envelope[
        "probability_reporting_rule"
    ] = (
        "REPORT_CENTRAL_PLUS_SENSITIVITY_ENVELOPE;"
        "NOT_CONFIDENCE_INTERVAL"
    )

    envelope[
        "recommendation_enabled"
    ] = False

    envelope[
        "recommendation"
    ] = "NOT_ISSUED"

    # ========================================================
    # Compact robustness summary by baseline / target
    # ========================================================

    summary_rows = []

    for _, row in (
        envelope_base.iterrows()
    ):

        baseline_group = row[
            "baseline_group"
        ]

        threshold = float(
            row[
                "required_gain_mph"
            ]
        )

        relevant_prior = (
            prior_sensitivity[
                (
                    prior_sensitivity[
                        "baseline_group"
                    ]
                    == baseline_group
                )
                &
                (
                    np.isclose(
                        prior_sensitivity[
                            "required_gain_mph"
                        ],
                        threshold,
                    )
                )
            ]
        )

        recovery_probs = relevant_prior[
            "posterior_mean_recovery_probability"
        ].to_numpy(
            dtype=float
        )

        summary_rows.append(
            {
                "baseline_group":
                    baseline_group,

                "required_gain_mph":
                    threshold,

                "central_target_probability_given_completed":
                    row[
                        "central_probability"
                    ],

                "robustness_lower_given_completed":
                    row[
                        "robustness_lower_given_completed"
                    ],

                "robustness_upper_given_completed":
                    row[
                        "robustness_upper_given_completed"
                    ],

                "robustness_width_given_completed":
                    row[
                        "robustness_width_given_completed"
                    ],

                "loyo_min_probability":
                    row[
                        "loyo_min_probability"
                    ],

                "loyo_max_probability":
                    row[
                        "loyo_max_probability"
                    ],

                "prior_sensitivity_min_probability":
                    row[
                        "prior_sensitivity_min_probability"
                    ],

                "prior_sensitivity_max_probability":
                    row[
                        "prior_sensitivity_max_probability"
                    ],

                "recovery_posterior_mean_min_across_priors":
                    float(
                        recovery_probs.min()
                    ),

                "recovery_posterior_mean_max_across_priors":
                    float(
                        recovery_probs.max()
                    ),

                "largest_sensitivity_source":
                    row[
                        "largest_sensitivity_source"
                    ],

                "reporting_interpretation":
                    (
                        "DESCRIPTIVE_ROBUSTNESS_ENVELOPE;"
                        "NOT_CONFIDENCE_INTERVAL"
                    ),
            }
        )

    robustness_summary = pd.DataFrame(
        summary_rows
    )

    # ========================================================
    # Policy hash
    # ========================================================

    policy_payload = {
        "phase":
            "7B",

        "policy_version":
            POLICY_VERSION,

        "gain_thresholds_mph":
            GAIN_THRESHOLDS_MPH,

        "baseline_groups":
            BASELINE_GROUPS,

        "recovery_priors":
            RECOVERY_PRIORS,

        "central_prior":
            "Beta(1,1)",

        "cross_year_sensitivity":
            "LOYO_2020_2021_2023",

        "envelope_definition":
            (
                "min/max across central full-data, "
                "LOYO profiles, and recovery-prior sensitivity"
            ),

        "confidence_interval_claim":
            False,

        "recommendation_enabled":
            False,
    }

    policy_hash = stable_hash(
        policy_payload
    )

    prior_sensitivity[
        "policy_hash"
    ] = policy_hash

    robustness_summary[
        "policy_hash"
    ] = policy_hash

    envelope[
        "policy_hash"
    ] = policy_hash

    # ========================================================
    # QA
    # ========================================================

    expected_prior_rows = (
        len(
            BASELINE_GROUPS
        )
        * len(
            RECOVERY_PRIORS
        )
        * len(
            GAIN_THRESHOLDS_MPH
        )
    )

    expected_summary_rows = (
        len(
            BASELINE_GROUPS
        )
        * len(
            GAIN_THRESHOLDS_MPH
        )
    )

    probability_columns = [
        "central_unconditional_probability",
        "robustness_lower_unconditional",
        "robustness_upper_unconditional",
        "p_completed_rerun",
        "p_no_completed_rerun",
    ]

    prob_values = envelope[
        probability_columns
    ]

    all_probs_valid = (
        (
            prob_values
            >= 0
        )
        &
        (
            prob_values
            <= 1
        )
    ).all().all()

    checks = {
        "uncertainty_rows_equal_39":
            len(
                uncertainty
            )
            == 39,

        "normal_rows_equal_35":
            len(
                normal
            )
            == 35,

        "recovery_rows_equal_4":
            len(
                recovery
            )
            == 4,

        "target_profile_rows_equal_480":
            len(
                target_profiles
            )
            == 480,

        "loyo_profile_rows_equal_24":
            len(
                loyo_profiles
            )
            == 24,

        "prior_sensitivity_rows_match_expected":
            len(
                prior_sensitivity
            )
            == expected_prior_rows,

        "summary_rows_match_expected":
            len(
                robustness_summary
            )
            == expected_summary_rows,

        "envelope_rows_equal_target_profiles":
            len(
                envelope
            )
            == len(
                target_profiles
            ),

        "all_probabilities_in_0_1":
            all_probs_valid,

        "lower_not_above_central_when_completion_positive":
            (
                envelope[
                    "robustness_lower_unconditional"
                ]
                <=
                envelope[
                    "central_unconditional_probability"
                ]
                + 1e-12
            ).all(),

        "upper_not_below_central_when_completion_positive":
            (
                envelope[
                    "robustness_upper_unconditional"
                ]
                + 1e-12
                >=
                envelope[
                    "central_unconditional_probability"
                ]
            ).all(),

        "cutoff_blocked_rows_have_zero_unconditional_envelope":
            (
                envelope.loc[
                    envelope[
                        "cutoff_state"
                    ]
                    == "CUTOFF_BLOCKED",
                    [
                        "central_unconditional_probability",
                        "robustness_lower_unconditional",
                        "robustness_upper_unconditional",
                    ],
                ]
                == 0.0
            ).all().all(),

        "no_recommendation_enabled":
            not envelope[
                "recommendation_enabled"
            ].any(),

        "all_recommendations_not_issued":
            (
                envelope[
                    "recommendation"
                ]
                == "NOT_ISSUED"
            ).all(),

        "all_policy_hashes_present":
            (
                prior_sensitivity[
                    "policy_hash"
                ].notna().all()
                and
                robustness_summary[
                    "policy_hash"
                ].notna().all()
                and
                envelope[
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
                    "prior_sensitivity_rows",

                "value":
                    len(
                        prior_sensitivity
                    ),

                "status":
                    "INFO",
            },

            {
                "metric":
                    "robustness_summary_rows",

                "value":
                    len(
                        robustness_summary
                    ),

                "status":
                    "INFO",
            },

            {
                "metric":
                    "robustness_envelope_rows",

                "value":
                    len(
                        envelope
                    ),

                "status":
                    "INFO",
            },

            {
                "metric":
                    "max_conditional_robustness_width",

                "value":
                    float(
                        robustness_summary[
                            "robustness_width_given_completed"
                        ].max()
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
    print("RECOVERY PRIOR SENSITIVITY")
    print("-" * 150)

    print(
        prior_sensitivity[
            [
                "baseline_group",
                "prior_id",
                "recovery_successes",
                "recovery_trials",
                "posterior_mean_recovery_probability",
                "required_gain_mph",
                "p_target_given_completed",
            ]
        ]
        .sort_values(
            [
                "baseline_group",
                "required_gain_mph",
                "prior_id",
            ]
        )
        .to_string(
            index=False
        )
    )

    print()
    print("ROBUSTNESS SUMMARY")
    print("-" * 180)

    print(
        robustness_summary[
            [
                "baseline_group",
                "required_gain_mph",
                "central_target_probability_given_completed",
                "robustness_lower_given_completed",
                "robustness_upper_given_completed",
                "robustness_width_given_completed",
                "loyo_min_probability",
                "loyo_max_probability",
                "prior_sensitivity_min_probability",
                "prior_sensitivity_max_probability",
                "largest_sensitivity_source",
            ]
        ]
        .sort_values(
            [
                "baseline_group",
                "required_gain_mph",
            ]
        )
        .to_string(
            index=False
        )
    )

    print()
    print(
        "DECISION ENVELOPE SAMPLE — "
        "231 MPH, +0.50 MPH TARGET"
    )
    print("-" * 190)

    sample = envelope[
        (
            np.isclose(
                envelope[
                    "current_retained_speed_mph"
                ],
                231.0,
            )
        )
        &
        (
            np.isclose(
                envelope[
                    "required_gain_mph"
                ],
                0.50,
            )
        )
    ].copy()

    print(
        sample[
            [
                "baseline_group",
                "time_remaining_minutes",
                "wait_scenario_id",
                "p_completed_rerun",
                "p_no_completed_rerun",
                "central_unconditional_probability",
                "robustness_lower_unconditional",
                "robustness_upper_unconditional",
                "p_any_loss_given_completed",
                "expected_delta_given_completed_mph",
                "delta_q05_mph",
                "delta_q95_mph",
                "cutoff_state",
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
    print("MOST UNCERTAIN CONDITIONAL PROFILE")
    print("-" * 130)

    worst = robustness_summary.loc[
        robustness_summary[
            "robustness_width_given_completed"
        ].idxmax()
    ]

    print(
        worst.to_string()
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

    PRIOR_SENSITIVITY_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    prior_sensitivity.to_csv(
        PRIOR_SENSITIVITY_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    envelope.to_csv(
        ROBUSTNESS_ENVELOPE_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    robustness_summary.to_csv(
        ROBUSTNESS_SUMMARY_FILE,
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

    max_width = float(
        robustness_summary[
            "robustness_width_given_completed"
        ].max()
    )

    report = []

    report.append(
        "# Decision Robustness / Sensitivity Envelope V1"
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
        "Aggregate the major supported uncertainty "
        "diagnostics into a display-ready robustness envelope."
    )

    report.append("")

    report.append(
        "## Included sensitivity sources"
    )

    report.append("")

    report.append(
        "- leave-one-year-out performance / recovery recalibration;"
    )

    report.append(
        "- recovery Beta prior sensitivity;"
    )

    report.append(
        "- explicit wait scenarios;"
    )

    report.append(
        "- cutoff feasibility;"
    )

    report.append(
        "- target-gain level."
    )

    report.append("")

    report.append(
        "## Central policy"
    )

    report.append("")

    report.append(
        "The central estimate remains the frozen V1 "
        "full-data Beta(1,1) recovery mixture."
    )

    report.append("")

    report.append(
        "Alternative priors are used only for sensitivity analysis."
    )

    report.append("")

    report.append(
        "## Robustness envelope"
    )

    report.append("")

    report.append(
        "The lower and upper bounds are descriptive "
        "min/max sensitivity bounds across the central estimate, "
        "LOYO results, and recovery-prior sensitivity."
    )

    report.append("")

    report.append(
        "They are NOT frequentist confidence intervals "
        "and NOT Bayesian credible intervals."
    )

    report.append("")

    report.append(
        f"Maximum conditional envelope width: "
        f"`{max_width:.6f}`"
    )

    report.append("")

    report.append(
        "## Cutoff"
    )

    report.append("")

    report.append(
        "For cutoff-blocked scenarios the unconditional "
        "target-success probability and its envelope are zero."
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
        "The envelope is intended to expose robustness "
        "before any final risk policy is introduced."
    )

    report.append("")

    report.append(
        "## Status"
    )

    report.append("")

    if all_pass:

        report.append(
            "**DECISION_ROBUSTNESS_ENVELOPE_READY**"
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
            "DECISION_ROBUSTNESS_ENVELOPE_READY"
        )

    else:

        print(
            "FINAL STATUS: REVIEW_REQUIRED"
        )

    print("=" * 100)

    print()
    print(
        "NO MODEL WAS RETRAINED."
    )

    print(
        "NO WAIT SCENARIO WAS RELABELED "
        "AS HISTORICAL TRUTH."
    )

    print(
        "ROBUSTNESS BOUNDS ARE NOT "
        "CONFIDENCE INTERVALS."
    )

    print(
        "NO RETAIN/WITHDRAW RECOMMENDATION "
        "WAS ISSUED."
    )

    print()
    print("OUTPUTS")

    print(
        PRIOR_SENSITIVITY_FILE
    )

    print(
        ROBUSTNESS_ENVELOPE_FILE
    )

    print(
        ROBUSTNESS_SUMMARY_FILE
    )

    print(
        QA_FILE
    )

    print(
        REPORT_FILE
    )


if __name__ == "__main__":
    main()
