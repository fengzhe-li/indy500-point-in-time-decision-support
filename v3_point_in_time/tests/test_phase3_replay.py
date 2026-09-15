"""Phase 3 Step 19 tests (18 required items).

Uses two kinds of fixtures, matching the existing project convention
(see tests/fixtures.py docstring):
  - clearly-labelled SYNTHETIC_TEST_FIXTURE data for pure software-behaviour
    tests (leakage rejection, abstention-vs-fabrication, reason-code
    machine-readability) that must never be mistaken for a scientific result;
  - the real, non-fabricated 2021 candidate cases (via
    run_phase2_evaluation.find_candidates(), the same single source of
    truth Phase 2 itself uses) for tests that must exercise genuine
    historical evidence (illustrative-case handling, inference/historical-
    scoring distinctness, determinism, provenance).
"""
from __future__ import annotations

import csv
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

import fixtures  # noqa: F401  (adds src/ to sys.path)
from fixtures import make_synthetic_forecast, SYNTHETIC_TEST_FIXTURE_LABEL

import applicability_gate
import replay_engine
from schemas import ABSTENTION_REASON_CODES, REPLAY_EVENT_TYPES
from forecast_vintage_store import ForecastVintageStore

REPO_ROOT = fixtures.REPO_ROOT
SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
REPLAY_DIR = Path(__file__).resolve().parents[1] / "output" / "replay"

sys.path.insert(0, str(SCRIPTS_DIR))
from run_phase2_evaluation import find_candidates  # noqa: E402

LATITUDE_DEG = 39.7950
LONGITUDE_DEG = -86.2348
RANDOM_SEED = 20260914
N_MC = 2000  # smaller than production for fast tests; determinism doesn't depend on n_mc size

DECISION_TIME = "2020-08-15T12:00:00Z"
TARGET_TIME_60 = "2020-08-15T13:00:00Z"


def _parse(ts):
    return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(timezone.utc)


def _synthetic_case(store_forecasts):
    store = ForecastVintageStore()
    for fc in store_forecasts:
        store.add(fc)
    case = dict(
        case_id="SYNTH_TEST_CASE", event_year=2020, car_or_entry_id="C",
        decision_time=DECISION_TIME, current_track_temp_c=28.0, current_ambient_temp_c=21.0,
        current_track_temp_known_at=DECISION_TIME, current_ambient_temp_known_at=DECISION_TIME,
        realised_attempt_time="2020-08-15T13:04:08Z", realised_horizon_minutes=64.1,
        observed_delta_v=1.234,
    )
    return case, store


_REAL_CANDIDATES_CACHE = None


def _real_candidates():
    global _REAL_CANDIDATES_CACHE
    if _REAL_CANDIDATES_CACHE is None:
        candidates, excluded = find_candidates()
        _REAL_CANDIDATES_CACHE = (candidates, excluded)
    return _REAL_CANDIDATES_CACHE


def _real_case_dict(raw):
    return dict(
        case_id=raw["case_id"], event_year=raw["event_year"], car_or_entry_id=raw["car_or_entry_id"],
        decision_time=raw["decision_time"].tz_convert("UTC").isoformat().replace("+00:00", "Z"),
        current_track_temp_c=raw["current_track_temp_c"], current_ambient_temp_c=raw["current_ambient_temp_c"],
        current_track_temp_known_at=raw["decision_time"].tz_convert("UTC").isoformat().replace("+00:00", "Z"),
        current_ambient_temp_known_at=raw["decision_time"].tz_convert("UTC").isoformat().replace("+00:00", "Z"),
        realised_attempt_time=raw["realised_attempt_time"].tz_convert("UTC").isoformat().replace("+00:00", "Z"),
        realised_horizon_minutes=raw["realised_horizon_minutes"], observed_delta_v=raw["observed_delta_v"],
    )


_REAL_STORE_CACHE = None


def _real_store():
    global _REAL_STORE_CACHE
    if _REAL_STORE_CACHE is None:
        HRRR_FILE = REPO_ROOT / "weather/output/hrrr_ims_2020_2024_features.csv"
        _REAL_STORE_CACHE = ForecastVintageStore.load_hrrr_features(HRRR_FILE, LATITUDE_DEG, LONGITUDE_DEG)
    return _REAL_STORE_CACHE


def _real_case(case_id):
    candidates, _ = _real_candidates()
    raw = next(c for c in candidates if c["case_id"] == case_id)
    return _real_case_dict(raw)


class TimeOrderingTests(unittest.TestCase):
    def test_1_replay_events_are_strictly_time_ordered(self):
        case = _real_case("2021_car60")
        with tempfile.TemporaryDirectory() as d:
            result = replay_engine.replay_case(case, _real_store(), Path(d), LATITUDE_DEG, LONGITUDE_DEG, RANDOM_SEED, N_MC)
        times = [_parse(ev.event_time) for ev in result.events]
        self.assertEqual(times, sorted(times), "events must already be produced in non-decreasing event_time order")


class InformationStateTests(unittest.TestCase):
    def test_2_information_state_excludes_items_known_after_decision_time(self):
        state, excluded = replay_engine.build_information_state(
            DECISION_TIME,
            [
                {"name": "before", "known_at": "2020-08-15T11:00:00Z", "value": 1},
                {"name": "after", "known_at": "2020-08-15T13:00:00Z", "value": 2},
                {"name": "unknown", "known_at": None, "value": 3},
            ],
        )
        self.assertEqual(state, {"before": 1})
        self.assertIn("after", excluded)
        self.assertIn("unknown", excluded)

    def test_3_forecast_issued_after_decision_time_cannot_enter_replay_state(self):
        future_forecast = make_synthetic_forecast("f-future", issue_time="2020-08-15T12:30:00Z", valid_time=TARGET_TIME_60, ambient_temp_c=5.0)
        case, store = _synthetic_case([future_forecast])
        with tempfile.TemporaryDirectory() as d:
            result = replay_engine.replay_case(case, store, Path(d), LATITUDE_DEG, LONGITUDE_DEG, RANDOM_SEED, N_MC)
        issued = [e for e in result.events if e.event_type == "SHADOW_INFERENCE_ISSUED"]
        self.assertEqual(issued, [], "a post-decision-time forecast must never produce an inference")
        for e in result.events:
            for pid in e.provenance_ids:
                self.assertNotEqual(pid, "f-future")


class AbstentionNotFabricationTests(unittest.TestCase):
    def test_4_abstention_produced_instead_of_fabricated_inference(self):
        case, store = _synthetic_case([])  # no forecast at all
        with tempfile.TemporaryDirectory() as d:
            result = replay_engine.replay_case(case, store, Path(d), LATITUDE_DEG, LONGITUDE_DEG, RANDOM_SEED, N_MC)
        self.assertEqual([e for e in result.events if e.event_type == "SHADOW_INFERENCE_ISSUED"], [])
        abstained = [e for e in result.events if e.event_type == "SHADOW_INFERENCE_ABSTAINED"]
        inference_abstained = [e for e in abstained if e.payload.get("scope") == "INFERENCE"]
        scoring_abstained = [e for e in abstained if e.payload.get("scope") == "HISTORICAL_SCORING"]
        self.assertEqual(len(inference_abstained), len(replay_engine.CALIBRATED_ANCHOR_HORIZONS_MIN))
        for e in inference_abstained:
            self.assertEqual(e.abstention_reason_codes, ("NO_VALID_FORECAST_VINTAGE",))
        # With no forecast at all, historical scoring is also abstained
        # (there is no anchor outlook to pair the realised attempt against).
        self.assertEqual(len(scoring_abstained), 1)

    def test_5_reason_codes_are_from_the_closed_machine_readable_vocabulary(self):
        case, store = _synthetic_case([])
        with tempfile.TemporaryDirectory() as d:
            result = replay_engine.replay_case(case, store, Path(d), LATITUDE_DEG, LONGITUDE_DEG, RANDOM_SEED, N_MC)
        for e in result.events:
            self.assertIn(e.event_type, REPLAY_EVENT_TYPES)
            for code in e.abstention_reason_codes:
                self.assertIn(code, ABSTENTION_REASON_CODES)


class IllustrativeCaseTests(unittest.TestCase):
    def test_6_illustrative_case_not_counted_as_aggregate_validation(self):
        case = _real_case("2021_car60")
        with tempfile.TemporaryDirectory() as d:
            result = replay_engine.replay_case(case, _real_store(), Path(d), LATITUDE_DEG, LONGITUDE_DEG, RANDOM_SEED, N_MC)
        self.assertEqual(result.category, "ILLUSTRATIVE_ONLY")
        scored = next(e for e in result.events if e.event_type == "PREDICTION_SCORED")
        self.assertFalse(scored.payload["counts_toward_aggregate_validation"])
        self.assertEqual(scored.evaluation_status, "ILLUSTRATIVE_ONLY")
        self.assertIn("NON_ANCHOR_EVALUATION_NOT_APPROVED", scored.abstention_reason_codes)

    def test_7_illustrative_case_remains_accessible_for_diagnostic_replay(self):
        case = _real_case("2021_car60")
        with tempfile.TemporaryDirectory() as d:
            result = replay_engine.replay_case(case, _real_store(), Path(d), LATITUDE_DEG, LONGITUDE_DEG, RANDOM_SEED, N_MC)
        scored = next(e for e in result.events if e.event_type == "PREDICTION_SCORED")
        self.assertIn("observed_delta_v", scored.payload)
        self.assertIn("expected_delta_v", scored.payload)
        self.assertAlmostEqual(scored.payload["observed_delta_v"], case["observed_delta_v"])


class HorizonSupportTests(unittest.TestCase):
    def test_8_supported_scientific_horizons_remain_exactly_the_five_anchors(self):
        self.assertEqual(replay_engine.CALIBRATED_ANCHOR_HORIZONS_MIN, (15, 30, 60, 90, 120))

    def test_9_horizons_above_120_are_never_attempted_by_replay(self):
        self.assertTrue(all(h <= 120 for h in replay_engine.CALIBRATED_ANCHOR_HORIZONS_MIN))
        result = applicability_gate.evaluate(150, 28.0, 20.0, 19.0)
        self.assertEqual(result.status, "OUT_OF_SUPPORT")


class ForbiddenOutputsTests(unittest.TestCase):
    def test_10_no_queue_prediction_is_produced(self):
        case = _real_case("2021_car60")
        with tempfile.TemporaryDirectory() as d:
            result = replay_engine.replay_case(case, _real_store(), Path(d), LATITUDE_DEG, LONGITUDE_DEG, RANDOM_SEED, N_MC)
        issued = [e for e in result.events if e.event_type == "SHADOW_INFERENCE_ISSUED"]
        self.assertTrue(issued)
        for e in issued:
            self.assertEqual(e.payload["queue_time_prediction"], "NOT MODELLED")
            self.assertNotIn("p_opportunity", e.payload)
            self.assertNotIn("queue_wait_minutes", e.payload)

    def test_11_no_retain_withdraw_recommendation_is_produced(self):
        case = _real_case("2021_car60")
        with tempfile.TemporaryDirectory() as d:
            result = replay_engine.replay_case(case, _real_store(), Path(d), LATITUDE_DEG, LONGITUDE_DEG, RANDOM_SEED, N_MC)
        issued = [e for e in result.events if e.event_type == "SHADOW_INFERENCE_ISSUED"]
        for e in issued:
            self.assertEqual(e.payload["retain_withdraw_recommendation"], "NOT ISSUED")
        applicability_events = [e for e in result.events if e.event_type == "APPLICABILITY_CHANGED"]
        for e in applicability_events:
            self.assertEqual(e.payload["strategy_identifiability"]["status"], "NOT_MODELLED")


class ProvenanceTests(unittest.TestCase):
    def test_12_replay_prediction_provenance_matches_actual_inputs(self):
        case = _real_case("2021_car60")
        with tempfile.TemporaryDirectory() as d:
            result = replay_engine.replay_case(case, _real_store(), Path(d), LATITUDE_DEG, LONGITUDE_DEG, RANDOM_SEED, N_MC)
        scored = next(e for e in result.events if e.event_type == "PREDICTION_SCORED")
        forecast_event = next(
            e for e in result.events
            if e.event_type == "SHADOW_INFERENCE_ISSUED" and e.payload["horizon_minutes"] == scored.payload["anchor_horizon_minutes"]
        )
        self.assertEqual(scored.provenance_ids[0], forecast_event.provenance_ids[0])
        self.assertEqual(scored.prediction_id, forecast_event.prediction_id)


class DeterminismTests(unittest.TestCase):
    def test_13_repeated_replay_is_deterministic_at_the_hash_level(self):
        case = _real_case("2021_car60")
        with tempfile.TemporaryDirectory() as d1, tempfile.TemporaryDirectory() as d2:
            r1 = replay_engine.replay_case(case, _real_store(), Path(d1), LATITUDE_DEG, LONGITUDE_DEG, RANDOM_SEED, N_MC)
            r2 = replay_engine.replay_case(case, _real_store(), Path(d2), LATITUDE_DEG, LONGITUDE_DEG, RANDOM_SEED, N_MC)
        issued1 = {e.payload["horizon_minutes"]: e for e in r1.events if e.event_type == "SHADOW_INFERENCE_ISSUED"}
        issued2 = {e.payload["horizon_minutes"]: e for e in r2.events if e.event_type == "SHADOW_INFERENCE_ISSUED"}
        for h in issued1:
            self.assertEqual(issued1[h].payload["expected_delta_v"], issued2[h].payload["expected_delta_v"])
            self.assertEqual(issued1[h].provenance_ids, issued2[h].provenance_ids)


class SyntheticIsolationTests(unittest.TestCase):
    def test_14_synthetic_fixture_cannot_enter_historical_replay_results(self):
        for f in (REPLAY_DIR / "replay_events.jsonl", REPLAY_DIR / "replay_events.csv", REPLAY_DIR / "replay_case_summary.csv"):
            if not f.exists():
                continue
            text = f.read_text(encoding="utf-8")
            self.assertNotIn(SYNTHETIC_TEST_FIXTURE_LABEL, text)
        candidates, _ = _real_candidates()
        self.assertGreater(len(candidates), 0)


class ImmutabilityAndRegressionTests(unittest.TestCase):
    def test_15_v2_frozen_dependencies_remain_byte_identical(self):
        script = SCRIPTS_DIR / "run_v2_immutability_check.py"
        result = subprocess.run([sys.executable, str(script)], cwd=REPO_ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("OVERALL RESULT: PASS", result.stdout)

    def test_16_v3_v2_behavioural_regression_remains_pass(self):
        script = SCRIPTS_DIR / "run_v3_v2_behavioral_regression.py"
        result = subprocess.run([sys.executable, str(script)], cwd=REPO_ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("Overall result: PASS", result.stdout)


class SupportDistinctionTests(unittest.TestCase):
    def test_17_historical_scoring_support_is_distinct_from_inference_support(self):
        case = _real_case("2021_car18")  # realised horizon 288 min: out of historical-scoring support
        with tempfile.TemporaryDirectory() as d:
            result = replay_engine.replay_case(case, _real_store(), Path(d), LATITUDE_DEG, LONGITUDE_DEG, RANDOM_SEED, N_MC)
        self.assertEqual(len(result.inference_supported_horizons), 5, "conditional outlook must be issued at all 5 anchors")
        self.assertEqual(result.historical_support.status, "ABSTAINED", "realised horizon 288min cannot be historically scored")
        self.assertEqual(result.category, "CONDITIONAL_OUTLOOK_SUPPORTED_BUT_HISTORICAL_SCORING_UNSUPPORTED")


class AuditTrailTests(unittest.TestCase):
    def test_18_abstained_cases_remain_in_audit_outputs_not_silently_dropped(self):
        case_summary = REPLAY_DIR / "replay_case_summary.csv"
        if not case_summary.exists():
            self.skipTest("replay_case_summary.csv not yet generated by run_phase3_replay.py")
        with open(case_summary, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        abstained = [r for r in rows if r["category"] == "ABSTAINED_INSUFFICIENT_TIMESTAMP"]
        self.assertEqual(len(abstained), 31, "all 31 excluded pre-candidates must appear, not be dropped")


if __name__ == "__main__":
    unittest.main()
