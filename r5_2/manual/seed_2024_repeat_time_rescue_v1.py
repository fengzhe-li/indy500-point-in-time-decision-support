from pathlib import Path
import pandas as pd

ROOT = Path("/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈")
OUT = ROOT / "r5_2/manual"
OUT.mkdir(parents=True, exist_ok=True)

rows = [
    # VeeKay
    {
        "year": 2024,
        "car_number": 21,
        "driver_name": "Rinus VeeKay",
        "speed_mph": 231.166,
        "time_utc": "2024-05-18T19:51:00Z",
        "time_quality": "APPROXIMATE_POINT",
        "evidence_type": "OFFICIAL_EDITORIAL_DERIVED",
        "source": "INDYCAR",
        "notes": "Official report states second qualifying attempt at 3:26 p.m. ET was waved off; returned 25 minutes later and recorded 231.166 mph."
    },
    {
        "year": 2024,
        "car_number": 21,
        "driver_name": "Rinus VeeKay",
        "speed_mph": 232.419,
        "time_utc": "2024-05-18T21:49:55Z",
        "time_quality": "TIGHT_BOUND",
        "evidence_type": "OFFICIAL_EDITORIAL",
        "source": "INDYCAR",
        "notes": "Official report states run crossed Yard of Bricks with five seconds remaining before 5:50 p.m. ET session end."
    },

    # Pato
    {
        "year": 2024,
        "car_number": 5,
        "driver_name": "Pato O'Ward",
        "speed_mph": 231.833,
        "time_utc": "2024-05-18T19:41:00Z",
        "time_quality": "APPROXIMATE_POINT",
        "evidence_type": "LIVEBLOG",
        "source": "Crash.net",
        "notes": "Liveblog says run two underway at 20:38 BST and at 20:41 BST O'Ward had moved to 19th with 231.833 mph."
    },
    {
        "year": 2024,
        "car_number": 5,
        "driver_name": "Pato O'Ward",
        "speed_mph": 232.434,
        "time_utc": "2024-05-18T20:33:00Z",
        "time_quality": "APPROXIMATE_POINT",
        "evidence_type": "LIVEBLOG",
        "source": "Crash.net",
        "notes": "Liveblog records 232.434 mph at 21:33 BST."
    },

    # Callum Ilott
    {
        "year": 2024,
        "car_number": 6,
        "driver_name": "Callum Ilott",
        "speed_mph": 231.728,
        "time_utc": "2024-05-18T18:32:00Z",
        "time_quality": "APPROXIMATE_POINT",
        "evidence_type": "LIVEBLOG",
        "source": "Crash.net",
        "notes": "Liveblog says Ilott back on track for another qualifying run at 19:32 BST; later leaderboard shows 231.728 mph."
    },
    {
        "year": 2024,
        "car_number": 6,
        "driver_name": "Callum Ilott",
        "speed_mph": 232.230,
        "time_utc": "2024-05-18T20:37:00Z",
        "time_quality": "APPROXIMATE_POINT",
        "evidence_type": "LIVEBLOG",
        "source": "Crash.net",
        "notes": "Liveblog records Ilott at 232.230 mph at 21:37 BST."
    },

    # Hunter-Reay
    {
        "year": 2024,
        "car_number": 23,
        "driver_name": "Ryan Hunter-Reay",
        "speed_mph": 232.385,
        "time_utc": "2024-05-18T21:02:00Z",
        "time_quality": "APPROXIMATE_POINT",
        "evidence_type": "LIVEBLOG",
        "source": "Crash.net",
        "notes": "Liveblog records 232.385 mph at 22:02 BST."
    },
]

df = pd.DataFrame(rows)

out = OUT / "repeat_time_rescue_2024_seed_v1.csv"
df.to_csv(out, index=False)

print(df.to_string(index=False))
print("\nOUTPUT:", out.relative_to(ROOT))
