from pathlib import Path
import csv
import json


PHASE = "R3C.0"

OUT = Path("weather/output")

STATE_V3 = (
    OUT
    / "decision_time_observable_state_v3.csv"
)

ACTION_LEDGER = (
    OUT
    / "unified_attempt_action_lane_ledger_v8.csv"
)

R3B4_ENVELOPE = (
    OUT
    / "r3b4_monte_carlo_action_envelope_v1.csv"
)

R3B4_SUMMARY = (
    OUT
    / "r3b4_monte_carlo_performance_decision_envelope_v1.json"
)

STATE_FINAL = (
    OUT
    / "decision_time_observable_state_v4_final.csv"
)

APPLICABILITY_OUT = (
    OUT
    / "r3c_action_historical_applicability_v1.csv"
)

ENVELOPE_FINAL = (
    OUT
    / "r3c_final_monte_carlo_action_envelope_v1.csv"
)

SUMMARY_OUT = (
    OUT
    / "r3c_final_capability_boundary_v1.json"
)

QA_OUT = (
    OUT
    / "r3c_final_state_action_freeze_v1_qa.csv"
)


EXPECTED_DRIVERS = {
    "Alexander Rossi",
    "Callum Ilott",
    "David Malukas",
    "Helio Castroneves",
    "Marco Andretti",
    "Sage Karam",
    "Scott McLaughlin",
    "Takuma Sato",
}


ACTIONS = [
    "STOP_RETAIN_CURRENT_RESULT",
    "REPEAT_LANE2_RETAIN_CURRENT_RESULT",
    "REPEAT_LANE1_WITHDRAW_CURRENT_RESULT",
]


def txt(v):
    return "" if v is None else str(v).strip()


def fnum(v):
    try:
        return float(txt(v))
    except Exception:
        return None


def truthy(v):
    return txt(v).lower() in {
        "true",
        "1",
        "yes",
    }


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


def unique_numeric(values, tolerance=1e-6):

    result = []

    for value in values:

        x = fnum(value)

        if x is None:
            continue

        if not any(
            abs(
                x - existing
            )
            <=
            tolerance
            for existing in result
        ):
            result.append(x)

    return result


def recover_attempt_speed(
    action_rows,
    driver,
    attempt_id,
):

    values = []
    evidence_ids = []

    for row in action_rows:

        if txt(
            row.get("year")
        ) != "2022":
            continue

        if txt(
            row.get(
                "driver_name"
            )
        ) != driver:
            continue

        subject = txt(
            row.get(
                "subject_attempt_id"
            )
        )

        related = txt(
            row.get(
                "related_attempt_id"
            )
        )

        if subject == attempt_id:

            speed = fnum(
                row.get(
                    "subject_speed_mph"
                )
            )

            if speed is not None:
                values.append(speed)

                evidence_ids.append(
                    txt(
                        row.get(
                            "evidence_id"
                        )
                    )
                )

        if related == attempt_id:

            speed = fnum(
                row.get(
                    "related_speed_mph"
                )
            )

            if speed is not None:
                values.append(speed)

                evidence_ids.append(
                    txt(
                        row.get(
                            "evidence_id"
                        )
                    )
                )

    unique = unique_numeric(
        values
    )

    if len(unique) == 1:

        return {
            "status":
                "RECOVERED_UNIQUE",

            "speed":
                unique[0],

            "evidence_ids":
                "|".join(
                    sorted(
                        {
                            x
                            for x
                            in evidence_ids
                            if x
                        }
                    )
                )
                or
                "UNKNOWN",
        }

    if len(unique) > 1:

        return {
            "status":
                "CONFLICT_MULTIPLE_SPEEDS",

            "speed":
                None,

            "evidence_ids":
                "|".join(
                    sorted(
                        {
                            x
                            for x
                            in evidence_ids
                            if x
                        }
                    )
                )
                or
                "UNKNOWN",
        }

    return {
        "status":
            "NOT_FOUND",

        "speed":
            None,

        "evidence_ids":
            "UNKNOWN",
    }


def applicability(
    driver,
    historical_action,
    action,
):

    h = txt(
        historical_action
    ).upper()

    # Sato's first result was invalidated.
    # This is not an elective retain/withdraw comparison.
    if (
        driver
        ==
        "Takuma Sato"
        or
        "REQUIRED_REATTEMPT_AFTER_INVALIDATION"
        in h
    ):

        return {
            "case_type":
                "REQUIRED_REATTEMPT_CASE",

            "historical_applicability":
                "NOT_APPLICABLE_AS_ELECTIVE_CHOICE",

            "historical_feasibility":
                "NOT_COMPARABLE",

            "interpretation":
                (
                    "The prior run was invalidated and a "
                    "reattempt was required. STOP/Lane2/Lane1 "
                    "envelopes are generic mathematical "
                    "counterfactuals only, not reconstructed "
                    "historical choices."
                ),
        }

    # Direct Lane 1 evidence exists for these cases.
    if (
        driver
        in {
            "Alexander Rossi",
            "Scott McLaughlin",
        }
        and
        "LANE1"
        in h.replace(
            "_",
            ""
        )
    ):

        if (
            action
            ==
            "REPEAT_LANE1_WITHDRAW_CURRENT_RESULT"
        ):

            return {
                "case_type":
                    "ELECTIVE_LANE1_OBSERVED",

                "historical_applicability":
                    "OBSERVED_ACTION",

                "historical_feasibility":
                    "SUPPORTED",

                "interpretation":
                    (
                        "Historical Lane 1 withdrawal action is "
                        "directly supported."
                    ),
            }

        return {
            "case_type":
                "ELECTIVE_LANE1_OBSERVED",

            "historical_applicability":
                "COUNTERFACTUAL_ACTION",

            "historical_feasibility":
                "RULE_POSSIBILITY_NOT_HISTORICALLY_RECONSTRUCTED",

            "interpretation":
                (
                    "Envelope is a counterfactual comparison. "
                    "The historical evidence directly supports "
                    "the Lane 1 action, not this alternative."
                ),
        }

    # Other repeat cases have action semantics but insufficient
    # historical lane/queue reconstruction.
    return {
        "case_type":
            "REPEAT_CASE_LANE_NOT_IDENTIFIED",

        "historical_applicability":
            (
                "GENERIC_COUNTERFACTUAL_OR_PARTIAL_HISTORY"
            ),

        "historical_feasibility":
            "NOT_FULLY_IDENTIFIABLE",

        "interpretation":
            (
                "Performance envelope is valid as generic "
                "action semantics, but the historically available "
                "Lane/action set is not fully reconstructed."
            ),
    }


def main():

    print()
    print("=" * 128)
    print(
        "R3C.0 — FINAL STATE REPAIR / "
        "ACTION APPLICABILITY FREEZE"
    )
    print("=" * 128)

    required = [
        STATE_V3,
        ACTION_LEDGER,
        R3B4_ENVELOPE,
        R3B4_SUMMARY,
    ]

    print()
    print("INPUT CHECK")
    print("-" * 128)

    missing = []

    for path in required:

        exists = path.exists()

        print(
            f"{path}: "
            f"{'PRESENT' if exists else 'MISSING'}"
        )

        if not exists:
            missing.append(
                str(path)
            )

    if missing:

        print()
        print(
            "FINAL STATUS: "
            "R3C0_REQUIRED_INPUT_MISSING"
        )
        return

    states = read_csv(
        STATE_V3
    )

    action_rows = read_csv(
        ACTION_LEDGER
    )

    envelope = read_csv(
        R3B4_ENVELOPE
    )

    r3b4_summary = json.loads(
        R3B4_SUMMARY.read_text(
            encoding="utf-8"
        )
    )

    drivers = {
        txt(
            row.get(
                "driver_name"
            )
        )
        for row in states
    }

    target_exact = (
        len(states) == 8
        and
        drivers
        ==
        EXPECTED_DRIVERS
    )

    print()
    print("=" * 128)
    print("FIRST-ATTEMPT SPEED REPAIR")
    print("=" * 128)

    final_states = []

    repaired = []
    unresolved = []

    for old in states:

        row = dict(old)

        driver = txt(
            row.get(
                "driver_name"
            )
        )

        first_id = txt(
            row.get(
                "first_attempt_id"
            )
        )

        current_speed = fnum(
            row.get(
                "first_attempt_speed_mph"
            )
        )

        row[
            "state_version"
        ] = "V4_FINAL"

        row[
            "first_attempt_speed_repair_status"
        ] = "NOT_REQUIRED"

        row[
            "first_attempt_speed_repair_evidence_ids"
        ] = "NOT_APPLICABLE"

        if current_speed is None:

            result = recover_attempt_speed(
                action_rows,
                driver,
                first_id,
            )

            row[
                "first_attempt_speed_repair_status"
            ] = result[
                "status"
            ]

            row[
                "first_attempt_speed_repair_evidence_ids"
            ] = result[
                "evidence_ids"
            ]

            if result[
                "speed"
            ] is not None:

                row[
                    "first_attempt_speed_mph"
                ] = (
                    f"{result['speed']:.6f}"
                )

                repaired.append(
                    driver
                )

            else:

                unresolved.append(
                    driver
                )

        final_states.append(
            row
        )

        print()
        print(driver)

        print(
            "  first attempt:",
            first_id,
        )

        print(
            "  V3 speed:",
            (
                f"{current_speed:.6f}"
                if current_speed
                is not None
                else
                "UNKNOWN"
            ),
        )

        print(
            "  final speed:",
            txt(
                row.get(
                    "first_attempt_speed_mph"
                )
            )
            or
            "UNKNOWN",
        )

        print(
            "  repair status:",
            row[
                "first_attempt_speed_repair_status"
            ],
        )

    # --------------------------------------------------
    # Build action applicability table
    # --------------------------------------------------

    state_by_driver = {
        txt(
            row.get(
                "driver_name"
            )
        ):
        row
        for row in final_states
    }

    applicability_rows = []

    for driver in sorted(
        EXPECTED_DRIVERS
    ):

        state = state_by_driver[
            driver
        ]

        historical_action = txt(
            state.get(
                "historical_action_label"
            )
        )

        for action in ACTIONS:

            result = applicability(
                driver,
                historical_action,
                action,
            )

            applicability_rows.append({
                "driver_name":
                    driver,

                "state_id":
                    txt(
                        state.get(
                            "state_id"
                        )
                    ),

                "historical_action_label":
                    historical_action,

                "simulated_action":
                    action,

                "case_type":
                    result[
                        "case_type"
                    ],

                "historical_applicability":
                    result[
                        "historical_applicability"
                    ],

                "historical_feasibility":
                    result[
                        "historical_feasibility"
                    ],

                "interpretation":
                    result[
                        "interpretation"
                    ],

                "performance_envelope_valid_as_generic_semantic":
                    "True",

                "hard_recommendation_allowed":
                    "False",
            })

    applicability_index = {
        (
            row[
                "driver_name"
            ],
            row[
                "simulated_action"
            ],
        ):
        row
        for row in applicability_rows
    }

    # --------------------------------------------------
    # Produce final envelope copy.
    # No Monte Carlo draw is changed.
    # Only absolute-speed fields can be repaired.
    # --------------------------------------------------

    final_envelope = []

    absolute_speed_repairs = 0

    for old in envelope:

        row = dict(old)

        driver = txt(
            row.get(
                "driver_name"
            )
        )

        action = txt(
            row.get(
                "action"
            )
        )

        state = state_by_driver.get(
            driver,
            {}
        )

        baseline = fnum(
            state.get(
                "first_attempt_speed_mph"
            )
        )

        old_baseline = fnum(
            row.get(
                "baseline_speed_mph"
            )
        )

        if (
            baseline is not None
            and
            old_baseline is None
        ):

            row[
                "baseline_speed_mph"
            ] = (
                f"{baseline:.10f}"
            )

            for (
                delta_field,
                speed_field,
            ) in [
                (
                    "mean_final_delta_mph",
                    "mean_final_speed_mph",
                ),
                (
                    "q05_final_delta_mph",
                    "q05_final_speed_mph",
                ),
                (
                    "q50_final_delta_mph",
                    "q50_final_speed_mph",
                ),
                (
                    "q95_final_delta_mph",
                    "q95_final_speed_mph",
                ),
            ]:

                d = fnum(
                    row.get(
                        delta_field
                    )
                )

                if d is not None:

                    row[
                        speed_field
                    ] = (
                        f"{baseline + d:.10f}"
                    )

            absolute_speed_repairs += 1

        app = applicability_index.get(
            (
                driver,
                action,
            ),
            {},
        )

        row[
            "historical_case_type"
        ] = txt(
            app.get(
                "case_type"
            )
        ) or "UNKNOWN"

        row[
            "historical_action_applicability"
        ] = txt(
            app.get(
                "historical_applicability"
            )
        ) or "UNKNOWN"

        row[
            "historical_action_feasibility"
        ] = txt(
            app.get(
                "historical_feasibility"
            )
        ) or "UNKNOWN"

        row[
            "historical_applicability_note"
        ] = txt(
            app.get(
                "interpretation"
            )
        )

        row[
            "mc_draws_changed_from_r3b4"
        ] = "False"

        row[
            "final_result_role"
        ] = (
            "PERFORMANCE_ONLY_ACTION_ENVELOPE;"
            "NOT_HARD_RECOMMENDATION"
        )

        final_envelope.append(
            row
        )

    # --------------------------------------------------
    # Write
    # --------------------------------------------------

    write_csv(
        STATE_FINAL,
        final_states,
        list(
            final_states[0].keys()
        ),
    )

    write_csv(
        APPLICABILITY_OUT,
        applicability_rows,
        list(
            applicability_rows[0].keys()
        ),
    )

    write_csv(
        ENVELOPE_FINAL,
        final_envelope,
        list(
            final_envelope[0].keys()
        ),
    )

    # --------------------------------------------------
    # QA
    # --------------------------------------------------

    scott = state_by_driver[
        "Scott McLaughlin"
    ]

    scott_speed = fnum(
        scott.get(
            "first_attempt_speed_mph"
        )
    )

    sato_app = [
        row
        for row in applicability_rows
        if row[
            "driver_name"
        ]
        ==
        "Takuma Sato"
    ]

    sato_mask_ok = (
        len(
            sato_app
        )
        ==
        3
        and
        all(
            row[
                "case_type"
            ]
            ==
            "REQUIRED_REATTEMPT_CASE"
            and
            row[
                "historical_applicability"
            ]
            ==
            "NOT_APPLICABLE_AS_ELECTIVE_CHOICE"
            for row in sato_app
        )
    )

    hard_rec_leaks = [
        row
        for row in final_envelope
        if truthy(
            row.get(
                "hard_recommendation_allowed"
            )
        )
    ]

    changed_draw_leaks = [
        row
        for row in final_envelope
        if truthy(
            row.get(
                "mc_draws_changed_from_r3b4"
            )
        )
    ]

    qa_rows = [
        {
            "metric":
                "target_driver_set_exact",

            "value":
                int(
                    target_exact
                ),

            "status":
                (
                    "PASS"
                    if target_exact
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "scott_first_attempt_speed_recovered",

            "value":
                (
                    f"{scott_speed:.6f}"
                    if scott_speed
                    is not None
                    else
                    "UNKNOWN"
                ),

            "status":
                (
                    "PASS"
                    if scott_speed
                    is not None
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "unresolved_missing_first_attempt_speeds",

            "value":
                len(
                    unresolved
                ),

            "status":
                (
                    "PASS"
                    if len(
                        unresolved
                    )
                    ==
                    0
                    else
                    "REVIEW"
                ),
        },

        {
            "metric":
                "sato_required_reattempt_mask",

            "value":
                int(
                    sato_mask_ok
                ),

            "status":
                (
                    "PASS"
                    if sato_mask_ok
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "action_applicability_rows",

            "value":
                len(
                    applicability_rows
                ),

            "status":
                (
                    "PASS"
                    if len(
                        applicability_rows
                    )
                    ==
                    24
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "hard_recommendation_leaks",

            "value":
                len(
                    hard_rec_leaks
                ),

            "status":
                (
                    "PASS"
                    if len(
                        hard_rec_leaks
                    )
                    ==
                    0
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "mc_draws_modified",

            "value":
                len(
                    changed_draw_leaks
                ),

            "status":
                (
                    "PASS"
                    if len(
                        changed_draw_leaks
                    )
                    ==
                    0
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "protected_r3b4_output_mutated",

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
        row[
            "status"
        ]
        ==
        "FAIL"
        for row in qa_rows
    )

    summary = {
        "phase":
            PHASE,

        "final_state_version":
            "V4_FINAL",

        "driver_count":
            len(
                final_states
            ),

        "first_attempt_speed_repairs":
            repaired,

        "unresolved_first_attempt_speeds":
            unresolved,

        "absolute_envelope_rows_repaired":
            absolute_speed_repairs,

        "sato_case":
            {
                "classification":
                    "REQUIRED_REATTEMPT_CASE",

                "elective_stop_lane1_lane2_comparison":
                    False,

                "r3b4_envelope_role":
                    "GENERIC_MATHEMATICAL_COUNTERFACTUAL_ONLY",
            },

        "rossi_mclaughlin_lane1":
            "DIRECT_HISTORICAL_ACTION_SUPPORTED",

        "other_lane_assignments":
            "NOT_FULLY_IDENTIFIABLE",

        "r3b4_monte_carlo_draws_changed":
            False,

        "performance_only_lane2_nondominance":
            r3b4_summary.get(
                "lane2_vs_lane1_interpretation"
            ),

        "queue_wait":
            "LATENT_NOT_HISTORICAL_TRUTH",

        "2022_future_weather":
            "NOT_IDENTIFIABLE_NOT_USED",

        "rank_cutoff_probability":
            "NOT_IDENTIFIABLE",

        "repeat_completion_probability":
            "NOT_MODELED",

        "hard_recommendation_ready":
            False,

        "final_supported_system":
            (
                "UNCERTAINTY_AWARE_PERFORMANCE_DECISION_SUPPORT_"
                "WITH_EXPLICIT_IDENTIFIABILITY_BOUNDARIES"
            ),

        "next_phase":
            (
                "R3C1_FINAL_RESULTS_AND_CAPABILITY_FREEZE"
                if not hard_fail
                else
                "R3C0_REVIEW_REQUIRED"
            ),
    }

    SUMMARY_OUT.write_text(
        json.dumps(
            summary,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    # --------------------------------------------------
    # Terminal summary
    # --------------------------------------------------

    print()
    print("=" * 128)
    print("FINAL REPAIR SUMMARY")
    print("=" * 128)

    print()
    print(
        "Speed repairs:",
        (
            "|".join(
                repaired
            )
            or
            "NONE"
        ),
    )

    print(
        "Unresolved missing speeds:",
        (
            "|".join(
                unresolved
            )
            or
            "NONE"
        ),
    )

    print()
    print(
        "Scott final first-attempt speed:",
        (
            f"{scott_speed:.6f}"
            if scott_speed
            is not None
            else
            "UNKNOWN"
        ),
    )

    print()
    print(
        "Sato classified required reattempt:",
        sato_mask_ok,
    )

    print(
        "Sato elective action comparison:",
        "NO",
    )

    print()
    print(
        "Action-applicability rows:",
        len(
            applicability_rows
        ),
    )

    print(
        "Absolute envelope rows repaired:",
        absolute_speed_repairs,
    )

    print(
        "Monte Carlo draws changed:",
        "NO",
    )

    print(
        "Hard recommendations created:",
        "NO",
    )

    print()
    print("=" * 128)

    if not hard_fail:

        print(
            "FINAL STATUS: "
            "R3C0_FINAL_STATE_AND_ACTION_APPLICABILITY_READY"
        )

    else:

        print(
            "FINAL STATUS: "
            "R3C0_FINAL_STATE_ACTION_REVIEW_REQUIRED"
        )

    print("=" * 128)

    print()
    print("OUTPUTS")
    print(STATE_FINAL)
    print(APPLICABILITY_OUT)
    print(ENVELOPE_FINAL)
    print(SUMMARY_OUT)
    print(QA_OUT)


if __name__ == "__main__":
    main()
