from __future__ import annotations

from random import Random
from typing import Protocol

from r4.simulator.actions import Action
from r4.simulator.errors import NotConfiguredError
from r4.simulator.types import FutureEnvironment, InterruptionOutcome, RepeatPerformance, WaitSample
from r4.state import PitWallState


class RepeatPerformanceModel(Protocol):
    def sample_repeat_performance(
        self, state: PitWallState, action: Action, wait: WaitSample,
        environment: FutureEnvironment, interruption: InterruptionOutcome, rng: Random,
    ) -> RepeatPerformance: ...


class NotConfiguredRepeatPerformanceModel:
    def sample_repeat_performance(self, state, action, wait, environment, interruption, rng):
        raise NotConfiguredError("repeat performance model")
