from pathlib import Path
import csv
import json
import re
from collections import Counter, defaultdict

ROOT = Path("/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈")
R4 = ROOT / "r4"
OUT = R4 / "output"
WEATHER_OUT = ROOT / "weather" / "output"

OUT_FIELDS = OUT / "r4f8h_d_competitor_evolution_candidate_fields_v1.csv"
OUT_FILES = OUT / "r4f8h_d_competitor_evolution_candidate_files_v1.csv"
OUT_QA = OUT / "r4f8h_d_competitor_evolution_evidence_qa_v1.csv"
OUT_REPORT = OUT / "r4f8h_d_competitor_evolution_evidence_report_v1.json"

# =============================================================================
# R4F8H-D — COMPETITIVE STATE EVOLUTION EVIDENCE AUDIT
#
# PURPOSE
# -------
# Determine whether the existing repository contains a defensible,
# decision-safe representation of how leaderboard / benchmark / competitor
# state evolves after a decision while the focal car waits and reattempts.
#
# READ-ONLY with respect to frozen project assets.
#
# DOES NOT:
# - run final Monte Carlo
# - fit a new model
# - use future outcomes as current decision features
# - assume benchmark is static
# - fabricate competitor attempts
# - reinterpret historical actions as optimal labels
# =============================================================================

FIELD_KEYWORDS = [
    "leaderboard",
    "rank",
    "position",
    "cutoff",
    "benchmark",
    "competitor",
    "field_state",
    "field_mean",
    "field_speed",
    "future_field",
    "future_rank",
    "rank_change",
    "benchmark_change",
    "cutoff_change",
    "leaderboard_change",
    "later_attempt",
    "future_attempt",
    "session_progress",
    "elapsed",
    "throughput",
    "attempt_rate",
    "runs_per",
    "completion_rate",
    "event_rate",
]

TEXT_KEYWORDS = [
    "competitor evolution",
    "leaderboard evolution",
    "benchmark evolution",
    "cutoff evolution",
    "future leaderboard",
    "future competitor",
    "rank evolution",
    "field evolution",
    "attempt throughput",
    "runs per hour",
    "attempts per hour",
    "session progression",
    "later competitors",
    "subsequent attempts",
    "future attempts",
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


def norm(v):
    return re.sub(
        r"[^a-z0-9]+",
        "_",
        str(v).lower(),
    ).strip("_")


def field_relevant(field):
    n = norm(field)

    # Prevent absurdly broad matches where possible.
    exactish = [
        norm(k)
        for k in FIELD_KEYWORDS
    ]

    return any(k in n for k in exactish)


def file_allowed(path):
    if path.suffix.lower() not in SCAN_EXTENSIONS:
        return False

    if any(part in SKIP_DIR_NAMES for part in path.parts):
        return False

    return True


def rel(path):
    try:
        return str(path.relative_to(ROOT))
    except Exception:
        return str(path)


# =============================================================================
# 1. CSV schema / populated-field audit
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
                field
                for field in fields
                if field_relevant(field)
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

                if len(examples) >= 5:
                    break

            candidate_fields.append({
                "path": rel(path),
                "file_type": "csv",
                "dataset_rows": len(rows),
                "field": field,
                "nonempty_count": len(vals),
                "unique_nonempty_count": len(set(vals)),
                "example_values": " | ".join(examples),
            })

    except Exception:
        pass


# =============================================================================
# 2. JSON key audit
# =============================================================================

def walk_json(obj, prefix=""):
    hits = []

    if isinstance(obj, dict):

        for key, value in obj.items():

            p = (
                f"{prefix}.{key}"
                if prefix
                else str(key)
            )

            if field_relevant(key):
                hits.append((p, value))

            hits.extend(
                walk_json(value, p)
            )

    elif isinstance(obj, list):

        # Plenty for metadata/contracts without exploding traversal.
        for i, value in enumerate(obj[:1000]):
            hits.extend(
                walk_json(
                    value,
                    f"{prefix}[{i}]",
                )
            )

    return hits


for path in ROOT.rglob("*.json"):

    if not file_allowed(path):
        continue

    try:
        obj = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )
    except Exception:
        continue

    for key_path, value in walk_json(obj):

        if isinstance(value, (dict, list)):
            example = f"<{type(value).__name__}>"
        else:
            example = clean(value)

        candidate_fields.append({
            "path": rel(path),
            "file_type": "json",
            "dataset_rows": "",
            "field": key_path,
            "nonempty_count": 1 if example else 0,
            "unique_nonempty_count": 1 if example else 0,
            "example_values": example[:500],
        })


# =============================================================================
# 3. Text/code search
# =============================================================================

candidate_files = []

for ext in [
    ".md",
    ".txt",
    ".py",
    ".json",
]:

    for path in ROOT.rglob(f"*{ext}"):

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
            if keyword.lower() in low
        ]

        if hits:

            candidate_files.append({
                "path": rel(path),
                "file_type": ext.lstrip("."),
                "keyword_hits": " | ".join(
                    sorted(set(hits))
                ),
            })


# =============================================================================
# 4. Categorise strongest candidate fields
# =============================================================================

populated = [
    row
    for row in candidate_fields
    if str(row["nonempty_count"])
    not in {"", "0"}
]

leaderboard_candidates = []
benchmark_candidates = []
competitor_candidates = []
throughput_candidates = []
future_candidates = []

for row in populated:

    n = norm(row["field"])

    if "leaderboard" in n:
        leaderboard_candidates.append(row)

    if (
        "benchmark" in n
        or "cutoff" in n
    ):
        benchmark_candidates.append(row)

    if "competitor" in n:
        competitor_candidates.append(row)

    if (
        "throughput" in n
        or "attempt_rate" in n
        or "runs_per" in n
    ):
        throughput_candidates.append(row)

    if (
        "future" in n
        or "later" in n
        or "subsequent" in n
    ):
        future_candidates.append(row)


# =============================================================================
# 5. Identify files that MAY be particularly relevant
# =============================================================================

SPECIAL_PATTERNS = [
    "leaderboard",
    "competitor",
    "throughput",
    "cutoff",
    "benchmark",
    "decision_time",
    "observable_state",
    "monte_carlo",
    "action_envelope",
    "session",
]

special_file_counts = Counter()

for row in populated:

    path_low = row["path"].lower()

    score = sum(
        token in path_low
        for token in SPECIAL_PATTERNS
    )

    if score:
        special_file_counts[
            row["path"]
        ] += score


# =============================================================================
# 6. Save candidate inventories
# =============================================================================

FIELDNAMES = [
    "path",
    "file_type",
    "dataset_rows",
    "field",
    "nonempty_count",
    "unique_nonempty_count",
    "example_values",
]

with OUT_FIELDS.open(
    "w",
    encoding="utf-8",
    newline="",
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=FIELDNAMES,
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
            "file_type",
            "keyword_hits",
        ],
    )

    writer.writeheader()
    writer.writerows(candidate_files)


# =============================================================================
# 7. QA
# =============================================================================

f8hc_contract = (
    OUT /
    "r4f8h_c_cutoff_completion_policy_contract_v1.json"
)

f8g_state = (
    OUT /
    "r4f8g_decision_predictive_uncertainty_state_v1.csv"
)

f8f_wait = (
    OUT /
    "r4f8f_action_wait_distribution_parameters_v1.csv"
)

f8e_actions = (
    OUT /
    "r4f8e_reconstructed_action_numeric_interface_v1.csv"
)


qa_rows = []


def add_qa(
    metric,
    value,
    expected,
    status,
):
    qa_rows.append({
        "metric": metric,
        "value": value,
        "expected": expected,
        "status": status,
    })


add_qa(
    "f8hc_cutoff_policy_present",
    f8hc_contract.exists(),
    True,
    (
        "PASS"
        if f8hc_contract.exists()
        else "FAIL"
    ),
)

add_qa(
    "f8g_uncertainty_present",
    f8g_state.exists(),
    True,
    (
        "PASS"
        if f8g_state.exists()
        else "FAIL"
    ),
)

add_qa(
    "f8f_wait_model_present",
    f8f_wait.exists(),
    True,
    (
        "PASS"
        if f8f_wait.exists()
        else "FAIL"
    ),
)

add_qa(
    "f8e_action_interface_present",
    f8e_actions.exists(),
    True,
    (
        "PASS"
        if f8e_actions.exists()
        else "FAIL"
    ),
)

add_qa(
    "candidate_competitive_fields_found",
    len(candidate_fields),
    "MEASURED",
    "PASS",
)

add_qa(
    "populated_competitive_fields_found",
    len(populated),
    "MEASURED",
    "PASS",
)

add_qa(
    "leaderboard_candidates_found",
    len(leaderboard_candidates),
    "MEASURED_NOT_ASSUMED_VALID",
    "PASS",
)

add_qa(
    "benchmark_candidates_found",
    len(benchmark_candidates),
    "MEASURED_NOT_ASSUMED_VALID",
    "PASS",
)

add_qa(
    "competitor_candidates_found",
    len(competitor_candidates),
    "MEASURED_NOT_ASSUMED_VALID",
    "PASS",
)

add_qa(
    "throughput_candidates_found",
    len(throughput_candidates),
    "MEASURED_NOT_ASSUMED_VALID",
    "PASS",
)

add_qa(
    "future_state_candidates_found",
    len(future_candidates),
    "MEASURED_NOT_ASSUMED_VALID",
    "PASS",
)

add_qa(
    "final_monte_carlo_executed",
    False,
    False,
    "PASS",
)

add_qa(
    "future_outcomes_promoted_to_decision_features",
    False,
    False,
    "PASS",
)

add_qa(
    "competitor_evolution_fabricated",
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
# 8. Report
# =============================================================================

fails = sum(
    r["status"] == "FAIL"
    for r in qa_rows
)

warns = sum(
    r["status"] == "WARN"
    for r in qa_rows
)

passes = sum(
    r["status"] == "PASS"
    for r in qa_rows
)


report = {
    "phase":
        "R4F8H-D",

    "purpose":
        "Competitive-state evolution evidence audit before final MC.",

    "candidate_field_rows":
        len(candidate_fields),

    "populated_candidate_field_rows":
        len(populated),

    "candidate_categories": {
        "leaderboard":
            len(leaderboard_candidates),
        "benchmark_or_cutoff":
            len(benchmark_candidates),
        "competitor":
            len(competitor_candidates),
        "throughput":
            len(throughput_candidates),
        "future_or_later_state":
            len(future_candidates),
    },

    "top_candidate_paths":
        special_file_counts.most_common(30),

    "text_candidate_files":
        len(candidate_files),

    "interpretation_boundary": (
        "A current leaderboard/benchmark field is not itself a "
        "competitor-evolution model. A historical later outcome is also "
        "not automatically decision-safe for simulation. Candidate sources "
        "must be inspected semantically before use."
    ),

    "allowed_downstream_options": [
        (
            "If a defensible frozen competitor-evolution component exists, "
            "join it into final action MC."
        ),
        (
            "If only static current benchmark exists, final MC may report "
            "speed-vs-current-benchmark results but must not claim dynamic "
            "future rank probabilities."
        ),
        (
            "If only structural throughput/session-progress evidence exists, "
            "freeze a structural competitor-evolution sensitivity component "
            "and label it explicitly."
        ),
    ],

    "research_integrity": {
        "final_mc_run":
            False,
        "future_outcome_leakage":
            False,
        "competitor_evolution_fabricated":
            False,
        "historical_action_used_as_optimal_label":
            False,
    },

    "qa": {
        "pass":
            passes,
        "warn":
            warns,
        "fail":
            fails,
    },

    "next_step": (
        "Inspect strongest competitor/leaderboard/benchmark evolution "
        "candidates and freeze the allowed competitive-state treatment "
        "before final action-conditioned Monte Carlo."
    ),
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
# Console helper
# =============================================================================

def print_rows(title, rows, limit=30):

    print(title)
    print("-" * 130)

    if not rows:
        print("  none")
        print()
        return

    for row in rows[:limit]:

        print(row["path"])
        print(
            f"  FIELD: {row['field']}"
        )
        print(
            f"  NONEMPTY: "
            f"{row['nonempty_count']}"
        )
        print(
            f"  EXAMPLES: "
            f"{row['example_values'][:250]}"
        )
        print()


# =============================================================================
# Console
# =============================================================================

print("=" * 130)
print(
    "R4F8H-D — COMPETITIVE STATE EVOLUTION EVIDENCE AUDIT"
)
print("=" * 130)
print()

print("SUMMARY")
print("-" * 130)

print(
    f"Candidate competitive field rows:          "
    f"{len(candidate_fields)}"
)

print(
    f"Populated competitive field rows:          "
    f"{len(populated)}"
)

print(
    f"Leaderboard candidate rows:                "
    f"{len(leaderboard_candidates)}"
)

print(
    f"Benchmark/cutoff candidate rows:           "
    f"{len(benchmark_candidates)}"
)

print(
    f"Explicit competitor candidate rows:        "
    f"{len(competitor_candidates)}"
)

print(
    f"Throughput candidate rows:                 "
    f"{len(throughput_candidates)}"
)

print(
    f"Future/later-state candidate rows:         "
    f"{len(future_candidates)}"
)

print(
    f"Text candidate files:                      "
    f"{len(candidate_files)}"
)

print()

print_rows(
    "TOP LEADERBOARD CANDIDATES",
    leaderboard_candidates,
    25,
)

print_rows(
    "TOP BENCHMARK / CUTOFF CANDIDATES",
    benchmark_candidates,
    25,
)

print_rows(
    "TOP COMPETITOR CANDIDATES",
    competitor_candidates,
    25,
)

print_rows(
    "TOP THROUGHPUT CANDIDATES",
    throughput_candidates,
    25,
)

print_rows(
    "TOP FUTURE / LATER-STATE CANDIDATES",
    future_candidates,
    25,
)

print("TOP CANDIDATE FILES")
print("-" * 130)

for path, score in special_file_counts.most_common(30):
    print(
        f"{score:3d} | {path}"
    )

if not special_file_counts:
    print("  none")

print()

print("QA")
print("-" * 130)

for row in qa_rows:

    print(
        f"{row['status']:5s} | "
        f"{row['metric']} | "
        f"value={row['value']} | "
        f"expected={row['expected']}"
    )

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
    print(
        "R4F8H_D_COMPETITIVE_STATE_EVIDENCE_AUDIT_FAILED"
    )
    raise SystemExit(1)

print(
    "R4F8H_D_COMPETITIVE_STATE_EVOLUTION_EVIDENCE_AUDIT_COMPLETE"
)

print()
print(
    "IMPORTANT: Current leaderboard state is not automatically "
    "future competitor evolution. Do not run final rank-based MC "
    "until candidate semantics are inspected."
)
