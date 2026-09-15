from pathlib import Path
from collections import defaultdict
import csv
import json
import math
import re
import statistics

ROOT = Path(
    "/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈"
)

OUT = ROOT / "r4/output"

ATTEMPT_PATH = (
    OUT /
    "r4p1_attempt_four_lap_panel_v1.csv"
)

REFERENCE_PATH = (
    OUT /
    "r4f6k_expanded_fast_friday_canonical_panel_v1.csv"
)

MODEL_CONTRACT = (
    OUT /
    "r4f7c7_final_performance_architecture_contract_v1.json"
)

VALIDATION_CONCLUSION = (
    OUT /
    "r4f7v2_external_validation_conclusion_v1.json"
)

OUT_2022 = (
    OUT /
    "r4f7t1_2022_degraded_transfer_rows_v1.csv"
)

OUT_2025 = (
    OUT /
    "r4f7t1_2025_reference_transfer_rows_v1.csv"
)

OUT_SUMMARY = (
    OUT /
    "r4f7t1_2022_2025_transfer_closeout_summary_v1.csv"
)

OUT_QA = (
    OUT /
    "r4f7t1_2022_2025_transfer_closeout_qa_v1.csv"
)

OUT_REPORT = (
    OUT /
    "r4f7t1_2022_2025_transfer_closeout_report_v1.json"
)


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


def truthy(v):
    return clean(v).lower() in {
        "1",
        "true",
        "yes",
        "y",
        "t",
    }


def norm_name(v):
    s = clean(v).lower()

    s = (
        s.replace("’", "'")
        .replace("`", "'")
    )

    s = re.sub(
        r"[^a-z0-9]+",
        "",
        s
    )

    return s


def read_csv(path):
    with path.open(
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as f:

        reader = csv.DictReader(f)

        return (
            reader.fieldnames or [],
            list(reader),
        )


def find_field(
    fields,
    candidates,
):

    normalized = {
        re.sub(
            r"[^a-z0-9]+",
            "_",
            f.lower()
        ).strip("_"):
            f
        for f in fields
    }

    for candidate in candidates:

        if candidate in normalized:
            return normalized[candidate]

    return None


def mae(actual, pred):

    return (
        sum(
            abs(a - b)
            for a, b
            in zip(actual, pred)
        )
        /
        len(actual)
    )


def rmse(actual, pred):

    return math.sqrt(
        sum(
            (a - b) ** 2
            for a, b
            in zip(actual, pred)
        )
        /
        len(actual)
    )


def bias(actual, pred):

    return (
        sum(
            p - a
            for a, p
            in zip(actual, pred)
        )
        /
        len(actual)
    )


for path in [
    ATTEMPT_PATH,
    REFERENCE_PATH,
    MODEL_CONTRACT,
    VALIDATION_CONCLUSION,
]:

    if not path.exists():

        raise SystemExit(
            f"MISSING INPUT: {path}"
        )


attempt_fields, attempts = read_csv(
    ATTEMPT_PATH
)

ref_fields, refs = read_csv(
    REFERENCE_PATH
)

contract = json.loads(
    MODEL_CONTRACT.read_text(
        encoding="utf-8"
    )
)

validation = json.loads(
    VALIDATION_CONCLUSION.read_text(
        encoding="utf-8"
    )
)


if (
    contract.get("status")
    !=
    "R4F7C7_FINAL_DEVELOPMENT_ARCHITECTURE_FROZEN"
):

    raise SystemExit(
        "PERFORMANCE ARCHITECTURE NOT FROZEN"
    )


if (
    validation.get("status")
    !=
    "R4F7V2_EXTERNAL_VALIDATION_CONCLUSION_FROZEN"
):

    raise SystemExit(
        "EXTERNAL VALIDATION CONCLUSION NOT FROZEN"
    )


frozen_prior = num(
    contract.get(
        "frozen_cross_year_prior_mean_residual_mph"
    )
)

if frozen_prior is None:

    raise SystemExit(
        "MISSING FROZEN PRIOR"
    )


# =============================================================================
# Resolve actual schemas
# =============================================================================

attempt_year_field = find_field(
    attempt_fields,
    [
        "year",
        "season",
    ]
)

attempt_driver_field = find_field(
    attempt_fields,
    [
        "driver_name",
        "driver",
    ]
)

attempt_speed_field = find_field(
    attempt_fields,
    [
        "four_lap_average_speed_mph",
        "average_speed_mph",
    ]
)

attempt_index_field = find_field(
    attempt_fields,
    [
        "car_attempt_index",
        "run_index_observed",
    ]
)


ref_year_field = find_field(
    ref_fields,
    [
        "year",
        "season",
    ]
)

ref_driver_field = find_field(
    ref_fields,
    [
        "driver_name",
        "normalized_driver_name",
        "driver",
    ]
)

ref_speed_field = find_field(
    ref_fields,
    [
        "reference_speed_mph",
        "fast_friday_reference_mph",
    ]
)

ref_type_field = find_field(
    ref_fields,
    [
        "reference_type",
        "canonical_reference_type",
    ]
)


required_schema = {
    "attempt_year":
        attempt_year_field,

    "attempt_driver":
        attempt_driver_field,

    "attempt_speed":
        attempt_speed_field,

    "reference_year":
        ref_year_field,

    "reference_driver":
        ref_driver_field,

    "reference_speed":
        ref_speed_field,
}


missing_schema = [
    key
    for key, value
    in required_schema.items()
    if value is None
]


if missing_schema:

    raise SystemExit(
        "SCHEMA RESOLUTION FAILED: "
        +
        ", ".join(
            missing_schema
        )
    )


# =============================================================================
# Exact 2022 chronology support audit
# =============================================================================

attempts_2022 = [
    r
    for r in attempts
    if int(
        float(
            clean(
                r.get(
                    attempt_year_field
                )
            )
        )
    ) == 2022
]


def nonempty_count(
    field
):

    if field not in attempt_fields:
        return 0

    return sum(
        bool(
            clean(
                r.get(field)
            )
        )
        for r in attempts_2022
    )


time_support_2022 = {
    "rows":
        len(
            attempts_2022
        ),

    "time_point_utc_nonempty":
        nonempty_count(
            "time_point_utc"
        ),

    "canonical_start_time_utc_nonempty":
        nonempty_count(
            "canonical_start_time_utc"
        ),

    "canonical_end_time_utc_nonempty":
        nonempty_count(
            "canonical_end_time_utc"
        ),

    "time_lower_utc_nonempty":
        nonempty_count(
            "time_lower_utc"
        ),

    "time_upper_utc_nonempty":
        nonempty_count(
            "time_upper_utc"
        ),

    "chronology_usable_true":
        sum(
            truthy(
                r.get(
                    "chronology_usable"
                )
            )
            for r in attempts_2022
        ),
}


# =============================================================================
# Canonical references by year + normalized driver
# =============================================================================

reference_lookup = defaultdict(
    list
)


for r in refs:

    year_value = num(
        r.get(
            ref_year_field
        )
    )

    if year_value is None:
        continue

    year = int(
        year_value
    )

    driver_key = norm_name(
        r.get(
            ref_driver_field
        )
    )

    speed = num(
        r.get(
            ref_speed_field
        )
    )

    if (
        not driver_key
        or
        speed is None
    ):
        continue

    reference_lookup[
        (
            year,
            driver_key,
        )
    ].append(
        r
    )


# =============================================================================
# 2022 degraded robustness
#
# Use FIRST complete qualifying attempt per driver.
#
# This avoids overweighting repeat attempts and does not require exact
# chronology. It is a transfer/robustness check only.
# =============================================================================

by_driver_2022 = defaultdict(
    list
)


for r in attempts_2022:

    driver_key = norm_name(
        r.get(
            attempt_driver_field
        )
    )

    speed = num(
        r.get(
            attempt_speed_field
        )
    )

    if (
        not driver_key
        or
        speed is None
    ):
        continue

    idx = num(
        r.get(
            attempt_index_field
        )
    ) if attempt_index_field else None

    by_driver_2022[
        driver_key
    ].append(
        (
            idx,
            r,
        )
    )


transfer_2022 = []


for driver_key, driver_rows in (
    by_driver_2022.items()
):

    driver_rows.sort(
        key=lambda item: (
            item[0]
            if item[0] is not None
            else 9999
        )
    )

    attempt_row = (
        driver_rows[
            0
        ][
            1
        ]
    )

    refs_for_driver = reference_lookup.get(
        (
            2022,
            driver_key,
        ),
        []
    )

    if not refs_for_driver:
        continue


    # Canonical panel should be unique by year-driver.
    if len(
        refs_for_driver
    ) != 1:

        raise SystemExit(
            f"NON-UNIQUE 2022 REFERENCE: {driver_key}"
        )


    ref_row = refs_for_driver[0]

    actual = num(
        attempt_row.get(
            attempt_speed_field
        )
    )

    reference = num(
        ref_row.get(
            ref_speed_field
        )
    )


    transfer_2022.append({
        "year":
            2022,

        "driver_name":
            clean(
                attempt_row.get(
                    attempt_driver_field
                )
            ),

        "driver_key":
            driver_key,

        "qualifying_attempt_index":
            (
                clean(
                    attempt_row.get(
                        attempt_index_field
                    )
                )
                if attempt_index_field
                else ""
            ),

        "qualifying_speed_mph":
            actual,

        "fast_friday_reference_mph":
            reference,

        "reference_type":
            (
                clean(
                    ref_row.get(
                        ref_type_field
                    )
                )
                if ref_type_field
                else ""
            ),

        "actual_minus_reference_mph":
            actual
            -
            reference,

        "frozen_prior_calibrated_prediction_mph":
            reference
            +
            frozen_prior,

        "raw_reference_absolute_error_mph":
            abs(
                reference
                -
                actual
            ),

        "frozen_prior_absolute_error_mph":
            abs(
                (
                    reference
                    +
                    frozen_prior
                )
                -
                actual
            ),

        "validation_role":
            "DEGRADED_CHRONOLOGY_TRANSFER_ROBUSTNESS",
    })


transfer_2022.sort(
    key=lambda r:
        r[
            "driver_name"
        ]
)


# =============================================================================
# 2022 metrics
# =============================================================================

actual_22 = [
    r[
        "qualifying_speed_mph"
    ]
    for r in transfer_2022
]

raw_pred_22 = [
    r[
        "fast_friday_reference_mph"
    ]
    for r in transfer_2022
]

prior_pred_22 = [
    r[
        "frozen_prior_calibrated_prediction_mph"
    ]
    for r in transfer_2022
]


if transfer_2022:

    raw_mae_22 = mae(
        actual_22,
        raw_pred_22,
    )

    raw_rmse_22 = rmse(
        actual_22,
        raw_pred_22,
    )

    raw_bias_22 = bias(
        actual_22,
        raw_pred_22,
    )

    prior_mae_22 = mae(
        actual_22,
        prior_pred_22,
    )

    prior_rmse_22 = rmse(
        actual_22,
        prior_pred_22,
    )

    prior_bias_22 = bias(
        actual_22,
        prior_pred_22,
    )

    residuals_22 = [
        a - p
        for a, p
        in zip(
            actual_22,
            raw_pred_22
        )
    ]

else:

    raw_mae_22 = None
    raw_rmse_22 = None
    raw_bias_22 = None
    prior_mae_22 = None
    prior_rmse_22 = None
    prior_bias_22 = None
    residuals_22 = []


# =============================================================================
# 2025 evidence-only transfer registry
# =============================================================================

transfer_2025 = []


for (
    (
        year,
        driver_key,
    ),
    ref_rows
) in reference_lookup.items():

    if year != 2025:
        continue

    if len(
        ref_rows
    ) != 1:

        raise SystemExit(
            f"NON-UNIQUE 2025 REFERENCE: {driver_key}"
        )

    r = ref_rows[0]

    transfer_2025.append({
        "year":
            2025,

        "driver_name":
            clean(
                r.get(
                    ref_driver_field
                )
            ),

        "driver_key":
            driver_key,

        "reference_speed_mph":
            num(
                r.get(
                    ref_speed_field
                )
            ),

        "reference_type":
            (
                clean(
                    r.get(
                        ref_type_field
                    )
                )
                if ref_type_field
                else ""
            ),

        "transfer_role":
            "TECHNICAL_REGIME_REFERENCE_TRANSFER_EVIDENCE_ONLY",

        "qualifying_outcome_available_locally":
            False,

        "performance_validation_performed":
            False,
    })


transfer_2025.sort(
    key=lambda r:
        r[
            "driver_name"
        ]
)


# =============================================================================
# Summary
# =============================================================================

summary_rows = [
    {
        "year":
            2022,

        "role":
            "DEGRADED_CHRONOLOGY_TRANSFER_ROBUSTNESS",

        "canonical_attempt_rows":
            len(
                attempts_2022
            ),

        "matched_first_attempt_reference_rows":
            len(
                transfer_2022
            ),

        "point_time_rows":
            time_support_2022[
                "time_point_utc_nonempty"
            ],

        "interval_lower_rows":
            time_support_2022[
                "time_lower_utc_nonempty"
            ],

        "interval_upper_rows":
            time_support_2022[
                "time_upper_utc_nonempty"
            ],

        "chronology_usable_rows":
            time_support_2022[
                "chronology_usable_true"
            ],

        "raw_reference_mae_mph":
            (
                raw_mae_22
                if raw_mae_22 is not None
                else ""
            ),

        "frozen_prior_mae_mph":
            (
                prior_mae_22
                if prior_mae_22 is not None
                else ""
            ),

        "strongest_valid_claim":
            (
                "REFERENCE_TO_OUTCOME_ROBUSTNESS; "
                "PREQUENTIAL_REPLAY_ONLY_IF_REAL_POINT_TIMES_EXIST"
            ),
    },

    {
        "year":
            2025,

        "role":
            "TECHNICAL_REGIME_TRANSFER",

        "canonical_attempt_rows":
            0,

        "matched_first_attempt_reference_rows":
            len(
                transfer_2025
            ),

        "point_time_rows":
            0,

        "interval_lower_rows":
            0,

        "interval_upper_rows":
            0,

        "chronology_usable_rows":
            0,

        "raw_reference_mae_mph":
            "",

        "frozen_prior_mae_mph":
            "",

        "strongest_valid_claim":
            (
                "REFERENCE_TRANSFER_EVIDENCE_ONLY; "
                "NO LOCAL QUALIFYING OUTCOME VALIDATION"
            ),
    },
]


# =============================================================================
# Save
# =============================================================================

with OUT_2022.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    if transfer_2022:

        writer = csv.DictWriter(
            f,
            fieldnames=list(
                transfer_2022[
                    0
                ].keys()
            )
        )

        writer.writeheader()
        writer.writerows(
            transfer_2022
        )


with OUT_2025.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=list(
            transfer_2025[
                0
            ].keys()
        )
    )

    writer.writeheader()
    writer.writerows(
        transfer_2025
    )


with OUT_SUMMARY.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=list(
            summary_rows[
                0
            ].keys()
        )
    )

    writer.writeheader()
    writer.writerows(
        summary_rows
    )


# =============================================================================
# QA
# =============================================================================

qa_rows = [
    {
        "metric":
            "2022_attempt_rows",
        "value":
            len(
                attempts_2022
            ),
        "expected":
            44,
        "status":
            (
                "PASS"
                if len(
                    attempts_2022
                ) == 44
                else "FAIL"
            ),
    },

    {
        "metric":
            "2022_reference_outcome_matches",
        "value":
            len(
                transfer_2022
            ),
        "expected":
            ">=25",
        "status":
            (
                "PASS"
                if len(
                    transfer_2022
                ) >= 25
                else "WARN"
            ),
    },

    {
        "metric":
            "2022_point_time_claim_based_on_values_not_schema",
        "value":
            time_support_2022[
                "time_point_utc_nonempty"
            ],
        "expected":
            "MEASURED",
        "status":
            "PASS",
    },

    {
        "metric":
            "2025_canonical_reference_rows",
        "value":
            len(
                transfer_2025
            ),
        "expected":
            33,
        "status":
            (
                "PASS"
                if len(
                    transfer_2025
                ) == 33
                else "FAIL"
            ),
    },

    {
        "metric":
            "2025_fake_outcome_validation_performed",
        "value":
            False,
        "expected":
            False,
        "status":
            "PASS",
    },

    {
        "metric":
            "2024_reused_for_tuning",
        "value":
            False,
        "expected":
            False,
        "status":
            "PASS",
    },

    {
        "metric":
            "frozen_model_refit",
        "value":
            False,
        "expected":
            False,
        "status":
            "PASS",
    },

    {
        "metric":
            "transfer_closeout_only",
        "value":
            True,
        "expected":
            True,
        "status":
            "PASS",
    },
]


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
        "R4F7T1",

    "status":
        "R4F7T1_2022_2025_TRANSFER_CLOSEOUT_COMPLETE",

    "2022": {
        "attempt_rows":
            len(
                attempts_2022
            ),

        "matched_first_attempt_rows":
            len(
                transfer_2022
            ),

        "time_support":
            time_support_2022,

        "raw_fast_friday_mae_mph":
            raw_mae_22,

        "raw_fast_friday_rmse_mph":
            raw_rmse_22,

        "raw_fast_friday_bias_mph":
            raw_bias_22,

        "frozen_prior_calibrated_mae_mph":
            prior_mae_22,

        "frozen_prior_calibrated_rmse_mph":
            prior_rmse_22,

        "frozen_prior_calibrated_bias_mph":
            prior_bias_22,

        "actual_minus_reference_mean_mph":
            (
                statistics.mean(
                    residuals_22
                )
                if residuals_22
                else None
            ),

        "role":
            "DEGRADED_CHRONOLOGY_TRANSFER_ROBUSTNESS",

        "interpretation_boundary":
            (
                "2022 is not promoted to ordinary point-time "
                "prequential validation unless actual nonempty "
                "timestamp support demonstrates that capability."
            ),
    },

    "2025": {
        "canonical_reference_rows":
            len(
                transfer_2025
            ),

        "qualifying_outcome_rows_locally":
            0,

        "role":
            "TECHNICAL_REGIME_REFERENCE_TRANSFER_EVIDENCE_ONLY",

        "performance_validation_performed":
            False,

        "interpretation_boundary":
            (
                "The project currently contains 2025 Fast Friday "
                "entry-strength reference evidence but no canonical "
                "2025 qualifying outcome panel. No artificial "
                "reference-vs-reference validation is performed."
            ),
    },

    "frozen_main_model_changed":
        False,

    "2024_validation_reopened":
        False,

    "next_major_stage":
        (
            "R4F8_ACTION_MONTE_CARLO_INTEGRATION"
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

print("=" * 150)
print("R4F7T1 — 2022 / 2025 TRANSFER CLOSEOUT")
print("=" * 150)


print()
print("=" * 150)
print("2022 ACTUAL CHRONOLOGY SUPPORT")
print("=" * 150)

for key, value in (
    time_support_2022.items()
):

    print(
        f"{key:42s} | {value}"
    )


print()
print("=" * 150)
print("2022 DEGRADED PERFORMANCE ROBUSTNESS")
print("=" * 150)

print(
    f"matched first-attempt/reference rows: "
    f"{len(transfer_2022)}"
)

if transfer_2022:

    print(
        f"Raw Fast Friday MAE: "
        f"{raw_mae_22:.6f}"
    )

    print(
        f"Raw Fast Friday RMSE: "
        f"{raw_rmse_22:.6f}"
    )

    print(
        f"Raw Fast Friday bias: "
        f"{raw_bias_22:+.6f}"
    )

    print(
        f"Frozen prior-calibrated MAE: "
        f"{prior_mae_22:.6f}"
    )

    print(
        f"Frozen prior-calibrated RMSE: "
        f"{prior_rmse_22:.6f}"
    )

    print(
        f"Frozen prior-calibrated bias: "
        f"{prior_bias_22:+.6f}"
    )

    print(
        f"Actual minus reference mean: "
        f"{statistics.mean(residuals_22):+.6f}"
    )


print()
print("=" * 150)
print("2025 TECHNICAL-REGIME TRANSFER")
print("=" * 150)

print(
    f"Canonical Fast Friday references: "
    f"{len(transfer_2025)}"
)

print(
    "Canonical local qualifying outcomes: 0"
)

print(
    "Performance validation performed: False"
)

print(
    "Status: REFERENCE_TRANSFER_EVIDENCE_ONLY"
)


print()
print("=" * 150)
print("TRANSFER CLOSEOUT")
print("=" * 150)

print(
    "2022 = DEGRADED_CHRONOLOGY_TRANSFER_ROBUSTNESS"
)

print(
    "2025 = TECHNICAL_REGIME_REFERENCE_TRANSFER_EVIDENCE_ONLY"
)

print(
    "Frozen main performance model changed: False"
)

print(
    "2024 validation reopened: False"
)

print(
    "NEXT MAJOR STAGE = R4F8 ACTION MONTE CARLO INTEGRATION"
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
    OUT_2022.relative_to(
        ROOT
    )
)

print(
    OUT_2025.relative_to(
        ROOT
    )
)

print(
    OUT_SUMMARY.relative_to(
        ROOT
    )
)

print(
    OUT_QA.relative_to(
        ROOT
    )
)

print(
    OUT_REPORT.relative_to(
        ROOT
    )
)

print()
print(
    "R4F7T1_2022_2025_TRANSFER_CLOSEOUT_COMPLETE"
)
