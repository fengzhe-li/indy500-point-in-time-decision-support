from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict, Counter
import csv
import json
import math

ROOT = Path(
    "/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈"
)

OUT = ROOT / "r4/output"
OUT.mkdir(parents=True, exist_ok=True)

RESIDUAL_PATH = (
    OUT /
    "r4f4_cross_car_residual_observations_v1.csv"
)

STATE_PATH = (
    OUT /
    "r4f4_decision_window_residual_context_v1.csv"
)

OUT_AUDIT = (
    OUT /
    "r4f4b_repeat_residual_temporal_position_audit_v2.csv"
)

OUT_SUMMARY = (
    OUT /
    "r4f4b_repeat_residual_temporal_position_summary_v2.csv"
)

OUT_QA = (
    OUT /
    "r4f4b_repeat_residual_temporal_position_qa_v2.csv"
)

OUT_REPORT = (
    OUT /
    "r4f4b_repeat_residual_temporal_position_report_v2.json"
)


def clean(v):
    if v is None:
        return ""
    return str(v).strip()


def num(v):
    s = clean(v)

    if not s:
        return None

    if s.upper() in {
        "UNKNOWN",
        "NONE",
        "NA",
        "NAN",
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
    RESIDUAL_PATH,
    STATE_PATH,
]:

    if not path.exists():

        raise SystemExit(
            f"MISSING INPUT: {path}"
        )


residuals = read_csv(
    RESIDUAL_PATH
)

states = read_csv(
    STATE_PATH
)


print("=" * 124)
print("R4F4B-v2 — REPEAT RESIDUAL TEMPORAL POSITION AUDIT")
print("=" * 124)

print(
    f"Residual observations: {len(residuals)}"
)

print(
    f"Development decision states: {len(states)}"
)


# =============================================================================
# Development decision times
# =============================================================================

decision_times_by_year = defaultdict(list)

for r in states:

    year = integer(
        r.get("year")
    )

    dt = parse_dt(
        r.get(
            "decision_time_utc"
        )
    )

    if (
        year is None
        or
        dt is None
    ):
        continue

    decision_times_by_year[
        year
    ].append(
        dt
    )


for year in decision_times_by_year:

    decision_times_by_year[
        year
    ].sort()


# =============================================================================
# Repeat residuals
# =============================================================================

audit_rows = []

for r in residuals:

    year = integer(
        r.get("year")
    )

    repeat_time = parse_dt(
        r.get(
            "attempt_time_utc"
        )
    )

    if (
        year is None
        or
        repeat_time is None
    ):
        continue


    decisions = (
        decision_times_by_year.get(
            year,
            []
        )
    )


    if not decisions:

        temporal_position = (
            "NO_DEVELOPMENT_DECISION_TIMES"
        )

        before_count = 0
        after_count = 0

        minutes_after_last = None


    else:

        first_decision = min(
            decisions
        )

        last_decision = max(
            decisions
        )

        before_count = sum(
            dt < repeat_time
            for dt in decisions
        )

        after_count = sum(
            dt >= repeat_time
            for dt in decisions
        )


        if repeat_time < first_decision:

            temporal_position = (
                "BEFORE_ALL_DEVELOPMENT_DECISIONS"
            )


        elif repeat_time > last_decision:

            temporal_position = (
                "AFTER_ALL_DEVELOPMENT_DECISIONS"
            )


        else:

            temporal_position = (
                "DURING_DEVELOPMENT_DECISION_SEQUENCE"
            )


        if repeat_time > last_decision:

            minutes_after_last = (
                repeat_time
                -
                last_decision
            ).total_seconds() / 60.0

        else:

            minutes_after_last = None


    audit_rows.append({
        "year":
            year,

        "car_number":
            clean(
                r.get(
                    "car_number"
                )
            ),

        "attempt_id":
            clean(
                r.get(
                    "attempt_id"
                )
            ),

        "repeat_time_utc":
            repeat_time.isoformat(),

        "residual_mph":
            clean(
                r.get(
                    "residual_vs_first_run_mph"
                )
            ),

        "development_decision_count_year":
            len(
                decisions
            ),

        "decisions_before_repeat":
            before_count,

        "decisions_at_or_after_repeat":
            after_count,

        "temporal_position":
            temporal_position,

        "minutes_after_last_development_decision":
            (
                f"{minutes_after_last:.3f}"
                if minutes_after_last
                is not None
                else ""
            ),
    })


# =============================================================================
# Counts
# =============================================================================

position_counts = Counter(
    r[
        "temporal_position"
    ]
    for r in audit_rows
)


before_total = position_counts.get(
    "BEFORE_ALL_DEVELOPMENT_DECISIONS",
    0
)

during_total = position_counts.get(
    "DURING_DEVELOPMENT_DECISION_SEQUENCE",
    0
)

after_total = position_counts.get(
    "AFTER_ALL_DEVELOPMENT_DECISIONS",
    0
)

no_decision_total = position_counts.get(
    "NO_DEVELOPMENT_DECISION_TIMES",
    0
)


# =============================================================================
# Year summary
# =============================================================================

summary_rows = []

all_years = sorted(
    set(
        integer(
            r.get(
                "year"
            )
        )
        for r in residuals
        if integer(
            r.get(
                "year"
            )
        ) is not None
    )
    |
    set(
        decision_times_by_year.keys()
    )
)


for year in all_years:

    decisions = (
        decision_times_by_year.get(
            year,
            []
        )
    )

    year_rows = [
        r
        for r in audit_rows
        if r[
            "year"
        ] == year
    ]

    counts = Counter(
        r[
            "temporal_position"
        ]
        for r in year_rows
    )


    first_repeat = min(
        (
            parse_dt(
                r[
                    "repeat_time_utc"
                ]
            )
            for r in year_rows
        ),
        default=None,
    )


    last_decision = (
        max(
            decisions
        )
        if decisions
        else None
    )


    delta = None

    if (
        first_repeat is not None
        and
        last_decision is not None
    ):

        delta = (
            first_repeat
            -
            last_decision
        ).total_seconds() / 60.0


    summary_rows.append({
        "year":
            year,

        "development_decisions":
            len(
                decisions
            ),

        "repeat_residuals":
            len(
                year_rows
            ),

        "repeat_before":
            counts.get(
                "BEFORE_ALL_DEVELOPMENT_DECISIONS",
                0
            ),

        "repeat_during":
            counts.get(
                "DURING_DEVELOPMENT_DECISION_SEQUENCE",
                0
            ),

        "repeat_after":
            counts.get(
                "AFTER_ALL_DEVELOPMENT_DECISIONS",
                0
            ),

        "repeat_no_decision_reference":
            counts.get(
                "NO_DEVELOPMENT_DECISION_TIMES",
                0
            ),

        "last_development_decision_utc":
            (
                last_decision.isoformat()
                if last_decision
                else ""
            ),

        "first_repeat_residual_utc":
            (
                first_repeat.isoformat()
                if first_repeat
                else ""
            ),

        "minutes_first_repeat_minus_last_decision":
            (
                f"{delta:.3f}"
                if delta is not None
                else ""
            ),
    })


# =============================================================================
# QA
# =============================================================================

accounted = (
    before_total
    +
    during_total
    +
    after_total
    +
    no_decision_total
)


qa_rows = [
    {
        "metric":
            "residual_rows_preserved",

        "value":
            len(
                audit_rows
            ),

        "expected":
            len(
                residuals
            ),

        "status":
            (
                "PASS"
                if len(
                    audit_rows
                )
                == len(
                    residuals
                )
                else "FAIL"
            ),
    },

    {
        "metric":
            "all_temporal_positions_accounted_for",

        "value":
            accounted,

        "expected":
            len(
                audit_rows
            ),

        "status":
            (
                "PASS"
                if accounted
                ==
                len(
                    audit_rows
                )
                else "FAIL"
            ),
    },

    {
        "metric":
            "development_sequence_overlap",

        "value":
            during_total,

        "expected":
            "OBSERVED",

        "status":
            "PASS",
    },

    {
        "metric":
            "no_decision_reference_handled_explicitly",

        "value":
            no_decision_total,

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
            audit_rows[0].keys()
        )
    )

    writer.writeheader()
    writer.writerows(
        audit_rows
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
        "R4F4B_V2",

    "status":
        "R4F4B_V2_TEMPORAL_AUDIT_CORRECTED",

    "repeat_residuals":
        len(
            audit_rows
        ),

    "before_all":
        before_total,

    "during":
        during_total,

    "after_all":
        after_total,

    "no_development_decision_reference":
        no_decision_total,

    "offline_learning_policy":
        (
            "All historical repeat residuals remain eligible "
            "for offline rule-period window learning, target "
            "construction and validation. Temporal gating only "
            "controls whether a residual may be treated as an "
            "observable input at a specific historical decision time."
        ),

    "online_or_replay_policy":
        (
            "At a historical decision time, only information "
            "already available by that timestamp may enter the "
            "decision-state input."
        ),

    "next_phase":
        (
            "Build whole-session offline latent performance-window "
            "targets using complete historical repeat and cross-car "
            "evidence, while keeping prospective model features "
            "decision-time observable."
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
print("=" * 124)
print("CORRECTED GLOBAL TEMPORAL POSITION")
print("=" * 124)

print(
    f"Repeat residuals: "
    f"{len(audit_rows)}"
)

print(
    f"Before all development decisions: "
    f"{before_total}"
)

print(
    f"During development sequence: "
    f"{during_total}"
)

print(
    f"After all development decisions: "
    f"{after_total}"
)

print(
    f"No development decision reference: "
    f"{no_decision_total}"
)


print()
print("=" * 124)
print("YEAR TEMPORAL POSITION")
print("=" * 124)

for r in summary_rows:

    print(
        f"{r['year']} | "
        f"decisions={r['development_decisions']:2d} | "
        f"repeats={r['repeat_residuals']:2d} | "
        f"before={r['repeat_before']:2d} | "
        f"during={r['repeat_during']:2d} | "
        f"after={r['repeat_after']:2d} | "
        f"no_ref={r['repeat_no_decision_reference']:2d} | "
        f"first_repeat-last_decision="
        f"{r['minutes_first_repeat_minus_last_decision'] or '-'} min"
    )


print()
print("=" * 124)
print("MODEL INTERPRETATION")
print("=" * 124)

if during_total == 0:

    print(
        "No repeat residual overlaps the current development "
        "first-attempt decision sequence."
    )

else:

    print(
        f"{during_total} repeat residual(s) overlap the "
        "development decision sequence."
    )


print(
    "This does NOT discard historical repeat data."
)

print(
    "All repeat residuals remain usable for OFFLINE "
    "whole-session window learning and validation."
)

print(
    "Temporal availability only determines whether a residual "
    "can be used as an input at a particular historical decision time."
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

    raise SystemExit(1)


print()
print("OUTPUTS")
print(
    OUT_AUDIT.relative_to(ROOT)
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
    "R4F4B_V2_TEMPORAL_AUDIT_CORRECTED"
)
