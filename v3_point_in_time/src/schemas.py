"""Formal data contracts for the V3 point-in-time layer.

Nothing here changes any FINAL_V2 semantics. These are Phase 1 records
for: a forecast vintage, an immutable decision snapshot, and an
immutable shadow prediction. Field names for physical-state variables
follow the existing project's own naming
(`track_temp_c`, `ambient_temp_c`, `thermal_gap_0_c`,
`solar_elevation_mean_deg`) so V3 does not invent incompatible
duplicate identifiers for concepts the project already names.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional


# ---------------------------------------------------------------------------
# Evaluation mode
# ---------------------------------------------------------------------------

class EvaluationMode(str, Enum):
    """FINAL_V2 did not exist during historical qualifying sessions.

    RETROSPECTIVE_POINT_IN_TIME_INPUTS means: the modern frozen model is
    retrospectively evaluated using only input information that would
    have been available at the historical decision time. It is never
    used to claim the model was deployed live in the past.
    """

    RETROSPECTIVE_POINT_IN_TIME_INPUTS = "RETROSPECTIVE_POINT_IN_TIME_INPUTS"
    SYNTHETIC_SOFTWARE_TEST = "SYNTHETIC_SOFTWARE_TEST"


class ApplicabilityStatus(str, Enum):
    SUPPORTED = "SUPPORTED"
    CAUTION = "CAUTION"
    OUT_OF_SUPPORT = "OUT_OF_SUPPORT"
    INPUT_INSUFFICIENT = "INPUT_INSUFFICIENT"


# ---------------------------------------------------------------------------
# Step 2 — forecast vintage schema
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ForecastVintage:
    forecast_id: str
    source: str
    model_name: str
    model_run: str
    issue_time: str          # ISO-8601 UTC; nominal model-run / cycle time
    retrieved_at: Optional[str]
    valid_time: str          # ISO-8601 UTC; the timestamp the forecast is FOR
    lead_minutes: float

    ambient_temp_c: Optional[float] = None
    solar_or_radiation: Optional[float] = None
    wind_speed: Optional[float] = None
    wind_gust: Optional[float] = None
    cloud_cover: Optional[float] = None
    pressure: Optional[float] = None

    source_uri: str = ""
    source_hash: str = ""

    # Provenance / QA extras (not part of the "at minimum" list, but required
    # to make forecast selection auditable per the Step 3 provenance rule).
    availability_time: Optional[str] = None
    availability_time_quality: str = "UNKNOWN"

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Step 5 — decision snapshot
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DecisionSnapshot:
    snapshot_id: str
    event_year: int
    car_or_entry_id: str
    decision_time: str  # ISO-8601 UTC

    current_official_speed: Optional[float]
    current_track_temp_c: float
    current_ambient_temp_c: float

    selected_forecast_ids: tuple  # one per requested horizon
    information_cutoff: str  # ISO-8601 UTC; == decision_time unless tightened

    evaluation_mode: str  # EvaluationMode value

    # known_at provenance for the leakage guard (Step 4)
    current_official_speed_known_at: Optional[str]
    current_track_temp_known_at: str
    current_ambient_temp_known_at: str

    input_hash: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Step 6 — FINAL_V2 adapter output (per horizon)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class FinalV2Output:
    horizon_minutes: int
    expected_delta_v: float
    median_delta_v: float
    p_improve: float
    pi80_low: float
    pi80_high: float
    pi90_low: float
    pi90_high: float
    mc_sd: float

    # explicit mapping documentation (Step 6: "if names differ, map explicitly")
    source_field_mapping: dict = field(default_factory=lambda: {
        "expected_delta_v": "expected_delta_speed_mph",
        "median_delta_v": "median_delta_speed_mph",
        "p_improve": "p_improve",
        "pi80_low": "lower_80_mph",
        "pi80_high": "upper_80_mph",
        "pi90_low": "lower_90_mph",
        "pi90_high": "upper_90_mph",
        "mc_sd": "mc_sd_mph",
    })

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Step 8 — immutable shadow prediction record
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ShadowPrediction:
    prediction_id: str
    snapshot_id: str
    decision_time: str
    event_year: int
    car_or_entry_id: str

    forecast_vintage_ids: tuple

    model_version: str
    model_hash: str

    horizon_minutes: int

    expected_delta_v: float
    median_delta_v: float
    p_improve: float

    pi80_low: float
    pi80_high: float
    pi90_low: float
    pi90_high: float

    applicability_status: str

    input_hash: str
    prediction_hash: str

    created_at: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class GuardResult:
    passed: bool
    reasons: tuple  # machine-readable reason codes; empty when passed

    def to_dict(self) -> dict:
        return asdict(self)


POINT_IN_TIME_VIOLATION = "POINT_IN_TIME_VIOLATION"


# ---------------------------------------------------------------------------
# Phase 3 Step 2 — replay event schema
# ---------------------------------------------------------------------------

REPLAY_EVENT_TYPES = (
    "ATTEMPT_COMPLETED",
    "CURRENT_RESULT_UPDATED",
    "PHYSICAL_STATE_OBSERVED",
    "FORECAST_AVAILABLE",
    "SHADOW_INFERENCE_ISSUED",
    "SHADOW_INFERENCE_ABSTAINED",
    "FUTURE_ATTEMPT_OBSERVED",
    "PREDICTION_SCORED",
    "APPLICABILITY_CHANGED",
)

# Phase 3 Step 5 — machine-readable abstention reason codes. Only codes
# actually produced by replay_engine.py are used; this tuple is the
# closed vocabulary (no ad hoc string reasons elsewhere).
ABSTENTION_REASON_CODES = (
    "INSUFFICIENT_ATTEMPT_TIMESTAMP",
    "INSUFFICIENT_CURRENT_STATE",
    "NO_VALID_FORECAST_VINTAGE",
    "POINT_IN_TIME_VIOLATION",
    "HORIZON_OUT_OF_SUPPORT",
    "NON_ANCHOR_EVALUATION_NOT_APPROVED",
    "MISSING_REQUIRED_FORECAST_INPUT",
    "REGIME_APPLICABILITY_UNRESOLVED",
    "PROVENANCE_MISMATCH",
)

# Phase 3 Step 10 — smallest defensible case-category set.
REPLAY_CASE_CATEGORIES = (
    "FULL_SHADOW_INFERENCE_SUPPORTED",
    "CONDITIONAL_OUTLOOK_SUPPORTED_BUT_HISTORICAL_SCORING_UNSUPPORTED",
    "ILLUSTRATIVE_ONLY",
    "ABSTAINED_INSUFFICIENT_TIMESTAMP",
    "ABSTAINED_OUT_OF_SUPPORT",
    "ABSTAINED_FORECAST_UNAVAILABLE",
)


@dataclass(frozen=True)
class ReplayEvent:
    """An immutable, hashable record of one step in a historical replay.

    `event_hash` is computed over every other field (via
    hashing.sha256_obj on to_dict() with event_hash excluded) so that
    replaying the same case twice is verifiable at the hash level
    (Phase 3 test 13). `payload` carries event-type-specific data (a
    conditional outlook, an abstention detail, a scored comparison,
    ...) so this one schema serves every event type in
    REPLAY_EVENT_TYPES without inventing a parallel per-type schema.
    """

    event_id: str
    event_year: int
    event_time: str  # ISO-8601 UTC
    event_type: str  # one of REPLAY_EVENT_TYPES
    car_or_entry_id: str

    decision_snapshot_id: Optional[str]
    prediction_id: Optional[str]

    information_cutoff: str  # ISO-8601 UTC

    payload: dict

    provenance_ids: tuple  # forecast_id(s), frozen-artifact hashes, etc.
    input_hash: str
    event_hash: str

    evaluation_status: str  # e.g. SUPPORTED / ILLUSTRATIVE_ONLY / ABSTAINED / OK
    abstention_reason_codes: tuple  # subset of ABSTENTION_REASON_CODES; empty if none

    def to_dict(self) -> dict:
        return asdict(self)
