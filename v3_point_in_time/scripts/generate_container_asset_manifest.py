"""Phase 5 Step 18 -- container scientific asset manifest.

Documents exactly which frozen scientific assets Scenario Mode invokes
at request time (6 files, imported by src/final_v2_adapter.py, not
re-declared here), plus the fuller 32-file baseline the
`/api/system/readiness` check verifies. Both sets are already staged
into the Docker build context by scripts/prepare_docker_context.sh;
this manifest is the audit trail for exactly what is in there and why.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

V3_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(V3_ROOT / "src"))
REPO_ROOT = V3_ROOT.parent

from hashing import sha256_file  # noqa: E402
import final_v2_adapter  # noqa: E402

BASELINE_FILE = V3_ROOT / "output" / "qa" / "v2_pre_implementation_hashes.txt"
OUT_FILE = V3_ROOT / "output" / "qa" / "container_scientific_asset_manifest.json"

SCENARIO_ASSET_PURPOSE = {
    final_v2_adapter.TRACK_COEF_FILE: "frozen M2b_mean_solar track-temperature model coefficients",
    final_v2_adapter.TRACK_RESID_FILE: "frozen track-temperature residual pool (symmetrized bootstrap draws)",
    final_v2_adapter.PERF_BOOT_FILE: "frozen performance-response coefficient bootstrap draws",
    final_v2_adapter.PERF_RESID_FILE: "frozen performance-response (LOYO) residual pool",
    final_v2_adapter.MC_SCRIPT: "source of the frozen pure MC-combination functions (imported, not modified)",
    final_v2_adapter.SOLAR_SCRIPT: "source of the frozen solar-elevation function (imported, not modified)",
}


def _load_baseline():
    entries = []
    for line in BASELINE_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        h, rel_path = line.split("  ", 1)
        entries.append((rel_path, h))
    return entries


def main() -> int:
    scenario_assets = []
    for path, purpose in SCENARIO_ASSET_PURPOSE.items():
        rel = str(path.relative_to(REPO_ROOT))
        scenario_assets.append({
            "path": rel,
            "purpose": purpose,
            "sha256": sha256_file(path),
            "read_only_expected": True,
            "required_by": "app/scenario_service.py (via src/final_v2_adapter.py)",
        })

    readiness_assets = [
        {"path": rel_path, "sha256": h, "read_only_expected": True, "required_by": "app/health_service.py readiness check"}
        for rel_path, h in _load_baseline()
    ]

    manifest = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "scenario_mode_required_assets": scenario_assets,
        "scenario_mode_required_asset_count": len(scenario_assets),
        "readiness_check_baseline_assets": readiness_assets,
        "readiness_check_baseline_asset_count": len(readiness_assets),
        "note": (
            "scenario_mode_required_assets is the minimum set FINAL_V2 inference actually reads "
            "at request time. readiness_check_baseline_assets is the fuller 32-file immutability "
            "baseline app/health_service.py verifies (a superset, including freeze manifests and "
            "documentation not read at inference time). Both sets are staged into the Docker build "
            "context by scripts/prepare_docker_context.sh and made read-only at runtime via "
            "docker-compose.yml's read_only root filesystem."
        ),
    }
    OUT_FILE.write_text(json.dumps(manifest, indent=2, sort_keys=False), encoding="utf-8")
    print(f"Wrote {OUT_FILE}")
    print(f"scenario_mode_required_assets: {len(scenario_assets)}")
    print(f"readiness_check_baseline_assets: {len(readiness_assets)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
