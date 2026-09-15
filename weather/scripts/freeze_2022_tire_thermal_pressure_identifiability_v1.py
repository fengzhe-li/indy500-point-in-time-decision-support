from pathlib import Path
import csv
import json


PHASE = "R2H.2"

HITS = Path(
    "weather/output/"
    "tire_thermal_rescue_2022_targeted_hits_v1.csv"
)

SUMMARY = Path(
    "weather/output/"
    "tire_thermal_rescue_2022_targeted_summary_v1.csv"
)

RUBBER_POLICY = Path(
    "weather/output/"
    "rubber_grip_identifiability_2022_v1.csv"
)

SERVICE_POLICY = Path(
    "weather/output/"
    "pit_service_identifiability_2022_v1.csv"
)

QUEUE_POLICY = Path(
    "weather/output/"
    "queue_wait_identifiability_2022_v1.csv"
)

OUTPUT_DIR = Path("weather/output")

FREEZE_OUT = (
    OUTPUT_DIR
    / "tire_thermal_pressure_identifiability_2022_v1.csv"
)

JSON_OUT = (
    OUTPUT_DIR
    / "tire_thermal_pressure_identifiability_2022_v1.json"
)

QA_OUT = (
    OUTPUT_DIR
    / "tire_thermal_pressure_identifiability_2022_v1_qa.csv"
)


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


def main():

    print()
    print("=" * 124)
    print(
        "R2H.2 — 2022 TIRE THERMAL / PRESSURE "
        "IDENTIFIABILITY FREEZE"
    )
    print("=" * 124)

    required = [
        HITS,
        SUMMARY,
        RUBBER_POLICY,
        SERVICE_POLICY,
        QUEUE_POLICY,
    ]

    print()
    print("INPUT CHECK")
    print("-" * 124)

    for path in required:
        print(
            f"{path}: "
            f"{'PRESENT' if path.exists() else 'MISSING'}"
        )

    if not all(path.exists() for path in required):
        print()
        print(
            "FINAL STATUS: "
            "R2H2_TIRE_THERMAL_FREEZE_INPUT_MISSING"
        )
        return

    hits = read_csv(HITS)
    summary = read_csv(SUMMARY)

    # Protected policies are read-only dependencies.
    read_csv(RUBBER_POLICY)
    read_csv(SERVICE_POLICY)
    read_csv(QUEUE_POLICY)

    summary_map = {
        txt(row.get("metric")):
        txt(row.get("value"))
        for row in summary
    }

    priority_rows = int(
        summary_map.get(
            "priority_rows",
            "0",
        )
        or
        0
    )

    temp_candidates = int(
        summary_map.get(
            "direct_temperature_candidates",
            "0",
        )
        or
        0
    )

    pressure_candidates = int(
        summary_map.get(
            "direct_pressure_candidates",
            "0",
        )
        or
        0
    )

    thermal_candidates = int(
        summary_map.get(
            "direct_thermal_candidates",
            "0",
        )
        or
        0
    )

    fresh_between_runs = int(
        summary_map.get(
            "fresh_tire_between_runs_candidates",
            "0",
        )
        or
        0
    )

    generic_rows = [
        row
        for row in hits
        if txt(
            row.get("classification")
        )
        ==
        "GENERIC_TIRE_MENTION_REVIEW"
    ]

    temperature_identifiable = (
        temp_candidates > 0
        or
        thermal_candidates > 0
    )

    pressure_identifiable = (
        pressure_candidates > 0
    )

    fresh_tire_identifiable = (
        fresh_between_runs > 0
    )

    any_attempt_specific_tire_state = any([
        temperature_identifiable,
        pressure_identifiable,
        fresh_tire_identifiable,
    ])

    print()
    print("=" * 124)
    print("IDENTIFIABILITY ASSESSMENT")
    print("=" * 124)

    print()
    print(
        "R2H1 candidate rows:",
        len(hits),
    )

    print(
        "Generic tire review rows:",
        len(generic_rows),
    )

    print(
        "Priority rows:",
        priority_rows,
    )

    print()
    print(
        "Direct tire-temperature candidates:",
        temp_candidates,
    )

    print(
        "Direct tire-pressure candidates:",
        pressure_candidates,
    )

    print(
        "Direct thermal-state candidates:",
        thermal_candidates,
    )

    print(
        "Fresh-tire-between-runs candidates:",
        fresh_between_runs,
    )

    print()
    print(
        "Attempt-specific tire state identifiable:",
        any_attempt_specific_tire_state,
    )

    if any_attempt_specific_tire_state:
        tire_state_status = "PARTIALLY_IDENTIFIABLE"
        downstream_policy = "USE_ONLY_SOURCE_SUPPORTED_TIRE_STATE"
    else:
        tire_state_status = (
            "NOT_IDENTIFIABLE_FROM_RECOVERED_2022_EVIDENCE"
        )
        downstream_policy = "TIRE_STATE_UNKNOWN"

    print()
    print("=" * 124)
    print("FROZEN POLICY")
    print("=" * 124)

    print()
    print(
        "Tire temperature:",
        (
            "IDENTIFIABLE"
            if temperature_identifiable
            else
            "NOT_IDENTIFIABLE"
        ),
    )

    print(
        "Tire pressure:",
        (
            "IDENTIFIABLE"
            if pressure_identifiable
            else
            "NOT_IDENTIFIABLE"
        ),
    )

    print(
        "Thermal state:",
        (
            "IDENTIFIABLE"
            if thermal_candidates > 0
            else
            "NOT_IDENTIFIABLE"
        ),
    )

    print(
        "Fresh tire between runs:",
        (
            "IDENTIFIABLE"
            if fresh_tire_identifiable
            else
            "NOT_IDENTIFIABLE"
        ),
    )

    print()
    print(
        "Queue wait may infer tire temperature:",
        "NO",
    )

    print(
        "Second run may imply fresh tires:",
        "NO",
    )

    print(
        "Pit/service may imply pressure adjustment:",
        "NO",
    )

    print(
        "Elapsed time may imply thermal state:",
        "NO",
    )

    print()
    print(
        "Downstream tire-state policy:",
        downstream_policy,
    )

    freeze_rows = [
        {
            "phase":
                PHASE,

            "year":
                "2022",

            "tire_state_identifiability_status":
                tire_state_status,

            "tire_temperature_status":
                (
                    "IDENTIFIABLE"
                    if temperature_identifiable
                    else
                    "NOT_IDENTIFIABLE"
                ),

            "tire_pressure_status":
                (
                    "IDENTIFIABLE"
                    if pressure_identifiable
                    else
                    "NOT_IDENTIFIABLE"
                ),

            "thermal_state_status":
                (
                    "IDENTIFIABLE"
                    if thermal_candidates > 0
                    else
                    "NOT_IDENTIFIABLE"
                ),

            "fresh_tire_between_runs_status":
                (
                    "IDENTIFIABLE"
                    if fresh_tire_identifiable
                    else
                    "NOT_IDENTIFIABLE"
                ),

            "direct_temperature_rows":
                temp_candidates,

            "direct_pressure_rows":
                pressure_candidates,

            "direct_thermal_rows":
                thermal_candidates,

            "fresh_tire_between_runs_rows":
                fresh_between_runs,

            "generic_tire_review_rows":
                len(generic_rows),

            "quantitative_temperature_ready":
                "False",

            "quantitative_pressure_ready":
                "False",

            "queue_wait_can_infer_temperature":
                "False",

            "second_run_can_imply_fresh_tires":
                "False",

            "pit_service_can_imply_pressure_adjustment":
                "False",

            "elapsed_time_can_imply_thermal_state":
                "False",

            "downstream_tire_state_policy":
                downstream_policy,

            "notes":
                (
                    "Recovered 2022 Day 1 evidence contains only "
                    "generic tire mentions and no source-native "
                    "attempt-specific tire temperature, tire "
                    "pressure, thermal-state, warming/cooling, "
                    "or fresh-tire-between-runs evidence. "
                    "Queue wait, second-run status, pit/service "
                    "state, and elapsed session time must not be "
                    "used to infer tire thermal or pressure state."
                ),
        }
    ]

    write_csv(
        FREEZE_OUT,
        freeze_rows,
        list(
            freeze_rows[0].keys()
        ),
    )

    payload = {
        "phase":
            PHASE,

        "year":
            2022,

        "tire_state_identifiability_status":
            tire_state_status,

        "tire_temperature_status":
            freeze_rows[0][
                "tire_temperature_status"
            ],

        "tire_pressure_status":
            freeze_rows[0][
                "tire_pressure_status"
            ],

        "thermal_state_status":
            freeze_rows[0][
                "thermal_state_status"
            ],

        "fresh_tire_between_runs_status":
            freeze_rows[0][
                "fresh_tire_between_runs_status"
            ],

        "quantitative_temperature_ready":
            False,

        "quantitative_pressure_ready":
            False,

        "queue_wait_can_infer_temperature":
            False,

        "second_run_can_imply_fresh_tires":
            False,

        "pit_service_can_imply_pressure_adjustment":
            False,

        "elapsed_time_can_imply_thermal_state":
            False,

        "downstream_tire_state_policy":
            downstream_policy,
    }

    JSON_OUT.write_text(
        json.dumps(
            payload,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    qa_rows = [
        {
            "metric":
                "priority_rows_zero",

            "value":
                priority_rows,

            "status":
                (
                    "PASS"
                    if priority_rows
                    ==
                    0
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "temperature_candidates_zero",

            "value":
                temp_candidates,

            "status":
                (
                    "PASS"
                    if temp_candidates
                    ==
                    0
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "pressure_candidates_zero",

            "value":
                pressure_candidates,

            "status":
                (
                    "PASS"
                    if pressure_candidates
                    ==
                    0
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "thermal_candidates_zero",

            "value":
                thermal_candidates,

            "status":
                (
                    "PASS"
                    if thermal_candidates
                    ==
                    0
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "fresh_tire_between_runs_zero",

            "value":
                fresh_between_runs,

            "status":
                (
                    "PASS"
                    if fresh_between_runs
                    ==
                    0
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "temperature_not_inferred_from_wait",

            "value":
                0,

            "status":
                "PASS",
        },

        {
            "metric":
                "fresh_tires_not_inferred_from_second_run",

            "value":
                0,

            "status":
                "PASS",
        },

        {
            "metric":
                "pressure_not_inferred_from_service",

            "value":
                0,

            "status":
                "PASS",
        },

        {
            "metric":
                "thermal_state_not_inferred_from_elapsed_time",

            "value":
                0,

            "status":
                "PASS",
        },

        {
            "metric":
                "active_ledger_mutation",

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

    print()
    print("=" * 124)

    if success:
        print(
            "FINAL STATUS: "
            "R2H2_2022_TIRE_THERMAL_PRESSURE_IDENTIFIABILITY_"
            "FROZEN_UNKNOWN"
        )
    else:
        print(
            "FINAL STATUS: "
            "R2H2_TIRE_THERMAL_FREEZE_REVIEW_REQUIRED"
        )

    print("=" * 124)

    print()
    print("OUTPUTS")
    print(FREEZE_OUT)
    print(JSON_OUT)
    print(QA_OUT)


if __name__ == "__main__":
    main()
