from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path("/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈")
OUT = ROOT / "r5_2/manual"
OUT.mkdir(parents=True, exist_ok=True)

REPEAT = ROOT / "r5_1/output/day1_same_car_repeat_inventory_v1.csv"
RESCUE = ROOT / "r5_2/manual/rescued_repeat_physical_transitions_v2.csv"

repeat = pd.read_csv(REPEAT)
rescue = pd.read_csv(RESCUE)

# ------------------------------------------------------------------
# normalize
# ------------------------------------------------------------------

repeat["year"] = pd.to_numeric(repeat["year"], errors="coerce").astype("Int64")
rescue["year"] = pd.to_numeric(rescue["year"], errors="coerce").astype("Int64")

repeat["car_number"] = (
    repeat["car_number"].astype(str).str.replace(r"\.0$", "", regex=True)
)
rescue["car_number"] = (
    rescue["car_number"].astype(str).str.replace(r"\.0$", "", regex=True)
)

def as_bool(s):
    return s.astype(str).str.lower().isin(["true", "1", "yes"])

repeat["_frozen39"] = as_bool(repeat["in_frozen_39"])

# ------------------------------------------------------------------
# 1. overlap audit
# ------------------------------------------------------------------

print("=" * 150)
print("PART 1 — RESCUE / FROZEN 39 OVERLAP AUDIT")
print("=" * 150)

frozen_ids = set(
    repeat.loc[repeat["_frozen39"], "transition_id"]
    .dropna()
    .astype(str)
)

rescue["transition_id"] = rescue["transition_id"].astype(str)

rescue["already_in_frozen_39_by_id"] = (
    rescue["transition_id"].isin(frozen_ids)
)

# fallback speed-pair check
def pair_key(df, before_col, after_col):
    return (
        df["year"].astype(str)
        + "|"
        + df["car_number"].astype(str)
        + "|"
        + pd.to_numeric(df[before_col], errors="coerce").round(3).astype(str)
        + "|"
        + pd.to_numeric(df[after_col], errors="coerce").round(3).astype(str)
    )

repeat["_pair_key"] = pair_key(
    repeat,
    "before_four_lap_average_speed_mph",
    "after_four_lap_average_speed_mph",
)

rescue["_pair_key"] = pair_key(
    rescue,
    "before_speed_mph",
    "after_speed_mph",
)

frozen_pair_keys = set(
    repeat.loc[repeat["_frozen39"], "_pair_key"]
)

rescue["already_in_frozen_39_by_pair"] = (
    rescue["_pair_key"].isin(frozen_pair_keys)
)

print(
    rescue[
        [
            "year",
            "car_number",
            "driver_name",
            "before_speed_mph",
            "after_speed_mph",
            "already_in_frozen_39_by_id",
            "already_in_frozen_39_by_pair",
        ]
    ].to_string(index=False)
)

safe_rescue = rescue[
    ~rescue["already_in_frozen_39_by_id"]
    & ~rescue["already_in_frozen_39_by_pair"]
].copy()

print("\nTOTAL RESCUED:", len(rescue))
print("NEW NON-OVERLAPPING RESCUED:", len(safe_rescue))

# ------------------------------------------------------------------
# 2. construct combined derived analysis set
# ------------------------------------------------------------------

print("\n" + "=" * 150)
print("PART 2 — BUILD R5.2 DERIVED ANALYSIS SET")
print("=" * 150)

frozen = repeat[repeat["_frozen39"]].copy()
frozen["analysis_source"] = "FROZEN_39"

# Match rescued transition back to canonical 92-row repeat record.
added_rows = []

for _, rr in safe_rescue.iterrows():

    hit = repeat[
        repeat["transition_id"].astype(str).eq(
            str(rr["transition_id"])
        )
    ].copy()

    if hit.empty:
        hit = repeat[
            repeat["_pair_key"].eq(rr["_pair_key"])
        ].copy()

    if len(hit) != 1:
        print(
            "WARNING rescue canonical match count:",
            rr["driver_name"],
            len(hit)
        )
        continue

    row = hit.iloc[0].copy()

    # performance remains canonical from repeat inventory
    # overwrite / supply physical values only from rescued evidence

    mapping = {
        "delta_track_temp_c":
            "delta_track_temp_c",

        "delta_air_temp_c":
            "delta_air_temp_c",

        "delta_dewpoint_c":
            "delta_dewpoint_c",

        "delta_relative_humidity_pct":
            "delta_relative_humidity_pct",

        "delta_pressure_hpa":
            "delta_pressure_hpa",

        "delta_air_density_kg_m3":
            "delta_air_density_kg_m3",

        "delta_wind_speed_ms":
            "delta_wind_speed_ms",

        "delta_gust_ms":
            "delta_gust_ms",

        "delta_cloud_cover_pct":
            "delta_cloud_cover_pct",

        "delta_shortwave_radiation_wm2":
            "delta_shortwave_radiation_wm2",
    }

    for dest, src in mapping.items():
        if src in rr.index:
            row[dest] = rr[src]

    # endpoint physical states where columns exist
    endpoint_mapping = {
        "previous_track_temp_c":
            "before_track_temp_c",
        "next_track_temp_c":
            "after_track_temp_c",

        "previous_air_temp_c":
            "before_air_temp_c",
        "next_air_temp_c":
            "after_air_temp_c",

        "previous_dewpoint_c":
            "before_dewpoint_c",
        "next_dewpoint_c":
            "after_dewpoint_c",

        "previous_relative_humidity_pct":
            "before_relative_humidity_pct",
        "next_relative_humidity_pct":
            "after_relative_humidity_pct",

        "previous_pressure_hpa":
            "before_pressure_hpa",
        "next_pressure_hpa":
            "after_pressure_hpa",

        "previous_air_density_kg_m3":
            "before_air_density_kg_m3",
        "next_air_density_kg_m3":
            "after_air_density_kg_m3",

        "previous_wind_speed_ms":
            "before_wind_speed_ms",
        "next_wind_speed_ms":
            "after_wind_speed_ms",

        "previous_gust_ms":
            "before_gust_ms",
        "next_gust_ms":
            "after_gust_ms",

        "previous_shortwave_radiation_wm2":
            "before_shortwave_radiation_wm2",
        "next_shortwave_radiation_wm2":
            "after_shortwave_radiation_wm2",

        "previous_cloud_cover_pct":
            "before_cloud_cover_pct",
        "next_cloud_cover_pct":
            "after_cloud_cover_pct",
    }

    for dest, src in endpoint_mapping.items():
        if dest in row.index and src in rr.index:
            row[dest] = rr[src]

    row["physical_link_quality"] = (
        "PUBLIC_CHRONOLOGY_FULL_ENV_RESCUE"
    )

    row["analysis_source"] = "R5_2_PUBLIC_RESCUE"
    row["in_frozen_39"] = False

    added_rows.append(row)

added = pd.DataFrame(added_rows)

combined = pd.concat(
    [frozen, added],
    ignore_index=True,
    sort=False,
)

print("FROZEN ROWS:", len(frozen))
print("RESCUE ADDED:", len(added))
print("COMBINED ROWS:", len(combined))

print("\nADDED:")
if not added.empty:
    print(
        added[
            [
                "year",
                "car_number",
                "driver_name",
                "delta_four_lap_average_speed_mph",
                "delta_track_temp_c",
                "delta_air_density_kg_m3",
                "delta_gust_ms",
                "delta_shortwave_radiation_wm2",
            ]
        ].to_string(index=False)
    )

COMBINED_FILE = OUT / "r5_2_repeat_analysis_set_v1.csv"
combined.to_csv(COMBINED_FILE, index=False)

# ------------------------------------------------------------------
# helpers for model comparison
# ------------------------------------------------------------------

def fit_zero(X, y):
    b, *_ = np.linalg.lstsq(X, y, rcond=None)
    return b

def metrics(y, p):
    e = p - y
    return (
        np.mean(np.abs(e)),
        np.sqrt(np.mean(e**2)),
        np.mean(e),
    )

def evaluate(dataset, label, features):

    cols = (
        ["year", "delta_four_lap_average_speed_mph"]
        + features
    )

    d = dataset[cols].copy()

    for c in (
        ["delta_four_lap_average_speed_mph"]
        + features
    ):
        d[c] = pd.to_numeric(d[c], errors="coerce")

    d = d.dropna()

    if len(d) < 10:
        return None

    y = d[
        "delta_four_lap_average_speed_mph"
    ].to_numpy(float)

    X = d[features].to_numpy(float)

    beta_all = fit_zero(X, y)

    pred = np.full(len(d), np.nan)

    for yr in sorted(d["year"].dropna().unique()):

        train = d["year"] != yr
        test = d["year"] == yr

        if train.sum() <= len(features):
            continue

        beta = fit_zero(
            d.loc[train, features].to_numpy(float),
            d.loc[
                train,
                "delta_four_lap_average_speed_mph"
            ].to_numpy(float),
        )

        pred[test] = (
            d.loc[test, features].to_numpy(float)
            @ beta
        )

    valid = ~np.isnan(pred)

    mae, rmse, bias = metrics(
        y[valid],
        pred[valid]
    )

    base_mae, base_rmse, _ = metrics(
        y[valid],
        np.zeros(valid.sum())
    )

    out = {
        "dataset": label,
        "model": "+".join(features),
        "n": len(d),
        "loyo_n": int(valid.sum()),
        "mae": mae,
        "rmse": rmse,
        "bias": bias,
        "no_change_mae": base_mae,
        "no_change_rmse": base_rmse,
        "beats_no_change_mae":
            mae < base_mae,
        "beats_no_change_rmse":
            rmse < base_rmse,
    }

    for f, b in zip(features, beta_all):
        out["beta_" + f] = b

    return out


# ------------------------------------------------------------------
# 3. old vs rescued model comparison
# ------------------------------------------------------------------

print("\n" + "=" * 150)
print("PART 3 — OLD 39 VS R5.2 RESCUED MODEL COMPARISON")
print("=" * 150)

models = {
    "TRACK_ONLY": [
        "delta_track_temp_c"
    ],

    "TRACK_GUST": [
        "delta_track_temp_c",
        "delta_gust_ms",
    ],

    "TRACK_DENSITY": [
        "delta_track_temp_c",
        "delta_air_density_kg_m3",
    ],

    "TRACK_SHORTWAVE": [
        "delta_track_temp_c",
        "delta_shortwave_radiation_wm2",
    ],

    "DENSITY_ONLY": [
        "delta_air_density_kg_m3"
    ],

    "SHORTWAVE_ONLY": [
        "delta_shortwave_radiation_wm2"
    ],
}

results = []

for dset, name in [
    (frozen, "FROZEN_39"),
    (combined, "R5_2_COMBINED"),
]:

    for model_name, feats in models.items():

        r = evaluate(
            dset,
            name,
            feats
        )

        if r is not None:
            r["model_name"] = model_name
            results.append(r)

res = pd.DataFrame(results)

showcols = [
    "dataset",
    "model_name",
    "n",
    "mae",
    "rmse",
    "bias",
    "no_change_mae",
    "no_change_rmse",
    "beats_no_change_mae",
    "beats_no_change_rmse",
]

print(
    res[showcols]
    .sort_values(["dataset", "mae"])
    .round(6)
    .to_string(index=False)
)

# ------------------------------------------------------------------
# 4. track relationship diagnostics
# ------------------------------------------------------------------

print("\n" + "=" * 150)
print("PART 4 — TRACK TEMP SIGN STABILITY")
print("=" * 150)

for dset, name in [
    (frozen, "FROZEN_39"),
    (combined, "R5_2_COMBINED"),
]:

    d = dset[
        [
            "delta_four_lap_average_speed_mph",
            "delta_track_temp_c",
        ]
    ].copy()

    d.iloc[:, 0] = pd.to_numeric(
        d.iloc[:, 0], errors="coerce"
    )
    d.iloc[:, 1] = pd.to_numeric(
        d.iloc[:, 1], errors="coerce"
    )

    d = d.dropna()

    y = d[
        "delta_four_lap_average_speed_mph"
    ].to_numpy(float)

    x = d[
        "delta_track_temp_c"
    ].to_numpy(float)

    pear = np.corrcoef(x, y)[0, 1]

    spear = pd.Series(x).corr(
        pd.Series(y),
        method="spearman"
    )

    beta = np.sum(x * y) / np.sum(x * x)

    rng = np.random.default_rng(500)
    boots = []

    for _ in range(10000):

        idx = rng.integers(
            0,
            len(d),
            len(d)
        )

        xb = x[idx]
        yb = y[idx]

        den = np.sum(xb * xb)

        if den > 0:
            boots.append(
                np.sum(xb * yb) / den
            )

    boots = np.asarray(boots)

    print("\n", name)
    print("N =", len(d))
    print("Pearson =", round(pear, 6))
    print("Spearman =", round(spear, 6))
    print("Zero-intercept beta =", round(beta, 6))
    print(
        "Bootstrap 95% =",
        round(np.percentile(boots, 2.5), 6),
        "to",
        round(np.percentile(boots, 97.5), 6)
    )
    print(
        "P(beta < 0) =",
        round(np.mean(boots < 0), 6)
    )

# ------------------------------------------------------------------
# outputs
# ------------------------------------------------------------------

RESULT_FILE = OUT / "r5_2_old_vs_rescued_model_comparison_v1.csv"
res.to_csv(RESULT_FILE, index=False)

print("\n" + "=" * 150)
print("OUTPUTS")
print("=" * 150)
print(COMBINED_FILE.relative_to(ROOT))
print(RESULT_FILE.relative_to(ROOT))

print("\nR5_2_RESCUED_ANALYSIS_COMPARE_V1_COMPLETE")
