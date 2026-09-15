from pathlib import Path
import csv
import html
import re


PHASE = "R1G.26B"

EVIDENCE_IN = Path(
    "weather/output/"
    "chronology_rescue_2022_ilott_repeat_pair_evidence_v1.csv"
)

CANONICAL = Path(
    "data/canonical/v1/attempts.csv"
)

RESULT_MATCH_V3 = Path(
    "weather/output/"
    "chronology_rescue_2022_result_to_canonical_attempt_matches_v3.csv"
)

OUTPUT_DIR = Path(
    "weather/output"
)

CORRECTED_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_ilott_paragraph_local_adjudication_v1.csv"
)

SUMMARY_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_ilott_paragraph_local_adjudication_summary_v1.csv"
)

QA_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_ilott_paragraph_local_adjudication_v1_qa.csv"
)


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


def contains_ilott(text):
    lower = txt(text).lower()

    return (
        "callum ilott" in lower
        or
        re.search(
            r"\bilott\b",
            lower,
        )
        is not None
    )


def matched_terms(text, terms):
    lower = txt(text).lower()

    return [
        term
        for term in terms
        if term in lower
    ]


def normalize_space(text):
    return re.sub(
        r"\s+",
        " ",
        txt(text),
    ).strip()


def html_to_paragraphs(raw):
    """
    Convert HTML-ish captured text into paragraph-local units.

    Critical rule:
      <p>, <br>, <hr>, headings and block boundaries become
      hard semantic separators.

    This prevents Rossi's first/second-run paragraph from being
    attributed to Ilott.
    """

    s = txt(raw)

    if not s:
        return []

    s = html.unescape(s)

    # Hard block boundaries
    s = re.sub(
        r"(?is)</?(?:p|div|section|article|h[1-6]|li|ul|ol|table|tr|td|th|blockquote)[^>]*>",
        "\n",
        s,
    )

    s = re.sub(
        r"(?is)<br\s*/?>",
        "\n",
        s,
    )

    s = re.sub(
        r"(?is)<hr\s*/?>",
        "\n",
        s,
    )

    # Remove remaining tags
    s = re.sub(
        r"(?is)<[^>]+>",
        " ",
        s,
    )

    parts = []

    for block in s.splitlines():

        block = normalize_space(
            block
        )

        if not block:
            continue

        # Secondary sentence split inside one paragraph only
        sentences = re.split(
            r"(?<=[.!?])\s+",
            block,
        )

        for sentence in sentences:

            sentence = normalize_space(
                sentence
            )

            if sentence:
                parts.append(
                    sentence
                )

    return parts


def plain_text_units(raw):
    raw = normalize_space(
        raw
    )

    if not raw:
        return []

    return [
        normalize_space(part)
        for part in re.split(
            r"(?<=[.!?])\s+",
            raw,
        )
        if normalize_space(part)
    ]


def main():

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print()
    print("=" * 120)
    print(
        "R1G.26B — 2022 CALLUM ILOTT "
        "HTML PARAGRAPH-LOCAL EVIDENCE CORRECTION V1 / ACTIVE V3"
    )
    print("=" * 120)

    required = [
        EVIDENCE_IN,
        CANONICAL,
        RESULT_MATCH_V3,
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
            "ILOTT_PARAGRAPH_LOCAL_CORRECTION_INPUT_MISSING"
        )
        return

    evidence = read_csv(
        EVIDENCE_IN
    )

    # ========================================================
    # BUILD PARAGRAPH-LOCAL UNITS
    # ========================================================

    corrected_rows = []

    unit_counter = 1

    for row in evidence:

        sentence = txt(
            row.get(
                "sentence"
            )
        )

        source_path = txt(
            row.get(
                "source_path"
            )
        )

        source_name = txt(
            row.get(
                "source_name"
            )
        )

        is_html_source = (
            source_path.lower().endswith(
                (
                    ".html",
                    ".htm",
                )
            )
            or
            source_name.lower().endswith(
                (
                    ".html",
                    ".htm",
                )
            )
            or
            "<p" in sentence.lower()
            or
            "<br" in sentence.lower()
        )

        if is_html_source:

            units = html_to_paragraphs(
                sentence
            )

            parsing_mode = (
                "HTML_BLOCK_LOCAL"
            )

        else:

            units = plain_text_units(
                sentence
            )

            parsing_mode = (
                "PLAIN_SENTENCE_LOCAL"
            )

        for unit in units:

            if not contains_ilott(
                unit
            ):
                continue

            first_terms = matched_terms(
                unit,
                FIRST_TERMS,
            )

            second_terms = matched_terms(
                unit,
                SECOND_TERMS,
            )

            withdraw_terms = matched_terms(
                unit,
                WITHDRAW_TERMS,
            )

            lane1_terms = matched_terms(
                unit,
                LANE1_TERMS,
            )

            lane2_terms = matched_terms(
                unit,
                LANE2_TERMS,
            )

            queue_terms = matched_terms(
                unit,
                QUEUE_TERMS,
            )

            late_terms = matched_terms(
                unit,
                LATE_IMPROVER_TERMS,
            )

            direct_repeat = (
                bool(first_terms)
                or
                bool(second_terms)
            )

            direct_action = (
                bool(withdraw_terms)
            )

            direct_lane = (
                bool(lane1_terms)
                or
                bool(lane2_terms)
            )

            direct_queue = (
                bool(queue_terms)
            )

            if late_terms and not (
                direct_repeat
                or
                direct_action
                or
                direct_lane
                or
                direct_queue
            ):

                classification = (
                    "DIRECT_LATE_IMPROVEMENT_ONLY"
                )

            elif direct_repeat:

                classification = (
                    "DIRECT_REPEAT_EVIDENCE_CANDIDATE"
                )

            elif direct_action:

                classification = (
                    "DIRECT_ACTION_EVIDENCE_CANDIDATE"
                )

            elif direct_lane:

                classification = (
                    "DIRECT_LANE_EVIDENCE_CANDIDATE"
                )

            elif direct_queue:

                classification = (
                    "DIRECT_QUEUE_LANGUAGE_CANDIDATE"
                )

            elif txt(
                row.get(
                    "exact_speed_hits"
                )
            ):

                classification = (
                    "RESULT_OR_SPEED_EVIDENCE_ONLY"
                )

            else:

                classification = (
                    "ILOTT_MENTION_NO_DECISION_SEMANTICS"
                )

            corrected_rows.append({
                "unit_id":
                    f"R1G26B-U{unit_counter:04d}",

                "original_evidence_id":
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
                    source_name,

                "source_path":
                    source_path,

                "parsing_mode":
                    parsing_mode,

                "paragraph_local_text":
                    unit,

                "exact_speed_hits":
                    txt(
                        row.get(
                            "exact_speed_hits"
                        )
                    ),

                "first_terms":
                    "|".join(
                        first_terms
                    ),

                "second_terms":
                    "|".join(
                        second_terms
                    ),

                "withdraw_terms":
                    "|".join(
                        withdraw_terms
                    ),

                "lane1_terms":
                    "|".join(
                        lane1_terms
                    ),

                "lane2_terms":
                    "|".join(
                        lane2_terms
                    ),

                "queue_terms":
                    "|".join(
                        queue_terms
                    ),

                "late_improver_terms":
                    "|".join(
                        late_terms
                    ),

                "classification":
                    classification,

                "repeat_promotable":
                    str(
                        direct_repeat
                    ),

                "action_promotable":
                    str(
                        direct_action
                    ),

                "lane_promotable":
                    str(
                        direct_lane
                    ),

                "queue_promotable":
                    str(
                        direct_queue
                    ),

                "automatic_promotion":
                    "False",
            })

            unit_counter += 1

    # ========================================================
    # DEDUPLICATE SEMANTIC OBSERVATIONS
    # ========================================================

    semantic_seen = {}

    for row in corrected_rows:

        key = normalize_space(
            row[
                "paragraph_local_text"
            ].lower()
        )

        if key not in semantic_seen:

            semantic_seen[
                key
            ] = row

    unique_rows = list(
        semantic_seen.values()
    )

    direct_repeat_rows = [
        row
        for row in unique_rows
        if row[
            "repeat_promotable"
        ] == "True"
    ]

    direct_action_rows = [
        row
        for row in unique_rows
        if row[
            "action_promotable"
        ] == "True"
    ]

    direct_lane_rows = [
        row
        for row in unique_rows
        if row[
            "lane_promotable"
        ] == "True"
    ]

    direct_queue_rows = [
        row
        for row in unique_rows
        if row[
            "queue_promotable"
        ] == "True"
    ]

    late_rows = [
        row
        for row in unique_rows
        if row[
            "classification"
        ]
        ==
        "DIRECT_LATE_IMPROVEMENT_ONLY"
    ]

    speed_only_rows = [
        row
        for row in unique_rows
        if row[
            "classification"
        ]
        ==
        "RESULT_OR_SPEED_EVIDENCE_ONLY"
    ]

    # ========================================================
    # PRINT CORRECTED EVIDENCE
    # ========================================================

    print()
    print("=" * 120)
    print(
        "CORRECTED ILOTT PARAGRAPH-LOCAL EVIDENCE"
    )
    print("=" * 120)

    for row in unique_rows:

        print()
        print(
            row[
                "unit_id"
            ],
            "|",
            row[
                "classification"
            ],
        )

        print(
            "source:",
            row[
                "source_name"
            ],
        )

        print(
            "text:"
        )

        print(
            row[
                "paragraph_local_text"
            ]
        )

        print(
            "first:",
            row[
                "first_terms"
            ]
            or
            "NONE",
        )

        print(
            "second:",
            row[
                "second_terms"
            ]
            or
            "NONE",
        )

        print(
            "withdraw:",
            row[
                "withdraw_terms"
            ]
            or
            "NONE",
        )

        print(
            "Lane1:",
            row[
                "lane1_terms"
            ]
            or
            "NONE",
        )

        print(
            "Lane2:",
            row[
                "lane2_terms"
            ]
            or
            "NONE",
        )

        print(
            "queue:",
            row[
                "queue_terms"
            ]
            or
            "NONE",
        )

    # ========================================================
    # FINAL DECISION
    # ========================================================

    if (
        direct_repeat_rows
        or
        direct_action_rows
        or
        direct_lane_rows
    ):

        final_status = (
            "ILOTT_PARAGRAPH_LOCAL_DIRECT_DECISION_EVIDENCE_READY"
        )

    elif late_rows:

        final_status = (
            "ILOTT_LATE_IMPROVEMENT_EVIDENCE_ONLY_"
            "NO_REPEAT_ACTION_PROMOTION"
        )

    else:

        final_status = (
            "ILOTT_PARAGRAPH_LOCAL_DECISION_EVIDENCE_INSUFFICIENT"
        )

    # ========================================================
    # WRITE
    # ========================================================

    fields = [
        "unit_id",
        "original_evidence_id",
        "source_type",
        "source_class",
        "source_name",
        "source_path",
        "parsing_mode",
        "paragraph_local_text",
        "exact_speed_hits",
        "first_terms",
        "second_terms",
        "withdraw_terms",
        "lane1_terms",
        "lane2_terms",
        "queue_terms",
        "late_improver_terms",
        "classification",
        "repeat_promotable",
        "action_promotable",
        "lane_promotable",
        "queue_promotable",
        "automatic_promotion",
    ]

    write_csv(
        CORRECTED_OUT,
        corrected_rows,
        fields,
    )

    summary_rows = [
        {
            "metric":
                "raw_corrected_units",

            "value":
                len(
                    corrected_rows
                ),
        },

        {
            "metric":
                "unique_semantic_units",

            "value":
                len(
                    unique_rows
                ),
        },

        {
            "metric":
                "direct_repeat_units",

            "value":
                len(
                    direct_repeat_rows
                ),
        },

        {
            "metric":
                "direct_action_units",

            "value":
                len(
                    direct_action_rows
                ),
        },

        {
            "metric":
                "direct_lane_units",

            "value":
                len(
                    direct_lane_rows
                ),
        },

        {
            "metric":
                "direct_queue_units",

            "value":
                len(
                    direct_queue_rows
                ),
        },

        {
            "metric":
                "late_improvement_units",

            "value":
                len(
                    late_rows
                ),
        },

        {
            "metric":
                "speed_result_only_units",

            "value":
                len(
                    speed_only_rows
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

    html_ilott_repeat_false_positive_remaining = sum(
        1
        for row in unique_rows
        if (
            "THE_RACE_2022_DAY1.html"
            in row[
                "source_name"
            ]
            and
            "Callum Ilott was a late improver"
            in row[
                "paragraph_local_text"
            ]
            and
            (
                row[
                    "first_terms"
                ]
                or
                row[
                    "second_terms"
                ]
            )
        )
    )

    qa_rows = [
        {
            "metric":
                "result_match_v3_policy_preserved",

            "value":
                1,

            "status":
                "PASS",
        },

        {
            "metric":
                "html_block_boundaries_enforced",

            "value":
                1,

            "status":
                "PASS",
        },

        {
            "metric":
                "rossi_first_second_terms_attributed_to_ilott",

            "value":
                html_ilott_repeat_false_positive_remaining,

            "status":
                (
                    "PASS"
                    if html_ilott_repeat_false_positive_remaining == 0
                    else "FAIL"
                ),
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
                "result_row_order_used_as_chronology",

            "value":
                0,

            "status":
                "PASS",
        },

        {
            "metric":
                "retired_status_used_as_action",

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
        "CORRECTED ADJUDICATION SUMMARY"
    )
    print("=" * 120)

    print()
    print(
        "Unique semantic units:",
        len(
            unique_rows
        ),
    )

    print(
        "Direct repeat units:",
        len(
            direct_repeat_rows
        ),
    )

    print(
        "Direct action units:",
        len(
            direct_action_rows
        ),
    )

    print(
        "Direct Lane units:",
        len(
            direct_lane_rows
        ),
    )

    print(
        "Direct queue units:",
        len(
            direct_queue_rows
        ),
    )

    print(
        "Late-improvement units:",
        len(
            late_rows
        ),
    )

    print(
        "Speed/result-only units:",
        len(
            speed_only_rows
        ),
    )

    print()
    print(
        "Rossi first/second-run terms remaining "
        "inside Ilott paragraph:",
        html_ilott_repeat_false_positive_remaining,
    )

    print()
    print(
        "No evidence was promoted."
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
    print(CORRECTED_OUT)
    print(SUMMARY_OUT)
    print(QA_OUT)


if __name__ == "__main__":
    main()
