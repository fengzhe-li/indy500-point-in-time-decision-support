#!/usr/bin/env bash
# Phase 5 Step 17/18 -- stage a minimal, auditable Docker build context.
#
# Copies EXACTLY the 32 frozen FINAL_V2 dependencies already enumerated
# in output/qa/v2_pre_implementation_hashes.txt (the same list
# scripts/run_v2_immutability_check.py treats as authoritative -- one
# definition, reused, not re-declared), preserving their relative paths
# from the repo root, plus the whole v3_point_in_time/ subsystem, into
# v3_point_in_time/docker/build_context/. Nothing else from the parent
# research repository is included: no raw PDFs, no unrelated weather
# archives, no other phases' scratch data.
#
# Run before `docker build` / `docker compose build`. Re-run any time the
# frozen dependency list or v3_point_in_time/ content changes.
set -euo pipefail

V3_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_ROOT="$(cd "$V3_ROOT/.." && pwd)"
CONTEXT_DIR="$V3_ROOT/docker/build_context"
BASELINE="$V3_ROOT/output/qa/v2_pre_implementation_hashes.txt"

echo "Preparing Docker build context at $CONTEXT_DIR ..."
rm -rf "$CONTEXT_DIR"
mkdir -p "$CONTEXT_DIR"

# 1. The 32 frozen FINAL_V2 dependencies, exact relative paths preserved.
n=0
while IFS= read -r line; do
  [ -z "$line" ] && continue
  rel_path="${line#*  }"
  src="$REPO_ROOT/$rel_path"
  dst="$CONTEXT_DIR/$rel_path"
  mkdir -p "$(dirname "$dst")"
  cp "$src" "$dst"
  n=$((n + 1))
done < "$BASELINE"
echo "Copied $n frozen scientific dependency files."

# 2. The whole v3_point_in_time/ subsystem, excluding local dev artifacts.
mkdir -p "$CONTEXT_DIR/v3_point_in_time"
rsync -a \
  --exclude 'frontend/node_modules' \
  --exclude 'frontend/dist' \
  --exclude 'docker/build_context' \
  --exclude '__pycache__' \
  --exclude '*.pyc' \
  --exclude '.pytest_cache' \
  "$V3_ROOT/" "$CONTEXT_DIR/v3_point_in_time/"

echo "Docker build context ready: $CONTEXT_DIR"
du -sh "$CONTEXT_DIR"
