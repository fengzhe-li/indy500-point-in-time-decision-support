from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path(
    "/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈"
)

SRC = (
    ROOT /
    "r6_regime_extension/output/"
    "timing71_legacy_attempt_reconstruction_v5/"
    "legacy_official_attempt_matches_global_v5.csv"
)

OUT = (
    ROOT /
    "r6_regime_extension/output/"
    "timing71_legacy_run_overlap_qa_v1"
)

OUT.mkdir(
    parents=True,
    exist_ok=True
)

matches = pd.read_csv(
    SRC,
    low_memory=False
)

required = [
    "year",
    "source_rank",
    "car_number",
    "driver_name",
    "official_speed_mph",
    "match_quality",
    "lap_match_abs_sum_s",
    "attempt_start_ts",
    "attempt_mid_ts",
    "attempt_end_ts",
    "attempt_start_utc",
    "attempt_mid_utc",
    "attempt_end_utc",
    "candidate_id",
]

missing = [
    c
    for c in required
    if c not in matches.columns
]

if missing:
    raise RuntimeError(
        "Missing columns: "
        + ", ".join(missing)
    )

# ============================================================
# Only scientifically acceptable attempt matches
# ============================================================

accepted = matches[
    matches[
        "match_quality"
    ].isin([
        "EXACT_OR_NEAR_EXACT",
        "PLAUSIBLE",
    ])
].copy()

accepted = accepted[
    accepted[
        "attempt_mid_ts"
    ].notna()
].copy()

accepted = accepted.sort_values(
    [
        "year",
        "car_number",
        "attempt_mid_ts",
    ]
)

# ============================================================
# Build consecutive same-car pairs
# ============================================================

pair_rows = []

for (
    year,
    car
), g in accepted.groupby(
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

    if len(g) < 2:
        continue

    for i in range(
        len(g) - 1
    ):

        a = g.iloc[i]
        b = g.iloc[i + 1]

        a_start = float(
            a["attempt_start_ts"]
        )

        a_end = float(
            a["attempt_end_ts"]
        )

        b_start = float(
            b["attempt_start_ts"]
        )

        b_end = float(
            b["attempt_end_ts"]
        )

        mid_gap_s = (
            float(
                b["attempt_mid_ts"]
            )
            -
            float(
                a["attempt_mid_ts"]
            )
        )

        # Two reconstructed four-lap attempts cannot be
        # independent if their timing intervals overlap.
        interval_overlap_s = max(
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

        intervals_overlap = (
            interval_overlap_s
            > 0
        )

        # Also flag if B begins before A has completed.
        b_starts_before_a_ends = (
            b_start
            <
            a_end
        )

        # No arbitrary queue threshold here.
        # This is purely interval consistency.
        run_relation = (
            "OVERLAPPING_SAME_RUN_CANDIDATES"
            if intervals_overlap
            else
            "NON_OVERLAPPING"
        )

        pair_rows.append({
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

            "from_match_error_s":
                a[
                    "lap_match_abs_sum_s"
                ],

            "to_match_error_s":
                b[
                    "lap_match_abs_sum_s"
                ],

            "from_start_utc":
                a[
                    "attempt_start_utc"
                ],

            "from_mid_utc":
                a[
                    "attempt_mid_utc"
                ],

            "from_end_utc":
                a[
                    "attempt_end_utc"
                ],

            "to_start_utc":
                b[
                    "attempt_start_utc"
                ],

            "to_mid_utc":
                b[
                    "attempt_mid_utc"
                ],

            "to_end_utc":
                b[
                    "attempt_end_utc"
                ],

            "mid_gap_s":
                mid_gap_s,

            "mid_gap_minutes":
                mid_gap_s / 60.0,

            "interval_overlap_s":
                interval_overlap_s,

            "b_starts_before_a_ends":
                b_starts_before_a_ends,

            "run_relation":
                run_relation,

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

# ============================================================
# Produce clean repeat-transition set
# ============================================================

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
# QA summaries
# ============================================================

summary_rows = []

for year in sorted(
    accepted[
        "year"
    ].unique()
):

    p = pairs[
        pairs[
            "year"
        ]
        == year
    ]

    summary_rows.append({
        "year":
            int(year),

        "timestamped_acceptable_attempts":
            int(
                (
                    accepted[
                        "year"
                    ]
                    == year
                ).sum()
            ),

        "consecutive_same_car_pairs":
            len(p),

        "overlapping_pairs":
            int(
                (
                    p[
                        "run_relation"
                    ]
                    ==
                    "OVERLAPPING_SAME_RUN_CANDIDATES"
                ).sum()
            )
            if not p.empty
            else 0,

        "non_overlapping_repeat_transitions":
            int(
                (
                    p[
                        "run_relation"
                    ]
                    ==
                    "NON_OVERLAPPING"
                ).sum()
            )
            if not p.empty
            else 0,
    })

summary = pd.DataFrame(
    summary_rows
)

# ============================================================
# Save
# ============================================================

PAIR_OUT = (
    OUT /
    "legacy_same_car_pair_overlap_audit_v1.csv"
)

CLEAN_OUT = (
    OUT /
    "legacy_verified_nonoverlap_repeat_transitions_v1.csv"
)

SUMMARY_OUT = (
    OUT /
    "legacy_run_overlap_summary_v1.csv"
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
    "PART 1 — RUN OVERLAP SUMMARY"
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
    "PART 2 — OVERLAPPING / INVALID SAME-RUN PAIRS"
)
print(
    "=" * 160
)

bad = pairs[
    pairs[
        "run_relation"
    ]
    ==
    "OVERLAPPING_SAME_RUN_CANDIDATES"
].copy()

if bad.empty:

    print(
        "NONE"
    )

else:

    print(
        bad[
            [
                "year",
                "car_number",
                "driver_name",
                "from_source_rank",
                "to_source_rank",
                "mid_gap_minutes",
                "interval_overlap_s",
                "from_match_quality",
                "to_match_quality",
                "from_match_error_s",
                "to_match_error_s",
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
    "PART 3 — CLEAN NON-OVERLAPPING REPEAT TRANSITIONS"
)
print(
    "=" * 160
)

if clean.empty:

    print(
        "NONE"
    )

else:

    print(
        clean[
            [
                "year",
                "car_number",
                "driver_name",
                "from_source_rank",
                "to_source_rank",
                "from_mid_utc",
                "to_mid_utc",
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
    "\nR6_LEGACY_RUN_OVERLAP_QA_V1_COMPLETE"
)
