from pathlib import Path
import csv
from collections import Counter


# ============================================================
# PHASE
# ============================================================

PHASE = "R1G.25H"


# ============================================================
# INPUTS
# ============================================================

CANONICAL = Path(
    "data/canonical/v1/attempts.csv"
)

MATCH_V2 = Path(
    "weather/output/"
    "chronology_rescue_2022_result_to_canonical_attempt_matches_v2.csv"
)

OFFICIAL_RESULTS = Path(
    "weather/output/"
    "official_day1_results_attempt_rows_v1.csv"
)


# ============================================================
# OUTPUTS
# ============================================================

OUTPUT_DIR = Path(
    "weather/output"
)

MATCH_V3 = (
    OUTPUT_DIR
    / "chronology_rescue_2022_result_to_canonical_attempt_matches_v3.csv"
)

REPAIR_AUDIT_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_result_match_car_number_literal_repair_audit_v1.csv"
)

SUMMARY_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_result_match_car_number_literal_repair_summary_v1.csv"
)

QA_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_result_match_car_number_literal_repair_v1_qa.csv"
)


# ============================================================
# HELPERS
# ============================================================

def txt(v):
    return "" if v is None else str(v).strip()


def read_csv(path):
    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fields = list(reader.fieldnames or [])
        return rows, fields


def write_csv(path, rows, fields):
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


def speed_close(a, b, tol=0.003):
    try:
        return abs(
            float(txt(a))
            -
            float(txt(b))
        ) <= tol
    except Exception:
        return False


def canonical_speed(row):
    for field in [
        "four_lap_average_speed_mph",
        "average_speed_mph",
        "speed_mph",
    ]:
        value = txt(
            row.get(field)
        )
        if value:
            return value

    return ""


def is_2022(row):
    return (
        txt(row.get("year")) == "2022"
        or
        "2022" in txt(
            row.get("session_id")
        )
    )


def normalize_person_name(value):
    """
    Comparison helper only.

    Handles:
      'Helio Castroneves'
      'Castroneves, Helio'

    This is NOT used as an identity key.
    """

    raw = txt(value)

    if not raw:
        return ""

    if "," in raw:
        parts = [
            part.strip()
            for part in raw.split(",")
            if part.strip()
        ]

        if len(parts) == 2:
            raw = (
                parts[1]
                + " "
                + parts[0]
            )

    return " ".join(
        raw.lower()
        .replace(".", "")
        .replace("'", "")
        .replace("’", "")
        .replace("-", " ")
        .split()
    )


# ============================================================
# MAIN
# ============================================================

def main():

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print()
    print("=" * 120)
    print(
        "R1G.25H — 2022 RESULT-MATCH "
        "LITERAL CAR-NUMBER REPAIR V1"
    )
    print("=" * 120)

    inputs = [
        CANONICAL,
        MATCH_V2,
        OFFICIAL_RESULTS,
    ]

    missing = []

    print()
    print("INPUT CHECK")
    print("-" * 120)

    for path in inputs:

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
            "RESULT_MATCH_LITERAL_REPAIR_INPUT_MISSING"
        )
        return

    canonical, canonical_fields = read_csv(
        CANONICAL
    )

    match_v2, match_fields = read_csv(
        MATCH_V2
    )

    official, official_fields = read_csv(
        OFFICIAL_RESULTS
    )

    # ========================================================
    # CANONICAL MAP
    # ========================================================

    canonical_2022 = [
        row
        for row in canonical
        if is_2022(row)
    ]

    canonical_by_id = {
        txt(
            row.get("attempt_id")
        ): row
        for row in canonical_2022
        if txt(
            row.get("attempt_id")
        )
    }

    print()
    print(
        "Canonical 2022 attempts:",
        len(
            canonical_by_id
        ),
    )

    print(
        "V2 rows:",
        len(
            match_v2
        ),
    )

    # ========================================================
    # OFFICIAL RESULT ROW MAP
    # ========================================================

    official_2022_by_row = {}

    for row in official:

        if txt(
            row.get("year")
        ) != "2022":
            continue

        result_row = txt(
            row.get("result_row")
        )

        if result_row:
            official_2022_by_row[
                result_row
            ] = row

    print(
        "Official parsed 2022 rows:",
        len(
            official_2022_by_row
        ),
    )

    # ========================================================
    # V3 FIELDS
    # ========================================================

    v3_fields = list(
        match_fields
    )

    extra_fields = [
        "car_number_v2_original",
        "car_number_literal_repaired",
        "car_number_literal_source",
        "canonical_driver_name",
        "official_pdf_driver_name",
        "driver_identity_verified",
        "official_literal_car_number",
        "official_literal_car_number_matches_canonical",
        "repair_stage",
    ]

    for field in extra_fields:

        if field not in v3_fields:
            v3_fields.append(field)

    # ========================================================
    # ROW LOOP
    # ========================================================

    v3_rows = []
    audit_rows = []

    repaired_rows = 0
    missing_attempt_ids = 0
    speed_mismatches = 0
    canonical_driver_mismatches = 0
    official_literal_mismatches = 0
    official_row_missing = 0

    repair_counts = Counter()

    print()
    print("=" * 120)
    print(
        "ROW-BY-ROW REPAIR AUDIT"
    )
    print("=" * 120)

    for row_number, row in enumerate(
        match_v2,
        start=2,
    ):

        attempt_id = txt(
            row.get("attempt_id")
        )

        canonical_row = (
            canonical_by_id.get(
                attempt_id
            )
        )

        if canonical_row is None:

            missing_attempt_ids += 1

            print()
            print(
                "MISSING CANONICAL ATTEMPT:",
                attempt_id,
            )

            continue

        canonical_car = txt(
            canonical_row.get(
                "car_number"
            )
        )

        canonical_driver = txt(
            canonical_row.get(
                "driver_name"
            )
        )

        can_speed = canonical_speed(
            canonical_row
        )

        old_car = txt(
            row.get(
                "car_number"
            )
        )

        official_speed_value = txt(
            row.get(
                "official_speed_mph"
            )
        )

        speed_ok = (
            speed_close(
                official_speed_value,
                can_speed,
            )
            if official_speed_value
            and can_speed
            else True
        )

        if not speed_ok:
            speed_mismatches += 1

        official_result_row = txt(
            row.get(
                "official_result_row"
            )
        )

        raw = official_2022_by_row.get(
            official_result_row
        )

        if raw is None:

            official_row_missing += 1

            raw_car = ""
            raw_driver = ""

        else:

            raw_car = txt(
                raw.get(
                    "car_number"
                )
            )

            raw_driver = txt(
                raw.get(
                    "driver_name_pdf"
                )
            )

        match_driver = txt(
            row.get(
                "driver_name"
            )
        )

        canonical_driver_norm = (
            normalize_person_name(
                canonical_driver
            )
        )

        match_driver_norm = (
            normalize_person_name(
                match_driver
            )
        )

        raw_driver_norm = (
            normalize_person_name(
                raw_driver
            )
        )

        match_driver_ok = (
            bool(
                canonical_driver_norm
            )
            and
            bool(
                match_driver_norm
            )
            and
            canonical_driver_norm
            ==
            match_driver_norm
        )

        raw_driver_ok = (
            (
                canonical_driver_norm
                ==
                raw_driver_norm
            )
            if raw_driver_norm
            else False
        )

        driver_verified = (
            match_driver_ok
            and
            (
                raw_driver_ok
                if raw_driver
                else True
            )
        )

        if not driver_verified:
            canonical_driver_mismatches += 1

        official_literal_ok = (
            (
                raw_car
                ==
                canonical_car
            )
            if raw_car
            else False
        )

        if (
            raw_car
            and
            not official_literal_ok
        ):
            official_literal_mismatches += 1

        repaired = (
            old_car
            !=
            canonical_car
        )

        if repaired:

            repaired_rows += 1

            repair_counts[
                f"{old_car}->{canonical_car}"
            ] += 1

        out = {
            field: ""
            for field in v3_fields
        }

        for key, value in row.items():

            if key in out:
                out[key] = value

        # Actual literal repair
        out[
            "car_number"
        ] = canonical_car

        out[
            "car_number_v2_original"
        ] = old_car

        out[
            "car_number_literal_repaired"
        ] = str(
            repaired
        )

        out[
            "car_number_literal_source"
        ] = (
            "CANONICAL_ATTEMPT_ID_GROUNDED"
        )

        out[
            "canonical_driver_name"
        ] = canonical_driver

        out[
            "official_pdf_driver_name"
        ] = raw_driver

        out[
            "driver_identity_verified"
        ] = str(
            driver_verified
        )

        out[
            "official_literal_car_number"
        ] = raw_car

        out[
            "official_literal_car_number_matches_canonical"
        ] = str(
            official_literal_ok
        )

        out[
            "repair_stage"
        ] = "R1G25H"

        v3_rows.append(
            out
        )

        classification = (
            "LITERAL_CAR_NUMBER_REPAIRED"
            if repaired
            else
            "NO_LITERAL_REPAIR_REQUIRED"
        )

        audit_rows.append({
            "csv_row":
                row_number,

            "attempt_id":
                attempt_id,

            "official_result_row":
                official_result_row,

            "v2_car_number":
                old_car,

            "canonical_car_number":
                canonical_car,

            "official_raw_car_number":
                raw_car,

            "canonical_driver":
                canonical_driver,

            "v2_driver":
                match_driver,

            "official_pdf_driver":
                raw_driver,

            "canonical_speed_mph":
                can_speed,

            "v2_official_speed_mph":
                official_speed_value,

            "speed_matches":
                speed_ok,

            "driver_identity_verified":
                driver_verified,

            "official_literal_matches_canonical":
                official_literal_ok,

            "classification":
                classification,
        })

    # ========================================================
    # SPECIAL #06 / #6 CHECK
    # ========================================================

    collision_rows = [
        row
        for row in audit_rows
        if (
            row[
                "canonical_car_number"
            ]
            in {
                "06",
                "6",
            }
        )
    ]

    print()
    print("=" * 120)
    print(
        "#06 / #6 TARGET VERIFICATION"
    )
    print("=" * 120)

    for row in collision_rows:

        print()
        print(
            "attempt_id:",
            row[
                "attempt_id"
            ],
        )

        print(
            "  V2 car:",
            repr(
                row[
                    "v2_car_number"
                ]
            ),
        )

        print(
            "  V3/canonical car:",
            repr(
                row[
                    "canonical_car_number"
                ]
            ),
        )

        print(
            "  official raw car:",
            repr(
                row[
                    "official_raw_car_number"
                ]
            ),
        )

        print(
            "  canonical driver:",
            row[
                "canonical_driver"
            ],
        )

        print(
            "  V2 driver:",
            row[
                "v2_driver"
            ],
        )

        print(
            "  official driver:",
            row[
                "official_pdf_driver"
            ],
        )

        print(
            "  speed matches:",
            row[
                "speed_matches"
            ],
        )

        print(
            "  driver identity verified:",
            row[
                "driver_identity_verified"
            ],
        )

        print(
            "  classification:",
            row[
                "classification"
            ],
        )

    # ========================================================
    # GLOBAL V3 VALIDATION
    # ========================================================

    v3_attempt_ids = [
        txt(
            row.get(
                "attempt_id"
            )
        )
        for row in v3_rows
        if txt(
            row.get(
                "attempt_id"
            )
        )
    ]

    unique_v3_attempt_ids = (
        len(
            set(
                v3_attempt_ids
            )
        )
    )

    duplicate_v3_attempt_ids = (
        len(
            v3_attempt_ids
        )
        -
        unique_v3_attempt_ids
    )

    v3_car06_rows = [
        row
        for row in v3_rows
        if txt(
            row.get(
                "car_number"
            )
        ) == "06"
    ]

    v3_car6_rows = [
        row
        for row in v3_rows
        if txt(
            row.get(
                "car_number"
            )
        ) == "6"
    ]

    # ========================================================
    # WRITE
    # ========================================================

    write_csv(
        MATCH_V3,
        v3_rows,
        v3_fields,
    )

    write_csv(
        REPAIR_AUDIT_OUT,
        audit_rows,
        [
            "csv_row",
            "attempt_id",
            "official_result_row",
            "v2_car_number",
            "canonical_car_number",
            "official_raw_car_number",
            "canonical_driver",
            "v2_driver",
            "official_pdf_driver",
            "canonical_speed_mph",
            "v2_official_speed_mph",
            "speed_matches",
            "driver_identity_verified",
            "official_literal_matches_canonical",
            "classification",
        ],
    )

    summary_rows = [
        {
            "metric":
                "v2_rows",

            "value":
                len(
                    match_v2
                ),
        },

        {
            "metric":
                "v3_rows",

            "value":
                len(
                    v3_rows
                ),
        },

        {
            "metric":
                "literal_car_number_repairs",

            "value":
                repaired_rows,
        },

        {
            "metric":
                "missing_canonical_attempt_ids",

            "value":
                missing_attempt_ids,
        },

        {
            "metric":
                "speed_mismatches",

            "value":
                speed_mismatches,
        },

        {
            "metric":
                "driver_identity_verification_failures",

            "value":
                canonical_driver_mismatches,
        },

        {
            "metric":
                "official_literal_vs_canonical_mismatches",

            "value":
                official_literal_mismatches,
        },

        {
            "metric":
                "official_result_rows_missing",

            "value":
                official_row_missing,
        },

        {
            "metric":
                "duplicate_v3_attempt_ids",

            "value":
                duplicate_v3_attempt_ids,
        },

        {
            "metric":
                "v3_car06_rows",

            "value":
                len(
                    v3_car06_rows
                ),
        },

        {
            "metric":
                "v3_car6_rows",

            "value":
                len(
                    v3_car6_rows
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

    # ========================================================
    # QA
    # ========================================================

    qa_rows = [
        {
            "metric":
                "row_count_preserved",

            "value":
                (
                    len(
                        v3_rows
                    )
                    ==
                    len(
                        match_v2
                    )
                ),

            "status":
                (
                    "PASS"
                    if len(
                        v3_rows
                    )
                    ==
                    len(
                        match_v2
                    )
                    else "FAIL"
                ),
        },

        {
            "metric":
                "all_attempt_ids_grounded",

            "value":
                missing_attempt_ids,

            "status":
                (
                    "PASS"
                    if missing_attempt_ids == 0
                    else "FAIL"
                ),
        },

        {
            "metric":
                "speed_consistency",

            "value":
                speed_mismatches,

            "status":
                (
                    "PASS"
                    if speed_mismatches == 0
                    else "FAIL"
                ),
        },

        {
            "metric":
                "driver_identity_consistency",

            "value":
                canonical_driver_mismatches,

            "status":
                (
                    "PASS"
                    if canonical_driver_mismatches == 0
                    else "FAIL"
                ),
        },

        {
            "metric":
                "official_literal_consistency",

            "value":
                official_literal_mismatches,

            "status":
                (
                    "PASS"
                    if official_literal_mismatches == 0
                    else "FAIL"
                ),
        },

        {
            "metric":
                "duplicate_attempt_ids",

            "value":
                duplicate_v3_attempt_ids,

            "status":
                (
                    "PASS"
                    if duplicate_v3_attempt_ids == 0
                    else "FAIL"
                ),
        },

        {
            "metric":
                "v2_mutated",

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
                "matching_algorithm_rerun",

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
    # PRINT SUMMARY
    # ========================================================

    print()
    print("=" * 120)
    print(
        "REPAIR SUMMARY"
    )
    print("=" * 120)

    print()
    print(
        "V2 rows:",
        len(
            match_v2
        ),
    )

    print(
        "V3 rows:",
        len(
            v3_rows
        ),
    )

    print(
        "Literal car-number repairs:",
        repaired_rows,
    )

    if repair_counts:

        print()
        print(
            "Repair transformations:"
        )

        for key, value in sorted(
            repair_counts.items()
        ):

            print(
                f"  {key}: {value}"
            )

    print()
    print(
        "Missing canonical attempt IDs:",
        missing_attempt_ids,
    )

    print(
        "Speed mismatches:",
        speed_mismatches,
    )

    print(
        "Driver identity verification failures:",
        canonical_driver_mismatches,
    )

    print(
        "Official literal/canonical mismatches:",
        official_literal_mismatches,
    )

    print(
        "Duplicate V3 attempt IDs:",
        duplicate_v3_attempt_ids,
    )

    print()
    print(
        "V3 #06 rows:",
        len(
            v3_car06_rows
        ),
    )

    print(
        "V3 #6 rows:",
        len(
            v3_car6_rows
        ),
    )

    print()
    print(
        "V2 was preserved unchanged."
    )

    print(
        "No matching algorithm was rerun."
    )

    print(
        "No canonical data was modified."
    )

    print()
    print("=" * 120)

    success = (
        len(
            v3_rows
        )
        ==
        len(
            match_v2
        )
        and
        missing_attempt_ids == 0
        and
        speed_mismatches == 0
        and
        canonical_driver_mismatches == 0
        and
        official_literal_mismatches == 0
        and
        duplicate_v3_attempt_ids == 0
    )

    if success:

        print(
            "FINAL STATUS: "
            "RESULT_MATCH_V3_LITERAL_CAR_NUMBER_REPAIR_COMPLETE"
        )

    else:

        print(
            "FINAL STATUS: "
            "RESULT_MATCH_V3_LITERAL_CAR_NUMBER_REPAIR_REVIEW_REQUIRED"
        )

    print("=" * 120)

    print()
    print("OUTPUTS")
    print(MATCH_V3)
    print(REPAIR_AUDIT_OUT)
    print(SUMMARY_OUT)
    print(QA_OUT)


if __name__ == "__main__":
    main()
