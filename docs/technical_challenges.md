# Technical challenges and engineering decisions

## Reconstructing a missing state

Qualifying PDFs establish results but not the complete pit-lane state. Timing replays are uneven across years. Weather sources use different clocks, units and meanings. The pipeline therefore separates source parsing from canonical reconciliation and carries field-level provenance into eligibility decisions.

## Avoiding future leakage

Decision-state data may only use information available at that historical instant. Future leaderboard state, future weather observations, later actions and later outcomes are prohibited from predictive features. Realized future weather is used only in explicitly retrospective validation.

## Protecting the statistical unit

The four-lap attempt is the competition result and the transition is the response unit. Section timing can diagnose a mechanism, but multiplying 39 transitions by nine sections would manufacture a sample size of 351 from dependent measurements.

## Rejecting attractive but unsupported features

Solar state improved the future track-temperature pathway and was retained there. Direct solar and wind performance terms were not retained. More variables were not treated as automatically better; out-of-year stability and physical interpretation controlled selection.

## Separating model from interface

The scientific model has five calibrated horizons. The operational curve is a labelled interpolation of frozen summaries. This makes the interface usable without claiming minute-level scientific calibration.

## Freezing before external evaluation

The 2020–2024 core was frozen before 2025 evaluation. Hybrid-era observations remain external, and a separate R6 analysis addresses regime compatibility. This prevents favourable external cases from silently becoming training data.

