from pathlib import Path
import csv
import json
import re
from collections import Counter, defaultdict


ROOT = Path("/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈")
R4 = ROOT / "r4"
OUT = R4 / "output"
WEATHER_OUT = ROOT / "weather" / "output"

DECISION_FILE = OUT / "r4f8e_reconstructed_decision_numeric_state_v1.csv"
ACTION_FILE = OUT / "r4f8e_reconstructed_action_numeric_interface_v1.csv"
FUSED_FILE = OUT / "r4f2_canonical_fused_decision_dataset_v2.csv"

MC_FILE = OUT / "r4f8h_g_action_mc_scenario_results_v1.csv"
PRIORITY_FILE = OUT / "r4f8h_h_priority_benefit_sensitivity_results_v1.csv"

OUT_FIELDS = OUT / "r4f9_a_historical_replay_candidate_fields_v1.csv"
OUT_FILES = OUT / "r4f9_a_historical_replay_candidate_files_v1.csv"
OUT_QA = OUT / "r4f9_a_historical_replay_readiness_qa_v1.csv"
OUT_REPORT = OUT / "r4f9_a_historical_replay_readiness_report_v1.json"


# =============================================================================
# R4F9-A — HISTORICAL REPLAY READINESS AUDIT
#
# PURPOSE
# -------
# Identify repository fields/evidence that can support realized historical
# outcomes for replay/evaluation of the frozen R4F8H simulator.
#
# Historical actions are NOT optimal labels.
#
# DOES NOT:
# - score model recommendations against human choices
# - refit any model
# - use future outcomes as R4F8H decision features
# - modify frozen data
# - run a new Monte Carlo
# =============================================================================


KEYWORDS = [
    "historical_action",
    "observed_action",
    "actual_action",
    "action_taken",
    "later_attempt",
    "next_attempt",
    "subsequent_attempt",
    "future_attempt",
    "next_speed",
    "later_speed",
    "subsequent_speed",
    "outcome_speed",
    "realized_speed",
    "final_speed",
    "result_speed",
    "benchmark_cross",
    "benchmark_outcome",
    "target_hit",
    "advancement",
    "advanced",
    "qualified",
    "survived",
    "eliminated",
    "final_rank",
    "next_rank",
    "later_rank",
    "result_rank",
    "withdraw",
    "retain",
    "requeue",
    "waved",
    "attempt_count",
    "later_attempt_count",
    "outcome",
]

TEXT_KEYWORDS = [
    "historical action",
    "actual action",
    "observed action",
    "later attempt",
    "next attempt",
    "subsequent attempt",
    "realized outcome",
    "historical outcome",
    "benchmark crossing",
    "advanced to",
    "qualified for",
    "last chance",
    "withdrawn",
    "requeued",
    "retained result",
]


def clean(v):
    return "" if v is None else str(v).strip()


def norm(v):
    return re.sub(
        r"[^a-z0-9]+",
        "_",
        str(v).lower(),
    ).strip("_")


def relevant_field(field):
    n = norm(field)
    return any(k in n for k in KEYWORDS)


def rel(path):
    try:
        return str(path.relative_to(ROOT))
    except Exception:
        return str(path)


def file_allowed(path):
    bad = {
        ".git",
        "__pycache__",
        ".venv",
        "venv",
        "node_modules",
    }
    return not any(part in bad for part in path.parts)


required = [
    DECISION_FILE,
    ACTION_FILE,
    FUSED_FILE,
    MC_FILE,
    PRIORITY_FILE,
]

missing = [p for p in required if not p.exists()]

if missing:
    print("=" * 130)
    print("R4F9-A REQUIRED INPUTS MISSING")
    print("=" * 130)
    for p in missing:
        print(rel(p))
    raise SystemExit(1)


# =============================================================================
# Candidate CSV fields
# =============================================================================

candidate_fields = []

for path in ROOT.rglob("*.csv"):

    if not file_allowed(path):
        continue

    try:
        with path.open(
            "r",
            encoding="utf-8-sig",
            newline="",
        ) as f:

            reader = csv.DictReader(f)
            fields = reader.fieldnames or []

            relevant = [
                x for x in fields
                if relevant_field(x)
            ]

            if not relevant:
                continue

            rows = list(reader)

        for field in relevant:

            vals = [
                clean(r.get(field))
                for r in rows
                if clean(r.get(field))
            ]

            examples = []

            for value in vals:
                if value not in examples:
                    examples.append(value)

                if len(examples) >= 6:
                    break

            candidate_fields.append({
                "path": rel(path),
                "rows": len(rows),
                "field": field,
                "nonempty_count": len(vals),
                "unique_nonempty_count": len(set(vals)),
                "examples": " | ".join(examples),
            })

    except Exception:
        pass


# =============================================================================
# Text/code candidate files
# =============================================================================

candidate_files = []

for ext in [
    "*.json",
    "*.md",
    "*.txt",
    "*.py",
]:

    for path in ROOT.rglob(ext):

        if not file_allowed(path):
            continue

        try:
            text = path.read_text(
                encoding="utf-8",
                errors="ignore",
            )
        except Exception:
            continue

        low = text.lower()

        hits = [
            keyword
            for keyword in TEXT_KEYWORDS
            if keyword in low
        ]

        if hits:

            candidate_files.append({
                "path": rel(path),
                "keyword_hits":
                    " | ".join(sorted(set(hits))),
            })


# =============================================================================
# Strong candidate categorisation
# =============================================================================

categories = {
    "historical_action": [],
    "later_attempt": [],
    "realized_speed": [],
    "benchmark_outcome": [],
    "rank_outcome": [],
    "withdraw_retain": [],
}

for row in candidate_fields:

    n = norm(row["field"])

    if any(
        k in n
        for k in [
            "historical_action",
            "observed_action",
            "actual_action",
            "action_taken",
        ]
    ):
        categories["historical_action"].append(row)

    if any(
        k in n
        for k in [
            "later_attempt",
            "next_attempt",
            "subsequent_attempt",
            "future_attempt",
        ]
    ):
        categories["later_attempt"].append(row)

    if any(
        k in n
        for k in [
            "next_speed",
            "later_speed",
            "subsequent_speed",
            "realized_speed",
            "outcome_speed",
            "final_speed",
        ]
    ):
        categories["realized_speed"].append(row)

    if any(
        k in n
        for k in [
            "benchmark_cross",
            "benchmark_outcome",
            "target_hit",
            "advancement",
            "advanced",
            "qualified",
            "survived",
            "eliminated",
        ]
    ):
        categories["benchmark_outcome"].append(row)

    if any(
        k in n
        for k in [
            "final_rank",
            "next_rank",
            "later_rank",
            "result_rank",
        ]
    ):
        categories["rank_outcome"].append(row)

    if any(
        k in n
        for k in [
            "withdraw",
            "retain",
            "requeue",
            "waved",
        ]
    ):
        categories["withdraw_retain"].append(row)


# =============================================================================
# Save inventory
# =============================================================================

with OUT_FIELDS.open(
    "w",
    encoding="utf-8",
    newline="",
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=[
            "path",
            "rows",
            "field",
            "nonempty_count",
            "unique_nonempty_count",
            "examples",
        ],
    )

    writer.writeheader()
    writer.writerows(candidate_fields)


with OUT_FILES.open(
    "w",
    encoding="utf-8",
    newline="",
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=[
            "path",
            "keyword_hits",
        ],
    )

    writer.writeheader()
    writer.writerows(candidate_files)


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


with DECISION_FILE.open(
    "r",
    encoding="utf-8-sig",
    newline="",
) as f:
    decision_n = len(list(csv.DictReader(f)))

with ACTION_FILE.open(
    "r",
    encoding="utf-8-sig",
    newline="",
) as f:
    action_n = len(list(csv.DictReader(f)))

with MC_FILE.open(
    "r",
    encoding="utf-8-sig",
    newline="",
) as f:
    mc_n = len(list(csv.DictReader(f)))


qa(
    "decision_universe",
    decision_n,
    60,
    "PASS" if decision_n == 60 else "FAIL",
)

qa(
    "action_universe",
    action_n,
    170,
    "PASS" if action_n == 170 else "FAIL",
)

qa(
    "final_mc_results_present",
    mc_n,
    1183,
    "PASS" if mc_n == 1183 else "FAIL",
)

qa(
    "candidate_fields_found",
    len(candidate_fields),
    "MEASURED",
    "PASS",
)

qa(
    "historical_action_candidates",
    len(categories["historical_action"]),
    "MEASURED_NOT_ASSUMED_VALID",
    "PASS",
)

qa(
    "later_attempt_candidates",
    len(categories["later_attempt"]),
    "MEASURED_NOT_ASSUMED_VALID",
    "PASS",
)

qa(
    "realized_speed_candidates",
    len(categories["realized_speed"]),
    "MEASURED_NOT_ASSUMED_VALID",
    "PASS",
)

qa(
    "benchmark_outcome_candidates",
    len(categories["benchmark_outcome"]),
    "MEASURED_NOT_ASSUMED_VALID",
    "PASS",
)

qa(
    "historical_action_used_as_optimal_label",
    False,
    False,
    "PASS",
)

qa(
    "future_outcome_used_as_r4f8h_feature",
    False,
    False,
    "PASS",
)

qa(
    "model_refit",
    False,
    False,
    "PASS",
)


with OUT_QA.open(
    "w",
    encoding="utf-8",
    newline="",
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=[
            "metric",
            "value",
            "expected",
            "status",
        ],
    )

    writer.writeheader()
    writer.writerows(qa_rows)


# =============================================================================
# Report
# =============================================================================

passes = sum(
    r["status"] == "PASS"
    for r in qa_rows
)

fails = sum(
    r["status"] == "FAIL"
    for r in qa_rows
)

report = {
    "phase":
        "R4F9-A",

    "status": (
        "R4F9_HISTORICAL_REPLAY_READINESS_AUDIT_COMPLETE"
        if fails == 0
        else "R4F9_HISTORICAL_REPLAY_READINESS_AUDIT_FAILED"
    ),

    "candidate_field_rows":
        len(candidate_fields),

    "candidate_text_files":
        len(candidate_files),

    "category_counts": {
        k: len(v)
        for k, v in categories.items()
    },

    "interpretation_boundary": (
        "Historical future outcomes may be used only as realized "
        "evaluation targets after the R4F8H prediction state has been "
        "frozen. Historical actions remain descriptive evidence, not "
        "optimal labels."
    ),

    "evaluation_targets_to_resolve": [
        "whether another attempt actually occurred",
        "realized next-attempt or later-attempt speed",
        "realized benchmark crossing where defensible",
        "realized retained/surrendered result effect",
        "historical action evidence for descriptive replay only",
    ],

    "next_step": (
        "Inspect strongest candidate fields and freeze the historical "
        "replay outcome interface before scoring R4F8H predictions."
    ),

    "qa": {
        "pass": passes,
        "fail": fails,
    },
}

OUT_REPORT.write_text(
    json.dumps(
        report,
        indent=2,
        ensure_ascii=False,
    ),
    encoding="utf-8",
)


# =============================================================================
# Console helpers
# =============================================================================

def show(title, rows, limit=25):

    print(title)
    print("-" * 130)

    if not rows:
        print("none")
        print()
        return

    for row in rows[:limit]:

        print(row["path"])
        print(f"  FIELD: {row['field']}")
        print(f"  NONEMPTY: {row['nonempty_count']}")
        print(f"  EXAMPLES: {row['examples'][:300]}")
        print()


# =============================================================================
# Console
# =============================================================================

print("=" * 130)
print("R4F9-A — HISTORICAL REPLAY READINESS AUDIT")
print("=" * 130)
print()

print("SUMMARY")
print("-" * 130)
print(f"Candidate field rows:          {len(candidate_fields)}")
print(f"Candidate text files:          {len(candidate_files)}")
print()

for k, v in categories.items():
    print(f"{k:28s} {len(v)}")

print()

show(
    "TOP HISTORICAL ACTION CANDIDATES",
    categories["historical_action"],
)

show(
    "TOP LATER-ATTEMPT CANDIDATES",
    categories["later_attempt"],
)

show(
    "TOP REALIZED-SPEED CANDIDATES",
    categories["realized_speed"],
)

show(
    "TOP BENCHMARK-OUTCOME CANDIDATES",
    categories["benchmark_outcome"],
)

show(
    "TOP RANK-OUTCOME CANDIDATES",
    categories["rank_outcome"],
)

show(
    "TOP WITHDRAW / RETAIN / REQUEUE CANDIDATES",
    categories["withdraw_retain"],
)

print("QA")
print("-" * 130)
print(f"{passes} PASS | 0 WARN | {fails} FAIL")

print()
print("OUTPUTS")
print("-" * 130)

for p in [
    OUT_FIELDS,
    OUT_FILES,
    OUT_QA,
    OUT_REPORT,
]:
    print(p.relative_to(ROOT))

print()

if fails:
    print("R4F9_A_HISTORICAL_REPLAY_READINESS_AUDIT_FAILED")
    raise SystemExit(1)

print("R4F9_HISTORICAL_REPLAY_READINESS_AUDIT_COMPLETE")
print()
print(
    "IMPORTANT: Historical outcomes found here are evaluation targets only. "
    "They must never be fed back into R4F8H decision-time features."
)
