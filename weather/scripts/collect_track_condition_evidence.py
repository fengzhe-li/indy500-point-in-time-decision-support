from pathlib import Path
from urllib.parse import urlparse
from datetime import datetime, timezone
import csv
import hashlib
import random
import re
import time

import requests
from pypdf import PdfReader


# ============================================================
# PATHS
# ============================================================

DISCOVERED_CSV = Path(
    "weather/evidence/indy500_discovered_sources.csv"
)

DOWNLOAD_ROOT = Path(
    "weather/evidence/downloads"
)

TEXT_ROOT = Path(
    "weather/evidence/extracted_text"
)

MANIFEST_CSV = Path(
    "weather/evidence/priority_download_manifest.csv"
)

EVIDENCE_CSV = Path(
    "weather/evidence/track_condition_evidence_candidates_v2.csv"
)


DOWNLOAD_ROOT.mkdir(
    parents=True,
    exist_ok=True,
)

TEXT_ROOT.mkdir(
    parents=True,
    exist_ok=True,
)


# ============================================================
# HTTP CONFIG
# ============================================================

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 "
        "(Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 "
        "Chrome/152 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,"
        "application/xml;q=0.9,"
        "application/pdf;q=0.8,*/*;q=0.7"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


# 正常两个请求之间至少等这么久。
BASE_DELAY_SECONDS = 12

# 再加一点随机抖动，避免机械式固定间隔。
RANDOM_DELAY_SECONDS = 5

# 429 后最多重试次数。
MAX_RETRIES = 3


# ============================================================
# DOCUMENT FILTER
# ============================================================

# 现在只抓真正跟 Day 1 qualifying / track condition
# 很有关系的文件。
#
# 不下载：
# Race
# Carb Day
# Pole Day
# Post-Qualifying
# 等当前无关资料。

PRIORITY_TERMS = [
    "time trials day 1",
    "time trials – day 1",
    "time trials - day 1",
    "top section",
    "section results",
    "morning practice",
    "qualifying draw order",
    "qualifying procedure",
]


# ============================================================
# WEATHER EVIDENCE PATTERNS
# ============================================================

EVIDENCE_PATTERNS = {

    # 最重要：真实赛道/沥青表面温度
    "TRACK_TEMPERATURE": [
        r"\btrack temperature\b",
        r"\btrack temp\b",
        r"\basphalt temperature\b",
        r"\basphalt temp\b",
        r"\btrack surface temperature\b",
        r"\btrack surface temp\b",
        r"\bsurface temperature\b",
        r"\bsurface temp\b",
    ],

    # 与 HRRR TMP_2m 同类，主要用于 validation
    "AIR_TEMPERATURE": [
        r"\bair temperature\b",
        r"\bair temp\b",
        r"\bambient temperature\b",
        r"\bambient temp\b",
    ],

    "HUMIDITY": [
        r"\brelative humidity\b",
        r"\bhumidity\b",
    ],

    "WIND": [
        r"\bwind speed\b",
        r"\bwind\b",
        r"\bgust\b",
    ],

    "PRESSURE": [
        r"\bbarometric pressure\b",
        r"\bbarometer\b",
        r"\bpressure\b",
    ],

    "WEATHER_GENERAL": [
        r"\bweather\b",
        r"\bcloud cover\b",
        r"\bcloudy\b",
        r"\bpartly cloudy\b",
        r"\bsunny\b",
        r"\bovercast\b",
    ],
}


# ============================================================
# REGEX
# ============================================================

TEMP_RE = re.compile(
    r"""
    (?P<value>-?\d+(?:\.\d+)?)
    \s*
    (?:°\s*)?
    (?P<unit>F|C)
    \b

    |

    (?P<value2>-?\d+(?:\.\d+)?)
    \s*
    degrees?
    \s*
    (?P<unit2>
        Fahrenheit|
        Celsius|
        F|
        C
    )?
    """,
    re.IGNORECASE | re.VERBOSE,
)


TIME_RE = re.compile(
    r"""
    \b
    (?:1[0-2]|0?[1-9])
    :
    [0-5][0-9]
    \s*
    (?:a\.?m\.?|p\.?m\.?)
    (?:\s*(?:ET|EDT|EST))?
    \b
    """,
    re.IGNORECASE | re.VERBOSE,
)


# ============================================================
# HELPERS
# ============================================================

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def safe_filename(url: str, fallback: str) -> str:

    parsed = urlparse(url)

    filename = Path(parsed.path).name

    if not filename:
        filename = fallback

    if not filename.lower().endswith(".pdf"):
        filename += ".pdf"

    filename = re.sub(
        r"[^A-Za-z0-9._-]+",
        "_",
        filename,
    )

    return filename


def normalize_fallback_name(text: str) -> str:

    text = text.strip().lower()

    text = text.replace("–", "-")
    text = text.replace("—", "-")

    text = re.sub(
        r"[^a-z0-9_-]+",
        "_",
        text,
    )

    text = re.sub(
        r"_+",
        "_",
        text,
    )

    return text.strip("_")


def is_priority_document(anchor_text: str) -> bool:

    text = anchor_text.lower()

    return any(
        term in text
        for term in PRIORITY_TERMS
    )


def sleep_between_requests():

    wait = (
        BASE_DELAY_SECONDS
        + random.uniform(
            0,
            RANDOM_DELAY_SECONDS,
        )
    )

    print(
        f"    polite delay: "
        f"{wait:.1f}s"
    )

    time.sleep(wait)


# ============================================================
# DOWNLOAD
# ============================================================

def download_pdf(
    session,
    year,
    anchor_text,
    url,
):

    year_dir = (
        DOWNLOAD_ROOT
        / str(year)
    )

    year_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    fallback = normalize_fallback_name(
        anchor_text
    )

    filename = safe_filename(
        url,
        fallback,
    )

    output_path = (
        year_dir
        / filename
    )

    # ------------------------------
    # Already downloaded
    # ------------------------------

    if output_path.exists():

        data = output_path.read_bytes()

        if data.startswith(b"%PDF"):

            print(
                f"    already exists: "
                f"{output_path}"
            )

            return {
                "year": year,
                "anchor_text": anchor_text,
                "url": url,
                "status": "ALREADY_EXISTS",
                "http_status": "",
                "local_path": str(
                    output_path
                ),
                "bytes": len(data),
                "sha256": sha256_bytes(
                    data
                ),
                "downloaded_at_utc": "",
                "notes": "",
            }

    # ------------------------------
    # Download with retry
    # ------------------------------

    for retry in range(
        MAX_RETRIES
    ):

        try:

            print(
                f"    request attempt "
                f"{retry + 1}/"
                f"{MAX_RETRIES}"
            )

            response = session.get(
                url,
                headers=HEADERS,
                timeout=40,
                allow_redirects=True,
            )

            # ----------------------
            # 429
            # ----------------------

            if response.status_code == 429:

                retry_after = (
                    response.headers.get(
                        "Retry-After"
                    )
                )

                if (
                    retry_after
                    and
                    retry_after.isdigit()
                ):
                    wait_seconds = int(
                        retry_after
                    )

                else:
                    # 60 / 120 / 180
                    wait_seconds = (
                        60
                        * (retry + 1)
                    )

                print(
                    "    429 rate limited."
                )

                print(
                    f"    waiting "
                    f"{wait_seconds}s..."
                )

                time.sleep(
                    wait_seconds
                )

                continue

            response.raise_for_status()

            data = response.content

            content_type = (
                response.headers
                .get(
                    "Content-Type",
                    "",
                )
                .lower()
            )

            is_pdf = (
                data.startswith(b"%PDF")
                or
                "application/pdf"
                in content_type
            )

            if not is_pdf:

                return {
                    "year": year,
                    "anchor_text": anchor_text,
                    "url": url,
                    "status": "NOT_PDF",
                    "http_status": (
                        response.status_code
                    ),
                    "local_path": "",
                    "bytes": len(data),
                    "sha256": (
                        sha256_bytes(data)
                    ),
                    "downloaded_at_utc": (
                        datetime.now(
                            timezone.utc
                        ).isoformat()
                    ),
                    "notes": (
                        "Content-Type="
                        f"{content_type}"
                    ),
                }

            output_path.write_bytes(
                data
            )

            print(
                f"    downloaded: "
                f"{output_path}"
            )

            return {
                "year": year,
                "anchor_text": anchor_text,
                "url": url,
                "status": "DOWNLOADED",
                "http_status": (
                    response.status_code
                ),
                "local_path": str(
                    output_path
                ),
                "bytes": len(data),
                "sha256": (
                    sha256_bytes(data)
                ),
                "downloaded_at_utc": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
                "notes": "",
            }

        except requests.RequestException as exc:

            print(
                f"    request error: "
                f"{exc}"
            )

            if retry < (
                MAX_RETRIES - 1
            ):

                wait_seconds = (
                    30
                    * (retry + 1)
                )

                print(
                    f"    waiting "
                    f"{wait_seconds}s..."
                )

                time.sleep(
                    wait_seconds
                )

                continue

            return {
                "year": year,
                "anchor_text": anchor_text,
                "url": url,
                "status": "FAILED",
                "http_status": (
                    getattr(
                        getattr(
                            exc,
                            "response",
                            None,
                        ),
                        "status_code",
                        "",
                    )
                ),
                "local_path": "",
                "bytes": "",
                "sha256": "",
                "downloaded_at_utc": "",
                "notes": str(exc),
            }

    return {
        "year": year,
        "anchor_text": anchor_text,
        "url": url,
        "status": "FAILED",
        "http_status": 429,
        "local_path": "",
        "bytes": "",
        "sha256": "",
        "downloaded_at_utc": "",
        "notes": (
            "Repeated rate limiting"
        ),
    }


# ============================================================
# PDF TEXT EXTRACTION
# ============================================================

def extract_pdf_text(
    pdf_path: Path
) -> str:

    try:

        reader = PdfReader(
            str(pdf_path)
        )

        parts = []

        for page_number, page in enumerate(
            reader.pages,
            start=1,
        ):

            try:

                text = (
                    page.extract_text()
                    or ""
                )

                if text.strip():

                    parts.append(
                        f"\n"
                        f"--- PAGE "
                        f"{page_number} ---\n"
                        f"{text}"
                    )

            except Exception as exc:

                parts.append(
                    f"\n"
                    f"--- PAGE "
                    f"{page_number} "
                    f"EXTRACTION ERROR ---\n"
                    f"{exc}"
                )

        return "\n".join(
            parts
        )

    except Exception as exc:

        print(
            f"    PDF extraction "
            f"failed: {exc}"
        )

        return ""


def save_extracted_text(
    year,
    pdf_path: Path,
    text: str,
):

    year_dir = (
        TEXT_ROOT
        / str(year)
    )

    year_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    txt_path = (
        year_dir
        / (
            pdf_path.stem
            + ".txt"
        )
    )

    txt_path.write_text(
        text,
        encoding="utf-8",
    )

    return txt_path


# ============================================================
# TEXT PROCESSING
# ============================================================

def clean_extracted_text(
    text: str
) -> str:

    text = text.replace(
        "\xa0",
        " ",
    )

    text = re.sub(
        r"[ \t]+",
        " ",
        text,
    )

    text = re.sub(
        r"\n{3,}",
        "\n\n",
        text,
    )

    return text.strip()


def split_context_blocks(
    text: str
):

    # PDF text is often not perfect prose.
    # Split on newlines and sentence boundaries.

    pieces = re.split(
        r"(?<=[.!?])\s+|\n+",
        text,
    )

    return [
        p.strip()
        for p in pieces
        if len(
            p.strip()
        ) >= 5
    ]


def classify_block(
    text: str
):

    lower = text.lower()

    found = []

    for evidence_type, patterns in (
        EVIDENCE_PATTERNS.items()
    ):

        for pattern in patterns:

            if re.search(
                pattern,
                lower,
                re.IGNORECASE,
            ):

                found.append(
                    evidence_type
                )

                break

    return found


def extract_temperatures(
    text: str
):

    values = []

    for match in TEMP_RE.finditer(
        text
    ):

        value = (
            match.group("value")
            or
            match.group("value2")
        )

        unit = (
            match.group("unit")
            or
            match.group("unit2")
            or ""
        )

        values.append(
            f"{value} "
            f"{unit}".strip()
        )

    return "; ".join(
        values
    )


def extract_times(
    text: str
):

    values = [
        m.group(0)
        for m in TIME_RE.finditer(
            text
        )
    ]

    return "; ".join(
        values
    )


def build_context(
    blocks,
    index,
):

    previous_block = (
        blocks[index - 1]
        if index > 0
        else ""
    )

    current_block = (
        blocks[index]
    )

    next_block = (
        blocks[index + 1]
        if index + 1
        < len(blocks)
        else ""
    )

    context = " | ".join(
        x
        for x in [
            previous_block,
            current_block,
            next_block,
        ]
        if x
    )

    return context


# ============================================================
# EVIDENCE EXTRACTION
# ============================================================

def extract_evidence_from_text(
    year,
    anchor_text,
    source_url,
    pdf_path,
    text_path,
    text,
):

    blocks = split_context_blocks(
        text
    )

    rows = []

    seen = set()

    for i, block in enumerate(
        blocks
    ):

        types = classify_block(
            block
        )

        if not types:
            continue

        context = build_context(
            blocks,
            i,
        )

        # 去重
        dedupe_key = (
            year,
            str(pdf_path),
            context,
        )

        if dedupe_key in seen:
            continue

        seen.add(
            dedupe_key
        )

        temperatures = (
            extract_temperatures(
                context
            )
        )

        times = (
            extract_times(
                context
            )
        )

        for evidence_type in types:

            # Track temp 是核心。
            if (
                evidence_type
                ==
                "TRACK_TEMPERATURE"
            ):
                priority = "HIGH"

            elif (
                evidence_type
                ==
                "AIR_TEMPERATURE"
            ):
                priority = "MEDIUM"

            else:
                priority = "LOW"

            rows.append(
                {
                    "year": year,
                    "document_title": (
                        anchor_text
                    ),
                    "source_url": (
                        source_url
                    ),
                    "local_pdf_path": (
                        str(pdf_path)
                    ),
                    "extracted_text_path": (
                        str(text_path)
                    ),
                    "evidence_type": (
                        evidence_type
                    ),
                    "priority": (
                        priority
                    ),
                    "temperature_values": (
                        temperatures
                    ),
                    "time_values": (
                        times
                    ),
                    "matched_text": (
                        block
                    ),
                    "context": (
                        context
                    ),
                    "review_status": (
                        "UNREVIEWED"
                    ),
                    "accepted_as_observation": (
                        ""
                    ),
                    "notes": "",
                }
            )

    return rows


# ============================================================
# MAIN
# ============================================================

def main():

    if not DISCOVERED_CSV.exists():

        raise FileNotFoundError(
            f"Missing input file: "
            f"{DISCOVERED_CSV}"
        )

    # --------------------------------------------------------
    # Load discovered sources
    # --------------------------------------------------------

    candidates = []

    with DISCOVERED_CSV.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as f:

        reader = csv.DictReader(
            f
        )

        for row in reader:

            if (
                row.get(
                    "source_type"
                )
                !=
                "PDF"
            ):
                continue

            anchor_text = (
                row.get(
                    "anchor_text",
                    "",
                )
            )

            if not is_priority_document(
                anchor_text
            ):
                continue

            candidates.append(
                row
            )

    print(
        "================================="
    )
    print(
        "TRACK CONDITION EVIDENCE COLLECTOR"
    )
    print(
        "================================="
    )

    print(
        f"Priority PDF candidates: "
        f"{len(candidates)}"
    )

    print()

    # --------------------------------------------------------
    # Download
    # --------------------------------------------------------

    session = requests.Session()

    manifest_rows = []

    for index, row in enumerate(
        candidates,
        start=1,
    ):

        year = row["year"]

        anchor_text = (
            row["anchor_text"]
        )

        url = row["url"]

        print(
            f"\n"
            f"{index}/"
            f"{len(candidates)}"
        )

        print(
            f"[{year}] "
            f"{anchor_text}"
        )

        print(
            f"    {url}"
        )

        result = download_pdf(
            session=session,
            year=year,
            anchor_text=anchor_text,
            url=url,
        )

        manifest_rows.append(
            result
        )

        # 已存在不需要浪费等待。
        if (
            result["status"]
            !=
            "ALREADY_EXISTS"
        ):
            sleep_between_requests()

    # --------------------------------------------------------
    # Save manifest
    # --------------------------------------------------------

    manifest_fields = [
        "year",
        "anchor_text",
        "url",
        "status",
        "http_status",
        "local_path",
        "bytes",
        "sha256",
        "downloaded_at_utc",
        "notes",
    ]

    with MANIFEST_CSV.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=manifest_fields,
        )

        writer.writeheader()

        writer.writerows(
            manifest_rows
        )

    # --------------------------------------------------------
    # Extract PDF evidence
    # --------------------------------------------------------

    evidence_rows = []

    for row in manifest_rows:

        if row["status"] not in {
            "DOWNLOADED",
            "ALREADY_EXISTS",
        }:
            continue

        local_path = row[
            "local_path"
        ]

        if not local_path:
            continue

        pdf_path = Path(
            local_path
        )

        if not pdf_path.exists():
            continue

        print(
            f"\nScanning PDF:"
        )

        print(
            f"    {pdf_path}"
        )

        raw_text = extract_pdf_text(
            pdf_path
        )

        if not raw_text.strip():

            print(
                "    no extractable text"
            )

            continue

        text = clean_extracted_text(
            raw_text
        )

        text_path = save_extracted_text(
            row["year"],
            pdf_path,
            text,
        )

        new_rows = (
            extract_evidence_from_text(
                year=row["year"],
                anchor_text=(
                    row["anchor_text"]
                ),
                source_url=row["url"],
                pdf_path=pdf_path,
                text_path=text_path,
                text=text,
            )
        )

        evidence_rows.extend(
            new_rows
        )

        high_count = sum(
            1
            for x in new_rows
            if x["priority"]
            ==
            "HIGH"
        )

        print(
            f"    candidates: "
            f"{len(new_rows)}"
        )

        print(
            f"    HIGH "
            f"track-temp candidates: "
            f"{high_count}"
        )

    # --------------------------------------------------------
    # Sort evidence
    # --------------------------------------------------------

    priority_order = {
        "HIGH": 0,
        "MEDIUM": 1,
        "LOW": 2,
    }

    evidence_rows.sort(
        key=lambda r: (
            priority_order.get(
                r["priority"],
                99,
            ),
            int(r["year"]),
            r["document_title"],
        )
    )

    # --------------------------------------------------------
    # Save evidence CSV
    # --------------------------------------------------------

    evidence_fields = [
        "year",
        "document_title",
        "source_url",
        "local_pdf_path",
        "extracted_text_path",
        "evidence_type",
        "priority",
        "temperature_values",
        "time_values",
        "matched_text",
        "context",
        "review_status",
        "accepted_as_observation",
        "notes",
    ]

    with EVIDENCE_CSV.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=evidence_fields,
        )

        writer.writeheader()

        writer.writerows(
            evidence_rows
        )

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    downloaded = sum(
        1
        for x in manifest_rows
        if x["status"]
        ==
        "DOWNLOADED"
    )

    existing = sum(
        1
        for x in manifest_rows
        if x["status"]
        ==
        "ALREADY_EXISTS"
    )

    failed = sum(
        1
        for x in manifest_rows
        if x["status"]
        ==
        "FAILED"
    )

    track_temp_hits = sum(
        1
        for x in evidence_rows
        if x[
            "evidence_type"
        ]
        ==
        "TRACK_TEMPERATURE"
    )

    air_temp_hits = sum(
        1
        for x in evidence_rows
        if x[
            "evidence_type"
        ]
        ==
        "AIR_TEMPERATURE"
    )

    print(
        "\n"
        "================================="
    )

    print(
        "DONE"
    )

    print(
        "================================="
    )

    print(
        f"Priority PDFs: "
        f"{len(candidates)}"
    )

    print(
        f"Newly downloaded: "
        f"{downloaded}"
    )

    print(
        f"Already existed: "
        f"{existing}"
    )

    print(
        f"Failed: "
        f"{failed}"
    )

    print(
        f"Evidence candidates: "
        f"{len(evidence_rows)}"
    )

    print(
        f"TRACK_TEMPERATURE "
        f"candidates: "
        f"{track_temp_hits}"
    )

    print(
        f"AIR_TEMPERATURE "
        f"candidates: "
        f"{air_temp_hits}"
    )

    print(
        f"\nManifest:"
    )

    print(
        MANIFEST_CSV
    )

    print(
        f"\nEvidence:"
    )

    print(
        EVIDENCE_CSV
    )


if __name__ == "__main__":
    main()