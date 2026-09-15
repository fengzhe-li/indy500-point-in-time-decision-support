from pathlib import Path
import json
import hashlib
import pandas as pd

ROOT = Path(".")
OUTDIR = Path("weather/output/final_integration")
OUTDIR.mkdir(parents=True, exist_ok=True)

OUT = OUTDIR / "final_architecture_audit_v1.txt"

# =============================================================================
# EXPECTED FROZEN COMPONENTS
# =============================================================================

components = {
    "PHYSICS_CORE": [
        Path("r5_2/manual/probabilistic_physics_coefficient_bootstrap_v1.csv"),
        Path("r5_2/manual/probabilistic_physics_loyo_residuals_v1.csv"),
    ],

    "V2_A_FUTURE_TRACK_STATE": [
        Path("weather/output/v2_future_track/v2a_freeze_manifest_v1.json"),
        Path("weather/output/v2_future_track/v2a_final_results_table_v1.csv"),
        Path("weather/output/v2_future_track/v2a_final_scenario_outlook_v1.png"),
        Path("weather/output/v2_future_track/v2a_freeze_summary_v1.txt"),
    ],

    "V2_B_SECTION_MECHANISM": [
        Path("weather/output/v2b_section_mechanism/v2b_freeze_manifest_v1.json"),
        Path("weather/output/v2b_section_mechanism/v2b_freeze_summary_v1.txt"),
        Path("weather/output/v2b_section_mechanism/v2b_transition_section_mechanism_metrics_v1.csv"),
    ],

    "V2_C_WIND_DIAGNOSTIC": [
        Path("weather/output/v2c_wind_diagnostic/v2c_freeze_manifest_v1.json"),
        Path("weather/output/v2c_wind_diagnostic/v2c_freeze_summary_v1.txt"),
        Path("weather/output/v2c_wind_diagnostic/v2c_wind_residual_diagnostic_v1.csv"),
    ],
}


def sha256(path):
    h = hashlib.sha256()

    with open(path, "rb") as f:
        for chunk in iter(
            lambda: f.read(1024 * 1024),
            b""
        ):
            h.update(chunk)

    return h.hexdigest()


lines = []


def add(x=""):
    lines.append(str(x))


add("=" * 110)
add("INDY 500 FINAL SYSTEM ARCHITECTURE AUDIT")
add("=" * 110)

# =============================================================================
# COMPONENT INVENTORY
# =============================================================================

add()
add("1. FROZEN COMPONENT INVENTORY")
add("-" * 110)

all_present = True

for component, paths in components.items():

    add()
    add(component)

    for p in paths:

        exists = p.exists()

        if not exists:
            all_present = False

        status = "FOUND" if exists else "MISSING"

        add(f"  [{status}] {p}")

        if exists:
            add(f"          bytes: {p.stat().st_size}")

            if p.suffix.lower() != ".png":
                add(f"          sha256: {sha256(p)}")


# =============================================================================
# MANIFEST CONTENT
# =============================================================================

add()
add("=" * 110)
add("2. FROZEN MANIFEST STATUS")
add("-" * 110)

manifest_paths = [
    Path("weather/output/v2_future_track/v2a_freeze_manifest_v1.json"),
    Path("weather/output/v2b_section_mechanism/v2b_freeze_manifest_v1.json"),
    Path("weather/output/v2c_wind_diagnostic/v2c_freeze_manifest_v1.json"),
]

for p in manifest_paths:

    add()
    add(str(p))

    if not p.exists():
        add("  MISSING")
        continue

    try:
        obj = json.loads(
            p.read_text(
                encoding="utf-8"
            )
        )

        add(
            f"  module: "
            f"{obj.get('module', 'not recorded')}"
        )

        add(
            f"  status: "
            f"{obj.get('status', 'not recorded')}"
        )

        add(
            f"  freeze_time_utc: "
            f"{obj.get('freeze_time_utc', 'not recorded')}"
        )

    except Exception as e:
        add(f"  JSON READ ERROR: {e}")


# =============================================================================
# PHYSICS CORE
# =============================================================================

add()
add("=" * 110)
add("3. PHYSICS CORE")
add("-" * 110)

resid_path = Path(
    "r5_2/manual/"
    "probabilistic_physics_loyo_residuals_v1.csv"
)

boot_path = Path(
    "r5_2/manual/"
    "probabilistic_physics_coefficient_bootstrap_v1.csv"
)

if resid_path.exists():

    resid = pd.read_csv(resid_path)

    add(f"LOYO transition rows: {len(resid)}")

    for c in [
        "delta_four_lap_average_speed_mph",
        "delta_track_temp_c",
        "delta_air_temp_c",
        "predicted_physical_delta_mph_loyo",
        "residual_loyo_raw",
        "residual_loyo_centered",
    ]:
        add(
            f"  {c}: "
            f"{'FOUND' if c in resid.columns else 'MISSING'}"
        )

if boot_path.exists():

    boot = pd.read_csv(boot_path)

    add(f"coefficient bootstrap rows: {len(boot)}")

    beta_cols = [
        c for c in boot.columns
        if "beta" in c.lower()
    ]

    add(f"bootstrap coefficient columns: {beta_cols}")

    if len(beta_cols) >= 2:

        corr = boot[
            beta_cols[:2]
        ].corr().iloc[0, 1]

        add(
            f"first-two-beta correlation: "
            f"{corr:.6f}"
        )


# =============================================================================
# FINAL ARCHITECTURE
# =============================================================================

add()
add("=" * 110)
add("4. FINAL SYSTEM ARCHITECTURE")
add("-" * 110)

add("""
HISTORICAL EVIDENCE
        |
        v
IDENTIFIABILITY AUDIT
        |
        +-----------------------------+
        |                             |
        | identifiable                | not reliably identifiable
        v                             v
PHYSICAL PERFORMANCE CORE       QUEUE / OPPORTUNITY PROCESS
        |                             |
        |                             +--> retained as external live input
        |                                  rather than historical target
        v
FUTURE OPPORTUNITY HORIZON h
(user/scenario supplied)
        |
        v
V2-A FUTURE TRACK-STATE MODEL
        |
        |  distribution of future track state
        v
PHYSICS COEFFICIENT UNCERTAINTY
+
EMPIRICAL PERFORMANCE RESIDUAL
        |
        v
MONTE CARLO PERFORMANCE OUTLOOK
        |
        +--> E[delta speed]
        +--> 80% interval
        +--> 90% interval
        +--> P(delta speed > 0)

SUPPORTING VALIDATION LAYERS

V2-B SECTION MECHANISM VALIDATION
        |
        +--> tests spatial coherence of attempt-level changes
        +--> diagnostic only
        +--> does not increase training N

V2-C WIND RESIDUAL DIAGNOSTIC
        |
        +--> tests historical wind proxies against unresolved error
        +--> diagnostic / limitation only
        +--> no deterministic wind coefficient
        +--> no production heteroskedastic wind model
""".strip())


# =============================================================================
# CAPABILITY BOUNDARY
# =============================================================================

add()
add("=" * 110)
add("5. CAPABILITY BOUNDARY")
add("-" * 110)

capabilities = [
    (
        "SUPPORTED",
        "Estimate the distribution of four-lap performance change "
        "conditional on a specified future opportunity horizon h."
    ),
    (
        "SUPPORTED",
        "Propagate future track-state uncertainty, paired physics-coefficient "
        "uncertainty, and empirical performance residual uncertainty."
    ),
    (
        "SUPPORTED",
        "Return expected delta speed, calibrated uncertainty intervals, "
        "and probability of improvement."
    ),
    (
        "SUPPORTED",
        "Use section evidence to diagnose whether observed performance "
        "changes are spatially coherent or localized."
    ),
    (
        "SUPPORTED",
        "Use historical wind evidence as a residual-identifiability diagnostic."
    ),

    (
        "NOT SUPPORTED",
        "Predict the exact time at which another qualifying opportunity "
        "will occur."
    ),
    (
        "NOT SUPPORTED",
        "Predict Lane 1 / Lane 2 queue waiting time from the historical dataset."
    ),
    (
        "NOT SUPPORTED",
        "Automatically decide retain versus withdraw without external "
        "competitive and operational state."
    ),
    (
        "NOT SUPPORTED",
        "Attribute thermal-model residuals uniquely to wind, tyres, setup, "
        "fuel, driver execution, or another latent mechanism."
    ),
    (
        "NOT SUPPORTED",
        "Treat section observations as independent performance-training rows."
    ),
]

for status, text in capabilities:
    add(f"[{status}] {text}")


# =============================================================================
# DECISION-SUPPORT INTERFACE
# =============================================================================

add()
add("=" * 110)
add("6. FINAL DECISION-SUPPORT INTERFACE")
add("-" * 110)

add("""
INPUTS

Required scenario/state inputs:
- current track temperature
- current ambient temperature
- future ambient-temperature scenario
- future opportunity horizon h
- solar state / geometry required by frozen V2-A model

External operational inputs NOT modelled historically:
- current qualifying position
- bubble position / competitor state
- Lane 1 / Lane 2 queue state
- remaining session time
- interruption / no-run risk
- team utility of retaining current result

MODEL OUTPUTS

For each supported horizon:
- expected four-lap speed change
- 80% prediction interval
- 90% prediction interval
- probability of improvement

INTERPRETATION

The model answers:

"If another on-track opportunity occurs h minutes from now,
what distribution of four-lap performance change should be expected?"

It does NOT answer:

"When will another opportunity occur?"

or

"Should the team withdraw the current result?"
""".strip())


# =============================================================================
# FINAL AUDIT STATUS
# =============================================================================

add()
add("=" * 110)
add("7. AUDIT STATUS")
add("-" * 110)

if all_present:
    add("PASS: all expected frozen integration artifacts were found.")
else:
    add(
        "ATTENTION: one or more expected artifacts were missing. "
        "Review inventory before final documentation."
    )

add()
add(
    "No frozen model or diagnostic artifact was modified by this audit."
)

summary = "\n".join(lines)

OUT.write_text(
    summary,
    encoding="utf-8"
)

print(summary)

print()
print("=" * 110)
print("OUTPUT")
print("=" * 110)
print(OUT)
print()
print("DONE")
