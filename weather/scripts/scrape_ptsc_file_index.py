from pathlib import Path
from urllib.parse import urljoin, urlparse
import csv
import re

import requests
from bs4 import BeautifulSoup


URL = "https://ptscin.com/files/"

OUTPUT = Path(
    "weather/evidence/ptsc_all_file_links.csv"
)

OUTPUT.parent.mkdir(
    parents=True,
    exist_ok=True,
)


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 "
        "(Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 "
        "Chrome/152 Safari/537.36"
    )
}


KEYWORDS = [
    "firestone",
    "temperature",
    "temp",
    "weather",
    "indy",
    "indianapolis",
    "500",
    "track",
    "sensor",
]


def classify(url):
    lower = url.lower()

    if lower.endswith(".xlsx"):
        return "XLSX"

    if lower.endswith(".xls"):
        return "XLS"

    if lower.endswith(".csv"):
        return "CSV"

    if lower.endswith(".pdf"):
        return "PDF"

    return "PAGE_OR_OTHER"


def relevance(anchor_text, url):
    combined = (
        anchor_text + " " + url
    ).lower()

    matched = [
        keyword
        for keyword in KEYWORDS
        if keyword in combined
    ]

    return len(matched), "; ".join(matched)


def main():
    print(f"Fetching: {URL}")

    response = requests.get(
        URL,
        headers=HEADERS,
        timeout=30,
    )

    response.raise_for_status()

    soup = BeautifulSoup(
        response.text,
        "html.parser",
    )

    rows = []
    seen = set()

    for a in soup.find_all(
        "a",
        href=True,
    ):
        anchor_text = a.get_text(
            " ",
            strip=True,
        )

        href = a.get("href")

        if not href:
            continue

        full_url = urljoin(
            URL,
            href,
        )

        if full_url in seen:
            continue

        seen.add(full_url)

        score, matched = relevance(
            anchor_text,
            full_url,
        )

        rows.append(
            {
                "anchor_text": anchor_text,
                "url": full_url,
                "domain": urlparse(
                    full_url
                ).netloc,
                "file_type": classify(
                    full_url
                ),
                "relevance_score": score,
                "matched_keywords": matched,
            }
        )

    rows.sort(
        key=lambda x: (
            -x["relevance_score"],
            x["file_type"],
            x["anchor_text"],
        )
    )

    fieldnames = [
        "anchor_text",
        "url",
        "domain",
        "file_type",
        "relevance_score",
        "matched_keywords",
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
        writer.writerows(rows)

    print()
    print("========================")
    print("DONE")
    print("========================")
    print(f"Total links: {len(rows)}")
    print(f"Output: {OUTPUT}")

    print()
    print("TOP RELEVANT LINKS:")
    print()

    for row in rows[:50]:
        print(
            f"[{row['relevance_score']}] "
            f"[{row['file_type']}] "
            f"{row['anchor_text']}"
        )

        print(
            f"    {row['url']}"
        )


if __name__ == "__main__":
    main()