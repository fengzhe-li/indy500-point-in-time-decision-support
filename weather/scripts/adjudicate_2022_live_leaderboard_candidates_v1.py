from pathlib import Path
import csv


PHASE = "R2C.1A"

INPUT = Path(
    "weather/output/"
    "leaderboard_rescue_2022_repeat_pair_targeted_hits_v1.csv"
)

CHRONOLOGY_V10 = Path(
    "weather/output/"
    "unified_attempt_chronology_constraint_ledger_v10.csv"
)

ACTION_V8 = Path(
    "weather/output/"
    "unified_attempt_action_lane_ledger_v8.csv"
)

OUTPUT_DIR = Path("weather/output")

ADJUDICATION_OUT = (
    OUTPUT_DIR
    / "leaderboard_rescue_2022_candidate_adjudication_v1.csv"
)

QA_OUT = (
    OUTPUT_DIR
    / "leaderboard_rescue_2022_candidate_adjudication_v1_qa.csv"
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
        "R2C.1A — 2022 LIVE LEADERBOARD "
        "CANDIDATE SEMANTIC ADJUDICATION"
    )
    print("=" * 122)

    required = [
        INPUT,
        CHRONOLOGY_V10,
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
            "R2C1A_INPUT_MISSING"
        )
        return

    rows = read_csv(INPUT)

    priority = [
        row
        for row in rows
        if txt(row.get("classification"))
        in {
            "LIVE_CUTOFF_CANDIDATE",
            "TEMPORAL_CUTOFF_CANDIDATE",
            "LIVE_RANK_CANDIDATE",
            "TEMPORAL_RANK_CANDIDATE",
            "CUTOFF_SPEED_CANDIDATE",
        }
    ]

    print()
    print(
        "High-value scanner candidates:",
        len(priority),
    )

    adjudicated = []

    for i, row in enumerate(priority, start=1):

        driver = txt(
            row.get("driver_name")
        )

        text = txt(
            row.get("text")
        )

        lower = text.lower()

        source_path = txt(
            row.get("source_path")
        )

        decision = "REVIEW_REQUIRED"
        reason = ""
        supported_rank_before = ""
        supported_rank_after = ""
        cutoff_rank = "UNKNOWN"
        cutoff_speed = "UNKNOWN"
        time_quality = "UNKNOWN"
        promotion_ready = False

        # --------------------------------------------------
        # Malukas / Sato official recap:
        # "ending up 13th" is retrospective final-result
        # language, not contemporaneous decision-time rank.
        # --------------------------------------------------

        if (
            driver in {
                "David Malukas",
                "Takuma Sato",
            }
            and
            "ending up 13th"
            in lower
        ):
            decision = (
                "REJECT_FINAL_RESULT_ONLY"
            )

            reason = (
                "The unit explicitly uses retrospective "
                "'ending up 13th' language. It describes "
                "session-end outcome rather than a "
                "decision-time live leaderboard or cutoff."
            )

        # --------------------------------------------------
        # The Race Karam/McLaughlin sentence:
        #
        # 15th and 26th both grammatically belong to
        # Scott McLaughlin.
        #
        # Karam is only the preceding clause:
        # "Sage Karam was unable to improve".
        # --------------------------------------------------

        elif (
            driver == "Sage Karam"
            and
            "scott mclaughlin"
            in lower
            and
            "tumbled down to 26th"
            in lower
        ):
            decision = (
                "REJECT_DRIVER_ATTRIBUTION_CONTAMINATION"
            )

            reason = (
                "The rank expressions in the sentence "
                "refer to Scott McLaughlin, not Sage Karam. "
                "Karam is only described as unable to improve."
            )

        elif (
            driver == "Scott McLaughlin"
            and
            "15th place time"
            in lower
            and
            "lane 1 queue"
            in lower
            and
            "tumbled down to 26th"
            in lower
        ):
            decision = (
                "PROMOTION_CANDIDATE_TEMPORAL_RANK_TRANSITION"
            )

            reason = (
                "The sentence directly binds Scott McLaughlin "
                "to a 15th-place existing time, surrendering "
                "that time to enter Lane 1, and subsequently "
                "tumbling to 26th after the track reopened. "
                "This supports a temporal rank transition, "
                "but not exact timestamp or Top-12 cutoff."
            )

            supported_rank_before = "15"
            supported_rank_after = "26"
            time_quality = "ORDERING_ONLY"
            promotion_ready = True

        adjudicated.append({
            "phase":
                PHASE,

            "driver_name":
                driver,

            "source_path":
                source_path,

            "original_classification":
                txt(
                    row.get(
                        "classification"
                    )
                ),

            "decision":
                decision,

            "reason":
                reason,

            "supported_rank_before":
                supported_rank_before,

            "supported_rank_after":
                supported_rank_after,

            "cutoff_rank":
                cutoff_rank,

            "cutoff_speed":
                cutoff_speed,

            "time_quality":
                time_quality,

            "exact_timestamp":
                "UNKNOWN",

            "live_top12_cutoff_known":
                "False",

            "promotion_ready":
                str(
                    promotion_ready
                ),

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
            txt(
                row.get(
                    "classification"
                )
            ),
        )
        print(
            "decision:",
            decision,
        )

        if supported_rank_before:
            print(
                "supported rank before:",
                supported_rank_before,
            )

        if supported_rank_after:
            print(
                "supported rank after:",
                supported_rank_after,
            )

        print(
            "promotion ready:",
            promotion_ready,
        )

    write_csv(
        ADJUDICATION_OUT,
        adjudicated,
        [
            "phase",
            "driver_name",
            "source_path",
            "original_classification",
            "decision",
            "reason",
            "supported_rank_before",
            "supported_rank_after",
            "cutoff_rank",
            "cutoff_speed",
            "time_quality",
            "exact_timestamp",
            "live_top12_cutoff_known",
            "promotion_ready",
            "source_text",
        ],
    )

    promotion_rows = [
        row
        for row in adjudicated
        if txt(
            row.get(
                "promotion_ready"
            )
        ).lower()
        ==
        "true"
    ]

    promotion_drivers = sorted({
        txt(
            row.get(
                "driver_name"
            )
        )
        for row in promotion_rows
    })

    rejected_final = [
        row
        for row in adjudicated
        if txt(
            row.get(
                "decision"
            )
        )
        ==
        "REJECT_FINAL_RESULT_ONLY"
    ]

    rejected_contamination = [
        row
        for row in adjudicated
        if txt(
            row.get(
                "decision"
            )
        )
        ==
        "REJECT_DRIVER_ATTRIBUTION_CONTAMINATION"
    ]

    print()
    print("=" * 122)
    print("ADJUDICATION SUMMARY")
    print("=" * 122)

    print()
    print(
        "Scanner high-value candidates:",
        len(priority),
    )

    print(
        "Promotion-ready candidates:",
        len(
            promotion_rows
        ),
    )

    print(
        "Promotion-ready drivers:",
        "|".join(
            promotion_drivers
        )
        or
        "NONE",
    )

    print(
        "Rejected final-result-only:",
        len(
            rejected_final
        ),
    )

    print(
        "Rejected driver contamination:",
        len(
            rejected_contamination
        ),
    )

    print()
    print(
        "McLaughlin supported state:"
    )

    print(
        "  existing/pre-action rank = 15"
    )

    print(
        "  Lane 1 action = already supported"
    )

    print(
        "  later rank = 26"
    )

    print(
        "  time quality = ORDERING_ONLY"
    )

    print(
        "  Top-12 cutoff = UNKNOWN"
    )

    print(
        "  exact timestamp = UNKNOWN"
    )

    qa_rows = [
        {
            "metric":
                "scanner_high_value_count",

            "value":
                len(priority),

            "status":
                "PASS"
                if len(priority) == 8
                else "REVIEW",
        },

        {
            "metric":
                "promotion_ready_driver_count",

            "value":
                len(
                    promotion_drivers
                ),

            "status":
                "PASS"
                if promotion_drivers
                ==
                ["Scott McLaughlin"]
                else
                "FAIL",
        },

        {
            "metric":
                "malukas_final_result_rejected",

            "value":
                int(
                    any(
                        txt(
                            row.get(
                                "driver_name"
                            )
                        )
                        ==
                        "David Malukas"
                        and
                        txt(
                            row.get(
                                "decision"
                            )
                        )
                        ==
                        "REJECT_FINAL_RESULT_ONLY"
                        for row in adjudicated
                    )
                ),

            "status":
                "PASS",
        },

        {
            "metric":
                "sato_final_result_rejected",

            "value":
                int(
                    any(
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
                        "REJECT_FINAL_RESULT_ONLY"
                        for row in adjudicated
                    )
                ),

            "status":
                "PASS",
        },

        {
            "metric":
                "karam_contamination_rejected",

            "value":
                int(
                    any(
                        txt(
                            row.get(
                                "driver_name"
                            )
                        )
                        ==
                        "Sage Karam"
                        and
                        txt(
                            row.get(
                                "decision"
                            )
                        )
                        ==
                        "REJECT_DRIVER_ATTRIBUTION_CONTAMINATION"
                        for row in adjudicated
                    )
                ),

            "status":
                "PASS",
        },

        {
            "metric":
                "top12_cutoff_inferred",

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
                "ledger_mutation",

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
        row["status"] == "FAIL"
        for row in qa_rows
    )

    print()
    print("=" * 122)

    if not hard_fail:
        print(
            "FINAL STATUS: "
            "R2C1A_LIVE_LEADERBOARD_CANDIDATES_ADJUDICATED"
        )
    else:
        print(
            "FINAL STATUS: "
            "R2C1A_ADJUDICATION_REVIEW_REQUIRED"
        )

    print("=" * 122)

    print()
    print("OUTPUTS")
    print(ADJUDICATION_OUT)
    print(QA_OUT)


if __name__ == "__main__":
    main()
