from pathlib import Path
from datetime import datetime, time
import pandas as pd


INPUT_FILE = Path(
    "weather/evidence/ptsc/"
    "FirestoneTemperatures_current.xlsx"
)

OUTPUT_FILE = Path(
    "weather/evidence/ptsc/"
    "indy500_day1_track_temp_2020_2024.csv"
)

EXCLUDED_BLOCKS_FILE = Path(
    "weather/evidence/ptsc/"
    "indy500_day1_track_temp_excluded_blocks.csv"
)

OUTPUT_FILE.parent.mkdir(
    parents=True,
    exist_ok=True,
)


TARGETS = {
    2020: {
        "sheet": "2020 Temp Archive",
        "date": "2020-08-15",
        "sensor_names": [
            "SF",
            "I6",
            "I10",
            "I15",
        ],
        "occurrence": 1,
    },
    2021: {
        "sheet": "2021 Temp Archive",
        "date": "2021-05-22",
        "sensor_names": [
            "T1T",
            "T2T",
            "T3",
            "T4T",
        ],
        "occurrence": 1,
    },
    2022: {
        "sheet": "2022 Temp Archive",
        "date": "2022-05-21",
        "sensor_names": [
            "I2",
            "I3T",
            "I5",
            "I6",
        ],

        # IMPORTANT:
        # The source workbook contains
        # 2022-05-21 twice.
        #
        # We use only the FIRST contiguous
        # source block for Day 1.
        #
        # The second occurrence is preserved
        # separately as excluded source data.
        "occurrence": 1,
    },
    2023: {
        "sheet": "2023 Temp Archive",
        "date": "2023-05-20",
        "sensor_names": [
            "SF",
            "I3",
            "I5",
            "I6",
        ],
        "occurrence": 1,
    },
    2024: {
        "sheet": "2024 Temp Archive",
        "date": "2024-05-18",
        "sensor_names": [
            "I2",
            "I3T",
            "I5",
            "I6",
        ],
        "occurrence": 1,
    },
}


def parse_date(value):

    if pd.isna(value):
        return None

    if isinstance(
        value,
        (pd.Timestamp, datetime),
    ):
        return value.date()

    text = str(value).strip()

    if not any(
        char.isdigit()
        for char in text
    ):
        return None

    parsed = pd.to_datetime(
        value,
        errors="coerce",
    )

    if pd.isna(parsed):
        return None

    return parsed.date()


def parse_time(value):

    if pd.isna(value):
        return None

    if isinstance(value, time):
        return value.strftime(
            "%H:%M:%S"
        )

    if isinstance(
        value,
        (pd.Timestamp, datetime),
    ):
        return value.strftime(
            "%H:%M:%S"
        )

    text = str(value).strip()

    parsed = pd.to_datetime(
        text,
        errors="coerce",
    )

    if pd.isna(parsed):
        return None

    return parsed.strftime(
        "%H:%M:%S"
    )


def numeric(value):

    return pd.to_numeric(
        value,
        errors="coerce",
    )


def fahrenheit_to_celsius(value):

    value = numeric(value)

    if pd.isna(value):
        return None

    return (
        float(value) - 32
    ) * 5 / 9


def find_date_occurrences(
    df,
    target_date,
):

    locations = []

    for row_index in range(
        len(df)
    ):

        value = df.iloc[
            row_index,
            0
        ]

        detected = parse_date(
            value
        )

        if detected == target_date:

            locations.append(
                row_index
            )

    return locations


def find_block_end(
    df,
    start_row,
):

    """
    A source block begins at an explicit
    date in column 0 and continues until
    the next explicit date in column 0
    or the end of the sheet.

    Blank separator rows do NOT by
    themselves terminate the block.
    """

    for row_index in range(
        start_row + 1,
        len(df),
    ):

        value = df.iloc[
            row_index,
            0
        ]

        detected = parse_date(
            value
        )

        if detected is not None:

            return row_index

    return len(df)


def build_result(
    year,
    target_date,
    row,
    sensor_names,
    source_row_index,
    source_block_occurrence,
):

    if len(row) < 8:
        return None

    time_value = parse_time(
        row.iloc[1]
    )

    if time_value is None:
        return None

    ambient_f = numeric(
        row.iloc[2]
    )

    track_f = numeric(
        row.iloc[3]
    )

    humidity = numeric(
        row.iloc[4]
    )

    wind_raw = (
        row.iloc[5]
    )

    wind = numeric(
        wind_raw
    )

    direction = (
        None
        if pd.isna(
            row.iloc[6]
        )
        else str(
            row.iloc[6]
        ).strip()
    )

    pressure_raw = numeric(
        row.iloc[7]
    )

    # -----------------------------
    # Conservative pressure policy
    # -----------------------------
    #
    # Preserve the raw source value.
    # Values outside plausible
    # barometric range are NOT
    # silently corrected.
    #
    # Example:
    # 2022-05-21 08:30 = 239.13
    #
    # It is retained as pressure_raw
    # but canonical pressure becomes
    # missing with a quality flag.

    if pd.isna(pressure_raw):

        pressure = None

        pressure_quality = (
            "MISSING"
        )

    elif (
        float(pressure_raw) < 25
        or float(pressure_raw) > 32
    ):

        pressure = None

        pressure_quality = (
            "SOURCE_VALUE_OUT_OF_RANGE"
        )

    else:

        pressure = float(
            pressure_raw
        )

        pressure_quality = "VALID"

    sensor_values = []

    for col_index in [
        9,
        10,
        11,
        12,
    ]:

        if col_index < len(row):

            sensor_values.append(
                numeric(
                    row.iloc[
                        col_index
                    ]
                )
            )

        else:

            sensor_values.append(
                None
            )

    sensor_avg = (
        numeric(
            row.iloc[13]
        )
        if len(row) > 13
        else None
    )

    return {
        "year": year,

        "session_date": (
            target_date.isoformat()
        ),

        "local_time": time_value,

        "source_sheet": (
            f"{year} Temp Archive"
        ),

        "source_row_index": (
            source_row_index
        ),

        "source_block_occurrence": (
            source_block_occurrence
        ),

        "ambient_f": (
            None
            if pd.isna(
                ambient_f
            )
            else float(
                ambient_f
            )
        ),

        "ambient_c": (
            fahrenheit_to_celsius(
                ambient_f
            )
        ),

        "track_f": (
            None
            if pd.isna(
                track_f
            )
            else float(
                track_f
            )
        ),

        "track_c": (
            fahrenheit_to_celsius(
                track_f
            )
        ),

        "humidity": (
            None
            if pd.isna(
                humidity
            )
            else float(
                humidity
            )
        ),

        "wind_raw": (
            None
            if pd.isna(
                wind_raw
            )
            else str(
                wind_raw
            )
        ),

        "wind": (
            None
            if pd.isna(
                wind
            )
            else float(
                wind
            )
        ),

        "wind_direction": (
            direction
        ),

        "pressure_raw": (
            None
            if pd.isna(
                pressure_raw
            )
            else float(
                pressure_raw
            )
        ),

        "pressure": pressure,

        "pressure_quality": (
            pressure_quality
        ),

        "sensor_1_name": (
            sensor_names[0]
        ),

        "sensor_1_f": (
            None
            if pd.isna(
                sensor_values[0]
            )
            else float(
                sensor_values[0]
            )
        ),

        "sensor_2_name": (
            sensor_names[1]
        ),

        "sensor_2_f": (
            None
            if pd.isna(
                sensor_values[1]
            )
            else float(
                sensor_values[1]
            )
        ),

        "sensor_3_name": (
            sensor_names[2]
        ),

        "sensor_3_f": (
            None
            if pd.isna(
                sensor_values[2]
            )
            else float(
                sensor_values[2]
            )
        ),

        "sensor_4_name": (
            sensor_names[3]
        ),

        "sensor_4_f": (
            None
            if pd.isna(
                sensor_values[3]
            )
            else float(
                sensor_values[3]
            )
        ),

        "sensor_avg_f": (
            None
            if pd.isna(
                sensor_avg
            )
            else float(
                sensor_avg
            )
        ),
    }


def extract_year(
    year,
    config,
):

    sheet = config["sheet"]

    target_date = pd.Timestamp(
        config["date"]
    ).date()

    sensor_names = config[
        "sensor_names"
    ]

    requested_occurrence = config[
        "occurrence"
    ]

    print()
    print(
        "================================="
    )

    print(
        f"{year} — {target_date}"
    )

    print(
        "================================="
    )

    df = pd.read_excel(
        INPUT_FILE,
        sheet_name=sheet,
        header=None,
    )

    occurrences = (
        find_date_occurrences(
            df,
            target_date,
        )
    )

    print(
        "Source date occurrences:",
        len(occurrences),
    )

    print(
        "Source rows:",
        occurrences,
    )

    if len(occurrences) == 0:

        print(
            "No source block found."
        )

        return [], []

    if (
        requested_occurrence
        > len(occurrences)
    ):

        raise RuntimeError(
            f"{year}: requested "
            f"occurrence "
            f"{requested_occurrence}, "
            f"but only "
            f"{len(occurrences)} found."
        )

    selected_start = (
        occurrences[
            requested_occurrence - 1
        ]
    )

    selected_end = find_block_end(
        df,
        selected_start,
    )

    results = []

    for row_index in range(
        selected_start,
        selected_end,
    ):

        row = df.iloc[
            row_index
        ]

        result = build_result(
            year=year,
            target_date=target_date,
            row=row,
            sensor_names=sensor_names,
            source_row_index=row_index,
            source_block_occurrence=(
                requested_occurrence
            ),
        )

        if result is not None:

            results.append(
                result
            )

    excluded = []

    # Preserve every duplicate-date source
    # block that was NOT selected.
    for occurrence_number, start in (
        enumerate(
            occurrences,
            start=1,
        )
    ):

        if (
            occurrence_number
            == requested_occurrence
        ):
            continue

        end = find_block_end(
            df,
            start,
        )

        for row_index in range(
            start,
            end,
        ):

            row = df.iloc[
                row_index
            ]

            result = build_result(
                year=year,
                target_date=target_date,
                row=row,
                sensor_names=sensor_names,
                source_row_index=(
                    row_index
                ),
                source_block_occurrence=(
                    occurrence_number
                ),
            )

            if result is None:
                continue

            result[
                "exclusion_reason"
            ] = (
                "DUPLICATE_SOURCE_DATE_BLOCK_"
                "NOT_SELECTED_FOR_DAY1"
            )

            excluded.append(
                result
            )

    print(
        f"Selected source block: "
        f"rows {selected_start}"
        f"–{selected_end - 1}"
    )

    print(
        f"Rows extracted: "
        f"{len(results)}"
    )

    print(
        f"Rows excluded from duplicate "
        f"date blocks: "
        f"{len(excluded)}"
    )

    if results:

        print()
        print(
            "First observation:"
        )

        print(
            results[0]
        )

        print()
        print(
            "Last observation:"
        )

        print(
            results[-1]
        )

    return results, excluded


def main():

    if not INPUT_FILE.exists():

        raise FileNotFoundError(
            f"Input workbook not found: "
            f"{INPUT_FILE}"
        )

    all_rows = []
    all_excluded = []

    for year, config in (
        TARGETS.items()
    ):

        rows, excluded = (
            extract_year(
                year,
                config,
            )
        )

        all_rows.extend(
            rows
        )

        all_excluded.extend(
            excluded
        )

    output_df = pd.DataFrame(
        all_rows
    )

    output_df.to_csv(
        OUTPUT_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    excluded_df = pd.DataFrame(
        all_excluded
    )

    excluded_df.to_csv(
        EXCLUDED_BLOCKS_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    print()
    print(
        "================================="
    )
    print(
        "DONE"
    )
    print(
        "================================="
    )

    print(
        f"Total extracted rows: "
        f"{len(output_df)}"
    )

    print(
        f"Output: "
        f"{OUTPUT_FILE}"
    )

    print(
        f"Excluded blocks: "
        f"{EXCLUDED_BLOCKS_FILE}"
    )

    print()

    if not output_df.empty:

        print(
            "Rows by year:"
        )

        print(
            output_df.groupby(
                "year"
            )
            .size()
            .to_string()
        )

    if not excluded_df.empty:

        print()
        print(
            "Excluded rows by year:"
        )

        print(
            excluded_df.groupby(
                "year"
            )
            .size()
            .to_string()
        )


if __name__ == "__main__":
    main()