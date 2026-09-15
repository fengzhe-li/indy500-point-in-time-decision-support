"""Step 6 — adapter around the frozen FINAL_V2 implementation.

This module does NOT reimplement FINAL_V2 mathematics. It:

  1. Reads the already-frozen, already-hashed numeric artifacts listed
     in weather/output/v2_future_track/v2a_freeze_manifest_v1.json and
     weather/output/final_integration/indy500_final_v2_freeze_manifest.json
     (frozen M2b track-model coefficients, frozen track-residual pool,
     frozen performance-core bootstrap draws, frozen performance-residual
     pool) as plain read-only data.
  2. Imports and calls, UNMODIFIED, the two pure helper functions that
     already implement the Monte Carlo combination
     (`symmetrized_draws_from_values`, `summarize_draws`) directly from
     weather/scripts/v2_integrate_track_to_performance_mc.py.
  3. Imports and calls, UNMODIFIED, the solar-geometry function
     `solar_elevation_deg` from weather/scripts/v2_add_solar_features.py.
  4. Evaluates the exact closed-form formula documented in
     indy500_final_v2_system_specification.md section 9 for ONE new
     point-in-time scenario, instead of the pre-built row set the
     original batch script iterates over.

No LinearRegression.fit() is ever called here. No frozen file is ever
opened for writing.
"""
from __future__ import annotations

import importlib.util
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict

import numpy as np
import pandas as pd

from schemas import FinalV2Output

REPO_ROOT = Path(__file__).resolve().parents[2]

TRACK_COEF_FILE = REPO_ROOT / "weather/output/v2_future_track/v2a_full_sample_track_model_coefficients_v1.csv"
TRACK_RESID_FILE = REPO_ROOT / "weather/output/v2_future_track/future_track_residuals_v1.csv"
PERF_BOOT_FILE = REPO_ROOT / "r5_2/manual/probabilistic_physics_coefficient_bootstrap_v1.csv"
PERF_RESID_FILE = REPO_ROOT / "r5_2/manual/probabilistic_physics_loyo_residuals_v1.csv"

MC_SCRIPT = REPO_ROOT / "weather/scripts/v2_integrate_track_to_performance_mc.py"
SOLAR_SCRIPT = REPO_ROOT / "weather/scripts/v2_add_solar_features.py"

TRACK_MODEL_NAME = "M2b_mean_solar"
MODEL_VERSION = "FINAL_V2"


def _import_from_path(module_name: str, path: Path):
    """Import a standalone script (not a package) by file path, without
    executing its `if __name__ == "__main__"` block (that guard means
    importing it never triggers its batch main()/file writes)."""
    spec = importlib.util.spec_from_file_location(module_name, str(path))
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


_mc_module = _import_from_path("_frozen_v2_mc", MC_SCRIPT)
_solar_module = _import_from_path("_frozen_v2_solar", SOLAR_SCRIPT)

# Reused, unmodified frozen pure functions.
symmetrized_draws_from_values = _mc_module.symmetrized_draws_from_values
summarize_draws = _mc_module.summarize_draws
solar_elevation_deg = _solar_module.solar_elevation_deg


def _parse(ts: str) -> datetime:
    dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


@dataclass
class FrozenArtifacts:
    track_coefficients: Dict[int, dict]
    track_residual_pools: Dict[int, np.ndarray]
    bootstrap_pairs: pd.DataFrame
    performance_residual_pool: np.ndarray
    source_hashes: Dict[str, str]


_CACHE: FrozenArtifacts | None = None


def load_frozen_artifacts() -> FrozenArtifacts:
    """Load frozen inputs once and cache them for the process lifetime.
    Every path here is opened for reading only."""
    global _CACHE
    if _CACHE is not None:
        return _CACHE

    from hashing import sha256_file

    coef_df = pd.read_csv(TRACK_COEF_FILE)
    track_coefficients = {
        int(row["horizon_min"]): {
            "intercept_c": float(row["intercept_c"]),
            "beta_delta_ambient_temp_c": float(row["beta_delta_ambient_temp_c"]),
            "beta_thermal_gap_0_c": float(row["beta_thermal_gap_0_c"]),
            "beta_solar_elevation_mean_deg": float(row["beta_solar_elevation_mean_deg"]),
        }
        for _, row in coef_df.iterrows()
    }

    resid_df = pd.read_csv(TRACK_RESID_FILE)
    resid_df = resid_df[resid_df["model"] == TRACK_MODEL_NAME]
    track_residual_pools = {
        int(h): resid_df.loc[resid_df["horizon_min"] == h, "residual_c"].dropna().to_numpy()
        for h in sorted(resid_df["horizon_min"].unique())
    }

    bootstrap_pairs = (
        pd.read_csv(PERF_BOOT_FILE)[["beta_track_temp", "beta_ambient_temp"]]
        .dropna()
        .reset_index(drop=True)
    )

    performance_residual_pool = (
        pd.read_csv(PERF_RESID_FILE)["residual_loyo_centered"].dropna().to_numpy()
    )

    source_hashes = {
        str(p): sha256_file(p)
        for p in [TRACK_COEF_FILE, TRACK_RESID_FILE, PERF_BOOT_FILE, PERF_RESID_FILE]
    }

    _CACHE = FrozenArtifacts(
        track_coefficients=track_coefficients,
        track_residual_pools=track_residual_pools,
        bootstrap_pairs=bootstrap_pairs,
        performance_residual_pool=performance_residual_pool,
        source_hashes=source_hashes,
    )
    return _CACHE


def model_hash() -> str:
    """A stable identifier for exactly which frozen artifacts this
    adapter run used, for inclusion in every ShadowPrediction."""
    from hashing import sha256_obj

    artifacts = load_frozen_artifacts()
    return sha256_obj({"model_version": MODEL_VERSION, **artifacts.source_hashes})


def infer(
    current_track_temp_c: float,
    current_ambient_temp_c: float,
    forecast_future_ambient_temp_c: float,
    decision_time: str,
    target_time: str,
    horizon_min: int,
    latitude_deg: float,
    longitude_deg: float,
    random_seed: int,
    n_mc: int,
) -> FinalV2Output:
    """Run the frozen FINAL_V2 physical-response Monte Carlo for one new
    point-in-time scenario at a single supported horizon.

    Raises KeyError if horizon_min is not one of the frozen model's five
    fitted horizons (15/30/60/90/120) -- callers must route horizon
    support decisions through applicability_gate.py before calling this.
    """
    artifacts = load_frozen_artifacts()
    if horizon_min not in artifacts.track_coefficients:
        raise KeyError(
            f"horizon_min={horizon_min} has no frozen M2b coefficients; "
            f"supported: {sorted(artifacts.track_coefficients)}"
        )

    coef = artifacts.track_coefficients[horizon_min]
    thermal_gap_0_c = current_track_temp_c - current_ambient_temp_c
    delta_ambient_temp_c = forecast_future_ambient_temp_c - current_ambient_temp_c

    t0 = _parse(decision_time)
    t1 = _parse(target_time)
    solar_elevation_mean_deg = (
        solar_elevation_deg(t0, latitude_deg, longitude_deg)
        + solar_elevation_deg(t1, latitude_deg, longitude_deg)
    ) / 2.0

    # Frozen M2b_mean_solar point prediction (already-fitted coefficients;
    # no .fit() call).
    point_delta_track = (
        coef["intercept_c"]
        + coef["beta_delta_ambient_temp_c"] * delta_ambient_temp_c
        + coef["beta_thermal_gap_0_c"] * thermal_gap_0_c
        + coef["beta_solar_elevation_mean_deg"] * solar_elevation_mean_deg
    )

    rng = np.random.default_rng(random_seed)

    track_noise = symmetrized_draws_from_values(
        artifacts.track_residual_pools[horizon_min], n_mc, rng
    )
    delta_track_draws = point_delta_track + track_noise

    coef_idx = rng.integers(0, len(artifacts.bootstrap_pairs), size=n_mc)
    beta_track = artifacts.bootstrap_pairs["beta_track_temp"].to_numpy()[coef_idx]
    beta_ambient = artifacts.bootstrap_pairs["beta_ambient_temp"].to_numpy()[coef_idx]

    perf_noise = symmetrized_draws_from_values(
        artifacts.performance_residual_pool, n_mc, rng
    )

    delta_speed_draws = (
        beta_track * delta_track_draws
        + beta_ambient * delta_ambient_temp_c
        + perf_noise
    )

    summary = summarize_draws(delta_speed_draws)

    return FinalV2Output(
        horizon_minutes=horizon_min,
        expected_delta_v=summary["expected_delta_speed_mph"],
        median_delta_v=summary["median_delta_speed_mph"],
        p_improve=summary["p_improve"],
        pi80_low=summary["lower_80_mph"],
        pi80_high=summary["upper_80_mph"],
        pi90_low=summary["lower_90_mph"],
        pi90_high=summary["upper_90_mph"],
        mc_sd=summary["mc_sd_mph"],
    )
