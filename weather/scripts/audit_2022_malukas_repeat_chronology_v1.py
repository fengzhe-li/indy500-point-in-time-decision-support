from pathlib import Path
import csv
import re


PHASE = "R1G.29A"

CANONICAL = Path(
    "data/canonical/v1/attempts.csv"
)

RESULT_V3 = Path(
    "weather/output/"
    "chronology_rescue_2022_result_to_canonical_attempt_matches_v3.csv"
)

CHRONOLOGY_V8 = Path(
    "weather/output/"
    "unified_attempt_chronology_constraint_ledger_v8.csv"
)

ACTION_V5 = Path(
    "weather/output/"
    "unified_attempt_action_lane_ledger_v5.csv"
)

REPEAT_PAIR = Path(
    "weather/output/"
    "chronology_rescue_2022_repeat_pair_coverage_v1.csv"
)

OUTPUT_DIR = Path(
    "weather/output"
)

AUDIT_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_malukas_repeat_chronology_audit_v1.csv"
)

HITS_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_malukas_repeat_evidence_hits_v1.csv"
)

QA_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_malukas_repeat_chronology_audit_v1_qa.csv"
)


MALUKAS_FIRST_ID = "619575d3-e7eb-5cce-886f-0a8485b98eba"
MALUKAS_SECOND_ID = "85c917fa-1c7a-52cb-a47f-468b4bdae9a5"

EXPECTED_FIRST_SPEED = "231.233"
EXPECTED_SECOND_SPEED = "231.607"


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
        "weather/output"
    ),
]


TEXT_EXTENSIONS = {
    ".txt",
    ".md",
    ".csv",
    ".json",
    ".html",
    ".htm",
}


SECOND_RUN_TERMS = [
    "second attempt",
    "second run",
    "another attempt",
    "another run",
    "retake",
    "re-take",
    "retry",
    "rerun",
    "re-run",
    "went back out",
    "returned for another",
    "returned for a second",
    "made another attempt",
    "made a second attempt",
    "made another run",
    "made a second run",
    "tried again",
]

FIRST_RUN_TERMS = [
    "first attempt",
    "first run",
    "initial attempt",
    "initial run",
]

IMPROVEMENT_TERMS = [
    "improved",
    "improvement",
    "improving",
    "moved up",
    "gained",
    "faster",
    "better run",
]

STATUS_TERMS = [
    "retired",
    "withdrawn",
    "waved off",
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


def first(row, fields):
    for field in fields:
        value = txt(row.get(field))
        if value:
            return value
    return ""


def driver(row):
    return first(
        row,
        [
            "driver_name",
            "driver",
            "driver_full_name",
        ],
    )


def speed(row):
    return first(
        row,
        [
            "four_lap_average_speed_mph",
            "average_speed_mph",
            "speed_mph",
        ],
    )


def attempt_index(row):
    return first(
        row,
        [
            "car_attempt_index",
            "attempt_index",
        ],
    )


def official_status(row):
    return first(
        row,
        [
            "official_status",
            "status",
        ],
    )


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


def split_units(raw):
    raw = re.sub(
        r"(?is)<[^>]+>",
        " ",
        raw,
    )

    raw = normalize(raw)

    if not raw:
        return []

    return [
        normalize(part)
        for part in re.split(
            r"(?<=[.!?])\s+",
            raw,
        )
        if normalize(part)
    ]


def matches(text, terms):
    lower = text.lower()

    return [
        term
        for term in terms
        if term in lower
    ]


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
        if (
            "the_race"
            in lower
            or
            "therace"
            in lower
        ):
            return "SECONDARY_THE_RACE"

        if "autosport" in lower:
            return "SECONDARY_AUTOSPORT"

        if "nbc" in lower:
            return "SECONDARY_NBC"

        return "SECONDARY_EDITORIAL"

    if (
        "official_day1_session_details"
        in lower
    ):
        return "INDYCAR_OFFICIAL_RESULTS_OR_API"

    return "LOCAL_DERIVED_OR_OTHER"


def row_mentions(row, ids):
    fields = [
        "attempt_id",
        "subject_attempt_id",
        "related_attempt_id",
    ]

    return any(
        txt(row.get(field)) in ids
        for field in fields
    )


def main():

    print()
    print("=" * 118)
    print(
        "R1G.29A — 2022 DAVID MALUKAS "
        "REPEAT-ATTEMPT CHRONOLOGY RECONNAISSANCE"
    )
    print("=" * 118)

    required = [
        CANONICAL,
        RESULT_V3,
        CHRONOLOGY_V8,
        ACTION_V5,
        REPEAT_PAIR,
    ]

    print()
    print("INPUT CHECK")
    print("-" * 118)

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
            "MALUKAS_REPEAT_RECON_INPUT_MISSING"
        )
        return

    canonical = read_csv(
        CANONICAL
    )

    result_v3 = read_csv(
        RESULT_V3
    )

    chronology = read_csv(
        CHRONOLOGY_V8
    )

    action = read_csv(
        ACTION_V5
    )

    repeat_pair = read_csv(
        REPEAT_PAIR
    )

    canonical_by_id = {
        txt(row.get("attempt_id")): row
        for row in canonical
        if txt(row.get("attempt_id"))
    }

    result_by_id = {
        txt(row.get("attempt_id")): row
        for row in result_v3
        if txt(row.get("attempt_id"))
    }

    first_row = canonical_by_id.get(
        MALUKAS_FIRST_ID
    )

    second_row = canonical_by_id.get(
        MALUKAS_SECOND_ID
    )

    first_result = result_by_id.get(
        MALUKAS_FIRST_ID
    )

    second_result = result_by_id.get(
        MALUKAS_SECOND_ID
    )

    if (
        first_row is None
        or
        second_row is None
        or
        first_result is None
        or
        second_result is None
    ):
        print()
        print(
            "FINAL STATUS: "
            "MALUKAS_CANONICAL_GROUNDING_FAILED"
        )
        return

    first_ok = all([
        driver(first_row)
        ==
        "David Malukas",

        attempt_index(first_row)
        ==
        "1",

        speed(first_row)
        ==
        EXPECTED_FIRST_SPEED,
    ])

    second_ok = all([
        driver(second_row)
        ==
        "David Malukas",

        attempt_index(second_row)
        ==
        "2",

        speed(second_row)
        ==
        EXPECTED_SECOND_SPEED,
    ])

    repeat_rows = [
        row
        for row in repeat_pair
        if txt(
            row.get(
                "driver_name"
            )
        )
        ==
        "David Malukas"
    ]

    repeat_pair_ok = False

    if len(repeat_rows) == 1:

        rr = repeat_rows[0]

        repeat_pair_ok = all([
            txt(
                rr.get(
                    "first_attempt_id"
                )
            )
            ==
            MALUKAS_FIRST_ID,

            txt(
                rr.get(
                    "first_speed_mph"
                )
            )
            ==
            EXPECTED_FIRST_SPEED,

            txt(
                rr.get(
                    "second_attempt_id"
                )
            )
            ==
            MALUKAS_SECOND_ID,

            txt(
                rr.get(
                    "second_speed_mph"
                )
            )
            ==
            EXPECTED_SECOND_SPEED,
        ])

    print()
    print("=" * 118)
    print("CANONICAL GROUNDING")
    print("=" * 118)

    print()
    print(
        "First:",
        MALUKAS_FIRST_ID,
        "| index",
        repr(
            attempt_index(
                first_row
            )
        ),
        "| speed",
        repr(
            speed(
                first_row
            )
        ),
        "| official status",
        repr(
            official_status(
                first_result
            )
        ),
    )

    print(
        "Second:",
        MALUKAS_SECOND_ID,
        "| index",
        repr(
            attempt_index(
                second_row
            )
        ),
        "| speed",
        repr(
            speed(
                second_row
            )
        ),
        "| official status",
        repr(
            official_status(
                second_result
            )
        ),
    )

    print()
    print(
        "First grounding:",
        first_ok,
    )

    print(
        "Second grounding:",
        second_ok,
    )

    print(
        "Frozen repeat-pair grounding:",
        repeat_pair_ok,
    )

    malukas_ids = {
        MALUKAS_FIRST_ID,
        MALUKAS_SECOND_ID,
    }

    chrono_hits = [
        row
        for row in chronology
        if (
            row_mentions(
                row,
                malukas_ids,
            )
            or
            txt(
                row.get(
                    "driver_name"
                )
            )
            ==
            "David Malukas"
        )
    ]

    action_hits = [
        row
        for row in action
        if (
            row_mentions(
                row,
                malukas_ids,
            )
            or
            txt(
                row.get(
                    "driver_name"
                )
            )
            ==
            "David Malukas"
        )
    ]

    covered_ids = {
        txt(
            row.get(
                "attempt_id"
            )
        )
        for row in chronology
        if (
            txt(
                row.get(
                    "attempt_id"
                )
            )
            in
            malukas_ids
            and
            txt(
                row.get(
                    "chronology_usable"
                )
            ).lower()
            ==
            "true"
        )
    }

    missing_ids = sorted(
        malukas_ids
        -
        covered_ids
    )

    print()
    print("=" * 118)
    print("ACTIVE LEDGER STATE")
    print("=" * 118)

    print()
    print(
        "Chronology V8 Malukas hits:",
        len(
            chrono_hits
        ),
    )

    for i, row in enumerate(
        chrono_hits,
        start=1,
    ):
        print()
        print(
            f"CHRONOLOGY HIT {i}"
        )

        print(
            " attempt_id:",
            repr(
                txt(
                    row.get(
                        "attempt_id"
                    )
                )
            ),
        )

        print(
            " relation:",
            repr(
                txt(
                    row.get(
                        "ordering_relation"
                    )
                )
            ),
        )

        print(
            " related_attempt_id:",
            repr(
                txt(
                    row.get(
                        "related_attempt_id"
                    )
                )
            ),
        )

        print(
            " chronology_usable:",
            repr(
                txt(
                    row.get(
                        "chronology_usable"
                    )
                )
            ),
        )

        print(
            " action:",
            repr(
                txt(
                    row.get(
                        "action"
                    )
                )
            ),
        )

        print(
            " lane:",
            repr(
                txt(
                    row.get(
                        "lane"
                    )
                )
            ),
        )

    print()
    print(
        "Action V5 Malukas hits:",
        len(
            action_hits
        ),
    )

    print(
        "Chronology-covered Malukas attempts:",
        len(
            covered_ids
        ),
    )

    print(
        "Missing attempt IDs:",
        "|".join(
            missing_ids
        )
        or
        "NONE",
    )

    # --------------------------------------------------
    # Precision local evidence scan
    # --------------------------------------------------

    hit_rows = []
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
                "malukas_repeat_evidence_hits_v1"
                in path.name
            ):
                continue

            files_scanned += 1

            raw = safe_read(
                path
            )

            if not raw:
                continue

            low_raw = raw.lower()

            if (
                "david malukas"
                not in low_raw
                and
                "malukas, david"
                not in low_raw
            ):
                continue

            for unit_index, unit in enumerate(
                split_units(raw),
                start=1,
            ):

                low = unit.lower()

                if (
                    "david malukas"
                    not in low
                    and
                    "malukas, david"
                    not in low
                ):
                    continue

                speed_hits = [
                    s
                    for s in [
                        EXPECTED_FIRST_SPEED,
                        EXPECTED_SECOND_SPEED,
                    ]
                    if s in unit
                ]

                first_terms = matches(
                    unit,
                    FIRST_RUN_TERMS,
                )

                second_terms = matches(
                    unit,
                    SECOND_RUN_TERMS,
                )

                improvement_terms = matches(
                    unit,
                    IMPROVEMENT_TERMS,
                )

                status_terms = matches(
                    unit,
                    STATUS_TERMS,
                )

                if not any([
                    speed_hits,
                    first_terms,
                    second_terms,
                    improvement_terms,
                    status_terms,
                ]):
                    continue

                source = source_class(
                    path
                )

                source_native = source in {
                    "INDYCAR_OFFICIAL_EDITORIAL",
                    "SECONDARY_THE_RACE",
                    "SECONDARY_AUTOSPORT",
                    "SECONDARY_NBC",
                    "SECONDARY_EDITORIAL",
                }

                direct_repeat_semantic = (
                    len(
                        second_terms
                    )
                    >
                    0
                )

                strong_repeat_binding = (
                    source_native
                    and
                    direct_repeat_semantic
                    and
                    (
                        EXPECTED_FIRST_SPEED
                        in
                        speed_hits
                        or
                        EXPECTED_SECOND_SPEED
                        in
                        speed_hits
                        or
                        len(
                            improvement_terms
                        )
                        >
                        0
                    )
                )

                key = (
                    str(path),
                    unit,
                )

                if key in seen:
                    continue

                seen.add(
                    key
                )

                hit_rows.append({
                    "source_path":
                        str(path),

                    "source_class":
                        source,

                    "unit_index":
                        unit_index,

                    "text":
                        unit[:2200],

                    "speed_hits":
                        "|".join(
                            speed_hits
                        ),

                    "first_attempt_terms":
                        "|".join(
                            first_terms
                        ),

                    "second_attempt_terms":
                        "|".join(
                            second_terms
                        ),

                    "improvement_terms":
                        "|".join(
                            improvement_terms
                        ),

                    "status_terms":
                        "|".join(
                            status_terms
                        ),

                    "source_native":
                        str(
                            source_native
                        ),

                    "direct_repeat_semantic":
                        str(
                            direct_repeat_semantic
                        ),

                    "strong_repeat_binding":
                        str(
                            strong_repeat_binding
                        ),
                })

    direct_hits = [
        row
        for row in hit_rows
        if txt(
            row.get(
                "source_native"
            )
        ).lower()
        ==
        "true"
        and
        txt(
            row.get(
                "direct_repeat_semantic"
            )
        ).lower()
        ==
        "true"
    ]

    strong_hits = [
        row
        for row in hit_rows
        if txt(
            row.get(
                "strong_repeat_binding"
            )
        ).lower()
        ==
        "true"
    ]

    print()
    print("=" * 118)
    print("PRECISION LOCAL EVIDENCE")
    print("=" * 118)

    print()
    print(
        "Files scanned:",
        files_scanned,
    )

    print(
        "Malukas relevant units:",
        len(
            hit_rows
        ),
    )

    print(
        "Direct source-native repeat hits:",
        len(
            direct_hits
        ),
    )

    print(
        "Strong repeat binding hits:",
        len(
            strong_hits
        ),
    )

    for i, row in enumerate(
        hit_rows,
        start=1,
    ):

        print()
        print("-" * 118)
        print(
            f"HIT {i}"
        )

        print(
            row[
                "source_class"
            ]
        )

        print(
            row[
                "source_path"
            ]
        )

        print(
            "speeds:",
            row[
                "speed_hits"
            ]
            or
            "NONE",
        )

        print(
            "first:",
            row[
                "first_attempt_terms"
            ]
            or
            "NONE",
        )

        print(
            "second:",
            row[
                "second_attempt_terms"
            ]
            or
            "NONE",
        )

        print(
            "improvement:",
            row[
                "improvement_terms"
            ]
            or
            "NONE",
        )

        print(
            "status:",
            row[
                "status_terms"
            ]
            or
            "NONE",
        )

        print(
            "direct-repeat:",
            row[
                "direct_repeat_semantic"
            ],
            "| strong-binding:",
            row[
                "strong_repeat_binding"
            ],
        )

        print(
            row[
                "text"
            ]
        )

    audit_rows = [
        {
            "attempt_id":
                MALUKAS_FIRST_ID,

            "driver_name":
                "David Malukas",

            "car_attempt_index":
                attempt_index(
                    first_row
                ),

            "speed_mph":
                speed(
                    first_row
                ),

            "official_status":
                official_status(
                    first_result
                ),

            "chronology_covered":
                str(
                    MALUKAS_FIRST_ID
                    in
                    covered_ids
                ),
        },

        {
            "attempt_id":
                MALUKAS_SECOND_ID,

            "driver_name":
                "David Malukas",

            "car_attempt_index":
                attempt_index(
                    second_row
                ),

            "speed_mph":
                speed(
                    second_row
                ),

            "official_status":
                official_status(
                    second_result
                ),

            "chronology_covered":
                str(
                    MALUKAS_SECOND_ID
                    in
                    covered_ids
                ),
        },
    ]

    write_csv(
        AUDIT_OUT,
        audit_rows,
        [
            "attempt_id",
            "driver_name",
            "car_attempt_index",
            "speed_mph",
            "official_status",
            "chronology_covered",
        ],
    )

    write_csv(
        HITS_OUT,
        hit_rows,
        [
            "source_path",
            "source_class",
            "unit_index",
            "text",
            "speed_hits",
            "first_attempt_terms",
            "second_attempt_terms",
            "improvement_terms",
            "status_terms",
            "source_native",
            "direct_repeat_semantic",
            "strong_repeat_binding",
        ],
    )

    qa_rows = [
        {
            "metric":
                "first_grounding",

            "value":
                int(
                    first_ok
                ),

            "status":
                "PASS"
                if first_ok
                else "FAIL",
        },

        {
            "metric":
                "second_grounding",

            "value":
                int(
                    second_ok
                ),

            "status":
                "PASS"
                if second_ok
                else "FAIL",
        },

        {
            "metric":
                "frozen_repeat_pair_grounding",

            "value":
                int(
                    repeat_pair_ok
                ),

            "status":
                "PASS"
                if repeat_pair_ok
                else "FAIL",
        },

        {
            "metric":
                "chronology_covered_count",

            "value":
                len(
                    covered_ids
                ),

            "status":
                "PASS",
        },

        {
            "metric":
                "direct_repeat_hits",

            "value":
                len(
                    direct_hits
                ),

            "status":
                "PASS"
                if len(
                    direct_hits
                )
                >
                0
                else "REVIEW",
        },

        {
            "metric":
                "ledger_mutation",

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
    print("=" * 118)
    print("AUDIT SUMMARY")
    print("=" * 118)

    print()
    print(
        "Malukas canonical attempts:",
        2,
    )

    print(
        "Chronology-covered Malukas attempts:",
        len(
            covered_ids
        ),
    )

    print(
        "Missing Malukas IDs:",
        "|".join(
            missing_ids
        )
        or
        "NONE",
    )

    print(
        "Existing Malukas action rows:",
        len(
            action_hits
        ),
    )

    print(
        "Direct source-native repeat hits:",
        len(
            direct_hits
        ),
    )

    print(
        "Strong repeat binding hits:",
        len(
            strong_hits
        ),
    )

    print()
    print(
        "FINAL STATUS: "
        "MALUKAS_REPEAT_CHRONOLOGY_RECONNAISSANCE_COMPLETE"
    )

    print()
    print("OUTPUTS")
    print(AUDIT_OUT)
    print(HITS_OUT)
    print(QA_OUT)


if __name__ == "__main__":
    main()
