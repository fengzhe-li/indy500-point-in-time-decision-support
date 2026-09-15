from pathlib import Path
import csv
import re
from collections import defaultdict


PHASE = "R2H.1"

ELIGIBILITY = Path(
    "weather/output/"
    "chronology_rescue_2022_repeat_pair_driver_eligibility_v1.csv"
)

RUBBER_POLICY = Path(
    "weather/output/"
    "rubber_grip_identifiability_2022_v1.csv"
)

SERVICE_POLICY = Path(
    "weather/output/"
    "pit_service_identifiability_2022_v1.csv"
)

CHRONOLOGY_V10 = Path(
    "weather/output/"
    "unified_attempt_chronology_constraint_ledger_v10.csv"
)

OUTPUT_DIR = Path("weather/output")

HITS_OUT = (
    OUTPUT_DIR
    / "tire_thermal_rescue_2022_targeted_hits_v1.csv"
)

SUMMARY_OUT = (
    OUTPUT_DIR
    / "tire_thermal_rescue_2022_targeted_summary_v1.csv"
)

QA_OUT = (
    OUTPUT_DIR
    / "tire_thermal_rescue_2022_targeted_v1_qa.csv"
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


TIRE_TEMP_PATTERNS = [
    r"\btire temperature\b",
    r"\btire temperatures\b",
    r"\btyre temperature\b",
    r"\btyre temperatures\b",
    r"\btire temp\b",
    r"\btyre temp\b",
    r"\bhot tires\b",
    r"\bhot tyres\b",
    r"\bcold tires\b",
    r"\bcold tyres\b",
    r"\bwarm tires\b",
    r"\bwarm tyres\b",
    r"\bwarmer tires\b",
    r"\bwarmer tyres\b",
    r"\bcool tires\b",
    r"\bcool tyres\b",
]


PRESSURE_PATTERNS = [
    r"\btire pressure\b",
    r"\btire pressures\b",
    r"\btyre pressure\b",
    r"\btyre pressures\b",
    r"\bpressure adjustment\b",
    r"\bpressure adjustments\b",
    r"\bchanged tire pressure\b",
    r"\bchanged tyre pressure\b",
    r"\badjusted tire pressure\b",
    r"\badjusted tyre pressure\b",
    r"\bpsi\b",
]


THERMAL_PATTERNS = [
    r"\bthermal\b",
    r"\bthermal window\b",
    r"\btemperature window\b",
    r"\bheat cycle\b",
    r"\bheat cycles\b",
    r"\bheat in the tires\b",
    r"\bheat in the tyres\b",
    r"\bbuild heat\b",
    r"\bbuilding heat\b",
    r"\bget heat into\b",
    r"\bgetting heat into\b",
]


WARMING_PATTERNS = [
    r"\bwarm(?:ed|ing)? the tires\b",
    r"\bwarm(?:ed|ing)? the tyres\b",
    r"\btire warmers\b",
    r"\btyre warmers\b",
    r"\bbring the tires up\b",
    r"\bbring the tyres up\b",
]


COOLING_PATTERNS = [
    r"\bcool(?:ed|ing)? the tires\b",
    r"\bcool(?:ed|ing)? the tyres\b",
    r"\btire cooling\b",
    r"\btyre cooling\b",
    r"\blet the tires cool\b",
    r"\blet the tyres cool\b",
]


FRESH_TIRE_PATTERNS = [
    r"\bfresh tires\b",
    r"\bfresh tyres\b",
    r"\bnew tires\b",
    r"\bnew tyres\b",
    r"\bnew set of tires\b",
    r"\bnew set of tyres\b",
]


GENERIC_TIRE_PATTERNS = [
    r"\btires?\b",
    r"\btyres?\b",
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
    r"\bqualifying run\b",
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

        paragraph = normalize(paragraph)

        if not paragraph:
            continue

        for sentence in re.split(
            r"(?<=[.!?])\s+",
            paragraph,
        ):

            sentence = normalize(sentence)

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

        if "nbc" in lower:
            return "SECONDARY_NBC"

        return "SECONDARY_EDITORIAL"

    return "OTHER_LOCAL_EVIDENCE"


def source_native(source):
    return source in {
        "INDYCAR_OFFICIAL_EDITORIAL",
        "SECONDARY_AUTOSPORT",
        "SECONDARY_THE_RACE",
        "SECONDARY_NBC",
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
    tire_temp,
    pressure,
    thermal,
    warming,
    cooling,
    fresh,
    generic_tire,
    run_context,
):
    if not source_native(source):
        return "NON_SOURCE_NATIVE"

    if tire_temp:
        return "DIRECT_TIRE_TEMPERATURE_CANDIDATE"

    if pressure:
        return "DIRECT_TIRE_PRESSURE_CANDIDATE"

    if thermal:
        return "DIRECT_TIRE_THERMAL_CANDIDATE"

    if warming:
        return "DIRECT_TIRE_WARMING_CANDIDATE"

    if cooling:
        return "DIRECT_TIRE_COOLING_CANDIDATE"

    if fresh and run_context:
        return "FRESH_TIRE_BETWEEN_RUNS_CANDIDATE"

    if fresh:
        return "FRESH_TIRE_REVIEW"

    if generic_tire and drivers:
        return "GENERIC_TIRE_MENTION_REVIEW"

    return "LOW_VALUE"


def main():

    print()
    print("=" * 126)
    print(
        "R2H.1 — 2022 TIRE THERMAL / PRESSURE "
        "TARGETED RECONNAISSANCE"
    )
    print("=" * 126)

    required = [
        ELIGIBILITY,
        RUBBER_POLICY,
        SERVICE_POLICY,
        CHRONOLOGY_V10,
    ]

    print()
    print("INPUT CHECK")
    print("-" * 126)

    for path in required:
        print(
            f"{path}: "
            f"{'PRESENT' if path.exists() else 'MISSING'}"
        )

    if not all(path.exists() for path in required):
        print()
        print(
            "FINAL STATUS: "
            "R2H1_TIRE_THERMAL_RECON_INPUT_MISSING"
        )
        return

    eligibility = read_csv(ELIGIBILITY)
    read_csv(RUBBER_POLICY)
    read_csv(SERVICE_POLICY)
    read_csv(CHRONOLOGY_V10)

    eligible_drivers = {
        txt(
            row.get("driver_name")
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

    target_ok = (
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
        target_ok,
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
                "tire_thermal_rescue_2022"
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

                tire_temp = regex_values(
                    unit,
                    TIRE_TEMP_PATTERNS,
                )

                pressure = regex_values(
                    unit,
                    PRESSURE_PATTERNS,
                )

                thermal = regex_values(
                    unit,
                    THERMAL_PATTERNS,
                )

                warming = regex_values(
                    unit,
                    WARMING_PATTERNS,
                )

                cooling = regex_values(
                    unit,
                    COOLING_PATTERNS,
                )

                fresh = regex_values(
                    unit,
                    FRESH_TIRE_PATTERNS,
                )

                generic_tire = regex_values(
                    unit,
                    GENERIC_TIRE_PATTERNS,
                )

                run_context = regex_values(
                    unit,
                    RUN_CONTEXT_PATTERNS,
                )

                if not any([
                    tire_temp,
                    pressure,
                    thermal,
                    warming,
                    cooling,
                    fresh,
                    generic_tire,
                ]):
                    continue

                classification = classify(
                    source,
                    drivers,
                    tire_temp,
                    pressure,
                    thermal,
                    warming,
                    cooling,
                    fresh,
                    generic_tire,
                    run_context,
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
                    "|".join(drivers),
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
                        "|".join(drivers),

                    "tire_temperature_terms":
                        "|".join(tire_temp),

                    "pressure_terms":
                        "|".join(pressure),

                    "thermal_terms":
                        "|".join(thermal),

                    "warming_terms":
                        "|".join(warming),

                    "cooling_terms":
                        "|".join(cooling),

                    "fresh_tire_terms":
                        "|".join(fresh),

                    "generic_tire_terms":
                        "|".join(generic_tire),

                    "run_context_terms":
                        "|".join(run_context),

                    "attempt_specific":
                        "UNKNOWN",

                    "temperature_value":
                        "UNKNOWN",

                    "pressure_value":
                        "UNKNOWN",

                    "tire_state":
                        "UNKNOWN",

                    "promotion_status":
                        "REVIEW_REQUIRED",

                    "text":
                        unit[:3000],
                })

    by_class = defaultdict(int)

    for row in hits:
        by_class[
            row["classification"]
        ] += 1

    priority_classes = {
        "DIRECT_TIRE_TEMPERATURE_CANDIDATE",
        "DIRECT_TIRE_PRESSURE_CANDIDATE",
        "DIRECT_TIRE_THERMAL_CANDIDATE",
        "DIRECT_TIRE_WARMING_CANDIDATE",
        "DIRECT_TIRE_COOLING_CANDIDATE",
        "FRESH_TIRE_BETWEEN_RUNS_CANDIDATE",
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
    print("CANDIDATE CLASS SUMMARY")
    print("=" * 126)

    print()

    for classification in sorted(
        by_class
    ):
        print(
            classification,
            ":",
            by_class[classification],
        )

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
            "classification:",
            row["classification"],
        )

        print(
            "drivers:",
            row["drivers_in_unit"]
            or
            "NONE",
        )

        print(
            "tire temperature:",
            row["tire_temperature_terms"]
            or
            "NONE",
        )

        print(
            "pressure:",
            row["pressure_terms"]
            or
            "NONE",
        )

        print(
            "thermal:",
            row["thermal_terms"]
            or
            "NONE",
        )

        print(
            "warming:",
            row["warming_terms"]
            or
            "NONE",
        )

        print(
            "cooling:",
            row["cooling_terms"]
            or
            "NONE",
        )

        print(
            "fresh tires:",
            row["fresh_tire_terms"]
            or
            "NONE",
        )

        print(
            "run context:",
            row["run_context_terms"]
            or
            "NONE",
        )

        print(
            "source:",
            row["source_class"],
        )

        print(
            row["source_path"]
        )

        print(
            row["text"]
        )

    fields = [
        "source_path",
        "source_class",
        "unit_index",
        "classification",
        "drivers_in_unit",
        "tire_temperature_terms",
        "pressure_terms",
        "thermal_terms",
        "warming_terms",
        "cooling_terms",
        "fresh_tire_terms",
        "generic_tire_terms",
        "run_context_terms",
        "attempt_specific",
        "temperature_value",
        "pressure_value",
        "tire_state",
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
                len(hits),
        },
        {
            "metric":
                "priority_rows",
            "value":
                len(priority),
        },
        {
            "metric":
                "direct_temperature_candidates",
            "value":
                by_class.get(
                    "DIRECT_TIRE_TEMPERATURE_CANDIDATE",
                    0,
                ),
        },
        {
            "metric":
                "direct_pressure_candidates",
            "value":
                by_class.get(
                    "DIRECT_TIRE_PRESSURE_CANDIDATE",
                    0,
                ),
        },
        {
            "metric":
                "direct_thermal_candidates",
            "value":
                by_class.get(
                    "DIRECT_TIRE_THERMAL_CANDIDATE",
                    0,
                ),
        },
        {
            "metric":
                "fresh_tire_between_runs_candidates",
            "value":
                by_class.get(
                    "FRESH_TIRE_BETWEEN_RUNS_CANDIDATE",
                    0,
                ),
        },
        {
            "metric":
                "temperature_value_inferred",
            "value":
                0,
        },
        {
            "metric":
                "pressure_value_inferred",
            "value":
                0,
        },
        {
            "metric":
                "wait_used_to_infer_tire_temperature",
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
                int(target_ok),

            "status":
                (
                    "PASS"
                    if target_ok
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
                "temperature_value_inferred",

            "value":
                0,

            "status":
                "PASS",
        },

        {
            "metric":
                "pressure_value_inferred",

            "value":
                0,

            "status":
                "PASS",
        },

        {
            "metric":
                "fresh_tires_inferred_from_second_run",

            "value":
                0,

            "status":
                "PASS",
        },

        {
            "metric":
                "wait_used_to_infer_tire_temperature",

            "value":
                0,

            "status":
                "PASS",
        },

        {
            "metric":
                "pit_service_used_to_infer_pressure",

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
        row["status"]
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
        len(hits),
    )

    print(
        "Priority candidates:",
        len(priority),
    )

    print()
    print(
        "Direct tire-temperature candidates:",
        by_class.get(
            "DIRECT_TIRE_TEMPERATURE_CANDIDATE",
            0,
        ),
    )

    print(
        "Direct pressure candidates:",
        by_class.get(
            "DIRECT_TIRE_PRESSURE_CANDIDATE",
            0,
        ),
    )

    print(
        "Direct thermal candidates:",
        by_class.get(
            "DIRECT_TIRE_THERMAL_CANDIDATE",
            0,
        ),
    )

    print(
        "Fresh-tire-between-runs candidates:",
        by_class.get(
            "FRESH_TIRE_BETWEEN_RUNS_CANDIDATE",
            0,
        ),
    )

    print()
    print(
        "Temperature values inferred:",
        0,
    )

    print(
        "Pressure values inferred:",
        0,
    )

    print(
        "Queue wait used for tire temperature:",
        0,
    )

    print()
    print("=" * 126)

    if not hard_fail:
        print(
            "FINAL STATUS: "
            "R2H1_2022_TIRE_THERMAL_PRESSURE_RECON_COMPLETE"
        )
    else:
        print(
            "FINAL STATUS: "
            "R2H1_TIRE_THERMAL_RECON_REVIEW_REQUIRED"
        )

    print("=" * 126)

    print()
    print("OUTPUTS")
    print(HITS_OUT)
    print(SUMMARY_OUT)
    print(QA_OUT)


if __name__ == "__main__":
    main()
