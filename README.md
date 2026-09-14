# Indy 500 Requalification / Result-Withdrawal Decision Support

**Physics-Conditioned Probabilistic Performance Inference for Indianapolis 500 Requalification / Result-Withdrawal Decision Support**

This project studies a specific pit-wall question in Indianapolis 500 qualifying:

> If another on-track opportunity occurs *h* minutes from now, how might four-lap qualifying performance change relative to the car's current official result?

The original idea was broader: support the practical decision between preserving an existing result and waiting for another run, or withdrawing that result to gain higher requalification priority. Historical reconstruction showed that queue entry, lane state, withdrawal timing, requeue behaviour, live queue position and team intent were not consistently identifiable across seasons. Rather than fitting a weak queue-time target, the project separates **opportunity uncertainty** from **physical-performance uncertainty**.

The scientific model therefore estimates

\[
p(\Delta v \mid H=h)
\]

rather than

\[
P(H=h).
\]

In practical terms: this is a **requalification / result-withdrawal decision-support reference**, not an automated strategy recommender.

## What the system does

- Reconstructs multi-season Indy 500 qualifying evidence at attempt level.
- Uses same-car repeat attempts to reduce persistent between-car performance differences.
- Fits a compact zero-intercept physical-response model for four-lap speed change.
- Models future track-temperature change separately from performance response.
- Propagates future-state uncertainty, paired coefficient uncertainty and empirical performance residuals by Monte Carlo simulation.
- Produces calibrated performance distributions at 15, 30, 60, 90 and 120 minute future-opportunity horizons.
- Provides a derived operational 15–120 minute visualization layer without pretending that every intermediate minute is independently calibrated.
- Keeps live queue / pit-wall context outside the physical model so a plausible opportunity window can be overlaid without claiming to predict queue waiting time.

## Frozen core

The frozen 2020–2024 same-car performance core contains **41 evidence-qualified transitions**.

The retained physical-response model is

\[
\widehat{\Delta v}_{physical}
= -0.03482533\,\Delta T_{track}
+ 0.18239338\,\Delta T_{ambient}.
\]

The ambient coefficient is interpreted conditionally, not causally, because the retained thermal predictors are correlated.

## External evaluation

The frozen 2020–2024 inference core was evaluated on **15 eligible 2025 hybrid-era repeat attempts**.

| Metric | Result |
|---|---:|
| Mean absolute error | 0.492 mph |
| Median absolute error | 0.425 mph |
| RMSE | 0.610 mph |
| Nominal 80% PI coverage | 80% |
| Nominal 90% PI coverage | 100% |
| Directional accuracy | 46.7% |

The limited directional accuracy is important: this project is better interpreted as **probabilistic physical-state decision support** than as a binary predictor of whether the next attempt will improve.

## Scientific vs operational layers

```text
FINAL_V2
= scientific / modelling layer

15 / 30 / 60 / 90 / 120 min
= independently calibrated anchors

OPERATIONAL_CURVE_V2
= derived 15–120 min presentation layer

external queue / pit-wall context
= determines which part of the curve is operationally relevant
```

No queue-time distribution, optimal waiting time, or automatic withdraw / retain recommendation is inferred.

## Repository structure

```text
.
├── README.md
├── paper/
│   └── final-paper.pdf
├── figures/
│   └── publication and diagnostic figures
├── data/
│   └── documented modelling / plotting data included where appropriate
├── src/
│   └── reproducible analysis and plotting code
├── results/
│   └── frozen FINAL_V2 and external-evaluation summaries
├── docs/
│   └── methodology and project notes
└── requirements.txt
```

## Key modelling boundary

The model answers:

> **Assume another on-track opportunity occurs after a specified amount of time. What distribution of performance change is expected?**

It does **not** answer:

- When will the next opportunity occur?
- What is the probability that another attempt will occur?
- Should the team withdraw the current result?
- What is the optimal waiting time?

Those decisions depend on live queue state, remaining session time, leaderboard position, competitor behaviour, vehicle condition, driver feedback and team risk tolerance.

## Author

**Fengzhe Li**  
University College London  
London, United Kingdom

## Status

`FINAL_V2` scientific layer frozen.  
`OPERATIONAL_CURVE_V2` derived presentation layer frozen.

This repository is being organized as a reproducible project portfolio around the final frozen analysis, rather than as a dump of every exploratory intermediate file.
