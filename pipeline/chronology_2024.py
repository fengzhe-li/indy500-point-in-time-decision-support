from datetime import datetime, timedelta, timezone
from decimal import Decimal

from .config import EVIDENCE, ROOT, RUN_RECORDED_AT
from .io_utils import canonical_json, stable_id, write_csv
from .source_registry import register_file


SESSION_ID = "INDY500_DAY1_2024"
SESSION_START = "2024-05-18T15:00:00Z"
SESSION_END = "2024-05-18T21:50:00Z"

SOURCE_DEFINITIONS = {
    "indycar_2024_qualifying_explainer": {
        "source_name": "Official INDYCAR 2024 Indy 500 qualifying explainer",
        "source_type": "OFFICIAL_RULES_EXPLAINER",
        "evidence_quality": "OFFICIAL_EDITORIAL",
        "source_priority_rank": 3,
        "source_uri": "https://www.indycar.com/-/media/Files/2024/NICS/06-500/indycar-qual-explainer-2024Indy500.pdf",
    },
    "indycar_2024_veekay_buzz": {
        "source_name": "Official INDYCAR Paddock Buzz VeeKay Late Dash",
        "source_type": "OFFICIAL_EDITORIAL",
        "evidence_quality": "OFFICIAL_EDITORIAL",
        "source_priority_rank": 3,
        "source_uri": "https://www.indycar.com/news/2024/05/05-18-buzz",
    },
    "indycar_2024_day1_report": {
        "source_name": "Official INDYCAR Power Fastest Day 1 report",
        "source_type": "OFFICIAL_EDITORIAL",
        "evidence_quality": "OFFICIAL_EDITORIAL",
        "source_priority_rank": 3,
        "source_uri": "https://www.indycar.com/News/2024/05/05-18-Quals-Day1",
    },
    "indycar_2024_event_page": {
        "source_name": "Official INDYCAR 2024 Indianapolis 500 event page",
        "source_type": "OFFICIAL_EVENT_PAGE",
        "evidence_quality": "OFFICIAL_EDITORIAL",
        "source_priority_rank": 3,
        "source_uri": "https://www.indycar.com/Schedule/2024/Indianapolis-500",
    },
    "nbc_2024_day1_live_blog": {
        "source_name": "NBC Sports Day 1 live qualifying blog",
        "source_type": "REPUTABLE_EDITORIAL",
        "evidence_quality": "REPUTABLE_EDITORIAL",
        "source_priority_rank": 4,
        "source_uri": "https://www.nbcsports.com/motor-sports/news/indy-500-live-qualifying-blog-updates-day-1-problem-kyle-larson-rinus-veekay",
    },
    "motorsport_2024_veekay_report": {
        "source_name": "Motorsport.com Penske and VeeKay Day 1 report",
        "source_type": "REPUTABLE_EDITORIAL",
        "evidence_quality": "REPUTABLE_EDITORIAL",
        "source_priority_rank": 4,
        "source_uri": "https://www.motorsport.com/indycar/news/indy-500-penske-heroic-veekay-rebounds-crash/10612685/",
    },
}


ANCHORS = (
    {"key":"VEEKAY_CRASH","selector":{"car":"21","status":"WAVED_OFF","complete_laps":0},"source":"indycar_2024_veekay_buzz","locator":"anchor:11:14 ET VeeKay crash","text":"VeeKay's first qualifying attempt ended in a Turn 3 crash reported at 11:14 a.m. ET.","anchor_type":"CRASH","time":"2024-05-18T15:14:00Z","quality":"APPROXIMATE_OBSERVED","classification":"RECONSTRUCTED_FROM_OFFICIAL_EVIDENCE","capture":"2024-05-18T15:15:01Z","order":{"within_car":1,"global_lower":4,"global_upper":4,"notes":["INITIAL_QUALIFYING_ORDER_4"]},"note":"Editorial clock time has minute precision; crash time is not timed-run start."},
    {"key":"VEEKAY_WAVEOFF","selector":{"car":"21","status":"WAVED_OFF","complete_laps":1},"source":"indycar_2024_veekay_buzz","locator":"anchor:15:26 ET VeeKay waved off","text":"VeeKay made a later qualifying attempt at 3:26 p.m. ET and waved it off.","anchor_type":"ATTEMPT_OCCURRENCE","time":"2024-05-18T19:26:00Z","quality":"APPROXIMATE_OBSERVED","classification":"RECONSTRUCTED_FROM_OFFICIAL_EVIDENCE","capture":"2024-05-18T19:24:59Z","order":{"within_car":2,"notes":["AFTER_VEEKAY_CRASH","BEFORE_VEEKAY_231_166"]},"note":"The reported minute locates the attempt occurrence, not release or first timed-lap start."},
    {"key":"VEEKAY_231_166","selector":{"car":"21","speed":231.166},"source":"indycar_2024_veekay_buzz","locator":"anchor:25 minutes after 15:26 ET","text":"VeeKay returned about 25 minutes after the 3:26 p.m. waved-off attempt and posted 231.166 mph.","anchor_type":"ATTEMPT_OCCURRENCE","lower":"2024-05-18T19:50:00Z","upper":"2024-05-18T19:52:00Z","quality":"BOUNDED_INTERVAL","classification":"RECONSTRUCTED_FROM_OFFICIAL_EVIDENCE","capture":"2024-05-18T19:51:55Z","order":{"within_car":3,"notes":["ABOUT_25_MINUTES_AFTER_VEEKAY_ATTEMPT_2","BEFORE_VEEKAY_FINAL"]},"note":"The 25-minute interval is approximate; the two-minute window preserves that uncertainty."},
    {"key":"VEEKAY_FINAL","selector":{"car":"21","speed":232.419},"source":"indycar_2024_veekay_buzz","locator":"anchor:five seconds before cutoff","text":"VeeKay completed the 232.419 mph run about five seconds before the 5:50 p.m. ET cutoff; it was the penultimate attempt.","anchor_type":"TIMED_RUN_END","lower":"2024-05-18T21:49:50Z","upper":"2024-05-18T21:50:00Z","quality":"BOUNDED_INTERVAL","classification":"RECONSTRUCTED_FROM_OFFICIAL_EVIDENCE","capture":"2024-05-18T21:46:22Z","order":{"within_car":4,"global_lower":73,"global_upper":73,"notes":["PENULTIMATE_OFFICIAL_ATTEMPT","IMMEDIATELY_BEFORE_RAHAL_FINAL"]},"note":"Five-seconds-to-spare is approximate; the finish window is bounded and the derived start inherits the same uncertainty."},
    {"key":"ROSSI_FIRST","selector":{"car":"7","speed":232.962},"source":"nbc_2024_day1_live_blog","locator":"anchor:13:57 ET Rossi official time","text":"Rossi posted an official qualifying time at 1:57 p.m. ET, provisionally fourth, before O'Ward went next.","anchor_type":"RESULT_POSTED","time":"2024-05-18T17:57:00Z","quality":"APPROXIMATE_OBSERVED","classification":"INFERRED_UNCERTAIN","capture":"2024-05-18T17:53:59Z","order":{"within_car":1,"notes":["BEFORE_OWARD_NEXT_ON_TRACK"]},"note":"The blog clock anchors result posting/attempt occurrence, not a timed-run endpoint."},
    {"key":"ROSSI_233_069","selector":{"car":"7","speed":233.069},"source":"motorsport_2024_veekay_report","locator":"anchor:70 minutes remaining Rossi 233.069","text":"Rossi's 233.069 mph run occurred with about 70 minutes remaining in the session.","anchor_type":"ATTEMPT_OCCURRENCE","lower":"2024-05-18T20:39:00Z","upper":"2024-05-18T20:41:00Z","quality":"BOUNDED_INTERVAL","classification":"INFERRED_UNCERTAIN","capture":"2024-05-18T20:37:01Z","order":{"within_car":2,"notes":["AFTER_ROSSI_232_962"]},"note":"Remaining-time wording supports only an approximate two-minute occurrence window."},
    {"key":"POWER_INITIAL","selector":{"car":"12","speed":233.758},"source":"nbc_2024_day1_live_blog","locator":"ordering:Power ninth initial qualifier","text":"Will Power was ninth in the initial qualifying order and completed the run that remained fastest on Day 1.","anchor_type":"INITIAL_ORDER","quality":"APPROXIMATE_OBSERVED","classification":"INFERRED_UNCERTAIN","capture":"2024-05-18T15:56:00Z","order":{"within_car":1,"global_lower":9,"global_upper":9,"notes":["INITIAL_QUALIFYING_ORDER_9"]},"note":"The independent order fact and unique car/run identity support the capture linkage; capture time remains approximate."},
    {"key":"LARSON_INITIAL","selector":{"car":"17","status":"WAVED_OFF","complete_laps":3},"source":"nbc_2024_day1_live_blog","locator":"ordering:Larson sixth initial qualifier","text":"Kyle Larson was sixth in the initial order and aborted his first run during lap four after three recorded laps.","anchor_type":"INITIAL_ORDER","quality":"ORDERING_ONLY","classification":"INFERRED_UNCERTAIN","order":{"within_car":1,"global_lower":6,"global_upper":6,"notes":["INITIAL_QUALIFYING_ORDER_6","ABORTED_DURING_LAP_4"]},"note":"The available Timing71 car 17 captures conflict with the stated initial order, so none is linked here."},
    {"key":"RAHAL_FINAL","selector":{"car":"15","status":"WAVED_OFF","complete_laps":1},"source":"indycar_2024_day1_report","locator":"anchor:Rahal immediately before cutoff","text":"Rahal was the final car to enter the oval immediately before the 5:50 p.m. ET cutoff and waved off after one lap.","anchor_type":"TRACK_ENTRY","lower":"2024-05-18T21:49:50Z","upper":"2024-05-18T21:50:00Z","quality":"BOUNDED_INTERVAL","classification":"RECONSTRUCTED_FROM_OFFICIAL_EVIDENCE","capture":"2024-05-18T21:50:26Z","order":{"global_lower":74,"global_upper":74,"notes":["FINAL_OFFICIAL_ATTEMPT","AFTER_VEEKAY_FINAL"]},"note":"Track entry is bounded by the preceding VeeKay finish and cutoff; it is not release time or timed-run start."},
)


def reconcile_2024(tables, provenance, attempts, parser_stats=None):
    pack=register_file("2024_indy500_day1_chronology_evidence_pack.docx","CHRONOLOGY_EVIDENCE_PACK","SECONDARY_COMPILATION","Carries cited source identities and normalized chronology anchors; underlying pages were not re-fetched in this phase")
    tables["sources"].append(pack)
    provenance.item(pack["source_id"],"pages=1-3","Narrow 2024 chronology evidence pack with session, editorial clock, and ordering anchors.",note="Compilation layer only; underlying cited source identity is retained for each used anchor.")
    if parser_stats is not None: parser_stats.append({"source":"2024_indy500_day1_chronology_evidence_pack.docx","status":"PASS","rows":len(ANCHORS)+4})
    sources={key:_add_source(tables,value,key) for key,value in SOURCE_DEFINITIONS.items()}
    by_attempt={a["attempt_id"]:_base_constraint(a,tables["attempt_laps"]) for a in attempts}
    capture_by_time={e["event_time_utc"]:e for e in tables["chronology_events"] if e["session_id"]==SESSION_ID and e["time_basis"]=="RECORDER_CAPTURE"}

    _set_session_boundaries(tables,provenance,sources)
    for anchor in ANCHORS:
        attempt=_select_attempt(attempts,tables["attempt_laps"],anchor["selector"])
        if attempt is None:
            raise ValueError(f"2024 anchor selector is not unique: {anchor['key']}")
        source=sources[anchor["source"]]
        item=provenance.item(source["source_id"],anchor["locator"],anchor["text"],anchor.get("time"),"EDITORIAL_DISPLAY",anchor["note"])
        row=by_attempt[attempt["attempt_id"]]
        _apply_anchor(row,anchor,source["source_id"],item)
        _apply_order(attempt,anchor,item,provenance)
        _add_anchor_event(tables,provenance,attempt,anchor,item)
        capture_time=anchor.get("capture")
        if capture_time:
            capture=capture_by_time.get(capture_time)
            if capture is None or capture["entry_key"] != attempt["entry_key"]:
                raise ValueError(f"2024 capture constraint not uniquely satisfied: {anchor['key']}")
            capture["attempt_id"]=attempt["attempt_id"]
            capture["event_payload_json"]={"relation_status":"MATCHED_CONSTRAINED_2024","reason_codes":["INDEPENDENT_EDITORIAL_ANCHOR","CAR_IDENTITY","ATTEMPT_STRUCTURE","SEQUENCE_COMPATIBLE"],"anchor_key":anchor["key"],"capture_source_payload":capture["event_payload_json"].get("capture_source_payload")}
            row["timing71_capture_event_id"]=capture["chronology_event_id"]
            row["capture_time_utc"]=capture["event_time_utc"]
            provenance.derived("chronology_constraints",row["chronology_constraint_id"],"timing71_capture_event_id","CONSTRAINED_CAPTURE_MATCH_2024_V1","1",{"anchor_key":anchor["key"],"capture_event_id":capture["chronology_event_id"]},[{"table":"chronology_events","id":capture["chronology_event_id"]}])
            provenance.derived("chronology_constraints",row["chronology_constraint_id"],"capture_time_utc","CONSTRAINT_COPY_CAPTURE_TIME_V1","1",{"capture_time_utc":capture["event_time_utc"]},[{"table":"chronology_events","id":capture["chronology_event_id"],"field":"event_time_utc"}])
        _add_constraint_provenance(provenance,row,anchor,item)

    for row in by_attempt.values():
        attempt=next(a for a in attempts if a["attempt_id"]==row["attempt_id"])
        row["car_attempt_index"]=attempt["car_attempt_index"]
        if row["event_time_quality"]=="UNKNOWN":
            row["reconciliation_status"]="UNRESOLVED"
            row["unresolved_reason"]="NO_UNIQUE_ATTEMPT_LEVEL_CLOCK_OR_ORDER_CONSTRAINT"
            row["uncertainty_note"]="Timing71 capture candidates remain unlinked because no independent evidence makes one mapping unique."
    tables["chronology_constraints"]=[by_attempt[key] for key in sorted(by_attempt)]
    _constraint_identity_provenance(tables,provenance)
    _duration_provenance(tables,provenance)


def _add_source(tables,definition,source_id):
    existing=next((s for s in tables["sources"] if s["source_id"]==source_id),None)
    if existing:return existing
    row={"source_id":source_id,**definition,"content_hash":None,"retrieved_at_utc":RUN_RECORDED_AT,"coverage_note":"Anchor identity and normalized meaning supplied in the evidence pack; underlying page not independently re-fetched in Phase 3.5A"}
    tables["sources"].append(row)
    return row


def _base_constraint(attempt,laps):
    attempt_laps=[l for l in laps if l["attempt_id"]==attempt["attempt_id"] and l["lap_completion_status"]=="COMPLETE" and l["lap_time_seconds"] is not None]
    duration=float(sum((Decimal(str(l["lap_time_seconds"])) for l in attempt_laps),Decimal("0"))) if attempt_laps else None
    coverage="COMPLETE_FOUR_LAP" if len(attempt_laps)==4 else ("OBSERVED_PARTIAL" if attempt_laps else "UNAVAILABLE")
    return {"chronology_constraint_id":stable_id("chronology_constraint",attempt["attempt_id"],"PHASE_3_5A"),"session_id":attempt["session_id"],"attempt_id":attempt["attempt_id"],"entry_key":attempt["entry_key"],"car_number":attempt["car_number"],"driver_name":attempt["driver_name"],"car_attempt_index":attempt["car_attempt_index"],"result_status":attempt["result_status"],"timing71_capture_event_id":None,"capture_time_utc":None,"anchor_event_type":None,"anchor_time_utc":None,"anchor_time_lower_utc":None,"anchor_time_upper_utc":None,"timed_run_duration_seconds":round(duration,4) if duration is not None else None,"duration_coverage":coverage,"timed_run_start_utc":None,"timed_run_end_utc":None,"timed_run_start_lower_utc":None,"timed_run_start_upper_utc":None,"timed_run_end_lower_utc":None,"timed_run_end_upper_utc":None,"event_time_quality":"UNKNOWN","value_classification":None,"anchor_source_id":None,"anchor_evidence_item_id":None,"reconciliation_status":"UNRESOLVED","ordering_constraints_json":{},"unresolved_reason":None,"uncertainty_note":None}


def _select_attempt(attempts,laps,selector):
    result=[]
    for attempt in attempts:
        if attempt["car_number"]!=selector["car"]:continue
        if selector.get("status") and attempt["result_status"]!=selector["status"]:continue
        if selector.get("speed") is not None and attempt["four_lap_average_speed_mph"]!=selector["speed"]:continue
        lap_count=sum(l["attempt_id"]==attempt["attempt_id"] and l["lap_completion_status"]=="COMPLETE" for l in laps)
        if selector.get("complete_laps") is not None and lap_count!=selector["complete_laps"]:continue
        result.append(attempt)
    return result[0] if len(result)==1 else None


def _apply_anchor(row,anchor,source_id,item):
    row.update({"anchor_event_type":anchor["anchor_type"],"anchor_time_utc":anchor.get("time"),"anchor_time_lower_utc":anchor.get("lower"),"anchor_time_upper_utc":anchor.get("upper"),"event_time_quality":anchor["quality"],"value_classification":anchor["classification"],"anchor_source_id":source_id,"anchor_evidence_item_id":item,"reconciliation_status":"ORDERING_ONLY" if anchor["quality"]=="ORDERING_ONLY" else "ANCHORED","ordering_constraints_json":anchor.get("order",{}),"unresolved_reason":None,"uncertainty_note":anchor["note"]})
    if anchor["anchor_type"]=="TIMED_RUN_END":
        row["timed_run_end_lower_utc"]=anchor["lower"]
        row["timed_run_end_upper_utc"]=anchor["upper"]
        if row["duration_coverage"]=="COMPLETE_FOUR_LAP":
            row["timed_run_start_lower_utc"]=_shift(anchor["lower"],-row["timed_run_duration_seconds"])
            row["timed_run_start_upper_utc"]=_shift(anchor["upper"],-row["timed_run_duration_seconds"])


def _apply_order(attempt,anchor,item,provenance):
    order=anchor.get("order",{})
    index=order.get("within_car")
    if index is not None:
        attempt["car_attempt_index"]=index; attempt["car_attempt_order_quality"]="ORDERING_ONLY"
        attempt["attempt_key"]=f"{attempt['session_id']}|{attempt['entry_key']}|{index}"
        for field,value in (("car_attempt_index",index),("car_attempt_order_quality","ORDERING_ONLY"),("attempt_key",attempt["attempt_key"])):
            provenance.supersede("attempts",attempt["attempt_id"],field)
            provenance.reconstructed("attempts",attempt["attempt_id"],field,item,"EDITORIAL_ORDER_CONSTRAINT_2024_V1","1",{"anchor_key":anchor["key"],"value":value},[{"table":"evidence_items","id":item}],anchor["note"])
    for field,key in (("global_order_lower_bound","global_lower"),("global_order_upper_bound","global_upper")):
        if key in order:
            attempt[field]=order[key]
            provenance.reconstructed("attempts",attempt["attempt_id"],field,item,"EDITORIAL_ORDER_CONSTRAINT_2024_V1","1",{"anchor_key":anchor["key"],"value":order[key]},[{"table":"evidence_items","id":item}],anchor["note"])


def _add_anchor_event(tables,provenance,attempt,anchor,item):
    event_id=stable_id("chronology",2024,"editorial_anchor",anchor["key"])
    event_type="TIMED_RUN_END" if anchor["anchor_type"]=="TIMED_RUN_END" else "ATTEMPT_EVENT_ANCHOR"
    row={"chronology_event_id":event_id,"session_id":SESSION_ID,"attempt_id":attempt["attempt_id"],"entry_key":attempt["entry_key"],"event_type":event_type,"event_time_utc":anchor.get("time"),"event_time_lower_utc":anchor.get("lower"),"event_time_upper_utc":anchor.get("upper"),"event_time_quality":anchor["quality"],"time_basis":"EDITORIAL_DISPLAY" if anchor.get("time") else "RECONSTRUCTED_BOUND","event_order_lower_bound":anchor.get("order",{}).get("global_lower"),"event_order_upper_bound":anchor.get("order",{}).get("global_upper"),"withdrawal_evidence":"UNKNOWN","requeue_evidence":"UNKNOWN","lane_action":"UNKNOWN","lane_evidence":"UNKNOWN","queue_state_evidence":"UNKNOWN","queue_fact_text":None,"event_payload_json":{"anchor_key":anchor["key"],"anchor_semantics":anchor["anchor_type"],"not_release_time":True,"not_queue_entry_time":True}}
    tables["chronology_events"].append(row)
    for field in ("event_type","event_time_utc","event_time_lower_utc","event_time_upper_utc","event_time_quality","time_basis","event_order_lower_bound","event_order_upper_bound"):
        if row[field] is not None: provenance.observed("chronology_events",event_id,field,item,anchor["classification"],rule="EDITORIAL_ANCHOR_2024_V1",version="1",note=anchor["note"])


def _set_session_boundaries(tables,provenance,sources):
    session=next(e for e in tables["qualifying_events"] if e["session_id"]==SESSION_ID)
    source=sources["indycar_2024_qualifying_explainer"]
    item=provenance.item(source["source_id"],"session window 11:00-17:50 ET","Day 1 qualifying ran from 11:00 a.m. to 5:50 p.m. ET.",note="EDT conversion gives 15:00-21:50 UTC.")
    session["scheduled_start_utc"]=SESSION_START; session["scheduled_end_utc"]=SESSION_END
    for field,value in (("scheduled_start_utc",SESSION_START),("scheduled_end_utc",SESSION_END)):
        provenance.observed("qualifying_events",SESSION_ID,field,item,"RECONSTRUCTED_FROM_OFFICIAL_EVIDENCE",rule="SESSION_WINDOW_2024_V1",version="1",note="Official session boundary; not an individual attempt time.")
    for label,value,kind in (("START",SESSION_START,"SESSION_START"),("CUTOFF",SESSION_END,"SESSION_CUTOFF")):
        event_id=stable_id("chronology",2024,"session_boundary",label)
        tables["chronology_events"].append({"chronology_event_id":event_id,"session_id":SESSION_ID,"attempt_id":None,"entry_key":None,"event_type":"SESSION_BOUNDARY","event_time_utc":value,"event_time_lower_utc":None,"event_time_upper_utc":None,"event_time_quality":"EXACT_OBSERVED","time_basis":"OFFICIAL_EVENT_TIME","event_order_lower_bound":None,"event_order_upper_bound":None,"withdrawal_evidence":"UNKNOWN","requeue_evidence":"UNKNOWN","lane_action":"UNKNOWN","lane_evidence":"UNKNOWN","queue_state_evidence":"UNKNOWN","queue_fact_text":None,"event_payload_json":{"boundary_type":kind}})
        provenance.observed("chronology_events",event_id,"event_time_utc",item,"RECONSTRUCTED_FROM_OFFICIAL_EVIDENCE",rule="SESSION_WINDOW_2024_V1",version="1")


def _add_constraint_provenance(provenance,row,anchor,item):
    entity=row["chronology_constraint_id"]
    for field in ("anchor_event_type","anchor_time_utc","anchor_time_lower_utc","anchor_time_upper_utc","event_time_quality","value_classification","anchor_source_id","anchor_evidence_item_id","ordering_constraints_json","uncertainty_note"):
        if row[field] not in (None,{},""):
            provenance.observed("chronology_constraints",entity,field,item,anchor["classification"],rule="EDITORIAL_ANCHOR_2024_V1",version="1",note=anchor["note"])
    if row["timed_run_end_lower_utc"]:
        for field in ("timed_run_end_lower_utc","timed_run_end_upper_utc"):
            provenance.reconstructed("chronology_constraints",entity,field,item,"VEEKAY_FINISH_BOUND_2024_V1","1",{"source_bound":row[field]},[{"table":"evidence_items","id":item}],anchor["note"])
        for field in ("timed_run_start_lower_utc","timed_run_start_upper_utc"):
            provenance.derived("chronology_constraints",entity,field,"TIMED_RUN_ENDPOINT_FROM_DURATION_V1","1",{"end_bound":row["timed_run_end_lower_utc" if field.endswith("lower_utc") else "timed_run_end_upper_utc"],"duration_seconds":row["timed_run_duration_seconds"],"propagated_quality":propagate_time_quality(row["event_time_quality"])},[{"table":"chronology_constraints","id":entity,"field":"timed_run_end_lower_utc" if field.endswith("lower_utc") else "timed_run_end_upper_utc"},{"table":"chronology_constraints","id":entity,"field":"timed_run_duration_seconds"}])


def _duration_provenance(tables,provenance):
    laps_by_attempt={}
    for lap in tables["attempt_laps"]: laps_by_attempt.setdefault(lap["attempt_id"],[]).append(lap)
    for row in tables["chronology_constraints"]:
        laps=[l for l in laps_by_attempt.get(row["attempt_id"],[]) if l["lap_completion_status"]=="COMPLETE" and l["lap_time_seconds"] is not None]
        refs=[{"table":"attempt_laps","id":l["attempt_lap_id"],"field":"lap_time_seconds"} for l in laps]
        provenance.derived("chronology_constraints",row["chronology_constraint_id"],"duration_coverage","OBSERVED_LAP_DURATION_SUM_V1","1",{"complete_lap_count":len(laps)},refs)
        if row["timed_run_duration_seconds"] is not None:
            provenance.derived("chronology_constraints",row["chronology_constraint_id"],"timed_run_duration_seconds","OBSERVED_LAP_DURATION_SUM_V1","1",{"lap_times":[l["lap_time_seconds"] for l in laps],"coverage":row["duration_coverage"]},refs)


def _constraint_identity_provenance(tables,provenance):
    for row in tables["chronology_constraints"]:
        entity=row["chronology_constraint_id"]
        attempt_ref={"table":"attempts","id":row["attempt_id"]}
        for field in ("session_id","attempt_id","entry_key","car_number","driver_name","car_attempt_index","result_status"):
            if row[field] is not None:
                provenance.derived("chronology_constraints",entity,field,"CONSTRAINT_ATTEMPT_JOIN_2024_V1","1",{"attempt_id":row["attempt_id"],"field":field,"value":row[field]},[{**attempt_ref,"field":field}])
        provenance.derived("chronology_constraints",entity,"reconciliation_status","CONSTRAINED_RECONCILIATION_2024_V1","1",{"status":row["reconciliation_status"],"quality":row["event_time_quality"]},[{**attempt_ref,"field":"attempt_id"}])
        if row["event_time_quality"]=="UNKNOWN":
            provenance.derived("chronology_constraints",entity,"event_time_quality","CONSTRAINED_RECONCILIATION_2024_V1","1",{"status":"UNKNOWN","reason":row["unresolved_reason"]},[{**attempt_ref,"field":"attempt_id"}])
            provenance.derived("chronology_constraints",entity,"unresolved_reason","CONSTRAINED_RECONCILIATION_2024_V1","1",{"reason":row["unresolved_reason"]},[{**attempt_ref,"field":"attempt_id"}])


def _shift(value,seconds):
    parsed=datetime.fromisoformat(value.replace("Z","+00:00"))+timedelta(seconds=seconds)
    return parsed.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")


def propagate_time_quality(input_quality):
    if input_quality=="APPROXIMATE_OBSERVED":return "APPROXIMATE_OBSERVED"
    if input_quality in ("BOUNDED_INTERVAL","EXACT_OBSERVED"):return "BOUNDED_INTERVAL"
    return input_quality


def golden_checks(tables):
    constraints=tables["chronology_constraints"]
    veekay=sorted((c for c in constraints if c["car_number"]=="21"),key=lambda c:c["car_attempt_index"] or 999)
    rahal=next(c for c in constraints if c["car_number"]=="15" and c["result_status"]=="WAVED_OFF" and c["duration_coverage"]=="OBSERVED_PARTIAL")
    veekay_pass=(
        [c["car_attempt_index"] for c in veekay]==[1,2,3,4]
        and veekay[0]["anchor_event_type"]=="CRASH" and not veekay[0]["timed_run_start_utc"] and not veekay[0]["timed_run_start_lower_utc"]
        and veekay[1]["anchor_time_utc"]=="2024-05-18T19:26:00Z"
        and veekay[2]["anchor_time_lower_utc"] <= "2024-05-18T19:51:00Z" <= veekay[2]["anchor_time_upper_utc"]
        and float(veekay[3]["timed_run_duration_seconds"])==154.893
        and veekay[3]["timed_run_end_lower_utc"] <= "2024-05-18T21:49:55Z" <= veekay[3]["timed_run_end_upper_utc"]
        and veekay[3]["ordering_constraints_json"].get("global_lower")==73
        and rahal["ordering_constraints_json"].get("global_lower")==74
    )
    rahal_pass=(rahal["anchor_event_type"]=="TRACK_ENTRY" and rahal["event_time_quality"]=="BOUNDED_INTERVAL"
        and rahal["anchor_time_upper_utc"]==SESSION_END and rahal["duration_coverage"]=="OBSERVED_PARTIAL"
        and "AFTER_VEEKAY_FINAL" in rahal["ordering_constraints_json"].get("notes",[])
        and not rahal["timed_run_start_utc"])
    return {"VEEKAY_2024_MULTI_ANCHOR_GOLDEN":veekay_pass,"RAHAL_2024_FINAL_ATTEMPT_CONSISTENCY":rahal_pass}


def phase35_metrics(tables):
    constraints=tables["chronology_constraints"]
    captures=[e for e in tables["chronology_events"] if e["session_id"]==SESSION_ID and e["time_basis"]=="RECORDER_CAPTURE"]
    qualities={q:sum(c["event_time_quality"]==q for c in constraints) for q in ("APPROXIMATE_OBSERVED","BOUNDED_INTERVAL","ORDERING_ONLY","UNKNOWN")}
    return {"attempts":len(constraints),"captures":len(captures),"linked_captures":sum(e["attempt_id"] is not None for e in captures),"unlinked_captures":sum(e["attempt_id"] is None for e in captures),**qualities,"deterministic_duration_values":sum(c["timed_run_duration_seconds"] is not None for c in constraints),"complete_durations":sum(c["duration_coverage"]=="COMPLETE_FOUR_LAP" for c in constraints),"partial_durations":sum(c["duration_coverage"]=="OBSERVED_PARTIAL" for c in constraints),"derived_endpoint_constraints":sum(bool(c["timed_run_start_lower_utc"] or c["timed_run_start_utc"]) for c in constraints)+sum(bool(c["timed_run_end_lower_utc"] or c["timed_run_end_utc"]) for c in constraints),"inter_attempt_gaps":0}


def write_phase35_outputs(tables,chronology_status):
    write_csv(ROOT/"2024_inter_attempt_gap_diagnostics.csv",[],["prior_attempt_id","next_attempt_id","gap_lower_seconds","gap_upper_seconds","event_time_quality","value_classification","uncertainty_note"])
    metrics=phase35_metrics(tables); checks=golden_checks(tables)
    lines=["# 2024 Constrained Chronology Reconciliation","","Phase 3.5A preserves the 77-attempt corrected canonical backbone and adds only constraints supported by the supplied evidence pack, its cited source identities, and compatible Timing71 captures. The count comprises 74 official Results attempts plus three preserved `C_SECTION_ONLY` evidence rows from the preceding correctness patch. Capture, editorial anchor, and timed-run endpoint semantics remain separate.","","## Outcome","","| Metric | Result |","|---|---:|",f"| Canonical attempts | {metrics['attempts']} |",f"| Timing71 capture events | {metrics['captures']} |",f"| Uniquely linked captures | {metrics['linked_captures']} |",f"| Ambiguous or unlinked captures | {metrics['unlinked_captures']} |",f"| Approximate observed attempt constraints | {metrics['APPROXIMATE_OBSERVED']} |",f"| Bounded attempt constraints | {metrics['BOUNDED_INTERVAL']} |",f"| Ordering-only attempt constraints | {metrics['ORDERING_ONLY']} |",f"| Unknown attempt constraints | {metrics['UNKNOWN']} |",f"| Deterministic duration values | {metrics['deterministic_duration_values']} |",f"| Complete four-lap duration values | {metrics['complete_durations']} |",f"| Partial observed-duration constraints | {metrics['partial_durations']} |",f"| Bounded timed-run endpoint constraints | {metrics['derived_endpoint_constraints']} |",f"| Usable inter-attempt-gap diagnostics | {metrics['inter_attempt_gaps']} |","",f"2024 chronology reconciliation remains **{chronology_status}**. The global gate is unchanged.","","## Golden cases","",f"- VeeKay multi-anchor sequence: **{'PASS' if checks['VEEKAY_2024_MULTI_ANCHOR_GOLDEN'] else 'FAIL'}**.",f"- Rahal final-attempt consistency: **{'PASS' if checks['RAHAL_2024_FINAL_ATTEMPT_CONSISTENCY'] else 'FAIL'}**.","","VeeKay's four canonical attempts are ordered as crash, 3:26 p.m. waved-off run, approximately 3:51 p.m. 231.166 mph run, and the final 232.419 mph run. The final run has a bounded finish of 21:49:50-21:50:00 UTC and a duration-derived bounded start of 21:47:15.107-21:47:25.107 UTC. Rahal's final track entry is bounded after VeeKay and no later than the cutoff; it is not represented as release time or timed-run start.","","## Timing71 reconciliation","","Eight captures are linked: four VeeKay anchors, two Rossi anchors, Power's independently ordered initial run, and Rahal's externally documented final-attempt context. The remaining 89 captures are unlinked. Every link requires an independent anchor plus compatible car identity, attempt structure, and sequence; no link uses positional order alone.","","## Contradiction assessment","","No hard contradiction exists among the eight accepted links after capture semantics are kept separate. The following conflicts prevent broader linkage:","","- Larson's available car 17 capture sequence is incompatible with the cited sixth-initial-order fact if capture time is interpreted as on-track order, so no Larson capture is linked.","- Rahal's final recorder capture is 26 seconds after the official cutoff, while the article places track entry just before the cutoff. This confirms that capture time cannot be treated as release or track-entry time.","- VeeKay's first capture follows the reported crash minute. It is linked only as a capture associated with the uniquely identified attempt and is not converted into timed-run start.","","## Evidence and uncertainty","","The supplied DOCX is registered as a secondary compilation. Each used anchor retains the cited underlying source identity. Official INDYCAR editorial evidence ranks ahead of NBC and Motorsport.com editorial evidence; the pack itself does not supersede those sources.","","Event-time quality describes precision. Field-level provenance separately records whether a value is reconstructed from official evidence, inferred uncertainly from editorial evidence, or deterministically derived. The bounded VeeKay start inherits the bounded finish uncertainty despite exact duration arithmetic.","","No queue-entry time, release time, queue wait, lane chronology, queue length, queue position, or full historical queue state is materialized. No inter-attempt gap meets the required paired timed-run-boundary standard in this phase.","","## Sources","","- [Official INDYCAR qualifying explainer](https://www.indycar.com/-/media/Files/2024/NICS/06-500/indycar-qual-explainer-2024Indy500.pdf)","- [Official INDYCAR VeeKay Paddock Buzz](https://www.indycar.com/news/2024/05/05-18-buzz)","- [Official INDYCAR Day 1 report](https://www.indycar.com/News/2024/05/05-18-Quals-Day1)","- [NBC Sports live qualifying blog](https://www.nbcsports.com/motor-sports/news/indy-500-live-qualifying-blog-updates-day-1-problem-kyle-larson-rinus-veekay)","- [Motorsport.com Day 1 report](https://www.motorsport.com/indycar/news/indy-500-penske-heroic-veekay-rebounds-crash/10612685/)","","## Baseline comparison","","Pre-Phase-3.5A: **97 Timing71 capture events / 0 linked 2024 attempts**.",f"Post-Phase-3.5A: **97 Timing71 capture events / {metrics['linked_captures']} uniquely linked captures / {metrics['unlinked_captures']} unresolved captures**.",""]
    (ROOT/"2024_chronology_reconciliation_report.md").write_text("\n".join(lines),encoding="utf-8")
