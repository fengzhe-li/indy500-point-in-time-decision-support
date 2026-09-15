from pathlib import Path
import csv
import json
import re
import urllib.request

ROOT = Path(
    "/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈"
)

OUT = ROOT / "r4/output"
OUT.mkdir(parents=True, exist_ok=True)

EVIDENCE = (
    ROOT /
    "weather/evidence/last_chance_official"
)

EVIDENCE.mkdir(
    parents=True,
    exist_ok=True
)

BUNDLE_URL = (
    "https://www.indycar.com/"
    "bundles/scripts/indycar/v2/bundle"
    "?v=Y7uvJAxKjgqcUN-MzaUNJ58nW7SCLw7-yYV2trrlOd41"
)

BUNDLE_PATH = (
    EVIDENCE /
    "indycar_v2_bundle.js"
)

OUT_HITS = (
    OUT /
    "r4lc2c_bundle_endpoint_hits_v1.csv"
)

OUT_URLS = (
    OUT /
    "r4lc2c_bundle_url_candidates_v1.csv"
)

OUT_QA = (
    OUT /
    "r4lc2c_bundle_endpoint_qa_v1.csv"
)

OUT_REPORT = (
    OUT /
    "r4lc2c_bundle_endpoint_report_v1.json"
)


def fetch(url):

    req = urllib.request.Request(
        url,
        headers={
            "User-Agent":
                "Mozilla/5.0"
        },
    )

    try:

        with urllib.request.urlopen(
            req,
            timeout=30
        ) as response:

            body = response.read()

            return {
                "status":
                    response.status,

                "body":
                    body,

                "content_type":
                    response.headers.get(
                        "Content-Type",
                        ""
                    ),

                "final_url":
                    response.geturl(),

                "error":
                    "",
            }

    except Exception as exc:

        return {
            "status":
                None,

            "body":
                b"",

            "content_type":
                "",

            "final_url":
                "",

            "error":
                repr(exc),
        }


print("=" * 112)
print("R4LC2C — INDYCAR BUNDLE ENDPOINT DISCOVERY")
print("=" * 112)

result = fetch(
    BUNDLE_URL
)

print()
print(
    f"HTTP: {result['status']}"
)

print(
    f"Bytes: {len(result['body'])}"
)

print(
    f"Content-Type: {result['content_type']}"
)

if result["status"] != 200:

    raise SystemExit(
        "BUNDLE DOWNLOAD FAILED: "
        + result["error"]
    )


BUNDLE_PATH.write_bytes(
    result["body"]
)

text = result[
    "body"
].decode(
    "utf-8",
    errors="ignore"
)


PATTERNS = {
    "AJAX":
        r"ajax",

    "FETCH":
        r"fetch\s*\(",

    "AXIOS":
        r"axios",

    "API_PATH":
        r"/api/",

    "RESULTS":
        r"results",

    "SECTION_RESULTS":
        r"sectionresults|section-results|section results",

    "TOP_SECTION_TIMES":
        r"topsectiontimes|top-section-times|top section times",

    "SESSION":
        r"session",

    "EVENT":
        r"event",

    "QUALIFY":
        r"qualif",

    "ENDPOINT":
        r"endpoint",

    "GET_JSON":
        r"getjson",

    "XMLHTTP":
        r"xmlhttprequest",

    "DOT_NET_HANDLER":
        r"\.ashx|\.asmx",

    "CONTROLLER":
        r"controller",
}


hit_rows = []

for label, pattern in PATTERNS.items():

    matches = list(
        re.finditer(
            pattern,
            text,
            flags=re.IGNORECASE
        )
    )

    for i, m in enumerate(
        matches[:100],
        start=1
    ):

        start = max(
            0,
            m.start() - 300
        )

        end = min(
            len(text),
            m.end() + 500
        )

        context = (
            text[start:end]
            .replace("\n", " ")
            .replace("\r", " ")
        )

        hit_rows.append({
            "token":
                label,

            "match_index":
                i,

            "position":
                m.start(),

            "context":
                context,
        })


# =============================================================================
# Extract literal URL/path-looking strings
# =============================================================================

url_candidates = set()

patterns = [
    r'''https?://[^"'\\\s<>]+''',

    r'''["'](/[^"'\\]{3,200})["']''',

    r'''["']([^"'\\]{0,120}(?:result|session|event|qualif|section)[^"'\\]{0,120})["']''',
]

for pattern in patterns:

    for m in re.finditer(
        pattern,
        text,
        flags=re.IGNORECASE
    ):

        value = (
            m.group(1)
            if m.lastindex
            else m.group(0)
        )

        value = value.strip()

        low = value.lower()

        if any(
            token in low
            for token in [
                "result",
                "session",
                "event",
                "qualif",
                "section",
                "/api/",
            ]
        ):

            url_candidates.add(
                value
            )


url_rows = [
    {
        "candidate":
            value
    }
    for value in sorted(
        url_candidates
    )
]


# =============================================================================
# Save
# =============================================================================

with OUT_HITS.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    fields = [
        "token",
        "match_index",
        "position",
        "context",
    ]

    writer = csv.DictWriter(
        f,
        fieldnames=fields
    )

    writer.writeheader()
    writer.writerows(
        hit_rows
    )


with OUT_URLS.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    fields = [
        "candidate",
    ]

    writer = csv.DictWriter(
        f,
        fieldnames=fields
    )

    writer.writeheader()
    writer.writerows(
        url_rows
    )


counts = {}

for label in PATTERNS:

    counts[label] = sum(
        1
        for r in hit_rows
        if r["token"] == label
    )


qa_rows = [
    {
        "metric":
            "bundle_http_200",

        "value":
            result["status"],

        "expected":
            200,

        "status":
            (
                "PASS"
                if result["status"] == 200
                else "FAIL"
            ),
    },

    {
        "metric":
            "bundle_nontrivial",

        "value":
            len(result["body"]),

        "expected":
            ">10000",

        "status":
            (
                "PASS"
                if len(result["body"]) > 10000
                else "FAIL"
            ),
    },

    {
        "metric":
            "endpoint_related_hits",

        "value":
            len(hit_rows),

        "expected":
            ">0",

        "status":
            (
                "PASS"
                if len(hit_rows) > 0
                else "WARN"
            ),
    },

    {
        "metric":
            "url_candidates",

        "value":
            len(url_rows),

        "expected":
            ">0",

        "status":
            (
                "PASS"
                if len(url_rows) > 0
                else "WARN"
            ),
    },
]


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
    writer.writerows(
        qa_rows
    )


report = {
    "phase":
        "R4LC2C",

    "status":
        "R4LC2C_BUNDLE_ENDPOINT_DISCOVERY_READY",

    "bundle_url":
        BUNDLE_URL,

    "bundle_bytes":
        len(result["body"]),

    "token_counts":
        counts,

    "url_candidate_count":
        len(url_rows),

    "purpose":
        (
            "Inspect the common INDYCAR frontend bundle "
            "for dynamic historical-results data endpoints."
        ),
}


OUT_REPORT.write_text(
    json.dumps(
        report,
        indent=2,
        ensure_ascii=False
    ),
    encoding="utf-8"
)


# =============================================================================
# Console
# =============================================================================

print()
print("=" * 112)
print("TOKEN COUNTS")
print("=" * 112)

for key, value in counts.items():

    print(
        f"{key:22s} | "
        f"{value}"
    )


print()
print("=" * 112)
print("URL / ENDPOINT CANDIDATES")
print("=" * 112)

for row in url_rows[:120]:

    print(
        row["candidate"]
    )


print()
print("=" * 112)
print("MOST USEFUL CONTEXT HITS")
print("=" * 112)

priority = [
    "API_PATH",
    "AJAX",
    "FETCH",
    "GET_JSON",
    "SECTION_RESULTS",
    "TOP_SECTION_TIMES",
    "RESULTS",
    "SESSION",
]

shown = 0

for token in priority:

    subset = [
        r
        for r in hit_rows
        if r["token"] == token
    ]

    for r in subset[:8]:

        print()
        print(
            f"[{r['token']}] "
            f"position={r['position']}"
        )

        print(
            r["context"]
        )

        shown += 1

        if shown >= 30:
            break

    if shown >= 30:
        break


fails = [
    r
    for r in qa_rows
    if r["status"] == "FAIL"
]

warns = [
    r
    for r in qa_rows
    if r["status"] == "WARN"
]

print()
print(
    f"QA: "
    f"{len(qa_rows)-len(fails)-len(warns)} PASS | "
    f"{len(warns)} WARN | "
    f"{len(fails)} FAIL"
)

if fails:

    raise SystemExit(
        "R4LC2C FAILED QA"
    )


print()
print("OUTPUTS")
print(
    BUNDLE_PATH.relative_to(ROOT)
)
print(
    OUT_HITS.relative_to(ROOT)
)
print(
    OUT_URLS.relative_to(ROOT)
)
print(
    OUT_QA.relative_to(ROOT)
)
print(
    OUT_REPORT.relative_to(ROOT)
)

print()
print(
    "R4LC2C_BUNDLE_ENDPOINT_DISCOVERY_READY"
)
