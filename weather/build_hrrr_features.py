from __future__ import annotations

from pathlib import Path
import math

import pandas as pd


DATES = [
    "20200815",
    "20210522",
    "20220521",
    "20230520",
    "20240518",
]

OUTPUT_DIR = Path("weather/output")


def wind_direction_deg(u: float, v: float) -> float:
    """
    Meteorological wind direction:
    direction FROM which the wind is blowing.

    0   = North
    90  = East
    180 = South
    270 = West
    """

    direction = math.degrees(
        math.atan2(-u, -v)
    )

    return direction % 360


def relative_humidity_pct(
    temp_c: float,
    dewpoint_c: float,
) -> float:
    """
    Relative humidity from temperature
    and dew point using Magnus formula.
    """

    a = 17.625
    b = 243.04

    numerator = math.exp(
        (a * dewpoint_c)
        / (b + dewpoint_c)
    )

    denominator = math.exp(
        (a * temp_c)
        / (b + temp_c)
    )

    rh = (
        100.0
        * numerator
        / denominator
    )

    return max(
        0.0,
        min(100.0, rh),
    )


def build_features(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:

    df = dataframe.copy()

    df["cycle_time_utc"] = pd.to_datetime(
        df["cycle_time_utc"],
        utc=True,
    )

    df["valid_time_utc"] = pd.to_datetime(
        df["valid_time_utc"],
        utc=True,
    )

    # Temperature: Kelvin -> Celsius
    df["temp_c"] = (
        df["TMP_2m"]
        - 273.15
    )

    df["dewpoint_c"] = (
        df["DPT_2m"]
        - 273.15
    )

    # Relative humidity
    df["relative_humidity_pct"] = [
        relative_humidity_pct(
            temp,
            dew,
        )
        if pd.notna(temp)
        and pd.notna(dew)
        else None
        for temp, dew
        in zip(
            df["temp_c"],
            df["dewpoint_c"],
        )
    ]

    # Wind speed
    df["wind_speed_10m_ms"] = (
        (
            df["UGRD_10m"] ** 2
            + df["VGRD_10m"] ** 2
        )
        ** 0.5
    )

    # Wind direction
    df["wind_direction_deg"] = [
        wind_direction_deg(
            u,
            v,
        )
        if pd.notna(u)
        and pd.notna(v)
        else None
        for u, v
        in zip(
            df["UGRD_10m"],
            df["VGRD_10m"],
        )
    ]

    # Pressure Pa -> hPa
    df["pressure_hpa"] = (
        df["PRES_surface"]
        / 100.0
    )

    df["gust_ms"] = (
        df["GUST_surface"]
    )

    df["cloud_cover_pct"] = (
        df["TCDC_atmosphere"]
    )

    df["shortwave_radiation_wm2"] = (
        df["DSWRF_surface"]
    )

    # Forecast lead
    df["forecast_lead_hours"] = (
        (
            df["valid_time_utc"]
            - df["cycle_time_utc"]
        )
        .dt.total_seconds()
        / 3600.0
    )

    return df


def quality_report(
    date: str,
    df: pd.DataFrame,
) -> None:

    print()
    print("=" * 70)
    print(f"HRRR FEATURE QA — {date}")
    print("=" * 70)

    print(
        f"Rows: {len(df)}"
    )

    print(
        f"Unique cycles: "
        f"{df['cycle_time_utc'].nunique()}"
    )

    print(
        f"Unique valid times: "
        f"{df['valid_time_utc'].nunique()}"
    )

    print()

    missing = df.isna().sum()

    missing_nonzero = (
        missing[
            missing > 0
        ]
    )

    if missing_nonzero.empty:
        print("Missing values: NONE")
    else:
        print("Missing values:")
        print(
            missing_nonzero.to_string()
        )

    print()

    expected_pairs = {
        (cycle, forecast_hour)
        for cycle in range(11, 24)
        for forecast_hour in range(0, 4)
    }

    actual_pairs = {
        (
            timestamp.hour,
            int(forecast_hour),
        )
        for timestamp, forecast_hour
        in zip(
            df["cycle_time_utc"],
            df["forecast_hour"],
        )
    }

    missing_pairs = sorted(
        expected_pairs
        - actual_pairs
    )

    print(
        f"Expected cycle/lead pairs: "
        f"{len(expected_pairs)}"
    )

    print(
        f"Observed cycle/lead pairs: "
        f"{len(actual_pairs)}"
    )

    if missing_pairs:
        print(
            "Missing cycle/lead pairs:"
        )

        for cycle, lead in missing_pairs:
            print(
                f"  cycle={cycle:02d}Z "
                f"f{lead:02d}"
            )
    else:
        print(
            "Missing cycle/lead pairs: NONE"
        )

    print()

    print(
        "Temperature °C:",
        df["temp_c"].min(),
        "to",
        df["temp_c"].max(),
    )

    print(
        "Relative humidity %:",
        df["relative_humidity_pct"].min(),
        "to",
        df["relative_humidity_pct"].max(),
    )

    print(
        "Wind speed m/s:",
        df["wind_speed_10m_ms"].min(),
        "to",
        df["wind_speed_10m_ms"].max(),
    )

    print(
        "Pressure hPa:",
        df["pressure_hpa"].min(),
        "to",
        df["pressure_hpa"].max(),
    )

    print(
        "Cloud cover %:",
        df["cloud_cover_pct"].min(),
        "to",
        df["cloud_cover_pct"].max(),
    )

    print(
        "Shortwave radiation W/m²:",
        df["shortwave_radiation_wm2"].min(),
        "to",
        df["shortwave_radiation_wm2"].max(),
    )

    print(
        "Forecast leads:",
        sorted(
            df["forecast_lead_hours"]
            .dropna()
            .unique()
            .tolist()
        ),
    )


def process_date(
    date: str,
) -> pd.DataFrame:

    input_file = (
        OUTPUT_DIR
        / f"hrrr_ims_{date}.csv"
    )

    output_file = (
        OUTPUT_DIR
        / f"hrrr_ims_{date}_features.csv"
    )

    if not input_file.exists():
        raise FileNotFoundError(
            f"Input file not found: "
            f"{input_file}"
        )

    dataframe = pd.read_csv(
        input_file
    )

    features = build_features(
        dataframe
    )

    features.to_csv(
        output_file,
        index=False,
    )

    quality_report(
        date,
        features,
    )

    print()
    print(
        f"Saved: {output_file}"
    )

    return features


def main() -> None:

    all_years = []

    for date in DATES:

        features = process_date(
            date
        )

        all_years.append(
            features
        )

    combined = pd.concat(
        all_years,
        ignore_index=True,
    )

    combined_file = (
        OUTPUT_DIR
        / "hrrr_ims_2020_2024_features.csv"
    )

    combined.to_csv(
        combined_file,
        index=False,
    )

    print()
    print("=" * 70)
    print("ALL FIVE FEATURE TABLES COMPLETED")
    print("=" * 70)

    print(
        f"Combined rows: "
        f"{len(combined)}"
    )

    print(
        f"Combined output: "
        f"{combined_file}"
    )


if __name__ == "__main__":
    main()