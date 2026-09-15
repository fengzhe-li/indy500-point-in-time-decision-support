from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path("/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈")
OUT = ROOT / "r5_1/manual"
OUT.mkdir(parents=True, exist_ok=True)

DAY1_CANDIDATES = [
    ROOT / "weather/output/unified_attempt_chronology_constraint_ledger_v9.csv",
    ROOT / "weather/output/unified_attempt_chronology_constraint_ledger_v8.csv",
    ROOT / "weather/output/unified_attempt_chronology_constraint_ledger_v7.csv",
]

LAST_CHANCE_LEDGER = ROOT / "r4/output/r4lc5a_last_chance_chronology_action_ledger_v1.csv"

def first_existing(paths):
    for p in paths:
        if p.exists():
            return p
    return None

def parse_time_col(df):
    candidates = [
        "exact_timestamp",
        "time_midpoint_utc",
        "timestamp_utc",
        "attempt_time_utc",
        "time_utc",
    ]
    for c in candidates:
        if c in df.columns:
            s = pd.to_datetime(df[c], errors="coerce", utc=True)
            if s.notna().any():
                return c, s
    return None, pd.Series(pd.NaT, index=df.index, dtype="datetime64[ns, UTC]")

# ============================================================
# DAY1
# ============================================================

day1_path = first_existing(DAY1_CANDIDATES)

if day1_path is None:
    print("NO DAY1 CHRONOLOGY LEDGER FOUND")
    raise SystemExit

day1 = pd.read_csv(day1_path, dtype=str, keep_default_na=False)

time_col, parsed_time = parse_time_col(day1)
day1["_parsed_time"] = parsed_time

for c in ["year", "car_number", "driver_name", "car_attempt_index", "result_status"]:
    if c not in day1.columns:
        day1[c] = ""

# numeric attempt order
day1["_attempt_index_num"] = pd.to_numeric(
    day1["car_attempt_index"], errors="coerce"
)

# only rows that look like actual car attempts
day1_attempts = day1[
    day1["_attempt_index_num"].notna()
].copy()

day1_attempts = day1_attempts.sort_values(
    ["year", "car_number", "_attempt_index_num", "_parsed_time"],
    na_position="last"
)

rows = []

for (year, car), g in day1_attempts.groupby(["year", "car_number"], dropna=False):
    g = g.sort_values(["_attempt_index_num", "_parsed_time"], na_position="last")

    if len(g) < 2:
        continue

    for i in range(len(g) - 1):
        a = g.iloc[i]
        b = g.iloc[i + 1]

        t1 = a["_parsed_time"]
        t2 = b["_parsed_time"]

        interval_min = np.nan
        interval_status = "UNAVAILABLE"

        if pd.notna(t1) and pd.notna(t2):
            interval_min = (t2 - t1).total_seconds() / 60.0
            interval_status = "EXACT_FROM_AVAILABLE_TIMESTAMPS"

        text = " | ".join([
            str(a.get("notes", "")),
            str(a.get("evidence_summary", "")),
            str(a.get("constraint_class", "")),
            str(a.get("result_status", "")),
            str(b.get("notes", "")),
            str(b.get("evidence_summary", "")),
            str(b.get("constraint_class", "")),
            str(b.get("result_status", "")),
        ]).lower()

        regime = "UNKNOWN"

        # conservative classification only
        if any(k in text for k in [
            "lane 1", "lane1", "priority lane", "withdraw"
        ]):
            regime = "DAY1_PRIORITY"

        if any(k in text for k in [
            "lane 2", "lane2", "retain"
        ]):
            # only override if lane2 is explicitly indicated
            if "lane 2" in text or "lane2" in text:
                regime = "DAY1_RETAIN_QUEUE"

        rows.append({
            "year": year,
            "car_number": car,
            "driver_name": a.get("driver_name", ""),
            "attempt_from": a.get("car_attempt_index", ""),
            "attempt_to": b.get("car_attempt_index", ""),
            "time_from": "" if pd.isna(t1) else t1.isoformat(),
            "time_to": "" if pd.isna(t2) else t2.isoformat(),
            "reattempt_interval_min": interval_min,
            "interval_status": interval_status,
            "regime": regime,
            "from_result_status": a.get("result_status", ""),
            "to_result_status": b.get("result_status", ""),
            "from_constraint_class": a.get("constraint_class", ""),
            "to_constraint_class": b.get("constraint_class", ""),
            "from_evidence_summary": a.get("evidence_summary", ""),
            "to_evidence_summary": b.get("evidence_summary", ""),
            "source_ledger": str(day1_path.relative_to(ROOT)),
        })

day1_out = pd.DataFrame(rows)

day1_outfile = OUT / "day1_reattempt_intervals_v1.csv"
day1_out.to_csv(day1_outfile, index=False)

# ============================================================
# LAST CHANCE
# ============================================================

lc_rows = []

if LAST_CHANCE_LEDGER.exists():
    lc = pd.read_csv(LAST_CHANCE_LEDGER, dtype=str, keep_default_na=False)

    for c in [
        "year", "car_number", "driver_name",
        "attempt_ordinal", "exact_timestamp",
        "timestamp_status", "completion_status",
        "chronology_quality", "relative_order",
        "strategy_event", "evidence_note"
    ]:
        if c not in lc.columns:
            lc[c] = ""

    lc["_attempt_num"] = pd.to_numeric(lc["attempt_ordinal"], errors="coerce")
    lc["_parsed_time"] = pd.to_datetime(
        lc["exact_timestamp"], errors="coerce", utc=True
    )

    lc_attempts = lc[
        lc["_attempt_num"].notna()
    ].copy()

    for (year, car), g in lc_attempts.groupby(["year", "car_number"], dropna=False):
        g = g.sort_values(["_attempt_num", "_parsed_time"], na_position="last")

        if len(g) < 2:
            continue

        for i in range(len(g) - 1):
            a = g.iloc[i]
            b = g.iloc[i + 1]

            t1 = a["_parsed_time"]
            t2 = b["_parsed_time"]

            interval_min = np.nan
            interval_status = "UNAVAILABLE"

            if pd.notna(t1) and pd.notna(t2):
                interval_min = (t2 - t1).total_seconds() / 60.0
                interval_status = "EXACT_FROM_AVAILABLE_TIMESTAMPS"

            lc_rows.append({
                "year": year,
                "car_number": car,
                "driver_name": a.get("driver_name", ""),
                "attempt_from": a.get("attempt_ordinal", ""),
                "attempt_to": b.get("attempt_ordinal", ""),
                "time_from": "" if pd.isna(t1) else t1.isoformat(),
                "time_to": "" if pd.isna(t2) else t2.isoformat(),
                "reattempt_interval_min": interval_min,
                "interval_status": interval_status,
                "regime": "LAST_CHANCE",
                "from_completion_status": a.get("completion_status", ""),
                "to_completion_status": b.get("completion_status", ""),
                "from_chronology_quality": a.get("chronology_quality", ""),
                "to_chronology_quality": b.get("chronology_quality", ""),
                "from_relative_order": a.get("relative_order", ""),
                "to_relative_order": b.get("relative_order", ""),
                "from_strategy_event": a.get("strategy_event", ""),
                "to_strategy_event": b.get("strategy_event", ""),
                "from_evidence_note": a.get("evidence_note", ""),
                "to_evidence_note": b.get("evidence_note", ""),
                "source_ledger": str(LAST_CHANCE_LEDGER.relative_to(ROOT)),
            })

lc_out = pd.DataFrame(lc_rows)
lc_outfile = OUT / "last_chance_reattempt_intervals_v1.csv"
lc_out.to_csv(lc_outfile, index=False)

# ============================================================
# SUMMARY
# ============================================================

print("=" * 140)
print("DAY1 REATTEMPT INTERVAL AUDIT")
print("=" * 140)
print("SOURCE:", day1_path.relative_to(ROOT))
print("TIME COLUMN:", time_col)
print("ROWS:", len(day1_out))

if not day1_out.empty:
    print("\nBY REGIME:")
    print(day1_out["regime"].value_counts(dropna=False).to_string())

    exact = day1_out[
        day1_out["interval_status"] == "EXACT_FROM_AVAILABLE_TIMESTAMPS"
    ].copy()

    print("\nEXACT INTERVALS:", len(exact))

    if not exact.empty:
        print(
            exact[
                [
                    "year",
                    "car_number",
                    "driver_name",
                    "attempt_from",
                    "attempt_to",
                    "reattempt_interval_min",
                    "regime",
                ]
            ]
            .sort_values(["year", "reattempt_interval_min"])
            .to_string(index=False)
        )

        print("\nINTERVAL SUMMARY BY REGIME:")
        summary = (
            exact.groupby("regime")["reattempt_interval_min"]
            .agg(["count", "min", "median", "mean", "max"])
            .reset_index()
        )
        print(summary.to_string(index=False))

print("\n" + "=" * 140)
print("LAST CHANCE REATTEMPT INTERVAL AUDIT")
print("=" * 140)
print("ROWS:", len(lc_out))

if not lc_out.empty:
    print(
        lc_out[
            [
                "year",
                "car_number",
                "driver_name",
                "attempt_from",
                "attempt_to",
                "reattempt_interval_min",
                "interval_status",
            ]
        ].to_string(index=False)
    )

print("\nOUTPUTS:")
print(day1_outfile.relative_to(ROOT))
print(lc_outfile.relative_to(ROOT))
print("\nREATTEMPT_INTERVAL_AUDIT_COMPLETE")
