from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path("/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈")
OUT = ROOT / "r5_2/manual"

REPEAT = ROOT / "r5_1/output/day1_same_car_repeat_inventory_v1.csv"
STATES = ROOT / "r5_2/manual/rescued_attempt_environment_states_v1.csv"

repeat = pd.read_csv(REPEAT)
states = pd.read_csv(STATES)

repeat["year"] = pd.to_numeric(repeat["year"], errors="coerce").astype("Int64")
states["year"] = pd.to_numeric(states["year"], errors="coerce").astype("Int64")

repeat["car_number"] = (
    repeat["car_number"].astype(str).str.replace(r"\.0$", "", regex=True)
)
states["car_number"] = (
    states["car_number"].astype(str).str.replace(r"\.0$", "", regex=True)
)

repeat["before_four_lap_average_speed_mph"] = pd.to_numeric(
    repeat["before_four_lap_average_speed_mph"], errors="coerce"
)
repeat["after_four_lap_average_speed_mph"] = pd.to_numeric(
    repeat["after_four_lap_average_speed_mph"], errors="coerce"
)

states["speed_mph"] = pd.to_numeric(states["speed_mph"], errors="coerce")
states["_time"] = pd.to_datetime(states["time_utc"], utc=True, errors="coerce")

SPEED_TOL = 0.005

def find_point(year, car, speed):
    c = states[
        (states["year"] == year) &
        (states["car_number"] == car)
    ].copy()

    if c.empty:
        return None

    c["_err"] = (c["speed_mph"] - speed).abs()
    c = c.sort_values("_err")

    if c.iloc[0]["_err"] > SPEED_TOL:
        return None

    return c.iloc[0]

rows = []
quarantine = []

delta_features = {
    "track_temp_c": "ptsc_track_c",
    "air_temp_c": "hrrr_temp_c",
    "dewpoint_c": "hrrr_dewpoint_c",
    "relative_humidity_pct": "hrrr_relative_humidity_pct",
    "pressure_hpa": "hrrr_pressure_hpa",
    "air_density_kg_m3": "hrrr_air_density_kg_m3",
    "wind_speed_ms": "hrrr_wind_speed_10m_ms",
    "gust_ms": "hrrr_gust_ms",
    "cloud_cover_pct": "hrrr_cloud_cover_pct",
    "shortwave_radiation_wm2": "hrrr_shortwave_radiation_wm2",
}

for _, r in repeat.iterrows():
    year = r["year"]
    car = r["car_number"]
    driver = r["driver_name"]

    bs = r["before_four_lap_average_speed_mph"]
    as_ = r["after_four_lap_average_speed_mph"]

    if pd.isna(bs) or pd.isna(as_):
        continue

    a = find_point(year, car, bs)
    b = find_point(year, car, as_)

    if a is None or b is None:
        continue

    ta = a["_time"]
    tb = b["_time"]

    if pd.isna(ta) or pd.isna(tb):
        continue

    if tb <= ta:
        quarantine.append({
            "year": year,
            "car_number": car,
            "driver_name": driver,
            "before_speed_mph": bs,
            "after_speed_mph": as_,
            "rescued_before_time_utc": ta.isoformat(),
            "rescued_after_time_utc": tb.isoformat(),
            "reason": "RESCUED_TIME_ORDER_CONFLICTS_WITH_REPEAT_SEQUENCE",
        })
        continue

    ah = str(a.get("hrrr_match_status", ""))
    bh = str(b.get("hrrr_match_status", ""))

    if ah != "ACCEPT" or bh != "ACCEPT":
        quarantine.append({
            "year": year,
            "car_number": car,
            "driver_name": driver,
            "before_speed_mph": bs,
            "after_speed_mph": as_,
            "rescued_before_time_utc": ta.isoformat(),
            "rescued_after_time_utc": tb.isoformat(),
            "reason": "HRRR_ENDPOINT_NOT_ACCEPTED",
        })
        continue

    row = {
        "transition_id": r.get("transition_id", ""),
        "year": year,
        "car_number": car,
        "driver_name": driver,
        "team_name": r.get("team_name", ""),

        "before_attempt_id": r.get("before_attempt_id", ""),
        "after_attempt_id": r.get("after_attempt_id", ""),

        "before_run_index": r.get("before_run_index", np.nan),
        "after_run_index": r.get("after_run_index", np.nan),

        "before_speed_mph": bs,
        "after_speed_mph": as_,
        "delta_speed_mph": as_ - bs,

        "before_time_utc": ta.isoformat(),
        "after_time_utc": tb.isoformat(),

        "elapsed_between_attempt_points_min":
            (tb - ta).total_seconds() / 60.0,

        "before_time_quality": a.get("time_quality", ""),
        "after_time_quality": b.get("time_quality", ""),

        "before_hrrr_distance_min":
            a.get("hrrr_time_distance_min", np.nan),

        "after_hrrr_distance_min":
            b.get("hrrr_time_distance_min", np.nan),

        "before_ptsc_distance_min":
            a.get("ptsc_time_distance_min", np.nan),

        "after_ptsc_distance_min":
            b.get("ptsc_time_distance_min", np.nan),

        "before_ptsc_status":
            a.get("ptsc_match_status", ""),

        "after_ptsc_status":
            b.get("ptsc_match_status", ""),
    }

    for label, col in delta_features.items():
        av = pd.to_numeric(
            pd.Series([a.get(col)]),
            errors="coerce"
        ).iloc[0]

        bv = pd.to_numeric(
            pd.Series([b.get(col)]),
            errors="coerce"
        ).iloc[0]

        row["before_" + label] = av
        row["after_" + label] = bv
        row["delta_" + label] = (
            bv - av if pd.notna(av) and pd.notna(bv) else np.nan
        )

    row["rescued_physical_quality"] = (
        "FULL_ENV_RESCUED"
        if (
            row["before_ptsc_status"] == "ACCEPT" and
            row["after_ptsc_status"] == "ACCEPT"
        )
        else "HRRR_ONLY_RESCUED"
    )

    rows.append(row)

out = pd.DataFrame(rows)
q = pd.DataFrame(quarantine)

OUTFILE = OUT / "rescued_repeat_physical_transitions_v2.csv"
QFILE = OUT / "rescued_repeat_transition_quarantine_v2.csv"

out.to_csv(OUTFILE, index=False)
q.to_csv(QFILE, index=False)

print("=" * 150)
print("RESCUED REPEAT TRANSITIONS — SPEED-PAIR MATCH V2")
print("=" * 150)

print("\nVALID RESCUED TRANSITIONS:", len(out))

if not out.empty:
    show = [
        "year",
        "car_number",
        "driver_name",
        "before_speed_mph",
        "after_speed_mph",
        "delta_speed_mph",
        "before_time_utc",
        "after_time_utc",
        "elapsed_between_attempt_points_min",
        "before_ptsc_distance_min",
        "after_ptsc_distance_min",
        "delta_track_temp_c",
        "delta_air_temp_c",
        "delta_air_density_kg_m3",
        "delta_gust_ms",
        "delta_shortwave_radiation_wm2",
        "rescued_physical_quality",
    ]

    print(out[show].to_string(index=False))

print("\nQUARANTINE:", len(q))

if not q.empty:
    print(q.to_string(index=False))

print("\nBY YEAR:")
if not out.empty:
    print(out["year"].value_counts().sort_index().to_string())

print("\nFULL ENV RESCUED:")
if not out.empty:
    print(
        out["rescued_physical_quality"]
        .value_counts()
        .to_string()
    )

print("\nOUTPUTS:")
print(OUTFILE.relative_to(ROOT))
print(QFILE.relative_to(ROOT))

print("\nRESCUED_REPEAT_TRANSITIONS_SPEED_PAIR_V2_COMPLETE")
