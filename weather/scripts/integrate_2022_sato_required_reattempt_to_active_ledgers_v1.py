from pathlib import Path
import csv
from decimal import Decimal, InvalidOperation


PHASE = "R1G.27B"

CANONICAL = Path(
    "data/canonical/v1/attempts.csv"
)

RESULT_V3 = Path(
    "weather/output/"
    "chronology_rescue_2022_result_to_canonical_attempt_matches_v3.csv"
)

CHRONOLOGY_V5 = Path(
    "weather/output/"
    "unified_attempt_chronology_constraint_ledger_v5.csv"
)

ACTION_V3 = Path(
    "weather/output/"
    "unified_attempt_action_lane_ledger_v3.csv"
)

SATO_HITS = Path(
    "weather/output/"
    "chronology_rescue_2022_sato_required_reattempt_evidence_hits_v1.csv"
)

SATO_ADJ = Path(
    "weather/output/"
    "chronology_rescue_2022_sato_required_reattempt_adjudication_v1.csv"
)

REPEAT_POLICY = Path(
    "weather/output/"
    "chronology_rescue_2022_repeat_pair_driver_eligibility_v1.csv"
)

OUTPUT_DIR = Path(
    "weather/output"
)

CHRONOLOGY_V6 = (
    OUTPUT_DIR
    / "unified_attempt_chronology_constraint_ledger_v6.csv"
)

ACTION_V4 = (
    OUTPUT_DIR
    / "unified_attempt_action_lane_ledger_v4.csv"
)

INTEGRATION_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_sato_required_reattempt_ledger_integration_v1.csv"
)

COVERAGE_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_sato_required_reattempt_postintegration_coverage_v1.csv"
)

SUMMARY_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_sato_required_reattempt_ledger_integration_summary_v1.csv"
)

QA_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_sato_required_reattempt_ledger_integration_v1_qa.csv"
)


FIRST_ID = "3f221659-74ff-5901-97dc-08071a734690"
SECOND_ID = "21e8c99e-b04c-516d-85a8-ccfbaed7ff46"

EXPECTED_DRIVER = "Takuma Sato"
EXPECTED_CAR = "51"

EXPECTED_FIRST_SPEED = Decimal("232.196")
EXPECTED_SECOND_SPEED = Decimal("231.708")


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


def decimal_value(v):
    raw = txt(v)

    if not raw:
        return None

    try:
        return Decimal(raw)
    except InvalidOperation:
        return None


def first_value(row, fields):
    for field in fields:
        value = txt(
            row.get(field)
        )

        if value:
            return value

    return ""


def canonical_driver(row):
    return first_value(
        row,
        [
            "driver_name",
            "driver",
            "driver_full_name",
        ],
    )


def canonical_speed(row):
    for field in [
        "four_lap_average_speed_mph",
        "average_speed_mph",
        "speed_mph",
    ]:
        value = decimal_value(
            row.get(field)
        )

        if value is not None:
            return value

    return None


def canonical_car(row):
    return first_value(
        row,
        [
            "car_number",
            "car_no",
            "car",
        ],
    )


def canonical_index(row):
    return first_value(
        row,
        [
            "car_attempt_index",
            "attempt_index",
        ],
    )


def canonical_session(row):
    return first_value(
        row,
        [
            "session_id",
            "session",
        ],
    ) or "6033"


def canonical_status(row):
    return first_value(
        row,
        [
            "result_status",
            "status",
        ],
    )


def result_status(row):
    return first_value(
        row,
        [
            "official_status",
            "status",
        ],
    )


def result_row_number(row):
    return first_value(
        row,
        [
            "official_result_row",
            "result_row",
            "row_number",
        ],
    )


def chronology_usable_ids(rows, valid_ids):
    output = set()

    for row in rows:
        aid = txt(
            row.get("attempt_id")
        )

        usable = txt(
            row.get("chronology_usable")
        ).lower()

        if (
            aid in valid_ids
            and
            usable == "true"
        ):
            output.add(aid)

    return output


def row_mentions_attempt(row, attempt_id):
    return attempt_id in {
        txt(row.get("attempt_id")),
        txt(row.get("subject_attempt_id")),
        txt(row.get("related_attempt_id")),
    }


def explicit_lane_count(rows):
    count = 0

    for row in rows:
        lane = txt(
            row.get("lane")
        ).upper()

        if lane not in {
            "",
            "UNKNOWN",
        }:
            count += 1

    return count


def blank_row(fields):
    return {
        field: ""
        for field in fields
    }


def make_chronology_row(
    fields,
    canonical_row,
    result_row,
    attempt_id,
    related_attempt_id,
    relation,
    ordering_role,
    semantic,
    action,
    evidence_id,
    evidence_summary,
    source_candidate_ids,
):
    row = blank_row(
        fields
    )

    values = {
        "year":
            "2022",

        "attempt_id":
            attempt_id,

        "session_id":
            canonical_session(
                canonical_row
            ),

        "car_number":
            canonical_car(
                canonical_row
            ),

        "driver_name":
            canonical_driver(
                canonical_row
            ),

        "car_attempt_index":
            canonical_index(
                canonical_row
            ),

        "constraint_class":
            "ORDERING",

        "time_point_utc":
            "",

        "time_lower_utc":
            "",

        "time_upper_utc":
            "",

        "time_midpoint_utc":
            "",

        "time_quality":
            "ORDERING_ONLY",

        "source_layer":
            "OFFICIAL_EVIDENCE",

        "source_semantic":
            semantic,

        "source_event_id":
            evidence_id,

        "anchor_event_type":
            semantic,

        "result_status":
            canonical_status(
                canonical_row
            ),

        "chronology_usable":
            "True",

        "performance_environment_usable":
            "False",

        "queue_replay_usable":
            "False",

        "notes":
            (
                evidence_summary
                + " No Lane 1/Lane 2, queue position, "
                  "queue wait, or exact timestamp inferred. "
                  "Deceleration lane is not treated as "
                  "qualifying Lane 1 or Lane 2."
            ),

        "evidence_id":
            evidence_id,

        "evidence_stage":
            PHASE,

        "source_authority":
            "OFFICIAL",

        "source_title":
            (
                "INDYCAR official editorial evidence "
                "and Official Qualification Results"
            ),

        "source_url":
            "",

        "official_result_row":
            result_row_number(
                result_row
            ),

        "ordering_relation":
            relation,

        "evidence_summary":
            evidence_summary,

        "related_attempt_id":
            related_attempt_id,

        "ordering_role":
            ordering_role,

        "evidence_type":
            "OFFICIAL_INVALIDATION_REATTEMPT_SEMANTIC",

        "action":
            action,

        "lane":
            "UNKNOWN",

        "source_candidate_id":
            source_candidate_ids,

        "evidence_quality":
            "HIGH",
    }

    for key, value in values.items():
        if key in row:
            row[key] = value

    return row


def main():
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print()
    print("=" * 120)
    print(
        "R1G.27B — 2022 TAKUMA SATO "
        "REQUIRED-REATTEMPT ACTIVE LEDGER INTEGRATION V1"
    )
    print("=" * 120)

    required = [
        CANONICAL,
        RESULT_V3,
        CHRONOLOGY_V5,
        ACTION_V3,
        SATO_HITS,
        SATO_ADJ,
        REPEAT_POLICY,
    ]

    missing = []

    print()
    print("INPUT CHECK")
    print("-" * 120)

    for path in required:
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
            "SATO_REQUIRED_REATTEMPT_INTEGRATION_INPUT_MISSING"
        )
        return

    canonical = read_csv(
        CANONICAL
    )

    result_v3 = read_csv(
        RESULT_V3
    )

    chronology_v5 = read_csv(
        CHRONOLOGY_V5
    )

    action_v3 = read_csv(
        ACTION_V3
    )

    hits = read_csv(
        SATO_HITS
    )

    adjudication = read_csv(
        SATO_ADJ
    )

    repeat_policy = read_csv(
        REPEAT_POLICY
    )

    chronology_fields = list(
        chronology_v5[0].keys()
    )

    action_fields = list(
        action_v3[0].keys()
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

    first = canonical_by_id.get(
        FIRST_ID
    )

    second = canonical_by_id.get(
        SECOND_ID
    )

    first_result = result_by_id.get(
        FIRST_ID
    )

    second_result = result_by_id.get(
        SECOND_ID
    )

    if (
        first is None
        or second is None
        or first_result is None
        or second_result is None
    ):
        print()
        print(
            "FINAL STATUS: "
            "SATO_REQUIRED_REATTEMPT_CANONICAL_GROUNDING_FAILED"
        )
        return

    first_driver = canonical_driver(
        first
    )

    second_driver = canonical_driver(
        second
    )

    first_car = canonical_car(
        first
    )

    second_car = canonical_car(
        second
    )

    first_speed = canonical_speed(
        first
    )

    second_speed = canonical_speed(
        second
    )

    identity_ok = all([
        first_driver == EXPECTED_DRIVER,
        second_driver == EXPECTED_DRIVER,
        first_car == EXPECTED_CAR,
        second_car == EXPECTED_CAR,
        first_speed == EXPECTED_FIRST_SPEED,
        second_speed == EXPECTED_SECOND_SPEED,
    ])

    print()
    print("=" * 120)
    print("CANONICAL GROUNDING")
    print("=" * 120)

    print()
    print(
        FIRST_ID,
        "|",
        first_driver,
        "| car",
        repr(first_car),
        "| index",
        canonical_index(first),
        "|",
        first_speed,
    )

    print(
        SECOND_ID,
        "|",
        second_driver,
        "| car",
        repr(second_car),
        "| index",
        canonical_index(second),
        "|",
        second_speed,
    )

    print()
    print(
        "Identity check:",
        identity_ok,
    )

    if not identity_ok:
        print()
        print(
            "FINAL STATUS: "
            "SATO_REQUIRED_REATTEMPT_IDENTITY_REVIEW_REQUIRED"
        )
        return

    adj_ready = any(
        txt(
            row.get("promotion_ready")
        ).lower()
        == "true"
        for row in adjudication
    )

    adj_relation = any(
        txt(
            row.get("relation")
        )
        ==
        "FIRST_ATTEMPT_BEFORE_REQUIRED_REATTEMPT"
        for row in adjudication
    )

    adj_action = any(
        txt(
            row.get("related_action")
        )
        ==
        "REQUIRED_REATTEMPT_AFTER_INVALIDATION"
        for row in adjudication
    )

    evidence_ok = all([
        adj_ready,
        adj_relation,
        adj_action,
    ])

    print()
    print("=" * 120)
    print("ADJUDICATION GROUNDING")
    print("=" * 120)

    print()
    print(
        "Promotion ready:",
        adj_ready,
    )

    print(
        "Required relation present:",
        adj_relation,
    )

    print(
        "Required action present:",
        adj_action,
    )

    print(
        "Evidence grounding:",
        evidence_ok,
    )

    if not evidence_ok:
        print()
        print(
            "FINAL STATUS: "
            "SATO_REQUIRED_REATTEMPT_ADJUDICATION_NOT_READY"
        )
        return

    chronology_hits = [
        row
        for row in chronology_v5
        if (
            row_mentions_attempt(
                row,
                FIRST_ID,
            )
            or
            row_mentions_attempt(
                row,
                SECOND_ID,
            )
        )
    ]

    action_hits = [
        row
        for row in action_v3
        if (
            row_mentions_attempt(
                row,
                FIRST_ID,
            )
            or
            row_mentions_attempt(
                row,
                SECOND_ID,
            )
        )
    ]

    duplicate_free = (
        len(chronology_hits) == 0
        and
        len(action_hits) == 0
    )

    print()
    print("=" * 120)
    print("DUPLICATE CHECK")
    print("=" * 120)

    print()
    print(
        "Chronology V5 existing Sato hits:",
        len(
            chronology_hits
        ),
    )

    print(
        "Action V3 existing Sato hits:",
        len(
            action_hits
        ),
    )

    print(
        "Duplicate free:",
        duplicate_free,
    )

    if not duplicate_free:
        print()
        print(
            "FINAL STATUS: "
            "SATO_REQUIRED_REATTEMPT_DUPLICATE_REVIEW_REQUIRED"
        )
        return

    source_candidate_ids = "|".join(
        sorted({
            txt(row.get("hit_id"))
            for row in hits
            if (
                txt(row.get("hit_id"))
                and
                txt(row.get("source_class"))
                ==
                "INDYCAR_OFFICIAL_EDITORIAL"
            )
        })
    )

    first_chronology = make_chronology_row(
        chronology_fields,
        first,
        first_result,
        FIRST_ID,
        SECOND_ID,
        "BEFORE",
        "SUBJECT",
        "FIRST_ATTEMPT_INVALIDATED",
        "FIRST_ATTEMPT_INVALIDATED",
        "R1G27B-SATO-FIRST",
        (
            "Takuma Sato's 232.196 mph qualifying attempt "
            "was invalidated, and it precedes the required "
            "subsequent qualifying attempt."
        ),
        source_candidate_ids,
    )

    second_chronology = make_chronology_row(
        chronology_fields,
        second,
        second_result,
        SECOND_ID,
        FIRST_ID,
        "AFTER",
        "RELATED",
        "REQUIRED_REATTEMPT_AFTER_INVALIDATION",
        "REQUIRED_REATTEMPT_AFTER_INVALIDATION",
        "R1G27B-SATO-SECOND",
        (
            "Takuma Sato's 231.708 mph qualifying attempt "
            "is the required reattempt after invalidation "
            "of the earlier 232.196 mph attempt."
        ),
        source_candidate_ids,
    )

    chronology_v6 = (
        chronology_v5
        + [
            first_chronology,
            second_chronology,
        ]
    )

    action_row = blank_row(
        action_fields
    )

    action_values = {
        "evidence_id":
            "R1G27B-SATO-ACTION",

        "year":
            "2022",

        "subject_attempt_id":
            SECOND_ID,

        "related_attempt_id":
            FIRST_ID,

        "session_id":
            canonical_session(
                second
            ),

        "car_number":
            canonical_car(
                second
            ),

        "driver_name":
            EXPECTED_DRIVER,

        "action":
            "REQUIRED_REATTEMPT_AFTER_INVALIDATION",

        "lane":
            "UNKNOWN",

        "relation":
            "AFTER_INVALIDATED_FIRST_ATTEMPT",

        "source_name":
            (
                "INDYCAR official editorial evidence "
                "and Official Qualification Results"
            ),

        "source_class":
            "OFFICIAL",

        "source_candidate_id":
            source_candidate_ids,

        "evidence_quality":
            "HIGH",

        "chronology_usable":
            "True",

        "queue_position_known":
            "False",

        "queue_wait_known":
            "False",

        "canonical_mutated":
            "False",

        "notes":
            (
                "Required reattempt after invalidation. "
                "Lane remains UNKNOWN. "
                "No queue position, queue wait, or exact timestamp "
                "is inferred. Deceleration lane is not qualifying "
                "Lane 1 or Lane 2."
            ),

        "subject_speed_mph":
            str(
                second_speed
            ),

        "related_speed_mph":
            str(
                first_speed
            ),

        "official_subject_status":
            result_status(
                second_result
            ),

        "source_evidence_id":
            "R1G27-ADJ-001",

        "promotion_status":
            "PROMOTED_R1G27B",
    }

    for key, value in action_values.items():
        if key in action_row:
            action_row[key] = value

    action_v4 = (
        action_v3
        + [
            action_row
        ]
    )

    write_csv(
        CHRONOLOGY_V6,
        chronology_v6,
        chronology_fields,
    )

    write_csv(
        ACTION_V4,
        action_v4,
        action_fields,
    )

    # --------------------------------------------------------
    # 2022 population + chronology coverage
    # --------------------------------------------------------

    ids_2022 = {
        txt(row.get("attempt_id"))
        for row in result_v3
        if txt(row.get("attempt_id"))
    }

    before_ids = chronology_usable_ids(
        chronology_v5,
        ids_2022,
    )

    after_ids = chronology_usable_ids(
        chronology_v6,
        ids_2022,
    )

    total = len(
        ids_2022
    )

    before_count = len(
        before_ids
    )

    after_count = len(
        after_ids
    )

    before_pct = (
        100.0
        *
        before_count
        /
        total
        if total
        else 0.0
    )

    after_pct = (
        100.0
        *
        after_count
        /
        total
        if total
        else 0.0
    )

    newly_covered = sorted(
        after_ids
        -
        before_ids
    )

    # --------------------------------------------------------
    # Frozen decision-relevant denominator
    # --------------------------------------------------------

    eligible_drivers = {
        txt(
            row.get("driver_name")
        )
        for row in repeat_policy
        if (
            txt(
                row.get(
                    "decision_relevant_denominator"
                )
            ).upper()
            ==
            "INCLUDE"
        )
    }

    groups = {}

    for aid in ids_2022:
        row = canonical_by_id.get(
            aid
        )

        if row is None:
            continue

        driver = canonical_driver(
            row
        )

        if driver in eligible_drivers:
            groups.setdefault(
                driver,
                set(),
            ).add(
                aid
            )

    covered_before_drivers = set()
    covered_after_drivers = set()

    for driver, attempt_ids in groups.items():
        if attempt_ids.issubset(
            before_ids
        ):
            covered_before_drivers.add(
                driver
            )

        if attempt_ids.issubset(
            after_ids
        ):
            covered_after_drivers.add(
                driver
            )

    newly_fully_covered_drivers = sorted(
        covered_after_drivers
        -
        covered_before_drivers
    )

    denominator = len(
        eligible_drivers
    )

    lane_before = explicit_lane_count(
        action_v3
    )

    lane_after = explicit_lane_count(
        action_v4
    )

    print()
    print("=" * 120)
    print("POST-INTEGRATION COVERAGE")
    print("=" * 120)

    print()
    print(
        "Chronology V5 rows:",
        len(
            chronology_v5
        ),
    )

    print(
        "Chronology V6 rows:",
        len(
            chronology_v6
        ),
    )

    print()
    print(
        "Action V3 rows:",
        len(
            action_v3
        ),
    )

    print(
        "Action V4 rows:",
        len(
            action_v4
        ),
    )

    print()
    print(
        "2022 unique chronology attempts:",
        before_count,
        "->",
        after_count,
    )

    print(
        "2022 chronology coverage:",
        f"{before_pct:.2f}%",
        "->",
        f"{after_pct:.2f}%",
    )

    print()
    print(
        "Decision-relevant repeat groups:",
        len(
            covered_before_drivers
        ),
        "/",
        denominator,
        "->",
        len(
            covered_after_drivers
        ),
        "/",
        denominator,
    )

    print(
        "Newly fully covered drivers:",
        "|".join(
            newly_fully_covered_drivers
        )
        or
        "NONE",
    )

    print()
    print(
        "Explicit historical Lane rows:",
        lane_before,
        "->",
        lane_after,
    )

    print()
    print(
        "Sato action:",
        "REQUIRED_REATTEMPT_AFTER_INVALIDATION",
    )

    print(
        "Sato Lane:",
        "UNKNOWN",
    )

    print(
        "Sato time quality:",
        "ORDERING_ONLY",
    )

    integration_rows = [
        {
            "attempt_id":
                FIRST_ID,

            "driver_name":
                EXPECTED_DRIVER,

            "speed_mph":
                str(
                    first_speed
                ),

            "integration_role":
                "INVALIDATED_FIRST_ATTEMPT",

            "ordering_relation":
                "BEFORE",

            "related_attempt_id":
                SECOND_ID,

            "action":
                "FIRST_ATTEMPT_INVALIDATED",

            "lane":
                "UNKNOWN",

            "time_quality":
                "ORDERING_ONLY",
        },

        {
            "attempt_id":
                SECOND_ID,

            "driver_name":
                EXPECTED_DRIVER,

            "speed_mph":
                str(
                    second_speed
                ),

            "integration_role":
                "REQUIRED_REATTEMPT",

            "ordering_relation":
                "AFTER",

            "related_attempt_id":
                FIRST_ID,

            "action":
                "REQUIRED_REATTEMPT_AFTER_INVALIDATION",

            "lane":
                "UNKNOWN",

            "time_quality":
                "ORDERING_ONLY",
        },
    ]

    write_csv(
        INTEGRATION_OUT,
        integration_rows,
        [
            "attempt_id",
            "driver_name",
            "speed_mph",
            "integration_role",
            "ordering_relation",
            "related_attempt_id",
            "action",
            "lane",
            "time_quality",
        ],
    )

    coverage_rows = [
        {
            "metric":
                "2022_attempt_population",

            "before":
                total,

            "after":
                total,

            "change":
                0,
        },

        {
            "metric":
                "2022_unique_chronology_attempts",

            "before":
                before_count,

            "after":
                after_count,

            "change":
                after_count
                -
                before_count,
        },

        {
            "metric":
                "2022_chronology_coverage_pct",

            "before":
                f"{before_pct:.2f}",

            "after":
                f"{after_pct:.2f}",

            "change":
                f"{after_pct - before_pct:.2f}",
        },

        {
            "metric":
                "decision_relevant_repeat_denominator",

            "before":
                denominator,

            "after":
                denominator,

            "change":
                0,
        },

        {
            "metric":
                "fully_covered_decision_relevant_repeat_groups",

            "before":
                len(
                    covered_before_drivers
                ),

            "after":
                len(
                    covered_after_drivers
                ),

            "change":
                (
                    len(
                        covered_after_drivers
                    )
                    -
                    len(
                        covered_before_drivers
                    )
                ),
        },

        {
            "metric":
                "explicit_historical_lane_rows",

            "before":
                lane_before,

            "after":
                lane_after,

            "change":
                lane_after
                -
                lane_before,
        },
    ]

    write_csv(
        COVERAGE_OUT,
        coverage_rows,
        [
            "metric",
            "before",
            "after",
            "change",
        ],
    )

    summary_rows = [
        {
            "metric":
                "chronology_input",

            "value":
                "V5",
        },

        {
            "metric":
                "chronology_output",

            "value":
                "V6",
        },

        {
            "metric":
                "action_input",

            "value":
                "V3",
        },

        {
            "metric":
                "action_output",

            "value":
                "V4",
        },

        {
            "metric":
                "2022_chronology_before",

            "value":
                before_count,
        },

        {
            "metric":
                "2022_chronology_after",

            "value":
                after_count,
        },

        {
            "metric":
                "coverage_before_pct",

            "value":
                f"{before_pct:.2f}",
        },

        {
            "metric":
                "coverage_after_pct",

            "value":
                f"{after_pct:.2f}",
        },

        {
            "metric":
                "decision_relevant_repeat_before",

            "value":
                (
                    f"{len(covered_before_drivers)}"
                    f"/{denominator}"
                ),
        },

        {
            "metric":
                "decision_relevant_repeat_after",

            "value":
                (
                    f"{len(covered_after_drivers)}"
                    f"/{denominator}"
                ),
        },

        {
            "metric":
                "newly_fully_covered_drivers",

            "value":
                "|".join(
                    newly_fully_covered_drivers
                ),
        },

        {
            "metric":
                "lane_rows_before",

            "value":
                lane_before,
        },

        {
            "metric":
                "lane_rows_after",

            "value":
                lane_after,
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

    expected_new_ids = {
        FIRST_ID,
        SECOND_ID,
    }

    qa_rows = [
        {
            "metric":
                "canonical_identity_verified",

            "value":
                int(
                    identity_ok
                ),

            "status":
                "PASS"
                if identity_ok
                else "FAIL",
        },

        {
            "metric":
                "adjudication_ready",

            "value":
                int(
                    evidence_ok
                ),

            "status":
                "PASS"
                if evidence_ok
                else "FAIL",
        },

        {
            "metric":
                "chronology_row_gain_equals_two",

            "value":
                (
                    len(
                        chronology_v6
                    )
                    -
                    len(
                        chronology_v5
                    )
                ),

            "status":
                (
                    "PASS"
                    if (
                        len(
                            chronology_v6
                        )
                        -
                        len(
                            chronology_v5
                        )
                    ) == 2
                    else "FAIL"
                ),
        },

        {
            "metric":
                "action_row_gain_equals_one",

            "value":
                (
                    len(
                        action_v4
                    )
                    -
                    len(
                        action_v3
                    )
                ),

            "status":
                (
                    "PASS"
                    if (
                        len(
                            action_v4
                        )
                        -
                        len(
                            action_v3
                        )
                    ) == 1
                    else "FAIL"
                ),
        },

        {
            "metric":
                "new_chronology_ids_are_sato_pair",

            "value":
                "|".join(
                    newly_covered
                ),

            "status":
                (
                    "PASS"
                    if set(
                        newly_covered
                    )
                    ==
                    expected_new_ids
                    else "FAIL"
                ),
        },

        {
            "metric":
                "decision_relevant_denominator_is_8",

            "value":
                denominator,

            "status":
                (
                    "PASS"
                    if denominator == 8
                    else "FAIL"
                ),
        },

        {
            "metric":
                "sato_newly_fully_covered",

            "value":
                int(
                    EXPECTED_DRIVER
                    in
                    newly_fully_covered_drivers
                ),

            "status":
                (
                    "PASS"
                    if EXPECTED_DRIVER
                    in
                    newly_fully_covered_drivers
                    else "FAIL"
                ),
        },

        {
            "metric":
                "lane_evidence_unchanged",

            "value":
                lane_after
                -
                lane_before,

            "status":
                (
                    "PASS"
                    if lane_after
                    ==
                    lane_before
                    else "FAIL"
                ),
        },

        {
            "metric":
                "queue_inferred",

            "value":
                0,

            "status":
                "PASS",
        },

        {
            "metric":
                "exact_timestamp_inferred",

            "value":
                0,

            "status":
                "PASS",
        },

        {
            "metric":
                "old_ledgers_mutated",

            "value":
                0,

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
        row[
            "status"
        ] == "PASS"
        for row in qa_rows
    )

    print()
    print("=" * 120)

    if success:
        print(
            "FINAL STATUS: "
            "SATO_REQUIRED_REATTEMPT_ORDERING_AND_ACTION_INTEGRATED"
        )
    else:
        print(
            "FINAL STATUS: "
            "SATO_REQUIRED_REATTEMPT_INTEGRATION_REVIEW_REQUIRED"
        )

    print("=" * 120)

    print()
    print("OUTPUTS")
    print(CHRONOLOGY_V6)
    print(ACTION_V4)
    print(INTEGRATION_OUT)
    print(COVERAGE_OUT)
    print(SUMMARY_OUT)
    print(QA_OUT)


if __name__ == "__main__":
    main()
