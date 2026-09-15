from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path("/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈")
OUT = ROOT / "r5_1/manual"
OUT.mkdir(parents=True, exist_ok=True)

FIRST = ROOT / "r5_1/output/day1_first_run_field_sweep_v1.csv"
FADE = ROOT / "r5_1/output/day1_within_run_fade_physics_v1.csv"
REPEAT = ROOT / "r5_1/output/day1_same_car_repeat_inventory_v1.csv"

first = pd.read_csv(FIRST)
fade = pd.read_csv(FADE)
repeat = pd.read_csv(REPEAT)

def num(s):
    return pd.to_numeric(s, errors="coerce")

def assoc(df, target, features, title):
    print("\n" + "=" * 145)
    print(title)
    print("=" * 145)

    if target not in df.columns:
        print("TARGET MISSING:", target)
        return pd.DataFrame()

    y = num(df[target])
    print("TARGET:", target)
    print("TARGET N:", int(y.notna().sum()))

    rows = []

    for label, col in features.items():
        if col not in df.columns:
            rows.append({
                "feature": label,
                "column": col,
                "n": 0,
                "pearson": np.nan,
                "spearman": np.nan,
                "slope": np.nan,
            })
            continue

        x = num(df[col])
        m = x.notna() & y.notna()
        n = int(m.sum())

        if n < 5:
            rows.append({
                "feature": label,
                "column": col,
                "n": n,
                "pearson": np.nan,
                "spearman": np.nan,
                "slope": np.nan,
            })
            continue

        xx = x[m]
        yy = y[m]

        slope, intercept = np.polyfit(xx, yy, 1)

        rows.append({
            "feature": label,
            "column": col,
            "n": n,
            "pearson": xx.corr(yy, method="pearson"),
            "spearman": xx.corr(yy, method="spearman"),
            "slope": slope,
        })

    out = pd.DataFrame(rows)

    if not out.empty:
        out = out.sort_values(
            "spearman",
            key=lambda s: s.abs(),
            ascending=False,
            na_position="last"
        )

        print(out.round(5).to_string(index=False))

    return out


# ============================================================
# A. FIRST RUN RELATIVE TO OWN FAST FRIDAY FOUR-LAP BASELINE
# Positive target = Day1 faster than own FF 4-lap baseline
# ============================================================

first_features = {
    "track_temp": "track_temperature",
    "track_temp_trend": "track_temperature_trend_c_per_min",
    "air_temp": "air_temperature_c",
    "dewpoint": "dew_point_c",
    "humidity": "humidity_pct",
    "pressure": "pressure_hpa",
    "air_density": "air_density_kg_m3",
    "wind_speed": "wind_speed_ms",
    "gust": "gust_ms",
    "wind_u": "wind_u_ms",
    "wind_v": "wind_v_ms",
    "solar_elevation": "solar_elevation_deg_assembled",
    "shortwave": "shortwave_radiation_wm2",
    "cloud": "cloud_cover_pct",
}

a = assoc(
    first,
    "day1_minus_own_fast_friday_four_lap_mph",
    first_features,
    "A. DAY1 FIRST COMPLETE RUN RELATIVE TO OWN FAST FRIDAY 4-LAP BASELINE"
)

a.to_csv(
    OUT / "first_run_relative_ff_associations_v2.csv",
    index=False
)


# ============================================================
# B. WITHIN-RUN FADE
#
# IMPORTANT:
# Confirmed from assembled schema / scale:
# target is SPEED-domain Lap4 - Lap1.
#
# More negative = larger loss of speed across the run.
# ============================================================

fade_features = {
    "track_temp": "track_temperature_c_assembled",
    "air_temp": "forecast_air_temperature_c",
    "dewpoint": "forecast_dewpoint_c",
    "humidity": "forecast_relative_humidity_pct",
    "pressure": "forecast_pressure_hpa",
    "air_density": "air_density_kg_m3",
    "wind_speed": "forecast_wind_speed_10m_ms",
    "gust": "forecast_gust_ms",
    "wind_u": "wind_u_ms",
    "wind_v": "wind_v_ms",
    "solar_elevation": "solar_elevation_deg_assembled",
    "shortwave": "forecast_shortwave_radiation_wm2",
    "cloud": "forecast_cloud_cover_pct",
}

# Find actual fade target safely
fade_target = None
for c in [
    "lap4_minus_lap1",
    "lap1_to_lap4_delta_mph",
    "lap4_minus_lap1_mph",
]:
    if c in fade.columns:
        fade_target = c
        break

print("\nFADE TARGET SELECTED:", fade_target)

b = assoc(
    fade,
    fade_target,
    fade_features,
    "B. WITHIN-RUN SPEED FADE: LAP4 SPEED - LAP1 SPEED (MORE NEGATIVE = MORE FADE)"
)

b.to_csv(
    OUT / "within_run_fade_associations_v2.csv",
    index=False
)


# ============================================================
# C. SAME-CAR REPEAT
#
# Positive target = later attempt faster than previous attempt.
# All physical predictors are AFTER - BEFORE.
# ============================================================

repeat_features = {
    "delta_track_temp": "delta_track_temp_c",
    "delta_air_temp": "delta_air_temp_c",
    "delta_dewpoint": "delta_dewpoint_c",
    "delta_humidity": "delta_relative_humidity_pct",
    "delta_pressure": "delta_pressure_hpa",
    "delta_air_density": "delta_air_density_kg_m3",
    "delta_wind_speed": "delta_wind_speed_ms",
    "delta_gust": "delta_gust_ms",
    "delta_wind_u": "delta_wind_u_ms",
    "delta_wind_v": "delta_wind_v_ms",
    "delta_solar_elevation": "delta_solar_elevation_deg",
    "delta_shortwave": "delta_shortwave_radiation_wm2",
    "delta_cloud": "delta_cloud_cover_pct",
}

c = assoc(
    repeat,
    "delta_four_lap_average_speed_mph",
    repeat_features,
    "C. SAME-CAR REPEAT: DELTA PHYSICAL STATE -> DELTA FOUR-LAP SPEED"
)

c.to_csv(
    OUT / "same_car_repeat_associations_v2.csv",
    index=False
)


# ============================================================
# D. REPEAT SUBSET COUNTS
# ============================================================

print("\n" + "=" * 145)
print("D. SAME-CAR REPEAT USABLE PHYSICAL SUBSETS")
print("=" * 145)

print("TOTAL:", len(repeat))

if "physical_link_quality" in repeat.columns:
    print("\nPHYSICAL LINK QUALITY:")
    print(repeat["physical_link_quality"].value_counts(dropna=False).to_string())

target = num(repeat["delta_four_lap_average_speed_mph"])

track = (
    num(repeat["delta_track_temp_c"])
    if "delta_track_temp_c" in repeat.columns
    else pd.Series(np.nan, index=repeat.index)
)

hrrr = (
    repeat["full_environment_pair_available"].astype(str).str.lower().isin(
        ["true", "1", "yes"]
    )
    if "full_environment_pair_available" in repeat.columns
    else pd.Series(False, index=repeat.index)
)

print("\nTARGET SPEED DELTA AVAILABLE:", int(target.notna().sum()))
print("TARGET + DELTA TRACK TEMP:", int((target.notna() & track.notna()).sum()))
print("TARGET + FULL ENVIRONMENT:", int((target.notna() & hrrr).sum()))

if "in_frozen_39" in repeat.columns:
    frozen = repeat["in_frozen_39"].astype(str).str.lower().isin(
        ["true", "1", "yes"]
    )
    print("TARGET + FROZEN 39:", int((target.notna() & frozen).sum()))

print("\n" + "=" * 145)
print("PHYSICS_CORE_ASSOCIATIONS_V2_COMPLETE")
print("=" * 145)
