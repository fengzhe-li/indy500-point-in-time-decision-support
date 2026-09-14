# Indy 500 Requalification / Result-Withdrawal Decision Support

**Physics-Conditioned Probabilistic Performance Inference for Indianapolis 500 Requalification / Result-Withdrawal Decision Support**

A multi-season motorsport decision-support project built from fragmented qualifying, timing and environmental records. The original pit-wall question was whether to preserve an existing qualifying result or withdraw it for priority and another attempt. Historical reconstruction showed that the queue/opportunity process could not be identified reliably enough for a defensible queue-time model, so the problem was deliberately reformulated.

> **Final scientific question:** If another on-track opportunity occurs `h` minutes from now, what distribution of four-lap qualifying-performance change should be expected relative to the current official result?

The system estimates **p(Δv | H = h)**. It does **not** estimate `P(H=h)`, predict queue waiting time, or automatically recommend a withdraw/retain strategy.

## Why this project is technically difficult

The final regression is intentionally compact; the difficult part is the system around it:

- multi-season attempt chronology reconstruction from fragmented evidence;
- provenance, evidence hierarchy and quarantine of ambiguous records;
- explicit **identifiability analysis** before choosing the modelling target;
- same-car differencing to reduce persistent configuration effects;
- physics-conditioned thermal response modelling;
- future track-state inference using current thermal gap and future solar state;
- leave-one-year-out evaluation and paired bootstrap coefficient uncertainty;
- horizon-specific conformal calibration;
- Monte Carlo propagation of parameter, future-state and empirical performance uncertainty;
- section-level mechanism and wind residual diagnostics;
- uncertainty-source ablation and a 135-scenario stress test;
- regulation-aware comparison across pre-Aeroscreen, Aeroscreen/pre-hybrid, and hybrid-era evidence;
- frozen 2020–2024 reference core evaluated on 2025 hybrid-era repeat attempts;
- a separate operational layer preserving the distinction between calibrated anchors and interpolated presentation values.

## Architecture

```text
Real strategy problem
    ↓
Data archaeology + chronology reconstruction
    ↓
Identifiability analysis
    ├── queue/opportunity process P(H|Q): not reliably reconstructable
    └── performance process p(Δv|H=h): defensibly identifiable
             ↓
41 frozen same-car transitions (2020–2024)
             ↓
Physics-conditioned performance core
             + future track-state model
             + bootstrap / conformal / residual uncertainty
             ↓
Monte Carlo conditional performance distribution
             ↓
FINAL_V2 calibrated anchors: 15 / 30 / 60 / 90 / 120 min
             ↓
OPERATIONAL_CURVE_V2 presentation layer
             ↓
Human pit-wall decision + external live context
```

## Frozen performance core

`Δv = β_track ΔT_track + β_ambient ΔT_ambient + ε`

- `β_track = -0.03482533`
- `β_ambient = +0.18239338`

The ambient coefficient is treated conditionally rather than as a universal causal effect because the retained thermal variables are correlated.

## Regulation-aware analysis

The project investigates three technical-regime periods, but they do not all play the same statistical role.

| Technical period | Role | Quantitative repeat-transition sample |
|---|---|---:|
| 2018–2019 pre-Aeroscreen | early-regime investigation | 2019: **10** clean transitions; 2018 insufficient after filtering |
| 2020–2024 Aeroscreen / pre-hybrid | frozen production reference | **41** transitions |
| 2025–2026 hybrid-era / later regime | external transfer + applicability analysis | 2025: **23** primary physics-safe transitions; 2026 used mainly as a format/applicability boundary case |

For the three quantitatively comparable samples, the same zero-intercept thermal-response form was fitted:

| Regime | N | β_track | β_ambient |
|---|---:|---:|---:|
| 2019 pre-Aeroscreen | 10 | -0.05059 | +0.17008 |
| 2020–2024 reference | 41 | -0.03483 | +0.18239 |
| 2025 hybrid era | 23 | -0.06308 | +0.12100 |

All three quantitative regime fits preserve the same coefficient signs (`β_track < 0`, `β_ambient > 0`). The goal is not to merge all years into one larger training set, but to test whether the compact physical-response structure remains qualitatively stable across materially different vehicle eras.

The **technical regime** and **qualifying-format regime** are kept separate. In particular, the 2026 event is retained mainly as an applicability boundary case because the weather-modified qualifying format changed the normal repeat-attempt decision structure.

## Future physical-state inference

The retained future-track specification uses future horizon, ambient trajectory, current thermal gap and mean future solar state. Solar informs track heating/cooling; it is **not** inserted as a direct qualifying-speed term.

![Future track model selection](figures/future_track_model_selection.svg)

Supported calibrated horizons are exactly **15, 30, 60, 90 and 120 minutes**. The 120-minute limit is an empirical/model-validation boundary, not a rules-derived limit.

## Calibrated uncertainty

Future track-state uncertainty is calibrated horizon-by-horizon. Aggregate historical coverage is close to nominal, while the difficult 2022 held-out season is retained as an explicit distribution-shift limitation.

![Conformal calibration](figures/conformal_calibration.svg)

The final distribution propagates coefficient uncertainty, future physical-state uncertainty and empirical unexplained attempt-level performance variation.

![Uncertainty ablation](figures/uncertainty_ablation.svg)

The empirical performance residual dominates final predictive width. This is an ablation/sensitivity result, not a strict variance decomposition.

## External 2025 evaluation

The frozen 2020–2024 core was evaluated on **15 eligible 2025 hybrid-era repeat-attempt cases** without refitting the reference core.

| Metric | Result |
|---|---:|
| Cases | 15 |
| MAE | **0.492 mph** |
| Median absolute error | **0.425 mph** |
| RMSE | **0.610 mph** |
| Nominal 80% PI coverage | **80.0%** |
| Nominal 90% PI coverage | **100.0%** |
| Directional accuracy | **46.7%** |

The 15-case external evaluation and the 23-transition 2025 regime-comparison sample serve different purposes and should not be conflated. The former evaluates the frozen end-to-end inference chain; the latter supports regulation-aware coefficient comparison.

The weak directional classification is important: this is better interpreted as **probabilistic physical-state decision support** than as a standalone binary next-attempt predictor.

## Operational presentation layer

`FINAL_V2` is the scientific/model layer. `OPERATIONAL_CURVE_V2` is a derived visualization layer and remains separate.

![Operational performance outlook](figures/operational_performance_outlook.svg)

Only the five anchors are independently calibrated. Intermediate 15–120 minute values are piecewise-linear interpolation of frozen output summaries for visualization, not new Monte Carlo calibrations. No output beyond 120 minutes is production-supported.

## Selected diagnostics

**V2-B — section mechanism analysis.** Meaningful changes are generally broad and spatially coherent rather than isolated to a few sections. This improves mechanism interpretation but does not justify expanding the predictive feature set.

**V2-C — wind diagnostic.** Available historical wind proxies did not provide sufficiently stable evidence to justify an explicit deterministic or heteroskedastic wind term. This does not imply that wind has no physical effect.

**V2-D — uncertainty ablation.** Empirical attempt-level residual variation dominates final predictive uncertainty.

**V2-E — stress testing.** 135 combinations of thermal gap × ambient trajectory × solar state × horizon were evaluated systematically.

## Repository map

```text
├── README.md
├── docs/                  # methodology and design rationale
├── data/                  # canonical and modelling data
├── figures/               # technical visualisations
├── pipeline/              # reconstruction, provenance, eligibility, validation
├── src/                   # selected V2 modelling and diagnostic scripts
├── results/final_v2/      # frozen specification, manifests and QA outputs
├── paper/                 # final technical report
├── requirements.txt
└── .gitignore
```

The public repository is intentionally broader than a minimal model demo: it retains evidence of the reconstruction, validation and uncertainty-engineering work that makes the compact final model defensible, while excluding caches and redundant exploratory artefacts.

## Status

- Scientific/model layer: **FINAL_V2 — FROZEN**
- Operational visualization layer: **OPERATIONAL_CURVE_V2 — FROZEN**
- Technical periods investigated: **2018–2019 / 2020–2024 / 2025–2026**
- Frozen production reference: **2020–2024**
- Quantitative external technical-regime comparison: **2019 and 2025**
- End-to-end external evaluation: **2025**
- 2026 role: **qualifying-format / applicability boundary case**
- Supported future-opportunity anchors: **15 / 30 / 60 / 90 / 120 min**

## Scope boundary

This does not replace pit-wall judgement. A real withdraw/retain decision also depends on live queue state, leaderboard position, competitors, driver feedback, team risk tolerance and race-control context. The project isolates the historically defensible physical-performance component and quantifies it probabilistically.

---

**Fengzhe Li — University College London**
