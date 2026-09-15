from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path("/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈")

SRC = (
    ROOT /
    "r6_regime_extension/evidence/official_api_v2/"
    "regime_extension_all_session_records_v1.csv"
)

OUT = (
    ROOT /
    "r6_regime_extension/output"
)

OUT.mkdir(
    parents=True,
    exist_ok=True
)

df = pd.read_csv(
    SRC,
    low_memory=False
)

# ============================================================
# target sessions
# ============================================================

TARGETS = {
    2018: "Qualifications - Day 1",
    2019: "Qualifications - Day 1",
    2025: "Qualifications - Day 1",
    2026: "Combined Qualifying",
}

core_parts = []

for year, session_name in TARGETS.items():

    part = df[
        (pd.to_numeric(
            df["year"],
            errors="coerce"
        ) == year)
        &
        (
            df["session_name"]
            .astype(str)
            == session_name
        )
    ].copy()

    core_parts.append(
        part
    )

core = pd.concat(
    core_parts,
    ignore_index=True,
    sort=False
)

# ============================================================
# cleanup
# ============================================================

for c in [
    "PositionFinish",
    "SpeedAvg",
    "QualLap1",
    "QualLap2",
    "QualLap3",
    "QualLap4",
]:

    if c in core.columns:

        core[c] = pd.to_numeric(
            core[c],
            errors="coerce"
        )

core["CarNumber"] = (
    core["CarNumber"]
    .astype(str)
    .str.strip()
)

core["DriverName"] = (
    core["DriverName"]
    .astype(str)
    .str.strip()
)

# Complete 4-lap attempt:
# all four timed laps must be strictly positive.
lap_cols = [
    "QualLap1",
    "QualLap2",
    "QualLap3",
    "QualLap4",
]

core[
    "complete_four_lap_attempt"
] = (
    core[lap_cols]
    .notna()
    .all(axis=1)
    &
    (
        core[lap_cols]
        > 0
    )
    .all(axis=1)
)

core[
    "timed_lap_count"
] = (
    core[lap_cols]
    .fillna(0)
    .gt(0)
    .sum(axis=1)
)

# ============================================================
# stable within-session source order
# ============================================================

core[
    "api_row_order"
] = (
    core
    .groupby(
        [
            "year",
            "session_name"
        ],
        sort=False
    )
    .cumcount()
    + 1
)

# IMPORTANT:
# api_row_order is only source row order.
# It is NOT yet accepted as chronology.

# ============================================================
# car occurrence / repeats
# ============================================================

core[
    "car_occurrence_index"
] = (
    core
    .groupby(
        [
            "year",
            "session_name",
            "CarNumber"
        ],
        sort=False
    )
    .cumcount()
    + 1
)

core[
    "car_session_record_count"
] = (
    core
    .groupby(
        [
            "year",
            "session_name",
            "CarNumber"
        ]
    )["CarNumber"]
    .transform("size")
)

core[
    "is_repeat_car_record"
] = (
    core[
        "car_session_record_count"
    ]
    > 1
)

# Count complete attempts per car
complete_counts = (
    core[
        core[
            "complete_four_lap_attempt"
        ]
    ]
    .groupby(
        [
            "year",
            "session_name",
            "CarNumber"
        ]
    )
    .size()
    .rename(
        "complete_attempts_for_car"
    )
    .reset_index()
)

core = core.merge(
    complete_counts,
    on=[
        "year",
        "session_name",
        "CarNumber"
    ],
    how="left"
)

core[
    "complete_attempts_for_car"
] = (
    core[
        "complete_attempts_for_car"
    ]
    .fillna(0)
    .astype(int)
)

core[
    "has_repeat_complete_attempt"
] = (
    core[
        "complete_attempts_for_car"
    ]
    >= 2
)

# ============================================================
# summary by year
# ============================================================

summary_rows = []

for year, session_name in TARGETS.items():

    s = core[
        (core["year"] == year)
        &
        (
            core["session_name"]
            == session_name
        )
    ].copy()

    unique_cars = (
        s["CarNumber"]
        .nunique()
    )

    complete = int(
        s[
            "complete_four_lap_attempt"
        ]
        .sum()
    )

    repeat_cars = int(
        (
            s.groupby(
                "CarNumber"
            )
            .size()
            > 1
        ).sum()
    )

    repeat_complete_cars = int(
        (
            s[
                s[
                    "complete_four_lap_attempt"
                ]
            ]
            .groupby(
                "CarNumber"
            )
            .size()
            >= 2
        ).sum()
    )

    complete_repeat_transitions = 0

    if not s.empty:

        for car, g in (
            s[
                s[
                    "complete_four_lap_attempt"
                ]
            ]
            .groupby(
                "CarNumber"
            )
        ):

            n = len(g)

            if n >= 2:
                complete_repeat_transitions += (
                    n - 1
                )

    summary_rows.append({
        "year":
            year,

        "session_name":
            session_name,

        "total_api_records":
            len(s),

        "unique_cars":
            unique_cars,

        "complete_four_lap_records":
            complete,

        "incomplete_or_aborted_records":
            len(s) - complete,

        "cars_with_multiple_records":
            repeat_cars,

        "cars_with_2plus_complete_attempts":
            repeat_complete_cars,

        "potential_complete_repeat_transitions":
            complete_repeat_transitions,
    })

summary = pd.DataFrame(
    summary_rows
)

# ============================================================
# repeat-car detail
# ============================================================

repeat_detail = core[
    core[
        "is_repeat_car_record"
    ]
].copy()

show_cols = [
    "year",
    "session_name",
    "api_row_order",
    "PositionFinish",
    "CarNumber",
    "DriverName",
    "car_occurrence_index",
    "QualLap1",
    "QualLap2",
    "QualLap3",
    "QualLap4",
    "timed_lap_count",
    "SpeedAvg",
    "complete_four_lap_attempt",
    "complete_attempts_for_car",
]

show_cols = [
    c
    for c in show_cols
    if c in repeat_detail.columns
]

# ============================================================
# chronology plausibility screen
# ============================================================

# If PositionFinish is unique sequential 1..N,
# it might merely be API record order,
# but we do NOT accept chronology yet.

chronology_rows = []

for year, session_name in TARGETS.items():

    s = core[
        (core["year"] == year)
        &
        (
            core["session_name"]
            == session_name
        )
    ].copy()

    pos = (
        pd.to_numeric(
            s["PositionFinish"],
            errors="coerce"
        )
        if "PositionFinish" in s.columns
        else pd.Series(
            dtype=float
        )
    )

    expected = set(
        range(
            1,
            len(s) + 1
        )
    )

    observed = set(
        pos.dropna()
        .astype(int)
        .tolist()
    )

    sequential = (
        observed == expected
    )

    chronology_rows.append({
        "year":
            year,

        "session_name":
            session_name,

        "records":
            len(s),

        "positionfinish_unique":
            pos.nunique(
                dropna=True
            ),

        "positionfinish_is_exact_1_to_n":
            sequential,

        "api_row_equals_positionfinish_pct":
            (
                100.0
                *
                (
                    s[
                        "api_row_order"
                    ]
                    ==
                    pos
                )
                .mean()
                if len(s)
                else np.nan
            ),

        "chronology_status":
            (
                "UNVERIFIED_SOURCE_ORDER_ONLY"
            )
    })

chronology = pd.DataFrame(
    chronology_rows
)

# ============================================================
# write
# ============================================================

CORE_OUT = (
    OUT /
    "regime_core_attempt_inventory_v1.csv"
)

SUMMARY_OUT = (
    OUT /
    "regime_attempt_inventory_summary_v1.csv"
)

REPEAT_OUT = (
    OUT /
    "regime_repeat_car_records_v1.csv"
)

CHRONOLOGY_OUT = (
    OUT /
    "regime_attempt_order_semantics_audit_v1.csv"
)

core.to_csv(
    CORE_OUT,
    index=False
)

summary.to_csv(
    SUMMARY_OUT,
    index=False
)

repeat_detail.to_csv(
    REPEAT_OUT,
    index=False
)

chronology.to_csv(
    CHRONOLOGY_OUT,
    index=False
)

# ============================================================
# print
# ============================================================

print("=" * 150)
print("PART 1 — REGIME ATTEMPT INVENTORY SUMMARY")
print("=" * 150)

print(
    summary
    .to_string(
        index=False
    )
)

print("\n" + "=" * 150)
print("PART 2 — REPEAT-CAR RECORDS")
print("=" * 150)

if repeat_detail.empty:

    print(
        "NO MULTIPLE RECORDS FOUND"
    )

else:

    print(
        repeat_detail[
            show_cols
        ]
        .sort_values(
            [
                "year",
                "CarNumber",
                "api_row_order",
            ]
        )
        .to_string(
            index=False
        )
    )

print("\n" + "=" * 150)
print("PART 3 — ATTEMPT ORDER SEMANTICS")
print("=" * 150)

print(
    chronology
    .round(2)
    .to_string(
        index=False
    )
)

print("\nOUTPUTS:")
print(
    CORE_OUT.relative_to(ROOT)
)
print(
    SUMMARY_OUT.relative_to(ROOT)
)
print(
    REPEAT_OUT.relative_to(ROOT)
)
print(
    CHRONOLOGY_OUT.relative_to(ROOT)
)

print(
    "\nR6_REGIME_ATTEMPT_INVENTORY_AUDIT_V1_COMPLETE"
)
