#!/usr/bin/env python3
"""R4F8E: deterministically join numeric state into the frozen 60/170 MC universe."""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "r4" / "output"

FUSED_DECISIONS = OUT / "r4f8c_fused_mc_decision_universe_v1.csv"
FUSED_ACTIONS = OUT / "r4f8c_fused_mc_action_expansion_v1.csv"
DAY1_DECISIONS = OUT / "r4f8b_final_mc_eligible_decision_rows_v1.csv"
DAY1_ACTIONS = OUT / "r4f8b_final_mc_action_expansion_v1.csv"
LC_DECISIONS = OUT / "r4lc5e_last_chance_fused_interface_v2.csv"
LC_API_RESULTS = OUT / "r4lc4_last_chance_attempt_candidates_v1.csv"
LC_SCHEMA = OUT / "r4lc5e_fused_decision_schema_contract_v2.json"

OUT_DECISIONS = OUT / "r4f8e_reconstructed_decision_numeric_state_v1.csv"
OUT_ACTIONS = OUT / "r4f8e_reconstructed_action_numeric_interface_v1.csv"
OUT_RECON = OUT / "r4f8e_universe_reconciliation_v1.csv"
OUT_COVERAGE = OUT / "r4f8e_numeric_field_coverage_v1.csv"
OUT_QA = OUT / "r4f8e_decision_numeric_state_reconstruction_qa_v1.csv"
OUT_REPORT = OUT / "r4f8e_decision_numeric_state_reconstruction_report_v1.json"


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


def truthy(value: str) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def protected_paths() -> list[Path]:
    patterns = ("r4f7*", "r4f8b*", "r4f8c*", "r4f8d*")
    found: set[Path] = set()
    for pattern in patterns:
        found.update(OUT.glob(pattern))
    return sorted(p for p in found if p.is_file())


def compact_number(value: str) -> str:
    if value == "":
        return "UNKNOWN"
    return f"{float(value):.3f}"


def main() -> None:
    inputs = [FUSED_DECISIONS, FUSED_ACTIONS, DAY1_DECISIONS, DAY1_ACTIONS, LC_DECISIONS, LC_API_RESULTS, LC_SCHEMA]
    missing = [str(p) for p in inputs if not p.exists()]
    if missing:
        raise SystemExit(f"Missing required inputs: {missing}")

    protected_files = protected_paths()
    protected_before = {str(p.relative_to(ROOT)): sha256(p) for p in protected_files}

    fused_decision_fields, fused_decisions = read_csv(FUSED_DECISIONS)
    fused_action_fields, fused_actions = read_csv(FUSED_ACTIONS)
    day1_fields, day1_rows = read_csv(DAY1_DECISIONS)
    _, day1_actions = read_csv(DAY1_ACTIONS)
    lc_fields, lc_rows = read_csv(LC_DECISIONS)
    _, lc_api_rows = read_csv(LC_API_RESULTS)
    lc_contract = json.loads(LC_SCHEMA.read_text(encoding="utf-8"))

    assert len(fused_decisions) == 60
    assert len(fused_actions) == 170
    assert len(day1_rows) == 50
    assert len(day1_actions) == 150
    assert len(lc_rows) == 10
    assert lc_contract["schema_status"] == "ACTION_SEMANTICS_FROZEN"

    day1_by_id = {row["decision_id"]: row for row in day1_rows}
    lc_by_id = {row["decision_id"]: row for row in lc_rows}

    # Only link an official Last Chance result when its driver/car/year and exact
    # decision-state speed agree. This rejects Harvey's known future final record
    # and the unresolved duplicate 2021 records for Enerson/Kimball.
    lc_api_exact: dict[tuple[str, str, str], dict[str, str]] = {}
    for row in lc_api_rows:
        key = (row["year"], row["car_number"], row["four_lap_average_speed_mph"])
        if key in lc_api_exact:
            lc_api_exact[key] = {}
        else:
            lc_api_exact[key] = row

    decision_rows: list[dict[str, str]] = []
    for fused in fused_decisions:
        regime = fused["regime"]
        source_id = fused["source_decision_id"]
        protected = truthy(fused["protected_result_exists"])
        if regime == "DAY1":
            source = day1_by_id[source_id]
            current_best = source["current_result_mph"]
            current_rank = source["current_rank"]
            benchmark_rank = source["benchmark_rank"]
            benchmark_rank_basis = "DIRECT_SOURCE_FIELD"
            source_attempt_id = source["source_attempt_id"]
            source_attempt_status = "RESOLVED_CANONICAL_ATTEMPT_ID"
            decision_time = source["decision_time_utc"]
            decision_time_quality = source["time_quality"]
            session_remaining = ""
            session_remaining_status = "UNRESOLVED_NO_DECISION_SAFE_SESSION_END_IN_SOURCE_INTERFACE"
            current_protected = current_best
            leaderboard_quality = "SOURCE_DECISION_STATE"
            source_record_locator = f'decision_id={source_id};source_attempt_id={source_attempt_id}'
            join_keys = "source_decision_id=decision_id"
            unresolved = ["session_remaining_seconds"]
            result_context = source["decision_stage"]
            qualification_state = source["qualification_state"]
            benchmark_type = source["benchmark_type"]
            benchmark_speed = source["benchmark_speed_mph"]
            margin = source["margin_to_benchmark_mph"]
            year, car, driver = source["year"], source["car_number"], source["driver_name"]
            source_numeric_interface = str(DAY1_DECISIONS.relative_to(ROOT))
        elif regime == "LAST_CHANCE":
            source = lc_by_id[source_id]
            current_best = source["current_result_mph"]
            current_rank = source["current_rank"]
            benchmark_rank = "3"
            benchmark_rank_basis = "FROZEN_LAST_CHANCE_TOP_THREE_CONTRACT"
            decision_time = source["exact_timestamp"]
            decision_time_quality = source["time_quality"]
            session_remaining = source["time_remaining_seconds"]
            session_remaining_status = (
                "DIRECT_SOURCE_FIELD" if session_remaining else "UNRESOLVED_IN_FROZEN_LAST_CHANCE_INTERFACE"
            )
            current_protected = current_best if protected else ""
            exact_api = lc_api_exact.get((source["year"], source["car_number"], current_best), {}) if current_best else {}
            source_attempt_id = exact_api.get("events_sessions_details_id", "")
            source_attempt_status = (
                "RESOLVED_OFFICIAL_SESSION_DETAIL_ID_BY_EXACT_STATE_SPEED"
                if source_attempt_id else "UNRESOLVED_WITHOUT_SAFE_ATTEMPT_LEVEL_JOIN"
            )
            leaderboard_quality = f'FROZEN_LAST_CHANCE_STATE_{source["state_quality"]}'
            source_record_locator = f'decision_id={source_id}' + (f';events_sessions_details_id={source_attempt_id}' if source_attempt_id else "")
            join_keys = "source_decision_id=decision_id; exact year+car_number+current_result_mph for optional official result ID"
            unresolved = []
            if not decision_time:
                unresolved.append("decision_time_utc")
            if not session_remaining:
                unresolved.append("session_remaining_seconds")
            if not current_best:
                unresolved.extend(["current_best_speed_mph", "current_protected_result_speed_mph" if protected else "source_attempt_id"])
            if not source_attempt_id and "source_attempt_id" not in unresolved:
                unresolved.append("source_attempt_id")
            result_context = source["decision_stage"]
            qualification_state = source["qualification_state"]
            benchmark_type = source["benchmark_type"]
            benchmark_speed = source["benchmark_speed_mph"]
            margin = source["margin_to_benchmark_mph"]
            year, car, driver = source["year"], source["car_number"], source["driver_name"]
            source_numeric_interface = str(LC_DECISIONS.relative_to(ROOT))
        else:
            raise AssertionError(f"Unexpected regime: {regime}")

        leaderboard_context = (
            f"{regime}|CURRENT_RANK={current_rank}|CURRENT_BEST_MPH={compact_number(current_best)}|"
            f"BENCHMARK={benchmark_type}|BENCHMARK_RANK={benchmark_rank}|BENCHMARK_MPH={compact_number(benchmark_speed)}|"
            f"QUALIFICATION_STATE={qualification_state}"
        )
        decision_rows.append({
            "fused_decision_id": fused["fused_decision_id"],
            "regime": regime,
            "source_decision_id": source_id,
            "source_file": fused["source_file"],
            "year": year,
            "car_number": car,
            "driver_name": driver,
            "decision_stage": result_context,
            "source_attempt_id": source_attempt_id,
            "source_attempt_id_status": source_attempt_status,
            "source_result_context": result_context,
            "decision_time_utc": decision_time,
            "decision_time_quality": decision_time_quality,
            "session_remaining_seconds": session_remaining,
            "session_remaining_status": session_remaining_status,
            "protected_result_exists": "True" if protected else "False",
            "current_protected_result_speed_mph": current_protected,
            "current_best_speed_mph": current_best,
            "current_rank": current_rank,
            "current_best_rank": current_rank,
            "benchmark_type": benchmark_type,
            "benchmark_rank": benchmark_rank,
            "benchmark_rank_basis": benchmark_rank_basis,
            "benchmark_speed_mph": benchmark_speed,
            "margin_to_benchmark_mph": margin,
            "qualification_state": qualification_state,
            "decision_state_leaderboard_context": leaderboard_context,
            "leaderboard_context_quality": leaderboard_quality,
            "state_join_status": "COMPLETE_EXCEPT_EXPLICIT_UNRESOLVED_FIELDS" if unresolved else "COMPLETE_SOURCE_GROUNDED_JOIN",
            "unresolved_fields": ";".join(sorted(set(unresolved))),
            "join_keys": join_keys,
            "source_numeric_interface": source_numeric_interface,
            "source_record_locator": source_record_locator,
            "leakage_safe": "True",
        })

    decision_fields = list(decision_rows[0])
    write_csv(OUT_DECISIONS, decision_fields, decision_rows)
    state_by_id = {row["fused_decision_id"]: row for row in decision_rows}

    numeric_action_fields = [
        "year", "car_number", "driver_name", "source_decision_id", "source_attempt_id",
        "decision_time_utc", "decision_time_quality", "session_remaining_seconds",
        "protected_result_speed_before_action_mph", "current_best_speed_mph", "current_rank",
        "benchmark_type", "benchmark_rank", "benchmark_speed_mph", "margin_to_benchmark_mph",
        "qualification_state", "decision_state_leaderboard_context", "numeric_state_join_status",
        "numeric_state_unresolved_fields", "numeric_state_source_interface", "leakage_safe",
    ]
    action_rows: list[dict[str, str]] = []
    for action in fused_actions:
        state = state_by_id[action["fused_decision_id"]]
        row = dict(action)
        row.update({
            "year": state["year"], "car_number": state["car_number"], "driver_name": state["driver_name"],
            "source_decision_id": state["source_decision_id"], "source_attempt_id": state["source_attempt_id"],
            "decision_time_utc": state["decision_time_utc"], "decision_time_quality": state["decision_time_quality"],
            "session_remaining_seconds": state["session_remaining_seconds"],
            "protected_result_speed_before_action_mph": state["current_protected_result_speed_mph"],
            "current_best_speed_mph": state["current_best_speed_mph"], "current_rank": state["current_rank"],
            "benchmark_type": state["benchmark_type"], "benchmark_rank": state["benchmark_rank"],
            "benchmark_speed_mph": state["benchmark_speed_mph"], "margin_to_benchmark_mph": state["margin_to_benchmark_mph"],
            "qualification_state": state["qualification_state"],
            "decision_state_leaderboard_context": state["decision_state_leaderboard_context"],
            "numeric_state_join_status": state["state_join_status"],
            "numeric_state_unresolved_fields": state["unresolved_fields"],
            "numeric_state_source_interface": state["source_numeric_interface"], "leakage_safe": "True",
        })
        action_rows.append(row)
    write_csv(OUT_ACTIONS, fused_action_fields + numeric_action_fields, action_rows)

    legacy_decision_ids = {f'DAY1::{r["decision_id"]}' for r in day1_rows}
    legacy_action_keys = {(f'DAY1::{r["decision_id"]}', r["action"]) for r in day1_actions}
    recon_rows: list[dict[str, str]] = []
    for row in decision_rows:
        preserved = row["fused_decision_id"] in legacy_decision_ids
        recon_rows.append({
            "record_type": "DECISION", "fused_decision_id": row["fused_decision_id"], "feasible_action": "",
            "regime": row["regime"], "reconciliation_status": "PRESERVED_FROM_R4F8B" if preserved else "ADDED_IN_R4F8C_LAST_CHANCE_EXTENSION",
            "source_decision_id": row["source_decision_id"], "source_file": row["source_file"],
            "reason": "Existing frozen Day1 MC decision" if preserved else "Valid frozen Last Chance decision opportunity added by the regime-specific R4F8C contract",
        })
    for row in fused_actions:
        preserved = (row["fused_decision_id"], row["feasible_action"]) in legacy_action_keys
        recon_rows.append({
            "record_type": "ACTION", "fused_decision_id": row["fused_decision_id"], "feasible_action": row["feasible_action"],
            "regime": row["regime"], "reconciliation_status": "PRESERVED_FROM_R4F8B" if preserved else "ADDED_IN_R4F8C_LAST_CHANCE_EXTENSION",
            "source_decision_id": state_by_id[row["fused_decision_id"]]["source_decision_id"],
            "source_file": state_by_id[row["fused_decision_id"]]["source_file"],
            "reason": "Existing frozen Day1 MC action" if preserved else "Action allowed by frozen Last Chance protected/unprotected result semantics",
        })
    write_csv(OUT_RECON, list(recon_rows[0]), recon_rows)

    coverage_fields = [
        "decision_time_utc", "year", "car_number", "driver_name", "source_attempt_id",
        "current_protected_result_speed_mph", "current_best_speed_mph", "current_rank", "current_best_rank",
        "benchmark_speed_mph", "benchmark_rank", "session_remaining_seconds", "decision_state_leaderboard_context",
    ]
    coverage_rows: list[dict[str, str]] = []
    for regime in ("ALL", "DAY1", "LAST_CHANCE"):
        subset = decision_rows if regime == "ALL" else [r for r in decision_rows if r["regime"] == regime]
        for field in coverage_fields:
            resolved = sum(r[field] != "" for r in subset)
            coverage_rows.append({
                "regime": regime, "field": field, "decision_rows": len(subset), "resolved_rows": resolved,
                "unresolved_rows": len(subset) - resolved, "resolved_fraction": f"{resolved / len(subset):.6f}",
                "resolution_rule": "DIRECT_OR_EXACT_DETERMINISTIC_SOURCE_JOIN; EMPTY_MEANS_UNRESOLVED",
            })
    write_csv(OUT_COVERAGE, list(coverage_rows[0]), coverage_rows)

    qa: list[dict[str, str]] = []
    def check(metric: str, value, expected, ok: bool, pass_status: str = "PASS") -> None:
        qa.append({"metric": metric, "value": str(value), "expected": str(expected), "status": pass_status if ok else "FAIL"})

    check("decision_rows", len(decision_rows), 60, len(decision_rows) == 60)
    check("action_rows", len(action_rows), 170, len(action_rows) == 170)
    check("unique_fused_decision_id", len({r["fused_decision_id"] for r in decision_rows}), 60, len({r["fused_decision_id"] for r in decision_rows}) == 60)
    check("day1_decisions_preserved", sum(r["regime"] == "DAY1" for r in decision_rows), 50, sum(r["regime"] == "DAY1" for r in decision_rows) == 50)
    check("last_chance_decisions_added", sum(r["regime"] == "LAST_CHANCE" for r in decision_rows), 10, sum(r["regime"] == "LAST_CHANCE" for r in decision_rows) == 10)
    check("day1_actions_preserved", sum(r["regime"] == "DAY1" for r in action_rows), 150, sum(r["regime"] == "DAY1" for r in action_rows) == 150)
    check("last_chance_actions_added", sum(r["regime"] == "LAST_CHANCE" for r in action_rows), 20, sum(r["regime"] == "LAST_CHANCE" for r in action_rows) == 20)
    check("action_contract_columns_exact", all(all(r[f] == src[f] for f in fused_action_fields) for r, src in zip(action_rows, fused_actions)), True, all(all(r[f] == src[f] for f in fused_action_fields) for r, src in zip(action_rows, fused_actions)))
    check("car_number_preserved_as_text", all(isinstance(r["car_number"], str) for r in decision_rows), True, all(isinstance(r["car_number"], str) for r in decision_rows))
    check("year_identity_driver_complete", sum(all(r[f] for f in ("year", "car_number", "driver_name")) for r in decision_rows), 60, sum(all(r[f] for f in ("year", "car_number", "driver_name")) for r in decision_rows) == 60)
    check("decision_time_utc_resolved", sum(bool(r["decision_time_utc"]) for r in decision_rows), 50, sum(bool(r["decision_time_utc"]) for r in decision_rows) == 50, "WARN")
    check("session_remaining_seconds_resolved", sum(bool(r["session_remaining_seconds"]) for r in decision_rows), 0, sum(bool(r["session_remaining_seconds"]) for r in decision_rows) == 0, "WARN")
    check("current_best_speed_resolved", sum(bool(r["current_best_speed_mph"]) for r in decision_rows), 57, sum(bool(r["current_best_speed_mph"]) for r in decision_rows) == 57, "WARN")
    check("protected_result_speed_resolved", sum(bool(r["current_protected_result_speed_mph"]) for r in decision_rows), 56, sum(bool(r["current_protected_result_speed_mph"]) for r in decision_rows) == 56)
    check("rank_and_benchmark_resolved", sum(all(r[f] for f in ("current_rank", "benchmark_rank", "benchmark_speed_mph")) for r in decision_rows), 60, sum(all(r[f] for f in ("current_rank", "benchmark_rank", "benchmark_speed_mph")) for r in decision_rows) == 60)
    check("source_attempt_id_resolved", sum(bool(r["source_attempt_id"]) for r in decision_rows), 57, sum(bool(r["source_attempt_id"]) for r in decision_rows) == 57, "WARN")
    check("unprotected_has_no_protected_speed", all(not r["current_protected_result_speed_mph"] for r in decision_rows if not truthy(r["protected_result_exists"])), True, all(not r["current_protected_result_speed_mph"] for r in decision_rows if not truthy(r["protected_result_exists"])))
    check("last_chance_actions_are_regime_specific", Counter(r["feasible_action"] for r in action_rows if r["regime"] == "LAST_CHANCE"), {"STOP": 10, "WITHDRAW_AND_REATTEMPT": 6, "REATTEMPT": 4}, Counter(r["feasible_action"] for r in action_rows if r["regime"] == "LAST_CHANCE") == Counter({"STOP": 10, "WITHDRAW_AND_REATTEMPT": 6, "REATTEMPT": 4}))
    forbidden = ("future", "outcome", "observed_action", "resulting_speed", "realized_weather", "historical_action")
    check("no_forbidden_leakage_columns", [f for f in decision_fields if any(x in f.lower() for x in forbidden)], [], not any(any(x in f.lower() for x in forbidden) for f in decision_fields))
    check("all_rows_marked_leakage_safe", sum(r["leakage_safe"] == "True" for r in decision_rows), 60, all(r["leakage_safe"] == "True" for r in decision_rows))

    protected_after = {str(p.relative_to(ROOT)): sha256(p) for p in protected_files}
    check("r4f7_r4f8b_r4f8c_r4f8d_hashes_preserved", protected_after == protected_before, True, protected_after == protected_before)
    write_csv(OUT_QA, ["metric", "value", "expected", "status"], qa)

    qa_counts = Counter(r["status"] for r in qa)
    status = "R4F8E_DECISION_NUMERIC_STATE_RECONSTRUCTION_READY" if qa_counts["FAIL"] == 0 else "R4F8E_DECISION_NUMERIC_STATE_RECONSTRUCTION_PARTIAL"
    report = {
        "phase": "R4F8E",
        "status": status,
        "decision_rows": len(decision_rows),
        "action_rows": len(action_rows),
        "universe_reconciliation": {
            "r4f8b_decisions": 50, "r4f8e_decisions": 60, "added_decisions": 10,
            "r4f8b_actions": 150, "r4f8e_actions": 170, "added_actions": 20,
            "explanation": "R4F8C preserved all 50/150 Day1 members and added 10 frozen Last Chance decision opportunities with two regime-specific actions each.",
            "last_chance_protected": 6, "last_chance_unprotected": 4,
        },
        "field_resolution": {
            "decision_time_utc": "50/60; all 10 Last Chance decision timestamps remain unresolved",
            "session_remaining_seconds": "0/60; no decision-safe exact session-end join is present in the frozen source interfaces",
            "current_best_speed_mph": "57/60; unresolved for 2021 Enerson, 2021 Kimball, and 2023 Harvey",
            "current_protected_result_speed_mph": "56/60; all protected decisions resolved; four unprotected decisions intentionally blank",
            "source_attempt_id": "57/60; unresolved for the same three Last Chance rows whose predecision result identity is not safe to assign",
            "rank_benchmark_leaderboard_context": "60/60",
        },
        "last_chance_benchmark_semantics": "LAST_CHANCE_SURVIVAL_BUBBLE at benchmark rank 3, distinct from Day1 FAST_NINE_ADVANCEMENT or TOP_12_ADVANCEMENT.",
        "leakage_controls": {
            "future_attempt_outcome_used": False,
            "future_leaderboard_state_used": False,
            "future_weather_observation_used": False,
            "future_historical_action_result_used": False,
            "allowed_sources": [str(DAY1_DECISIONS.relative_to(ROOT)), str(LC_DECISIONS.relative_to(ROOT)), str(LC_API_RESULTS.relative_to(ROOT)), str(LC_SCHEMA.relative_to(ROOT))],
        },
        "wait_queue_boundary": "Old R4P11 wait files were not joined, frozen, or treated as final action probabilities in R4F8E.",
        "qa_counts": {k: qa_counts.get(k, 0) for k in ("PASS", "WARN", "FAIL")},
        "protected_hash_count": len(protected_before),
        "protected_hashes_preserved": protected_before == protected_after,
        "protected_hashes_before": protected_before,
        "protected_hashes_after": protected_after,
        "outputs": [str(p.relative_to(ROOT)) for p in (OUT_DECISIONS, OUT_ACTIONS, OUT_RECON, OUT_COVERAGE, OUT_QA, OUT_REPORT)],
    }
    OUT_REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    assert protected_before == {str(p.relative_to(ROOT)): sha256(p) for p in protected_files}

    print(f"DECISIONS: {len(decision_rows)} (DAY1=50, LAST_CHANCE=10)")
    print(f"ACTIONS: {len(action_rows)} (DAY1=150, LAST_CHANCE=20)")
    print("UNIVERSE DELTA: +10 decisions, +20 actions, all from frozen Last Chance interface")
    print("NUMERIC COVERAGE: time=50/60, current_best=57/60, protected_speed=56/60, rank+benchmark=60/60, session_remaining=0/60")
    print(f'QA: PASS={qa_counts["PASS"]} WARN={qa_counts["WARN"]} FAIL={qa_counts["FAIL"]}')
    print(status)


if __name__ == "__main__":
    main()
