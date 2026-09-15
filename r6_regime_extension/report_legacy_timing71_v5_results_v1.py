from pathlib import Path
import pandas as pd

ROOT = Path(
    "/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈"
)

SRC = (
    ROOT /
    "r6_regime_extension/output/"
    "timing71_legacy_attempt_reconstruction_v5"
)

MATCH_FILE = (
    SRC /
    "legacy_official_attempt_matches_global_v5.csv"
)

COVERAGE_FILE = (
    SRC /
    "legacy_official_coverage_audit_v5.csv"
)

SUMMARY_FILE = (
    SRC /
    "legacy_match_summary_v5.csv"
)

TRANS_FILE = (
    SRC /
    "legacy_verified_repeat_transitions_v5.csv"
)

required = [
    MATCH_FILE,
    COVERAGE_FILE,
    SUMMARY_FILE,
    TRANS_FILE,
]

for p in required:

    if not p.exists():

        raise FileNotFoundError(
            f"Missing expected V5 output: {p}"
        )


matches = pd.read_csv(
    MATCH_FILE,
    low_memory=False
)

coverage = pd.read_csv(
    COVERAGE_FILE,
    low_memory=False
)

summary = pd.read_csv(
    SUMMARY_FILE,
    low_memory=False
)

transitions = pd.read_csv(
    TRANS_FILE,
    low_memory=False
)


# ============================================================
# QA — required columns
# ============================================================

required_match_columns = [
    "year",
    "source_rank",
    "car_number",
    "driver_name",
    "match_quality",
    "lap_match_abs_sum_s",
    "timestamp_quality",
    "attempt_mid_ts",
    "attempt_mid_utc",
    "candidate_id",
]

missing = [
    c
    for c in required_match_columns
    if c not in matches.columns
]

if missing:

    raise RuntimeError(
        "V5 match file is missing columns: "
        + ", ".join(
            missing
        )
    )


print(
    "=" * 160
)

print(
    "PART 1 — SAVED V5 SUMMARY"
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
    "PART 2 — SAVED V5 UNMATCHED REASONS"
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


# ============================================================
# Correct PART 4:
# sort FULL dataframe first, then select display columns
# ============================================================

print(
    "\n" + "=" * 160
)

print(
    "PART 4 — MATCH DETAIL"
)

print(
    "=" * 160
)

ordered_matches = (
    matches
    .sort_values(
        [
            "year",
            "attempt_mid_ts",
            "source_rank",
        ],
        na_position="last"
    )
)

display_columns = [
    "year",
    "source_rank",
    "car_number",
    "driver_name",
    "match_quality",
    "lap_match_abs_sum_s",
    "timestamp_quality",
    "attempt_mid_utc",
]

print(
    ordered_matches[
        display_columns
    ]
    .to_string(
        index=False
    )
)


# ============================================================
# PART 5
# ============================================================

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

    sort_cols = []

    if "year" in transitions.columns:
        sort_cols.append(
            "year"
        )

    if (
        "from_timestamp_utc"
        in transitions.columns
    ):
        sort_cols.append(
            "from_timestamp_utc"
        )

    if sort_cols:

        transitions = (
            transitions
            .sort_values(
                sort_cols
            )
        )

    print(
        transitions.to_string(
            index=False
        )
    )


# ============================================================
# Extra QA
# ============================================================

print(
    "\n" + "=" * 160
)

print(
    "PART 6 — ONE-TO-ONE / TIMESTAMP QA"
)

print(
    "=" * 160
)

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

acceptable = matches[
    matches[
        "match_quality"
    ]
    .isin([
        "EXACT_OR_NEAR_EXACT",
        "PLAUSIBLE",
    ])
].copy()

timestamped_acceptable = acceptable[
    acceptable[
        "attempt_mid_ts"
    ]
    .notna()
].copy()

print(
    "duplicate_candidate_rows =",
    duplicate_candidate_rows
)

print(
    "duplicate_official_rows =",
    duplicate_official_rows
)

print(
    "acceptable_matches =",
    len(
        acceptable
    )
)

print(
    "timestamped_acceptable_matches =",
    len(
        timestamped_acceptable
    )
)

print(
    "\nBY YEAR:"
)

qa_year = (
    matches.groupby(
        "year"
    )
    .agg(
        assigned_matches=(
            "source_rank",
            "size"
        ),

        unique_candidates=(
            "candidate_id",
            "nunique"
        ),

        timestamped_matches=(
            "attempt_mid_ts",
            lambda s:
                int(
                    s.notna().sum()
                )
        ),
    )
    .reset_index()
)

print(
    qa_year.to_string(
        index=False
    )
)


if (
    duplicate_candidate_rows
    != 0
):

    raise RuntimeError(
        "One-to-one QA failed: "
        "candidate reused."
    )

if (
    duplicate_official_rows
    != 0
):

    raise RuntimeError(
        "One-to-one QA failed: "
        "official attempt duplicated."
    )


print(
    "\nR6_LEGACY_TIMING71_V5_REPORT_V1_COMPLETE"
)
