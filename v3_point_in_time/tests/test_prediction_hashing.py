"""Mandatory Phase 1 tests 7-8: provenance/input/prediction hashing.

Updated for the Phase 2 single-source-of-truth forecast-selection fix:
forecast selection now happens once, in select_and_build_snapshot, and
is baked into the snapshot's own selected_forecast_ids / input_hash.
Using a different forecast vintage necessarily means building a
different snapshot -- there is no longer a way to swap a forecast under
an already-built snapshot (see test_provenance_mismatch_is_a_hard_failure).

Uses SYNTHETIC_TEST_FIXTURE forecasts so the test is fast and does not
depend on which real HRRR rows happen to exist -- hashing behaviour is
a software property, not a scientific claim.
"""
import tempfile
import unittest
from pathlib import Path

from fixtures import make_synthetic_forecast

from forecast_vintage_store import ForecastVintageStore
import shadow_engine

DECISION_TIME = "2020-08-15T12:00:00Z"
TARGET_TIME = "2020-08-15T13:00:00Z"  # decision_time + 60 min


def _store(ambient_temp_c: float, forecast_id: str = "f-hash-test"):
    store = ForecastVintageStore()
    store.add(make_synthetic_forecast(
        forecast_id, issue_time=DECISION_TIME, valid_time=TARGET_TIME, ambient_temp_c=ambient_temp_c,
    ))
    return store


def _snapshot_and_selection(snapshot_id: str, store: ForecastVintageStore):
    snapshot, guard, selections = shadow_engine.select_and_build_snapshot(
        store=store,
        snapshot_id=snapshot_id,
        event_year=2020,
        car_or_entry_id="SYNTHETIC_CAR",
        decision_time=DECISION_TIME,
        current_track_temp_c=28.0,
        current_ambient_temp_c=20.0,
        current_track_temp_known_at=DECISION_TIME,
        current_ambient_temp_known_at=DECISION_TIME,
        horizons_min=[60],
    )
    assert guard.passed
    return snapshot, selections


class PredictionHashingTests(unittest.TestCase):
    def test_7_identical_snapshot_and_forecast_produce_identical_hashes(self):
        store_a = _store(ambient_temp_c=19.5)
        store_b = _store(ambient_temp_c=19.5)  # separate store, identical content
        snapshot_a, sel_a = _snapshot_and_selection("hash-test", store_a)
        snapshot_b, sel_b = _snapshot_and_selection("hash-test", store_b)
        self.assertEqual(snapshot_a.input_hash, snapshot_b.input_hash)
        self.assertEqual(snapshot_a.selected_forecast_ids, snapshot_b.selected_forecast_ids)

        with tempfile.TemporaryDirectory() as d1, tempfile.TemporaryDirectory() as d2:
            result_a = shadow_engine.run_single_horizon(
                snapshot_a, 60, sel_a[60]["vintage"], 39.7950, -86.2348, random_seed=42, n_mc=1000, output_dir=Path(d1),
            )
            result_b = shadow_engine.run_single_horizon(
                snapshot_b, 60, sel_b[60]["vintage"], 39.7950, -86.2348, random_seed=42, n_mc=1000, output_dir=Path(d2),
            )
            self.assertEqual(result_a.status, "OK")
            self.assertEqual(result_b.status, "OK")
            self.assertEqual(result_a.prediction.prediction_hash, result_b.prediction.prediction_hash)
            self.assertEqual(result_a.prediction.expected_delta_v, result_b.prediction.expected_delta_v)
            # Provenance identity, per Step 5: snapshot declares it, the vintage
            # actually used matches it, and the persisted prediction matches both.
            self.assertEqual(result_a.prediction.forecast_vintage_ids, snapshot_a.selected_forecast_ids)

    def test_8_changing_forecast_vintage_changes_the_hash(self):
        # A different forecast means a different snapshot (Step 5: selection
        # happens once, before the snapshot exists) -- there are necessarily
        # two distinct snapshots here, not one snapshot reused with a swap.
        snapshot_a, sel_a = _snapshot_and_selection(
            "hash-test-vary-a", _store(ambient_temp_c=19.5, forecast_id="f-hash-test-a"))
        snapshot_b, sel_b = _snapshot_and_selection(
            "hash-test-vary-b", _store(ambient_temp_c=25.0, forecast_id="f-hash-test-b"))

        self.assertNotEqual(snapshot_a.input_hash, snapshot_b.input_hash)
        self.assertNotEqual(snapshot_a.selected_forecast_ids, snapshot_b.selected_forecast_ids)

        with tempfile.TemporaryDirectory() as d1, tempfile.TemporaryDirectory() as d2:
            result_a = shadow_engine.run_single_horizon(
                snapshot_a, 60, sel_a[60]["vintage"], 39.7950, -86.2348, random_seed=42, n_mc=1000, output_dir=Path(d1),
            )
            result_b = shadow_engine.run_single_horizon(
                snapshot_b, 60, sel_b[60]["vintage"], 39.7950, -86.2348, random_seed=42, n_mc=1000, output_dir=Path(d2),
            )
            self.assertEqual(result_a.status, "OK")
            self.assertEqual(result_b.status, "OK")
            self.assertNotEqual(result_a.prediction.prediction_hash, result_b.prediction.prediction_hash)
            self.assertNotEqual(result_a.prediction.expected_delta_v, result_b.prediction.expected_delta_v)

    def test_provenance_mismatch_is_a_hard_failure(self):
        """Passing a vintage that was NOT the one selected for this
        snapshot must raise, never silently proceed (Step 5)."""
        snapshot_a, sel_a = _snapshot_and_selection(
            "mismatch-test", _store(ambient_temp_c=19.5, forecast_id="f-mismatch-a"))
        _, sel_other = _snapshot_and_selection(
            "mismatch-test-other", _store(ambient_temp_c=99.0, forecast_id="f-mismatch-b"))

        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(shadow_engine.ForecastProvenanceMismatch):
                shadow_engine.run_single_horizon(
                    snapshot_a, 60, sel_other[60]["vintage"], 39.7950, -86.2348,
                    random_seed=1, n_mc=200, output_dir=Path(d),
                )

    def test_shadow_predictions_are_append_only(self):
        snapshot, sel = _snapshot_and_selection("append-only-test", _store(ambient_temp_c=19.5))
        with tempfile.TemporaryDirectory() as d:
            r1 = shadow_engine.run_single_horizon(
                snapshot, 60, sel[60]["vintage"], 39.7950, -86.2348, random_seed=1, n_mc=200, output_dir=Path(d),
            )
            self.assertEqual(r1.status, "OK")
            with self.assertRaises(FileExistsError):
                shadow_engine._write_append_only(Path(d), r1.prediction)


if __name__ == "__main__":
    unittest.main()
