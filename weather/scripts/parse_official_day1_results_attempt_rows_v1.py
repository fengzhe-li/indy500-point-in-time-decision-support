from pathlib import Path
import csv
import re


# ============================================================
# PHASE
# ============================================================

PHASE = "R1F.3"

TEXT_DIR = Path(
    "weather/evidence/rescue/"
    "official_day1_session_details/report_text_v1"
)

OUTPUT_DIR = Path("weather/output")

OUTPUT_CSV = (
    OUTPUT_DIR
    / "official_day1_results_attempt_rows_v1.csv"
)

QA_CSV = (
    OUTPUT_DIR
    / "official_day1_results_attempt_rows_v1_qa.csv"
)


# ============================================================
# PRIMARY FULL RESULTS FILES
#
# 2023_6202_03_Results.txt is MOD34 and is deliberately
# excluded from the full attempt-history table.
# ============================================================

FILES = {
    2020: (
        "2020_5771_01_Results.txt"
    ),
    2021: (
        "2021_5838_01_Results.txt"
    ),
    2022: (
        "2022_6033_01_Results.txt"
    ),
    2023: (
        "2023_6202_02_Results.txt"
    ),
    2024: (
        "2024_6382_01_Results.txt"
    ),
}


# ============================================================
# KNOWN STATUS LABELS
# ============================================================

STATUS_LABELS = [
    "Failed Attempt",
    "No Attempt",
    "Waved Off",
    "Withdrawn",
    "Incomplete",
    "Retired",
    "Bumped",
]


# ============================================================
# HELPERS
# ============================================================

def write_csv(
    path,
    rows,
    fields,
):

    with path.open(
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as handle:

        writer = csv.DictWriter(
            handle,
            fieldnames=fields,
        )

        writer.writeheader()
        writer.writerows(rows)


def normalize_space(text):

    return re.sub(
        r"\s+",
        " ",
        text.strip(),
    )


def detect_status(line):

    for status in STATUS_LABELS:

        if re.search(
            rf"\b{re.escape(status)}\b",
            line,
            flags=re.IGNORECASE,
        ):

            return status

    return ""


def looks_like_result_row(line):

    # Official result rows begin with:
    #
    # position / row number
    # car number
    # driver surname, firstname
    #
    # Example:
    # 33 51 Sato, Takuma ...

    return bool(
        re.match(
            r"^\s*\d+\s+\S+\s+"
            r".+?,\s+.+?\s+"
            r"[A-Z]/[A-Z]/[A-Z]\s+",
            line,
        )
    )


def parse_row(
    year,
    source_file,
    source_line_number,
    raw_line,
):

    line = raw_line.rstrip()

    # Split on 2+ spaces.
    # This works well for pdftotext -layout output.
    parts = [
        part.strip()
        for part in re.split(
            r"\s{2,}",
            line.strip(),
        )
        if part.strip()
    ]

    # First block can still contain:
    # position car driver
    #
    # so parse the beginning separately.

    prefix = re.match(
        r"^\s*"
        r"(?P<result_row>\d+)\s+"
        r"(?P<car>\S+)\s+"
        r"(?P<driver>.+?)\s+"
        r"(?P<engine_tire>[A-Z]/[A-Z]/[A-Z])\s+"
        r"(?P<rest>.+?)"
        r"\s*$",
        line,
    )

    if not prefix:

        return None

    result_row = (
        prefix.group(
            "result_row"
        )
    )

    car = (
        prefix.group(
            "car"
        )
    )

    driver = normalize_space(
        prefix.group(
            "driver"
        )
    )

    engine_tire = (
        prefix.group(
            "engine_tire"
        )
    )

    rest = (
        prefix.group(
            "rest"
        )
    )

    status = detect_status(
        line
    )

    # Remove trailing Day 1 + status for numeric parsing.
    numeric_part = re.sub(
        r"\s+Day\s+1"
        r"(?:\s+.*)?$",
        "",
        rest,
        flags=re.IGNORECASE,
    ).strip()

    tokens = numeric_part.split()

    # Expected first 6 numeric columns:
    # lap1 lap2 lap3 lap4 elapsed speed
    #
    # Some values may be zero.

    if len(tokens) < 6:

        lap1 = ""
        lap2 = ""
        lap3 = ""
        lap4 = ""
        elapsed = ""
        speed = ""

    else:

        lap1 = tokens[0]
        lap2 = tokens[1]
        lap3 = tokens[2]
        lap4 = tokens[3]
        elapsed = tokens[4]
        speed = tokens[5]

    return {
        "year":
            year,

        "source_file":
            source_file,

        "source_line_number":
            source_line_number,

        "result_row":
            result_row,

        "car_number":
            car,

        "driver_name_pdf":
            driver,

        "engine_tire":
            engine_tire,

        "qual_lap_1":
            lap1,

        "qual_lap_2":
            lap2,

        "qual_lap_3":
            lap3,

        "qual_lap_4":
            lap4,

        "elapsed_time":
            elapsed,

        "speed_avg_mph":
            speed,

        "status":
            status,

        "raw_line":
            raw_line.rstrip(),
    }


# ============================================================
# MAIN
# ============================================================

def main():

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print()
    print("=" * 120)
    print(
        "R1F.3 — OFFICIAL DAY 1 RESULTS "
        "ATTEMPT-ROW PARSER V1"
    )
    print("=" * 120)

    rows = []
    year_counts = {}
    year_status_counts = {}

    missing_files = []

    for year, filename in FILES.items():

        path = (
            TEXT_DIR
            / filename
        )

        print()
        print("=" * 120)
        print(
            f"YEAR {year}"
        )
        print("=" * 120)

        print(
            "SOURCE:",
            path,
        )

        if not path.exists():

            print(
                "MISSING"
            )

            missing_files.append(
                str(path)
            )

            continue

        lines = path.read_text(
            encoding="utf-8",
            errors="replace",
        ).splitlines()

        parsed = []

        for line_number, line in enumerate(
            lines,
            start=1,
        ):

            if not looks_like_result_row(
                line
            ):

                continue

            row = parse_row(
                year,
                filename,
                line_number,
                line,
            )

            if row is not None:

                parsed.append(
                    row
                )

        rows.extend(
            parsed
        )

        year_counts[
            year
        ] = len(
            parsed
        )

        status_counts = {}

        for row in parsed:

            key = (
                row["status"]
                if row["status"]
                else "VALID_OR_UNLABELED"
            )

            status_counts[
                key
            ] = (
                status_counts.get(
                    key,
                    0,
                )
                + 1
            )

        year_status_counts[
            year
        ] = status_counts

        print(
            "PARSED ROWS:",
            len(
                parsed
            ),
        )

        print()
        print(
            "STATUS DISTRIBUTION"
        )
        print("-" * 120)

        for status, count in (
            sorted(
                status_counts.items(),
                key=lambda item: (
                    -item[1],
                    item[0],
                ),
            )
        ):

            print(
                f"{status:<22} "
                f"{count}"
            )

        print()
        print(
            "FIRST 10 PARSED ROWS"
        )
        print("-" * 120)

        for row in parsed[:10]:

            print(
                f"row={row['result_row']:<3} | "
                f"car={row['car_number']:<3} | "
                f"{row['driver_name_pdf']:<28} | "
                f"speed={row['speed_avg_mph']:<8} | "
                f"status={row['status']!r}"
            )

        if year == 2022:

            print()
            print(
                "2022 TARGETED ROWS"
            )
            print("-" * 120)

            for row in parsed:

                if row[
                    "car_number"
                ] in {
                    "51",
                    "3",
                    "27",
                    "24",
                    "06",
                    "2",
                }:

                    print(
                        f"row={row['result_row']:<3} | "
                        f"car={row['car_number']:<3} | "
                        f"{row['driver_name_pdf']:<25} | "
                        f"speed={row['speed_avg_mph']:<8} | "
                        f"elapsed={row['elapsed_time']:<12} | "
                        f"status={row['status']!r}"
                    )

    # ========================================================
    # WRITE MAIN OUTPUT
    # ========================================================

    write_csv(
        OUTPUT_CSV,
        rows,
        [
            "year",
            "source_file",
            "source_line_number",
            "result_row",
            "car_number",
            "driver_name_pdf",
            "engine_tire",
            "qual_lap_1",
            "qual_lap_2",
            "qual_lap_3",
            "qual_lap_4",
            "elapsed_time",
            "speed_avg_mph",
            "status",
            "raw_line",
        ],
    )

    # ========================================================
    # QA
    # ========================================================

    EXPECTED_MIN_ROWS = {
        2020: 59,
        2021: 59,
        2022: 44,
        2023: 80,
        2024: 70,
    }

    qa_rows = []

    for year in FILES:

        actual = year_counts.get(
            year,
            0,
        )

        minimum = EXPECTED_MIN_ROWS[
            year
        ]

        qa_rows.append({
            "metric":
                f"{year}_parsed_rows",

            "value":
                actual,

            "status":
                (
                    "PASS"
                    if actual >= minimum
                    else "REVIEW"
                ),
        })

    qa_rows.extend([
        {
            "metric":
                "source_files_missing",

            "value":
                len(
                    missing_files
                ),

            "status":
                (
                    "PASS"
                    if not missing_files
                    else "FAIL"
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
                "result_row_treated_as_chronology",

            "value":
                0,

            "status":
                "PASS",
        },

        {
            "metric":
                "timestamps_inferred",

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
    ])

    write_csv(
        QA_CSV,
        qa_rows,
        [
            "metric",
            "value",
            "status",
        ],
    )

    # ========================================================
    # SUMMARY
    # ========================================================

    print()
    print("=" * 120)
    print(
        "CROSS-YEAR PARSE SUMMARY"
    )
    print("=" * 120)

    for year in FILES:

        print(
            f"{year}: "
            f"{year_counts.get(year, 0)}"
        )

    print()
    print(
        "TOTAL PARSED ROWS:",
        len(
            rows
        ),
    )

    print()
    print(
        "IMPORTANT:"
    )

    print(
        "Result-row order is NOT treated "
        "as run chronology."
    )

    print(
        "Blank status means only that the "
        "official Results PDF supplied no "
        "special status label on that row."
    )

    print()
    print("=" * 120)

    if (
        not missing_files
        and
        all(
            year_counts.get(
                year,
                0,
            )
            >= EXPECTED_MIN_ROWS[
                year
            ]
            for year in FILES
        )
    ):

        print(
            "FINAL STATUS: "
            "OFFICIAL_DAY1_ATTEMPT_STATUS_TABLE_RECOVERED"
        )

    else:

        print(
            "FINAL STATUS: "
            "OFFICIAL_DAY1_ATTEMPT_STATUS_TABLE_REVIEW_REQUIRED"
        )

    print("=" * 120)

    print()
    print(
        "NO CANONICAL DATA WAS MODIFIED."
    )

    print(
        "NO CHRONOLOGY WAS INFERRED."
    )

    print()
    print(
        "OUTPUTS"
    )

    print(
        OUTPUT_CSV
    )

    print(
        QA_CSV
    )


if __name__ == "__main__":
    main()
