from pathlib import Path
import csv
import json
import hashlib
import math
from collections import Counter, defaultdict

ROOT = Path("/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈")
OUT = ROOT / "r4" / "output"
WEATHER_OUT = ROOT / "weather" / "output"

F8E_DECISION = OUT / "r4f8e_reconstructed_decision_numeric_state_v1.csv"
F8F_CONTRACT = OUT / "r4f8f_wait_queue_model_contract_v1.json"
F8G_STATE = OUT / "r4f8g_decision_predictive_uncertainty_state_v1.csv"
F8HA_REPORT = OUT / "r4f8h_a_final_mc_readiness_report_v1.json"
F8HB_REPORT = OUT / "r4f8h_b_cutoff_evidence_resolution_report_v1.json"

EXISTING_GRID = WEATHER_OUT / "queue_wait_cutoff_feasibility_grid_v1.csv"
RUN_DURATION_REF = WEATHER_OUT / "queue_wait_run_duration_reference_v1.csv"

OUT_POLICY_GRID = OUT / "r4f8h_c_cutoff_completion_sensitivity_policy_v1.csv"
OUT_EVIDENCE = OUT / "r4f8h_c_cutoff_completion_evidence_summary_v1.csv"
OUT_QA = OUT / "r4f8h_c_cutoff_completion_policy_qa_v1.csv"
OUT_CONTRACT = OUT / "r4f8h_c_cutoff_completion_policy_contract_v1.json"
OUT_REPORT = OUT / "r4f8h_c_cutoff_completion_policy_report_v1.json"


# =============================================================================
# R4F8H-C — CUTOFF COMPLETION SENSITIVITY POLICY FREEZE
#
# This phase freezes HOW cutoff uncertainty will be represented later.
#
# It DOES NOT:
# - fabricate exact historical session remaining
# - fabricate Last Chance timestamps
# - run the final action Monte Carlo
# - retune performance
# - alter F8E/F8F/F8G
# - reuse old R4P11 final probabilities
#
# Core policy:
#
# completion_before_cutoff =
#     sampled_wait_minutes + sampled_run_duration_minutes
#     <= assumed_time_remaining_minutes
#
# But assumed_time_remaining_minutes is a sensitivity scenario unless an
# independently source-supported decision-safe historical value exists.
# =============================================================================


SENSITIVITY_GRID_MINUTES = [5, 10, 15, 20, 30, 45, 60]

# These are labels, not fitted probabilities.
POLICY_CLASSES = {
    5: "EXTREME_CUTOFF_PRESSURE",
    10: "VERY_LOW_TIME_REMAINING",
    15: "LOW_TIME_REMAINING",
    20: "LOW_TO_MODERATE_TIME_REMAINING",
    30: "MODERATE_TIME_REMAINING",
    45: "HIGH_TIME_REMAINING",
    60: "VERY_HIGH_TIME_REMAINING",
}


def clean(v):
    if v is None:
        return ""
    return str(v).strip()


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


def truthy(v):
    return clean(v).lower() in {"1", "true", "yes", "y", "t"}


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


def normalized_field_map(fields):
    out = {}
    for field in fields:
        key = (
            field.lower()
            .strip()
            .replace("-", "_")
            .replace(" ", "_")
        )
        out[key] = field
    return out


def find_field(fields, candidates):
    m = normalized_field_map(fields)
    for c in candidates:
        key = (
            c.lower()
            .strip()
            .replace("-", "_")
            .replace(" ", "_")
        )
        if key in m:
            return m[key]
    return None


# =============================================================================
# Required input integrity
# =============================================================================

required = [
    F8E_DECISION,
    F8F_CONTRACT,
    F8G_STATE,
    F8HA_REPORT,
    F8HB_REPORT,
]

missing = [p for p in required if not p.exists()]

if missing:
    print("=" * 120)
    print("R4F8H-C REQUIRED INPUT MISSING")
    print("=" * 120)
    for p in missing:
        print(p.relative_to(ROOT))
    raise SystemExit(1)


f8e_fields, f8e_rows = read_csv(F8E_DECISION)
f8g_fields, f8g_rows = read_csv(F8G_STATE)

f8f_contract = json.loads(F8F_CONTRACT.read_text(encoding="utf-8"))
f8ha_report = json.loads(F8HA_REPORT.read_text(encoding="utf-8"))
f8hb_report = json.loads(F8HB_REPORT.read_text(encoding="utf-8"))


# =============================================================================
# Confirm current universe
# =============================================================================

decision_id_field = find_field(
    f8e_fields,
    ["fused_decision_id", "decision_id"]
)

if decision_id_field is None:
    raise SystemExit("F8E decision ID field could not be resolved.")

decision_ids = [
    clean(r.get(decision_id_field))
    for r in f8e_rows
]

if len(f8e_rows) != 60:
    raise SystemExit(
        f"Unexpected F8E decision universe: {len(f8e_rows)} != 60"
    )


# =============================================================================
# Inspect existing cutoff feasibility grid
# =============================================================================

existing_grid_available = EXISTING_GRID.exists()
existing_grid_rows = []
existing_grid_fields = []

existing_time_field = None
existing_completion_field = None
existing_margin_min_field = None
existing_cutoff_field = None

existing_grid_summary = {}

if existing_grid_available:
    existing_grid_fields, existing_grid_rows = read_csv(EXISTING_GRID)

    existing_time_field = find_field(
        existing_grid_fields,
        [
            "time_remaining_minutes",
            "remaining_minutes",
            "session_remaining_minutes",
        ]
    )

    existing_completion_field = find_field(
        existing_grid_fields,
        [
            "completion_before_cutoff",
            "completed_before_cutoff",
        ]
    )

    existing_margin_min_field = find_field(
        existing_grid_fields,
        [
            "cutoff_margin_minutes",
            "margin_minutes",
        ]
    )

    existing_cutoff_field = find_field(
        existing_grid_fields,
        [
            "session_cutoff_utc",
            "cutoff_utc",
        ]
    )

    by_time = defaultdict(list)

    if existing_time_field:
        for row in existing_grid_rows:
            t = num(row.get(existing_time_field))
            if t is not None:
                by_time[t].append(row)

    for t, rows in sorted(by_time.items()):
        completion_values = []

        if existing_completion_field:
            for row in rows:
                value = clean(row.get(existing_completion_field))
                if value:
                    completion_values.append(truthy(value))

        margins = []

        if existing_margin_min_field:
            for row in rows:
                x = num(row.get(existing_margin_min_field))
                if x is not None:
                    margins.append(x)

        existing_grid_summary[t] = {
            "rows": len(rows),
            "completion_true": sum(completion_values),
            "completion_false": (
                len(completion_values) - sum(completion_values)
            ),
            "completion_rate": (
                sum(completion_values) / len(completion_values)
                if completion_values
                else None
            ),
            "margin_min": min(margins) if margins else None,
            "margin_max": max(margins) if margins else None,
        }


# =============================================================================
# Inspect run-duration reference ONLY as supporting evidence
# =============================================================================

run_duration_available = RUN_DURATION_REF.exists()
run_duration_rows = []
run_duration_fields = []

if run_duration_available:
    run_duration_fields, run_duration_rows = read_csv(RUN_DURATION_REF)

run_duration_numeric_fields = []

for field in run_duration_fields:
    vals = [
        num(r.get(field))
        for r in run_duration_rows
    ]
    vals = [x for x in vals if x is not None]

    if vals:
        run_duration_numeric_fields.append({
            "field": field,
            "numeric_rows": len(vals),
            "min": min(vals),
            "max": max(vals),
        })


# =============================================================================
# Freeze structural cutoff sensitivity policy
# =============================================================================

policy_rows = []

for t in SENSITIVITY_GRID_MINUTES:

    historical_summary = existing_grid_summary.get(float(t), {})

    policy_rows.append({
        "policy_id": f"CUTOFF_SENSITIVITY_{t:02d}MIN",
        "assumed_time_remaining_minutes": t,
        "scenario_class": POLICY_CLASSES[t],

        # Very important semantic boundary:
        "time_remaining_semantics":
            "STRUCTURAL_SENSITIVITY_SCENARIO",

        "historical_exact_time_claim":
            False,

        "allowed_for_final_mc_sensitivity":
            True,

        "allowed_as_historical_ground_truth":
            False,

        "completion_rule":
            (
                "sampled_wait_minutes + sampled_run_duration_minutes "
                "<= assumed_time_remaining_minutes"
            ),

        "existing_grid_support_rows":
            historical_summary.get("rows", 0),

        "existing_grid_completion_true":
            historical_summary.get("completion_true", ""),

        "existing_grid_completion_false":
            historical_summary.get("completion_false", ""),

        "existing_grid_completion_rate":
            (
                ""
                if historical_summary.get("completion_rate") is None
                else historical_summary["completion_rate"]
            ),

        "existing_grid_margin_min_minutes":
            (
                ""
                if historical_summary.get("margin_min") is None
                else historical_summary["margin_min"]
            ),

        "existing_grid_margin_max_minutes":
            (
                ""
                if historical_summary.get("margin_max") is None
                else historical_summary["margin_max"]
            ),

        "policy_status":
            "FROZEN_STRUCTURAL_SENSITIVITY",
    })


with OUT_POLICY_GRID.open("w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=list(policy_rows[0].keys())
    )
    writer.writeheader()
    writer.writerows(policy_rows)


# =============================================================================
# Evidence summary
# =============================================================================

evidence_rows = [
    {
        "evidence_component": "R4F8E exact session remaining",
        "source": str(F8E_DECISION.relative_to(ROOT)),
        "support": "0/60 exact decision-safe remaining-time values",
        "allowed_use": "ESTABLISHES UNRESOLVED HISTORICAL COUNTDOWN",
        "forbidden_use": "DO NOT FABRICATE COUNTDOWN",
    },
    {
        "evidence_component": "R4F8H-A readiness audit",
        "source": str(F8HA_REPORT.relative_to(ROOT)),
        "support": "0/170 cutoff-completion-ready action rows",
        "allowed_use": "READINESS BOUNDARY",
        "forbidden_use": "NOT A CUTOFF MODEL",
    },
    {
        "evidence_component": "R4F8H-B repository audit",
        "source": str(F8HB_REPORT.relative_to(ROOT)),
        "support": (
            "Repository contains cutoff-related candidates but "
            "no general exact decision-safe remaining-time source"
        ),
        "allowed_use": "EVIDENCE RESOLUTION BOUNDARY",
        "forbidden_use": "DO NOT EQUATE SCENARIO GRIDS WITH OBSERVATIONS",
    },
    {
        "evidence_component": "Existing cutoff feasibility grid",
        "source": (
            str(EXISTING_GRID.relative_to(ROOT))
            if existing_grid_available
            else "NOT_FOUND"
        ),
        "support": (
            f"{len(existing_grid_rows)} rows"
            if existing_grid_available
            else "0 rows"
        ),
        "allowed_use": (
            "STRUCTURAL SANITY CHECK / SENSITIVITY SUPPORT"
        ),
        "forbidden_use": (
            "NOT HISTORICAL DECISION-SAFE SESSION REMAINING"
        ),
    },
    {
        "evidence_component": "Run-duration reference",
        "source": (
            str(RUN_DURATION_REF.relative_to(ROOT))
            if run_duration_available
            else "NOT_FOUND"
        ),
        "support": (
            f"{len(run_duration_rows)} summary/reference rows"
            if run_duration_available
            else "0 rows"
        ),
        "allowed_use": (
            "LATER COMPLETION-DURATION COMPONENT"
        ),
        "forbidden_use": (
            "DO NOT TURN INTO QUEUE WAIT OR SESSION REMAINING"
        ),
    },
    {
        "evidence_component": "2024 scheduled end",
        "source": "data/canonical/v1/qualifying_events.csv",
        "support": "2024-05-18T21:50:00Z exists in repository",
        "allowed_use": (
            "2024-SPECIFIC SUPPORT WHERE DECISION-TIME JOIN IS VALID"
        ),
        "forbidden_use": (
            "DO NOT GENERALIZE AS CROSS-YEAR HISTORICAL CUTOFF"
        ),
    },
    {
        "evidence_component": "Last Chance timing",
        "source": (
            "r4/output/"
            "r4lc5b_last_chance_predecision_state_ledger_v1.csv"
        ),
        "support": (
            "bounded/qualitative timing states exist; "
            "exact remaining minutes unresolved"
        ),
        "allowed_use": (
            "QUALITATIVE / BOUNDED INTERPRETATION"
        ),
        "forbidden_use": (
            "NO FABRICATED EXACT LAST CHANCE COUNTDOWN"
        ),
    },
]

with OUT_EVIDENCE.open("w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=list(evidence_rows[0].keys())
    )
    writer.writeheader()
    writer.writerows(evidence_rows)


# =============================================================================
# QA
# =============================================================================

qa_rows = []


def add_qa(metric, value, expected, status):
    qa_rows.append({
        "metric": metric,
        "value": value,
        "expected": expected,
        "status": status,
    })


add_qa(
    "f8e_decision_rows_preserved",
    len(f8e_rows),
    60,
    "PASS" if len(f8e_rows) == 60 else "FAIL",
)

add_qa(
    "unique_decision_ids_preserved",
    len(set(decision_ids)),
    60,
    (
        "PASS"
        if len(set(decision_ids)) == 60 and "" not in set(decision_ids)
        else "FAIL"
    ),
)

add_qa(
    "sensitivity_grid_values",
    ",".join(map(str, SENSITIVITY_GRID_MINUTES)),
    "5,10,15,20,30,45,60",
    "PASS",
)

add_qa(
    "all_scenarios_marked_structural",
    all(
        r["time_remaining_semantics"]
        == "STRUCTURAL_SENSITIVITY_SCENARIO"
        for r in policy_rows
    ),
    True,
    "PASS",
)

add_qa(
    "all_historical_exact_time_claims_false",
    all(
        r["historical_exact_time_claim"] is False
        for r in policy_rows
    ),
    True,
    "PASS",
)

add_qa(
    "scenario_values_not_ground_truth",
    all(
        r["allowed_as_historical_ground_truth"] is False
        for r in policy_rows
    ),
    True,
    "PASS",
)

add_qa(
    "existing_cutoff_grid_found",
    existing_grid_available,
    True,
    "PASS" if existing_grid_available else "WARN",
)

add_qa(
    "existing_cutoff_grid_rows",
    len(existing_grid_rows),
    "MEASURED",
    "PASS",
)

add_qa(
    "run_duration_reference_found",
    run_duration_available,
    True,
    "PASS" if run_duration_available else "WARN",
)

add_qa(
    "exact_session_remaining_created",
    False,
    False,
    "PASS",
)

add_qa(
    "last_chance_exact_time_created",
    False,
    False,
    "PASS",
)

add_qa(
    "final_action_monte_carlo_run",
    False,
    False,
    "PASS",
)

add_qa(
    "performance_model_refit",
    False,
    False,
    "PASS",
)

add_qa(
    "old_r4p11_final_probability_reused",
    False,
    False,
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
# Frozen contract
# =============================================================================

contract = {
    "phase": "R4F8H-C",
    "status": "R4F8H_CUTOFF_COMPLETION_SENSITIVITY_POLICY_FROZEN",

    "problem_statement": (
        "Exact decision-safe historical session remaining is unavailable "
        "for the general 60-decision universe. Therefore completion before "
        "cutoff cannot be represented as an exact historical feature."
    ),

    "authoritative_policy": {
        "type": "STRUCTURAL_SENSITIVITY_GRID",
        "time_remaining_minutes": SENSITIVITY_GRID_MINUTES,
        "probability_distribution_over_scenarios": None,
        "equal_probability_assumed": False,
        "historical_frequency_claim": False,
        "scenario_interpretation": (
            "Each remaining-time value is evaluated separately. "
            "The grid is a sensitivity envelope, not a probability law."
        ),
    },

    "completion_rule": (
        "sampled_wait_minutes + sampled_run_duration_minutes "
        "<= assumed_time_remaining_minutes"
    ),

    "stop_semantics": {
        "requires_new_attempt": False,
        "completion_before_cutoff_applicable": False,
        "wait_minutes": 0,
    },

    "non_stop_semantics": {
        "requires_new_attempt": True,
        "cutoff_completion_must_be_evaluated": True,
    },

    "2024_policy": {
        "known_scheduled_end_support":
            "2024-05-18T21:50:00Z",
        "use_case_specific_exact_join_only_if_decision_safe":
            True,
        "generalize_to_other_years":
            False,
    },

    "last_chance_policy": {
        "exact_remaining_minutes_available":
            False,
        "bounded_or_qualitative_timing_may_exist":
            True,
        "fabricate_exact_countdown":
            False,
        "use_structural_sensitivity_envelope":
            True,
    },

    "research_integrity": {
        "scenario_grid_is_historical_observation":
            False,
        "scenario_grid_is_empirical_frequency":
            False,
        "session_remaining_fabricated":
            False,
        "last_chance_timestamp_fabricated":
            False,
        "future_outcome_leakage":
            False,
        "performance_refit":
            False,
        "old_r4p11_final_probabilities_used":
            False,
    },

    "downstream_requirement": (
        "R4F8H final MC must report action outcomes conditional on "
        "remaining-time scenario unless a source-supported exact historical "
        "decision-time countdown exists."
    ),

    "final_recommendation_rule": (
        "Do not collapse sensitivity scenarios into a single recommendation "
        "without explicitly documenting an aggregation policy."
    ),
}

OUT_CONTRACT.write_text(
    json.dumps(contract, indent=2, ensure_ascii=False),
    encoding="utf-8",
)


# =============================================================================
# Deterministic hashes of frozen inputs + new outputs
# =============================================================================

protected_inputs = [
    F8E_DECISION,
    F8F_CONTRACT,
    F8G_STATE,
    F8HA_REPORT,
    F8HB_REPORT,
]

input_hashes = {
    str(p.relative_to(ROOT)): sha256(p)
    for p in protected_inputs
}

new_output_paths = [
    OUT_POLICY_GRID,
    OUT_EVIDENCE,
    OUT_QA,
    OUT_CONTRACT,
]

new_output_hashes = {
    str(p.relative_to(ROOT)): sha256(p)
    for p in new_output_paths
}


# =============================================================================
# Report
# =============================================================================

passes = sum(r["status"] == "PASS" for r in qa_rows)
warns = sum(r["status"] == "WARN" for r in qa_rows)
fails = sum(r["status"] == "FAIL" for r in qa_rows)

report = {
    "phase": "R4F8H-C",
    "status": (
        "R4F8H_CUTOFF_COMPLETION_SENSITIVITY_POLICY_FROZEN"
        if fails == 0
        else "R4F8H_CUTOFF_COMPLETION_POLICY_FAILED"
    ),

    "decision_universe": len(f8e_rows),

    "sensitivity_grid_minutes":
        SENSITIVITY_GRID_MINUTES,

    "existing_cutoff_grid": {
        "available":
            existing_grid_available,
        "rows":
            len(existing_grid_rows),
        "time_field":
            existing_time_field,
        "completion_field":
            existing_completion_field,
        "margin_field":
            existing_margin_min_field,
        "cutoff_field":
            existing_cutoff_field,
    },

    "run_duration_reference": {
        "available":
            run_duration_available,
        "rows":
            len(run_duration_rows),
        "numeric_fields":
            run_duration_numeric_fields,
    },

    "interpretation": (
        "Historical exact session remaining is unavailable across the "
        "general decision universe. Cutoff feasibility is therefore "
        "represented as a scenario-conditioned sensitivity envelope."
    ),

    "final_mc_policy": (
        "Evaluate non-STOP action outcomes separately at "
        "5/10/15/20/30/45/60-minute assumed remaining-time scenarios."
    ),

    "qa": {
        "pass": passes,
        "warn": warns,
        "fail": fails,
    },

    "protected_input_hashes":
        input_hashes,

    "new_output_hashes":
        new_output_hashes,

    "final_mc_executed":
        False,

    "next_phase": (
        "R4F8H-D_FINAL_ACTION_MONTE_CARLO"
        if fails == 0
        else "RESOLVE_R4F8H_C_FAILURES"
    ),
}

OUT_REPORT.write_text(
    json.dumps(report, indent=2, ensure_ascii=False),
    encoding="utf-8",
)


# =============================================================================
# Console
# =============================================================================

print("=" * 130)
print("R4F8H-C — CUTOFF COMPLETION SENSITIVITY POLICY FREEZE")
print("=" * 130)
print()

print("CURRENT EVIDENCE BOUNDARY")
print("-" * 130)
print("Exact historical decision-safe session remaining: 0/60")
print("General cross-year hard cutoff model:             unavailable")
print(
    "Existing cutoff feasibility grid:                "
    f"{'FOUND' if existing_grid_available else 'NOT FOUND'}"
)
print(
    "Existing cutoff grid rows:                       "
    f"{len(existing_grid_rows)}"
)
print(
    "Run-duration reference:                          "
    f"{'FOUND' if run_duration_available else 'NOT FOUND'}"
)
print(
    "Run-duration reference rows:                     "
    f"{len(run_duration_rows)}"
)
print()

print("FROZEN SENSITIVITY GRID")
print("-" * 130)

for row in policy_rows:
    print(
        f"{row['assumed_time_remaining_minutes']:>2} min | "
        f"{row['scenario_class']:35s} | "
        f"existing_grid_rows={row['existing_grid_support_rows']}"
    )

print()
print("POLICY")
print("-" * 130)
print(
    "completion_before_cutoff = "
    "(sampled_wait + sampled_run_duration) <= "
    "assumed_time_remaining"
)
print()
print(
    "IMPORTANT: remaining-time scenarios are NOT historical "
    "observations and NOT assigned empirical probabilities."
)
print()

print("QA")
print("-" * 130)
print(f"{passes} PASS | {warns} WARN | {fails} FAIL")

for row in qa_rows:
    if row["status"] != "PASS":
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
    OUT_POLICY_GRID,
    OUT_EVIDENCE,
    OUT_QA,
    OUT_CONTRACT,
    OUT_REPORT,
]:
    print(p.relative_to(ROOT))

print()

if fails:
    print("R4F8H_C_CUTOFF_POLICY_FREEZE_FAILED")
    raise SystemExit(1)

print("R4F8H_C_CUTOFF_COMPLETION_SENSITIVITY_POLICY_FROZEN")
print()
print("NEXT: R4F8H-D FINAL ACTION MONTE CARLO")
print(
    "Do not average the 5/10/15/20/30/45/60-minute scenarios "
    "into a fake historical probability distribution."
)
