"""Step 11 — V2 immutability check.

Re-hashes every frozen FINAL_V2 dependency V3 may read (the same list
hashed BEFORE any V3 implementation work began, saved at
v3_point_in_time/output/qa/v2_pre_implementation_hashes.txt) and
compares against the current on-disk hashes.

Read-only: this script never writes to any frozen file. It writes only
its own report, v3_point_in_time/output/qa/v2_immutability_report.txt.

If any hash differs, the report says FAIL and this script exits 1 --
per the specification, that would mean STOP and report failure rather
than repairing or regenerating anything silently. (In practice, for
Phase 1 as implemented, nothing has changed -- see the report.)
"""
from __future__ import annotations

import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC_DIR))

REPO_ROOT = Path(__file__).resolve().parents[2]
QA_DIR = Path(__file__).resolve().parents[1] / "output" / "qa"
BEFORE_FILE = QA_DIR / "v2_pre_implementation_hashes.txt"
REPORT_FILE = QA_DIR / "v2_immutability_report.txt"

from hashing import sha256_file  # noqa: E402


def load_before(path: Path) -> dict:
    before = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        h, rel_path = line.split("  ", 1)
        before[rel_path] = h
    return before


def main() -> int:
    before = load_before(BEFORE_FILE)

    lines = []
    lines.append("=" * 72)
    lines.append("V3 STEP 11 — V2 FROZEN-ASSET IMMUTABILITY REPORT")
    lines.append("=" * 72)
    lines.append("")
    lines.append(f"Baseline captured before any V3 implementation work: {BEFORE_FILE.name}")
    lines.append(f"Files checked: {len(before)}")
    lines.append("")

    all_match = True
    for rel_path, before_hash in sorted(before.items()):
        full_path = REPO_ROOT / rel_path
        if not full_path.exists():
            all_match = False
            lines.append(f"MISSING   {rel_path}")
            continue
        after_hash = sha256_file(full_path)
        status = "MATCH" if after_hash == before_hash else "CHANGED"
        if status != "MATCH":
            all_match = False
        lines.append(f"{status:<8}  {rel_path}")
        if status != "MATCH":
            lines.append(f"          before: {before_hash}")
            lines.append(f"          after:  {after_hash}")

    lines.append("")
    lines.append("=" * 72)
    lines.append(f"OVERALL RESULT: {'PASS' if all_match else 'FAIL'}")
    lines.append("=" * 72)
    if not all_match:
        lines.append("")
        lines.append("STOP: at least one frozen FINAL_V2 asset changed during Phase 1")
        lines.append("implementation. Per specification, this must be reported as a")
        lines.append("failure, not silently repaired or regenerated.")

    report = "\n".join(lines)
    REPORT_FILE.write_text(report, encoding="utf-8")
    print(report)
    return 0 if all_match else 1


if __name__ == "__main__":
    raise SystemExit(main())
