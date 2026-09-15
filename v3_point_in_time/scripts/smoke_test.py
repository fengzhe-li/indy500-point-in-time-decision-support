"""Phase 5 Step 22 — end-to-end application smoke test.

Runs entirely in-process against the real FastAPI app object (no
subprocess/server needed), reading the real, on-disk frozen Phase 1-4
evidence. This is deliberately simple: assertions, not a test
framework, so it can also be run as a plain script for a human demo.
"""
from __future__ import annotations

import sys
from pathlib import Path

V3_ROOT = Path(__file__).resolve().parents[1]
for p in (V3_ROOT / "src", V3_ROOT / "app", V3_ROOT / "api"):
    sys.path.insert(0, str(p))

from fastapi.testclient import TestClient  # noqa: E402
from main import app  # noqa: E402

client = TestClient(app)
checks = []


def check(name, condition):
    checks.append((name, bool(condition)))
    print(f"{'PASS' if condition else 'FAIL'}  {name}")


def main() -> int:
    r = client.get("/api/health")
    check("application starts / health endpoint succeeds", r.status_code == 200 and r.json()["status"] == "ok")

    r = client.get("/api/system/readiness")
    check("readiness reports READY", r.status_code == 200 and r.json()["status"] == "READY")

    r = client.get("/api/replay/cases")
    cases = r.json()
    check("historical cases load (10 real candidates)", r.status_code == 200 and len(cases) == 10)

    r = client.get("/api/replay/cases/representative")
    rep = r.json()
    check("representative default case loads and is not illustrative-only",
          r.status_code == 200 and rep["category"] != "ILLUSTRATIVE_ONLY")

    r = client.get("/api/replay/cases/2021_car60")
    check("illustrative case (2021_car60) loads", r.status_code == 200 and r.json()["category"] == "ILLUSTRATIVE_ONLY")

    r = client.get("/api/scenario/schema")
    check("scenario schema loads", r.status_code == 200 and r.json()["mode"] == "HYPOTHETICAL_SCENARIO")

    r = client.post("/api/scenario/infer", json={
        "current_track_temp_c": 35.0, "current_ambient_temp_c": 27.0, "forecast_future_ambient_temp_c": 29.0,
    })
    body = r.json()
    check("hypothetical scenario inference succeeds", r.status_code == 200)
    check("scenario output contains all five supported horizons",
          sorted(h["horizon_minutes"] for h in body.get("horizons", [])) == [15, 30, 60, 90, 120])
    check("scenario output labelled NOT_HISTORICAL_EVIDENCE", body.get("evidence_status") == "NOT_HISTORICAL_EVIDENCE")

    blob_values = []

    def walk(obj):
        if isinstance(obj, dict):
            for v in obj.values():
                walk(v)
        elif isinstance(obj, list):
            for v in obj:
                walk(v)
        elif isinstance(obj, str):
            blob_values.append(obj)

    walk(body)
    forbidden = {"RETAIN", "WITHDRAW", "OPTIMAL", "RECOMMENDED HORIZON"}
    check("no strategy recommendation appears in scenario output",
          not any(v.strip().upper() in forbidden for v in blob_values))

    print()
    n_pass = sum(1 for _, ok in checks if ok)
    print(f"{n_pass}/{len(checks)} smoke checks passed")
    return 0 if n_pass == len(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
