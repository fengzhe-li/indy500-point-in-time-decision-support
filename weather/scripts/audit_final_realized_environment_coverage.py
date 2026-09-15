from pathlib import Path
import math
import pandas as pd


# ============================================================
# INPUTS
# ============================================================

ATTEMPTS_FILE = Path(
    "data/canonical/v1/attempts.csv"
)

LEGACY_PERFORMANCE_ENV_FILE = Path(
    "weather/output/"
    "performance_grade_attempt_realized_environment.csv"
)

PERFORMANCE_2024_ENV_FILE = Path(
    "weather/output/"
    "performance_grade_attempt_realized_environment_2024_supported.csv"
)

CHRONOLOGY_2024_ENV_FILE = Path(
    "weather/output/"
    "ptsc_attempt_realized_environment_alignment.csv"
)


# ============================================================
# OUTPUTS
# ============================================================

COVERAGE_OUTPUT = Path(
    "weather/output/"
    "final_realized_environment_coverage_audit.csv"
)

OVERLAP_OUTPUT = Path(
    "weather/output/"
    "final_realized_environment_2024_overlap_audit.csv"
)

REPORT_OUTPUT = Path(
    "weather/output/"
    "final_realized_environment_coverage_audit.md"
)


# ============================================================
# CONSTANTS
# ============================================================

SESSION_BY_YEAR = {
    2020: "INDY500_DAY1_2020",
    2021: "INDY500_DAY1_2021",
    2022: "INDY500_DAY1_2022",
    2023: "INDY500_DAY1_2023",
    2024: "INDY500_DAY1_2024",
}

SUCCESS_STATUSES = {
    "LINEAR_INTERPOLATION",
    "EXACT_PTSC_OBSERVATION",
}

YEAR_STATUS = {
    2020: "READY_WITH_SUPPORTED_SUBSET",
    2021: "READY_WITH_SUPPORTED_SUBSET",
    2022: "UNAVAILABLE_NO_TRUSTWORTHY_ATTEMPT_TIME_BRIDGE",
    2023: "READY_WITH_SUPPORTED_SUBSET",
    2024: "READY_WITH_SUPPORTED_SUBSET",
}


# ============================================================
# HELPERS
# ============================================================

def read_required(path):
    if not path.exists():
        raise FileNotFoundError(
            f"Missing required file: {path}"
        )

    return pd.read_csv(
        path,
        low_memory=False,
    )


def detect_column(
    df,
    exact_candidates,
    contains_candidates=None,
):
    for col in exact_candidates:
        if col in df.columns:
            return col

    if contains_candidates:
        for col in df.columns:
            lower = col.lower()

            if all(
                token.lower() in lower
                for token in contains_candidates
            ):
                return col

    return None


def detect_track_column(df):
    return detect_column(
        df,
        [
            "ptsc_track_c",
            "track_c",
            "aligned_track_c",
            "track_temp_c",
            "track_temperature_c",
        ],
        [
            "track",
            "c",
        ],
    )


def detect_ambient_column(df):
    return detect_column(
        df,
        [
            "ptsc_ambient_c",
            "ambient_c",
            "aligned_ambient_c",
            "air_temp_c",
            "temperature_c",
        ],
    )


def detect_humidity_column(df):
    return detect_column(
        df,
        [
            "ptsc_humidity",
            "humidity",
            "aligned_humidity",
            "relative_humidity",
            "relative_humidity_pct",
        ],
    )


def detect_status_column(df):
    return detect_column(
        df,
        [
            "ptsc_alignment_status",
            "alignment_status",
            "environment_alignment_status",
        ],
    )


def detect_time_column(df):
    return detect_column(
        df,
        [
            "mapped_capture_time_utc",
            "target_time_utc",
            "alignment_target_time_utc",
            "event_time_utc",
            "midpoint_utc",
        ],
    )


def numeric_series(df, col):
    if col is None:
        return pd.Series(
            [math.nan] * len(df),
            index=df.index,
            dtype=float,
        )

    return pd.to_numeric(
        df[col],
        errors="coerce",
    )


def normalize_attempt_id(series):
    return (
        series
        .astype("string")
        .str.strip()
    )


def successful_mask(df):
    status_col = detect_status_column(df)
    track_col = detect_track_column(df)

    if status_col is not None:
        status_success = (
            df[status_col]
            .astype(str)
            .isin(SUCCESS_STATUSES)
        )
    else:
        status_success = pd.Series(
            [True] * len(df),
            index=df.index,
        )

    if track_col is not None:
        track_success = (
            pd.to_numeric(
                df[track_col],
                errors="coerce",
            )
            .notna()
        )
    else:
        track_success = pd.Series(
            [False] * len(df),
            index=df.index,
        )

    return status_success & track_success


def infer_year(df):
    if "year" in df.columns:
        return pd.to_numeric(
            df["year"],
            errors="coerce",
        )

    if "session_id" in df.columns:
        return pd.to_numeric(
            df["session_id"]
            .astype(str)
            .str.extract(
                r"(20\d{2})",
                expand=False,
            ),
            errors="coerce",
        )

    return pd.Series(
        [math.nan] * len(df),
        index=df.index,
    )


def safe_mae(series):
    s = pd.to_numeric(
        series,
        errors="coerce",
    ).dropna()

    if s.empty:
        return math.nan

    return float(
        s.abs().mean()
    )


def safe_max_abs(series):
    s = pd.to_numeric(
        series,
        errors="coerce",
    ).dropna()

    if s.empty:
        return math.nan

    return float(
        s.abs().max()
    )


# ============================================================
# MAIN
# ============================================================

def main():

    # --------------------------------------------------------
    # Load
    # --------------------------------------------------------

    attempts = read_required(
        ATTEMPTS_FILE
    )

    legacy = read_required(
        LEGACY_PERFORMANCE_ENV_FILE
    )

    perf2024 = read_required(
        PERFORMANCE_2024_ENV_FILE
    )

    chrono2024 = read_required(
        CHRONOLOGY_2024_ENV_FILE
    )

    print()
    print("=" * 100)
    print(
        "FINAL REALIZED-ENVIRONMENT COVERAGE AUDIT"
    )
    print("=" * 100)

    print()
    print("INPUT FILES")
    print("-" * 70)

    print(
        f"Attempts:              {len(attempts)} rows"
    )
    print(
        f"Legacy performance:    {len(legacy)} rows"
    )
    print(
        f"2024 performance:       {len(perf2024)} rows"
    )
    print(
        f"2024 chronology layer:  {len(chrono2024)} rows"
    )

    # --------------------------------------------------------
    # Schema detection
    # --------------------------------------------------------

    legacy_track = detect_track_column(
        legacy
    )

    perf2024_track = detect_track_column(
        perf2024
    )

    chrono_track = detect_track_column(
        chrono2024
    )

    legacy_status = detect_status_column(
        legacy
    )

    perf2024_status = detect_status_column(
        perf2024
    )

    chrono_status = detect_status_column(
        chrono2024
    )

    print()
    print("DETECTED ENVIRONMENT COLUMNS")
    print("-" * 70)

    print(
        f"Legacy performance track:   {legacy_track}"
    )
    print(
        f"2024 performance track:      {perf2024_track}"
    )
    print(
        f"2024 chronology track:       {chrono_track}"
    )

    print(
        f"Legacy alignment status:     {legacy_status}"
    )
    print(
        f"2024 performance status:     {perf2024_status}"
    )
    print(
        f"2024 chronology status:      {chrono_status}"
    )

    if legacy_track is None:
        raise RuntimeError(
            "Could not detect track temperature column "
            "in legacy performance environment file."
        )

    if perf2024_track is None:
        raise RuntimeError(
            "Could not detect track temperature column "
            "in 2024 performance environment file."
        )

    if chrono_track is None:
        raise RuntimeError(
            "Could not detect track temperature column "
            "in 2024 chronology environment file."
        )

    # --------------------------------------------------------
    # Normalize years
    # --------------------------------------------------------

    legacy = legacy.copy()
    perf2024 = perf2024.copy()
    chrono2024 = chrono2024.copy()

    legacy["_year"] = infer_year(
        legacy
    )

    perf2024["_year"] = infer_year(
        perf2024
    )

    chrono2024["_year"] = infer_year(
        chrono2024
    )

    # --------------------------------------------------------
    # Successful rows
    # --------------------------------------------------------

    legacy["_environment_success"] = (
        successful_mask(
            legacy
        )
    )

    perf2024["_environment_success"] = (
        successful_mask(
            perf2024
        )
    )

    chrono2024["_environment_success"] = (
        successful_mask(
            chrono2024
        )
    )

    # --------------------------------------------------------
    # Canonical attempt denominators
    # --------------------------------------------------------

    canonical_counts = {}

    for year, session in SESSION_BY_YEAR.items():

        canonical_counts[year] = int(
            (
                attempts[
                    "session_id"
                ].astype(str)
                == session
            ).sum()
        )

    # --------------------------------------------------------
    # Performance-grade counts
    # --------------------------------------------------------

    performance_counts = {}

    for year in [
        2020,
        2021,
        2023,
    ]:

        subset = legacy[
            legacy["_year"] == year
        ]

        performance_counts[year] = int(
            subset[
                "_environment_success"
            ].sum()
        )

    performance_counts[2022] = 0

    performance_counts[2024] = int(
        perf2024[
            "_environment_success"
        ].sum()
    )

    # --------------------------------------------------------
    # 2024 chronology counts
    # --------------------------------------------------------

    chronology_2024_success = chrono2024[
        chrono2024[
            "_environment_success"
        ]
    ].copy()

    chronology_2024_count = len(
        chronology_2024_success
    )

    # --------------------------------------------------------
    # 2024 overlap
    # --------------------------------------------------------

    if "attempt_id" not in perf2024.columns:
        raise RuntimeError(
            "2024 performance file has no attempt_id."
        )

    if "attempt_id" not in chrono2024.columns:
        raise RuntimeError(
            "2024 chronology environment file "
            "has no attempt_id."
        )

    perf_success = perf2024[
        perf2024[
            "_environment_success"
        ]
    ].copy()

    chrono_success = chronology_2024_success.copy()

    perf_success["_attempt_id_norm"] = (
        normalize_attempt_id(
            perf_success[
                "attempt_id"
            ]
        )
    )

    chrono_success["_attempt_id_norm"] = (
        normalize_attempt_id(
            chrono_success[
                "attempt_id"
            ]
        )
    )

    perf_success = perf_success[
        perf_success[
            "_attempt_id_norm"
        ].notna()
    ].copy()

    chrono_success = chrono_success[
        chrono_success[
            "_attempt_id_norm"
        ].notna()
    ].copy()

    perf_ambient = detect_ambient_column(
        perf_success
    )

    chrono_ambient = detect_ambient_column(
        chrono_success
    )

    perf_humidity = detect_humidity_column(
        perf_success
    )

    chrono_humidity = detect_humidity_column(
        chrono_success
    )

    perf_time = detect_time_column(
        perf_success
    )

    chrono_time = detect_time_column(
        chrono_success
    )

    perf_extract = pd.DataFrame(
        {
            "_attempt_id_norm":
                perf_success[
                    "_attempt_id_norm"
                ],
            "attempt_id":
                perf_success[
                    "attempt_id"
                ],
            "car_number_performance":
                (
                    perf_success[
                        "car_number"
                    ]
                    if "car_number" in perf_success.columns
                    else pd.NA
                ),
            "driver_name_performance":
                (
                    perf_success[
                        "driver_name"
                    ]
                    if "driver_name" in perf_success.columns
                    else pd.NA
                ),
            "performance_time_utc":
                (
                    perf_success[
                        perf_time
                    ]
                    if perf_time is not None
                    else pd.NA
                ),
            "performance_track_c":
                numeric_series(
                    perf_success,
                    perf2024_track,
                ),
            "performance_ambient_c":
                numeric_series(
                    perf_success,
                    perf_ambient,
                ),
            "performance_humidity":
                numeric_series(
                    perf_success,
                    perf_humidity,
                ),
        }
    )

    chrono_extract = pd.DataFrame(
        {
            "_attempt_id_norm":
                chrono_success[
                    "_attempt_id_norm"
                ],
            "attempt_id_chronology":
                chrono_success[
                    "attempt_id"
                ],
            "car_number_chronology":
                (
                    chrono_success[
                        "car_number"
                    ]
                    if "car_number" in chrono_success.columns
                    else pd.NA
                ),
            "driver_name_chronology":
                (
                    chrono_success[
                        "driver_name"
                    ]
                    if "driver_name" in chrono_success.columns
                    else pd.NA
                ),
            "chronology_time_utc":
                (
                    chrono_success[
                        chrono_time
                    ]
                    if chrono_time is not None
                    else pd.NA
                ),
            "chronology_track_c":
                numeric_series(
                    chrono_success,
                    chrono_track,
                ),
            "chronology_ambient_c":
                numeric_series(
                    chrono_success,
                    chrono_ambient,
                ),
            "chronology_humidity":
                numeric_series(
                    chrono_success,
                    chrono_humidity,
                ),
        }
    )

    overlap = perf_extract.merge(
        chrono_extract,
        on="_attempt_id_norm",
        how="inner",
    )

    if not overlap.empty:

        overlap[
            "track_c_difference_performance_minus_chronology"
        ] = (
            overlap[
                "performance_track_c"
            ]
            - overlap[
                "chronology_track_c"
            ]
        )

        overlap[
            "ambient_c_difference_performance_minus_chronology"
        ] = (
            overlap[
                "performance_ambient_c"
            ]
            - overlap[
                "chronology_ambient_c"
            ]
        )

        overlap[
            "humidity_difference_performance_minus_chronology"
        ] = (
            overlap[
                "performance_humidity"
            ]
            - overlap[
                "chronology_humidity"
            ]
        )

    else:

        overlap[
            "track_c_difference_performance_minus_chronology"
        ] = pd.Series(
            dtype=float
        )

        overlap[
            "ambient_c_difference_performance_minus_chronology"
        ] = pd.Series(
            dtype=float
        )

        overlap[
            "humidity_difference_performance_minus_chronology"
        ] = pd.Series(
            dtype=float
        )

    # --------------------------------------------------------
    # Unique combined 2024 attempt coverage
    # --------------------------------------------------------

    perf_ids = set(
        perf_success[
            "_attempt_id_norm"
        ].dropna()
    )

    chrono_ids = set(
        chrono_success[
            "_attempt_id_norm"
        ].dropna()
    )

    overlap_ids = (
        perf_ids
        & chrono_ids
    )

    combined_2024_ids = (
        perf_ids
        | chrono_ids
    )

    # --------------------------------------------------------
    # Coverage table
    # --------------------------------------------------------

    coverage_rows = []

    for year in range(
        2020,
        2025,
    ):

        canonical = canonical_counts[
            year
        ]

        performance = performance_counts[
            year
        ]

        chronology = (
            chronology_2024_count
            if year == 2024
            else 0
        )

        overlap_n = (
            len(overlap_ids)
            if year == 2024
            else 0
        )

        if year == 2024:
            combined_unique = len(
                combined_2024_ids
            )
        else:
            combined_unique = performance

        coverage_pct = (
            combined_unique
            / canonical
            * 100.0
            if canonical
            else math.nan
        )

        if year == 2022:

            note = (
                "PTSC observations available, but no "
                "trustworthy attempt absolute-time bridge; "
                "realized attempt-level environment not joined."
            )

        elif year == 2024:

            note = (
                "Performance-grade supported subset plus "
                "separate chronology-derived constrained "
                "environment; overlap audited by attempt_id."
            )

        else:

            note = (
                "Performance-grade recorder-capture timing "
                "aligned to PTSC within supported subset."
            )

        coverage_rows.append(
            {
                "year":
                    year,
                "canonical_attempts":
                    canonical,
                "performance_grade_environment_rows":
                    performance,
                "chronology_derived_environment_rows":
                    chronology,
                "cross_layer_overlap_attempts":
                    overlap_n,
                "combined_unique_environment_attempts":
                    combined_unique,
                "combined_unique_coverage_pct":
                    coverage_pct,
                "realized_environment_status":
                    YEAR_STATUS[
                        year
                    ],
                "note":
                    note,
            }
        )

    coverage = pd.DataFrame(
        coverage_rows
    )

    # --------------------------------------------------------
    # Global totals
    # --------------------------------------------------------

    performance_total = sum(
        performance_counts.values()
    )

    combined_total = int(
        coverage[
            "combined_unique_environment_attempts"
        ].sum()
    )

    canonical_total = int(
        coverage[
            "canonical_attempts"
        ].sum()
    )

    combined_total_pct = (
        combined_total
        / canonical_total
        * 100.0
        if canonical_total
        else math.nan
    )

    # --------------------------------------------------------
    # Diagnostics
    # --------------------------------------------------------

    print()
    print("COVERAGE BY YEAR")
    print("-" * 100)

    print(
        coverage[
            [
                "year",
                "canonical_attempts",
                "performance_grade_environment_rows",
                "chronology_derived_environment_rows",
                "cross_layer_overlap_attempts",
                "combined_unique_environment_attempts",
                "combined_unique_coverage_pct",
                "realized_environment_status",
            ]
        ].to_string(
            index=False
        )
    )

    print()
    print("GLOBAL")
    print("-" * 70)

    print(
        "Performance-grade aligned rows:",
        performance_total,
    )

    print(
        "Combined unique realized-environment attempts:",
        combined_total,
    )

    print(
        "Canonical attempts across 2020-2024:",
        canonical_total,
    )

    print(
        "Combined unique coverage:",
        f"{combined_total_pct:.3f}%",
    )

    print()
    print("2024 CROSS-LAYER OVERLAP")
    print("-" * 100)

    print(
        "2024 performance-grade successful attempts:",
        len(
            perf_ids
        ),
    )

    print(
        "2024 chronology-derived successful attempts:",
        len(
            chrono_ids
        ),
    )

    print(
        "Overlapping attempt_ids:",
        len(
            overlap_ids
        ),
    )

    print(
        "Combined unique 2024 attempts:",
        len(
            combined_2024_ids
        ),
    )

    if overlap.empty:

        print()
        print(
            "No successful attempt_id overlap."
        )

    else:

        display_cols = [
            "attempt_id",
            "car_number_performance",
            "driver_name_performance",
            "performance_time_utc",
            "chronology_time_utc",
            "performance_track_c",
            "chronology_track_c",
            "track_c_difference_performance_minus_chronology",
            "performance_ambient_c",
            "chronology_ambient_c",
            "ambient_c_difference_performance_minus_chronology",
            "performance_humidity",
            "chronology_humidity",
            "humidity_difference_performance_minus_chronology",
        ]

        print()
        print(
            overlap[
                display_cols
            ].to_string(
                index=False
            )
        )

        print()
        print("OVERLAP DIFFERENCE SUMMARY")
        print("-" * 70)

        print(
            "Track C MAE:",
            safe_mae(
                overlap[
                    "track_c_difference_performance_minus_chronology"
                ]
            ),
        )

        print(
            "Track C max abs difference:",
            safe_max_abs(
                overlap[
                    "track_c_difference_performance_minus_chronology"
                ]
            ),
        )

        print(
            "Ambient C MAE:",
            safe_mae(
                overlap[
                    "ambient_c_difference_performance_minus_chronology"
                ]
            ),
        )

        print(
            "Humidity MAE:",
            safe_mae(
                overlap[
                    "humidity_difference_performance_minus_chronology"
                ]
            ),
        )

    # --------------------------------------------------------
    # Freeze criteria
    # --------------------------------------------------------

    freeze_checks = {
        "legacy_2020_matches_expected_46":
            performance_counts[
                2020
            ] == 46,

        "legacy_2021_matches_expected_53":
            performance_counts[
                2021
            ] == 53,

        "2022_has_zero_attempt_environment_rows":
            performance_counts[
                2022
            ] == 0,

        "legacy_2023_matches_expected_28":
            performance_counts[
                2023
            ] == 28,

        "2024_supported_performance_matches_expected_7":
            performance_counts[
                2024
            ] == 7,

        "2024_chronology_has_successful_environment":
            chronology_2024_count > 0,
    }

    print()
    print("FREEZE CHECKS")
    print("-" * 70)

    all_pass = True

    for name, passed in (
        freeze_checks.items()
    ):

        status = (
            "PASS"
            if passed
            else "FAIL"
        )

        print(
            f"{status:4}  {name}"
        )

        if not passed:
            all_pass = False

    # --------------------------------------------------------
    # Write outputs
    # --------------------------------------------------------

    COVERAGE_OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    coverage.to_csv(
        COVERAGE_OUTPUT,
        index=False,
        encoding="utf-8-sig",
    )

    overlap.to_csv(
        OVERLAP_OUTPUT,
        index=False,
        encoding="utf-8-sig",
    )

    report_lines = []

    report_lines.append(
        "# Final Realized-Environment Coverage Audit"
    )

    report_lines.append("")

    report_lines.append(
        "## Scope"
    )

    report_lines.append("")

    report_lines.append(
        "This audit consolidates coverage status only. "
        "It does not manufacture new attempt timestamps, "
        "modify canonical chronology, or overwrite any "
        "existing realized-environment alignment."
    )

    report_lines.append("")

    report_lines.append(
        "## Frozen semantic policy"
    )

    report_lines.append("")

    report_lines.append(
        "- Performance-grade Timing71 recorder captures are "
        "approximate environment-alignment timestamps only."
    )

    report_lines.append(
        "- Recorder captures are not exact timed-run starts."
    )

    report_lines.append(
        "- 2024 chronology-derived constrained alignments remain "
        "a separate, stronger-provenance layer."
    )

    report_lines.append(
        "- 2022 remains unavailable for attempt-level realized "
        "environment because no trustworthy absolute-time bridge "
        "was found."
    )

    report_lines.append(
        "- No new chronology salvage is performed by this audit."
    )

    report_lines.append("")

    report_lines.append(
        "## Coverage"
    )

    report_lines.append("")

    markdown_columns = [
        "year",
        "canonical_attempts",
        "performance_grade_environment_rows",
        "chronology_derived_environment_rows",
        "cross_layer_overlap_attempts",
        "combined_unique_environment_attempts",
        "combined_unique_coverage_pct",
        "realized_environment_status",
    ]

    report_lines.append(
        "| " + " | ".join(markdown_columns) + " |"
    )

    report_lines.append(
        "| " + " | ".join(["---"] * len(markdown_columns)) + " |"
    )

    for _, markdown_row in coverage[markdown_columns].iterrows():

        values = []

        for column in markdown_columns:

            value = markdown_row[column]

            if column == "combined_unique_coverage_pct":
                try:
                    value = f"{float(value):.3f}"
                except Exception:
                    value = str(value)

            values.append(
                str(value).replace("|", "\\|")
            )

        report_lines.append(
            "| " + " | ".join(values) + " |"
        )

    report_lines.append("")

    report_lines.append(
        "## Global totals"
    )

    report_lines.append("")

    report_lines.append(
        f"- Performance-grade aligned rows: "
        f"{performance_total}"
    )

    report_lines.append(
        f"- Combined unique realized-environment attempts: "
        f"{combined_total}"
    )

    report_lines.append(
        f"- Canonical attempts across 2020-2024: "
        f"{canonical_total}"
    )

    report_lines.append(
        f"- Combined unique coverage: "
        f"{combined_total_pct:.3f}%"
    )

    report_lines.append("")

    report_lines.append(
        "## 2024 cross-layer audit"
    )

    report_lines.append("")

    report_lines.append(
        f"- Performance-grade successful attempts: "
        f"{len(perf_ids)}"
    )

    report_lines.append(
        f"- Chronology-derived successful attempts: "
        f"{len(chrono_ids)}"
    )

    report_lines.append(
        f"- Overlapping attempt IDs: "
        f"{len(overlap_ids)}"
    )

    report_lines.append(
        f"- Combined unique 2024 attempts: "
        f"{len(combined_2024_ids)}"
    )

    if not overlap.empty:

        report_lines.append("")

        report_lines.append(
            "### Overlap differences"
        )

        report_lines.append("")

        report_lines.append(
            f"- Track temperature MAE: "
            f"{safe_mae(overlap['track_c_difference_performance_minus_chronology'])}"
        )

        report_lines.append(
            f"- Track temperature max absolute difference: "
            f"{safe_max_abs(overlap['track_c_difference_performance_minus_chronology'])}"
        )

        report_lines.append(
            f"- Ambient temperature MAE: "
            f"{safe_mae(overlap['ambient_c_difference_performance_minus_chronology'])}"
        )

        report_lines.append(
            f"- Humidity MAE: "
            f"{safe_mae(overlap['humidity_difference_performance_minus_chronology'])}"
        )

    report_lines.append("")

    report_lines.append(
        "## Freeze checks"
    )

    report_lines.append("")

    for name, passed in (
        freeze_checks.items()
    ):

        report_lines.append(
            f"- {'PASS' if passed else 'FAIL'} — {name}"
        )

    report_lines.append("")

    report_lines.append(
        "## Final audit status"
    )

    report_lines.append("")

    if all_pass:

        report_lines.append(
            "**REALIZED_ENVIRONMENT_LAYER_READY_TO_FREEZE**"
        )

        report_lines.append("")

        report_lines.append(
            "The supported historical realized-environment "
            "layer is ready to freeze. The next phase may move "
            "to forecast/decision-state weather alignment "
            "without further timing salvage."
        )

    else:

        report_lines.append(
            "**REVIEW_REQUIRED_BEFORE_FREEZE**"
        )

        report_lines.append("")

        report_lines.append(
            "At least one expected coverage invariant failed. "
            "Review the audit output before freezing."
        )

    REPORT_OUTPUT.write_text(
        "\n".join(
            report_lines
        ),
        encoding="utf-8",
    )

    print()
    print("=" * 100)

    if all_pass:

        print(
            "FINAL STATUS: "
            "REALIZED_ENVIRONMENT_LAYER_READY_TO_FREEZE"
        )

    else:

        print(
            "FINAL STATUS: "
            "REVIEW_REQUIRED_BEFORE_FREEZE"
        )

    print("=" * 100)

    print()
    print("OUTPUTS")

    print(
        COVERAGE_OUTPUT
    )

    print(
        OVERLAP_OUTPUT
    )

    print(
        REPORT_OUTPUT
    )


if __name__ == "__main__":
    main()
