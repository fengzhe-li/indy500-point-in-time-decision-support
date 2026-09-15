from pathlib import Path
from collections import Counter
import csv
import json
import math
import hashlib

ROOT = Path(
    "/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈"
)

OUT = ROOT / "r4/output"

READINESS_PATH = (
    OUT /
    "r4f7a_v2_expanded_latent_window_input_readiness_rows.csv"
)

REFERENCE_PATH = (
    OUT /
    "r4f6k_expanded_fast_friday_canonical_panel_v1.csv"
)

ATTEMPT_PATH = (
    OUT /
    "r4p1_attempt_four_lap_panel_v1.csv"
)

OUT_MANIFEST = (
    OUT /
    "r4f7b_latent_window_training_manifest_v1.csv"
)

OUT_CONTRACT = (
    OUT /
    "r4f7b_latent_window_model_contract_v1.json"
)

OUT_QA = (
    OUT /
    "r4f7b_latent_window_model_qa_v1.csv"
)

OUT_REPORT = (
    OUT /
    "r4f7b_latent_window_model_contract_report_v1.json"
)


CORE_YEARS = {
    2020,
    2021,
    2023,
}

DEGRADED_VALIDATION_YEARS = {
    2022,
}

VALIDATION_ONLY_YEARS = {
    2024,
}

TRANSFER_ONLY_YEARS = {
    2025,
}

PRIMARY_STATUSES = {
    "VALID_RETAINED",
    "VALID_SUPERSEDED",
    "WITHDRAWN",
}

REFERENCE_TYPES = {
    "FOUR_LAP_QUALIFYING_SIM",
    "NO_TOW_SINGLE_LAP",
    "GENERAL_FAST_FRIDAY_BEST_SPEED",
}


def clean(v):
    if v is None:
        return ""
    return str(v).strip()


def num(v):
    s = clean(v)

    if not s:
        return None

    try:
        x = float(s)

        if math.isfinite(x):
            return x

    except Exception:
        pass

    return None


def year_int(v):
    x = num(v)

    if x is None:
        return None

    return int(x)


def truthy(v):
    return clean(v).lower() in {
        "1",
        "true",
        "yes",
        "y",
        "t",
    }


def read_csv(path):
    with path.open(
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as f:

        return list(
            csv.DictReader(f)
        )


def sha256(path):
    h = hashlib.sha256()

    with path.open(
        "rb"
    ) as f:

        while True:

            chunk = f.read(
                1024 * 1024
            )

            if not chunk:
                break

            h.update(
                chunk
            )

    return h.hexdigest()


for path in [
    READINESS_PATH,
    REFERENCE_PATH,
    ATTEMPT_PATH,
]:

    if not path.exists():

        raise SystemExit(
            f"MISSING INPUT: {path}"
        )


readiness = read_csv(
    READINESS_PATH
)

references = read_csv(
    REFERENCE_PATH
)

attempts = read_csv(
    ATTEMPT_PATH
)


print("=" * 140)
print("R4F7B — LATENT WINDOW MODEL CONTRACT FREEZE")
print("=" * 140)

print(
    f"Readiness rows: {len(readiness)}"
)

print(
    f"Expanded reference rows: {len(references)}"
)

print(
    f"Attempt rows: {len(attempts)}"
)


# =============================================================================
# Build frozen model-facing manifest
# =============================================================================

manifest = []

for r in readiness:

    year = year_int(
        r.get(
            "year"
        )
    )

    if year is None:
        continue

    observed_ready = truthy(
        r.get(
            "observed_latent_ready"
        )
    )

    forecast_ready = truthy(
        r.get(
            "forecast_latent_ready"
        )
    )

    strict = truthy(
        r.get(
            "strict_performance_eligible"
        )
    )

    reference_available = truthy(
        r.get(
            "reference_available"
        )
    )

    point_time = truthy(
        r.get(
            "point_time_available"
        )
    )

    env_align = truthy(
        r.get(
            "environment_alignment_usable"
        )
    )

    ptsc = truthy(
        r.get(
            "ptsc_track_temp_available"
        )
    )

    hrrr = truthy(
        r.get(
            "hrrr_leakage_safe_available"
        )
    )

    reference_type = clean(
        r.get(
            "reference_type"
        )
    )

    reference_speed = num(
        r.get(
            "reference_speed_mph"
        )
    )

    dataset_role = clean(
        r.get(
            "dataset_role"
        )
    )


    if year in CORE_YEARS:

        expected_role = (
            "CORE_DEVELOPMENT"
        )

        split_role = (
            "DEVELOPMENT"
        )

        model_eligible = (
            observed_ready
            and
            forecast_ready
        )


    elif year in DEGRADED_VALIDATION_YEARS:

        expected_role = (
            "DEGRADED_CHRONOLOGY_VALIDATION"
        )

        split_role = (
            "DEGRADED_VALIDATION"
        )

        model_eligible = False


    elif year in VALIDATION_ONLY_YEARS:

        expected_role = (
            "VALIDATION_ONLY"
        )

        split_role = (
            "VALIDATION_ONLY"
        )

        model_eligible = (
            observed_ready
            and
            forecast_ready
        )


    else:

        expected_role = dataset_role

        split_role = (
            "OTHER"
        )

        model_eligible = False


    if dataset_role != expected_role:

        raise SystemExit(
            f"DATASET ROLE MISMATCH | "
            f"year={year} | "
            f"got={dataset_role} | "
            f"expected={expected_role}"
        )


    manifest.append({
        "year":
            year,

        "attempt_id":
            clean(
                r.get(
                    "attempt_id"
                )
            ),

        "driver_name":
            clean(
                r.get(
                    "driver_name"
                )
            ),

        "driver_key":
            clean(
                r.get(
                    "driver_key"
                )
            ),

        "car_number":
            clean(
                r.get(
                    "car_number"
                )
            ),

        "result_status":
            clean(
                r.get(
                    "result_status"
                )
            ),

        "strict_performance_eligible":
            strict,

        "reference_available":
            reference_available,

        "reference_speed_mph":
            (
                reference_speed
                if reference_speed is not None
                else ""
            ),

        "reference_type":
            reference_type,

        "point_time_available":
            point_time,

        "environment_alignment_usable":
            env_align,

        "ptsc_track_temp_available":
            ptsc,

        "hrrr_leakage_safe_available":
            hrrr,

        "observed_latent_ready":
            observed_ready,

        "forecast_latent_ready":
            forecast_ready,

        "dataset_role":
            dataset_role,

        "split_role":
            split_role,

        "model_eligible":
            model_eligible,

        "prospective_feature_policy":
            (
                "TIME_SAFE_ONLY"
            ),

        "historical_future_target_policy":
            (
                "ALLOWED_FOR_TARGETS_NOT_FEATURES"
            ),
    })


# =============================================================================
# Core counts
# =============================================================================

core_model_rows = [
    r
    for r in manifest
    if (
        r[
            "split_role"
        ] == "DEVELOPMENT"
        and
        r[
            "model_eligible"
        ]
    )
]

validation_rows = [
    r
    for r in manifest
    if (
        r[
            "split_role"
        ] == "VALIDATION_ONLY"
        and
        r[
            "model_eligible"
        ]
    )
]

degraded_rows = [
    r
    for r in manifest
    if (
        r[
            "split_role"
        ] == "DEGRADED_VALIDATION"
    )
]


core_year_counts = Counter(
    r[
        "year"
    ]
    for r in core_model_rows
)

validation_year_counts = Counter(
    r[
        "year"
    ]
    for r in validation_rows
)

reference_type_counts = Counter(
    r[
        "reference_type"
    ]
    for r in core_model_rows
)


# =============================================================================
# Frozen contract
# =============================================================================

contract = {
    "phase":
        "R4F7B",

    "status":
        "R4F7B_LATENT_WINDOW_MODEL_CONTRACT_FROZEN",

    "research_objective":
        (
            "Estimate a probabilistic common performance window "
            "under uncertainty while separating entry strength, "
            "thermal/environment effects, and run noise."
        ),

    "development_years":
        [
            2020,
            2021,
            2023,
        ],

    "degraded_validation_years":
        [
            2022,
        ],

    "validation_only_years":
        [
            2024,
        ],

    "transfer_only_years":
        [
            2025,
        ],

    "core_development_observations":
        len(
            core_model_rows
        ),

    "validation_observations":
        len(
            validation_rows
        ),

    "degraded_validation_attempt_rows":
        len(
            degraded_rows
        ),

    "observation_equation":
        (
            "Q_i_t = R_i + entry_residual_i + "
            "thermal_component(X_t) + latent_window_t + run_noise_i_t"
        ),

    "terms": {
        "Q_i_t":
            (
                "Observed qualifying four-lap average speed for "
                "entry i at attempt time t."
            ),

        "R_i":
            (
                "Pre-session Fast Friday reference speed. "
                "Measurement type is retained explicitly."
            ),

        "entry_residual_i":
            (
                "Hierarchically shrunk entry-specific correction "
                "around the pre-session reference."
            ),

        "thermal_component":
            (
                "Observed and/or forecast environmental/thermal "
                "state contribution using only leakage-safe inputs."
            ),

        "latent_window_t":
            (
                "Common field-level time-varying performance state. "
                "It is latent and must NOT be hard-defined as a "
                "local residual median."
            ),

        "run_noise_i_t":
            (
                "Attempt-specific residual variation including "
                "execution, setup, tire preparation, traffic residuals, "
                "and other unmodeled effects."
            ),
    },

    "reference_measurement_policy": {
        "GENERAL_FAST_FRIDAY_BEST_SPEED":
            {
                "role":
                    "PRIMARY_FIELD_COMPLETE_REFERENCE",

                "relative_uncertainty":
                    "BASELINE",
            },

        "NO_TOW_SINGLE_LAP":
            {
                "role":
                    "HIGHER_QUALITY_SPARSE_REFERENCE",

                "relative_uncertainty":
                    "LOWER_THAN_GENERAL_BUT_NOT_FIXED_NUMERIC_YET",
            },

        "FOUR_LAP_QUALIFYING_SIM":
            {
                "role":
                    "QUALIFYING_LIKE_SPARSE_REFERENCE",

                "relative_uncertainty":
                    "LOWER_THAN_GENERAL_BUT_NOT_FIXED_NUMERIC_YET",
            },
    },

    "critical_reference_rule":
        (
            "Reference types are not assumed statistically identical. "
            "Sparse no-tow and four-lap references must not each receive "
            "freely estimated standalone response models because their "
            "sample counts are too small."
        ),

    "performance_observation_status_policy":
        [
            "VALID_RETAINED",
            "VALID_SUPERSEDED",
            "WITHDRAWN",
        ],

    "excluded_primary_performance_statuses":
        [
            "FAILED",
            "RETIRED",
            "DISALLOWED",
        ],

    "prospective_feature_policy": {
        "allowed":
            [
                "information observable at decision time t",
                "past qualifying attempts",
                "current leaderboard state",
                "session elapsed/remaining",
                "current observed track/environment state",
                "leakage-safe HRRR forecast information",
                "pre-session Fast Friday reference",
                "past observed field performance",
            ],

        "not_allowed":
            [
                "future qualifying outcomes as contemporaneous features",
                "future competitor outcomes not yet observed at t",
                "future realized weather as if known at t",
                "future queue state as if known at t",
                "historical action labels treated as optimal actions",
            ],

        "offline_training_exception":
            (
                "Later historical outcomes may be used as targets, labels, "
                "posterior-learning evidence, or retrospective structural "
                "validation, but not as prospective predictor features "
                "for an earlier decision state."
            ),
    },

    "latent_window_policy":
        {
            "definition":
                (
                    "Field-level time-varying latent performance state "
                    "shared partially across entries."
                ),

            "must_not_be":
                (
                    "Defined directly as the median or mean of nearby "
                    "cross-car residuals."
                ),

            "evidence_sources":
                [
                    "whole-field qualifying residual observations",
                    "PTSC track temperature",
                    "HRRR leakage-safe thermal forecasts",
                    "thermal trends/slopes",
                    "time-of-day/session progression",
                    "repeat observations where available",
                ],
        },

    "thermal_policy": {
        "interpretation":
            (
                "Track temperature and weather variables are predictors "
                "or physical proxies. They must not automatically be "
                "described as causal tire temperature effects."
            ),

        "candidate_structure":
            [
                "track_temp_c level",
                "5/10/20 minute thermal slopes where available",
                "ambient temperature",
                "relative humidity",
                "pressure",
                "wind/gust/direction",
                "cloud/shortwave/solar",
                "forecast direction",
                "nonlinear thermal terms",
                "thermal interactions",
            ],
    },

    "required_baselines_for_r4f7c":
        [
            "YEAR_INTERCEPT_ONLY",
            "FAST_FRIDAY_REFERENCE_ONLY",
            "FAST_FRIDAY_PLUS_THERMAL",
            "HIERARCHICAL_ENTRY_PLUS_THERMAL",
            "HIERARCHICAL_ENTRY_PLUS_THERMAL_PLUS_LATENT_WINDOW",
        ],

    "validation_policy": {
        "development":
            (
                "Model development and hyperparameter decisions use "
                "2020, 2021, and 2023 only."
            ),

        "2022":
            (
                "Degraded chronology validation only. Do not force into "
                "time-aligned latent-window training."
            ),

        "2024":
            (
                "Validation-only. Do not use for model-selection or "
                "hyperparameter tuning."
            ),

        "2025":
            (
                "Technical-regime transfer only. Do not merge with "
                "2020-2024 main technical regime development."
            ),
    },

    "primary_model_targets":
        [
            "qualifying four-lap average speed",
            "future attempt speed distribution",
            "probability of beating current result",
            "probability of crossing advancement benchmark",
        ],

    "downstream_monte_carlo_outputs":
        [
            "P(beat_current_result)",
            "P(cross_advancement_benchmark)",
            "expected_speed",
            "expected_rank",
            "rank_change_distribution",
            "downside_probability",
            "completion_probability",
        ],

    "action_layer_boundary":
        {
            "actions":
                [
                    "STOP",
                    "REATTEMPT",
                    "RETAIN_AND_REATTEMPT",
                    "WITHDRAW_AND_REATTEMPT",
                    "WITHDRAW_AND_PRIORITY_REATTEMPT",
                ],

            "rule":
                (
                    "The performance-window model predicts outcome "
                    "distributions. Action choice is a downstream "
                    "counterfactual simulation problem, not a historical "
                    "action-classification problem."
                ),
        },

    "r4f7c_initial_modeling_rule":
        (
            "Begin with low-complexity regularized / hierarchical models. "
            "Do not start with a highly flexible neural model because the "
            "core development sample is 104 observations."
        ),

    "r4f7c_model_selection_metric_policy":
        [
            "MAE / RMSE for speed",
            "year-held-out diagnostics within development years",
            "2024 final validation after development freeze",
            "calibration metrics for probability outputs later",
        ],

    "known_limitations":
        [
            (
                "Reference-type distribution is highly imbalanced: "
                "general Fast Friday best speed dominates."
            ),

            (
                "2022 has no model-ready time-aligned latent observations."
            ),

            (
                "2024 has only a small number of fully model-ready "
                "validation observations."
            ),

            (
                "Latent-window identifiability remains limited by sparse "
                "within-session synchronized observations."
            ),

            (
                "Entry-specific and latent-window components can be "
                "partially confounded and require shrinkage / constraints."
            ),
    ],
}


# =============================================================================
# QA
# =============================================================================

qa_rows = [
    {
        "metric":
            "readiness_rows",
        "value":
            len(
                readiness
            ),
        "expected":
            329,
        "status":
            (
                "PASS"
                if len(
                    readiness
                ) == 329
                else "FAIL"
            ),
    },

    {
        "metric":
            "core_development_rows",
        "value":
            len(
                core_model_rows
            ),
        "expected":
            104,
        "status":
            (
                "PASS"
                if len(
                    core_model_rows
                ) == 104
                else "FAIL"
            ),
    },

    {
        "metric":
            "2020_core_rows",
        "value":
            core_year_counts[
                2020
            ],
        "expected":
            39,
        "status":
            (
                "PASS"
                if core_year_counts[
                    2020
                ] == 39
                else "FAIL"
            ),
    },

    {
        "metric":
            "2021_core_rows",
        "value":
            core_year_counts[
                2021
            ],
        "expected":
            48,
        "status":
            (
                "PASS"
                if core_year_counts[
                    2021
                ] == 48
                else "FAIL"
            ),
    },

    {
        "metric":
            "2023_core_rows",
        "value":
            core_year_counts[
                2023
            ],
        "expected":
            17,
        "status":
            (
                "PASS"
                if core_year_counts[
                    2023
                ] == 17
                else "FAIL"
            ),
    },

    {
        "metric":
            "2024_validation_rows",
        "value":
            validation_year_counts[
                2024
            ],
        "expected":
            6,
        "status":
            (
                "PASS"
                if validation_year_counts[
                    2024
                ] == 6
                else "FAIL"
            ),
    },

    {
        "metric":
            "2022_not_model_eligible",
        "value":
            all(
                not r[
                    "model_eligible"
                ]
                for r in manifest
                if r[
                    "year"
                ] == 2022
            ),
        "expected":
            True,
        "status":
            (
                "PASS"
                if all(
                    not r[
                        "model_eligible"
                    ]
                    for r in manifest
                    if r[
                        "year"
                    ] == 2022
                )
                else "FAIL"
            ),
    },

    {
        "metric":
            "2024_never_development",
        "value":
            all(
                r[
                    "split_role"
                ]
                ==
                "VALIDATION_ONLY"
                for r in manifest
                if r[
                    "year"
                ] == 2024
            ),
        "expected":
            True,
        "status":
            (
                "PASS"
                if all(
                    r[
                        "split_role"
                    ]
                    ==
                    "VALIDATION_ONLY"
                    for r in manifest
                    if r[
                        "year"
                    ] == 2024
                )
                else "FAIL"
            ),
    },

    {
        "metric":
            "all_core_reference_types_valid",
        "value":
            all(
                r[
                    "reference_type"
                ]
                in REFERENCE_TYPES
                for r in core_model_rows
            ),
        "expected":
            True,
        "status":
            (
                "PASS"
                if all(
                    r[
                        "reference_type"
                    ]
                    in REFERENCE_TYPES
                    for r in core_model_rows
                )
                else "FAIL"
            ),
    },

    {
        "metric":
            "car_number_string_policy_frozen",
        "value":
            True,
        "expected":
            True,
        "status":
            "PASS",
    },

    {
        "metric":
            "historical_actions_not_training_targets",
        "value":
            True,
        "expected":
            True,
        "status":
            "PASS",
    },

    {
        "metric":
            "contract_only_no_model_fit",
        "value":
            True,
        "expected":
            True,
        "status":
            "PASS",
    },
]


# =============================================================================
# Save
# =============================================================================

with OUT_MANIFEST.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=list(
            manifest[0].keys()
        )
    )

    writer.writeheader()
    writer.writerows(
        manifest
    )


OUT_CONTRACT.write_text(
    json.dumps(
        contract,
        indent=2,
        ensure_ascii=False
    ),
    encoding="utf-8"
)


with OUT_QA.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=[
            "metric",
            "value",
            "expected",
            "status",
        ]
    )

    writer.writeheader()
    writer.writerows(
        qa_rows
    )


report = {
    "phase":
        "R4F7B",

    "status":
        "R4F7B_LATENT_WINDOW_MODEL_CONTRACT_FROZEN",

    "input_hashes": {
        str(
            READINESS_PATH.relative_to(
                ROOT
            )
        ):
            sha256(
                READINESS_PATH
            ),

        str(
            REFERENCE_PATH.relative_to(
                ROOT
            )
        ):
            sha256(
                REFERENCE_PATH
            ),

        str(
            ATTEMPT_PATH.relative_to(
                ROOT
            )
        ):
            sha256(
                ATTEMPT_PATH
            ),
    },

    "manifest_hash":
        sha256(
            OUT_MANIFEST
        ),

    "contract_hash":
        sha256(
            OUT_CONTRACT
        ),

    "core_development_observations":
        len(
            core_model_rows
        ),

    "core_year_counts":
        dict(
            core_year_counts
        ),

    "validation_observations":
        len(
            validation_rows
        ),

    "reference_type_distribution_core":
        dict(
            reference_type_counts
        ),

    "next_phase":
        (
            "R4F7C: assemble numeric thermal/model matrix and "
            "compare frozen low-complexity baselines before "
            "introducing latent-window dynamics."
        ),
}


OUT_REPORT.write_text(
    json.dumps(
        report,
        indent=2,
        ensure_ascii=False
    ),
    encoding="utf-8"
)


# =============================================================================
# Console
# =============================================================================

print()
print("=" * 140)
print("FROZEN MODEL SPLIT")
print("=" * 140)

print(
    f"CORE DEVELOPMENT: "
    f"{len(core_model_rows)}"
)

for year in sorted(
    CORE_YEARS
):

    print(
        f"  {year}: "
        f"{core_year_counts[year]}"
    )


print(
    f"2022 DEGRADED VALIDATION ATTEMPT ROWS: "
    f"{len(degraded_rows)}"
)

print(
    f"2024 VALIDATION-READY: "
    f"{len(validation_rows)}"
)


print()
print("=" * 140)
print("CORE REFERENCE DISTRIBUTION")
print("=" * 140)

for key, value in sorted(
    reference_type_counts.items()
):

    print(
        f"{key:36s} | "
        f"{value}"
    )


print()
print("=" * 140)
print("MODEL CONTRACT")
print("=" * 140)

print(
    "Q_i_t = R_i + entry_residual_i + "
    "thermal_component(X_t) + latent_window_t + run_noise_i_t"
)

print()
print(
    "Development years: 2020, 2021, 2023"
)

print(
    "2022: degraded chronology validation"
)

print(
    "2024: validation-only"
)

print(
    "2025: technical-regime transfer only"
)

print()
print(
    "Historical future outcomes may be TARGETS, "
    "but never prospective FEATURES for an earlier state."
)

print(
    "Historical action labels are NOT optimality labels."
)

print(
    "latent_window_t is NOT defined as a local residual median."
)


fails = [
    r
    for r in qa_rows
    if r[
        "status"
    ] == "FAIL"
]

warns = [
    r
    for r in qa_rows
    if r[
        "status"
    ] == "WARN"
]


print()
print(
    f"QA: "
    f"{len(qa_rows)-len(fails)-len(warns)} PASS | "
    f"{len(warns)} WARN | "
    f"{len(fails)} FAIL"
)

if fails:

    for r in fails:

        print(
            f"FAIL | "
            f"{r['metric']} | "
            f"value={r['value']} | "
            f"expected={r['expected']}"
        )

    raise SystemExit(1)


print()
print("OUTPUTS")
print(
    OUT_MANIFEST.relative_to(ROOT)
)
print(
    OUT_CONTRACT.relative_to(ROOT)
)
print(
    OUT_QA.relative_to(ROOT)
)
print(
    OUT_REPORT.relative_to(ROOT)
)

print()
print(
    "R4F7B_LATENT_WINDOW_MODEL_CONTRACT_FROZEN"
)
