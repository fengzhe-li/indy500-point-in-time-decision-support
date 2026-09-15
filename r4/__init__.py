"""R4 stochastic strategic decision simulator engineering scaffold."""

__all__ = ["Action", "MonteCarloRunner", "PitWallState"]


def __getattr__(name):
    if name == "Action":
        from .simulator.actions import Action
        return Action
    if name == "MonteCarloRunner":
        from .simulator.runner import MonteCarloRunner
        return MonteCarloRunner
    if name == "PitWallState":
        from .state.models import PitWallState
        return PitWallState
    raise AttributeError(name)
