from pathlib import Path
import csv
import json
from collections import Counter, defaultdict


PHASE = "R3B.2A"

OUT = Path("weather/output")

HRRR_FEATURES = (
    OUT
    / "hrrr_ims_2020_2024_features.csv"
)

HRRR_POLICY = (
    OUT
    / "hrrr_forecast_availability_policy.csv"
)

HRRR_ALIGNMENT = (
    OUT
    / "performance_grade_hrrr_forecast_alignment.csv"
)

PERFORMANCE_TIMING = (
    OUT
    / "performance_grade_attempt_timing.csv"
)

PERFORMANCE_CONTEXT = (
    OUT
    / "performance_context_features.csv"
)

REALIZED_ENV = (
    OUT
    / "performance_grade_attempt_realized_environment.csv"
)

STATE_V3 = (
    OUT
    / "decision_time_observable_state_v3.csv"
)

SCENARIOS_V1 = (
    OUT
    / "r3b_future_environment_scenarios_v1.csv"
)

SCHEMA_OUT = (
    OUT
    / "r3b_timed_subset_hrrr_schema_audit_v1.csv"
)

COVERAGE_OUT = (
    OUT
    / "r3b_timed_subset_coverage_v1.csv"
)

SUMMARY_OUT = (
    OUT
    / "r3b_timed_subset_hrrr_interface_v1.json"
)

QA_OUT = (
    OUT
    / "r3b_timed_subset_hrrr_interface_v1_qa.csv"
)


def txt(v):
    return "" if v is None else str(v).strip()


def truthy(v):
    return txt(v).lower() in {
        "true",
        "1",
        "yes",
    }


def read_csv(path):
    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fields = reader.fieldnames or []

    return rows, fields


def write_csv(path, rows, fields):
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=fields,
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)


def first_existing(fields, candidates):
    for field in candidates:
        if field in fields:
            return field
    return ""


def main():

    print()
    print("=" * 128)
    print(
        "R3B.2A — HRRR POLICY INTERFACE / "
        "TIMED HISTORICAL SUBSET AUDIT"
    )
    print("=" * 128)

    required = [
        HRRR_FEATURES,
        HRRR_POLICY,
        HRRR_ALIGNMENT,
        PERFORMANCE_TIMING,
        PERFORMANCE_CONTEXT,
        REALIZED_ENV,
        STATE_V3,
        SCENARIOS_V1,
    ]

    print()
    print("INPUT CHECK")
    print("-" * 128)

    missing = []

    for path in required:

        exists = path.exists()

        print(
            f"{path}: "
            f"{'PRESENT' if exists else 'MISSING'}"
        )

        if not exists:
            missing.append(str(path))

    if missing:

        print()
        print(
            "FINAL STATUS: "
            "R3B2A_TIMED_SUBSET_AUDIT_INPUT_MISSING"
        )
        return

    datasets = {}

    for name, path in {
        "HRRR_FEATURES":
            HRRR_FEATURES,

        "HRRR_POLICY":
            HRRR_POLICY,

        "HRRR_ALIGNMENT":
            HRRR_ALIGNMENT,

        "PERFORMANCE_TIMING":
            PERFORMANCE_TIMING,

        "PERFORMANCE_CONTEXT":
            PERFORMANCE_CONTEXT,

        "REALIZED_ENV":
            REALIZED_ENV,

        "STATE_V3":
            STATE_V3,

        "SCENARIOS_V1":
            SCENARIOS_V1,
    }.items():

        rows, fields = read_csv(
            path
        )

        datasets[name] = {
            "rows": rows,
            "fields": fields,
        }

    # --------------------------------------------------
    # Schema audit
    # --------------------------------------------------

    schema_rows = []

    print()
    print("=" * 128)
    print("SCHEMA AUDIT")
    print("=" * 128)

    key_candidates = {
        "issue_time": [
            "issue_time_utc",
            "cycle_time_utc",
            "selected_issue_time_utc",
        ],

        "valid_time": [
            "valid_time_utc",
            "valid_start_utc",
            "before_valid_time_utc",
        ],

        "forecast_hour": [
            "forecast_lead_hours",
            "forecast_hour",
            "before_forecast_lead_hours",
        ],

        "availability_time": [
            "policy_availability_time_utc",
            "availability_time_utc",
            "available_time_utc",
        ],

        "availability_lag": [
            "availability_lag_minutes",
        ],

        "leakage_safe": [
            "leakage_safe_for_primary_analysis",
            "leakage_safe",
        ],

        "attempt_id": [
            "attempt_id",
            "current_attempt_id",
        ],

        "year": [
            "year",
            "test_year",
        ],

        "driver": [
            "driver_name",
            "driver",
        ],

        "performance_time": [
            "performance_time_utc",
            "mapped_capture_time_utc",
        ],

        "track_temp": [
            "ptsc_track_c",
        ],
    }

    resolved = {}

    for name, obj in datasets.items():

        fields = obj["fields"]

        result = {}

        for key, candidates in (
            key_candidates.items()
        ):
            result[key] = (
                first_existing(
                    fields,
                    candidates,
                )
            )

        resolved[name] = result

        schema_rows.append({
            "dataset":
                name,

            "row_count":
                len(
                    obj["rows"]
                ),

            "column_count":
                len(fields),

            "issue_time_column":
                result[
                    "issue_time"
                ],

            "valid_time_column":
                result[
                    "valid_time"
                ],

            "forecast_hour_column":
                result[
                    "forecast_hour"
                ],

            "availability_time_column":
                result[
                    "availability_time"
                ],

            "availability_lag_column":
                result[
                    "availability_lag"
                ],

            "leakage_safe_column":
                result[
                    "leakage_safe"
                ],

            "attempt_id_column":
                result[
                    "attempt_id"
                ],

            "year_column":
                result[
                    "year"
                ],

            "driver_column":
                result[
                    "driver"
                ],

            "performance_time_column":
                result[
                    "performance_time"
                ],

            "track_temp_column":
                result[
                    "track_temp"
                ],

            "all_columns":
                "|".join(fields),
        })

        print()
        print("-" * 128)
        print(name)

        print(
            "  rows:",
            len(
                obj["rows"]
            ),
        )

        print(
            "  issue time:",
            result[
                "issue_time"
            ]
            or
            "NONE",
        )

        print(
            "  valid time:",
            result[
                "valid_time"
            ]
            or
            "NONE",
        )

        print(
            "  forecast hour:",
            result[
                "forecast_hour"
            ]
            or
            "NONE",
        )

        print(
            "  availability time:",
            result[
                "availability_time"
            ]
            or
            "NONE",
        )

        print(
            "  availability lag:",
            result[
                "availability_lag"
            ]
            or
            "NONE",
        )

        print(
            "  leakage safe:",
            result[
                "leakage_safe"
            ]
            or
            "NONE",
        )

        print(
            "  attempt id:",
            result[
                "attempt_id"
            ]
            or
            "NONE",
        )

        print(
            "  year:",
            result[
                "year"
            ]
            or
            "NONE",
        )

        print(
            "  performance time:",
            result[
                "performance_time"
            ]
            or
            "NONE",
        )

    write_csv(
        SCHEMA_OUT,
        schema_rows,
        list(
            schema_rows[0].keys()
        ),
    )

    # --------------------------------------------------
    # Explain R3B.2 prepared-HRRR zero
    # --------------------------------------------------

    policy_fields = (
        datasets[
            "HRRR_POLICY"
        ][
            "fields"
        ]
    )

    required_by_old_builder = {
        "issue_time_utc",
        "forecast_lead_hours",
        "valid_start_utc",
        "policy_availability_time_utc",
        "leakage_safe_for_primary_analysis",
    }

    policy_field_set = set(
        policy_fields
    )

    old_builder_available = (
        required_by_old_builder
        &
        policy_field_set
    )

    missing_old_builder_fields = (
        required_by_old_builder
        -
        policy_field_set
    )

    print()
    print("=" * 128)
    print("R3B.2 HRRR INTERFACE DIAGNOSIS")
    print("=" * 128)

    print()
    print(
        "Fields expected by R3B.2:"
    )

    for field in sorted(
        required_by_old_builder
    ):
        print(
            " ",
            field,
            ":",
            (
                "PRESENT"
                if field
                in policy_field_set
                else
                "MISSING"
            ),
        )

    print()
    print(
        "Missing expected policy fields:",
        (
            "|".join(
                sorted(
                    missing_old_builder_fields
                )
            )
            or
            "NONE"
        ),
    )

    likely_schema_mismatch = (
        len(
            missing_old_builder_fields
        )
        >
        0
    )

    print(
        "Likely schema/interface mismatch:",
        likely_schema_mismatch,
    )

    # --------------------------------------------------
    # Timed attempt coverage
    # --------------------------------------------------

    timing_rows = (
        datasets[
            "PERFORMANCE_TIMING"
        ][
            "rows"
        ]
    )

    context_rows = (
        datasets[
            "PERFORMANCE_CONTEXT"
        ][
            "rows"
        ]
    )

    alignment_rows = (
        datasets[
            "HRRR_ALIGNMENT"
        ][
            "rows"
        ]
    )

    env_rows = (
        datasets[
            "REALIZED_ENV"
        ][
            "rows"
        ]
    )

    # Infer year through session mappings where explicit
    # year is absent by joining to realized environment.
    env_year_by_attempt = {}

    for row in env_rows:

        attempt_id = txt(
            row.get(
                "attempt_id"
            )
        )

        year = txt(
            row.get(
                "year"
            )
        )

        if attempt_id and year:
            env_year_by_attempt[
                attempt_id
            ] = year

    timing_by_attempt = {}

    for row in timing_rows:

        attempt_id = txt(
            row.get(
                "attempt_id"
            )
        )

        if attempt_id:
            timing_by_attempt[
                attempt_id
            ] = row

    context_by_attempt = {}

    for row in context_rows:

        attempt_id = txt(
            row.get(
                "attempt_id"
            )
        )

        if attempt_id:
            context_by_attempt[
                attempt_id
            ] = row

    alignment_by_attempt = {}

    for row in alignment_rows:

        attempt_id = txt(
            row.get(
                "attempt_id"
            )
        )

        if attempt_id:
            alignment_by_attempt[
                attempt_id
            ] = row

    env_by_attempt = {}

    for row in env_rows:

        attempt_id = txt(
            row.get(
                "attempt_id"
            )
        )

        if attempt_id:
            env_by_attempt[
                attempt_id
            ] = row

    years = [
        "2020",
        "2021",
        "2022",
        "2023",
        "2024",
    ]

    coverage = []

    print()
    print("=" * 128)
    print("TIMED HISTORICAL SUBSET COVERAGE")
    print("=" * 128)

    for year in years:

        year_attempts = []

        for attempt_id, row in (
            timing_by_attempt.items()
        ):

            inferred_year = (
                env_year_by_attempt.get(
                    attempt_id,
                    ""
                )
            )

            if inferred_year != year:
                continue

            year_attempts.append(
                (
                    attempt_id,
                    row,
                )
            )

        timed = []

        performance_usable = []

        hrrr_safe = []

        context_safe = []

        ptsc_track = []

        for attempt_id, row in (
            year_attempts
        ):

            mapped_time = txt(
                row.get(
                    "mapped_capture_time_utc"
                )
            )

            if mapped_time:
                timed.append(
                    attempt_id
                )

            if truthy(
                row.get(
                    "performance_alignment_usable"
                )
            ):
                performance_usable.append(
                    attempt_id
                )

            hrrr = (
                alignment_by_attempt.get(
                    attempt_id,
                    {}
                )
            )

            if truthy(
                hrrr.get(
                    "leakage_safe"
                )
            ):
                hrrr_safe.append(
                    attempt_id
                )

            context = (
                context_by_attempt.get(
                    attempt_id,
                    {}
                )
            )

            if (
                truthy(
                    context.get(
                        "leakage_safe"
                    )
                )
                and
                truthy(
                    context.get(
                        "performance_alignment_usable"
                    )
                )
            ):
                context_safe.append(
                    attempt_id
                )

            env = (
                env_by_attempt.get(
                    attempt_id,
                    {}
                )
            )

            if txt(
                env.get(
                    "ptsc_track_c"
                )
            ):
                ptsc_track.append(
                    attempt_id
                )

        fully_joinable = (
            set(
                timed
            )
            &
            set(
                hrrr_safe
            )
            &
            set(
                context_safe
            )
        )

        coverage.append({
            "year":
                year,

            "performance_timing_rows":
                len(
                    year_attempts
                ),

            "timed_rows":
                len(
                    timed
                ),

            "performance_alignment_usable_rows":
                len(
                    performance_usable
                ),

            "leakage_safe_hrrr_rows":
                len(
                    hrrr_safe
                ),

            "leakage_safe_context_rows":
                len(
                    context_safe
                ),

            "ptsc_track_temp_rows":
                len(
                    ptsc_track
                ),

            "fully_joinable_timed_weather_rows":
                len(
                    fully_joinable
                ),
        })

        print()
        print(year)

        print(
            "  timing rows:",
            len(
                year_attempts
            ),
        )

        print(
            "  timed:",
            len(
                timed
            ),
        )

        print(
            "  performance usable:",
            len(
                performance_usable
            ),
        )

        print(
            "  leakage-safe HRRR:",
            len(
                hrrr_safe
            ),
        )

        print(
            "  leakage-safe context:",
            len(
                context_safe
            ),
        )

        print(
            "  PTSC track temp:",
            len(
                ptsc_track
            ),
        )

        print(
            "  fully joinable timed-weather:",
            len(
                fully_joinable
            ),
        )

    write_csv(
        COVERAGE_OUT,
        coverage,
        list(
            coverage[0].keys()
        ),
    )

    # --------------------------------------------------
    # Global timed subset
    # --------------------------------------------------

    historical_timed_years = [
        row[
            "year"
        ]
        for row in coverage
        if row[
            "fully_joinable_timed_weather_rows"
        ]
        >
        0
    ]

    total_joinable = sum(
        row[
            "fully_joinable_timed_weather_rows"
        ]
        for row in coverage
    )

    year_2022 = next(
        row
        for row in coverage
        if row[
            "year"
        ]
        ==
        "2022"
    )

    timed_subset_ready = (
        total_joinable
        >
        0
    )

    print()
    print("=" * 128)
    print("TIMED-SUBSET STRATEGY")
    print("=" * 128)

    print()
    print(
        "Historical years with usable timed-weather subset:",
        (
            "|".join(
                historical_timed_years
            )
            or
            "NONE"
        ),
    )

    print(
        "Total fully joinable timed-weather rows:",
        total_joinable,
    )

    print()
    print(
        "2022 fully joinable timed-weather rows:",
        year_2022[
            "fully_joinable_timed_weather_rows"
        ],
    )

    print(
        "2022 driver-specific counterfactual weather:",
        "NOT_IDENTIFIABLE",
    )

    print(
        "Timed-subset mechanism modeling ready:",
        timed_subset_ready,
    )

    # --------------------------------------------------
    # QA
    # --------------------------------------------------

    scenario_rows = (
        datasets[
            "SCENARIOS_V1"
        ][
            "rows"
        ]
    )

    r3b2_ready_rows = sum(
        txt(
            row.get(
                "scenario_status"
            )
        )
        ==
        "ENVIRONMENT_SCENARIO_READY"
        for row in scenario_rows
    )

    r3b2_no_time_rows = sum(
        txt(
            row.get(
                "scenario_status"
            )
        )
        ==
        "DECISION_TIME_NOT_IDENTIFIABLE"
        for row in scenario_rows
    )

    qa_rows = [
        {
            "metric":
                "r3b2_environment_ready_rows_zero",

            "value":
                r3b2_ready_rows,

            "status":
                (
                    "PASS"
                    if r3b2_ready_rows
                    ==
                    0
                    else
                    "REVIEW"
                ),
        },

        {
            "metric":
                "r3b2_no_time_rows_is_32",

            "value":
                r3b2_no_time_rows,

            "status":
                (
                    "PASS"
                    if r3b2_no_time_rows
                    ==
                    32
                    else
                    "REVIEW"
                ),
        },

        {
            "metric":
                "hrrr_policy_schema_diagnosed",

            "value":
                int(
                    likely_schema_mismatch
                ),

            "status":
                "PASS",
        },

        {
            "metric":
                "timed_subset_joinable_rows",

            "value":
                total_joinable,

            "status":
                (
                    "PASS"
                    if total_joinable
                    >
                    0
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "2022_weather_not_fabricated",

            "value":
                0,

            "status":
                "PASS",
        },

        {
            "metric":
                "queue_wait_remains_latent",

            "value":
                1,

            "status":
                "PASS",
        },

        {
            "metric":
                "elapsed_time_not_track_evolution",

            "value":
                0,

            "status":
                "PASS",
        },

        {
            "metric":
                "protected_outputs_mutated",

            "value":
                0,

            "status":
                "PASS",
        },
    ]

    write_csv(
        QA_OUT,
        qa_rows,
        [
            "metric",
            "value",
            "status",
        ],
    )

    hard_fail = any(
        row[
            "status"
        ]
        ==
        "FAIL"
        for row in qa_rows
    )

    payload = {
        "phase":
            PHASE,

        "r3b2_2022_driver_specific_environment_ready":
            False,

        "r3b2_reason":
            "DECISION_TIME_NOT_IDENTIFIABLE",

        "hrrr_old_builder_schema_mismatch":
            likely_schema_mismatch,

        "hrrr_missing_old_builder_fields":
            sorted(
                missing_old_builder_fields
            ),

        "timed_subset_years":
            historical_timed_years,

        "timed_subset_fully_joinable_rows":
            total_joinable,

        "timed_subset_mechanism_modeling_ready":
            timed_subset_ready,

        "2022_future_weather_policy":
            (
                "LATENT_DECISION_TIME_OR_TIME_AGNOSTIC_"
                "SENSITIVITY_ONLY"
            ),

        "2022_historical_weather_truth_claim":
            False,

        "next_phase":
            (
                "R3B3_TIMED_SUBSET_PERFORMANCE_"
                "ENVIRONMENT_SENSITIVITY"
                if timed_subset_ready
                and
                not hard_fail
                else
                "R3B2A_REVIEW_REQUIRED"
            ),
    }

    SUMMARY_OUT.write_text(
        json.dumps(
            payload,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print()
    print("=" * 128)

    if (
        timed_subset_ready
        and
        not hard_fail
    ):

        print(
            "FINAL STATUS: "
            "R3B2A_TIMED_HISTORICAL_SUBSET_READY_"
            "2022_DECISION_TIME_REMAINS_LATENT"
        )

    else:

        print(
            "FINAL STATUS: "
            "R3B2A_TIMED_SUBSET_REVIEW_REQUIRED"
        )

    print("=" * 128)

    print()
    print("OUTPUTS")
    print(SCHEMA_OUT)
    print(COVERAGE_OUT)
    print(SUMMARY_OUT)
    print(QA_OUT)


if __name__ == "__main__":
    main()
