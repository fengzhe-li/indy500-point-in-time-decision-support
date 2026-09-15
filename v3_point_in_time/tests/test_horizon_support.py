"""Mandatory Phase 1 tests 4-5: horizon support boundary.

These tests exercise the REAL frozen FINAL_V2 artifacts (applicability
gate + adapter), because "which horizons are scientifically supported"
is a property of the frozen system itself, not of any synthetic
fixture.
"""
import unittest

import fixtures  # noqa: F401  (adds src/ to sys.path)

import applicability_gate
import final_v2_adapter


class HorizonSupportTests(unittest.TestCase):
    def test_4_h150_cannot_receive_production_inference(self):
        gate = applicability_gate.evaluate(
            horizon_min=150,
            current_track_temp_c=30.0,
            current_ambient_temp_c=22.0,
            forecast_future_ambient_temp_c=21.0,
        )
        self.assertEqual(gate.status, "OUT_OF_SUPPORT")

        # Defense in depth: even if a caller bypassed the gate, the
        # adapter itself has no frozen coefficients for h=150 and must
        # refuse rather than silently extrapolating.
        with self.assertRaises(KeyError):
            final_v2_adapter.infer(
                current_track_temp_c=30.0,
                current_ambient_temp_c=22.0,
                forecast_future_ambient_temp_c=21.0,
                decision_time="2020-08-15T12:00:00Z",
                target_time="2020-08-15T14:30:00Z",
                horizon_min=150,
                latitude_deg=39.7950,
                longitude_deg=-86.2348,
                random_seed=1,
                n_mc=200,
            )

    def test_5_h120_remains_supported(self):
        gate = applicability_gate.evaluate(
            horizon_min=120,
            current_track_temp_c=30.0,
            current_ambient_temp_c=22.0,
            forecast_future_ambient_temp_c=21.0,
        )
        self.assertEqual(gate.status, "SUPPORTED")

        output = final_v2_adapter.infer(
            current_track_temp_c=30.0,
            current_ambient_temp_c=22.0,
            forecast_future_ambient_temp_c=21.0,
            decision_time="2020-08-15T12:00:00Z",
            target_time="2020-08-15T14:00:00Z",
            horizon_min=120,
            latitude_deg=39.7950,
            longitude_deg=-86.2348,
            random_seed=1,
            n_mc=2000,
        )
        self.assertEqual(output.horizon_minutes, 120)
        self.assertTrue(-5.0 < output.expected_delta_v < 5.0)
        self.assertTrue(0.0 <= output.p_improve <= 1.0)
        self.assertLess(output.pi80_low, output.pi80_high)
        self.assertLess(output.pi90_low, output.pi90_high)

    def test_all_five_calibrated_anchors_supported(self):
        for h in (15, 30, 60, 90, 120):
            gate = applicability_gate.evaluate(
                horizon_min=h,
                current_track_temp_c=30.0,
                current_ambient_temp_c=22.0,
                forecast_future_ambient_temp_c=21.0,
            )
            self.assertEqual(gate.status, "SUPPORTED", msg=f"horizon {h} min")

    def test_zero_minute_is_current_state_boundary_not_supported(self):
        gate = applicability_gate.evaluate(
            horizon_min=0,
            current_track_temp_c=30.0,
            current_ambient_temp_c=22.0,
            forecast_future_ambient_temp_c=21.0,
        )
        self.assertEqual(gate.status, "OUT_OF_SUPPORT")


if __name__ == "__main__":
    unittest.main()
