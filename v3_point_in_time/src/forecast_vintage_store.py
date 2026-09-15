"""Step 3 — forecast vintage store and selection layer.

Fundamental invariant enforced here:

    forecast.issue_time <= decision_time

For a decision timestamp t and target horizon h, target_time = t + h.
The store selects only a forecast that was available at or before t,
preferring the most recent valid vintage, and secondarily the vintage
whose valid_time is closest to target_time (HRRR's hourly valid-time
grid rarely lands exactly on t + h; the resulting error is recorded,
never hidden).

This module never selects a forecast issued after decision_time. If no
eligible forecast exists, `select()` returns None and the caller (the
point-in-time guard / shadow engine) must fail closed.
"""
from __future__ import annotations

import csv
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional

from schemas import ForecastVintage
from hashing import sha256_file


def _parse(ts: str) -> datetime:
    dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


class ForecastVintageStore:
    """Holds a list of ForecastVintage records and selects among them.

    Records can come from a real frozen source file (load_hrrr_features)
    or be supplied directly (e.g. synthetic test fixtures). The
    selection logic (`select`) is identical either way -- it never knows
    or cares whether a vintage is real or synthetic.
    """

    def __init__(self, vintages: Optional[List[ForecastVintage]] = None):
        self._vintages: List[ForecastVintage] = list(vintages or [])

    def add(self, vintage: ForecastVintage) -> None:
        self._vintages.append(vintage)

    def all(self) -> List[ForecastVintage]:
        return list(self._vintages)

    @classmethod
    def load_hrrr_features(
        cls,
        path: Path,
        latitude_deg: float,
        longitude_deg: float,
    ) -> "ForecastVintageStore":
        """Load real historical HRRR forecast vintages from the frozen
        project extract. Read-only; the source file is never modified.

        issue_time is the nominal HRRR cycle_time_utc (see
        point_in_time_guard.py module docstring for the documented
        availability-latency limitation this implies).
        """
        path = Path(path)
        source_hash = sha256_file(path)
        store = cls()
        with path.open(newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                cycle = row["cycle_time_utc"]
                valid = row["valid_time_utc"]
                lead_hours = float(row["forecast_lead_hours"])
                forecast_id = (
                    f"HRRR:{row['date']}:{row['forecast_hour']}:"
                    f"{cycle}:{valid}"
                )
                store.add(
                    ForecastVintage(
                        forecast_id=forecast_id,
                        source="NOAA",
                        model_name="HRRR",
                        model_run=str(row["forecast_hour"]),
                        issue_time=_iso(_parse(cycle)),
                        retrieved_at=None,
                        valid_time=_iso(_parse(valid)),
                        lead_minutes=lead_hours * 60.0,
                        ambient_temp_c=float(row["temp_c"]),
                        solar_or_radiation=float(row.get("shortwave_radiation_wm2") or 0.0) or None,
                        wind_speed=float(row.get("wind_speed_10m_ms") or 0.0) or None,
                        wind_gust=float(row.get("gust_ms") or 0.0) or None,
                        cloud_cover=float(row.get("cloud_cover_pct") or 0.0) or None,
                        pressure=float(row.get("pressure_hpa") or 0.0) or None,
                        source_uri=str(path),
                        source_hash=source_hash,
                        availability_time=None,
                        availability_time_quality="UNKNOWN",
                    )
                )
        return store

    def select(
        self,
        decision_time: str,
        target_time: str,
    ) -> Optional[dict]:
        """Select the best eligible forecast vintage for a decision.

        Eligibility: vintage.issue_time <= decision_time (strict
        invariant; never violated, regardless of how close a
        higher-quality vintage might otherwise be).

        Preference order among eligible vintages (per specification
        Step 3: "Prefer the most recent valid forecast vintage available
        at t"):
          1. Most recent issue_time (freshest model run available at t)
             is the PRIMARY criterion -- a fresher initialization is
             preferred even over an older run's closer nominal lead.
          2. Among vintages tied on issue_time (e.g. several lead times
             from the same model run), smallest absolute difference
             between valid_time and target_time is the tiebreaker.

        Returns a dict: {"vintage": ForecastVintage,
        "valid_time_error_minutes": float} or None if no eligible
        vintage exists.
        """
        t_decision = _parse(decision_time)
        t_target = _parse(target_time)

        eligible = [
            v for v in self._vintages
            if _parse(v.issue_time) <= t_decision
        ]
        if not eligible:
            return None

        def sort_key(v: ForecastVintage):
            issue_recency = -_parse(v.issue_time).timestamp()
            valid_error = abs((_parse(v.valid_time) - t_target).total_seconds())
            return (issue_recency, valid_error)

        best = min(eligible, key=sort_key)
        error_minutes = abs((_parse(best.valid_time) - t_target).total_seconds()) / 60.0
        return {"vintage": best, "valid_time_error_minutes": error_minutes}
