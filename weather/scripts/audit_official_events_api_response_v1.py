from pathlib import Path

import json


RAW_DIR = Path(
    "weather/evidence/rescue/"
    "official_indy500_day1_sessions/raw_api"
)

YEARS = [
    2020,
    2021,
    2022,
    2023,
    2024,
]


def load_json(path):

    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


def summarize_value(value):

    if value is None:
        return "NULL"

    if isinstance(
        value,
        str,
    ):
        return repr(
            value[:500]
        )

    if isinstance(
        value,
        (
            int,
            float,
            bool,
        ),
    ):
        return repr(
            value
        )

    if isinstance(
        value,
        list,
    ):

        return (
            f"LIST(len={len(value)}) "
            f"{repr(value[:2])[:1000]}"
        )

    if isinstance(
        value,
        dict,
    ):

        return (
            f"DICT(keys={list(value.keys())}) "
            f"{repr(value)[:1000]}"
        )

    return repr(
        value
    )[:1000]


def extract_list(data):

    if isinstance(
        data,
        list,
    ):
        return data

    if isinstance(
        data,
        dict,
    ):

        print(
            "TOP-LEVEL DICT KEYS:",
            list(
                data.keys()
            ),
        )

        for key in [
            "Events",
            "events",
            "Data",
            "data",
            "Results",
            "results",
        ]:

            value = data.get(
                key
            )

            if isinstance(
                value,
                list,
            ):

                print(
                    "USING WRAPPED LIST FIELD:",
                    key,
                )

                return value

    return None


def main():

    print()
    print("=" * 110)
    print(
        "OFFICIAL EVENTS API RESPONSE "
        "SCHEMA AUDIT V1"
    )
    print("=" * 110)

    for year in YEARS:

        path = (
            RAW_DIR
            /
            f"{year}_events_by_year_series.json"
        )

        print()
        print("=" * 110)
        print(
            f"YEAR {year}"
        )
        print("=" * 110)

        print(
            "PATH:",
            path,
        )

        if not path.exists():

            print(
                "MISSING FILE"
            )

            continue

        data = load_json(
            path
        )

        print(
            "TOP-LEVEL TYPE:",
            type(
                data
            ).__name__,
        )

        objects = extract_list(
            data
        )

        if objects is None:

            print(
                "NO LIST COULD BE IDENTIFIED"
            )

            print(
                "RAW PREVIEW:"
            )

            print(
                repr(
                    data
                )[:5000]
            )

            continue

        print(
            "OBJECT COUNT:",
            len(
                objects
            ),
        )

        if not objects:

            print(
                "EMPTY RESPONSE"
            )

            continue

        # ----------------------------------------------------
        # Union of all keys
        # ----------------------------------------------------

        key_union = []

        seen = set()

        for obj in objects:

            if not isinstance(
                obj,
                dict,
            ):
                continue

            for key in obj.keys():

                if key in seen:
                    continue

                seen.add(
                    key
                )

                key_union.append(
                    key
                )

        print()
        print(
            "ALL OBJECT KEYS:"
        )

        for key in key_union:

            print(
                "  -",
                key,
            )

        # ----------------------------------------------------
        # Print every returned object compactly
        # ----------------------------------------------------

        print()
        print(
            "RETURNED OBJECTS"
        )
        print("-" * 110)

        for index, obj in enumerate(
            objects,
            start=1,
        ):

            print()
            print(
                f"OBJECT {index}"
            )

            if not isinstance(
                obj,
                dict,
            ):

                print(
                    repr(
                        obj
                    )[:3000]
                )

                continue

            for key, value in (
                obj.items()
            ):

                print(
                    f"  {key}: "
                    f"{summarize_value(value)}"
                )

        # ----------------------------------------------------
        # Search every string value for likely Indy terms
        # ----------------------------------------------------

        print()
        print(
            "INDY-LIKE STRING HITS"
        )
        print("-" * 110)

        hits = []

        for index, obj in enumerate(
            objects,
            start=1,
        ):

            if not isinstance(
                obj,
                dict,
            ):
                continue

            serialized = json.dumps(
                obj,
                ensure_ascii=False,
            )

            lower = serialized.lower()

            if (
                "indianapolis"
                in lower
                or
                "indy"
                in lower
                or
                "500"
                in lower
            ):

                hits.append(
                    (
                        index,
                        obj,
                    )
                )

        print(
            "HIT COUNT:",
            len(
                hits
            ),
        )

        for index, obj in hits:

            print()
            print(
                f"HIT OBJECT {index}:"
            )

            print(
                json.dumps(
                    obj,
                    ensure_ascii=False,
                    indent=2,
                )[:6000]
            )

    print()
    print("=" * 110)
    print(
        "FINAL STATUS: "
        "OFFICIAL_EVENTS_API_RESPONSE_AUDITED"
    )
    print("=" * 110)

    print()
    print(
        "NO API CALLS WERE MADE."
    )

    print(
        "NO CANONICAL DATA WAS MODIFIED."
    )


if __name__ == "__main__":
    main()
