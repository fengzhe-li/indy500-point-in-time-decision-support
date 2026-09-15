from pathlib import Path
import csv
import re

ROOT = Path("/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈")

SEARCH_DIRS = [
    ROOT / "weather",
    ROOT / "r4" / "output",
]

TOKENS = {
    "track_temp": [
        "track_temp", "track_temperature", "surface_temp",
        "surface_temperature", "tracktemp"
    ],
    "air_temp": [
        "air_temp", "air_temperature", "ambient_temp",
        "ambient_temperature", "tmp_2m", "temperature"
    ],
    "solar": [
        "dswrf", "solar", "shortwave", "radiation"
    ],
    "cloud": [
        "cloud", "tcc"
    ],
    "wind": [
        "wind", "gust", "ugrd", "vgrd"
    ],
    "humidity": [
        "humidity", "relative_humidity", "rh",
        "dew", "dpt"
    ],
    "pressure": [
        "pressure", "pres", "spfh"
    ],
    "time": [
        "timestamp", "time_utc", "attempt_time",
        "decision_time", "datetime", "valid_time"
    ],
    "attempt": [
        "attempt_id", "entry_key", "car_attempt_index"
    ],
    "car": [
        "car_number", "car", "driver", "entry_key"
    ],
    "speed": [
        "four_lap_average_speed", "speed_mph",
        "average_speed", "lap_speed"
    ],
    "section": [
        "section", "sector"
    ],
}

def norm(s):
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")

def read_header(path):
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            r = csv.reader(f)
            return next(r, [])
    except Exception:
        return []

def count_rows(path):
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            return max(sum(1 for _ in f) - 1, 0)
    except Exception:
        return -1

def matches(fields, variants):
    out = []
    for f in fields:
        nf = norm(f)
        for v in variants:
            nv = norm(v)
            if nv in nf or nf in nv:
                out.append(f)
                break
    return out

files = []

for d in SEARCH_DIRS:
    if not d.exists():
        continue
    for p in d.rglob("*.csv"):
        fields = read_header(p)
        if not fields:
            continue

        found = {}
        score = 0

        for category, variants in TOKENS.items():
            ms = matches(fields, variants)
            if ms:
                found[category] = ms
                score += 1

        if score >= 3:
            files.append((score, p, fields, found))

files.sort(key=lambda x: (-x[0], str(x[1])))

print("=" * 150)
print("MANUAL PHYSICS ASSET AUDIT")
print("=" * 150)
print()

for score, path, fields, found in files[:40]:
    print("-" * 150)
    print(f"FILE: {path.relative_to(ROOT)}")
    print(f"ROWS: {count_rows(path)}")
    print(f"PHYSICS/STATE CATEGORIES FOUND: {score}")
    for category, cols in found.items():
        print(f"  {category:12s}: {', '.join(cols)}")
    print()

print("=" * 150)
print("PRIORITY FILE FULL SCHEMAS")
print("=" * 150)

priority_names = [
    "performance_context_features.csv",
    "hrrr_ims_2020_2024_features.csv",
    "indy500_day1_track_temp_2020_2024_time_normalized.csv",
    "r4f7c2c_frozen_numeric_model_matrix_v1.csv",
    "r4p1_attempt_four_lap_panel_v1.csv",
]

for name in priority_names:
    matches_paths = list(ROOT.rglob(name))
    for p in matches_paths:
        fields = read_header(p)
        print()
        print("-" * 150)
        print(f"FILE: {p.relative_to(ROOT)}")
        print(f"ROWS: {count_rows(p)}")
        print("FIELDS:")
        for f in fields:
            print(f"  {f}")

print()
print("=" * 150)
print("AUDIT COMPLETE")
print("=" * 150)
