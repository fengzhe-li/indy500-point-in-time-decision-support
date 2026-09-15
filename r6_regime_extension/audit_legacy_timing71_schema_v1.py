from pathlib import Path
import json
import re
from collections import Counter, defaultdict

import pandas as pd

ROOT = Path("/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈")

SRC = (
    ROOT /
    "r6_regime_extension/evidence/timing71_indy500_v2"
)

OUT = (
    ROOT /
    "r6_regime_extension/output/timing71_legacy_schema_audit_v1"
)

OUT.mkdir(
    parents=True,
    exist_ok=True
)

FILES = sorted(
    list(
        SRC.glob(
            "2018*_analysis.json"
        )
    )
    +
    list(
        SRC.glob(
            "2019*_analysis.json"
        )
    )
)

TARGET_KEYS = {
    "lap",
    "laps",
    "lapnumber",
    "laptime",
    "time",
    "timestamp",
    "sessiontime",
    "elapsed",
    "car",
    "cars",
    "driver",
    "drivers",
    "stint",
    "stints",
    "position",
    "speed",
    "number",
}

path_rows = []
key_rows = []
list_rows = []
dict_rows = []
scalar_candidate_rows = []

# ============================================================
# Recursive walker
# ============================================================

def walk(
    obj,
    file_name,
    year,
    path="$",
    depth=0
):

    if depth > 14:
        return

    if isinstance(
        obj,
        dict
    ):

        keys = list(
            obj.keys()
        )

        dict_rows.append({
            "year":
                year,

            "file":
                file_name,

            "json_path":
                path,

            "depth":
                depth,

            "key_count":
                len(keys),

            "keys":
                " | ".join(
                    map(
                        str,
                        keys[:100]
                    )
                ),
        })

        for key, value in obj.items():

            key_str = str(
                key
            )

            key_low = re.sub(
                r"[^a-z0-9]+",
                "",
                key_str.lower()
            )

            child_path = (
                f"{path}.{key_str}"
            )

            path_rows.append({
                "year":
                    year,

                "file":
                    file_name,

                "json_path":
                    child_path,

                "depth":
                    depth + 1,

                "value_type":
                    type(
                        value
                    ).__name__,
            })

            if (
                key_low in TARGET_KEYS
                or any(
                    token in key_low
                    for token in [
                        "lap",
                        "time",
                        "stamp",
                        "session",
                        "elapsed",
                        "car",
                        "driver",
                        "stint",
                        "speed",
                    ]
                )
            ):

                preview = str(
                    value
                )

                if len(
                    preview
                ) > 800:

                    preview = (
                        preview[:800]
                        + "..."
                    )

                key_rows.append({
                    "year":
                        year,

                    "file":
                        file_name,

                    "json_path":
                        child_path,

                    "key":
                        key_str,

                    "normalized_key":
                        key_low,

                    "value_type":
                        type(
                            value
                        ).__name__,

                    "value_preview":
                        preview,
                })

            walk(
                value,
                file_name,
                year,
                child_path,
                depth + 1
            )

    elif isinstance(
        obj,
        list
    ):

        list_rows.append({
            "year":
                year,

            "file":
                file_name,

            "json_path":
                path,

            "depth":
                depth,

            "list_len":
                len(obj),

            "first_item_type":
                (
                    type(
                        obj[0]
                    ).__name__
                    if obj
                    else None
                ),
        })

        # inspect up to 500 items
        for i, value in enumerate(
            obj[:500]
        ):

            walk(
                value,
                file_name,
                year,
                f"{path}[{i}]",
                depth + 1
            )

    else:

        # Look for scalar values that resemble timestamps
        if isinstance(
            obj,
            (
                int,
                float
            )
        ):

            v = float(
                obj
            )

            # unix sec or ms ranges around 2018-2019
            looks_timestamp = (
                1.4e9
                <= v
                <= 2.0e9
            ) or (
                1.4e12
                <= v
                <= 2.0e12
            )

            if looks_timestamp:

                scalar_candidate_rows.append({
                    "year":
                        year,

                    "file":
                        file_name,

                    "json_path":
                        path,

                    "value":
                        obj,
                })


# ============================================================
# Load files
# ============================================================

print("=" * 160)
print("PART 1 — LEGACY ANALYSIS FILES")
print("=" * 160)

for path in FILES:

    m = re.match(
        r"^(2018|2019)_",
        path.name
    )

    if not m:
        continue

    year = int(
        m.group(1)
    )

    payload = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    print(
        year,
        path.name,
        "top_type=",
        type(
            payload
        ).__name__,
        "top_keys=",
        (
            list(
                payload.keys()
            )
            if isinstance(
                payload,
                dict
            )
            else None
        )
    )

    walk(
        payload,
        path.name,
        year
    )

paths = pd.DataFrame(
    path_rows
)

keys = pd.DataFrame(
    key_rows
)

lists = pd.DataFrame(
    list_rows
)

dicts = pd.DataFrame(
    dict_rows
)

scalar_ts = pd.DataFrame(
    scalar_candidate_rows
)

# ============================================================
# Save
# ============================================================

PATH_OUT = (
    OUT /
    "legacy_json_paths_v1.csv"
)

KEY_OUT = (
    OUT /
    "legacy_time_lap_car_key_hits_v1.csv"
)

LIST_OUT = (
    OUT /
    "legacy_list_inventory_v1.csv"
)

DICT_OUT = (
    OUT /
    "legacy_dict_inventory_v1.csv"
)

TS_OUT = (
    OUT /
    "legacy_timestamp_like_scalars_v1.csv"
)

paths.to_csv(
    PATH_OUT,
    index=False
)

keys.to_csv(
    KEY_OUT,
    index=False
)

lists.to_csv(
    LIST_OUT,
    index=False
)

dicts.to_csv(
    DICT_OUT,
    index=False
)

scalar_ts.to_csv(
    TS_OUT,
    index=False
)

# ============================================================
# Console
# ============================================================

print("\n" + "=" * 160)
print("PART 2 — TARGET KEY FREQUENCIES")
print("=" * 160)

if keys.empty:

    print(
        "NONE"
    )

else:

    freq = (
        keys.groupby(
            [
                "year",
                "normalized_key"
            ]
        )
        .size()
        .reset_index(
            name="count"
        )
        .sort_values(
            [
                "year",
                "count"
            ],
            ascending=[
                True,
                False
            ]
        )
    )

    print(
        freq.to_string(
            index=False
        )
    )

print("\n" + "=" * 160)
print("PART 3 — HIGH VALUE KEY EXAMPLES")
print("=" * 160)

if keys.empty:

    print(
        "NONE"
    )

else:

    hv = keys[
        keys[
            "normalized_key"
        ]
        .str.contains(
            r"lap|time|stamp|car|driver|stint|session",
            regex=True,
            na=False
        )
    ]

    print(
        hv[
            [
                "year",
                "file",
                "json_path",
                "key",
                "value_type",
                "value_preview",
            ]
        ]
        .head(400)
        .to_string(
            index=False
        )
    )

print("\n" + "=" * 160)
print("PART 4 — LARGE LIST CANDIDATES")
print("=" * 160)

if lists.empty:

    print(
        "NONE"
    )

else:

    large = (
        lists[
            lists[
                "list_len"
            ]
            >= 5
        ]
        .sort_values(
            [
                "year",
                "list_len"
            ],
            ascending=[
                True,
                False
            ]
        )
    )

    print(
        large[
            [
                "year",
                "file",
                "json_path",
                "list_len",
                "first_item_type",
            ]
        ]
        .head(250)
        .to_string(
            index=False
        )
    )

print("\n" + "=" * 160)
print("PART 5 — TIMESTAMP-LIKE SCALARS")
print("=" * 160)

if scalar_ts.empty:

    print(
        "NONE"
    )

else:

    print(
        scalar_ts[
            [
                "year",
                "file",
                "json_path",
                "value",
            ]
        ]
        .head(300)
        .to_string(
            index=False
        )
    )

print("\n" + "=" * 160)
print("PART 6 — TOP-LEVEL / SHALLOW DICTS")
print("=" * 160)

if dicts.empty:

    print(
        "NONE"
    )

else:

    shallow = (
        dicts[
            dicts[
                "depth"
            ]
            <= 3
        ]
        .sort_values(
            [
                "year",
                "file",
                "depth",
                "json_path",
            ]
        )
    )

    print(
        shallow[
            [
                "year",
                "file",
                "json_path",
                "depth",
                "key_count",
                "keys",
            ]
        ]
        .head(250)
        .to_string(
            index=False
        )
    )

print("\nOUTPUTS:")

for p in [
    PATH_OUT,
    KEY_OUT,
    LIST_OUT,
    DICT_OUT,
    TS_OUT,
]:

    print(
        p.relative_to(
            ROOT
        )
    )

print(
    "\nR6_TIMING71_LEGACY_SCHEMA_AUDIT_V1_COMPLETE"
)
