from pathlib import Path

import csv
import json
from collections import Counter, defaultdict


# ============================================================
# PHASE
# ============================================================

PHASE = "R1F.1"


# ============================================================
# INPUT
# ============================================================

RAW_JSON_DIR = Path(
    "weather/evidence/rescue/"
    "official_day1_session_details/raw_api"
)

TARGETS = {
    2020: "5771",
    2021: "5838",
    2022: "6033",
    2023: "6202",
    2024: "6382",
}


# ============================================================
# OUTPUT
# ============================================================

OUTPUT_DIR = Path(
    "weather/output"
)

FIELD_INVENTORY_CSV = (
    OUTPUT_DIR
    / "official_day1_api_record_field_inventory_v1.csv"
)

RECORD_INVENTORY_CSV = (
    OUTPUT_DIR
    / "official_day1_api_record_inventory_v1.csv"
)

VALUE_INVENTORY_CSV = (
    OUTPUT_DIR
    / "official_day1_api_record_categorical_values_v1.csv"
)

QA_CSV = (
    OUTPUT_DIR
    / "official_day1_api_record_schema_audit_v1_qa.csv"
)


# ============================================================
# HELPERS
# ============================================================

def safe_text(value):

    if value is None:
        return ""

    if isinstance(
        value,
        (
            dict,
            list,
        ),
    ):

        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
        )

    return str(
        value
    )


def type_name(value):

    if value is None:
        return "null"

    if isinstance(
        value,
        bool,
    ):
        return "bool"

    if isinstance(
        value,
        int,
    ):
        return "int"

    if isinstance(
        value,
        float,
    ):
        return "float"

    if isinstance(
        value,
        list,
    ):
        return "list"

    if isinstance(
        value,
        dict,
    ):
        return "dict"

    return type(
        value
    ).__name__


def write_csv(
    path,
    rows,
    fields,
):

    with path.open(
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as handle:

        writer = csv.DictWriter(
            handle,
            fieldnames=fields,
        )

        writer.writeheader()

        writer.writerows(
            rows
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
        "R1F.1 — OFFICIAL DAY 1 "
        "EVENTSSESSIONDETAILS RECORD SCHEMA AUDIT V1"
    )
    print("=" * 120)

    field_rows = []
    record_rows = []
    categorical_rows = []

    successful_years = []
    total_records = 0

    # Used to collect distinct values.
    field_value_counts = defaultdict(
        Counter
    )

    for year, session_id in (
        TARGETS.items()
    ):

        path = (
            RAW_JSON_DIR
            /
            f"{year}_{session_id}_session_details.json"
        )

        print()
        print("=" * 120)
        print(
            f"YEAR {year}"
        )
        print("=" * 120)

        print(
            "SOURCE:",
            path,
        )

        if not path.exists():

            print(
                "SOURCE JSON MISSING"
            )

            continue

        detail = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

        records = detail.get(
            "records"
        )

        if not isinstance(
            records,
            list,
        ):

            print(
                "records IS NOT A LIST"
            )

            continue

        successful_years.append(
            year
        )

        total_records += len(
            records
        )

        print(
            "RECORD COUNT:",
            len(
                records
            ),
        )

        # ====================================================
        # UNION OF KEYS
        # ====================================================

        union_keys = []

        for record in records:

            if not isinstance(
                record,
                dict,
            ):
                continue

            for key in record.keys():

                if key not in union_keys:

                    union_keys.append(
                        key
                    )

        print()
        print(
            "UNION OF RECORD KEYS:"
        )

        for key in union_keys:

            print(
                "  -",
                key,
            )

        print()
        print(
            "FIELD TYPE / COVERAGE INVENTORY"
        )
        print("-" * 120)

        for key in union_keys:

            values = []

            for record in records:

                if not isinstance(
                    record,
                    dict,
                ):
                    continue

                if key in record:

                    values.append(
                        record[
                            key
                        ]
                    )

            nonnull = [
                value
                for value in values
                if value is not None
            ]

            nonempty = [
                value
                for value in nonnull
                if safe_text(
                    value
                ).strip()
                != ""
            ]

            types = sorted(
                {
                    type_name(
                        value
                    )
                    for value in values
                }
            )

            unique_preview_values = []

            for value in nonempty:

                rendered = safe_text(
                    value
                )

                if (
                    rendered
                    not in
                    unique_preview_values
                ):

                    unique_preview_values.append(
                        rendered
                    )

                if len(
                    unique_preview_values
                ) >= 12:

                    break

            print(
                f"{key:<35} "
                f"present={len(values):<4} "
                f"nonnull={len(nonnull):<4} "
                f"nonempty={len(nonempty):<4} "
                f"types={types}"
            )

            print(
                "    preview:",
                unique_preview_values,
            )

            field_rows.append(
                {
                    "year":
                        year,

                    "session_id":
                        session_id,

                    "field_name":
                        key,

                    "record_count":
                        len(
                            records
                        ),

                    "present_count":
                        len(
                            values
                        ),

                    "nonnull_count":
                        len(
                            nonnull
                        ),

                    "nonempty_count":
                        len(
                            nonempty
                        ),

                    "types":
                        json.dumps(
                            types,
                            ensure_ascii=False,
                        ),

                    "preview_values":
                        json.dumps(
                            unique_preview_values,
                            ensure_ascii=False,
                        ),
                }
            )

        # ====================================================
        # COMPLETE RECORD DUMP
        # ====================================================

        print()
        print(
            "COMPLETE RECORD INVENTORY"
        )
        print("-" * 120)

        for index, record in enumerate(
            records,
            start=1,
        ):

            if not isinstance(
                record,
                dict,
            ):

                print(
                    f"RECORD {index}: "
                    f"NON-DICT {repr(record)}"
                )

                continue

            print()
            print(
                f"RECORD {index:03d}"
            )

            for key in union_keys:

                if key not in record:
                    continue

                value = record[
                    key
                ]

                print(
                    f"  {key}: "
                    f"{value!r}"
                )

                rendered = safe_text(
                    value
                ).strip()

                # Small scalar values can be useful for
                # categorical inventory.
                if (
                    rendered
                    and
                    not isinstance(
                        value,
                        (
                            dict,
                            list,
                        ),
                    )
                    and
                    len(
                        rendered
                    ) <= 120
                ):

                    field_value_counts[
                        (
                            year,
                            key,
                        )
                    ][
                        rendered
                    ] += 1

            flat_row = {
                "year":
                    year,

                "session_id":
                    session_id,

                "record_index":
                    index,

                "raw_json":
                    json.dumps(
                        record,
                        ensure_ascii=False,
                        sort_keys=True,
                    ),
            }

            for key in union_keys:

                flat_row[
                    f"field__{key}"
                ] = safe_text(
                    record.get(
                        key
                    )
                )

            record_rows.append(
                flat_row
            )

    # ========================================================
    # CATEGORICAL VALUE INVENTORY
    # ========================================================

    print()
    print("=" * 120)
    print(
        "CATEGORICAL / LOW-CARDINALITY VALUE INVENTORY"
    )
    print("=" * 120)

    for (
        year,
        key,
    ), counter in sorted(
        field_value_counts.items()
    ):

        # Only print fields with manageable distinct counts.
        if len(
            counter
        ) > 40:
            continue

        print()
        print(
            f"{year} | {key}"
        )

        for value, count in (
            counter.most_common()
        ):

            print(
                f"  {value!r}: "
                f"{count}"
            )

            categorical_rows.append(
                {
                    "year":
                        year,

                    "field_name":
                        key,

                    "value":
                        value,

                    "count":
                        count,
                }
            )

    # ========================================================
    # WRITE FIELD INVENTORY
    # ========================================================

    write_csv(
        FIELD_INVENTORY_CSV,
        field_rows,
        [
            "year",
            "session_id",
            "field_name",
            "record_count",
            "present_count",
            "nonnull_count",
            "nonempty_count",
            "types",
            "preview_values",
        ],
    )

    # ========================================================
    # WRITE RECORD INVENTORY
    #
    # Because schemas may differ by year, use raw_json as
    # canonical audit representation plus all discovered
    # dynamic columns.
    # ========================================================

    all_record_fields = []

    for row in record_rows:

        for key in row.keys():

            if (
                key
                not in
                all_record_fields
            ):

                all_record_fields.append(
                    key
                )

    write_csv(
        RECORD_INVENTORY_CSV,
        record_rows,
        all_record_fields,
    )

    write_csv(
        VALUE_INVENTORY_CSV,
        categorical_rows,
        [
            "year",
            "field_name",
            "value",
            "count",
        ],
    )

    # ========================================================
    # HIGH-VALUE FIELD SEARCH
    # ========================================================

    HIGH_VALUE_PATTERNS = [
        "time",
        "date",
        "order",
        "sequence",
        "position",
        "rank",
        "status",
        "attempt",
        "lane",
        "queue",
        "withdraw",
        "waved",
        "bump",
        "qual",
        "lap",
        "speed",
        "car",
        "driver",
        "result",
        "session",
    ]

    high_value_fields = []

    for row in field_rows:

        lower = row[
            "field_name"
        ].lower()

        if any(
            pattern
            in lower
            for pattern
            in HIGH_VALUE_PATTERNS
        ):

            key = (
                row[
                    "year"
                ],
                row[
                    "field_name"
                ],
            )

            if key not in (
                high_value_fields
            ):

                high_value_fields.append(
                    key
                )

    print()
    print("=" * 120)
    print(
        "HIGH-VALUE FIELD NAMES"
    )
    print("=" * 120)

    if not high_value_fields:

        print(
            "NONE"
        )

    else:

        for year, key in (
            high_value_fields
        ):

            print(
                f"{year} | {key}"
            )

    # ========================================================
    # QA
    # ========================================================

    qa_rows = [
        {
            "metric":
                "target_years_expected",

            "value":
                5,

            "status":
                "INFO",
        },

        {
            "metric":
                "successful_years",

            "value":
                ",".join(
                    str(
                        year
                    )
                    for year
                    in successful_years
                ),

            "status":
                (
                    "PASS"
                    if len(
                        successful_years
                    )
                    == 5
                    else "REVIEW"
                ),
        },

        {
            "metric":
                "total_api_records",

            "value":
                total_records,

            "status":
                "INFO",
        },

        {
            "metric":
                "field_inventory_rows",

            "value":
                len(
                    field_rows
                ),

            "status":
                "INFO",
        },

        {
            "metric":
                "canonical_data_mutated",

            "value":
                0,

            "status":
                "PASS",
        },

        {
            "metric":
                "chronology_inferred",

            "value":
                0,

            "status":
                "PASS",
        },

        {
            "metric":
                "queue_state_inferred",

            "value":
                0,

            "status":
                "PASS",
        },

        {
            "metric":
                "lane_state_inferred",

            "value":
                0,

            "status":
                "PASS",
        },
    ]

    write_csv(
        QA_CSV,
        qa_rows,
        [
            "metric",
            "value",
            "status",
        ],
    )

    # ========================================================
    # FINAL SUMMARY
    # ========================================================

    print()
    print("=" * 120)
    print(
        "R1F.1 SUMMARY"
    )
    print("=" * 120)

    print()
    print(
        "Successful years:",
        successful_years,
    )

    print(
        "Total API records:",
        total_records,
    )

    print(
        "Field inventory rows:",
        len(
            field_rows
        ),
    )

    print()
    print(
        "QA"
    )
    print("-" * 120)

    for row in qa_rows:

        print(
            f"{row['metric']}: "
            f"{row['value']} "
            f"[{row['status']}]"
        )

    print()
    print("=" * 120)

    if len(
        successful_years
    ) == 5:

        print(
            "FINAL STATUS: "
            "OFFICIAL_DAY1_API_RECORD_SCHEMA_AUDIT_COMPLETE"
        )

    else:

        print(
            "FINAL STATUS: "
            "OFFICIAL_DAY1_API_RECORD_SCHEMA_REVIEW_REQUIRED"
        )

    print("=" * 120)

    print()
    print(
        "NO CANONICAL DATA WAS MODIFIED."
    )

    print(
        "NO CHRONOLOGY WAS INFERRED."
    )

    print(
        "NO QUEUE OR LANE STATE WAS INFERRED."
    )

    print()
    print(
        "OUTPUTS"
    )

    print(
        FIELD_INVENTORY_CSV
    )

    print(
        RECORD_INVENTORY_CSV
    )

    print(
        VALUE_INVENTORY_CSV
    )

    print(
        QA_CSV
    )


if __name__ == "__main__":
    main()
