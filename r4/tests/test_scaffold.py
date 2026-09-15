from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
import unittest

from r4.competitors import NotConfiguredCompetitorActionModel
from r4.config import COMPONENTS, SimulatorConfig
from r4.environment import NotConfiguredFutureEnvironmentModel
from r4.performance import NotConfiguredRepeatPerformanceModel, R3C1ReadOnlyAdapter
from r4.queue import NotConfiguredQueueWaitModel
from r4.simulator.actions import Action
from r4.simulator.errors import NotConfiguredError, R4ConfigurationError
from r4.simulator.interfaces import (
    NotConfiguredInterruptionModel, NotConfiguredLeaderboardUpdateModel,
    NotConfiguredUtilityRiskEvaluator,
)
from r4.simulator.runner import COMPONENT_STREAMS, MonteCarloRunner, derive_component_seed
from r4.simulator.types import (
    CompetitorOutcome, FutureEnvironment, InterruptionOutcome, LeaderboardSnapshot,
    QueueEvolution, RepeatPerformance, UtilityEvaluation, WaitSample,
)
from r4.state import PitWallState, QueueObservation


ROOT = Path(__file__).resolve().parents[2]


def state():
    return PitWallState(
        decision_timestamp=datetime(2024, 5, 18, 17, 0, tzinfo=timezone.utc),
        session_remaining_seconds=3600.0, driver_id="TEST", driver_name="Interface Test",
        car_number="T", current_valid_speed_mph=None, current_rank=None, cutoff_rank=None,
        cutoff_speed_mph=None, attempt_count=0,
        action_eligibility={action.value: True for action in Action},
        lane1_queue_state=QueueObservation("UNKNOWN"), lane2_queue_state=QueueObservation("UNKNOWN"),
        ambient_temperature_c=None, track_temperature_c=None, relative_humidity_percent=None,
        pressure_hpa=None, wind_speed_mps=None, wind_direction_degrees=None,
        gust_speed_mps=None, cloud_cover_percent=None, shortwave_radiation_w_m2=None,
        solar_elevation_degrees=None, solar_azimuth_degrees=None,
    )


def configured():
    return SimulatorConfig.from_mapping({
        "simulation": {"trials_per_action": 2, "master_seed": 20240910,
                       "actions": [action.value for action in Action]},
        "models": {name: {"implementation": "INTERFACE_TEST_DOUBLE", "parameters": {}} for name in COMPONENTS},
    })


class TraceQueue:
    def sample_queue_evolution(self, state, action, rng):
        return QueueEvolution({}, {}, {"seed_trace": rng.getrandbits(32)})
    def sample_wait_time(self, state, action, queue, rng):
        return WaitSample(0.0, None, {"seed_trace": rng.getrandbits(32)})


class TraceEnvironment:
    def sample_future_environment(self, state, action, queue, wait, interruption, rng):
        return FutureEnvironment(state.decision_timestamp, {}, {"seed_trace": rng.getrandbits(32)})


class TracePerformance:
    def sample_repeat_performance(self, state, action, wait, environment, interruption, rng):
        return RepeatPerformance(False, None, None, {"seed_trace": rng.getrandbits(32)})


class TraceCompetitors:
    def sample_competitor_outcomes(self, state, action, queue, wait, environment, rng):
        return (CompetitorOutcome("TEST_COMPETITOR", "NO_POLICY", None, {"seed_trace": rng.getrandbits(32)}),)


class TraceInterruption:
    def sample_interruption(self, state, action, wait, rng):
        return InterruptionOutcome(False, 0.0, None, "INTERFACE_TEST", {"seed_trace": rng.getrandbits(32)})


class TraceLeaderboard:
    def update_leaderboard(self, state, action, performance, competitors, interruption, rng):
        return LeaderboardSnapshot(state.driver_id, None, None, (), {"seed_trace": rng.getrandbits(32)})


class TraceUtility:
    def evaluate(self, state, action, leaderboard, rng):
        return UtilityEvaluation(None, None, None, "NOT_SPECIFIED", "INTERFACE_TEST_ONLY", {"seed_trace": rng.getrandbits(32)})


def runner():
    return MonteCarloRunner(configured(), TraceQueue(), TraceEnvironment(), TracePerformance(),
                            TraceCompetitors(), TraceInterruption(), TraceLeaderboard(), TraceUtility())


class ScaffoldTests(unittest.TestCase):
    def test_schema_contains_exact_required_state_fields(self):
        schema = json.loads((ROOT / "r4/state/pit_wall_state.schema.json").read_text())
        expected = set(PitWallState.__dataclass_fields__)
        self.assertEqual(set(schema["required"]), expected)
        self.assertEqual(set(schema["properties"]), expected)

    def test_template_has_no_stochastic_values(self):
        config = SimulatorConfig.load(ROOT / "r4/config/stochastic_parameters.template.json")
        self.assertEqual(config.raw["status"], "NOT_CONFIGURED")
        self.assertTrue(all(spec["implementation"] == "NOT_CONFIGURED" and spec["parameters"] is None
                            for spec in config.raw["models"].values()))
        with self.assertRaisesRegex(R4ConfigurationError, "NOT_CONFIGURED"):
            config.assert_ready()

    def test_default_models_fail_explicitly(self):
        s, a = state(), Action.STOP_RETAIN_CURRENT_RESULT
        with self.assertRaises(NotConfiguredError):
            NotConfiguredQueueWaitModel().sample_queue_evolution(s, a, None)
        with self.assertRaises(NotConfiguredError):
            NotConfiguredFutureEnvironmentModel().sample_future_environment(s, a, None, None, None, None)
        with self.assertRaises(NotConfiguredError):
            NotConfiguredRepeatPerformanceModel().sample_repeat_performance(s, a, None, None, None, None)
        with self.assertRaises(NotConfiguredError):
            NotConfiguredCompetitorActionModel().sample_competitor_outcomes(s, a, None, None, None, None)
        with self.assertRaises(NotConfiguredError):
            NotConfiguredInterruptionModel().sample_interruption(s, a, None, None)
        with self.assertRaises(NotConfiguredError):
            NotConfiguredLeaderboardUpdateModel().update_leaderboard(s, a, None, None, None, None)
        with self.assertRaises(NotConfiguredError):
            NotConfiguredUtilityRiskEvaluator().evaluate(s, a, None, None)

    def test_seed_streams_are_stable_and_separated(self):
        seeds = [derive_component_seed(7, Action.STOP_RETAIN_CURRENT_RESULT, 0, c) for c in COMPONENT_STREAMS]
        self.assertEqual(seeds, [derive_component_seed(7, Action.STOP_RETAIN_CURRENT_RESULT, 0, c) for c in COMPONENT_STREAMS])
        self.assertEqual(len(seeds), len(set(seeds)))

    def test_runner_is_reproducible_and_records_required_outputs(self):
        first, second = runner().run(state()), runner().run(state())
        self.assertEqual(first, second)
        self.assertEqual(len(first.records), 6)
        self.assertTrue(all(record.final_rank is None and record.final_speed_mph is None for record in first.records))
        self.assertTrue(all(record.success_indicator is None and record.downside_indicator is None for record in first.records))

    def test_action_order_does_not_change_component_streams(self):
        s = state()
        forward = runner().run(s, tuple(Action))
        reverse = runner().run(s, tuple(reversed(tuple(Action))))
        by_key = lambda run: {(r.action, r.trial_index): r.component_seeds for r in run.records}
        self.assertEqual(by_key(forward), by_key(reverse))

    def test_r3c1_adapter_verifies_manifest_and_reads_only(self):
        adapter = R3C1ReadOnlyAdapter(ROOT)
        verified = adapter.verify()
        self.assertEqual(len(verified), 13)
        self.assertTrue(all(verified.values()))
        summary = adapter.read_json("final_capability_summary_v1.json")
        self.assertTrue(summary["technical_phase_complete"])
        self.assertEqual(summary["phase"], "R3C.1")


if __name__ == "__main__":
    unittest.main()
