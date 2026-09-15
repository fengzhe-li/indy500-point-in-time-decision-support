from dataclasses import dataclass
from enum import Enum


class DecisionTargetType(str, Enum):
    BEAT_CURRENT_RESULT = "BEAT_CURRENT_RESULT"
    CROSS_ADVANCEMENT_BENCHMARK = "CROSS_ADVANCEMENT_BENCHMARK"
    IMPROVE_RANK = "IMPROVE_RANK"
    REMAIN_ABOVE_CUTOFF = "REMAIN_ABOVE_CUTOFF"
    MAXIMIZE_EXPECTED_RANK = "MAXIMIZE_EXPECTED_RANK"


@dataclass(frozen=True)
class DecisionTarget:
    """A target definition only; it contains no utility threshold or recommendation rule."""

    target_type: DecisionTargetType


class FutureOutputSemantic(str, Enum):
    """Names reserved for later model outputs; no probability is computed in R4P0."""

    P_BEAT_CURRENT_RESULT = "P_BEAT_CURRENT_RESULT"
    P_CROSS_ADVANCEMENT_BENCHMARK = "P_CROSS_ADVANCEMENT_BENCHMARK"
    P_IMPROVE_RANK = "P_IMPROVE_RANK"
    P_FINISH_WORSE_THAN_CURRENT_RESULT = "P_FINISH_WORSE_THAN_CURRENT_RESULT"
    P_COMPLETE_BEFORE_SESSION_END = "P_COMPLETE_BEFORE_SESSION_END"


@dataclass(frozen=True)
class CurrentResultReference:
    """The driver's current valid result, the primary repeat comparison reference."""

    speed_mph: float | None
    rank: int | None
    validity: str | None


@dataclass(frozen=True)
class AdvancementBenchmark:
    """A format-regime boundary, not a fixed team objective or universal rank."""

    label: str | None
    rank: int | None
    cutoff_speed_mph: float | None
