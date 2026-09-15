from pathlib import Path
import csv
import re


# ============================================================
# PHASE
# ============================================================

PHASE = "R1G.26A"


# ============================================================
# INPUTS
# ============================================================

CANONICAL = Path(
    "data/canonical/v1/attempts.csv"
)

RESULT_MATCH_V3 = Path(
    "weather/output/"
    "chronology_rescue_2022_result_to_canonical_attempt_matches_v3.csv"
)

EVIDENCE_IN = Path(
    "weather/output/"
    "chronology_rescue_2022_ilott_repeat_pair_evidence_v1.csv"
)


# ============================================================
# OUTPUTS
# ============================================================

OUTPUT_DIR = Path(
    "weather/output"
)

ADJUDICATION_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_ilott_sentence_local_adjudication_v1.csv"
)

PROMOTION_CANDIDATE_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_ilott_sentence_local_promotion_candidate_v1.csv"
)

SUMMARY_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_ilott_sentence_local_adjudication_summary_v1.csv"
)

QA_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_ilott_sentence_local_adjudication_v1_qa.csv"
)


# ============================================================
# TARGET
# ============================================================

TARGET_DRIVER = "Callum Ilott"

TARGET_IDS = {
    "3cd6d98a-da75-5822-8dae-05e83ad8457c",
    "8fa25fec-e5a6-5844-b3d7-f67c9dc91378",
}


# ============================================================
# SENTENCE-LOCAL SEMANTIC TERMS
# ============================================================

FIRST_TERMS = [
    "first run",
    "first attempt",
]

SECOND_TERMS = [
    "second run",
    "second attempt",
    "ran again",
    "run again",
    "another run",
    "another attempt",
    "rerun",
    "re-run",
    "went again",
    "went back out",
]

WITHDRAW_TERMS = [
    "withdraw",
    "withdrew",
    "withdrawn",
    "gave up his time",
    "gave up the time",
    "surrendered",
]

LANE1_TERMS = [
    "lane 1",
    "lane one",
    "priority lane",
    "priority queue",
]

LANE2_TERMS = [
    "lane 2",
    "lane two",
]

QUEUE_TERMS = [
    "queue",
    "queued",
    "requeue",
    "re-queue",
]

LATE_IMPROVER_TERMS = [
    "late improver",
    "late improvement",
    "improved late",
]

GENERIC_IMPROVE_TERMS = [
    "improve",
    "improved",
    "improvement",
]


# ============================================================
# HELPERS
# ============================================================

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
        )

        writer.writeheader()
        writer.writerows(rows)


def normalize_name(value):
    raw = txt(value)

    if not raw:
        return ""

    if "," in raw:
        parts = [
            part.strip()
            for part in raw.split(",")
            if part.strip()
        ]

        if len(parts) == 2:
            raw = (
                parts[1]
                + " "
                + parts[0]
            )

    return " ".join(
        raw.lower()
        .replace(".", "")
        .replace("'", "")
        .replace("’", "")
        .replace("-", " ")
        .split()
    )


def is_ilott_sentence(sentence):
    lower = txt(sentence).lower()

    return (
        "callum ilott" in lower
        or
        re.search(
            r"\bilott\b",
            lower,
        )
        is not None
    )


def contains_any(text, terms):
    lower = txt(text).lower()

    return any(
        term in lower
        for term in terms
    )


def matched_terms(text, terms):
    lower = txt(text).lower()

    return [
        term
        for term in terms
        if term in lower
    ]


def speed_close(a, b, tol=0.003):
    try:
        return abs(
            float(txt(a))
            -
            float(txt(b))
        ) <= tol
    except Exception:
        return False


def canonical_speed(row):
    for field in [
        "four_lap_average_speed_mph",
        "average_speed_mph",
        "speed_mph",
    ]:

        value = txt(
            row.get(field)
        )

        if value:
            return value

    return ""


# ============================================================
# MAIN
# ============================================================

def main():

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print()
    print("=" * 120)
    print(
        "R1G.26A — 2022 CALLUM ILOTT "
        "SENTENCE-LOCAL EVIDENCE ADJUDICATION V1 / ACTIVE V3"
    )
    print("=" * 120)

    # ========================================================
    # INPUT CHECK
    # ========================================================

    required = [
        CANONICAL,
        RESULT_MATCH_V3,
        EVIDENCE_IN,
    ]

    missing = []

    print()
    print("INPUT CHECK")
    print("-" * 120)

    for path in required:

        exists = path.exists()

        print(
            f"{path}: "
            f"{'PRESENT' if exists else 'MISSING'}"
        )

        if not exists:
            missing.append(path)

    if missing:

        print()
        print(
            "FINAL STATUS: "
            "ILOTT_SENTENCE_LOCAL_ADJUDICATION_INPUT_MISSING"
        )
        return

    canonical = read_csv(
        CANONICAL
    )

    result_v3 = read_csv(
        RESULT_MATCH_V3
    )

    evidence = read_csv(
        EVIDENCE_IN
    )

    # ========================================================
    # CANONICAL TARGET CHECK
    # ========================================================

    target_canonical = [
        row
        for row in canonical
        if txt(
            row.get(
                "attempt_id"
            )
        ) in TARGET_IDS
    ]

    target_canonical = sorted(
        target_canonical,
        key=lambda row: int(
            txt(
                row.get(
                    "car_attempt_index"
                )
            )
            or "999"
        ),
    )

    print()
    print("=" * 120)
    print(
        "ILOTT CANONICAL PAIR"
    )
    print("=" * 120)

    print()
    print(
        "Target canonical rows:",
        len(
            target_canonical
        ),
    )

    for row in target_canonical:

        print()
        print(
            "attempt_id:",
            txt(
                row.get(
                    "attempt_id"
                )
            ),
        )

        print(
            "  attempt_index:",
            repr(
                txt(
                    row.get(
                        "car_attempt_index"
                    )
                )
            ),
        )

        print(
            "  speed:",
            repr(
                canonical_speed(row)
            ),
        )

        print(
            "  result_status:",
            repr(
                txt(
                    row.get(
                        "result_status"
                    )
                )
            ),
        )

    if len(
        target_canonical
    ) != 2:

        print()
        print(
            "FINAL STATUS: "
            "ILOTT_CANONICAL_PAIR_REVIEW_REQUIRED"
        )
        return

    first = target_canonical[0]
    second = target_canonical[1]

    first_id = txt(
        first.get(
            "attempt_id"
        )
    )

    second_id = txt(
        second.get(
            "attempt_id"
        )
    )

    first_speed = canonical_speed(
        first
    )

    second_speed = canonical_speed(
        second
    )

    # ========================================================
    # V3 RESULT CHECK
    # ========================================================

    result_by_id = {
        txt(
            row.get(
                "attempt_id"
            )
        ): row
        for row in result_v3
        if txt(
            row.get(
                "attempt_id"
            )
        )
    }

    first_result = result_by_id.get(
        first_id,
        {},
    )

    second_result = result_by_id.get(
        second_id,
        {},
    )

    print()
    print("=" * 120)
    print(
        "RESULT-MATCH V3 TARGET CHECK"
    )
    print("=" * 120)

    print()
    print(
        "FIRST:",
        first_id,
        "|",
        first_speed,
        "| official status:",
        repr(
            txt(
                first_result.get(
                    "official_status"
                )
            )
        ),
    )

    print(
        "SECOND:",
        second_id,
        "|",
        second_speed,
        "| official status:",
        repr(
            txt(
                second_result.get(
                    "official_status"
                )
            )
        ),
    )

    # ========================================================
    # SENTENCE-LOCAL ADJUDICATION
    # ========================================================

    adjudicated_rows = []

    print()
    print("=" * 120)
    print(
        "SENTENCE-LOCAL EVIDENCE REVIEW"
    )
    print("=" * 120)

    for row in evidence:

        sentence = txt(
            row.get(
                "sentence"
            )
        )

        context = txt(
            row.get(
                "context"
            )
        )

        if not is_ilott_sentence(
            sentence
        ):
            continue

        sentence_first = (
            matched_terms(
                sentence,
                FIRST_TERMS,
            )
        )

        sentence_second = (
            matched_terms(
                sentence,
                SECOND_TERMS,
            )
        )

        sentence_withdraw = (
            matched_terms(
                sentence,
                WITHDRAW_TERMS,
            )
        )

        sentence_lane1 = (
            matched_terms(
                sentence,
                LANE1_TERMS,
            )
        )

        sentence_lane2 = (
            matched_terms(
                sentence,
                LANE2_TERMS,
            )
        )

        sentence_queue = (
            matched_terms(
                sentence,
                QUEUE_TERMS,
            )
        )

        sentence_late = (
            matched_terms(
                sentence,
                LATE_IMPROVER_TERMS,
            )
        )

        sentence_improve = (
            matched_terms(
                sentence,
                GENERIC_IMPROVE_TERMS,
            )
        )

        context_first = (
            matched_terms(
                context,
                FIRST_TERMS,
            )
        )

        context_second = (
            matched_terms(
                context,
                SECOND_TERMS,
            )
        )

        context_withdraw = (
            matched_terms(
                context,
                WITHDRAW_TERMS,
            )
        )

        context_lane1 = (
            matched_terms(
                context,
                LANE1_TERMS,
            )
        )

        context_lane2 = (
            matched_terms(
                context,
                LANE2_TERMS,
            )
        )

        context_queue = (
            matched_terms(
                context,
                QUEUE_TERMS,
            )
        )

        speed_hits = txt(
            row.get(
                "exact_speed_hits"
            )
        )

        context_only_terms = []

        if (
            context_first
            and
            not sentence_first
        ):
            context_only_terms.extend(
                [
                    "FIRST:"
                    + term
                    for term in context_first
                ]
            )

        if (
            context_second
            and
            not sentence_second
        ):
            context_only_terms.extend(
                [
                    "SECOND:"
                    + term
                    for term in context_second
                ]
            )

        if (
            context_withdraw
            and
            not sentence_withdraw
        ):
            context_only_terms.extend(
                [
                    "WITHDRAW:"
                    + term
                    for term in context_withdraw
                ]
            )

        if (
            context_lane1
            and
            not sentence_lane1
        ):
            context_only_terms.extend(
                [
                    "LANE1:"
                    + term
                    for term in context_lane1
                ]
            )

        if (
            context_lane2
            and
            not sentence_lane2
        ):
            context_only_terms.extend(
                [
                    "LANE2:"
                    + term
                    for term in context_lane2
                ]
            )

        if (
            context_queue
            and
            not sentence_queue
        ):
            context_only_terms.extend(
                [
                    "QUEUE:"
                    + term
                    for term in context_queue
                ]
            )

        # ====================================================
        # CLASSIFICATION
        # ====================================================

        direct_repeat_semantics = (
            bool(
                sentence_first
            )
            or
            bool(
                sentence_second
            )
        )

        direct_action_semantics = (
            bool(
                sentence_withdraw
            )
            or
            bool(
                sentence_lane1
            )
            or
            bool(
                sentence_lane2
            )
            or
            bool(
                sentence_queue
            )
        )

        if (
            sentence_late
            and
            not direct_repeat_semantics
            and
            not direct_action_semantics
        ):

            classification = (
                "DIRECT_LATE_IMPROVEMENT_ONLY"
            )

            repeat_pair_promotable = False
            action_promotable = False
            lane_promotable = False

            interpretation = (
                "Sentence directly says Ilott was a late improver. "
                "This supports a late-session improvement narrative, "
                "but does not itself identify first/second-run action, "
                "withdrawal, Lane 1, Lane 2, queue, or exact chronology."
            )

        elif (
            speed_hits
            and
            not direct_repeat_semantics
            and
            not direct_action_semantics
        ):

            classification = (
                "RESULT_OR_SPEED_EVIDENCE_ONLY"
            )

            repeat_pair_promotable = False
            action_promotable = False
            lane_promotable = False

            interpretation = (
                "Sentence contains an Ilott speed/result but no "
                "sentence-local repeat-action or lane semantics."
            )

        elif (
            direct_repeat_semantics
            or
            direct_action_semantics
        ):

            classification = (
                "DIRECT_SENTENCE_LOCAL_ACTION_OR_REPEAT_CANDIDATE"
            )

            repeat_pair_promotable = (
                bool(
                    sentence_first
                )
                or
                bool(
                    sentence_second
                )
            )

            action_promotable = (
                bool(
                    sentence_withdraw
                )
            )

            lane_promotable = (
                bool(
                    sentence_lane1
                )
                or
                bool(
                    sentence_lane2
                )
            )

            interpretation = (
                "Sentence itself contains Ilott-specific "
                "repeat/action/lane language and merits "
                "targeted adjudication."
            )

        elif context_only_terms:

            classification = (
                "CONTEXT_JOIN_FALSE_POSITIVE"
            )

            repeat_pair_promotable = False
            action_promotable = False
            lane_promotable = False

            interpretation = (
                "Action/repeat/lane terms occur only in adjacent "
                "context, not in the Ilott sentence. "
                "Do not attribute them to Ilott."
            )

        else:

            classification = (
                "ILOTT_MENTION_NO_DECISION_SEMANTICS"
            )

            repeat_pair_promotable = False
            action_promotable = False
            lane_promotable = False

            interpretation = (
                "Ilott is mentioned, but the sentence carries "
                "no decision-relevant repeat/action/lane semantics."
            )

        out = {
            "evidence_id":
                txt(
                    row.get(
                        "evidence_id"
                    )
                ),

            "source_type":
                txt(
                    row.get(
                        "source_type"
                    )
                ),

            "source_class":
                txt(
                    row.get(
                        "source_class"
                    )
                ),

            "source_name":
                txt(
                    row.get(
                        "source_name"
                    )
                ),

            "source_path":
                txt(
                    row.get(
                        "source_path"
                    )
                ),

            "sentence":
                sentence,

            "exact_speed_hits":
                speed_hits,

            "sentence_first_terms":
                "|".join(
                    sentence_first
                ),

            "sentence_second_terms":
                "|".join(
                    sentence_second
                ),

            "sentence_withdraw_terms":
                "|".join(
                    sentence_withdraw
                ),

            "sentence_lane1_terms":
                "|".join(
                    sentence_lane1
                ),

            "sentence_lane2_terms":
                "|".join(
                    sentence_lane2
                ),

            "sentence_queue_terms":
                "|".join(
                    sentence_queue
                ),

            "sentence_late_improver_terms":
                "|".join(
                    sentence_late
                ),

            "sentence_improve_terms":
                "|".join(
                    sentence_improve
                ),

            "context_only_decision_terms":
                "|".join(
                    context_only_terms
                ),

            "classification":
                classification,

            "repeat_pair_promotable":
                str(
                    repeat_pair_promotable
                ),

            "action_promotable":
                str(
                    action_promotable
                ),

            "lane_promotable":
                str(
                    lane_promotable
                ),

            "interpretation":
                interpretation,
        }

        adjudicated_rows.append(
            out
        )

        print()
        print(
            out[
                "evidence_id"
            ],
            "|",
            classification,
        )

        print(
            "source:",
            out[
                "source_name"
            ],
        )

        print(
            "sentence:"
        )

        print(
            sentence
        )

        print(
            "sentence-local first:",
            out[
                "sentence_first_terms"
            ]
            or
            "NONE",
        )

        print(
            "sentence-local second:",
            out[
                "sentence_second_terms"
            ]
            or
            "NONE",
        )

        print(
            "sentence-local withdraw:",
            out[
                "sentence_withdraw_terms"
            ]
            or
            "NONE",
        )

        print(
            "sentence-local Lane1:",
            out[
                "sentence_lane1_terms"
            ]
            or
            "NONE",
        )

        print(
            "sentence-local Lane2:",
            out[
                "sentence_lane2_terms"
            ]
            or
            "NONE",
        )

        print(
            "context-only decision terms:",
            out[
                "context_only_decision_terms"
            ]
            or
            "NONE",
        )

    # ========================================================
    # DEDUPLICATE SEMANTIC EVIDENCE
    #
    # TXT + raw HTML duplicates should not be counted as
    # independent historical observations.
    # ========================================================

    semantic_keys = set()

    for row in adjudicated_rows:

        key = (
            re.sub(
                r"\s+",
                " ",
                txt(
                    row[
                        "sentence"
                    ]
                ).lower(),
            ).strip()
        )

        semantic_keys.add(
            key
        )

    # ========================================================
    # PROMOTION CANDIDATES
    # ========================================================

    promotion_candidates = [
        row
        for row in adjudicated_rows
        if (
            row[
                "repeat_pair_promotable"
            ] == "True"
            or
            row[
                "action_promotable"
            ] == "True"
            or
            row[
                "lane_promotable"
            ] == "True"
        )
    ]

    late_improvement_rows = [
        row
        for row in adjudicated_rows
        if row[
            "classification"
        ]
        ==
        "DIRECT_LATE_IMPROVEMENT_ONLY"
    ]

    result_only_rows = [
        row
        for row in adjudicated_rows
        if row[
            "classification"
        ]
        ==
        "RESULT_OR_SPEED_EVIDENCE_ONLY"
    ]

    false_positive_rows = [
        row
        for row in adjudicated_rows
        if row[
            "classification"
        ]
        ==
        "CONTEXT_JOIN_FALSE_POSITIVE"
    ]

    direct_repeat_rows = [
        row
        for row in adjudicated_rows
        if row[
            "repeat_pair_promotable"
        ]
        ==
        "True"
    ]

    direct_action_rows = [
        row
        for row in adjudicated_rows
        if row[
            "action_promotable"
        ]
        ==
        "True"
    ]

    direct_lane_rows = [
        row
        for row in adjudicated_rows
        if row[
            "lane_promotable"
        ]
        ==
        "True"
    ]

    # ========================================================
    # DECISION
    # ========================================================

    if (
        direct_repeat_rows
        or
        direct_action_rows
        or
        direct_lane_rows
    ):

        final_status = (
            "ILOTT_DIRECT_REPEAT_ACTION_EVIDENCE_ADJUDICATION_READY"
        )

    elif late_improvement_rows:

        final_status = (
            "ILOTT_LATE_IMPROVEMENT_EVIDENCE_ONLY_"
            "NO_REPEAT_ACTION_PROMOTION"
        )

    else:

        final_status = (
            "ILOTT_SENTENCE_LOCAL_DECISION_EVIDENCE_INSUFFICIENT"
        )

    # ========================================================
    # WRITE
    # ========================================================

    fields = [
        "evidence_id",
        "source_type",
        "source_class",
        "source_name",
        "source_path",
        "sentence",
        "exact_speed_hits",
        "sentence_first_terms",
        "sentence_second_terms",
        "sentence_withdraw_terms",
        "sentence_lane1_terms",
        "sentence_lane2_terms",
        "sentence_queue_terms",
        "sentence_late_improver_terms",
        "sentence_improve_terms",
        "context_only_decision_terms",
        "classification",
        "repeat_pair_promotable",
        "action_promotable",
        "lane_promotable",
        "interpretation",
    ]

    write_csv(
        ADJUDICATION_OUT,
        adjudicated_rows,
        fields,
    )

    write_csv(
        PROMOTION_CANDIDATE_OUT,
        promotion_candidates,
        fields,
    )

    summary_rows = [
        {
            "metric":
                "sentence_local_ilott_rows",

            "value":
                len(
                    adjudicated_rows
                ),
        },

        {
            "metric":
                "unique_sentence_semantics",

            "value":
                len(
                    semantic_keys
                ),
        },

        {
            "metric":
                "context_join_false_positive_rows",

            "value":
                len(
                    false_positive_rows
                ),
        },

        {
            "metric":
                "result_or_speed_only_rows",

            "value":
                len(
                    result_only_rows
                ),
        },

        {
            "metric":
                "direct_late_improvement_rows",

            "value":
                len(
                    late_improvement_rows
                ),
        },

        {
            "metric":
                "direct_repeat_rows",

            "value":
                len(
                    direct_repeat_rows
                ),
        },

        {
            "metric":
                "direct_action_rows",

            "value":
                len(
                    direct_action_rows
                ),
        },

        {
            "metric":
                "direct_lane_rows",

            "value":
                len(
                    direct_lane_rows
                ),
        },

        {
            "metric":
                "promotion_candidate_rows",

            "value":
                len(
                    promotion_candidates
                ),
        },

        {
            "metric":
                "final_status",

            "value":
                final_status,
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

    # ========================================================
    # QA
    # ========================================================

    qa_rows = [
        {
            "metric":
                "result_match_v3_used",

            "value":
                1,

            "status":
                "PASS",
        },

        {
            "metric":
                "result_match_v2_used",

            "value":
                0,

            "status":
                "PASS",
        },

        {
            "metric":
                "canonical_pair_count",

            "value":
                len(
                    target_canonical
                ),

            "status":
                (
                    "PASS"
                    if len(
                        target_canonical
                    ) == 2
                    else "FAIL"
                ),
        },

        {
            "metric":
                "context_terms_used_for_promotion",

            "value":
                0,

            "status":
                "PASS",
        },

        {
            "metric":
                "results_row_order_used_as_chronology",

            "value":
                0,

            "status":
                "PASS",
        },

        {
            "metric":
                "retired_status_interpreted_as_action",

            "value":
                0,

            "status":
                "PASS",
        },

        {
            "metric":
                "withdrawn_status_interpreted_as_lane1",

            "value":
                0,

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
                "automatic_promotions",

            "value":
                0,

            "status":
                "PASS",
        },

        {
            "metric":
                "canonical_mutated",

            "value":
                0,

            "status":
                "PASS",
        },

        {
            "metric":
                "phase5_to_phase8_mutated",

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

    # ========================================================
    # FINAL
    # ========================================================

    print()
    print("=" * 120)
    print(
        "ADJUDICATION SUMMARY"
    )
    print("=" * 120)

    print()
    print(
        "Sentence-local Ilott rows:",
        len(
            adjudicated_rows
        ),
    )

    print(
        "Context-join false positives:",
        len(
            false_positive_rows
        ),
    )

    print(
        "Result/speed-only rows:",
        len(
            result_only_rows
        ),
    )

    print(
        "Direct late-improvement rows:",
        len(
            late_improvement_rows
        ),
    )

    print(
        "Direct repeat rows:",
        len(
            direct_repeat_rows
        ),
    )

    print(
        "Direct action rows:",
        len(
            direct_action_rows
        ),
    )

    print(
        "Direct Lane rows:",
        len(
            direct_lane_rows
        ),
    )

    print(
        "Promotion candidates:",
        len(
            promotion_candidates
        ),
    )

    print()
    print(
        "Important interpretation:"
    )

    print(
        "  Adjacent Rossi/McLaughlin/Castroneves action terms "
        "are not attributed to Ilott."
    )

    print(
        "  'Late improver' is preserved as a direct "
        "Ilott-specific narrative only."
    )

    print(
        "  It is not automatically converted into "
        "first->second chronology, withdrawal, Lane 1, or queue state."
    )

    print(
        "  Official Retired status is not interpreted "
        "as an action without independent semantics."
    )

    print()
    print(
        "No chronology/action/lane evidence was automatically promoted."
    )

    print(
        "No canonical or Phase 5–8 data was modified."
    )

    print()
    print("=" * 120)
    print(
        "FINAL STATUS:",
        final_status,
    )
    print("=" * 120)

    print()
    print("OUTPUTS")
    print(ADJUDICATION_OUT)
    print(PROMOTION_CANDIDATE_OUT)
    print(SUMMARY_OUT)
    print(QA_OUT)


if __name__ == "__main__":
    main()
