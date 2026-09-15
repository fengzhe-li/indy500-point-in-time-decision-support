from pathlib import Path
import json
import hashlib
import datetime

ROOT = Path("/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈")
OUT = ROOT / "r5_2/manual"

FILES = [
    "r5_2/manual/r5_2_repeat_analysis_set_v1.csv",
    "r5_2/manual/probabilistic_physics_core_v1.json",
    "r5_2/manual/probabilistic_physics_coefficient_bootstrap_v1.csv",
    "r5_2/manual/probabilistic_physics_loyo_residuals_v1.csv",
    "r5_2/manual/extended_invariant_future_state_model_v3.json",
    "r5_2/manual/extended_future_state_horizon_uncertainty_v3.csv",
    "r5_2/manual/extended_future_state_standardized_residuals_v3.csv",
    "r5_2/manual/final_engine_rescued_case_backtest_v1.csv",
    "r5_2/manual/build_final_wait_performance_engine_v1.py",
]

def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(1024 * 1024)
            if not b:
                break
            h.update(b)
    return h.hexdigest()

manifest_files = []

for rel in FILES:
    p = ROOT / rel

    manifest_files.append({
        "path": rel,
        "exists": p.exists(),
        "sha256": sha256(p) if p.exists() else None,
        "size_bytes": p.stat().st_size if p.exists() else None,
    })

manifest = {
    "version": "INDY500_CORE_REGIME_2020_2024_V1",

    "frozen_at_utc":
        datetime.datetime.now(
            datetime.timezone.utc
        ).isoformat(),

    "technical_regime": {
        "years": [2020, 2021, 2022, 2023, 2024],
        "description":
            "Aeroscreen-era Indy 500 qualifying before the hybrid-era Indy 500."
    },

    "scientific_objective":
        "Physics-conditioned probabilistic estimation of change in four-lap qualifying average under hypothetical waiting intervals.",

    "observation_unit":
        "One complete four-lap Indy 500 qualifying attempt.",

    "performance_target":
        "delta_four_lap_average_speed_mph",

    "performance_core": {
        "features": [
            "delta_track_temp_c",
            "delta_air_temp_c"
        ],
        "track_temp_constraint": "<= 0",
        "generic_reattempt_intercept": 0.0,
        "air_density_role": "diagnostic only",
        "gust_wind_role": "secondary sensitivity / uncertainty",
        "shortwave_cloud_role": "thermal forcing / mechanism"
    },

    "future_state": {
        "validated_wait_horizon_minutes": [0, 180],
        "target": "delta_track_temp_c",
        "zero_wait_invariance": True
    },

    "decision_boundary": {
        "model_outputs": [
            "expected_delta_speed",
            "median_delta_speed",
            "80_percent_interval",
            "90_percent_interval",
            "p_improve"
        ],
        "model_does_not_output": [
            "DELETE",
            "WITHDRAW",
            "RETAIN",
            "REATTEMPT"
        ]
    },

    "validation": {
        "performance_same_car_analysis_rows": 42,
        "future_track_transition_rows": 1016,
        "future_state_loyo_years": [
            2020, 2021, 2022, 2023, 2024
        ],
        "independent_rescued_end_to_end_cases_within_horizon": 2,
        "rescued_case_80pct_hits": "1/2",
        "rescued_case_90pct_hits": "2/2",
        "rescued_case_mean_absolute_point_error_mph": 0.8757
    },

    "known_limitations": [
        "Performance-layer sample size is small.",
        "Unobserved setup, tire preparation, and vehicle-state changes remain in residual uncertainty.",
        "Future track-temperature point prediction can miss transient cooling/heating events.",
        "The model is decision support, not a strategy recommendation system.",
        "The 2020-2024 core must not be assumed valid in other technical regulation regimes without revalidation."
    ],

    "files": manifest_files
}

OUTFILE = OUT / "CORE_REGIME_2020_2024_V1_FROZEN_MANIFEST.json"

with open(OUTFILE, "w", encoding="utf-8") as f:
    json.dump(manifest, f, indent=2)

print("=" * 120)
print("2020-2024 CORE REGIME FREEZE")
print("=" * 120)

for x in manifest_files:
    print(
        x["path"],
        "OK" if x["exists"] else "MISSING",
        x["sha256"][:12] if x["sha256"] else ""
    )

print("\nOUTPUT:")
print(OUTFILE.relative_to(ROOT))

print("\nCORE_REGIME_2020_2024_V1_FROZEN")
