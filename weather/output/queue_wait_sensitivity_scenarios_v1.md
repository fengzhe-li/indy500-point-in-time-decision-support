# Queue / Wait Sensitivity Scenarios V1

Policy version: `QUEUE_WAIT_SENSITIVITY_SCENARIOS_V1`
Policy hash: `683a5d2e8477187f1d4c453eeb4e6c4859e87100725ed7459bf30a9c758e6efb`

## Central rule

Historical individual queue waiting time is unobserved.
Therefore V1 does not fit or claim a historical queue-wait distribution.

Instead, the simulator will sweep explicit latent pre-run-delay scenarios.

## Wait scenarios

- `5 minutes`
- `15 minutes`
- `30 minutes`
- `45 minutes`

Each scenario represents the time from withdrawal until the timed run begins and therefore includes queue, staging, and release overhead.

These values are assumptions for sensitivity analysis, not historical estimates.

## Timed-run duration

- Median complete four-lap run: `155.779 s`
- Q95 complete four-lap run: `158.103 s`

Withdraw-to-completion time is defined as latent pre-run delay plus timed-run duration.

## Cutoff

2024 uses the exact supported session cutoff `2024-05-18 21:50 UTC`.

If required withdraw-to-completion time exceeds time remaining, the branch becomes the explicit `NO_COMPLETED_RERUN_BEFORE_CUTOFF` outcome.

## Important boundary

- No queue position is inferred.
- No queue wait is estimated from attempt spacing.
- No stochastic queue distribution is fitted.
- No Monte Carlo performance draw is made yet.
- Latest-withdraw timestamps are conditional scenario references, not reconstructed historical decisions.

## Next phase

Phase 6C may combine these wait scenarios with the frozen repeat-performance empirical uncertainty to build the first retain/withdraw Monte Carlo engine.

## Status

**QUEUE_WAIT_SENSITIVITY_SCENARIOS_READY**