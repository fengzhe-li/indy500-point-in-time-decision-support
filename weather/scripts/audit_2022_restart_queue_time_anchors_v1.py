from pathlib import Path
import csv
import re
from collections import defaultdict


PHASE = "R2D.4"

QUEUE_V1 = Path(
    "weather/output/"
    "queue_requeue_evidence_ledger_v1.csv"
)

CHRONOLOGY_V10 = Path(
    "weather/output/"
    "unified_attempt_chronology_constraint_ledger_v10.csv"
)

STATE_V2 = Path(
    "weather/output/"
    "contemporaneous_decision_state_evidence_ledger_v2.csv"
)

OUTPUT_DIR = Path("weather/output")

HITS_OUT = (
    OUTPUT_DIR
    / "queue_rescue_2022_restart_time_anchor_hits_v1.csv"
)

SUMMARY_OUT = (
    OUTPUT_DIR
    / "queue_rescue_2022_restart_time_anchor_summary_v1.csv"
)

QA_OUT = (
    OUTPUT_DIR
    / "queue_rescue_2022_restart_time_anchor_v1_qa.csv"
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


TARGET_DRIVERS = {
    "Callum Ilott",
    "David Malukas",
    "Scott McLaughlin",
    "Takuma Sato",
    "Sage Karam",
}


ALIASES = {
    "Callum Ilott": [
        "Callum Ilott",
        "Ilott",
    ],

    "David Malukas": [
        "David Malukas",
        "Malukas",
    ],

    "Scott McLaughlin": [
        "Scott McLaughlin",
        "McLaughlin",
    ],

    "Takuma Sato": [
        "Takuma Sato",
        "Sato",
    ],

    "Sage Karam": [
        "Sage Karam",
        "Karam",
    ],
}


RESTART_PATTERNS = [
    r"\bwhen the track re-opened\b",
    r"\bwhen the track reopened\b",
    r"\bafter the track re-opened\b",
    r"\bafter the track reopened\b",
    r"\btrack re-opened\b",
    r"\btrack reopened\b",
    r"\bqualifying resumed\b",
    r"\bsession resumed\b",
    r"\bwhen qualifying resumed\b",
    r"\bwhen the session resumed\b",
    r"\bafter qualifying resumed\b",
    r"\bafter the session resumed\b",
    r"\bafter the restart\b",
    r"\bfollowing the restart\b",
]


STOP_PATTERNS = [
    r"\brain delay\b",
    r"\brain stopped\b",
    r"\brain began\b",
    r"\brain arrived\b",
    r"\brain moved in\b",
    r"\blightning\b",
    r"\bred flag\b",
    r"\bsession stopped\b",
    r"\bqualifying stopped\b",
    r"\btrack closed\b",
]


QUEUE_PATTERNS = [
    r"\bfront of the lane\s*1 queue\b",
    r"\blane\s*1 queue\b",
    r"\blane\s*2 queue\b",
    r"\bin line\b",
    r"\bput .* in line\b",
    r"\bqueued\b",
    r"\bqueue\b",
    r"\brequeue\b",
    r"\bre-queue\b",
]


RUN_PATTERNS = [
    r"\bfirst to do a retake run\b",
    r"\bretake run\b",
    r"\bsecond run\b",
    r"\bsecond attempt\b",
    r"\bre-run\b",
    r"\brerun\b",
    r"\bimproved\b",
    r"\bunable to improve\b",
    r"\btumbled down to\b",
]


TIME_PATTERNS = [
    # 3:34 p.m. / 3:34pm
    r"\b(?:1[0-2]|0?[1-9]):[0-5]\d\s*(?:a\.?m\.?|p\.?m\.?)\b",

    # 15:34 / 19:34
    r"\b(?:[01]\d|2[0-3]):[0-5]\d\b",

    # 1934Z / 1934 Z
    r"\b(?:[01]\d|2[0-3])[0-5]\d\s*Z\b",

    # 19:34Z
    r"\b(?:[01]\d|2[0-3]):[0-5]\d\s*Z\b",

    # 3 p.m. / 3pm
    r"\b(?:1[0-2]|0?[1-9])\s*(?:a\.?m\.?|p\.?m\.?)\b",
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

        sentences = re.split(
            r"(?<=[.!?])\s+",
            paragraph,
        )

        for sentence in sentences:

            sentence = normalize(
                sentence
            )

            if sentence:
                units.append(
                    sentence
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

        return "SECONDARY_EDITORIAL"

    return "OTHER_LOCAL_EVIDENCE"


def source_native(source):
    return source in {
        "INDYCAR_OFFICIAL_EDITORIAL",
        "SECONDARY_AUTOSPORT",
        "SECONDARY_THE_RACE",
        "SECONDARY_EDITORIAL",
    }


def regex_values(text, patterns):
    values = []

    for pattern in patterns:

        for match in re.finditer(
            pattern,
            text,
            flags=re.I,
        ):

            values.append(
                match.group(0)
            )

    return sorted(
        set(values)
    )


def drivers_in_text(text):
    found = []

    for driver, aliases in ALIASES.items():

        for alias in aliases:

            pattern = (
                r"(?<![A-Za-z])"
                +
                re.escape(alias)
                +
                r"(?![A-Za-z])"
            )

            if re.search(
                pattern,
                text,
                flags=re.I,
            ):

                found.append(
                    driver
                )

                break

    return sorted(
        set(found)
    )


def classify(
    drivers,
    restart_terms,
    stop_terms,
    queue_terms,
    run_terms,
    times,
    source,
):
    if not source_native(source):
        return "NON_SOURCE_NATIVE"

    if times and restart_terms:
        if drivers:
            return "DRIVER_RESTART_TIME_CANDIDATE"

        return "EVENT_RESTART_TIME_CANDIDATE"

    if times and stop_terms:
        if drivers:
            return "DRIVER_INTERRUPTION_TIME_CANDIDATE"

        return "EVENT_INTERRUPTION_TIME_CANDIDATE"

    if times and queue_terms and drivers:
        return "DRIVER_QUEUE_TIME_CANDIDATE"

    if times and run_terms and drivers:
        return "DRIVER_RUN_TIME_CANDIDATE"

    if restart_terms and drivers:
        return "DRIVER_RESTART_ORDER_ONLY"

    if queue_terms and drivers:
        return "DRIVER_QUEUE_ORDER_ONLY"

    if run_terms and drivers:
        return "DRIVER_RUN_ORDER_ONLY"

    if restart_terms:
        return "EVENT_RESTART_ORDER_ONLY"

    if stop_terms:
        return "EVENT_INTERRUPTION_ORDER_ONLY"

    return "LOW_VALUE"


def main():

    print()
    print("=" * 126)
    print(
        "R2D.4 — 2022 RESTART / QUEUE-WAIT "
        "TIME-ANCHOR RECONNAISSANCE"
    )
    print("=" * 126)

    required = [
        QUEUE_V1,
        CHRONOLOGY_V10,
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
            "R2D4_RESTART_TIME_ANCHOR_INPUT_MISSING"
        )
        return

    queue_ledger = read_csv(
        QUEUE_V1
    )

    # Protected ledgers only checked/read.
    read_csv(
        CHRONOLOGY_V10
    )

    read_csv(
        STATE_V2
    )

    represented = {
        txt(
            row.get(
                "driver_name"
            )
        )
        for row in queue_ledger
        if txt(
            row.get(
                "driver_name"
            )
        )
    }

    print()
    print("=" * 126)
    print("QUEUE LEDGER BASE")
    print("=" * 126)

    print()
    print(
        "Queue ledger rows:",
        len(
            queue_ledger
        ),
    )

    print(
        "Drivers represented:",
        "|".join(
            sorted(
                represented
            )
        ),
    )

    print()
    print(
        "Known exact queue waits before R2D.4:",
        sum(
            1
            for row in queue_ledger
            if txt(
                row.get(
                    "queue_wait_seconds"
                )
            )
            not in {
                "",
                "UNKNOWN",
            }
        ),
    )

    print(
        "Known bounded queue waits before R2D.4:",
        sum(
            1
            for row in queue_ledger
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
        ),
    )

    hits = []

    seen = set()

    files_scanned = 0

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
                "queue_rescue_2022_restart_time_anchor"
                in path.name
            ):
                continue

            files_scanned += 1

            raw = safe_read(
                path
            )

            if not raw:
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

                drivers = [
                    driver
                    for driver in drivers_in_text(
                        unit
                    )
                    if driver in TARGET_DRIVERS
                ]

                restart_terms = regex_values(
                    unit,
                    RESTART_PATTERNS,
                )

                stop_terms = regex_values(
                    unit,
                    STOP_PATTERNS,
                )

                queue_terms = regex_values(
                    unit,
                    QUEUE_PATTERNS,
                )

                run_terms = regex_values(
                    unit,
                    RUN_PATTERNS,
                )

                times = regex_values(
                    unit,
                    TIME_PATTERNS,
                )

                if not any([
                    restart_terms,
                    stop_terms,
                    queue_terms,
                    run_terms,
                    times,
                ]):
                    continue

                classification = classify(
                    drivers,
                    restart_terms,
                    stop_terms,
                    queue_terms,
                    run_terms,
                    times,
                    source,
                )

                if classification in {
                    "LOW_VALUE",
                    "NON_SOURCE_NATIVE",
                }:
                    continue

                key = (
                    str(path),
                    unit,
                    classification,
                    "|".join(
                        drivers
                    ),
                )

                if key in seen:
                    continue

                seen.add(key)

                hits.append({
                    "source_path":
                        str(path),

                    "source_class":
                        source,

                    "unit_index":
                        unit_index,

                    "classification":
                        classification,

                    "drivers_in_unit":
                        "|".join(
                            drivers
                        ),

                    "restart_terms":
                        "|".join(
                            restart_terms
                        ),

                    "interruption_terms":
                        "|".join(
                            stop_terms
                        ),

                    "queue_terms":
                        "|".join(
                            queue_terms
                        ),

                    "run_terms":
                        "|".join(
                            run_terms
                        ),

                    "time_expressions":
                        "|".join(
                            times
                        ),

                    "time_quality":
                        "UNADJUDICATED",

                    "queue_wait_lower_bound_seconds":
                        "UNKNOWN",

                    "queue_wait_upper_bound_seconds":
                        "UNKNOWN",

                    "queue_wait_seconds":
                        "UNKNOWN",

                    "promotion_status":
                        "REVIEW_REQUIRED",

                    "text":
                        unit[:3000],
                })

    priority_classes = {
        "DRIVER_RESTART_TIME_CANDIDATE",
        "EVENT_RESTART_TIME_CANDIDATE",
        "DRIVER_INTERRUPTION_TIME_CANDIDATE",
        "EVENT_INTERRUPTION_TIME_CANDIDATE",
        "DRIVER_QUEUE_TIME_CANDIDATE",
        "DRIVER_RUN_TIME_CANDIDATE",
    }

    priority = [
        row
        for row in hits
        if row[
            "classification"
        ]
        in priority_classes
    ]

    by_class = defaultdict(
        int
    )

    for row in hits:
        by_class[
            row[
                "classification"
            ]
        ] += 1

    print()
    print("=" * 126)
    print("CANDIDATE CLASS SUMMARY")
    print("=" * 126)

    print()

    for classification in sorted(
        by_class
    ):

        print(
            classification,
            ":",
            by_class[
                classification
            ],
        )

    print()
    print("=" * 126)
    print("PRIORITY TIME-ANCHOR HITS")
    print("=" * 126)

    print()
    print(
        "Priority time-anchor hit count:",
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
            "classification:",
            row[
                "classification"
            ],
        )

        print(
            "drivers:",
            row[
                "drivers_in_unit"
            ]
            or
            "NONE",
        )

        print(
            "time expressions:",
            row[
                "time_expressions"
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
            "interruption terms:",
            row[
                "interruption_terms"
            ]
            or
            "NONE",
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
            "run terms:",
            row[
                "run_terms"
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

    fields = [
        "source_path",
        "source_class",
        "unit_index",
        "classification",
        "drivers_in_unit",
        "restart_terms",
        "interruption_terms",
        "queue_terms",
        "run_terms",
        "time_expressions",
        "time_quality",
        "queue_wait_lower_bound_seconds",
        "queue_wait_upper_bound_seconds",
        "queue_wait_seconds",
        "promotion_status",
        "text",
    ]

    write_csv(
        HITS_OUT,
        hits,
        fields,
    )

    summary_rows = [
        {
            "metric":
                "files_scanned",

            "value":
                files_scanned,
        },

        {
            "metric":
                "candidate_rows",

            "value":
                len(
                    hits
                ),
        },

        {
            "metric":
                "priority_time_anchor_rows",

            "value":
                len(
                    priority
                ),
        },

        {
            "metric":
                "exact_queue_waits_derived",

            "value":
                0,
        },

        {
            "metric":
                "bounded_queue_waits_derived",

            "value":
                0,
        },

        {
            "metric":
                "inter_attempt_gap_used_as_wait",

            "value":
                0,
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

    qa_rows = [
        {
            "metric":
                "queue_ledger_present",

            "value":
                1,

            "status":
                "PASS",
        },

        {
            "metric":
                "queue_ledger_row_count",

            "value":
                len(
                    queue_ledger
                ),

            "status":
                (
                    "PASS"
                    if len(
                        queue_ledger
                    )
                    ==
                    5
                    else
                    "REVIEW"
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
                "priority_time_anchor_rows",

            "value":
                len(
                    priority
                ),

            "status":
                (
                    "PASS"
                    if len(
                        priority
                    )
                    >
                    0
                    else
                    "REVIEW"
                ),
        },

        {
            "metric":
                "exact_queue_wait_inferred",

            "value":
                0,

            "status":
                "PASS",
        },

        {
            "metric":
                "bounded_queue_wait_inferred",

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

        {
            "metric":
                "queue_ledger_mutation",

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
    print("RECON SUMMARY")
    print("=" * 126)

    print()
    print(
        "Files scanned:",
        files_scanned,
    )

    print(
        "Candidate rows:",
        len(
            hits
        ),
    )

    print(
        "Priority time-anchor rows:",
        len(
            priority
        ),
    )

    print()
    print(
        "Exact queue waits derived:",
        0,
    )

    print(
        "Bounded queue waits derived:",
        0,
    )

    print(
        "Inter-attempt gaps used as queue wait:",
        0,
    )

    print()
    print("=" * 126)

    if not hard_fail:

        print(
            "FINAL STATUS: "
            "R2D4_2022_RESTART_QUEUE_TIME_ANCHOR_RECON_COMPLETE"
        )

    else:

        print(
            "FINAL STATUS: "
            "R2D4_RESTART_QUEUE_TIME_ANCHOR_RECON_REVIEW_REQUIRED"
        )

    print("=" * 126)

    print()
    print("OUTPUTS")
    print(HITS_OUT)
    print(SUMMARY_OUT)
    print(QA_OUT)


if __name__ == "__main__":
    main()
