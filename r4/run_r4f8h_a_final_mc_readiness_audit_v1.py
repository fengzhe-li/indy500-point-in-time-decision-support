from pathlib import Path
import csv
import json
import hashlib
from collections import Counter, defaultdict

ROOT = Path("/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈")
OUT = ROOT / "r4" / "output"

# =============================================================================
# R4F8H-A — FINAL ACTION MONTE CARLO READINESS AUDIT
#
# PURPOSE
# -------
# Read-only inspection of the frozen R4F8E/F/G interfaces before implementing
# the final action-conditioned Monte Carlo.
#
# This script:
#   - DOES NOT run Monte Carlo
#   - DOES NOT modify frozen inputs
#   - DOES NOT infer missing timestamps/session remaining
#   - DOES NOT reuse old R4P11 probabilities
#   - DOES NOT retune the frozen performance model
#
# It produces only new R4F8H-A audit outputs.
# =============================================================================

CANDIDATE_FILES = {
    "f8e_decision": [
        "r4f8e_reconstructed_decision_numeric_state_v1.csv",
        "r4f8e_final_mc_decision_interface_v1.csv",
    ],
    "f8e_action": [
        "r4f8e_reconstructed_action_numeric_interface_v1.csv",
        "r4f8e_final_mc_action_numeric_interface_v1.csv",
    ],
    "f8f_wait_params": [
        "r4f8f_action_wait_distribution_parameters_v1.csv",
    ],
    "f8f_wait_support": [
        "r4f8f_wait_support_summary_v1.csv",
    ],
    "f8g_decision_uncertainty": [
        "r4f8g_decision_predictive_uncertainty_state_v1.csv",
    ],
    "f8g_uncertainty_params": [
        "r4f8g_uncertainty_parameters_v1.csv",
    ],
}

OUT_SCHEMA = OUT / "r4f8h_a_input_schema_inventory_v1.csv"
OUT_JOIN = OUT / "r4f8h_a_join_key_readiness_v1.csv"
OUT_ACTION = OUT / "r4f8h_a_action_readiness_v1.csv"
OUT_DECISION = OUT / "r4f8h_a_decision_readiness_v1.csv"
OUT_QA = OUT / "r4f8h_a_final_mc_readiness_qa_v1.csv"
OUT_REPORT = OUT / "r4f8h_a_final_mc_readiness_report_v1.json"


def clean(v):
    if v is None:
        return ""
    return str(v).strip()


def truthy(v):
    return clean(v).lower() in {"1", "true", "yes", "y", "t"}


def num(v):
    s = clean(v)
    if not s:
        return None
    try:
        x = float(s)
        if x == x and abs(x) != float("inf"):
            return x
    except Exception:
        return None
    return None


def read_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return reader.fieldnames or [], list(reader)


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def first_existing(candidates):
    for name in candidates:
        p = OUT / name
        if p.exists():
            return p
    return None


def find_field(fields, candidates):
    """
    Conservative resolver.
    Match exact normalized field names only.
    """
    norm = {}
    for f in fields:
        key = (
            f.lower()
            .strip()
            .replace("-", "_")
            .replace(" ", "_")
        )
        norm[key] = f

    for c in candidates:
        key = (
            c.lower()
            .strip()
            .replace("-", "_")
            .replace(" ", "_")
        )
        if key in norm:
            return norm[key]
    return None


# =============================================================================
# Resolve files
# =============================================================================

resolved = {}
missing_groups = []

for group, candidates in CANDIDATE_FILES.items():
    p = first_existing(candidates)
    if p is None:
        missing_groups.append(group)
    else:
        resolved[group] = p

required_groups = {
    "f8e_decision",
    "f8e_action",
    "f8f_wait_params",
    "f8g_decision_uncertainty",
}

missing_required = sorted(required_groups - set(resolved))

if missing_required:
    print("=" * 120)
    print("R4F8H-A — REQUIRED INPUT FILES MISSING")
    print("=" * 120)
    for g in missing_required:
        print(f"MISSING GROUP: {g}")
        for c in CANDIDATE_FILES[g]:
            print(f"  tried: r4/output/{c}")
    raise SystemExit(1)


# =============================================================================
# Load
# =============================================================================

datasets = {}

for group, path in resolved.items():
    fields, rows = read_csv(path)
    datasets[group] = {
        "path": path,
        "fields": fields,
        "rows": rows,
    }


# =============================================================================
# Schema inventory
# =============================================================================

schema_rows = []

for group, data in datasets.items():
    fields = data["fields"]
    rows = data["rows"]

    for field in fields:
        nonempty = sum(bool(clean(r.get(field))) for r in rows)
        numeric = sum(num(r.get(field)) is not None for r in rows)

        examples = []
        for r in rows:
            v = clean(r.get(field))
            if v and v not in examples:
                examples.append(v)
            if len(examples) >= 3:
                break

        schema_rows.append({
            "dataset_group": group,
            "filename": data["path"].name,
            "dataset_rows": len(rows),
            "field": field,
            "nonempty_rows": nonempty,
            "numeric_rows": numeric,
            "example_values": " | ".join(examples),
        })

with OUT_SCHEMA.open("w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=list(schema_rows[0].keys()))
    writer.writeheader()
    writer.writerows(schema_rows)


# =============================================================================
# Resolve key semantic fields
# =============================================================================

dec_fields = datasets["f8e_decision"]["fields"]
dec_rows = datasets["f8e_decision"]["rows"]

act_fields = datasets["f8e_action"]["fields"]
act_rows = datasets["f8e_action"]["rows"]

wait_fields = datasets["f8f_wait_params"]["fields"]
wait_rows = datasets["f8f_wait_params"]["rows"]

unc_fields = datasets["f8g_decision_uncertainty"]["fields"]
unc_rows = datasets["f8g_decision_uncertainty"]["rows"]


semantic_candidates = {
    "decision_id": [
        "fused_decision_id",
        "decision_id",
        "source_decision_id",
    ],
    "action": [
        "feasible_action",
        "action",
    ],
    "regime": [
        "regime",
        "session_regime",
        "qualifying_regime",
    ],
    "protected": [
        "protected_result_exists",
        "has_protected_result",
    ],
    "current_speed": [
        "current_best_speed_mph",
        "current_result_mph",
        "protected_result_speed_mph",
        "current_speed_mph",
    ],
    "protected_speed": [
        "protected_result_speed_mph",
        "current_protected_result_speed_mph",
    ],
    "rank": [
        "current_rank",
        "current_best_rank",
        "rank",
    ],
    "benchmark_speed": [
        "benchmark_speed_mph",
        "regime_benchmark_speed_mph",
        "cutoff_speed_mph",
        "advancement_benchmark_speed_mph",
    ],
    "benchmark_rank": [
        "benchmark_rank",
        "cutoff_rank",
        "benchmark_position",
    ],
    "decision_time": [
        "decision_time_utc",
        "decision_timestamp_utc",
        "time_point_utc",
    ],
    "session_remaining": [
        "session_remaining_minutes",
        "session_remaining_min",
        "remaining_minutes",
    ],
    "driver": [
        "driver_name",
        "driver",
        "normalized_driver_name",
    ],
    "year": [
        "year",
        "season",
    ],
    "source_attempt": [
        "source_attempt_id",
        "attempt_id",
        "canonical_attempt_id",
    ],
    "wait_distribution_id": [
        "wait_distribution_id",
        "distribution_id",
        "wait_model_id",
    ],
    "wait_mean": [
        "mean_wait_minutes",
        "wait_mean_minutes",
        "mean_minutes",
    ],
    "wait_median": [
        "median_wait_minutes",
        "q50_wait_minutes",
        "median_minutes",
    ],
    "wait_q95": [
        "q95_wait_minutes",
        "wait_q95_minutes",
        "q95_minutes",
    ],
    "predictive_mean": [
        "predictive_mean_speed_mph",
        "predicted_speed_mph",
        "predictive_mean_mph",
        "mean_speed_mph",
    ],
    "predictive_sd": [
        "predictive_sd_mph",
        "prediction_sd_mph",
        "sd_mph",
        "predictive_scale_mph",
    ],
    "q05": [
        "q05_mph",
        "predictive_q05_mph",
        "q05_speed_mph",
    ],
    "q50": [
        "q50_mph",
        "predictive_q50_mph",
        "q50_speed_mph",
    ],
    "q95": [
        "q95_mph",
        "predictive_q95_mph",
        "q95_speed_mph",
    ],
    "sample_ready": [
        "sample_ready",
        "performance_sample_ready",
        "sampleable",
        "performance_sampleable",
    ],
}


resolved_fields = {
    "decision": {
        k: find_field(dec_fields, v)
        for k, v in semantic_candidates.items()
    },
    "action": {
        k: find_field(act_fields, v)
        for k, v in semantic_candidates.items()
    },
    "wait": {
        k: find_field(wait_fields, v)
        for k, v in semantic_candidates.items()
    },
    "uncertainty": {
        k: find_field(unc_fields, v)
        for k, v in semantic_candidates.items()
    },
}


# =============================================================================
# Join-key readiness
# =============================================================================

join_rows = []

for semantic in [
    "decision_id",
    "action",
    "regime",
    "protected",
    "wait_distribution_id",
    "predictive_mean",
    "predictive_sd",
    "sample_ready",
]:
    row = {"semantic": semantic}

    for group_label, source_key in [
        ("decision", "decision"),
        ("action", "action"),
        ("wait", "wait"),
        ("uncertainty", "uncertainty"),
    ]:
        f = resolved_fields[source_key][semantic]
        row[f"{group_label}_field"] = f or ""

        if source_key == "decision":
            rows = dec_rows
        elif source_key == "action":
            rows = act_rows
        elif source_key == "wait":
            rows = wait_rows
        else:
            rows = unc_rows

        row[f"{group_label}_nonempty"] = (
            sum(bool(clean(r.get(f))) for r in rows)
            if f
            else 0
        )

    join_rows.append(row)

with OUT_JOIN.open("w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=list(join_rows[0].keys()))
    writer.writeheader()
    writer.writerows(join_rows)


# =============================================================================
# Decision readiness
# =============================================================================

decision_id_field = resolved_fields["decision"]["decision_id"]
if decision_id_field is None:
    raise SystemExit("Could not resolve decision ID in F8E decision interface.")

unc_decision_id_field = resolved_fields["uncertainty"]["decision_id"]
if unc_decision_id_field is None:
    raise SystemExit("Could not resolve decision ID in F8G uncertainty interface.")

unc_by_id = defaultdict(list)
for r in unc_rows:
    unc_by_id[clean(r.get(unc_decision_id_field))].append(r)

decision_readiness = []

for d in dec_rows:
    did = clean(d.get(decision_id_field))
    unc_matches = unc_by_id.get(did, [])

    def value(semantic):
        f = resolved_fields["decision"][semantic]
        return clean(d.get(f)) if f else ""

    u = unc_matches[0] if len(unc_matches) == 1 else {}

    def uvalue(semantic):
        f = resolved_fields["uncertainty"][semantic]
        return clean(u.get(f)) if f and u else ""

    current_speed = value("current_speed")
    protected_speed = value("protected_speed")
    benchmark_speed = value("benchmark_speed")
    benchmark_rank = value("benchmark_rank")
    rank = value("rank")
    decision_time = value("decision_time")
    session_remaining = value("session_remaining")

    pred_mean = uvalue("predictive_mean")
    pred_sd = uvalue("predictive_sd")
    q05 = uvalue("q05")
    q50 = uvalue("q50")
    q95 = uvalue("q95")

    sample_ready_field = resolved_fields["uncertainty"]["sample_ready"]
    if sample_ready_field and u:
        performance_sample_ready = truthy(u.get(sample_ready_field))
    else:
        # Conservative fallback:
        # only consider sample-ready if both predictive center and scale exist.
        performance_sample_ready = (
            num(pred_mean) is not None
            and num(pred_sd) is not None
            and num(pred_sd) > 0
        )

    decision_readiness.append({
        "fused_decision_id": did,
        "year": value("year"),
        "driver": value("driver"),
        "regime": value("regime"),
        "protected_result_exists": value("protected"),
        "current_speed_available": bool(current_speed),
        "protected_speed_available": bool(protected_speed),
        "rank_available": bool(rank),
        "benchmark_speed_available": bool(benchmark_speed),
        "benchmark_rank_available": bool(benchmark_rank),
        "decision_time_available": bool(decision_time),
        "session_remaining_available": bool(session_remaining),
        "uncertainty_match_count": len(unc_matches),
        "predictive_mean_available": num(pred_mean) is not None,
        "predictive_sd_available": (
            num(pred_sd) is not None
            and num(pred_sd) > 0
        ),
        "predictive_q05_available": num(q05) is not None,
        "predictive_q50_available": num(q50) is not None,
        "predictive_q95_available": num(q95) is not None,
        "performance_sample_ready": performance_sample_ready,
    })

with OUT_DECISION.open("w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=list(decision_readiness[0].keys())
    )
    writer.writeheader()
    writer.writerows(decision_readiness)


# =============================================================================
# Action readiness
# =============================================================================

action_decision_id_field = resolved_fields["action"]["decision_id"]
action_field = resolved_fields["action"]["action"]
action_regime_field = resolved_fields["action"]["regime"]

if action_decision_id_field is None:
    raise SystemExit("Could not resolve decision ID in F8E action interface.")

if action_field is None:
    raise SystemExit("Could not resolve action field in F8E action interface.")

# Build decision-readiness lookup
decision_ready_by_id = {
    r["fused_decision_id"]: r
    for r in decision_readiness
}

# Resolve wait action/regime/distribution fields
wait_action_field = resolved_fields["wait"]["action"]
wait_regime_field = resolved_fields["wait"]["regime"]
wait_dist_field = resolved_fields["wait"]["wait_distribution_id"]
wait_mean_field = resolved_fields["wait"]["wait_mean"]
wait_median_field = resolved_fields["wait"]["wait_median"]
wait_q95_field = resolved_fields["wait"]["wait_q95"]

# candidate matching helper
def wait_matches(regime, action):
    matches = []
    for w in wait_rows:
        a_ok = (
            clean(w.get(wait_action_field)) == action
            if wait_action_field
            else False
        )

        if wait_regime_field:
            r_ok = clean(w.get(wait_regime_field)) == regime
        else:
            r_ok = True

        if a_ok and r_ok:
            matches.append(w)

    # fallback to action-only ONLY if no regime field exists.
    return matches


action_readiness = []

for a in act_rows:
    did = clean(a.get(action_decision_id_field))
    action = clean(a.get(action_field))
    regime = (
        clean(a.get(action_regime_field))
        if action_regime_field
        else clean(
            next(
                (
                    d.get(resolved_fields["decision"]["regime"], "")
                    for d in dec_rows
                    if clean(d.get(decision_id_field)) == did
                ),
                ""
            )
        )
    )

    dr = decision_ready_by_id.get(did, {})
    wm = wait_matches(regime, action)

    # STOP is valid deterministic zero-wait even if matching representation differs.
    is_stop = action == "STOP"

    wait_model_found = bool(wm) or is_stop

    wait_mean = None
    wait_median = None
    wait_q95 = None
    wait_distribution_id = ""

    if is_stop:
        wait_mean = 0.0
        wait_median = 0.0
        wait_q95 = 0.0
        wait_distribution_id = "DETERMINISTIC_ZERO_WAIT"
    elif len(wm) == 1:
        w = wm[0]
        if wait_mean_field:
            wait_mean = num(w.get(wait_mean_field))
        if wait_median_field:
            wait_median = num(w.get(wait_median_field))
        if wait_q95_field:
            wait_q95 = num(w.get(wait_q95_field))
        if wait_dist_field:
            wait_distribution_id = clean(w.get(wait_dist_field))

    performance_ready = bool(
        dr.get("performance_sample_ready", False)
    )

    current_state_ready = (
        bool(dr.get("rank_available", False))
        and (
            bool(dr.get("benchmark_speed_available", False))
            or bool(dr.get("benchmark_rank_available", False))
        )
    )

    # NOTE:
    # cutoff_ready is intentionally false unless actual decision-safe
    # session-remaining information exists.
    cutoff_ready = bool(
        dr.get("session_remaining_available", False)
    )

    action_readiness.append({
        "fused_decision_id": did,
        "regime": regime,
        "feasible_action": action,
        "performance_sample_ready": performance_ready,
        "wait_model_match_count": len(wm),
        "wait_model_ready": wait_model_found,
        "wait_distribution_id": wait_distribution_id,
        "wait_mean_minutes": (
            "" if wait_mean is None else wait_mean
        ),
        "wait_median_minutes": (
            "" if wait_median is None else wait_median
        ),
        "wait_q95_minutes": (
            "" if wait_q95 is None else wait_q95
        ),
        "current_state_ready": current_state_ready,
        "decision_time_available": bool(
            dr.get("decision_time_available", False)
        ),
        "session_remaining_available": bool(
            dr.get("session_remaining_available", False)
        ),
        "cutoff_completion_ready": cutoff_ready,
        "pre_mc_core_ready_except_cutoff": (
            current_state_ready
            and wait_model_found
            and (
                performance_ready
                if not is_stop
                else True
            )
        ),
    })

with OUT_ACTION.open("w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=list(action_readiness[0].keys())
    )
    writer.writeheader()
    writer.writerows(action_readiness)


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
    "decision_rows",
    len(dec_rows),
    60,
    "PASS" if len(dec_rows) == 60 else "FAIL",
)

qa(
    "action_rows",
    len(act_rows),
    170,
    "PASS" if len(act_rows) == 170 else "FAIL",
)

decision_ids = [clean(r.get(decision_id_field)) for r in dec_rows]

qa(
    "unique_decision_ids",
    len(set(decision_ids)),
    60,
    "PASS"
    if len(set(decision_ids)) == 60 and "" not in set(decision_ids)
    else "FAIL",
)

action_counts = Counter(
    clean(r.get(action_field))
    for r in act_rows
)

qa(
    "stop_action_present",
    action_counts.get("STOP", 0),
    ">0",
    "PASS" if action_counts.get("STOP", 0) > 0 else "FAIL",
)

sample_ready_count = sum(
    bool(r["performance_sample_ready"])
    for r in decision_readiness
)

qa(
    "performance_sample_ready_decisions",
    sample_ready_count,
    59,
    "PASS" if sample_ready_count == 59 else "WARN",
)

unc_unique_match = sum(
    r["uncertainty_match_count"] == 1
    for r in decision_readiness
)

qa(
    "decisions_with_unique_uncertainty_match",
    unc_unique_match,
    60,
    "PASS" if unc_unique_match == 60 else "WARN",
)

session_remaining_count = sum(
    r["session_remaining_available"]
    for r in decision_readiness
)

qa(
    "decision_safe_exact_session_remaining",
    session_remaining_count,
    0,
    "PASS" if session_remaining_count == 0 else "WARN",
)

decision_time_count = sum(
    r["decision_time_available"]
    for r in decision_readiness
)

qa(
    "decision_timestamp_available",
    decision_time_count,
    50,
    "PASS" if decision_time_count == 50 else "WARN",
)

wait_ready_nonstop = [
    r
    for r in action_readiness
    if r["feasible_action"] != "STOP"
]

wait_ready_count = sum(
    bool(r["wait_model_ready"])
    for r in wait_ready_nonstop
)

qa(
    "nonstop_actions_with_wait_model",
    wait_ready_count,
    len(wait_ready_nonstop),
    (
        "PASS"
        if wait_ready_count == len(wait_ready_nonstop)
        else "FAIL"
    ),
)

stop_rows = [
    r
    for r in action_readiness
    if r["feasible_action"] == "STOP"
]

stop_zero_ok = all(
    num(r["wait_mean_minutes"]) == 0.0
    and num(r["wait_median_minutes"]) == 0.0
    and num(r["wait_q95_minutes"]) == 0.0
    for r in stop_rows
)

qa(
    "stop_wait_deterministic_zero",
    stop_zero_ok,
    True,
    "PASS" if stop_zero_ok else "FAIL",
)

core_ready_except_cutoff = sum(
    bool(r["pre_mc_core_ready_except_cutoff"])
    for r in action_readiness
)

qa(
    "action_rows_core_ready_except_cutoff",
    core_ready_except_cutoff,
    "<=170; report measured",
    (
        "PASS"
        if core_ready_except_cutoff >= 160
        else "WARN"
    ),
)

cutoff_ready_count = sum(
    bool(r["cutoff_completion_ready"])
    for r in action_readiness
)

qa(
    "actions_with_decision_safe_cutoff_completion_input",
    cutoff_ready_count,
    0,
    "PASS" if cutoff_ready_count == 0 else "WARN",
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

fails = [r for r in qa_rows if r["status"] == "FAIL"]
warns = [r for r in qa_rows if r["status"] == "WARN"]
passes = [r for r in qa_rows if r["status"] == "PASS"]

unready_perf = [
    r["fused_decision_id"]
    for r in decision_readiness
    if not r["performance_sample_ready"]
]

missing_current_speed = [
    r["fused_decision_id"]
    for r in decision_readiness
    if not r["current_speed_available"]
]

decision_time_missing = [
    r["fused_decision_id"]
    for r in decision_readiness
    if not r["decision_time_available"]
]

report = {
    "phase": "R4F8H-A",
    "purpose": (
        "Final Action Monte Carlo readiness audit only; "
        "no Monte Carlo executed."
    ),
    "input_files": {
        k: {
            "path": str(v["path"].relative_to(ROOT)),
            "rows": len(v["rows"]),
            "sha256": sha256(v["path"]),
        }
        for k, v in datasets.items()
    },
    "authoritative_universe": {
        "decision_rows": len(dec_rows),
        "action_rows": len(act_rows),
        "action_counts": dict(sorted(action_counts.items())),
    },
    "decision_readiness": {
        "performance_sample_ready": sample_ready_count,
        "decision_time_available": decision_time_count,
        "session_remaining_available": session_remaining_count,
        "unready_performance_decision_ids": unready_perf,
        "missing_current_speed_decision_ids": missing_current_speed,
        "missing_decision_time_decision_ids": decision_time_missing,
    },
    "action_readiness": {
        "nonstop_action_rows": len(wait_ready_nonstop),
        "nonstop_wait_model_ready": wait_ready_count,
        "core_ready_except_cutoff": core_ready_except_cutoff,
        "cutoff_completion_ready": cutoff_ready_count,
    },
    "cutoff_completion_status": (
        "UNRESOLVED_DECISION_SAFE_SESSION_REMAINING"
        if cutoff_ready_count == 0
        else "PARTIALLY_AVAILABLE"
    ),
    "research_integrity": {
        "final_mc_run": False,
        "old_r4p11_final_probabilities_used": False,
        "future_outcomes_used": False,
        "fake_session_remaining_created": False,
        "fake_last_chance_timestamp_created": False,
        "performance_model_refit": False,
    },
    "qa": {
        "pass": len(passes),
        "warn": len(warns),
        "fail": len(fails),
    },
    "next_step_if_no_fail": (
        "Resolve the cutoff/completion policy and then implement "
        "R4F8H final action-conditioned Monte Carlo."
    ),
}

OUT_REPORT.write_text(
    json.dumps(report, indent=2, ensure_ascii=False),
    encoding="utf-8",
)


# =============================================================================
# Console summary
# =============================================================================

print("=" * 120)
print("R4F8H-A — FINAL ACTION MONTE CARLO READINESS AUDIT")
print("=" * 120)
print()

print("INPUT FILES")
print("-" * 120)
for group, data in datasets.items():
    print(
        f"{group:28s} | "
        f"{data['path'].name:60s} | "
        f"rows={len(data['rows'])}"
    )

print()
print("UNIVERSE")
print("-" * 120)
print(f"Decision rows: {len(dec_rows)}")
print(f"Action rows:   {len(act_rows)}")
print("Action counts:")
for k, v in sorted(action_counts.items()):
    print(f"  {k:45s} {v}")

print()
print("DECISION READINESS")
print("-" * 120)
print(
    f"Performance sample-ready:       "
    f"{sample_ready_count}/{len(dec_rows)}"
)
print(
    f"Decision timestamp available:   "
    f"{decision_time_count}/{len(dec_rows)}"
)
print(
    f"Exact session remaining:        "
    f"{session_remaining_count}/{len(dec_rows)}"
)

print()
print("ACTION READINESS")
print("-" * 120)
print(
    f"Non-STOP wait-model ready:      "
    f"{wait_ready_count}/{len(wait_ready_nonstop)}"
)
print(
    f"Core ready except cutoff:       "
    f"{core_ready_except_cutoff}/{len(act_rows)}"
)
print(
    f"Cutoff-completion input ready:  "
    f"{cutoff_ready_count}/{len(act_rows)}"
)

print()
print("UNRESOLVED PERFORMANCE DECISIONS")
print("-" * 120)
if unready_perf:
    for x in unready_perf:
        print(f"  {x}")
else:
    print("  none")

print()
print("QA")
print("-" * 120)
print(
    f"{len(passes)} PASS | "
    f"{len(warns)} WARN | "
    f"{len(fails)} FAIL"
)
for r in qa_rows:
    if r["status"] != "PASS":
        print(
            f"{r['status']:5s} | "
            f"{r['metric']} | "
            f"value={r['value']} | "
            f"expected={r['expected']}"
        )

print()
print("OUTPUTS")
print("-" * 120)
for p in [
    OUT_SCHEMA,
    OUT_JOIN,
    OUT_DECISION,
    OUT_ACTION,
    OUT_QA,
    OUT_REPORT,
]:
    print(p.relative_to(ROOT))

print()

if fails:
    print("R4F8H_A_READINESS_AUDIT_FAILED")
    raise SystemExit(1)

print("R4F8H_A_READINESS_AUDIT_COMPLETE")
print()
print(
    "IMPORTANT: No Monte Carlo was run. "
    "Cutoff/completion policy remains unresolved unless "
    "decision-safe session remaining is actually present."
)
