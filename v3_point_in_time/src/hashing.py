"""Hashing utilities for V3 provenance and immutability checks.

Uses the same convention as the existing frozen project
(weather/scripts/final_v2_freeze.py): plain hashlib.sha256 over file
bytes for files, and a canonical JSON encoding for in-memory records so
that identical logical content always hashes identically regardless of
Python dict ordering.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def sha256_file(path: Path) -> str:
    """Hash a file's raw bytes. Read-only; never writes to `path`."""
    data = Path(path).read_bytes()
    return hashlib.sha256(data).hexdigest()


def canonical_json(obj: Any) -> str:
    """Stable JSON encoding: sorted keys, fixed separators, no NaN/Infinity."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), allow_nan=False)


def sha256_obj(obj: Any) -> str:
    """Hash a JSON-serializable object via its canonical encoding."""
    return hashlib.sha256(canonical_json(obj).encode("utf-8")).hexdigest()


def hash_many_files(paths: list[Path]) -> dict:
    """Hash a list of files, returning {relative_path_str: sha256_hex}.

    Used by the V2 immutability check (Step 11). Read-only.
    """
    out = {}
    for p in paths:
        p = Path(p)
        out[str(p)] = sha256_file(p)
    return out
