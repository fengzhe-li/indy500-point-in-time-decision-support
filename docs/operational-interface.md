# Operational interface

## Inputs

An operational outlook requires current track and ambient temperature, a credible future ambient trajectory, solar geometry/state and an opportunity horizon. The supported scientific horizons are 15, 30, 60, 90 and 120 minutes.

## Outputs

- expected and median four-lap speed change;
- 80% and 90% predictive intervals;
- probability of improving the current result;
- future track-temperature outlook.

## Continuous presentation

`OPERATIONAL_CURVE_V2` preserves the scientific anchors and interpolates summary values at one-minute resolution between them. Intermediate rows are explicitly `INTERPOLATED_OPERATIONAL`; no additional stochastic model or historical calibration is fitted there. Values above 120 minutes are not generated for production.

## External live context

The pit wall must supply queue position, cars ahead, live leaderboard and cutoff, session time remaining, interruptions, competitor intent and the consequence of withdrawing the current result. A queue-derived opportunity window may be overlaid on the performance curve, but the model does not estimate that window.

## Human decision

The interface supports a judgement; it does not output retain, withdraw, Lane 1, Lane 2 or best-wait actions. P(improvement) is conditional physical evidence and must not be substituted for expected strategy utility.

