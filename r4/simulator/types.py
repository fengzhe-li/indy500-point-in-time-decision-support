from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Mapping

from .actions import Action


@dataclass(frozen=True)
class QueueEvolution:
    lane1_state: Mapping[str, Any]
    lane2_state: Mapping[str, Any]
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class WaitSample:
    wait_seconds: float
    completed_before_session_end: bool | None
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class FutureEnvironment:
    valid_at: datetime
    values: Mapping[str, float | None]
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RepeatPerformance:
    attempted: bool
    completed: bool | None
    four_lap_speed_mph: float | None
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CompetitorOutcome:
    competitor_id: str
    action: str
    final_speed_mph: float | None
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class InterruptionOutcome:
    occurred: bool
    delay_seconds: float
    prevents_attempt: bool | None
    label: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class LeaderboardSnapshot:
    target_driver_id: str
    target_final_rank: int | None
    target_final_speed_mph: float | None
    entries: tuple[Mapping[str, Any], ...]
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class UtilityEvaluation:
    success_indicator: bool | None
    downside_indicator: bool | None
    utility_value: float | None
    risk_profile: str
    status: str
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TrialRecord:
    action: Action
    trial_index: int
    component_seeds: Mapping[str, int]
    queue_evolution: QueueEvolution
    wait: WaitSample
    future_environment: FutureEnvironment
    interruption: InterruptionOutcome
    repeat_performance: RepeatPerformance
    competitor_outcomes: tuple[CompetitorOutcome, ...]
    final_leaderboard: LeaderboardSnapshot
    utility: UtilityEvaluation

    @property
    def final_rank(self) -> int | None:
        return self.final_leaderboard.target_final_rank

    @property
    def final_speed_mph(self) -> float | None:
        return self.final_leaderboard.target_final_speed_mph

    @property
    def success_indicator(self) -> bool | None:
        return self.utility.success_indicator

    @property
    def downside_indicator(self) -> bool | None:
        return self.utility.downside_indicator

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["action"] = self.action.value
        value["future_environment"]["valid_at"] = self.future_environment.valid_at.isoformat()
        value.update({
            "final_rank": self.final_rank,
            "final_speed_mph": self.final_speed_mph,
            "success_indicator": self.success_indicator,
            "downside_indicator": self.downside_indicator,
        })
        return value


@dataclass(frozen=True)
class SimulationRun:
    master_seed: int
    trials_per_action: int
    records: tuple[TrialRecord, ...]
    configuration_fingerprint: str
