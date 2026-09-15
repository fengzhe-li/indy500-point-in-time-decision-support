# Indy 500 Conditional Performance System — Applicability Gate

The frozen model should only be used when all relevant gates below are satisfied.

| Gate | Requirement | If not satisfied |
|---|---|---|
| Technical regime | Vehicle / aerodynamic / power-unit regime must be sufficiently comparable to the validated regime, or explicitly treated as external transfer | Treat output as external / transfer evidence rather than directly validated prediction |
| Qualifying-format regime | A meaningful repeat-attempt opportunity structure must exist | The retain / withdraw decision context is not operationally applicable |
| Horizon | Future opportunity horizon must be one of 15, 30, 60, 90, or 120 minutes | Do not interpolate automatically; unsupported horizon |
| Current physical state | Current track temperature, ambient temperature, thermal gap and required solar state must be available and credible | Do not produce operational outlook |
| Future ambient scenario | A plausible future ambient-temperature trajectory must be supplied | Output cannot be interpreted as a future physical-state outlook |
| Input support | Scenario should remain reasonably close to empirical thermal / environmental support | Flag as extrapolative |
| Queue / opportunity state | Queue state is external and is not predicted historically | Do not interpret model as predicting when another run will occur |
| Competitive state | Rank, bubble, session remaining and competitor state must be supplied externally for strategy use | Do not infer retain / withdraw utility |
| Unmodelled risks | Interruption, waved-off attempt, no-run risk and operational failures remain external | Do not interpret P(improvement) as overall strategy success probability |

## Supported model question

> If another on-track opportunity occurs h minutes from now, what distribution of four-lap qualifying-performance change should be expected relative to the current official result?

## Explicitly unsupported questions

- When exactly will another opportunity occur?
- How long will Lane 1 or Lane 2 take?
- Will the driver definitely improve?
- Should the current result automatically be withdrawn?
- Which latent mechanism uniquely caused an unexplained residual?
