"""Step 5 — build an immutable decision snapshot.

A DecisionSnapshot is constructed once, validated by the point-in-time
guard, hashed, and never mutated afterward. Building one does not by
itself run FINAL_V2 inference -- it only fixes the inputs that a later
inference call may use.
"""
from __future__ import annotations

from typing import Optional, Sequence

from schemas import DecisionSnapshot
from hashing import sha256_obj
from point_in_time_guard import check_point_in_time
from forecast_vintage_store import ForecastVintageStore


def build_decision_snapshot(
    snapshot_id: str,
    event_year: int,
    car_or_entry_id: str,
    decision_time: str,
    current_track_temp_c: float,
    current_ambient_temp_c: float,
    current_track_temp_known_at: str,
    current_ambient_temp_known_at: str,
    current_official_speed: Optional[float] = None,
    current_official_speed_known_at: Optional[str] = None,
    selected_forecast_ids: Sequence[str] = (),
    forecast_issue_times: Sequence[str] = (),
    evaluation_mode: str = "RETROSPECTIVE_POINT_IN_TIME_INPUTS",
    information_cutoff: Optional[str] = None,
):
    """Validate inputs against the point-in-time guard and, if they
    pass, return a frozen DecisionSnapshot with its input_hash set.

    Returns (snapshot_or_none, guard_result). If the guard fails,
    snapshot_or_none is None and the caller must treat this as
    POINT_IN_TIME_VIOLATION -- no snapshot is created from leaking
    inputs, so a leaking snapshot can never exist to be hashed or
    stored.
    """
    guard_result = check_point_in_time(
        decision_time=decision_time,
        current_official_speed_known_at=current_official_speed_known_at,
        current_track_temp_known_at=current_track_temp_known_at,
        current_ambient_temp_known_at=current_ambient_temp_known_at,
        forecast_issue_times=forecast_issue_times,
    )
    if not guard_result.passed:
        return None, guard_result

    cutoff = information_cutoff or decision_time

    input_payload = {
        "snapshot_id": snapshot_id,
        "event_year": event_year,
        "car_or_entry_id": car_or_entry_id,
        "decision_time": decision_time,
        "current_official_speed": current_official_speed,
        "current_track_temp_c": current_track_temp_c,
        "current_ambient_temp_c": current_ambient_temp_c,
        "selected_forecast_ids": list(selected_forecast_ids),
        "information_cutoff": cutoff,
        "evaluation_mode": evaluation_mode,
    }
    input_hash = sha256_obj(input_payload)

    snapshot = DecisionSnapshot(
        snapshot_id=snapshot_id,
        event_year=event_year,
        car_or_entry_id=car_or_entry_id,
        decision_time=decision_time,
        current_official_speed=current_official_speed,
        current_track_temp_c=current_track_temp_c,
        current_ambient_temp_c=current_ambient_temp_c,
        selected_forecast_ids=tuple(selected_forecast_ids),
        information_cutoff=cutoff,
        evaluation_mode=evaluation_mode,
        current_official_speed_known_at=current_official_speed_known_at,
        current_track_temp_known_at=current_track_temp_known_at,
        current_ambient_temp_known_at=current_ambient_temp_known_at,
        input_hash=input_hash,
    )
    return snapshot, guard_result
