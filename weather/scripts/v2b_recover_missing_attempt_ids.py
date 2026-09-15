from pathlib import Path
import pandas as pd
import numpy as np

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

OUT_CANDIDATES = (
    OUTDIR
    / "v2b_missing_transition_recovery_candidates_v1.csv"
)

OUT_SUMMARY = (
    OUTDIR
    / "v2b_missing_transition_recovery_summary_v1.txt"
)


def norm_name(x):
    return (
        str(x)
        .strip()
        .lower()
        .replace(".", "")
        .replace("’", "'")
    )


def load_first_existing(paths):

    for p in paths:
        p = Path(p)

        if p.exists():
            return p, pd.read_csv(p)

    return None, None


print("=" * 100)
print("INDY 500 V2-B MISSING ATTEMPT-ID RECOVERY")
print("=" * 100)

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

print(
    missing[
        [
            "year",
            "car_number",
            "driver_name",
            "delta_speed_final_core_mph",
        ]
    ]
    .to_string(index=False)
)

# ============================================================
# DISCOVER CANONICAL ATTEMPT TABLE
# ============================================================

attempt_paths = [
    "data/canonical/v1/attempts.csv",
    "data/canonical/v1/attempt_results.csv",
    "data/canonical/v1/qualifying_attempts.csv",
    "data/canonical/v1/attempt_performance.csv",
]

attempt_path, attempts = load_first_existing(
    attempt_paths
)

if attempts is None:

    print()
    print("=" * 100)
    print("NO STANDARD ATTEMPT TABLE FOUND — SEARCHING CSV HEADERS")
    print("=" * 100)

    candidates = []

    for p in Path(".").rglob("*.csv"):

        try:
            df = pd.read_csv(
                p,
                nrows=3
            )
        except Exception:
            continue

        cols = [
            str(c).lower()
            for c in df.columns
        ]

        score = 0

        needed_groups = {
            "attempt":
                any("attempt_id" in c for c in cols),

            "year":
                any(c == "year" for c in cols),

            "car":
                any("car_number" in c for c in cols),

            "driver":
                any("driver_name" in c for c in cols),

            "speed":
                any(
                    (
                        "four_lap" in c
                        and "speed" in c
                    )
                    or
                    "average_speed" in c
                    or
                    "avg_speed" in c
                    for c in cols
                ),
        }

        score = sum(
            needed_groups.values()
        )

        if score >= 4:
            candidates.append(
                (
                    score,
                    str(p),
                    list(df.columns),
                )
            )

    for score, path, cols in sorted(
        candidates,
        key=lambda x: (-x[0], x[1])
    )[:50]:

        print()
        print(
            f"[score={score}] {path}"
        )
        print(cols)

    print()
    print(
        "STOP: paste this discovery output back before proceeding."
    )

    raise SystemExit(0)


print()
print(
    "Using canonical attempt table:"
)
print(attempt_path)

print(
    "shape:",
    attempts.shape
)

print(
    "columns:",
    attempts.columns.tolist()
)

# ============================================================
# IDENTIFY REQUIRED COLUMNS
# ============================================================

cols_lower = {
    str(c).lower(): c
    for c in attempts.columns
}

def find_col(exact=None, contains=None):

    if exact:

        for e in exact:
            if e in cols_lower:
                return cols_lower[e]

    if contains:

        for c in attempts.columns:
            low = str(c).lower()

            if all(
                token in low
                for token in contains
            ):
                return c

    return None


attempt_id_col = find_col(
    exact=["attempt_id"]
)

year_col = find_col(
    exact=["year"]
)

car_col = find_col(
    exact=["car_number", "car_no"]
)

driver_col = find_col(
    exact=["driver_name", "driver"]
)

speed_col = None

speed_preferences = [
    ["four_lap_average_speed_mph"],
    ["four", "lap", "average", "speed"],
    ["average", "speed", "mph"],
    ["avg", "speed", "mph"],
]

for tokens in speed_preferences:

    speed_col = find_col(
        contains=tokens
    )

    if speed_col is not None:
        break


print()
print("Resolved columns")
print("-" * 100)
print("attempt_id:", attempt_id_col)
print("year:", year_col)
print("car:", car_col)
print("driver:", driver_col)
print("speed:", speed_col)

required = [
    attempt_id_col,
    year_col,
    car_col,
    driver_col,
    speed_col,
]

if any(x is None for x in required):

    print()
    print(
        "Could not identify all required columns."
    )
    print(
        "Paste the resolved-column output back."
    )

    raise SystemExit(0)

# ============================================================
# NORMALIZE ATTEMPTS
# ============================================================

a = attempts.copy()

a["_year"] = pd.to_numeric(
    a[year_col],
    errors="coerce"
).astype("Int64")

a["_car"] = (
    a[car_col]
    .astype(str)
    .str.strip()
)

a["_driver"] = (
    a[driver_col]
    .map(norm_name)
)

a["_speed"] = pd.to_numeric(
    a[speed_col],
    errors="coerce"
)

# ============================================================
# FIND ORDERING COLUMN
# ============================================================

order_candidates = [
    "attempt_sequence",
    "attempt_number",
    "sequence",
    "sequence_index",
    "chronology_index",
    "start_time",
    "timestamp",
    "attempt_time",
    "session_elapsed",
    "session_elapsed_s",
]

order_col = None

for name in order_candidates:

    if name in cols_lower:
        order_col = cols_lower[name]
        break

print()
print(
    "Ordering column:",
    order_col
)

# If no explicit ordering column, preserve original canonical table order.
a["_source_order"] = np.arange(
    len(a)
)

# ============================================================
# BUILD SAME-CAR SEQUENTIAL TRANSITION CANDIDATES
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
        target["driver_name"]
    )

    target_delta = float(
        target[
            "delta_speed_final_core_mph"
        ]
    )

    g = a[
        (a["_year"] == year)
        &
        (a["_car"] == car)
        &
        (a["_driver"] == driver)
        &
        a["_speed"].notna()
    ].copy()

    if order_col is not None:

        # Try numeric first, fallback textual sort.
        numeric_order = pd.to_numeric(
            g[order_col],
            errors="coerce"
        )

        if numeric_order.notna().all():

            g["_order"] = numeric_order
            g = g.sort_values(
                "_order"
            )

        else:

            try:
                dt = pd.to_datetime(
                    g[order_col],
                    errors="coerce"
                )

                if dt.notna().all():
                    g["_order"] = dt
                    g = g.sort_values(
                        "_order"
                    )
                else:
                    g = g.sort_values(
                        "_source_order"
                    )

            except Exception:
                g = g.sort_values(
                    "_source_order"
                )

    else:
        g = g.sort_values(
            "_source_order"
        )

    g = g.reset_index(
        drop=True
    )

    if len(g) < 2:

        candidate_rows.append({
            "year": year,
            "car_number": car,
            "driver_name":
                target["driver_name"],
            "target_delta_speed_mph":
                target_delta,
            "candidate_rank": np.nan,
            "before_attempt_id": np.nan,
            "after_attempt_id": np.nan,
            "before_speed_mph": np.nan,
            "after_speed_mph": np.nan,
            "candidate_delta_speed_mph":
                np.nan,
            "delta_difference_mph":
                np.nan,
            "candidate_attempt_count":
                len(g),
            "status":
                "fewer_than_two_attempts",
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
            "year": year,
            "car_number": car,
            "driver_name":
                target["driver_name"],
            "target_delta_speed_mph":
                target_delta,
            "before_attempt_id":
                before[attempt_id_col],
            "after_attempt_id":
                after[attempt_id_col],
            "before_speed_mph":
                before["_speed"],
            "after_speed_mph":
                after["_speed"],
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

        row["candidate_rank"] = rank

        if row[
            "delta_difference_mph"
        ] <= 0.005:

            row["status"] = (
                "strong_numeric_match"
            )

        elif row[
            "delta_difference_mph"
        ] <= 0.02:

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
# SECTION TABLE PRESENCE CHECK
# ============================================================

section_attempt_ids = set(
    sections["attempt_id"]
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
    .isin(section_attempt_ids)
)

candidates[
    "after_in_section_table"
] = (
    candidates[
        "after_attempt_id"
    ]
    .astype(str)
    .isin(section_attempt_ids)
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

candidates.to_csv(
    OUT_CANDIDATES,
    index=False
)

# ============================================================
# BEST CANDIDATE SUMMARY
# ============================================================

best = (
    candidates[
        candidates[
            "candidate_rank"
        ] == 1
    ]
    .copy()
)

best["auto_recovery_status"] = np.where(
    (
        best[
            "delta_difference_mph"
        ] <= 0.005
    )
    &
    best[
        "both_in_section_table"
    ],
    "RECOVERABLE",
    "REVIEW"
)

lines = []

def add(x=""):
    lines.append(str(x))


add("=" * 100)
add(
    "INDY 500 V2-B MISSING TRANSITION RECOVERY SUMMARY"
)
add("=" * 100)

add()
add(
    f"missing transitions evaluated: {len(missing)}"
)

add()
add("BEST CANDIDATE PER TRANSITION")
add("-" * 100)

add(
    best[
        [
            "year",
            "car_number",
            "driver_name",
            "target_delta_speed_mph",
            "candidate_attempt_count",
            "before_attempt_id",
            "after_attempt_id",
            "candidate_delta_speed_mph",
            "delta_difference_mph",
            "both_in_section_table",
            "auto_recovery_status",
        ]
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
        "auto_recovery_status"
    ]
    .value_counts()
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
print(summary)

print()
print("=" * 100)
print("OUTPUTS")
print("=" * 100)
print(OUT_CANDIDATES)
print(OUT_SUMMARY)

print()
print("DONE")
