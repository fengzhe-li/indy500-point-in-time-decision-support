from __future__ import annotations

from random import Random
from typing import Protocol, Sequence

from r4.simulator.actions import Action
from r4.simulator.errors import NotConfiguredError
from r4.simulator.types import CompetitorOutcome, FutureEnvironment, QueueEvolution, WaitSample
from r4.state import PitWallState


class CompetitorActionModel(Protocol):
    def sample_competitor_outcomes(
        self, state: PitWallState, action: Action, queue: QueueEvolution,
        wait: WaitSample, environment: FutureEnvironment, rng: Random,
    ) -> Sequence[CompetitorOutcome]: ...


class NotConfiguredCompetitorActionModel:
    def sample_competitor_outcomes(self, state, action, queue, wait, environment, rng):
        raise NotConfiguredError("competitor action model")
