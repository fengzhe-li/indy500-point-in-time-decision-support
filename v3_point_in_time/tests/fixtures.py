"""Shared test fixtures. Not a test module itself (no test_ prefix, so
unittest discovery in the parent repo's `Makefile` `make test` target,
which globs `test_*.py`, never picks this file up).

SYNTHETIC_TEST_FIXTURE below is clearly labelled and used ONLY to test
software behaviour (leakage rejection, hashing, horizon gating). It is
never passed through final_v2_adapter in a way that could be mistaken
for a scientific evaluation result -- see test_no_future_leakage.py's
own docstring for how each test uses it.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from schemas import ForecastVintage  # noqa: E402

SYNTHETIC_TEST_FIXTURE_LABEL = "SYNTHETIC_TEST_FIXTURE"


def make_synthetic_forecast(
    forecast_id: str,
    issue_time: str,
    valid_time: str,
    ambient_temp_c: float,
    lead_minutes: float = 60.0,
) -> ForecastVintage:
    """A clearly-labelled synthetic forecast vintage for software tests
    only. source="SYNTHETIC_TEST_FIXTURE" makes this unmistakable in any
    provenance record it ends up in."""
    return ForecastVintage(
        forecast_id=forecast_id,
        source=SYNTHETIC_TEST_FIXTURE_LABEL,
        model_name="SYNTHETIC",
        model_run="0",
        issue_time=issue_time,
        retrieved_at=None,
        valid_time=valid_time,
        lead_minutes=lead_minutes,
        ambient_temp_c=ambient_temp_c,
        source_uri="synthetic://test-fixture",
        source_hash="",
    )


# A real, non-fabricated historical decision point sourced from the
# frozen project's own future-track sample file (see
# existing_system_inventory.md section 4). Used only by tests/CLI code
# that explicitly wants a genuine historical case; kept here so tests
# don't need to re-derive it.
REAL_DEMO_DECISION_TIME = "2020-08-15T12:15:00Z"
REAL_DEMO_CURRENT_TRACK_TEMP_C = 26.666667
REAL_DEMO_CURRENT_AMBIENT_TEMP_C = 21.111111
REAL_DEMO_EVENT_YEAR = 2020
REAL_DEMO_CAR_OR_ENTRY_ID = "PTSC_SAMPLE_2020_DAY1_ROW000"
