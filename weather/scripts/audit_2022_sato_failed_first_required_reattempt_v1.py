from pathlib import Path
import csv
import html
import re
from decimal import Decimal, InvalidOperation


PHASE = "R1G.27"

CANONICAL = Path(
    "data/canonical/v1/attempts.csv"
)

RESULT_V3 = Path(
    "weather/output/"
    "chronology_rescue_2022_result_to_canonical_attempt_matches_v3.csv"
)

CHRONOLOGY_V5 = Path(
    "weather/output/"
    "unified_attempt_chronology_constraint_ledger_v5.csv"
)

ACTION_V3 = Path(
    "weather/output/"
    "unified_attempt_action_lane_ledger_v3.csv"
)

EVIDENCE_DIRS = [
    Path(
        "weather/evidence/rescue/"
        "official_2022_editorial_chronology"
    ),
    Path(
        "weather/evidence/rescue/"
        "official_lane_queue_live_resources"
    ),
    Path(
        "weather/evidence/rescue/"
        "official_day1_session_details"
    ),
]

OUTPUT_DIR = Path(
    "weather/output"
)

HITS_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_sato_required_reattempt_evidence_hits_v1.csv"
)

ADJUDICATION_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_sato_required_reattempt_adjudication_v1.csv"
)

SUMMARY_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_sato_required_reattempt_summary_v1.csv"
)

QA_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_sato_required_reattempt_v1_qa.csv"
)


FIRST_ATTEMPT_ID = (
    "3f221659-74ff-5901-97dc-08071a734690"
)

SECOND_ATTEMPT_ID = (
    "21e8c99e-b04c-516d-85a8-ccfbaed7ff46"
)

EXPECTED_DRIVER = "Takuma Sato"

EXPECTED_FIRST_SPEED = Decimal("232.196")
EXPECTED_SECOND_SPEED = Decimal("231.708")


# ------------------------------------------------------------
# Terms
# ------------------------------------------------------------

SATO_TERMS = [
    "takuma sato",
    "sato",
]

INVALIDATION_TERMS = [
    "invalidated",
    "disallowed",
    "deleted",
    "failed attempt",
    "penalty",
    "penalized",
    "penalised",
    "did not count",
    "would not count",
    "time was removed",
    "time removed",
]

REATTEMPT_TERMS = [
    "had to make another attempt",
    "had to make another qualifying attempt",
    "had to qualify again",
    "required to make another attempt",
    "required to make another qualifying attempt",
    "required another attempt",
    "forced to make another attempt",
    "forced to make another qualifying attempt",
    "second attempt",
    "another attempt",
    "another qualifying attempt",
    "qualify again",
    "requalify",
    "re-qualify",
]

FIRST_TERMS = [
    "first attempt",
    "first qualifying attempt",
    "first run",
]

SECOND_TERMS = [
    "second attempt",
    "second qualifying attempt",
    "second run",
    "another attempt",
    "another qualifying attempt",
]

DECELERATION_TERMS = [
    "deceleration lane",
]

QUALIFYING_LANE_TERMS = [
    "lane 1",
    "lane one",
    "lane 2",
    "lane two",
    "priority lane",
    "priority queue",
]


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------

def txt(v):
    return "" if v is None else str(v).strip()


def read_csv(path):
    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as f:
        reader = csv.DictReader(f)
        return list(reader)


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
        )
        writer.writeheader()
        writer.writerows(rows)


def decimal_value(v):
    raw = txt(v)

    if not raw:
        return None

    try:
        return Decimal(raw)
    except InvalidOperation:
        return None


def canonical_speed(row):
    for field in [
        "four_lap_average_speed_mph",
        "average_speed_mph",
        "speed_mph",
    ]:
        value = decimal_value(
            row.get(field)
        )

        if value is not None:
            return value

    return None


def canonical_driver(row):
    for field in [
        "driver_name",
        "driver",
        "driver_full_name",
    ]:
        value = txt(
            row.get(field)
        )

        if value:
            return value

    return ""


def normalize_space(text):
    return re.sub(
        r"\s+",
        " ",
        txt(text),
    ).strip()


def contains_sato(text):
    lower = normalize_space(
        text
    ).lower()

    return (
        "takuma sato" in lower
        or
        re.search(
            r"\bsato\b",
            lower,
        )
        is not None
    )


def matched_terms(text, terms):
    lower = normalize_space(
        text
    ).lower()

    return [
        term
        for term in terms
        if term in lower
    ]


def html_to_units(raw):
    s = html.unescape(
        txt(raw)
    )

    s = re.sub(
        r"(?is)</?(?:p|div|section|article|h[1-6]|li|ul|ol|blockquote|table|tr|td|th)[^>]*>",
        "\n",
        s,
    )

    s = re.sub(
        r"(?is)<br\s*/?>",
        "\n",
        s,
    )

    s = re.sub(
        r"(?is)<hr\s*/?>",
        "\n",
        s,
    )

    s = re.sub(
        r"(?is)<[^>]+>",
        " ",
        s,
    )

    units = []

    for block in s.splitlines():
        block = normalize_space(
            block
        )

        if not block:
            continue

        sentences = re.split(
            r"(?<=[.!?])\s+",
            block,
        )

        for sentence in sentences:
            sentence = normalize_space(
                sentence
            )

            if sentence:
                units.append(
                    sentence
                )

    return units


def plain_units(raw):
    raw = normalize_space(
        raw
    )

    if not raw:
        return []

    return [
        normalize_space(part)
        for part in re.split(
            r"(?<=[.!?])\s+",
            raw,
        )
        if normalize_space(part)
    ]


def safe_read(path):
    try:
        return path.read_text(
            encoding="utf-8",
            errors="replace",
        )
    except Exception:
        return ""


def text_like(path):
    return path.suffix.lower() in {
        ".txt",
        ".md",
        ".html",
        ".htm",
        ".json",
        ".csv",
    }


def source_class(path):
    lower = str(path).lower()

    if "official_2022_editorial_chronology" in lower:
        return "INDYCAR_OFFICIAL_EDITORIAL"

    if "official_day1_session_details" in lower:
        return "INDYCAR_OFFICIAL_RESULTS_OR_API"

    if "official_lane_queue_live_resources" in lower:
        return "INDYCAR_OFFICIAL_RESOURCE_RECON"

    return "LOCAL_EVIDENCE"


def row_contains_attempt(row, attempt_id):
    return attempt_id in " | ".join(
        txt(v)
        for v in row.values()
    )


# ------------------------------------------------------------
# Main
# ------------------------------------------------------------

def main():

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print()
    print("=" * 115)
    print(
        "R1G.27 — 2022 TAKUMA SATO "
        "FAILED-FIRST / REQUIRED-REATTEMPT AUDIT V1"
    )
    print("=" * 115)

    required = [
        CANONICAL,
        RESULT_V3,
        CHRONOLOGY_V5,
        ACTION_V3,
    ]

    missing = []

    print()
    print("INPUT CHECK")
    print("-" * 115)

    for path in required:

        exists = path.exists()

        print(
            f"{path}: "
            f"{'PRESENT' if exists else 'MISSING'}"
        )

        if not exists:
            missing.append(path)

    for path in EVIDENCE_DIRS:
        print(
            f"{path}: "
            f"{'PRESENT' if path.exists() else 'MISSING_OPTIONAL'}"
        )

    if missing:

        print()
        print(
            "FINAL STATUS: "
            "SATO_REQUIRED_REATTEMPT_AUDIT_INPUT_MISSING"
        )
        return

    canonical = read_csv(
        CANONICAL
    )

    result_v3 = read_csv(
        RESULT_V3
    )

    chronology_v5 = read_csv(
        CHRONOLOGY_V5
    )

    action_v3 = read_csv(
        ACTION_V3
    )

    # --------------------------------------------------------
    # Canonical pair grounding
    # --------------------------------------------------------

    canonical_by_id = {
        txt(
            row.get(
                "attempt_id"
            )
        ): row
        for row in canonical
        if txt(
            row.get(
                "attempt_id"
            )
        )
    }

    first = canonical_by_id.get(
        FIRST_ATTEMPT_ID
    )

    second = canonical_by_id.get(
        SECOND_ATTEMPT_ID
    )

    if first is None or second is None:

        print()
        print(
            "FINAL STATUS: "
            "SATO_CANONICAL_PAIR_MISSING"
        )
        return

    first_driver = canonical_driver(
        first
    )

    second_driver = canonical_driver(
        second
    )

    first_speed = canonical_speed(
        first
    )

    second_speed = canonical_speed(
        second
    )

    first_index = txt(
        first.get(
            "car_attempt_index"
        )
    )

    second_index = txt(
        second.get(
            "car_attempt_index"
        )
    )

    identity_ok = all([
        first_driver == EXPECTED_DRIVER,
        second_driver == EXPECTED_DRIVER,
        first_speed == EXPECTED_FIRST_SPEED,
        second_speed == EXPECTED_SECOND_SPEED,
        first_index == "1",
        second_index == "2",
    ])

    print()
    print("=" * 115)
    print(
        "CANONICAL SATO PAIR"
    )
    print("=" * 115)

    print()
    print(
        FIRST_ATTEMPT_ID,
        "| index",
        first_index,
        "|",
        first_speed,
    )

    print(
        SECOND_ATTEMPT_ID,
        "| index",
        second_index,
        "|",
        second_speed,
    )

    print()
    print(
        "Identity check:",
        identity_ok,
    )

    # --------------------------------------------------------
    # Result V3 grounding
    # --------------------------------------------------------

    result_by_id = {
        txt(
            row.get(
                "attempt_id"
            )
        ): row
        for row in result_v3
        if txt(
            row.get(
                "attempt_id"
            )
        )
    }

    first_result = result_by_id.get(
        FIRST_ATTEMPT_ID
    )

    second_result = result_by_id.get(
        SECOND_ATTEMPT_ID
    )

    result_grounding_ok = (
        first_result is not None
        and
        second_result is not None
    )

    first_official_status = (
        txt(
            first_result.get(
                "official_status"
            )
        )
        if first_result
        else ""
    )

    second_official_status = (
        txt(
            second_result.get(
                "official_status"
            )
        )
        if second_result
        else ""
    )

    print()
    print("=" * 115)
    print(
        "RESULT-MATCH V3 GROUNDING"
    )
    print("=" * 115)

    print()
    print(
        "First official status:",
        repr(
            first_official_status
        ),
    )

    print(
        "Second official status:",
        repr(
            second_official_status
        ),
    )

    print(
        "Result grounding:",
        result_grounding_ok,
    )

    # --------------------------------------------------------
    # Existing ledger state
    # --------------------------------------------------------

    chronology_hits = [
        row
        for row in chronology_v5
        if (
            row_contains_attempt(
                row,
                FIRST_ATTEMPT_ID,
            )
            or
            row_contains_attempt(
                row,
                SECOND_ATTEMPT_ID,
            )
        )
    ]

    action_hits = [
        row
        for row in action_v3
        if (
            row_contains_attempt(
                row,
                FIRST_ATTEMPT_ID,
            )
            or
            row_contains_attempt(
                row,
                SECOND_ATTEMPT_ID,
            )
        )
    ]

    print()
    print("=" * 115)
    print(
        "CURRENT LEDGER STATE"
    )
    print("=" * 115)

    print()
    print(
        "Chronology V5 Sato hits:",
        len(
            chronology_hits
        ),
    )

    print(
        "Action V3 Sato hits:",
        len(
            action_hits
        ),
    )

    # --------------------------------------------------------
    # Local official evidence scan
    # --------------------------------------------------------

    hit_rows = []

    files_scanned = 0
    hit_counter = 1

    for root in EVIDENCE_DIRS:

        if not root.exists():
            continue

        for path in sorted(
            root.rglob("*")
        ):

            if (
                not path.is_file()
                or
                not text_like(path)
            ):
                continue

            files_scanned += 1

            raw = safe_read(
                path
            )

            if not raw:
                continue

            if (
                path.suffix.lower()
                in {".html", ".htm"}
            ):
                units = html_to_units(
                    raw
                )
            else:
                units = plain_units(
                    raw
                )

            for idx, unit in enumerate(
                units,
                start=1,
            ):

                if not contains_sato(
                    unit
                ):
                    continue

                invalid_terms = matched_terms(
                    unit,
                    INVALIDATION_TERMS,
                )

                reattempt_terms = matched_terms(
                    unit,
                    REATTEMPT_TERMS,
                )

                first_terms = matched_terms(
                    unit,
                    FIRST_TERMS,
                )

                second_terms = matched_terms(
                    unit,
                    SECOND_TERMS,
                )

                deceleration_terms = matched_terms(
                    unit,
                    DECELERATION_TERMS,
                )

                qualifying_lane_terms = matched_terms(
                    unit,
                    QUALIFYING_LANE_TERMS,
                )

                speed_hits = []

                if "232.196" in unit:
                    speed_hits.append(
                        "232.196"
                    )

                if "231.708" in unit:
                    speed_hits.append(
                        "231.708"
                    )

                decision_relevant = any([
                    invalid_terms,
                    reattempt_terms,
                    first_terms,
                    second_terms,
                    speed_hits,
                    deceleration_terms,
                    qualifying_lane_terms,
                ])

                if not decision_relevant:
                    continue

                hit_rows.append({
                    "hit_id":
                        f"R1G27-H{hit_counter:04d}",

                    "source_class":
                        source_class(
                            path
                        ),

                    "source_path":
                        str(
                            path
                        ),

                    "unit_index":
                        idx,

                    "text":
                        unit,

                    "invalidation_terms":
                        "|".join(
                            invalid_terms
                        ),

                    "reattempt_terms":
                        "|".join(
                            reattempt_terms
                        ),

                    "first_terms":
                        "|".join(
                            first_terms
                        ),

                    "second_terms":
                        "|".join(
                            second_terms
                        ),

                    "speed_hits":
                        "|".join(
                            speed_hits
                        ),

                    "deceleration_lane_terms":
                        "|".join(
                            deceleration_terms
                        ),

                    "qualifying_lane_terms":
                        "|".join(
                            qualifying_lane_terms
                        ),

                    "promotion_status":
                        "REVIEW_REQUIRED",
                })

                hit_counter += 1

    print()
    print("=" * 115)
    print(
        "OFFICIAL EVIDENCE HITS"
    )
    print("=" * 115)

    print()
    print(
        "Files scanned:",
        files_scanned,
    )

    print(
        "Decision-relevant Sato hits:",
        len(
            hit_rows
        ),
    )

    for row in hit_rows:

        print()
        print(
            row[
                "hit_id"
            ],
            "|",
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

        print(
            "invalidation:",
            row[
                "invalidation_terms"
            ]
            or
            "NONE",
        )

        print(
            "reattempt:",
            row[
                "reattempt_terms"
            ]
            or
            "NONE",
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
            "deceleration lane:",
            row[
                "deceleration_lane_terms"
            ]
            or
            "NONE",
        )

        print(
            "qualifying Lane 1/2:",
            row[
                "qualifying_lane_terms"
            ]
            or
            "NONE",
        )

    # --------------------------------------------------------
    # Adjudication logic
    # --------------------------------------------------------

    official_editorial_hits = [
        row
        for row in hit_rows
        if row[
            "source_class"
        ] == "INDYCAR_OFFICIAL_EDITORIAL"
    ]

    official_invalidation = [
        row
        for row in official_editorial_hits
        if txt(
            row[
                "invalidation_terms"
            ]
        )
    ]

    official_reattempt = [
        row
        for row in official_editorial_hits
        if txt(
            row[
                "reattempt_terms"
            ]
        )
    ]

    official_first_speed = [
        row
        for row in hit_rows
        if "232.196"
        in txt(
            row[
                "speed_hits"
            ]
        )
    ]

    official_second_speed = [
        row
        for row in hit_rows
        if "231.708"
        in txt(
            row[
                "speed_hits"
            ]
        )
    ]

    direct_semantics_ready = (
        len(
            official_invalidation
        ) >= 1
        and
        len(
            official_reattempt
        ) >= 1
    )

    official_status_support = (
        first_official_status.lower()
        ==
        "failed attempt"
    )

    promotion_ready = all([
        identity_ok,
        result_grounding_ok,
        official_status_support,
        direct_semantics_ready,
    ])

    # qualifying lane evidence only counts if literal Lane 1/2
    direct_qualifying_lane_rows = [
        row
        for row in official_editorial_hits
        if txt(
            row[
                "qualifying_lane_terms"
            ]
        )
    ]

    deceleration_only_rows = [
        row
        for row in official_editorial_hits
        if (
            txt(
                row[
                    "deceleration_lane_terms"
                ]
            )
            and
            not txt(
                row[
                    "qualifying_lane_terms"
                ]
            )
        )
    ]

    adjudication_rows = [
        {
            "adjudication_id":
                "R1G27-ADJ-001",

            "year":
                "2022",

            "driver_name":
                EXPECTED_DRIVER,

            "subject_attempt_id":
                FIRST_ATTEMPT_ID,

            "related_attempt_id":
                SECOND_ATTEMPT_ID,

            "subject_speed_mph":
                str(
                    first_speed
                ),

            "related_speed_mph":
                str(
                    second_speed
                ),

            "subject_official_status":
                first_official_status,

            "relation":
                (
                    "FIRST_ATTEMPT_BEFORE_REQUIRED_REATTEMPT"
                    if promotion_ready
                    else "REVIEW_REQUIRED"
                ),

            "subject_semantic":
                (
                    "FIRST_ATTEMPT_INVALIDATED"
                    if promotion_ready
                    else "REVIEW_REQUIRED"
                ),

            "related_action":
                (
                    "REQUIRED_REATTEMPT_AFTER_INVALIDATION"
                    if promotion_ready
                    else "REVIEW_REQUIRED"
                ),

            "time_quality":
                (
                    "ORDERING_ONLY"
                    if promotion_ready
                    else "UNKNOWN"
                ),

            "lane":
                "UNKNOWN",

            "queue_position":
                "UNKNOWN",

            "queue_wait":
                "UNKNOWN",

            "exact_timestamp":
                "UNKNOWN",

            "direct_official_invalidation_rows":
                len(
                    official_invalidation
                ),

            "direct_official_reattempt_rows":
                len(
                    official_reattempt
                ),

            "direct_qualifying_lane_rows":
                len(
                    direct_qualifying_lane_rows
                ),

            "deceleration_lane_only_rows":
                len(
                    deceleration_only_rows
                ),

            "promotion_ready":
                str(
                    promotion_ready
                ),

            "notes":
                (
                    "Qualifying Lane 1/Lane 2 is not inferred. "
                    "'Deceleration lane' is treated as a distinct "
                    "track-exit concept and never as qualifying "
                    "Lane 1 or Lane 2."
                ),
        }
    ]

    # --------------------------------------------------------
    # Write
    # --------------------------------------------------------

    write_csv(
        HITS_OUT,
        hit_rows,
        [
            "hit_id",
            "source_class",
            "source_path",
            "unit_index",
            "text",
            "invalidation_terms",
            "reattempt_terms",
            "first_terms",
            "second_terms",
            "speed_hits",
            "deceleration_lane_terms",
            "qualifying_lane_terms",
            "promotion_status",
        ],
    )

    write_csv(
        ADJUDICATION_OUT,
        adjudication_rows,
        [
            "adjudication_id",
            "year",
            "driver_name",
            "subject_attempt_id",
            "related_attempt_id",
            "subject_speed_mph",
            "related_speed_mph",
            "subject_official_status",
            "relation",
            "subject_semantic",
            "related_action",
            "time_quality",
            "lane",
            "queue_position",
            "queue_wait",
            "exact_timestamp",
            "direct_official_invalidation_rows",
            "direct_official_reattempt_rows",
            "direct_qualifying_lane_rows",
            "deceleration_lane_only_rows",
            "promotion_ready",
            "notes",
        ],
    )

    summary_rows = [
        {
            "metric":
                "canonical_identity_verified",

            "value":
                int(
                    identity_ok
                ),
        },

        {
            "metric":
                "first_official_status",

            "value":
                first_official_status,
        },

        {
            "metric":
                "official_invalidation_hits",

            "value":
                len(
                    official_invalidation
                ),
        },

        {
            "metric":
                "official_required_reattempt_hits",

            "value":
                len(
                    official_reattempt
                ),
        },

        {
            "metric":
                "official_first_speed_hits",

            "value":
                len(
                    official_first_speed
                ),
        },

        {
            "metric":
                "official_second_speed_hits",

            "value":
                len(
                    official_second_speed
                ),
        },

        {
            "metric":
                "direct_qualifying_lane_hits",

            "value":
                len(
                    direct_qualifying_lane_rows
                ),
        },

        {
            "metric":
                "deceleration_lane_only_hits",

            "value":
                len(
                    deceleration_only_rows
                ),
        },

        {
            "metric":
                "existing_chronology_hits",

            "value":
                len(
                    chronology_hits
                ),
        },

        {
            "metric":
                "existing_action_hits",

            "value":
                len(
                    action_hits
                ),
        },

        {
            "metric":
                "promotion_ready",

            "value":
                int(
                    promotion_ready
                ),
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
                "canonical_identity_verified",

            "value":
                int(
                    identity_ok
                ),

            "status":
                "PASS"
                if identity_ok
                else "FAIL",
        },

        {
            "metric":
                "result_v3_grounded",

            "value":
                int(
                    result_grounding_ok
                ),

            "status":
                "PASS"
                if result_grounding_ok
                else "FAIL",
        },

        {
            "metric":
                "first_status_failed_attempt",

            "value":
                first_official_status,

            "status":
                "PASS"
                if official_status_support
                else "FAIL",
        },

        {
            "metric":
                "official_invalidation_semantics_found",

            "value":
                len(
                    official_invalidation
                ),

            "status":
                "PASS"
                if len(
                    official_invalidation
                ) >= 1
                else "FAIL",
        },

        {
            "metric":
                "official_required_reattempt_semantics_found",

            "value":
                len(
                    official_reattempt
                ),

            "status":
                "PASS"
                if len(
                    official_reattempt
                ) >= 1
                else "FAIL",
        },

        {
            "metric":
                "deceleration_lane_mapped_to_qualifying_lane",

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
                "queue_wait_inferred",

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

        {
            "metric":
                "phase5_to_phase8_mutation",

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
    print("=" * 115)
    print(
        "ADJUDICATION SUMMARY"
    )
    print("=" * 115)

    print()
    print(
        "Official invalidation semantics:",
        len(
            official_invalidation
        ),
    )

    print(
        "Official required-reattempt semantics:",
        len(
            official_reattempt
        ),
    )

    print(
        "Direct qualifying Lane 1/2 evidence:",
        len(
            direct_qualifying_lane_rows
        ),
    )

    print(
        "Deceleration-lane-only evidence:",
        len(
            deceleration_only_rows
        ),
    )

    print()
    print(
        "Supported relation:",
        (
            "FIRST_ATTEMPT_BEFORE_REQUIRED_REATTEMPT"
            if promotion_ready
            else "NOT YET"
        ),
    )

    print(
        "Supported action:",
        (
            "REQUIRED_REATTEMPT_AFTER_INVALIDATION"
            if promotion_ready
            else "NOT YET"
        ),
    )

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

    print()
    print(
        "Promotion ready:",
        promotion_ready,
    )

    print()
    print(
        "No ledger, canonical, or Phase 5–8 data was modified."
    )

    print()
    print("=" * 115)

    if promotion_ready:

        print(
            "FINAL STATUS: "
            "SATO_FAILED_FIRST_REQUIRED_REATTEMPT_ADJUDICATION_READY"
        )

    else:

        print(
            "FINAL STATUS: "
            "SATO_REQUIRED_REATTEMPT_EVIDENCE_REVIEW_REQUIRED"
        )

    print("=" * 115)

    print()
    print("OUTPUTS")
    print(HITS_OUT)
    print(ADJUDICATION_OUT)
    print(SUMMARY_OUT)
    print(QA_OUT)


if __name__ == "__main__":
    main()
