from pathlib import Path
import hashlib
import json
import pandas as pd
from datetime import datetime, timezone

OUTDIR = Path(
    "weather/output/v2b_section_mechanism"
)

FILES = [
    OUTDIR / "v2b_transition_map_v1.csv",
    OUTDIR / "v2b_section_changes_long_v1.csv",
    OUTDIR / "v2b_transition_section_mechanism_metrics_v1.csv",
    OUTDIR / "v2b_section_mechanism_descriptive_summary_v1.txt",
    OUTDIR / "v2b_section_residual_diagnostics_v1.csv",
    OUTDIR / "v2b_section_residual_diagnostics_summary_v1.txt",
    OUTDIR / "v2b_section_magnitude_control_summary_v1.txt",
]

MANIFEST = (
    OUTDIR /
    "v2b_freeze_manifest_v1.json"
)

SUMMARY = (
    OUTDIR /
    "v2b_freeze_summary_v1.txt"
)


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
        "Missing required V2-B artifacts:\n"
        + "\n".join(missing)
    )


metrics = pd.read_csv(
    OUTDIR /
    "v2b_transition_section_mechanism_metrics_v1.csv"
)

diag = pd.read_csv(
    OUTDIR /
    "v2b_section_residual_diagnostics_v1.csv"
)

manifest = {
    "module":
        "V2-B Section Mechanism Validation",

    "status":
        "FROZEN",

    "freeze_time_utc":
        datetime.now(
            timezone.utc
        ).isoformat(),

    "scope": {
        "final_physics_core_transitions": 41,
        "linked_transition_identities": 39,
        "linked_with_usable_section_evidence": 39,
        "common_complete_sections_per_transition": 9,
    },

    "role": (
        "Mechanism validation only; "
        "section observations are not independent "
        "training rows and are not added to the "
        "production performance model."
    ),

    "principal_findings": [
        (
            "Direction coherence increases strongly "
            "with the magnitude of overall attempt-level "
            "performance change."
        ),
        (
            "Low coherence is concentrated primarily "
            "among near-zero overall performance changes, "
            "where sign-based classification is unstable."
        ),
        (
            "Many of the largest thermal-model residuals "
            "remain spatially coherent across sections."
        ),
        (
            "Large unexplained performance changes therefore "
            "cannot be attributed primarily to localized "
            "section anomalies."
        ),
        (
            "After controlling for absolute overall speed "
            "change, relationships between section-pattern "
            "metrics and absolute physics residual are weak."
        ),
        (
            "Section evidence is retained as descriptive "
            "mechanism validation rather than predictive input."
        ),
    ],

    "magnitude_controlled_partial_spearman": {
        "direction_coherence":
            -0.010948,
        "section_speed_dispersion":
            0.178387,
        "relative_section_dispersion":
            -0.198201,
        "max_abs_section_change_share":
            -0.130146,
    },

    "files": {},
}

for path in FILES:

    manifest["files"][
        str(path)
    ] = {
        "sha256":
            sha256(path),
        "bytes":
            path.stat().st_size,
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
INDY 500 V2-B SECTION MECHANISM VALIDATION — FINAL FREEZE
====================================================================================================

STATUS: FROZEN

SCOPE
----------------------------------------------------------------------------------------------------
Final physics core transitions: 41
Transition identities linked: 39/41
Linked transitions with usable section evidence: 39/39
Common complete sections per linked transition: 9

PURPOSE
----------------------------------------------------------------------------------------------------
Section data are used only as mechanism-validation evidence.

They are NOT treated as independent training observations.
They do NOT expand the effective sample size.
They are NOT added as predictors to the production performance model.

CORE FINDING 1 — DIRECTIONAL COHERENCE
----------------------------------------------------------------------------------------------------
For all 39 linked transitions:
mean direction coherence = 0.723647
median direction coherence = 0.777778

As overall performance-change magnitude increases:

|delta v| >= 0.10 mph:
mean coherence = 0.781481

|delta v| >= 0.20 mph:
mean coherence = 0.843434

|delta v| >= 0.50 mph:
mean coherence = 0.935185

Interpretation:
Low-coherence cases are concentrated largely among near-zero overall performance changes,
where section-level sign comparisons become unstable.

Meaningful attempt-level performance changes are usually spatially coherent across the lap.

CORE FINDING 2 — LARGE PHYSICS RESIDUALS
----------------------------------------------------------------------------------------------------
Large residuals from the thermal model are frequently associated with high section coherence.

Examples include:
Jack Harvey: residual 4.617627 mph, coherence 9/9
Callum Ilott: residual 3.392225 mph, coherence 8/9
Ben Hanley: residual 1.579455 mph, coherence 8/9
Colton Herta: residual 1.272254 mph, coherence 8/9
Max Chilton: residual 1.170208 mph, coherence 9/9

Therefore:

large thermal-model residual
DOES NOT imply
localized section anomaly.

The residual term likely includes broad, unobserved performance-state variation.

Potential sources may include tyre preparation, setup, fuel state,
wind/aerodynamic state, or globally persistent driver-execution effects,
but these causes are not individually identifiable from the section evidence.

CORE FINDING 3 — MAGNITUDE CONTROL
----------------------------------------------------------------------------------------------------
Raw Spearman association with absolute physics residual:

direction coherence:              +0.430869
section-speed dispersion:         +0.270850
relative section dispersion:      -0.531781
max absolute section share:       -0.232186

After controlling for absolute overall speed change:

direction coherence:              -0.010948
section-speed dispersion:         +0.178387
relative section dispersion:      -0.198201
max absolute section share:       -0.130146

Interpretation:
Much of the apparent relationship between section structure and residual magnitude
is explained by the magnitude of the overall attempt-level performance change itself.

No strong independent section-pattern predictor of thermal-model residual magnitude
is supported by the current evidence.

FINAL INTERPRETATION
----------------------------------------------------------------------------------------------------
Section-level evidence supports the view that meaningful qualifying-performance changes
are generally broad and spatially coherent rather than isolated to a small number of
track sections.

Large unexplained changes from the thermal model are also commonly spatially coherent.
Therefore, residual performance variation cannot be interpreted primarily as localized
driver or section anomalies.

Section analysis improves mechanism interpretation but does not justify expanding
the predictive feature set or effective training sample.

FINAL ROLE IN PROJECT
----------------------------------------------------------------------------------------------------
Physics model:
predicts thermal contribution to attempt-level performance change.

Future-track model:
projects physical state conditional on future opportunity horizon h.

Section mechanism validation:
tests whether unexplained attempt-level changes appear spatially coherent or localized.

Section evidence is diagnostic, not predictive.

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
print("V2-B STATUS: FROZEN")
