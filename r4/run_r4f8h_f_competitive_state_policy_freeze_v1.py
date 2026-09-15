from pathlib import Path
import csv
import json
import hashlib

ROOT = Path("/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈")
OUT = ROOT / "r4" / "output"

F8E_DECISION = OUT / "r4f8e_reconstructed_decision_numeric_state_v1.csv"
F8E_ACTION = OUT / "r4f8e_reconstructed_action_numeric_interface_v1.csv"
F8HD_REPORT = OUT / "r4f8h_d_competitor_evolution_evidence_report_v1.json"
F8HE_REPORT = OUT / "r4f8h_e_throughput_proxy_report_v1.json"

OUT_POLICY = OUT / "r4f8h_f_competitive_state_policy_contract_v1.json"
OUT_QA = OUT / "r4f8h_f_competitive_state_policy_qa_v1.csv"
OUT_REPORT = OUT / "r4f8h_f_competitive_state_policy_report_v1.json"


# =============================================================================
# R4F8H-F — COMPETITIVE STATE TREATMENT FREEZE
#
# Purpose:
# Freeze the strongest defensible treatment of benchmark / competitor evolution
# before final action-conditioned Monte Carlo.
#
# No modelling.
# No final Monte Carlo.
# No future leaderboard leakage.
# No invented competitor-arrival process.
# =============================================================================


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        r = csv.DictReader(f)
        return r.fieldnames or [], list(r)


required = [
    F8E_DECISION,
    F8E_ACTION,
    F8HD_REPORT,
    F8HE_REPORT,
]

missing = [p for p in required if not p.exists()]

if missing:
    print("R4F8H-F REQUIRED INPUTS MISSING")
    for p in missing:
        print(p.relative_to(ROOT))
    raise SystemExit(1)


decision_fields, decision_rows = read_csv(F8E_DECISION)
action_fields, action_rows = read_csv(F8E_ACTION)

d_report = json.loads(F8HD_REPORT.read_text(encoding="utf-8"))
e_report = json.loads(F8HE_REPORT.read_text(encoding="utf-8"))


def nonempty(field, rows):
    if field not in (rows[0].keys() if rows else []):
        return 0
    return sum(
        str(r.get(field, "")).strip() != ""
        for r in rows
    )


benchmark_speed_n = nonempty("benchmark_speed_mph", decision_rows)
benchmark_rank_n = nonempty("benchmark_rank", decision_rows)
leaderboard_context_n = nonempty(
    "decision_state_leaderboard_context",
    decision_rows
)

throughput_numeric_available = (
    e_report
    .get("semantic_status")
    == "STRUCTURAL_THROUGHPUT_PROXY_USABLE"
)

policy = {
    "phase": "R4F8H-F",
    "status": "R4F8H_COMPETITIVE_STATE_POLICY_FROZEN",

    "empirical_competitor_evolution_model_available": False,
    "empirical_future_leaderboard_model_available": False,
    "numeric_structural_arrival_calibration_available":
        throughput_numeric_available,

    "primary_mc_treatment": {
        "benchmark_semantics":
            "STATIC_DECISION_TIME_OBSERVED_BENCHMARK",
        "benchmark_speed_source":
            "R4F8E benchmark_speed_mph",
        "benchmark_rank_source":
            "R4F8E benchmark_rank",
        "leaderboard_context_source":
            "R4F8E decision_state_leaderboard_context",

        "interpretation": (
            "The benchmark is frozen at the state observable at the "
            "decision moment. Final MC may estimate probability that a "
            "new/final result exceeds that decision-time benchmark."
        )
    },

    "allowed_primary_outputs": [
        "probability_reattempt_completed",
        "probability_new_attempt_beats_current_result",
        "probability_final_result_beats_current_decision_time_benchmark",
        "expected_new_attempt_speed",
        "expected_final_result_speed",
        "final_speed_quantiles",
        "probability_final_result_worse_than_current",
        "probability_protected_result_lost",
        "wait_summary",
        "cutoff_sensitivity_by_time_remaining_scenario",
    ],

    "forbidden_primary_claims": [
        "dynamic final-rank probability",
        "expected final rank from simulated competitor evolution",
        "probability of being overtaken by future competitors",
        "probability of finishing above a dynamically evolving cutoff",
        "empirically fitted competitor-action model",
        "empirically calibrated competitor-arrival process",
    ],

    "historical_future_information_policy": {
        "future_competitor_actions_used_as_features": False,
        "future_leaderboard_used_as_features": False,
        "later_attempt_count_used_as_decision_feature": False,
        "realized_final_cutoff_used_as_decision_feature": False,
    },

    "secondary_interpretation": (
        "Historical later leaderboard/outcome information may be used "
        "only in later R4F9 replay/evaluation, never as a decision-time "
        "input to R4F8H."
    ),

    "research_claim_boundary": (
        "R4F8H is a conditional action comparison under the observed "
        "decision-time competitive benchmark, not a full dynamic "
        "leaderboard forecast."
    ),
}

OUT_POLICY.write_text(
    json.dumps(policy, indent=2, ensure_ascii=False),
    encoding="utf-8",
)


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
    len(decision_rows),
    60,
    "PASS" if len(decision_rows) == 60 else "FAIL",
)

qa(
    "action_rows",
    len(action_rows),
    170,
    "PASS" if len(action_rows) == 170 else "FAIL",
)

qa(
    "benchmark_speed_available",
    benchmark_speed_n,
    60,
    "PASS" if benchmark_speed_n == 60 else "FAIL",
)

qa(
    "benchmark_rank_available",
    benchmark_rank_n,
    60,
    "PASS" if benchmark_rank_n == 60 else "FAIL",
)

qa(
    "leaderboard_context_available",
    leaderboard_context_n,
    60,
    "PASS" if leaderboard_context_n == 60 else "FAIL",
)

qa(
    "empirical_competitor_model_claimed",
    False,
    False,
    "PASS",
)

qa(
    "future_leaderboard_used",
    False,
    False,
    "PASS",
)

qa(
    "future_competitor_actions_used",
    False,
    False,
    "PASS",
)

qa(
    "later_attempt_count_used",
    False,
    False,
    "PASS",
)

qa(
    "dynamic_rank_claim_allowed",
    False,
    False,
    "PASS",
)

qa(
    "static_decision_time_benchmark_allowed",
    True,
    True,
    "PASS",
)

qa(
    "final_monte_carlo_run",
    False,
    False,
    "PASS",
)


with OUT_QA.open("w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=["metric", "value", "expected", "status"],
    )
    writer.writeheader()
    writer.writerows(qa_rows)


fails = sum(r["status"] == "FAIL" for r in qa_rows)
warns = sum(r["status"] == "WARN" for r in qa_rows)
passes = sum(r["status"] == "PASS" for r in qa_rows)

report = {
    "phase": "R4F8H-F",

    "status": (
        "R4F8H_COMPETITIVE_STATE_POLICY_FROZEN"
        if fails == 0
        else "R4F8H_COMPETITIVE_STATE_POLICY_FAILED"
    ),

    "evidence": {
        "competitor_audit_status":
            d_report.get("phase"),
        "throughput_semantic_status":
            e_report.get("semantic_status"),
        "decision_time_benchmark_speed_coverage":
            f"{benchmark_speed_n}/60",
        "decision_time_benchmark_rank_coverage":
            f"{benchmark_rank_n}/60",
        "leaderboard_context_coverage":
            f"{leaderboard_context_n}/60",
    },

    "final_policy":
        "STATIC_DECISION_TIME_BENCHMARK_PRIMARY",

    "dynamic_competitor_evolution":
        "UNIDENTIFIABLE_WITH_CURRENT_EVIDENCE",

    "primary_rank_outputs":
        "NOT_ALLOWED",

    "primary_benchmark_crossing_outputs":
        "ALLOWED_CONDITIONAL_ON_DECISION_TIME_BENCHMARK",

    "qa": {
        "pass": passes,
        "warn": warns,
        "fail": fails,
    },

    "protected_input_hashes": {
        str(p.relative_to(ROOT)): sha256(p)
        for p in required
    },

    "final_mc_executed": False,

    "next_phase": (
        "R4F8H-G_FINAL_ACTION_MONTE_CARLO"
        if fails == 0
        else "RESOLVE_R4F8H_F_FAILURES"
    ),
}

OUT_REPORT.write_text(
    json.dumps(report, indent=2, ensure_ascii=False),
    encoding="utf-8",
)


print("=" * 125)
print("R4F8H-F — COMPETITIVE STATE TREATMENT FREEZE")
print("=" * 125)
print()

print("EVIDENCE BOUNDARY")
print("-" * 125)
print(
    f"Decision-time benchmark speed:     "
    f"{benchmark_speed_n}/60"
)
print(
    f"Decision-time benchmark rank:      "
    f"{benchmark_rank_n}/60"
)
print(
    f"Decision-time leaderboard context: "
    f"{leaderboard_context_n}/60"
)
print(
    "Empirical competitor evolution:    unavailable"
)
print(
    "Numeric throughput calibration:    "
    f"{'available' if throughput_numeric_available else 'unavailable'}"
)
print()

print("FROZEN PRIMARY TREATMENT")
print("-" * 125)
print("STATIC_DECISION_TIME_BENCHMARK")
print()
print(
    "Allowed: P(final result beats the benchmark visible at "
    "the decision moment)."
)
print(
    "Not allowed: dynamic final-rank probabilities or "
    "future competitor-overtake probabilities."
)
print()

print("QA")
print("-" * 125)
print(f"{passes} PASS | {warns} WARN | {fails} FAIL")

for row in qa_rows:
    if row["status"] != "PASS":
        print(
            f"{row['status']} | "
            f"{row['metric']} | "
            f"value={row['value']} | "
            f"expected={row['expected']}"
        )

print()
print("OUTPUTS")
print("-" * 125)
print(OUT_POLICY.relative_to(ROOT))
print(OUT_QA.relative_to(ROOT))
print(OUT_REPORT.relative_to(ROOT))
print()

if fails:
    print("R4F8H_F_COMPETITIVE_STATE_POLICY_FAILED")
    raise SystemExit(1)

print("R4F8H_COMPETITIVE_STATE_POLICY_FROZEN")
print()
print("NEXT: R4F8H-G FINAL ACTION MONTE CARLO")
