import json
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path
from .config import ROOT
from .provenance import Provenance
from .io_utils import stable_id
from .chronology_2024 import golden_checks

RULES=json.loads((Path(__file__).parent/"rules"/"section_reconstruction_v1.json").read_text())

def section_validation(tables):
    attempts={a["attempt_id"]:a for a in tables["attempts"]}
    grouped=defaultdict(list)
    for section in tables["attempt_sections"]:
        grouped[(section["attempt_id"],section["source_report_lap_index"])].append(section)
    rows=[]; additions=Provenance()
    evidence_by_section={}
    coverage_links_by_section=defaultdict(list)
    for link in tables["field_evidence_links"]:
        if link["entity_table"]=="ATTEMPT_SECTIONS" and link["field_name"]=="section_time_seconds" and link["evidence_item_id"]:
            evidence_by_section[link["entity_id"]]=link["evidence_item_id"]
        if link["entity_table"]=="ATTEMPT_SECTIONS" and link["field_name"]=="section_lap_coverage_status" and link["is_primary"]:
            coverage_links_by_section[link["entity_id"]].append(link)
    for (attempt_id,source_index),sections in grouped.items():
        attempt=attempts[attempt_id]; version=sections[0]["section_set_version"]; config=RULES["formats"][version]
        reconstructed_decimal=sum((Decimal(str(s["section_time_seconds"])) for s in sections),Decimal("0"))
        reconstructed=float(reconstructed_decimal)
        official_values={s["source_report_lap_time_seconds"] for s in sections if s["source_report_lap_time_seconds"] is not None}
        official=next(iter(official_values)) if len(official_values)==1 else None
        complete_candidate=len(sections)==config["required_section_count"] and official is not None
        residual=float(reconstructed_decimal-Decimal(str(official))) if official is not None else None
        passed=bool(complete_candidate and abs(residual)<=config["tolerance_seconds"])
        final_status="VALIDATED_COMPLETE" if passed else ("VALIDATION_FAILED" if complete_candidate else "PARTIAL_OBSERVATION")
        reason="PASS" if passed else ("RESIDUAL_EXCEEDS_FORMAT_TOLERANCE" if complete_candidate else "INCOMPLETE_SECTION_COVERAGE_OR_MISSING_LAP_TIME")
        lap_no=sections[0]["lap_number"]
        linked_lap_id=next((s["attempt_lap_id"] for s in sections if s["attempt_lap_id"]),None)
        existing=next((l for l in tables["attempt_laps"] if l["attempt_lap_id"]==linked_lap_id),None)
        lap_id=existing["attempt_lap_id"] if existing else None
        if passed and existing is None and attempt["attempt_class"]=="C_SECTION_ONLY":
            lap_id=stable_id("attempt_lap",attempt_id,lap_no,"section_reconstruction",source_index)
            lap={"attempt_lap_id":lap_id,"attempt_id":attempt_id,"source_report_lap_index":source_index,"lap_number":lap_no,"lap_completion_status":"COMPLETE","lap_time_seconds":round(reconstructed,4),"lap_speed_mph":round(9000/reconstructed,3),"reconstruction_rule_id":config["rule_version"],"reconstruction_validation_status":"PASSED"}
            tables["attempt_laps"].append(lap)
            evidence_ids=[evidence_by_section.get(s["attempt_section_id"]) for s in sections]
            evidence_ids=[e for e in evidence_ids if e]
            lineage={"attempt_id":attempt_id,"source_report_lap_index":source_index,"section_ids":[s["attempt_section_id"] for s in sections],"section_times":[s["section_time_seconds"] for s in sections],"tolerance_seconds":config["tolerance_seconds"]}
            refs=[{"table":"attempt_sections","id":s["attempt_section_id"],"field":"section_time_seconds"} for s in sections]
            for index,evidence_id in enumerate(evidence_ids): additions.reconstructed("attempt_laps",lap_id,"lap_time_seconds",evidence_id,config["rule_version"],"1",lineage,refs,"All published non-overlapping sections; validated against source lap time",primary=index==0)
            additions.derived("attempt_laps",lap_id,"lap_number","SECTION_ATTEMPT_LAP_POSITION_V1","1",{"source_report_lap_index":source_index,"lap_number":lap_no},refs)
            additions.derived("attempt_laps",lap_id,"lap_completion_status","LAP_COMPLETION_V1","1",{"validation_pass":True},refs)
            additions.derived("attempt_laps",lap_id,"lap_speed_mph","LAP_SPEED_FROM_TIME_V1","1",{"distance_miles":2.5,"lap_time_seconds":round(reconstructed,4)},[{"table":"attempt_laps","id":lap_id,"field":"lap_time_seconds"}])
        elif passed and existing is not None:
            existing["reconstruction_validation_status"]="PASSED"
        for section in sections:
            section["section_lap_coverage_status"]=final_status
            section["full_lap_coverage_member"]=passed
            if passed: section["attempt_lap_id"]=lap_id
            for link in coverage_links_by_section.get(section["attempt_section_id"],[]):
                link["is_primary"]=False; link["conflict_disposition"]="SUPERSEDED"
            refs=[{"table":"attempt_sections","id":s["attempt_section_id"],"field":"section_time_seconds"} for s in sections]
            additions.derived("attempt_sections",section["attempt_section_id"],"section_lap_coverage_status","SECTION_COVERAGE_V2","2",{"status":final_status,"source_report_lap_index":source_index,"validation_reason":reason},refs)
            additions.derived("attempt_sections",section["attempt_section_id"],"full_lap_coverage_member","SECTION_COVERAGE_V2","2",{"validation_pass":passed,"source_report_lap_index":source_index},refs)
        rows.append({"year":int(attempt["session_id"][-4:]),"section_set_version":version,
            "attempt_lap_reference":lap_id or f"{attempt_id}:source_lap={source_index}","official_lap_time":official,
            "reconstructed_lap_time":reconstructed,"residual":residual,"section_observation_count":len(sections),
            "coverage_status":final_status,"validation_reason":reason,"published_precision_seconds":config["published_precision_seconds"],
            "tolerance_seconds":config["tolerance_seconds"],"validation_pass":passed,"rule_version":config["rule_version"]})
    tables["field_evidence_links"].extend(additions.links)
    return rows

def chronology_reconciliation(tables):
    attempts=defaultdict(list); events=defaultdict(list)
    for a in tables["attempts"]: attempts[int(a["session_id"][-4:])].append(a)
    for e in tables["chronology_events"]: events[int(e["session_id"][-4:])].append(e)
    output=[]; statuses={}
    for year in range(2020,2025):
        linked={e["attempt_id"] for e in events[year] if e["attempt_id"]}
        year_entity_ids={a["attempt_id"] for a in attempts[year]}|{e["chronology_event_id"] for e in events[year]}
        checks=[]
        unmatched=[a["attempt_id"] for a in attempts[year] if a["attempt_id"] not in linked]
        checks.append(("KNOWN_OFFICIAL_ATTEMPTS_DISPOSITIONED",not unmatched,len(unmatched),"OFFICIAL_ATTEMPTS_WITHOUT_MATCHED_CHRONOLOGY","|".join(unmatched)))
        ids=[a["attempt_id"] for a in attempts[year]]; checks.append(("NO_DUPLICATE_CANONICAL_ATTEMPT",len(ids)==len(set(ids)),len(ids)-len(set(ids)),"DUPLICATE_ATTEMPT_ID"))
        keys=[a["attempt_key"] for a in attempts[year] if a["attempt_key"]]; checks.append(("NO_WITHIN_CAR_ORDER_CONFLICT",len(keys)==len(set(keys)),len(keys)-len(set(keys)),"DUPLICATE_ATTEMPT_KEY",""))
        event_times=defaultdict(set)
        for event in events[year]:
            if event["attempt_id"] and event["event_time_utc"]: event_times[(event["attempt_id"],event["event_type"])].add(event["event_time_utc"])
        provenance_time_conflicts=[l for l in tables["field_evidence_links"] if l["conflict_disposition"]=="CONFLICTING_UNRESOLVED" and "time" in l["field_name"].lower() and l["entity_id"] in year_entity_ids]
        timestamp_conflicts=["|".join(k) for k,v in event_times.items() if len(v)>1]+[l["field_evidence_link_id"] for l in provenance_time_conflicts]
        checks.append(("NO_CRITICAL_TIMESTAMP_CONFLICT",not timestamp_conflicts,len(timestamp_conflicts),"MULTIPLE_EVENT_TIMES_OR_UNRESOLVED_TIME_CONFLICT" if timestamp_conflicts else "","|".join(timestamp_conflicts)))
        official_cars={a["car_number"] for a in attempts[year]}; capture_starts=[e for e in events[year] if e["time_basis"]=="RECORDER_CAPTURE"]
        replay_only=[e for e in capture_starts if e["entry_key"] and e["entry_key"].split("CAR_")[-1].split("|")[0] not in official_cars]
        unexplained=max(len(replay_only),max(0,len(capture_starts)-len(attempts[year])))
        checks.append(("NO_UNEXPLAINED_REPLAY_ONLY_ATTEMPT",unexplained==0,unexplained,"UNMATCHED_CAPTURE_OCCASION" if unexplained else "","|".join(e["chronology_event_id"] for e in replay_only)))
        gaps=[e for e in events[year] if e["event_type"]=="COVERAGE_GAP"]
        checks.append(("NO_UNRESOLVED_CORE_WINDOW_GAP",not gaps,len(gaps),"KNOWN_REPLAY_COVERAGE_GAP" if gaps else "","|".join(e["chronology_event_id"] for e in gaps)))
        primary_counts=Counter((l["entity_table"],l["entity_id"],l["field_name"]) for l in tables["field_evidence_links"] if l["entity_id"] in year_entity_ids and l["is_primary"])
        duplicate_primary=["|".join(k) for k,v in primary_counts.items() if v>1]
        undocumented=[l["field_evidence_link_id"] for l in tables["field_evidence_links"] if l["entity_id"] in year_entity_ids and l["conflict_disposition"]=="CONFLICTING_UNRESOLVED" and not l["uncertainty_note"]]
        source_conflicts=duplicate_primary+undocumented
        checks.append(("SOURCE_CONFLICTS_EXPLICIT",not source_conflicts,len(source_conflicts),"DUPLICATE_PRIMARY_OR_UNDOCUMENTED_CONFLICT" if source_conflicts else "","|".join(source_conflicts)))
        normalized=[]
        for check in checks:
            if len(check)==4: check=check+("",)
            normalized.append(check)
        for check,passed,count,reason,identifiers in normalized:
            output.append({"year":year,"check_id":check,"check_pass":passed,"affected_count":max(0,count),"reason_code":reason,"affected_identifiers":identifiers})
        usable=any(e["time_basis"]=="RECORDER_CAPTURE" and e["event_time_quality"] in ("EXACT_OBSERVED","APPROXIMATE_OBSERVED","BOUNDED_INTERVAL") for e in events[year])
        critical_ok=all(passed for check,passed,_,_,_ in normalized if check in ("NO_DUPLICATE_CANONICAL_ATTEMPT","NO_WITHIN_CAR_ORDER_CONFLICT","NO_CRITICAL_TIMESTAMP_CONFLICT","SOURCE_CONFLICTS_EXPLICIT"))
        status=_chronology_status(normalized,usable,critical_ok)
        statuses[year]=status
    existing={(l["entity_table"],l["entity_id"],l["field_name"]) for l in tables["field_evidence_links"]}
    additions=Provenance()
    for event in tables["qualifying_events"]:
        event["chronology_reconciliation_status"]=statuses[event["year"]]
        key=("QUALIFYING_EVENTS",event["session_id"],"chronology_reconciliation_status")
        if key not in existing:
            additions.derived("qualifying_events",event["session_id"],"chronology_reconciliation_status","CHRONOLOGY_RECONCILIATION_V1","1",{"year":event["year"],"checks":[r for r in output if r["year"]==event["year"]]},[{"table":"chronology_reconciliation_report","year":event["year"]}])
    tables["field_evidence_links"].extend(additions.links)
    return output,statuses

def _chronology_status(checks,has_usable_events,critical_checks_pass):
    if all(check[1] for check in checks): return "PASS"
    if has_usable_events and critical_checks_pass: return "PARTIAL"
    return "FAIL"

def data_quality(tables, section_rows, chronology_rows, issues, weather_rows=None):
    checks=[]
    def add(check_id,year,entity,severity,passed,count,reason,ids=""):
        checks.append({"check_id":check_id,"year":year,"entity_type":entity,"severity":severity,"pass_fail":"PASS" if passed else "FAIL","affected_count":count,"reason":reason,"affected_identifiers":ids})
    ids=[a["attempt_id"] for a in tables["attempts"]]; add("ATTEMPT_UUID_UNIQUE","ALL","ATTEMPT","BLOCKING",len(ids)==len(set(ids)),len(ids)-len(set(ids)),"Canonical attempt UUIDs must be unique")
    class_a=[a for a in tables["attempts"] if a["attempt_class"]=="A_COMPLETE"]; lap_counts=Counter(l["attempt_id"] for l in tables["attempt_laps"] if l["lap_completion_status"]=="COMPLETE")
    bad=[a["attempt_id"] for a in class_a if lap_counts[a["attempt_id"]]!=4]; add("CLASS_A_EXACTLY_FOUR_LAPS","ALL","ATTEMPT","BLOCKING",not bad,len(bad),"Class A must have exactly four complete qualifying laps","|".join(bad))
    zero=[l["attempt_lap_id"] for l in tables["attempt_laps"] if l["lap_time_seconds"]==0]; add("NO_ZERO_FILLED_LAPS","ALL","LAP","BLOCKING",not zero,len(zero),"Missing laps are omitted rather than zero-filled","|".join(zero))
    reconstructed_ids={l["attempt_lap_id"] for l in tables["attempt_laps"] if l["reconstruction_rule_id"]}
    invalid_reconstructed=[r for r in section_rows if r["attempt_lap_reference"] in reconstructed_ids and not r["validation_pass"]]
    add("SECTION_RECONSTRUCTION_WITHIN_FROZEN_TOLERANCE","ALL","LAP","BLOCKING",not invalid_reconstructed,len(invalid_reconstructed),"Only section groups passing the format-specific rule may create reconstructed laps","|".join(r["attempt_lap_reference"] for r in invalid_reconstructed))
    partial_groups=[r for r in section_rows if r["coverage_status"]=="PARTIAL_OBSERVATION"]
    failed_candidates=[r for r in section_rows if r["coverage_status"]=="VALIDATION_FAILED"]
    add("PARTIAL_SECTION_OBSERVATIONS_PRESERVED","ALL","SECTION","INFO",True,len(partial_groups),"Partial official source-report laps remain section evidence and do not create complete laps","|".join(r["attempt_lap_reference"] for r in partial_groups[:50]))
    add("FAILED_SECTION_CANDIDATES_DISABLED","ALL","SECTION","WARNING",True,len(failed_candidates),"Complete candidates outside the frozen tolerance remain preserved but unreconstructed","|".join(r["attempt_lap_reference"] for r in failed_candidates[:50]))
    source_ids={s["source_id"] for s in tables["sources"]}; orphan=[e["evidence_item_id"] for e in tables["evidence_items"] if e["source_id"] not in source_ids]; add("EVIDENCE_SOURCE_FOREIGN_KEYS","ALL","EVIDENCE","BLOCKING",not orphan,len(orphan),"Every evidence item references a registered source","|".join(orphan))
    malformed=[l["field_evidence_link_id"] for l in tables["field_evidence_links"] if l["value_classification"]=="DERIVED_DETERMINISTIC" and (l["evidence_item_id"] or not all((l["derivation_rule_id"],l["derivation_rule_version"],l["input_lineage_json"],l["input_entity_field_refs_json"])))]; add("DERIVED_LINEAGE_COMPLETE","ALL","PROVENANCE","BLOCKING",not malformed,len(malformed),"Derived values require null direct evidence and reproducible lineage","|".join(malformed))
    evidence_ids={e["evidence_item_id"] for e in tables["evidence_items"]}; links=tables["field_evidence_links"]
    direct_bad=[l["field_evidence_link_id"] for l in links if l["value_classification"] in ("RAW_OBSERVED","MANUALLY_ANNOTATED","RECONSTRUCTED_FROM_OFFICIAL_EVIDENCE") and l["evidence_item_id"] not in evidence_ids]
    add("DIRECT_RECONSTRUCTED_MANUAL_EVIDENCE_PRESENT","ALL","PROVENANCE","BLOCKING",not direct_bad,len(direct_bad),"Observed reconstructed and manual assertions require real registered evidence","|".join(direct_bad))
    rule_bad=[l["field_evidence_link_id"] for l in links if l["value_classification"] in ("MANUALLY_ANNOTATED","RECONSTRUCTED_FROM_OFFICIAL_EVIDENCE") and not (l["derivation_rule_id"] and l["derivation_rule_version"])]
    add("RECONSTRUCTED_MANUAL_RULE_PRESENT","ALL","PROVENANCE","BLOCKING",not rule_bad,len(rule_bad),"Reconstructed and manual assertions require a versioned rule","|".join(rule_bad))
    primary_counts=Counter((l["entity_table"],l["entity_id"],l["field_name"]) for l in links if l["is_primary"])
    duplicate_primary=["|".join(k) for k,v in primary_counts.items() if v>1]
    add("AT_MOST_ONE_PRIMARY_FIELD_ASSERTION","ALL","PROVENANCE","BLOCKING",not duplicate_primary,len(duplicate_primary),"Each entity field has at most one current primary assertion",";".join(duplicate_primary[:50]))
    evidenced={(l["entity_table"],l["entity_id"],l["field_name"]) for l in links if l["evidence_item_id"] in evidence_ids}
    substantive=[]
    for a in tables["attempts"]:
        if ("ATTEMPTS",a["attempt_id"],"car_number") not in evidenced: substantive.append(a["attempt_id"]+":car_number")
        if a["four_lap_total_seconds"] is not None and not any(("ATTEMPTS",a["attempt_id"],f) in evidenced or any(l["entity_id"]==a["attempt_id"] and l["field_name"]==f and l["value_classification"]=="DERIVED_DETERMINISTIC" for l in links) for f in ("four_lap_total_seconds",)): substantive.append(a["attempt_id"]+":four_lap_total_seconds")
    for l in tables["attempt_laps"]:
        if ("ATTEMPT_LAPS",l["attempt_lap_id"],"lap_time_seconds") not in evidenced: substantive.append(l["attempt_lap_id"]+":lap_time_seconds")
    for s in tables["attempt_sections"]:
        if ("ATTEMPT_SECTIONS",s["attempt_section_id"],"section_time_seconds") not in evidenced: substantive.append(s["attempt_section_id"]+":section_time_seconds")
    add("SUBSTANTIVE_VALUE_PROVENANCE_COVERAGE","ALL","PROVENANCE","BLOCKING",not substantive,len(substantive),"Attempt identity performance laps and section values require evidence or reproducible derivation","|".join(substantive[:50]))
    targets={r["analysis_target"] for r in tables["row_eligibility"]}; required={"FOUR_LAP_PERFORMANCE","LAP_PERFORMANCE","WITHIN_CAR_COMPARISON","SECTION_ANALYSIS","CHRONOLOGY","QUEUE_CALIBRATION"}; add("TARGET_SPECIFIC_ELIGIBILITY","ALL","ELIGIBILITY","BLOCKING",required<=targets,len(required-targets),"All frozen analysis targets must be represented","|".join(sorted(required-targets)))
    leaks=[]
    snapshots={s["forecast_snapshot_id"]:s for s in tables["forecast_snapshots"]}
    for state in tables["decision_state_features"]:
        sid=state.get("forecast_snapshot_id")
        if sid and (not snapshots[sid]["availability_time_utc"] or snapshots[sid]["availability_time_utc"]>state["state_as_of_time_utc"]): leaks.append(state["decision_state_id"])
    add("NO_WEATHER_LOOKAHEAD","ALL","DECISION_STATE","BLOCKING",not leaks,len(leaks),"Forecast availability must be known and no later than state time","|".join(leaks))
    weather_failures=[r for r in (weather_rows or []) if r["severity"]=="BLOCKING" and r["pass_fail"]=="FAIL"]
    add("HRRR_NUMERIC_LAYER_VALID","ALL","WEATHER","BLOCKING",not weather_failures,len(weather_failures),"All Phase 4A frozen-input and canonical weather checks must pass","|".join(r["check_id"] for r in weather_failures))
    capture_precision=[e["chronology_event_id"] for e in tables["chronology_events"] if e["time_basis"]=="RECORDER_CAPTURE" and e["event_time_quality"]=="EXACT_OBSERVED"]
    add("CAPTURE_TIME_NOT_PROMOTED_TO_EXACT","ALL","CHRONOLOGY","BLOCKING",not capture_precision,len(capture_precision),"Recorder capture times must remain approximate","|".join(capture_precision))
    missing_gaps=[year for year in (2020,2023) if not any(e["event_type"]=="COVERAGE_GAP" and e["session_id"].endswith(str(year)) for e in tables["chronology_events"])]
    add("KNOWN_COVERAGE_GAPS_PRESENT","ALL","CHRONOLOGY","BLOCKING",not missing_gaps,len(missing_gaps),"2020 internal and 2023 terminal gaps must be explicit","|".join(map(str,missing_gaps)))
    constraints=tables["chronology_constraints"]
    attempts_2024=[a for a in tables["attempts"] if a["session_id"].endswith("2024")]
    constrained_ids=[c["attempt_id"] for c in constraints]
    complete_constraints=len(constraints)==len(attempts_2024) and len(constrained_ids)==len(set(constrained_ids)) and set(constrained_ids)=={a["attempt_id"] for a in attempts_2024}
    add("2024_ONE_CHRONOLOGY_CONSTRAINT_PER_ATTEMPT",2024,"CHRONOLOGY_CONSTRAINT","BLOCKING",complete_constraints,abs(len(attempts_2024)-len(constraints)),"Every 2024 canonical attempt must have exactly one strongest-supported constraint row")
    propagated_bad=[c["chronology_constraint_id"] for c in constraints if c["event_time_quality"]=="EXACT_OBSERVED" and (c["timing71_capture_event_id"] or c["timed_run_start_lower_utc"] or c["timed_run_end_lower_utc"])]
    add("2024_UNCERTAINTY_NOT_PROMOTED_TO_EXACT",2024,"CHRONOLOGY_CONSTRAINT","BLOCKING",not propagated_bad,len(propagated_bad),"Capture, bounded, and derived endpoints cannot become exact observed truth","|".join(propagated_bad))
    crash_start=[c["chronology_constraint_id"] for c in constraints if c["anchor_event_type"]=="CRASH" and any(c[x] for x in ("timed_run_start_utc","timed_run_start_lower_utc","timed_run_start_upper_utc"))]
    add("2024_CRASH_ANCHOR_NOT_TIMED_RUN_START",2024,"CHRONOLOGY_CONSTRAINT","BLOCKING",not crash_start,len(crash_start),"A crash clock anchor cannot be reinterpreted as first timed-lap start","|".join(crash_start))
    queue_wait_fields=[key for c in constraints for key in c if "queue_wait" in key.lower()]
    add("2024_NO_INTER_ATTEMPT_GAP_AS_QUEUE_WAIT",2024,"CHRONOLOGY_CONSTRAINT","BLOCKING",not queue_wait_fields,len(queue_wait_fields),"No chronology diagnostic may be labelled queue wait without queue entry and release evidence")
    boundary_bad=[]
    for c in constraints:
        for field in ("anchor_time_utc","anchor_time_lower_utc","anchor_time_upper_utc","timed_run_start_utc","timed_run_end_utc","timed_run_start_lower_utc","timed_run_start_upper_utc","timed_run_end_lower_utc","timed_run_end_upper_utc"):
            value=c[field]
            if value and not ("2024-05-18T15:00:00Z" <= value <= "2024-05-18T21:50:00Z"): boundary_bad.append(c["chronology_constraint_id"]+":"+field)
    add("2024_SESSION_BOUNDARY_CONSISTENCY",2024,"CHRONOLOGY_CONSTRAINT","BLOCKING",not boundary_bad,len(boundary_bad),"Attempt-level event and timed-run bounds must remain within the supported session window","|".join(boundary_bad))
    phase_checks=golden_checks(tables)
    add("VEEKAY_2024_MULTI_ANCHOR_GOLDEN",2024,"CHRONOLOGY_CONSTRAINT","BLOCKING",phase_checks["VEEKAY_2024_MULTI_ANCHOR_GOLDEN"],0 if phase_checks["VEEKAY_2024_MULTI_ANCHOR_GOLDEN"] else 1,"VeeKay crash, later runs, penultimate finish, duration, and Rahal ordering must remain mutually compatible")
    add("RAHAL_2024_FINAL_ATTEMPT_CONSISTENCY",2024,"CHRONOLOGY_CONSTRAINT","BLOCKING",phase_checks["RAHAL_2024_FINAL_ATTEMPT_CONSISTENCY"],0 if phase_checks["RAHAL_2024_FINAL_ATTEMPT_CONSISTENCY"] else 1,"Rahal must remain the bounded final one-lap waved-off attempt after VeeKay")
    constraint_ids={c["chronology_constraint_id"] for c in constraints}
    provenance_fields={(l["entity_id"],l["field_name"]) for l in tables["field_evidence_links"] if l["entity_id"] in constraint_ids}
    missing_lineage=[c["chronology_constraint_id"] for c in constraints if c["event_time_quality"]!="UNKNOWN" and (c["chronology_constraint_id"],"event_time_quality") not in provenance_fields]
    add("2024_CHRONOLOGY_CONSTRAINT_PROVENANCE",2024,"PROVENANCE","BLOCKING",not missing_lineage,len(missing_lineage),"Every non-unknown attempt constraint must retain field-level evidence lineage","|".join(missing_lineage))
    core_2022=[r["entity_id"] for r in tables["row_eligibility"] if r["eligible_core_training"] and any(a["attempt_id"]==r["entity_id"] and a["session_id"].endswith("2022") for a in tables["attempts"])]
    add("YEAR_POLICY_CANNOT_GRANT_2022_CORE","2022","ELIGIBILITY","BLOCKING",not core_2022,len(core_2022),"2022 remains supporting/robustness only","|".join(core_2022))
    sato=[a for a in tables["attempts"] if a["session_id"].endswith("2022") and a["car_number"]=="51" and a["car_attempt_index"]==1 and a["result_status"]=="DISALLOWED"]
    add("SATO_2022_FIRST_ATTEMPT_GOLDEN","2022","ATTEMPT","BLOCKING",len(sato)==1,abs(1-len(sato)),"First 232.196 mph attempt must remain separate and disallowed","|".join(a["attempt_id"] for a in sato))
    chronology_not_pass=sorted({r["year"] for r in chronology_rows if not r["check_pass"]})
    add("GLOBAL_CHRONOLOGY_ANALYSIS_READY","ALL","CHRONOLOGY","BLOCKING",not chronology_not_pass,len(chronology_not_pass),"Global chronology analysis requires reconciliation PASS; affected rows remain chronology-core ineligible","|".join(map(str,chronology_not_pass)))
    for year in range(2020,2025):
        unmatched=[i for i in issues if i["year"]==year]
        add("UNMATCHED_SECTION_BLOCKS_RETAINED_AS_UNRESOLVED",year,"SECTION","WARNING",True,len(unmatched),"Ambiguous Section runs were materialized as C_SECTION_ONLY without fabricated complete laps","|".join(i["id"] for i in unmatched))
    return checks
