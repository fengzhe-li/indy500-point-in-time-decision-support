"""Mandatory Phase 1 test 6: V3 does not alter frozen FINAL_V2 files.

This is a fast, in-process check that running the adapter (which reads
frozen files) never writes to them. The full, authoritative Step 11
before/after hash comparison across ALL identified frozen dependencies
is performed separately by
v3_point_in_time/scripts/run_v2_immutability_check.py and recorded in
v3_point_in_time/output/qa/v2_immutability_report.txt -- this test is a
narrower, quick regression guard that runs every time `make test` runs.
"""
import unittest

import fixtures  # noqa: F401  (adds src/ to sys.path)

import final_v2_adapter
from hashing import sha256_file


WATCHED_FROZEN_FILES = [
    final_v2_adapter.TRACK_COEF_FILE,
    final_v2_adapter.TRACK_RESID_FILE,
    final_v2_adapter.PERF_BOOT_FILE,
    final_v2_adapter.PERF_RESID_FILE,
    final_v2_adapter.MC_SCRIPT,
    final_v2_adapter.SOLAR_SCRIPT,
]


class V2ImmutabilityTests(unittest.TestCase):
    def test_6_running_the_adapter_does_not_alter_frozen_files(self):
        before = {str(p): sha256_file(p) for p in WATCHED_FROZEN_FILES}

        # Exercise the adapter across all five supported horizons --
        # the operation most likely to accidentally write output if the
        # adapter were implemented by calling the original script's
        # main() instead of reusing its pure functions.
        for h in (15, 30, 60, 90, 120):
            final_v2_adapter.infer(
                current_track_temp_c=28.0,
                current_ambient_temp_c=20.0,
                forecast_future_ambient_temp_c=19.0,
                decision_time="2020-08-15T12:00:00Z",
                target_time="2020-08-15T12:00:00Z",  # not used for gating here
                horizon_min=h,
                latitude_deg=39.7950,
                longitude_deg=-86.2348,
                random_seed=7,
                n_mc=500,
            )

        after = {str(p): sha256_file(p) for p in WATCHED_FROZEN_FILES}
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
