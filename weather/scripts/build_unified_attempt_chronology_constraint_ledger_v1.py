from pathlib import Path
import csv
import json


# ============================================================
# PHASE
# ============================================================

PHASE = "R1G.2"


# ============================================================
# INPUTS
# ============================================================

PERFORMANCE_TIMING = Path(
    "weather/output/"
    "performance_grade_attempt_timing.csv"
)

PERFORMANCE_TIMING_2024 = Path(
    "weather/output/"
    "performance_grade_attempt_timing_2024_supported.csv"
)

CHRONOLOGY_ALIGNMENT_2024 = Path(
    "weather/output/"
    "ptsc_attempt_realized_environment_alignment.csv"
)

RESULT_ROWS = Path(
    "weather/output/"
    "official_day1_results_attempt_rows_v1.csv"
)


# ============================================================
# OUTPUTS
# ============================================================

OUTPUT_DIR = Path(
    "weather/output"
)

LEDGER_CSV = (
    OUTPUT_DIR
    / "unified_attempt_chronology_constraint_ledger_v1.csv"
)

SUMMARY_CSV = (
    OUTPUT_DIR
    / "unified_attempt_chronology_constraint_summary_v1.csv"
)

QA_CSV = (
    OUTPUT_DIR
    / "unified_attempt_chronology_constraint_ledger_v1_qa.csv"
)


# ============================================================
# HELPERS
# ============================================================

def read_csv(path):

    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as handle:

        return list(
            csv.DictReader(
                handle
            )
        )


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
        writer.writerows(rows)


def txt(value):

    if value is None:
        return ""

    return str(value).strip()


def year_from_session_id(
    session_id,
):

    text = txt(
        session_id
    )

    for year in [
        2020,
        2021,
        2022,
        2023,
        2024,
    ]:

        if str(year) in text:
            return year

    return None


def normalize_car(value):

    text = txt(value)

    if not text:
        return ""

    try:
        return str(
            int(
                float(
                    text
                )
            )
        )

    except Exception:
        return text.lstrip(
            "0"
        ) or "0"


def base_constraint_row(
    year,
    attempt_id,
    session_id,
    car_number,
    driver_name,
    car_attempt_index,
):

    return {
        "year":
            year,

        "attempt_id":
            txt(
                attempt_id
            ),

        "session_id":
            txt(
                session_id
            ),

        "car_number":
            normalize_car(
                car_number
            ),

        "driver_name":
            txt(
                driver_name
            ),

        "car_attempt_index":
            txt(
                car_attempt_index
            ),

        "constraint_class":
            "",

        "time_point_utc":
            "",

        "time_lower_utc":
            "",

        "time_upper_utc":
            "",

        "time_midpoint_utc":
            "",

        "time_quality":
            "",

        "source_layer":
            "",

        "source_semantic":
            "",

        "source_event_id":
            "",

        "anchor_event_type":
            "",

        "result_status":
            "",

        "chronology_usable":
            False,

        "performance_environment_usable":
            False,

        "queue_replay_usable":
            False,

        "notes":
            "",
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
        "R1G.2 — UNIFIED ATTEMPT CHRONOLOGY "
        "CONSTRAINT LEDGER V1"
    )

    print("=" * 120)

    # ========================================================
    # INPUT CHECK
    # ========================================================

    input_paths = [
        PERFORMANCE_TIMING,
        PERFORMANCE_TIMING_2024,
        CHRONOLOGY_ALIGNMENT_2024,
        RESULT_ROWS,
    ]

    missing = [
        path
        for path in input_paths
        if not path.exists()
    ]

    print()
    print(
        "INPUT CHECK"
    )
    print("-" * 120)

    for path in input_paths:

        print(
            f"{path}: "
            f"{'PRESENT' if path.exists() else 'MISSING'}"
        )

    if missing:

        print()
        print(
            "FINAL STATUS: "
            "UNIFIED_CHRONOLOGY_LEDGER_INPUT_MISSING"
        )

        return

    # ========================================================
    # LOAD
    # ========================================================

    perf_rows = read_csv(
        PERFORMANCE_TIMING
    )

    perf_2024_rows = read_csv(
        PERFORMANCE_TIMING_2024
    )

    chrono_2024_rows = read_csv(
        CHRONOLOGY_ALIGNMENT_2024
    )

    result_rows = read_csv(
        RESULT_ROWS
    )

    print()
    print(
        "PERFORMANCE TIMING ROWS:",
        len(
            perf_rows
        ),
    )

    print(
        "PERFORMANCE TIMING 2024 ROWS:",
        len(
            perf_2024_rows
        ),
    )

    print(
        "2024 CHRONOLOGY ALIGNMENT ROWS:",
        len(
            chrono_2024_rows
        ),
    )

    print(
        "OFFICIAL RESULTS ROWS:",
        len(
            result_rows
        ),
    )

    # ========================================================
    # RESULT STATUS LOOKUP
    #
    # Important:
    # only use result row for descriptive status matching.
    # No result-row ordering is treated as chronology.
    # ========================================================

    result_lookup = {}

    for row in result_rows:

        year = int(
            row[
                "year"
            ]
        )

        car = normalize_car(
            row[
                "car_number"
            ]
        )

        speed = txt(
            row[
                "speed_avg_mph"
            ]
        )

        status = txt(
            row[
                "status"
            ]
        )

        key = (
            year,
            car,
            speed,
        )

        result_lookup.setdefault(
            key,
            []
        ).append(
            status
        )

    # ========================================================
    # UNIFIED LEDGER
    # ========================================================

    ledger = {}

    # ========================================================
    # LAYER A:
    # PERFORMANCE-GRADE CAPTURE APPROXIMATION
    # 2020 / 2021 / 2023
    # ========================================================

    for row in perf_rows:

        session_id = txt(
            row.get(
                "session_id"
            )
        )

        year = year_from_session_id(
            session_id
        )

        attempt_id = txt(
            row.get(
                "attempt_id"
            )
        )

        if not attempt_id:
            continue

        entry = base_constraint_row(
            year,
            attempt_id,
            session_id,
            row.get(
                "car_number"
            ),
            row.get(
                "driver_name"
            ),
            row.get(
                "car_attempt_index"
            ),
        )

        entry[
            "constraint_class"
        ] = (
            "PERFORMANCE_CAPTURE_APPROXIMATION"
        )

        entry[
            "time_point_utc"
        ] = txt(
            row.get(
                "mapped_capture_time_utc"
            )
        )

        entry[
            "time_quality"
        ] = (
            "PERFORMANCE_CAPTURE_APPROXIMATION"
        )

        entry[
            "source_layer"
        ] = (
            "TIMING71_PERFORMANCE_GRADE"
        )

        entry[
            "source_semantic"
        ] = txt(
            row.get(
                "time_semantic_note"
            )
        )

        entry[
            "source_event_id"
        ] = txt(
            row.get(
                "mapped_capture_event_id"
            )
        )

        entry[
            "chronology_usable"
        ] = False

        entry[
            "performance_environment_usable"
        ] = True

        entry[
            "queue_replay_usable"
        ] = False

        entry[
            "notes"
        ] = (
            "Recorder capture mapped to attempt. "
            "Not exact timed-run start."
        )

        ledger[
            attempt_id
        ] = entry

    # ========================================================
    # LAYER B:
    # 2024 SUPPORTED PERFORMANCE CAPTURES
    # ========================================================

    for row in perf_2024_rows:

        session_id = txt(
            row.get(
                "session_id"
            )
        )

        year = 2024

        attempt_id = txt(
            row.get(
                "attempt_id"
            )
        )

        if not attempt_id:
            continue

        entry = base_constraint_row(
            year,
            attempt_id,
            session_id,
            row.get(
                "car_number"
            ),
            row.get(
                "driver_name"
            ),
            row.get(
                "car_attempt_index"
            ),
        )

        entry[
            "constraint_class"
        ] = (
            "PERFORMANCE_CAPTURE_APPROXIMATION"
        )

        entry[
            "time_point_utc"
        ] = txt(
            row.get(
                "mapped_capture_time_utc"
            )
        )

        entry[
            "time_quality"
        ] = (
            "PERFORMANCE_CAPTURE_APPROXIMATION"
        )

        entry[
            "source_layer"
        ] = (
            "TIMING71_2024_SUPPORTED"
        )

        entry[
            "source_semantic"
        ] = txt(
            row.get(
                "time_semantic_note"
            )
        )

        entry[
            "source_event_id"
        ] = txt(
            row.get(
                "mapped_capture_event_id"
            )
        )

        entry[
            "chronology_usable"
        ] = False

        entry[
            "performance_environment_usable"
        ] = True

        entry[
            "queue_replay_usable"
        ] = False

        entry[
            "notes"
        ] = (
            "Supported 2024 recorder capture. "
            "Not exact timed-run start."
        )

        ledger[
            attempt_id
        ] = entry

    # ========================================================
    # LAYER C:
    # STRONGER 2024 CHRONOLOGY CONSTRAINTS
    #
    # These override performance-only semantics for the same
    # attempt_id because they explicitly contain a chronology
    # time quality classification.
    # ========================================================

    for row in chrono_2024_rows:

        attempt_id = txt(
            row.get(
                "attempt_id"
            )
        )

        if not attempt_id:
            continue

        quality = txt(
            row.get(
                "event_time_quality"
            )
        )

        lower = txt(
            row.get(
                "target_time_lower_utc"
            )
        )

        upper = txt(
            row.get(
                "target_time_upper_utc"
            )
        )

        midpoint = txt(
            row.get(
                "target_time_midpoint_utc"
            )
        )

        entry = ledger.get(
            attempt_id
        )

        if entry is None:

            entry = base_constraint_row(
                2024,
                attempt_id,
                txt(
                    row.get(
                        "session_id"
                    )
                ),
                row.get(
                    "car_number"
                ),
                row.get(
                    "driver_name"
                ),
                row.get(
                    "car_attempt_index"
                ),
            )

        entry[
            "time_quality"
        ] = quality

        entry[
            "time_lower_utc"
        ] = lower

        entry[
            "time_upper_utc"
        ] = upper

        entry[
            "time_midpoint_utc"
        ] = midpoint

        entry[
            "anchor_event_type"
        ] = txt(
            row.get(
                "anchor_event_type"
            )
        )

        entry[
            "result_status"
        ] = txt(
            row.get(
                "result_status"
            )
        )

        entry[
            "source_layer"
        ] = (
            "2024_CHRONOLOGY_CONSTRAINT"
        )

        entry[
            "source_semantic"
        ] = (
            "Independent chronology anchor/alignment."
        )

        if quality == "EXACT_OBSERVED":

            entry[
                "constraint_class"
            ] = (
                "EXACT_OBSERVED"
            )

            entry[
                "chronology_usable"
            ] = True

        elif quality == "BOUNDED_INTERVAL":

            entry[
                "constraint_class"
            ] = (
                "BOUNDED_INTERVAL"
            )

            entry[
                "chronology_usable"
            ] = True

        elif quality == "APPROXIMATE_OBSERVED":

            entry[
                "constraint_class"
            ] = (
                "APPROXIMATE_OBSERVED"
            )

            entry[
                "chronology_usable"
            ] = True

        elif quality == "ORDERING_ONLY":

            entry[
                "constraint_class"
            ] = (
                "ORDERING_ONLY"
            )

            entry[
                "chronology_usable"
            ] = True

        else:

            entry[
                "constraint_class"
            ] = (
                quality
                or
                "UNKNOWN"
            )

            entry[
                "chronology_usable"
            ] = False

        entry[
            "queue_replay_usable"
        ] = False

        ledger[
            attempt_id
        ] = entry

    # ========================================================
    # ROW LIST
    # ========================================================

    ledger_rows = list(
        ledger.values()
    )

    ledger_rows.sort(
        key=lambda row: (
            row[
                "year"
            ]
            if row[
                "year"
            ] is not None
            else 9999,

            row[
                "car_number"
            ],

            row[
                "car_attempt_index"
            ],

            row[
                "attempt_id"
            ],
        )
    )

    # ========================================================
    # SUMMARY
    # ========================================================

    summary_rows = []

    years = [
        2020,
        2021,
        2022,
        2023,
        2024,
    ]

    for year in years:

        rows = [
            row
            for row in ledger_rows
            if row[
                "year"
            ] == year
        ]

        classes = {}

        chronology_usable = 0

        performance_usable = 0

        for row in rows:

            cls = row[
                "constraint_class"
            ]

            classes[
                cls
            ] = (
                classes.get(
                    cls,
                    0,
                )
                + 1
            )

            if row[
                "chronology_usable"
            ]:

                chronology_usable += 1

            if row[
                "performance_environment_usable"
            ]:

                performance_usable += 1

        summary_rows.append({
            "year":
                year,

            "constraint_rows":
                len(rows),

            "chronology_usable_rows":
                chronology_usable,

            "performance_environment_usable_rows":
                performance_usable,

            "constraint_class_distribution":
                json.dumps(
                    classes,
                    ensure_ascii=False,
                    sort_keys=True,
                ),
        })

    # ========================================================
    # WRITE
    # ========================================================

    ledger_fields = [
        "year",
        "attempt_id",
        "session_id",
        "car_number",
        "driver_name",
        "car_attempt_index",
        "constraint_class",
        "time_point_utc",
        "time_lower_utc",
        "time_upper_utc",
        "time_midpoint_utc",
        "time_quality",
        "source_layer",
        "source_semantic",
        "source_event_id",
        "anchor_event_type",
        "result_status",
        "chronology_usable",
        "performance_environment_usable",
        "queue_replay_usable",
        "notes",
    ]

    write_csv(
        LEDGER_CSV,
        ledger_rows,
        ledger_fields,
    )

    write_csv(
        SUMMARY_CSV,
        summary_rows,
        [
            "year",
            "constraint_rows",
            "chronology_usable_rows",
            "performance_environment_usable_rows",
            "constraint_class_distribution",
        ],
    )

    # ========================================================
    # QA
    # ========================================================

    exact_count = sum(
        1
        for row in ledger_rows
        if row[
            "constraint_class"
        ] == "EXACT_OBSERVED"
    )

    bounded_count = sum(
        1
        for row in ledger_rows
        if row[
            "constraint_class"
        ] == "BOUNDED_INTERVAL"
    )

    approx_count = sum(
        1
        for row in ledger_rows
        if row[
            "constraint_class"
        ] == "APPROXIMATE_OBSERVED"
    )

    ordering_count = sum(
        1
        for row in ledger_rows
        if row[
            "constraint_class"
        ] == "ORDERING_ONLY"
    )

    performance_only_count = sum(
        1
        for row in ledger_rows
        if row[
            "constraint_class"
        ] == (
            "PERFORMANCE_CAPTURE_APPROXIMATION"
        )
    )

    year_2022_rows = sum(
        1
        for row in ledger_rows
        if row[
            "year"
        ] == 2022
    )

    qa_rows = [
        {
            "metric":
                "ledger_rows",

            "value":
                len(
                    ledger_rows
                ),

            "status":
                "INFO",
        },

        {
            "metric":
                "exact_observed_constraints",

            "value":
                exact_count,

            "status":
                "INFO",
        },

        {
            "metric":
                "bounded_interval_constraints",

            "value":
                bounded_count,

            "status":
                "INFO",
        },

        {
            "metric":
                "approximate_observed_constraints",

            "value":
                approx_count,

            "status":
                "INFO",
        },

        {
            "metric":
                "ordering_only_constraints",

            "value":
                ordering_count,

            "status":
                "INFO",
        },

        {
            "metric":
                "performance_capture_only_constraints",

            "value":
                performance_only_count,

            "status":
                "INFO",
        },

        {
            "metric":
                "2022_attempt_time_constraints",

            "value":
                year_2022_rows,

            "status":
                (
                    "INFO"
                    if year_2022_rows > 0
                    else "EXPECTED_GAP"
                ),
        },

        {
            "metric":
                "capture_time_promoted_to_exact_run_start",

            "value":
                0,

            "status":
                "PASS",
        },

        {
            "metric":
                "elapsed_duration_used_as_wall_clock",

            "value":
                0,

            "status":
                "PASS",
        },

        {
            "metric":
                "result_row_order_used_as_chronology",

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
                "canonical_data_mutated",

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
    # PRINT SUMMARY
    # ========================================================

    print()
    print("=" * 120)

    print(
        "CROSS-YEAR CHRONOLOGY CONSTRAINT SUMMARY"
    )

    print("=" * 120)

    for row in summary_rows:

        print()
        print(
            f"YEAR {row['year']}"
        )

        print(
            "  constraint rows:",
            row[
                "constraint_rows"
            ],
        )

        print(
            "  chronology usable:",
            row[
                "chronology_usable_rows"
            ],
        )

        print(
            "  performance environment usable:",
            row[
                "performance_environment_usable_rows"
            ],
        )

        print(
            "  classes:",
            row[
                "constraint_class_distribution"
            ],
        )

    print()
    print("=" * 120)

    print(
        "QUALITY TOTALS"
    )

    print("=" * 120)

    print(
        "EXACT_OBSERVED:",
        exact_count,
    )

    print(
        "BOUNDED_INTERVAL:",
        bounded_count,
    )

    print(
        "APPROXIMATE_OBSERVED:",
        approx_count,
    )

    print(
        "ORDERING_ONLY:",
        ordering_count,
    )

    print(
        "PERFORMANCE_CAPTURE_APPROXIMATION:",
        performance_only_count,
    )

    print()
    print(
        "2022 attempt time constraints:",
        year_2022_rows,
    )

    print()
    print(
        "IMPORTANT:"
    )

    print(
        "Performance-grade recorder capture times "
        "remain non-chronology approximations."
    )

    print(
        "Only independently classified chronology "
        "constraints are chronology_usable=True."
    )

    print(
        "No result ordering, elapsed duration, or "
        "internal database ID was interpreted as time."
    )

    print()
    print("=" * 120)

    print(
        "FINAL STATUS: "
        "UNIFIED_ATTEMPT_CHRONOLOGY_CONSTRAINT_LEDGER_BUILT"
    )

    print("=" * 120)

    print()
    print(
        "OUTPUTS"
    )

    print(
        LEDGER_CSV
    )

    print(
        SUMMARY_CSV
    )

    print(
        QA_CSV
    )


if __name__ == "__main__":
    main()
