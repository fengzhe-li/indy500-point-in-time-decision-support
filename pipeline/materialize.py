from collections import Counter, defaultdict
from pathlib import Path
from .config import OUTPUT, ROOT, TABLE_FIELDS
from .io_utils import write_csv
from .chronology_2024 import write_phase35_outputs

def materialize(tables, qa):
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for name, fields in TABLE_FIELDS.items():
        write_csv(OUTPUT/f"{name}.csv", tables[name], fields)
    write_csv(ROOT/"data_quality_report.csv",qa["data_quality"],["check_id","year","entity_type","severity","pass_fail","affected_count","reason","affected_identifiers"])
    write_csv(ROOT/"section_reconstruction_validation.csv",qa["sections"],["year","section_set_version","attempt_lap_reference","official_lap_time","reconstructed_lap_time","residual","section_observation_count","coverage_status","validation_reason","published_precision_seconds","tolerance_seconds","validation_pass","rule_version"])
    write_csv(ROOT/"chronology_reconciliation_report.csv",qa["chronology"],["year","check_id","check_pass","affected_count","reason_code","affected_identifiers"])
    write_csv(ROOT/"hrrr_weather_qa.csv",qa["weather"],["check_id","year","severity","pass_fail","affected_count","expected_count","actual_count","details"])
    write_csv(ROOT/"canonical_year_summary.csv",qa["year_summary"],["year","attempt_count","complete_attempts","partial_attempts","section_only_attempts","chronology_only_attempts","repeated_attempt_count_where_supportable","usable_timestamps","unresolved_timestamp_counts","chronology_status","performance_core_eligible_count","chronology_core_eligible_count","robustness_supporting_count"])
    write_csv(ROOT/"2024_chronology_constraints.csv",tables["chronology_constraints"],TABLE_FIELDS["chronology_constraints"])
    status=next(e["chronology_reconciliation_status"] for e in tables["qualifying_events"] if e["year"]==2024)
    write_phase35_outputs(tables,status)

def year_summary(tables):
    eligibility=defaultdict(list)
    for row in tables["row_eligibility"]: eligibility[row["entity_id"]].append(row)
    rows=[]
    statuses={e["year"]:e["chronology_reconciliation_status"] for e in tables["qualifying_events"]}
    constraint_by_attempt={c["attempt_id"]:c for c in tables["chronology_constraints"]}
    for year in range(2020,2025):
        attempts=[a for a in tables["attempts"] if a["session_id"].endswith(str(year))]
        core_perf=sum(any(r["analysis_target"]=="FOUR_LAP_PERFORMANCE" and r["eligible_core_training"] for r in eligibility[a["attempt_id"]]) for a in attempts)
        core_chrono=sum(any(r["analysis_target"]=="CHRONOLOGY" and r["eligible_core_training"] for r in eligibility[a["attempt_id"]]) for a in attempts)
        supporting=sum(any(r["supporting_only"] or r["robustness_only"] for r in eligibility[a["attempt_id"]]) for a in attempts)
        qualities=[constraint_by_attempt[a["attempt_id"]]["event_time_quality"] if a["attempt_id"] in constraint_by_attempt else a["event_time_quality"] for a in attempts]
        rows.append({"year":year,"attempt_count":len(attempts),"complete_attempts":sum(a["attempt_class"]=="A_COMPLETE" for a in attempts),
            "partial_attempts":sum(a["attempt_class"]=="B_PARTIAL_COMPLETE_LAPS" for a in attempts),"section_only_attempts":sum(a["attempt_class"]=="C_SECTION_ONLY" for a in attempts),
            "chronology_only_attempts":sum(a["attempt_class"]=="D_CHRONOLOGY_ONLY" for a in attempts),
            "repeated_attempt_count_where_supportable":sum((a["car_attempt_index"] or 0)>1 for a in attempts),
            "usable_timestamps":sum(q in ("EXACT_OBSERVED","APPROXIMATE_OBSERVED","BOUNDED_INTERVAL") for q in qualities),
            "unresolved_timestamp_counts":sum(q in ("UNKNOWN","ORDERING_ONLY") for q in qualities),
            "chronology_status":statuses[year],"performance_core_eligible_count":core_perf,"chronology_core_eligible_count":core_chrono,
            "robustness_supporting_count":supporting})
    return rows
