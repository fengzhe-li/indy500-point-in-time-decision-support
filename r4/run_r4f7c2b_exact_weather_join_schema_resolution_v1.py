from pathlib import Path
from datetime import datetime, timezone
import csv
import json
import math
import re

ROOT = Path(
    "/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈"
)

OUT = ROOT / "r4/output"

TARGET_FILES = [
    ROOT / "weather/evidence/ptsc/indy500_day1_track_temp_2020_2024.csv",
    ROOT / "weather/evidence/ptsc/indy500_day1_track_temp_2020_2024_time_normalized.csv",
    ROOT / "weather/output/performance_grade_attempt_realized_environment.csv",
    ROOT / "weather/output/performance_context_features.csv",
    ROOT / "weather/output/performance_grade_hrrr_forecast_alignment.csv",
    ROOT / "weather/output/hrrr_ims_2020_2024_features.csv",
]

MANIFEST_PATH = (
    OUT /
    "r4f7b_latent_window_training_manifest_v1.csv"
)

ATTEMPT_PATH = (
    OUT /
    "r4p1_attempt_four_lap_panel_v1.csv"
)

OUT_COLUMNS = (
    OUT /
    "r4f7c2b_exact_weather_join_schema_columns_v1.csv"
)

OUT_FILES = (
    OUT /
    "r4f7c2b_exact_weather_join_schema_files_v1.csv"
)

OUT_QA = (
    OUT /
    "r4f7c2b_exact_weather_join_schema_qa_v1.csv"
)

OUT_REPORT = (
    OUT /
    "r4f7c2b_exact_weather_join_schema_report_v1.json"
)


def clean(v):
    if v is None:
        return ""
    return str(v).strip()


def truthy(v):
    return clean(v).lower() in {
        "1",
        "true",
        "yes",
        "y",
        "t",
    }


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


def parse_iso(v):
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


def looks_datetime_text(v):
    s = clean(v)

    if not s:
        return False

    if parse_iso(s):
        return True

    patterns = [
        r"^\d{4}-\d{2}-\d{2}",
        r"^\d{1,2}:\d{2}",
        r"^\d{1,2}/\d{1,2}/\d{4}",
        r"^\d{4}/\d{1,2}/\d{1,2}",
    ]

    return any(
        re.search(
            p,
            s
        )
        for p in patterns
    )


if not MANIFEST_PATH.exists():
    raise SystemExit(
        f"MISSING INPUT: {MANIFEST_PATH}"
    )

if not ATTEMPT_PATH.exists():
    raise SystemExit(
        f"MISSING INPUT: {ATTEMPT_PATH}"
    )


_, manifest = read_csv(
    MANIFEST_PATH
)

_, attempts = read_csv(
    ATTEMPT_PATH
)


target_ids = {
    clean(
        r.get(
            "attempt_id"
        )
    )
    for r in manifest
    if (
        truthy(
            r.get(
                "model_eligible"
            )
        )
        and
        clean(
            r.get(
                "split_role"
            )
        )
        in {
            "DEVELOPMENT",
            "VALIDATION_ONLY",
        }
    )
}


attempt_map = {
    clean(
        r.get(
            "attempt_id"
        )
    ):
    r
    for r in attempts
    if clean(
        r.get(
            "attempt_id"
        )
    )
}


target_times = []

for aid in target_ids:

    r = attempt_map.get(
        aid
    )

    if not r:
        continue

    dt = parse_iso(
        r.get(
            "time_point_utc"
        )
    )

    if not dt:
        continue

    try:
        year = int(
            float(
                clean(
                    r.get(
                        "year"
                    )
                )
            )
        )

    except Exception:
        continue

    target_times.append(
        (
            aid,
            year,
            dt,
        )
    )


print("=" * 150)
print("R4F7C2B — EXACT WEATHER JOIN SCHEMA RESOLUTION")
print("=" * 150)

print(
    f"Frozen target IDs: {len(target_ids)}"
)

print(
    f"Frozen target times: {len(target_times)}"
)


column_rows = []
file_rows = []


for path in TARGET_FILES:

    print()
    print("=" * 150)
    print(
        f"FILE: "
        f"{path.relative_to(ROOT)}"
    )
    print("=" * 150)

    if not path.exists():

        print("MISSING")

        file_rows.append({
            "file":
                str(
                    path.relative_to(ROOT)
                ),

            "exists":
                False,

            "rows":
                0,

            "columns":
                0,

            "parseable_datetime_columns":
                "",

            "numeric_columns":
                "",

            "exact_target_time_matches":
                0,
        })

        continue


    fields, rows = read_csv(
        path
    )

    print(
        f"rows={len(rows)}"
    )

    print(
        f"columns={len(fields)}"
    )


    datetime_cols = []
    numeric_cols = []


    for field in fields:

        values = [
            clean(
                r.get(
                    field
                )
            )
            for r in rows
            if clean(
                r.get(
                    field
                )
            )
        ]


        sample_values = []

        for v in values:

            if v not in sample_values:
                sample_values.append(v)

            if len(
                sample_values
            ) >= 3:
                break


        numeric_values = [
            num(v)
            for v in values
        ]

        numeric_values = [
            x
            for x in numeric_values
            if x is not None
        ]


        numeric_fraction = (
            len(
                numeric_values
            )
            /
            len(
                values
            )
            if values
            else 0.0
        )


        datetime_count = sum(
            looks_datetime_text(v)
            for v in values
        )

        datetime_fraction = (
            datetime_count
            /
            len(
                values
            )
            if values
            else 0.0
        )


        if (
            numeric_fraction >= 0.95
            and
            len(
                {
                    round(
                        x,
                        8
                    )
                    for x in numeric_values
                }
            ) >= 2
        ):
            numeric_cols.append(
                field
            )


        if datetime_fraction >= 0.50:
            datetime_cols.append(
                field
            )


        column_rows.append({
            "file":
                str(
                    path.relative_to(ROOT)
                ),

            "column":
                field,

            "nonempty_rows":
                len(
                    values
                ),

            "numeric_fraction":
                numeric_fraction,

            "numeric_unique":
                len(
                    {
                        round(
                            x,
                            8
                        )
                        for x in numeric_values
                    }
                ),

            "numeric_min":
                (
                    min(
                        numeric_values
                    )
                    if numeric_values
                    else ""
                ),

            "numeric_max":
                (
                    max(
                        numeric_values
                    )
                    if numeric_values
                    else ""
                ),

            "datetime_fraction":
                datetime_fraction,

            "sample_1":
                (
                    sample_values[0]
                    if len(
                        sample_values
                    ) >= 1
                    else ""
                ),

            "sample_2":
                (
                    sample_values[1]
                    if len(
                        sample_values
                    ) >= 2
                    else ""
                ),

            "sample_3":
                (
                    sample_values[2]
                    if len(
                        sample_values
                    ) >= 3
                    else ""
                ),
        })


    print()
    print("ALL COLUMNS")

    for field in fields:
        print(
            f"  {field}"
        )


    print()
    print("PARSEABLE DATETIME-LIKE COLUMNS")

    if not datetime_cols:
        print("  NONE")
    else:
        for c in datetime_cols:
            print(
                f"  {c}"
            )


    print()
    print("NUMERIC COLUMNS")

    if not numeric_cols:
        print("  NONE")

    else:

        for c in numeric_cols:

            audit = next(
                r
                for r in column_rows
                if (
                    r[
                        "file"
                    ]
                    ==
                    str(
                        path.relative_to(
                            ROOT
                        )
                    )
                    and
                    r[
                        "column"
                    ]
                    ==
                    c
                )
            )

            print(
                f"  {c:48s} | "
                f"min={audit['numeric_min']} | "
                f"max={audit['numeric_max']} | "
                f"unique={audit['numeric_unique']}"
            )


    print()
    print("FIRST 3 ROWS — SELECTED VALUES")

    for i, r in enumerate(
        rows[:3],
        start=1
    ):

        parts = []

        for field in fields:

            value = clean(
                r.get(
                    field
                )
            )

            if not value:
                continue

            if (
                field in datetime_cols
                or
                field in numeric_cols
                or
                "time" in field.lower()
                or
                "date" in field.lower()
                or
                "track" in field.lower()
                or
                "temp" in field.lower()
                or
                "capture" in field.lower()
            ):

                parts.append(
                    f"{field}={value}"
                )

        print(
            f"  ROW {i}: "
            +
            " | ".join(
                parts
            )
        )


    exact_matches = 0

    if datetime_cols:

        source_times = set()

        for c in datetime_cols:

            for r in rows:

                dt = parse_iso(
                    r.get(c)
                )

                if dt:
                    source_times.add(
                        dt
                    )


        target_dt_set = {
            dt
            for _, _, dt
            in target_times
        }

        exact_matches = len(
            target_dt_set
            &
            source_times
        )


    file_rows.append({
        "file":
            str(
                path.relative_to(ROOT)
            ),

        "exists":
            True,

        "rows":
            len(
                rows
            ),

        "columns":
            len(
                fields
            ),

        "parseable_datetime_columns":
            ";".join(
                datetime_cols
            ),

        "numeric_columns":
            ";".join(
                numeric_cols
            ),

        "exact_target_time_matches":
            exact_matches,
    })


# =============================================================================
# PTSC special inspection
# =============================================================================

print()
print("=" * 150)
print("PTSC TIME-FIELD FORENSICS")
print("=" * 150)


for path in TARGET_FILES[:2]:

    if not path.exists():
        continue

    fields, rows = read_csv(
        path
    )

    print()
    print(
        f"FILE: {path.relative_to(ROOT)}"
    )

    for field in fields:

        fname = field.lower()

        if (
            "time" in fname
            or
            "date" in fname
            or
            "hour" in fname
            or
            "minute" in fname
            or
            "session" in fname
            or
            "capture" in fname
            or
            "source" in fname
        ):

            values = []

            for r in rows:

                v = clean(
                    r.get(
                        field
                    )
                )

                if (
                    v
                    and
                    v not in values
                ):
                    values.append(
                        v
                    )

                if len(
                    values
                ) >= 8:
                    break


            print(
                f"  {field}: "
                +
                " | ".join(
                    values
                )
            )


# =============================================================================
# QA
# =============================================================================

present_count = sum(
    r[
        "exists"
    ]
    for r in file_rows
)

ptsc_present = all(
    path.exists()
    for path in TARGET_FILES[:2]
)

hrrr_present = TARGET_FILES[-1].exists()


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
            "target_times",
        "value":
            len(
                target_times
            ),
        "expected":
            110,
        "status":
            (
                "PASS"
                if len(
                    target_times
                ) == 110
                else "FAIL"
            ),
    },

    {
        "metric":
            "ptsc_sources_present",
        "value":
            ptsc_present,
        "expected":
            True,
        "status":
            (
                "PASS"
                if ptsc_present
                else "FAIL"
            ),
    },

    {
        "metric":
            "canonical_hrrr_present",
        "value":
            hrrr_present,
        "expected":
            True,
        "status":
            (
                "PASS"
                if hrrr_present
                else "FAIL"
            ),
    },

    {
        "metric":
            "target_sources_present",
        "value":
            present_count,
        "expected":
            f">=5",
        "status":
            (
                "PASS"
                if present_count >= 5
                else "FAIL"
            ),
    },

    {
        "metric":
            "schema_only_no_model_fit",
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
        "R4F7C2B",

    "status":
        "R4F7C2B_EXACT_WEATHER_JOIN_SCHEMA_READY",

    "frozen_target_attempts":
        len(
            target_ids
        ),

    "source_files":
        file_rows,

    "goal":
        (
            "Resolve exact PTSC temporal schema and confirm the "
            "already-aligned performance-context / canonical HRRR "
            "schemas before constructing the frozen numeric matrix."
        ),

    "no_model_fit":
        True,
}


OUT_REPORT.write_text(
    json.dumps(
        report,
        indent=2,
        ensure_ascii=False
    ),
    encoding="utf-8"
)


fails = [
    r
    for r in qa_rows
    if r[
        "status"
    ]
    ==
    "FAIL"
]


print()
print("=" * 150)
print("SOURCE SUMMARY")
print("=" * 150)

for r in file_rows:

    print(
        f"{r['file'][:78]:78s} | "
        f"rows={r['rows']:3d} | "
        f"datetime=[{r['parseable_datetime_columns']}] | "
        f"exact_target_matches={r['exact_target_time_matches']}"
    )


print()
print(
    f"QA: "
    f"{len(qa_rows)-len(fails)} PASS | "
    f"0 WARN | "
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
    OUT_COLUMNS.relative_to(ROOT)
)
print(
    OUT_FILES.relative_to(ROOT)
)
print(
    OUT_QA.relative_to(ROOT)
)
print(
    OUT_REPORT.relative_to(ROOT)
)

print()
print(
    "R4F7C2B_EXACT_WEATHER_JOIN_SCHEMA_READY"
)
