#!/usr/bin/env python3
from __future__ import annotations

import hashlib, json, math
from pathlib import Path
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"r5_1"/"output"; OUT.mkdir(parents=True,exist_ok=True)
PROTECTED={
"r5/frozen_inputs/day1/day1_environment_linked_transitions_39_FROZEN.csv":"a2e4dd7f10d5c6dfefb6e0ce36c79165d3e5d2d6a1d1b971eece2879aa4db355",
"r5/frozen_inputs/last_chance/last_chance_official_performance_15_FROZEN.csv":"0bcfd3878ba9a2cac99b892432edc264949ad54094dfaac66a1a7e699fc97649",
"r5/frozen_inputs/last_chance/last_chance_attempt_chronology_22_FROZEN.csv":"d50b7dd5f3f3e6735d05c92a246cd7c31ee64ffb2ceb42a226c8352a4212d10b"}

def h(p):
 q=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1<<20),b''): q.update(b)
 return q.hexdigest()
def csv(d,n): d.to_csv(OUT/n,index=False,lineterminator='\n',float_format='%.10g')
def js(o,n): (OUT/n).write_text(json.dumps(o,indent=2,sort_keys=True,default=lambda x:int(x) if isinstance(x,np.integer) else float(x) if isinstance(x,np.floating) else str(x))+'\n')
def hashes(): return {p:h(ROOT/p) for p in PROTECTED}
def truth(s): return s.astype(str).str.lower().eq('true')

def solar(ts):
 t=pd.Timestamp(ts)
 if pd.isna(t): return (np.nan,np.nan,np.nan)
 t=t.tz_localize('UTC') if t.tzinfo is None else t.tz_convert('UTC')
 doy=t.dayofyear; hour=t.hour+t.minute/60+t.second/3600
 g=2*math.pi/365*(doy-1+(hour-12)/24)
 eq=229.18*(.000075+.001868*math.cos(g)-.032077*math.sin(g)-.014615*math.cos(2*g)-.040849*math.sin(2*g))
 dec=.006918-.399912*math.cos(g)+.070257*math.sin(g)-.006758*math.cos(2*g)+.000907*math.sin(2*g)-.002697*math.cos(3*g)+.00148*math.sin(3*g)
 ha=math.radians(((hour*60+eq+4*(-86.234))%1440)/4-180); lat=math.radians(39.795)
 z=math.degrees(math.acos(np.clip(math.sin(lat)*math.sin(dec)+math.cos(lat)*math.cos(dec)*math.cos(ha),-1,1)))
 az=(math.degrees(math.atan2(math.sin(ha),math.cos(ha)*math.sin(lat)-math.tan(dec)*math.cos(lat)))+180)%360
 return 90-z,z,az

def physical_backbone(p1):
 ctx=pd.read_csv(ROOT/'weather/output/performance_context_features.csv',dtype={'car_number':str})
 strict=pd.read_csv(ROOT/'r5/output/r5b_solar_physics_features.csv',dtype={'car_number':str})
 real=pd.read_csv(ROOT/'weather/output/performance_grade_attempt_realized_environment.csv',dtype={'car_number':str})
 keep=['attempt_id','forecast_temp_c','forecast_dewpoint_c','forecast_relative_humidity_pct','forecast_wind_speed_10m_ms','forecast_wind_direction_deg','forecast_gust_ms','forecast_pressure_hpa','forecast_cloud_cover_pct','forecast_shortwave_radiation_wm2','selected_issue_time_utc','leakage_safe']
 x=p1.merge(ctx[keep],on='attempt_id',how='left').merge(real[['attempt_id','ptsc_track_c','ptsc_ambient_c','ptsc_humidity','ptsc_wind','ptsc_pressure','ptsc_alignment_status']],on='attempt_id',how='left')
 sk=['attempt_id','track_temperature_c','track_observation_time_utc','track_observation_age_minutes','solar_elevation_deg','solar_zenith_deg','solar_azimuth_deg']
 x=x.merge(strict[sk],on='attempt_id',how='left')
 x['track_temperature_c_assembled']=x.track_temperature_c.combine_first(x.ptsc_track_c)
 x['track_temperature_source']=np.where(x.track_temperature_c.notna(),'PAST_SAFE_PTSC_AT_OR_BEFORE_ATTEMPT',np.where(x.ptsc_track_c.notna(),'PTSC_REALIZED_INTERPOLATION_CONTEXT_ONLY','UNAVAILABLE'))
 times=pd.to_datetime(x.time_point_utc.combine_first(x.canonical_start_time_utc),utc=True,errors='coerce')
 sol=[solar(t) for t in times]
 for j,c in enumerate(['solar_elevation_derived_deg','solar_zenith_derived_deg','solar_azimuth_derived_deg']): x[c]=[v[j] for v in sol]
 x['solar_elevation_deg_assembled']=x.solar_elevation_deg.combine_first(x.solar_elevation_derived_deg)
 x['solar_zenith_deg_assembled']=x.solar_zenith_deg.combine_first(x.solar_zenith_derived_deg)
 x['solar_azimuth_deg_assembled']=x.solar_azimuth_deg.combine_first(x.solar_azimuth_derived_deg)
 rad=np.pi/180*x.forecast_wind_direction_deg
 x['wind_u_ms']=-x.forecast_wind_speed_10m_ms*np.sin(rad); x['wind_v_ms']=-x.forecast_wind_speed_10m_ms*np.cos(rad)
 T=x.forecast_temp_c+273.15; pv=6.112*np.exp(17.67*x.forecast_dewpoint_c/(x.forecast_dewpoint_c+243.5))*100; pdry=x.forecast_pressure_hpa*100-pv
 x['air_density_kg_m3']=pdry/(287.05*T)+pv/(461.495*T)
 x['physical_link_quality']=np.select([x.track_temperature_c.notna()&x.forecast_temp_c.notna(),x.ptsc_track_c.notna()&x.forecast_temp_c.notna(),x.forecast_temp_c.notna(),x.ptsc_track_c.notna()],['PAST_SAFE_TRACK_PLUS_ISSUE_GATED_HRRR','REALIZED_INTERPOLATED_TRACK_PLUS_ISSUE_GATED_HRRR','HRRR_ONLY','PTSC_ONLY'],default='UNAVAILABLE')
 return x

def fast_friday(entrants):
 ev=pd.read_csv(ROOT/'r4/output/r4f6k_expanded_fast_friday_all_evidence_v1.csv',dtype={'car_number':str})
 can=pd.read_csv(ROOT/'r4/output/r4f6k_expanded_fast_friday_canonical_panel_v1.csv',dtype={'car_number':str})
 ev=ev[ev.year.between(2020,2024)].copy(); entrants=entrants.copy()
 keys=entrants[['year','car_number','driver_name','team_name']].drop_duplicates()
 inv=keys.merge(ev,on=['year','car_number'],how='left',suffixes=('_day1','_ff'))
 ck={(int(r.year),str(r.car_number),r.reference_type,round(float(r.reference_speed_mph),6)) for _,r in can[can.year.between(2020,2024)].iterrows()}
 inv['driver_name']=inv.driver_name_day1.combine_first(inv.driver_name_ff)
 inv['source_path']=inv.source_file; inv['qualifying_simulation_indicator']=inv.reference_type.eq('FOUR_LAP_QUALIFYING_SIM')
 inv['four_lap_average_mph']=inv.reference_speed_mph.where(inv.qualifying_simulation_indicator)
 for c in ['lap1','lap2','lap3','lap4']: inv[c]=np.nan
 inv['single_lap_speed_if_present']=inv.reference_speed_mph.where(~inv.qualifying_simulation_indicator)
 inv['no_tow_indicator_if_present']=inv.reference_type.eq('NO_TOW_SINGLE_LAP').where(inv.reference_type.notna())
 inv['timestamp_or_order']=inv.pdf_position
 inv['weather_linkage_if_present']='UNAVAILABLE'
 inv['existing_baseline_reference']=[pd.notna(r.reference_speed_mph) and (int(r.year),str(r.car_number),r.reference_type,round(float(r.reference_speed_mph),6)) in ck for _,r in inv.iterrows()]
 counts=inv.groupby(['year','car_number']).reference_speed_mph.transform('count')
 inv['baseline_quality']=np.where(inv.reference_speed_mph.isna(),'MISSING',np.where(inv.qualifying_simulation_indicator,inv.source_quality.astype(str)+'_FOUR_LAP_QUAL_SIM',inv.source_quality.astype(str)+'_'+inv.reference_type.astype(str)))
 inv['ambiguity_reason']=np.where(inv.reference_speed_mph.isna(),'NO_EXISTING_REFERENCE',np.where(counts>1,'MULTIPLE_CANDIDATE_EVIDENCE_ROWS',np.where(~inv.qualifying_simulation_indicator,'REFERENCE_IS_SINGLE_LAP_NOT_FOUR_LAP_AVERAGE','')))
 cols=['year','car_number','driver_name','team_name','source_path','source_type','qualifying_simulation_indicator','four_lap_average_mph','lap1','lap2','lap3','lap4','single_lap_speed_if_present','no_tow_indicator_if_present','timestamp_or_order','weather_linkage_if_present','existing_baseline_reference','reference_speed_mph','reference_type','baseline_quality','ambiguity_reason','source_quality','source_url','provenance_note']
 inv=inv[cols].sort_values(['year','car_number','existing_baseline_reference'],ascending=[True,True,False]); csv(inv,'fast_friday_baseline_candidate_inventory_v1.csv')
 rows=[]
 for y,g in keys.groupby('year'):
  cars=g.car_number.astype(str); q=inv[inv.year==y]
  avail=set(q.loc[q.existing_baseline_reference,'car_number'].astype(str)); four=set(q.loc[q.qualifying_simulation_indicator& q.four_lap_average_mph.notna(),'car_number'].astype(str)); amb=set(q.loc[q.ambiguity_reason.ne(''),'car_number'].astype(str))
  rows.append({'year':y,'day1_entrants':cars.nunique(),'fast_friday_reference_available':len(set(cars)&avail),'four_lap_fast_friday_average_available':len(set(cars)&four),'ambiguous_baseline':len(set(cars)&amb),'missing_baseline':len(set(cars)-avail)})
 cov=pd.DataFrame(rows); csv(cov,'fast_friday_baseline_coverage_report_v1.csv')
 return inv,cov,can

def add_lap_metrics(d, speed_prefix='lap'):
 x=d.copy(); speeds=[]
 for i in range(1,5):
  c=f'{speed_prefix}{i}_speed_mph'; speeds.append(c); x[f'lap{i}_s']=9000/x[c]
 x['lap2_minus_lap1']=x[speeds[1]]-x[speeds[0]]; x['lap3_minus_lap2']=x[speeds[2]]-x[speeds[1]]; x['lap4_minus_lap3']=x[speeds[3]]-x[speeds[2]]; x['lap4_minus_lap1']=x[speeds[3]]-x[speeds[0]]
 x['mean_laps_3_4_minus_mean_laps_1_2']=(x[speeds[2]]+x[speeds[3]]-x[speeds[0]]-x[speeds[1]])/2
 x['four_lap_slope_mph_per_lap']=[np.polyfit([1,2,3,4],r,1)[0] if np.isfinite(r).all() else np.nan for r in x[speeds].to_numpy(float)]
 return x

def day1_tables(p1,phys,ffcan):
 comp=phys[truth(phys.complete_performance_record)].copy(); comp['_row']=np.arange(len(comp)); comp['_idx']=pd.to_numeric(comp.car_attempt_index,errors='coerce').fillna(1e9)
 # Select an actual source row. groupby.first() is forbidden here because it can
 # combine the first non-null value of each column from different attempts.
 first=comp.sort_values(['year','car_number','_idx','_row']).drop_duplicates(['year','car_number'],keep='first').copy()
 first=add_lap_metrics(first)
 ff=ffcan[ffcan.year.between(2020,2024)].copy(); ff=ff.sort_values('reference_priority').drop_duplicates(['year','car_number'])
 ff=ff[['year','car_number','reference_speed_mph','reference_type','source_quality']].rename(columns={'reference_speed_mph':'own_car_fast_friday_baseline_reference','reference_type':'fast_friday_reference_type','source_quality':'fast_friday_baseline_quality'})
 first=first.merge(ff,on=['year','car_number'],how='left'); first['own_car_fast_friday_four_lap_average_mph']=first.own_car_fast_friday_baseline_reference.where(first.fast_friday_reference_type.eq('FOUR_LAP_QUALIFYING_SIM'))
 first['day1_minus_own_fast_friday_four_lap_mph']=first.four_lap_average_speed_mph-first.own_car_fast_friday_four_lap_average_mph
 first['source_car_attempt_index']=first.car_attempt_index; first['first_complete_attempt_order']=1
 t=pd.to_datetime(first.time_point_utc.combine_first(first.canonical_start_time_utc),utc=True,errors='coerce'); first['timestamp_utc']=t
 first['attempt_order']=t.groupby(first.year).rank(method='first').where(t.notna()).combine_first(first.global_order_lower_bound)
 first['attempt_order_basis']=np.where(t.notna(),'AVAILABLE_TIMESTAMP_ORDER',np.where(first.global_order_lower_bound.notna(),'CANONICAL_GLOBAL_ORDER_BOUND','UNKNOWN'))
 first['chronology_quality']=first.canonical_event_time_quality; first['elapsed_session_position_minutes']=t.groupby(first.year).transform(lambda s:(s-s.min()).dt.total_seconds()/60)
 first['track_temperature']=first.track_temperature_c_assembled; first['track_temperature_trend_c_per_min']=np.nan
 strict=pd.read_csv(ROOT/'r5/output/r5b_solar_physics_features.csv'); slope=pd.read_csv(ROOT/'r4/output/r4f7c2c_frozen_numeric_model_matrix_v1.csv')[['attempt_id','ptsc_track_temp_slope_c_per_min_past_safe']]
 first=first.merge(slope,on='attempt_id',how='left'); first['track_temperature_trend_c_per_min']=first.ptsc_track_temp_slope_c_per_min_past_safe
 first['air_temperature_c']=first.forecast_temp_c; first['dew_point_c']=first.forecast_dewpoint_c; first['humidity_pct']=first.forecast_relative_humidity_pct; first['pressure_hpa']=first.forecast_pressure_hpa; first['wind_speed_ms']=first.forecast_wind_speed_10m_ms; first['gust_ms']=first.forecast_gust_ms; first['wind_direction_deg']=first.forecast_wind_direction_deg; first['shortwave_radiation_wm2']=first.forecast_shortwave_radiation_wm2; first['cloud_cover_pct']=first.forecast_cloud_cover_pct
 first['first_half_vs_second_half_fade_mph']=first.late_run_fade_mph
 first['team_year_id']=first.year.astype(str)+'|'+first.team_name.fillna('UNKNOWN')
 first['teammate_identifiers']=['|'.join(sorted(set(map(str,first[(first.year==r.year)&(first.team_name==r.team_name)&(first.car_number.astype(str)!=str(r.car_number))].car_number)))) for _,r in first.iterrows()]
 outcols=['year','car_number','driver_name','team_name','attempt_id','first_complete_attempt_order','source_car_attempt_index','lap1_s','lap2_s','lap3_s','lap4_s','four_lap_average_speed_mph','lap1_to_lap4_delta_mph','first_half_vs_second_half_fade_mph','four_lap_slope_mph_per_lap','attempt_order','attempt_order_basis','timestamp_utc','chronology_quality','elapsed_session_position_minutes','own_car_fast_friday_baseline_reference','own_car_fast_friday_four_lap_average_mph','fast_friday_reference_type','fast_friday_baseline_quality','day1_minus_own_fast_friday_four_lap_mph','track_temperature','track_temperature_trend_c_per_min','air_temperature_c','dew_point_c','humidity_pct','pressure_hpa','air_density_kg_m3','wind_speed_ms','gust_ms','wind_direction_deg','wind_u_ms','wind_v_ms','solar_elevation_deg_assembled','solar_zenith_deg_assembled','solar_azimuth_deg_assembled','shortwave_radiation_wm2','cloud_cover_pct','team_year_id','teammate_identifiers','physical_link_quality']
 firstout=first[outcols].sort_values(['year','timestamp_utc','car_number']); csv(firstout,'day1_first_run_field_sweep_v1.csv')
 fade=add_lap_metrics(comp); fade['thermal_degradation_interpretation']='FOUR_LAP_FADE_PROXY_NOT_MEASURED_TYRE_WEAR'
 fcols=['year','car_number','driver_name','team_name','attempt_id','car_attempt_index','lap1_s','lap2_s','lap3_s','lap4_s','lap1_speed_mph','lap2_speed_mph','lap3_speed_mph','lap4_speed_mph','four_lap_average_speed_mph','lap2_minus_lap1','lap3_minus_lap2','lap4_minus_lap3','lap4_minus_lap1','mean_laps_3_4_minus_mean_laps_1_2','four_lap_slope_mph_per_lap','track_temperature_c_assembled','forecast_temp_c','forecast_dewpoint_c','forecast_relative_humidity_pct','forecast_pressure_hpa','air_density_kg_m3','forecast_wind_speed_10m_ms','forecast_gust_ms','forecast_wind_direction_deg','wind_u_ms','wind_v_ms','solar_elevation_deg_assembled','solar_zenith_deg_assembled','solar_azimuth_deg_assembled','forecast_shortwave_radiation_wm2','forecast_cloud_cover_pct','physical_link_quality','thermal_degradation_interpretation']
 csv(fade[fcols].sort_values(['year','car_number','car_attempt_index']),'day1_within_run_fade_physics_v1.csv')
 miss=[]
 fields=['own_car_fast_friday_baseline_reference','own_car_fast_friday_four_lap_average_mph','timestamp_utc','track_temperature','air_temperature_c','dew_point_c','humidity_pct','pressure_hpa','wind_speed_ms','gust_ms','solar_elevation_deg_assembled','shortwave_radiation_wm2','cloud_cover_pct']
 for y,g in firstout.groupby('year'):
  for f in fields: miss.append({'year':y,'table':'DAY1_FIRST_RUN','field':f,'rows':len(g),'non_null':int(g[f].notna().sum()),'missing':int(g[f].isna().sum()),'coverage_pct':100*g[f].notna().mean()})
 csv(pd.DataFrame(miss),'day1_first_run_join_missingness_by_year_v1.csv')
 return firstout,fade

def last_chance_tables():
 perf=pd.read_csv(ROOT/'r5/frozen_inputs/last_chance/last_chance_official_performance_15_FROZEN.csv',dtype={'car_number':str})
 x=perf.copy()
 for i in range(1,5): x[f'lap{i}_speed_mph']=9000/x[f'lap{i}_s']
 speeds=[f'lap{i}_speed_mph' for i in range(1,5)]
 x['lap2_minus_lap1']=x.lap2_s-x.lap1_s; x['lap3_minus_lap2']=x.lap3_s-x.lap2_s; x['lap4_minus_lap3']=x.lap4_s-x.lap3_s; x['lap4_minus_lap1']=x.lap4_s-x.lap1_s; x['mean_laps_3_4_minus_mean_laps_1_2']=(x.lap3_s+x.lap4_s-x.lap1_s-x.lap2_s)/2
 x['four_lap_slope_seconds_per_lap']=[np.polyfit([1,2,3,4],r,1)[0] for r in x[['lap1_s','lap2_s','lap3_s','lap4_s']].to_numpy(float)]
 for col in ['track_temperature_c','air_temperature_c','dewpoint_c','relative_humidity_pct','pressure_hpa','air_density_kg_m3','wind_speed_ms','gust_ms','wind_direction_deg','wind_u_ms','wind_v_ms','solar_elevation_deg','solar_zenith_deg','solar_azimuth_deg','shortwave_radiation_wm2','cloud_cover_pct']: x[col]=np.nan
 x['physical_link_quality']='UNAVAILABLE_NO_EXACT_TIMESTAMP'; x['thermal_degradation_interpretation']='FOUR_LAP_FADE_PROXY_NOT_MEASURED_TYRE_WEAR'
 csv(x,'last_chance_within_run_fade_physics_v1.csv')
 c=pd.read_csv(ROOT/'r5/frozen_inputs/last_chance/last_chance_attempt_chronology_22_FROZEN.csv',dtype={'car_number':str})
 c['repeat_opportunity_class']='CHRONOLOGY_ONLY_OR_INITIAL'
 for (y,car),g in c.groupby(['year','car_number']):
  idx=list(g.sort_values('attempt_ordinal',na_position='last').index)
  if g.event_kind.eq('COMPLETE_REPEAT_RECORD').sum()>=2: c.loc[idx,'repeat_opportunity_class']='COMPLETE_TO_COMPLETE_ORDER_UNRESOLVED'
  else:
   ordered=g[g.attempt_ordinal.notna()].sort_values('attempt_ordinal'); prev=None
   for ix,r in ordered.iterrows():
    if prev is not None:
     a=str(prev.completion_status); b=str(r.completion_status)
     if 'CRASH' in b: cls='COMPLETE_TO_CRASH_INCOMPLETE' if 'COMPLETE' in a else 'INCOMPLETE_TO_CRASH'
     elif b=='COMPLETE' or 'COMPLETE_BUT' in b: cls='COMPLETE_TO_COMPLETE' if a=='COMPLETE' else 'PARTIAL_TO_COMPLETE'
     elif 'WAVED' in b or 'FAILED' in b: cls='COMPLETE_TO_PARTIAL' if a=='COMPLETE' else 'PARTIAL_TO_PARTIAL'
     else: cls='CHRONOLOGY_ONLY'
     c.loc[ix,'repeat_opportunity_class']=cls
    prev=r
   if len(ordered): c.loc[ordered.index[0],'repeat_opportunity_class']='INITIAL_ATTEMPT'
 c['four_lap_delta_target_eligible']=c.repeat_opportunity_class.eq('COMPLETE_TO_COMPLETE') & c.performance_mph.notna()
 csv(c,'last_chance_same_car_repeat_inventory_v1.csv')
 return x,c

def repeats(phys):
 p=pd.read_csv(ROOT/'r4/output/r4p2_multi_run_transitions_v1.csv',dtype={'car_number':str}); frozen=pd.read_csv(ROOT/'r5/frozen_inputs/day1/day1_environment_linked_transitions_39_FROZEN.csv')
 ids=set(frozen.transition_id); p['in_frozen_39']=p.transition_id.isin(ids)
 state_cols={'track_temperature_c_assembled':'track_temp_c','forecast_temp_c':'air_temp_c','forecast_dewpoint_c':'dewpoint_c','forecast_relative_humidity_pct':'relative_humidity_pct','forecast_pressure_hpa':'pressure_hpa','air_density_kg_m3':'air_density_kg_m3','forecast_wind_speed_10m_ms':'wind_speed_ms','forecast_gust_ms':'gust_ms','forecast_wind_direction_deg':'wind_direction_deg','wind_u_ms':'wind_u_ms','wind_v_ms':'wind_v_ms','solar_elevation_deg_assembled':'solar_elevation_deg','solar_zenith_deg_assembled':'solar_zenith_deg','solar_azimuth_deg_assembled':'solar_azimuth_deg','forecast_shortwave_radiation_wm2':'shortwave_radiation_wm2','forecast_cloud_cover_pct':'cloud_cover_pct'}
 lookup=phys[['attempt_id']+list(state_cols)].drop_duplicates('attempt_id')
 for side,key in [('previous','before_attempt_id'),('next','after_attempt_id')]:
  z=lookup.rename(columns={'attempt_id':key,**{c:f'{side}_{n}' for c,n in state_cols.items()}})
  p=p.merge(z,on=key,how='left')
 for n in state_cols.values():
  a,b=f'previous_{n}',f'next_{n}'
  if a in p and b in p:
   p[f'delta_{n}']=((p[b]-p[a]+180)%360-180) if n=='wind_direction_deg' else p[b]-p[a]
 p['physical_link_quality']=np.select([p.in_frozen_39,truth(p.ptsc_pair_available)&~truth(p.hrrr_pair_available),truth(p.ptsc_pair_available),truth(p.hrrr_pair_available)],['FROZEN_39_FULL_ENVIRONMENT','PTSC_PAIR_ONLY_NO_HRRR_PAIR','PTSC_PAIR_OTHER','HRRR_PAIR_ONLY'],default='NO_PAIRED_PHYSICAL_STATE')
 p['exclusion_reason']=np.where(p.in_frozen_39,'',np.where(truth(p.ptsc_pair_available)&~truth(p.hrrr_pair_available),'PTSC_PAIR_AVAILABLE_BUT_HRRR_PAIR_UNAVAILABLE',np.where(~truth(p.ptsc_pair_available),'PTSC_PAIR_UNAVAILABLE','DOES_NOT_MEET_FROZEN_FULL_ENVIRONMENT_CRITERION')))
 csv(p,'day1_same_car_repeat_inventory_v1.csv')
 extra=p[truth(p.ptsc_pair_available)&~truth(p.full_environment_pair_available)][['transition_id','year','car_number','driver_name','hrrr_pair_available','ptsc_pair_available','full_environment_pair_available','exclusion_reason']]
 csv(extra,'day1_39_vs_40_reconciliation_v1.csv')
 return p,extra

def teams(first):
 rows=[]
 for (y,team),g in first.groupby(['year','team_name'],dropna=False):
  for _,r in g.iterrows():
   mates=g[g.car_number.astype(str)!=str(r.car_number)]
   t=pd.Timestamp(r.timestamp_utc) if pd.notna(r.timestamp_utc) else pd.NaT
   valid=mates[mates.timestamp_utc.notna()].copy() if pd.notna(t) else mates.iloc[0:0].copy()
   if len(valid):
    valid['_sep']=valid.timestamp_utc.map(lambda v:abs((pd.Timestamp(v)-t).total_seconds()/60)); near=valid.sort_values('_sep').iloc[0]
    nearcar=near.car_number; sep=near._sep; dtrack=near.track_temperature-r.track_temperature if pd.notna(near.track_temperature) and pd.notna(r.track_temperature) else np.nan; dair=near.air_temperature_c-r.air_temperature_c if pd.notna(near.air_temperature_c) and pd.notna(r.air_temperature_c) else np.nan; assess='DIRECT_DIFFERENCES_REPORTED_NO_BINARY_SIMILARITY_THRESHOLD'
   else: nearcar=''; sep=dtrack=dair=np.nan; assess='UNAVAILABLE'
   rows.append({'year':y,'team_name':team,'team_year_id':r.team_year_id,'car_number':r.car_number,'driver_name':r.driver_name,'teammate_cars':'|'.join(map(str,mates.car_number)),'teammate_drivers':'|'.join(mates.driver_name.astype(str)),'nearest_teammate_car':nearcar,'nearest_teammate_timing_separation_min':sep,'nearest_teammate_track_temp_difference_c':dtrack,'nearest_teammate_air_temp_difference_c':dair,'similar_physical_conditions':assess,'own_fast_friday_reference_available':pd.notna(r.own_car_fast_friday_baseline_reference),'teammate_fast_friday_references_available':int(mates.own_car_fast_friday_baseline_reference.notna().sum()),'own_day1_first_run_speed_mph':r.four_lap_average_speed_mph,'teammate_day1_first_run_speeds_mph':'|'.join(map(str,mates.four_lap_average_speed_mph.round(3))), 'teammates_are_identical_assumption':False})
 out=pd.DataFrame(rows); csv(out,'team_year_control_inventory_v1.csv'); return out

def waits():
 base='weather/output/queue_wait_evidence_inventory_v1.csv'
 rows=[]
 for regime,sem in [('DAY1_LANE1_PRIORITY','Day1 priority lane'),('DAY1_LANE2_RETAIN','Day1 retain-result queue')]:
  rows.append({'year':'2020-2024','regime':regime,'car_number':'UNKNOWN','driver_name':'UNKNOWN','queue_entry_time':'UNKNOWN','run_time':'UNKNOWN','observed_wait_minutes':np.nan,'lower_wait_bound_minutes':np.nan,'upper_wait_bound_minutes':np.nan,'related_attempt_interval_minutes':np.nan,'related_interval_lower_minutes':np.nan,'related_interval_upper_minutes':np.nan,'source':base,'evidence_quality':'UNAVAILABLE_DIRECT_WAIT','evidence_class':'unavailable','note':sem+' has no recovered queue-entry/run-start pair.'})
 # All 92 complete-to-complete Day1 transitions are relevant opportunities, but
 # their elapsed times are explicitly performance-observation intervals, not waits.
 p=pd.read_csv(ROOT/'r4/output/r4p2_multi_run_transitions_v1.csv',dtype={'car_number':str})
 for _,r in p.iterrows():
  rows.append({'year':int(r.year),'regime':'DAY1_LANE_UNKNOWN_REPEAT','car_number':r.car_number,'driver_name':r.driver_name,'queue_entry_time':'UNKNOWN','run_time':r.after_time_utc if pd.notna(r.after_time_utc) else 'UNKNOWN','observed_wait_minutes':np.nan,'lower_wait_bound_minutes':np.nan,'upper_wait_bound_minutes':np.nan,'related_attempt_interval_minutes':r.elapsed_between_performance_observations_min,'related_interval_lower_minutes':np.nan,'related_interval_upper_minutes':np.nan,'source':'r4/output/r4p2_multi_run_transitions_v1.csv','evidence_quality':'ATTEMPT_INTERVAL_NOT_QUEUE_WAIT','evidence_class':'unavailable','note':'Lane and queue-entry time are not observed; elapsed interval must not be converted to queue wait.'})
 # Five Last Chance ordinal reattempt links exist, all without exact timestamps.
 lc=pd.read_csv(ROOT/'r5/frozen_inputs/last_chance/last_chance_attempt_chronology_22_FROZEN.csv',dtype={'car_number':str})
 for (year,car),g in lc.groupby(['year','car_number']):
  g=g[g.attempt_ordinal.notna()].sort_values('attempt_ordinal')
  for i in range(1,len(g)):
   r=g.iloc[i]
   rows.append({'year':int(year),'regime':'LAST_CHANCE_REATTEMPT','car_number':car,'driver_name':r.driver_name,'queue_entry_time':'UNKNOWN','run_time':r.exact_timestamp if pd.notna(r.exact_timestamp) else 'UNKNOWN','observed_wait_minutes':np.nan,'lower_wait_bound_minutes':np.nan,'upper_wait_bound_minutes':np.nan,'related_attempt_interval_minutes':np.nan,'related_interval_lower_minutes':np.nan,'related_interval_upper_minutes':np.nan,'source':'r5/frozen_inputs/last_chance/last_chance_attempt_chronology_22_FROZEN.csv','evidence_quality':'PARTIAL_ORDER_NO_TIME_PAIR','evidence_class':'unavailable','note':f'Attempt {int(g.iloc[i-1].attempt_ordinal)} to {int(r.attempt_ordinal)} is ordered, but has no queue-entry/run-start time pair.'})
 # The 2024 VeeKay event anchors bound an event-to-event interval of 24-26
 # minutes. They do not bound queue wait and lane is not directly observed.
 rows.append({'year':2024,'regime':'DAY1_LANE_UNKNOWN_EVENT_INTERVAL','car_number':'21','driver_name':'Rinus VeeKay','queue_entry_time':'UNKNOWN','run_time':'2024-05-18T19:50:00Z/2024-05-18T19:52:00Z event bound','observed_wait_minutes':np.nan,'lower_wait_bound_minutes':np.nan,'upper_wait_bound_minutes':np.nan,'related_attempt_interval_minutes':25.0,'related_interval_lower_minutes':24.0,'related_interval_upper_minutes':26.0,'source':'weather/output/unified_attempt_chronology_constraint_ledger_v9.csv','evidence_quality':'EVENT_TO_EVENT_BOUND_NOT_QUEUE_WAIT','evidence_class':'bounded_event_interval_only','note':'19:26 attempt occurrence to 19:50-19:52 later event; no queue-entry observation and no lane inference.'})
 out=pd.DataFrame(rows); csv(out,'historical_wait_regime_evidence_inventory_v1.csv')
 rep={'inventory_rows':len(out),'exact_historical_wait_observations':0,'bounded_historical_wait_observations':0,'related_timed_attempt_intervals':int(out.related_attempt_interval_minutes.notna().sum()),'by_regime':{r:{'rows':int((out.regime==r).sum()),'exact_wait':0,'bounded_wait':0,'status':'UNAVAILABLE_AS_QUEUE_WAIT'} for r in sorted(out.regime.unique())},'structural_wait_grids_used':False,'inter_attempt_gap_used_as_wait':False,'source':base}
 js(rep,'historical_wait_regime_coverage_report_v1.json'); return out,rep

def roles():
 rows=[
('track_temperature','PRIMARY_THERMAL_STATE','OBSERVED_PTSC','surface temperature; not ambient'),('track_temperature_trend','PRIMARY_THERMAL_STATE','DERIVED_FROM_PRIOR_PTSC','past-only trend where available'),('solar_radiation','FUTURE_TRACK_STATE_DRIVER','HRRR_FORECAST','downward shortwave'),('solar_geometry','FUTURE_TRACK_STATE_DRIVER','DETERMINISTIC_ASTRONOMY','not corner shadow'),('cloud_cover','FUTURE_TRACK_STATE_DRIVER','HRRR_FORECAST','not direct shade'),('air_temperature','FUTURE_TRACK_STATE_DRIVER','HRRR_FORECAST','must not substitute for track temperature'),('wind_speed','DIRECT_PERFORMANCE_AERO_CANDIDATE','HRRR_FORECAST','also cooling driver'),('gust','DIRECT_PERFORMANCE_AERO_CANDIDATE','HRRR_FORECAST',''),('wind_vector_uv','DIRECT_PERFORMANCE_AERO_CANDIDATE','DERIVED_FROM_HRRR','meteorological direction conversion'),('air_density','DIRECT_PERFORMANCE_AERO_CANDIDATE','DERIVED_FROM_HRRR','moist-air ideal gas calculation'),('pressure','ATMOSPHERIC_SUPPORT','HRRR_FORECAST',''),('relative_humidity','ATMOSPHERIC_SUPPORT','HRRR_FORECAST',''),('dew_point','ATMOSPHERIC_SUPPORT','HRRR_FORECAST',''),('four_lap_fade','DEGRADATION_PROXY','OFFICIAL_LAP_SPEEDS','not measured tyre wear'),('tyre_temperature','UNAVAILABLE_DIRECT_MEASUREMENT','UNAVAILABLE','must not be fabricated'),('direct_tyre_wear','UNAVAILABLE_DIRECT_MEASUREMENT','UNAVAILABLE','must not be fabricated')]
 d=pd.DataFrame(rows,columns=['feature','role','evidence_class','interpretation_boundary']); csv(d,'physics_feature_role_map_v1.csv')

def physical_missingness(first,fade,repeats,lcfade):
 rows=[]
 specs=[
  ('DAY1_FIRST_RUN',first,{'track_temperature':'track_temperature','air_temperature':'air_temperature_c','dew_point':'dew_point_c','humidity':'humidity_pct','pressure':'pressure_hpa','air_density':'air_density_kg_m3','wind_speed':'wind_speed_ms','gust':'gust_ms','wind_direction':'wind_direction_deg','solar_geometry':'solar_elevation_deg_assembled','shortwave_radiation':'shortwave_radiation_wm2','cloud_cover':'cloud_cover_pct'}),
  ('DAY1_ALL_COMPLETE_FADE',fade,{'track_temperature':'track_temperature_c_assembled','air_temperature':'forecast_temp_c','dew_point':'forecast_dewpoint_c','humidity':'forecast_relative_humidity_pct','pressure':'forecast_pressure_hpa','air_density':'air_density_kg_m3','wind_speed':'forecast_wind_speed_10m_ms','gust':'forecast_gust_ms','wind_direction':'forecast_wind_direction_deg','solar_geometry':'solar_elevation_deg_assembled','shortwave_radiation':'forecast_shortwave_radiation_wm2','cloud_cover':'forecast_cloud_cover_pct'}),
  ('DAY1_REPEAT_PAIRS',repeats,{'track_temperature':'before_ptsc_track_c','air_temperature':'before_forecast_temp_c','humidity':'delta_forecast_relative_humidity_pct','pressure':'delta_forecast_pressure_hpa','wind_speed':'delta_forecast_wind_speed_10m_ms','gust':'delta_forecast_gust_ms','shortwave_radiation':'delta_forecast_shortwave_radiation_wm2','cloud_cover':'delta_forecast_cloud_cover_pct'}),
 ]
 for layer,d,mapping in specs:
  for y,g in d.groupby('year'):
   for concept,col in mapping.items(): rows.append({'year':int(y),'evidence_layer':layer,'physical_variable':concept,'rows':len(g),'non_null_rows':int(g[col].notna().sum()),'missing_rows':int(g[col].isna().sum()),'coverage_pct':100*g[col].notna().mean()})
 for y,g in lcfade.groupby('year'):
  for concept in ['track_temperature','air_temperature','dew_point','humidity','pressure','air_density','wind_speed','gust','wind_direction','solar_geometry','shortwave_radiation','cloud_cover']:
   rows.append({'year':int(y),'evidence_layer':'LAST_CHANCE_COMPLETE_FADE','physical_variable':concept,'rows':len(g),'non_null_rows':0,'missing_rows':len(g),'coverage_pct':0.0})
 out=pd.DataFrame(rows).sort_values(['evidence_layer','year','physical_variable']); csv(out,'physical_variable_missingness_by_year_v1.csv'); return out

def main():
 start=hashes(); assert start==PROTECTED,start
 p1=pd.read_csv(ROOT/'r4/output/r4p1_attempt_four_lap_panel_v1.csv',dtype={'car_number':str})
 inv,cov,ffcan=fast_friday(p1); phys=physical_backbone(p1); first,fade=day1_tables(p1,phys,ffcan); lcfade,lcrep=last_chance_tables(); rep,extra=repeats(phys); team=teams(first); wait,waitrep=waits(); roles(); missing=physical_missingness(first,fade,rep,lcfade)
 qa=[]
 def q(name,val,exp,status=None): qa.append({'check':name,'value':val,'expected':exp,'status':status or ('PASS' if val==exp else 'FAIL')})
 q('protected hashes valid at start',start,PROTECTED); q('Day1 backbone rows',len(p1),329); q('Day1 complete fade rows',len(fade),260); q('Day1 first complete car-years',len(first),168); q('Day1 repeat transitions',len(rep),92); q('frozen membership rows',int(rep.in_frozen_39.sum()),39); q('PTSC-pair rows',int(truth(rep.ptsc_pair_available).sum()),40); q('39-vs-40 discrepancy rows',len(extra),1); q('Last Chance complete rows',len(lcfade),15); q('Last Chance chronology rows',len(lcrep),22); q('exact wait observations',int(wait.observed_wait_minutes.notna().sum()),0); q('bounded wait observations',int(wait.lower_wait_bound_minutes.notna().sum()),0)
 end=hashes(); q('protected hashes unchanged at end',end,start)
 qad=pd.DataFrame(qa); csv(qad,'r5_1_data_assembly_qa_v1.csv')
 report={'phase':'R5.1','status':'R5_1_PHYSICS_EVIDENCE_DATA_ASSEMBLY_PARTIAL','reasons':['only 17 existing Fast Friday qualifying-simulation four-lap candidate rows across evidence; other references are single-lap types','only 39 of 92 Day1 repeat transitions meet frozen full-environment criterion','Last Chance lacks exact timestamps for physical linkage','zero exact or bounded historical queue waits'],
 'counts':{'fast_friday_inventory_rows':len(inv),'fast_friday_four_lap_candidate_rows':int(inv.qualifying_simulation_indicator.astype(str).str.lower().eq('true').sum()),'fast_friday_four_lap_candidate_car_years':int(inv.loc[inv.qualifying_simulation_indicator.astype(str).str.lower().eq('true'),['year','car_number']].drop_duplicates().shape[0]),'fast_friday_coverage_by_year':cov.to_dict('records'),'day1_first_complete_runs':len(first),'day1_first_complete_by_year':first.groupby('year').size().to_dict(),'day1_complete_four_lap_fade_rows':len(fade),'day1_complete_fade_by_year':fade.groupby('year').size().to_dict(),'day1_same_car_repeat_transitions':len(rep),'day1_repeat_by_year':rep.groupby('year').size().to_dict(),'day1_frozen_39_membership':int(rep.in_frozen_39.sum()),'ptsc_pair_current_flag':int(truth(rep.ptsc_pair_available).sum()),'last_chance_complete_runs':len(lcfade),'last_chance_complete_by_year':lcfade.groupby('year').size().to_dict(),'last_chance_chronology_rows':len(lcrep),'last_chance_repeat_event_rows':int((~lcrep.repeat_opportunity_class.isin(['INITIAL_ATTEMPT','CHRONOLOGY_ONLY_OR_INITIAL'])).sum()),'last_chance_repeat_classes':lcrep.repeat_opportunity_class.value_counts().to_dict(),'team_year_rows':len(team),'team_year_groups':team.team_year_id.nunique(),'team_rows_with_own_fast_friday_reference':int(team.own_fast_friday_reference_available.astype(str).str.lower().eq('true').sum()),'historical_wait_inventory_rows':len(wait),'exact_wait_observations':0,'bounded_wait_observations':0,'related_attempt_intervals_not_wait':int(wait.related_attempt_interval_minutes.notna().sum()),'wait_evidence_by_regime':waitrep['by_regime'],'physical_missingness_rows':len(missing)},
 'reconciliation_39_vs_40':{'frozen_criterion':'full_environment_pair_available == true','broader_40_criterion':'ptsc_pair_available == true','extra_transition':extra.to_dict('records')},'protected_hashes_start':start,'protected_hashes_end':end,'models_fitted':False,'strategy_recommendations_created':False,'arbitrary_wait_grid_created':False}
 js(report,'r5_1_data_assembly_report_v1.json')
 files=sorted([ROOT/'r5_1/README.md',ROOT/'r5_1/run_r5_1_data_assembly_v1.py',ROOT/'r5_1/run_r5_1_qa_v1.py']+[p for p in OUT.iterdir() if p.is_file() and p.name!='r5_1_manifest_sha256.txt'])
 (OUT/'r5_1_manifest_sha256.txt').write_text(''.join(f'{h(p)}  {p.relative_to(ROOT)}\n' for p in files))
 print(json.dumps(report,indent=2,default=str))

if __name__=='__main__': main()
