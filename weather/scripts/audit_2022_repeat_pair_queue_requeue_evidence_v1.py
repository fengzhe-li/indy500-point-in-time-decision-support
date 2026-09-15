from pathlib import Path
import csv
import re
from collections import defaultdict


PHASE = "R2D.1"

ELIGIBILITY = Path(
    "weather/output/"
    "chronology_rescue_2022_repeat_pair_driver_eligibility_v1.csv"
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

HITS_OUT = (
    OUTPUT_DIR
    / "queue_rescue_2022_repeat_pair_targeted_hits_v1.csv"
)

SUMMARY_OUT = (
    OUTPUT_DIR
    / "queue_rescue_2022_repeat_pair_driver_summary_v1.csv"
)

QA_OUT = (
    OUTPUT_DIR
    / "queue_rescue_2022_repeat_pair_targeted_v1_qa.csv"
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


QUEUE_PATTERNS = [
    r"\bfront of the lane\s*1 queue\b",
    r"\bfront of lane\s*1 queue\b",
    r"\blane\s*1 queue\b",
    r"\blane\s*2 queue\b",
    r"\bpriority queue\b",
    r"\bnon[- ]priority queue\b",
    r"\bjoined the queue\b",
    r"\bjoin the queue\b",
    r"\bin the queue\b",
    r"\bqueued\b",
    r"\bqueueing\b",
    r"\bqueuing\b",
    r"\brequeued\b",
    r"\bre-queued\b",
    r"\brequeue\b",
    r"\bre-queue\b",
    r"\bin line\b",
    r"\bput .* in line\b",
]


ORDER_PATTERNS = [
    r"\bfirst to do a retake run\b",
    r"\bfirst to do a re-run\b",
    r"\bfirst to rerun\b",
    r"\bfirst to re-run\b",
    r"\bfirst car out\b",
    r"\bfirst car back out\b",
    r"\bnext to run\b",
    r"\bnext car\b",
    r"\bfollowed by\b",
    r"\bthen came\b",
    r"\bthen .* ran\b",
    r"\bafter .* run\b",
]


RESTART_PATTERNS = [
    r"\bwhen the track re-opened\b",
    r"\bwhen the track reopened\b",
    r"\bafter the track re-opened\b",
    r"\bafter the track reopened\b",
    r"\bafter the restart\b",
    r"\bfollowing the restart\b",
    r"\bwhen qualifying resumed\b",
    r"\bafter qualifying resumed\b",
    r"\bwhen the session resumed\b",
    r"\bafter the session resumed\b",
    r"\bafter the rain\b",
]


ACTION_PATTERNS = [
    r"\bgave up his .* time\b",
    r"\bgave up .* time\b",
    r"\bwithdrew\b",
    r"\bwithdrawn\b",
    r"\bretake run\b",
    r"\bre-run\b",
    r"\brerun\b",
    r"\bsecond run\b",
    r"\bsecond attempt\b",
    r"\bimproved\b",
    r"\bunable to improve\b",
]


POSITION_PATTERNS = [
    r"\bfront of the lane\s*1 queue\b",
    r"\bfront of lane\s*1 queue\b",
    r"\bfront of the queue\b",
    r"\bfirst in line\b",
    r"\bsecond in line\b",
    r"\bthird in line\b",
    r"\b\d+\s+cars?\s+ahead\b",
    r"\b\d+\s+cars?\s+in front\b",
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
    text = re.sub(
        r"(?is)<script.*?</script>",
        " ",
        text,
    )

    text = re.sub(
        r"(?is)<style.*?</style>",
        " ",
        text,
    )

    return re.sub(
        r"(?is)<[^>]+>",
        " ",
        text,
    )


def split_units(raw):
    raw = strip_html(raw)
    raw = raw.replace("\r", "\n")

    units = []

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
                units.append(
                    part
                )

    return units


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
            "the_race" in lower
            or
            "therace" in lower
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
                "raw":
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


def interval_distance(
    a_start,
    a_end,
    b_start,
    b_end,
):
    if a_end < b_start:
        return b_start - a_end

    if b_end < a_start:
        return a_start - b_end

    return 0


def nearest_driver(
    driver_map,
    hit,
):
    distances = []

    for driver, mentions in driver_map.items():

        best = min(
            interval_distance(
                mention["start"],
                mention["end"],
                hit["start"],
                hit["end"],
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
        )

    minimum = distances[0][0]

    tied = [
        driver
        for distance, driver in distances
        if distance == minimum
    ]

    if len(tied) == 1:
        return (
            tied[0],
            minimum,
        )

    return (
        "|".join(tied),
        minimum,
    )


def classify_queue_hit(
    driver,
    driver_map,
    queue_hit,
    position_hits,
    source,
):
    nearest, distance = nearest_driver(
        driver_map,
        queue_hit,
    )

    target_mentions = driver_map.get(
        driver,
        [],
    )

    if not target_mentions:
        return (
            "NO_TARGET_DRIVER",
            nearest,
            "",
        )

    target_distance = min(
        interval_distance(
            mention["start"],
            mention["end"],
            queue_hit["start"],
            queue_hit["end"],
        )
        for mention in target_mentions
    )

    if not source_native(source):
        return (
            "NON_SOURCE_NATIVE_QUEUE_MENTION",
            nearest,
            target_distance,
        )

    if "|" in nearest:
        if driver in nearest.split("|"):
            return (
                "AMBIGUOUS_MULTI_DRIVER_QUEUE_CLAUSE",
                nearest,
                target_distance,
            )

    if nearest != driver:
        return (
            "QUEUE_TERM_BELONGS_CLOSER_TO_OTHER_DRIVER",
            nearest,
            target_distance,
        )

    position_direct = any(
        interval_distance(
            p["start"],
            p["end"],
            queue_hit["start"],
            queue_hit["end"],
        )
        <=
        20
        for p in position_hits
    )

    if position_direct:
        return (
            "DIRECT_QUEUE_POSITION_CANDIDATE",
            nearest,
            target_distance,
        )

    if target_distance <= 100:
        return (
            "DIRECT_QUEUE_MEMBERSHIP_CANDIDATE",
            nearest,
            target_distance,
        )

    return (
        "QUEUE_SAME_UNIT_REVIEW",
        nearest,
        target_distance,
    )


def main():

    print()
    print("=" * 126)
    print(
        "R2D.1 — 2022 DECISION-RELEVANT REPEAT-PAIR "
        "QUEUE / REQUEUE TARGETED RECONNAISSANCE"
    )
    print("=" * 126)

    required = [
        ELIGIBILITY,
        CHRONOLOGY_V10,
        ACTION_V8,
        STATE_V2,
    ]

    print()
    print("INPUT CHECK")
    print("-" * 126)

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
            "R2D1_QUEUE_RECON_INPUT_MISSING"
        )
        return

    eligibility = read_csv(
        ELIGIBILITY
    )

    eligible_drivers = {
        txt(
            row.get(
                "driver_name"
            )
        )
        for row in eligibility
        if txt(
            row.get(
                "decision_relevant_denominator"
            )
        ).upper()
        ==
        "INCLUDE"
    }

    target_set_ok = (
        eligible_drivers
        ==
        EXPECTED_DRIVERS
    )

    print()
    print("=" * 126)
    print("FROZEN TARGET SET")
    print("=" * 126)

    print()

    for driver in sorted(
        eligible_drivers
    ):
        print(driver)

    print()
    print(
        "Frozen target set exact match:",
        target_set_ok,
    )

    print(
        "Chronology:",
        "V10",
    )

    print(
        "Action/Lane:",
        "V8",
    )

    print(
        "Decision-state:",
        "V2",
    )

    hits = []
    seen = set()

    files_scanned = 0
    source_files_with_queue = 0
    source_files_with_order = 0

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

            if (
                "queue_rescue_2022_repeat_pair"
                in path.name
            ):
                continue

            files_scanned += 1

            raw = safe_read(
                path
            )

            if not raw:
                continue

            whole_queue = regex_hits(
                raw,
                QUEUE_PATTERNS,
            )

            whole_order = regex_hits(
                raw,
                ORDER_PATTERNS,
            )

            if whole_queue:
                source_files_with_queue += 1

            if whole_order:
                source_files_with_order += 1

            if not (
                whole_queue
                or
                whole_order
            ):
                continue

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

                driver_map = all_driver_mentions(
                    unit
                )

                if not driver_map:
                    continue

                queue_hits = regex_hits(
                    unit,
                    QUEUE_PATTERNS,
                )

                order_hits = regex_hits(
                    unit,
                    ORDER_PATTERNS,
                )

                restart_hits = regex_hits(
                    unit,
                    RESTART_PATTERNS,
                )

                action_hits = regex_hits(
                    unit,
                    ACTION_PATTERNS,
                )

                position_hits = regex_hits(
                    unit,
                    POSITION_PATTERNS,
                )

                # ------------------------------------------
                # Explicit queue / requeue terms
                # ------------------------------------------

                for qhit in queue_hits:

                    for driver in sorted(
                        driver_map
                    ):

                        if driver not in eligible_drivers:
                            continue

                        (
                            classification,
                            nearest,
                            distance,
                        ) = classify_queue_hit(
                            driver,
                            driver_map,
                            qhit,
                            position_hits,
                            source,
                        )

                        key = (
                            str(path),
                            unit,
                            driver,
                            qhit["start"],
                            classification,
                        )

                        if key in seen:
                            continue

                        seen.add(key)

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

                            "evidence_family":
                                "QUEUE",

                            "classification":
                                classification,

                            "nearest_driver":
                                nearest,

                            "target_distance_chars":
                                distance,

                            "queue_terms":
                                "|".join(
                                    sorted({
                                        hit["raw"]
                                        for hit in queue_hits
                                    })
                                ),

                            "position_terms":
                                "|".join(
                                    sorted({
                                        hit["raw"]
                                        for hit in position_hits
                                    })
                                ),

                            "ordering_terms":
                                "|".join(
                                    sorted({
                                        hit["raw"]
                                        for hit in order_hits
                                    })
                                ),

                            "restart_terms":
                                "|".join(
                                    sorted({
                                        hit["raw"]
                                        for hit in restart_hits
                                    })
                                ),

                            "action_terms":
                                "|".join(
                                    sorted({
                                        hit["raw"]
                                        for hit in action_hits
                                    })
                                ),

                            "drivers_in_unit":
                                "|".join(
                                    sorted(
                                        driver_map
                                    )
                                ),

                            "queue_wait_seconds":
                                "UNKNOWN",

                            "exact_timestamp":
                                "UNKNOWN",

                            "text":
                                unit[:2800],

                            "promotion_status":
                                "REVIEW_REQUIRED",
                        })

                # ------------------------------------------
                # Ordering-only evidence
                #
                # This does NOT prove queue membership.
                # ------------------------------------------

                if (
                    order_hits
                    and
                    source_native(
                        source
                    )
                ):

                    for driver in sorted(
                        driver_map
                    ):

                        if driver not in eligible_drivers:
                            continue

                        key = (
                            str(path),
                            unit,
                            driver,
                            "ORDER_ONLY",
                        )

                        if key in seen:
                            continue

                        seen.add(key)

                        classification = (
                            "SOURCE_NATIVE_RUN_ORDER_CANDIDATE"
                        )

                        if restart_hits:
                            classification = (
                                "SOURCE_NATIVE_RESTART_ORDER_CANDIDATE"
                            )

                        hits.append({
                            "driver_name":
                                driver,

                            "source_path":
                                str(path),

                            "source_class":
                                source,

                            "source_native":
                                "True",

                            "unit_index":
                                unit_index,

                            "evidence_family":
                                "ORDERING_ONLY",

                            "classification":
                                classification,

                            "nearest_driver":
                                "",

                            "target_distance_chars":
                                "",

                            "queue_terms":
                                "",

                            "position_terms":
                                "",

                            "ordering_terms":
                                "|".join(
                                    sorted({
                                        hit["raw"]
                                        for hit in order_hits
                                    })
                                ),

                            "restart_terms":
                                "|".join(
                                    sorted({
                                        hit["raw"]
                                        for hit in restart_hits
                                    })
                                ),

                            "action_terms":
                                "|".join(
                                    sorted({
                                        hit["raw"]
                                        for hit in action_hits
                                    })
                                ),

                            "drivers_in_unit":
                                "|".join(
                                    sorted(
                                        driver_map
                                    )
                                ),

                            "queue_wait_seconds":
                                "UNKNOWN",

                            "exact_timestamp":
                                "UNKNOWN",

                            "text":
                                unit[:2800],

                            "promotion_status":
                                "REVIEW_REQUIRED",
                        })

    by_driver = defaultdict(
        list
    )

    for row in hits:
        by_driver[
            row["driver_name"]
        ].append(
            row
        )

    high_value_classes = {
        "DIRECT_QUEUE_POSITION_CANDIDATE",
        "DIRECT_QUEUE_MEMBERSHIP_CANDIDATE",
        "SOURCE_NATIVE_RUN_ORDER_CANDIDATE",
        "SOURCE_NATIVE_RESTART_ORDER_CANDIDATE",
    }

    driver_summary = []

    print()
    print("=" * 126)
    print("TARGETED DRIVER RESULTS")
    print("=" * 126)

    for driver in sorted(
        eligible_drivers
    ):

        rows = by_driver.get(
            driver,
            [],
        )

        direct_position = [
            row
            for row in rows
            if row[
                "classification"
            ]
            ==
            "DIRECT_QUEUE_POSITION_CANDIDATE"
        ]

        direct_membership = [
            row
            for row in rows
            if row[
                "classification"
            ]
            ==
            "DIRECT_QUEUE_MEMBERSHIP_CANDIDATE"
        ]

        ordering = [
            row
            for row in rows
            if row[
                "classification"
            ]
            in {
                "SOURCE_NATIVE_RUN_ORDER_CANDIDATE",
                "SOURCE_NATIVE_RESTART_ORDER_CANDIDATE",
            }
        ]

        contamination = [
            row
            for row in rows
            if row[
                "classification"
            ]
            ==
            "QUEUE_TERM_BELONGS_CLOSER_TO_OTHER_DRIVER"
        ]

        print()
        print("-" * 126)
        print(driver)

        print(
            "  total queue/order units:",
            len(rows),
        )

        print(
            "  direct queue-position candidates:",
            len(
                direct_position
            ),
        )

        print(
            "  direct queue-membership candidates:",
            len(
                direct_membership
            ),
        )

        print(
            "  source-native ordering candidates:",
            len(
                ordering
            ),
        )

        print(
            "  contamination / other-driver closer:",
            len(
                contamination
            ),
        )

        driver_summary.append({
            "driver_name":
                driver,

            "total_queue_order_units":
                len(rows),

            "direct_queue_position_candidates":
                len(
                    direct_position
                ),

            "direct_queue_membership_candidates":
                len(
                    direct_membership
                ),

            "source_native_ordering_candidates":
                len(
                    ordering
                ),

            "other_driver_contamination":
                len(
                    contamination
                ),

            "queue_wait_known":
                "False",

            "promotion_ready":
                "False",
        })

    priority = [
        row
        for row in hits
        if row[
            "classification"
        ]
        in high_value_classes
    ]

    print()
    print("=" * 126)
    print("PRIORITY REVIEW HITS")
    print("=" * 126)

    print()
    print(
        "Priority review hit count:",
        len(
            priority
        ),
    )

    for i, row in enumerate(
        priority,
        start=1,
    ):

        print()
        print("-" * 126)

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
            "family:",
            row[
                "evidence_family"
            ],
        )

        print(
            "classification:",
            row[
                "classification"
            ],
        )

        print(
            "nearest driver:",
            row[
                "nearest_driver"
            ]
            or
            "N/A",
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
            "position terms:",
            row[
                "position_terms"
            ]
            or
            "NONE",
        )

        print(
            "ordering terms:",
            row[
                "ordering_terms"
            ]
            or
            "NONE",
        )

        print(
            "restart terms:",
            row[
                "restart_terms"
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
            "drivers in unit:",
            row[
                "drivers_in_unit"
            ],
        )

        print(
            "queue wait:",
            "UNKNOWN",
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

    fields = [
        "driver_name",
        "source_path",
        "source_class",
        "source_native",
        "unit_index",
        "evidence_family",
        "classification",
        "nearest_driver",
        "target_distance_chars",
        "queue_terms",
        "position_terms",
        "ordering_terms",
        "restart_terms",
        "action_terms",
        "drivers_in_unit",
        "queue_wait_seconds",
        "exact_timestamp",
        "text",
        "promotion_status",
    ]

    write_csv(
        HITS_OUT,
        hits,
        fields,
    )

    write_csv(
        SUMMARY_OUT,
        driver_summary,
        [
            "driver_name",
            "total_queue_order_units",
            "direct_queue_position_candidates",
            "direct_queue_membership_candidates",
            "source_native_ordering_candidates",
            "other_driver_contamination",
            "queue_wait_known",
            "promotion_ready",
        ],
    )

    direct_position_total = sum(
        int(
            row[
                "direct_queue_position_candidates"
            ]
        )
        for row in driver_summary
    )

    direct_membership_total = sum(
        int(
            row[
                "direct_queue_membership_candidates"
            ]
        )
        for row in driver_summary
    )

    ordering_total = sum(
        int(
            row[
                "source_native_ordering_candidates"
            ]
        )
        for row in driver_summary
    )

    high_drivers = sorted({
        row[
            "driver_name"
        ]
        for row in priority
    })

    print()
    print("=" * 126)
    print("RECON SUMMARY")
    print("=" * 126)

    print()
    print(
        "Files scanned:",
        files_scanned,
    )

    print(
        "Files with queue/requeue terms:",
        source_files_with_queue,
    )

    print(
        "Files with run-order terms:",
        source_files_with_order,
    )

    print(
        "Total queue/order candidate rows:",
        len(
            hits
        ),
    )

    print(
        "Direct queue-position candidates:",
        direct_position_total,
    )

    print(
        "Direct queue-membership candidates:",
        direct_membership_total,
    )

    print(
        "Source-native ordering candidates:",
        ordering_total,
    )

    print(
        "Drivers with priority candidates:",
        "|".join(
            high_drivers
        )
        or
        "NONE",
    )

    print()
    print(
        "Queue waits inferred:",
        0,
    )

    print(
        "Exact timestamps inferred:",
        0,
    )

    qa_rows = [
        {
            "metric":
                "target_driver_count",

            "value":
                len(
                    eligible_drivers
                ),

            "status":
                (
                    "PASS"
                    if len(
                        eligible_drivers
                    )
                    ==
                    8
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "target_set_exact",

            "value":
                int(
                    target_set_ok
                ),

            "status":
                (
                    "PASS"
                    if target_set_ok
                    else
                    "FAIL"
                ),
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
                "direct_queue_position_candidates",

            "value":
                direct_position_total,

            "status":
                (
                    "PASS"
                    if direct_position_total
                    >
                    0
                    else
                    "REVIEW"
                ),
        },

        {
            "metric":
                "source_native_ordering_candidates",

            "value":
                ordering_total,

            "status":
                (
                    "PASS"
                    if ordering_total
                    >
                    0
                    else
                    "REVIEW"
                ),
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

    hard_fail = any(
        row[
            "status"
        ]
        ==
        "FAIL"
        for row in qa_rows
    )

    print()
    print("=" * 126)

    if not hard_fail:

        print(
            "FINAL STATUS: "
            "R2D1_2022_QUEUE_REQUEUE_TARGETED_RECON_COMPLETE"
        )

    else:

        print(
            "FINAL STATUS: "
            "R2D1_QUEUE_REQUEUE_RECON_REVIEW_REQUIRED"
        )

    print("=" * 126)

    print()
    print("OUTPUTS")
    print(HITS_OUT)
    print(SUMMARY_OUT)
    print(QA_OUT)


if __name__ == "__main__":
    main()
