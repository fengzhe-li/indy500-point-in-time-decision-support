from pathlib import Path
from zoneinfo import ZoneInfo
import pandas as pd


INPUT_FILE = Path(
    "weather/evidence/ptsc/"
    "indy500_day1_track_temp_2020_2024.csv"
)

OUTPUT_FILE = Path(
    "weather/evidence/ptsc/"
    "indy500_day1_track_temp_2020_2024_time_normalized.csv"
)

TIMEZONE_NAME = "America/Indiana/Indianapolis"

LOCAL_TZ = ZoneInfo(TIMEZONE_NAME)
UTC_TZ = ZoneInfo("UTC")


def main():

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Input file not found: {INPUT_FILE}"
        )

    df = pd.read_csv(INPUT_FILE)

    required = [
        "year",
        "session_date",
        "local_time",
    ]

    missing = [
        c for c in required
        if c not in df.columns
    ]

    if missing:
        raise RuntimeError(
            f"Missing required columns: {missing}"
        )

    # ---------------------------------
    # Build naive local datetime
    # ---------------------------------

    local_naive = pd.to_datetime(
        df["session_date"].astype(str)
        + " "
        + df["local_time"].astype(str),
        errors="coerce",
    )

    if local_naive.isna().any():

        bad = df[
            local_naive.isna()
        ][
            [
                "year",
                "session_date",
                "local_time",
            ]
        ]

        raise RuntimeError(
            "Failed to parse some timestamps:\n"
            + bad.to_string(index=False)
        )

    # ---------------------------------
    # Apply Indianapolis timezone
    # ---------------------------------

    local_aware = local_naive.dt.tz_localize(
        TIMEZONE_NAME,
        ambiguous="raise",
        nonexistent="raise",
    )

    utc_aware = local_aware.dt.tz_convert(
        "UTC"
    )

    # ---------------------------------
    # Add canonical time fields
    # ---------------------------------

    df.insert(
        3,
        "timezone_name",
        TIMEZONE_NAME,
    )

    df.insert(
        4,
        "local_datetime",
        local_aware.astype(str),
    )

    df.insert(
        5,
        "utc_datetime",
        utc_aware.astype(str),
    )

    df.insert(
        6,
        "utc_offset_hours",
        local_aware.apply(
            lambda x:
            x.utcoffset().total_seconds()
            / 3600
        ),
    )

    # ---------------------------------
    # QA
    # ---------------------------------

    print()
    print("========================")
    print("PTSC TIMESTAMP NORMALIZATION")
    print("========================")
    print()

    print(
        "Timezone:",
        TIMEZONE_NAME,
    )

    print(
        "Rows:",
        len(df),
    )

    print()
    print("UTC OFFSET COUNTS")
    print("------------------------")

    print(
        df["utc_offset_hours"]
        .value_counts()
        .sort_index()
        .to_string()
    )

    print()
    print("ROWS BY YEAR")
    print("------------------------")

    print(
        df.groupby("year")
        .size()
        .to_string()
    )

    print()
    print("FIRST / LAST BY YEAR")
    print("------------------------")

    for year, group in df.groupby(
        "year",
        sort=True,
    ):

        group = group.sort_values(
            "utc_datetime"
        )

        print()
        print(year)

        print(
            " first local:",
            group.iloc[0][
                "local_datetime"
            ],
        )

        print(
            " first UTC:  ",
            group.iloc[0][
                "utc_datetime"
            ],
        )

        print(
            " last local: ",
            group.iloc[-1][
                "local_datetime"
            ],
        )

        print(
            " last UTC:   ",
            group.iloc[-1][
                "utc_datetime"
            ],
        )

    # ---------------------------------
    # Assertions
    # ---------------------------------

    assert len(df) == 168, (
        f"Expected 168 rows, got {len(df)}"
    )

    assert (
        df["utc_datetime"]
        .notna()
        .all()
    )

    # All five target dates should
    # fall under daylight saving time.
    assert set(
        df["utc_offset_hours"]
        .unique()
    ) == {-4.0}, (
        "Unexpected UTC offset detected: "
        f"{sorted(df['utc_offset_hours'].unique())}"
    )

    # No duplicate observation timestamp
    # within a year/date/time combination.
    duplicate_count = (
        df.duplicated(
            subset=[
                "year",
                "session_date",
                "local_time",
            ]
        )
        .sum()
    )

    assert duplicate_count == 0, (
        f"Duplicate local timestamps: "
        f"{duplicate_count}"
    )

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    df.to_csv(
        OUTPUT_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    print()
    print("========================")
    print("PASS")
    print("========================")

    print(
        "Output:",
        OUTPUT_FILE,
    )

    print(
        "All 168 observations converted "
        "from Indianapolis local time "
        "to UTC."
    )


if __name__ == "__main__":
    main()