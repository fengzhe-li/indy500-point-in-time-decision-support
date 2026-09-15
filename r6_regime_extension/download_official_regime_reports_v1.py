from pathlib import Path
import json
import requests
import pandas as pd
from urllib.parse import urljoin

ROOT = Path("/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈")

SRC = (
    ROOT /
    "r6_regime_extension/evidence/official_api_v2"
)

OUT = (
    ROOT /
    "r6_regime_extension/evidence/official_reports"
)

OUT.mkdir(
    parents=True,
    exist_ok=True
)

BASE = "https://www.indycar.com/"

TARGETS = {
    2018: 5320,
    2019: 5565,
    2025: 6656,
    2026: 6835,
}

HEADERS = {
    "User-Agent":
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 Chrome/153 Safari/537.36",
}

s = requests.Session()
s.headers.update(HEADERS)

def walk(obj, path="root"):

    out = []

    if isinstance(obj, dict):

        for k, v in obj.items():

            child = f"{path}.{k}"

            if isinstance(v, (str, int, float, bool)) or v is None:

                out.append({
                    "path": child,
                    "key": k,
                    "value": v,
                })

            out.extend(
                walk(
                    v,
                    child
                )
            )

    elif isinstance(obj, list):

        for i, v in enumerate(obj):

            out.extend(
                walk(
                    v,
                    f"{path}[{i}]"
                )
            )

    return out


def normalize_url(value):

    if not isinstance(value, str):
        return None

    v = value.strip()

    if ".pdf" not in v.lower():
        return None

    # common relative forms
    if v.startswith("//"):
        return "https:" + v

    if v.startswith("http://") or v.startswith("https://"):
        return v

    if v.startswith("/"):
        return urljoin(
            BASE,
            v
        )

    return urljoin(
        BASE,
        v
    )


manifest = []

print("=" * 150)
print("PART 1 — SESSION REPORT INVENTORY")
print("=" * 150)

for year, sid in TARGETS.items():

    p = (
        SRC /
        f"{year}_session_{sid}_raw.json"
    )

    print("\n" + "-" * 120)
    print("YEAR", year, "SESSION", sid)
    print("-" * 120)

    if not p.exists():

        print("MISSING JSON:", p)

        manifest.append({
            "year": year,
            "session_id": sid,
            "status": "MISSING_JSON",
        })

        continue

    with open(
        p,
        "r",
        encoding="utf-8"
    ) as f:

        obj = json.load(f)

    print(
        "SessionName =",
        obj.get("SessionName")
        if isinstance(obj, dict)
        else None
    )

    if isinstance(obj, dict):

        reports = obj.get(
            "SessionReports"
        )

        print(
            "SessionReports type =",
            type(reports).__name__
        )

        print(
            "SessionReports raw ="
        )

        print(
            json.dumps(
                reports,
                indent=2,
                ensure_ascii=False
            )
        )

    flat = walk(obj)

    pdf_candidates = []

    for row in flat:

        url = normalize_url(
            row["value"]
        )

        if url:

            pdf_candidates.append({
                "path": row["path"],
                "key": row["key"],
                "raw_value": row["value"],
                "url": url,
            })

    # dedupe by URL
    seen = set()
    deduped = []

    for x in pdf_candidates:

        if x["url"] in seen:
            continue

        seen.add(
            x["url"]
        )

        deduped.append(
            x
        )

    print(
        "\nPDF CANDIDATES =",
        len(deduped)
    )

    for x in deduped:
        print(
            x["path"],
            "->",
            x["url"]
        )

    # --------------------------------------------------------
    # download
    # --------------------------------------------------------

    for i, x in enumerate(deduped, start=1):

        url = x["url"]

        filename = (
            url.split("?")[0]
            .rstrip("/")
            .split("/")[-1]
        )

        dest = (
            OUT /
            f"{year}_{sid}_{filename}"
        )

        try:

            r = s.get(
                url,
                timeout=30
            )

            print(
                "GET",
                url,
                "status=",
                r.status_code,
                "type=",
                r.headers.get(
                    "content-type"
                ),
                "bytes=",
                len(r.content)
            )

            r.raise_for_status()

            # avoid silently saving HTML error pages
            is_pdf = (
                r.content[:4]
                == b"%PDF"
            )

            if not is_pdf:

                print(
                    "NOT PDF:",
                    r.text[:300]
                )

                manifest.append({
                    "year": year,
                    "session_id": sid,
                    "session_name":
                        obj.get("SessionName"),
                    "report_path":
                        x["path"],
                    "source_url":
                        url,
                    "status":
                        "NON_PDF_RESPONSE",
                    "http_status":
                        r.status_code,
                    "content_type":
                        r.headers.get(
                            "content-type"
                        ),
                })

                continue

            dest.write_bytes(
                r.content
            )

            print(
                "SAVED:",
                dest.relative_to(ROOT)
            )

            manifest.append({
                "year": year,
                "session_id": sid,
                "session_name":
                    obj.get("SessionName"),
                "report_path":
                    x["path"],
                "source_url":
                    url,
                "local_path":
                    str(
                        dest.relative_to(
                            ROOT
                        )
                    ),
                "status":
                    "DOWNLOADED",
                "http_status":
                    r.status_code,
                "bytes":
                    len(r.content),
            })

        except Exception as e:

            print(
                "ERROR:",
                repr(e)
            )

            manifest.append({
                "year": year,
                "session_id": sid,
                "session_name":
                    obj.get("SessionName"),
                "report_path":
                    x["path"],
                "source_url":
                    url,
                "status":
                    "DOWNLOAD_ERROR",
                "error":
                    repr(e),
            })

manifest_df = pd.DataFrame(
    manifest
)

MANIFEST = (
    OUT /
    "official_regime_report_download_manifest_v1.csv"
)

manifest_df.to_csv(
    MANIFEST,
    index=False
)

print("\n" + "=" * 150)
print("PART 2 — DOWNLOAD SUMMARY")
print("=" * 150)

if not manifest_df.empty:

    cols = [
        c
        for c in [
            "year",
            "session_id",
            "session_name",
            "status",
            "source_url",
            "local_path",
            "bytes",
        ]
        if c in manifest_df.columns
    ]

    print(
        manifest_df[
            cols
        ]
        .to_string(
            index=False
        )
    )

    print(
        "\nSTATUS COUNTS:"
    )

    print(
        manifest_df.groupby(
            [
                "year",
                "status"
            ]
        )
        .size()
        .to_string()
    )

print("\nOUTPUT:")
print(
    MANIFEST.relative_to(ROOT)
)

print(
    "\nR6_OFFICIAL_REGIME_REPORT_DOWNLOAD_V1_COMPLETE"
)
