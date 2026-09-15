from pathlib import Path
import csv
import hashlib
import json
import re

ROOT = Path(
    "/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈"
)

EVIDENCE = (
    ROOT /
    "weather/evidence/last_chance_official"
)

OUT = ROOT / "r4/output"
OUT.mkdir(parents=True, exist_ok=True)

OUT_HTML_AUDIT = (
    OUT /
    "r4lc2b_last_chance_html_audit_v1.csv"
)

OUT_SCRIPTS = (
    OUT /
    "r4lc2b_last_chance_script_sources_v1.csv"
)

OUT_URLS = (
    OUT /
    "r4lc2b_last_chance_embedded_urls_v1.csv"
)

OUT_TOKENS = (
    OUT /
    "r4lc2b_last_chance_dynamic_tokens_v1.csv"
)

OUT_QA = (
    OUT /
    "r4lc2b_last_chance_dynamic_source_qa_v1.csv"
)

OUT_REPORT = (
    OUT /
    "r4lc2b_last_chance_dynamic_source_report_v1.json"
)


FILES = {
    2021:
        EVIDENCE /
        "2021_last_chance_official_page.html",

    2023:
        EVIDENCE /
        "2023_last_chance_official_page.html",

    2024:
        EVIDENCE /
        "2024_last_chance_official_page.html",
}


SEARCH_PATTERNS = {
    "NEXT_DATA":
        r"__NEXT_DATA__",

    "NEXT_STATIC":
        r"_next/static",

    "API":
        r"\bapi\b",

    "GRAPHQL":
        r"graphql",

    "RESULTS":
        r"results",

    "SECTION_RESULTS":
        r"section results",

    "TOP_SECTION_TIMES":
        r"top section times",

    "SESSION":
        r"session",

    "EVENT":
        r"event",

    "QUALIFICATIONS":
        r"qualifications",

    "LAST_CHANCE":
        r"last chance",

    "LAST_ROW":
        r"last row",

    "PDF":
        r"\.pdf",

    "JSON":
        r"\.json",
}


def sha256_bytes(data):
    return hashlib.sha256(
        data
    ).hexdigest()


def normalize_html(text):
    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


def extract_script_srcs(text):
    return sorted(
        set(
            re.findall(
                r'''<script[^>]+src=["']([^"']+)["']''',
                text,
                flags=re.IGNORECASE,
            )
        )
    )


def extract_urls(text):
    candidates = re.findall(
        r'''https?://[^\s"'<>\\]+''',
        text,
        flags=re.IGNORECASE,
    )

    cleaned = []

    for url in candidates:
        url = (
            url
            .replace("&amp;", "&")
            .rstrip("),.;]")
        )

        cleaned.append(
            url
        )

    return sorted(
        set(cleaned)
    )


def interesting_url(url):
    low = url.lower()

    tokens = [
        "api",
        "result",
        "qual",
        "session",
        "event",
        "pdf",
        "json",
        "graphql",
        "indycar",
    ]

    return any(
        token in low
        for token in tokens
    )


html_rows = []
script_rows = []
url_rows = []
token_rows = []

texts = {}


for year, path in FILES.items():

    if not path.exists():
        raise SystemExit(
            f"MISSING HTML: {path}"
        )

    raw = path.read_bytes()

    text = raw.decode(
        "utf-8",
        errors="ignore"
    )

    texts[year] = text

    normalized = normalize_html(
        text
    )

    scripts = extract_script_srcs(
        text
    )

    urls = [
        u
        for u in extract_urls(text)
        if interesting_url(u)
    ]

    html_rows.append({
        "year":
            year,

        "bytes":
            len(raw),

        "sha256":
            sha256_bytes(raw),

        "normalized_characters":
            len(normalized),

        "script_src_count":
            len(scripts),

        "interesting_url_count":
            len(urls),
    })

    for src in scripts:

        script_rows.append({
            "year":
                year,

            "script_src":
                src,
        })

    for url in urls:

        url_rows.append({
            "year":
                year,

            "url":
                url,
        })

    low = text.lower()

    for label, pattern in SEARCH_PATTERNS.items():

        matches = list(
            re.finditer(
                pattern,
                low,
                flags=re.IGNORECASE
            )
        )

        contexts = []

        for m in matches[:5]:

            start = max(
                0,
                m.start() - 100
            )

            end = min(
                len(text),
                m.end() + 180
            )

            context = (
                text[start:end]
                .replace("\n", " ")
                .replace("\r", " ")
            )

            contexts.append(
                context
            )

        token_rows.append({
            "year":
                year,

            "token":
                label,

            "match_count":
                len(matches),

            "sample_context":
                " || ".join(
                    contexts
                ),
        })


# =============================================================================
# Cross-year HTML similarity
# =============================================================================

similarity_rows = []

years = sorted(
    texts
)

for i, y1 in enumerate(years):

    for y2 in years[i + 1:]:

        a = normalize_html(
            texts[y1]
        )

        b = normalize_html(
            texts[y2]
        )

        shorter = min(
            len(a),
            len(b)
        )

        same_prefix = 0

        for x, y in zip(a, b):

            if x == y:
                same_prefix += 1
            else:
                break

        ratio = (
            same_prefix / shorter
            if shorter
            else 0.0
        )

        similarity_rows.append({
            "year_a":
                y1,

            "year_b":
                y2,

            "same_prefix_characters":
                same_prefix,

            "shorter_document_characters":
                shorter,

            "same_prefix_ratio":
                ratio,
        })


# =============================================================================
# Save
# =============================================================================

with OUT_HTML_AUDIT.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    fields = [
        "year",
        "bytes",
        "sha256",
        "normalized_characters",
        "script_src_count",
        "interesting_url_count",
    ]

    writer = csv.DictWriter(
        f,
        fieldnames=fields
    )

    writer.writeheader()
    writer.writerows(
        html_rows
    )


with OUT_SCRIPTS.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    fields = [
        "year",
        "script_src",
    ]

    writer = csv.DictWriter(
        f,
        fieldnames=fields
    )

    writer.writeheader()
    writer.writerows(
        script_rows
    )


with OUT_URLS.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    fields = [
        "year",
        "url",
    ]

    writer = csv.DictWriter(
        f,
        fieldnames=fields
    )

    writer.writeheader()
    writer.writerows(
        url_rows
    )


with OUT_TOKENS.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    fields = [
        "year",
        "token",
        "match_count",
        "sample_context",
    ]

    writer = csv.DictWriter(
        f,
        fieldnames=fields
    )

    writer.writeheader()
    writer.writerows(
        token_rows
    )


OUT_SIMILARITY = (
    OUT /
    "r4lc2b_last_chance_html_similarity_v1.csv"
)

with OUT_SIMILARITY.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    fields = [
        "year_a",
        "year_b",
        "same_prefix_characters",
        "shorter_document_characters",
        "same_prefix_ratio",
    ]

    writer = csv.DictWriter(
        f,
        fieldnames=fields
    )

    writer.writeheader()
    writer.writerows(
        similarity_rows
    )


# =============================================================================
# QA
# =============================================================================

qa_rows = []

for row in html_rows:

    qa_rows.append({
        "metric":
            f"{row['year']}_html_exists_and_nonempty",

        "value":
            row["bytes"],

        "expected":
            ">1000",

        "status":
            (
                "PASS"
                if row["bytes"] > 1000
                else "FAIL"
            ),
    })


has_dynamic_signal = any(
    int(r["match_count"]) > 0
    for r in token_rows
    if r["token"] in {
        "NEXT_DATA",
        "NEXT_STATIC",
        "API",
        "GRAPHQL",
        "SESSION",
        "EVENT",
        "RESULTS",
    }
)

qa_rows.append({
    "metric":
        "dynamic_source_signal_present",

    "value":
        has_dynamic_signal,

    "expected":
        True,

    "status":
        (
            "PASS"
            if has_dynamic_signal
            else "WARN"
        ),
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
    writer.writerows(
        qa_rows
    )


report = {
    "phase":
        "R4LC2B",

    "status":
        "R4LC2B_LAST_CHANCE_DYNAMIC_SOURCE_DISCOVERY_READY",

    "interpretation_policy":
        (
            "HTTP 200 alone does not establish availability "
            "of attempt-level historical results. Static HTML "
            "must be inspected for embedded data or dynamic "
            "data-source references before canonical ingestion."
        ),

    "years":
        years,

    "html_audit":
        html_rows,

    "similarity":
        similarity_rows,
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

print("=" * 112)
print("R4LC2B — LAST CHANCE DYNAMIC SOURCE DISCOVERY")
print("=" * 112)

print()
print("HTML AUDIT")

for row in html_rows:

    print(
        f"{row['year']} | "
        f"bytes={row['bytes']} | "
        f"scripts={row['script_src_count']} | "
        f"interesting_urls={row['interesting_url_count']} | "
        f"sha={row['sha256'][:16]}"
    )


print()
print("CROSS-YEAR SIMILARITY")

for row in similarity_rows:

    print(
        f"{row['year_a']} vs {row['year_b']} | "
        f"same-prefix="
        f"{row['same_prefix_characters']} | "
        f"ratio="
        f"{row['same_prefix_ratio']:.6f}"
    )


print()
print("DYNAMIC TOKEN COUNTS")

interesting_tokens = {
    "NEXT_DATA",
    "NEXT_STATIC",
    "API",
    "GRAPHQL",
    "RESULTS",
    "SECTION_RESULTS",
    "TOP_SECTION_TIMES",
    "SESSION",
    "EVENT",
    "QUALIFICATIONS",
    "LAST_CHANCE",
    "LAST_ROW",
    "JSON",
}

for row in token_rows:

    if (
        row["token"] in interesting_tokens
        and int(row["match_count"]) > 0
    ):

        print(
            f"{row['year']} | "
            f"{row['token']:20s} | "
            f"matches={row['match_count']}"
        )


print()
print("SCRIPT SOURCES")

for row in script_rows[:60]:

    print(
        f"{row['year']} | "
        f"{row['script_src']}"
    )


print()
print("INTERESTING EMBEDDED URLS")

for row in url_rows[:80]:

    print(
        f"{row['year']} | "
        f"{row['url']}"
    )


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

    print("FAILED QA")

    for r in fails:

        print(
            f"{r['metric']} | "
            f"value={r['value']} | "
            f"expected={r['expected']}"
        )

    raise SystemExit(1)


print()
print("OUTPUTS")
print(OUT_HTML_AUDIT.relative_to(ROOT))
print(OUT_SIMILARITY.relative_to(ROOT))
print(OUT_SCRIPTS.relative_to(ROOT))
print(OUT_URLS.relative_to(ROOT))
print(OUT_TOKENS.relative_to(ROOT))
print(OUT_QA.relative_to(ROOT))
print(OUT_REPORT.relative_to(ROOT))

print()
print(
    "R4LC2B_LAST_CHANCE_DYNAMIC_SOURCE_DISCOVERY_READY"
)
