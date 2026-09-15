"""Phase 4 — system status and validation-summary queries.

Reads authoritative QA/freeze artifacts rather than hard-coding mutable
results, so that re-running the Phase 1-3 verification scripts (which a
maintainer might do at any time) is reflected here without an
application code change.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Optional

import yaml

import replay_service

V3_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = V3_ROOT / "config" / "v3_config.yaml"
V2_IMMUTABILITY_REPORT = V3_ROOT / "output" / "qa" / "v2_immutability_report.txt"
BEHAVIOURAL_REGRESSION_REPORT = V3_ROOT / "output" / "qa" / "v3_v2_behavioural_regression_report.md"
PHASE3_FREEZE_MANIFEST = V3_ROOT / "output" / "phase3_freeze" / "phase3_freeze_manifest.json"


def _read_text(path: Path) -> Optional[str]:
    return path.read_text(encoding="utf-8") if path.exists() else None


def _pass_fail(text: Optional[str], pattern: str) -> str:
    if text is None:
        return "UNKNOWN"
    return "PASS" if re.search(pattern, text) else "FAIL"


def system_status() -> dict:
    config = yaml.safe_load(_read_text(CONFIG_PATH) or "{}")
    v2_report = _read_text(V2_IMMUTABILITY_REPORT)
    regression_report = _read_text(BEHAVIOURAL_REGRESSION_REPORT)
    phase3_manifest = json.loads(_read_text(PHASE3_FREEZE_MANIFEST) or "{}")

    return {
        "system": "INDY 500 V3",
        "scientific_core": config.get("frozen_scientific_version", "FINAL_V2"),
        "phase": "PHASE_4_APPLICATION",
        "operating_mode": "HISTORICAL_SHADOW_RESEARCH_MODE",
        "supported_horizons_min": config.get("supported_horizons_min", [15, 30, 60, 90, 120]),
        "max_supported_horizon_min": config.get("max_supported_horizon_min", 120),
        "performance_model_status": "FROZEN",
        "future_track_model_status": "FROZEN",
        "queue_model": "NOT_MODELLED",
        "opportunity_time_model": "NOT_MODELLED",
        "strategy_recommendation": "NOT_ISSUED",
        "historical_scoring_validation": "NOT_ESTABLISHED",
        "v2_integrity": _pass_fail(v2_report, r"OVERALL RESULT:\s*PASS"),
        "behavioural_regression": _pass_fail(regression_report, r"Overall result:\s*PASS"),
        "phase3_freeze_status": phase3_manifest.get("status", "UNKNOWN"),
    }


def validation_summary() -> dict:
    case_rows = replay_service.load_case_summary()
    abstention_rows = replay_service.load_abstention_summary()
    phase3_manifest = json.loads(_read_text(PHASE3_FREEZE_MANIFEST) or "{}")

    category_counts = {}
    for r in case_rows:
        category_counts[r["category"]] = category_counts.get(r["category"], 0) + 1

    reason_counts = {
        row["category"].split("REASON:", 1)[1]: int(row["count"])
        for row in abstention_rows
        if row["category"].startswith("REASON:")
    }

    return {
        "total_transitions_considered": len(case_rows),
        "candidate_cases_with_replay_timeline": sum(1 for r in case_rows if r["category"] != "ABSTAINED_INSUFFICIENT_TIMESTAMP"),
        "conditional_inference_supported": category_counts.get("FULL_SHADOW_INFERENCE_SUPPORTED", 0)
            + category_counts.get("CONDITIONAL_OUTLOOK_SUPPORTED_BUT_HISTORICAL_SCORING_UNSUPPORTED", 0),
        "historical_scoring_formally_supported": category_counts.get("FULL_SHADOW_INFERENCE_SUPPORTED", 0),
        "illustrative_only": category_counts.get("ILLUSTRATIVE_ONLY", 0),
        "abstained_insufficient_timestamp": category_counts.get("ABSTAINED_INSUFFICIENT_TIMESTAMP", 0),
        "abstained_out_of_support": category_counts.get("ABSTAINED_OUT_OF_SUPPORT", 0),
        "abstained_forecast_unavailable": category_counts.get("ABSTAINED_FORECAST_UNAVAILABLE", 0),
        "category_counts": category_counts,
        "abstention_reason_counts": reason_counts,
        "phase3_freeze_status": phase3_manifest.get("status", "UNKNOWN"),
        "note": (
            "Illustrative case (2021 car 60) is retained as a diagnostic and "
            "excluded from historical_scoring_formally_supported and from any "
            "aggregate validation metric."
        ),
    }
