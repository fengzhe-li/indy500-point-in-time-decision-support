from pathlib import Path
import importlib.util
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

ROOT = Path("/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈")
OUT = ROOT / "r5_2/manual"

STATE_FILE = OUT / "track_temperature_state_panel_v1.csv"
ENGINE_FILE = OUT / "build_final_wait_performance_engine_v1.py"

YEAR = 2024
HORIZON_MIN = 180
NSIM = 30000
SEED = 500

# ============================================================
# load engine
# ============================================================

spec = importlib.util.spec_from_file_location(
    "final_engine",
    ENGINE_FILE
)

engine = importlib.util.module_from_spec(spec)
spec.loader.exec_module(engine)

# ============================================================
# load historical physical states
# ============================================================

state = pd.read_csv(STATE_FILE)

state["year"] = pd.to_numeric(
    state["year"],
    errors="coerce"
)

state["time_utc"] = pd.to_datetime(
    state["time_utc"],
    utc=True,
    errors="coerce"
)

for c in [
    "track_c",
    "hrrr_temp_c",
]:
    state[c] = pd.to_numeric(
        state[c],
        errors="coerce"
    )

g = state[
    (state["year"] == YEAR)
    &
    state["time_utc"].notna()
    &
    state["track_c"].notna()
    &
    state["hrrr_temp_c"].notna()
].copy()

g = g.sort_values("time_utc").reset_index(drop=True)

if g.empty:
    raise RuntimeError(
        f"No usable state rows for {YEAR}"
    )

# ============================================================
# find earliest starting point with >=180 min future coverage
# ============================================================

last_time = g["time_utc"].max()

candidates = g[
    (
        last_time
        -
        g["time_utc"]
    ).dt.total_seconds() / 60.0
    >= HORIZON_MIN
].copy()

if candidates.empty:
    raise RuntimeError(
        f"No {YEAR} state has {HORIZON_MIN} min future coverage"
    )

# Prefer a starting point not at the very first instant:
# choose candidate nearest to median candidate time.
mid_time = candidates["time_utc"].median()

candidates["_mid_dist"] = (
    candidates["time_utc"] - mid_time
).abs().dt.total_seconds()

current = (
    candidates
    .sort_values("_mid_dist")
    .iloc[0]
)

current_time = current["time_utc"]
current_track = float(current["track_c"])
current_ambient = float(current["hrrr_temp_c"])

end_time = (
    current_time
    +
    pd.Timedelta(minutes=HORIZON_MIN)
)

# ============================================================
# build real historical ambient trajectory
# ============================================================

future = g[
    (g["time_utc"] >= current_time)
    &
    (g["time_utc"] <= end_time)
].copy()

future["wait_minutes"] = (
    future["time_utc"] - current_time
).dt.total_seconds() / 60.0

traj = future[
    [
        "wait_minutes",
        "hrrr_temp_c",
    ]
].copy()

traj = traj.rename(
    columns={
        "hrrr_temp_c":
            "future_ambient_temp_c"
    }
)

traj = (
    traj.dropna()
    .sort_values("wait_minutes")
    .drop_duplicates(
        "wait_minutes",
        keep="last"
    )
)

# force exact zero anchor
if np.isclose(
    traj["wait_minutes"],
    0
).any():

    traj.loc[
        np.isclose(
            traj["wait_minutes"],
            0
        ),
        "future_ambient_temp_c"
    ] = current_ambient

else:

    traj = pd.concat(
        [
            pd.DataFrame({
                "wait_minutes": [0.0],
                "future_ambient_temp_c": [
                    current_ambient
                ]
            }),
            traj
        ],
        ignore_index=True
    )

# ensure 180-minute endpoint exists
if traj["wait_minutes"].max() < HORIZON_MIN:

    last_temp = float(
        traj.sort_values(
            "wait_minutes"
        ).iloc[-1][
            "future_ambient_temp_c"
        ]
    )

    traj = pd.concat(
        [
            traj,
            pd.DataFrame({
                "wait_minutes": [
                    HORIZON_MIN
                ],
                "future_ambient_temp_c": [
                    last_temp
                ]
            })
        ],
        ignore_index=True
    )

TRAJ_FILE = (
    OUT /
    f"historical_{YEAR}_ambient_trajectory_v1.csv"
)

traj.to_csv(
    TRAJ_FILE,
    index=False
)

# ============================================================
# run final probabilistic curve
# ============================================================

curve = engine.build_curve(
    current_track_c=current_track,
    current_ambient_c=current_ambient,
    ambient_trajectory=traj,
    session_remaining_min=HORIZON_MIN,
    nsim=NSIM,
    seed=SEED
)

# ============================================================
# attach expected absolute physical state
# ============================================================

curve["expected_track_temp_c"] = (
    current_track
    +
    curve["expected_delta_track_temp_c"]
)

# ============================================================
# sanity
# ============================================================

assert curve.iloc[0]["wait_minutes"] == 0
assert abs(
    curve.iloc[0]["expected_delta_track_temp_c"]
) < 1e-12
assert abs(
    curve.iloc[0]["expected_delta_speed_mph"]
) < 1e-12

# ============================================================
# outputs
# ============================================================

CSV_OUT = (
    OUT /
    f"historical_{YEAR}_final_wait_curve_v1.csv"
)

curve.to_csv(
    CSV_OUT,
    index=False
)

# ============================================================
# FIGURE 1 — final Δspeed curve
# ============================================================

FIG1 = (
    OUT /
    f"historical_{YEAR}_final_wait_performance_curve_v1.png"
)

fig, ax = plt.subplots(figsize=(10, 6))

x = curve["wait_minutes"].to_numpy(float)

ax.fill_between(
    x,
    curve["lower_90_mph"],
    curve["upper_90_mph"],
    alpha=0.15,
    label="90% uncertainty interval"
)

ax.fill_between(
    x,
    curve["lower_80_mph"],
    curve["upper_80_mph"],
    alpha=0.25,
    label="80% uncertainty interval"
)

ax.plot(
    x,
    curve["expected_delta_speed_mph"],
    linewidth=2,
    label="Expected physical Δspeed"
)

ax.axhline(
    0,
    linestyle="--",
    linewidth=1,
    label="Current official-result anchor"
)

ax.set_xlabel(
    "Hypothetical wait until reattempt (minutes)"
)

ax.set_ylabel(
    "Δ four-lap average speed (mph)"
)

ax.set_title(
    f"{YEAR} Indy 500 — Physics-Conditioned Performance Change"
)

ax.legend()
ax.grid(alpha=0.2)

fig.tight_layout()

fig.savefig(
    FIG1,
    dpi=180,
    bbox_inches="tight"
)

plt.close(fig)

# ============================================================
# FIGURE 2 — probability curve
# ============================================================

FIG2 = (
    OUT /
    f"historical_{YEAR}_probability_improve_curve_v1.png"
)

fig, ax = plt.subplots(figsize=(10, 5))

ax.plot(
    x,
    curve["p_improve"],
    linewidth=2
)

ax.axhline(
    0.5,
    linestyle="--",
    linewidth=1
)

ax.set_ylim(0, 1)

ax.set_xlabel(
    "Hypothetical wait until reattempt (minutes)"
)

ax.set_ylabel(
    "P(improve current four-lap average)"
)

ax.set_title(
    f"{YEAR} Indy 500 — Probability of Performance Improvement"
)

ax.grid(alpha=0.2)

fig.tight_layout()

fig.savefig(
    FIG2,
    dpi=180,
    bbox_inches="tight"
)

plt.close(fig)

# ============================================================
# FIGURE 3 — projected physical state
# ============================================================

FIG3 = (
    OUT /
    f"historical_{YEAR}_physical_state_curve_v1.png"
)

fig, ax = plt.subplots(figsize=(10, 5))

ax.plot(
    x,
    curve["expected_track_temp_c"],
    linewidth=2,
    label="Expected track temperature"
)

ax.plot(
    x,
    curve["future_ambient_temp_c"],
    linewidth=2,
    label="Ambient temperature"
)

ax.set_xlabel(
    "Hypothetical wait (minutes)"
)

ax.set_ylabel(
    "Temperature (°C)"
)

ax.set_title(
    f"{YEAR} Indy 500 — Projected Physical State"
)

ax.legend()
ax.grid(alpha=0.2)

fig.tight_layout()

fig.savefig(
    FIG3,
    dpi=180,
    bbox_inches="tight"
)

plt.close(fig)

# ============================================================
# summary points
# ============================================================

best_mean = curve.loc[
    curve[
        "expected_delta_speed_mph"
    ].idxmax()
]

worst_mean = curve.loc[
    curve[
        "expected_delta_speed_mph"
    ].idxmin()
]

best_prob = curve.loc[
    curve[
        "p_improve"
    ].idxmax()
]

# Key checkpoint rows
checkpoint_waits = [
    0, 15, 30, 45, 60,
    90, 120, 150, 180
]

checkpoint = curve[
    curve["wait_minutes"].isin(
        checkpoint_waits
    )
][
    [
        "wait_minutes",
        "future_ambient_temp_c",
        "expected_track_temp_c",
        "expected_delta_speed_mph",
        "median_delta_speed_mph",
        "lower_80_mph",
        "upper_80_mph",
        "lower_90_mph",
        "upper_90_mph",
        "p_improve",
    ]
]

CHECKPOINT_FILE = (
    OUT /
    f"historical_{YEAR}_final_curve_checkpoints_v1.csv"
)

checkpoint.to_csv(
    CHECKPOINT_FILE,
    index=False
)

# ============================================================
# print
# ============================================================

print("=" * 150)
print("PART 1 — HISTORICAL FINAL CASE INPUT")
print("=" * 150)

print("YEAR =", YEAR)
print("CURRENT TIME UTC =", current_time)
print("CURRENT TRACK TEMP =", round(current_track, 4), "C")
print("CURRENT AMBIENT TEMP =", round(current_ambient, 4), "C")
print("HORIZON =", HORIZON_MIN, "min")

print("\nAmbient trajectory points =", len(traj))

print(
    traj.round(4)
    .to_string(index=False)
)

print("\n" + "=" * 150)
print("PART 2 — FINAL CURVE CHECKPOINTS")
print("=" * 150)

print(
    checkpoint
    .round(4)
    .to_string(index=False)
)

print("\n" + "=" * 150)
print("PART 3 — CURVE SUMMARY")
print("=" * 150)

print(
    "MAX EXPECTED ΔSPEED:",
    "wait =", int(best_mean["wait_minutes"]),
    "min,",
    "Δspeed =", round(
        best_mean["expected_delta_speed_mph"],
        4
    ),
    "mph,",
    "P(improve) =", round(
        best_mean["p_improve"],
        4
    )
)

print(
    "MAX P(IMPROVE):",
    "wait =", int(best_prob["wait_minutes"]),
    "min,",
    "P(improve) =", round(
        best_prob["p_improve"],
        4
    ),
    ", Δspeed =", round(
        best_prob["expected_delta_speed_mph"],
        4
    ),
    "mph"
)

print(
    "MIN EXPECTED ΔSPEED:",
    "wait =", int(worst_mean["wait_minutes"]),
    "min,",
    "Δspeed =", round(
        worst_mean["expected_delta_speed_mph"],
        4
    ),
    "mph"
)

print("\nZERO CHECK:")
print(
    curve.iloc[0][
        [
            "expected_delta_track_temp_c",
            "expected_delta_speed_mph",
            "median_delta_speed_mph",
            "p_improve",
        ]
    ].round(6).to_string()
)

print("\nOUTPUTS:")
print(TRAJ_FILE.relative_to(ROOT))
print(CSV_OUT.relative_to(ROOT))
print(CHECKPOINT_FILE.relative_to(ROOT))
print(FIG1.relative_to(ROOT))
print(FIG2.relative_to(ROOT))
print(FIG3.relative_to(ROOT))

print(
    "\nHISTORICAL_FINAL_CASE_V1_COMPLETE"
)
