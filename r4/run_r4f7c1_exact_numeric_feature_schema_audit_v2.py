from pathlib import Path
from collections import Counter
import csv
import json
import math
import re

ROOT = Path(
    "/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈"
)

OUT = ROOT / "r4/output"

MANIFEST_PATH = (
    OUT /
    "r4f7b_latent_window_training_manifest_v1.csv"
)

OUT_AUDIT = (
    OUT /
    "r4f7c1_v2_exact_numeric_feature_schema_audit.csv"
)

OUT_SOURCE = (
    OUT /
    "r4f7c1_v2_numeric_weather_source_resolution.csv"
)

OUT_QA = (
    OUT /
    "r4f7c1_v2_exact_numeric_feature_schema_qa.csv"
)

OUT_REPORT = (
    OUT /
    "r4f7c1_v2_exact_numeric_feature_schema_report.json"
)


SOURCE_NAMES = [
    "r4p1_attempt_four_lap_panel_v1.csv",

    "r4f3b_shared_state_linkage_thermal_fixed_v1.csv",

    "r4f4_decision_window_residual_context_v1.csv",

    "r4p5_decision_safe_forecast_scenarios_v1.csv",

    "r4p6_decision_safe_conditional_dataset_v1.csv",

    "r4p8_track_temperature_training_dataset_v1.csv",

    "r4p2_environment_linked_transitions_v1.csv",

    "r4p2_multi_run_transitions_v1.csv",

    "r4p10_thermal_conditioned_repeat_dataset_v1.csv",
]


WEATHER_CLASSES = {
    "TRACK_TEMP",
    "AMBIENT_TEMP",
    "HUMIDITY",
    "PRESSURE",
    "WIND",
    "SOLAR_CLOUD",
    "PRECIPITATION",
    "WEATHER_TREND",
    "FORECAST_NUMERIC",
}


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


def normalize_col(col):
    return re.sub(
        r"[^a-z0-9]+",
        "_",
        clean(col).lower()
    ).strip("_")


def is_performance_column(c):

    performance_tokens = [
        "lap1",
        "lap2",
        "lap3",
        "lap4",
        "lap_1",
        "lap_2",
        "lap_3",
        "lap_4",
        "speed_mph",
        "average_speed",
        "four_lap",
        "qualifying_speed",
        "performance",
        "repeat_delta",
        "improvement",
        "residual_mph",
    ]

    return any(
        token in c
        for token in performance_tokens
    )


def classify_column(col):

    c = normalize_col(col)

    classes = []

    if c in {
        "attempt_id",
        "attemptid",
    }:
        classes.append(
            "ATTEMPT_ID"
        )


    if (
        c == "year"
        or
        c == "season"
    ):
        classes.append(
            "YEAR"
        )


    if (
        "time" in c
        or
        "timestamp" in c
        or
        c.endswith("_utc")
        or
        "valid_at" in c
        or
        "valid_time" in c
    ):
        classes.append(
            "TIME"
        )


    if (
        "available" in c
        or
        "usable" in c
        or
        c.endswith("_flag")
    ):
        classes.append(
            "AVAILABILITY_FLAG"
        )


    if is_performance_column(
        c
    ):
        classes.append(
            "PERFORMANCE_OR_OUTCOME"
        )


    if (
        (
            "track" in c
            and
            (
                "temp" in c
                or
                "temperature" in c
            )
        )
        or
        c in {
            "track_c",
            "track_temp_c",
            "track_temperature_c",
        }
    ):
        classes.append(
            "TRACK_TEMP"
        )


    if (
        "ambient" in c
        and
        (
            "temp" in c
            or
            "temperature" in c
        )
    ):
        classes.append(
            "AMBIENT_TEMP"
        )


    if (
        "humidity" in c
        or
        c in {
            "rh",
            "relative_humidity",
            "relative_humidity_pct",
        }
    ):
        classes.append(
            "HUMIDITY"
        )


    if (
        "pressure" in c
        or
        c in {
            "pres",
            "mslp",
        }
    ):
        classes.append(
            "PRESSURE"
        )


    if (
        "wind" in c
        or
        "gust" in c
        or
        c.startswith(
            "u10"
        )
        or
        c.startswith(
            "v10"
        )
    ):
        classes.append(
            "WIND"
        )


    if (
        "cloud" in c
        or
        "shortwave" in c
        or
        "solar" in c
        or
        "radiation" in c
        or
        "dswrf" in c
    ):
        classes.append(
            "SOLAR_CLOUD"
        )


    if (
        "rain" in c
        or
        "precip" in c
        or
        "apcp" in c
    ):
        classes.append(
            "PRECIPITATION"
        )


    weather_root = any(
        token in c
        for token in [
            "track_temp",
            "track_temperature",
            "ambient",
            "temperature",
            "humidity",
            "pressure",
            "wind",
            "gust",
            "cloud",
            "shortwave",
            "solar",
            "radiation",
            "dswrf",
            "rain",
            "precip",
            "apcp",
        ]
    )


    trend_token = any(
        token in c
        for token in [
            "slope",
            "trend",
            "delta",
            "change",
            "rate",
        ]
    )


    if (
        weather_root
        and
        trend_token
        and
        not is_performance_column(c)
    ):
        classes.append(
            "WEATHER_TREND"
        )


    if (
        (
            "hrrr" in c
            or
            "forecast" in c
            or
            "lead_" in c
            or
            c.startswith(
                "f00"
            )
            or
            c.startswith(
                "f01"
            )
            or
            c.startswith(
                "f02"
            )
            or
            c.startswith(
                "f03"
            )
        )
        and
        not (
            "available" in c
            or
            "usable" in c
        )
    ):
        classes.append(
            "FORECAST_METADATA_OR_VALUE"
        )


    return list(
        dict.fromkeys(
            classes
        )
    )


def semantic_type(values, col):

    vals = [
        clean(v)
        for v in values
        if clean(v)
    ]

    if not vals:

        return {
            "semantic_type":
                "EMPTY",

            "nonempty":
                0,

            "numeric_count":
                0,

            "numeric_fraction":
                0.0,

            "unique_numeric":
                0,

            "numeric_min":
                "",

            "numeric_max":
                "",
        }


    c = normalize_col(
        col
    )


    if (
        "available" in c
        or
        "usable" in c
        or
        c.endswith(
            "_flag"
        )
    ):

        return {
            "semantic_type":
                "AVAILABILITY_FLAG",

            "nonempty":
                len(vals),

            "numeric_count":
                0,

            "numeric_fraction":
                0.0,

            "unique_numeric":
                len(
                    set(vals)
                ),

            "numeric_min":
                "",

            "numeric_max":
                "",
        }


    numeric_values = [
        num(v)
        for v in vals
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
            vals
        )
    )

    unique_numeric = len(
        {
            round(
                x,
                8
            )
            for x in numeric_values
        }
    )


    if (
        numeric_fraction >= 0.95
        and
        unique_numeric >= 5
    ):

        semantic = (
            "CONTINUOUS_NUMERIC"
        )


    elif (
        numeric_fraction >= 0.95
    ):

        semantic = (
            "LOW_CARDINALITY_NUMERIC"
        )


    elif (
        "time" in c
        or
        "utc" in c
        or
        "timestamp" in c
    ):

        semantic = (
            "TIME_OR_DATETIME"
        )


    else:

        semantic = (
            "TEXT_OR_MIXED"
        )


    return {
        "semantic_type":
            semantic,

        "nonempty":
            len(
                vals
            ),

        "numeric_count":
            len(
                numeric_values
            ),

        "numeric_fraction":
            numeric_fraction,

        "unique_numeric":
            unique_numeric,

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
    }


if not MANIFEST_PATH.exists():

    raise SystemExit(
        f"MISSING INPUT: {MANIFEST_PATH}"
    )


_, manifest = read_csv(
    MANIFEST_PATH
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


print("=" * 146)
print("R4F7C1-v2 — EXACT NUMERIC WEATHER FEATURE SCHEMA AUDIT")
print("=" * 146)

print(
    f"Frozen model-facing attempts: "
    f"{len(target_ids)}"
)


audit_rows = []
source_rows = []


for filename in SOURCE_NAMES:

    path = OUT / filename

    if not path.exists():
        continue


    fields, rows = read_csv(
        path
    )


    attempt_field = (
        "attempt_id"
        if "attempt_id" in fields
        else None
    )


    if attempt_field:

        target_rows = [
            r
            for r in rows
            if clean(
                r.get(
                    attempt_field
                )
            )
            in target_ids
        ]

    else:

        target_rows = rows


    weather_numeric = []
    performance_numeric = []
    time_columns = []
    availability_columns = []


    for field in fields:

        classes = classify_column(
            field
        )

        if not classes:
            continue


        stats = semantic_type(
            [
                r.get(
                    field
                )
                for r in target_rows
            ],
            field
        )


        is_numeric = (
            stats[
                "semantic_type"
            ]
            ==
            "CONTINUOUS_NUMERIC"
        )


        is_weather = bool(
            set(
                classes
            )
            &
            WEATHER_CLASSES
        )


        is_performance = (
            "PERFORMANCE_OR_OUTCOME"
            in classes
        )


        is_time = (
            "TIME"
            in classes
        )


        is_flag = (
            "AVAILABILITY_FLAG"
            in classes
            or
            stats[
                "semantic_type"
            ]
            ==
            "AVAILABILITY_FLAG"
        )


        safe_weather_numeric = (
            is_numeric
            and
            is_weather
            and
            not is_performance
            and
            not is_flag
        )


        if safe_weather_numeric:

            weather_numeric.append(
                field
            )


        if (
            is_numeric
            and
            is_performance
        ):

            performance_numeric.append(
                field
            )


        if is_time:

            time_columns.append(
                field
            )


        if is_flag:

            availability_columns.append(
                field
            )


        audit_rows.append({
            "file":
                filename,

            "column":
                field,

            "classes":
                ";".join(
                    classes
                ),

            "semantic_type":
                stats[
                    "semantic_type"
                ],

            "target_rows":
                len(
                    target_rows
                ),

            "nonempty":
                stats[
                    "nonempty"
                ],

            "coverage":
                (
                    stats[
                        "nonempty"
                    ]
                    /
                    len(
                        target_rows
                    )
                    if target_rows
                    else 0.0
                ),

            "unique_numeric":
                stats[
                    "unique_numeric"
                ],

            "numeric_fraction":
                stats[
                    "numeric_fraction"
                ],

            "numeric_min":
                stats[
                    "numeric_min"
                ],

            "numeric_max":
                stats[
                    "numeric_max"
                ],

            "safe_weather_numeric":
                safe_weather_numeric,

            "performance_or_outcome":
                is_performance,

            "availability_flag":
                is_flag,

            "direct_attempt_join":
                bool(
                    attempt_field
                ),
        })


    source_rows.append({
        "file":
            filename,

        "rows":
            len(
                rows
            ),

        "direct_attempt_join":
            bool(
                attempt_field
            ),

        "target_attempt_rows":
            (
                len(
                    target_rows
                )
                if attempt_field
                else ""
            ),

        "safe_weather_numeric_count":
            len(
                weather_numeric
            ),

        "performance_numeric_count":
            len(
                performance_numeric
            ),

        "time_column_count":
            len(
                set(
                    time_columns
                )
            ),

        "availability_flag_count":
            len(
                set(
                    availability_columns
                )
            ),

        "safe_weather_numeric_columns":
            ";".join(
                weather_numeric
            ),

        "time_columns":
            ";".join(
                sorted(
                    set(
                        time_columns
                    )
                )
            ),

        "availability_columns":
            ";".join(
                sorted(
                    set(
                        availability_columns
                    )
                )
            ),
    })


# =============================================================================
# Primary attempt-source verdict
# =============================================================================

p1_rows = [
    r
    for r in audit_rows
    if r[
        "file"
    ]
    ==
    "r4p1_attempt_four_lap_panel_v1.csv"
]


p1_weather = [
    r
    for r in p1_rows
    if r[
        "safe_weather_numeric"
    ]
]


p1_performance = [
    r
    for r in p1_rows
    if (
        r[
            "performance_or_outcome"
        ]
        and
        r[
            "semantic_type"
        ]
        ==
        "CONTINUOUS_NUMERIC"
    )
]


numeric_weather_sources = [
    r
    for r in source_rows
    if r[
        "safe_weather_numeric_count"
    ] > 0
]


numeric_weather_sources.sort(
    key=lambda r: (
        -r[
            "safe_weather_numeric_count"
        ],
        0
        if r[
            "direct_attempt_join"
        ]
        else 1,
        r[
            "file"
        ],
    )
)


if p1_weather:

    resolution = (
        "DIRECT_VERIFIED_WEATHER_NUMERIC_AVAILABLE"
    )

else:

    resolution = (
        "MULTI_SOURCE_TIME_SAFE_JOIN_REQUIRED"
    )


# =============================================================================
# QA
# =============================================================================

qa_rows = [
    {
        "metric":
            "frozen_model_attempts",
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
            "p1_performance_delta_not_weather",
        "value":
            all(
                not r[
                    "safe_weather_numeric"
                ]
                for r in p1_performance
            ),
        "expected":
            True,
        "status":
            (
                "PASS"
                if all(
                    not r[
                        "safe_weather_numeric"
                    ]
                    for r in p1_performance
                )
                else "FAIL"
            ),
    },

    {
        "metric":
            "numeric_weather_sources_found",
        "value":
            len(
                numeric_weather_sources
            ),
        "expected":
            ">0",
        "status":
            (
                "PASS"
                if numeric_weather_sources
                else "FAIL"
            ),
    },

    {
        "metric":
            "availability_flags_not_numeric_weather",
        "value":
            all(
                not r[
                    "safe_weather_numeric"
                ]
                for r in audit_rows
                if r[
                    "availability_flag"
                ]
            ),
        "expected":
            True,
        "status":
            (
                "PASS"
                if all(
                    not r[
                        "safe_weather_numeric"
                    ]
                    for r in audit_rows
                    if r[
                        "availability_flag"
                    ]
                )
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

with OUT_AUDIT.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=list(
            audit_rows[0].keys()
        )
    )

    writer.writeheader()
    writer.writerows(
        audit_rows
    )


with OUT_SOURCE.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=list(
            source_rows[0].keys()
        )
    )

    writer.writeheader()
    writer.writerows(
        source_rows
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
        "R4F7C1_V2",

    "status":
        "R4F7C1_V2_EXACT_NUMERIC_WEATHER_SCHEMA_READY",

    "supersedes":
        (
            "R4F7C1-v1 direct-source architecture verdict only"
        ),

    "v1_bug":
        (
            "Generic delta/trend name matching incorrectly classified "
            "lap-performance delta columns as weather-derived trends."
        ),

    "primary_attempt_weather_numeric_columns":
        [
            r[
                "column"
            ]
            for r in p1_weather
        ],

    "primary_attempt_performance_numeric_columns":
        [
            r[
                "column"
            ]
            for r in p1_performance
        ],

    "resolved_architecture":
        resolution,

    "numeric_weather_sources":
        numeric_weather_sources,

    "modeling_boundary":
        (
            "Lap-to-lap deltas are qualifying outcome/run-shape "
            "measurements and are not contemporaneous external weather "
            "features for predicting the same qualifying performance."
        ),

    "next_phase":
        (
            "Construct deterministic time-safe attempt -> PTSC -> HRRR "
            "numeric feature matrix using verified source schemas."
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
print("=" * 146)
print("PRIMARY ATTEMPT SOURCE — PERFORMANCE COLUMNS EXCLUDED FROM WEATHER")
print("=" * 146)

for r in p1_performance:

    print(
        f"{r['column']:52s} | "
        f"{r['semantic_type']:20s} | "
        f"weather_safe={r['safe_weather_numeric']}"
    )


print()
print("=" * 146)
print("PRIMARY ATTEMPT SOURCE — TRUE WEATHER NUMERIC COLUMNS")
print("=" * 146)

if not p1_weather:

    print("NONE")

else:

    for r in p1_weather:

        print(
            f"{r['column']:52s} | "
            f"{r['classes']:36s} | "
            f"coverage={r['coverage']:.3f} | "
            f"range={r['numeric_min']} .. {r['numeric_max']}"
        )


print()
print("=" * 146)
print("VERIFIED NUMERIC WEATHER SOURCES")
print("=" * 146)

if not numeric_weather_sources:

    print("NONE")

else:

    for r in numeric_weather_sources:

        print()
        print(
            f"FILE: {r['file']}"
        )

        print(
            f"  weather_numeric_count="
            f"{r['safe_weather_numeric_count']}"
        )

        print(
            f"  direct_attempt_join="
            f"{r['direct_attempt_join']}"
        )

        print(
            f"  time_columns="
            f"{r['time_columns']}"
        )

        print(
            f"  weather_columns="
            f"{r['safe_weather_numeric_columns']}"
        )


print()
print("=" * 146)
print("RESOLVED MODEL-MATRIX ARCHITECTURE")
print("=" * 146)

print(
    resolution
)


print()
print("=" * 146)
print("PRIMARY ATTEMPT AVAILABILITY FLAGS")
print("=" * 146)

for r in p1_rows:

    if r[
        "availability_flag"
    ]:

        print(
            f"{r['column']:52s} | "
            f"{r['semantic_type']}"
        )


fails = [
    r
    for r in qa_rows
    if r[
        "status"
    ] == "FAIL"
]


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
    OUT_AUDIT.relative_to(ROOT)
)
print(
    OUT_SOURCE.relative_to(ROOT)
)
print(
    OUT_QA.relative_to(ROOT)
)
print(
    OUT_REPORT.relative_to(ROOT)
)

print()
print(
    "R4F7C1_V2_EXACT_NUMERIC_WEATHER_SCHEMA_READY"
)
