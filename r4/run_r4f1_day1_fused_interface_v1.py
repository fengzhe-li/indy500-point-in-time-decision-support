from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime, timezone
import csv
import json
import math

ROOT = Path(
    "/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈"
)

OUT = ROOT / "r4/output"
OUT.mkdir(parents=True, exist_ok=True)

ATTEMPT_PATH = (
    OUT /
    "r4p1_attempt_four_lap_panel_v1.csv"
)

CHRONOLOGY_PATH = (
    ROOT /
    "weather/output/"
    "unified_attempt_chronology_constraint_ledger_v10.csv"
)

FUSED_SCHEMA_PATH = (
    OUT /
    "r4lc5e_fused_decision_schema_contract_v2.json"
)

OUT_PANEL = (
    OUT /
    "r4f1_day1_fused_interface_v1.csv"
)

OUT_SUMMARY = (
    OUT /
    "r4f1_day1_fused_interface_summary_v1.csv"
)

OUT_QA = (
    OUT /
    "r4f1_day1_fused_interface_qa_v1.csv"
)

OUT_REPORT = (
    OUT /
    "r4f1_day1_fused_interface_report_v1.json"
)


TRAIN_YEARS = {
    2020,
    2021,
    2023,
}

VALIDATION_YEARS = {
    2022,
    2024,
}

CUTOFF_RANK = {
    2020: 9,
    2021: 9,
    2022: 12,
    2023: 12,
    2024: 12,
}


STOP = "STOP"

RETAIN_AND_REATTEMPT = (
    "RETAIN_AND_REATTEMPT"
)

WITHDRAW_AND_PRIORITY_REATTEMPT = (
    "WITHDRAW_AND_PRIORITY_REATTEMPT"
)

UNRESOLVED_REATTEMPT = (
    "REATTEMPT_SEMANTICS_UNRESOLVED"
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


def clean(v):
    if v is None:
        return ""

    return str(v).strip()


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


def truth(v):
    return clean(v).lower() in {
        "true",
        "1",
        "yes",
    }


def parse_dt(v):
    s = clean(v)

    if not s:
        return None

    if s.upper() == "UNKNOWN":
        return None

    s = s.replace(
        "Z",
        "+00:00"
    )

    try:
        dt = datetime.fromisoformat(
            s
        )
    except Exception:
        return None

    if dt.tzinfo is None:
        dt = dt.replace(
            tzinfo=timezone.utc
        )

    return dt.astimezone(
        timezone.utc
    )


def first_existing(fields, candidates):
    for c in candidates:

        if c in fields:
            return c

    return None


for path in [
    ATTEMPT_PATH,
    CHRONOLOGY_PATH,
    FUSED_SCHEMA_PATH,
]:

    if not path.exists():

        raise SystemExit(
            f"MISSING INPUT: {path}"
        )


attempts = read_csv(
    ATTEMPT_PATH
)

chronology = read_csv(
    CHRONOLOGY_PATH
)

schema = json.loads(
    FUSED_SCHEMA_PATH.read_text(
        encoding="utf-8"
    )
)


print("=" * 122)
print("R4F1 — DAY1 → FUSED V2 DECISION INTERFACE")
print("=" * 122)

print(
    f"Attempt rows: "
    f"{len(attempts)}"
)

print(
    f"Chronology rows: "
    f"{len(chronology)}"
)

print(
    f"Frozen schema: "
    f"{schema.get('schema_name')}"
)


if not attempts:
    raise SystemExit(
        "EMPTY ATTEMPT PANEL"
    )


fields = set(
    attempts[0].keys()
)


YEAR_COL = first_existing(
    fields,
    [
        "year",
    ]
)

ATTEMPT_ID_COL = first_existing(
    fields,
    [
        "attempt_id",
    ]
)

CAR_COL = first_existing(
    fields,
    [
        "car_number",
    ]
)

DRIVER_COL = first_existing(
    fields,
    [
        "driver_name",
    ]
)

INDEX_COL = first_existing(
    fields,
    [
        "car_attempt_index",
    ]
)

SPEED_COL = first_existing(
    fields,
    [
        "four_lap_average_speed_mph",
        "speed_mph",
    ]
)

STATUS_COL = first_existing(
    fields,
    [
        "result_status",
    ]
)

TIME_COL = first_existing(
    fields,
    [
        "time_point_utc",
    ]
)

TIME_CLASS_COL = first_existing(
    fields,
    [
        "time_evidence_class",
        "canonical_event_time_quality",
    ]
)

LANE_COL = first_existing(
    fields,
    [
        "lane_action",
    ]
)


required = [
    YEAR_COL,
    ATTEMPT_ID_COL,
    CAR_COL,
    INDEX_COL,
]

if any(
    c is None
    for c in required
):

    raise SystemExit(
        "REQUIRED R4P1 COLUMN UNRESOLVED"
    )


# =============================================================================
# Chronology lookup
# =============================================================================

chron_by_id = {}

for r in chronology:

    aid = clean(
        r.get(
            "attempt_id"
        )
    )

    if not aid:
        continue

    chron_by_id[
        aid
    ] = r


# =============================================================================
# Canonical attempt objects
# =============================================================================

canonical = []

for r in attempts:

    year = integer(
        r.get(
            YEAR_COL
        )
    )

    if year not in CUTOFF_RANK:
        continue

    attempt_id = clean(
        r.get(
            ATTEMPT_ID_COL
        )
    )

    car = clean(
        r.get(
            CAR_COL
        )
    )

    index = integer(
        r.get(
            INDEX_COL
        )
    )

    if (
        not attempt_id
        or not car
        or index is None
    ):
        continue

    c = chron_by_id.get(
        attempt_id,
        {}
    )

    time_point = parse_dt(
        r.get(
            TIME_COL
        )
        if TIME_COL
        else ""
    )

    if time_point is None:

        time_point = parse_dt(
            c.get(
                "time_point_utc"
            )
        )

    speed = (
        num(
            r.get(
                SPEED_COL
            )
        )
        if SPEED_COL
        else None
    )

    result_status = (
        clean(
            r.get(
                STATUS_COL
            )
        )
        if STATUS_COL
        else ""
    )

    chronology_action = clean(
        c.get(
            "action"
        )
    )

    chronology_lane = clean(
        c.get(
            "lane"
        )
    )

    r4_lane = (
        clean(
            r.get(
                LANE_COL
            )
        )
        if LANE_COL
        else ""
    )

    canonical.append({
        "year":
            year,

        "attempt_id":
            attempt_id,

        "car_number":
            car,

        "driver_name":
            (
                clean(
                    r.get(
                        DRIVER_COL
                    )
                )
                if DRIVER_COL
                else ""
            ),

        "car_attempt_index":
            index,

        "speed_mph":
            speed,

        "result_status":
            result_status,

        "time_point":
            time_point,

        "time_point_utc":
            (
                time_point.isoformat()
                if time_point
                else ""
            ),

        "time_quality":
            (
                clean(
                    r.get(
                        TIME_CLASS_COL
                    )
                )
                if TIME_CLASS_COL
                else ""
            ),

        "chronology_action":
            chronology_action,

        "chronology_lane":
            chronology_lane,

        "r4_lane_action":
            r4_lane,

        "chronology_usable":
            (
                truth(
                    c.get(
                        "chronology_usable"
                    )
                )
                if c
                else False
            ),
    })


# =============================================================================
# Group attempts by year/car
# =============================================================================

by_entry = defaultdict(list)

for r in canonical:

    by_entry[
        (
            r["year"],
            r["car_number"],
        )
    ].append(
        r
    )


for key in by_entry:

    by_entry[
        key
    ].sort(
        key=lambda r: (
            r[
                "car_attempt_index"
            ],
            r[
                "attempt_id"
            ],
        )
    )


# =============================================================================
# Determine reattempt action semantics
# =============================================================================

def resolve_repeat_action(
    first,
    later_attempts,
):

    if not later_attempts:

        return (
            STOP,
            "NO_LATER_ATTEMPT_OBSERVED",
            "HIGH"
        )

    next_attempt = later_attempts[
        0
    ]

    evidence = " | ".join(
        [
            clean(
                next_attempt.get(
                    "chronology_action"
                )
            ),
            clean(
                next_attempt.get(
                    "chronology_lane"
                )
            ),
            clean(
                next_attempt.get(
                    "r4_lane_action"
                )
            ),
        ]
    ).upper()

    if (
        "LANE_1" in evidence
        or
        "LANE1" in evidence
        or
        "WITHDRAW_EXISTING_RESULT"
        in evidence
    ):

        return (
            WITHDRAW_AND_PRIORITY_REATTEMPT,
            evidence,
            "HIGH"
        )

    if (
        "LANE_2" in evidence
        or
        "LANE2" in evidence
        or
        "RETAIN" in evidence
        and
        "REATTEMPT" in evidence
    ):

        return (
            RETAIN_AND_REATTEMPT,
            evidence,
            "HIGH"
        )

    return (
        UNRESOLVED_REATTEMPT,
        evidence,
        "PARTIAL"
    )


# =============================================================================
# Reconstruct point-time leaderboard
#
# Only attempts that have a point timestamp <= decision time are admitted.
# For each car, only its best observed valid numeric result is retained.
# =============================================================================

def leaderboard_at(
    year,
    decision_dt,
):

    if decision_dt is None:
        return None

    observed = [
        r
        for r in canonical
        if (
            r["year"] == year
            and
            r["time_point"] is not None
            and
            r["time_point"]
            <= decision_dt
            and
            r["speed_mph"] is not None
        )
    ]

    best_by_car = {}

    for r in observed:

        car = r[
            "car_number"
        ]

        current = best_by_car.get(
            car
        )

        if (
            current is None
            or
            r["speed_mph"]
            >
            current["speed_mph"]
        ):

            best_by_car[
                car
            ] = r

    ranked = sorted(
        best_by_car.values(),
        key=lambda r: (
            -r[
                "speed_mph"
            ],
            r[
                "car_number"
            ],
        )
    )

    return ranked


# =============================================================================
# Build one decision opportunity after first observed attempt per entry
# =============================================================================

rows = []

for (
    year,
    car
), group in sorted(
    by_entry.items()
):

    first_candidates = [
        r
        for r in group
        if r[
            "car_attempt_index"
        ] == 1
    ]

    if not first_candidates:
        continue

    first = first_candidates[
        0
    ]

    later = [
        r
        for r in group
        if r[
            "car_attempt_index"
        ] > 1
    ]

    observed_action, action_evidence, action_quality = (
        resolve_repeat_action(
            first,
            later
        )
    )

    board = leaderboard_at(
        year,
        first[
            "time_point"
        ]
    )

    current_rank = None
    benchmark_speed = None

    cutoff_rank = CUTOFF_RANK[
        year
    ]

    if board is not None:

        for idx, entry in enumerate(
            board,
            start=1
        ):

            if entry[
                "car_number"
            ] == car:

                current_rank = idx
                break

        if len(
            board
        ) >= cutoff_rank:

            benchmark_speed = board[
                cutoff_rank - 1
            ][
                "speed_mph"
            ]

    margin = None

    if (
        first[
            "speed_mph"
        ] is not None
        and
        benchmark_speed is not None
    ):

        margin = (
            first[
                "speed_mph"
            ]
            - benchmark_speed
        )

    if year in TRAIN_YEARS:

        evidence_role = (
            "TRAIN_CORE_CANDIDATE"
        )

    elif year in VALIDATION_YEARS:

        evidence_role = (
            "VALIDATION_ONLY"
        )

    else:

        evidence_role = (
            "EXCLUDED"
        )


    # =========================================================================
    # Action masks
    #
    # Normal Day1 after a valid held result:
    # STOP / retain+reattempt / withdraw+priority reattempt.
    #
    # If result status indicates invalid/disallowed, this is not a normal
    # protected-result strategic decision and must not be policy-fit.
    # =========================================================================

    status_upper = (
        first[
            "result_status"
        ].upper()
    )

    invalid_result = any(
        token in status_upper
        for token in [
            "DISALLOW",
            "INVALID",
            "WAVED",
            "ABORT",
        ]
    )

    has_protected_result = (
        first[
            "speed_mph"
        ] is not None
        and
        not invalid_result
    )

    if has_protected_result:

        feasible = (
            "STOP|"
            "RETAIN_AND_REATTEMPT|"
            "WITHDRAW_AND_PRIORITY_REATTEMPT"
        )

        mask_stop = True
        mask_retain = True
        mask_priority = True

    else:

        feasible = (
            "STOP|REATTEMPT"
        )

        mask_stop = True
        mask_retain = False
        mask_priority = False


    state_numeric = (
        first[
            "speed_mph"
        ] is not None
        and
        current_rank is not None
        and
        benchmark_speed is not None
    )

    decision_time_safe = (
        first[
            "time_point"
        ] is not None
    )

    action_fit_safe = (
        evidence_role
        == "TRAIN_CORE_CANDIDATE"
        and
        action_quality
        == "HIGH"
        and
        observed_action
        in {
            STOP,
            RETAIN_AND_REATTEMPT,
            WITHDRAW_AND_PRIORITY_REATTEMPT,
        }
        and
        has_protected_result
    )

    rows.append({
        "decision_id":
            (
                f"DAY1_{year}_{car}_"
                f"POST_FIRST_ATTEMPT"
            ),

        "year":
            year,

        "session_regime":
            "DAY1",

        "car_number":
            car,

        "driver_name":
            first[
                "driver_name"
            ],

        "decision_stage":
            "POST_FIRST_ATTEMPT",

        "source_attempt_id":
            first[
                "attempt_id"
            ],

        "source_attempt_index":
            first[
                "car_attempt_index"
            ],

        "later_attempt_count":
            len(
                later
            ),

        "current_result_mph":
            (
                f"{first['speed_mph']:.6f}"
                if first[
                    "speed_mph"
                ]
                is not None
                else ""
            ),

        "current_rank":
            (
                current_rank
                if current_rank
                is not None
                else ""
            ),

        "benchmark_type":
            (
                "FAST_NINE_ADVANCEMENT"
                if cutoff_rank == 9
                else
                "TOP_12_ADVANCEMENT"
            ),

        "benchmark_rank":
            cutoff_rank,

        "benchmark_speed_mph":
            (
                f"{benchmark_speed:.6f}"
                if benchmark_speed
                is not None
                else ""
            ),

        "margin_to_benchmark_mph":
            (
                f"{margin:.6f}"
                if margin
                is not None
                else ""
            ),

        "qualification_state":
            (
                "CURRENTLY_INSIDE_ADVANCEMENT"
                if (
                    current_rank
                    is not None
                    and
                    current_rank
                    <= cutoff_rank
                )
                else
                "CURRENTLY_OUTSIDE_ADVANCEMENT"
                if current_rank
                is not None
                else
                "UNKNOWN"
            ),

        "has_protected_result":
            has_protected_result,

        "feasible_action_set":
            feasible,

        "action_mask_STOP":
            mask_stop,

        "action_mask_REATTEMPT":
            not has_protected_result,

        "action_mask_RETAIN_AND_REATTEMPT":
            mask_retain,

        "action_mask_WITHDRAW_AND_REATTEMPT":
            False,

        "action_mask_WITHDRAW_AND_PRIORITY_REATTEMPT":
            mask_priority,

        "observed_action_unified":
            observed_action,

        "observed_action_quality":
            action_quality,

        "observed_action_evidence":
            action_evidence,

        "decision_time_utc":
            first[
                "time_point_utc"
            ],

        "time_quality":
            first[
                "time_quality"
            ],

        "decision_time_safe":
            decision_time_safe,

        "state_numeric_complete":
            state_numeric,

        "thermal_state_available":
            False,

        "performance_uncertainty_available":
            True,

        "wait_model_available":
            True,

        "shared_feature_link_status":
            "PERFORMANCE_AND_WAIT_READY_THERMAL_PENDING",

        "evidence_role":
            evidence_role,

        "safe_for_policy_fit":
            action_fit_safe,

        "source":
            (
                "R4P1_ATTEMPT_PANEL_PLUS_"
                "CHRONOLOGY_V10"
            ),
    })


# =============================================================================
# QA
# =============================================================================

action_counts = Counter(
    r[
        "observed_action_unified"
    ]
    for r in rows
)

year_counts = Counter(
    r[
        "year"
    ]
    for r in rows
)

validation_fit_leak = [
    r
    for r in rows
    if (
        r[
            "year"
        ]
        in VALIDATION_YEARS
        and
        r[
            "safe_for_policy_fit"
        ]
    )
]

bad_last_chance_action = [
    r
    for r in rows
    if r[
        "action_mask_WITHDRAW_AND_REATTEMPT"
    ]
]

bad_core_year = [
    r
    for r in rows
    if (
        r[
            "safe_for_policy_fit"
        ]
        and
        r[
            "year"
        ]
        not in TRAIN_YEARS
    )
]

qa_rows = [
    {
        "metric":
            "day1_decision_rows",

        "value":
            len(rows),

        "expected":
            ">0",

        "status":
            (
                "PASS"
                if rows
                else "FAIL"
            ),
    },

    {
        "metric":
            "2022_2024_validation_leakage",

        "value":
            len(
                validation_fit_leak
            ),

        "expected":
            0,

        "status":
            (
                "PASS"
                if not validation_fit_leak
                else "FAIL"
            ),
    },

    {
        "metric":
            "day1_never_uses_last_chance_withdraw_action",

        "value":
            len(
                bad_last_chance_action
            ),

        "expected":
            0,

        "status":
            (
                "PASS"
                if not bad_last_chance_action
                else "FAIL"
            ),
    },

    {
        "metric":
            "policy_fit_only_core_years",

        "value":
            len(
                bad_core_year
            ),

        "expected":
            0,

        "status":
            (
                "PASS"
                if not bad_core_year
                else "FAIL"
            ),
    },

    {
        "metric":
            "frozen_schema_loaded",

        "value":
            schema.get(
                "schema_status"
            ),

        "expected":
            "ACTION_SEMANTICS_FROZEN",

        "status":
            (
                "PASS"
                if schema.get(
                    "schema_status"
                )
                ==
                "ACTION_SEMANTICS_FROZEN"
                else "FAIL"
            ),
    },
]


# =============================================================================
# Summary
# =============================================================================

summary_rows = []

for year in sorted(
    year_counts
):

    subset = [
        r
        for r in rows
        if r[
            "year"
        ] == year
    ]

    summary_rows.append({
        "year":
            year,

        "rows":
            len(
                subset
            ),

        "point_time_rows":
            sum(
                bool(
                    r[
                        "decision_time_utc"
                    ]
                )
                for r in subset
            ),

        "numeric_state_rows":
            sum(
                bool(
                    r[
                        "state_numeric_complete"
                    ]
                )
                for r in subset
            ),

        "STOP":
            sum(
                r[
                    "observed_action_unified"
                ] == STOP
                for r in subset
            ),

        "RETAIN_AND_REATTEMPT":
            sum(
                r[
                    "observed_action_unified"
                ]
                ==
                RETAIN_AND_REATTEMPT
                for r in subset
            ),

        "WITHDRAW_AND_PRIORITY_REATTEMPT":
            sum(
                r[
                    "observed_action_unified"
                ]
                ==
                WITHDRAW_AND_PRIORITY_REATTEMPT
                for r in subset
            ),

        "UNRESOLVED_REATTEMPT":
            sum(
                r[
                    "observed_action_unified"
                ]
                ==
                UNRESOLVED_REATTEMPT
                for r in subset
            ),

        "policy_fit_rows":
            sum(
                bool(
                    r[
                        "safe_for_policy_fit"
                    ]
                )
                for r in subset
            ),

        "evidence_role":
            (
                "TRAIN_CORE"
                if year
                in TRAIN_YEARS
                else
                "VALIDATION_ONLY"
            ),
    })


# =============================================================================
# Save
# =============================================================================

with OUT_PANEL.open(
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
        "R4F1",

    "status":
        "R4F1_DAY1_FUSED_INTERFACE_READY",

    "decision_rows":
        len(rows),

    "action_counts":
        dict(
            action_counts
        ),

    "training_years":
        sorted(
            TRAIN_YEARS
        ),

    "validation_only_years":
        sorted(
            VALIDATION_YEARS
        ),

    "policy_fit_rows":
        sum(
            bool(
                r[
                    "safe_for_policy_fit"
                ]
            )
            for r in rows
        ),

    "numeric_state_rows":
        sum(
            bool(
                r[
                    "state_numeric_complete"
                ]
            )
            for r in rows
        ),

    "important_methodology": [
        (
            "Current rank and advancement benchmark are reconstructed "
            "only from attempts with point timestamps at or before the "
            "decision time."
        ),
        (
            "2022 and 2024 are emitted for validation but prohibited "
            "from policy fitting."
        ),
        (
            "Repeat attempts without explicit Lane1/Lane2 semantics "
            "remain REATTEMPT_SEMANTICS_UNRESOLVED."
        ),
        (
            "No future final qualifying cutoff is substituted for the "
            "decision-time benchmark."
        ),
    ],

    "next_phase":
        (
            "Combine R4F1 Day1 interface with frozen R4LC5E-v2 "
            "Last Chance interface into the canonical Fused dataset."
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
print("=" * 122)
print("DAY1 ACTION COUNTS")
print("=" * 122)

for action in sorted(
    action_counts
):

    print(
        f"{action:40s} | "
        f"{action_counts[action]}"
    )


print()
print("=" * 122)
print("YEAR SUMMARY")
print("=" * 122)

for r in summary_rows:

    print(
        f"{r['year']} | "
        f"rows={r['rows']} | "
        f"point={r['point_time_rows']} | "
        f"numeric={r['numeric_state_rows']} | "
        f"STOP={r['STOP']} | "
        f"retain={r['RETAIN_AND_REATTEMPT']} | "
        f"priority={r['WITHDRAW_AND_PRIORITY_REATTEMPT']} | "
        f"unresolved={r['UNRESOLVED_REATTEMPT']} | "
        f"fit={r['policy_fit_rows']} | "
        f"{r['evidence_role']}"
    )


print()
print("=" * 122)
print("POLICY-FIT DAY1 ROWS")
print("=" * 122)

fit_rows = [
    r
    for r in rows
    if r[
        "safe_for_policy_fit"
    ]
]

for r in fit_rows[:80]:

    print(
        f"{r['decision_id']} | "
        f"rank={r['current_rank'] or '-'} | "
        f"benchmark="
        f"{r['benchmark_speed_mph'] or '-'} | "
        f"margin="
        f"{r['margin_to_benchmark_mph'] or '-'} | "
        f"action="
        f"{r['observed_action_unified']} | "
        f"time="
        f"{r['decision_time_utc'] or '-'}"
    )


print()
print(
    f"Policy-fit rows: "
    f"{len(fit_rows)}"
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
    OUT_PANEL.relative_to(ROOT)
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
    "R4F1_DAY1_FUSED_INTERFACE_READY"
)
