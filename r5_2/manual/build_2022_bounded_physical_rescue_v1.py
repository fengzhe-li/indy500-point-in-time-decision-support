from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path("/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈")
OUT = ROOT / "r5_2/manual"
OUT.mkdir(parents=True, exist_ok=True)

SRC = ROOT / "r5_2/manual/repeat_regime_rescue_2022_seed_v1.csv"

df = pd.read_csv(SRC)

# Session:
# 2022 Day 1 qualifying began 11:00 ET.
# Official IndyCar report:
# - first 15 min: track about 85F
# - 12:30 ET: track about 107F
# - first rain followed after warming phase
#
# These are evidence bounds, NOT invented exact timestamps.

df["before_time_lower_et"] = ""
df["before_time_upper_et"] = ""
df["after_time_lower_et"] = ""
df["after_time_upper_et"] = ""

df["before_track_temp_lower_c"] = np.nan
df["before_track_temp_upper_c"] = np.nan
df["after_track_temp_lower_c"] = np.nan
df["after_track_temp_upper_c"] = np.nan

df["physical_bound_quality"] = "ORDER_ONLY"
df["physical_bound_notes"] = ""

# Scott McLaughlin:
# first 231.543 pre-rain, later 230.154 after weather interruption
m = df["driver_name"].eq("Scott McLaughlin")

df.loc[m, "before_time_lower_et"] = "2022-05-21 11:00"
df.loc[m, "before_time_upper_et"] = "2022-05-21 12:30"

df.loc[m, "before_track_temp_lower_c"] = 29.4
df.loc[m, "before_track_temp_upper_c"] = 41.7

df.loc[m, "after_time_lower_et"] = "2022-05-21 12:30"
df.loc[m, "after_time_upper_et"] = "2022-05-21 17:50"

df.loc[m, "physical_bound_quality"] = "WEATHER_REGIME_BOUNDED"
df.loc[m, "physical_bound_notes"] = (
    "Official IndyCar report establishes pre-rain warming from ~85F "
    "in first 15 min to ~107F by 12:30 ET. McLaughlin's later attempt "
    "occurred after the weather interruption; exact post-rain track "
    "temperature remains unresolved."
)

# Sato:
# chronology known, but no sufficiently tight timestamp yet.
m = df["driver_name"].eq("Takuma Sato")
df.loc[m, "physical_bound_quality"] = "OFFICIAL_SEQUENCE_ONLY"
df.loc[m, "physical_bound_notes"] = (
    "Official IndyCar confirms first 232.196 was disallowed and "
    "second attempt was 231.708. Exact attempt timestamps unresolved."
)

# Malukas:
m = df["driver_name"].eq("David Malukas")
df.loc[m, "physical_bound_quality"] = "OFFICIAL_FINAL_RESULT_SEQUENCE"
df.loc[m, "physical_bound_notes"] = (
    "Official IndyCar confirms later/final 231.607. "
    "Exact pair timestamps unresolved."
)

# All remaining rows stay ORDER_ONLY.
for name in [
    "Callum Ilott",
    "Sage Karam",
    "Alexander Rossi",
    "Helio Castroneves",
    "Marco Andretti",
]:
    m = df["driver_name"].eq(name)
    df.loc[m, "physical_bound_notes"] = (
        "Performance pair verified in public/official result context; "
        "exact or bounded attempt time still requires targeted chronology rescue."
    )

out = OUT / "repeat_bounded_physical_rescue_2022_v1.csv"
df.to_csv(out, index=False)

print("=" * 140)
print("2022 BOUNDED PHYSICAL RESCUE")
print("=" * 140)

print(
    df[
        [
            "driver_name",
            "before_speed_mph",
            "after_speed_mph",
            "before_time_lower_et",
            "before_time_upper_et",
            "after_time_lower_et",
            "after_time_upper_et",
            "before_track_temp_lower_c",
            "before_track_temp_upper_c",
            "physical_bound_quality",
        ]
    ].to_string(index=False)
)

print("\nQUALITY COUNTS:")
print(df["physical_bound_quality"].value_counts().to_string())

print("\nOUTPUT:", out.relative_to(ROOT))
print("\nBOUNDED_PHYSICAL_RESCUE_2022_V1_COMPLETE")
