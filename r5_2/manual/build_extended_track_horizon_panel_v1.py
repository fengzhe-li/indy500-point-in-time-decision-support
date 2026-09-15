from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path("/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈")
OUT = ROOT / "r5_2/manual"

STATE_FILE = OUT / "track_temperature_state_panel_v1.csv"

state = pd.read_csv(STATE_FILE)

state["time_utc"] = pd.to_datetime(
    state["time_utc"],
    utc=True,
    errors="coerce"
)

numeric_cols = [
    "year",
    "track_c",
    "hrrr_temp_c",
    "hrrr_shortwave_radiation_wm2",
    "hrrr_cloud_cover_pct",
    "hrrr_wind_speed_10m_ms",
    "hrrr_gust_ms",
]

for c in numeric_cols:
    state[c] = pd.to_numeric(
        state[c],
        errors="coerce"
    )

HORIZONS = [
    15, 30, 45, 60,
    90, 120, 150, 180
]

TOLERANCE_MIN = 8

rows = []

for year, g in state.groupby("year"):

    g = (
        g.sort_values("time_utc")
        .reset_index(drop=True)
    )

    for _, cur in g.iterrows():

        if pd.isna(cur["time_utc"]):
            continue

        for horizon in HORIZONS:

            target = (
                cur["time_utc"]
                + pd.Timedelta(minutes=horizon)
            )

            future = g[
                g["time_utc"] > cur["time_utc"]
            ].copy()

            if future.empty:
                continue

            future["_err"] = (
                future["time_utc"] - target
            ).abs().dt.total_seconds() / 60.0

            nxt = (
                future.sort_values("_err")
                .iloc[0]
            )

            if nxt["_err"] > TOLERANCE_MIN:
                continue

            rows.append({
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
                        - cur["time_utc"]
                    ).total_seconds() / 60.0,

                "target_error_min":
                    nxt["_err"],

                "current_track_temp_c":
                    cur["track_c"],

                "future_track_temp_c":
                    nxt["track_c"],

                "delta_track_temp_c":
                    nxt["track_c"]
                    - cur["track_c"],

                "current_ambient_temp_c":
                    cur["hrrr_temp_c"],

                "future_ambient_temp_c":
                    nxt["hrrr_temp_c"],

                "delta_ambient_temp_c":
                    nxt["hrrr_temp_c"]
                    - cur["hrrr_temp_c"],

                "current_shortwave_wm2":
                    cur["hrrr_shortwave_radiation_wm2"],

                "future_shortwave_wm2":
                    nxt["hrrr_shortwave_radiation_wm2"],

                "current_wind_ms":
                    cur["hrrr_wind_speed_10m_ms"],

                "future_wind_ms":
                    nxt["hrrr_wind_speed_10m_ms"],
            })

panel = pd.DataFrame(rows)

panel = panel.drop_duplicates(
    subset=[
        "year",
        "current_time_utc",
        "future_time_utc",
        "requested_horizon_min",
    ]
)

print("=" * 150)
print("PART 1 — EXTENDED HORIZON COVERAGE")
print("=" * 150)

print("TOTAL =", len(panel))

print("\nBY HORIZON:")
print(
    panel.groupby("requested_horizon_min")
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

print("\n" + "=" * 150)
print("PART 2 — DELTA TRACK TEMP BY HORIZON")
print("=" * 150)

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

OUTFILE = (
    OUT /
    "track_temperature_extended_horizon_panel_v1.csv"
)

panel.to_csv(
    OUTFILE,
    index=False
)

print("\nOUTPUT:")
print(OUTFILE.relative_to(ROOT))

print(
    "\nEXTENDED_TRACK_HORIZON_PANEL_V1_COMPLETE"
)
