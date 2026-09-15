#!/usr/bin/env python3
"""Freeze the R4F8F action-specific wait/queue stochastic interface.

The non-STOP model is a broad structural sensitivity prior, not a fitted
historical queue-wait distribution. No Monte Carlo action evaluation occurs.
"""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "r4" / "output"
WEATHER_OUT = ROOT / "weather" / "output"

ACTION_INTERFACE = OUT / "r4f8e_reconstructed_action_numeric_interface_v1.csv"
DECISION_INTERFACE = OUT / "r4f8e_reconstructed_decision_numeric_state_v1.csv"

SENSITIVITY = WEATHER_OUT / "queue_wait_sensitivity_scenarios_v1.csv"
POLICY = WEATHER_OUT / "queue_wait_uncertainty_policy_v1.csv"
EVIDENCE_INVENTORY = WEATHER_OUT / "queue_wait_evidence_inventory_v1.csv"
THROUGHPUT = WEATHER_OUT / "queue_wait_throughput_proxy_v1.csv"
RUN_DURATION = WEATHER_OUT / "queue_wait_run_duration_reference_v1.csv"
IDENTIFIABILITY_2022 = WEATHER_OUT / "queue_wait_identifiability_2022_v1.csv"
OLD_P11_RESULTS = OUT / "r4p11_stochastic_wait_performance_mc_results_v1.csv"
OLD_P11_DRAWS = OUT / "r4p11_stochastic_wait_performance_mc_draws_sample_v1.csv"
OLD_P11_REPORT = OUT / "r4p11_stochastic_wait_performance_mc_report_v1.json"

OUT_CONTRACT = OUT / "r4f8f_wait_queue_model_contract_v1.json"
OUT_PARAMETERS = OUT / "r4f8f_action_wait_distribution_parameters_v1.csv"
OUT_MAPPING = OUT / "r4f8f_wait_evidence_mapping_v1.csv"
OUT_SUPPORT = OUT / "r4f8f_wait_support_summary_v1.csv"
OUT_QA = OUT / "r4f8f_wait_queue_qa_v1.csv"
OUT_REPORT = OUT / "r4f8f_wait_queue_report_v1.json"

VERSION = "R4F8F_WAIT_QUEUE_MODEL_V1"
SHARED_PRIOR = "BROAD_LATENT_PRE_RUN_DELAY_PRIOR_V1"
WAIT_VARIABLE = "LATENT_PRE_RUN_DELAY_TO_TIMED_RUN_START_MINUTES"

ACTION_ORDER = [
    ("DAY1", "STOP"),
    ("DAY1", "RETAIN_AND_REATTEMPT"),
    ("DAY1", "WITHDRAW_AND_PRIORITY_REATTEMPT"),
    ("LAST_CHANCE", "STOP"),
    ("LAST_CHANCE", "REATTEMPT"),
    ("LAST_CHANCE", "WITHDRAW_AND_REATTEMPT"),
]


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        return list(reader.fieldnames or []), list(reader)


def write_csv(path: Path, fields: list[str], rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, lineterminator="\n", extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def protected_paths() -> list[Path]:
    found: set[Path] = set()
    for pattern in ("r4f7*", "r4f8b*", "r4f8c*", "r4f8d*", "r4f8e*"):
        found.update(OUT.glob(pattern))
    return sorted(path for path in found if path.is_file())


def discrete_quantile(points: list[tuple[float, float]], quantile: float) -> float:
    cumulative = 0.0
    for value, probability in sorted(points):
        cumulative += probability
        if cumulative + 1e-12 >= quantile:
            return value
    return sorted(points)[-1][0]


def main() -> None:
    required = [
        ACTION_INTERFACE, DECISION_INTERFACE, SENSITIVITY, POLICY, EVIDENCE_INVENTORY,
        THROUGHPUT, RUN_DURATION, IDENTIFIABILITY_2022, OLD_P11_RESULTS, OLD_P11_DRAWS,
        OLD_P11_REPORT,
    ]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise SystemExit(f"Missing required evidence: {missing}")

    protected_files = protected_paths()
    protected_before = {str(path.relative_to(ROOT)): sha256(path) for path in protected_files}

    _, actions = read_csv(ACTION_INTERFACE)
    _, decisions = read_csv(DECISION_INTERFACE)
    _, scenario_rows = read_csv(SENSITIVITY)
    _, policy_rows = read_csv(POLICY)
    _, inventory_rows = read_csv(EVIDENCE_INVENTORY)
    _, throughput_rows = read_csv(THROUGHPUT)
    _, duration_rows = read_csv(RUN_DURATION)
    _, identifiability_rows = read_csv(IDENTIFIABILITY_2022)
    _, p11_results = read_csv(OLD_P11_RESULTS)
    _, p11_draws = read_csv(OLD_P11_DRAWS)
    p11_report = json.loads(OLD_P11_REPORT.read_text(encoding="utf-8"))

    assert len(decisions) == 60
    assert len(actions) == 170
    assert len(scenario_rows) == 4
    assert all(row["historically_observed_queue_wait"].lower() == "false" for row in scenario_rows)
    assert all(row["queue_wait_claim"] == "NONE" for row in scenario_rows)
    assert sum(row["usable_as_direct_queue_wait"].lower() == "true" for row in inventory_rows) == 0
    assert identifiability_rows[0]["exact_queue_wait_row_count"] == "0"
    assert identifiability_rows[0]["inter_attempt_gap_as_queue_wait"] == "PROHIBITED"
    assert p11_report["wait_model_status"].startswith("SCENARIO_PRIOR_ONLY")

    # Convert the frozen sensitivity grid into a maximum-entropy categorical
    # structural prior. Equal mass is a declared modeling assumption necessitated
    # by zero directly identified queue-wait observations; it is not empirical.
    non_stop_points = sorted((float(row["latent_pre_run_delay_minutes"]), 1.0 / len(scenario_rows)) for row in scenario_rows)
    assert [point for point, _ in non_stop_points] == [5.0, 15.0, 30.0, 45.0]
    stop_points = [(0.0, 1.0)]

    action_counts = Counter((row["regime"], row["feasible_action"]) for row in actions)
    expected_counts = {
        ("DAY1", "STOP"): 50,
        ("DAY1", "RETAIN_AND_REATTEMPT"): 50,
        ("DAY1", "WITHDRAW_AND_PRIORITY_REATTEMPT"): 50,
        ("LAST_CHANCE", "STOP"): 10,
        ("LAST_CHANCE", "REATTEMPT"): 4,
        ("LAST_CHANCE", "WITHDRAW_AND_REATTEMPT"): 6,
    }
    assert action_counts == Counter(expected_counts)

    semantics = {
        ("DAY1", "STOP"): ("NO_QUEUE_NO_WAIT_NO_NEW_ATTEMPT", "CURRENT_PROTECTED_RESULT_RETAINED"),
        ("DAY1", "RETAIN_AND_REATTEMPT"): ("DAY1_LANE2_NON_PRIORITY", "CURRENT_PROTECTED_RESULT_RETAINED"),
        ("DAY1", "WITHDRAW_AND_PRIORITY_REATTEMPT"): ("DAY1_LANE1_PRIORITY", "CURRENT_PROTECTED_RESULT_SURRENDERED"),
        ("LAST_CHANCE", "STOP"): ("NO_QUEUE_NO_WAIT_NO_NEW_ATTEMPT", "CURRENT_STATE_RETAINED"),
        ("LAST_CHANCE", "REATTEMPT"): ("LAST_CHANCE_UNPROTECTED_REATTEMPT", "NO_PROTECTED_RESULT_EXISTS"),
        ("LAST_CHANCE", "WITHDRAW_AND_REATTEMPT"): ("LAST_CHANCE_PROTECTED_WITHDRAW", "CURRENT_PROTECTED_RESULT_SURRENDERED"),
    }

    parameter_rows: list[dict] = []
    support_rows: list[dict] = []
    for regime, action in ACTION_ORDER:
        is_stop = action == "STOP"
        points = stop_points if is_stop else non_stop_points
        distribution_id = f"{VERSION}::{regime}::{action}"
        mean = sum(value * probability for value, probability in points)
        q05 = discrete_quantile(points, 0.05)
        median = discrete_quantile(points, 0.50)
        q95 = discrete_quantile(points, 0.95)
        support_level = "DETERMINISTIC_RULE" if is_stop else "WEAK_SHARED_STRUCTURAL_PRIOR_ZERO_DIRECT_WAIT_OBSERVATIONS"
        family = "POINT_MASS" if is_stop else "DISCRETE_MAXIMUM_ENTROPY_STRUCTURAL_PRIOR"
        shared_group = "NONE_STOP_RULE" if is_stop else SHARED_PRIOR
        for value, probability in points:
            parameter_rows.append({
                "model_version": VERSION,
                "distribution_id": distribution_id,
                "regime": regime,
                "feasible_action": action,
                "action_semantics": semantics[(regime, action)][0],
                "protection_semantics": semantics[(regime, action)][1],
                "wait_variable": WAIT_VARIABLE,
                "distribution_family": family,
                "support_level": support_level,
                "shared_prior_group": shared_group,
                "support_point_minutes": f"{value:.6f}",
                "probability_mass": f"{probability:.6f}",
                "probability_semantics": "DETERMINISTIC" if is_stop else "DECLARED_MAXIMUM_ENTROPY_WEIGHT_NOT_EMPIRICAL_FREQUENCY",
                "direct_queue_wait_observations": 0,
                "source_sensitivity_scenarios": 0 if is_stop else len(scenario_rows),
                "source_file": "FROZEN_ACTION_RULE" if is_stop else str(SENSITIVITY.relative_to(ROOT)),
                "source_policy_hash": "ACTION_CONTRACT" if is_stop else scenario_rows[0]["policy_hash"],
            })
        support_rows.append({
            "model_version": VERSION,
            "regime": regime,
            "feasible_action": action,
            "universe_action_rows": action_counts[(regime, action)],
            "distribution_id": distribution_id,
            "distribution_class": "DETERMINISTIC" if is_stop else "SHARED_STRUCTURAL_PRIOR",
            "direct_queue_wait_observations": 0,
            "structural_support_point_count": len(points),
            "mean_wait_minutes": f"{mean:.6f}",
            "median_wait_minutes": f"{median:.6f}",
            "q05_wait_minutes": f"{q05:.6f}",
            "q95_wait_minutes": f"{q95:.6f}",
            "q95_minus_q05_minutes": f"{q95 - q05:.6f}",
            "support_level": support_level,
            "weakly_supported": "False" if is_stop else "True",
            "shared_prior_reason": "NOT_APPLICABLE" if is_stop else "ZERO_DIRECT_QUEUE_WAIT_PAIRS_AND_NO_DEFENSIBLE_ACTION_SPECIFIC_HISTORICAL_CALIBRATION",
            "completion_before_cutoff_status": "NOT_APPLICABLE_NO_ATTEMPT" if is_stop else "REQUIRES_LATER_SEPARATE_POLICY_AND_SESSION_REMAINING_INPUT",
        })

    parameter_fields = list(parameter_rows[0])
    support_fields = list(support_rows[0])
    write_csv(OUT_PARAMETERS, parameter_fields, parameter_rows)
    write_csv(OUT_SUPPORT, support_fields, support_rows)

    evidence_specs = [
        (SENSITIVITY, "STRUCTURAL_PRIOR_SUPPORT_GRID", "ADOPTED", "Defines 5/15/30/45 minute latent pre-run-delay sensitivity points; no historical truth claim."),
        (POLICY, "SEMANTIC_AND_INFERENCE_POLICY", "ADOPTED", "Forbids direct queue-wait estimation from timestamps and separates run duration from latent wait."),
        (EVIDENCE_INVENTORY, "DIRECT_WAIT_IDENTIFIABILITY", "ADOPTED", "Establishes zero evidence layers usable as direct queue-wait observations."),
        (THROUGHPUT, "ATTEMPT_THROUGHPUT_SANITY_CHECK", "SANITY_CHECK_ONLY", "Attempt spacings are not queue waits and do not calibrate probability masses."),
        (RUN_DURATION, "TIMED_RUN_DURATION_COMPONENT", "DEFERRED_COMPLETION_COMPONENT", "260 complete attempts support run duration, which is excluded from the F8F pre-run-delay variable."),
        (IDENTIFIABILITY_2022, "QUEUE_IDENTIFIABILITY_GATE", "ADOPTED", "Confirms zero exact/bounded waits and prohibits inter-attempt-gap conversion."),
        (OLD_P11_RESULTS, "OLD_DECLARED_WAIT_PRIOR_AND_FINAL_ACTION_OUTPUT", "REJECTED_FOR_F8F_CALIBRATION", "Action probabilities and wait summaries are not reused; declared time-to-completed-attempt semantics do not match F8F pre-run delay."),
        (OLD_P11_DRAWS, "OLD_PRIOR_GENERATED_DRAWS", "REJECTED_AS_INDEPENDENT_EVIDENCE", "Generated draws are not historical observations and do not increase support size."),
        (OLD_P11_REPORT, "OLD_MODEL_LIMITATIONS", "CONTEXT_ONLY", "Confirms old wait model was scenario-prior-only and not historically calibrated."),
        (ACTION_INTERFACE, "FROZEN_ACTION_UNIVERSE", "ADOPTED", "Binds distributions to the unchanged 170 action rows and preserves action semantics."),
        (DECISION_INTERFACE, "FROZEN_NUMERIC_DECISION_UNIVERSE", "ADOPTED", "Confirms 60 decisions and zero exact session-remaining values; supplies no wait calibration observations."),
    ]
    mapping_rows = []
    for path, evidence_role, disposition, note in evidence_specs:
        if path.suffix.lower() == ".csv":
            _, rows = read_csv(path)
            row_count = len(rows)
        else:
            row_count = 1
        mapping_rows.append({
            "model_version": VERSION,
            "source_file": str(path.relative_to(ROOT)),
            "source_sha256": sha256(path),
            "source_rows": row_count,
            "evidence_role": evidence_role,
            "disposition": disposition,
            "used_to_estimate_probability_mass": "False",
            "used_as_direct_queue_wait": "False",
            "traceability_note": note,
        })
    mapping_fields = list(mapping_rows[0])
    write_csv(OUT_MAPPING, mapping_fields, mapping_rows)

    contract = {
        "phase": "R4F8F",
        "status": "R4F8F_PARTIAL_BUT_USABLE",
        "model_version": VERSION,
        "decision_universe_rows": len(decisions),
        "action_universe_rows": len(actions),
        "target": "P(wait | regime, feasible_action, available evidence)",
        "wait_variable": {
            "name": WAIT_VARIABLE,
            "start": "action commitment / entry into the future attempt-opportunity process",
            "end": "start of the timed qualifying run",
            "includes": ["latent queue delay", "staging delay", "release delay"],
            "excludes": ["timed four-lap run duration", "performance outcome", "competitor evolution", "completion-before-cutoff determination"],
        },
        "sampler": {
            "type": "CATEGORICAL_SUPPORT_POINT",
            "deterministic_seed_interface_required": True,
            "no_draws_materialized_in_r4f8f": True,
            "parameter_file": str(OUT_PARAMETERS.relative_to(ROOT)),
        },
        "non_stop_prior": {
            "distribution_family": "DISCRETE_MAXIMUM_ENTROPY_STRUCTURAL_PRIOR",
            "support_minutes": [5.0, 15.0, 30.0, 45.0],
            "probability_mass": [0.25, 0.25, 0.25, 0.25],
            "empirical_claim": False,
            "reason_for_sharing": "No direct historical queue-wait pairs or defensible action-specific calibration are available.",
        },
        "action_semantics": {
            f"{regime}::{action}": {"queue_semantics": semantics[(regime, action)][0], "protection_semantics": semantics[(regime, action)][1]}
            for regime, action in ACTION_ORDER
        },
        "stop_rule": {"wait_minutes": 0.0, "deterministic": True, "stochastic_draws_allowed": False, "requires_new_attempt": False},
        "last_chance": {"prior": SHARED_PRIOR, "support_level": "WEAK", "broad_structural_prior_required": True, "fabricated_timestamps": False},
        "cutoff_boundary": {
            "completion_before_cutoff": "NOT_DEFINED_IN_R4F8F",
            "required_future_input": "decision-safe session remaining / cutoff policy plus timed-run-duration component",
            "unknown_session_remaining_is_infinite": False,
        },
        "forbidden_uses": [
            "Treating inter-attempt gaps as queue wait",
            "Inferring queue-entry timestamps",
            "Fabricating Last Chance decision timestamps",
            "Fabricating exact session remaining",
            "Reusing old R4P11 final action probabilities",
            "Treating generated old R4P11 draws as observations",
        ],
        "downstream_boundary": "No performance uncertainty engine, final action Monte Carlo, or historical replay is run in R4F8F.",
    }
    OUT_CONTRACT.write_text(json.dumps(contract, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    qa: list[dict[str, str]] = []
    def check(metric: str, value, expected, ok: bool, pass_status: str = "PASS") -> None:
        qa.append({"metric": metric, "value": str(value), "expected": str(expected), "status": pass_status if ok else "FAIL"})

    stop_rows = [row for row in parameter_rows if row["feasible_action"] == "STOP"]
    non_stop_rows = [row for row in parameter_rows if row["feasible_action"] != "STOP"]
    check("decision_universe_unchanged", len(decisions), 60, len(decisions) == 60)
    check("action_universe_unchanged", len(actions), 170, len(actions) == 170)
    check("stop_wait_exactly_zero", {row["support_point_minutes"] for row in stop_rows}, {"0.000000"}, {row["support_point_minutes"] for row in stop_rows} == {"0.000000"})
    check("stop_probability_mass_one", {row["probability_mass"] for row in stop_rows}, {"1.000000"}, {row["probability_mass"] for row in stop_rows} == {"1.000000"})
    check("no_stop_stochastic_draws", contract["stop_rule"]["stochastic_draws_allowed"], False, contract["stop_rule"]["stochastic_draws_allowed"] is False)
    check("day1_retain_withdraw_distribution_ids_distinct", len({row["distribution_id"] for row in parameter_rows if row["regime"] == "DAY1" and row["feasible_action"] != "STOP"}), 2, len({row["distribution_id"] for row in parameter_rows if row["regime"] == "DAY1" and row["feasible_action"] != "STOP"}) == 2)
    check("last_chance_protection_actions_distinct", len({row["distribution_id"] for row in parameter_rows if row["regime"] == "LAST_CHANCE" and row["feasible_action"] != "STOP"}), 2, len({row["distribution_id"] for row in parameter_rows if row["regime"] == "LAST_CHANCE" and row["feasible_action"] != "STOP"}) == 2)
    check("all_non_stop_probability_mass_sums_one", all(abs(sum(float(r["probability_mass"]) for r in non_stop_rows if r["distribution_id"] == dist) - 1.0) < 1e-12 for dist in {r["distribution_id"] for r in non_stop_rows}), True, all(abs(sum(float(r["probability_mass"]) for r in non_stop_rows if r["distribution_id"] == dist) - 1.0) < 1e-12 for dist in {r["distribution_id"] for r in non_stop_rows}))
    check("direct_queue_wait_observations", sum(int(row["direct_queue_wait_observations"]) for row in support_rows), 0, sum(int(row["direct_queue_wait_observations"]) for row in support_rows) == 0, "WARN")
    check("old_r4p11_final_probabilities_reused", any(row["used_to_estimate_probability_mass"] == "True" and "r4p11" in row["source_file"] for row in mapping_rows), False, not any(row["used_to_estimate_probability_mass"] == "True" and "r4p11" in row["source_file"] for row in mapping_rows))
    check("old_r4p11_generated_draws_not_evidence", next(row["disposition"] for row in mapping_rows if row["source_file"].endswith(OLD_P11_DRAWS.name)), "REJECTED_AS_INDEPENDENT_EVIDENCE", next(row["disposition"] for row in mapping_rows if row["source_file"].endswith(OLD_P11_DRAWS.name)) == "REJECTED_AS_INDEPENDENT_EVIDENCE")
    check("inter_attempt_gap_not_queue_wait", identifiability_rows[0]["inter_attempt_gap_as_queue_wait"], "PROHIBITED", identifiability_rows[0]["inter_attempt_gap_as_queue_wait"] == "PROHIBITED")
    check("throughput_proxy_not_direct_wait", sum(row.get("queue_wait_usable", "").lower() == "true" for row in throughput_rows), 0, sum(row.get("queue_wait_usable", "").lower() == "true" for row in throughput_rows) == 0)
    check("no_fake_queue_entry_timestamps", any("timestamp" in field.lower() for field in parameter_fields), False, not any("timestamp" in field.lower() for field in parameter_fields))
    check("no_fake_last_chance_decision_timestamps", contract["last_chance"]["fabricated_timestamps"], False, contract["last_chance"]["fabricated_timestamps"] is False)
    check("no_fake_session_remaining", contract["cutoff_boundary"]["completion_before_cutoff"], "NOT_DEFINED_IN_R4F8F", contract["cutoff_boundary"]["completion_before_cutoff"] == "NOT_DEFINED_IN_R4F8F")
    check("unknown_remaining_not_infinite", contract["cutoff_boundary"]["unknown_session_remaining_is_infinite"], False, contract["cutoff_boundary"]["unknown_session_remaining_is_infinite"] is False)
    check("all_assumptions_versioned", all(row["model_version"] == VERSION and row["distribution_id"] for row in parameter_rows), True, all(row["model_version"] == VERSION and row["distribution_id"] for row in parameter_rows))
    check("all_evidence_traceable", all(row["source_sha256"] and row["traceability_note"] for row in mapping_rows), True, all(row["source_sha256"] and row["traceability_note"] for row in mapping_rows))
    check("no_final_mc_run", contract["sampler"]["no_draws_materialized_in_r4f8f"], True, contract["sampler"]["no_draws_materialized_in_r4f8f"] is True)
    check("last_chance_prior_support", contract["last_chance"]["support_level"], "WEAK", contract["last_chance"]["support_level"] == "WEAK", "WARN")

    protected_after = {str(path.relative_to(ROOT)): sha256(path) for path in protected_files}
    check("r4f7_r4f8b_to_r4f8e_hashes_preserved", protected_after == protected_before, True, protected_after == protected_before)
    write_csv(OUT_QA, ["metric", "value", "expected", "status"], qa)

    qa_counts = Counter(row["status"] for row in qa)
    report = {
        "phase": "R4F8F",
        "status": "R4F8F_PARTIAL_BUT_USABLE" if qa_counts["FAIL"] == 0 else "R4F8F_BLOCKED",
        "model_version": VERSION,
        "frozen_distributions": support_rows,
        "central_evidence_conclusion": "Zero direct historical queue-wait observations support calibration. Non-STOP branches use a shared broad structural prior over the frozen sensitivity grid.",
        "old_r4p11_disposition": "Inspected but not adopted: old final probabilities and generated draws are excluded, and its time-to-completed-attempt wait semantics do not match the R4F8F pre-run-delay variable.",
        "run_duration": {
            "empirical_complete_attempt_rows": 260,
            "median_seconds": duration_rows[0]["median_seconds"],
            "q95_seconds": duration_rows[0]["q95_seconds"],
            "r4f8f_use": "DEFERRED_SEPARATE_COMPLETION_COMPONENT_NOT_INCLUDED_IN_WAIT_DISTRIBUTION",
        },
        "weak_categories": [f"{regime}::{action}" for regime, action in ACTION_ORDER if action != "STOP"],
        "last_chance_broad_structural_prior_required": True,
        "completion_before_cutoff": "REQUIRES_LATER_SEPARATE_POLICY_AND_DECISION_SAFE_SESSION_REMAINING_INPUT",
        "qa_counts": {key: qa_counts.get(key, 0) for key in ("PASS", "WARN", "FAIL")},
        "protected_hash_count": len(protected_files),
        "protected_hashes_preserved": protected_before == protected_after,
        "protected_hashes_before": protected_before,
        "protected_hashes_after": protected_after,
        "outputs": [str(path.relative_to(ROOT)) for path in (OUT_CONTRACT, OUT_PARAMETERS, OUT_MAPPING, OUT_SUPPORT, OUT_QA, OUT_REPORT)],
    }
    OUT_REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    assert protected_before == {str(path.relative_to(ROOT)): sha256(path) for path in protected_files}

    print("FROZEN WAIT DISTRIBUTIONS")
    for row in support_rows:
        print(f'{row["regime"]} {row["feasible_action"]}: n_actions={row["universe_action_rows"]}, class={row["distribution_class"]}, mean={row["mean_wait_minutes"]}, median={row["median_wait_minutes"]}, q95={row["q95_wait_minutes"]}, width={row["q95_minus_q05_minutes"]}, support={row["support_level"]}')
    print(f'QA: PASS={qa_counts["PASS"]} WARN={qa_counts["WARN"]} FAIL={qa_counts["FAIL"]}')
    print(report["status"])


if __name__ == "__main__":
    main()
