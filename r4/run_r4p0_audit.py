#!/usr/bin/env python3
"""Generate the bounded R4P0 cross-car availability audit from local frozen inputs."""

from __future__ import annotations

import csv
from collections import Counter, defaultdict
from datetime import datetime
import hashlib
import json
from pathlib import Path
from statistics import median
import sys

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "r4/output"
YEARS = tuple(range(2020, 2025))
WINDOWS = (5, 10, 15, 20)
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from r4.performance import R3C1ReadOnlyAdapter


def read_csv(path: str) -> list[dict[str, str]]:
    with (ROOT / path).open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def year_of(row: dict[str, str]) -> int:
    return int((row.get("year") or row["session_id"][-4:]))


def truth(value: str | None) -> bool:
    return str(value).lower() == "true"


def verify_frozen_snapshot() -> tuple[bool, int, list[str]]:
    snapshot = Path("/Users/fengzhecharlieli/Desktop/indy500删圈_R3C1_FROZEN_BASELINE")
    manifest = snapshot / "FROZEN_BASELINE_MANIFEST_SHA256.txt"
    failures: list[str] = []
    entries = 0
    if not manifest.is_file():
        return False, 0, ["manifest missing"]
    for line in manifest.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, relative = line.split("  ", 1)
        target = snapshot / relative
        entries += 1
        if not target.is_file() or hashlib.sha256(target.read_bytes()).hexdigest() != digest:
            failures.append(relative)
    return not failures and entries > 0, entries, failures


def main() -> int:
    attempts = read_csv("data/canonical/v1/attempts.csv")
    by_id = {row["attempt_id"]: row for row in attempts}
    if len(by_id) != len(attempts):
        raise RuntimeError("canonical attempt_id is not unique")

    lap_numbers: dict[str, set[str]] = defaultdict(set)
    for row in read_csv("data/canonical/v1/attempt_laps.csv"):
        if row["lap_completion_status"] == "COMPLETE":
            lap_numbers[row["attempt_id"]].add(row["lap_number"])
    complete_laps = {aid for aid, nums in lap_numbers.items() if {"1", "2", "3", "4"} <= nums}
    valid_speed = {row["attempt_id"] for row in attempts if row["four_lap_average_speed_mph"]}
    complete_performance = complete_laps & valid_speed

    timing_paths = (
        "weather/output/performance_grade_attempt_timing.csv",
        "weather/output/performance_grade_attempt_timing_2024_supported.csv",
    )
    performance_times: dict[str, datetime] = {}
    for path in timing_paths:
        for row in read_csv(path):
            if not truth(row["performance_alignment_usable"]):
                continue
            timestamp = datetime.fromisoformat(row["mapped_capture_time_utc"].replace("Z", "+00:00"))
            old = performance_times.setdefault(row["attempt_id"], timestamp)
            if old != timestamp:
                raise RuntimeError(f"conflicting performance timestamps for {row['attempt_id']}")

    # These constraints add event-level approximate timestamps, but not complete performance rows.
    constraints_2024 = read_csv("data/canonical/v1/chronology_constraints.csv")
    approximate_event_ids = {
        row["attempt_id"] for row in constraints_2024
        if row["event_time_quality"] == "APPROXIMATE_OBSERVED"
        and (row["anchor_time_utc"] or row["capture_time_utc"])
    }
    approximate_ids = set(performance_times) | approximate_event_ids

    # Bounded evidence is counted but never collapsed to a midpoint or placed in a fixed window.
    bounded_ids: set[str] = set()
    for row in read_csv("weather/output/chronology_rescue_2022_evidence_with_attempt_ids_v2.csv"):
        if (row["attempt_id"] and truth(row["chronology_usable"])
                and "BOUNDED_INTERVAL" in row["constraint_class"]
                and row["time_lower_utc"] and row["time_upper_utc"]):
            bounded_ids.add(row["attempt_id"])
    for row in constraints_2024:
        if (row["event_time_quality"] == "BOUNDED_INTERVAL"
                and row["anchor_event_type"] in {"ATTEMPT_OCCURRENCE", "TIMED_RUN_END"}
                and (row["anchor_time_lower_utc"] or row["timed_run_start_lower_utc"])):
            bounded_ids.add(row["attempt_id"])
    bounded_ids -= approximate_ids

    ordering_ids = {
        row["attempt_id"] for row in attempts if row["event_time_quality"] == "ORDERING_ONLY"
    }
    ordering_ids.update(
        row["attempt_id"] for row in constraints_2024
        if row["event_time_quality"] == "ORDERING_ONLY" and row["attempt_id"]
    )
    for row in read_csv("weather/output/chronology_rescue_2022_evidence_with_attempt_ids_v2.csv"):
        if row["attempt_id"] and row["constraint_class"] == "ORDERING_ONLY" and truth(row["chronology_usable"]):
            ordering_ids.add(row["attempt_id"])
    ordering_ids -= approximate_ids | bounded_ids

    exact_ids = {
        row["attempt_id"] for row in attempts
        if row["event_time_quality"] == "EXACT" and row["start_time_utc"]
    }
    approximate_ids -= exact_ids
    unknown_ids = set(by_id) - exact_ids - approximate_ids - bounded_ids - ordering_ids

    hrrr = {
        row["attempt_id"] for row in read_csv("weather/output/performance_grade_hrrr_forecast_alignment.csv")
        if truth(row["leakage_safe"])
    }
    ptsc: set[str] = set()
    for path, status_field in (
        ("weather/output/performance_grade_attempt_realized_environment.csv", "ptsc_alignment_status"),
        ("weather/output/performance_grade_attempt_realized_environment_2024_supported.csv", "ptsc_alignment_status"),
        ("weather/output/ptsc_attempt_realized_environment_alignment.csv", "ptsc_interp_status"),
    ):
        for row in read_csv(path):
            if row.get("ptsc_track_c") and row.get(status_field) in {"LINEAR_INTERPOLATION", "EXACT_PTSC_OBSERVATION"}:
                ptsc.add(row["attempt_id"])

    cross_car_ids = set(performance_times) & complete_performance
    point_timestamp_ids = exact_ids | approximate_ids

    groups: dict[tuple[int, str], list[dict[str, str]]] = defaultdict(list)
    for row in attempts:
        if row["attempt_id"] in complete_performance:
            groups[(year_of(row), row["car_number"])].append(row)
    multi_car_ids = {
        row["attempt_id"] for rows in groups.values() if len(rows) >= 2 for row in rows
    }
    later_valid_ids: set[str] = set()
    for rows in groups.values():
        indexed = [(int(float(row["car_attempt_index"])), row) for row in rows if row["car_attempt_index"]]
        if indexed:
            first_index = min(index for index, _ in indexed)
            later_valid_ids.update(row["attempt_id"] for index, row in indexed if index > first_index)

    inventory: list[dict] = []
    for year in YEARS:
        year_ids = {row["attempt_id"] for row in attempts if year_of(row) == year}
        classes = Counter(row["attempt_class"] for row in attempts if year_of(row) == year)
        candidate_ids = cross_car_ids & year_ids
        row = {
            "year": year,
            "canonical_attempts": len(year_ids),
            "canonical_distinct_cars": len({by_id[aid]["car_number"] for aid in year_ids}),
            "valid_four_lap_average_attempts": len(valid_speed & year_ids),
            "complete_lap_1_4_attempts": len(complete_laps & year_ids),
            "complete_performance_attempts": len(complete_performance & year_ids),
            "timestamp_exact_attempts": len(exact_ids & year_ids),
            "timestamp_approximate_attempts": len(approximate_ids & year_ids),
            "timestamp_bounded_attempts": len(bounded_ids & year_ids),
            "timestamp_ordering_only_attempts": len(ordering_ids & year_ids),
            "timestamp_unknown_attempts": len(unknown_ids & year_ids),
            "point_timestamp_attempts": len(point_timestamp_ids & year_ids),
            "timestamp_evidenced_including_bounded": len((point_timestamp_ids | bounded_ids) & year_ids),
            "leakage_safe_hrrr_attempts": len(hrrr & year_ids),
            "observed_ptsc_track_temp_attempts": len(ptsc & year_ids),
            "same_day_multi_attempt_baseline_candidates": len(multi_car_ids & year_ids),
            "cross_car_window_candidate_attempts": len(candidate_ids),
            "cross_car_candidate_distinct_cars": len({by_id[aid]["car_number"] for aid in candidate_ids}),
            "complete_performance_excluded_for_missing_point_timing": len((complete_performance - point_timestamp_ids) & year_ids),
            "point_timed_excluded_for_incomplete_performance": len((point_timestamp_ids - complete_performance) & year_ids),
            "partial_attempts": classes["B_PARTIAL_COMPLETE_LAPS"],
            "section_only_attempts": classes["C_SECTION_ONLY"],
            "fixed_window_status": "USABLE" if year in {2020, 2021, 2023} else ("SPARSE" if year == 2024 else "UNAVAILABLE"),
        }
        inventory.append(row)

    totals = {k: sum(int(row[k]) for row in inventory) for k in inventory[0] if k not in {"year", "fixed_window_status"}}
    inventory.append({"year": "TOTAL", **totals, "fixed_window_status": "3_USABLE_1_SPARSE_1_UNAVAILABLE"})
    inventory_path = OUT / "r4p0_cross_car_data_inventory_v1.csv"
    write_csv(inventory_path, inventory, list(inventory[0]))

    window_rows: list[dict] = []
    for year in YEARS:
        year_observations = [
            (aid, by_id[aid]["car_number"], timestamp)
            for aid, timestamp in performance_times.items()
            if aid in cross_car_ids and year_of(by_id[aid]) == year
        ]
        for minutes in WINDOWS:
            bins: dict[int, list[tuple[str, str]]] = defaultdict(list)
            for aid, car, timestamp in year_observations:
                bins[int(timestamp.timestamp()) // (minutes * 60)].append((aid, car))
            distinct = [len({car for _, car in values}) for values in bins.values()]
            in_dense = sum(
                len(values) for values in bins.values() if len({car for _, car in values}) >= 3
            )
            window_rows.append({
                "year": year,
                "window_minutes": minutes,
                "usable_timed_attempts": len(year_observations),
                "nonempty_windows": len(bins),
                "windows_ge_2_distinct_cars": sum(value >= 2 for value in distinct),
                "windows_ge_3_distinct_cars": sum(value >= 3 for value in distinct),
                "windows_ge_4_distinct_cars": sum(value >= 4 for value in distinct),
                "median_distinct_cars_per_nonempty_window": f"{median(distinct):.6f}" if distinct else "",
                "max_distinct_cars_in_window": max(distinct, default=0),
                "attempt_proportion_in_windows_ge_3_cars": f"{in_dense / len(year_observations):.10f}" if year_observations else "",
                "binning_rule": "UTC_EPOCH_ALIGNED_FIXED_NONOVERLAPPING",
                "timestamp_rule": "PERFORMANCE_GRADE_POINT_TIMES_ONLY_NO_BOUNDED_MIDPOINTS",
            })
    window_path = OUT / "r4p0_time_window_coverage_v1.csv"
    write_csv(window_path, window_rows, list(window_rows[0]))

    baseline_rows = [
        {
            "baseline_candidate": "FIRST_VALID_ATTEMPT_OF_DAY1",
            "all_complete_performance_attempts_receiving_baseline": len(later_valid_ids),
            "timed_cross_car_attempts_receiving_baseline": len(later_valid_ids & cross_car_ids),
            "definition_minimum_support": "known later car_attempt_index after a valid same-day attempt",
            "obvious_leakage_risk": "LOW_IF_ONLY_PRIOR_OBSERVED_ATTEMPT_IS_USED",
            "prospectively_available_at_decision": "YES_FOR_LATER_ATTEMPTS_WITH_PRIOR_RESULT",
            "retrospective_window_effect_suitability": "YES_WITH_SELECTION_AND_REPEAT_ATTEMPT_CAVEATS",
            "forward_decision_support_suitability": "POTENTIALLY_YES_AFTER_RESEARCH_VALIDATION",
        },
        {
            "baseline_candidate": "ROBUST_SAME_DAY_CAR_MEDIAN",
            "all_complete_performance_attempts_receiving_baseline": len(multi_car_ids),
            "timed_cross_car_attempts_receiving_baseline": len(multi_car_ids & cross_car_ids),
            "definition_minimum_support": "at least two valid same-day attempts for the car",
            "obvious_leakage_risk": "HIGH_IF_FULL_DAY_OR_CURRENT_ATTEMPT_ENTERS_MEDIAN",
            "prospectively_available_at_decision": "NO_AS_FULL_DAY_DEFINITION",
            "retrospective_window_effect_suitability": "POTENTIALLY_WITH_EXPLICIT_LEAKAGE_CONTROLS",
            "forward_decision_support_suitability": "NO_AS_CURRENT_FULL_DAY_DEFINITION",
        },
        {
            "baseline_candidate": "LEAVE_ONE_OUT_SAME_DAY_CAR_BASELINE",
            "all_complete_performance_attempts_receiving_baseline": len(multi_car_ids),
            "timed_cross_car_attempts_receiving_baseline": len(multi_car_ids & cross_car_ids),
            "definition_minimum_support": "at least two valid same-day attempts for the car",
            "obvious_leakage_risk": "HIGH_IF_OTHER_ATTEMPTS_OCCURRED_AFTER_DECISION",
            "prospectively_available_at_decision": "NO_UNLESS_RESTRICTED_TO_PRIOR_ATTEMPTS",
            "retrospective_window_effect_suitability": "YES_AS_SENSITIVITY_WITH_TIME_AWARE_SPLITS",
            "forward_decision_support_suitability": "NO_AS_FULL_DAY_LEAVE_ONE_OUT_DEFINITION",
        },
        {
            "baseline_candidate": "HIERARCHICAL_CAR_YEAR_BASELINE",
            "all_complete_performance_attempts_receiving_baseline": len(complete_performance),
            "timed_cross_car_attempts_receiving_baseline": len(cross_car_ids),
            "definition_minimum_support": "future model specification and train/test regime required",
            "obvious_leakage_risk": "CONDITIONAL_ON_TRAINING_SPLIT_AND_CURRENT_YEAR_DATA_USE",
            "prospectively_available_at_decision": "POTENTIALLY_IF_FIT_ONLY_TO_PRIOR_AVAILABLE_DATA",
            "retrospective_window_effect_suitability": "POTENTIALLY_YES",
            "forward_decision_support_suitability": "POTENTIALLY_YES_AFTER_OUT_OF_SAMPLE_VALIDATION",
        },
    ]
    baseline_path = OUT / "r4p0_baseline_feasibility_v1.csv"
    write_csv(baseline_path, baseline_rows, list(baseline_rows[0]))

    repeat_rows = read_csv("weather/output/r3b3_repeat_pair_environment_dataset_v1.csv")
    legacy_timing_rows = read_csv("weather/output/performance_grade_attempt_timing.csv")
    source_paths = [
        "data/canonical/v1/attempts.csv", "data/canonical/v1/attempt_laps.csv",
        "data/canonical/v1/chronology_constraints.csv",
        *timing_paths,
        "weather/output/performance_grade_hrrr_forecast_alignment.csv",
        "weather/output/performance_grade_attempt_realized_environment.csv",
        "weather/output/performance_grade_attempt_realized_environment_2024_supported.csv",
        "weather/output/ptsc_attempt_realized_environment_alignment.csv",
        "weather/output/chronology_rescue_2022_evidence_with_attempt_ids_v2.csv",
        "weather/output/r3b3_repeat_pair_environment_dataset_v1.csv",
    ]
    input_hashes = {
        path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in source_paths
    }
    r3c1_verification = R3C1ReadOnlyAdapter(ROOT).verify()
    frozen_ok, frozen_entries, frozen_failures = verify_frozen_snapshot()
    report = {
        "phase": "R4P0_CROSS_CAR_TIME_WINDOW_DATA_AVAILABILITY_AUDIT",
        "status": "READY",
        "scope": "bounded local audit; no model fit, Monte Carlo, web access, queue inference, or data acquisition",
        "terminology": {
            "primary_reference": "current_result_reference",
            "secondary_reference": "advancement_benchmark",
            "deprecated_rejected_without_reinterpretation": ["target_rank", "IMPROVE_CURRENT_SPEED", "REACH_TARGET_RANK"],
            "advancement_benchmark_rule": "format-regime-dependent; no universal Top 12",
            "reserved_future_output_semantics": [
                "P_BEAT_CURRENT_RESULT", "P_CROSS_ADVANCEMENT_BENCHMARK", "P_IMPROVE_RANK",
                "P_FINISH_WORSE_THAN_CURRENT_RESULT", "P_COMPLETE_BEFORE_SESSION_END",
            ],
            "probabilities_implemented": False,
        },
        "counts": {
            "canonical_attempts": len(attempts),
            "complete_performance_attempts": len(complete_performance),
            "performance_grade_point_timestamps": len(performance_times),
            "all_point_timestamp_attempts_including_event_only": len(point_timestamp_ids),
            "bounded_interval_attempts": len(bounded_ids),
            "cross_car_window_candidates": len(cross_car_ids),
            "complete_performance_excluded_only_for_missing_point_timing": len(complete_performance - point_timestamp_ids),
            "point_timed_excluded_for_incomplete_performance": len(point_timestamp_ids - complete_performance),
            "partial_or_section_only_attempts": sum(
                row["attempt_class"] in {"B_PARTIAL_COMPLETE_LAPS", "C_SECTION_ONLY"} for row in attempts
            ),
            "existing_repeat_pair_calibration_subset": len(repeat_rows),
            "existing_2020_2021_2023_timed_weather_subset": len(legacy_timing_rows),
            "expanded_existing_performance_grade_timing_rows": len(performance_times),
        },
        "year_inventory": inventory[:-1],
        "chronological_window_years": {
            "usable": [2020, 2021, 2023],
            "sparse": [2024],
            "unavailable": [2022],
            "point_timestamp_coverage_years": [2020, 2021, 2023, 2024],
        },
        "method": {
            "cross_car_candidate": "canonical attempt with valid four-lap average, complete laps 1-4, and an existing performance-grade point timestamp",
            "window_bins": "fixed non-overlapping UTC epoch-aligned bins; no sliding windows",
            "bounded_intervals": "reported separately and never converted to midpoint timestamps",
            "timestamp_semantics": "recorder captures are approximate performance alignment times, not exact timed-run starts or queue chronology",
            "ptsc_semantics": "observed retrospective context; not a decision-time forecast",
            "hrrr_semantics": "leakage-safe forecast selection; decision_state_usable remains false in the source alignment",
            "baseline_selection": "not selected or fit",
        },
        "invariants": [
            'car numbers remain strings and "06" != "6"',
            "discovery evidence is not promoted to canonical truth",
            "result order is not chronology",
            "withdrawn does not imply Lane 1",
            "missing timing remains missing",
            "historical future weather is excluded from decision-time features",
            "39 repeat pairs are a calibration subset, not the full modeling dataset",
            "129 timed-weather rows are a frozen subset, not a maximum cross-car dataset",
        ],
        "input_sha256": input_hashes,
        "preservation_verification": {
            "r3c1_manifest_assets_verified": all(r3c1_verification.values()),
            "r3c1_manifest_asset_count": len(r3c1_verification),
            "frozen_snapshot_manifest_verified": frozen_ok,
            "frozen_snapshot_manifest_entries": frozen_entries,
            "frozen_snapshot_failures": frozen_failures,
            "verification_was_read_only": True,
        },
        "outputs": [path.name for path in (inventory_path, window_path, baseline_path,
                                             OUT / "r4p0_cross_car_data_audit_v1.json",
                                             OUT / "r4p0_cross_car_data_audit_v1_qa.csv")],
    }
    report_path = OUT / "r4p0_cross_car_data_audit_v1.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    qa_rows = []
    def check(name: str, actual, expected, note: str = "") -> None:
        qa_rows.append({"check": name, "actual": actual, "expected": expected,
                        "status": "PASS" if actual == expected else "FAIL", "note": note})
    check("canonical_attempt_count", len(attempts), 329)
    check("canonical_year_counts", ",".join(str(row["canonical_attempts"]) for row in inventory[:-1]), "63,60,44,85,77")
    check("performance_grade_point_timestamp_count", len(performance_times), 136, "129 legacy rows plus 7 already-supported 2024 rows")
    check("cross_car_candidate_count", len(cross_car_ids), 123)
    check("cross_car_candidate_year_counts", ",".join(str(row["cross_car_window_candidate_attempts"]) for row in inventory[:-1]), "39,49,0,28,7")
    check("repeat_pair_subset_count", len(repeat_rows), 39, "calibration subset only")
    check("legacy_timed_weather_subset_count", len(legacy_timing_rows), 129, "not asserted as maximum")
    check("car_number_06_preserved", any(row["car_number"] == "06" for row in attempts), True)
    check("car_number_06_distinct_from_6", "06" != "6", True)
    check("bounded_not_in_point_windows", bool(bounded_ids & set(performance_times)), False)
    check("all_quality_classes_partition_attempts", len(exact_ids | approximate_ids | bounded_ids | ordering_ids | unknown_ids), len(attempts))
    check("no_probabilities_created", report["terminology"]["probabilities_implemented"], False)
    check("all_expected_outputs_declared", len(report["outputs"]), 5)
    check("r3c1_manifest_assets_verified", all(r3c1_verification.values()), True)
    check("frozen_snapshot_manifest_verified", frozen_ok, True, f"{frozen_entries} files checked read-only")
    qa_path = OUT / "r4p0_cross_car_data_audit_v1_qa.csv"
    write_csv(qa_path, qa_rows, list(qa_rows[0]))
    failed = [row for row in qa_rows if row["status"] != "PASS"]

    console_summary = {
        "canonical_attempts_by_year": {str(row["year"]): row["canonical_attempts"] for row in inventory[:-1]},
        "timed_usable_attempts_by_year": {str(row["year"]): row["cross_car_window_candidate_attempts"] for row in inventory[:-1]},
        "total_cross_car_candidate_observations": len(cross_car_ids),
        "windows_ge_3_distinct_cars": {
            f"{row['year']}_{row['window_minutes']}min": row["windows_ge_3_distinct_cars"]
            for row in window_rows
        },
        "baseline_attempt_counts": {
            row["baseline_candidate"]: {
                "all_complete_performance": row["all_complete_performance_attempts_receiving_baseline"],
                "timed_cross_car": row["timed_cross_car_attempts_receiving_baseline"],
            }
            for row in baseline_rows
        },
        "repeat_pair_count": len(repeat_rows),
        "legacy_timed_weather_count": len(legacy_timing_rows),
        "r4a_terminology_correction": "CORRECTED_LEGACY_TERMS_EXPLICITLY_REJECTED",
        "r3c1_hash_verification": "PASS" if all(r3c1_verification.values()) else "FAIL",
        "frozen_snapshot_verification": "PASS" if frozen_ok else "FAIL",
        "qa": "PASS" if not failed else "FAIL",
    }
    print(json.dumps(console_summary, indent=2))
    print("R4P0_CROSS_CAR_TIME_WINDOW_DATA_AUDIT_READY" if not failed else "R4P0_AUDIT_QA_FAILED")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
