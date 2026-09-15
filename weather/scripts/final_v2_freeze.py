from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

OUTDIR = Path("weather/output/final_integration")
OUTDIR.mkdir(parents=True, exist_ok=True)

MANIFEST = OUTDIR / "indy500_final_v2_freeze_manifest.json"
SPEC = OUTDIR / "indy500_final_v2_system_specification.md"
SUMMARY = OUTDIR / "indy500_final_v2_freeze_summary.txt"

# ============================================================
# FROZEN / FINAL ARTIFACT INVENTORY
# ============================================================

ARTIFACTS = {
    "physics_core_bootstrap": Path(
        "r5_2/manual/"
        "probabilistic_physics_coefficient_bootstrap_v1.csv"
    ),

    "physics_core_loyo_residuals": Path(
        "r5_2/manual/"
        "probabilistic_physics_loyo_residuals_v1.csv"
    ),

    "v2a_manifest": Path(
        "weather/output/v2_future_track/"
        "v2a_freeze_manifest_v1.json"
    ),

    "v2a_final_results": Path(
        "weather/output/v2_future_track/"
        "v2a_final_results_table_v1.csv"
    ),

    "v2b_manifest": Path(
        "weather/output/v2b_section_mechanism/"
        "v2b_freeze_manifest_v1.json"
    ),

    "v2c_manifest": Path(
        "weather/output/v2c_wind_diagnostic/"
        "v2c_freeze_manifest_v1.json"
    ),

    "v2d_manifest": Path(
        "weather/output/v2d_uncertainty_ablation/"
        "v2d_freeze_manifest_v1.json"
    ),

    "v2d_summary": Path(
        "weather/output/v2d_uncertainty_ablation/"
        "v2d_freeze_summary_v1.txt"
    ),

    "v2e_manifest": Path(
        "weather/output/v2e_scenario_stress_test/"
        "v2e_freeze_manifest_v1.json"
    ),

    "v2e_summary": Path(
        "weather/output/v2e_scenario_stress_test/"
        "v2e_freeze_summary_v1.txt"
    ),

    "applicability_gate": Path(
        "weather/output/final_integration/"
        "applicability_gate_v2.md"
    ),

    "prospective_event_ledger": Path(
        "weather/output/final_integration/"
        "future_prospective_event_ledger_schema_v2.csv"
    ),
}


def sha256(path):
    h = hashlib.sha256()

    with open(path, "rb") as f:
        for chunk in iter(
            lambda: f.read(1024 * 1024),
            b"",
        ):
            h.update(chunk)

    return h.hexdigest()


# ============================================================
# EXISTENCE CHECK
# ============================================================

missing = [
    str(path)
    for path in ARTIFACTS.values()
    if not path.exists()
]

if missing:
    raise FileNotFoundError(
        "Missing FINAL_V2 artifacts:\n"
        + "\n".join(missing)
    )


# ============================================================
# VERIFY MODULE FREEZE STATUS
# ============================================================

module_manifests = {
    "V2-A": ARTIFACTS["v2a_manifest"],
    "V2-B": ARTIFACTS["v2b_manifest"],
    "V2-C": ARTIFACTS["v2c_manifest"],
    "V2-D": ARTIFACTS["v2d_manifest"],
    "V2-E": ARTIFACTS["v2e_manifest"],
}

module_status = {}

for module, path in module_manifests.items():

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    status = data.get(
        "status",
        "UNKNOWN",
    )

    module_status[module] = status

    if status != "FROZEN":
        raise ValueError(
            f"{module} is not FROZEN: {status}"
        )


# ============================================================
# SYSTEM SPECIFICATION
# ============================================================

spec = """# Indianapolis 500 Conditional Performance Decision-Support System

## FINAL_V2 System Specification

### 1. Operational problem

Indianapolis 500 qualifying permits repeat attempts under an operational
trade-off involving retained qualifying performance, queue priority,
remaining session time, and future physical conditions.

Historical reconstruction showed that exact future queue waiting time
and next-run opportunity could not be reliably identified from the
available historical evidence.

The system therefore does not model queue waiting time as a historical
training target.

### 2. Final research question

> If another on-track opportunity occurs h minutes from now, what
> distribution of four-lap qualifying-performance change should be
> expected relative to the current official result?

The future opportunity horizon h is an externally supplied scenario axis.

Supported horizons are:

- 15 minutes
- 30 minutes
- 60 minutes
- 90 minutes
- 120 minutes

### 3. Physics-conditioned performance core

The frozen performance model is:

Delta_v =
beta_track * Delta_T_track
+ beta_ambient * Delta_T_ambient
+ epsilon

with a zero intercept.

The production core uses same-car repeat-attempt transitions and
leave-one-year-out validation.

Coefficient uncertainty is represented using paired bootstrap draws.

Attempt-level unexplained performance variation is represented using
symmetrized empirical LOYO residual magnitude.

### 4. V2-A — Future physical-state model

V2-A predicts future track-temperature change conditional on:

- future ambient-temperature change
- current track-to-ambient thermal gap
- mean future solar elevation

One separately fitted M2b model is used for each supported horizon.

Future-track uncertainty is represented using horizon-specific
symmetrized LOYO residuals.

The future-track distribution is propagated into the performance model
using Monte Carlo simulation.

### 5. V2-B — Section / trap mechanism diagnostic

Section-level evidence is diagnostic rather than predictive.

Meaningful attempt-level performance changes are generally spatially
coherent across the lap rather than isolated to a small number of
sections.

Large thermal-model residuals can also remain spatially coherent.

Section rows are not treated as independent training observations and
do not expand effective sample size.

### 6. V2-C — Wind residual diagnostic

Historical fixed-point wind and gust proxies were evaluated against
absolute physics-model residuals.

The available historical wind evidence was not sufficiently stable
across years to justify either:

- a deterministic wind coefficient, or
- a production heteroskedastic residual-scale model.

This does not imply that wind is physically irrelevant.

### 7. V2-D — Uncertainty-source ablation

The final predictive spread was decomposed diagnostically through
source ablation involving:

- future-track uncertainty
- paired coefficient uncertainty
- empirical performance-residual uncertainty

This is a sensitivity analysis, not a strict additive variance
decomposition.

Empirical attempt-level residual variation is the dominant uncertainty
source.

Future-track and coefficient uncertainty remain secondary contributors
and become increasingly important at longer horizons.

### 8. V2-E — Systematic scenario stress test

The frozen system was evaluated across 135 empirically grounded
physical-state scenarios:

3 thermal-gap states
x 3 ambient trajectories
x 3 solar states
x 5 supported horizons.

All ambient trajectory scenarios remained within the corresponding
horizon-specific historical observed range.

Scenario separation increased substantially with horizon.

At 15 minutes:

P(improvement) range:
0.39646 to 0.58500

Expected delta-speed range:
-0.12261 to +0.10369 mph

At 120 minutes:

P(improvement) range:
0.20552 to 0.67040

Expected delta-speed range:
-0.46298 to +0.22479 mph

Physical-state scenarios therefore shift the centre and probability of
the conditional outlook, but substantial residual uncertainty remains.

### 9. Final uncertainty architecture

For Monte Carlo draw m:

Delta_T_track^(m)
=
predicted_Delta_T_track
+
track_residual^(m)

Delta_v^(m)
=
beta_track^(m) * Delta_T_track^(m)
+
beta_ambient^(m) * Delta_T_ambient
+
performance_residual^(m)

The coefficient pair is always sampled jointly from the same bootstrap
row.

### 10. Supported outputs

For a supported future horizon and physical-state scenario, the system
can produce:

- expected qualifying speed change
- median qualifying speed change
- probability of improvement
- 80% predictive interval
- 90% predictive interval
- future track-temperature outlook

### 11. Explicitly unsupported outputs

The system does not predict:

- exact queue waiting time
- exact next-run opportunity
- Lane 1 / Lane 2 waiting-time distribution
- probability that another run occurs
- autonomous retain / withdraw decisions
- overall strategy-success probability
- unique causal attribution of residual performance variation

### 12. Operational interpretation

The output is conditional:

> Given another on-track opportunity at horizon h and the supplied
> physical-state scenario, what performance distribution should be
> expected?

It is one input into a larger strategy decision.

A complete retain / withdraw decision would additionally require
external live information including:

- current rank and bubble position
- queue state
- cars ahead
- session time remaining
- interruption risk
- probability of receiving another attempt
- consequences of withdrawing the current result

### 13. Applicability boundary

Use of the system is subject to:

- technical-regime applicability
- qualifying-format applicability
- supported horizon
- credible physical-state inputs
- empirical-support / extrapolation checks
- external queue and competitive-state information

### 14. Prospective extension

A future event-ledger schema is defined for prospective collection of:

- exact timestamps
- lane state
- queue position
- cars ahead
- withdrawal and requeue events
- attempt start and completion
- rank / bubble state
- session time remaining
- interruptions
- physical conditions

Such prospective data could support a future opportunity model:

p(H = h | queue state)

which could later be combined with the present conditional
performance model:

p(Delta_v(h) | physical state)

inside a properly specified expected-utility strategy layer.

### 15. Final methodological position

The central methodological contribution is not model complexity.

It is the sequence:

real strategy problem
-> historical identifiability audit
-> rejection of weak queue-time labels
-> physically identifiable conditional subproblem
-> uncertainty-aware probabilistic inference
-> mechanism and residual diagnostics
-> systematic sensitivity and scenario analysis
-> explicit applicability boundary.

The system deliberately prefers a smaller defensible model over a
larger model built on historically unrecoverable variables.
"""

SPEC.write_text(
    spec + "\n",
    encoding="utf-8",
)


# ============================================================
# BUILD FINAL_V2 MANIFEST
# ============================================================

artifact_records = {}

for name, path in ARTIFACTS.items():

    artifact_records[name] = {
        "path": str(path),
        "sha256": sha256(path),
        "bytes": path.stat().st_size,
    }

artifact_records[
    "final_v2_system_specification"
] = {
    "path": str(SPEC),
    "sha256": sha256(SPEC),
    "bytes": SPEC.stat().st_size,
}

manifest = {
    "project":
        "Indianapolis 500 Conditional Performance Decision-Support System",

    "version":
        "FINAL_V2",

    "status":
        "FINAL_FROZEN",

    "freeze_time_utc":
        datetime.now(
            timezone.utc
        ).isoformat(),

    "module_status": module_status,

    "architecture": {
        "performance_core":
            "same-car physics-conditioned probabilistic inference",

        "future_state":
            "V2-A",

        "section_mechanism_diagnostic":
            "V2-B",

        "wind_residual_diagnostic":
            "V2-C",

        "uncertainty_source_ablation":
            "V2-D",

        "scenario_stress_test":
            "V2-E",

        "applicability_gate":
            "included",

        "prospective_event_ledger":
            "included",
    },

    "supported_horizons_min":
        [15, 30, 60, 90, 120],

    "research_question": (
        "If another on-track opportunity occurs h minutes from now, "
        "what distribution of four-lap qualifying-performance change "
        "should be expected relative to the current official result?"
    ),

    "artifacts":
        artifact_records,
}

MANIFEST.write_text(
    json.dumps(
        manifest,
        indent=2,
    ),
    encoding="utf-8",
)

manifest_hash = sha256(
    MANIFEST
)


# ============================================================
# FINAL SUMMARY
# ============================================================

lines = []

def add(x=""):
    lines.append(str(x))


add("=" * 110)
add("INDIANAPOLIS 500 CONDITIONAL PERFORMANCE SYSTEM")
add("FINAL_V2 PROJECT FREEZE")
add("=" * 110)

add()
add("STATUS: FINAL_FROZEN")
add("VERSION: FINAL_V2")

add()
add("MODULE STATUS")
add("-" * 110)

for module, status in module_status.items():
    add(
        f"{module}: {status}"
    )

add()
add("FINAL ARCHITECTURE")
add("-" * 110)

add(
    "Historical evidence"
)
add(
    "-> identifiability audit"
)
add(
    "-> frozen physics-conditioned performance core"
)
add(
    "-> V2-A future physical-state model"
)
add(
    "-> Monte Carlo uncertainty propagation"
)
add(
    "-> V2-B section mechanism diagnostic"
)
add(
    "-> V2-C wind residual diagnostic"
)
add(
    "-> V2-D uncertainty-source ablation"
)
add(
    "-> V2-E systematic scenario stress test"
)
add(
    "-> applicability gate"
)
add(
    "-> prospective event-ledger design"
)

add()
add("SUPPORTED QUESTION")
add("-" * 110)

add(
    "If another on-track opportunity occurs h minutes from now, "
    "what distribution of four-lap qualifying-performance change "
    "should be expected relative to the current official result?"
)

add()
add(
    "Supported horizons: 15 / 30 / 60 / 90 / 120 min"
)

add()
add("SYSTEM BOUNDARY")
add("-" * 110)

add(
    "The system provides conditional probabilistic physical-performance "
    "decision support."
)

add(
    "It does NOT predict exact queue waiting time or autonomously "
    "recommend retain / withdraw decisions."
)

add()
add("SYSTEM SPECIFICATION")
add("-" * 110)
add(str(SPEC))
add(
    f"SHA256: {sha256(SPEC)}"
)

add()
add("FINAL MANIFEST")
add("-" * 110)
add(str(MANIFEST))
add(
    f"SHA256: {manifest_hash}"
)

add()
add("=" * 110)
add("PROJECT STATUS: FINAL_V2 FROZEN")
add("=" * 110)

summary = "\n".join(
    lines
)

SUMMARY.write_text(
    summary + "\n",
    encoding="utf-8",
)

print(summary)

print()
print("OUTPUTS")
print("-" * 110)
print(SPEC)
print(MANIFEST)
print(SUMMARY)
print()
print("DONE")
