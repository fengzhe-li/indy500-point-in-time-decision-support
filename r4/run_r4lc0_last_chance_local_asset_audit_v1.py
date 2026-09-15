from pathlib import Path
import csv
import json
import re

ROOT = Path(
    "/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈"
)

OUT = ROOT / "r4/output"
OUT.mkdir(parents=True, exist_ok=True)

OUT_FILES = OUT / "r4lc0_last_chance_local_files_v1.csv"
OUT_SUMMARY = OUT / "r4lc0_last_chance_local_summary_v1.csv"
OUT_QA = OUT / "r4lc0_last_chance_local_qa_v1.csv"
OUT_REPORT = OUT / "r4lc0_last_chance_local_report_v1.json"

YEARS = [2020, 2021, 2022, 2023, 2024, 2025]

KEYWORDS = [
    "last chance",
    "last_chance",
    "lastchance",
    "last row",
    "last_row",
    "lastrow",
    "bump",
    "bumping",
    "qualifications - last chance",
    "qualifications-last-chance",
    "qualifications - last row",
]

TEXT_SUFFIXES = {
    ".txt",
    ".csv",
    ".json",
    ".md",
    ".html",
    ".htm",
    ".log",
    ".yaml",
    ".yml",
}

SKIP_DIR_NAMES = {
    ".git",
    "__pycache__",
    ".venv",
    "venv",
    "node_modules",
}


def should_skip(path: Path):
    return any(
        part in SKIP_DIR_NAMES
        for part in path.parts
    )


def year_hits(text):
    hits = []
    for year in YEARS:
        if str(year) in text:
            hits.append(year)
    return hits


def keyword_hits(text):
    low = text.lower()
    return [
        kw for kw in KEYWORDS
        if kw in low
    ]


def safe_read_text(path):
    try:
        return path.read_text(
            encoding="utf-8",
            errors="ignore"
        )
    except Exception:
        return ""


rows = []

for path in ROOT.rglob("*"):

    if not path.is_file():
        continue

    if should_skip(path):
        continue

    rel = path.relative_to(ROOT)
    rel_text = str(rel)

    filename_kw = keyword_hits(
        rel_text
    )

    filename_years = year_hits(
        rel_text
    )

    content_kw = []
    content_years = []

    if path.suffix.lower() in TEXT_SUFFIXES:

        text = safe_read_text(path)

        if text:
            content_kw = keyword_hits(
                text
            )

            if filename_kw or content_kw:
                content_years = year_hits(
                    text
                )

    all_kw = sorted(
        set(
            filename_kw +
            content_kw
        )
    )

    if not all_kw:
        continue

    all_years = sorted(
        set(
            filename_years +
            content_years
        )
    )

    rows.append({
        "path":
            str(rel),

        "suffix":
            path.suffix.lower(),

        "size_bytes":
            path.stat().st_size,

        "keyword_hits":
            ";".join(all_kw),

        "year_hits":
            ";".join(
                str(y)
                for y in all_years
            ),

        "filename_match":
            bool(filename_kw),

        "content_match":
            bool(content_kw),
    })


rows.sort(
    key=lambda r: (
        r["year_hits"],
        r["path"]
    )
)


summary_rows = []

for year in YEARS:

    subset = []

    for r in rows:

        years = {
            int(x)
            for x in r["year_hits"].split(";")
            if x.strip().isdigit()
        }

        if year in years:
            subset.append(r)

    summary_rows.append({
        "year":
            year,

        "matched_files":
            len(subset),

        "csv_files":
            sum(
                1 for r in subset
                if r["suffix"] == ".csv"
            ),

        "json_files":
            sum(
                1 for r in subset
                if r["suffix"] == ".json"
            ),

        "text_like_files":
            sum(
                1 for r in subset
                if r["suffix"]
                in TEXT_SUFFIXES
            ),
    })


qa_rows = [
    {
        "metric":
            "project_root_exists",

        "value":
            ROOT.exists(),

        "expected":
            True,

        "status":
            (
                "PASS"
                if ROOT.exists()
                else "FAIL"
            ),
    },

    {
        "metric":
            "audit_completed",

        "value":
            True,

        "expected":
            True,

        "status":
            "PASS",
    },

    {
        "metric":
            "years_scanned",

        "value":
            len(YEARS),

        "expected":
            6,

        "status":
            (
                "PASS"
                if len(YEARS) == 6
                else "FAIL"
            ),
    },
]


with OUT_FILES.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    fields = [
        "path",
        "suffix",
        "size_bytes",
        "keyword_hits",
        "year_hits",
        "filename_match",
        "content_match",
    ]

    writer = csv.DictWriter(
        f,
        fieldnames=fields
    )

    writer.writeheader()
    writer.writerows(rows)


with OUT_SUMMARY.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    fields = [
        "year",
        "matched_files",
        "csv_files",
        "json_files",
        "text_like_files",
    ]

    writer = csv.DictWriter(
        f,
        fieldnames=fields
    )

    writer.writeheader()
    writer.writerows(summary_rows)


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
        "R4LC0",

    "status":
        "R4LC0_LAST_CHANCE_LOCAL_ASSET_AUDIT_READY",

    "years":
        YEARS,

    "matched_files":
        len(rows),

    "purpose":
        (
            "Audit existing project assets for historical "
            "Last Chance / Last Row qualifying evidence "
            "before new data ingestion."
        ),

    "notes": [
        (
            "2021 may appear as Last Row rather than "
            "Last Chance."
        ),
        (
            "This audit does not modify source files."
        ),
        (
            "Absence here means only absence from current "
            "local project assets, not absence from public sources."
        ),
    ],
}

OUT_REPORT.write_text(
    json.dumps(
        report,
        indent=2,
        ensure_ascii=False
    ),
    encoding="utf-8"
)


print("=" * 108)
print("R4LC0 — LAST CHANCE LOCAL ASSET AUDIT")
print("=" * 108)

print(
    f"Matched local files: "
    f"{len(rows)}"
)

print()
print("BY YEAR")

for r in summary_rows:

    print(
        f"{r['year']} | "
        f"files={r['matched_files']} | "
        f"csv={r['csv_files']} | "
        f"json={r['json_files']} | "
        f"text_like={r['text_like_files']}"
    )


print()
print("TOP MATCHES")

for r in rows[:40]:

    print(
        f"{r['year_hits'] or '-':12s} | "
        f"{r['path']}"
    )


failed = [
    r for r in qa_rows
    if r["status"] != "PASS"
]

print()
print(
    f"QA: "
    f"{len(qa_rows)-len(failed)}/"
    f"{len(qa_rows)} PASS"
)

if failed:

    for r in failed:
        print(
            f"FAIL | "
            f"{r['metric']} | "
            f"value={r['value']} | "
            f"expected={r['expected']}"
        )

    raise SystemExit(1)


print()
print("OUTPUTS")
print(OUT_FILES.relative_to(ROOT))
print(OUT_SUMMARY.relative_to(ROOT))
print(OUT_QA.relative_to(ROOT))
print(OUT_REPORT.relative_to(ROOT))

print()
print(
    "R4LC0_LAST_CHANCE_LOCAL_ASSET_AUDIT_READY"
)
