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

C0_COLUMNS_PATH = (
    OUT /
    "r4f7c0_numeric_feature_candidate_columns_v1.csv"
)

C0_FILES_PATH = (
    OUT /
    "r4f7c0_numeric_feature_candidate_files_v1.csv"
)

PRIMARY_ATTEMPT_PATH = (
    OUT /
    "r4p1_attempt_four_lap_panel_v1.csv"
)

OUT_AUDIT = (
    OUT /
    "r4f7c1_exact_numeric_feature_schema_audit_v1.csv"
)

OUT_SOURCE = (
    OUT /
    "r4f7c1_numeric_source_resolution_v1.csv"
)

OUT_QA = (
    OUT /
    "r4f7c1_exact_numeric_feature_schema_qa_v1.csv"
)

OUT_REPORT = (
    OUT /
    "r4f7c1_exact_numeric_feature_schema_report_v1.json"
)


RELEVANT_CLASSES = {
    "TRACK_TEMP",
    "AMBIENT_TEMP",
    "HUMIDITY",
    "PRESSURE",
    "WIND",
    "SOLAR_CLOUD",
    "FORECAST",
    "DERIVED_TREND",
    "TIME",
}

BOOLEAN_WORDS = {
    "true",
    "false",
    "yes",
    "no",
    "y",
    "n",
    "t",
    "f",
    "0",
    "1",
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


def classify_name(col):
    c = normalize_col(col)

    classes = []

    if (
        "track" in c
        and
        (
            "temp" in c
            or
            "temperature" in c
        )
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
        }
    ):
        classes.append(
            "HUMIDITY"
        )

    if "pressure" in c:
        classes.append(
            "PRESSURE"
        )

    if (
        "wind" in c
        or
        "gust" in c
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
        "hrrr" in c
        or
        "forecast" in c
        or
        "lead" in c
        or
        "cycle" in c
    ):
        classes.append(
            "FORECAST"
        )

    if (
        "slope" in c
        or
        "trend" in c
        or
        "delta" in c
        or
        "change" in c
    ):
        classes.append(
            "DERIVED_TREND"
        )

    if (
        "time" in c
        or
        c.endswith("_utc")
        or
        "timestamp" in c
    ):
        classes.append(
            "TIME"
        )

    return classes


def semantic_type(values, column_name):
    vals = [
        clean(v)
        for v in values
        if clean(v)
    ]

    if not vals:
        return (
            "EMPTY",
            0,
            0,
            0.0,
        )

    low = {
        v.lower()
        for v in vals
    }

    cname = normalize_col(
        column_name
    )

    if (
        "available" in cname
        or
        "usable" in cname
        or
        "flag" in cname
    ):
        return (
            "AVAILABILITY_OR_BOOLEAN_FLAG",
            len(vals),
            len(low),
            0.0,
        )

    if low.issubset(
        BOOLEAN_WORDS
    ):
        return (
            "BOOLEAN_FLAG",
            len(vals),
            len(low),
            0.0,
        )

    numeric = [
        num(v)
        for v in vals
    ]

    numeric = [
        x
        for x in numeric
        if x is not None
    ]

    fraction = (
        len(numeric)
        /
        len(vals)
    )

    unique_numeric = len(
        {
            round(
                x,
                8
            )
            for x in numeric
        }
    )

    if (
        fraction >= 0.95
        and
        unique_numeric >= 5
    ):
        return (
            "CONTINUOUS_NUMERIC",
            len(vals),
            unique_numeric,
            fraction,
        )

    if (
        fraction >= 0.95
        and
        unique_numeric < 5
    ):
        return (
            "LOW_CARDINALITY_NUMERIC",
            len(vals),
            unique_numeric,
            fraction,
        )

    if (
        "time" in cname
        or
        "utc" in cname
        or
        "timestamp" in cname
    ):
        return (
            "TIME_OR_DATETIME",
            len(vals),
            len(low),
            fraction,
        )

    return (
        "TEXT_OR_MIXED",
        len(vals),
        len(low),
        fraction,
    )


for path in [
    MANIFEST_PATH,
    C0_COLUMNS_PATH,
    C0_FILES_PATH,
    PRIMARY_ATTEMPT_PATH,
]:

    if not path.exists():
        raise SystemExit(
            f"MISSING INPUT: {path}"
        )


_, manifest = read_csv(
    MANIFEST_PATH
)

_, c0_columns = read_csv(
    C0_COLUMNS_PATH
)

_, c0_files = read_csv(
    C0_FILES_PATH
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


print("=" * 144)
print("R4F7C1 — EXACT NUMERIC FEATURE SCHEMA AUDIT")
print("=" * 144)

print(
    f"Model-facing target attempts: {len(target_ids)}"
)


# =============================================================================
# Select potentially relevant source files from C0.
# =============================================================================

candidate_names = []

for r in c0_files:

    try:
        thermal_score = int(
            float(
                clean(
                    r.get(
                        "thermal_score"
                    )
                )
                or
                0
            )
        )

    except Exception:
        thermal_score = 0

    try:
        total_score = int(
            float(
                clean(
                    r.get(
                        "total_score"
                    )
                )
                or
                0
            )
        )

    except Exception:
        total_score = 0

    if (
        thermal_score > 0
        or
        total_score > 15
    ):
        candidate_names.append(
            clean(
                r.get(
                    "file"
                )
            )
        )


# Force known high-value sources into audit.
for name in [
    "r4p1_attempt_four_lap_panel_v1.csv",
    "r4f3b_shared_state_linkage_thermal_fixed_v1.csv",
    "r4f4_decision_window_residual_context_v1.csv",
    "r4p5_decision_safe_forecast_scenarios_v1.csv",
    "r4p6_decision_safe_conditional_dataset_v1.csv",
    "r4p8_track_temperature_training_dataset_v1.csv",
    "r4p2_environment_linked_transitions_v1.csv",
    "r4p2_multi_run_transitions_v1.csv",
]:

    if name not in candidate_names:
        candidate_names.append(
            name
        )


audit_rows = []
source_rows = []


for name in candidate_names:

    path = OUT / name

    if not path.exists():
        continue

    try:
        fields, rows = read_csv(
            path
        )

    except Exception:
        continue

    attempt_col = (
        "attempt_id"
        if "attempt_id" in fields
        else None
    )


    if attempt_col:

        target_rows = [
            r
            for r in rows
            if clean(
                r.get(
                    attempt_col
                )
            )
            in target_ids
        ]

    else:

        target_rows = rows


    real_numeric_feature_count = 0
    boolean_feature_count = 0
    relevant_column_count = 0


    for field in fields:

        classes = classify_name(
            field
        )

        if not (
            set(classes)
            &
            RELEVANT_CLASSES
        ):
            continue

        relevant_column_count += 1

        values = [
            r.get(
                field
            )
            for r in target_rows
        ]

        (
            semantic,
            nonempty,
            unique_count,
            numeric_fraction,
        ) = semantic_type(
            values,
            field
        )


        numeric_values = [
            num(v)
            for v in values
        ]

        numeric_values = [
            x
            for x in numeric_values
            if x is not None
        ]


        numeric_min = (
            min(
                numeric_values
            )
            if numeric_values
            else ""
        )

        numeric_max = (
            max(
                numeric_values
            )
            if numeric_values
            else ""
        )


        if semantic == "CONTINUOUS_NUMERIC":
            real_numeric_feature_count += 1

        if semantic in {
            "BOOLEAN_FLAG",
            "AVAILABILITY_OR_BOOLEAN_FLAG",
        }:
            boolean_feature_count += 1


        audit_rows.append({
            "file":
                name,

            "column":
                field,

            "classes":
                ";".join(
                    classes
                ),

            "semantic_type":
                semantic,

            "target_rows":
                len(
                    target_rows
                ),

            "nonempty":
                nonempty,

            "coverage":
                (
                    nonempty
                    /
                    len(
                        target_rows
                    )
                    if target_rows
                    else 0.0
                ),

            "unique_values":
                unique_count,

            "numeric_fraction":
                numeric_fraction,

            "numeric_min":
                numeric_min,

            "numeric_max":
                numeric_max,

            "direct_attempt_join":
                bool(
                    attempt_col
                ),
        })


    source_rows.append({
        "file":
            name,

        "rows":
            len(
                rows
            ),

        "direct_attempt_join":
            bool(
                attempt_col
            ),

        "target_attempt_rows":
            (
                len(
                    target_rows
                )
                if attempt_col
                else ""
            ),

        "relevant_columns":
            relevant_column_count,

        "continuous_numeric_features":
            real_numeric_feature_count,

        "boolean_or_availability_features":
            boolean_feature_count,
    })


# =============================================================================
# Resolve direct source truth.
# =============================================================================

p1_relevant = [
    r
    for r in audit_rows
    if r[
        "file"
    ]
    ==
    "r4p1_attempt_four_lap_panel_v1.csv"
]

p1_continuous = [
    r
    for r in p1_relevant
    if (
        r[
            "semantic_type"
        ]
        ==
        "CONTINUOUS_NUMERIC"
        and
        bool(
            set(
                clean(
                    r[
                        "classes"
                    ]
                ).split(
                    ";"
                )
            )
            &
            {
                "TRACK_TEMP",
                "AMBIENT_TEMP",
                "HUMIDITY",
                "PRESSURE",
                "WIND",
                "SOLAR_CLOUD",
                "FORECAST",
                "DERIVED_TREND",
            }
        )
    )
]

p1_flags = [
    r
    for r in p1_relevant
    if r[
        "semantic_type"
    ]
    in {
        "BOOLEAN_FLAG",
        "AVAILABILITY_OR_BOOLEAN_FLAG",
    }
]


# =============================================================================
# Find actual numeric weather source candidates.
# =============================================================================

actual_numeric_sources = []

for source in source_rows:

    if source[
        "continuous_numeric_features"
    ] > 0:

        actual_numeric_sources.append(
            source
        )


actual_numeric_sources.sort(
    key=lambda r: (
        -r[
            "continuous_numeric_features"
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


# =============================================================================
# QA
# =============================================================================

qa_rows = [
    {
        "metric":
            "model_target_attempts",
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
            "primary_attempt_source_audited",
        "value":
            bool(
                p1_relevant
            ),
        "expected":
            True,
        "status":
            (
                "PASS"
                if p1_relevant
                else "FAIL"
            ),
    },

    {
        "metric":
            "numeric_feature_sources_found",
        "value":
            len(
                actual_numeric_sources
            ),
        "expected":
            ">0",
        "status":
            (
                "PASS"
                if actual_numeric_sources
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


resolution = (
    "DIRECT_NUMERIC_SOURCE_AVAILABLE"
    if p1_continuous
    else
    "MULTI_SOURCE_TIME_SAFE_JOIN_REQUIRED"
)


report = {
    "phase":
        "R4F7C1",

    "status":
        "R4F7C1_EXACT_NUMERIC_FEATURE_SCHEMA_READY",

    "primary_attempt_source":
        "r4p1_attempt_four_lap_panel_v1.csv",

    "primary_source_real_numeric_weather_features":
        [
            r[
                "column"
            ]
            for r in p1_continuous
        ],

    "primary_source_boolean_or_availability_columns":
        [
            r[
                "column"
            ]
            for r in p1_flags
        ],

    "resolved_architecture":
        resolution,

    "actual_numeric_weather_sources":
        actual_numeric_sources,

    "important_rule":
        (
            "Availability/usable flags are metadata and may not be "
            "used as substitutes for actual numeric thermal or "
            "forecast measurements."
        ),

    "next_phase":
        (
            "R4F7C2 will construct a deterministic leakage-safe "
            "numeric model matrix using only verified continuous "
            "weather/thermal features and the frozen 110 observation "
            "development+validation universe."
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
print("=" * 144)
print("PRIMARY ATTEMPT SOURCE — EXACT RELEVANT COLUMNS")
print("=" * 144)

for r in p1_relevant:

    print(
        f"{r['column'][:48]:48s} | "
        f"{r['classes'][:28]:28s} | "
        f"{r['semantic_type']:32s} | "
        f"coverage={r['coverage']:.3f} | "
        f"unique={r['unique_values']}"
    )


print()
print("=" * 144)
print("PRIMARY ATTEMPT SOURCE — VERIFIED CONTINUOUS WEATHER FEATURES")
print("=" * 144)

if not p1_continuous:

    print("NONE")

else:

    for r in p1_continuous:

        print(
            f"{r['column']:52s} | "
            f"{r['classes']:28s} | "
            f"coverage={r['coverage']:.3f} | "
            f"range={r['numeric_min']} .. {r['numeric_max']}"
        )


print()
print("=" * 144)
print("ACTUAL NUMERIC WEATHER SOURCE CANDIDATES")
print("=" * 144)

if not actual_numeric_sources:

    print("NONE")

else:

    for r in actual_numeric_sources[:20]:

        print(
            f"{r['file'][:76]:76s} | "
            f"continuous={r['continuous_numeric_features']:3d} | "
            f"flags={r['boolean_or_availability_features']:3d} | "
            f"direct_attempt_join={r['direct_attempt_join']} | "
            f"target_rows={r['target_attempt_rows']}"
        )


print()
print("=" * 144)
print("RESOLVED MODEL-MATRIX ARCHITECTURE")
print("=" * 144)

print(
    resolution
)

if resolution == "MULTI_SOURCE_TIME_SAFE_JOIN_REQUIRED":

    print(
        "r4p1 provides the attempt spine, but verified numeric "
        "thermal/forecast features must be joined from other sources."
    )

else:

    print(
        "r4p1 contains verified continuous numeric weather features "
        "suitable for direct model-matrix construction."
    )


print()
print("=" * 144)
print("VERIFIED AVAILABILITY/BOOLEAN FLAGS IN PRIMARY SOURCE")
print("=" * 144)

if not p1_flags:

    print("NONE")

else:

    for r in p1_flags:

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
    "R4F7C1_EXACT_NUMERIC_FEATURE_SCHEMA_READY"
)
