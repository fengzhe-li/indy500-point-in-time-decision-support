from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path("/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈")
OUT = ROOT / "r5_2/manual"

RESID_FILE = OUT / "probabilistic_physics_loyo_residuals_v1.csv"
BOOT_FILE = OUT / "probabilistic_physics_coefficient_bootstrap_v1.csv"

df = pd.read_csv(RESID_FILE)
boots = pd.read_csv(BOOT_FILE)

Y = "delta_four_lap_average_speed_mph"
TRACK = "delta_track_temp_c"
AIR = "delta_air_temp_c"
R = "residual_loyo_raw"

for c in [Y, TRACK, AIR, R]:
    df[c] = pd.to_numeric(df[c], errors="coerce")

B = boots[
    ["beta_track_temp", "beta_ambient_temp"]
].to_numpy(float)

d = df[
    [Y, TRACK, AIR, R]
].dropna().copy()

raw = d[R].to_numpy(float)

# ============================================================
# THREE RESIDUAL UNCERTAINTY CANDIDATES
# ============================================================

# A. current method
median_centered = raw - np.median(raw)

# B. zero expected residual
mean_centered = raw - np.mean(raw)

# C. symmetric empirical uncertainty
# retain empirical |residual| magnitudes but randomly assign +/-.
abs_residual = np.abs(raw - np.median(raw))

rng = np.random.default_rng(500)

NSIM = 20000


def simulate_residual(method, n):

    if method == "MEDIAN_CENTERED":

        idx = rng.integers(0, len(median_centered), n)
        return median_centered[idx]

    if method == "MEAN_CENTERED":

        idx = rng.integers(0, len(mean_centered), n)
        return mean_centered[idx]

    if method == "SYMMETRIC_EMPIRICAL":

        idx = rng.integers(0, len(abs_residual), n)
        signs = rng.choice([-1.0, 1.0], size=n)

        return abs_residual[idx] * signs

    raise ValueError(method)


METHODS = [
    "MEDIAN_CENTERED",
    "MEAN_CENTERED",
    "SYMMETRIC_EMPIRICAL",
]


# ============================================================
# PART 1 — RESIDUAL DISTRIBUTION CHECK
# ============================================================

print("=" * 150)
print("PART 1 — RESIDUAL UNCERTAINTY DISTRIBUTIONS")
print("=" * 150)

for method in METHODS:

    sim = simulate_residual(method, 200000)

    print("\nMETHOD:", method)
    print("mean =", round(np.mean(sim), 6))
    print("median =", round(np.median(sim), 6))
    print("SD =", round(np.std(sim, ddof=1), 6))

    print(
        "5/25/50/75/95 =",
        np.round(
            np.percentile(
                sim,
                [5, 25, 50, 75, 95]
            ),
            6
        )
    )

    print(
        "P(residual > 0) =",
        round(np.mean(sim > 0), 6)
    )


# ============================================================
# PART 2 — HISTORICAL PROBABILISTIC BACKTEST
# ============================================================

print("\n" + "=" * 150)
print("PART 2 — UNCERTAINTY METHOD BACKTEST")
print("=" * 150)

summary_rows = []

for method in METHODS:

    rows = []

    for _, row in d.iterrows():

        x = np.array(
            [row[TRACK], row[AIR]],
            dtype=float
        )

        bidx = rng.integers(
            0,
            len(B),
            NSIM
        )

        physics = B[bidx] @ x

        uncertainty = simulate_residual(
            method,
            NSIM
        )

        sim = physics + uncertainty

        actual = row[Y]

        q05, q10, q50, q90, q95 = np.percentile(
            sim,
            [5, 10, 50, 90, 95]
        )

        rows.append({
            "actual": actual,
            "predicted_median": q50,
            "p_improve": np.mean(sim > 0),

            "inside_80":
                q10 <= actual <= q90,

            "inside_90":
                q05 <= actual <= q95,

            "actual_improve":
                float(actual > 0),
        })

    bt = pd.DataFrame(rows)

    # Brier score for probability of improvement
    brier = np.mean(
        (
            bt["p_improve"]
            -
            bt["actual_improve"]
        ) ** 2
    )

    summary_rows.append({
        "method": method,
        "coverage_80":
            bt["inside_80"].mean(),

        "coverage_90":
            bt["inside_90"].mean(),

        "median_absolute_point_error":
            np.median(
                np.abs(
                    bt["predicted_median"]
                    -
                    bt["actual"]
                )
            ),

        "brier_score":
            brier,

        "mean_p_improve":
            bt["p_improve"].mean(),
    })

summary = pd.DataFrame(summary_rows)

print(
    summary
    .round(6)
    .to_string(index=False)
)


# ============================================================
# PART 3 — ZERO-STATE TOTAL DISTRIBUTION
#
# Critical final scientific sanity test.
# ============================================================

print("\n" + "=" * 150)
print("PART 3 — ZERO-STATE TOTAL-DISTRIBUTION SANITY")
print("=" * 150)

ZERO_X = np.array([0.0, 0.0])

for method in METHODS:

    bidx = rng.integers(
        0,
        len(B),
        200000
    )

    physics = B[bidx] @ ZERO_X

    uncertainty = simulate_residual(
        method,
        200000
    )

    total = physics + uncertainty

    print("\nMETHOD:", method)

    print(
        "expected total Δspeed at zero physical change =",
        round(np.mean(total), 6)
    )

    print(
        "median total Δspeed at zero physical change =",
        round(np.median(total), 6)
    )

    print(
        "P(improve) at zero physical change =",
        round(np.mean(total > 0), 6)
    )


# ============================================================
# PART 4 — RECOMMENDED UNCERTAINTY RULE
# ============================================================

print("\n" + "=" * 150)
print("PART 4 — SELECTION TABLE")
print("=" * 150)

print(
    summary
    .sort_values(
        [
            "brier_score",
            "median_absolute_point_error"
        ]
    )
    .round(6)
    .to_string(index=False)
)

summary.to_csv(
    OUT / "zero_centered_uncertainty_calibration_v1.csv",
    index=False
)

print("\nZERO_CENTERED_UNCERTAINTY_CALIBRATION_V1_COMPLETE")
