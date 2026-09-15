"""Phase 4 Step 30 — freeze package.

Status: V3_PHASE4_APPLICATION_FROZEN (still NOT "FINAL_V3").

Freezes the application layer: the FastAPI contract, the frontend route
manifest, and a snapshot test/verification summary. Does not re-run the
test suite itself (run it separately and pass the counts in) so this
script stays fast and side-effect-free with respect to the scientific
backend.
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC_DIR))
REPO_ROOT = Path(__file__).resolve().parents[2]

from hashing import sha256_file  # noqa: E402

V3_ROOT = Path(__file__).resolve().parents[1]
FREEZE_DIR = V3_ROOT / "output" / "phase4_freeze"

STATUS = "V3_PHASE4_APPLICATION_FROZEN"


def _run(cmd, cwd):
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return result.returncode == 0, result.stdout + result.stderr


def main() -> int:
    FREEZE_DIR.mkdir(parents=True, exist_ok=True)

    py_ok, py_out = _run(
        [sys.executable, "-m", "unittest", "discover", "-s", "v3_point_in_time/tests", "-p", "test_*.py"],
        cwd=REPO_ROOT,
    )
    py_count_line = next((l for l in py_out.splitlines() if l.startswith("Ran ")), "Ran ? tests")

    v2_ok, v2_out = _run([sys.executable, "v3_point_in_time/scripts/run_v2_immutability_check.py"], cwd=REPO_ROOT)
    v2_pass = "OVERALL RESULT: PASS" in v2_out

    reg_ok, reg_out = _run([sys.executable, "v3_point_in_time/scripts/run_v3_v2_behavioral_regression.py"], cwd=REPO_ROOT)
    reg_pass = "Overall result: PASS" in reg_out

    frontend_test_ok, frontend_out = _run(["npx", "vitest", "run"], cwd=V3_ROOT / "frontend")
    frontend_summary_line = next((l for l in frontend_out.splitlines() if l.strip().startswith("Tests")), "Tests  ? ")

    test_summary_lines = [
        "Phase 4 test summary",
        "=" * 40,
        f"Python suite (unittest discover): {'PASS' if py_ok else 'FAIL'} -- {py_count_line}",
        f"V2 immutability check: {'PASS' if v2_pass else 'FAIL'}",
        f"V3<->V2 behavioural regression: {'PASS' if reg_pass else 'FAIL'}",
        f"Frontend suite (vitest): {'PASS' if frontend_test_ok else 'FAIL'} -- {frontend_summary_line.strip()}",
    ]
    (FREEZE_DIR / "phase4_test_summary.txt").write_text("\n".join(test_summary_lines) + "\n", encoding="utf-8")

    hash_targets = [
        V3_ROOT / "api" / "main.py",
        V3_ROOT / "api" / "models.py",
        V3_ROOT / "app" / "replay_service.py",
        V3_ROOT / "app" / "provenance_service.py",
        V3_ROOT / "app" / "query_service.py",
        V3_ROOT / "output" / "phase4_freeze" / "api_contract.json",
        V3_ROOT / "output" / "phase4_freeze" / "ui_route_manifest.json",
    ]
    hashes_path = FREEZE_DIR / "phase4_hashes.csv"
    with open(hashes_path, "w", encoding="utf-8") as f:
        f.write("path,sha256\n")
        for p in hash_targets:
            if p.is_file():
                f.write(f"{p.relative_to(REPO_ROOT)},{sha256_file(p)}\n")

    summary_lines = [
        "=" * 72,
        "INDY 500 V3 PHASE 4 -- FREEZE SUMMARY",
        "=" * 72,
        "",
        f"Status: {STATUS}",
        "This is explicitly NOT FINAL_V3.",
        "",
        "Phase 4 is a product/interface layer only: a FastAPI application (app/, api/)",
        "that reads Phase 1-3's already-frozen output read-only, and a React+TypeScript",
        "frontend (frontend/) that renders exactly what the API returns. No scientific",
        "computation was added, changed, or duplicated in the frontend.",
        "",
        *test_summary_lines,
        "",
        f"Frozen at: {datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')}",
    ]
    (FREEZE_DIR / "phase4_summary.txt").write_text("\n".join(summary_lines), encoding="utf-8")

    manifest = {
        "phase": 4,
        "status": STATUS,
        "not_to_be_called": "FINAL_V3",
        "backend": "FastAPI (app/, api/) -- read-only over Phase 1-3 frozen output",
        "frontend": "React + TypeScript + Vite (frontend/)",
        "python_tests_pass": py_ok,
        "v2_immutability_pass": v2_pass,
        "behavioural_regression_pass": reg_pass,
        "frontend_tests_pass": frontend_test_ok,
        "files": ["phase4_summary.txt", "api_contract.json", "ui_route_manifest.json",
                  "phase4_test_summary.txt", "phase4_hashes.csv"],
        "frozen_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    (FREEZE_DIR / "phase4_freeze_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
    )

    print(f"Froze Phase 4 package to {FREEZE_DIR} with status {STATUS}")
    print(json.dumps({k: manifest[k] for k in ("python_tests_pass", "v2_immutability_pass", "behavioural_regression_pass", "frontend_tests_pass")}, indent=2))
    return 0 if (py_ok and v2_pass and reg_pass and frontend_test_ok) else 1


if __name__ == "__main__":
    raise SystemExit(main())
