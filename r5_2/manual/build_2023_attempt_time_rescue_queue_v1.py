from pathlib import Path
import pandas as pd

ROOT = Path("/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈")
SRC = ROOT / "r5_2/manual/repeat_physical_rescue_targets_v1.csv"
OUT = ROOT / "r5_2/manual"

df = pd.read_csv(SRC)

d = df[df["year"] == 2023].copy()

# Prioritize drivers with multiple consecutive transitions:
priority_names = [
    "Colton Herta",
    "Christian Lundgaard",
    "David Malukas",
    "Ryan Hunter-Reay",
    "Stefan Wilson",
    "Sting Ray Robb",
    "Will Power",
    "Helio Castroneves",
    "Simon Pagenaud",
    "Scott McLaughlin",
    "Josef Newgarden",
]

d["driver_priority"] = d["driver_name"].apply(
    lambda x: priority_names.index(x) + 1 if x in priority_names else 999
)

d = d.sort_values(
    ["driver_priority", "driver_name", "before_run_index", "after_run_index"]
)

cols = [
    "driver_priority",
    "car_number",
    "driver_name",
    "before_run_index",
    "after_run_index",
    "before_four_lap_average_speed_mph",
    "after_four_lap_average_speed_mph",
    "delta_four_lap_average_speed_mph",
    "before_time_class",
    "after_time_class",
]

cols = [c for c in cols if c in d.columns]

out = OUT / "repeat_attempt_time_rescue_2023_queue_v1.csv"
d[cols].to_csv(out, index=False)

print("=" * 130)
print("2023 ATTEMPT-TIME RESCUE QUEUE")
print("=" * 130)
print(d[cols].to_string(index=False))
print("\nOUTPUT:", out.relative_to(ROOT))
print("\nATTEMPT_TIME_RESCUE_2023_QUEUE_V1_COMPLETE")
