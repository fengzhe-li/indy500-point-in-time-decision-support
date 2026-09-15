import csv
import datetime as dt
import math
from collections import Counter, defaultdict

from ..io_utils import stable_id

RAW_VARIABLES = {"TMP_2m":"K", "DPT_2m":"K", "UGRD_10m":"m/s", "VGRD_10m":"m/s",
    "GUST_surface":"m/s", "PRES_surface":"Pa", "TCDC_atmosphere":"%", "DSWRF_surface":"W/m^2"}
DERIVED_VARIABLES = {"temp_c":"degC", "dewpoint_c":"degC", "relative_humidity_pct":"%",
    "wind_speed_10m_ms":"m/s", "wind_direction_deg":"degree", "pressure_hpa":"hPa",
    "gust_ms":"m/s", "cloud_cover_pct":"%", "shortwave_radiation_wm2":"W/m^2"}
VARIABLE_UNITS = {**RAW_VARIABLES, **DERIVED_VARIABLES}
REQUIRED_COLUMNS = {"date","cycle_time_utc","forecast_hour","valid_time_utc","ims_lat","ims_lon",
    *RAW_VARIABLES,*DERIVED_VARIABLES,"forecast_lead_hours"}
PHYSICAL_RANGES = {
    "TMP_2m":(180,330), "DPT_2m":(180,330), "UGRD_10m":(-100,100), "VGRD_10m":(-100,100),
    "GUST_surface":(0,100), "PRES_surface":(50000,110000), "TCDC_atmosphere":(0,100), "DSWRF_surface":(0,1400),
    "temp_c":(-90,60), "dewpoint_c":(-90,60), "relative_humidity_pct":(0,100),
    "wind_speed_10m_ms":(0,100), "wind_direction_deg":(0,360), "pressure_hpa":(500,1100),
    "gust_ms":(0,100), "cloud_cover_pct":(0,100), "shortwave_radiation_wm2":(0,1400)}

def _utc(text):
    value=dt.datetime.fromisoformat(text.replace("Z","+00:00"))
    if value.utcoffset()!=dt.timedelta(0): raise ValueError(f"timestamp is not UTC: {text}")
    return value

def _iso(value): return value.astimezone(dt.timezone.utc).isoformat().replace("+00:00","Z")

def parse_hrrr_numeric(path):
    """Parse the frozen one-row-per-cycle/lead numeric extract without filling gaps."""
    with path.open(encoding="utf-8-sig",newline="") as handle:
        reader=csv.DictReader(handle)
        missing=REQUIRED_COLUMNS-set(reader.fieldnames or [])
        if missing: raise ValueError(f"HRRR numeric input missing columns: {sorted(missing)}")
        rows=[]
        for number,source in enumerate(reader,2):
            cycle=_utc(source["cycle_time_utc"]); valid=_utc(source["valid_time_utc"])
            forecast_hour=int(source["forecast_hour"]); lead=float(source["forecast_lead_hours"])
            if lead!=forecast_hour: raise ValueError(f"row {number}: forecast lead fields disagree")
            rows.append({"source_row_number":number,"date":source["date"],"year":int(source["date"][:4]),
                "cycle_time_utc":_iso(cycle),"forecast_hour":forecast_hour,"valid_time_utc":_iso(valid),
                "ims_lat":float(source["ims_lat"]),"ims_lon":float(source["ims_lon"]),
                "forecast_lead_hours":lead,"values":{name:float(source[name]) for name in VARIABLE_UNITS}})
    return rows

def expected_derived(values):
    temp=values["TMP_2m"]-273.15; dew=values["DPT_2m"]-273.15
    return {"temp_c":temp,"dewpoint_c":dew,
        "relative_humidity_pct":100*math.exp((17.625*dew)/(243.04+dew)-(17.625*temp)/(243.04+temp)),
        "wind_speed_10m_ms":math.hypot(values["UGRD_10m"],values["VGRD_10m"]),
        "wind_direction_deg":(math.degrees(math.atan2(-values["UGRD_10m"],-values["VGRD_10m"]))+360)%360,
        "pressure_hpa":values["PRES_surface"]/100,"gust_ms":values["GUST_surface"],
        "cloud_cover_pct":values["TCDC_atmosphere"],"shortwave_radiation_wm2":values["DSWRF_surface"]}

def build_snapshot(row,session_id,source_id):
    snapshot_id=stable_id("forecast_snapshot","NOAA","HRRR",row["cycle_time_utc"],row["forecast_lead_hours"],row["ims_lat"],row["ims_lon"])
    return {"forecast_snapshot_id":snapshot_id,"session_id":session_id,"source_id":source_id,
        "provider":"NOAA","model_name":"HRRR","model_version":None,"issue_time_utc":row["cycle_time_utc"],
        "availability_time_utc":None,"availability_time_quality":"UNKNOWN","valid_start_utc":row["valid_time_utc"],
        "valid_end_utc":row["valid_time_utc"],"forecast_lead_hours":row["forecast_lead_hours"],
        "location_type":"GRID_POINT","spatial_locator":f"IMS_HRRR_GRID_POINT;lat={row['ims_lat']};lon={row['ims_lon']}",
        "latitude":row["ims_lat"],"longitude":row["ims_lon"],"extraction_metadata_json":{
            "status":"NUMERIC_MATERIALIZED","availability_status":"POLICY_REQUIRED","source_row_number":row["source_row_number"],
            "source_date":row["date"],"forecast_hour":row["forecast_hour"],"raw_variable_codes":list(RAW_VARIABLES),
            "derived_variable_codes":list(DERIVED_VARIABLES),
            "extraction_method":"NOAA historical HRRR GRIB .idx plus HTTP Range requests and ecCodes"}}

def build_values(row,snapshot_id):
    return [{"weather_forecast_value_id":stable_id("weather_forecast",snapshot_id,name),
        "forecast_snapshot_id":snapshot_id,"variable_code":name,"value_numeric":row["values"][name],
        "value_text":None,"unit":unit} for name,unit in VARIABLE_UNITS.items()]

def qa_rows(path,tables):
    """Validate the frozen input and its canonical materialization."""
    rows=parse_hrrr_numeric(path); snapshots=tables["forecast_snapshots"]; values=tables["weather_forecasts"]; checks=[]
    def add(cid,passed,affected=0,expected=None,actual=None,details="",year="ALL",severity="BLOCKING"):
        checks.append({"check_id":cid,"year":year,"severity":severity,"pass_fail":"PASS" if passed else "FAIL",
            "affected_count":affected,"expected_count":expected,"actual_count":actual,"details":details})
    add("INPUT_ROW_COUNT",len(rows)==259,abs(259-len(rows)),259,len(rows),"Frozen numeric input row count")
    keys=[(r["cycle_time_utc"],r["forecast_hour"],r["ims_lat"],r["ims_lon"]) for r in rows]
    duplicates=sum(n-1 for n in Counter(keys).values() if n>1)
    add("INPUT_CYCLE_LEAD_LOCATION_UNIQUE",duplicates==0,duplicates,len(rows),len(set(keys)),"No duplicate input snapshot identities")
    for year in range(2020,2025):
        actual={(int(r["cycle_time_utc"][11:13]),r["forecast_hour"]) for r in rows if r["year"]==year}
        expected={(cycle,lead) for cycle in range(11,24) for lead in range(4)}; missing=sorted(expected-actual)
        expected_missing=[(14,3)] if year==2024 else []
        label=";".join(f"{c:02d}Z_f{lead:02d}" for c,lead in missing) or "NONE"
        add("EXPECTED_CYCLE_LEAD_COVERAGE",missing==expected_missing,len(missing),52,len(actual),f"missing={label}",year)
    bad=[r["source_row_number"] for r in rows if _utc(r["valid_time_utc"])!=_utc(r["cycle_time_utc"])+dt.timedelta(hours=r["forecast_lead_hours"])]
    add("VALID_TIME_ARITHMETIC",not bad,len(bad),len(rows),len(rows)-len(bad),f"bad_rows={bad[:20]}")
    range_bad=[(r["source_row_number"],name) for r in rows for name,(low,high) in PHYSICAL_RANGES.items() if not low<=r["values"][name]<=high]
    add("PHYSICAL_RANGE_SANITY",not range_bad,len(range_bad),len(rows)*17,len(rows)*17-len(range_bad),f"bad={range_bad[:20]}")
    residuals=[(r["source_row_number"],name,abs(r["values"][name]-expected)) for r in rows for name,expected in expected_derived(r["values"]).items()]
    derived_bad=[x for x in residuals if x[2]>1e-10]
    add("DERIVED_FIELD_CONSISTENCY",not derived_bad,len(derived_bad),len(rows)*9,len(rows)*9-len(derived_bad),f"max_abs_residual={max(x[2] for x in residuals):.3g};bad={derived_bad[:10]}")
    coord_bad=[r["source_row_number"] for r in rows if (r["ims_lat"],r["ims_lon"])!=(39.795,-86.234)]
    add("IMS_EXTRACTION_COORDINATES",not coord_bad,len(coord_bad),len(rows),len(rows)-len(coord_bad),"Expected frozen extraction point 39.795,-86.234")
    ids=[s["forecast_snapshot_id"] for s in snapshots]; duplicate_snapshots=len(ids)-len(set(ids))
    add("CANONICAL_SNAPSHOT_UNIQUE",duplicate_snapshots==0,duplicate_snapshots,len(rows),len(snapshots),"One canonical snapshot per input cycle/lead/location")
    source_ids={s["source_id"] for s in tables["sources"]}; source_fk_bad=[s["forecast_snapshot_id"] for s in snapshots if s["source_id"] not in source_ids]
    add("FORECAST_SNAPSHOT_SOURCE_FOREIGN_KEYS",not source_fk_bad,len(source_fk_bad),len(snapshots),len(snapshots)-len(source_fk_bad),f"bad={source_fk_bad[:20]}")
    value_keys=[(v["forecast_snapshot_id"],v["variable_code"]) for v in values]; duplicate_values=len(value_keys)-len(set(value_keys))
    add("CANONICAL_VARIABLE_UNIQUE",duplicate_values==0,duplicate_values,len(rows)*17,len(values),"At most one value per snapshot and variable")
    snapshot_id_set=set(ids); value_fk_bad=[v["weather_forecast_value_id"] for v in values if v["forecast_snapshot_id"] not in snapshot_id_set]
    add("WEATHER_VALUE_SNAPSHOT_FOREIGN_KEYS",not value_fk_bad,len(value_fk_bad),len(values),len(values)-len(value_fk_bad),f"bad={value_fk_bad[:20]}")
    units_bad=[v["weather_forecast_value_id"] for v in values if VARIABLE_UNITS.get(v["variable_code"])!=v["unit"]]
    add("CANONICAL_UNIT_CONSISTENCY",not units_bad,len(units_bad),len(values),len(values)-len(units_bad),f"bad={units_bad[:20]}")
    placeholders=[s["forecast_snapshot_id"] for s in snapshots if s["extraction_metadata_json"].get("status")=="INDEX_ONLY_NO_VALUES"]
    add("NO_INDEX_ONLY_PLACEHOLDERS",not placeholders,len(placeholders),0,len(placeholders),"No index inventory row is represented as a numeric snapshot")
    availability_bad=[s["forecast_snapshot_id"] for s in snapshots if s["availability_time_utc"] is not None or s["availability_time_quality"]!="UNKNOWN" or s["extraction_metadata_json"].get("availability_status")!="POLICY_REQUIRED"]
    add("CYCLE_VALID_AVAILABILITY_DISTINCT",not availability_bad,len(availability_bad),len(snapshots),len(snapshots)-len(availability_bad),"Cycle and valid time retained; public availability is null and POLICY_REQUIRED")
    prohibited=[v["weather_forecast_value_id"] for v in values if any(x in v["variable_code"].lower() for x in ("track","asphalt","shade","tire","rubber"))]
    add("NO_TRACK_OR_TIRE_PROXY_SEMANTICS",not prohibited,len(prohibited),0,len(prohibited),"Only supplied atmospheric and radiative variables are materialized")
    primary={(l["entity_id"],l["field_name"]):l for l in tables["field_evidence_links"] if l["is_primary"]}
    provenance_bad=[]
    for value in values:
        link=primary.get((value["weather_forecast_value_id"],"value_numeric"))
        expected="RAW_OBSERVED" if value["variable_code"] in RAW_VARIABLES else "DERIVED_DETERMINISTIC"
        if not link or link["value_classification"]!=expected: provenance_bad.append(value["weather_forecast_value_id"])
    add("RAW_DERIVED_PROVENANCE_CLASSIFICATION",not provenance_bad,len(provenance_bad),len(values),len(values)-len(provenance_bad),f"bad={provenance_bad[:20]}")
    by_row={s["extraction_metadata_json"]["source_row_number"]:s for s in snapshots}; canonical=defaultdict(dict)
    for value in values: canonical[value["forecast_snapshot_id"]][value["variable_code"]]=value["value_numeric"]
    fabricated=[]
    for row in rows:
        snapshot=by_row.get(row["source_row_number"])
        if not snapshot: fabricated.append(f"row={row['source_row_number']}:missing_snapshot")
        elif canonical[snapshot["forecast_snapshot_id"]]!=row["values"]: fabricated.append(f"row={row['source_row_number']}:value_mismatch")
    fabricated += [f"row={x}:extra_snapshot" for x in sorted(set(by_row)-{r["source_row_number"] for r in rows})]
    add("ZERO_FABRICATED_WEATHER_VALUES",not fabricated,len(fabricated),len(rows)*17,len(values),f"issues={fabricated[:20]}")
    add("NO_PHASE_4B_WEATHER_JOINS",not tables["decision_state_features"],len(tables["decision_state_features"]),0,len(tables["decision_state_features"]),"Phase 4A ends before attempt or decision-state weather alignment")
    return checks
