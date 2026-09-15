from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

OUTDIR = Path(
    "weather/output/v2c_wind_diagnostic"
)

FILES = [
    OUTDIR / "v2c_wind_linkage_coverage_audit_v1.csv",
    OUTDIR / "v2c_wind_linkage_coverage_summary_v1.txt",
    OUTDIR / "v2c_wind_residual_diagnostic_v1.csv",
    OUTDIR / "v2c_wind_residual_diagnostic_summary_v1.txt",
]

MANIFEST = OUTDIR / "v2c_freeze_manifest_v1.json"
SUMMARY = OUTDIR / "v2c_freeze_summary_v1.txt"


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(
            lambda: f.read(1024 * 1024),
            b""
        ):
            h.update(chunk)
    return h.hexdigest()


missing = [
    str(p)
    for p in FILES
    if not p.exists()
]

if missing:
    raise FileNotFoundError(
        "Missing V2-C artifacts:\n"
        + "\n".join(missing)
    )


manifest = {
    "module":
        "V2-C Wind Residual Diagnostic",

    "status":
        "FROZEN",

    "freeze_time_utc":
        datetime.now(
            timezone.utc
        ).isoformat(),

    "scope": {
        "final_physics_core_transitions": 41,
        "wind_linked_transitions": 39,
        "raw_loyo_residual_available": 39,
        "wind_speed_change_available": 39,
        "gust_change_available": 39,
        "wind_vector_change_available": 38,
    },

    "role": (
        "Residual diagnostic and applicability limitation only. "
        "Wind is not added as a deterministic performance predictor "
        "or as a production heteroskedastic uncertainty term."
    ),

    "principal_findings": [
        (
            "Absolute wind-speed change showed essentially no "
            "relationship with absolute LOYO thermal-model residual."
        ),
        (
            "Absolute gust change showed a modest raw association, "
            "but the relationship weakened after controlling for "
            "absolute overall performance change."
        ),
        (
            "Wind-vector state change also showed only a weak "
            "magnitude-controlled association with residual size."
        ),
        (
            "Within-year wind/residual associations were unstable "
            "in both sign and magnitude."
        ),
        (
            "Large thermal-model residuals did not consistently "
            "coincide with large wind-state changes."
        ),
        (
            "Available fixed-point or gridded historical wind "
            "proxies are not sufficient representations of the "
            "spatially varying aerodynamic wind exposure experienced "
            "around the oval."
        ),
        (
            "The evidence does not justify an explicit deterministic "
            "wind coefficient or production residual-scale model."
        ),
    ],

    "partial_spearman_controlling_abs_delta_speed": {
        "abs_delta_wind_speed_ms":
            -0.031890,
        "abs_delta_gust_ms":
            0.199002,
        "wind_vector_change_ms":
            0.208751,
        "mean_wind_speed_ms":
            0.028497,
        "mean_gust_ms":
            0.060187,
        "abs_delta_ptsc_wind":
            -0.122406,
        "abs_delta_forecast_wind_speed_10m_ms":
            -0.045482,
        "abs_delta_forecast_gust_ms":
            0.189685,
    },

    "files": {},
}

for path in FILES:
    manifest["files"][str(path)] = {
        "sha256": sha256(path),
        "bytes": path.stat().st_size,
    }

MANIFEST.write_text(
    json.dumps(
        manifest,
        indent=2
    ),
    encoding="utf-8"
)

summary = f"""
====================================================================================================
INDY 500 V2-C WIND RESIDUAL DIAGNOSTIC — FINAL FREEZE
====================================================================================================

STATUS: FROZEN

SCOPE
----------------------------------------------------------------------------------------------------
Final physics core transitions: 41
Wind-linked transitions used in diagnostic: 39
Raw LOYO residual coverage: 39/39
Wind-speed-change coverage: 39/39
Gust-change coverage: 39/39
Wind-vector-change coverage: 38/39

PURPOSE
----------------------------------------------------------------------------------------------------
Wind evidence is used only to test whether unresolved thermal-model error
shows a stable relationship with historical wind-state proxies.

This is NOT a new predictive wind model.

No wind variable is added to the frozen deterministic performance model.

No heteroskedastic residual model is introduced.

CORE RESULT — RAW ASSOCIATIONS
----------------------------------------------------------------------------------------------------
Spearman association with absolute raw LOYO physics residual:

|delta wind speed|:              +0.064170
|delta gust|:                    +0.344534
wind-vector change magnitude:    +0.115877
mean wind speed:                 +0.064980
mean gust:                       +0.107287
|delta PTSC wind|:               -0.063796
|delta forecast wind speed|:     +0.032498
|delta forecast gust|:           +0.313492

The strongest raw signal appears in gust change,
but raw associations are not sufficient because residual magnitude
also depends on overall attempt-level performance-change magnitude.

MAGNITUDE-CONTROLLED RESULT
----------------------------------------------------------------------------------------------------
Partial Spearman controlling absolute overall performance change:

|delta wind speed|:              -0.031890
|delta gust|:                    +0.199002
wind-vector change magnitude:    +0.208751
mean wind speed:                 +0.028497
mean gust:                       +0.060187
|delta PTSC wind|:               -0.122406
|delta forecast wind speed|:     -0.045482
|delta forecast gust|:           +0.189685

No strong independent wind-residual relationship remains.

CROSS-YEAR STABILITY
----------------------------------------------------------------------------------------------------
Within-year relationships are not stable.

Examples:

|delta wind speed|
2020: -0.509
2021: -0.132
2023: +0.429

|delta gust|
2020: +0.355
2021: +0.046
2023: +0.549

The variation in both sign and magnitude does not support a stable
production wind or variance effect.

PHYSICAL INTERPRETATION
----------------------------------------------------------------------------------------------------
Wind remains physically relevant to qualifying performance.

However, the available historical proxies do not represent the full
aerodynamic wind exposure experienced by the car around the oval.

Fixed-point or gridded wind cannot reconstruct:
- instantaneous gust timing,
- spatial variation around the circuit,
- changing headwind/tailwind/crosswind orientation,
- car/setup-specific aerodynamic sensitivity,
- local turbulence and exposure.

Therefore:

physical relevance
DOES NOT imply
historical identifiability sufficient for modelling.

FINAL DECISION
----------------------------------------------------------------------------------------------------
Do NOT add a deterministic wind coefficient.

Do NOT introduce a production heteroskedastic wind-residual model.

Retain wind as:
- a plausible contributor to unresolved performance variation,
- a residual interpretation limitation,
- a candidate variable for future prospective high-resolution data collection.

FINAL PROJECT INTERPRETATION
----------------------------------------------------------------------------------------------------
The frozen thermal model explains the identifiable broad physical-state contribution.

Section validation shows that many unexplained changes are spatially coherent.

Wind diagnostics show that available historical wind proxies do not independently
explain those residuals in a stable way.

Therefore, the residual term should remain an empirical representation of broad,
unresolved performance-state variation rather than being decomposed into
unsupported historical mechanisms.

====================================================================================================
MANIFEST
====================================================================================================
{MANIFEST}

SHA256(manifest):
{sha256(MANIFEST)}
""".strip()

SUMMARY.write_text(
    summary,
    encoding="utf-8"
)

print(summary)

print()
print("=" * 100)
print("OUTPUTS")
print("=" * 100)
print(MANIFEST)
print(SUMMARY)
print()
print("V2-C STATUS: FROZEN")
