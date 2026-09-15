from pathlib import Path
import csv
import json
import re
from collections import Counter

ROOT = Path("/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈")
R4 = ROOT / "r4"
OUT = R4 / "output"

OUT_FIELDS = OUT / "r4f8h_b_cutoff_candidate_fields_v1.csv"
OUT_FILES = OUT / "r4f8h_b_cutoff_candidate_files_v1.csv"
OUT_QA = OUT / "r4f8h_b_cutoff_evidence_resolution_qa_v1.csv"
OUT_REPORT = OUT / "r4f8h_b_cutoff_evidence_resolution_report_v1.json"

# =============================================================================
# R4F8H-B — CUTOFF / SESSION-END EVIDENCE RESOLUTION AUDIT
#
# READ-ONLY with respect to all frozen project assets.
#
# PURPOSE:
# Search existing repository evidence for legitimate decision-safe information
# related to qualifying session end / cutoff / remaining time.
#
# THIS SCRIPT DOES NOT:
# - invent session end times
# - infer missing Last Chance timestamps
# - run Monte Carlo
# - alter frozen files
# - use future outcomes as decision features
# =============================================================================

FIELD_KEYWORDS = [
    "session_end",
    "end_time",
    "scheduled_end",
    "cutoff",
    "close_time",
    "closing_time",
    "remaining",
    "time_remaining",
    "minutes_remaining",
    "session_duration",
    "qualifying_end",
    "day1_end",
    "last_chance_end",
    "checkered",
    "chequered",
    "gun_time",
    "deadline",
]

TEXT_KEYWORDS = [
    "session end",
    "session ends",
    "scheduled end",
    "qualifying ends",
    "qualifying ended",
    "cutoff",
    "cut-off",
    "remaining time",
    "time remaining",
    "last chance",
    "checkered flag",
    "chequered flag",
    "6:00 p.m.",
    "6:00 pm",
    "5:50 p.m.",
    "5:50 pm",
]

SCAN_EXTENSIONS = {
    ".csv",
    ".json",
    ".md",
    ".txt",
    ".py",
}

SKIP_DIR_NAMES = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".venv",
    "venv",
    "node_modules",
}


def clean(v):
    if v is None:
        return ""
    return str(v).strip()


def norm(s):
    return re.sub(r"[^a-z0-9]+", "_", str(s).lower()).strip("_")


def looks_relevant_field(field):
    n = norm(field)
    return any(norm(k) in n for k in FIELD_KEYWORDS)


def file_is_allowed(path):
    if path.suffix.lower() not in SCAN_EXTENSIONS:
        return False
    if any(part in SKIP_DIR_NAMES for part in path.parts):
        return False
    return True


def safe_relative(path):
    try:
        return str(path.relative_to(ROOT))
    except Exception:
        return str(path)


candidate_field_rows = []
candidate_file_rows = []

# =============================================================================
# 1. Scan CSV schemas + populated values
# =============================================================================

for path in ROOT.rglob("*.csv"):
    if not file_is_allowed(path):
        continue

    try:
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            fields = reader.fieldnames or []

            relevant_fields = [x for x in fields if looks_relevant_field(x)]

            if not relevant_fields:
                continue

            rows = list(reader)

            for field in relevant_fields:
                values = [
                    clean(r.get(field))
                    for r in rows
                    if clean(r.get(field))
                ]

                examples = []
                for v in values:
                    if v not in examples:
                        examples.append(v)
                    if len(examples) >= 5:
                        break

                candidate_field_rows.append({
                    "path": safe_relative(path),
                    "file_type": "csv",
                    "row_count": len(rows),
                    "field": field,
                    "nonempty_count": len(values),
                    "unique_nonempty_count": len(set(values)),
                    "example_values": " | ".join(examples),
                })

    except Exception as e:
        candidate_file_rows.append({
            "path": safe_relative(path),
            "file_type": "csv",
            "keyword_hits": "",
            "reason": f"CSV_READ_ERROR: {type(e).__name__}",
        })

# =============================================================================
# 2. Scan JSON key names recursively
# =============================================================================

def walk_json(obj, prefix=""):
    hits = []

    if isinstance(obj, dict):
        for k, v in obj.items():
            new_prefix = f"{prefix}.{k}" if prefix else str(k)

            if looks_relevant_field(k):
                hits.append((new_prefix, v))

            hits.extend(walk_json(v, new_prefix))

    elif isinstance(obj, list):
        for i, item in enumerate(obj[:1000]):
            hits.extend(walk_json(item, f"{prefix}[{i}]"))

    return hits


for path in ROOT.rglob("*.json"):
    if not file_is_allowed(path):
        continue

    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
        hits = walk_json(obj)

        for key_path, value in hits:
            if isinstance(value, (dict, list)):
                example = f"<{type(value).__name__}>"
            else:
                example = clean(value)

            candidate_field_rows.append({
                "path": safe_relative(path),
                "file_type": "json",
                "row_count": "",
                "field": key_path,
                "nonempty_count": 1 if example else 0,
                "unique_nonempty_count": 1 if example else 0,
                "example_values": example[:500],
            })

    except Exception:
        pass

# =============================================================================
# 3. Scan textual files for cutoff/session-end language
# =============================================================================

for ext in [".md", ".txt", ".py", ".json"]:
    for path in ROOT.rglob(f"*{ext}"):
        if not file_is_allowed(path):
            continue

        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        low = text.lower()

        hits = [
            kw
            for kw in TEXT_KEYWORDS
            if kw.lower() in low
        ]

        if hits:
            candidate_file_rows.append({
                "path": safe_relative(path),
                "file_type": ext.lstrip("."),
                "keyword_hits": " | ".join(sorted(set(hits))),
                "reason": "TEXT_MATCH",
            })

# =============================================================================
# Save candidate field inventory
# =============================================================================

fieldnames = [
    "path",
    "file_type",
    "row_count",
    "field",
    "nonempty_count",
    "unique_nonempty_count",
    "example_values",
]

with OUT_FIELDS.open("w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(candidate_field_rows)

file_fieldnames = [
    "path",
    "file_type",
    "keyword_hits",
    "reason",
]

with OUT_FILES.open("w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=file_fieldnames)
    writer.writeheader()
    writer.writerows(candidate_file_rows)

# =============================================================================
# Summaries
# =============================================================================

nonempty_field_candidates = [
    r for r in candidate_field_rows
    if str(r["nonempty_count"]) not in {"", "0"}
]

exact_remaining_candidates = [
    r for r in nonempty_field_candidates
    if any(
        token in norm(r["field"])
        for token in [
            "session_remaining",
            "time_remaining",
            "minutes_remaining",
        ]
    )
]

session_end_candidates = [
    r for r in nonempty_field_candidates
    if any(
        token in norm(r["field"])
        for token in [
            "session_end",
            "scheduled_end",
            "qualifying_end",
            "cutoff",
            "closing_time",
            "close_time",
        ]
    )
]

counts_by_path = Counter(r["path"] for r in nonempty_field_candidates)

qa_rows = [
    {
        "metric": "existing_f8h_a_report_present",
        "value": (OUT / "r4f8h_a_final_mc_readiness_report_v1.json").exists(),
        "expected": True,
        "status": (
            "PASS"
            if (OUT / "r4f8h_a_final_mc_readiness_report_v1.json").exists()
            else "FAIL"
        ),
    },
    {
        "metric": "candidate_cutoff_related_fields_found",
        "value": len(candidate_field_rows),
        "expected": "MEASURED",
        "status": "PASS",
    },
    {
        "metric": "populated_cutoff_related_fields_found",
        "value": len(nonempty_field_candidates),
        "expected": "MEASURED",
        "status": "PASS",
    },
    {
        "metric": "populated_exact_remaining_candidates",
        "value": len(exact_remaining_candidates),
        "expected": "MEASURED_NOT_ASSUMED_VALID",
        "status": "PASS",
    },
    {
        "metric": "populated_session_end_candidates",
        "value": len(session_end_candidates),
        "expected": "MEASURED_NOT_ASSUMED_VALID",
        "status": "PASS",
    },
    {
        "metric": "monte_carlo_executed",
        "value": False,
        "expected": False,
        "status": "PASS",
    },
    {
        "metric": "session_remaining_fabricated",
        "value": False,
        "expected": False,
        "status": "PASS",
    },
]

with OUT_QA.open("w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=["metric", "value", "expected", "status"],
    )
    writer.writeheader()
    writer.writerows(qa_rows)

report = {
    "phase": "R4F8H-B",
    "purpose": "Resolve existing cutoff/session-end evidence only.",
    "candidate_field_rows": len(candidate_field_rows),
    "populated_candidate_field_rows": len(nonempty_field_candidates),
    "exact_remaining_candidate_rows": len(exact_remaining_candidates),
    "session_end_candidate_rows": len(session_end_candidates),
    "text_candidate_files": len(candidate_file_rows),
    "top_candidate_paths": counts_by_path.most_common(25),
    "important_boundary": (
        "Presence of a field or textual mention does not establish "
        "decision-safe session remaining. Candidates require semantic "
        "inspection before use."
    ),
    "final_mc_executed": False,
    "next_step": (
        "Inspect the strongest populated session-end/cutoff candidates. "
        "If no defensible decision-safe source exists, freeze an explicit "
        "structural cutoff sensitivity policy rather than fabricating "
        "historical exact session remaining."
    ),
}

OUT_REPORT.write_text(
    json.dumps(report, indent=2, ensure_ascii=False),
    encoding="utf-8",
)

# =============================================================================
# Console
# =============================================================================

print("=" * 125)
print("R4F8H-B — CUTOFF / SESSION-END EVIDENCE RESOLUTION AUDIT")
print("=" * 125)
print()

print("SUMMARY")
print("-" * 125)
print(f"Candidate cutoff-related field rows:      {len(candidate_field_rows)}")
print(f"Populated candidate field rows:           {len(nonempty_field_candidates)}")
print(f"Exact remaining-time candidate rows:      {len(exact_remaining_candidates)}")
print(f"Session-end/cutoff candidate rows:        {len(session_end_candidates)}")
print(f"Text candidate files:                     {len(candidate_file_rows)}")
print()

print("TOP POPULATED CANDIDATE FIELDS")
print("-" * 125)

for r in nonempty_field_candidates[:40]:
    print(
        f"{r['path']}\n"
        f"  FIELD: {r['field']}\n"
        f"  NONEMPTY: {r['nonempty_count']}\n"
        f"  EXAMPLES: {r['example_values'][:250]}\n"
    )

if not nonempty_field_candidates:
    print("  none")

print()
print("EXACT REMAINING-TIME CANDIDATES")
print("-" * 125)

for r in exact_remaining_candidates[:30]:
    print(
        f"{r['path']} | "
        f"{r['field']} | "
        f"nonempty={r['nonempty_count']} | "
        f"{r['example_values'][:180]}"
    )

if not exact_remaining_candidates:
    print("  none")

print()
print("SESSION-END / CUTOFF CANDIDATES")
print("-" * 125)

for r in session_end_candidates[:30]:
    print(
        f"{r['path']} | "
        f"{r['field']} | "
        f"nonempty={r['nonempty_count']} | "
        f"{r['example_values'][:180]}"
    )

if not session_end_candidates:
    print("  none")

print()
print("QA")
print("-" * 125)

for r in qa_rows:
    print(
        f"{r['status']:5s} | "
        f"{r['metric']} | "
        f"value={r['value']} | "
        f"expected={r['expected']}"
    )

print()
print("OUTPUTS")
print("-" * 125)

for p in [
    OUT_FIELDS,
    OUT_FILES,
    OUT_QA,
    OUT_REPORT,
]:
    print(p.relative_to(ROOT))

print()
print("R4F8H_B_CUTOFF_EVIDENCE_AUDIT_COMPLETE")
print()
print(
    "IMPORTANT: Candidate presence is not evidence of decision-safe "
    "session remaining. We must inspect semantics before using any field."
)
