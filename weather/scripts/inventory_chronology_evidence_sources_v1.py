from pathlib import Path
import csv
import json
import re


# ============================================================
# PHASE
# ============================================================

PHASE = "R1G.1"


# ============================================================
# SEARCH ROOTS
# ============================================================

ROOTS = [
    Path("weather/output"),
    Path("weather/evidence"),
    Path("weather"),
]


# ============================================================
# OUTPUT
# ============================================================

OUTPUT_DIR = Path("weather/output")

INVENTORY_CSV = (
    OUTPUT_DIR
    / "chronology_evidence_source_inventory_v1.csv"
)

FIELD_CSV = (
    OUTPUT_DIR
    / "chronology_evidence_field_inventory_v1.csv"
)

QA_CSV = (
    OUTPUT_DIR
    / "chronology_evidence_source_inventory_v1_qa.csv"
)


# ============================================================
# FILE NAME FILTERS
# ============================================================

NAME_KEYWORDS = [
    "chronology",
    "timing",
    "timestamp",
    "capture",
    "attempt",
    "anchor",
    "replay",
    "session",
    "performance_grade",
    "timing71",
    "event",
]


# ============================================================
# TIME-LIKE FIELD FILTERS
# ============================================================

TIME_FIELD_KEYWORDS = [
    "time",
    "timestamp",
    "datetime",
    "date_time",
    "capture",
    "start",
    "end",
    "issue",
    "valid",
    "local",
    "utc",
    "anchor",
    "bound",
    "interval",
    "session",
    "elapsed",
]


IDENTITY_FIELD_KEYWORDS = [
    "year",
    "car",
    "driver",
    "attempt",
    "session",
    "speed",
    "lap",
    "status",
    "event",
]


# ============================================================
# HELPERS
# ============================================================

def write_csv(path, rows, fields):

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
        writer.writerows(rows)


def is_candidate_name(path):

    lower = path.name.lower()

    return any(
        keyword in lower
        for keyword in NAME_KEYWORDS
    )


def field_is_time_like(field):

    lower = field.lower()

    return any(
        keyword in lower
        for keyword in TIME_FIELD_KEYWORDS
    )


def field_is_identity_like(field):

    lower = field.lower()

    return any(
        keyword in lower
        for keyword in IDENTITY_FIELD_KEYWORDS
    )


def sample_nonempty_values(rows, field, limit=8):

    values = []

    for row in rows:

        value = row.get(field)

        if value is None:
            continue

        text = str(value).strip()

        if not text:
            continue

        if text not in values:
            values.append(text)

        if len(values) >= limit:
            break

    return values


def collect_years(rows):

    year_fields = [
        "year",
        "Year",
        "season_year",
        "qualifying_year",
    ]

    years = set()

    for row in rows:

        for field in year_fields:

            if field not in row:
                continue

            value = str(
                row.get(field, "")
            ).strip()

            if re.fullmatch(
                r"20\d{2}",
                value,
            ):

                years.add(
                    int(value)
                )

    return sorted(years)


def read_csv_file(path):

    try:

        with path.open(
            "r",
            encoding="utf-8-sig",
            errors="replace",
            newline="",
        ) as handle:

            reader = csv.DictReader(
                handle
            )

            rows = list(reader)

            fields = (
                reader.fieldnames
                or []
            )

        return {
            "ok": True,
            "rows": rows,
            "fields": fields,
            "error": "",
        }

    except Exception as exc:

        return {
            "ok": False,
            "rows": [],
            "fields": [],
            "error": (
                f"{type(exc).__name__}: "
                f"{exc}"
            ),
        }


def read_json_file(path):

    try:

        data = json.loads(
            path.read_text(
                encoding="utf-8",
                errors="replace",
            )
        )

        rows = []

        if isinstance(data, list):

            rows = [
                item
                for item in data
                if isinstance(
                    item,
                    dict,
                )
            ]

        elif isinstance(data, dict):

            # Prefer common row containers.
            for key in [
                "records",
                "events",
                "attempts",
                "captures",
                "rows",
                "data",
            ]:

                value = data.get(key)

                if isinstance(
                    value,
                    list,
                ):

                    rows = [
                        item
                        for item in value
                        if isinstance(
                            item,
                            dict,
                        )
                    ]

                    if rows:
                        break

            if not rows:

                rows = [data]

        fields = []

        for row in rows:

            for key in row.keys():

                if key not in fields:
                    fields.append(key)

        return {
            "ok": True,
            "rows": rows,
            "fields": fields,
            "error": "",
        }

    except Exception as exc:

        return {
            "ok": False,
            "rows": [],
            "fields": [],
            "error": (
                f"{type(exc).__name__}: "
                f"{exc}"
            ),
        }


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
        "R1G.1 — CHRONOLOGY EVIDENCE "
        "SOURCE INVENTORY V1"
    )
    print("=" * 120)

    candidate_paths = set()

    # ========================================================
    # DISCOVER
    # ========================================================

    for root in ROOTS:

        if not root.exists():
            continue

        for path in root.rglob("*"):

            if not path.is_file():
                continue

            if path.suffix.lower() not in {
                ".csv",
                ".json",
            }:
                continue

            if is_candidate_name(path):

                candidate_paths.add(
                    path
                )

    candidate_paths = sorted(
        candidate_paths
    )

    print()
    print(
        "CANDIDATE FILE COUNT:",
        len(candidate_paths),
    )

    inventory_rows = []
    field_rows = []

    successful_files = 0
    timestamp_capable_files = 0

    # ========================================================
    # FILE AUDIT
    # ========================================================

    for file_index, path in enumerate(
        candidate_paths,
        start=1,
    ):

        print()
        print("=" * 120)

        print(
            f"FILE {file_index:03d}/"
            f"{len(candidate_paths)}"
        )

        print("=" * 120)

        print(
            "PATH:",
            path,
        )

        if path.suffix.lower() == ".csv":

            result = read_csv_file(
                path
            )

        else:

            result = read_json_file(
                path
            )

        if not result["ok"]:

            print(
                "READ ERROR:",
                result["error"],
            )

            inventory_rows.append({
                "path":
                    str(path),

                "file_type":
                    path.suffix.lower(),

                "read_ok":
                    False,

                "row_count":
                    "",

                "field_count":
                    "",

                "years":
                    "",

                "time_like_fields":
                    "",

                "identity_like_fields":
                    "",

                "has_time_like_field":
                    False,

                "error":
                    result["error"],
            })

            continue

        successful_files += 1

        rows = result["rows"]
        fields = result["fields"]

        years = collect_years(
            rows
        )

        time_fields = [
            field
            for field in fields
            if field_is_time_like(
                field
            )
        ]

        identity_fields = [
            field
            for field in fields
            if field_is_identity_like(
                field
            )
        ]

        if time_fields:
            timestamp_capable_files += 1

        print(
            "ROWS:",
            len(rows),
        )

        print(
            "FIELDS:",
            len(fields),
        )

        print(
            "YEARS:",
            years,
        )

        print()
        print(
            "TIME-LIKE FIELDS:"
        )

        if not time_fields:

            print(
                "  NONE"
            )

        else:

            for field in time_fields:

                samples = sample_nonempty_values(
                    rows,
                    field,
                )

                print(
                    f"  {field}"
                )

                print(
                    "    samples:",
                    samples,
                )

                field_rows.append({
                    "path":
                        str(path),

                    "field_name":
                        field,

                    "field_class":
                        "TIME_LIKE",

                    "nonempty_samples":
                        json.dumps(
                            samples,
                            ensure_ascii=False,
                        ),
                })

        print()
        print(
            "IDENTITY-LIKE FIELDS:"
        )

        if not identity_fields:

            print(
                "  NONE"
            )

        else:

            for field in identity_fields:

                samples = sample_nonempty_values(
                    rows,
                    field,
                )

                print(
                    f"  {field}"
                )

                print(
                    "    samples:",
                    samples,
                )

                field_rows.append({
                    "path":
                        str(path),

                    "field_name":
                        field,

                    "field_class":
                        "IDENTITY_LIKE",

                    "nonempty_samples":
                        json.dumps(
                            samples,
                            ensure_ascii=False,
                        ),
                })

        inventory_rows.append({
            "path":
                str(path),

            "file_type":
                path.suffix.lower(),

            "read_ok":
                True,

            "row_count":
                len(rows),

            "field_count":
                len(fields),

            "years":
                ",".join(
                    str(year)
                    for year in years
                ),

            "time_like_fields":
                json.dumps(
                    time_fields,
                    ensure_ascii=False,
                ),

            "identity_like_fields":
                json.dumps(
                    identity_fields,
                    ensure_ascii=False,
                ),

            "has_time_like_field":
                bool(
                    time_fields
                ),

            "error":
                "",
        })

    # ========================================================
    # WRITE OUTPUTS
    # ========================================================

    write_csv(
        INVENTORY_CSV,
        inventory_rows,
        [
            "path",
            "file_type",
            "read_ok",
            "row_count",
            "field_count",
            "years",
            "time_like_fields",
            "identity_like_fields",
            "has_time_like_field",
            "error",
        ],
    )

    write_csv(
        FIELD_CSV,
        field_rows,
        [
            "path",
            "field_name",
            "field_class",
            "nonempty_samples",
        ],
    )

    # ========================================================
    # HIGH-VALUE CANDIDATES
    # ========================================================

    print()
    print("=" * 120)
    print(
        "HIGH-VALUE CHRONOLOGY CANDIDATES"
    )
    print("=" * 120)

    high_value = []

    for row in inventory_rows:

        if not row[
            "read_ok"
        ]:
            continue

        fields_text = (
            str(
                row[
                    "time_like_fields"
                ]
            ).lower()
        )

        path_lower = (
            row[
                "path"
            ].lower()
        )

        score = 0

        if "timestamp" in fields_text:
            score += 4

        if "capture" in fields_text:
            score += 4

        if "start" in fields_text:
            score += 3

        if "end" in fields_text:
            score += 2

        if "bound" in fields_text:
            score += 3

        if "interval" in fields_text:
            score += 3

        if "timing71" in path_lower:
            score += 4

        if "chronology" in path_lower:
            score += 4

        if "performance_grade_attempt_timing" in path_lower:
            score += 5

        if score > 0:

            high_value.append(
                (
                    score,
                    row,
                )
            )

    high_value.sort(
        key=lambda item: (
            -item[0],
            item[1]["path"],
        )
    )

    if not high_value:

        print(
            "NONE"
        )

    else:

        for score, row in high_value:

            print()
            print(
                f"SCORE={score}"
            )

            print(
                "PATH:",
                row["path"],
            )

            print(
                "ROWS:",
                row["row_count"],
            )

            print(
                "YEARS:",
                row["years"],
            )

            print(
                "TIME FIELDS:",
                row[
                    "time_like_fields"
                ],
            )

            print(
                "IDENTITY FIELDS:",
                row[
                    "identity_like_fields"
                ],
            )

    # ========================================================
    # SPECIFIC KNOWN FILE CHECK
    # ========================================================

    KNOWN_FILES = [
        Path(
            "weather/output/"
            "performance_grade_attempt_timing.csv"
        ),

        Path(
            "weather/output/"
            "performance_grade_attempt_timing_2024_supported.csv"
        ),

        Path(
            "weather/output/"
            "official_day1_results_attempt_rows_v1.csv"
        ),
    ]

    print()
    print("=" * 120)
    print(
        "KNOWN INPUT CHECK"
    )
    print("=" * 120)

    known_present = 0

    for path in KNOWN_FILES:

        exists = path.exists()

        print(
            f"{path}: "
            f"{'PRESENT' if exists else 'MISSING'}"
        )

        if exists:
            known_present += 1

    # ========================================================
    # QA
    # ========================================================

    qa_rows = [
        {
            "metric":
                "candidate_files_discovered",

            "value":
                len(
                    candidate_paths
                ),

            "status":
                "INFO",
        },

        {
            "metric":
                "candidate_files_read_successfully",

            "value":
                successful_files,

            "status":
                (
                    "PASS"
                    if successful_files > 0
                    else "FAIL"
                ),
        },

        {
            "metric":
                "files_with_time_like_fields",

            "value":
                timestamp_capable_files,

            "status":
                (
                    "PASS"
                    if timestamp_capable_files > 0
                    else "REVIEW"
                ),
        },

        {
            "metric":
                "known_inputs_present",

            "value":
                known_present,

            "status":
                (
                    "PASS"
                    if known_present >= 2
                    else "REVIEW"
                ),
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
                "elapsed_time_treated_as_wall_clock",

            "value":
                0,

            "status":
                "PASS",
        },

        {
            "metric":
                "capture_time_treated_as_run_start",

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
        "R1G.1 SUMMARY"
    )
    print("=" * 120)

    print()
    print(
        "Candidate files:",
        len(
            candidate_paths
        ),
    )

    print(
        "Successfully read:",
        successful_files,
    )

    print(
        "Files with time-like fields:",
        timestamp_capable_files,
    )

    print(
        "High-value chronology candidates:",
        len(
            high_value
        ),
    )

    print()
    print(
        "IMPORTANT:"
    )

    print(
        "No elapsed duration was interpreted "
        "as a wall-clock timestamp."
    )

    print(
        "No Timing71 capture time was interpreted "
        "as exact run start."
    )

    print(
        "No chronology was reconstructed."
    )

    print()
    print("=" * 120)

    if (
        successful_files > 0
        and
        timestamp_capable_files > 0
    ):

        print(
            "FINAL STATUS: "
            "CHRONOLOGY_EVIDENCE_SOURCE_INVENTORY_COMPLETE"
        )

    else:

        print(
            "FINAL STATUS: "
            "CHRONOLOGY_EVIDENCE_SOURCE_INVENTORY_REVIEW_REQUIRED"
        )

    print("=" * 120)

    print()
    print(
        "OUTPUTS"
    )

    print(
        INVENTORY_CSV
    )

    print(
        FIELD_CSV
    )

    print(
        QA_CSV
    )


if __name__ == "__main__":
    main()
