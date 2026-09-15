# Retain / Withdraw Decision Semantics V1

Policy ID: `RETAIN_WITHDRAW_DECISION_SEMANTICS_V1`
Policy hash: `4c120fe7d799401d5a1774812db5cbc65ff60b6c9498b851f1953d4d50fbc31b`

## Central principle

V1 separates probabilistic outcome reporting from normative recommendation.

The simulator may report the probability and magnitude of improvement, loss, and no completed rerun without assigning arbitrary utility weights.

## Gain thresholds

- `+0.10 mph`
- `+0.25 mph`
- `+0.50 mph`
- `+1.00 mph`

These are sensitivity targets, not historical Top-12 or bump thresholds.

If a defensible external target speed becomes available, `required_gain = target_speed - retained_speed` can be evaluated without retraining the performance model.

## Recommendation boundary

No retain/withdraw recommendation is enabled in Phase 6D.
A recommendation requires either an explicit target objective or an explicitly frozen utility/risk policy.

## Status

**RETAIN_WITHDRAW_DECISION_SEMANTICS_FROZEN**