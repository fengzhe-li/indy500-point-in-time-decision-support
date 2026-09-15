from pathlib import Path
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

OFFICIAL = (
    ROOT /
    "r6_regime_extension/output/regime_attempt_inventory_v3/"
    "regime_official_attempt_inventory_v3.csv"
)

CANDIDATES = (
    ROOT /
    "r6_regime_extension/output/timing71_attempt_reconstruction_v1/"
    "timing71_fourlap_window_candidates_v1.csv"
)

OUT = (
    ROOT /
    "r6_regime_extension/output/"
    "timing71_2025_clean_chronology_v1"
)

OUT.mkdir(
    parents=True,
    exist_ok=True
)


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


def boolish(x):

    if isinstance(x, bool):
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
# Load
# ============================================================

official = pd.read_csv(
    OFFICIAL,
    low_memory=False
)

official = official[
    official["year"] == 2025
].copy()

official["complete"] = (
    official[
        "complete_four_lap"
    ]
    .map(boolish)
)

official = official[
    official["complete"]
].copy()

official["car_key"] = (
    official[
        "car_number"
    ]
    .map(norm_car)
)

candidates = pd.read_csv(
    CANDIDATES,
    low_memory=False
)

candidates = candidates[
    candidates["year"] == 2025
].copy()

candidates["car_key"] = (
    candidates[
        "car_number"
    ]
    .map(norm_car)
)

candidates = candidates.reset_index(
    drop=True
)

candidates["candidate_id"] = (
    "T71_2025_"
    +
    candidates["car_key"].astype(str)
    +
    "_"
    +
    candidates.index.astype(str)
)


# ============================================================
# Global one-to-one matching by car
# ============================================================

match_rows = []

for car, off_group in official.groupby(
    "car_key"
):

    cand_group = candidates[
        candidates["car_key"] == car
    ].copy()

    if cand_group.empty:
        continue

    off_indices = list(
        off_group.index
    )

    cand_indices = list(
        cand_group.index
    )

    n_o = len(off_indices)
    n_c = len(cand_indices)

    cost = np.full(
        (n_o, n_c),
        9999.0
    )

    detail = {}

    for oi_pos, oi in enumerate(
        off_indices
    ):

        off = official.loc[oi]

        target = np.array([
            float(off["lap1_s"]),
            float(off["lap2_s"]),
            float(off["lap3_s"]),
            float(off["lap4_s"]),
        ])

        for ci_pos, ci in enumerate(
            cand_indices
        ):

            cand = candidates.loc[ci]

            observed = np.array([
                float(cand["lap1_s"]),
                float(cand["lap2_s"]),
                float(cand["lap3_s"]),
                float(cand["lap4_s"]),
            ])

            diff = np.abs(
                target - observed
            )

            sum_diff = float(
                diff.sum()
            )

            max_diff = float(
                diff.max()
            )

            if sum_diff > 0.50:
                continue

            cost[
                oi_pos,
                ci_pos
            ] = sum_diff

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

        rows, cols = (
            linear_sum_assignment(
                cost
            )
        )

        assignments = list(
            zip(rows, cols)
        )

    else:

        possibilities = []

        for oi_pos in range(n_o):
            for ci_pos in range(n_c):

                if cost[
                    oi_pos,
                    ci_pos
                ] >= 9999:
                    continue

                possibilities.append(
                    (
                        cost[
                            oi_pos,
                            ci_pos
                        ],
                        oi_pos,
                        ci_pos,
                    )
                )

        possibilities.sort()

        used_o = set()
        used_c = set()

        for _, oi_pos, ci_pos in possibilities:

            if oi_pos in used_o:
                continue

            if ci_pos in used_c:
                continue

            used_o.add(oi_pos)
            used_c.add(ci_pos)

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

        oi = off_indices[oi_pos]
        ci = cand_indices[ci_pos]

        off = official.loc[oi]
        cand = candidates.loc[ci]

        d = detail[
            (
                oi_pos,
                ci_pos
            )
        ]

        sum_diff = d["sum_diff"]
        max_diff = d["max_diff"]

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
            quality = "PLAUSIBLE"

        else:
            quality = "WEAK"

        first_ms = float(
            cand[
                "first_lap_timestamp_ms"
            ]
        )

        fourth_ms = float(
            cand[
                "fourth_lap_timestamp_ms"
            ]
        )

        mid_ms = (
            first_ms + fourth_ms
        ) / 2.0

        match_rows.append({
            "year":
                2025,

            "source_rank":
                off["source_rank"],

            "car_number":
                car,

            "driver_name":
                off["driver_name"],

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
                sum_diff,

            "lap_match_abs_max_s":
                max_diff,

            "match_quality":
                quality,

            "candidate_id":
                cand["candidate_id"],

            "first_lap_timestamp_ms":
                first_ms,

            "fourth_lap_timestamp_ms":
                fourth_ms,

            "attempt_mid_timestamp_ms":
                mid_ms,

            "attempt_anchor_utc":
                cand[
                    "attempt_anchor_utc"
                ],

            "analysis_files":
                cand[
                    "analysis_files"
                ],
        })


matches = pd.DataFrame(
    match_rows
)


# ============================================================
# One-to-one QA
# ============================================================

duplicate_candidate_rows = int(
    matches[
        "candidate_id"
    ]
    .duplicated(
        keep=False
    )
    .sum()
)

duplicate_official_rows = int(
    matches[
        [
            "year",
            "source_rank",
            "car_number",
        ]
    ]
    .duplicated(
        keep=False
    )
    .sum()
)

if duplicate_candidate_rows != 0:
    raise RuntimeError(
        "Candidate reuse remains."
    )

if duplicate_official_rows != 0:
    raise RuntimeError(
        "Official attempt duplication remains."
    )


# ============================================================
# Accepted matches only
# ============================================================

accepted = matches[
    matches[
        "match_quality"
    ]
    .isin([
        "EXACT_OR_NEAR_EXACT",
        "PLAUSIBLE",
    ])
].copy()

accepted = accepted.sort_values(
    [
        "car_number",
        "attempt_mid_timestamp_ms",
    ]
)


# ============================================================
# Same-car pair / overlap QA
# ============================================================

pair_rows = []

for car, g in accepted.groupby(
    "car_number"
):

    g = (
        g.sort_values(
            "attempt_mid_timestamp_ms"
        )
        .reset_index(
            drop=True
        )
    )

    if len(g) < 2:
        continue

    for i in range(
        len(g) - 1
    ):

        a = g.iloc[i]
        b = g.iloc[i + 1]

        a_start = float(
            a[
                "first_lap_timestamp_ms"
            ]
        )

        a_end = float(
            a[
                "fourth_lap_timestamp_ms"
            ]
        )

        b_start = float(
            b[
                "first_lap_timestamp_ms"
            ]
        )

        b_end = float(
            b[
                "fourth_lap_timestamp_ms"
            ]
        )

        overlap_ms = max(
            0.0,
            min(
                a_end,
                b_end
            )
            -
            max(
                a_start,
                b_start
            )
        )

        mid_gap_ms = (
            float(
                b[
                    "attempt_mid_timestamp_ms"
                ]
            )
            -
            float(
                a[
                    "attempt_mid_timestamp_ms"
                ]
            )
        )

        relation = (
            "OVERLAPPING_SAME_RUN_CANDIDATES"
            if overlap_ms > 0
            else
            "NON_OVERLAPPING"
        )

        pair_rows.append({
            "year":
                2025,

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

            "from_candidate_id":
                a[
                    "candidate_id"
                ],

            "to_candidate_id":
                b[
                    "candidate_id"
                ],

            "from_match_quality":
                a[
                    "match_quality"
                ],

            "to_match_quality":
                b[
                    "match_quality"
                ],

            "mid_gap_minutes":
                mid_gap_ms
                /
                60000.0,

            "interval_overlap_s":
                overlap_ms
                /
                1000.0,

            "run_relation":
                relation,

            "from_timestamp_ms":
                a[
                    "attempt_mid_timestamp_ms"
                ],

            "to_timestamp_ms":
                b[
                    "attempt_mid_timestamp_ms"
                ],

            "from_speed_mph":
                a[
                    "official_speed_mph"
                ],

            "to_speed_mph":
                b[
                    "official_speed_mph"
                ],

            "delta_speed_mph":
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
                ),
        })


pairs = pd.DataFrame(
    pair_rows
)

if pairs.empty:

    clean = pd.DataFrame()

else:

    clean = pairs[
        pairs[
            "run_relation"
        ]
        ==
        "NON_OVERLAPPING"
    ].copy()


# ============================================================
# Summary
# ============================================================

strong = int(
    (
        matches[
            "match_quality"
        ]
        ==
        "EXACT_OR_NEAR_EXACT"
    ).sum()
)

acceptable_n = int(
    matches[
        "match_quality"
    ]
    .isin([
        "EXACT_OR_NEAR_EXACT",
        "PLAUSIBLE",
    ])
    .sum()
)

overlap_n = (
    int(
        (
            pairs[
                "run_relation"
            ]
            ==
            "OVERLAPPING_SAME_RUN_CANDIDATES"
        ).sum()
    )
    if not pairs.empty
    else 0
)

clean_n = (
    int(
        (
            pairs[
                "run_relation"
            ]
            ==
            "NON_OVERLAPPING"
        ).sum()
    )
    if not pairs.empty
    else 0
)

summary = pd.DataFrame([
    {
        "year":
            2025,

        "official_complete_attempts":
            len(official),

        "assigned_matches":
            len(matches),

        "strong_matches":
            strong,

        "acceptable_matches":
            acceptable_n,

        "acceptable_coverage":
            acceptable_n
            /
            len(official),

        "duplicate_candidate_rows":
            duplicate_candidate_rows,

        "duplicate_official_rows":
            duplicate_official_rows,

        "same_car_consecutive_pairs":
            len(pairs),

        "overlapping_pairs":
            overlap_n,

        "clean_repeat_transitions":
            clean_n,
    }
])


# ============================================================
# Save
# ============================================================

MATCH_OUT = (
    OUT /
    "timing71_2025_global_one_to_one_matches_v1.csv"
)

PAIR_OUT = (
    OUT /
    "timing71_2025_same_car_overlap_audit_v1.csv"
)

CLEAN_OUT = (
    OUT /
    "timing71_2025_clean_repeat_transitions_v1.csv"
)

SUMMARY_OUT = (
    OUT /
    "timing71_2025_chronology_summary_v1.csv"
)

matches.to_csv(
    MATCH_OUT,
    index=False
)

pairs.to_csv(
    PAIR_OUT,
    index=False
)

clean.to_csv(
    CLEAN_OUT,
    index=False
)

summary.to_csv(
    SUMMARY_OUT,
    index=False
)


# ============================================================
# Console
# ============================================================

print(
    "=" * 160
)
print(
    "PART 1 — 2025 GLOBAL MATCH SUMMARY"
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
    "PART 2 — 2025 OVERLAPPING PAIRS"
)
print(
    "=" * 160
)

if pairs.empty:

    print("NONE")

else:

    bad = pairs[
        pairs[
            "run_relation"
        ]
        ==
        "OVERLAPPING_SAME_RUN_CANDIDATES"
    ]

    if bad.empty:
        print("NONE")

    else:

        print(
            bad[
                [
                    "car_number",
                    "driver_name",
                    "from_source_rank",
                    "to_source_rank",
                    "mid_gap_minutes",
                    "interval_overlap_s",
                    "from_match_quality",
                    "to_match_quality",
                ]
            ]
            .to_string(
                index=False
            )
        )

print(
    "\n" + "=" * 160
)
print(
    "PART 3 — 2025 CLEAN REPEAT TRANSITIONS"
)
print(
    "=" * 160
)

if clean.empty:

    print("NONE")

else:

    print(
        clean[
            [
                "car_number",
                "driver_name",
                "from_source_rank",
                "to_source_rank",
                "mid_gap_minutes",
                "from_speed_mph",
                "to_speed_mph",
                "delta_speed_mph",
            ]
        ]
        .to_string(
            index=False
        )
    )

print(
    "\nOUTPUTS:"
)

for p in [
    MATCH_OUT,
    PAIR_OUT,
    CLEAN_OUT,
    SUMMARY_OUT,
]:

    print(
        p.relative_to(
            ROOT
        )
    )

print(
    "\nR6_TIMING71_2025_CLEAN_CHRONOLOGY_V1_COMPLETE"
)
