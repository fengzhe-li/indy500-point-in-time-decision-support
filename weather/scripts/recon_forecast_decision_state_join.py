from pathlib import Path
import pandas as pd


FORECAST_SNAPSHOTS = Path(
    "data/canonical/v1/forecast_snapshots.csv"
)

WEATHER_FORECASTS = Path(
    "data/canonical/v1/weather_forecasts.csv"
)

ATTEMPTS = Path(
    "data/canonical/v1/attempts.csv"
)

PERF_TIMING_2020_2023 = Path(
    "weather/output/performance_grade_attempt_timing.csv"
)

PERF_TIMING_2024 = Path(
    "weather/output/performance_grade_attempt_timing_2024_supported.csv"
)

DECISION_STATE_CANDIDATES = [
    Path("data/derived/v1/decision_state_features.csv"),
    Path("data/canonical/v1/decision_state_features.csv"),
    Path("data/decision_state_features.csv"),
]


def read_required(path):
    if not path.exists():
        raise FileNotFoundError(
            f"Missing required file: {path}"
        )

    return pd.read_csv(
        path,
        low_memory=False,
    )


def print_columns(title, df):
    print()
    print("=" * 100)
    print(title)
    print("=" * 100)

    print(f"Rows: {len(df)}")

    print()
    print("Columns:")

    for col in df.columns:
        print(f"  {col}")


def print_nonnull(df, columns):
    print()
    print("NON-NULL COUNTS")
    print("-" * 70)

    for col in columns:
        if col in df.columns:
            print(
                f"{col}: "
                f"{df[col].notna().sum()}/{len(df)}"
            )


def candidate_time_columns(df):
    keys = [
        "time",
        "date",
        "cycle",
        "valid",
        "forecast",
        "issue",
        "release",
        "publish",
        "avail",
        "lead",
    ]

    return [
        c
        for c in df.columns
        if any(
            key in c.lower()
            for key in keys
        )
    ]


def main():

    snapshots = read_required(
        FORECAST_SNAPSHOTS
    )

    weather = read_required(
        WEATHER_FORECASTS
    )

    attempts = read_required(
        ATTEMPTS
    )

    perf_old = read_required(
        PERF_TIMING_2020_2023
    )

    perf_2024 = read_required(
        PERF_TIMING_2024
    )

    print()
    print("=" * 100)
    print(
        "PHASE 4C-0 — FORECAST / DECISION-STATE "
        "JOIN RECONNAISSANCE"
    )
    print("=" * 100)

    # --------------------------------------------------------
    # Forecast snapshots
    # --------------------------------------------------------

    print_columns(
        "FORECAST SNAPSHOTS",
        snapshots,
    )

    snapshot_time_cols = candidate_time_columns(
        snapshots
    )

    print_nonnull(
        snapshots,
        snapshot_time_cols,
    )

    print()
    print("SAMPLE FORECAST SNAPSHOTS")
    print("-" * 70)

    sample_cols = [
        c
        for c in [
            "forecast_snapshot_id",
            "source_id",
            "year",
            "forecast_cycle_time_utc",
            "cycle_time_utc",
            "forecast_valid_time_utc",
            "valid_time_utc",
            "forecast_lead_hours",
            "availability_time_utc",
            "availability_status",
            "availability_basis",
        ]
        if c in snapshots.columns
    ]

    if sample_cols:
        print(
            snapshots[
                sample_cols
            ]
            .head(20)
            .to_string(
                index=False
            )
        )
    else:
        print(
            snapshots
            .head(10)
            .to_string(
                index=False
            )
        )

    # --------------------------------------------------------
    # Weather forecast values
    # --------------------------------------------------------

    print_columns(
        "WEATHER FORECAST VALUES",
        weather,
    )

    weather_time_cols = candidate_time_columns(
        weather
    )

    print_nonnull(
        weather,
        weather_time_cols,
    )

    print()
    print("SNAPSHOT LINKAGE CANDIDATES")
    print("-" * 70)

    for col in weather.columns:
        if (
            "snapshot" in col.lower()
            or "forecast" in col.lower()
        ):
            print(
                f"{col}: "
                f"{weather[col].notna().sum()}/{len(weather)}"
            )

    # --------------------------------------------------------
    # Availability fields
    # --------------------------------------------------------

    print()
    print("=" * 100)
    print("FORECAST AVAILABILITY SEMANTICS")
    print("=" * 100)

    availability_cols = [
        c
        for c in snapshots.columns
        if any(
            key in c.lower()
            for key in [
                "avail",
                "publish",
                "release",
                "issue",
            ]
        )
    ]

    if not availability_cols:
        print(
            "No availability/publication/release columns found."
        )
    else:
        for col in availability_cols:

            print()
            print(col)
            print("-" * 50)

            print(
                snapshots[col]
                .value_counts(
                    dropna=False
                )
                .head(30)
                .to_string()
            )

    # --------------------------------------------------------
    # Performance timing
    # --------------------------------------------------------

    print_columns(
        "PERFORMANCE TIMING 2020/2021/2023",
        perf_old,
    )

    print_columns(
        "PERFORMANCE TIMING 2024 SUPPORTED",
        perf_2024,
    )

    timing_frames = []

    old = perf_old.copy()
    old["_source_layer"] = (
        "PERFORMANCE_GRADE_2020_2021_2023"
    )

    new = perf_2024.copy()
    new["_source_layer"] = (
        "PERFORMANCE_GRADE_2024_SUPPORTED"
    )

    timing_frames.append(
        old
    )

    timing_frames.append(
        new
    )

    timing = pd.concat(
        timing_frames,
        ignore_index=True,
        sort=False,
    )

    print()
    print("=" * 100)
    print("COMBINED PERFORMANCE DECISION-TIME CANDIDATES")
    print("=" * 100)

    print(
        "Rows:",
        len(timing)
    )

    time_candidates = [
        c
        for c in timing.columns
        if any(
            key in c.lower()
            for key in [
                "time",
                "capture",
            ]
        )
    ]

    print_nonnull(
        timing,
        time_candidates,
    )

    print()
    print("ROWS BY SESSION")
    print("-" * 70)

    if "session_id" in timing.columns:
        print(
            timing[
                "session_id"
            ]
            .value_counts()
            .sort_index()
            .to_string()
        )

    # --------------------------------------------------------
    # Canonical attempts
    # --------------------------------------------------------

    print()
    print("=" * 100)
    print("CANONICAL ATTEMPT TIME FIELDS")
    print("=" * 100)

    attempt_time_cols = candidate_time_columns(
        attempts
    )

    print_nonnull(
        attempts,
        attempt_time_cols,
    )

    # --------------------------------------------------------
    # Existing decision-state features
    # --------------------------------------------------------

    print()
    print("=" * 100)
    print("DECISION STATE FEATURES")
    print("=" * 100)

    found_decision_state = False

    for path in DECISION_STATE_CANDIDATES:

        if path.exists():

            found_decision_state = True

            ds = pd.read_csv(
                path,
                low_memory=False,
            )

            print()
            print(
                f"FOUND: {path}"
            )

            print(
                f"Rows: {len(ds)}"
            )

            print(
                "Columns:"
            )

            for col in ds.columns:
                print(
                    f"  {col}"
                )

    if not found_decision_state:
        print(
            "No decision_state_features.csv found "
            "in expected locations."
        )

    # --------------------------------------------------------
    # Join-key feasibility
    # --------------------------------------------------------

    print()
    print("=" * 100)
    print("JOIN-KEY FEASIBILITY")
    print("=" * 100)

    snapshot_ids = [
        c
        for c in snapshots.columns
        if "snapshot" in c.lower()
        and "id" in c.lower()
    ]

    weather_snapshot_ids = [
        c
        for c in weather.columns
        if "snapshot" in c.lower()
        and "id" in c.lower()
    ]

    print(
        "Snapshot ID columns in forecast_snapshots:",
        snapshot_ids,
    )

    print(
        "Snapshot ID columns in weather_forecasts:",
        weather_snapshot_ids,
    )

    common_cols = sorted(
        set(
            snapshots.columns
        )
        & set(
            weather.columns
        )
    )

    print()
    print(
        "Common columns between snapshot/value tables:"
    )

    for col in common_cols:
        print(
            f"  {col}"
        )

    # --------------------------------------------------------
    # Hard policy statement
    # --------------------------------------------------------

    print()
    print("=" * 100)
    print("CURRENT HARD POLICY")
    print("=" * 100)

    print(
        "1. forecast cycle time MUST NOT be treated "
        "as publication/availability time."
    )

    print(
        "2. A forecast may be joined to a decision only "
        "when availability <= decision time under an "
        "explicitly documented policy."
    )

    print(
        "3. This script performs NO forecast selection "
        "and writes NO outputs."
    )

    print(
        "4. Realized-environment layer remains frozen."
    )

    print()
    print("=" * 100)
    print("DONE")
    print("=" * 100)


if __name__ == "__main__":
    main()
