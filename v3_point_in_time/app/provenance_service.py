"""Phase 4 — provenance and explanation lookups for a single prediction.

Everything here is assembled from fields already present in the frozen
Phase 3 replay events (replay_service.load_events()); nothing is
recomputed. `find_prediction_event` is the only place a prediction_id is
resolved, so provenance and explanation views are guaranteed to describe
the same underlying record.
"""
from __future__ import annotations

from typing import Optional

import replay_service
from replay_service import NotFoundError


def get_prediction(prediction_id: str) -> dict:
    e = replay_service.find_prediction_event(prediction_id)
    scoring = _scoring_for_prediction(prediction_id)
    return {
        "prediction_id": prediction_id,
        "case_id": _case_id_from_snapshot(e["decision_snapshot_id"]),
        "decision_snapshot_id": e["decision_snapshot_id"],
        "information_cutoff": e["information_cutoff"],
        "horizon_minutes": e["payload"]["horizon_minutes"],
        "inference_support": e["evaluation_status"],
        "historical_scoring_support": scoring["status"] if scoring else "NOT_ATTEMPTED",
        "outlook": {
            "expected_delta_v": e["payload"]["expected_delta_v"],
            "median_delta_v": e["payload"]["median_delta_v"],
            "p_improve": e["payload"]["p_improve"],
            "pi80_low": e["payload"]["pi80_low"],
            "pi80_high": e["payload"]["pi80_high"],
            "pi90_low": e["payload"]["pi90_low"],
            "pi90_high": e["payload"]["pi90_high"],
        },
        "queue_time_prediction": e["payload"]["queue_time_prediction"],
        "retain_withdraw_recommendation": e["payload"]["retain_withdraw_recommendation"],
    }


def get_provenance(prediction_id: str) -> dict:
    e = replay_service.find_prediction_event(prediction_id)
    forecast_id = e["provenance_ids"][0] if e["provenance_ids"] else None
    model_hash = e["provenance_ids"][1] if len(e["provenance_ids"]) > 1 else None
    forecast_event = replay_service.find_forecast_event_for(
        e["event_year"], e["car_or_entry_id"], e["payload"]["horizon_minutes"]
    )
    scoring = _scoring_for_prediction(prediction_id)
    return {
        "prediction_id": prediction_id,
        "decision_snapshot_id": e["decision_snapshot_id"],
        "information_cutoff": e["information_cutoff"],
        "forecast_vintage_id": forecast_id,
        "forecast_issue_time": forecast_event["payload"]["forecast_issue_time"] if forecast_event else None,
        "forecast_valid_time": forecast_event["payload"]["forecast_valid_time"] if forecast_event else None,
        "forecast_target_time_error_minutes": forecast_event["payload"]["valid_time_error_minutes"] if forecast_event else None,
        "forecast_ambient_temp_c": forecast_event["payload"]["forecast_ambient_temp_c"] if forecast_event else None,
        "final_v2_model_hash": model_hash,
        "input_hash": e["input_hash"],
        "prediction_hash_note": "Derived deterministically from decision_snapshot_id + horizon + frozen model hash; see shadow_engine.py.",
        "scientific_support": e["evaluation_status"],
        "historical_scoring_support": scoring["status"] if scoring else "NOT_ATTEMPTED",
    }


def get_explanation(prediction_id: str) -> dict:
    e = replay_service.find_prediction_event(prediction_id)
    explanation = e["payload"].get("explanation", {})
    return {
        "prediction_id": prediction_id,
        "current_track_to_ambient_thermal_gap_c": explanation.get("current_track_to_ambient_thermal_gap_c"),
        "forecast_ambient_trajectory_c": explanation.get("forecast_ambient_trajectory_c"),
        "predicted_future_track_temperature_change_c": explanation.get("predicted_future_track_temperature_change_c"),
        "solar_elevation_mean_deg": explanation.get("solar_elevation_mean_deg"),
        "note": explanation.get("note"),
        "uncertainty_source_reference": {
            **explanation.get("uncertainty_source_reference", {}),
            "diagnostic_scope": "GLOBAL_HORIZON_LEVEL_DIAGNOSTIC",
            "diagnostic_kind": "uncertainty-source ablation / sensitivity diagnostic (not a formal variance decomposition, not case-specific)",
        },
    }


def _scoring_for_prediction(prediction_id: str) -> Optional[dict]:
    case_id = _case_id_from_prediction_id(prediction_id)
    if case_id is None:
        return None
    try:
        return replay_service.get_case_scoring(case_id)
    except NotFoundError:
        return None


def _case_id_from_snapshot(decision_snapshot_id: Optional[str]) -> Optional[str]:
    if not decision_snapshot_id or ":" not in decision_snapshot_id:
        return None
    return decision_snapshot_id.split(":", 1)[1]


def _case_id_from_prediction_id(prediction_id: str) -> Optional[str]:
    # prediction_id format: "phase3:<case_id>:h<horizon>"
    parts = prediction_id.split(":")
    if len(parts) != 3 or parts[0] != "phase3":
        return None
    return parts[1]
