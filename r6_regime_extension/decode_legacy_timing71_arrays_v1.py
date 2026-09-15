from pathlib import Path
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import json
import re
import math
import pandas as pd

ROOT = Path("/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈")

SRC = (
    ROOT /
    "r6_regime_extension/evidence/timing71_indy500_v2"
)

OUT = (
    ROOT /
    "r6_regime_extension/output/timing71_legacy_array_decode_v1"
)

OUT.mkdir(
    parents=True,
    exist_ok=True
)

INDY_TZ = ZoneInfo(
    "America/Indiana/Indianapolis"
)

FILES = sorted(
    list(SRC.glob("2018*_analysis.json"))
    +
    list(SRC.glob("2019*_analysis.json"))
)

# Cars chosen because they are relevant to official repeat inventory
PREFERRED_CARS = {
    2018: [
        "17",   # Daly
        "9",    # Dixon
        "28",   # Hunter-Reay
        "63",   # Mann
        "15",   # Rahal
        "27",   # Rossi
    ],

    2019: [
        "66",   # Alonso
        "24",   # Karam
        "15",   # Rahal
        "10",   # Rosenqvist
        "27",   # Rossi
        "25",   # Daly
        "31",   # O'Ward
        "5T",   # Hinchcliffe
    ],
}


def is_unix_timestamp(x):

    if not isinstance(
        x,
        (int, float)
    ):
        return False

    try:
        v = float(x)
    except Exception:
        return False

    return (
        1.4e9 <= v <= 2.0e9
        or
        1.4e12 <= v <= 2.0e12
    )


def timestamp_to_iso(x):

    if not is_unix_timestamp(
        x
    ):
        return None

    v = float(x)

    if v > 1e12:
        v /= 1000.0

    dt = datetime.fromtimestamp(
        v,
        tz=timezone.utc
    )

    return {
        "utc":
            dt.isoformat(),

        "indy":
            dt.astimezone(
                INDY_TZ
            ).isoformat(),
    }


def describe_value(x):

    result = {
        "type":
            type(x).__name__,

        "repr":
            repr(x)[:1200],

        "looks_timestamp":
            is_unix_timestamp(x),
    }

    iso = timestamp_to_iso(
        x
    )

    if iso:

        result[
            "timestamp_utc"
        ] = iso[
            "utc"
        ]

        result[
            "timestamp_indianapolis"
        ] = iso[
            "indy"
        ]

    return result


def flatten_array(
    obj,
    prefix=""
):

    rows = []

    if isinstance(
        obj,
        list
    ):

        for i, value in enumerate(
            obj
        ):

            path = (
                f"{prefix}[{i}]"
            )

            if isinstance(
                value,
                list
            ):

                rows.extend(
                    flatten_array(
                        value,
                        path
                    )
                )

            elif isinstance(
                value,
                dict
            ):

                rows.append({
                    "path":
                        path,

                    **describe_value(
                        value
                    )
                })

            else:

                rows.append({
                    "path":
                        path,

                    **describe_value(
                        value
                    )
                })

    else:

        rows.append({
            "path":
                prefix,

            **describe_value(
                obj
            )
        })

    return rows


summary_rows = []
array_rows = []
car_rows = []

print(
    "=" * 170
)
print(
    "PART 1 — FILE / TOP-LEVEL SUMMARY"
)
print(
    "=" * 170
)

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
        "\nYEAR",
        year,
        "FILE",
        path.name
    )

    print(
        "top keys =",
        list(
            payload.keys()
        )
    )

    service = payload.get(
        "service",
        {}
    )

    session = payload.get(
        "session",
        {}
    )

    state = payload.get(
        "state",
        {}
    )

    print(
        "service.startTime =",
        service.get(
            "startTime"
        ),
        timestamp_to_iso(
            service.get(
                "startTime"
            )
        )
    )

    print(
        "service.colSpec =",
        repr(
            service.get(
                "colSpec"
            )
        )[:4000]
    )

    print(
        "service.trackDataSpec =",
        repr(
            service.get(
                "trackDataSpec"
            )
        )[:4000]
    )

    print(
        "session =",
        repr(
            session
        )[:4000]
    )

    print(
        "state.session =",
        repr(
            state.get(
                "session"
            )
        )[:4000]
    )

    summary_rows.append({
        "year":
            year,

        "file":
            path.name,

        "service_startTime":
            service.get(
                "startTime"
            ),

        "service_colSpec":
            repr(
                service.get(
                    "colSpec"
                )
            ),

        "service_trackDataSpec":
            repr(
                service.get(
                    "trackDataSpec"
                )
            ),

        "session_repr":
            repr(
                session
            ),

        "state_session_repr":
            repr(
                state.get(
                    "session"
                )
            ),
    })

    lap_root = payload.get(
        "lap",
        {}
    )

    stint_root = payload.get(
        "stint",
        {}
    )

    driver_root = payload.get(
        "driver",
        {}
    )

    static_root = payload.get(
        "static",
        {}
    )

    available_cars = set()

    for root in [
        lap_root,
        stint_root,
        driver_root,
        static_root,
    ]:

        if isinstance(
            root,
            dict
        ):
            available_cars.update(
                map(
                    str,
                    root.keys()
                )
            )

    selected = [
        car
        for car in PREFERRED_CARS[
            year
        ]
        if car in available_cars
    ]

    # ensure at least some cars get printed
    if not selected:

        selected = sorted(
            available_cars
        )[:8]

    print(
        "\nSELECTED CARS =",
        selected
    )

    for car in selected:

        lap_obj = (
            lap_root.get(
                car
            )
            if isinstance(
                lap_root,
                dict
            )
            else None
        )

        stint_obj = (
            stint_root.get(
                car
            )
            if isinstance(
                stint_root,
                dict
            )
            else None
        )

        driver_obj = (
            driver_root.get(
                car
            )
            if isinstance(
                driver_root,
                dict
            )
            else None
        )

        static_obj = (
            static_root.get(
                car
            )
            if isinstance(
                static_root,
                dict
            )
            else None
        )

        print(
            "\n" + "-" * 140
        )

        print(
            "YEAR",
            year,
            "CAR",
            car
        )

        print(
            "driver =",
            repr(
                driver_obj
            )[:4000]
        )

        print(
            "static =",
            repr(
                static_obj
            )[:4000]
        )

        print(
            "lap =",
            repr(
                lap_obj
            )[:8000]
        )

        print(
            "stint =",
            repr(
                stint_obj
            )[:12000]
        )

        car_rows.append({
            "year":
                year,

            "file":
                path.name,

            "car":
                car,

            "driver_repr":
                repr(
                    driver_obj
                ),

            "static_repr":
                repr(
                    static_obj
                ),

            "lap_repr":
                repr(
                    lap_obj
                ),

            "stint_repr":
                repr(
                    stint_obj
                ),
        })

        for field_name, obj in [
            (
                "lap",
                lap_obj
            ),
            (
                "stint",
                stint_obj
            ),
        ]:

            flat = flatten_array(
                obj,
                prefix=f"$.{field_name}.{car}"
            )

            for r in flat:

                array_rows.append({
                    "year":
                        year,

                    "file":
                        path.name,

                    "car":
                        car,

                    "field":
                        field_name,

                    **r
                })


summary_df = pd.DataFrame(
    summary_rows
)

cars_df = pd.DataFrame(
    car_rows
)

arrays_df = pd.DataFrame(
    array_rows
)

SUMMARY_OUT = (
    OUT /
    "legacy_file_schema_summary_v1.csv"
)

CARS_OUT = (
    OUT /
    "legacy_selected_car_objects_v1.csv"
)

ARRAYS_OUT = (
    OUT /
    "legacy_array_position_inventory_v1.csv"
)

summary_df.to_csv(
    SUMMARY_OUT,
    index=False
)

cars_df.to_csv(
    CARS_OUT,
    index=False
)

arrays_df.to_csv(
    ARRAYS_OUT,
    index=False
)

print(
    "\n" + "=" * 170
)
print(
    "PART 2 — ARRAY POSITION TYPE PATTERNS"
)
print(
    "=" * 170
)

if arrays_df.empty:

    print(
        "NONE"
    )

else:

    pattern = (
        arrays_df.groupby(
            [
                "year",
                "field",
                "path",
                "type",
                "looks_timestamp",
            ],
            dropna=False
        )
        .size()
        .reset_index(
            name="count"
        )
        .sort_values(
            [
                "year",
                "field",
                "path",
            ]
        )
    )

    print(
        pattern
        .head(500)
        .to_string(
            index=False
        )
    )


print(
    "\n" + "=" * 170
)
print(
    "PART 3 — ALL TIMESTAMP POSITIONS"
)
print(
    "=" * 170
)

timestamps = arrays_df[
    arrays_df[
        "looks_timestamp"
    ]
    == True
].copy()

if timestamps.empty:

    print(
        "NONE"
    )

else:

    print(
        timestamps[
            [
                "year",
                "file",
                "car",
                "field",
                "path",
                "repr",
                "timestamp_utc",
                "timestamp_indianapolis",
            ]
        ]
        .to_string(
            index=False
        )
    )


print(
    "\n" + "=" * 170
)
print(
    "PART 4 — LAP OBJECTS, ALL SELECTED CARS"
)
print(
    "=" * 170
)

for _, r in cars_df.iterrows():

    print(
        r[
            "year"
        ],
        r[
            "file"
        ],
        "CAR",
        r[
            "car"
        ],
        "LAP =",
        r[
            "lap_repr"
        ]
    )


print(
    "\n" + "=" * 170
)
print(
    "PART 5 — STINT OBJECTS, ALL SELECTED CARS"
)
print(
    "=" * 170
)

for _, r in cars_df.iterrows():

    print(
        "\n",
        r[
            "year"
        ],
        r[
            "file"
        ],
        "CAR",
        r[
            "car"
        ]
    )

    print(
        r[
            "stint_repr"
        ]
    )


print(
    "\nOUTPUTS:"
)

for p in [
    SUMMARY_OUT,
    CARS_OUT,
    ARRAYS_OUT,
]:

    print(
        p.relative_to(
            ROOT
        )
    )

print(
    "\nR6_TIMING71_LEGACY_ARRAY_DECODE_V1_COMPLETE"
)
