"""Mandatory Phase 1 tests 1-3: point-in-time leakage rejection.

Uses only SYNTHETIC_TEST_FIXTURE data -- these tests prove software
behaviour (does the guard reject/allow correctly?), not a scientific
claim about FINAL_V2's output.
"""
import unittest

from fixtures import make_synthetic_forecast

from point_in_time_guard import check_point_in_time
from decision_snapshot import build_decision_snapshot
from forecast_vintage_store import ForecastVintageStore


DECISION_TIME = "2020-08-15T12:00:00Z"


class NoFutureLeakageTests(unittest.TestCase):
    def test_1_forecast_issued_one_second_after_decision_time_is_rejected(self):
        result = check_point_in_time(
            decision_time=DECISION_TIME,
            current_official_speed_known_at=None,
            current_track_temp_known_at=DECISION_TIME,
            current_ambient_temp_known_at=DECISION_TIME,
            forecast_issue_times=["2020-08-15T12:00:01Z"],
        )
        self.assertFalse(result.passed)
        self.assertIn("FORECAST_0_ISSUE_TIME_AFTER_DECISION_TIME", result.reasons)

    def test_2_forecast_issued_exactly_at_decision_time_is_allowed(self):
        result = check_point_in_time(
            decision_time=DECISION_TIME,
            current_official_speed_known_at=None,
            current_track_temp_known_at=DECISION_TIME,
            current_ambient_temp_known_at=DECISION_TIME,
            forecast_issue_times=[DECISION_TIME],
        )
        self.assertTrue(result.passed)
        self.assertEqual(result.reasons, ())

    def test_3_future_track_observation_cannot_enter_current_snapshot(self):
        # A "current" track-temperature reading whose known_at is AFTER
        # decision_time is exactly a future observation being smuggled
        # into the present snapshot. The guard must fail closed and
        # build_decision_snapshot must therefore refuse to construct a
        # snapshot at all -- there is no leaking snapshot object to
        # inspect afterward.
        future_known_at = "2020-08-15T12:00:05Z"

        snapshot, guard_result = build_decision_snapshot(
            snapshot_id="synthetic-leak-test",
            event_year=2020,
            car_or_entry_id="SYNTHETIC_CAR",
            decision_time=DECISION_TIME,
            current_track_temp_c=99.0,  # implausible value: proves it was never used
            current_ambient_temp_c=20.0,
            current_track_temp_known_at=future_known_at,
            current_ambient_temp_known_at=DECISION_TIME,
            selected_forecast_ids=("synthetic-1",),
            forecast_issue_times=(DECISION_TIME,),
        )

        self.assertIsNone(snapshot)
        self.assertFalse(guard_result.passed)
        self.assertIn("CURRENT_TRACK_TEMP_KNOWN_AT_AFTER_DECISION_TIME", guard_result.reasons)

    def test_forecast_vintage_store_never_selects_a_post_decision_issue_time(self):
        store = ForecastVintageStore()
        store.add(make_synthetic_forecast("f-late", issue_time="2020-08-15T12:00:01Z",
                                           valid_time="2020-08-15T13:00:00Z", ambient_temp_c=22.0))
        store.add(make_synthetic_forecast("f-ontime", issue_time=DECISION_TIME,
                                           valid_time="2020-08-15T13:00:00Z", ambient_temp_c=21.0))
        selection = store.select(decision_time=DECISION_TIME, target_time="2020-08-15T13:00:00Z")
        self.assertIsNotNone(selection)
        self.assertEqual(selection["vintage"].forecast_id, "f-ontime")


if __name__ == "__main__":
    unittest.main()
