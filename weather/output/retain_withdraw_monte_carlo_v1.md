# Retain / Withdraw Monte Carlo Prototype V1

Policy version: `RETAIN_WITHDRAW_MONTE_CARLO_V1`
Policy hash: `d2cd3f54f3398999d73c5503cb26e3a1acca8d7be420bb74541dd612b9d1c22e`

## Purpose

Combine frozen repeat-performance uncertainty with explicit queue/wait sensitivity scenarios.

This is the first Monte Carlo retain/withdraw prototype, but it does not yet apply leaderboard or utility semantics.

## Retain branch

Retain deterministically preserves the current retained speed.

## Withdraw branch

Each draw samples:

- recovery probability uncertainty from the frozen Beta posterior;
- normal or recovery-like empirical performance delta;
- empirical complete four-lap run duration;
- a fixed outer latent pre-run-delay sensitivity scenario.

If wait plus sampled run duration exceeds time remaining, the outcome is `NO_COMPLETED_RERUN_BEFORE_CUTOFF`.

## Important boundary

- Wait values are sensitivity assumptions.
- No historical queue-wait distribution is claimed.
- No numeric utility function is applied.
- No leaderboard / Top-12 / bump threshold is applied.
- No recommendation is issued yet.

## Next phase

Phase 6D should define explicit decision utility and threshold semantics before a recommendation engine is allowed to compare retain versus withdraw.

## Status

**RETAIN_WITHDRAW_MONTE_CARLO_V1_COMPLETE**