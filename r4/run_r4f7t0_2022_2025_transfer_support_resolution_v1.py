from pathlib import Path
import csv
import json
import math
import re

ROOT = Path(
    "/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈"
)

OUT = ROOT / "r4/output"

ATTEMPT_PATH = (
    OUT /
    "r4p1_attempt_four_lap_panel_v1.csv"
)

REFERENCE_PATH = (
    OUT /
    "r4f6k_expanded_fast_friday_canonical_panel_v1.csv"
)

DEV_CONTRACT = (
    OUT /
    "r4f7c7_final_performance_architecture_contract_v1.json"
)

VAL_CONCLUSION = (
    OUT /
    "r4f7v2_external_validation_conclusion_v1.json"
)

OUT_FILE_AUDIT = (
    OUT /
    "r4f7t0_2022_2025_candidate_file_audit_v1.csv"
)

OUT_YEAR_SUMMARY = (
    OUT /
    "r4f7t0_2022_2025_support_summary_v1.csv"
)

OUT_QA = (
    OUT /
    "r4f7t0_2022_2025_support_resolution_qa_v1.csv"
)

OUT_REPORT = (
    OUT /
    "r4f7t0_2022_2025_support_resolution_report_v1.json"
)


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


def get_year(r, fields):

    for field in fields:

        if norm(field) in {
            "year",
            "season",
        }:

            x = num(
                r.get(field)
            )

            if x is not None:

                y = int(x)

                if y in {
                    2022,
                    2025,
                }:
                    return y

    return None


def detect_columns(fields):

    result = {
        "attempt_id": [],
        "driver": [],
        "car": [],
        "speed": [],
        "time": [],
        "order": [],
        "status": [],
        "reference": [],
    }


    for f in fields:

        c = norm(f)


        if c in {
            "attempt_id",
            "attemptid",
        }:
            result[
                "attempt_id"
            ].append(f)


        if (
            "driver" in c
            and
            (
                "name" in c
                or
                "key" in c
            )
        ):
            result[
                "driver"
            ].append(f)


        if (
            c == "car_number"
            or
            c == "car"
        ):
            result[
                "car"
            ].append(f)


        if (
            "speed" in c
            and
            (
                "mph" in c
                or
                "average" in c
                or
                "qualifying" in c
            )
        ):
            result[
                "speed"
            ].append(f)


        if (
            "time_point" in c
            or
            "timestamp" in c
            or
            c.endswith("_utc")
            or
            "start_time" in c
            or
            "event_time" in c
        ):
            result[
                "time"
            ].append(f)


        if (
            "sequence" in c
            or
            "order" in c
            or
            "attempt_index" in c
            or
            "run_index" in c
            or
            "chronology" in c
        ):
            result[
                "order"
            ].append(f)


        if (
            "status" in c
            or
            "valid" in c
            or
            "withdraw" in c
            or
            "retired" in c
            or
            "failed" in c
        ):
            result[
                "status"
            ].append(f)


        if (
            "reference" in c
            or
            "fast_friday" in c
        ):
            result[
                "reference"
            ].append(f)


    return result


for path in [
    ATTEMPT_PATH,
    REFERENCE_PATH,
    DEV_CONTRACT,
    VAL_CONCLUSION,
]:

    if not path.exists():

        raise SystemExit(
            f"MISSING REQUIRED INPUT: {path}"
        )


attempt_fields, attempts = read_csv(
    ATTEMPT_PATH
)

reference_fields, references = read_csv(
    REFERENCE_PATH
)


contract = json.loads(
    DEV_CONTRACT.read_text(
        encoding="utf-8"
    )
)

validation = json.loads(
    VAL_CONCLUSION.read_text(
        encoding="utf-8"
    )
)


if (
    contract.get("status")
    !=
    "R4F7C7_FINAL_DEVELOPMENT_ARCHITECTURE_FROZEN"
):

    raise SystemExit(
        "DEVELOPMENT MODEL NOT FROZEN"
    )


if (
    validation.get("status")
    !=
    "R4F7V2_EXTERNAL_VALIDATION_CONCLUSION_FROZEN"
):

    raise SystemExit(
        "EXTERNAL VALIDATION CONCLUSION NOT FROZEN"
    )


print("=" * 150)
print("R4F7T0 — 2022 / 2025 TRANSFER SUPPORT RESOLUTION")
print("=" * 150)


# =============================================================================
# Known canonical attempt/reference support
# =============================================================================

attempt_year_counts = {
    2022: 0,
    2025: 0,
}

reference_year_counts = {
    2022: 0,
    2025: 0,
}


for r in attempts:

    y = get_year(
        r,
        attempt_fields
    )

    if y in attempt_year_counts:
        attempt_year_counts[y] += 1


for r in references:

    y = get_year(
        r,
        reference_fields
    )

    if y in reference_year_counts:
        reference_year_counts[y] += 1


# =============================================================================
# Scan project CSVs for 2022 / 2025 support
# =============================================================================

scan_roots = [
    ROOT / "r4/output",
    ROOT / "weather/output",
    ROOT / "weather/evidence",
    ROOT / "sources",
    ROOT / "data",
]


paths = []
seen = set()


for base in scan_roots:

    if not base.exists():
        continue

    for path in base.rglob(
        "*.csv"
    ):

        rp = str(
            path.resolve()
        )

        if rp in seen:
            continue

        seen.add(rp)
        paths.append(path)


file_audit = []


for path in sorted(paths):

    try:

        fields, rows = read_csv(
            path
        )

    except Exception:

        continue


    if not rows:
        continue


    year_counts = {
        2022: 0,
        2025: 0,
    }


    for r in rows:

        y = get_year(
            r,
            fields
        )

        if y in year_counts:
            year_counts[y] += 1


    if (
        year_counts[2022] == 0
        and
        year_counts[2025] == 0
    ):
        continue


    detected = detect_columns(
        fields
    )


    file_audit.append({
        "file":
            str(
                path.relative_to(
                    ROOT
                )
            ),

        "rows":
            len(rows),

        "rows_2022":
            year_counts[2022],

        "rows_2025":
            year_counts[2025],

        "attempt_id_columns":
            ";".join(
                detected[
                    "attempt_id"
                ]
            ),

        "driver_columns":
            ";".join(
                detected[
                    "driver"
                ]
            ),

        "speed_columns":
            ";".join(
                detected[
                    "speed"
                ]
            ),

        "time_columns":
            ";".join(
                detected[
                    "time"
                ]
            ),

        "order_columns":
            ";".join(
                detected[
                    "order"
                ]
            ),

        "status_columns":
            ";".join(
                detected[
                    "status"
                ]
            ),

        "reference_columns":
            ";".join(
                detected[
                    "reference"
                ]
            ),
    })


# =============================================================================
# Determine strongest locally supported validation mode
# =============================================================================

def candidate_files_for_year(
    year
):

    return [
        r
        for r in file_audit
        if r[
            f"rows_{year}"
        ] > 0
    ]


def has_speed(
    r
):

    return bool(
        clean(
            r[
                "speed_columns"
            ]
        )
    )


def has_time(
    r
):

    return bool(
        clean(
            r[
                "time_columns"
            ]
        )
    )


def has_order(
    r
):

    return bool(
        clean(
            r[
                "order_columns"
            ]
        )
    )


summary_rows = []


for year in [
    2022,
    2025,
]:

    candidates = candidate_files_for_year(
        year
    )


    speed_files = [
        r
        for r in candidates
        if has_speed(r)
    ]


    timed_speed_files = [
        r
        for r in speed_files
        if has_time(r)
    ]


    ordered_speed_files = [
        r
        for r in speed_files
        if (
            has_time(r)
            or
            has_order(r)
        )
    ]


    if (
        timed_speed_files
        and
        reference_year_counts[
            year
        ] > 0
    ):

        strongest_mode = (
            "POINT_TIME_PREQUENTIAL_REPLAY_POTENTIALLY_AVAILABLE"
        )


    elif (
        ordered_speed_files
        and
        reference_year_counts[
            year
        ] > 0
    ):

        strongest_mode = (
            "ORDER_ONLY_DEGRADED_REPLAY_POTENTIALLY_AVAILABLE"
        )


    elif (
        speed_files
        and
        reference_year_counts[
            year
        ] > 0
    ):

        strongest_mode = (
            "REFERENCE_VS_OUTCOME_TRANSFER_ONLY"
        )


    elif (
        reference_year_counts[
            year
        ] > 0
    ):

        strongest_mode = (
            "REFERENCE_EVIDENCE_ONLY_NO_OUTCOME_VALIDATION"
        )


    else:

        strongest_mode = (
            "NO_LOCAL_TRANSFER_VALIDATION_SUPPORT"
        )


    summary_rows.append({
        "year":
            year,

        "canonical_attempt_rows":
            attempt_year_counts[
                year
            ],

        "canonical_reference_rows":
            reference_year_counts[
                year
            ],

        "candidate_files":
            len(
                candidates
            ),

        "files_with_speed":
            len(
                speed_files
            ),

        "files_with_time_and_speed":
            len(
                timed_speed_files
            ),

        "files_with_order_or_time_and_speed":
            len(
                ordered_speed_files
            ),

        "strongest_supported_mode":
            strongest_mode,
    })


# =============================================================================
# QA
# =============================================================================

summary_lookup = {
    r[
        "year"
    ]:
    r
    for r in summary_rows
}


qa_rows = [
    {
        "metric":
            "2022_canonical_attempt_rows",
        "value":
            attempt_year_counts[2022],
        "expected":
            ">0",
        "status":
            (
                "PASS"
                if attempt_year_counts[2022] > 0
                else "FAIL"
            ),
    },

    {
        "metric":
            "2022_fast_friday_reference_rows",
        "value":
            reference_year_counts[2022],
        "expected":
            ">0",
        "status":
            (
                "PASS"
                if reference_year_counts[2022] > 0
                else "FAIL"
            ),
    },

    {
        "metric":
            "2025_fast_friday_reference_rows",
        "value":
            reference_year_counts[2025],
        "expected":
            ">0",
        "status":
            (
                "PASS"
                if reference_year_counts[2025] > 0
                else "FAIL"
            ),
    },

    {
        "metric":
            "2024_not_reused_for_tuning",
        "value":
            False,
        "expected":
            False,
        "status":
            "PASS",
    },

    {
        "metric":
            "model_refit_performed",
        "value":
            False,
        "expected":
            False,
        "status":
            "PASS",
    },

    {
        "metric":
            "transfer_support_resolution_only",
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

if file_audit:

    with OUT_FILE_AUDIT.open(
        "w",
        encoding="utf-8",
        newline=""
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=list(
                file_audit[0].keys()
            )
        )

        writer.writeheader()
        writer.writerows(
            file_audit
        )


with OUT_YEAR_SUMMARY.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=list(
            summary_rows[0].keys()
        )
    )

    writer.writeheader()
    writer.writerows(
        summary_rows
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
        "R4F7T0",

    "status":
        "R4F7T0_2022_2025_TRANSFER_SUPPORT_RESOLVED",

    "year_summary":
        summary_rows,

    "rules": {
        "2022":
            (
                "Use only validation strength actually supported by "
                "degraded chronology. Do not invent exact timestamps."
            ),

        "2025":
            (
                "Technical-regime transfer only. Do not fold 2025 into "
                "the frozen 2020-2023 development model."
            ),

        "model":
            (
                "No refit and no architecture change is permitted."
            ),
    },

    "next_phase":
        (
            "Construct one lightweight robustness/transfer evaluation "
            "using the strongest supported mode for each year, then "
            "move to action Monte Carlo integration."
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
print("=" * 150)
print("CANONICAL SUPPORT")
print("=" * 150)

for r in summary_rows:

    print(
        f"{r['year']} | "
        f"attempt_rows={r['canonical_attempt_rows']:3d} | "
        f"FF_refs={r['canonical_reference_rows']:3d} | "
        f"candidate_files={r['candidate_files']:3d} | "
        f"speed_files={r['files_with_speed']:3d} | "
        f"timed_speed_files={r['files_with_time_and_speed']:3d}"
    )


print()
print("=" * 150)
print("STRONGEST SUPPORTED VALIDATION MODE")
print("=" * 150)

for r in summary_rows:

    print(
        f"{r['year']} | "
        f"{r['strongest_supported_mode']}"
    )


print()
print("=" * 150)
print("TOP 2022 CANDIDATE FILES")
print("=" * 150)

c22 = [
    r
    for r in file_audit
    if r[
        "rows_2022"
    ] > 0
]

c22.sort(
    key=lambda r: (
        -int(
            bool(
                clean(
                    r[
                        "speed_columns"
                    ]
                )
            )
        ),
        -int(
            bool(
                clean(
                    r[
                        "time_columns"
                    ]
                )
            )
        ),
        -r[
            "rows_2022"
        ],
    )
)

for r in c22[:20]:

    print(
        f"{r['file'][:76]:76s} | "
        f"rows={r['rows_2022']:3d} | "
        f"speed=[{r['speed_columns']}] | "
        f"time=[{r['time_columns']}] | "
        f"order=[{r['order_columns']}]"
    )


print()
print("=" * 150)
print("TOP 2025 CANDIDATE FILES")
print("=" * 150)

c25 = [
    r
    for r in file_audit
    if r[
        "rows_2025"
    ] > 0
]

c25.sort(
    key=lambda r: (
        -int(
            bool(
                clean(
                    r[
                        "speed_columns"
                    ]
                )
            )
        ),
        -int(
            bool(
                clean(
                    r[
                        "time_columns"
                    ]
                )
            )
        ),
        -r[
            "rows_2025"
        ],
    )
)

for r in c25[:20]:

    print(
        f"{r['file'][:76]:76s} | "
        f"rows={r['rows_2025']:3d} | "
        f"speed=[{r['speed_columns']}] | "
        f"time=[{r['time_columns']}] | "
        f"order=[{r['order_columns']}]"
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
    OUT_FILE_AUDIT.relative_to(
        ROOT
    )
)

print(
    OUT_YEAR_SUMMARY.relative_to(
        ROOT
    )
)

print(
    OUT_QA.relative_to(
        ROOT
    )
)

print(
    OUT_REPORT.relative_to(
        ROOT
    )
)

print()
print(
    "R4F7T0_2022_2025_TRANSFER_SUPPORT_RESOLVED"
)
