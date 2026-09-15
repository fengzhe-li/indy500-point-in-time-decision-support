from pathlib import Path
import pandas as pd

ROOT = Path("/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈")
OUT = ROOT / "r5_2/manual"
OUT.mkdir(parents=True, exist_ok=True)

rows = [
    {
        "year": 2023,
        "car_number": 23,
        "driver_name": "Ryan Hunter-Reay",
        "speed_mph": 232.133,
        "attempt_role": "SECOND_ATTEMPT",
        "time_et": "2023-05-20 13:48",
        "time_utc": "2023-05-20T17:48:00Z",
        "time_quality": "EXACT_MINUTE_PUBLIC_CHRONICLE",
        "source_authority": "PUBLIC_CHRONICLE",
        "notes": "IndySpeedway chronology states at 1:48p Hunter-Reay was first driver to take a second run and posted 232.133."
    },
    {
        "year": 2023,
        "car_number": 18,
        "driver_name": "David Malukas",
        "speed_mph": 231.769,
        "attempt_role": "LATER_ATTEMPT",
        "time_et": "2023-05-20 17:38",
        "time_utc": "2023-05-20T21:38:00Z",
        "time_quality": "EXACT_MINUTE_PUBLIC_CHRONICLE",
        "source_authority": "PUBLIC_CHRONICLE",
        "notes": "IndySpeedway chronology states at 5:38p David Malukas moved from the bottom up to 23rd; official result is 231.769."
    },
    {
        "year": 2023,
        "car_number": 6,
        "driver_name": "Felix Rosenqvist",
        "speed_mph": 233.099,
        "attempt_role": "FIRST_ATTEMPT",
        "time_et": "2023-05-20 11:55",
        "time_utc": "2023-05-20T15:55:00Z",
        "time_quality": "EXACT_MINUTE_OFFICIAL",
        "source_authority": "INDYCAR_OFFICIAL",
        "notes": "Official IndyCar states first attempt occurred at 11:55 a.m. ET."
    },
    {
        "year": 2023,
        "car_number": 6,
        "driver_name": "Felix Rosenqvist",
        "speed_mph": 233.947,
        "attempt_role": "SECOND_ATTEMPT",
        "time_et": "2023-05-20 16:42",
        "time_utc": "2023-05-20T20:42:00Z",
        "time_quality": "EXACT_MINUTE_OFFICIAL",
        "source_authority": "INDYCAR_OFFICIAL",
        "notes": "Official IndyCar states second run occurred at 4:42 p.m. ET."
    },
]

df = pd.DataFrame(rows)

out = OUT / "repeat_attempt_time_rescue_2023_seed_v2.csv"
df.to_csv(out, index=False)

print(df.to_string(index=False))
print("\nOUTPUT:", out.relative_to(ROOT))
print("\nREPEAT_ATTEMPT_TIME_RESCUE_2023_SEED_V2_COMPLETE")
