from pathlib import Path
import hashlib
import json
import math

import numpy as np
import pandas as pd


# ============================================================
# INPUT
# ============================================================

INPUT_FILE = Path(
    "weather/output/"
    "repeat_delta_regime_row_diagnostics_v1.csv"
)


# ============================================================
# OUTPUTS
# ============================================================

ROW_FILE = Path(
    "weather/output/"
    "repeat_performance_uncertainty_rows_v1.csv"
)

DISTRIBUTION_FILE = Path(
    "weather/output/"
    "repeat_performance_empirical_distributions_v1.csv"
)

RECOVERY_PROBABILITY_FILE = Path(
    "weather/output/"
    "repeat_performance_recovery_probability_v1.csv"
)

BOOTSTRAP_FILE = Path(
    "weather/output/"
    "repeat_performance_distribution_bootstrap_v1.csv"
)

QA_FILE = Path(
    "weather/output/"
    "repeat_performance_uncertainty_v1_qa.csv"
)

REPORT_FILE = Path(
    "weather/output/"
    "repeat_performance_uncertainty_v1.md"
)


# ============================================================
# FROZEN / DIAGNOSTIC DESIGN
# ============================================================

TARGET = (
    "target_speed_delta_vs_best_prior_mph"
)

PRIMARY_YEARS = [
    2020,
    2021,
    2023,
]

EXPECTED_PRIMARY_ROWS = 39

EXPECTED_NORMAL_ROWS = 35

EXPECTED_RECOVERY_ROWS = 4

RECOVERY_COLUMN = (
    "diagnostic_large_gain"
)

LOW_BASELINE_COLUMN = (
    "baseline_below_year_median"
)

# ------------------------------------------------------------
# Beta prior
#
# Intentionally weak and transparent.
# This is not a final scientific prior.
# Sensitivity can be added later.
# ------------------------------------------------------------

BETA_PRIOR_ALPHA = 1.0
BETA_PRIOR_BETA = 1.0

BOOTSTRAP_REPS = 10000

RANDOM_SEED = 500

POLICY_VERSION = (
    "REPEAT_PERFORMANCE_EMPIRICAL_UNCERTAINTY_V1"
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


def empirical_summary(
    values,
):

    x = np.asarray(
        values,
        dtype=float,
    )

    if len(x) == 0:

        return {
            "rows":
                0,

            "mean_delta_mph":
                np.nan,

            "median_delta_mph":
                np.nan,

            "std_delta_mph":
                np.nan,

            "min_delta_mph":
                np.nan,

            "q05_delta_mph":
                np.nan,

            "q10_delta_mph":
                np.nan,

            "q25_delta_mph":
                np.nan,

            "q50_delta_mph":
                np.nan,

            "q75_delta_mph":
                np.nan,

            "q90_delta_mph":
                np.nan,

            "q95_delta_mph":
                np.nan,

            "max_delta_mph":
                np.nan,

            "prob_delta_gt_0":
                np.nan,

            "prob_delta_lt_0":
                np.nan,

            "mae_vs_zero_mph":
                np.nan,

            "rmse_vs_zero_mph":
                np.nan,
        }

    return {
        "rows":
            int(
                len(x)
            ),

        "mean_delta_mph":
            float(
                np.mean(x)
            ),

        "median_delta_mph":
            float(
                np.median(x)
            ),

        "std_delta_mph":
            float(
                np.std(
                    x,
                    ddof=1,
                )
            )
            if len(x) > 1
            else np.nan,

        "min_delta_mph":
            float(
                np.min(x)
            ),

        "q05_delta_mph":
            float(
                np.quantile(
                    x,
                    0.05,
                )
            ),

        "q10_delta_mph":
            float(
                np.quantile(
                    x,
                    0.10,
                )
            ),

        "q25_delta_mph":
            float(
                np.quantile(
                    x,
                    0.25,
                )
            ),

        "q50_delta_mph":
            float(
                np.quantile(
                    x,
                    0.50,
                )
            ),

        "q75_delta_mph":
            float(
                np.quantile(
                    x,
                    0.75,
                )
            ),

        "q90_delta_mph":
            float(
                np.quantile(
                    x,
                    0.90,
                )
            ),

        "q95_delta_mph":
            float(
                np.quantile(
                    x,
                    0.95,
                )
            ),

        "max_delta_mph":
            float(
                np.max(x)
            ),

        "prob_delta_gt_0":
            float(
                np.mean(
                    x > 0
                )
            ),

        "prob_delta_lt_0":
            float(
                np.mean(
                    x < 0
                )
            ),

        "mae_vs_zero_mph":
            float(
                np.mean(
                    np.abs(x)
                )
            ),

        "rmse_vs_zero_mph":
            float(
                np.sqrt(
                    np.mean(
                        x ** 2
                    )
                )
            ),
    }


def beta_posterior_summary(
    successes,
    trials,
    alpha_prior,
    beta_prior,
    rng,
    draws=200000,
):

    alpha_post = (
        alpha_prior
        + successes
    )

    beta_post = (
        beta_prior
        + trials
        - successes
    )

    samples = rng.beta(
        alpha_post,
        beta_post,
        size=draws,
    )

    return {
        "successes":
            int(
                successes
            ),

        "trials":
            int(
                trials
            ),

        "observed_rate":
            float(
                successes / trials
            )
            if trials > 0
            else np.nan,

        "prior_alpha":
            float(
                alpha_prior
            ),

        "prior_beta":
            float(
                beta_prior
            ),

        "posterior_alpha":
            float(
                alpha_post
            ),

        "posterior_beta":
            float(
                beta_post
            ),

        "posterior_mean_probability":
            float(
                alpha_post
                / (
                    alpha_post
                    + beta_post
                )
            ),

        "posterior_median_probability":
            float(
                np.median(
                    samples
                )
            ),

        "posterior_q025_probability":
            float(
                np.quantile(
                    samples,
                    0.025,
                )
            ),

        "posterior_q05_probability":
            float(
                np.quantile(
                    samples,
                    0.05,
                )
            ),

        "posterior_q95_probability":
            float(
                np.quantile(
                    samples,
                    0.95,
                )
            ),

        "posterior_q975_probability":
            float(
                np.quantile(
                    samples,
                    0.975,
                )
            ),
    }


# ============================================================
# MAIN
# ============================================================

def main():

    df = read_required(
        INPUT_FILE
    )

    print()
    print("=" * 100)
    print(
        "PHASE 5B-5A — REPEAT-PERFORMANCE "
        "EMPIRICAL UNCERTAINTY MATERIALIZATION"
    )
    print("=" * 100)

    # ========================================================
    # Validate
    # ========================================================

    required = [
        "current_attempt_id",
        "baseline_attempt_id",
        "year",
        "car_number",
        "driver_name",
        "baseline_speed_mph",
        TARGET,
        RECOVERY_COLUMN,
        LOW_BASELINE_COLUMN,
    ]

    missing = [
        col
        for col in required
        if col not in df.columns
    ]

    if missing:

        raise RuntimeError(
            "Missing required columns: "
            + ", ".join(
                missing
            )
        )

    work = df.copy()

    work[
        "year"
    ] = numeric(
        work[
            "year"
        ]
    ).astype(int)

    work[
        TARGET
    ] = numeric(
        work[
            TARGET
        ]
    )

    work[
        "baseline_speed_mph"
    ] = numeric(
        work[
            "baseline_speed_mph"
        ]
    )

    work[
        "_recovery"
    ] = as_bool(
        work[
            RECOVERY_COLUMN
        ]
    )

    work[
        "_low_baseline"
    ] = as_bool(
        work[
            LOW_BASELINE_COLUMN
        ]
    )

    primary = work[
        work[
            "year"
        ].isin(
            PRIMARY_YEARS
        )
    ].copy()

    if len(
        primary
    ) != EXPECTED_PRIMARY_ROWS:

        raise RuntimeError(
            f"Expected {EXPECTED_PRIMARY_ROWS} "
            f"primary rows, got {len(primary)}"
        )

    if primary[
        "current_attempt_id"
    ].duplicated().any():

        raise RuntimeError(
            "Duplicate current_attempt_id."
        )

    normal = primary[
        ~primary[
            "_recovery"
        ]
    ].copy()

    recovery = primary[
        primary[
            "_recovery"
        ]
    ].copy()

    if len(
        normal
    ) != EXPECTED_NORMAL_ROWS:

        raise RuntimeError(
            f"Expected {EXPECTED_NORMAL_ROWS} "
            f"normal rows, got {len(normal)}"
        )

    if len(
        recovery
    ) != EXPECTED_RECOVERY_ROWS:

        raise RuntimeError(
            f"Expected {EXPECTED_RECOVERY_ROWS} "
            f"recovery-like rows, got {len(recovery)}"
        )

    # ========================================================
    # Distribution summaries
    # ========================================================

    distribution_rows = []

    distribution_scopes = {
        "ALL_PRIMARY":
            primary,

        "NORMAL_DIAGNOSTIC":
            normal,

        "RECOVERY_LIKE_DIAGNOSTIC":
            recovery,

        "LOW_BASELINE_ALL":
            primary[
                primary[
                    "_low_baseline"
                ]
            ],

        "HIGH_BASELINE_ALL":
            primary[
                ~primary[
                    "_low_baseline"
                ]
            ],

        "LOW_BASELINE_NORMAL":
            primary[
                primary[
                    "_low_baseline"
                ]
                &
                ~primary[
                    "_recovery"
                ]
            ],

        "HIGH_BASELINE_NORMAL":
            primary[
                ~primary[
                    "_low_baseline"
                ]
                &
                ~primary[
                    "_recovery"
                ]
            ],
    }

    for scope, subset in (
        distribution_scopes.items()
    ):

        summary = empirical_summary(
            subset[
                TARGET
            ]
        )

        distribution_rows.append(
            {
                "distribution_scope":
                    scope,

                **summary,
            }
        )

    for year, subset in (
        primary.groupby(
            "year"
        )
    ):

        summary = empirical_summary(
            subset[
                TARGET
            ]
        )

        distribution_rows.append(
            {
                "distribution_scope":
                    f"YEAR_{int(year)}",

                **summary,
            }
        )

    distribution = pd.DataFrame(
        distribution_rows
    )

    # ========================================================
    # Recovery probability posteriors
    # ========================================================

    rng = np.random.default_rng(
        RANDOM_SEED
    )

    probability_rows = []

    probability_groups = {
        "ALL_PRIMARY":
            primary,

        "LOW_BASELINE":
            primary[
                primary[
                    "_low_baseline"
                ]
            ],

        "AT_OR_ABOVE_BASELINE_MEDIAN":
            primary[
                ~primary[
                    "_low_baseline"
                ]
            ],
    }

    for group_name, subset in (
        probability_groups.items()
    ):

        successes = int(
            subset[
                "_recovery"
            ].sum()
        )

        trials = len(
            subset
        )

        posterior = (
            beta_posterior_summary(
                successes=successes,
                trials=trials,
                alpha_prior=BETA_PRIOR_ALPHA,
                beta_prior=BETA_PRIOR_BETA,
                rng=rng,
            )
        )

        probability_rows.append(
            {
                "eligibility_group":
                    group_name,

                **posterior,
            }
        )

    recovery_probability = pd.DataFrame(
        probability_rows
    )

    # ========================================================
    # Bootstrap empirical distribution uncertainty
    #
    # We are not fitting a parametric Normal distribution.
    # Bootstrap only quantifies instability caused by tiny N.
    # ========================================================

    bootstrap_rng = np.random.default_rng(
        RANDOM_SEED + 1
    )

    bootstrap_rows = []

    bootstrap_scopes = {
        "NORMAL_DIAGNOSTIC":
            normal[
                TARGET
            ].to_numpy(
                dtype=float
            ),

        "RECOVERY_LIKE_DIAGNOSTIC":
            recovery[
                TARGET
            ].to_numpy(
                dtype=float
            ),
    }

    for scope, values in (
        bootstrap_scopes.items()
    ):

        n = len(
            values
        )

        boot_means = np.empty(
            BOOTSTRAP_REPS,
            dtype=float,
        )

        boot_medians = np.empty(
            BOOTSTRAP_REPS,
            dtype=float,
        )

        boot_mae_zero = np.empty(
            BOOTSTRAP_REPS,
            dtype=float,
        )

        for i in range(
            BOOTSTRAP_REPS
        ):

            sample = (
                bootstrap_rng.choice(
                    values,
                    size=n,
                    replace=True,
                )
            )

            boot_means[i] = (
                np.mean(
                    sample
                )
            )

            boot_medians[i] = (
                np.median(
                    sample
                )
            )

            boot_mae_zero[i] = (
                np.mean(
                    np.abs(
                        sample
                    )
                )
            )

        bootstrap_rows.append(
            {
                "distribution_scope":
                    scope,

                "rows":
                    n,

                "bootstrap_reps":
                    BOOTSTRAP_REPS,

                "mean_estimate_mph":
                    float(
                        np.mean(
                            values
                        )
                    ),

                "mean_bootstrap_q025_mph":
                    float(
                        np.quantile(
                            boot_means,
                            0.025,
                        )
                    ),

                "mean_bootstrap_q975_mph":
                    float(
                        np.quantile(
                            boot_means,
                            0.975,
                        )
                    ),

                "median_estimate_mph":
                    float(
                        np.median(
                            values
                        )
                    ),

                "median_bootstrap_q025_mph":
                    float(
                        np.quantile(
                            boot_medians,
                            0.025,
                        )
                    ),

                "median_bootstrap_q975_mph":
                    float(
                        np.quantile(
                            boot_medians,
                            0.975,
                        )
                    ),

                "mae_zero_estimate_mph":
                    float(
                        np.mean(
                            np.abs(
                                values
                            )
                        )
                    ),

                "mae_zero_bootstrap_q025_mph":
                    float(
                        np.quantile(
                            boot_mae_zero,
                            0.025,
                        )
                    ),

                "mae_zero_bootstrap_q975_mph":
                    float(
                        np.quantile(
                            boot_mae_zero,
                            0.975,
                        )
                    ),
            }
        )

    bootstrap = pd.DataFrame(
        bootstrap_rows
    )

    # ========================================================
    # Row materialization
    # ========================================================

    row_output = primary[
        [
            "current_attempt_id",
            "baseline_attempt_id",
            "year",
            "car_number",
            "driver_name",
            "baseline_speed_mph",
            TARGET,
        ]
    ].copy()

    row_output[
        "diagnostic_recovery_like"
    ] = primary[
        "_recovery"
    ].astype(bool)

    row_output[
        "baseline_below_year_median"
    ] = primary[
        "_low_baseline"
    ].astype(bool)

    row_output[
        "diagnostic_branch"
    ] = np.where(
        row_output[
            "diagnostic_recovery_like"
        ],
        "RECOVERY_LIKE_DIAGNOSTIC",
        "NORMAL_DIAGNOSTIC",
    )

    # ========================================================
    # Policy hash
    # ========================================================

    policy_payload = {
        "phase":
            "5B-5A",

        "policy_version":
            POLICY_VERSION,

        "target":
            TARGET,

        "primary_years":
            PRIMARY_YEARS,

        "normal_rows":
            len(
                normal
            ),

        "recovery_rows":
            len(
                recovery
            ),

        "beta_prior_alpha":
            BETA_PRIOR_ALPHA,

        "beta_prior_beta":
            BETA_PRIOR_BETA,

        "bootstrap_reps":
            BOOTSTRAP_REPS,

        "random_seed":
            RANDOM_SEED,
    }

    policy_hash = stable_hash(
        policy_payload
    )

    row_output[
        "uncertainty_policy_hash"
    ] = policy_hash

    distribution[
        "uncertainty_policy_hash"
    ] = policy_hash

    recovery_probability[
        "uncertainty_policy_hash"
    ] = policy_hash

    bootstrap[
        "uncertainty_policy_hash"
    ] = policy_hash

    # ========================================================
    # QA
    # ========================================================

    low = primary[
        primary[
            "_low_baseline"
        ]
    ]

    high = primary[
        ~primary[
            "_low_baseline"
        ]
    ]

    checks = {
        "primary_rows_equal_39":
            len(
                primary
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

        "all_recovery_rows_low_baseline":
            bool(
                recovery[
                    "_low_baseline"
                ].all()
            ),

        "low_baseline_rows_equal_18":
            len(
                low
            )
            == 18,

        "high_baseline_rows_equal_21":
            len(
                high
            )
            == 21,

        "low_baseline_recovery_count_equal_4":
            int(
                low[
                    "_recovery"
                ].sum()
            )
            == 4,

        "high_baseline_recovery_count_equal_0":
            int(
                high[
                    "_recovery"
                ].sum()
            )
            == 0,

        "distribution_output_nonempty":
            len(
                distribution
            )
            > 0,

        "probability_output_has_three_groups":
            len(
                recovery_probability
            )
            == 3,

        "bootstrap_output_has_two_groups":
            len(
                bootstrap
            )
            == 2,

        "all_policy_hashes_present":
            (
                row_output[
                    "uncertainty_policy_hash"
                ].notna().all()
                and
                distribution[
                    "uncertainty_policy_hash"
                ].notna().all()
                and
                recovery_probability[
                    "uncertainty_policy_hash"
                ].notna().all()
                and
                bootstrap[
                    "uncertainty_policy_hash"
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

    normal_summary = empirical_summary(
        normal[
            TARGET
        ]
    )

    recovery_summary = empirical_summary(
        recovery[
            TARGET
        ]
    )

    qa_rows.extend(
        [
            {
                "metric":
                    "normal_mean_delta_mph",

                "value":
                    normal_summary[
                        "mean_delta_mph"
                    ],

                "status":
                    "INFO",
            },

            {
                "metric":
                    "normal_median_delta_mph",

                "value":
                    normal_summary[
                        "median_delta_mph"
                    ],

                "status":
                    "INFO",
            },

            {
                "metric":
                    "normal_zero_mae_mph",

                "value":
                    normal_summary[
                        "mae_vs_zero_mph"
                    ],

                "status":
                    "INFO",
            },

            {
                "metric":
                    "normal_prob_gain",

                "value":
                    normal_summary[
                        "prob_delta_gt_0"
                    ],

                "status":
                    "INFO",
            },

            {
                "metric":
                    "recovery_mean_delta_mph",

                "value":
                    recovery_summary[
                        "mean_delta_mph"
                    ],

                "status":
                    "INFO",
            },

            {
                "metric":
                    "recovery_median_delta_mph",

                "value":
                    recovery_summary[
                        "median_delta_mph"
                    ],

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
    print("EMPIRICAL DISTRIBUTIONS")
    print("-" * 180)

    print(
        distribution.to_string(
            index=False
        )
    )

    print()
    print("RECOVERY PROBABILITY POSTERIORS")
    print("-" * 180)

    print(
        recovery_probability.to_string(
            index=False
        )
    )

    print()
    print("BOOTSTRAP DISTRIBUTION UNCERTAINTY")
    print("-" * 160)

    print(
        bootstrap.to_string(
            index=False
        )
    )

    print()
    print("KEY PERFORMANCE UNCERTAINTY SUMMARY")
    print("-" * 100)

    print(
        "Normal rows:",
        len(
            normal
        )
    )

    print(
        "Normal median delta:",
        normal_summary[
            "median_delta_mph"
        ],
        "mph",
    )

    print(
        "Normal zero-delta MAE:",
        normal_summary[
            "mae_vs_zero_mph"
        ],
        "mph",
    )

    print(
        "Normal probability delta > 0:",
        normal_summary[
            "prob_delta_gt_0"
        ],
    )

    print(
        "Recovery-like rows:",
        len(
            recovery
        )
    )

    print(
        "Recovery-like median delta:",
        recovery_summary[
            "median_delta_mph"
        ],
        "mph",
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

    ROW_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    row_output.to_csv(
        ROW_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    distribution.to_csv(
        DISTRIBUTION_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    recovery_probability.to_csv(
        RECOVERY_PROBABILITY_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    bootstrap.to_csv(
        BOOTSTRAP_FILE,
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
        "# Repeat-Performance Empirical Uncertainty V1"
    )

    report.append("")

    report.append(
        "## Purpose"
    )

    report.append("")

    report.append(
        "Represent repeat-attempt performance uncertainty "
        "without promoting an unstable point-prediction model."
    )

    report.append("")

    report.append(
        "## Primary sample"
    )

    report.append("")

    report.append(
        f"- Primary rows: `{len(primary)}`"
    )

    report.append(
        f"- Normal diagnostic rows: `{len(normal)}`"
    )

    report.append(
        f"- Recovery-like diagnostic rows: `{len(recovery)}`"
    )

    report.append("")

    report.append(
        "## Normal branch"
    )

    report.append("")

    report.append(
        f"- Median delta: "
        f"`{normal_summary['median_delta_mph']:.6f} mph`"
    )

    report.append(
        f"- Zero-delta MAE: "
        f"`{normal_summary['mae_vs_zero_mph']:.6f} mph`"
    )

    report.append(
        f"- Empirical gain probability: "
        f"`{normal_summary['prob_delta_gt_0']:.6f}`"
    )

    report.append("")

    report.append(
        "## Recovery-like branch"
    )

    report.append("")

    report.append(
        f"- Rows: `{len(recovery)}`"
    )

    report.append(
        f"- Median delta: "
        f"`{recovery_summary['median_delta_mph']:.6f} mph`"
    )

    report.append("")

    report.append(
        "Recovery probability is represented with "
        "Beta-Binomial uncertainty rather than a trained classifier."
    )

    report.append("")

    report.append(
        "## Important boundary"
    )

    report.append("")

    report.append(
        "- Diagnostic recovery labels are not ground-truth causal labels."
    )

    report.append(
        "- No recovery classifier is trained."
    )

    report.append(
        "- No parametric Normal performance assumption is imposed."
    )

    report.append(
        "- No queue or decision utility is modeled here."
    )

    report.append(
        "- These distributions are intended for later "
        "Monte Carlo sensitivity analysis."
    )

    report.append("")

    report.append(
        "## Status"
    )

    report.append("")

    if all_pass:

        report.append(
            "**REPEAT_PERFORMANCE_UNCERTAINTY_READY**"
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
            "REPEAT_PERFORMANCE_UNCERTAINTY_READY"
        )

    else:

        print(
            "FINAL STATUS: REVIEW_REQUIRED"
        )

    print("=" * 100)

    print()
    print(
        "NO POINT-PREDICTION MODEL WAS PROMOTED."
    )

    print(
        "NO RECOVERY CLASSIFIER WAS TRAINED."
    )

    print(
        "NO QUEUE OR RETAIN/WITHDRAW UTILITY "
        "WAS MODELED."
    )

    print()
    print("OUTPUTS")

    print(
        ROW_FILE
    )

    print(
        DISTRIBUTION_FILE
    )

    print(
        RECOVERY_PROBABILITY_FILE
    )

    print(
        BOOTSTRAP_FILE
    )

    print(
        QA_FILE
    )

    print(
        REPORT_FILE
    )


if __name__ == "__main__":
    main()
