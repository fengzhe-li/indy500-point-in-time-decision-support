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
    },
}


def parse_date(value):
    """
    Safely identify actual Excel dates.
    Event names and other text return None.
    """

    if pd.isna(value):
        return None

    if isinstance(
        value,
        (pd.Timestamp, datetime),
    ):
        return value.date()

    text = str(value).strip()

    # Only attempt strings that look like dates.
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
    """
    Normalize Excel/Pandas/string time to HH:MM:SS.
    """

    if pd.isna(value):
        return None

    if isinstance(value, time):
        return value.strftime("%H:%M:%S")

    if isinstance(
        value,
        (pd.Timestamp, datetime),
    ):
        return value.strftime("%H:%M:%S")

    text = str(value).strip()

    parsed = pd.to_datetime(
        text,
        errors="coerce",
    )

    if pd.isna(parsed):
        return None

    return parsed.strftime("%H:%M:%S")


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

    # header=None is intentional.
    # These archive sheets contain embedded
    # session headers and irregular metadata.
    df = pd.read_excel(
        INPUT_FILE,
        sheet_name=sheet,
        header=None,
    )

    results = []

    current_date = None

    for _, row in df.iterrows():

        first_cell = (
            row.iloc[0]
            if len(row) > 0
            else None
        )

        detected_date = parse_date(
            first_cell
        )

        if detected_date is not None:

            current_date = (
                detected_date
            )

        # If a non-date event label appears
        # in column 0 with no time, reset until
        # the next actual date is encountered.
        elif (
            not pd.isna(first_cell)
            and
            isinstance(
                first_cell,
                str,
            )
            and
            parse_time(
                row.iloc[1]
                if len(row) > 1
                else None
            )
            is None
        ):
            current_date = None

        if current_date != target_date:
            continue

        if len(row) < 8:
            continue

        time_value = parse_time(
            row.iloc[1]
        )

        if time_value is None:
            continue

        ambient_f = numeric(
            row.iloc[2]
        )

        track_f = numeric(
            row.iloc[3]
        )

        humidity = numeric(
            row.iloc[4]
        )

        wind = numeric(
            row.iloc[5]
        )

        direction = (
            None
            if pd.isna(row.iloc[6])
            else str(
                row.iloc[6]
            ).strip()
        )

        pressure = numeric(
            row.iloc[7]
        )

        # In these archives the four
        # track sensors normally occupy
        # columns 9–12 and AVG column 13.
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

        result = {
            "year": year,
            "session_date": (
                target_date.isoformat()
            ),
            "local_time": time_value,

            "ambient_f": (
                None
                if pd.isna(ambient_f)
                else float(ambient_f)
            ),

            "ambient_c": (
                fahrenheit_to_celsius(
                    ambient_f
                )
            ),

            "track_f": (
                None
                if pd.isna(track_f)
                else float(track_f)
            ),

            "track_c": (
                fahrenheit_to_celsius(
                    track_f
                )
            ),

            "humidity": (
                None
                if pd.isna(humidity)
                else float(humidity)
            ),

            "wind": (
                None
                if pd.isna(wind)
                else float(wind)
            ),

            "wind_direction": (
                direction
            ),

            "pressure": (
                None
                if pd.isna(pressure)
                else float(pressure)
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

        results.append(
            result
        )

    print(
        f"Rows found: {len(results)}"
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

    return results


def main():

    if not INPUT_FILE.exists():

        raise FileNotFoundError(
            f"Input workbook not found: "
            f"{INPUT_FILE}"
        )

    all_rows = []

    for year, config in (
        TARGETS.items()
    ):

        rows = extract_year(
            year,
            config,
        )

        all_rows.extend(
            rows
        )

    output_df = pd.DataFrame(
        all_rows
    )

    output_df.to_csv(
        OUTPUT_FILE,
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
        f"Output: {OUTPUT_FILE}"
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


if __name__ == "__main__":
    main()