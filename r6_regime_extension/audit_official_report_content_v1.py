from pathlib import Path
import re
import pandas as pd
from pypdf import PdfReader

ROOT = Path("/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈")

SRC = (
    ROOT /
    "r6_regime_extension/evidence/official_reports_v2"
)

OUT = (
    ROOT /
    "r6_regime_extension/output/report_text_audit"
)

OUT.mkdir(
    parents=True,
    exist_ok=True
)

pdfs = sorted(
    SRC.glob("*.pdf")
)

print("PDF COUNT =", len(pdfs))

KEYWORDS = [
    "attempt",
    "attempts",
    "qualifying attempt",
    "lane",
    "lane 1",
    "lane 2",
    "withdraw",
    "withdrawn",
    "requeue",
    "queue",
    "priority",
    "time of day",
    "timestamp",
    "start time",
    "end time",
    "session time",
    "lap 1",
    "lap1",
    "section",
    "results",
]

TIME_PATTERNS = {
    "clock_hhmm_ampm":
        r"\b(?:1[0-2]|0?[1-9]):[0-5]\d(?::[0-5]\d(?:\.\d+)?)?\s*(?:AM|PM)\b",

    "clock_24h":
        r"\b(?:[01]?\d|2[0-3]):[0-5]\d(?::[0-5]\d(?:\.\d+)?)?\b",

    "elapsed_mmss":
        r"\b\d{1,2}:\d{2}\.\d{1,4}\b",
}

summary_rows = []
hit_rows = []
time_rows = []

for pdf in pdfs:

    m = re.match(
        r"(\d{4})_(\d+)_",
        pdf.name
    )

    year = int(m.group(1)) if m else None
    session_id = m.group(2) if m else None

    print("\n" + "=" * 150)
    print(pdf.name)
    print("=" * 150)

    try:

        reader = PdfReader(
            str(pdf)
        )

    except Exception as e:

        print("PDF READ ERROR:", repr(e))

        summary_rows.append({
            "year": year,
            "session_id": session_id,
            "file": pdf.name,
            "status": "READ_ERROR",
            "error": repr(e),
        })

        continue

    pages_text = []

    for page_no, page in enumerate(
        reader.pages,
        start=1
    ):

        try:
            text = page.extract_text() or ""
        except Exception as e:
            text = ""

        pages_text.append(
            f"\n===== PAGE {page_no} =====\n{text}"
        )

        lower = text.lower()

        # ----------------------------------------
        # keyword contexts
        # ----------------------------------------

        for kw in KEYWORDS:

            pos = 0

            while True:

                idx = lower.find(
                    kw,
                    pos
                )

                if idx < 0:
                    break

                context = text[
                    max(0, idx - 180):
                    min(len(text), idx + 320)
                ].replace(
                    "\n",
                    " "
                )

                hit_rows.append({
                    "year": year,
                    "session_id": session_id,
                    "file": pdf.name,
                    "page": page_no,
                    "keyword": kw,
                    "context": context,
                })

                pos = idx + len(kw)

        # ----------------------------------------
        # time-like tokens
        # ----------------------------------------

        for label, pattern in TIME_PATTERNS.items():

            for match in re.finditer(
                pattern,
                text,
                flags=re.I
            ):

                token = match.group(0)

                context = text[
                    max(0, match.start() - 120):
                    min(len(text), match.end() + 200)
                ].replace(
                    "\n",
                    " "
                )

                time_rows.append({
                    "year": year,
                    "session_id": session_id,
                    "file": pdf.name,
                    "page": page_no,
                    "time_type": label,
                    "token": token,
                    "context": context,
                })

    full_text = "\n".join(
        pages_text
    )

    txt_path = (
        OUT /
        f"{pdf.stem}.txt"
    )

    txt_path.write_text(
        full_text,
        encoding="utf-8"
    )

    print(
        "pages =",
        len(reader.pages),
        "chars =",
        len(full_text)
    )

    summary_rows.append({
        "year": year,
        "session_id": session_id,
        "file": pdf.name,
        "pages": len(reader.pages),
        "chars_extracted": len(full_text),
        "contains_attempt":
            "attempt" in full_text.lower(),
        "contains_lane":
            "lane" in full_text.lower(),
        "contains_withdraw":
            "withdraw" in full_text.lower(),
        "contains_queue":
            "queue" in full_text.lower(),
        "status": "OK",
    })

summary = pd.DataFrame(
    summary_rows
)

hits = pd.DataFrame(
    hit_rows
)

times = pd.DataFrame(
    time_rows
)

SUMMARY_OUT = (
    OUT /
    "official_report_text_summary_v1.csv"
)

HITS_OUT = (
    OUT /
    "official_report_keyword_hits_v1.csv"
)

TIMES_OUT = (
    OUT /
    "official_report_time_tokens_v1.csv"
)

summary.to_csv(
    SUMMARY_OUT,
    index=False
)

hits.to_csv(
    HITS_OUT,
    index=False
)

times.to_csv(
    TIMES_OUT,
    index=False
)

print("\n" + "=" * 150)
print("PART 1 — PDF TEXT EXTRACTION SUMMARY")
print("=" * 150)

print(
    summary.to_string(
        index=False
    )
)

print("\n" + "=" * 150)
print("PART 2 — KEYWORD HIT COUNTS")
print("=" * 150)

if hits.empty:

    print("NO KEYWORD HITS")

else:

    counts = (
        hits
        .groupby(
            [
                "year",
                "file",
                "keyword"
            ]
        )
        .size()
        .reset_index(
            name="hits"
        )
    )

    print(
        counts.to_string(
            index=False
        )
    )

print("\n" + "=" * 150)
print("PART 3 — TIME TOKEN COUNTS")
print("=" * 150)

if times.empty:

    print("NO TIME TOKENS")

else:

    counts = (
        times
        .groupby(
            [
                "year",
                "file",
                "time_type"
            ]
        )
        .size()
        .reset_index(
            name="hits"
        )
    )

    print(
        counts.to_string(
            index=False
        )
    )

print("\n" + "=" * 150)
print("PART 4 — CLOCK-TIME EXAMPLES")
print("=" * 150)

if not times.empty:

    clock = times[
        times["time_type"]
        .isin(
            [
                "clock_hhmm_ampm",
                "clock_24h",
            ]
        )
    ]

    if clock.empty:

        print(
            "NO CLOCK-TIME CANDIDATES"
        )

    else:

        print(
            clock[
                [
                    "year",
                    "file",
                    "page",
                    "time_type",
                    "token",
                    "context",
                ]
            ]
            .head(100)
            .to_string(
                index=False
            )
        )

print("\nOUTPUTS:")
print(SUMMARY_OUT.relative_to(ROOT))
print(HITS_OUT.relative_to(ROOT))
print(TIMES_OUT.relative_to(ROOT))

print(
    "\nR6_OFFICIAL_REPORT_CONTENT_AUDIT_V1_COMPLETE"
)
