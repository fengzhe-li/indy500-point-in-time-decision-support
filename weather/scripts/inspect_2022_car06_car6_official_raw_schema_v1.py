from pathlib import Path
import csv


OFFICIAL_RESULTS = Path(
    "weather/output/"
    "official_day1_results_attempt_rows_v1.csv"
)

CANONICAL = Path(
    "data/canonical/v1/attempts.csv"
)

MATCH_V2 = Path(
    "weather/output/"
    "chronology_rescue_2022_result_to_canonical_attempt_matches_v2.csv"
)

OUTPUT_DIR = Path(
    "weather/output"
)

AUDIT_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_car06_car6_official_raw_schema_audit_v1.csv"
)

QA_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_car06_car6_official_raw_schema_audit_v1_qa.csv"
)


TARGET_ROWS = {
    "27",
    "30",
    "40",
}

TARGET_ATTEMPTS = {
    "90eea27e-6e83-5e24-8428-811eae3ff157",
    "bb599e9f-cbdc-5c79-9791-ce325ef01086",
    "01896a4f-c482-5093-a806-89bc4273641d",
}


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


def first_nonempty(row, names):
    for name in names:
        value = txt(
            row.get(name)
        )

        if value:
            return value

    return ""


def get_year(row):
    value = txt(
        row.get("year")
    )

    if value:
        return value

    for field in [
        "session_id",
        "event_id",
        "source_file",
    ]:
        value = txt(
            row.get(field)
        )

        if "2022" in value:
            return "2022"

    return ""


def get_result_row_number(row):
    for field in [
        "official_result_row",
        "result_row",
        "row_number",
        "source_row",
        "result_index",
        "record_index",
    ]:

        value = txt(
            row.get(field)
        )

        if value:
            return value

    return ""


def canonical_speed(row):
    return first_nonempty(
        row,
        [
            "four_lap_average_speed_mph",
            "average_speed_mph",
            "speed_mph",
        ],
    )


def main():

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print()
    print("=" * 120)
    print(
        "R1G.25G — 2022 #06/#6 OFFICIAL RESULTS "
        "RAW SCHEMA + TARGET ROW INSPECTION V1"
    )
    print("=" * 120)

    inputs = [
        OFFICIAL_RESULTS,
        CANONICAL,
        MATCH_V2,
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
            "OFFICIAL_RAW_SCHEMA_INSPECTION_INPUT_MISSING"
        )

        return

    official, official_fields = read_csv(
        OFFICIAL_RESULTS
    )

    canonical, canonical_fields = read_csv(
        CANONICAL
    )

    matches, match_fields = read_csv(
        MATCH_V2
    )

    # ========================================================
    # SCHEMA
    # ========================================================

    print()
    print("=" * 120)
    print(
        "OFFICIAL RESULTS CSV SCHEMA"
    )
    print("=" * 120)

    print()
    print(
        "Column count:",
        len(
            official_fields
        ),
    )

    for i, field in enumerate(
        official_fields,
        start=1,
    ):

        print(
            f"{i:02d}. {field}"
        )

    # ========================================================
    # FIND 2022 TARGET RAW ROWS
    # ========================================================

    target_raw_rows = []

    for row in official:

        if get_year(row) != "2022":
            continue

        row_number = get_result_row_number(
            row
        )

        if row_number in TARGET_ROWS:

            target_raw_rows.append(
                (
                    row_number,
                    row,
                )
            )

    print()
    print("=" * 120)
    print(
        "OFFICIAL RAW TARGET ROWS"
    )
    print("=" * 120)

    print()
    print(
        "Target rows found:",
        len(
            target_raw_rows
        ),
    )

    audit_rows = []

    for row_number, row in sorted(
        target_raw_rows,
        key=lambda item: int(
            item[0]
        ),
    ):

        print()
        print("-" * 120)
        print(
            "OFFICIAL RESULT ROW:",
            row_number,
        )
        print("-" * 120)

        nonempty = []

        for field in official_fields:

            value = txt(
                row.get(field)
            )

            if value:

                nonempty.append(
                    (
                        field,
                        value,
                    )
                )

                print(
                    f"{field}: {value}"
                )

        for field, value in nonempty:

            audit_rows.append({
                "record_type":
                    "OFFICIAL_RAW_FIELD",

                "official_result_row":
                    row_number,

                "attempt_id":
                    "",

                "field_name":
                    field,

                "field_value":
                    value,

                "notes":
                    "Raw parsed official Results field.",
            })

    # ========================================================
    # CANONICAL TARGETS
    # ========================================================

    print()
    print("=" * 120)
    print(
        "CANONICAL TARGET ATTEMPTS"
    )
    print("=" * 120)

    canonical_targets = [
        row
        for row in canonical
        if txt(
            row.get(
                "attempt_id"
            )
        ) in TARGET_ATTEMPTS
    ]

    print()
    print(
        "Canonical target rows:",
        len(
            canonical_targets
        ),
    )

    for row in canonical_targets:

        aid = txt(
            row.get(
                "attempt_id"
            )
        )

        print()
        print(
            "attempt_id:",
            aid,
        )

        print(
            "  car_number:",
            repr(
                txt(
                    row.get(
                        "car_number"
                    )
                )
            ),
        )

        print(
            "  driver_name:",
            txt(
                row.get(
                    "driver_name"
                )
            ),
        )

        print(
            "  attempt_index:",
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
                canonical_speed(
                    row
                )
            ),
        )

        audit_rows.append({
            "record_type":
                "CANONICAL_TARGET",

            "official_result_row":
                "",

            "attempt_id":
                aid,

            "field_name":
                "canonical_identity",

            "field_value":
                " | ".join([
                    txt(
                        row.get(
                            "car_number"
                        )
                    ),
                    txt(
                        row.get(
                            "driver_name"
                        )
                    ),
                    canonical_speed(
                        row
                    ),
                ]),

            "notes":
                "Canonical identity reference.",
        })

    # ========================================================
    # V2 TARGET MATCH ROWS
    # ========================================================

    print()
    print("=" * 120)
    print(
        "RESULT-MATCH V2 TARGET ROWS"
    )
    print("=" * 120)

    match_targets = [
        row
        for row in matches
        if txt(
            row.get(
                "attempt_id"
            )
        ) in TARGET_ATTEMPTS
    ]

    print()
    print(
        "V2 target rows:",
        len(
            match_targets
        ),
    )

    for row in match_targets:

        aid = txt(
            row.get(
                "attempt_id"
            )
        )

        print()
        print("-" * 120)
        print(
            "attempt_id:",
            aid,
        )
        print("-" * 120)

        for field in match_fields:

            value = txt(
                row.get(field)
            )

            if value:

                print(
                    f"{field}: {value}"
                )

                audit_rows.append({
                    "record_type":
                        "MATCH_V2_FIELD",

                    "official_result_row":
                        get_result_row_number(
                            row
                        ),

                    "attempt_id":
                        aid,

                    "field_name":
                        field,

                    "field_value":
                        value,

                    "notes":
                        "Current contaminated V2 match row.",
                })

    # ========================================================
    # FIELD-DISCOVERY HINTS
    # ========================================================

    print()
    print("=" * 120)
    print(
        "LIKELY IDENTITY / SPEED FIELDS"
    )
    print("=" * 120)

    candidate_fields = []

    keywords = [
        "driver",
        "name",
        "car",
        "number",
        "speed",
        "mph",
        "average",
        "status",
        "result",
        "row",
        "position",
    ]

    for field in official_fields:

        lower = field.lower()

        if any(
            keyword in lower
            for keyword in keywords
        ):

            candidate_fields.append(
                field
            )

    print()

    for field in candidate_fields:

        print(field)

    # ========================================================
    # QA / WRITE
    # ========================================================

    write_csv(
        AUDIT_OUT,
        audit_rows,
        [
            "record_type",
            "official_result_row",
            "attempt_id",
            "field_name",
            "field_value",
            "notes",
        ],
    )

    qa_rows = [
        {
            "metric":
                "official_schema_columns",

            "value":
                len(
                    official_fields
                ),

            "status":
                "PASS"
                if official_fields
                else "FAIL",
        },

        {
            "metric":
                "target_official_rows_found",

            "value":
                len(
                    target_raw_rows
                ),

            "status":
                "PASS"
                if len(
                    target_raw_rows
                ) == 3
                else "REVIEW",
        },

        {
            "metric":
                "canonical_targets_found",

            "value":
                len(
                    canonical_targets
                ),

            "status":
                "PASS"
                if len(
                    canonical_targets
                ) == 3
                else "FAIL",
        },

        {
            "metric":
                "v2_targets_found",

            "value":
                len(
                    match_targets
                ),

            "status":
                "PASS"
                if len(
                    match_targets
                ) == 3
                else "FAIL",
        },

        {
            "metric":
                "existing_match_v2_mutated",

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
    print(
        "FINAL SUMMARY"
    )
    print("=" * 120)

    print()
    print(
        "Official schema columns:",
        len(
            official_fields
        ),
    )

    print(
        "Official target rows found:",
        len(
            target_raw_rows
        ),
    )

    print(
        "Canonical targets found:",
        len(
            canonical_targets
        ),
    )

    print(
        "V2 target rows found:",
        len(
            match_targets
        ),
    )

    print()
    print(
        "No result-match file was modified."
    )

    print(
        "No canonical data was modified."
    )

    print()
    print("=" * 120)

    if (
        len(
            target_raw_rows
        ) == 3
        and
        len(
            canonical_targets
        ) == 3
        and
        len(
            match_targets
        ) == 3
    ):

        print(
            "FINAL STATUS: "
            "OFFICIAL_RAW_SCHEMA_TARGET_INSPECTION_COMPLETE"
        )

    else:

        print(
            "FINAL STATUS: "
            "OFFICIAL_RAW_SCHEMA_TARGET_INSPECTION_REVIEW_REQUIRED"
        )

    print("=" * 120)

    print()
    print("OUTPUTS")
    print(AUDIT_OUT)
    print(QA_OUT)


if __name__ == "__main__":
    main()
