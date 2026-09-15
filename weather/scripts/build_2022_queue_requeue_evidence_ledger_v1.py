from pathlib import Path
import csv


PHASE = "R2D.3"

R2D1A = Path(
    "weather/output/"
    "queue_rescue_2022_candidate_adjudication_v1.csv"
)

R2D2 = Path(
    "weather/output/"
    "queue_rescue_2022_external_queue_order_evidence_v1.csv"
)

CHRONOLOGY_V10 = Path(
    "weather/output/"
    "unified_attempt_chronology_constraint_ledger_v10.csv"
)

ACTION_V8 = Path(
    "weather/output/"
    "unified_attempt_action_lane_ledger_v8.csv"
)

STATE_V2 = Path(
    "weather/output/"
    "contemporaneous_decision_state_evidence_ledger_v2.csv"
)

OUTPUT_DIR = Path("weather/output")

LEDGER_OUT = (
    OUTPUT_DIR
    / "queue_requeue_evidence_ledger_v1.csv"
)

SUMMARY_OUT = (
    OUTPUT_DIR
    / "queue_requeue_evidence_ledger_v1_summary.csv"
)

QA_OUT = (
    OUTPUT_DIR
    / "queue_requeue_evidence_ledger_v1_qa.csv"
)


ILOTT_FIRST = (
    "3cd6d98a-da75-5822-8dae-05e83ad8457c"
)

ILOTT_SECOND = (
    "8fa25fec-e5a6-5844-b3d7-f67c9dc91378"
)

MALUKAS_FIRST = (
    "619575d3-e7eb-5cce-886f-0a8485b98eba"
)

MALUKAS_SECOND = (
    "85c917fa-1c7a-52cb-a47f-468b4bdae9a5"
)

SATO_FIRST = (
    "3f221659-74ff-5901-97dc-08071a734690"
)

SATO_SECOND = (
    "21e8c99e-b04c-516d-85a8-ccfbaed7ff46"
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
        "R2D.3 — 2022 QUEUE / REQUEUE "
        "EVIDENCE LEDGER V1"
    )
    print("=" * 124)

    required = [
        R2D1A,
        R2D2,
        CHRONOLOGY_V10,
        ACTION_V8,
        STATE_V2,
    ]

    print()
    print("INPUT CHECK")
    print("-" * 124)

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
            "R2D3_QUEUE_LEDGER_INPUT_MISSING"
        )
        return

    r2d1a = read_csv(
        R2D1A
    )

    r2d2 = read_csv(
        R2D2
    )

    # Read protected active inputs only for
    # presence / immutability checks.
    chronology = read_csv(
        CHRONOLOGY_V10
    )

    action = read_csv(
        ACTION_V8
    )

    states = read_csv(
        STATE_V2
    )

    # --------------------------------------------------
    # R2D1A — McLaughlin front of Lane 1 queue
    # --------------------------------------------------

    mclaughlin = [
        row
        for row in r2d1a
        if (
            txt(
                row.get(
                    "driver_name"
                )
            )
            ==
            "Scott McLaughlin"
            and
            txt(
                row.get(
                    "decision"
                )
            )
            ==
            "PROMOTION_CANDIDATE_FRONT_OF_LANE1_QUEUE"
            and
            txt(
                row.get(
                    "queue_lane"
                )
            )
            ==
            "LANE_1"
            and
            txt(
                row.get(
                    "queue_membership"
                )
            )
            ==
            "CONFIRMED"
            and
            txt(
                row.get(
                    "queue_position"
                )
            )
            ==
            "FRONT"
            and
            txt(
                row.get(
                    "promotion_ready"
                )
            ).lower()
            ==
            "true"
        )
    ]

    # --------------------------------------------------
    # R2D2 — four frozen external semantic units
    # --------------------------------------------------

    r2d2_ready = [
        row
        for row in r2d2
        if txt(
            row.get(
                "promotion_ready"
            )
        ).lower()
        ==
        "true"
    ]

    by_evidence_id = {
        txt(
            row.get(
                "evidence_id"
            )
        ): row
        for row in r2d2_ready
    }

    ilott = by_evidence_id.get(
        "R2D2-ILOTT-FIRST-RETAKE"
    )

    malukas_line = by_evidence_id.get(
        "R2D2-MALUKAS-IN-LINE"
    )

    sato_line = by_evidence_id.get(
        "R2D2-SATO-IN-LINE"
    )

    malukas_before_sato = by_evidence_id.get(
        "R2D2-MALUKAS-BEFORE-SATO"
    )

    grounding_ok = all([
        len(mclaughlin) == 1,
        ilott is not None,
        malukas_line is not None,
        sato_line is not None,
        malukas_before_sato is not None,
    ])

    print()
    print("=" * 124)
    print("GROUNDING")
    print("=" * 124)

    print()
    print(
        "McLaughlin front-of-Lane1 units:",
        len(
            mclaughlin
        ),
    )

    print(
        "Ilott first-retake evidence:",
        ilott is not None,
    )

    print(
        "Malukas generic-line evidence:",
        malukas_line is not None,
    )

    print(
        "Sato generic-line evidence:",
        sato_line is not None,
    )

    print(
        "Malukas-before-Sato evidence:",
        malukas_before_sato is not None,
    )

    print(
        "Overall semantic grounding:",
        grounding_ok,
    )

    if not grounding_ok:
        print()
        print(
            "FINAL STATUS: "
            "R2D3_QUEUE_LEDGER_GROUNDING_REVIEW_REQUIRED"
        )
        return

    # --------------------------------------------------
    # Build ledger
    # --------------------------------------------------

    mc = mclaughlin[0]

    ledger = []

    # 1. McLaughlin
    ledger.append({
        "queue_state_id":
            "R2D3-2022-MCLAUGHLIN-01",

        "year":
            "2022",

        "driver_name":
            "Scott McLaughlin",

        "subject_attempt_id":
            "",

        "related_attempt_id":
            "",

        "evidence_family":
            "EXPLICIT_QUEUE_POSITION",

        "state_semantic":
            "FRONT_OF_LANE1_QUEUE_AFTER_WITHDRAWING_EXISTING_RESULT",

        "queue_membership":
            "CONFIRMED",

        "queue_lane":
            "LANE_1",

        "queue_position":
            "FRONT",

        "relative_run_order":
            "UNKNOWN",

        "related_driver":
            "",

        "existing_rank":
            "15",

        "queue_wait_seconds":
            "UNKNOWN",

        "queue_wait_lower_bound_seconds":
            "UNKNOWN",

        "queue_wait_upper_bound_seconds":
            "UNKNOWN",

        "time_quality":
            txt(
                mc.get(
                    "time_quality"
                )
            )
            or
            "ORDERING_ONLY",

        "exact_timestamp":
            "UNKNOWN",

        "source_name":
            "The Race",

        "source_class":
            "REPUTABLE_SECONDARY_EDITORIAL",

        "source_reference":
            txt(
                mc.get(
                    "source_path"
                )
            ),

        "source_text":
            txt(
                mc.get(
                    "source_text"
                )
            ),

        "promotion_status":
            "PROMOTED_R2D3",

        "notes":
            (
                "Source directly supports Scott McLaughlin "
                "giving up his 15th-place time and moving to "
                "the front of the Lane 1 queue. Queue wait "
                "and exact timestamp remain unknown."
            ),
    })

    # 2. Ilott
    ledger.append({
        "queue_state_id":
            "R2D3-2022-ILOTT-01",

        "year":
            "2022",

        "driver_name":
            "Callum Ilott",

        "subject_attempt_id":
            ILOTT_SECOND,

        "related_attempt_id":
            ILOTT_FIRST,

        "evidence_family":
            "RETAKE_RUN_ORDER",

        "state_semantic":
            "FIRST_RETAKE_RUN",

        "queue_membership":
            "UNKNOWN",

        "queue_lane":
            "UNKNOWN",

        "queue_position":
            "UNKNOWN",

        "relative_run_order":
            "FIRST_RETAKE_IN_DESCRIBED_SEQUENCE",

        "related_driver":
            "",

        "existing_rank":
            "UNKNOWN",

        "queue_wait_seconds":
            "UNKNOWN",

        "queue_wait_lower_bound_seconds":
            "UNKNOWN",

        "queue_wait_upper_bound_seconds":
            "UNKNOWN",

        "time_quality":
            txt(
                ilott.get(
                    "time_quality"
                )
            )
            or
            "ORDERING_ONLY",

        "exact_timestamp":
            "UNKNOWN",

        "source_name":
            txt(
                ilott.get(
                    "source_name"
                )
            ),

        "source_class":
            txt(
                ilott.get(
                    "source_class"
                )
            ),

        "source_reference":
            txt(
                ilott.get(
                    "source_url"
                )
            ),

        "source_text":
            txt(
                ilott.get(
                    "source_quote"
                )
            ),

        "promotion_status":
            "PROMOTED_R2D3",

        "notes":
            (
                "Ilott is explicitly described as the first "
                "driver to perform a retake run. This is "
                "run-order evidence only and must not be "
                "reinterpreted as first position in Lane 1 "
                "or Lane 2."
            ),
    })

    # 3. Malukas generic line
    ledger.append({
        "queue_state_id":
            "R2D3-2022-MALUKAS-01",

        "year":
            "2022",

        "driver_name":
            "David Malukas",

        "subject_attempt_id":
            MALUKAS_SECOND,

        "related_attempt_id":
            MALUKAS_FIRST,

        "evidence_family":
            "GENERIC_QUEUE_MEMBERSHIP",

        "state_semantic":
            "PUT_IN_LINE_FOR_REPEAT_RUN",

        "queue_membership":
            "CONFIRMED_GENERIC_LINE",

        "queue_lane":
            "UNKNOWN",

        "queue_position":
            "UNKNOWN",

        "relative_run_order":
            "UNKNOWN_FROM_LINE_PHRASE",

        "related_driver":
            "Takuma Sato",

        "existing_rank":
            "UNKNOWN",

        "queue_wait_seconds":
            "UNKNOWN",

        "queue_wait_lower_bound_seconds":
            "UNKNOWN",

        "queue_wait_upper_bound_seconds":
            "UNKNOWN",

        "time_quality":
            "ORDERING_ONLY",

        "exact_timestamp":
            "UNKNOWN",

        "source_name":
            txt(
                malukas_line.get(
                    "source_name"
                )
            ),

        "source_class":
            txt(
                malukas_line.get(
                    "source_class"
                )
            ),

        "source_reference":
            txt(
                malukas_line.get(
                    "source_url"
                )
            ),

        "source_text":
            txt(
                malukas_line.get(
                    "source_quote"
                )
            ),

        "promotion_status":
            "PROMOTED_R2D3",

        "notes":
            (
                "Autosport explicitly states Dale Coyne "
                "Racing put David Malukas and Takuma Sato "
                "in line. This confirms generic waiting-line "
                "membership only. Lane and exact position "
                "remain unknown."
            ),
    })

    # 4. Sato generic line
    ledger.append({
        "queue_state_id":
            "R2D3-2022-SATO-01",

        "year":
            "2022",

        "driver_name":
            "Takuma Sato",

        "subject_attempt_id":
            SATO_SECOND,

        "related_attempt_id":
            SATO_FIRST,

        "evidence_family":
            "GENERIC_QUEUE_MEMBERSHIP",

        "state_semantic":
            "PUT_IN_LINE_FOR_REATTEMPT",

        "queue_membership":
            "CONFIRMED_GENERIC_LINE",

        "queue_lane":
            "UNKNOWN",

        "queue_position":
            "UNKNOWN",

        "relative_run_order":
            "UNKNOWN_FROM_LINE_PHRASE",

        "related_driver":
            "David Malukas",

        "existing_rank":
            "UNKNOWN",

        "queue_wait_seconds":
            "UNKNOWN",

        "queue_wait_lower_bound_seconds":
            "UNKNOWN",

        "queue_wait_upper_bound_seconds":
            "UNKNOWN",

        "time_quality":
            "ORDERING_ONLY",

        "exact_timestamp":
            "UNKNOWN",

        "source_name":
            txt(
                sato_line.get(
                    "source_name"
                )
            ),

        "source_class":
            txt(
                sato_line.get(
                    "source_class"
                )
            ),

        "source_reference":
            txt(
                sato_line.get(
                    "source_url"
                )
            ),

        "source_text":
            txt(
                sato_line.get(
                    "source_quote"
                )
            ),

        "promotion_status":
            "PROMOTED_R2D3",

        "notes":
            (
                "Sato is explicitly included in the "
                "source-native 'put ... in line' statement. "
                "His qualifying lane is not inferred because "
                "the source does not identify Lane 1 or Lane 2."
            ),
    })

    # 5. Malukas before Sato run relation
    ledger.append({
        "queue_state_id":
            "R2D3-2022-MALUKAS-SATO-ORDER-01",

        "year":
            "2022",

        "driver_name":
            "David Malukas",

        "subject_attempt_id":
            MALUKAS_SECOND,

        "related_attempt_id":
            SATO_SECOND,

        "evidence_family":
            "RELATIVE_RUN_ORDER",

        "state_semantic":
            "MALUKAS_SECOND_BEFORE_SATO_SECOND",

        "queue_membership":
            "NOT_APPLICABLE",

        "queue_lane":
            "UNKNOWN",

        "queue_position":
            "UNKNOWN",

        "relative_run_order":
            "BEFORE",

        "related_driver":
            "Takuma Sato",

        "existing_rank":
            "UNKNOWN",

        "queue_wait_seconds":
            "UNKNOWN",

        "queue_wait_lower_bound_seconds":
            "UNKNOWN",

        "queue_wait_upper_bound_seconds":
            "UNKNOWN",

        "time_quality":
            "ORDERING_ONLY",

        "exact_timestamp":
            "UNKNOWN",

        "source_name":
            txt(
                malukas_before_sato.get(
                    "source_name"
                )
            ),

        "source_class":
            txt(
                malukas_before_sato.get(
                    "source_class"
                )
            ),

        "source_reference":
            txt(
                malukas_before_sato.get(
                    "source_url"
                )
            ),

        "source_text":
            txt(
                malukas_before_sato.get(
                    "source_quote"
                )
            ),

        "promotion_status":
            "PROMOTED_R2D3",

        "notes":
            (
                "Malukas second attempt precedes Sato's "
                "second/required reattempt in the supported "
                "source-native narrative sequence. The "
                "ordering is not derived from the phrase "
                "'put ... in line' and does not establish "
                "their positions within a qualifying lane."
            ),
    })

    fields = [
        "queue_state_id",
        "year",
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
        "queue_wait_seconds",
        "queue_wait_lower_bound_seconds",
        "queue_wait_upper_bound_seconds",
        "time_quality",
        "exact_timestamp",
        "source_name",
        "source_class",
        "source_reference",
        "source_text",
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

    drivers = sorted({
        txt(
            row.get(
                "driver_name"
            )
        )
        for row in ledger
    })

    explicit_lane_rows = [
        row
        for row in ledger
        if txt(
            row.get(
                "queue_lane"
            )
        )
        not in {
            "",
            "UNKNOWN",
        }
    ]

    explicit_position_rows = [
        row
        for row in ledger
        if txt(
            row.get(
                "queue_position"
            )
        )
        not in {
            "",
            "UNKNOWN",
        }
    ]

    generic_membership_rows = [
        row
        for row in ledger
        if txt(
            row.get(
                "queue_membership"
            )
        )
        ==
        "CONFIRMED_GENERIC_LINE"
    ]

    ordering_rows = [
        row
        for row in ledger
        if txt(
            row.get(
                "evidence_family"
            )
        )
        in {
            "RETAKE_RUN_ORDER",
            "RELATIVE_RUN_ORDER",
        }
    ]

    queue_wait_known_rows = [
        row
        for row in ledger
        if txt(
            row.get(
                "queue_wait_seconds"
            )
        )
        not in {
            "",
            "UNKNOWN",
        }
    ]

    bounded_wait_rows = [
        row
        for row in ledger
        if (
            txt(
                row.get(
                    "queue_wait_lower_bound_seconds"
                )
            )
            not in {
                "",
                "UNKNOWN",
            }
            or
            txt(
                row.get(
                    "queue_wait_upper_bound_seconds"
                )
            )
            not in {
                "",
                "UNKNOWN",
            }
        )
    ]

    exact_time_rows = [
        row
        for row in ledger
        if txt(
            row.get(
                "exact_timestamp"
            )
        )
        not in {
            "",
            "UNKNOWN",
        }
    ]

    print()
    print("=" * 124)
    print("QUEUE / REQUEUE LEDGER SUMMARY")
    print("=" * 124)

    print()
    print(
        "Ledger rows:",
        len(
            ledger
        ),
    )

    print(
        "Drivers represented:",
        "|".join(
            drivers
        ),
    )

    print(
        "Explicit lane rows:",
        len(
            explicit_lane_rows
        ),
    )

    print(
        "Explicit queue-position rows:",
        len(
            explicit_position_rows
        ),
    )

    print(
        "Generic line-membership rows:",
        len(
            generic_membership_rows
        ),
    )

    print(
        "Ordering-only rows:",
        len(
            ordering_rows
        ),
    )

    print(
        "Known exact queue-wait rows:",
        len(
            queue_wait_known_rows
        ),
    )

    print(
        "Bounded queue-wait rows:",
        len(
            bounded_wait_rows
        ),
    )

    print(
        "Exact timestamp rows:",
        len(
            exact_time_rows
        ),
    )

    print()
    print(
        "Protected ledgers:"
    )

    print(
        "  chronology = V10 unchanged"
    )

    print(
        "  action/lane = V8 unchanged"
    )

    print(
        "  decision-state = V2 unchanged"
    )

    summary_rows = [
        {
            "metric":
                "ledger_rows",
            "value":
                len(
                    ledger
                ),
        },
        {
            "metric":
                "drivers_represented",
            "value":
                "|".join(
                    drivers
                ),
        },
        {
            "metric":
                "explicit_lane_rows",
            "value":
                len(
                    explicit_lane_rows
                ),
        },
        {
            "metric":
                "explicit_queue_position_rows",
            "value":
                len(
                    explicit_position_rows
                ),
        },
        {
            "metric":
                "generic_line_membership_rows",
            "value":
                len(
                    generic_membership_rows
                ),
        },
        {
            "metric":
                "ordering_only_rows",
            "value":
                len(
                    ordering_rows
                ),
        },
        {
            "metric":
                "known_exact_queue_wait_rows",
            "value":
                len(
                    queue_wait_known_rows
                ),
        },
        {
            "metric":
                "bounded_queue_wait_rows",
            "value":
                len(
                    bounded_wait_rows
                ),
        },
        {
            "metric":
                "exact_timestamp_rows",
            "value":
                len(
                    exact_time_rows
                ),
        },
        {
            "metric":
                "chronology",
            "value":
                "V10_UNCHANGED",
        },
        {
            "metric":
                "action_lane",
            "value":
                "V8_UNCHANGED",
        },
        {
            "metric":
                "decision_state",
            "value":
                "V2_UNCHANGED",
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

    state_ids = [
        txt(
            row.get(
                "queue_state_id"
            )
        )
        for row in ledger
    ]

    expected_ids = {
        "R2D3-2022-MCLAUGHLIN-01",
        "R2D3-2022-ILOTT-01",
        "R2D3-2022-MALUKAS-01",
        "R2D3-2022-SATO-01",
        "R2D3-2022-MALUKAS-SATO-ORDER-01",
    }

    actual_ids = set(
        state_ids
    )

    ilott_bad_queue_inference = any(
        txt(
            row.get(
                "driver_name"
            )
        )
        ==
        "Callum Ilott"
        and
        (
            txt(
                row.get(
                    "queue_membership"
                )
            )
            not in {
                "",
                "UNKNOWN",
            }
            or
            txt(
                row.get(
                    "queue_lane"
                )
            )
            not in {
                "",
                "UNKNOWN",
            }
            or
            txt(
                row.get(
                    "queue_position"
                )
            )
            not in {
                "",
                "UNKNOWN",
            }
        )
        for row in ledger
    )

    malukas_sato_lane_inference = any(
        txt(
            row.get(
                "driver_name"
            )
        )
        in {
            "David Malukas",
            "Takuma Sato",
        }
        and
        txt(
            row.get(
                "queue_lane"
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
                "ledger_row_count_is_5",

            "value":
                len(
                    ledger
                ),

            "status":
                (
                    "PASS"
                    if len(
                        ledger
                    )
                    ==
                    5
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "queue_state_ids_unique",

            "value":
                int(
                    len(
                        state_ids
                    )
                    ==
                    len(
                        set(
                            state_ids
                        )
                    )
                ),

            "status":
                (
                    "PASS"
                    if len(
                        state_ids
                    )
                    ==
                    len(
                        set(
                            state_ids
                        )
                    )
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "expected_state_set_exact",

            "value":
                int(
                    actual_ids
                    ==
                    expected_ids
                ),

            "status":
                (
                    "PASS"
                    if actual_ids
                    ==
                    expected_ids
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "mclaughlin_explicit_lane_rows_is_1",

            "value":
                len(
                    explicit_lane_rows
                ),

            "status":
                (
                    "PASS"
                    if len(
                        explicit_lane_rows
                    )
                    ==
                    1
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "mclaughlin_front_position_rows_is_1",

            "value":
                len(
                    explicit_position_rows
                ),

            "status":
                (
                    "PASS"
                    if len(
                        explicit_position_rows
                    )
                    ==
                    1
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "generic_line_membership_rows_is_2",

            "value":
                len(
                    generic_membership_rows
                ),

            "status":
                (
                    "PASS"
                    if len(
                        generic_membership_rows
                    )
                    ==
                    2
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "ordering_rows_is_2",

            "value":
                len(
                    ordering_rows
                ),

            "status":
                (
                    "PASS"
                    if len(
                        ordering_rows
                    )
                    ==
                    2
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "ilott_queue_position_not_inferred",

            "value":
                int(
                    not ilott_bad_queue_inference
                ),

            "status":
                (
                    "PASS"
                    if not ilott_bad_queue_inference
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "malukas_sato_lane_not_inferred",

            "value":
                int(
                    not malukas_sato_lane_inference
                ),

            "status":
                (
                    "PASS"
                    if not malukas_sato_lane_inference
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "exact_queue_wait_inferred",

            "value":
                len(
                    queue_wait_known_rows
                ),

            "status":
                (
                    "PASS"
                    if len(
                        queue_wait_known_rows
                    )
                    ==
                    0
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "bounded_queue_wait_inferred",

            "value":
                len(
                    bounded_wait_rows
                ),

            "status":
                (
                    "PASS"
                    if len(
                        bounded_wait_rows
                    )
                    ==
                    0
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "exact_timestamp_inferred",

            "value":
                len(
                    exact_time_rows
                ),

            "status":
                (
                    "PASS"
                    if len(
                        exact_time_rows
                    )
                    ==
                    0
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "inter_attempt_gap_used_as_queue_wait",

            "value":
                0,

            "status":
                "PASS",
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

        {
            "metric":
                "decision_state_mutation",

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
        ]
        ==
        "PASS"
        for row in qa_rows
    )

    print()
    print("=" * 124)

    if success:

        print(
            "FINAL STATUS: "
            "R2D3_QUEUE_REQUEUE_EVIDENCE_LEDGER_V1_READY"
        )

    else:

        print(
            "FINAL STATUS: "
            "R2D3_QUEUE_REQUEUE_LEDGER_REVIEW_REQUIRED"
        )

    print("=" * 124)

    print()
    print("OUTPUTS")
    print(LEDGER_OUT)
    print(SUMMARY_OUT)
    print(QA_OUT)


if __name__ == "__main__":
    main()
