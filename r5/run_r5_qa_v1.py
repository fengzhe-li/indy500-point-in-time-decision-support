#!/usr/bin/env python3
"""Read-only invariant checks for the generated R5 branch."""
from pathlib import Path
import json
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"r5"/"output"

def main():
    failures=[]
    tr=pd.read_csv(OUT/"r5c_same_car_physics_transitions.csv",dtype={"car_number":str})
    solar=pd.read_csv(OUT/"r5b_solar_physics_features.csv")
    future=pd.read_csv(OUT/"r5f_future_physical_state_interface.csv")
    sim=json.load(open(OUT/"r5g_report.json"))
    checks={
        "transition_count_27":len(tr)==27,
        "transition_times_forward":(pd.to_datetime(tr.after_time_utc,utc=True)>pd.to_datetime(tr.before_time_utc,utc=True)).all(),
        "all_transition_physics_safe":tr.both_ptsc_past_safe.astype(bool).all() and tr.both_hrrr_leakage_safe.astype(bool).all(),
        "solar_complement":((solar.solar_elevation_deg+solar.solar_zenith_deg-90).abs()<1e-8).all(),
        "solar_azimuth_bounds":solar.solar_azimuth_deg.between(0,360,inclusive="left").all(),
        "future_ready_issue_gate":True,
        "future_ready_track_past_only":True,
        "simulator_full_support_50":sim["supported_decisions"]==50,
        "simulator_blocked_10":sim["blocked_decisions"]==10,
    }
    ready=future.future_state_status.eq("READY_DECISION_SAFE_FORECAST")
    checks["future_ready_issue_gate"]=(pd.to_datetime(future.loc[ready,"selected_hrrr_cycle_utc"],utc=True)+pd.Timedelta(minutes=90)<=pd.to_datetime(future.loc[ready,"decision_time_utc"],utc=True)).all()
    checks["future_ready_track_past_only"]=(pd.to_datetime(future.loc[ready,"track_observation_time_utc"],utc=True)<=pd.to_datetime(future.loc[ready,"decision_time_utc"],utc=True)).all()
    for p in sorted(OUT.glob("*qa.csv")):
        q=pd.read_csv(p)
        checks[f"no_FAIL::{p.name}"]=not q.status.astype(str).eq("FAIL").any()
    checks={k:bool(v) for k,v in checks.items()}
    failures=[k for k,v in checks.items() if not v]
    result={"status":"PASS" if not failures else "FAIL","checks":checks,"failures":failures}
    print(json.dumps(result,indent=2))
    if failures: raise SystemExit(1)

if __name__=="__main__": main()
