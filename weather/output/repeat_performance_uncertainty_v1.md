# Repeat-Performance Empirical Uncertainty V1

## Purpose

Represent repeat-attempt performance uncertainty without promoting an unstable point-prediction model.

## Primary sample

- Primary rows: `39`
- Normal diagnostic rows: `35`
- Recovery-like diagnostic rows: `4`

## Normal branch

- Median delta: `0.080000 mph`
- Zero-delta MAE: `0.296514 mph`
- Empirical gain probability: `0.657143`

## Recovery-like branch

- Rows: `4`
- Median delta: `2.716500 mph`

Recovery probability is represented with Beta-Binomial uncertainty rather than a trained classifier.

## Important boundary

- Diagnostic recovery labels are not ground-truth causal labels.
- No recovery classifier is trained.
- No parametric Normal performance assumption is imposed.
- No queue or decision utility is modeled here.
- These distributions are intended for later Monte Carlo sensitivity analysis.

## Status

**REPEAT_PERFORMANCE_UNCERTAINTY_READY**