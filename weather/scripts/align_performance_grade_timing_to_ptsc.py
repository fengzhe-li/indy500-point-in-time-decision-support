from pathlib import Path
import math
import pandas as pd


TIMING_FILE = Path(
    "weather/output/performance_grade_attempt_timing.csv"
)

PTSC_FILE = Path(
    "weather/evidence/ptsc/"
    "indy500_day1_track_temp_2020_2024_time_normalized.csv"
)

OUTPUT_FILE = Path(
    "weather/output/"
    "performance_grade_attempt_realized_environment.csv"
)

QA_FILE = Path(
    "weather/output/"
    "performance_grade_attempt_realized_environment_qa.csv"
)

MAX_INTERPOLATION_GAP_MINUTES = 30.0


PREFERRED_ENV_COLUMNS = [
    "ambient_c",
    "track_c",
    "humidity",
    "wind",
    "pressure",
    "sensor_1_f",
    "sensor_2_f",
    "sensor_3_f",
    "sensor_4_f",
    "sensor_avg_f",
]


def parse_utc(series):
    return pd.to_datetime(
        series,
        utc=True,
        errors="coerce",
    )


def infer_year_from_session(session_id):
    if pd.isna(session_id):
        return None

    s = str(session_id)

    for year in [
        2020,
        2021,
        2022,
        2023,
        2024,
    ]:
        if str(year) in s:
            return year

    return None


def interpolate_value(
    before_row,
    after_row,
    target_time,
    column,
):
    v0 = before_row[column]
    v1 = after_row[column]

    if pd.isna(v0) or pd.isna(v1):
        return math.nan

    t0 = before_row["_utc"]
    t1 = after_row["_utc"]

    total_seconds = (
        t1 - t0
    ).total_seconds()

    if total_seconds <= 0:
        return math.nan

    fraction = (
        target_time - t0
    ).total_seconds() / total_seconds

    return (
        float(v0)
        + fraction
        * (
            float(v1)
            - float(v0)
        )
    )


def align_one_time(
    ptsc_year,
    target_time,
    env_columns,
):
    result = {
        "ptsc_alignment_status": None,
        "ptsc_before_utc": None,
        "ptsc_after_utc": None,
        "ptsc_gap_minutes": math.nan,
    }

    for col in env_columns:
        result[f"ptsc_{col}"] = math.nan

    if pd.isna(target_time):
        result[
            "ptsc_alignment_status"
        ] = "NO_TARGET_TIME"

        return result

    g = ptsc_year.sort_values(
        "_utc"
    ).reset_index(drop=True)

    if g.empty:
        result[
            "ptsc_alignment_status"
        ] = "NO_PTSC_ROWS_FOR_YEAR"

        return result

    before = g[
        g["_utc"] <= target_time
    ]

    after = g[
        g["_utc"] >= target_time
    ]

    if before.empty or after.empty:
        result[
            "ptsc_alignment_status"
        ] = "OUTSIDE_PTSC_COVERAGE"

        return result

    b = before.iloc[-1]
    a = after.iloc[0]

    result[
        "ptsc_before_utc"
    ] = b["_utc"].isoformat()

    result[
        "ptsc_after_utc"
    ] = a["_utc"].isoformat()

    gap_minutes = (
        a["_utc"] - b["_utc"]
    ).total_seconds() / 60.0

    result[
        "ptsc_gap_minutes"
    ] = gap_minutes

    if b["_utc"] == a["_utc"]:

        result[
            "ptsc_alignment_status"
        ] = "EXACT_PTSC_OBSERVATION"

        for col in env_columns:
            result[
                f"ptsc_{col}"
            ] = b[col]

        return result

    if (
        gap_minutes
        > MAX_INTERPOLATION_GAP_MINUTES
    ):

        result[
            "ptsc_alignment_status"
        ] = "PTSC_GAP_TOO_LARGE"

        return result

    result[
        "ptsc_alignment_status"
    ] = "LINEAR_INTERPOLATION"

    for col in env_columns:
        result[
            f"ptsc_{col}"
        ] = interpolate_value(
            b,
            a,
            target_time,
            col,
        )

    return result


def main():

    for file in [
        TIMING_FILE,
        PTSC_FILE,
    ]:
        if not file.exists():
            raise FileNotFoundError(
                f"Missing file: {file}"
            )

    timing = pd.read_csv(
        TIMING_FILE
    )

    ptsc = pd.read_csv(
        PTSC_FILE
    )

    if len(timing) != 129:
        raise RuntimeError(
            f"Expected 129 timing rows, got "
            f"{len(timing)}"
        )

    if (
        timing[
            "timing_class"
        ]
        .ne(
            "PERFORMANCE_GRADE_SEQUENCE_MATCH"
        )
        .any()
    ):
        raise RuntimeError(
            "Unexpected timing_class present."
        )

    if (
        timing[
            "performance_alignment_usable"
        ]
        .astype(str)
        .str.lower()
        .ne("true")
        .any()
    ):
        raise RuntimeError(
            "Found timing rows not marked "
            "performance_alignment_usable."
        )

    timing["_target_utc"] = parse_utc(
        timing[
            "mapped_capture_time_utc"
        ]
    )

    if timing[
        "_target_utc"
    ].isna().any():
        raise RuntimeError(
            "Unparseable mapped_capture_time_utc "
            "found."
        )

    timing["year"] = timing[
        "session_id"
    ].apply(
        infer_year_from_session
    )

    if timing[
        "year"
    ].isna().any():
        raise RuntimeError(
            "Could not infer year for some timing rows."
        )

    timing[
        "year"
    ] = timing[
        "year"
    ].astype(int)

    ptsc["_utc"] = parse_utc(
        ptsc["utc_datetime"]
    )

    if ptsc["_utc"].isna().any():
        raise RuntimeError(
            "Unparseable PTSC UTC timestamp found."
        )

    env_columns = [
        col
        for col in PREFERRED_ENV_COLUMNS
        if col in ptsc.columns
    ]

    if "track_c" not in env_columns:
        raise RuntimeError(
            "PTSC track_c column not found."
        )

    rows = []

    for _, row in timing.iterrows():

        year = int(
            row["year"]
        )

        target_time = row[
            "_target_utc"
        ]

        ptsc_year = ptsc[
            ptsc["year"] == year
        ].copy()

        aligned = align_one_time(
            ptsc_year,
            target_time,
            env_columns,
        )

        out = {
            "attempt_id":
                row["attempt_id"],
            "session_id":
                row["session_id"],
            "year":
                year,
            "entry_key":
                row.get(
                    "entry_key",
                    None,
                ),
            "attempt_key":
                row.get(
                    "attempt_key",
                    None,
                ),
            "car_number":
                row.get(
                    "car_number",
                    None,
                ),
            "driver_name":
                row.get(
                    "driver_name",
                    None,
                ),
            "car_attempt_index":
                row.get(
                    "car_attempt_index",
                    None,
                ),
            "mapped_capture_event_id":
                row[
                    "mapped_capture_event_id"
                ],
            "mapped_capture_time_utc":
                row[
                    "mapped_capture_time_utc"
                ],
            "timing_class":
                row[
                    "timing_class"
                ],
            "timing_basis":
                row[
                    "timing_basis"
                ],
            "calibration_status":
                row[
                    "calibration_status"
                ],
            "calibration_reference":
                row[
                    "calibration_reference"
                ],
            "performance_alignment_usable":
                row[
                    "performance_alignment_usable"
                ],
            "chronology_usable":
                row[
                    "chronology_usable"
                ],
            "queue_replay_usable":
                row[
                    "queue_replay_usable"
                ],
            "environment_time_semantic":
                (
                    "RECORDER_CAPTURE_AS_"
                    "PERFORMANCE_GRADE_APPROXIMATION"
                ),
            "max_interpolation_gap_minutes":
                MAX_INTERPOLATION_GAP_MINUTES,
        }

        out.update(
            aligned
        )

        rows.append(
            out
        )

    result = pd.DataFrame(
        rows
    )

    if result[
        "attempt_id"
    ].duplicated().any():
        raise RuntimeError(
            "Duplicate attempt_id in aligned output."
        )

    result = result.sort_values(
        [
            "year",
            "mapped_capture_time_utc",
            "car_number",
            "car_attempt_index",
        ]
    ).reset_index(drop=True)

    # -----------------------------
    # QA summary
    # -----------------------------

    qa_rows = []

    for year, g in result.groupby(
        "year"
    ):

        total = len(g)

        usable = g[
            "ptsc_alignment_status"
        ].isin(
            [
                "EXACT_PTSC_OBSERVATION",
                "LINEAR_INTERPOLATION",
            ]
        ).sum()

        track_nonnull = g[
            "ptsc_track_c"
        ].notna().sum()

        qa_rows.append(
            {
                "year":
                    year,
                "timing_rows":
                    total,
                "environment_aligned_rows":
                    int(usable),
                "track_c_nonnull_rows":
                    int(track_nonnull),
                "environment_coverage_pct":
                    (
                        100.0
                        * usable
                        / total
                        if total
                        else 0.0
                    ),
            }
        )

    qa = pd.DataFrame(
        qa_rows
    )

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    result.to_csv(
        OUTPUT_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    qa.to_csv(
        QA_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    print()
    print("=" * 90)
    print(
        "PERFORMANCE-GRADE TIMING "
        "TO PTSC ALIGNMENT"
    )
    print("=" * 90)

    print()
    print(
        "Input timing rows:",
        len(timing)
    )

    print()
    print("ALIGNMENT STATUS COUNTS")
    print("-" * 40)

    print(
        result[
            "ptsc_alignment_status"
        ]
        .value_counts(
            dropna=False
        )
        .to_string()
    )

    print()
    print("COVERAGE BY YEAR")
    print("-" * 40)

    print(
        qa.to_string(
            index=False
        )
    )

    print()
    print("TRACK_C SUMMARY")
    print("-" * 40)

    track_summary = (
        result[
            result[
                "ptsc_track_c"
            ].notna()
        ]
        .groupby(
            "year"
        )[
            "ptsc_track_c"
        ]
        .agg(
            [
                "count",
                "min",
                "median",
                "max",
            ]
        )
    )

    print(
        track_summary.to_string()
    )

    print()
    print("LARGE-GAP / COVERAGE FAILURES")
    print("-" * 40)

    failures = result[
        ~result[
            "ptsc_alignment_status"
        ].isin(
            [
                "EXACT_PTSC_OBSERVATION",
                "LINEAR_INTERPOLATION",
            ]
        )
    ]

    if failures.empty:
        print("None")
    else:
        print(
            failures[
                [
                    "year",
                    "car_number",
                    "driver_name",
                    "car_attempt_index",
                    "mapped_capture_time_utc",
                    "ptsc_alignment_status",
                    "ptsc_before_utc",
                    "ptsc_after_utc",
                    "ptsc_gap_minutes",
                ]
            ].to_string(
                index=False
            )
        )

    print()
    print("=" * 90)
    print("SEMANTIC POLICY")
    print("=" * 90)

    print(
        "Recorder capture remains an approximate "
        "performance-alignment timestamp."
    )

    print(
        "It is NOT treated as exact timed-run start."
    )

    print(
        "PTSC interpolation is rejected when "
        f"bracketing gap > "
        f"{MAX_INTERPOLATION_GAP_MINUTES:.0f} minutes."
    )

    print()
    print("=" * 90)
    print("OUTPUT")
    print("=" * 90)

    print(
        OUTPUT_FILE
    )

    print(
        QA_FILE
    )


if __name__ == "__main__":
    main()
    