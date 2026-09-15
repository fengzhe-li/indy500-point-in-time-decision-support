from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pandas as pd
import requests

from eccodes import (
    codes_grib_new_from_file,
    codes_grib_find_nearest,
    codes_release,
)


# Indianapolis Motor Speedway approximate center
IMS_LAT = 39.795
IMS_LON = -86.234

AWS_BASE = "https://noaa-hrrr-bdp-pds.s3.amazonaws.com"


# Indy 500 Day 1 qualifying dates
DATES = [
    "20200815",
    "20210522",
    "20220521",
    "20230520",
    "20240518",
]


TARGETS = {
    "TMP_2m": ("TMP", "2 m above ground"),
    "DPT_2m": ("DPT", "2 m above ground"),
    "UGRD_10m": ("UGRD", "10 m above ground"),
    "VGRD_10m": ("VGRD", "10 m above ground"),
    "GUST_surface": ("GUST", "surface"),
    "PRES_surface": ("PRES", "surface"),
    "TCDC_atmosphere": ("TCDC", "entire atmosphere"),
    "DSWRF_surface": ("DSWRF", "surface"),
}


@dataclass
class IndexRecord:
    message_number: int
    start_byte: int
    end_byte: int | None
    variable: str
    level: str
    raw: str


def hrrr_urls(
    date: str,
    cycle: int,
    forecast_hour: int,
) -> tuple[str, str]:

    filename = (
        f"hrrr.t{cycle:02d}z."
        f"wrfsfcf{forecast_hour:02d}.grib2"
    )

    base = (
        f"{AWS_BASE}/hrrr.{date}/conus/"
        f"{filename}"
    )

    return base, base + ".idx"


def parse_idx(text: str) -> list[IndexRecord]:

    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    temporary = []

    for line in lines:
        parts = line.split(":")

        if len(parts) < 5:
            continue

        try:
            message_number = int(parts[0])
            start_byte = int(parts[1])
        except ValueError:
            continue

        temporary.append(
            {
                "message_number": message_number,
                "start_byte": start_byte,
                "variable": parts[3],
                "level": parts[4],
                "raw": line,
            }
        )

    records = []

    for index, item in enumerate(temporary):

        if index + 1 < len(temporary):
            end_byte = (
                temporary[index + 1]["start_byte"] - 1
            )
        else:
            end_byte = None

        records.append(
            IndexRecord(
                message_number=item["message_number"],
                start_byte=item["start_byte"],
                end_byte=end_byte,
                variable=item["variable"],
                level=item["level"],
                raw=item["raw"],
            )
        )

    return records


def select_records(
    records: list[IndexRecord],
) -> dict[str, IndexRecord]:

    selected = {}

    for output_name, (
        wanted_variable,
        wanted_level,
    ) in TARGETS.items():

        candidates = [
            record
            for record in records
            if record.variable == wanted_variable
            and wanted_level.lower()
            in record.level.lower()
        ]

        if candidates:
            selected[output_name] = candidates[0]

    return selected


def download_byte_range(
    grib_url: str,
    record: IndexRecord,
    output_path: Path,
) -> None:

    if record.end_byte is None:
        byte_range = (
            f"bytes={record.start_byte}-"
        )
    else:
        byte_range = (
            f"bytes={record.start_byte}-"
            f"{record.end_byte}"
        )

    response = requests.get(
        grib_url,
        headers={"Range": byte_range},
        timeout=120,
    )

    response.raise_for_status()

    output_path.write_bytes(
        response.content
    )


def extract_point_with_eccodes(
    grib_file: Path,
) -> float:

    with open(
        grib_file,
        "rb",
    ) as file_handle:

        gid = codes_grib_new_from_file(
            file_handle
        )

        if gid is None:
            raise RuntimeError(
                f"Could not decode GRIB file: {grib_file}"
            )

        try:
            nearest = codes_grib_find_nearest(
                gid,
                IMS_LAT,
                IMS_LON,
                npoints=1,
            )

            point = nearest[0]

            if isinstance(point, dict):
                value = float(
                    point["value"]
                )

            elif isinstance(
                point,
                (tuple, list),
            ):
                value = float(
                    point[2]
                )

            else:
                raise TypeError(
                    "Unexpected ecCodes nearest-point "
                    f"return type: {type(point)}"
                )

        finally:
            codes_release(
                gid
            )

    return value


def collect_snapshot(
    date: str,
    cycle: int,
    forecast_hour: int,
    workdir: Path,
) -> dict:

    grib_url, idx_url = hrrr_urls(
        date,
        cycle,
        forecast_hour,
    )

    idx_response = requests.get(
        idx_url,
        timeout=60,
    )

    idx_response.raise_for_status()

    records = parse_idx(
        idx_response.text
    )

    selected = select_records(
        records
    )

    cycle_time = datetime.strptime(
        f"{date}{cycle:02d}",
        "%Y%m%d%H",
    ).replace(
        tzinfo=timezone.utc
    )

    valid_time = (
        cycle_time
        + timedelta(
            hours=forecast_hour
        )
    )

    row = {
        "date": date,
        "cycle_time_utc": cycle_time.isoformat(),
        "forecast_hour": forecast_hour,
        "valid_time_utc": valid_time.isoformat(),
        "ims_lat": IMS_LAT,
        "ims_lon": IMS_LON,
    }

    workdir.mkdir(
        parents=True,
        exist_ok=True,
    )

    for output_name in TARGETS:

        record = selected.get(
            output_name
        )

        if record is None:
            print(
                f"  Variable not found: {output_name}"
            )
            row[output_name] = None
            continue

        temp_file = (
            workdir
            / (
                f"{date}_"
                f"{cycle:02d}_"
                f"f{forecast_hour:02d}_"
                f"{output_name}.grib2"
            )
        )

        download_byte_range(
            grib_url,
            record,
            temp_file,
        )

        try:
            value = extract_point_with_eccodes(
                temp_file
            )

            row[output_name] = value

            print(
                f"  {output_name}: {value}"
            )

        finally:
            temp_file.unlink(
                missing_ok=True
            )

    return row


def process_date(
    date: str,
) -> None:

    output_dir = Path(
        "weather/output"
    )

    temp_dir = Path(
        "weather/tmp"
    )

    rows = []

    print()
    print("=" * 70)
    print(f"PROCESSING DATE: {date}")
    print("=" * 70)

    # Wider cycle window:
    # 11Z–23Z
    for cycle in range(11, 24):

        # Keep short forecast leads
        for forecast_hour in range(0, 4):

            print()
            print(
                f"Fetching {date} "
                f"cycle={cycle:02d} "
                f"f{forecast_hour:02d}"
            )

            try:
                row = collect_snapshot(
                    date=date,
                    cycle=cycle,
                    forecast_hour=forecast_hour,
                    workdir=temp_dir,
                )

                rows.append(
                    row
                )

            except requests.HTTPError as exc:

                print(
                    "  Missing/unavailable:"
                    f" {exc}"
                )

            except Exception as exc:

                print(
                    "  ERROR:"
                    f" {type(exc).__name__}: {exc}"
                )

    dataframe = pd.DataFrame(
        rows
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_file = (
        output_dir
        / f"hrrr_ims_{date}.csv"
    )

    dataframe.to_csv(
        output_file,
        index=False,
    )

    print()
    print("-" * 70)
    print(
        f"Saved {len(dataframe)} rows"
    )
    print(
        f"Output: {output_file}"
    )
    print("-" * 70)


def main() -> None:

    for date in DATES:
        process_date(
            date
        )

    print()
    print("=" * 70)
    print("ALL FIVE DATES COMPLETED")
    print("=" * 70)


if __name__ == "__main__":
    main()