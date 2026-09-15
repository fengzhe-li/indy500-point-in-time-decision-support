from pathlib import Path
import csv
import json
import math
from collections import defaultdict

ROOT = Path(
    "/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈"
)

OUT = ROOT / "r4/output"
OUT.mkdir(parents=True, exist_ok=True)

INPUT = (
    OUT /
    "r4lc3_last_chance_official_records_v1.csv"
)

OUT_PANEL = (
    OUT /
    "r4lc4_last_chance_attempt_candidates_v1.csv"
)

OUT_GROUPS = (
    OUT /
    "r4lc4_last_chance_repeat_group_summary_v1.csv"
)

OUT_QA = (
    OUT /
    "r4lc4_last_chance_attempt_candidates_qa_v1.csv"
)

OUT_REPORT = (
    OUT /
    "r4lc4_last_chance_attempt_candidates_report_v1.json"
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
        return (
            x
            if math.isfinite(x)
            else None
        )
    except Exception:
        return None


def integer(v):
    x = num(v)

    if x is None:
        return None

    return int(x)


def bool_value(v):
    s = clean(v).lower()

    if s in {
        "true",
        "1",
        "yes",
    }:
        return True

    if s in {
        "false",
        "0",
        "no",
    }:
        return False

    return None


def four_lap_speed_from_times(times):
    clean_times = [
        t
        for t in times
        if t is not None
    ]

    if len(clean_times) != 4:
        return None

    total_seconds = sum(
        clean_times
    )

    if total_seconds <= 0:
        return None

    # Indianapolis Motor Speedway oval:
    # 2.5 miles/lap × 4 laps = 10 miles.
    return (
        10.0 /
        (total_seconds / 3600.0)
    )


def mean(values):
    vals = [
        v
        for v in values
        if v is not None
    ]

    if not vals:
        return None

    return sum(vals) / len(vals)


def fmt(v, digits=6):
    if v is None:
        return ""

    return f"{v:.{digits}f}"


if not INPUT.exists():
    raise SystemExit(
        f"MISSING INPUT: {INPUT}"
    )


with INPUT.open(
    "r",
    encoding="utf-8-sig",
    newline=""
) as f:

    rows = list(
        csv.DictReader(f)
    )


print("=" * 118)
print("R4LC4 — LAST CHANCE CANONICAL ATTEMPT CANDIDATES")
print("=" * 118)

print(
    f"Input official records: "
    f"{len(rows)}"
)


# =============================================================================
# 1. Group by year + entry/car
# =============================================================================

groups = defaultdict(list)

for r in rows:

    year = integer(
        r.get("year")
    )

    car = clean(
        r.get("CarNumber")
    )

    driver = (
        clean(
            r.get("DriverName")
        )
        or
        (
            clean(
                r.get("FirstName")
            )
            + " "
            + clean(
                r.get("LastName")
            )
        ).strip()
    )

    if (
        year is None
        or not car
    ):
        continue

    groups[
        (
            year,
            car,
            driver,
        )
    ].append(
        r
    )


# =============================================================================
# 2. Build canonical attempt-candidate rows
# =============================================================================

panel = []

for (
    year,
    car,
    driver
), group in sorted(
    groups.items()
):

    group_size = len(
        group
    )

    for local_index, r in enumerate(
        group,
        start=1
    ):

        lap1 = num(
            r.get("QualLap1")
        )

        lap2 = num(
            r.get("QualLap2")
        )

        lap3 = num(
            r.get("QualLap3")
        )

        lap4 = num(
            r.get("QualLap4")
        )

        laps = [
            lap1,
            lap2,
            lap3,
            lap4,
        ]

        api_speed = num(
            r.get("SpeedAvg")
        )

        recomputed_speed = (
            four_lap_speed_from_times(
                laps
            )
        )

        speed_error = None

        if (
            api_speed is not None
            and recomputed_speed is not None
        ):
            speed_error = (
                recomputed_speed
                - api_speed
            )

        first_half = mean([
            lap1,
            lap2,
        ])

        second_half = mean([
            lap3,
            lap4,
        ])

        late_run_fade_seconds = None

        if (
            first_half is not None
            and second_half is not None
        ):
            late_run_fade_seconds = (
                second_half
                - first_half
            )

        lap1_to_lap4_delta_seconds = None

        if (
            lap1 is not None
            and lap4 is not None
        ):
            lap1_to_lap4_delta_seconds = (
                lap4
                - lap1
            )

        record_index = integer(
            r.get(
                "record_index"
            )
        )

        detail_id = clean(
            r.get(
                "EventsSessionsDetailsID"
            )
        )

        position_finish = integer(
            r.get(
                "PositionFinish"
            )
        )

        is_deleted = bool_value(
            r.get(
                "IsDeleted"
            )
        )

        # Important:
        # source_record_index and DB ID are preserved as provenance.
        # Neither is promoted to true chronology without independent evidence.
        if group_size >= 2:
            repeat_evidence = (
                "MULTIPLE_OFFICIAL_RECORDS_SAME_ENTRY"
            )
        else:
            repeat_evidence = (
                "SINGLE_OFFICIAL_RECORD"
            )

        panel.append({
            "year":
                year,

            "session_regime":
                (
                    "LAST_ROW"
                    if year == 2021
                    else "LAST_CHANCE"
                ),

            "session_id":
                clean(
                    r.get(
                        "session_id"
                    )
                ),

            "car_number":
                car,

            "driver_name":
                driver,

            "team_name":
                clean(
                    r.get(
                        "TeamName"
                    )
                ),

            "official_record_index":
                (
                    record_index
                    if record_index
                    is not None
                    else ""
                ),

            "same_entry_record_index":
                local_index,

            "same_entry_record_count":
                group_size,

            "events_sessions_details_id":
                detail_id,

            "events_entrylist_id":
                clean(
                    r.get(
                        "EventsEntrylistID"
                    )
                ),

            "position_finish_raw":
                (
                    position_finish
                    if position_finish
                    is not None
                    else ""
                ),

            "elapsed_time_raw":
                clean(
                    r.get(
                        "ElapsedTime"
                    )
                ),

            "lap1_s":
                fmt(
                    lap1,
                    4
                ),

            "lap2_s":
                fmt(
                    lap2,
                    4
                ),

            "lap3_s":
                fmt(
                    lap3,
                    4
                ),

            "lap4_s":
                fmt(
                    lap4,
                    4
                ),

            "four_lap_average_speed_mph":
                fmt(
                    api_speed,
                    6
                ),

            "recomputed_four_lap_average_speed_mph":
                fmt(
                    recomputed_speed,
                    6
                ),

            "speed_recompute_error_mph":
                fmt(
                    speed_error,
                    6
                ),

            "lap1_to_lap4_delta_s":
                fmt(
                    lap1_to_lap4_delta_seconds,
                    6
                ),

            "late_run_fade_s":
                fmt(
                    late_run_fade_seconds,
                    6
                ),

            "is_deleted_api":
                (
                    is_deleted
                    if is_deleted
                    is not None
                    else ""
                ),

            "status_raw":
                clean(
                    r.get(
                        "Status"
                    )
                ),

            "repeat_evidence":
                repeat_evidence,

            "chronology_status":
                "UNRESOLVED",

            "attempt_sequence_status":
                "UNRESOLVED",

            "strategy_action":
                "UNKNOWN",

            "withdraw_before_attempt":
                "UNKNOWN",

            "result_retained_before_attempt":
                "UNKNOWN",

            "time_quality":
                "UNKNOWN",

            "source_type":
                "OFFICIAL_INDYCAR_EVENTS_SESSION_DETAILS_API",

            "source_semantics":
                (
                    "OFFICIAL_SESSION_RECORD; "
                    "DATABASE_ROW_ORDER_NOT_ASSUMED_CHRONOLOGICAL"
                ),
        })


# =============================================================================
# 3. Repeat-group summary
# =============================================================================

group_rows = []

for (
    year,
    car,
    driver
), group in sorted(
    groups.items()
):

    speeds = [
        num(
            r.get(
                "SpeedAvg"
            )
        )
        for r in group
    ]

    detail_ids = [
        clean(
            r.get(
                "EventsSessionsDetailsID"
            )
        )
        for r in group
    ]

    finish_positions = [
        clean(
            r.get(
                "PositionFinish"
            )
        )
        for r in group
    ]

    group_rows.append({
        "year":
            year,

        "car_number":
            car,

        "driver_name":
            driver,

        "official_record_count":
            len(group),

        "repeat_candidate":
            len(group) >= 2,

        "speeds_mph":
            ";".join(
                fmt(
                    x,
                    3
                )
                for x in speeds
                if x is not None
            ),

        "events_sessions_details_ids":
            ";".join(
                detail_ids
            ),

        "position_finish_values":
            ";".join(
                finish_positions
            ),

        "chronology_status":
            "UNRESOLVED",

        "interpretation":
            (
                "OFFICIAL_REPEAT_RECORD_EVIDENCE"
                if len(group) >= 2
                else
                "SINGLE_RESULT_ONLY"
            ),
    })


# =============================================================================
# 4. QA
# =============================================================================

complete_four_lap = [
    r
    for r in panel
    if all(
        clean(
            r.get(k)
        )
        for k in [
            "lap1_s",
            "lap2_s",
            "lap3_s",
            "lap4_s",
        ]
    )
]

speed_errors = [
    abs(
        num(
            r.get(
                "speed_recompute_error_mph"
            )
        )
    )
    for r in panel
    if num(
        r.get(
            "speed_recompute_error_mph"
        )
    ) is not None
]

max_speed_error = (
    max(
        speed_errors
    )
    if speed_errors
    else None
)

repeat_groups = [
    r
    for r in group_rows
    if r[
        "repeat_candidate"
    ]
]

repeat_rows = sum(
    int(
        r[
            "official_record_count"
        ]
    )
    for r in repeat_groups
)

qa_rows = [
    {
        "metric":
            "official_records_preserved",

        "value":
            len(panel),

        "expected":
            len(rows),

        "status":
            (
                "PASS"
                if len(panel)
                == len(rows)
                else "FAIL"
            ),
    },

    {
        "metric":
            "complete_four_lap_records",

        "value":
            len(
                complete_four_lap
            ),

        "expected":
            len(panel),

        "status":
            (
                "PASS"
                if len(
                    complete_four_lap
                )
                == len(panel)
                else "WARN"
            ),
    },

    {
        "metric":
            "speed_recompute_max_abs_error_mph",

        "value":
            (
                fmt(
                    max_speed_error,
                    6
                )
                if max_speed_error
                is not None
                else ""
            ),

        "expected":
            "<=0.005 mph",

        "status":
            (
                "PASS"
                if (
                    max_speed_error
                    is not None
                    and
                    max_speed_error
                    <= 0.005
                )
                else "WARN"
            ),
    },

    {
        "metric":
            "repeat_candidate_groups",

        "value":
            len(
                repeat_groups
            ),

        "expected":
            ">0",

        "status":
            (
                "PASS"
                if repeat_groups
                else "WARN"
            ),
    },

    {
        "metric":
            "strategy_actions_not_fabricated",

        "value":
            sum(
                1
                for r in panel
                if r[
                    "strategy_action"
                ]
                == "UNKNOWN"
            ),

        "expected":
            len(panel),

        "status":
            (
                "PASS"
                if all(
                    r[
                        "strategy_action"
                    ]
                    == "UNKNOWN"
                    for r in panel
                )
                else "FAIL"
            ),
    },
]


# =============================================================================
# 5. Write outputs
# =============================================================================

panel_fields = list(
    panel[0].keys()
) if panel else []

with OUT_PANEL.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=panel_fields
    )

    writer.writeheader()
    writer.writerows(
        panel
    )


group_fields = list(
    group_rows[0].keys()
) if group_rows else []

with OUT_GROUPS.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=group_fields
    )

    writer.writeheader()
    writer.writerows(
        group_rows
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


summary = {
    "phase":
        "R4LC4",

    "status":
        "R4LC4_LAST_CHANCE_CANONICAL_ATTEMPT_CANDIDATES_READY",

    "official_records":
        len(panel),

    "records_by_year": {
        str(year):
            sum(
                1
                for r in panel
                if r[
                    "year"
                ] == year
            )
        for year in sorted(
            {
                r["year"]
                for r in panel
            }
        )
    },

    "entry_groups":
        len(
            group_rows
        ),

    "repeat_candidate_groups":
        len(
            repeat_groups
        ),

    "repeat_candidate_rows":
        repeat_rows,

    "repeat_groups": [
        {
            "year":
                r[
                    "year"
                ],

            "car_number":
                r[
                    "car_number"
                ],

            "driver_name":
                r[
                    "driver_name"
                ],

            "record_count":
                r[
                    "official_record_count"
                ],

            "speeds_mph":
                r[
                    "speeds_mph"
                ],
        }
        for r in repeat_groups
    ],

    "important_constraints": [
        (
            "Official record order is preserved only as provenance "
            "and is not treated as true attempt chronology."
        ),
        (
            "EventsSessionsDetailsID is preserved but not assumed "
            "to encode chronological order."
        ),
        (
            "No withdraw/retain action is inferred from duplicate "
            "records without independent chronology evidence."
        ),
        (
            "2023 and 2024 API records currently represent only "
            "single official records per participating entry."
        ),
    ],
}


OUT_REPORT.write_text(
    json.dumps(
        summary,
        indent=2,
        ensure_ascii=False
    ),
    encoding="utf-8"
)


# =============================================================================
# 6. Console
# =============================================================================

print()
print("=" * 118)
print("YEAR / RECORD SUMMARY")
print("=" * 118)

for year in sorted(
    {
        r["year"]
        for r in panel
    }
):

    subset = [
        r
        for r in panel
        if r[
            "year"
        ] == year
    ]

    entries = {
        (
            r[
                "car_number"
            ],
            r[
                "driver_name"
            ]
        )
        for r in subset
    }

    repeated = {
        (
            r[
                "car_number"
            ],
            r[
                "driver_name"
            ]
        )
        for r in subset
        if int(
            r[
                "same_entry_record_count"
            ]
        ) >= 2
    }

    print(
        f"{year} | "
        f"records={len(subset)} | "
        f"entries={len(entries)} | "
        f"repeat_entries={len(repeated)}"
    )


print()
print("=" * 118)
print("OFFICIAL REPEAT-CANDIDATE GROUPS")
print("=" * 118)

if not repeat_groups:

    print(
        "NONE"
    )

else:

    for r in repeat_groups:

        print(
            f"{r['year']} | "
            f"car={r['car_number']} | "
            f"{r['driver_name']} | "
            f"records={r['official_record_count']} | "
            f"speeds={r['speeds_mph']} | "
            f"finish_values={r['position_finish_values']} | "
            f"detail_ids={r['events_sessions_details_ids']}"
        )


print()
print("=" * 118)
print("SPEED RECOMPUTATION QA")
print("=" * 118)

print(
    f"Complete four-lap records: "
    f"{len(complete_four_lap)}/{len(panel)}"
)

print(
    "Max |recomputed - API| speed error: "
    + (
        f"{max_speed_error:.6f} mph"
        if max_speed_error
        is not None
        else "N/A"
    )
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

    print()
    print("FAILED QA")

    for r in fails:

        print(
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
    OUT_GROUPS.relative_to(ROOT)
)
print(
    OUT_QA.relative_to(ROOT)
)
print(
    OUT_REPORT.relative_to(ROOT)
)

print()
print(
    "R4LC4_LAST_CHANCE_CANONICAL_ATTEMPT_CANDIDATES_READY"
)
