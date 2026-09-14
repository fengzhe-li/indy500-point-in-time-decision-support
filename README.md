# Indy 500 Requalification / Result-Withdrawal Decision Support

**Research + evidence engineering + probabilistic decision support for Indianapolis 500 qualifying**

> **This project does not attempt to predict whether a team should requalify.**
>
> Historical analysis showed that queue state, withdrawal timing, requeue behaviour, opportunity timing and team intent were not consistently observable enough to support a defensible end-to-end strategy model.
>
> The problem was therefore reformulated into an identifiable conditional inference task:
>
> **If another qualifying opportunity occurs `h` minutes from now, how might the distribution of four-lap performance change relative to the car's current official result?**

The system estimates **p(Δv | H = h)**. It does **not** estimate `P(H=h)`, predict queue waiting time, or autonomously decide whether to withdraw a result.

![Identifiability-driven architecture](figures/figure1_identifiability_architecture.svg)

## Why this project is technically difficult

The final response model is intentionally compact. The difficult part is constructing a defensible system around it:

- multi-season data archaeology and attempt chronology reconstruction from fragmented evidence;
- source registry, field-level provenance, evidence hierarchy, conflict handling and quarantine;
- explicit **identifiability analysis** before choosing the modelling target;
- same-car differencing to reduce persistent car/driver/configuration effects;
- physics-conditioned thermal response inference;
- future track-state inference from horizon, ambient trajectory, current thermal gap and solar state;
- leave-one-year-out evaluation and paired bootstrap coefficient uncertainty;
- horizon-specific conformal calibration;
- Monte Carlo propagation of parameter, future-state and empirical performance uncertainty;
- section-level mechanism diagnostics and wind residual diagnostics;
- uncertainty-source ablation and a 135-scenario stress test;
- regulation-aware comparison across pre-Aeroscreen, Aeroscreen/pre-hybrid and hybrid-era evidence;
- frozen 2020–2024 reference core evaluated without refitting on later 2025 hybrid-era cases;
- a separate operational layer that does not pretend interpolated minute-level outputs are newly calibrated forecasts.

## Key quantitative results

| Result | Value |
|---|---:|
| Frozen same-car reference transitions | **41** |
| External 2025 end-to-end cases | **15** |
| External MAE | **0.492 mph** |
| External median absolute error | **0.425 mph** |
| External RMSE | **0.610 mph** |
| External 80% PI coverage | **80.0%** |
| External 90% PI coverage | **100.0%** |
| External directional accuracy | **46.7%** |
| Calibrated horizons | **15 / 30 / 60 / 90 / 120 min** |
| Systematic V2-E stress-test scenarios | **135** |

The weak directional accuracy is not hidden: it is evidence that thermal state alone is insufficient for deterministic next-attempt classification. The system is therefore positioned as **probabilistic physical-performance decision support**, not an autonomous strategy predictor.

## Frozen performance core

For evidence-qualified consecutive attempts by the same car:

`Δv = β_track ΔT_track + β_ambient ΔT_ambient + ε`

- `β_track = -0.03482533`
- `β_ambient = +0.18239338`

The ambient coefficient is treated as conditional rather than a universal causal effect because the retained thermal variables are correlated.

## Regulation-aware analysis

Three technical-regime periods were investigated, but they deliberately play different statistical roles.

| Technical period | Role | Quantitative repeat-transition sample |
|---|---|---:|
| 2018–2019 pre-Aeroscreen | early-regime investigation | 2019: **10** clean transitions; 2018 insufficient after filtering |
| 2020–2024 Aeroscreen / pre-hybrid | frozen production reference | **41** transitions |
| 2025–2026 hybrid-era / later regime | external transfer + applicability analysis | 2025: **23** primary physics-safe transitions; 2026 mainly a format/applicability boundary case |

For the three quantitatively comparable samples:

| Regime | N | β_track | β_ambient |
|---|---:|---:|---:|
| 2019 pre-Aeroscreen | 10 | -0.05059 | +0.17008 |
| 2020–2024 reference | 41 | -0.03483 | +0.18239 |
| 2025 hybrid era | 23 | -0.06308 | +0.12100 |

All three quantitative fits preserve the same coefficient signs (`β_track < 0`, `β_ambient > 0`). The objective is not to pool every year into a larger training set, but to examine whether the compact physical-response structure remains qualitatively stable across materially different technical eras.

Technical regime and qualifying-format regime are kept separate. The weather-modified 2026 qualifying format is retained primarily as an applicability-boundary case rather than treated as an equivalent external validation sample.

## Future physical-state inference

The retained future-track specification uses future horizon, ambient trajectory, current thermal gap and mean future solar state. Solar informs track heating/cooling; it is **not** inserted as a direct qualifying-speed term.

![Future track model selection](figures/future_track_model_selection.svg)

The scientific layer is calibrated only at **15, 30, 60, 90 and 120 minutes**. The 120-minute limit is an empirical/model-validation boundary, not a rules-derived limit.

## Calibrated uncertainty

Future track-state uncertainty is calibrated horizon-by-horizon. Aggregate historical coverage is close to nominal, while the difficult 2022 held-out season remains visible as a distribution-shift limitation.

![Conformal calibration](figures/conformal_calibration.svg)

The final performance distribution propagates coefficient uncertainty, future physical-state uncertainty and empirical unexplained attempt-level performance variation.

![Uncertainty ablation](figures/uncertainty_ablation.svg)

The empirical performance residual dominates final predictive width. This is an ablation/sensitivity result, not a strict variance decomposition.

## External 2025 evaluation

The frozen 2020–2024 core was evaluated on **15 eligible 2025 hybrid-era repeat-attempt cases** without refitting the reference core.

The 15-case end-to-end external evaluation and the 23-transition 2025 regime-comparison sample serve different purposes and should not be conflated: the former evaluates the frozen inference chain; the latter supports regulation-aware coefficient comparison.

## Operational presentation layer

`FINAL_V2` is the frozen scientific/model layer. `OPERATIONAL_CURVE_V2` is a separate derived presentation layer.

![Operational performance outlook](figures/operational_performance_outlook.svg)

Only the five anchor horizons are independently calibrated. Intermediate 15–120 minute values are piecewise-linear interpolation of frozen output summaries for visualization; they are **not** new Monte Carlo calibrations. No output beyond 120 minutes is treated as production-supported.

## What this project supports — and what it does not

### Supported by the evidence

- Measurable thermal-state change contains a repeatable component of same-car four-lap performance change.
- The retained physical-response structure shows useful probabilistic behaviour when applied to a later 2025 hybrid-era sample.
- Physical state can materially shift the centre and improvement probability of the future performance distribution.
- Unresolved attempt-level variation dominates total predictive uncertainty.
- Public historical evidence is insufficient for a defensible queue-duration or autonomous requalification model.

### Not claimed

- The next attempt will definitely be faster or slower.
- Queue waiting time can be predicted from this historical reconstruction.
- Lane 1 versus Lane 2 can be recommended by this model.
- The model can decide whether a team should withdraw its current result.
- Thermal coefficients are invariant across technical eras.
- Weather-forecast skill has been externally validated merely because realised-environment performance inference has been evaluated.

## Rejected extensions are results too

Several plausible extensions were deliberately rejected or kept outside the scientific core:

- **Queue-time predictor** — rejected because the historical opportunity process was not reliably identifiable.
- **Direct solar performance term** — rejected; solar remains on the physical pathway through future track state.
- **Wind performance term** — not retained because historical support was not sufficiently stable across years.
- **Unsupported feature expansion** — diagnostics were used to test mechanisms, not automatically convert every correlation into a production feature.
- **Arbitrary minute-level scientific forecasts** — rejected; minute-level operational interpolation is explicitly separated from the five calibrated anchors.
- **Pooling 2025 into the frozen reference fit** — rejected to preserve external-evaluation integrity.

## Selected diagnostics

**V2-B — section mechanism analysis.** Meaningful performance changes are generally broad and spatially coherent rather than isolated to a few sections. This improves mechanism interpretation but does not justify expanding the predictive feature set.

**V2-C — wind diagnostic.** Available historical wind proxies did not provide sufficiently stable evidence to justify an explicit deterministic or heteroskedastic wind term. This does not imply that wind has no physical effect.

**V2-D — uncertainty ablation.** Empirical attempt-level residual variation dominates final predictive uncertainty.

**V2-E — stress testing.** 135 combinations of thermal gap × ambient trajectory × solar state × horizon were evaluated systematically.

## Repository map

```text
├── README.md
├── docs/                  # research boundary, methodology and model documentation
├── data/                  # canonical, provenance and plotting data
├── figures/               # technical visualisations
├── pipeline/              # reconstruction, provenance, eligibility and validation
├── src/                   # selected V2 modelling and diagnostic implementations
├── results/               # frozen outputs, QA and external evaluation
├── paper/                 # technical report
├── requirements.txt
└── .gitignore
```

The public repository is intentionally broader than a minimal ML demo: it retains evidence of the reconstruction, validation, negative results and uncertainty engineering that make the compact final model defensible, while excluding caches and redundant exploratory artefacts.

## Status

- Scientific/model layer: **FINAL_V2 — FROZEN**
- Operational visualization layer: **OPERATIONAL_CURVE_V2 — FROZEN**
- Technical periods investigated: **2018–2019 / 2020–2024 / 2025–2026**
- Frozen production reference: **2020–2024**
- Quantitative cross-regime comparison: **2019 / 2020–2024 / 2025**
- End-to-end external evaluation: **2025**
- 2026 role: **qualifying-format / applicability boundary case**
- Supported future-opportunity anchors: **15 / 30 / 60 / 90 / 120 min**

## Scope boundary

A real pit-wall withdraw/retain decision also depends on live queue state, leaderboard position, competitors, driver feedback, team risk tolerance and race-control context. This project isolates the historically defensible physical-performance component and quantifies it probabilistically so that it can be combined with those live inputs and engineering judgement.

---

**Fengzhe Li — University College London**
