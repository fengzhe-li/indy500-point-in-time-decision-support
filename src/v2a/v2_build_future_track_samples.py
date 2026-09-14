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

# Operational forecast horizons to evaluate.
HORIZONS_MIN = [15, 30, 60, 90, 120]

# Maximum mismatch allowed when pairing a target future time
# to an observed track-temperature sample.
TARGET_TOLERANCE_MIN = 5.0


# ============================================================
# HELPERS
# ============================================================

def require_columns(df: pd.DataFrame, cols: list[str]) -> None:
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise ValueError(
            "Missing required columns: "
            + ", ".join(missing)
        )


def parse_utc(series: pd.Series) -> pd.Series:
    return pd.to_datetime(
        series,
        utc=True,
        errors="coerce",
    )


def minutes_between(
    t0: pd.Timestamp,
    t1: pd.Timestamp,
) -> float:
    return (
        (t1 - t0).total_seconds()
        / 60.0
    )


def safe_float(x):
    if pd.isna(x):
        return np.nan
    return float(x)


def build_pair_rows(
    day_df: pd.DataFrame,
    year: int,
) -> list[dict]:
    """
    Build forward pairs within one qualifying day.

    Each current observation is paired to the nearest
    observed future track-temperature point around each
    requested horizon.
    """

    rows: list[dict] = []

    day_df = (
        day_df
        .sort_values("timestamp_utc")
        .reset_index(drop=True)
    )

    for i, current in day_df.iterrows():
        t0 = current["timestamp_utc"]

        if pd.isna(t0):
            continue

        future = day_df.iloc[i + 1 :].copy()
        if future.empty:
            continue

        future["actual_horizon_min"] = (
            future["timestamp_utc"] - t0
        ).dt.total_seconds() / 60.0

        for requested_h in HORIZONS_MIN:
            candidate = future.copy()
            candidate["target_error_min"] = (
                candidate["actual_horizon_min"]
                - requested_h
            ).abs()

            candidate = candidate[
                candidate["target_error_min"]
                <= TARGET_TOLERANCE_MIN
            ]

            if candidate.empty:
                continue

            best = (
                candidate
                .sort_values(
                    [
                        "target_error_min",
                        "timestamp_utc",
                    ]
                )
                .iloc[0]
            )

            row = {
                "year": int(year),
                "current_timestamp_utc": t0,
                "future_timestamp_utc": best["timestamp_utc"],
                "requested_horizon_min": int(requested_h),
                "actual_horizon_min": safe_float(
                    best["actual_horizon_min"]
                ),
                "target_error_min": safe_float(
                    best["target_error_min"]
                ),
                "current_track_temp_c": safe_float(
                    current["track_temp_c"]
                ),
                "future_track_temp_c": safe_float(
                    best["track_temp_c"]
                ),
                "delta_track_temp_c": (
                    safe_float(best["track_temp_c"])
                    - safe_float(current["track_temp_c"])
                ),
            }

            # Carry environmental variables when available.
            for col in (
                "ambient_temp_c",
                "relative_humidity_pct",
                "wind_speed_ms",
                "gust_ms",
                "solar_wm2",
            ):
                if col in day_df.columns:
                    row[f"current_{col}"] = safe_float(
                        current[col]
                    )
                    row[f"future_{col}"] = safe_float(
                        best[col]
                    )

                    if col == "ambient_temp_c":
                        row["delta_ambient_temp_c"] = (
                            safe_float(best[col])
                            - safe_float(current[col])
                        )

            if "ambient_temp_c" in day_df.columns:
                row["current_thermal_gap_c"] = (
                    safe_float(current["track_temp_c"])
                    - safe_float(current["ambient_temp_c"])
                )

            rows.append(row)

    return rows


def main() -> None:
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    df = pd.read_csv(INPUT_FILE)

    require_columns(
        df,
        [
            "year",
            "timestamp_utc",
            "track_temp_c",
        ],
    )

    df["timestamp_utc"] = parse_utc(
        df["timestamp_utc"]
    )

    df["year"] = pd.to_numeric(
        df["year"],
        errors="coerce",
    ).astype("Int64")

    df["track_temp_c"] = pd.to_numeric(
        df["track_temp_c"],
        errors="coerce",
    )

    df = df.dropna(
        subset=[
            "year",
            "timestamp_utc",
            "track_temp_c",
        ]
    ).copy()

    pair_rows: list[dict] = []

    for year, day_df in df.groupby("year"):
        pair_rows.extend(
            build_pair_rows(
                day_df=day_df,
                year=int(year),
            )
        )

    out = pd.DataFrame(pair_rows)

    if out.empty:
        raise RuntimeError(
            "No future-track pairs were constructed."
        )

    out = out.sort_values(
        [
            "year",
            "current_timestamp_utc",
            "requested_horizon_min",
        ]
    ).reset_index(drop=True)

    out.to_csv(
        OUTPUT_FILE,
        index=False,
    )

    counts = (
        out.groupby(
            ["year", "requested_horizon_min"]
        )
        .size()
        .rename("n")
        .reset_index()
    )

    qa_lines = [
        "V2 FUTURE TRACK SAMPLE BUILD",
        "=" * 72,
        f"input_rows={len(df)}",
        f"paired_rows={len(out)}",
        "",
        "PAIR COUNTS BY YEAR / HORIZON",
        "-" * 72,
        counts.to_string(index=False),
        "",
        "TARGET ERROR (MINUTES)",
        "-" * 72,
        out["target_error_min"].describe().to_string(),
    ]

    QA_FILE.write_text(
        "\n".join(qa_lines) + "\n",
        encoding="utf-8",
    )

    print(
        "Wrote",
        OUTPUT_FILE,
        len(out),
    )
    print(
        "Wrote",
        QA_FILE,
    )


if __name__ == "__main__":
    main()
