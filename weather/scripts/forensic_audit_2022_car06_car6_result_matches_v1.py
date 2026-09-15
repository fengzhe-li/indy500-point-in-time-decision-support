from pathlib import Path
import csv


# ============================================================
# INPUTS
# ============================================================

CANONICAL = Path(
    "data/canonical/v1/attempts.csv"
)

MATCH_V1 = Path(
    "weather/output/"
    "chronology_rescue_2022_result_to_canonical_attempt_matches_v1.csv"
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

FORENSIC_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_car06_car6_result_match_forensics_v1.csv"
)

SUMMARY_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_car06_car6_result_match_forensics_summary_v1.csv"
)

QA_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_car06_car6_result_match_forensics_v1_qa.csv"
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
        return list(csv.DictReader(f))


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
            float(txt(a)) -
            float(txt(b))
        ) <= tol
    except Exception:
        return False


def is_2022(row):
    return (
        txt(row.get("year")) == "2022"
        or
        "2022" in txt(
            row.get("session_id")
        )
    )


def first_value(row, names):
    for name in names:
        value = txt(
            row.get(name)
        )

        if value:
            return value

    return ""


def canonical_speed(row):
    return first_value(
        row,
        [
            "four_lap_average_speed_mph",
            "average_speed_mph",
            "speed_mph",
        ],
    )


def canonical_driver(row):
    return first_value(
        row,
        [
            "driver_name",
            "driver",
            "driver_full_name",
        ],
    )


def match_driver(row):
    return first_value(
        row,
        [
            "driver_name",
            "official_driver_name",
            "driver",
        ],
    )


def official_driver(row):
    return first_value(
        row,
        [
            "driver_name",
            "driver",
            "driver_full_name",
        ],
    )


def official_car(row):
    return first_value(
        row,
        [
            "car_number",
            "car",
        ],
    )


def official_speed(row):
    return first_value(
        row,
        [
            "official_speed_mph",
            "four_lap_average_speed_mph",
            "speed_mph",
            "average_speed_mph",
        ],
    )


def official_status(row):
    return first_value(
        row,
        [
            "official_status",
            "status",
            "result_status",
        ],
    )


def get_official_row_number(row):
    return first_value(
        row,
        [
            "official_result_row",
            "result_row",
            "source_row",
            "row_number",
        ],
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
        "R1G.25F — 2022 #06/#6 RESULT-MATCH "
        "IDENTITY FORENSIC AUDIT V1"
    )
    print("=" * 120)

    inputs = [
        CANONICAL,
        MATCH_V1,
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
            "CAR06_CAR6_RESULT_MATCH_FORENSICS_INPUT_MISSING"
        )

        return

    canonical = read_csv(
        CANONICAL
    )

    match_v1 = read_csv(
        MATCH_V1
    )

    match_v2 = read_csv(
        MATCH_V2
    )

    official = read_csv(
        OFFICIAL_RESULTS
    )

    # ========================================================
    # CANONICAL COLLISION TRUTH
    # ========================================================

    collision_canonical = [
        row
        for row in canonical
        if (
            is_2022(row)
            and
            txt(
                row.get("car_number")
            )
            in {
                "06",
                "6",
            }
        )
    ]

    canonical_by_id = {
        txt(
            row.get("attempt_id")
        ): row
        for row in collision_canonical
        if txt(
            row.get("attempt_id")
        )
    }

    print()
    print("=" * 120)
    print(
        "CANONICAL COLLISION TRUTH"
    )
    print("=" * 120)

    print()
    print(
        "Collision-sensitive canonical rows:",
        len(
            collision_canonical
        ),
    )

    for row in collision_canonical:

        print()
        print(
            "attempt_id:",
            txt(
                row.get("attempt_id")
            ),
        )

        print(
            "  car:",
            repr(
                txt(
                    row.get("car_number")
                )
            ),
        )

        print(
            "  driver:",
            canonical_driver(row),
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
            repr(
                canonical_speed(row)
            ),
        )

    # ========================================================
    # OFFICIAL RAW ROW INDEX
    # ========================================================

    official_by_row = {}

    for row in official:

        year = txt(
            row.get("year")
        )

        if year and year != "2022":
            continue

        row_number = get_official_row_number(
            row
        )

        if row_number:
            official_by_row[
                row_number
            ] = row

    print()
    print(
        "Official 2022 parsed rows indexed:",
        len(
            official_by_row
        ),
    )

    # ========================================================
    # FORENSIC FUNCTION
    # ========================================================

    forensic_rows = []

    def audit_match_file(
        version,
        path,
        rows,
    ):

        print()
        print("=" * 120)
        print(
            f"{version} COLLISION ROW FORENSICS"
        )
        print("=" * 120)

        relevant = []

        for row in rows:

            attempt_id = txt(
                row.get(
                    "attempt_id"
                )
            )

            if attempt_id in canonical_by_id:
                relevant.append(row)

        print()
        print(
            "Rows whose attempt_id belongs to "
            "#06/#6 canonical truth:",
            len(
                relevant
            ),
        )

        for row in relevant:

            attempt_id = txt(
                row.get(
                    "attempt_id"
                )
            )

            truth = canonical_by_id[
                attempt_id
            ]

            match_car = txt(
                row.get(
                    "car_number"
                )
            )

            mdriver = match_driver(
                row
            )

            match_speed = first_value(
                row,
                [
                    "official_speed_mph",
                    "speed_mph",
                    "four_lap_average_speed_mph",
                ],
            )

            match_status = first_value(
                row,
                [
                    "official_status",
                    "status",
                ],
            )

            result_row = get_official_row_number(
                row
            )

            raw = official_by_row.get(
                result_row,
                {},
            )

            raw_car = official_car(
                raw
            )

            raw_driver = official_driver(
                raw
            )

            raw_speed = official_speed(
                raw
            )

            raw_status = official_status(
                raw
            )

            truth_car = txt(
                truth.get(
                    "car_number"
                )
            )

            truth_driver = canonical_driver(
                truth
            )

            truth_speed = canonical_speed(
                truth
            )

            # ====================================================
            # TEST whether row metadata fits its current attempt_id
            # ====================================================

            driver_matches_truth = (
                bool(mdriver)
                and
                mdriver == truth_driver
            )

            speed_matches_truth = (
                bool(match_speed)
                and
                speed_close(
                    match_speed,
                    truth_speed,
                )
            )

            raw_driver_matches_truth = (
                bool(raw_driver)
                and
                raw_driver == truth_driver
            )

            raw_speed_matches_truth = (
                bool(raw_speed)
                and
                speed_close(
                    raw_speed,
                    truth_speed,
                )
            )

            # ====================================================
            # Does the raw official row belong to some OTHER
            # canonical collision-sensitive attempt?
            # ====================================================

            raw_matches_other_attempt_id = ""

            if raw:

                for other_id, other_truth in canonical_by_id.items():

                    if other_id == attempt_id:
                        continue

                    other_driver = canonical_driver(
                        other_truth
                    )

                    other_speed = canonical_speed(
                        other_truth
                    )

                    driver_ok = (
                        raw_driver
                        and
                        raw_driver == other_driver
                    )

                    speed_ok = (
                        raw_speed
                        and
                        speed_close(
                            raw_speed,
                            other_speed,
                        )
                    )

                    if driver_ok and speed_ok:

                        raw_matches_other_attempt_id = (
                            other_id
                        )

                        break

            # ====================================================
            # CLASSIFICATION
            # ====================================================

            if (
                raw_driver_matches_truth
                and
                raw_speed_matches_truth
            ):

                if (
                    match_car == truth_car
                    and
                    driver_matches_truth
                    and
                    speed_matches_truth
                ):

                    classification = (
                        "FULLY_CORRECT"
                    )

                else:

                    classification = (
                        "ATTEMPT_ID_CORRECT_METADATA_WRONG"
                    )

            elif raw_matches_other_attempt_id:

                classification = (
                    "ATTEMPT_ID_WRONG"
                )

            elif (
                driver_matches_truth
                and
                speed_matches_truth
            ):

                classification = (
                    "ATTEMPT_ID_LIKELY_CORRECT_RAW_ROW_LINK_UNCLEAR"
                )

            else:

                classification = (
                    "AMBIGUOUS"
                )

            forensic_rows.append({
                "match_version":
                    version,

                "match_file":
                    str(path),

                "attempt_id":
                    attempt_id,

                "canonical_car_number":
                    truth_car,

                "canonical_driver":
                    truth_driver,

                "canonical_speed_mph":
                    truth_speed,

                "match_car_number":
                    match_car,

                "match_driver":
                    mdriver,

                "match_speed_mph":
                    match_speed,

                "match_status":
                    match_status,

                "official_result_row":
                    result_row,

                "raw_official_car_number":
                    raw_car,

                "raw_official_driver":
                    raw_driver,

                "raw_official_speed_mph":
                    raw_speed,

                "raw_official_status":
                    raw_status,

                "driver_matches_canonical":
                    driver_matches_truth,

                "speed_matches_canonical":
                    speed_matches_truth,

                "raw_driver_matches_canonical":
                    raw_driver_matches_truth,

                "raw_speed_matches_canonical":
                    raw_speed_matches_truth,

                "raw_matches_other_attempt_id":
                    raw_matches_other_attempt_id,

                "classification":
                    classification,
            })

            print()
            print(
                "attempt_id:",
                attempt_id,
            )

            print(
                "  CANONICAL:",
                repr(
                    truth_car
                ),
                "|",
                truth_driver,
                "|",
                truth_speed,
            )

            print(
                "  MATCH ROW:",
                repr(
                    match_car
                ),
                "|",
                mdriver,
                "|",
                match_speed,
                "| status=",
                repr(
                    match_status
                ),
            )

            print(
                "  OFFICIAL RAW ROW:",
                repr(
                    raw_car
                ),
                "|",
                raw_driver,
                "|",
                raw_speed,
                "| status=",
                repr(
                    raw_status
                ),
            )

            print(
                "  official result row:",
                repr(
                    result_row
                ),
            )

            print(
                "  raw matches other attempt_id:",
                (
                    raw_matches_other_attempt_id
                    or
                    "NONE"
                ),
            )

            print(
                "  CLASSIFICATION:",
                classification,
            )

    # ========================================================
    # RUN BOTH
    # ========================================================

    audit_match_file(
        "V1",
        MATCH_V1,
        match_v1,
    )

    audit_match_file(
        "V2",
        MATCH_V2,
        match_v2,
    )

    # ========================================================
    # SUMMARY COUNTS
    # ========================================================

    summary_counts = {}

    for row in forensic_rows:

        key = (
            row[
                "classification"
            ]
        )

        summary_counts[
            key
        ] = (
            summary_counts.get(
                key,
                0,
            )
            + 1
        )

    print()
    print("=" * 120)
    print(
        "FORENSIC CLASSIFICATION SUMMARY"
    )
    print("=" * 120)

    print()

    for key in sorted(
        summary_counts
    ):

        print(
            f"{key}: "
            f"{summary_counts[key]}"
        )

    # ========================================================
    # V2 REBUILD DECISION
    # ========================================================

    v2_rows = [
        row
        for row in forensic_rows
        if row[
            "match_version"
        ] == "V2"
    ]

    v2_wrong_ids = [
        row
        for row in v2_rows
        if row[
            "classification"
        ] == "ATTEMPT_ID_WRONG"
    ]

    v2_metadata_only = [
        row
        for row in v2_rows
        if row[
            "classification"
        ] == "ATTEMPT_ID_CORRECT_METADATA_WRONG"
    ]

    v2_ambiguous = [
        row
        for row in v2_rows
        if row[
            "classification"
        ]
        in {
            "AMBIGUOUS",
            "ATTEMPT_ID_LIKELY_CORRECT_RAW_ROW_LINK_UNCLEAR",
        }
    ]

    print()
    print("=" * 120)
    print(
        "V2 REMEDIATION DECISION"
    )
    print("=" * 120)

    print()
    print(
        "V2 attempt-ID-wrong rows:",
        len(
            v2_wrong_ids
        ),
    )

    print(
        "V2 metadata-only wrong rows:",
        len(
            v2_metadata_only
        ),
    )

    print(
        "V2 ambiguous rows:",
        len(
            v2_ambiguous
        ),
    )

    if v2_wrong_ids:

        remediation = (
            "REBUILD_V2_COLLISION_ROWS_FROM_OFFICIAL_RAW_AND_CANONICAL"
        )

    elif v2_metadata_only and not v2_ambiguous:

        remediation = (
            "PATCH_V2_METADATA_BY_ATTEMPT_ID_AND_VERIFY_HASHED_DESCENDANTS"
        )

    elif v2_ambiguous:

        remediation = (
            "MANUAL_OR_TARGETED_RECONCILIATION_REQUIRED"
        )

    else:

        remediation = (
            "NO_V2_COLLISION_REMEDIATION_REQUIRED"
        )

    print()
    print(
        "Recommended remediation:",
        remediation,
    )

    # ========================================================
    # WRITE
    # ========================================================

    write_csv(
        FORENSIC_OUT,
        forensic_rows,
        [
            "match_version",
            "match_file",
            "attempt_id",
            "canonical_car_number",
            "canonical_driver",
            "canonical_speed_mph",
            "match_car_number",
            "match_driver",
            "match_speed_mph",
            "match_status",
            "official_result_row",
            "raw_official_car_number",
            "raw_official_driver",
            "raw_official_speed_mph",
            "raw_official_status",
            "driver_matches_canonical",
            "speed_matches_canonical",
            "raw_driver_matches_canonical",
            "raw_speed_matches_canonical",
            "raw_matches_other_attempt_id",
            "classification",
        ],
    )

    summary_rows = [
        {
            "metric":
                "forensic_rows",

            "value":
                len(
                    forensic_rows
                ),
        },

        {
            "metric":
                "v2_attempt_id_wrong_rows",

            "value":
                len(
                    v2_wrong_ids
                ),
        },

        {
            "metric":
                "v2_metadata_only_wrong_rows",

            "value":
                len(
                    v2_metadata_only
                ),
        },

        {
            "metric":
                "v2_ambiguous_rows",

            "value":
                len(
                    v2_ambiguous
                ),
        },

        {
            "metric":
                "recommended_remediation",

            "value":
                remediation,
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
                "canonical_collision_rows",

            "value":
                len(
                    collision_canonical
                ),

            "status":
                (
                    "PASS"
                    if len(
                        collision_canonical
                    ) == 3
                    else "REVIEW"
                ),
        },

        {
            "metric":
                "v1_v2_forensic_rows",

            "value":
                len(
                    forensic_rows
                ),

            "status":
                (
                    "PASS"
                    if len(
                        forensic_rows
                    ) == 6
                    else "REVIEW"
                ),
        },

        {
            "metric":
                "numeric_car_number_used_as_identity",

            "value":
                0,

            "status":
                "PASS",
        },

        {
            "metric":
                "attempt_id_used_as_grounding_key",

            "value":
                1,

            "status":
                "PASS",
        },

        {
            "metric":
                "existing_result_match_files_mutated",

            "value":
                0,

            "status":
                "PASS",
        },

        {
            "metric":
                "canonical_data_mutated",

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
        "FINAL SUMMARY"
    )
    print("=" * 120)

    print()
    print(
        "Forensic rows:",
        len(
            forensic_rows
        ),
    )

    print(
        "V2 wrong attempt IDs:",
        len(
            v2_wrong_ids
        ),
    )

    print(
        "V2 metadata-only errors:",
        len(
            v2_metadata_only
        ),
    )

    print(
        "V2 ambiguous:",
        len(
            v2_ambiguous
        ),
    )

    print()
    print(
        "Recommended remediation:",
        remediation,
    )

    print()
    print(
        "No existing result-match file was modified."
    )

    print(
        "No canonical data was modified."
    )

    print()
    print("=" * 120)

    if (
        len(
            forensic_rows
        ) >= 1
        and
        not v2_ambiguous
    ):

        print(
            "FINAL STATUS: "
            "CAR06_CAR6_RESULT_MATCH_FORENSICS_COMPLETE"
        )

    else:

        print(
            "FINAL STATUS: "
            "CAR06_CAR6_RESULT_MATCH_FORENSICS_REVIEW_REQUIRED"
        )

    print("=" * 120)

    print()
    print("OUTPUTS")
    print(FORENSIC_OUT)
    print(SUMMARY_OUT)
    print(QA_OUT)


if __name__ == "__main__":
    main()
