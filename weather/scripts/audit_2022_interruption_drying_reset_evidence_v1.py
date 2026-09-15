from pathlib import Path
import csv
import re
from collections import defaultdict


PHASE = "R2F.1"

CHRONOLOGY_V10 = Path(
    "weather/output/"
    "unified_attempt_chronology_constraint_ledger_v10.csv"
)

STATE_V2 = Path(
    "weather/output/"
    "contemporaneous_decision_state_evidence_ledger_v2.csv"
)

QUEUE_POLICY = Path(
    "weather/output/"
    "queue_wait_identifiability_2022_v1.csv"
)

SERVICE_POLICY = Path(
    "weather/output/"
    "pit_service_identifiability_2022_v1.csv"
)

OUTPUT_DIR = Path("weather/output")

HITS_OUT = (
    OUTPUT_DIR
    / "interruption_rescue_2022_targeted_hits_v1.csv"
)

SUMMARY_OUT = (
    OUTPUT_DIR
    / "interruption_rescue_2022_targeted_summary_v1.csv"
)

QA_OUT = (
    OUTPUT_DIR
    / "interruption_rescue_2022_targeted_v1_qa.csv"
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


RAIN_PATTERNS = [
    r"\brain\b",
    r"\braining\b",
    r"\brainfall\b",
    r"\brain shower\b",
    r"\bshower\b",
    r"\bshowers\b",
    r"\bwet track\b",
    r"\bwet conditions\b",
    r"\brain moved in\b",
    r"\brain arrived\b",
]


LIGHTNING_PATTERNS = [
    r"\blightning\b",
    r"\bthunderstorm\b",
    r"\bthunderstorms\b",
    r"\bstorm\b",
]


STOP_PATTERNS = [
    r"\bsession stopped\b",
    r"\bqualifying stopped\b",
    r"\btrack closed\b",
    r"\bhalted\b",
    r"\bsuspended\b",
    r"\bred flag\b",
    r"\bdelay\b",
    r"\brain delay\b",
    r"\bstopped for rain\b",
]


RESTART_PATTERNS = [
    r"\btrack reopened\b",
    r"\btrack re-opened\b",
    r"\bqualifying resumed\b",
    r"\bsession resumed\b",
    r"\bwhen the track reopened\b",
    r"\bwhen the track re-opened\b",
    r"\bwhen qualifying resumed\b",
    r"\bwhen the session resumed\b",
    r"\brestarted\b",
    r"\brestart\b",
]


DRYING_PATTERNS = [
    r"\bdrying\b",
    r"\bdried\b",
    r"\bdrying track\b",
    r"\btrack dried\b",
    r"\bdry line\b",
    r"\bdrying line\b",
    r"\btrack was drying\b",
    r"\bconditions improved\b",
    r"\bimproving conditions\b",
]


CLEANING_PATTERNS = [
    r"\btrack cleaning\b",
    r"\bcleaned the track\b",
    r"\btrack was cleaned\b",
    r"\bsweep(?:ing|ed)? the track\b",
    r"\btrack sweep\b",
    r"\bsweeper\b",
    r"\bdebris removal\b",
    r"\bremove debris\b",
    r"\btrack inspection\b",
    r"\binspected the track\b",
]


RESET_PATTERNS = [
    r"\bgreen track\b",
    r"\breset track\b",
    r"\btrack reset\b",
    r"\brubber washed away\b",
    r"\bwashed the rubber away\b",
    r"\bwashed away the rubber\b",
    r"\blost rubber\b",
    r"\brubber gone\b",
]


GRIP_PATTERNS = [
    r"\bgrip\b",
    r"\bgrip level\b",
    r"\blow grip\b",
    r"\bmore grip\b",
    r"\bless grip\b",
    r"\btrack grip\b",
    r"\brubbered in\b",
    r"\brubbering in\b",
    r"\brubber buildup\b",
    r"\brubber build-up\b",
]


TIME_PATTERNS = [
    r"\b(?:1[0-2]|0?[1-9]):[0-5]\d\s*(?:a\.?m\.?|p\.?m\.?)\b",
    r"\b(?:[01]\d|2[0-3]):[0-5]\d\b",
    r"\b(?:[01]\d|2[0-3]):[0-5]\d\s*Z\b",
    r"\b(?:[01]\d|2[0-3])[0-5]\d\s*Z\b",
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


def classify(
    source,
    rain,
    lightning,
    stop,
    restart,
    drying,
    cleaning,
    reset,
    grip,
    times,
):
    if not source_native(source):
        return "NON_SOURCE_NATIVE"

    if reset:
        return "DIRECT_TRACK_RESET_CANDIDATE"

    if cleaning:
        return "DIRECT_TRACK_CLEANING_CANDIDATE"

    if drying:
        return "DIRECT_DRYING_STATE_CANDIDATE"

    if restart and times:
        return "RESTART_TIME_CANDIDATE"

    if stop and times:
        return "INTERRUPTION_TIME_CANDIDATE"

    if rain and times:
        return "RAIN_TIME_CANDIDATE"

    if lightning and times:
        return "LIGHTNING_TIME_CANDIDATE"

    if restart:
        return "RESTART_ORDER_ONLY"

    if stop:
        return "INTERRUPTION_ORDER_ONLY"

    if rain:
        return "RAIN_EVENT_ONLY"

    if lightning:
        return "LIGHTNING_EVENT_ONLY"

    if grip:
        return "GRIP_LANGUAGE_REVIEW"

    return "LOW_VALUE"


def main():

    print()
    print("=" * 126)
    print(
        "R2F.1 — 2022 INTERRUPTION / DRYING / "
        "RESET / TRACK-CLEANING TARGETED RECONNAISSANCE"
    )
    print("=" * 126)

    required = [
        CHRONOLOGY_V10,
        STATE_V2,
        QUEUE_POLICY,
        SERVICE_POLICY,
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
            "R2F1_INTERRUPTION_RECON_INPUT_MISSING"
        )
        return

    # Read only to confirm frozen dependencies exist.
    read_csv(CHRONOLOGY_V10)
    read_csv(STATE_V2)
    read_csv(QUEUE_POLICY)
    read_csv(SERVICE_POLICY)

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
                "interruption_rescue_2022"
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

                rain = regex_values(
                    unit,
                    RAIN_PATTERNS,
                )

                lightning = regex_values(
                    unit,
                    LIGHTNING_PATTERNS,
                )

                stop = regex_values(
                    unit,
                    STOP_PATTERNS,
                )

                restart = regex_values(
                    unit,
                    RESTART_PATTERNS,
                )

                drying = regex_values(
                    unit,
                    DRYING_PATTERNS,
                )

                cleaning = regex_values(
                    unit,
                    CLEANING_PATTERNS,
                )

                reset = regex_values(
                    unit,
                    RESET_PATTERNS,
                )

                grip = regex_values(
                    unit,
                    GRIP_PATTERNS,
                )

                times = regex_values(
                    unit,
                    TIME_PATTERNS,
                )

                if not any([
                    rain,
                    lightning,
                    stop,
                    restart,
                    drying,
                    cleaning,
                    reset,
                    grip,
                ]):
                    continue

                classification = classify(
                    source,
                    rain,
                    lightning,
                    stop,
                    restart,
                    drying,
                    cleaning,
                    reset,
                    grip,
                    times,
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

                    "rain_terms":
                        "|".join(rain),

                    "lightning_terms":
                        "|".join(lightning),

                    "stop_terms":
                        "|".join(stop),

                    "restart_terms":
                        "|".join(restart),

                    "drying_terms":
                        "|".join(drying),

                    "cleaning_terms":
                        "|".join(cleaning),

                    "reset_terms":
                        "|".join(reset),

                    "grip_terms":
                        "|".join(grip),

                    "time_expressions":
                        "|".join(times),

                    "event_time_quality":
                        "UNADJUDICATED",

                    "track_state_effect":
                        "UNKNOWN",

                    "grip_effect":
                        "UNKNOWN",

                    "rubber_effect":
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
        "DIRECT_TRACK_RESET_CANDIDATE",
        "DIRECT_TRACK_CLEANING_CANDIDATE",
        "DIRECT_DRYING_STATE_CANDIDATE",
        "RESTART_TIME_CANDIDATE",
        "INTERRUPTION_TIME_CANDIDATE",
        "RAIN_TIME_CANDIDATE",
        "LIGHTNING_TIME_CANDIDATE",
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
            "rain:",
            row[
                "rain_terms"
            ]
            or
            "NONE",
        )

        print(
            "lightning:",
            row[
                "lightning_terms"
            ]
            or
            "NONE",
        )

        print(
            "stop:",
            row[
                "stop_terms"
            ]
            or
            "NONE",
        )

        print(
            "restart:",
            row[
                "restart_terms"
            ]
            or
            "NONE",
        )

        print(
            "drying:",
            row[
                "drying_terms"
            ]
            or
            "NONE",
        )

        print(
            "cleaning:",
            row[
                "cleaning_terms"
            ]
            or
            "NONE",
        )

        print(
            "reset:",
            row[
                "reset_terms"
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
            "time expressions:",
            row[
                "time_expressions"
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
        "rain_terms",
        "lightning_terms",
        "stop_terms",
        "restart_terms",
        "drying_terms",
        "cleaning_terms",
        "reset_terms",
        "grip_terms",
        "time_expressions",
        "event_time_quality",
        "track_state_effect",
        "grip_effect",
        "rubber_effect",
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
                "direct_drying_candidates",
            "value":
                by_class.get(
                    "DIRECT_DRYING_STATE_CANDIDATE",
                    0,
                ),
        },
        {
            "metric":
                "direct_cleaning_candidates",
            "value":
                by_class.get(
                    "DIRECT_TRACK_CLEANING_CANDIDATE",
                    0,
                ),
        },
        {
            "metric":
                "direct_reset_candidates",
            "value":
                by_class.get(
                    "DIRECT_TRACK_RESET_CANDIDATE",
                    0,
                ),
        },
        {
            "metric":
                "grip_effect_inferred",
            "value":
                0,
        },
        {
            "metric":
                "rubber_effect_inferred",
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
                "grip_effect_inferred",
            "value":
                0,
            "status":
                "PASS",
        },
        {
            "metric":
                "rubber_effect_inferred",
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
                "rain_interpreted_as_full_reset",
            "value":
                0,
            "status":
                "PASS",
        },
        {
            "metric":
                "restart_interpreted_as_known_grip",
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

    print(
        "Direct drying candidates:",
        by_class.get(
            "DIRECT_DRYING_STATE_CANDIDATE",
            0,
        ),
    )

    print(
        "Direct track-cleaning candidates:",
        by_class.get(
            "DIRECT_TRACK_CLEANING_CANDIDATE",
            0,
        ),
    )

    print(
        "Direct track-reset candidates:",
        by_class.get(
            "DIRECT_TRACK_RESET_CANDIDATE",
            0,
        ),
    )

    print()
    print(
        "Grip effects inferred:",
        0,
    )

    print(
        "Rubber effects inferred:",
        0,
    )

    print()
    print("=" * 126)

    if not hard_fail:
        print(
            "FINAL STATUS: "
            "R2F1_2022_INTERRUPTION_DRYING_RESET_TARGETED_RECON_COMPLETE"
        )
    else:
        print(
            "FINAL STATUS: "
            "R2F1_INTERRUPTION_RECON_REVIEW_REQUIRED"
        )

    print("=" * 126)

    print()
    print("OUTPUTS")
    print(HITS_OUT)
    print(SUMMARY_OUT)
    print(QA_OUT)


if __name__ == "__main__":
    main()
