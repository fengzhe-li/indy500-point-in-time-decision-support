# Indy 500 Requalification / Result-Withdrawal Decision Support

**Physics-conditioned probabilistic performance inference for Indianapolis 500 qualifying**

> Historical reconstruction showed that queue state, withdrawal timing, requeue behaviour, opportunity timing and team intent were not consistently observable enough to support a defensible end-to-end strategy model. The project therefore reformulates the problem as an identifiable conditional inference task: **if another qualifying opportunity occurs `h` minutes from now, what distribution of four-lap performance change should be expected relative to the car's current official result?**

The scientific system estimates **p(Δv | H = h)**. It does **not** estimate `P(H=h)`, predict queue waiting time, or autonomously decide whether a result should be withdrawn.

## Research architecture

The project combines historical evidence engineering, physical-state reconstruction, a compact thermal-response model, future track-state inference, calibrated uncertainty, Monte Carlo propagation, diagnostics, external-regime evaluation and a separately frozen operational presentation layer.

![Identifiability-driven architecture](figures/figure1_identifiability_architecture.svg)

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

The weak directional accuracy is retained as an important result: the system is **probabilistic physical-performance decision support**, not a deterministic next-attempt classifier.

## Frozen physical-response core

For evidence-qualified consecutive attempts by the same car:

`Δv = β_track ΔT_track + β_ambient ΔT_ambient + ε`

- `β_track = -0.03482533`
- `β_ambient = +0.18239338`

The ambient coefficient is interpreted conditionally rather than as a universal causal effect.

## Final-paper figures

The repository now keeps a paper-aligned figure set separately from legacy/project-development figure names. The numbering below follows the final manuscript.

### Figure 1 — future track-temperature model selection

![Paper Figure 1](figures/paper/figure01_future_track_model_selection.svg)

The retained M2b specification combines future horizon, ambient trajectory, current thermal gap and mean future solar state. Solar informs future track state rather than entering the speed model directly.

### Figure 2 — future track-state conformal calibration

![Paper Figure 2](figures/paper/figure02_future_track_conformal_calibration.svg)

Aggregate calibration is close to nominal, while the difficult 2022 held-out season remains an explicit distribution-shift/applicability warning.

### Additional diagnostics and operational figures

The repository also retains the broader project figure gallery: uncertainty ablation, V2-E stress testing, 2025 external evaluation, operational performance and improvement-probability curves, LOYO coefficient stability, queue-context overlays, supported-horizon external evaluation and beyond-120-minute appendix diagnostics. See [`figures/README.md`](figures/README.md).

## Scientific and operational layers

`FINAL_V2` is the frozen scientific/model layer. It propagates future track-state uncertainty, paired coefficient uncertainty and symmetrised empirical performance-residual uncertainty at the calibrated horizons `{15, 30, 60, 90, 120}` minutes.

`OPERATIONAL_CURVE_V2` is a separately frozen derived visualization layer. It preserves the five calibrated anchors exactly and uses piecewise-linear interpolation between them for presentation. Intermediate minute-level values are **not** newly calibrated forecasts, and the production-supported domain does not extend beyond 120 minutes.

## External 2025 evaluation

The frozen 2020–2024 reference core was evaluated without refitting on **15 eligible 2025 hybrid-era repeat-attempt cases**. MAE was **0.492 mph**, directional accuracy **46.7%**, and nominal 80% / 90% predictive-interval coverage was **80% / 100%**. The result supports the uncertainty-oriented interpretation more strongly than exact directional prediction.

The broader 2025 regime-comparison transition sample serves a different purpose: regulation-aware coefficient transferability analysis. It is not the same sample as the 15-case end-to-end external evaluation.

## Regulation-aware interpretation

The production model remains the frozen **2020–2024** reference core. Earlier and later technical regimes are used as transferability/applicability evidence rather than silently pooled into training. The available evidence preserves the qualitative coefficient directions across the comparable 2019, 2020–2024 and 2025 samples, but does not justify claiming invariant coefficients. The weather-modified 2026 qualifying format is treated principally as an operational applicability boundary.

## What the model does not claim

It does not predict exact queue duration, `P(H|Q)`, Lane 1 versus Lane 2 waiting time, competitor response, weather-forecast skill, an optimal waiting time, or an automatic withdraw/retain strategy. A real pit-wall decision must combine this conditional physical-performance evidence with live leaderboard and queue state, remaining session time, driver feedback, competitors, team objectives and engineering judgement.

## Repository map

```text
├── README.md
├── docs/                  # research boundary, methodology and model documentation
├── data/                  # canonical, provenance and plotting data
├── figures/
│   ├── paper/             # numbering aligned to the final manuscript
│   └── ...                # broader diagnostic/project figure gallery
├── pipeline/              # reconstruction, provenance, eligibility and validation
├── src/                   # selected V2 modelling and diagnostic implementations
├── results/               # frozen outputs, QA and external evaluation
├── paper/                 # technical report
├── requirements.txt
└── .gitignore
```

## Status

- Scientific/model layer: **FINAL_V2 — FROZEN**
- Operational visualization layer: **OPERATIONAL_CURVE_V2 — FROZEN**
- Frozen production reference: **2020–2024**
- End-to-end external evaluation: **2025**
- Supported scientific anchors: **15 / 30 / 60 / 90 / 120 min**

---

**Fengzhe Li — University College London**
