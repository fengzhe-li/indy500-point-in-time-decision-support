from pathlib import Path
import json
import requests
import pandas as pd

ROOT = Path("/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈")

SRC = ROOT / "r6_regime_extension/evidence/official_api_v2"
OUT = ROOT / "r6_regime_extension/evidence/official_reports_v2"
OUT.mkdir(parents=True, exist_ok=True)

TARGETS = {
    2018: 5320,
    2019: 5565,
    2025: 6656,
    2026: 6835,
}

HEADERS = {
    "User-Agent":
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 Chrome/153 Safari/537.36"
}

s = requests.Session()
s.headers.update(HEADERS)

def candidate_urls(raw_path):

    p = str(raw_path).lstrip("/")

    return [
        "http://www.imscdn.com/" + p,
        "https://www.imscdn.com/" + p,
        "http://imscdn.com/" + p,
        "https://imscdn.com/" + p,
        "https://www.indycar.com/" + p,
    ]


manifest = []

for year, sid in TARGETS.items():

    src_json = SRC / f"{year}_session_{sid}_raw.json"

    print("\n" + "=" * 140)
    print("YEAR", year, "SESSION", sid)
    print("=" * 140)

    if not src_json.exists():
        print("MISSING", src_json)
        continue

    with open(src_json, "r", encoding="utf-8") as f:
        obj = json.load(f)

    reports = obj.get("SessionReports", []) or []

    for report in reports:

        raw_path = report.get("Url")

        if not raw_path or ".pdf" not in raw_path.lower():
            continue

        name = report.get("Name")
        filename = raw_path.split("/")[-1]

        print("\nREPORT:", name)
        print("RAW:", raw_path)

        success = False

        for url in candidate_urls(raw_path):

            try:

                r = s.get(
                    url,
                    timeout=30,
                    allow_redirects=True
                )

                is_pdf = (
                    r.status_code == 200
                    and r.content[:4] == b"%PDF"
                )

                print(
                    r.status_code,
                    len(r.content),
                    r.url,
                    "PDF=",
                    is_pdf
                )

                if not is_pdf:
                    continue

                dest = OUT / f"{year}_{sid}_{filename}"

                dest.write_bytes(
                    r.content
                )

                print(
                    "SUCCESS ->",
                    dest.relative_to(ROOT)
                )

                manifest.append({
                    "year": year,
                    "session_id": sid,
                    "session_name": obj.get("SessionName"),
                    "report_name": name,
                    "raw_path": raw_path,
                    "resolved_url": r.url,
                    "local_path": str(dest.relative_to(ROOT)),
                    "bytes": len(r.content),
                    "status": "DOWNLOADED",
                })

                success = True
                break

            except Exception as e:

                print(
                    "ERROR",
                    url,
                    repr(e)
                )

        if not success:

            manifest.append({
                "year": year,
                "session_id": sid,
                "session_name": obj.get("SessionName"),
                "report_name": name,
                "raw_path": raw_path,
                "resolved_url": None,
                "local_path": None,
                "bytes": None,
                "status": "UNRESOLVED",
            })


manifest_df = pd.DataFrame(
    manifest
)

manifest_path = (
    OUT /
    "official_regime_report_download_manifest_v2.csv"
)

manifest_df.to_csv(
    manifest_path,
    index=False
)

print("\n" + "=" * 140)
print("FINAL SUMMARY")
print("=" * 140)

if not manifest_df.empty:

    print(
        manifest_df[
            [
                "year",
                "report_name",
                "status",
                "resolved_url",
                "local_path",
            ]
        ].to_string(index=False)
    )

    print("\nSTATUS COUNTS")

    print(
        manifest_df.groupby(
            ["year", "status"]
        )
        .size()
        .to_string()
    )

print("\nOUTPUT:")
print(manifest_path.relative_to(ROOT))

print("\nR6_OFFICIAL_REGIME_REPORT_DOWNLOAD_V2_COMPLETE")
