from pathlib import Path
import hashlib
import json

import numpy as np
import pandas as pd


# ============================================================
# INPUTS
# ============================================================

MONTE_CARLO_RESULTS_FILE = Path(
    "weather/output/"
    "retain_withdraw_monte_carlo_scenario_results_v1.csv"
)

UNCERTAINTY_ROWS_FILE = Path(
    "weather/output/"
    "repeat_performance_uncertainty_rows_v1.csv"
)

QUEUE_POLICY_FILE = Path(
    "weather/output/"
    "queue_wait_uncertainty_policy_v1.csv"
)


# ============================================================
# OUTPUTS
# ============================================================

SEMANTICS_FILE = Path(
    "weather/output/"
    "retain_withdraw_decision_semantics_v1.csv"
)

THRESHOLD_POLICY_FILE = Path(
    "weather/output/"
    "retain_withdraw_threshold_policy_v1.csv"
)

SCENARIO_CLASSIFICATION_FILE = Path(
    "weather/output/"
    "retain_withdraw_scenario_classification_v1.csv"
)

QA_FILE = Path(
    "weather/output/"
    "retain_withdraw_decision_semantics_v1_qa.csv"
)

REPORT_FILE = Path(
    "weather/output/"
    "retain_withdraw_decision_semantics_v1.md"
)


# ============================================================
# DESIGN
# ============================================================

POLICY_ID = (
    "RETAIN_WITHDRAW_DECISION_SEMANTICS_V1"
)

POLICY_VERSION = (
    "RETAIN_WITHDRAW_DECISION_SEMANTICS_FREEZE_V1"
)

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

EXPECTED_MC_ROWS = 120

EXPECTED_NORMAL_ROWS = 35
EXPECTED_RECOVERY_ROWS = 4


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


# ============================================================
# MAIN
# ============================================================

def main():

    mc = read_required(
        MONTE_CARLO_RESULTS_FILE
    )

    uncertainty = read_required(
        UNCERTAINTY_ROWS_FILE
    )

    queue_policy = read_required(
        QUEUE_POLICY_FILE
    )

    print()
    print("=" * 100)
    print(
        "PHASE 6D — RETAIN / WITHDRAW "
        "DECISION SEMANTICS FREEZE V1"
    )
    print("=" * 100)

    # ========================================================
    # Validate Phase 6C
    # ========================================================

    required_mc = [
        "current_retained_speed_mph",
        "baseline_group",
        "time_remaining_minutes",
        "wait_scenario_id",
        "p_completed_rerun",
        "p_no_completed_rerun",
        "p_improve_unconditional",
        "p_improve_given_completed",
        "p_slower_given_completed",
        "expected_delta_given_completed_mph",
        "delta_q05_mph",
        "delta_q50_mph",
        "delta_q95_mph",
        "utility_function_applied",
        "leaderboard_target_applied",
        "queue_wait_historical_claim",
    ]

    missing = [
        col
        for col in required_mc
        if col not in mc.columns
    ]

    if missing:

        raise RuntimeError(
            "Missing Monte Carlo columns: "
            + ", ".join(
                missing
            )
        )

    if len(
        mc
    ) != EXPECTED_MC_ROWS:

        raise RuntimeError(
            f"Expected {EXPECTED_MC_ROWS} Monte Carlo rows, "
            f"got {len(mc)}"
        )

    if as_bool(
        mc[
            "utility_function_applied"
        ]
    ).any():

        raise RuntimeError(
            "Phase 6C unexpectedly contains utility semantics."
        )

    if as_bool(
        mc[
            "leaderboard_target_applied"
        ]
    ).any():

        raise RuntimeError(
            "Phase 6C unexpectedly contains leaderboard target."
        )

    if as_bool(
        mc[
            "queue_wait_historical_claim"
        ]
    ).any():

        raise RuntimeError(
            "Phase 6C contains forbidden queue-wait claim."
        )

    # ========================================================
    # Validate empirical uncertainty rows
    # ========================================================

    required_uncertainty = [
        "target_speed_delta_vs_best_prior_mph",
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
        "_delta"
    ] = numeric(
        uncertainty[
            "target_speed_delta_vs_best_prior_mph"
        ]
    )

    uncertainty[
        "_recovery"
    ] = as_bool(
        uncertainty[
            "diagnostic_recovery_like"
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
    ) != EXPECTED_NORMAL_ROWS:

        raise RuntimeError(
            f"Expected {EXPECTED_NORMAL_ROWS} normal rows, "
            f"got {len(normal)}"
        )

    if len(
        recovery
    ) != EXPECTED_RECOVERY_ROWS:

        raise RuntimeError(
            f"Expected {EXPECTED_RECOVERY_ROWS} recovery rows, "
            f"got {len(recovery)}"
        )

    # ========================================================
    # Decision semantics
    # ========================================================

    semantics_rows = [
        {
            "policy_id":
                POLICY_ID,

            "decision_component":
                "RETAIN",

            "semantic_type":
                "ACTION",

            "definition":
                (
                    "Preserve the current retained qualifying result."
                ),

            "observable":
                True,

            "probabilistic":
                False,

            "utility_assigned":
                False,

            "leaderboard_required":
                False,

            "allowed_use":
                (
                    "Deterministic baseline branch."
                ),
        },

        {
            "policy_id":
                POLICY_ID,

            "decision_component":
                "WITHDRAW",

            "semantic_type":
                "ACTION",

            "definition":
                (
                    "Forfeit the current retained result and "
                    "enter the probabilistic rerun branch."
                ),

            "observable":
                True,

            "probabilistic":
                True,

            "utility_assigned":
                False,

            "leaderboard_required":
                False,

            "allowed_use":
                (
                    "Monte Carlo risk-profile branch."
                ),
        },

        {
            "policy_id":
                POLICY_ID,

            "decision_component":
                "NO_COMPLETED_RERUN",

            "semantic_type":
                "OUTCOME",

            "definition":
                (
                    "Withdrawal occurs but no qualifying rerun "
                    "is completed before the supported session cutoff."
                ),

            "observable":
                False,

            "probabilistic":
                True,

            "utility_assigned":
                False,

            "leaderboard_required":
                False,

            "allowed_use":
                (
                    "Explicit downside probability. "
                    "Must not silently be converted to zero speed."
                ),
        },

        {
            "policy_id":
                POLICY_ID,

            "decision_component":
                "SPEED_IMPROVEMENT",

            "semantic_type":
                "OUTCOME",

            "definition":
                (
                    "Completed rerun speed exceeds current "
                    "retained speed."
                ),

            "observable":
                False,

            "probabilistic":
                True,

            "utility_assigned":
                False,

            "leaderboard_required":
                False,

            "allowed_use":
                (
                    "Probability and magnitude reporting."
                ),
        },

        {
            "policy_id":
                POLICY_ID,

            "decision_component":
                "TARGET_GAIN",

            "semantic_type":
                "THRESHOLD_OUTCOME",

            "definition":
                (
                    "Completed rerun improves by at least "
                    "a user- or scenario-specified mph threshold."
                ),

            "observable":
                False,

            "probabilistic":
                True,

            "utility_assigned":
                False,

            "leaderboard_required":
                False,

            "allowed_use":
                (
                    "Utility-free target-success probability."
                ),
        },

        {
            "policy_id":
                POLICY_ID,

            "decision_component":
                "ABSOLUTE_TARGET_SPEED",

            "semantic_type":
                "DERIVED_THRESHOLD",

            "definition":
                (
                    "If an external target speed T is known, "
                    "required gain = T - current retained speed."
                ),

            "observable":
                False,

            "probabilistic":
                True,

            "utility_assigned":
                False,

            "leaderboard_required":
                True,

            "allowed_use":
                (
                    "May be applied only when target speed is "
                    "externally supplied or defensibly reconstructed."
                ),
        },

        {
            "policy_id":
                POLICY_ID,

            "decision_component":
                "RECOMMENDATION",

            "semantic_type":
                "DECISION_OUTPUT",

            "definition":
                (
                    "Choose retain or withdraw."
                ),

            "observable":
                False,

            "probabilistic":
                False,

            "utility_assigned":
                False,

            "leaderboard_required":
                True,

            "allowed_use":
                (
                    "NOT_ENABLED_IN_V1_SEMANTICS_FREEZE."
                ),
        },
    ]

    semantics = pd.DataFrame(
        semantics_rows
    )

    # ========================================================
    # Threshold policy
    # ========================================================

    threshold_rows = []

    for threshold in GAIN_THRESHOLDS_MPH:

        threshold_rows.append(
            {
                "threshold_type":
                    "GAIN_AT_LEAST",

                "threshold_mph":
                    float(
                        threshold
                    ),

                "mathematical_rule":
                    (
                        f"delta_mph >= {threshold:.2f}"
                    ),

                "interpretation":
                    (
                        f"Probability rerun gains at least "
                        f"{threshold:.2f} mph."
                    ),

                "requires_leaderboard":
                    False,

                "historical_claim":
                    False,

                "utility_weight":
                    np.nan,

                "use":
                    "SENSITIVITY_TARGET",
            }
        )

    for threshold in LOSS_THRESHOLDS_MPH:

        threshold_rows.append(
            {
                "threshold_type":
                    "LOSS_AT_MOST",

                "threshold_mph":
                    float(
                        threshold
                    ),

                "mathematical_rule":
                    (
                        f"delta_mph <= {threshold:.2f}"
                    ),

                "interpretation":
                    (
                        f"Probability completed rerun loses at least "
                        f"{abs(threshold):.2f} mph."
                    ),

                "requires_leaderboard":
                    False,

                "historical_claim":
                    False,

                "utility_weight":
                    np.nan,

                "use":
                    "DOWNSIDE_SENSITIVITY",
            }
        )

    threshold_policy = pd.DataFrame(
        threshold_rows
    )

    # ========================================================
    # Empirical threshold rates by branch
    #
    # These are descriptive empirical branch rates.
    # They are NOT yet unconditional withdraw probabilities.
    # ========================================================

    branch_sets = {
        "NORMAL_DIAGNOSTIC":
            normal[
                "_delta"
            ].to_numpy(
                dtype=float
            ),

        "RECOVERY_LIKE_DIAGNOSTIC":
            recovery[
                "_delta"
            ].to_numpy(
                dtype=float
            ),
    }

    classification_rows = []

    for branch_name, values in (
        branch_sets.items()
    ):

        for threshold in GAIN_THRESHOLDS_MPH:

            classification_rows.append(
                {
                    "classification_scope":
                        branch_name,

                    "threshold_type":
                        "GAIN_AT_LEAST",

                    "threshold_mph":
                        float(
                            threshold
                        ),

                    "rows":
                        len(
                            values
                        ),

                    "empirical_probability":
                        float(
                            np.mean(
                                values
                                >= threshold
                            )
                        ),

                    "event_count":
                        int(
                            np.sum(
                                values
                                >= threshold
                            )
                        ),

                    "interpretation":
                        (
                            "EMPIRICAL_BRANCH_RATE_ONLY"
                        ),
                }
            )

        for threshold in LOSS_THRESHOLDS_MPH:

            classification_rows.append(
                {
                    "classification_scope":
                        branch_name,

                    "threshold_type":
                        "LOSS_AT_MOST",

                    "threshold_mph":
                        float(
                            threshold
                        ),

                    "rows":
                        len(
                            values
                        ),

                    "empirical_probability":
                        float(
                            np.mean(
                                values
                                <= threshold
                            )
                        ),

                    "event_count":
                        int(
                            np.sum(
                                values
                                <= threshold
                            )
                        ),

                    "interpretation":
                        (
                            "EMPIRICAL_BRANCH_RATE_ONLY"
                        ),
                }
            )

    classification = pd.DataFrame(
        classification_rows
    )

    # ========================================================
    # Scenario-level structural classification
    #
    # No recommendation:
    #
    # FEASIBLE
    # CUTOFF_BLOCKED
    #
    # plus downside / opportunity descriptors.
    # ========================================================

    mc = mc.copy()

    mc[
        "completion_state"
    ] = np.where(
        numeric(
            mc[
                "p_completed_rerun"
            ]
        )
        == 0.0,
        "CUTOFF_BLOCKED",
        np.where(
            numeric(
                mc[
                    "p_completed_rerun"
                ]
            )
            == 1.0,
            "COMPLETION_FEASIBLE_UNDER_SCENARIO",
            "PARTIAL_COMPLETION_PROBABILITY",
        ),
    )

    mc[
        "opportunity_profile"
    ] = np.where(
        numeric(
            mc[
                "p_improve_given_completed"
            ]
        )
        >= 0.70,
        "HIGHER_EMPIRICAL_IMPROVEMENT_OPPORTUNITY",
        np.where(
            numeric(
                mc[
                    "p_improve_given_completed"
                ]
            )
            >= 0.60,
            "MODERATE_EMPIRICAL_IMPROVEMENT_OPPORTUNITY",
            np.where(
                numeric(
                    mc[
                        "p_improve_given_completed"
                    ]
                ).notna(),
                "LOWER_EMPIRICAL_IMPROVEMENT_OPPORTUNITY",
                "NOT_APPLICABLE_NO_COMPLETION",
            ),
        ),
    )

    mc[
        "downside_profile"
    ] = np.where(
        numeric(
            mc[
                "p_no_completed_rerun"
            ]
        )
        > 0,
        "CUTOFF_FAILURE_PRESENT",
        np.where(
            numeric(
                mc[
                    "delta_q05_mph"
                ]
            )
            <= -0.75,
            "MATERIAL_COMPLETED_RUN_DOWNSIDE_TAIL",
            "LIMITED_COMPLETED_RUN_DOWNSIDE_TAIL",
        ),
    )

    scenario_classification = mc[
        [
            "current_retained_speed_mph",
            "baseline_group",
            "time_remaining_minutes",
            "wait_scenario_id",
            "p_completed_rerun",
            "p_no_completed_rerun",
            "p_improve_unconditional",
            "p_improve_given_completed",
            "p_slower_given_completed",
            "expected_delta_given_completed_mph",
            "delta_q05_mph",
            "delta_q50_mph",
            "delta_q95_mph",
            "completion_state",
            "opportunity_profile",
            "downside_profile",
        ]
    ].copy()

    scenario_classification[
        "recommendation_enabled"
    ] = False

    scenario_classification[
        "recommendation"
    ] = "NOT_ISSUED"

    # ========================================================
    # Policy hash
    # ========================================================

    policy_payload = {
        "phase":
            "6D",

        "policy_id":
            POLICY_ID,

        "policy_version":
            POLICY_VERSION,

        "gain_thresholds_mph":
            GAIN_THRESHOLDS_MPH,

        "loss_thresholds_mph":
            LOSS_THRESHOLDS_MPH,

        "numeric_utility":
            "NONE",

        "recommendation_enabled":
            False,

        "leaderboard_threshold":
            "NOT_ASSUMED",
    }

    policy_hash = stable_hash(
        policy_payload
    )

    semantics[
        "policy_hash"
    ] = policy_hash

    threshold_policy[
        "policy_hash"
    ] = policy_hash

    classification[
        "policy_hash"
    ] = policy_hash

    scenario_classification[
        "policy_hash"
    ] = policy_hash

    # ========================================================
    # QA
    # ========================================================

    checks = {
        "monte_carlo_rows_equal_120":
            len(
                mc
            )
            == 120,

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

        "gain_threshold_count_equal_4":
            len(
                GAIN_THRESHOLDS_MPH
            )
            == 4,

        "loss_threshold_count_equal_3":
            len(
                LOSS_THRESHOLDS_MPH
            )
            == 3,

        "no_numeric_utility_assigned":
            threshold_policy[
                "utility_weight"
            ].isna().all(),

        "no_recommendation_enabled":
            not scenario_classification[
                "recommendation_enabled"
            ].any(),

        "all_recommendations_not_issued":
            (
                scenario_classification[
                    "recommendation"
                ]
                == "NOT_ISSUED"
            ).all(),

        "no_historical_threshold_claim":
            not threshold_policy[
                "historical_claim"
            ].any(),

        "absolute_target_requires_leaderboard":
            bool(
                semantics.loc[
                    semantics[
                        "decision_component"
                    ]
                    == "ABSOLUTE_TARGET_SPEED",
                    "leaderboard_required",
                ].iloc[0]
            ),

        "recommendation_not_enabled":
            (
                semantics.loc[
                    semantics[
                        "decision_component"
                    ]
                    == "RECOMMENDATION",
                    "allowed_use",
                ].iloc[0]
                == "NOT_ENABLED_IN_V1_SEMANTICS_FREEZE."
            ),

        "scenario_classification_rows_equal_120":
            len(
                scenario_classification
            )
            == 120,

        "all_policy_hashes_present":
            (
                semantics[
                    "policy_hash"
                ].notna().all()
                and
                threshold_policy[
                    "policy_hash"
                ].notna().all()
                and
                classification[
                    "policy_hash"
                ].notna().all()
                and
                scenario_classification[
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
                    "decision_semantic_rows",

                "value":
                    len(
                        semantics
                    ),

                "status":
                    "INFO",
            },

            {
                "metric":
                    "threshold_policy_rows",

                "value":
                    len(
                        threshold_policy
                    ),

                "status":
                    "INFO",
            },

            {
                "metric":
                    "branch_threshold_classification_rows",

                "value":
                    len(
                        classification
                    ),

                "status":
                    "INFO",
            },

            {
                "metric":
                    "scenario_classification_rows",

                "value":
                    len(
                        scenario_classification
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
    print("DECISION SEMANTICS")
    print("-" * 150)

    print(
        semantics[
            [
                "decision_component",
                "semantic_type",
                "probabilistic",
                "utility_assigned",
                "leaderboard_required",
                "allowed_use",
            ]
        ]
        .to_string(
            index=False
        )
    )

    print()
    print("GAIN / LOSS THRESHOLD POLICY")
    print("-" * 130)

    print(
        threshold_policy[
            [
                "threshold_type",
                "threshold_mph",
                "requires_leaderboard",
                "historical_claim",
                "use",
            ]
        ]
        .to_string(
            index=False
        )
    )

    print()
    print("EMPIRICAL BRANCH THRESHOLD RATES")
    print("-" * 140)

    print(
        classification[
            [
                "classification_scope",
                "threshold_type",
                "threshold_mph",
                "rows",
                "event_count",
                "empirical_probability",
            ]
        ]
        .to_string(
            index=False
        )
    )

    print()
    print(
        "SCENARIO CLASSIFICATION SAMPLE "
        "(RETAINED SPEED 231 MPH)"
    )
    print("-" * 180)

    sample = scenario_classification[
        scenario_classification[
            "current_retained_speed_mph"
        ]
        == 231.0
    ].copy()

    print(
        sample[
            [
                "baseline_group",
                "time_remaining_minutes",
                "wait_scenario_id",
                "p_completed_rerun",
                "p_improve_given_completed",
                "expected_delta_given_completed_mph",
                "delta_q05_mph",
                "delta_q95_mph",
                "completion_state",
                "opportunity_profile",
                "downside_profile",
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

    SEMANTICS_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    semantics.to_csv(
        SEMANTICS_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    threshold_policy.to_csv(
        THRESHOLD_POLICY_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    scenario_classification.to_csv(
        SCENARIO_CLASSIFICATION_FILE,
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
        "# Retain / Withdraw Decision Semantics V1"
    )

    report.append("")

    report.append(
        f"Policy ID: `{POLICY_ID}`"
    )

    report.append(
        f"Policy hash: `{policy_hash}`"
    )

    report.append("")

    report.append(
        "## Central principle"
    )

    report.append("")

    report.append(
        "V1 separates probabilistic outcome reporting "
        "from normative recommendation."
    )

    report.append("")

    report.append(
        "The simulator may report the probability and magnitude "
        "of improvement, loss, and no completed rerun without "
        "assigning arbitrary utility weights."
    )

    report.append("")

    report.append(
        "## Gain thresholds"
    )

    report.append("")

    for threshold in GAIN_THRESHOLDS_MPH:

        report.append(
            f"- `+{threshold:.2f} mph`"
        )

    report.append("")

    report.append(
        "These are sensitivity targets, not historical "
        "Top-12 or bump thresholds."
    )

    report.append("")

    report.append(
        "If a defensible external target speed becomes available, "
        "`required_gain = target_speed - retained_speed` "
        "can be evaluated without retraining the performance model."
    )

    report.append("")

    report.append(
        "## Recommendation boundary"
    )

    report.append("")

    report.append(
        "No retain/withdraw recommendation is enabled in Phase 6D."
    )

    report.append(
        "A recommendation requires either an explicit target objective "
        "or an explicitly frozen utility/risk policy."
    )

    report.append("")

    report.append(
        "## Status"
    )

    report.append("")

    if all_pass:

        report.append(
            "**RETAIN_WITHDRAW_DECISION_SEMANTICS_FROZEN**"
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
            "RETAIN_WITHDRAW_DECISION_SEMANTICS_FROZEN"
        )

    else:

        print(
            "FINAL STATUS: REVIEW_REQUIRED"
        )

    print("=" * 100)

    print()
    print(
        "NO ARBITRARY NUMERIC UTILITY WAS INTRODUCED."
    )

    print(
        "NO HISTORICAL LEADERBOARD THRESHOLD WAS INVENTED."
    )

    print(
        "NO RETAIN/WITHDRAW RECOMMENDATION WAS ISSUED."
    )

    print()
    print("OUTPUTS")

    print(
        SEMANTICS_FILE
    )

    print(
        THRESHOLD_POLICY_FILE
    )

    print(
        SCENARIO_CLASSIFICATION_FILE
    )

    print(
        QA_FILE
    )

    print(
        REPORT_FILE
    )


if __name__ == "__main__":
    main()
