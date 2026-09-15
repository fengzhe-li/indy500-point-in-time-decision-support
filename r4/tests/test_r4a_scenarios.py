from __future__ import annotations

import json
from pathlib import Path
import unittest

from r4.state.loader import ScenarioLoader
from r4.state.scenario import Availability, ObservableScenario, SCENARIO_FIELDS, ScenarioValidationError, to_pit_wall_state


ROOT = Path(__file__).resolve().parents[2]
DECISION = "2025-05-17T16:00:00Z"
BEFORE = "2025-05-17T15:00:00Z"


def unknown():
    return {"value": None, "availability": "UNKNOWN", "available_at_utc": None,
            "valid_at_utc": None, "source_reference": None, "derivation": None}


def observed(value, valid_at=DECISION):
    return {"value": value, "availability": "OBSERVED", "available_at_utc": BEFORE,
            "valid_at_utc": valid_at, "source_reference": "SYNTHETIC_INTERFACE_TEST", "derivation": None}


def derived(value, rule):
    return {"value": value, "availability": "DERIVED_FROM_OBSERVABLES", "available_at_utc": DECISION,
            "valid_at_utc": DECISION, "source_reference": "SYNTHETIC_INTERFACE_TEST", "derivation": rule}


def base_scenario():
    fields = {name: unknown() for name in SCENARIO_FIELDS}
    fields.update({
        "driver_name": observed("TEST DRIVER"),
        "car_number": observed("06"),
        "decision_timestamp_utc": observed(DECISION),
        "session_start_time_utc": observed("2025-05-17T15:00:00Z"),
        "session_end_time_utc": observed("2025-05-17T22:00:00Z"),
        "session_remaining_seconds": derived(21600.0, "session_end minus decision timestamp"),
        "completed_attempt_count": observed(1),
        "current_result_validity": observed("VALID"),
        "lane1_eligibility": observed(True),
        "lane2_eligibility": observed(True),
    })
    return {"schema_version": "R4A_OBSERVABLE_SCENARIO_V1", "fields": fields,
            "decision_target": {"type": "BEAT_CURRENT_RESULT"}}


class R4AScenarioTests(unittest.TestCase):
    def test_schema_declares_all_fields_and_provenance(self):
        schema = json.loads((ROOT / "r4/state/observable_scenario.schema.json").read_text())
        declared = schema["properties"]["fields"]
        self.assertEqual(set(declared["required"]), set(SCENARIO_FIELDS))
        self.assertEqual(set(declared["properties"]), set(SCENARIO_FIELDS))
        self.assertEqual(set(schema["$defs"]["fieldBase"]["properties"]),
                         {"value", "availability", "available_at_utc", "valid_at_utc", "source_reference", "derivation"})

    def test_fully_observed_state(self):
        raw = base_scenario()
        values = {
            "current_valid_four_lap_average_speed_mph": 1.0, "current_rank": 1,
            "advancement_benchmark_label": "SYNTHETIC FORMAT BOUNDARY",
            "advancement_benchmark_rank": 1, "current_cutoff_speed_mph": 1.0,
            "visible_lane1_queue_count": 0, "visible_lane2_queue_count": 0,
            "visible_cars_currently_queued": [], "ambient_temperature_c": 1.0,
            "track_temperature_c": 1.0, "relative_humidity_percent": 1.0,
            "pressure_hpa": 1.0, "wind_speed_mps": 1.0, "wind_direction_degrees": 1.0,
            "gust_speed_mps": 1.0, "cloud_cover_percent": 1.0,
            "shortwave_radiation_w_m2": 1.0, "solar_elevation_degrees": 1.0,
            "solar_azimuth_degrees": 1.0, "rain_interruption_observable_state": "TEST_STATE",
        }
        for name, value in values.items(): raw["fields"][name] = observed(value)
        loaded = ScenarioLoader(ROOT).load_mapping(raw)
        self.assertFalse(loaded.simulation_blockers)
        self.assertEqual(loaded.pit_wall_state.car_number, "06")
        self.assertEqual(loaded.pit_wall_state.session_end_time.isoformat(), "2025-05-17T22:00:00+00:00")
        self.assertEqual(loaded.pit_wall_state.rain_interruption_observable_state, "TEST_STATE")
        self.assertEqual(loaded.pit_wall_state.decision_target.target_type.value, "BEAT_CURRENT_RESULT")
        self.assertEqual(loaded.pit_wall_state.current_result_reference.speed_mph, 1.0)
        self.assertEqual(loaded.pit_wall_state.advancement_benchmark.rank, 1)
        self.assertEqual(loaded.pit_wall_state.field_provenance["car_number"].value, "06")

    def test_partial_state_preserves_unknown(self):
        raw = base_scenario()
        raw["fields"]["ambient_temperature_c"] = unknown()
        loaded = ScenarioLoader(ROOT).load_mapping(raw)
        self.assertIsNone(loaded.scenario.fields["ambient_temperature_c"].value)
        self.assertIs(loaded.scenario.fields["ambient_temperature_c"].availability, Availability.UNKNOWN)
        self.assertIsNone(loaded.pit_wall_state.ambient_temperature_c)

    def test_unknown_queue_remains_unknown(self):
        raw = base_scenario()
        raw["fields"]["visible_lane1_queue_count"] = unknown()
        raw["fields"]["visible_lane2_queue_count"] = unknown()
        raw["fields"]["visible_cars_currently_queued"] = unknown()
        loaded = ScenarioLoader(ROOT).load_mapping(raw)
        self.assertEqual(loaded.pit_wall_state.lane1_queue_state.observation_status, "UNKNOWN")
        self.assertEqual(loaded.pit_wall_state.lane2_queue_state.observation_status, "UNKNOWN")
        self.assertIsNone(loaded.scenario.fields["visible_cars_currently_queued"].value)

    def test_unknown_cutoff_remains_unknown(self):
        raw = base_scenario()
        raw["fields"]["current_cutoff_speed_mph"] = unknown()
        loaded = ScenarioLoader(ROOT).load_mapping(raw)
        self.assertIsNone(loaded.pit_wall_state.cutoff_speed_mph)
        self.assertIs(loaded.scenario.fields["current_cutoff_speed_mph"].availability, Availability.UNKNOWN)

    def test_post_decision_observation_is_rejected(self):
        raw = base_scenario()
        raw["fields"]["ambient_temperature_c"] = observed(1.0, "2025-05-17T16:01:00Z")
        with self.assertRaisesRegex(ScenarioValidationError, "realized future"):
            ObservableScenario.from_mapping(raw)

    def test_future_availability_is_rejected(self):
        raw = base_scenario()
        raw["fields"]["ambient_temperature_c"] = observed(1.0)
        raw["fields"]["ambient_temperature_c"]["available_at_utc"] = "2025-05-17T16:01:00Z"
        with self.assertRaisesRegex(ScenarioValidationError, "post-decision"):
            ObservableScenario.from_mapping(raw)

    def test_decision_time_forecast_is_allowed_but_realized_future_is_not(self):
        raw = base_scenario()
        raw["fields"]["ambient_temperature_c"] = {
            "value": 1.0, "availability": "FORECAST_AVAILABLE_AT_DECISION_TIME",
            "available_at_utc": BEFORE, "valid_at_utc": "2025-05-17T17:00:00Z",
            "source_reference": "SYNTHETIC_FORECAST_INTERFACE_TEST", "derivation": None,
        }
        scenario = ObservableScenario.from_mapping(raw)
        self.assertIs(scenario.fields["ambient_temperature_c"].availability,
                      Availability.FORECAST_AVAILABLE_AT_DECISION_TIME)

    def test_prohibited_future_field_is_rejected(self):
        for field in ("realized_future_weather", "future_competitor_actions",
                      "inferred_historical_queue_wait", "future_track_grip_truth",
                      "future_tire_temperature_truth", "post_decision_information"):
            raw = base_scenario(); raw[field] = {}
            with self.subTest(field=field), self.assertRaisesRegex(ScenarioValidationError, "prohibited"):
                ObservableScenario.from_mapping(raw)

    def test_leading_zero_car_number_is_preserved_and_numeric_is_rejected(self):
        loaded = ScenarioLoader(ROOT).load_mapping(base_scenario())
        self.assertEqual(loaded.pit_wall_state.car_number, "06")
        raw = base_scenario(); raw["fields"]["car_number"] = observed(6)
        with self.assertRaisesRegex(ScenarioValidationError, "string"):
            ObservableScenario.from_mapping(raw)

    def test_advancement_target_requires_explicit_benchmark(self):
        raw = base_scenario(); raw["decision_target"]["type"] = "CROSS_ADVANCEMENT_BENCHMARK"
        with self.assertRaisesRegex(ScenarioValidationError, "benchmark rank or cutoff speed"):
            ObservableScenario.from_mapping(raw)
        raw["fields"]["advancement_benchmark_rank"] = observed(9)
        self.assertEqual(ObservableScenario.from_mapping(raw).decision_target.target_type.value,
                         "CROSS_ADVANCEMENT_BENCHMARK")

    def test_legacy_target_terms_are_rejected_without_reinterpretation(self):
        for old_target in ("IMPROVE_CURRENT_SPEED", "REACH_TARGET_RANK"):
            raw = base_scenario(); raw["decision_target"]["type"] = old_target
            with self.subTest(old_target=old_target), self.assertRaisesRegex(
                    ScenarioValidationError, "deprecated.*not silently reinterpreted"):
                ObservableScenario.from_mapping(raw)
        raw = base_scenario()
        raw["fields"]["target_rank"] = raw["fields"].pop("advancement_benchmark_rank")
        with self.assertRaisesRegex(ScenarioValidationError, "target_rank is deprecated"):
            ObservableScenario.from_mapping(raw)

    def test_r3c1_loader_does_not_infer_lane_from_historical_action(self):
        raw = base_scenario()
        raw["fields"]["car_number"] = observed("TEST-CAR")
        raw["fields"]["lane1_eligibility"] = unknown()
        raw["fields"]["lane2_eligibility"] = unknown()
        loaded = ScenarioLoader(ROOT).load_r3c1("DTV3-2022-ALEXANDER_ROSSI", raw)
        self.assertIs(loaded.scenario.fields["lane1_eligibility"].availability, Availability.UNKNOWN)
        self.assertIs(loaded.scenario.fields["lane2_eligibility"].availability, Availability.UNKNOWN)
        self.assertFalse(loaded.pit_wall_state.action_eligibility["REPEAT_LANE1_WITHDRAW_CURRENT_RESULT"])
        self.assertIn("eligibility UNKNOWN", "|".join(loaded.simulation_blockers))

    def test_blank_generic_status_does_not_infer_lane_or_validity(self):
        class FakeR3:
            def assert_verified(self): pass
            def read_csv(self, asset):
                return ({"state_id":"TEST", "state_scope":"TEMPORAL_SAFE_LIMITED_PREDECISION_STATE",
                         "driver_name":"TEST DRIVER", "first_attempt_speed_mph":"UNKNOWN",
                         "predecision_current_rank":"UNKNOWN", "predecision_rank_lower_bound":"UNKNOWN",
                         "predecision_rank_upper_bound":"UNKNOWN", "predecision_cutoff_speed_mph":"UNKNOWN",
                         "first_car_attempt_index":"1", "first_attempt_status":"",
                         "historical_action_label":"WITHDRAW_EXISTING_RESULT_AND_USE_LANE1",
                         "historical_lane_label":"LANE_1"},)
        raw = base_scenario()
        raw["fields"]["current_result_validity"] = unknown()
        raw["fields"]["lane1_eligibility"] = unknown()
        loader = ScenarioLoader(ROOT); loader.r3c1 = FakeR3()
        loaded = loader.load_r3c1("TEST", raw)
        self.assertIs(loaded.scenario.fields["current_result_validity"].availability, Availability.UNKNOWN)
        self.assertIs(loaded.scenario.fields["lane1_eligibility"].availability, Availability.UNKNOWN)
        self.assertFalse(loaded.pit_wall_state.action_eligibility["REPEAT_LANE1_WITHDRAW_CURRENT_RESULT"])


if __name__ == "__main__":
    unittest.main()
