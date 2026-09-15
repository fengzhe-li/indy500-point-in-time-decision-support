from pathlib import Path
import pandas as pd
import numpy as np
import json

ROOT = Path("/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈")
OUT = ROOT / "r5_2/manual"

FUTURE_MODEL_FILE = OUT / "extended_invariant_future_state_model_v3.json"
HORIZON_FILE = OUT / "extended_future_state_horizon_uncertainty_v3.csv"
TRACK_RESID_FILE = OUT / "extended_future_state_standardized_residuals_v3.csv"

PERF_BOOT_FILE = OUT / "probabilistic_physics_coefficient_bootstrap_v1.csv"
PERF_RESID_FILE = OUT / "probabilistic_physics_loyo_residuals_v1.csv"

# ============================================================
# load frozen components
# ============================================================

with open(FUTURE_MODEL_FILE, "r", encoding="utf-8") as f:
    future_model = json.load(f)

hs = pd.read_csv(HORIZON_FILE)
track_std = pd.read_csv(TRACK_RESID_FILE)

perf_boot = pd.read_csv(PERF_BOOT_FILE)
perf_resid = pd.read_csv(PERF_RESID_FILE)

# ============================================================
# future-track model
# ============================================================

coef = future_model["coefficients"]

B_H = float(coef["h"])
B_STATE = float(coef["h_x_track_state"])
B_AMBIENT = float(coef["delta_ambient_temp_c"])

TRACK_REF = float(
    future_model["track_reference_c"]
)

# ============================================================
# empirical track uncertainty scale
#
# Use observed LOYO residual SD by validated horizon,
# anchored at wait=0 -> sigma=0.
# ============================================================

hs["horizon_min"] = pd.to_numeric(
    hs["horizon_min"], errors="coerce"
)

hs["residual_sd"] = pd.to_numeric(
    hs["residual_sd"], errors="coerce"
)

sigma_x = np.concatenate([
    np.array([0.0]),
    hs["horizon_min"].to_numpy(float)
])

sigma_y = np.concatenate([
    np.array([0.0]),
    hs["residual_sd"].to_numpy(float)
])

order = np.argsort(sigma_x)
sigma_x = sigma_x[order]
sigma_y = sigma_y[order]


def track_sigma(wait_min):
    wait_min = float(wait_min)

    if wait_min < 0:
        raise ValueError("wait_min must be >= 0")

    if wait_min > 180:
        raise ValueError(
            "Validated future-state horizon is 0–180 minutes."
        )

    return float(
        np.interp(
            wait_min,
            sigma_x,
            sigma_y
        )
    )

# Standardized empirical track residual shape
track_pool = pd.to_numeric(
    track_std["standardized_residual"],
    errors="coerce"
).dropna().to_numpy(float)

track_pool = (
    track_pool
    - np.median(track_pool)
)

track_pool_sd = np.std(
    track_pool,
    ddof=1
)

if track_pool_sd <= 0:
    raise RuntimeError(
        "Invalid track residual pool SD"
    )

# normalize to SD approximately 1
track_pool = (
    track_pool
    / track_pool_sd
)

# ============================================================
# performance coefficient bootstrap
# ============================================================

PERF_B = perf_boot[
    [
        "beta_track_temp",
        "beta_ambient_temp",
    ]
].apply(
    pd.to_numeric,
    errors="coerce"
).dropna().to_numpy(float)

# ============================================================
# symmetric empirical performance uncertainty
#
# no generic reattempt bonus:
# residual distribution mean/median approximately zero.
# ============================================================

raw_perf_resid = pd.to_numeric(
    perf_resid["residual_loyo_raw"],
    errors="coerce"
).dropna().to_numpy(float)

perf_center = np.median(
    raw_perf_resid
)

perf_abs = np.abs(
    raw_perf_resid - perf_center
)

# ============================================================
# deterministic mean future-track function
# ============================================================

def mean_delta_track(
    wait_min,
    current_track_c,
    delta_ambient_c
):
    h = wait_min / 60.0

    return (
        B_H * h
        +
        B_STATE
        * h
        * (current_track_c - TRACK_REF)
        +
        B_AMBIENT
        * delta_ambient_c
    )

# ============================================================
# simulation for one wait time
# ============================================================

def simulate_wait(
    wait_min,
    current_track_c,
    current_ambient_c,
    future_ambient_c,
    rng,
    nsim=20000
):
    wait_min = float(wait_min)

    delta_ambient = (
        float(future_ambient_c)
        -
        float(current_ambient_c)
    )

    # ----------------------------------------
    # future track state
    # ----------------------------------------

    mu_dt = mean_delta_track(
        wait_min,
        current_track_c,
        delta_ambient
    )

    sig_track = track_sigma(
        wait_min
    )

    if wait_min == 0:
        track_noise = np.zeros(nsim)

    else:
        idx = rng.integers(
            0,
            len(track_pool),
            nsim
        )

        track_noise = (
            track_pool[idx]
            * sig_track
        )

    delta_track_draws = (
        mu_dt
        +
        track_noise
    )

    # ----------------------------------------
    # performance coefficient uncertainty
    # ----------------------------------------

    bidx = rng.integers(
        0,
        len(PERF_B),
        nsim
    )

    beta_draws = PERF_B[bidx]

    physical_perf = (
        beta_draws[:, 0]
        * delta_track_draws
        +
        beta_draws[:, 1]
        * delta_ambient
    )

    # ----------------------------------------
    # intrinsic performance uncertainty
    #
    # symmetric empirical distribution
    # ----------------------------------------

    ridx = rng.integers(
        0,
        len(perf_abs),
        nsim
    )

    signs = rng.choice(
        [-1.0, 1.0],
        size=nsim
    )

    perf_noise = (
        perf_abs[ridx]
        * signs
    )

    total = (
        physical_perf
        +
        perf_noise
    )

    q05, q10, q50, q90, q95 = np.percentile(
        total,
        [5, 10, 50, 90, 95]
    )

    return {
        "wait_minutes":
            wait_min,

        "future_ambient_temp_c":
            float(future_ambient_c),

        "delta_ambient_temp_c":
            delta_ambient,

        "expected_delta_track_temp_c":
            float(mu_dt),

        "track_temp_uncertainty_sd_c":
            float(sig_track),

        "expected_delta_speed_mph":
            float(np.mean(physical_perf)),

        "median_delta_speed_mph":
            float(q50),

        "lower_80_mph":
            float(q10),

        "upper_80_mph":
            float(q90),

        "lower_90_mph":
            float(q05),

        "upper_90_mph":
            float(q95),

        "p_improve":
            float(np.mean(total > 0)),
    }

# ============================================================
# continuous curve engine
# ============================================================

def build_curve(
    current_track_c,
    current_ambient_c,
    ambient_trajectory,
    session_remaining_min,
    nsim=20000,
    seed=500
):
    if session_remaining_min > 180:
        raise ValueError(
            "Current validated horizon is 180 minutes."
        )

    if session_remaining_min < 0:
        raise ValueError(
            "session_remaining_min must be >= 0"
        )

    traj = ambient_trajectory.copy()

    traj["wait_minutes"] = pd.to_numeric(
        traj["wait_minutes"],
        errors="coerce"
    )

    traj["future_ambient_temp_c"] = pd.to_numeric(
        traj["future_ambient_temp_c"],
        errors="coerce"
    )

    traj = traj.dropna().sort_values(
        "wait_minutes"
    )

    if traj.empty:
        raise ValueError(
            "Ambient trajectory is empty."
        )

    if traj["wait_minutes"].min() > 0:
        traj = pd.concat(
            [
                pd.DataFrame({
                    "wait_minutes": [0.0],
                    "future_ambient_temp_c": [
                        current_ambient_c
                    ],
                }),
                traj,
            ],
            ignore_index=True
        )

    waits = np.arange(
        0,
        int(session_remaining_min) + 1,
        1
    )

    future_ambient = np.interp(
        waits,
        traj["wait_minutes"],
        traj["future_ambient_temp_c"]
    )

    rng = np.random.default_rng(seed)

    rows = []

    for w, a in zip(
        waits,
        future_ambient
    ):
        rows.append(
            simulate_wait(
                wait_min=w,
                current_track_c=current_track_c,
                current_ambient_c=current_ambient_c,
                future_ambient_c=a,
                rng=rng,
                nsim=nsim
            )
        )

    return pd.DataFrame(rows)

# ============================================================
# scientific sanity checks
# ============================================================

print("=" * 150)
print("PART 1 — FINAL ENGINE COMPONENT CHECK")
print("=" * 150)

print("Future-state model:", future_model["version"])
print("Validated horizon: 0–180 min")
print("Performance bootstrap draws:", len(PERF_B))
print("Track residual pool:", len(track_pool))
print("Performance residual magnitudes:", len(perf_abs))

print("\nEmpirical track sigma anchors:")
for x, y in zip(sigma_x, sigma_y):
    print(
        f"{int(x):3d} min -> {y:.6f} C"
    )

# ============================================================
# zero-wait full engine test
# ============================================================

print("\n" + "=" * 150)
print("PART 2 — ZERO-WAIT FULL ENGINE SANITY")
print("=" * 150)

rng = np.random.default_rng(500)

zero = simulate_wait(
    wait_min=0,
    current_track_c=45.0,
    current_ambient_c=25.0,
    future_ambient_c=25.0,
    rng=rng,
    nsim=100000
)

print(
    "expected_delta_track_temp_c =",
    round(
        zero["expected_delta_track_temp_c"],
        12
    )
)

print(
    "track_temp_uncertainty_sd_c =",
    round(
        zero["track_temp_uncertainty_sd_c"],
        12
    )
)

print(
    "expected physical delta speed =",
    round(
        zero["expected_delta_speed_mph"],
        6
    )
)

print(
    "median total delta speed =",
    round(
        zero["median_delta_speed_mph"],
        6
    )
)

print(
    "P(improve) =",
    round(
        zero["p_improve"],
        6
    )
)

assert abs(
    zero["expected_delta_track_temp_c"]
) < 1e-12

assert abs(
    zero["track_temp_uncertainty_sd_c"]
) < 1e-12

assert abs(
    zero["expected_delta_speed_mph"]
) < 1e-12

print(
    "PASS: wait=0 preserves physical-state anchor"
)

# ============================================================
# create reusable example ambient trajectory template
# ============================================================

TEMPLATE_FILE = (
    OUT /
    "final_curve_ambient_trajectory_template.csv"
)

template = pd.DataFrame({
    "wait_minutes": [
        0, 30, 60, 90,
        120, 150, 180
    ],
    "future_ambient_temp_c": [
        np.nan, np.nan, np.nan, np.nan,
        np.nan, np.nan, np.nan
    ],
})

template.to_csv(
    TEMPLATE_FILE,
    index=False
)

print("\n" + "=" * 150)
print("PART 3 — FINAL ENGINE READY")
print("=" * 150)

print(
    "Ambient trajectory template:",
    TEMPLATE_FILE.relative_to(ROOT)
)

print(
    "\nFINAL_WAIT_PERFORMANCE_ENGINE_V1_READY"
)
