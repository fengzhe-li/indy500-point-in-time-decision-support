# Identifiability boundary

## Original target

The original question was whether an entrant should preserve its current Indianapolis 500 qualifying result or withdraw it to gain priority for another attempt. A complete statistical solution would require both an opportunity model and a performance model, followed by a utility function.

## What the historical audit found

Official results recover completed attempts well, but the public record does not consistently expose the decision-time operational state across seasons. Lane 1/Lane 2 entry, cars ahead, withdrawals, requeue events, pit return, team intent and the exact opportunity set are partial or absent. Treating elapsed time between observed attempts as queue waiting time would conflate queueing, preparation, discretionary delay, interruptions and unrecorded actions.

The rejected target was therefore:

```text
P(H = h | queue state Q)
```

No synthetic queue labels or assumed lane distributions were introduced to close this gap.

## Identifiable target

The defensible target is conditional:

```text
p(Δv | H = h, current physical state, future environmental scenario)
```

Here, `h` is an externally supplied opportunity horizon. The model estimates how the physical performance distribution may differ from the current official result if another run occurs at that horizon.

## Decision boundary

The output becomes one input to a human pit-wall decision. Live queue position, leaderboard state, session remaining, competitor state, interruption risk and the consequences of withdrawing a result remain external. The project makes no retain/withdraw recommendation and does not claim an optimal wait.

This scope reduction is a research result: the architecture follows the observable evidence instead of manufacturing a complete strategy target.

