from pathlib import Path
import csv


PHASE = "R1G.30B"

CANONICAL = Path("data/canonical/v1/attempts.csv")

RESULT_V3 = Path(
    "weather/output/"
    "chronology_rescue_2022_result_to_canonical_attempt_matches_v3.csv"
)

CHRONOLOGY_V9 = Path(
    "weather/output/"
    "unified_attempt_chronology_constraint_ledger_v9.csv"
)

ACTION_V6 = Path(
    "weather/output/"
    "unified_attempt_action_lane_ledger_v6.csv"
)

AUDIT_30A = Path(
    "weather/output/"
    "chronology_rescue_2022_karam_repeat_object_reconciliation_v1.csv"
)

OUTPUT_DIR = Path("weather/output")

EVIDENCE_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_karam_repeat_conflict_evidence_v1.csv"
)

ADJUDICATION_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_karam_repeat_conflict_adjudication_v1.csv"
)

QA_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_karam_repeat_conflict_evidence_v1_qa.csv"
)


FIRST_ID = "8e0c8731-4ddc-515a-949e-7902dd01eaeb"
SECOND_ID = "2c453335-3a19-5653-8d5c-79d94db93028"
NO_ATTEMPT_ID = "4778bf12-3fb5-5321-b4ae-9dc2f0880c25"

FIRST_SPEED = "229.905"
SECOND_SPEED = "230.464"

AUTOSPORT_URL = (
    "https://www.autosport.com/indycar/news/"
    "indy-500-sato-grosjean-johnson-into-top-12-fight-"
    "p13-33-set/10308540/"
)

THERACE_URL = (
    "https://www.the-race.com/indycar/"
    "everything-that-happened-in-tense-first-indy-500-qualifying/"
)

# Deliberately short source-native quotations.
AUTOSPORT_WARMUP_QUOTE = (
    "Karam was on his warm-up lap when the rain moved in"
)

AUTOSPORT_IMPROVEMENT_QUOTE = (
    "Karam improved his average speed by 0.5mph"
)

THERACE_CONFLICT_QUOTE = (
    "Sage Karam was unable to improve"
)


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
    path.parent.mkdir(parents=True, exist_ok=True)

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


def attempt_index(row):
    return first(
        row,
        [
            "car_attempt_index",
            "attempt_index",
        ],
    )


def speed(row):
    return first(
        row,
        [
            "four_lap_average_speed_mph",
            "average_speed_mph",
            "speed_mph",
        ],
    )


def official_status(row):
    return first(
        row,
        [
            "official_status",
            "status",
        ],
    )


def official_result_row(row):
    return first(
        row,
        [
            "official_result_row",
            "result_row",
            "row_number",
        ],
    )


def main():

    print()
    print("=" * 120)
    print(
        "R1G.30B — 2022 SAGE KARAM "
        "REPEAT / IMPROVEMENT CONFLICT ADJUDICATION"
    )
    print("=" * 120)

    required = [
        CANONICAL,
        RESULT_V3,
        CHRONOLOGY_V9,
        ACTION_V6,
        AUDIT_30A,
    ]

    print()
    print("INPUT CHECK")
    print("-" * 120)

    for path in required:
        print(
            f"{path}: "
            f"{'PRESENT' if path.exists() else 'MISSING'}"
        )

    if not all(path.exists() for path in required):
        print()
        print(
            "FINAL STATUS: "
            "KARAM_REPEAT_CONFLICT_CAPTURE_INPUT_MISSING"
        )
        return

    canonical = read_csv(CANONICAL)
    result_v3 = read_csv(RESULT_V3)
    chronology = read_csv(CHRONOLOGY_V9)
    action = read_csv(ACTION_V6)

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

    first_row = canonical_by_id.get(FIRST_ID)
    second_row = canonical_by_id.get(SECOND_ID)
    no_attempt_row = canonical_by_id.get(NO_ATTEMPT_ID)

    first_result = result_by_id.get(FIRST_ID)
    second_result = result_by_id.get(SECOND_ID)
    no_attempt_result = result_by_id.get(NO_ATTEMPT_ID)

    if any(
        item is None
        for item in [
            first_row,
            second_row,
            no_attempt_row,
            first_result,
            second_result,
            no_attempt_result,
        ]
    ):
        print()
        print(
            "FINAL STATUS: "
            "KARAM_REPEAT_CONFLICT_CANONICAL_GROUNDING_FAILED"
        )
        return

    first_ok = all([
        driver(first_row) == "Sage Karam",
        attempt_index(first_row) == "1",
        speed(first_row) == FIRST_SPEED,
        official_status(first_result) == "Withdrawn",
    ])

    second_ok = all([
        driver(second_row) == "Sage Karam",
        attempt_index(second_row) == "2",
        speed(second_row) == SECOND_SPEED,
        official_result_row(second_result) == "22",
    ])

    no_attempt_ok = all([
        driver(no_attempt_row) == "Sage Karam",
        official_status(no_attempt_result) == "No Attempt",
    ])

    first_in_v9 = any(
        txt(row.get("attempt_id")) == FIRST_ID
        and
        txt(row.get("chronology_usable")).lower() == "true"
        for row in chronology
    )

    second_in_v9 = any(
        txt(row.get("attempt_id")) == SECOND_ID
        and
        txt(row.get("chronology_usable")).lower() == "true"
        for row in chronology
    )

    existing_action = [
        row
        for row in action
        if (
            txt(row.get("subject_attempt_id"))
            in {FIRST_ID, SECOND_ID, NO_ATTEMPT_ID}
            or
            txt(row.get("related_attempt_id"))
            in {FIRST_ID, SECOND_ID, NO_ATTEMPT_ID}
            or
            txt(row.get("driver_name")) == "Sage Karam"
        )
    ]

    delta = (
        float(SECOND_SPEED)
        -
        float(FIRST_SPEED)
    )

    autosport_rounding_ok = (
        round(delta, 1)
        ==
        0.6
        or
        abs(delta - 0.5) <= 0.1
    )

    objective_improvement = (
        delta > 0.0
    )

    print()
    print("=" * 120)
    print("CANONICAL / OFFICIAL GROUNDING")
    print("=" * 120)

    print()
    print(
        "First:",
        FIRST_ID,
        "| index",
        repr(attempt_index(first_row)),
        "| speed",
        repr(speed(first_row)),
        "| official status",
        repr(official_status(first_result)),
    )

    print(
        "Second:",
        SECOND_ID,
        "| index",
        repr(attempt_index(second_row)),
        "| speed",
        repr(speed(second_row)),
        "| official row",
        repr(official_result_row(second_result)),
    )

    print(
        "No Attempt:",
        NO_ATTEMPT_ID,
        "| official status",
        repr(official_status(no_attempt_result)),
    )

    print()
    print("First grounding:", first_ok)
    print("Second grounding:", second_ok)
    print("No Attempt grounding:", no_attempt_ok)

    print()
    print(
        "Objective speed delta:",
        f"{delta:+.3f}",
        "mph",
    )

    print(
        "Objective improvement:",
        objective_improvement,
    )

    print(
        "Autosport ~0.5 mph consistency:",
        autosport_rounding_ok,
    )

    print()
    print(
        "First already in V9:",
        first_in_v9,
    )

    print(
        "Second already in V9:",
        second_in_v9,
    )

    print(
        "Existing Karam action rows:",
        len(existing_action),
    )

    print()
    print("=" * 120)
    print("SOURCE EVIDENCE")
    print("=" * 120)

    print()
    print("SOURCE 1 — AUTOSPORT")
    print(
        "Warm-up/rain quote:",
        repr(AUTOSPORT_WARMUP_QUOTE),
    )

    print(
        "Improvement quote:",
        repr(AUTOSPORT_IMPROVEMENT_QUOTE),
    )

    print()
    print("SOURCE 2 — THE RACE")
    print(
        "Conflicting quote:",
        repr(THERACE_CONFLICT_QUOTE),
    )

    print()
    print("=" * 120)
    print("CONFLICT ADJUDICATION")
    print("=" * 120)

    autosport_supported = all([
        first_ok,
        second_ok,
        objective_improvement,
        autosport_rounding_ok,
    ])

    therace_conflicts_with_numeric_record = (
        objective_improvement
    )

    no_attempt_excluded = (
        NO_ATTEMPT_ID
        not in {
            FIRST_ID,
            SECOND_ID,
        }
        and
        no_attempt_ok
    )

    #
    # Promotion policy:
    #
    # Autosport provides:
    # - Karam on warm-up before rain interruption
    # - after restart, explicit +0.5 mph improvement
    #
    # Canonical/official data provide:
    # - 229.905 attempt 1, Withdrawn
    # - 230.464 attempt 2, final P22
    # - numerical gain +0.559 mph
    #
    # The Race's "unable to improve" conflicts with the
    # objective speed record and Autosport. Preserve the
    # conflict but do not use that sentence to erase the
    # source-native Autosport chronology.
    #

    promotion_ready = all([
        autosport_supported,
        therace_conflicts_with_numeric_record,
        no_attempt_excluded,
        not first_in_v9,
        not second_in_v9,
        len(existing_action) == 0,
    ])

    relation = (
        "KARAM_229.905_FIRST_ATTEMPT_BEFORE_230.464_POST_RESTART_IMPROVEMENT"
        if promotion_ready
        else
        "REVIEW_REQUIRED"
    )

    action_label = (
        "REPEAT_ATTEMPT_IMPROVED"
        if promotion_ready
        else
        "REVIEW_REQUIRED"
    )

    conflict_status = (
        "SECONDARY_SOURCE_CONFLICT_RESOLVED_BY_SPEED_BOUND_EVIDENCE"
        if promotion_ready
        else
        "UNRESOLVED"
    )

    print()
    print(
        "Autosport speed-bound evidence supported:",
        autosport_supported,
    )

    print(
        "The Race conflicts with objective speed record:",
        therace_conflicts_with_numeric_record,
    )

    print(
        "No Attempt excluded from decision pair:",
        no_attempt_excluded,
    )

    print(
        "Conflict status:",
        conflict_status,
    )

    print()
    print(
        "Promotion ready:",
        promotion_ready,
    )

    print(
        "Supported relation:",
        relation
        if promotion_ready
        else
        "NOT_YET",
    )

    print(
        "Supported action:",
        action_label
        if promotion_ready
        else
        "NOT_YET",
    )

    print()
    print("Lane: UNKNOWN")
    print("Queue position: UNKNOWN")
    print("Queue wait: UNKNOWN")
    print("Exact timestamp: UNKNOWN")

    evidence_rows = [
        {
            "evidence_id":
                "R1G30B-KARAM-AUTOSPORT",

            "phase":
                PHASE,

            "year":
                "2022",

            "driver_name":
                "Sage Karam",

            "first_attempt_id":
                FIRST_ID,

            "first_speed_mph":
                FIRST_SPEED,

            "second_attempt_id":
                SECOND_ID,

            "second_speed_mph":
                SECOND_SPEED,

            "no_attempt_object_id":
                NO_ATTEMPT_ID,

            "source_name":
                "Autosport",

            "source_class":
                "REPUTABLE_SECONDARY_EDITORIAL",

            "source_url":
                AUTOSPORT_URL,

            "source_quote_1":
                AUTOSPORT_WARMUP_QUOTE,

            "source_quote_2":
                AUTOSPORT_IMPROVEMENT_QUOTE,

            "semantic":
                "POST_RESTART_IMPROVEMENT",

            "evidence_direction":
                "SUPPORT",

            "speed_delta_mph":
                f"{delta:+.3f}",
        },

        {
            "evidence_id":
                "R1G30B-KARAM-THERACE-CONFLICT",

            "phase":
                PHASE,

            "year":
                "2022",

            "driver_name":
                "Sage Karam",

            "first_attempt_id":
                FIRST_ID,

            "first_speed_mph":
                FIRST_SPEED,

            "second_attempt_id":
                SECOND_ID,

            "second_speed_mph":
                SECOND_SPEED,

            "no_attempt_object_id":
                NO_ATTEMPT_ID,

            "source_name":
                "The Race",

            "source_class":
                "REPUTABLE_SECONDARY_EDITORIAL",

            "source_url":
                THERACE_URL,

            "source_quote_1":
                THERACE_CONFLICT_QUOTE,

            "source_quote_2":
                "",

            "semantic":
                "CONTRADICTORY_IMPROVEMENT_CLAIM",

            "evidence_direction":
                "CONFLICT",

            "speed_delta_mph":
                f"{delta:+.3f}",
        },
    ]

    write_csv(
        EVIDENCE_OUT,
        evidence_rows,
        [
            "evidence_id",
            "phase",
            "year",
            "driver_name",
            "first_attempt_id",
            "first_speed_mph",
            "second_attempt_id",
            "second_speed_mph",
            "no_attempt_object_id",
            "source_name",
            "source_class",
            "source_url",
            "source_quote_1",
            "source_quote_2",
            "semantic",
            "evidence_direction",
            "speed_delta_mph",
        ],
    )

    adjudication_rows = [
        {
            "phase":
                PHASE,

            "driver_name":
                "Sage Karam",

            "first_attempt_id":
                FIRST_ID,

            "first_speed_mph":
                FIRST_SPEED,

            "second_attempt_id":
                SECOND_ID,

            "second_speed_mph":
                SECOND_SPEED,

            "no_attempt_object_id":
                NO_ATTEMPT_ID,

            "objective_speed_delta_mph":
                f"{delta:+.3f}",

            "autosport_supported":
                str(autosport_supported),

            "therace_conflict_present":
                str(
                    therace_conflicts_with_numeric_record
                ),

            "conflict_status":
                conflict_status,

            "relation":
                relation,

            "action":
                action_label,

            "time_quality":
                (
                    "ORDERING_ONLY"
                    if promotion_ready
                    else
                    "UNKNOWN"
                ),

            "lane":
                "UNKNOWN",

            "queue_position":
                "UNKNOWN",

            "queue_wait":
                "UNKNOWN",

            "exact_timestamp":
                "UNKNOWN",

            "promotion_ready":
                str(promotion_ready),

            "notes":
                (
                    "Autosport explicitly reports Karam on his "
                    "warm-up lap when rain interrupted the session, "
                    "then a post-restart improvement of approximately "
                    "0.5 mph. Canonical/official speeds move from "
                    "229.905 to 230.464 mph (+0.559). The Race states "
                    "that Karam was unable to improve; this conflicting "
                    "secondary claim is preserved but is inconsistent "
                    "with the speed-bound official/canonical record. "
                    "No Attempt object remains outside the frozen "
                    "decision-relevant repeat pair."
                ),
        }
    ]

    write_csv(
        ADJUDICATION_OUT,
        adjudication_rows,
        [
            "phase",
            "driver_name",
            "first_attempt_id",
            "first_speed_mph",
            "second_attempt_id",
            "second_speed_mph",
            "no_attempt_object_id",
            "objective_speed_delta_mph",
            "autosport_supported",
            "therace_conflict_present",
            "conflict_status",
            "relation",
            "action",
            "time_quality",
            "lane",
            "queue_position",
            "queue_wait",
            "exact_timestamp",
            "promotion_ready",
            "notes",
        ],
    )

    qa_rows = [
        {
            "metric": "first_grounding",
            "value": int(first_ok),
            "status": "PASS" if first_ok else "FAIL",
        },
        {
            "metric": "second_grounding",
            "value": int(second_ok),
            "status": "PASS" if second_ok else "FAIL",
        },
        {
            "metric": "no_attempt_grounding",
            "value": int(no_attempt_ok),
            "status": "PASS" if no_attempt_ok else "FAIL",
        },
        {
            "metric": "positive_speed_delta",
            "value": f"{delta:+.3f}",
            "status": "PASS" if objective_improvement else "FAIL",
        },
        {
            "metric": "autosport_speed_consistency",
            "value": int(autosport_rounding_ok),
            "status": "PASS" if autosport_rounding_ok else "FAIL",
        },
        {
            "metric": "source_conflict_preserved",
            "value": 1,
            "status": "PASS",
        },
        {
            "metric": "no_attempt_excluded",
            "value": int(no_attempt_excluded),
            "status": "PASS" if no_attempt_excluded else "FAIL",
        },
        {
            "metric": "lane_inferred",
            "value": 0,
            "status": "PASS",
        },
        {
            "metric": "queue_wait_inferred",
            "value": 0,
            "status": "PASS",
        },
        {
            "metric": "ledger_mutation",
            "value": 0,
            "status": "PASS",
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

    print()
    print("=" * 120)

    if promotion_ready:
        print(
            "FINAL STATUS: "
            "KARAM_REPEAT_CONFLICT_ADJUDICATED_PROMOTION_READY"
        )
    else:
        print(
            "FINAL STATUS: "
            "KARAM_REPEAT_CONFLICT_REVIEW_REQUIRED"
        )

    print("=" * 120)

    print()
    print("OUTPUTS")
    print(EVIDENCE_OUT)
    print(ADJUDICATION_OUT)
    print(QA_OUT)


if __name__ == "__main__":
    main()
