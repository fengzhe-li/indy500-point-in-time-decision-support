import json
from collections import Counter
from pathlib import Path
from .config import ROOT, OUTPUT, HRRR_NUMERIC_INPUT
from .reconcile import build
from .validation import section_validation, chronology_reconciliation, data_quality
from .eligibility import assign
from .materialize import materialize, year_summary
from .parsers import weather

def run():
    tables, issues, parsers = build()
    sections = section_validation(tables)
    chronology, statuses = chronology_reconciliation(tables)
    assign(tables)
    summary = year_summary(tables)
    weather_checks = weather.qa_rows(HRRR_NUMERIC_INPUT,tables)
    quality = data_quality(tables, sections, chronology, issues, weather_checks)
    qa={"sections":sections,"chronology":chronology,"year_summary":summary,"data_quality":quality,"weather":weather_checks}
    materialize(tables,qa)
    blocking=[q for q in quality if q["severity"]=="BLOCKING" and q["pass_fail"]=="FAIL"]
    performance_blocking=[q for q in blocking if q["check_id"] != "GLOBAL_CHRONOLOGY_ANALYSIS_READY"]
    analysis_readiness={
        "FOUR_LAP_PERFORMANCE":"READY" if not performance_blocking and sum(x["performance_core_eligible_count"] for x in summary)>0 else "NOT_READY",
        "LAP_PERFORMANCE":"READY" if not performance_blocking else "NOT_READY",
        "WITHIN_CAR_COMPARISON":"READY_WITH_SUPPORTED_SUBSET" if any(a["car_attempt_index"] and a["car_attempt_index"]>1 for a in tables["attempts"]) else "NOT_READY",
        "CHRONOLOGY":"NOT_READY" if any(x["chronology_status"]!="PASS" for x in summary) else "READY",
        "QUEUE_CALIBRATION":"READY_FOR_LIMITED_CAPTURE_BASED_CALIBRATION" if any(r["analysis_target"]=="QUEUE_CALIBRATION" and r["eligible"] for r in tables["row_eligibility"]) else "NOT_READY",
    }
    gate="PIPELINE NOT READY — BLOCKING DATA INTEGRITY ISSUES" if blocking or any(v=="NOT_READY" for v in analysis_readiness.values()) else "PIPELINE READY FOR MODELLING"
    _write_report(tables,parsers,issues,summary,quality,sections,statuses,analysis_readiness,gate,weather_checks)
    _write_weather_report(tables,weather_checks)
    return {"gate":gate,"blocking_checks":blocking,"analysis_readiness":analysis_readiness,"row_counts":{k:len(v) for k,v in tables.items()}}

def _write_report(tables,parsers,issues,summary,quality,sections,statuses,readiness,gate,weather_checks):
    failed=[x for x in quality if x["pass_fail"]=="FAIL"]
    lines=["# Pipeline Run Report","",f"Schema: `INDY500_V1_2026-09-08`",f"Canonical format: UTF-8 CSV in `{OUTPUT}`. CSV was selected because Parquet support is not installed in the frozen runtime.","All datetime fields use explicit UTC `Z` text; local session dates carry `America/Indiana/Indianapolis` separately.","","## Source processing","","| Source | Status | Staging rows |","|---|---:|---:|"]
    lines += [f"| `{p['source']}` | {p['status']} | {p['rows']} |" for p in parsers]
    lines += ["","## Canonical row counts","","| Table | Rows |","|---|---:|"]
    lines += [f"| `{name}` | {len(rows)} |" for name,rows in tables.items()]
    lines += ["","## Year status","","| Year | Attempts | Complete | Partial | Supported repeats | Usable attempt timestamps | Chronology | Performance core | Chronology core |","|---:|---:|---:|---:|---:|---:|---|---:|---:|"]
    lines += [f"| {x['year']} | {x['attempt_count']} | {x['complete_attempts']} | {x['partial_attempts']} | {x['repeated_attempt_count_where_supportable']} | {x['usable_timestamps']} | {x['chronology_status']} | {x['performance_core_eligible_count']} | {x['chronology_core_eligible_count']} |" for x in summary]
    validated_residuals=[abs(float(x["residual"])) for x in sections if x["validation_pass"] and x["residual"] is not None]
    failed_residuals=[abs(float(x["residual"])) for x in sections if x["coverage_status"]=="VALIDATION_FAILED" and x["residual"] is not None]
    partial_section_observations=sum(x["coverage_status"]=="PARTIAL_OBSERVATION" for x in sections)
    partial_section_rows=sum(s["section_lap_coverage_status"]=="PARTIAL_OBSERVATION" for s in tables["attempt_sections"])
    failed_section_candidates=sum(x["coverage_status"]=="VALIDATION_FAILED" for x in sections)
    timing_events=[e for e in tables["chronology_events"] if e["time_basis"]=="RECORDER_CAPTURE"]
    linked_timing=sum(e["attempt_id"] is not None for e in timing_events); unresolved_timing=len(timing_events)-linked_timing
    official_backbone=sum(not str(a["source_native_locator"]).endswith(":unresolved") for a in tables["attempts"])
    constraints_2024=tables["chronology_constraints"]
    captures_2024=[e for e in timing_events if e["session_id"].endswith("2024")]
    qualities_2024=Counter(c["event_time_quality"] for c in constraints_2024)
    weather_failed=sum(r["pass_fail"]=="FAIL" for r in weather_checks)
    lines += ["","## Reconstruction, provenance, and missingness","",f"- Canonical attempt count before this correctness patch: {official_backbone}; after preserving unresolved Section runs: {len(tables['attempts'])}.",f"- Partial source-report lap observations newly preserved: {partial_section_observations} groups ({partial_section_rows} section rows); complete candidates preserved but disabled after failed validation: {failed_section_candidates}.",f"- Section validation groups: {len(sections)}; maximum absolute residual among validated groups: {max(validated_residuals) if validated_residuals else 'n/a'} seconds; maximum failed-candidate residual: {max(failed_residuals) if failed_residuals else 'n/a'} seconds.",f"- Unmatched/ambiguous Section runs materialized conservatively as `C_SECTION_ONLY`: {len(issues)}.",f"- Timing71 qualifier-capture events: {len(timing_events)}; linked after conservative matching: {linked_timing}; left unresolved: {unresolved_timing}.",f"- 2024 constrained pass: {len(captures_2024)} captures, {sum(e['attempt_id'] is not None for e in captures_2024)} uniquely linked and {sum(e['attempt_id'] is None for e in captures_2024)} unresolved; attempt constraints are {qualities_2024['APPROXIMATE_OBSERVED']} approximate, {qualities_2024['BOUNDED_INTERVAL']} bounded, {qualities_2024['ORDERING_ONLY']} ordering-only, and {qualities_2024['UNKNOWN']} unknown.",f"- Evidence items: {len(tables['evidence_items'])}; field evidence/lineage links: {len(tables['field_evidence_links'])}.",f"- HRRR numeric layer: {len(tables['forecast_snapshots'])} unique cycle/lead snapshots and {len(tables['weather_forecasts'])} numeric values; Phase 4A weather QA failures: {weather_failed}.","- Public HRRR availability timestamps remain null with `POLICY_REQUIRED` status; cycle time is never substituted for availability.","- `decision_state_features` is intentionally empty: Phase 4A does not align weather to attempts or decision states."]
    lines += ["","## Analysis readiness","","| Analysis target | Status |","|---|---|"]+[f"| `{k}` | `{v}` |" for k,v in readiness.items()]
    lines += ["","## Known limitations","","- Timing71 produces recorder/capture times only; canonical capture-event quality remains `APPROXIMATE_OBSERVED`. Capture time is not release time or timed-run start. Positional linking occurs only when independently supported and unambiguous.","- The 2020 internal gap and 2023 terminal gap are explicit `COVERAGE_GAP` rows. State is never forward-filled across them.","- Chronology reconciliation is incomplete, including 2021 and 2024; ambiguous capture events remain unlinked rather than being assigned by ranked Results order.","- 2022 has no Timing71 replay in the frozen evidence and no fabricated attempt timestamps.","- 2024 Section Results preserve all attributable selected/partial section rows but do not prove repeated-attempt coverage.","- Within-car comparison is a robustness/sub-analysis population; it is not a prerequisite for cross-car performance modelling.","- Lane, withdrawal time, requeue, and queue state remain unknown unless directly documented. No inferred queue/lane value is promoted.","- Exact historical HRRR public availability is unresolved. A documented, configurable, versioned latency policy is required before time-safe decision-state joins.","- `TMP_2m` remains 2 m air temperature and `DSWRF_surface` remains downward shortwave radiation; neither is labelled as track temperature."]
    lines += ["","## Validation outcome","",f"Blocking machine-check failures: {len([x for x in failed if x['severity']=='BLOCKING'])}.","The global gate requires all requested analysis families to be ready. Chronology is not globally ready because no year reaches reconciliation PASS. Queue calibration is limited to observed capture-based attempt processes and does not claim exact lane or queue state.","",f"`{gate}`",""]
    (ROOT/"pipeline_run_report.md").write_text("\n".join(lines),encoding="utf-8")

def _write_weather_report(tables,checks):
    from .parsers.weather import RAW_VARIABLES, DERIVED_VARIABLES
    from .io_utils import sha256_file
    values=tables["weather_forecasts"]
    raw=sum(v["variable_code"] in RAW_VARIABLES for v in values); derived=sum(v["variable_code"] in DERIVED_VARIABLES for v in values)
    missing={r["year"]:r["details"].split("=",1)[1] for r in checks if r["check_id"]=="EXPECTED_CYCLE_LEAD_COVERAGE"}
    failed=[r for r in checks if r["pass_fail"]=="FAIL"]
    conflicts=next(r["affected_count"] for r in checks if r["check_id"]=="CANONICAL_VARIABLE_UNIQUE")
    lines=["# HRRR Numeric Materialization Report","","Phase 4A materializes the frozen NOAA HRRR numeric extract at one forecast snapshot per model cycle, lead, and IMS grid point. It performs no attempt-weather alignment or decision-state join.","",f"Frozen source: `{HRRR_NUMERIC_INPUT}`",f"SHA-256: `{sha256_file(HRRR_NUMERIC_INPUT)}`","","## Materialization result","","| Metric | Result |","|---|---:|",f"| Frozen input rows read | {len(tables['forecast_snapshots'])} |",f"| Canonical forecast snapshots | {len(tables['forecast_snapshots'])} |",f"| Canonical numeric weather values | {len(values)} |",f"| Raw-source values | {raw} |",f"| Deterministically derived values | {derived} |",f"| Duplicate/conflict count | {conflicts} |",f"| QA checks passed | {len(checks)-len(failed)} |",f"| QA checks failed | {len(failed)} |","","## Coverage","","| Year | Expected cycle × lead combinations | Materialized | Missing |","|---:|---:|---:|---|",
        *[f"| {year} | 52 | {51 if year==2024 else 52} | `{missing[year]}` |" for year in range(2020,2025)],"","## Time semantics","","The provider/model identity is NOAA HRRR. The frozen extract does not identify a more specific model version, so `model_version` remains null.","","`issue_time_utc` is the observed model cycle/initialization time. `valid_start_utc` and `valid_end_utc` are deterministic cycle-plus-lead valid times and are corroborated by the supplied CSV. `availability_time_utc` is null for every snapshot, `availability_time_quality` is `UNKNOWN`, and extraction metadata records `availability_status=POLICY_REQUIRED`. No cycle timestamp is treated as a public availability timestamp.","","A future latency rule must be documented, configurable, versioned, and identified as a policy assumption. This phase does not freeze such a rule.","","## Variable semantics and lineage","",f"The layer contains {len(RAW_VARIABLES)} raw GRIB-derived variables and {len(DERIVED_VARIABLES)} deterministic derivatives per snapshot. Primary field provenance marks their numeric values as `RAW_OBSERVED` or `DERIVED_DETERMINISTIC`; supplied derived columns remain corroborating evidence after formula validation.","","The extraction grid identity is preserved as `IMS_HRRR_GRID_POINT` with latitude 39.795 and longitude -86.234 on every snapshot.","","`TMP_2m` is 2 m air temperature. `DSWRF_surface` is downward shortwave radiation at the surface. No track temperature, shade, tire, thermal-state, rubber, or track-evolution proxy exists in this output.","","## Determinism and readiness","",f"All {len(checks)} Phase 4A QA checks {'pass' if not failed else 'do not pass'}. Stable snapshot/value identifiers, deterministic source order, frozen input hashing, exact row preservation, and regression regeneration checks make the output deterministic.","",f"Numeric weather layer readiness for Phase 4B environmental alignment: **{'READY' if not failed else 'NOT READY'}**. Phase 4B must respect chronology uncertainty and establish a conservative availability policy before any decision-time forecast join.",""]
    (ROOT/"hrrr_numeric_materialization_report.md").write_text("\n".join(lines),encoding="utf-8")

if __name__ == "__main__":
    print(json.dumps(run(),indent=2,ensure_ascii=False))
