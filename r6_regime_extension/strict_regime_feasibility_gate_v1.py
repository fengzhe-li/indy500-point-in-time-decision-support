from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path("/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈")
OUT = ROOT / "r6_regime_extension/output"
OUT.mkdir(parents=True, exist_ok=True)

TARGET_YEARS = [2018, 2019, 2025, 2026]

FILES = {
    "attempt_laps":
        ROOT / "data/canonical/v1/attempt_laps.csv",

    "attempt_sections":
        ROOT / "data/canonical/v1/attempt_sections.csv",

    "chronology_events":
        ROOT / "data/canonical/v1/chronology_events.csv",

    "day1_first_run":
        ROOT / "r5_1/output/day1_first_run_field_sweep_v1.csv",

    "day1_repeats":
        ROOT / "r5_1/output/day1_same_car_repeat_inventory_v1.csv",
}

def load(name):
    path = FILES[name]

    if not path.exists():
        print("MISSING:", path.relative_to(ROOT))
        return None

    df = pd.read_csv(path, low_memory=False)

    print(
        f"{name}: {len(df)} rows, "
        f"{len(df.columns)} cols"
    )

    return df

tables = {
    name: load(name)
    for name in FILES
}

# ============================================================
# helpers
# ============================================================

def find_year_col(df):

    if df is None:
        return None

    preferred = [
        "year",
        "season_year",
        "session_year",
        "event_year",
    ]

    for c in preferred:
        if c in df.columns:
            return c

    # fallback: date-like columns
    date_candidates = [
        c for c in df.columns
        if any(
            x in c.lower()
            for x in [
                "date",
                "datetime",
                "timestamp",
                "time_utc",
            ]
        )
    ]

    for c in date_candidates:

        parsed = pd.to_datetime(
            df[c],
            errors="coerce",
            utc=True
        )

        if parsed.notna().sum() > 0:
            return ("__DATE__", c)

    return None


def extract_year(df, year_info):

    if df is None or year_info is None:
        return pd.Series(
            np.nan,
            index=df.index if df is not None else []
        )

    if isinstance(year_info, tuple):

        _, c = year_info

        return pd.to_datetime(
            df[c],
            errors="coerce",
            utc=True
        ).dt.year

    return pd.to_numeric(
        df[year_info],
        errors="coerce"
    )


def find_col(df, candidates):

    if df is None:
        return None

    for c in candidates:
        if c in df.columns:
            return c

    return None


# ============================================================
# inspect year semantics
# ============================================================

print("\n" + "=" * 150)
print("PART 1 — STRICT YEAR FIELD DISCOVERY")
print("=" * 150)

year_sources = {}

for name, df in tables.items():

    yi = find_year_col(df)
    year_sources[name] = yi

    print(
        name,
        "->",
        yi
    )

# ============================================================
# raw true-year row counts
# ============================================================

print("\n" + "=" * 150)
print("PART 2 — TRUE YEAR ROW COUNTS")
print("=" * 150)

year_count_rows = []

for name, df in tables.items():

    if df is None:
        continue

    yi = year_sources[name]

    if yi is None:
        continue

    years = extract_year(df, yi)

    for y in TARGET_YEARS:

        n = int(
            (years == y).sum()
        )

        year_count_rows.append({
            "table": name,
            "year": y,
            "rows": n,
        })

counts = pd.DataFrame(year_count_rows)

if not counts.empty:
    print(
        counts.pivot(
            index="table",
            columns="year",
            values="rows"
        )
        .fillna(0)
        .astype(int)
        .to_string()
    )

# ============================================================
# attempt-lap feasibility
# ============================================================

print("\n" + "=" * 150)
print("PART 3 — ATTEMPT / FOUR-LAP FEASIBILITY")
print("=" * 150)

attempt_df = tables["attempt_laps"]

attempt_rows = []

if attempt_df is not None:

    yi = year_sources["attempt_laps"]
    years = extract_year(attempt_df, yi)

    attempt_id_col = find_col(
        attempt_df,
        [
            "attempt_id",
            "qualifying_attempt_id",
            "run_id",
        ]
    )

    lap_no_col = find_col(
        attempt_df,
        [
            "lap_number",
            "lap_index",
            "attempt_lap_number",
        ]
    )

    driver_col = find_col(
        attempt_df,
        [
            "driver_name",
            "driver",
        ]
    )

    car_col = find_col(
        attempt_df,
        [
            "car_number",
            "car_no",
        ]
    )

    time_col = find_col(
        attempt_df,
        [
            "timestamp_utc",
            "attempt_time_utc",
            "time_utc",
            "performance_time_utc",
        ]
    )

    speed_col = find_col(
        attempt_df,
        [
            "lap_speed_mph",
            "speed_mph",
            "official_lap_speed_mph",
        ]
    )

    print("attempt_id_col =", attempt_id_col)
    print("lap_no_col =", lap_no_col)
    print("driver_col =", driver_col)
    print("car_col =", car_col)
    print("time_col =", time_col)
    print("speed_col =", speed_col)

    for y in TARGET_YEARS:

        sub = attempt_df[
            years == y
        ].copy()

        if sub.empty:
            attempt_rows.append({
                "year": y,
                "lap_rows": 0,
                "unique_attempts": 0,
                "complete_4lap_attempts": 0,
                "timestamp_nonnull_rows": 0,
                "timestamp_coverage_pct": 0.0,
            })
            continue

        unique_attempts = (
            sub[attempt_id_col].nunique()
            if attempt_id_col
            else np.nan
        )

        complete_4lap = np.nan

        if (
            attempt_id_col
            and lap_no_col
        ):

            lap_counts = (
                sub.groupby(
                    attempt_id_col
                )[lap_no_col]
                .nunique()
            )

            complete_4lap = int(
                (lap_counts >= 4).sum()
            )

        timestamp_nonnull = (
            int(sub[time_col].notna().sum())
            if time_col
            else 0
        )

        timestamp_cov = (
            100.0
            *
            timestamp_nonnull
            /
            len(sub)
            if len(sub)
            else 0.0
        )

        attempt_rows.append({
            "year": y,
            "lap_rows": len(sub),
            "unique_attempts": unique_attempts,
            "complete_4lap_attempts": complete_4lap,
            "timestamp_nonnull_rows":
                timestamp_nonnull,
            "timestamp_coverage_pct":
                timestamp_cov,
        })

attempt_summary = pd.DataFrame(
    attempt_rows
)

print(
    attempt_summary
    .round(2)
    .to_string(index=False)
)

# ============================================================
# repeat feasibility
# ============================================================

print("\n" + "=" * 150)
print("PART 4 — SAME-CAR REPEAT FEASIBILITY")
print("=" * 150)

repeat_df = tables["day1_repeats"]

repeat_rows = []

if repeat_df is not None:

    yi = year_sources["day1_repeats"]
    years = extract_year(
        repeat_df,
        yi
    )

    for y in TARGET_YEARS:

        sub = repeat_df[
            years == y
        ].copy()

        repeat_rows.append({
            "year": y,
            "repeat_transition_rows":
                len(sub),

            "full_env_rows":
                int(
                    (
                        sub.get(
                            "physical_link_quality",
                            pd.Series(
                                index=sub.index,
                                dtype=object
                            )
                        )
                        .astype(str)
                        .str.contains(
                            "FULL",
                            case=False,
                            na=False
                        )
                    ).sum()
                )
                if not sub.empty
                else 0,
        })

repeat_summary = pd.DataFrame(
    repeat_rows
)

print(
    repeat_summary
    .to_string(index=False)
)

# ============================================================
# chronology feasibility
# ============================================================

print("\n" + "=" * 150)
print("PART 5 — CHRONOLOGY FEASIBILITY")
print("=" * 150)

chrono_df = tables["chronology_events"]

chrono_rows = []

if chrono_df is not None:

    yi = year_sources[
        "chronology_events"
    ]

    years = extract_year(
        chrono_df,
        yi
    )

    time_candidates = [
        c
        for c in chrono_df.columns
        if any(
            x in c.lower()
            for x in [
                "timestamp",
                "time_utc",
                "datetime",
                "event_time",
                "local_time",
            ]
        )
    ]

    print(
        "Chronology time-like columns:",
        time_candidates
    )

    for y in TARGET_YEARS:

        sub = chrono_df[
            years == y
        ].copy()

        best_time_col = None
        best_nonnull = 0

        for c in time_candidates:

            n = int(
                sub[c]
                .notna()
                .sum()
            )

            if n > best_nonnull:
                best_nonnull = n
                best_time_col = c

        chrono_rows.append({
            "year": y,
            "chronology_rows":
                len(sub),

            "best_time_col":
                best_time_col,

            "timestamp_nonnull":
                best_nonnull,

            "timestamp_coverage_pct":
                (
                    100.0
                    *
                    best_nonnull
                    /
                    len(sub)
                    if len(sub)
                    else 0.0
                )
        })

chrono_summary = pd.DataFrame(
    chrono_rows
)

print(
    chrono_summary
    .round(2)
    .to_string(index=False)
)

# ============================================================
# final feasibility gate
# ============================================================

print("\n" + "=" * 150)
print("PART 6 — REGIME FEASIBILITY GATE")
print("=" * 150)

final_rows = []

for y in TARGET_YEARS:

    a = attempt_summary[
        attempt_summary["year"] == y
    ]

    r = repeat_summary[
        repeat_summary["year"] == y
    ]

    c = chrono_summary[
        chrono_summary["year"] == y
    ]

    complete_attempts = (
        int(
            a.iloc[0][
                "complete_4lap_attempts"
            ]
        )
        if (
            not a.empty
            and pd.notna(
                a.iloc[0][
                    "complete_4lap_attempts"
                ]
            )
        )
        else 0
    )

    repeats = (
        int(
            r.iloc[0][
                "repeat_transition_rows"
            ]
        )
        if not r.empty
        else 0
    )

    chrono_cov = (
        float(
            c.iloc[0][
                "timestamp_coverage_pct"
            ]
        )
        if not c.empty
        else 0.0
    )

    # conservative gate
    attempt_gate = (
        complete_attempts >= 20
    )

    repeat_gate = (
        repeats >= 5
    )

    time_gate = (
        chrono_cov >= 50
    )

    if (
        attempt_gate
        and repeat_gate
        and time_gate
    ):
        verdict = "STRONG_EXTENSION_CANDIDATE"

    elif (
        complete_attempts >= 10
        and repeats >= 2
    ):
        verdict = "PARTIAL_EXTENSION_CANDIDATE"

    elif complete_attempts > 0:
        verdict = "EXTERNAL_VALIDATION_ONLY"

    else:
        verdict = "NO_CURRENT_DATA"

    final_rows.append({
        "year": y,
        "complete_4lap_attempts":
            complete_attempts,
        "repeat_transitions":
            repeats,
        "chronology_timestamp_coverage_pct":
            chrono_cov,
        "attempt_gate":
            attempt_gate,
        "repeat_gate":
            repeat_gate,
        "time_gate":
            time_gate,
        "verdict":
            verdict,
    })

final = pd.DataFrame(
    final_rows
)

print(
    final
    .round(2)
    .to_string(index=False)
)

# ============================================================
# save
# ============================================================

attempt_summary.to_csv(
    OUT /
    "strict_attempt_feasibility_v1.csv",
    index=False
)

repeat_summary.to_csv(
    OUT /
    "strict_repeat_feasibility_v1.csv",
    index=False
)

chrono_summary.to_csv(
    OUT /
    "strict_chronology_feasibility_v1.csv",
    index=False
)

final.to_csv(
    OUT /
    "strict_regime_feasibility_gate_v1.csv",
    index=False
)

print("\nOUTPUTS:")
print(
    "r6_regime_extension/output/"
    "strict_attempt_feasibility_v1.csv"
)
print(
    "r6_regime_extension/output/"
    "strict_repeat_feasibility_v1.csv"
)
print(
    "r6_regime_extension/output/"
    "strict_chronology_feasibility_v1.csv"
)
print(
    "r6_regime_extension/output/"
    "strict_regime_feasibility_gate_v1.csv"
)

print(
    "\nR6_STRICT_REGIME_FEASIBILITY_GATE_V1_COMPLETE"
)
