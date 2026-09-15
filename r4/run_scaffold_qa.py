#!/usr/bin/env python3
"""Run R4 engineering-only checks and write an additive QA result."""

from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from r4.config import SimulatorConfig
from r4.performance import R3C1ReadOnlyAdapter
from r4.simulator.errors import R4ConfigurationError


def main() -> int:
    suite = unittest.defaultTestLoader.loadTestsFromName("r4.tests.test_scaffold")
    result = unittest.TextTestRunner(verbosity=2).run(suite)

    adapter = R3C1ReadOnlyAdapter(ROOT)
    verified = adapter.verify()
    template = SimulatorConfig.load(ROOT / "r4/config/stochastic_parameters.template.json")
    rejects_unconfigured = False
    try:
        template.assert_ready()
    except R4ConfigurationError:
        rejects_unconfigured = True

    checks = {
        "engineering_unit_tests_pass": result.wasSuccessful(),
        "engineering_unit_tests_run": result.testsRun,
        "r3c1_manifest_assets_verified": all(verified.values()),
        "r3c1_manifest_asset_count": len(verified),
        "unconfigured_template_rejected": rejects_unconfigured,
        "substantive_simulation_run": False,
        "strategy_probabilities_created": False,
        "decision_thresholds_created": False,
    }
    payload = {
        "phase": "R4_ENGINEERING_SCAFFOLD",
        "status": "PASS" if result.wasSuccessful() and all(verified.values()) and rejects_unconfigured else "FAIL",
        "checks": checks,
        "r3c1_assets": verified,
        "notes": "Interface-only QA; no substantive strategy simulation or research parameter estimation.",
    }
    output = ROOT / "r4/output/r4_engineering_scaffold_qa.json"
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
