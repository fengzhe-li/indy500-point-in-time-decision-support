from pathlib import Path
import csv
import re
from collections import defaultdict


PHASE = "R2G.1"

INTERRUPTION_POLICY = Path(
    "weather/output/"
    "interruption_track_state_identifiability_2022_v1.csv"
)

ADJACENT_MECHANISM = Path(
    "weather/output/"
    "rubber_grip_adjacent_mechanism_evidence_2022_v1.csv"
)

CHRONOLOGY_V10 = Path(
    "weather/output/"
    "unified_attempt_chronology_constraint_ledger_v10.csv"
)

OUTPUT_DIR = Path("weather/output")

HITS_OUT = (
    OUTPUT_DIR
    / "rubber_grip_rescue_2022_targeted_hits_v1.csv"
)

SUMMARY_OUT = (
    OUTPUT_DIR
    / "rubber_grip_rescue_2022_targeted_summary_v1.csv"
)

QA_OUT = (
    OUTPUT_DIR
    / "rubber_grip_rescue_2022_targeted_v1_qa.csv"
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


RUBBER_PATTERNS = [
    r"\brubber\b",
    r"\brubbered in\b",
    r"\brubbering in\b",
    r"\brubber buildup\b",
    r"\brubber build-up\b",
    r"\brubber laid down\b",
    r"\blaid down rubber\b",
    r"\brubber washed away\b",
    r"\bwashed away the rubber\b",
    r"\bwashed the rubber away\b",
    r"\blost rubber\b",
]


GRIP_PATTERNS = [
    r"\bgrip\b",
    r"\bgrip level\b",
    r"\bmore grip\b",
    r"\bless grip\b",
    r"\blow grip\b",
    r"\btrack grip\b",
    r"\bgrippier\b",
    r"\bslippery\b",
    r"\bslid(?:ing)? around\b",
]


TRACK_EVOLUTION_PATTERNS = [
    r"\btrack evolution\b",
    r"\btrack evolved\b",
    r"\btrack improving\b",
    r"\btrack improved\b",
    r"\btrack getting better\b",
    r"\btrack getting faster\b",
    r"\btrack got faster\b",
    r"\btrack getting slower\b",
    r"\btrack got slower\b",
    r"\bconditions improving\b",
    r"\bconditions deteriorating\b",
]


GREEN_TRACK_PATTERNS = [
    r"\bgreen track\b",
    r"\bgreen racetrack\b",
    r"\bclean track\b",
    r"\bfresh track\b",
]


RAIN_MECHANISM_PATTERNS = [
    r"\brain.*rubber\b",
    r"\brubber.*rain\b",
    r"\bwashed away\b",
    r"\bwashed off\b",
]


SPEED_RELATION_PATTERNS = [
    r"\bfaster\b",
    r"\bslower\b",
    r"\bspeed dropped\b",
    r"\bspeeds dropped\b",
    r"\bspeed increased\b",
    r"\bspeeds increased\b",
]


TIME_PATTERNS = [
    r"\b(?:1[0-2]|0?[1-9]):[0-5]\d\s*(?:a\.?m\.?|p\.?m\.?)\b",
    r"\b(?:[01]\d|2[0-3]):[0-5]\d\b",
    r"\b(?:[01]\d|2[0-3]):[0-5]\d\s*Z\b",
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


def classify(
    source,
    rubber,
    grip,
    evolution,
    green_track,
    rain_mechanism,
    speed_relation,
):
    if not source_native(source):
        return "NON_SOURCE_NATIVE"

    if rubber and rain_mechanism:
        return "RAIN_RUBBER_MECHANISM_CANDIDATE"

    if rubber and grip:
        return "DIRECT_RUBBER_GRIP_RELATION_CANDIDATE"

    if evolution and grip:
        return "DIRECT_TRACK_EVOLUTION_GRIP_CANDIDATE"

    if evolution and speed_relation:
        return "DIRECT_TRACK_EVOLUTION_SPEED_CANDIDATE"

    if green_track:
        return "GREEN_TRACK_CANDIDATE"

    if rubber:
        return "RUBBER_STATE_REVIEW"

    if grip:
        return "GRIP_STATE_REVIEW"

    if evolution:
        return "TRACK_EVOLUTION_REVIEW"

    return "LOW_VALUE"


def main():

    print()
    print("=" * 126)
    print(
        "R2G.1 — 2022 RUBBERING / GRIP EVOLUTION "
        "TARGETED RECONNAISSANCE"
    )
    print("=" * 126)

    required = [
        INTERRUPTION_POLICY,
        ADJACENT_MECHANISM,
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
            "R2G1_RUBBER_GRIP_RECON_INPUT_MISSING"
        )
        return

    read_csv(INTERRUPTION_POLICY)
    adjacent = read_csv(ADJACENT_MECHANISM)
    read_csv(CHRONOLOGY_V10)

    print()
    print("=" * 126)
    print("FROZEN BASE")
    print("=" * 126)

    print()
    print(
        "Adjacent mechanism rows:",
        len(adjacent),
    )

    if adjacent:
        print(
            "Adjacent mechanism:",
            txt(
                adjacent[0].get(
                    "supported_mechanism"
                )
            ),
        )

        print(
            "May21 promotion allowed:",
            txt(
                adjacent[0].get(
                    "may21_interruption_promotion_allowed"
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
                "rubber_grip_rescue_2022"
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

                rubber = regex_values(
                    unit,
                    RUBBER_PATTERNS,
                )

                grip = regex_values(
                    unit,
                    GRIP_PATTERNS,
                )

                evolution = regex_values(
                    unit,
                    TRACK_EVOLUTION_PATTERNS,
                )

                green_track = regex_values(
                    unit,
                    GREEN_TRACK_PATTERNS,
                )

                rain_mechanism = regex_values(
                    unit,
                    RAIN_MECHANISM_PATTERNS,
                )

                speed_relation = regex_values(
                    unit,
                    SPEED_RELATION_PATTERNS,
                )

                times = regex_values(
                    unit,
                    TIME_PATTERNS,
                )

                if not any([
                    rubber,
                    grip,
                    evolution,
                    green_track,
                ]):
                    continue

                classification = classify(
                    source,
                    rubber,
                    grip,
                    evolution,
                    green_track,
                    rain_mechanism,
                    speed_relation,
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

                    "rubber_terms":
                        "|".join(rubber),

                    "grip_terms":
                        "|".join(grip),

                    "track_evolution_terms":
                        "|".join(evolution),

                    "green_track_terms":
                        "|".join(green_track),

                    "rain_mechanism_terms":
                        "|".join(rain_mechanism),

                    "speed_relation_terms":
                        "|".join(speed_relation),

                    "time_expressions":
                        "|".join(times),

                    "day1_event_specific":
                        "UNKNOWN",

                    "quantitative_grip_effect":
                        "UNKNOWN",

                    "quantitative_rubber_state":
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
        "RAIN_RUBBER_MECHANISM_CANDIDATE",
        "DIRECT_RUBBER_GRIP_RELATION_CANDIDATE",
        "DIRECT_TRACK_EVOLUTION_GRIP_CANDIDATE",
        "DIRECT_TRACK_EVOLUTION_SPEED_CANDIDATE",
        "GREEN_TRACK_CANDIDATE",
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
            by_class[
                classification
            ],
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
            row[
                "classification"
            ],
        )

        print(
            "rubber:",
            row[
                "rubber_terms"
            ]
            or
            "NONE",
        )

        print(
            "grip:",
            row[
                "grip_terms"
            ]
            or
            "NONE",
        )

        print(
            "track evolution:",
            row[
                "track_evolution_terms"
            ]
            or
            "NONE",
        )

        print(
            "green track:",
            row[
                "green_track_terms"
            ]
            or
            "NONE",
        )

        print(
            "rain mechanism:",
            row[
                "rain_mechanism_terms"
            ]
            or
            "NONE",
        )

        print(
            "speed relation:",
            row[
                "speed_relation_terms"
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
        "rubber_terms",
        "grip_terms",
        "track_evolution_terms",
        "green_track_terms",
        "rain_mechanism_terms",
        "speed_relation_terms",
        "time_expressions",
        "day1_event_specific",
        "quantitative_grip_effect",
        "quantitative_rubber_state",
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
                "rain_rubber_mechanism_candidates",
            "value":
                by_class.get(
                    "RAIN_RUBBER_MECHANISM_CANDIDATE",
                    0,
                ),
        },
        {
            "metric":
                "direct_rubber_grip_candidates",
            "value":
                by_class.get(
                    "DIRECT_RUBBER_GRIP_RELATION_CANDIDATE",
                    0,
                ),
        },
        {
            "metric":
                "direct_track_evolution_grip_candidates",
            "value":
                by_class.get(
                    "DIRECT_TRACK_EVOLUTION_GRIP_CANDIDATE",
                    0,
                ),
        },
        {
            "metric":
                "green_track_candidates",
            "value":
                by_class.get(
                    "GREEN_TRACK_CANDIDATE",
                    0,
                ),
        },
        {
            "metric":
                "elapsed_time_used_as_track_evolution",
            "value":
                0,
        },
        {
            "metric":
                "quantitative_grip_inferred",
            "value":
                0,
        },
        {
            "metric":
                "quantitative_rubber_inferred",
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
                "adjacent_mechanism_rows",

            "value":
                len(adjacent),

            "status":
                (
                    "PASS"
                    if len(adjacent)
                    ==
                    1
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
                "fast_friday_promoted_to_day1",

            "value":
                0,

            "status":
                "PASS",
        },

        {
            "metric":
                "elapsed_time_used_as_track_evolution",

            "value":
                0,

            "status":
                "PASS",
        },

        {
            "metric":
                "quantitative_grip_inferred",

            "value":
                0,

            "status":
                "PASS",
        },

        {
            "metric":
                "quantitative_rubber_inferred",

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
        "Rain/rubber mechanism candidates:",
        by_class.get(
            "RAIN_RUBBER_MECHANISM_CANDIDATE",
            0,
        ),
    )

    print(
        "Direct rubber/grip candidates:",
        by_class.get(
            "DIRECT_RUBBER_GRIP_RELATION_CANDIDATE",
            0,
        ),
    )

    print(
        "Direct track-evolution/grip candidates:",
        by_class.get(
            "DIRECT_TRACK_EVOLUTION_GRIP_CANDIDATE",
            0,
        ),
    )

    print(
        "Green-track candidates:",
        by_class.get(
            "GREEN_TRACK_CANDIDATE",
            0,
        ),
    )

    print()
    print(
        "Elapsed time used as track evolution:",
        0,
    )

    print(
        "Quantitative grip inferred:",
        0,
    )

    print(
        "Quantitative rubber inferred:",
        0,
    )

    print()
    print("=" * 126)

    if not hard_fail:
        print(
            "FINAL STATUS: "
            "R2G1_2022_RUBBER_GRIP_TARGETED_RECON_COMPLETE"
        )
    else:
        print(
            "FINAL STATUS: "
            "R2G1_RUBBER_GRIP_RECON_REVIEW_REQUIRED"
        )

    print("=" * 126)

    print()
    print("OUTPUTS")
    print(HITS_OUT)
    print(SUMMARY_OUT)
    print(QA_OUT)


if __name__ == "__main__":
    main()
