from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

OUTDIR = Path("weather/output/v2e_scenario_stress_test")

SCENARIO = OUTDIR / "v2e_scenario_grid_v1.csv"
RESULTS = OUTDIR / "v2e_scenario_stress_test_results_v1.csv"
PROFILES = OUTDIR / "v2e_scenario_horizon_profiles_v1.csv"
SUMMARY = OUTDIR / "v2e_scenario_stress_test_summary_v1.txt"

MANIFEST = OUTDIR / "v2e_freeze_manifest_v1.json"
FREEZE_SUMMARY = OUTDIR / "v2e_freeze_summary_v1.txt"

required = [
    SCENARIO,
    RESULTS,
    PROFILES,
    SUMMARY,
]

for p in required:
    if not p.exists():
        raise FileNotFoundError(p)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


manifest = {
    "module": "V2-E Systematic Scenario Stress Test",
    "status": "FROZEN",
    "freeze_time_utc": datetime.now(timezone.utc).isoformat(),

    "purpose": (
        "Evaluate how the frozen conditional probabilistic "
        "performance system behaves across empirically supported "
        "thermal-gap, ambient-trajectory, solar-state, and horizon scenarios."
    ),

    "scenario_design": {
        "total_scenarios": 135,
        "thermal_gap_states": 3,
        "ambient_trajectory_states": 3,
        "solar_states": 3,
        "supported_horizons_min": [15, 30, 60, 90, 120],
        "ambient_support_check_fraction": 1.0,
    },

    "principal_findings": {
        "scenario_separation": (
            "Conditional physical-state scenarios increasingly separate "
            "performance outlooks at longer horizons."
        ),

        "15_min_p_improve_range": [0.39646, 0.58500],
        "120_min_p_improve_range": [0.20552, 0.67040],

        "15_min_expected_delta_range_mph": [-0.12261, 0.10369],
        "120_min_expected_delta_range_mph": [-0.46298, 0.22479],

        "best_observed_grid_scenario": {
            "horizon_min": 120,
            "thermal_gap_state": "HIGH_GAP",
            "ambient_trajectory": "WARMING",
            "solar_state": "LOW_SOLAR",
            "expected_delta_speed_mph": 0.22479,
            "p_improve": 0.67040,
            "lower_80_mph": -0.53037,
            "upper_80_mph": 1.00849,
        },

        "worst_observed_grid_scenario": {
            "horizon_min": 120,
            "thermal_gap_state": "LOW_GAP",
            "ambient_trajectory": "COOLING",
            "solar_state": "HIGH_SOLAR",
            "expected_delta_speed_mph": -0.46298,
            "p_improve": 0.20552,
            "lower_80_mph": -1.32475,
            "upper_80_mph": 0.30757,
        },
    },

    "interpretation_boundary": (
        "The stress test is conditional on another on-track opportunity "
        "occurring at the specified horizon. It does not model queue waiting "
        "time, opportunity probability, or retain/withdraw utility."
    ),

    "artifacts": {},
}

for p in required:
    manifest["artifacts"][str(p)] = {
        "sha256": sha256(p),
        "bytes": p.stat().st_size,
    }

MANIFEST.write_text(
    json.dumps(manifest, indent=2),
    encoding="utf-8",
)

summary = f"""
====================================================================================================
INDY 500 V2-E SYSTEMATIC SCENARIO STRESS TEST — FINAL FREEZE
====================================================================================================

STATUS: FROZEN

SCENARIO DESIGN
----------------------------------------------------------------------------------------------------
135 empirically grounded scenarios:

3 thermal-gap states
× 3 ambient trajectories
× 3 solar states
× 5 supported horizons

Supported horizons:
15 / 30 / 60 / 90 / 120 min

All ambient-delta scenarios remain inside the corresponding
horizon-specific historical observed range.

MAIN RESULT
----------------------------------------------------------------------------------------------------
Scenario separation increases with horizon.

P(improvement) range:

15 min:
0.39646 to 0.58500

120 min:
0.20552 to 0.67040

Expected delta-speed range:

15 min:
-0.12261 to +0.10369 mph

120 min:
-0.46298 to +0.22479 mph

MOST FAVOURABLE GRID SCENARIO
----------------------------------------------------------------------------------------------------
120 min
HIGH_GAP
WARMING
LOW_SOLAR

Expected delta speed:
+0.22479 mph

P(improvement):
0.67040

80% interval:
[-0.53037, +1.00849] mph

MOST UNFAVOURABLE GRID SCENARIO
----------------------------------------------------------------------------------------------------
120 min
LOW_GAP
COOLING
HIGH_SOLAR

Expected delta speed:
-0.46298 mph

P(improvement):
0.20552

80% interval:
[-1.32475, +0.30757] mph

FINAL INTERPRETATION
----------------------------------------------------------------------------------------------------
Physical-state scenarios materially shift the centre and probability
of the conditional performance outlook, particularly at longer horizons.

However, predictive intervals remain wide and generally overlap zero,
consistent with V2-D's finding that unresolved attempt-level residual
variation dominates final uncertainty.

The stress test therefore supports probabilistic physical-state decision
support, not deterministic retain/withdraw recommendations.

MANIFEST
----------------------------------------------------------------------------------------------------
{MANIFEST}

SHA256(manifest):
{sha256(MANIFEST)}

====================================================================================================
V2-E STATUS: FROZEN
====================================================================================================
""".strip()

FREEZE_SUMMARY.write_text(
    summary + "\n",
    encoding="utf-8",
)

print(summary)
print()
print("OUTPUTS")
print("-" * 100)
print(MANIFEST)
print(FREEZE_SUMMARY)
print()
print("DONE")
