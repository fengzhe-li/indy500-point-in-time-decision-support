from pathlib import Path
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import json
import math
import re

import numpy as np
import pandas as pd

try:
    from scipy.optimize import linear_sum_assignment
except Exception:
    linear_sum_assignment = None

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
    "timing71_legacy_attempt_reconstruction_v5"
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


def norm_car(x):

    if pd.isna(x):
        return ""

    s = str(x).strip().upper()

    if re.fullmatch(
        r"\d+\.0",
        s
    ):
        s = s[:-2]

    return s


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


def normalize_ts(x):

    if not is_timestamp(
        x
    ):
        return None

    v = float(x)

    if v > 1e12:
        v /= 1000.0

    return v


def ts_to_utc(x):

    v = normalize_ts(
        x
    )

    if v is None:
        return None

    return datetime.fromtimestamp(
        v,
        tz=timezone.utc
    ).isoformat()


def ts_to_indy(x):

    v = normalize_ts(
        x
    )

    if v is None:
        return None

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


def plausible_laptime(x):

    try:
        v = float(x)
    except Exception:
        return False

    return (
        math.isfinite(v)
        and
        35.0 <= v <= 55.0
    )


def boolish(x):

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
# OFFICIAL
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
] = (
    official[
        "complete_four_lap"
    ]
    .map(
        boolish
    )
)

official_complete = (
    official[
        official[
            "is_complete"
        ]
    ]
    .copy()
)

official_complete[
    "official_id"
] = (
    official_complete[
        "year"
    ].astype(str)
    +
    "__"
    +
    official_complete[
        "source_rank"
    ].astype(str)
    +
    "__"
    +
    official_complete[
        "car_key"
    ].astype(str)
)


# ============================================================
# PARSE LEGACY TIMING OBJECTS
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

        for car_raw, obj in root.items():

            car = norm_car(
                car_raw
            )

            records = []

            if isinstance(
                obj,
                list
            ):

                # direct record
                if (
                    len(obj) >= 10
                    and
                    is_timestamp(
                        obj[1]
                    )
                    and
                    is_timestamp(
                        obj[3]
                    )
                ):

                    records.append(
                        (
                            0,
                            obj
                        )
                    )

                else:

                    for idx, item in enumerate(
                        obj
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

                        records.append(
                            (
                                idx,
                                item
                            )
                        )

            for record_index, record in records:

                start_ts = normalize_ts(
                    record[1]
                )

                end_ts = normalize_ts(
                    record[3]
                )

                history = (
                    record[9]
                    if len(
                        record
                    ) > 9
                    else None
                )

                if not isinstance(
                    history,
                    list
                ):
                    continue

                parsed = []

                for hist_idx, entry in enumerate(
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

                        lt = float(
                            entry[0]
                        )

                    except Exception:

                        continue

                    flag = (
                        entry[1]
                        if len(
                            entry
                        )
                        > 1
                        else None
                    )

                    parsed.append({
                        "history_index":
                            hist_idx,

                        "laptime_s":
                            lt,

                        "flag":
                            flag,
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
                        start_ts,

                    "parent_end_ts":
                        end_ts,

                    "parent_start_utc":
                        ts_to_utc(
                            start_ts
                        ),

                    "parent_end_utc":
                        ts_to_utc(
                            end_ts
                        ),

                    "history_count":
                        len(
                            parsed
                        ),
                })

                # ------------------------------------------
                # all plausible 4-lap windows
                # ------------------------------------------

                for j in range(
                    0,
                    len(parsed)
                    - 3
                ):

                    block = parsed[
                        j:j+4
                    ]

                    lts = [
                        b[
                            "laptime_s"
                        ]
                        for b in block
                    ]

                    if not all(
                        plausible_laptime(
                            x
                        )
                        for x in lts
                    ):
                        continue

                    four_total = float(
                        sum(
                            lts
                        )
                    )

                    derived_speed = (
                        10.0
                        /
                        (
                            four_total
                            /
                            3600.0
                        )
                    )

                    flags = [
                        b[
                            "flag"
                        ]
                        for b in block
                    ]

                    flag1_count = sum(
                        1
                        for f in flags
                        if str(
                            f
                        )
                        in {
                            "1",
                            "1.0",
                        }
                    )

                    tail = parsed[
                        j + 4:
                    ]

                    # --------------------------------------
                    # Timestamp estimate:
                    #
                    # If this is at the end of the history,
                    # parent_end is the strongest anchor.
                    #
                    # If only a few plausible timed laps
                    # follow, back-calculate.
                    #
                    # Otherwise preserve performance
                    # fingerprint but mark unresolved.
                    # --------------------------------------

                    candidate_end_ts = None
                    timestamp_quality = (
                        "UNRESOLVED"
                    )

                    if len(
                        tail
                    ) == 0:

                        candidate_end_ts = (
                            end_ts
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
                        all(
                            plausible_laptime(
                                x[
                                    "laptime_s"
                                ]
                            )
                            for x in tail
                        )
                    ):

                        candidate_end_ts = (
                            end_ts
                            -
                            sum(
                                x[
                                    "laptime_s"
                                ]
                                for x in tail
                            )
                        )

                        timestamp_quality = (
                            "PARENT_END_BACKCALC"
                        )

                    candidate_start_ts = None
                    candidate_mid_ts = None

                    if (
                        candidate_end_ts
                        is not None
                    ):

                        candidate_start_ts = (
                            candidate_end_ts
                            -
                            four_total
                        )

                        candidate_mid_ts = (
                            candidate_start_ts
                            +
                            four_total
                            /
                            2.0
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
                                "history_index"
                            ],

                        "history_end_index":
                            block[
                                -1
                            ][
                                "history_index"
                            ],

                        "lap1_s":
                            lts[
                                0
                            ],

                        "lap2_s":
                            lts[
                                1
                            ],

                        "lap3_s":
                            lts[
                                2
                            ],

                        "lap4_s":
                            lts[
                                3
                            ],

                        "fourlap_total_s":
                            four_total,

                        "derived_speed_mph":
                            derived_speed,

                        "flag1_count":
                            flag1_count,

                        "candidate_start_ts":
                            candidate_start_ts,

                        "candidate_mid_ts":
                            candidate_mid_ts,

                        "candidate_end_ts":
                            candidate_end_ts,

                        "candidate_start_utc":
                            ts_to_utc(
                                candidate_start_ts
                            ),

                        "candidate_mid_utc":
                            ts_to_utc(
                                candidate_mid_ts
                            ),

                        "candidate_end_utc":
                            ts_to_utc(
                                candidate_end_ts
                            ),

                        "candidate_mid_indianapolis":
                            ts_to_indy(
                                candidate_mid_ts
                            ),

                        "timestamp_quality":
                            timestamp_quality,
                    })


parents = pd.DataFrame(
    parent_rows
)

candidates = pd.DataFrame(
    candidate_rows
)

if candidates.empty:

    raise RuntimeError(
        "No legacy candidates parsed"
    )


# ============================================================
# DEDUPE CANDIDATES
# ============================================================

for col in [
    "lap1_s",
    "lap2_s",
    "lap3_s",
    "lap4_s",
]:

    candidates[
        col + "_r"
    ] = (
        candidates[
            col
        ]
        .round(
            4
        )
    )

candidates[
    "candidate_mid_r"
] = (
    candidates[
        "candidate_mid_ts"
    ]
    .round(
        1
    )
)

candidates[
    "timestamp_resolved"
] = (
    candidates[
        "candidate_mid_ts"
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
            "lap1_s_r",
            "lap2_s_r",
            "lap3_s_r",
            "lap4_s_r",
            "candidate_mid_r",
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
    ].astype(str)
    +
    "_"
    +
    candidates[
        "car_number"
    ].astype(str)
    +
    "_"
    +
    candidates.index
    .astype(str)
)


# ============================================================
# GLOBAL ONE-TO-ONE ASSIGNMENT BY YEAR + CAR
# ============================================================

matches = []

for (
    year,
    car
), off_group in official_complete.groupby(
    [
        "year",
        "car_key",
    ]
):

    cand_group = candidates[
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
    ].copy()

    if cand_group.empty:
        continue

    off_group = off_group.copy()

    off_indices = list(
        off_group.index
    )

    cand_indices = list(
        cand_group.index
    )

    n_o = len(
        off_indices
    )

    n_c = len(
        cand_indices
    )

    cost = np.full(
        (
            n_o,
            n_c
        ),
        9999.0
    )

    detail = {}

    for oi_pos, oi in enumerate(
        off_indices
    ):

        off = off_group.loc[
            oi
        ]

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

        for ci_pos, ci in enumerate(
            cand_indices
        ):

            cand = cand_group.loc[
                ci
            ]

            obs = np.array([
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
                obs
            )

            sum_diff = float(
                diff.sum()
            )

            max_diff = float(
                diff.max()
            )

            # Hard reject impossible fingerprint
            if sum_diff > 0.50:
                continue

            # Tiny secondary penalties only
            ts_penalty = (
                0.0005
                if not bool(
                    cand[
                        "timestamp_resolved"
                    ]
                )
                else 0.0
            )

            root_penalty = (
                0.00005
                *
                float(
                    cand[
                        "root_priority"
                    ]
                )
            )

            total_cost = (
                sum_diff
                +
                ts_penalty
                +
                root_penalty
            )

            cost[
                oi_pos,
                ci_pos
            ] = total_cost

            detail[
                (
                    oi_pos,
                    ci_pos
                )
            ] = {
                "sum_diff":
                    sum_diff,

                "max_diff":
                    max_diff,
            }

    assignments = []

    if linear_sum_assignment is not None:

        row_ind, col_ind = (
            linear_sum_assignment(
                cost
            )
        )

        assignments = list(
            zip(
                row_ind,
                col_ind
            )
        )

    else:

        # deterministic fallback
        possible = []

        for oi_pos in range(
            n_o
        ):

            for ci_pos in range(
                n_c
            ):

                if cost[
                    oi_pos,
                    ci_pos
                ] >= 9999:
                    continue

                possible.append(
                    (
                        cost[
                            oi_pos,
                            ci_pos
                        ],
                        oi_pos,
                        ci_pos,
                    )
                )

        possible.sort()

        used_o = set()
        used_c = set()

        for _, oi_pos, ci_pos in possible:

            if oi_pos in used_o:
                continue

            if ci_pos in used_c:
                continue

            used_o.add(
                oi_pos
            )

            used_c.add(
                ci_pos
            )

            assignments.append(
                (
                    oi_pos,
                    ci_pos
                )
            )

    for oi_pos, ci_pos in assignments:

        if cost[
            oi_pos,
            ci_pos
        ] >= 9999:
            continue

        oi = off_indices[
            oi_pos
        ]

        ci = cand_indices[
            ci_pos
        ]

        off = official_complete.loc[
            oi
        ]

        cand = candidates.loc[
            ci
        ]

        d = detail[
            (
                oi_pos,
                ci_pos
            )
        ]

        sum_diff = d[
            "sum_diff"
        ]

        max_diff = d[
            "max_diff"
        ]

        if (
            sum_diff <= 0.08
            and
            max_diff <= 0.04
        ):

            quality = (
                "EXACT_OR_NEAR_EXACT"
            )

        elif (
            sum_diff <= 0.20
            and
            max_diff <= 0.10
        ):

            quality = (
                "PLAUSIBLE"
            )

        else:

            quality = (
                "WEAK"
            )

        matches.append({
            "year":
                int(
                    year
                ),

            "source_rank":
                off[
                    "source_rank"
                ],

            "car_number":
                car,

            "driver_name":
                off[
                    "driver_name"
                ],

            "official_speed_mph":
                off[
                    "average_speed_mph"
                ],

            "official_lap1_s":
                off[
                    "lap1_s"
                ],

            "official_lap2_s":
                off[
                    "lap2_s"
                ],

            "official_lap3_s":
                off[
                    "lap3_s"
                ],

            "official_lap4_s":
                off[
                    "lap4_s"
                ],

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
                quality,

            "timestamp_quality":
                cand[
                    "timestamp_quality"
                ],

            "attempt_start_ts":
                cand[
                    "candidate_start_ts"
                ],

            "attempt_mid_ts":
                cand[
                    "candidate_mid_ts"
                ],

            "attempt_end_ts":
                cand[
                    "candidate_end_ts"
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
    matches
)


# ============================================================
# OFFICIAL COVERAGE / UNMATCHED REASON
# ============================================================

timing_cars = (
    candidates.groupby(
        "year"
    )[
        "car_number"
    ]
    .apply(
        lambda s:
            set(
                s.astype(str)
            )
    )
    .to_dict()
)

matched_official_ids = set()

if not matches.empty:

    matched_official_ids = set(
        (
            matches[
                "year"
            ].astype(str)
            +
            "__"
            +
            matches[
                "source_rank"
            ].astype(str)
            +
            "__"
            +
            matches[
                "car_number"
            ].astype(str)
        )
    )

coverage_rows = []

for _, off in official_complete.iterrows():

    year = int(
        off[
            "year"
        ]
    )

    car = off[
        "car_key"
    ]

    oid = (
        str(
            year
        )
        +
        "__"
        +
        str(
            off[
                "source_rank"
            ]
        )
        +
        "__"
        +
        str(
            car
        )
    )

    if oid in matched_official_ids:

        status = "MATCHED"

    elif car not in timing_cars.get(
        year,
        set()
    ):

        status = "NO_TIMING_CAR"

    else:

        status = (
            "NO_ACCEPTABLE_FINGERPRINT_MATCH"
        )

    coverage_rows.append({
        "year":
            year,

        "source_rank":
            off[
                "source_rank"
            ],

        "car_number":
            car,

        "driver_name":
            off[
                "driver_name"
            ],

        "coverage_status":
            status,
    })


coverage = pd.DataFrame(
    coverage_rows
)


# ============================================================
# SUMMARY
# ============================================================

summary_rows = []

for year in YEARS:

    off_y = official_complete[
        official_complete[
            "year"
        ]
        == year
    ]

    if matches.empty:

        m_y = pd.DataFrame()

    else:

        m_y = matches[
            matches[
                "year"
            ]
            == year
        ]

    strong = (
        0
        if m_y.empty
        else int(
            (
                m_y[
                    "match_quality"
                ]
                ==
                "EXACT_OR_NEAR_EXACT"
            )
            .sum()
        )
    )

    acceptable = (
        0
        if m_y.empty
        else int(
            m_y[
                "match_quality"
            ]
            .isin([
                "EXACT_OR_NEAR_EXACT",
                "PLAUSIBLE",
            ])
            .sum()
        )
    )

    timestamped_acceptable = (
        0
        if m_y.empty
        else int(
            (
                (
                    m_y[
                        "match_quality"
                    ]
                    .isin([
                        "EXACT_OR_NEAR_EXACT",
                        "PLAUSIBLE",
                    ])
                )
                &
                (
                    m_y[
                        "attempt_mid_ts"
                    ]
                    .notna()
                )
            ).sum()
        )
    )

    c_y = coverage[
        coverage[
            "year"
        ]
        == year
    ]

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

        "timestamped_acceptable_matches":
            timestamped_acceptable,

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

        "timestamped_acceptable_coverage":
            (
                timestamped_acceptable
                /
                len(
                    off_y
                )
                if len(
                    off_y
                )
                else np.nan
            ),

        "no_timing_car":
            int(
                (
                    c_y[
                        "coverage_status"
                    ]
                    ==
                    "NO_TIMING_CAR"
                )
                .sum()
            ),

        "no_acceptable_fingerprint_match":
            int(
                (
                    c_y[
                        "coverage_status"
                    ]
                    ==
                    "NO_ACCEPTABLE_FINGERPRINT_MATCH"
                )
                .sum()
            ),
    })


summary = pd.DataFrame(
    summary_rows
)


# ============================================================
# VERIFIED REPEAT TRANSITIONS
# ============================================================

transition_rows = []

if not matches.empty:

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
            "car_number",
        ]
    ):

        g = (
            g.sort_values(
                "attempt_mid_ts"
            )
            .reset_index(
                drop=True
            )
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

            dt_minutes = (
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
            ) / 60.0

            if dt_minutes <= 0:
                continue

            transition_rows.append({
                "year":
                    int(
                        year
                    ),

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
                    dt_minutes,

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
# SAVE
# ============================================================

PARENTS_OUT = (
    OUT /
    "legacy_parent_objects_v5.csv"
)

CAND_OUT = (
    OUT /
    "legacy_fourlap_candidates_v5.csv"
)

MATCH_OUT = (
    OUT /
    "legacy_official_attempt_matches_global_v5.csv"
)

COVERAGE_OUT = (
    OUT /
    "legacy_official_coverage_audit_v5.csv"
)

SUMMARY_OUT = (
    OUT /
    "legacy_match_summary_v5.csv"
)

TRANS_OUT = (
    OUT /
    "legacy_verified_repeat_transitions_v5.csv"
)

parents.to_csv(
    PARENTS_OUT,
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

coverage.to_csv(
    COVERAGE_OUT,
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
# CONSOLE
# ============================================================

print(
    "=" * 160
)
print(
    "PART 1 — CANDIDATE COUNTS"
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
        cars=(
            "car_number",
            "nunique"
        ),
        timestamp_resolved=(
            "timestamp_resolved",
            "sum"
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
    "PART 2 — GLOBAL ONE-TO-ONE MATCH SUMMARY"
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
    "PART 3 — UNMATCHED REASON COUNTS"
)
print(
    "=" * 160
)

print(
    coverage.groupby(
        [
            "year",
            "coverage_status",
        ]
    )
    .size()
    .reset_index(
        name="rows"
    )
    .to_string(
        index=False
    )
)

print(
    "\n" + "=" * 160
)
print(
    "PART 4 — MATCH DETAIL"
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
            ],
            na_position="last"
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
        transitions
        .sort_values(
            [
                "year",
                "from_timestamp_utc",
            ]
        )
        .to_string(
            index=False
        )
    )

print(
    "\nOUTPUTS:"
)

for p in [
    PARENTS_OUT,
    CAND_OUT,
    MATCH_OUT,
    COVERAGE_OUT,
    SUMMARY_OUT,
    TRANS_OUT,
]:

    print(
        p.relative_to(
            ROOT
        )
    )

print(
    "\nR6_LEGACY_TIMING71_ATTEMPT_RECONSTRUCTION_V5_COMPLETE"
)
