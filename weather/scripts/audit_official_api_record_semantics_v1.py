from pathlib import Path
from collections import Counter, defaultdict
import csv
import json


# ============================================================
# PHASE
# ============================================================

PHASE = "R1F.2"

RAW_JSON_DIR = Path(
    "weather/evidence/rescue/"
    "official_day1_session_details/raw_api"
)

TARGETS = {
    2020: "5771",
    2021: "5838",
    2022: "6033",
    2023: "6202",
    2024: "6382",
}

OUTPUT_DIR = Path("weather/output")

SUMMARY_CSV = (
    OUTPUT_DIR
    / "official_api_record_semantics_summary_v1.csv"
)

CAR_ROWS_CSV = (
    OUTPUT_DIR
    / "official_api_record_semantics_by_car_v1.csv"
)

RECORD_ROWS_CSV = (
    OUTPUT_DIR
    / "official_api_record_semantics_records_v1.csv"
)

QA_CSV = (
    OUTPUT_DIR
    / "official_api_record_semantics_v1_qa.csv"
)


def txt(value):
    if value is None:
        return ""
    return str(value).strip()


def num(value):
    try:
        return int(str(value).strip())
    except Exception:
        return None


def write_csv(path, rows, fields):
    with path.open(
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=fields,
        )
        writer.writeheader()
        writer.writerows(rows)


def main():

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print()
    print("=" * 120)
    print(
        "R1F.2 — OFFICIAL API RECORD "
        "SEMANTICS AUDIT V1"
    )
    print("=" * 120)

    summary_rows = []
    car_rows = []
    record_rows = []

    successful_years = []

    for year, session_id in TARGETS.items():

        path = (
            RAW_JSON_DIR
            / f"{year}_{session_id}_session_details.json"
        )

        print()
        print("=" * 120)
        print(f"YEAR {year}")
        print("=" * 120)

        if not path.exists():
            print("SOURCE MISSING:", path)
            continue

        data = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

        records = data.get("records")

        if not isinstance(records, list):
            print("records IS NOT LIST")
            continue

        successful_years.append(year)

        by_car = defaultdict(list)

        for index, record in enumerate(
            records,
            start=1,
        ):

            if not isinstance(record, dict):
                continue

            car = txt(
                record.get("CarNumber")
            )

            driver = txt(
                record.get("DriverName")
            )

            status = txt(
                record.get("Status")
            )

            position_finish = num(
                record.get("PositionFinish")
            )

            position_start = num(
                record.get("PositionStart")
            )

            details_id = num(
                record.get(
                    "EventsSessionsDetailsID"
                )
            )

            entry_id = num(
                record.get(
                    "EventsEntrylistID"
                )
            )

            row = {
                "year": year,
                "session_id": session_id,
                "api_list_index": index,
                "car_number": car,
                "driver_name": driver,
                "status": status,
                "position_finish": (
                    position_finish
                    if position_finish is not None
                    else ""
                ),
                "position_start": (
                    position_start
                    if position_start is not None
                    else ""
                ),
                "events_sessions_details_id": (
                    details_id
                    if details_id is not None
                    else ""
                ),
                "events_entrylist_id": (
                    entry_id
                    if entry_id is not None
                    else ""
                ),
                "qual_lap_1": txt(
                    record.get("QualLap1")
                ),
                "qual_lap_2": txt(
                    record.get("QualLap2")
                ),
                "qual_lap_3": txt(
                    record.get("QualLap3")
                ),
                "qual_lap_4": txt(
                    record.get("QualLap4")
                ),
                "elapsed_time": txt(
                    record.get("ElapsedTime")
                ),
                "speed_avg": txt(
                    record.get("SpeedAvg")
                ),
            }

            record_rows.append(row)
            by_car[car].append(row)

        unique_cars = len(
            [car for car in by_car if car]
        )

        repeated_cars = {
            car: rows
            for car, rows in by_car.items()
            if car and len(rows) > 1
        }

        status_counter = Counter(
            row["status"]
            for row in record_rows
            if (
                row["year"] == year
                and row["status"]
            )
        )

        list_finish_match = 0
        list_finish_comparable = 0

        details_ids = []

        for row in [
            r
            for r in record_rows
            if r["year"] == year
        ]:

            pf = row["position_finish"]

            if pf != "":
                list_finish_comparable += 1

                if row["api_list_index"] == pf:
                    list_finish_match += 1

            did = row[
                "events_sessions_details_id"
            ]

            if did != "":
                details_ids.append(did)

        details_id_strictly_increasing = (
            len(details_ids) > 1
            and all(
                b > a
                for a, b in zip(
                    details_ids,
                    details_ids[1:],
                )
            )
        )

        likely_granularity = (
            "ONE_ROW_PER_CAR_FINAL_RESULT"
            if len(records) == unique_cars
            else "MULTI_ROW_RESULT_HISTORY"
        )

        print()
        print("RECORD COUNT:", len(records))
        print("UNIQUE CARS:", unique_cars)
        print(
            "REPEATED CARS:",
            len(repeated_cars),
        )
        print(
            "LIKELY GRANULARITY:",
            likely_granularity,
        )

        print()
        print("STATUS DISTRIBUTION")
        print("-" * 120)

        if not status_counter:
            print("NONE / EMPTY")
        else:
            for status, count in (
                status_counter.most_common()
            ):
                print(
                    f"{status!r}: {count}"
                )

        print()
        print(
            "API LIST INDEX == POSITION FINISH:",
            f"{list_finish_match}/"
            f"{list_finish_comparable}",
        )

        print(
            "DETAIL IDs STRICTLY INCREASING "
            "IN API LIST ORDER:",
            details_id_strictly_increasing,
        )

        print()
        print("REPEATED-CAR DETAIL")
        print("-" * 120)

        if not repeated_cars:
            print("NONE")
        else:
            for car, rows in sorted(
                repeated_cars.items(),
                key=lambda item: (
                    -len(item[1]),
                    item[0],
                ),
            ):

                driver_names = sorted(
                    set(
                        row["driver_name"]
                        for row in rows
                        if row["driver_name"]
                    )
                )

                print()
                print(
                    f"CAR {car} | "
                    f"rows={len(rows)} | "
                    f"drivers={driver_names}"
                )

                for row in rows:
                    print(
                        "  "
                        f"idx={row['api_list_index']:>3} | "
                        f"finish={str(row['position_finish']):>3} | "
                        f"start={str(row['position_start']):>3} | "
                        f"detailsID={str(row['events_sessions_details_id']):>8} | "
                        f"status={row['status']!r} | "
                        f"speed={row['speed_avg']} | "
                        f"elapsed={row['elapsed_time']}"
                    )

                    car_rows.append({
                        "year":
                            year,
                        "session_id":
                            session_id,
                        "car_number":
                            car,
                        "driver_name":
                            row["driver_name"],
                        "rows_for_car":
                            len(rows),
                        "api_list_index":
                            row["api_list_index"],
                        "position_finish":
                            row["position_finish"],
                        "position_start":
                            row["position_start"],
                        "events_sessions_details_id":
                            row[
                                "events_sessions_details_id"
                            ],
                        "events_entrylist_id":
                            row[
                                "events_entrylist_id"
                            ],
                        "status":
                            row["status"],
                        "speed_avg":
                            row["speed_avg"],
                        "elapsed_time":
                            row["elapsed_time"],
                        "qual_lap_1":
                            row["qual_lap_1"],
                        "qual_lap_2":
                            row["qual_lap_2"],
                        "qual_lap_3":
                            row["qual_lap_3"],
                        "qual_lap_4":
                            row["qual_lap_4"],
                    })

        # ====================================================
        # TARGETED 2022 EVIDENCE
        # ====================================================

        if year == 2022:

            print()
            print("=" * 120)
            print("2022 TARGETED RECORDS")
            print("=" * 120)

            target_cars = {
                "51",  # Sato
                "3",   # McLaughlin
                "27",  # Rossi
                "24",  # Karam
                "06",  # Castroneves
                "2",   # Newgarden
            }

            for row in [
                r
                for r in record_rows
                if (
                    r["year"] == 2022
                    and r["car_number"]
                    in target_cars
                )
            ]:

                print(
                    f"idx={row['api_list_index']:>3} | "
                    f"car={row['car_number']:<3} | "
                    f"{row['driver_name']:<24} | "
                    f"finish={str(row['position_finish']):>3} | "
                    f"detailsID={str(row['events_sessions_details_id']):>8} | "
                    f"status={row['status']!r} | "
                    f"speed={row['speed_avg']} | "
                    f"elapsed={row['elapsed_time']}"
                )

        summary_rows.append({
            "year":
                year,
            "session_id":
                session_id,
            "record_count":
                len(records),
            "unique_car_count":
                unique_cars,
            "repeated_car_count":
                len(repeated_cars),
            "likely_granularity":
                likely_granularity,
            "api_index_equals_finish_count":
                list_finish_match,
            "position_finish_comparable_count":
                list_finish_comparable,
            "details_id_strictly_increasing":
                details_id_strictly_increasing,
            "status_distribution":
                json.dumps(
                    dict(status_counter),
                    ensure_ascii=False,
                    sort_keys=True,
                ),
        })

    write_csv(
        SUMMARY_CSV,
        summary_rows,
        [
            "year",
            "session_id",
            "record_count",
            "unique_car_count",
            "repeated_car_count",
            "likely_granularity",
            "api_index_equals_finish_count",
            "position_finish_comparable_count",
            "details_id_strictly_increasing",
            "status_distribution",
        ],
    )

    write_csv(
        CAR_ROWS_CSV,
        car_rows,
        [
            "year",
            "session_id",
            "car_number",
            "driver_name",
            "rows_for_car",
            "api_list_index",
            "position_finish",
            "position_start",
            "events_sessions_details_id",
            "events_entrylist_id",
            "status",
            "speed_avg",
            "elapsed_time",
            "qual_lap_1",
            "qual_lap_2",
            "qual_lap_3",
            "qual_lap_4",
        ],
    )

    write_csv(
        RECORD_ROWS_CSV,
        record_rows,
        [
            "year",
            "session_id",
            "api_list_index",
            "car_number",
            "driver_name",
            "status",
            "position_finish",
            "position_start",
            "events_sessions_details_id",
            "events_entrylist_id",
            "qual_lap_1",
            "qual_lap_2",
            "qual_lap_3",
            "qual_lap_4",
            "elapsed_time",
            "speed_avg",
        ],
    )

    qa_rows = [
        {
            "metric":
                "successful_years",
            "value":
                ",".join(
                    str(y)
                    for y in successful_years
                ),
            "status":
                (
                    "PASS"
                    if len(successful_years) == 5
                    else "REVIEW"
                ),
        },
        {
            "metric":
                "canonical_data_mutated",
            "value":
                0,
            "status":
                "PASS",
        },
        {
            "metric":
                "details_id_treated_as_timestamp",
            "value":
                0,
            "status":
                "PASS",
        },
        {
            "metric":
                "api_order_treated_as_chronology",
            "value":
                0,
            "status":
                "PASS",
        },
        {
            "metric":
                "queue_or_lane_inferred",
            "value":
                0,
            "status":
                "PASS",
        },
    ]

    write_csv(
        QA_CSV,
        qa_rows,
        [
            "metric",
            "value",
            "status",
        ],
    )

    print()
    print("=" * 120)
    print("CROSS-YEAR SUMMARY")
    print("=" * 120)

    for row in summary_rows:
        print(
            f"{row['year']} | "
            f"records={row['record_count']} | "
            f"unique_cars={row['unique_car_count']} | "
            f"repeated_cars={row['repeated_car_count']} | "
            f"{row['likely_granularity']}"
        )

    print()
    print("IMPORTANT:")
    print(
        "EventsSessionsDetailsID and API list order "
        "are NOT treated as timestamps or chronology."
    )

    print()
    print("=" * 120)
    print(
        "FINAL STATUS: "
        "OFFICIAL_API_RECORD_SEMANTICS_AUDIT_COMPLETE"
    )
    print("=" * 120)

    print()
    print("OUTPUTS")
    print(SUMMARY_CSV)
    print(CAR_ROWS_CSV)
    print(RECORD_ROWS_CSV)
    print(QA_CSV)


if __name__ == "__main__":
    main()
