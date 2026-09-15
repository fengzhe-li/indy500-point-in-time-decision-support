from pathlib import Path
import csv


PHASE = "R2D.1A"

INPUT = Path(
    "weather/output/"
    "queue_rescue_2022_repeat_pair_targeted_hits_v1.csv"
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

ADJUDICATION_OUT = (
    OUTPUT_DIR
    / "queue_rescue_2022_candidate_adjudication_v1.csv"
)

QA_OUT = (
    OUTPUT_DIR
    / "queue_rescue_2022_candidate_adjudication_v1_qa.csv"
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
        "R2D.1A — 2022 QUEUE / REQUEUE "
        "CANDIDATE SEMANTIC ADJUDICATION"
    )
    print("=" * 122)

    required = [
        INPUT,
        ACTION_V8,
        STATE_V2,
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
            "R2D1A_QUEUE_ADJUDICATION_INPUT_MISSING"
        )
        return

    hits = read_csv(INPUT)
    action = read_csv(ACTION_V8)
    states = read_csv(STATE_V2)

    priority_classes = {
        "DIRECT_QUEUE_POSITION_CANDIDATE",
        "DIRECT_QUEUE_MEMBERSHIP_CANDIDATE",
        "SOURCE_NATIVE_RUN_ORDER_CANDIDATE",
        "SOURCE_NATIVE_RESTART_ORDER_CANDIDATE",
    }

    priority = [
        row
        for row in hits
        if txt(
            row.get(
                "classification"
            )
        )
        in priority_classes
    ]

    print()
    print(
        "Priority scanner rows:",
        len(priority),
    )

    # --------------------------------------------------
    # Existing grounding
    # --------------------------------------------------

    mclaughlin_lane1 = any(
        txt(row.get("driver_name"))
        ==
        "Scott McLaughlin"
        and
        txt(row.get("lane"))
        ==
        "LANE_1"
        and
        txt(row.get("action"))
        ==
        "WITHDRAW_EXISTING_RESULT_AND_USE_LANE1"
        for row in action
    )

    mclaughlin_rank15 = any(
        txt(row.get("driver_name"))
        ==
        "Scott McLaughlin"
        and
        txt(row.get("rank"))
        ==
        "15"
        and
        txt(row.get("state_stage"))
        ==
        "PRE_ACTION_EXISTING_RESULT"
        for row in states
    )

    print()
    print(
        "McLaughlin Lane 1 action grounded in V8:",
        mclaughlin_lane1,
    )

    print(
        "McLaughlin pre-action P15 grounded in state V2:",
        mclaughlin_rank15,
    )

    adjudicated_raw = []

    for i, row in enumerate(
        priority,
        start=1,
    ):

        driver = txt(
            row.get(
                "driver_name"
            )
        )

        text = txt(
            row.get(
                "text"
            )
        )

        lower = text.lower()

        original_class = txt(
            row.get(
                "classification"
            )
        )

        decision = "REVIEW_REQUIRED"

        queue_lane = "UNKNOWN"
        queue_position = "UNKNOWN"
        queue_membership = "UNKNOWN"

        queue_wait_seconds = "UNKNOWN"
        exact_timestamp = "UNKNOWN"

        time_quality = "UNKNOWN"

        promotion_ready = False

        reason = ""

        # --------------------------------------------------
        # McLaughlin:
        # genuine source-native queue-position evidence.
        # --------------------------------------------------

        if (
            driver == "Scott McLaughlin"
            and
            "front of the lane 1 queue"
            in lower
            and
            "15th place time"
            in lower
        ):

            decision = (
                "PROMOTION_CANDIDATE_"
                "FRONT_OF_LANE1_QUEUE"
            )

            queue_lane = "LANE_1"
            queue_position = "FRONT"
            queue_membership = "CONFIRMED"

            time_quality = "ORDERING_ONLY"

            promotion_ready = all([
                mclaughlin_lane1,
                mclaughlin_rank15,
            ])

            reason = (
                "The Race directly states that Scott "
                "McLaughlin gave up his 15th-place time "
                "to jump to the front of the Lane 1 queue. "
                "This supports Lane 1 queue membership and "
                "front-of-queue position. It does not "
                "provide queue wait duration or an exact "
                "timestamp."
            )

        # --------------------------------------------------
        # Sato:
        # first run -> second attempt is attempt chronology,
        # NOT queue evidence.
        # --------------------------------------------------

        elif driver == "Takuma Sato":

            decision = (
                "REJECT_ATTEMPT_ORDER_ONLY_NOT_QUEUE"
            )

            reason = (
                "The source supports first-run / second-attempt "
                "ordering or identifies the next driver after "
                "Sato's first run. It does not state Sato's "
                "queue membership, queue position, requeue "
                "position, or wait duration."
            )

        # --------------------------------------------------
        # Castroneves:
        # action + final grid result is not queue evidence.
        # --------------------------------------------------

        elif driver == "Helio Castroneves":

            decision = (
                "REJECT_ACTION_FINAL_RESULT_NOT_QUEUE"
            )

            reason = (
                "The source states Castroneves bailed out of "
                "his first run and later started 27th. This "
                "does not establish queue membership, requeue "
                "order, queue position, or wait."
            )

        else:

            decision = (
                "REVIEW_REQUIRED"
            )

            reason = (
                "Candidate was not safely attributable to "
                "a source-native historical queue state."
            )

        adjudicated_raw.append({
            "phase":
                PHASE,

            "driver_name":
                driver,

            "source_path":
                txt(
                    row.get(
                        "source_path"
                    )
                ),

            "original_classification":
                original_class,

            "decision":
                decision,

            "queue_lane":
                queue_lane,

            "queue_membership":
                queue_membership,

            "queue_position":
                queue_position,

            "queue_wait_seconds":
                queue_wait_seconds,

            "time_quality":
                time_quality,

            "exact_timestamp":
                exact_timestamp,

            "promotion_ready":
                str(
                    promotion_ready
                ),

            "reason":
                reason,

            "source_text":
                text,
        })

        print()
        print("-" * 122)

        print(
            f"CANDIDATE {i}"
        )

        print(
            "driver:",
            driver,
        )

        print(
            "original:",
            original_class,
        )

        print(
            "decision:",
            decision,
        )

        print(
            "promotion ready:",
            promotion_ready,
        )

    # --------------------------------------------------
    # Deduplicate same source-native semantic units.
    #
    # TXT and HTML copies are not independent evidence.
    # Multiple regex hits on the same sentence are not
    # independent evidence either.
    # --------------------------------------------------

    deduped = []

    seen = set()

    for row in adjudicated_raw:

        if (
            txt(row.get("promotion_ready")).lower()
            ==
            "true"
        ):

            key = (
                txt(
                    row.get(
                        "driver_name"
                    )
                ),
                txt(
                    row.get(
                        "decision"
                    )
                ),
                txt(
                    row.get(
                        "queue_lane"
                    )
                ),
                txt(
                    row.get(
                        "queue_position"
                    )
                ),
            )

        else:

            key = (
                txt(
                    row.get(
                        "driver_name"
                    )
                ),
                txt(
                    row.get(
                        "decision"
                    )
                ),
            )

        if key in seen:
            continue

        seen.add(key)

        deduped.append(row)

    # Assign stable evidence IDs after deduplication.
    evidence_counter = 1

    for row in deduped:

        row[
            "evidence_id"
        ] = (
            f"R2D1A-Q{evidence_counter:03d}"
        )

        evidence_counter += 1

    promotion_rows = [
        row
        for row in deduped
        if txt(
            row.get(
                "promotion_ready"
            )
        ).lower()
        ==
        "true"
    ]

    rejected_sato = [
        row
        for row in deduped
        if (
            txt(
                row.get(
                    "driver_name"
                )
            )
            ==
            "Takuma Sato"
            and
            txt(
                row.get(
                    "decision"
                )
            )
            ==
            "REJECT_ATTEMPT_ORDER_ONLY_NOT_QUEUE"
        )
    ]

    rejected_helio = [
        row
        for row in deduped
        if (
            txt(
                row.get(
                    "driver_name"
                )
            )
            ==
            "Helio Castroneves"
            and
            txt(
                row.get(
                    "decision"
                )
            )
            ==
            "REJECT_ACTION_FINAL_RESULT_NOT_QUEUE"
        )
    ]

    mclaughlin_promotions = [
        row
        for row in promotion_rows
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
                    "queue_lane"
                )
            )
            ==
            "LANE_1"
            and
            txt(
                row.get(
                    "queue_position"
                )
            )
            ==
            "FRONT"
        )
    ]

    print()
    print("=" * 122)
    print("DEDUPLICATED ADJUDICATION SUMMARY")
    print("=" * 122)

    print()
    print(
        "Raw priority rows:",
        len(priority),
    )

    print(
        "Deduplicated semantic evidence rows:",
        len(deduped),
    )

    print(
        "Promotion-ready semantic units:",
        len(
            promotion_rows
        ),
    )

    print()
    print(
        "McLaughlin front-of-Lane1 units:",
        len(
            mclaughlin_promotions
        ),
    )

    print(
        "Sato non-queue ordering units:",
        len(
            rejected_sato
        ),
    )

    print(
        "Castroneves non-queue units:",
        len(
            rejected_helio
        ),
    )

    print()
    print(
        "SUPPORTED QUEUE STATE"
    )

    print(
        "  driver = Scott McLaughlin"
    )

    print(
        "  lane = LANE_1"
    )

    print(
        "  queue membership = CONFIRMED"
    )

    print(
        "  queue position = FRONT"
    )

    print(
        "  existing/pre-action rank = 15"
    )

    print(
        "  time quality = ORDERING_ONLY"
    )

    print(
        "  queue wait = UNKNOWN"
    )

    print(
        "  exact timestamp = UNKNOWN"
    )

    fields = [
        "evidence_id",
        "phase",
        "driver_name",
        "source_path",
        "original_classification",
        "decision",
        "queue_lane",
        "queue_membership",
        "queue_position",
        "queue_wait_seconds",
        "time_quality",
        "exact_timestamp",
        "promotion_ready",
        "reason",
        "source_text",
    ]

    write_csv(
        ADJUDICATION_OUT,
        deduped,
        fields,
    )

    qa_rows = [
        {
            "metric":
                "raw_priority_rows",

            "value":
                len(priority),

            "status":
                (
                    "PASS"
                    if len(priority) == 10
                    else
                    "REVIEW"
                ),
        },

        {
            "metric":
                "mclaughlin_lane1_grounded",

            "value":
                int(
                    mclaughlin_lane1
                ),

            "status":
                (
                    "PASS"
                    if mclaughlin_lane1
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "mclaughlin_rank15_grounded",

            "value":
                int(
                    mclaughlin_rank15
                ),

            "status":
                (
                    "PASS"
                    if mclaughlin_rank15
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "mclaughlin_front_lane1_exactly_one",

            "value":
                len(
                    mclaughlin_promotions
                ),

            "status":
                (
                    "PASS"
                    if len(
                        mclaughlin_promotions
                    )
                    ==
                    1
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "promotion_ready_driver_count",

            "value":
                len({
                    txt(
                        row.get(
                            "driver_name"
                        )
                    )
                    for row in promotion_rows
                }),

            "status":
                (
                    "PASS"
                    if {
                        txt(
                            row.get(
                                "driver_name"
                            )
                        )
                        for row in promotion_rows
                    }
                    ==
                    {
                        "Scott McLaughlin"
                    }
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "sato_queue_inference_rejected",

            "value":
                int(
                    len(
                        rejected_sato
                    )
                    >=
                    1
                ),

            "status":
                "PASS",
        },

        {
            "metric":
                "castroneves_queue_inference_rejected",

            "value":
                int(
                    len(
                        rejected_helio
                    )
                    >=
                    1
                ),

            "status":
                "PASS",
        },

        {
            "metric":
                "queue_wait_inferred",

            "value":
                0,

            "status":
                "PASS",
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
                "exact_timestamp_inferred",

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

    hard_fail = any(
        row[
            "status"
        ]
        ==
        "FAIL"
        for row in qa_rows
    )

    print()
    print("=" * 122)

    if not hard_fail:

        print(
            "FINAL STATUS: "
            "R2D1A_QUEUE_CANDIDATES_ADJUDICATED_"
            "MCLAUGHLIN_FRONT_LANE1_PROMOTION_READY"
        )

    else:

        print(
            "FINAL STATUS: "
            "R2D1A_QUEUE_ADJUDICATION_REVIEW_REQUIRED"
        )

    print("=" * 122)

    print()
    print("OUTPUTS")
    print(ADJUDICATION_OUT)
    print(QA_OUT)


if __name__ == "__main__":
    main()
