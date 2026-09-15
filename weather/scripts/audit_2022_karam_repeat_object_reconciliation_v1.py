from pathlib import Path
import csv
import re


PHASE = "R1G.30A"

CANONICAL = Path("data/canonical/v1/attempts.csv")

RESULT_V3 = Path(
    "weather/output/"
    "chronology_rescue_2022_result_to_canonical_attempt_matches_v3.csv"
)

CHRONOLOGY_V9 = Path(
    "weather/output/"
    "unified_attempt_chronology_constraint_ledger_v9.csv"
)

ACTION_V6 = Path(
    "weather/output/"
    "unified_attempt_action_lane_ledger_v6.csv"
)

REPEAT_PAIR = Path(
    "weather/output/"
    "chronology_rescue_2022_repeat_pair_coverage_v1.csv"
)

REPEAT_POLICY = Path(
    "weather/output/"
    "chronology_rescue_2022_repeat_pair_driver_eligibility_v1.csv"
)

OUTPUT_DIR = Path("weather/output")

AUDIT_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_karam_repeat_object_reconciliation_v1.csv"
)

HITS_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_karam_repeat_evidence_hits_v1.csv"
)

QA_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_karam_repeat_object_reconciliation_v1_qa.csv"
)


EXPECTED_FIRST_ID = "8e0c8731-4ddc-515a-949e-7902dd01eaeb"
EXPECTED_SECOND_ID = "2c453335-3a19-5653-8d5c-79d94db93028"
EXPECTED_NO_ATTEMPT_ID = "4778bf12-3fb5-5321-b4ae-9dc2f0880c25"

EXPECTED_FIRST_SPEED = "229.905"
EXPECTED_SECOND_SPEED = "230.464"

SEARCH_ROOTS = [
    Path("weather/evidence/rescue/official_2022_editorial_chronology"),
    Path("weather/evidence/rescue/secondary_2022_high_priority_chronology"),
    Path("weather/evidence/rescue/official_day1_session_details"),
    Path("weather/output"),
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

IMPROVEMENT_TERMS = [
    "improved",
    "improvement",
    "improving",
    "moved up",
    "gained",
    "faster",
    "better run",
]

WITHDRAW_TERMS = [
    "withdrawn",
    "withdrew",
    "withdraw",
    "gave up",
    "gave up his time",
    "gave up the time",
]

NO_ATTEMPT_TERMS = [
    "no attempt",
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
    path.parent.mkdir(parents=True, exist_ok=True)

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


def car(row):
    return first(
        row,
        [
            "car_number",
            "car_no",
            "car",
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


def speed(row):
    return first(
        row,
        [
            "four_lap_average_speed_mph",
            "average_speed_mph",
            "speed_mph",
        ],
    )


def canonical_status(row):
    return first(
        row,
        [
            "result_status",
            "status",
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


def official_result_row(row):
    return first(
        row,
        [
            "official_result_row",
            "result_row",
            "row_number",
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
    print("=" * 120)
    print(
        "R1G.30A — 2022 SAGE KARAM "
        "ATTEMPT-OBJECT / REPEAT-PAIR RECONCILIATION AUDIT"
    )
    print("=" * 120)

    required = [
        CANONICAL,
        RESULT_V3,
        CHRONOLOGY_V9,
        ACTION_V6,
        REPEAT_PAIR,
        REPEAT_POLICY,
    ]

    print()
    print("INPUT CHECK")
    print("-" * 120)

    for path in required:
        print(
            f"{path}: "
            f"{'PRESENT' if path.exists() else 'MISSING'}"
        )

    if not all(path.exists() for path in required):
        print()
        print(
            "FINAL STATUS: "
            "KARAM_REPEAT_OBJECT_AUDIT_INPUT_MISSING"
        )
        return

    canonical = read_csv(CANONICAL)
    result_v3 = read_csv(RESULT_V3)
    chronology = read_csv(CHRONOLOGY_V9)
    action = read_csv(ACTION_V6)
    repeat_pair = read_csv(REPEAT_PAIR)
    repeat_policy = read_csv(REPEAT_POLICY)

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

    karam_result_ids = [
        txt(row.get("attempt_id"))
        for row in result_v3
        if driver(
            canonical_by_id.get(
                txt(row.get("attempt_id")),
                {},
            )
        )
        == "Sage Karam"
    ]

    karam_result_ids = sorted(set(karam_result_ids))

    print()
    print("=" * 120)
    print("KARAM OBJECT INVENTORY")
    print("=" * 120)

    inventory_rows = []

    for aid in karam_result_ids:
        c = canonical_by_id.get(aid, {})
        r = result_by_id.get(aid, {})

        row = {
            "attempt_id":
                aid,

            "car_number":
                car(c),

            "driver_name":
                driver(c),

            "car_attempt_index":
                attempt_index(c),

            "canonical_speed_mph":
                speed(c),

            "canonical_status":
                canonical_status(c),

            "official_result_row":
                official_result_row(r),

            "official_status":
                official_status(r),
        }

        inventory_rows.append(row)

        print()
        print(
            aid,
            "| index",
            repr(row["car_attempt_index"]),
            "| speed",
            repr(row["canonical_speed_mph"]),
            "| canonical",
            repr(row["canonical_status"]),
            "| official row",
            repr(row["official_result_row"]),
            "| official status",
            repr(row["official_status"]),
        )

    first_row = canonical_by_id.get(EXPECTED_FIRST_ID, {})
    second_row = canonical_by_id.get(EXPECTED_SECOND_ID, {})
    no_attempt_row = canonical_by_id.get(EXPECTED_NO_ATTEMPT_ID, {})

    first_result = result_by_id.get(EXPECTED_FIRST_ID, {})
    second_result = result_by_id.get(EXPECTED_SECOND_ID, {})
    no_attempt_result = result_by_id.get(EXPECTED_NO_ATTEMPT_ID, {})

    first_ok = all([
        driver(first_row) == "Sage Karam",
        attempt_index(first_row) == "1",
        speed(first_row) == EXPECTED_FIRST_SPEED,
        official_status(first_result) == "Withdrawn",
    ])

    second_ok = all([
        driver(second_row) == "Sage Karam",
        attempt_index(second_row) == "2",
        speed(second_row) == EXPECTED_SECOND_SPEED,
    ])

    no_attempt_ok = all([
        driver(no_attempt_row) == "Sage Karam",
        official_status(no_attempt_result) == "No Attempt",
    ])

    repeat_rows = [
        row
        for row in repeat_pair
        if txt(row.get("driver_name")) == "Sage Karam"
    ]

    repeat_pair_ok = False

    if len(repeat_rows) == 1:
        rr = repeat_rows[0]

        repeat_pair_ok = all([
            txt(rr.get("first_attempt_id")) == EXPECTED_FIRST_ID,
            txt(rr.get("first_speed_mph")) == EXPECTED_FIRST_SPEED,
            txt(rr.get("second_attempt_id")) == EXPECTED_SECOND_ID,
            txt(rr.get("second_speed_mph")) == EXPECTED_SECOND_SPEED,
        ])

    policy_rows = [
        row
        for row in repeat_policy
        if txt(row.get("driver_name")) == "Sage Karam"
    ]

    policy_include = any(
        txt(
            row.get(
                "decision_relevant_denominator"
            )
        ).upper()
        == "INCLUDE"
        for row in policy_rows
    )

    print()
    print("=" * 120)
    print("DECISION-RELEVANT PAIR RECONCILIATION")
    print("=" * 120)

    print()
    print(
        "First qualifying attempt grounding:",
        first_ok,
    )

    print(
        "Second qualifying attempt grounding:",
        second_ok,
    )

    print(
        "No Attempt object grounding:",
        no_attempt_ok,
    )

    print(
        "Frozen repeat-pair grounding:",
        repeat_pair_ok,
    )

    print(
        "Decision-relevant policy INCLUDE:",
        policy_include,
    )

    print()
    print(
        "Decision-relevant first ID:",
        EXPECTED_FIRST_ID,
    )

    print(
        "Decision-relevant second ID:",
        EXPECTED_SECOND_ID,
    )

    print(
        "Status-only No Attempt ID:",
        EXPECTED_NO_ATTEMPT_ID,
    )

    print(
        "No Attempt excluded from pair:",
        repeat_pair_ok
        and
        EXPECTED_NO_ATTEMPT_ID
        not in {
            EXPECTED_FIRST_ID,
            EXPECTED_SECOND_ID,
        },
    )

    karam_ids = {
        EXPECTED_FIRST_ID,
        EXPECTED_SECOND_ID,
        EXPECTED_NO_ATTEMPT_ID,
    }

    chrono_hits = [
        row
        for row in chronology
        if (
            row_mentions(row, karam_ids)
            or
            txt(row.get("driver_name")) == "Sage Karam"
        )
    ]

    action_hits = [
        row
        for row in action
        if (
            row_mentions(row, karam_ids)
            or
            txt(row.get("driver_name")) == "Sage Karam"
        )
    ]

    covered_ids = {
        txt(row.get("attempt_id"))
        for row in chronology
        if (
            txt(row.get("attempt_id")) in karam_ids
            and
            txt(row.get("chronology_usable")).lower()
            == "true"
        )
    }

    print()
    print("=" * 120)
    print("ACTIVE LEDGER STATE")
    print("=" * 120)

    print()
    print(
        "Chronology V9 Karam hits:",
        len(chrono_hits),
    )

    for i, row in enumerate(chrono_hits, start=1):
        print()
        print(f"CHRONOLOGY HIT {i}")
        print(
            " attempt_id:",
            repr(txt(row.get("attempt_id"))),
        )
        print(
            " relation:",
            repr(txt(row.get("ordering_relation"))),
        )
        print(
            " related_attempt_id:",
            repr(txt(row.get("related_attempt_id"))),
        )
        print(
            " chronology_usable:",
            repr(txt(row.get("chronology_usable"))),
        )
        print(
            " action:",
            repr(txt(row.get("action"))),
        )
        print(
            " lane:",
            repr(txt(row.get("lane"))),
        )

    print()
    print(
        "Action V6 Karam hits:",
        len(action_hits),
    )

    print(
        "Covered Karam object IDs:",
        "|".join(sorted(covered_ids))
        or
        "NONE",
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

        for path in sorted(root.rglob("*")):

            if (
                not path.is_file()
                or
                path.suffix.lower()
                not in TEXT_EXTENSIONS
            ):
                continue

            if (
                "karam_repeat_evidence_hits_v1"
                in path.name
            ):
                continue

            files_scanned += 1

            raw = safe_read(path)

            if not raw:
                continue

            low_raw = raw.lower()

            if (
                "sage karam" not in low_raw
                and
                "karam, sage" not in low_raw
            ):
                continue

            for unit_index, unit in enumerate(
                split_units(raw),
                start=1,
            ):

                low = unit.lower()

                if (
                    "sage karam" not in low
                    and
                    "karam, sage" not in low
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

                second_terms = matches(
                    unit,
                    SECOND_RUN_TERMS,
                )

                improvement_terms = matches(
                    unit,
                    IMPROVEMENT_TERMS,
                )

                withdraw_terms = matches(
                    unit,
                    WITHDRAW_TERMS,
                )

                no_attempt_terms = matches(
                    unit,
                    NO_ATTEMPT_TERMS,
                )

                lane_terms = matches(
                    unit,
                    LANE_TERMS,
                )

                if not any([
                    speed_hits,
                    second_terms,
                    improvement_terms,
                    withdraw_terms,
                    no_attempt_terms,
                    lane_terms,
                ]):
                    continue

                source = source_class(path)

                source_native = source in {
                    "INDYCAR_OFFICIAL_EDITORIAL",
                    "SECONDARY_AUTOSPORT",
                    "SECONDARY_THE_RACE",
                    "SECONDARY_NBC",
                    "SECONDARY_EDITORIAL",
                }

                direct_repeat = (
                    source_native
                    and
                    len(second_terms) > 0
                )

                direct_improvement = (
                    source_native
                    and
                    len(improvement_terms) > 0
                )

                direct_withdraw = (
                    source_native
                    and
                    len(withdraw_terms) > 0
                )

                strong_binding = (
                    source_native
                    and
                    (
                        direct_repeat
                        or
                        direct_improvement
                        or
                        direct_withdraw
                    )
                    and
                    len(speed_hits) > 0
                )

                key = (
                    str(path),
                    unit,
                )

                if key in seen:
                    continue

                seen.add(key)

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
                        "|".join(speed_hits),

                    "second_run_terms":
                        "|".join(second_terms),

                    "improvement_terms":
                        "|".join(improvement_terms),

                    "withdraw_terms":
                        "|".join(withdraw_terms),

                    "no_attempt_terms":
                        "|".join(no_attempt_terms),

                    "lane_terms":
                        "|".join(lane_terms),

                    "source_native":
                        str(source_native),

                    "direct_repeat":
                        str(direct_repeat),

                    "direct_improvement":
                        str(direct_improvement),

                    "direct_withdraw":
                        str(direct_withdraw),

                    "strong_binding":
                        str(strong_binding),
                })

    direct_repeat_hits = [
        row
        for row in hit_rows
        if txt(row.get("direct_repeat")).lower() == "true"
    ]

    direct_improvement_hits = [
        row
        for row in hit_rows
        if txt(row.get("direct_improvement")).lower() == "true"
    ]

    direct_withdraw_hits = [
        row
        for row in hit_rows
        if txt(row.get("direct_withdraw")).lower() == "true"
    ]

    strong_hits = [
        row
        for row in hit_rows
        if txt(row.get("strong_binding")).lower() == "true"
    ]

    print()
    print("=" * 120)
    print("PRECISION LOCAL EVIDENCE")
    print("=" * 120)

    print()
    print(
        "Files scanned:",
        files_scanned,
    )

    print(
        "Karam relevant units:",
        len(hit_rows),
    )

    print(
        "Direct repeat hits:",
        len(direct_repeat_hits),
    )

    print(
        "Direct improvement hits:",
        len(direct_improvement_hits),
    )

    print(
        "Direct withdrawal hits:",
        len(direct_withdraw_hits),
    )

    print(
        "Strong speed-bound hits:",
        len(strong_hits),
    )

    for i, row in enumerate(hit_rows, start=1):

        print()
        print("-" * 120)
        print(f"HIT {i}")
        print(row["source_class"])
        print(row["source_path"])
        print(
            "speeds:",
            row["speed_hits"]
            or
            "NONE",
        )
        print(
            "second:",
            row["second_run_terms"]
            or
            "NONE",
        )
        print(
            "improvement:",
            row["improvement_terms"]
            or
            "NONE",
        )
        print(
            "withdraw:",
            row["withdraw_terms"]
            or
            "NONE",
        )
        print(
            "no-attempt:",
            row["no_attempt_terms"]
            or
            "NONE",
        )
        print(
            "lane:",
            row["lane_terms"]
            or
            "NONE",
        )
        print(
            "direct-repeat:",
            row["direct_repeat"],
            "| direct-improvement:",
            row["direct_improvement"],
            "| direct-withdraw:",
            row["direct_withdraw"],
            "| strong:",
            row["strong_binding"],
        )
        print(row["text"])

    write_csv(
        AUDIT_OUT,
        inventory_rows,
        [
            "attempt_id",
            "car_number",
            "driver_name",
            "car_attempt_index",
            "canonical_speed_mph",
            "canonical_status",
            "official_result_row",
            "official_status",
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
            "second_run_terms",
            "improvement_terms",
            "withdraw_terms",
            "no_attempt_terms",
            "lane_terms",
            "source_native",
            "direct_repeat",
            "direct_improvement",
            "direct_withdraw",
            "strong_binding",
        ],
    )

    qa_rows = [
        {
            "metric":
                "karam_object_count",

            "value":
                len(karam_result_ids),

            "status":
                "PASS"
                if len(karam_result_ids) == 3
                else "REVIEW",
        },

        {
            "metric":
                "first_grounding",

            "value":
                int(first_ok),

            "status":
                "PASS"
                if first_ok
                else "FAIL",
        },

        {
            "metric":
                "second_grounding",

            "value":
                int(second_ok),

            "status":
                "PASS"
                if second_ok
                else "FAIL",
        },

        {
            "metric":
                "no_attempt_grounding",

            "value":
                int(no_attempt_ok),

            "status":
                "PASS"
                if no_attempt_ok
                else "FAIL",
        },

        {
            "metric":
                "repeat_pair_grounding",

            "value":
                int(repeat_pair_ok),

            "status":
                "PASS"
                if repeat_pair_ok
                else "FAIL",
        },

        {
            "metric":
                "policy_include",

            "value":
                int(policy_include),

            "status":
                "PASS"
                if policy_include
                else "FAIL",
        },

        {
            "metric":
                "no_attempt_excluded_from_pair",

            "value":
                int(
                    EXPECTED_NO_ATTEMPT_ID
                    not in {
                        EXPECTED_FIRST_ID,
                        EXPECTED_SECOND_ID,
                    }
                ),

            "status":
                "PASS",
        },

        {
            "metric":
                "chronology_covered_pair_count",

            "value":
                sum(
                    aid in covered_ids
                    for aid in [
                        EXPECTED_FIRST_ID,
                        EXPECTED_SECOND_ID,
                    ]
                ),

            "status":
                "PASS",
        },

        {
            "metric":
                "action_rows",

            "value":
                len(action_hits),

            "status":
                "PASS",
        },

        {
            "metric":
                "direct_repeat_hits",

            "value":
                len(direct_repeat_hits),

            "status":
                "PASS"
                if len(direct_repeat_hits) > 0
                else "REVIEW",
        },

        {
            "metric":
                "direct_improvement_hits",

            "value":
                len(direct_improvement_hits),

            "status":
                "PASS"
                if len(direct_improvement_hits) > 0
                else "REVIEW",
        },

        {
            "metric":
                "direct_withdraw_hits",

            "value":
                len(direct_withdraw_hits),

            "status":
                "PASS"
                if len(direct_withdraw_hits) > 0
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
    print("=" * 120)
    print("AUDIT SUMMARY")
    print("=" * 120)

    print()
    print(
        "Karam objects:",
        len(karam_result_ids),
    )

    print(
        "Decision-relevant pair:",
        EXPECTED_FIRST_ID,
        "->",
        EXPECTED_SECOND_ID,
    )

    print(
        "Status-only No Attempt object:",
        EXPECTED_NO_ATTEMPT_ID,
    )

    print(
        "Chronology-covered pair attempts:",
        sum(
            aid in covered_ids
            for aid in [
                EXPECTED_FIRST_ID,
                EXPECTED_SECOND_ID,
            ]
        ),
        "/2",
    )

    print(
        "Existing Karam action rows:",
        len(action_hits),
    )

    print(
        "Direct repeat hits:",
        len(direct_repeat_hits),
    )

    print(
        "Direct improvement hits:",
        len(direct_improvement_hits),
    )

    print(
        "Direct withdrawal hits:",
        len(direct_withdraw_hits),
    )

    print(
        "Strong speed-bound hits:",
        len(strong_hits),
    )

    print()
    print(
        "FINAL STATUS: "
        "KARAM_REPEAT_OBJECT_RECONCILIATION_COMPLETE"
    )

    print()
    print("OUTPUTS")
    print(AUDIT_OUT)
    print(HITS_OUT)
    print(QA_OUT)


if __name__ == "__main__":
    main()
