# Reproducibility and repository guide

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
make figures
make portfolio-check
make test
```

`make figures` creates only the curated GitHub visual layer from frozen CSV/JSON/PNG artefacts. It does not refit FINAL_V2.

## Repository layers

| Path | Role |
|---|---|
| `pipeline/` | Source-specific ingestion, reconciliation, provenance, validation and materialization |
| `data/canonical/v1/` | Canonical attempts, laps, weather and QA products |
| `weather/output/final_integration/` | FINAL_V2 specification, freeze summary and manifest |
| `weather/output/v2_*` | Future state, diagnostics, ablation and stress test |
| `weather/output/operational_curve_v2/` | Frozen presentation layer |
| `r5_2/manual/` | Frozen physical-response artefacts and builders |
| `r6_regime_extension/` | Cross-regime reconstruction and 2025 evaluation |
| `figures/portfolio/` | Semantic GitHub-facing visuals |
| `docs/paper/` | Full final research report |

## Freeze controls

FINAL_V2 and each post-freeze diagnostic include manifests or summaries with hashes. `scripts/validate_portfolio.py` verifies key source hashes against the frozen manifest and checks that public claims match authoritative outputs.

The operational curve is separately frozen and has 120/120 anchor-identity checks. Later regime evidence does not modify the 2020–2024 model.

## Raw-data limits

The repository includes physical source files that were available during reconstruction, along with derived canonical and provenance products. Historical replay services and public endpoints can change or disappear. This repository therefore supports exact analytical-state verification more strongly than indefinite reacquisition of every external source.

Where redistribution or durability is uncertain, derived evidence, extraction logs, source catalogues and hashes document what was used. Reviewers should not interpret unavailable future downloads as absent provenance.

## Reproducing scientific modules

The full research report identifies the builder scripts and frozen outputs for each scientific module. Some early-phase scripts are retained as research history; the freeze manifests and final system specification determine the authoritative result. Do not run every historical script as one monolithic pipeline or overwrite frozen outputs.

