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

FULL_PROFILE_FILE = Path(
    "weather/output/"
    "retain_withdraw_target_aware_compact_v1.csv"
)


# ============================================================
# OUTPUTS
# ============================================================

LOYO_PROFILE_FILE = Path(
    "weather/output/"
    "target_aware_loyo_profiles_v1.csv"
)

LOYO_STABILITY_FILE = Path(
    "weather/output/"
    "target_aware_loyo_stability_summary_v1.csv"
)

LOYO_RECOVERY_FILE = Path(
    "weather/output/"
    "target_aware_loyo_recovery_posterior_v1.csv"
)

QA_FILE = Path(
    "weather/output/"
    "target_aware_cross_year_robustness_v1_qa.csv"
)

REPORT_FILE = Path(
    "weather/output/"
    "target_aware_cross_year_robustness_v1.md"
)


# ============================================================
# DESIGN
# ============================================================

POLICY_VERSION = (
    "TARGET_AWARE_CROSS_YEAR_ROBUSTNESS_V1"
)

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

BETA_PRIOR_ALPHA = 1.0
BETA_PRIOR_BETA = 1.0

EXPECTED_TOTAL_ROWS = 39
EXPECTED_RECOVERY_ROWS = 4
EXPECTED_NORMAL_ROWS = 35


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


def empirical_prob(
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
):

    return float(
        (
            BETA_PRIOR_ALPHA
            + successes
        )
        /
        (
            BETA_PRIOR_ALPHA
            + BETA_PRIOR_BETA
            + trials
        )
    )


# ============================================================
# MAIN
# ============================================================

def main():

    df = read_required(
        UNCERTAINTY_FILE
    )

    full_profiles = read_required(
        FULL_PROFILE_FILE
    )

    print()
    print("=" * 100)
    print(
        "PHASE 7A — TARGET-AWARE "
        "CROSS-YEAR ROBUSTNESS / LOYO STRESS TEST V1"
    )
    print("=" * 100)

    # ========================================================
    # Validate
    # ========================================================

    required = [
        "year",
        "current_attempt_id",
        "baseline_speed_mph",
        "target_speed_delta_vs_best_prior_mph",
        "diagnostic_recovery_like",
        "baseline_below_year_median",
    ]

    missing = [
        col
        for col in required
        if col not in df.columns
    ]

    if missing:
        raise RuntimeError(
            "Missing uncertainty columns: "
            + ", ".join(
                missing
            )
        )

    if len(df) != EXPECTED_TOTAL_ROWS:
        raise RuntimeError(
            f"Expected {EXPECTED_TOTAL_ROWS} rows, "
            f"got {len(df)}"
        )

    work = df.copy()

    work["year"] = numeric(
        work["year"]
    ).astype(int)

    work["_delta"] = numeric(
        work[
            "target_speed_delta_vs_best_prior_mph"
        ]
    )

    work["_recovery"] = as_bool(
        work[
            "diagnostic_recovery_like"
        ]
    )

    work["_low_baseline"] = as_bool(
        work[
            "baseline_below_year_median"
        ]
    )

    if int(
        work[
            "_recovery"
        ].sum()
    ) != EXPECTED_RECOVERY_ROWS:

        raise RuntimeError(
            "Unexpected recovery count."
        )

    if int(
        (
            ~work[
                "_recovery"
            ]
        ).sum()
    ) != EXPECTED_NORMAL_ROWS:

        raise RuntimeError(
            "Unexpected normal count."
        )

    # ========================================================
    # Full-data reference probabilities
    # ========================================================

    full_normal = work[
        ~work[
            "_recovery"
        ]
    ]

    full_recovery = work[
        work[
            "_recovery"
        ]
    ]

    full_reference = {}

    for group in BASELINE_GROUPS:

        if group == "LOW_BASELINE":

            group_rows = work[
                work[
                    "_low_baseline"
                ]
            ]

        else:

            group_rows = work[
                ~work[
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

        p_recovery = (
            beta_posterior_mean(
                successes,
                trials,
            )
        )

        p_normal = (
            1.0
            - p_recovery
        )

        for threshold in (
            GAIN_THRESHOLDS_MPH
        ):

            p_normal_target = (
                empirical_prob(
                    full_normal[
                        "_delta"
                    ],
                    threshold,
                )
            )

            p_recovery_target = (
                empirical_prob(
                    full_recovery[
                        "_delta"
                    ],
                    threshold,
                )
            )

            mixture = (
                p_normal
                * p_normal_target
                +
                p_recovery
                * p_recovery_target
            )

            full_reference[
                (
                    group,
                    threshold,
                )
            ] = {
                "p_recovery":
                    p_recovery,

                "p_normal_target":
                    p_normal_target,

                "p_recovery_target":
                    p_recovery_target,

                "p_target":
                    mixture,
            }

    # ========================================================
    # LOYO
    # ========================================================

    profile_rows = []
    recovery_rows = []

    for holdout_year in (
        PRIMARY_YEARS
    ):

        train = work[
            work[
                "year"
            ]
            != holdout_year
        ].copy()

        test = work[
            work[
                "year"
            ]
            == holdout_year
        ].copy()

        train_normal = train[
            ~train[
                "_recovery"
            ]
        ]

        train_recovery = train[
            train[
                "_recovery"
            ]
        ]

        if len(train_normal) == 0:
            raise RuntimeError(
                f"No normal rows after holding out {holdout_year}"
            )

        if len(train_recovery) == 0:
            raise RuntimeError(
                f"No recovery rows after holding out {holdout_year}"
            )

        for group in BASELINE_GROUPS:

            if group == "LOW_BASELINE":

                train_group = train[
                    train[
                        "_low_baseline"
                    ]
                ]

                test_group = test[
                    test[
                        "_low_baseline"
                    ]
                ]

            else:

                train_group = train[
                    ~train[
                        "_low_baseline"
                    ]
                ]

                test_group = test[
                    ~test[
                        "_low_baseline"
                    ]
                ]

            successes = int(
                train_group[
                    "_recovery"
                ].sum()
            )

            trials = len(
                train_group
            )

            p_recovery = (
                beta_posterior_mean(
                    successes,
                    trials,
                )
            )

            p_normal = (
                1.0
                - p_recovery
            )

            recovery_rows.append(
                {
                    "holdout_year":
                        holdout_year,

                    "baseline_group":
                        group,

                    "train_rows":
                        trials,

                    "train_recovery_events":
                        successes,

                    "posterior_alpha":
                        BETA_PRIOR_ALPHA
                        + successes,

                    "posterior_beta":
                        (
                            BETA_PRIOR_BETA
                            + trials
                            - successes
                        ),

                    "posterior_mean_recovery_probability":
                        p_recovery,

                    "holdout_rows":
                        len(
                            test_group
                        ),

                    "holdout_recovery_events":
                        int(
                            test_group[
                                "_recovery"
                            ].sum()
                        ),
                }
            )

            for threshold in (
                GAIN_THRESHOLDS_MPH
            ):

                normal_rate = (
                    empirical_prob(
                        train_normal[
                            "_delta"
                        ],
                        threshold,
                    )
                )

                recovery_rate = (
                    empirical_prob(
                        train_recovery[
                            "_delta"
                        ],
                        threshold,
                    )
                )

                p_target = (
                    p_normal
                    * normal_rate
                    +
                    p_recovery
                    * recovery_rate
                )

                full = full_reference[
                    (
                        group,
                        threshold,
                    )
                ]

                deviation = (
                    p_target
                    - full[
                        "p_target"
                    ]
                )

                profile_rows.append(
                    {
                        "holdout_year":
                            holdout_year,

                        "baseline_group":
                            group,

                        "required_gain_mph":
                            threshold,

                        "train_total_rows":
                            len(
                                train
                            ),

                        "train_normal_rows":
                            len(
                                train_normal
                            ),

                        "train_recovery_rows":
                            len(
                                train_recovery
                            ),

                        "recovery_posterior_mean":
                            p_recovery,

                        "normal_branch_target_rate":
                            normal_rate,

                        "recovery_branch_target_rate":
                            recovery_rate,

                        "loyo_p_target_given_completed":
                            p_target,

                        "full_data_p_target_given_completed":
                            full[
                                "p_target"
                            ],

                        "absolute_difference":
                            abs(
                                deviation
                            ),

                        "signed_difference":
                            deviation,

                        "relative_difference_pct":
                            (
                                deviation
                                / full[
                                    "p_target"
                                ]
                                * 100.0
                                if full[
                                    "p_target"
                                ]
                                > 0
                                else np.nan
                            ),
                    }
                )

    loyo_profiles = pd.DataFrame(
        profile_rows
    )

    recovery_audit = pd.DataFrame(
        recovery_rows
    )

    # ========================================================
    # Stability summary
    # ========================================================

    stability_rows = []

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

        full_value = float(
            group[
                "full_data_p_target_given_completed"
            ].iloc[0]
        )

        values = group[
            "loyo_p_target_given_completed"
        ].to_numpy(
            dtype=float
        )

        abs_diffs = np.abs(
            values
            - full_value
        )

        stability_rows.append(
            {
                "baseline_group":
                    baseline_group,

                "required_gain_mph":
                    threshold,

                "full_data_probability":
                    full_value,

                "loyo_min_probability":
                    float(
                        np.min(
                            values
                        )
                    ),

                "loyo_max_probability":
                    float(
                        np.max(
                            values
                        )
                    ),

                "loyo_range":
                    float(
                        np.max(
                            values
                        )
                        -
                        np.min(
                            values
                        )
                    ),

                "max_absolute_deviation_from_full":
                    float(
                        np.max(
                            abs_diffs
                        )
                    ),

                "mean_absolute_deviation_from_full":
                    float(
                        np.mean(
                            abs_diffs
                        )
                    ),

                "most_sensitive_holdout_year":
                    int(
                        group.iloc[
                            int(
                                np.argmax(
                                    abs_diffs
                                )
                            )
                        ][
                            "holdout_year"
                        ]
                    ),
            }
        )

    stability = pd.DataFrame(
        stability_rows
    )

    # ========================================================
    # Policy hash
    # ========================================================

    policy_payload = {
        "phase":
            "7A",

        "policy_version":
            POLICY_VERSION,

        "primary_years":
            PRIMARY_YEARS,

        "gain_thresholds_mph":
            GAIN_THRESHOLDS_MPH,

        "beta_prior":
            [
                BETA_PRIOR_ALPHA,
                BETA_PRIOR_BETA,
            ],

        "validation":
            "LEAVE_ONE_YEAR_OUT",
    }

    policy_hash = stable_hash(
        policy_payload
    )

    loyo_profiles[
        "policy_hash"
    ] = policy_hash

    stability[
        "policy_hash"
    ] = policy_hash

    recovery_audit[
        "policy_hash"
    ] = policy_hash

    # ========================================================
    # QA
    # ========================================================

    expected_profile_rows = (
        len(
            PRIMARY_YEARS
        )
        * len(
            BASELINE_GROUPS
        )
        * len(
            GAIN_THRESHOLDS_MPH
        )
    )

    expected_recovery_rows = (
        len(
            PRIMARY_YEARS
        )
        * len(
            BASELINE_GROUPS
        )
    )

    checks = {
        "input_rows_equal_39":
            len(
                work
            )
            == 39,

        "input_normal_rows_equal_35":
            len(
                full_normal
            )
            == 35,

        "input_recovery_rows_equal_4":
            len(
                full_recovery
            )
            == 4,

        "three_holdout_years":
            set(
                loyo_profiles[
                    "holdout_year"
                ].unique()
            )
            == set(
                PRIMARY_YEARS
            ),

        "profile_rows_match_expected":
            len(
                loyo_profiles
            )
            == expected_profile_rows,

        "recovery_rows_match_expected":
            len(
                recovery_audit
            )
            == expected_recovery_rows,

        "all_probabilities_in_0_1":
            (
                (
                    loyo_profiles[
                        [
                            "recovery_posterior_mean",
                            "normal_branch_target_rate",
                            "recovery_branch_target_rate",
                            "loyo_p_target_given_completed",
                            "full_data_p_target_given_completed",
                        ]
                    ]
                    >= 0
                )
                &
                (
                    loyo_profiles[
                        [
                            "recovery_posterior_mean",
                            "normal_branch_target_rate",
                            "recovery_branch_target_rate",
                            "loyo_p_target_given_completed",
                            "full_data_p_target_given_completed",
                        ]
                    ]
                    <= 1
                )
            ).all().all(),

        "no_training_fold_loses_all_normal_rows":
            (
                loyo_profiles[
                    "train_normal_rows"
                ]
                > 0
            ).all(),

        "no_training_fold_loses_all_recovery_rows":
            (
                loyo_profiles[
                    "train_recovery_rows"
                ]
                > 0
            ).all(),

        "all_policy_hashes_present":
            (
                loyo_profiles[
                    "policy_hash"
                ].notna().all()
                and
                stability[
                    "policy_hash"
                ].notna().all()
                and
                recovery_audit[
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
                    "loyo_profile_rows",

                "value":
                    len(
                        loyo_profiles
                    ),

                "status":
                    "INFO",
            },

            {
                "metric":
                    "max_absolute_probability_deviation",

                "value":
                    float(
                        stability[
                            "max_absolute_deviation_from_full"
                        ].max()
                    ),

                "status":
                    "INFO",
            },

            {
                "metric":
                    "max_loyo_probability_range",

                "value":
                    float(
                        stability[
                            "loyo_range"
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
    print("LOYO RECOVERY POSTERIOR")
    print("-" * 130)

    print(
        recovery_audit[
            [
                "holdout_year",
                "baseline_group",
                "train_rows",
                "train_recovery_events",
                "posterior_mean_recovery_probability",
                "holdout_rows",
                "holdout_recovery_events",
            ]
        ]
        .sort_values(
            [
                "baseline_group",
                "holdout_year",
            ]
        )
        .to_string(
            index=False
        )
    )

    print()
    print("LOYO TARGET PROFILES")
    print("-" * 160)

    print(
        loyo_profiles[
            [
                "holdout_year",
                "baseline_group",
                "required_gain_mph",
                "train_normal_rows",
                "train_recovery_rows",
                "recovery_posterior_mean",
                "normal_branch_target_rate",
                "recovery_branch_target_rate",
                "loyo_p_target_given_completed",
                "full_data_p_target_given_completed",
                "absolute_difference",
            ]
        ]
        .sort_values(
            [
                "baseline_group",
                "required_gain_mph",
                "holdout_year",
            ]
        )
        .to_string(
            index=False
        )
    )

    print()
    print("STABILITY SUMMARY")
    print("-" * 150)

    print(
        stability[
            [
                "baseline_group",
                "required_gain_mph",
                "full_data_probability",
                "loyo_min_probability",
                "loyo_max_probability",
                "loyo_range",
                "max_absolute_deviation_from_full",
                "most_sensitive_holdout_year",
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
    print("MOST SENSITIVE PROFILE")
    print("-" * 120)

    worst = stability.loc[
        stability[
            "max_absolute_deviation_from_full"
        ].idxmax()
    ]

    print(
        worst.to_string()
    )

    print()
    print("QA")
    print("-" * 120)

    print(
        qa.to_string(
            index=False
        )
    )

    # ========================================================
    # WRITE
    # ========================================================

    LOYO_PROFILE_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    loyo_profiles.to_csv(
        LOYO_PROFILE_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    stability.to_csv(
        LOYO_STABILITY_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    recovery_audit.to_csv(
        LOYO_RECOVERY_FILE,
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

    max_abs_dev = float(
        stability[
            "max_absolute_deviation_from_full"
        ].max()
    )

    max_range = float(
        stability[
            "loyo_range"
        ].max()
    )

    report = []

    report.append(
        "# Target-Aware Cross-Year Robustness V1"
    )

    report.append("")

    report.append(
        f"Policy hash: `{policy_hash}`"
    )

    report.append("")

    report.append(
        "## Validation protocol"
    )

    report.append("")

    report.append(
        "Leave one primary year out at a time: "
        "2020, 2021, and 2023."
    )

    report.append("")

    report.append(
        "For each training subset, recompute:"
    )

    report.append("")

    report.append(
        "- empirical normal performance target rates;"
    )

    report.append(
        "- empirical recovery-like target rates;"
    )

    report.append(
        "- baseline-conditioned Beta recovery posterior;"
    )

    report.append(
        "- resulting target-success probability conditional on completion."
    )

    report.append("")

    report.append(
        "No model is retrained and no historical leaderboard "
        "target is introduced."
    )

    report.append("")

    report.append(
        "## Stability"
    )

    report.append("")

    report.append(
        f"- Maximum absolute deviation from full-data "
        f"target probability: `{max_abs_dev:.6f}`"
    )

    report.append(
        f"- Maximum LOYO probability range: "
        f"`{max_range:.6f}`"
    )

    report.append("")

    report.append(
        "These values quantify year sensitivity caused by "
        "the small repeat-attempt sample."
    )

    report.append("")

    report.append(
        "## Interpretation boundary"
    )

    report.append("")

    report.append(
        "- LOYO is a robustness diagnostic, not a new model-selection exercise."
    )

    report.append(
        "- Recovery events remain sparse."
    )

    report.append(
        "- Large deviations must be reported rather than tuned away."
    )

    report.append(
        "- No recommendation is enabled."
    )

    report.append("")

    report.append(
        "## Status"
    )

    report.append("")

    if all_pass:

        report.append(
            "**TARGET_AWARE_CROSS_YEAR_ROBUSTNESS_COMPLETE**"
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
            "TARGET_AWARE_CROSS_YEAR_ROBUSTNESS_COMPLETE"
        )

    else:

        print(
            "FINAL STATUS: REVIEW_REQUIRED"
        )

    print("=" * 100)

    print()
    print(
        "NO MODEL WAS RETUNED."
    )

    print(
        "NO YEAR WAS PERMANENTLY EXCLUDED."
    )

    print(
        "NO RECOMMENDATION WAS ISSUED."
    )

    print()
    print("OUTPUTS")

    print(
        LOYO_PROFILE_FILE
    )

    print(
        LOYO_STABILITY_FILE
    )

    print(
        LOYO_RECOVERY_FILE
    )

    print(
        QA_FILE
    )

    print(
        REPORT_FILE
    )


if __name__ == "__main__":
    main()
