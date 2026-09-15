from pathlib import Path
from collections import Counter
from datetime import datetime, timezone
import csv
import json
import math
import re

ROOT = Path(
    "/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈"
)

OUT = ROOT / "r4/output"

MANIFEST = (
    OUT /
    "r4f7b_latent_window_training_manifest_v1.csv"
)

ATTEMPTS = (
    OUT /
    "r4p1_attempt_four_lap_panel_v1.csv"
)

OUT_FILES = (
    OUT /
    "r4f7c2a_canonical_weather_source_candidates_v1.csv"
)

OUT_COLUMNS = (
    OUT /
    "r4f7c2a_canonical_weather_source_columns_v1.csv"
)

OUT_JOIN = (
    OUT /
    "r4f7c2a_weather_source_join_coverage_v1.csv"
)

OUT_QA = (
    OUT /
    "r4f7c2a_canonical_weather_source_discovery_qa_v1.csv"
)

OUT_REPORT = (
    OUT /
    "r4f7c2a_canonical_weather_source_discovery_report_v1.json"
)


SCAN_DIRS = [
    ROOT / "r4/output",
    ROOT / "weather/output",
    ROOT / "weather",
]


TRACK_HINTS = [
    "ptsc_track_temp_c",
    "track_temp_c",
    "track_temperature_c",
    "track_c",
]

HRRR_HINTS = [
    "hrrr",
    "relative_humidity",
    "wind_speed",
    "pressure",
    "gust",
    "cloud_cover",
    "shortwave",
]

TIME_HINTS = [
    "time_point_utc",
    "decision_time_utc",
    "valid_time_utc",
    "valid_time",
    "timestamp_utc",
    "timestamp",
    "ptsc_selected_time_utc",
    "selected_hrrr_cycle_utc",
    "hrrr_selected_cycle_utc",
    "target_time_utc",
    "forecast_time_utc",
]

YEAR_HINTS = [
    "year",
    "season",
]


def clean(v):
    if v is None:
        return ""
    return str(v).strip()


def num(v):
    s = clean(v)

    if not s:
        return None

    try:
        x = float(s)

        if math.isfinite(x):
            return x

    except Exception:
        pass

    return None


def truthy(v):
    return clean(v).lower() in {
        "1",
        "true",
        "yes",
        "y",
        "t",
    }


def year_int(v):
    x = num(v)

    if x is None:
        return None

    y = int(x)

    if 2000 <= y <= 2100:
        return y

    return None


def parse_dt(v):
    s = clean(v)

    if not s:
        return None

    if s.endswith("Z"):
        s = s[:-1] + "+00:00"

    try:
        dt = datetime.fromisoformat(s)

    except Exception:
        return None

    if dt.tzinfo is None:
        dt = dt.replace(
            tzinfo=timezone.utc
        )

    return dt.astimezone(
        timezone.utc
    )


def read_csv(path):
    with path.open(
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as f:

        reader = csv.DictReader(f)

        return (
            reader.fieldnames or [],
            list(reader),
        )


def norm(s):
    return re.sub(
        r"[^a-z0-9]+",
        "_",
        clean(s).lower()
    ).strip("_")


def is_track_column(col):
    c = norm(col)

    return (
        c in TRACK_HINTS
        or
        (
            "track" in c
            and
            (
                "temp" in c
                or
                "temperature" in c
            )
        )
    )


def is_hrrr_numeric_column(col):
    c = norm(col)

    if (
        "available" in c
        or
        "usable" in c
    ):
        return False

    return any(
        token in c
        for token in HRRR_HINTS
    )


def detect_time_columns(fields):
    result = []

    for f in fields:
        c = norm(f)

        if (
            c in TIME_HINTS
            or
            "time_utc" in c
            or
            c.endswith("_utc")
            or
            "valid_time" in c
            or
            "timestamp" in c
        ):
            result.append(f)

    return result


def detect_year_columns(fields):
    return [
        f
        for f in fields
        if norm(f) in YEAR_HINTS
    ]


def continuous_numeric(rows, field):
    vals = []

    for r in rows:
        x = num(
            r.get(field)
        )

        if x is not None:
            vals.append(x)

    if not vals:
        return False, 0, "", ""

    unique = len(
        {
            round(x, 8)
            for x in vals
        }
    )

    return (
        unique >= 5,
        len(vals),
        min(vals),
        max(vals),
    )


for path in [
    MANIFEST,
    ATTEMPTS,
]:

    if not path.exists():
        raise SystemExit(
            f"MISSING INPUT: {path}"
        )


_, manifest = read_csv(
    MANIFEST
)

attempt_fields, attempt_rows = read_csv(
    ATTEMPTS
)


target_ids = {
    clean(
        r.get("attempt_id")
    )
    for r in manifest
    if (
        truthy(
            r.get("model_eligible")
        )
        and
        clean(
            r.get("split_role")
        )
        in {
            "DEVELOPMENT",
            "VALIDATION_ONLY",
        }
    )
}


attempt_by_id = {
    clean(
        r.get("attempt_id")
    ):
    r
    for r in attempt_rows
    if clean(
        r.get("attempt_id")
    )
}


targets = []

for aid in target_ids:

    r = attempt_by_id.get(aid)

    if not r:
        continue

    dt = parse_dt(
        r.get(
            "time_point_utc"
        )
    )

    y = year_int(
        r.get("year")
    )

    if (
        dt is None
        or
        y is None
    ):
        continue

    targets.append({
        "attempt_id":
            aid,

        "year":
            y,

        "time":
            dt,
    })


print("=" * 148)
print("R4F7C2A — CANONICAL WEATHER SOURCE DISCOVERY")
print("=" * 148)

print(
    f"Frozen target IDs: {len(target_ids)}"
)

print(
    f"Targets with year + point time: {len(targets)}"
)


# =============================================================================
# Discover CSV files recursively
# =============================================================================

all_paths = []

seen_paths = set()

for base in SCAN_DIRS:

    if not base.exists():
        continue

    for path in base.rglob("*.csv"):

        rp = str(
            path.resolve()
        )

        if rp in seen_paths:
            continue

        seen_paths.add(rp)
        all_paths.append(path)


file_rows = []
column_rows = []
join_rows = []


for path in sorted(all_paths):

    try:
        fields, rows = read_csv(path)

    except Exception:
        continue

    if not fields or not rows:
        continue


    time_cols = detect_time_columns(
        fields
    )

    year_cols = detect_year_columns(
        fields
    )

    track_cols = []
    hrrr_cols = []


    for f in fields:

        ok, n, mn, mx = continuous_numeric(
            rows,
            f
        )

        if not ok:
            continue

        if is_track_column(f):

            track_cols.append(f)

            column_rows.append({
                "file":
                    str(
                        path.relative_to(ROOT)
                    ),

                "column":
                    f,

                "class":
                    "TRACK_TEMPERATURE",

                "numeric_rows":
                    n,

                "min":
                    mn,

                "max":
                    mx,
            })


        if is_hrrr_numeric_column(f):

            hrrr_cols.append(f)

            column_rows.append({
                "file":
                    str(
                        path.relative_to(ROOT)
                    ),

                "column":
                    f,

                "class":
                    "HRRR_OR_WEATHER",

                "numeric_rows":
                    n,

                "min":
                    mn,

                "max":
                    mx,
            })


    if (
        not track_cols
        and
        not hrrr_cols
    ):
        continue


    file_type = (
        "TRACK_AND_HRRR"
        if (
            track_cols
            and
            hrrr_cols
        )
        else
        (
            "TRACK"
            if track_cols
            else
            "HRRR_WEATHER"
        )
    )


    file_rows.append({
        "file":
            str(
                path.relative_to(ROOT)
            ),

        "rows":
            len(rows),

        "file_type":
            file_type,

        "track_numeric_cols":
            len(track_cols),

        "hrrr_weather_numeric_cols":
            len(hrrr_cols),

        "time_columns":
            ";".join(
                time_cols
            ),

        "year_columns":
            ";".join(
                year_cols
            ),

        "track_columns":
            ";".join(
                track_cols
            ),

        "hrrr_weather_columns":
            ";".join(
                hrrr_cols
            ),
    })


    # -------------------------------------------------------------------------
    # Joinability audit.
    #
    # For each candidate time column, see how many target attempts have
    # a same-year source point within 5 / 15 / 30 / 60 minutes.
    #
    # This does NOT perform the final join.
    # -------------------------------------------------------------------------

    for time_col in time_cols:

        source_points = []

        for r in rows:

            dt = parse_dt(
                r.get(
                    time_col
                )
            )

            if dt is None:
                continue


            year = None

            for yc in year_cols:

                year = year_int(
                    r.get(yc)
                )

                if year is not None:
                    break


            if year is None:
                year = dt.year


            source_points.append(
                (
                    year,
                    dt,
                )
            )


        if not source_points:
            continue


        counts = {
            5: 0,
            15: 0,
            30: 0,
            60: 0,
        }

        abs_deltas = []


        by_year = {}

        for year, dt in source_points:

            by_year.setdefault(
                year,
                []
            ).append(dt)


        for t in targets:

            candidates = by_year.get(
                t["year"],
                []
            )

            if not candidates:
                continue

            best_seconds = min(
                abs(
                    (
                        s
                        -
                        t["time"]
                    ).total_seconds()
                )
                for s in candidates
            )

            best_minutes = (
                best_seconds
                /
                60.0
            )

            abs_deltas.append(
                best_minutes
            )

            for threshold in counts:

                if best_minutes <= threshold:
                    counts[
                        threshold
                    ] += 1


        join_rows.append({
            "file":
                str(
                    path.relative_to(ROOT)
                ),

            "file_type":
                file_type,

            "time_column":
                time_col,

            "source_time_rows":
                len(
                    source_points
                ),

            "target_rows":
                len(
                    targets
                ),

            "within_5m":
                counts[5],

            "within_15m":
                counts[15],

            "within_30m":
                counts[30],

            "within_60m":
                counts[60],

            "coverage_5m":
                counts[5]
                /
                len(targets),

            "coverage_15m":
                counts[15]
                /
                len(targets),

            "coverage_30m":
                counts[30]
                /
                len(targets),

            "coverage_60m":
                counts[60]
                /
                len(targets),

            "median_nearest_minutes":
                (
                    sorted(
                        abs_deltas
                    )[
                        len(
                            abs_deltas
                        )
                        //
                        2
                    ]
                    if abs_deltas
                    else ""
                ),
        })


file_rows.sort(
    key=lambda r: (
        -r[
            "track_numeric_cols"
        ],
        -r[
            "hrrr_weather_numeric_cols"
        ],
        -r[
            "rows"
        ],
        r[
            "file"
        ],
    )
)


join_rows.sort(
    key=lambda r: (
        -r[
            "coverage_15m"
        ],
        -r[
            "coverage_30m"
        ],
        r[
            "file"
        ],
        r[
            "time_column"
        ],
    )
)


track_sources = [
    r
    for r in file_rows
    if r[
        "track_numeric_cols"
    ] > 0
]


hrrr_sources = [
    r
    for r in file_rows
    if r[
        "hrrr_weather_numeric_cols"
    ] > 0
]


# =============================================================================
# Special expected canonical HRRR source check
# =============================================================================

canonical_hrrr = (
    ROOT /
    "weather/output/"
    "hrrr_ims_2020_2024_features.csv"
)

canonical_hrrr_present = (
    canonical_hrrr.exists()
)


# =============================================================================
# QA
# =============================================================================

qa_rows = [
    {
        "metric":
            "frozen_target_ids",
        "value":
            len(
                target_ids
            ),
        "expected":
            110,
        "status":
            (
                "PASS"
                if len(
                    target_ids
                ) == 110
                else "FAIL"
            ),
    },

    {
        "metric":
            "targets_with_point_time",
        "value":
            len(
                targets
            ),
        "expected":
            110,
        "status":
            (
                "PASS"
                if len(
                    targets
                ) == 110
                else "FAIL"
            ),
    },

    {
        "metric":
            "track_numeric_source_found",
        "value":
            len(
                track_sources
            ),
        "expected":
            ">0",
        "status":
            (
                "PASS"
                if track_sources
                else "FAIL"
            ),
    },

    {
        "metric":
            "weather_numeric_source_found",
        "value":
            len(
                hrrr_sources
            ),
        "expected":
            ">0",
        "status":
            (
                "PASS"
                if hrrr_sources
                else "FAIL"
            ),
    },

    {
        "metric":
            "canonical_hrrr_file_present",
        "value":
            canonical_hrrr_present,
        "expected":
            True,
        "status":
            (
                "PASS"
                if canonical_hrrr_present
                else "WARN"
            ),
    },

    {
        "metric":
            "discovery_only_no_model_fit",
        "value":
            True,
        "expected":
            True,
        "status":
            "PASS",
    },
]


# =============================================================================
# Save
# =============================================================================

if file_rows:

    with OUT_FILES.open(
        "w",
        encoding="utf-8",
        newline=""
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=list(
                file_rows[0].keys()
            )
        )

        writer.writeheader()
        writer.writerows(
            file_rows
        )


if column_rows:

    with OUT_COLUMNS.open(
        "w",
        encoding="utf-8",
        newline=""
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=list(
                column_rows[0].keys()
            )
        )

        writer.writeheader()
        writer.writerows(
            column_rows
        )


if join_rows:

    with OUT_JOIN.open(
        "w",
        encoding="utf-8",
        newline=""
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=list(
                join_rows[0].keys()
            )
        )

        writer.writeheader()
        writer.writerows(
            join_rows
        )


with OUT_QA.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=[
            "metric",
            "value",
            "expected",
            "status",
        ]
    )

    writer.writeheader()
    writer.writerows(
        qa_rows
    )


report = {
    "phase":
        "R4F7C2A",

    "status":
        "R4F7C2A_CANONICAL_WEATHER_SOURCE_DISCOVERY_READY",

    "target_attempts":
        len(
            targets
        ),

    "track_source_count":
        len(
            track_sources
        ),

    "hrrr_weather_source_count":
        len(
            hrrr_sources
        ),

    "canonical_hrrr_expected_path":
        (
            "weather/output/"
            "hrrr_ims_2020_2024_features.csv"
        ),

    "canonical_hrrr_present":
        canonical_hrrr_present,

    "top_track_sources":
        track_sources[:10],

    "top_weather_sources":
        hrrr_sources[:10],

    "top_join_candidates":
        join_rows[:20],

    "next_phase":
        (
            "R4F7C2B constructs the frozen 110-row numeric model "
            "matrix from the resolved canonical PTSC and HRRR sources "
            "using explicit time-safe join rules."
        ),
}


OUT_REPORT.write_text(
    json.dumps(
        report,
        indent=2,
        ensure_ascii=False
    ),
    encoding="utf-8"
)


# =============================================================================
# Console
# =============================================================================

print()
print("=" * 148)
print("TRACK TEMPERATURE SOURCE CANDIDATES")
print("=" * 148)

if not track_sources:

    print("NONE")

else:

    for r in track_sources[:20]:

        print()
        print(
            f"FILE: {r['file']}"
        )

        print(
            f"  rows={r['rows']}"
        )

        print(
            f"  time_columns={r['time_columns']}"
        )

        print(
            f"  year_columns={r['year_columns']}"
        )

        print(
            f"  track_columns={r['track_columns']}"
        )


print()
print("=" * 148)
print("HRRR / WEATHER SOURCE CANDIDATES")
print("=" * 148)

if not hrrr_sources:

    print("NONE")

else:

    for r in hrrr_sources[:20]:

        print()
        print(
            f"FILE: {r['file']}"
        )

        print(
            f"  rows={r['rows']}"
        )

        print(
            f"  time_columns={r['time_columns']}"
        )

        print(
            f"  year_columns={r['year_columns']}"
        )

        print(
            f"  weather_numeric_cols="
            f"{r['hrrr_weather_numeric_cols']}"
        )


print()
print("=" * 148)
print("TIME-JOIN COVERAGE — TOP CANDIDATES")
print("=" * 148)

if not join_rows:

    print("NONE")

else:

    for r in join_rows[:30]:

        print(
            f"{r['file'][:72]:72s} | "
            f"time={r['time_column'][:28]:28s} | "
            f"5m={r['within_5m']:3d}/110 | "
            f"15m={r['within_15m']:3d}/110 | "
            f"30m={r['within_30m']:3d}/110 | "
            f"60m={r['within_60m']:3d}/110 | "
            f"median={r['median_nearest_minutes']}"
        )


print()
print("=" * 148)
print("CANONICAL HRRR SOURCE")
print("=" * 148)

print(
    "weather/output/"
    "hrrr_ims_2020_2024_features.csv"
)

print(
    f"present={canonical_hrrr_present}"
)


fails = [
    r
    for r in qa_rows
    if r[
        "status"
    ] == "FAIL"
]

warns = [
    r
    for r in qa_rows
    if r[
        "status"
    ] == "WARN"
]


print()
print(
    f"QA: "
    f"{len(qa_rows)-len(fails)-len(warns)} PASS | "
    f"{len(warns)} WARN | "
    f"{len(fails)} FAIL"
)

if fails:

    for r in fails:

        print(
            f"FAIL | "
            f"{r['metric']} | "
            f"value={r['value']} | "
            f"expected={r['expected']}"
        )

    raise SystemExit(1)


print()
print("OUTPUTS")
print(
    OUT_FILES.relative_to(ROOT)
)
print(
    OUT_COLUMNS.relative_to(ROOT)
)
print(
    OUT_JOIN.relative_to(ROOT)
)
print(
    OUT_QA.relative_to(ROOT)
)
print(
    OUT_REPORT.relative_to(ROOT)
)

print()
print(
    "R4F7C2A_CANONICAL_WEATHER_SOURCE_DISCOVERY_READY"
)
