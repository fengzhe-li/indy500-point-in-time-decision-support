#!/usr/bin/env python3
"""Validate public claims, figure links and selected frozen source hashes."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)
    print(f"PASS  {message}")


def main() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    image_refs = re.findall(r"!\[[^]]*\]\(([^)]+)\)", readme)
    require(bool(image_refs), "README contains figures")
    missing = [ref for ref in image_refs if not (ROOT / ref).is_file()]
    require(not missing, f"all {len(image_refs)} README figure references resolve")

    core = json.loads((ROOT / "r5_2/manual/probabilistic_physics_core_v1.json").read_text())
    require(abs(core["mean_core"]["full_data_huber_coefficients"]["delta_track_temp_c"] + 0.03482532976361639) < 1e-12, "frozen track coefficient matches README")
    require(abs(core["mean_core"]["full_data_huber_coefficients"]["delta_air_temp_c"] - 0.18239338404039918) < 1e-12, "frozen ambient coefficient matches README")

    final = json.loads((ROOT / "weather/output/final_integration/indy500_final_v2_freeze_manifest.json").read_text())
    require(final["version"] == "FINAL_V2" and final["status"] == "FINAL_FROZEN", "FINAL_V2 manifest is frozen")
    for item in final.get("artifacts", {}).values():
        if isinstance(item, dict) and "path" in item and "sha256" in item:
            path = ROOT / item["path"]
            require(path.is_file() and sha256(path) == item["sha256"], f"frozen hash: {item['path']}")

    section = json.loads((ROOT / "weather/output/v2b_section_mechanism/v2b_freeze_manifest_v1.json").read_text())
    require(section["scope"]["final_physics_core_transitions"] == 41, "FINAL_V2 contains 41 transitions")
    require(section["scope"]["linked_with_usable_section_evidence"] == 39, "section linkage is 39/41")

    samples = pd.read_csv(ROOT / "weather/output/v2_future_track/future_track_samples_with_solar_v1.csv")
    require(len(samples) == 656, "future-state sample interface has 656 rows")

    stress = json.loads((ROOT / "weather/output/v2e_scenario_stress_test/v2e_freeze_manifest_v1.json").read_text())
    require(stress["scenario_design"]["total_scenarios"] == 135, "stress test has 135 scenarios")
    require(stress["principal_findings"]["120_min_p_improve_range"] == [0.20552, 0.6704], "120-minute probability range matches README")

    ext = json.loads((ROOT / "r6_regime_extension/output/external_regime_inference_backtest_2025_v2/external_regime_inference_backtest_2025_metrics_v2.json").read_text())
    require(ext["extended_validation"]["n"] == 15, "external sample has 15 cases")
    require(ext["product_subset"]["n"] == 4, "production-boundary external subset has 4 cases")
    require(abs(ext["extended_validation"]["mae_mph"] - 0.49160020387931286) < 1e-12, "external MAE matches README")
    require(abs(ext["extended_validation"]["direction_accuracy"] - 0.4666666666666667) < 1e-12, "external directional accuracy matches README")

    banned = ["predicts queue duration", "optimal wait recommendation", "autonomous race-strategy system"]
    require(not any(term in readme.lower() for term in banned), "README avoids prohibited strategy claims")
    print("\nPORTFOLIO_INTEGRITY_PASS")


if __name__ == "__main__":
    main()
