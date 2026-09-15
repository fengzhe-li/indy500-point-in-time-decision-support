# Final Integrated Decision Output V1

Policy version: `FINAL_INTEGRATED_DECISION_OUTPUT_V1`
Policy hash: `e0fcb330ff1d3953549fa63adb805a1a03b452ceb606affc228de0ba82288394`

## Purpose

Provide a final consumer-facing decision profile that integrates target success, completion risk, repeat-performance uncertainty, and robustness sensitivity.

## Inputs

- current retained speed;
- required gain / target speed;
- baseline condition;
- time remaining;
- latent pre-run-delay sensitivity scenario.

## Outputs

- completion probability;
- no-completion probability;
- central target-success probability;
- robustness lower / upper sensitivity envelope;
- probability of any completed-run improvement;
- probability of completed-run loss;
- expected repeat-attempt delta;
- q05 / median / q95 repeat-attempt delta;
- cutoff state;
- dominant sensitivity source.

## Evidence boundaries

Historical individual queue wait is not observed.
Historical exact queue position is not observed.
Repeat performance uncertainty is based on `35` normal and `4` recovery-like empirical rows.
Recovery-like labels are diagnostic rather than causal.
Robustness bounds are descriptive sensitivity envelopes, not confidence intervals.
The baseline-condition grouping is retrospective and requires a pre-decision observable mapping before live deployment.
No historical leaderboard target is assumed.

## Recommendation boundary

No retain/withdraw action recommendation is issued in V1.
Recommendation requires an explicit target objective and/or an explicitly frozen risk-preference policy.

## Status

**FINAL_INTEGRATED_DECISION_OUTPUT_READY**