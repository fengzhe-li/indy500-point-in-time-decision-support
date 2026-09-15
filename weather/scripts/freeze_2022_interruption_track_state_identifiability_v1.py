from pathlib import Path
import csv
import json


PHASE = "R2F.3"

LEDGER_V1 = Path(
    "weather/output/"
    "interruption_state_evidence_ledger_2022_v1.csv"
)

SUMMARY_V1 = Path(
    "weather/output/"
    "interruption_state_evidence_ledger_2022_v1_summary.csv"
)

R2F1A = Path(
    "weather/output/"
    "interruption_rescue_2022_candidate_adjudication_v1.csv"
)

OUTPUT_DIR = Path("weather/output")

FREEZE_OUT = (
    OUTPUT_DIR
    / "interruption_track_state_identifiability_2022_v1.csv"
)

MECHANISM_OUT = (
    OUTPUT_DIR
    / "rubber_grip_adjacent_mechanism_evidence_2022_v1.csv"
)

JSON_OUT = (
    OUTPUT_DIR
    / "interruption_track_state_identifiability_2022_v1.json"
)

QA_OUT = (
    OUTPUT_DIR
    / "interruption_track_state_identifiability_2022_v1_qa.csv"
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
    print("=" * 124)
    print(
        "R2F.3 — 2022 INTERRUPTION / DRYING / RESET "
        "IDENTIFIABILITY FREEZE"
    )
    print("=" * 124)

    required = [
        LEDGER_V1,
        SUMMARY_V1,
        R2F1A,
    ]

    print()
    print("INPUT CHECK")
    print("-" * 124)

    for path in required:
        print(
            f"{path}: "
            f"{'PRESENT' if path.exists() else 'MISSING'}"
        )

    if not all(path.exists() for path in required):
        print()
        print(
            "FINAL STATUS: "
            "R2F3_TRACK_STATE_FREEZE_INPUT_MISSING"
        )
        return

    ledger = read_csv(LEDGER_V1)
    summary = read_csv(SUMMARY_V1)
    adjudication = read_csv(R2F1A)

    summary_map = {
        txt(row.get("metric")):
        txt(row.get("value"))
        for row in summary
    }

    wet_terminal_rows = [
        row
        for row in adjudication
        if (
            txt(row.get("event_semantic"))
            ==
            "SESSION_END_TRACK_TOO_WET_FOR_DRYING"
            and
            txt(row.get("promotion_ready")).lower()
            ==
            "true"
        )
    ]

    cleaning_supported = [
        row
        for row in ledger
        if txt(
            row.get("track_cleaning_state")
        )
        ==
        "SUPPORTED"
    ]

    reset_supported = [
        row
        for row in ledger
        if txt(
            row.get("track_reset_state")
        )
        ==
        "SUPPORTED"
    ]

    grip_known = [
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

    rubber_known = [
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

    print()
    print("=" * 124)
    print("EVIDENCE ASSESSMENT")
    print("=" * 124)

    print()
    print(
        "Interruption ledger rows:",
        len(ledger),
    )

    print(
        "Wet terminal-state rows:",
        len(wet_terminal_rows),
    )

    print(
        "Track-cleaning supported rows:",
        len(cleaning_supported),
    )

    print(
        "Track-reset supported rows:",
        len(reset_supported),
    )

    print(
        "Known post-event grip-state rows:",
        len(grip_known),
    )

    print(
        "Known Day1 rubber-state rows:",
        len(rubber_known),
    )

    # --------------------------------------------------
    # External R2F.3 findings.
    #
    # These are frozen manually as adjudicated evidence:
    #
    # 1. INDYCAR Day 1 recap:
    #    first rain arrived, dropping grip and speeds.
    #
    # 2. The Race:
    #    track reopened and cars resumed attempts,
    #    but no direct drying/cleaning/reset/grip state.
    #
    # 3. RACER Fast Friday, May 20:
    #    overnight rain washed away rubber.
    #    This is adjacent mechanism evidence ONLY,
    #    not Day 1 interruption-state evidence.
    # --------------------------------------------------

    day1_rain_grip_supported = True

    post_restart_grip_identifiable = False

    day1_cleaning_identifiable = (
        len(cleaning_supported)
        >
        0
    )

    day1_reset_identifiable = (
        len(reset_supported)
        >
        0
    )

    day1_rubber_washoff_identifiable = (
        len(rubber_known)
        >
        0
    )

    drying_trajectory_identifiable = False

    wet_terminal_supported = (
        len(wet_terminal_rows)
        ==
        1
    )

    print()
    print("=" * 124)
    print("EXTERNAL NARROW-SEARCH ADJUDICATION")
    print("=" * 124)

    print()
    print(
        "Day1 rain-arrival grip drop:",
        "SUPPORTED",
    )

    print(
        "Day1 rain-arrival speed drop:",
        "SUPPORTED",
    )

    print()
    print(
        "Post-restart grip trajectory:",
        "UNKNOWN",
    )

    print(
        "Post-restart drying trajectory:",
        "UNKNOWN",
    )

    print(
        "Day1 track cleaning:",
        "NOT_OBSERVED",
    )

    print(
        "Day1 track reset:",
        "NOT_OBSERVED",
    )

    print(
        "Day1 rubber wash-off:",
        "NOT_IDENTIFIABLE",
    )

    print()
    print(
        "Fast Friday overnight-rain rubber wash-off:",
        "SUPPORTED_ADJACENT_MECHANISM_ONLY",
    )

    print()
    print(
        "IMPORTANT:"
    )

    print(
        "  Fast Friday rubber wash-off evidence "
        "must NOT be promoted to the May 21 "
        "qualifying interruption."
    )

    print(
        "  Rain-related grip loss before/during the "
        "interruption does NOT determine the "
        "post-restart grip state."
    )

    # --------------------------------------------------
    # Main freeze
    # --------------------------------------------------

    freeze_rows = [
        {
            "phase":
                PHASE,

            "year":
                "2022",

            "interruption_chronology_support":
                "PARTIAL",

            "wet_terminal_state_support":
                (
                    "SUPPORTED"
                    if wet_terminal_supported
                    else
                    "NOT_READY"
                ),

            "day1_rain_arrival_grip_effect":
                "LOWER_GRIP_SUPPORTED",

            "day1_rain_arrival_speed_effect":
                "LOWER_SPEEDS_SUPPORTED",

            "post_restart_grip_state":
                "UNKNOWN",

            "drying_trajectory":
                "UNKNOWN",

            "track_cleaning_support":
                (
                    "SUPPORTED"
                    if day1_cleaning_identifiable
                    else
                    "NOT_OBSERVED"
                ),

            "track_reset_support":
                (
                    "SUPPORTED"
                    if day1_reset_identifiable
                    else
                    "NOT_OBSERVED"
                ),

            "day1_rubber_washoff_support":
                (
                    "SUPPORTED"
                    if day1_rubber_washoff_identifiable
                    else
                    "NOT_IDENTIFIABLE"
                ),

            "green_track_support":
                "NOT_OBSERVED",

            "post_restart_quantitative_grip_ready":
                "False",

            "rubber_reset_feature_ready":
                "False",

            "elapsed_time_as_track_evolution":
                "PROHIBITED",

            "rain_implies_full_reset":
                "False",

            "reopen_implies_known_grip":
                "False",

            "downstream_track_state_policy":
                (
                    "USE_OBSERVED_WEATHER_AND_TRACK_TEMP;"
                    "KEEP_POST_INTERRUPTION_GRIP_AND_RUBBER_UNKNOWN"
                ),

            "notes":
                (
                    "Day 1 evidence supports rain-related loss "
                    "of grip and speed and a terminal wet state, "
                    "but does not identify the post-restart grip "
                    "trajectory, track cleaning, track reset, or "
                    "Day 1 rubber wash-off. Adjacent Fast Friday "
                    "evidence shows that overnight rain can wash "
                    "rubber from IMS, but that mechanism must not "
                    "be promoted to the May 21 interruption."
                ),
        }
    ]

    write_csv(
        FREEZE_OUT,
        freeze_rows,
        list(
            freeze_rows[0].keys()
        ),
    )

    # --------------------------------------------------
    # Adjacent mechanism evidence.
    # Kept separate from event-state ledger.
    # --------------------------------------------------

    mechanism_rows = [
        {
            "mechanism_evidence_id":
                "R2F3-2022-IMS-RAIN-RUBBER-MECHANISM-01",

            "year":
                "2022",

            "date":
                "2022-05-20",

            "session_context":
                "FAST_FRIDAY_PRACTICE",

            "source_name":
                "RACER",

            "source_class":
                "REPUTABLE_SECONDARY_EDITORIAL",

            "source_title":
                (
                    "Daly amazed after tailwinds deliver "
                    "insane speeds at IMS"
                ),

            "source_url":
                (
                    "https://racer.com/2022/05/20/"
                    "daly-amazed-after-tailwinds-deliver-"
                    "insane-speeds-at-ims/"
                ),

            "supported_mechanism":
                "OVERNIGHT_RAIN_CAN_WASH_AWAY_RUBBER_AT_IMS",

            "driver_observation":
                (
                    "Conor Daly described reduced grip after "
                    "overnight rain washed away rubber."
                ),

            "event_specific_to_day1_qualifying":
                "False",

            "may21_interruption_promotion_allowed":
                "False",

            "use_policy":
                "ADJACENT_MECHANISM_EVIDENCE_ONLY",

            "notes":
                (
                    "Useful for the later rubbering/grip "
                    "mechanism rescue. It cannot establish "
                    "that the May 21 qualifying rain "
                    "interruption washed away rubber."
                ),
        }
    ]

    write_csv(
        MECHANISM_OUT,
        mechanism_rows,
        list(
            mechanism_rows[0].keys()
        ),
    )

    # --------------------------------------------------
    # JSON freeze
    # --------------------------------------------------

    payload = {
        "phase":
            PHASE,

        "year":
            2022,

        "interruption_chronology_support":
            "PARTIAL",

        "wet_terminal_state_support":
            (
                "SUPPORTED"
                if wet_terminal_supported
                else
                "NOT_READY"
            ),

        "day1_rain_arrival_grip_effect":
            "LOWER_GRIP_SUPPORTED",

        "day1_rain_arrival_speed_effect":
            "LOWER_SPEEDS_SUPPORTED",

        "post_restart_grip_state":
            "UNKNOWN",

        "drying_trajectory":
            "UNKNOWN",

        "track_cleaning_support":
            "NOT_OBSERVED",

        "track_reset_support":
            "NOT_OBSERVED",

        "day1_rubber_washoff_support":
            "NOT_IDENTIFIABLE",

        "green_track_support":
            "NOT_OBSERVED",

        "adjacent_mechanism_evidence": {
            "date":
                "2022-05-20",

            "context":
                "FAST_FRIDAY_PRACTICE",

            "mechanism":
                "OVERNIGHT_RAIN_CAN_WASH_AWAY_RUBBER_AT_IMS",

            "may21_event_promotion_allowed":
                False,
        },

        "elapsed_time_as_track_evolution":
            "PROHIBITED",

        "rain_implies_full_reset":
            False,

        "reopen_implies_known_grip":
            False,
    }

    JSON_OUT.write_text(
        json.dumps(
            payload,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    # --------------------------------------------------
    # QA
    # --------------------------------------------------

    qa_rows = [
        {
            "metric":
                "interruption_ledger_rows_is_5",

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
                "wet_terminal_state_exactly_one",

            "value":
                len(wet_terminal_rows),

            "status":
                (
                    "PASS"
                    if len(wet_terminal_rows)
                    ==
                    1
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "day1_cleaning_promoted",

            "value":
                len(cleaning_supported),

            "status":
                (
                    "PASS"
                    if len(cleaning_supported)
                    ==
                    0
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "day1_reset_promoted",

            "value":
                len(reset_supported),

            "status":
                (
                    "PASS"
                    if len(reset_supported)
                    ==
                    0
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "day1_rubber_washoff_promoted",

            "value":
                len(rubber_known),

            "status":
                (
                    "PASS"
                    if len(rubber_known)
                    ==
                    0
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "post_restart_grip_inferred",

            "value":
                int(
                    post_restart_grip_identifiable
                ),

            "status":
                (
                    "PASS"
                    if not post_restart_grip_identifiable
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "drying_trajectory_inferred",

            "value":
                int(
                    drying_trajectory_identifiable
                ),

            "status":
                (
                    "PASS"
                    if not drying_trajectory_identifiable
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "fast_friday_mechanism_promoted_to_day1",

            "value":
                0,

            "status":
                "PASS",
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
    print("=" * 124)
    print("FROZEN POLICY")
    print("=" * 124)

    print()
    print(
        "Interruption chronology:",
        "PARTIALLY_SUPPORTED",
    )

    print(
        "Wet terminal state:",
        "SUPPORTED",
    )

    print(
        "Day1 rain -> lower grip/speeds:",
        "SUPPORTED",
    )

    print(
        "Post-restart grip:",
        "UNKNOWN",
    )

    print(
        "Drying trajectory:",
        "UNKNOWN",
    )

    print(
        "Track cleaning:",
        "NOT_OBSERVED",
    )

    print(
        "Track reset:",
        "NOT_OBSERVED",
    )

    print(
        "Day1 rubber wash-off:",
        "NOT_IDENTIFIABLE",
    )

    print()
    print(
        "Fast Friday rain/rubber mechanism:",
        "ADJACENT_MECHANISM_ONLY",
    )

    print()
    print("=" * 124)

    if success:
        print(
            "FINAL STATUS: "
            "R2F3_2022_INTERRUPTION_TRACK_STATE_FROZEN_"
            "POST_RESTART_GRIP_RUBBER_UNKNOWN"
        )
    else:
        print(
            "FINAL STATUS: "
            "R2F3_INTERRUPTION_TRACK_STATE_FREEZE_REVIEW_REQUIRED"
        )

    print("=" * 124)

    print()
    print("OUTPUTS")
    print(FREEZE_OUT)
    print(MECHANISM_OUT)
    print(JSON_OUT)
    print(QA_OUT)


if __name__ == "__main__":
    main()
