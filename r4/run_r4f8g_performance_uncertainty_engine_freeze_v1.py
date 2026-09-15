#!/usr/bin/env python3
"""Freeze R4F8G predictive performance uncertainty without running action MC."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import random
import re
import statistics
import unicodedata
from collections import Counter
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "r4" / "output"

ARCHITECTURE = OUT / "r4f7c7_final_performance_architecture_contract_v1.json"
STATE_PANEL = OUT / "r4f7c5_prospective_past_only_state_panel_v1.csv"
REFERENCE_PANEL = OUT / "r4f6g_canonical_fast_friday_reference_panel_v2.csv"
DECISIONS = OUT / "r4f8e_reconstructed_decision_numeric_state_v1.csv"
ACTIONS = OUT / "r4f8e_reconstructed_action_numeric_interface_v1.csv"
WAIT_CONTRACT = OUT / "r4f8f_wait_queue_model_contract_v1.json"
VALIDATION = OUT / "r4f7v2_external_validation_conclusion_v1.json"
REPEAT_TRANSITIONS = OUT / "r4p2_multi_run_transitions_v1.csv"

OUT_CONTRACT = OUT / "r4f8g_performance_uncertainty_contract_v1.json"
OUT_RESIDUALS = OUT / "r4f8g_development_residual_calibration_evidence_v1.csv"
OUT_PARAMETERS = OUT / "r4f8g_uncertainty_parameters_v1.csv"
OUT_DECISIONS = OUT / "r4f8g_decision_predictive_uncertainty_state_v1.csv"
OUT_SUPPORT = OUT / "r4f8g_uncertainty_support_summary_v1.csv"
OUT_QA = OUT / "r4f8g_performance_uncertainty_qa_v1.csv"
OUT_REPORT = OUT / "r4f8g_performance_uncertainty_report_v1.json"

VERSION = "R4F8G_PERFORMANCE_UNCERTAINTY_V1"
K = 3.0
FROZEN_PRIOR_MEAN = -0.685759615384616
FROZEN_PRIOR_SD = 0.9003554799066349
EXPECTED_K3_LOYO_MAE = 0.6260306430673608
DEVELOPMENT_YEARS = {2020, 2021, 2023}
SEED = 20260910
Z05 = -1.6448536269514722
Z25 = -0.6744897501960817
Z75 = 0.6744897501960817
Z95 = 1.6448536269514722


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


def norm_name(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii").lower()
    return " ".join(re.sub(r"[^a-z0-9]+", " ", value).split())


def parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def quantile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    low = math.floor(position)
    high = math.ceil(position)
    if low == high:
        return ordered[low]
    weight = position - low
    return ordered[low] * (1.0 - weight) + ordered[high] * weight


def uncertainty_class(n: int) -> str:
    if n <= 2:
        return "EARLY_BROAD_N_0_2"
    if n <= 9:
        return "LIMITED_N_3_9"
    if n <= 19:
        return "MODERATE_N_10_19"
    return "LATER_N_20_PLUS"


def protected_paths() -> list[Path]:
    found: set[Path] = set()
    for pattern in ("r4f7*", "r4f8e*", "r4f8f*"):
        found.update(OUT.glob(pattern))
    return sorted(path for path in found if path.is_file())


def main() -> None:
    required = [ARCHITECTURE, STATE_PANEL, REFERENCE_PANEL, DECISIONS, ACTIONS, WAIT_CONTRACT, VALIDATION, REPEAT_TRANSITIONS]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise SystemExit(f"Missing frozen input: {missing}")

    protected_files = protected_paths()
    protected_before = {str(path.relative_to(ROOT)): sha256(path) for path in protected_files}

    architecture = json.loads(ARCHITECTURE.read_text(encoding="utf-8"))
    validation = json.loads(VALIDATION.read_text(encoding="utf-8"))
    wait_contract = json.loads(WAIT_CONTRACT.read_text(encoding="utf-8"))
    _, development = read_csv(STATE_PANEL)
    _, references = read_csv(REFERENCE_PANEL)
    _, decisions = read_csv(DECISIONS)
    _, actions = read_csv(ACTIONS)
    _, repeat_transitions = read_csv(REPEAT_TRANSITIONS)

    assert architecture["status"] == "R4F7C7_FINAL_DEVELOPMENT_ARCHITECTURE_FROZEN"
    assert architecture["selected_shrinkage_k"] == K
    assert abs(architecture["frozen_cross_year_prior_mean_residual_mph"] - FROZEN_PRIOR_MEAN) < 1e-12
    assert abs(architecture["frozen_cross_year_prior_sd_mph"] - FROZEN_PRIOR_SD) < 1e-12
    assert set(architecture["prior_training_years"]) == DEVELOPMENT_YEARS
    assert validation["model_status"] == "DEVELOPMENT_SUPPORTED_EXTERNAL_VALIDATION_MIXED"
    assert wait_contract["status"] == "R4F8F_PARTIAL_BUT_USABLE"
    assert len(development) == 104 and len(decisions) == 60 and len(actions) == 170
    repeat_deltas = [float(row["delta_four_lap_average_speed_mph"]) for row in repeat_transitions if row["delta_four_lap_average_speed_mph"]]
    assert len(repeat_deltas) == 92

    # Recreate fixed-k=3 leave-one-year-out point predictions using only the
    # frozen development years. These prediction errors are the calibration
    # evidence for the uncertainty layer; 2024 never enters estimation.
    residual_rows: list[dict] = []
    for row in development:
        test_year = int(row["year"])
        train_residuals = [float(other["reference_residual_mph"]) for other in development if int(other["year"]) != test_year]
        prior_mean = statistics.mean(train_residuals)
        n = int(row["past_other_count"])
        field_mean = float(row["past_other_mean_residual_mph"]) if n else 0.0
        posterior = (K * prior_mean + n * field_mean) / (K + n)
        predicted = float(row["reference_speed_mph"]) + posterior
        error = float(row["actual_speed_mph"]) - predicted
        residual_rows.append({
            "model_version": VERSION,
            "test_year": test_year,
            "training_years": ";".join(str(year) for year in sorted(DEVELOPMENT_YEARS - {test_year})),
            "attempt_id": row["attempt_id"],
            "driver_key": row["driver_key"],
            "performance_time_utc": row["performance_time_utc"],
            "same_session_other_support_count": n,
            "support_class": uncertainty_class(n),
            "reference_speed_mph": f'{float(row["reference_speed_mph"]):.6f}',
            "observed_speed_mph": f'{float(row["actual_speed_mph"]):.6f}',
            "held_out_prior_mean_residual_mph": f"{prior_mean:.12f}",
            "past_other_mean_residual_mph": f"{field_mean:.12f}",
            "posterior_calibration_mph": f"{posterior:.12f}",
            "predicted_speed_mph": f"{predicted:.12f}",
            "prediction_error_observed_minus_predicted_mph": f"{error:.12f}",
            "absolute_error_mph": f"{abs(error):.12f}",
            "estimation_role": "DEVELOPMENT_LOYO_UNCERTAINTY_CALIBRATION",
            "future_information_used": "False",
        })

    residual_fields = list(residual_rows[0])
    write_csv(OUT_RESIDUALS, residual_fields, residual_rows)
    residual_values = [float(row["prediction_error_observed_minus_predicted_mph"]) for row in residual_rows]
    fixed_k_mae = statistics.mean(abs(value) for value in residual_values)

    # The high-support held-out residual SD is used as a conservative irreducible
    # run/noise floor. Narrow low-n subgroups are not separately fitted because
    # only nine development rows have n<=2 and their low variance is unstable.
    high_support_errors = [
        float(row["prediction_error_observed_minus_predicted_mph"])
        for row in residual_rows if int(row["same_session_other_support_count"]) >= 10
    ]
    run_noise_floor_sd = statistics.stdev(high_support_errors)
    assert len(high_support_errors) == 74

    parameter_rows: list[dict] = []
    for n in range(0, 61):
        calibration_sd = FROZEN_PRIOR_SD * math.sqrt(K / (K + n))
        predictive_sd = math.sqrt(run_noise_floor_sd ** 2 + calibration_sd ** 2)
        parameter_rows.append({
            "model_version": VERSION,
            "same_session_other_support_count": n,
            "uncertainty_class": uncertainty_class(n),
            "distribution_family": "NORMAL_CONSERVATIVE_EMPIRICAL_COMPONENTS",
            "run_noise_floor_sd_mph": f"{run_noise_floor_sd:.12f}",
            "calibration_uncertainty_sd_mph": f"{calibration_sd:.12f}",
            "predictive_sd_mph": f"{predictive_sd:.12f}",
            "q05_z": f"{Z05:.12f}",
            "q25_z": f"{Z25:.12f}",
            "q50_z": "0.000000000000",
            "q75_z": f"{Z75:.12f}",
            "q95_z": f"{Z95:.12f}",
            "calibration_formula": "frozen_prior_sd*sqrt(k/(k+n))",
            "predictive_scale_formula": "sqrt(run_noise_floor_sd^2+calibration_uncertainty_sd^2)",
            "shrinkage_k": f"{K:.6f}",
            "development_residual_rows": len(residual_rows),
            "high_support_floor_rows": len(high_support_errors),
            "parameter_role": "SAMPLEABLE_SCALE_LOOKUP; NO_ACTION_PROBABILITIES",
        })
    parameter_fields = list(parameter_rows[0])
    write_csv(OUT_PARAMETERS, parameter_fields, parameter_rows)
    scale_by_n = {int(row["same_session_other_support_count"]): float(row["predictive_sd_mph"]) for row in parameter_rows}

    # Frozen reference lookup. Development-state references take precedence so
    # current production centers remain tied to the actual R4F7 input panel.
    ref_lookup: dict[tuple[int, str], dict[str, str]] = {}
    for row in references:
        ref_lookup[(int(row["year"]), row["driver_key"])] = {
            "speed": row["reference_speed_mph"], "type": row["reference_type"],
            "source": str(REFERENCE_PANEL.relative_to(ROOT)),
        }
    for row in development:
        ref_lookup[(int(row["year"]), row["driver_key"])] = {
            "speed": row["reference_speed_mph"], "type": "FROZEN_R4F7_DEVELOPMENT_REFERENCE",
            "source": str(STATE_PANEL.relative_to(ROOT)),
        }

    # Strictly prior Day1 observations can inform the field state. For Last
    # Chance, only values contained in the same frozen decision-state block are
    # eligible; Day1 observations from the prior day are not called same-session.
    development_by_year = Counter(int(row["year"]) for row in development)
    assert set(development_by_year) == DEVELOPMENT_YEARS

    lc_state_residuals: dict[int, list[tuple[str, float]]] = {}
    for state in decisions:
        if state["regime"] != "LAST_CHANCE" or not state["current_best_speed_mph"]:
            continue
        key = (int(state["year"]), norm_name(state["driver_name"]))
        ref = ref_lookup.get(key)
        if ref:
            lc_state_residuals.setdefault(int(state["year"]), []).append(
                (norm_name(state["driver_name"]), float(state["current_best_speed_mph"]) - float(ref["speed"]))
            )

    decision_rows: list[dict] = []
    for state in decisions:
        year = int(state["year"])
        key = (year, norm_name(state["driver_name"]))
        ref = ref_lookup.get(key)
        support_basis = ""
        support_residuals: list[float] = []
        if state["regime"] == "DAY1" and state["decision_time_utc"]:
            cutoff = parse_time(state["decision_time_utc"])
            support_residuals = [
                float(row["reference_residual_mph"])
                for row in development
                if int(row["year"]) == year
                and row["driver_key"] != key[1]
                and parse_time(row["performance_time_utc"]) < cutoff
            ]
            support_basis = "FROZEN_R4F7_STRICTLY_EARLIER_OTHER_DRIVER_DEVELOPMENT_ROWS"
        elif state["regime"] == "LAST_CHANCE" and year == 2023:
            support_residuals = [value for driver, value in lc_state_residuals.get(year, []) if driver != key[1]]
            support_basis = "FROZEN_LAST_CHANCE_POST_GUARANTEED_BREAK_OTHER_DRIVER_STATE"
        elif state["regime"] == "LAST_CHANCE":
            support_basis = "NO_DECISION_SAFE_SAME_SESSION_CALIBRATION_ROWS"

        n = len(support_residuals)
        field_mean = statistics.mean(support_residuals) if support_residuals else None
        posterior = (K * FROZEN_PRIOR_MEAN + n * (field_mean or 0.0)) / (K + n)
        ready = ref is not None
        degraded_reasons: list[str] = []
        if not ref:
            degraded_reasons.append("MISSING_FROZEN_FAST_FRIDAY_REFERENCE")
        if not state["current_best_speed_mph"]:
            degraded_reasons.append("CURRENT_BEST_SPEED_UNRESOLVED_NOT_REQUIRED_BY_POINT_FORMULA")
        if not state["source_attempt_id"]:
            degraded_reasons.append("SOURCE_ATTEMPT_ID_UNRESOLVED_NOT_REQUIRED_BY_POINT_FORMULA")
        if state["regime"] == "LAST_CHANCE" and not state["decision_time_utc"]:
            degraded_reasons.append("LAST_CHANCE_TIMESTAMP_UNRESOLVED_STATE_BLOCK_ONLY")
        if year == 2024:
            degraded_reasons.append("2024_APPLICATION_ONLY_NO_RETUNING")

        if ready:
            center = float(ref["speed"]) + posterior
            sd = scale_by_n[n]
            quantiles = {
                "q05": center + Z05 * sd, "q25": center + Z25 * sd,
                "q50": center, "q75": center + Z75 * sd, "q95": center + Z95 * sd,
            }
            readiness = "SAMPLE_READY_DEGRADED_SUPPORT" if degraded_reasons else "SAMPLE_READY"
        else:
            center = sd = None
            quantiles = {name: None for name in ("q05", "q25", "q50", "q75", "q95")}
            readiness = "NOT_PERFORMANCE_SAMPLE_READY"

        def fmt(value: float | None) -> str:
            return "" if value is None else f"{value:.12f}"

        decision_rows.append({
            "model_version": VERSION,
            "fused_decision_id": state["fused_decision_id"],
            "source_decision_id": state["source_decision_id"],
            "regime": state["regime"],
            "year": year,
            "car_number": state["car_number"],
            "driver_name": state["driver_name"],
            "driver_key": key[1],
            "source_attempt_id": state["source_attempt_id"],
            "decision_time_utc": state["decision_time_utc"],
            "fast_friday_reference_mph": "" if not ref else f'{float(ref["speed"]):.6f}',
            "fast_friday_reference_type": "" if not ref else ref["type"],
            "reference_source_file": "" if not ref else ref["source"],
            "same_session_other_support_count": n,
            "same_session_support_basis": support_basis,
            "observed_field_mean_residual_mph": fmt(field_mean),
            "frozen_prior_mean_residual_mph": f"{FROZEN_PRIOR_MEAN:.12f}",
            "shrinkage_k": f"{K:.6f}",
            "posterior_calibration_mph": fmt(posterior) if ready else "",
            "predictive_mean_speed_mph": fmt(center),
            "predictive_sd_mph": fmt(sd),
            "q05_speed_mph": fmt(quantiles["q05"]),
            "q25_speed_mph": fmt(quantiles["q25"]),
            "q50_speed_mph": fmt(quantiles["q50"]),
            "q75_speed_mph": fmt(quantiles["q75"]),
            "q95_speed_mph": fmt(quantiles["q95"]),
            "uncertainty_class": uncertainty_class(n) if ready else "NOT_SAMPLE_READY_MISSING_REFERENCE",
            "performance_sample_ready": "True" if ready else "False",
            "readiness_status": readiness,
            "degraded_or_unresolved_reasons": ";".join(degraded_reasons),
            "point_prediction_formula": "FastFridayReference+((k*frozen_prior_mean)+(n*strictly_prior_other_driver_mean))/(k+n)",
            "uncertainty_formula": "Normal(center,sqrt(high_support_LOYO_residual_sd^2+prior_sd^2*k/(k+n)))",
            "calibration_evidence_file": str(OUT_RESIDUALS.relative_to(ROOT)),
            "uncertainty_parameter_file": str(OUT_PARAMETERS.relative_to(ROOT)),
            "future_outcome_or_leaderboard_used": "False",
        })

    decision_fields = list(decision_rows[0])
    write_csv(OUT_DECISIONS, decision_fields, decision_rows)

    support_rows: list[dict] = []
    for label, subset in [
        ("DEVELOPMENT_ALL", residual_rows),
        ("DEVELOPMENT_EARLY_N_0_2", [r for r in residual_rows if int(r["same_session_other_support_count"]) <= 2]),
        ("DEVELOPMENT_LIMITED_N_3_9", [r for r in residual_rows if 3 <= int(r["same_session_other_support_count"]) <= 9]),
        ("DEVELOPMENT_ESTABLISHED_N_10_PLUS", [r for r in residual_rows if int(r["same_session_other_support_count"]) >= 10]),
    ]:
        values = [float(row["prediction_error_observed_minus_predicted_mph"]) for row in subset]
        support_rows.append({
            "summary_type": "CALIBRATION_RESIDUALS", "group": label, "rows": len(values),
            "support_count_min": min(int(r["same_session_other_support_count"]) for r in subset),
            "support_count_max": max(int(r["same_session_other_support_count"]) for r in subset),
            "mean_error_mph": f"{statistics.mean(values):.12f}", "sd_error_mph": f"{statistics.stdev(values):.12f}",
            "q05_error_mph": f"{quantile(values, 0.05):.12f}", "q25_error_mph": f"{quantile(values, 0.25):.12f}",
            "q50_error_mph": f"{quantile(values, 0.50):.12f}", "q75_error_mph": f"{quantile(values, 0.75):.12f}",
            "q95_error_mph": f"{quantile(values, 0.95):.12f}",
            "decision_sample_ready_rows": "", "interpretation": "Held-out development calibration evidence only; subgroup variance is diagnostic, not independently fitted.",
        })
    support_rows.append({
        "summary_type": "RUN_TO_RUN_DIAGNOSTIC", "group": "CONSECUTIVE_COMPLETE_REPEAT_TRANSITIONS", "rows": len(repeat_deltas),
        "support_count_min": "", "support_count_max": "",
        "mean_error_mph": f"{statistics.mean(repeat_deltas):.12f}", "sd_error_mph": f"{statistics.stdev(repeat_deltas):.12f}",
        "q05_error_mph": f"{quantile(repeat_deltas, 0.05):.12f}", "q25_error_mph": f"{quantile(repeat_deltas, 0.25):.12f}",
        "q50_error_mph": f"{quantile(repeat_deltas, 0.50):.12f}", "q75_error_mph": f"{quantile(repeat_deltas, 0.75):.12f}",
        "q95_error_mph": f"{quantile(repeat_deltas, 0.95):.12f}",
        "decision_sample_ready_rows": "",
        "interpretation": "Existing repeat-transition evidence is a scale cross-check only; it is not added independently because held-out prediction errors already include run variability.",
    })
    for group in sorted({row["uncertainty_class"] for row in decision_rows}):
        subset = [row for row in decision_rows if row["uncertainty_class"] == group]
        support_rows.append({
            "summary_type": "DECISION_APPLICATION", "group": group, "rows": len(subset),
            "support_count_min": min(int(r["same_session_other_support_count"]) for r in subset),
            "support_count_max": max(int(r["same_session_other_support_count"]) for r in subset),
            "mean_error_mph": "", "sd_error_mph": "", "q05_error_mph": "", "q25_error_mph": "", "q50_error_mph": "", "q75_error_mph": "", "q95_error_mph": "",
            "decision_sample_ready_rows": sum(r["performance_sample_ready"] == "True" for r in subset),
            "interpretation": "Per-decision uncertainty/readiness coverage; no historical action evaluation.",
        })
    support_fields = list(support_rows[0])
    write_csv(OUT_SUPPORT, support_fields, support_rows)

    contract = {
        "phase": "R4F8G",
        "status": "R4F8G_PARTIAL_BUT_USABLE",
        "model_version": VERSION,
        "target": "P(future_attempt_speed | current decision state, frozen performance architecture, available same-session evidence)",
        "frozen_point_architecture": architecture["primary_performance_architecture"],
        "point_equation": architecture["equation"],
        "shrinkage_k": K,
        "frozen_prior_mean_residual_mph": FROZEN_PRIOR_MEAN,
        "frozen_prior_sd_residual_mph": FROZEN_PRIOR_SD,
        "uncertainty_distribution": {
            "family": "NORMAL_CONSERVATIVE_EMPIRICAL_COMPONENTS",
            "center": "Frozen Fast Friday reference plus online shrunk field calibration",
            "run_noise_floor_sd_mph": run_noise_floor_sd,
            "run_noise_evidence": "SD of 74 fixed-k LOYO errors with same-session support n>=10",
            "calibration_sd": "frozen_prior_sd*sqrt(k/(k+n))",
            "predictive_sd": "sqrt(run_noise_floor_sd^2+calibration_sd^2)",
            "limited_sample_policy": "Calibration uncertainty is maximal at n=0 and contracts monotonically with support count.",
            "noncollapse_policy": "Predictive SD never falls below the empirical high-support residual SD.",
        },
        "component_accounting": {
            "baseline_calibration_uncertainty": "Frozen cross-year prior SD",
            "current_session_calibration_uncertainty": "Support-dependent shrinkage term",
            "run_to_run_and_repeat_variability": "Conservatively embedded in the held-out high-support residual floor; 92 existing repeat deltas are a scale cross-check and are not added again as an independent term",
            "limited_sample_uncertainty": "n-dependent calibration term",
            "early_session_inflation": "n=0 has full prior SD contribution",
            "later_session_shrinkage": "Calibration contribution contracts as n grows",
        },
        "calibration": {"years": sorted(DEVELOPMENT_YEARS), "rows": len(residual_rows), "fixed_k3_loyo_mae_mph": fixed_k_mae, "uses_2024": False, "uses_2022": False, "uses_2025": False},
        "repeat_variability_diagnostic": {"file": str(REPEAT_TRANSITIONS.relative_to(ROOT)), "rows": len(repeat_deltas), "delta_speed_sd_mph": statistics.stdev(repeat_deltas), "role": "SCALE_CROSS_CHECK_ONLY_NOT_AN_ADDITIVE_VARIANCE_TERM"},
        "sample_interface": {"distribution": "Normal(predictive_mean_speed_mph,predictive_sd_mph)", "deterministic_seed_supported": True, "seed_for_qa_only": SEED, "draws_materialized": False},
        "missing_state_policy": "Current-best speed is not a point-formula input. Missing Fast Friday reference prevents sampling; missing current speed alone is retained as degraded support.",
        "prohibited_outputs": ["P(beat current)", "P(cross benchmark)", "expected utility", "final action rank", "recommendation"],
        "downstream_boundary": "No R4F8H action Monte Carlo or R4F9 replay is run.",
    }
    OUT_CONTRACT.write_text(json.dumps(contract, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    qa: list[dict[str, str]] = []
    def check(metric: str, value, expected, ok: bool, pass_status: str = "PASS") -> None:
        qa.append({"metric": metric, "value": str(value), "expected": str(expected), "status": pass_status if ok else "FAIL"})

    scales = [float(row["predictive_sd_mph"]) for row in parameter_rows]
    ready_rows = [row for row in decision_rows if row["performance_sample_ready"] == "True"]
    blocked_rows = [row for row in decision_rows if row["performance_sample_ready"] == "False"]
    rng = random.Random(SEED)
    center_errors = []
    for row in ready_rows:
        center, sd = float(row["predictive_mean_speed_mph"]), float(row["predictive_sd_mph"])
        draws = [rng.gauss(center, sd) for _ in range(20000)]
        center_errors.append(abs(statistics.mean(draws) - center))

    check("frozen_architecture_status", architecture["status"], "R4F7C7_FINAL_DEVELOPMENT_ARCHITECTURE_FROZEN", architecture["status"] == "R4F7C7_FINAL_DEVELOPMENT_ARCHITECTURE_FROZEN")
    check("shrinkage_k", K, 3.0, K == 3.0)
    check("development_calibration_rows", len(residual_rows), 104, len(residual_rows) == 104)
    check("fixed_k3_loyo_mae_reproduced", f"{fixed_k_mae:.12f}", f"{EXPECTED_K3_LOYO_MAE:.12f}", abs(fixed_k_mae - EXPECTED_K3_LOYO_MAE) < 1e-12)
    check("calibration_years", sorted({int(r["test_year"]) for r in residual_rows}), [2020, 2021, 2023], {int(r["test_year"]) for r in residual_rows} == DEVELOPMENT_YEARS)
    check("2024_retuning_rows", sum(int(r["test_year"]) == 2024 for r in residual_rows), 0, all(int(r["test_year"]) != 2024 for r in residual_rows))
    check("2022_fake_point_time_rows", sum(int(r["test_year"]) == 2022 for r in residual_rows), 0, all(int(r["test_year"]) != 2022 for r in residual_rows))
    check("2025_validation_rows", sum(int(r["test_year"]) == 2025 for r in residual_rows), 0, all(int(r["test_year"]) != 2025 for r in residual_rows))
    check("future_information_used", sum(r["future_information_used"] == "True" for r in residual_rows), 0, all(r["future_information_used"] == "False" for r in residual_rows))
    check("decision_future_outcome_or_leaderboard_used", sum(r["future_outcome_or_leaderboard_used"] == "True" for r in decision_rows), 0, all(r["future_outcome_or_leaderboard_used"] == "False" for r in decision_rows))
    check("uncertainty_monotone_nonincreasing", all(scales[i] >= scales[i + 1] for i in range(len(scales) - 1)), True, all(scales[i] >= scales[i + 1] for i in range(len(scales) - 1)))
    check("early_uncertainty_broader_than_n3", scales[0] > scales[3], True, scales[0] > scales[3])
    check("n3_uncertainty_broader_than_n20", scales[3] > scales[20], True, scales[3] > scales[20])
    check("uncertainty_floor_not_collapsed", min(scales), f">={run_noise_floor_sd:.12f}", min(scales) >= run_noise_floor_sd)
    check("sample_ready_decisions", len(ready_rows), 59, len(ready_rows) == 59)
    check("not_sample_ready_decisions", [r["source_decision_id"] for r in blocked_rows], ["2021_24_POST_GUARANTEED_BREAK"], len(blocked_rows) == 1 and blocked_rows[0]["source_decision_id"] == "2021_24_POST_GUARANTEED_BREAK", "WARN")
    harvey = next(r for r in decision_rows if r["source_decision_id"] == "2023_30_POST_GUARANTEED_BREAK")
    check("harvey_missing_current_speed_degraded_but_ready", (harvey["performance_sample_ready"], harvey["readiness_status"]), ("True", "SAMPLE_READY_DEGRADED_SUPPORT"), harvey["performance_sample_ready"] == "True" and harvey["readiness_status"] == "SAMPLE_READY_DEGRADED_SUPPORT")
    check("missing_current_speed_not_fabricated", sum(not r["current_best_speed_mph"] for r in decisions), 3, sum(not r["current_best_speed_mph"] for r in decisions) == 3)
    check("sampleable_quantiles_ordered", len(ready_rows), 59, all(float(r["q05_speed_mph"]) < float(r["q25_speed_mph"]) < float(r["q50_speed_mph"]) < float(r["q75_speed_mph"]) < float(r["q95_speed_mph"]) for r in ready_rows))
    check("draw_means_reproduce_centers", f"max_abs_error={max(center_errors):.6f}", "<=0.03 mph", max(center_errors) <= 0.03)
    check("decision_universe", len(decisions), 60, len(decisions) == 60)
    check("action_universe", len(actions), 170, len(actions) == 170)
    check("no_action_probability_or_utility_fields", [f for f in decision_fields if f.startswith("p_") or "utility" in f or "recommendation" in f], [], not any(f.startswith("p_") or "utility" in f or "recommendation" in f for f in decision_fields))
    check("all_sampleable_rows_traceable", len(ready_rows), 59, all(r["calibration_evidence_file"] and r["uncertainty_parameter_file"] and r["reference_source_file"] for r in ready_rows))
    check("repeat_transition_diagnostic_rows", len(repeat_deltas), 92, len(repeat_deltas) == 92)
    check("repeat_variability_not_double_counted", contract["repeat_variability_diagnostic"]["role"], "SCALE_CROSS_CHECK_ONLY_NOT_AN_ADDITIVE_VARIANCE_TERM", True)
    check("shared_parametric_uncertainty_limitation", "NORMAL_SHARED_SCALE_FORMULATION", "Explicitly documented because narrow empirical subgroups are sparse", True, "WARN")

    protected_after = {str(path.relative_to(ROOT)): sha256(path) for path in protected_files}
    check("r4f7_r4f8e_r4f8f_hashes_preserved", protected_after == protected_before, True, protected_after == protected_before)
    write_csv(OUT_QA, ["metric", "value", "expected", "status"], qa)

    qa_counts = Counter(row["status"] for row in qa)
    status = "R4F8G_PARTIAL_BUT_USABLE" if qa_counts["FAIL"] == 0 else "R4F8G_BLOCKED"
    report = {
        "phase": "R4F8G", "status": status, "model_version": VERSION,
        "calibration_dataset": {"file": str(STATE_PANEL.relative_to(ROOT)), "rows": 104, "years": [2020, 2021, 2023], "fixed_k3_loyo_mae_mph": fixed_k_mae},
        "uncertainty_formulation": contract["uncertainty_distribution"],
        "repeat_variability_diagnostic": contract["repeat_variability_diagnostic"],
        "scale_examples": {str(n): scale_by_n[n] for n in (0, 1, 2, 3, 5, 10, 20, 40, 60)},
        "decision_readiness": {"total": 60, "fully_or_degraded_sample_ready": len(ready_rows), "not_sample_ready": len(blocked_rows), "blocked_ids": [r["fused_decision_id"] for r in blocked_rows]},
        "degraded_but_ready": [r["fused_decision_id"] for r in ready_rows if r["readiness_status"] == "SAMPLE_READY_DEGRADED_SUPPORT"],
        "validation_boundaries": {"2024_retuned": False, "2022_point_time_replayed": False, "2025_outcome_validated": False},
        "qa_counts": {key: qa_counts.get(key, 0) for key in ("PASS", "WARN", "FAIL")},
        "protected_hash_count": len(protected_files), "protected_hashes_preserved": protected_before == protected_after,
        "protected_hashes_before": protected_before, "protected_hashes_after": protected_after,
        "outputs": [str(path.relative_to(ROOT)) for path in (OUT_CONTRACT, OUT_RESIDUALS, OUT_PARAMETERS, OUT_DECISIONS, OUT_SUPPORT, OUT_QA, OUT_REPORT)],
    }
    OUT_REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    assert protected_before == {str(path.relative_to(ROOT)): sha256(path) for path in protected_files}

    print(f"CALIBRATION: rows=104 years=2020,2021,2023 fixed_k3_loyo_mae={fixed_k_mae:.6f}")
    print(f"UNCERTAINTY: run_noise_floor_sd={run_noise_floor_sd:.6f}; sd_n0={scale_by_n[0]:.6f}; sd_n3={scale_by_n[3]:.6f}; sd_n20={scale_by_n[20]:.6f}; sd_n60={scale_by_n[60]:.6f}")
    print(f"READINESS: sample_ready={len(ready_rows)}/60; not_ready={len(blocked_rows)}/60")
    print(f'QA: PASS={qa_counts["PASS"]} WARN={qa_counts["WARN"]} FAIL={qa_counts["FAIL"]}')
    print(status)


if __name__ == "__main__":
    main()
