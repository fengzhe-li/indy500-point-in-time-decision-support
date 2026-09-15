from pathlib import Path
import csv


PHASE = "R1G.28B"

CANONICAL = Path(
    "data/canonical/v1/attempts.csv"
)

RESULT_V3 = Path(
    "weather/output/"
    "chronology_rescue_2022_result_to_canonical_attempt_matches_v3.csv"
)

CHRONOLOGY_V6 = Path(
    "weather/output/"
    "unified_attempt_chronology_constraint_ledger_v6.csv"
)

EDITORIAL_CANDIDATES = Path(
    "weather/output/"
    "chronology_rescue_2022_high_priority_editorial_candidates_v1.csv"
)

SATO_HITS = Path(
    "weather/output/"
    "chronology_rescue_2022_sato_required_reattempt_evidence_hits_v1.csv"
)

REPEAT_PAIR = Path(
    "weather/output/"
    "chronology_rescue_2022_repeat_pair_coverage_v1.csv"
)

OUT = Path(
    "weather/output/"
    "chronology_rescue_2022_marco_first_attempt_identity_binding_v1.csv"
)

QA_OUT = Path(
    "weather/output/"
    "chronology_rescue_2022_marco_first_attempt_identity_binding_v1_qa.csv"
)


SATO_FIRST_ID = "3f221659-74ff-5901-97dc-08071a734690"

MARCO_FIRST_ID = "c044edbc-0f6c-5aab-bdef-9c4156b50617"
MARCO_SECOND_ID = "63982b5e-7639-5140-a6a2-702a77c2fc85"

EXPECTED_FIRST_SPEED = "226.108"
EXPECTED_SECOND_SPEED = "230.345"


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
    with path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as f:
        w = csv.DictWriter(
            f,
            fieldnames=fields,
            extrasaction="ignore",
        )
        w.writeheader()
        w.writerows(rows)


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


def car_index(row):
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


def main():
    print()
    print("=" * 115)
    print(
        "R1G.28B — 2022 MARCO FIRST-ATTEMPT "
        "IDENTITY BINDING AUDIT"
    )
    print("=" * 115)

    required = [
        CANONICAL,
        RESULT_V3,
        CHRONOLOGY_V6,
        EDITORIAL_CANDIDATES,
        SATO_HITS,
        REPEAT_PAIR,
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

    if missing:
        print()
        print(
            "FINAL STATUS: "
            "MARCO_FIRST_ATTEMPT_IDENTITY_BINDING_INPUT_MISSING"
        )
        return

    canonical = read_csv(CANONICAL)
    result_v3 = read_csv(RESULT_V3)
    chronology = read_csv(CHRONOLOGY_V6)
    candidates = read_csv(EDITORIAL_CANDIDATES)
    sato_hits = read_csv(SATO_HITS)
    repeat_pair = read_csv(REPEAT_PAIR)

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

    marco_first = canonical_by_id.get(
        MARCO_FIRST_ID
    )

    marco_second = canonical_by_id.get(
        MARCO_SECOND_ID
    )

    if marco_first is None or marco_second is None:
        print()
        print(
            "FINAL STATUS: "
            "MARCO_CANONICAL_PAIR_MISSING"
        )
        return

    first_grounding_ok = all([
        driver(marco_first) == "Marco Andretti",
        car_index(marco_first) == "1",
        speed(marco_first) == EXPECTED_FIRST_SPEED,
    ])

    second_grounding_ok = all([
        driver(marco_second) == "Marco Andretti",
        car_index(marco_second) == "2",
        speed(marco_second) == EXPECTED_SECOND_SPEED,
    ])

    print()
    print("=" * 115)
    print("CANONICAL GROUNDING")
    print("=" * 115)

    print()
    print(
        "Marco first:",
        MARCO_FIRST_ID,
        "| index",
        repr(car_index(marco_first)),
        "| speed",
        repr(speed(marco_first)),
        "| status",
        repr(
            official_status(
                result_by_id.get(
                    MARCO_FIRST_ID,
                    {},
                )
            )
        ),
    )

    print(
        "Marco second:",
        MARCO_SECOND_ID,
        "| index",
        repr(car_index(marco_second)),
        "| speed",
        repr(speed(marco_second)),
        "| status",
        repr(
            official_status(
                result_by_id.get(
                    MARCO_SECOND_ID,
                    {},
                )
            )
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

    # --------------------------------------------------------
    # Frozen repeat-pair definition
    # --------------------------------------------------------

    repeat_rows = [
        row
        for row in repeat_pair
        if txt(row.get("driver_name")) == "Marco Andretti"
    ]

    repeat_pair_ok = False

    if len(repeat_rows) == 1:
        rr = repeat_rows[0]

        repeat_pair_ok = all([
            txt(rr.get("first_attempt_id")) == MARCO_FIRST_ID,
            txt(rr.get("first_speed_mph")) == EXPECTED_FIRST_SPEED,
            txt(rr.get("second_attempt_id")) == MARCO_SECOND_ID,
            txt(rr.get("second_speed_mph")) == EXPECTED_SECOND_SPEED,
        ])

    print()
    print("=" * 115)
    print("FROZEN REPEAT-PAIR GROUNDING")
    print("=" * 115)

    print()
    print(
        "Repeat pair rows:",
        len(repeat_rows),
    )

    print(
        "Frozen first/second identity matches:",
        repeat_pair_ok,
    )

    # --------------------------------------------------------
    # Official editorial evidence:
    # "next driver, Marco Andretti"
    # --------------------------------------------------------

    official_next_driver_hits = []

    for row in candidates:
        text = txt(
            row.get("text")
        )

        lower = text.lower()

        if (
            "marco andretti" in lower
            and
            "next driver" in lower
            and
            "sato" in lower
        ):
            official_next_driver_hits.append(
                row
            )

    for row in sato_hits:
        text = txt(
            row.get("text")
        )

        lower = text.lower()

        if (
            "marco andretti" in lower
            and
            "next driver" in lower
            and
            "sato" in lower
        ):
            official_next_driver_hits.append(
                row
            )

    # dedupe by text
    dedup = {}

    for row in official_next_driver_hits:
        text = txt(
            row.get("text")
        )

        if text:
            dedup[text] = row

    official_next_driver_hits = list(
        dedup.values()
    )

    print()
    print("=" * 115)
    print("OFFICIAL NEXT-DRIVER EVIDENCE")
    print("=" * 115)

    print()
    print(
        "Direct official next-driver hits:",
        len(
            official_next_driver_hits
        ),
    )

    for i, row in enumerate(
        official_next_driver_hits,
        start=1,
    ):
        print()
        print(
            f"HIT {i}:"
        )

        print(
            txt(
                row.get("text")
            )
        )

    next_driver_evidence_ok = (
        len(
            official_next_driver_hits
        )
        >= 1
    )

    # --------------------------------------------------------
    # Key binding logic
    #
    # Official text identifies Marco as the next driver.
    # Frozen canonical pair establishes Marco attempt index 1
    # is 226.108 and index 2 is 230.345.
    #
    # Therefore the qualifying attempt in the "next driver"
    # incident can bind to Marco's first attempt only if:
    # 1) pair index identity is verified;
    # 2) official incident concerns Marco's qualifying attempt;
    # 3) no competing pre-existing Marco attempt exists before
    #    index 1 in the canonical pair.
    # --------------------------------------------------------

    chronology_marco_ids = {
        txt(row.get("attempt_id"))
        for row in chronology
        if txt(row.get("driver_name")) == "Marco Andretti"
    }

    no_existing_conflicting_marco_chronology = (
        MARCO_FIRST_ID not in chronology_marco_ids
        and
        MARCO_SECOND_ID not in chronology_marco_ids
    )

    binding_ready = all([
        first_grounding_ok,
        second_grounding_ok,
        repeat_pair_ok,
        next_driver_evidence_ok,
        no_existing_conflicting_marco_chronology,
    ])

    relation_supported = (
        "SATO_232.196_BEFORE_MARCO_FIRST_ATTEMPT_226.108"
        if binding_ready
        else
        "NOT_YET"
    )

    print()
    print("=" * 115)
    print("IDENTITY BINDING RESULT")
    print("=" * 115)

    print()
    print(
        "No conflicting Marco chronology:",
        no_existing_conflicting_marco_chronology,
    )

    print(
        "Binding ready:",
        binding_ready,
    )

    print(
        "Supported relation:",
        relation_supported,
    )

    print(
        "Marco first attempt bound to:",
        (
            MARCO_FIRST_ID
            if binding_ready
            else
            "UNKNOWN"
        ),
    )

    print(
        "Marco first speed:",
        (
            EXPECTED_FIRST_SPEED
            if binding_ready
            else
            "UNKNOWN"
        ),
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

    out_rows = [
        {
            "phase":
                PHASE,

            "subject_attempt_id":
                SATO_FIRST_ID,

            "subject_driver":
                "Takuma Sato",

            "subject_speed_mph":
                "232.196",

            "related_attempt_id":
                (
                    MARCO_FIRST_ID
                    if binding_ready
                    else ""
                ),

            "related_driver":
                "Marco Andretti",

            "related_speed_mph":
                (
                    EXPECTED_FIRST_SPEED
                    if binding_ready
                    else ""
                ),

            "related_car_attempt_index":
                (
                    "1"
                    if binding_ready
                    else ""
                ),

            "relation":
                relation_supported,

            "time_quality":
                (
                    "ORDERING_ONLY"
                    if binding_ready
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
                    binding_ready
                ),

            "notes":
                (
                    "Binding uses direct official next-driver "
                    "editorial semantics plus frozen canonical "
                    "Marco first/second attempt identity. "
                    "No Lane, queue wait, or exact timestamp inferred."
                ),
        }
    ]

    write_csv(
        OUT,
        out_rows,
        [
            "phase",
            "subject_attempt_id",
            "subject_driver",
            "subject_speed_mph",
            "related_attempt_id",
            "related_driver",
            "related_speed_mph",
            "related_car_attempt_index",
            "relation",
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
                "marco_first_grounding",

            "value":
                int(
                    first_grounding_ok
                ),

            "status":
                "PASS"
                if first_grounding_ok
                else "FAIL",
        },

        {
            "metric":
                "marco_second_grounding",

            "value":
                int(
                    second_grounding_ok
                ),

            "status":
                "PASS"
                if second_grounding_ok
                else "FAIL",
        },

        {
            "metric":
                "frozen_repeat_pair_matches",

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
                "official_next_driver_evidence",

            "value":
                len(
                    official_next_driver_hits
                ),

            "status":
                "PASS"
                if next_driver_evidence_ok
                else "FAIL",
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
                "timestamp_inferred",

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
    print("=" * 115)

    if binding_ready:
        print(
            "FINAL STATUS: "
            "MARCO_FIRST_ATTEMPT_IDENTITY_BINDING_READY"
        )
    else:
        print(
            "FINAL STATUS: "
            "MARCO_FIRST_ATTEMPT_IDENTITY_BINDING_REVIEW_REQUIRED"
        )

    print("=" * 115)

    print()
    print("OUTPUTS")
    print(OUT)
    print(QA_OUT)


if __name__ == "__main__":
    main()
