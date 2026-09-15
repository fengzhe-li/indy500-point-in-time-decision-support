#!/usr/bin/env python3
"""Read-only final QA for R5.1 data assembly."""
import hashlib,json
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'r5_1/output'
EXPECTED={'r5/frozen_inputs/day1/day1_environment_linked_transitions_39_FROZEN.csv':'a2e4dd7f10d5c6dfefb6e0ce36c79165d3e5d2d6a1d1b971eece2879aa4db355','r5/frozen_inputs/last_chance/last_chance_official_performance_15_FROZEN.csv':'0bcfd3878ba9a2cac99b892432edc264949ad54094dfaac66a1a7e699fc97649','r5/frozen_inputs/last_chance/last_chance_attempt_chronology_22_FROZEN.csv':'d50b7dd5f3f3e6735d05c92a246cd7c31ee64ffb2ceb42a226c8352a4212d10b'}
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 first=pd.read_csv(OUT/'day1_first_run_field_sweep_v1.csv',dtype={'car_number':str}); fade=pd.read_csv(OUT/'day1_within_run_fade_physics_v1.csv'); rep=pd.read_csv(OUT/'day1_same_car_repeat_inventory_v1.csv'); inv=pd.read_csv(OUT/'fast_friday_baseline_candidate_inventory_v1.csv'); lc=pd.read_csv(OUT/'last_chance_within_run_fade_physics_v1.csv'); waits=pd.read_csv(OUT/'historical_wait_regime_evidence_inventory_v1.csv')
 checks={'protected_hashes':all(sha(ROOT/p)==v for p,v in EXPECTED.items()),'first_run_168':len(first)==168,'first_unique_car_year':not first.duplicated(['year','car_number']).any(),'first_complete_order_one':first.first_complete_attempt_order.eq(1).all(),'fade_260':len(fade)==260,'repeat_92':len(rep)==92,'frozen_39':rep.in_frozen_39.astype(str).str.lower().eq('true').sum()==39,'ptsc_40':rep.ptsc_pair_available.astype(str).str.lower().eq('true').sum()==40,'last_chance_15':len(lc)==15,'fast_friday_four_lap_not_single_lap':inv.loc[inv.four_lap_average_mph.notna(),'qualifying_simulation_indicator'].astype(str).str.lower().eq('true').all(),'wait_exact_zero':waits.observed_wait_minutes.notna().sum()==0,'wait_bounds_zero':waits.lower_wait_bound_minutes.notna().sum()+waits.upper_wait_bound_minutes.notna().sum()==0,'no_model_output':not any('model' in p.name.lower() or 'recommend' in p.name.lower() for p in OUT.iterdir())}
 checks={k:bool(v) for k,v in checks.items()}; result={'status':'PASS' if all(checks.values()) else 'FAIL','checks':checks,'failures':[k for k,v in checks.items() if not v]}; print(json.dumps(result,indent=2)); raise SystemExit(0 if all(checks.values()) else 1)
if __name__=='__main__': main()
