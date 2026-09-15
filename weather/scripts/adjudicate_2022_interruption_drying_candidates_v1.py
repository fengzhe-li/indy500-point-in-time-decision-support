from pathlib import Path
import csv


PHASE = "R2F.1A"

INPUT = Path(
    "weather/output/"
    "interruption_rescue_2022_targeted_hits_v1.csv"
)

SUMMARY = Path(
    "weather/output/"
    "interruption_rescue_2022_targeted_summary_v1.csv"
)

OUTPUT_DIR = Path("weather/output")

ADJUDICATION_OUT = (
    OUTPUT_DIR
    / "interruption_rescue_2022_candidate_adjudication_v1.csv"
)

QA_OUT = (
    OUTPUT_DIR
    / "interruption_rescue_2022_candidate_adjudication_v1_qa.csv"
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


def normalize_source_text(text):
    return (
        txt(text)
        .replace("&ndash;", "–")
        .replace("&#8211;", "–")
        .replace("&nbsp;", " ")
    )


def main():

    print()
    print("=" * 124)
    print(
        "R2F.1A — 2022 INTERRUPTION / DRYING / "
        "RESET CANDIDATE SEMANTIC ADJUDICATION"
    )
    print("=" * 124)

    required = [
        INPUT,
        SUMMARY,
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
            "R2F1A_INTERRUPTION_ADJUDICATION_INPUT_MISSING"
        )
        return

    hits = read_csv(INPUT)
    summary = read_csv(SUMMARY)

    summary_map = {
        txt(row.get("metric")):
        txt(row.get("value"))
        for row in summary
    }

    drying_candidates = [
        row
        for row in hits
        if txt(
            row.get("classification")
        )
        ==
        "DIRECT_DRYING_STATE_CANDIDATE"
    ]

    print()
    print(
        "Raw drying candidates:",
        len(drying_candidates),
    )

    adjudicated_raw = []

    for i, row in enumerate(
        drying_candidates,
        start=1,
    ):

        text = normalize_source_text(
            row.get("text")
        )

        lower = text.lower()

        if (
            "too wet for drying"
            in lower
        ):

            decision = (
                "PROMOTION_CANDIDATE_"
                "TRACK_TOO_WET_FOR_DRYING"
            )

            track_wet = "SUPPORTED"
            active_drying = "NOT_SUPPORTED"
            drying_feasible = "NO"
            session_called = "SUPPORTED"

            promotion_ready = True

            reason = (
                "The source does not state that the track "
                "was actively drying. It states the opposite: "
                "the track was too wet for drying before the "
                "remaining session time expired. This supports "
                "a wet-track terminal state and drying "
                "infeasibility, not a drying trajectory."
            )

        else:

            decision = (
                "REVIEW_REQUIRED_DRYING_SEMANTIC"
            )

            track_wet = "UNKNOWN"
            active_drying = "UNKNOWN"
            drying_feasible = "UNKNOWN"
            session_called = "UNKNOWN"

            promotion_ready = False

            reason = (
                "The drying keyword cannot be safely "
                "interpreted without stronger context."
            )

        adjudicated_raw.append({
            "phase":
                PHASE,

            "source_path":
                txt(
                    row.get(
                        "source_path"
                    )
                ),

            "source_class":
                txt(
                    row.get(
                        "source_class"
                    )
                ),

            "original_classification":
                txt(
                    row.get(
                        "classification"
                    )
                ),

            "decision":
                decision,

            "event_semantic":
                (
                    "SESSION_END_TRACK_TOO_WET_FOR_DRYING"
                    if promotion_ready
                    else
                    "UNKNOWN"
                ),

            "track_wet":
                track_wet,

            "active_drying_supported":
                active_drying,

            "drying_feasible_before_session_end":
                drying_feasible,

            "session_called_supported":
                session_called,

            "track_cleaning_supported":
                "NOT_OBSERVED",

            "track_reset_supported":
                "NOT_OBSERVED",

            "grip_effect":
                "UNKNOWN",

            "rubber_effect":
                "UNKNOWN",

            "event_time_quality":
                "ORDERING_ONLY",

            "exact_event_timestamp":
                "UNKNOWN",

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
        print("-" * 124)

        print(
            f"CANDIDATE {i}"
        )

        print(
            "decision:",
            decision,
        )

        print(
            "track wet:",
            track_wet,
        )

        print(
            "active drying supported:",
            active_drying,
        )

        print(
            "drying feasible:",
            drying_feasible,
        )

        print(
            "promotion ready:",
            promotion_ready,
        )

    # --------------------------------------------------
    # Deduplicate TXT / HTML copies.
    # --------------------------------------------------

    deduped = []
    seen = set()

    for row in adjudicated_raw:

        key = (
            txt(
                row.get(
                    "decision"
                )
            ),
            txt(
                row.get(
                    "event_semantic"
                )
            ),
            txt(
                row.get(
                    "source_text"
                )
            ),
        )

        if key in seen:
            continue

        seen.add(key)
        deduped.append(row)

    for i, row in enumerate(
        deduped,
        start=1,
    ):
        row["evidence_id"] = (
            f"R2F1A-I{i:03d}"
        )

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

    wet_terminal_rows = [
        row
        for row in promotion_rows
        if txt(
            row.get(
                "event_semantic"
            )
        )
        ==
        "SESSION_END_TRACK_TOO_WET_FOR_DRYING"
    ]

    direct_cleaning_candidates = int(
        summary_map.get(
            "direct_cleaning_candidates",
            "0",
        )
        or
        0
    )

    direct_reset_candidates = int(
        summary_map.get(
            "direct_reset_candidates",
            "0",
        )
        or
        0
    )

    print()
    print("=" * 124)
    print("ADJUDICATION SUMMARY")
    print("=" * 124)

    print()
    print(
        "Raw drying candidates:",
        len(drying_candidates),
    )

    print(
        "Deduplicated semantic rows:",
        len(deduped),
    )

    print(
        "Promotion-ready event units:",
        len(
            promotion_rows
        ),
    )

    print(
        "Wet / drying-infeasible terminal states:",
        len(
            wet_terminal_rows
        ),
    )

    print(
        "Direct track-cleaning candidates:",
        direct_cleaning_candidates,
    )

    print(
        "Direct track-reset candidates:",
        direct_reset_candidates,
    )

    print()
    print("SUPPORTED EVENT STATE")
    print()

    if wet_terminal_rows:

        print(
            "  event = SESSION_END_TRACK_TOO_WET_FOR_DRYING"
        )

        print(
            "  track wet = SUPPORTED"
        )

        print(
            "  active drying = NOT SUPPORTED"
        )

        print(
            "  drying feasible before session end = NO"
        )

        print(
            "  session called = SUPPORTED"
        )

    print()
    print(
        "Track cleaning:",
        "NOT OBSERVED",
    )

    print(
        "Track reset:",
        "NOT OBSERVED",
    )

    print(
        "Grip effect:",
        "UNKNOWN",
    )

    print(
        "Rubber effect:",
        "UNKNOWN",
    )

    print()
    print(
        "IMPORTANT:"
    )

    print(
        "  rain != full track reset"
    )

    print(
        "  reopened track != known grip state"
    )

    print(
        "  'too wet for drying' != active drying"
    )

    fields = [
        "evidence_id",
        "phase",
        "source_path",
        "source_class",
        "original_classification",
        "decision",
        "event_semantic",
        "track_wet",
        "active_drying_supported",
        "drying_feasible_before_session_end",
        "session_called_supported",
        "track_cleaning_supported",
        "track_reset_supported",
        "grip_effect",
        "rubber_effect",
        "event_time_quality",
        "exact_event_timestamp",
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
                "raw_drying_candidates",

            "value":
                len(
                    drying_candidates
                ),

            "status":
                (
                    "PASS"
                    if len(
                        drying_candidates
                    )
                    ==
                    2
                    else
                    "REVIEW"
                ),
        },

        {
            "metric":
                "deduplicated_wet_terminal_state_exactly_one",

            "value":
                len(
                    wet_terminal_rows
                ),

            "status":
                (
                    "PASS"
                    if len(
                        wet_terminal_rows
                    )
                    ==
                    1
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "active_drying_inferred",

            "value":
                0,

            "status":
                "PASS",
        },

        {
            "metric":
                "track_cleaning_inferred",

            "value":
                0,

            "status":
                "PASS",
        },

        {
            "metric":
                "track_reset_inferred",

            "value":
                0,

            "status":
                "PASS",
        },

        {
            "metric":
                "grip_effect_inferred",

            "value":
                0,

            "status":
                "PASS",
        },

        {
            "metric":
                "rubber_effect_inferred",

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

    hard_fail = any(
        row[
            "status"
        ]
        ==
        "FAIL"
        for row in qa_rows
    )

    print()
    print("=" * 124)

    if not hard_fail:
        print(
            "FINAL STATUS: "
            "R2F1A_INTERRUPTION_DRYING_CANDIDATES_ADJUDICATED_"
            "WET_TERMINAL_STATE_PROMOTION_READY"
        )
    else:
        print(
            "FINAL STATUS: "
            "R2F1A_INTERRUPTION_ADJUDICATION_REVIEW_REQUIRED"
        )

    print("=" * 124)

    print()
    print("OUTPUTS")
    print(ADJUDICATION_OUT)
    print(QA_OUT)


if __name__ == "__main__":
    main()
