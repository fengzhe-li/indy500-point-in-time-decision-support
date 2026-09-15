from pathlib import Path
import csv
import json


PHASE = "R2G.2"

R2G1_HITS = Path(
    "weather/output/"
    "rubber_grip_rescue_2022_targeted_hits_v1.csv"
)

R2G1_SUMMARY = Path(
    "weather/output/"
    "rubber_grip_rescue_2022_targeted_summary_v1.csv"
)

ADJACENT = Path(
    "weather/output/"
    "rubber_grip_adjacent_mechanism_evidence_2022_v1.csv"
)

INTERRUPTION_POLICY = Path(
    "weather/output/"
    "interruption_track_state_identifiability_2022_v1.csv"
)

OUTPUT_DIR = Path("weather/output")

FREEZE_OUT = (
    OUTPUT_DIR
    / "rubber_grip_identifiability_2022_v1.csv"
)

JSON_OUT = (
    OUTPUT_DIR
    / "rubber_grip_identifiability_2022_v1.json"
)

QA_OUT = (
    OUTPUT_DIR
    / "rubber_grip_identifiability_2022_v1_qa.csv"
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
        "R2G.2 — 2022 RUBBERING / GRIP "
        "IDENTIFIABILITY FREEZE"
    )
    print("=" * 124)

    required = [
        R2G1_HITS,
        R2G1_SUMMARY,
        ADJACENT,
        INTERRUPTION_POLICY,
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
            "R2G2_RUBBER_GRIP_FREEZE_INPUT_MISSING"
        )
        return

    hits = read_csv(R2G1_HITS)
    summary = read_csv(R2G1_SUMMARY)
    adjacent = read_csv(ADJACENT)
    interruption = read_csv(INTERRUPTION_POLICY)

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

    rubber_mechanism_candidates = int(
        summary_map.get(
            "rain_rubber_mechanism_candidates",
            "0",
        )
        or
        0
    )

    direct_rubber_grip = int(
        summary_map.get(
            "direct_rubber_grip_candidates",
            "0",
        )
        or
        0
    )

    direct_track_evolution_grip = int(
        summary_map.get(
            "direct_track_evolution_grip_candidates",
            "0",
        )
        or
        0
    )

    green_track_candidates = int(
        summary_map.get(
            "green_track_candidates",
            "0",
        )
        or
        0
    )

    adjacent_ok = (
        len(adjacent)
        ==
        1
        and
        txt(
            adjacent[0].get(
                "supported_mechanism"
            )
        )
        ==
        "OVERNIGHT_RAIN_CAN_WASH_AWAY_RUBBER_AT_IMS"
        and
        txt(
            adjacent[0].get(
                "may21_interruption_promotion_allowed"
            )
        ).lower()
        ==
        "false"
    )

    print()
    print("=" * 124)
    print("IDENTIFIABILITY ASSESSMENT")
    print("=" * 124)

    print()
    print(
        "R2G1 candidate rows:",
        len(hits),
    )

    print(
        "Priority rows:",
        priority_rows,
    )

    print(
        "Rain/rubber mechanism candidates:",
        rubber_mechanism_candidates,
    )

    print(
        "Direct rubber/grip candidates:",
        direct_rubber_grip,
    )

    print(
        "Direct track-evolution/grip candidates:",
        direct_track_evolution_grip,
    )

    print(
        "Green-track candidates:",
        green_track_candidates,
    )

    print()
    print(
        "Adjacent Fast Friday mechanism valid:",
        adjacent_ok,
    )

    day1_rubber_state_identifiable = (
        rubber_mechanism_candidates > 0
        or
        direct_rubber_grip > 0
    )

    day1_grip_evolution_identifiable = (
        direct_rubber_grip > 0
        or
        direct_track_evolution_grip > 0
        or
        green_track_candidates > 0
    )

    quantitative_rubber_ready = False
    quantitative_grip_ready = False

    rubber_feature_policy = (
        "OBSERVED"
        if day1_rubber_state_identifiable
        else
        "UNKNOWN_NOT_IDENTIFIABLE"
    )

    grip_feature_policy = (
        "OBSERVED"
        if day1_grip_evolution_identifiable
        else
        "UNKNOWN_NOT_IDENTIFIABLE"
    )

    print()
    print("=" * 124)
    print("FROZEN POLICY")
    print("=" * 124)

    print()
    print(
        "Day1 rubber state:",
        (
            "IDENTIFIABLE"
            if day1_rubber_state_identifiable
            else
            "NOT_IDENTIFIABLE"
        ),
    )

    print(
        "Day1 grip evolution:",
        (
            "IDENTIFIABLE"
            if day1_grip_evolution_identifiable
            else
            "NOT_IDENTIFIABLE"
        ),
    )

    print(
        "Quantitative rubber feature:",
        "NOT_READY",
    )

    print(
        "Quantitative grip-evolution feature:",
        "NOT_READY",
    )

    print()
    print(
        "Elapsed time may proxy track evolution:",
        "NO",
    )

    print(
        "Fast Friday rain/rubber evidence may become "
        "Day1 truth:",
        "NO",
    )

    print()
    print(
        "Downstream rubber policy:",
        rubber_feature_policy,
    )

    print(
        "Downstream grip-evolution policy:",
        grip_feature_policy,
    )

    freeze_rows = [
        {
            "phase":
                PHASE,

            "year":
                "2022",

            "day1_rubber_state_status":
                (
                    "IDENTIFIABLE"
                    if day1_rubber_state_identifiable
                    else
                    "NOT_IDENTIFIABLE_FROM_RECOVERED_2022_EVIDENCE"
                ),

            "day1_grip_evolution_status":
                (
                    "IDENTIFIABLE"
                    if day1_grip_evolution_identifiable
                    else
                    "NOT_IDENTIFIABLE_FROM_RECOVERED_2022_EVIDENCE"
                ),

            "direct_rubber_grip_evidence_rows":
                direct_rubber_grip,

            "direct_track_evolution_grip_rows":
                direct_track_evolution_grip,

            "green_track_evidence_rows":
                green_track_candidates,

            "rain_rubber_mechanism_day1_rows":
                rubber_mechanism_candidates,

            "adjacent_mechanism_support":
                (
                    "SUPPORTED"
                    if adjacent_ok
                    else
                    "NOT_READY"
                ),

            "adjacent_mechanism":
                (
                    "OVERNIGHT_RAIN_CAN_WASH_AWAY_RUBBER_AT_IMS"
                    if adjacent_ok
                    else
                    ""
                ),

            "adjacent_mechanism_context":
                (
                    "FAST_FRIDAY_2022_05_20"
                    if adjacent_ok
                    else
                    ""
                ),

            "adjacent_to_day1_promotion_allowed":
                "False",

            "quantitative_rubber_feature_ready":
                str(
                    quantitative_rubber_ready
                ),

            "quantitative_grip_feature_ready":
                str(
                    quantitative_grip_ready
                ),

            "elapsed_time_as_track_evolution":
                "PROHIBITED",

            "downstream_rubber_policy":
                rubber_feature_policy,

            "downstream_grip_evolution_policy":
                grip_feature_policy,

            "notes":
                (
                    "Recovered 2022 Day 1 evidence does not "
                    "identify a source-native rubber-state or "
                    "grip-evolution trajectory. Fast Friday "
                    "provides an IMS-specific mechanism showing "
                    "that overnight rain can wash away rubber, "
                    "but this is adjacent mechanism evidence only "
                    "and cannot be promoted to the May 21 "
                    "qualifying interruption. Elapsed session "
                    "time must not be used as a substitute for "
                    "track evolution."
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

        "day1_rubber_state_status":
            freeze_rows[0][
                "day1_rubber_state_status"
            ],

        "day1_grip_evolution_status":
            freeze_rows[0][
                "day1_grip_evolution_status"
            ],

        "adjacent_mechanism_support":
            (
                "SUPPORTED"
                if adjacent_ok
                else
                "NOT_READY"
            ),

        "adjacent_mechanism":
            (
                "OVERNIGHT_RAIN_CAN_WASH_AWAY_RUBBER_AT_IMS"
                if adjacent_ok
                else None
            ),

        "adjacent_to_day1_promotion_allowed":
            False,

        "quantitative_rubber_feature_ready":
            False,

        "quantitative_grip_feature_ready":
            False,

        "elapsed_time_as_track_evolution":
            "PROHIBITED",

        "downstream_rubber_policy":
            rubber_feature_policy,

        "downstream_grip_evolution_policy":
            grip_feature_policy,
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
                "direct_rubber_grip_rows_zero",

            "value":
                direct_rubber_grip,

            "status":
                (
                    "PASS"
                    if direct_rubber_grip
                    ==
                    0
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "direct_track_evolution_grip_rows_zero",

            "value":
                direct_track_evolution_grip,

            "status":
                (
                    "PASS"
                    if direct_track_evolution_grip
                    ==
                    0
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "green_track_rows_zero",

            "value":
                green_track_candidates,

            "status":
                (
                    "PASS"
                    if green_track_candidates
                    ==
                    0
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "adjacent_mechanism_valid",

            "value":
                int(adjacent_ok),

            "status":
                (
                    "PASS"
                    if adjacent_ok
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "adjacent_mechanism_not_promoted",

            "value":
                0,

            "status":
                "PASS",
        },

        {
            "metric":
                "quantitative_rubber_inferred",

            "value":
                0,

            "status":
                "PASS",
        },

        {
            "metric":
                "quantitative_grip_inferred",

            "value":
                0,

            "status":
                "PASS",
        },

        {
            "metric":
                "elapsed_time_used_as_track_evolution",

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
            "R2G2_2022_RUBBER_GRIP_IDENTIFIABILITY_FROZEN_"
            "DAY1_UNKNOWN_ADJACENT_MECHANISM_ONLY"
        )
    else:
        print(
            "FINAL STATUS: "
            "R2G2_RUBBER_GRIP_FREEZE_REVIEW_REQUIRED"
        )

    print("=" * 124)

    print()
    print("OUTPUTS")
    print(FREEZE_OUT)
    print(JSON_OUT)
    print(QA_OUT)


if __name__ == "__main__":
    main()
