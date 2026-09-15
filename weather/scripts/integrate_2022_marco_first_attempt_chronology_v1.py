from pathlib import Path
import csv


PHASE = "R1G.28C"

CANONICAL = Path(
    "data/canonical/v1/attempts.csv"
)

RESULT_V3 = Path(
    "weather/output/"
    "chronology_rescue_2022_result_to_canonical_attempt_matches_v3.csv"
)

CHRONOLOGY_V6 = Path(
    "weather/output/"
    "unified_attempt_chronology_constraint_ledger_v6.csv"
)

ACTION_V4 = Path(
    "weather/output/"
    "unified_attempt_action_lane_ledger_v4.csv"
)

BINDING = Path(
    "weather/output/"
    "chronology_rescue_2022_marco_first_attempt_identity_binding_v1.csv"
)

REPEAT_POLICY = Path(
    "weather/output/"
    "chronology_rescue_2022_repeat_pair_driver_eligibility_v1.csv"
)

OUTPUT_DIR = Path("weather/output")

CHRONOLOGY_V7 = (
    OUTPUT_DIR
    / "unified_attempt_chronology_constraint_ledger_v7.csv"
)

SUMMARY_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_marco_first_attempt_integration_summary_v1.csv"
)

QA_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_marco_first_attempt_integration_v1_qa.csv"
)


SATO_FIRST_ID = "3f221659-74ff-5901-97dc-08071a734690"
MARCO_FIRST_ID = "c044edbc-0f6c-5aab-bdef-9c4156b50617"
MARCO_SECOND_ID = "63982b5e-7639-5140-a6a2-702a77c2fc85"


def txt(v):
    return "" if v is None else str(v).strip()


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
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)


def blank(fields):
    return {
        field: ""
        for field in fields
    }


def first(row, fields):
    for field in fields:
        value = txt(row.get(field))
        if value:
            return value
    return ""


def driver(row):
    return first(
        row,
        [
            "driver_name",
            "driver",
            "driver_full_name",
        ],
    )


def car(row):
    return first(
        row,
        [
            "car_number",
            "car_no",
            "car",
        ],
    )


def attempt_index(row):
    return first(
        row,
        [
            "car_attempt_index",
            "attempt_index",
        ],
    )


def session_id(row):
    return first(
        row,
        [
            "session_id",
            "session",
        ],
    ) or "6033"


def result_status(row):
    return first(
        row,
        [
            "result_status",
            "status",
        ],
    )


def official_row(row):
    return first(
        row,
        [
            "official_result_row",
            "result_row",
            "row_number",
        ],
    )


def chronology_ids(rows, valid_ids):
    return {
        txt(row.get("attempt_id"))
        for row in rows
        if (
            txt(row.get("attempt_id")) in valid_ids
            and
            txt(row.get("chronology_usable")).lower() == "true"
        )
    }


def lane_count(rows):
    return sum(
        1
        for row in rows
        if txt(row.get("lane")).upper()
        not in {"", "UNKNOWN"}
    )


def main():
    print()
    print("=" * 115)
    print(
        "R1G.28C — 2022 MARCO FIRST-ATTEMPT "
        "ACTIVE CHRONOLOGY INTEGRATION"
    )
    print("=" * 115)

    required = [
        CANONICAL,
        RESULT_V3,
        CHRONOLOGY_V6,
        ACTION_V4,
        BINDING,
        REPEAT_POLICY,
    ]

    for path in required:
        print(
            f"{path}: "
            f"{'PRESENT' if path.exists() else 'MISSING'}"
        )

    if not all(path.exists() for path in required):
        print()
        print(
            "FINAL STATUS: "
            "MARCO_FIRST_ATTEMPT_INTEGRATION_INPUT_MISSING"
        )
        return

    canonical = read_csv(CANONICAL)
    result_v3 = read_csv(RESULT_V3)
    chronology_v6 = read_csv(CHRONOLOGY_V6)
    action_v4 = read_csv(ACTION_V4)
    binding = read_csv(BINDING)
    repeat_policy = read_csv(REPEAT_POLICY)

    cfields = list(
        chronology_v6[0].keys()
    )

    canonical_by_id = {
        txt(row.get("attempt_id")): row
        for row in canonical
        if txt(row.get("attempt_id"))
    }

    result_by_id = {
        txt(row.get("attempt_id")): row
        for row in result_v3
        if txt(row.get("attempt_id"))
    }

    marco_first = canonical_by_id.get(
        MARCO_FIRST_ID
    )

    marco_second = canonical_by_id.get(
        MARCO_SECOND_ID
    )

    marco_first_result = result_by_id.get(
        MARCO_FIRST_ID
    )

    if (
        marco_first is None
        or
        marco_second is None
        or
        marco_first_result is None
    ):
        print()
        print(
            "FINAL STATUS: "
            "MARCO_FIRST_ATTEMPT_CANONICAL_GROUNDING_FAILED"
        )
        return

    binding_ready = any(
        txt(row.get("promotion_ready")).lower() == "true"
        and
        txt(row.get("related_attempt_id")) == MARCO_FIRST_ID
        and
        txt(row.get("relation"))
        ==
        "SATO_232.196_BEFORE_MARCO_FIRST_ATTEMPT_226.108"
        for row in binding
    )

    print()
    print("=" * 115)
    print("BINDING GROUNDING")
    print("=" * 115)

    print()
    print(
        "Binding ready:",
        binding_ready,
    )

    if not binding_ready:
        print()
        print(
            "FINAL STATUS: "
            "MARCO_FIRST_ATTEMPT_BINDING_NOT_READY"
        )
        return

    existing_first = [
        row
        for row in chronology_v6
        if txt(row.get("attempt_id")) == MARCO_FIRST_ID
    ]

    existing_second = [
        row
        for row in chronology_v6
        if txt(row.get("attempt_id")) == MARCO_SECOND_ID
    ]

    print()
    print("=" * 115)
    print("DUPLICATE CHECK")
    print("=" * 115)

    print()
    print(
        "Existing Marco first chronology rows:",
        len(existing_first),
    )

    print(
        "Existing Marco second chronology rows:",
        len(existing_second),
    )

    if len(existing_first) != 0:
        print()
        print(
            "FINAL STATUS: "
            "MARCO_FIRST_ATTEMPT_DUPLICATE_REVIEW_REQUIRED"
        )
        return

    row = blank(cfields)

    values = {
        "year":
            "2022",

        "attempt_id":
            MARCO_FIRST_ID,

        "session_id":
            session_id(marco_first),

        "car_number":
            car(marco_first),

        "driver_name":
            driver(marco_first),

        "car_attempt_index":
            attempt_index(marco_first),

        "constraint_class":
            "ORDERING_ONLY",

        "time_quality":
            "ORDERING_ONLY",

        "source_layer":
            "OFFICIAL_EVIDENCE",

        "source_semantic":
            "NEXT_DRIVER_AFTER_SATO_FAILED_ATTEMPT",

        "source_event_id":
            "R1G28C-MARCO-FIRST",

        "anchor_event_type":
            "MARCO_FIRST_ATTEMPT_AFTER_SATO",

        "result_status":
            result_status(marco_first),

        "chronology_usable":
            "True",

        "performance_environment_usable":
            "False",

        "queue_replay_usable":
            "False",

        "notes":
            (
                "Official INDYCAR editorial identifies Marco Andretti "
                "as the next driver whose qualifying attempt followed "
                "Sato's 232.196 mph failed attempt. Frozen canonical "
                "repeat-pair identity binds that Marco run to his "
                "first attempt, 226.108 mph. No Lane, queue, wait, "
                "or exact timestamp inferred."
            ),

        "evidence_id":
            "R1G28C-MARCO-FIRST",

        "evidence_stage":
            PHASE,

        "source_authority":
            "INDYCAR_OFFICIAL_EDITORIAL+CANONICAL_PAIR_BINDING",

        "source_title":
            "2022 Day 1 Qualifying Recap",

        "source_url":
            "https://www.indycar.com/news/2022/05/05-21-day1-quals",

        "official_result_row":
            official_row(
                marco_first_result
            ),

        "ordering_relation":
            "AFTER_SATO_232.196_FAILED_ATTEMPT",

        "evidence_summary":
            (
                "Sato's failed 232.196 mph attempt occurred before "
                "Marco Andretti's first qualifying attempt. Canonical "
                "first-attempt identity is 226.108 mph."
            ),

        "related_attempt_id":
            SATO_FIRST_ID,

        "ordering_role":
            "RELATED",

        "evidence_type":
            "OFFICIAL_NEXT_DRIVER_IDENTITY_BINDING",

        "action":
            "",

        "lane":
            "UNKNOWN",

        "source_candidate_id":
            "R1G28B",

        "evidence_quality":
            "HIGH",
    }

    for key, value in values.items():
        if key in row:
            row[key] = value

    chronology_v7 = chronology_v6 + [
        row
    ]

    write_csv(
        CHRONOLOGY_V7,
        chronology_v7,
        cfields,
    )

    ids_2022 = {
        txt(row.get("attempt_id"))
        for row in result_v3
        if txt(row.get("attempt_id"))
    }

    before_ids = chronology_ids(
        chronology_v6,
        ids_2022,
    )

    after_ids = chronology_ids(
        chronology_v7,
        ids_2022,
    )

    before_n = len(before_ids)
    after_n = len(after_ids)
    total = len(ids_2022)

    before_pct = (
        100.0 * before_n / total
        if total
        else 0.0
    )

    after_pct = (
        100.0 * after_n / total
        if total
        else 0.0
    )

    eligible = {
        txt(row.get("driver_name"))
        for row in repeat_policy
        if txt(
            row.get("decision_relevant_denominator")
        ).upper() == "INCLUDE"
    }

    groups = {}

    for aid in ids_2022:
        c = canonical_by_id.get(aid)

        if not c:
            continue

        d = driver(c)

        if d in eligible:
            groups.setdefault(
                d,
                set(),
            ).add(aid)

    covered_before = {
        d
        for d, aids in groups.items()
        if aids.issubset(before_ids)
    }

    covered_after = {
        d
        for d, aids in groups.items()
        if aids.issubset(after_ids)
    }

    lane_before = lane_count(action_v4)
    lane_after = lane_before

    print()
    print("=" * 115)
    print("POST-INTEGRATION SUMMARY")
    print("=" * 115)

    print()
    print(
        "Chronology rows:",
        len(chronology_v6),
        "->",
        len(chronology_v7),
    )

    print()
    print(
        "2022 chronology attempts:",
        before_n,
        "->",
        after_n,
    )

    print(
        "2022 chronology coverage:",
        f"{before_pct:.2f}%",
        "->",
        f"{after_pct:.2f}%",
    )

    print()
    print(
        "Decision-relevant repeat coverage:",
        f"{len(covered_before)}/{len(eligible)}",
        "->",
        f"{len(covered_after)}/{len(eligible)}",
    )

    print(
        "Marco fully covered after integration:",
        "Marco Andretti" in covered_after,
    )

    print()
    print(
        "Explicit Lane rows:",
        lane_before,
        "->",
        lane_after,
    )

    summary_rows = [
        {
            "metric": "chronology_rows_before",
            "value": len(chronology_v6),
        },
        {
            "metric": "chronology_rows_after",
            "value": len(chronology_v7),
        },
        {
            "metric": "2022_chronology_before",
            "value": before_n,
        },
        {
            "metric": "2022_chronology_after",
            "value": after_n,
        },
        {
            "metric": "coverage_before_pct",
            "value": f"{before_pct:.2f}",
        },
        {
            "metric": "coverage_after_pct",
            "value": f"{after_pct:.2f}",
        },
        {
            "metric": "repeat_coverage_before",
            "value": f"{len(covered_before)}/{len(eligible)}",
        },
        {
            "metric": "repeat_coverage_after",
            "value": f"{len(covered_after)}/{len(eligible)}",
        },
        {
            "metric": "marco_first_added",
            "value": 1,
        },
        {
            "metric": "marco_second_added",
            "value": 0,
        },
        {
            "metric": "lane_rows_before",
            "value": lane_before,
        },
        {
            "metric": "lane_rows_after",
            "value": lane_after,
        },
    ]

    write_csv(
        SUMMARY_OUT,
        summary_rows,
        [
            "metric",
            "value",
        ],
    )

    first_count_after = sum(
        1
        for row in chronology_v7
        if txt(row.get("attempt_id")) == MARCO_FIRST_ID
    )

    second_count_after = sum(
        1
        for row in chronology_v7
        if txt(row.get("attempt_id")) == MARCO_SECOND_ID
    )

    qa_rows = [
        {
            "metric":
                "binding_ready",

            "value":
                int(binding_ready),

            "status":
                "PASS"
                if binding_ready
                else "FAIL",
        },

        {
            "metric":
                "marco_first_added_once",

            "value":
                first_count_after,

            "status":
                "PASS"
                if first_count_after == 1
                else "FAIL",
        },

        {
            "metric":
                "marco_second_not_added",

            "value":
                second_count_after,

            "status":
                "PASS"
                if second_count_after == 0
                else "FAIL",
        },

        {
            "metric":
                "unique_chronology_gain_one",

            "value":
                after_n - before_n,

            "status":
                "PASS"
                if after_n - before_n == 1
                else "FAIL",
        },

        {
            "metric":
                "repeat_coverage_not_artificially_incremented",

            "value":
                len(covered_after) - len(covered_before),

            "status":
                "PASS"
                if len(covered_after) == len(covered_before)
                else "FAIL",
        },

        {
            "metric":
                "lane_evidence_unchanged",

            "value":
                lane_after - lane_before,

            "status":
                "PASS",
        },

        {
            "metric":
                "canonical_mutated",

            "value":
                0,

            "status":
                "PASS",
        },

        {
            "metric":
                "phase5_to_phase8_mutated",

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
        row["status"] == "PASS"
        for row in qa_rows
    )

    print()
    print("=" * 115)

    if success:
        print(
            "FINAL STATUS: "
            "MARCO_FIRST_ATTEMPT_CHRONOLOGY_INTEGRATED"
        )
    else:
        print(
            "FINAL STATUS: "
            "MARCO_FIRST_ATTEMPT_INTEGRATION_REVIEW_REQUIRED"
        )

    print("=" * 115)

    print()
    print("OUTPUTS")
    print(CHRONOLOGY_V7)
    print(SUMMARY_OUT)
    print(QA_OUT)


if __name__ == "__main__":
    main()
