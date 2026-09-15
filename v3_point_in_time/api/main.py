"""Phase 4 FastAPI application.

CRITICAL RULE (Phase 4 spec Step 4/API RULE): this process is the only
thing the frontend talks to. It never lets the frontend read frozen
CSV/JSON files directly, and it never recomputes FINAL_V2 -- every
route here is a thin read of Phase 1-3's already-frozen, already-tested
outputs (see app/replay_service.py's module docstring).

Run with:
    uvicorn main:app --reload --port 8000
(from this directory), or via scripts/run_v3_app.sh from the repo root.
"""
from __future__ import annotations

import sys
from pathlib import Path

API_DIR = Path(__file__).resolve().parent
V3_ROOT = API_DIR.parent
APP_DIR = V3_ROOT / "app"

for p in (API_DIR, APP_DIR):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes import health, system, replay, predictions, validation, scenario

app = FastAPI(
    title="INDY 500 V3 — Pit-Wall Decision Support API",
    description=(
        "Read-only application layer over the frozen Phase 1-3 point-in-time "
        "probabilistic decision-support engine. Estimates p(Δv | H=h) for "
        "h in {15,30,60,90,120} minutes. Does not estimate P(H=h), does not "
        "predict queue waiting time, and never issues a retain/withdraw "
        "recommendation."
    ),
    version="4.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(system.router)
app.include_router(replay.router)
app.include_router(predictions.router)
app.include_router(validation.router)
app.include_router(scenario.router)
