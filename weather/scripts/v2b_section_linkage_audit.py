from pathlib import Path
import pandas as pd
import numpy as np

SECTION_FILE = Path(
    "data/canonical/v1/attempt_sections.csv"
)

FINAL_CORE_FILE = Path(
    "r5_2/manual/probabilistic_physics_loyo_residuals_v1.csv"
)

ANCHOR_FILE = Path(
    "r5/output/r5_final_thermal_response_repeat_predictions_v1.csv"
)

OUTDIR = Path(
    "weather/output/v2b_section_mechanism"
)

OUTDIR.mkdir(
    parents=True,
    exist_ok=True
)

LINKAGE_OUT = (
    OUTDIR
    / "v2b_final_core_attempt_linkage_audit_v1.csv"
)

ATTEMPT_COVERAGE_OUT = (
    OUTDIR
    / "v2b_attempt_section_coverage_v1.csv"
)

SUMMARY_OUT = (
    OUTDIR
    / "v2b_section_linkage_audit_summary_v1.txt"
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
print("INDY 500 V2-B SECTION LINKAGE AUDIT")
print("=" * 100)

sections = pd.read_csv(
    SECTION_FILE
)

core = pd.read_csv(
    FINAL_CORE_FILE
)

anchor = pd.read_csv(
    ANCHOR_FILE
)

print()
print("INPUT SHAPES")
print("-" * 100)
print(
    "attempt_sections:",
    sections.shape
)
print(
    "final 41-transition core:",
    core.shape
)
print(
    "explicit-ID anchor transitions:",
    anchor.shape
)

# ============================================================
# NORMALIZE KEYS
# ============================================================

for df in [core, anchor]:

    df["_driver_key"] = (
        df["driver_name"]
        .map(norm_name)
    )

    df["_car_key"] = (
        df["car_number"]
        .astype(str)
        .str.strip()
    )

    df["_year_key"] = (
        pd.to_numeric(
            df["year"],
            errors="coerce"
        )
        .astype("Int64")
    )

# ============================================================
# DIRECT MATCH FINAL CORE -> OLD EXPLICIT-ID ANCHOR
#
# Use identity plus observed delta speed.
# We do NOT assume one transition per car/year.
# ============================================================

rows = []

for idx, r in core.iterrows():

    cand = anchor[
        (anchor["_year_key"] == r["_year_key"])
        &
        (anchor["_car_key"] == r["_car_key"])
        &
        (anchor["_driver_key"] == r["_driver_key"])
    ].copy()

    target_delta = (
        r["delta_four_lap_average_speed_mph"]
    )

    if len(cand):

        cand["_delta_diff"] = (
            cand["delta_speed_mph"]
            - target_delta
        ).abs()

        cand = cand.sort_values(
            "_delta_diff"
        )

        best = cand.iloc[0]

        # Tight enough to identify the same transition,
        # but retain difference explicitly for audit.
        if best["_delta_diff"] <= 0.005:

            status = "matched_explicit_anchor"

            before_id = (
                best["before_attempt_id"]
            )

            after_id = (
                best["after_attempt_id"]
            )

            diff = float(
                best["_delta_diff"]
            )

        else:

            status = (
                "identity_found_delta_mismatch"
            )

            before_id = np.nan
            after_id = np.nan
            diff = float(
                best["_delta_diff"]
            )

    else:

        status = "no_explicit_anchor"

        before_id = np.nan
        after_id = np.nan
        diff = np.nan

    rows.append({
        "core_row": idx,
        "year": r["year"],
        "car_number": r["car_number"],
        "driver_name": r["driver_name"],
        "delta_speed_final_core_mph":
            target_delta,
        "residual_loyo_centered":
            r["residual_loyo_centered"],
        "linkage_status":
            status,
        "before_attempt_id":
            before_id,
        "after_attempt_id":
            after_id,
        "anchor_delta_difference_mph":
            diff,
    })

linkage = pd.DataFrame(
    rows
)

# ============================================================
# SECTION COVERAGE PER ATTEMPT
# ============================================================

coverage_rows = []

for attempt_id, g in sections.groupby(
    "attempt_id",
    dropna=False
):

    valid_speed = g[
        "section_speed_mph"
    ].notna()

    valid_time = g[
        "section_time_seconds"
    ].notna()

    section_names = sorted(
        g.loc[
            valid_speed | valid_time,
            "section_name"
        ]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    laps = sorted(
        pd.to_numeric(
            g.loc[
                valid_speed | valid_time,
                "lap_number"
            ],
            errors="coerce"
        )
        .dropna()
        .astype(int)
        .unique()
        .tolist()
    )

    coverage_rows.append({
        "attempt_id":
            attempt_id,
        "section_rows":
            len(g),
        "valid_section_speed_rows":
            int(valid_speed.sum()),
        "valid_section_time_rows":
            int(valid_time.sum()),
        "unique_section_names":
            len(section_names),
        "section_names":
            "|".join(section_names),
        "covered_laps":
            "|".join(map(str, laps)),
        "n_covered_laps":
            len(laps),
        "full_lap_coverage_rows":
            int(
                pd.to_numeric(
                    g[
                        "full_lap_coverage_member"
                    ],
                    errors="coerce"
                )
                .fillna(0)
                .astype(bool)
                .sum()
            ),
    })

attempt_coverage = pd.DataFrame(
    coverage_rows
)

# ============================================================
# ATTACH BEFORE / AFTER COVERAGE
# ============================================================

before_cov = (
    attempt_coverage
    .add_prefix("before_")
    .rename(
        columns={
            "before_attempt_id":
                "before_attempt_id"
        }
    )
)

after_cov = (
    attempt_coverage
    .add_prefix("after_")
    .rename(
        columns={
            "after_attempt_id":
                "after_attempt_id"
        }
    )
)

linkage = linkage.merge(
    before_cov,
    on="before_attempt_id",
    how="left"
)

linkage = linkage.merge(
    after_cov,
    on="after_attempt_id",
    how="left"
)

linkage["both_attempts_in_section_table"] = (
    linkage[
        "before_section_rows"
    ].notna()
    &
    linkage[
        "after_section_rows"
    ].notna()
)

linkage["both_have_section_speed"] = (
    linkage[
        "before_valid_section_speed_rows"
    ].fillna(0)
    > 0
) & (
    linkage[
        "after_valid_section_speed_rows"
    ].fillna(0)
    > 0
)

linkage["both_cover_four_laps"] = (
    linkage[
        "before_n_covered_laps"
    ].fillna(0)
    >= 4
) & (
    linkage[
        "after_n_covered_laps"
    ].fillna(0)
    >= 4
)

# ============================================================
# SAVE
# ============================================================

linkage.to_csv(
    LINKAGE_OUT,
    index=False
)

attempt_coverage.to_csv(
    ATTEMPT_COVERAGE_OUT,
    index=False
)

# ============================================================
# SUMMARY
# ============================================================

status_counts = (
    linkage[
        "linkage_status"
    ]
    .value_counts(
        dropna=False
    )
)

n_core = len(linkage)

n_linked = int(
    (
        linkage[
            "linkage_status"
        ]
        == "matched_explicit_anchor"
    ).sum()
)

n_both = int(
    linkage[
        "both_attempts_in_section_table"
    ].sum()
)

n_speed = int(
    linkage[
        "both_have_section_speed"
    ].sum()
)

n_four = int(
    linkage[
        "both_cover_four_laps"
    ].sum()
)

lines = []

def add(x=""):
    lines.append(str(x))


add("=" * 100)
add(
    "INDY 500 V2-B SECTION LINKAGE AUDIT SUMMARY"
)
add("=" * 100)

add()
add("FINAL CORE")
add(
    f"transitions: {n_core}"
)

add()
add("EXPLICIT ATTEMPT-ID LINKAGE")
add(
    f"matched: {n_linked}/{n_core}"
)

add()
add(
    status_counts.to_string()
)

add()
add("SECTION AVAILABILITY AMONG FINAL CORE")
add(
    "both before/after attempts present in "
    f"attempt_sections.csv: {n_both}/{n_core}"
)

add(
    "both before/after have section-speed data: "
    f"{n_speed}/{n_core}"
)

add(
    "both before/after cover >=4 laps in section table: "
    f"{n_four}/{n_core}"
)

add()
add("MATCHED TRANSITIONS")
add(
    linkage[
        [
            "year",
            "car_number",
            "driver_name",
            "delta_speed_final_core_mph",
            "linkage_status",
            "both_attempts_in_section_table",
            "both_have_section_speed",
            "before_n_covered_laps",
            "after_n_covered_laps",
        ]
    ]
    .to_string(
        index=False
    )
)

summary = "\n".join(
    lines
)

SUMMARY_OUT.write_text(
    summary,
    encoding="utf-8"
)

print()
print(summary)

print()
print("=" * 100)
print("OUTPUTS")
print("=" * 100)

print(LINKAGE_OUT)
print(ATTEMPT_COVERAGE_OUT)
print(SUMMARY_OUT)

print()
print("DONE")
