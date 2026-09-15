# Queue / Wait Uncertainty Design V1

Policy ID: `QUEUE_WAIT_UNCERTAINTY_POLICY_V1`
Policy hash: `181e8000471333de5348722998444fcf40ff49807db0f2a0845631d3de21e707`

## Central evidence conclusion

Historical evidence does not support direct reconstruction of individual queue waiting time.

Defensible direct queue-wait pairs: `0`

Supported attempt timestamps may be used only as a system-throughput sanity-check proxy. They must not be interpreted as queue-entry times or individual queue waits.

## Timed-run duration

Complete four-lap duration rows: `260`

Timed-run duration is empirically supported and may be used as one component of withdraw-to-completion time.

## Session cutoff

2024 exact 21:50 UTC cutoff confirmed: `True`

Other years must not receive invented hard cutoff times until equivalent evidence is verified.

## Simulator policy

Retain is the deterministic current-result branch.
Withdraw is a probabilistic branch combining latent wait uncertainty, timed-run duration, cutoff risk, and frozen repeat-performance uncertainty.

If the simulated withdraw-to-completion time exceeds the session cutoff, the simulator must represent an explicit no-completed-rerun outcome.

## Forbidden inference

- Recorder capture timestamp is not queue entry.
- Attempt timestamp spacing is not queue waiting time.
- Inter-attempt gap is not queue waiting time.
- Missing lane state must not be reconstructed as fact.
- Unknown staging overhead must not silently be set to zero.

## Next phase

Phase 6B should parameterize explicit queue/wait sensitivity scenarios for Monte Carlo simulation. Those scenarios must remain labeled assumptions rather than historical observations.

## Status

**QUEUE_WAIT_UNCERTAINTY_DESIGN_FROZEN**