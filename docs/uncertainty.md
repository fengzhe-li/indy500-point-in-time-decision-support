# Uncertainty architecture

## Propagated sources

### Physical-response coefficient uncertainty

Five thousand paired bootstrap draws preserve the joint dependence of the track and ambient coefficients. Drawing coefficients independently would create unsupported combinations.

### Future track-state uncertainty

Each horizon uses finite-sample residual calibration from leave-one-year-out future-state predictions. This uncertainty grows in importance with horizon and includes known weakness in the 2022 regime.

### Empirical performance residual uncertainty

Centered, symmetrized out-of-year residual magnitudes represent unresolved attempt-level effects. They include tyre preparation, setup, driver execution, wind exposure and other latent vehicle state without pretending to identify a unique cause.

## Ablation result

The empirical performance residual is the dominant contributor to interval width. Removing it reduces mean 80% interval width by 90.4%, 85.5%, 79.9%, 75.9% and 72.8% at 15, 30, 60, 90 and 120 minutes respectively.

This experiment removes one source at a time from a joint predictive system. It is a sensitivity analysis rather than an orthogonal variance decomposition.

## Probability semantics

P(Δv > 0) is conditional on the supplied opportunity horizon and physical scenario. It excludes the probability of receiving another run and the downside from withdrawing a current result. It is not overall strategy success.

