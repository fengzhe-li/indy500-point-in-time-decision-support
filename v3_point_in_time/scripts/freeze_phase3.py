"""Phase 3 Step 21 — freeze package.

Status: V3_PHASE3_SHADOW_REPLAY_FROZEN (still NOT "FINAL_V3").

Freezes the historical shadow-replay engineering layer: real-evidence
replay over all 41 same-car transitions (10 defensible candidates + 31
excluded pre-candidates), with abstention as a first-class, auditable
output. This is an engineering/architecture freeze, not a new
statistical validation claim -- Phase 2's evidence/identifiability
boundary (output/qa/phase2_interpretation_addendum.md) is unchanged.
"""
from __future__ import annotations

import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC_DIR))
REPO_ROOT = Path(__file__).resolve().parents[2]

from hashing import sha256_file  # noqa: E402

V3_ROOT = Path(__file__).resolve().parents[1]
REPLAY_DIR = V3_ROOT / "output" / "replay"
FREEZE_DIR = V3_ROOT / "output" / "phase3_freeze"

STATUS = "V3_PHASE3_SHADOW_REPLAY_FROZEN"


def main() -> int:
    FREEZE_DIR.mkdir(parents=True, exist_ok=True)

    case_summary_src = REPLAY_DIR / "replay_case_summary.csv"
    with open(case_summary_src, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    counts = {}
    for r in rows:
        counts[r["category"]] = counts.get(r["category"], 0) + 1

    for name in ("replay_case_summary.csv", "replay_abstention_summary.csv"):
        (FREEZE_DIR / name).write_bytes((REPLAY_DIR / name).read_bytes())

    sources = [
        ("v3_point_in_time/output/evaluation/phase2_case_table.csv", "10 defensible real 2021 candidates (Phase 2 frozen evidence, reused unmodified)"),
        ("v3_point_in_time/output/evaluation/phase2_excluded_transitions.csv", "31 excluded pre-candidates (Phase 2 frozen evidence, reused unmodified)"),
        ("weather/output/hrrr_ims_2020_2024_features.csv", "real NOAA HRRR forecast vintages (same source as Phase 2)"),
        ("weather/output/v2_future_track/v2a_full_sample_track_model_coefficients_v1.csv", "frozen M2b coefficients (read-only)"),
        ("weather/output/v2_future_track/future_track_residuals_v1.csv", "frozen track-residual pool (read-only)"),
        ("r5_2/manual/probabilistic_physics_coefficient_bootstrap_v1.csv", "frozen performance bootstrap draws (read-only)"),
        ("r5_2/manual/probabilistic_physics_loyo_residuals_v1.csv", "frozen performance-residual pool (read-only)"),
        ("weather/output/v2d_uncertainty_ablation/v2d_uncertainty_ablation_width_reduction_v1.csv", "frozen V2-D uncertainty-source reference (display-only, read-only)"),
    ]
    manifest_path = FREEZE_DIR / "phase3_source_manifest.csv"
    with open(manifest_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["source", "role"])
        for s, role in sources:
            w.writerow([s, role])

    hash_targets = [REPO_ROOT / s for s, _ in sources if (REPO_ROOT / s).is_file()]
    hash_targets += [REPLAY_DIR / n for n in ("replay_events.jsonl", "replay_events.csv",
                                                "replay_case_summary.csv", "replay_abstention_summary.csv")]
    hashes_path = FREEZE_DIR / "phase3_hashes.csv"
    with open(hashes_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["path", "sha256"])
        for p in hash_targets:
            label = str(p.relative_to(REPO_ROOT)) if REPO_ROOT in p.parents else str(p)
            w.writerow([label, sha256_file(p)])

    summary_lines = [
        "=" * 72,
        "INDY 500 V3 PHASE 3 -- FREEZE SUMMARY",
        "=" * 72,
        "",
        f"Status: {STATUS}",
        "This is explicitly NOT FINAL_V3 and NOT a new statistical validation claim.",
        "",
        "Phase 3 turns the Phase 1/2 point-in-time execution path into an",
        "auditable historical shadow-replay system over all 41 real same-car",
        "transitions found in the project's evidence base (same 41 Phase 2",
        "already inventoried; no new data acquired).",
        "",
        "Case-level category counts:",
    ]
    for cat, n in sorted(counts.items()):
        summary_lines.append(f"  {cat}: {n}")
    summary_lines += [
        "",
        "The single illustrative case (2021, car 60) remains approved ONLY as",
        "ILLUSTRATIVE_POINT_IN_TIME_SHADOW_CASE, per",
        "output/qa/phase2_interpretation_addendum.md, and contributes 0 to",
        "aggregate validation metrics.",
        "",
        "9 of the 10 real candidates now have a genuine, non-fabricated",
        "conditional physical outlook issued at all five calibrated anchors",
        "(15/30/60/90/120 min) -- inference support -- while historical",
        "scoring against their realised (>120 min) future attempt remains",
        "correctly abstained -- historical evaluation support. These are",
        "reported as functionally distinct, per Phase 3 Step 6.",
        "",
        f"Frozen at: {datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')}",
    ]
    (FREEZE_DIR / "phase3_summary.txt").write_text("\n".join(summary_lines), encoding="utf-8")

    manifest = {
        "phase": 3,
        "status": STATUS,
        "not_to_be_called": "FINAL_V3",
        "case_category_counts": counts,
        "total_transitions_considered": len(rows),
        "no_new_data_acquired": True,
        "illustrative_case_excluded_from_aggregate_validation": True,
        "files": ["phase3_summary.txt", "replay_case_summary.csv", "replay_abstention_summary.csv",
                  "phase3_source_manifest.csv", "phase3_hashes.csv"],
        "frozen_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    (FREEZE_DIR / "phase3_freeze_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
    )

    print(f"Froze Phase 3 package to {FREEZE_DIR} with status {STATUS}")
    print(f"counts={counts}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
