from pathlib import Path
import csv

CHRONOLOGY = Path(
    "weather/output/unified_attempt_chronology_constraint_ledger_v5.csv"
)

ACTION = Path(
    "weather/output/unified_attempt_action_lane_ledger_v3.csv"
)

FIRST_ID = "3f221659-74ff-5901-97dc-08071a734690"
SECOND_ID = "21e8c99e-b04c-516d-85a8-ccfbaed7ff46"


def txt(v):
    return "" if v is None else str(v).strip()


def read_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def main():
    print()
    print("=" * 110)
    print("R1G.27C — SATO EXISTING V5 CHRONOLOGY ROW AUDIT")
    print("=" * 110)

    print()
    print("INPUT CHECK")
    print("-" * 110)

    for path in [CHRONOLOGY, ACTION]:
        print(
            f"{path}: "
            f"{'PRESENT' if path.exists() else 'MISSING'}"
        )

    if not CHRONOLOGY.exists() or not ACTION.exists():
        print()
        print("FINAL STATUS: SATO_EXISTING_ROW_AUDIT_INPUT_MISSING")
        return

    chronology = read_csv(CHRONOLOGY)
    action = read_csv(ACTION)

    hits = [
        row
        for row in chronology
        if txt(row.get("attempt_id")) in {FIRST_ID, SECOND_ID}
    ]

    action_hits = [
        row
        for row in action
        if (
            txt(row.get("subject_attempt_id")) in {FIRST_ID, SECOND_ID}
            or
            txt(row.get("related_attempt_id")) in {FIRST_ID, SECOND_ID}
        )
    ]

    fields = [
        "year",
        "attempt_id",
        "driver_name",
        "car_number",
        "car_attempt_index",
        "constraint_class",
        "time_quality",
        "source_layer",
        "source_semantic",
        "result_status",
        "chronology_usable",
        "performance_environment_usable",
        "queue_replay_usable",
        "ordering_relation",
        "related_attempt_id",
        "ordering_role",
        "evidence_type",
        "action",
        "lane",
        "evidence_id",
        "source_authority",
        "source_title",
        "source_url",
        "evidence_summary",
        "notes",
    ]

    print()
    print("=" * 110)
    print("SATO CHRONOLOGY V5 ROWS")
    print("=" * 110)

    print()
    print("Hit count:", len(hits))

    for i, row in enumerate(hits, start=1):
        print()
        print("-" * 110)
        print(f"ROW {i}")
        print("-" * 110)

        for field in fields:
            if field in row:
                print(
                    f"{field}: {repr(txt(row.get(field)))}"
                )

    print()
    print("=" * 110)
    print("SATO ACTION V3 ROWS")
    print("=" * 110)

    print()
    print("Action hit count:", len(action_hits))

    for i, row in enumerate(action_hits, start=1):
        print()
        print("-" * 110)
        print(f"ACTION ROW {i}")
        print("-" * 110)

        for key, value in row.items():
            print(
                f"{key}: {repr(txt(value))}"
            )

    ids = {
        txt(row.get("attempt_id"))
        for row in hits
    }

    both_present = ids == {
        FIRST_ID,
        SECOND_ID,
    }

    chronology_usable = (
        len(hits) == 2
        and
        all(
            txt(row.get("chronology_usable")).lower() == "true"
            for row in hits
        )
    )

    no_lane_claim = all(
        txt(row.get("lane")).upper() in {"", "UNKNOWN"}
        for row in hits
    )

    action_gap = len(action_hits) == 0

    print()
    print("=" * 110)
    print("AUDIT SUMMARY")
    print("=" * 110)

    print()
    print("Both canonical Sato attempts already present:", both_present)
    print("Both chronology usable:", chronology_usable)
    print("No qualifying Lane claim:", no_lane_claim)
    print("Action ledger currently missing Sato:", action_gap)

    print()
    print("=" * 110)

    if (
        both_present
        and chronology_usable
        and no_lane_claim
        and action_gap
    ):
        print(
            "FINAL STATUS: "
            "SATO_CHRONOLOGY_ALREADY_COVERED_ACTION_ONLY_PROMOTION_READY"
        )
    else:
        print(
            "FINAL STATUS: "
            "SATO_EXISTING_CHRONOLOGY_REVIEW_REQUIRED"
        )

    print("=" * 110)


if __name__ == "__main__":
    main()
