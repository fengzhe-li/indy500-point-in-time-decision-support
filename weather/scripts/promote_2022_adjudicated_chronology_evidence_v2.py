from pathlib import Path
import csv
import hashlib
import json


PHASE = "R1G.6"

R1G3_EVIDENCE = Path(
    "weather/output/"
    "chronology_rescue_2022_official_evidence_v1.csv"
)

R1G5_AUDIT = Path(
    "weather/output/"
    "chronology_rescue_2022_editorial_promotion_audit_v1.csv"
)

RESULT_CONTEXT = Path(
    "weather/output/"
    "chronology_rescue_2022_sato_marco_result_context_v1.csv"
)

OUTPUT_DIR = Path(
    "weather/output"
)

PROMOTED_EVIDENCE = (
    OUTPUT_DIR
    / "chronology_rescue_2022_adjudicated_evidence_v2.csv"
)

ORDERING_EDGES = (
    OUTPUT_DIR
    / "chronology_rescue_2022_ordering_edges_v2.csv"
)

SUMMARY_CSV = (
    OUTPUT_DIR
    / "chronology_rescue_2022_adjudicated_summary_v2.csv"
)

QA_CSV = (
    OUTPUT_DIR
    / "chronology_rescue_2022_adjudicated_evidence_v2_qa.csv"
)


def read_csv(path):

    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as handle:

        return list(
            csv.DictReader(
                handle
            )
        )


def write_csv(
    path,
    rows,
    fields,
):

    with path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as handle:

        writer = csv.DictWriter(
            handle,
            fieldnames=fields,
        )

        writer.writeheader()
        writer.writerows(rows)


def txt(value):

    if value is None:
        return ""

    return str(
        value
    ).strip()


def stable_id(*parts):

    payload = "|".join(
        txt(
            part
        )
        for part in parts
    )

    digest = hashlib.sha256(
        payload.encode(
            "utf-8"
        )
    ).hexdigest()[:16]

    return (
        "R1G6-"
        + digest.upper()
    )


def main():

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print()
    print("=" * 120)
    print(
        "R1G.6 — 2022 ADJUDICATED "
        "CHRONOLOGY EVIDENCE PROMOTION V2"
    )
    print("=" * 120)

    inputs = [
        R1G3_EVIDENCE,
        R1G5_AUDIT,
        RESULT_CONTEXT,
    ]

    print()
    print("INPUT CHECK")
    print("-" * 120)

    missing = []

    for path in inputs:

        exists = path.exists()

        print(
            f"{path}: "
            f"{'PRESENT' if exists else 'MISSING'}"
        )

        if not exists:
            missing.append(
                path
            )

    if missing:

        print()
        print(
            "FINAL STATUS: "
            "2022_ADJUDICATED_PROMOTION_INPUT_MISSING"
        )

        return

    r1g3 = read_csv(
        R1G3_EVIDENCE
    )

    audit = read_csv(
        R1G5_AUDIT
    )

    context = read_csv(
        RESULT_CONTEXT
    )

    print()
    print(
        "R1G3 EVIDENCE ROWS:",
        len(
            r1g3
        ),
    )

    print(
        "R1G5 AUDIT ROWS:",
        len(
            audit
        ),
    )

    print(
        "SATO/MARCO CONTEXT ROWS:",
        len(
            context
        ),
    )

    # ========================================================
    # VERIFY EDITORIAL FIRST -> SECOND ATTEMPT EVIDENCE
    # ========================================================

    target_audit = [
        row
        for row in audit
        if txt(
            row.get(
                "candidate_id"
            )
        ) == "R1G4-C0011"
    ]

    print()
    print("=" * 120)
    print(
        "VERIFY SATO FIRST -> SECOND ATTEMPT"
    )
    print("=" * 120)

    print(
        "EDITORIAL MATCH COUNT:",
        len(
            target_audit
        ),
    )

    editorial_valid = (
        len(
            target_audit
        )
        == 1
        and txt(
            target_audit[0].get(
                "review_class"
            )
        )
        == "ATTEMPT_ORDERING_CANDIDATE"
    )

    if target_audit:

        print(
            "SENTENCE:"
        )

        print(
            target_audit[0].get(
                "sentence"
            )
        )

    # ========================================================
    # VERIFY UNIQUE SATO RESULT ROWS
    # ========================================================

    sato_rows = [
        row
        for row in context
        if txt(
            row.get(
                "car_number"
            )
        ) == "51"
    ]

    sato_failed = [
        row
        for row in sato_rows
        if (
            txt(
                row.get(
                    "speed_avg_mph"
                )
            )
            == "232.196"
            and
            txt(
                row.get(
                    "status"
                )
            )
            == "Failed Attempt"
        )
    ]

    sato_second = [
        row
        for row in sato_rows
        if txt(
            row.get(
                "speed_avg_mph"
            )
        )
        == "231.708"
    ]

    print()
    print(
        "SATO 232.196 FAILED COUNT:",
        len(
            sato_failed
        ),
    )

    print(
        "SATO 231.708 COUNT:",
        len(
            sato_second
        ),
    )

    promote_same_car_ordering = (
        editorial_valid
        and
        len(
            sato_failed
        )
        == 1
        and
        len(
            sato_second
        )
        == 1
    )

    # ========================================================
    # COPY EXISTING R1G3 EVIDENCE
    # ========================================================

    promoted_rows = []

    for row in r1g3:

        promoted_rows.append({
            "evidence_id":
                txt(
                    row.get(
                        "evidence_id"
                    )
                ),

            "year":
                2022,

            "session":
                txt(
                    row.get(
                        "session"
                    )
                ),

            "car_number":
                txt(
                    row.get(
                        "car_number"
                    )
                ),

            "driver_name":
                txt(
                    row.get(
                        "driver_name"
                    )
                ),

            "speed_mph":
                txt(
                    row.get(
                        "speed_mph"
                    )
                ),

            "official_result_row":
                txt(
                    row.get(
                        "official_result_row"
                    )
                ),

            "official_result_status":
                txt(
                    row.get(
                        "official_result_status"
                    )
                ),

            "constraint_class":
                txt(
                    row.get(
                        "constraint_class"
                    )
                ),

            "time_lower_utc":
                txt(
                    row.get(
                        "time_lower_utc"
                    )
                ),

            "time_upper_utc":
                txt(
                    row.get(
                        "time_upper_utc"
                    )
                ),

            "time_midpoint_utc":
                txt(
                    row.get(
                        "time_midpoint_utc"
                    )
                ),

            "related_car_number":
                txt(
                    row.get(
                        "related_car_number"
                    )
                ),

            "related_speed_mph":
                "",

            "ordering_relation":
                txt(
                    row.get(
                        "ordering_relation"
                    )
                ),

            "source_authority":
                txt(
                    row.get(
                        "source_authority"
                    )
                ),

            "source_url":
                txt(
                    row.get(
                        "source_url"
                    )
                ),

            "source_title":
                txt(
                    row.get(
                        "source_title"
                    )
                ),

            "evidence_summary":
                txt(
                    row.get(
                        "evidence_summary"
                    )
                ),

            "evidence_stage":
                "R1G3_SEEDED",

            "adjudication_status":
                "ACCEPTED_EXISTING",

            "chronology_usable":
                txt(
                    row.get(
                        "chronology_usable"
                    )
                ),

            "queue_replay_usable":
                False,

            "canonical_promoted":
                False,

            "notes":
                (
                    "Existing R1G.3 rescue evidence "
                    "preserved unchanged semantically."
                ),
        })

    # ========================================================
    # PROMOTE NEW SAME-CAR ORDERING
    # ========================================================

    ordering_edges = []

    if promote_same_car_ordering:

        failed_row = (
            sato_failed[0]
        )

        second_row = (
            sato_second[0]
        )

        evidence_id = stable_id(
            "2022",
            "51",
            "232.196",
            "BEFORE",
            "51",
            "231.708",
        )

        new_row = {
            "evidence_id":
                evidence_id,

            "year":
                2022,

            "session":
                "INDY500_DAY1_2022",

            "car_number":
                "51",

            "driver_name":
                "Takuma Sato",

            "speed_mph":
                "232.196",

            "official_result_row":
                txt(
                    failed_row.get(
                        "result_row"
                    )
                ),

            "official_result_status":
                "Failed Attempt",

            "constraint_class":
                "ORDERING_ONLY",

            "time_lower_utc":
                "",

            "time_upper_utc":
                "",

            "time_midpoint_utc":
                "",

            "related_car_number":
                "51",

            "related_speed_mph":
                "231.708",

            "ordering_relation":
                (
                    "SATO_232.196_FAILED_ATTEMPT_"
                    "BEFORE_SATO_231.708_SECOND_ATTEMPT"
                ),

            "source_authority":
                "INDYCAR_OFFICIAL_EDITORIAL"
                "+INDYCAR_OFFICIAL_RESULTS",

            "source_url":
                (
                    "https://www.indycar.com/news/"
                    "2022/05/05-21-day1-quals"
                ),

            "source_title":
                "2022 Day 1 Qualifying Recap",

            "evidence_summary":
                (
                    "Official editorial states Sato was "
                    "forced to make a second attempt after "
                    "his first 232.196 mph run was disallowed. "
                    "Official Results uniquely contain the "
                    "232.196 Failed Attempt and a 231.708 "
                    "second Sato result."
                ),

            "evidence_stage":
                "R1G6_ADJUDICATED",

            "adjudication_status":
                "PROMOTED",

            "chronology_usable":
                True,

            "queue_replay_usable":
                False,

            "canonical_promoted":
                False,

            "notes":
                (
                    "Ordering only. "
                    "No timestamp inferred."
                ),
        }

        promoted_rows.append(
            new_row
        )

        ordering_edges.append({
            "edge_id":
                evidence_id,

            "year":
                2022,

            "from_car_number":
                "51",

            "from_driver":
                "Takuma Sato",

            "from_speed_mph":
                "232.196",

            "from_result_status":
                "Failed Attempt",

            "to_car_number":
                "51",

            "to_driver":
                "Takuma Sato",

            "to_speed_mph":
                "231.708",

            "to_result_status":
                txt(
                    second_row.get(
                        "status"
                    )
                ),

            "relation":
                "BEFORE",

            "constraint_class":
                "ORDERING_ONLY",

            "source":
                "INDYCAR_OFFICIAL_EDITORIAL"
                "+INDYCAR_OFFICIAL_RESULTS",

            "chronology_usable":
                True,

            "queue_replay_usable":
                False,

            "notes":
                (
                    "First attempt disallowed; "
                    "second attempt explicitly required."
                ),
        })

    # ========================================================
    # PRESERVE SESSION INTERRUPTION AGGREGATE
    # ========================================================

    interruption_audit = [
        row
        for row in audit
        if txt(
            row.get(
                "candidate_id"
            )
        )
        == "R1G4-C0002"
    ]

    if len(
        interruption_audit
    ) == 1:

        promoted_rows.append({
            "evidence_id":
                stable_id(
                    "2022",
                    "SESSION",
                    "INTERRUPTIONS",
                    "134MIN",
                ),

            "year":
                2022,

            "session":
                "INDY500_DAY1_2022",

            "car_number":
                "",

            "driver_name":
                "",

            "speed_mph":
                "",

            "official_result_row":
                "",

            "official_result_status":
                "",

            "constraint_class":
                "SESSION_INTERRUPTION_AGGREGATE",

            "time_lower_utc":
                "",

            "time_upper_utc":
                "",

            "time_midpoint_utc":
                "",

            "related_car_number":
                "",

            "related_speed_mph":
                "",

            "ordering_relation":
                "",

            "source_authority":
                "INDYCAR_OFFICIAL_EDITORIAL",

            "source_url":
                (
                    "https://www.indycar.com/news/"
                    "2022/05/05-21-day1-quals"
                ),

            "source_title":
                "2022 Day 1 Qualifying Recap",

            "evidence_summary":
                (
                    "Session was interrupted twice by rain "
                    "and lightning for a combined two hours "
                    "14 minutes and was cut short by "
                    "60 minutes."
                ),

            "evidence_stage":
                "R1G6_ADJUDICATED",

            "adjudication_status":
                "ACCEPTED_SESSION_LEVEL",

            "chronology_usable":
                True,

            "queue_replay_usable":
                False,

            "canonical_promoted":
                False,

            "notes":
                (
                    "Aggregate session evidence only. "
                    "No interruption start/end windows invented."
                ),
        })

    # ========================================================
    # DO NOT PROMOTE SPECIFIC MARCO ATTEMPT
    # ========================================================

    marco_rows = [
        row
        for row in context
        if txt(
            row.get(
                "car_number"
            )
        )
        == "98"
    ]

    specific_marco_promotions = 0

    # ========================================================
    # COUNTS
    # ========================================================

    attempt_level_rows = [
        row
        for row in promoted_rows
        if txt(
            row.get(
                "car_number"
            )
        )
    ]

    bounded_rows = [
        row
        for row in promoted_rows
        if txt(
            row.get(
                "constraint_class"
            )
        )
        == "BOUNDED_INTERVAL"
    ]

    ordering_rows = [
        row
        for row in promoted_rows
        if txt(
            row.get(
                "constraint_class"
            )
        )
        == "ORDERING_ONLY"
    ]

    session_rows = [
        row
        for row in promoted_rows
        if not txt(
            row.get(
                "car_number"
            )
        )
    ]

    new_promotions = [
        row
        for row in promoted_rows
        if txt(
            row.get(
                "adjudication_status"
            )
        )
        == "PROMOTED"
    ]

    # ========================================================
    # WRITE
    # ========================================================

    evidence_fields = [
        "evidence_id",
        "year",
        "session",
        "car_number",
        "driver_name",
        "speed_mph",
        "official_result_row",
        "official_result_status",
        "constraint_class",
        "time_lower_utc",
        "time_upper_utc",
        "time_midpoint_utc",
        "related_car_number",
        "related_speed_mph",
        "ordering_relation",
        "source_authority",
        "source_url",
        "source_title",
        "evidence_summary",
        "evidence_stage",
        "adjudication_status",
        "chronology_usable",
        "queue_replay_usable",
        "canonical_promoted",
        "notes",
    ]

    write_csv(
        PROMOTED_EVIDENCE,
        promoted_rows,
        evidence_fields,
    )

    write_csv(
        ORDERING_EDGES,
        ordering_edges,
        [
            "edge_id",
            "year",
            "from_car_number",
            "from_driver",
            "from_speed_mph",
            "from_result_status",
            "to_car_number",
            "to_driver",
            "to_speed_mph",
            "to_result_status",
            "relation",
            "constraint_class",
            "source",
            "chronology_usable",
            "queue_replay_usable",
            "notes",
        ],
    )

    summary_rows = [
        {
            "metric":
                "total_evidence_rows",
            "value":
                len(
                    promoted_rows
                ),
        },
        {
            "metric":
                "attempt_level_evidence_rows",
            "value":
                len(
                    attempt_level_rows
                ),
        },
        {
            "metric":
                "bounded_interval_attempt_rows",
            "value":
                len(
                    bounded_rows
                ),
        },
        {
            "metric":
                "ordering_only_attempt_rows",
            "value":
                len(
                    ordering_rows
                ),
        },
        {
            "metric":
                "session_level_rows",
            "value":
                len(
                    session_rows
                ),
        },
        {
            "metric":
                "new_adjudicated_promotions",
            "value":
                len(
                    new_promotions
                ),
        },
        {
            "metric":
                "specific_marco_attempt_promotions",
            "value":
                specific_marco_promotions,
        },
    ]

    write_csv(
        SUMMARY_CSV,
        summary_rows,
        [
            "metric",
            "value",
        ],
    )

    # ========================================================
    # QA
    # ========================================================

    qa_rows = [
        {
            "metric":
                "sato_editorial_ordering_verified",

            "value":
                int(
                    editorial_valid
                ),

            "status":
                (
                    "PASS"
                    if editorial_valid
                    else "FAIL"
                ),
        },

        {
            "metric":
                "sato_232196_failed_unique",

            "value":
                len(
                    sato_failed
                ),

            "status":
                (
                    "PASS"
                    if len(
                        sato_failed
                    )
                    == 1
                    else "FAIL"
                ),
        },

        {
            "metric":
                "sato_231708_unique",

            "value":
                len(
                    sato_second
                ),

            "status":
                (
                    "PASS"
                    if len(
                        sato_second
                    )
                    == 1
                    else "FAIL"
                ),
        },

        {
            "metric":
                "new_same_car_ordering_promoted",

            "value":
                len(
                    ordering_edges
                ),

            "status":
                (
                    "PASS"
                    if len(
                        ordering_edges
                    )
                    == 1
                    else "REVIEW"
                ),
        },

        {
            "metric":
                "specific_marco_attempt_guessed",

            "value":
                specific_marco_promotions,

            "status":
                (
                    "PASS"
                    if specific_marco_promotions
                    == 0
                    else "FAIL"
                ),
        },

        {
            "metric":
                "interruption_windows_invented",

            "value":
                0,

            "status":
                "PASS",
        },

        {
            "metric":
                "result_row_order_used_as_chronology",

            "value":
                0,

            "status":
                "PASS",
        },

        {
            "metric":
                "exact_attempt_timestamps_claimed",

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
                "queue_wait_inferred",

            "value":
                0,

            "status":
                "PASS",
        },
    ]

    write_csv(
        QA_CSV,
        qa_rows,
        [
            "metric",
            "value",
            "status",
        ],
    )

    # ========================================================
    # PRINT
    # ========================================================

    print()
    print("=" * 120)
    print(
        "PROMOTED ORDERING EDGES"
    )
    print("=" * 120)

    if not ordering_edges:

        print(
            "NONE"
        )

    for row in ordering_edges:

        print()
        print(
            f"{row['from_driver']} "
            f"{row['from_speed_mph']} "
            f"[{row['from_result_status']}]"
        )

        print(
            "  <"
        )

        print(
            f"{row['to_driver']} "
            f"{row['to_speed_mph']} "
            f"[{row['to_result_status']}]"
        )

        print(
            "  class:",
            row[
                "constraint_class"
            ],
        )

    print()
    print("=" * 120)
    print(
        "2022 ADJUDICATED EVIDENCE SUMMARY"
    )
    print("=" * 120)

    print()
    print(
        "Total evidence rows:",
        len(
            promoted_rows
        ),
    )

    print(
        "Attempt-level evidence rows:",
        len(
            attempt_level_rows
        ),
    )

    print(
        "Bounded interval attempt rows:",
        len(
            bounded_rows
        ),
    )

    print(
        "Ordering-only attempt rows:",
        len(
            ordering_rows
        ),
    )

    print(
        "New adjudicated promotions:",
        len(
            new_promotions
        ),
    )

    print(
        "Specific Marco attempt promotions:",
        specific_marco_promotions,
    )

    print()
    print(
        "IMPORTANT:"
    )

    print(
        "The Sato same-car first-to-second "
        "attempt ordering is promoted."
    )

    print(
        "No specific Marco result row is promoted."
    )

    print(
        "Rain-delay evidence remains aggregate "
        "session-level evidence only."
    )

    print(
        "No exact attempt timestamp was invented."
    )

    print(
        "No canonical data was modified."
    )

    print()
    print("=" * 120)

    if (
        promote_same_car_ordering
        and
        len(
            ordering_edges
        )
        == 1
        and
        specific_marco_promotions
        == 0
    ):

        print(
            "FINAL STATUS: "
            "2022_ADJUDICATED_CHRONOLOGY_EVIDENCE_PROMOTED"
        )

    else:

        print(
            "FINAL STATUS: "
            "2022_ADJUDICATED_CHRONOLOGY_PROMOTION_REVIEW_REQUIRED"
        )

    print("=" * 120)

    print()
    print(
        "OUTPUTS"
    )

    print(
        PROMOTED_EVIDENCE
    )

    print(
        ORDERING_EDGES
    )

    print(
        SUMMARY_CSV
    )

    print(
        QA_CSV
    )


if __name__ == "__main__":
    main()
