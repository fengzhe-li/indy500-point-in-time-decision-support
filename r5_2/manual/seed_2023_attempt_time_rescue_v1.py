from pathlib import Path
import pandas as pd

ROOT = Path("/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈")
OUT = ROOT / "r5_2/manual"
OUT.mkdir(parents=True, exist_ok=True)

rows = [
    # Exact official chronology anchor
    {
        "year": 2023,
        "car_number": 6,
        "driver_name": "Felix Rosenqvist",
        "speed_mph": 233.099,
        "attempt_role": "FIRST_ATTEMPT",
        "time_et": "2023-05-20 11:55",
        "time_utc": "2023-05-20T15:55:00Z",
        "time_quality": "EXACT_MINUTE",
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
        "time_quality": "EXACT_MINUTE",
        "source_authority": "INDYCAR_OFFICIAL",
        "notes": "Official IndyCar states second run occurred at 4:42 p.m. ET."
    },

    # Strong repeat-sequence evidence; timestamp unresolved
    {
        "year": 2023,
        "car_number": 12,
        "driver_name": "Will Power",
        "speed_mph": 232.719,
        "attempt_role": "LATER_ATTEMPT",
        "time_et": "",
        "time_utc": "",
        "time_quality": "SEQUENCE_ONLY",
        "source_authority": "INDYCAR_OFFICIAL",
        "notes": "Official final Day1 result; known later attempt in repeat sequence."
    },
    {
        "year": 2023,
        "car_number": 6,
        "driver_name": "Helio Castroneves",
        "speed_mph": 231.954,
        "attempt_role": "SECOND_ATTEMPT",
        "time_et": "",
        "time_utc": "",
        "time_quality": "SEQUENCE_ONLY",
        "source_authority": "PUBLIC_REPORT_PLUS_OFFICIAL_RESULT",
        "notes": "Reported as improvement on second run; official result confirms 231.954."
    },
    {
        "year": 2023,
        "car_number": 18,
        "driver_name": "David Malukas",
        "speed_mph": 231.769,
        "attempt_role": "LATER_ATTEMPT",
        "time_et": "",
        "time_utc": "",
        "time_quality": "SEQUENCE_ONLY",
        "source_authority": "INDYCAR_OFFICIAL",
        "notes": "Official Day1 result confirms later 231.769."
    },
    {
        "year": 2023,
        "car_number": 23,
        "driver_name": "Ryan Hunter-Reay",
        "speed_mph": 232.133,
        "attempt_role": "LATER_ATTEMPT",
        "time_et": "",
        "time_utc": "",
        "time_quality": "SEQUENCE_ONLY",
        "source_authority": "INDYCAR_OFFICIAL",
        "notes": "Official Day1 result confirms 232.133."
    },
    {
        "year": 2023,
        "car_number": 24,
        "driver_name": "Stefan Wilson",
        "speed_mph": 231.648,
        "attempt_role": "LATER_ATTEMPT",
        "time_et": "",
        "time_utc": "",
        "time_quality": "SEQUENCE_ONLY",
        "source_authority": "INDYCAR_OFFICIAL",
        "notes": "Official Day1 result confirms 231.648."
    },
    {
        "year": 2023,
        "car_number": 26,
        "driver_name": "Colton Herta",
        "speed_mph": 231.951,
        "attempt_role": "LATER_ATTEMPT",
        "time_et": "",
        "time_utc": "",
        "time_quality": "SEQUENCE_ONLY",
        "source_authority": "INDYCAR_OFFICIAL",
        "notes": "Official Day1 result confirms 231.951."
    },
    {
        "year": 2023,
        "car_number": 45,
        "driver_name": "Christian Lundgaard",
        "speed_mph": 231.056,
        "attempt_role": "LATER_ATTEMPT",
        "time_et": "",
        "time_utc": "",
        "time_quality": "SEQUENCE_ONLY",
        "source_authority": "INDYCAR_OFFICIAL",
        "notes": "Official Day1 result confirms 231.056."
    },
    {
        "year": 2023,
        "car_number": 51,
        "driver_name": "Sting Ray Robb",
        "speed_mph": 230.740,
        "attempt_role": "LATER_ATTEMPT",
        "time_et": "",
        "time_utc": "",
        "time_quality": "SEQUENCE_ONLY",
        "source_authority": "INDYCAR_OFFICIAL",
        "notes": "Official Day1 result confirms 230.740."
    },
]

df = pd.DataFrame(rows)

out = OUT / "repeat_attempt_time_rescue_2023_seed_v1.csv"
df.to_csv(out, index=False)

print(df.to_string(index=False))
print("\nQUALITY COUNTS:")
print(df["time_quality"].value_counts().to_string())
print("\nOUTPUT:", out.relative_to(ROOT))
print("\nREPEAT_ATTEMPT_TIME_RESCUE_2023_SEED_V1_COMPLETE")
