from pathlib import Path
import csv
import re


PHASE = "R1G.28D"

CANONICAL = Path(
    "data/canonical/v1/attempts.csv"
)

RESULT_V3 = Path(
    "weather/output/"
    "chronology_rescue_2022_result_to_canonical_attempt_matches_v3.csv"
)

CHRONOLOGY_V7 = Path(
    "weather/output/"
    "unified_attempt_chronology_constraint_ledger_v7.csv"
)

ACTION_V4 = Path(
    "weather/output/"
    "unified_attempt_action_lane_ledger_v4.csv"
)

MARCO_FIRST_BINDING = Path(
    "weather/output/"
    "chronology_rescue_2022_marco_first_attempt_identity_binding_v1.csv"
)

OUTPUT_DIR = Path(
    "weather/output"
)

HITS_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_marco_second_run_direct_evidence_hits_v1.csv"
)

ADJ_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_marco_second_run_direct_evidence_adjudication_v1.csv"
)

QA_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_marco_second_run_direct_evidence_v1_qa.csv"
)


MARCO_FIRST_ID = "c044edbc-0f6c-5aab-bdef-9c4156b50617"
MARCO_SECOND_ID = "63982b5e-7639-5140-a6a2-702a77c2fc85"

EXPECTED_FIRST_SPEED = "226.108"
EXPECTED_SECOND_SPEED = "230.345"


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


DIRECT_SECOND_RUN_TERMS = [
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
    "returned to the track",
    "returned for another",
    "returned for a second",
    "made another attempt",
    "made a second attempt",
    "made another run",
    "made a second run",
    "went again",
    "tried again",
]

IMPROVEMENT_TERMS = [
    "improved",
    "improvement",
    "improving",
    "moved up",
    "jumped",
    "gained",
    "faster",
    "better run",
]

FIRST_ATTEMPT_TERMS = [
    "first attempt",
    "first run",
    "initial attempt",
    "initial run",
]

STATUS_TERMS = [
    "retired",
    "withdrawn",
    "waved off",
]

LANE_TERMS = [
    "lane 1",
    "lane one",
    "lane 2",
    "lane two",
    "priority lane",
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

    parts = re.split(
        r"(?<=[.!?])\s+",
        raw,
    )

    return [
        normalize(part)
        for part in parts
        if normalize(part)
    ]


def matches(text, terms):
    lower = normalize(text).lower()

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
        "official_day1_session_details"
        in lower
    ):
        return "INDYCAR_OFFICIAL_RESULTS_OR_API"

    if (
        "secondary_2022_high_priority_chronology"
        in lower
    ):
        return "SECONDARY_EDITORIAL"

    if (
        "autosport"
        in lower
    ):
        return "SECONDARY_AUTOSPORT"

    if (
        "the_race"
        in lower
        or
        "therace"
        in lower
    ):
        return "SECONDARY_THE_RACE"

    if (
        "nbc"
        in lower
    ):
        return "SECONDARY_NBC"

    return "LOCAL_DERIVED_OR_OTHER"


def is_output_self_reference(path):
    name = path.name.lower()

    blocked = [
        "marco_second_run_direct_evidence_hits_v1",
        "marco_second_run_direct_evidence_adjudication_v1",
        "marco_second_run_direct_evidence_v1_qa",
    ]

    return any(
        item in name
        for item in blocked
    )


def main():
    print()
    print("=" * 118)
    print(
        "R1G.28D — 2022 MARCO SECOND-RUN "
        "DIRECT EVIDENCE AUDIT"
    )
    print("=" * 118)

    required = [
        CANONICAL,
        RESULT_V3,
        CHRONOLOGY_V7,
        ACTION_V4,
        MARCO_FIRST_BINDING,
    ]

    print()
    print("INPUT CHECK")
    print("-" * 118)

    missing = []

    for path in required:
        exists = path.exists()

        print(
            f"{path}: "
            f"{'PRESENT' if exists else 'MISSING'}"
        )

        if not exists:
            missing.append(path)

    if missing:
        print()
        print(
            "FINAL STATUS: "
            "MARCO_SECOND_RUN_AUDIT_INPUT_MISSING"
        )
        return

    canonical = read_csv(CANONICAL)
    result_v3 = read_csv(RESULT_V3)
    chronology = read_csv(CHRONOLOGY_V7)
    action = read_csv(ACTION_V4)
    first_binding = read_csv(
        MARCO_FIRST_BINDING
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
        MARCO_FIRST_ID
    )

    second_row = canonical_by_id.get(
        MARCO_SECOND_ID
    )

    first_result = result_by_id.get(
        MARCO_FIRST_ID
    )

    second_result = result_by_id.get(
        MARCO_SECOND_ID
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
            "MARCO_SECOND_RUN_CANONICAL_GROUNDING_FAILED"
        )
        return

    first_grounding_ok = all([
        driver(first_row) == "Marco Andretti",
        attempt_index(first_row) == "1",
        speed(first_row) == EXPECTED_FIRST_SPEED,
    ])

    second_grounding_ok = all([
        driver(second_row) == "Marco Andretti",
        attempt_index(second_row) == "2",
        speed(second_row) == EXPECTED_SECOND_SPEED,
    ])

    first_binding_ok = any(
        txt(
            row.get(
                "promotion_ready"
            )
        ).lower()
        ==
        "true"
        and
        txt(
            row.get(
                "related_attempt_id"
            )
        )
        ==
        MARCO_FIRST_ID
        for row in first_binding
    )

    print()
    print("=" * 118)
    print("CANONICAL / FIRST-BINDING GROUNDING")
    print("=" * 118)

    print()
    print(
        "First:",
        MARCO_FIRST_ID,
        "| index",
        repr(
            attempt_index(first_row)
        ),
        "| speed",
        repr(
            speed(first_row)
        ),
        "| official status",
        repr(
            official_status(first_result)
        ),
    )

    print(
        "Second:",
        MARCO_SECOND_ID,
        "| index",
        repr(
            attempt_index(second_row)
        ),
        "| speed",
        repr(
            speed(second_row)
        ),
        "| official status",
        repr(
            official_status(second_result)
        ),
    )

    print()
    print(
        "First grounding:",
        first_grounding_ok,
    )

    print(
        "Second grounding:",
        second_grounding_ok,
    )

    print(
        "First-attempt binding already ready:",
        first_binding_ok,
    )

    chrono_first_count = sum(
        1
        for row in chronology
        if txt(
            row.get(
                "attempt_id"
            )
        )
        ==
        MARCO_FIRST_ID
        and
        txt(
            row.get(
                "chronology_usable"
            )
        ).lower()
        ==
        "true"
    )

    chrono_second_count = sum(
        1
        for row in chronology
        if txt(
            row.get(
                "attempt_id"
            )
        )
        ==
        MARCO_SECOND_ID
        and
        txt(
            row.get(
                "chronology_usable"
            )
        ).lower()
        ==
        "true"
    )

    print()
    print(
        "Chronology V7 first count:",
        chrono_first_count,
    )

    print(
        "Chronology V7 second count:",
        chrono_second_count,
    )

    # --------------------------------------------------
    # Precision evidence scan
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
                or
                is_output_self_reference(path)
            ):
                continue

            files_scanned += 1

            raw = safe_read(path)

            if not raw:
                continue

            lower_raw = raw.lower()

            if (
                "marco andretti"
                not in lower_raw
                and
                "andretti, marco"
                not in lower_raw
            ):
                continue

            units = split_units(raw)

            for unit_index, unit in enumerate(
                units,
                start=1,
            ):

                lower = unit.lower()

                marco_present = (
                    "marco andretti"
                    in lower
                    or
                    "andretti, marco"
                    in lower
                )

                if not marco_present:
                    continue

                speed_hits = [
                    s
                    for s in [
                        EXPECTED_FIRST_SPEED,
                        EXPECTED_SECOND_SPEED,
                    ]
                    if s in unit
                ]

                second_terms = matches(
                    unit,
                    DIRECT_SECOND_RUN_TERMS,
                )

                improvement_terms = matches(
                    unit,
                    IMPROVEMENT_TERMS,
                )

                first_terms = matches(
                    unit,
                    FIRST_ATTEMPT_TERMS,
                )

                status_terms = matches(
                    unit,
                    STATUS_TERMS,
                )

                lane_terms = matches(
                    unit,
                    LANE_TERMS,
                )

                # Only keep potentially useful Marco units.
                relevant = any([
                    speed_hits,
                    second_terms,
                    improvement_terms,
                    first_terms,
                    status_terms,
                    lane_terms,
                ])

                if not relevant:
                    continue

                key = (
                    str(path),
                    unit,
                )

                if key in seen:
                    continue

                seen.add(key)

                direct_second_run_semantic = (
                    len(
                        second_terms
                    )
                    >
                    0
                )

                direct_second_speed = (
                    EXPECTED_SECOND_SPEED
                    in
                    speed_hits
                )

                direct_first_speed = (
                    EXPECTED_FIRST_SPEED
                    in
                    speed_hits
                )

                source = source_class(
                    path
                )

                source_native = source in {
                    "INDYCAR_OFFICIAL_EDITORIAL",
                    "SECONDARY_EDITORIAL",
                    "SECONDARY_AUTOSPORT",
                    "SECONDARY_THE_RACE",
                    "SECONDARY_NBC",
                }

                high_value = (
                    source_native
                    and
                    direct_second_run_semantic
                )

                very_high_value = (
                    source_native
                    and
                    direct_second_run_semantic
                    and
                    (
                        direct_second_speed
                        or
                        direct_first_speed
                        or
                        len(
                            improvement_terms
                        )
                        >
                        0
                    )
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

                    "second_run_terms":
                        "|".join(
                            second_terms
                        ),

                    "improvement_terms":
                        "|".join(
                            improvement_terms
                        ),

                    "first_attempt_terms":
                        "|".join(
                            first_terms
                        ),

                    "status_terms":
                        "|".join(
                            status_terms
                        ),

                    "lane_terms":
                        "|".join(
                            lane_terms
                        ),

                    "source_native":
                        str(
                            source_native
                        ),

                    "high_value":
                        str(
                            high_value
                        ),

                    "very_high_value":
                        str(
                            very_high_value
                        ),
                })

    print()
    print("=" * 118)
    print("PRECISION EVIDENCE HITS")
    print("=" * 118)

    print()
    print(
        "Files scanned:",
        files_scanned,
    )

    print(
        "Marco relevant units:",
        len(
            hit_rows
        ),
    )

    high_hits = [
        row
        for row in hit_rows
        if txt(
            row.get(
                "high_value"
            )
        ).lower()
        ==
        "true"
    ]

    very_high_hits = [
        row
        for row in hit_rows
        if txt(
            row.get(
                "very_high_value"
            )
        ).lower()
        ==
        "true"
    ]

    print(
        "High-value direct second-run hits:",
        len(
            high_hits
        ),
    )

    print(
        "Very-high-value hits:",
        len(
            very_high_hits
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
            "second-run:",
            row[
                "second_run_terms"
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
            "first-attempt:",
            row[
                "first_attempt_terms"
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
            "lane:",
            row[
                "lane_terms"
            ]
            or
            "NONE",
        )

        print(
            "high-value:",
            row[
                "high_value"
            ],
            "| very-high-value:",
            row[
                "very_high_value"
            ],
        )

        print(
            row[
                "text"
            ]
        )

    # --------------------------------------------------
    # Adjudication
    # --------------------------------------------------

    #
    # Promotion standard:
    #
    # At least one source-native unit must explicitly
    # identify Marco as making a second/repeat run.
    #
    # Stronger if it also mentions 230.345, 226.108,
    # or improvement.
    #
    # We DO NOT infer second-run chronology merely from:
    # - official result row ordering
    # - car_attempt_index alone
    # - presence of both speeds
    # - Retired status
    #

    direct_second_run_ready = (
        len(
            high_hits
        )
        >=
        1
    )

    strong_binding_ready = (
        len(
            very_high_hits
        )
        >=
        1
    )

    promotion_ready = all([
        first_grounding_ok,
        second_grounding_ok,
        first_binding_ok,
        chrono_first_count >= 1,
        chrono_second_count == 0,
        direct_second_run_ready,
    ])

    supported_relation = (
        "MARCO_226.108_FIRST_ATTEMPT_BEFORE_230.345_SECOND_RUN"
        if promotion_ready
        else
        "NOT_YET"
    )

    supported_action = (
        "SECOND_RUN"
        if promotion_ready
        else
        "NOT_YET"
    )

    print()
    print("=" * 118)
    print("ADJUDICATION")
    print("=" * 118)

    print()
    print(
        "Direct source-native second-run evidence:",
        direct_second_run_ready,
    )

    print(
        "Strong speed/improvement binding:",
        strong_binding_ready,
    )

    print(
        "Promotion ready:",
        promotion_ready,
    )

    print(
        "Supported relation:",
        supported_relation,
    )

    print(
        "Supported action:",
        supported_action,
    )

    print()
    print(
        "Lane:",
        "UNKNOWN",
    )

    print(
        "Queue:",
        "UNKNOWN",
    )

    print(
        "Exact timestamp:",
        "UNKNOWN",
    )

    adjudication_rows = [
        {
            "phase":
                PHASE,

            "first_attempt_id":
                MARCO_FIRST_ID,

            "first_speed_mph":
                EXPECTED_FIRST_SPEED,

            "second_attempt_id":
                MARCO_SECOND_ID,

            "second_speed_mph":
                EXPECTED_SECOND_SPEED,

            "direct_source_native_second_run_hits":
                len(
                    high_hits
                ),

            "strong_speed_or_improvement_hits":
                len(
                    very_high_hits
                ),

            "relation":
                supported_relation,

            "action":
                supported_action,

            "time_quality":
                (
                    "ORDERING_ONLY"
                    if promotion_ready
                    else
                    "UNKNOWN"
                ),

            "lane":
                "UNKNOWN",

            "queue":
                "UNKNOWN",

            "exact_timestamp":
                "UNKNOWN",

            "promotion_ready":
                str(
                    promotion_ready
                ),

            "notes":
                (
                    "Result-row ordering, canonical attempt index, "
                    "and presence of both speeds are not used alone "
                    "to establish chronology. Promotion requires "
                    "source-native Marco second/repeat-run semantics."
                ),
        }
    ]

    write_csv(
        HITS_OUT,
        hit_rows,
        [
            "source_path",
            "source_class",
            "unit_index",
            "text",
            "speed_hits",
            "second_run_terms",
            "improvement_terms",
            "first_attempt_terms",
            "status_terms",
            "lane_terms",
            "source_native",
            "high_value",
            "very_high_value",
        ],
    )

    write_csv(
        ADJ_OUT,
        adjudication_rows,
        [
            "phase",
            "first_attempt_id",
            "first_speed_mph",
            "second_attempt_id",
            "second_speed_mph",
            "direct_source_native_second_run_hits",
            "strong_speed_or_improvement_hits",
            "relation",
            "action",
            "time_quality",
            "lane",
            "queue",
            "exact_timestamp",
            "promotion_ready",
            "notes",
        ],
    )

    qa_rows = [
        {
            "metric":
                "first_grounding",

            "value":
                int(
                    first_grounding_ok
                ),

            "status":
                (
                    "PASS"
                    if first_grounding_ok
                    else "FAIL"
                ),
        },

        {
            "metric":
                "second_grounding",

            "value":
                int(
                    second_grounding_ok
                ),

            "status":
                (
                    "PASS"
                    if second_grounding_ok
                    else "FAIL"
                ),
        },

        {
            "metric":
                "first_binding_ready",

            "value":
                int(
                    first_binding_ok
                ),

            "status":
                (
                    "PASS"
                    if first_binding_ok
                    else "FAIL"
                ),
        },

        {
            "metric":
                "marco_first_in_v7",

            "value":
                chrono_first_count,

            "status":
                (
                    "PASS"
                    if chrono_first_count >= 1
                    else "FAIL"
                ),
        },

        {
            "metric":
                "marco_second_not_yet_in_v7",

            "value":
                chrono_second_count,

            "status":
                (
                    "PASS"
                    if chrono_second_count == 0
                    else "FAIL"
                ),
        },

        {
            "metric":
                "direct_second_run_hits",

            "value":
                len(
                    high_hits
                ),

            "status":
                (
                    "PASS"
                    if len(
                        high_hits
                    )
                    >=
                    1
                    else "REVIEW"
                ),
        },

        {
            "metric":
                "result_order_used_as_chronology",

            "value":
                0,

            "status":
                "PASS",
        },

        {
            "metric":
                "lane_inferred",

            "value":
                0,

            "status":
                "PASS",
        },

        {
            "metric":
                "queue_inferred",

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

    if promotion_ready:
        print(
            "FINAL STATUS: "
            "MARCO_SECOND_RUN_DIRECT_EVIDENCE_READY"
        )
    else:
        print(
            "FINAL STATUS: "
            "MARCO_SECOND_RUN_DIRECT_EVIDENCE_NOT_YET_SUFFICIENT"
        )

    print("=" * 118)

    print()
    print("OUTPUTS")
    print(HITS_OUT)
    print(ADJ_OUT)
    print(QA_OUT)


if __name__ == "__main__":
    main()
