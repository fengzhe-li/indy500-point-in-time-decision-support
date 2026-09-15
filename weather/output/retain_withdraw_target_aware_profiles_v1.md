# Target-Aware Retain / Withdraw Profiles V1

Policy version: `RETAIN_WITHDRAW_TARGET_AWARE_PROFILE_V1`
Policy hash: `e1e442abde646a21d6f2724dd33abb2828b1ef80becbf80ec3b7e24be579ef0e`

## Purpose

Convert the frozen retain/withdraw Monte Carlo risk layer into target-aware success probabilities without introducing arbitrary utility weights.

## Gain targets

- `+0.10 mph`
- `+0.25 mph`
- `+0.50 mph`
- `+1.00 mph`

For any retained speed S and gain target G, the corresponding absolute target is S + G.

These are sensitivity targets, not reconstructed historical leaderboard thresholds.

## Combination rule

`P(target success)` combines:

- cutoff completion probability;
- baseline-condition recovery posterior mean;
- empirical normal-branch target rate;
- empirical recovery-like target rate.

## Decision outputs

The profile reports target-success probability, ordinary improvement probability, short-of-target probability, completed-run downside, and no-completion risk.

## Recommendation boundary

No retain/withdraw recommendation is issued.
A final recommendation layer still requires either a defensible external objective or an explicitly frozen risk preference.

## Status

**TARGET_AWARE_DECISION_PROFILES_READY**