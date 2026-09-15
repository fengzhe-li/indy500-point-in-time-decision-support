from pathlib import Path
import pandas as pd
import re

ROOT = Path("/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈")

OUT = ROOT / "r5_1/manual"
OUT.mkdir(parents=True, exist_ok=True)

search_roots = [
    ROOT / "r4",
    ROOT / "r5",
    ROOT / "weather",
]

keywords = [
    "lane 1",
    "lane1",
    "lane 2",
    "lane2",
    "priority",
    "priority lane",
    "retain",
    "withdraw",
    "queue",
    "queued",
    "waiting",
    "wait",
    "requeue",
    "last chance",
    "last row",
    "cool-down",
    "cool down",
]

target_years = {"2020", "2021", "2022", "2023", "2024"}

rows = []

# -------------------------------------------------------
# 1. Search text-like files
# -------------------------------------------------------

for base in search_roots:
    if not base.exists():
        continue

    for p in base.rglob("*"):
        if not p.is_file():
            continue

        if p.suffix.lower() not in {".txt", ".md", ".json", ".html"}:
            continue

        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        low = text.lower()

        if not any(k in low for k in keywords):
            continue

        years_in_file = [y for y in target_years if y in str(p) or y in text]

        for i, line in enumerate(text.splitlines(), start=1):
            line_low = line.lower()

            matched = [k for k in keywords if k in line_low]
            if not matched:
                continue

            rows.append({
                "source_path": str(p.relative_to(ROOT)),
                "source_type": p.suffix.lower().lstrip("."),
                "line_or_row": i,
                "year_hint": ";".join(sorted(years_in_file)),
                "matched_terms": ";".join(matched),
                "context": line[:2500],
            })

# -------------------------------------------------------
# 2. Search CSVs
# -------------------------------------------------------

for base in search_roots:
    if not base.exists():
        continue

    for p in base.rglob("*.csv"):
        try:
            df = pd.read_csv(p, dtype=str, keep_default_na=False)
        except Exception:
            continue

        if df.empty:
            continue

        for idx, r in df.iterrows():
            context = " | ".join(
                f"{c}={r[c]}"
                for c in df.columns
                if str(r[c]).strip()
            )

            low = context.lower()
            matched = [k for k in keywords if k in low]

            if not matched:
                continue

            year_hint = ""
            if "year" in df.columns:
                year_hint = str(r["year"])

            rows.append({
                "source_path": str(p.relative_to(ROOT)),
                "source_type": "csv",
                "line_or_row": int(idx) + 2,
                "year_hint": year_hint,
                "matched_terms": ";".join(matched),
                "context": context[:2500],
            })

hits = pd.DataFrame(rows)

if hits.empty:
    print("NO WAIT / QUEUE EVIDENCE FOUND")
    raise SystemExit

hits = hits.drop_duplicates(
    subset=["source_path", "line_or_row", "context"]
)

# -------------------------------------------------------
# 3. Rough regime classification
# -------------------------------------------------------

def classify(ctx):
    c = ctx.lower()

    if "last chance" in c or "last row" in c:
        return "LAST_CHANCE"

    if "lane 1" in c or "lane1" in c or "priority" in c or "withdraw" in c:
        return "DAY1_PRIORITY"

    if "lane 2" in c or "lane2" in c or "retain" in c:
        return "DAY1_RETAIN_QUEUE"

    if "queue" in c or "wait" in c or "requeue" in c:
        return "UNRESOLVED_QUEUE"

    return "OTHER"

hits["regime_guess"] = hits["context"].map(classify)

# -------------------------------------------------------
# 4. Score evidence quality
# -------------------------------------------------------

def score(row):
    s = 0
    p = row["source_path"].lower()
    c = row["context"].lower()

    if "official" in p:
        s += 4

    if "chronology" in p:
        s += 3

    if "action" in p:
        s += 2

    if "decision" in p:
        s += 2

    if "lane 1" in c or "lane1" in c:
        s += 3

    if "lane 2" in c or "lane2" in c:
        s += 3

    if "priority" in c:
        s += 2

    if "requeue" in c:
        s += 2

    if re.search(r"\b\d{1,3}\s*(?:min|mins|minute|minutes)\b", c):
        s += 4

    if re.search(r"\b\d{1,2}:\d{2}(?::\d{2})?\b", c):
        s += 2

    return s

hits["evidence_score"] = hits.apply(score, axis=1)

hits = hits.sort_values(
    ["regime_guess", "evidence_score"],
    ascending=[True, False]
)

outfile = OUT / "wait_regime_repository_evidence_hits_v1.csv"
hits.to_csv(outfile, index=False)

print("=" * 150)
print("WAIT REGIME REPOSITORY AUDIT")
print("=" * 150)

for regime in [
    "DAY1_PRIORITY",
    "DAY1_RETAIN_QUEUE",
    "LAST_CHANCE",
    "UNRESOLVED_QUEUE",
]:
    sub = hits[hits["regime_guess"] == regime]

    print("\n" + "#" * 150)
    print(regime, "N =", len(sub))
    print("#" * 150)

    for _, r in sub.head(25).iterrows():
        print("\nSOURCE:", r["source_path"])
        print("ROW/LINE:", r["line_or_row"])
        print("YEAR:", r["year_hint"])
        print("SCORE:", r["evidence_score"])
        print("MATCH:", r["matched_terms"])
        print("CONTEXT:")
        print(r["context"][:1800])

print("\nOUTPUT:")
print(outfile.relative_to(ROOT))
print("\nWAIT_REGIME_REPOSITORY_AUDIT_COMPLETE")
