from pathlib import Path
from collections import Counter, defaultdict
import csv
import json
import re
import math

ROOT = Path(
    "/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈"
)

OUT = ROOT / "r4/output"

MANIFEST_PATH = (
    OUT /
    "r4f7b_latent_window_training_manifest_v1.csv"
)

READINESS_PATH = (
    OUT /
    "r4f7a_v2_expanded_latent_window_input_readiness_rows.csv"
)

OUT_FILES = (
    OUT /
    "r4f7c0_numeric_feature_candidate_files_v1.csv"
)

OUT_COLUMNS = (
    OUT /
    "r4f7c0_numeric_feature_candidate_columns_v1.csv"
)

OUT_JOIN = (
    OUT /
    "r4f7c0_numeric_feature_joinability_v1.csv"
)

OUT_QA = (
    OUT /
    "r4f7c0_numeric_feature_source_resolution_qa_v1.csv"
)

OUT_REPORT = (
    OUT /
    "r4f7c0_numeric_feature_source_resolution_report_v1.json"
)


CORE_YEARS = {
    2020,
    2021,
    2023,
}

VALIDATION_YEAR = 2024


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
        return None

    return None


def year_int(v):
    x = num(v)

    if x is None:
        return None

    return int(x)


def read_csv(path, limit=None):
    rows = []

    with path.open(
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as f:

        reader = csv.DictReader(f)

        fieldnames = (
            reader.fieldnames
            or
            []
        )

        for i, r in enumerate(reader):

            rows.append(r)

            if (
                limit is not None
                and
                i + 1 >= limit
            ):
                break

    return (
        fieldnames,
        rows,
    )


def normalized_col(col):
    return re.sub(
        r"[^a-z0-9]+",
        "_",
        clean(col).lower()
    ).strip("_")


def classify_column(col):
    c = normalized_col(col)

    classes = []

    if c in {
        "attempt_id",
        "attemptid",
    }:
        classes.append(
            "ATTEMPT_ID"
        )

    if (
        "driver" in c
        and
        (
            "name" in c
            or
            "key" in c
        )
    ):
        classes.append(
            "DRIVER_IDENTITY"
        )

    if c in {
        "year",
        "season",
    }:
        classes.append(
            "YEAR"
        )

    if (
        "time_point" in c
        or
        "timestamp" in c
        or
        c.endswith("_utc")
        or
        "event_time" in c
        or
        "valid_time" in c
        or
        "forecast_time" in c
    ):
        classes.append(
            "TIME"
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
        }
    ):
        classes.append(
            "HUMIDITY"
        )

    if (
        "pressure" in c
        or
        "pres" == c
    ):
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
        "delta" in c
        or
        "trend" in c
        or
        "change" in c
    ):
        classes.append(
            "DERIVED_TREND"
        )

    if (
        "speed" in c
        and
        "reference" not in c
    ):
        classes.append(
            "PERFORMANCE"
        )

    if "reference" in c:
        classes.append(
            "REFERENCE"
        )

    return classes


if not MANIFEST_PATH.exists():
    raise SystemExit(
        f"MISSING INPUT: {MANIFEST_PATH}"
    )

if not READINESS_PATH.exists():
    raise SystemExit(
        f"MISSING INPUT: {READINESS_PATH}"
    )


manifest_fields, manifest = read_csv(
    MANIFEST_PATH
)

_, readiness = read_csv(
    READINESS_PATH
)


core_rows = [
    r
    for r in manifest
    if (
        clean(
            r.get(
                "split_role"
            )
        ) == "DEVELOPMENT"
        and
        truthy(
            r.get(
                "model_eligible"
            )
        )
    )
]

validation_rows = [
    r
    for r in manifest
    if (
        clean(
            r.get(
                "split_role"
            )
        ) == "VALIDATION_ONLY"
        and
        truthy(
            r.get(
                "model_eligible"
            )
        )
    )
]

target_attempt_ids = {
    clean(
        r.get(
            "attempt_id"
        )
    )
    for r in (
        core_rows
        +
        validation_rows
    )
    if clean(
        r.get(
            "attempt_id"
        )
    )
}


print("=" * 142)
print("R4F7C0 — NUMERIC FEATURE SOURCE RESOLUTION")
print("=" * 142)

print(
    f"Core model rows: {len(core_rows)}"
)

print(
    f"Validation rows: {len(validation_rows)}"
)

print(
    f"Target attempt IDs: {len(target_attempt_ids)}"
)


# =============================================================================
# Scan CSVs
# =============================================================================

candidate_files = []
candidate_columns = []
join_rows = []


exclude_names = {
    OUT_FILES.name,
    OUT_COLUMNS.name,
    OUT_JOIN.name,
    OUT_QA.name,
}


csv_paths = sorted(
    OUT.glob(
        "*.csv"
    )
)


for path in csv_paths:

    if path.name in exclude_names:
        continue

    try:

        fields, sample = read_csv(
            path,
            limit=500
        )

    except Exception:
        continue

    if not fields:
        continue


    class_counter = Counter()

    for field in fields:

        classes = classify_column(
            field
        )

        for cls in classes:
            class_counter[
                cls
            ] += 1

        if classes:

            numeric_count = 0
            nonempty_count = 0

            for r in sample:

                value = clean(
                    r.get(
                        field
                    )
                )

                if not value:
                    continue

                nonempty_count += 1

                if num(value) is not None:
                    numeric_count += 1


            candidate_columns.append({
                "file":
                    path.name,

                "column":
                    field,

                "classes":
                    ";".join(
                        classes
                    ),

                "sample_nonempty":
                    nonempty_count,

                "sample_numeric":
                    numeric_count,

                "numeric_fraction":
                    (
                        numeric_count
                        /
                        nonempty_count
                        if nonempty_count
                        else 0.0
                    ),
            })


    thermal_score = (
        5 * class_counter[
            "TRACK_TEMP"
        ]
        +
        3 * class_counter[
            "AMBIENT_TEMP"
        ]
        +
        2 * class_counter[
            "HUMIDITY"
        ]
        +
        2 * class_counter[
            "PRESSURE"
        ]
        +
        2 * class_counter[
            "WIND"
        ]
        +
        2 * class_counter[
            "SOLAR_CLOUD"
        ]
        +
        3 * class_counter[
            "FORECAST"
        ]
        +
        2 * class_counter[
            "DERIVED_TREND"
        ]
    )


    identity_score = (
        5 * class_counter[
            "ATTEMPT_ID"
        ]
        +
        2 * class_counter[
            "TIME"
        ]
        +
        class_counter[
            "YEAR"
        ]
        +
        class_counter[
            "DRIVER_IDENTITY"
        ]
    )


    total_score = (
        thermal_score
        +
        identity_score
    )


    if total_score <= 0:
        continue


    attempt_field = None

    for field in fields:

        if (
            "ATTEMPT_ID"
            in classify_column(
                field
            )
        ):
            attempt_field = field
            break


    overlap = 0
    unique_attempts = 0

    if attempt_field:

        values = {
            clean(
                r.get(
                    attempt_field
                )
            )
            for r in sample
            if clean(
                r.get(
                    attempt_field
                )
            )
        }

        unique_attempts = len(
            values
        )

        overlap = len(
            values
            &
            target_attempt_ids
        )


    candidate_files.append({
        "file":
            path.name,

        "sample_rows":
            len(
                sample
            ),

        "column_count":
            len(
                fields
            ),

        "thermal_score":
            thermal_score,

        "identity_score":
            identity_score,

        "total_score":
            total_score,

        "track_temp_cols":
            class_counter[
                "TRACK_TEMP"
            ],

        "forecast_cols":
            class_counter[
                "FORECAST"
            ],

        "trend_cols":
            class_counter[
                "DERIVED_TREND"
            ],

        "time_cols":
            class_counter[
                "TIME"
            ],

        "attempt_id_cols":
            class_counter[
                "ATTEMPT_ID"
            ],

        "attempt_overlap_sample":
            overlap,

        "sample_unique_attempt_ids":
            unique_attempts,
    })


# =============================================================================
# Full join audit for files that actually contain attempt_id
# =============================================================================

for file_row in candidate_files:

    if file_row[
        "attempt_id_cols"
    ] <= 0:
        continue

    path = (
        OUT /
        file_row[
            "file"
        ]
    )

    try:

        fields, all_rows = read_csv(
            path
        )

    except Exception:
        continue


    attempt_field = None

    for field in fields:

        if (
            "ATTEMPT_ID"
            in classify_column(
                field
            )
        ):
            attempt_field = field
            break

    if not attempt_field:
        continue


    ids = {
        clean(
            r.get(
                attempt_field
            )
        )
        for r in all_rows
        if clean(
            r.get(
                attempt_field
            )
        )
    }


    core_ids = {
        clean(
            r.get(
                "attempt_id"
            )
        )
        for r in core_rows
    }

    validation_ids = {
        clean(
            r.get(
                "attempt_id"
            )
        )
        for r in validation_rows
    }


    core_overlap = len(
        ids
        &
        core_ids
    )

    val_overlap = len(
        ids
        &
        validation_ids
    )


    join_rows.append({
        "file":
            path.name,

        "attempt_id_column":
            attempt_field,

        "file_rows":
            len(
                all_rows
            ),

        "unique_attempt_ids":
            len(
                ids
            ),

        "core_overlap":
            core_overlap,

        "core_total":
            len(
                core_ids
            ),

        "core_coverage":
            (
                core_overlap
                /
                len(
                    core_ids
                )
                if core_ids
                else 0.0
            ),

        "validation_overlap":
            val_overlap,

        "validation_total":
            len(
                validation_ids
            ),

        "validation_coverage":
            (
                val_overlap
                /
                len(
                    validation_ids
                )
                if validation_ids
                else 0.0
            ),

        "thermal_score":
            file_row[
                "thermal_score"
            ],

        "forecast_cols":
            file_row[
                "forecast_cols"
            ],

        "track_temp_cols":
            file_row[
                "track_temp_cols"
            ],
    })


# =============================================================================
# Rank sources
# =============================================================================

candidate_files.sort(
    key=lambda r: (
        -r[
            "total_score"
        ],
        -r[
            "attempt_overlap_sample"
        ],
        r[
            "file"
        ],
    )
)

candidate_columns.sort(
    key=lambda r: (
        r[
            "file"
        ],
        r[
            "column"
        ],
    )
)

join_rows.sort(
    key=lambda r: (
        -r[
            "core_coverage"
        ],
        -r[
            "thermal_score"
        ],
        r[
            "file"
        ],
    )
)


# =============================================================================
# Identify promising direct model-matrix sources
# =============================================================================

promising = [
    r
    for r in join_rows
    if (
        r[
            "core_coverage"
        ] >= 0.80
        and
        r[
            "thermal_score"
        ] > 0
    )
]


best_direct = (
    promising[0]
    if promising
    else None
)


# =============================================================================
# Column-class summary
# =============================================================================

class_files = defaultdict(
    set
)

for r in candidate_columns:

    for cls in clean(
        r[
            "classes"
        ]
    ).split(
        ";"
    ):

        if cls:
            class_files[
                cls
            ].add(
                r[
                    "file"
                ]
            )


# =============================================================================
# QA
# =============================================================================

qa_rows = [
    {
        "metric":
            "core_rows",
        "value":
            len(
                core_rows
            ),
        "expected":
            104,
        "status":
            (
                "PASS"
                if len(
                    core_rows
                ) == 104
                else "FAIL"
            ),
    },

    {
        "metric":
            "validation_rows",
        "value":
            len(
                validation_rows
            ),
        "expected":
            6,
        "status":
            (
                "PASS"
                if len(
                    validation_rows
                ) == 6
                else "FAIL"
            ),
    },

    {
        "metric":
            "candidate_files_found",
        "value":
            len(
                candidate_files
            ),
        "expected":
            ">0",
        "status":
            (
                "PASS"
                if candidate_files
                else "FAIL"
            ),
    },

    {
        "metric":
            "track_temperature_source_found",
        "value":
            len(
                class_files[
                    "TRACK_TEMP"
                ]
            ),
        "expected":
            ">0",
        "status":
            (
                "PASS"
                if class_files[
                    "TRACK_TEMP"
                ]
                else "FAIL"
            ),
    },

    {
        "metric":
            "forecast_source_found",
        "value":
            len(
                class_files[
                    "FORECAST"
                ]
            ),
        "expected":
            ">0",
        "status":
            (
                "PASS"
                if class_files[
                    "FORECAST"
                ]
                else "FAIL"
            ),
    },

    {
        "metric":
            "resolution_only_no_model_fit",
        "value":
            True,
        "expected":
            True,
        "status":
            "PASS",
    },
]


# =============================================================================
# Save outputs
# =============================================================================

if candidate_files:

    with OUT_FILES.open(
        "w",
        encoding="utf-8",
        newline=""
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=list(
                candidate_files[0].keys()
            )
        )

        writer.writeheader()
        writer.writerows(
            candidate_files
        )


if candidate_columns:

    with OUT_COLUMNS.open(
        "w",
        encoding="utf-8",
        newline=""
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=list(
                candidate_columns[0].keys()
            )
        )

        writer.writeheader()
        writer.writerows(
            candidate_columns
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
        "R4F7C0",

    "status":
        "R4F7C0_NUMERIC_FEATURE_SOURCE_RESOLUTION_READY",

    "core_rows":
        len(
            core_rows
        ),

    "validation_rows":
        len(
            validation_rows
        ),

    "candidate_files":
        len(
            candidate_files
        ),

    "candidate_numeric_columns":
        len(
            candidate_columns
        ),

    "joinable_attempt_id_files":
        len(
            join_rows
        ),

    "promising_direct_join_sources":
        promising[:10],

    "best_direct_source":
        best_direct,

    "feature_class_file_counts": {
        key:
            len(
                value
            )
        for key, value
        in sorted(
            class_files.items()
        )
    },

    "decision_rule":
        (
            "R4F7C1 may assemble the frozen numeric model matrix only "
            "after actual PTSC/HRRR numeric columns and safe join paths "
            "are resolved. No filename or schema is guessed."
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
print("=" * 142)
print("TOP NUMERIC FEATURE SOURCE CANDIDATES")
print("=" * 142)

for r in candidate_files[:20]:

    print(
        f"{r['file'][:72]:72s} | "
        f"score={r['total_score']:3d} | "
        f"thermal={r['thermal_score']:3d} | "
        f"id={r['identity_score']:2d} | "
        f"track={r['track_temp_cols']:2d} | "
        f"forecast={r['forecast_cols']:2d} | "
        f"time={r['time_cols']:2d} | "
        f"attempt={r['attempt_id_cols']:1d} | "
        f"sample_overlap={r['attempt_overlap_sample']:3d}"
    )


print()
print("=" * 142)
print("DIRECT ATTEMPT-ID JOIN COVERAGE")
print("=" * 142)

if not join_rows:

    print("NONE")

else:

    for r in join_rows[:20]:

        print(
            f"{r['file'][:72]:72s} | "
            f"core={r['core_overlap']:3d}/{r['core_total']:3d} "
            f"({r['core_coverage']:.3f}) | "
            f"val={r['validation_overlap']:2d}/{r['validation_total']:2d} "
            f"({r['validation_coverage']:.3f}) | "
            f"thermal={r['thermal_score']:2d} | "
            f"track={r['track_temp_cols']:2d} | "
            f"forecast={r['forecast_cols']:2d}"
        )


print()
print("=" * 142)
print("FEATURE CLASS AVAILABILITY")
print("=" * 142)

for key in [
    "TRACK_TEMP",
    "AMBIENT_TEMP",
    "HUMIDITY",
    "PRESSURE",
    "WIND",
    "SOLAR_CLOUD",
    "FORECAST",
    "DERIVED_TREND",
    "TIME",
    "ATTEMPT_ID",
]:

    files = sorted(
        class_files.get(
            key,
            set()
        )
    )

    print(
        f"{key:20s} | "
        f"files={len(files):2d}"
    )

    for name in files[:5]:

        print(
            f"  {name}"
        )


print()
print("=" * 142)
print("BEST DIRECT MODEL-MATRIX SOURCE")
print("=" * 142)

if best_direct is None:

    print(
        "NONE — model matrix will require deterministic multi-source join."
    )

else:

    print(
        f"file={best_direct['file']}"
    )

    print(
        f"core_coverage={best_direct['core_coverage']:.3f}"
    )

    print(
        f"validation_coverage={best_direct['validation_coverage']:.3f}"
    )

    print(
        f"track_temp_cols={best_direct['track_temp_cols']}"
    )

    print(
        f"forecast_cols={best_direct['forecast_cols']}"
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
    "R4F7C0_NUMERIC_FEATURE_SOURCE_RESOLUTION_READY"
)
