"""Canonical decision-time state types.

Unknown observations remain ``None`` or use an explicit UNKNOWN observation
status.  This module does not fill missing state from elapsed time or results.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Mapping


@dataclass(frozen=True)
class QueueObservation:
    observation_status: str
    observed_at: datetime | None = None
    queue_length: int | None = None
    ordered_entry_ids: tuple[str, ...] | None = None
    evidence_reference: str | None = None

    def __post_init__(self) -> None:
        allowed = {"OBSERVED", "PARTIAL", "UNKNOWN", "NOT_CONFIGURED"}
        if self.observation_status not in allowed:
            raise ValueError(f"queue observation_status must be one of {sorted(allowed)}")
        if self.queue_length is not None and self.queue_length < 0:
            raise ValueError("queue_length cannot be negative")


@dataclass(frozen=True)
class PitWallState:
    decision_timestamp: datetime
    session_remaining_seconds: float
    driver_id: str
    driver_name: str
    car_number: str
    current_valid_speed_mph: float | None
    current_rank: int | None
    cutoff_rank: int | None
    cutoff_speed_mph: float | None
    attempt_count: int
    action_eligibility: Mapping[str, bool]
    lane1_queue_state: QueueObservation
    lane2_queue_state: QueueObservation
    ambient_temperature_c: float | None
    track_temperature_c: float | None
    relative_humidity_percent: float | None
    pressure_hpa: float | None
    wind_speed_mps: float | None
    wind_direction_degrees: float | None
    gust_speed_mps: float | None
    cloud_cover_percent: float | None
    shortwave_radiation_w_m2: float | None
    solar_elevation_degrees: float | None
    solar_azimuth_degrees: float | None

    def __post_init__(self) -> None:
        if self.decision_timestamp.tzinfo is None or self.decision_timestamp.utcoffset() is None:
            raise ValueError("decision_timestamp must be timezone-aware")
        if self.session_remaining_seconds < 0:
            raise ValueError("session_remaining_seconds cannot be negative")
        if self.attempt_count < 0:
            raise ValueError("attempt_count cannot be negative")
        if not self.driver_id or not self.driver_name or not self.car_number:
            raise ValueError("driver_id, driver_name, and car_number are required")
        required_actions = {
            "STOP_RETAIN_CURRENT_RESULT",
            "REPEAT_LANE2_RETAIN_CURRENT_RESULT",
            "REPEAT_LANE1_WITHDRAW_CURRENT_RESULT",
        }
        if set(self.action_eligibility) != required_actions:
            raise ValueError("action_eligibility must contain exactly the three supported actions")

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["decision_timestamp"] = self.decision_timestamp.astimezone(timezone.utc).isoformat()
        for key in ("lane1_queue_state", "lane2_queue_state"):
            observed_at = value[key]["observed_at"]
            if observed_at is not None:
                value[key]["observed_at"] = observed_at.astimezone(timezone.utc).isoformat()
        return value
