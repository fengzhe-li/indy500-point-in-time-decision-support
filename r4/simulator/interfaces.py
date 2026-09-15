"""Protocols for components that act after queue/environment/performance sampling."""

from __future__ import annotations

from random import Random
from typing import Protocol, Sequence

from r4.state import PitWallState

from .actions import Action
from .errors import NotConfiguredError
from .types import (
    CompetitorOutcome, FutureEnvironment, InterruptionOutcome,
    LeaderboardSnapshot, QueueEvolution, RepeatPerformance, UtilityEvaluation,
    WaitSample,
)


class InterruptionModel(Protocol):
    def sample_interruption(self, state: PitWallState, action: Action, wait: WaitSample, rng: Random) -> InterruptionOutcome: ...


class LeaderboardUpdateModel(Protocol):
    def update_leaderboard(
        self, state: PitWallState, action: Action, performance: RepeatPerformance,
        competitors: Sequence[CompetitorOutcome], interruption: InterruptionOutcome,
        rng: Random,
    ) -> LeaderboardSnapshot: ...


class UtilityRiskEvaluator(Protocol):
    def evaluate(self, state: PitWallState, action: Action, leaderboard: LeaderboardSnapshot, rng: Random) -> UtilityEvaluation: ...


class NotConfiguredInterruptionModel:
    def sample_interruption(self, state, action, wait, rng):
        raise NotConfiguredError("interruption/random-shock model")


class NotConfiguredLeaderboardUpdateModel:
    def update_leaderboard(self, state, action, performance, competitors, interruption, rng):
        raise NotConfiguredError("leaderboard update model")


class NotConfiguredUtilityRiskEvaluator:
    def evaluate(self, state, action, leaderboard, rng):
        raise NotConfiguredError("utility/risk-profile evaluator")
