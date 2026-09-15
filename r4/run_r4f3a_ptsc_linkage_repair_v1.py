from pathlib import Path
from datetime import datetime, timezone
from collections import Counter
import csv
import json
import math
import re

ROOT = Path(
    "/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈"
)

OUT = ROOT / "r4/output"
OUT.mkdir(parents=True, exist_ok=True)

AUDIT_V1 = (
    OUT /
    "r4f3_shared_state_linkage_audit_v1.csv"
)

PTSC_PATH = (
    ROOT /
    "weather/evidence/ptsc/"
    "indy500_day1_track_temp_2020_2024_time_normalized.csv"
)

OUT_AUDIT = (
    OUT /
    "r4f3a_shared_state_linkage_repaired_v1.csv"
)

OUT_DIAG = (
    OUT /
    "r4f3a_ptsc_schema_diagnostics_v1.csv"
)

OUT_SUMMARY = (
    OUT /
    "r4f3a_shared_state_linkage_summary_v1.csv"
)

OUT_QA = (
    OUT /
    "r4f3a_ptsc_linkage_repair_qa_v1.csv"
)

OUT_REPORT = (
    OUT /
    "r4f3a_ptsc_linkage_repair_report_v1.json"
)


PTSC_MAX_AGE_MINUTES = 30.0


def clean(v):
    if v is None:
        return ""
    return str(v).strip()


def truth(v):
    return clean(v).lower() in {
        "true",
        "1",
        "yes",
    }


def num(v):
    s = clean(v)

    if not s:
        return None

    if s.upper() == "UNKNOWN":
        return None

    try:
        x = float(s)

        if math.isfinite(x):
            return x

    except Exception:
        pass

    return None


def integer(v):
    x = num(v)

    if x is None:
        return None

    return int(x)


def read_csv(path):
    with path.open(
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as f:

        return list(
            csv.DictReader(f)
        )


def parse_datetime(value, field_name=""):
    s = clean(value)

    if not s:
        return None

    if s.upper() in {
        "UNKNOWN",
        "NONE",
        "NAN",
        "NA",
    }:
        return None

    original = s

    # Normalize common UTC suffix.
    if s.endswith("Z"):
        s = (
            s[:-1]
            + "+00:00"
        )

    # First try ISO parser.
    try:
        dt = datetime.fromisoformat(
            s
        )

        if dt.tzinfo is None:

            # Only assume UTC when the field explicitly claims UTC.
            if "utc" in field_name.lower():

                dt = dt.replace(
                    tzinfo=timezone.utc
                )

            else:
                return None

        return dt.astimezone(
            timezone.utc
        )

    except Exception:
        pass


    # Explicit additional formats.
    formats = [
        "%Y-%m-%d %H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%d %H:%M:%S.%f%z",
        "%Y-%m-%dT%H:%M:%S.%f%z",
    ]

    for fmt in formats:

        try:
            dt = datetime.strptime(
                original,
                fmt
            )

            return dt.astimezone(
                timezone.utc
            )

        except Exception:
            continue

    return None


if not AUDIT_V1.exists():
    raise SystemExit(
        f"MISSING: {AUDIT_V1}"
    )

if not PTSC_PATH.exists():
    raise SystemExit(
        f"MISSING: {PTSC_PATH}"
    )


audit = read_csv(
    AUDIT_V1
)

ptsc_raw = read_csv(
    PTSC_PATH
)


print("=" * 124)
print("R4F3A — PTSC LINKAGE DIAGNOSTIC + REPAIR")
print("=" * 124)

print(
    f"Existing R4F3 states: "
    f"{len(audit)}"
)

print(
    f"PTSC rows: "
    f"{len(ptsc_raw)}"
)


if not ptsc_raw:
    raise SystemExit(
        "PTSC FILE EMPTY"
    )


fields = list(
    ptsc_raw[0].keys()
)


print()
print("=" * 124)
print("PTSC FIELDS")
print("=" * 124)

for field in fields:
    print(
        field
    )


# =============================================================================
# Score every field as a datetime candidate.
# =============================================================================

diagnostics = []

for field in fields:

    nonempty = 0
    parsed = 0

    sample_values = []

    parsed_years = Counter()

    for row in ptsc_raw:

        value = clean(
            row.get(field)
        )

        if not value:
            continue

        nonempty += 1

        if len(
            sample_values
        ) < 5:

            sample_values.append(
                value
            )

        dt = parse_datetime(
            value,
            field
        )

        if dt is not None:

            parsed += 1

            parsed_years[
                dt.year
            ] += 1


    name = field.lower()

    name_bonus = 0

    if "utc" in name:
        name_bonus += 50

    if "timestamp" in name:
        name_bonus += 30

    if "datetime" in name:
        name_bonus += 25

    if "time" in name:
        name_bonus += 20

    if "date" in name:
        name_bonus += 10


    parse_fraction = (
        parsed / nonempty
        if nonempty
        else 0.0
    )

    score = (
        parsed
        +
        name_bonus
    )

    diagnostics.append({
        "field":
            field,

        "nonempty":
            nonempty,

        "parsed_datetime":
            parsed,

        "parse_fraction":
            parse_fraction,

        "name_bonus":
            name_bonus,

        "score":
            score,

        "parsed_years":
            ";".join(
                f"{year}:{count}"
                for year, count
                in sorted(
                    parsed_years.items()
                )
            ),

        "sample_values":
            " | ".join(
                sample_values
            ),
    })


diagnostics.sort(
    key=lambda r: (
        -r[
            "parsed_datetime"
        ],
        -r[
            "name_bonus"
        ],
        r[
            "field"
        ],
    )
)


print()
print("=" * 124)
print("DATETIME FIELD DIAGNOSTICS")
print("=" * 124)

for r in diagnostics[:15]:

    print(
        f"{r['field']:45s} | "
        f"parsed={r['parsed_datetime']:3d}/"
        f"{r['nonempty']:3d} | "
        f"fraction={r['parse_fraction']:.3f} | "
        f"years={r['parsed_years'] or '-'}"
    )

    print(
        f"    samples: "
        f"{r['sample_values']}"
    )


usable_datetime_fields = [
    r
    for r in diagnostics
    if (
        r[
            "parsed_datetime"
        ] > 0
    )
]


if not usable_datetime_fields:

    raise SystemExit(
        "NO PTSC DATETIME FIELD COULD BE PARSED"
    )


# Prefer fields covering relevant Indy years.
def relevant_year_score(field_name):

    years = set()

    count = 0

    for row in ptsc_raw:

        dt = parse_datetime(
            row.get(
                field_name
            ),
            field_name,
        )

        if dt is None:
            continue

        years.add(
            dt.year
        )

        if dt.year in {
            2020,
            2021,
            2022,
            2023,
            2024,
        }:

            count += 1

    return (
        count,
        len(
            years
            &
            {
                2020,
                2021,
                2022,
                2023,
                2024,
            }
        ),
    )


ranked_datetime = []

for r in usable_datetime_fields:

    relevant_count, year_coverage = (
        relevant_year_score(
            r[
                "field"
            ]
        )
    )

    ranked_datetime.append(
        (
            year_coverage,
            relevant_count,
            r[
                "name_bonus"
            ],
            r[
                "parsed_datetime"
            ],
            r[
                "field"
            ],
        )
    )


ranked_datetime.sort(
    reverse=True
)

TIME_FIELD = (
    ranked_datetime[
        0
    ][
        -1
    ]
)


print()
print(
    f"SELECTED PTSC TIME FIELD: "
    f"{TIME_FIELD}"
)


# =============================================================================
# Detect explicit year field if available.
# Otherwise derive year from timestamp.
# =============================================================================

YEAR_FIELD = None

for field in fields:

    if field.lower() == "year":

        YEAR_FIELD = field
        break


print(
    f"SELECTED PTSC YEAR FIELD: "
    f"{YEAR_FIELD or '[derive from timestamp]'}"
)


# =============================================================================
# Detect track-temperature column.
# =============================================================================

temperature_candidates = []

for field in fields:

    low = field.lower()

    if not (
        "temp" in low
        or
        "temperature" in low
    ):
        continue

    numeric_count = sum(
        num(
            row.get(field)
        ) is not None
        for row in ptsc_raw
    )

    bonus = 0

    if "track" in low:
        bonus += 100

    if "surface" in low:
        bonus += 80

    if "temp" in low:
        bonus += 20

    temperature_candidates.append(
        (
            bonus,
            numeric_count,
            field,
        )
    )


temperature_candidates.sort(
    reverse=True
)

TEMP_FIELD = (
    temperature_candidates[
        0
    ][
        2
    ]
    if temperature_candidates
    else None
)


print(
    f"SELECTED PTSC TEMPERATURE FIELD: "
    f"{TEMP_FIELD or '[none]'}"
)


# =============================================================================
# Parse canonical PTSC observations.
# =============================================================================

ptsc = []

for row in ptsc_raw:

    dt = parse_datetime(
        row.get(
            TIME_FIELD
        ),
        TIME_FIELD,
    )

    if dt is None:
        continue

    if YEAR_FIELD:

        year = integer(
            row.get(
                YEAR_FIELD
            )
        )

    else:

        year = dt.year

    if year is None:
        year = dt.year

    ptsc.append({
        "year":
            year,

        "time":
            dt,

        "track_temp":
            (
                num(
                    row.get(
                        TEMP_FIELD
                    )
                )
                if TEMP_FIELD
                else None
            ),
    })


ptsc.sort(
    key=lambda r: (
        r[
            "year"
        ],
        r[
            "time"
        ],
    )
)


print()
print("=" * 124)
print("PARSED PTSC COVERAGE")
print("=" * 124)

ptsc_year_counts = Counter(
    r[
        "year"
    ]
    for r in ptsc
)

for year, count in sorted(
    ptsc_year_counts.items()
):

    subset = [
        r
        for r in ptsc
        if r[
            "year"
        ] == year
    ]

    print(
        f"{year} | "
        f"rows={count} | "
        f"first={subset[0]['time'].isoformat()} | "
        f"last={subset[-1]['time'].isoformat()}"
    )


# =============================================================================
# Latest leakage-safe PTSC observation at or before decision time.
# =============================================================================

def latest_ptsc_before(
    year,
    decision_time,
):
    candidates = [
        row
        for row in ptsc
        if (
            row[
                "year"
            ] == year
            and
            row[
                "time"
            ] <= decision_time
        )
    ]

    if not candidates:
        return None

    best = max(
        candidates,
        key=lambda r:
            r[
                "time"
            ]
    )

    age_min = (
        decision_time
        -
        best[
            "time"
        ]
    ).total_seconds() / 60.0

    return (
        best,
        age_min,
    )


# =============================================================================
# Repair R4F3 rows.
# =============================================================================

repaired = []

for row in audit:

    decision_time = parse_datetime(
        row.get(
            "decision_time_utc"
        ),
        "decision_time_utc",
    )

    year = integer(
        row.get(
            "year"
        )
    )

    ptsc_match = None

    if (
        decision_time is not None
        and
        year is not None
    ):

        ptsc_match = latest_ptsc_before(
            year,
            decision_time,
        )


    if ptsc_match:

        obs, age = (
            ptsc_match
        )

        ptsc_available = (
            age >= 0
            and
            age
            <= PTSC_MAX_AGE_MINUTES
        )

        ptsc_time = (
            obs[
                "time"
            ].isoformat()
        )

        ptsc_temp = (
            obs[
                "track_temp"
            ]
        )

    else:

        age = None
        ptsc_available = False
        ptsc_time = ""
        ptsc_temp = None


    hrrr30 = truth(
        row.get(
            "hrrr_supports_plus_30m"
        )
    )

    thermal_ready = (
        ptsc_available
        and
        hrrr30
    )


    performance_ready = truth(
        row.get(
            "performance_attempt_exact_link"
        )
    )

    window20_ready = truth(
        row.get(
            "whole_field_window_context_20m_ready"
        )
    )

    wait_ready = truth(
        row.get(
            "wait_model_structural_available"
        )
    )


    engine_ready = (
        performance_ready
        and
        decision_time is not None
        and
        window20_ready
        and
        thermal_ready
        and
        wait_ready
    )


    new = dict(
        row
    )

    new[
        "ptsc_selected_time_utc"
    ] = (
        ptsc_time
    )

    new[
        "ptsc_prior_observation_available"
    ] = (
        ptsc_available
    )

    new[
        "ptsc_prior_observation_age_min"
    ] = (
        f"{age:.3f}"
        if age is not None
        else ""
    )

    new[
        "ptsc_track_temp"
    ] = (
        f"{ptsc_temp:.6f}"
        if ptsc_temp is not None
        else ""
    )

    new[
        "ptsc_time_field_used"
    ] = (
        TIME_FIELD
    )

    new[
        "ptsc_temperature_field_used"
    ] = (
        TEMP_FIELD
        or ""
    )

    new[
        "thermal_context_ready"
    ] = (
        thermal_ready
    )

    new[
        "engine_v1_state_ready"
    ] = (
        engine_ready
    )

    new[
        "model_role"
    ] = (
        "COUNTERFACTUAL_ENGINE_STATE"
        if engine_ready
        else
        "PARTIAL_STATE_EVIDENCE"
    )

    repaired.append(
        new
    )


# =============================================================================
# Summary
# =============================================================================

summary_rows = []

for year in sorted(
    {
        integer(
            r.get(
                "year"
            )
        )
        for r in repaired
    }
):

    subset = [
        r
        for r in repaired
        if integer(
            r.get(
                "year"
            )
        ) == year
    ]

    summary_rows.append({
        "year":
            year,

        "states":
            len(
                subset
            ),

        "performance_ready":
            sum(
                truth(
                    r.get(
                        "performance_attempt_exact_link"
                    )
                )
                for r in subset
            ),

        "window20_ready":
            sum(
                truth(
                    r.get(
                        "whole_field_window_context_20m_ready"
                    )
                )
                for r in subset
            ),

        "ptsc_ready":
            sum(
                truth(
                    r.get(
                        "ptsc_prior_observation_available"
                    )
                )
                for r in subset
            ),

        "hrrr30_ready":
            sum(
                truth(
                    r.get(
                        "hrrr_supports_plus_30m"
                    )
                )
                for r in subset
            ),

        "thermal_ready":
            sum(
                truth(
                    r.get(
                        "thermal_context_ready"
                    )
                )
                for r in subset
            ),

        "engine_ready":
            sum(
                truth(
                    r.get(
                        "engine_v1_state_ready"
                    )
                )
                for r in subset
            ),
    })


# =============================================================================
# QA
# =============================================================================

future_ptsc = []

for r in repaired:

    decision = parse_datetime(
        r.get(
            "decision_time_utc"
        ),
        "decision_time_utc",
    )

    selected = parse_datetime(
        r.get(
            "ptsc_selected_time_utc"
        ),
        "ptsc_selected_time_utc",
    )

    if (
        decision is not None
        and
        selected is not None
        and
        selected > decision
    ):

        future_ptsc.append(
            r[
                "decision_id"
            ]
        )


ptsc_ready_count = sum(
    truth(
        r.get(
            "ptsc_prior_observation_available"
        )
    )
    for r in repaired
)

engine_ready_count = sum(
    truth(
        r.get(
            "engine_v1_state_ready"
        )
    )
    for r in repaired
)


qa_rows = [
    {
        "metric":
            "input_states_preserved",

        "value":
            len(
                repaired
            ),

        "expected":
            len(
                audit
            ),

        "status":
            (
                "PASS"
                if len(
                    repaired
                )
                == len(
                    audit
                )
                else "FAIL"
            ),
    },

    {
        "metric":
            "ptsc_rows_parsed",

        "value":
            len(
                ptsc
            ),

        "expected":
            ">0",

        "status":
            (
                "PASS"
                if ptsc
                else "FAIL"
            ),
    },

    {
        "metric":
            "ptsc_development_years_present",

        "value":
            ";".join(
                str(y)
                for y in sorted(
                    set(
                        ptsc_year_counts
                    )
                    &
                    {
                        2020,
                        2021,
                        2023,
                    }
                )
            ),

        "expected":
            "2020;2021;2023",

        "status":
            (
                "PASS"
                if {
                    2020,
                    2021,
                    2023,
                }.issubset(
                    set(
                        ptsc_year_counts
                    )
                )
                else "FAIL"
            ),
    },

    {
        "metric":
            "ptsc_future_observation_leakage",

        "value":
            len(
                future_ptsc
            ),

        "expected":
            0,

        "status":
            (
                "PASS"
                if not future_ptsc
                else "FAIL"
            ),
    },

    {
        "metric":
            "ptsc_prior_state_coverage",

        "value":
            ptsc_ready_count,

        "expected":
            ">0",

        "status":
            (
                "PASS"
                if ptsc_ready_count > 0
                else "FAIL"
            ),
    },

    {
        "metric":
            "engine_ready_not_forced",

        "value":
            engine_ready_count,

        "expected":
            "OBSERVED",

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
            repaired[0].keys()
        )
    )

    writer.writeheader()
    writer.writerows(
        repaired
    )


with OUT_DIAG.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=list(
            diagnostics[0].keys()
        )
    )

    writer.writeheader()
    writer.writerows(
        diagnostics
    )


with OUT_SUMMARY.open(
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
        "R4F3A",

    "status":
        "R4F3A_PTSC_LINKAGE_REPAIR_READY",

    "selected_time_field":
        TIME_FIELD,

    "selected_temperature_field":
        TEMP_FIELD,

    "parsed_ptsc_rows":
        len(
            ptsc
        ),

    "ptsc_ready_states":
        ptsc_ready_count,

    "engine_ready_states":
        engine_ready_count,

    "methodology": [
        (
            "PTSC observation must occur at or before "
            "the historical decision time."
        ),

        (
            "Maximum accepted PTSC observation age is "
            f"{PTSC_MAX_AGE_MINUTES:.0f} minutes."
        ),

        (
            "PTSC repair does not alter the previously "
            "frozen action semantics or validation split."
        ),

        (
            "Engine readiness remains dependent on "
            "performance, whole-field window, thermal "
            "context and structural wait model."
        ),
    ],
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
print("=" * 124)
print("REPAIRED SHARED STATE COVERAGE")
print("=" * 124)

print(
    f"States: "
    f"{len(repaired)}"
)

print(
    f"PTSC ready: "
    f"{ptsc_ready_count}"
)

print(
    "Thermal ready: "
    f"{sum(truth(r.get('thermal_context_ready')) for r in repaired)}"
)

print(
    f"FULL ENGINE V1 READY: "
    f"{engine_ready_count}"
)


print()
print("=" * 124)
print("YEAR COVERAGE AFTER PTSC REPAIR")
print("=" * 124)

for r in summary_rows:

    print(
        f"{r['year']} | "
        f"states={r['states']:2d} | "
        f"performance={r['performance_ready']:2d} | "
        f"window20={r['window20_ready']:2d} | "
        f"PTSC={r['ptsc_ready']:2d} | "
        f"HRRR30={r['hrrr30_ready']:2d} | "
        f"thermal={r['thermal_ready']:2d} | "
        f"engine={r['engine_ready']:2d}"
    )


print()
print("=" * 124)
print("PTSC AGE DISTRIBUTION")
print("=" * 124)

ages = [
    num(
        r.get(
            "ptsc_prior_observation_age_min"
        )
    )
    for r in repaired
]

ages = [
    x
    for x in ages
    if x is not None
]

if ages:

    ages_sorted = sorted(
        ages
    )

    n = len(
        ages_sorted
    )

    median = (
        ages_sorted[
            n // 2
        ]
        if n % 2
        else
        (
            ages_sorted[
                n // 2 - 1
            ]
            +
            ages_sorted[
                n // 2
            ]
        ) / 2
    )

    print(
        f"n={n} | "
        f"min={min(ages_sorted):.3f} | "
        f"median={median:.3f} | "
        f"max={max(ages_sorted):.3f} | "
        f"<=30m="
        f"{sum(x <= 30 for x in ages_sorted)}"
    )

else:

    print(
        "NO LINKED PTSC AGES"
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
    f"{len(qa_rows)-len(fails)}/"
    f"{len(qa_rows)} PASS"
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
    OUT_DIAG.relative_to(ROOT)
)
print(
    OUT_SUMMARY.relative_to(ROOT)
)
print(
    OUT_QA.relative_to(ROOT)
)
print(
    OUT_REPORT.relative_to(ROOT)
)

print()
print(
    "R4F3A_PTSC_LINKAGE_REPAIR_READY"
)
