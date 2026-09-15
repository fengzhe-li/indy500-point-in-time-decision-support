"""Phase 5 Step 24 tests, items 1-13: Hypothetical Scenario Mode.

Exercises both the service layer directly (app/scenario_service.py) and
the FastAPI route (api/routes/scenario.py) so that a bug introduced at
either layer is caught.
"""
from __future__ import annotations

import inspect
import json
import sys
import unittest
from pathlib import Path

V3_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = V3_ROOT / "src"
APP_DIR = V3_ROOT / "app"
API_DIR = V3_ROOT / "api"
for p in (SRC_DIR, APP_DIR, API_DIR):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import final_v2_adapter  # noqa: E402
import scenario_service  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from main import app  # noqa: E402

REPLAY_EVENTS_FILE = V3_ROOT / "output" / "replay" / "replay_events.jsonl"
CASE_SUMMARY_FILE = V3_ROOT / "output" / "replay" / "replay_case_summary.csv"

def _walk_string_values(obj):
    """Yield only dict *values* (never keys) recursively -- so a field
    literally named retain_withdraw_recommendation doesn't trip a check
    for the word "retain" appearing as an actionable value."""
    if isinstance(obj, dict):
        for v in obj.values():
            yield from _walk_string_values(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _walk_string_values(v)
    elif isinstance(obj, str):
        yield obj


VALID_INPUT = {
    "current_track_temp_c": 36.0,
    "current_ambient_temp_c": 27.0,
    "forecast_future_ambient_temp_c": 29.0,
    "decision_time": "2026-05-22T17:00:00Z",
}


class ScenarioServiceTests(unittest.TestCase):
    def test_1_scenario_accepts_valid_input(self):
        result = scenario_service.run_scenario(**VALID_INPUT)
        self.assertEqual(len(result["horizons"]), 5)
        self.assertTrue(all(h["status"] == "SUPPORTED" for h in result["horizons"]))

    def test_2_scenario_rejects_missing_required_scientific_input(self):
        result = scenario_service.run_scenario(
            current_track_temp_c=None, current_ambient_temp_c=27.0, forecast_future_ambient_temp_c=29.0,
        )
        self.assertTrue(all(h["status"] == "INPUT_INSUFFICIENT" for h in result["horizons"]))
        self.assertTrue(all("expected_delta_v" not in h for h in result["horizons"]))

    def test_3_scenario_cannot_infer_above_120min(self):
        result = scenario_service.run_scenario(**VALID_INPUT)
        horizons = [h["horizon_minutes"] for h in result["horizons"]]
        self.assertEqual(sorted(horizons), [15, 30, 60, 90, 120])
        self.assertTrue(all(h <= 120 for h in horizons))
        # Structural guarantee: no code path in scenario_service accepts an
        # arbitrary horizon parameter at all.
        sig = inspect.signature(scenario_service.run_scenario)
        self.assertNotIn("horizon", sig.parameters)
        self.assertNotIn("horizon_min", sig.parameters)

    def test_4_scenario_output_is_hypothetical_scenario_mode(self):
        result = scenario_service.run_scenario(**VALID_INPUT)
        self.assertEqual(result["mode"], "HYPOTHETICAL_SCENARIO")

    def test_5_scenario_output_is_not_historical_evidence(self):
        result = scenario_service.run_scenario(**VALID_INPUT)
        self.assertEqual(result["evidence_status"], "NOT_HISTORICAL_EVIDENCE")

    def test_6_scenario_output_cannot_enter_historical_replay_storage(self):
        before_hash = REPLAY_EVENTS_FILE.read_bytes() if REPLAY_EVENTS_FILE.exists() else b""
        for _ in range(3):
            scenario_service.run_scenario(**VALID_INPUT)
        after_hash = REPLAY_EVENTS_FILE.read_bytes() if REPLAY_EVENTS_FILE.exists() else b""
        self.assertEqual(before_hash, after_hash, "running scenarios must never modify frozen replay evidence")
        # Source-level guarantee: no write-mode file I/O anywhere in the module.
        source = Path(scenario_service.__file__).read_text(encoding="utf-8")
        self.assertNotIn('"w"', source)
        self.assertNotIn("'w'", source)
        self.assertNotIn("write_text", source)
        self.assertNotIn("write_bytes", source)

    def test_7_scenario_output_cannot_enter_validation_metrics(self):
        client = TestClient(app)
        before = client.get("/api/validation/summary").json()
        client.post("/api/scenario/infer", json=VALID_INPUT)
        after = client.get("/api/validation/summary").json()
        self.assertEqual(before, after)

    def test_8_identical_scenario_input_is_reproducible(self):
        r1 = scenario_service.run_scenario(**VALID_INPUT)
        r2 = scenario_service.run_scenario(**VALID_INPUT)
        for h1, h2 in zip(r1["horizons"], r2["horizons"]):
            self.assertEqual(h1["expected_delta_v"], h2["expected_delta_v"])
            self.assertEqual(h1["pi80_low"], h2["pi80_low"])
        self.assertEqual(r1["input_hash"], r2["input_hash"])

    def test_9_scenario_agrees_with_direct_v3_scientific_inference(self):
        """Scenario Mode must be a thin interface, not a second model
        implementation: for the same inputs/seed/n_mc, it must produce
        exactly what calling final_v2_adapter.infer() directly produces."""
        result = scenario_service.run_scenario(**VALID_INPUT)
        for h in result["horizons"]:
            direct = final_v2_adapter.infer(
                current_track_temp_c=VALID_INPUT["current_track_temp_c"],
                current_ambient_temp_c=VALID_INPUT["current_ambient_temp_c"],
                forecast_future_ambient_temp_c=VALID_INPUT["forecast_future_ambient_temp_c"],
                decision_time=result["input"]["decision_time"],
                target_time=h["target_time"],
                horizon_min=h["horizon_minutes"],
                latitude_deg=scenario_service.LATITUDE_DEG,
                longitude_deg=scenario_service.LONGITUDE_DEG,
                random_seed=scenario_service.RANDOM_SEED,
                n_mc=scenario_service.N_MC,
            )
            self.assertEqual(h["expected_delta_v"], direct.expected_delta_v)
            self.assertEqual(h["pi90_high"], direct.pi90_high)

    def test_10_no_retain_recommendation(self):
        result = scenario_service.run_scenario(**VALID_INPUT)
        self.assertEqual(result["retain_withdraw_recommendation"], "NOT ISSUED")
        for value in _walk_string_values(result):
            self.assertNotEqual(value.strip().upper(), "RETAIN")

    def test_11_no_withdraw_recommendation(self):
        result = scenario_service.run_scenario(**VALID_INPUT)
        self.assertEqual(result["retain_withdraw_recommendation"], "NOT ISSUED")
        for value in _walk_string_values(result):
            self.assertNotEqual(value.strip().upper(), "WITHDRAW")

    def test_12_no_optimal_horizon_recommendation(self):
        result = scenario_service.run_scenario(**VALID_INPUT)
        blob = json.dumps(result).lower()
        for phrase in ("optimal", "best time", "recommended horizon", "best opportunity"):
            self.assertNotIn(phrase, blob)

    def test_13_no_queue_prediction(self):
        result = scenario_service.run_scenario(**VALID_INPUT)
        self.assertEqual(result["queue_time_prediction"], "NOT MODELLED")
        blob = json.dumps(result).lower()
        for phrase in ("queue wait", "opportunity in", "next run estimate"):
            self.assertNotIn(phrase, blob)


class ScenarioApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_schema_endpoint_lists_only_scientifically_derived_fields(self):
        r = self.client.get("/api/scenario/schema")
        self.assertEqual(r.status_code, 200)
        names = {f["name"] for f in r.json()["fields"]}
        self.assertEqual(names, {"current_track_temp_c", "current_ambient_temp_c", "forecast_future_ambient_temp_c", "decision_time"})

    def test_infer_endpoint_returns_200_for_valid_input(self):
        r = self.client.post("/api/scenario/infer", json=VALID_INPUT)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["mode"], "HYPOTHETICAL_SCENARIO")

    def test_infer_endpoint_200_with_input_insufficient_for_missing_fields(self):
        r = self.client.post("/api/scenario/infer", json={})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(all(h["status"] == "INPUT_INSUFFICIENT" for h in r.json()["horizons"]))

    def test_infer_endpoint_422_for_unparsable_decision_time(self):
        bad = dict(VALID_INPUT, decision_time="not-a-timestamp")
        r = self.client.post("/api/scenario/infer", json=bad)
        self.assertEqual(r.status_code, 422)

    def test_presets_are_labelled_demonstration_hypothetical(self):
        presets = self.client.get("/api/scenario/schema").json()["presets"]
        self.assertGreaterEqual(len(presets), 3)
        for preset in presets.values():
            self.assertEqual(preset["kind"], "DEMONSTRATION_PRESET")
            self.assertEqual(preset["status"], "HYPOTHETICAL")
            self.assertEqual(preset["evidence_status"], "NOT_HISTORICAL_EVIDENCE")


if __name__ == "__main__":
    unittest.main()
