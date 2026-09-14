# Canonical data layer

The research workspace materializes a larger canonical evidence model than the compact modelling table alone suggests. Its principal entities include:

- `qualifying_events`
- `attempts`
- `attempt_laps`
- `attempt_sections`
- `chronology_events`
- `chronology_constraints`
- `sources`
- `evidence_items`
- `field_evidence_links`
- `row_eligibility`
- `forecast_snapshots`
- `weather_forecasts`
- `decision_state_features`

The public repository intentionally exposes representative canonical tables and source metadata rather than blindly copying the entire 60+ MB field-level lineage export. The full research workspace retains field-level provenance links and deterministic hashes for auditability.

## Why a canonical layer exists

Historical Indy 500 qualifying evidence is heterogeneous: official results, section reports, editorial anchors, replay captures and reconstructed environmental records do not share one reliable attempt-level schema. The canonical layer separates source ingestion from modelling and preserves uncertainty instead of silently converting incomplete chronology into exact timestamps.

For example, chronology constraints can be `EXACT_OBSERVED`, `APPROXIMATE_OBSERVED`, `BOUNDED_INTERVAL`, `ORDERING_ONLY` or `UNKNOWN`. An unresolved timestamp remains unresolved; it is not converted into an estimated queue wait.

## Public-source registry

`sources.csv` is a sanitized copy of the research source registry. Local workstation paths have been replaced with repository-relative evidence identifiers. Hashes and evidence-quality classes are retained because they are part of the reproducibility design.

## Production eligibility

Eligibility is target-specific. A record can be useful for four-lap performance analysis while being unusable for chronology or queue calibration. This is why the pipeline assigns eligibility separately for performance, within-car comparison, chronology, section analysis and queue-related targets rather than applying one global `dropna()` filter.
