from pathlib import Path
import csv
import re
from collections import defaultdict


PHASE = "R2E.1"

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

QUEUE_POLICY = Path(
    "weather/output/"
    "queue_wait_identifiability_2022_v1.csv"
)

OUTPUT_DIR = Path("weather/output")

HITS_OUT = (
    OUTPUT_DIR
    / "pit_service_rescue_2022_repeat_pair_targeted_hits_v1.csv"
)

SUMMARY_OUT = (
    OUTPUT_DIR
    / "pit_service_rescue_2022_repeat_pair_driver_summary_v1.csv"
)

QA_OUT = (
    OUTPUT_DIR
    / "pit_service_rescue_2022_repeat_pair_targeted_v1_qa.csv"
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


PIT_PATTERNS = [
    r"\bpits?\b",
    r"\bpit lane\b",
    r"\bpit road\b",
    r"\bpit box\b",
    r"\bgarage\b",
    r"\breturned to the pits\b",
    r"\breturn(?:ed)? to pit\b",
    r"\bback to the pits\b",
    r"\bcame to the pits\b",
    r"\bwent to the pits\b",
]


REFUEL_PATTERNS = [
    r"\brefuel(?:ed|ing)?\b",
    r"\bre-fuel(?:ed|ing)?\b",
    r"\bfuel(?:led|ed|ing)?\b",
    r"\badded fuel\b",
    r"\badd fuel\b",
    r"\btook fuel\b",
    r"\bput fuel\b",
]


COOLING_PATTERNS = [
    r"\bcool(?:ed|ing)?\b",
    r"\bcool down\b",
    r"\bcooldown\b",
    r"\bcooling the car\b",
    r"\bcooling the engine\b",
    r"\bcooling the tires\b",
    r"\bcooling the tyres\b",
    r"\blet .* cool\b",
    r"\btemperature down\b",
]


TIRE_PATTERNS = [
    r"\btires?\b",
    r"\btyres?\b",
    r"\bnew tires?\b",
    r"\bnew tyres?\b",
    r"\bfresh tires?\b",
    r"\bfresh tyres?\b",
    r"\btire change\b",
    r"\btyre change\b",
    r"\bchanged tires?\b",
    r"\bchanged tyres?\b",
]


ADJUSTMENT_PATTERNS = [
    r"\badjust(?:ed|ment|ments|ing)?\b",
    r"\bsetup change\b",
    r"\bset-up change\b",
    r"\bwing change\b",
    r"\btrim change\b",
    r"\bchanged the car\b",
    r"\bchange to the car\b",
    r"\bmechanical change\b",
    r"\bpressure change\b",
    r"\btire pressure\b",
    r"\btyre pressure\b",
]


REPAIR_PATTERNS = [
    r"\brepair(?:ed|ing)?\b",
    r"\bfix(?:ed|ing)?\b",
    r"\bdamage\b",
    r"\breplaced\b",
    r"\bwork on the car\b",
    r"\bworked on the car\b",
]


RUN_CONTEXT_PATTERNS = [
    r"\bfirst run\b",
    r"\bsecond run\b",
    r"\bfirst attempt\b",
    r"\bsecond attempt\b",
    r"\bretake run\b",
    r"\bre-run\b",
    r"\brerun\b",
    r"\bretry\b",
    r"\bimproved\b",
    r"\bwithdrew\b",
    r"\bwithdrawn\b",
    r"\bbailed out\b",
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

        for sentence in re.split(
            r"(?<=[.!?])\s+",
            paragraph,
        ):

            sentence = normalize(
                sentence
            )

            if sentence:
                units.append(sentence)

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

    return sorted(set(values))


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
                found.append(driver)
                break

    return sorted(set(found))


def classify(
    source,
    drivers,
    pit,
    refuel,
    cooling,
    tire,
    adjustment,
    repair,
    run_context,
):
    if not source_native(source):
        return "NON_SOURCE_NATIVE"

    if not drivers:
        return "NO_TARGET_DRIVER"

    if refuel:
        return "DIRECT_REFUEL_CANDIDATE"

    if cooling:
        return "DIRECT_COOLING_CANDIDATE"

    if tire:
        return "DIRECT_TIRE_SERVICE_CANDIDATE"

    if adjustment:
        return "DIRECT_ADJUSTMENT_CANDIDATE"

    if repair:
        return "DIRECT_REPAIR_CANDIDATE"

    if pit and run_context:
        return "PIT_BETWEEN_RUNS_REVIEW"

    if pit:
        return "PIT_MENTION_REVIEW"

    return "LOW_VALUE"


def main():

    print()
    print("=" * 126)
    print(
        "R2E.1 — 2022 DECISION-RELEVANT REPEAT-PAIR "
        "PIT / SERVICE / REFUEL / COOLING RECONNAISSANCE"
    )
    print("=" * 126)

    required = [
        ELIGIBILITY,
        CHRONOLOGY_V10,
        ACTION_V8,
        QUEUE_POLICY,
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
            "R2E1_PIT_SERVICE_RECON_INPUT_MISSING"
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
        "Queue wait policy:",
        "LATENT_SENSITIVITY_VARIABLE",
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
                "pit_service_rescue_2022_repeat_pair"
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
                    driver
                    for driver in drivers_in_text(
                        unit
                    )
                    if driver in eligible_drivers
                ]

                if not drivers:
                    continue

                pit = regex_values(
                    unit,
                    PIT_PATTERNS,
                )

                refuel = regex_values(
                    unit,
                    REFUEL_PATTERNS,
                )

                cooling = regex_values(
                    unit,
                    COOLING_PATTERNS,
                )

                tire = regex_values(
                    unit,
                    TIRE_PATTERNS,
                )

                adjustment = regex_values(
                    unit,
                    ADJUSTMENT_PATTERNS,
                )

                repair = regex_values(
                    unit,
                    REPAIR_PATTERNS,
                )

                run_context = regex_values(
                    unit,
                    RUN_CONTEXT_PATTERNS,
                )

                if not any([
                    pit,
                    refuel,
                    cooling,
                    tire,
                    adjustment,
                    repair,
                ]):
                    continue

                classification = classify(
                    source,
                    drivers,
                    pit,
                    refuel,
                    cooling,
                    tire,
                    adjustment,
                    repair,
                    run_context,
                )

                if classification in {
                    "LOW_VALUE",
                    "NON_SOURCE_NATIVE",
                    "NO_TARGET_DRIVER",
                }:
                    continue

                for driver in drivers:

                    key = (
                        str(path),
                        unit,
                        driver,
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

                        "unit_index":
                            unit_index,

                        "classification":
                            classification,

                        "pit_terms":
                            "|".join(pit),

                        "refuel_terms":
                            "|".join(refuel),

                        "cooling_terms":
                            "|".join(cooling),

                        "tire_terms":
                            "|".join(tire),

                        "adjustment_terms":
                            "|".join(adjustment),

                        "repair_terms":
                            "|".join(repair),

                        "run_context_terms":
                            "|".join(run_context),

                        "drivers_in_unit":
                            "|".join(drivers),

                        "service_between_attempts":
                            "UNKNOWN",

                        "refuel_confirmed":
                            "UNKNOWN",

                        "cooling_confirmed":
                            "UNKNOWN",

                        "tire_service_confirmed":
                            "UNKNOWN",

                        "adjustment_confirmed":
                            "UNKNOWN",

                        "repair_confirmed":
                            "UNKNOWN",

                        "exact_service_time":
                            "UNKNOWN",

                        "promotion_status":
                            "REVIEW_REQUIRED",

                        "text":
                            unit[:3000],
                    })

    by_driver = defaultdict(list)

    for row in hits:
        by_driver[
            row["driver_name"]
        ].append(row)

    priority_classes = {
        "DIRECT_REFUEL_CANDIDATE",
        "DIRECT_COOLING_CANDIDATE",
        "DIRECT_TIRE_SERVICE_CANDIDATE",
        "DIRECT_ADJUSTMENT_CANDIDATE",
        "DIRECT_REPAIR_CANDIDATE",
        "PIT_BETWEEN_RUNS_REVIEW",
    }

    priority = [
        row
        for row in hits
        if row[
            "classification"
        ]
        in priority_classes
    ]

    print()
    print("=" * 126)
    print("TARGETED DRIVER RESULTS")
    print("=" * 126)

    summary_rows = []

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
            in priority_classes
        ]

        classes = sorted({
            row[
                "classification"
            ]
            for row in rows
        })

        print()
        print("-" * 126)
        print(driver)

        print(
            "  total service-related units:",
            len(rows),
        )

        print(
            "  priority candidates:",
            len(high),
        )

        print(
            "  classes:",
            "|".join(classes)
            or
            "NONE",
        )

        summary_rows.append({
            "driver_name":
                driver,

            "service_related_units":
                len(rows),

            "priority_candidates":
                len(high),

            "classes":
                "|".join(classes),

            "service_between_attempts_known":
                "False",

            "promotion_ready":
                "False",
        })

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
            "pit terms:",
            row[
                "pit_terms"
            ]
            or
            "NONE",
        )

        print(
            "refuel terms:",
            row[
                "refuel_terms"
            ]
            or
            "NONE",
        )

        print(
            "cooling terms:",
            row[
                "cooling_terms"
            ]
            or
            "NONE",
        )

        print(
            "tire terms:",
            row[
                "tire_terms"
            ]
            or
            "NONE",
        )

        print(
            "adjustment terms:",
            row[
                "adjustment_terms"
            ]
            or
            "NONE",
        )

        print(
            "repair terms:",
            row[
                "repair_terms"
            ]
            or
            "NONE",
        )

        print(
            "run context:",
            row[
                "run_context_terms"
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
        "driver_name",
        "source_path",
        "source_class",
        "unit_index",
        "classification",
        "pit_terms",
        "refuel_terms",
        "cooling_terms",
        "tire_terms",
        "adjustment_terms",
        "repair_terms",
        "run_context_terms",
        "drivers_in_unit",
        "service_between_attempts",
        "refuel_confirmed",
        "cooling_confirmed",
        "tire_service_confirmed",
        "adjustment_confirmed",
        "repair_confirmed",
        "exact_service_time",
        "promotion_status",
        "text",
    ]

    write_csv(
        HITS_OUT,
        hits,
        fields,
    )

    write_csv(
        SUMMARY_OUT,
        summary_rows,
        [
            "driver_name",
            "service_related_units",
            "priority_candidates",
            "classes",
            "service_between_attempts_known",
            "promotion_ready",
        ],
    )

    priority_drivers = sorted({
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
                "priority_candidate_count",

            "value":
                len(priority),

            "status":
                (
                    "PASS"
                    if len(priority) > 0
                    else
                    "REVIEW"
                ),
        },

        {
            "metric":
                "service_between_attempts_inferred",

            "value":
                0,

            "status":
                "PASS",
        },

        {
            "metric":
                "refuel_inferred_without_source",

            "value":
                0,

            "status":
                "PASS",
        },

        {
            "metric":
                "cooling_inferred_from_wait_time",

            "value":
                0,

            "status":
                "PASS",
        },

        {
            "metric":
                "tire_service_inferred",

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
    print("=" * 126)
    print("RECON SUMMARY")
    print("=" * 126)

    print()
    print(
        "Files scanned:",
        files_scanned,
    )

    print(
        "Service-related candidate rows:",
        len(hits),
    )

    print(
        "Priority candidates:",
        len(priority),
    )

    print(
        "Drivers with priority candidates:",
        "|".join(
            priority_drivers
        )
        or
        "NONE",
    )

    print()
    print(
        "Service-between-attempts inferred:",
        0,
    )

    print(
        "Refuel inferred without source:",
        0,
    )

    print(
        "Cooling inferred from waiting time:",
        0,
    )

    print()
    print("=" * 126)

    if not hard_fail:
        print(
            "FINAL STATUS: "
            "R2E1_2022_PIT_SERVICE_TARGETED_RECON_COMPLETE"
        )
    else:
        print(
            "FINAL STATUS: "
            "R2E1_PIT_SERVICE_RECON_REVIEW_REQUIRED"
        )

    print("=" * 126)

    print()
    print("OUTPUTS")
    print(HITS_OUT)
    print(SUMMARY_OUT)
    print(QA_OUT)


if __name__ == "__main__":
    main()
