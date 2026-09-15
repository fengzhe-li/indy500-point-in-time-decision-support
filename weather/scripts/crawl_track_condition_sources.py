from pathlib import Path
import csv
import re
import time
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


# =========================
# 基础配置
# =========================

OUTPUT_DIR = Path("weather/evidence")
RAW_DIR = OUTPUT_DIR / "raw_pages"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
RAW_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_CSV = OUTPUT_DIR / "track_condition_evidence_candidates.csv"


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 Chrome/120 Safari/537.36"
    )
}


KEYWORDS = [
    "track temperature",
    "track temp",
    "asphalt temperature",
    "asphalt temp",
    "surface temperature",
    "surface temp",
    "air temperature",
    "air temp",
    "ambient temperature",
    "ambient temp",
    "weather",
    "degrees fahrenheit",
    "degrees f",
    "°f",
    "degrees celsius",
    "°c",
]


# 第一版先用已知高价值入口。
# 后面我们会让脚本从这些 archive/page 继续发现更多链接。
SEED_URLS = {
    2020: [
        "https://doctorindy.com/",
    ],
    2021: [
        "https://doctorindy.com/",
    ],
    2022: [
        "https://www.indycar.com/news/2022/05/05-21-buzz",
        "https://doctorindy.com/",
    ],
    2023: [
        "https://doctorindy.com/",
    ],
    2024: [
        "https://www.indycar.com/news/2024/05/05-18-buzz",
        "https://doctorindy.com/2024/04/10/2024-indianapolis-500-archive/",
    ],
}


# =========================
# 工具函数
# =========================

def fetch_html(url):
    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=20,
        )

        response.raise_for_status()

        return response.text

    except requests.RequestException as exc:
        print(f"[ERROR] {url}")
        print(f"        {exc}")
        return None


def clean_text(html):
    soup = BeautifulSoup(html, "html.parser")

    # 去掉网页中一般没用的元素
    for tag in soup(
        [
            "script",
            "style",
            "nav",
            "footer",
            "noscript",
            "svg",
        ]
    ):
        tag.decompose()

    text = soup.get_text(
        separator=" ",
        strip=True,
    )

    # 连续空白压成一个空格
    text = re.sub(r"\s+", " ", text)

    return text


def get_title(html):
    soup = BeautifulSoup(html, "html.parser")

    if soup.title and soup.title.string:
        return soup.title.string.strip()

    return ""


def split_sentences(text):
    """
    很简单的句子切分。
    新闻正文足够用了。
    """
    return re.split(
        r"(?<=[.!?])\s+",
        text,
    )


def find_keyword_matches(text):
    results = []

    sentences = split_sentences(text)

    for sentence in sentences:

        lower_sentence = sentence.lower()

        matched_keywords = [
            keyword
            for keyword in KEYWORDS
            if keyword in lower_sentence
        ]

        if matched_keywords:

            results.append(
                {
                    "sentence": sentence,
                    "keywords": "; ".join(matched_keywords),
                }
            )

    return results


def extract_temperature_values(sentence):
    """
    找类似：
    85 F
    85°F
    107 degrees
    41 C
    """

    pattern = re.compile(
        r"""
        (?P<value>-?\d+(?:\.\d+)?)
        \s*
        (?:
            °\s*
        )?
        (?P<unit>[FC])
        \b
        |
        (?P<value2>-?\d+(?:\.\d+)?)
        \s*
        degrees?
        \s*
        (?P<unit2>Fahrenheit|Celsius|F|C)?
        """,
        re.IGNORECASE | re.VERBOSE,
    )

    values = []

    for match in pattern.finditer(sentence):

        value = (
            match.group("value")
            or match.group("value2")
        )

        unit = (
            match.group("unit")
            or match.group("unit2")
            or ""
        )

        values.append(
            f"{value} {unit}".strip()
        )

    return "; ".join(values)


def extract_time_values(sentence):
    """
    抓类似：
    11:14 a.m.
    3:26 p.m. ET
    12:30 PM
    """

    pattern = re.compile(
        r"""
        \b
        (?:1[0-2]|0?[1-9])
        :
        [0-5][0-9]
        \s*
        (?:a\.?m\.?|p\.?m\.?)
        (?:\s*ET)?
        \b
        """,
        re.IGNORECASE | re.VERBOSE,
    )

    return "; ".join(
        match.group(0)
        for match in pattern.finditer(sentence)
    )


def save_raw_text(year, url, text):
    parsed = urlparse(url)

    safe_name = re.sub(
        r"[^A-Za-z0-9_-]+",
        "_",
        parsed.path.strip("/") or "homepage",
    )

    filename = f"{year}_{parsed.netloc}_{safe_name}.txt"

    path = RAW_DIR / filename

    path.write_text(
        text,
        encoding="utf-8",
    )

    return str(path)


# =========================
# 主抓取逻辑
# =========================

def process_page(year, url):
    print(f"\n[{year}] {url}")

    html = fetch_html(url)

    if html is None:
        return []

    title = get_title(html)
    text = clean_text(html)

    raw_path = save_raw_text(
        year,
        url,
        text,
    )

    matches = find_keyword_matches(text)

    rows = []

    for match in matches:

        sentence = match["sentence"]

        rows.append(
            {
                "year": year,
                "source_domain": urlparse(url).netloc,
                "page_title": title,
                "url": url,
                "matched_keywords": match["keywords"],
                "temperature_values": extract_temperature_values(
                    sentence
                ),
                "time_values": extract_time_values(
                    sentence
                ),
                "matched_sentence": sentence,
                "raw_text_path": raw_path,
                "review_status": "UNREVIEWED",
                "notes": "",
            }
        )

    print(
        f"    found {len(rows)} candidate sentences"
    )

    return rows


def main():

    all_rows = []

    for year, urls in SEED_URLS.items():

        for url in urls:

            rows = process_page(
                year,
                url,
            )

            all_rows.extend(rows)

            # 礼貌一点，不要连续猛刷网站
            time.sleep(1.5)

    fieldnames = [
        "year",
        "source_domain",
        "page_title",
        "url",
        "matched_keywords",
        "temperature_values",
        "time_values",
        "matched_sentence",
        "raw_text_path",
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

    print("\n=========================")
    print("DONE")
    print("=========================")
    print(f"Candidate rows: {len(all_rows)}")
    print(f"Output: {OUTPUT_CSV}")
    print(f"Raw pages: {RAW_DIR}")


if __name__ == "__main__":
    main()