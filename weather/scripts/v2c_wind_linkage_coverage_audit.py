from pathlib import Path
import pandas as pd
import numpy as np

CORE = Path(
    "r5_2/manual/probabilistic_physics_loyo_residuals_v1.csv"
)

TRANSITION_MAP = Path(
    "weather/output/v2b_section_mechanism/"
    "v2b_transition_map_v1.csv"
)

FROZEN_ENV = Path(
    "r5/frozen_inputs/day1/"
    "day1_environment_linked_transitions_39_FROZEN.csv"
)

REPEAT_ANALYSIS = Path(
    "r5_2/manual/r5_2_repeat_analysis_set_v1.csv"
)

R5C = Path(
    "r5/output/r5c_same_car_physics_transitions.csv"
)

OUTDIR = Path(
    "weather/output/v2c_wind_diagnostic"
)

OUT_AUDIT = OUTDIR / "v2c_wind_linkage_coverage_audit_v1.csv"
OUT_SUMMARY = OUTDIR / "v2c_wind_linkage_coverage_summary_v1.txt"

OUTDIR.mkdir(parents=True, exist_ok=True)


def norm_id(x):
    if pd.isna(x):
        return None
    return str(x).strip()


def coverage(df, cols):
    rows = []
    for c in cols:
        if c in df.columns:
            s = pd.to_numeric(df[c], errors="coerce")
            rows.append({
                "field": c,
                "n_nonnull": int(s.notna().sum()),
                "n_total": len(df),
                "coverage": float(s.notna().mean()),
                "min": float(s.min()) if s.notna().any() else np.nan,
                "median": float(s.median()) if s.notna().any() else np.nan,
                "max": float(s.max()) if s.notna().any() else np.nan,
            })
    return pd.DataFrame(rows)


print("=" * 100)
print("INDY 500 V2-C WIND LINKAGE / COVERAGE AUDIT")
print("=" * 100)

core = pd.read_csv(CORE)
tm = pd.read_csv(TRANSITION_MAP)
frozen = pd.read_csv(FROZEN_ENV)
repeat = pd.read_csv(REPEAT_ANALYSIS)
r5c = pd.read_csv(R5C)

for df in [tm, frozen, repeat, r5c]:
    for c in ["before_attempt_id", "after_attempt_id"]:
        if c in df.columns:
            df[c] = df[c].map(norm_id)

print()
print("ROW COUNTS")
print("-" * 100)
print("final physics core:", len(core))
print("V2-B linked transition map:", len(tm))
print("frozen environment transitions:", len(frozen))
print("r5_2 repeat analysis:", len(repeat))
print("r5c same-car transitions:", len(r5c))

# ------------------------------------------------------------------
# Exact attempt-pair overlap
# ------------------------------------------------------------------

tm_pairs = set(
    zip(
        tm["before_attempt_id"],
        tm["after_attempt_id"]
    )
)

sources = {
    "frozen_environment": frozen,
    "r5_2_repeat_analysis": repeat,
    "r5c_same_car": r5c,
}

print()
print("EXACT ATTEMPT-PAIR OVERLAP WITH V2-B LINKED MAP")
print("-" * 100)

for name, df in sources.items():

    if not {
        "before_attempt_id",
        "after_attempt_id"
    }.issubset(df.columns):

        print(name, ": no attempt-pair IDs")
        continue

    pairs = set(
        zip(
            df["before_attempt_id"],
            df["after_attempt_id"]
        )
    )

    overlap = tm_pairs & pairs

    print(
        f"{name}: "
        f"{len(overlap)}/{len(tm_pairs)} "
        f"V2-B linked transitions"
    )

# ------------------------------------------------------------------
# Build one audit row per V2-B linked transition
# ------------------------------------------------------------------

rows = []

for _, tr in tm.iterrows():

    before_id = tr["before_attempt_id"]
    after_id = tr["after_attempt_id"]

    row = {
        "core_row": tr.get("core_row"),
        "year": tr.get("year"),
        "car_number": tr.get("car_number"),
        "driver_name": tr.get("driver_name"),
        "delta_speed_mph": tr.get("delta_speed_mph"),
        "before_attempt_id": before_id,
        "after_attempt_id": after_id,
    }

    for source_name, df in sources.items():

        m = df[
            (df["before_attempt_id"] == before_id)
            &
            (df["after_attempt_id"] == after_id)
        ]

        row[f"{source_name}_exact_pair_count"] = len(m)

        if len(m) == 1:

            r = m.iloc[0]

            candidate_cols = [
                "delta_ptsc_wind",
                "delta_forecast_wind_speed_10m_ms",
                "delta_forecast_gust_ms",
                "delta_wind_speed_ms",
                "delta_gust_ms",
                "delta_wind_direction_deg",
                "delta_wind_u_ms",
                "delta_wind_v_ms",
                "before_wind_speed_ms",
                "after_wind_speed_ms",
                "before_gust_ms",
                "after_gust_ms",
                "previous_wind_speed_ms",
                "next_wind_speed_ms",
                "previous_gust_ms",
                "next_gust_ms",
                "before_time_utc",
                "after_time_utc",
                "before_time_class",
                "after_time_class",
                "analysis_source",
            ]

            for c in candidate_cols:
                if c in r.index:
                    row[
                        f"{source_name}__{c}"
                    ] = r[c]

    rows.append(row)

audit = pd.DataFrame(rows)
audit.to_csv(OUT_AUDIT, index=False)

# ------------------------------------------------------------------
# Coverage summaries
# ------------------------------------------------------------------

lines = []

def add(x=""):
    lines.append(str(x))


add("=" * 100)
add("INDY 500 V2-C WIND LINKAGE / COVERAGE SUMMARY")
add("=" * 100)

add()
add("CORE / LINKAGE COUNTS")
add("-" * 100)
add(f"Final physics core: {len(core)}")
add(f"V2-B exact transition identities: {len(tm)}")

for source_name in sources:

    c = f"{source_name}_exact_pair_count"

    exact = int(
        (audit[c] == 1).sum()
    )

    duplicate = int(
        (audit[c] > 1).sum()
    )

    add(
        f"{source_name}: "
        f"exact unique pair matches {exact}/{len(tm)}, "
        f"duplicate matches {duplicate}"
    )

# ------------------------------------------------------------------
# Wind field coverage in each source
# ------------------------------------------------------------------

for source_name, df in sources.items():

    add()
    add(source_name.upper())
    add("-" * 100)

    wind_cols = [
        c for c in df.columns
        if (
            "wind" in c.lower()
            or
            "gust" in c.lower()
        )
    ]

    add("wind/gust fields:")
    for c in wind_cols:
        add(f"  {c}")

    numeric_candidates = [
        c for c in wind_cols
        if any(
            token in c.lower()
            for token in [
                "speed",
                "gust",
                "delta",
                "_u_",
                "_v_",
                "ptsc_wind",
            ]
        )
    ]

    cov = coverage(
        df,
        numeric_candidates
    )

    if len(cov):
        add()
        add(
            cov.to_string(
                index=False
            )
        )

# ------------------------------------------------------------------
# Inspect unmatched V2-B transitions
# ------------------------------------------------------------------

add()
add("V2-B TRANSITIONS NOT EXACTLY MATCHED IN FROZEN ENVIRONMENT")
add("-" * 100)

missing = audit[
    audit[
        "frozen_environment_exact_pair_count"
    ] != 1
]

if len(missing):

    add(
        missing[
            [
                "core_row",
                "year",
                "car_number",
                "driver_name",
                "delta_speed_mph",
                "before_attempt_id",
                "after_attempt_id",
            ]
        ].to_string(index=False)
    )

else:
    add("none")

add()
add("INTERPRETATION BOUNDARY")
add("-" * 100)
add(
    "This audit does not test whether wind predicts performance residuals."
)
add(
    "PTSC wind and HRRR wind/gust are retained as distinct evidence streams."
)
add(
    "No deterministic wind coefficient is introduced at this stage."
)

summary = "\n".join(lines)

OUT_SUMMARY.write_text(
    summary,
    encoding="utf-8"
)

print()
print(summary)

print()
print("=" * 100)
print("OUTPUTS")
print("=" * 100)
print(OUT_AUDIT)
print(OUT_SUMMARY)
print()
print("DONE")
