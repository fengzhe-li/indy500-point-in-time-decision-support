from pathlib import Path
import csv


PHASE = "R2C.3"

R2C1A = Path(
    "weather/output/"
    "leaderboard_rescue_2022_candidate_adjudication_v1.csv"
)

R2C2 = Path(
    "weather/output/"
    "leaderboard_rescue_2022_external_temporal_evidence_v1.csv"
)

ACTION_V8 = Path(
    "weather/output/"
    "unified_attempt_action_lane_ledger_v8.csv"
)

OUTPUT_DIR = Path("weather/output")

LEDGER_OUT = (
    OUTPUT_DIR
    / "contemporaneous_decision_state_evidence_ledger_v1.csv"
)

SUMMARY_OUT = (
    OUTPUT_DIR
    / "contemporaneous_decision_state_evidence_ledger_v1_summary.csv"
)

QA_OUT = (
    OUTPUT_DIR
    / "contemporaneous_decision_state_evidence_ledger_v1_qa.csv"
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
    print("=" * 122)
    print(
        "R2C.3 — 2022 CONTEMPORANEOUS "
        "DECISION-STATE EVIDENCE LEDGER V1"
    )
    print("=" * 122)

    required = [
        R2C1A,
        R2C2,
        ACTION_V8,
    ]

    print()
    print("INPUT CHECK")
    print("-" * 122)

    for path in required:
        print(
            f"{path}: "
            f"{'PRESENT' if path.exists() else 'MISSING'}"
        )

    if not all(path.exists() for path in required):
        print()
        print(
            "FINAL STATUS: "
            "R2C3_DECISION_STATE_LEDGER_INPUT_MISSING"
        )
        return

    r2c1a = read_csv(R2C1A)
    r2c2 = read_csv(R2C2)
    action = read_csv(ACTION_V8)

    rows = []

    # --------------------------------------------------
    # Scott McLaughlin
    # --------------------------------------------------

    mclaughlin = [
        row
        for row in r2c1a
        if (
            txt(row.get("driver_name"))
            ==
            "Scott McLaughlin"
            and
            txt(row.get("promotion_ready")).lower()
            ==
            "true"
        )
    ]

    # TXT/HTML duplicates represent the same evidence unit.
    if mclaughlin:

        source = mclaughlin[0]

        lane1_supported = any(
            txt(row.get("driver_name"))
            ==
            "Scott McLaughlin"
            and
            txt(row.get("lane"))
            ==
            "LANE_1"
            for row in action
        )

        rows.append({
            "state_id":
                "R2C3-2022-MCLAUGHLIN-01",

            "year":
                "2022",

            "driver_name":
                "Scott McLaughlin",

            "subject_attempt_id":
                "",

            "related_attempt_id":
                "",

            "state_stage":
                "PRE_ACTION_EXISTING_RESULT",

            "rank":
                "15",

            "rank_lower_bound":
                "15",

            "rank_upper_bound":
                "15",

            "top12_state":
                "OUTSIDE",

            "cutoff_rank":
                "12",

            "cutoff_speed_mph":
                "UNKNOWN",

            "action":
                (
                    "WITHDRAW_EXISTING_RESULT_AND_USE_LANE1"
                    if lane1_supported
                    else
                    "UNKNOWN"
                ),

            "lane":
                (
                    "LANE_1"
                    if lane1_supported
                    else
                    "UNKNOWN"
                ),

            "time_quality":
                "ORDERING_ONLY",

            "exact_timestamp":
                "UNKNOWN",

            "source_name":
                "The Race",

            "source_class":
                "REPUTABLE_SECONDARY_EDITORIAL",

            "source_semantic":
                "EXISTING_15TH_PLACE_RESULT_BEFORE_LANE1_ACTION",

            "promotion_status":
                "PROMOTED_R2C3",

            "notes":
                (
                    "The Race states McLaughlin gave up his "
                    "15th-place time to enter the front of the "
                    "Lane 1 queue. Rank 15 is directly bound to "
                    "the pre-action existing result. Exact "
                    "timestamp and cutoff speed remain unknown."
                ),
        })

        rows.append({
            "state_id":
                "R2C3-2022-MCLAUGHLIN-02",

            "year":
                "2022",

            "driver_name":
                "Scott McLaughlin",

            "subject_attempt_id":
                "",

            "related_attempt_id":
                "",

            "state_stage":
                "POST_RERUN_SEQUENCE",

            "rank":
                "26",

            "rank_lower_bound":
                "26",

            "rank_upper_bound":
                "26",

            "top12_state":
                "OUTSIDE",

            "cutoff_rank":
                "12",

            "cutoff_speed_mph":
                "UNKNOWN",

            "action":
                "",

            "lane":
                "UNKNOWN",

            "time_quality":
                "ORDERING_ONLY",

            "exact_timestamp":
                "UNKNOWN",

            "source_name":
                "The Race",

            "source_class":
                "REPUTABLE_SECONDARY_EDITORIAL",

            "source_semantic":
                "LATER_TEMPORAL_RANK_AFTER_TRACK_REOPENED",

            "promotion_status":
                "PROMOTED_R2C3",

            "notes":
                (
                    "The Race states McLaughlin later tumbled "
                    "to 26th after the track reopened. This is "
                    "an ordering anchor, not an exact-timestamp "
                    "live leaderboard snapshot."
                ),
        })

    # --------------------------------------------------
    # R2C2 evidence
    # --------------------------------------------------

    for row in r2c2:

        if (
            txt(row.get("promotion_ready")).lower()
            !=
            "true"
        ):
            continue

        evidence_id = txt(
            row.get("evidence_id")
        )

        driver = txt(
            row.get("driver_name")
        )

        rank_before = txt(
            row.get("rank_before")
        )

        rank_after = txt(
            row.get("rank_after")
        )

        top12_before = txt(
            row.get("top12_state_before")
        )

        top12_after = txt(
            row.get("top12_state_after")
        )

        subject_attempt_id = txt(
            row.get("subject_attempt_id")
        )

        related_attempt_id = txt(
            row.get("related_attempt_id")
        )

        source_name = txt(
            row.get("source_name")
        )

        source_class = txt(
            row.get("source_class")
        )

        semantic = txt(
            row.get("state_semantic")
        )

        cutoff_rank = txt(
            row.get("cutoff_rank")
        ) or "UNKNOWN"

        cutoff_speed = txt(
            row.get("cutoff_speed_mph")
        ) or "UNKNOWN"

        time_quality = txt(
            row.get("time_quality")
        ) or "UNKNOWN"

        exact_timestamp = txt(
            row.get("exact_timestamp")
        ) or "UNKNOWN"

        # Rossi has a before + after state.
        if evidence_id == "R2C2-ROSSI-RANK-TRANSITION":

            rows.append({
                "state_id":
                    "R2C3-2022-ROSSI-01",

                "year":
                    "2022",

                "driver_name":
                    driver,

                "subject_attempt_id":
                    related_attempt_id,

                "related_attempt_id":
                    subject_attempt_id,

                "state_stage":
                    "PRE_SECOND_RUN",

                "rank":
                    rank_before,

                "rank_lower_bound":
                    rank_before,

                "rank_upper_bound":
                    rank_before,

                "top12_state":
                    top12_before,

                "cutoff_rank":
                    cutoff_rank,

                "cutoff_speed_mph":
                    cutoff_speed,

                "action":
                    "WITHDRAW_EXISTING_RESULT_AND_USE_LANE1",

                "lane":
                    "LANE_1",

                "time_quality":
                    time_quality,

                "exact_timestamp":
                    exact_timestamp,

                "source_name":
                    source_name,

                "source_class":
                    source_class,

                "source_semantic":
                    "ROSSI_PRE_SECOND_RUN_RANK",

                "promotion_status":
                    "PROMOTED_R2C3",

                "notes":
                    (
                        "Rossi held 15th before the second-run "
                        "Lane 1 action."
                    ),
            })

            rows.append({
                "state_id":
                    "R2C3-2022-ROSSI-02",

                "year":
                    "2022",

                "driver_name":
                    driver,

                "subject_attempt_id":
                    subject_attempt_id,

                "related_attempt_id":
                    related_attempt_id,

                "state_stage":
                    "POST_SECOND_RUN",

                "rank":
                    rank_after,

                "rank_lower_bound":
                    rank_after,

                "rank_upper_bound":
                    rank_after,

                "top12_state":
                    top12_after,

                "cutoff_rank":
                    cutoff_rank,

                "cutoff_speed_mph":
                    cutoff_speed,

                "action":
                    "",

                "lane":
                    "LANE_1",

                "time_quality":
                    time_quality,

                "exact_timestamp":
                    exact_timestamp,

                "source_name":
                    source_name,

                "source_class":
                    source_class,

                "source_semantic":
                    "ROSSI_POST_SECOND_RUN_RANK",

                "promotion_status":
                    "PROMOTED_R2C3",

                "notes":
                    (
                        "Autosport supports Rossi dropping "
                        "from 15th to 21st on the second run."
                    ),
            })

        elif evidence_id == "R2C2-MALUKAS-PROVISIONAL-P12":

            rows.append({
                "state_id":
                    "R2C3-2022-MALUKAS-01",

                "year":
                    "2022",

                "driver_name":
                    driver,

                "subject_attempt_id":
                    subject_attempt_id,

                "related_attempt_id":
                    related_attempt_id,

                "state_stage":
                    "POST_REPEAT_PROVISIONAL",

                "rank":
                    "12",

                "rank_lower_bound":
                    "12",

                "rank_upper_bound":
                    "12",

                "top12_state":
                    "INSIDE",

                "cutoff_rank":
                    "12",

                "cutoff_speed_mph":
                    cutoff_speed,

                "action":
                    "REPEAT_ATTEMPT_IMPROVED",

                "lane":
                    "UNKNOWN",

                "time_quality":
                    time_quality,

                "exact_timestamp":
                    exact_timestamp,

                "source_name":
                    source_name,

                "source_class":
                    source_class,

                "source_semantic":
                    semantic,

                "promotion_status":
                    "PROMOTED_R2C3",

                "notes":
                    (
                        "Autosport explicitly places Malukas "
                        "provisionally 12th after his improvement."
                    ),
            })

        elif evidence_id == "R2C2-SATO-P12-BUMPS-MALUKAS":

            rows.append({
                "state_id":
                    "R2C3-2022-SATO-01",

                "year":
                    "2022",

                "driver_name":
                    driver,

                "subject_attempt_id":
                    subject_attempt_id,

                "related_attempt_id":
                    related_attempt_id,

                "state_stage":
                    "POST_REATTEMPT_PROVISIONAL",

                "rank":
                    "12",

                "rank_lower_bound":
                    "12",

                "rank_upper_bound":
                    "12",

                "top12_state":
                    "INSIDE",

                "cutoff_rank":
                    "12",

                "cutoff_speed_mph":
                    cutoff_speed,

                "action":
                    "REQUIRED_REATTEMPT_AFTER_INVALIDATION",

                "lane":
                    "UNKNOWN",

                "time_quality":
                    time_quality,

                "exact_timestamp":
                    exact_timestamp,

                "source_name":
                    source_name,

                "source_class":
                    source_class,

                "source_semantic":
                    semantic,

                "promotion_status":
                    "PROMOTED_R2C3",

                "notes":
                    (
                        "Autosport and The Race support Sato "
                        "moving to provisional 12th and thereby "
                        "displacing Malukas from the Top 12."
                    ),
            })

        elif evidence_id == "R2C2-MALUKAS-DISPLACED-BY-SATO":

            rows.append({
                "state_id":
                    "R2C3-2022-MALUKAS-02",

                "year":
                    "2022",

                "driver_name":
                    driver,

                "subject_attempt_id":
                    subject_attempt_id,

                "related_attempt_id":
                    related_attempt_id,

                "state_stage":
                    "POST_SATO_DISPLACEMENT",

                "rank":
                    "UNKNOWN",

                "rank_lower_bound":
                    "13",

                "rank_upper_bound":
                    "UNKNOWN",

                "top12_state":
                    "OUTSIDE",

                "cutoff_rank":
                    "12",

                "cutoff_speed_mph":
                    cutoff_speed,

                "action":
                    "",

                "lane":
                    "UNKNOWN",

                "time_quality":
                    time_quality,

                "exact_timestamp":
                    exact_timestamp,

                "source_name":
                    source_name,

                "source_class":
                    source_class,

                "source_semantic":
                    semantic,

                "promotion_status":
                    "PROMOTED_R2C3",

                "notes":
                    (
                        "Only the lower bound rank >=13 is stored. "
                        "No exact contemporaneous P13 is invented."
                    ),
            })

    fields = [
        "state_id",
        "year",
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
        "exact_timestamp",
        "source_name",
        "source_class",
        "source_semantic",
        "promotion_status",
        "notes",
    ]

    write_csv(
        LEDGER_OUT,
        rows,
        fields,
    )

    drivers = sorted({
        txt(row.get("driver_name"))
        for row in rows
    })

    exact_rank_rows = [
        row
        for row in rows
        if (
            txt(row.get("rank"))
            not in {
                "",
                "UNKNOWN",
            }
        )
    ]

    bounded_rank_rows = [
        row
        for row in rows
        if (
            txt(row.get("rank")) == "UNKNOWN"
            and
            txt(row.get("rank_lower_bound"))
            not in {
                "",
                "UNKNOWN",
            }
        )
    ]

    top12_known_rows = [
        row
        for row in rows
        if txt(row.get("top12_state"))
        in {
            "INSIDE",
            "OUTSIDE",
        }
    ]

    cutoff_speed_known = [
        row
        for row in rows
        if txt(row.get("cutoff_speed_mph"))
        not in {
            "",
            "UNKNOWN",
        }
    ]

    exact_time_rows = [
        row
        for row in rows
        if txt(row.get("exact_timestamp"))
        not in {
            "",
            "UNKNOWN",
        }
    ]

    print()
    print("=" * 122)
    print("LEDGER SUMMARY")
    print("=" * 122)

    print()
    print(
        "State rows:",
        len(rows),
    )

    print(
        "Drivers represented:",
        "|".join(drivers),
    )

    print(
        "Exact-rank state rows:",
        len(exact_rank_rows),
    )

    print(
        "Bounded-rank-only rows:",
        len(bounded_rank_rows),
    )

    print(
        "Known Top-12 state rows:",
        len(top12_known_rows),
    )

    print(
        "Known live cutoff-speed rows:",
        len(cutoff_speed_known),
    )

    print(
        "Exact timestamp rows:",
        len(exact_time_rows),
    )

    print()
    print(
        "Active chronology ledger:",
        "V10 unchanged",
    )

    print(
        "Active action/lane ledger:",
        "V8 unchanged",
    )

    summary_rows = [
        {
            "metric":
                "state_rows",
            "value":
                len(rows),
        },
        {
            "metric":
                "drivers_represented",
            "value":
                "|".join(drivers),
        },
        {
            "metric":
                "exact_rank_rows",
            "value":
                len(exact_rank_rows),
        },
        {
            "metric":
                "bounded_rank_only_rows",
            "value":
                len(bounded_rank_rows),
        },
        {
            "metric":
                "known_top12_state_rows",
            "value":
                len(top12_known_rows),
        },
        {
            "metric":
                "known_cutoff_speed_rows",
            "value":
                len(cutoff_speed_known),
        },
        {
            "metric":
                "exact_timestamp_rows",
            "value":
                len(exact_time_rows),
        },
        {
            "metric":
                "chronology_ledger",
            "value":
                "V10_UNCHANGED",
        },
        {
            "metric":
                "action_lane_ledger",
            "value":
                "V8_UNCHANGED",
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

    state_ids = [
        txt(row.get("state_id"))
        for row in rows
    ]

    unique_ids = (
        len(state_ids)
        ==
        len(set(state_ids))
    )

    required_states = {
        "R2C3-2022-MCLAUGHLIN-01",
        "R2C3-2022-MCLAUGHLIN-02",
        "R2C3-2022-ROSSI-01",
        "R2C3-2022-ROSSI-02",
        "R2C3-2022-MALUKAS-01",
        "R2C3-2022-MALUKAS-02",
        "R2C3-2022-SATO-01",
    }

    actual_states = set(state_ids)

    required_present = (
        required_states
        ==
        actual_states
    )

    qa_rows = [
        {
            "metric":
                "state_row_count_is_7",

            "value":
                len(rows),

            "status":
                "PASS"
                if len(rows) == 7
                else "FAIL",
        },

        {
            "metric":
                "state_ids_unique",

            "value":
                int(unique_ids),

            "status":
                "PASS"
                if unique_ids
                else "FAIL",
        },

        {
            "metric":
                "expected_state_set_exact",

            "value":
                int(required_present),

            "status":
                "PASS"
                if required_present
                else "FAIL",
        },

        {
            "metric":
                "driver_count_is_4",

            "value":
                len(drivers),

            "status":
                "PASS"
                if len(drivers) == 4
                else "FAIL",
        },

        {
            "metric":
                "live_cutoff_speed_invented",

            "value":
                len(cutoff_speed_known),

            "status":
                "PASS"
                if len(cutoff_speed_known) == 0
                else "FAIL",
        },

        {
            "metric":
                "exact_timestamp_invented",

            "value":
                len(exact_time_rows),

            "status":
                "PASS"
                if len(exact_time_rows) == 0
                else "FAIL",
        },

        {
            "metric":
                "chronology_mutation",

            "value":
                0,

            "status":
                "PASS",
        },

        {
            "metric":
                "action_lane_mutation",

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
    print("=" * 122)

    if success:
        print(
            "FINAL STATUS: "
            "R2C3_CONTEMPORANEOUS_DECISION_STATE_LEDGER_V1_READY"
        )
    else:
        print(
            "FINAL STATUS: "
            "R2C3_DECISION_STATE_LEDGER_REVIEW_REQUIRED"
        )

    print("=" * 122)

    print()
    print("OUTPUTS")
    print(LEDGER_OUT)
    print(SUMMARY_OUT)
    print(QA_OUT)


if __name__ == "__main__":
    main()
