from collections import Counter, defaultdict
from .config import CORE_PERFORMANCE_YEARS, RUN_RECORDED_AT

TARGETS = ("FOUR_LAP_PERFORMANCE", "WITHIN_CAR_COMPARISON", "CHRONOLOGY", "QUEUE_CALIBRATION")

def assign(tables):
    rows=[]; attempts=tables["attempts"]
    constraint_by_attempt={c["attempt_id"]:c for c in tables["chronology_constraints"]}
    entry_counts=Counter(a["entry_key"] for a in attempts if a["car_attempt_index"] is not None)
    year_status={e["year"]:e["chronology_reconciliation_status"] for e in tables["qualifying_events"]}
    for attempt in attempts:
        year=int(attempt["session_id"][-4:])
        four=attempt["attempt_class"]=="A_COMPLETE" and attempt["four_lap_total_seconds"] is not None
        within=four and attempt["car_attempt_index"] is not None and entry_counts[attempt["entry_key"]] >= 2
        constraint=constraint_by_attempt.get(attempt["attempt_id"])
        chrono=(constraint["event_time_quality"] if constraint else attempt["event_time_quality"]) in ("EXACT_OBSERVED","APPROXIMATE_OBSERVED","BOUNDED_INTERVAL","ORDERING_ONLY")
        for target,eligible in (("FOUR_LAP_PERFORMANCE",four),("WITHIN_CAR_COMPARISON",within),("CHRONOLOGY",chrono),("QUEUE_CALIBRATION",False)):
            core = eligible and ((target in ("FOUR_LAP_PERFORMANCE","WITHIN_CAR_COMPARISON") and year in CORE_PERFORMANCE_YEARS) or (target=="CHRONOLOGY" and year_status[year]=="PASS"))
            reasons=[]
            if not eligible: reasons.append({"FOUR_LAP_PERFORMANCE":"NOT_COMPLETE_FOUR_LAP","WITHIN_CAR_COMPARISON":"ORDERED_COMPATIBLE_REPEAT_UNAVAILABLE","CHRONOLOGY":"USABLE_EVENT_TIME_UNAVAILABLE","QUEUE_CALIBRATION":"NO_DIRECT_QUEUE_OR_SERVICE_FACT"}[target])
            if eligible and not core: reasons.append("YEAR_POLICY_OR_RECONCILIATION_NOT_CORE")
            rows.append(_row("ATTEMPT",attempt["attempt_id"],target,eligible,core,year==2022 or (eligible and not core),year==2022,"|".join(reasons)))
    for lap in tables["attempt_laps"]:
        attempt=next(a for a in attempts if a["attempt_id"]==lap["attempt_id"]); year=int(attempt["session_id"][-4:])
        eligible=lap["lap_completion_status"]=="COMPLETE" and lap["lap_time_seconds"] is not None
        core=eligible and year in CORE_PERFORMANCE_YEARS
        rows.append(_row("LAP",lap["attempt_lap_id"],"LAP_PERFORMANCE",eligible,core,year==2022 or (eligible and not core),year==2022,"" if eligible else "INCOMPLETE_LAP"))
    for section in tables["attempt_sections"]:
        eligible=section["section_time_seconds"] is not None and section["section_set_version"] is not None
        rows.append(_row("SECTION",section["attempt_section_id"],"SECTION_ANALYSIS",eligible,False,True,False,"NESTED_COMPONENT_NOT_INDEPENDENT_SAMPLE"))
    for event in tables["chronology_events"]:
        year=int(event["session_id"][-4:]); usable=event["event_time_quality"] != "UNKNOWN"
        for target in ("CHRONOLOGY","QUEUE_CALIBRATION"):
            eligible=usable if target=="CHRONOLOGY" else (usable and event["event_type"] in ("ATTEMPT_START","ATTEMPT_END","QUALIFIER_CAPTURE","QUEUE_FACT","REQUEUE","LANE_SELECTION"))
            core=eligible and target=="CHRONOLOGY" and year_status[year]=="PASS"
            rows.append(_row("CHRONOLOGY_EVENT",event["chronology_event_id"],target,eligible,core,eligible and not core,False,"" if eligible else "EVENT_NOT_USABLE_FOR_TARGET"))
    tables["row_eligibility"]=rows
    return rows

def _row(entity_type,entity_id,target,eligible,core,supporting,robustness,reasons):
    return {"entity_type":entity_type,"entity_id":entity_id,"analysis_target":target,"ruleset_version":"ELIGIBILITY_V2","eligible":eligible,"eligible_core_training":core,"supporting_only":supporting,"robustness_only":robustness,"reason_codes":reasons,"evaluated_at_utc":RUN_RECORDED_AT}
