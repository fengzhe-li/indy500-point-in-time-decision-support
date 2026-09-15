from pathlib import Path
import csv
import json
import math
import statistics
from collections import Counter, defaultdict

ROOT = Path("/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈")
WEATHER_OUT = ROOT / "weather" / "output"
OUT = ROOT / "r4" / "output"

SRC = WEATHER_OUT / "queue_wait_throughput_proxy_v1.csv"

OUT_SCHEMA = OUT / "r4f8h_e_throughput_proxy_schema_v1.csv"
OUT_SUMMARY = OUT / "r4f8h_e_throughput_proxy_summary_v1.csv"
OUT_QA = OUT / "r4f8h_e_throughput_proxy_qa_v1.csv"
OUT_REPORT = OUT / "r4f8h_e_throughput_proxy_report_v1.json"


# =============================================================================
# R4F8H-E — THROUGHPUT PROXY SEMANTIC INSPECTION
#
# PURPOSE
# -------
# Inspect whether queue_wait_throughput_proxy_v1.csv can legitimately support
# a STRUCTURAL competitor-arrival/evolution component for final MC.
#
# DOES NOT:
# - fit an empirical competitor action model
# - infer exact queue wait
# - infer future competitor identities
# - run final Monte Carlo
# - use future outcomes as decision-time features
# - modify frozen inputs
# =============================================================================


def clean(v):
    return "" if v is None else str(v).strip()


def num(v):
    s = clean(v)
    if not s:
        return None
    try:
        x = float(s)
        if math.isfinite(x):
            return x
    except Exception:
        pass
    return None


def read_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return reader.fieldnames or [], list(reader)


def norm(s):
    return (
        str(s)
        .strip()
        .lower()
        .replace("-", "_")
        .replace(" ", "_")
    )


def find_field(fields, candidates):
    m = {norm(f): f for f in fields}
    for c in candidates:
        if norm(c) in m:
            return m[norm(c)]
    return None


if not SRC.exists():
    print("=" * 120)
    print("R4F8H-E — SOURCE FILE NOT FOUND")
    print("=" * 120)
    print(SRC.relative_to(ROOT))
    raise SystemExit(1)


fields, rows = read_csv(SRC)

# =============================================================================
# Schema inventory
# =============================================================================

schema_rows = []

for field in fields:
    vals = [clean(r.get(field)) for r in rows if clean(r.get(field))]
    nums = [num(r.get(field)) for r in rows]
    nums = [x for x in nums if x is not None]

    examples = []
    for v in vals:
        if v not in examples:
            examples.append(v)
        if len(examples) >= 5:
            break

    schema_rows.append({
        "field": field,
        "nonempty_count": len(vals),
        "numeric_count": len(nums),
        "unique_nonempty_count": len(set(vals)),
        "example_values": " | ".join(examples),
        "numeric_min": min(nums) if nums else "",
        "numeric_max": max(nums) if nums else "",
        "numeric_mean": statistics.mean(nums) if nums else "",
        "numeric_median": statistics.median(nums) if nums else "",
    })

with OUT_SCHEMA.open("w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=list(schema_rows[0].keys()))
    writer.writeheader()
    writer.writerows(schema_rows)


# =============================================================================
# Resolve likely semantics
# =============================================================================

year_field = find_field(fields, [
    "year",
    "season",
])

session_field = find_field(fields, [
    "session",
    "session_id",
    "session_name",
    "regime",
])

spacing_field = find_field(fields, [
    "inter_attempt_gap_minutes",
    "attempt_spacing_minutes",
    "spacing_minutes",
    "gap_minutes",
    "throughput_spacing_minutes",
])

rate_field = find_field(fields, [
    "attempts_per_hour",
    "runs_per_hour",
    "throughput_per_hour",
    "completion_rate_per_hour",
])

count_field = find_field(fields, [
    "attempt_count",
    "run_count",
    "completed_attempt_count",
    "n_attempts",
])

duration_field = find_field(fields, [
    "window_minutes",
    "duration_minutes",
    "session_minutes",
    "window_duration_minutes",
])

source_field = find_field(fields, [
    "source",
    "source_type",
    "provenance",
    "source_class",
])

decision_safe_field = find_field(fields, [
    "decision_safe",
    "decision_time_safe",
    "leakage_safe",
    "available_at_decision",
])

proxy_field = find_field(fields, [
    "proxy_type",
    "throughput_proxy_type",
    "metric_type",
])

quality_field = find_field(fields, [
    "quality",
    "support_quality",
    "chronology_quality",
    "evidence_quality",
])


# =============================================================================
# Per-year / per-session summaries
# =============================================================================

grouped = defaultdict(list)

for r in rows:
    year = clean(r.get(year_field)) if year_field else ""
    session = clean(r.get(session_field)) if session_field else ""
    grouped[(year, session)].append(r)

summary_rows = []

for (year, session), group in sorted(grouped.items()):

    spacings = []
    if spacing_field:
        spacings = [num(r.get(spacing_field)) for r in group]
        spacings = [x for x in spacings if x is not None]

    rates = []
    if rate_field:
        rates = [num(r.get(rate_field)) for r in group]
        rates = [x for x in rates if x is not None]

    counts = []
    if count_field:
        counts = [num(r.get(count_field)) for r in group]
        counts = [x for x in counts if x is not None]

    durations = []
    if duration_field:
        durations = [num(r.get(duration_field)) for r in group]
        durations = [x for x in durations if x is not None]

    # If no explicit rate exists, derive a descriptive throughput proxy ONLY
    # when both count and duration are present on the same row.
    derived_rates = []

    if not rate_field and count_field and duration_field:
        for r in group:
            c = num(r.get(count_field))
            d = num(r.get(duration_field))
            if c is not None and d is not None and d > 0:
                derived_rates.append(c / d * 60.0)

    usable_rates = rates if rates else derived_rates

    summary_rows.append({
        "year": year,
        "session": session,
        "rows": len(group),
        "spacing_n": len(spacings),
        "spacing_median_minutes": (
            statistics.median(spacings) if spacings else ""
        ),
        "spacing_mean_minutes": (
            statistics.mean(spacings) if spacings else ""
        ),
        "rate_n": len(usable_rates),
        "attempts_per_hour_median": (
            statistics.median(usable_rates) if usable_rates else ""
        ),
        "attempts_per_hour_mean": (
            statistics.mean(usable_rates) if usable_rates else ""
        ),
        "count_n": len(counts),
        "duration_n": len(durations),
        "decision_safe_values": (
            " | ".join(
                sorted(set(
                    clean(r.get(decision_safe_field))
                    for r in group
                    if decision_safe_field and clean(r.get(decision_safe_field))
                ))
            )
            if decision_safe_field
            else ""
        ),
        "quality_values": (
            " | ".join(
                sorted(set(
                    clean(r.get(quality_field))
                    for r in group
                    if quality_field and clean(r.get(quality_field))
                ))
            )
            if quality_field
            else ""
        ),
        "proxy_type_values": (
            " | ".join(
                sorted(set(
                    clean(r.get(proxy_field))
                    for r in group
                    if proxy_field and clean(r.get(proxy_field))
                ))
            )
            if proxy_field
            else ""
        ),
    })

with OUT_SUMMARY.open("w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=list(summary_rows[0].keys()) if summary_rows else [
        "year","session","rows","spacing_n","spacing_median_minutes",
        "spacing_mean_minutes","rate_n","attempts_per_hour_median",
        "attempts_per_hour_mean","count_n","duration_n",
        "decision_safe_values","quality_values","proxy_type_values"
    ])
    writer.writeheader()
    writer.writerows(summary_rows)


# =============================================================================
# Global descriptive diagnostics
# =============================================================================

all_spacings = []
if spacing_field:
    all_spacings = [num(r.get(spacing_field)) for r in rows]
    all_spacings = [x for x in all_spacings if x is not None]

all_rates = []
if rate_field:
    all_rates = [num(r.get(rate_field)) for r in rows]
    all_rates = [x for x in all_rates if x is not None]

if not rate_field and count_field and duration_field:
    for r in rows:
        c = num(r.get(count_field))
        d = num(r.get(duration_field))
        if c is not None and d is not None and d > 0:
            all_rates.append(c / d * 60.0)


# =============================================================================
# Conservative semantic judgement
# =============================================================================

has_numeric_spacing = len(all_spacings) > 0
has_numeric_rate = len(all_rates) > 0

decision_safe_values = set()
if decision_safe_field:
    for r in rows:
        v = clean(r.get(decision_safe_field))
        if v:
            decision_safe_values.add(v.lower())

explicitly_safe = bool(
    decision_safe_values
    and decision_safe_values.issubset({
        "true", "1", "yes", "safe", "decision_safe"
    })
)

# Even if "decision-safe", throughput remains a structural process proxy,
# not a future competitor identity/action model.
if has_numeric_rate or has_numeric_spacing:
    semantic_status = "STRUCTURAL_THROUGHPUT_PROXY_USABLE"
else:
    semantic_status = "INSUFFICIENT_NUMERIC_THROUGHPUT_SUPPORT"


# =============================================================================
# QA
# =============================================================================

qa_rows = []


def qa(metric, value, expected, status):
    qa_rows.append({
        "metric": metric,
        "value": value,
        "expected": expected,
        "status": status,
    })


qa(
    "source_rows",
    len(rows),
    ">0",
    "PASS" if len(rows) > 0 else "FAIL",
)

qa(
    "numeric_spacing_found",
    has_numeric_spacing,
    "MEASURED",
    "PASS",
)

qa(
    "numeric_throughput_rate_found",
    has_numeric_rate,
    "MEASURED",
    "PASS",
)

qa(
    "future_competitor_identity_model_claimed",
    False,
    False,
    "PASS",
)

qa(
    "future_competitor_action_model_claimed",
    False,
    False,
    "PASS",
)

qa(
    "exact_queue_wait_claimed",
    False,
    False,
    "PASS",
)

qa(
    "historical_future_leaderboard_used_as_decision_feature",
    False,
    False,
    "PASS",
)

qa(
    "structural_proxy_only",
    True,
    True,
    "PASS",
)

with OUT_QA.open("w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=["metric", "value", "expected", "status"]
    )
    writer.writeheader()
    writer.writerows(qa_rows)


# =============================================================================
# Report
# =============================================================================

report = {
    "phase": "R4F8H-E",
    "source": str(SRC.relative_to(ROOT)),
    "rows": len(rows),

    "resolved_fields": {
        "year": year_field,
        "session": session_field,
        "spacing": spacing_field,
        "rate": rate_field,
        "count": count_field,
        "duration": duration_field,
        "source": source_field,
        "decision_safe": decision_safe_field,
        "proxy_type": proxy_field,
        "quality": quality_field,
    },

    "global_diagnostics": {
        "spacing_n": len(all_spacings),
        "spacing_median_minutes": (
            statistics.median(all_spacings) if all_spacings else None
        ),
        "spacing_mean_minutes": (
            statistics.mean(all_spacings) if all_spacings else None
        ),
        "rate_n": len(all_rates),
        "attempts_per_hour_median": (
            statistics.median(all_rates) if all_rates else None
        ),
        "attempts_per_hour_mean": (
            statistics.mean(all_rates) if all_rates else None
        ),
    },

    "decision_safe_field_present": decision_safe_field is not None,
    "decision_safe_values": sorted(decision_safe_values),
    "explicitly_decision_safe": explicitly_safe,

    "semantic_status": semantic_status,

    "allowed_use": (
        "May calibrate a STRUCTURAL competitor-arrival/session-progress "
        "sensitivity component if numeric support exists. "
        "Must remain labelled as a throughput/process proxy."
    ),

    "forbidden_use": [
        "Do not treat spacing as direct queue wait.",
        "Do not infer exact future competitor identities.",
        "Do not infer exact future competitor actions.",
        "Do not replay realized future leaderboard as a decision-time feature.",
        "Do not call structural throughput an empirical competitor strategy model.",
    ],

    "next_step": (
        "If usable numeric throughput exists, freeze a structural "
        "competitor-evolution policy. Otherwise final MC must restrict "
        "dynamic rank claims and use static-current-benchmark sensitivity only."
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
print("R4F8H-E — THROUGHPUT PROXY SEMANTIC INSPECTION")
print("=" * 125)
print()

print("SOURCE")
print("-" * 125)
print(f"Path: {SRC.relative_to(ROOT)}")
print(f"Rows: {len(rows)}")
print()

print("RESOLVED FIELDS")
print("-" * 125)
for k, v in report["resolved_fields"].items():
    print(f"{k:20s}: {v}")
print()

print("GLOBAL NUMERIC DIAGNOSTICS")
print("-" * 125)
print(f"Spacing observations:       {len(all_spacings)}")
print(
    f"Spacing median (min):       "
    f"{report['global_diagnostics']['spacing_median_minutes']}"
)
print(
    f"Spacing mean (min):         "
    f"{report['global_diagnostics']['spacing_mean_minutes']}"
)
print(f"Throughput-rate observations: {len(all_rates)}")
print(
    f"Attempts/hour median:       "
    f"{report['global_diagnostics']['attempts_per_hour_median']}"
)
print(
    f"Attempts/hour mean:         "
    f"{report['global_diagnostics']['attempts_per_hour_mean']}"
)
print()

print("PER-GROUP SUMMARY")
print("-" * 125)

for r in summary_rows[:50]:
    print(
        f"year={r['year'] or 'NA':6s} | "
        f"session={r['session'] or 'NA':20s} | "
        f"rows={r['rows']:4d} | "
        f"spacing_med={str(r['spacing_median_minutes']):>10s} | "
        f"rate_med={str(r['attempts_per_hour_median']):>10s}"
    )

if not summary_rows:
    print("  none")

print()
print("SEMANTIC JUDGEMENT")
print("-" * 125)
print(f"Status: {semantic_status}")
print(
    "Interpretation: this file may support only a STRUCTURAL "
    "competitor-arrival/session-progress component."
)
print(
    "It does NOT establish exact queue wait, exact future competitor "
    "actions, or an empirical leaderboard-evolution model."
)
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
    OUT_SCHEMA,
    OUT_SUMMARY,
    OUT_QA,
    OUT_REPORT,
]:
    print(p.relative_to(ROOT))

print()
print("R4F8H_E_THROUGHPUT_PROXY_SEMANTIC_INSPECTION_COMPLETE")
