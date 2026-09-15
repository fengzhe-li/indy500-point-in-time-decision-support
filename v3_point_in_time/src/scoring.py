"""Step 9 — Conditional Physical Opportunity Value.

This is a derived, presentation-level quantity computed ONLY from
existing ShadowPrediction records. It is explicitly:

  E[Delta_v | H = h]

and, optionally, differences such as:

  E[Delta_v | H = h2] - E[Delta_v | H = h1]

It MUST NOT be interpreted, labelled, or reported as:
  - optimal waiting time
  - withdraw value
  - strategy value
  - expected race value

The correct interpretation, reproduced in every value this module
returns, is: "expected physical-performance change conditional on
another opportunity at horizon h." No queue, opportunity-probability,
or utility model is used or implied anywhere in this module.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from schemas import ShadowPrediction

FORBIDDEN_LABELS = (
    "optimal waiting time",
    "withdraw value",
    "strategy value",
    "expected race value",
)


@dataclass(frozen=True)
class ConditionalPhysicalOpportunityValue:
    horizon_minutes: int
    expected_delta_v: float
    interpretation: str = (
        "Expected physical-performance change conditional on another "
        "on-track opportunity occurring at this horizon. Not a queue-time, "
        "opportunity-probability, or strategy-utility estimate."
    )


def conditional_physical_opportunity_value(
    predictions: List[ShadowPrediction],
) -> Dict[int, ConditionalPhysicalOpportunityValue]:
    """E[Delta_v | H = h] for each horizon present in `predictions`."""
    return {
        p.horizon_minutes: ConditionalPhysicalOpportunityValue(
            horizon_minutes=p.horizon_minutes,
            expected_delta_v=p.expected_delta_v,
        )
        for p in predictions
    }


def opportunity_value_difference(
    predictions: List[ShadowPrediction],
    horizon_a_min: int,
    horizon_b_min: int,
) -> float:
    """E[Delta_v | H = horizon_b] - E[Delta_v | H = horizon_a].

    This is a difference of two conditional physical-performance
    expectations. It does not represent, and must never be labelled as,
    the value of waiting from horizon_a to horizon_b -- that would
    require an opportunity-probability model, which Phase 1 explicitly
    does not build (P(H = h) is out of scope; see the FINAL_V2 system
    specification section 15).
    """
    values = conditional_physical_opportunity_value(predictions)
    if horizon_a_min not in values or horizon_b_min not in values:
        missing = [h for h in (horizon_a_min, horizon_b_min) if h not in values]
        raise KeyError(f"No prediction available for horizon(s): {missing}")
    return values[horizon_b_min].expected_delta_v - values[horizon_a_min].expected_delta_v


def assert_no_forbidden_labels(text: str) -> None:
    """Defensive helper: fail loudly if a forbidden strategy-style label
    is ever attached to opportunity-value output by calling code."""
    lowered = text.lower()
    for label in FORBIDDEN_LABELS:
        if label in lowered:
            raise ValueError(
                f"Forbidden label {label!r} found in opportunity-value output text. "
                "Conditional physical opportunity value must not be described as "
                "a waiting-time, withdraw, or strategy recommendation."
            )
