from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

OUTDIR = Path(
    "weather/output/v2d_uncertainty_ablation"
)

DETAIL = (
    OUTDIR
    / "v2d_uncertainty_ablation_detail_v1.csv"
)

SUMMARY_CSV = (
    OUTDIR
    / "v2d_uncertainty_ablation_summary_v1.csv"
)

REDUCTION = (
    OUTDIR
    / "v2d_uncertainty_ablation_width_reduction_v1.csv"
)

SUMMARY_TXT = (
    OUTDIR
    / "v2d_uncertainty_ablation_summary_v1.txt"
)

MANIFEST = (
    OUTDIR
    / "v2d_freeze_manifest_v1.json"
)

FREEZE_SUMMARY = (
    OUTDIR
    / "v2d_freeze_summary_v1.txt"
)

required = [
    DETAIL,
    SUMMARY_CSV,
    REDUCTION,
    SUMMARY_TXT,
]

for p in required:
    if not p.exists():
        raise FileNotFoundError(p)


def sha256(path):
    h = hashlib.sha256()

    with open(path, "rb") as f:
        for chunk in iter(
            lambda: f.read(1024 * 1024),
            b"",
        ):
            h.update(chunk)

    return h.hexdigest()


manifest = {
    "module":
        "V2-D Uncertainty-Source Ablation",

    "status":
        "FROZEN",

    "freeze_time_utc":
        datetime.now(
            timezone.utc
        ).isoformat(),

    "purpose": (
        "Assess the sensitivity of final predictive spread "
        "to future-track uncertainty, paired coefficient "
        "uncertainty, and empirical performance-residual "
        "uncertainty."
    ),

    "interpretation_boundary": (
        "This is an uncertainty-source ablation / sensitivity "
        "analysis, not a strict additive variance decomposition."
    ),

    "principal_findings": {
        "dominant_source":
            "empirical performance residual",

        "track_uncertainty_role":
            "secondary but increasingly important with horizon",

        "coefficient_uncertainty_role":
            "secondary but increasingly important with horizon",

        "main_system_implication": (
            "Improving future track-state point prediction alone "
            "cannot substantially collapse final performance "
            "intervals while unresolved attempt-level residual "
            "variation remains dominant."
        ),
    },

    "selected_results": {
        "pi80_reduction_no_residual": {
            "15_min": 0.904239,
            "30_min": 0.855426,
            "60_min": 0.798707,
            "90_min": 0.758780,
            "120_min": 0.727920,
        },

        "pi90_reduction_no_residual": {
            "15_min": 0.913789,
            "30_min": 0.871940,
            "60_min": 0.817248,
            "90_min": 0.783765,
            "120_min": 0.756675,
        },

        "track_only_pi80_width_mph": {
            "15_min": 0.116486,
            "30_min": 0.167695,
            "60_min": 0.241044,
            "90_min": 0.288155,
            "120_min": 0.314869,
        },

        "coefficient_only_pi80_width_mph": {
            "15_min": 0.071618,
            "30_min": 0.100979,
            "60_min": 0.156121,
            "90_min": 0.200324,
            "120_min": 0.228228,
        },
    },

    "artifacts": {},
}

for p in required:
    manifest["artifacts"][
        str(p)
    ] = {
        "sha256": sha256(p),
        "bytes": p.stat().st_size,
    }

MANIFEST.write_text(
    json.dumps(
        manifest,
        indent=2,
    ),
    encoding="utf-8",
)

summary = f"""
====================================================================================================
INDY 500 V2-D UNCERTAINTY-SOURCE ABLATION — FINAL FREEZE
====================================================================================================

STATUS: FROZEN

PURPOSE
----------------------------------------------------------------------------------------------------
Assess how final predictive spread changes when uncertainty sources are
individually enabled or removed.

This is an uncertainty-source ablation / sensitivity analysis.

It is NOT a strict additive variance decomposition.

MAIN RESULT
----------------------------------------------------------------------------------------------------
Empirical attempt-level performance residual variation is the dominant
source of final predictive uncertainty.

Removing the empirical performance residual reduces mean 80% PI width by:

15 min:   90.42%
30 min:   85.54%
60 min:   79.87%
90 min:   75.88%
120 min:  72.79%

Removing the empirical performance residual reduces mean 90% PI width by:

15 min:   91.38%
30 min:   87.19%
60 min:   81.72%
90 min:   78.38%
120 min:  75.67%

HORIZON EFFECT
----------------------------------------------------------------------------------------------------
Future-track uncertainty and coefficient uncertainty both become more
important as horizon increases.

TRACK-ONLY mean 80% PI width:

15 min:   0.1165 mph
30 min:   0.1677 mph
60 min:   0.2410 mph
90 min:   0.2882 mph
120 min:  0.3149 mph

COEFFICIENT-ONLY mean 80% PI width:

15 min:   0.0716 mph
30 min:   0.1010 mph
60 min:   0.1561 mph
90 min:   0.2003 mph
120 min:  0.2282 mph

FINAL INTERPRETATION
----------------------------------------------------------------------------------------------------
The final performance interval is dominated by unresolved attempt-level
variation rather than future track-state forecast error or coefficient
estimation uncertainty.

Track-state and coefficient uncertainty remain real contributors and
grow with prediction horizon.

Therefore, improving future track-temperature point prediction alone
would not substantially collapse final performance intervals while
empirical attempt-level variation remains dominant.

Quantile-width reductions are nonlinear and interacting.

They MUST NOT be interpreted as additive percentages or variance shares.

MANIFEST
----------------------------------------------------------------------------------------------------
{MANIFEST}

SHA256(manifest):
{sha256(MANIFEST)}

====================================================================================================
V2-D STATUS: FROZEN
====================================================================================================
""".strip()

FREEZE_SUMMARY.write_text(
    summary + "\n",
    encoding="utf-8",
)

print(summary)

print()
print("OUTPUTS")
print("-" * 100)
print(MANIFEST)
print(FREEZE_SUMMARY)
print()
print("DONE")
