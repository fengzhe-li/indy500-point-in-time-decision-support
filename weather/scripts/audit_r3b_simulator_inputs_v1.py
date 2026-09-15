from pathlib import Path
import csv
import json
import re


PHASE = "R3B.0"

OUTPUT_ROOT = Path("weather/output")

STATE_V3 = OUTPUT_ROOT / "decision_time_observable_state_v3.csv"

KNOWN_INPUTS = [
    OUTPUT_ROOT / "hrrr_ims_2020_2024_features.csv",
    OUTPUT_ROOT / "decision_time_observable_state_v3.csv",
    OUTPUT_ROOT / "decision_time_observable_state_v3_summary.json",
    OUTPUT_ROOT / "rescue_readiness_summary_v1.json",
    OUTPUT_ROOT / "queue_wait_identifiability_2022_v1.csv",
]

AUDIT_OUT = (
    OUTPUT_ROOT
    / "r3b_simulator_input_inventory_v1.csv"
)

QA_OUT = (
    OUTPUT_ROOT
    / "r3b_simulator_input_inventory_v1_qa.csv"
)


KEYWORDS = [
    "model",
    "performance",
    "repeat",
    "delta",
    "context",
    "hrrr",
    "weather",
    "ptsc",
    "track",
    "temperature",
    "phase5",
    "phase6",
    "recovery",
    "beta",
]


INTEREST_COLUMNS = [
    "year",
    "driver_name",
    "driver",
    "attempt_id",
    "subject_attempt_id",
    "related_attempt_id",
    "speed_mph",
    "four_lap_speed_mph",
    "mean_speed_mph",
    "delta_mph",
    "repeat_delta_mph",
    "predicted",
    "prediction",
    "prediction_mean",
    "prediction_std",
    "residual",
    "mae",
    "model",
    "model_name",
    "air_temp",
    "track_temp",
    "track_temperature",
    "TMP",
    "DPT",
    "wind",
    "gust",
    "PRES",
    "DSWRF",
    "valid_time",
    "forecast_valid_time",
    "availability_time",
    "cycle_time",
]


def txt(v):
    return "" if v is None else str(v).strip()


def read_csv_meta(path):
    try:
        with path.open(
            "r",
            encoding="utf-8-sig",
            newline="",
        ) as f:
            reader = csv.DictReader(f)
            fields = reader.fieldnames or []
            rows = list(reader)

        return {
            "readable": True,
            "row_count": len(rows),
            "fields": fields,
            "sample": rows[:2],
        }

    except Exception as e:
        return {
            "readable": False,
            "row_count": 0,
            "fields": [],
            "sample": [],
            "error": str(e),
        }


def read_json_meta(path):
    try:
        obj = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

        if isinstance(obj, dict):
            fields = list(obj.keys())
            row_count = 1
        elif isinstance(obj, list):
            row_count = len(obj)
            if obj and isinstance(obj[0], dict):
                fields = list(obj[0].keys())
            else:
                fields = []
        else:
            row_count = 1
            fields = []

        return {
            "readable": True,
            "row_count": row_count,
            "fields": fields,
            "sample": [],
        }

    except Exception as e:
        return {
            "readable": False,
            "row_count": 0,
            "fields": [],
            "sample": [],
            "error": str(e),
        }


def relevant_file(path):
    name = path.name.lower()

    if path.suffix.lower() not in {
        ".csv",
        ".json",
    }:
        return False

    return any(
        keyword in name
        for keyword in KEYWORDS
    )


def matching_columns(fields):
    field_lower = {
        f.lower(): f
        for f in fields
    }

    matched = []

    for candidate in INTEREST_COLUMNS:
        if candidate.lower() in field_lower:
            matched.append(
                field_lower[
                    candidate.lower()
                ]
            )

    return matched


def sample_text(sample, fields):
    if not sample:
        return ""

    parts = []

    for row in sample[:2]:
        row_parts = []

        for field in fields[:12]:
            value = txt(
                row.get(field)
            )

            if value:
                row_parts.append(
                    f"{field}={value[:80]}"
                )

        if row_parts:
            parts.append(
                "; ".join(row_parts)
            )

    return " || ".join(parts)


def main():

    print()
    print("=" * 126)
    print(
        "R3B.0 — LIMITED SEQUENTIAL SIMULATOR "
        "INPUT INVENTORY / SCHEMA AUDIT"
    )
    print("=" * 126)

    print()
    print("KNOWN INPUT CHECK")
    print("-" * 126)

    for path in KNOWN_INPUTS:
        print(
            f"{path}: "
            f"{'PRESENT' if path.exists() else 'MISSING'}"
        )

    if not STATE_V3.exists():
        print()
        print(
            "FINAL STATUS: "
            "R3B0_STATE_V3_MISSING"
        )
        return

    candidates = []

    for path in sorted(
        OUTPUT_ROOT.glob("*")
    ):

        if not path.is_file():
            continue

        if not relevant_file(path):
            continue

        if path == AUDIT_OUT or path == QA_OUT:
            continue

        if path.suffix.lower() == ".csv":
            meta = read_csv_meta(path)
        else:
            meta = read_json_meta(path)

        fields = meta[
            "fields"
        ]

        matched = matching_columns(
            fields
        )

        candidates.append({
            "path":
                str(path),

            "filename":
                path.name,

            "suffix":
                path.suffix.lower(),

            "readable":
                str(
                    meta[
                        "readable"
                    ]
                ),

            "row_count":
                meta[
                    "row_count"
                ],

            "column_count":
                len(fields),

            "matched_interest_columns":
                "|".join(
                    matched
                ),

            "all_columns":
                "|".join(
                    fields
                ),

            "sample":
                sample_text(
                    meta.get(
                        "sample",
                        [],
                    ),
                    matched,
                ),

            "error":
                txt(
                    meta.get(
                        "error"
                    )
                ),
        })

    print()
    print("=" * 126)
    print("CANDIDATE INPUT FILES")
    print("=" * 126)

    for row in candidates:

        print()
        print("-" * 126)

        print(
            row[
                "filename"
            ]
        )

        print(
            "  rows:",
            row[
                "row_count"
            ],
        )

        print(
            "  columns:",
            row[
                "column_count"
            ],
        )

        print(
            "  matched:",
            row[
                "matched_interest_columns"
            ]
            or
            "NONE",
        )

        print(
            "  ALL:",
            row[
                "all_columns"
            ],
        )

        if row["sample"]:
            print(
                "  sample:",
                row[
                    "sample"
                ],
            )

    performance_candidates = [
        row
        for row in candidates
        if any(
            key
            in row[
                "filename"
            ].lower()
            for key in [
                "performance",
                "model",
                "delta",
                "repeat",
                "recovery",
                "phase5",
            ]
        )
    ]

    weather_candidates = [
        row
        for row in candidates
        if any(
            key
            in row[
                "filename"
            ].lower()
            for key in [
                "hrrr",
                "weather",
                "ptsc",
                "track",
                "temperature",
            ]
        )
    ]

    print()
    print("=" * 126)
    print("AUDIT SUMMARY")
    print("=" * 126)

    print()
    print(
        "Total relevant files:",
        len(
            candidates
        ),
    )

    print(
        "Performance/model candidates:",
        len(
            performance_candidates
        ),
    )

    print(
        "Weather/track candidates:",
        len(
            weather_candidates
        ),
    )

    print()
    print("PERFORMANCE/MODEL FILES")

    for row in performance_candidates:
        print(
            " ",
            row[
                "filename"
            ],
        )

    print()
    print("WEATHER/TRACK FILES")

    for row in weather_candidates:
        print(
            " ",
            row[
                "filename"
            ],
        )

    fields = [
        "path",
        "filename",
        "suffix",
        "readable",
        "row_count",
        "column_count",
        "matched_interest_columns",
        "all_columns",
        "sample",
        "error",
    ]

    with AUDIT_OUT.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=fields,
        )
        writer.writeheader()
        writer.writerows(
            candidates
        )

    qa_rows = [
        {
            "metric":
                "state_v3_present",

            "value":
                int(
                    STATE_V3.exists()
                ),

            "status":
                (
                    "PASS"
                    if STATE_V3.exists()
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "relevant_files_found",

            "value":
                len(
                    candidates
                ),

            "status":
                (
                    "PASS"
                    if len(
                        candidates
                    )
                    >
                    0
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "performance_candidates_found",

            "value":
                len(
                    performance_candidates
                ),

            "status":
                (
                    "PASS"
                    if len(
                        performance_candidates
                    )
                    >
                    0
                    else
                    "REVIEW"
                ),
        },

        {
            "metric":
                "weather_candidates_found",

            "value":
                len(
                    weather_candidates
                ),

            "status":
                (
                    "PASS"
                    if len(
                        weather_candidates
                    )
                    >
                    0
                    else
                    "REVIEW"
                ),
        },

        {
            "metric":
                "files_mutated",

            "value":
                0,

            "status":
                "PASS",
        },
    ]

    with QA_OUT.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "metric",
                "value",
                "status",
            ],
        )
        writer.writeheader()
        writer.writerows(
            qa_rows
        )

    hard_fail = any(
        row[
            "status"
        ]
        ==
        "FAIL"
        for row in qa_rows
    )

    print()
    print("=" * 126)

    if not hard_fail:
        print(
            "FINAL STATUS: "
            "R3B0_SIMULATOR_INPUT_INVENTORY_COMPLETE"
        )
    else:
        print(
            "FINAL STATUS: "
            "R3B0_SIMULATOR_INPUT_INVENTORY_REVIEW_REQUIRED"
        )

    print("=" * 126)

    print()
    print("OUTPUTS")
    print(AUDIT_OUT)
    print(QA_OUT)


if __name__ == "__main__":
    main()
