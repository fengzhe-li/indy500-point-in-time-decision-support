from pathlib import Path
import pandas as pd
import json
import re
import csv

ROOT = Path("/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈")
OUT = ROOT / "r5/recovery"
OUT.mkdir(parents=True, exist_ok=True)

targets = {
    2021: {
        "Charlie Kimball": ["Kimball"],
        "RC Enerson": ["Enerson"],
    },
    2023: {
        "Jack Harvey": ["Harvey"],
    },
    2024: {
        "Marcus Ericsson": ["Ericsson"],
        "Nolan Siegel": ["Siegel"],
    },
}

# speed-like pattern, intentionally broad
speed_rx = re.compile(r"\b(?:22[0-9]|23[0-9])\.\d{3}\b")
lap_rx = re.compile(r"\b(?:3[89]|40)\.\d{4}\b")

rows = []

def add_hit(year, driver, path, source_type, context, line_no=None):
    speeds = speed_rx.findall(context)
    laps = lap_rx.findall(context)

    rows.append({
        "year": year,
        "driver_name": driver,
        "source_path": str(path.relative_to(ROOT)),
        "source_type": source_type,
        "line_or_row": line_no,
        "speed_hits_mph": ";".join(speeds),
        "lap_time_hits_s": ";".join(laps),
        "context": context[:2500],
    })

# ---------------------------------------------------------
# 1. Search text-like files
# ---------------------------------------------------------

roots = [
    ROOT / "r4",
    ROOT / "weather",
]

extensions = {".txt", ".md", ".json", ".html"}

for base in roots:
    if not base.exists():
        continue

    for p in base.rglob("*"):
        if not p.is_file() or p.suffix.lower() not in extensions:
            continue

        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        lines = text.splitlines()

        for year, drivers in targets.items():
            # prefer year-specific evidence where year appears in path/text
            year_match = str(year) in str(p) or str(year) in text

            if not year_match:
                continue

            for driver, aliases in drivers.items():
                for i, line in enumerate(lines, start=1):

                    if not any(a.lower() in line.lower() for a in aliases):
                        continue

                    start = max(0, i - 4)
                    end = min(len(lines), i + 3)

                    context = " || ".join(lines[start:end])

                    add_hit(
                        year,
                        driver,
                        p,
                        p.suffix.lower().lstrip("."),
                        context,
                        i
                    )

# ---------------------------------------------------------
# 2. Search CSVs
# ---------------------------------------------------------

for base in roots:
    if not base.exists():
        continue

    for p in base.rglob("*.csv"):
        try:
            df = pd.read_csv(p, dtype=str, keep_default_na=False)
        except Exception:
            continue

        if df.empty:
            continue

        for year, drivers in targets.items():

            # weak year filter
            if "year" in df.columns:
                df_y = df[df["year"].astype(str).eq(str(year))]
            else:
                if str(year) not in str(p):
                    continue
                df_y = df

            if df_y.empty:
                continue

            for driver, aliases in drivers.items():

                mask = pd.Series(False, index=df_y.index)

                for c in df_y.columns:
                    vals = df_y[c].astype(str)
                    for a in aliases:
                        mask |= vals.str.contains(
                            re.escape(a),
                            case=False,
                            regex=True,
                            na=False
                        )

                hits = df_y[mask]

                for idx, r in hits.iterrows():
                    context = " | ".join(
                        f"{c}={r[c]}"
                        for c in df.columns
                        if str(r[c]).strip()
                    )

                    add_hit(
                        year,
                        driver,
                        p,
                        "csv",
                        context,
                        int(idx) + 2
                    )

# ---------------------------------------------------------
# 3. De-duplicate exact repeated evidence
# ---------------------------------------------------------

hits = pd.DataFrame(rows)

if hits.empty:
    print("NO HITS FOUND")
    raise SystemExit

hits = hits.drop_duplicates(
    subset=[
        "year",
        "driver_name",
        "source_path",
        "line_or_row",
        "context"
    ]
)

# ---------------------------------------------------------
# 4. Evidence scoring
# ---------------------------------------------------------

def score_row(r):
    s = 0
    p = r["source_path"].lower()
    ctx = r["context"].lower()

    if "indycar" in p or "official" in p:
        s += 4

    if "last_chance" in p or "last row" in ctx or "last chance" in ctx:
        s += 3

    if r["speed_hits_mph"]:
        s += 3

    if r["lap_time_hits_s"]:
        s += 2

    if any(k in ctx for k in [
        "attempt",
        "second run",
        "second attempt",
        "third attempt",
        "fourth attempt",
        "waved off",
        "crash",
        "qualified",
        "bumped",
    ]):
        s += 2

    if "news" in p or "paddock" in p or "recap" in p:
        s += 1

    return s

hits["evidence_score"] = hits.apply(score_row, axis=1)

hits = hits.sort_values(
    ["year", "driver_name", "evidence_score"],
    ascending=[True, True, False]
)

outfile = OUT / "last_chance_missing_attempt_evidence_hits_v1.csv"
hits.to_csv(outfile, index=False)

# ---------------------------------------------------------
# 5. Print only high-value evidence
# ---------------------------------------------------------

print("=" * 160)
print("LAST CHANCE MISSING-ATTEMPT RECOVERY")
print("=" * 160)

for year, drivers in targets.items():

    for driver in drivers:

        sub = hits[
            (hits["year"] == year)
            & (hits["driver_name"] == driver)
        ]

        print("\n" + "#" * 160)
        print(year, driver)
        print("#" * 160)

        print("TOTAL HITS:", len(sub))

        # top 12 only
        for _, r in sub.head(12).iterrows():

            print("\nSOURCE:", r["source_path"])
            print("ROW/LINE:", r["line_or_row"])
            print("SCORE:", r["evidence_score"])

            if r["speed_hits_mph"]:
                print("SPEED:", r["speed_hits_mph"])

            if r["lap_time_hits_s"]:
                print("LAPS:", r["lap_time_hits_s"])

            print("CONTEXT:")
            print(r["context"][:1800])

print("\n" + "=" * 160)
print("OUTPUT")
print("=" * 160)
print(outfile.relative_to(ROOT))
print()
print("LAST_CHANCE_MISSING_ATTEMPT_RECOVERY_COMPLETE")
