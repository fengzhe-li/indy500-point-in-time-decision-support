"""Pydantic response models for the Phase 4 API.

Event/outlook/provenance/explanation payloads vary by event type (an
ABSTAINED horizon has different fields than a SUPPORTED one), so those
endpoints are typed as `dict` rather than forced into one rigid schema
-- forcing them into a single model would either lose information or
require optional fields on every variant, which is worse for frontend
clarity than a well-documented dict. Endpoints with a stable, uniform
shape (health, system status, case list, validation summary) get full
Pydantic models.
"""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str


class SystemStatusResponse(BaseModel):
    system: str
    scientific_core: str
    phase: str
    operating_mode: str
    supported_horizons_min: List[int]
    max_supported_horizon_min: int
    performance_model_status: str
    future_track_model_status: str
    queue_model: str
    opportunity_time_model: str
    strategy_recommendation: str
    historical_scoring_validation: str
    v2_integrity: str
    behavioural_regression: str
    phase3_freeze_status: str


class ReplayCaseSummary(BaseModel):
    case_id: str
    event_year: int
    car_or_entry_id: str
    category: str
    historical_scoring_status: str
    historical_scoring_anchor_horizon_min: Optional[int] = None
    realised_horizon_minutes: Optional[float] = None
    observed_delta_v: Optional[float] = None
    decision_time: Optional[str] = None
    event_count: int


class ValidationSummaryResponse(BaseModel):
    total_transitions_considered: int
    candidate_cases_with_replay_timeline: int
    conditional_inference_supported: int
    historical_scoring_formally_supported: int
    illustrative_only: int
    abstained_insufficient_timestamp: int
    abstained_out_of_support: int
    abstained_forecast_unavailable: int
    category_counts: dict
    abstention_reason_counts: dict
    phase3_freeze_status: str
    note: str


class ErrorResponse(BaseModel):
    detail: str


class ScenarioRequest(BaseModel):
    """Fields left Optional (rather than required-and-422-on-omission) so
    that a request missing a scientific input still reaches
    scenario_service, which fails closed to INPUT_INSUFFICIENT per
    horizon -- the same abstention-as-first-class-output pattern used
    everywhere else in this project, rather than a bare HTTP error."""

    current_track_temp_c: Optional[float] = None
    current_ambient_temp_c: Optional[float] = None
    forecast_future_ambient_temp_c: Optional[float] = None
    decision_time: Optional[str] = None
