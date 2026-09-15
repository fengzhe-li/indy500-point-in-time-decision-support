from pathlib import Path
import pandas as pd

ROOT = Path("/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈")
OUT = ROOT / "r5_2/manual"
OUT.mkdir(parents=True, exist_ok=True)

rows = [
    {
        "year": 2022,
        "car_number": 3,
        "driver_name": "Scott McLaughlin",
        "before_speed_mph": 231.543,
        "after_speed_mph": 230.154,
        "before_regime": "PRE_RAIN",
        "after_regime": "POST_RAIN_COOLER",
        "time_quality": "REGIME_BOUNDED",
        "source_authority": "NBC_PLUS_OFFICIAL",
        "notes": "Withdrew 231.543 to try for Fast 12. Qualifying then paused about 90 min by lightning/rain. Second run 230.154 occurred after restart on cooler track."
    },
    {
        "year": 2022,
        "car_number": 51,
        "driver_name": "Takuma Sato",
        "before_speed_mph": 232.196,
        "after_speed_mph": 231.708,
        "before_regime": "INITIAL_FIELD_SWEEP",
        "after_regime": "LATER_ATTEMPT",
        "time_quality": "ORDER_ONLY",
        "source_authority": "INDYCAR_OFFICIAL",
        "notes": "First 232.196 invalidated for impeding Andretti; forced to make a second attempt, resulting 231.708."
    },
    {
        "year": 2022,
        "car_number": 18,
        "driver_name": "David Malukas",
        "before_speed_mph": 231.233,
        "after_speed_mph": 231.607,
        "before_regime": "INITIAL_FIELD_SWEEP",
        "after_regime": "LATER_ATTEMPT",
        "time_quality": "ORDER_ONLY",
        "source_authority": "PUBLIC_SECONDARY",
        "notes": "Multiple-attempt sequence independently reported."
    },
    {
        "year": 2022,
        "car_number": 77,
        "driver_name": "Callum Ilott",
        "before_speed_mph": 230.212,
        "after_speed_mph": 230.961,
        "before_regime": "INITIAL_FIELD_SWEEP",
        "after_regime": "LATER_ATTEMPT",
        "time_quality": "ORDER_ONLY",
        "source_authority": "PUBLIC_SECONDARY",
        "notes": "Multiple-attempt sequence independently reported."
    },
    {
        "year": 2022,
        "car_number": 24,
        "driver_name": "Sage Karam",
        "before_speed_mph": 229.905,
        "after_speed_mph": 230.464,
        "before_regime": "INITIAL_FIELD_SWEEP",
        "after_regime": "LATER_ATTEMPT",
        "time_quality": "ORDER_ONLY",
        "source_authority": "PUBLIC_SECONDARY",
        "notes": "Multiple-attempt sequence independently reported."
    },
    {
        "year": 2022,
        "car_number": 27,
        "driver_name": "Alexander Rossi",
        "before_speed_mph": 231.341,
        "after_speed_mph": 230.812,
        "before_regime": "INITIAL_FIELD_SWEEP",
        "after_regime": "LATER_ATTEMPT",
        "time_quality": "ORDER_ONLY",
        "source_authority": "NBC_PLUS_SECONDARY",
        "notes": "Rossi made a later attempt to improve but dropped from 231.341 to 230.812."
    },
    {
        "year": 2022,
        "car_number": 6,
        "driver_name": "Helio Castroneves",
        "before_speed_mph": 225.482,
        "after_speed_mph": 229.630,
        "before_regime": "INITIAL_FIELD_SWEEP",
        "after_regime": "LATER_ATTEMPT",
        "time_quality": "ORDER_ONLY",
        "source_authority": "PUBLIC_SECONDARY_PLUS_OFFICIAL_RESULT",
        "notes": "Large improvement on repeat attempt; exact timing still unresolved."
    },
    {
        "year": 2022,
        "car_number": 98,
        "driver_name": "Marco Andretti",
        "before_speed_mph": 226.108,
        "after_speed_mph": 230.345,
        "before_regime": "INITIAL_FIELD_SWEEP",
        "after_regime": "LATER_ATTEMPT",
        "time_quality": "ORDER_ONLY",
        "source_authority": "PUBLIC_SECONDARY",
        "notes": "Large improvement on repeat attempt; exact timing still unresolved."
    },
]

df = pd.DataFrame(rows)

out = OUT / "repeat_regime_rescue_2022_seed_v1.csv"
df.to_csv(out, index=False)

print(df.to_string(index=False))
print("\nOUTPUT:", out.relative_to(ROOT))
print("\nREPEAT_REGIME_RESCUE_2022_SEED_V1_COMPLETE")
