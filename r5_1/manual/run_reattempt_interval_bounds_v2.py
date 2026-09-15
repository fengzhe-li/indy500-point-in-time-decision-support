from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path("/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈")
OUT = ROOT / "r5_1/manual"
OUT.mkdir(parents=True, exist_ok=True)

SRC = ROOT / "weather/output/unified_attempt_chronology_constraint_ledger_v9.csv"

df = pd.read_csv(SRC, dtype=str, keep_default_na=False)

for c in [
    "year", "car_number", "driver_name", "car_attempt_index",
    "time_lower_utc", "time_upper_utc", "time_midpoint_utc",
    "constraint_class", "result_status", "notes",
    "evidence_summary", "source_authority"
]:
    if c not in df.columns:
        df[c] = ""

df["_attempt"] = pd.to_numeric(df["car_attempt_index"], errors="coerce")

for c in ["time_lower_utc", "time_upper_utc", "time_midpoint_utc"]:
    df["_" + c] = pd.to_datetime(df[c], errors="coerce", utc=True)

df = df[df["_attempt"].notna()].copy()

# Deduplicate same attempt conservatively:
# prefer rows with narrower time windows / usable bounds
def width_minutes(r):
    lo, hi = r["_time_lower_utc"], r["_time_upper_utc"]
    if pd.notna(lo) and pd.notna(hi):
        return (hi - lo).total_seconds() / 60
    return np.inf

df["_window_width"] = df.apply(width_minutes, axis=1)

df = df.sort_values(
    ["year", "car_number", "_attempt", "_window_width"],
    na_position="last"
)

df = df.drop_duplicates(
    subset=["year", "car_number", "_attempt"],
    keep="first"
)

rows = []

for (year, car), g in df.groupby(["year", "car_number"], dropna=False):
    g = g.sort_values("_attempt")

    if len(g) < 2:
        continue

    for i in range(len(g) - 1):
        a = g.iloc[i]
        b = g.iloc[i + 1]

        # require consecutive attempt ordinals
        if b["_attempt"] != a["_attempt"] + 1:
            continue

        a_lo = a["_time_lower_utc"]
        a_hi = a["_time_upper_utc"]
        b_lo = b["_time_lower_utc"]
        b_hi = b["_time_upper_utc"]

        lower = np.nan
        upper = np.nan
        midpoint = np.nan
        quality = "NO_USABLE_TIME_BOUNDS"

        if all(pd.notna(x) for x in [a_lo, a_hi, b_lo, b_hi]):

            # Minimum possible separation:
            # earliest B minus latest A
            lower = (b_lo - a_hi).total_seconds() / 60

            # Maximum possible separation:
            # latest B minus earliest A
            upper = (b_hi - a_lo).total_seconds() / 60

            lower = max(0.0, lower)
            upper = max(0.0, upper)

            midpoint = (lower + upper) / 2

            if (
                a_lo == a_hi and
                b_lo == b_hi
            ):
                quality = "EXACT"
            elif upper - lower <= 5:
                quality = "TIGHT_BOUND"
            elif upper - lower <= 15:
                quality = "MODERATE_BOUND"
            else:
                quality = "WIDE_BOUND"

        text = " | ".join([
            str(a.get("notes", "")),
            str(a.get("evidence_summary", "")),
            str(b.get("notes", "")),
            str(b.get("evidence_summary", "")),
        ]).lower()

        regime = "UNKNOWN"

        # Explicit evidence only
        if (
            "lane 1" in text or
            "lane1" in text or
            "priority lane" in text
        ):
            regime = "DAY1_PRIORITY"

        if (
            "lane 2" in text or
            "lane2" in text or
            "second lane" in text
        ):
            regime = "DAY1_RETAIN_QUEUE"

        rows.append({
            "year": year,
            "car_number": car,
            "driver_name": a["driver_name"],

            "attempt_from": int(a["_attempt"]),
            "attempt_to": int(b["_attempt"]),

            "from_lower": "" if pd.isna(a_lo) else a_lo.isoformat(),
            "from_upper": "" if pd.isna(a_hi) else a_hi.isoformat(),
            "to_lower": "" if pd.isna(b_lo) else b_lo.isoformat(),
            "to_upper": "" if pd.isna(b_hi) else b_hi.isoformat(),

            "interval_lower_min": lower,
            "interval_upper_min": upper,
            "interval_midpoint_min": midpoint,
            "interval_width_min": (
                upper - lower
                if pd.notna(lower) and pd.notna(upper)
                else np.nan
            ),

            "time_quality": quality,
            "regime": regime,

            "from_constraint": a["constraint_class"],
            "to_constraint": b["constraint_class"],
            "from_status": a["result_status"],
            "to_status": b["result_status"],

            "from_source_authority": a["source_authority"],
            "to_source_authority": b["source_authority"],

            "from_evidence": a["evidence_summary"],
            "to_evidence": b["evidence_summary"],
        })

out = pd.DataFrame(rows)

outfile = OUT / "day1_reattempt_interval_bounds_v2.csv"
out.to_csv(outfile, index=False)

print("=" * 150)
print("DAY1 REATTEMPT INTERVAL BOUNDS V2")
print("=" * 150)

print("\nTOTAL CONSECUTIVE TRANSITIONS:", len(out))

print("\nTIME QUALITY:")
print(out["time_quality"].value_counts(dropna=False).to_string())

print("\nREGIME:")
print(out["regime"].value_counts(dropna=False).to_string())

usable = out[
    out["time_quality"] != "NO_USABLE_TIME_BOUNDS"
].copy()

print("\nUSABLE BOUNDED / EXACT TRANSITIONS:", len(usable))

if not usable.empty:
    cols = [
        "year",
        "car_number",
        "driver_name",
        "attempt_from",
        "attempt_to",
        "interval_lower_min",
        "interval_upper_min",
        "interval_midpoint_min",
        "time_quality",
        "regime",
    ]

    print("\nALL USABLE:")
    print(
        usable[cols]
        .sort_values(["year", "interval_midpoint_min"])
        .to_string(index=False)
    )

    print("\nBY YEAR:")
    print(
        usable.groupby("year")["interval_midpoint_min"]
        .agg(["count", "min", "median", "mean", "max"])
        .round(2)
        .to_string()
    )

    print("\nEXPLICIT PRIORITY:")
    priority = usable[
        usable["regime"] == "DAY1_PRIORITY"
    ]

    if priority.empty:
        print("NONE")
    else:
        print(priority[cols].to_string(index=False))

    print("\nEXPLICIT LANE 2:")
    lane2 = usable[
        usable["regime"] == "DAY1_RETAIN_QUEUE"
    ]

    if lane2.empty:
        print("NONE")
    else:
        print(lane2[cols].to_string(index=False))

print("\nOUTPUT:")
print(outfile.relative_to(ROOT))
print("\nREATTEMPT_INTERVAL_BOUNDS_V2_COMPLETE")
