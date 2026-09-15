from pathlib import Path
import importlib.util
import pandas as pd
import numpy as np

ROOT = Path("/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈")
OUT = ROOT / "r5_2/manual"

ENGINE_FILE = OUT / "build_final_wait_performance_engine_v1.py"
CASES_FILE = OUT / "rescued_repeat_physical_transitions_v2.csv"

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
# load audited rescued cases
# ============================================================

cases = pd.read_csv(CASES_FILE)

numeric = [
    "elapsed_between_attempt_points_min",
    "before_track_temp_c",
    "after_track_temp_c",
    "before_air_temp_c",
    "after_air_temp_c",
    "before_speed_mph",
    "after_speed_mph",
    "delta_speed_mph",
]

for c in numeric:
    cases[c] = pd.to_numeric(
        cases[c],
        errors="coerce"
    )

# Only use cases within validated future-state horizon.
valid = cases[
    cases["elapsed_between_attempt_points_min"].between(
        0,
        180,
        inclusive="both"
    )
].copy()

excluded = cases[
    ~cases.index.isin(valid.index)
].copy()

print("=" * 150)
print("PART 1 — FINAL ENGINE HISTORICAL VALIDATION CASES")
print("=" * 150)

print("TOTAL AUDITED RESCUED CASES =", len(cases))
print("WITHIN 0–180 MIN VALIDATED HORIZON =", len(valid))
print("EXCLUDED OUTSIDE HORIZON =", len(excluded))

if not excluded.empty:
    print("\nEXCLUDED:")
    print(
        excluded[
            [
                "year",
                "driver_name",
                "elapsed_between_attempt_points_min",
                "delta_speed_mph",
            ]
        ]
        .round(4)
        .to_string(index=False)
    )

# ============================================================
# run final engine at actual elapsed interval
# ============================================================

rng = np.random.default_rng(500)

rows = []

for _, r in valid.iterrows():

    wait = float(
        r["elapsed_between_attempt_points_min"]
    )

    result = engine.simulate_wait(
        wait_min=wait,
        current_track_c=float(
            r["before_track_temp_c"]
        ),
        current_ambient_c=float(
            r["before_air_temp_c"]
        ),
        future_ambient_c=float(
            r["after_air_temp_c"]
        ),
        rng=rng,
        nsim=100000
    )

    actual_delta = float(
        r["delta_speed_mph"]
    )

    actual_track_delta = (
        float(r["after_track_temp_c"])
        -
        float(r["before_track_temp_c"])
    )

    rows.append({
        "year":
            int(r["year"]),

        "driver_name":
            r["driver_name"],

        "wait_min":
            wait,

        "before_speed_mph":
            r["before_speed_mph"],

        "after_speed_mph":
            r["after_speed_mph"],

        "actual_delta_speed_mph":
            actual_delta,

        "actual_delta_track_temp_c":
            actual_track_delta,

        "model_expected_delta_track_temp_c":
            result[
                "expected_delta_track_temp_c"
            ],

        "track_temp_model_error_c":
            result[
                "expected_delta_track_temp_c"
            ] - actual_track_delta,

        "model_expected_delta_speed_mph":
            result[
                "expected_delta_speed_mph"
            ],

        "model_median_delta_speed_mph":
            result[
                "median_delta_speed_mph"
            ],

        "lower_80_mph":
            result["lower_80_mph"],

        "upper_80_mph":
            result["upper_80_mph"],

        "lower_90_mph":
            result["lower_90_mph"],

        "upper_90_mph":
            result["upper_90_mph"],

        "p_improve":
            result["p_improve"],

        "inside_80":
            (
                result["lower_80_mph"]
                <= actual_delta
                <= result["upper_80_mph"]
            ),

        "inside_90":
            (
                result["lower_90_mph"]
                <= actual_delta
                <= result["upper_90_mph"]
            ),
    })

bt = pd.DataFrame(rows)

# ============================================================
# print
# ============================================================

print("\n" + "=" * 150)
print("PART 2 — CAR-SPECIFIC END-TO-END BACKTEST")
print("=" * 150)

show = [
    "year",
    "driver_name",
    "wait_min",
    "actual_delta_track_temp_c",
    "model_expected_delta_track_temp_c",
    "track_temp_model_error_c",
    "actual_delta_speed_mph",
    "model_expected_delta_speed_mph",
    "model_median_delta_speed_mph",
    "lower_80_mph",
    "upper_80_mph",
    "lower_90_mph",
    "upper_90_mph",
    "p_improve",
    "inside_80",
    "inside_90",
]

print(
    bt[show]
    .round(4)
    .to_string(index=False)
)

print("\n" + "=" * 150)
print("PART 3 — VALIDATION SUMMARY")
print("=" * 150)

if not bt.empty:

    print(
        "cases =",
        len(bt)
    )

    print(
        "mean absolute Δspeed point error =",
        round(
            np.mean(
                np.abs(
                    bt[
                        "model_expected_delta_speed_mph"
                    ]
                    -
                    bt[
                        "actual_delta_speed_mph"
                    ]
                )
            ),
            4
        ),
        "mph"
    )

    print(
        "80% interval hits =",
        int(bt["inside_80"].sum()),
        "/",
        len(bt)
    )

    print(
        "90% interval hits =",
        int(bt["inside_90"].sum()),
        "/",
        len(bt)
    )

# ============================================================
# save
# ============================================================

OUTFILE = (
    OUT /
    "final_engine_rescued_case_backtest_v1.csv"
)

bt.to_csv(
    OUTFILE,
    index=False
)

print("\nOUTPUT:")
print(OUTFILE.relative_to(ROOT))

print(
    "\nFINAL_ENGINE_RESCUED_CASE_BACKTEST_V1_COMPLETE"
)
