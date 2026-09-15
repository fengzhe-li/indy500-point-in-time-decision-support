from collections import defaultdict
from datetime import datetime
import json
from pathlib import Path
from .config import EVIDENCE, YEARS, RESULT_INPUT, SECTION_INPUT, TIMING_INPUT, KNOWN_GAPS, RUN_RECORDED_AT, HRRR_NUMERIC_INPUT
from .io_utils import stable_id, sha256_file, canonical_json
from .source_registry import register_file
from .provenance import Provenance
from .parsers import official_results, section_results, timing71, weather
from .chronology_2024 import reconcile_2024

SECTION_RULES = json.loads((Path(__file__).parent / "rules" / "section_reconstruction_v1.json").read_text())

def build():
    tables = {name: [] for name in ("qualifying_events", "attempts", "attempt_laps", "attempt_sections",
        "chronology_events", "chronology_constraints", "forecast_snapshots", "weather_forecasts", "sources", "evidence_items",
        "field_evidence_links", "row_eligibility", "decision_state_features")}
    provenance = Provenance(); issues = []; parser_stats = []
    attempts_by_year = defaultdict(list); result_items = {}

    for year in YEARS:
        kind, filename = RESULT_INPUT[year]
        source = register_file(filename, "OFFICIAL_RESULTS", "OFFICIAL_RAW" if kind == "json" else "OFFICIAL_REPORT")
        tables["sources"].append(source)
        rows = official_results.parse_json(EVIDENCE / filename, year) if kind == "json" else official_results.parse_pdf(EVIDENCE / filename, year)
        parser_stats.append({"source": filename, "status": "PASS", "rows": len(rows)})
        session_id = f"INDY500_DAY1_{year}"
        first = rows[0]
        session = {"session_id": session_id, "year": year, "official_session_id": first.get("official_session_id"),
            "event_name": first.get("event_name") or f"{year} Indianapolis 500", "session_name": first.get("session_name") or "Qualifications - Day One",
            "event_date": _iso_date(first.get("event_date"), year), "local_timezone": "America/Indiana/Indianapolis",
            "scheduled_start_utc": None, "scheduled_end_utc": None, "actual_start_utc": None, "actual_end_utc": None,
            "chronology_reconciliation_status": None, "year_policy_version": "YEAR_POLICY_V1"}
        tables["qualifying_events"].append(session)
        session_item = provenance.item(source["source_id"], rows[0]["source_locator"], rows[0]["source_text"])
        for field in ("year", "official_session_id", "event_name", "session_name", "event_date"):
            if session.get(field) is not None: provenance.observed("qualifying_events", session_id, field, session_item)
        provenance.derived("qualifying_events", session_id, "session_id", "SESSION_ID_V1", "1", {"year": year}, [{"table":"qualifying_events","field":"year"}])
        for row in rows:
            attempt, laps = _result_attempt(row, session_id)
            tables["attempts"].append(attempt); attempts_by_year[year].append(attempt)
            item = provenance.item(source["source_id"], row["source_locator"], row["source_text"])
            result_items[attempt["attempt_id"]] = item
            for field in ("car_number", "driver_name", "team_name", "official_status_raw", "four_lap_total_seconds", "four_lap_average_speed_mph"):
                if attempt.get(field) not in (None, ""): provenance.observed("attempts", attempt["attempt_id"], field, item)
            if attempt.get("outcome_label"): provenance.observed("attempts",attempt["attempt_id"],"outcome_label",item)
            provenance.derived("attempts", attempt["attempt_id"], "entry_key", "ENTRY_KEY_V1", "1", {"session_id":session_id,"car_number":attempt["car_number"]}, [{"table":"attempts","field":"car_number"}])
            provenance.derived("attempts", attempt["attempt_id"], "attempt_class", "ATTEMPT_CLASS_V1", "1", {"positive_laps":len(laps)}, [{"table":"attempt_laps","field":"lap_completion_status"}])
            provenance.derived("attempts", attempt["attempt_id"], "result_status", "RESULT_STATUS_V1", "1", {"official_status_raw":attempt["official_status_raw"],"positive_laps":len(laps)}, [{"table":"attempts","field":"official_status_raw"},{"table":"attempt_laps","field":"lap_completion_status"}])
            if attempt["result_counted_at_session_end"] is not None:
                provenance.derived("attempts", attempt["attempt_id"], "result_counted_at_session_end", "SESSION_END_RESULT_V1", "1", {"result_status":attempt["result_status"]}, [{"table":"attempts","field":"result_status"}])
            for field in ("car_attempt_order_quality","event_time_quality","time_basis","withdrawal_evidence","lane_action","lane_evidence","requeue_evidence","fuel_strategy_class"):
                provenance.derived("attempts", attempt["attempt_id"], field, "MISSING_EVIDENCE_STATE_V1", "1", {"canonical_value":attempt[field],"source_locator":attempt["source_native_locator"]}, [{"table":"attempts","field":"source_native_locator"}])
            for lap in laps:
                tables["attempt_laps"].append(lap)
                provenance.observed("attempt_laps", lap["attempt_lap_id"], "lap_time_seconds", item)
                provenance.derived("attempt_laps", lap["attempt_lap_id"], "lap_number", "RESULT_LAP_POSITION_V1", "1", {"attempt_id":attempt["attempt_id"],"lap_number":lap["lap_number"]}, [{"table":"attempts","id":attempt["attempt_id"]}])
                provenance.derived("attempt_laps",lap["attempt_lap_id"],"lap_completion_status","LAP_COMPLETION_V1","1",{"lap_time_seconds":lap["lap_time_seconds"]},[{"table":"attempt_laps","field":"lap_time_seconds"}])
                provenance.derived("attempt_laps",lap["attempt_lap_id"],"lap_speed_mph","LAP_SPEED_FROM_TIME_V1","1",{"distance_miles":2.5,"lap_time_seconds":lap["lap_time_seconds"]},[{"table":"attempt_laps","field":"lap_time_seconds"}])

    # Official Section Results: match each reconstructed per-car block to an official Results lap tuple.
    for year in YEARS:
        filename = SECTION_INPUT[year]; source = register_file(filename, "OFFICIAL_SECTION_REPORT", "OFFICIAL_REPORT")
        tables["sources"].append(source)
        observations = section_results.parse(EVIDENCE / filename, year)
        parser_stats.append({"source": filename, "status": "PASS", "rows": len(observations)})
        blocks = _section_blocks(observations, year)
        for (car, block_index), block in blocks.items():
            attempt = _match_attempt(attempts_by_year[year], car, block)
            created_from_section = False
            if attempt is None and year == 2022 and car == "51" and block_index == 1 and len(block) == 4:
                attempt = _sato_attempt(block, f"INDY500_DAY1_{year}")
                created_from_section = True
                tables["attempts"].append(attempt); attempts_by_year[year].append(attempt)
                for lap in _laps_from_block(attempt, block): tables["attempt_laps"].append(lap)
            elif attempt is None and any(obs["section_times"] for obs in block):
                attempt = _section_only_attempt(block, f"INDY500_DAY1_{year}", block_index)
                created_from_section = True
                tables["attempts"].append(attempt); attempts_by_year[year].append(attempt)
                issues.append({"year":year,"code":"UNRESOLVED_SECTION_RUN_MATERIALIZED","id":f"car={car};block={block_index}"})
            if attempt is not None and year == 2022 and car == "51" and block_index == 1:
                attempt["official_status_raw"] = "Disallowed (official recap)"
                attempt["result_status"] = "DISALLOWED"
                attempt["result_counted_at_session_end"] = False
                status_source = _manual_source(tables["sources"], "official_editorial_sato_2022", "2022 IMS official recap", "https://www.indianapolismotorspeedway.com/news-multimedia/news/2022/05/21/05-21-VeeKay-Leads-Day1Quals")
                status_item = provenance.item(status_source["source_id"], "passage:Sato first attempt", "Sato first 232.196 mph attempt was disallowed and a second attempt was required.", note="Official editorial status evidence; performance remains from Section Report.")
                provenance.supersede("attempts",attempt["attempt_id"],"result_status")
                provenance.supersede("attempts",attempt["attempt_id"],"result_counted_at_session_end")
                provenance.observed("attempts", attempt["attempt_id"], "result_status", status_item, "MANUALLY_ANNOTATED", rule="RESULT_STATUS_V1", version="1")
                provenance.observed("attempts", attempt["attempt_id"], "result_counted_at_session_end", status_item, "RECONSTRUCTED_FROM_OFFICIAL_EVIDENCE", rule="SESSION_END_RESULT_V1", version="1")
                if created_from_section:
                    provenance.derived("attempts", attempt["attempt_id"], "entry_key", "ENTRY_KEY_V1", "1", {"session_id":attempt["session_id"],"car_number":"51"}, [{"table":"attempts","field":"car_number"}])
                    provenance.derived("attempts", attempt["attempt_id"], "attempt_class", "ATTEMPT_CLASS_V1", "1", {"positive_laps":4}, [{"table":"attempt_laps","field":"lap_completion_status"}])
                    provenance.derived("attempts", attempt["attempt_id"], "four_lap_total_seconds", "SUM_FOUR_LAPS_V1", "1", {"lap_times":[x["official_lap_time"] for x in block]}, [{"table":"attempt_laps","field":"lap_time_seconds"}])
                    provenance.derived("attempts", attempt["attempt_id"], "four_lap_average_speed_mph", "TEN_MILES_OVER_TIME_V1", "1", {"total_seconds":attempt["four_lap_total_seconds"]}, [{"table":"attempts","field":"four_lap_total_seconds"}])
            if attempt is None: continue
            if year <= 2023:
                _assign_attempt_order(attempt, block_index, provenance)
            lap_map = {lap["lap_number"]: lap for lap in tables["attempt_laps"] if lap["attempt_id"] == attempt["attempt_id"]}
            order_evidence_added = False
            creation_evidence_added = False
            for obs in block:
                lap_no = section_results.attempt_block(year, obs["source_report_lap_index"])[1]
                if lap_no not in range(1, 5) or not obs["section_times"]: continue
                item = provenance.item(source["source_id"], f"pages={','.join(map(str,obs['pages']))};car={car};source_lap={obs['source_report_lap_index']}", " | ".join(obs["raw_rows"]))
                if created_from_section and not creation_evidence_added:
                    provenance.observed("attempts",attempt["attempt_id"],"car_number",item)
                    provenance.observed("attempts",attempt["attempt_id"],"driver_name",item)
                    provenance.derived("attempts",attempt["attempt_id"],"entry_key","ENTRY_KEY_V1","1",{"session_id":attempt["session_id"],"car_number":attempt["car_number"]},[{"table":"attempts","field":"car_number"}])
                    provenance.derived("attempts",attempt["attempt_id"],"attempt_class","ATTEMPT_CLASS_V1","1",{"origin":"UNRESOLVED_SECTION_RUN"},[{"table":"attempt_sections","field":"section_time_seconds"}])
                    creation_evidence_added=True
                if year <= 2023 and not order_evidence_added:
                    provenance.supersede("attempts",attempt["attempt_id"],"car_attempt_order_quality")
                    provenance.reconstructed("attempts", attempt["attempt_id"], "car_attempt_index", item,
                        "SECTION_SEGMENT_2020_2023_V1", "1", {"block_index":block_index,"source_lap":obs["source_report_lap_index"]},
                        [{"table":"attempt_sections","field":"source_report_lap_index"}], "Continuous index plus transition-row segmentation")
                    provenance.reconstructed("attempts",attempt["attempt_id"],"car_attempt_order_quality",item,"SECTION_SEGMENT_2020_2023_V1","1",{"quality":"ORDERING_ONLY","block_index":block_index},[{"table":"attempt_sections","field":"source_report_lap_index"}],"Per-car order only; no global sequence")
                    order_evidence_added = True
                candidate_time = _candidate_lap_time(year, obs)
                coverage_status = "COMPLETE_CANDIDATE" if candidate_time is not None and len(obs["section_times"]) == _section_config(year)["required_section_count"] else "PARTIAL_OBSERVATION"
                lap = lap_map.get(lap_no)
                linked_lap = lap if lap and candidate_time is not None and round(float(lap["lap_time_seconds"]),4)==round(candidate_time,4) else None
                if linked_lap:
                    linked_lap["source_report_lap_index"] = obs["source_report_lap_index"]
                    provenance.observed("attempt_laps", linked_lap["attempt_lap_id"], "source_report_lap_index", item, primary=True)
                    provenance.observed("attempt_laps", linked_lap["attempt_lap_id"], "lap_time_seconds", item,
                        primary=created_from_section)
                for index, section_time in enumerate(obs["section_times"], 1):
                    section_id = stable_id("attempt_section", attempt["attempt_id"], obs["source_report_lap_index"], index)
                    section = {"attempt_section_id": section_id, "attempt_id": attempt["attempt_id"],
                        "attempt_lap_id": linked_lap["attempt_lap_id"] if linked_lap else None,
                        "source_report_lap_index": obs["source_report_lap_index"], "source_report_lap_time_seconds": candidate_time, "lap_number": lap_no,
                        "section_set_version": "SECTION_SET_2020_2023" if year <= 2023 else "SECTION_SET_2024",
                        "section_lap_coverage_status": coverage_status,
                        "section_sequence_index": index, "section_name": _section_names(year)[index-1],
                        "start_timing_point": None, "end_timing_point": None,
                        "section_time_seconds": section_time,
                        "section_speed_mph": obs["section_speeds"][index-1] if index <= len(obs["section_speeds"]) else None,
                        "full_lap_coverage_member": False}
                    tables["attempt_sections"].append(section)
                    provenance.observed("attempt_sections", section_id, "section_time_seconds", item)
                    provenance.observed("attempt_sections", section_id, "source_report_lap_index", item)
                    if candidate_time is not None: provenance.observed("attempt_sections",section_id,"source_report_lap_time_seconds",item)
                    provenance.observed("attempt_sections",section_id,"section_name",item)
                    if section["section_speed_mph"] is not None: provenance.observed("attempt_sections",section_id,"section_speed_mph",item)
                    provenance.reconstructed("attempt_sections",section_id,"lap_number",item,"SECTION_SEGMENT_2020_2023_V1" if year<=2023 else "SELECTED_ATTEMPT_2024_V1","1",{"source_report_lap_index":obs["source_report_lap_index"],"lap_number":lap_no},[{"table":"attempt_sections","field":"source_report_lap_index"}])
                    provenance.observed("attempt_sections",section_id,"section_set_version",item,"MANUALLY_ANNOTATED",rule="SECTION_SET_V1",version="1")
                    provenance.derived("attempt_sections",section_id,"section_lap_coverage_status","SECTION_COVERAGE_V2","1",{"section_count":len(obs["section_times"]),"source_report_lap_time_seconds":candidate_time},[{"table":"attempt_sections","field":"section_time_seconds"},{"table":"attempt_sections","field":"source_report_lap_time_seconds"}])

    # Recompute class and attempt keys after Section matching/addition.
    laps_by_attempt = defaultdict(list)
    for lap in tables["attempt_laps"]: laps_by_attempt[lap["attempt_id"]].append(lap)
    for attempt in tables["attempts"]:
        count = len([x for x in laps_by_attempt[attempt["attempt_id"]] if x["lap_completion_status"] == "COMPLETE"])
        if attempt["attempt_class"] != "C_SECTION_ONLY":
            attempt["attempt_class"] = "A_COMPLETE" if count == 4 else ("B_PARTIAL_COMPLETE_LAPS" if count else "D_CHRONOLOGY_ONLY")
        if attempt["car_attempt_index"] is not None:
            attempt["attempt_key"] = f"{attempt['session_id']}|{attempt['entry_key']}|{attempt['car_attempt_index']}"
            provenance.derived("attempts",attempt["attempt_id"],"attempt_key","ATTEMPT_KEY_V1","1",{"session_id":attempt["session_id"],"entry_key":attempt["entry_key"],"car_attempt_index":attempt["car_attempt_index"]},[{"table":"attempts","field":"session_id"},{"table":"attempts","field":"entry_key"},{"table":"attempts","field":"car_attempt_index"}])

    _add_timing_and_gaps(tables, provenance, attempts_by_year, parser_stats)
    reconcile_2024(tables, provenance, attempts_by_year[2024], parser_stats)
    _add_editorial_annotations(tables, provenance, attempts_by_year)
    _add_weather(tables, provenance, parser_stats)
    tables["evidence_items"] = _dedupe(provenance.items, "evidence_item_id")
    tables["field_evidence_links"] = provenance.links
    return tables, issues, parser_stats

def _result_attempt(row, session_id):
    attempt_id = stable_id("attempt", session_id, row["source_locator"])
    positive = [(i, x) for i, x in enumerate(row["laps"], 1) if x and x > 0]
    status, outcome, counted = _status(row["status_raw"], len(positive))
    attempt = {"attempt_id": attempt_id, "session_id": session_id, "entry_key": f"{session_id}|CAR_{row['car_number']}|1",
        "car_number": row["car_number"], "driver_name": row["driver_name"], "team_name": row.get("team_name"),
        "car_attempt_index": None, "attempt_key": None, "car_attempt_order_quality": "UNKNOWN",
        "global_order_lower_bound": None, "global_order_upper_bound": None,
        "attempt_class": "A_COMPLETE" if len(positive)==4 else ("B_PARTIAL_COMPLETE_LAPS" if positive else "D_CHRONOLOGY_ONLY"),
        "official_status_raw": row["status_raw"], "result_status": status, "outcome_label": outcome,
        "result_counted_at_session_end": counted,
        "four_lap_total_seconds": row["total_seconds"] if len(positive)==4 else None,
        "four_lap_average_speed_mph": row["average_speed_mph"] if len(positive)==4 else None,
        "start_time_utc": None, "end_time_utc": None, "event_time_lower_utc": None, "event_time_upper_utc": None,
        "event_time_quality": "UNKNOWN", "time_basis": "UNKNOWN", "withdrawal_evidence": "UNKNOWN",
        "lane_action": "UNKNOWN", "lane_evidence": "UNKNOWN", "requeue_evidence": "UNKNOWN",
        "fuel_strategy_class": "UNKNOWN_FUEL_STRATEGY", "source_native_locator": row["source_locator"],
        "_lap_values": [value for _, value in positive]}
    laps = [{"attempt_lap_id": stable_id("attempt_lap", attempt_id, number), "attempt_id": attempt_id,
        "source_report_lap_index": None, "lap_number": number, "lap_completion_status": "COMPLETE",
        "lap_time_seconds": value, "lap_speed_mph": round(9000/value, 3),
        "reconstruction_rule_id": None, "reconstruction_validation_status": "NOT_APPLICABLE"} for number,value in positive]
    return attempt, laps

def _status(raw, lap_count):
    text = (raw or "").upper()
    if "WITHDRAW" in text: return "WITHDRAWN", None, False
    if "WAVED" in text: return "WAVED_OFF", None, False
    if "FAILED" in text: return "FAILED", None, False
    if "RETIRED" in text: return "RETIRED", None, False
    if "INCOMPLETE" in text: return "INCOMPLETE", None, False
    if "BUMPED" in text: return "VALID_SUPERSEDED", "BUMPED", False
    if "BUBBLE" in text: return "VALID_RETAINED", "ON_BUBBLE", True
    return ("VALID_RETAINED" if lap_count == 4 else "UNKNOWN"), None, (True if lap_count == 4 else None)

def _section_blocks(observations, year):
    blocks = defaultdict(list)
    for obs in observations:
        block, lap = section_results.attempt_block(year, obs["source_report_lap_index"])
        if lap in range(1,5): blocks[(obs["car_number"], block)].append(obs)
    for key in blocks: blocks[key].sort(key=lambda x:x["source_report_lap_index"])
    return blocks

def _match_attempt(attempts, car, block):
    year=block[0]["year"]
    signature=[]
    for obs in block:
        lap_no=section_results.attempt_block(year,obs["source_report_lap_index"])[1]
        candidate=_candidate_lap_time(year,obs)
        if candidate is not None: signature.append((lap_no,round(candidate,4)))
    if not signature: return None
    candidates=[]
    for attempt in attempts:
        if attempt["car_number"] != car: continue
        # result tuple is recovered from total/lap table later; use source locator through injected cache absent here
        candidates.append(attempt)
    exact=[]
    for attempt in candidates:
        values=attempt.get("_lap_values",[])
        if all(lap_no<=len(values) and round(values[lap_no-1],4)==value for lap_no,value in signature):
            exact.append(attempt)
    if len(exact)==1: return exact[0]
    return None

def _section_config(year):
    return SECTION_RULES["formats"]["SECTION_SET_2020_2023" if year<=2023 else "SECTION_SET_2024"]

def _candidate_lap_time(year,obs):
    value=obs.get("official_lap_time")
    if value is None:return None
    lower,upper=_section_config(year)["official_lap_time_range_seconds"]
    return float(value) if lower<=float(value)<=upper else None

def _section_only_attempt(block,session_id,block_index):
    first=block[0]; year=first["year"]; car=first["car_number"]
    attempt_id=stable_id("attempt",session_id,f"section_{year}:car={car}:block={block_index}:unresolved")
    index=block_index if year<=2023 else None
    return {"attempt_id":attempt_id,"session_id":session_id,"entry_key":f"{session_id}|CAR_{car}|1","car_number":car,"driver_name":first["driver_name"],"team_name":None,"car_attempt_index":index,"attempt_key":None,"car_attempt_order_quality":"ORDERING_ONLY" if index else "UNKNOWN","global_order_lower_bound":None,"global_order_upper_bound":None,"attempt_class":"C_SECTION_ONLY","official_status_raw":None,"result_status":"UNKNOWN","outcome_label":None,"result_counted_at_session_end":None,"four_lap_total_seconds":None,"four_lap_average_speed_mph":None,"start_time_utc":None,"end_time_utc":None,"event_time_lower_utc":None,"event_time_upper_utc":None,"event_time_quality":"ORDERING_ONLY" if index else "UNKNOWN","time_basis":"UNKNOWN","withdrawal_evidence":"UNKNOWN","lane_action":"UNKNOWN","lane_evidence":"UNKNOWN","requeue_evidence":"UNKNOWN","fuel_strategy_class":"UNKNOWN_FUEL_STRATEGY","source_native_locator":f"section_{year}.pdf:car={car}:block={block_index}:unresolved","_lap_values":[]}

def _assign_attempt_order(attempt, index, provenance):
    attempt["car_attempt_index"] = index; attempt["car_attempt_order_quality"] = "ORDERING_ONLY"

def _sato_attempt(block, session_id):
    attempt_id=stable_id("attempt",session_id,"section_2022:car51:block1")
    total=round(sum(x["official_lap_time"] for x in block),4)
    return {"attempt_id":attempt_id,"session_id":session_id,"entry_key":f"{session_id}|CAR_51|1","car_number":"51","driver_name":"Takuma Sato","team_name":None,"car_attempt_index":1,"attempt_key":f"{session_id}|{session_id}|CAR_51|1|1","car_attempt_order_quality":"ORDERING_ONLY","global_order_lower_bound":None,"global_order_upper_bound":None,"attempt_class":"A_COMPLETE","official_status_raw":"Disallowed (official recap)","result_status":"DISALLOWED","outcome_label":None,"result_counted_at_session_end":False,"four_lap_total_seconds":total,"four_lap_average_speed_mph":round(36000/total,3),"start_time_utc":None,"end_time_utc":None,"event_time_lower_utc":None,"event_time_upper_utc":None,"event_time_quality":"ORDERING_ONLY","time_basis":"UNKNOWN","withdrawal_evidence":"UNKNOWN","lane_action":"UNKNOWN","lane_evidence":"UNKNOWN","requeue_evidence":"UNKNOWN","fuel_strategy_class":"UNKNOWN_FUEL_STRATEGY","source_native_locator":"section_2022.pdf:car=51:block=1"}

def _laps_from_block(attempt, block):
    rows=[]
    for lap_no, obs in enumerate(block,1):
        rows.append({"attempt_lap_id":stable_id("attempt_lap",attempt["attempt_id"],lap_no),"attempt_id":attempt["attempt_id"],"source_report_lap_index":obs["source_report_lap_index"],"lap_number":lap_no,"lap_completion_status":"COMPLETE","lap_time_seconds":obs["official_lap_time"],"lap_speed_mph":round(9000/obs["official_lap_time"],3),"reconstruction_rule_id":None,"reconstruction_validation_status":"NOT_APPLICABLE"})
    return rows

def _manual_source(sources, source_id, name, uri):
    for source in sources:
        if source["source_id"]==source_id:return source
    source={"source_id":source_id,"source_name":name,"source_type":"OFFICIAL_EDITORIAL","evidence_quality":"OFFICIAL_EDITORIAL","source_priority_rank":3,"source_uri":uri,"content_hash":None,"retrieved_at_utc":RUN_RECORDED_AT,"coverage_note":"Narrow status/action evidence only"}
    sources.append(source); return source

def _add_timing_and_gaps(tables, provenance, attempts_by_year, parser_stats):
    for year, filenames in TIMING_INPUT.items():
        observed=[]
        for filename in filenames:
            note="Known internal gap" if year==2020 else ("Known terminal gap" if year==2023 else "Capture timestamps are approximate event evidence")
            source=register_file(filename,"TIMING71_REPLAY","THIRD_PARTY_CAPTURE",note); tables["sources"].append(source)
            events=timing71.parse_capture_events(EVIDENCE/filename,year); observed.extend((e,source) for e in events)
            parser_stats.append({"source":filename,"status":"PASS","rows":len(events)})
        by_car=defaultdict(list)
        for event,source in observed: by_car[event["car_number"]].append((event,source))
        for car,values in by_car.items():
            values.sort(key=lambda x:x[0]["capture_time_utc"])
            candidates=[a for a in attempts_by_year[year] if a["car_number"]==car]
            candidates.sort(key=lambda a:(a["car_attempt_index"] is None,a["car_attempt_index"] or 999,a["attempt_id"]))
            reason_codes=[]
            if len(values)!=len(candidates): reason_codes.append("CAPTURE_ATTEMPT_COUNT_MISMATCH")
            if year in KNOWN_GAPS: reason_codes.append("SESSION_HAS_RELEVANT_COVERAGE_GAP")
            indices=[a["car_attempt_index"] for a in candidates]
            if any(index is None for index in indices): reason_codes.append("WITHIN_CAR_ORDER_UNRESOLVED")
            if len([x for x in indices if x is not None])!=len(set(x for x in indices if x is not None)): reason_codes.append("WITHIN_CAR_ORDER_CONFLICT")
            positional_mapping_safe=not reason_codes
            for index,(event,source) in enumerate(values):
                attempt=candidates[index] if positional_mapping_safe else None
                event_id=stable_id("chronology",year,event["source_locator"],car)
                item=provenance.item(source["source_id"],event["source_locator"],event["source_text"],event["capture_time_utc"],"RECORDER_CAPTURE","Capture time brackets/approximates qualifier transition; not exact event time")
                relation={"relation_status":"MATCHED_UNAMBIGUOUS" if attempt else "UNRESOLVED","reason_codes":reason_codes,"capture_source_payload":event["source_text"]}
                tables["chronology_events"].append({"chronology_event_id":event_id,"session_id":f"INDY500_DAY1_{year}","attempt_id":attempt["attempt_id"] if attempt else None,"entry_key":f"INDY500_DAY1_{year}|CAR_{car}|1","event_type":"QUALIFIER_CAPTURE" if year==2024 else "ATTEMPT_START","event_time_utc":event["capture_time_utc"],"event_time_lower_utc":None,"event_time_upper_utc":None,"event_time_quality":"APPROXIMATE_OBSERVED","time_basis":"RECORDER_CAPTURE","event_order_lower_bound":None,"event_order_upper_bound":None,"withdrawal_evidence":"UNKNOWN","requeue_evidence":"UNKNOWN","lane_action":"UNKNOWN","lane_evidence":"UNKNOWN","queue_state_evidence":"UNKNOWN","queue_fact_text":None,"event_payload_json":relation})
                provenance.observed("chronology_events",event_id,"event_time_utc",item,"RECONSTRUCTED_FROM_OFFICIAL_EVIDENCE",rule="CAPTURE_TO_APPROX_EVENT_V1",version="1",note="Recorder capture time; approximate event timing")
                if attempt and attempt["start_time_utc"] is None:
                    attempt["start_time_utc"] = event["capture_time_utc"]
                    attempt["event_time_quality"] = "APPROXIMATE_OBSERVED"
                    attempt["time_basis"] = "RECORDER_CAPTURE"
                    provenance.reconstructed("attempts", attempt["attempt_id"], "start_time_utc", item,
                        "CAPTURE_TO_APPROX_EVENT_V1", "1", {"capture":event["capture_time_utc"]},
                        [{"table":"evidence_items","id":item,"field":"source_timestamp_utc"}], "Recorder capture time; not exact event time")
                    for field,value in (("event_time_quality","APPROXIMATE_OBSERVED"),("time_basis","RECORDER_CAPTURE")):
                        provenance.supersede("attempts",attempt["attempt_id"],field)
                        provenance.reconstructed("attempts",attempt["attempt_id"],field,item,"CAPTURE_TO_APPROX_EVENT_V1","1",{"capture":event["capture_time_utc"],"value":value},[{"table":"evidence_items","id":item,"field":"source_timestamp_utc"}],"Capture semantics preserved")
        if year in KNOWN_GAPS:
            lower,upper,reason=KNOWN_GAPS[year]; event_id=stable_id("coverage_gap",year,reason)
            tables["chronology_events"].append({"chronology_event_id":event_id,"session_id":f"INDY500_DAY1_{year}","attempt_id":None,"entry_key":None,"event_type":"COVERAGE_GAP","event_time_utc":None,"event_time_lower_utc":lower,"event_time_upper_utc":upper,"event_time_quality":"BOUNDED_INTERVAL" if lower else "ORDERING_ONLY","time_basis":"RECONSTRUCTED_BOUND" if lower else "UNKNOWN","event_order_lower_bound":None,"event_order_upper_bound":None,"withdrawal_evidence":"UNKNOWN","requeue_evidence":"UNKNOWN","lane_action":"UNKNOWN","lane_evidence":"UNKNOWN","queue_state_evidence":"UNKNOWN","queue_fact_text":reason,"event_payload_json":{"reason_code":reason,"no_forward_fill":True}})

def _add_weather(tables, provenance, parser_stats):
    source={"source_id":"hrrr_ims_2020_2024_features_csv","source_name":HRRR_NUMERIC_INPUT.name,
        "source_type":"HRRR_EXTRACTED_NUMERIC","evidence_quality":"OFFICIAL_RAW","source_priority_rank":1,
        "source_uri":str(HRRR_NUMERIC_INPUT),"content_hash":sha256_file(HRRR_NUMERIC_INPUT),
        "retrieved_at_utc":RUN_RECORDED_AT,
        "coverage_note":"Frozen 259-row IMS point extract from NOAA historical HRRR GRIB via .idx, HTTP Range, and ecCodes; public availability timestamps unresolved."}
    tables["sources"].append(source)
    rows=weather.parse_hrrr_numeric(HRRR_NUMERIC_INPUT)
    for row in rows:
        snapshot=weather.build_snapshot(row,f"INDY500_DAY1_{row['year']}",source["source_id"])
        values=weather.build_values(row,snapshot["forecast_snapshot_id"])
        tables["forecast_snapshots"].append(snapshot); tables["weather_forecasts"].extend(values)
        locator=f"row={row['source_row_number']};cycle={row['cycle_time_utc']};f{row['forecast_hour']:02d}"
        item=provenance.item(source["source_id"],locator,canonical_json({
            "date":row["date"],"cycle_time_utc":row["cycle_time_utc"],"forecast_hour":row["forecast_hour"],
            "valid_time_utc":row["valid_time_utc"],"ims_lat":row["ims_lat"],"ims_lon":row["ims_lon"],
            "forecast_lead_hours":row["forecast_lead_hours"],**row["values"]}),
            source_timestamp=row["cycle_time_utc"],basis="MODEL_CYCLE",
            note="Frozen numeric extraction row; source timestamp is model initialization, not public availability.")
        sid=snapshot["forecast_snapshot_id"]
        for field in ("provider","model_name","issue_time_utc","location_type","spatial_locator","latitude","longitude","extraction_metadata_json"):
            provenance.observed("forecast_snapshots",sid,field,item)
        provenance.derived("forecast_snapshots",sid,"source_id","FORECAST_SOURCE_REGISTRATION_V1","1",
            {"source_id":source["source_id"],"content_hash":source["content_hash"]},[{"table":"sources","id":source["source_id"]}])
        provenance.derived("forecast_snapshots",sid,"forecast_lead_hours","HRRR_FORECAST_LEAD_V1","1",
            {"forecast_hour":row["forecast_hour"],"forecast_lead_hours":row["forecast_lead_hours"]},
            [{"table":"evidence_items","id":item,"field":"captured_value_text"}])
        provenance.observed("forecast_snapshots",sid,"forecast_lead_hours",item,primary=False,note="Supplied forecast_hour and forecast_lead_hours agree")
        provenance.derived("forecast_snapshots",sid,"forecast_snapshot_id","HRRR_SNAPSHOT_ID_V1","1",
            {"provider":"NOAA","model":"HRRR","cycle":row["cycle_time_utc"],"lead":row["forecast_lead_hours"],"latitude":row["ims_lat"],"longitude":row["ims_lon"]},
            [{"table":"forecast_snapshots","field":"issue_time_utc"},{"table":"forecast_snapshots","field":"forecast_lead_hours"},{"table":"forecast_snapshots","field":"latitude"},{"table":"forecast_snapshots","field":"longitude"}])
        for field in ("valid_start_utc","valid_end_utc"):
            provenance.derived("forecast_snapshots",sid,field,"HRRR_VALID_TIME_V1","1",
                {"cycle_time_utc":row["cycle_time_utc"],"forecast_lead_hours":row["forecast_lead_hours"],"valid_time_utc":row["valid_time_utc"]},
                [{"table":"forecast_snapshots","field":"issue_time_utc"},{"table":"forecast_snapshots","field":"forecast_lead_hours"}])
            provenance.observed("forecast_snapshots",sid,field,item,primary=False,note="Supplied valid time corroborates deterministic cycle plus lead arithmetic")
        provenance.observed("forecast_snapshots",sid,"availability_time_utc",item,"UNAVAILABLE",note="Historical public availability is unresolved; a versioned latency policy is required before time-safe joins")
        provenance.observed("forecast_snapshots",sid,"availability_time_quality",item,"MANUALLY_ANNOTATED",rule="HRRR_AVAILABILITY_STATE_V1",version="1",note="UNKNOWN; cycle time is not substituted")
        for value in values:
            vid=value["weather_forecast_value_id"]; name=value["variable_code"]
            provenance.observed("weather_forecasts",vid,"variable_code",item)
            provenance.observed("weather_forecasts",vid,"unit",item)
            if name in weather.RAW_VARIABLES:
                provenance.observed("weather_forecasts",vid,"value_numeric",item)
            else:
                expected=weather.expected_derived(row["values"])[name]
                refs={
                    "temp_c":["TMP_2m"],"dewpoint_c":["DPT_2m"],"relative_humidity_pct":["TMP_2m","DPT_2m"],
                    "wind_speed_10m_ms":["UGRD_10m","VGRD_10m"],"wind_direction_deg":["UGRD_10m","VGRD_10m"],
                    "pressure_hpa":["PRES_surface"],"gust_ms":["GUST_surface"],"cloud_cover_pct":["TCDC_atmosphere"],
                    "shortwave_radiation_wm2":["DSWRF_surface"]}[name]
                provenance.derived("weather_forecasts",vid,"value_numeric",f"HRRR_{name.upper()}_V1","1",
                    {"source_values":{key:row["values"][key] for key in refs},"computed_value":expected},
                    [{"table":"weather_forecasts","field":"value_numeric","variable_code":key,"forecast_snapshot_id":sid} for key in refs])
                provenance.observed("weather_forecasts",vid,"value_numeric",item,primary=False,note="Supplied derived column corroborates deterministic formula")
    parser_stats.append({"source":HRRR_NUMERIC_INPUT.name,"status":"PASS_NUMERIC","rows":len(rows)})

def _add_editorial_annotations(tables, provenance, attempts_by_year):
    source=_manual_source(tables["sources"],"official_editorial_2021_day1","2021 INDYCAR Day 1 recap","https://www.indycar.com/News/2021/05/05-22-Day1-Qualifying")
    power_first=[a for a in attempts_by_year[2021] if a["car_number"]=="12" and a["car_attempt_index"]==1]
    if len(power_first)==1:
        attempt=power_first[0]
        item=provenance.item(source["source_id"],"passage:Power withdrawal and fast lane","Will Power withdrew his first result to leave the normal line and use the fast line before his later run.",note="Official editorial action evidence; no exact withdrawal timestamp stated.")
        attempt["result_status"]="WITHDRAWN"; attempt["result_counted_at_session_end"]=False
        attempt["withdrawal_evidence"]="EDITORIALLY_DOCUMENTED_WITHDRAWAL"
        attempt["lane_action"]="PRIORITY_LANE"; attempt["lane_evidence"]="EDITORIALLY_DOCUMENTED_LANE"
        for field in ("result_status","result_counted_at_session_end","withdrawal_evidence","lane_action","lane_evidence"):
            provenance.supersede("attempts",attempt["attempt_id"],field)
            provenance.observed("attempts",attempt["attempt_id"],field,item,"MANUALLY_ANNOTATED",rule="OFFICIAL_EDITORIAL_ACTION_V1",version="1")

def _date_code(year): return {2020:"20200815",2021:"20210522",2022:"20220521",2023:"20230520",2024:"20240518"}[year]
def _section_names(year):
    if year <= 2023:
        return ["T/SSF to T1","T1 to SS1","SS1 to T2","T2 to BS","BS to T3","T3 to SS2","SS2 to T4","T4 to FS","FS to SF"]
    return ["Front Stretch 5","Turn 1 Entry","Turn 1 Exit","Turn 2 Entry","Turn 2 Exit","Back Stretch 1","Back Stretch 2","Back Stretch 3","Back Stretch 4","Turn 3 Entry","Turn 3 Exit","Turn 4 Entry","Turn 4 Exit","Front Stretch 1","Front Stretch 2","Front Stretch 3","Front Stretch 4"]
def _iso_date(value,year):
    if value:
        try:return datetime.strptime(value,"%m/%d/%Y").date().isoformat()
        except ValueError: pass
    return {2020:"2020-08-15",2021:"2021-05-22",2022:"2022-05-21",2023:"2023-05-20",2024:"2024-05-18"}[year]
def _dedupe(rows,key): return list({row[key]:row for row in rows}.values())
