from pathlib import Path
import csv


DECISION_STATE = Path(
    "weather/output/"
    "contemporaneous_decision_state_evidence_ledger_v2.csv"
)

QUEUE = Path(
    "weather/output/"
    "queue_requeue_evidence_ledger_v1.csv"
)

STATE_V2 = Path(
    "weather/output/"
    "decision_time_observable_state_v2.csv"
)


TARGETS = [
    "Scott McLaughlin",
    "David Malukas",
    "Callum Ilott",
    "Takuma Sato",
]


def txt(v):
    return "" if v is None else str(v).strip()


def read_csv(path):
    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as f:
        return list(csv.DictReader(f))


def print_row(row, fields):
    for field in fields:
        print(
            f"  {field}: "
            f"{txt(row.get(field)) or 'BLANK'}"
        )


def main():

    print()
    print("=" * 120)
    print(
        "R3A.1A — DECISION-TIME STATE V2 "
        "BINDING ANOMALY AUDIT"
    )
    print("=" * 120)

    required = [
        DECISION_STATE,
        QUEUE,
        STATE_V2,
    ]

    print()
    print("INPUT CHECK")
    print("-" * 120)

    for path in required:
        print(
            f"{path}: "
            f"{'PRESENT' if path.exists() else 'MISSING'}"
        )

    if not all(
        path.exists()
        for path in required
    ):
        print()
        print(
            "FINAL STATUS: "
            "R3A1A_INPUT_MISSING"
        )
        return

    decision_rows = read_csv(
        DECISION_STATE
    )

    queue_rows = read_csv(
        QUEUE
    )

    states = read_csv(
        STATE_V2
    )

    state_by_driver = {
        txt(row.get("driver_name")):
        row
        for row in states
    }

    print()
    print("=" * 120)
    print("STATE V2 PAIRS")
    print("=" * 120)

    for driver in TARGETS:

        state = state_by_driver.get(
            driver
        )

        print()
        print("-" * 120)
        print(driver)

        if not state:
            print("  STATE ROW MISSING")
            continue

        print(
            "  first_attempt_id:",
            txt(
                state.get(
                    "first_attempt_id"
                )
            ),
        )

        print(
            "  second_attempt_id:",
            txt(
                state.get(
                    "second_attempt_id"
                )
            ),
        )

        print(
            "  current_rank:",
            txt(
                state.get(
                    "current_rank"
                )
            ),
        )

        print(
            "  queue_membership:",
            txt(
                state.get(
                    "queue_membership"
                )
            ),
        )

        print(
            "  relative_run_order:",
            txt(
                state.get(
                    "relative_run_order"
                )
            ),
        )

    print()
    print("=" * 120)
    print("RAW DECISION-STATE ROWS")
    print("=" * 120)

    decision_fields = [
        "state_id",
        "driver_name",
        "subject_attempt_id",
        "related_attempt_id",
        "state_stage",
        "rank",
        "rank_lower_bound",
        "rank_upper_bound",
        "top12_state",
        "cutoff_rank",
        "cutoff_speed_mph",
        "action",
        "lane",
        "time_quality",
        "source_name",
        "source_class",
        "source_semantic",
        "promotion_status",
        "notes",
    ]

    for driver in TARGETS:

        rows = [
            row
            for row in decision_rows
            if txt(
                row.get(
                    "driver_name"
                )
            )
            ==
            driver
        ]

        print()
        print("#" * 120)
        print(
            driver,
            "decision-state rows:",
            len(rows),
        )

        for i, row in enumerate(
            rows,
            start=1,
        ):

            print()
            print(
                f"DECISION ROW {i}"
            )

            print_row(
                row,
                decision_fields,
            )

    print()
    print("=" * 120)
    print("RAW QUEUE ROWS")
    print("=" * 120)

    queue_fields = [
        "queue_state_id",
        "driver_name",
        "subject_attempt_id",
        "related_attempt_id",
        "evidence_family",
        "state_semantic",
        "queue_membership",
        "queue_lane",
        "queue_position",
        "relative_run_order",
        "related_driver",
        "existing_rank",
        "time_quality",
        "source_name",
        "source_class",
        "source_reference",
        "promotion_status",
        "notes",
    ]

    for driver in TARGETS:

        rows = [
            row
            for row in queue_rows
            if txt(
                row.get(
                    "driver_name"
                )
            )
            ==
            driver
        ]

        print()
        print("#" * 120)
        print(
            driver,
            "queue rows:",
            len(rows),
        )

        for i, row in enumerate(
            rows,
            start=1,
        ):

            print()
            print(
                f"QUEUE ROW {i}"
            )

            print_row(
                row,
                queue_fields,
            )

    print()
    print("=" * 120)
    print(
        "FINAL STATUS: "
        "R3A1A_STATE_BINDING_ANOMALY_AUDIT_COMPLETE"
    )
    print("=" * 120)


if __name__ == "__main__":
    main()
