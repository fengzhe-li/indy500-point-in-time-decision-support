from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


# ============================================================
# PATHS
# ============================================================

INPUT_FILE = Path(
    "weather/evidence/ptsc/"
    "indy500_day1_track_temp_2020_2024_time_normalized.csv"
)

OUTPUT_DIR = Path(
    "weather/output/v2_future_track"
)

OUTPUT_FILE = (
    OUTPUT_DIR
    / "future_track_samples_v1.csv"
)

QA_FILE = (
    OUTPUT_DIR
    / "future_track_samples_v1_qa.txt"
)


# ============================================================
# CONFIG
# ============================================================

# Operational forecast horizons we want to evaluate
HORIZONS_MIN = [
    15,
    30,
    60,
    90,
    120,
]

# Future target may differ slightly from requested horizon
# because some terminal observations occur at :50 / :52.
FUTURE_TOLERANCE_MIN = 5.0

# Thermal trend should represent approximately the preceding
# 15 minutes rather than blindly using the immediately prior row.
THERMAL_RATE_TARGET_LOOKBACK_MIN = 15.0

# We accept a previous observation 10–20 minutes earlier.
THERMAL_RATE_MIN_LOOKBACK_MIN = 10.0
THERMAL_RATE_MAX_LOOKBACK_MIN = 20.0


# ============================================================
# LOAD DATA
# ============================================================

def load_data() -> pd.DataFrame:

    df = pd.read_csv(INPUT_FILE)

    required = [
        "year",
        "session_date",
        "local_datetime",
        "utc_datetime",
        "ambient_c",
        "track_c",
    ]

    missing = [
        col
        for col in required
        if col not in df.columns
    ]

    if missing:
        raise ValueError(
            f"Missing required columns: {missing}"
        )

    # UTC is used as canonical time for all calculations.
    df["utc_datetime"] = pd.to_datetime(
        df["utc_datetime"],
        utc=True,
    )

    # Keep local timestamp for human-readable QA only.
    df["local_datetime"] = pd.to_datetime(
        df["local_datetime"],
        utc=True,
    )

    df["session_id"] = (
        df["year"].astype(str)
        + "_"
        + df["session_date"].astype(str)
        + "_day1"
    )

    df = (
        df
        .sort_values(
            [
                "session_id",
                "utc_datetime",
            ]
        )
        .reset_index(drop=True)
    )

    return df


# ============================================================
# THERMAL RATE
# ============================================================

def find_thermal_rate(
    session_df: pd.DataFrame,
    current_idx: int,
) -> dict:

    current = session_df.iloc[current_idx]

    t0 = current["utc_datetime"]
    track0 = current["track_c"]

    earlier = session_df[
        session_df["utc_datetime"] < t0
    ].copy()

    if earlier.empty:
        return {
            "track_rate_c_per_min": np.nan,
            "rate_lookback_min": np.nan,
            "rate_source_time": pd.NaT,
            "rate_source_track_c": np.nan,
            "rate_valid": False,
        }

    earlier["lookback_min"] = (
        (
            t0
            - earlier["utc_datetime"]
        )
        .dt.total_seconds()
        / 60.0
    )

    candidates = earlier[
        (
            earlier["lookback_min"]
            >= THERMAL_RATE_MIN_LOOKBACK_MIN
        )
        &
        (
            earlier["lookback_min"]
            <= THERMAL_RATE_MAX_LOOKBACK_MIN
        )
    ].copy()

    if candidates.empty:
        return {
            "track_rate_c_per_min": np.nan,
            "rate_lookback_min": np.nan,
            "rate_source_time": pd.NaT,
            "rate_source_track_c": np.nan,
            "rate_valid": False,
        }

    candidates["distance_from_15"] = (
        candidates["lookback_min"]
        - THERMAL_RATE_TARGET_LOOKBACK_MIN
    ).abs()

    best = (
        candidates
        .sort_values(
            [
                "distance_from_15",
                "lookback_min",
            ]
        )
        .iloc[0]
    )

    dt_min = float(
        best["lookback_min"]
    )

    rate = (
        track0
        - best["track_c"]
    ) / dt_min

    return {
        "track_rate_c_per_min": rate,
        "rate_lookback_min": dt_min,
        "rate_source_time": best[
            "utc_datetime"
        ],
        "rate_source_track_c": best[
            "track_c"
        ],
        "rate_valid": True,
    }


# ============================================================
# FUTURE TARGET MATCHING
# ============================================================

def find_future_target(
    session_df: pd.DataFrame,
    current_idx: int,
    requested_horizon_min: float,
) -> dict | None:

    current = session_df.iloc[current_idx]

    t0 = current["utc_datetime"]

    future = session_df[
        session_df["utc_datetime"] > t0
    ].copy()

    if future.empty:
        return None

    future["actual_horizon_min"] = (
        (
            future["utc_datetime"]
            - t0
        )
        .dt.total_seconds()
        / 60.0
    )

    future["horizon_error_min"] = (
        future["actual_horizon_min"]
        - requested_horizon_min
    ).abs()

    candidates = future[
        future["horizon_error_min"]
        <= FUTURE_TOLERANCE_MIN
    ].copy()

    if candidates.empty:
        return None

    best = (
        candidates
        .sort_values(
            [
                "horizon_error_min",
                "actual_horizon_min",
            ]
        )
        .iloc[0]
    )

    return {
        "future_row": best,
        "actual_horizon_min": float(
            best["actual_horizon_min"]
        ),
        "horizon_error_min": float(
            best["horizon_error_min"]
        ),
    }


# ============================================================
# BUILD SAMPLES
# ============================================================

def build_samples(
    df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:

    samples = []
    attempted_matches = []

    for (
        session_id,
        session_df,
    ) in df.groupby(
        "session_id",
        sort=True,
    ):

        session_df = (
            session_df
            .sort_values(
                "utc_datetime"
            )
            .reset_index(drop=True)
        )

        for current_idx in range(
            len(session_df)
        ):

            current = session_df.iloc[
                current_idx
            ]

            thermal = find_thermal_rate(
                session_df,
                current_idx,
            )

            thermal_gap = (
                current["track_c"]
                - current["ambient_c"]
            )

            for requested_horizon in (
                HORIZONS_MIN
            ):

                match = find_future_target(
                    session_df,
                    current_idx,
                    requested_horizon,
                )

                attempted_matches.append(
                    {
                        "year": current["year"],
                        "session_id": session_id,
                        "t0": current[
                            "utc_datetime"
                        ],
                        "requested_horizon_min":
                            requested_horizon,
                        "matched":
                            match is not None,
                    }
                )

                if match is None:
                    continue

                future = match[
                    "future_row"
                ]

                actual_horizon = match[
                    "actual_horizon_min"
                ]

                delta_track = (
                    future["track_c"]
                    - current["track_c"]
                )

                delta_ambient = (
                    future["ambient_c"]
                    - current["ambient_c"]
                )

                row = {
                    # ----------------------------
                    # Identity
                    # ----------------------------

                    "pair_id": (
                        f"{session_id}_"
                        f"{current_idx:03d}_"
                        f"h{requested_horizon}"
                    ),

                    "year": int(
                        current["year"]
                    ),

                    "session_id":
                        session_id,

                    # ----------------------------
                    # Time
                    # ----------------------------

                    "t0_utc":
                        current[
                            "utc_datetime"
                        ],

                    "t0_local":
                        current[
                            "local_datetime"
                        ],

                    "future_utc":
                        future[
                            "utc_datetime"
                        ],

                    "future_local":
                        future[
                            "local_datetime"
                        ],

                    "requested_horizon_min":
                        requested_horizon,

                    "actual_horizon_min":
                        actual_horizon,

                    "horizon_error_min":
                        match[
                            "horizon_error_min"
                        ],

                    # ----------------------------
                    # Current state
                    # ----------------------------

                    "track_temp_0_c":
                        current[
                            "track_c"
                        ],

                    "ambient_temp_0_c":
                        current[
                            "ambient_c"
                        ],

                    "thermal_gap_0_c":
                        thermal_gap,

                    # ----------------------------
                    # Current thermal trend
                    # ----------------------------

                    "track_rate_0_c_per_min":
                        thermal[
                            "track_rate_c_per_min"
                        ],

                    "rate_lookback_min":
                        thermal[
                            "rate_lookback_min"
                        ],

                    "rate_source_utc":
                        thermal[
                            "rate_source_time"
                        ],

                    "rate_source_track_c":
                        thermal[
                            "rate_source_track_c"
                        ],

                    "rate_valid":
                        thermal[
                            "rate_valid"
                        ],

                    # ----------------------------
                    # Future observed state
                    # ----------------------------

                    "future_track_temp_c":
                        future[
                            "track_c"
                        ],

                    "future_ambient_temp_c":
                        future[
                            "ambient_c"
                        ],

                    # ----------------------------
                    # Prediction targets
                    # ----------------------------

                    "delta_track_temp_c":
                        delta_track,

                    "delta_ambient_temp_c":
                        delta_ambient,

                    # ----------------------------
                    # Source provenance
                    # ----------------------------

                    "source_row_0":
                        int(
                            current[
                                "source_row_index"
                            ]
                        ),

                    "source_row_future":
                        int(
                            future[
                                "source_row_index"
                            ]
                        ),
                }

                samples.append(row)

    samples_df = pd.DataFrame(
        samples
    )

    attempts_df = pd.DataFrame(
        attempted_matches
    )

    return (
        samples_df,
        attempts_df,
    )


# ============================================================
# QA
# ============================================================

def run_qa(
    samples: pd.DataFrame,
    attempts: pd.DataFrame,
) -> str:

    lines = []

    def add(x=""):
        lines.append(str(x))

    add("=" * 72)
    add("INDY 500 V2 FUTURE TRACK SAMPLE QA")
    add("=" * 72)

    add()
    add("TOTAL MATCHED PAIRS")
    add(len(samples))

    add()
    add("MATCH RATE")
    add(
        attempts[
            "matched"
        ]
        .value_counts()
        .to_string()
    )

    add()
    add("PAIRS BY YEAR / HORIZON")
    add(
        samples.groupby(
            [
                "year",
                "requested_horizon_min",
            ]
        )
        .size()
        .unstack(
            fill_value=0
        )
        .to_string()
    )

    add()
    add("MATCH SUCCESS BY REQUESTED HORIZON")
    add(
        attempts.groupby(
            "requested_horizon_min"
        )["matched"]
        .agg(
            [
                "count",
                "sum",
                "mean",
            ]
        )
        .to_string()
    )

    add()
    add("ACTUAL HORIZON ERROR")
    add(
        samples[
            "horizon_error_min"
        ]
        .describe()
        .to_string()
    )

    add()
    add("THERMAL RATE VALIDITY")
    add(
        samples[
            "rate_valid"
        ]
        .value_counts(
            dropna=False
        )
        .to_string()
    )

    add()
    add("THERMAL RATE LOOKBACK")
    add(
        samples[
            "rate_lookback_min"
        ]
        .describe()
        .to_string()
    )

    add()
    add("THERMAL RATE RANGE")
    add(
        samples[
            "track_rate_0_c_per_min"
        ]
        .describe()
        .to_string()
    )

    add()
    add("THERMAL GAP RANGE")
    add(
        samples[
            "thermal_gap_0_c"
        ]
        .describe()
        .to_string()
    )

    add()
    add("DELTA TRACK TEMPERATURE")
    add(
        samples[
            "delta_track_temp_c"
        ]
        .describe()
        .to_string()
    )

    add()
    add("DELTA AMBIENT TEMPERATURE")
    add(
        samples[
            "delta_ambient_temp_c"
        ]
        .describe()
        .to_string()
    )

    # --------------------------------------------------------
    # Hard integrity tests
    # --------------------------------------------------------

    add()
    add("=" * 72)
    add("INTEGRITY CHECKS")
    add("=" * 72)

    duplicate_ids = (
        samples[
            "pair_id"
        ]
        .duplicated()
        .sum()
    )

    add(
        f"Duplicate pair_id: "
        f"{duplicate_ids}"
    )

    invalid_horizon = (
        samples[
            "actual_horizon_min"
        ]
        <= 0
    ).sum()

    add(
        f"Non-positive horizons: "
        f"{invalid_horizon}"
    )

    tolerance_failures = (
        samples[
            "horizon_error_min"
        ]
        > FUTURE_TOLERANCE_MIN
    ).sum()

    add(
        f"Horizon tolerance failures: "
        f"{tolerance_failures}"
    )

    wrong_year = (
        pd.to_datetime(
            samples[
                "t0_utc"
            ],
            utc=True,
        ).dt.year
        != samples[
            "year"
        ]
    ).sum()

    add(
        f"Year mismatch: "
        f"{wrong_year}"
    )

    add()
    add("INVALID / MISSING RATE EXAMPLES")

    invalid_rate = samples[
        ~samples[
            "rate_valid"
        ]
    ]

    if invalid_rate.empty:
        add("None")
    else:
        add(
            invalid_rate[
                [
                    "year",
                    "t0_local",
                    "requested_horizon_min",
                ]
            ]
            .head(20)
            .to_string(
                index=False
            )
        )

    add()
    add("LARGEST ABSOLUTE TRACK CHANGES")

    largest = (
        samples.assign(
            abs_delta=lambda x:
            x[
                "delta_track_temp_c"
            ].abs()
        )
        .sort_values(
            "abs_delta",
            ascending=False,
        )
        .head(15)
    )

    add(
        largest[
            [
                "year",
                "t0_local",
                "future_local",
                "requested_horizon_min",
                "actual_horizon_min",
                "track_temp_0_c",
                "future_track_temp_c",
                "delta_track_temp_c",
            ]
        ]
        .to_string(
            index=False
        )
    )

    return "\n".join(
        lines
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "=" * 72
    )
    print(
        "INDY 500 V2-A "
        "FUTURE TRACK SAMPLE BUILDER"
    )
    print(
        "=" * 72
    )

    print(
        f"\nInput:\n{INPUT_FILE}"
    )

    df = load_data()

    print(
        f"\nSource rows: {len(df)}"
    )

    print(
        "Years:",
        sorted(
            df[
                "year"
            ].unique()
        ),
    )

    print(
        "Sessions:",
        df[
            "session_id"
        ].nunique(),
    )

    samples, attempts = (
        build_samples(df)
    )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    samples.to_csv(
        OUTPUT_FILE,
        index=False,
    )

    qa = run_qa(
        samples,
        attempts,
    )

    QA_FILE.write_text(
        qa,
        encoding="utf-8",
    )

    print()
    print(qa)

    print(
        "\nOUTPUT"
    )

    print(
        OUTPUT_FILE
    )

    print(
        QA_FILE
    )

    print(
        "\nDONE"
    )


if __name__ == "__main__":
    main()
    