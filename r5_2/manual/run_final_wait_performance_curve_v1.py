from pathlib import Path
import argparse
import importlib.util
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

ROOT = Path("/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈")
OUT = ROOT / "r5_2/manual"

ENGINE_FILE = OUT / "build_final_wait_performance_engine_v1.py"

# ------------------------------------------------------------
# load engine
# ------------------------------------------------------------

spec = importlib.util.spec_from_file_location(
    "final_engine",
    ENGINE_FILE
)

engine = importlib.util.module_from_spec(spec)
spec.loader.exec_module(engine)

# ------------------------------------------------------------
# arguments
# ------------------------------------------------------------

parser = argparse.ArgumentParser()

parser.add_argument(
    "--current-track",
    type=float,
    required=True,
    help="Current track temperature in Celsius"
)

parser.add_argument(
    "--current-ambient",
    type=float,
    required=True,
    help="Current ambient temperature in Celsius"
)

parser.add_argument(
    "--session-remaining",
    type=int,
    required=True,
    help="Remaining qualifying session time in minutes, max 180"
)

parser.add_argument(
    "--ambient-file",
    type=str,
    default=str(
        OUT / "final_curve_ambient_trajectory_template.csv"
    )
)

parser.add_argument(
    "--nsim",
    type=int,
    default=30000
)

args = parser.parse_args()

# ------------------------------------------------------------
# validation
# ------------------------------------------------------------

if args.session_remaining < 0:
    raise ValueError("session remaining must be >= 0")

if args.session_remaining > 180:
    raise ValueError(
        "Validated future-state horizon is currently limited to 180 minutes."
    )

ambient_file = Path(args.ambient_file)

if not ambient_file.exists():
    raise FileNotFoundError(
        f"Ambient trajectory file not found: {ambient_file}"
    )

traj = pd.read_csv(ambient_file)

required = {
    "wait_minutes",
    "future_ambient_temp_c"
}

missing = required - set(traj.columns)

if missing:
    raise ValueError(
        f"Ambient file missing columns: {missing}"
    )

traj["wait_minutes"] = pd.to_numeric(
    traj["wait_minutes"],
    errors="coerce"
)

traj["future_ambient_temp_c"] = pd.to_numeric(
    traj["future_ambient_temp_c"],
    errors="coerce"
)

traj = traj.dropna()

if traj.empty:
    raise ValueError(
        "Ambient trajectory contains no usable numeric rows."
    )

# ------------------------------------------------------------
# ensure wait=0 anchor is current ambient
# ------------------------------------------------------------

traj = traj[
    traj["wait_minutes"] <= args.session_remaining
].copy()

zero_exists = np.isclose(
    traj["wait_minutes"],
    0
).any()

if zero_exists:
    traj.loc[
        np.isclose(traj["wait_minutes"], 0),
        "future_ambient_temp_c"
    ] = args.current_ambient

else:
    traj = pd.concat(
        [
            pd.DataFrame({
                "wait_minutes": [0.0],
                "future_ambient_temp_c": [
                    args.current_ambient
                ]
            }),
            traj
        ],
        ignore_index=True
    )

# Need an endpoint for interpolation
if traj["wait_minutes"].max() < args.session_remaining:

    last_temp = traj.sort_values(
        "wait_minutes"
    ).iloc[-1]["future_ambient_temp_c"]

    traj = pd.concat(
        [
            traj,
            pd.DataFrame({
                "wait_minutes": [
                    float(args.session_remaining)
                ],
                "future_ambient_temp_c": [
                    float(last_temp)
                ]
            })
        ],
        ignore_index=True
    )

traj = (
    traj.sort_values("wait_minutes")
    .drop_duplicates(
        "wait_minutes",
        keep="last"
    )
)

# ------------------------------------------------------------
# run final curve
# ------------------------------------------------------------

curve = engine.build_curve(
    current_track_c=args.current_track,
    current_ambient_c=args.current_ambient,
    ambient_trajectory=traj,
    session_remaining_min=args.session_remaining,
    nsim=args.nsim,
    seed=500
)

# ------------------------------------------------------------
# strict zero anchor
# ------------------------------------------------------------

zero = curve.iloc[0]

assert zero["wait_minutes"] == 0
assert abs(
    zero["expected_delta_track_temp_c"]
) < 1e-12
assert abs(
    zero["expected_delta_speed_mph"]
) < 1e-12

# ------------------------------------------------------------
# save data
# ------------------------------------------------------------

CSV_OUT = OUT / "final_wait_performance_curve_v1.csv"

curve.to_csv(
    CSV_OUT,
    index=False
)

# ------------------------------------------------------------
# FIGURE 1 — Δspeed distribution vs hypothetical wait
# ------------------------------------------------------------

FIG1 = OUT / "final_wait_performance_curve_v1.png"

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
    linewidth=1,
    linestyle="--",
    label="Current official result"
)

ax.set_xlabel(
    "Hypothetical wait until reattempt (minutes)"
)

ax.set_ylabel(
    "Δ four-lap average speed (mph)"
)

ax.set_title(
    "Physics-Conditioned Indy 500 Qualifying Performance Change"
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

# ------------------------------------------------------------
# FIGURE 2 — P(improve)
# ------------------------------------------------------------

FIG2 = OUT / "final_probability_improve_curve_v1.png"

fig, ax = plt.subplots(figsize=(10, 5))

ax.plot(
    x,
    curve["p_improve"],
    linewidth=2
)

ax.axhline(
    0.5,
    linewidth=1,
    linestyle="--"
)

ax.set_ylim(
    0,
    1
)

ax.set_xlabel(
    "Hypothetical wait until reattempt (minutes)"
)

ax.set_ylabel(
    "Probability of improving current four-lap average"
)

ax.set_title(
    "Probability of Qualifying Performance Improvement"
)

ax.grid(alpha=0.2)

fig.tight_layout()

fig.savefig(
    FIG2,
    dpi=180,
    bbox_inches="tight"
)

plt.close(fig)

# ------------------------------------------------------------
# FIGURE 3 — physical state trajectory
# ------------------------------------------------------------

FIG3 = OUT / "final_physical_state_trajectory_v1.png"

fig, ax = plt.subplots(figsize=(10, 5))

ax.plot(
    x,
    args.current_track
    +
    curve["expected_delta_track_temp_c"],
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
    "Projected Physical State"
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

# ------------------------------------------------------------
# summary
# ------------------------------------------------------------

best = curve.loc[
    curve["expected_delta_speed_mph"].idxmax()
]

lowest = curve.loc[
    curve["expected_delta_speed_mph"].idxmin()
]

prob_best = curve.loc[
    curve["p_improve"].idxmax()
]

print("=" * 150)
print("FINAL WAIT -> PERFORMANCE CURVE COMPLETE")
print("=" * 150)

print("\nINPUT STATE:")
print(
    "current track temp =",
    args.current_track,
    "C"
)
print(
    "current ambient temp =",
    args.current_ambient,
    "C"
)
print(
    "session remaining =",
    args.session_remaining,
    "min"
)

print("\nZERO-WAIT CHECK:")
print(
    "expected Δspeed =",
    round(
        curve.iloc[0]["expected_delta_speed_mph"],
        8
    )
)
print(
    "median Δspeed =",
    round(
        curve.iloc[0]["median_delta_speed_mph"],
        8
    )
)
print(
    "P(improve) =",
    round(
        curve.iloc[0]["p_improve"],
        5
    )
)

print("\nMAX EXPECTED PHYSICAL ΔSPEED POINT:")
print(
    "wait =",
    int(best["wait_minutes"]),
    "min"
)
print(
    "expected Δspeed =",
    round(
        best["expected_delta_speed_mph"],
        4
    ),
    "mph"
)
print(
    "P(improve) =",
    round(
        best["p_improve"],
        4
    )
)

print("\nMAX P(IMPROVE) POINT:")
print(
    "wait =",
    int(prob_best["wait_minutes"]),
    "min"
)
print(
    "P(improve) =",
    round(
        prob_best["p_improve"],
        4
    )
)
print(
    "expected Δspeed =",
    round(
        prob_best["expected_delta_speed_mph"],
        4
    ),
    "mph"
)

print("\nMIN EXPECTED PHYSICAL ΔSPEED POINT:")
print(
    "wait =",
    int(lowest["wait_minutes"]),
    "min"
)
print(
    "expected Δspeed =",
    round(
        lowest["expected_delta_speed_mph"],
        4
    ),
    "mph"
)

print("\nOUTPUTS:")
print(CSV_OUT.relative_to(ROOT))
print(FIG1.relative_to(ROOT))
print(FIG2.relative_to(ROOT))
print(FIG3.relative_to(ROOT))

print(
    "\nFINAL_WAIT_PERFORMANCE_CURVE_V1_COMPLETE"
)
