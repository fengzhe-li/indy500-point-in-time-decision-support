from pathlib import Path
import numpy as np
import pandas as pd


INPUT_FILE = Path(
    "weather/evidence/ptsc/"
    "indy500_day1_track_temp_2020_2024.csv"
)

QA_OUTPUT = Path(
    "weather/evidence/ptsc/"
    "indy500_day1_track_temp_qa.csv"
)

SUMMARY_OUTPUT = Path(
    "weather/evidence/ptsc/"
    "indy500_day1_track_temp_qa_summary.csv"
)


EXPECTED_YEARS = [2020, 2021, 2022, 2023, 2024]


def circular_wind_check(series):
    """
    We do not convert direction here.
    Only report missing / raw unique values.
    """
    cleaned = (
        series
        .dropna()
        .astype(str)
        .str.strip()
    )

    return sorted(
        cleaned.unique().tolist()
    )


def add_datetime(df):
    df = df.copy()

    df["datetime_local"] = pd.to_datetime(
        df["session_date"].astype(str)
        + " "
        + df["local_time"].astype(str),
        errors="coerce",
    )

    return df


def qa_year(year_df, year):

    year_df = year_df.copy()
    year_df = year_df.sort_values(
        "datetime_local"
    ).reset_index(drop=True)

    rows = []

    # ---------------------------------
    # 1. BASIC COVERAGE
    # ---------------------------------

    row_count = len(year_df)

    first_time = (
        year_df["datetime_local"].min()
        if row_count
        else pd.NaT
    )

    last_time = (
        year_df["datetime_local"].max()
        if row_count
        else pd.NaT
    )

    rows.append({
        "year": year,
        "check": "ROW_COUNT",
        "status": (
            "PASS"
            if row_count > 0
            else "FAIL"
        ),
        "value": row_count,
        "details": "",
    })

    rows.append({
        "year": year,
        "check": "TIME_COVERAGE",
        "status": (
            "PASS"
            if row_count > 0
            else "FAIL"
        ),
        "value": "",
        "details": (
            f"{first_time} -> {last_time}"
        ),
    })

    # ---------------------------------
    # 2. DUPLICATE TIMESTAMPS
    # ---------------------------------

    duplicate_count = int(
        year_df["datetime_local"]
        .duplicated()
        .sum()
    )

    rows.append({
        "year": year,
        "check": "DUPLICATE_TIMESTAMPS",
        "status": (
            "PASS"
            if duplicate_count == 0
            else "WARN"
        ),
        "value": duplicate_count,
        "details": "",
    })

    # ---------------------------------
    # 3. SAMPLING INTERVALS
    # ---------------------------------

    diffs = (
        year_df["datetime_local"]
        .diff()
        .dt.total_seconds()
        .div(60)
    )

    valid_diffs = diffs.dropna()

    if len(valid_diffs):

        median_interval = float(
            valid_diffs.median()
        )

        max_interval = float(
            valid_diffs.max()
        )

        min_interval = float(
            valid_diffs.min()
        )

        gap_over_30 = int(
            (valid_diffs > 30).sum()
        )

        gap_over_60 = int(
            (valid_diffs > 60).sum()
        )

    else:

        median_interval = np.nan
        max_interval = np.nan
        min_interval = np.nan
        gap_over_30 = 0
        gap_over_60 = 0

    rows.append({
        "year": year,
        "check": "MEDIAN_INTERVAL_MIN",
        "status": "INFO",
        "value": median_interval,
        "details": "",
    })

    rows.append({
        "year": year,
        "check": "MAX_INTERVAL_MIN",
        "status": (
            "PASS"
            if (
                pd.isna(max_interval)
                or max_interval <= 60
            )
            else "WARN"
        ),
        "value": max_interval,
        "details": (
            f">30min gaps={gap_over_30}; "
            f">60min gaps={gap_over_60}"
        ),
    })

    # ---------------------------------
    # 4. MISSINGNESS
    # ---------------------------------

    numeric_cols = [
        "ambient_f",
        "ambient_c",
        "track_f",
        "track_c",
        "humidity",
        "wind",
        "pressure",
        "sensor_1_f",
        "sensor_2_f",
        "sensor_3_f",
        "sensor_4_f",
        "sensor_avg_f",
    ]

    for col in numeric_cols:

        if col not in year_df.columns:
            continue

        missing = int(
            year_df[col].isna().sum()
        )

        pct = (
            missing / row_count * 100
            if row_count
            else np.nan
        )

        rows.append({
            "year": year,
            "check": f"MISSING_{col}",
            "status": (
                "PASS"
                if missing == 0
                else "WARN"
            ),
            "value": missing,
            "details": (
                f"{pct:.2f}%"
                if not pd.isna(pct)
                else ""
            ),
        })

    # ---------------------------------
    # 5. RANGE CHECKS
    # ---------------------------------

    range_rules = {
        "ambient_f": (-20, 130),
        "track_f": (-20, 180),
        "humidity": (0, 1.05),
        "wind": (0, 100),
        "pressure": (25, 32),
        "sensor_1_f": (-20, 180),
        "sensor_2_f": (-20, 180),
        "sensor_3_f": (-20, 180),
        "sensor_4_f": (-20, 180),
        "sensor_avg_f": (-20, 180),
    }

    for col, (low, high) in range_rules.items():

        if col not in year_df.columns:
            continue

        series = pd.to_numeric(
            year_df[col],
            errors="coerce",
        )

        bad = (
            series.notna()
            & (
                (series < low)
                | (series > high)
            )
        )

        bad_count = int(
            bad.sum()
        )

        rows.append({
            "year": year,
            "check": f"RANGE_{col}",
            "status": (
                "PASS"
                if bad_count == 0
                else "WARN"
            ),
            "value": bad_count,
            "details": (
                f"expected [{low}, {high}]"
            ),
        })

    # ---------------------------------
    # 6. TRACK VS SENSOR AVG
    # ---------------------------------

    compare = year_df[
        ["track_f", "sensor_avg_f"]
    ].dropna()

    if len(compare):

        diff = (
            compare["track_f"]
            - compare["sensor_avg_f"]
        )

        mean_abs_diff = float(
            diff.abs().mean()
        )

        median_abs_diff = float(
            diff.abs().median()
        )

        max_abs_diff = float(
            diff.abs().max()
        )

        correlation = (
            float(
                compare["track_f"]
                .corr(
                    compare["sensor_avg_f"]
                )
            )
            if len(compare) > 1
            else np.nan
        )

    else:

        mean_abs_diff = np.nan
        median_abs_diff = np.nan
        max_abs_diff = np.nan
        correlation = np.nan

    rows.append({
        "year": year,
        "check": "TRACK_SENSOR_AVG_MAE_F",
        "status": "INFO",
        "value": mean_abs_diff,
        "details": (
            f"median_abs_diff={median_abs_diff}; "
            f"max_abs_diff={max_abs_diff}; "
            f"corr={correlation}"
        ),
    })

    # ---------------------------------
    # 7. SENSOR SPREAD
    # ---------------------------------

    sensor_cols = [
        "sensor_1_f",
        "sensor_2_f",
        "sensor_3_f",
        "sensor_4_f",
    ]

    sensor_matrix = year_df[
        sensor_cols
    ].apply(
        pd.to_numeric,
        errors="coerce",
    )

    sensor_spread = (
        sensor_matrix.max(axis=1)
        - sensor_matrix.min(axis=1)
    )

    valid_spread = sensor_spread.dropna()

    if len(valid_spread):

        median_spread = float(
            valid_spread.median()
        )

        max_spread = float(
            valid_spread.max()
        )

        spread_over_10 = int(
            (valid_spread > 10).sum()
        )

        spread_over_20 = int(
            (valid_spread > 20).sum()
        )

    else:

        median_spread = np.nan
        max_spread = np.nan
        spread_over_10 = 0
        spread_over_20 = 0

    rows.append({
        "year": year,
        "check": "SENSOR_SPREAD_F",
        "status": "INFO",
        "value": median_spread,
        "details": (
            f"max={max_spread}; "
            f">10F={spread_over_10}; "
            f">20F={spread_over_20}"
        ),
    })

    # ---------------------------------
    # 8. CONSISTENCY OF F -> C
    # ---------------------------------

    for f_col, c_col in [
        ("ambient_f", "ambient_c"),
        ("track_f", "track_c"),
    ]:

        compare_fc = year_df[
            [f_col, c_col]
        ].dropna()

        if len(compare_fc):

            expected_c = (
                compare_fc[f_col] - 32
            ) * 5 / 9

            error = (
                compare_fc[c_col]
                - expected_c
            ).abs()

            max_error = float(
                error.max()
            )

        else:
            max_error = np.nan

        rows.append({
            "year": year,
            "check": (
                f"FC_CONSISTENCY_"
                f"{f_col}_{c_col}"
            ),
            "status": (
                "PASS"
                if (
                    pd.isna(max_error)
                    or max_error < 1e-6
                )
                else "FAIL"
            ),
            "value": max_error,
            "details": "",
        })

    # ---------------------------------
    # 9. WEATHER DIRECTION VALUES
    # ---------------------------------

    directions = circular_wind_check(
        year_df["wind_direction"]
    )

    rows.append({
        "year": year,
        "check": "WIND_DIRECTION_VALUES",
        "status": "INFO",
        "value": len(directions),
        "details": "; ".join(directions),
    })

    return rows


def main():

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Input file not found: "
            f"{INPUT_FILE}"
        )

    df = pd.read_csv(
        INPUT_FILE
    )

    df = add_datetime(
        df
    )

    all_qa_rows = []

    summary_rows = []

    print()
    print(
        "================================="
    )
    print(
        "PTSC INDY 500 DAY 1 TRACK TEMP QA"
    )
    print(
        "================================="
    )

    for year in EXPECTED_YEARS:

        year_df = df[
            df["year"] == year
        ].copy()

        qa_rows = qa_year(
            year_df,
            year,
        )

        all_qa_rows.extend(
            qa_rows
        )

        pass_count = sum(
            r["status"] == "PASS"
            for r in qa_rows
        )

        warn_count = sum(
            r["status"] == "WARN"
            for r in qa_rows
        )

        fail_count = sum(
            r["status"] == "FAIL"
            for r in qa_rows
        )

        summary_rows.append({
            "year": year,
            "rows": len(year_df),
            "pass": pass_count,
            "warn": warn_count,
            "fail": fail_count,
        })

        print()
        print(f"{year}")
        print(
            f"Rows: {len(year_df)}"
        )
        print(
            f"PASS={pass_count} "
            f"WARN={warn_count} "
            f"FAIL={fail_count}"
        )

        year_sorted = year_df.sort_values(
            "datetime_local"
        )

        if len(year_sorted) > 1:

            intervals = (
                year_sorted[
                    "datetime_local"
                ]
                .diff()
                .dt.total_seconds()
                .div(60)
                .dropna()
            )

            print(
                "Median interval:",
                intervals.median(),
                "min",
            )

            print(
                "Max interval:",
                intervals.max(),
                "min",
            )

        compare = year_df[
            ["track_f", "sensor_avg_f"]
        ].dropna()

        if len(compare):

            diff = (
                compare["track_f"]
                - compare["sensor_avg_f"]
            ).abs()

            print(
                "Track vs sensor AVG MAE:",
                round(
                    diff.mean(),
                    3,
                ),
                "F",
            )

            print(
                "Track vs sensor AVG corr:",
                round(
                    compare["track_f"]
                    .corr(
                        compare[
                            "sensor_avg_f"
                        ]
                    ),
                    4,
                ),
            )

    qa_df = pd.DataFrame(
        all_qa_rows
    )

    qa_df.to_csv(
        QA_OUTPUT,
        index=False,
        encoding="utf-8-sig",
    )

    summary_df = pd.DataFrame(
        summary_rows
    )

    summary_df.to_csv(
        SUMMARY_OUTPUT,
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
        f"QA detail: {QA_OUTPUT}"
    )

    print(
        f"QA summary: {SUMMARY_OUTPUT}"
    )

    print()
    print(
        summary_df.to_string(
            index=False
        )
    )


if __name__ == "__main__":
    main()
    