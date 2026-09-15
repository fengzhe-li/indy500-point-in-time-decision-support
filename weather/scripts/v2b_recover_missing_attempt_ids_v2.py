from pathlib import Path
import pandas as pd
import numpy as np

ATTEMPT_FILE = Path(
    "data/canonical/v1/attempts.csv"
)

CORE_FILE = Path(
    "r5_2/manual/probabilistic_physics_loyo_residuals_v1.csv"
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
    / "v2b_missing_transition_recovery_candidates_v2.csv"
)

OUT_BEST = (
    OUTDIR
    / "v2b_missing_transition_recovery_best_v2.csv"
)

OUT_SUMMARY = (
    OUTDIR
    / "v2b_missing_transition_recovery_summary_v2.txt"
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
print("INDY 500 V2-B MISSING ATTEMPT-ID RECOVERY V2")
print("=" * 100)

attempts = pd.read_csv(
    ATTEMPT_FILE
)

core = pd.read_csv(
    CORE_FILE
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
# FIND SESSION TABLE
# ============================================================

session_candidates = [
    Path("data/canonical/v1/sessions.csv"),
    Path("data/canonical/v1/session.csv"),
    Path("data/canonical/v1/session_metadata.csv"),
    Path("data/canonical/v1/events.csv"),
]

session_file = None
sessions = None

for p in session_candidates:

    if p.exists():

        try:
            df = pd.read_csv(p)
        except Exception:
            continue

        cols = [
            str(c).lower()
            for c in df.columns
        ]

        if "session_id" in cols:
            session_file = p
            sessions = df
            break


if sessions is None:

    print()
    print("=" * 100)
    print("SEARCHING FOR SESSION TABLE")
    print("=" * 100)

    discovered = []

    for p in Path(
        "data/canonical/v1"
    ).glob("*.csv"):

        try:
            df = pd.read_csv(
                p,
                nrows=5
            )
        except Exception:
            continue

        low = [
            str(c).lower()
            for c in df.columns
        ]

        if "session_id" in low:

            discovered.append(
                (
                    str(p),
                    list(df.columns),
                )
            )

    for path, cols in discovered:
        print()
        print(path)
        print(cols)

    raise SystemExit(
        "\nNo automatically usable session table found."
    )


print()
print(
    "Using session table:",
    session_file
)

print(
    "shape:",
    sessions.shape
)

print(
    "columns:",
    sessions.columns.tolist()
)

# ============================================================
# RESOLVE YEAR
# ============================================================

session_cols = {
    str(c).lower(): c
    for c in sessions.columns
}

year_col = None

for candidate in [
    "year",
    "event_year",
    "season",
    "season_year",
]:

    if candidate in session_cols:
        year_col = session_cols[
            candidate
        ]
        break


# If no explicit year column, derive from date/time.
if year_col is None:

    date_col = None

    for candidate in [
        "session_date",
        "date",
        "start_time_utc",
        "event_date",
        "session_start_utc",
    ]:

        if candidate in session_cols:
            date_col = session_cols[
                candidate
            ]
            break

    if date_col is not None:

        sessions["_derived_year"] = (
            pd.to_datetime(
                sessions[date_col],
                errors="coerce",
                utc=True
            )
            .dt.year
        )

        year_col = "_derived_year"


if year_col is None:

    print()
    print(
        "Could not resolve year from session table."
    )
    print(
        sessions.columns.tolist()
    )

    raise SystemExit(0)


print(
    "Resolved year column:",
    year_col
)

# ============================================================
# ATTACH YEAR TO ATTEMPTS
# ============================================================

session_year = (
    sessions[
        [
            session_cols["session_id"],
            year_col,
        ]
    ]
    .copy()
)

session_year.columns = [
    "session_id",
    "_year",
]

session_year["_year"] = (
    pd.to_numeric(
        session_year["_year"],
        errors="coerce"
    )
    .astype("Int64")
)

attempts = attempts.merge(
    session_year,
    on="session_id",
    how="left",
    validate="many_to_one",
)

print()
print("Attempt years:")
print(
    attempts[
        "_year"
    ]
    .value_counts(
        dropna=False
    )
    .sort_index()
    .to_string()
)

# ============================================================
# NORMALIZE ATTEMPT DATA
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

attempts["_speed"] = (
    pd.to_numeric(
        attempts[
            "four_lap_average_speed_mph"
        ],
        errors="coerce"
    )
)

attempts["_attempt_index"] = (
    pd.to_numeric(
        attempts[
            "car_attempt_index"
        ],
        errors="coerce"
    )
)

# ============================================================
# BUILD CANDIDATE TRANSITIONS
#
# Important:
# Use car_attempt_index as chronology.
# Compare consecutive valid attempts for same car/year/driver.
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
        (attempts["_year"] == year)
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
    print("-" * 100)
    print(
        year,
        target["car_number"],
        target["driver_name"],
        "target Δ=",
        target_delta,
    )

    print(
        "usable attempts:",
        len(g)
    )

    if len(g):

        show_cols = [
            "attempt_id",
            "car_attempt_index",
            "four_lap_average_speed_mph",
            "start_time_utc",
            "result_status",
            "attempt_class",
        ]

        existing_show = [
            c for c in show_cols
            if c in g.columns
        ]

        print(
            g[
                existing_show
            ]
            .to_string(
                index=False
            )
        )

    if len(g) < 2:

        candidate_rows.append({
            "year":
                year,
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
            "candidate_attempt_count":
                len(g),
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

        local.append({
            "year":
                year,

            "car_number":
                target["car_number"],

            "driver_name":
                target["driver_name"],

            "target_delta_speed_mph":
                target_delta,

            "before_attempt_id":
                before["attempt_id"],

            "after_attempt_id":
                after["attempt_id"],

            "before_attempt_index":
                before[
                    "car_attempt_index"
                ],

            "after_attempt_index":
                after[
                    "car_attempt_index"
                ],

            "before_speed_mph":
                before[
                    "_speed"
                ],

            "after_speed_mph":
                after[
                    "_speed"
                ],

            "candidate_delta_speed_mph":
                delta,

            "delta_difference_mph":
                diff,

            "candidate_attempt_count":
                len(g),
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
        ):

            row["status"] = (
                "strong_numeric_match"
            )

        elif (
            row[
                "delta_difference_mph"
            ]
            <= 0.020
        ):

            row["status"] = (
                "possible_numeric_match"
            )

        else:

            row["status"] = (
                "weak_match"
            )

        candidate_rows.append(
            row
        )


candidates = pd.DataFrame(
    candidate_rows
)

# ============================================================
# CHECK SECTION AVAILABILITY
# ============================================================

section_ids = set(
    sections[
        "attempt_id"
    ]
    .dropna()
    .astype(str)
)

candidates[
    "before_in_section_table"
] = (
    candidates[
        "before_attempt_id"
    ]
    .astype(str)
    .isin(section_ids)
)

candidates[
    "after_in_section_table"
] = (
    candidates[
        "after_attempt_id"
    ]
    .astype(str)
    .isin(section_ids)
)

candidates[
    "both_in_section_table"
] = (
    candidates[
        "before_in_section_table"
    ]
    &
    candidates[
        "after_in_section_table"
    ]
)

# ============================================================
# SECTION LAP COVERAGE
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

before_cov = (
    coverage.rename(
        columns={
            "attempt_id":
                "before_attempt_id",
            "section_rows":
                "before_section_rows",
            "covered_laps":
                "before_covered_laps",
            "valid_speed_rows":
                "before_valid_speed_rows",
        }
    )
)

after_cov = (
    coverage.rename(
        columns={
            "attempt_id":
                "after_attempt_id",
            "section_rows":
                "after_section_rows",
            "covered_laps":
                "after_covered_laps",
            "valid_speed_rows":
                "after_valid_speed_rows",
        }
    )
)

candidates = candidates.merge(
    before_cov,
    on="before_attempt_id",
    how="left"
)

candidates = candidates.merge(
    after_cov,
    on="after_attempt_id",
    how="left"
)

candidates[
    "both_four_lap_section_coverage"
] = (
    candidates[
        "before_covered_laps"
    ]
    .fillna(0)
    >= 4
) & (
    candidates[
        "after_covered_laps"
    ]
    .fillna(0)
    >= 4
)

candidates.to_csv(
    OUT_CANDIDATES,
    index=False
)

# ============================================================
# BEST CANDIDATE PER TARGET TRANSITION
# ============================================================

best = (
    candidates[
        candidates[
            "candidate_rank"
        ] == 1
    ]
    .copy()
)

best[
    "recovery_status"
] = np.select(
    [
        (
            best[
                "delta_difference_mph"
            ]
            <= 0.005
        )
        &
        best[
            "both_four_lap_section_coverage"
        ],

        (
            best[
                "delta_difference_mph"
            ]
            <= 0.020
        )
        &
        best[
            "both_in_section_table"
        ],
    ],
    [
        "RECOVERABLE_STRONG",
        "REVIEW_POSSIBLE",
    ],
    default="UNRESOLVED",
)

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
    "INDY 500 V2-B MISSING TRANSITION RECOVERY SUMMARY V2"
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
    "both_in_section_table",
    "both_four_lap_section_coverage",
    "recovery_status",
]

add(
    best[
        show
    ]
    .to_string(
        index=False
    )
)

add()
add("RECOVERY COUNTS")
add("-" * 100)

add(
    best[
        "recovery_status"
    ]
    .value_counts(
        dropna=False
    )
    .to_string()
)

summary = "\n".join(
    lines
)

OUT_SUMMARY.write_text(
    summary,
    encoding="utf-8"
)

print()
print("=" * 100)
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
