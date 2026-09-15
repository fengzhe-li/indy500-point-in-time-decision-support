"""Step 4 — hard point-in-time leakage guard.

Every input used for inference must have a known-at / issue timestamp
that is not later than the decision timestamp. If any input violates
this, the guard fails CLOSED: callers must not issue a production-style
prediction. This module never produces a prediction itself; it only
validates.

KNOWN LIMITATION (documented, not silently assumed away): forecast
`issue_time` here is the nominal HRRR cycle time. Real-world forecast
publication latency after the nominal cycle time is not quantified
anywhere in this project (see existing_system_inventory.md, section 5).
The guard therefore proves "not issued after decision_time" against the
nominal cycle time, which is the only timestamp that exists -- it does
not additionally prove the forecast bytes were actually downloadable by
decision_time.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable, Optional

from schemas import GuardResult, POINT_IN_TIME_VIOLATION


def _parse(ts: str) -> datetime:
    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def check_point_in_time(
    decision_time: str,
    current_official_speed_known_at: Optional[str],
    current_track_temp_known_at: str,
    current_ambient_temp_known_at: str,
    forecast_issue_times: Iterable[str],
) -> GuardResult:
    """Validate that no input used for a decision is known only in the future.

    Returns a GuardResult. `passed=False` means the caller MUST return
    POINT_IN_TIME_VIOLATION and must not run FINAL_V2 inference for this
    snapshot.
    """
    reasons = []
    t_decision = _parse(decision_time)

    def _later(label: str, ts: Optional[str]):
        if ts is None:
            return
        if _parse(ts) > t_decision:
            reasons.append(f"{label}_KNOWN_AT_AFTER_DECISION_TIME")

    _later("CURRENT_OFFICIAL_SPEED", current_official_speed_known_at)
    _later("CURRENT_TRACK_TEMP", current_track_temp_known_at)
    _later("CURRENT_AMBIENT_TEMP", current_ambient_temp_known_at)

    for i, issue_time in enumerate(forecast_issue_times):
        if _parse(issue_time) > t_decision:
            reasons.append(f"FORECAST_{i}_ISSUE_TIME_AFTER_DECISION_TIME")

    return GuardResult(passed=(len(reasons) == 0), reasons=tuple(reasons))


def enforce(guard_result: GuardResult) -> None:
    """Raise if the guard failed. Fail-closed helper for call sites that
    should abort rather than continue with a degraded result."""
    if not guard_result.passed:
        raise PointInTimeViolation(guard_result.reasons)


class PointInTimeViolation(Exception):
    """Raised when a future observation would leak into a decision snapshot."""

    def __init__(self, reasons: tuple):
        self.reasons = reasons
        self.code = POINT_IN_TIME_VIOLATION
        super().__init__(f"{POINT_IN_TIME_VIOLATION}: {reasons}")
