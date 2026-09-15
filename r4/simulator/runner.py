"""Top-level Monte Carlo orchestration with independent deterministic streams."""

from __future__ import annotations

import hashlib
from random import Random
from typing import Sequence

from r4.competitors import CompetitorActionModel
from r4.config import SimulatorConfig
from r4.environment import FutureEnvironmentModel
from r4.performance import RepeatPerformanceModel
from r4.queue import QueueWaitModel
from r4.state import PitWallState

from .actions import Action
from .interfaces import InterruptionModel, LeaderboardUpdateModel, UtilityRiskEvaluator
from .types import SimulationRun, TrialRecord


COMPONENT_STREAMS = (
    "queue_evolution", "wait_time", "interruption", "future_environment",
    "repeat_performance", "competitor_outcomes", "leaderboard_update", "utility_evaluation",
)


def derive_component_seed(master_seed: int, action: Action, trial_index: int, component: str) -> int:
    if component not in COMPONENT_STREAMS:
        raise ValueError(f"unknown random component stream: {component}")
    material = f"R4|SHA256_COMPONENT_STREAM_V1|{master_seed}|{action.value}|{trial_index}|{component}"
    return int.from_bytes(hashlib.sha256(material.encode("utf-8")).digest()[:8], "big")


class MonteCarloRunner:
    def __init__(
        self,
        config: SimulatorConfig,
        queue_wait_model: QueueWaitModel,
        future_environment_model: FutureEnvironmentModel,
        repeat_performance_model: RepeatPerformanceModel,
        competitor_action_model: CompetitorActionModel,
        interruption_model: InterruptionModel,
        leaderboard_update_model: LeaderboardUpdateModel,
        utility_risk_evaluator: UtilityRiskEvaluator,
    ):
        self.config = config
        self.queue_wait_model = queue_wait_model
        self.future_environment_model = future_environment_model
        self.repeat_performance_model = repeat_performance_model
        self.competitor_action_model = competitor_action_model
        self.interruption_model = interruption_model
        self.leaderboard_update_model = leaderboard_update_model
        self.utility_risk_evaluator = utility_risk_evaluator

    def run(self, state: PitWallState, actions: Sequence[Action] | None = None) -> SimulationRun:
        self.config.assert_ready()
        selected = tuple(actions) if actions is not None else self.config.actions
        if not all(isinstance(action, Action) for action in selected):
            raise ValueError("all requested actions must be Action enum values")
        ineligible = [action.value for action in selected if not state.action_eligibility[action.value]]
        if ineligible:
            raise ValueError("requested ineligible actions: " + ", ".join(ineligible))

        records = []
        for action in selected:
            for trial_index in range(self.config.trials_per_action):
                seeds = {
                    component: derive_component_seed(self.config.master_seed, action, trial_index, component)
                    for component in COMPONENT_STREAMS
                }
                queue = self.queue_wait_model.sample_queue_evolution(state, action, Random(seeds["queue_evolution"]))
                wait = self.queue_wait_model.sample_wait_time(state, action, queue, Random(seeds["wait_time"]))
                interruption = self.interruption_model.sample_interruption(state, action, wait, Random(seeds["interruption"]))
                environment = self.future_environment_model.sample_future_environment(
                    state, action, queue, wait, interruption, Random(seeds["future_environment"])
                )
                performance = self.repeat_performance_model.sample_repeat_performance(
                    state, action, wait, environment, interruption, Random(seeds["repeat_performance"])
                )
                competitors = tuple(self.competitor_action_model.sample_competitor_outcomes(
                    state, action, queue, wait, environment, Random(seeds["competitor_outcomes"])
                ))
                leaderboard = self.leaderboard_update_model.update_leaderboard(
                    state, action, performance, competitors, interruption, Random(seeds["leaderboard_update"])
                )
                utility = self.utility_risk_evaluator.evaluate(
                    state, action, leaderboard, Random(seeds["utility_evaluation"])
                )
                records.append(TrialRecord(
                    action=action, trial_index=trial_index, component_seeds=seeds,
                    queue_evolution=queue, wait=wait, future_environment=environment,
                    interruption=interruption, repeat_performance=performance,
                    competitor_outcomes=competitors, final_leaderboard=leaderboard, utility=utility,
                ))
        return SimulationRun(
            master_seed=self.config.master_seed,
            trials_per_action=self.config.trials_per_action,
            records=tuple(records),
            configuration_fingerprint=self.config.fingerprint,
        )
