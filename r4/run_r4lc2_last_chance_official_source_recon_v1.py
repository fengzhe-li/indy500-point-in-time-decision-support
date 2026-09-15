from pathlib import Path
import csv
import json
import re
import urllib.request
from urllib.parse import urljoin

ROOT = Path(
    "/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈"
)

OUT = ROOT / "r4/output"
EVIDENCE = (
    ROOT /
    "weather/evidence/last_chance_official"
)

OUT.mkdir(parents=True, exist_ok=True)
EVIDENCE.mkdir(parents=True, exist_ok=True)

OUT_REGISTRY = (
    OUT /
    "r4lc2_last_chance_official_source_registry_v1.csv"
)

OUT_LINKS = (
    OUT /
    "r4lc2_last_chance_official_report_links_v1.csv"
)

OUT_QA = (
    OUT /
    "r4lc2_last_chance_official_source_qa_v1.csv"
)

OUT_REPORT = (
    OUT /
    "r4lc2_last_chance_official_source_report_v1.json"
)


SOURCES = [
    {
        "year": 2021,
        "session_regime": "LAST_ROW",
        "session_name": "Qualifications - Last Row",
        "url": (
            "https://www.indycar.com/"
            "results/ntt-indycar-series/2021/"
            "105th-running-of-the-indianapolis-500/"
            "qualifications---last-row"
        ),
        "development_role":
            "LAST_CHANCE_ONLY_AND_FUSED_DEVELOPMENT",
    },
    {
        "year": 2023,
        "session_regime": "LAST_CHANCE",
        "session_name": "Qualifications - Last Chance",
        "url": (
            "https://www.indycar.com/"
            "results/ntt-indycar-series/2023/"
            "107th-running-of-the-indianapolis-500/"
            "qualifications---last-chance"
        ),
        "development_role":
            "LAST_CHANCE_ONLY_AND_FUSED_DEVELOPMENT",
    },
    {
        "year": 2024,
        "session_regime": "LAST_CHANCE",
        "session_name": "Qualifications - Last Chance",
        "url": (
            "https://www.indycar.com/"
            "results/ntt-indycar-series/2024/"
            "108th-running-of-the-indianapolis-500/"
            "qualifications---last-chance"
        ),
        "development_role":
            "QUALITY_GATED_DEVELOPMENT_OR_DEGRADED_VALIDATION",
    },
]


def fetch(url):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 "
                "Indy500AcademicResearch/1.0"
            )
        },
    )

    try:
        with urllib.request.urlopen(
            req,
            timeout=30
        ) as response:

            body = response.read()

            content_type = (
                response.headers.get(
                    "Content-Type",
                    ""
                )
            )

            return {
                "status": response.status,
                "content_type": content_type,
                "body": body,
                "error": "",
                "final_url": response.geturl(),
            }

    except Exception as exc:
        return {
            "status": None,
            "content_type": "",
            "body": b"",
            "error": repr(exc),
            "final_url": "",
        }


def extract_links(html, base_url):
    hrefs = re.findall(
        r'''href=["']([^"']+)["']''',
        html,
        flags=re.IGNORECASE,
    )

    links = []

    for href in hrefs:

        full = urljoin(
            base_url,
            href
        )

        low = full.lower()

        relevant = any(
            token in low
            for token in [
                ".pdf",
                "result",
                "section",
                "report",
                "qual",
                "indy500",
                "indy-500",
            ]
        )

        if relevant:
            links.append(full)

    return sorted(
        set(links)
    )


registry_rows = []
link_rows = []

for source in SOURCES:

    year = source["year"]
    url = source["url"]

    print()
    print(
        f"FETCHING {year}: "
        f"{source['session_name']}"
    )

    result = fetch(url)

    html_path = (
        EVIDENCE /
        f"{year}_last_chance_official_page.html"
    )

    if result["body"]:

        html_path.write_bytes(
            result["body"]
        )

    body_text = (
        result["body"]
        .decode(
            "utf-8",
            errors="ignore"
        )
        if result["body"]
        else ""
    )

    links = extract_links(
        body_text,
        result["final_url"] or url
    )

    for link in links:

        low = link.lower()

        if ".pdf" in low:
            link_class = "PDF"
        elif "section" in low:
            link_class = "SECTION_REPORT_OR_PAGE"
        elif "result" in low:
            link_class = "RESULT_OR_REPORT"
        elif "report" in low:
            link_class = "REPORT"
        else:
            link_class = "OTHER_RELEVANT"

        link_rows.append({
            "year":
                year,

            "session_regime":
                source["session_regime"],

            "link_class":
                link_class,

            "url":
                link,
        })

    registry_rows.append({
        "year":
            year,

        "session_regime":
            source["session_regime"],

        "session_name":
            source["session_name"],

        "development_role":
            source["development_role"],

        "official_url":
            url,

        "http_status":
            result["status"],

        "content_type":
            result["content_type"],

        "final_url":
            result["final_url"],

        "downloaded_bytes":
            len(result["body"]),

        "saved_html":
            str(
                html_path.relative_to(ROOT)
            )
            if result["body"]
            else "",

        "relevant_links_found":
            len(links),

        "error":
            result["error"],
    })


with OUT_REGISTRY.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    fields = [
        "year",
        "session_regime",
        "session_name",
        "development_role",
        "official_url",
        "http_status",
        "content_type",
        "final_url",
        "downloaded_bytes",
        "saved_html",
        "relevant_links_found",
        "error",
    ]

    writer = csv.DictWriter(
        f,
        fieldnames=fields
    )

    writer.writeheader()
    writer.writerows(registry_rows)


with OUT_LINKS.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    fields = [
        "year",
        "session_regime",
        "link_class",
        "url",
    ]

    writer = csv.DictWriter(
        f,
        fieldnames=fields
    )

    writer.writeheader()
    writer.writerows(link_rows)


qa_rows = []

for row in registry_rows:

    status_ok = (
        row["http_status"] == 200
    )

    bytes_ok = (
        row["downloaded_bytes"] > 1000
    )

    qa_rows.append({
        "metric":
            f"{row['year']}_official_page_http_200",

        "value":
            row["http_status"],

        "expected":
            200,

        "status":
            "PASS"
            if status_ok
            else "FAIL",
    })

    qa_rows.append({
        "metric":
            f"{row['year']}_official_page_nontrivial",

        "value":
            row["downloaded_bytes"],

        "expected":
            ">1000",

        "status":
            "PASS"
            if bytes_ok
            else "FAIL",
    })


with OUT_QA.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    fields = [
        "metric",
        "value",
        "expected",
        "status",
    ]

    writer = csv.DictWriter(
        f,
        fieldnames=fields
    )

    writer.writeheader()
    writer.writerows(qa_rows)


report = {
    "phase":
        "R4LC2",

    "status":
        "R4LC2_LAST_CHANCE_OFFICIAL_SOURCE_RECON_READY",

    "development_years":
        [
            2021,
            2023,
            2024,
        ],

    "reserved_cross_technical_validation_year":
        2025,

    "official_pages_checked":
        len(registry_rows),

    "relevant_links_discovered":
        len(link_rows),

    "purpose":
        (
            "Establish official Last Row / Last Chance "
            "source availability before attempt-level "
            "canonical ingestion."
        ),

    "research_policy": {
        "2021":
            "development",
        "2023":
            "development",
        "2024":
            (
                "quality-gated development; "
                "excluded low-quality observations may "
                "serve degraded validation"
            ),
        "2025":
            (
                "do not use for parameter fitting; "
                "reserve for cross-technical-regime validation"
            ),
    },
}

OUT_REPORT.write_text(
    json.dumps(
        report,
        indent=2,
        ensure_ascii=False
    ),
    encoding="utf-8"
)


print()
print("=" * 110)
print("R4LC2 OFFICIAL PAGE SUMMARY")
print("=" * 110)

for row in registry_rows:

    print(
        f"{row['year']} | "
        f"HTTP={row['http_status']} | "
        f"bytes={row['downloaded_bytes']} | "
        f"links={row['relevant_links_found']} | "
        f"regime={row['session_regime']}"
    )


print()
print("=" * 110)
print("R4LC2 REPORT LINK CANDIDATES")
print("=" * 110)

for row in link_rows:

    print(
        f"{row['year']} | "
        f"{row['link_class']:24s} | "
        f"{row['url']}"
    )


failed = [
    r
    for r in qa_rows
    if r["status"] != "PASS"
]

print()
print(
    f"QA: "
    f"{len(qa_rows)-len(failed)}/"
    f"{len(qa_rows)} PASS"
)

if failed:

    print("FAILED QA")

    for r in failed:

        print(
            f"{r['metric']} | "
            f"value={r['value']} | "
            f"expected={r['expected']}"
        )

    raise SystemExit(1)


print()
print("OUTPUTS")
print(
    OUT_REGISTRY.relative_to(ROOT)
)
print(
    OUT_LINKS.relative_to(ROOT)
)
print(
    OUT_QA.relative_to(ROOT)
)
print(
    OUT_REPORT.relative_to(ROOT)
)

print()
print(
    "R4LC2_LAST_CHANCE_OFFICIAL_SOURCE_RECON_READY"
)
