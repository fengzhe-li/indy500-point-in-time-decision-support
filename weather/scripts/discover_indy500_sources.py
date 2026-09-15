from pathlib import Path
from urllib.parse import urljoin, urlparse
import csv
import re
import time

import requests
from bs4 import BeautifulSoup


OUTPUT_DIR = Path("weather/evidence")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_CSV = OUTPUT_DIR / "indy500_discovered_sources.csv"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 Chrome/152 Safari/537.36"
    )
}


ARCHIVES = {
    2020: "https://doctorindy.com/2022/06/03/2020-indianapolis-500-archive/",
    2021: "https://doctorindy.com/2022/06/03/2021-indianapolis-500-archive/",
    2022: "https://doctorindy.com/2021/05/22/indianapolis-500-timing-scoring-report-archive/",
    2023: "https://doctorindy.com/2023/04/18/2023-indianapolis-500-archive/",
    2024: "https://doctorindy.com/2024/04/10/2024-indianapolis-500-archive/",
}


# 我们现在宁可多抓候选，再人工筛
RELEVANT_TERMS = [
    "time trials",
    "qualifying",
    "qualification",
    "results",
    "section",
    "top section",
    "morning practice",
    "weather",
    "schedule",
    "draw order",
]


def fetch(url):
    try:
        r = requests.get(
            url,
            headers=HEADERS,
            timeout=25,
        )
        r.raise_for_status()
        return r
    except requests.RequestException as e:
        print(f"[ERROR] {url}")
        print(f"        {e}")
        return None


def classify_url(url):
    lower = url.lower()

    if ".pdf" in lower:
        return "PDF"

    if urlparse(url).netloc.endswith("doctorindy.com"):
        return "DOCTORINDY_PAGE"

    if "indycar.com" in urlparse(url).netloc:
        return "INDYCAR_PAGE"

    return "OTHER"


def relevance_score(anchor_text, url):
    text = f"{anchor_text} {url}".lower()

    matched = [
        term
        for term in RELEVANT_TERMS
        if term in text
    ]

    return len(matched), "; ".join(matched)


def discover_year(year, archive_url):
    print(f"\n=== {year} ===")
    print(archive_url)

    r = fetch(archive_url)

    if r is None:
        return []

    soup = BeautifulSoup(r.text, "html.parser")

    rows = []
    seen = set()

    for a in soup.find_all("a", href=True):
        text = a.get_text(" ", strip=True)
        href = a.get("href")

        if not href:
            continue

        full_url = urljoin(archive_url, href)

        if full_url in seen:
            continue

        seen.add(full_url)

        score, matched_terms = relevance_score(
            text,
            full_url,
        )

        if score == 0:
            continue

        rows.append(
            {
                "year": year,
                "archive_url": archive_url,
                "anchor_text": text,
                "url": full_url,
                "source_type": classify_url(full_url),
                "relevance_score": score,
                "matched_terms": matched_terms,
                "review_status": "UNREVIEWED",
                "notes": "",
            }
        )

    rows.sort(
        key=lambda x: x["relevance_score"],
        reverse=True,
    )

    print(f"Found {len(rows)} relevant links")

    for row in rows[:15]:
        print(
            f"  [{row['source_type']}] "
            f"{row['anchor_text'][:80]}"
        )

    return rows


def main():
    all_rows = []

    for year, archive_url in ARCHIVES.items():
        rows = discover_year(
            year,
            archive_url,
        )

        all_rows.extend(rows)

        time.sleep(1.5)

    fieldnames = [
        "year",
        "archive_url",
        "anchor_text",
        "url",
        "source_type",
        "relevance_score",
        "matched_terms",
        "review_status",
        "notes",
    ]

    with OUTPUT_CSV.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames,
        )
        writer.writeheader()
        writer.writerows(all_rows)

    print("\n========================")
    print("DONE")
    print("========================")
    print(f"Total discovered links: {len(all_rows)}")
    print(f"Output: {OUTPUT_CSV}")


if __name__ == "__main__":
    main()