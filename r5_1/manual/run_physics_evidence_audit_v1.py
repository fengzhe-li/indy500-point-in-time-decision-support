from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path("/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈")
OUT = ROOT / "r5_1/manual"
OUT.mkdir(parents=True, exist_ok=True)

FILES = {
    "first_run": ROOT / "r5_1/output/day1_first_run_field_sweep_v1.csv",
    "fade": ROOT / "r5_1/output/day1_within_run_fade_physics_v1.csv",
    "repeat": ROOT / "r5_1/output/day1_same_car_repeat_inventory_v1.csv",
    "ff_inventory": ROOT / "r5_1/output/fast_friday_baseline_candidate_inventory_v1.csv",
    "ff_coverage": ROOT / "r5_1/output/fast_friday_baseline_coverage_report_v1.csv",
}

# ------------------------------------------------------------
# helpers
# ------------------------------------------------------------

def load(name):
    p = FILES[name]
    if not p.exists():
        print(f"\nMISSING FILE: {p.relative_to(ROOT)}")
        return None
    df = pd.read_csv(p)
    print(f"\nLOADED {name}: {len(df)} rows")
    return df

def find_col(df, candidates):
    if df is None:
        return None

    exact = {c.lower(): c for c in df.columns}

    for c in candidates:
        if c.lower() in exact:
            return exact[c.lower()]

    # relaxed substring matching
    for c in candidates:
        cl = c.lower()
        for real in df.columns:
            if cl in real.lower():
                return real

    return None

def numeric(df, col):
    if col is None:
        return None
    return pd.to_numeric(df[col], errors="coerce")

def assoc_table(df, target_candidates, feature_groups, title):
    print("\n" + "=" * 150)
    print(title)
    print("=" * 150)

    if df is None:
        return

    target = find_col(df, target_candidates)

    if target is None:
        print("TARGET NOT FOUND")
        print("AVAILABLE COLUMNS:")
        print("\n".join(df.columns))
        return

    y = numeric(df, target)

    print("TARGET:", target)
    print("TARGET N:", int(y.notna().sum()))

    rows = []

    for label, candidates in feature_groups.items():
        col = find_col(df, candidates)

        if col is None:
            rows.append({
                "feature": label,
                "column": "NOT_FOUND",
                "n": 0,
                "pearson": np.nan,
                "spearman": np.nan,
                "slope": np.nan,
                "intercept": np.nan,
            })
            continue

        x = numeric(df, col)
        mask = x.notna() & y.notna()

        n = int(mask.sum())

        if n < 5:
            rows.append({
                "feature": label,
                "column": col,
                "n": n,
                "pearson": np.nan,
                "spearman": np.nan,
                "slope": np.nan,
                "intercept": np.nan,
            })
            continue

        xx = x[mask]
        yy = y[mask]

        pearson = xx.corr(yy, method="pearson")
        spearman = xx.corr(yy, method="spearman")

        # descriptive one-variable least squares only
        slope, intercept = np.polyfit(xx, yy, 1)

        rows.append({
            "feature": label,
            "column": col,
            "n": n,
            "pearson": pearson,
            "spearman": spearman,
            "slope": slope,
            "intercept": intercept,
        })

    res = pd.DataFrame(rows)

    print(
        res.sort_values(
            "spearman",
            key=lambda s: s.abs(),
            ascending=False,
            na_position="last"
        ).round(5).to_string(index=False)
    )

    return res

def print_year_counts(df, title):
    if df is None:
        return

    year = find_col(df, ["year"])

    print("\n" + title)

    if year is None:
        print("NO YEAR COLUMN")
        return

    print(df[year].value_counts(dropna=False).sort_index().to_string())

# ------------------------------------------------------------
# load
# ------------------------------------------------------------

first = load("first_run")
fade = load("fade")
repeat = load("repeat")
ffi = load("ff_inventory")
ffc = load("ff_coverage")

# ------------------------------------------------------------
# A. basic counts
# ------------------------------------------------------------

print("\n" + "#" * 150)
print("A. BASIC COVERAGE")
print("#" * 150)

print_year_counts(first, "FIRST RUN BY YEAR")
print_year_counts(fade, "FADE BY YEAR")
print_year_counts(repeat, "REPEAT BY YEAR")

if ffc is not None:
    print("\nFAST FRIDAY COVERAGE REPORT:")
    print(ffc.to_string(index=False))

# ------------------------------------------------------------
# B. Fast Friday ambiguity audit
# ------------------------------------------------------------

print("\n" + "#" * 150)
print("B. FAST FRIDAY AMBIGUITY")
print("#" * 150)

if ffi is not None:
    amb_col = find_col(
        ffi,
        [
            "ambiguity_reason",
            "baseline_quality",
            "qualifying_simulation_indicator",
        ],
    )

    if amb_col:
        vals = ffi[amb_col].fillna("").astype(str)
        bad = ffi[
            vals.str.len().gt(0)
            & ~vals.str.lower().isin(
                ["high", "good", "yes", "true", "1", "confirmed"]
            )
        ]

        print("POTENTIALLY AMBIGUOUS ROWS:", len(bad))

        show_cols = [
            c for c in [
                find_col(ffi, ["year"]),
                find_col(ffi, ["car_number"]),
                find_col(ffi, ["driver_name"]),
                find_col(ffi, ["four_lap_average_mph"]),
                find_col(ffi, ["baseline_quality"]),
                find_col(ffi, ["ambiguity_reason"]),
                find_col(ffi, ["source_path"]),
            ]
            if c
        ]

        if len(bad):
            print(bad[show_cols].head(80).to_string(index=False))

# ------------------------------------------------------------
# physical feature aliases
# ------------------------------------------------------------

PHYSICAL = {
    "track_temp": [
        "track_temperature",
        "track_temp_c",
        "track_temp",
        "ptsc",
    ],
    "track_temp_trend": [
        "track_temperature_trend",
        "track_temp_slope",
        "track_temp_trend",
    ],
    "air_temp": [
        "air_temperature",
        "air_temp_c",
        "air_temp",
        "tmp_c",
    ],
    "dewpoint": [
        "dew_point",
        "dewpoint",
        "dpt_c",
    ],
    "humidity": [
        "humidity",
        "relative_humidity",
        "rh",
    ],
    "pressure": [
        "pressure",
        "pressure_hpa",
        "pres",
    ],
    "air_density": [
        "air_density",
        "density",
        "rho",
    ],
    "wind_speed": [
        "wind_speed",
        "wind_speed_mps",
    ],
    "wind_gust": [
        "gust",
        "wind_gust",
    ],
    "wind_u": [
        "wind_u",
        "u_wind",
    ],
    "wind_v": [
        "wind_v",
        "v_wind",
    ],
    "solar_elevation": [
        "solar_elevation",
    ],
    "shortwave": [
        "shortwave",
        "dswrf",
        "solar_radiation",
    ],
    "cloud": [
        "cloud_cover",
        "tcdc",
        "cloud",
    ],
}

DELTA_PHYSICAL = {
    "delta_track_temp": [
        "delta_track_temp",
        "track_temp_delta",
        "delta_track_temperature",
    ],
    "delta_air_temp": [
        "delta_air_temp",
        "air_temp_delta",
    ],
    "delta_dewpoint": [
        "delta_dew",
        "dewpoint_delta",
    ],
    "delta_humidity": [
        "delta_humidity",
        "humidity_delta",
    ],
    "delta_pressure": [
        "delta_pressure",
        "pressure_delta",
    ],
    "delta_air_density": [
        "delta_air_density",
        "air_density_delta",
        "delta_density",
    ],
    "delta_wind_speed": [
        "delta_wind_speed",
        "wind_speed_delta",
    ],
    "delta_gust": [
        "delta_gust",
        "gust_delta",
    ],
    "delta_wind_u": [
        "delta_wind_u",
        "wind_u_delta",
    ],
    "delta_wind_v": [
        "delta_wind_v",
        "wind_v_delta",
    ],
    "delta_shortwave": [
        "delta_shortwave",
        "shortwave_delta",
        "delta_dswrf",
    ],
    "delta_cloud": [
        "delta_cloud",
        "cloud_delta",
    ],
}

# ------------------------------------------------------------
# C. Day1 first-run sweep
# ------------------------------------------------------------

first_assoc = assoc_table(
    first,
    [
        "day1_minus_own_fast_friday_baseline",
        "day1_minus_fast_friday",
        "relative_performance",
        "baseline_delta_mph",
    ],
    PHYSICAL,
    "C. DAY1 FIRST RUN: PERFORMANCE RELATIVE TO OWN FAST FRIDAY BASELINE",
)

if first_assoc is not None:
    first_assoc.to_csv(
        OUT / "first_run_physical_associations_v1.csv",
        index=False
    )

# ------------------------------------------------------------
# D. within-run fade
# time-based fade:
# positive Lap4-Lap1 = worsening
# ------------------------------------------------------------

fade_assoc = assoc_table(
    fade,
    [
        "lap4_minus_lap1",
        "lap4_s_minus_lap1_s",
        "lap1_to_lap4_delta",
    ],
    PHYSICAL,
    "D. WITHIN-RUN FADE: LAP4 - LAP1 (TIME DOMAIN)",
)

if fade_assoc is not None:
    fade_assoc.to_csv(
        OUT / "fade_physical_associations_v1.csv",
        index=False
    )

# ------------------------------------------------------------
# E. same-car repeat
# delta speed positive = second/later run faster
# ------------------------------------------------------------

repeat_assoc = assoc_table(
    repeat,
    [
        "delta_speed",
        "delta_speed_mph",
        "speed_delta_mph",
        "next_minus_previous_speed",
    ],
    DELTA_PHYSICAL,
    "E. SAME-CAR REPEAT: DELTA PHYSICAL STATE -> DELTA SPEED",
)

if repeat_assoc is not None:
    repeat_assoc.to_csv(
        OUT / "repeat_physical_associations_v1.csv",
        index=False
    )

# ------------------------------------------------------------
# F. repeat availability / frozen 39 / 40 audit
# ------------------------------------------------------------

print("\n" + "#" * 150)
print("F. REPEAT ENVIRONMENT COVERAGE")
print("#" * 150)

if repeat is not None:

    print("TOTAL REPEAT ROWS:", len(repeat))

    membership = find_col(
        repeat,
        [
            "in_frozen_39",
            "frozen_39_membership",
            "is_in_frozen_39",
        ],
    )

    if membership:
        print("\nFROZEN 39 MEMBERSHIP:")
        print(repeat[membership].value_counts(dropna=False).to_string())

    quality = find_col(
        repeat,
        [
            "physical_link_quality",
            "environment_link_quality",
            "physical_quality",
        ],
    )

    if quality:
        print("\nPHYSICAL LINK QUALITY:")
        print(repeat[quality].value_counts(dropna=False).to_string())

    exclusion = find_col(
        repeat,
        [
            "exclusion_reason",
            "environment_exclusion_reason",
        ],
    )

    if exclusion:
        print("\nTOP EXCLUSION REASONS:")
        print(
            repeat[exclusion]
            .fillna("NA")
            .value_counts(dropna=False)
            .head(20)
            .to_string()
        )

# ------------------------------------------------------------
# G. missingness of physical variables by year
# ------------------------------------------------------------

print("\n" + "#" * 150)
print("G. PHYSICAL VARIABLE COVERAGE BY YEAR")
print("#" * 150)

for name, df in [
    ("FIRST_RUN", first),
    ("FADE", fade),
    ("REPEAT", repeat),
]:
    if df is None:
        continue

    year = find_col(df, ["year"])

    print("\n---", name, "---")

    records = []

    feature_set = PHYSICAL if name != "REPEAT" else DELTA_PHYSICAL

    for label, candidates in feature_set.items():
        col = find_col(df, candidates)

        if col is None:
            records.append({
                "dataset": name,
                "year": "ALL",
                "feature": label,
                "column": "NOT_FOUND",
                "n_total": len(df),
                "n_available": 0,
                "coverage": 0,
            })
            continue

        x = pd.to_numeric(df[col], errors="coerce")

        if year:
            for yr, idx in df.groupby(year).groups.items():
                n_total = len(idx)
                n_avail = int(x.loc[idx].notna().sum())

                records.append({
                    "dataset": name,
                    "year": yr,
                    "feature": label,
                    "column": col,
                    "n_total": n_total,
                    "n_available": n_avail,
                    "coverage": n_avail / n_total if n_total else np.nan,
                })

    cov = pd.DataFrame(records)

    if len(cov):
        print(
            cov[
                ["year", "feature", "n_available", "n_total", "coverage"]
            ]
            .sort_values(["year", "feature"])
            .round(3)
            .to_string(index=False)
        )

        cov.to_csv(
            OUT / f"{name.lower()}_physical_coverage_v1.csv",
            index=False
        )

print("\n" + "=" * 150)
print("PHYSICS_EVIDENCE_AUDIT_V1_COMPLETE")
print("=" * 150)
