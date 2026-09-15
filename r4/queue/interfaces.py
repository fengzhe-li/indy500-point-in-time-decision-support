from __future__ import annotations

from random import Random
from typing import Protocol

from r4.simulator.actions import Action
from r4.simulator.errors import NotConfiguredError
from r4.simulator.types import QueueEvolution, WaitSample
from r4.state import PitWallState


class QueueWaitModel(Protocol):
    def sample_queue_evolution(self, state: PitWallState, action: Action, rng: Random) -> QueueEvolution: ...
    def sample_wait_time(self, state: PitWallState, action: Action, queue: QueueEvolution, rng: Random) -> WaitSample: ...


class NotConfiguredQueueWaitModel:
    def sample_queue_evolution(self, state, action, rng):
        raise NotConfiguredError("queue wait model")

    def sample_wait_time(self, state, action, queue, rng):
        raise NotConfiguredError("queue wait model")
