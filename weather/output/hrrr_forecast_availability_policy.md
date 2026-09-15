# HRRR Forecast Availability Policy

Policy ID: `HRRR_CONSERVATIVE_FIXED_LAG_V1`

## Primary rule

`policy_availability_time_utc = issue_time_utc + 90 minutes`

This is a conservative modeling policy, not an observed historical NOAA publication timestamp.

A forecast snapshot is eligible for a decision only when its policy availability time is less than or equal to the decision-state timestamp.

## Leakage policy

- `issue_time_utc` alone must not be used as forecast availability.
- Canonical `availability_time_utc` remains unchanged and unresolved.
- The policy layer is derived and separate from canonical weather provenance.
- Primary analysis uses a 90-minute conservative lag.
- Sensitivity analysis should repeat forecast joins with 60-minute and 120-minute lags.

## Policy hash

`7fa0a02223a77db591539cf42bdd4e9461df15bf4a9de77dfd5360c3deac89c6`

## Readiness

**READY_FOR_LEAKAGE_SAFE_FORECAST_SELECTION**