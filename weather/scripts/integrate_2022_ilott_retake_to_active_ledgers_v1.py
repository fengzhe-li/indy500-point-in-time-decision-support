from pathlib import Path
import csv
from decimal import Decimal, InvalidOperation

PHASE = "R1G.26F"

CANONICAL = Path("data/canonical/v1/attempts.csv")
RESULT_MATCH_V3 = Path(
    "weather/output/chronology_rescue_2022_result_to_canonical_attempt_matches_v3.csv"
)
CHRONOLOGY_V4 = Path(
    "weather/output/unified_attempt_chronology_constraint_ledger_v4.csv"
)
ACTION_V2 = Path(
    "weather/output/unified_attempt_action_lane_ledger_v2.csv"
)
EVIDENCE_V2 = Path(
    "weather/output/chronology_rescue_2022_ilott_autosport_retake_evidence_v2.csv"
)
ADJUDICATION_V2 = Path(
    "weather/output/chronology_rescue_2022_ilott_autosport_retake_adjudication_v2.csv"
)

OUTPUT_DIR = Path("weather/output")

CHRONOLOGY_V5 = OUTPUT_DIR / "unified_attempt_chronology_constraint_ledger_v5.csv"
ACTION_V3 = OUTPUT_DIR / "unified_attempt_action_lane_ledger_v3.csv"
INTEGRATION_AUDIT_OUT = (
    OUTPUT_DIR / "chronology_rescue_2022_ilott_retake_ledger_integration_v1.csv"
)
COVERAGE_OUT = (
    OUTPUT_DIR / "chronology_rescue_2022_ilott_retake_postintegration_coverage_v1.csv"
)
SUMMARY_OUT = (
    OUTPUT_DIR / "chronology_rescue_2022_ilott_retake_ledger_integration_summary_v1.csv"
)
QA_OUT = (
    OUTPUT_DIR / "chronology_rescue_2022_ilott_retake_ledger_integration_v1_qa.csv"
)

FIRST_ATTEMPT_ID = "3cd6d98a-da75-5822-8dae-05e83ad8457c"
SECOND_ATTEMPT_ID = "8fa25fec-e5a6-5844-b3d7-f67c9dc91378"

EXPECTED_DRIVER = "Callum Ilott"
EXPECTED_CAR = "77"
EXPECTED_FIRST_SPEED = Decimal("230.212")
EXPECTED_SECOND_SPEED = Decimal("230.961")

EVIDENCE_ID = "R1G26D-ILOTT-AUTOSPORT-RETAKE"
SOURCE_AUTHORITY = "AUTOSPORT"
SOURCE_TITLE = "Indy 500: Sato, Grosjean, Johnson into top 12 fight"
SOURCE_URL = (
    "https://www.autosport.com/indycar/news/"
    "indy-500-sato-grosjean-johnson-into-top-12-fight-p13-33-set/"
    "10308540/"
)
SOURCE_CLASS = "REPUTABLE_SECONDARY_EDITORIAL"
SOURCE_DATE_LABEL = "EDITED"
SOURCE_DATE_DISPLAY = "May 22, 2022, 2:31 AM"


def txt(v):
    return "" if v is None else str(v).strip()


def read_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return list(reader), list(reader.fieldnames or [])


def write_csv(path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
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


def canonical_speed(row):
    for field in [
        "four_lap_average_speed_mph",
        "average_speed_mph",
        "speed_mph",
    ]:
        value = decimal_value(row.get(field))

        if value is not None:
            return value

    return None


def canonical_driver(row):
    for field in [
        "driver_name",
        "driver",
        "driver_full_name",
    ]:
        value = txt(row.get(field))

        if value:
            return value

    return ""


def empty_row(fields):
    return {field: "" for field in fields}


def set_if_present(row, field, value):
    if field in row:
        row[field] = value


def row_contains_attempt(row, attempt_id):
    return attempt_id in " | ".join(txt(v) for v in row.values())


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print()
    print("=" * 120)
    print("R1G.26F — 2022 CALLUM ILOTT RETAKE ACTIVE LEDGER INTEGRATION V1")
    print("=" * 120)

    required = [
        CANONICAL,
        RESULT_MATCH_V3,
        CHRONOLOGY_V4,
        ACTION_V2,
        EVIDENCE_V2,
        ADJUDICATION_V2,
    ]

    missing = []

    print()
    print("INPUT CHECK")
    print("-" * 120)

    for path in required:
        exists = path.exists()
        print(f"{path}: {'PRESENT' if exists else 'MISSING'}")

        if not exists:
            missing.append(path)

    if missing:
        print()
        print("FINAL STATUS: ILOTT_RETAKE_LEDGER_INTEGRATION_INPUT_MISSING")
        return

    canonical, _ = read_csv(CANONICAL)
    result_v3, _ = read_csv(RESULT_MATCH_V3)
    chronology_v4, chronology_fields = read_csv(CHRONOLOGY_V4)
    action_v2, action_fields = read_csv(ACTION_V2)
    evidence_v2, _ = read_csv(EVIDENCE_V2)
    adjudication_v2, _ = read_csv(ADJUDICATION_V2)

    canonical_by_id = {
        txt(row.get("attempt_id")): row
        for row in canonical
        if txt(row.get("attempt_id"))
    }

    first = canonical_by_id.get(FIRST_ATTEMPT_ID)
    second = canonical_by_id.get(SECOND_ATTEMPT_ID)

    if first is None or second is None:
        print()
        print("FINAL STATUS: ILOTT_CANONICAL_TARGET_MISSING")
        return

    first_driver = canonical_driver(first)
    second_driver = canonical_driver(second)

    first_car = txt(first.get("car_number"))
    second_car = txt(second.get("car_number"))

    first_speed = canonical_speed(first)
    second_speed = canonical_speed(second)

    first_index = txt(first.get("car_attempt_index"))
    second_index = txt(second.get("car_attempt_index"))

    first_status = txt(first.get("result_status"))
    second_status = txt(second.get("result_status"))

    session_id = (
        txt(first.get("session_id"))
        or txt(second.get("session_id"))
    )

    identity_ok = all([
        first_driver == EXPECTED_DRIVER,
        second_driver == EXPECTED_DRIVER,
        first_car == EXPECTED_CAR,
        second_car == EXPECTED_CAR,
        first_speed == EXPECTED_FIRST_SPEED,
        second_speed == EXPECTED_SECOND_SPEED,
        first_index == "1",
        second_index == "2",
    ])

    print()
    print("=" * 120)
    print("CANONICAL GROUNDING")
    print("=" * 120)

    print()
    print(
        FIRST_ATTEMPT_ID,
        "|",
        first_driver,
        "|",
        repr(first_car),
        "| index",
        first_index,
        "|",
        first_speed,
    )

    print(
        SECOND_ATTEMPT_ID,
        "|",
        second_driver,
        "|",
        repr(second_car),
        "| index",
        second_index,
        "|",
        second_speed,
    )

    print()
    print("Identity check:", identity_ok)

    if not identity_ok:
        print()
        print("FINAL STATUS: ILOTT_CANONICAL_GROUNDING_FAILED")
        return

    result_by_id = {
        txt(row.get("attempt_id")): row
        for row in result_v3
        if txt(row.get("attempt_id"))
    }

    first_result = result_by_id.get(FIRST_ATTEMPT_ID)
    second_result = result_by_id.get(SECOND_ATTEMPT_ID)

    result_grounding_ok = (
        first_result is not None
        and second_result is not None
    )

    if not result_grounding_ok:
        print()
        print("FINAL STATUS: ILOTT_RESULT_V3_GROUNDING_FAILED")
        return

    first_official_row = txt(first_result.get("official_result_row"))
    second_official_row = txt(second_result.get("official_result_row"))

    first_official_status = txt(first_result.get("official_status"))
    second_official_status = txt(second_result.get("official_status"))

    evidence_match = [
        row
        for row in evidence_v2
        if txt(row.get("evidence_id")) == EVIDENCE_ID
    ]

    adjudication_match = [
        row
        for row in adjudication_v2
        if txt(row.get("evidence_id")) == EVIDENCE_ID
    ]

    evidence_ok = len(evidence_match) == 1

    adjudication_ok = (
        len(adjudication_match) == 1
        and
        txt(adjudication_match[0].get("promotion_ready")).lower()
        == "true"
    )

    if not (evidence_ok and adjudication_ok):
        print()
        print("FINAL STATUS: ILOTT_ADJUDICATED_EVIDENCE_NOT_READY")
        return

    chronology_existing_hits = [
        row
        for row in chronology_v4
        if (
            row_contains_attempt(row, FIRST_ATTEMPT_ID)
            or
            row_contains_attempt(row, SECOND_ATTEMPT_ID)
        )
    ]

    action_existing_hits = [
        row
        for row in action_v2
        if (
            row_contains_attempt(row, FIRST_ATTEMPT_ID)
            or
            row_contains_attempt(row, SECOND_ATTEMPT_ID)
        )
    ]

    duplicate_free = (
        len(chronology_existing_hits) == 0
        and
        len(action_existing_hits) == 0
    )

    print()
    print("=" * 120)
    print("DUPLICATE CHECK")
    print("=" * 120)

    print()
    print(
        "Chronology V4 existing Ilott hits:",
        len(chronology_existing_hits),
    )

    print(
        "Action V2 existing Ilott hits:",
        len(action_existing_hits),
    )

    print("Duplicate free:", duplicate_free)

    if not duplicate_free:
        print()
        print("FINAL STATUS: ILOTT_LEDGER_DUPLICATE_REVIEW_REQUIRED")
        return

    chronology_v5 = [dict(row) for row in chronology_v4]

    first_chron = empty_row(chronology_fields)

    values = {
        "year": "2022",
        "attempt_id": FIRST_ATTEMPT_ID,
        "session_id": session_id,
        "car_number": first_car,
        "driver_name": first_driver,
        "car_attempt_index": first_index,
        "constraint_class": "ORDERING_ONLY",
        "time_quality": "ORDERING_ONLY",
        "source_layer": "SECONDARY_EDITORIAL",
        "source_semantic": "DIRECT_RETAKE_ORDERING",
        "source_event_id": EVIDENCE_ID,
        "anchor_event_type": "INITIAL_ATTEMPT_BEFORE_RETAKE",
        "result_status": first_status,
        "chronology_usable": "True",
        "performance_environment_usable": "False",
        "queue_replay_usable": "False",
        "notes": (
            "Autosport reports that Callum Ilott later made a retake run "
            "and improved by approximately 0.7 mph. This row represents "
            "the initial attempt in the supported ordering relation. "
            "No timestamp, Lane, withdrawal semantics, queue position, "
            "or queue wait is inferred."
        ),
        "evidence_id": EVIDENCE_ID,
        "evidence_stage": PHASE,
        "source_authority": SOURCE_AUTHORITY,
        "source_title": SOURCE_TITLE,
        "source_url": SOURCE_URL,
        "official_result_row": first_official_row,
        "ordering_relation": "BEFORE",
        "evidence_summary": (
            "Initial Ilott attempt precedes the Autosport-described "
            "retake attempt; canonical speed delta 0.749 mph is "
            "compatible with source wording of approximately 0.7 mph."
        ),
        "related_attempt_id": SECOND_ATTEMPT_ID,
        "ordering_role": "INITIAL_ATTEMPT",
        "evidence_type": "REPEAT_ATTEMPT_ACTION_ORDERING",
        "action": "",
        "lane": "UNKNOWN",
        "source_candidate_id": EVIDENCE_ID,
        "evidence_quality": "HIGH",
    }

    for field, value in values.items():
        set_if_present(
            first_chron,
            field,
            value,
        )

    second_chron = empty_row(chronology_fields)

    values = {
        "year": "2022",
        "attempt_id": SECOND_ATTEMPT_ID,
        "session_id": session_id,
        "car_number": second_car,
        "driver_name": second_driver,
        "car_attempt_index": second_index,
        "constraint_class": "ORDERING_ONLY",
        "time_quality": "ORDERING_ONLY",
        "source_layer": "SECONDARY_EDITORIAL",
        "source_semantic": "DIRECT_RETAKE_ORDERING",
        "source_event_id": EVIDENCE_ID,
        "anchor_event_type": "RETAKE_ATTEMPT_AFTER_INITIAL",
        "result_status": second_status,
        "chronology_usable": "True",
        "performance_environment_usable": "False",
        "queue_replay_usable": "False",
        "notes": (
            "Autosport explicitly describes Callum Ilott making a "
            "retake run and improving approximately 0.7 mph. "
            "Lane, withdrawal semantics, queue position, queue wait, "
            "and exact timestamp remain UNKNOWN."
        ),
        "evidence_id": EVIDENCE_ID,
        "evidence_stage": PHASE,
        "source_authority": SOURCE_AUTHORITY,
        "source_title": SOURCE_TITLE,
        "source_url": SOURCE_URL,
        "official_result_row": second_official_row,
        "ordering_relation": "AFTER",
        "evidence_summary": (
            "Autosport identifies this as Ilott's retake run and "
            "reports an approximately 0.7 mph improvement."
        ),
        "related_attempt_id": FIRST_ATTEMPT_ID,
        "ordering_role": "RETAKE_ATTEMPT",
        "evidence_type": "REPEAT_ATTEMPT_ACTION_ORDERING",
        "action": "RETAKE_RUN",
        "lane": "UNKNOWN",
        "source_candidate_id": EVIDENCE_ID,
        "evidence_quality": "HIGH",
    }

    for field, value in values.items():
        set_if_present(
            second_chron,
            field,
            value,
        )

    chronology_v5.extend([
        first_chron,
        second_chron,
    ])

    action_v3 = [dict(row) for row in action_v2]

    ilott_action = empty_row(action_fields)

    values = {
        "evidence_id": EVIDENCE_ID,
        "year": "2022",
        "subject_attempt_id": SECOND_ATTEMPT_ID,
        "related_attempt_id": FIRST_ATTEMPT_ID,
        "session_id": session_id,
        "car_number": second_car,
        "driver_name": second_driver,
        "action": "RETAKE_RUN",
        "lane": "UNKNOWN",
        "relation": "RETAKE_ATTEMPT_AFTER_INITIAL_ATTEMPT",
        "source_name": SOURCE_AUTHORITY,
        "source_class": SOURCE_CLASS,
        "source_candidate_id": EVIDENCE_ID,
        "evidence_quality": "HIGH",
        "chronology_usable": "True",
        "queue_position_known": "False",
        "queue_wait_known": "False",
        "canonical_mutated": "False",
        "notes": (
            "Autosport directly describes Ilott making a retake run "
            "and improving approximately 0.7 mph. Canonical pair is "
            "230.212 -> 230.961 (+0.749 mph). "
            "Lane, withdrawal semantics, queue position, queue wait, "
            "and exact timestamp remain UNKNOWN. "
            f"Source date semantics: {SOURCE_DATE_LABEL} "
            f"{SOURCE_DATE_DISPLAY}."
        ),
        "subject_speed_mph": str(second_speed),
        "related_speed_mph": str(first_speed),
        "official_subject_status": second_official_status,
        "source_evidence_id": EVIDENCE_ID,
        "promotion_status": "PROMOTED_TO_ACTIVE_LEDGER",
    }

    for field, value in values.items():
        set_if_present(
            ilott_action,
            field,
            value,
        )

    action_v3.append(
        ilott_action
    )

    chronology_new_hits = [
        row
        for row in chronology_v5
        if txt(row.get("evidence_id")) == EVIDENCE_ID
    ]

    action_new_hits = [
        row
        for row in action_v3
        if txt(row.get("evidence_id")) == EVIDENCE_ID
    ]

    chronology_count_ok = (
        len(chronology_v5)
        ==
        len(chronology_v4) + 2
    )

    action_count_ok = (
        len(action_v3)
        ==
        len(action_v2) + 1
    )

    canonical_2022_ids = {
        txt(row.get("attempt_id"))
        for row in canonical
        if (
            txt(row.get("year")) == "2022"
            and
            txt(row.get("attempt_id"))
        )
    }

    chronology_v4_2022_ids = {
        txt(row.get("attempt_id"))
        for row in chronology_v4
        if (
            txt(row.get("year")) == "2022"
            and
            txt(row.get("attempt_id"))
            and
            txt(row.get("chronology_usable")).lower() == "true"
        )
    }

    chronology_v5_2022_ids = {
        txt(row.get("attempt_id"))
        for row in chronology_v5
        if (
            txt(row.get("year")) == "2022"
            and
            txt(row.get("attempt_id"))
            and
            txt(row.get("chronology_usable")).lower() == "true"
        )
    }

    total_2022 = len(canonical_2022_ids)
    before_unique = len(chronology_v4_2022_ids)
    after_unique = len(chronology_v5_2022_ids)

    before_pct = (
        before_unique / total_2022 * 100
        if total_2022
        else 0
    )

    after_pct = (
        after_unique / total_2022 * 100
        if total_2022
        else 0
    )

    groups = {}

    for row in canonical:
        if txt(row.get("year")) != "2022":
            continue

        driver = canonical_driver(row)
        aid = txt(row.get("attempt_id"))

        if not driver or not aid:
            continue

        groups.setdefault(
            driver,
            []
        ).append(aid)

    repeat_pairs = {
        driver: ids
        for driver, ids in groups.items()
        if len(ids) >= 2
    }

    fully_before = 0
    fully_after = 0

    for ids in repeat_pairs.values():
        id_set = set(ids)

        if id_set.issubset(
            chronology_v4_2022_ids
        ):
            fully_before += 1

        if id_set.issubset(
            chronology_v5_2022_ids
        ):
            fully_after += 1

    explicit_lane_v2 = sum(
        1
        for row in action_v2
        if txt(row.get("lane")).upper()
        not in {"", "UNKNOWN"}
    )

    explicit_lane_v3 = sum(
        1
        for row in action_v3
        if txt(row.get("lane")).upper()
        not in {"", "UNKNOWN"}
    )

    lane_unchanged = (
        explicit_lane_v2
        ==
        explicit_lane_v3
    )

    write_csv(
        CHRONOLOGY_V5,
        chronology_v5,
        chronology_fields,
    )

    write_csv(
        ACTION_V3,
        action_v3,
        action_fields,
    )

    integration_rows = [
        {
            "phase": PHASE,
            "ledger": "CHRONOLOGY_V5",
            "attempt_id": FIRST_ATTEMPT_ID,
            "related_attempt_id": SECOND_ATTEMPT_ID,
            "driver_name": EXPECTED_DRIVER,
            "car_number": EXPECTED_CAR,
            "role": "INITIAL_ATTEMPT",
            "relation": "BEFORE",
            "action": "",
            "lane": "UNKNOWN",
            "time_quality": "ORDERING_ONLY",
            "chronology_usable": "True",
            "evidence_id": EVIDENCE_ID,
            "source_authority": SOURCE_AUTHORITY,
            "evidence_quality": "HIGH",
        },
        {
            "phase": PHASE,
            "ledger": "CHRONOLOGY_V5",
            "attempt_id": SECOND_ATTEMPT_ID,
            "related_attempt_id": FIRST_ATTEMPT_ID,
            "driver_name": EXPECTED_DRIVER,
            "car_number": EXPECTED_CAR,
            "role": "RETAKE_ATTEMPT",
            "relation": "AFTER",
            "action": "RETAKE_RUN",
            "lane": "UNKNOWN",
            "time_quality": "ORDERING_ONLY",
            "chronology_usable": "True",
            "evidence_id": EVIDENCE_ID,
            "source_authority": SOURCE_AUTHORITY,
            "evidence_quality": "HIGH",
        },
        {
            "phase": PHASE,
            "ledger": "ACTION_V3",
            "attempt_id": SECOND_ATTEMPT_ID,
            "related_attempt_id": FIRST_ATTEMPT_ID,
            "driver_name": EXPECTED_DRIVER,
            "car_number": EXPECTED_CAR,
            "role": "RETAKE_ATTEMPT",
            "relation": "RETAKE_ATTEMPT_AFTER_INITIAL_ATTEMPT",
            "action": "RETAKE_RUN",
            "lane": "UNKNOWN",
            "time_quality": "ORDERING_ONLY",
            "chronology_usable": "True",
            "evidence_id": EVIDENCE_ID,
            "source_authority": SOURCE_AUTHORITY,
            "evidence_quality": "HIGH",
        },
    ]

    write_csv(
        INTEGRATION_AUDIT_OUT,
        integration_rows,
        [
            "phase",
            "ledger",
            "attempt_id",
            "related_attempt_id",
            "driver_name",
            "car_number",
            "role",
            "relation",
            "action",
            "lane",
            "time_quality",
            "chronology_usable",
            "evidence_id",
            "source_authority",
            "evidence_quality",
        ],
    )

    coverage_rows = [
        {
            "metric": "canonical_2022_attempts",
            "before": total_2022,
            "after": total_2022,
            "change": 0,
        },
        {
            "metric": "2022_unique_chronology_attempts",
            "before": before_unique,
            "after": after_unique,
            "change": after_unique - before_unique,
        },
        {
            "metric": "2022_chronology_coverage_pct",
            "before": f"{before_pct:.2f}",
            "after": f"{after_pct:.2f}",
            "change": f"{after_pct - before_pct:.2f}",
        },
        {
            "metric": "fully_chronology_covered_repeat_pairs",
            "before": fully_before,
            "after": fully_after,
            "change": fully_after - fully_before,
        },
        {
            "metric": "explicit_historical_lane_rows",
            "before": explicit_lane_v2,
            "after": explicit_lane_v3,
            "change": explicit_lane_v3 - explicit_lane_v2,
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
            "metric": "chronology_v4_rows",
            "value": len(chronology_v4),
        },
        {
            "metric": "chronology_v5_rows",
            "value": len(chronology_v5),
        },
        {
            "metric": "action_v2_rows",
            "value": len(action_v2),
        },
        {
            "metric": "action_v3_rows",
            "value": len(action_v3),
        },
        {
            "metric": "new_chronology_rows",
            "value": len(chronology_new_hits),
        },
        {
            "metric": "new_action_rows",
            "value": len(action_new_hits),
        },
        {
            "metric": "2022_unique_chronology_attempts_before",
            "value": before_unique,
        },
        {
            "metric": "2022_unique_chronology_attempts_after",
            "value": after_unique,
        },
        {
            "metric": "fully_covered_repeat_pairs_before",
            "value": fully_before,
        },
        {
            "metric": "fully_covered_repeat_pairs_after",
            "value": fully_after,
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

    qa_rows = [
        {
            "metric": "canonical_identity_grounded",
            "value": int(identity_ok),
            "status": "PASS" if identity_ok else "FAIL",
        },
        {
            "metric": "result_v3_grounded",
            "value": int(result_grounding_ok),
            "status": "PASS" if result_grounding_ok else "FAIL",
        },
        {
            "metric": "adjudicated_evidence_ready",
            "value": int(evidence_ok and adjudication_ok),
            "status": (
                "PASS"
                if evidence_ok and adjudication_ok
                else "FAIL"
            ),
        },
        {
            "metric": "preintegration_duplicate_free",
            "value": int(duplicate_free),
            "status": "PASS" if duplicate_free else "FAIL",
        },
        {
            "metric": "chronology_row_count_increment",
            "value": len(chronology_v5) - len(chronology_v4),
            "status": "PASS" if chronology_count_ok else "FAIL",
        },
        {
            "metric": "action_row_count_increment",
            "value": len(action_v3) - len(action_v2),
            "status": "PASS" if action_count_ok else "FAIL",
        },
        {
            "metric": "new_chronology_evidence_rows",
            "value": len(chronology_new_hits),
            "status": (
                "PASS"
                if len(chronology_new_hits) == 2
                else "FAIL"
            ),
        },
        {
            "metric": "new_action_evidence_rows",
            "value": len(action_new_hits),
            "status": (
                "PASS"
                if len(action_new_hits) == 1
                else "FAIL"
            ),
        },
        {
            "metric": "lane_evidence_count_unchanged",
            "value": int(lane_unchanged),
            "status": "PASS" if lane_unchanged else "FAIL",
        },
        {
            "metric": "canonical_mutated",
            "value": 0,
            "status": "PASS",
        },
        {
            "metric": "chronology_v4_mutated",
            "value": 0,
            "status": "PASS",
        },
        {
            "metric": "action_v2_mutated",
            "value": 0,
            "status": "PASS",
        },
        {
            "metric": "phase5_to_phase8_mutated",
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
    print("POST-INTEGRATION COVERAGE")
    print("=" * 120)

    print()
    print(
        "Chronology V4 rows:",
        len(chronology_v4),
    )

    print(
        "Chronology V5 rows:",
        len(chronology_v5),
    )

    print()
    print(
        "Action V2 rows:",
        len(action_v2),
    )

    print(
        "Action V3 rows:",
        len(action_v3),
    )

    print()
    print(
        "2022 unique chronology attempts:",
        before_unique,
        "->",
        after_unique,
    )

    print(
        "2022 chronology coverage:",
        f"{before_pct:.2f}%",
        "->",
        f"{after_pct:.2f}%",
    )

    print()
    print(
        "Fully chronology-covered repeat pairs:",
        fully_before,
        "/",
        len(repeat_pairs),
        "->",
        fully_after,
        "/",
        len(repeat_pairs),
    )

    print()
    print(
        "Explicit historical Lane rows:",
        explicit_lane_v2,
        "->",
        explicit_lane_v3,
    )

    print()
    print(
        "Ilott action:",
        "RETAKE_RUN",
    )

    print(
        "Ilott Lane:",
        "UNKNOWN",
    )

    print(
        "Ilott time quality:",
        "ORDERING_ONLY",
    )

    success = all([
        identity_ok,
        result_grounding_ok,
        evidence_ok,
        adjudication_ok,
        duplicate_free,
        chronology_count_ok,
        action_count_ok,
        len(chronology_new_hits) == 2,
        len(action_new_hits) == 1,
        lane_unchanged,
        after_unique == before_unique + 2,
    ])

    print()
    print("=" * 120)

    if success:
        print(
            "FINAL STATUS: "
            "ILOTT_RETAKE_ORDERING_AND_ACTION_INTEGRATED"
        )
    else:
        print(
            "FINAL STATUS: "
            "ILOTT_RETAKE_LEDGER_INTEGRATION_REVIEW_REQUIRED"
        )

    print("=" * 120)

    print()
    print("OUTPUTS")
    print(CHRONOLOGY_V5)
    print(ACTION_V3)
    print(INTEGRATION_AUDIT_OUT)
    print(COVERAGE_OUT)
    print(SUMMARY_OUT)
    print(QA_OUT)


if __name__ == "__main__":
    main()
