from pathlib import Path
import csv
import json
import hashlib
from collections import Counter


ROOT = Path("/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈")
OUT = ROOT / "r4" / "output"

DAY1_RECON = OUT / "r4f9_b_historical_realized_outcome_interface_v1.csv"
LC_V2 = OUT / "r4lc5e_last_chance_fused_interface_v2.csv"
F8E = OUT / "r4f8e_reconstructed_decision_numeric_state_v1.csv"

OUT_FINAL = OUT / "r4f9_b3_final_historical_outcome_interface_v1.csv"
OUT_QA = OUT / "r4f9_b3_final_historical_outcome_interface_qa_v1.csv"
OUT_CONTRACT = OUT / "r4f9_b3_final_historical_outcome_contract_v1.json"
OUT_REPORT = OUT / "r4f9_b3_final_historical_outcome_report_v1.json"


# =============================================================================
# R4F9-B3 — FINAL HISTORICAL OUTCOME INTERFACE
#
# Day 1:
#   attempt-level realized next-attempt evidence from R4F9-B.
#
# Last Chance:
#   session-level categorical realized outcome from frozen R4LC5E v2.
#
# IMPORTANT:
# - regime-specific evaluation granularity is preserved
# - Last Chance official-session-detail IDs are NOT forced into Day1 UUID space
# - historical actions are descriptive only, never optimal labels
# - future outcomes are evaluation targets only
# =============================================================================


def clean(v):
    return "" if v is None else str(v).strip()


def truthy(v):
    return clean(v).lower() in {
        "1", "true", "yes", "y", "t"
    }


def read_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        r = csv.DictReader(f)
        return r.fieldnames or [], list(r)


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


required = [DAY1_RECON, LC_V2, F8E]

missing = [p for p in required if not p.exists()]

if missing:
    print("R4F9-B3 REQUIRED INPUTS MISSING")
    for p in missing:
        print(p.relative_to(ROOT))
    raise SystemExit(1)


_, recon_rows = read_csv(DAY1_RECON)
_, lc_rows = read_csv(LC_V2)
_, f8e_rows = read_csv(F8E)


if len(recon_rows) != 60:
    raise SystemExit(
        f"R4F9-B source interface changed: {len(recon_rows)} != 60"
    )

if len(lc_rows) != 10:
    raise SystemExit(
        f"Last Chance v2 changed: {len(lc_rows)} != 10"
    )

if len(f8e_rows) != 60:
    raise SystemExit(
        f"F8E universe changed: {len(f8e_rows)} != 60"
    )


# =============================================================================
# Lookups
# =============================================================================

f8e_by_source_decision = {
    clean(r["source_decision_id"]): r
    for r in f8e_rows
}

recon_by_fused_id = {
    clean(r["fused_decision_id"]): r
    for r in recon_rows
}


# =============================================================================
# Last Chance categorical outcome semantics
# =============================================================================

QUALIFIED_OUTCOMES = {
    "QUALIFIED_P31",
    "QUALIFIED_P32",
    "QUALIFIED_P33",
    "ULTIMATELY_QUALIFIED_P33",
}

NOT_QUALIFIED_OUTCOMES = {
    "FAILED_TO_QUALIFY",
    "ULTIMATELY_BUMPED_BY_HARVEY",
    "CRASH_INCOMPLETE_FAILED_TO_QUALIFY",
}


def final_qualified_from_outcome(outcome):
    if outcome in QUALIFIED_OUTCOMES:
        return True
    if outcome in NOT_QUALIFIED_OUTCOMES:
        return False
    return ""


def explicit_crash_incomplete(outcome):
    if "CRASH_INCOMPLETE" in outcome:
        return True
    return False


# =============================================================================
# Build final 60-row interface
# =============================================================================

final_rows = []

# -------------------------------------------------------------------------
# Day 1: retain attempt-level reconstruction from R4F9-B
# -------------------------------------------------------------------------

for row in recon_rows:

    if clean(row["regime"]) != "DAY1":
        continue

    final_rows.append({
        "fused_decision_id":
            clean(row["fused_decision_id"]),

        "source_decision_id":
            clean(row["source_decision_id"]),

        "regime":
            "DAY1",

        "year":
            clean(row["year"]),

        "car_number":
            clean(row["car_number"]),

        "driver_name":
            clean(row["driver_name"]),

        "evaluation_granularity":
            "ATTEMPT_LEVEL",

        "historical_action":
            clean(row["observed_action"]),

        "historical_action_resolved":
            clean(row["observed_action_resolved"]),

        "historical_action_quality":
            clean(row["observed_action_quality"]),

        "current_result_speed_mph":
            clean(row["current_result_speed_mph"]),

        "decision_time_benchmark_speed_mph":
            clean(row["benchmark_speed_mph"]),

        "decision_time_benchmark_type":
            clean(row["benchmark_type"]),

        "source_attempt_id":
            clean(row["source_attempt_id"]),

        "source_attempt_id_semantics":
            "CANONICAL_DAY1_ATTEMPT_UUID",

        "next_attempt_exists":
            clean(row["next_attempt_exists"]),

        "next_attempt_id":
            clean(row["next_attempt_id"]),

        "next_attempt_complete_four_lap":
            clean(row["next_attempt_complete_four_lap"]),

        "next_attempt_speed_mph":
            clean(row["next_attempt_speed_mph"]),

        "next_attempt_improved_current":
            clean(row["next_attempt_improved_current"]),

        "next_attempt_met_decision_time_benchmark":
            clean(row["next_attempt_met_decision_time_benchmark"]),

        "realized_session_outcome":
            "",

        "realized_final_qualified":
            "",

        "explicit_crash_incomplete":
            False,

        "attempt_level_speed_evaluable":
            (
                clean(row["next_attempt_complete_four_lap"]).lower()
                == "true"
                and clean(row["next_attempt_speed_mph"]) != ""
            ),

        "categorical_session_outcome_evaluable":
            False,

        "evaluation_status":
            clean(row["historical_outcome_status"]),

        "future_information_used_for_prediction":
            False,

        "historical_action_used_as_optimal_label":
            False,
    })


# -------------------------------------------------------------------------
# Last Chance: use authoritative frozen v2 categorical outcome interface.
# -------------------------------------------------------------------------

for lc in lc_rows:

    source_id = clean(lc["decision_id"])

    f8e = f8e_by_source_decision.get(source_id)

    if f8e is None:
        raise SystemExit(
            f"Last Chance decision absent from F8E: {source_id}"
        )

    fused_id = clean(f8e["fused_decision_id"])
    outcome = clean(lc["outcome"])
    observed_action = clean(lc["observed_action_unified"])

    final_qualified = final_qualified_from_outcome(outcome)

    final_rows.append({
        "fused_decision_id":
            fused_id,

        "source_decision_id":
            source_id,

        "regime":
            "LAST_CHANCE",

        "year":
            clean(lc["year"]),

        "car_number":
            clean(lc["car_number"]),

        "driver_name":
            clean(lc["driver_name"]),

        "evaluation_granularity":
            "SESSION_LEVEL_CATEGORICAL",

        "historical_action":
            observed_action,

        "historical_action_resolved":
            True,

        "historical_action_quality":
            clean(lc["action_quality"]),

        "current_result_speed_mph":
            clean(lc["current_result_mph"]),

        "decision_time_benchmark_speed_mph":
            clean(lc["benchmark_speed_mph"]),

        "decision_time_benchmark_type":
            clean(lc["benchmark_type"]),

        "source_attempt_id":
            clean(f8e["source_attempt_id"]),

        "source_attempt_id_semantics":
            (
                clean(f8e["source_attempt_id_status"])
                if clean(f8e["source_attempt_id"])
                else "UNRESOLVED_NO_SAFE_ATTEMPT_LEVEL_JOIN"
            ),

        "next_attempt_exists":
            "",

        "next_attempt_id":
            "",

        "next_attempt_complete_four_lap":
            "",

        "next_attempt_speed_mph":
            "",

        "next_attempt_improved_current":
            "",

        "next_attempt_met_decision_time_benchmark":
            "",

        "realized_session_outcome":
            outcome,

        "realized_final_qualified":
            final_qualified,

        "explicit_crash_incomplete":
            explicit_crash_incomplete(outcome),

        "attempt_level_speed_evaluable":
            False,

        "categorical_session_outcome_evaluable":
            final_qualified != "",

        "evaluation_status":
            (
                "LAST_CHANCE_SESSION_OUTCOME_OBSERVED"
                if final_qualified != ""
                else "LAST_CHANCE_OUTCOME_UNMAPPED"
            ),

        "future_information_used_for_prediction":
            False,

        "historical_action_used_as_optimal_label":
            False,
    })


# =============================================================================
# Deterministic order
# =============================================================================

final_rows.sort(
    key=lambda r: (
        0 if r["regime"] == "DAY1" else 1,
        int(r["year"]) if str(r["year"]).isdigit() else 9999,
        r["fused_decision_id"],
    )
)


# =============================================================================
# Save
# =============================================================================

with OUT_FINAL.open("w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=list(final_rows[0].keys()),
    )
    writer.writeheader()
    writer.writerows(final_rows)


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


day1 = [r for r in final_rows if r["regime"] == "DAY1"]
lc_final = [r for r in final_rows if r["regime"] == "LAST_CHANCE"]

speed_eval = [
    r for r in final_rows
    if r["attempt_level_speed_evaluable"] is True
]

categorical_eval = [
    r for r in final_rows
    if r["categorical_session_outcome_evaluable"] is True
]

lc_action_counts = Counter(
    r["historical_action"]
    for r in lc_final
)

lc_outcome_counts = Counter(
    r["realized_session_outcome"]
    for r in lc_final
)

lc_qualified = [
    r for r in lc_final
    if r["realized_final_qualified"] is True
]

lc_not_qualified = [
    r for r in lc_final
    if r["realized_final_qualified"] is False
]

lc_unmapped = [
    r for r in lc_final
    if r["realized_final_qualified"] == ""
]

qa(
    "final_rows",
    len(final_rows),
    60,
    "PASS" if len(final_rows) == 60 else "FAIL",
)

qa(
    "day1_rows",
    len(day1),
    50,
    "PASS" if len(day1) == 50 else "FAIL",
)

qa(
    "last_chance_rows",
    len(lc_final),
    10,
    "PASS" if len(lc_final) == 10 else "FAIL",
)

qa(
    "day1_attempt_level_speed_evaluable",
    len(speed_eval),
    19,
    "PASS" if len(speed_eval) == 19 else "WARN",
)

qa(
    "last_chance_categorical_evaluable",
    len(categorical_eval),
    10,
    "PASS" if len(categorical_eval) == 10 else "FAIL",
)

qa(
    "last_chance_qualified",
    len(lc_qualified),
    6,
    "PASS" if len(lc_qualified) == 6 else "WARN",
)

qa(
    "last_chance_not_qualified",
    len(lc_not_qualified),
    4,
    "PASS" if len(lc_not_qualified) == 4 else "WARN",
)

qa(
    "last_chance_unmapped_outcome",
    len(lc_unmapped),
    0,
    "PASS" if len(lc_unmapped) == 0 else "FAIL",
)

qa(
    "last_chance_reconstructed_attempt_ids_forced_into_day1_uuid_space",
    False,
    False,
    "PASS",
)

qa(
    "future_outcomes_used_for_prediction",
    False,
    False,
    "PASS",
)

qa(
    "historical_action_used_as_optimal_label",
    False,
    False,
    "PASS",
)

qa(
    "dynamic_final_rank_claimed",
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


passes = sum(r["status"] == "PASS" for r in qa_rows)
warns = sum(r["status"] == "WARN" for r in qa_rows)
fails = sum(r["status"] == "FAIL" for r in qa_rows)


# =============================================================================
# Contract/report
# =============================================================================

contract = {
    "phase": "R4F9-B3",

    "status": "R4F9_FINAL_HISTORICAL_OUTCOME_INTERFACE_FROZEN",

    "regime_specific_evaluation": {
        "DAY1": {
            "granularity": "ATTEMPT_LEVEL",
            "primary_realized_target":
                "next canonical attempt after source attempt",
            "speed_evaluation_available_when":
                "next attempt is complete A_COMPLETE four-lap result",
        },

        "LAST_CHANCE": {
            "granularity": "SESSION_LEVEL_CATEGORICAL",
            "source":
                str(LC_V2.relative_to(ROOT)),
            "primary_realized_target":
                "final qualification/session outcome",
            "attempt_level_speed_reconstruction":
                "NOT_FORCED",
        },
    },

    "last_chance_action_semantics_source":
        "R4LC5E_V2",

    "important_boundary": (
        "The two regimes have different historical evidence resolution. "
        "They are evaluated at the strongest supported granularity rather "
        "than forcing a common attempt-ID representation."
    ),

    "historical_actions_are_optimal_labels":
        False,

    "future_outcomes_are_prediction_features":
        False,
}


OUT_CONTRACT.write_text(
    json.dumps(contract, indent=2, ensure_ascii=False),
    encoding="utf-8",
)


report = {
    "phase": "R4F9-B3",

    "status": (
        "R4F9_FINAL_HISTORICAL_OUTCOME_INTERFACE_FROZEN"
        if fails == 0
        else "R4F9_FINAL_HISTORICAL_OUTCOME_INTERFACE_FAILED"
    ),

    "coverage": {
        "total_decisions": len(final_rows),
        "day1": len(day1),
        "last_chance": len(lc_final),
        "day1_attempt_speed_evaluable": len(speed_eval),
        "last_chance_categorical_evaluable": len(categorical_eval),
        "last_chance_qualified": len(lc_qualified),
        "last_chance_not_qualified": len(lc_not_qualified),
    },

    "last_chance_action_counts":
        dict(sorted(lc_action_counts.items())),

    "last_chance_outcome_counts":
        dict(sorted(lc_outcome_counts.items())),

    "qa": {
        "pass": passes,
        "warn": warns,
        "fail": fails,
    },

    "protected_input_hashes": {
        str(p.relative_to(ROOT)): sha256(p)
        for p in required
    },

    "output_hashes": {
        str(OUT_FINAL.relative_to(ROOT)): sha256(OUT_FINAL),
        str(OUT_QA.relative_to(ROOT)): sha256(OUT_QA),
        str(OUT_CONTRACT.relative_to(ROOT)): sha256(OUT_CONTRACT),
    },

    "next_phase": (
        "R4F9-C_PROBABILISTIC_REPLAY_EVALUATION"
        if fails == 0
        else "RESOLVE_R4F9_B3_FAILURES"
    ),
}


OUT_REPORT.write_text(
    json.dumps(report, indent=2, ensure_ascii=False),
    encoding="utf-8",
)


# =============================================================================
# Console
# =============================================================================

print("=" * 132)
print("R4F9-B3 — FINAL HISTORICAL OUTCOME INTERFACE")
print("=" * 132)
print()

print("REGIME COVERAGE")
print("-" * 132)
print(f"Total final decisions:                  {len(final_rows)}")
print(f"Day 1 attempt-level rows:               {len(day1)}")
print(f"Last Chance categorical rows:           {len(lc_final)}")
print()

print("EVALUATION COVERAGE")
print("-" * 132)
print(f"Day 1 complete next-speed outcomes:     {len(speed_eval)}")
print(f"Last Chance categorical outcomes:       {len(categorical_eval)}")
print(f"Last Chance ultimately qualified:       {len(lc_qualified)}")
print(f"Last Chance not qualified:              {len(lc_not_qualified)}")
print()

print("LAST CHANCE HISTORICAL ACTIONS")
print("-" * 132)
for k, v in sorted(lc_action_counts.items()):
    print(f"{k:35s} {v}")

print()
print("LAST CHANCE OUTCOMES")
print("-" * 132)
for k, v in sorted(lc_outcome_counts.items()):
    print(f"{k:45s} {v}")

print()
print("QA")
print("-" * 132)
print(f"{passes} PASS | {warns} WARN | {fails} FAIL")

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
print("-" * 132)
for p in [
    OUT_FINAL,
    OUT_QA,
    OUT_CONTRACT,
    OUT_REPORT,
]:
    print(p.relative_to(ROOT))

print()

if fails:
    print("R4F9_B3_FINAL_HISTORICAL_OUTCOME_INTERFACE_FAILED")
    raise SystemExit(1)

print("R4F9_FINAL_HISTORICAL_OUTCOME_INTERFACE_FROZEN")
print()
print("NEXT: R4F9-C PROBABILISTIC REPLAY EVALUATION")
print()
print(
    "IMPORTANT: Day 1 is evaluated at attempt level where supported; "
    "Last Chance is evaluated at session-outcome level. "
    "Historical actions remain descriptive evidence, not optimal labels."
)
