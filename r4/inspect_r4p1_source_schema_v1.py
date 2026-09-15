from pathlib import Path
import json
import pandas as pd

ROOT = Path("/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈")

print("=" * 110)
print("R4P1 SOURCE SCHEMA INSPECTION")
print("=" * 110)

# ---------------------------------------------------------------------
# 1. Read R4P0 outputs
# ---------------------------------------------------------------------

r4p0_files = [
    ROOT / "r4/output/r4p0_cross_car_data_inventory_v1.csv",
    ROOT / "r4/output/r4p0_time_window_coverage_v1.csv",
    ROOT / "r4/output/r4p0_baseline_feasibility_v1.csv",
    ROOT / "r4/output/r4p0_cross_car_data_audit_v1.json",
    ROOT / "r4/output/r4p0_cross_car_data_audit_v1_qa.csv",
]

print("\n" + "=" * 110)
print("A. R4P0 OUTPUTS")
print("=" * 110)

for path in r4p0_files:
    print(f"\nFILE: {path.relative_to(ROOT)}")

    if not path.exists():
        print("  MISSING")
        continue

    print(f"  size_bytes={path.stat().st_size}")

    try:
        if path.suffix == ".csv":
            df = pd.read_csv(path)
            print(f"  rows={len(df)}")
            print(f"  columns={list(df.columns)}")
            print("  HEAD:")
            print(df.head(20).to_string(index=False))

        elif path.suffix == ".json":
            obj = json.loads(path.read_text(encoding="utf-8"))
            print("  JSON TOP-LEVEL:")
            if isinstance(obj, dict):
                print(f"  keys={list(obj.keys())}")
                print(json.dumps(obj, indent=2, ensure_ascii=False)[:12000])
            else:
                print(json.dumps(obj, indent=2, ensure_ascii=False)[:12000])

    except Exception as e:
        print(f"  ERROR: {type(e).__name__}: {e}")


# ---------------------------------------------------------------------
# 2. Discover relevant upstream CSV/JSON files
# ---------------------------------------------------------------------

keywords = [
    "attempt",
    "lap",
    "chronology",
    "timing",
    "sequence",
    "section",
    "official",
    "canonical",
    "decision",
]

candidates = []

for base in [ROOT / "weather/output", ROOT / "r4/output"]:
    if not base.exists():
        continue

    for path in base.rglob("*"):
        if not path.is_file():
            continue

        if path.suffix.lower() not in {".csv", ".json"}:
            continue

        name = path.name.lower()

        if not any(k in name for k in keywords):
            continue

        # Skip already-inspected R4P0 files here.
        if "r4p0_" in name:
            continue

        candidates.append(path)

candidates = sorted(set(candidates))

print("\n" + "=" * 110)
print("B. RELEVANT UPSTREAM FILES")
print("=" * 110)
print(f"candidate_count={len(candidates)}")

summaries = []

for path in candidates:
    rel = path.relative_to(ROOT)

    try:
        if path.suffix.lower() == ".csv":
            sample = pd.read_csv(path, nrows=5)
            cols = list(sample.columns)

            # Cheap row count.
            with open(path, "rb") as f:
                rows = max(sum(1 for _ in f) - 1, 0)

        else:
            obj = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(obj, list):
                rows = len(obj)
                cols = sorted({
                    k
                    for x in obj[:10]
                    if isinstance(x, dict)
                    for k in x.keys()
                })
            elif isinstance(obj, dict):
                rows = 1
                cols = list(obj.keys())
            else:
                rows = None
                cols = []

        summaries.append((path, rows, cols))

    except Exception as e:
        summaries.append(
            (path, "ERROR", [f"{type(e).__name__}: {e}"])
        )


# ---------------------------------------------------------------------
# 3. Prioritize likely useful files
# ---------------------------------------------------------------------

def score(item):
    path, rows, cols = item
    text = (path.name + " " + " ".join(map(str, cols))).lower()

    points = 0

    for term, weight in [
        ("attempt_id", 8),
        ("lap_number", 8),
        ("lap_speed", 7),
        ("average_speed", 6),
        ("four", 5),
        ("chronology", 7),
        ("sequence", 6),
        ("timestamp", 6),
        ("time_quality", 6),
        ("event_order", 5),
        ("car_number", 5),
        ("driver", 4),
        ("section", 3),
    ]:
        if term in text:
            points += weight

    return -points, str(path)


summaries.sort(key=score)

for i, (path, rows, cols) in enumerate(summaries, start=1):
    print(f"\n[{i:03d}] {path.relative_to(ROOT)}")
    print(f"rows={rows}")
    print("columns:")
    for col in cols:
        print(f"  - {col}")

    if i <= 15 and path.suffix.lower() == ".csv":
        try:
            preview = pd.read_csv(path, nrows=5)
            print("HEAD:")
            print(preview.to_string(index=False))
        except Exception as e:
            print(f"HEAD ERROR: {e}")


# ---------------------------------------------------------------------
# 4. Highlight likely builders
# ---------------------------------------------------------------------

print("\n" + "=" * 110)
print("C. HIGH-VALUE SHORTLIST")
print("=" * 110)

groups = {
    "CANONICAL ATTEMPTS": [
        "attempt",
    ],
    "FOUR-LAP / LAP DATA": [
        "lap",
    ],
    "CHRONOLOGY / ORDER": [
        "chronology",
        "sequence",
        "timing",
    ],
    "SECTION / PARTIAL": [
        "section",
    ],
}

for label, terms in groups.items():
    print(f"\n{label}")

    matched = []

    for path, rows, cols in summaries:
        text = (
            str(path.relative_to(ROOT)) + " " + " ".join(map(str, cols))
        ).lower()

        if any(term in text for term in terms):
            matched.append((path, rows, cols))

    for path, rows, cols in matched[:12]:
        print(
            f"  {path.relative_to(ROOT)}"
            f" | rows={rows}"
            f" | cols={len(cols)}"
        )


print("\n" + "=" * 110)
print("R4P1_SOURCE_SCHEMA_INSPECTION_READY")
print("=" * 110)
