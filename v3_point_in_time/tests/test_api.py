"""Phase 4 Step 23 tests (14 required items) for the FastAPI application
layer. Uses FastAPI's TestClient against the real app object (which
itself reads the real, frozen Phase 3 output on disk) -- no mocking of
scientific data, since the whole point of Phase 4 is that the API can
only ever serve what Phase 3 already froze and tested.
"""
from __future__ import annotations

import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

API_DIR = Path(__file__).resolve().parents[1] / "api"
APP_DIR = Path(__file__).resolve().parents[1] / "app"
for p in (API_DIR, APP_DIR):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from fastapi.testclient import TestClient  # noqa: E402
from main import app  # noqa: E402

ILLUSTRATIVE_CASE_ID = "2021_car60"
OUT_OF_SUPPORT_CASE_ID = "2021_car18"
FORBIDDEN_ACTIONABLE_VALUES = {"RETAIN", "WITHDRAW", "RETAIN NOW", "WITHDRAW NOW"}


def _parse(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(timezone.utc)


def _walk_strings(obj):
    if isinstance(obj, dict):
        for v in obj.values():
            yield from _walk_strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _walk_strings(v)
    elif isinstance(obj, str):
        yield obj


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_1_health_endpoint_works(self):
        r = self.client.get("/api/health")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["status"], "ok")

    def test_2_system_status_exposes_correct_scientific_boundaries(self):
        r = self.client.get("/api/system/status")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertEqual(body["supported_horizons_min"], [15, 30, 60, 90, 120])
        self.assertEqual(body["max_supported_horizon_min"], 120)
        self.assertEqual(body["queue_model"], "NOT_MODELLED")
        self.assertEqual(body["opportunity_time_model"], "NOT_MODELLED")
        self.assertEqual(body["strategy_recommendation"], "NOT_ISSUED")
        self.assertEqual(body["historical_scoring_validation"], "NOT_ESTABLISHED")
        self.assertEqual(body["v2_integrity"], "PASS")
        self.assertEqual(body["behavioural_regression"], "PASS")

    def test_3_replay_cases_endpoint_returns_phase3_cases(self):
        r = self.client.get("/api/replay/cases")
        self.assertEqual(r.status_code, 200)
        cases = r.json()
        self.assertEqual(len(cases), 10)
        self.assertIn(ILLUSTRATIVE_CASE_ID, {c["case_id"] for c in cases})

    def test_4_replay_events_preserve_chronological_order(self):
        r = self.client.get(f"/api/replay/cases/{ILLUSTRATIVE_CASE_ID}/events")
        self.assertEqual(r.status_code, 200)
        events = r.json()
        self.assertGreater(len(events), 0)
        times = [_parse(e["event_time"]) for e in events]
        self.assertEqual(times, sorted(times))

    def test_5_prediction_endpoint_returns_authoritative_prediction(self):
        r = self.client.get(f"/api/predictions/phase3:{ILLUSTRATIVE_CASE_ID}:h60")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertAlmostEqual(body["outlook"]["expected_delta_v"], 0.023574048313559002)
        self.assertEqual(body["horizon_minutes"], 60)

    def test_6_provenance_endpoint_matches_stored_prediction_provenance(self):
        pred_id = f"phase3:{ILLUSTRATIVE_CASE_ID}:h60"
        prov = self.client.get(f"/api/predictions/{pred_id}/provenance").json()
        events = self.client.get(f"/api/replay/cases/{ILLUSTRATIVE_CASE_ID}/events").json()
        forecast_event = next(
            e for e in events if e["event_type"] == "FORECAST_AVAILABLE" and e["payload"]["horizon_minutes"] == 60
        )
        self.assertEqual(prov["forecast_vintage_id"], forecast_event["provenance_ids"][0])
        self.assertEqual(prov["forecast_issue_time"], forecast_event["payload"]["forecast_issue_time"])

    def test_7_illustrative_case_is_flagged_correctly(self):
        scoring = self.client.get(f"/api/replay/cases/{ILLUSTRATIVE_CASE_ID}/scoring").json()
        self.assertEqual(scoring["status"], "ILLUSTRATIVE_ONLY")

    def test_8_illustrative_case_counts_toward_aggregate_validation_is_false(self):
        scoring = self.client.get(f"/api/replay/cases/{ILLUSTRATIVE_CASE_ID}/scoring").json()
        self.assertFalse(scoring["counts_toward_aggregate_validation"])

    def test_9_abstained_cases_remain_accessible(self):
        r = self.client.get(f"/api/replay/cases/{OUT_OF_SUPPORT_CASE_ID}/scoring")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["status"], "ABSTAINED")
        summary = self.client.get("/api/validation/summary").json()
        self.assertEqual(summary["abstained_insufficient_timestamp"], 31)

    def test_10_above_120min_inference_never_exposed_as_supported(self):
        outlook = self.client.get(f"/api/replay/cases/{ILLUSTRATIVE_CASE_ID}/outlook").json()
        horizons = [h["horizon_minutes"] for h in outlook["horizons"]]
        self.assertEqual(sorted(horizons), [15, 30, 60, 90, 120])
        status = self.client.get("/api/system/status").json()
        self.assertEqual(status["max_supported_horizon_min"], 120)

    def test_11_queue_prediction_is_absent(self):
        outlook = self.client.get(f"/api/replay/cases/{ILLUSTRATIVE_CASE_ID}/outlook").json()
        for h in outlook["horizons"]:
            if h["status"] == "SUPPORTED":
                self.assertEqual(h["queue_time_prediction"], "NOT MODELLED")
                self.assertNotIn("p_opportunity", h)
                self.assertNotIn("queue_wait_minutes", h)

    def test_12_strategy_recommendation_is_absent(self):
        outlook = self.client.get(f"/api/replay/cases/{ILLUSTRATIVE_CASE_ID}/outlook").json()
        for h in outlook["horizons"]:
            if h["status"] == "SUPPORTED":
                self.assertEqual(h["retain_withdraw_recommendation"], "NOT ISSUED")

    def test_13_no_api_payload_implies_retain_or_withdraw(self):
        endpoints = [
            "/api/system/status",
            "/api/replay/cases",
            f"/api/replay/cases/{ILLUSTRATIVE_CASE_ID}/outlook",
            f"/api/replay/cases/{ILLUSTRATIVE_CASE_ID}/events",
            f"/api/replay/cases/{ILLUSTRATIVE_CASE_ID}/scoring",
            f"/api/predictions/phase3:{ILLUSTRATIVE_CASE_ID}:h60",
            f"/api/predictions/phase3:{ILLUSTRATIVE_CASE_ID}:h60/provenance",
            f"/api/predictions/phase3:{ILLUSTRATIVE_CASE_ID}:h60/explanation",
            "/api/validation/summary",
        ]
        for ep in endpoints:
            body = self.client.get(ep).json()
            for s in _walk_strings(body):
                self.assertNotIn(s.strip().upper(), FORBIDDEN_ACTIONABLE_VALUES, msg=f"{ep} -> {s!r}")

    def test_14_no_future_information_leakage_in_replay_api_state(self):
        events = self.client.get(f"/api/replay/cases/{ILLUSTRATIVE_CASE_ID}/events").json()
        decision_events = [e for e in events if e["event_type"] in
                            ("PHYSICAL_STATE_OBSERVED", "FORECAST_AVAILABLE", "SHADOW_INFERENCE_ISSUED", "APPLICABILITY_CHANGED")]
        later_events = [e for e in events if e["event_type"] in ("FUTURE_ATTEMPT_OBSERVED", "PREDICTION_SCORED")]
        self.assertTrue(decision_events and later_events)
        max_decision_time = max(_parse(e["event_time"]) for e in decision_events)
        min_later_time = min(_parse(e["event_time"]) for e in later_events)
        self.assertLessEqual(max_decision_time, min_later_time)
        for e in decision_events:
            self.assertNotIn("observed_delta_v", e["payload"])


class ErrorHandlingTests(unittest.TestCase):
    """Scientific abstention/not-found must render as clean 404s, never 500s."""

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_unknown_case_is_404_not_500(self):
        r = self.client.get("/api/replay/cases/NOT_A_REAL_CASE")
        self.assertEqual(r.status_code, 404)

    def test_excluded_pre_candidate_case_id_is_404_not_500(self):
        r = self.client.get("/api/replay/cases/2020_car20_excluded")
        self.assertEqual(r.status_code, 404)

    def test_unknown_prediction_id_is_404_not_500(self):
        r = self.client.get("/api/predictions/phase3:does_not_exist:h60")
        self.assertEqual(r.status_code, 404)


if __name__ == "__main__":
    unittest.main()
