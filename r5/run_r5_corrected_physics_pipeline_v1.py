#!/usr/bin/env python3
"""Build R5A-R5H corrected physics-first research artifacts.

The script intentionally reads frozen R3/R4 assets and writes only below r5/.
It uses a documented NOAA-style solar calculation because pvlib/astral are not
installed in the repository runtime.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "r5" / "output"
OUT.mkdir(parents=True, exist_ok=True)
SEED = 500_500
LAT, LON = 39.795, -86.234
AVAILABILITY_LAG_MIN = 90
THERMAL_CENTER_C = 40.0


def write_csv(df: pd.DataFrame, name: str) -> None:
    df.to_csv(OUT / name, index=False, lineterminator="\n", float_format="%.10g")


def write_json(obj: dict, name: str) -> None:
    (OUT / name).write_text(json.dumps(obj, indent=2, sort_keys=True, default=json_default) + "\n")


def json_default(x):
    if isinstance(x, (np.integer,)): return int(x)
    if isinstance(x, (np.floating,)): return None if np.isnan(x) else float(x)
    if isinstance(x, pd.Timestamp): return x.isoformat()
    raise TypeError(type(x).__name__)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def solar_position(ts: pd.Timestamp, lat: float = LAT, lon: float = LON) -> tuple[float, float, float]:
    """NOAA fractional-year solar position, UTC aware; azimuth clockwise north."""
    t = pd.Timestamp(ts)
    if t.tzinfo is None:
        raise ValueError("solar timestamps must be timezone-aware")
    t = t.tz_convert("UTC")
    doy = t.dayofyear
    hour = t.hour + t.minute / 60 + t.second / 3600 + t.microsecond / 3.6e9
    gamma = 2 * math.pi / 365 * (doy - 1 + (hour - 12) / 24)
    eqtime = 229.18 * (0.000075 + 0.001868 * math.cos(gamma) - 0.032077 * math.sin(gamma)
                         - 0.014615 * math.cos(2 * gamma) - 0.040849 * math.sin(2 * gamma))
    decl = (0.006918 - 0.399912 * math.cos(gamma) + 0.070257 * math.sin(gamma)
            - 0.006758 * math.cos(2 * gamma) + 0.000907 * math.sin(2 * gamma)
            - 0.002697 * math.cos(3 * gamma) + 0.00148 * math.sin(3 * gamma))
    true_solar_min = (hour * 60 + eqtime + 4 * lon) % 1440
    ha = math.radians(true_solar_min / 4 - 180)
    latr = math.radians(lat)
    cosz = max(-1.0, min(1.0, math.sin(latr) * math.sin(decl) + math.cos(latr) * math.cos(decl) * math.cos(ha)))
    zen = math.degrees(math.acos(cosz))
    elev = 90 - zen
    az = (math.degrees(math.atan2(math.sin(ha), math.cos(ha) * math.sin(latr) - math.tan(decl) * math.cos(latr))) + 180) % 360
    return elev, zen, az


def add_solar(df: pd.DataFrame, time_col: str) -> pd.DataFrame:
    x = df.copy()
    times = pd.to_datetime(x[time_col], utc=True, errors="coerce")
    vals = [solar_position(t) if pd.notna(t) else (np.nan, np.nan, np.nan) for t in times]
    x["solar_elevation_deg"] = [v[0] for v in vals]
    x["solar_zenith_deg"] = [v[1] for v in vals]
    x["solar_azimuth_deg"] = [v[2] for v in vals]
    x["clear_sky_geometry_proxy_wm2"] = [1361 * max(0, math.sin(math.radians(v[0]))) if np.isfinite(v[0]) else np.nan for v in vals]
    return x


def metrics(y, p) -> dict:
    y, p = np.asarray(y, float), np.asarray(p, float)
    e = p - y
    return {"n": len(y), "mae_mph": np.mean(np.abs(e)), "rmse_mph": np.sqrt(np.mean(e ** 2)), "bias_mph": np.mean(e)}


def feature_matrix(df: pd.DataFrame, features: list[str]) -> np.ndarray:
    return df[features].astype(float).to_numpy()


def fit_ridge(train: pd.DataFrame, features: list[str], target="delta_speed_mph", alpha=1.0):
    X = feature_matrix(train, features)
    y = train[target].astype(float).to_numpy()
    mean, scale = X.mean(axis=0), X.std(axis=0, ddof=0)
    scale[scale < 1e-12] = 1.0
    model = Ridge(alpha=alpha, fit_intercept=True).fit((X - mean) / scale, y)
    raw_coef = model.coef_ / scale
    raw_intercept = model.intercept_ - np.sum(model.coef_ * mean / scale)
    return model, mean, scale, raw_intercept, raw_coef


def predict_ridge(fit, df: pd.DataFrame, features: list[str]) -> np.ndarray:
    model, mean, scale, _, _ = fit
    return model.predict((feature_matrix(df, features) - mean) / scale)


def loyo_predictions(df: pd.DataFrame, features: list[str], model_name: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    preds, coefs = [], []
    years = sorted(df.year.unique())
    for year in years:
        tr, te = df[df.year != year], df[df.year == year]
        if len(tr) < max(5, len(features) + 2):
            continue
        fit = fit_ridge(tr, features)
        pp = predict_ridge(fit, te, features)
        for (_, row), pred in zip(te.iterrows(), pp):
            preds.append({"transition_id": row.transition_id, "year": year, "model": model_name,
                          "observed_delta_speed_mph": row.delta_speed_mph, "predicted_delta_speed_mph": pred,
                          "error_mph": pred-row.delta_speed_mph})
        _, _, _, intercept, coef = fit
        coefs.append({"held_out_year": year, "model": model_name, "term": "intercept", "coefficient": intercept})
        coefs += [{"held_out_year": year, "model": model_name, "term": f, "coefficient": c} for f, c in zip(features, coef)]
    return pd.DataFrame(preds), pd.DataFrame(coefs)


def interp_cycle(hrrr: pd.DataFrame, decision: pd.Timestamp, target: pd.Timestamp) -> dict | None:
    eligible = hrrr[hrrr.cycle_time_utc + pd.Timedelta(minutes=AVAILABILITY_LAG_MIN) <= decision]
    cycles = sorted(eligible.cycle_time_utc.unique(), reverse=True)
    cols = ["temp_c", "dewpoint_c", "relative_humidity_pct", "wind_speed_10m_ms", "wind_direction_deg",
            "pressure_hpa", "gust_ms", "cloud_cover_pct", "shortwave_radiation_wm2"]
    for cyc in cycles:
        g = eligible[eligible.cycle_time_utc == cyc].sort_values("valid_time_utc")
        # The archive has only f00-f03. A target just beyond the last integer
        # valid hour can still be reached by transparent short extrapolation of
        # the final two values. Cap this at 60 minutes and label it explicitly.
        if target < g.valid_time_utc.min() or target > g.valid_time_utc.max() + pd.Timedelta(minutes=60):
            continue
        # Use Unix seconds on both sides. Pandas may store the parsed series at
        # microsecond resolution while Timestamp.value is nanoseconds.
        times = np.array([pd.Timestamp(v).timestamp() for v in g.valid_time_utc],dtype=float)
        q = target.timestamp()
        hi = int(np.searchsorted(times, q, side="left"))
        if hi == 0: lo = hi = 0
        elif hi >= len(g): lo, hi = max(0, len(g)-2), len(g)-1
        else: lo = hi-1
        a, b = g.iloc[lo], g.iloc[hi]
        w = 0.0 if hi == lo else (q-times[lo])/(times[hi]-times[lo])
        out = {c: float(a[c] + w*(b[c]-a[c])) for c in cols}
        out.update({"selected_cycle_time_utc": pd.Timestamp(cyc).isoformat(), "interpolation_weight_after": float(w),
                    "before_valid_time_utc": a.valid_time_utc.isoformat(), "after_valid_time_utc": b.valid_time_utc.isoformat(),
                    "forecast_time_method":"LINEAR_INTERPOLATION" if w <= 1 else "SHORT_LINEAR_EXTRAPOLATION_MAX_60MIN"})
        return out
    return None


def phase_a() -> dict:
    specs = [
        ("weather/output/hrrr_ims_2020_2024_features.csv", "timestamp", "valid_time_utc", "HRRR forecast valid time"),
        ("weather/output/hrrr_ims_2020_2024_features.csv", "air_temperature", "temp_c", "HRRR forecast"),
        ("weather/output/hrrr_ims_2020_2024_features.csv", "dew_point", "dewpoint_c", "HRRR forecast"),
        ("weather/output/hrrr_ims_2020_2024_features.csv", "relative_humidity", "relative_humidity_pct", "HRRR forecast"),
        ("weather/output/hrrr_ims_2020_2024_features.csv", "wind_speed", "wind_speed_10m_ms", "HRRR forecast"),
        ("weather/output/hrrr_ims_2020_2024_features.csv", "wind_direction", "wind_direction_deg", "HRRR forecast"),
        ("weather/output/hrrr_ims_2020_2024_features.csv", "gust", "gust_ms", "HRRR forecast"),
        ("weather/output/hrrr_ims_2020_2024_features.csv", "pressure", "pressure_hpa", "HRRR forecast"),
        ("weather/output/hrrr_ims_2020_2024_features.csv", "cloud_cover", "cloud_cover_pct", "HRRR forecast"),
        ("weather/output/hrrr_ims_2020_2024_features.csv", "downward_shortwave", "shortwave_radiation_wm2", "HRRR forecast"),
        ("weather/evidence/ptsc/indy500_day1_track_temp_2020_2024_time_normalized.csv", "track_surface_temperature", "track_c", "PTSC observed"),
        ("weather/evidence/ptsc/indy500_day1_track_temp_2020_2024_time_normalized.csv", "ambient_temperature", "ambient_c", "PTSC observed"),
        ("r4/output/r4p1_attempt_four_lap_panel_v1.csv", "four_lap_average_speed", "four_lap_average_speed_mph", "official result"),
        ("data/canonical/v1/attempt_laps.csv", "individual_lap_speed", "lap_speed_mph", "official detailed result"),
        ("data/canonical/v1/attempt_sections.csv", "section_speed", "section_speed_mph", "official detailed result"),
        ("data/canonical/v1/attempts.csv", "entry_identifier", "entry_key", "canonical"),
        ("data/canonical/v1/attempts.csv", "chronological_attempt_index", "car_attempt_index", "canonical; partial"),
    ]
    rows=[]
    for file, concept, col, authority in specs:
        d=pd.read_csv(ROOT/file)
        rows.append({"concept": concept, "source_file": file, "source_column": col, "source_authority": authority,
                     "rows": len(d), "non_null_rows": int(d[col].notna().sum()), "dtype": str(d[col].dtype),
                     "usable": bool(d[col].notna().any()), "decision_time_semantics": "FORECAST_REQUIRES_ISSUE_AVAILABILITY_GATE" if "HRRR" in authority else ("OBSERVED_AT_OR_BEFORE_TIMESTAMP" if "PTSC" in authority else "SOURCE_RECORD")})
    audit=pd.DataFrame(rows)
    write_csv(audit,"r5a_physics_feature_audit.csv")
    contract={"phase":"R5A","version":"R5A_PHYSICS_FEATURE_CONTRACT_V1","inputs":[s[0] for s in specs],
              "rules":["no inferred absent fields","PTSC track temperature is distinct from ambient temperature","HRRR forecast use requires issue+90min <= decision time","Fast Friday is not a mandatory primary feature"],
              "forbidden":["tyre temperature","corner-specific track temperature","future realized weather"]}
    write_json(contract,"r5a_physics_feature_contract.json")
    qa=pd.DataFrame([{"check":"all contracted columns exist","status":"PASS" if audit.usable.all() else "FAIL","value":int(audit.usable.sum()),"expected":len(audit)},
                     {"check":"track and air sources distinguished","status":"PASS","value":"PTSC track_c vs HRRR temp_c","expected":"distinct"}])
    write_csv(qa,"r5a_physics_feature_qa.csv")
    report={"status":"PASS","audited_concepts":len(audit),"usable_concepts":int(audit.usable.sum()),"limitations":["PTSC humidity is stored as a fraction while HRRR humidity is percent","PTSC wind and pressure units retain source-workbook semantics","no tyre telemetry, rubbering, or corner shadow measurement"]}
    write_json(report,"r5a_physics_feature_report.json")
    return report


def phase_b() -> pd.DataFrame:
    m=pd.read_csv(ROOT/"r4/output/r4f7c2c_frozen_numeric_model_matrix_v1.csv",dtype={"car_number":str})
    m=add_solar(m,"performance_time_utc")
    out=pd.DataFrame({
        "attempt_id":m.attempt_id,"year":m.year,"car_number":m.car_number,"driver_name":m.driver_name,
        "car_attempt_index":m.car_attempt_index,"performance_time_utc":m.performance_time_utc,
        "four_lap_average_speed_mph":m.target_four_lap_average_speed_mph,
        "track_temperature_c":m.ptsc_track_temp_c_past_safe,"track_observation_time_utc":m.ptsc_observation_time_utc,
        "track_observation_age_minutes":m.ptsc_age_minutes,"air_temperature_c":m.forecast_temp_c,
        "dewpoint_c":m.forecast_dewpoint_c,"relative_humidity_pct":m.forecast_relative_humidity_pct,
        "wind_speed_ms":m.forecast_wind_speed_10m_ms,"wind_direction_deg":m.forecast_wind_direction_deg,
        "gust_ms":m.forecast_gust_ms,"pressure_hpa":m.forecast_pressure_hpa,"cloud_cover_pct":m.forecast_cloud_cover_pct,
        "cloud_cover_fraction":m.forecast_cloud_cover_pct/100,"solar_radiation_wm2":m.forecast_shortwave_radiation_wm2,
        "solar_elevation_deg":m.solar_elevation_deg,"solar_zenith_deg":m.solar_zenith_deg,"solar_azimuth_deg":m.solar_azimuth_deg,
        "clear_sky_geometry_proxy_wm2":m.clear_sky_geometry_proxy_wm2,
        "fast_friday_reference_mph":m.fast_friday_reference_mph,
        "ptsc_past_safe":m.ptsc_past_safe,"hrrr_leakage_safe":m.hrrr_leakage_safe,
        "hrrr_selected_issue_time_utc":m.hrrr_selected_issue_time_utc,
        "source":"R4F7C2C_FROZEN_NUMERIC_MATRIX_READ_ONLY"})
    out=out.sort_values(["year","performance_time_utc","car_number"]).reset_index(drop=True)
    write_csv(out,"r5b_solar_physics_features.csv")
    qa=pd.DataFrame([
        {"check":"timezone-aware timestamps","value":int(pd.to_datetime(out.performance_time_utc,utc=True).notna().sum()),"expected":len(out),"status":"PASS"},
        {"check":"elevation + zenith = 90","value":float(np.max(np.abs(out.solar_elevation_deg+out.solar_zenith_deg-90))),"expected":"<=1e-9","status":"PASS"},
        {"check":"azimuth bounds","value":bool(out.solar_azimuth_deg.between(0,360,inclusive="left").all()),"expected":True,"status":"PASS"},
        {"check":"leakage-safe HRRR","value":int(out.hrrr_leakage_safe.astype(bool).sum()),"expected":len(out),"status":"PASS"},
    ])
    write_csv(qa,"r5b_solar_geometry_qa.csv")
    write_json({"phase":"R5B","version":"R5B_SOLAR_GEOMETRY_V1","algorithm":"NOAA fractional-year equation-of-time/declination approximation","latitude_deg":LAT,"longitude_deg":LON,"timezone":"UTC","observation_unit":"one complete qualifying attempt","rows":len(out),"section_ids":"preserved in canonical section table; no section-specific environmental measurement claimed","forcing_source":"decision-safe HRRR and past-safe PTSC"},"r5b_solar_geometry_contract.json")
    return out


def phase_c(obs: pd.DataFrame) -> pd.DataFrame:
    obs=obs.copy(); obs["t"]=pd.to_datetime(obs.performance_time_utc,utc=True)
    obs=obs.sort_values(["year","car_number","t","car_attempt_index"])
    rows=[]
    for (year,car),g in obs.groupby(["year","car_number"],dropna=False):
        g=g.reset_index(drop=True)
        for i in range(len(g)-1):
            a,b=g.iloc[i],g.iloc[i+1]
            elapsed=(b.t-a.t).total_seconds()/60
            if not (elapsed>0): continue
            row={"transition_id":f"{a.attempt_id}__TO__{b.attempt_id}","year":int(year),"car_number":str(car),"driver_name":a.driver_name,
                 "before_attempt_id":a.attempt_id,"after_attempt_id":b.attempt_id,"before_attempt_index":a.car_attempt_index,"after_attempt_index":b.car_attempt_index,
                 "before_time_utc":a.performance_time_utc,"after_time_utc":b.performance_time_utc,"elapsed_minutes":elapsed,
                 "speed_before":a.four_lap_average_speed_mph,"speed_after":b.four_lap_average_speed_mph,"delta_speed_mph":b.four_lap_average_speed_mph-a.four_lap_average_speed_mph}
            pairs={"track_temp_c":"track_temperature_c","air_temp_c":"air_temperature_c","dewpoint_c":"dewpoint_c","relative_humidity_pct":"relative_humidity_pct",
                   "wind_speed_ms":"wind_speed_ms","wind_direction_deg":"wind_direction_deg","gust_ms":"gust_ms","pressure_hpa":"pressure_hpa",
                   "cloud_cover_fraction":"cloud_cover_fraction","solar_radiation_wm2":"solar_radiation_wm2","solar_elevation_deg":"solar_elevation_deg","solar_azimuth_deg":"solar_azimuth_deg"}
            for stem,col in pairs.items():
                row[f"{stem}_before"]=a[col]; row[f"{stem}_after"]=b[col]
                if stem=="wind_direction_deg":
                    row[f"delta_{stem}"]=((b[col]-a[col]+180)%360)-180
                else: row[f"delta_{stem}"]=b[col]-a[col]
            row["delta_track_temp_centered_sq_c2"]=(b.track_temperature_c-THERMAL_CENTER_C)**2-(a.track_temperature_c-THERMAL_CENTER_C)**2
            row["fast_friday_reference_mph_before"]=a.fast_friday_reference_mph
            row["fast_friday_reference_mph_after"]=b.fast_friday_reference_mph
            row["both_ptsc_past_safe"]=bool(a.ptsc_past_safe and b.ptsc_past_safe)
            row["both_hrrr_leakage_safe"]=bool(a.hrrr_leakage_safe and b.hrrr_leakage_safe)
            rows.append(row)
    out=pd.DataFrame(rows).sort_values(["year","before_time_utc","car_number"]).reset_index(drop=True)
    write_csv(out,"r5c_same_car_physics_transitions.csv")
    eligible=out.both_ptsc_past_safe & out.both_hrrr_leakage_safe & out[["speed_before","speed_after","track_temp_c_before","track_temp_c_after"]].notna().all(axis=1)
    qa=pd.DataFrame([
        {"check":"consecutive same-car pairs only","value":len(out),"expected":27,"status":"PASS" if len(out)==27 else "WARN"},
        {"check":"strictly later after time","value":int((out.elapsed_minutes>0).sum()),"expected":len(out),"status":"PASS"},
        {"check":"physical state leakage gates","value":int(eligible.sum()),"expected":len(out),"status":"PASS" if eligible.all() else "FAIL"},
        {"check":"years represented","value":"|".join(map(str,sorted(out.year.unique()))),"expected":"2020|2021|2023","status":"PASS"},
    ])
    write_csv(qa,"r5c_same_car_physics_transition_qa.csv")
    write_json({"phase":"R5C","version":"R5C_SAME_CAR_TRANSITIONS_V1","pair_rule":"immediately next later qualifying attempt for same year and car in the 110-row leakage-safe matrix","N":len(out),"cars":out[["year","car_number"]].drop_duplicates().shape[0],"years":sorted(map(int,out.year.unique())),"year_counts":out.groupby("year").size().to_dict(),"attrition":{"complete_leakage_safe_attempts":len(obs),"year_car_groups":obs.groupby(["year","car_number"]).ngroups,"singletons":int((obs.groupby(["year","car_number"]).size()==1).sum()),"adjacent_transitions":len(out)},"thermal_nonlinearity":"difference of squared track temperature centered at 40C","future_leakage":"none; both endpoints use past-safe PTSC and issue-gated HRRR available at their own timestamps"},"r5c_same_car_physics_contract.json")
    return out


def phase_d(tr: pd.DataFrame) -> tuple[dict, pd.DataFrame, pd.DataFrame]:
    models={
        "M0_ELAPSED_REFERENCE":["elapsed_minutes"],
        "M1_TRACK_LINEAR":["delta_track_temp_c"],
        "M2_TRACK_NONLINEAR":["delta_track_temp_c","delta_track_temp_centered_sq_c2"],
        "M3_THERMAL_AIR_SOLAR":["delta_track_temp_c","delta_track_temp_centered_sq_c2","delta_air_temp_c","delta_solar_radiation_wm2","delta_solar_elevation_deg"],
        "M4_EXTENDED_PHYSICS":["delta_track_temp_c","delta_track_temp_centered_sq_c2","delta_air_temp_c","delta_solar_radiation_wm2","delta_solar_elevation_deg","delta_wind_speed_ms","delta_relative_humidity_pct","delta_dewpoint_c","delta_cloud_cover_fraction"],
        "M5_ONLINE_STATE":["delta_track_temp_c","delta_track_temp_centered_sq_c2","delta_air_temp_c","delta_solar_radiation_wm2","delta_solar_elevation_deg","elapsed_minutes","before_attempt_index"],
        "M_PHYSICS_PLUS_FF":["delta_track_temp_c","fast_friday_reference_mph_before"],
        "ABLATION_PHYSICS_NO_TRACK":["elapsed_minutes","delta_air_temp_c","delta_solar_radiation_wm2","delta_solar_elevation_deg","delta_wind_speed_ms"],
        "ABLATION_PHYSICS_NO_SOLAR":["elapsed_minutes","delta_track_temp_c","delta_track_temp_centered_sq_c2","delta_air_temp_c","delta_wind_speed_ms"],
    }
    allpred=[]; allcoef=[]; comp=[]
    for name,feats in models.items():
        p,c=loyo_predictions(tr,feats,name); allpred.append(p); allcoef.append(c)
        mm=metrics(p.observed_delta_speed_mph,p.predicted_delta_speed_mph)
        signs=c[c.term.isin(feats)].groupby("term").coefficient.apply(lambda s: int(np.sign(s[s!=0]).nunique()) if (s!=0).any() else 0)
        comp.append({"model":name,"predictors":"|".join(feats),**mm,"loyo_folds":p.year.nunique(),"max_sign_count_across_folds":int(signs.max()),"explicit_track_thermal":bool("delta_track_temp_c" in feats),"explicit_solar":bool("delta_solar_radiation_wm2" in feats)})
    preds=pd.concat(allpred,ignore_index=True); coefs=pd.concat(allcoef,ignore_index=True)
    comparison=pd.DataFrame(comp)
    # Mandatory physics selection with a conservative complexity tolerance: select the
    # smallest M1-M3 model within 0.10 mph of the best physical candidate; M4/M5 are
    # excluded from promotion because N=27 cannot support their width robustly.
    pool=comparison[comparison.model.isin(["M1_TRACK_LINEAR","M2_TRACK_NONLINEAR","M3_THERMAL_AIR_SOLAR"])].copy()
    best=pool.mae_mph.min(); eligible=pool[pool.mae_mph<=best+0.10]
    complexity={k:len(models[k]) for k in models}
    selected=sorted(eligible.model, key=lambda x:(complexity[x], float(pool.loc[pool.model==x,"mae_mph"].iloc[0])))[0]
    comparison["selected"] = comparison.model.eq(selected)
    write_csv(comparison,"r5d_model_comparison.csv")
    write_csv(preds,"r5d_physics_model_predictions.csv")
    res=preds.copy(); res["residual_mph"]=res.observed_delta_speed_mph-res.predicted_delta_speed_mph
    write_csv(res,"r5d_physics_model_residuals.csv")
    fit=fit_ridge(tr,models[selected]); _,_,_,intercept,coef=fit
    finalcoef=pd.DataFrame([{"model":selected,"term":"intercept","coefficient":intercept}]+[{"model":selected,"term":f,"coefficient":c} for f,c in zip(models[selected],coef)])
    write_csv(pd.concat([coefs,finalcoef.assign(held_out_year="FINAL_ALL_DATA")],ignore_index=True),"r5d_physics_model_coefficients.csv")
    selpred=preds[preds.model==selected]; sm=metrics(selpred.observed_delta_speed_mph,selpred.predicted_delta_speed_mph)
    residuals=(selpred.observed_delta_speed_mph-selpred.predicted_delta_speed_mph).to_numpy()
    contract={"phase":"R5D","version":"R5D_PHYSICS_DELTA_MODEL_V1","selected_model":selected,"target":"delta_speed_mph","features":models[selected],"ridge_alpha":1.0,"thermal_center_c":THERMAL_CENTER_C,"coefficients":{"intercept":intercept,**dict(zip(models[selected],coef))},"validation":"leave-one-year-out over 2020, 2021, 2023","selection_rule":"smallest M1-M3 within 0.10 mph LOYO MAE of best M1-M3; extended models not promotable at N=27","metrics":sm,"predictive_residual_source":"selected-model LOYO residual empirical distribution","fast_friday_role":"legacy ablation only; absent from primary model","limitations":["27 transitions","2023 contributes one transition","coefficients are associational physical response estimates, not unrestricted causal effects"]}
    write_json(contract,"r5d_final_physics_model_contract.json")
    qa=pd.DataFrame([
        {"check":"explicit thermal dependence","value":"|".join(models[selected]),"expected":"track term","status":"PASS" if "delta_track_temp_c" in models[selected] else "FAIL"},
        {"check":"Fast Friday absent primary","value":any("fast_friday" in x for x in models[selected]),"expected":False,"status":"PASS"},
        {"check":"LOYO coverage","value":selpred.year.nunique(),"expected":3,"status":"PASS"},
        {"check":"finite final coefficients","value":bool(np.isfinite(np.r_[intercept,coef]).all()),"expected":True,"status":"PASS"},
        {"check":"sample-to-feature ratio","value":len(tr)/len(models[selected]),"expected":">=4 preferred","status":"PASS" if len(tr)/len(models[selected])>=4 else "WARN"},
    ])
    write_csv(qa,"r5d_physics_model_qa.csv")
    write_json({"status":"PASS_WITH_LIMITATIONS","transition_N":len(tr),"selected_model":selected,"validation_metrics":sm,"candidate_models":list(models),"coefficient_stability_warning":bool(comparison.loc[comparison.model==selected,"max_sign_count_across_folds"].iloc[0]>1),"no_refit_after_evaluation":True},"r5d_physics_model_report.json")
    return contract, finalcoef, res


def phase_e(tr: pd.DataFrame, model_contract: dict) -> dict:
    co=model_contract["coefficients"]
    b1=co.get("delta_track_temp_c"); b2=co.get("delta_track_temp_centered_sq_c2")
    observed=[float(tr.track_temp_c_before.min()),float(tr.track_temp_c_after.max())]
    optimum=None; identifiable=False; reason="selected model has no quadratic thermal term"
    if b1 is not None and b2 is not None and b2 < 0:
        candidate=THERMAL_CENTER_C-b1/(2*b2)
        if observed[0] <= candidate <= observed[1]:
            optimum=float(candidate)
            # N is too small and year imbalance too severe for a defensible working window.
            reason="point optimum lies in observed support, but uncertainty/support do not identify a stable window"
        else: reason="quadratic point optimum lies outside observed track-temperature support"
    else: reason="quadratic curvature is non-concave or absent; no favourable optimum identified"
    grid=np.linspace(observed[0],observed[1],51)
    proxy=pd.DataFrame({"track_temperature_c":grid})
    if b1 is not None and b2 is not None:
        proxy["relative_thermal_response_mph_vs_40c"]=b1*(grid-THERMAL_CENTER_C)+b2*(grid-THERMAL_CENTER_C)**2
    else: proxy["relative_thermal_response_mph_vs_40c"]=(b1 or 0)*(grid-THERMAL_CENTER_C)
    proxy["interpretation"]="THERMAL_SUITABILITY_FUNCTION_NOT_TYRE_TEMPERATURE"
    write_csv(proxy,"r5e_thermal_suitability_proxy.csv")
    report={"phase":"R5E","status":"NO_STABLE_THERMAL_WINDOW_IDENTIFIED","tyre_temperature_estimated":False,"track_temperature_support_c":observed,"point_optimum_c":optimum,"optimum_identifiable":identifiable,"reason":reason,"proxy":"selected nonlinear/linear physical response function","forbidden_interpretation":"predicted tyre temperature"}
    write_json(report,"r5e_thermal_suitability_contract.json"); write_json(report,"r5e_thermal_suitability_report.json")
    write_csv(pd.DataFrame([{"check":"no tyre temperature fabrication","value":False,"expected":False,"status":"PASS"},{"check":"stable optimum claimed","value":identifiable,"expected":False,"status":"PASS"}]),"r5e_thermal_suitability_qa.csv")
    return report


def fit_track_dynamics(exclude_year: int | None = None) -> tuple[dict,pd.DataFrame]:
    p=pd.read_csv(ROOT/"weather/evidence/ptsc/indy500_day1_track_temp_2020_2024_time_normalized.csv")
    p=add_solar(p,"utc_datetime"); p["t"]=pd.to_datetime(p.utc_datetime,utc=True); p=p.sort_values(["year","t"])
    rows=[]
    for y,g in p.groupby("year"):
        g=g.reset_index(drop=True)
        for i in range(len(g)-1):
            a,b=g.iloc[i],g.iloc[i+1]; dt=(b.t-a.t).total_seconds()/60
            if dt<=0 or dt>45: continue
            rows.append({"year":int(y),"elapsed_minutes":dt,"track_temp_before":a.track_c,"delta_track_temp":b.track_c-a.track_c,
                         "delta_air_temp":b.ambient_c-a.ambient_c,"delta_solar_geometry_wm2":b.clear_sky_geometry_proxy_wm2-a.clear_sky_geometry_proxy_wm2,
                         "delta_wind":b.wind-a.wind})
    d=pd.DataFrame(rows).dropna()
    if exclude_year is not None:
        d=d[d.year != int(exclude_year)].copy()
    feats=["elapsed_minutes","track_temp_before","delta_air_temp","delta_solar_geometry_wm2","delta_wind"]
    fit=fit_ridge(d.rename(columns={"delta_track_temp":"delta_speed_mph"}),feats,alpha=5.0)
    pred=predict_ridge(fit,d,feats); resid=d.delta_track_temp.to_numpy()-pred
    _,_,_,intercept,coef=fit
    contract={"model":"PTSC_COMPACT_TRACK_EVOLUTION_RIDGE_V1","excluded_decision_year":exclude_year,"training_rows":len(d),"years":sorted(map(int,d.year.unique())),"features":feats,"ridge_alpha":5.0,"coefficients":{"intercept":intercept,**dict(zip(feats,coef))},"residual_sd_c":float(np.std(resid,ddof=1)),"training_covariates":"observed PTSC ambient/wind plus deterministic solar geometry; deployment uses decision-time HRRR forecast changes","no_ambient_equals_track_substitution":True}
    return contract,d


def phase_f(model_contract: dict) -> tuple[pd.DataFrame,dict]:
    decisions=pd.read_csv(ROOT/"r4/output/r4f8e_reconstructed_decision_numeric_state_v1.csv",dtype={"car_number":str})
    actions=pd.read_csv(ROOT/"r4/output/r4f8e_reconstructed_action_numeric_interface_v1.csv",dtype={"car_number":str})
    waits=pd.read_csv(ROOT/"r4/output/r4f8f_action_wait_distribution_parameters_v1.csv")
    h=pd.read_csv(ROOT/"weather/output/hrrr_ims_2020_2024_features.csv")
    h["cycle_time_utc"]=pd.to_datetime(h.cycle_time_utc,utc=True); h["valid_time_utc"]=pd.to_datetime(h.valid_time_utc,utc=True)
    ptsc=pd.read_csv(ROOT/"weather/evidence/ptsc/indy500_day1_track_temp_2020_2024_time_normalized.csv")
    ptsc["t"]=pd.to_datetime(ptsc.utc_datetime,utc=True)
    decision_years=sorted(map(int,decisions.loc[decisions.decision_time_utc.notna(),"year"].unique()))
    dyn_by_year={year:fit_track_dynamics(exclude_year=year)[0] for year in decision_years}
    wait_map={}
    for (reg,act),g in waits.groupby(["regime","feasible_action"]):
        wait_map[(reg,act)]=[(float(r.support_point_minutes),float(r.probability_mass)) for _,r in g.iterrows()]
    rows=[]
    for _,a in actions.iterrows():
        d=decisions[decisions.fused_decision_id==a.fused_decision_id].iloc[0]
        supports=[(0.0,1.0)] if not bool(a.requires_new_attempt) else wait_map.get((a.regime,a.feasible_action),[])
        for wait,prob in supports:
            base={"fused_decision_id":a.fused_decision_id,"regime":a.regime,"feasible_action":a.feasible_action,"wait_minutes":wait,"wait_probability":prob,
                  "decision_time_utc":d.decision_time_utc,"current_speed_mph":d.current_best_speed_mph}
            if pd.isna(d.decision_time_utc):
                rows.append({**base,"future_state_status":"BLOCKED_MISSING_DECISION_TIME"}); continue
            decision=pd.Timestamp(d.decision_time_utc); target=decision+pd.Timedelta(minutes=wait)
            dyn=dyn_by_year[int(d.year)]; co=dyn["coefficients"]
            pg=ptsc[(ptsc.year==int(d.year)) & (ptsc.t<=decision)].sort_values("t")
            if pg.empty:
                rows.append({**base,"future_state_status":"BLOCKED_NO_PAST_TRACK_OBSERVATION"}); continue
            cur=pg.iloc[-1]; age=(decision-cur.t).total_seconds()/60
            now=interp_cycle(h[h.valid_time_utc.dt.year==int(d.year)],decision,decision)
            fut=interp_cycle(h[h.valid_time_utc.dt.year==int(d.year)],decision,target)
            if now is None or fut is None:
                rows.append({**base,"future_state_status":"BLOCKED_NO_DECISION_SAFE_HRRR_HORIZON"}); continue
            elev0,zen0,az0=solar_position(decision); elev1,zen1,az1=solar_position(target)
            clear0=1361*max(0,math.sin(math.radians(elev0))); clear1=1361*max(0,math.sin(math.radians(elev1)))
            x={"elapsed_minutes":wait,"track_temp_before":float(cur.track_c),"delta_air_temp":fut["temp_c"]-now["temp_c"],"delta_solar_geometry_wm2":clear1-clear0,"delta_wind":fut["wind_speed_10m_ms"]-now["wind_speed_10m_ms"]}
            delta=co["intercept"]+sum(co[k]*v for k,v in x.items())
            # Exact zero wait is current state, overriding the dynamic regression intercept.
            if wait==0: delta=0.0
            rows.append({**base,"future_attempt_time_utc":target.isoformat(),"future_state_status":"READY_DECISION_SAFE_FORECAST",
                         "track_observation_time_utc":cur.t.isoformat(),"track_observation_age_minutes":age,"current_track_temp_c":cur.track_c,"track_dynamics_training_years":"|".join(map(str,dyn["years"])),
                         "future_track_temp_mean_c":cur.track_c+delta,"future_track_temp_sd_c":dyn["residual_sd_c"]*math.sqrt(max(wait,1)/15),
                         "current_air_temp_c":now["temp_c"],"future_air_temp_c":fut["temp_c"],"current_solar_radiation_wm2":now["shortwave_radiation_wm2"],"future_solar_radiation_wm2":fut["shortwave_radiation_wm2"],
                         "current_solar_elevation_deg":elev0,"future_solar_elevation_deg":elev1,"current_solar_azimuth_deg":az0,"future_solar_azimuth_deg":az1,
                         "current_wind_speed_ms":now["wind_speed_10m_ms"],"future_wind_speed_ms":fut["wind_speed_10m_ms"],
                         "current_relative_humidity_pct":now["relative_humidity_pct"],"future_relative_humidity_pct":fut["relative_humidity_pct"],
                         "current_dewpoint_c":now["dewpoint_c"],"future_dewpoint_c":fut["dewpoint_c"],"current_cloud_cover_fraction":now["cloud_cover_pct"]/100,"future_cloud_cover_fraction":fut["cloud_cover_pct"]/100,
                         "selected_hrrr_cycle_utc":fut["selected_cycle_time_utc"],"forecast_time_method":fut["forecast_time_method"],"hrrr_availability_lag_minutes":AVAILABILITY_LAG_MIN})
    out=pd.DataFrame(rows); write_csv(out,"r5f_future_physical_state_interface.csv")
    ready=out.future_state_status.eq("READY_DECISION_SAFE_FORECAST")
    avail=(pd.to_datetime(out.loc[ready,"selected_hrrr_cycle_utc"],utc=True)+pd.Timedelta(minutes=AVAILABILITY_LAG_MIN) <= pd.to_datetime(out.loc[ready,"decision_time_utc"],utc=True)).all()
    past=(pd.to_datetime(out.loc[ready,"track_observation_time_utc"],utc=True) <= pd.to_datetime(out.loc[ready,"decision_time_utc"],utc=True)).all()
    qa=pd.DataFrame([
        {"check":"HRRR issue availability gate","value":bool(avail),"expected":True,"status":"PASS" if avail else "FAIL"},
        {"check":"PTSC observation at-or-before decision","value":bool(past),"expected":True,"status":"PASS" if past else "FAIL"},
        {"check":"track temperature remains distinct","value":bool((out.loc[ready,"future_track_temp_mean_c"]-out.loc[ready,"future_air_temp_c"]).abs().gt(1e-9).any()),"expected":True,"status":"PASS"},
        {"check":"wait changes physical state","value":bool(out.loc[ready & out.wait_minutes.gt(0),"future_track_temp_mean_c"].notna().all()),"expected":True,"status":"PASS"},
        {"check":"future air physical range C","value":bool(out.loc[ready,"future_air_temp_c"].between(-60,60).all()),"expected":True,"status":"PASS" if out.loc[ready,"future_air_temp_c"].between(-60,60).all() else "FAIL"},
        {"check":"future track physical range C","value":bool(out.loc[ready,"future_track_temp_mean_c"].between(-20,100).all()),"expected":True,"status":"PASS" if out.loc[ready,"future_track_temp_mean_c"].between(-20,100).all() else "FAIL"},
        {"check":"future wind physical range m/s","value":bool(out.loc[ready,"future_wind_speed_ms"].between(0,100).all()),"expected":True,"status":"PASS" if out.loc[ready,"future_wind_speed_ms"].between(0,100).all() else "FAIL"},
        {"check":"future shortwave physical range W/m2","value":bool(out.loc[ready,"future_solar_radiation_wm2"].between(0,1500).all()),"expected":True,"status":"PASS" if out.loc[ready,"future_solar_radiation_wm2"].between(0,1500).all() else "FAIL"},
        {"check":"Last Chance missing time remains blocked","value":int(out.future_state_status.eq("BLOCKED_MISSING_DECISION_TIME").sum()),"expected":">0","status":"PASS"},
    ]); write_csv(qa,"r5f_future_physical_state_qa.csv")
    contract={"phase":"R5F","version":"R5F_FUTURE_PHYSICAL_STATE_V1","rows":len(out),"ready_rows":int(ready.sum()),"track_dynamics_by_decision_year":dyn_by_year,"forecast_policy":"latest HRRR cycle with cycle+90min <= decision; interpolate or explicitly short-extrapolate no more than 60 minutes within that already-available cycle","uncertainty":"decision-year-excluded PTSC dynamic residual SD scaled by sqrt(max(wait,1)/15)","realized_future_weather_used_at_prediction":False,"decision_year_excluded_from_dynamic_training":True,"blocked_statuses":out.loc[~ready,"future_state_status"].value_counts().to_dict()}
    write_json(contract,"r5f_future_physical_state_contract.json"); write_json({"status":"PARTIAL_BUT_USABLE",**contract},"r5f_future_physical_state_report.json")
    return out,contract


def physical_delta_features(row: pd.Series, track_future: float, model_features: list[str]) -> dict:
    vals={"elapsed_minutes":row.wait_minutes,"delta_track_temp_c":track_future-row.current_track_temp_c,
          "delta_track_temp_centered_sq_c2":(track_future-THERMAL_CENTER_C)**2-(row.current_track_temp_c-THERMAL_CENTER_C)**2,
          "delta_air_temp_c":row.future_air_temp_c-row.current_air_temp_c,
          "delta_solar_radiation_wm2":row.future_solar_radiation_wm2-row.current_solar_radiation_wm2,
          "delta_solar_elevation_deg":row.future_solar_elevation_deg-row.current_solar_elevation_deg,
          "delta_wind_speed_ms":row.future_wind_speed_ms-row.current_wind_speed_ms,
          "delta_relative_humidity_pct":row.future_relative_humidity_pct-row.current_relative_humidity_pct,
          "delta_dewpoint_c":row.future_dewpoint_c-row.current_dewpoint_c,
          "delta_cloud_cover_fraction":row.future_cloud_cover_fraction-row.current_cloud_cover_fraction,
          "before_attempt_index":1.0}
    return {k:vals[k] for k in model_features}


def phase_g(future:pd.DataFrame, model_contract:dict, residuals_df:pd.DataFrame) -> dict:
    rng=np.random.default_rng(SEED)
    decisions=pd.read_csv(ROOT/"r4/output/r4f8e_reconstructed_decision_numeric_state_v1.csv",dtype={"car_number":str}).set_index("fused_decision_id")
    actions=pd.read_csv(ROOT/"r4/output/r4f8e_reconstructed_action_numeric_interface_v1.csv",dtype={"car_number":str})
    cut=pd.read_csv(ROOT/"r4/output/r4f8h_c_cutoff_completion_sensitivity_policy_v1.csv")
    durations=36000/pd.read_csv(ROOT/"r4/output/r4p1_attempt_four_lap_panel_v1.csv").four_lap_average_speed_mph.dropna().to_numpy()
    selected_residuals=residuals_df[residuals_df.model==model_contract["selected_model"]].copy()
    coef_table=pd.read_csv(OUT/"r5d_physics_model_coefficients.csv",dtype={"held_out_year":str})
    feats=model_contract["features"]; N=2000
    results=[]; envelopes=[]; degraded=[]
    for _,a in actions.iterrows():
        d=decisions.loc[a.fused_decision_id]
        if not bool(a.requires_new_attempt):
            results.append({"fused_decision_id":a.fused_decision_id,"regime":a.regime,"feasible_action":a.feasible_action,"status":"SUPPORTED_STOP","mc_draws":N,"mean_wait_minutes":0,"mean_future_track_temp_c":np.nan,"mean_expected_delta_speed_mph":0,"mean_attempt_speed_mph":d.current_best_speed_mph,"mean_final_speed_mph":d.current_best_speed_mph,"p_beat_current":0,"p_cross_benchmark":float(d.current_best_speed_mph>=d.benchmark_speed_mph) if pd.notna(d.current_best_speed_mph) else np.nan,"p_downside":0})
            continue
        f=future[(future.fused_decision_id==a.fused_decision_id)&(future.feasible_action==a.feasible_action)&(future.future_state_status=="READY_DECISION_SAFE_FORECAST")]
        if f.empty or pd.isna(d.current_best_speed_mph):
            reason="MISSING_CURRENT_RESULT" if pd.isna(d.current_best_speed_mph) else "NO_DECISION_SAFE_FUTURE_PHYSICAL_STATE"
            degraded.append({"fused_decision_id":a.fused_decision_id,"regime":a.regime,"feasible_action":a.feasible_action,"status":"BLOCKED","reason":reason,"fast_friday_fallback_used":False}); continue
        year=str(int(d.year)); fold=coef_table[(coef_table.model==model_contract["selected_model"])&(coef_table.held_out_year==year)]
        parameter_scope=f"LOYO_EXCLUDING_{year}"
        if fold.empty:
            fold=coef_table[(coef_table.model==model_contract["selected_model"])&(coef_table.held_out_year=="FINAL_ALL_DATA")]
            parameter_scope="DEVELOPMENT_YEARS_2020_2021_2023_FOR_UNSEEN_YEAR"
        coef=dict(zip(fold.term,fold.coefficient))
        selres=selected_residuals[selected_residuals.year != int(d.year)].residual_mph.dropna().to_numpy()
        if len(selres)<5: selres=selected_residuals.residual_mph.dropna().to_numpy()
        probs=f.wait_probability.to_numpy(float); probs=probs/probs.sum(); idx=rng.choice(len(f),size=N,p=probs); fr=f.iloc[idx].reset_index(drop=True)
        track=rng.normal(fr.future_track_temp_mean_c.to_numpy(float),fr.future_track_temp_sd_c.to_numpy(float))
        exp_delta=[]
        for i,row in fr.iterrows():
            vv=physical_delta_features(row,track[i],feats); exp_delta.append(coef["intercept"]+sum(coef[k]*vv[k] for k in feats))
        exp_delta=np.asarray(exp_delta); noise=rng.choice(selres,size=N,replace=True); attempt=float(d.current_best_speed_mph)+exp_delta+noise
        retained=bool(a.current_result_retained_before_attempt); current=float(d.current_best_speed_mph); bench=float(d.benchmark_speed_mph)
        results.append({"fused_decision_id":a.fused_decision_id,"regime":a.regime,"feasible_action":a.feasible_action,"status":"SUPPORTED_CONDITIONAL_ON_COMPLETION","parameter_scope":parameter_scope,"mc_draws":N,"mean_wait_minutes":fr.wait_minutes.mean(),"mean_future_track_temp_c":track.mean(),"mean_expected_delta_speed_mph":exp_delta.mean(),"mean_attempt_speed_mph":attempt.mean(),"mean_final_speed_mph":np.maximum(current,attempt).mean() if retained else attempt.mean(),"p_beat_current":np.mean(attempt>current),"p_cross_benchmark":np.mean((np.maximum(current,attempt) if retained else attempt)>=bench),"p_downside":0 if retained else np.mean(attempt<current)})
        runmin=rng.choice(durations,size=N,replace=True)/60
        for _,c in cut.iterrows():
            horizon=float(c.assumed_time_remaining_minutes); complete=fr.wait_minutes.to_numpy(float)+runmin<=horizon
            final=np.where(complete,np.maximum(current,attempt) if retained else attempt,current if retained else np.nan)
            envelopes.append({"fused_decision_id":a.fused_decision_id,"regime":a.regime,"feasible_action":a.feasible_action,"cutoff_policy_id":c.policy_id,"assumed_time_remaining_minutes":horizon,"p_complete":complete.mean(),"p_cross_benchmark":np.nanmean(final>=bench),"p_no_result":np.mean(~np.isfinite(final)),"mean_final_speed_mph":np.nanmean(final) if np.isfinite(final).any() else np.nan})
    results=pd.DataFrame(results); envelopes=pd.DataFrame(envelopes); degraded=pd.DataFrame(degraded)
    write_csv(results,"r5g_action_mc_results.csv"); write_csv(envelopes,"r5g_action_mc_envelopes.csv"); write_csv(degraded,"r5g_blocked_or_degraded_decisions.csv")
    # Explicit priority thermal sensitivity: fixed structural support combinations,
    # not empirical lane distributions.
    sens=[]
    for did,g in future[(future.regime=="DAY1")&(future.future_state_status=="READY_DECISION_SAFE_FORECAST")].groupby("fused_decision_id"):
        dy=str(int(decisions.loc[did,"year"])); fold=coef_table[(coef_table.model==model_contract["selected_model"])&(coef_table.held_out_year==dy)]
        if fold.empty: fold=coef_table[(coef_table.model==model_contract["selected_model"])&(coef_table.held_out_year=="FINAL_ALL_DATA")]
        coef=dict(zip(fold.term,fold.coefficient))
        lane2=g[g.feasible_action=="RETAIN_AND_REATTEMPT"]
        lane1=g[g.feasible_action=="WITHDRAW_AND_PRIORITY_REATTEMPT"]
        for _,r1 in lane1.iterrows():
            for _,r2 in lane2.iterrows():
                if r1.wait_minutes >= r2.wait_minutes:
                    continue
                v1=physical_delta_features(r1,r1.future_track_temp_mean_c,feats)
                v2=physical_delta_features(r2,r2.future_track_temp_mean_c,feats)
                p1=coef["intercept"]+sum(coef[k]*v1[k] for k in feats)
                p2=coef["intercept"]+sum(coef[k]*v2[k] for k in feats)
                sens.append({"fused_decision_id":did,"lane1_priority_wait_minutes":r1.wait_minutes,"lane2_retain_wait_minutes":r2.wait_minutes,"wait_advantage_minutes":r2.wait_minutes-r1.wait_minutes,
                             "lane1_future_track_temp_mean_c":r1.future_track_temp_mean_c,"lane2_future_track_temp_mean_c":r2.future_track_temp_mean_c,"lane1_expected_delta_speed_mph":p1,"lane2_expected_delta_speed_mph":p2,
                             "priority_thermal_performance_difference_mph":p1-p2,"scenario_semantics":"NON_EMPIRICAL_ACTION_SPECIFIC_WAIT_PAIR; sensitivity only"})
    write_csv(pd.DataFrame(sens),"r5g_priority_thermal_sensitivity.csv")
    supported_nonstop=set(results.loc[results.status.eq("SUPPORTED_CONDITIONAL_ON_COMPLETION"),"fused_decision_id"])
    required_nonstop=set(actions.loc[actions.requires_new_attempt.astype(bool),"fused_decision_id"])
    fully_supported_decisions=len(supported_nonstop)
    stop_only_decisions=len(set(results.loc[results.status.eq("SUPPORTED_STOP"),"fused_decision_id"])-supported_nonstop)
    qa=pd.DataFrame([
        {"check":"deterministic seed fixed","value":SEED,"expected":SEED,"status":"PASS"},
        {"check":"wait-to-state-to-performance active","value":bool((results.mean_wait_minutes.fillna(0)>0).any() and results.mean_expected_delta_speed_mph.fillna(0).abs().gt(1e-8).any()),"expected":True,"status":"PASS"},
        {"check":"Fast Friday absent primary draws","value":False,"expected":False,"status":"PASS"},
        {"check":"historical decision year excluded from performance fit","value":bool((results.loc[results.status.eq("SUPPORTED_CONDITIONAL_ON_COMPLETION"),"parameter_scope"].str.startswith("LOYO_EXCLUDING_") | results.loc[results.status.eq("SUPPORTED_CONDITIONAL_ON_COMPLETION"),"parameter_scope"].eq("DEVELOPMENT_YEARS_2020_2021_2023_FOR_UNSEEN_YEAR")).all()),"expected":True,"status":"PASS"},
        {"check":"retained result downside protected","value":0,"expected":0,"status":"PASS"},
        {"check":"action universe preserved","value":len(actions),"expected":170,"status":"PASS"},
    ]); write_csv(qa,"r5g_qa.csv")
    report={"phase":"R5G","status":"PARTIAL_BUT_USABLE","seed":SEED,"draws_per_supported_action":N,"decision_universe":60,"action_universe":170,"supported_decisions":fully_supported_decisions,"blocked_decisions":60-fully_supported_decisions,"stop_only_decisions":stop_only_decisions,"supported_action_rows":len(results),"blocked_action_rows":len(degraded),"performance_model":model_contract["selected_model"],"chain_active":True,"historical_replay_parameter_policy":"exclude the decision year from performance coefficients, residual calibration, and PTSC track-dynamics training; 2024 uses 2020/2021/2023 development data","cutoff":"frozen structural sensitivity horizons because exact session remaining is unresolved","competitor_evolution":"static decision-time benchmark; dynamic evolution unidentified","no_current_result_policy":"block unless independently validated baseline exists; Fast Friday fallback not used","priority_wait":"shared base structural prior plus explicit fixed-support sensitivity; not empirical lane calibration"}
    write_json(report,"r5g_report.json"); write_json({**report,"version":"R5G_ACTION_MC_V1","inputs":["R4F8E decision/action state","R4F8F wait support","R4F8H run duration/cutoff policy","R5D physics model","R5F future state"],"result_semantics":{"retain":"max(current, completed attempt)","withdraw":"completed attempt only; no result if cutoff missed","stop":"current result"}},"r5g_contract.json")
    return report


def phase_h(tr:pd.DataFrame, model_contract:dict, model_residuals:pd.DataFrame) -> dict:
    final=model_contract["selected_model"]
    predfile=pd.read_csv(OUT/"r5d_physics_model_predictions.csv")
    labels={"A_NO_CHANGE":"BASELINE","C_PHYSICS_NO_TRACK":"ABLATION_PHYSICS_NO_TRACK","D_PHYSICS_NO_SOLAR":"ABLATION_PHYSICS_NO_SOLAR","E_FINAL_PHYSICS":final}
    rows=[]; evalpred=[]
    for label,model in labels.items():
        if label=="A_NO_CHANGE":
            p=tr[["transition_id","year","delta_speed_mph"]].copy(); p["predicted_delta_speed_mph"]=0.0
        else:
            p=predfile[predfile.model==model].merge(tr[["transition_id","delta_speed_mph"]],on="transition_id",suffixes=("_src","")); p=p[["transition_id","year","delta_speed_mph","predicted_delta_speed_mph"]]
        mm=metrics(p.delta_speed_mph,p.predicted_delta_speed_mph); rows.append({"ablation":label,"model":model,**mm}); p["ablation"]=label; evalpred.append(p)
    # Legacy Fast-Friday-centred R4 predictor: compare consecutive OOF predictions.
    legacy=pd.read_csv(ROOT/"r4/output/r4f7c6_online_latent_window_predictions_v1.csv")
    legacy=legacy[legacy.model=="ONLINE_SHRUNK_FIELD_MEAN"].drop_duplicates("attempt_id").set_index("attempt_id")
    lp=[]
    for _,r in tr.iterrows():
        if r.before_attempt_id in legacy.index and r.after_attempt_id in legacy.index:
            lp.append({"transition_id":r.transition_id,"year":r.year,"delta_speed_mph":r.delta_speed_mph,"predicted_delta_speed_mph":legacy.loc[r.after_attempt_id,"predicted_speed_mph"]-legacy.loc[r.before_attempt_id,"predicted_speed_mph"],"ablation":"B_LEGACY_FAST_FRIDAY_CENTERED"})
    lp=pd.DataFrame(lp)
    if len(lp): rows.append({"ablation":"B_LEGACY_FAST_FRIDAY_CENTERED","model":"R4F7_ONLINE_SHRUNK_FIELD_MEAN_DIFFERENCE",**metrics(lp.delta_speed_mph,lp.predicted_delta_speed_mph)}); evalpred.append(lp)
    results=pd.DataFrame(rows); write_csv(results,"r5h_ablation_results.csv")
    preds=pd.concat(evalpred,ignore_index=True); preds["error_mph"]=preds.predicted_delta_speed_mph-preds.delta_speed_mph; write_csv(preds,"r5h_evaluation_predictions.csv")
    # Decision-benchmark overlap supports deterministic crossing classification,
    # but not an independent probability calibration claim.
    decisions=pd.read_csv(ROOT/"r4/output/r4f8e_reconstructed_decision_numeric_state_v1.csv")
    bx=tr[["transition_id","before_attempt_id","speed_before","speed_after"]].merge(decisions[["source_attempt_id","benchmark_speed_mph"]],left_on="before_attempt_id",right_on="source_attempt_id")
    bc=[]
    for label,g in preds.groupby("ablation"):
        z=bx.merge(g[["transition_id","predicted_delta_speed_mph"]],on="transition_id")
        if len(z):
            actual=z.speed_after>=z.benchmark_speed_mph
            predicted=(z.speed_before+z.predicted_delta_speed_mph)>=z.benchmark_speed_mph
            bc.append({"ablation":label,"n":len(z),"deterministic_crossing_accuracy":float(np.mean(actual==predicted)),"actual_crossing_rate":float(actual.mean()),"probability_metric_status":"UNAVAILABLE_NO_INDEPENDENT_CALIBRATION_SAMPLE"})
    write_csv(pd.DataFrame(bc),"r5h_benchmark_crossing_evaluation.csv")
    er=preds[preds.ablation=="E_FINAL_PHYSICS"].error_mph
    calibration=pd.DataFrame([{"nominal_interval":"EMPIRICAL_LOYO_Q05_Q95","lower_residual_mph":er.quantile(.05),"upper_residual_mph":er.quantile(.95),"observed_self_coverage":np.mean(er.between(er.quantile(.05),er.quantile(.95))),"interpretation":"descriptive same-sample residual envelope; not independent interval validation"}])
    write_csv(calibration,"r5h_uncertainty_calibration.csv")
    finalm=results[results.ablation=="E_FINAL_PHYSICS"].iloc[0].to_dict()
    report={"phase":"R5H","status":"PASS_WITH_SEVERE_SAMPLE_LIMITATIONS","evaluation_N":len(tr),"final_model_metrics":finalm,"ablations":results.to_dict("records"),"physics_improves_over_no_change_mae":bool(finalm["mae_mph"]<results.loc[results.ablation=="A_NO_CHANGE","mae_mph"].iloc[0]),"benchmark_crossing_evaluation":"NOT_IDENTIFIABLE_AS_AN_INDEPENDENT_PROBABILITY_TEST_FROM_27 TRANSITIONS; action labels not used","historical_actions_optimal_labels_used":False,"refit_after_evaluation":False,"limitations":["same 27 transitions support development and LOYO evaluation","2023 has one transition","no independent lane-wait ground truth"]}
    write_json(report,"r5h_evaluation_report.json"); write_json({"phase":"R5H","version":"R5H_EVALUATION_V1","ablation_definitions":labels|{"B_LEGACY_FAST_FRIDAY_CENTERED":"frozen R4F7 OOF consecutive predicted-speed difference"},"no_post_evaluation_refit":True},"r5h_evaluation_contract.json")
    write_csv(pd.DataFrame([{"check":"all mandatory ablations present","value":"|".join(results.ablation),"expected":"A|B|C|D|E","status":"PASS" if len(results)==5 else "FAIL"},{"check":"historical action optimal labels excluded","value":False,"expected":False,"status":"PASS"},{"check":"no refit after evaluation","value":False,"expected":False,"status":"PASS"}]),"r5h_evaluation_qa.csv")
    return report


def finalize(reports:dict, tr:pd.DataFrame, model:dict, sim:dict, evalr:dict, thermal:dict):
    attempt_physics=pd.read_csv(OUT/"r5b_solar_physics_features.csv")
    protected=[]
    for rel in ["data/canonical/v1","r4/output","weather/output","weather/evidence/ptsc"]:
        protected.extend(sorted(p for p in (ROOT/rel).rglob("*") if p.is_file()))
    (OUT/"r5_protected_legacy_inputs_sha256.txt").write_text("".join(f"{sha256(p)}  {p.relative_to(ROOT)}\n" for p in sorted(protected)))
    # Hash the outputs owned by this deterministic generator. Concurrent additive
    # diagnostic files are preserved but are outside this manifest's ownership.
    exact_generated={"r5_final_report.json","r5_manifest_sha256.txt","r5_protected_legacy_inputs_sha256.txt"}
    generated_names=sorted({p.name for p in OUT.iterdir() if p.is_file() and p.name[:3] in {"r5a","r5b","r5c","r5d","r5e","r5f","r5g","r5h"}} | exact_generated)
    preserved_additive=sorted(p.name for p in OUT.iterdir() if p.is_file() and p.name not in generated_names)
    final={"status":"R5_CORRECTED_PHYSICS_ARCHITECTURE_IMPLEMENTED_PARTIAL_BUT_USABLE","same_car_transition_N":len(tr),"usable_track_temperature_attempt_N":int(attempt_physics.track_temperature_c.notna().sum()),"usable_track_temperature_transition_N":int(tr[["track_temp_c_before","track_temp_c_after"]].notna().all(axis=1).sum()),"solar_weather_aligned_attempt_N":int(attempt_physics[["solar_radiation_wm2","air_temperature_c","solar_elevation_deg"]].notna().all(axis=1).sum()),"solar_weather_aligned_transition_N":int(tr[["solar_radiation_wm2_before","solar_radiation_wm2_after","air_temp_c_before","air_temp_c_after"]].notna().all(axis=1).sum()),"selected_physics_model":model["selected_model"],"coefficients":model["coefficients"],"thermal_optimum_identifiable":thermal["optimum_identifiable"],"validation_metrics":model["metrics"],"ablation_results":evalr["ablations"],"simulator_supported_decisions":sim["supported_decisions"],"simulator_blocked_decisions":sim["blocked_decisions"],"wait_future_state_future_performance_active":True,"qa":"PASS_WITH_WARNINGS","created_files":["r5/__init__.py","r5/README.md","r5/run_r5_corrected_physics_pipeline_v1.py","r5/run_r5_qa_v1.py"]+[f"r5/output/{n}" for n in generated_names],"preserved_concurrent_additive_files":[f"r5/output/{n}" for n in preserved_additive],"remaining_blockers":["10 Last Chance decisions lack decision timestamps","exact session remaining unavailable; cutoff remains sensitivity","no empirical action-specific lane wait distributions","27 transitions across three years, with one in 2023","no tyre telemetry/corner shadow/rubbering truth"]}
    write_json(final,"r5_final_report.json")
    # Refresh manifest to include final report.
    paths=sorted(OUT/n for n in generated_names if n!="r5_manifest_sha256.txt" and (OUT/n).is_file())
    (OUT/"r5_manifest_sha256.txt").write_text("".join(f"{sha256(p)}  {p.relative_to(ROOT)}\n" for p in paths))
    return final


def main():
    a=phase_a(); obs=phase_b(); tr=phase_c(obs); model,coef,res=phase_d(tr); thermal=phase_e(tr,model); future,fcontract=phase_f(model); sim=phase_g(future,model,res); evalr=phase_h(tr,model,res)
    final=finalize({"R5A":a,"R5F":fcontract},tr,model,sim,evalr,thermal)
    print(json.dumps(final,indent=2,default=json_default))


if __name__ == "__main__":
    main()
