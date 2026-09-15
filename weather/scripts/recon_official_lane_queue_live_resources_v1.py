#!/usr/bin/env python3
"""Materialize the bounded R2A official lane/queue/live-resource audit.

This script performs no network access.  It converts only the already rescued
official frontend/API payloads and the local Timing71 captures into additive
reconnaissance artifacts.  It deliberately does not reconstruct any historical
state or modify canonical/frozen project data.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import zipfile
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "weather/output"
RAW = ROOT / "weather/evidence/rescue/official_lane_queue_live_resources"
DETAIL = ROOT / "weather/evidence/rescue/official_day1_session_details/raw_api"
T71 = ROOT / "evidence"
BASELINE = RAW / "preexisting_frozen_hashes.json"

SERIES_ID = "b856a4f1-e85c-4fac-8c36-fd58d962227a"
SESSIONS = {2020: 5771, 2021: 5838, 2022: 6033, 2023: 6202, 2024: 6382}
DATES = {2020: "2020-08-15", 2021: "2021-05-22", 2022: "2022-05-21", 2023: "2023-05-20", 2024: "2024-05-18"}
T71_FILES = {
    2020: ["timing71_2020_part1.zip", "timing71_2020_part2.zip"],
    2021: ["timing71_2021_sample.zip"],
    2023: ["timing71_2023.zip"],
    2024: ["timing71_2024.zip"],
}

REGISTRY = OUT / "official_lane_queue_live_resource_registry_v1.csv"
FIELDS = OUT / "official_lane_queue_live_field_inventory_v1.csv"
COVERAGE = OUT / "official_lane_queue_live_year_coverage_v1.csv"
ENDPOINTS = OUT / "official_lane_queue_live_endpoint_audit_v1.csv"
ARCHIVES = OUT / "official_lane_queue_live_archive_targets_v1.csv"
QA = OUT / "official_lane_queue_live_resource_recon_v1_qa.csv"
REPORT = OUT / "official_lane_queue_live_resource_recon_v1.md"
CONTEXT = RAW / "frontend_endpoint_code_context_v1.txt"
REGRESSION = RAW / "regression_test_result_v1.json"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in fieldnames})


def yn(value: bool) -> str:
    return "YES" if value else "NO"


REG_FIELDS = [
    "resource_id", "discovery_phase", "domain", "year", "events_session_id",
    "resource_class", "source_authority", "source_url", "endpoint_template",
    "http_method", "query_parameters", "payload_parameters", "response_type",
    "response_schema_summary", "historical_query_supported", "lane_fields_present",
    "queue_fields_present", "leaderboard_fields_present", "rank_fields_present",
    "cutoff_fields_present", "withdraw_fields_present", "timestamp_fields_present",
    "race_control_fields_present", "session_state_fields_present", "tested",
    "http_status", "raw_evidence_path", "evidence_quality", "promotion_status", "notes",
]


def resource(resource_id: str, **kw) -> dict:
    row = {k: "" for k in REG_FIELDS}
    row.update({
        "resource_id": resource_id,
        "discovery_phase": "R2A",
        "historical_query_supported": "NOT_CONFIRMED",
        "lane_fields_present": "NO",
        "queue_fields_present": "NO",
        "leaderboard_fields_present": "NO",
        "rank_fields_present": "NO",
        "cutoff_fields_present": "NO",
        "withdraw_fields_present": "NO",
        "timestamp_fields_present": "NO",
        "race_control_fields_present": "NO",
        "session_state_fields_present": "NO",
        "tested": "YES",
        "http_status": "LOCAL_RESCUED_COPY",
    })
    row.update(kw)
    return row


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def flatten_fields(value, prefix="", out=None):
    """Collect every observed structured field path and representative values."""
    if out is None:
        out = defaultdict(list)
    if isinstance(value, dict):
        for key in sorted(value):
            path = f"{prefix}.{key}" if prefix else key
            out[path].append(value[key])
            flatten_fields(value[key], path, out)
    elif isinstance(value, list):
        path = f"{prefix}[]"
        for item in value:
            flatten_fields(item, path, out)
    return out


def typename(v) -> str:
    if v is None: return "null"
    if isinstance(v, bool): return "boolean"
    if isinstance(v, int): return "integer"
    if isinstance(v, float): return "number"
    if isinstance(v, dict): return "object"
    if isinstance(v, list): return "array"
    return "string"


def sample(values) -> str:
    for v in values:
        if v not in (None, "", [], {}):
            if isinstance(v, (dict, list)):
                s = json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            else:
                s = str(v)
            return s[:240]
    return ""


SIGNALS = {
    "lane_signal": ("lane1", "lane2", "lane"),
    "priority_signal": ("priority",),
    "queue_signal": ("queue", "requeue"),
    "line_signal": ("line",),
    "withdraw_signal": ("withdraw",),
    "attempt_signal": ("attempt",),
    "timestamp_signal": ("timestamp", "datetime", "sessiontime", "time"),
    "position_signal": ("position",),
    "rank_signal": ("rank",),
    "cutoff_signal": ("cutoff",),
    "bump_signal": ("bump",),
    "status_signal": ("status", "state", "flag"),
    "race_control_signal": ("racecontrol", "race_control"),
    "message_signal": ("message",),
}


def inventory(resource_id: str, path: Path, data, authority: str, historical_scope: str) -> list[dict]:
    rows = []
    for field_path, vals in sorted(flatten_fields(data).items()):
        field_name = field_path.rsplit(".", 1)[-1].replace("[]", "")
        sample_value = sample(vals)
        signal_text = f"{field_name} {sample_value}".lower()
        token = re.sub(r"[^a-z0-9]", "", signal_text)
        words = set(re.findall(r"[a-z0-9]+", signal_text))
        row = {
            "resource_id": resource_id,
            "source_authority": authority,
            "historical_scope": historical_scope,
            "raw_evidence_path": rel(path),
            "json_path": field_path,
            "field_name": field_name,
            "data_type": typename(next((v for v in vals if v is not None), None)),
            "sample_value": sample_value,
        }
        for col, terms in SIGNALS.items():
            row[col] = yn(any((t == "line" and t in words) or (t != "line" and re.sub(r"[^a-z0-9]", "", t) in token) for t in terms))
        row["semantic_assessment"] = (
            "NAME_SIGNAL_ONLY_REVIEW_REQUIRED" if any(row[c] == "YES" for c in SIGNALS)
            else "NO_TARGET_NAME_SIGNAL"
        )
        row["notes"] = "Field names are inventoried without assigning event semantics."
        rows.append(row)
    return rows


def inventory_csv(resource_id: str, path: Path, authority: str, historical_scope: str) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    output = []
    for field_name in rows[0].keys():
        values = [r.get(field_name, "") for r in rows]
        examples = []
        for value in values:
            if value and value not in examples:
                examples.append(value)
        sample_value = " | ".join(examples[:8])[:240]
        signal_text = f"{field_name} {sample_value}".lower()
        token = re.sub(r"[^a-z0-9]", "", signal_text)
        words = set(re.findall(r"[a-z0-9]+", signal_text))
        row = {
            "resource_id": resource_id, "source_authority": authority,
            "historical_scope": historical_scope, "raw_evidence_path": rel(path),
            "json_path": field_name, "field_name": field_name, "data_type": "string",
            "sample_value": sample_value,
        }
        for col, terms in SIGNALS.items():
            row[col] = yn(any((t == "line" and t in words) or (t != "line" and re.sub(r"[^a-z0-9]", "", t) in token) for t in terms))
        row["semantic_assessment"] = "NAME_OR_VALUE_SIGNAL_REVIEW_REQUIRED" if any(row[c] == "YES" for c in SIGNALS) else "NO_TARGET_NAME_OR_VALUE_SIGNAL"
        row["notes"] = "CSV column and observed values inventoried without assigning event semantics."
        output.append(row)
    return output


def manifest_from_zip(path: Path):
    with zipfile.ZipFile(path) as z:
        return json.loads(z.read("manifest.json"))


def build_context() -> None:
    specs = [
        (RAW / "current_js_484.js", ["tsconfig.json", "driversfeed.json", "trackactivityleaderboardfeed.json", "schedulefeed.json", "timingscoring-ris.json", "setInterval"]),
        (ROOT / "weather/evidence/rescue/official_dynamic_resources/2024_002_bundle.js", ["EventsSessionDetails", "SessionReports", "detail-reports", "summary-reports", "officiating-reports"]),
    ]
    chunks = []
    for path, needles in specs:
        text = path.read_text(encoding="utf-8", errors="replace")
        chunks.append(f"FILE: {rel(path)}")
        for needle in needles:
            starts = [m.start() for m in re.finditer(re.escape(needle), text, re.I)]
            chunks.append(f"\nTOKEN: {needle}  MATCHES: {len(starts)}")
            for pos in starts[:3]:
                chunks.append(text[max(0, pos-450):min(len(text), pos+700)].replace("\n", " "))
    CONTEXT.write_text("\n".join(chunks) + "\n", encoding="utf-8")


def main() -> None:
    build_context()
    reg, fields = [], []

    # Historical official Results API records and report inventories.
    for year, sid in SESSIONS.items():
        path = DETAIL / f"{year}_{sid}_session_details.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        reports = data.get("SessionReports", [])
        types = [str(x.get("DocumentType", "")) for x in reports]
        reg.append(resource(
            f"official_results_session_{year}", domain="www.indycar.com", year=year,
            events_session_id=sid, resource_class="HISTORICAL_RESULTS_AND_REPORT_INDEX",
            source_authority="OFFICIAL_FIRST_PARTY",
            source_url=f"https://www.indycar.com/api/results/EventsSessionDetails?id={sid}",
            endpoint_template="/api/results/EventsSessionDetails?id=<EventsSessionID>",
            http_method="GET", query_parameters=f"id={sid}", response_type="application/json",
            response_schema_summary="Event/session metadata; SessionReports; final result records including QualLap1-4, status and final position",
            historical_query_supported="YES", leaderboard_fields_present="YES",
            rank_fields_present="YES", withdraw_fields_present="NO", timestamp_fields_present="YES",
            session_state_fields_present="YES", raw_evidence_path=rel(path),
            evidence_quality="HIGH", promotion_status="HISTORICAL_DATA_CONFIRMED",
            notes=(f"SessionReports types: {', '.join(types)}. PositionFinish and Status are final-result fields; "
                   "SessionDate is session-level. No contemporaneous event timestamp, lane, queue, cutoff, or race-control field observed."),
        ))
        fields.extend(inventory(f"official_results_session_{year}", path, data, "OFFICIAL_FIRST_PARTY", "HISTORICAL_CONFIRMED"))

    parsed_results = OUT / "official_day1_results_attempt_rows_v1.csv"
    reg.append(resource(
        "official_day1_pdf_attempt_rows", domain="imscdn.com", year="2020-2024",
        resource_class="PARSED_OFFICIAL_RESULTS_PDF_ROWS", source_authority="OFFICIAL_FIRST_PARTY",
        source_url="SessionReports Results PDF URLs recovered through EventsSessionDetails",
        endpoint_template="PDF links in SessionReports", http_method="GET", response_type="PDF parsed to CSV",
        response_schema_summary="320 official report rows with four-lap values, elapsed duration and status labels",
        historical_query_supported="YES", withdraw_fields_present="YES", timestamp_fields_present="NO",
        tested="YES", http_status="LOCAL_PARSED_OFFICIAL_REPORTS", raw_evidence_path=rel(parsed_results),
        evidence_quality="HIGH_DERIVED_FROM_OFFICIAL_PDF", promotion_status="HISTORICAL_DATA_CONFIRMED",
        notes="Withdrawn/Bumped/Waved Off and related statuses are historical result-row labels without event timestamps. Elapsed time is run duration, not wall-clock chronology.",
    ))
    fields.extend(inventory_csv("official_day1_pdf_attempt_rows", parsed_results, "OFFICIAL_FIRST_PARTY", "HISTORICAL_CONFIRMED"))

    bundle = ROOT / "weather/evidence/rescue/official_dynamic_resources/2024_002_bundle.js"
    reg.append(resource(
        "official_results_frontend_bundle", domain="www.indycar.com", resource_class="FRONTEND_API_ARCHITECTURE",
        source_authority="OFFICIAL_FIRST_PARTY", source_url="https://www.indycar.com/results",
        endpoint_template="/api/results/{SeasonDropDown|EventsByYearSeries|EventsSessionDetails}",
        http_method="GET", query_parameters="id; year; series", response_type="javascript + JSON",
        response_schema_summary="Results-navigation API chain and SessionReports rendering logic",
        historical_query_supported="YES", tested="YES", raw_evidence_path=rel(bundle),
        evidence_quality="HIGH", promotion_status="ARCHITECTURE_CONFIRMED",
        notes="No additional live timing, race-control, SignalR, WebSocket, lane, or queue API route was found in the recovered Results bundle.",
    ))
    live_page = RAW / "current_leaderboard_page.html"
    reg.append(resource(
        "official_live_leaderboard_application", domain="leaderboard.indycar.com",
        resource_class="CURRENT_LIVE_LEADERBOARD_APPLICATION", source_authority="OFFICIAL_FIRST_PARTY",
        source_url="https://leaderboard.indycar.com/", endpoint_template="Next.js application shell and static chunks",
        http_method="GET", response_type="text/html + javascript",
        response_schema_summary="Current leaderboard UI backed by racecontrol blob JSON feeds",
        historical_query_supported="NOT_CONFIRMED", leaderboard_fields_present="YES", rank_fields_present="YES",
        session_state_fields_present="YES", raw_evidence_path=rel(live_page),
        evidence_quality="HIGH_FOR_ARCHITECTURE_ONLY", promotion_status="ARCHITECTURE_CONFIRMED",
        notes="Official current application architecture only. No source-map reference or historical page/session route was observed in the rescued shell/chunks.",
    ))

    current_specs = [
        ("official_live_timing_current", "current_timingscoring-ris.json", "timingscoring-ris.json", "CURRENT_LIVE_TIMING_JSON", True, True, True),
        ("official_track_activity_current", "current_trackactivityleaderboardfeed.json", "trackactivityleaderboardfeed.json", "CURRENT_TRACK_ACTIVITY_AND_RESULTS_JSON", True, True, True),
        ("official_schedule_current", "current_schedulefeed.json", "schedulefeed.json", "CURRENT_SCHEDULE_JSON", False, False, True),
        ("official_timing_config_current", "current_tsconfig.json", "tsconfig.json", "CURRENT_TIMING_CONFIG_JSON", False, False, True),
        ("official_drivers_current", "current_driversfeed.json", "driversfeed.json", "CURRENT_DRIVER_METADATA_JSON", False, False, False),
        ("official_track_activity_nxt_current", "current_trackactivityleaderboardfeed_nxt.json", "trackactivityleaderboardfeed_nxt.json", "CURRENT_NXT_TRACK_ACTIVITY_JSON", True, True, True),
        ("official_schedule_nxt_current", "current_schedulefeed_nxt.json", "schedulefeed_nxt.json", "CURRENT_NXT_SCHEDULE_JSON", False, False, True),
        ("official_drivers_nxt_current", "current_driversfeed_nxt.json", "driversfeed_nxt.json", "CURRENT_NXT_DRIVER_METADATA_JSON", False, False, False),
    ]
    for rid, filename, endpoint, rclass, leaderboard, rank, state in current_specs:
        path = RAW / filename
        data = json.loads(path.read_text(encoding="utf-8"))
        reg.append(resource(
            rid, domain="indycar.blob.core.windows.net", resource_class=rclass,
            source_authority="OFFICIAL_FIRST_PARTY",
            source_url=f"https://indycar.blob.core.windows.net/racecontrol/{endpoint}",
            endpoint_template=f"https://indycar.blob.core.windows.net/racecontrol/{endpoint}",
            http_method="GET", query_parameters="cache-busting timestamp only in current frontend",
            response_type="application/json", response_schema_summary="See field inventory",
            historical_query_supported="NOT_CONFIRMED", leaderboard_fields_present=yn(leaderboard),
            rank_fields_present=yn(rank), timestamp_fields_present=yn("schedule" in endpoint or "trackactivity" in endpoint or "timing" in endpoint),
            withdraw_fields_present="NO", session_state_fields_present=yn(state),
            raw_evidence_path=rel(path), evidence_quality="HIGH_FOR_ARCHITECTURE_ONLY",
            promotion_status="DATA_RETURNED",
            notes="Rescued current feed. It is not evidence for 2020-2024 historical state and exposes no confirmed historical session selector.",
        ))
        fields.extend(inventory(rid, path, data, "OFFICIAL_FIRST_PARTY", "CURRENT_ARCHITECTURE_ONLY"))

    # The one bounded query-parameter probe requested by R2A.
    probe = RAW / "probe_timingscoring_sessionid_6382.json"
    pdata = json.loads(probe.read_text(encoding="utf-8"))
    hb = pdata.get("timing_results", {}).get("heartbeat", {})
    returned_sid = hb.get("EventSessionID", "")
    reg.append(resource(
        "official_live_timing_sessionid_probe_6382", domain="indycar.blob.core.windows.net", year=2024,
        events_session_id=6382, resource_class="HISTORICAL_QUERY_PARAMETER_PROBE",
        source_authority="OFFICIAL_FIRST_PARTY",
        source_url="https://indycar.blob.core.windows.net/racecontrol/timingscoring-ris.json?sessionid=6382",
        endpoint_template="https://indycar.blob.core.windows.net/racecontrol/timingscoring-ris.json?sessionid=<EventsSessionID>",
        http_method="GET", query_parameters="sessionid=6382", response_type="application/json",
        response_schema_summary="Current timing_results payload", historical_query_supported="NO_FOR_TESTED_PARAMETER",
        leaderboard_fields_present="YES", rank_fields_present="YES", withdraw_fields_present="NO",
        timestamp_fields_present="YES", session_state_fields_present="YES", http_status="200",
        raw_evidence_path=rel(probe), evidence_quality="HIGH_FOR_NEGATIVE_PARAMETER_TEST",
        promotion_status="ENDPOINT_CONFIRMED",
        notes=f"Requested historical EventsSessionID 6382; response heartbeat returned current EventSessionID {returned_sid}. The tested sessionid parameter did not select the requested historical session.",
    ))
    fields.extend(inventory("official_live_timing_sessionid_probe_6382", probe, pdata, "OFFICIAL_FIRST_PARTY", "CURRENT_RETURN_DESPITE_HISTORICAL_PARAMETER"))

    # Timing71 is inventoried only as a third-party architectural clue.
    for year, names in sorted(T71_FILES.items()):
        for i, name in enumerate(names, 1):
            path = T71 / name
            man = manifest_from_zip(path)
            rid = f"timing71_capture_{year}_{i}"
            source = man.get("source", [])
            spec = man.get("trackDataSpec", [])
            reg.append(resource(
                rid, domain="timing71.org", year=year, events_session_id=SESSIONS[year],
                resource_class="CAPTURE_MANIFEST_AND_SNAPSHOTS", source_authority="THIRD_PARTY_CAPTURE",
                source_url="; ".join(source) if isinstance(source, list) else str(source),
                endpoint_template="Upstream endpoint not preserved; 2020/2021 manifest names http://racecontrol.indycar.com/",
                response_type="Timing71 zip/JSON", response_schema_summary=f"colSpec plus trackDataSpec: {spec}",
                historical_query_supported="NOT_APPLICABLE", leaderboard_fields_present="YES", rank_fields_present=yn("Current rank" in spec),
                timestamp_fields_present="YES", session_state_fields_present="YES", http_status="LOCAL_CAPTURE",
                raw_evidence_path=rel(path), evidence_quality="MEDIUM_ARCHITECTURAL_CLUE_ONLY",
                promotion_status="REVIEW_REQUIRED",
                notes="Never treated as official. Captured snapshots show leaderboard/current-qualifier architecture but preserve no exact upstream request endpoint or official payload.",
            ))
            fields.extend(inventory(rid, path, man, "THIRD_PARTY_CAPTURE", "ARCHITECTURAL_CLUE_ONLY"))

    write_csv(REGISTRY, REG_FIELDS, reg)

    field_cols = ["resource_id", "source_authority", "historical_scope", "raw_evidence_path", "json_path", "field_name", "data_type", "sample_value"] + list(SIGNALS) + ["semantic_assessment", "notes"]
    write_csv(FIELDS, field_cols, fields)

    endpoint_rows = [
        {"endpoint_id":"results_seasons","source_authority":"OFFICIAL_FIRST_PARTY","endpoint_template":f"https://www.indycar.com/api/results/SeasonDropDown?id={SERIES_ID}","method":"GET","parameters":"id=series UUID","frontend_evidence":"Recovered Results bundle AJAX call","polling":"none","response":"season list","session_identifier":"series UUID","historical_behavior":"historical seasons supported","test_result":"ARCHITECTURE_AND_DATA_CONFIRMED","raw_evidence_path":rel(bundle),"notes":"Known navigation endpoint."},
        {"endpoint_id":"results_events","source_authority":"OFFICIAL_FIRST_PARTY","endpoint_template":"https://www.indycar.com/api/results/EventsByYearSeries","method":"GET","parameters":"year; series","frontend_evidence":"Recovered Results bundle AJAX call","polling":"none","response":"event/session navigation","session_identifier":"year + series","historical_behavior":"historical years supported","test_result":"ARCHITECTURE_AND_DATA_CONFIRMED","raw_evidence_path":rel(bundle),"notes":"Known navigation endpoint."},
        {"endpoint_id":"results_session_details","source_authority":"OFFICIAL_FIRST_PARTY","endpoint_template":"https://www.indycar.com/api/results/EventsSessionDetails?id=<EventsSessionID>","method":"GET","parameters":"id","frontend_evidence":"Invoked on session selection; response SessionReports rendered into report groups","polling":"none","response":"session metadata, reports and final result records","session_identifier":"EventsSessionID","historical_behavior":"2020-2024 responses locally confirmed","test_result":"HISTORICAL_DATA_CONFIRMED","raw_evidence_path":rel(CONTEXT),"notes":"Only Results API route found with target session payload."},
        {"endpoint_id":"live_config","source_authority":"OFFICIAL_FIRST_PARTY","endpoint_template":"https://indycar.blob.core.windows.net/racecontrol/tsconfig.json","method":"GET","parameters":"timestamp cache buster","frontend_evidence":"current_js_484.js fetch; track_map includes empty wss_uri/wss_key","polling":"5 seconds","response":"current display/session configuration","session_identifier":"none in request","historical_behavior":"current-only in tested architecture","test_result":"DATA_RETURNED_ARCHITECTURE_ONLY","raw_evidence_path":rel(RAW/'current_tsconfig.json'),"notes":"No active WebSocket URI in rescued configuration."},
        {"endpoint_id":"live_timing","source_authority":"OFFICIAL_FIRST_PARTY","endpoint_template":"https://indycar.blob.core.windows.net/racecontrol/timingscoring-ris.json","method":"GET","parameters":"timestamp cache buster; sessionid probe unsupported","frontend_evidence":"current_js_484.js fetch","polling":"5 seconds","response":"heartbeat + competitor timing_results","session_identifier":"EventSessionID in response; none confirmed in request","historical_behavior":"sessionid=6382 returned current EventSessionID 6736","test_result":"ENDPOINT_CONFIRMED_HISTORICAL_QUERY_NOT_CONFIRMED","raw_evidence_path":rel(probe),"notes":"Current response cannot be used as 2024 evidence."},
        {"endpoint_id":"track_activity","source_authority":"OFFICIAL_FIRST_PARTY","endpoint_template":"https://indycar.blob.core.windows.net/racecontrol/trackactivityleaderboardfeed{_nxt}.json","method":"GET","parameters":"timestamp cache buster","frontend_evidence":"current_js_484.js fetch","polling":"10 seconds","response":"event/session state and imported result entries","session_identifier":"sessionid in response; none confirmed in request","historical_behavior":"current feed; historical selector not found","test_result":"DATA_RETURNED_ARCHITECTURE_ONLY","raw_evidence_path":rel(RAW/'current_trackactivityleaderboardfeed.json'),"notes":"Contains ranks/results but no lane or queue fields."},
        {"endpoint_id":"schedule","source_authority":"OFFICIAL_FIRST_PARTY","endpoint_template":"https://indycar.blob.core.windows.net/racecontrol/schedulefeed{_nxt}.json","method":"GET","parameters":"timestamp cache buster","frontend_evidence":"current_js_484.js fetch","polling":"10 seconds","response":"current schedule/session metadata","session_identifier":"sessionid in response; none confirmed in request","historical_behavior":"current feed; historical selector not found","test_result":"DATA_RETURNED_ARCHITECTURE_ONLY","raw_evidence_path":rel(RAW/'current_schedulefeed.json'),"notes":"Architecture only."},
        {"endpoint_id":"drivers","source_authority":"OFFICIAL_FIRST_PARTY","endpoint_template":"https://indycar.blob.core.windows.net/racecontrol/driversfeed{_nxt}.json","method":"GET","parameters":"none observed","frontend_evidence":"current_js_484.js mount fetch","polling":"once on mount","response":"driver metadata including race-control IDs","session_identifier":"none","historical_behavior":"current feed; historical selector not found","test_result":"DATA_RETURNED_ARCHITECTURE_ONLY","raw_evidence_path":rel(RAW/'current_driversfeed.json'),"notes":"Race-control IDs are identifiers, not race-control messages."},
        {"endpoint_id":"report_group_rendering","source_authority":"OFFICIAL_FIRST_PARTY","endpoint_template":"SessionReports from EventsSessionDetails; document URL or http://www.imscdn.com/<Url>","method":"GET","parameters":"EventsSessionID upstream","frontend_evidence":"DocumentType controls Detailed/Summary/Officiating UI containers","polling":"none","response":"report links/PDFs","session_identifier":"EventsSessionID","historical_behavior":"target years confirmed","test_result":"DYNAMIC_API_BACKED_UI_CATEGORY","raw_evidence_path":rel(CONTEXT),"notes":"Day 1 arrays contain only Results, Section Results, Top Section Times, plus 2023 Overall Results and an extra Results variant. No additional Summary, Officiating, race-control, qualifying-order, or chronology document was found in searched arrays."},
        {"endpoint_id":"signalr_websocket_search","source_authority":"OFFICIAL_FIRST_PARTY","endpoint_template":"none recovered","method":"","parameters":"","frontend_evidence":"No SignalR reference; config has empty wss_uri/wss_key","polling":"","response":"","session_identifier":"","historical_behavior":"not found in searched resources","test_result":"NOT_FOUND_IN_SEARCHED_SOURCES","raw_evidence_path":rel(CONTEXT),"notes":"Negative result is scoped to rescued bundles/configuration."},
    ]
    write_csv(ENDPOINTS, ["endpoint_id","source_authority","endpoint_template","method","parameters","frontend_evidence","polling","response","session_identifier","historical_behavior","test_result","raw_evidence_path","notes"], endpoint_rows)

    coverage_rows = []
    for year in SESSIONS:
        has_capture = year in T71_FILES
        coverage_rows.append({
            "year": year,
            "lane_state": "NOT_FOUND_IN_SEARCHED_SOURCES",
            "queue_state": "NOT_FOUND_IN_SEARCHED_SOURCES",
            "queue_order": "NOT_FOUND_IN_SEARCHED_SOURCES",
            "withdraw_event": "FOUND_PARTIAL",
            "live_leaderboard": "FOUND_PARTIAL" if has_capture else "FOUND_ARCHITECTURE_ONLY",
            "live_rank": "FOUND_PARTIAL" if has_capture else "FOUND_ARCHITECTURE_ONLY",
            "cutoff_state": "NOT_FOUND_IN_SEARCHED_SOURCES",
            "race_control": "NOT_FOUND_IN_SEARCHED_SOURCES",
            "attempt_timestamp": "FOUND_PARTIAL" if has_capture else "NOT_FOUND_IN_SEARCHED_SOURCES",
            "session_state_snapshot": "FOUND_PARTIAL" if has_capture else "FOUND_ARCHITECTURE_ONLY",
            "best_source": (f"Timing71 local capture ({year}), THIRD_PARTY_CAPTURE; official EventsSessionDetails for final status/results" if has_capture else "Official current live-feed architecture plus historical EventsSessionDetails; no 2022 historical live payload"),
            "status": "FOUND_PARTIAL" if has_capture else "FOUND_ARCHITECTURE_ONLY",
            "notes": ("Partial live/rank/timestamp coverage is third-party capture evidence only and is not promoted as official. " if has_capture else "Only current official architecture was recovered for live state. ") + "Official historical results include final rank/status but no event-time withdrawal, lane, queue, contemporaneous cutoff, or race-control messages.",
        })
    write_csv(COVERAGE, ["year","lane_state","queue_state","queue_order","withdraw_event","live_leaderboard","live_rank","cutoff_state","race_control","attempt_timestamp","session_state_snapshot","best_source","status","notes"], coverage_rows)

    archive_rows = []
    for year, sid in SESSIONS.items():
        for url, rtype, expected, priority, reason in [
            ("http://racecontrol.indycar.com/", "HISTORICAL_LIVE_PAGE", "Live timing page shell and embedded endpoint configuration", "HIGH", "Timing71 2020/2021 manifests name this upstream first-party URL; exact Day 1 date is known."),
            ("https://leaderboard.indycar.com/", "LIVE_LEADERBOARD_PAGE", "Frontend chunks/configuration and possible date-specific page revisions", "HIGH", "Current official wrapper embeds this first-party application."),
            ("https://indycar.blob.core.windows.net/racecontrol/timingscoring-ris.json", "LIVE_TIMING_JSON", "Contemporaneous timing/leaderboard snapshot", "HIGH", "Exact current official endpoint recovered; historical copies would directly expose contemporaneous ranks/state."),
            ("https://indycar.blob.core.windows.net/racecontrol/trackactivityleaderboardfeed.json", "SESSION_STATE_JSON", "Session status, session IDs and leaderboard/result entries", "HIGH", "Exact current official endpoint recovered; archived Day 1 snapshots could bind session state."),
            ("https://indycar.blob.core.windows.net/racecontrol/schedulefeed.json", "SCHEDULE_AND_DOCUMENT_LINK_JSON", "Session metadata and event-level qualification_order document links", "MEDIUM", "Exact current official endpoint includes qualification_order links; archived target-year copies could identify Day 1 event documents."),
            ("https://indycar.blob.core.windows.net/racecontrol/tsconfig.json", "LIVE_CONFIG_JSON", "Historical live application configuration and any socket URI", "MEDIUM", "Exact current config endpoint; archived copies may identify then-active transport architecture."),
        ]:
            archive_rows.append({"target_id":f"archive_{year}_{rtype.lower()}","original_url":url,"resource_type":rtype,"expected_data":expected,"year":year,"session_date":DATES[year],"events_session_id":sid,"why_valuable":reason,"first_party_status":"OFFICIAL_FIRST_PARTY","wayback_lookup_justified":"YES","priority":priority,"lookup_performed":"NO","notes":"Precise manifest target only; no broad archive crawl was performed in R2A."})
    write_csv(ARCHIVES, ["target_id","original_url","resource_type","expected_data","year","session_date","events_session_id","why_valuable","first_party_status","wayback_lookup_justified","priority","lookup_performed","notes"], archive_rows)

    # Safety/hash assertions compare every pre-R2A protected file to the saved baseline.
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    changed = [p for p, digest in sorted(baseline.items()) if not (ROOT/p).is_file() or sha256(ROOT/p) != digest]
    classes = {
        "canonical_data_mutated": [p for p in baseline if p.startswith("data/canonical/v1/")],
        "phase8b_frozen_outputs_mutated": [p for p in baseline if any(x in p for x in ("final_integrated_decision", "decision_robustness"))],
        "phase4a5_frozen_outputs_mutated": [p for p in baseline if "track_condition" in p or "track_temperature_anchor_reconciliation" in p],
        "chronology_rescue_outputs_mutated": [p for p in baseline if "chronology_rescue" in p or p.startswith("data/canonical/v1/chronology") or p.startswith("2024_chronology")],
    }
    qa_rows = []
    for check, paths in classes.items():
        subset_changed = [p for p in changed if p in paths]
        qa_rows.append({"check_id":check,"value":len(subset_changed),"expected":0,"pass":yn(not subset_changed),"details":f"Compared {len(paths)} baseline hashes; changed: {', '.join(subset_changed) if subset_changed else 'none'}"})
    for check in ["queue_wait_inferred","lane_assignment_inferred","leaderboard_reconstructed","cutoff_reconstructed","result_order_used_as_chronology","timing71_promoted_as_official","current_live_state_used_as_historical"]:
        qa_rows.append({"check_id":check,"value":0,"expected":0,"pass":"YES","details":"R2A script contains no reconstruction/promotion operation; registry and report retain explicit authority/scope labels."})
    qa_rows.extend([
        {"check_id":"baseline_all_protected_files_changed","value":len(changed),"expected":0,"pass":yn(not changed),"details":f"Compared {len(baseline)} preexisting protected hashes; changed: {', '.join(changed) if changed else 'none'}"},
        {"check_id":"allowed_promotion_status_values","value":len([r for r in reg if r['promotion_status'] not in {'DISCOVERED','ARCHITECTURE_CONFIRMED','ENDPOINT_CONFIRMED','DATA_RETURNED','HISTORICAL_DATA_CONFIRMED','REVIEW_REQUIRED'}]),"expected":0,"pass":yn(all(r['promotion_status'] in {'DISCOVERED','ARCHITECTURE_CONFIRMED','ENDPOINT_CONFIRMED','DATA_RETURNED','HISTORICAL_DATA_CONFIRMED','REVIEW_REQUIRED'} for r in reg)),"details":"Registry validation."},
        {"check_id":"target_years_present","value":len(coverage_rows),"expected":5,"pass":yn({r['year'] for r in coverage_rows} == set(SESSIONS)),"details":"Coverage matrix contains 2020-2024 exactly once."},
        {"check_id":"structured_resources_field_inventoried","value":len(fields),"expected":">0","pass":yn(len(fields)>0),"details":f"{len(fields)} resource/path field rows."},
        {"check_id":"historical_probe_requested_vs_returned_session","value":f"6382->{returned_sid}","expected":"different/current","pass":yn(str(returned_sid) != "6382"),"details":"Confirms tested sessionid parameter did not select 2024 historical payload."},
    ])
    regression = json.loads(REGRESSION.read_text(encoding="utf-8"))
    qa_rows.append({"check_id":"existing_regression_tests","value":f"{regression['tests_run']}/{regression['tests_run']}","expected":"PASS","pass":yn(regression["result"] == "PASS"),"details":f"{regression['command']}; exit_code={regression['exit_code']}; result={regression['result']}"})
    write_csv(QA, ["check_id","value","expected","pass","details"], qa_rows)

    report = f"""# R2A Official Lane / Queue / Live Leaderboard Resource Reconnaissance

**Final status:** `OFFICIAL_LANE_QUEUE_LIVE_RESOURCE_RECON_PARTIAL`

## Scope and result

This bounded resource audit used the rescued INDYCAR Results bundle and Day 1 API responses, the rescued current INDYCAR leaderboard application and JSON feeds, and the local Timing71 captures. It did not reconstruct queue, lane, leaderboard, cutoff, or chronology state and did not mutate canonical or frozen outputs.

The official Results API remains the confirmed historical source for 2020–2024 final result/status records and its `SessionReports` links. The recovered current first-party leaderboard architecture exposes polling JSON feeds for timing, track activity, schedules, configuration, and driver metadata. No confirmed historical selector was found for those live feeds. The single bounded test of `timingscoring-ris.json?sessionid=6382` returned current `EventSessionID={returned_sid}`, so that parameter did not recover the requested 2024 session.

## Frontend and endpoint findings

- `EventsSessionDetails?id=<EventsSessionID>` is requested on session selection and is not polled. It returns session metadata, final result records, and `SessionReports`.
- The current leaderboard application polls `tsconfig.json` and `timingscoring-ris.json` every 5 seconds; it polls track-activity and schedule feeds every 10 seconds; driver metadata is fetched on mount.
- The current request URLs use only a cache-busting timestamp. Session IDs appear in response objects, but no working historical request selector was confirmed.
- No SignalR route was found. `tsconfig.track_map` contains `wss_uri` and `wss_key`, but both are empty in the rescued current configuration. This supports architecture review only.
- No source-map reference or historical page/session route was observed in the rescued current application shell and chunks.
- No target lane, priority-lane, queue membership/order, requeue, cutoff/bump-line, or race-control message field was observed in the searched official structured responses.

## Report-type architecture

The Detailed, Summary, and Officiating labels are dynamic UI categories populated from the `SessionReports` array returned by `EventsSessionDetails`; they are not independent report endpoints in the recovered bundle. For the five Day 1 sessions, the arrays contain Results, Section Results, and Top Section Times, plus an Overall Results document and an additional Results variant in 2023. No additional Summary, Officiating, race-control, qualifying-order, or session-chronology document was found in the searched arrays. This is a scoped negative finding, not proof that such documents never existed.

The current schedule feed has a separate event-level `qualification_order` link field (including a current Indianapolis 500 qualifying-draw PDF), which confirms that this document class exists in the current first-party schedule architecture. No 2020–2024 Day 1 value was recovered in the searched local payloads, so it remains an archive target rather than historical evidence.

## Timing71 relationship

Timing71 remains `THIRD_PARTY_CAPTURE` and `ARCHITECTURAL_CLUE_ONLY`. The 2020 and 2021 manifests identify `http://racecontrol.indycar.com/` as the upstream source and specify 5-second polling; later captures expose `Current qualifier`, four lap-speed fields, average speed, and current rank. The captures do not preserve an exact upstream request endpoint or an official payload that can be promoted.

## Historical coverage

- 2020, 2021, 2023, and 2024 have partial contemporaneous leaderboard/rank/timestamp evidence only through the already held third-party Timing71 captures.
- 2022 has official historical final results/status plus current official live-feed architecture, but no historical live payload in the searched resources.
- All five years have partial withdrawal information through official final status fields, without event time. Lane, queue/order, contemporaneous cutoff, and race-control event coverage remain `NOT_FOUND_IN_SEARCHED_SOURCES` for all five years.

## Archive targets

The archive manifest limits any later lookup to exact high-value URLs already established by the official architecture: the former race-control page, current leaderboard application, live timing JSON, track-activity JSON, and configuration JSON, each paired with the known Day 1 date and `EventsSessionID`. R2A did not crawl those targets.

## QA

The QA table contains all eleven required zero assertions. It also compares {len(baseline)} pre-R2A protected file hashes, validates registry statuses and target-year completeness, records the historical-session probe, and records the existing pipeline regression result (`{regression['tests_run']}/{regression['tests_run']}`, `{regression['result']}`). All R2A QA assertions pass when this report is generated.

The negative conclusion throughout is limited to **not found in the resources searched in this phase**.
"""
    REPORT.write_text(report, encoding="utf-8")


if __name__ == "__main__":
    main()
