from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path("/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈")
OUT = ROOT / "r5_2/manual"

PTSC_FILE = ROOT / "weather/evidence/ptsc/indy500_day1_track_temp_2020_2024_time_normalized.csv"
HRRR_FILE = ROOT / "weather/output/hrrr_ims_2020_2024_features.csv"

ptsc = pd.read_csv(PTSC_FILE)
hrrr = pd.read_csv(HRRR_FILE)

# ============================================================
# normalize
# ============================================================

ptsc["time_utc"] = pd.to_datetime(
    ptsc["utc_datetime"],
    utc=True,
    errors="coerce"
)

hrrr["time_utc"] = pd.to_datetime(
    hrrr["valid_time_utc"],
    utc=True,
    errors="coerce"
)

ptsc["year"] = pd.to_numeric(
    ptsc["year"],
    errors="coerce"
)

for c in [
    "track_c",
    "ambient_c",
    "humidity",
    "pressure",
]:
    ptsc[c] = pd.to_numeric(
        ptsc[c],
        errors="coerce"
    )

for c in [
    "temp_c",
    "dewpoint_c",
    "relative_humidity_pct",
    "wind_speed_10m_ms",
    "gust_ms",
    "cloud_cover_pct",
    "shortwave_radiation_wm2",
    "pressure_hpa",
    "forecast_lead_hours",
]:
    hrrr[c] = pd.to_numeric(
        hrrr[c],
        errors="coerce"
    )

# Prefer shortest forecast lead for duplicated valid times
hrrr = (
    hrrr.sort_values(
        ["time_utc", "forecast_lead_hours"]
    )
    .drop_duplicates(
        "time_utc",
        keep="first"
    )
)

# ============================================================
# attach nearest HRRR to every PTSC observation
# ============================================================

rows = []

for _, r in ptsc.iterrows():

    if pd.isna(r["time_utc"]):
        continue

    H = hrrr[hrrr["time_utc"].notna()].copy()

    H["_dist_min"] = (
        H["time_utc"] - r["time_utc"]
    ).abs().dt.total_seconds() / 60.0

    if H.empty:
        continue

    best = H.sort_values("_dist_min").iloc[0]

    row = r.to_dict()

    row["hrrr_match_time_utc"] = best["time_utc"]
    row["hrrr_offset_min"] = best["_dist_min"]

    for c in [
        "temp_c",
        "dewpoint_c",
        "relative_humidity_pct",
        "wind_speed_10m_ms",
        "gust_ms",
        "cloud_cover_pct",
        "shortwave_radiation_wm2",
        "pressure_hpa",
    ]:
        row["hrrr_" + c] = best[c]

    rows.append(row)

state = pd.DataFrame(rows)

# Keep reasonable hourly HRRR alignment
state = state[
    state["hrrr_offset_min"] <= 35
].copy()

state = state.sort_values(
    ["year", "time_utc"]
).reset_index(drop=True)

print("=" * 150)
print("PART 1 — TRACK STATE PANEL")
print("=" * 150)

print("PTSC raw rows =", len(ptsc))
print("PTSC + HRRR rows =", len(state))

print("\nBY YEAR:")
print(
    state.groupby("year")
    .size()
    .to_string()
)

print("\nHRRR OFFSET:")
print(
    state["hrrr_offset_min"]
    .describe()
    .round(3)
    .to_string()
)

# ============================================================
# construct future-state transitions
#
# target horizons:
# 15 / 30 / 45 / 60 min
#
# accept nearest future PTSC observation within ±8 min
# ============================================================

TARGET_HORIZONS = [15, 30, 45, 60]
TOLERANCE_MIN = 8

pairs = []

for year, g in state.groupby("year"):

    g = g.sort_values("time_utc").reset_index(drop=True)

    for i, cur in g.iterrows():

        for horizon in TARGET_HORIZONS:

            target_time = (
                cur["time_utc"]
                + pd.Timedelta(minutes=horizon)
            )

            future = g[
                g["time_utc"] > cur["time_utc"]
            ].copy()

            if future.empty:
                continue

            future["_target_error_min"] = (
                future["time_utc"] - target_time
            ).abs().dt.total_seconds() / 60.0

            nxt = future.sort_values(
                "_target_error_min"
            ).iloc[0]

            if nxt["_target_error_min"] > TOLERANCE_MIN:
                continue

            row = {
                "year": int(year),

                "current_time_utc":
                    cur["time_utc"],

                "future_time_utc":
                    nxt["time_utc"],

                "requested_horizon_min":
                    horizon,

                "actual_horizon_min":
                    (
                        nxt["time_utc"]
                        -
                        cur["time_utc"]
                    ).total_seconds() / 60.0,

                "target_time_error_min":
                    nxt["_target_error_min"],

                "current_track_temp_c":
                    cur["track_c"],

                "future_track_temp_c":
                    nxt["track_c"],

                "delta_track_temp_c":
                    nxt["track_c"] - cur["track_c"],

                "current_ambient_temp_c":
                    cur["hrrr_temp_c"],

                "future_ambient_temp_c":
                    nxt["hrrr_temp_c"],

                "delta_ambient_temp_c":
                    nxt["hrrr_temp_c"]
                    -
                    cur["hrrr_temp_c"],

                "current_shortwave_wm2":
                    cur["hrrr_shortwave_radiation_wm2"],

                "future_shortwave_wm2":
                    nxt["hrrr_shortwave_radiation_wm2"],

                "delta_shortwave_wm2":
                    nxt["hrrr_shortwave_radiation_wm2"]
                    -
                    cur["hrrr_shortwave_radiation_wm2"],

                "current_cloud_pct":
                    cur["hrrr_cloud_cover_pct"],

                "future_cloud_pct":
                    nxt["hrrr_cloud_cover_pct"],

                "delta_cloud_pct":
                    nxt["hrrr_cloud_cover_pct"]
                    -
                    cur["hrrr_cloud_cover_pct"],

                "current_wind_ms":
                    cur["hrrr_wind_speed_10m_ms"],

                "future_wind_ms":
                    nxt["hrrr_wind_speed_10m_ms"],

                "delta_wind_ms":
                    nxt["hrrr_wind_speed_10m_ms"]
                    -
                    cur["hrrr_wind_speed_10m_ms"],

                "current_gust_ms":
                    cur["hrrr_gust_ms"],

                "future_gust_ms":
                    nxt["hrrr_gust_ms"],

                "delta_gust_ms":
                    nxt["hrrr_gust_ms"]
                    -
                    cur["hrrr_gust_ms"],
            }

            pairs.append(row)

panel = pd.DataFrame(pairs)

# remove accidental duplicate current/future/horizon rows
panel = panel.drop_duplicates(
    subset=[
        "year",
        "current_time_utc",
        "future_time_utc",
        "requested_horizon_min",
    ]
)

print("\n" + "=" * 150)
print("PART 2 — FUTURE TRACK-TEMPERATURE TRANSITION PANEL")
print("=" * 150)

print("TOTAL PAIRS =", len(panel))

print("\nBY HORIZON:")
print(
    panel.groupby("requested_horizon_min")
    .size()
    .to_string()
)

print("\nBY YEAR:")
print(
    panel.groupby("year")
    .size()
    .to_string()
)

print("\nBY YEAR / HORIZON:")
print(
    pd.crosstab(
        panel["year"],
        panel["requested_horizon_min"]
    ).to_string()
)

print("\nΔTRACK TEMP SUMMARY:")
print(
    panel.groupby(
        "requested_horizon_min"
    )["delta_track_temp_c"]
    .agg([
        "count",
        "mean",
        "median",
        "std",
        "min",
        "max",
    ])
    .round(4)
    .to_string()
)

# ============================================================
# simple directional diagnostics
# ============================================================

print("\n" + "=" * 150)
print("PART 3 — TRACK-TEMPERATURE DRIVER DIAGNOSTICS")
print("=" * 150)

features = [
    "current_track_temp_c",
    "current_ambient_temp_c",
    "delta_ambient_temp_c",
    "current_shortwave_wm2",
    "delta_shortwave_wm2",
    "current_cloud_pct",
    "delta_cloud_pct",
    "current_wind_ms",
    "delta_wind_ms",
]

for f in features:

    z = panel[
        ["delta_track_temp_c", f]
    ].dropna()

    if len(z) < 10:
        continue

    pear = z[f].corr(
        z["delta_track_temp_c"]
    )

    spear = z[f].corr(
        z["delta_track_temp_c"],
        method="spearman"
    )

    print(
        f"{f:30s}",
        "N =", len(z),
        "Pearson =", round(pear, 5),
        "Spearman =", round(spear, 5)
    )

# ============================================================
# save
# ============================================================

STATE_OUT = (
    OUT /
    "track_temperature_state_panel_v1.csv"
)

PAIR_OUT = (
    OUT /
    "track_temperature_future_transition_panel_v1.csv"
)

state.to_csv(
    STATE_OUT,
    index=False
)

panel.to_csv(
    PAIR_OUT,
    index=False
)

print("\n" + "=" * 150)
print("OUTPUTS")
print("=" * 150)

print(STATE_OUT.relative_to(ROOT))
print(PAIR_OUT.relative_to(ROOT))

print(
    "\nTRACK_TEMPERATURE_TRANSITION_PANEL_V1_COMPLETE"
)
