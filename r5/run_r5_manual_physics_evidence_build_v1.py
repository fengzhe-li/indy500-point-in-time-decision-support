from pathlib import Path
import csv
import math
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone

ROOT = Path("/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈")

ATTEMPTS = ROOT / "r4/output/r4p1_attempt_four_lap_panel_v1.csv"
PHYSICS = ROOT / "r4/output/r4f7c2c_frozen_numeric_model_matrix_v1.csv"
PTSC = ROOT / "weather/evidence/ptsc/indy500_day1_track_temp_2020_2024_time_normalized.csv"

OUT_WITHIN = ROOT / "r5/output/r5_manual_within_run_fade_physics_v1.csv"
OUT_FIRST = ROOT / "r5/output/r5_manual_first_run_sequence_physics_v1.csv"
OUT_REPEAT = ROOT / "r5/output/r5_manual_same_car_repeat_physics_v1.csv"
OUT_REPORT = ROOT / "r5/output/r5_manual_physics_evidence_report_v1.json"


def clean(v):
    return "" if v is None else str(v).strip()


def num(v):
    s = clean(v)
    if not s:
        return None
    try:
        x = float(s)
        return x if math.isfinite(x) else None
    except Exception:
        return None


def parse_dt(v):
    s = clean(v)
    if not s:
        return None
    s = s.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(s)
    except Exception:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def read_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        r = csv.DictReader(f)
        return r.fieldnames or [], list(r)


def write_csv(path, rows):
    if not rows:
        return
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def solar_position(dt_utc, lat_deg=39.795, lon_deg=-86.234):
    if dt_utc is None:
        return None, None, None

    dt = dt_utc.astimezone(timezone.utc)
    n = dt.timetuple().tm_yday
    hour = dt.hour + dt.minute/60 + dt.second/3600

    gamma = 2 * math.pi / 365 * (n - 1 + (hour - 12)/24)

    eqtime = 229.18 * (
        0.000075
        + 0.001868 * math.cos(gamma)
        - 0.032077 * math.sin(gamma)
        - 0.014615 * math.cos(2*gamma)
        - 0.040849 * math.sin(2*gamma)
    )

    decl = (
        0.006918
        - 0.399912 * math.cos(gamma)
        + 0.070257 * math.sin(gamma)
        - 0.006758 * math.cos(2*gamma)
        + 0.000907 * math.sin(2*gamma)
        - 0.002697 * math.cos(3*gamma)
        + 0.00148 * math.sin(3*gamma)
    )

    true_solar_minutes = (
        dt.hour*60 + dt.minute + dt.second/60
        + eqtime + 4*lon_deg
    ) % 1440

    hour_angle = true_solar_minutes / 4 - 180

    lat = math.radians(lat_deg)
    ha = math.radians(hour_angle)

    cosz = (
        math.sin(lat)*math.sin(decl)
        + math.cos(lat)*math.cos(decl)*math.cos(ha)
    )
    cosz = max(-1, min(1, cosz))

    zenith = math.degrees(math.acos(cosz))
    elevation = 90 - zenith

    az = math.atan2(
        math.sin(ha),
        math.cos(ha)*math.sin(lat) - math.tan(decl)*math.cos(lat)
    )

    azimuth = (math.degrees(az) + 180) % 360

    return elevation, zenith, azimuth


_, attempts = read_csv(ATTEMPTS)
_, physics = read_csv(PHYSICS)
_, ptsc = read_csv(PTSC)

# ============================================================================
# 1. SENSOR IDENTITY
# ============================================================================

print("=" * 150)
print("R5 MANUAL PHYSICS EVIDENCE BUILD")
print("=" * 150)
print()

print("PTSC SENSOR IDENTITY")
print("-" * 150)

for i in range(1, 5):
    names = Counter(
        clean(r.get(f"sensor_{i}_name"))
        for r in ptsc
        if clean(r.get(f"sensor_{i}_name"))
    )
    vals = sum(
        num(r.get(f"sensor_{i}_f")) is not None
        for r in ptsc
    )

    print(f"\nSENSOR {i} | valid={vals}/{len(ptsc)}")
    for name, count in names.most_common():
        print(f"  {name!r}: {count}")

# ============================================================================
# 2. PHYSICS LOOKUP BY ATTEMPT ID
# ============================================================================

phys_by_attempt = {
    clean(r["attempt_id"]): r
    for r in physics
}

# ============================================================================
# 3. WITHIN-RUN FADE PANEL
# ============================================================================

within_rows = []

for a in attempts:
    aid = clean(a["attempt_id"])
    p = phys_by_attempt.get(aid)

    if p is None:
        continue

    lap1 = num(a.get("lap1_speed_mph"))
    lap2 = num(a.get("lap2_speed_mph"))
    lap3 = num(a.get("lap3_speed_mph"))
    lap4 = num(a.get("lap4_speed_mph"))

    if None in [lap1, lap2, lap3, lap4]:
        continue

    dt = parse_dt(p.get("performance_time_utc"))
    elev, zen, az = solar_position(dt)

    within_rows.append({
        "attempt_id": aid,
        "year": clean(a["year"]),
        "entry_key": clean(a["entry_key"]),
        "car_number": clean(a["car_number"]),
        "driver_name": clean(a["driver_name"]),
        "car_attempt_index": clean(a["car_attempt_index"]),

        "performance_time_utc": clean(p.get("performance_time_utc")),

        "lap1_speed_mph": lap1,
        "lap2_speed_mph": lap2,
        "lap3_speed_mph": lap3,
        "lap4_speed_mph": lap4,

        "lap1_to_lap2_delta_mph": lap2 - lap1,
        "lap2_to_lap3_delta_mph": lap3 - lap2,
        "lap3_to_lap4_delta_mph": lap4 - lap3,
        "lap1_to_lap4_delta_mph": lap4 - lap1,
        "late_run_fade_mph": lap4 - lap1,

        "four_lap_average_speed_mph":
            num(a.get("four_lap_average_speed_mph")),

        "track_temp_c":
            num(p.get("ptsc_track_temp_c_past_safe")),

        "track_temp_slope_c_per_min":
            num(p.get("ptsc_track_temp_slope_c_per_min_past_safe")),

        "air_temp_c":
            num(p.get("forecast_temp_c")),

        "dewpoint_c":
            num(p.get("forecast_dewpoint_c")),

        "relative_humidity_pct":
            num(p.get("forecast_relative_humidity_pct")),

        "wind_speed_10m_ms":
            num(p.get("forecast_wind_speed_10m_ms")),

        "wind_direction_deg":
            num(p.get("forecast_wind_direction_deg")),

        "gust_ms":
            num(p.get("forecast_gust_ms")),

        "pressure_hpa":
            num(p.get("forecast_pressure_hpa")),

        "cloud_cover_pct":
            num(p.get("forecast_cloud_cover_pct")),

        "shortwave_radiation_wm2":
            num(p.get("forecast_shortwave_radiation_wm2")),

        "solar_elevation_deg": elev,
        "solar_zenith_deg": zen,
        "solar_azimuth_deg": az,
    })

# ============================================================================
# 4. FIRST-RUN SEQUENCE PANEL
# ============================================================================

by_year = defaultdict(list)

for row in within_rows:
    if str(row["car_attempt_index"]) == "1":
        by_year[row["year"]].append(row)

first_rows = []

for year, rows in sorted(by_year.items()):

    rows = sorted(
        rows,
        key=lambda r: (
            parse_dt(r["performance_time_utc"])
            or datetime.max.replace(tzinfo=timezone.utc)
        )
    )

    for seq, r in enumerate(rows, start=1):
        out = dict(r)
        out["first_run_sequence_position"] = seq
        out["first_run_sequence_n"] = len(rows)
        first_rows.append(out)

# ============================================================================
# 5. SAME-CAR REPEAT TRANSITIONS
# ============================================================================

by_entry = defaultdict(list)

for row in within_rows:
    by_entry[(row["year"], row["entry_key"])].append(row)

repeat_rows = []

for (year, entry_key), rows in by_entry.items():

    rows = sorted(
        rows,
        key=lambda r: (
            int(r["car_attempt_index"])
            if str(r["car_attempt_index"]).isdigit()
            else 999,
            parse_dt(r["performance_time_utc"])
            or datetime.max.replace(tzinfo=timezone.utc)
        )
    )

    for before, after in zip(rows, rows[1:]):

        t0 = parse_dt(before["performance_time_utc"])
        t1 = parse_dt(after["performance_time_utc"])

        elapsed = (
            (t1 - t0).total_seconds()/60
            if t0 and t1
            else None
        )

        def delta(field):
            a = num(before.get(field))
            b = num(after.get(field))
            if a is None or b is None:
                return None
            return b - a

        repeat_rows.append({
            "year": year,
            "entry_key": entry_key,
            "car_number": before["car_number"],
            "driver_name": before["driver_name"],

            "before_attempt_id": before["attempt_id"],
            "after_attempt_id": after["attempt_id"],

            "before_attempt_index": before["car_attempt_index"],
            "after_attempt_index": after["car_attempt_index"],

            "before_time_utc": before["performance_time_utc"],
            "after_time_utc": after["performance_time_utc"],
            "elapsed_minutes": elapsed,

            "before_four_lap_average_speed_mph":
                before["four_lap_average_speed_mph"],

            "after_four_lap_average_speed_mph":
                after["four_lap_average_speed_mph"],

            "delta_four_lap_average_speed_mph":
                delta("four_lap_average_speed_mph"),

            "before_late_run_fade_mph":
                before["late_run_fade_mph"],

            "after_late_run_fade_mph":
                after["late_run_fade_mph"],

            "delta_late_run_fade_mph":
                delta("late_run_fade_mph"),

            "before_track_temp_c":
                before["track_temp_c"],

            "after_track_temp_c":
                after["track_temp_c"],

            "delta_track_temp_c":
                delta("track_temp_c"),

            "before_track_temp_slope_c_per_min":
                before["track_temp_slope_c_per_min"],

            "after_track_temp_slope_c_per_min":
                after["track_temp_slope_c_per_min"],

            "before_air_temp_c":
                before["air_temp_c"],

            "after_air_temp_c":
                after["air_temp_c"],

            "delta_air_temp_c":
                delta("air_temp_c"),

            "before_shortwave_radiation_wm2":
                before["shortwave_radiation_wm2"],

            "after_shortwave_radiation_wm2":
                after["shortwave_radiation_wm2"],

            "delta_shortwave_radiation_wm2":
                delta("shortwave_radiation_wm2"),

            "before_cloud_cover_pct":
                before["cloud_cover_pct"],

            "after_cloud_cover_pct":
                after["cloud_cover_pct"],

            "delta_cloud_cover_pct":
                delta("cloud_cover_pct"),

            "before_wind_speed_10m_ms":
                before["wind_speed_10m_ms"],

            "after_wind_speed_10m_ms":
                after["wind_speed_10m_ms"],

            "delta_wind_speed_10m_ms":
                delta("wind_speed_10m_ms"),

            "before_relative_humidity_pct":
                before["relative_humidity_pct"],

            "after_relative_humidity_pct":
                after["relative_humidity_pct"],

            "delta_relative_humidity_pct":
                delta("relative_humidity_pct"),

            "before_solar_elevation_deg":
                before["solar_elevation_deg"],

            "after_solar_elevation_deg":
                after["solar_elevation_deg"],

            "delta_solar_elevation_deg":
                delta("solar_elevation_deg"),

            "before_solar_azimuth_deg":
                before["solar_azimuth_deg"],

            "after_solar_azimuth_deg":
                after["solar_azimuth_deg"],
        })

# ============================================================================
# COUNTS
# ============================================================================

def full_physics(row):
    req = [
        row.get("track_temp_c"),
        row.get("air_temp_c"),
        row.get("shortwave_radiation_wm2"),
        row.get("wind_speed_10m_ms"),
    ]
    return all(v is not None for v in req)


within_full = [r for r in within_rows if full_physics(r)]
first_full = [r for r in first_rows if full_physics(r)]

repeat_full = [
    r for r in repeat_rows
    if all(
        r.get(k) is not None
        for k in [
            "delta_four_lap_average_speed_mph",
            "before_track_temp_c",
            "after_track_temp_c",
            "before_air_temp_c",
            "after_air_temp_c",
            "before_shortwave_radiation_wm2",
            "after_shortwave_radiation_wm2",
        ]
    )
]

write_csv(OUT_WITHIN, within_rows)
write_csv(OUT_FIRST, first_rows)
write_csv(OUT_REPEAT, repeat_rows)

report = {
    "within_run_complete_lap4_rows": len(within_rows),
    "within_run_full_physics_rows": len(within_full),

    "first_attempt_rows": len(first_rows),
    "first_attempt_full_physics_rows": len(first_full),

    "same_car_repeat_transitions": len(repeat_rows),
    "same_car_repeat_full_physics_rows": len(repeat_full),

    "years_with_first_run_sequence":
        sorted(by_year.keys()),

    "within_run_by_year":
        dict(Counter(r["year"] for r in within_rows)),

    "first_run_by_year":
        dict(Counter(r["year"] for r in first_rows)),

    "repeat_by_year":
        dict(Counter(r["year"] for r in repeat_rows)),
}

OUT_REPORT.write_text(
    json.dumps(report, indent=2, ensure_ascii=False),
    encoding="utf-8"
)

print()
print("=" * 150)
print("PHYSICS EVIDENCE COVERAGE")
print("=" * 150)

print(f"Within-run 4-lap physics rows:        {len(within_rows)}")
print(f"Within-run full-physics rows:         {len(within_full)}")
print()

print(f"First-run sequence rows:              {len(first_rows)}")
print(f"First-run full-physics rows:          {len(first_full)}")
print()

print(f"Same-car repeat transitions:          {len(repeat_rows)}")
print(f"Same-car repeat full-physics rows:    {len(repeat_full)}")

print()
print("BY YEAR")
print("-" * 150)

for year in sorted(set(r["year"] for r in within_rows)):
    print(
        f"{year} | "
        f"within={sum(r['year']==year for r in within_rows):3d} | "
        f"first={sum(r['year']==year for r in first_rows):3d} | "
        f"repeat={sum(r['year']==year for r in repeat_rows):3d}"
    )

print()
print("OUTPUTS")
print("-" * 150)
print(OUT_WITHIN.relative_to(ROOT))
print(OUT_FIRST.relative_to(ROOT))
print(OUT_REPEAT.relative_to(ROOT))
print(OUT_REPORT.relative_to(ROOT))

print()
print("R5_MANUAL_PHYSICS_EVIDENCE_BUILD_COMPLETE")
