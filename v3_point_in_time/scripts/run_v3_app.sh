#!/usr/bin/env bash
# Phase 4 Step 25 — one-command local start for the Pit-Wall Decision
# Support application. Starts the FastAPI backend and the Vite frontend
# dev server, both reading only local, already-frozen Phase 1-3 output
# (HISTORICAL_SHADOW_RESEARCH_MODE) -- no internet connection or
# environment-variable setup is required beyond `pip install` / `npm install`.
set -euo pipefail

V3_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
API_DIR="$V3_ROOT/api"
FRONTEND_DIR="$V3_ROOT/frontend"

cleanup() {
  echo ""
  echo "Stopping V3 application..."
  [[ -n "${API_PID:-}" ]] && kill "$API_PID" 2>/dev/null || true
  [[ -n "${WEB_PID:-}" ]] && kill "$WEB_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "============================================================"
echo "INDY 500 V3 -- PIT-WALL DECISION SUPPORT (Phase 4)"
echo "HISTORICAL_SHADOW_RESEARCH_MODE"
echo "============================================================"

echo "[1/2] Starting FastAPI backend on http://127.0.0.1:8000 ..."
(cd "$API_DIR" && uvicorn main:app --port 8000) &
API_PID=$!

echo "[2/2] Starting Vite frontend dev server on http://127.0.0.1:5173 ..."
(cd "$FRONTEND_DIR" && npm run dev) &
WEB_PID=$!

echo ""
echo "Backend API docs:  http://127.0.0.1:8000/docs"
echo "Frontend app:      http://127.0.0.1:5173"
echo ""
echo "Press Ctrl+C to stop both."

wait
