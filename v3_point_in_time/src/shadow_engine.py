"""Step 8 (Phase 1) / Step 5 provenance fix (Phase 2) — orchestrates
forecast selection -> guard -> applicability gate -> FINAL_V2 adapter ->
immutable, append-only shadow prediction record.

PHASE 2 PROVENANCE FIX: forecast selection now happens exactly ONCE, in
`select_and_build_snapshot`, before the DecisionSnapshot is built. The
selected forecast IDs are written into the snapshot's
`selected_forecast_ids` (and folded into its `input_hash`) at that same
moment. `run_single_horizon` no longer re-selects from the store; it
requires the caller to pass the exact ForecastVintage object that was
already selected, and HARD-FAILS (raises ForecastProvenanceMismatch) if
that vintage's forecast_id is not present in
`snapshot.selected_forecast_ids`. A mismatch between "the forecast the
snapshot declares it used" and "the forecast actually passed to
inference" is therefore not silently possible -- it is a bug that stops
execution, not a discrepancy that could pass unnoticed into a
prediction record.

This is a structural fix to V3's own code, not a change to any frozen
FINAL_V2 file.

No queue-time prediction and no retain/withdraw recommendation is ever
produced anywhere in this module.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional

import applicability_gate
import final_v2_adapter
from schemas import DecisionSnapshot, ForecastVintage, ShadowPrediction
from hashing import sha256_obj
from point_in_time_guard import POINT_IN_TIME_VIOLATION, check_point_in_time
from decision_snapshot import build_decision_snapshot
from forecast_vintage_store import ForecastVintageStore


class ForecastProvenanceMismatch(Exception):
    """Raised when the forecast vintage passed to inference is not the
    one recorded in the snapshot's own provenance. This must never be
    caught and silently worked around -- it means a caller bypassed
    select_and_build_snapshot's single selection point."""


class ShadowEngineResult:
    def __init__(self, status: str, prediction: Optional[ShadowPrediction], reasons: tuple, notes: tuple = ()):
        self.status = status  # "OK" | "POINT_IN_TIME_VIOLATION" | applicability status
        self.prediction = prediction
        self.reasons = reasons
        self.notes = notes


def target_time_for(decision_time: str, horizon_min: int) -> str:
    dt = datetime.fromisoformat(decision_time.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return (dt + timedelta(minutes=horizon_min)).astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def select_forecasts_for_horizons(
    store: ForecastVintageStore,
    decision_time: str,
    horizons_min: List[int],
) -> Dict[int, Optional[dict]]:
    """The single point where forecast vintages are chosen for a
    decision. Returns {horizon: selection_or_None}, where selection is
    {"vintage": ForecastVintage, "valid_time_error_minutes": float}.
    """
    return {
        h: store.select(decision_time, target_time_for(decision_time, h))
        for h in horizons_min
    }


def select_and_build_snapshot(
    store: ForecastVintageStore,
    snapshot_id: str,
    event_year: int,
    car_or_entry_id: str,
    decision_time: str,
    current_track_temp_c: float,
    current_ambient_temp_c: float,
    current_track_temp_known_at: str,
    current_ambient_temp_known_at: str,
    horizons_min: List[int],
    current_official_speed: Optional[float] = None,
    current_official_speed_known_at: Optional[str] = None,
    evaluation_mode: str = "RETROSPECTIVE_POINT_IN_TIME_INPUTS",
):
    """Phase 2 single source of truth: select forecasts for every
    requested horizon FIRST, then build the snapshot recording exactly
    those forecast IDs. Returns (snapshot_or_none, guard_result,
    selections). `selections` is what `run_single_horizon` must be
    given -- it is never re-derived independently downstream.
    """
    selections = select_forecasts_for_horizons(store, decision_time, horizons_min)

    forecast_ids = []
    issue_times = []
    for h in horizons_min:
        sel = selections[h]
        if sel is not None:
            forecast_ids.append(sel["vintage"].forecast_id)
            issue_times.append(sel["vintage"].issue_time)

    snapshot, guard_result = build_decision_snapshot(
        snapshot_id=snapshot_id,
        event_year=event_year,
        car_or_entry_id=car_or_entry_id,
        decision_time=decision_time,
        current_track_temp_c=current_track_temp_c,
        current_ambient_temp_c=current_ambient_temp_c,
        current_track_temp_known_at=current_track_temp_known_at,
        current_ambient_temp_known_at=current_ambient_temp_known_at,
        current_official_speed=current_official_speed,
        current_official_speed_known_at=current_official_speed_known_at,
        selected_forecast_ids=tuple(forecast_ids),
        forecast_issue_times=tuple(issue_times),
        evaluation_mode=evaluation_mode,
    )
    return snapshot, guard_result, selections


def run_single_horizon(
    snapshot: DecisionSnapshot,
    horizon_min: int,
    vintage: ForecastVintage,
    latitude_deg: float,
    longitude_deg: float,
    random_seed: int,
    n_mc: int,
    output_dir: Path,
    valid_time_error_minutes: Optional[float] = None,
) -> ShadowEngineResult:
    """Evaluate exactly one supported horizon for an already-guard-passed
    snapshot, using the ALREADY-SELECTED forecast vintage for that
    horizon (from select_and_build_snapshot). This function does not
    select a forecast itself -- selection has exactly one source of
    truth, upstream of snapshot construction.
    """
    if vintage.forecast_id not in snapshot.selected_forecast_ids:
        raise ForecastProvenanceMismatch(
            f"vintage {vintage.forecast_id!r} passed to run_single_horizon for horizon "
            f"{horizon_min} is not among snapshot.selected_forecast_ids "
            f"{snapshot.selected_forecast_ids!r}. Selection must happen exactly once, "
            "in select_and_build_snapshot."
        )

    target_time = target_time_for(snapshot.decision_time, horizon_min)

    # Defense in depth: re-verify the fundamental invariant at the point
    # of use, even though the forecast was already selected upstream
    # under the same rule.
    guard = check_point_in_time(
        decision_time=snapshot.decision_time,
        current_official_speed_known_at=snapshot.current_official_speed_known_at,
        current_track_temp_known_at=snapshot.current_track_temp_known_at,
        current_ambient_temp_known_at=snapshot.current_ambient_temp_known_at,
        forecast_issue_times=[vintage.issue_time],
    )
    if not guard.passed:
        return ShadowEngineResult(status=POINT_IN_TIME_VIOLATION, prediction=None, reasons=guard.reasons)

    gate = applicability_gate.evaluate(
        horizon_min=horizon_min,
        current_track_temp_c=snapshot.current_track_temp_c,
        current_ambient_temp_c=snapshot.current_ambient_temp_c,
        forecast_future_ambient_temp_c=vintage.ambient_temp_c,
    )
    if gate.status in ("OUT_OF_SUPPORT", "INPUT_INSUFFICIENT"):
        return ShadowEngineResult(status=gate.status, prediction=None, reasons=gate.reasons, notes=gate.notes)

    output = final_v2_adapter.infer(
        current_track_temp_c=snapshot.current_track_temp_c,
        current_ambient_temp_c=snapshot.current_ambient_temp_c,
        forecast_future_ambient_temp_c=vintage.ambient_temp_c,
        decision_time=snapshot.decision_time,
        target_time=target_time,
        horizon_min=horizon_min,
        latitude_deg=latitude_deg,
        longitude_deg=longitude_deg,
        random_seed=random_seed,
        n_mc=n_mc,
    )

    prediction_id = f"{snapshot.snapshot_id}:h{horizon_min}"
    created_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    m_hash = final_v2_adapter.model_hash()

    prediction_payload = {
        "prediction_id": prediction_id,
        "snapshot_id": snapshot.snapshot_id,
        "decision_time": snapshot.decision_time,
        "event_year": snapshot.event_year,
        "car_or_entry_id": snapshot.car_or_entry_id,
        "forecast_vintage_ids": [vintage.forecast_id],
        "model_version": final_v2_adapter.MODEL_VERSION,
        "model_hash": m_hash,
        "horizon_minutes": horizon_min,
        "expected_delta_v": output.expected_delta_v,
        "median_delta_v": output.median_delta_v,
        "p_improve": output.p_improve,
        "pi80_low": output.pi80_low,
        "pi80_high": output.pi80_high,
        "pi90_low": output.pi90_low,
        "pi90_high": output.pi90_high,
        "applicability_status": gate.status,
        "input_hash": snapshot.input_hash,
    }
    prediction_hash = sha256_obj(prediction_payload)

    prediction = ShadowPrediction(
        prediction_id=prediction_id,
        snapshot_id=snapshot.snapshot_id,
        decision_time=snapshot.decision_time,
        event_year=snapshot.event_year,
        car_or_entry_id=snapshot.car_or_entry_id,
        forecast_vintage_ids=(vintage.forecast_id,),
        model_version=final_v2_adapter.MODEL_VERSION,
        model_hash=m_hash,
        horizon_minutes=horizon_min,
        expected_delta_v=output.expected_delta_v,
        median_delta_v=output.median_delta_v,
        p_improve=output.p_improve,
        pi80_low=output.pi80_low,
        pi80_high=output.pi80_high,
        pi90_low=output.pi90_low,
        pi90_high=output.pi90_high,
        applicability_status=gate.status,
        input_hash=snapshot.input_hash,
        prediction_hash=prediction_hash,
        created_at=created_at,
    )

    _write_append_only(output_dir, prediction)

    return ShadowEngineResult(status="OK", prediction=prediction, reasons=(), notes=gate.notes)


def _write_append_only(output_dir: Path, prediction: ShadowPrediction) -> Path:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    file_path = output_dir / f"{prediction.prediction_id.replace(':', '_')}.json"
    if file_path.exists():
        raise FileExistsError(
            f"Refusing to overwrite existing prediction record: {file_path}. "
            "Shadow predictions are append-only."
        )
    file_path.write_text(json.dumps(prediction.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
    return file_path


def run_all_supported_horizons(
    snapshot: DecisionSnapshot,
    selections: Dict[int, Optional[dict]],
    latitude_deg: float,
    longitude_deg: float,
    random_seed: int,
    n_mc: int,
    output_dir: Path,
    horizons_min: List[int] = (15, 30, 60, 90, 120),
) -> Dict[int, ShadowEngineResult]:
    """Run every horizon using the SAME `selections` mapping produced by
    select_and_build_snapshot for this snapshot -- never re-selecting."""
    results = {}
    for h in horizons_min:
        sel = selections.get(h)
        if sel is None:
            results[h] = ShadowEngineResult(
                status=POINT_IN_TIME_VIOLATION,
                prediction=None,
                reasons=(f"NO_FORECAST_VINTAGE_AVAILABLE_AT_OR_BEFORE_DECISION_TIME_FOR_HORIZON_{h}",),
            )
            continue
        results[h] = run_single_horizon(
            snapshot, h, sel["vintage"], latitude_deg, longitude_deg, random_seed, n_mc, output_dir,
            valid_time_error_minutes=sel["valid_time_error_minutes"],
        )
    return results
