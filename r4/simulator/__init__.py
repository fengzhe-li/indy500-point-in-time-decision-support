from .actions import Action
from .errors import NotConfiguredError, R4ConfigurationError
from .types import SimulationRun, TrialRecord

__all__ = ["Action", "MonteCarloRunner", "NotConfiguredError", "R4ConfigurationError", "SimulationRun", "TrialRecord"]


def __getattr__(name):
    if name == "MonteCarloRunner":
        from .runner import MonteCarloRunner
        return MonteCarloRunner
    raise AttributeError(name)
