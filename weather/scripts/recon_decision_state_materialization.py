from pathlib import Path
import pandas as pd
import numpy as np


ATTEMPTS_FILE = Path(
    "data/canonical/v1/attempts.csv"
)

CHRONOLOGY_EVENTS_FILE = Path(
    "data/canonical/v1/chronology_events.csv"
)

QUALIFYING_EVENTS_FILE = Path(
    "data/canonical/v1/qualifying_events.csv"
)

PERF_2020_2023_FILE = Path(
    "weather/output/performance_grade_attempt_timing.csv"
)

PERF_2024_FILE = Path(
    "weather/output/performance_grade_attempt_timing_2024_supported.csv"
)

FORECAST_ALIGNMENT_FILE = Path(
    "weather/output/performance_grade_hrrr_forecast_alignment.csv"
)

DECISION_STATE_FILE = Path(
    "data/canonical/v1/decision_state_features.csv"
)


def read_required(path):
    if not path.exists():
        raise FileNotFoundError(
            f"Missing required file: {path}"
        )

    return pd.read_csv(
        path,
        low_memory=False,
    )


def read_optional(path):
    if not path.exists():
        return None

    return pd.read_csv(
        path,
        low_memory=False,
    )


def parse_utc(series):
    return pd.to_datetime(
        series,
        utc=True,
        errors="coerce",
    )


def print_columns(
    title,
    df,
):
    print()
    print("=" * 100)
    print(title)
    print("=" * 100)

    if df is None:
        print("FILE NOT FOUND")
        return

    print(
        "Rows:",
        len(df)
    )

    print()
    print("Columns:")

    for col in df.columns:
        print(
            f"  {col}"
        )


def main():

    attempts = read_required(
        ATTEMPTS_FILE
    )

    chronology = read_required(
        CHRONOLOGY_EVENTS_FILE
    )

    qualifying_events = read_optional(
        QUALIFYING_EVENTS_FILE
    )

    perf_old = read_required(
        PERF_2020_2023_FILE
    )

    perf_2024 = read_required(
        PERF_2024_FILE
    )

    forecast = read_required(
        FORECAST_ALIGNMENT_FILE
    )

    decision_state = read_required(
        DECISION_STATE_FILE
    )

    print()
    print("=" * 100)
    print(
        "PHASE 5A-0 — DECISION-STATE "
        "MATERIALIZATION RECONNAISSANCE"
    )
    print("=" * 100)

    # ========================================================
    # Basic schemas
    # ========================================================

    print_columns(
        "ATTEMPTS",
        attempts,
    )

    print_columns(
        "CHRONOLOGY EVENTS",
        chronology,
    )

    print_columns(
        "QUALIFYING EVENTS",
        qualifying_events,
    )

    print_columns(
        "EXISTING DECISION STATE SCHEMA",
        decision_state,
    )

    # ========================================================
    # Session boundaries
    # ========================================================

    print()
    print("=" * 100)
    print("SESSION BOUNDARY EVIDENCE")
    print("=" * 100)

    if "event_type" in chronology.columns:

        boundaries = chronology[
            chronology[
                "event_type"
            ].astype(str)
            == "SESSION_BOUNDARY"
        ].copy()

        print(
            "Chronology SESSION_BOUNDARY rows:",
            len(boundaries)
        )

        if not boundaries.empty:

            boundary_cols = [
                c
                for c in [
                    "session_id",
                    "chronology_event_id",
                    "event_type",
                    "event_time_utc",
                    "event_time_lower_utc",
                    "event_time_upper_utc",
                    "event_time_quality",
                    "time_basis",
                    "event_payload_json",
                    "notes",
                ]
                if c in boundaries.columns
            ]

            print()
            print(
                boundaries[
                    boundary_cols
                ].to_string(
                    index=False
                )
            )

    else:
        print(
            "No event_type column in chronology_events."
        )

    if qualifying_events is not None:

        print()
        print(
            "QUALIFYING EVENT TIME-LIKE FIELDS"
        )
        print("-" * 70)

        time_cols = [
            c
            for c in qualifying_events.columns
            if any(
                token in c.lower()
                for token in [
                    "time",
                    "start",
                    "end",
                    "date",
                    "session",
                ]
            )
        ]

        for col in time_cols:

            nonnull = (
                qualifying_events[
                    col
                ]
                .notna()
                .sum()
            )

            print(
                f"{col}: "
                f"{nonnull}/{len(qualifying_events)}"
            )

    # ========================================================
    # Performance timing combined
    # ========================================================

    perf_old = perf_old.copy()
    perf_2024 = perf_2024.copy()

    perf_old[
        "_source_layer"
    ] = (
        "PERFORMANCE_GRADE_2020_2021_2023"
    )

    perf_2024[
        "_source_layer"
    ] = (
        "PERFORMANCE_GRADE_2024_SUPPORTED"
    )

    timing = pd.concat(
        [
            perf_old,
            perf_2024,
        ],
        ignore_index=True,
        sort=False,
    )

    timing[
        "_performance_time"
    ] = parse_utc(
        timing[
            "mapped_capture_time_utc"
        ]
    )

    print()
    print("=" * 100)
    print("PERFORMANCE TIMING ORDERABILITY")
    print("=" * 100)

    print(
        "Combined timing rows:",
        len(timing)
    )

    print(
        "Unique attempt IDs:",
        timing[
            "attempt_id"
        ].nunique()
    )

    print(
        "Non-null performance times:",
        timing[
            "_performance_time"
        ].notna().sum()
    )

    duplicate_times = (
        timing
        .duplicated(
            subset=[
                "session_id",
                "mapped_capture_time_utc",
            ],
            keep=False,
        )
    )

    print(
        "Rows sharing exact timestamp within session:",
        int(
            duplicate_times.sum()
        )
    )

    print()
    print("ROWS BY SESSION")
    print("-" * 70)

    print(
        timing[
            "session_id"
        ]
        .value_counts()
        .sort_index()
        .to_string()
    )

    print()
    print("TIME RANGE BY SESSION")
    print("-" * 100)

    timing_ranges = (
        timing
        .groupby(
            "session_id",
            dropna=False,
        )
        .agg(
            rows=(
                "attempt_id",
                "size",
            ),
            first_time=(
                "_performance_time",
                "min",
            ),
            last_time=(
                "_performance_time",
                "max",
            ),
        )
        .reset_index()
    )

    print(
        timing_ranges.to_string(
            index=False
        )
    )

    # ========================================================
    # Join attempts
    # ========================================================

    attempt_keep = [
        c
        for c in [
            "attempt_id",
            "session_id",
            "entry_key",
            "attempt_key",
            "car_number",
            "driver_name",
            "car_attempt_index",
            "car_attempt_order_quality",
            "attempt_class",
            "result_status",
            "result_counted_at_session_end",
            "four_lap_total_seconds",
            "four_lap_average_speed_mph",
            "start_time_utc",
            "event_time_quality",
            "time_basis",
        ]
        if c in attempts.columns
    ]

    joined = timing.merge(
        attempts[
            attempt_keep
        ],
        on="attempt_id",
        how="left",
        suffixes=(
            "_timing",
            "_attempt",
        ),
        validate="one_to_one",
    )

    attempt_match_rows = (
        joined[
            "session_id_attempt"
        ].notna().sum()
        if "session_id_attempt" in joined.columns
        else len(joined)
    )

    print()
    print("=" * 100)
    print("ATTEMPT ATTRIBUTE SUPPORT")
    print("=" * 100)

    print(
        "Timing rows matched to attempts:",
        f"{attempt_match_rows}/{len(joined)}"
    )

    candidate_fields = [
        "car_attempt_index_attempt",
        "car_attempt_order_quality",
        "attempt_class",
        "result_status",
        "result_counted_at_session_end",
        "four_lap_total_seconds",
        "four_lap_average_speed_mph",
    ]

    for col in candidate_fields:

        if col in joined.columns:

            print(
                f"{col}: "
                f"{joined[col].notna().sum()}/"
                f"{len(joined)}"
            )

    # ========================================================
    # Result-status semantics
    # ========================================================

    print()
    print("=" * 100)
    print("RESULT STATUS DISTRIBUTION")
    print("=" * 100)

    if "result_status" in joined.columns:

        print(
            joined[
                "result_status"
            ]
            .value_counts(
                dropna=False
            )
            .to_string()
        )

    print()
    print(
        "RESULT COUNTED AT SESSION END"
    )
    print("-" * 70)

    if (
        "result_counted_at_session_end"
        in joined.columns
    ):

        print(
            joined[
                "result_counted_at_session_end"
            ]
            .value_counts(
                dropna=False
            )
            .to_string()
        )

    # ========================================================
    # Repeated-attempt structure
    # ========================================================

    print()
    print("=" * 100)
    print("REPEATED-ATTEMPT STRUCTURE")
    print("=" * 100)

    car_col = (
        "car_number_timing"
        if "car_number_timing" in joined.columns
        else "car_number"
    )

    session_col = (
        "session_id_timing"
        if "session_id_timing" in joined.columns
        else "session_id"
    )

    repeated = (
        joined
        .groupby(
            [
                session_col,
                car_col,
            ],
            dropna=False,
        )
        .size()
        .reset_index(
            name="supported_attempt_count"
        )
    )

    print(
        "Supported car/session groups:",
        len(repeated)
    )

    print(
        "Groups with >1 supported attempt:",
        int(
            (
                repeated[
                    "supported_attempt_count"
                ]
                > 1
            ).sum()
        )
    )

    print(
        "Rows belonging to repeated supported groups:",
        int(
            repeated.loc[
                repeated[
                    "supported_attempt_count"
                ]
                > 1,
                "supported_attempt_count",
            ].sum()
        )
    )

    print()
    print(
        "SUPPORTED ATTEMPT COUNT DISTRIBUTION"
    )
    print("-" * 70)

    print(
        repeated[
            "supported_attempt_count"
        ]
        .value_counts()
        .sort_index()
        .to_string()
    )

    # ========================================================
    # Chronological repeated-attempt examples
    # ========================================================

    repeated_keys = repeated[
        repeated[
            "supported_attempt_count"
        ]
        > 1
    ][
        [
            session_col,
            car_col,
        ]
    ]

    repeated_rows = joined.merge(
        repeated_keys,
        on=[
            session_col,
            car_col,
        ],
        how="inner",
    )

    repeated_rows = repeated_rows.sort_values(
        [
            session_col,
            car_col,
            "_performance_time",
        ]
    )

    print()
    print(
        "REPEATED-ATTEMPT CHRONOLOGICAL SAMPLE"
    )
    print("-" * 120)

    display_cols = [
        c
        for c in [
            session_col,
            car_col,
            "driver_name_timing",
            "driver_name",
            "car_attempt_index_timing",
            "car_attempt_index_attempt",
            "mapped_capture_time_utc",
            "result_status",
            "result_counted_at_session_end",
            "four_lap_average_speed_mph",
            "four_lap_total_seconds",
        ]
        if c in repeated_rows.columns
    ]

    print(
        repeated_rows[
            display_cols
        ]
        .head(60)
        .to_string(
            index=False
        )
    )

    # ========================================================
    # Forecast join integrity
    # ========================================================

    print()
    print("=" * 100)
    print("FORECAST ALIGNMENT LINK")
    print("=" * 100)

    print(
        "Forecast alignment rows:",
        len(forecast)
    )

    forecast_ids = set(
        forecast[
            "attempt_id"
        ].astype(str)
    )

    timing_ids = set(
        timing[
            "attempt_id"
        ].astype(str)
    )

    print(
        "Timing attempt IDs missing forecast alignment:",
        len(
            timing_ids
            - forecast_ids
        )
    )

    print(
        "Forecast alignment IDs missing timing:",
        len(
            forecast_ids
            - timing_ids
        )
    )

    # ========================================================
    # Leaderboard reconstruction feasibility
    # ========================================================

    print()
    print("=" * 100)
    print("LEADERBOARD RECONSTRUCTION FEASIBILITY")
    print("=" * 100)

    complete_speed = pd.to_numeric(
        joined.get(
            "four_lap_average_speed_mph",
            pd.Series(
                index=joined.index,
                dtype=float,
            ),
        ),
        errors="coerce",
    )

    print(
        "Supported timing rows with complete "
        "four-lap average speed:",
        int(
            complete_speed.notna().sum()
        ),
        "/",
        len(joined),
    )

    print()
    print(
        "IMPORTANT LIMITATION"
    )
    print("-" * 70)

    print(
        "Supported performance timing is incomplete "
        "relative to the full 329-attempt canonical table."
    )

    print(
        "Therefore provisional rank / Top-12 cutoff / "
        "bump cutoff CANNOT automatically be reconstructed "
        "from only these 136 supported timing rows without "
        "proving complete leaderboard state coverage."
    )

    print(
        "Canonical row position/source locator MUST NOT be "
        "used as chronology."
    )

    # ========================================================
    # Existing decision-state schema readiness
    # ========================================================

    print()
    print("=" * 100)
    print("DECISION-STATE SCHEMA READINESS")
    print("=" * 100)

    print(
        "Existing decision_state_features rows:",
        len(decision_state)
    )

    schema_fields = [
        "decision_state_id",
        "session_id",
        "subject_entry_key",
        "subject_attempt_id",
        "state_as_of_time_utc",
        "state_order_boundary",
        "current_best_average_speed_mph",
        "current_best_total_seconds",
        "provisional_rank_before",
        "top12_cutoff_speed_mph",
        "bump_cutoff_speed_mph",
        "margin_to_top12_mph",
        "margin_to_bump_cutoff_mph",
        "session_elapsed_seconds",
        "session_remaining_seconds",
        "prior_observed_attempt_count",
        "most_recent_attempt_time_utc",
        "seconds_since_prior_attempt",
        "forecast_snapshot_id",
        "leaderboard_state_complete",
        "chronology_complete_through_state",
        "queue_state_qualitative",
        "queue_state_evidence",
        "derivation_rule_version",
        "input_lineage_hash",
    ]

    missing_schema = [
        c
        for c in schema_fields
        if c not in decision_state.columns
    ]

    print(
        "Expected schema fields missing:",
        len(missing_schema)
    )

    if missing_schema:
        for col in missing_schema:
            print(
                "  MISSING:",
                col
            )

    # ========================================================
    # Final classification
    # ========================================================

    print()
    print("=" * 100)
    print("MATERIALIZATION CLASSIFICATION")
    print("=" * 100)

    print(
        "SAFE NOW:"
    )

    print(
        "  - performance timestamp"
    )

    print(
        "  - subject attempt / car / driver"
    )

    print(
        "  - attempt performance"
    )

    print(
        "  - prior supported same-car attempt timing"
    )

    print(
        "  - seconds since prior supported same-car attempt"
    )

    print(
        "  - leakage-safe HRRR forecast features"
    )

    print()
    print(
        "NOT YET SAFE WITHOUT ADDITIONAL EVIDENCE:"
    )

    print(
        "  - full provisional leaderboard rank"
    )

    print(
        "  - Top-12 cutoff"
    )

    print(
        "  - bump cutoff"
    )

    print(
        "  - session remaining time unless session "
        "boundaries are proven per year"
    )

    print(
        "  - queue state"
    )

    print(
        "  - treating recorder capture as exact "
        "retain/withdraw decision time"
    )

    print()
    print("=" * 100)
    print(
        "FINAL STATUS: DECISION_STATE_RECON_READY"
    )
    print("=" * 100)

    print()
    print(
        "NO DECISION STATE ROWS WERE WRITTEN."
    )


if __name__ == "__main__":
    main()
