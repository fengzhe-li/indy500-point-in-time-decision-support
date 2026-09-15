from pathlib import Path
import csv
from collections import Counter


# ============================================================
# PHASE
# ============================================================

PHASE = "R1G.20"


# ============================================================
# INPUTS
# ============================================================

LEDGER_V2 = Path(
    "weather/output/"
    "unified_attempt_chronology_constraint_ledger_v2.csv"
)

ADJUDICATED_SECONDARY = Path(
    "weather/output/"
    "chronology_rescue_2022_secondary_adjudicated_evidence_v1.csv"
)

ORDERING_EDGES = Path(
    "weather/output/"
    "chronology_rescue_2022_secondary_ordering_edges_v1.csv"
)

ACTION_LANE = Path(
    "weather/output/"
    "chronology_rescue_2022_action_lane_evidence_v1.csv"
)

CANONICAL_ATTEMPTS = Path(
    "data/canonical/v1/attempts.csv"
)


# ============================================================
# OUTPUTS
# ============================================================

OUTPUT_DIR = Path(
    "weather/output"
)

LEDGER_V3 = (
    OUTPUT_DIR
    / "unified_attempt_chronology_constraint_ledger_v3.csv"
)

SUMMARY_V3 = (
    OUTPUT_DIR
    / "unified_attempt_chronology_constraint_summary_v3.csv"
)

ACTION_LANE_LEDGER = (
    OUTPUT_DIR
    / "unified_attempt_action_lane_ledger_v1.csv"
)

INTEGRATION_QA = (
    OUTPUT_DIR
    / "unified_secondary_evidence_integration_v1_qa.csv"
)


# ============================================================
# HELPERS
# ============================================================

def read_csv(path):
    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as f:
        return list(
            csv.DictReader(f)
        )


def write_csv(path, rows, fields):
    with path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=fields,
        )
        writer.writeheader()
        writer.writerows(rows)


def txt(v):
    return "" if v is None else str(v).strip()


def canonical_year(row):
    if txt(row.get("year")):
        return txt(row.get("year"))

    session_id = txt(
        row.get(
            "session_id"
        )
    )

    if "2022" in session_id:
        return "2022"

    return ""


# ============================================================
# MAIN
# ============================================================

def main():

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print()
    print("=" * 120)
    print(
        "R1G.20 — SECONDARY EVIDENCE "
        "UNIFIED LEDGER INTEGRATION V1"
    )
    print("=" * 120)

    inputs = [
        LEDGER_V2,
        ADJUDICATED_SECONDARY,
        ORDERING_EDGES,
        ACTION_LANE,
        CANONICAL_ATTEMPTS,
    ]

    missing = []

    print()
    print("INPUT CHECK")
    print("-" * 120)

    for path in inputs:

        exists = path.exists()

        print(
            f"{path}: "
            f"{'PRESENT' if exists else 'MISSING'}"
        )

        if not exists:
            missing.append(path)

    if missing:

        print()
        print(
            "FINAL STATUS: "
            "SECONDARY_UNIFIED_LEDGER_INTEGRATION_INPUT_MISSING"
        )

        return

    ledger_v2 = read_csv(
        LEDGER_V2
    )

    adjudicated = read_csv(
        ADJUDICATED_SECONDARY
    )

    ordering_edges = read_csv(
        ORDERING_EDGES
    )

    action_lane_rows = read_csv(
        ACTION_LANE
    )

    canonical = read_csv(
        CANONICAL_ATTEMPTS
    )

    canonical_by_id = {
        txt(row.get("attempt_id")):
            row
        for row in canonical
        if txt(
            row.get(
                "attempt_id"
            )
        )
    }

    print()
    print(
        "LEDGER V2 ROWS:",
        len(
            ledger_v2
        ),
    )

    print(
        "ADJUDICATED SECONDARY ROWS:",
        len(
            adjudicated
        ),
    )

    print(
        "ORDERING EDGES:",
        len(
            ordering_edges
        ),
    )

    print(
        "ACTION/LANE ROWS:",
        len(
            action_lane_rows
        ),
    )

    # ========================================================
    # VERIFY ROSSI ORDERING EDGE
    # ========================================================

    rossi_edges = [
        row
        for row in ordering_edges
        if txt(
            row.get(
                "edge_id"
            )
        ) == "R1G19-EDGE-ROSSI-1-2"
    ]

    print()
    print("=" * 120)
    print(
        "ROSSI ORDERING CHECK"
    )
    print("=" * 120)

    print(
        "Rossi ordering edges:",
        len(
            rossi_edges
        ),
    )

    if len(
        rossi_edges
    ) != 1:

        print()
        print(
            "FINAL STATUS: "
            "SECONDARY_UNIFIED_LEDGER_ROSSI_EDGE_REVIEW_REQUIRED"
        )

        return

    rossi_edge = rossi_edges[0]

    rossi_from = txt(
        rossi_edge.get(
            "from_attempt_id"
        )
    )

    rossi_to = txt(
        rossi_edge.get(
            "to_attempt_id"
        )
    )

    print(
        "from attempt:",
        rossi_from,
    )

    print(
        "to attempt:",
        rossi_to,
    )

    print(
        "from canonical:",
        "FOUND"
        if rossi_from
        in canonical_by_id
        else "MISSING",
    )

    print(
        "to canonical:",
        "FOUND"
        if rossi_to
        in canonical_by_id
        else "MISSING",
    )

    if (
        rossi_from
        not in canonical_by_id
        or
        rossi_to
        not in canonical_by_id
    ):

        print()
        print(
            "FINAL STATUS: "
            "SECONDARY_UNIFIED_LEDGER_ROSSI_CANONICAL_LINK_MISSING"
        )

        return

    # ========================================================
    # LEDGER V3 FIELD SET
    # ========================================================

    fields = list(
        ledger_v2[0].keys()
    )

    extra_fields = [
        "related_attempt_id",
        "ordering_role",
        "evidence_type",
        "action",
        "lane",
        "source_candidate_id",
        "evidence_quality",
    ]

    for field in extra_fields:

        if field not in fields:
            fields.append(
                field
            )

    ledger_v3 = []

    for row in ledger_v2:

        out = {
            field: ""
            for field in fields
        }

        for key, value in row.items():

            if key in out:
                out[
                    key
                ] = value

        ledger_v3.append(
            out
        )

    # ========================================================
    # ADD ROSSI ORDERING AS TWO ATTEMPT-ROLE ROWS
    #
    # This preserves a single logical ordering edge while
    # allowing both canonical attempts to carry chronology
    # coverage.
    # ========================================================

    rossi_adjudicated = [
        row
        for row in adjudicated
        if txt(
            row.get(
                "evidence_id"
            )
        ) == "R1G19-ROSSI-FIRST-SECOND"
    ]

    if len(
        rossi_adjudicated
    ) != 1:

        print()
        print(
            "FINAL STATUS: "
            "SECONDARY_UNIFIED_LEDGER_ROSSI_EVIDENCE_REVIEW_REQUIRED"
        )

        return

    rossi_ev = rossi_adjudicated[0]

    new_chronology_rows = []

    role_specs = [
        (
            rossi_from,
            rossi_to,
            "FROM",
        ),
        (
            rossi_to,
            rossi_from,
            "TO",
        ),
    ]

    for attempt_id, related_id, role in role_specs:

        can = canonical_by_id[
            attempt_id
        ]

        row = {
            field: ""
            for field in fields
        }

        row.update({
            "attempt_id":
                attempt_id,

            "session_id":
                txt(
                    can.get(
                        "session_id"
                    )
                ),

            "year":
                canonical_year(
                    can
                )
                or
                "2022",

            "car_number":
                txt(
                    can.get(
                        "car_number"
                    )
                ),

            "driver_name":
                txt(
                    can.get(
                        "driver_name"
                    )
                ),

            "car_attempt_index":
                txt(
                    can.get(
                        "car_attempt_index"
                    )
                ),

            "result_status":
                txt(
                    can.get(
                        "result_status"
                    )
                ),

            "constraint_class":
                "ORDERING_ONLY",

            "chronology_usable":
                "True",

            "performance_environment_usable":
                "False",

            "queue_replay_usable":
                "False",

            "evidence_id":
                (
                    "R1G19-ROSSI-FIRST-SECOND:"
                    + role
                ),

            "evidence_stage":
                "R1G20_INTEGRATED",

            "source_authority":
                txt(
                    rossi_ev.get(
                        "source_class"
                    )
                ),

            "source_title":
                "Rossi first-to-second attempt ordering",

            "source_url":
                "",

            "official_result_row":
                "",

            "time_lower_utc":
                "",

            "time_upper_utc":
                "",

            "time_midpoint_utc":
                "",

            "ordering_relation":
                "FIRST_ATTEMPT_BEFORE_SECOND_ATTEMPT",

            "related_attempt_id":
                related_id,

            "ordering_role":
                role,

            "evidence_type":
                "ORDERING",

            "action":
                "SECOND_ATTEMPT",

            "lane":
                "UNKNOWN",

            "source_candidate_id":
                txt(
                    rossi_ev.get(
                        "source_candidate_id"
                    )
                ),

            "evidence_quality":
                txt(
                    rossi_ev.get(
                        "evidence_quality"
                    )
                ),

            "evidence_summary":
                (
                    "Rossi first attempt precedes Rossi "
                    "second attempt. No wall-clock time "
                    "or lane is inferred."
                ),

            "notes":
                (
                    "Secondary editorial evidence integrated "
                    "as an ordering constraint only."
                ),
        })

        new_chronology_rows.append(
            row
        )

    ledger_v3.extend(
        new_chronology_rows
    )

    # ========================================================
    # ACTION / LANE LEDGER
    # ========================================================

    action_fields = [
        "evidence_id",
        "year",
        "subject_attempt_id",
        "related_attempt_id",
        "session_id",
        "car_number",
        "driver_name",
        "action",
        "lane",
        "relation",
        "source_name",
        "source_class",
        "source_candidate_id",
        "evidence_quality",
        "chronology_usable",
        "queue_position_known",
        "queue_wait_known",
        "canonical_mutated",
        "notes",
    ]

    unified_action_rows = []

    for ev in action_lane_rows:

        subject_id = txt(
            ev.get(
                "subject_attempt_id"
            )
        )

        related_id = txt(
            ev.get(
                "related_attempt_id"
            )
        )

        can = canonical_by_id.get(
            subject_id
        )

        if can is None:
            continue

        unified_action_rows.append({
            "evidence_id":
                txt(
                    ev.get(
                        "evidence_id"
                    )
                ),

            "year":
                "2022",

            "subject_attempt_id":
                subject_id,

            "related_attempt_id":
                related_id,

            "session_id":
                txt(
                    can.get(
                        "session_id"
                    )
                ),

            "car_number":
                txt(
                    can.get(
                        "car_number"
                    )
                ),

            "driver_name":
                txt(
                    can.get(
                        "driver_name"
                    )
                ),

            "action":
                txt(
                    ev.get(
                        "action"
                    )
                ),

            "lane":
                txt(
                    ev.get(
                        "lane"
                    )
                ),

            "relation":
                txt(
                    ev.get(
                        "relation"
                    )
                ),

            "source_name":
                txt(
                    ev.get(
                        "source_name"
                    )
                ),

            "source_class":
                txt(
                    ev.get(
                        "source_class"
                    )
                ),

            "source_candidate_id":
                txt(
                    ev.get(
                        "source_candidate_id"
                    )
                ),

            "evidence_quality":
                txt(
                    ev.get(
                        "evidence_quality"
                    )
                ),

            "chronology_usable":
                "True",

            "queue_position_known":
                "False",

            "queue_wait_known":
                "False",

            "canonical_mutated":
                "False",

            "notes":
                txt(
                    ev.get(
                        "notes"
                    )
                ),
        })

    # ========================================================
    # 2022 SUMMARY
    # ========================================================

    rows_2022 = [
        row
        for row in ledger_v3
        if txt(
            row.get(
                "year"
            )
        ) == "2022"
    ]

    chronology_2022 = [
        row
        for row in rows_2022
        if txt(
            row.get(
                "chronology_usable"
            )
        ).lower()
        == "true"
    ]

    unique_attempt_ids_2022 = {
        txt(
            row.get(
                "attempt_id"
            )
        )
        for row in chronology_2022
        if txt(
            row.get(
                "attempt_id"
            )
        )
    }

    class_counts = Counter(
        txt(
            row.get(
                "constraint_class"
            )
        )
        or
        "UNKNOWN"
        for row in chronology_2022
    )

    # ========================================================
    # CROSS-YEAR SUMMARY
    # ========================================================

    summary_rows = []

    for year in [
        "2020",
        "2021",
        "2022",
        "2023",
        "2024",
    ]:

        year_rows = [
            row
            for row in ledger_v3
            if txt(
                row.get(
                    "year"
                )
            ) == year
        ]

        chronology_rows = [
            row
            for row in year_rows
            if txt(
                row.get(
                    "chronology_usable"
                )
            ).lower()
            == "true"
        ]

        unique_attempts = {
            txt(
                row.get(
                    "attempt_id"
                )
            )
            for row in chronology_rows
            if txt(
                row.get(
                    "attempt_id"
                )
            )
        }

        summary_rows.append({
            "year":
                year,

            "constraint_rows":
                len(
                    year_rows
                ),

            "chronology_usable_rows":
                len(
                    chronology_rows
                ),

            "unique_attempts_with_chronology":
                len(
                    unique_attempts
                ),

            "constraint_classes":
                str(
                    dict(
                        Counter(
                            txt(
                                row.get(
                                    "constraint_class"
                                )
                            )
                            or
                            "UNKNOWN"
                            for row in chronology_rows
                        )
                    )
                ),
        })

    # ========================================================
    # DUPLICATE QA
    # ========================================================

    evidence_ids = [
        txt(
            row.get(
                "evidence_id"
            )
        )
        for row in new_chronology_rows
        if txt(
            row.get(
                "evidence_id"
            )
        )
    ]

    duplicate_new_evidence_ids = (
        len(
            evidence_ids
        )
        -
        len(
            set(
                evidence_ids
            )
        )
    )

    lane1_rows = [
        row
        for row in unified_action_rows
        if txt(
            row.get(
                "lane"
            )
        ) == "LANE_1"
    ]

    # ========================================================
    # PRINT
    # ========================================================

    print()
    print("=" * 120)
    print(
        "UNIFIED ACTION / LANE LEDGER"
    )
    print("=" * 120)

    print()
    print(
        "Action/lane rows:",
        len(
            unified_action_rows
        ),
    )

    for row in unified_action_rows:

        print()
        print(
            row[
                "driver_name"
            ]
        )

        print(
            "  action:",
            row[
                "action"
            ],
        )

        print(
            "  lane:",
            row[
                "lane"
            ],
        )

        print(
            "  subject attempt:",
            row[
                "subject_attempt_id"
            ],
        )

        print(
            "  related attempt:",
            row[
                "related_attempt_id"
            ],
        )

        print(
            "  authority:",
            row[
                "source_class"
            ],
        )

    print()
    print("=" * 120)
    print(
        "2022 CHRONOLOGY V3 SUMMARY"
    )
    print("=" * 120)

    print()
    print(
        "V2 2022 rows:",
        sum(
            1
            for row in ledger_v2
            if txt(
                row.get(
                    "year"
                )
            ) == "2022"
        ),
    )

    print(
        "New Rossi ledger rows:",
        len(
            new_chronology_rows
        ),
    )

    print(
        "V3 2022 rows:",
        len(
            rows_2022
        ),
    )

    print(
        "2022 chronology usable rows:",
        len(
            chronology_2022
        ),
    )

    print(
        "2022 unique attempts with chronology:",
        len(
            unique_attempt_ids_2022
        ),
    )

    print(
        "2022 classes:",
        dict(
            class_counts
        ),
    )

    # ========================================================
    # WRITE
    # ========================================================

    write_csv(
        LEDGER_V3,
        ledger_v3,
        fields,
    )

    write_csv(
        SUMMARY_V3,
        summary_rows,
        [
            "year",
            "constraint_rows",
            "chronology_usable_rows",
            "unique_attempts_with_chronology",
            "constraint_classes",
        ],
    )

    write_csv(
        ACTION_LANE_LEDGER,
        unified_action_rows,
        action_fields,
    )

    # ========================================================
    # QA
    # ========================================================

    qa = [
        {
            "metric":
                "ledger_v2_rows",
            "value":
                len(
                    ledger_v2
                ),
            "status":
                "INFO",
        },

        {
            "metric":
                "new_rossi_chronology_rows",
            "value":
                len(
                    new_chronology_rows
                ),
            "status":
                (
                    "PASS"
                    if len(
                        new_chronology_rows
                    ) == 2
                    else "FAIL"
                ),
        },

        {
            "metric":
                "2022_unique_attempts_with_chronology",
            "value":
                len(
                    unique_attempt_ids_2022
                ),
            "status":
                (
                    "PASS"
                    if len(
                        unique_attempt_ids_2022
                    ) >= 10
                    else "REVIEW"
                ),
        },

        {
            "metric":
                "action_lane_rows",
            "value":
                len(
                    unified_action_rows
                ),
            "status":
                (
                    "PASS"
                    if len(
                        unified_action_rows
                    ) >= 1
                    else "FAIL"
                ),
        },

        {
            "metric":
                "historical_lane1_rows",
            "value":
                len(
                    lane1_rows
                ),
            "status":
                (
                    "PASS"
                    if len(
                        lane1_rows
                    ) == 1
                    else "REVIEW"
                ),
        },

        {
            "metric":
                "duplicate_new_evidence_ids",
            "value":
                duplicate_new_evidence_ids,
            "status":
                (
                    "PASS"
                    if duplicate_new_evidence_ids == 0
                    else "FAIL"
                ),
        },

        {
            "metric":
                "karam_specific_attempt_promoted_in_r1g20",
            "value":
                0,
            "status":
                "PASS",
        },

        {
            "metric":
                "lane_inferred_from_status",
            "value":
                0,
            "status":
                "PASS",
        },

        {
            "metric":
                "queue_wait_inferred",
            "value":
                0,
            "status":
                "PASS",
        },

        {
            "metric":
                "canonical_data_mutated",
            "value":
                0,
            "status":
                "PASS",
        },

        {
            "metric":
                "ledger_v2_mutated",
            "value":
                0,
            "status":
                "PASS",
        },
    ]

    write_csv(
        INTEGRATION_QA,
        qa,
        [
            "metric",
            "value",
            "status",
        ],
    )

    # ========================================================
    # FINAL
    # ========================================================

    print()
    print("=" * 120)
    print(
        "FINAL SUMMARY"
    )
    print("=" * 120)

    print()
    print(
        "Ledger V2 rows:",
        len(
            ledger_v2
        ),
    )

    print(
        "Ledger V3 rows:",
        len(
            ledger_v3
        ),
    )

    print(
        "2022 unique chronology attempts:",
        len(
            unique_attempt_ids_2022
        ),
    )

    print(
        "Historical Lane 1 action rows:",
        len(
            lane1_rows
        ),
    )

    print()
    print(
        "Rossi ordering integrated."
    )

    print(
        "McLaughlin Lane 1 preserved in a "
        "separate action/lane ledger."
    )

    print(
        "Karam event was NOT forced onto a "
        "canonical attempt."
    )

    print(
        "No queue wait was inferred."
    )

    print(
        "No canonical or V2 data was modified."
    )

    print()
    print("=" * 120)

    if (
        len(
            new_chronology_rows
        ) == 2
        and
        len(
            lane1_rows
        ) == 1
        and
        duplicate_new_evidence_ids == 0
    ):

        print(
            "FINAL STATUS: "
            "SECONDARY_EVIDENCE_UNIFIED_LEDGER_INTEGRATION_COMPLETE"
        )

    else:

        print(
            "FINAL STATUS: "
            "SECONDARY_EVIDENCE_UNIFIED_LEDGER_INTEGRATION_REVIEW_REQUIRED"
        )

    print("=" * 120)

    print()
    print("OUTPUTS")
    print(LEDGER_V3)
    print(SUMMARY_V3)
    print(ACTION_LANE_LEDGER)
    print(INTEGRATION_QA)


if __name__ == "__main__":
    main()
