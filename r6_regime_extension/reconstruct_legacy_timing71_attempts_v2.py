from pathlib import Path
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import json
import math
import re

import numpy as np
import pandas as pd

ROOT = Path(
    "/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈"
)

SRC = (
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
    "r6_regime_extension/output/"
    "timing71_legacy_attempt_reconstruction_v2"
)

OUT.mkdir(
    parents=True,
    exist_ok=True
)

INDY_TZ = ZoneInfo(
    "America/Indiana/Indianapolis"
)

YEARS = [
    2018,
    2019,
]

# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------

def norm_car(x):

    if pd.isna(x):
        return ""

    s = str(x).strip().upper()

    # pandas sometimes converts numeric car number to "9.0"
    if re.fullmatch(
        r"\d+\.0",
        s
    ):
        s = s[:-2]

    return s


def unix_to_iso(ts):

    if ts is None:
        return None

    try:
        v = float(ts)
    except Exception:
        return None

    if not math.isfinite(v):
        return None

    if v > 1e12:
        v /= 1000.0

    try:

        return datetime.fromtimestamp(
            v,
            tz=timezone.utc
        ).isoformat()

    except Exception:

        return None


def unix_to_indy(ts):

    if ts is None:
        return None

    try:
        v = float(ts)
    except Exception:
        return None

    if not math.isfinite(v):
        return None

    if v > 1e12:
        v /= 1000.0

    try:

        return (
            datetime.fromtimestamp(
                v,
                tz=timezone.utc
            )
            .astimezone(
                INDY_TZ
            )
            .isoformat()
        )

    except Exception:

        return None


def is_timestamp(x):

    try:

        v = float(x)

    except Exception:

        return False

    return (
        1.4e9 <= v <= 2.0e9
        or
        1.4e12 <= v <= 2.0e12
    )


def plausible_laptime(x):

    try:

        v = float(x)

    except Exception:

        return False

    return (
        math.isfinite(v)
        and 35.0 <= v <= 55.0
    )


def official_complete(row):

    x = row.get(
        "complete_four_lap"
    )

    if isinstance(
        x,
        bool
    ):
        return x

    return (
        str(x)
        .strip()
        .lower()
        in {
            "true",
            "1",
            "yes",
        }
    )


# ============================================================
# Official attempts
# ============================================================

official = pd.read_csv(
    OFFICIAL,
    low_memory=False
)

official = official[
    official[
        "year"
    ].isin(
        YEARS
    )
].copy()

official[
    "car_key"
] = (
    official[
        "car_number"
    ]
    .map(
        norm_car
    )
)

official[
    "is_complete"
] = official.apply(
    official_complete,
    axis=1
)

official_complete_df = official[
    official[
        "is_complete"
    ]
].copy()

# ============================================================
# Legacy object extraction
# ============================================================

parent_rows = []
candidate_rows = []

FILES = sorted(
    list(
        SRC.glob(
            "2018*_analysis.json"
        )
    )
    +
    list(
        SRC.glob(
            "2019*_analysis.json"
        )
    )
)

for file_path in FILES:

    m = re.match(
        r"^(2018|2019)_",
        file_path.name
    )

    if not m:
        continue

    year = int(
        m.group(1)
    )

    payload = json.loads(
        file_path.read_text(
            encoding="utf-8"
        )
    )

    for root_name in [
        "lap",
        "stint",
    ]:

        root = payload.get(
            root_name,
            {}
        )

        if not isinstance(
            root,
            dict
        ):
            continue

        for car_raw, object_value in root.items():

            car = norm_car(
                car_raw
            )

            # ----------------------------------------------
            # lap:
            # sometimes [parent_record, current_timestamp]
            #
            # stint:
            # usually [parent_record, parent_record, ...]
            # ----------------------------------------------

            possible_records = []

            if (
                isinstance(
                    object_value,
                    list
                )
            ):

                # a direct legacy record itself
                if (
                    len(
                        object_value
                    )
                    >= 10
                    and is_timestamp(
                        object_value[1]
                    )
                    and is_timestamp(
                        object_value[3]
                    )
                ):

                    possible_records.append(
                        (
                            0,
                            object_value
                        )
                    )

                else:

                    for record_index, item in enumerate(
                        object_value
                    ):

                        if not isinstance(
                            item,
                            list
                        ):
                            continue

                        if len(
                            item
                        ) < 10:
                            continue

                        if not (
                            is_timestamp(
                                item[1]
                            )
                            and
                            is_timestamp(
                                item[3]
                            )
                        ):
                            continue

                        possible_records.append(
                            (
                                record_index,
                                item
                            )
                        )

            for record_index, record in possible_records:

                try:

                    parent_start = float(
                        record[1]
                    )

                    parent_end = float(
                        record[3]
                    )

                except Exception:

                    continue

                history = record[9]

                if not isinstance(
                    history,
                    list
                ):
                    continue

                parsed_history = []

                for hist_index, entry in enumerate(
                    history
                ):

                    if not (
                        isinstance(
                            entry,
                            list
                        )
                        and
                        len(
                            entry
                        )
                        >= 1
                    ):
                        continue

                    try:

                        lap_time = float(
                            entry[0]
                        )

                    except Exception:

                        continue

                    flag_code = (
                        entry[1]
                        if len(
                            entry
                        )
                        >= 2
                        else None
                    )

                    parsed_history.append({
                        "original_index":
                            hist_index,

                        "laptime":
                            lap_time,

                        "flag":
                            flag_code,
                    })

                parent_rows.append({
                    "year":
                        year,

                    "analysis_file":
                        file_path.name,

                    "root":
                        root_name,

                    "car_number":
                        car,

                    "record_index":
                        record_index,

                    "parent_start_ts":
                        parent_start,

                    "parent_end_ts":
                        parent_end,

                    "parent_start_utc":
                        unix_to_iso(
                            parent_start
                        ),

                    "parent_end_utc":
                        unix_to_iso(
                            parent_end
                        ),

                    "history_count":
                        len(
                            parsed_history
                        ),

                    "record_repr":
                        repr(
                            record
                        )[:5000],
                })

                # ------------------------------------------
                # Scan every consecutive 4-lap sequence
                # ------------------------------------------

                for j in range(
                    len(
                        parsed_history
                    ) - 3
                ):

                    block = parsed_history[
                        j:j+4
                    ]

                    lap_times = [
                        x[
                            "laptime"
                        ]
                        for x in block
                    ]

                    if not all(
                        plausible_laptime(
                            x
                        )
                        for x in lap_times
                    ):
                        continue

                    flags = [
                        x[
                            "flag"
                        ]
                        for x in block
                    ]

                    # Indy timing status "1" repeatedly appears
                    # on valid green/timed laps.
                    flag1_count = sum(
                        1
                        for x in flags
                        if str(
                            x
                        )
                        in {
                            "1",
                            "1.0",
                        }
                    )

                    total_4lap_s = sum(
                        lap_times
                    )

                    derived_speed = (
                        10.0
                        /
                        (
                            total_4lap_s
                            /
                            3600.0
                        )
                    )

                    # --------------------------------------
                    # Timestamp reconstruction
                    #
                    # Best case:
                    # candidate sits at END of parent history.
                    #
                    # Then parent_end ≈ end of fourth timed lap.
                    #
                    # If a small number of plausible laps follow,
                    # subtract their durations.
                    #
                    # If a large/noisy tail follows, timestamp
                    # confidence is reduced.
                    # --------------------------------------

                    tail = parsed_history[
                        j + 4:
                    ]

                    tail_plausible = [
                        x[
                            "laptime"
                        ]
                        for x in tail
                        if plausible_laptime(
                            x[
                                "laptime"
                            ]
                        )
                    ]

                    noisy_tail_count = sum(
                        1
                        for x in tail
                        if not plausible_laptime(
                            x[
                                "laptime"
                            ]
                        )
                    )

                    candidate_end = None
                    timestamp_quality = (
                        "UNRESOLVED"
                    )

                    if len(
                        tail
                    ) == 0:

                        candidate_end = (
                            parent_end
                        )

                        timestamp_quality = (
                            "PARENT_END_DIRECT"
                        )

                    elif (
                        len(
                            tail
                        )
                        <= 3
                        and
                        noisy_tail_count
                        == 0
                    ):

                        candidate_end = (
                            parent_end
                            -
                            sum(
                                tail_plausible
                            )
                        )

                        timestamp_quality = (
                            "PARENT_END_BACKCALC"
                        )

                    # if parent duration itself is nonsense /
                    # stale state, we still retain the
                    # performance candidate but not timestamp.

                    candidate_start = None
                    candidate_mid = None

                    if candidate_end is not None:

                        candidate_start = (
                            candidate_end
                            -
                            total_4lap_s
                        )

                        candidate_mid = (
                            candidate_start
                            +
                            total_4lap_s
                            / 2.0
                        )

                    candidate_rows.append({
                        "year":
                            year,

                        "analysis_file":
                            file_path.name,

                        "root":
                            root_name,

                        "car_number":
                            car,

                        "record_index":
                            record_index,

                        "history_start_index":
                            block[
                                0
                            ][
                                "original_index"
                            ],

                        "history_end_index":
                            block[
                                -1
                            ][
                                "original_index"
                            ],

                        "lap1_s":
                            lap_times[
                                0
                            ],

                        "lap2_s":
                            lap_times[
                                1
                            ],

                        "lap3_s":
                            lap_times[
                                2
                            ],

                        "lap4_s":
                            lap_times[
                                3
                            ],

                        "flag1_count":
                            flag1_count,

                        "fourlap_total_s":
                            total_4lap_s,

                        "derived_speed_mph":
                            derived_speed,

                        "parent_start_ts":
                            parent_start,

                        "parent_end_ts":
                            parent_end,

                        "candidate_start_ts":
                            candidate_start,

                        "candidate_mid_ts":
                            candidate_mid,

                        "candidate_end_ts":
                            candidate_end,

                        "candidate_start_utc":
                            unix_to_iso(
                                candidate_start
                            ),

                        "candidate_mid_utc":
                            unix_to_iso(
                                candidate_mid
                            ),

                        "candidate_end_utc":
                            unix_to_iso(
                                candidate_end
                            ),

                        "candidate_mid_indianapolis":
                            unix_to_indy(
                                candidate_mid
                            ),

                        "timestamp_quality":
                            timestamp_quality,

                        "tail_count":
                            len(
                                tail
                            ),
                    })


parents = pd.DataFrame(
    parent_rows
)

candidates = pd.DataFrame(
    candidate_rows
)

if candidates.empty:

    raise RuntimeError(
        "No legacy four-lap candidates extracted"
    )

# ============================================================
# Deduplicate replay-state duplicates
# ============================================================

for c in [
    "lap1_s",
    "lap2_s",
    "lap3_s",
    "lap4_s",
]:

    candidates[
        c + "_round"
    ] = (
        candidates[
            c
        ]
        .round(
            4
        )
    )

candidates[
    "candidate_end_round"
] = (
    candidates[
        "candidate_end_ts"
    ]
    .round(
        1
    )
)

# Prefer:
# timestamp resolved > unresolved
# lap root > stint
# more green flag codes

candidates[
    "timestamp_resolved"
] = (
    candidates[
        "candidate_end_ts"
    ]
    .notna()
)

candidates[
    "root_priority"
] = (
    candidates[
        "root"
    ]
    .map({
        "lap": 0,
        "stint": 1,
    })
    .fillna(
        2
    )
)

candidates = (
    candidates
    .sort_values(
        [
            "timestamp_resolved",
            "flag1_count",
            "root_priority",
        ],
        ascending=[
            False,
            False,
            True,
        ]
    )
    .drop_duplicates(
        subset=[
            "year",
            "car_number",
            "lap1_s_round",
            "lap2_s_round",
            "lap3_s_round",
            "lap4_s_round",
            "candidate_end_round",
        ],
        keep="first"
    )
    .reset_index(
        drop=True
    )
)

candidates[
    "candidate_id"
] = (
    "LEGACY_"
    +
    candidates[
        "year"
    ]
    .astype(str)
    +
    "_"
    +
    candidates[
        "car_number"
    ]
    .astype(str)
    +
    "_"
    +
    candidates.index
    .astype(str)
)

# ============================================================
# Build all official ↔ timing candidate edges
# ============================================================

edges = []

for official_index, off in official_complete_df.iterrows():

    year = int(
        off[
            "year"
        ]
    )

    car = norm_car(
        off[
            "car_number"
        ]
    )

    pool = candidates[
        (
            candidates[
                "year"
            ]
            == year
        )
        &
        (
            candidates[
                "car_number"
            ]
            == car
        )
    ]

    if pool.empty:
        continue

    target = np.array([
        float(
            off[
                "lap1_s"
            ]
        ),
        float(
            off[
                "lap2_s"
            ]
        ),
        float(
            off[
                "lap3_s"
            ]
        ),
        float(
            off[
                "lap4_s"
            ]
        ),
    ])

    for candidate_index, cand in pool.iterrows():

        observed = np.array([
            float(
                cand[
                    "lap1_s"
                ]
            ),
            float(
                cand[
                    "lap2_s"
                ]
            ),
            float(
                cand[
                    "lap3_s"
                ]
            ),
            float(
                cand[
                    "lap4_s"
                ]
            ),
        ])

        diff = np.abs(
            target
            -
            observed
        )

        sum_diff = float(
            diff.sum()
        )

        max_diff = float(
            diff.max()
        )

        # broad enough to diagnose;
        # final accepted quality is stricter.
        if sum_diff > 0.50:
            continue

        edges.append({
            "official_index":
                official_index,

            "candidate_index":
                candidate_index,

            "year":
                year,

            "car_number":
                car,

            "source_rank":
                off.get(
                    "source_rank"
                ),

            "driver_name":
                off.get(
                    "driver_name"
                ),

            "official_speed_mph":
                off.get(
                    "average_speed_mph"
                ),

            "lap_match_abs_sum_s":
                sum_diff,

            "lap_match_abs_max_s":
                max_diff,

            "candidate_timestamp_resolved":
                bool(
                    cand[
                        "timestamp_resolved"
                    ]
                ),

            "candidate_flag1_count":
                int(
                    cand[
                        "flag1_count"
                    ]
                ),

            "candidate_end_ts":
                cand[
                    "candidate_end_ts"
                ],
        })


edges_df = pd.DataFrame(
    edges
)

# ============================================================
# Strict one-to-one assignment
# ============================================================

assigned_rows = []

used_official = set()
used_candidates = set()

if not edges_df.empty:

    edges_df[
        "timestamp_penalty"
    ] = np.where(
        edges_df[
            "candidate_timestamp_resolved"
        ],
        0,
        1
    )

    # Primary objective = lap match accuracy.
    # Timestamp resolution only breaks similar ties.
    edges_df = edges_df.sort_values(
        [
            "lap_match_abs_sum_s",
            "lap_match_abs_max_s",
            "timestamp_penalty",
            "candidate_flag1_count",
        ],
        ascending=[
            True,
            True,
            True,
            False,
        ]
    )

    for _, edge in edges_df.iterrows():

        oi = int(
            edge[
                "official_index"
            ]
        )

        ci = int(
            edge[
                "candidate_index"
            ]
        )

        if oi in used_official:
            continue

        if ci in used_candidates:
            continue

        used_official.add(
            oi
        )

        used_candidates.add(
            ci
        )

        off = official_complete_df.loc[
            oi
        ]

        cand = candidates.loc[
            ci
        ]

        sum_diff = float(
            edge[
                "lap_match_abs_sum_s"
            ]
        )

        max_diff = float(
            edge[
                "lap_match_abs_max_s"
            ]
        )

        if (
            sum_diff <= 0.08
            and
            max_diff <= 0.04
        ):

            match_quality = (
                "EXACT_OR_NEAR_EXACT"
            )

        elif (
            sum_diff <= 0.20
            and
            max_diff <= 0.10
        ):

            match_quality = (
                "PLAUSIBLE"
            )

        else:

            match_quality = (
                "WEAK"
            )

        assigned_rows.append({
            "year":
                int(
                    off[
                        "year"
                    ]
                ),

            "source_rank":
                off.get(
                    "source_rank"
                ),

            "car_number":
                norm_car(
                    off[
                        "car_number"
                    ]
                ),

            "driver_name":
                off.get(
                    "driver_name"
                ),

            "official_status":
                off.get(
                    "status"
                ),

            "official_speed_mph":
                off.get(
                    "average_speed_mph"
                ),

            "official_lap1_s":
                off.get(
                    "lap1_s"
                ),

            "official_lap2_s":
                off.get(
                    "lap2_s"
                ),

            "official_lap3_s":
                off.get(
                    "lap3_s"
                ),

            "official_lap4_s":
                off.get(
                    "lap4_s"
                ),

            "timing_lap1_s":
                cand[
                    "lap1_s"
                ],

            "timing_lap2_s":
                cand[
                    "lap2_s"
                ],

            "timing_lap3_s":
                cand[
                    "lap3_s"
                ],

            "timing_lap4_s":
                cand[
                    "lap4_s"
                ],

            "lap_match_abs_sum_s":
                sum_diff,

            "lap_match_abs_max_s":
                max_diff,

            "match_quality":
                match_quality,

            "timestamp_quality":
                cand[
                    "timestamp_quality"
                ],

            "attempt_start_utc":
                cand[
                    "candidate_start_utc"
                ],

            "attempt_mid_utc":
                cand[
                    "candidate_mid_utc"
                ],

            "attempt_end_utc":
                cand[
                    "candidate_end_utc"
                ],

            "attempt_mid_indianapolis":
                cand[
                    "candidate_mid_indianapolis"
                ],

            "attempt_mid_ts":
                cand[
                    "candidate_mid_ts"
                ],

            "timing_root":
                cand[
                    "root"
                ],

            "timing_analysis_file":
                cand[
                    "analysis_file"
                ],

            "candidate_id":
                cand[
                    "candidate_id"
                ],
        })


matches = pd.DataFrame(
    assigned_rows
)

# ============================================================
# Summary
# ============================================================

summary_rows = []

for year in YEARS:

    off_y = official_complete_df[
        official_complete_df[
            "year"
        ]
        == year
    ]

    m_y = matches[
        matches[
            "year"
        ]
        == year
    ] if not matches.empty else pd.DataFrame()

    if m_y.empty:

        strong = 0
        acceptable = 0
        timestamped = 0

    else:

        strong = int(
            (
                m_y[
                    "match_quality"
                ]
                ==
                "EXACT_OR_NEAR_EXACT"
            )
            .sum()
        )

        acceptable = int(
            m_y[
                "match_quality"
            ]
            .isin([
                "EXACT_OR_NEAR_EXACT",
                "PLAUSIBLE",
            ])
            .sum()
        )

        timestamped = int(
            (
                m_y[
                    "attempt_mid_ts"
                ]
                .notna()
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

        "assigned_matches":
            len(
                m_y
            ),

        "strong_matches":
            strong,

        "strong_or_plausible_matches":
            acceptable,

        "timestamp_resolved_matches":
            timestamped,

        "strong_coverage":
            (
                strong
                /
                len(
                    off_y
                )
                if len(
                    off_y
                )
                else np.nan
            ),

        "acceptable_coverage":
            (
                acceptable
                /
                len(
                    off_y
                )
                if len(
                    off_y
                )
                else np.nan
            ),

        "timestamp_coverage":
            (
                timestamped
                /
                len(
                    off_y
                )
                if len(
                    off_y
                )
                else np.nan
            ),
    })


summary = pd.DataFrame(
    summary_rows
)

# ============================================================
# Verified chronological repeats
# ============================================================

if matches.empty:

    verified = pd.DataFrame()

else:

    verified = matches[
        (
            matches[
                "match_quality"
            ]
            .isin([
                "EXACT_OR_NEAR_EXACT",
                "PLAUSIBLE",
            ])
        )
        &
        (
            matches[
                "attempt_mid_ts"
            ]
            .notna()
        )
    ].copy()

transition_rows = []

if not verified.empty:

    verified = verified.sort_values(
        [
            "year",
            "car_number",
            "attempt_mid_ts",
        ]
    )

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
            "attempt_mid_ts"
        ).reset_index(
            drop=True
        )

        if len(
            g
        ) < 2:
            continue

        for i in range(
            len(
                g
            )
            - 1
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
                        "attempt_mid_utc"
                    ],

                "to_timestamp_utc":
                    b[
                        "attempt_mid_utc"
                    ],

                "delta_minutes":
                    (
                        float(
                            b[
                                "attempt_mid_ts"
                            ]
                        )
                        -
                        float(
                            a[
                                "attempt_mid_ts"
                            ]
                        )
                    )
                    /
                    60.0,

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
                        float(
                            b[
                                "official_speed_mph"
                            ]
                        )
                        -
                        float(
                            a[
                                "official_speed_mph"
                            ]
                        )
                    ),
            })


transitions = pd.DataFrame(
    transition_rows
)

# ============================================================
# Save
# ============================================================

PARENTS_OUT = (
    OUT /
    "legacy_parent_timing_objects_v2.csv"
)

CANDIDATES_OUT = (
    OUT /
    "legacy_fourlap_candidates_v2.csv"
)

EDGES_OUT = (
    OUT /
    "legacy_official_candidate_edges_v2.csv"
)

MATCH_OUT = (
    OUT /
    "legacy_official_attempt_matches_one_to_one_v2.csv"
)

SUMMARY_OUT = (
    OUT /
    "legacy_attempt_match_summary_v2.csv"
)

TRANSITIONS_OUT = (
    OUT /
    "legacy_verified_repeat_transitions_v2.csv"
)

parents.to_csv(
    PARENTS_OUT,
    index=False
)

candidates.to_csv(
    CANDIDATES_OUT,
    index=False
)

edges_df.to_csv(
    EDGES_OUT,
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
    TRANSITIONS_OUT,
    index=False
)

# ============================================================
# Console
# ============================================================

print(
    "=" * 160
)
print(
    "PART 1 — LEGACY PARENT OBJECT COUNTS"
)
print(
    "=" * 160
)

print(
    parents.groupby(
        [
            "year",
            "root",
        ]
    )
    .size()
    .reset_index(
        name="parent_objects"
    )
    .to_string(
        index=False
    )
)

print(
    "\n" + "=" * 160
)
print(
    "PART 2 — FOUR-LAP CANDIDATE COUNTS"
)
print(
    "=" * 160
)

print(
    candidates.groupby(
        "year"
    )
    .agg(
        candidates=(
            "candidate_id",
            "size"
        ),
        timestamp_resolved=(
            "timestamp_resolved",
            "sum"
        ),
        cars=(
            "car_number",
            "nunique"
        ),
    )
    .reset_index()
    .to_string(
        index=False
    )
)

print(
    "\n" + "=" * 160
)
print(
    "PART 3 — ONE-TO-ONE OFFICIAL MATCH SUMMARY"
)
print(
    "=" * 160
)

print(
    summary.to_string(
        index=False
    )
)

print(
    "\n" + "=" * 160
)
print(
    "PART 4 — MATCH QUALITY DETAIL"
)
print(
    "=" * 160
)

if matches.empty:

    print(
        "NONE"
    )

else:

    print(
        matches[
            [
                "year",
                "source_rank",
                "car_number",
                "driver_name",
                "match_quality",
                "lap_match_abs_sum_s",
                "timestamp_quality",
                "attempt_mid_utc",
            ]
        ]
        .sort_values(
            [
                "year",
                "attempt_mid_ts",
                "source_rank",
            ]
        )
        .to_string(
            index=False
        )
    )

print(
    "\n" + "=" * 160
)
print(
    "PART 5 — VERIFIED LEGACY REPEAT TRANSITIONS"
)
print(
    "=" * 160
)

if transitions.empty:

    print(
        "NONE"
    )

else:

    print(
        transitions.to_string(
            index=False
        )
    )

print(
    "\nOUTPUTS:"
)

for p in [
    PARENTS_OUT,
    CANDIDATES_OUT,
    EDGES_OUT,
    MATCH_OUT,
    SUMMARY_OUT,
    TRANSITIONS_OUT,
]:

    print(
        p.relative_to(
            ROOT
        )
    )

print(
    "\nR6_LEGACY_TIMING71_ATTEMPT_RECONSTRUCTION_V2_COMPLETE"
)
