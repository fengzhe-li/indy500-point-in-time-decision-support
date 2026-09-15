"""Forecast vintage selection behaviour (Step 3), beyond the two
leakage-boundary cases already covered in test_no_future_leakage.py."""
import unittest

from fixtures import make_synthetic_forecast
from forecast_vintage_store import ForecastVintageStore

DECISION_TIME = "2020-08-15T12:15:00Z"
TARGET_TIME = "2020-08-15T13:15:00Z"


class ForecastSelectionTests(unittest.TestCase):
    def test_prefers_most_recent_eligible_issue_time_over_closer_valid_time(self):
        store = ForecastVintageStore()
        # Older run, exact valid_time match.
        store.add(make_synthetic_forecast(
            "f-old-exact", issue_time="2020-08-15T11:00:00Z",
            valid_time=TARGET_TIME, ambient_temp_c=20.0,
        ))
        # Newer run, valid_time 15 minutes off.
        store.add(make_synthetic_forecast(
            "f-new-close", issue_time="2020-08-15T12:00:00Z",
            valid_time="2020-08-15T13:00:00Z", ambient_temp_c=21.0,
        ))
        selection = store.select(DECISION_TIME, TARGET_TIME)
        self.assertEqual(selection["vintage"].forecast_id, "f-new-close")
        self.assertAlmostEqual(selection["valid_time_error_minutes"], 15.0)

    def test_breaks_ties_on_issue_time_by_closest_valid_time(self):
        store = ForecastVintageStore()
        store.add(make_synthetic_forecast(
            "f-tie-far", issue_time="2020-08-15T12:00:00Z",
            valid_time="2020-08-15T15:00:00Z", ambient_temp_c=25.0,
        ))
        store.add(make_synthetic_forecast(
            "f-tie-close", issue_time="2020-08-15T12:00:00Z",
            valid_time="2020-08-15T13:00:00Z", ambient_temp_c=21.0,
        ))
        selection = store.select(DECISION_TIME, TARGET_TIME)
        self.assertEqual(selection["vintage"].forecast_id, "f-tie-close")

    def test_no_eligible_vintage_returns_none(self):
        store = ForecastVintageStore()
        store.add(make_synthetic_forecast(
            "f-too-late", issue_time="2020-08-15T13:00:00Z",
            valid_time=TARGET_TIME, ambient_temp_c=20.0,
        ))
        selection = store.select(DECISION_TIME, TARGET_TIME)
        self.assertIsNone(selection)

    def test_loads_real_historical_hrrr_vintages_without_modifying_source(self):
        import fixtures  # noqa: F401  (adds src/ to sys.path)
        from hashing import sha256_file

        path = fixtures.REPO_ROOT / "weather/output/hrrr_ims_2020_2024_features.csv"
        before = sha256_file(path)
        store = ForecastVintageStore.load_hrrr_features(path, 39.7950, -86.2348)
        after = sha256_file(path)

        self.assertEqual(before, after)
        self.assertGreater(len(store.all()), 0)
        self.assertTrue(all(v.source == "NOAA" for v in store.all()))


if __name__ == "__main__":
    unittest.main()
