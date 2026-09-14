# Identifiability Boundary

## Original strategy question

The project began from an operational Indianapolis 500 qualifying decision: whether a team should retain its current official result or withdraw it for priority and another qualifying attempt.

An end-to-end historical strategy model would require reconstructing not only physical performance but also the opportunity process that determines when another run can actually occur.

## Evidence required for an end-to-end model

A defensible historical model of the opportunity horizon `H` would require sufficiently consistent observations of variables such as:

- exact attempt and withdrawal timing;
- Lane 1 / Lane 2 state;
- requeue and pit-return events;
- live queue composition and service progression;
- contemporaneous leaderboard state;
- race-control interruptions and other availability constraints;
- team intent and the reason an attempt was abandoned, withdrawn or repeated.

The historical evidence base did not provide these variables consistently enough across seasons to identify `P(H | Q)` without introducing assumptions that could not be validated from the source record.

## Decision: reject the queue-time target

The absence of a queue-time model is therefore a research result rather than a missing feature.

The project does **not** infer queue duration from the elapsed time between two recorded attempts. Inter-attempt elapsed time can contain waiting, pit activity, preparation, strategic delay, interruptions and other unobserved processes. Treating it as queue service time would create false precision.

Likewise, a plausible live opportunity window may be overlaid on model output for operational context, but that window is external context rather than a probability distribution estimated by the frozen scientific model.

## Reformulated identifiable target

The historically defensible component is the conditional physical-performance process:

`p(Δv | H = h)`

where:

- `Δv` is the change in four-lap qualifying performance relative to the current official result;
- `H` is the future opportunity horizon;
- `h` is treated as a condition supplied to the physical-performance model rather than a queue-time prediction.

The final question is therefore:

> If another on-track opportunity occurs `h` minutes from now, what distribution of four-lap qualifying-performance change should be expected relative to the current official result?

## Consequence for system architecture

The resulting system has a deliberate boundary:

```text
Real pit-wall decision
        |
        v
Historical identifiability analysis
        |
        +---- opportunity / queue process ----> not modelled probabilistically
        |
        +---- physical state evolution -------> modelled
                                                |
                                                v
                                  future track-state distribution
                                                |
                                                v
                                  performance-response distribution
                                                |
                                                v
                                       p(Δv | H = h)
                                                |
                                                v
                         live queue + leaderboard + engineer judgement
```

This boundary prevents the project from presenting an autonomous strategy recommendation that the historical evidence cannot support.

## What remains operationally useful

Conditional physical-performance inference still answers an important component of the strategy problem. Given a plausible future opportunity horizon, the system can provide:

- expected physical speed change;
- predictive intervals;
- probability of improvement;
- expected future four-lap speed;
- sensitivity across the validated 15 / 30 / 60 / 90 / 120 minute anchors.

These outputs can be combined with live information that is observable on race day but was not reliably reconstructable historically.

## Research principle

The central methodological choice is simple:

> **Do not replace missing historical observability with an untestable strategy model. Model the identifiable component well, quantify its uncertainty, and expose the boundary explicitly.**
