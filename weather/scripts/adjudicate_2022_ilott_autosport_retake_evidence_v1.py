from pathlib import Path
import csv
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


PHASE = "R1G.26D"

CANONICAL = Path(
    "data/canonical/v1/attempts.csv"
)

RESULT_MATCH_V3 = Path(
    "weather/output/"
    "chronology_rescue_2022_result_to_canonical_attempt_matches_v3.csv"
)

OUTPUT_DIR = Path(
    "weather/output"
)

EVIDENCE_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_ilott_autosport_retake_evidence_v1.csv"
)

ADJUDICATION_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_ilott_autosport_retake_adjudication_v1.csv"
)

SUMMARY_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_ilott_autosport_retake_adjudication_summary_v1.csv"
)

QA_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_ilott_autosport_retake_adjudication_v1_qa.csv"
)


SOURCE_URL = (
    "https://www.autosport.com/indycar/news/"
    "indy-500-sato-grosjean-johnson-into-top-12-fight-p13-33-set/"
    "10308540/"
)

SOURCE_TITLE = (
    "Indy 500: Sato, Grosjean, Johnson into top 12 fight"
)

SOURCE_PUBLICATION_DATE = "2022-05-22"

SOURCE_CLASS = "REPUTABLE_SECONDARY_EDITORIAL"

SOURCE_AUTHORITY = "AUTOSPORT"

SOURCE_QUOTE = (
    "Callum Ilott of Juncos Hollinger Racing was the first to do a "
    "retake run and improved by 0.7mph but only gained three places"
)

SOURCE_PARAPHRASE = (
    "Autosport reports that Callum Ilott was the first driver to make "
    "a retake run and that the retake improved his qualifying average "
    "by approximately 0.7 mph."
)

TARGET_DRIVER = "Callum Ilott"

EXPECTED_FIRST_ATTEMPT_ID = (
    "3cd6d98a-da75-5822-8dae-05e83ad8457c"
)

EXPECTED_SECOND_ATTEMPT_ID = (
    "8fa25fec-e5a6-5844-b3d7-f67c9dc91378"
)

EXPECTED_FIRST_SPEED = Decimal("230.212")
EXPECTED_SECOND_SPEED = Decimal("230.961")


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


def is_2022(row):
    if txt(
        row.get("year")
    ) == "2022":
        return True

    return "2022" in txt(
        row.get("session_id")
    )


def main():

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print()
    print("=" * 120)
    print(
        "R1G.26D — 2022 CALLUM ILOTT "
        "AUTOSPORT RETAKE EVIDENCE ADJUDICATION V1"
    )
    print("=" * 120)

    # ========================================================
    # INPUT CHECK
    # ========================================================

    required = [
        CANONICAL,
        RESULT_MATCH_V3,
    ]

    missing = []

    print()
    print("INPUT CHECK")
    print("-" * 120)

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
            "ILOTT_AUTOSPORT_RETAKE_ADJUDICATION_INPUT_MISSING"
        )
        return

    canonical = read_csv(
        CANONICAL
    )

    result_v3 = read_csv(
        RESULT_MATCH_V3
    )

    # ========================================================
    # CANONICAL ILOTT PAIR
    # ========================================================

    ilott = [
        row
        for row in canonical
        if (
            is_2022(row)
            and
            canonical_driver(row)
            ==
            TARGET_DRIVER
        )
    ]

    ilott = sorted(
        ilott,
        key=lambda row: int(
            txt(
                row.get(
                    "car_attempt_index"
                )
            )
            or "999"
        ),
    )

    print()
    print("=" * 120)
    print(
        "CANONICAL ILOTT PAIR"
    )
    print("=" * 120)

    print()
    print(
        "Canonical Ilott rows:",
        len(ilott),
    )

    for row in ilott:

        print()
        print(
            "attempt_id:",
            txt(
                row.get(
                    "attempt_id"
                )
            ),
        )

        print(
            "  index:",
            repr(
                txt(
                    row.get(
                        "car_attempt_index"
                    )
                )
            ),
        )

        print(
            "  speed:",
            canonical_speed(row),
        )

    if len(ilott) != 2:

        print()
        print(
            "FINAL STATUS: "
            "ILOTT_CANONICAL_PAIR_REVIEW_REQUIRED"
        )
        return

    first = ilott[0]
    second = ilott[1]

    first_id = txt(
        first.get(
            "attempt_id"
        )
    )

    second_id = txt(
        second.get(
            "attempt_id"
        )
    )

    first_speed = canonical_speed(
        first
    )

    second_speed = canonical_speed(
        second
    )

    # ========================================================
    # EXPECTED IDENTITY CHECK
    # ========================================================

    first_id_ok = (
        first_id
        ==
        EXPECTED_FIRST_ATTEMPT_ID
    )

    second_id_ok = (
        second_id
        ==
        EXPECTED_SECOND_ATTEMPT_ID
    )

    first_speed_ok = (
        first_speed
        ==
        EXPECTED_FIRST_SPEED
    )

    second_speed_ok = (
        second_speed
        ==
        EXPECTED_SECOND_SPEED
    )

    # ========================================================
    # DELTA CHECK
    # ========================================================

    speed_delta = (
        second_speed
        -
        first_speed
    )

    delta_one_decimal = (
        speed_delta.quantize(
            Decimal("0.1"),
            rounding=ROUND_HALF_UP,
        )
    )

    autosport_delta_compatible = (
        delta_one_decimal
        ==
        Decimal("0.7")
    )

    print()
    print("=" * 120)
    print(
        "RETAKE PERFORMANCE BINDING"
    )
    print("=" * 120)

    print()
    print(
        "First speed:",
        first_speed,
    )

    print(
        "Second speed:",
        second_speed,
    )

    print(
        "Exact delta:",
        speed_delta,
        "mph",
    )

    print(
        "Delta at Autosport precision:",
        delta_one_decimal,
        "mph",
    )

    print(
        "Autosport reported improvement:",
        "0.7 mph",
    )

    print(
        "Delta compatible:",
        autosport_delta_compatible,
    )

    # ========================================================
    # V3 LINK CHECK
    # ========================================================

    v3_by_id = {
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

    first_v3 = v3_by_id.get(
        first_id
    )

    second_v3 = v3_by_id.get(
        second_id
    )

    first_v3_found = (
        first_v3 is not None
    )

    second_v3_found = (
        second_v3 is not None
    )

    print()
    print("=" * 120)
    print(
        "RESULT-MATCH V3 CHECK"
    )
    print("=" * 120)

    print()
    print(
        "First attempt linked:",
        first_v3_found,
    )

    print(
        "Second attempt linked:",
        second_v3_found,
    )

    if first_v3:

        print(
            "First official row:",
            txt(
                first_v3.get(
                    "official_result_row"
                )
            ),
        )

        print(
            "First official status:",
            repr(
                txt(
                    first_v3.get(
                        "official_status"
                    )
                )
            ),
        )

    if second_v3:

        print(
            "Second official row:",
            txt(
                second_v3.get(
                    "official_result_row"
                )
            ),
        )

        print(
            "Second official status:",
            repr(
                txt(
                    second_v3.get(
                        "official_status"
                    )
                )
            ),
        )

    # ========================================================
    # EVIDENCE ADJUDICATION
    # ========================================================

    binding_pass = all([
        first_id_ok,
        second_id_ok,
        first_speed_ok,
        second_speed_ok,
        autosport_delta_compatible,
        first_v3_found,
        second_v3_found,
    ])

    if binding_pass:

        adjudication_status = (
            "PROMOTABLE_REPEAT_ORDERING_AND_RETAKE_SEMANTICS"
        )

        evidence_quality = "HIGH"

    else:

        adjudication_status = (
            "REVIEW_REQUIRED"
        )

        evidence_quality = "MEDIUM"

    evidence_rows = [
        {
            "evidence_id":
                "R1G26D-ILOTT-AUTOSPORT-RETAKE",

            "year":
                "2022",

            "driver":
                TARGET_DRIVER,

            "source_title":
                SOURCE_TITLE,

            "source_url":
                SOURCE_URL,

            "source_publication_date":
                SOURCE_PUBLICATION_DATE,

            "source_class":
                SOURCE_CLASS,

            "source_authority":
                SOURCE_AUTHORITY,

            "source_quote":
                SOURCE_QUOTE,

            "source_paraphrase":
                SOURCE_PARAPHRASE,

            "evidence_type":
                "REPEAT_ATTEMPT_ACTION_ORDERING",

            "subject_attempt_id":
                first_id,

            "related_attempt_id":
                second_id,

            "subject_speed_mph":
                str(first_speed),

            "related_speed_mph":
                str(second_speed),

            "observed_speed_delta_mph":
                str(speed_delta),

            "reported_speed_delta_mph":
                "0.7",

            "relation":
                "FIRST_ATTEMPT_BEFORE_RETAKE_ATTEMPT",

            "action":
                "RETAKE_RUN",

            "performance_effect":
                "IMPROVED_ON_RETAKE",

            "lane":
                "UNKNOWN",

            "queue_position":
                "UNKNOWN",

            "queue_wait":
                "UNKNOWN",

            "timestamp":
                "UNKNOWN",

            "withdrawal_semantics":
                "UNKNOWN",

            "evidence_quality":
                evidence_quality,

            "adjudication_status":
                adjudication_status,

            "notes":
                (
                    "Autosport explicitly identifies an Ilott retake "
                    "run and approximately 0.7 mph improvement. "
                    "Canonical pair delta is 0.749 mph. "
                    "No Lane 1/Lane 2, withdrawal, queue position, "
                    "queue wait, or exact timestamp is inferred."
                ),
        }
    ]

    adjudication_rows = [
        {
            "adjudication_id":
                "R1G26D-ADJ-001",

            "evidence_id":
                "R1G26D-ILOTT-AUTOSPORT-RETAKE",

            "subject_attempt_id":
                first_id,

            "related_attempt_id":
                second_id,

            "subject_role":
                "INITIAL_ATTEMPT",

            "related_role":
                "RETAKE_ATTEMPT",

            "relation":
                "FIRST_ATTEMPT_BEFORE_RETAKE_ATTEMPT",

            "action_semantics":
                "RETAKE_RUN",

            "performance_semantics":
                "IMPROVED_ON_RETAKE",

            "lane_semantics":
                "UNKNOWN",

            "withdrawal_semantics":
                "UNKNOWN",

            "queue_semantics":
                "UNKNOWN",

            "timestamp_semantics":
                "ORDERING_ONLY",

            "time_quality":
                "ORDERING_ONLY",

            "source_class":
                SOURCE_CLASS,

            "evidence_quality":
                evidence_quality,

            "promotion_ready":
                str(binding_pass),

            "canonical_mutation":
                "False",

            "interpretation":
                (
                    "The source directly establishes that Ilott made "
                    "a retake run and improved. The canonical two-run "
                    "pair is uniquely consistent with the reported "
                    "approximately 0.7 mph gain. This supports "
                    "attempt ordering and retake semantics only."
                ),
        }
    ]

    # ========================================================
    # WRITE
    # ========================================================

    write_csv(
        EVIDENCE_OUT,
        evidence_rows,
        [
            "evidence_id",
            "year",
            "driver",
            "source_title",
            "source_url",
            "source_publication_date",
            "source_class",
            "source_authority",
            "source_quote",
            "source_paraphrase",
            "evidence_type",
            "subject_attempt_id",
            "related_attempt_id",
            "subject_speed_mph",
            "related_speed_mph",
            "observed_speed_delta_mph",
            "reported_speed_delta_mph",
            "relation",
            "action",
            "performance_effect",
            "lane",
            "queue_position",
            "queue_wait",
            "timestamp",
            "withdrawal_semantics",
            "evidence_quality",
            "adjudication_status",
            "notes",
        ],
    )

    write_csv(
        ADJUDICATION_OUT,
        adjudication_rows,
        [
            "adjudication_id",
            "evidence_id",
            "subject_attempt_id",
            "related_attempt_id",
            "subject_role",
            "related_role",
            "relation",
            "action_semantics",
            "performance_semantics",
            "lane_semantics",
            "withdrawal_semantics",
            "queue_semantics",
            "timestamp_semantics",
            "time_quality",
            "source_class",
            "evidence_quality",
            "promotion_ready",
            "canonical_mutation",
            "interpretation",
        ],
    )

    summary_rows = [
        {
            "metric":
                "canonical_ilott_attempts",

            "value":
                len(ilott),
        },

        {
            "metric":
                "first_attempt_id_verified",

            "value":
                int(first_id_ok),
        },

        {
            "metric":
                "second_attempt_id_verified",

            "value":
                int(second_id_ok),
        },

        {
            "metric":
                "first_speed_verified",

            "value":
                int(first_speed_ok),
        },

        {
            "metric":
                "second_speed_verified",

            "value":
                int(second_speed_ok),
        },

        {
            "metric":
                "canonical_speed_delta_mph",

            "value":
                str(speed_delta),
        },

        {
            "metric":
                "canonical_delta_at_source_precision",

            "value":
                str(delta_one_decimal),
        },

        {
            "metric":
                "autosport_delta_compatible",

            "value":
                int(
                    autosport_delta_compatible
                ),
        },

        {
            "metric":
                "promotion_ready",

            "value":
                int(binding_pass),
        },

        {
            "metric":
                "lane_evidence",

            "value":
                0,
        },

        {
            "metric":
                "queue_wait_evidence",

            "value":
                0,
        },

        {
            "metric":
                "exact_timestamp_evidence",

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

    # ========================================================
    # QA
    # ========================================================

    qa_rows = [
        {
            "metric":
                "canonical_pair_exactly_two",

            "value":
                len(ilott),

            "status":
                (
                    "PASS"
                    if len(ilott) == 2
                    else "FAIL"
                ),
        },

        {
            "metric":
                "expected_attempt_ids_verified",

            "value":
                int(
                    first_id_ok
                    and
                    second_id_ok
                ),

            "status":
                (
                    "PASS"
                    if (
                        first_id_ok
                        and
                        second_id_ok
                    )
                    else "FAIL"
                ),
        },

        {
            "metric":
                "expected_speeds_verified",

            "value":
                int(
                    first_speed_ok
                    and
                    second_speed_ok
                ),

            "status":
                (
                    "PASS"
                    if (
                        first_speed_ok
                        and
                        second_speed_ok
                    )
                    else "FAIL"
                ),
        },

        {
            "metric":
                "reported_delta_compatible",

            "value":
                int(
                    autosport_delta_compatible
                ),

            "status":
                (
                    "PASS"
                    if autosport_delta_compatible
                    else "FAIL"
                ),
        },

        {
            "metric":
                "both_attempts_linked_in_v3",

            "value":
                int(
                    first_v3_found
                    and
                    second_v3_found
                ),

            "status":
                (
                    "PASS"
                    if (
                        first_v3_found
                        and
                        second_v3_found
                    )
                    else "FAIL"
                ),
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
                "withdrawal_inferred",

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
                "results_row_order_used_as_chronology",

            "value":
                0,

            "status":
                "PASS",
        },

        {
            "metric":
                "automatic_unified_ledger_mutation",

            "value":
                0,

            "status":
                "PASS",
        },

        {
            "metric":
                "canonical_mutated",

            "value":
                0,

            "status":
                "PASS",
        },

        {
            "metric":
                "phase5_to_phase8_mutated",

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

    # ========================================================
    # FINAL
    # ========================================================

    print()
    print("=" * 120)
    print(
        "ADJUDICATION RESULT"
    )
    print("=" * 120)

    print()
    print(
        "Evidence source:",
        SOURCE_AUTHORITY,
    )

    print(
        "Source publication date:",
        SOURCE_PUBLICATION_DATE,
    )

    print()
    print(
        "Supported relation:"
    )

    print(
        " ",
        first_id,
    )

    print(
        "      FIRST_ATTEMPT_BEFORE_RETAKE_ATTEMPT"
    )

    print(
        " ",
        second_id,
    )

    print()
    print(
        "Supported action semantics:",
        "RETAKE_RUN",
    )

    print(
        "Supported performance semantics:",
        "IMPROVED_ON_RETAKE",
    )

    print()
    print(
        "Lane:",
        "UNKNOWN",
    )

    print(
        "Withdrawal semantics:",
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
        binding_pass,
    )

    print()
    print(
        "No unified chronology/action ledger was modified."
    )

    print(
        "No canonical or Phase 5–8 data was modified."
    )

    print()
    print("=" * 120)

    if binding_pass:

        print(
            "FINAL STATUS: "
            "ILOTT_RETAKE_REPEAT_ORDERING_EVIDENCE_ADJUDICATED"
        )

    else:

        print(
            "FINAL STATUS: "
            "ILOTT_RETAKE_EVIDENCE_REVIEW_REQUIRED"
        )

    print("=" * 120)

    print()
    print("OUTPUTS")
    print(EVIDENCE_OUT)
    print(ADJUDICATION_OUT)
    print(SUMMARY_OUT)
    print(QA_OUT)


if __name__ == "__main__":
    main()
