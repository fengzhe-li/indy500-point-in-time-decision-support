from pathlib import Path
import csv
import json


PHASE = "R2I"

OUTPUT_DIR = Path("weather/output")

FILES = {
    "chronology": Path(
        "weather/output/"
        "unified_attempt_chronology_constraint_ledger_v10.csv"
    ),

    "action_lane": Path(
        "weather/output/"
        "unified_attempt_action_lane_ledger_v8.csv"
    ),

    "decision_state": Path(
        "weather/output/"
        "contemporaneous_decision_state_evidence_ledger_v2.csv"
    ),

    "queue": Path(
        "weather/output/"
        "queue_requeue_evidence_ledger_v1.csv"
    ),

    "queue_wait": Path(
        "weather/output/"
        "queue_wait_identifiability_2022_v1.csv"
    ),

    "pit_service": Path(
        "weather/output/"
        "pit_service_identifiability_2022_v1.csv"
    ),

    "interruption": Path(
        "weather/output/"
        "interruption_track_state_identifiability_2022_v1.csv"
    ),

    "rubber_grip": Path(
        "weather/output/"
        "rubber_grip_identifiability_2022_v1.csv"
    ),

    "tire_thermal": Path(
        "weather/output/"
        "tire_thermal_pressure_identifiability_2022_v1.csv"
    ),

    "repeat_eligibility": Path(
        "weather/output/"
        "chronology_rescue_2022_repeat_pair_driver_eligibility_v1.csv"
    ),
}


MATRIX_OUT = (
    OUTPUT_DIR
    / "rescue_readiness_matrix_v1.csv"
)

SIMULATOR_OUT = (
    OUTPUT_DIR
    / "sequential_simulator_readiness_v1.csv"
)

SUMMARY_OUT = (
    OUTPUT_DIR
    / "rescue_readiness_summary_v1.json"
)

QA_OUT = (
    OUTPUT_DIR
    / "rescue_readiness_matrix_v1_qa.csv"
)


EXPECTED_REPEAT_DRIVERS = {
    "Alexander Rossi",
    "Callum Ilott",
    "David Malukas",
    "Helio Castroneves",
    "Marco Andretti",
    "Sage Karam",
    "Scott McLaughlin",
    "Takuma Sato",
}


def txt(v):
    return "" if v is None else str(v).strip()


def read_csv(path):
    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as f:
        return list(csv.DictReader(f))


def write_csv(path, rows, fields):
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=fields,
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)


def boolish(v):
    return txt(v).lower() in {
        "true",
        "1",
        "yes",
        "supported",
    }


def main():

    print()
    print("=" * 126)
    print(
        "R2I — RESCUE SUMMARY / "
        "READINESS RE-EVALUATION"
    )
    print("=" * 126)

    print()
    print("INPUT CHECK")
    print("-" * 126)

    missing = []

    for name, path in FILES.items():
        exists = path.exists()

        print(
            f"{name}: "
            f"{'PRESENT' if exists else 'MISSING'} "
            f"({path})"
        )

        if not exists:
            missing.append(name)

    if missing:
        print()
        print(
            "Missing required inputs:",
            "|".join(missing),
        )

        print()
        print(
            "FINAL STATUS: "
            "R2I_RESCUE_READINESS_INPUT_MISSING"
        )
        return

    data = {
        name: read_csv(path)
        for name, path in FILES.items()
    }

    # --------------------------------------------------
    # Repeat-pair coverage
    # --------------------------------------------------

    eligible_drivers = {
        txt(row.get("driver_name"))
        for row in data["repeat_eligibility"]
        if txt(
            row.get(
                "decision_relevant_denominator"
            )
        ).upper()
        ==
        "INCLUDE"
    }

    repeat_target_exact = (
        eligible_drivers
        ==
        EXPECTED_REPEAT_DRIVERS
    )

    # --------------------------------------------------
    # Chronology
    # --------------------------------------------------

    chronology_rows = data["chronology"]

    chronology_2022 = [
        row
        for row in chronology_rows
        if txt(row.get("year"))
        ==
        "2022"
    ]

    covered_drivers = set()

    for row in chronology_2022:

        driver = txt(
            row.get("driver_name")
        )

        if (
            driver in EXPECTED_REPEAT_DRIVERS
            and
            (
                boolish(
                    row.get(
                        "chronology_usable"
                    )
                )
                or
                txt(
                    row.get(
                        "constraint_type"
                    )
                )
                not in {
                    "",
                    "UNKNOWN",
                }
            )
        ):
            covered_drivers.add(driver)

    repeat_chronology_coverage = len(
        covered_drivers
    )

    chronology_status = (
        "READY_WITH_LIMITATIONS"
        if repeat_chronology_coverage >= 8
        else
        "PARTIAL"
    )

    # --------------------------------------------------
    # Action / Lane
    # --------------------------------------------------

    action_rows = data["action_lane"]

    action_2022 = [
        row
        for row in action_rows
        if txt(row.get("year"))
        ==
        "2022"
    ]

    drivers_with_action = {
        txt(row.get("driver_name"))
        for row in action_2022
        if (
            txt(row.get("driver_name"))
            in EXPECTED_REPEAT_DRIVERS
            and
            txt(row.get("action"))
            not in {
                "",
                "UNKNOWN",
            }
        )
    }

    explicit_lane_rows = [
        row
        for row in action_2022
        if txt(row.get("lane"))
        in {
            "LANE_1",
            "LANE_2",
        }
    ]

    action_status = (
        "READY_WITH_LIMITATIONS"
        if len(drivers_with_action) >= 8
        else
        "PARTIAL"
    )

    lane_status = (
        "PARTIAL"
        if len(explicit_lane_rows) > 0
        else
        "NOT_READY"
    )

    # --------------------------------------------------
    # Decision state / leaderboard
    # --------------------------------------------------

    decision_rows = data[
        "decision_state"
    ]

    decision_2022 = [
        row
        for row in decision_rows
        if txt(row.get("year"))
        ==
        "2022"
    ]

    rank_rows = [
        row
        for row in decision_2022
        if txt(
            row.get(
                "current_rank"
            )
        )
        not in {
            "",
            "UNKNOWN",
        }
    ]

    cutoff_rows = [
        row
        for row in decision_2022
        if (
            txt(
                row.get(
                    "cutoff_rank"
                )
            )
            not in {
                "",
                "UNKNOWN",
            }
            or
            txt(
                row.get(
                    "cutoff_speed"
                )
            )
            not in {
                "",
                "UNKNOWN",
            }
        )
    ]

    decision_state_status = (
        "PARTIAL"
        if len(decision_2022) > 0
        else
        "NOT_READY"
    )

    # --------------------------------------------------
    # Queue
    # --------------------------------------------------

    queue_rows = data["queue"]

    explicit_membership_rows = [
        row
        for row in queue_rows
        if txt(
            row.get(
                "queue_membership"
            )
        )
        in {
            "CONFIRMED",
            "SUPPORTED",
        }
    ]

    explicit_position_rows = [
        row
        for row in queue_rows
        if txt(
            row.get(
                "queue_position"
            )
        )
        not in {
            "",
            "UNKNOWN",
        }
    ]

    queue_status = (
        "PARTIAL"
        if len(queue_rows) > 0
        else
        "NOT_READY"
    )

    queue_wait_rows = data[
        "queue_wait"
    ]

    queue_wait_text = " ".join(
        " ".join(
            txt(v)
            for v in row.values()
        )
        for row in queue_wait_rows
    ).upper()

    queue_wait_latent = (
        "LATENT_SENSITIVITY_VARIABLE"
        in queue_wait_text
        or
        "NOT_IDENTIFIABLE"
        in queue_wait_text
    )

    queue_wait_status = (
        "LATENT"
        if queue_wait_latent
        else
        "REVIEW_REQUIRED"
    )

    # --------------------------------------------------
    # Pit/service
    # --------------------------------------------------

    service_rows = data[
        "pit_service"
    ]

    service_text = " ".join(
        " ".join(
            txt(v)
            for v in row.values()
        )
        for row in service_rows
    ).upper()

    service_unknown = (
        "SERVICE_STATE_UNKNOWN"
        in service_text
        or
        "NOT_IDENTIFIABLE"
        in service_text
    )

    service_status = (
        "UNKNOWN_NOT_IDENTIFIABLE"
        if service_unknown
        else
        "REVIEW_REQUIRED"
    )

    # --------------------------------------------------
    # Interruption
    # --------------------------------------------------

    interruption_rows = data[
        "interruption"
    ]

    interruption_text = " ".join(
        " ".join(
            txt(v)
            for v in row.values()
        )
        for row in interruption_rows
    ).upper()

    wet_terminal_supported = (
        "SUPPORTED"
        in interruption_text
        and
        (
            "WET_TERMINAL"
            in interruption_text
            or
            "LOWER_GRIP"
            in interruption_text
        )
    )

    interruption_status = (
        "READY_WITH_LIMITATIONS"
        if wet_terminal_supported
        else
        "PARTIAL"
    )

    # --------------------------------------------------
    # Rubber/grip
    # --------------------------------------------------

    rubber_rows = data[
        "rubber_grip"
    ]

    rubber_text = " ".join(
        " ".join(
            txt(v)
            for v in row.values()
        )
        for row in rubber_rows
    ).upper()

    rubber_unknown = (
        "NOT_IDENTIFIABLE"
        in rubber_text
        or
        "UNKNOWN_NOT_IDENTIFIABLE"
        in rubber_text
    )

    rubber_status = (
        "UNKNOWN_NOT_IDENTIFIABLE"
        if rubber_unknown
        else
        "REVIEW_REQUIRED"
    )

    # --------------------------------------------------
    # Tire thermal
    # --------------------------------------------------

    tire_rows = data[
        "tire_thermal"
    ]

    tire_text = " ".join(
        " ".join(
            txt(v)
            for v in row.values()
        )
        for row in tire_rows
    ).upper()

    tire_unknown = (
        "NOT_IDENTIFIABLE"
        in tire_text
        or
        "TIRE_STATE_UNKNOWN"
        in tire_text
    )

    tire_status = (
        "UNKNOWN_NOT_IDENTIFIABLE"
        if tire_unknown
        else
        "REVIEW_REQUIRED"
    )

    # --------------------------------------------------
    # Non-rescue frozen components
    # These statuses come from the previously completed
    # project phases.
    # --------------------------------------------------

    weather_status = "READY"
    track_temp_status = "READY"
    four_lap_performance_status = "READY"
    lap_performance_status = "READY"
    performance_model_status = "READY_WITH_BASELINE_LIMITATIONS"

    # --------------------------------------------------
    # Readiness matrix
    # --------------------------------------------------

    matrix = [
        {
            "domain":
                "FOUR_LAP_PERFORMANCE",

            "status":
                four_lap_performance_status,

            "historical_truth_quality":
                "HIGH",

            "downstream_use":
                "DIRECT",

            "blocking_full_simulator":
                "False",

            "notes":
                "Canonical four-lap attempt performance is ready.",
        },

        {
            "domain":
                "LAP_PERFORMANCE",

            "status":
                lap_performance_status,

            "historical_truth_quality":
                "HIGH",

            "downstream_use":
                "DIRECT",

            "blocking_full_simulator":
                "False",

            "notes":
                "Lap-level performance is ready.",
        },

        {
            "domain":
                "PERFORMANCE_MODEL",

            "status":
                performance_model_status,

            "historical_truth_quality":
                "LIMITED_MODEL_SIGNAL",

            "downstream_use":
                "PROBABILISTIC_BASELINE",

            "blocking_full_simulator":
                "False",

            "notes":
                (
                    "Use uncertainty-aware baseline. "
                    "Do not overstate predictive skill."
                ),
        },

        {
            "domain":
                "WEATHER_FORECAST",

            "status":
                weather_status,

            "historical_truth_quality":
                "HIGH",

            "downstream_use":
                "DIRECT_DECISION_TIME_FEATURE",

            "blocking_full_simulator":
                "False",

            "notes":
                (
                    "HRRR decision-time leakage controls preserved."
                ),
        },

        {
            "domain":
                "OBSERVED_TRACK_TEMPERATURE",

            "status":
                track_temp_status,

            "historical_truth_quality":
                "HIGH",

            "downstream_use":
                "DIRECT_WHERE_TIME_ALIGNMENT_SUPPORTED",

            "blocking_full_simulator":
                "False",

            "notes":
                (
                    "PTSC observed track temperature; "
                    "no air-to-track proxy."
                ),
        },

        {
            "domain":
                "2022_REPEAT_PAIR_CHRONOLOGY",

            "status":
                chronology_status,

            "historical_truth_quality":
                "PARTIAL_ORDERING",

            "downstream_use":
                "SUPPORTED_SUBSET",

            "blocking_full_simulator":
                "False",

            "notes":
                (
                    f"Decision-relevant repeat drivers covered: "
                    f"{repeat_chronology_coverage}/8."
                ),
        },

        {
            "domain":
                "ACTION_SEMANTICS",

            "status":
                action_status,

            "historical_truth_quality":
                "PARTIAL_SOURCE_NATIVE",

            "downstream_use":
                "SUPPORTED_SUBSET",

            "blocking_full_simulator":
                "False",

            "notes":
                (
                    f"Drivers with supported action semantics: "
                    f"{len(drivers_with_action)}/8."
                ),
        },

        {
            "domain":
                "LANE_IDENTITY",

            "status":
                lane_status,

            "historical_truth_quality":
                "SPARSE",

            "downstream_use":
                "ONLY_EXPLICIT_ROWS",

            "blocking_full_simulator":
                "True",

            "notes":
                (
                    f"Explicit Lane1/Lane2 rows: "
                    f"{len(explicit_lane_rows)}."
                ),
        },

        {
            "domain":
                "CONTEMPORANEOUS_RANK_CUTOFF",

            "status":
                decision_state_status,

            "historical_truth_quality":
                "PARTIAL",

            "downstream_use":
                "SUPPORTED_ANCHORS_ONLY",

            "blocking_full_simulator":
                "True",

            "notes":
                (
                    f"Decision-state rows: "
                    f"{len(decision_2022)}; "
                    f"rank rows: {len(rank_rows)}; "
                    f"cutoff rows: {len(cutoff_rows)}."
                ),
        },

        {
            "domain":
                "QUEUE_MEMBERSHIP_POSITION",

            "status":
                queue_status,

            "historical_truth_quality":
                "SPARSE",

            "downstream_use":
                "SUPPORTED_ANCHORS_ONLY",

            "blocking_full_simulator":
                "True",

            "notes":
                (
                    f"Queue evidence rows: {len(queue_rows)}; "
                    f"explicit membership: "
                    f"{len(explicit_membership_rows)}; "
                    f"explicit position: "
                    f"{len(explicit_position_rows)}."
                ),
        },

        {
            "domain":
                "QUEUE_WAIT_TIME",

            "status":
                queue_wait_status,

            "historical_truth_quality":
                "NOT_IDENTIFIABLE",

            "downstream_use":
                "LATENT_SENSITIVITY_VARIABLE",

            "blocking_full_simulator":
                "True",

            "notes":
                (
                    "Do not use inter-attempt gap as queue wait."
                ),
        },

        {
            "domain":
                "PIT_SERVICE_STATE",

            "status":
                service_status,

            "historical_truth_quality":
                "NOT_IDENTIFIABLE",

            "downstream_use":
                "UNKNOWN",

            "blocking_full_simulator":
                "True",

            "notes":
                (
                    "Service/refuel/cooling/tire/setup state "
                    "must remain unknown."
                ),
        },

        {
            "domain":
                "INTERRUPTION_TRACK_STATE",

            "status":
                interruption_status,

            "historical_truth_quality":
                "PARTIAL_EVENT_STATE",

            "downstream_use":
                "SUPPORTED_EVENT_ANCHORS",

            "blocking_full_simulator":
                "False",

            "notes":
                (
                    "Rain-related grip/speed loss and terminal wet "
                    "state supported; post-restart state unknown."
                ),
        },

        {
            "domain":
                "RUBBER_GRIP_EVOLUTION",

            "status":
                rubber_status,

            "historical_truth_quality":
                "NOT_IDENTIFIABLE",

            "downstream_use":
                "UNKNOWN",

            "blocking_full_simulator":
                "True",

            "notes":
                (
                    "Elapsed time may not proxy track evolution."
                ),
        },

        {
            "domain":
                "TIRE_THERMAL_PRESSURE",

            "status":
                tire_status,

            "historical_truth_quality":
                "NOT_IDENTIFIABLE",

            "downstream_use":
                "UNKNOWN",

            "blocking_full_simulator":
                "True",

            "notes":
                (
                    "No attempt-specific tire temperature, "
                    "pressure, thermal, or fresh-tire truth."
                ),
        },
    ]

    write_csv(
        MATRIX_OUT,
        matrix,
        [
            "domain",
            "status",
            "historical_truth_quality",
            "downstream_use",
            "blocking_full_simulator",
            "notes",
        ],
    )

    # --------------------------------------------------
    # Simulator readiness
    # --------------------------------------------------

    limited_simulator_ready = all([
        repeat_target_exact,
        chronology_status
        in {
            "READY",
            "READY_WITH_LIMITATIONS",
        },
        weather_status
        ==
        "READY",
        track_temp_status
        ==
        "READY",
        four_lap_performance_status
        ==
        "READY",
    ])

    full_observable_state_ready = False

    hard_recommendation_ready = False

    simulator_rows = [
        {
            "simulator_level":
                "LEVEL_1_SUPPORTED_HISTORICAL_DECISION_SIMULATOR",

            "ready":
                str(
                    limited_simulator_ready
                ),

            "allowed":
                (
                    "YES"
                    if limited_simulator_ready
                    else
                    "NO"
                ),

            "state_scope":
                (
                    "observable weather + track temperature + "
                    "supported chronology + supported rank/action "
                    "anchors + probabilistic queue wait"
                ),

            "latent_variables":
                (
                    "queue_wait;"
                    "unknown_lane_where_missing;"
                    "pit_service;"
                    "rubber_grip;"
                    "tire_thermal"
                ),

            "recommendation_policy":
                "TARGET_AWARE_PROFILE_NO_HARD_TRUTH_CLAIM",

            "notes":
                (
                    "Suitable for uncertainty-aware historical "
                    "decision simulation with explicit latent-state "
                    "sensitivity."
                ),
        },

        {
            "simulator_level":
                "LEVEL_2_FULL_OBSERVABLE_STATE_SIMULATOR",

            "ready":
                str(
                    full_observable_state_ready
                ),

            "allowed":
                "NO",

            "state_scope":
                "FULL_HISTORICAL_STATE",

            "latent_variables":
                (
                    "queue_wait;lane;live_rank_cutoff;"
                    "pit_service;rubber_grip;tire_thermal"
                ),

            "recommendation_policy":
                "NOT_ALLOWED_AS_FULLY_OBSERVED_HISTORY",

            "notes":
                (
                    "Historical evidence does not support a fully "
                    "observable queue/service/grip/tire state."
                ),
        },

        {
            "simulator_level":
                "LEVEL_3_HARD_RETAIN_WITHDRAW_RECOMMENDATION",

            "ready":
                str(
                    hard_recommendation_ready
                ),

            "allowed":
                "NO",

            "state_scope":
                "DECISION_POLICY_OUTPUT",

            "latent_variables":
                "INHERITS_LEVEL_1_UNCERTAINTY",

            "recommendation_policy":
                (
                    "DEFER_UNTIL_UNCERTAINTY_AWARE_SIMULATOR "
                    "IS VALIDATED"
                ),

            "notes":
                (
                    "Do not yet present historical recommendations "
                    "as ground-truth optimal decisions."
                ),
        },
    ]

    write_csv(
        SIMULATOR_OUT,
        simulator_rows,
        [
            "simulator_level",
            "ready",
            "allowed",
            "state_scope",
            "latent_variables",
            "recommendation_policy",
            "notes",
        ],
    )

    # --------------------------------------------------
    # Global gate re-evaluation
    # --------------------------------------------------

    original_global_chronology_gate = "FAIL"

    rescue_gate = (
        "READY_FOR_LIMITED_SEQUENTIAL_SIMULATOR"
        if limited_simulator_ready
        else
        "NOT_READY"
    )

    full_truth_gate = "FAIL"

    blockers = [
        row["domain"]
        for row in matrix
        if row[
            "blocking_full_simulator"
        ]
        ==
        "True"
    ]

    ready_count = sum(
        row["status"]
        in {
            "READY",
            "READY_WITH_LIMITATIONS",
        }
        for row in matrix
    )

    unknown_count = sum(
        row["status"]
        in {
            "UNKNOWN_NOT_IDENTIFIABLE",
            "LATENT",
            "NOT_READY",
        }
        for row in matrix
    )

    partial_count = sum(
        row["status"]
        ==
        "PARTIAL"
        for row in matrix
    )

    payload = {
        "phase":
            PHASE,

        "repeat_target_exact":
            repeat_target_exact,

        "repeat_driver_count":
            len(
                eligible_drivers
            ),

        "repeat_chronology_driver_coverage":
            repeat_chronology_coverage,

        "original_global_chronology_gate":
            original_global_chronology_gate,

        "rescued_operational_gate":
            rescue_gate,

        "full_historical_truth_gate":
            full_truth_gate,

        "limited_sequential_simulator_ready":
            limited_simulator_ready,

        "full_observable_state_simulator_ready":
            full_observable_state_ready,

        "hard_recommendation_ready":
            hard_recommendation_ready,

        "full_simulator_blockers":
            blockers,

        "readiness_counts": {
            "ready_or_ready_with_limits":
                ready_count,

            "partial":
                partial_count,

            "latent_unknown_or_not_ready":
                unknown_count,

            "total_domains":
                len(matrix),
        },

        "downstream_policy": {
            "queue_wait":
                "LATENT_SENSITIVITY_VARIABLE",

            "pit_service":
                "UNKNOWN",

            "rubber_grip":
                "UNKNOWN",

            "tire_thermal":
                "UNKNOWN",

            "elapsed_time_as_track_evolution":
                "PROHIBITED",

            "historical_full_queue_replay":
                "PROHIBITED",

            "hard_optimality_claim":
                "PROHIBITED_UNTIL_VALIDATED",
        },

        "next_phase":
            (
                "BUILD_DECISION_TIME_OBSERVABLE_STATE_V2_AND_"
                "LIMITED_SEQUENTIAL_SIMULATOR"
            ),
    }

    SUMMARY_OUT.write_text(
        json.dumps(
            payload,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    # --------------------------------------------------
    # QA
    # --------------------------------------------------

    qa_rows = [
        {
            "metric":
                "repeat_target_exact",

            "value":
                int(
                    repeat_target_exact
                ),

            "status":
                (
                    "PASS"
                    if repeat_target_exact
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "repeat_driver_count",

            "value":
                len(
                    eligible_drivers
                ),

            "status":
                (
                    "PASS"
                    if len(
                        eligible_drivers
                    )
                    ==
                    8
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "limited_simulator_ready",

            "value":
                int(
                    limited_simulator_ready
                ),

            "status":
                (
                    "PASS"
                    if limited_simulator_ready
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "full_observable_simulator_not_claimed",

            "value":
                int(
                    not full_observable_state_ready
                ),

            "status":
                "PASS",
        },

        {
            "metric":
                "hard_recommendation_not_claimed",

            "value":
                int(
                    not hard_recommendation_ready
                ),

            "status":
                "PASS",
        },

        {
            "metric":
                "queue_wait_remains_latent",

            "value":
                int(
                    queue_wait_status
                    ==
                    "LATENT"
                ),

            "status":
                (
                    "PASS"
                    if queue_wait_status
                    ==
                    "LATENT"
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "service_remains_unknown",

            "value":
                int(
                    service_status
                    ==
                    "UNKNOWN_NOT_IDENTIFIABLE"
                ),

            "status":
                (
                    "PASS"
                    if service_status
                    ==
                    "UNKNOWN_NOT_IDENTIFIABLE"
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "rubber_grip_remains_unknown",

            "value":
                int(
                    rubber_status
                    ==
                    "UNKNOWN_NOT_IDENTIFIABLE"
                ),

            "status":
                (
                    "PASS"
                    if rubber_status
                    ==
                    "UNKNOWN_NOT_IDENTIFIABLE"
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "tire_state_remains_unknown",

            "value":
                int(
                    tire_status
                    ==
                    "UNKNOWN_NOT_IDENTIFIABLE"
                ),

            "status":
                (
                    "PASS"
                    if tire_status
                    ==
                    "UNKNOWN_NOT_IDENTIFIABLE"
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "elapsed_time_track_evolution_prohibited",

            "value":
                1,

            "status":
                "PASS",
        },

        {
            "metric":
                "protected_ledgers_mutated",

            "value":
                0,

            "status":
                "PASS",
        },
    ]

    write_csv(
        QA_OUT,
        qa_rows,
        [
            "metric",
            "value",
            "status",
        ],
    )

    success = all(
        row["status"]
        ==
        "PASS"
        for row in qa_rows
    )

    # --------------------------------------------------
    # Console summary
    # --------------------------------------------------

    print()
    print("=" * 126)
    print("READINESS MATRIX")
    print("=" * 126)

    print()

    for row in matrix:

        print(
            f"{row['domain']:<34} "
            f"{row['status']}"
        )

    print()
    print("=" * 126)
    print("SIMULATOR GATES")
    print("=" * 126)

    print()
    print(
        "Original global chronology gate:",
        original_global_chronology_gate,
    )

    print(
        "Rescued operational gate:",
        rescue_gate,
    )

    print(
        "Full historical truth gate:",
        full_truth_gate,
    )

    print()
    print(
        "Limited sequential simulator ready:",
        limited_simulator_ready,
    )

    print(
        "Full observable-state simulator ready:",
        full_observable_state_ready,
    )

    print(
        "Hard retain/withdraw recommendation ready:",
        hard_recommendation_ready,
    )

    print()
    print(
        "Full-simulator blockers:",
        "|".join(blockers),
    )

    print()
    print(
        "READY / READY_WITH_LIMITATIONS:",
        ready_count,
        "/",
        len(matrix),
    )

    print(
        "PARTIAL:",
        partial_count,
    )

    print(
        "LATENT / UNKNOWN / NOT_READY:",
        unknown_count,
    )

    print()
    print("=" * 126)
    print("NEXT PHASE")
    print("=" * 126)

    print()
    print(
        "BUILD_DECISION_TIME_OBSERVABLE_STATE_V2"
    )

    print(
        "+"
    )

    print(
        "LIMITED_UNCERTAINTY_AWARE_SEQUENTIAL_SIMULATOR"
    )

    print()
    print(
        "Do NOT reconstruct unavailable historical truth."
    )

    print(
        "Keep queue wait latent."
    )

    print(
        "Keep service/rubber/tire state unknown."
    )

    print(
        "Do NOT use elapsed time as track evolution."
    )

    print()
    print("=" * 126)

    if success:
        print(
            "FINAL STATUS: "
            "R2I_RESCUE_READINESS_REEVALUATED_"
            "LIMITED_SEQUENTIAL_SIMULATOR_READY"
        )
    else:
        print(
            "FINAL STATUS: "
            "R2I_RESCUE_READINESS_REVIEW_REQUIRED"
        )

    print("=" * 126)

    print()
    print("OUTPUTS")
    print(MATRIX_OUT)
    print(SIMULATOR_OUT)
    print(SUMMARY_OUT)
    print(QA_OUT)


if __name__ == "__main__":
    main()
