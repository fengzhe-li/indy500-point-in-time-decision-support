"""Leakage-safe, field-provenanced R4A scenario input."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
import math
from typing import Any, Mapping

from r4.simulator.actions import Action

from .models import PitWallState, QueueObservation
from .targets import AdvancementBenchmark, CurrentResultReference, DecisionTarget, DecisionTargetType


class ScenarioValidationError(ValueError):
    pass


class Availability(str, Enum):
    OBSERVED = "OBSERVED"
    DERIVED_FROM_OBSERVABLES = "DERIVED_FROM_OBSERVABLES"
    FORECAST_AVAILABLE_AT_DECISION_TIME = "FORECAST_AVAILABLE_AT_DECISION_TIME"
    UNKNOWN = "UNKNOWN"


SCENARIO_FIELDS = (
    "driver_name", "car_number", "decision_timestamp_utc", "session_start_time_utc",
    "session_end_time_utc", "session_remaining_seconds",
    "current_valid_four_lap_average_speed_mph", "current_rank", "advancement_benchmark_label",
    "advancement_benchmark_rank",
    "current_cutoff_speed_mph", "completed_attempt_count", "current_result_validity",
    "lane1_eligibility", "lane2_eligibility", "visible_lane1_queue_count",
    "visible_lane2_queue_count", "visible_cars_currently_queued", "ambient_temperature_c",
    "track_temperature_c", "relative_humidity_percent", "pressure_hpa", "wind_speed_mps",
    "wind_direction_degrees", "gust_speed_mps", "cloud_cover_percent",
    "shortwave_radiation_w_m2", "solar_elevation_degrees", "solar_azimuth_degrees",
    "rain_interruption_observable_state",
)

WEATHER_FIELDS = {
    "ambient_temperature_c", "track_temperature_c", "relative_humidity_percent",
    "pressure_hpa", "wind_speed_mps", "wind_direction_degrees", "gust_speed_mps",
    "cloud_cover_percent", "shortwave_radiation_w_m2", "solar_elevation_degrees",
    "solar_azimuth_degrees", "rain_interruption_observable_state",
}

STRING_FIELDS = {
    "driver_name", "car_number", "decision_timestamp_utc", "session_start_time_utc",
    "session_end_time_utc", "current_result_validity", "advancement_benchmark_label",
    "rain_interruption_observable_state",
}
INTEGER_FIELDS = {
    "current_rank", "advancement_benchmark_rank", "completed_attempt_count", "visible_lane1_queue_count",
    "visible_lane2_queue_count",
}
BOOLEAN_FIELDS = {"lane1_eligibility", "lane2_eligibility"}
LIST_FIELDS = {"visible_cars_currently_queued"}
NUMBER_FIELDS = set(SCENARIO_FIELDS) - STRING_FIELDS - INTEGER_FIELDS - BOOLEAN_FIELDS - LIST_FIELDS

PROHIBITED_INPUT_NAMES = {
    "post_decision_information", "post_decision_result", "realized_future_weather",
    "future_competitor_actions", "inferred_historical_queue_wait", "historical_queue_wait",
    "future_track_grip_truth", "future_tire_temperature_truth", "future_tire_thermal_truth",
}


def parse_utc(value: str, field_name: str) -> datetime:
    if not isinstance(value, str):
        raise ScenarioValidationError(f"{field_name} must be an ISO-8601 UTC string")
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ScenarioValidationError(f"{field_name} is not a valid ISO-8601 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise ScenarioValidationError(f"{field_name} must be UTC")
    return parsed.astimezone(timezone.utc)


@dataclass(frozen=True)
class ProvenancedValue:
    value: Any
    availability: Availability
    available_at_utc: str | None
    valid_at_utc: str | None
    source_reference: str | None
    derivation: str | None

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any], field_name: str) -> "ProvenancedValue":
        expected = {"value", "availability", "available_at_utc", "valid_at_utc", "source_reference", "derivation"}
        if not isinstance(value, Mapping) or set(value) != expected:
            raise ScenarioValidationError(f"{field_name} must contain exactly {sorted(expected)}")
        try:
            availability = Availability(value["availability"])
        except (ValueError, TypeError) as exc:
            raise ScenarioValidationError(f"{field_name}.availability is invalid") from exc
        return cls(value["value"], availability, value["available_at_utc"], value["valid_at_utc"],
                   value["source_reference"], value["derivation"])


@dataclass(frozen=True)
class ObservableScenario:
    schema_version: str
    fields: Mapping[str, ProvenancedValue]
    decision_target: DecisionTarget

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> "ObservableScenario":
        if not isinstance(raw, Mapping):
            raise ScenarioValidationError("scenario must be a JSON object")
        allowed_top = {"schema_version", "fields", "decision_target"}
        extras = set(raw) - allowed_top
        if extras:
            forbidden = sorted(extras & PROHIBITED_INPUT_NAMES)
            if forbidden:
                raise ScenarioValidationError("prohibited future/leakage fields: " + ", ".join(forbidden))
            raise ScenarioValidationError("unexpected scenario fields: " + ", ".join(sorted(extras)))
        if raw.get("schema_version") != "R4A_OBSERVABLE_SCENARIO_V1":
            raise ScenarioValidationError("schema_version must be R4A_OBSERVABLE_SCENARIO_V1")
        fields_raw = raw.get("fields")
        if isinstance(fields_raw, Mapping) and "target_rank" in fields_raw:
            raise ScenarioValidationError(
                "target_rank is deprecated and is not reinterpreted; supply an explicit "
                "advancement_benchmark_rank and format-regime benchmark provenance"
            )
        if not isinstance(fields_raw, Mapping) or set(fields_raw) != set(SCENARIO_FIELDS):
            missing = sorted(set(SCENARIO_FIELDS) - set(fields_raw or {}))
            extra = sorted(set(fields_raw or {}) - set(SCENARIO_FIELDS))
            raise ScenarioValidationError(f"scenario fields mismatch; missing={missing}; extra={extra}")
        fields = {name: ProvenancedValue.from_mapping(fields_raw[name], name) for name in SCENARIO_FIELDS}
        target_raw = raw.get("decision_target")
        if not isinstance(target_raw, Mapping) or set(target_raw) != {"type"}:
            raise ScenarioValidationError("decision_target must contain only type")
        if target_raw.get("type") in {"IMPROVE_CURRENT_SPEED", "REACH_TARGET_RANK"}:
            raise ScenarioValidationError(
                f"decision_target.type {target_raw['type']} is deprecated and is not silently reinterpreted"
            )
        try:
            target = DecisionTarget(DecisionTargetType(target_raw["type"]))
        except (ValueError, TypeError) as exc:
            raise ScenarioValidationError("decision_target.type is invalid") from exc
        scenario = cls(raw["schema_version"], fields, target)
        scenario.validate()
        return scenario

    def validate(self) -> None:
        decision_field = self.fields["decision_timestamp_utc"]
        if decision_field.availability is Availability.UNKNOWN or decision_field.value is None:
            raise ScenarioValidationError("decision_timestamp_utc cannot be UNKNOWN")
        decision_time = parse_utc(decision_field.value, "decision_timestamp_utc")

        for name, field in self.fields.items():
            if field.availability is Availability.UNKNOWN:
                if field.value is not None:
                    raise ScenarioValidationError(f"{name}: UNKNOWN must have null value")
                if field.available_at_utc is not None or field.valid_at_utc is not None:
                    raise ScenarioValidationError(f"{name}: UNKNOWN cannot carry availability/valid timestamps")
                continue
            if field.value is None:
                raise ScenarioValidationError(f"{name}: non-UNKNOWN field must have a value")
            if not field.source_reference:
                raise ScenarioValidationError(f"{name}: non-UNKNOWN field requires source_reference")
            if field.available_at_utc is None:
                raise ScenarioValidationError(f"{name}: non-UNKNOWN field requires available_at_utc")
            available = parse_utc(field.available_at_utc, f"{name}.available_at_utc")
            if available > decision_time:
                raise ScenarioValidationError(f"{name}: post-decision availability is prohibited")
            if field.availability is Availability.DERIVED_FROM_OBSERVABLES and not field.derivation:
                raise ScenarioValidationError(f"{name}: derived value requires derivation")
            if field.availability is Availability.FORECAST_AVAILABLE_AT_DECISION_TIME:
                if name not in WEATHER_FIELDS:
                    raise ScenarioValidationError(f"{name}: forecast provenance is allowed only for environment fields")
                if field.valid_at_utc is None:
                    raise ScenarioValidationError(f"{name}: forecast field requires valid_at_utc")
                parse_utc(field.valid_at_utc, f"{name}.valid_at_utc")
            elif field.valid_at_utc is not None and parse_utc(field.valid_at_utc, f"{name}.valid_at_utc") > decision_time:
                raise ScenarioValidationError(f"{name}: realized future value is prohibited")
            self._validate_type(name, field.value)

        start = self._required_time("session_start_time_utc")
        end = self._required_time("session_end_time_utc")
        if not start <= decision_time <= end:
            raise ScenarioValidationError("decision_timestamp_utc must lie within the session interval")
        remaining = self.fields["session_remaining_seconds"]
        if remaining.availability is not Availability.UNKNOWN:
            expected = (end - decision_time).total_seconds()
            if not math.isclose(float(remaining.value), expected, rel_tol=0.0, abs_tol=1e-6):
                raise ScenarioValidationError("session_remaining_seconds must equal session_end_time_utc - decision_timestamp_utc")
        if self.decision_target.target_type is DecisionTargetType.CROSS_ADVANCEMENT_BENCHMARK:
            rank_unknown = self.fields["advancement_benchmark_rank"].availability is Availability.UNKNOWN
            speed_unknown = self.fields["current_cutoff_speed_mph"].availability is Availability.UNKNOWN
            if rank_unknown and speed_unknown:
                raise ScenarioValidationError(
                    "CROSS_ADVANCEMENT_BENCHMARK requires an observed/derived benchmark rank or cutoff speed"
                )

    def _required_time(self, name: str) -> datetime:
        field = self.fields[name]
        if field.availability is Availability.UNKNOWN or field.value is None:
            raise ScenarioValidationError(f"{name} cannot be UNKNOWN")
        return parse_utc(field.value, name)

    @staticmethod
    def _validate_type(name: str, value: Any) -> None:
        if name in STRING_FIELDS and not isinstance(value, str):
            raise ScenarioValidationError(f"{name} must be a string; numeric car-number normalization is prohibited")
        if name in INTEGER_FIELDS and (not isinstance(value, int) or isinstance(value, bool)):
            raise ScenarioValidationError(f"{name} must be an integer")
        if name in BOOLEAN_FIELDS and not isinstance(value, bool):
            raise ScenarioValidationError(f"{name} must be boolean")
        if name in LIST_FIELDS and (not isinstance(value, list) or not all(isinstance(v, str) for v in value)):
            raise ScenarioValidationError(f"{name} must be an array of strings")
        if name in NUMBER_FIELDS and (not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(float(value))):
            raise ScenarioValidationError(f"{name} must be a finite number")
        if name in {"current_rank", "advancement_benchmark_rank"} and value < 1:
            raise ScenarioValidationError(f"{name} must be at least 1")
        if name in {"completed_attempt_count", "visible_lane1_queue_count", "visible_lane2_queue_count"} and value < 0:
            raise ScenarioValidationError(f"{name} cannot be negative")
        if name in {"session_remaining_seconds", "wind_speed_mps", "gust_speed_mps", "shortwave_radiation_w_m2"} and value < 0:
            raise ScenarioValidationError(f"{name} cannot be negative")
        if name in {"relative_humidity_percent", "cloud_cover_percent"} and not 0 <= value <= 100:
            raise ScenarioValidationError(f"{name} must be within 0..100")
        if name in {"wind_direction_degrees", "solar_azimuth_degrees"} and not 0 <= value < 360:
            raise ScenarioValidationError(f"{name} must be within [0, 360)")
        if name == "solar_elevation_degrees" and not -90 <= value <= 90:
            raise ScenarioValidationError("solar_elevation_degrees must be within -90..90")
        if name == "pressure_hpa" and value <= 0:
            raise ScenarioValidationError("pressure_hpa must be positive")
        if name == "current_result_validity" and value not in {"VALID", "INVALID", "NO_CURRENT_RESULT"}:
            raise ScenarioValidationError("current_result_validity must be VALID, INVALID, or NO_CURRENT_RESULT")


@dataclass(frozen=True)
class ObservablePitWallState(PitWallState):
    """PitWallState extension carrying the complete R4A decision context."""

    session_start_time: datetime
    session_end_time: datetime
    advancement_benchmark_label: str | None
    advancement_benchmark_rank: int | None
    current_result_validity: str | None
    visible_cars_currently_queued: tuple[str, ...] | None
    rain_interruption_observable_state: str | None
    decision_target: DecisionTarget
    field_provenance: Mapping[str, ProvenancedValue]

    @property
    def current_result_reference(self) -> CurrentResultReference:
        return CurrentResultReference(
            self.current_valid_speed_mph, self.current_rank, self.current_result_validity
        )

    @property
    def advancement_benchmark(self) -> AdvancementBenchmark:
        return AdvancementBenchmark(
            self.advancement_benchmark_label, self.advancement_benchmark_rank, self.cutoff_speed_mph
        )

    def to_dict(self) -> dict[str, Any]:
        value = super().to_dict()
        value["session_start_time"] = self.session_start_time.isoformat()
        value["session_end_time"] = self.session_end_time.isoformat()
        value["decision_target"] = {"type": self.decision_target.target_type.value}
        value["field_provenance"] = {
            name: {
                "value": item.value,
                "availability": item.availability.value,
                "available_at_utc": item.available_at_utc,
                "valid_at_utc": item.valid_at_utc,
                "source_reference": item.source_reference,
                "derivation": item.derivation,
            }
            for name, item in self.field_provenance.items()
        }
        return value


@dataclass(frozen=True)
class LoadedScenario:
    scenario: ObservableScenario
    pit_wall_state: ObservablePitWallState
    simulation_blockers: tuple[str, ...]


def _queue_observation(field: ProvenancedValue) -> QueueObservation:
    if field.availability is Availability.UNKNOWN:
        return QueueObservation("UNKNOWN")
    return QueueObservation(
        "OBSERVED" if field.availability is Availability.OBSERVED else "PARTIAL",
        observed_at=parse_utc(field.available_at_utc, "queue.available_at_utc"),
        queue_length=int(field.value), ordered_entry_ids=None,
        evidence_reference=field.source_reference,
    )


def to_pit_wall_state(scenario: ObservableScenario) -> LoadedScenario:
    f = scenario.fields
    get = lambda name: None if f[name].availability is Availability.UNKNOWN else f[name].value
    driver_name, car_number = get("driver_name"), get("car_number")
    if not driver_name or not car_number:
        raise ScenarioValidationError("driver_name and car_number must be available to construct PitWallState")
    if get("session_remaining_seconds") is None or get("completed_attempt_count") is None:
        raise ScenarioValidationError(
            "session_remaining_seconds and completed_attempt_count must be available to construct PitWallState"
        )
    result_validity = get("current_result_validity")
    lane1 = get("lane1_eligibility")
    lane2 = get("lane2_eligibility")
    blockers = []
    if lane1 is None: blockers.append("REPEAT_LANE1_WITHDRAW_CURRENT_RESULT: eligibility UNKNOWN")
    if lane2 is None: blockers.append("REPEAT_LANE2_RETAIN_CURRENT_RESULT: eligibility UNKNOWN")
    if result_validity is None: blockers.append("STOP_RETAIN_CURRENT_RESULT: current result validity UNKNOWN")
    eligibility = {
        Action.STOP_RETAIN_CURRENT_RESULT.value: result_validity == "VALID",
        Action.REPEAT_LANE2_RETAIN_CURRENT_RESULT.value: lane2 is True,
        Action.REPEAT_LANE1_WITHDRAW_CURRENT_RESULT.value: lane1 is True,
    }
    visible_cars = get("visible_cars_currently_queued")
    pit = ObservablePitWallState(
        decision_timestamp=parse_utc(get("decision_timestamp_utc"), "decision_timestamp_utc"),
        session_remaining_seconds=float(get("session_remaining_seconds")),
        driver_id=f"SCENARIO::{car_number}::{driver_name}", driver_name=driver_name, car_number=car_number,
        current_valid_speed_mph=get("current_valid_four_lap_average_speed_mph"),
        current_rank=get("current_rank"), cutoff_rank=None,
        cutoff_speed_mph=get("current_cutoff_speed_mph"),
        attempt_count=int(get("completed_attempt_count")), action_eligibility=eligibility,
        lane1_queue_state=_queue_observation(f["visible_lane1_queue_count"]),
        lane2_queue_state=_queue_observation(f["visible_lane2_queue_count"]),
        ambient_temperature_c=get("ambient_temperature_c"), track_temperature_c=get("track_temperature_c"),
        relative_humidity_percent=get("relative_humidity_percent"), pressure_hpa=get("pressure_hpa"),
        wind_speed_mps=get("wind_speed_mps"), wind_direction_degrees=get("wind_direction_degrees"),
        gust_speed_mps=get("gust_speed_mps"), cloud_cover_percent=get("cloud_cover_percent"),
        shortwave_radiation_w_m2=get("shortwave_radiation_w_m2"),
        solar_elevation_degrees=get("solar_elevation_degrees"), solar_azimuth_degrees=get("solar_azimuth_degrees"),
        session_start_time=parse_utc(get("session_start_time_utc"), "session_start_time_utc"),
        session_end_time=parse_utc(get("session_end_time_utc"), "session_end_time_utc"),
        advancement_benchmark_label=get("advancement_benchmark_label"),
        advancement_benchmark_rank=get("advancement_benchmark_rank"),
        current_result_validity=result_validity,
        visible_cars_currently_queued=None if visible_cars is None else tuple(visible_cars),
        rain_interruption_observable_state=get("rain_interruption_observable_state"),
        decision_target=scenario.decision_target, field_provenance=dict(f),
    )
    return LoadedScenario(scenario, pit, tuple(blockers))
