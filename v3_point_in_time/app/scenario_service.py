"""Phase 5 Step 2 — Hypothetical Scenario Mode.

STRICT ISOLATION: this is the ONLY module in app/ that imports src/
scientific code (final_v2_adapter, applicability_gate, shadow_engine).
replay_service.py, provenance_service.py, and query_service.py remain
untouched and continue to read only Phase 3's already-frozen output --
the Step 1 architectural boundary (historical API = read-only
projection of frozen evidence) is preserved exactly by keeping this
module entirely separate from those three.

Scenario Mode runs the real, frozen FINAL_V2 adapter -- the exact same
`final_v2_adapter.infer()` function Phase 1-3 use, imported unmodified
-- on user-supplied hypothetical current-state and hypothetical
future-ambient input. There is no second implementation of the model
here (Phase 5 Step 23).

Its output is EPHEMERAL: nothing in this module writes to disk, to
output/replay/, to output/evaluation/, or to any other Phase 2/3 frozen
location. A scenario response is constructed in memory and returned;
if the caller does not keep it, it is gone.
"""
from __future__ import annotations

import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import applicability_gate  # noqa: E402
import final_v2_adapter  # noqa: E402
import shadow_engine  # noqa: E402 -- reused only for target_time_for(); not reimplemented here
from hashing import sha256_obj  # noqa: E402

# Same site constants Phase 1-3 use (weather/scripts/v2_add_solar_features.py).
# Not a user-editable scientific input -- the site does not change.
LATITUDE_DEG = 39.7950
LONGITUDE_DEG = -86.2348

# Same frozen Monte Carlo convention as config/v3_config.yaml. Using the
# same fixed seed/n_mc for every scenario call (rather than inventing a
# per-request seeding scheme) is what makes identical inputs reproducible
# (Phase 5 Step 6) without changing FINAL_V2's statistical semantics.
RANDOM_SEED = 20260914
N_MC = 20000

CALIBRATED_ANCHOR_HORIZONS_MIN = applicability_gate.CALIBRATED_ANCHOR_HORIZONS_MIN

MODE = "HYPOTHETICAL_SCENARIO"
EVIDENCE_STATUS = "NOT_HISTORICAL_EVIDENCE"

# Phase 5 Step 10 -- a small number of clearly synthetic, physically
# realistic presets (values drawn from the real range seen in
# weather/evidence/ptsc/... track/ambient observations, not invented
# extremes). Every preset is labelled DEMONSTRATION_PRESET /
# HYPOTHETICAL / NOT_HISTORICAL_EVIDENCE wherever it is surfaced.
SCENARIO_PRESETS = {
    "THERMALLY_STABLE": {
        "label": "Thermally stable",
        "current_track_temp_c": 35.0,
        "current_ambient_temp_c": 27.0,
        "forecast_future_ambient_temp_c": 27.0,
        "kind": "DEMONSTRATION_PRESET",
        "status": "HYPOTHETICAL",
        "evidence_status": EVIDENCE_STATUS,
    },
    "COOLING_TRACK": {
        "label": "Cooling track",
        "current_track_temp_c": 40.0,
        "current_ambient_temp_c": 30.0,
        "forecast_future_ambient_temp_c": 24.0,
        "kind": "DEMONSTRATION_PRESET",
        "status": "HYPOTHETICAL",
        "evidence_status": EVIDENCE_STATUS,
    },
    "WARMING_AMBIENT": {
        "label": "Warming ambient",
        "current_track_temp_c": 32.0,
        "current_ambient_temp_c": 22.0,
        "forecast_future_ambient_temp_c": 29.0,
        "kind": "DEMONSTRATION_PRESET",
        "status": "HYPOTHETICAL",
        "evidence_status": EVIDENCE_STATUS,
    },
}


class ScenarioInputError(Exception):
    """A malformed (not merely missing) scenario request, e.g. an
    unparsable decision_time. Routes translate this to HTTP 422 -- never
    a 500, and never a silently-defaulted value."""


def _resolve_decision_time(decision_time: Optional[str]) -> str:
    if decision_time is None:
        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    try:
        dt = datetime.fromisoformat(decision_time.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ScenarioInputError(f"decision_time {decision_time!r} is not valid ISO-8601: {exc}") from exc
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def run_scenario(
    current_track_temp_c: Optional[float],
    current_ambient_temp_c: Optional[float],
    forecast_future_ambient_temp_c: Optional[float],
    decision_time: Optional[str] = None,
) -> dict:
    """Run the frozen FINAL_V2 adapter at all five calibrated anchors for
    one hypothetical scenario. Missing required input fails closed to
    INPUT_INSUFFICIENT per horizon (matching applicability_gate's own
    fail-closed design) rather than being silently defaulted -- see
    Phase 5 Step 7.
    """
    decision_time_iso = _resolve_decision_time(decision_time)

    input_payload = {
        "current_track_temp_c": current_track_temp_c,
        "current_ambient_temp_c": current_ambient_temp_c,
        "forecast_future_ambient_temp_c": forecast_future_ambient_temp_c,
        "decision_time": decision_time_iso,
        "latitude_deg": LATITUDE_DEG,
        "longitude_deg": LONGITUDE_DEG,
        "random_seed": RANDOM_SEED,
        "n_mc": N_MC,
    }
    input_hash = sha256_obj(input_payload)
    scenario_id = f"scenario-{uuid.uuid4()}"
    model_hash = final_v2_adapter.model_hash()

    horizons = []
    for h in CALIBRATED_ANCHOR_HORIZONS_MIN:
        gate = applicability_gate.evaluate(
            horizon_min=h,
            current_track_temp_c=current_track_temp_c,
            current_ambient_temp_c=current_ambient_temp_c,
            forecast_future_ambient_temp_c=forecast_future_ambient_temp_c,
        )
        if gate.status in ("OUT_OF_SUPPORT", "INPUT_INSUFFICIENT"):
            horizons.append({
                "horizon_minutes": h,
                "status": gate.status,
                "reasons": list(gate.reasons),
            })
            continue

        target_time_iso = shadow_engine.target_time_for(decision_time_iso, h)
        output = final_v2_adapter.infer(
            current_track_temp_c=current_track_temp_c,
            current_ambient_temp_c=current_ambient_temp_c,
            forecast_future_ambient_temp_c=forecast_future_ambient_temp_c,
            decision_time=decision_time_iso,
            target_time=target_time_iso,
            horizon_min=h,
            latitude_deg=LATITUDE_DEG,
            longitude_deg=LONGITUDE_DEG,
            random_seed=RANDOM_SEED,
            n_mc=N_MC,
        )
        horizons.append({
            "horizon_minutes": h,
            "status": gate.status,
            "target_time": target_time_iso,
            "expected_delta_v": output.expected_delta_v,
            "median_delta_v": output.median_delta_v,
            "p_improve": output.p_improve,
            "pi80_low": output.pi80_low,
            "pi80_high": output.pi80_high,
            "pi90_low": output.pi90_low,
            "pi90_high": output.pi90_high,
            "mc_sd": output.mc_sd,
            "conditional_physical_opportunity_value": output.expected_delta_v,
        })

    return {
        "scenario_id": scenario_id,
        "mode": MODE,
        "evidence_status": EVIDENCE_STATUS,
        "input": {
            "current_track_temp_c": current_track_temp_c,
            "current_ambient_temp_c": current_ambient_temp_c,
            "forecast_future_ambient_temp_c": forecast_future_ambient_temp_c,
            "forecast_label": "USER-SUPPLIED HYPOTHETICAL FORECAST",
            "forecast_provenance": "NONE -- not tied to any real forecast vintage",
            "decision_time": decision_time_iso,
        },
        "supported_horizons_min": list(CALIBRATED_ANCHOR_HORIZONS_MIN),
        "horizons": horizons,
        "model_version": final_v2_adapter.MODEL_VERSION,
        "model_hash": model_hash,
        "input_hash": input_hash,
        "queue_time_prediction": "NOT MODELLED",
        "retain_withdraw_recommendation": "NOT ISSUED",
        "note": (
            "If another opportunity occurs at horizon h -- this is an ephemeral "
            "hypothetical conditional physical outlook. It is NOT historical "
            "evidence and NOT a forecast of when an opportunity will occur."
        ),
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }


def schema() -> dict:
    return {
        "mode": MODE,
        "evidence_status": EVIDENCE_STATUS,
        "fields": [
            {"name": "current_track_temp_c", "type": "float", "required": True, "unit": "degC"},
            {"name": "current_ambient_temp_c", "type": "float", "required": True, "unit": "degC"},
            {
                "name": "forecast_future_ambient_temp_c",
                "type": "float",
                "required": True,
                "unit": "degC",
                "note": (
                    "USER-SUPPLIED HYPOTHETICAL FORECAST, applied uniformly as the assumed "
                    "ambient temperature at every horizon's target time. Not derived from, "
                    "and not labelled as, any real forecast vintage."
                ),
            },
            {
                "name": "decision_time",
                "type": "string (ISO-8601 UTC)",
                "required": False,
                "note": "Defaults to the current time if omitted. Used only for solar geometry and target-time computation -- never treated as historical evidence.",
            },
        ],
        "supported_horizons_min": list(CALIBRATED_ANCHOR_HORIZONS_MIN),
        "presets": SCENARIO_PRESETS,
    }
