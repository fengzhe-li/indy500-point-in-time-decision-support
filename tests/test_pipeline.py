import unittest
from collections import Counter
from copy import deepcopy

from pipeline.reconcile import build
from pipeline.validation import section_validation, chronology_reconciliation, _chronology_status
from pipeline.eligibility import assign
from pipeline.chronology_2024 import golden_checks, propagate_time_quality
from pipeline.parsers import weather
from pipeline.config import HRRR_NUMERIC_INPUT

class PipelineGoldenTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tables, cls.issues, cls.parsers = build()
        cls.section_rows = section_validation(cls.tables)
        cls.chronology_rows, cls.statuses = chronology_reconciliation(cls.tables)
        assign(cls.tables)

    def test_attempt_identity_unique_and_attempt_key_conditional(self):
        ids=[a["attempt_id"] for a in self.tables["attempts"]]
        self.assertEqual(len(ids),len(set(ids)))
        for attempt in self.tables["attempts"]:
            self.assertEqual(attempt["attempt_key"] is not None, attempt["car_attempt_index"] is not None)

    def test_four_lap_integrity_and_no_zero_fill(self):
        counts=Counter(l["attempt_id"] for l in self.tables["attempt_laps"] if l["lap_completion_status"]=="COMPLETE")
        for attempt in self.tables["attempts"]:
            if attempt["attempt_class"]=="A_COMPLETE": self.assertEqual(counts[attempt["attempt_id"]],4)
            if attempt["attempt_class"]=="B_PARTIAL_COMPLETE_LAPS": self.assertLess(counts[attempt["attempt_id"]],4)
        self.assertFalse(any(l["lap_time_seconds"]==0 for l in self.tables["attempt_laps"]))

    def test_source_report_index_is_distinct_from_attempt_lap(self):
        sato_lap8=[l for l in self.tables["attempt_laps"] if l["source_report_lap_index"]==8 and any(a["attempt_id"]==l["attempt_id"] and a["car_number"]=="51" and a["session_id"].endswith("2022") for a in self.tables["attempts"])]
        self.assertEqual(len(sato_lap8),1)
        self.assertEqual(sato_lap8[0]["lap_number"],3)

    def test_section_rules_are_format_specific_and_complete_only(self):
        self.assertTrue(any(r["validation_pass"] for r in self.section_rows))
        self.assertTrue(any(not r["validation_pass"] for r in self.section_rows))
        self.assertEqual({r["section_set_version"] for r in self.section_rows},{"SECTION_SET_2020_2023","SECTION_SET_2024"})
        section_2024_laps={s["attempt_lap_id"] for s in self.tables["attempt_sections"] if s["section_set_version"]=="SECTION_SET_2024"}
        result_2024_laps={l["attempt_lap_id"] for l in self.tables["attempt_laps"] if any(a["attempt_id"]==l["attempt_id"] and a["session_id"].endswith("2024") for a in self.tables["attempts"])}
        self.assertLess(len(section_2024_laps),len(result_2024_laps))

    def test_partial_section_lap_is_preserved(self):
        partial=[r for r in self.section_rows if r["coverage_status"]=="PARTIAL_OBSERVATION"]
        self.assertTrue(partial)
        reference=partial[0]["attempt_lap_reference"]
        attempt_id,source_part=reference.split(":source_lap=")
        source_index=int(source_part)
        sections=[s for s in self.tables["attempt_sections"] if s["attempt_id"]==attempt_id and s["source_report_lap_index"]==source_index]
        self.assertTrue(sections)
        self.assertTrue(all(s["section_lap_coverage_status"]=="PARTIAL_OBSERVATION" and not s["full_lap_coverage_member"] for s in sections))

    def test_incomplete_section_group_does_not_create_complete_lap(self):
        partial=next(r for r in self.section_rows if r["coverage_status"]=="PARTIAL_OBSERVATION")
        attempt_id,source_part=partial["attempt_lap_reference"].split(":source_lap=")
        source_index=int(source_part)
        self.assertFalse(any(l["attempt_id"]==attempt_id and l["source_report_lap_index"]==source_index for l in self.tables["attempt_laps"]))

    def test_chronology_gaps_and_capture_quality(self):
        gaps=[e for e in self.tables["chronology_events"] if e["event_type"]=="COVERAGE_GAP"]
        self.assertEqual({e["session_id"] for e in gaps},{"INDY500_DAY1_2020","INDY500_DAY1_2023"})
        captures=[e for e in self.tables["chronology_events"] if e["time_basis"]=="RECORDER_CAPTURE"]
        self.assertTrue(captures)
        self.assertTrue(all(e["event_time_quality"]=="APPROXIMATE_OBSERVED" for e in captures))
        self.assertEqual(self.statuses[2021],"PARTIAL")
        self.assertEqual(self.statuses[2024],"PARTIAL")
        self.assertEqual(self.chronology_rows, chronology_reconciliation(self.tables)[0])

    def test_ambiguous_timing_position_remains_unlinked(self):
        captures=[e for e in self.tables["chronology_events"] if e["time_basis"]=="RECORDER_CAPTURE"]
        mismatched=[e for e in captures if "CAPTURE_ATTEMPT_COUNT_MISMATCH" in e["event_payload_json"].get("reason_codes",[])]
        self.assertTrue(mismatched)
        self.assertTrue(all(e["attempt_id"] is None and e["event_payload_json"]["relation_status"]=="UNRESOLVED" for e in mismatched))

    def test_capture_count_mismatch_does_not_shift_later_attempts(self):
        captures=[e for e in self.tables["chronology_events"] if e["time_basis"]=="RECORDER_CAPTURE"]
        car18=[e for e in captures if e["entry_key"]=="INDY500_DAY1_2024|CAR_18|1"]
        self.assertTrue(car18)
        self.assertTrue(all("CAPTURE_ATTEMPT_COUNT_MISMATCH" in e["event_payload_json"].get("reason_codes",[]) for e in car18))
        self.assertTrue(all(e["attempt_id"] is None for e in car18))

    def test_chronology_status_is_check_derived(self):
        all_pass=[("A",True,0,"","")]
        one_fail=[("A",False,1,"X","")]
        self.assertEqual(_chronology_status(all_pass,False,True),"PASS")
        self.assertEqual(_chronology_status(one_fail,True,True),"PARTIAL")
        self.assertEqual(_chronology_status(one_fail,False,True),"FAIL")

    def test_critical_timestamp_conflict_check_reads_provenance(self):
        tables=deepcopy(self.tables)
        attempt=next(a for a in tables["attempts"] if a["session_id"].endswith("2021"))
        link=deepcopy(next(l for l in tables["field_evidence_links"] if l["entity_table"]=="ATTEMPTS" and l["entity_id"]==attempt["attempt_id"]))
        link.update({"field_evidence_link_id":"synthetic-time-conflict","field_name":"start_time_utc","conflict_disposition":"CONFLICTING_UNRESOLVED","uncertainty_note":"Two source times remain unresolved","is_primary":False})
        tables["field_evidence_links"].append(link)
        rows,_=chronology_reconciliation(tables)
        check=next(r for r in rows if r["year"]==2021 and r["check_id"]=="NO_CRITICAL_TIMESTAMP_CONFLICT")
        self.assertFalse(check["check_pass"])
        self.assertEqual(check["affected_count"],1)

    def test_source_conflict_check_detects_duplicate_primary(self):
        tables=deepcopy(self.tables)
        attempt=next(a for a in tables["attempts"] if a["session_id"].endswith("2021"))
        link=deepcopy(next(l for l in tables["field_evidence_links"] if l["entity_table"]=="ATTEMPTS" and l["entity_id"]==attempt["attempt_id"] and l["is_primary"]))
        link["field_evidence_link_id"]="synthetic-duplicate-primary"
        tables["field_evidence_links"].append(link)
        rows,_=chronology_reconciliation(tables)
        check=next(r for r in rows if r["year"]==2021 and r["check_id"]=="SOURCE_CONFLICTS_EXPLICIT")
        self.assertFalse(check["check_pass"])
        self.assertEqual(check["affected_count"],1)

    def test_provenance_semantics(self):
        evidence_ids={e["evidence_item_id"] for e in self.tables["evidence_items"]}
        for link in self.tables["field_evidence_links"]:
            if link["value_classification"]=="DERIVED_DETERMINISTIC":
                self.assertIsNone(link["evidence_item_id"])
                self.assertTrue(link["derivation_rule_id"] and link["derivation_rule_version"])
                self.assertTrue(link["input_lineage_json"] and link["input_entity_field_refs_json"])
            elif link["evidence_item_id"] is not None:
                self.assertIn(link["evidence_item_id"],evidence_ids)

    def test_target_specific_eligibility(self):
        keys=[(r["entity_type"],r["entity_id"],r["analysis_target"],r["ruleset_version"]) for r in self.tables["row_eligibility"]]
        self.assertEqual(len(keys),len(set(keys)))
        targets={r["analysis_target"] for r in self.tables["row_eligibility"]}
        self.assertEqual(targets,{"FOUR_LAP_PERFORMANCE","LAP_PERFORMANCE","WITHIN_CAR_COMPARISON","SECTION_ANALYSIS","CHRONOLOGY","QUEUE_CALIBRATION"})
        self.assertFalse(any(r["entity_type"]=="SECTION" and r["eligible_core_training"] for r in self.tables["row_eligibility"]))
        by_attempt={}
        for row in self.tables["row_eligibility"]:
            if row["entity_type"]=="ATTEMPT": by_attempt.setdefault(row["entity_id"],{})[row["analysis_target"]]=row
        cross_car=[v for v in by_attempt.values() if v["FOUR_LAP_PERFORMANCE"]["eligible_core_training"] and not v["WITHIN_CAR_COMPARISON"]["eligible"]]
        self.assertTrue(cross_car)

    def test_active_fuel_enum_has_no_ambiguous_legacy_value(self):
        allowed={"STANDARD_SINGLE_ATTEMPT_CONTEXT","SUSPECTED_CONSECUTIVE_ATTEMPT_STRATEGY","CONFIRMED_CONSECUTIVE_ATTEMPT_STRATEGY","UNKNOWN_FUEL_STRATEGY"}
        self.assertTrue({a["fuel_strategy_class"] for a in self.tables["attempts"]}<=allowed)

    def test_weather_has_no_lookahead_join(self):
        self.assertEqual(self.tables["decision_state_features"],[])
        self.assertTrue(all(s["availability_time_utc"] is None for s in self.tables["forecast_snapshots"]))

    def test_hrrr_numeric_snapshot_and_value_grain(self):
        self.assertEqual(len(self.tables["forecast_snapshots"]),259)
        self.assertEqual(len(self.tables["weather_forecasts"]),259*17)
        counts=Counter(v["forecast_snapshot_id"] for v in self.tables["weather_forecasts"])
        self.assertEqual(set(counts.values()),{17})
        self.assertEqual(len(counts),259)

    def test_hrrr_raw_and_derived_primary_provenance(self):
        primary={(l["entity_id"],l["field_name"]):l for l in self.tables["field_evidence_links"] if l["is_primary"]}
        for value in self.tables["weather_forecasts"]:
            link=primary[(value["weather_forecast_value_id"],"value_numeric")]
            expected="RAW_OBSERVED" if value["variable_code"] in weather.RAW_VARIABLES else "DERIVED_DETERMINISTIC"
            self.assertEqual(link["value_classification"],expected)

    def test_hrrr_cycle_valid_and_availability_are_distinct(self):
        for snapshot in self.tables["forecast_snapshots"]:
            self.assertIsNone(snapshot["availability_time_utc"])
            self.assertEqual(snapshot["availability_time_quality"],"UNKNOWN")
            self.assertEqual(snapshot["extraction_metadata_json"]["availability_status"],"POLICY_REQUIRED")
            self.assertEqual(snapshot["valid_start_utc"],snapshot["valid_end_utc"])

    def test_hrrr_known_2024_missing_combination_is_explicit(self):
        checks=weather.qa_rows(HRRR_NUMERIC_INPUT,self.tables)
        coverage=next(r for r in checks if r["year"]==2024 and r["check_id"]=="EXPECTED_CYCLE_LEAD_COVERAGE")
        self.assertEqual((coverage["pass_fail"],coverage["actual_count"],coverage["details"]),("PASS",51,"missing=14Z_f03"))
        self.assertTrue(all(r["pass_fail"]=="PASS" for r in checks))

    def test_hrrr_has_no_index_placeholder_or_track_temperature_semantics(self):
        self.assertFalse(any(s["extraction_metadata_json"]["status"]=="INDEX_ONLY_NO_VALUES" for s in self.tables["forecast_snapshots"]))
        variables={v["variable_code"] for v in self.tables["weather_forecasts"]}
        self.assertEqual(variables,set(weather.VARIABLE_UNITS))
        self.assertFalse(any(any(token in name.lower() for token in ("track","asphalt","shade","tire","rubber")) for name in variables))

    def test_hrrr_build_is_deterministic(self):
        again,_,_=build()
        self.assertEqual(self.tables["forecast_snapshots"],again["forecast_snapshots"])
        self.assertEqual(self.tables["weather_forecasts"],again["weather_forecasts"])

    def test_2024_veekay_multi_anchor_golden(self):
        self.assertTrue(golden_checks(self.tables)["VEEKAY_2024_MULTI_ANCHOR_GOLDEN"])
        veekay=sorted((c for c in self.tables["chronology_constraints"] if c["car_number"]=="21"),key=lambda c:c["car_attempt_index"])
        self.assertEqual([c["car_attempt_index"] for c in veekay],[1,2,3,4])
        self.assertEqual(veekay[0]["anchor_event_type"],"CRASH")
        self.assertIsNone(veekay[0]["timed_run_start_utc"])
        self.assertEqual(veekay[-1]["event_time_quality"],"BOUNDED_INTERVAL")

    def test_2024_rahal_final_attempt_consistency(self):
        self.assertTrue(golden_checks(self.tables)["RAHAL_2024_FINAL_ATTEMPT_CONSISTENCY"])
        rahal=next(c for c in self.tables["chronology_constraints"] if c["car_number"]=="15" and c["result_status"]=="WAVED_OFF" and c["duration_coverage"]=="OBSERVED_PARTIAL")
        self.assertEqual(rahal["anchor_time_upper_utc"],"2024-05-18T21:50:00Z")
        self.assertIsNone(rahal["timed_run_start_utc"])

    def test_2024_capture_links_require_independent_anchor(self):
        captures=[e for e in self.tables["chronology_events"] if e["session_id"]=="INDY500_DAY1_2024" and e["time_basis"]=="RECORDER_CAPTURE"]
        linked=[e for e in captures if e["attempt_id"]]
        self.assertEqual(len(linked),8)
        self.assertTrue(all(e["event_payload_json"]["relation_status"]=="MATCHED_CONSTRAINED_2024" and e["event_payload_json"].get("anchor_key") for e in linked))
        self.assertEqual(sum(e["attempt_id"] is None for e in captures),89)

    def test_2024_uncertainty_propagation(self):
        self.assertEqual(propagate_time_quality("APPROXIMATE_OBSERVED"),"APPROXIMATE_OBSERVED")
        self.assertEqual(propagate_time_quality("BOUNDED_INTERVAL"),"BOUNDED_INTERVAL")
        self.assertEqual(propagate_time_quality("EXACT_OBSERVED"),"BOUNDED_INTERVAL")
        final=next(c for c in self.tables["chronology_constraints"] if c["car_number"]=="21" and c["result_status"]=="VALID_RETAINED")
        self.assertTrue(final["timed_run_start_lower_utc"] and final["timed_run_start_upper_utc"])
        self.assertIsNone(final["timed_run_start_utc"])

    def test_2024_no_capture_or_crash_promoted_to_exact_start(self):
        linked=[c for c in self.tables["chronology_constraints"] if c["timing71_capture_event_id"]]
        self.assertTrue(all(c["event_time_quality"]!="EXACT_OBSERVED" for c in linked))
        crash=next(c for c in self.tables["chronology_constraints"] if c["anchor_event_type"]=="CRASH")
        self.assertFalse(any(crash[x] for x in ("timed_run_start_utc","timed_run_start_lower_utc","timed_run_start_upper_utc")))

    def test_2024_no_queue_wait_or_coverage_driven_upgrade(self):
        constraints=self.tables["chronology_constraints"]
        self.assertFalse(any("queue_wait" in key.lower() for c in constraints for key in c))
        usable=[c for c in constraints if c["event_time_quality"]!="UNKNOWN"]
        self.assertEqual(len(usable),9)
        self.assertTrue(all(c["anchor_evidence_item_id"] for c in usable))

    def test_2024_session_boundaries_and_constraint_lineage(self):
        session=next(e for e in self.tables["qualifying_events"] if e["year"]==2024)
        self.assertEqual((session["scheduled_start_utc"],session["scheduled_end_utc"]),("2024-05-18T15:00:00Z","2024-05-18T21:50:00Z"))
        evidence_ids={e["evidence_item_id"] for e in self.tables["evidence_items"]}
        constraint_ids={c["chronology_constraint_id"] for c in self.tables["chronology_constraints"]}
        links=[l for l in self.tables["field_evidence_links"] if l["entity_id"] in constraint_ids]
        self.assertTrue(links)
        self.assertTrue(all(l["evidence_item_id"] is None or l["evidence_item_id"] in evidence_ids for l in links))

    def test_2022_sato_first_attempt_golden_case(self):
        sato=[a for a in self.tables["attempts"] if a["session_id"]=="INDY500_DAY1_2022" and a["car_number"]=="51"]
        first=[a for a in sato if a["car_attempt_index"]==1 and a["four_lap_average_speed_mph"]==232.196]
        self.assertEqual(len(first),1)
        first=first[0]
        self.assertEqual(first["result_status"],"DISALLOWED")
        self.assertFalse(first["result_counted_at_session_end"])
        self.assertIsNone(first["start_time_utc"])
        laps=sorted((l for l in self.tables["attempt_laps"] if l["attempt_id"]==first["attempt_id"]),key=lambda x:x["lap_number"])
        self.assertEqual([l["lap_time_seconds"] for l in laps],[38.7399,38.7001,38.7706,38.8307])
        status_links=[l for l in self.tables["field_evidence_links"] if l["entity_id"]==first["attempt_id"] and l["field_name"]=="result_status"]
        primary=[l for l in status_links if l["is_primary"]]
        self.assertEqual(len(primary),1)
        self.assertTrue(primary[0]["evidence_item_id"])

if __name__ == "__main__":
    unittest.main()
