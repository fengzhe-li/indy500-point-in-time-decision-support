"""Step 7 — applicability gate.

Statuses: SUPPORTED, CAUTION, OUT_OF_SUPPORT, INPUT_INSUFFICIENT.

Thresholds used here are copied from the frozen system's own published
definitions (v2a_freeze_manifest_v1.json,
operational_curve_metadata_v2.json), not invented. Where the frozen
system has not published a defensible numeric threshold (a current-state
physical-input support boundary), this gate reports NOT_YET_DEFINED
rather than fabricating one -- see existing_system_inventory.md
section 7.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

CALIBRATED_ANCHOR_HORIZONS_MIN = (15, 30, 60, 90, 120)
MAX_SUPPORTED_HORIZON_MIN = 120


@dataclass(frozen=True)
class ApplicabilityResult:
    status: str  # ApplicabilityStatus value
    reasons: tuple
    notes: tuple = ()


def evaluate(
    horizon_min: int,
    current_track_temp_c: Optional[float],
    current_ambient_temp_c: Optional[float],
    forecast_future_ambient_temp_c: Optional[float],
) -> ApplicabilityResult:
    reasons = []
    notes = []

    missing = [
        name
        for name, value in [
            ("current_track_temp_c", current_track_temp_c),
            ("current_ambient_temp_c", current_ambient_temp_c),
            ("forecast_future_ambient_temp_c", forecast_future_ambient_temp_c),
        ]
        if value is None
    ]
    if missing:
        return ApplicabilityResult(
            status="INPUT_INSUFFICIENT",
            reasons=tuple(f"MISSING_{m.upper()}" for m in missing),
        )

    if horizon_min > MAX_SUPPORTED_HORIZON_MIN:
        return ApplicabilityResult(
            status="OUT_OF_SUPPORT",
            reasons=(f"HORIZON_{horizon_min}_MIN_EXCEEDS_MAX_SUPPORTED_{MAX_SUPPORTED_HORIZON_MIN}_MIN",),
        )

    if horizon_min <= 0:
        return ApplicabilityResult(
            status="OUT_OF_SUPPORT",
            reasons=("HORIZON_AT_OR_BELOW_CURRENT_STATE_BOUNDARY",),
            notes=("Matches CURRENT_STATE_BOUNDARY policy in operational_curve_metadata_v2.json.",),
        )

    if horizon_min not in CALIBRATED_ANCHOR_HORIZONS_MIN:
        # Not one of the five independently fitted/calibrated anchors, but
        # within the supported <=120 min range: this is the same status the
        # frozen operational curve already assigns to intermediate minutes
        # (INTERPOLATED_OPERATIONAL), not a new invented category.
        reasons.append(f"HORIZON_{horizon_min}_MIN_NOT_A_CALIBRATED_ANCHOR")
        notes.append(
            "Frozen system anchors are exactly 15/30/60/90/120 min; "
            "intermediate minutes are INTERPOLATED_OPERATIONAL presentation "
            "values in the frozen operational curve, not independently "
            "calibrated FINAL_V2 scientific inference."
        )
        return ApplicabilityResult(status="CAUTION", reasons=tuple(reasons), notes=tuple(notes))

    notes.append(
        "No numeric historical-support boundary for arbitrary current "
        "track/ambient state is published by the frozen system "
        "(existing_system_inventory.md section 7): NOT_YET_DEFINED. "
        "This gate does not invent one, so a physically extreme but "
        "otherwise complete input still returns SUPPORTED here."
    )
    return ApplicabilityResult(status="SUPPORTED", reasons=(), notes=tuple(notes))
