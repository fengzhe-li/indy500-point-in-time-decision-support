from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path("/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈")
OUT = ROOT / "r5_2/manual"
OUT.mkdir(parents=True, exist_ok=True)

REPEAT = ROOT / "r5_1/output/day1_same_car_repeat_inventory_v1.csv"
HRRR = ROOT / "weather/output/hrrr_ims_2020_2024_features.csv"
PTSC = ROOT / "weather/evidence/ptsc/indy500_day1_track_temp_2020_2024_time_normalized.csv"

RESCUE_FILES = [
    ROOT / "r5_2/manual/repeat_attempt_time_rescue_2023_seed_v2.csv",
    ROOT / "r5_2/manual/repeat_time_rescue_2024_seed_v1.csv",
]

repeat = pd.read_csv(REPEAT)
hrrr = pd.read_csv(HRRR)
ptsc = pd.read_csv(PTSC)

# ============================================================
# NORMALIZE TIMES
# ============================================================

hrrr["_time"] = pd.to_datetime(
    hrrr["valid_time_utc"],
    utc=True,
    errors="coerce"
)

ptsc["_time"] = pd.to_datetime(
    ptsc["utc_datetime"],
    utc=True,
    errors="coerce"
)

# HRRR can contain several cycles verifying same valid time.
# Prefer shortest forecast lead.
hrrr["forecast_lead_hours"] = pd.to_numeric(
    hrrr["forecast_lead_hours"],
    errors="coerce"
)

hrrr = (
    hrrr.sort_values(
        ["_time", "forecast_lead_hours"],
        na_position="last"
    )
    .drop_duplicates("_time", keep="first")
)

# ============================================================
# LOAD RESCUE POINTS
# ============================================================

parts = []

for f in RESCUE_FILES:
    if not f.exists():
        continue

    d = pd.read_csv(f)

    if "time_utc" not in d.columns:
        continue

    d["_rescue_file"] = str(f.relative_to(ROOT))
    parts.append(d)

rescue = pd.concat(parts, ignore_index=True)

rescue["_time"] = pd.to_datetime(
    rescue["time_utc"],
    utc=True,
    errors="coerce"
)

rescue["speed_mph"] = pd.to_numeric(
    rescue["speed_mph"],
    errors="coerce"
)

rescue["year"] = pd.to_numeric(
    rescue["year"],
    errors="coerce"
).astype("Int64")

rescue["car_number"] = (
    rescue["car_number"]
    .astype(str)
    .str.replace(r"\.0$", "", regex=True)
)

# Remove rows without usable time
rescue = rescue[rescue["_time"].notna()].copy()

# ============================================================
# BUILD REPEAT ATTEMPT SPEED SEQUENCE
# ============================================================

seq_rows = []

for _, r in repeat.iterrows():

    year = int(r["year"])
    car = str(r["car_number"]).replace(".0", "")
    driver = r["driver_name"]

    before_speed = pd.to_numeric(
        r["before_four_lap_average_speed_mph"],
        errors="coerce"
    )
    after_speed = pd.to_numeric(
        r["after_four_lap_average_speed_mph"],
        errors="coerce"
    )

    br = pd.to_numeric(
        r.get("before_run_index"),
        errors="coerce"
    )
    ar = pd.to_numeric(
        r.get("after_run_index"),
        errors="coerce"
    )

    if pd.notna(before_speed):
        seq_rows.append({
            "year": year,
            "car_number": car,
            "driver_name": driver,
            "run_index": br,
            "speed_mph": before_speed,
        })

    if pd.notna(after_speed):
        seq_rows.append({
            "year": year,
            "car_number": car,
            "driver_name": driver,
            "run_index": ar,
            "speed_mph": after_speed,
        })

seq = pd.DataFrame(seq_rows)

seq = seq.drop_duplicates(
    subset=[
        "year",
        "car_number",
        "driver_name",
        "run_index",
        "speed_mph",
    ]
)

# ============================================================
# MATCH RESCUED SPEED TO RUN INDEX
# ============================================================

matched = []

for _, r in rescue.iterrows():

    cand = seq[
        (seq["year"] == int(r["year"])) &
        (seq["car_number"] == r["car_number"])
    ].copy()

    if cand.empty:
        matched.append({
            **r.to_dict(),
            "matched_run_index": np.nan,
            "speed_match_error_mph": np.nan,
            "sequence_match_status": "CAR_NOT_FOUND",
        })
        continue

    cand["err"] = (
        cand["speed_mph"] - r["speed_mph"]
    ).abs()

    best = cand.sort_values("err").iloc[0]

    err = float(best["err"])

    status = (
        "MATCHED"
        if err <= 0.005
        else "SPEED_NOT_MATCHED"
    )

    matched.append({
        **r.to_dict(),
        "matched_run_index": best["run_index"],
        "speed_match_error_mph": err,
        "sequence_match_status": status,
    })

m = pd.DataFrame(matched)

# ============================================================
# DETECT TIME / RUN ORDER CONTRADICTIONS
# ============================================================

m["chronology_status"] = "OK"

for (year, car), idx in m.groupby(
    ["year", "car_number"]
).groups.items():

    g = m.loc[idx].copy()

    g = g[
        (g["sequence_match_status"] == "MATCHED") &
        g["matched_run_index"].notna()
    ]

    if len(g) < 2:
        continue

    by_time = g.sort_values("_time")

    run_order = by_time["matched_run_index"].to_numpy(float)

    # rescued chronological order must not imply decreasing run index
    if np.any(np.diff(run_order) < 0):
        m.loc[g.index, "chronology_status"] = (
            "QUARANTINE_ORDER_CONFLICT"
        )

# ============================================================
# NEAREST HRRR
#
# Hourly forecast valid-time:
# max 35 min so rounding/near-hour matching remains reasonable.
# ============================================================

HRRR_MAX_MIN = 35

hrrr_cols = [
    "temp_c",
    "dewpoint_c",
    "relative_humidity_pct",
    "wind_speed_10m_ms",
    "wind_direction_deg",
    "pressure_hpa",
    "gust_ms",
    "cloud_cover_pct",
    "shortwave_radiation_wm2",
    "forecast_lead_hours",
]

# ============================================================
# NEAREST PTSC
#
# Do not assume dense observations.
# Store distance and only accept <= 20 min as primary rescued PTSC.
# ============================================================

PTSC_MAX_MIN = 20

ptsc_cols = [
    "ambient_c",
    "track_c",
    "humidity",
    "wind",
    "wind_direction",
    "pressure",
    "sensor_avg_f",
]

joined = []

for _, r in m.iterrows():

    row = r.to_dict()

    t = r["_time"]

    # ---------------- HRRR ----------------
    H = hrrr[hrrr["_time"].notna()].copy()

    H["_dist"] = (
        H["_time"] - t
    ).abs().dt.total_seconds() / 60

    if not H.empty:
        hb = H.sort_values("_dist").iloc[0]
        hdist = float(hb["_dist"])

        row["hrrr_match_time_utc"] = hb["_time"].isoformat()
        row["hrrr_time_distance_min"] = hdist

        row["hrrr_match_status"] = (
            "ACCEPT"
            if hdist <= HRRR_MAX_MIN
            else "TOO_FAR"
        )

        for c in hrrr_cols:
            row["hrrr_" + c] = hb.get(c, np.nan)

    # ---------------- PTSC ----------------
    P = ptsc[
        (pd.to_numeric(ptsc["year"], errors="coerce") == int(r["year"])) &
        ptsc["_time"].notna()
    ].copy()

    if not P.empty:

        P["_dist"] = (
            P["_time"] - t
        ).abs().dt.total_seconds() / 60

        pb = P.sort_values("_dist").iloc[0]
        pdist = float(pb["_dist"])

        row["ptsc_match_time_utc"] = pb["_time"].isoformat()
        row["ptsc_time_distance_min"] = pdist

        row["ptsc_match_status"] = (
            "ACCEPT"
            if pdist <= PTSC_MAX_MIN
            else "TOO_FAR"
        )

        for c in ptsc_cols:
            row["ptsc_" + c] = pb.get(c, np.nan)

    joined.append(row)

attempt_env = pd.DataFrame(joined)

# ============================================================
# DERIVE AIR DENSITY
# ============================================================

def moist_air_density(temp_c, dew_c, pressure_hpa):
    try:
        T = float(temp_c) + 273.15
        Td = float(dew_c)
        p = float(pressure_hpa) * 100.0
    except:
        return np.nan

    # Magnus vapor pressure
    e_hpa = 6.112 * np.exp(
        (17.67 * Td) / (Td + 243.5)
    )

    e = e_hpa * 100.0
    pdry = p - e

    Rd = 287.05
    Rv = 461.495

    return pdry / (Rd * T) + e / (Rv * T)


attempt_env["hrrr_air_density_kg_m3"] = attempt_env.apply(
    lambda r: moist_air_density(
        r.get("hrrr_temp_c"),
        r.get("hrrr_dewpoint_c"),
        r.get("hrrr_pressure_hpa"),
    ),
    axis=1
)

# ============================================================
# USABILITY
# ============================================================

attempt_env["rescue_environment_status"] = "NOT_MODEL_READY"

good = (
    attempt_env["sequence_match_status"].eq("MATCHED") &
    attempt_env["chronology_status"].eq("OK") &
    attempt_env["hrrr_match_status"].eq("ACCEPT")
)

attempt_env.loc[
    good,
    "rescue_environment_status"
] = "HRRR_READY"

if "ptsc_match_status" in attempt_env.columns:
    full = good & attempt_env["ptsc_match_status"].eq("ACCEPT")

    attempt_env.loc[
        full,
        "rescue_environment_status"
    ] = "FULL_ENV_READY"

# ============================================================
# BUILD COMPLETE RESCUED TRANSITIONS
# ============================================================

transition_rows = []

for (year, car), g in attempt_env.groupby(
    ["year", "car_number"]
):

    g = g[
        g["chronology_status"].eq("OK") &
        g["sequence_match_status"].eq("MATCHED")
    ].copy()

    if len(g) < 2:
        continue

    g = g.sort_values("matched_run_index")

    for i in range(len(g) - 1):

        a = g.iloc[i]
        b = g.iloc[i + 1]

        ra = a["matched_run_index"]
        rb = b["matched_run_index"]

        if pd.isna(ra) or pd.isna(rb):
            continue

        # Require consecutive observed run indices
        if rb != ra + 1:
            continue

        row = {
            "year": year,
            "car_number": car,
            "driver_name": a["driver_name"],

            "before_run_index": ra,
            "after_run_index": rb,

            "before_speed_mph": a["speed_mph"],
            "after_speed_mph": b["speed_mph"],

            "delta_speed_mph":
                b["speed_mph"] - a["speed_mph"],

            "before_time_utc": a["_time"].isoformat(),
            "after_time_utc": b["_time"].isoformat(),

            "elapsed_between_attempt_points_min":
                (
                    b["_time"] - a["_time"]
                ).total_seconds() / 60,

            "before_environment_status":
                a["rescue_environment_status"],

            "after_environment_status":
                b["rescue_environment_status"],
        }

        delta_map = {
            "track_temp_c": "ptsc_track_c",
            "air_temp_c": "hrrr_temp_c",
            "dewpoint_c": "hrrr_dewpoint_c",
            "relative_humidity_pct":
                "hrrr_relative_humidity_pct",
            "pressure_hpa": "hrrr_pressure_hpa",
            "air_density_kg_m3":
                "hrrr_air_density_kg_m3",
            "wind_speed_ms":
                "hrrr_wind_speed_10m_ms",
            "gust_ms": "hrrr_gust_ms",
            "cloud_cover_pct":
                "hrrr_cloud_cover_pct",
            "shortwave_radiation_wm2":
                "hrrr_shortwave_radiation_wm2",
        }

        for label, c in delta_map.items():

            av = pd.to_numeric(
                pd.Series([a.get(c)]),
                errors="coerce"
            ).iloc[0]

            bv = pd.to_numeric(
                pd.Series([b.get(c)]),
                errors="coerce"
            ).iloc[0]

            row["before_" + label] = av
            row["after_" + label] = bv

            row["delta_" + label] = (
                bv - av
                if pd.notna(av) and pd.notna(bv)
                else np.nan
            )

        transition_rows.append(row)

transitions = pd.DataFrame(transition_rows)

# ============================================================
# OUTPUT
# ============================================================

attempt_file = OUT / "rescued_attempt_environment_states_v1.csv"
transition_file = OUT / "rescued_repeat_physical_transitions_v1.csv"
quarantine_file = OUT / "rescued_attempt_quarantine_v1.csv"

attempt_env.to_csv(attempt_file, index=False)
transitions.to_csv(transition_file, index=False)

quarantine = attempt_env[
    (
        attempt_env["chronology_status"]
        != "OK"
    ) |
    (
        attempt_env["sequence_match_status"]
        != "MATCHED"
    )
].copy()

quarantine.to_csv(quarantine_file, index=False)

print("=" * 150)
print("RESCUED ATTEMPT -> ENVIRONMENT JOIN")
print("=" * 150)

print("\nATTEMPT ENVIRONMENT STATUS:")
print(
    attempt_env[
        "rescue_environment_status"
    ].value_counts(dropna=False).to_string()
)

print("\nCHRONOLOGY STATUS:")
print(
    attempt_env[
        "chronology_status"
    ].value_counts(dropna=False).to_string()
)

print("\nHRRR DISTANCES:")
print(
    attempt_env[
        [
            "year",
            "car_number",
            "driver_name",
            "speed_mph",
            "time_utc",
            "matched_run_index",
            "hrrr_match_time_utc",
            "hrrr_time_distance_min",
            "hrrr_match_status",
        ]
    ].to_string(index=False)
)

print("\nPTSC DISTANCES:")
show = [
    "year",
    "car_number",
    "driver_name",
    "speed_mph",
    "ptsc_match_time_utc",
    "ptsc_time_distance_min",
    "ptsc_match_status",
    "ptsc_track_c",
]

show = [
    c for c in show
    if c in attempt_env.columns
]

print(attempt_env[show].to_string(index=False))

print("\nQUARANTINED:")
if quarantine.empty:
    print("NONE")
else:
    print(
        quarantine[
            [
                "year",
                "car_number",
                "driver_name",
                "speed_mph",
                "matched_run_index",
                "sequence_match_status",
                "chronology_status",
            ]
        ].to_string(index=False)
    )

print("\nRESCUED COMPLETE TRANSITIONS:")
if transitions.empty:
    print("NONE")
else:
    print(transitions.to_string(index=False))

print("\nCOUNTS:")
print("rescued attempt points:", len(attempt_env))
print("model-ready HRRR points:",
      int(attempt_env[
          "rescue_environment_status"
      ].isin(["HRRR_READY", "FULL_ENV_READY"]).sum()))

print("model-ready full-env points:",
      int(attempt_env[
          "rescue_environment_status"
      ].eq("FULL_ENV_READY").sum()))

print("rescued complete transitions:", len(transitions))

if not transitions.empty:
    print(
        "complete transitions with delta track temp:",
        int(
            transitions[
                "delta_track_temp_c"
            ].notna().sum()
        )
    )

    print(
        "complete transitions with HRRR deltas:",
        int(
            transitions[
                "delta_air_temp_c"
            ].notna().sum()
        )
    )

print("\nOUTPUTS:")
print(attempt_file.relative_to(ROOT))
print(transition_file.relative_to(ROOT))
print(quarantine_file.relative_to(ROOT))

print("\nRESCUED_ENVIRONMENT_JOIN_V1_COMPLETE")
