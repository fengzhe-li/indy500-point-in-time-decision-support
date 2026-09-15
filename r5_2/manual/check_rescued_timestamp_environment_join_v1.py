from pathlib import Path
import pandas as pd

ROOT = Path("/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈")

rescues = [
    ROOT / "r5_2/manual/repeat_time_rescue_2024_seed_v1.csv",
    ROOT / "r5_2/manual/repeat_attempt_time_rescue_2023_seed_v2.csv",
]

hrrr = ROOT / "weather/output/hrrr_ims_2020_2024_features.csv"
ptsc = ROOT / "weather/evidence/ptsc/indy500_day1_track_temp_2020_2024_time_normalized.csv"

H = pd.read_csv(hrrr)
P = pd.read_csv(ptsc)

print("=" * 120)
print("HRRR")
print("=" * 120)
print("ROWS:", len(H))
print("COLUMNS:")
for c in H.columns:
    print(c)

print("\n" + "=" * 120)
print("PTSC")
print("=" * 120)
print("ROWS:", len(P))
print("COLUMNS:")
for c in P.columns:
    print(c)

print("\n" + "=" * 120)
print("RESCUE FILES")
print("=" * 120)

for f in rescues:
    print("\nFILE:", f.relative_to(ROOT))
    if not f.exists():
        print("MISSING")
        continue

    d = pd.read_csv(f)
    print("ROWS:", len(d))
    print(d.to_string(index=False))

print("\nENVIRONMENT_JOIN_SCHEMA_CHECK_COMPLETE")
