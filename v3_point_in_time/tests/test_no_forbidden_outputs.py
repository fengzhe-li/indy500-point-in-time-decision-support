"""Mandatory Phase 1 tests 9-10: no queue prediction, no RETAIN/WITHDRAW
recommendation is ever generated, anywhere in V3."""
import dataclasses
import re
import unittest
from pathlib import Path

import fixtures  # noqa: F401  (adds src/ to sys.path)

import scoring
from schemas import FinalV2Output, ShadowPrediction, DecisionSnapshot

SRC_DIR = Path(__file__).resolve().parents[1] / "src"

FORBIDDEN_PATTERNS = [
    r"\bretain\b",
    r"\bwithdraw\b",
    r"queue.?wait",
    r"P\s*\(\s*H\s*\|",  # P(H|...) style opportunity-probability estimate
    r"optimal.?wait",
]


class NoForbiddenOutputsTests(unittest.TestCase):
    def test_9_no_queue_prediction_field_or_logic_exists(self):
        # Structural check: none of the V3 output schemas carry a queue /
        # opportunity-probability field.
        for cls in (FinalV2Output, ShadowPrediction, DecisionSnapshot):
            field_names = {f.name.lower() for f in dataclasses.fields(cls)}
            for name in field_names:
                self.assertNotIn("queue", name)
                self.assertNotIn("opportunity_prob", name)

        # Source-scan: no V3 module computes P(H=h) / queue wait time.
        offenders = _scan_source_for_patterns([r"queue.?wait", r"P\s*\(\s*H\s*="])
        self.assertEqual(offenders, [], msg=f"Forbidden queue-model pattern found in: {offenders}")

    def test_10_no_retain_withdraw_recommendation_field_or_logic_exists(self):
        for cls in (FinalV2Output, ShadowPrediction, DecisionSnapshot):
            field_names = {f.name.lower() for f in dataclasses.fields(cls)}
            for name in field_names:
                self.assertNotIn("retain", name)
                self.assertNotIn("withdraw", name)
                self.assertNotIn("recommend", name)

        offenders = _scan_source_for_patterns([r"\bretain\b", r"\bwithdraw\b", r"\brecommend"])
        self.assertEqual(offenders, [], msg=f"Forbidden retain/withdraw pattern found in: {offenders}")

    def test_scoring_module_rejects_forbidden_strategy_labels(self):
        with self.assertRaises(ValueError):
            scoring.assert_no_forbidden_labels("this is the optimal waiting time")
        with self.assertRaises(ValueError):
            scoring.assert_no_forbidden_labels("withdraw value estimate")
        # A correctly-labelled description must pass without raising.
        scoring.assert_no_forbidden_labels(
            "expected physical-performance change conditional on another opportunity"
        )


ALLOW_MARKERS = (
    "FORBIDDEN", "forbidden", "MUST NOT", "must not", "does not", "never",
    "no queue", "No queue", "no RETAIN", "no retain",
    "predicts_queue_wait", "queue_wait_prediction",
)


def _scan_source_for_patterns(patterns, context_lines=6):
    """Flag a forbidden pattern unless it appears within a small context
    window that documents the prohibition (e.g. a module docstring
    listing forbidden labels, or a comment saying "never do X"). This
    lets scoring.py document/reject forbidden strategy labels without
    tripping the very scanner that checks no such logic exists."""
    offenders = []
    compiled = [re.compile(p, re.IGNORECASE) for p in patterns]
    for py_file in sorted(SRC_DIR.glob("*.py")):
        lines = py_file.read_text(encoding="utf-8").splitlines()
        for lineno, line in enumerate(lines, start=1):
            for pat in compiled:
                if not pat.search(line):
                    continue
                window = "\n".join(lines[max(0, lineno - 1 - context_lines): lineno])
                if any(marker in window for marker in ALLOW_MARKERS):
                    continue
                offenders.append(f"{py_file.name}:{lineno}: {line.strip()}")
    return offenders


if __name__ == "__main__":
    unittest.main()
