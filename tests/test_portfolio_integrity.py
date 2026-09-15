import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PortfolioIntegrityTests(unittest.TestCase):
    def test_readme_images_exist(self):
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        all_refs = re.findall(r"!\[[^]]*\]\(([^)]+)\)", text)
        # Remote badges (e.g. GitHub Actions status badges) are not local
        # figure files and are not expected to resolve on disk.
        refs = [ref for ref in all_refs if not ref.startswith(("http://", "https://"))]
        self.assertGreaterEqual(len(refs), 12)
        self.assertEqual([], [ref for ref in refs if not (ROOT / ref).is_file()])

    def test_external_validation_scope(self):
        path = ROOT / "r6_regime_extension/output/external_regime_inference_backtest_2025_v2/external_regime_inference_backtest_2025_metrics_v2.json"
        metrics = json.loads(path.read_text())
        self.assertEqual(15, metrics["extended_validation"]["n"])
        self.assertEqual(4, metrics["product_subset"]["n"])
        self.assertFalse(metrics["queue_wait_prediction"])
        self.assertFalse(metrics["strategy_recommendation"])

    def test_operational_curve_boundary(self):
        path = ROOT / "weather/output/operational_curve_v2/operational_curve_metadata_v2.json"
        metadata = json.loads(path.read_text())
        self.assertEqual([15, 30, 60, 90, 120], metadata["validated_anchor_horizons_min"])
        self.assertFalse(metadata["extrapolation_above_120"])
        self.assertFalse(metadata["queue_wait_prediction"])


if __name__ == "__main__":
    unittest.main()

