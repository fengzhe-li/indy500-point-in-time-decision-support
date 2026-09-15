from pathlib import Path
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import json
import math
import re

import pandas as pd
import numpy as np

ROOT = Path("/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈")

ANALYSIS_DIR = (
    ROOT /
    "r6_regime_extension/evidence/timing71_indy500_v2"
)

OFFICIAL = (
    ROOT /
    "r6_regime_extension/output/regime_attempt_inventory_v3/"
    "regime_official_attempt_inventory_v3.csv"
)

OUT = (
    ROOT /
    "r6_regime_extension/output/timing71_attempt_reconstruction_v1"
)

OUT.mkdir(
    parents=True,
    exist_ok=True
)

INDY_TZ = ZoneInfo(
    "America/Indiana/Indianapolis"
)

TARGET_YEARS = [
    2018,
    2019,
    2025,
]

# ------------------------------------------------------------
# Utilities
# ------------------------------------------------------------

def norm_car(x):
    return str(x).strip().upper()


def ts_to_utc(ts_ms):

    return datetime.fromtimestamp(
        float(ts_ms) / 1000.0,
        tz=timezone.utc
    )


def ts_to_indy(ts_ms):

    return ts_to_utc(
        ts_ms
    ).astimezone(
        INDY_TZ
    )


def fourlap_speed_from_times(laps):

    total_s = sum(
        laps
    )

    if total_s <= 0:
        return np.nan

    # 4 laps × 2.5 miles = 10 miles
    return 10.0 / (
        total_s / 3600.0
    )


# ============================================================
# Load official attempt inventory
# ============================================================

official = pd.read_csv(
    OFFICIAL,
    low_memory=False
)

official = official[
    official["year"].isin(
        TARGET_YEARS
    )
].copy()

official["car_key"] = (
    official["car_number"]
    .astype(str)
    .map(norm_car)
)

# ============================================================
# Parse all Timing71 analysis JSONs
# ============================================================

lap_rows = []

files = sorted(
    ANALYSIS_DIR.glob(
        "*_analysis.json"
    )
)

print("=" * 160)
print("PART 1 — ANALYSIS FILES")
print("=" * 160)

for path in files:

    m = re.match(
        r"^(2018|2019|2025)_",
        path.name
    )

    if not m:
        continue

    year = int(
        m.group(1)
    )

    print(
        year,
        path.name
    )

    payload = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    # Timing71 analysis structure observed:
    # payload["cars"]["cars"][car_number]["stints"][...]["laps"]
    cars_root = (
        payload.get(
            "cars",
            {}
        )
        .get(
            "cars",
            {}
        )
    )

    if not isinstance(
        cars_root,
        dict
    ):
        continue

    for car_id, car_obj in cars_root.items():

        car_number = norm_car(
            car_id
        )

        if not isinstance(
            car_obj,
            dict
        ):
            continue

        stints = car_obj.get(
            "stints",
            []
        )

        if not isinstance(
            stints,
            list
        ):
            continue

        for stint_index, stint in enumerate(
            stints
        ):

            if not isinstance(
                stint,
                dict
            ):
                continue

            laps = stint.get(
                "laps",
                []
            )

            if not isinstance(
                laps,
                list
            ):
                continue

            for lap_index, lap in enumerate(
                laps
            ):

                if not isinstance(
                    lap,
                    dict
                ):
                    continue

                lap_number = lap.get(
                    "lapNumber"
                )

                laptime = lap.get(
                    "laptime"
                )

                timestamp = lap.get(
                    "timestamp"
                )

                flag = lap.get(
                    "flag"
                )

                if (
                    lap_number is None
                    or laptime is None
                    or timestamp is None
                ):
                    continue

                try:

                    lap_number = int(
                        lap_number
                    )

                    laptime = float(
                        laptime
                    )

                    timestamp = int(
                        timestamp
                    )

                except Exception:
                    continue

                lap_rows.append({
                    "year":
                        year,

                    "analysis_file":
                        path.name,

                    "car_number":
                        car_number,

                    "stint_index":
                        stint_index,

                    "lap_index":
                        lap_index,

                    "lap_number":
                        lap_number,

                    "laptime_s":
                        laptime,

                    "timestamp_ms":
                        timestamp,

                    "timestamp_utc":
                        ts_to_utc(
                            timestamp
                        ).isoformat(),

                    "timestamp_indianapolis":
                        ts_to_indy(
                            timestamp
                        ).isoformat(),

                    "flag":
                        flag,
                })

laps = pd.DataFrame(
    lap_rows
)

if laps.empty:
    raise RuntimeError(
        "No lap rows parsed"
    )

laps = laps.sort_values(
    [
        "year",
        "timestamp_ms",
        "car_number",
        "lap_number",
    ]
)

# ============================================================
# Detect four consecutive green timed laps
# ============================================================
#
# Qualifying run signature:
# usually an out/opening lap followed by four ~38–40 sec laps.
#
# We DO NOT assume lap numbers reset.
# We search chronological lap stream for windows of 4 laps:
# - same car
# - consecutive chronological records
# - all plausible oval qualifying lap times
# - timestamps close together
#
# Broad plausible laptime range:
# 35–55 sec
#
# Window duration constraint:
# < 4 minutes from first lap timestamp to fourth lap timestamp
# ============================================================

candidate_rows = []

for (
    year,
    car
), g in laps.groupby(
    [
        "year",
        "car_number"
    ]
):

    g = (
        g.sort_values(
            "timestamp_ms"
        )
        .drop_duplicates(
            subset=[
                "timestamp_ms",
                "lap_number",
                "laptime_s",
            ]
        )
        .reset_index(
            drop=True
        )
    )

    for i in range(
        0,
        len(g) - 3
    ):

        w = g.iloc[
            i:i+4
        ].copy()

        lt = w[
            "laptime_s"
        ].tolist()

        if not all(
            35.0 <= x <= 55.0
            for x in lt
        ):
            continue

        t0 = int(
            w.iloc[0][
                "timestamp_ms"
            ]
        )

        t3 = int(
            w.iloc[3][
                "timestamp_ms"
            ]
        )

        span_s = (
            t3 - t0
        ) / 1000.0

        if not (
            90.0
            <= span_s
            <= 240.0
        ):
            continue

        speed = (
            fourlap_speed_from_times(
                lt
            )
        )

        candidate_rows.append({
            "year":
                year,

            "car_number":
                car,

            "candidate_start_index":
                i,

            "lapnum1":
                int(
                    w.iloc[0][
                        "lap_number"
                    ]
                ),

            "lapnum2":
                int(
                    w.iloc[1][
                        "lap_number"
                    ]
                ),

            "lapnum3":
                int(
                    w.iloc[2][
                        "lap_number"
                    ]
                ),

            "lapnum4":
                int(
                    w.iloc[3][
                        "lap_number"
                    ]
                ),

            "lap1_s":
                lt[0],

            "lap2_s":
                lt[1],

            "lap3_s":
                lt[2],

            "lap4_s":
                lt[3],

            "derived_avg_speed_mph":
                speed,

            "first_lap_timestamp_ms":
                t0,

            "fourth_lap_timestamp_ms":
                t3,

            "attempt_anchor_timestamp_ms":
                t0,

            "attempt_anchor_utc":
                ts_to_utc(
                    t0
                ).isoformat(),

            "attempt_anchor_indianapolis":
                ts_to_indy(
                    t0
                ).isoformat(),

            "window_span_s":
                span_s,

            "analysis_files":
                " | ".join(
                    sorted(
                        set(
                            w[
                                "analysis_file"
                            ]
                            .astype(str)
                        )
                    )
                ),
        })

candidates = pd.DataFrame(
    candidate_rows
)

# ============================================================
# Match candidate 4-lap windows to official result rows
# ============================================================
#
# Primary matching evidence:
# exact-ish four individual lap times
#
# Cost:
# sum absolute lap-time differences.
#
# Threshold:
# <= 0.08 sec total = very strong
# <= 0.20 sec total = plausible
#
# one candidate may overlap another; official matching later
# identifies correct windows.
# ============================================================

match_rows = []

for _, off in official.iterrows():

    year = int(
        off["year"]
    )

    car = norm_car(
        off["car_number"]
    )

    if not bool(
        off["complete_four_lap"]
    ):
        continue

    pool = candidates[
        (
            candidates["year"]
            == year
        )
        &
        (
            candidates["car_number"]
            == car
        )
    ].copy()

    if pool.empty:
        continue

    target_laps = np.array([
        float(
            off["lap1_s"]
        ),
        float(
            off["lap2_s"]
        ),
        float(
            off["lap3_s"]
        ),
        float(
            off["lap4_s"]
        ),
    ])

    costs = []

    for idx, cand in pool.iterrows():

        cand_laps = np.array([
            cand["lap1_s"],
            cand["lap2_s"],
            cand["lap3_s"],
            cand["lap4_s"],
        ])

        absdiff = np.abs(
            cand_laps
            - target_laps
        )

        costs.append(
            (
                idx,
                float(
                    absdiff.sum()
                ),
                float(
                    absdiff.max()
                ),
            )
        )

    costs.sort(
        key=lambda x: x[1]
    )

    best_idx, best_sum, best_max = (
        costs[0]
    )

    cand = pool.loc[
        best_idx
    ]

    if best_sum <= 0.08:
        quality = "EXACT_OR_NEAR_EXACT"

    elif best_sum <= 0.20:
        quality = "PLAUSIBLE"

    else:
        quality = "WEAK"

    match_rows.append({
        "year":
            year,

        "source_rank":
            off["source_rank"],

        "car_number":
            car,

        "driver_name":
            off["driver_name"],

        "official_status":
            off["status"],

        "official_speed_mph":
            off["average_speed_mph"],

        "official_lap1_s":
            off["lap1_s"],

        "official_lap2_s":
            off["lap2_s"],

        "official_lap3_s":
            off["lap3_s"],

        "official_lap4_s":
            off["lap4_s"],

        "timing_lap1_s":
            cand["lap1_s"],

        "timing_lap2_s":
            cand["lap2_s"],

        "timing_lap3_s":
            cand["lap3_s"],

        "timing_lap4_s":
            cand["lap4_s"],

        "lap_match_abs_sum_s":
            best_sum,

        "lap_match_abs_max_s":
            best_max,

        "match_quality":
            quality,

        "attempt_timestamp_ms":
            cand[
                "attempt_anchor_timestamp_ms"
            ],

        "attempt_timestamp_utc":
            cand[
                "attempt_anchor_utc"
            ],

        "attempt_timestamp_indianapolis":
            cand[
                "attempt_anchor_indianapolis"
            ],

        "timing_derived_avg_speed_mph":
            cand[
                "derived_avg_speed_mph"
            ],

        "timing_analysis_files":
            cand[
                "analysis_files"
            ],
    })

matches = pd.DataFrame(
    match_rows
)

# ============================================================
# Duplicate candidate usage audit
# ============================================================

if not matches.empty:

    matches[
        "timestamp_usage_count"
    ] = (
        matches.groupby(
            [
                "year",
                "car_number",
                "attempt_timestamp_ms"
            ]
        )[
            "source_rank"
        ]
        .transform(
            "size"
        )
    )

# ============================================================
# Summary
# ============================================================

summary_rows = []

for year in TARGET_YEARS:

    off_y = official[
        (
            official["year"]
            == year
        )
        &
        (
            official[
                "complete_four_lap"
            ]
        )
    ]

    m_y = matches[
        matches[
            "year"
        ]
        == year
    ]

    strong = m_y[
        m_y[
            "match_quality"
        ]
        == "EXACT_OR_NEAR_EXACT"
    ]

    plausible = m_y[
        m_y[
            "match_quality"
        ]
        .isin([
            "EXACT_OR_NEAR_EXACT",
            "PLAUSIBLE"
        ])
    ]

    duplicate_timestamp_rows = 0

    if (
        not m_y.empty
        and "timestamp_usage_count"
        in m_y.columns
    ):

        duplicate_timestamp_rows = int(
            (
                m_y[
                    "timestamp_usage_count"
                ]
                > 1
            )
            .sum()
        )

    summary_rows.append({
        "year":
            year,

        "official_complete_attempts":
            len(
                off_y
            ),

        "matched_rows":
            len(
                m_y
            ),

        "strong_matches":
            len(
                strong
            ),

        "strong_or_plausible_matches":
            len(
                plausible
            ),

        "strong_coverage":
            (
                len(strong)
                /
                len(off_y)
                if len(off_y)
                else np.nan
            ),

        "plausible_coverage":
            (
                len(plausible)
                /
                len(off_y)
                if len(off_y)
                else np.nan
            ),

        "duplicate_timestamp_match_rows":
            duplicate_timestamp_rows,
    })

summary = pd.DataFrame(
    summary_rows
)

# ============================================================
# Same-car repeat transitions with VERIFIED chronology
# ============================================================

verified = matches[
    matches[
        "match_quality"
    ]
    .isin([
        "EXACT_OR_NEAR_EXACT",
        "PLAUSIBLE"
    ])
].copy()

verified = verified.sort_values(
    [
        "year",
        "car_number",
        "attempt_timestamp_ms",
    ]
)

transition_rows = []

for (
    year,
    car
), g in verified.groupby(
    [
        "year",
        "car_number"
    ]
):

    g = g.sort_values(
        "attempt_timestamp_ms"
    ).reset_index(
        drop=True
    )

    if len(g) < 2:
        continue

    for i in range(
        len(g) - 1
    ):

        a = g.iloc[
            i
        ]

        b = g.iloc[
            i + 1
        ]

        transition_rows.append({
            "year":
                year,

            "car_number":
                car,

            "driver_name":
                a[
                    "driver_name"
                ],

            "from_source_rank":
                a[
                    "source_rank"
                ],

            "to_source_rank":
                b[
                    "source_rank"
                ],

            "from_timestamp_utc":
                a[
                    "attempt_timestamp_utc"
                ],

            "to_timestamp_utc":
                b[
                    "attempt_timestamp_utc"
                ],

            "delta_minutes":
                (
                    float(
                        b[
                            "attempt_timestamp_ms"
                        ]
                    )
                    -
                    float(
                        a[
                            "attempt_timestamp_ms"
                        ]
                    )
                )
                / 60000.0,

            "from_speed_mph":
                a[
                    "official_speed_mph"
                ],

            "to_speed_mph":
                b[
                    "official_speed_mph"
                ],

            "delta_speed_mph":
                (
                    b[
                        "official_speed_mph"
                    ]
                    -
                    a[
                        "official_speed_mph"
                    ]
                ),
        })

transitions = pd.DataFrame(
    transition_rows
)

# ============================================================
# Save
# ============================================================

LAPS_OUT = (
    OUT /
    "timing71_all_laps_v1.csv"
)

CAND_OUT = (
    OUT /
    "timing71_fourlap_window_candidates_v1.csv"
)

MATCH_OUT = (
    OUT /
    "timing71_official_attempt_matches_v1.csv"
)

SUMMARY_OUT = (
    OUT /
    "timing71_official_attempt_match_summary_v1.csv"
)

TRANS_OUT = (
    OUT /
    "timing71_verified_repeat_transitions_v1.csv"
)

laps.to_csv(
    LAPS_OUT,
    index=False
)

candidates.to_csv(
    CAND_OUT,
    index=False
)

matches.to_csv(
    MATCH_OUT,
    index=False
)

summary.to_csv(
    SUMMARY_OUT,
    index=False
)

transitions.to_csv(
    TRANS_OUT,
    index=False
)

# ============================================================
# Console
# ============================================================

print("\n" + "=" * 160)
print("PART 2 — LAP STREAM SUMMARY")
print("=" * 160)

print(
    laps.groupby(
        "year"
    )
    .agg(
        lap_rows=(
            "lap_number",
            "size"
        ),
        cars=(
            "car_number",
            "nunique"
        ),
        min_timestamp=(
            "timestamp_utc",
            "min"
        ),
        max_timestamp=(
            "timestamp_utc",
            "max"
        ),
    )
    .reset_index()
    .to_string(
        index=False
    )
)

print("\n" + "=" * 160)
print("PART 3 — FOUR-LAP CANDIDATE COUNTS")
print("=" * 160)

if candidates.empty:

    print(
        "NONE"
    )

else:

    print(
        candidates.groupby(
            "year"
        )
        .size()
        .reset_index(
            name="candidate_windows"
        )
        .to_string(
            index=False
        )
    )

print("\n" + "=" * 160)
print("PART 4 — OFFICIAL ATTEMPT MATCH SUMMARY")
print("=" * 160)

print(
    summary.to_string(
        index=False
    )
)

print("\n" + "=" * 160)
print("PART 5 — VERIFIED REPEAT TRANSITIONS")
print("=" * 160)

if transitions.empty:

    print(
        "NONE"
    )

else:

    print(
        transitions[
            [
                "year",
                "car_number",
                "driver_name",
                "from_source_rank",
                "to_source_rank",
                "from_timestamp_utc",
                "to_timestamp_utc",
                "delta_minutes",
                "from_speed_mph",
                "to_speed_mph",
                "delta_speed_mph",
            ]
        ]
        .to_string(
            index=False
        )
    )

print("\nOUTPUTS:")

for p in [
    LAPS_OUT,
    CAND_OUT,
    MATCH_OUT,
    SUMMARY_OUT,
    TRANS_OUT,
]:

    print(
        p.relative_to(
            ROOT
        )
    )

print(
    "\nR6_TIMING71_ATTEMPT_RECONSTRUCTION_V1_COMPLETE"
)
