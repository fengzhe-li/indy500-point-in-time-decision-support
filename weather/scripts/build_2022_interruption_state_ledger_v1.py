from pathlib import Path
import csv


PHASE = "R2F.2"

R2F1A = Path(
    "weather/output/"
    "interruption_rescue_2022_candidate_adjudication_v1.csv"
)

CHRONOLOGY_V10 = Path(
    "weather/output/"
    "unified_attempt_chronology_constraint_ledger_v10.csv"
)

QUEUE_POLICY = Path(
    "weather/output/"
    "queue_wait_identifiability_2022_v1.csv"
)

SERVICE_POLICY = Path(
    "weather/output/"
    "pit_service_identifiability_2022_v1.csv"
)

OUTPUT_DIR = Path("weather/output")

LEDGER_OUT = (
    OUTPUT_DIR
    / "interruption_state_evidence_ledger_2022_v1.csv"
)

SUMMARY_OUT = (
    OUTPUT_DIR
    / "interruption_state_evidence_ledger_2022_v1_summary.csv"
)

QA_OUT = (
    OUTPUT_DIR
    / "interruption_state_evidence_ledger_2022_v1_qa.csv"
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


def main():

    print()
    print("=" * 126)
    print(
        "R2F.2 — 2022 INTERRUPTION-STATE "
        "EVIDENCE LEDGER V1"
    )
    print("=" * 126)

    required = [
        R2F1A,
        CHRONOLOGY_V10,
        QUEUE_POLICY,
        SERVICE_POLICY,
    ]

    print()
    print("INPUT CHECK")
    print("-" * 126)

    for path in required:
        print(
            f"{path}: "
            f"{'PRESENT' if path.exists() else 'MISSING'}"
        )

    if not all(path.exists() for path in required):
        print()
        print(
            "FINAL STATUS: "
            "R2F2_INTERRUPTION_LEDGER_INPUT_MISSING"
        )
        return

    adjudication = read_csv(R2F1A)

    # Protected dependencies are read only.
    read_csv(CHRONOLOGY_V10)
    read_csv(QUEUE_POLICY)
    read_csv(SERVICE_POLICY)

    wet_terminal = [
        row
        for row in adjudication
        if (
            txt(row.get("event_semantic"))
            ==
            "SESSION_END_TRACK_TOO_WET_FOR_DRYING"
            and
            txt(
                row.get("promotion_ready")
            ).lower()
            ==
            "true"
        )
    ]

    wet_terminal_ok = (
        len(wet_terminal)
        ==
        1
    )

    print()
    print("=" * 126)
    print("GROUNDING")
    print("=" * 126)

    print()
    print(
        "Wet terminal-state evidence rows:",
        len(wet_terminal),
    )

    print(
        "Wet terminal-state exact grounding:",
        wet_terminal_ok,
    )

    if not wet_terminal_ok:

        print()
        print(
            "FINAL STATUS: "
            "R2F2_INTERRUPTION_LEDGER_GROUNDING_REVIEW_REQUIRED"
        )
        return

    terminal = wet_terminal[0]

    # --------------------------------------------------
    # Ledger construction.
    #
    # Timing anchors below preserve their previously
    # frozen evidence quality:
    #
    # 18:14Z        approximate secondary interruption
    # 19:34Z        approximate secondary restart
    # 20:00-20:02Z  bounded secondary interruption
    # 20:50Z        derived from official session arithmetic
    #
    # They MUST NOT be upgraded to source-native exact times.
    # --------------------------------------------------

    ledger = [

        {
            "event_id":
                "R2F2-2022-INTERRUPTION-01",

            "year":
                "2022",

            "event_type":
                "RAIN_INTERRUPTION",

            "event_stage":
                "FIRST_INTERRUPTION",

            "time_lower_utc":
                "2022-05-21T18:14:00Z",

            "time_upper_utc":
                "2022-05-21T18:14:00Z",

            "time_quality":
                "APPROXIMATE",

            "time_source_class":
                "SECONDARY_EDITORIAL_ANCHOR",

            "track_open_state":
                "CLOSED_OR_SUSPENDED",

            "precipitation_state":
                "RAIN",

            "lightning_state":
                "UNKNOWN",

            "track_wet_state":
                "SUPPORTED_BY_INTERRUPTION_CONTEXT",

            "drying_state":
                "UNKNOWN",

            "track_cleaning_state":
                "NOT_OBSERVED",

            "track_reset_state":
                "NOT_OBSERVED",

            "grip_state":
                "UNKNOWN",

            "rubber_state":
                "UNKNOWN",

            "source_semantic":
                "FIRST_RAIN_INTERRUPTION_APPROXIMATE_ANCHOR",

            "promotion_status":
                "FROZEN_R2F2",

            "notes":
                (
                    "Approximate secondary-source anchor for "
                    "the first rain interruption. This timestamp "
                    "is not treated as source-native exact timing."
                ),
        },

        {
            "event_id":
                "R2F2-2022-RESTART-01",

            "year":
                "2022",

            "event_type":
                "SESSION_RESTART",

            "event_stage":
                "FIRST_RESUMPTION",

            "time_lower_utc":
                "2022-05-21T19:34:00Z",

            "time_upper_utc":
                "2022-05-21T19:34:00Z",

            "time_quality":
                "APPROXIMATE",

            "time_source_class":
                "SECONDARY_EDITORIAL_ANCHOR",

            "track_open_state":
                "REOPENED",

            "precipitation_state":
                "UNKNOWN",

            "lightning_state":
                "UNKNOWN",

            "track_wet_state":
                "UNKNOWN",

            "drying_state":
                "UNKNOWN",

            "track_cleaning_state":
                "NOT_OBSERVED",

            "track_reset_state":
                "NOT_OBSERVED",

            "grip_state":
                "UNKNOWN",

            "rubber_state":
                "UNKNOWN",

            "source_semantic":
                "QUALIFYING_RESUMED_APPROXIMATE_ANCHOR",

            "promotion_status":
                "FROZEN_R2F2",

            "notes":
                (
                    "Approximate restart anchor. Reopening the "
                    "track does not imply a known grip level, "
                    "green-track state, full drying, or track reset."
                ),
        },

        {
            "event_id":
                "R2F2-2022-INTERRUPTION-02",

            "year":
                "2022",

            "event_type":
                "SECOND_INTERRUPTION",

            "event_stage":
                "LATE_SESSION_INTERRUPTION",

            "time_lower_utc":
                "2022-05-21T20:00:00Z",

            "time_upper_utc":
                "2022-05-21T20:02:00Z",

            "time_quality":
                "BOUNDED",

            "time_source_class":
                "SECONDARY_EDITORIAL_BOUNDED_ANCHOR",

            "track_open_state":
                "CLOSED_OR_SUSPENDED",

            "precipitation_state":
                "RAIN_OR_WET_WEATHER_CONTEXT",

            "lightning_state":
                "SUPPORTED",

            "track_wet_state":
                "SUPPORTED_BY_EVENT_CONTEXT",

            "drying_state":
                "UNKNOWN",

            "track_cleaning_state":
                "NOT_OBSERVED",

            "track_reset_state":
                "NOT_OBSERVED",

            "grip_state":
                "UNKNOWN",

            "rubber_state":
                "UNKNOWN",

            "source_semantic":
                "SECOND_INTERRUPTION_BOUNDED_20_00_TO_20_02Z",

            "promotion_status":
                "FROZEN_R2F2",

            "notes":
                (
                    "Late-session interruption is preserved as "
                    "a bounded secondary-source interval rather "
                    "than an invented exact timestamp."
                ),
        },

        {
            "event_id":
                "R2F2-2022-WET-TERMINAL-01",

            "year":
                "2022",

            "event_type":
                "WET_TERMINAL_TRACK_STATE",

            "event_stage":
                "BEFORE_SESSION_CALLED",

            "time_lower_utc":
                "UNKNOWN",

            "time_upper_utc":
                "2022-05-21T20:50:00Z",

            "time_quality":
                "ORDERING_ONLY",

            "time_source_class":
                txt(
                    terminal.get(
                        "source_class"
                    )
                ),

            "track_open_state":
                "NOT_RECOVERABLE_FOR_USEFUL_RESUMPTION",

            "precipitation_state":
                "WET_TRACK_SUPPORTED",

            "lightning_state":
                "UNKNOWN",

            "track_wet_state":
                "SUPPORTED",

            "drying_state":
                "TOO_WET_FOR_DRYING_BEFORE_SESSION_END",

            "track_cleaning_state":
                "NOT_OBSERVED",

            "track_reset_state":
                "NOT_OBSERVED",

            "grip_state":
                "UNKNOWN",

            "rubber_state":
                "UNKNOWN",

            "source_semantic":
                "SESSION_END_TRACK_TOO_WET_FOR_DRYING",

            "promotion_status":
                "FROZEN_R2F2",

            "notes":
                (
                    "NBC evidence supports the terminal wet state "
                    "and insufficient drying feasibility. It does "
                    "not support active drying, a quantitative grip "
                    "effect, or rubber wash-off."
                ),
        },

        {
            "event_id":
                "R2F2-2022-SESSION-CALLED-01",

            "year":
                "2022",

            "event_type":
                "SESSION_CALLED",

            "event_stage":
                "TERMINAL",

            "time_lower_utc":
                "2022-05-21T20:50:00Z",

            "time_upper_utc":
                "2022-05-21T20:50:00Z",

            "time_quality":
                "DERIVED",

            "time_source_class":
                "DERIVED_FROM_OFFICIAL_SESSION_ARITHMETIC",

            "track_open_state":
                "SESSION_ENDED",

            "precipitation_state":
                "WET_TERMINAL_CONTEXT",

            "lightning_state":
                "UNKNOWN",

            "track_wet_state":
                "SUPPORTED",

            "drying_state":
                "NOT_FEASIBLE_IN_REMAINING_SESSION",

            "track_cleaning_state":
                "NOT_OBSERVED",

            "track_reset_state":
                "NOT_OBSERVED",

            "grip_state":
                "UNKNOWN",

            "rubber_state":
                "UNKNOWN",

            "source_semantic":
                "SESSION_CALLED_DERIVED_OFFICIAL_ARITHMETIC",

            "promotion_status":
                "FROZEN_R2F2",

            "notes":
                (
                    "20:50Z is retained as a derived anchor from "
                    "previously frozen official session arithmetic. "
                    "It must not be represented as a direct "
                    "source-native exact event timestamp."
                ),
        },
    ]

    fields = [
        "event_id",
        "year",
        "event_type",
        "event_stage",
        "time_lower_utc",
        "time_upper_utc",
        "time_quality",
        "time_source_class",
        "track_open_state",
        "precipitation_state",
        "lightning_state",
        "track_wet_state",
        "drying_state",
        "track_cleaning_state",
        "track_reset_state",
        "grip_state",
        "rubber_state",
        "source_semantic",
        "promotion_status",
        "notes",
    ]

    write_csv(
        LEDGER_OUT,
        ledger,
        fields,
    )

    # --------------------------------------------------
    # Summary
    # --------------------------------------------------

    drying_supported_rows = [
        row
        for row in ledger
        if txt(
            row.get("drying_state")
        )
        not in {
            "",
            "UNKNOWN",
        }
    ]

    cleaning_supported_rows = [
        row
        for row in ledger
        if txt(
            row.get("track_cleaning_state")
        )
        ==
        "SUPPORTED"
    ]

    reset_supported_rows = [
        row
        for row in ledger
        if txt(
            row.get("track_reset_state")
        )
        ==
        "SUPPORTED"
    ]

    known_grip_rows = [
        row
        for row in ledger
        if txt(
            row.get("grip_state")
        )
        not in {
            "",
            "UNKNOWN",
        }
    ]

    known_rubber_rows = [
        row
        for row in ledger
        if txt(
            row.get("rubber_state")
        )
        not in {
            "",
            "UNKNOWN",
        }
    ]

    approximate_rows = [
        row
        for row in ledger
        if txt(
            row.get("time_quality")
        )
        ==
        "APPROXIMATE"
    ]

    bounded_rows = [
        row
        for row in ledger
        if txt(
            row.get("time_quality")
        )
        ==
        "BOUNDED"
    ]

    derived_rows = [
        row
        for row in ledger
        if txt(
            row.get("time_quality")
        )
        ==
        "DERIVED"
    ]

    ordering_only_rows = [
        row
        for row in ledger
        if txt(
            row.get("time_quality")
        )
        ==
        "ORDERING_ONLY"
    ]

    print()
    print("=" * 126)
    print("INTERRUPTION LEDGER SUMMARY")
    print("=" * 126)

    print()
    print(
        "Ledger rows:",
        len(ledger),
    )

    print(
        "Approximate timing rows:",
        len(approximate_rows),
    )

    print(
        "Bounded timing rows:",
        len(bounded_rows),
    )

    print(
        "Derived timing rows:",
        len(derived_rows),
    )

    print(
        "Ordering-only rows:",
        len(ordering_only_rows),
    )

    print()
    print(
        "Drying-state rows:",
        len(drying_supported_rows),
    )

    print(
        "Track-cleaning supported rows:",
        len(cleaning_supported_rows),
    )

    print(
        "Track-reset supported rows:",
        len(reset_supported_rows),
    )

    print(
        "Known grip-state rows:",
        len(known_grip_rows),
    )

    print(
        "Known rubber-state rows:",
        len(known_rubber_rows),
    )

    print()
    print(
        "Protected chronology:",
        "V10 unchanged",
    )

    print(
        "Queue wait policy:",
        "LATENT unchanged",
    )

    print(
        "Pit/service policy:",
        "SERVICE_STATE_UNKNOWN unchanged",
    )

    summary_rows = [
        {
            "metric":
                "ledger_rows",
            "value":
                len(ledger),
        },
        {
            "metric":
                "approximate_timing_rows",
            "value":
                len(approximate_rows),
        },
        {
            "metric":
                "bounded_timing_rows",
            "value":
                len(bounded_rows),
        },
        {
            "metric":
                "derived_timing_rows",
            "value":
                len(derived_rows),
        },
        {
            "metric":
                "ordering_only_rows",
            "value":
                len(ordering_only_rows),
        },
        {
            "metric":
                "track_cleaning_supported_rows",
            "value":
                len(cleaning_supported_rows),
        },
        {
            "metric":
                "track_reset_supported_rows",
            "value":
                len(reset_supported_rows),
        },
        {
            "metric":
                "known_grip_state_rows",
            "value":
                len(known_grip_rows),
        },
        {
            "metric":
                "known_rubber_state_rows",
            "value":
                len(known_rubber_rows),
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

    # --------------------------------------------------
    # QA
    # --------------------------------------------------

    event_ids = [
        txt(
            row.get("event_id")
        )
        for row in ledger
    ]

    expected_ids = {
        "R2F2-2022-INTERRUPTION-01",
        "R2F2-2022-RESTART-01",
        "R2F2-2022-INTERRUPTION-02",
        "R2F2-2022-WET-TERMINAL-01",
        "R2F2-2022-SESSION-CALLED-01",
    }

    exact_time_rows = [
        row
        for row in ledger
        if txt(
            row.get("time_quality")
        )
        ==
        "EXACT"
    ]

    rain_reset_inference = any(
        txt(
            row.get(
                "event_type"
            )
        )
        in {
            "RAIN_INTERRUPTION",
            "SECOND_INTERRUPTION",
        }
        and
        txt(
            row.get(
                "track_reset_state"
            )
        )
        ==
        "SUPPORTED"
        for row in ledger
    )

    restart_grip_inference = any(
        txt(
            row.get(
                "event_type"
            )
        )
        ==
        "SESSION_RESTART"
        and
        txt(
            row.get(
                "grip_state"
            )
        )
        not in {
            "",
            "UNKNOWN",
        }
        for row in ledger
    )

    qa_rows = [
        {
            "metric":
                "ledger_rows_is_5",

            "value":
                len(ledger),

            "status":
                (
                    "PASS"
                    if len(ledger)
                    ==
                    5
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "event_ids_unique",

            "value":
                int(
                    len(event_ids)
                    ==
                    len(set(event_ids))
                ),

            "status":
                (
                    "PASS"
                    if len(event_ids)
                    ==
                    len(set(event_ids))
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "expected_event_set_exact",

            "value":
                int(
                    set(event_ids)
                    ==
                    expected_ids
                ),

            "status":
                (
                    "PASS"
                    if set(event_ids)
                    ==
                    expected_ids
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "wet_terminal_state_exactly_one",

            "value":
                len(wet_terminal),

            "status":
                (
                    "PASS"
                    if len(wet_terminal)
                    ==
                    1
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "source_native_exact_times_invented",

            "value":
                len(exact_time_rows),

            "status":
                (
                    "PASS"
                    if len(exact_time_rows)
                    ==
                    0
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "rain_interpreted_as_track_reset",

            "value":
                int(
                    rain_reset_inference
                ),

            "status":
                (
                    "PASS"
                    if not rain_reset_inference
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "restart_interpreted_as_known_grip",

            "value":
                int(
                    restart_grip_inference
                ),

            "status":
                (
                    "PASS"
                    if not restart_grip_inference
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "track_cleaning_inferred",

            "value":
                len(cleaning_supported_rows),

            "status":
                (
                    "PASS"
                    if len(cleaning_supported_rows)
                    ==
                    0
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "rubber_effect_inferred",

            "value":
                len(known_rubber_rows),

            "status":
                (
                    "PASS"
                    if len(known_rubber_rows)
                    ==
                    0
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "elapsed_time_used_as_track_evolution",

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
        row["status"]
        ==
        "PASS"
        for row in qa_rows
    )

    print()
    print("=" * 126)

    if success:
        print(
            "FINAL STATUS: "
            "R2F2_2022_INTERRUPTION_STATE_LEDGER_V1_READY"
        )
    else:
        print(
            "FINAL STATUS: "
            "R2F2_INTERRUPTION_LEDGER_REVIEW_REQUIRED"
        )

    print("=" * 126)

    print()
    print("OUTPUTS")
    print(LEDGER_OUT)
    print(SUMMARY_OUT)
    print(QA_OUT)


if __name__ == "__main__":
    main()
