from pathlib import Path
import csv
import re

ROOT = Path("/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈")
SCRIPT = ROOT / "r4/run_r4p0_audit.py"

print("=" * 100)
print("R4P0 ACTUAL INPUT INSPECTION")
print("=" * 100)

if not SCRIPT.exists():
    raise SystemExit(f"MISSING: {SCRIPT}")

text = SCRIPT.read_text(encoding="utf-8")

# ------------------------------------------------------------------
# 1. Show every source-code line that references project data assets.
# ------------------------------------------------------------------

print("\nA. DATA-REFERENCE LINES IN run_r4p0_audit.py")
print("-" * 100)

interesting = []

for lineno, line in enumerate(text.splitlines(), start=1):
    low = line.lower()

    if (
        "weather/output" in low
        or ".csv" in low
        or ".json" in low
        or "read_csv" in low
        or "read_json" in low
    ):
        interesting.append((lineno, line.rstrip()))

for lineno, line in interesting:
    print(f"{lineno:04d}: {line}")

# ------------------------------------------------------------------
# 2. Extract literal CSV/JSON paths appearing in the script.
# ------------------------------------------------------------------

patterns = [
    r"""["']([^"']+\.csv)["']""",
    r"""["']([^"']+\.json)["']""",
]

raw_paths = []

for pattern in patterns:
    raw_paths.extend(re.findall(pattern, text))

# Preserve order, remove duplicates.
seen = set()
unique_paths = []

for value in raw_paths:
    if value not in seen:
        seen.add(value)
        unique_paths.append(value)

print("\nB. LITERAL DATA FILES REFERENCED")
print("-" * 100)

resolved = []

for value in unique_paths:
    p = Path(value)

    if not p.is_absolute():
        p = ROOT / p

    # Ignore R4P0 outputs; we want upstream inputs.
    try:
        rel = p.relative_to(ROOT)
    except ValueError:
        rel = p

    if "r4p0_" in p.name.lower():
        continue

    exists = p.exists()

    print(f"\nPATH: {rel}")
    print(f"EXISTS: {exists}")

    if exists and p.is_file():
        resolved.append(p)

        if p.suffix.lower() == ".csv":
            try:
                with p.open(
                    "r",
                    encoding="utf-8-sig",
                    newline=""
                ) as f:
                    reader = csv.reader(f)
                    header = next(reader, [])

                    count = 0
                    preview = []

                    for row in reader:
                        count += 1
                        if len(preview) < 3:
                            preview.append(row)

                print(f"ROWS: {count}")
                print("COLUMNS:")
                for col in header:
                    print(f"  - {col}")

                print("FIRST 3 DATA ROWS:")
                for row in preview:
                    print("  " + repr(row))

            except Exception as e:
                print(
                    f"CSV READ ERROR: "
                    f"{type(e).__name__}: {e}"
                )

        elif p.suffix.lower() == ".json":
            try:
                size = p.stat().st_size
                print(f"JSON SIZE BYTES: {size}")
            except Exception as e:
                print(
                    f"JSON READ ERROR: "
                    f"{type(e).__name__}: {e}"
                )

# ------------------------------------------------------------------
# 3. Inspect a tiny fixed shortlist we already know is important.
# ------------------------------------------------------------------

fixed_candidates = [
    ROOT / "weather/output/attempt_performance_model_matrix_v1.csv",
    ROOT / "weather/output/unified_attempt_chronology_constraint_ledger_v10.csv",
    ROOT / "weather/output/repeat_attempt_delta_baseline_aggregate_metrics_v1.csv",
    ROOT / "weather/output/repeat_attempt_delta_baseline_fold_metrics_v1.csv",
]

print("\nC. FIXED HIGH-VALUE FILE SCHEMAS")
print("-" * 100)

for p in fixed_candidates:
    print(f"\nFILE: {p.relative_to(ROOT)}")

    if not p.exists():
        print("MISSING")
        continue

    try:
        with p.open(
            "r",
            encoding="utf-8-sig",
            newline=""
        ) as f:
            reader = csv.reader(f)
            header = next(reader, [])

            count = 0
            preview = []

            for row in reader:
                count += 1
                if len(preview) < 5:
                    preview.append(row)

        print(f"ROWS: {count}")
        print("COLUMNS:")
        for col in header:
            print(f"  - {col}")

        print("FIRST 5 DATA ROWS:")
        for row in preview:
            print("  " + repr(row))

    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")

print("\n" + "=" * 100)
print("R4P0_ACTUAL_INPUT_INSPECTION_READY")
print("=" * 100)
