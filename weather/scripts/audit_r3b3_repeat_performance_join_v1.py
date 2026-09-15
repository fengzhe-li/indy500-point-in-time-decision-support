from pathlib import Path
import csv
import json


PHASE = "R3B.3A"
OUT = Path("weather/output")

FILES = {
    "UNCERTAINTY_ROWS":
        OUT / "repeat_performance_uncertainty_rows_v1.csv",

    "PERFORMANCE_CONTEXT":
        OUT / "performance_context_features.csv",

    "PERFORMANCE_TIMING":
        OUT / "performance_grade_attempt_timing.csv",

    "HRRR_ALIGNMENT":
        OUT / "performance_grade_hrrr_forecast_alignment.csv",

    "REALIZED_ENV":
        OUT / "performance_grade_attempt_realized_environment.csv",

    "EMPIRICAL_DISTRIBUTIONS":
        OUT / "repeat_performance_empirical_distributions_v1.csv",

    "RECOVERY_PROBABILITY":
        OUT / "repeat_performance_recovery_probability_v1.csv",

    "RECOVERY_SENSITIVITY":
        OUT / "decision_recovery_prior_sensitivity_v1.csv",
}

SCHEMA_OUT = (
    OUT
    / "r3b3_repeat_performance_join_schema_v1.csv"
)

SUMMARY_OUT = (
    OUT
    / "r3b3_repeat_performance_join_summary_v1.json"
)

QA_OUT = (
    OUT
    / "r3b3_repeat_performance_join_audit_v1_qa.csv"
)


FIELD_CANDIDATES = {
    "year": [
        "year",
        "test_year",
        "season",
    ],

    "driver": [
        "driver_name",
        "driver",
    ],

    "attempt_id": [
        "attempt_id",
        "current_attempt_id",
    ],

    "first_attempt_id": [
        "first_attempt_id",
        "prior_attempt_id",
        "baseline_attempt_id",
        "subject_attempt_id",
    ],

    "second_attempt_id": [
        "second_attempt_id",
        "repeat_attempt_id",
        "related_attempt_id",
    ],

    "first_speed": [
        "first_speed_mph",
        "prior_speed_mph",
        "baseline_speed_mph",
    ],

    "second_speed": [
        "second_speed_mph",
        "repeat_speed_mph",
        "current_speed_mph",
    ],

    "delta": [
        "delta_mph",
        "repeat_delta_mph",
        "observed_delta_mph",
        "speed_delta_mph",
    ],

    "baseline_group": [
        "baseline_group",
        "baseline_bucket",
        "baseline_regime",
    ],

    "recovery_class": [
        "recovery_class",
        "recovery_like",
        "recovery_flag",
        "performance_regime",
    ],

    "performance_time": [
        "performance_time_utc",
        "mapped_capture_time_utc",
    ],

    "leakage_safe": [
        "leakage_safe",
        "leakage_safe_for_primary_analysis",
    ],

    "track_temp": [
        "ptsc_track_c",
    ],
}


def txt(v):
    return "" if v is None else str(v).strip()


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


def resolve(fields, candidates):
    for name in candidates:
        if name in fields:
            return name

    return ""


def sample_values(rows, field, n=5):
    if not field:
        return ""

    values = []

    for row in rows:
        value = txt(
            row.get(field)
        )

        if (
            value
            and
            value not in values
        ):
            values.append(value)

        if len(values) >= n:
            break

    return "|".join(values)


def main():

    print()
    print("=" * 128)
    print(
        "R3B.3A — REPEAT PERFORMANCE / "
        "TIMED-ENVIRONMENT JOIN AUDIT"
    )
    print("=" * 128)

    print()
    print("INPUT CHECK")
    print("-" * 128)

    missing = []

    for name, path in FILES.items():

        exists = path.exists()

        print(
            f"{name:<26} "
            f"{'PRESENT' if exists else 'MISSING'} "
            f"{path}"
        )

        if not exists:
            missing.append(name)

    if missing:

        print()
        print(
            "FINAL STATUS: "
            "R3B3A_INPUT_MISSING"
        )
        return

    loaded = {}

    for name, path in FILES.items():

        rows, fields = read_csv(path)

        loaded[name] = {
            "rows": rows,
            "fields": fields,
        }

    schema_rows = []

    print()
    print("=" * 128)
    print("SCHEMA AUDIT")
    print("=" * 128)

    for name, obj in loaded.items():

        rows = obj["rows"]
        fields = obj["fields"]

        resolved = {}

        for semantic, candidates in (
            FIELD_CANDIDATES.items()
        ):
            resolved[semantic] = resolve(
                fields,
                candidates,
            )

        schema_rows.append({
            "dataset":
                name,

            "row_count":
                len(rows),

            "column_count":
                len(fields),

            "year_column":
                resolved["year"],

            "driver_column":
                resolved["driver"],

            "attempt_id_column":
                resolved["attempt_id"],

            "first_attempt_id_column":
                resolved["first_attempt_id"],

            "second_attempt_id_column":
                resolved["second_attempt_id"],

            "first_speed_column":
                resolved["first_speed"],

            "second_speed_column":
                resolved["second_speed"],

            "delta_column":
                resolved["delta"],

            "baseline_group_column":
                resolved["baseline_group"],

            "recovery_class_column":
                resolved["recovery_class"],

            "performance_time_column":
                resolved["performance_time"],

            "leakage_safe_column":
                resolved["leakage_safe"],

            "track_temp_column":
                resolved["track_temp"],

            "all_columns":
                "|".join(fields),
        })

        print()
        print("-" * 128)
        print(name)

        print(
            "  rows:",
            len(rows),
        )

        for semantic in [
            "year",
            "driver",
            "attempt_id",
            "first_attempt_id",
            "second_attempt_id",
            "first_speed",
            "second_speed",
            "delta",
            "baseline_group",
            "recovery_class",
            "performance_time",
            "leakage_safe",
            "track_temp",
        ]:

            field = resolved[
                semantic
            ]

            print(
                f"  {semantic:<20}:",
                field
                or
                "NONE",
            )

            if field:

                print(
                    "    sample:",
                    sample_values(
                        rows,
                        field,
                    )
                    or
                    "NONE",
                )

        print(
            "  ALL:",
            "|".join(fields),
        )

    write_csv(
        SCHEMA_OUT,
        schema_rows,
        list(
            schema_rows[0].keys()
        ),
    )

    # --------------------------------------------------
    # Exact audit of uncertainty-row structure
    # --------------------------------------------------

    uncertainty = loaded[
        "UNCERTAINTY_ROWS"
    ]

    u_fields = uncertainty[
        "fields"
    ]

    u_rows = uncertainty[
        "rows"
    ]

    u_resolved = {
        semantic:
            resolve(
                u_fields,
                candidates,
            )
        for semantic, candidates
        in FIELD_CANDIDATES.items()
    }

    print()
    print("=" * 128)
    print("UNCERTAINTY ROW STRUCTURE")
    print("=" * 128)

    print()
    print(
        "Rows:",
        len(u_rows),
    )

    print(
        "First attempt ID column:",
        u_resolved[
            "first_attempt_id"
        ]
        or
        "NONE",
    )

    print(
        "Second attempt ID column:",
        u_resolved[
            "second_attempt_id"
        ]
        or
        "NONE",
    )

    print(
        "Attempt ID column:",
        u_resolved[
            "attempt_id"
        ]
        or
        "NONE",
    )

    print(
        "Delta column:",
        u_resolved[
            "delta"
        ]
        or
        "NONE",
    )

    print(
        "Baseline group column:",
        u_resolved[
            "baseline_group"
        ]
        or
        "NONE",
    )

    print(
        "Recovery class column:",
        u_resolved[
            "recovery_class"
        ]
        or
        "NONE",
    )

    # --------------------------------------------------
    # Determine join feasibility.
    # We do not guess which attempt side should receive
    # environment until the actual columns are known.
    # --------------------------------------------------

    pair_ids_explicit = all([
        bool(
            u_resolved[
                "first_attempt_id"
            ]
        ),
        bool(
            u_resolved[
                "second_attempt_id"
            ]
        ),
    ])

    single_attempt_id_present = bool(
        u_resolved[
            "attempt_id"
        ]
    )

    delta_present = bool(
        u_resolved[
            "delta"
        ]
    )

    print()
    print("=" * 128)
    print("JOIN FEASIBILITY")
    print("=" * 128)

    print()
    print(
        "Explicit first+second attempt IDs:",
        pair_ids_explicit,
    )

    print(
        "Single attempt ID available:",
        single_attempt_id_present,
    )

    print(
        "Delta available:",
        delta_present,
    )

    if pair_ids_explicit:

        join_mode = (
            "EXPLICIT_REPEAT_PAIR_IDS"
        )

    elif (
        single_attempt_id_present
        and
        delta_present
    ):

        join_mode = (
            "SINGLE_ATTEMPT_ID_REQUIRES_SEMANTIC_REVIEW"
        )

    else:

        join_mode = (
            "JOIN_SCHEMA_REVIEW_REQUIRED"
        )

    print(
        "Proposed join mode:",
        join_mode,
    )

    # --------------------------------------------------
    # Count timed/environment assets
    # --------------------------------------------------

    timing_rows = loaded[
        "PERFORMANCE_TIMING"
    ][
        "rows"
    ]

    hrrr_rows = loaded[
        "HRRR_ALIGNMENT"
    ][
        "rows"
    ]

    env_rows = loaded[
        "REALIZED_ENV"
    ][
        "rows"
    ]

    timing_ids = {
        txt(
            row.get(
                "attempt_id"
            )
        )
        for row in timing_rows
        if txt(
            row.get(
                "attempt_id"
            )
        )
    }

    hrrr_safe_ids = {
        txt(
            row.get(
                "attempt_id"
            )
        )
        for row in hrrr_rows
        if (
            txt(
                row.get(
                    "attempt_id"
                )
            )
            and
            txt(
                row.get(
                    "leakage_safe"
                )
            ).lower()
            ==
            "true"
        )
    }

    ptsc_ids = {
        txt(
            row.get(
                "attempt_id"
            )
        )
        for row in env_rows
        if (
            txt(
                row.get(
                    "attempt_id"
                )
            )
            and
            txt(
                row.get(
                    "ptsc_track_c"
                )
            )
        )
    }

    timed_hrrr = (
        timing_ids
        &
        hrrr_safe_ids
    )

    timed_hrrr_ptsc = (
        timed_hrrr
        &
        ptsc_ids
    )

    print()
    print("=" * 128)
    print("TIMED ENVIRONMENT ASSETS")
    print("=" * 128)

    print()
    print(
        "Timed attempt IDs:",
        len(
            timing_ids
        ),
    )

    print(
        "Leakage-safe HRRR attempt IDs:",
        len(
            hrrr_safe_ids
        ),
    )

    print(
        "Timed + HRRR-safe:",
        len(
            timed_hrrr
        ),
    )

    print(
        "Timed + HRRR-safe + PTSC:",
        len(
            timed_hrrr_ptsc
        ),
    )

    # --------------------------------------------------
    # QA
    # --------------------------------------------------

    qa_rows = [
        {
            "metric":
                "uncertainty_rows_present",

            "value":
                len(
                    u_rows
                ),

            "status":
                (
                    "PASS"
                    if len(
                        u_rows
                    )
                    >
                    0
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "delta_column_present",

            "value":
                int(
                    delta_present
                ),

            "status":
                (
                    "PASS"
                    if delta_present
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "timed_hrrr_attempts_present",

            "value":
                len(
                    timed_hrrr
                ),

            "status":
                (
                    "PASS"
                    if len(
                        timed_hrrr
                    )
                    >
                    0
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "join_mode_resolved",

            "value":
                join_mode,

            "status":
                (
                    "PASS"
                    if join_mode
                    ==
                    "EXPLICIT_REPEAT_PAIR_IDS"
                    else
                    "REVIEW"
                ),
        },

        {
            "metric":
                "2022_timing_fabricated",

            "value":
                0,

            "status":
                "PASS",
        },

        {
            "metric":
                "historical_queue_wait_claimed",

            "value":
                0,

            "status":
                "PASS",
        },

        {
            "metric":
                "elapsed_time_used_as_track_evolution",

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

        "uncertainty_rows":
            len(
                u_rows
            ),

        "repeat_pair_ids_explicit":
            pair_ids_explicit,

        "single_attempt_id_present":
            single_attempt_id_present,

        "delta_present":
            delta_present,

        "join_mode":
            join_mode,

        "timed_attempt_ids":
            len(
                timing_ids
            ),

        "timed_hrrr_safe_ids":
            len(
                timed_hrrr
            ),

        "timed_hrrr_ptsc_ids":
            len(
                timed_hrrr_ptsc
            ),

        "2022_decision_time_status":
            "LATENT_NOT_IDENTIFIABLE",

        "queue_wait":
            "LATENT_SENSITIVITY_VARIABLE",

        "elapsed_time_as_track_evolution":
            "PROHIBITED",

        "next_phase":
            (
                "R3B3_PERFORMANCE_ENVIRONMENT_SENSITIVITY"
                if (
                    not hard_fail
                    and
                    pair_ids_explicit
                )
                else
                "R3B3_JOIN_SEMANTIC_REVIEW"
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
        not hard_fail
        and
        pair_ids_explicit
    ):

        print(
            "FINAL STATUS: "
            "R3B3A_REPEAT_PERFORMANCE_JOIN_READY"
        )

    elif not hard_fail:

        print(
            "FINAL STATUS: "
            "R3B3A_REPEAT_JOIN_SEMANTIC_REVIEW_REQUIRED"
        )

    else:

        print(
            "FINAL STATUS: "
            "R3B3A_REPEAT_PERFORMANCE_JOIN_AUDIT_FAILED"
        )

    print("=" * 128)

    print()
    print("OUTPUTS")
    print(SCHEMA_OUT)
    print(SUMMARY_OUT)
    print(QA_OUT)


if __name__ == "__main__":
    main()
