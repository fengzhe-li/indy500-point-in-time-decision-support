# Decision Robustness / Sensitivity Envelope V1

Policy version: `DECISION_ROBUSTNESS_ENVELOPE_V1`
Policy hash: `957026d0fdecd88e4af9bada85c293064350365f4d7b62e86e59c3f8eb0231f7`

## Purpose

Aggregate the major supported uncertainty diagnostics into a display-ready robustness envelope.

## Included sensitivity sources

- leave-one-year-out performance / recovery recalibration;
- recovery Beta prior sensitivity;
- explicit wait scenarios;
- cutoff feasibility;
- target-gain level.

## Central policy

The central estimate remains the frozen V1 full-data Beta(1,1) recovery mixture.

Alternative priors are used only for sensitivity analysis.

## Robustness envelope

The lower and upper bounds are descriptive min/max sensitivity bounds across the central estimate, LOYO results, and recovery-prior sensitivity.

They are NOT frequentist confidence intervals and NOT Bayesian credible intervals.

Maximum conditional envelope width: `0.151282`

## Cutoff

For cutoff-blocked scenarios the unconditional target-success probability and its envelope are zero.

## Recommendation boundary

No retain/withdraw recommendation is issued.
The envelope is intended to expose robustness before any final risk policy is introduced.

## Status

**DECISION_ROBUSTNESS_ENVELOPE_READY**