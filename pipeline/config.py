from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence"
OUTPUT = ROOT / "data" / "canonical" / "v1"
HRRR_NUMERIC_INPUT = ROOT / "weather" / "output" / "hrrr_ims_2020_2024_features.csv"
YEARS = (2020, 2021, 2022, 2023, 2024)
RUN_RECORDED_AT = "2026-09-08T00:00:00Z"
NAMESPACE = "2d0d1264-078f-4a5e-9011-51bd78373e4d"

RESULT_INPUT = {
    2020: ("json", "official_session_2020.json"),
    2021: ("json", "official_session_2021.json"),
    2022: ("json", "official_session_2022.json"),
    2023: ("pdf", "results_2023_1.pdf"),
    2024: ("pdf", "results_2024_0.pdf"),
}
SECTION_INPUT = {year: f"section_{year}.pdf" for year in YEARS}
TIMING_INPUT = {
    2020: ("timing71_2020_part1.zip", "timing71_2020_part2.zip"),
    2021: ("timing71_2021_sample.zip",),
    2022: (),
    2023: ("timing71_2023.zip",),
    2024: ("timing71_2024.zip",),
}
KNOWN_GAPS = {
    2020: ("2020-08-15T18:35:15Z", "2020-08-15T18:42:30Z", "KNOWN_INTERNAL_7M15S_GAP"),
    2023: (None, None, "KNOWN_TERMINAL_APPROX_58M38S_GAP"),
}
CORE_PERFORMANCE_YEARS = {2020, 2021, 2023, 2024}

TABLE_FIELDS = {
    "qualifying_events": ["session_id", "year", "official_session_id", "event_name", "session_name", "event_date", "local_timezone", "scheduled_start_utc", "scheduled_end_utc", "actual_start_utc", "actual_end_utc", "chronology_reconciliation_status", "year_policy_version"],
    "attempts": ["attempt_id", "session_id", "entry_key", "car_number", "driver_name", "team_name", "car_attempt_index", "attempt_key", "car_attempt_order_quality", "global_order_lower_bound", "global_order_upper_bound", "attempt_class", "official_status_raw", "result_status", "outcome_label", "result_counted_at_session_end", "four_lap_total_seconds", "four_lap_average_speed_mph", "start_time_utc", "end_time_utc", "event_time_lower_utc", "event_time_upper_utc", "event_time_quality", "time_basis", "withdrawal_evidence", "lane_action", "lane_evidence", "requeue_evidence", "fuel_strategy_class", "source_native_locator"],
    "attempt_laps": ["attempt_lap_id", "attempt_id", "source_report_lap_index", "lap_number", "lap_completion_status", "lap_time_seconds", "lap_speed_mph", "reconstruction_rule_id", "reconstruction_validation_status"],
    "attempt_sections": ["attempt_section_id", "attempt_id", "attempt_lap_id", "source_report_lap_index", "source_report_lap_time_seconds", "lap_number", "section_set_version", "section_lap_coverage_status", "section_sequence_index", "section_name", "start_timing_point", "end_timing_point", "section_time_seconds", "section_speed_mph", "full_lap_coverage_member"],
    "chronology_events": ["chronology_event_id", "session_id", "attempt_id", "entry_key", "event_type", "event_time_utc", "event_time_lower_utc", "event_time_upper_utc", "event_time_quality", "time_basis", "event_order_lower_bound", "event_order_upper_bound", "withdrawal_evidence", "requeue_evidence", "lane_action", "lane_evidence", "queue_state_evidence", "queue_fact_text", "event_payload_json"],
    "chronology_constraints": ["chronology_constraint_id", "session_id", "attempt_id", "entry_key", "car_number", "driver_name", "car_attempt_index", "result_status", "timing71_capture_event_id", "capture_time_utc", "anchor_event_type", "anchor_time_utc", "anchor_time_lower_utc", "anchor_time_upper_utc", "timed_run_duration_seconds", "duration_coverage", "timed_run_start_utc", "timed_run_end_utc", "timed_run_start_lower_utc", "timed_run_start_upper_utc", "timed_run_end_lower_utc", "timed_run_end_upper_utc", "event_time_quality", "value_classification", "anchor_source_id", "anchor_evidence_item_id", "reconciliation_status", "ordering_constraints_json", "unresolved_reason", "uncertainty_note"],
    "forecast_snapshots": ["forecast_snapshot_id", "session_id", "source_id", "provider", "model_name", "model_version", "issue_time_utc", "availability_time_utc", "availability_time_quality", "valid_start_utc", "valid_end_utc", "forecast_lead_hours", "location_type", "spatial_locator", "latitude", "longitude", "extraction_metadata_json"],
    "weather_forecasts": ["weather_forecast_value_id", "forecast_snapshot_id", "variable_code", "value_numeric", "value_text", "unit"],
    "sources": ["source_id", "source_name", "source_type", "evidence_quality", "source_priority_rank", "source_uri", "content_hash", "retrieved_at_utc", "coverage_note"],
    "evidence_items": ["evidence_item_id", "source_id", "source_native_locator", "captured_value_text", "source_timestamp_utc", "source_timestamp_basis", "review_note"],
    "field_evidence_links": ["field_evidence_link_id", "entity_table", "entity_id", "field_name", "evidence_item_id", "value_classification", "is_primary", "conflict_disposition", "derivation_rule_id", "derivation_rule_version", "input_lineage_json", "input_entity_field_refs_json", "input_snapshot_hash", "uncertainty_note", "reviewer_id", "recorded_at_utc"],
    "row_eligibility": ["entity_type", "entity_id", "analysis_target", "ruleset_version", "eligible", "eligible_core_training", "supporting_only", "robustness_only", "reason_codes", "evaluated_at_utc"],
    "decision_state_features": ["decision_state_id", "session_id", "subject_entry_key", "subject_attempt_id", "state_as_of_time_utc", "state_order_boundary", "current_best_average_speed_mph", "current_best_total_seconds", "provisional_rank_before", "top12_cutoff_speed_mph", "bump_cutoff_speed_mph", "margin_to_top12_mph", "margin_to_bump_cutoff_mph", "session_elapsed_seconds", "session_remaining_seconds", "prior_observed_attempt_count", "most_recent_attempt_time_utc", "seconds_since_prior_attempt", "forecast_snapshot_id", "leaderboard_state_complete", "chronology_complete_through_state", "queue_state_qualitative", "queue_state_evidence", "derivation_rule_version", "input_lineage_hash"],
}
