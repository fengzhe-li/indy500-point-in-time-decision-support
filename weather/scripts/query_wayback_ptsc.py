from pathlib import Path
import csv
import requests
from urllib.parse import quote


OUTPUT = Path(
    "weather/evidence/ptsc_wayback_results.csv"
)

OUTPUT.parent.mkdir(
    parents=True,
    exist_ok=True,
)


TARGETS = [
    {
        "label": "FirestoneTemperatures current URL",
        "url": "https://ptscin.com/wp-content/uploads/2025/06/FirestoneTemperatures.xlsx",
    },
    {
        "label": "PTSC files page",
        "url": "https://ptscin.com/files/",
    },
    {
        "label": "PTSC uploads FirestoneTemperatures wildcard",
        "url": "https://ptscin.com/wp-content/uploads/*/FirestoneTemperatures.xlsx",
    },
    {
        "label": "PTSC uploads FirestoneTemps wildcard",
        "url": "https://ptscin.com/wp-content/uploads/*/FirestoneTemps.xlsx",
    },
]


CDX_ENDPOINT = "https://web.archive.org/cdx/search/cdx"


def query_cdx(label, url):

    params = {
        "url": url,
        "output": "json",
        "fl": "timestamp,original,statuscode,mimetype,digest",
        "filter": "statuscode:200",
        "collapse": "digest",
        "from": "2020",
        "to": "2025",
    }

    print()
    print(f"Querying: {label}")
    print(url)

    try:
        response = requests.get(
            CDX_ENDPOINT,
            params=params,
            timeout=30,
        )

        response.raise_for_status()

        data = response.json()

    except Exception as exc:
        print(f"ERROR: {exc}")
        return []

    if not data or len(data) <= 1:
        print("  No archived captures found.")
        return []

    header = data[0]
    rows = []

    for record in data[1:]:

        item = dict(zip(header, record))

        timestamp = item.get(
            "timestamp",
            "",
        )

        original = item.get(
            "original",
            "",
        )

        wayback_url = (
            "https://web.archive.org/web/"
            f"{timestamp}id_/{original}"
        )

        rows.append(
            {
                "label": label,
                "timestamp": timestamp,
                "year": timestamp[:4],
                "original_url": original,
                "statuscode": item.get(
                    "statuscode",
                    "",
                ),
                "mimetype": item.get(
                    "mimetype",
                    "",
                ),
                "digest": item.get(
                    "digest",
                    "",
                ),
                "wayback_url": wayback_url,
            }
        )

    print(
        f"  Found {len(rows)} archived capture(s)."
    )

    for row in rows[:10]:
        print(
            "   ",
            row["timestamp"],
            row["original_url"],
        )

    return rows


def main():

    all_rows = []

    for target in TARGETS:

        rows = query_cdx(
            target["label"],
            target["url"],
        )

        all_rows.extend(
            rows
        )

    fieldnames = [
        "label",
        "timestamp",
        "year",
        "original_url",
        "statuscode",
        "mimetype",
        "digest",
        "wayback_url",
    ]

    with OUTPUT.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames,
        )

        writer.writeheader()
        writer.writerows(
            all_rows
        )

    print()
    print("========================")
    print("DONE")
    print("========================")
    print(
        f"Total archived captures: "
        f"{len(all_rows)}"
    )
    print(
        f"Output: {OUTPUT}"
    )

    if all_rows:

        years = sorted(
            set(
                row["year"]
                for row in all_rows
                if row["year"]
            )
        )

        print(
            "Years found:",
            ", ".join(years),
        )


if __name__ == "__main__":
    main()