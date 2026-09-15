from pathlib import Path
import pandas as pd

ROOT = Path("/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈")
OUT = ROOT / "r5_2/manual"
OUT.mkdir(parents=True, exist_ok=True)

SRC = ROOT / "r5_1/output/day1_same_car_repeat_inventory_v1.csv"

df = pd.read_csv(SRC)

def b(x):
    return x.astype(str).str.lower().isin(["true", "1", "yes"])

for c in [
    "full_environment_pair_available",
    "ptsc_pair_available",
    "hrrr_pair_available",
    "in_frozen_39",
]:
    if c in df.columns:
        df[c] = b(df[c])

full = df.get(
    "full_environment_pair_available",
    pd.Series(False, index=df.index)
)

missing = df[~full].copy()

def priority(r):
    ptsc = bool(r.get("ptsc_pair_available", False))
    hrrr = bool(r.get("hrrr_pair_available", False))

    if ptsc and not hrrr:
        return 1
    if hrrr and not ptsc:
        return 1
    return 2

missing["rescue_priority"] = missing.apply(priority, axis=1)

cols = [
    "rescue_priority",
    "year",
    "car_number",
    "driver_name",
    "team_name",

    "before_run_index",
    "after_run_index",

    "before_attempt_id",
    "after_attempt_id",

    "before_time_utc",
    "after_time_utc",

    "before_time_class",
    "after_time_class",

    "elapsed_between_performance_observations_min",

    "before_four_lap_average_speed_mph",
    "after_four_lap_average_speed_mph",
    "delta_four_lap_average_speed_mph",

    "ptsc_pair_available",
    "hrrr_pair_available",
    "full_environment_pair_available",

    "physical_link_quality",
    "exclusion_reason",
]

cols = [c for c in cols if c in missing.columns]

missing = missing[cols].sort_values(
    ["rescue_priority", "year", "car_number", "before_run_index"]
)

outfile = OUT / "repeat_physical_rescue_targets_v1.csv"
missing.to_csv(outfile, index=False)

print("=" * 150)
print("REPEAT PHYSICAL RESCUE TARGETS")
print("=" * 150)

print("\nTOTAL REPEAT:", len(df))
print("FULL ENVIRONMENT AVAILABLE:", int(full.sum()))
print("NEEDS RESCUE:", len(missing))

print("\nNEEDS RESCUE BY YEAR:")
print(
    missing["year"]
    .value_counts()
    .sort_index()
    .to_string()
)

for yr in [2022, 2024, 2023, 2020, 2021]:
    print("\n" + "=" * 80)
    print(f"{yr} TARGETS")
    print("=" * 80)

    sub = missing[missing["year"] == yr]

    if sub.empty:
        print("NONE")
    else:
        print(sub.to_string(index=False))

print("\nOUTPUT:")
print(outfile.relative_to(ROOT))
print("\nREPEAT_PHYSICAL_RESCUE_TARGETS_V1_COMPLETE")
