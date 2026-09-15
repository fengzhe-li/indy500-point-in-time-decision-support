from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict
import csv
import json
import math
import statistics

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

ATTEMPT_PATH = (
    OUT /
    "r4p1_attempt_four_lap_panel_v1.csv"
)

OUT_AUDIT = (
    OUT /
    "r4f4b_repeat_residual_temporal_position_audit_v1.csv"
)

OUT_SUMMARY = (
    OUT /
    "r4f4b_repeat_residual_temporal_position_summary_v1.csv"
)

OUT_QA = (
    OUT /
    "r4f4b_repeat_residual_temporal_position_qa_v1.csv"
)

OUT_REPORT = (
    OUT /
    "r4f4b_repeat_residual_temporal_position_report_v1.json"
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
    ATTEMPT_PATH,
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

attempts = read_csv(
    ATTEMPT_PATH
)


print("=" * 124)
print("R4F4B — REPEAT RESIDUAL TEMPORAL POSITION AUDIT")
print("=" * 124)

print(
    f"Residual observations: {len(residuals)}"
)

print(
    f"Decision states: {len(states)}"
)

print(
    f"Attempt rows: {len(attempts)}"
)


# =============================================================================
# Parse first-attempt decision times from the 50 development states.
# =============================================================================

state_times_by_year = defaultdict(list)

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

    state_times_by_year[
        year
    ].append(
        dt
    )


for year in state_times_by_year:

    state_times_by_year[
        year
    ].sort()


# =============================================================================
# Parse repeat residual times.
# =============================================================================

residual_by_year = defaultdict(list)

for r in residuals:

    year = integer(
        r.get("year")
    )

    dt = parse_dt(
        r.get(
            "attempt_time_utc"
        )
    )

    residual = num(
        r.get(
            "residual_vs_first_run_mph"
        )
    )

    if (
        year is None
        or
        dt is None
    ):
        continue

    residual_by_year[
        year
    ].append({
        "time":
            dt,

        "residual":
            residual,

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
    })


for year in residual_by_year:

    residual_by_year[
        year
    ].sort(
        key=lambda r:
            r["time"]
    )


# =============================================================================
# For each repeat residual, locate it relative to development decision states.
# =============================================================================

audit_rows = []

for year in sorted(
    residual_by_year
):

    decision_times = (
        state_times_by_year.get(
            year,
            []
        )
    )

    if decision_times:

        first_decision = (
            min(
                decision_times
            )
        )

        last_decision = (
            max(
                decision_times
            )
        )

    else:

        first_decision = None
        last_decision = None


    for r in residual_by_year[
        year
    ]:

        repeat_time = (
            r["time"]
        )

        prior_decisions = sum(
            dt < repeat_time
            for dt in decision_times
        )

        later_decisions = sum(
            dt >= repeat_time
            for dt in decision_times
        )

        if not decision_times:

            position = (
                "NO_DEVELOPMENT_DECISION_TIMES"
            )

        elif repeat_time < first_decision:

            position = (
                "BEFORE_ALL_DEVELOPMENT_DECISIONS"
            )

        elif repeat_time > last_decision:

            position = (
                "AFTER_ALL_DEVELOPMENT_DECISIONS"
            )

        else:

            position = (
                "DURING_DEVELOPMENT_DECISION_SEQUENCE"
            )


        minutes_after_last_decision = None

        if (
            last_decision is not None
            and
            repeat_time > last_decision
        ):

            minutes_after_last_decision = (
                repeat_time
                -
                last_decision
            ).total_seconds() / 60.0


        audit_rows.append({
            "year":
                year,

            "car_number":
                r[
                    "car_number"
                ],

            "attempt_id":
                r[
                    "attempt_id"
                ],

            "repeat_time_utc":
                repeat_time.isoformat(),

            "residual_mph":
                (
                    f"{r['residual']:.6f}"
                    if r[
                        "residual"
                    ]
                    is not None
                    else ""
                ),

            "development_decision_count_year":
                len(
                    decision_times
                ),

            "decisions_before_repeat":
                prior_decisions,

            "decisions_at_or_after_repeat":
                later_decisions,

            "temporal_position":
                position,

            "minutes_after_last_development_decision":
                (
                    f"{minutes_after_last_decision:.3f}"
                    if minutes_after_last_decision
                    is not None
                    else ""
                ),
        })


# =============================================================================
# Summary by year
# =============================================================================

summary_rows = []

all_years = sorted(
    set(
        state_times_by_year
    )
    |
    set(
        residual_by_year
    )
)

for year in all_years:

    decision_times = (
        state_times_by_year.get(
            year,
            []
        )
    )

    repeat_rows = [
        r
        for r in audit_rows
        if r[
            "year"
        ] == year
    ]

    after_all = sum(
        r[
            "temporal_position"
        ]
        ==
        "AFTER_ALL_DEVELOPMENT_DECISIONS"
        for r in repeat_rows
    )

    during = sum(
        r[
            "temporal_position"
        ]
        ==
        "DURING_DEVELOPMENT_DECISION_SEQUENCE"
        for r in repeat_rows
    )

    before_all = sum(
        r[
            "temporal_position"
        ]
        ==
        "BEFORE_ALL_DEVELOPMENT_DECISIONS"
        for r in repeat_rows
    )

    first_repeat = (
        min(
            (
                parse_dt(
                    r[
                        "repeat_time_utc"
                    ]
                )
                for r in repeat_rows
            ),
            default=None
        )
    )

    last_decision = (
        max(
            decision_times
        )
        if decision_times
        else None
    )

    gap_first_repeat_after_last_decision = None

    if (
        first_repeat is not None
        and
        last_decision is not None
    ):

        gap_first_repeat_after_last_decision = (
            first_repeat
            -
            last_decision
        ).total_seconds() / 60.0


    summary_rows.append({
        "year":
            year,

        "development_decisions":
            len(
                decision_times
            ),

        "repeat_residuals":
            len(
                repeat_rows
            ),

        "repeat_before_all_decisions":
            before_all,

        "repeat_during_decision_sequence":
            during,

        "repeat_after_all_decisions":
            after_all,

        "first_development_decision_utc":
            (
                min(
                    decision_times
                ).isoformat()
                if decision_times
                else ""
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
                f"{gap_first_repeat_after_last_decision:.3f}"
                if gap_first_repeat_after_last_decision
                is not None
                else ""
            ),
    })


# =============================================================================
# Global interpretation
# =============================================================================

total_repeat = len(
    audit_rows
)

after_all_total = sum(
    r[
        "temporal_position"
    ]
    ==
    "AFTER_ALL_DEVELOPMENT_DECISIONS"
    for r in audit_rows
)

during_total = sum(
    r[
        "temporal_position"
    ]
    ==
    "DURING_DEVELOPMENT_DECISION_SEQUENCE"
    for r in audit_rows
)

before_total = sum(
    r[
        "temporal_position"
    ]
    ==
    "BEFORE_ALL_DEVELOPMENT_DECISIONS"
    for r in audit_rows
)


# =============================================================================
# QA
# =============================================================================

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
                else "WARN"
            ),
    },

    {
        "metric":
            "development_state_count",

        "value":
            sum(
                len(v)
                for v in
                state_times_by_year.values()
            ),

        "expected":
            50,

        "status":
            (
                "PASS"
                if sum(
                    len(v)
                    for v in
                    state_times_by_year.values()
                ) == 50
                else "WARN"
            ),
    },

    {
        "metric":
            "temporal_positions_accounted_for",

        "value":
            (
                after_all_total
                +
                during_total
                +
                before_total
            ),

        "expected":
            total_repeat,

        "status":
            (
                "PASS"
                if (
                    after_all_total
                    +
                    during_total
                    +
                    before_total
                )
                == total_repeat
                else "FAIL"
            ),
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
        "R4F4B",

    "status":
        "R4F4B_REPEAT_RESIDUAL_TEMPORAL_POSITION_AUDIT_READY",

    "repeat_residuals":
        total_repeat,

    "repeat_before_all_development_decisions":
        before_total,

    "repeat_during_development_decision_sequence":
        during_total,

    "repeat_after_all_development_decisions":
        after_all_total,

    "interpretation":
        (
            "Repeat-derived normalized residuals are evaluated "
            "for temporal availability relative to first-attempt "
            "decision states. If they occur predominantly after "
            "the initial decision sequence, they must be treated "
            "as posterior sequential window evidence rather than "
            "contemporaneous predictors of first-run decisions."
        ),

    "revised_window_architecture": {
        "initial_sequence":
            (
                "PRESESSION_ENTRY_REFERENCE + "
                "PAST CROSS-CAR FIRST-RUN PERFORMANCE + "
                "THERMAL/WEATHER STATE"
            ),

        "later_sequence":
            (
                "INITIAL WINDOW ESTIMATE + "
                "OBSERVED CROSS-CAR REPEAT RESIDUAL UPDATES"
            ),
    },

    "next_phase":
        (
            "Construct leakage-safe pre-session performance "
            "references for first-run cross-car normalization."
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
print("GLOBAL TEMPORAL POSITION")
print("=" * 124)

print(
    f"Repeat residuals: {total_repeat}"
)

print(
    f"Before all development decisions: "
    f"{before_total}"
)

print(
    f"During development decision sequence: "
    f"{during_total}"
)

print(
    f"After all development decisions: "
    f"{after_all_total}"
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
        f"before={r['repeat_before_all_decisions']:2d} | "
        f"during={r['repeat_during_decision_sequence']:2d} | "
        f"after={r['repeat_after_all_decisions']:2d} | "
        f"first_repeat_minus_last_decision="
        f"{r['minutes_first_repeat_minus_last_decision'] or '-'} min"
    )


print()
print("=" * 124)
print("MODEL CONSEQUENCE")
print("=" * 124)

if (
    total_repeat > 0
    and
    after_all_total
    == total_repeat
):

    print(
        "ALL repeat residual evidence occurs after the "
        "development first-attempt decision sequence."
    )

    print(
        "Therefore repeat residuals CANNOT be used as "
        "contemporaneous predictors for those first-run decisions."
    )

    print(
        "They remain valid as posterior sequential evidence "
        "for later reattempt decisions and as window-model validation."
    )

else:

    print(
        "Some repeat residual evidence overlaps the "
        "development decision sequence."
    )

    print(
        "Its real-time use must be gated by exact historical "
        "availability at each decision time."
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
    "R4F4B_REPEAT_RESIDUAL_TEMPORAL_POSITION_AUDIT_READY"
)
