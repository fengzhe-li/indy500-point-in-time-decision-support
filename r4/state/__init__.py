from .models import PitWallState, QueueObservation
from .scenario import Availability, LoadedScenario, ObservablePitWallState, ObservableScenario, ProvenancedValue, ScenarioValidationError, to_pit_wall_state
from .targets import (
    AdvancementBenchmark, CurrentResultReference, DecisionTarget, DecisionTargetType,
    FutureOutputSemantic,
)

__all__ = [
    "AdvancementBenchmark", "Availability", "CurrentResultReference", "DecisionTarget",
    "DecisionTargetType", "FutureOutputSemantic", "LoadedScenario", "ObservablePitWallState", "ObservableScenario",
    "PitWallState", "ProvenancedValue", "QueueObservation", "R3C1_STATE_ASSET", "ScenarioLoader",
    "ScenarioValidationError", "to_pit_wall_state",
]


def __getattr__(name):
    if name in {"R3C1_STATE_ASSET", "ScenarioLoader"}:
        from .loader import R3C1_STATE_ASSET, ScenarioLoader
        return {"R3C1_STATE_ASSET": R3C1_STATE_ASSET, "ScenarioLoader": ScenarioLoader}[name]
    raise AttributeError(name)
