"""Phase 5 Step 24 tests, items 14-21: default-case selection, car 60
featured-diagnostic status, historical-API read-only/no-recompute
audit, immutability, behavioural regression, and readiness.
"""
from __future__ import annotations

import ast
import subprocess
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

import replay_service  # noqa: E402
import health_service  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from main import app  # noqa: E402

REPO_ROOT = V3_ROOT.parent
SCRIPTS_DIR = V3_ROOT / "scripts"


class DefaultCaseSelectionTests(unittest.TestCase):
    def test_14_default_landing_case_is_not_illustrative_only(self):
        rep = replay_service.select_representative_case()
        self.assertNotEqual(rep["category"], "ILLUSTRATIVE_ONLY")
        self.assertEqual(rep["category"], "CONDITIONAL_OUTLOOK_SUPPORTED_BUT_HISTORICAL_SCORING_UNSUPPORTED")

    def test_selection_reason_is_not_outcome_based(self):
        rep = replay_service.select_representative_case()
        reason = rep["selection_reason"].lower()
        for forbidden in ("largest", "best-looking", "most favourable", "highest expected", "biggest improvement"):
            self.assertNotIn(forbidden, reason)


class Car60FeaturedDiagnosticTests(unittest.TestCase):
    def test_15_car_60_remains_illustrative_only(self):
        scoring = replay_service.get_case_scoring("2021_car60")
        self.assertEqual(scoring["status"], "ILLUSTRATIVE_ONLY")

    def test_16_car_60_remains_excluded_from_aggregate_validation(self):
        scoring = replay_service.get_case_scoring("2021_car60")
        self.assertFalse(scoring["counts_toward_aggregate_validation"])
        client = TestClient(app)
        summary = client.get("/api/validation/summary").json()
        self.assertEqual(summary["historical_scoring_formally_supported"], 0)


class HistoricalApiReadOnlyTests(unittest.TestCase):
    WRITE_INDICATORS = ('write_text(', 'write_bytes(', '"w")', "'w')", '"wb")', "'wb')", '"a")', "'a')", 'csv.writer(', 'csv.DictWriter(')

    def test_17_historical_api_modules_remain_read_only(self):
        """replay_service.py / provenance_service.py / query_service.py
        must never write to output/replay or output/evaluation -- every
        file they open is opened in a read mode."""
        for module_name in ("replay_service", "provenance_service", "query_service"):
            source = (APP_DIR / f"{module_name}.py").read_text(encoding="utf-8")
            for indicator in self.WRITE_INDICATORS:
                self.assertNotIn(indicator, source, f"{module_name} contains write indicator {indicator!r}")

    def test_18_historical_api_does_not_import_scientific_inference_code(self):
        """Only scenario_service.py is permitted to import FINAL_V2
        scientific code. Verified by parsing imports, not just grepping,
        so a re-exported alias can't slip past a substring check."""
        forbidden_modules = {"final_v2_adapter", "shadow_engine", "applicability_gate", "point_in_time_guard"}
        for module_name in ("replay_service", "provenance_service", "query_service", "health_service"):
            tree = ast.parse((APP_DIR / f"{module_name}.py").read_text(encoding="utf-8"))
            imported = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imported.update(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imported.add(node.module)
            overlap = imported & forbidden_modules
            if module_name == "health_service":
                # health_service is allowed to import final_v2_adapter ONLY
                # to read its frozen file-path constants for a readiness
                # check -- it never calls .infer() or any MC code.
                self.assertEqual(overlap, {"final_v2_adapter"} & overlap)
                source = (APP_DIR / "health_service.py").read_text(encoding="utf-8")
                self.assertNotIn(".infer(", source)
            else:
                self.assertEqual(overlap, set(), f"{module_name} must not import {overlap}")


class FinalImmutabilityAndRegressionTests(unittest.TestCase):
    def test_19_final_v2_assets_remain_immutable(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "run_v2_immutability_check.py")],
            cwd=REPO_ROOT, capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("OVERALL RESULT: PASS", result.stdout)

    def test_20_v3_v2_behavioural_regression_remains_pass(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "run_v3_v2_behavioral_regression.py")],
            cwd=REPO_ROOT, capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("Overall result: PASS", result.stdout)


class ReadinessTests(unittest.TestCase):
    def test_21_readiness_fails_appropriately_if_scientific_assets_invalid(self):
        real_check = health_service.check_v2_integrity
        try:
            health_service.check_v2_integrity = lambda: {"status": "FAIL", "checked": 32, "mismatched": [{"path": "fake.csv", "reason": "HASH_MISMATCH"}]}
            result = health_service.readiness()
            self.assertEqual(result["status"], "NOT_READY")
            self.assertEqual(result["checks"]["final_v2_integrity"]["status"], "FAIL")
        finally:
            health_service.check_v2_integrity = real_check

    def test_readiness_is_ready_on_the_real_untouched_repository(self):
        result = health_service.readiness()
        self.assertEqual(result["status"], "READY")

    def test_readiness_endpoint_returns_503_when_not_ready(self):
        client = TestClient(app)
        real_check = health_service.check_v2_integrity
        try:
            health_service.check_v2_integrity = lambda: {"status": "FAIL", "checked": 0, "mismatched": ["x"]}
            r = client.get("/api/system/readiness")
            self.assertEqual(r.status_code, 503)
        finally:
            health_service.check_v2_integrity = real_check


if __name__ == "__main__":
    unittest.main()
