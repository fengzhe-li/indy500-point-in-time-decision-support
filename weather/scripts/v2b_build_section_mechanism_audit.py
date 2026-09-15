from pathlib import Path
import pandas as pd
import numpy as np

SECTION_FILE = Path(
    "data/canonical/v1/attempt_sections.csv"
)

CORE_FILE = Path(
    "r5_2/manual/probabilistic_physics_loyo_residuals_v1.csv"
)

OLD_LINKAGE_FILE = Path(
    "weather/output/v2b_section_mechanism/"
    "v2b_final_core_attempt_linkage_audit_v1.csv"
)

RECOVERY_FILE = Path(
    "weather/output/v2b_section_mechanism/"
    "v2b_missing_transition_recovery_best_v3.csv"
)

OUTDIR = Path(
    "weather/output/v2b_section_mechanism"
)

OUTDIR.mkdir(
    parents=True,
    exist_ok=True
)

OUT_TRANSITIONS = (
    OUTDIR /
    "v2b_transition_map_v1.csv"
)

OUT_SECTION_LONG = (
    OUTDIR /
    "v2b_section_changes_long_v1.csv"
)

OUT_MECHANISM = (
    OUTDIR /
    "v2b_transition_section_mechanism_metrics_v1.csv"
)

OUT_SUMMARY = (
    OUTDIR /
    "v2b_section_mechanism_descriptive_summary_v1.txt"
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
print("INDY 500 V2-B SECTION MECHANISM DESCRIPTIVE AUDIT")
print("=" * 100)

sections = pd.read_csv(SECTION_FILE)
core = pd.read_csv(CORE_FILE)
old = pd.read_csv(OLD_LINKAGE_FILE)
recovery = pd.read_csv(RECOVERY_FILE)

# =============================================================================
# CORE UNIQUE ROW ID
# =============================================================================

core = core.reset_index(drop=True)
core["core_row"] = core.index

core["_year"] = pd.to_numeric(
    core["year"],
    errors="coerce"
).astype("Int64")

core["_car"] = (
    core["car_number"]
    .astype(str)
    .str.strip()
)

core["_driver"] = (
    core["driver_name"]
    .map(norm_name)
)

# =============================================================================
# START WITH ORIGINAL 27 EXPLICIT-ID LINKS
# =============================================================================

transition_rows = []

for _, r in old.iterrows():

    if r["linkage_status"] == "matched_explicit_anchor":

        transition_rows.append({
            "core_row":
                int(r["core_row"]),

            "year":
                int(r["year"]),

            "car_number":
                r["car_number"],

            "driver_name":
                r["driver_name"],

            "delta_speed_mph":
                r["delta_speed_final_core_mph"],

            "residual_loyo_centered":
                r["residual_loyo_centered"],

            "before_attempt_id":
                r["before_attempt_id"],

            "after_attempt_id":
                r["after_attempt_id"],

            "linkage_source":
                "original_explicit_anchor",

            "linkage_status":
                "linked",
        })

# =============================================================================
# ADD 12 STRONG RECOVERIES
# =============================================================================

missing_old = old[
    old["linkage_status"] == "no_explicit_anchor"
].copy()

missing_old["_year"] = pd.to_numeric(
    missing_old["year"],
    errors="coerce"
).astype("Int64")

missing_old["_car"] = (
    missing_old["car_number"]
    .astype(str)
    .str.strip()
)

missing_old["_driver"] = (
    missing_old["driver_name"]
    .map(norm_name)
)

for _, rec in recovery.iterrows():

    if rec["status"] != "RECOVERABLE_STRONG":
        continue

    year = int(rec["year"])
    car = str(rec["car_number"]).strip()
    driver = norm_name(rec["driver_name"])
    target_delta = float(rec["target_delta_speed_mph"])

    cand = missing_old[
        (missing_old["_year"] == year)
        &
        (missing_old["_car"] == car)
        &
        (missing_old["_driver"] == driver)
        &
        (
            (
                missing_old["delta_speed_final_core_mph"]
                - target_delta
            ).abs()
            <= 0.005
        )
    ].copy()

    if len(cand) != 1:
        raise RuntimeError(
            f"Recovery mapping not unique: "
            f"{year} {car} {rec['driver_name']} "
            f"delta={target_delta}; matches={len(cand)}"
        )

    r = cand.iloc[0]

    transition_rows.append({
        "core_row":
            int(r["core_row"]),

        "year":
            year,

        "car_number":
            r["car_number"],

        "driver_name":
            r["driver_name"],

        "delta_speed_mph":
            r["delta_speed_final_core_mph"],

        "residual_loyo_centered":
            r["residual_loyo_centered"],

        "before_attempt_id":
            rec["before_attempt_id"],

        "after_attempt_id":
            rec["after_attempt_id"],

        "linkage_source":
            "recovered_strong",

        "linkage_status":
            "linked",
    })

transition_map = pd.DataFrame(transition_rows)

if transition_map["core_row"].duplicated().any():
    raise RuntimeError(
        "Duplicate final-core rows in transition map."
    )

transition_map = transition_map.sort_values(
    "core_row"
).reset_index(drop=True)

print()
print("TRANSITION LINKAGE")
print("-" * 100)
print(
    f"linked transitions: {len(transition_map)}/41"
)

print(
    transition_map["linkage_source"]
    .value_counts()
    .to_string()
)

# =============================================================================
# AGGREGATE EACH ATTEMPT TO FOUR-LAP MEAN SECTION SPEED
#
# Sections remain repeated measurements within an attempt.
# They are NOT treated as independent training observations.
# =============================================================================

sections["section_speed_mph"] = pd.to_numeric(
    sections["section_speed_mph"],
    errors="coerce"
)

sections["lap_number"] = pd.to_numeric(
    sections["lap_number"],
    errors="coerce"
)

valid_sections = sections[
    sections["section_speed_mph"].notna()
    &
    sections["lap_number"].between(1, 4)
].copy()

attempt_section = (
    valid_sections
    .groupby(
        [
            "attempt_id",
            "section_name",
        ],
        as_index=False
    )
    .agg(
        mean_section_speed_mph=(
            "section_speed_mph",
            "mean"
        ),
        section_speed_sd_mph=(
            "section_speed_mph",
            "std"
        ),
        n_laps=(
            "lap_number",
            "nunique"
        ),
    )
)

# Require all four laps for a section-level comparison.
attempt_section = attempt_section[
    attempt_section["n_laps"] == 4
].copy()

# =============================================================================
# BUILD BEFORE / AFTER SECTION CHANGES
# =============================================================================

long_rows = []

for _, tr in transition_map.iterrows():

    before = attempt_section[
        attempt_section["attempt_id"]
        == tr["before_attempt_id"]
    ].copy()

    after = attempt_section[
        attempt_section["attempt_id"]
        == tr["after_attempt_id"]
    ].copy()

    pair = before.merge(
        after,
        on="section_name",
        how="inner",
        suffixes=("_before", "_after"),
    )

    for _, s in pair.iterrows():

        delta_section = (
            s["mean_section_speed_mph_after"]
            -
            s["mean_section_speed_mph_before"]
        )

        long_rows.append({
            "core_row":
                tr["core_row"],

            "year":
                tr["year"],

            "car_number":
                tr["car_number"],

            "driver_name":
                tr["driver_name"],

            "delta_four_lap_average_speed_mph":
                tr["delta_speed_mph"],

            "residual_loyo_centered":
                tr["residual_loyo_centered"],

            "before_attempt_id":
                tr["before_attempt_id"],

            "after_attempt_id":
                tr["after_attempt_id"],

            "section_name":
                s["section_name"],

            "before_mean_section_speed_mph":
                s["mean_section_speed_mph_before"],

            "after_mean_section_speed_mph":
                s["mean_section_speed_mph_after"],

            "delta_section_speed_mph":
                delta_section,
        })

section_long = pd.DataFrame(long_rows)

# =============================================================================
# TRANSITION-LEVEL DESCRIPTIVE METRICS
# =============================================================================

metric_rows = []

for core_row, g in section_long.groupby("core_row"):

    meta = transition_map[
        transition_map["core_row"] == core_row
    ].iloc[0]

    overall_delta = float(
        meta["delta_speed_mph"]
    )

    section_delta = (
        g["delta_section_speed_mph"]
        .dropna()
        .to_numpy()
    )

    n = len(section_delta)

    if n == 0:
        continue

    # Direction coherence relative to overall 4-lap result.
    if overall_delta > 0:
        same_direction = section_delta > 0
    elif overall_delta < 0:
        same_direction = section_delta < 0
    else:
        same_direction = np.zeros(
            n,
            dtype=bool
        )

    direction_coherence = (
        float(np.mean(same_direction))
        if overall_delta != 0
        else np.nan
    )

    positive_fraction = float(
        np.mean(section_delta > 0)
    )

    negative_fraction = float(
        np.mean(section_delta < 0)
    )

    abs_delta = np.abs(section_delta)

    total_abs = float(
        np.sum(abs_delta)
    )

    max_abs_share = (
        float(np.max(abs_delta) / total_abs)
        if total_abs > 0
        else np.nan
    )

    metric_rows.append({
        "core_row":
            core_row,

        "year":
            meta["year"],

        "car_number":
            meta["car_number"],

        "driver_name":
            meta["driver_name"],

        "delta_four_lap_average_speed_mph":
            overall_delta,

        "residual_loyo_centered":
            meta["residual_loyo_centered"],

        "abs_residual_loyo_centered":
            abs(
                float(
                    meta["residual_loyo_centered"]
                )
            ),

        "n_common_complete_sections":
            n,

        "mean_delta_section_speed_mph":
            float(
                np.mean(section_delta)
            ),

        "median_delta_section_speed_mph":
            float(
                np.median(section_delta)
            ),

        "sd_delta_section_speed_mph":
            float(
                np.std(
                    section_delta,
                    ddof=1
                )
            )
            if n > 1
            else np.nan,

        "min_delta_section_speed_mph":
            float(
                np.min(section_delta)
            ),

        "max_delta_section_speed_mph":
            float(
                np.max(section_delta)
            ),

        "positive_section_fraction":
            positive_fraction,

        "negative_section_fraction":
            negative_fraction,

        "direction_coherence":
            direction_coherence,

        "max_abs_section_change_share":
            max_abs_share,
    })

mechanism = pd.DataFrame(metric_rows)

# =============================================================================
# SAVE
# =============================================================================

transition_map.to_csv(
    OUT_TRANSITIONS,
    index=False
)

section_long.to_csv(
    OUT_SECTION_LONG,
    index=False
)

mechanism.to_csv(
    OUT_MECHANISM,
    index=False
)

# =============================================================================
# DESCRIPTIVE SUMMARY
# =============================================================================

lines = []

def add(x=""):
    lines.append(str(x))


add("=" * 100)
add(
    "INDY 500 V2-B SECTION MECHANISM DESCRIPTIVE SUMMARY"
)
add("=" * 100)

add()
add("LINKAGE")
add(
    f"final physics core: 41"
)
add(
    f"transition identities linked: {len(transition_map)}/41"
)
add(
    f"transitions with usable common complete sections: "
    f"{len(mechanism)}/{len(transition_map)}"
)

add()
add("COMMON COMPLETE SECTION COUNT")
add(
    mechanism[
        "n_common_complete_sections"
    ]
    .value_counts()
    .sort_index()
    .to_string()
)

add()
add("DIRECTION COHERENCE")
add(
    mechanism[
        "direction_coherence"
    ]
    .describe(
        percentiles=[
            0.10,
            0.25,
            0.50,
            0.75,
            0.90,
        ]
    )
    .to_string()
)

add()
add("SECTION CHANGE DISPERSION")
add(
    mechanism[
        "sd_delta_section_speed_mph"
    ]
    .describe(
        percentiles=[
            0.10,
            0.25,
            0.50,
            0.75,
            0.90,
        ]
    )
    .to_string()
)

add()
add("MAX ABSOLUTE SECTION-CHANGE SHARE")
add(
    mechanism[
        "max_abs_section_change_share"
    ]
    .describe(
        percentiles=[
            0.10,
            0.25,
            0.50,
            0.75,
            0.90,
        ]
    )
    .to_string()
)

add()
add("ABSOLUTE PHYSICS RESIDUAL")
add(
    mechanism[
        "abs_residual_loyo_centered"
    ]
    .describe(
        percentiles=[
            0.10,
            0.25,
            0.50,
            0.75,
            0.90,
        ]
    )
    .to_string()
)

add()
add("LOWEST DIRECTION COHERENCE CASES")
add(
    mechanism.sort_values(
        [
            "direction_coherence",
            "abs_residual_loyo_centered",
        ],
        ascending=[
            True,
            False,
        ]
    )
    [
        [
            "year",
            "car_number",
            "driver_name",
            "delta_four_lap_average_speed_mph",
            "direction_coherence",
            "sd_delta_section_speed_mph",
            "max_abs_section_change_share",
            "abs_residual_loyo_centered",
        ]
    ]
    .head(10)
    .to_string(
        index=False
    )
)

add()
add("HIGHEST ABSOLUTE PHYSICS RESIDUAL CASES")
add(
    mechanism.sort_values(
        "abs_residual_loyo_centered",
        ascending=False
    )
    [
        [
            "year",
            "car_number",
            "driver_name",
            "delta_four_lap_average_speed_mph",
            "direction_coherence",
            "sd_delta_section_speed_mph",
            "max_abs_section_change_share",
            "abs_residual_loyo_centered",
        ]
    ]
    .head(10)
    .to_string(
        index=False
    )
)

summary = "\n".join(lines)

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

print(OUT_TRANSITIONS)
print(OUT_SECTION_LONG)
print(OUT_MECHANISM)
print(OUT_SUMMARY)

print()
print("IMPORTANT:")
print(
    "No mechanism classes or thresholds were imposed in this step."
)
print(
    "Sections were used only as within-transition mechanism evidence, "
    "not as independent model-training rows."
)
print()
print("DONE")
