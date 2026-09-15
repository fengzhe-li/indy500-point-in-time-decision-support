from pathlib import Path
import requests
import pandas as pd
import time

ROOT = Path("/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈")

OUT = (
    ROOT /
    "r6_regime_extension/output/racecontrol_wayback_v1"
)

OUT.mkdir(
    parents=True,
    exist_ok=True
)

TARGETS = {
    2018: {
        "from": "20180518",
        "to":   "20180521",
    },
    2019: {
        "from": "20190517",
        "to":   "20190520",
    },
    2025: {
        "from": "20250516",
        "to":   "20250519",
    },
}

BASE = "https://web.archive.org/cdx/search/cdx"

all_rows = []

for year, dates in TARGETS.items():

    print("\n" + "=" * 150)
    print("YEAR", year)
    print("=" * 150)

    params = {
        "url": "racecontrol.indycar.com/*",
        "from": dates["from"],
        "to": dates["to"],
        "output": "json",
        "fl": "timestamp,original,statuscode,mimetype,digest",
        "filter": "statuscode:200",
        "collapse": "digest",
    }

    try:

        r = requests.get(
            BASE,
            params=params,
            timeout=60
        )

        print(
            "HTTP",
            r.status_code
        )

        r.raise_for_status()

        data = r.json()

    except Exception as e:

        print(
            "ERROR",
            repr(e)
        )

        continue

    if not data or len(data) <= 1:

        print(
            "NO SNAPSHOTS"
        )

        continue

    header = data[0]

    rows = [
        dict(
            zip(
                header,
                row
            )
        )
        for row in data[1:]
    ]

    for row in rows:

        row["year"] = year

        original = row.get(
            "original",
            ""
        )

        low = original.lower()

        row["looks_like_data_resource"] = any(
            x in low
            for x in [
                ".json",
                ".xml",
                ".js",
                "api",
                "timing",
                "score",
                "session",
                "racecontrol",
                "data",
                "feed",
            ]
        )

        all_rows.append(
            row
        )

    print(
        "snapshots =",
        len(rows)
    )

    time.sleep(
        1
    )

df = pd.DataFrame(
    all_rows
)

if df.empty:

    print(
        "\nNO WAYBACK RESULTS FOUND"
    )

    raise SystemExit(
        0
    )

df = df[
    [
        "year",
        "timestamp",
        "original",
        "statuscode",
        "mimetype",
        "digest",
        "looks_like_data_resource",
    ]
]

df = df.sort_values(
    [
        "year",
        "timestamp",
        "original",
    ]
)

ALL_OUT = (
    OUT /
    "racecontrol_wayback_all_resources_v1.csv"
)

CAND_OUT = (
    OUT /
    "racecontrol_wayback_data_candidates_v1.csv"
)

df.to_csv(
    ALL_OUT,
    index=False
)

cand = df[
    df[
        "looks_like_data_resource"
    ]
].copy()

cand.to_csv(
    CAND_OUT,
    index=False
)

print("\n" + "=" * 150)
print("PART 1 — SNAPSHOT COUNTS")
print("=" * 150)

print(
    df.groupby(
        "year"
    )
    .size()
    .reset_index(
        name="snapshots"
    )
    .to_string(
        index=False
    )
)

print("\n" + "=" * 150)
print("PART 2 — MIMETYPE COUNTS")
print("=" * 150)

print(
    df.groupby(
        [
            "year",
            "mimetype"
        ]
    )
    .size()
    .reset_index(
        name="rows"
    )
    .to_string(
        index=False
    )
)

print("\n" + "=" * 150)
print("PART 3 — DATA-LIKE RESOURCE CANDIDATES")
print("=" * 150)

if cand.empty:

    print(
        "NONE"
    )

else:

    print(
        cand[
            [
                "year",
                "timestamp",
                "mimetype",
                "original",
            ]
        ]
        .head(300)
        .to_string(
            index=False
        )
    )

print("\nOUTPUTS:")
print(
    ALL_OUT.relative_to(
        ROOT
    )
)
print(
    CAND_OUT.relative_to(
        ROOT
    )
)

print(
    "\nR6_RACECONTROL_WAYBACK_DISCOVERY_V1_COMPLETE"
)
