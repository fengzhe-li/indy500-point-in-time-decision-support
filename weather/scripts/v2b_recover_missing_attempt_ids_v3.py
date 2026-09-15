from pathlib import Path
import pandas as pd
import numpy as np

ATTEMPT_FILE = Path(
    "data/canonical/v1/attempts.csv"
)

EVENT_FILE = Path(
    "data/canonical/v1/qualifying_events.csv"
)

LINKAGE_FILE = Path(
    "weather/output/v2b_section_mechanism/"
    "v2b_final_core_attempt_linkage_audit_v1.csv"
)

SECTION_FILE = Path(
    "data/canonical/v1/attempt_sections.csv"
)

OUTDIR = Path(
    "weather/output/v2b_section_mechanism"
)

OUTDIR.mkdir(
    parents=True,
    exist_ok=True
)

OUT_CANDIDATES = (
    OUTDIR
    / "v2b_missing_transition_recovery_candidates_v3.csv"
)

OUT_BEST = (
    OUTDIR
    / "v2b_missing_transition_recovery_best_v3.csv"
)

OUT_SUMMARY = (
    OUTDIR
    / "v2b_missing_transition_recovery_summary_v3.txt"
)


def norm_name(x):
    return (
        str(x)
        .strip()
        .lower()
        .replace(".", "")
        .replace("’", "'")
    )


print("=" * 100)
print("INDY 500 V2-B MISSING ATTEMPT-ID RECOVERY V3")
print("=" * 100)

attempts = pd.read_csv(
    ATTEMPT_FILE
)

events = pd.read_csv(
    EVENT_FILE
)

linkage = pd.read_csv(
    LINKAGE_FILE
)

sections = pd.read_csv(
    SECTION_FILE
)

missing = linkage[
    linkage["linkage_status"]
    == "no_explicit_anchor"
].copy()

print()
print(
    f"Missing final-core transitions: {len(missing)}"
)

# ============================================================
# ATTACH YEAR USING QUALIFYING EVENTS
# ============================================================

event_year = (
    events[
        [
            "session_id",
            "year",
        ]
    ]
    .drop_duplicates(
        "session_id"
    )
    .copy()
)

event_year["year"] = pd.to_numeric(
    event_year["year"],
    errors="coerce"
).astype("Int64")

attempts = attempts.merge(
    event_year,
    on="session_id",
    how="left",
    validate="many_to_one",
)

print()
print("ATTEMPT YEAR COUNTS")
print("-" * 100)

print(
    attempts[
        "year"
    ]
    .value_counts(
        dropna=False
    )
    .sort_index()
    .to_string()
)

# ============================================================
# NORMALIZE
# ============================================================

attempts["_car"] = (
    attempts[
        "car_number"
    ]
    .astype(str)
    .str.strip()
)

attempts["_driver"] = (
    attempts[
        "driver_name"
    ]
    .map(norm_name)
)

attempts["_speed"] = pd.to_numeric(
    attempts[
        "four_lap_average_speed_mph"
    ],
    errors="coerce"
)

attempts["_attempt_index"] = pd.to_numeric(
    attempts[
        "car_attempt_index"
    ],
    errors="coerce"
)

# ============================================================
# SECTION COVERAGE LOOKUP
# ============================================================

coverage = (
    sections.groupby(
        "attempt_id"
    )
    .agg(
        section_rows=(
            "attempt_section_id",
            "size"
        ),
        covered_laps=(
            "lap_number",
            lambda x:
                len(
                    pd.to_numeric(
                        x,
                        errors="coerce"
                    )
                    .dropna()
                    .unique()
                )
        ),
        valid_speed_rows=(
            "section_speed_mph",
            lambda x:
                pd.to_numeric(
                    x,
                    errors="coerce"
                )
                .notna()
                .sum()
        ),
    )
    .reset_index()
)

coverage_lookup = (
    coverage.set_index(
        "attempt_id"
    )
    .to_dict(
        orient="index"
    )
)

# ============================================================
# RECOVER EACH MISSING FINAL-CORE TRANSITION
# ============================================================

candidate_rows = []

for _, target in missing.iterrows():

    year = int(
        target["year"]
    )

    car = str(
        target["car_number"]
    ).strip()

    driver = norm_name(
        target[
            "driver_name"
        ]
    )

    target_delta = float(
        target[
            "delta_speed_final_core_mph"
        ]
    )

    g = attempts[
        (attempts["year"] == year)
        &
        (attempts["_car"] == car)
        &
        (attempts["_driver"] == driver)
        &
        attempts["_speed"].notna()
    ].copy()

    g = g.sort_values(
        [
            "_attempt_index",
            "start_time_utc",
        ],
        na_position="last"
    ).reset_index(
        drop=True
    )

    print()
    print("=" * 100)
    print(
        f"{year} | car {target['car_number']} | "
        f"{target['driver_name']} | target delta={target_delta:+.3f}"
    )
    print("-" * 100)

    if len(g):

        cols = [
            "attempt_id",
            "car_attempt_index",
            "four_lap_average_speed_mph",
            "start_time_utc",
            "result_status",
            "attempt_class",
        ]

        cols = [
            c for c in cols
            if c in g.columns
        ]

        print(
            g[
                cols
            ]
            .to_string(
                index=False
            )
        )

    else:

        print("No usable attempts found.")

    if len(g) < 2:

        candidate_rows.append({
            "year": year,
            "car_number":
                target["car_number"],
            "driver_name":
                target["driver_name"],
            "target_delta_speed_mph":
                target_delta,
            "candidate_rank":
                np.nan,
            "before_attempt_id":
                np.nan,
            "after_attempt_id":
                np.nan,
            "before_attempt_index":
                np.nan,
            "after_attempt_index":
                np.nan,
            "before_speed_mph":
                np.nan,
            "after_speed_mph":
                np.nan,
            "candidate_delta_speed_mph":
                np.nan,
            "delta_difference_mph":
                np.nan,
            "both_in_section_table":
                False,
            "both_four_lap_section_coverage":
                False,
            "status":
                "fewer_than_two_valid_attempts",
        })

        continue

    local = []

    for i in range(
        len(g) - 1
    ):

        before = g.iloc[i]
        after = g.iloc[i + 1]

        delta = (
            after["_speed"]
            - before["_speed"]
        )

        diff = abs(
            delta - target_delta
        )

        before_id = (
            before["attempt_id"]
        )

        after_id = (
            after["attempt_id"]
        )

        before_cov = (
            coverage_lookup.get(
                before_id,
                {}
            )
        )

        after_cov = (
            coverage_lookup.get(
                after_id,
                {}
            )
        )

        before_laps = (
            before_cov.get(
                "covered_laps",
                0
            )
        )

        after_laps = (
            after_cov.get(
                "covered_laps",
                0
            )
        )

        before_speed_rows = (
            before_cov.get(
                "valid_speed_rows",
                0
            )
        )

        after_speed_rows = (
            after_cov.get(
                "valid_speed_rows",
                0
            )
        )

        both_in_sections = (
            before_id
            in coverage_lookup
            and
            after_id
            in coverage_lookup
        )

        both_four_lap = (
            before_laps >= 4
            and
            after_laps >= 4
            and
            before_speed_rows > 0
            and
            after_speed_rows > 0
        )

        local.append({
            "year":
                year,

            "car_number":
                target["car_number"],

            "driver_name":
                target["driver_name"],

            "target_delta_speed_mph":
                target_delta,

            "candidate_attempt_count":
                len(g),

            "before_attempt_id":
                before_id,

            "after_attempt_id":
                after_id,

            "before_attempt_index":
                before[
                    "car_attempt_index"
                ],

            "after_attempt_index":
                after[
                    "car_attempt_index"
                ],

            "before_speed_mph":
                before["_speed"],

            "after_speed_mph":
                after["_speed"],

            "candidate_delta_speed_mph":
                delta,

            "delta_difference_mph":
                diff,

            "before_covered_laps":
                before_laps,

            "after_covered_laps":
                after_laps,

            "before_valid_speed_rows":
                before_speed_rows,

            "after_valid_speed_rows":
                after_speed_rows,

            "both_in_section_table":
                both_in_sections,

            "both_four_lap_section_coverage":
                both_four_lap,
        })

    local = sorted(
        local,
        key=lambda x:
            x[
                "delta_difference_mph"
            ]
    )

    for rank, row in enumerate(
        local,
        start=1
    ):

        row[
            "candidate_rank"
        ] = rank

        if (
            row[
                "delta_difference_mph"
            ]
            <= 0.005
            and
            row[
                "both_four_lap_section_coverage"
            ]
        ):
            row[
                "status"
            ] = "RECOVERABLE_STRONG"

        elif (
            row[
                "delta_difference_mph"
            ]
            <= 0.020
            and
            row[
                "both_in_section_table"
            ]
        ):
            row[
                "status"
            ] = "REVIEW_POSSIBLE"

        else:
            row[
                "status"
            ] = "WEAK_OR_UNRESOLVED"

        candidate_rows.append(
            row
        )

candidates = pd.DataFrame(
    candidate_rows
)

candidates.to_csv(
    OUT_CANDIDATES,
    index=False
)

# ============================================================
# BEST MATCH PER TARGET
# ============================================================

best = candidates[
    candidates[
        "candidate_rank"
    ] == 1
].copy()

best.to_csv(
    OUT_BEST,
    index=False
)

# ============================================================
# SUMMARY
# ============================================================

lines = []

def add(x=""):
    lines.append(str(x))


add("=" * 100)
add(
    "INDY 500 V2-B MISSING TRANSITION RECOVERY SUMMARY V3"
)
add("=" * 100)

add()
add(
    f"missing transitions evaluated: {len(missing)}"
)

add()
add(
    "BEST MATCH PER TRANSITION"
)
add("-" * 100)

show = [
    "year",
    "car_number",
    "driver_name",
    "target_delta_speed_mph",
    "candidate_attempt_count",
    "before_attempt_index",
    "after_attempt_index",
    "candidate_delta_speed_mph",
    "delta_difference_mph",
    "before_covered_laps",
    "after_covered_laps",
    "both_four_lap_section_coverage",
    "status",
]

existing = [
    c for c in show
    if c in best.columns
]

add(
    best[
        existing
    ]
    .to_string(
        index=False
    )
)

add()
add(
    "RECOVERY COUNTS"
)
add("-" * 100)

if "status" in best.columns:

    add(
        best[
            "status"
        ]
        .value_counts(
            dropna=False
        )
        .to_string()
    )

n_strong = int(
    (
        best[
            "status"
        ]
        == "RECOVERABLE_STRONG"
    ).sum()
)

add()
add(
    f"Strongly recoverable: {n_strong}/{len(missing)}"
)

add(
    f"Projected full-core linkage if accepted: "
    f"{27 + n_strong}/41"
)

summary = "\n".join(
    lines
)

OUT_SUMMARY.write_text(
    summary,
    encoding="utf-8"
)

print()
print(summary)

print()
print("=" * 100)
print("OUTPUTS")
print("=" * 100)

print(OUT_CANDIDATES)
print(OUT_BEST)
print(OUT_SUMMARY)

print()
print("DONE")
