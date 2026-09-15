from pathlib import Path
import csv
import re
from collections import defaultdict


PHASE = "R2C.1"

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

OUTPUT_DIR = Path("weather/output")

HITS_OUT = (
    OUTPUT_DIR
    / "leaderboard_rescue_2022_repeat_pair_targeted_hits_v1.csv"
)

DRIVER_SUMMARY_OUT = (
    OUTPUT_DIR
    / "leaderboard_rescue_2022_repeat_pair_driver_summary_v1.csv"
)

QA_OUT = (
    OUTPUT_DIR
    / "leaderboard_rescue_2022_repeat_pair_targeted_v1_qa.csv"
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


LIVE_STATE_PATTERNS = [
    r"\bcurrently\b",
    r"\bat the time\b",
    r"\bat that point\b",
    r"\bthen sat\b",
    r"\bwas sitting\b",
    r"\bsitting\b",
    r"\bheld\b",
    r"\bholding\b",
    r"\bprovisional\b",
    r"\bprovisionally\b",
    r"\bmoved (?:up|down) to\b",
    r"\bdropped to\b",
    r"\bjumped to\b",
    r"\bclimbed to\b",
    r"\bslipped to\b",
    r"\btumbled down to\b",
]


RANK_PATTERNS = [
    r"\bP([1-9]|[12][0-9]|3[0-3])\b",
    r"\b([1-9]|[12][0-9]|3[0-3])(?:st|nd|rd|th)\b",
    r"\bposition\b",
    r"\brank\b",
    r"\bplace\b",
]


CUTOFF_PATTERNS = [
    r"\btop\s*12\b",
    r"\btop twelve\b",
    r"\b12th\b",
    r"\b13th\b",
    r"\bP12\b",
    r"\bP13\b",
    r"\bcutoff\b",
    r"\bcut[- ]off\b",
    r"\bbubble\b",
    r"\bon the bubble\b",
    r"\boutside the top 12\b",
    r"\binside the top 12\b",
]


SPEED_PATTERN = re.compile(
    r"\b(22[0-9]\.\d{3}|23[0-9]\.\d{3})\b"
)


TEMPORAL_PATTERNS = [
    r"\bwhen the track re-opened\b",
    r"\bafter the track re-opened\b",
    r"\bafter the restart\b",
    r"\bfollowing the restart\b",
    r"\bbefore the rain\b",
    r"\bbefore rain\b",
    r"\bafter rain\b",
    r"\blate in the session\b",
    r"\bin the final hour\b",
    r"\bwith .* remaining\b",
    r"\bminutes remaining\b",
    r"\bseconds remaining\b",
]


FINAL_RESULT_PATTERNS = [
    r"\bended up\b",
    r"\bfinished\b",
    r"\bfinal result\b",
    r"\bfinal standings\b",
    r"\bqualified\b",
    r"\bwill start\b",
    r"\bstarting position\b",
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
    return re.sub(
        r"(?is)<[^>]+>",
        " ",
        text,
    )


def split_units(raw):
    raw = strip_html(raw)
    raw = raw.replace("\r", "\n")

    chunks = []

    for paragraph in raw.split("\n"):
        paragraph = normalize(paragraph)

        if not paragraph:
            continue

        parts = re.split(
            r"(?<=[.!?])\s+",
            paragraph,
        )

        for part in parts:
            part = normalize(part)

            if part:
                chunks.append(part)

    return chunks


def source_class(path):
    lower = str(path).lower()

    if "official_2022_editorial_chronology" in lower:
        return "INDYCAR_OFFICIAL_EDITORIAL"

    if "secondary_2022_high_priority_chronology" in lower:
        if "autosport" in lower:
            return "SECONDARY_AUTOSPORT"

        if "the_race" in lower or "therace" in lower:
            return "SECONDARY_THE_RACE"

        if "nbc" in lower:
            return "SECONDARY_NBC"

        return "SECONDARY_EDITORIAL"

    if "official_day1_session_details" in lower:
        return "INDYCAR_OFFICIAL_RESULTS_OR_API"

    return "OTHER_LOCAL_EVIDENCE"


def source_native(source):
    return source in {
        "INDYCAR_OFFICIAL_EDITORIAL",
        "SECONDARY_AUTOSPORT",
        "SECONDARY_THE_RACE",
        "SECONDARY_NBC",
        "SECONDARY_EDITORIAL",
    }


def regex_terms(text, patterns):
    hits = []

    for pattern in patterns:
        for match in re.finditer(
            pattern,
            text,
            flags=re.I,
        ):
            hits.append(
                match.group(0)
            )

    return sorted(set(hits))


def driver_mentions(text):
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
                found.append(driver)
                break

    return sorted(set(found))


def classify(
    source,
    drivers,
    live_terms,
    rank_terms,
    cutoff_terms,
    temporal_terms,
    final_terms,
    speed_hits,
):
    if not source_native(source):
        return "NON_SOURCE_NATIVE"

    if not drivers:
        return "NO_TARGET_DRIVER"

    if final_terms and not live_terms and not temporal_terms:
        return "LIKELY_FINAL_RESULT_ONLY"

    if cutoff_terms and temporal_terms:
        return "TEMPORAL_CUTOFF_CANDIDATE"

    if cutoff_terms and live_terms:
        return "LIVE_CUTOFF_CANDIDATE"

    if rank_terms and temporal_terms:
        return "TEMPORAL_RANK_CANDIDATE"

    if rank_terms and live_terms:
        return "LIVE_RANK_CANDIDATE"

    if speed_hits and cutoff_terms:
        return "CUTOFF_SPEED_CANDIDATE"

    if rank_terms or cutoff_terms or live_terms:
        return "LEADERBOARD_REVIEW"

    return "LOW_VALUE"


def main():

    print()
    print("=" * 126)
    print(
        "R2C.1 — 2022 DECISION-RELEVANT REPEAT-PAIR "
        "LIVE LEADERBOARD / CUTOFF TARGETED RECONNAISSANCE"
    )
    print("=" * 126)

    required = [
        ELIGIBILITY,
        CHRONOLOGY_V10,
        ACTION_V8,
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
            "R2C1_LEADERBOARD_RECON_INPUT_MISSING"
        )
        return

    eligibility = read_csv(
        ELIGIBILITY
    )

    chronology = read_csv(
        CHRONOLOGY_V10
    )

    action = read_csv(
        ACTION_V8
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
        "Active chronology ledger:",
        "V10",
    )

    print(
        "Active action/lane ledger:",
        "V8",
    )

    # --------------------------------------------------
    # Scan
    # --------------------------------------------------

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
                "leaderboard_rescue_2022_repeat_pair"
                in path.name
            ):
                continue

            files_scanned += 1

            raw = safe_read(path)

            if not raw:
                continue

            source = source_class(path)

            for unit_index, unit in enumerate(
                split_units(raw),
                start=1,
            ):

                drivers = [
                    d
                    for d in driver_mentions(unit)
                    if d in eligible_drivers
                ]

                if not drivers:
                    continue

                live_terms = regex_terms(
                    unit,
                    LIVE_STATE_PATTERNS,
                )

                rank_terms = regex_terms(
                    unit,
                    RANK_PATTERNS,
                )

                cutoff_terms = regex_terms(
                    unit,
                    CUTOFF_PATTERNS,
                )

                temporal_terms = regex_terms(
                    unit,
                    TEMPORAL_PATTERNS,
                )

                final_terms = regex_terms(
                    unit,
                    FINAL_RESULT_PATTERNS,
                )

                speed_hits = sorted(set(
                    SPEED_PATTERN.findall(
                        unit
                    )
                ))

                if not any([
                    live_terms,
                    rank_terms,
                    cutoff_terms,
                    speed_hits,
                ]):
                    continue

                classification = classify(
                    source,
                    drivers,
                    live_terms,
                    rank_terms,
                    cutoff_terms,
                    temporal_terms,
                    final_terms,
                    speed_hits,
                )

                for driver in drivers:

                    key = (
                        str(path),
                        unit,
                        driver,
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

                        "classification":
                            classification,

                        "drivers_in_unit":
                            "|".join(
                                drivers
                            ),

                        "live_state_terms":
                            "|".join(
                                live_terms
                            ),

                        "rank_terms":
                            "|".join(
                                rank_terms
                            ),

                        "cutoff_terms":
                            "|".join(
                                cutoff_terms
                            ),

                        "temporal_terms":
                            "|".join(
                                temporal_terms
                            ),

                        "final_result_terms":
                            "|".join(
                                final_terms
                            ),

                        "speed_hits_mph":
                            "|".join(
                                speed_hits
                            ),

                        "text":
                            unit[:2800],

                        "promotion_status":
                            "REVIEW_REQUIRED",
                    })

    # --------------------------------------------------
    # Summaries
    # --------------------------------------------------

    by_driver = defaultdict(list)

    for row in hits:
        by_driver[
            row["driver_name"]
        ].append(row)

    high_value_classes = {
        "LIVE_CUTOFF_CANDIDATE",
        "TEMPORAL_CUTOFF_CANDIDATE",
        "LIVE_RANK_CANDIDATE",
        "TEMPORAL_RANK_CANDIDATE",
        "CUTOFF_SPEED_CANDIDATE",
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

        high = [
            row
            for row in rows
            if row[
                "classification"
            ]
            in high_value_classes
        ]

        final_only = [
            row
            for row in rows
            if row[
                "classification"
            ]
            ==
            "LIKELY_FINAL_RESULT_ONLY"
        ]

        print()
        print("-" * 126)

        print(driver)

        print(
            "  total leaderboard-related units:",
            len(rows),
        )

        print(
            "  high-value live/temporal candidates:",
            len(high),
        )

        print(
            "  likely final-result-only units:",
            len(final_only),
        )

        classes = sorted({
            row[
                "classification"
            ]
            for row in rows
        })

        print(
            "  classes:",
            "|".join(classes)
            or
            "NONE",
        )

        driver_summary.append({
            "driver_name":
                driver,

            "total_leaderboard_units":
                len(rows),

            "high_value_candidates":
                len(high),

            "final_result_only_units":
                len(final_only),

            "classes":
                "|".join(
                    classes
                ),

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
        len(priority),
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
            "classification:",
            row[
                "classification"
            ],
        )

        print(
            "drivers in unit:",
            row[
                "drivers_in_unit"
            ],
        )

        print(
            "live terms:",
            row[
                "live_state_terms"
            ]
            or
            "NONE",
        )

        print(
            "rank terms:",
            row[
                "rank_terms"
            ]
            or
            "NONE",
        )

        print(
            "cutoff terms:",
            row[
                "cutoff_terms"
            ]
            or
            "NONE",
        )

        print(
            "temporal terms:",
            row[
                "temporal_terms"
            ]
            or
            "NONE",
        )

        print(
            "speed hits:",
            row[
                "speed_hits_mph"
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
            "classification",
            "drivers_in_unit",
            "live_state_terms",
            "rank_terms",
            "cutoff_terms",
            "temporal_terms",
            "final_result_terms",
            "speed_hits_mph",
            "text",
            "promotion_status",
        ],
    )

    write_csv(
        DRIVER_SUMMARY_OUT,
        driver_summary,
        [
            "driver_name",
            "total_leaderboard_units",
            "high_value_candidates",
            "final_result_only_units",
            "classes",
            "promotion_ready",
        ],
    )

    drivers_with_high = sorted({
        row[
            "driver_name"
        ]
        for row in priority
    })

    qa_rows = [
        {
            "metric":
                "target_driver_count",

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
                "target_set_exact",

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
                "files_scanned",

            "value":
                files_scanned,

            "status":
                "PASS",
        },

        {
            "metric":
                "total_candidate_units",

            "value":
                len(
                    hits
                ),

            "status":
                "PASS",
        },

        {
            "metric":
                "high_value_candidate_units",

            "value":
                len(
                    priority
                ),

            "status":
                "PASS"
                if len(
                    priority
                )
                >
                0
                else
                "REVIEW",
        },

        {
            "metric":
                "drivers_with_high_value_candidates",

            "value":
                len(
                    drivers_with_high
                ),

            "status":
                "PASS"
                if len(
                    drivers_with_high
                )
                >
                0
                else
                "REVIEW",
        },

        {
            "metric":
                "position_finish_promoted_as_live_rank",

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
    print("=" * 126)
    print("RECON SUMMARY")
    print("=" * 126)

    print()
    print(
        "Files scanned:",
        files_scanned,
    )

    print(
        "Total leaderboard-related candidate units:",
        len(
            hits
        ),
    )

    print(
        "High-value live/temporal candidates:",
        len(
            priority
        ),
    )

    print(
        "Drivers with high-value candidates:",
        "|".join(
            drivers_with_high
        )
        or
        "NONE",
    )

    print()
    print(
        "FINAL STATUS: "
        "R2C1_2022_REPEAT_PAIR_LIVE_LEADERBOARD_TARGETED_RECON_COMPLETE"
    )

    print()
    print("OUTPUTS")
    print(HITS_OUT)
    print(DRIVER_SUMMARY_OUT)
    print(QA_OUT)


if __name__ == "__main__":
    main()
