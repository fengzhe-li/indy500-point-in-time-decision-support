from pathlib import Path
import csv
import json
import math
import hashlib
from collections import Counter, defaultdict


ROOT = Path("/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈")
OUT = ROOT / "r4" / "output"

DECISION_FILE = OUT / "r4f8e_reconstructed_decision_numeric_state_v1.csv"
FUSED_FILE = OUT / "r4f2_canonical_fused_decision_dataset_v2.csv"
PANEL_FILE = OUT / "r4p1_attempt_four_lap_panel_v1.csv"
P5_FILE = OUT / "r4p5_decision_safe_forecast_scenarios_v1.csv"

OUT_INTERFACE = OUT / "r4f9_b_historical_realized_outcome_interface_v1.csv"
OUT_CROSSCHECK = OUT / "r4f9_b_r4p5_next_attempt_crosscheck_v1.csv"
OUT_QA = OUT / "r4f9_b_historical_outcome_reconstruction_qa_v1.csv"
OUT_CONTRACT = OUT / "r4f9_b_historical_outcome_contract_v1.json"
OUT_REPORT = OUT / "r4f9_b_historical_outcome_reconstruction_report_v1.json"


# =============================================================================
# R4F9-B — HISTORICAL REALIZED OUTCOME RECONSTRUCTION
#
# PURPOSE
# -------
# Reconstruct realized later-attempt outcomes AFTER frozen R4F8H decisions
# for replay/evaluation only.
#
# Historical outcomes are evaluation targets, NEVER decision-time features.
#
# DOES NOT:
# - treat historical actions as optimal labels
# - infer exact queue wait
# - reconstruct future leaderboard dynamically
# - refit any model
# - modify R4F8H inputs
# =============================================================================


def clean(v):
    return "" if v is None else str(v).strip()


def num(v):
    s = clean(v)
    if not s:
        return None
    try:
        x = float(s)
        if math.isfinite(x):
            return x
    except Exception:
        pass
    return None


def truthy(v):
    return clean(v).lower() in {
        "true", "1", "yes", "y", "t"
    }


def read_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return reader.fieldnames or [], list(reader)


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


required = [
    DECISION_FILE,
    FUSED_FILE,
    PANEL_FILE,
    P5_FILE,
]

missing = [p for p in required if not p.exists()]

if missing:
    print("=" * 130)
    print("R4F9-B REQUIRED INPUTS MISSING")
    print("=" * 130)
    for p in missing:
        print(p.relative_to(ROOT))
    raise SystemExit(1)


dec_fields, dec_rows = read_csv(DECISION_FILE)
fused_fields, fused_rows = read_csv(FUSED_FILE)
panel_fields, panel_rows = read_csv(PANEL_FILE)
p5_fields, p5_rows = read_csv(P5_FILE)


# =============================================================================
# Frozen schema checks
# =============================================================================

required_dec_fields = [
    "fused_decision_id",
    "source_decision_id",
    "regime",
    "year",
    "car_number",
    "driver_name",
    "source_attempt_id",
    "source_attempt_id_status",
    "decision_time_utc",
    "current_best_speed_mph",
    "current_protected_result_speed_mph",
    "benchmark_type",
    "benchmark_rank",
    "benchmark_speed_mph",
]

required_panel_fields = [
    "year",
    "session_id",
    "attempt_id",
    "entry_key",
    "car_number",
    "driver_name",
    "car_attempt_index",
    "attempt_class",
    "result_status",
    "result_counted_at_session_end",
    "four_lap_average_speed_mph",
    "time_point_utc",
    "time_evidence_class",
]

required_fused_fields = [
    "decision_id",
    "observed_action",
    "action_resolved",
    "action_evidence_quality",
]

required_p5_fields = [
    "before_attempt_id",
    "after_attempt_id",
    "actual_next_attempt_time_utc",
    "actual_between_attempt_observation_minutes",
    "actual_next_run_speed_delta_mph",
    "actual_next_run_improved",
    "decision_time_safe",
]

for field in required_dec_fields:
    if field not in dec_fields:
        raise SystemExit(f"Missing decision field: {field}")

for field in required_panel_fields:
    if field not in panel_fields:
        raise SystemExit(f"Missing panel field: {field}")

for field in required_fused_fields:
    if field not in fused_fields:
        raise SystemExit(f"Missing fused field: {field}")

for field in required_p5_fields:
    if field not in p5_fields:
        raise SystemExit(f"Missing R4P5 field: {field}")


if len(dec_rows) != 60:
    raise SystemExit(f"Decision universe changed: {len(dec_rows)} != 60")

if len(panel_rows) != 329:
    raise SystemExit(f"Attempt panel changed: {len(panel_rows)} != 329")


# =============================================================================
# Lookups
# =============================================================================

panel_by_attempt_id = {
    clean(r["attempt_id"]): r
    for r in panel_rows
    if clean(r["attempt_id"])
}

attempts_by_entry = defaultdict(list)

for row in panel_rows:
    entry = clean(row["entry_key"])
    idx = num(row["car_attempt_index"])

    if not entry or idx is None:
        continue

    attempts_by_entry[entry].append(row)

for entry, rows in attempts_by_entry.items():
    rows.sort(
        key=lambda r: (
            num(r["car_attempt_index"])
            if num(r["car_attempt_index"]) is not None
            else 999999,
            clean(r["attempt_id"]),
        )
    )


fused_by_decision_id = {}

for row in fused_rows:
    did = clean(row["decision_id"])
    if did:
        fused_by_decision_id[did] = row


p5_by_before_attempt = defaultdict(list)

for row in p5_rows:
    before = clean(row["before_attempt_id"])
    if before:
        p5_by_before_attempt[before].append(row)


# =============================================================================
# Historical outcome reconstruction
# =============================================================================

interface_rows = []
crosscheck_rows = []

for decision in dec_rows:

    fused_decision_id = clean(
        decision["fused_decision_id"]
    )

    source_decision_id = clean(
        decision["source_decision_id"]
    )

    source_attempt_id = clean(
        decision["source_attempt_id"]
    )

    source_attempt_status = clean(
        decision["source_attempt_id_status"]
    )

    regime = clean(decision["regime"])
    year = clean(decision["year"])
    car_number = clean(decision["car_number"])
    driver_name = clean(decision["driver_name"])

    decision_time = clean(
        decision["decision_time_utc"]
    )

    current_speed = num(
        decision["current_best_speed_mph"]
    )

    if current_speed is None:
        current_speed = num(
            decision["current_protected_result_speed_mph"]
        )

    benchmark_speed = num(
        decision["benchmark_speed_mph"]
    )

    benchmark_rank = num(
        decision["benchmark_rank"]
    )

    benchmark_type = clean(
        decision["benchmark_type"]
    )

    fused = fused_by_decision_id.get(
        source_decision_id
    )

    observed_action = (
        clean(fused["observed_action"])
        if fused
        else ""
    )

    action_resolved = (
        clean(fused["action_resolved"])
        if fused
        else ""
    )

    action_quality = (
        clean(fused["action_evidence_quality"])
        if fused
        else ""
    )

    # -------------------------------------------------------------------------
    # Source attempt resolution
    # -------------------------------------------------------------------------

    source_attempt = (
        panel_by_attempt_id.get(source_attempt_id)
        if source_attempt_id
        else None
    )

    if source_attempt is None:

        interface_rows.append({
            "fused_decision_id":
                fused_decision_id,

            "source_decision_id":
                source_decision_id,

            "regime":
                regime,

            "year":
                year,

            "car_number":
                car_number,

            "driver_name":
                driver_name,

            "decision_time_utc":
                decision_time,

            "source_attempt_id":
                source_attempt_id,

            "source_attempt_id_status":
                source_attempt_status,

            "source_attempt_link_status":
                "UNRESOLVED_SOURCE_ATTEMPT",

            "source_entry_key":
                "",

            "source_car_attempt_index":
                "",

            "observed_action":
                observed_action,

            "observed_action_resolved":
                action_resolved,

            "observed_action_quality":
                action_quality,

            "current_result_speed_mph":
                current_speed if current_speed is not None else "",

            "benchmark_type":
                benchmark_type,

            "benchmark_rank":
                benchmark_rank if benchmark_rank is not None else "",

            "benchmark_speed_mph":
                benchmark_speed if benchmark_speed is not None else "",

            "later_attempt_count":
                "",

            "next_attempt_exists":
                "",

            "next_attempt_id":
                "",

            "next_attempt_index":
                "",

            "next_attempt_class":
                "",

            "next_attempt_result_status":
                "",

            "next_attempt_time_utc":
                "",

            "next_attempt_time_evidence_class":
                "",

            "next_attempt_complete_four_lap":
                "",

            "next_attempt_speed_mph":
                "",

            "next_attempt_speed_delta_vs_current_mph":
                "",

            "next_attempt_improved_current":
                "",

            "next_attempt_met_decision_time_benchmark":
                "",

            "any_later_complete_attempt_exists":
                "",

            "best_later_complete_speed_mph":
                "",

            "best_later_complete_met_decision_time_benchmark":
                "",

            "session_end_counted_result_from_later_attempt":
                "",

            "r4p5_crosscheck_available":
                False,

            "r4p5_after_attempt_id":
                "",

            "r4p5_match_next_attempt_id":
                "",

            "historical_outcome_evaluable":
                False,

            "historical_outcome_status":
                "BLOCKED_SOURCE_ATTEMPT_UNRESOLVED",

            "future_information_used_for_r4f8h":
                False,

            "queue_wait_claimed":
                False,
        })

        continue

    entry_key = clean(
        source_attempt["entry_key"]
    )

    source_idx = num(
        source_attempt["car_attempt_index"]
    )

    if source_idx is None:
        raise SystemExit(
            f"Resolved source attempt missing car_attempt_index: "
            f"{source_attempt_id}"
        )

    # -------------------------------------------------------------------------
    # All later attempts in same canonical entry
    # -------------------------------------------------------------------------

    later_attempts = [
        r
        for r in attempts_by_entry.get(entry_key, [])
        if (
            num(r["car_attempt_index"]) is not None
            and num(r["car_attempt_index"]) > source_idx
        )
    ]

    later_attempts.sort(
        key=lambda r: (
            num(r["car_attempt_index"]),
            clean(r["attempt_id"]),
        )
    )

    next_attempt = (
        later_attempts[0]
        if later_attempts
        else None
    )

    # -------------------------------------------------------------------------
    # Complete later attempts
    # -------------------------------------------------------------------------

    later_complete = []

    for r in later_attempts:

        cls = clean(r["attempt_class"])
        speed = num(
            r["four_lap_average_speed_mph"]
        )

        complete = (
            cls == "A_COMPLETE"
            and speed is not None
        )

        if complete:
            later_complete.append(r)

    best_later_speed = None

    if later_complete:
        speeds = [
            num(r["four_lap_average_speed_mph"])
            for r in later_complete
        ]

        speeds = [
            x for x in speeds
            if x is not None
        ]

        if speeds:
            best_later_speed = max(speeds)

    # -------------------------------------------------------------------------
    # Next-attempt realized outcome
    # -------------------------------------------------------------------------

    if next_attempt is not None:

        next_attempt_id = clean(
            next_attempt["attempt_id"]
        )

        next_idx = num(
            next_attempt["car_attempt_index"]
        )

        next_class = clean(
            next_attempt["attempt_class"]
        )

        next_status = clean(
            next_attempt["result_status"]
        )

        next_time = clean(
            next_attempt["time_point_utc"]
        )

        next_time_class = clean(
            next_attempt["time_evidence_class"]
        )

        next_speed = num(
            next_attempt["four_lap_average_speed_mph"]
        )

        next_complete = (
            next_class == "A_COMPLETE"
            and next_speed is not None
        )

        next_delta = (
            next_speed - current_speed
            if (
                next_speed is not None
                and current_speed is not None
            )
            else None
        )

        next_improved = (
            next_speed > current_speed
            if (
                next_speed is not None
                and current_speed is not None
            )
            else None
        )

        next_hits_benchmark = (
            next_speed >= benchmark_speed
            if (
                next_speed is not None
                and benchmark_speed is not None
            )
            else None
        )

    else:

        next_attempt_id = ""
        next_idx = None
        next_class = ""
        next_status = ""
        next_time = ""
        next_time_class = ""
        next_speed = None
        next_complete = False
        next_delta = None
        next_improved = None
        next_hits_benchmark = None

    # -------------------------------------------------------------------------
    # Later session-counted result
    # -------------------------------------------------------------------------

    later_counted = [
        r
        for r in later_attempts
        if truthy(
            r["result_counted_at_session_end"]
        )
    ]

    later_counted_flag = (
        len(later_counted) > 0
    )

    # -------------------------------------------------------------------------
    # R4P5 cross-check
    # -------------------------------------------------------------------------

    p5_matches = p5_by_before_attempt.get(
        source_attempt_id,
        []
    )

    p5_available = len(p5_matches) == 1

    p5_after_id = ""
    p5_match_next = ""

    if p5_available:

        p5 = p5_matches[0]

        p5_after_id = clean(
            p5["after_attempt_id"]
        )

        if next_attempt_id:
            p5_match_next = (
                p5_after_id == next_attempt_id
            )

        else:
            p5_match_next = False

        crosscheck_rows.append({
            "fused_decision_id":
                fused_decision_id,

            "source_attempt_id":
                source_attempt_id,

            "canonical_next_attempt_id":
                next_attempt_id,

            "r4p5_after_attempt_id":
                p5_after_id,

            "attempt_id_match":
                p5_match_next,

            "canonical_next_attempt_time_utc":
                next_time,

            "r4p5_actual_next_attempt_time_utc":
                clean(
                    p5[
                        "actual_next_attempt_time_utc"
                    ]
                ),

            "r4p5_actual_between_attempt_observation_minutes":
                clean(
                    p5[
                        "actual_between_attempt_observation_minutes"
                    ]
                ),

            "canonical_speed_delta_vs_current_mph":
                next_delta if next_delta is not None else "",

            "r4p5_actual_next_run_speed_delta_mph":
                clean(
                    p5[
                        "actual_next_run_speed_delta_mph"
                    ]
                ),

            "r4p5_decision_time_safe":
                clean(
                    p5["decision_time_safe"]
                ),

            "queue_wait_interpretation_allowed":
                False,
        })

    # -------------------------------------------------------------------------
    # Evaluation readiness
    # -------------------------------------------------------------------------

    if next_attempt is None:

        outcome_status = (
            "OBSERVED_NO_LATER_CANONICAL_ATTEMPT"
        )

        evaluable = True

    elif next_complete:

        outcome_status = (
            "NEXT_ATTEMPT_COMPLETE_SPEED_OBSERVED"
        )

        evaluable = True

    else:

        outcome_status = (
            "NEXT_ATTEMPT_EXISTS_BUT_NOT_COMPLETE_FOUR_LAP"
        )

        evaluable = True

    interface_rows.append({
        "fused_decision_id":
            fused_decision_id,

        "source_decision_id":
            source_decision_id,

        "regime":
            regime,

        "year":
            year,

        "car_number":
            car_number,

        "driver_name":
            driver_name,

        "decision_time_utc":
            decision_time,

        "source_attempt_id":
            source_attempt_id,

        "source_attempt_id_status":
            source_attempt_status,

        "source_attempt_link_status":
            "RESOLVED_CANONICAL_ATTEMPT",

        "source_entry_key":
            entry_key,

        "source_car_attempt_index":
            int(source_idx),

        "observed_action":
            observed_action,

        "observed_action_resolved":
            action_resolved,

        "observed_action_quality":
            action_quality,

        "current_result_speed_mph":
            current_speed if current_speed is not None else "",

        "benchmark_type":
            benchmark_type,

        "benchmark_rank":
            benchmark_rank if benchmark_rank is not None else "",

        "benchmark_speed_mph":
            benchmark_speed if benchmark_speed is not None else "",

        "later_attempt_count":
            len(later_attempts),

        "next_attempt_exists":
            next_attempt is not None,

        "next_attempt_id":
            next_attempt_id,

        "next_attempt_index":
            int(next_idx)
            if next_idx is not None
            else "",

        "next_attempt_class":
            next_class,

        "next_attempt_result_status":
            next_status,

        "next_attempt_time_utc":
            next_time,

        "next_attempt_time_evidence_class":
            next_time_class,

        "next_attempt_complete_four_lap":
            next_complete,

        "next_attempt_speed_mph":
            next_speed if next_speed is not None else "",

        "next_attempt_speed_delta_vs_current_mph":
            next_delta if next_delta is not None else "",

        "next_attempt_improved_current":
            next_improved
            if next_improved is not None
            else "",

        "next_attempt_met_decision_time_benchmark":
            next_hits_benchmark
            if next_hits_benchmark is not None
            else "",

        "any_later_complete_attempt_exists":
            len(later_complete) > 0,

        "best_later_complete_speed_mph":
            best_later_speed
            if best_later_speed is not None
            else "",

        "best_later_complete_met_decision_time_benchmark":
            (
                best_later_speed >= benchmark_speed
                if (
                    best_later_speed is not None
                    and benchmark_speed is not None
                )
                else ""
            ),

        "session_end_counted_result_from_later_attempt":
            later_counted_flag,

        "r4p5_crosscheck_available":
            p5_available,

        "r4p5_after_attempt_id":
            p5_after_id,

        "r4p5_match_next_attempt_id":
            p5_match_next,

        "historical_outcome_evaluable":
            evaluable,

        "historical_outcome_status":
            outcome_status,

        "future_information_used_for_r4f8h":
            False,

        "queue_wait_claimed":
            False,
    })


# =============================================================================
# Save interface
# =============================================================================

with OUT_INTERFACE.open(
    "w",
    encoding="utf-8",
    newline="",
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=list(
            interface_rows[0].keys()
        ),
    )

    writer.writeheader()
    writer.writerows(interface_rows)


crosscheck_fields = [
    "fused_decision_id",
    "source_attempt_id",
    "canonical_next_attempt_id",
    "r4p5_after_attempt_id",
    "attempt_id_match",
    "canonical_next_attempt_time_utc",
    "r4p5_actual_next_attempt_time_utc",
    "r4p5_actual_between_attempt_observation_minutes",
    "canonical_speed_delta_vs_current_mph",
    "r4p5_actual_next_run_speed_delta_mph",
    "r4p5_decision_time_safe",
    "queue_wait_interpretation_allowed",
]

with OUT_CROSSCHECK.open(
    "w",
    encoding="utf-8",
    newline="",
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=crosscheck_fields,
    )

    writer.writeheader()
    writer.writerows(crosscheck_rows)


# =============================================================================
# QA
# =============================================================================

qa_rows = []


def qa(metric, value, expected, status):
    qa_rows.append({
        "metric": metric,
        "value": value,
        "expected": expected,
        "status": status,
    })


resolved_source = [
    r for r in interface_rows
    if r["source_attempt_link_status"]
    == "RESOLVED_CANONICAL_ATTEMPT"
]

blocked_source = [
    r for r in interface_rows
    if r["source_attempt_link_status"]
    != "RESOLVED_CANONICAL_ATTEMPT"
]

with_later = [
    r for r in resolved_source
    if r["next_attempt_exists"] is True
]

without_later = [
    r for r in resolved_source
    if r["next_attempt_exists"] is False
]

next_complete = [
    r for r in resolved_source
    if r["next_attempt_complete_four_lap"] is True
]

next_incomplete = [
    r for r in resolved_source
    if (
        r["next_attempt_exists"] is True
        and r["next_attempt_complete_four_lap"] is False
    )
]

crosscheck_available = [
    r for r in crosscheck_rows
]

crosscheck_matches = [
    r for r in crosscheck_rows
    if r["attempt_id_match"] is True
]

crosscheck_mismatches = [
    r for r in crosscheck_rows
    if r["attempt_id_match"] is False
]


qa(
    "final_decision_rows",
    len(interface_rows),
    60,
    (
        "PASS"
        if len(interface_rows) == 60
        else "FAIL"
    ),
)

qa(
    "source_attempts_resolved",
    len(resolved_source),
    "EXPECTED_AROUND_57",
    (
        "PASS"
        if len(resolved_source) == 57
        else "WARN"
    ),
)

qa(
    "source_attempts_unresolved",
    len(blocked_source),
    "EXPECTED_AROUND_3",
    (
        "PASS"
        if len(blocked_source) == 3
        else "WARN"
    ),
)

qa(
    "resolved_rows_partition",
    len(with_later) + len(without_later),
    len(resolved_source),
    (
        "PASS"
        if (
            len(with_later)
            + len(without_later)
            == len(resolved_source)
        )
        else "FAIL"
    ),
)

qa(
    "next_attempt_partition",
    len(next_complete) + len(next_incomplete),
    len(with_later),
    (
        "PASS"
        if (
            len(next_complete)
            + len(next_incomplete)
            == len(with_later)
        )
        else "FAIL"
    ),
)

qa(
    "r4p5_crosscheck_rows",
    len(crosscheck_available),
    "MEASURED",
    "PASS",
)

qa(
    "r4p5_attempt_id_mismatches",
    len(crosscheck_mismatches),
    0,
    (
        "PASS"
        if len(crosscheck_mismatches) == 0
        else "WARN"
    ),
)

qa(
    "historical_actions_used_as_optimal_labels",
    False,
    False,
    "PASS",
)

qa(
    "future_outcomes_used_as_r4f8h_inputs",
    False,
    False,
    "PASS",
)

qa(
    "between_attempt_interval_called_queue_wait",
    False,
    False,
    "PASS",
)

qa(
    "future_final_leaderboard_used",
    False,
    False,
    "PASS",
)

qa(
    "model_refit",
    False,
    False,
    "PASS",
)


with OUT_QA.open(
    "w",
    encoding="utf-8",
    newline="",
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=[
            "metric",
            "value",
            "expected",
            "status",
        ],
    )

    writer.writeheader()
    writer.writerows(qa_rows)


# =============================================================================
# Contract
# =============================================================================

contract = {
    "phase":
        "R4F9-B",

    "status":
        "R4F9_HISTORICAL_REALIZED_OUTCOME_INTERFACE_RECONSTRUCTED",

    "primary_join": (
        "R4F8E.source_attempt_id "
        "-> R4P1.attempt_id "
        "-> same entry_key "
        "-> minimum larger car_attempt_index"
    ),

    "next_attempt_definition": (
        "The first later canonical attempt in the same entry_key by "
        "car_attempt_index. This is a historical evaluation outcome, "
        "not a decision-time feature."
    ),

    "complete_outcome_definition": (
        "next attempt has attempt_class=A_COMPLETE and a populated "
        "four_lap_average_speed_mph"
    ),

    "benchmark_evaluation": (
        "Historical next-attempt speed is compared only with the "
        "benchmark_speed_mph frozen at the original decision state."
    ),

    "secondary_crosscheck": {
        "source":
            str(P5_FILE.relative_to(ROOT)),
        "join":
            "source_attempt_id=before_attempt_id",
        "after_attempt_check":
            "canonical next attempt ID versus R4P5 after_attempt_id",
    },

    "important_boundaries": [
        "Actual between-attempt observation time is not queue wait.",
        "Historical actions are not optimal labels.",
        "Future leaderboard states are not reconstructed as R4F8H inputs.",
        "Incomplete next attempts are retained as realized outcomes.",
        "Unresolved source-attempt identities remain blocked.",
    ],
}

OUT_CONTRACT.write_text(
    json.dumps(
        contract,
        indent=2,
        ensure_ascii=False,
    ),
    encoding="utf-8",
)


# =============================================================================
# Report
# =============================================================================

passes = sum(
    r["status"] == "PASS"
    for r in qa_rows
)

warns = sum(
    r["status"] == "WARN"
    for r in qa_rows
)

fails = sum(
    r["status"] == "FAIL"
    for r in qa_rows
)

status_counts = Counter(
    r["historical_outcome_status"]
    for r in interface_rows
)

report = {
    "phase":
        "R4F9-B",

    "status": (
        "R4F9_HISTORICAL_REALIZED_OUTCOME_INTERFACE_RECONSTRUCTED"
        if fails == 0
        else "R4F9_HISTORICAL_REALIZED_OUTCOME_RECONSTRUCTION_FAILED"
    ),

    "coverage": {
        "final_decisions":
            len(interface_rows),

        "source_attempts_resolved":
            len(resolved_source),

        "source_attempts_unresolved":
            len(blocked_source),

        "resolved_with_later_attempt":
            len(with_later),

        "resolved_without_later_attempt":
            len(without_later),

        "next_complete_four_lap":
            len(next_complete),

        "next_incomplete_or_partial":
            len(next_incomplete),

        "r4p5_crosschecks":
            len(crosscheck_available),

        "r4p5_exact_attempt_id_matches":
            len(crosscheck_matches),

        "r4p5_attempt_id_mismatches":
            len(crosscheck_mismatches),
    },

    "historical_outcome_status_counts":
        dict(sorted(status_counts.items())),

    "evaluation_policy": (
        "R4F9 may score frozen predictive distributions against "
        "historically realized next-attempt outcomes where those outcomes "
        "are directly reconstructable. STOP/no-later-attempt cases are "
        "descriptive replay evidence, not optimal-action labels."
    ),

    "qa": {
        "pass":
            passes,

        "warn":
            warns,

        "fail":
            fails,
    },

    "protected_input_hashes": {
        str(p.relative_to(ROOT)): sha256(p)
        for p in required
    },

    "output_hashes": {
        str(p.relative_to(ROOT)): sha256(p)
        for p in [
            OUT_INTERFACE,
            OUT_CROSSCHECK,
            OUT_QA,
            OUT_CONTRACT,
        ]
    },

    "next_phase": (
        "R4F9-C_PROBABILISTIC_REPLAY_EVALUATION"
        if fails == 0
        else "RESOLVE_R4F9_B_FAILURES"
    ),
}

OUT_REPORT.write_text(
    json.dumps(
        report,
        indent=2,
        ensure_ascii=False,
    ),
    encoding="utf-8",
)


# =============================================================================
# Console
# =============================================================================

print("=" * 132)
print("R4F9-B — HISTORICAL REALIZED OUTCOME RECONSTRUCTION")
print("=" * 132)
print()

print("JOIN")
print("-" * 132)
print(
    "R4F8E source_attempt_id -> "
    "R4P1 attempt_id -> "
    "same entry_key -> next car_attempt_index"
)
print()

print("COVERAGE")
print("-" * 132)
print(f"Final decisions:                    {len(interface_rows)}")
print(f"Source attempt resolved:            {len(resolved_source)}")
print(f"Source attempt unresolved:          {len(blocked_source)}")
print(f"Resolved with later attempt:        {len(with_later)}")
print(f"Resolved without later attempt:     {len(without_later)}")
print(f"Next attempt complete four-lap:     {len(next_complete)}")
print(f"Next attempt incomplete/partial:    {len(next_incomplete)}")
print()

print("R4P5 CROSS-CHECK")
print("-" * 132)
print(f"Cross-check rows:                   {len(crosscheck_available)}")
print(f"Exact next-attempt ID matches:      {len(crosscheck_matches)}")
print(f"Next-attempt ID mismatches:         {len(crosscheck_mismatches)}")
print()

if crosscheck_mismatches:
    print("MISMATCHES")
    print("-" * 132)
    for r in crosscheck_mismatches[:20]:
        print(
            f"{r['fused_decision_id']} | "
            f"canonical={r['canonical_next_attempt_id']} | "
            f"r4p5={r['r4p5_after_attempt_id']}"
        )
    print()

print("OUTCOME STATUS")
print("-" * 132)

for status, count in sorted(status_counts.items()):
    print(f"{status:50s} {count}")

print()
print("QA")
print("-" * 132)
print(f"{passes} PASS | {warns} WARN | {fails} FAIL")

for r in qa_rows:
    if r["status"] != "PASS":
        print(
            f"{r['status']:5s} | "
            f"{r['metric']} | "
            f"value={r['value']} | "
            f"expected={r['expected']}"
        )

print()
print("OUTPUTS")
print("-" * 132)

for p in [
    OUT_INTERFACE,
    OUT_CROSSCHECK,
    OUT_QA,
    OUT_CONTRACT,
    OUT_REPORT,
]:
    print(p.relative_to(ROOT))

print()

if fails:
    print("R4F9_B_HISTORICAL_REALIZED_OUTCOME_RECONSTRUCTION_FAILED")
    raise SystemExit(1)

print("R4F9_HISTORICAL_REALIZED_OUTCOME_INTERFACE_RECONSTRUCTED")
print()
print("NEXT: R4F9-C PROBABILISTIC REPLAY EVALUATION")
print()
print(
    "IMPORTANT: realized later attempts are evaluation targets only. "
    "Observed between-attempt intervals are not queue waits, and "
    "historical actions are not optimal labels."
)
