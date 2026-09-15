from pathlib import Path
import json
import re

import numpy as np
import pandas as pd


ROOT = Path(
    "/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈"
)

OUT = (
    ROOT /
    "r6_regime_extension/output/"
    "historical_holdout_lineage_v1"
)

OUT.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# Authoritative / model-touch datasets
# ============================================================

REFERENCE_FILES = {
    "FROZEN39": (
        ROOT /
        "r5/frozen_inputs/day1/"
        "day1_environment_linked_transitions_39_FROZEN.csv"
    ),

    "R5_2_ANALYSIS42": (
        ROOT /
        "r5_2/manual/"
        "r5_2_repeat_analysis_set_v1.csv"
    ),

    "R5_2_RESCUED": (
        ROOT /
        "r5_2/manual/"
        "rescued_repeat_physical_transitions_v2.csv"
    ),

    "R5_2_QUARANTINE": (
        ROOT /
        "r5_2/manual/"
        "rescued_repeat_transition_quarantine_v2.csv"
    ),

    "R5_2_RESCUED_BACKTEST": (
        ROOT /
        "r5_2/manual/"
        "final_engine_rescued_case_backtest_v1.csv"
    ),

    "R5_1_REPEAT_INVENTORY": (
        ROOT /
        "r5_1/output/"
        "day1_same_car_repeat_inventory_v1.csv"
    ),

    "R4_MULTI_RUN": (
        ROOT /
        "r4/output/"
        "r4p2_multi_run_transitions_v1.csv"
    ),
}


# ============================================================
# High-value candidate files
# ============================================================

CANDIDATE_FILES = [
    ROOT /
    "weather/output/"
    "performance_grade_attempt_timing.csv",

    ROOT /
    "weather/output/"
    "performance_grade_attempt_timing_2024_supported.csv",

    ROOT /
    "weather/output/"
    "performance_grade_attempt_realized_environment.csv",

    ROOT /
    "weather/output/"
    "performance_grade_attempt_realized_environment_2024_supported.csv",

    ROOT /
    "weather/output/"
    "official_day1_results_attempt_rows_v1.csv",

    ROOT /
    "weather/output/"
    "chronology_rescue_2022_repeat_pair_final_driver_coverage_v1.csv",

    ROOT /
    "weather/output/"
    "chronology_rescue_2022_repeat_pair_coverage_post_ilott_v1.csv",

    ROOT /
    "weather/output/"
    "chronology_rescue_2022_repeat_pair_coverage_v1.csv",

    ROOT /
    "weather/output/"
    "chronology_rescue_2022_repeat_pair_driver_eligibility_v1.csv",

    ROOT /
    "weather/output/"
    "chronology_rescue_2022_castroneves_repeat_pair_evidence_v1.csv",

    ROOT /
    "weather/output/"
    "chronology_rescue_2022_ilott_repeat_pair_evidence_v1.csv",

    ROOT /
    "weather/output/"
    "chronology_rescue_2022_karam_repeat_object_reconciliation_v1.csv",

    ROOT /
    "weather/output/"
    "chronology_rescue_2022_malukas_repeat_chronology_audit_v1.csv",

    ROOT /
    "weather/output/"
    "chronology_rescue_2022_marco_repeat_chronology_audit_v1.csv",

    ROOT /
    "weather/output/"
    "chronology_rescue_2022_sato_required_reattempt_adjudication_v1.csv",

    ROOT /
    "r5_2/manual/"
    "repeat_bounded_physical_rescue_2022_v1.csv",

    ROOT /
    "r5_2/manual/"
    "repeat_physical_rescue_targets_v1.csv",
]


# ============================================================
# Helpers
# ============================================================

def normalize_col(c):
    return (
        str(c)
        .strip()
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
    )


def safe_read_csv(path):

    try:
        return pd.read_csv(
            path,
            low_memory=False
        )

    except Exception as e:

        return None


def find_col(
    df,
    exact=None,
    tokens=None,
):

    if df is None:
        return None

    normalized = {
        normalize_col(c): c
        for c in df.columns
    }

    if exact:

        for name in exact:

            key = normalize_col(
                name
            )

            if key in normalized:
                return normalized[key]

    if tokens:

        for c in df.columns:

            n = normalize_col(
                c
            )

            if all(
                t.lower() in n
                for t in tokens
            ):
                return c

    return None


def detect_identity_columns(df):

    return {
        "year":
            find_col(
                df,
                exact=[
                    "year",
                    "season",
                ]
            ),

        "driver":
            find_col(
                df,
                exact=[
                    "driver_name",
                    "driver",
                    "name",
                ],
                tokens=[
                    "driver"
                ]
            ),

        "car":
            find_col(
                df,
                exact=[
                    "car_number",
                    "car_no",
                    "car",
                    "number",
                ],
                tokens=[
                    "car"
                ]
            ),

        "from_rank":
            find_col(
                df,
                exact=[
                    "from_source_rank",
                    "baseline_source_rank",
                    "current_source_rank",
                    "from_rank",
                    "baseline_rank",
                ]
            ),

        "to_rank":
            find_col(
                df,
                exact=[
                    "to_source_rank",
                    "repeat_source_rank",
                    "future_source_rank",
                    "to_rank",
                    "repeat_rank",
                ]
            ),

        "from_speed":
            find_col(
                df,
                exact=[
                    "from_speed_mph",
                    "baseline_speed_mph",
                    "current_speed_mph",
                    "from_avg_speed_mph",
                    "baseline_avg_speed_mph",
                ]
            ),

        "to_speed":
            find_col(
                df,
                exact=[
                    "to_speed_mph",
                    "repeat_speed_mph",
                    "future_speed_mph",
                    "to_avg_speed_mph",
                    "repeat_avg_speed_mph",
                ]
            ),

        "delta_speed":
            find_col(
                df,
                exact=[
                    "delta_speed_mph",
                    "speed_delta_mph",
                    "delta_mph",
                ],
                tokens=[
                    "delta",
                    "speed"
                ]
            ),

        "from_time":
            find_col(
                df,
                exact=[
                    "from_timestamp_utc",
                    "baseline_timestamp_utc",
                    "current_timestamp_utc",
                    "from_mid_utc",
                    "baseline_time_utc",
                ]
            ),

        "to_time":
            find_col(
                df,
                exact=[
                    "to_timestamp_utc",
                    "repeat_timestamp_utc",
                    "future_timestamp_utc",
                    "to_mid_utc",
                    "repeat_time_utc",
                ]
            ),
    }


def clean_driver(x):

    if pd.isna(x):
        return None

    s = str(x).strip().lower()

    s = re.sub(
        r"[^a-z0-9]+",
        "",
        s
    )

    return s or None


def clean_car(x):

    if pd.isna(x):
        return None

    s = str(x).strip().upper()

    s = re.sub(
        r"[^A-Z0-9]",
        "",
        s
    )

    if not s:
        return None

    # normalize numeric-looking car values
    try:

        if re.fullmatch(
            r"\d+\.0+",
            s
        ):

            s = str(
                int(
                    float(s)
                )
            )

    except Exception:
        pass

    return s


def clean_year(x):

    try:

        y = int(
            float(x)
        )

        if 2000 <= y <= 2035:
            return y

    except Exception:
        pass

    return None


def speed_round(x):

    try:

        return round(
            float(x),
            3
        )

    except Exception:

        return None


def make_row_signature(
    year,
    driver,
    car,
    from_speed,
    to_speed,
):

    if year is None:
        return None

    parts = [
        str(year),
        clean_driver(
            driver
        ) or "?",
        clean_car(
            car
        ) or "?",
        (
            f"{speed_round(from_speed):.3f}"
            if speed_round(from_speed)
            is not None
            else "?"
        ),
        (
            f"{speed_round(to_speed):.3f}"
            if speed_round(to_speed)
            is not None
            else "?"
        ),
    ]

    return "|".join(
        parts
    )


def extract_transition_like_rows(
    df,
    source_name,
):

    cols = detect_identity_columns(
        df
    )

    rows = []

    if df is None:
        return pd.DataFrame()

    for idx, r in df.iterrows():

        year = (
            clean_year(
                r[
                    cols["year"]
                ]
            )
            if cols[
                "year"
            ]
            else None
        )

        driver = (
            r[
                cols["driver"]
            ]
            if cols[
                "driver"
            ]
            else None
        )

        car = (
            r[
                cols["car"]
            ]
            if cols[
                "car"
            ]
            else None
        )

        from_speed = (
            r[
                cols["from_speed"]
            ]
            if cols[
                "from_speed"
            ]
            else None
        )

        to_speed = (
            r[
                cols["to_speed"]
            ]
            if cols[
                "to_speed"
            ]
            else None
        )

        delta_speed = (
            r[
                cols["delta_speed"]
            ]
            if cols[
                "delta_speed"
            ]
            else None
        )

        # Need at least some transition identity.
        usable = (
            year is not None
            and
            (
                driver is not None
                or
                car is not None
            )
            and
            (
                from_speed is not None
                or
                to_speed is not None
                or
                delta_speed is not None
                or
                cols["from_time"] is not None
                or
                cols["to_time"] is not None
            )
        )

        if not usable:
            continue

        rows.append({
            "source":
                source_name,

            "source_row":
                idx,

            "year":
                year,

            "driver_raw":
                driver,

            "driver_key":
                clean_driver(
                    driver
                ),

            "car_raw":
                car,

            "car_key":
                clean_car(
                    car
                ),

            "from_speed_mph":
                pd.to_numeric(
                    pd.Series(
                        [from_speed]
                    ),
                    errors="coerce"
                ).iloc[0],

            "to_speed_mph":
                pd.to_numeric(
                    pd.Series(
                        [to_speed]
                    ),
                    errors="coerce"
                ).iloc[0],

            "delta_speed_mph":
                pd.to_numeric(
                    pd.Series(
                        [delta_speed]
                    ),
                    errors="coerce"
                ).iloc[0],

            "from_time_raw":
                (
                    r[
                        cols[
                            "from_time"
                        ]
                    ]
                    if cols[
                        "from_time"
                    ]
                    else None
                ),

            "to_time_raw":
                (
                    r[
                        cols[
                            "to_time"
                        ]
                    ]
                    if cols[
                        "to_time"
                    ]
                    else None
                ),

            "signature":
                make_row_signature(
                    year,
                    driver,
                    car,
                    from_speed,
                    to_speed,
                ),
        })

    return pd.DataFrame(
        rows
    )


# ============================================================
# PART 1 — schema inventory
# ============================================================

schema_rows = []

print(
    "=" * 180
)
print(
    "PART 1 — CANDIDATE FILE SCHEMA INVENTORY"
)
print(
    "=" * 180
)

all_paths = []

for label, path in REFERENCE_FILES.items():

    all_paths.append(
        (
            "REFERENCE:" + label,
            path
        )
    )

for path in CANDIDATE_FILES:

    all_paths.append(
        (
            "CANDIDATE",
            path
        )
    )

for role, path in all_paths:

    exists = path.exists()

    if not exists:

        schema_rows.append({
            "role":
                role,

            "path":
                str(
                    path.relative_to(
                        ROOT
                    )
                ),

            "exists":
                False,

            "rows":
                np.nan,

            "columns":
                "",
        })

        continue

    df = safe_read_csv(
        path
    )

    if df is None:

        schema_rows.append({
            "role":
                role,

            "path":
                str(
                    path.relative_to(
                        ROOT
                    )
                ),

            "exists":
                True,

            "rows":
                np.nan,

            "columns":
                "READ_ERROR",
        })

        continue

    schema_rows.append({
        "role":
            role,

        "path":
            str(
                path.relative_to(
                    ROOT
                )
            ),

        "exists":
            True,

        "rows":
            len(
                df
            ),

        "columns":
            " | ".join(
                map(
                    str,
                    df.columns
                )
            ),
    })


schema = pd.DataFrame(
    schema_rows
)

print(
    schema.to_string(
        index=False
    )
)


# ============================================================
# PART 2 — reference lineage signatures
# ============================================================

reference_rows = []

for label, path in REFERENCE_FILES.items():

    if not path.exists():
        continue

    df = safe_read_csv(
        path
    )

    if df is None:
        continue

    extracted = extract_transition_like_rows(
        df,
        label
    )

    if not extracted.empty:

        reference_rows.append(
            extracted
        )


reference = (
    pd.concat(
        reference_rows,
        ignore_index=True
    )
    if reference_rows
    else pd.DataFrame()
)


# ============================================================
# PART 3 — candidate transition-like rows
# ============================================================

candidate_rows = []

for path in CANDIDATE_FILES:

    if not path.exists():
        continue

    df = safe_read_csv(
        path
    )

    if df is None:
        continue

    extracted = extract_transition_like_rows(
        df,
        str(
            path.relative_to(
                ROOT
            )
        )
    )

    if extracted.empty:
        continue

    candidate_rows.append(
        extracted
    )


candidates = (
    pd.concat(
        candidate_rows,
        ignore_index=True
    )
    if candidate_rows
    else pd.DataFrame()
)


# ============================================================
# PART 4 — lineage overlap
# ============================================================

def overlap_by_signature(
    candidate,
    reference_df,
    reference_label,
):

    if candidate is None:
        return False

    if (
        reference_df.empty
        or
        "signature"
        not in reference_df.columns
    ):

        return False

    refs = reference_df[
        reference_df[
            "source"
        ]
        ==
        reference_label
    ]

    if refs.empty:
        return False

    return candidate in set(
        refs[
            "signature"
        ]
        .dropna()
        .astype(str)
    )


if not candidates.empty:

    for label in REFERENCE_FILES.keys():

        candidates[
            "in_" + label.lower()
        ] = candidates[
            "signature"
        ].map(
            lambda s:
                overlap_by_signature(
                    s,
                    reference,
                    label
                )
        )

    touch_cols = [
        c
        for c in candidates.columns
        if c.startswith(
            "in_"
        )
    ]

    def classify(r):

        # Strictest definition:
        # must not be present in any fit/analysis/rescue/backtest set.
        if r.get(
            "in_frozen39",
            False
        ):

            return "TRAINED_FROZEN39"

        if r.get(
            "in_r5_2_analysis42",
            False
        ):

            return "MODEL_ANALYSIS_TOUCHED"

        if r.get(
            "in_r5_2_rescued",
            False
        ):

            return "RESCUED_TOUCHED"

        if r.get(
            "in_r5_2_rescued_backtest",
            False
        ):

            return "BACKTEST_ALREADY_USED"

        if r.get(
            "in_r5_2_quarantine",
            False
        ):

            return "QUARANTINED"

        return "POTENTIAL_STRICT_HOLDOUT"

    candidates[
        "lineage_class"
    ] = candidates.apply(
        classify,
        axis=1
    )


# ============================================================
# PART 5 — candidate readiness
# ============================================================

if not candidates.empty:

    candidates[
        "has_two_speeds"
    ] = (
        candidates[
            "from_speed_mph"
        ].notna()
        &
        candidates[
            "to_speed_mph"
        ].notna()
    )

    candidates[
        "has_time_pair"
    ] = (
        candidates[
            "from_time_raw"
        ].notna()
        &
        candidates[
            "to_time_raw"
        ].notna()
    )

    candidates[
        "candidate_priority"
    ] = np.select(
        [
            (
                candidates[
                    "lineage_class"
                ]
                ==
                "POTENTIAL_STRICT_HOLDOUT"
            )
            &
            candidates[
                "has_two_speeds"
            ]
            &
            candidates[
                "has_time_pair"
            ],

            (
                candidates[
                    "lineage_class"
                ]
                ==
                "POTENTIAL_STRICT_HOLDOUT"
            )
            &
            candidates[
                "has_two_speeds"
            ],
        ],
        [
            "HIGH",
            "MEDIUM",
        ],
        default="LOW"
    )


# ============================================================
# Save
# ============================================================

SCHEMA_OUT = (
    OUT /
    "historical_holdout_schema_inventory_v1.csv"
)

REFERENCE_OUT = (
    OUT /
    "historical_holdout_reference_lineage_v1.csv"
)

CANDIDATE_OUT = (
    OUT /
    "historical_holdout_candidates_lineage_v1.csv"
)

schema.to_csv(
    SCHEMA_OUT,
    index=False
)

reference.to_csv(
    REFERENCE_OUT,
    index=False
)

candidates.to_csv(
    CANDIDATE_OUT,
    index=False
)


# ============================================================
# Console summaries
# ============================================================

print(
    "\n" + "=" * 180
)
print(
    "PART 2 — REFERENCE LINEAGE SUMMARY"
)
print(
    "=" * 180
)

if reference.empty:

    print(
        "NO TRANSITION-LIKE REFERENCE ROWS DETECTED"
    )

else:

    print(
        reference.groupby(
            "source"
        )
        .size()
        .rename(
            "transition_like_rows"
        )
        .reset_index()
        .to_string(
            index=False
        )
    )


print(
    "\n" + "=" * 180
)
print(
    "PART 3 — CANDIDATE LINEAGE SUMMARY"
)
print(
    "=" * 180
)

if candidates.empty:

    print(
        "NO CANDIDATE TRANSITION-LIKE ROWS DETECTED"
    )

else:

    summary = (
        candidates.groupby(
            [
                "year",
                "lineage_class",
                "candidate_priority",
            ],
            dropna=False
        )
        .size()
        .rename(
            "rows"
        )
        .reset_index()
        .sort_values(
            [
                "year",
                "lineage_class",
                "candidate_priority",
            ]
        )
    )

    print(
        summary.to_string(
            index=False
        )
    )


print(
    "\n" + "=" * 180
)
print(
    "PART 4 — HIGH/MEDIUM POTENTIAL STRICT HOLDOUTS"
)
print(
    "=" * 180
)

if candidates.empty:

    print(
        "NONE"
    )

else:

    shortlist = candidates[
        (
            candidates[
                "lineage_class"
            ]
            ==
            "POTENTIAL_STRICT_HOLDOUT"
        )
        &
        (
            candidates[
                "candidate_priority"
            ]
            .isin(
                [
                    "HIGH",
                    "MEDIUM",
                ]
            )
        )
    ].copy()

    shortlist = shortlist[
        shortlist[
            "year"
        ].isin(
            [
                2022,
                2024,
            ]
        )
    ]

    if shortlist.empty:

        print(
            "NONE"
        )

    else:

        print(
            shortlist[
                [
                    "year",
                    "driver_raw",
                    "car_raw",
                    "from_speed_mph",
                    "to_speed_mph",
                    "delta_speed_mph",
                    "from_time_raw",
                    "to_time_raw",
                    "candidate_priority",
                    "source",
                    "signature",
                ]
            ]
            .drop_duplicates()
            .sort_values(
                [
                    "year",
                    "driver_raw",
                ]
            )
            .to_string(
                index=False
            )
        )


print(
    "\n" + "=" * 180
)
print(
    "PART 5 — MODEL-TOUCHED / EXCLUDED COUNTS"
)
print(
    "=" * 180
)

if candidates.empty:

    print(
        "NONE"
    )

else:

    print(
        candidates[
            "lineage_class"
        ]
        .value_counts(
            dropna=False
        )
        .rename_axis(
            "lineage_class"
        )
        .reset_index(
            name="rows"
        )
        .to_string(
            index=False
        )
    )


print(
    "\nOUTPUTS:"
)

for p in [
    SCHEMA_OUT,
    REFERENCE_OUT,
    CANDIDATE_OUT,
]:

    print(
        p.relative_to(
            ROOT
        )
    )

print(
    "\nHISTORICAL_HOLDOUT_LINEAGE_V1_COMPLETE"
)
