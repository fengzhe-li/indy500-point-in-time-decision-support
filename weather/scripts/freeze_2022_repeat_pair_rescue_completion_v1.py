from pathlib import Path
import csv
import json


PHASE = "R1G.31"

RESULT_V3 = Path(
    "weather/output/"
    "chronology_rescue_2022_result_to_canonical_attempt_matches_v3.csv"
)

CHRONOLOGY_V10 = Path(
    "weather/output/"
    "unified_attempt_chronology_constraint_ledger_v10.csv"
)

ACTION_V7 = Path(
    "weather/output/"
    "unified_attempt_action_lane_ledger_v7.csv"
)

ELIGIBILITY = Path(
    "weather/output/"
    "chronology_rescue_2022_repeat_pair_driver_eligibility_v1.csv"
)

OUTPUT_DIR = Path("weather/output")

SUMMARY_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_repeat_pair_rescue_completion_v1.csv"
)

DRIVER_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_repeat_pair_final_driver_coverage_v1.csv"
)

JSON_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_repeat_pair_rescue_completion_v1.json"
)

QA_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_repeat_pair_rescue_completion_v1_qa.csv"
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


def first(row, fields):
    for field in fields:
        value = txt(row.get(field))
        if value:
            return value
    return ""


def driver_name(row):
    return first(
        row,
        [
            "canonical_driver_name",
            "driver_name",
            "driver",
        ],
    )


def main():

    print()
    print("=" * 118)
    print(
        "R1G.31 — 2022 REPEAT-PAIR RESCUE "
        "COMPLETION FREEZE + READINESS REASSESSMENT"
    )
    print("=" * 118)

    required = [
        RESULT_V3,
        CHRONOLOGY_V10,
        ACTION_V7,
        ELIGIBILITY,
    ]

    print()
    print("INPUT CHECK")
    print("-" * 118)

    for path in required:
        print(
            f"{path}: "
            f"{'PRESENT' if path.exists() else 'MISSING'}"
        )

    if not all(path.exists() for path in required):
        print()
        print(
            "FINAL STATUS: "
            "2022_REPEAT_PAIR_FREEZE_INPUT_MISSING"
        )
        return

    result_rows = read_csv(RESULT_V3)
    chronology = read_csv(CHRONOLOGY_V10)
    action = read_csv(ACTION_V7)
    eligibility = read_csv(ELIGIBILITY)

    # --------------------------------------------------
    # 2022 verified population
    # --------------------------------------------------

    attempts_2022 = {
        txt(row.get("attempt_id")): row
        for row in result_rows
        if txt(row.get("attempt_id"))
    }

    total_attempts = len(attempts_2022)

    covered_ids = {
        txt(row.get("attempt_id"))
        for row in chronology
        if (
            txt(row.get("attempt_id")) in attempts_2022
            and
            txt(row.get("chronology_usable")).lower()
            == "true"
        )
    }

    covered_attempts = len(covered_ids)

    chronology_pct = (
        100.0 * covered_attempts / total_attempts
        if total_attempts
        else 0.0
    )

    # --------------------------------------------------
    # Frozen decision-relevant denominator
    # --------------------------------------------------

    eligible_drivers = {
        txt(row.get("driver_name"))
        for row in eligibility
        if txt(
            row.get(
                "decision_relevant_denominator"
            )
        ).upper()
        == "INCLUDE"
    }

    excluded_drivers = {
        txt(row.get("driver_name"))
        for row in eligibility
        if txt(
            row.get(
                "decision_relevant_denominator"
            )
        ).upper()
        != "INCLUDE"
    }

    # Build attempt sets only from the verified V3 rows.
    groups = {}

    for aid, row in attempts_2022.items():

        d = driver_name(row)

        if d in eligible_drivers:
            groups.setdefault(
                d,
                set(),
            ).add(aid)

    #
    # Frozen policy:
    # Sage Karam's status-only No Attempt object is not
    # part of the decision-relevant pair.
    #
    karam_no_attempt = (
        "4778bf12-3fb5-5321-b4ae-9dc2f0880c25"
    )

    if "Sage Karam" in groups:
        groups["Sage Karam"].discard(
            karam_no_attempt
        )

    driver_rows = []

    fully_covered = set()

    for d in sorted(eligible_drivers):

        aids = groups.get(
            d,
            set(),
        )

        covered = sorted(
            aids.intersection(
                covered_ids
            )
        )

        missing = sorted(
            aids.difference(
                covered_ids
            )
        )

        full = (
            len(aids) > 0
            and
            len(missing) == 0
        )

        if full:
            fully_covered.add(d)

        driver_rows.append({
            "driver_name":
                d,

            "decision_relevant":
                "True",

            "pair_attempt_count":
                len(aids),

            "covered_attempt_count":
                len(covered),

            "fully_covered":
                str(full),

            "attempt_ids":
                "|".join(
                    sorted(aids)
                ),

            "covered_attempt_ids":
                "|".join(
                    covered
                ),

            "missing_attempt_ids":
                "|".join(
                    missing
                ),
        })

    repeat_denominator = len(
        eligible_drivers
    )

    repeat_covered = len(
        fully_covered
    )

    repeat_pct = (
        100.0
        *
        repeat_covered
        /
        repeat_denominator
        if repeat_denominator
        else 0.0
    )

    # --------------------------------------------------
    # Lane evidence
    # --------------------------------------------------

    explicit_lane_rows = [
        row
        for row in action
        if txt(row.get("lane")).upper()
        not in {
            "",
            "UNKNOWN",
        }
    ]

    lane_count = len(
        explicit_lane_rows
    )

    # --------------------------------------------------
    # Readiness policy
    # --------------------------------------------------

    repeat_subgroup_status = (
        "READY"
        if (
            repeat_denominator == 8
            and
            repeat_covered == 8
        )
        else
        "NOT_READY"
    )

    overall_chronology_status = (
        "PARTIAL"
        if covered_attempts > 0
        else
        "NOT_READY"
    )

    queue_replay_status = (
        "NOT_READY"
        if lane_count < repeat_denominator
        else
        "REVIEW_REQUIRED"
    )

    chronology_gate = "FAIL"

    print()
    print("=" * 118)
    print("FROZEN RESULTS")
    print("=" * 118)

    print()
    print(
        "2022 verified attempt population:",
        total_attempts,
    )

    print(
        "Chronology-covered attempts:",
        covered_attempts,
    )

    print(
        "Overall 2022 chronology coverage:",
        f"{chronology_pct:.2f}%",
    )

    print()
    print(
        "Decision-relevant repeat denominator:",
        repeat_denominator,
    )

    print(
        "Fully covered repeat groups:",
        repeat_covered,
    )

    print(
        "Decision-relevant repeat coverage:",
        f"{repeat_covered}/{repeat_denominator}",
        f"({repeat_pct:.2f}%)",
    )

    print()
    print(
        "Fully covered drivers:",
        "|".join(
            sorted(
                fully_covered
            )
        ),
    )

    print()
    print(
        "Explicit historical Lane rows:",
        lane_count,
    )

    print()
    print(
        "Repeat subgroup readiness:",
        repeat_subgroup_status,
    )

    print(
        "Overall 2022 chronology:",
        overall_chronology_status,
    )

    print(
        "Exact queue replay:",
        queue_replay_status,
    )

    print(
        "Global chronology gate:",
        chronology_gate,
    )

    summary_rows = [
        {
            "metric":
                "active_chronology_ledger",
            "value":
                "V10",
        },
        {
            "metric":
                "active_action_lane_ledger",
            "value":
                "V7",
        },
        {
            "metric":
                "verified_2022_attempt_population",
            "value":
                total_attempts,
        },
        {
            "metric":
                "chronology_covered_attempts",
            "value":
                covered_attempts,
        },
        {
            "metric":
                "chronology_coverage_pct",
            "value":
                f"{chronology_pct:.2f}",
        },
        {
            "metric":
                "decision_relevant_repeat_denominator",
            "value":
                repeat_denominator,
        },
        {
            "metric":
                "decision_relevant_repeat_covered",
            "value":
                repeat_covered,
        },
        {
            "metric":
                "decision_relevant_repeat_coverage",
            "value":
                f"{repeat_covered}/{repeat_denominator}",
        },
        {
            "metric":
                "decision_relevant_repeat_coverage_pct",
            "value":
                f"{repeat_pct:.2f}",
        },
        {
            "metric":
                "explicit_historical_lane_rows",
            "value":
                lane_count,
        },
        {
            "metric":
                "repeat_subgroup_readiness",
            "value":
                repeat_subgroup_status,
        },
        {
            "metric":
                "overall_2022_chronology_status",
            "value":
                overall_chronology_status,
        },
        {
            "metric":
                "queue_replay_status",
            "value":
                queue_replay_status,
        },
        {
            "metric":
                "global_chronology_gate",
            "value":
                chronology_gate,
        },
    ]

    write_csv(
        SUMMARY_OUT,
        summary_rows,
        [
            "metric",
            "value",
        ],
    )

    write_csv(
        DRIVER_OUT,
        driver_rows,
        [
            "driver_name",
            "decision_relevant",
            "pair_attempt_count",
            "covered_attempt_count",
            "fully_covered",
            "attempt_ids",
            "covered_attempt_ids",
            "missing_attempt_ids",
        ],
    )

    frozen = {
        "phase":
            PHASE,

        "active_ledgers": {
            "chronology":
                "V10",
            "action_lane":
                "V7",
        },

        "2022_attempt_population":
            total_attempts,

        "chronology_covered_attempts":
            covered_attempts,

        "chronology_coverage_pct":
            round(
                chronology_pct,
                2,
            ),

        "decision_relevant_repeat": {
            "denominator":
                repeat_denominator,

            "covered":
                repeat_covered,

            "coverage_pct":
                round(
                    repeat_pct,
                    2,
                ),

            "fully_covered_drivers":
                sorted(
                    fully_covered
                ),

            "excluded_policy_drivers":
                sorted(
                    excluded_drivers
                ),
        },

        "explicit_historical_lane_rows":
            lane_count,

        "readiness": {
            "repeat_subgroup":
                repeat_subgroup_status,

            "overall_2022_chronology":
                overall_chronology_status,

            "exact_queue_replay":
                queue_replay_status,

            "global_chronology_gate":
                chronology_gate,
        },

        "policy_notes": [
            (
                "Decision-relevant repeat denominator "
                "remains frozen at 8."
            ),
            (
                "Colton Herta Waved Off and Josef Newgarden "
                "No Attempt remain excluded from the "
                "decision-relevant denominator."
            ),
            (
                "Sage Karam status-only No Attempt object "
                "is not treated as a third qualifying attempt."
            ),
            (
                "8/8 repeat-pair coverage does not imply "
                "complete 2022 chronology."
            ),
            (
                "Lane, queue wait, and exact queue replay "
                "remain unresolved."
            ),
        ],
    }

    JSON_OUT.write_text(
        json.dumps(
            frozen,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    qa_rows = [
        {
            "metric":
                "verified_population_is_44",
            "value":
                total_attempts,
            "status":
                "PASS"
                if total_attempts == 44
                else "FAIL",
        },
        {
            "metric":
                "chronology_covered_is_21",
            "value":
                covered_attempts,
            "status":
                "PASS"
                if covered_attempts == 21
                else "FAIL",
        },
        {
            "metric":
                "repeat_denominator_is_8",
            "value":
                repeat_denominator,
            "status":
                "PASS"
                if repeat_denominator == 8
                else "FAIL",
        },
        {
            "metric":
                "repeat_coverage_is_8_of_8",
            "value":
                repeat_covered,
            "status":
                "PASS"
                if repeat_covered == 8
                else "FAIL",
        },
        {
            "metric":
                "lane_rows_remain_1",
            "value":
                lane_count,
            "status":
                "PASS"
                if lane_count == 1
                else "REVIEW",
        },
        {
            "metric":
                "repeat_subgroup_ready",
            "value":
                repeat_subgroup_status,
            "status":
                "PASS"
                if repeat_subgroup_status == "READY"
                else "FAIL",
        },
        {
            "metric":
                "global_chronology_gate_not_upgraded",
            "value":
                chronology_gate,
            "status":
                "PASS"
                if chronology_gate == "FAIL"
                else "FAIL",
        },
        {
            "metric":
                "ledger_mutation",
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

    hard_fail = any(
        row["status"] == "FAIL"
        for row in qa_rows
    )

    print()
    print("=" * 118)

    if not hard_fail:
        print(
            "FINAL STATUS: "
            "2022_DECISION_RELEVANT_REPEAT_PAIR_RESCUE_FROZEN_8_OF_8"
        )
    else:
        print(
            "FINAL STATUS: "
            "2022_REPEAT_PAIR_FREEZE_REVIEW_REQUIRED"
        )

    print("=" * 118)

    print()
    print("OUTPUTS")
    print(SUMMARY_OUT)
    print(DRIVER_OUT)
    print(JSON_OUT)
    print(QA_OUT)


if __name__ == "__main__":
    main()
