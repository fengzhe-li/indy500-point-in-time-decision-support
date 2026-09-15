from pathlib import Path
from datetime import datetime, timezone
from collections import Counter
import csv
import json
import math

ROOT = Path(
    "/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈"
)

OUT = ROOT / "r4/output"
OUT.mkdir(parents=True, exist_ok=True)

R4F3A_PATH = (
    OUT /
    "r4f3a_shared_state_linkage_repaired_v1.csv"
)

PTSC_PATH = (
    ROOT /
    "weather/evidence/ptsc/"
    "indy500_day1_track_temp_2020_2024_time_normalized.csv"
)

OUT_DATA = (
    OUT /
    "r4f3b_shared_state_linkage_thermal_fixed_v1.csv"
)

OUT_SUMMARY = (
    OUT /
    "r4f3b_shared_state_linkage_summary_v1.csv"
)

OUT_QA = (
    OUT /
    "r4f3b_ptsc_track_temperature_semantic_qa_v1.csv"
)

OUT_REPORT = (
    OUT /
    "r4f3b_ptsc_track_temperature_semantic_report_v1.json"
)


PTSC_TIME_FIELD = "utc_datetime"
PTSC_YEAR_FIELD = "year"
PTSC_TEMP_C_FIELD = "track_c"

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

    if s.upper() in {
        "UNKNOWN",
        "NONE",
        "NAN",
        "NA",
    }:
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


def parse_dt(v):
    s = clean(v)

    if not s:
        return None

    if s.upper() == "UNKNOWN":
        return None

    if s.endswith("Z"):
        s = s[:-1] + "+00:00"

    try:
        dt = datetime.fromisoformat(s)

    except Exception:
        return None

    if dt.tzinfo is None:
        return None

    return dt.astimezone(
        timezone.utc
    )


def read_csv(path):
    with path.open(
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as f:

        return list(
            csv.DictReader(f)
        )


for path in [
    R4F3A_PATH,
    PTSC_PATH,
]:

    if not path.exists():

        raise SystemExit(
            f"MISSING INPUT: {path}"
        )


states = read_csv(
    R4F3A_PATH
)

ptsc_raw = read_csv(
    PTSC_PATH
)


print("=" * 124)
print("R4F3B — PTSC TRACK-TEMPERATURE SEMANTIC FIX")
print("=" * 124)

print(
    f"Input states: {len(states)}"
)

print(
    f"PTSC rows: {len(ptsc_raw)}"
)


if not ptsc_raw:
    raise SystemExit(
        "EMPTY PTSC INPUT"
    )


fields = set(
    ptsc_raw[0].keys()
)

required_ptsc_fields = {
    PTSC_TIME_FIELD,
    PTSC_YEAR_FIELD,
    PTSC_TEMP_C_FIELD,
}

missing_fields = (
    required_ptsc_fields
    -
    fields
)

if missing_fields:

    raise SystemExit(
        "MISSING PTSC FIELDS: "
        + ", ".join(
            sorted(
                missing_fields
            )
        )
    )


# =============================================================================
# Parse PTSC explicitly.
# =============================================================================

ptsc = []

bad_time_rows = 0
bad_temp_rows = 0

for r in ptsc_raw:

    year = integer(
        r.get(
            PTSC_YEAR_FIELD
        )
    )

    dt = parse_dt(
        r.get(
            PTSC_TIME_FIELD
        )
    )

    track_c = num(
        r.get(
            PTSC_TEMP_C_FIELD
        )
    )

    if (
        year is None
        or
        dt is None
    ):

        bad_time_rows += 1
        continue

    if track_c is None:

        bad_temp_rows += 1

    ptsc.append({
        "year":
            year,

        "time":
            dt,

        "track_c":
            track_c,
    })


ptsc.sort(
    key=lambda r: (
        r["year"],
        r["time"],
    )
)


print()
print("PTSC PARSE")

print(
    f"parsed rows={len(ptsc)}"
)

print(
    f"bad time rows={bad_time_rows}"
)

print(
    f"missing track_c rows={bad_temp_rows}"
)


# =============================================================================
# PTSC coverage by year.
# =============================================================================

print()
print("=" * 124)
print("PTSC TRACK-C COVERAGE")
print("=" * 124)

year_counts = Counter(
    r["year"]
    for r in ptsc
)

for year in sorted(
    year_counts
):

    subset = [
        r
        for r in ptsc
        if r["year"] == year
    ]

    temps = [
        r["track_c"]
        for r in subset
        if r["track_c"] is not None
    ]

    print(
        f"{year} | "
        f"rows={len(subset)} | "
        f"track_c={len(temps)} | "
        f"first={subset[0]['time'].isoformat()} | "
        f"last={subset[-1]['time'].isoformat()}"
    )


# =============================================================================
# Leakage-safe latest PTSC at or before decision.
# =============================================================================

def latest_ptsc_before(
    year,
    decision_time,
):

    candidates = [
        r
        for r in ptsc
        if (
            r["year"] == year
            and
            r["time"] <= decision_time
            and
            r["track_c"] is not None
        )
    ]

    if not candidates:
        return None

    best = max(
        candidates,
        key=lambda r:
            r["time"]
    )

    age_min = (
        decision_time
        -
        best["time"]
    ).total_seconds() / 60.0

    return (
        best,
        age_min,
    )


# =============================================================================
# Rebuild thermal readiness correctly.
# =============================================================================

rows = []

for r in states:

    year = integer(
        r.get("year")
    )

    decision_time = parse_dt(
        r.get(
            "decision_time_utc"
        )
    )

    match = None

    if (
        year is not None
        and
        decision_time is not None
    ):

        match = latest_ptsc_before(
            year,
            decision_time,
        )


    if match:

        obs, age_min = match

        ptsc_track_c_available = (
            0.0
            <= age_min
            <= PTSC_MAX_AGE_MINUTES
            and
            obs["track_c"] is not None
        )

        selected_time = (
            obs[
                "time"
            ]
        )

        track_c = (
            obs[
                "track_c"
            ]
        )

    else:

        age_min = None
        ptsc_track_c_available = False
        selected_time = None
        track_c = None


    hrrr30 = truth(
        r.get(
            "hrrr_supports_plus_30m"
        )
    )

    performance_ready = truth(
        r.get(
            "performance_attempt_exact_link"
        )
    )

    window20_ready = truth(
        r.get(
            "whole_field_window_context_20m_ready"
        )
    )

    wait_ready = truth(
        r.get(
            "wait_model_structural_available"
        )
    )


    # Correct thermal contract:
    #
    # PTSC observation exists
    # + actual track temperature value exists
    # + observation is not stale
    # + decision-safe HRRR supports +30m
    thermal_ready = (
        ptsc_track_c_available
        and
        hrrr30
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
        r
    )

    new[
        "ptsc_selected_time_utc"
    ] = (
        selected_time.isoformat()
        if selected_time
        else ""
    )

    new[
        "ptsc_prior_observation_age_min"
    ] = (
        f"{age_min:.3f}"
        if age_min is not None
        else ""
    )

    new[
        "ptsc_track_temp_c"
    ] = (
        f"{track_c:.6f}"
        if track_c is not None
        else ""
    )

    new[
        "ptsc_track_temperature_value_available"
    ] = (
        track_c is not None
    )

    new[
        "ptsc_prior_observation_available"
    ] = (
        ptsc_track_c_available
    )

    new[
        "ptsc_time_field_used"
    ] = (
        PTSC_TIME_FIELD
    )

    new[
        "ptsc_temperature_field_used"
    ] = (
        PTSC_TEMP_C_FIELD
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

    rows.append(
        new
    )


# =============================================================================
# QA
# =============================================================================

future_ptsc = []

for r in rows:

    decision = parse_dt(
        r.get(
            "decision_time_utc"
        )
    )

    selected = parse_dt(
        r.get(
            "ptsc_selected_time_utc"
        )
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


thermal_without_temp = [
    r
    for r in rows
    if (
        truth(
            r.get(
                "thermal_context_ready"
            )
        )
        and
        not truth(
            r.get(
                "ptsc_track_temperature_value_available"
            )
        )
    )
]


engine_without_thermal = [
    r
    for r in rows
    if (
        truth(
            r.get(
                "engine_v1_state_ready"
            )
        )
        and
        not truth(
            r.get(
                "thermal_context_ready"
            )
        )
    )
]


ptsc_ready_count = sum(
    truth(
        r.get(
            "ptsc_prior_observation_available"
        )
    )
    for r in rows
)

thermal_ready_count = sum(
    truth(
        r.get(
            "thermal_context_ready"
        )
    )
    for r in rows
)

engine_ready_count = sum(
    truth(
        r.get(
            "engine_v1_state_ready"
        )
    )
    for r in rows
)


qa_rows = [
    {
        "metric":
            "states_preserved",

        "value":
            len(rows),

        "expected":
            len(states),

        "status":
            (
                "PASS"
                if len(rows)
                == len(states)
                else "FAIL"
            ),
    },

    {
        "metric":
            "ptsc_time_field_exact",

        "value":
            PTSC_TIME_FIELD,

        "expected":
            "utc_datetime",

        "status":
            "PASS",
    },

    {
        "metric":
            "ptsc_temperature_field_exact",

        "value":
            PTSC_TEMP_C_FIELD,

        "expected":
            "track_c",

        "status":
            "PASS",
    },

    {
        "metric":
            "parsed_ptsc_rows",

        "value":
            len(ptsc),

        "expected":
            168,

        "status":
            (
                "PASS"
                if len(ptsc)
                == 168
                else "WARN"
            ),
    },

    {
        "metric":
            "future_ptsc_leakage",

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
            "thermal_ready_without_temperature_value",

        "value":
            len(
                thermal_without_temp
            ),

        "expected":
            0,

        "status":
            (
                "PASS"
                if not thermal_without_temp
                else "FAIL"
            ),
    },

    {
        "metric":
            "engine_ready_without_thermal",

        "value":
            len(
                engine_without_thermal
            ),

        "expected":
            0,

        "status":
            (
                "PASS"
                if not engine_without_thermal
                else "FAIL"
            ),
    },

    {
        "metric":
            "development_ptsc_coverage",

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
]


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
        for r in rows
    }
):

    subset = [
        r
        for r in rows
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

        "ptsc_track_c_ready":
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
# Save
# =============================================================================

with OUT_DATA.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=list(
            rows[0].keys()
        )
    )

    writer.writeheader()
    writer.writerows(
        rows
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
        "R4F3B",

    "status":
        "R4F3B_PTSC_TRACK_TEMPERATURE_SEMANTICS_FIXED",

    "ptsc_time_field":
        PTSC_TIME_FIELD,

    "ptsc_temperature_field":
        PTSC_TEMP_C_FIELD,

    "ptsc_ready_states":
        ptsc_ready_count,

    "thermal_ready_states":
        thermal_ready_count,

    "engine_ready_states":
        engine_ready_count,

    "correction":
        (
            "R4F3A correctly repaired PTSC timestamp linkage "
            "but incorrectly allowed thermal_context_ready "
            "without a parsed track-temperature value. "
            "R4F3B explicitly binds track_c and requires a "
            "non-null temperature value."
        ),

    "revised_model_remains": {
        "whole_field_window":
            True,

        "historical_action_classifier":
            False,

        "thermal_forecast":
            True,

        "performance_uncertainty":
            True,

        "stochastic_wait":
            True,

        "counterfactual_monte_carlo":
            True,
    },
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
print("CORRECTED THERMAL COVERAGE")
print("=" * 124)

print(
    f"States: {len(rows)}"
)

print(
    f"PTSC track_c ready: "
    f"{ptsc_ready_count}"
)

print(
    f"Thermal context ready: "
    f"{thermal_ready_count}"
)

print(
    f"FULL ENGINE V1 READY: "
    f"{engine_ready_count}"
)


print()
print("=" * 124)
print("YEAR COVERAGE")
print("=" * 124)

for r in summary_rows:

    print(
        f"{r['year']} | "
        f"states={r['states']:2d} | "
        f"performance={r['performance_ready']:2d} | "
        f"window20={r['window20_ready']:2d} | "
        f"track_c={r['ptsc_track_c_ready']:2d} | "
        f"HRRR30={r['hrrr30_ready']:2d} | "
        f"thermal={r['thermal_ready']:2d} | "
        f"engine={r['engine_ready']:2d}"
    )


print()
print("=" * 124)
print("TRACK TEMPERATURE RANGE")
print("=" * 124)

temps = [
    num(
        r.get(
            "ptsc_track_temp_c"
        )
    )
    for r in rows
]

temps = [
    x
    for x in temps
    if x is not None
]

if temps:

    temps_sorted = sorted(
        temps
    )

    n = len(
        temps_sorted
    )

    median = (
        temps_sorted[
            n // 2
        ]
        if n % 2
        else
        (
            temps_sorted[
                n // 2 - 1
            ]
            +
            temps_sorted[
                n // 2
            ]
        ) / 2
    )

    print(
        f"n={n} | "
        f"min={min(temps_sorted):.3f} C | "
        f"median={median:.3f} C | "
        f"max={max(temps_sorted):.3f} C"
    )

else:

    print(
        "NO VALID TRACK_C VALUES"
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
    OUT_DATA.relative_to(ROOT)
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
    "R4F3B_PTSC_TRACK_TEMPERATURE_SEMANTICS_FIXED"
)
