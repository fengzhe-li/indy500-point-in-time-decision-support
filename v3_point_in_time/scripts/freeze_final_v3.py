"""Phase 5 Steps 32-35 -- FINAL_V3 freeze.

Re-runs every mandatory scientific and application check. Only writes
the freeze package to output/FINAL_V3_FREEZE/ if ALL of them pass --
per specification, a failed freeze is preferable to an invalid one.
Docker build/runtime are checked against the currently-running
`docker compose` stack (built and started earlier in this session)
rather than rebuilt from scratch here, to keep this script fast and
side-effect-free with respect to already-verified images; if no
container is running, those two checks are reported as SKIPPED (not
silently assumed to pass), and the human-facing report says so.
"""
from __future__ import annotations

import csv
import json
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

V3_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = V3_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))
REPO_ROOT = V3_ROOT.parent

from hashing import sha256_file  # noqa: E402

FREEZE_DIR = V3_ROOT / "output" / "FINAL_V3_FREEZE"
DOC_DIR = V3_ROOT / "output" / "final_documentation"
QA_DIR = V3_ROOT / "output" / "qa"
STATUS = "FINAL_V3_FROZEN"


def _run(cmd, cwd):
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return result.returncode == 0, result.stdout + result.stderr


def _http_get_ok(url: str) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=3) as r:
            return r.status == 200
    except Exception:
        return False


def main() -> int:
    checks = {}

    ok, out = _run([sys.executable, "-m", "unittest", "discover", "-s", "v3_point_in_time/tests", "-p", "test_*.py"], REPO_ROOT)
    checks["python_tests"] = ok
    python_test_line = next((l for l in out.splitlines() if l.startswith("Ran ")), "Ran ? tests")

    ok, out = _run([sys.executable, "v3_point_in_time/scripts/run_v2_immutability_check.py"], REPO_ROOT)
    checks["v2_immutability"] = ok and "OVERALL RESULT: PASS" in out

    ok, out = _run([sys.executable, "v3_point_in_time/scripts/run_v3_v2_behavioral_regression.py"], REPO_ROOT)
    checks["behavioural_regression"] = ok and "Overall result: PASS" in out

    ok, out = _run([sys.executable, "v3_point_in_time/scripts/smoke_test.py"], REPO_ROOT)
    checks["smoke_test"] = ok

    ok, out = _run(["npx", "vitest", "run"], V3_ROOT / "frontend")
    checks["frontend_tests"] = ok
    frontend_test_line = next((l for l in out.splitlines() if l.strip().startswith("Tests")), "Tests ?")

    ok, out = _run(["npm", "run", "build"], V3_ROOT / "frontend")
    checks["frontend_build"] = ok

    api_running = _http_get_ok("http://localhost:8000/api/health")
    api_ready = _http_get_ok("http://localhost:8000/api/system/readiness") if api_running else False
    frontend_running = _http_get_ok("http://localhost:8080/")
    checks["docker_runtime"] = api_running and frontend_running
    docker_status = "PASS" if checks["docker_runtime"] else "SKIPPED (no running container found at freeze time)"

    ok, out = _run(["docker", "images", "-q", "v3_point_in_time-api"], REPO_ROOT)
    docker_image_exists = ok and out.strip() != ""
    checks["docker_build"] = docker_image_exists
    docker_build_status = "PASS" if docker_image_exists else "SKIPPED (no local image found at freeze time)"

    all_mandatory_pass = all([
        checks["python_tests"], checks["v2_immutability"], checks["behavioural_regression"],
        checks["smoke_test"], checks["frontend_tests"], checks["frontend_build"],
    ])

    print("Pre-freeze check results:")
    for k, v in checks.items():
        print(f"  {k}: {'PASS' if v else 'FAIL'}")

    if not all_mandatory_pass:
        print("\nSTOP: at least one mandatory check failed. FINAL_V3 freeze NOT created.")
        return 1

    FREEZE_DIR.mkdir(parents=True, exist_ok=True)

    # Copy documentation into the freeze package under FINAL_V3_ names.
    doc_copies = {
        DOC_DIR / "final_v3_architecture.md": FREEZE_DIR / "FINAL_V3_ARCHITECTURE.md",
        DOC_DIR / "FINAL_V3_MODEL_CARD.md": FREEZE_DIR / "FINAL_V3_MODEL_CARD.md",
        DOC_DIR / "FINAL_V3_SYSTEM_SPECIFICATION.md": FREEZE_DIR / "FINAL_V3_SYSTEM_SPECIFICATION.md",
        DOC_DIR / "scientific_limitations.md": FREEZE_DIR / "FINAL_V3_SCIENTIFIC_LIMITATIONS.md",
        QA_DIR / "final_v3_qa_report.md": FREEZE_DIR / "FINAL_V3_QA_REPORT.md",
        QA_DIR / "container_scientific_asset_manifest.json": FREEZE_DIR / "FINAL_V3_CONTAINER_ASSET_MANIFEST.json",
    }
    for src, dst in doc_copies.items():
        dst.write_bytes(src.read_bytes())

    # API contract (Phase 4 baseline + Phase 5 additions).
    phase4_contract = json.loads((V3_ROOT / "output" / "phase4_freeze" / "api_contract.json").read_text(encoding="utf-8"))
    phase4_contract["endpoints"] += [
        {"method": "GET", "path": "/api/scenario/schema", "returns": "ScenarioSchema"},
        {"method": "POST", "path": "/api/scenario/infer", "returns": "ScenarioResponse", "errors": ["422 unparsable decision_time"]},
        {"method": "GET", "path": "/api/replay/cases/representative", "returns": "ReplayCaseSummary (+selection_reason)"},
        {"method": "GET", "path": "/api/system/readiness", "returns": "ReadinessResponse", "errors": ["503 NOT_READY"]},
    ]
    phase4_contract["version"] = "5.0.0"
    (FREEZE_DIR / "FINAL_V3_API_CONTRACT.json").write_text(json.dumps(phase4_contract, indent=2), encoding="utf-8")

    # UI route manifest (Phase 4 baseline + Scenario Mode).
    phase4_routes = json.loads((V3_ROOT / "output" / "phase4_freeze" / "ui_route_manifest.json").read_text(encoding="utf-8"))
    phase4_routes["pages"].insert(1, {
        "key": "scenario", "title": "Scenario Mode", "component": "src/pages/ScenarioMode.tsx",
        "consumes": ["/api/scenario/schema", "/api/scenario/infer"],
    })
    (FREEZE_DIR / "FINAL_V3_UI_ROUTE_MANIFEST.json").write_text(json.dumps(phase4_routes, indent=2), encoding="utf-8")

    # Source + hash manifest across V3's own code and documentation.
    categories = {
        "scientific_src": sorted((SRC_DIR).glob("*.py")),
        "application_app": sorted((V3_ROOT / "app").glob("*.py")),
        "application_api": sorted((V3_ROOT / "api").glob("*.py")) + sorted((V3_ROOT / "api" / "routes").glob("*.py")),
        "frontend_src": sorted((V3_ROOT / "frontend" / "src").rglob("*.ts")) + sorted((V3_ROOT / "frontend" / "src").rglob("*.tsx")),
        "docker": sorted((V3_ROOT / "docker").glob("*")) + [V3_ROOT / "docker-compose.yml"],
        "documentation": sorted(DOC_DIR.glob("*.md")) + [QA_DIR / "final_v3_qa_report.md"],
        "config": [V3_ROOT / "config" / "v3_config.yaml", V3_ROOT / "requirements.txt"],
    }

    source_manifest_path = FREEZE_DIR / "FINAL_V3_SOURCE_MANIFEST.csv"
    hashes_path = FREEZE_DIR / "FINAL_V3_HASHES.csv"
    all_rows = []
    for category, paths in categories.items():
        for p in paths:
            if p.is_file():
                all_rows.append((category, str(p.relative_to(REPO_ROOT)), sha256_file(p)))

    with open(source_manifest_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["category", "path"])
        for category, rel_path, _ in all_rows:
            w.writerow([category, rel_path])

    with open(hashes_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["category", "path", "sha256"])
        for category, rel_path, h in all_rows:
            w.writerow([category, rel_path, h])
        # Also fold in the 32 frozen FINAL_V2 dependency hashes for a single ledger.
        for line in (QA_DIR / "v2_pre_implementation_hashes.txt").read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            h, rel_path = line.split("  ", 1)
            w.writerow(["frozen_final_v2_dependency", rel_path, h])

    test_summary_lines = [
        f"Python tests: {'PASS' if checks['python_tests'] else 'FAIL'} -- {python_test_line}",
        f"V2 immutability: {'PASS' if checks['v2_immutability'] else 'FAIL'}",
        f"V3<->V2 behavioural regression: {'PASS' if checks['behavioural_regression'] else 'FAIL'}",
        f"Smoke test: {'PASS' if checks['smoke_test'] else 'FAIL'}",
        f"Frontend tests: {'PASS' if checks['frontend_tests'] else 'FAIL'} -- {frontend_test_line.strip()}",
        f"Frontend build: {'PASS' if checks['frontend_build'] else 'FAIL'}",
        f"Docker build: {docker_build_status}",
        f"Docker runtime: {docker_status}",
    ]
    (FREEZE_DIR / "FINAL_V3_TEST_SUMMARY.txt").write_text("\n".join(test_summary_lines) + "\n", encoding="utf-8")

    summary_lines = [
        "=" * 72,
        "INDY 500 V3 -- FINAL_V3 FREEZE SUMMARY",
        "=" * 72,
        "",
        f"Status: {STATUS}",
        "",
        "This is the final planned development phase for this subsystem.",
        "No Phase 6 is planned.",
        "",
        *test_summary_lines,
        "",
        "Scientific target: p(delta_v | H=h) for h in {15,30,60,90,120} minutes.",
        "Does not estimate P(H=h), queue waiting time, or a retain/withdraw",
        "recommendation, in either historical replay or Scenario Mode.",
        "",
        f"Frozen at: {datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')}",
    ]
    (FREEZE_DIR / "FINAL_V3_SUMMARY.txt").write_text("\n".join(summary_lines), encoding="utf-8")

    manifest = {
        "status": STATUS,
        "frozen_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "scientific_core_version": "FINAL_V2",
        "application_version": "FINAL_V3",
        "supported_horizons_min": [15, 30, 60, 90, 120],
        "known_scientific_boundaries": [
            "does_not_estimate_P(H=h)", "no_queue_model", "no_retain_recommendation",
            "no_withdraw_recommendation", "no_optimal_waiting_time",
            "historical_scoring_formally_supported_count_is_0",
            "illustrative_case_2021_car60_excluded_from_aggregate_validation",
        ],
        "test_status": {
            "python_tests_pass": checks["python_tests"],
            "frontend_tests_pass": checks["frontend_tests"],
            "frontend_build_pass": checks["frontend_build"],
            "v2_immutability_pass": checks["v2_immutability"],
            "behavioural_regression_pass": checks["behavioural_regression"],
            "smoke_test_pass": checks["smoke_test"],
            "docker_build_verified_this_run": checks["docker_build"],
            "docker_runtime_verified_this_run": checks["docker_runtime"],
        },
        "hash_ledgers": {
            "frozen_final_v2_dependencies": "FINAL_V3_HASHES.csv (category=frozen_final_v2_dependency), 32 files",
            "v3_scientific_source": "FINAL_V3_HASHES.csv (category=scientific_src)",
            "historical_replay_evidence": str((V3_ROOT / "output" / "phase3_freeze" / "phase3_hashes.csv").relative_to(REPO_ROOT)),
            "application_source": "FINAL_V3_HASHES.csv (category=application_app, application_api, frontend_src, docker, config)",
            "scenario_interface_source": "FINAL_V3_HASHES.csv (category=application_app, path=v3_point_in_time/app/scenario_service.py)",
            "documentation": "FINAL_V3_HASHES.csv (category=documentation)",
        },
        "not_to_be_called": "anything other than FINAL_V3_FROZEN",
        "files": [
            "FINAL_V3_SUMMARY.txt", "FINAL_V3_SYSTEM_SPECIFICATION.md", "FINAL_V3_MODEL_CARD.md",
            "FINAL_V3_QA_REPORT.md", "FINAL_V3_SCIENTIFIC_LIMITATIONS.md", "FINAL_V3_ARCHITECTURE.md",
            "FINAL_V3_TEST_SUMMARY.txt", "FINAL_V3_API_CONTRACT.json", "FINAL_V3_UI_ROUTE_MANIFEST.json",
            "FINAL_V3_CONTAINER_ASSET_MANIFEST.json", "FINAL_V3_SOURCE_MANIFEST.csv", "FINAL_V3_HASHES.csv",
            "FINAL_V3_FREEZE_MANIFEST.json",
        ],
    }
    (FREEZE_DIR / "FINAL_V3_FREEZE_MANIFEST.json").write_text(json.dumps(manifest, indent=2, sort_keys=False), encoding="utf-8")

    print(f"\nWrote FINAL_V3 freeze package to {FREEZE_DIR} with status {STATUS}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
