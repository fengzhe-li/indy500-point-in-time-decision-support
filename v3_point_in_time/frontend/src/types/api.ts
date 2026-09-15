// Types mirror the FastAPI response shapes exactly (see api/models.py and
// app/*.py). The frontend never computes any of these values -- it only
// renders whatever the API returns.

export interface SystemStatus {
  system: string;
  scientific_core: string;
  phase: string;
  operating_mode: string;
  supported_horizons_min: number[];
  max_supported_horizon_min: number;
  performance_model_status: string;
  future_track_model_status: string;
  queue_model: string;
  opportunity_time_model: string;
  strategy_recommendation: string;
  historical_scoring_validation: string;
  v2_integrity: "PASS" | "FAIL" | "UNKNOWN";
  behavioural_regression: "PASS" | "FAIL" | "UNKNOWN";
  phase3_freeze_status: string;
}

export interface ReplayCaseSummary {
  case_id: string;
  event_year: number;
  car_or_entry_id: string;
  category: string;
  historical_scoring_status: string;
  historical_scoring_anchor_horizon_min: number | null;
  realised_horizon_minutes: number | null;
  observed_delta_v: number | null;
  decision_time: string | null;
  event_count: number;
}

export interface ReplayEvent {
  event_id: string;
  event_year: number;
  event_time: string;
  event_type: string;
  car_or_entry_id: string;
  decision_snapshot_id: string | null;
  prediction_id: string | null;
  information_cutoff: string;
  payload: Record<string, unknown>;
  provenance_ids: string[];
  input_hash: string;
  event_hash: string;
  evaluation_status: string;
  abstention_reason_codes: string[];
}

export interface OutlookHorizon {
  horizon_minutes: number;
  status: string; // e.g. SUPPORTED / ABSTAINED / NOT_EVALUATED / OUT_OF_SUPPORT / INPUT_INSUFFICIENT (scenario reuses this shape)
  prediction_id?: string;
  expected_delta_v?: number;
  median_delta_v?: number;
  p_improve?: number;
  pi80_low?: number;
  pi80_high?: number;
  pi90_low?: number;
  pi90_high?: number;
  applicability_status?: string;
  queue_time_prediction?: string;
  retain_withdraw_recommendation?: string;
  abstention_reason_codes?: string[];
}

export interface CaseOutlook {
  case_id: string;
  horizons: OutlookHorizon[];
  note: string;
}

export interface CaseScoring {
  case_id: string;
  status: string;
  counts_toward_aggregate_validation: boolean;
  anchor_horizon_minutes?: number | null;
  realised_horizon_minutes?: number | null;
  observed_delta_v?: number | null;
  expected_delta_v?: number | null;
  absolute_error?: number | null;
  note?: string | null;
  prediction_id?: string | null;
  abstention_reason_codes?: string[];
}

export interface PredictionDetail {
  prediction_id: string;
  case_id: string | null;
  decision_snapshot_id: string;
  information_cutoff: string;
  horizon_minutes: number;
  inference_support: string;
  historical_scoring_support: string;
  outlook: {
    expected_delta_v: number;
    median_delta_v: number;
    p_improve: number;
    pi80_low: number;
    pi80_high: number;
    pi90_low: number;
    pi90_high: number;
  };
  queue_time_prediction: string;
  retain_withdraw_recommendation: string;
}

export interface PredictionProvenance {
  prediction_id: string;
  decision_snapshot_id: string;
  information_cutoff: string;
  forecast_vintage_id: string | null;
  forecast_issue_time: string | null;
  forecast_valid_time: string | null;
  forecast_target_time_error_minutes: number | null;
  forecast_ambient_temp_c: number | null;
  final_v2_model_hash: string | null;
  input_hash: string;
  prediction_hash_note: string;
  scientific_support: string;
  historical_scoring_support: string;
}

export interface PredictionExplanation {
  prediction_id: string;
  current_track_to_ambient_thermal_gap_c: number | null;
  forecast_ambient_trajectory_c: {
    current_ambient_temp_c: number;
    forecast_future_ambient_temp_c: number;
    delta_ambient_temp_c: number;
  } | null;
  predicted_future_track_temperature_change_c: number | null;
  solar_elevation_mean_deg: number | null;
  note: string | null;
  uncertainty_source_reference: Record<string, unknown>;
}

export interface ValidationSummary {
  total_transitions_considered: number;
  candidate_cases_with_replay_timeline: number;
  conditional_inference_supported: number;
  historical_scoring_formally_supported: number;
  illustrative_only: number;
  abstained_insufficient_timestamp: number;
  abstained_out_of_support: number;
  abstained_forecast_unavailable: number;
  category_counts: Record<string, number>;
  abstention_reason_counts: Record<string, number>;
  phase3_freeze_status: string;
  note: string;
}

export interface AbstentionSummaryRow {
  category: string;
  count: string;
}

export interface RepresentativeCase extends ReplayCaseSummary {
  selection_reason: string;
}

export interface ScenarioRequest {
  current_track_temp_c?: number;
  current_ambient_temp_c?: number;
  forecast_future_ambient_temp_c?: number;
  decision_time?: string;
}

export interface ScenarioHorizonResult {
  horizon_minutes: number;
  status: string;
  reasons?: string[];
  target_time?: string;
  expected_delta_v?: number;
  median_delta_v?: number;
  p_improve?: number;
  pi80_low?: number;
  pi80_high?: number;
  pi90_low?: number;
  pi90_high?: number;
  mc_sd?: number;
  conditional_physical_opportunity_value?: number;
}

export interface ScenarioResponse {
  scenario_id: string;
  mode: "HYPOTHETICAL_SCENARIO";
  evidence_status: "NOT_HISTORICAL_EVIDENCE";
  input: {
    current_track_temp_c: number | null;
    current_ambient_temp_c: number | null;
    forecast_future_ambient_temp_c: number | null;
    forecast_label: string;
    forecast_provenance: string;
    decision_time: string;
  };
  supported_horizons_min: number[];
  horizons: ScenarioHorizonResult[];
  model_version: string;
  model_hash: string;
  input_hash: string;
  queue_time_prediction: string;
  retain_withdraw_recommendation: string;
  note: string;
  created_at: string;
}

export interface ScenarioPreset {
  label: string;
  current_track_temp_c: number;
  current_ambient_temp_c: number;
  forecast_future_ambient_temp_c: number;
  kind: string;
  status: string;
  evidence_status: string;
}

export interface ScenarioSchema {
  mode: string;
  evidence_status: string;
  fields: { name: string; type: string; required: boolean; unit?: string; note?: string }[];
  supported_horizons_min: number[];
  presets: Record<string, ScenarioPreset>;
}
