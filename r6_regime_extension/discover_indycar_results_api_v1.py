from pathlib import Path
import requests
import re
from urllib.parse import urljoin

ROOT = Path("/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈")
OUT = ROOT / "r6_regime_extension/evidence/official_results"
OUT.mkdir(parents=True, exist_ok=True)

PAGE_URL = (
    "https://www.indycar.com/results/ntt-indycar-series/"
    "2026/110th-running-of-the-indianapolis-500/"
    "combined-qualifying"
)

HEADERS = {
    "User-Agent":
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 Chrome/153 Safari/537.36"
}

# ============================================================
# page
# ============================================================

r = requests.get(
    PAGE_URL,
    headers=HEADERS,
    timeout=30
)

r.raise_for_status()

html = r.text

print("=" * 140)
print("PART 1 — PAGE METADATA")
print("=" * 140)

for field in [
    "hdnSeries",
    "hdnSeriesName",
    "hdnYear",
    "hdnEvent",
    "hdnSession",
]:

    m = re.search(
        rf'id="{field}"\s+value="([^"]+)"',
        html
    )

    print(
        field,
        "=",
        m.group(1) if m else None
    )

# ============================================================
# scripts
# ============================================================

scripts = re.findall(
    r'<script[^>]+src=["\']([^"\']+)["\']',
    html,
    flags=re.I
)

print("\n" + "=" * 140)
print("PART 2 — SCRIPT SOURCES")
print("=" * 140)

for s in scripts:
    print(s)

bundle_candidates = [
    s for s in scripts
    if "bundle" in s.lower()
    or "result" in s.lower()
    or "indycar" in s.lower()
]

all_js = []

for i, src in enumerate(bundle_candidates):

    url = urljoin(
        PAGE_URL,
        src
    )

    try:

        rr = requests.get(
            url,
            headers=HEADERS,
            timeout=30
        )

        rr.raise_for_status()

        text = rr.text

        all_js.append(
            (url, text)
        )

        outfile = (
            OUT /
            f"indycar_results_script_{i}.js"
        )

        outfile.write_text(
            text,
            encoding="utf-8"
        )

        print(
            "DOWNLOADED",
            url,
            "chars=",
            len(text)
        )

    except Exception as e:

        print(
            "SCRIPT ERROR",
            url,
            e
        )

# ============================================================
# endpoint discovery
# ============================================================

print("\n" + "=" * 140)
print("PART 3 — API / AJAX ENDPOINT CANDIDATES")
print("=" * 140)

patterns = [
    r'["\']([^"\']*/api/[^"\']+)["\']',
    r'["\']([^"\']*results[^"\']*(?:get|load|race|qual|session)[^"\']*)["\']',
    r'url\s*:\s*["\']([^"\']+)["\']',
    r'fetch\(\s*["\']([^"\']+)["\']',
]

hits = set()

for url, js in all_js:

    for pattern in patterns:

        for m in re.finditer(
            pattern,
            js,
            flags=re.I
        ):

            candidate = m.group(1)

            if len(candidate) < 250:

                hits.add(candidate)

for h in sorted(hits):

    if any(
        x in h.lower()
        for x in [
            "result",
            "race",
            "qual",
            "session",
            "event",
            "api",
        ]
    ):

        print(h)

# ============================================================
# keyword context
# ============================================================

print("\n" + "=" * 140)
print("PART 4 — RESULTS-JS KEYWORD CONTEXT")
print("=" * 140)

keywords = [
    "qualifying-results",
    "qualifyingResults",
    "race-results",
    "raceResults",
    "combined-qualifying",
    "results-btn",
    "section-results",
    "top-section-times",
    "hdnSession",
    "hdnEvent",
    "AverageSpeed",
    "Lap1",
    "Lap 1",
]

for url, js in all_js:

    print("\nSOURCE:", url)

    for kw in keywords:

        pos = js.lower().find(
            kw.lower()
        )

        if pos >= 0:

            start = max(
                0,
                pos - 500
            )

            end = min(
                len(js),
                pos + 1200
            )

            snippet = js[
                start:end
            ]

            print(
                "\nKEYWORD:",
                kw
            )

            print(
                snippet
            )

            print(
                "\n" + "-" * 100
            )

print("\nR6_INDIYCAR_RESULTS_API_DISCOVERY_V1_COMPLETE")
