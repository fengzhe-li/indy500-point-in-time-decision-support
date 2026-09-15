from __future__ import annotations

from random import Random
from typing import Protocol

from r4.simulator.actions import Action
from r4.simulator.errors import NotConfiguredError
from r4.simulator.types import FutureEnvironment, InterruptionOutcome, QueueEvolution, WaitSample
from r4.state import PitWallState


class FutureEnvironmentModel(Protocol):
    def sample_future_environment(
        self, state: PitWallState, action: Action, queue: QueueEvolution,
        wait: WaitSample, interruption: InterruptionOutcome, rng: Random,
    ) -> FutureEnvironment: ...


class NotConfiguredFutureEnvironmentModel:
    def sample_future_environment(self, state, action, queue, wait, interruption, rng):
        raise NotConfiguredError("future environment model")
