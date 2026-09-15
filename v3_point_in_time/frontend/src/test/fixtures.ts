import type {
  SystemStatus,
  ReplayCaseSummary,
  ReplayEvent,
  CaseOutlook,
  CaseScoring,
  ValidationSummary,
  AbstentionSummaryRow,
} from "../types/api";

export const systemStatus: SystemStatus = {
  system: "INDY 500 V3",
  scientific_core: "FINAL_V2",
  phase: "PHASE_4_APPLICATION",
  operating_mode: "HISTORICAL_SHADOW_RESEARCH_MODE",
  supported_horizons_min: [15, 30, 60, 90, 120],
  max_supported_horizon_min: 120,
  performance_model_status: "FROZEN",
  future_track_model_status: "FROZEN",
  queue_model: "NOT_MODELLED",
  opportunity_time_model: "NOT_MODELLED",
  strategy_recommendation: "NOT_ISSUED",
  historical_scoring_validation: "NOT_ESTABLISHED",
  v2_integrity: "PASS",
  behavioural_regression: "PASS",
  phase3_freeze_status: "V3_PHASE3_SHADOW_REPLAY_FROZEN",
};

export const cases: ReplayCaseSummary[] = [
  {
    case_id: "2021_car60",
    event_year: 2021,
    car_or_entry_id: "60",
    category: "ILLUSTRATIVE_ONLY",
    historical_scoring_status: "ILLUSTRATIVE_ONLY",
    historical_scoring_anchor_horizon_min: 60,
    realised_horizon_minutes: 64.13,
    observed_delta_v: 4.695,
    decision_time: "2021-05-22T17:58:16Z",
    event_count: 14,
  },
  {
    case_id: "2021_car18",
    event_year: 2021,
    car_or_entry_id: "18",
    category: "CONDITIONAL_OUTLOOK_SUPPORTED_BUT_HISTORICAL_SCORING_UNSUPPORTED",
    historical_scoring_status: "ABSTAINED",
    historical_scoring_anchor_horizon_min: null,
    realised_horizon_minutes: 288.0,
    observed_delta_v: 0.798,
    decision_time: "2021-05-22T16:19:56Z",
    event_count: 13,
  },
];

export const car60Events: ReplayEvent[] = [
  {
    event_id: "e1",
    event_year: 2021,
    event_time: "2021-05-22T17:58:16Z",
    event_type: "PHYSICAL_STATE_OBSERVED",
    car_or_entry_id: "60",
    decision_snapshot_id: null,
    prediction_id: null,
    information_cutoff: "2021-05-22T17:58:16Z",
    payload: { current_track_temp_c: 38.3, current_ambient_temp_c: 27.8 },
    provenance_ids: [],
    input_hash: "",
    event_hash: "h1",
    evaluation_status: "OK",
    abstention_reason_codes: [],
  },
  {
    event_id: "e2",
    event_year: 2021,
    event_time: "2021-05-22T17:58:16Z",
    event_type: "SHADOW_INFERENCE_ISSUED",
    car_or_entry_id: "60",
    decision_snapshot_id: "phase3:2021_car60",
    prediction_id: "phase3:2021_car60:h60",
    information_cutoff: "2021-05-22T17:58:16Z",
    payload: {
      horizon_minutes: 60,
      expected_delta_v: 0.0236,
      p_improve: 0.5217,
      pi80_low: -0.744,
      pi80_high: 0.798,
      applicability_status: "SUPPORTED",
      queue_time_prediction: "NOT MODELLED",
      retain_withdraw_recommendation: "NOT ISSUED",
    },
    provenance_ids: ["HRRR:x", "modelhash"],
    input_hash: "ih",
    event_hash: "h2",
    evaluation_status: "SUPPORTED",
    abstention_reason_codes: [],
  },
  {
    event_id: "e3",
    event_year: 2021,
    event_time: "2021-05-22T19:02:24Z",
    event_type: "PREDICTION_SCORED",
    car_or_entry_id: "60",
    decision_snapshot_id: "phase3:2021_car60",
    prediction_id: "phase3:2021_car60:h60",
    information_cutoff: "2021-05-22T19:02:24Z",
    payload: {
      anchor_horizon_minutes: 60,
      observed_delta_v: 4.695,
      expected_delta_v: 0.0236,
      counts_toward_aggregate_validation: false,
      note: "Approved ONLY as an illustrative diagnostic.",
    },
    provenance_ids: ["HRRR:x", "modelhash"],
    input_hash: "ih",
    event_hash: "h3",
    evaluation_status: "ILLUSTRATIVE_ONLY",
    abstention_reason_codes: ["NON_ANCHOR_EVALUATION_NOT_APPROVED"],
  },
];

export const car60Outlook: CaseOutlook = {
  case_id: "2021_car60",
  horizons: [15, 30, 60, 90, 120].map((h) => ({
    horizon_minutes: h,
    status: "SUPPORTED",
    prediction_id: `phase3:2021_car60:h${h}`,
    expected_delta_v: 0.02,
    median_delta_v: 0.02,
    p_improve: 0.5,
    pi80_low: -0.7,
    pi80_high: 0.8,
    pi90_low: -1.2,
    pi90_high: 1.2,
    applicability_status: "SUPPORTED",
    queue_time_prediction: "NOT MODELLED",
    retain_withdraw_recommendation: "NOT ISSUED",
  })),
  note: "If another opportunity occurs at h...",
};

export const car60Scoring: CaseScoring = {
  case_id: "2021_car60",
  status: "ILLUSTRATIVE_ONLY",
  counts_toward_aggregate_validation: false,
  anchor_horizon_minutes: 60,
  realised_horizon_minutes: 64.13,
  observed_delta_v: 4.695,
  expected_delta_v: 0.0236,
  absolute_error: 4.671,
  note: "Approved ONLY as an illustrative diagnostic (realised horizon ~64.1 min vs. the 60-min calibrated anchor).",
  prediction_id: "phase3:2021_car60:h60",
  abstention_reason_codes: ["NON_ANCHOR_EVALUATION_NOT_APPROVED"],
};

export const car18Scoring: CaseScoring = {
  case_id: "2021_car18",
  status: "ABSTAINED",
  counts_toward_aggregate_validation: false,
  realised_horizon_minutes: 288.0,
  note: "Realised horizon does not exactly match any calibrated anchor.",
  abstention_reason_codes: ["HORIZON_OUT_OF_SUPPORT"],
};

export const validationSummary: ValidationSummary = {
  total_transitions_considered: 41,
  candidate_cases_with_replay_timeline: 10,
  conditional_inference_supported: 9,
  historical_scoring_formally_supported: 0,
  illustrative_only: 1,
  abstained_insufficient_timestamp: 31,
  abstained_out_of_support: 0,
  abstained_forecast_unavailable: 0,
  category_counts: {
    CONDITIONAL_OUTLOOK_SUPPORTED_BUT_HISTORICAL_SCORING_UNSUPPORTED: 9,
    ILLUSTRATIVE_ONLY: 1,
    ABSTAINED_INSUFFICIENT_TIMESTAMP: 31,
  },
  abstention_reason_counts: {
    HORIZON_OUT_OF_SUPPORT: 9,
    INSUFFICIENT_ATTEMPT_TIMESTAMP: 31,
    NON_ANCHOR_EVALUATION_NOT_APPROVED: 1,
  },
  phase3_freeze_status: "V3_PHASE3_SHADOW_REPLAY_FROZEN",
  note: "Illustrative case is excluded from aggregate validation.",
};

export const abstentionRows: AbstentionSummaryRow[] = [
  { category: "REASON:INSUFFICIENT_ATTEMPT_TIMESTAMP", count: "31" },
  { category: "REASON:HORIZON_OUT_OF_SUPPORT", count: "9" },
];

export const representativeCase = {
  ...cases[1], // 2021_car18 stands in for the representative case in tests
  selection_reason: "Deterministic selection among 9 candidates; smallest total forecast target-time mismatch.",
};

export const scenarioSchema = {
  mode: "HYPOTHETICAL_SCENARIO",
  evidence_status: "NOT_HISTORICAL_EVIDENCE",
  fields: [
    { name: "current_track_temp_c", type: "float", required: true, unit: "degC" },
    { name: "current_ambient_temp_c", type: "float", required: true, unit: "degC" },
    { name: "forecast_future_ambient_temp_c", type: "float", required: true, unit: "degC", note: "USER-SUPPLIED HYPOTHETICAL FORECAST" },
    { name: "decision_time", type: "string (ISO-8601 UTC)", required: false },
  ],
  supported_horizons_min: [15, 30, 60, 90, 120],
  presets: {
    THERMALLY_STABLE: {
      label: "Thermally stable", current_track_temp_c: 35, current_ambient_temp_c: 27, forecast_future_ambient_temp_c: 27,
      kind: "DEMONSTRATION_PRESET", status: "HYPOTHETICAL", evidence_status: "NOT_HISTORICAL_EVIDENCE",
    },
  },
};

export const scenarioResponse = {
  scenario_id: "scenario-test-1",
  mode: "HYPOTHETICAL_SCENARIO" as const,
  evidence_status: "NOT_HISTORICAL_EVIDENCE" as const,
  input: {
    current_track_temp_c: 35,
    current_ambient_temp_c: 27,
    forecast_future_ambient_temp_c: 29,
    forecast_label: "USER-SUPPLIED HYPOTHETICAL FORECAST",
    forecast_provenance: "NONE -- not tied to any real forecast vintage",
    decision_time: "2026-05-22T17:00:00Z",
  },
  supported_horizons_min: [15, 30, 60, 90, 120],
  horizons: [15, 30, 60, 90, 120].map((h) => ({
    horizon_minutes: h,
    status: "SUPPORTED",
    target_time: "2026-05-22T18:00:00Z",
    expected_delta_v: 0.05,
    median_delta_v: 0.05,
    p_improve: 0.5,
    pi80_low: -0.7,
    pi80_high: 0.8,
    pi90_low: -1.2,
    pi90_high: 1.2,
    mc_sd: 0.6,
    conditional_physical_opportunity_value: 0.05,
  })),
  model_version: "FINAL_V2",
  model_hash: "abcdef1234567890",
  input_hash: "1234567890abcdef",
  queue_time_prediction: "NOT MODELLED",
  retain_withdraw_recommendation: "NOT ISSUED",
  note: "If another opportunity occurs at horizon h -- this is an ephemeral hypothetical conditional physical outlook.",
  created_at: "2026-05-22T17:00:00Z",
};
