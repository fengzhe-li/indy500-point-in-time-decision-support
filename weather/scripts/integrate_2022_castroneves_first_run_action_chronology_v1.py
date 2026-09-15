from pathlib import Path
import csv


CANONICAL = Path(
    "data/canonical/v1/attempts.csv"
)

RESULT_MATCHES = Path(
    "weather/output/"
    "chronology_rescue_2022_result_to_canonical_attempt_matches_v2.csv"
)

CASTRONEVES_EVIDENCE = Path(
    "weather/output/"
    "chronology_rescue_2022_castroneves_repeat_pair_evidence_v1.csv"
)

ACTION_LEDGER_V1 = Path(
    "weather/output/"
    "unified_attempt_action_lane_ledger_v1.csv"
)

CHRONOLOGY_LEDGER_V3 = Path(
    "weather/output/"
    "unified_attempt_chronology_constraint_ledger_v3.csv"
)


OUTPUT_DIR = Path(
    "weather/output"
)

ADJUDICATED_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_castroneves_first_run_final_adjudication_v1.csv"
)

ACTION_LEDGER_V2 = (
    OUTPUT_DIR
    / "unified_attempt_action_lane_ledger_v2.csv"
)

CHRONOLOGY_LEDGER_V4 = (
    OUTPUT_DIR
    / "unified_attempt_chronology_constraint_ledger_v4.csv"
)

SUMMARY_V4 = (
    OUTPUT_DIR
    / "unified_attempt_chronology_constraint_summary_v4.csv"
)

QA_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_castroneves_final_integration_v1_qa.csv"
)


def read_csv(path):
    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as f:
        return list(csv.DictReader(f))


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


def speed_close(a, b, tol=0.003):
    try:
        return abs(
            float(txt(a)) -
            float(txt(b))
        ) <= tol
    except Exception:
        return False


def canonical_speed(row):
    for field in [
        "four_lap_average_speed_mph",
        "average_speed_mph",
        "speed_mph",
    ]:
        value = txt(
            row.get(field)
        )

        if value:
            return value

    return ""


def is_2022(row):
    return (
        txt(
            row.get("year")
        ) == "2022"
        or
        "2022" in txt(
            row.get("session_id")
        )
    )


def truthy(v):
    return txt(v).lower() in {
        "true",
        "1",
        "yes",
    }


def main():

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print()
    print("=" * 120)
    print(
        "R1G.25C — 2022 HELIO CASTRONEVES "
        "FIRST-RUN ACTION + CHRONOLOGY FINAL INTEGRATION V1"
    )
    print("=" * 120)

    inputs = [
        CANONICAL,
        RESULT_MATCHES,
        CASTRONEVES_EVIDENCE,
        ACTION_LEDGER_V1,
        CHRONOLOGY_LEDGER_V3,
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
            "CASTRONEVES_FINAL_INTEGRATION_INPUT_MISSING"
        )
        return

    canonical = read_csv(
        CANONICAL
    )

    results = read_csv(
        RESULT_MATCHES
    )

    evidence = read_csv(
        CASTRONEVES_EVIDENCE
    )

    action_v1 = read_csv(
        ACTION_LEDGER_V1
    )

    chronology_v3 = read_csv(
        CHRONOLOGY_LEDGER_V3
    )

    # ========================================================
    # TRUE #06 CANONICAL SUBSET
    #
    # Preserve car number as string.
    # "06" != "6"
    # ========================================================

    car06 = [
        row
        for row in canonical
        if (
            is_2022(row)
            and
            txt(
                row.get("car_number")
            ) == "06"
        )
    ]

    first_rows = [
        row
        for row in car06
        if txt(
            row.get(
                "car_attempt_index"
            )
        ) == "1"
    ]

    second_rows = [
        row
        for row in car06
        if txt(
            row.get(
                "car_attempt_index"
            )
        ) == "2"
    ]

    print()
    print("=" * 120)
    print(
        "TRUE #06 CASTRONEVES CANONICAL CHECK"
    )
    print("=" * 120)

    print()
    print(
        "#06 canonical rows:",
        len(car06),
    )

    print(
        "index=1 rows:",
        len(first_rows),
    )

    print(
        "index=2 rows:",
        len(second_rows),
    )

    structure_ok = (
        len(car06) == 2
        and
        len(first_rows) == 1
        and
        len(second_rows) == 1
        and
        speed_close(
            canonical_speed(
                first_rows[0]
            ),
            "225.482",
        )
        and
        speed_close(
            canonical_speed(
                second_rows[0]
            ),
            "229.630",
        )
    )

    if not structure_ok:

        print()
        print(
            "FINAL STATUS: "
            "CASTRONEVES_TRUE_CAR06_STRUCTURE_REVIEW_REQUIRED"
        )
        return

    first = first_rows[0]
    second = second_rows[0]

    first_id = txt(
        first.get("attempt_id")
    )

    second_id = txt(
        second.get("attempt_id")
    )

    print()
    print(
        "FIRST attempt_id:",
        first_id,
    )

    print(
        "FIRST speed:",
        canonical_speed(first),
    )

    print(
        "SECOND attempt_id:",
        second_id,
    )

    print(
        "SECOND speed:",
        canonical_speed(second),
    )

    # ========================================================
    # RESULT MATCHES BY ATTEMPT_ID
    #
    # Do NOT filter result-match table by car_number because
    # that file normalized #06 to #6.
    # ========================================================

    result_by_attempt = {
        txt(
            row.get("attempt_id")
        ): row
        for row in results
        if txt(
            row.get("attempt_id")
        )
    }

    first_result = result_by_attempt.get(
        first_id,
        {},
    )

    second_result = result_by_attempt.get(
        second_id,
        {},
    )

    print()
    print("=" * 120)
    print(
        "ATTEMPT-ID-LINKED OFFICIAL RESULT CHECK"
    )
    print("=" * 120)

    print()
    print(
        "FIRST result link:",
        "FOUND"
        if first_result
        else "MISSING",
    )

    print(
        "  result car_number:",
        repr(
            txt(
                first_result.get(
                    "car_number"
                )
            )
        ),
    )

    print(
        "  official speed:",
        repr(
            txt(
                first_result.get(
                    "official_speed_mph"
                )
            )
        ),
    )

    print(
        "  official status:",
        repr(
            txt(
                first_result.get(
                    "official_status"
                )
            )
        ),
    )

    print()
    print(
        "SECOND result link:",
        "FOUND"
        if second_result
        else "MISSING",
    )

    print(
        "  result car_number:",
        repr(
            txt(
                second_result.get(
                    "car_number"
                )
            )
        ),
    )

    print(
        "  official speed:",
        repr(
            txt(
                second_result.get(
                    "official_speed_mph"
                )
            )
        ),
    )

    print(
        "  official status:",
        repr(
            txt(
                second_result.get(
                    "official_status"
                )
            )
        ),
    )

    result_identity_ok = (
        bool(first_result)
        and
        bool(second_result)
        and
        speed_close(
            first_result.get(
                "official_speed_mph"
            ),
            "225.482",
        )
        and
        speed_close(
            second_result.get(
                "official_speed_mph"
            ),
            "229.630",
        )
    )

    # ========================================================
    # DIRECT NARRATIVE
    # ========================================================

    qualifying_evidence = []

    for row in evidence:

        sentence = txt(
            row.get("sentence")
        )

        lower = sentence.lower()

        if (
            "castroneves" in lower
            and
            "first run" in lower
            and
            (
                "bailing out" in lower
                or
                "bailed out" in lower
            )
        ):

            qualifying_evidence.append(
                row
            )

    print()
    print("=" * 120)
    print(
        "DIRECT FIRST-RUN NARRATIVE"
    )
    print("=" * 120)

    print()
    print(
        "Direct evidence rows:",
        len(
            qualifying_evidence
        ),
    )

    for row in qualifying_evidence:

        print()
        print(
            "source:",
            txt(
                row.get(
                    "source_name"
                )
            ),
        )

        print(
            txt(
                row.get(
                    "sentence"
                )
            )
        )

    evidence_ok = (
        len(
            qualifying_evidence
        ) >= 1
    )

    # ========================================================
    # FINAL ADJUDICATION
    #
    # Conservative semantics:
    #
    # "BAILED_OUT_OF_FIRST_RUN"
    #
    # We preserve the secondary source wording.
    # We DO NOT reinterpret this as a technical aborted lap.
    # We DO NOT infer Lane 1 / Lane 2.
    # ========================================================

    adjudicated = []

    if (
        structure_ok
        and
        result_identity_ok
        and
        evidence_ok
    ):

        source = qualifying_evidence[0]

        adjudicated.append({
            "evidence_id":
                "R1G25C-CASTRONEVES-FIRST-RUN-BAILOUT",

            "year":
                "2022",

            "driver_name":
                "Helio Castroneves",

            "car_number":
                "06",

            "subject_attempt_id":
                first_id,

            "related_attempt_id":
                second_id,

            "subject_speed_mph":
                canonical_speed(first),

            "related_speed_mph":
                canonical_speed(second),

            "official_subject_status":
                txt(
                    first_result.get(
                        "official_status"
                    )
                ),

            "action":
                "BAILED_OUT_OF_FIRST_RUN",

            "lane":
                "UNKNOWN",

            "relation":
                "FIRST_RUN_BEFORE_SECOND_RUN",

            "source_name":
                txt(
                    source.get(
                        "source_name"
                    )
                ),

            "source_class":
                txt(
                    source.get(
                        "source_class"
                    )
                )
                or
                "REPUTABLE_SECONDARY_EDITORIAL",

            "source_evidence_id":
                txt(
                    source.get(
                        "evidence_id"
                    )
                ),

            "evidence_quality":
                "DIRECT_SECONDARY_FIRST_RUN_ACTION",

            "chronology_usable":
                "True",

            "queue_position_known":
                "False",

            "queue_wait_known":
                "False",

            "promotion_status":
                "PROMOTED_ACTION_AND_ORDERING",

            "notes":
                (
                    "The Race explicitly describes Castroneves "
                    "as bailing out of his first run. "
                    "The canonical #06 subset uniquely identifies "
                    "225.482 as car_attempt_index=1 and 229.630 "
                    "as car_attempt_index=2. "
                    "Result links are verified by attempt_id, "
                    "not by normalized car_number. "
                    "No technical abort semantics, lane, or "
                    "wall-clock timestamp are inferred."
                ),
        })

    # ========================================================
    # ACTION LEDGER V2
    # ========================================================

    action_fields = list(
        action_v1[0].keys()
    )

    for field in [
        "subject_speed_mph",
        "related_speed_mph",
        "official_subject_status",
        "source_evidence_id",
        "promotion_status",
    ]:

        if field not in action_fields:
            action_fields.append(field)

    action_v2 = []

    for row in action_v1:

        out = {
            field: ""
            for field in action_fields
        }

        for key, value in row.items():

            if key in out:
                out[key] = value

        action_v2.append(out)

    if adjudicated:

        ev = adjudicated[0]

        out = {
            field: ""
            for field in action_fields
        }

        values = {
            "evidence_id":
                ev["evidence_id"],

            "year":
                "2022",

            "subject_attempt_id":
                first_id,

            "related_attempt_id":
                second_id,

            "session_id":
                txt(
                    first.get(
                        "session_id"
                    )
                ),

            "car_number":
                "06",

            "driver_name":
                "Helio Castroneves",

            "action":
                ev["action"],

            "lane":
                "UNKNOWN",

            "relation":
                ev["relation"],

            "source_name":
                ev["source_name"],

            "source_class":
                ev["source_class"],

            "evidence_quality":
                ev["evidence_quality"],

            "chronology_usable":
                "True",

            "queue_position_known":
                "False",

            "queue_wait_known":
                "False",

            "canonical_mutated":
                "False",

            "notes":
                ev["notes"],

            "subject_speed_mph":
                ev["subject_speed_mph"],

            "related_speed_mph":
                ev["related_speed_mph"],

            "official_subject_status":
                ev["official_subject_status"],

            "source_evidence_id":
                ev["source_evidence_id"],

            "promotion_status":
                ev["promotion_status"],
        }

        for key, value in values.items():

            if key in out:
                out[key] = value

        action_v2.append(out)

    # ========================================================
    # CHRONOLOGY LEDGER V4
    #
    # Add two role rows for one ordering relation:
    #
    #   first attempt BEFORE second attempt
    #
    # ========================================================

    chronology_fields = list(
        chronology_v3[0].keys()
    )

    for field in [
        "related_attempt_id",
        "ordering_role",
        "evidence_type",
        "action",
        "lane",
        "source_candidate_id",
        "evidence_quality",
    ]:

        if field not in chronology_fields:
            chronology_fields.append(field)

    chronology_v4 = []

    for row in chronology_v3:

        out = {
            field: ""
            for field in chronology_fields
        }

        for key, value in row.items():

            if key in out:
                out[key] = value

        chronology_v4.append(out)

    new_chronology_rows = []

    if adjudicated:

        specs = [
            (
                first,
                first_id,
                second_id,
                "FROM",
            ),
            (
                second,
                second_id,
                first_id,
                "TO",
            ),
        ]

        for can, aid, related, role in specs:

            row = {
                field: ""
                for field in chronology_fields
            }

            values = {
                "attempt_id":
                    aid,

                "session_id":
                    txt(
                        can.get(
                            "session_id"
                        )
                    ),

                "year":
                    "2022",

                "car_number":
                    "06",

                "driver_name":
                    "Helio Castroneves",

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
                        "R1G25C-CASTRONEVES-FIRST-SECOND:"
                        + role
                    ),

                "evidence_stage":
                    "R1G25C_INTEGRATED",

                "source_authority":
                    adjudicated[0][
                        "source_class"
                    ],

                "source_title":
                    (
                        "Castroneves first-run bailout "
                        "and later second run"
                    ),

                "time_lower_utc":
                    "",

                "time_upper_utc":
                    "",

                "time_midpoint_utc":
                    "",

                "ordering_relation":
                    "FIRST_RUN_BEFORE_SECOND_RUN",

                "related_attempt_id":
                    related,

                "ordering_role":
                    role,

                "evidence_type":
                    "ORDERING",

                "action":
                    (
                        "BAILED_OUT_OF_FIRST_RUN"
                        if role == "FROM"
                        else "LATER_SECOND_RUN"
                    ),

                "lane":
                    "UNKNOWN",

                "source_candidate_id":
                    adjudicated[0][
                        "source_evidence_id"
                    ],

                "evidence_quality":
                    adjudicated[0][
                        "evidence_quality"
                    ],

                "evidence_summary":
                    (
                        "Direct secondary narrative identifies "
                        "Castroneves' first run; canonical #06 "
                        "attempt indices identify first and second "
                        "runs. No timestamp or lane inferred."
                    ),

                "notes":
                    (
                        "Result linkage verified by attempt_id "
                        "because result-match car_number formatting "
                        "does not preserve #06 versus #6."
                    ),
            }

            for key, value in values.items():

                if key in row:
                    row[key] = value

            new_chronology_rows.append(row)

        chronology_v4.extend(
            new_chronology_rows
        )

    # ========================================================
    # SUMMARY
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
            for row in chronology_v4
            if txt(
                row.get("year")
            ) == year
        ]

        chronology_rows = [
            row
            for row in year_rows
            if truthy(
                row.get(
                    "chronology_usable"
                )
            )
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
                len(year_rows),

            "chronology_usable_rows":
                len(
                    chronology_rows
                ),

            "unique_attempts_with_chronology":
                len(
                    unique_attempts
                ),
        })

    chronology_2022_ids = {
        txt(
            row.get(
                "attempt_id"
            )
        )
        for row in chronology_v4
        if (
            txt(
                row.get("year")
            ) == "2022"
            and
            truthy(
                row.get(
                    "chronology_usable"
                )
            )
            and
            txt(
                row.get(
                    "attempt_id"
                )
            )
        )
    }

    # ========================================================
    # DUPLICATE QA
    # ========================================================

    action_evidence_ids = [
        txt(
            row.get(
                "evidence_id"
            )
        )
        for row in action_v2
        if txt(
            row.get(
                "evidence_id"
            )
        )
    ]

    duplicate_action_ids = (
        len(action_evidence_ids)
        -
        len(
            set(
                action_evidence_ids
            )
        )
    )

    # ========================================================
    # WRITE
    # ========================================================

    write_csv(
        ADJUDICATED_OUT,
        adjudicated,
        [
            "evidence_id",
            "year",
            "driver_name",
            "car_number",
            "subject_attempt_id",
            "related_attempt_id",
            "subject_speed_mph",
            "related_speed_mph",
            "official_subject_status",
            "action",
            "lane",
            "relation",
            "source_name",
            "source_class",
            "source_evidence_id",
            "evidence_quality",
            "chronology_usable",
            "queue_position_known",
            "queue_wait_known",
            "promotion_status",
            "notes",
        ],
    )

    write_csv(
        ACTION_LEDGER_V2,
        action_v2,
        action_fields,
    )

    write_csv(
        CHRONOLOGY_LEDGER_V4,
        chronology_v4,
        chronology_fields,
    )

    write_csv(
        SUMMARY_V4,
        summary_rows,
        [
            "year",
            "constraint_rows",
            "chronology_usable_rows",
            "unique_attempts_with_chronology",
        ],
    )

    qa_rows = [
        {
            "metric":
                "true_car06_structure_ok",

            "value":
                int(structure_ok),

            "status":
                "PASS"
                if structure_ok
                else "FAIL",
        },

        {
            "metric":
                "attempt_id_result_link_ok",

            "value":
                int(
                    result_identity_ok
                ),

            "status":
                "PASS"
                if result_identity_ok
                else "FAIL",
        },

        {
            "metric":
                "direct_first_run_evidence_rows",

            "value":
                len(
                    qualifying_evidence
                ),

            "status":
                "PASS"
                if evidence_ok
                else "FAIL",
        },

        {
            "metric":
                "promoted_action_rows",

            "value":
                len(adjudicated),

            "status":
                "PASS"
                if len(adjudicated) == 1
                else "FAIL",
        },

        {
            "metric":
                "new_chronology_rows",

            "value":
                len(
                    new_chronology_rows
                ),

            "status":
                "PASS"
                if len(
                    new_chronology_rows
                ) == 2
                else "FAIL",
        },

        {
            "metric":
                "2022_unique_attempts_with_chronology",

            "value":
                len(
                    chronology_2022_ids
                ),

            "status":
                "PASS"
                if len(
                    chronology_2022_ids
                ) >= 12
                else "REVIEW",
        },

        {
            "metric":
                "technical_abort_claimed",

            "value":
                0,

            "status":
                "PASS",
        },

        {
            "metric":
                "lane_claimed",

            "value":
                0,

            "status":
                "PASS",
        },

        {
            "metric":
                "car_number_used_for_result_link",

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
                "duplicate_action_evidence_ids",

            "value":
                duplicate_action_ids,

            "status":
                "PASS"
                if duplicate_action_ids == 0
                else "FAIL",
        },

        {
            "metric":
                "canonical_data_mutated",

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

    # ========================================================
    # PRINT FINAL
    # ========================================================

    print()
    print("=" * 120)
    print(
        "PROMOTED CASTRONEVES ACTION"
    )
    print("=" * 120)

    if adjudicated:

        ev = adjudicated[0]

        print()
        print(
            "driver:",
            ev["driver_name"],
        )

        print(
            "subject attempt:",
            ev[
                "subject_attempt_id"
            ],
        )

        print(
            "subject speed:",
            ev[
                "subject_speed_mph"
            ],
        )

        print(
            "action:",
            ev["action"],
        )

        print(
            "related second attempt:",
            ev[
                "related_attempt_id"
            ],
        )

        print(
            "related speed:",
            ev[
                "related_speed_mph"
            ],
        )

        print(
            "lane:",
            ev["lane"],
        )

    print()
    print("=" * 120)
    print(
        "2022 CHRONOLOGY UPDATE"
    )
    print("=" * 120)

    print()
    print(
        "New chronology rows:",
        len(
            new_chronology_rows
        ),
    )

    print(
        "2022 unique attempts with chronology:",
        len(
            chronology_2022_ids
        ),
    )

    print()
    print("=" * 120)
    print(
        "FINAL SUMMARY"
    )
    print("=" * 120)

    print()
    print(
        "Action ledger V1 rows:",
        len(action_v1),
    )

    print(
        "Action ledger V2 rows:",
        len(action_v2),
    )

    print(
        "Chronology ledger V3 rows:",
        len(chronology_v3),
    )

    print(
        "Chronology ledger V4 rows:",
        len(chronology_v4),
    )

    print()
    print(
        "Castroneves first-run action is preserved "
        "using source wording only."
    )

    print(
        "No technical abort interpretation is asserted."
    )

    print(
        "No Lane 1/Lane 2 is asserted."
    )

    print(
        "No exact timestamp is asserted."
    )

    print(
        "Official result linkage used attempt_id, "
        "not normalized car_number."
    )

    print(
        "No canonical data was modified."
    )

    print()
    print("=" * 120)

    if (
        structure_ok
        and
        result_identity_ok
        and
        evidence_ok
        and
        len(adjudicated) == 1
        and
        len(
            new_chronology_rows
        ) == 2
        and
        duplicate_action_ids == 0
    ):

        print(
            "FINAL STATUS: "
            "CASTRONEVES_FIRST_RUN_ACTION_AND_CHRONOLOGY_INTEGRATED"
        )

    else:

        print(
            "FINAL STATUS: "
            "CASTRONEVES_FINAL_INTEGRATION_REVIEW_REQUIRED"
        )

    print("=" * 120)

    print()
    print("OUTPUTS")
    print(ADJUDICATED_OUT)
    print(ACTION_LEDGER_V2)
    print(CHRONOLOGY_LEDGER_V4)
    print(SUMMARY_V4)
    print(QA_OUT)


if __name__ == "__main__":
    main()
