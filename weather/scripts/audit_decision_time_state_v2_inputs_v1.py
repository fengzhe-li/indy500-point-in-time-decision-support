from pathlib import Path
import csv
import json


PHASE = "R3A.0"

FILES = {
    "eligibility": Path(
        "weather/output/"
        "chronology_rescue_2022_repeat_pair_driver_eligibility_v1.csv"
    ),

    "chronology": Path(
        "weather/output/"
        "unified_attempt_chronology_constraint_ledger_v10.csv"
    ),

    "action_lane": Path(
        "weather/output/"
        "unified_attempt_action_lane_ledger_v8.csv"
    ),

    "decision_state": Path(
        "weather/output/"
        "contemporaneous_decision_state_evidence_ledger_v2.csv"
    ),

    "queue": Path(
        "weather/output/"
        "queue_requeue_evidence_ledger_v1.csv"
    ),

    "queue_wait_policy": Path(
        "weather/output/"
        "queue_wait_identifiability_2022_v1.csv"
    ),

    "service_policy": Path(
        "weather/output/"
        "pit_service_identifiability_2022_v1.csv"
    ),

    "interruption_policy": Path(
        "weather/output/"
        "interruption_track_state_identifiability_2022_v1.csv"
    ),

    "rubber_grip_policy": Path(
        "weather/output/"
        "rubber_grip_identifiability_2022_v1.csv"
    ),

    "tire_policy": Path(
        "weather/output/"
        "tire_thermal_pressure_identifiability_2022_v1.csv"
    ),
}


OUTPUT_DIR = Path("weather/output")

SCHEMA_OUT = (
    OUTPUT_DIR
    / "decision_time_state_v2_input_schema_audit_v1.csv"
)

JOIN_OUT = (
    OUTPUT_DIR
    / "decision_time_state_v2_joinability_audit_v1.csv"
)

SUMMARY_OUT = (
    OUTPUT_DIR
    / "decision_time_state_v2_input_audit_v1.json"
)

QA_OUT = (
    OUTPUT_DIR
    / "decision_time_state_v2_input_audit_v1_qa.csv"
)


EXPECTED_DRIVERS = {
    "Alexander Rossi",
    "Callum Ilott",
    "David Malukas",
    "Helio Castroneves",
    "Marco Andretti",
    "Sage Karam",
    "Scott McLaughlin",
    "Takuma Sato",
}


DRIVER_COLUMNS = [
    "driver_name",
    "driver",
    "Driver",
    "DriverName",
]

YEAR_COLUMNS = [
    "year",
    "Year",
    "season",
]

ATTEMPT_COLUMNS = [
    "attempt_id",
    "AttemptID",
    "attempt",
]

ACTION_COLUMNS = [
    "action",
    "action_semantic",
]

LANE_COLUMNS = [
    "lane",
    "lane_id",
    "lane_identity",
]

RANK_COLUMNS = [
    "current_rank",
    "rank",
    "pre_action_rank",
]

CUTOFF_COLUMNS = [
    "cutoff_rank",
    "cutoff_speed",
]

QUEUE_COLUMNS = [
    "queue_membership",
    "queue_position",
    "queue_state",
]


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


def first_existing(fields, candidates):
    for c in candidates:
        if c in fields:
            return c
    return ""


def values_for(rows, column):
    if not column:
        return set()

    return {
        txt(row.get(column))
        for row in rows
        if txt(row.get(column))
    }


def main():

    print()
    print("=" * 126)
    print(
        "R3A.0 — DECISION-TIME OBSERVABLE STATE V2 "
        "INPUT SCHEMA / JOIN AUDIT"
    )
    print("=" * 126)

    print()
    print("INPUT CHECK")
    print("-" * 126)

    missing = []

    for name, path in FILES.items():

        exists = path.exists()

        print(
            f"{name:<24} "
            f"{'PRESENT' if exists else 'MISSING'} "
            f"{path}"
        )

        if not exists:
            missing.append(name)

    if missing:

        print()
        print(
            "Missing inputs:",
            "|".join(missing),
        )

        print()
        print(
            "FINAL STATUS: "
            "R3A0_STATE_V2_INPUT_AUDIT_MISSING_FILES"
        )

        return

    loaded = {}

    for name, path in FILES.items():

        rows, fields = read_csv(path)

        loaded[name] = {
            "rows": rows,
            "fields": fields,
        }

    # --------------------------------------------------
    # Schema audit
    # --------------------------------------------------

    schema_rows = []

    print()
    print("=" * 126)
    print("SCHEMA AUDIT")
    print("=" * 126)

    for name, obj in loaded.items():

        rows = obj["rows"]
        fields = obj["fields"]

        driver_col = first_existing(
            fields,
            DRIVER_COLUMNS,
        )

        year_col = first_existing(
            fields,
            YEAR_COLUMNS,
        )

        attempt_col = first_existing(
            fields,
            ATTEMPT_COLUMNS,
        )

        action_col = first_existing(
            fields,
            ACTION_COLUMNS,
        )

        lane_col = first_existing(
            fields,
            LANE_COLUMNS,
        )

        rank_col = first_existing(
            fields,
            RANK_COLUMNS,
        )

        cutoff_col = first_existing(
            fields,
            CUTOFF_COLUMNS,
        )

        queue_col = first_existing(
            fields,
            QUEUE_COLUMNS,
        )

        schema_rows.append({
            "source":
                name,

            "row_count":
                len(rows),

            "column_count":
                len(fields),

            "driver_column":
                driver_col,

            "year_column":
                year_col,

            "attempt_column":
                attempt_col,

            "action_column":
                action_col,

            "lane_column":
                lane_col,

            "rank_column":
                rank_col,

            "cutoff_column":
                cutoff_col,

            "queue_column":
                queue_col,

            "all_columns":
                "|".join(fields),
        })

        print()
        print(
            f"{name}"
        )

        print(
            "  rows:",
            len(rows),
        )

        print(
            "  columns:",
            len(fields),
        )

        print(
            "  driver:",
            driver_col or "NONE",
        )

        print(
            "  year:",
            year_col or "NONE",
        )

        print(
            "  attempt:",
            attempt_col or "NONE",
        )

        print(
            "  action:",
            action_col or "NONE",
        )

        print(
            "  lane:",
            lane_col or "NONE",
        )

        print(
            "  rank:",
            rank_col or "NONE",
        )

        print(
            "  cutoff:",
            cutoff_col or "NONE",
        )

        print(
            "  queue:",
            queue_col or "NONE",
        )

        print(
            "  ALL:",
            "|".join(fields),
        )

    write_csv(
        SCHEMA_OUT,
        schema_rows,
        [
            "source",
            "row_count",
            "column_count",
            "driver_column",
            "year_column",
            "attempt_column",
            "action_column",
            "lane_column",
            "rank_column",
            "cutoff_column",
            "queue_column",
            "all_columns",
        ],
    )

    # --------------------------------------------------
    # Eligibility target grounding
    # --------------------------------------------------

    eligibility = loaded[
        "eligibility"
    ]

    eligibility_driver_col = first_existing(
        eligibility["fields"],
        DRIVER_COLUMNS,
    )

    if not eligibility_driver_col:

        print()
        print(
            "FINAL STATUS: "
            "R3A0_ELIGIBILITY_DRIVER_COLUMN_NOT_FOUND"
        )
        return

    eligibility_rows = eligibility[
        "rows"
    ]

    target_drivers = {
        txt(
            row.get(
                eligibility_driver_col
            )
        )
        for row in eligibility_rows
        if (
            txt(
                row.get(
                    eligibility_driver_col
                )
            )
            in EXPECTED_DRIVERS
        )
    }

    target_exact = (
        target_drivers
        ==
        EXPECTED_DRIVERS
    )

    print()
    print("=" * 126)
    print("TARGET SET")
    print("=" * 126)

    print()

    for driver in sorted(
        target_drivers
    ):
        print(driver)

    print()
    print(
        "Target count:",
        len(target_drivers),
    )

    print(
        "Exact frozen target:",
        target_exact,
    )

    # --------------------------------------------------
    # Driver-level joinability
    # --------------------------------------------------

    join_sources = [
        "chronology",
        "action_lane",
        "decision_state",
        "queue",
    ]

    driver_presence = {}

    for source in join_sources:

        obj = loaded[source]

        driver_col = first_existing(
            obj["fields"],
            DRIVER_COLUMNS,
        )

        if driver_col:
            driver_presence[source] = (
                values_for(
                    obj["rows"],
                    driver_col,
                )
                &
                EXPECTED_DRIVERS
            )
        else:
            driver_presence[source] = set()

    join_rows = []

    for driver in sorted(
        EXPECTED_DRIVERS
    ):

        row = {
            "driver_name":
                driver,

            "in_eligibility":
                str(
                    driver in target_drivers
                ),
        }

        for source in join_sources:

            row[
                f"in_{source}"
            ] = str(
                driver
                in
                driver_presence[source]
            )

        row[
            "has_chronology"
        ] = row[
            "in_chronology"
        ]

        row[
            "has_action_lane"
        ] = row[
            "in_action_lane"
        ]

        row[
            "has_decision_state"
        ] = row[
            "in_decision_state"
        ]

        row[
            "has_queue_evidence"
        ] = row[
            "in_queue"
        ]

        join_rows.append(row)

    write_csv(
        JOIN_OUT,
        join_rows,
        [
            "driver_name",
            "in_eligibility",
            "in_chronology",
            "in_action_lane",
            "in_decision_state",
            "in_queue",
            "has_chronology",
            "has_action_lane",
            "has_decision_state",
            "has_queue_evidence",
        ],
    )

    print()
    print("=" * 126)
    print("DRIVER JOINABILITY")
    print("=" * 126)

    print()

    for row in join_rows:

        print(
            f"{row['driver_name']:<22} "
            f"chronology={row['in_chronology']:<5} "
            f"action={row['in_action_lane']:<5} "
            f"state={row['in_decision_state']:<5} "
            f"queue={row['in_queue']:<5}"
        )

    chronology_count = sum(
        row[
            "in_chronology"
        ]
        ==
        "True"
        for row in join_rows
    )

    action_count = sum(
        row[
            "in_action_lane"
        ]
        ==
        "True"
        for row in join_rows
    )

    state_count = sum(
        row[
            "in_decision_state"
        ]
        ==
        "True"
        for row in join_rows
    )

    queue_count = sum(
        row[
            "in_queue"
        ]
        ==
        "True"
        for row in join_rows
    )

    print()
    print(
        "Chronology driver coverage:",
        f"{chronology_count}/8",
    )

    print(
        "Action/Lane driver coverage:",
        f"{action_count}/8",
    )

    print(
        "Decision-state driver coverage:",
        f"{state_count}/8",
    )

    print(
        "Queue-evidence driver coverage:",
        f"{queue_count}/8",
    )

    # --------------------------------------------------
    # Attempt-ID availability
    # --------------------------------------------------

    attempt_summary = {}

    print()
    print("=" * 126)
    print("ATTEMPT-ID AVAILABILITY")
    print("=" * 126)

    for source in join_sources:

        obj = loaded[source]

        attempt_col = first_existing(
            obj["fields"],
            ATTEMPT_COLUMNS,
        )

        if attempt_col:

            values = values_for(
                obj["rows"],
                attempt_col,
            )

            attempt_summary[source] = {
                "column":
                    attempt_col,

                "nonblank":
                    len(values),
            }

        else:

            attempt_summary[source] = {
                "column":
                    "",

                "nonblank":
                    0,
            }

        print()
        print(
            source,
            "attempt column:",
            attempt_summary[
                source
            ][
                "column"
            ]
            or
            "NONE",
        )

        print(
            source,
            "unique nonblank attempt IDs:",
            attempt_summary[
                source
            ][
                "nonblank"
            ],
        )

    # --------------------------------------------------
    # State-builder feasibility
    # --------------------------------------------------

    chronology_driver_col = first_existing(
        loaded[
            "chronology"
        ][
            "fields"
        ],
        DRIVER_COLUMNS,
    )

    chronology_attempt_col = first_existing(
        loaded[
            "chronology"
        ][
            "fields"
        ],
        ATTEMPT_COLUMNS,
    )

    action_driver_col = first_existing(
        loaded[
            "action_lane"
        ][
            "fields"
        ],
        DRIVER_COLUMNS,
    )

    decision_driver_col = first_existing(
        loaded[
            "decision_state"
        ][
            "fields"
        ],
        DRIVER_COLUMNS,
    )

    queue_driver_col = first_existing(
        loaded[
            "queue"
        ][
            "fields"
        ],
        DRIVER_COLUMNS,
    )

    core_join_keys_ready = all([
        eligibility_driver_col,
        chronology_driver_col,
        action_driver_col,
        decision_driver_col,
        queue_driver_col,
    ])

    attempt_level_join_possible = bool(
        chronology_attempt_col
    )

    builder_ready = all([
        target_exact,
        core_join_keys_ready,
        chronology_count
        ==
        8,
        action_count
        ==
        8,
    ])

    payload = {
        "phase":
            PHASE,

        "target_driver_count":
            len(
                target_drivers
            ),

        "target_exact":
            target_exact,

        "driver_coverage": {
            "chronology":
                chronology_count,

            "action_lane":
                action_count,

            "decision_state":
                state_count,

            "queue":
                queue_count,
        },

        "core_join_keys_ready":
            core_join_keys_ready,

        "chronology_attempt_key_available":
            bool(
                chronology_attempt_col
            ),

        "attempt_level_join_possible":
            attempt_level_join_possible,

        "decision_time_state_v2_builder_ready":
            builder_ready,

        "policy": {
            "queue_wait":
                "LATENT",

            "service":
                "UNKNOWN",

            "rubber_grip":
                "UNKNOWN",

            "tire_state":
                "UNKNOWN",

            "elapsed_time_as_track_evolution":
                "PROHIBITED",
        },

        "next_step":
            (
                "BUILD_DECISION_TIME_OBSERVABLE_STATE_V2"
                if builder_ready
                else
                "REVIEW_JOIN_SCHEMA"
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

    qa_rows = [
        {
            "metric":
                "target_exact",

            "value":
                int(
                    target_exact
                ),

            "status":
                (
                    "PASS"
                    if target_exact
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "chronology_driver_coverage_8",

            "value":
                chronology_count,

            "status":
                (
                    "PASS"
                    if chronology_count
                    ==
                    8
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "action_driver_coverage_8",

            "value":
                action_count,

            "status":
                (
                    "PASS"
                    if action_count
                    ==
                    8
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "decision_state_partial_allowed",

            "value":
                state_count,

            "status":
                "PASS",
        },

        {
            "metric":
                "queue_partial_allowed",

            "value":
                queue_count,

            "status":
                "PASS",
        },

        {
            "metric":
                "core_join_keys_ready",

            "value":
                int(
                    core_join_keys_ready
                ),

            "status":
                (
                    "PASS"
                    if core_join_keys_ready
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "no_unknown_state_imputation",

            "value":
                0,

            "status":
                "PASS",
        },

        {
            "metric":
                "elapsed_time_track_evolution_used",

            "value":
                0,

            "status":
                "PASS",
        },

        {
            "metric":
                "active_ledger_mutation",

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

    success = all(
        row[
            "status"
        ]
        ==
        "PASS"
        for row in qa_rows
    )

    print()
    print("=" * 126)
    print("STATE BUILDER READINESS")
    print("=" * 126)

    print()
    print(
        "Core driver join keys ready:",
        core_join_keys_ready,
    )

    print(
        "Chronology attempt key available:",
        bool(
            chronology_attempt_col
        ),
    )

    print(
        "Attempt-level joining possible:",
        attempt_level_join_possible,
    )

    print(
        "Decision-time state V2 builder ready:",
        builder_ready,
    )

    print()
    print(
        "Unknown state imputation performed:",
        "NO",
    )

    print(
        "Elapsed time used as track evolution:",
        "NO",
    )

    print()
    print("=" * 126)

    if success and builder_ready:

        print(
            "FINAL STATUS: "
            "R3A0_DECISION_TIME_STATE_V2_INPUTS_AUDITED_"
            "BUILDER_READY"
        )

    else:

        print(
            "FINAL STATUS: "
            "R3A0_DECISION_TIME_STATE_V2_INPUT_AUDIT_"
            "REVIEW_REQUIRED"
        )

    print("=" * 126)

    print()
    print("OUTPUTS")
    print(SCHEMA_OUT)
    print(JOIN_OUT)
    print(SUMMARY_OUT)
    print(QA_OUT)


if __name__ == "__main__":
    main()
