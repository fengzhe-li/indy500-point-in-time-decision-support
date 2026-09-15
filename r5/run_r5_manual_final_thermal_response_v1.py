from pathlib import Path
import csv
import json
import math

import numpy as np
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.model_selection import LeaveOneGroupOut
from sklearn.metrics import mean_absolute_error, mean_squared_error


ROOT = Path("/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈")

REPEAT = ROOT / "r5/output/r5_manual_same_car_repeat_physics_v1.csv"
WITHIN = ROOT / "r5/output/r5_manual_within_run_fade_physics_v1.csv"

OUT_PARAMS = ROOT / "r5/output/r5_final_thermal_response_parameters_v1.csv"
OUT_REPEAT = ROOT / "r5/output/r5_final_thermal_response_repeat_predictions_v1.csv"
OUT_BOOT = ROOT / "r5/output/r5_final_thermal_response_bootstrap_v1.csv"
OUT_SUPPORT = ROOT / "r5/output/r5_final_thermal_fade_support_v1.csv"
OUT_CONTRACT = ROOT / "r5/output/r5_final_thermal_response_contract_v1.json"
OUT_REPORT = ROOT / "r5/output/r5_final_thermal_response_report_v1.json"


SEED = 500
BOOTSTRAPS = 10000

rng = np.random.default_rng(SEED)


def clean(v):
    return "" if v is None else str(v).strip()


def num(v):
    s = clean(v)
    if not s:
        return None
    try:
        x = float(s)
        return x if math.isfinite(x) else None
    except Exception:
        return None


def read_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        r = csv.DictReader(f)
        return r.fieldnames or [], list(r)


def write_csv(path, rows):
    if not rows:
        return

    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=list(rows[0].keys())
        )
        writer.writeheader()
        writer.writerows(rows)


_, repeat_rows = read_csv(REPEAT)
_, within_rows = read_csv(WITHIN)


# =====================================================================
# SAME-CAR PRIMARY DATA
# =====================================================================

usable = []

for r in repeat_rows:

    dx = num(r.get("delta_track_temp_c"))
    dy = num(r.get("delta_four_lap_average_speed_mph"))

    if dx is None or dy is None:
        continue

    usable.append({
        "year": clean(r["year"]),
        "driver_name": clean(r["driver_name"]),
        "car_number": clean(r["car_number"]),
        "before_attempt_id": clean(r["before_attempt_id"]),
        "after_attempt_id": clean(r["after_attempt_id"]),
        "delta_track_temp_c": dx,
        "delta_speed_mph": dy,
    })


X = np.array(
    [[r["delta_track_temp_c"]] for r in usable],
    dtype=float
)

y = np.array(
    [r["delta_speed_mph"] for r in usable],
    dtype=float
)

groups = np.array(
    [r["year"] for r in usable]
)


# =====================================================================
# SIMPLE PHYSICAL RESPONSE
#
# Δspeed = intercept + beta_track * Δtrack_temperature
# =====================================================================

model = LinearRegression()
model.fit(X, y)

beta = float(model.coef_[0])
intercept = float(model.intercept_)

fitted = model.predict(X)
residuals = y - fitted

residual_sd = float(np.std(residuals, ddof=2))


# =====================================================================
# LOYO
# =====================================================================

logo = LeaveOneGroupOut()

pred = np.full(len(y), np.nan)

for train, test in logo.split(X, y, groups):

    m = Ridge(alpha=1.0)
    m.fit(X[train], y[train])

    pred[test] = m.predict(X[test])


mask = np.isfinite(pred)

loyo_mae = float(
    mean_absolute_error(y[mask], pred[mask])
)

loyo_rmse = float(
    np.sqrt(
        mean_squared_error(y[mask], pred[mask])
    )
)

loyo_bias = float(
    np.mean(y[mask] - pred[mask])
)


# =====================================================================
# NO-CHANGE BASELINE
# =====================================================================

zero_pred = np.zeros_like(y)

zero_mae = float(
    mean_absolute_error(y, zero_pred)
)

zero_rmse = float(
    np.sqrt(mean_squared_error(y, zero_pred))
)


# =====================================================================
# BOOTSTRAP BETA
# =====================================================================

boot_rows = []
boot_beta = []

n = len(usable)

for b in range(BOOTSTRAPS):

    idx = rng.integers(
        0,
        n,
        size=n
    )

    xb = X[idx]
    yb = y[idx]

    if np.std(xb[:, 0]) < 1e-12:
        continue

    m = LinearRegression()
    m.fit(xb, yb)

    b_beta = float(m.coef_[0])
    b_intercept = float(m.intercept_)

    boot_beta.append(b_beta)

    boot_rows.append({
        "bootstrap_iteration": b,
        "beta_track_mph_per_c": b_beta,
        "intercept_mph": b_intercept,
    })


boot_beta = np.asarray(
    boot_beta,
    dtype=float
)

beta_q025 = float(np.quantile(boot_beta, 0.025))
beta_q50 = float(np.quantile(boot_beta, 0.50))
beta_q975 = float(np.quantile(boot_beta, 0.975))

p_beta_negative = float(
    np.mean(boot_beta < 0)
)


# =====================================================================
# WITHIN-RUN PHYSICAL SUPPORT
#
# Fade = lap4 - lap1
# Negative = greater degradation.
# =====================================================================

fade_x = []
fade_y = []

for r in within_rows:

    temp = num(r.get("track_temp_c"))
    fade = num(r.get("lap1_to_lap4_delta_mph"))

    if temp is not None and fade is not None:
        fade_x.append(temp)
        fade_y.append(fade)


fade_x = np.asarray(fade_x)
fade_y = np.asarray(fade_y)

fade_corr = float(
    np.corrcoef(fade_x, fade_y)[0, 1]
)

fade_model = LinearRegression()

fade_model.fit(
    fade_x.reshape(-1, 1),
    fade_y
)

fade_beta = float(
    fade_model.coef_[0]
)

fade_intercept = float(
    fade_model.intercept_
)


# =====================================================================
# THERMAL EFFECT TABLE
# =====================================================================

effect_rows = []

for delta_c in [
    -15,
    -10,
    -7.5,
    -5,
    -2.5,
    0,
    2.5,
    5,
    7.5,
    10,
    15,
]:

    central = intercept + beta * delta_c

    low = intercept + beta_q025 * delta_c
    high = intercept + beta_q975 * delta_c

    if low > high:
        low, high = high, low

    effect_rows.append({
        "delta_track_temp_c": delta_c,
        "predicted_delta_speed_mph": central,
        "bootstrap_beta_based_low_mph": low,
        "bootstrap_beta_based_high_mph": high,
    })


# =====================================================================
# ROW-LEVEL PREDICTIONS
# =====================================================================

prediction_rows = []

for i, r in enumerate(usable):

    prediction_rows.append({
        **r,
        "fitted_full_sample_delta_speed_mph": fitted[i],
        "loyo_predicted_delta_speed_mph": (
            pred[i]
            if np.isfinite(pred[i])
            else ""
        ),
        "loyo_error_actual_minus_predicted_mph": (
            y[i] - pred[i]
            if np.isfinite(pred[i])
            else ""
        ),
    })


# =====================================================================
# SAVE
# =====================================================================

parameter_rows = [{
    "model":
        "SAME_CAR_TRACK_TEMPERATURE_RESPONSE",

    "formula":
        "delta_speed_mph = intercept + beta_track * delta_track_temp_c",

    "n":
        len(usable),

    "intercept_mph":
        intercept,

    "beta_track_mph_per_c":
        beta,

    "beta_bootstrap_q025":
        beta_q025,

    "beta_bootstrap_median":
        beta_q50,

    "beta_bootstrap_q975":
        beta_q975,

    "bootstrap_probability_beta_negative":
        p_beta_negative,

    "residual_sd_mph":
        residual_sd,

    "loyo_mae_mph":
        loyo_mae,

    "loyo_rmse_mph":
        loyo_rmse,

    "loyo_bias_mph":
        loyo_bias,

    "zero_change_baseline_mae_mph":
        zero_mae,

    "zero_change_baseline_rmse_mph":
        zero_rmse,

    "fast_friday_used":
        False,
}]


write_csv(
    OUT_PARAMS,
    parameter_rows
)

write_csv(
    OUT_REPEAT,
    prediction_rows
)

write_csv(
    OUT_BOOT,
    boot_rows
)

write_csv(
    OUT_SUPPORT,
    effect_rows
)


contract = {
    "status":
        "R5_THERMAL_RESPONSE_MODEL_ESTIMATED",

    "primary_response_model":
        "SAME_CAR_DELTA_SPEED_FROM_DELTA_TRACK_TEMPERATURE",

    "formula":
        (
            "future_speed = current_qualifying_speed + "
            "predicted_delta_speed(delta_track_temperature)"
        ),

    "car_baseline":
        "CURRENT_SAME_DAY_QUALIFYING_RESULT",

    "fast_friday_primary_baseline":
        False,

    "physical_mechanism": {
        "primary":
            "track_surface_temperature",

        "supporting_forcing_for_future_track_state": [
            "shortwave solar radiation",
            "cloud cover",
            "ambient temperature",
            "wind",
            "solar geometry",
        ],

        "tyre_temperature_directly_observed":
            False,

        "tyre_interpretation":
            (
                "track-temperature-dependent thermal working "
                "condition proxy only"
            ),
    },

    "auxiliary_physical_evidence": {
        "within_run_four_lap_fade":
            True,

        "first_run_chronological_thermal_sweep":
            True,

        "same_car_repeat_attempts":
            True,
    },

    "important_boundary":
        (
            "The model predicts within-car performance change, "
            "not absolute car capability from weather alone."
        ),
}


OUT_CONTRACT.write_text(
    json.dumps(
        contract,
        indent=2,
        ensure_ascii=False
    ),
    encoding="utf-8"
)


report = {
    "status":
        "R5_FINAL_THERMAL_RESPONSE_ESTIMATION_COMPLETE",

    "same_car_n":
        len(usable),

    "beta_track_mph_per_c":
        beta,

    "beta_95_bootstrap_interval": [
        beta_q025,
        beta_q975,
    ],

    "bootstrap_probability_beta_negative":
        p_beta_negative,

    "loyo": {
        "mae_mph":
            loyo_mae,

        "rmse_mph":
            loyo_rmse,

        "bias_mph":
            loyo_bias,
    },

    "zero_change_reference": {
        "mae_mph":
            zero_mae,

        "rmse_mph":
            zero_rmse,
    },

    "within_run_support": {
        "n":
            len(fade_x),

        "track_temp_vs_fade_correlation":
            fade_corr,

        "fade_beta_mph_per_c":
            fade_beta,
    },

    "fast_friday_used":
        False,
}


OUT_REPORT.write_text(
    json.dumps(
        report,
        indent=2,
        ensure_ascii=False
    ),
    encoding="utf-8"
)


# =====================================================================
# CONSOLE
# =====================================================================

print("=" * 145)
print("R5 — FINAL THERMAL RESPONSE ESTIMATION")
print("=" * 145)
print()

print("PRIMARY SAME-CAR RESPONSE")
print("-" * 145)

print(f"N same-car transitions:                     {len(usable)}")
print(f"beta track-temperature:                     {beta:+.6f} mph / °C")
print(f"intercept:                                  {intercept:+.6f} mph")
print(
    f"bootstrap 95% beta interval:                "
    f"[{beta_q025:+.6f}, {beta_q975:+.6f}]"
)
print(
    f"P(beta < 0):                                "
    f"{p_beta_negative:.4f}"
)

print()
print("PREDICTIVE PERFORMANCE")
print("-" * 145)

print(f"LOYO MAE:                                   {loyo_mae:.6f} mph")
print(f"LOYO RMSE:                                  {loyo_rmse:.6f} mph")
print(f"LOYO bias:                                  {loyo_bias:+.6f} mph")
print()

print(f"No-change baseline MAE:                     {zero_mae:.6f} mph")
print(f"No-change baseline RMSE:                    {zero_rmse:.6f} mph")

print()
print("WITHIN-RUN SUPPORT")
print("-" * 145)

print(f"N four-lap runs:                            {len(fade_x)}")
print(f"track temp vs Lap1→Lap4 fade correlation:   {fade_corr:+.6f}")
print(f"fade response per +1°C track temp:          {fade_beta:+.6f} mph")

print()
print("THERMAL EFFECT EXAMPLES")
print("-" * 145)

for delta_c in [-10, -5, 5, 10]:

    central = intercept + beta * delta_c

    print(
        f"Δtrack={delta_c:+5.1f}°C "
        f"→ predicted Δspeed={central:+.4f} mph"
    )

print()
print("OUTPUTS")
print("-" * 145)

for p in [
    OUT_PARAMS,
    OUT_REPEAT,
    OUT_BOOT,
    OUT_SUPPORT,
    OUT_CONTRACT,
    OUT_REPORT,
]:
    print(p.relative_to(ROOT))

print()
print("FAST FRIDAY USED: NO")
print("R5_FINAL_THERMAL_RESPONSE_ESTIMATION_COMPLETE")
