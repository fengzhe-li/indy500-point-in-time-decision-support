#!/usr/bin/env python3
"""Run R4A observable-state QA without substantive simulation."""

from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from r4.performance import R3C1ReadOnlyAdapter
from r4.state.scenario import Availability, SCENARIO_FIELDS
from r4.state.targets import DecisionTargetType


def main() -> int:
    suite = unittest.defaultTestLoader.discover(str(ROOT / "r4/tests"), pattern="test_*.py", top_level_dir=str(ROOT))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    verified = R3C1ReadOnlyAdapter(ROOT).verify()
    payload = {
        "phase": "R4A_PIT_WALL_OBSERVABLE_STATE",
        "status": "PASS" if result.wasSuccessful() and all(verified.values()) else "FAIL",
        "checks": {
            "all_r4_engineering_and_r4a_tests_pass": result.wasSuccessful(),
            "tests_run": result.testsRun,
            "scenario_field_count": len(SCENARIO_FIELDS),
            "provenance_classes": [item.value for item in Availability],
            "decision_target_types": [item.value for item in DecisionTargetType],
            "post_decision_information_rejected": result.wasSuccessful(),
            "realized_future_weather_rejected": result.wasSuccessful(),
            "future_competitor_actions_rejected": result.wasSuccessful(),
            "inferred_historical_queue_wait_rejected": result.wasSuccessful(),
            "future_track_grip_truth_rejected": result.wasSuccessful(),
            "future_tire_temperature_truth_rejected": result.wasSuccessful(),
            "unknown_preserved": result.wasSuccessful(),
            "leading_zero_car_number_preserved": result.wasSuccessful(),
            "numeric_car_number_rejected": result.wasSuccessful(),
            "historical_status_not_used_for_lane_eligibility": result.wasSuccessful(),
            "substantive_simulation_run": False,
            "stochastic_probabilities_created": False
        },
        "r3c1_manifest_asset_count": len(verified),
        "r3c1_manifest_assets_verified": all(verified.values()),
        "r3c1_assets": verified,
        "notes": "Schema/loader QA only; no queue, competitor, weather, tire, shadow, utility, or strategy probability was created."
    }
    path = ROOT / "r4/output/r4a_pit_wall_observable_state_qa.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
