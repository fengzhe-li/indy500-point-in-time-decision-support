from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

OUTDIR = Path("weather/output/final_integration")
OUTDIR.mkdir(parents=True, exist_ok=True)

SPEC = OUTDIR / "indy500_final_system_specification_v1.md"
MANIFEST = OUTDIR / "indy500_final_project_freeze_manifest_v1.json"
SUMMARY = OUTDIR / "indy500_final_project_freeze_summary_v1.txt"

ARCH = OUTDIR / "final_architecture_audit_v1.txt"

V2A = Path(
    "weather/output/v2_future_track/"
    "v2a_freeze_manifest_v1.json"
)

V2B = Path(
    "weather/output/v2b_section_mechanism/"
    "v2b_freeze_manifest_v1.json"
)

V2C = Path(
    "weather/output/v2c_wind_diagnostic/"
    "v2c_freeze_manifest_v1.json"
)

BOOT = Path(
    "r5_2/manual/"
    "probabilistic_physics_coefficient_bootstrap_v1.csv"
)

RESID = Path(
    "r5_2/manual/"
    "probabilistic_physics_loyo_residuals_v1.csv"
)

required = [
    ARCH,
    V2A,
    V2B,
    V2C,
    BOOT,
    RESID,
]

missing = [
    str(p)
    for p in required
    if not p.exists()
]

if missing:
    raise FileNotFoundError(
        "Missing required frozen artifacts:\n"
        + "\n".join(missing)
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


spec = r"""
# Indy 500 Qualifying Decision-Support Project
## Final Frozen System Specification — Version 1

**Status:** FROZEN

---

# 1. Final Research Question

The final system answers:

> **If another on-track opportunity occurs h minutes from now, what distribution of four-lap qualifying-performance change should be expected relative to the current official result?**

The future opportunity horizon `h` is a scenario input.

The system does not predict when another opportunity will occur.

---

# 2. Original Decision Problem

During Indianapolis 500 qualifying, a team may face a sequential decision after obtaining a valid four-lap result.

Depending on the qualifying format and live operational state, the team may:

- retain the existing result and wait for another opportunity, or
- sacrifice / withdraw the current result in exchange for higher-priority access to another qualifying attempt.

The practical decision depends on two fundamentally different uncertainties:

1. **Opportunity uncertainty**

   Whether and when another on-track attempt becomes available.

2. **Performance-state uncertainty**

   Conditional on another attempt occurring, how physical conditions may affect achievable four-lap performance.

---

# 3. Identifiability-Driven Reformulation

The project initially investigated whether historical data could support reconstruction of the queue / opportunity process.

Required historical variables included:

- Lane 1 / Lane 2 queue state,
- withdrawal timing,
- requeue timing,
- pit-return behaviour,
- live queue order,
- leaderboard state,
- exact event timestamps,
- interruptions,
- team intent.

Historical evidence was incomplete and inconsistent across seasons.

Therefore, queue waiting time could not be reconstructed with sufficient reliability to serve as a defensible historical training target.

The project deliberately rejected false precision.

Instead of estimating:

    p(H | historical queue reconstruction)

the final project conditions on a supplied opportunity horizon:

    H = h

and estimates:

    p(delta_v | h, physical state)

This reformulation is a core methodological result of the project.

---

# 4. Canonical Performance Unit

The canonical observation is one complete four-lap qualifying attempt.

Individual laps and individual track sections are not treated as independent performance observations.

The principal historical comparison is a same-car transition:

    Attempt_i -> Attempt_i+1

with response:

    delta_v = v_(i+1) - v_i

Same-car comparisons reduce fixed variation associated with:

- driver identity,
- chassis,
- engine,
- persistent car characteristics,
- broad setup identity.

They do not eliminate transient latent variation.

---

# 5. Frozen Historical Physics Core

Final core:

    41 same-car qualifying transitions

Primary deterministic model:

    delta_v
      = beta_track * delta_T_track
      + beta_ambient * delta_T_ambient
      + epsilon

Zero intercept is used.

Frozen coefficients:

    beta_track   = -0.03482533 mph / degC
    beta_ambient = +0.18239338 mph / degC

The coefficients are conditional statistical effects.

The positive ambient coefficient is not interpreted as a standalone causal effect because track and ambient thermal states are correlated.

---

# 6. Validation Design

Random train/test splitting is not used as the primary validation strategy.

The core performance model uses leave-one-year-out validation.

Previously frozen aggregate diagnostic:

    median absolute point error = 0.3106 mph

Uncertainty calibration:

    nominal 80% interval -> approximately 82.93% observed coverage
    nominal 90% interval -> approximately 90.24% observed coverage

---

# 7. Coefficient Uncertainty

The frozen coefficient bootstrap contains:

    5000 paired coefficient draws

The track-temperature and ambient-temperature coefficients are strongly correlated:

    correlation approximately -0.9085

Therefore coefficient draws must remain paired.

The two coefficients must not be independently resampled in Monte Carlo propagation.

---

# 8. Empirical Performance Residual

LOYO residuals represent realized attempt-level variation not explained by the compact thermal model.

For production uncertainty propagation:

- empirical residual magnitude is retained,
- sign is randomized symmetrically,
- no generic directional reattempt bonus or penalty is imposed.

The residual is not interpreted as one physical mechanism.

It represents unresolved performance-state variation.

Potential contributors may include:

- tyre preparation,
- tyre state,
- setup changes,
- fuel state,
- wind / aerodynamic exposure,
- driver execution,
- other unobserved operational effects.

These mechanisms are not individually identifiable from the frozen historical evidence.

---

# 9. V2-A — Future Physical-State Model

## Purpose

Project future track temperature conditional on a supplied future opportunity horizon.

Supported horizons:

    15 min
    30 min
    60 min
    90 min
    120 min

Arbitrary interpolation between unsupported horizons is not part of the frozen production specification.

## Selected model

The selected future-track model uses:

- future ambient-temperature change,
- current track-minus-ambient thermal gap,
- mean future solar state.

Current thermal rate was tested and rejected.

Delta solar elevation was tested and rejected.

Solar geometry affects performance indirectly through future track state:

    solar state
        ->
    track heating / cooling
        ->
    track temperature
        ->
    performance

Solar state is not inserted directly into the frozen performance model.

## Calibration

Overall conformal coverage:

    nominal 80% -> 0.8064 observed
    nominal 90% -> 0.9085 observed

A major applicability limitation exists in 2022:

    80% coverage -> 0.6098
    90% coverage -> 0.6992

This is retained explicitly as evidence of distribution shift.

---

# 10. Monte Carlo Performance Outlook

For a supplied future horizon h:

1. project future track-state uncertainty;
2. sample a paired physics-coefficient bootstrap draw;
3. sample empirical performance residual magnitude with symmetric sign;
4. propagate all uncertainty into future four-lap performance change.

For each supported horizon, the system returns:

- expected delta speed,
- median delta speed,
- 80% prediction interval,
- 90% prediction interval,
- probability that delta speed > 0.

Approximate frozen mean 80% interval widths:

    15 min  -> 1.4659 mph
    30 min  -> 1.4751 mph
    60 min  -> 1.5129 mph
    90 min  -> 1.5437 mph
    120 min -> 1.5666 mph

Approximate frozen mean 90% interval widths:

    15 min  -> 2.4239 mph
    30 min  -> 2.4349 mph
    60 min  -> 2.4620 mph
    90 min  -> 2.4827 mph
    120 min -> 2.4984 mph

Future track-state uncertainty increases with horizon.

Performance uncertainty grows more slowly because empirical attempt-level residual variation dominates much of the final uncertainty width.

---

# 11. V2-B — Section Mechanism Validation

Section timing is used as mechanism evidence.

It is not used to manufacture additional training observations.

Final linkage:

    39 / 41 final physics transitions linked to usable section evidence

Each linked transition contains:

    9 common complete sections

Mean direction coherence across all linked transitions:

    0.723647

Median:

    0.777778

For non-trivial performance changes:

    |delta_v| >= 0.10 mph -> mean coherence 0.781481
    |delta_v| >= 0.20 mph -> mean coherence 0.843434
    |delta_v| >= 0.50 mph -> mean coherence 0.935185

Meaningful attempt-level performance changes are therefore generally spatially coherent.

Large thermal-model residuals are also frequently spatially coherent.

After controlling for absolute overall performance-change magnitude:

    partial Spearman(
        direction coherence,
        absolute residual
        | absolute delta_v
    )
    approximately -0.011

No strong independent section-pattern predictor of model residual is supported.

Final role:

    mechanism validation only

not:

    additional training data

and not:

    production predictor.

---

# 12. V2-C — Wind Residual Diagnostic

Wind remains physically relevant to qualifying performance.

However, available historical wind evidence consists of fixed-point or gridded proxies rather than the complete aerodynamic exposure experienced around the oval.

Diagnostic coverage:

    39 wind-linked transitions
    39/39 wind-speed change
    39/39 gust change
    38/39 wind-vector change

Magnitude-controlled partial Spearman relationships with absolute physics residual:

    |delta wind speed|   -> -0.031890
    |delta gust|         -> +0.199002
    wind-vector change   -> +0.208751
    mean wind speed      -> +0.028497
    mean gust            -> +0.060187

Relationships are not stable across years.

Therefore the evidence does not justify:

- a deterministic wind coefficient,
- a production heteroskedastic wind-residual model.

Wind is retained as:

- a plausible latent contributor,
- an interpretation limitation,
- a future prospective-data candidate.

---

# 13. External Regime Validation

The frozen 2020-2024 physics core was evaluated against:

    15 eligible 2025 hybrid-era repeat attempts

External results:

    MAE = 0.492 mph

    nominal 80% PI
    observed coverage = 80%

    nominal 90% PI
    observed coverage = 100%

    directional accuracy = 46.7%

Interpretation:

The model is useful as probabilistic physical-state decision support.

It is not a standalone classifier of whether the next attempt will improve.

---

# 14. Technical and Operational Regimes

Technical regime and qualifying-format regime are treated separately.

Technical changes test physical transferability.

Qualifying-format changes test operational applicability.

2020-2024:

    principal Aeroscreen / pre-hybrid reference regime

2025:

    hybrid-era external validation regime

2026:

    operational applicability boundary because weather disruption and revised qualifying procedure largely removed the normal initial-round repeat-attempt trade-off.

---

# 15. Final System Architecture

    HISTORICAL EVIDENCE
            |
            v
    IDENTIFIABILITY AUDIT
            |
            +-----------------------------+
            |                             |
            v                             v
    IDENTIFIABLE PHYSICS          NON-IDENTIFIABLE
    PERFORMANCE STATE             QUEUE OPPORTUNITY PROCESS
            |                             |
            |                             v
            |                       EXTERNAL LIVE INPUT
            |
            v
    USER-SUPPLIED HORIZON h
            |
            v
    V2-A FUTURE TRACK STATE
            |
            v
    PHYSICS MODEL
            |
            + paired coefficient uncertainty
            + future track-state uncertainty
            + empirical residual uncertainty
            |
            v
    MONTE CARLO PERFORMANCE OUTLOOK
            |
            + expected delta speed
            + 80% interval
            + 90% interval
            + probability of improvement

    DIAGNOSTIC LAYERS

    V2-B SECTION VALIDATION
        -> spatial mechanism evidence

    V2-C WIND DIAGNOSTIC
        -> residual identifiability / limitation

---

# 16. Supported Capability

The frozen system supports:

- conditional future performance inference at specified horizons;
- propagation of multiple uncertainty sources;
- probabilistic performance outlooks;
- section-level mechanism validation;
- wind residual-identifiability diagnostics;
- external technical-regime validation.

---

# 17. Unsupported Capability

The frozen system does not support:

- prediction of exact queue waiting time;
- prediction of exact next opportunity time;
- historical reconstruction of a reliable Lane 1 / Lane 2 queue model;
- autonomous retain / withdraw strategy;
- unique attribution of residual performance error to wind, tyres, fuel, setup, or driver;
- treating sections or laps as independent extra training observations;
- arbitrary interpolation outside the validated horizon interface.

---

# 18. Decision-Support Boundary

The system answers:

> If another opportunity occurs h minutes from now, what performance-change distribution should be expected?

A real retain / withdraw decision additionally requires external operational state such as:

- current qualifying rank,
- bubble position,
- competitor state,
- queue state,
- remaining session time,
- probability of receiving another run,
- interruption risk,
- consequences of sacrificing the current result,
- team-specific utility.

Therefore the final system is a component of a sequential decision-support architecture, not an autonomous race-strategy agent.

---

# 19. Natural Future Extension

A future prospective data-collection programme could record:

- exact queue entry time,
- Lane 1 / Lane 2 choice,
- withdrawal event,
- requeue event,
- pit-return event,
- live leaderboard state,
- interruptions,
- exact attempt start time.

That could support a separate opportunity model:

    p(H = h | live queue state)

which could eventually be combined with the frozen physical model:

    p(delta_v | H = h, physical state)

inside an explicit expected-utility decision layer.

Such a model is not inferred retrospectively from weak historical labels in the current project.

---

# 20. Final Methodological Principle

The project prioritizes identifiability over model complexity.

The central methodological sequence is:

    real strategy problem
        ->
    historical identifiability analysis
        ->
    rejection of weak targets
        ->
    physically identifiable subproblem
        ->
    probabilistic performance inference
        ->
    explicit capability boundary

The compactness of the final model is deliberate.

The difficulty of the project lies primarily in evidence reconstruction,
identifiability, uncertainty propagation, validation, and disciplined rejection
of unsupported precision rather than in model complexity alone.
""".strip()

SPEC.write_text(
    spec + "\n",
    encoding="utf-8"
)

manifest = {
    "project":
        "Indy 500 Qualifying Decision-Support Project",

    "version":
        "FINAL_V1",

    "status":
        "FROZEN",

    "freeze_time_utc":
        datetime.now(timezone.utc).isoformat(),

    "final_research_question": (
        "If another on-track opportunity occurs h minutes from now, "
        "what distribution of four-lap qualifying-performance change "
        "should be expected relative to the current official result?"
    ),

    "frozen_components": {
        "physics_core": {
            "transition_count": 41,
            "bootstrap_draw_count": 5000,
        },

        "v2a": {
            "role": "future physical-state model",
            "manifest_sha256": sha256(V2A),
        },

        "v2b": {
            "role": "section mechanism validation",
            "manifest_sha256": sha256(V2B),
        },

        "v2c": {
            "role": "wind residual identifiability diagnostic",
            "manifest_sha256": sha256(V2C),
        },
    },

    "validated_horizons_minutes": [
        15,
        30,
        60,
        90,
        120,
    ],

    "capability_boundary": {
        "predict_future_performance_distribution":
            True,

        "predict_queue_wait":
            False,

        "predict_exact_opportunity_time":
            False,

        "autonomous_retain_withdraw_decision":
            False,

        "section_rows_expand_training_n":
            False,

        "deterministic_wind_predictor":
            False,

        "heteroskedastic_wind_model":
            False,
    },

    "source_artifacts": {},
}

for p in required:
    manifest["source_artifacts"][str(p)] = {
        "sha256": sha256(p),
        "bytes": p.stat().st_size,
    }

manifest["system_specification"] = {
    "path": str(SPEC),
    "sha256": sha256(SPEC),
    "bytes": SPEC.stat().st_size,
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
INDY 500 QUALIFYING DECISION-SUPPORT PROJECT — FINAL PROJECT FREEZE
====================================================================================================

STATUS: FROZEN
VERSION: FINAL_V1

FINAL RESEARCH QUESTION
----------------------------------------------------------------------------------------------------
If another on-track opportunity occurs h minutes from now,
what distribution of four-lap qualifying-performance change
should be expected relative to the current official result?

FINAL COMPONENTS
----------------------------------------------------------------------------------------------------
Physics core:
41 same-car transitions
zero-intercept thermal response model
5000 paired coefficient bootstrap draws
empirical LOYO residual uncertainty

V2-A:
Future physical-state model
Supported horizons: 15 / 30 / 60 / 90 / 120 min

V2-B:
Section mechanism validation
39/41 linked transitions
diagnostic only

V2-C:
Wind residual identifiability diagnostic
39 linked transitions
no deterministic wind term
no heteroskedastic wind model

CAPABILITY BOUNDARY
----------------------------------------------------------------------------------------------------
SUPPORTED:
Conditional probabilistic four-lap performance outlook.

NOT SUPPORTED:
Queue waiting-time prediction.
Exact opportunity-time prediction.
Autonomous retain/withdraw decision.
Unique residual-mechanism attribution.

FINAL METHODOLOGICAL POSITION
----------------------------------------------------------------------------------------------------
The project prioritizes identifiability over model complexity.

Historical queue opportunity could not be reconstructed reliably enough
to justify a supervised historical target.

The opportunity horizon h is therefore treated as a scenario input.

The final system estimates:

p(delta_v | H = h, physical state)

rather than pretending to estimate:

p(H | incomplete historical queue state).

SYSTEM SPECIFICATION
----------------------------------------------------------------------------------------------------
{SPEC}

SHA256:
{sha256(SPEC)}

FINAL MANIFEST
----------------------------------------------------------------------------------------------------
{MANIFEST}

SHA256:
{sha256(MANIFEST)}

====================================================================================================
PROJECT STATUS: FINAL FROZEN
====================================================================================================
""".strip()

SUMMARY.write_text(
    summary + "\n",
    encoding="utf-8"
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
