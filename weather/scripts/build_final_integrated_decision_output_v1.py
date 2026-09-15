from pathlib import Path
import hashlib
import json

import numpy as np
import pandas as pd


# ============================================================
# INPUTS
# ============================================================

ROBUSTNESS_ENVELOPE_FILE = Path(
    "weather/output/"
    "decision_robustness_envelope_v1.csv"
)

ROBUSTNESS_SUMMARY_FILE = Path(
    "weather/output/"
    "decision_robustness_summary_v1.csv"
)

QUEUE_POLICY_FILE = Path(
    "weather/output/"
    "queue_wait_uncertainty_policy_v1.csv"
)

DECISION_SEMANTICS_FILE = Path(
    "weather/output/"
    "retain_withdraw_decision_semantics_v1.csv"
)

UNCERTAINTY_ROWS_FILE = Path(
    "weather/output/"
    "repeat_performance_uncertainty_rows_v1.csv"
)


# ============================================================
# OUTPUTS
# ============================================================

FINAL_PROFILE_FILE = Path(
    "weather/output/"
    "final_integrated_decision_profiles_v1.csv"
)

FINAL_COMPACT_FILE = Path(
    "weather/output/"
    "final_integrated_decision_compact_v1.csv"
)

FINAL_METADATA_FILE = Path(
    "weather/output/"
    "final_integrated_decision_metadata_v1.csv"
)

QA_FILE = Path(
    "weather/output/"
    "final_integrated_decision_output_v1_qa.csv"
)

REPORT_FILE = Path(
    "weather/output/"
    "final_integrated_decision_output_v1.md"
)


# ============================================================
# DESIGN
# ============================================================

POLICY_VERSION = (
    "FINAL_INTEGRATED_DECISION_OUTPUT_V1"
)

EXPECTED_ENVELOPE_ROWS = 480
EXPECTED_ROBUSTNESS_SUMMARY_ROWS = 8
EXPECTED_UNCERTAINTY_ROWS = 39

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

WAIT_SCENARIOS = [
    "WAIT_05MIN",
    "WAIT_15MIN",
    "WAIT_30MIN",
    "WAIT_45MIN",
]

TIME_REMAINING_VALUES = [
    10.0,
    20.0,
    30.0,
    45.0,
    60.0,
]

RETAINED_SPEEDS = [
    229.0,
    231.0,
    233.0,
]


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


def pct(
    value,
):

    if pd.isna(
        value
    ):

        return None

    return float(
        value
        * 100.0
    )


def risk_band(
    p_no_completion,
    p_loss,
):

    if pd.isna(
        p_no_completion
    ):

        return "UNAVAILABLE"

    if p_no_completion >= 0.50:

        return "CUTOFF_DOMINATED"

    if p_no_completion > 0.0:

        return "CUTOFF_RISK_PRESENT"

    if pd.isna(
        p_loss
    ):

        return "COMPLETION_ONLY"

    if p_loss >= 0.40:

        return "HIGH_COMPLETED_RUN_DOWNSIDE"

    if p_loss >= 0.20:

        return "MODERATE_COMPLETED_RUN_DOWNSIDE"

    return "LOW_COMPLETED_RUN_DOWNSIDE"


def opportunity_band(
    central_probability,
):

    if pd.isna(
        central_probability
    ):

        return "UNAVAILABLE"

    if central_probability >= 0.60:

        return "HIGH_TARGET_OPPORTUNITY"

    if central_probability >= 0.35:

        return "MODERATE_TARGET_OPPORTUNITY"

    if central_probability > 0.0:

        return "LOW_TARGET_OPPORTUNITY"

    return "NO_TARGET_OPPORTUNITY_UNDER_SCENARIO"


# ============================================================
# MAIN
# ============================================================

def main():

    envelope = read_required(
        ROBUSTNESS_ENVELOPE_FILE
    )

    robustness_summary = read_required(
        ROBUSTNESS_SUMMARY_FILE
    )

    queue_policy = read_required(
        QUEUE_POLICY_FILE
    )

    semantics = read_required(
        DECISION_SEMANTICS_FILE
    )

    uncertainty = read_required(
        UNCERTAINTY_ROWS_FILE
    )

    print()
    print("=" * 100)
    print(
        "PHASE 8A — FINAL INTEGRATED "
        "DECISION OUTPUT LAYER V1"
    )
    print("=" * 100)

    # ========================================================
    # Validate inputs
    # ========================================================

    if len(
        envelope
    ) != EXPECTED_ENVELOPE_ROWS:

        raise RuntimeError(
            f"Expected {EXPECTED_ENVELOPE_ROWS} robustness-envelope rows, "
            f"got {len(envelope)}"
        )

    if len(
        robustness_summary
    ) != EXPECTED_ROBUSTNESS_SUMMARY_ROWS:

        raise RuntimeError(
            f"Expected {EXPECTED_ROBUSTNESS_SUMMARY_ROWS} robustness-summary rows, "
            f"got {len(robustness_summary)}"
        )

    if len(
        uncertainty
    ) != EXPECTED_UNCERTAINTY_ROWS:

        raise RuntimeError(
            f"Expected {EXPECTED_UNCERTAINTY_ROWS} uncertainty rows, "
            f"got {len(uncertainty)}"
        )

    required_envelope = [
        "current_retained_speed_mph",
        "required_gain_mph",
        "absolute_target_speed_mph",
        "baseline_group",
        "time_remaining_minutes",
        "wait_scenario_id",
        "p_completed_rerun",
        "p_no_completed_rerun",
        "central_unconditional_probability",
        "robustness_lower_unconditional",
        "robustness_upper_unconditional",
        "p_any_gain_given_completed",
        "p_any_loss_given_completed",
        "expected_delta_given_completed_mph",
        "delta_q05_mph",
        "delta_q50_mph",
        "delta_q95_mph",
        "cutoff_state",
        "largest_sensitivity_source",
        "recommendation_enabled",
        "recommendation",
    ]

    missing = [
        col
        for col in required_envelope
        if col not in envelope.columns
    ]

    if missing:

        raise RuntimeError(
            "Missing robustness-envelope fields: "
            + ", ".join(
                missing
            )
        )

    if as_bool(
        envelope[
            "recommendation_enabled"
        ]
    ).any():

        raise RuntimeError(
            "Input envelope unexpectedly enables recommendations."
        )

    if not (
        envelope[
            "recommendation"
        ].astype(str)
        == "NOT_ISSUED"
    ).all():

        raise RuntimeError(
            "Input envelope unexpectedly contains recommendations."
        )

    # ========================================================
    # Validate queue policy boundary
    # ========================================================

    queue_policy_lookup = {
        str(row["component"]):
            str(row["status"])
        for _, row
        in queue_policy.iterrows()
    }

    required_queue_policy = {
        "DIRECT_QUEUE_WAIT":
            "UNOBSERVED",

        "QUEUE_POSITION":
            "UNOBSERVED",

        "SESSION_CUTOFF_2024":
            "EXACT_SUPPORTED",

        "WITHDRAW_ACTION":
            "PROBABILISTIC",

        "NO_COMPLETED_RERUN_BEFORE_CUTOFF":
            "EXPLICIT_FAILURE_STATE",
    }

    for (
        component,
        expected_status,
    ) in required_queue_policy.items():

        actual_status = (
            queue_policy_lookup.get(
                component
            )
        )

        if actual_status != expected_status:

            raise RuntimeError(
                f"Queue policy mismatch for {component}: "
                f"expected {expected_status}, got {actual_status}"
            )

    # ========================================================
    # Validate recommendation boundary
    # ========================================================

    recommendation_rows = semantics[
        semantics[
            "decision_component"
        ].astype(str)
        == "RECOMMENDATION"
    ]

    if len(
        recommendation_rows
    ) != 1:

        raise RuntimeError(
            "Expected one RECOMMENDATION semantic row."
        )

    recommendation_allowed_use = str(
        recommendation_rows.iloc[0][
            "allowed_use"
        ]
    )

    if (
        recommendation_allowed_use
        != "NOT_ENABLED_IN_V1_SEMANTICS_FREEZE."
    ):

        raise RuntimeError(
            "Recommendation boundary changed unexpectedly."
        )

    # ========================================================
    # Evidence metadata
    # ========================================================

    uncertainty = uncertainty.copy()

    uncertainty[
        "_recovery"
    ] = as_bool(
        uncertainty[
            "diagnostic_recovery_like"
        ]
    )

    normal_rows = int(
        (
            ~uncertainty[
                "_recovery"
            ]
        ).sum()
    )

    recovery_rows = int(
        uncertainty[
            "_recovery"
        ].sum()
    )

    if normal_rows != 35:

        raise RuntimeError(
            f"Expected 35 normal rows, got {normal_rows}"
        )

    if recovery_rows != 4:

        raise RuntimeError(
            f"Expected 4 recovery rows, got {recovery_rows}"
        )

    # ========================================================
    # Policy hash
    # ========================================================

    policy_payload = {
        "phase":
            "8A",

        "policy_version":
            POLICY_VERSION,

        "retained_speeds":
            RETAINED_SPEEDS,

        "baseline_groups":
            BASELINE_GROUPS,

        "wait_scenarios":
            WAIT_SCENARIOS,

        "time_remaining_values":
            TIME_REMAINING_VALUES,

        "gain_thresholds_mph":
            GAIN_THRESHOLDS_MPH,

        "normal_rows":
            normal_rows,

        "recovery_rows":
            recovery_rows,

        "recommendation_enabled":
            False,

        "robustness_reporting":
            (
                "central + descriptive sensitivity envelope"
            ),
    }

    policy_hash = stable_hash(
        policy_payload
    )

    # ========================================================
    # Build integrated output
    # ========================================================

    output = envelope.copy()

    output[
        "central_target_success_probability"
    ] = numeric(
        output[
            "central_unconditional_probability"
        ]
    )

    output[
        "target_success_robustness_lower"
    ] = numeric(
        output[
            "robustness_lower_unconditional"
        ]
    )

    output[
        "target_success_robustness_upper"
    ] = numeric(
        output[
            "robustness_upper_unconditional"
        ]
    )

    output[
        "target_success_robustness_width"
    ] = (
        output[
            "target_success_robustness_upper"
        ]
        -
        output[
            "target_success_robustness_lower"
        ]
    )

    output[
        "central_target_success_pct"
    ] = (
        output[
            "central_target_success_probability"
        ]
        * 100.0
    )

    output[
        "robustness_lower_pct"
    ] = (
        output[
            "target_success_robustness_lower"
        ]
        * 100.0
    )

    output[
        "robustness_upper_pct"
    ] = (
        output[
            "target_success_robustness_upper"
        ]
        * 100.0
    )

    output[
        "completion_probability_pct"
    ] = (
        numeric(
            output[
                "p_completed_rerun"
            ]
        )
        * 100.0
    )

    output[
        "no_completion_probability_pct"
    ] = (
        numeric(
            output[
                "p_no_completed_rerun"
            ]
        )
        * 100.0
    )

    output[
        "any_gain_given_completed_pct"
    ] = (
        numeric(
            output[
                "p_any_gain_given_completed"
            ]
        )
        * 100.0
    )

    output[
        "any_loss_given_completed_pct"
    ] = (
        numeric(
            output[
                "p_any_loss_given_completed"
            ]
        )
        * 100.0
    )

    # ========================================================
    # Descriptive profile bands
    #
    # These are labels for presentation only.
    # They do NOT choose retain/withdraw.
    # ========================================================

    output[
        "opportunity_band"
    ] = output[
        "central_target_success_probability"
    ].apply(
        opportunity_band
    )

    output[
        "risk_band"
    ] = [
        risk_band(
            p_no_completion=row[
                "p_no_completed_rerun"
            ],
            p_loss=row[
                "p_any_loss_given_completed"
            ],
        )
        for _, row in output.iterrows()
    ]

    # ========================================================
    # Evidence caveats
    # ========================================================

    output[
        "queue_wait_evidence_caveat"
    ] = (
        "WAIT_SCENARIO_IS_SENSITIVITY_ASSUMPTION;"
        "NOT_HISTORICAL_QUEUE_WAIT_ESTIMATE"
    )

    output[
        "queue_position_evidence_caveat"
    ] = (
        "EXACT_HISTORICAL_LANE_QUEUE_STATE_UNOBSERVED"
    )

    output[
        "performance_evidence_caveat"
    ] = (
        f"NORMAL_EMPIRICAL_ROWS_{normal_rows};"
        f"RECOVERY_LIKE_ROWS_{recovery_rows}"
    )

    output[
        "recovery_evidence_caveat"
    ] = (
        "RECOVERY_LIKE_LABEL_IS_DIAGNOSTIC;"
        "NOT_CAUSAL_GROUND_TRUTH"
    )

    output[
        "robustness_evidence_caveat"
    ] = (
        "ROBUSTNESS_RANGE_IS_DESCRIPTIVE_SENSITIVITY_ENVELOPE;"
        "NOT_CONFIDENCE_INTERVAL"
    )

    output[
        "baseline_group_caveat"
    ] = (
        "BASELINE_GROUP_IS_RETROSPECTIVE_DIAGNOSTIC_CONDITION;"
        "DEPLOYMENT_REQUIRES_PRE_DECISION_OBSERVABLE_MAPPING"
    )

    output[
        "leaderboard_caveat"
    ] = (
        "NO_HISTORICAL_LEADERBOARD_THRESHOLD_ASSUMED"
    )

    output[
        "recommendation_caveat"
    ] = (
        "NO_ACTION_RECOMMENDATION_WITHOUT_EXPLICIT_OBJECTIVE_"
        "OR_RISK_POLICY"
    )

    # ========================================================
    # Integrated status
    # ========================================================

    output[
        "decision_profile_status"
    ] = np.where(
        output[
            "cutoff_state"
        ]
        == "CUTOFF_BLOCKED",
        "NO_RERUN_COMPLETION_UNDER_WAIT_SCENARIO",
        "TARGET_AWARE_RISK_PROFILE_AVAILABLE",
    )

    output[
        "recommendation_enabled"
    ] = False

    output[
        "recommendation"
    ] = "NOT_ISSUED"

    output[
        "final_policy_hash"
    ] = policy_hash

    # ========================================================
    # Compact output
    # ========================================================

    compact_columns = [
        "current_retained_speed_mph",
        "required_gain_mph",
        "absolute_target_speed_mph",
        "baseline_group",
        "time_remaining_minutes",
        "wait_scenario_id",
        "p_completed_rerun",
        "p_no_completed_rerun",
        "central_target_success_probability",
        "target_success_robustness_lower",
        "target_success_robustness_upper",
        "p_any_gain_given_completed",
        "p_any_loss_given_completed",
        "expected_delta_given_completed_mph",
        "delta_q05_mph",
        "delta_q50_mph",
        "delta_q95_mph",
        "cutoff_state",
        "opportunity_band",
        "risk_band",
        "largest_sensitivity_source",
        "decision_profile_status",
        "recommendation",
        "final_policy_hash",
    ]

    compact = output[
        compact_columns
    ].copy()

    # ========================================================
    # Metadata
    # ========================================================

    metadata_rows = [
        {
            "metadata_key":
                "policy_version",

            "metadata_value":
                POLICY_VERSION,
        },

        {
            "metadata_key":
                "policy_hash",

            "metadata_value":
                policy_hash,
        },

        {
            "metadata_key":
                "profile_rows",

            "metadata_value":
                len(
                    output
                ),
        },

        {
            "metadata_key":
                "normal_empirical_rows",

            "metadata_value":
                normal_rows,
        },

        {
            "metadata_key":
                "recovery_like_empirical_rows",

            "metadata_value":
                recovery_rows,
        },

        {
            "metadata_key":
                "historical_queue_wait_observed",

            "metadata_value":
                False,
        },

        {
            "metadata_key":
                "historical_exact_queue_position_observed",

            "metadata_value":
                False,
        },

        {
            "metadata_key":
                "robustness_interval_type",

            "metadata_value":
                "DESCRIPTIVE_SENSITIVITY_ENVELOPE",
        },

        {
            "metadata_key":
                "confidence_interval_claim",

            "metadata_value":
                False,
        },

        {
            "metadata_key":
                "recommendation_enabled",

            "metadata_value":
                False,
        },

        {
            "metadata_key":
                "historical_leaderboard_target_assumed",

            "metadata_value":
                False,
        },

        {
            "metadata_key":
                "deployment_note",

            "metadata_value":
                (
                    "BASELINE_GROUP_REQUIRES_PRE_DECISION_"
                    "OBSERVABLE_MAPPING_BEFORE_LIVE_USE"
                ),
        },
    ]

    metadata = pd.DataFrame(
        metadata_rows
    )

    # ========================================================
    # QA
    # ========================================================

    expected_unique_scenario_combinations = (
        len(
            RETAINED_SPEEDS
        )
        * len(
            BASELINE_GROUPS
        )
        * len(
            TIME_REMAINING_VALUES
        )
        * len(
            WAIT_SCENARIOS
        )
        * len(
            GAIN_THRESHOLDS_MPH
        )
    )

    key_columns = [
        "current_retained_speed_mph",
        "baseline_group",
        "time_remaining_minutes",
        "wait_scenario_id",
        "required_gain_mph",
    ]

    probability_columns = [
        "p_completed_rerun",
        "p_no_completed_rerun",
        "central_target_success_probability",
        "target_success_robustness_lower",
        "target_success_robustness_upper",
        "p_any_gain_given_completed",
        "p_any_loss_given_completed",
    ]

    probability_values = output[
        probability_columns
    ]

    probabilities_valid = (
        (
            probability_values
            >= 0
        )
        &
        (
            probability_values
            <= 1
        )
    ).all().all()

    checks = {
        "output_rows_equal_480":
            len(
                output
            )
            == 480,

        "compact_rows_equal_480":
            len(
                compact
            )
            == 480,

        "unique_scenario_keys_equal_expected":
            (
                output[
                    key_columns
                ]
                .drop_duplicates()
                .shape[0]
                == expected_unique_scenario_combinations
            ),

        "no_duplicate_scenario_keys":
            not output[
                key_columns
            ].duplicated().any(),

        "all_probabilities_in_0_1":
            probabilities_valid,

        "completion_plus_failure_equals_one":
            np.allclose(
                (
                    numeric(
                        output[
                            "p_completed_rerun"
                        ]
                    )
                    +
                    numeric(
                        output[
                            "p_no_completed_rerun"
                        ]
                    )
                ),
                1.0,
                atol=1e-12,
                rtol=0.0,
            ),

        "robustness_lower_not_above_central":
            (
                output[
                    "target_success_robustness_lower"
                ]
                <=
                output[
                    "central_target_success_probability"
                ]
                + 1e-12
            ).all(),

        "robustness_upper_not_below_central":
            (
                output[
                    "target_success_robustness_upper"
                ]
                + 1e-12
                >=
                output[
                    "central_target_success_probability"
                ]
            ).all(),

        "cutoff_blocked_target_probability_zero":
            (
                output.loc[
                    output[
                        "cutoff_state"
                    ]
                    == "CUTOFF_BLOCKED",
                    "central_target_success_probability",
                ]
                == 0.0
            ).all(),

        "cutoff_blocked_robustness_zero":
            (
                output.loc[
                    output[
                        "cutoff_state"
                    ]
                    == "CUTOFF_BLOCKED",
                    [
                        "target_success_robustness_lower",
                        "target_success_robustness_upper",
                    ],
                ]
                == 0.0
            ).all().all(),

        "no_recommendation_enabled":
            not output[
                "recommendation_enabled"
            ].any(),

        "all_recommendations_not_issued":
            (
                output[
                    "recommendation"
                ]
                == "NOT_ISSUED"
            ).all(),

        "all_caveats_present":
            (
                output[
                    [
                        "queue_wait_evidence_caveat",
                        "queue_position_evidence_caveat",
                        "performance_evidence_caveat",
                        "recovery_evidence_caveat",
                        "robustness_evidence_caveat",
                        "baseline_group_caveat",
                        "leaderboard_caveat",
                        "recommendation_caveat",
                    ]
                ]
                .notna()
                .all()
                .all()
            ),

        "all_final_policy_hashes_present":
            output[
                "final_policy_hash"
            ].notna().all(),
    }

    qa_rows = []

    for (
        metric,
        passed,
    ) in checks.items():

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

    cutoff_blocked_rows = int(
        (
            output[
                "cutoff_state"
            ]
            == "CUTOFF_BLOCKED"
        ).sum()
    )

    feasible_rows = int(
        (
            output[
                "cutoff_state"
            ]
            == "COMPLETION_FEASIBLE_UNDER_SCENARIO"
        ).sum()
    )

    qa_rows.extend(
        [
            {
                "metric":
                    "final_profile_rows",

                "value":
                    len(
                        output
                    ),

                "status":
                    "INFO",
            },

            {
                "metric":
                    "cutoff_blocked_rows",

                "value":
                    cutoff_blocked_rows,

                "status":
                    "INFO",
            },

            {
                "metric":
                    "completion_feasible_rows",

                "value":
                    feasible_rows,

                "status":
                    "INFO",
            },

            {
                "metric":
                    "normal_empirical_rows",

                "value":
                    normal_rows,

                "status":
                    "INFO",
            },

            {
                "metric":
                    "recovery_like_empirical_rows",

                "value":
                    recovery_rows,

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
    print("FINAL OUTPUT SCHEMA SUMMARY")
    print("-" * 120)

    print(
        "Rows:",
        len(
            output
        )
    )

    print(
        "Retained speeds:",
        sorted(
            output[
                "current_retained_speed_mph"
            ].unique()
        )
    )

    print(
        "Baseline groups:",
        sorted(
            output[
                "baseline_group"
            ].astype(str)
            .unique()
        )
    )

    print(
        "Gain thresholds:",
        sorted(
            output[
                "required_gain_mph"
            ].unique()
        )
    )

    print(
        "Time remaining states:",
        sorted(
            output[
                "time_remaining_minutes"
            ].unique()
        )
    )

    print(
        "Wait scenarios:",
        sorted(
            output[
                "wait_scenario_id"
            ].astype(str)
            .unique()
        )
    )

    print()
    print(
        "FINAL INTEGRATED SAMPLE — "
        "231 MPH, +0.50 MPH TARGET"
    )
    print("-" * 190)

    sample = compact[
        (
            np.isclose(
                compact[
                    "current_retained_speed_mph"
                ],
                231.0,
            )
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
        sample[
            [
                "baseline_group",
                "time_remaining_minutes",
                "wait_scenario_id",
                "p_completed_rerun",
                "p_no_completed_rerun",
                "central_target_success_probability",
                "target_success_robustness_lower",
                "target_success_robustness_upper",
                "p_any_gain_given_completed",
                "p_any_loss_given_completed",
                "expected_delta_given_completed_mph",
                "delta_q05_mph",
                "delta_q50_mph",
                "delta_q95_mph",
                "opportunity_band",
                "risk_band",
                "largest_sensitivity_source",
                "cutoff_state",
                "recommendation",
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
        "DISPLAY EXAMPLE — "
        "LOW BASELINE, 231 MPH, +0.50 MPH, "
        "60 MIN, WAIT_15MIN"
    )
    print("-" * 130)

    display_example = compact[
        (
            np.isclose(
                compact[
                    "current_retained_speed_mph"
                ],
                231.0,
            )
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
        &
        (
            compact[
                "baseline_group"
            ]
            == "LOW_BASELINE"
        )
        &
        (
            np.isclose(
                compact[
                    "time_remaining_minutes"
                ],
                60.0,
            )
        )
        &
        (
            compact[
                "wait_scenario_id"
            ]
            == "WAIT_15MIN"
        )
    ]

    if len(
        display_example
    ) != 1:

        raise RuntimeError(
            "Expected one display example row."
        )

    row = display_example.iloc[0]

    print(
        f"Current retained speed: "
        f"{row['current_retained_speed_mph']:.3f} mph"
    )

    print(
        f"Required gain: "
        f"+{row['required_gain_mph']:.3f} mph"
    )

    print(
        f"Target speed: "
        f"{row['absolute_target_speed_mph']:.3f} mph"
    )

    print(
        f"Completion probability: "
        f"{row['p_completed_rerun'] * 100:.1f}%"
    )

    print(
        f"Central target-success probability: "
        f"{row['central_target_success_probability'] * 100:.1f}%"
    )

    print(
        f"Robustness envelope: "
        f"{row['target_success_robustness_lower'] * 100:.1f}%"
        f" – "
        f"{row['target_success_robustness_upper'] * 100:.1f}%"
    )

    print(
        f"Any improvement if completed: "
        f"{row['p_any_gain_given_completed'] * 100:.1f}%"
    )

    print(
        f"Any completed-run loss: "
        f"{row['p_any_loss_given_completed'] * 100:.1f}%"
    )

    print(
        f"Expected delta if completed: "
        f"{row['expected_delta_given_completed_mph']:+.3f} mph"
    )

    print(
        f"Delta q05 / median / q95: "
        f"{row['delta_q05_mph']:+.3f} / "
        f"{row['delta_q50_mph']:+.3f} / "
        f"{row['delta_q95_mph']:+.3f} mph"
    )

    print(
        f"Dominant sensitivity: "
        f"{row['largest_sensitivity_source']}"
    )

    print(
        f"Cutoff state: "
        f"{row['cutoff_state']}"
    )

    print(
        "Recommendation: NOT_ISSUED"
    )

    print()
    print("GLOBAL CAVEATS")
    print("-" * 120)

    print(
        "1. Queue wait remains a sensitivity scenario, "
        "not a reconstructed historical truth."
    )

    print(
        "2. Exact historical queue position is unavailable."
    )

    print(
        f"3. Repeat-performance empirical sample: "
        f"{normal_rows} normal + {recovery_rows} recovery-like rows."
    )

    print(
        "4. Recovery-like labels are diagnostic, not causal."
    )

    print(
        "5. Robustness bounds are sensitivity envelopes, "
        "not confidence intervals."
    )

    print(
        "6. LOW/HIGH baseline condition is retrospective "
        "and needs a pre-decision observable mapping before live use."
    )

    print(
        "7. No historical leaderboard cutoff is assumed."
    )

    print(
        "8. No retain/withdraw recommendation is issued "
        "without explicit objective or risk policy."
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
    # WRITE OUTPUTS
    # ========================================================

    FINAL_PROFILE_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output.to_csv(
        FINAL_PROFILE_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    compact.to_csv(
        FINAL_COMPACT_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    metadata.to_csv(
        FINAL_METADATA_FILE,
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
        "# Final Integrated Decision Output V1"
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
        "Provide a final consumer-facing decision profile "
        "that integrates target success, completion risk, "
        "repeat-performance uncertainty, and robustness sensitivity."
    )

    report.append("")

    report.append(
        "## Inputs"
    )

    report.append("")

    report.append(
        "- current retained speed;"
    )

    report.append(
        "- required gain / target speed;"
    )

    report.append(
        "- baseline condition;"
    )

    report.append(
        "- time remaining;"
    )

    report.append(
        "- latent pre-run-delay sensitivity scenario."
    )

    report.append("")

    report.append(
        "## Outputs"
    )

    report.append("")

    report.append(
        "- completion probability;"
    )

    report.append(
        "- no-completion probability;"
    )

    report.append(
        "- central target-success probability;"
    )

    report.append(
        "- robustness lower / upper sensitivity envelope;"
    )

    report.append(
        "- probability of any completed-run improvement;"
    )

    report.append(
        "- probability of completed-run loss;"
    )

    report.append(
        "- expected repeat-attempt delta;"
    )

    report.append(
        "- q05 / median / q95 repeat-attempt delta;"
    )

    report.append(
        "- cutoff state;"
    )

    report.append(
        "- dominant sensitivity source."
    )

    report.append("")

    report.append(
        "## Evidence boundaries"
    )

    report.append("")

    report.append(
        "Historical individual queue wait is not observed."
    )

    report.append(
        "Historical exact queue position is not observed."
    )

    report.append(
        f"Repeat performance uncertainty is based on "
        f"`{normal_rows}` normal and `{recovery_rows}` "
        f"recovery-like empirical rows."
    )

    report.append(
        "Recovery-like labels are diagnostic rather than causal."
    )

    report.append(
        "Robustness bounds are descriptive sensitivity envelopes, "
        "not confidence intervals."
    )

    report.append(
        "The baseline-condition grouping is retrospective and "
        "requires a pre-decision observable mapping before live deployment."
    )

    report.append(
        "No historical leaderboard target is assumed."
    )

    report.append("")

    report.append(
        "## Recommendation boundary"
    )

    report.append("")

    report.append(
        "No retain/withdraw action recommendation is issued in V1."
    )

    report.append(
        "Recommendation requires an explicit target objective "
        "and/or an explicitly frozen risk-preference policy."
    )

    report.append("")

    report.append(
        "## Status"
    )

    report.append("")

    if all_pass:

        report.append(
            "**FINAL_INTEGRATED_DECISION_OUTPUT_READY**"
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
            "FINAL_INTEGRATED_DECISION_OUTPUT_READY"
        )

    else:

        print(
            "FINAL STATUS: REVIEW_REQUIRED"
        )

    print("=" * 100)

    print()
    print(
        "THE CORE DECISION PROFILE PIPELINE "
        "IS NOW INTEGRATED."
    )

    print(
        "NO HARD RETAIN/WITHDRAW RECOMMENDATION "
        "WAS ISSUED."
    )

    print(
        "NO HISTORICAL QUEUE WAIT OR LEADERBOARD "
        "STATE WAS INVENTED."
    )

    print()
    print("OUTPUTS")

    print(
        FINAL_PROFILE_FILE
    )

    print(
        FINAL_COMPACT_FILE
    )

    print(
        FINAL_METADATA_FILE
    )

    print(
        QA_FILE
    )

    print(
        REPORT_FILE
    )


if __name__ == "__main__":
    main()
