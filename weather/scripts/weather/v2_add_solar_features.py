from __future__ import annotations

from pathlib import Path
import math

import pandas as pd


INPUT_FILE = Path(
    "weather/output/v2_future_track/future_track_samples_v1.csv"
)

OUTPUT_FILE = Path(
    "weather/output/v2_future_track/"
    "future_track_samples_with_solar_v1.csv"
)

QA_FILE = Path(
    "weather/output/v2_future_track/"
    "future_track_samples_with_solar_v1_qa.txt"
)


# Indianapolis Motor Speedway
LATITUDE_DEG = 39.7950
LONGITUDE_DEG = -86.2348


def solar_elevation_deg(
    timestamp_utc: pd.Timestamp,
    latitude_deg: float,
    longitude_deg: float,
) -> float:
    """
    Approximate solar elevation angle using NOAA-style solar geometry.

    Input timestamp must be timezone-aware UTC.
    Returns solar elevation in degrees.
    """

    ts = pd.Timestamp(timestamp_utc)

    if ts.tzinfo is None:
        ts = ts.tz_localize("UTC")
    else:
        ts = ts.tz_convert("UTC")

    day_of_year = ts.dayofyear

    hour_decimal = (
        ts.hour
        + ts.minute / 60.0
        + ts.second / 3600.0
    )

    gamma = (
        2.0
        * math.pi
        / 365.0
        * (
            day_of_year
            - 1
            + (hour_decimal - 12.0) / 24.0
        )
    )

    equation_of_time = 229.18 * (
        0.000075
        + 0.001868 * math.cos(gamma)
        - 0.032077 * math.sin(gamma)
        - 0.014615 * math.cos(2 * gamma)
        - 0.040849 * math.sin(2 * gamma)
    )

    solar_declination = (
        0.006918
        - 0.399912 * math.cos(gamma)
        + 0.070257 * math.sin(gamma)
        - 0.006758 * math.cos(2 * gamma)
        + 0.000907 * math.sin(2 * gamma)
        - 0.002697 * math.cos(3 * gamma)
        + 0.00148 * math.sin(3 * gamma)
    )

    # UTC timezone offset = 0
    true_solar_time = (
        hour_decimal * 60.0
        + equation_of_time
        + 4.0 * longitude_deg
    ) % 1440.0

    hour_angle_deg = (
        true_solar_time / 4.0 - 180.0
    )

    hour_angle_rad = math.radians(
        hour_angle_deg
    )

    latitude_rad = math.radians(
        latitude_deg
    )

    cos_zenith = (
        math.sin(latitude_rad)
        * math.sin(solar_declination)
        + math.cos(latitude_rad)
        * math.cos(solar_declination)
        * math.cos(hour_angle_rad)
    )

    cos_zenith = max(
        -1.0,
        min(1.0, cos_zenith),
    )

    zenith_rad = math.acos(
        cos_zenith
    )

    elevation_deg = (
        90.0
        - math.degrees(zenith_rad)
    )

    return elevation_deg


def main():

    print("=" * 72)
    print(
        "INDY 500 V2-A SOLAR FEATURE BUILDER"
    )
    print("=" * 72)

    df = pd.read_csv(INPUT_FILE)

    print(f"\nInput rows: {len(df)}")

    df["t0_utc"] = pd.to_datetime(
        df["t0_utc"],
        utc=True,
    )

    df["future_utc"] = pd.to_datetime(
        df["future_utc"],
        utc=True,
    )

    df["solar_elevation_0_deg"] = (
        df["t0_utc"].apply(
            lambda x: solar_elevation_deg(
                x,
                LATITUDE_DEG,
                LONGITUDE_DEG,
            )
        )
    )

    df["future_solar_elevation_deg"] = (
        df["future_utc"].apply(
            lambda x: solar_elevation_deg(
                x,
                LATITUDE_DEG,
                LONGITUDE_DEG,
            )
        )
    )

    df["delta_solar_elevation_deg"] = (
        df["future_solar_elevation_deg"]
        - df["solar_elevation_0_deg"]
    )

    df["solar_elevation_mean_deg"] = (
        (
            df["solar_elevation_0_deg"]
            + df["future_solar_elevation_deg"]
        )
        / 2.0
    )

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    df.to_csv(
        OUTPUT_FILE,
        index=False,
    )

    # =====================================================
    # QA
    # =====================================================

    lines = []

    def add(x=""):
        lines.append(str(x))

    add("=" * 72)
    add("INDY 500 V2-A SOLAR FEATURE QA")
    add("=" * 72)

    add()
    add("ROWS")
    add(len(df))

    add()
    add("MISSING VALUES")
    add(
        df[
            [
                "solar_elevation_0_deg",
                "future_solar_elevation_deg",
                "delta_solar_elevation_deg",
                "solar_elevation_mean_deg",
            ]
        ]
        .isna()
        .sum()
        .to_string()
    )

    add()
    add("SOLAR ELEVATION AT T0")
    add(
        df[
            "solar_elevation_0_deg"
        ]
        .describe()
        .to_string()
    )

    add()
    add("FUTURE SOLAR ELEVATION")
    add(
        df[
            "future_solar_elevation_deg"
        ]
        .describe()
        .to_string()
    )

    add()
    add("DELTA SOLAR ELEVATION")
    add(
        df[
            "delta_solar_elevation_deg"
        ]
        .describe()
        .to_string()
    )

    add()
    add("=" * 72)
    add("MEAN SOLAR FEATURES BY YEAR")
    add("=" * 72)

    add(
        df.groupby("year")[
            [
                "solar_elevation_0_deg",
                "future_solar_elevation_deg",
                "delta_solar_elevation_deg",
                "solar_elevation_mean_deg",
            ]
        ]
        .mean()
        .round(3)
        .to_string()
    )

    add()
    add("=" * 72)
    add("MEAN DELTA SOLAR BY HORIZON")
    add("=" * 72)

    add(
        df.groupby(
            "requested_horizon_min"
        )[
            "delta_solar_elevation_deg"
        ]
        .agg(
            [
                "mean",
                "std",
                "min",
                "max",
            ]
        )
        .round(3)
        .to_string()
    )

    add()
    add("=" * 72)
    add("2022 SOLAR SUMMARY")
    add("=" * 72)

    add(
        df[
            df["year"] == 2022
        ][
            [
                "solar_elevation_0_deg",
                "future_solar_elevation_deg",
                "delta_solar_elevation_deg",
                "solar_elevation_mean_deg",
            ]
        ]
        .describe()
        .round(3)
        .to_string()
    )

    add()
    add("=" * 72)
    add("EXTREME SOLAR CHANGES")
    add("=" * 72)

    extreme = (
        df[
            [
                "year",
                "t0_local",
                "future_local",
                "requested_horizon_min",
                "solar_elevation_0_deg",
                "future_solar_elevation_deg",
                "delta_solar_elevation_deg",
                "delta_track_temp_c",
            ]
        ]
        .assign(
            abs_delta_solar=lambda x:
            x[
                "delta_solar_elevation_deg"
            ].abs()
        )
        .sort_values(
            "abs_delta_solar",
            ascending=False,
        )
        .head(15)
    )

    add(
        extreme
        .round(3)
        .to_string(
            index=False
        )
    )

    summary = "\n".join(lines)

    QA_FILE.write_text(
        summary,
        encoding="utf-8",
    )

    print()
    print(summary)

    print()
    print("OUTPUT")
    print(OUTPUT_FILE)
    print(QA_FILE)
    print()
    print("DONE")


if __name__ == "__main__":
    main()
    