from pathlib import Path
import csv
import re
from collections import defaultdict


# ============================================================
# PHASE
# ============================================================

PHASE = "R1G.17"


# ============================================================
# INPUTS
# ============================================================

PRIORITY = Path(
    "weather/output/"
    "chronology_rescue_2022_next_rescue_priority_v1.csv"
)

OFFICIAL_ARTICLE_DIR = Path(
    "weather/evidence/rescue/"
    "official_2022_editorial_chronology/article_text"
)

RESULT_MATCHES = Path(
    "weather/output/"
    "chronology_rescue_2022_result_to_canonical_attempt_matches_v3.csv"
)


# ============================================================
# OUTPUTS
# ============================================================

OUTPUT_DIR = Path(
    "weather/output"
)

CANDIDATES_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_high_priority_editorial_candidates_v1.csv"
)

TARGET_SUMMARY_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_high_priority_editorial_target_summary_v1.csv"
)

QA_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_high_priority_editorial_candidates_v1_qa.csv"
)


# ============================================================
# TARGETS
# ============================================================

TARGET_DRIVERS = {
    "Alexander Rossi": [
        "rossi",
        "alexander rossi",
    ],
    "Sage Karam": [
        "karam",
        "sage karam",
    ],
    "Marco Andretti": [
        "marco",
        "marco andretti",
        "andretti",
    ],
    "Helio Castroneves": [
        "castroneves",
        "helio",
        "hélio",
    ],
    "Takuma Sato": [
        "sato",
        "takuma sato",
    ],
    "Colton Herta": [
        "herta",
        "colton herta",
    ],
    "Stefan Wilson": [
        "wilson",
        "stefan wilson",
    ],
    "David Malukas": [
        "malukas",
        "david malukas",
    ],
    "Callum Ilott": [
        "ilott",
        "callum ilott",
    ],
}


ACTION_PATTERNS = {
    "WITHDRAW": [
        r"\bwithdrew\b",
        r"\bwithdrawn\b",
        r"\bwithdraw\b",
        r"\bgave up\b",
        r"\bsurrendered\b",
    ],
    "SECOND_ATTEMPT": [
        r"\bsecond attempt\b",
        r"\bsecond run\b",
        r"\banother attempt\b",
        r"\banother run\b",
        r"\bre-ran\b",
        r"\breran\b",
        r"\breturned\b",
        r"\bwent back out\b",
    ],
    "IMPROVE": [
        r"\bimproved\b",
        r"\bimprove\b",
        r"\bfaster\b",
        r"\bslower\b",
        r"\bunable to improve\b",
        r"\bfailed to improve\b",
        r"\bdropped\b",
    ],
    "LANE": [
        r"\blane 1\b",
        r"\blane one\b",
        r"\blane 2\b",
        r"\blane two\b",
        r"\bpriority lane\b",
        r"\bpriority queue\b",
    ],
    "WEATHER": [
        r"\brain\b",
        r"\blightning\b",
        r"\bweather\b",
        r"\bdelay\b",
        r"\bhold\b",
        r"\bresumed\b",
        r"\brestart\b",
        r"\breopened\b",
    ],
    "WAVED_OFF": [
        r"\bwaved off\b",
        r"\bwave off\b",
    ],
    "INCOMPLETE": [
        r"\bincomplete\b",
        r"\bdid not complete\b",
        r"\bfailed to complete\b",
    ],
    "RETIRED": [
        r"\bretired\b",
    ],
    "FAILED_ATTEMPT": [
        r"\bfailed attempt\b",
        r"\bdisallowed\b",
        r"\binvalidated\b",
        r"\bpenalized\b",
    ],
}


TIME_PATTERN = re.compile(
    r"\b("
    r"(?:1[0-2]|[1-9]):[0-5][0-9]\s*(?:a\.?m\.?|p\.?m\.?)"
    r"|"
    r"(?:1[0-2]|[1-9])\s*(?:a\.?m\.?|p\.?m\.?)"
    r")\b",
    flags=re.IGNORECASE,
)


RELATIVE_PATTERNS = [
    r"\bafter\b",
    r"\bbefore\b",
    r"\bthen\b",
    r"\bnext\b",
    r"\blater\b",
    r"\bsubsequently\b",
    r"\bshortly after\b",
    r"\bshortly before\b",
    r"\bonce\b",
    r"\bwhen\b",
]


# ============================================================
# HELPERS
# ============================================================

def read_csv(path):
    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as f:
        return list(
            csv.DictReader(f)
        )


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


def normalize_space(s):
    return re.sub(
        r"\s+",
        " ",
        s,
    ).strip()


def split_sentences(text):
    text = text.replace(
        "\r",
        "\n",
    )

    chunks = re.split(
        r"(?<=[.!?])\s+|\n+",
        text,
    )

    return [
        normalize_space(chunk)
        for chunk in chunks
        if normalize_space(chunk)
    ]


def detect_driver(sentence):
    lower = sentence.lower()

    matches = []

    for driver, variants in TARGET_DRIVERS.items():

        for variant in variants:

            if variant.lower() in lower:
                matches.append(driver)
                break

    return sorted(
        set(matches)
    )


def detect_actions(sentence):
    lower = sentence.lower()

    found = []

    for label, patterns in ACTION_PATTERNS.items():

        if any(
            re.search(
                pattern,
                lower,
                flags=re.IGNORECASE,
            )
            for pattern in patterns
        ):
            found.append(label)

    return found


def detect_relative_terms(sentence):
    lower = sentence.lower()

    found = []

    for pattern in RELATIVE_PATTERNS:

        m = re.search(
            pattern,
            lower,
            flags=re.IGNORECASE,
        )

        if m:
            found.append(
                m.group(0)
            )

    return sorted(
        set(found)
    )


def source_name(path):
    return path.stem


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
        "R1G.17 — 2022 HIGH-PRIORITY "
        "EDITORIAL/SOURCE TARGET MINING V1"
    )
    print("=" * 120)

    inputs = [
        PRIORITY,
        RESULT_MATCHES,
    ]

    missing = []

    for path in inputs:

        exists = path.exists()

        print(
            f"{path}: "
            f"{'PRESENT' if exists else 'MISSING'}"
        )

        if not exists:
            missing.append(path)

    print(
        f"{OFFICIAL_ARTICLE_DIR}: "
        f"{'PRESENT' if OFFICIAL_ARTICLE_DIR.exists() else 'MISSING'}"
    )

    if not OFFICIAL_ARTICLE_DIR.exists():
        missing.append(
            OFFICIAL_ARTICLE_DIR
        )

    if missing:

        print()
        print(
            "FINAL STATUS: "
            "2022_HIGH_PRIORITY_EDITORIAL_MINING_INPUT_MISSING"
        )

        return

    priority_rows = read_csv(
        PRIORITY
    )

    result_rows = read_csv(
        RESULT_MATCHES
    )

    high_priority = [
        row
        for row in priority_rows
        if txt(
            row.get(
                "rescue_priority"
            )
        ) == "HIGH"
    ]

    print()
    print(
        "HIGH-PRIORITY ATTEMPT TARGETS:",
        len(
            high_priority
        ),
    )

    # ========================================================
    # TARGET LOOKUPS
    # ========================================================

    attempts_by_driver = defaultdict(
        list
    )

    for row in high_priority:

        driver = txt(
            row.get(
                "driver_name"
            )
        )

        attempts_by_driver[
            driver
        ].append(
            row
        )

    result_by_attempt = {
        txt(
            row.get(
                "attempt_id"
            )
        ):
        row
        for row in result_rows
        if txt(
            row.get(
                "attempt_id"
            )
        )
    }

    # ========================================================
    # MINE OFFICIAL LOCAL TEXT
    # ========================================================

    candidate_rows = []

    candidate_id = 1

    text_files = sorted(
        OFFICIAL_ARTICLE_DIR.glob(
            "*.txt"
        )
    )

    print(
        "OFFICIAL TEXT FILES:",
        len(
            text_files
        ),
    )

    for path in text_files:

        content = path.read_text(
            encoding="utf-8",
            errors="replace",
        )

        sentences = split_sentences(
            content
        )

        for sentence_index, sentence in enumerate(
            sentences,
            start=1,
        ):

            drivers = detect_driver(
                sentence
            )

            if not drivers:
                continue

            actions = detect_actions(
                sentence
            )

            times = TIME_PATTERN.findall(
                sentence
            )

            relatives = detect_relative_terms(
                sentence
            )

            # Keep only chronology/action-relevant sentences.
            if not (
                actions
                or
                times
                or
                relatives
            ):
                continue

            for driver in drivers:

                if driver not in attempts_by_driver:
                    continue

                target_attempts = attempts_by_driver[
                    driver
                ]

                candidate_rows.append({
                    "candidate_id":
                        f"R1G17-C{candidate_id:04d}",

                    "source_class":
                        "INDYCAR_OFFICIAL_EDITORIAL",

                    "source_file":
                        str(path),

                    "source_name":
                        source_name(
                            path
                        ),

                    "sentence_index":
                        sentence_index,

                    "driver_name":
                        driver,

                    "candidate_sentence":
                        sentence,

                    "detected_actions":
                        "|".join(
                            actions
                        ),

                    "detected_times":
                        "|".join(
                            times
                        ),

                    "detected_relative_terms":
                        "|".join(
                            relatives
                        ),

                    "target_attempt_count":
                        len(
                            target_attempts
                        ),

                    "target_attempt_ids":
                        "|".join(
                            txt(
                                row.get(
                                    "attempt_id"
                                )
                            )
                            for row in target_attempts
                        ),

                    "target_official_statuses":
                        "|".join(
                            sorted(
                                set(
                                    txt(
                                        row.get(
                                            "official_status"
                                        )
                                    )
                                    for row in target_attempts
                                )
                            )
                        ),

                    "promotion_status":
                        "REVIEW_REQUIRED",

                    "notes":
                        (
                            "Discovery candidate only. "
                            "No chronology promotion performed."
                        ),
                })

                candidate_id += 1

    # ========================================================
    # SCORE CANDIDATES
    # ========================================================

    for row in candidate_rows:

        score = 0

        actions = set(
            filter(
                None,
                txt(
                    row.get(
                        "detected_actions"
                    )
                ).split("|"),
            )
        )

        times = txt(
            row.get(
                "detected_times"
            )
        )

        relatives = txt(
            row.get(
                "detected_relative_terms"
            )
        )

        if "WITHDRAW" in actions:
            score += 5

        if "SECOND_ATTEMPT" in actions:
            score += 5

        if "LANE" in actions:
            score += 6

        if "WEATHER" in actions:
            score += 3

        if "WAVED_OFF" in actions:
            score += 5

        if "INCOMPLETE" in actions:
            score += 5

        if "RETIRED" in actions:
            score += 4

        if "FAILED_ATTEMPT" in actions:
            score += 5

        if "IMPROVE" in actions:
            score += 3

        if times:
            score += 4

        if relatives:
            score += 2

        row[
            "candidate_score"
        ] = score

        if score >= 10:

            row[
                "candidate_priority"
            ] = "HIGH"

        elif score >= 6:

            row[
                "candidate_priority"
            ] = "MEDIUM"

        else:

            row[
                "candidate_priority"
            ] = "LOW"

    candidate_rows.sort(
        key=lambda row: (
            {
                "HIGH": 0,
                "MEDIUM": 1,
                "LOW": 2,
            }.get(
                row[
                    "candidate_priority"
                ],
                9,
            ),
            -int(
                row[
                    "candidate_score"
                ]
            ),
            row[
                "driver_name"
            ],
            row[
                "source_name"
            ],
            int(
                row[
                    "sentence_index"
                ]
            ),
        )
    )

    # ========================================================
    # TARGET SUMMARY
    # ========================================================

    candidate_by_driver = defaultdict(
        list
    )

    for row in candidate_rows:

        candidate_by_driver[
            row[
                "driver_name"
            ]
        ].append(
            row
        )

    summary_rows = []

    for driver in sorted(
        attempts_by_driver
    ):

        attempts = attempts_by_driver[
            driver
        ]

        candidates = candidate_by_driver.get(
            driver,
            [],
        )

        high_candidates = [
            row
            for row in candidates
            if row[
                "candidate_priority"
            ] == "HIGH"
        ]

        medium_candidates = [
            row
            for row in candidates
            if row[
                "candidate_priority"
            ] == "MEDIUM"
        ]

        summary_rows.append({
            "driver_name":
                driver,

            "high_priority_attempt_targets":
                len(
                    attempts
                ),

            "attempt_ids":
                "|".join(
                    txt(
                        row.get(
                            "attempt_id"
                        )
                    )
                    for row in attempts
                ),

            "official_statuses":
                "|".join(
                    sorted(
                        set(
                            txt(
                                row.get(
                                    "official_status"
                                )
                            )
                            for row in attempts
                        )
                    )
                ),

            "candidate_sentences":
                len(
                    candidates
                ),

            "high_value_candidates":
                len(
                    high_candidates
                ),

            "medium_value_candidates":
                len(
                    medium_candidates
                ),

            "best_candidate_score":
                max(
                    [
                        int(
                            row[
                                "candidate_score"
                            ]
                        )
                        for row in candidates
                    ],
                    default=0,
                ),
        })

    # ========================================================
    # PRINT
    # ========================================================

    print()
    print("=" * 120)
    print(
        "TARGET CANDIDATE SUMMARY"
    )
    print("=" * 120)

    for row in summary_rows:

        print()
        print(
            row[
                "driver_name"
            ]
        )

        print(
            "  attempt targets:",
            row[
                "high_priority_attempt_targets"
            ],
        )

        print(
            "  candidate sentences:",
            row[
                "candidate_sentences"
            ],
        )

        print(
            "  high-value candidates:",
            row[
                "high_value_candidates"
            ],
        )

        print(
            "  medium-value candidates:",
            row[
                "medium_value_candidates"
            ],
        )

        print(
            "  best score:",
            row[
                "best_candidate_score"
            ],
        )

    top_candidates = [
        row
        for row in candidate_rows
        if row[
            "candidate_priority"
        ] in {
            "HIGH",
            "MEDIUM",
        }
    ]

    print()
    print("=" * 120)
    print(
        "TOP EDITORIAL CANDIDATES"
    )
    print("=" * 120)

    for row in top_candidates[:40]:

        print()
        print(
            row[
                "candidate_id"
            ],
            "|",
            row[
                "candidate_priority"
            ],
            "| score=",
            row[
                "candidate_score"
            ],
        )

        print(
            "driver:",
            row[
                "driver_name"
            ],
        )

        print(
            "source:",
            row[
                "source_name"
            ],
        )

        print(
            "actions:",
            row[
                "detected_actions"
            ],
        )

        print(
            "times:",
            row[
                "detected_times"
            ],
        )

        print(
            "relative:",
            row[
                "detected_relative_terms"
            ],
        )

        print(
            "sentence:"
        )

        print(
            row[
                "candidate_sentence"
            ]
        )

    # ========================================================
    # QA
    # ========================================================

    duplicate_candidate_ids = len(
        candidate_rows
    ) - len(
        {
            row[
                "candidate_id"
            ]
            for row in candidate_rows
        }
    )

    qa_rows = [
        {
            "metric":
                "high_priority_attempt_targets",
            "value":
                len(
                    high_priority
                ),
            "status":
                (
                    "PASS"
                    if len(
                        high_priority
                    ) > 0
                    else "FAIL"
                ),
        },
        {
            "metric":
                "official_text_files_scanned",
            "value":
                len(
                    text_files
                ),
            "status":
                (
                    "PASS"
                    if len(
                        text_files
                    ) > 0
                    else "FAIL"
                ),
        },
        {
            "metric":
                "candidate_sentences",
            "value":
                len(
                    candidate_rows
                ),
            "status":
                "INFO",
        },
        {
            "metric":
                "high_value_candidates",
            "value":
                sum(
                    1
                    for row in candidate_rows
                    if row[
                        "candidate_priority"
                    ] == "HIGH"
                ),
            "status":
                "INFO",
        },
        {
            "metric":
                "duplicate_candidate_ids",
            "value":
                duplicate_candidate_ids,
            "status":
                (
                    "PASS"
                    if duplicate_candidate_ids == 0
                    else "FAIL"
                ),
        },
        {
            "metric":
                "auto_promotions",
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

    # ========================================================
    # WRITE
    # ========================================================

    candidate_fields = [
        "candidate_id",
        "source_class",
        "source_file",
        "source_name",
        "sentence_index",
        "driver_name",
        "candidate_sentence",
        "detected_actions",
        "detected_times",
        "detected_relative_terms",
        "target_attempt_count",
        "target_attempt_ids",
        "target_official_statuses",
        "candidate_score",
        "candidate_priority",
        "promotion_status",
        "notes",
    ]

    write_csv(
        CANDIDATES_OUT,
        candidate_rows,
        candidate_fields,
    )

    write_csv(
        TARGET_SUMMARY_OUT,
        summary_rows,
        [
            "driver_name",
            "high_priority_attempt_targets",
            "attempt_ids",
            "official_statuses",
            "candidate_sentences",
            "high_value_candidates",
            "medium_value_candidates",
            "best_candidate_score",
        ],
    )

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

    high_value_total = sum(
        1
        for row in candidate_rows
        if row[
            "candidate_priority"
        ] == "HIGH"
    )

    medium_value_total = sum(
        1
        for row in candidate_rows
        if row[
            "candidate_priority"
        ] == "MEDIUM"
    )

    print()
    print("=" * 120)
    print(
        "FINAL SUMMARY"
    )
    print("=" * 120)

    print()
    print(
        "High-priority attempt targets:",
        len(
            high_priority
        ),
    )

    print(
        "Official text files scanned:",
        len(
            text_files
        ),
    )

    print(
        "Candidate sentences:",
        len(
            candidate_rows
        ),
    )

    print(
        "High-value candidates:",
        high_value_total,
    )

    print(
        "Medium-value candidates:",
        medium_value_total,
    )

    print()
    print(
        "No candidate was promoted automatically."
    )

    print(
        "No result-row ordering was used as chronology."
    )

    print(
        "No queue wait was inferred."
    )

    print(
        "No canonical data was modified."
    )

    print()
    print("=" * 120)

    if (
        len(
            high_priority
        ) > 0
        and
        len(
            text_files
        ) > 0
        and
        duplicate_candidate_ids == 0
    ):

        print(
            "FINAL STATUS: "
            "2022_HIGH_PRIORITY_EDITORIAL_TARGET_MINING_COMPLETE"
        )

    else:

        print(
            "FINAL STATUS: "
            "2022_HIGH_PRIORITY_EDITORIAL_TARGET_MINING_REVIEW_REQUIRED"
        )

    print("=" * 120)

    print()
    print("OUTPUTS")
    print(CANDIDATES_OUT)
    print(TARGET_SUMMARY_OUT)
    print(QA_OUT)


if __name__ == "__main__":
    main()
