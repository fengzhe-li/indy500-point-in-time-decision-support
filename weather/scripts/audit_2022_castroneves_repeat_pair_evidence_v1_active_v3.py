from pathlib import Path
import csv
import re


CANONICAL = Path(
    "data/canonical/v1/attempts.csv"
)

RESULT_MATCHES = Path(
    "weather/output/"
    "chronology_rescue_2022_result_to_canonical_attempt_matches_v3.csv"
)

OFFICIAL_DIR = Path(
    "weather/evidence/rescue/"
    "official_2022_editorial_chronology/article_text"
)

SECONDARY_DIR = Path(
    "weather/evidence/rescue/"
    "secondary_2022_high_priority_chronology/article_text"
)

OUTPUT_DIR = Path("weather/output")

EVIDENCE_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_castroneves_repeat_pair_evidence_v1.csv"
)

AUDIT_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_castroneves_repeat_pair_audit_v1.csv"
)

QA_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_castroneves_repeat_pair_audit_v1_qa.csv"
)


TARGET_TERMS = [
    "castroneves",
    "helio",
    "hélio",
]

ACTION_TERMS = [
    "first run",
    "second run",
    "second attempt",
    "another run",
    "returned",
    "went back out",
    "improved",
    "improve",
    "withdrew",
    "withdrawn",
    "bailed out",
    "bailing out",
    "aborted",
    "balance",
    "conditions",
    "later",
]


def read_csv(path):
    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as f:
        return list(csv.DictReader(f))


def write_csv(path, rows, fields):
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


def txt(v):
    return "" if v is None else str(v).strip()


def norm_car(v):
    value = txt(v)
    try:
        return str(int(float(value)))
    except Exception:
        return value.lstrip("0") or "0"


def speed_close(a, b, tol=0.003):
    try:
        return abs(
            float(txt(a)) - float(txt(b))
        ) <= tol
    except Exception:
        return False


def split_sentences(text):
    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return [
        x.strip()
        for x in re.split(
            r"(?<=[.!?])\s+",
            text,
        )
        if x.strip()
    ]


def has_target(text):
    lower = text.lower()
    return any(
        term in lower
        for term in TARGET_TERMS
    )


def matched_actions(text):
    lower = text.lower()
    return [
        term
        for term in ACTION_TERMS
        if term in lower
    ]


def main():

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print()
    print("=" * 120)
    print(
        "R1G.24 — 2022 HELIO CASTRONEVES "
        "REPEAT-PAIR TARGETED EVIDENCE AUDIT V1"
    )
    print("=" * 120)

    required = [
        CANONICAL,
        RESULT_MATCHES,
    ]

    missing = []

    for path in required:
        exists = path.exists()
        print(
            f"{path}: "
            f"{'PRESENT' if exists else 'MISSING'}"
        )
        if not exists:
            missing.append(path)

    print(
        f"{OFFICIAL_DIR}: "
        f"{'PRESENT' if OFFICIAL_DIR.exists() else 'MISSING_OPTIONAL'}"
    )

    print(
        f"{SECONDARY_DIR}: "
        f"{'PRESENT' if SECONDARY_DIR.exists() else 'MISSING_OPTIONAL'}"
    )

    if missing:
        print()
        print(
            "FINAL STATUS: "
            "CASTRONEVES_REPEAT_PAIR_AUDIT_INPUT_MISSING"
        )
        return

    canonical = read_csv(CANONICAL)
    results = read_csv(RESULT_MATCHES)

    result_rows = [
        row
        for row in results
        if norm_car(
            row.get("car_number")
        ) == "6"
    ]

    first_rows = [
        row
        for row in result_rows
        if speed_close(
            row.get("official_speed_mph"),
            "225.482",
        )
    ]

    second_rows = [
        row
        for row in result_rows
        if speed_close(
            row.get("official_speed_mph"),
            "229.630",
        )
    ]

    print()
    print("=" * 120)
    print("CANONICAL TARGET CHECK")
    print("=" * 120)

    print(
        "225.482 rows:",
        len(first_rows),
    )

    print(
        "229.630 rows:",
        len(second_rows),
    )

    if not (
        len(first_rows) == 1
        and
        len(second_rows) == 1
    ):
        print()
        print(
            "FINAL STATUS: "
            "CASTRONEVES_REPEAT_PAIR_STRUCTURE_REVIEW_REQUIRED"
        )
        return

    first_id = txt(
        first_rows[0].get("attempt_id")
    )

    second_id = txt(
        second_rows[0].get("attempt_id")
    )

    print(
        "first attempt_id:",
        first_id,
    )

    print(
        "second attempt_id:",
        second_id,
    )

    evidence_rows = []

    source_specs = []

    if OFFICIAL_DIR.exists():
        for path in sorted(
            OFFICIAL_DIR.glob("*.txt")
        ):
            source_specs.append({
                "source_class":
                    "INDYCAR_OFFICIAL_EDITORIAL",
                "source_name":
                    path.stem,
                "path":
                    path,
            })

    if SECONDARY_DIR.exists():
        for path in sorted(
            SECONDARY_DIR.glob("*.txt")
        ):

            source_name = path.stem

            source_class = (
                "REPUTABLE_SECONDARY_EDITORIAL"
            )

            source_specs.append({
                "source_class":
                    source_class,
                "source_name":
                    source_name,
                "path":
                    path,
            })

    print()
    print(
        "TEXT SOURCES TO SCAN:",
        len(source_specs),
    )

    evidence_id = 1

    for spec in source_specs:

        text = spec[
            "path"
        ].read_text(
            encoding="utf-8",
            errors="replace",
        )

        sentences = split_sentences(text)

        for idx, sentence in enumerate(
            sentences,
            start=1,
        ):

            if not has_target(sentence):
                continue

            actions = matched_actions(
                sentence
            )

            if not actions:
                continue

            start = max(
                0,
                idx - 2,
            )

            end = min(
                len(sentences),
                idx + 1,
            )

            context = " ".join(
                sentences[
                    start:end
                ]
            )

            evidence_rows.append({
                "evidence_id":
                    f"R1G24-C{evidence_id:04d}",

                "source_class":
                    spec[
                        "source_class"
                    ],

                "source_name":
                    spec[
                        "source_name"
                    ],

                "source_file":
                    str(
                        spec[
                            "path"
                        ]
                    ),

                "sentence_index":
                    idx,

                "sentence":
                    sentence,

                "context":
                    context,

                "detected_actions":
                    "|".join(
                        actions
                    ),

                "mentions_225_482":
                    "225.482"
                    in context,

                "mentions_229_630":
                    (
                        "229.630"
                        in context
                        or
                        "229.63"
                        in context
                    ),

                "mentions_first_run":
                    "first run"
                    in context.lower(),

                "mentions_second_run":
                    (
                        "second run"
                        in context.lower()
                        or
                        "second attempt"
                        in context.lower()
                    ),

                "mentions_withdraw":
                    (
                        "withdrew"
                        in context.lower()
                        or
                        "withdrawn"
                        in context.lower()
                    ),

                "mentions_bail_abort":
                    any(
                        term
                        in context.lower()
                        for term in [
                            "bailed out",
                            "bailing out",
                            "aborted",
                        ]
                    ),

                "promotion_status":
                    "REVIEW_REQUIRED",

                "notes":
                    (
                        "Discovery only. "
                        "No chronology/action promotion performed."
                    ),
            })

            evidence_id += 1

    print()
    print("=" * 120)
    print("CASTRONEVES EVIDENCE CANDIDATES")
    print("=" * 120)

    print()
    print(
        "Candidate rows:",
        len(evidence_rows),
    )

    for row in evidence_rows:

        print()
        print(
            row["evidence_id"],
            "|",
            row["source_name"],
        )

        print(
            "actions:",
            row[
                "detected_actions"
            ],
        )

        print(
            "225.482:",
            row[
                "mentions_225_482"
            ],
            "| 229.630:",
            row[
                "mentions_229_630"
            ],
        )

        print(
            "sentence:"
        )

        print(
            row[
                "sentence"
            ]
        )

    # ========================================================
    # PROMOTION READINESS
    # ========================================================

    direct_first = [
        row
        for row in evidence_rows
        if (
            row[
                "mentions_225_482"
            ]
            and
            (
                row[
                    "mentions_first_run"
                ]
                or
                row[
                    "mentions_bail_abort"
                ]
                or
                row[
                    "mentions_withdraw"
                ]
            )
        )
    ]

    direct_second = [
        row
        for row in evidence_rows
        if (
            row[
                "mentions_229_630"
            ]
            and
            row[
                "mentions_second_run"
            ]
        )
    ]

    ordering_candidates = [
        row
        for row in evidence_rows
        if (
            row[
                "mentions_first_run"
            ]
            and
            row[
                "mentions_second_run"
            ]
        )
    ]

    print()
    print("=" * 120)
    print("PROMOTION READINESS")
    print("=" * 120)

    print()
    print(
        "Direct first-attempt identity candidates:",
        len(direct_first),
    )

    print(
        "Direct second-attempt identity candidates:",
        len(direct_second),
    )

    print(
        "Direct first->second ordering candidates:",
        len(ordering_candidates),
    )

    promotion_ready = (
        len(ordering_candidates) >= 1
        or
        (
            len(direct_first) >= 1
            and
            len(direct_second) >= 1
        )
    )

    if promotion_ready:
        final_status = (
            "CASTRONEVES_REPEAT_PAIR_ADJUDICATION_READY"
        )
    else:
        final_status = (
            "CASTRONEVES_REPEAT_PAIR_EVIDENCE_INSUFFICIENT"
        )

    audit_rows = [
        {
            "metric":
                "first_attempt_unique",
            "value":
                len(first_rows),
        },
        {
            "metric":
                "second_attempt_unique",
            "value":
                len(second_rows),
        },
        {
            "metric":
                "candidate_rows",
            "value":
                len(evidence_rows),
        },
        {
            "metric":
                "direct_first_identity_candidates",
            "value":
                len(direct_first),
        },
        {
            "metric":
                "direct_second_identity_candidates",
            "value":
                len(direct_second),
        },
        {
            "metric":
                "ordering_candidates",
            "value":
                len(ordering_candidates),
        },
        {
            "metric":
                "promotion_ready",
            "value":
                int(
                    promotion_ready
                ),
        },
    ]

    write_csv(
        EVIDENCE_OUT,
        evidence_rows,
        [
            "evidence_id",
            "source_class",
            "source_name",
            "source_file",
            "sentence_index",
            "sentence",
            "context",
            "detected_actions",
            "mentions_225_482",
            "mentions_229_630",
            "mentions_first_run",
            "mentions_second_run",
            "mentions_withdraw",
            "mentions_bail_abort",
            "promotion_status",
            "notes",
        ],
    )

    write_csv(
        AUDIT_OUT,
        audit_rows,
        [
            "metric",
            "value",
        ],
    )

    qa_rows = [
        {
            "metric":
                "first_attempt_unique",
            "value":
                len(first_rows),
            "status":
                (
                    "PASS"
                    if len(first_rows) == 1
                    else "FAIL"
                ),
        },
        {
            "metric":
                "second_attempt_unique",
            "value":
                len(second_rows),
            "status":
                (
                    "PASS"
                    if len(second_rows) == 1
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
                "queue_wait_inferred",
            "value":
                0,
            "status":
                "PASS",
        },
        {
            "metric":
                "canonical_data_mutated",
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

    print()
    print("=" * 120)
    print("FINAL SUMMARY")
    print("=" * 120)

    print()
    print(
        "Castroneves first attempt:",
        first_id,
        "| 225.482",
    )

    print(
        "Castroneves second attempt:",
        second_id,
        "| 229.630",
    )

    print(
        "Candidate evidence rows:",
        len(evidence_rows),
    )

    print(
        "Promotion-ready:",
        promotion_ready,
    )

    print()
    print(
        "No chronology/action was promoted automatically."
    )

    print(
        "No result-row ordering was used."
    )

    print(
        "No queue wait was inferred."
    )

    print(
        "No canonical data was modified."
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
    print(EVIDENCE_OUT)
    print(AUDIT_OUT)
    print(QA_OUT)


if __name__ == "__main__":
    main()
