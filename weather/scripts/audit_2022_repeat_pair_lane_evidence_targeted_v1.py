from pathlib import Path
import csv
import re
from collections import defaultdict


PHASE = "R2B.1"

ELIGIBILITY = Path(
    "weather/output/"
    "chronology_rescue_2022_repeat_pair_driver_eligibility_v1.csv"
)

CHRONOLOGY_V10 = Path(
    "weather/output/"
    "unified_attempt_chronology_constraint_ledger_v10.csv"
)

ACTION_V7 = Path(
    "weather/output/"
    "unified_attempt_action_lane_ledger_v7.csv"
)

OUTPUT_DIR = Path("weather/output")

HITS_OUT = (
    OUTPUT_DIR
    / "lane_rescue_2022_repeat_pair_targeted_hits_v1.csv"
)

DRIVER_SUMMARY_OUT = (
    OUTPUT_DIR
    / "lane_rescue_2022_repeat_pair_targeted_driver_summary_v1.csv"
)

QA_OUT = (
    OUTPUT_DIR
    / "lane_rescue_2022_repeat_pair_targeted_v1_qa.csv"
)


SEARCH_ROOTS = [
    Path(
        "weather/evidence/rescue/"
        "official_2022_editorial_chronology"
    ),
    Path(
        "weather/evidence/rescue/"
        "secondary_2022_high_priority_chronology"
    ),
    Path(
        "weather/evidence/rescue/"
        "official_day1_session_details"
    ),
    Path(
        "weather/evidence/rescue"
    ),
]

TEXT_EXTENSIONS = {
    ".txt",
    ".md",
    ".html",
    ".htm",
    ".csv",
    ".json",
}


LANE_PATTERNS = [
    r"\blane\s*1\b",
    r"\blane\s*one\b",
    r"\blane\s*2\b",
    r"\blane\s*two\b",
    r"\bpriority\s+lane\b",
    r"\bnon[- ]priority\s+lane\b",
    r"\bfast\s+lane\b",
    r"\bpriority\s+queue\b",
]

QUEUE_PATTERNS = [
    r"\bfront\s+of\s+the\s+lane\s*1\s+queue\b",
    r"\blane\s*1\s+queue\b",
    r"\blane\s*2\s+queue\b",
    r"\bqueue\b",
    r"\brequeue\b",
    r"\bre-queue\b",
]

ACTION_PATTERNS = [
    r"\bgave\s+up\b",
    r"\bgive\s+up\b",
    r"\bgave\s+up\s+his\s+time\b",
    r"\bgave\s+up\s+the\s+time\b",
    r"\bwithdraw(?:n|al)?\b",
    r"\bwithdrew\b",
    r"\bretain(?:ed)?\b",
    r"\bkept\s+his\s+time\b",
]


EXPECTED_DRIVERS = {
    "Alexander Rossi",
    "Callum Ilott",
    "David Malukas",
    "Helio Castroneves",
    "Marco Andretti",
    "Sage Karam",
    "Scott McLaughlin",
    "Takuma Sato",
}


ALIASES = {
    "Alexander Rossi": [
        "Alexander Rossi",
        "Rossi",
    ],
    "Callum Ilott": [
        "Callum Ilott",
        "Ilott",
    ],
    "David Malukas": [
        "David Malukas",
        "Malukas",
    ],
    "Helio Castroneves": [
        "Helio Castroneves",
        "Hélio Castroneves",
        "Castroneves",
    ],
    "Marco Andretti": [
        "Marco Andretti",
        "Andretti",
    ],
    "Sage Karam": [
        "Sage Karam",
        "Karam",
    ],
    "Scott McLaughlin": [
        "Scott McLaughlin",
        "McLaughlin",
    ],
    "Takuma Sato": [
        "Takuma Sato",
        "Sato",
    ],
}


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


def normalize(text):
    return re.sub(
        r"\s+",
        " ",
        txt(text),
    ).strip()


def safe_read(path):
    try:
        return path.read_text(
            encoding="utf-8",
            errors="replace",
        )
    except Exception:
        return ""


def strip_html(text):
    return re.sub(
        r"(?is)<[^>]+>",
        " ",
        text,
    )


def split_units(raw):
    raw = strip_html(raw)

    raw = raw.replace(
        "\r",
        "\n",
    )

    raw = re.sub(
        r"\n+",
        "\n",
        raw,
    )

    chunks = []

    for paragraph in raw.split("\n"):

        paragraph = normalize(
            paragraph
        )

        if not paragraph:
            continue

        parts = re.split(
            r"(?<=[.!?])\s+",
            paragraph,
        )

        for part in parts:
            part = normalize(
                part
            )

            if part:
                chunks.append(
                    part
                )

    return chunks


def source_class(path):
    lower = str(path).lower()

    if (
        "official_2022_editorial_chronology"
        in lower
    ):
        return "INDYCAR_OFFICIAL_EDITORIAL"

    if (
        "secondary_2022_high_priority_chronology"
        in lower
    ):
        if "autosport" in lower:
            return "SECONDARY_AUTOSPORT"

        if (
            "the_race"
            in lower
            or
            "therace"
            in lower
        ):
            return "SECONDARY_THE_RACE"

        if "nbc" in lower:
            return "SECONDARY_NBC"

        return "SECONDARY_EDITORIAL"

    if (
        "official_day1_session_details"
        in lower
    ):
        return "INDYCAR_OFFICIAL_RESULTS_OR_API"

    if "/output/" in lower:
        return "DERIVED_OUTPUT"

    return "OTHER_LOCAL_EVIDENCE"


def source_native(source):
    return source in {
        "INDYCAR_OFFICIAL_EDITORIAL",
        "SECONDARY_AUTOSPORT",
        "SECONDARY_THE_RACE",
        "SECONDARY_NBC",
        "SECONDARY_EDITORIAL",
    }


def regex_hits(text, patterns):
    hits = []

    for pattern in patterns:
        for match in re.finditer(
            pattern,
            text,
            flags=re.I,
        ):
            hits.append({
                "match":
                    match.group(0),

                "start":
                    match.start(),

                "end":
                    match.end(),
            })

    return hits


def driver_mentions(text, driver):
    mentions = []

    for alias in ALIASES[driver]:

        pattern = (
            r"(?<![A-Za-z])"
            +
            re.escape(alias)
            +
            r"(?![A-Za-z])"
        )

        for match in re.finditer(
            pattern,
            text,
            flags=re.I,
        ):
            mentions.append({
                "alias":
                    alias,

                "start":
                    match.start(),

                "end":
                    match.end(),
            })

    return mentions


def all_driver_mentions(text):
    result = {}

    for driver in EXPECTED_DRIVERS:
        mentions = driver_mentions(
            text,
            driver,
        )

        if mentions:
            result[driver] = mentions

    return result


def interval_distance(a_start, a_end, b_start, b_end):
    if a_end < b_start:
        return b_start - a_end

    if b_end < a_start:
        return a_start - b_end

    return 0


def nearest_driver_to_lane(
    driver_map,
    lane_hit,
):
    distances = []

    for driver, mentions in driver_map.items():

        best = min(
            interval_distance(
                mention["start"],
                mention["end"],
                lane_hit["start"],
                lane_hit["end"],
            )
            for mention in mentions
        )

        distances.append(
            (
                best,
                driver,
            )
        )

    distances.sort()

    if not distances:
        return (
            "",
            None,
            [],
        )

    minimum = distances[0][0]

    tied = [
        driver
        for distance, driver in distances
        if distance == minimum
    ]

    return (
        tied[0]
        if len(tied) == 1
        else "|".join(tied),
        minimum,
        distances,
    )


def lane_normalized(lane_text):
    lower = lane_text.lower()

    if (
        "lane 1" in lower
        or
        "lane one" in lower
    ):
        return "LANE_1"

    if (
        "lane 2" in lower
        or
        "lane two" in lower
    ):
        return "LANE_2"

    if "non-priority" in lower:
        return "NON_PRIORITY_LANE"

    if "priority" in lower:
        return "PRIORITY_LANE"

    if "fast lane" in lower:
        return "FAST_LANE"

    return "LANE_UNSPECIFIED"


def classify_candidate(
    driver,
    driver_map,
    lane_hit,
    source,
):
    nearest_driver, nearest_distance, distances = (
        nearest_driver_to_lane(
            driver_map,
            lane_hit,
        )
    )

    target_mentions = driver_map.get(
        driver,
        [],
    )

    if not target_mentions:
        return (
            "NO_TARGET_DRIVER",
            nearest_driver,
            nearest_distance,
        )

    target_distance = min(
        interval_distance(
            mention["start"],
            mention["end"],
            lane_hit["start"],
            lane_hit["end"],
        )
        for mention in target_mentions
    )

    if not source_native(source):
        return (
            "DERIVED_OR_NON_SOURCE_NATIVE",
            nearest_driver,
            target_distance,
        )

    if nearest_driver == driver:
        if target_distance <= 90:
            return (
                "DIRECT_DRIVER_LANE_CANDIDATE",
                nearest_driver,
                target_distance,
            )

        return (
            "DRIVER_LANE_SAME_UNIT_REVIEW",
            nearest_driver,
            target_distance,
        )

    if "|" in nearest_driver:
        if driver in nearest_driver.split("|"):
            return (
                "AMBIGUOUS_MULTI_DRIVER_SENTENCE",
                nearest_driver,
                target_distance,
            )

    return (
        "LANE_MENTION_BUT_OTHER_DRIVER_CLOSER",
        nearest_driver,
        target_distance,
    )


def main():

    print()
    print("=" * 124)
    print(
        "R2B.1 — 2022 DECISION-RELEVANT REPEAT-PAIR "
        "TARGETED LANE EVIDENCE RECONNAISSANCE"
    )
    print("=" * 124)

    required = [
        ELIGIBILITY,
        CHRONOLOGY_V10,
        ACTION_V7,
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
            "R2B1_LANE_RECON_INPUT_MISSING"
        )
        return

    eligibility = read_csv(
        ELIGIBILITY
    )

    chronology = read_csv(
        CHRONOLOGY_V10
    )

    action = read_csv(
        ACTION_V7
    )

    eligible_drivers = {
        txt(row.get("driver_name"))
        for row in eligibility
        if txt(
            row.get(
                "decision_relevant_denominator"
            )
        ).upper()
        ==
        "INCLUDE"
    }

    print()
    print("=" * 124)
    print("FROZEN TARGET SET")
    print("=" * 124)

    print()

    for driver in sorted(
        eligible_drivers
    ):
        print(driver)

    target_set_ok = (
        eligible_drivers
        ==
        EXPECTED_DRIVERS
    )

    print()
    print(
        "Frozen target set exact match:",
        target_set_ok,
    )

    existing_lane_rows = [
        row
        for row in action
        if txt(
            row.get(
                "lane"
            )
        ).upper()
        not in {
            "",
            "UNKNOWN",
        }
    ]

    print()
    print(
        "Existing explicit historical Lane rows:",
        len(
            existing_lane_rows
        ),
    )

    for row in existing_lane_rows:
        print(
            " ",
            txt(
                row.get(
                    "driver_name"
                )
            ),
            "|",
            txt(
                row.get(
                    "lane"
                )
            ),
            "|",
            txt(
                row.get(
                    "action"
                )
            ),
        )

    # --------------------------------------------------
    # Source-native scan
    # --------------------------------------------------

    hits = []
    seen = set()
    files_scanned = 0
    source_files_with_lane = 0

    for root in SEARCH_ROOTS:

        if not root.exists():
            continue

        for path in sorted(
            root.rglob("*")
        ):

            if (
                not path.is_file()
                or
                path.suffix.lower()
                not in TEXT_EXTENSIONS
            ):
                continue

            # Avoid recursive inclusion of our own outputs.
            if (
                "lane_rescue_2022_repeat_pair_targeted"
                in
                path.name
            ):
                continue

            files_scanned += 1

            raw = safe_read(
                path
            )

            if not raw:
                continue

            lane_file_hits = regex_hits(
                raw,
                LANE_PATTERNS,
            )

            if not lane_file_hits:
                continue

            source_files_with_lane += 1

            source = source_class(
                path
            )

            units = split_units(
                raw
            )

            for unit_index, unit in enumerate(
                units,
                start=1,
            ):

                lane_hits = regex_hits(
                    unit,
                    LANE_PATTERNS,
                )

                if not lane_hits:
                    continue

                driver_map = all_driver_mentions(
                    unit
                )

                if not driver_map:
                    continue

                queue_hits = regex_hits(
                    unit,
                    QUEUE_PATTERNS,
                )

                action_hits = regex_hits(
                    unit,
                    ACTION_PATTERNS,
                )

                for lane_hit in lane_hits:

                    lane_label = lane_normalized(
                        lane_hit["match"]
                    )

                    for driver in sorted(
                        driver_map
                    ):

                        (
                            classification,
                            nearest_driver,
                            target_distance,
                        ) = classify_candidate(
                            driver,
                            driver_map,
                            lane_hit,
                            source,
                        )

                        key = (
                            str(path),
                            unit,
                            driver,
                            lane_hit["start"],
                            lane_hit["match"],
                        )

                        if key in seen:
                            continue

                        seen.add(
                            key
                        )

                        hits.append({
                            "driver_name":
                                driver,

                            "source_path":
                                str(path),

                            "source_class":
                                source,

                            "source_native":
                                str(
                                    source_native(
                                        source
                                    )
                                ),

                            "unit_index":
                                unit_index,

                            "lane_raw":
                                lane_hit["match"],

                            "lane_normalized":
                                lane_label,

                            "nearest_driver_to_lane":
                                nearest_driver,

                            "target_distance_chars":
                                target_distance
                                if target_distance is not None
                                else "",

                            "classification":
                                classification,

                            "queue_terms":
                                "|".join(
                                    sorted({
                                        hit["match"]
                                        for hit
                                        in queue_hits
                                    })
                                ),

                            "action_terms":
                                "|".join(
                                    sorted({
                                        hit["match"]
                                        for hit
                                        in action_hits
                                    })
                                ),

                            "drivers_in_unit":
                                "|".join(
                                    sorted(
                                        driver_map
                                    )
                                ),

                            "text":
                                unit[:2600],

                            "promotion_status":
                                "REVIEW_REQUIRED",
                        })

    # --------------------------------------------------
    # Driver summaries
    # --------------------------------------------------

    by_driver = defaultdict(
        list
    )

    for row in hits:
        by_driver[
            row["driver_name"]
        ].append(
            row
        )

    driver_summary = []

    print()
    print("=" * 124)
    print("TARGETED DRIVER RESULTS")
    print("=" * 124)

    for driver in sorted(
        eligible_drivers
    ):

        rows = by_driver.get(
            driver,
            [],
        )

        direct = [
            row
            for row in rows
            if row[
                "classification"
            ]
            ==
            "DIRECT_DRIVER_LANE_CANDIDATE"
        ]

        ambiguous = [
            row
            for row in rows
            if row[
                "classification"
            ]
            ==
            "AMBIGUOUS_MULTI_DRIVER_SENTENCE"
        ]

        other_driver = [
            row
            for row in rows
            if row[
                "classification"
            ]
            ==
            "LANE_MENTION_BUT_OTHER_DRIVER_CLOSER"
        ]

        review = [
            row
            for row in rows
            if row[
                "classification"
            ]
            ==
            "DRIVER_LANE_SAME_UNIT_REVIEW"
        ]

        direct_lane_labels = sorted({
            row[
                "lane_normalized"
            ]
            for row in direct
        })

        print()
        print("-" * 124)

        print(driver)

        print(
            "  total lane-containing units:",
            len(
                rows
            ),
        )

        print(
            "  direct candidates:",
            len(
                direct
            ),
        )

        print(
            "  same-unit review:",
            len(
                review
            ),
        )

        print(
            "  ambiguous multi-driver:",
            len(
                ambiguous
            ),
        )

        print(
            "  lane belongs closer to other driver:",
            len(
                other_driver
            ),
        )

        print(
            "  direct lane labels:",
            "|".join(
                direct_lane_labels
            )
            or
            "NONE",
        )

        driver_summary.append({
            "driver_name":
                driver,

            "total_lane_units":
                len(
                    rows
                ),

            "direct_driver_lane_candidates":
                len(
                    direct
                ),

            "same_unit_review":
                len(
                    review
                ),

            "ambiguous_multi_driver":
                len(
                    ambiguous
                ),

            "other_driver_closer":
                len(
                    other_driver
                ),

            "direct_lane_labels":
                "|".join(
                    direct_lane_labels
                ),

            "promotion_ready":
                "False",
        })

    # Print only the valuable candidates in detail.
    priority_hits = [
        row
        for row in hits
        if row[
            "classification"
        ]
        in {
            "DIRECT_DRIVER_LANE_CANDIDATE",
            "DRIVER_LANE_SAME_UNIT_REVIEW",
            "AMBIGUOUS_MULTI_DRIVER_SENTENCE",
        }
    ]

    print()
    print("=" * 124)
    print("PRIORITY REVIEW HITS")
    print("=" * 124)

    print()
    print(
        "Priority review hit count:",
        len(
            priority_hits
        ),
    )

    for i, row in enumerate(
        priority_hits,
        start=1,
    ):

        print()
        print("-" * 124)
        print(
            f"HIT {i}"
        )

        print(
            "driver:",
            row[
                "driver_name"
            ],
        )

        print(
            "classification:",
            row[
                "classification"
            ],
        )

        print(
            "lane:",
            row[
                "lane_normalized"
            ],
            "| raw:",
            repr(
                row[
                    "lane_raw"
                ]
            ),
        )

        print(
            "nearest driver:",
            row[
                "nearest_driver_to_lane"
            ],
        )

        print(
            "distance:",
            row[
                "target_distance_chars"
            ],
        )

        print(
            "drivers in unit:",
            row[
                "drivers_in_unit"
            ],
        )

        print(
            "queue terms:",
            row[
                "queue_terms"
            ]
            or
            "NONE",
        )

        print(
            "action terms:",
            row[
                "action_terms"
            ]
            or
            "NONE",
        )

        print(
            "source:",
            row[
                "source_class"
            ],
        )

        print(
            row[
                "source_path"
            ]
        )

        print(
            row[
                "text"
            ]
        )

    write_csv(
        HITS_OUT,
        hits,
        [
            "driver_name",
            "source_path",
            "source_class",
            "source_native",
            "unit_index",
            "lane_raw",
            "lane_normalized",
            "nearest_driver_to_lane",
            "target_distance_chars",
            "classification",
            "queue_terms",
            "action_terms",
            "drivers_in_unit",
            "text",
            "promotion_status",
        ],
    )

    write_csv(
        DRIVER_SUMMARY_OUT,
        driver_summary,
        [
            "driver_name",
            "total_lane_units",
            "direct_driver_lane_candidates",
            "same_unit_review",
            "ambiguous_multi_driver",
            "other_driver_closer",
            "direct_lane_labels",
            "promotion_ready",
        ],
    )

    direct_total = sum(
        int(
            row[
                "direct_driver_lane_candidates"
            ]
        )
        for row in driver_summary
    )

    drivers_with_direct = [
        row[
            "driver_name"
        ]
        for row in driver_summary
        if int(
            row[
                "direct_driver_lane_candidates"
            ]
        )
        >
        0
    ]

    qa_rows = [
        {
            "metric":
                "frozen_target_driver_count",

            "value":
                len(
                    eligible_drivers
                ),

            "status":
                "PASS"
                if len(
                    eligible_drivers
                )
                ==
                8
                else
                "FAIL",
        },

        {
            "metric":
                "frozen_target_set_exact",

            "value":
                int(
                    target_set_ok
                ),

            "status":
                "PASS"
                if target_set_ok
                else
                "FAIL",
        },

        {
            "metric":
                "existing_explicit_lane_rows",

            "value":
                len(
                    existing_lane_rows
                ),

            "status":
                "PASS",
        },

        {
            "metric":
                "files_scanned",

            "value":
                files_scanned,

            "status":
                "PASS",
        },

        {
            "metric":
                "source_files_with_lane_terms",

            "value":
                source_files_with_lane,

            "status":
                "PASS",
        },

        {
            "metric":
                "direct_lane_candidates",

            "value":
                direct_total,

            "status":
                "PASS"
                if direct_total > 0
                else
                "REVIEW",
        },

        {
            "metric":
                "drivers_with_direct_candidates",

            "value":
                len(
                    drivers_with_direct
                ),

            "status":
                "PASS"
                if len(
                    drivers_with_direct
                )
                >
                0
                else
                "REVIEW",
        },

        {
            "metric":
                "ledger_mutation",

            "value":
                0,

            "status":
                "PASS",
        },

        {
            "metric":
                "canonical_mutation",

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
    print("=" * 124)
    print("RECON SUMMARY")
    print("=" * 124)

    print()
    print(
        "Files scanned:",
        files_scanned,
    )

    print(
        "Files containing Lane terms:",
        source_files_with_lane,
    )

    print(
        "Total Lane-related driver hits:",
        len(
            hits
        ),
    )

    print(
        "Direct driver-Lane candidates:",
        direct_total,
    )

    print(
        "Drivers with direct candidates:",
        "|".join(
            sorted(
                drivers_with_direct
            )
        )
        or
        "NONE",
    )

    print()
    print(
        "Existing explicit historical Lane rows:",
        len(
            existing_lane_rows
        ),
    )

    print()
    print(
        "FINAL STATUS: "
        "R2B1_2022_REPEAT_PAIR_LANE_TARGETED_RECON_COMPLETE"
    )

    print()
    print("OUTPUTS")
    print(HITS_OUT)
    print(DRIVER_SUMMARY_OUT)
    print(QA_OUT)


if __name__ == "__main__":
    main()
