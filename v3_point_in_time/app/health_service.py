"""Phase 5 Step 20 — health / readiness.

Distinguishes three things a plain "is the process alive" health check
would conflate:

  1. the API process itself is running (trivially true if this code runs)
  2. historical replay evidence is present and non-empty
  3. FINAL_V2's frozen scientific dependencies are byte-identical to the
     baseline captured before any V3 implementation work began -- the
     same baseline file scripts/run_v2_immutability_check.py uses,
     reused here rather than re-declared, so there is exactly one
     definition of "the 32 frozen dependencies" in the whole project.

`/api/health` stays a trivial liveness probe (Phase 4 behaviour,
unchanged). `/api/system/readiness` is the new Phase 5 endpoint that
can legitimately report NOT_READY.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict

V3_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = V3_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import final_v2_adapter  # noqa: E402
from hashing import sha256_file  # noqa: E402

REPO_ROOT = V3_ROOT.parent
BASELINE_HASHES_FILE = V3_ROOT / "output" / "qa" / "v2_pre_implementation_hashes.txt"
REPLAY_EVENTS_FILE = V3_ROOT / "output" / "replay" / "replay_events.jsonl"

SCENARIO_REQUIRED_FILES = [
    final_v2_adapter.TRACK_COEF_FILE,
    final_v2_adapter.TRACK_RESID_FILE,
    final_v2_adapter.PERF_BOOT_FILE,
    final_v2_adapter.PERF_RESID_FILE,
    final_v2_adapter.MC_SCRIPT,
    final_v2_adapter.SOLAR_SCRIPT,
]


def _load_baseline() -> Dict[str, str]:
    baseline = {}
    for line in BASELINE_HASHES_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        h, rel_path = line.split("  ", 1)
        baseline[rel_path] = h
    return baseline


def check_v2_integrity() -> dict:
    if not BASELINE_HASHES_FILE.exists():
        return {"status": "FAIL", "reason": "baseline hash file missing", "checked": 0, "mismatched": []}
    baseline = _load_baseline()
    mismatched = []
    for rel_path, expected_hash in baseline.items():
        full_path = REPO_ROOT / rel_path
        if not full_path.exists():
            mismatched.append({"path": rel_path, "reason": "MISSING"})
            continue
        actual_hash = sha256_file(full_path)
        if actual_hash != expected_hash:
            mismatched.append({"path": rel_path, "reason": "HASH_MISMATCH"})
    return {
        "status": "PASS" if not mismatched else "FAIL",
        "checked": len(baseline),
        "mismatched": mismatched,
    }


def check_scenario_assets() -> dict:
    missing = [str(p.relative_to(REPO_ROOT)) for p in SCENARIO_REQUIRED_FILES if not p.exists()]
    return {"status": "PASS" if not missing else "FAIL", "checked": len(SCENARIO_REQUIRED_FILES), "missing": missing}


def check_historical_evidence() -> dict:
    if not REPLAY_EVENTS_FILE.exists():
        return {"status": "FAIL", "reason": "replay_events.jsonl missing"}
    if REPLAY_EVENTS_FILE.stat().st_size == 0:
        return {"status": "FAIL", "reason": "replay_events.jsonl is empty"}
    return {"status": "PASS"}


def readiness() -> dict:
    v2 = check_v2_integrity()
    scenario_assets = check_scenario_assets()
    historical = check_historical_evidence()
    overall = "READY" if all(c["status"] == "PASS" for c in (v2, scenario_assets, historical)) else "NOT_READY"
    return {
        "status": overall,
        "checks": {
            "final_v2_integrity": v2,
            "scenario_scientific_assets": scenario_assets,
            "historical_replay_evidence": historical,
        },
    }
