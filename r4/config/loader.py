from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from r4.simulator.actions import Action
from r4.simulator.errors import R4ConfigurationError


COMPONENTS = (
    "queue_wait_model", "future_environment_model", "repeat_performance_model",
    "competitor_action_model", "interruption_random_shock_model",
    "leaderboard_update_model", "utility_risk_profile_evaluator",
)


@dataclass(frozen=True)
class SimulatorConfig:
    raw: Mapping[str, Any]

    @classmethod
    def load(cls, path: str | Path) -> "SimulatorConfig":
        with Path(path).open(encoding="utf-8") as f:
            return cls(json.load(f))

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "SimulatorConfig":
        return cls(dict(value))

    @property
    def fingerprint(self) -> str:
        payload = json.dumps(self.raw, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @property
    def trials_per_action(self) -> int:
        value = self.raw.get("simulation", {}).get("trials_per_action")
        if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
            raise R4ConfigurationError("simulation.trials_per_action is NOT_CONFIGURED or invalid")
        return value

    @property
    def master_seed(self) -> int:
        value = self.raw.get("simulation", {}).get("master_seed")
        if not isinstance(value, int) or isinstance(value, bool):
            raise R4ConfigurationError("simulation.master_seed is NOT_CONFIGURED or invalid")
        return value

    @property
    def actions(self) -> tuple[Action, ...]:
        try:
            return tuple(Action(value) for value in self.raw["simulation"]["actions"])
        except (KeyError, TypeError, ValueError) as exc:
            raise R4ConfigurationError("simulation.actions is missing or invalid") from exc

    def assert_ready(self) -> None:
        models = self.raw.get("models", {})
        missing = []
        for name in COMPONENTS:
            spec = models.get(name)
            if not isinstance(spec, Mapping) or spec.get("implementation") in (None, "NOT_CONFIGURED") or spec.get("parameters") is None:
                missing.append(name)
        if missing:
            raise R4ConfigurationError("NOT_CONFIGURED model components: " + ", ".join(missing))
        _ = self.trials_per_action
        _ = self.master_seed
        if len(self.actions) != len(Action) or set(self.actions) != set(Action):
            raise R4ConfigurationError("simulation.actions must contain exactly the three supported actions")
