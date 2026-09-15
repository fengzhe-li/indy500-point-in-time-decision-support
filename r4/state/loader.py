"""Manual JSON and R3C1-backed observable-scenario loaders."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Any, Mapping

from r4.performance import R3C1ReadOnlyAdapter

from .scenario import Availability, LoadedScenario, ObservableScenario, ScenarioValidationError, to_pit_wall_state


R3C1_STATE_ASSET = "decision_time_observable_state_v4_1_final.csv"


class ScenarioLoader:
    def __init__(self, project_root: str | Path):
        self.project_root = Path(project_root).resolve()
        self.r3c1 = R3C1ReadOnlyAdapter(self.project_root)

    def load_json(self, path: str | Path) -> LoadedScenario:
        with Path(path).open("r", encoding="utf-8") as f:
            return self.load_mapping(json.load(f))

    def load_mapping(self, raw: Mapping[str, Any]) -> LoadedScenario:
        return to_pit_wall_state(ObservableScenario.from_mapping(raw))

    def load_r3c1(self, state_id: str, manual_scenario: Mapping[str, Any]) -> LoadedScenario:
        """Overlay only temporally admissible R3C1 fields onto a manual scenario.

        Identity/timing, targets, lane eligibility, queues, and live environment
        remain manual/UNKNOWN unless supplied directly. Historical action/lane
        labels and second-attempt outcomes are intentionally ignored.
        """
        self.r3c1.assert_verified()
        matches = [row for row in self.r3c1.read_csv(R3C1_STATE_ASSET) if row["state_id"] == state_id]
        if len(matches) != 1:
            raise ScenarioValidationError(f"expected one R3C1 state row for {state_id!r}; found {len(matches)}")
        row = matches[0]
        if row.get("state_scope") != "TEMPORAL_SAFE_LIMITED_PREDECISION_STATE":
            raise ScenarioValidationError("R3C1 state row is not marked temporal-safe predecision state")
        raw = deepcopy(dict(manual_scenario))
        fields = raw.get("fields")
        if not isinstance(fields, dict) or "decision_timestamp_utc" not in fields:
            raise ScenarioValidationError("manual scenario must supply the complete R4A field structure")
        decision_time = fields["decision_timestamp_utc"].get("value")
        if not isinstance(decision_time, str):
            raise ScenarioValidationError("manual scenario must supply decision_timestamp_utc before R3C1 loading")

        def observed(name: str, value: Any, source: str) -> None:
            fields[name] = {
                "value": value, "availability": Availability.OBSERVED.value,
                "available_at_utc": decision_time, "valid_at_utc": decision_time,
                "source_reference": source, "derivation": None,
            }

        def derived(name: str, value: Any, source: str, rule: str) -> None:
            fields[name] = {
                "value": value, "availability": Availability.DERIVED_FROM_OBSERVABLES.value,
                "available_at_utc": decision_time, "valid_at_utc": decision_time,
                "source_reference": source, "derivation": rule,
            }

        source = f"{R3C1_STATE_ASSET}#{state_id}"
        if row.get("driver_name") and row["driver_name"] != "UNKNOWN":
            observed("driver_name", row["driver_name"], source)
        speed = self._number_or_none(row.get("first_attempt_speed_mph"))
        if speed is not None:
            observed("current_valid_four_lap_average_speed_mph", speed, source + ":first_attempt_speed_mph")
        exact_rank = self._exact_rank(row)
        if exact_rank is not None:
            observed("current_rank", exact_rank, source + ":predecision_state_evidence_ids=" + row.get("predecision_state_evidence_ids", ""))
        cutoff_speed = self._number_or_none(row.get("predecision_cutoff_speed_mph"))
        if cutoff_speed is not None:
            observed("current_cutoff_speed_mph", cutoff_speed, source + ":predecision_cutoff_speed_mph")
        completed = self._integer_or_none(row.get("first_car_attempt_index"))
        if completed is not None:
            derived("completed_attempt_count", completed, source + ":first_car_attempt_index",
                    "completed attempt count equals the canonical predecision first_car_attempt_index")
        validity = {
            "VALID_RETAINED": "VALID",
            "DISALLOWED": "INVALID",
            "INVALIDATED": "INVALID",
        }.get(row.get("first_attempt_status"))
        if validity is not None:
            derived("current_result_validity", validity, source + ":first_attempt_status",
                    "map explicit R3C1 result status; blank/generic status is never used")

        # Deliberately no read of historical_action_label or historical_lane_label.
        return self.load_mapping(raw)

    @staticmethod
    def _number_or_none(value: str | None) -> float | None:
        if value in (None, "", "UNKNOWN", "NOT_APPLICABLE"):
            return None
        try:
            return float(value)
        except ValueError:
            return None

    @staticmethod
    def _integer_or_none(value: str | None) -> int | None:
        if value in (None, "", "UNKNOWN", "NOT_APPLICABLE"):
            return None
        try:
            return int(value)
        except ValueError:
            return None

    @classmethod
    def _exact_rank(cls, row: Mapping[str, str]) -> int | None:
        rank = cls._integer_or_none(row.get("predecision_current_rank"))
        lower = cls._integer_or_none(row.get("predecision_rank_lower_bound"))
        upper = cls._integer_or_none(row.get("predecision_rank_upper_bound"))
        if rank is not None and lower == rank == upper:
            return rank
        return None
