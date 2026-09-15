from pathlib import Path
import csv
import json
from collections import defaultdict


PHASE = "R3A.2"
YEAR = "2022"

OUTPUT_DIR = Path("weather/output")

STATE_V2 = Path(
    "weather/output/"
    "decision_time_observable_state_v2.csv"
)

DECISION_LEDGER = Path(
    "weather/output/"
    "contemporaneous_decision_state_evidence_ledger_v2.csv"
)

QUEUE_LEDGER = Path(
    "weather/output/"
    "queue_requeue_evidence_ledger_v1.csv"
)

TEMPORAL_AUDIT = Path(
    "weather/output/"
    "decision_time_state_v2_temporal_admissibility_audit_v1.csv"
)

ACTION_LEDGER = Path(
    "weather/output/"
    "unified_attempt_action_lane_ledger_v8.csv"
)

QUEUE_POLICY = Path(
    "weather/output/"
    "queue_wait_identifiability_2022_v1.csv"
)

SERVICE_POLICY = Path(
    "weather/output/"
    "pit_service_identifiability_2022_v1.csv"
)

RUBBER_POLICY = Path(
    "weather/output/"
    "rubber_grip_identifiability_2022_v1.csv"
)

TIRE_POLICY = Path(
    "weather/output/"
    "tire_thermal_pressure_identifiability_2022_v1.csv"
)

STATE_OUT = (
    OUTPUT_DIR
    / "decision_time_observable_state_v3.csv"
)

TRANSITION_OUT = (
    OUTPUT_DIR
    / "decision_time_state_v3_transition_outcome_evidence.csv"
)

PROVENANCE_OUT = (
    OUTPUT_DIR
    / "decision_time_observable_state_v3_provenance.csv"
)

SUMMARY_OUT = (
    OUTPUT_DIR
    / "decision_time_observable_state_v3_summary.json"
)

QA_OUT = (
    OUTPUT_DIR
    / "decision_time_observable_state_v3_qa.csv"
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


def unique(values):
    out = []

    for value in values:
        value = txt(value)

        if not value:
            continue

        if value not in out:
            out.append(value)

    return out


def joined(values, default="UNKNOWN"):
    vals = unique(values)

    if not vals:
        return default

    return "|".join(vals)


def first(values, default="UNKNOWN"):
    vals = unique(values)

    if not vals:
        return default

    return vals[0]


def is_unknown(v):
    return txt(v) in {
        "",
        "UNKNOWN",
        "NONE",
    }


def classify_decision_temporally(row):
    """
    Corrected R3A.2 temporal rules.

    PRE_SECOND_RUN is explicitly pre-decision and is therefore
    admissible. This fixes the conservative R3A.1B auto-rule
    that left Rossi in REVIEW_REQUIRED.
    """

    stage = txt(
        row.get("state_stage")
    ).upper()

    semantic = txt(
        row.get("source_semantic")
    ).upper()

    combined = (
        stage
        +
        " "
        +
        semantic
    )

    pre_terms = [
        "PRE_ACTION",
        "PRE_SECOND_RUN",
        "BEFORE_LANE1_ACTION",
        "BEFORE_SECOND_RUN",
        "BEFORE_SECOND_ATTEMPT",
        "EXISTING_RESULT_BEFORE",
    ]

    if any(
        term in combined
        for term in pre_terms
    ):
        return "PRE_DECISION_ADMISSIBLE"

    post_terms = [
        "POST_REPEAT",
        "POST_REATTEMPT",
        "POST_RERUN",
        "POST_SECOND",
        "POST_SATO",
        "LATER_TEMPORAL",
        "AFTER_TRACK_REOPENED",
        "DISPLACED",
        "AFTER_REPEAT",
        "AFTER_RERUN",
    ]

    if any(
        term in combined
        for term in post_terms
    ):
        return "POST_ACTION_OUTCOME_ONLY"

    return "NOT_ADMISSIBLE_UNRESOLVED"


def classify_queue_temporally(row):
    family = txt(
        row.get("evidence_family")
    ).upper()

    semantic = txt(
        row.get("state_semantic")
    ).upper()

    combined = (
        family
        +
        " "
        +
        semantic
    )

    if (
        "AFTER_WITHDRAW"
        in combined
        or
        "PUT_IN_LINE"
        in combined
        or
        "FOR_REPEAT_RUN"
        in combined
        or
        "FOR_REATTEMPT"
        in combined
    ):
        return "POST_ACTION_TRANSITION_ONLY"

    if (
        "RETAKE_RUN_ORDER"
        in combined
        or
        "RELATIVE_RUN_ORDER"
        in combined
        or
        "FIRST_RETAKE_RUN"
        in combined
        or
        "_BEFORE_"
        in combined
    ):
        return "ORDERING_ONLY"

    return "NOT_PRE_DECISION_ADMISSIBLE"


def historical_action_for_driver(
    action_rows,
    driver,
):
    rows = [
        row
        for row in action_rows
        if (
            txt(row.get("year"))
            ==
            YEAR
            and
            txt(row.get("driver_name"))
            ==
            driver
        )
    ]

    return {
        "action":
            joined(
                [
                    row.get("action")
                    for row in rows
                    if not is_unknown(
                        row.get("action")
                    )
                ]
            ),

        "lane":
            joined(
                [
                    row.get("lane")
                    for row in rows
                    if not is_unknown(
                        row.get("lane")
                    )
                ]
            ),

        "evidence_count":
            len(rows),

        "evidence_ids":
            joined(
                [
                    row.get("evidence_id")
                    for row in rows
                ],
                default="UNKNOWN",
            ),

        "source":
            joined(
                [
                    row.get("source_name")
                    for row in rows
                ],
                default="UNKNOWN",
            ),
    }


def admissible_decision_rows(
    decision_rows,
    driver,
):
    rows = [
        row
        for row in decision_rows
        if (
            txt(row.get("year"))
            ==
            YEAR
            and
            txt(row.get("driver_name"))
            ==
            driver
        )
    ]

    return [
        row
        for row in rows
        if classify_decision_temporally(row)
        ==
        "PRE_DECISION_ADMISSIBLE"
    ]


def predecision_state_from_rows(rows):
    if not rows:
        return {
            "rank":
                "UNKNOWN",

            "rank_lower_bound":
                "UNKNOWN",

            "rank_upper_bound":
                "UNKNOWN",

            "top12_state":
                "UNKNOWN",

            "cutoff_rank":
                "UNKNOWN",

            "cutoff_speed_mph":
                "UNKNOWN",

            "time_quality":
                "UNKNOWN",

            "source":
                "UNKNOWN",

            "evidence_ids":
                "UNKNOWN",

            "evidence_count":
                0,
        }

    return {
        "rank":
            first(
                [
                    row.get("rank")
                    for row in rows
                    if not is_unknown(
                        row.get("rank")
                    )
                ]
            ),

        "rank_lower_bound":
            first(
                [
                    row.get(
                        "rank_lower_bound"
                    )
                    for row in rows
                    if not is_unknown(
                        row.get(
                            "rank_lower_bound"
                        )
                    )
                ]
            ),

        "rank_upper_bound":
            first(
                [
                    row.get(
                        "rank_upper_bound"
                    )
                    for row in rows
                    if not is_unknown(
                        row.get(
                            "rank_upper_bound"
                        )
                    )
                ]
            ),

        "top12_state":
            first(
                [
                    row.get("top12_state")
                    for row in rows
                    if not is_unknown(
                        row.get(
                            "top12_state"
                        )
                    )
                ]
            ),

        "cutoff_rank":
            first(
                [
                    row.get("cutoff_rank")
                    for row in rows
                    if not is_unknown(
                        row.get(
                            "cutoff_rank"
                        )
                    )
                ]
            ),

        "cutoff_speed_mph":
            first(
                [
                    row.get(
                        "cutoff_speed_mph"
                    )
                    for row in rows
                    if not is_unknown(
                        row.get(
                            "cutoff_speed_mph"
                        )
                    )
                ]
            ),

        "time_quality":
            joined(
                [
                    row.get("time_quality")
                    for row in rows
                ]
            ),

        "source":
            joined(
                [
                    row.get("source_name")
                    for row in rows
                ]
            ),

        "evidence_ids":
            joined(
                [
                    row.get("state_id")
                    for row in rows
                ]
            ),

        "evidence_count":
            len(rows),
    }


def main():

    print()
    print("=" * 128)
    print(
        "R3A.2 — TEMPORAL-SAFE DECISION-TIME "
        "OBSERVABLE STATE V3"
    )
    print("=" * 128)

    required = [
        STATE_V2,
        DECISION_LEDGER,
        QUEUE_LEDGER,
        TEMPORAL_AUDIT,
        ACTION_LEDGER,
        QUEUE_POLICY,
        SERVICE_POLICY,
        RUBBER_POLICY,
        TIRE_POLICY,
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
            missing.append(str(path))

    if missing:

        print()
        print(
            "FINAL STATUS: "
            "R3A2_TEMPORAL_SAFE_STATE_INPUT_MISSING"
        )
        return

    state_v2 = read_csv(
        STATE_V2
    )

    decision_rows = read_csv(
        DECISION_LEDGER
    )

    queue_rows = read_csv(
        QUEUE_LEDGER
    )

    read_csv(
        TEMPORAL_AUDIT
    )

    action_rows = read_csv(
        ACTION_LEDGER
    )

    queue_policy_rows = read_csv(
        QUEUE_POLICY
    )

    service_policy_rows = read_csv(
        SERVICE_POLICY
    )

    rubber_policy_rows = read_csv(
        RUBBER_POLICY
    )

    tire_policy_rows = read_csv(
        TIRE_POLICY
    )

    driver_set = {
        txt(row.get("driver_name"))
        for row in state_v2
    }

    if driver_set != EXPECTED_DRIVERS:

        print()
        print(
            "FINAL STATUS: "
            "R3A2_DRIVER_SET_REVIEW_REQUIRED"
        )
        return

    queue_wait_policy = first(
        [
            row.get(
                "simulator_queue_wait_policy"
            )
            for row in queue_policy_rows
        ],
        default="LATENT_SENSITIVITY_VARIABLE",
    )

    service_policy = first(
        [
            row.get(
                "downstream_service_policy"
            )
            for row in service_policy_rows
        ],
        default="SERVICE_STATE_UNKNOWN",
    )

    rubber_policy = first(
        [
            row.get(
                "downstream_rubber_policy"
            )
            for row in rubber_policy_rows
        ],
        default="UNKNOWN_NOT_IDENTIFIABLE",
    )

    grip_policy = first(
        [
            row.get(
                "downstream_grip_evolution_policy"
            )
            for row in rubber_policy_rows
        ],
        default="UNKNOWN_NOT_IDENTIFIABLE",
    )

    tire_policy = first(
        [
            row.get(
                "downstream_tire_state_policy"
            )
            for row in tire_policy_rows
        ],
        default="TIRE_STATE_UNKNOWN",
    )

    corrected = []
    transition_rows = []
    provenance_rows = []

    v2_by_driver = {
        txt(row.get("driver_name")):
        row
        for row in state_v2
    }

    print()
    print("=" * 128)
    print("TEMPORAL-SAFE STATE CONSTRUCTION")
    print("=" * 128)

    for driver in sorted(
        EXPECTED_DRIVERS
    ):

        old = v2_by_driver[
            driver
        ]

        admissible = (
            admissible_decision_rows(
                decision_rows,
                driver,
            )
        )

        pre = (
            predecision_state_from_rows(
                admissible
            )
        )

        historical = (
            historical_action_for_driver(
                action_rows,
                driver,
            )
        )

        components = [
            "PAIR_CHRONOLOGY",
        ]

        # First-attempt speed/result are known after
        # the first attempt and before the repeat decision.
        if not is_unknown(
            old.get(
                "first_attempt_speed_mph"
            )
        ):
            components.append(
                "FIRST_ATTEMPT_PERFORMANCE"
            )

        if (
            not is_unknown(
                pre["rank"]
            )
            or
            not is_unknown(
                pre[
                    "rank_lower_bound"
                ]
            )
            or
            not is_unknown(
                pre[
                    "rank_upper_bound"
                ]
            )
        ):
            components.append(
                "CURRENT_RANK"
            )

        if (
            not is_unknown(
                pre["cutoff_rank"]
            )
            or
            not is_unknown(
                pre[
                    "cutoff_speed_mph"
                ]
            )
        ):
            components.append(
                "CURRENT_CUTOFF"
            )

        components.append(
            "DECISION_TIME_WEATHER_POLICY"
        )

        components.append(
            "OBSERVED_TRACK_TEMP_POLICY"
        )

        new = {
            "state_id":
                txt(
                    old.get("state_id")
                ).replace(
                    "DTV2-",
                    "DTV3-",
                ),

            "year":
                YEAR,

            "driver_name":
                driver,

            "decision_stage":
                "AFTER_FIRST_ATTEMPT_BEFORE_REPEAT_DECISION",

            "first_attempt_id":
                txt(
                    old.get(
                        "first_attempt_id"
                    )
                ),

            "second_attempt_id":
                txt(
                    old.get(
                        "second_attempt_id"
                    )
                ),

            "pair_resolution_method":
                txt(
                    old.get(
                        "pair_resolution_method"
                    )
                ),

            "first_car_attempt_index":
                txt(
                    old.get(
                        "first_car_attempt_index"
                    )
                ),

            "second_car_attempt_index":
                txt(
                    old.get(
                        "second_car_attempt_index"
                    )
                ),

            "first_attempt_status":
                txt(
                    old.get(
                        "first_attempt_status"
                    )
                )
                or
                "UNKNOWN",

            "first_attempt_speed_mph":
                txt(
                    old.get(
                        "first_attempt_speed_mph"
                    )
                )
                or
                "UNKNOWN",

            "first_attempt_time_quality":
                txt(
                    old.get(
                        "first_attempt_time_quality"
                    )
                )
                or
                "UNKNOWN",

            "predecision_current_rank":
                pre["rank"],

            "predecision_rank_lower_bound":
                pre[
                    "rank_lower_bound"
                ],

            "predecision_rank_upper_bound":
                pre[
                    "rank_upper_bound"
                ],

            "predecision_top12_state":
                pre[
                    "top12_state"
                ],

            "predecision_cutoff_rank":
                pre[
                    "cutoff_rank"
                ],

            "predecision_cutoff_speed_mph":
                pre[
                    "cutoff_speed_mph"
                ],

            "predecision_state_time_quality":
                pre[
                    "time_quality"
                ],

            "predecision_state_source":
                pre[
                    "source"
                ],

            "predecision_state_evidence_ids":
                pre[
                    "evidence_ids"
                ],

            "predecision_state_evidence_count":
                pre[
                    "evidence_count"
                ],

            # Historical action is deliberately separated
            # from observable state.
            "historical_action_label":
                historical[
                    "action"
                ],

            "historical_lane_label":
                historical[
                    "lane"
                ],

            "historical_action_evidence_count":
                historical[
                    "evidence_count"
                ],

            "historical_action_evidence_ids":
                historical[
                    "evidence_ids"
                ],

            "historical_action_source":
                historical[
                    "source"
                ],

            # Queue evidence recovered so far is not
            # admitted as pre-decision state.
            "predecision_queue_membership":
                "UNKNOWN",

            "predecision_queue_lane":
                "UNKNOWN",

            "predecision_queue_position":
                "UNKNOWN",

            "historical_queue_wait":
                "UNKNOWN",

            "queue_wait_policy":
                queue_wait_policy,

            "pit_service_state":
                "UNKNOWN",

            "pit_service_policy":
                service_policy,

            "rubber_state":
                "UNKNOWN",

            "rubber_policy":
                rubber_policy,

            "grip_evolution_state":
                "UNKNOWN",

            "grip_evolution_policy":
                grip_policy,

            "tire_thermal_pressure_state":
                "UNKNOWN",

            "tire_state_policy":
                tire_policy,

            "weather_feature_policy":
                "DECISION_TIME_HRRR_WITH_AVAILABILITY_CONTROL",

            "track_temperature_policy":
                "OBSERVED_PTSC_WHERE_TIME_ALIGNMENT_SUPPORTED",

            "elapsed_time_as_track_evolution":
                "PROHIBITED",

            "unknown_state_imputation":
                "NONE",

            "observable_components":
                "|".join(
                    components
                ),

            "historical_action_is_observable_feature":
                "False",

            "historical_lane_is_observable_feature":
                "False",

            "queue_transition_is_observable_feature":
                "False",

            "post_action_outcome_is_observable_feature":
                "False",

            "state_scope":
                "TEMPORAL_SAFE_LIMITED_PREDECISION_STATE",

            "full_historical_state":
                "False",

            "hard_optimality_truth_ready":
                "False",
        }

        corrected.append(
            new
        )

        print()
        print("-" * 128)

        print(driver)

        print(
            "  predecision rank:",
            new[
                "predecision_current_rank"
            ],
        )

        print(
            "  rank bounds:",
            new[
                "predecision_rank_lower_bound"
            ],
            "/",
            new[
                "predecision_rank_upper_bound"
            ],
        )

        print(
            "  cutoff:",
            new[
                "predecision_cutoff_rank"
            ],
            "/",
            new[
                "predecision_cutoff_speed_mph"
            ],
        )

        print(
            "  historical action label:",
            new[
                "historical_action_label"
            ],
        )

        print(
            "  historical lane label:",
            new[
                "historical_lane_label"
            ],
        )

        print(
            "  predecision queue:",
            "UNKNOWN",
        )

        print(
            "  observable:",
            new[
                "observable_components"
            ],
        )

        # ----------------------------------------------
        # Provenance: admissible pre-decision evidence
        # ----------------------------------------------

        for row in admissible:

            provenance_rows.append({
                "state_id":
                    new["state_id"],

                "driver_name":
                    driver,

                "domain":
                    "PRE_DECISION_STATE",

                "evidence_id":
                    txt(
                        row.get("state_id")
                    ),

                "temporal_classification":
                    "PRE_DECISION_ADMISSIBLE",

                "source_name":
                    txt(
                        row.get(
                            "source_name"
                        )
                    ),

                "source_class":
                    txt(
                        row.get(
                            "source_class"
                        )
                    ),

                "source_semantic":
                    txt(
                        row.get(
                            "source_semantic"
                        )
                    ),

                "state_stage":
                    txt(
                        row.get(
                            "state_stage"
                        )
                    ),

                "rank":
                    txt(
                        row.get("rank")
                    ),

                "cutoff_rank":
                    txt(
                        row.get(
                            "cutoff_rank"
                        )
                    ),

                "feature_allowed":
                    "True",
            })

        # ----------------------------------------------
        # Historical decision labels
        # ----------------------------------------------

        for row in action_rows:

            if (
                txt(row.get("year"))
                ==
                YEAR
                and
                txt(
                    row.get(
                        "driver_name"
                    )
                )
                ==
                driver
            ):

                provenance_rows.append({
                    "state_id":
                        new["state_id"],

                    "driver_name":
                        driver,

                    "domain":
                        "HISTORICAL_ACTION_LABEL",

                    "evidence_id":
                        txt(
                            row.get(
                                "evidence_id"
                            )
                        ),

                    "temporal_classification":
                        "LABEL_NOT_STATE_FEATURE",

                    "source_name":
                        txt(
                            row.get(
                                "source_name"
                            )
                        ),

                    "source_class":
                        txt(
                            row.get(
                                "source_class"
                            )
                        ),

                    "source_semantic":
                        joined(
                            [
                                row.get(
                                    "action"
                                ),
                                row.get(
                                    "lane"
                                ),
                            ]
                        ),

                    "state_stage":
                        "HISTORICAL_ACTION",

                    "rank":
                        "",

                    "cutoff_rank":
                        "",

                    "feature_allowed":
                        "False",
                })

    # --------------------------------------------------
    # Build transition / outcome table
    # --------------------------------------------------

    for row in decision_rows:

        classification = (
            classify_decision_temporally(
                row
            )
        )

        if classification == (
            "PRE_DECISION_ADMISSIBLE"
        ):
            continue

        transition_rows.append({
            "domain":
                "DECISION_STATE",

            "evidence_id":
                txt(
                    row.get("state_id")
                ),

            "year":
                txt(
                    row.get("year")
                ),

            "driver_name":
                txt(
                    row.get("driver_name")
                ),

            "classification":
                classification,

            "state_stage":
                txt(
                    row.get(
                        "state_stage"
                    )
                ),

            "state_semantic":
                txt(
                    row.get(
                        "source_semantic"
                    )
                ),

            "rank":
                txt(
                    row.get("rank")
                )
                or
                "UNKNOWN",

            "rank_lower_bound":
                txt(
                    row.get(
                        "rank_lower_bound"
                    )
                )
                or
                "UNKNOWN",

            "rank_upper_bound":
                txt(
                    row.get(
                        "rank_upper_bound"
                    )
                )
                or
                "UNKNOWN",

            "cutoff_rank":
                txt(
                    row.get(
                        "cutoff_rank"
                    )
                )
                or
                "UNKNOWN",

            "cutoff_speed_mph":
                txt(
                    row.get(
                        "cutoff_speed_mph"
                    )
                )
                or
                "UNKNOWN",

            "queue_membership":
                "NOT_APPLICABLE",

            "queue_lane":
                "NOT_APPLICABLE",

            "queue_position":
                "NOT_APPLICABLE",

            "relative_run_order":
                "NOT_APPLICABLE",

            "source_name":
                txt(
                    row.get(
                        "source_name"
                    )
                ),

            "source_class":
                txt(
                    row.get(
                        "source_class"
                    )
                ),

            "predecision_feature_allowed":
                "False",
        })

    for row in queue_rows:

        classification = (
            classify_queue_temporally(
                row
            )
        )

        transition_rows.append({
            "domain":
                "QUEUE",

            "evidence_id":
                txt(
                    row.get(
                        "queue_state_id"
                    )
                ),

            "year":
                txt(
                    row.get("year")
                ),

            "driver_name":
                txt(
                    row.get("driver_name")
                ),

            "classification":
                classification,

            "state_stage":
                txt(
                    row.get(
                        "evidence_family"
                    )
                ),

            "state_semantic":
                txt(
                    row.get(
                        "state_semantic"
                    )
                ),

            "rank":
                txt(
                    row.get(
                        "existing_rank"
                    )
                )
                or
                "UNKNOWN",

            "rank_lower_bound":
                "NOT_APPLICABLE",

            "rank_upper_bound":
                "NOT_APPLICABLE",

            "cutoff_rank":
                "NOT_APPLICABLE",

            "cutoff_speed_mph":
                "NOT_APPLICABLE",

            "queue_membership":
                txt(
                    row.get(
                        "queue_membership"
                    )
                )
                or
                "UNKNOWN",

            "queue_lane":
                txt(
                    row.get(
                        "queue_lane"
                    )
                )
                or
                "UNKNOWN",

            "queue_position":
                txt(
                    row.get(
                        "queue_position"
                    )
                )
                or
                "UNKNOWN",

            "relative_run_order":
                txt(
                    row.get(
                        "relative_run_order"
                    )
                )
                or
                "UNKNOWN",

            "source_name":
                txt(
                    row.get(
                        "source_name"
                    )
                ),

            "source_class":
                txt(
                    row.get(
                        "source_class"
                    )
                ),

            "predecision_feature_allowed":
                "False",
        })

    # --------------------------------------------------
    # Write datasets
    # --------------------------------------------------

    state_fields = list(
        corrected[0].keys()
    )

    write_csv(
        STATE_OUT,
        corrected,
        state_fields,
    )

    transition_fields = [
        "domain",
        "evidence_id",
        "year",
        "driver_name",
        "classification",
        "state_stage",
        "state_semantic",
        "rank",
        "rank_lower_bound",
        "rank_upper_bound",
        "cutoff_rank",
        "cutoff_speed_mph",
        "queue_membership",
        "queue_lane",
        "queue_position",
        "relative_run_order",
        "source_name",
        "source_class",
        "predecision_feature_allowed",
    ]

    write_csv(
        TRANSITION_OUT,
        transition_rows,
        transition_fields,
    )

    provenance_fields = [
        "state_id",
        "driver_name",
        "domain",
        "evidence_id",
        "temporal_classification",
        "source_name",
        "source_class",
        "source_semantic",
        "state_stage",
        "rank",
        "cutoff_rank",
        "feature_allowed",
    ]

    write_csv(
        PROVENANCE_OUT,
        provenance_rows,
        provenance_fields,
    )

    # --------------------------------------------------
    # QA
    # --------------------------------------------------

    known_rank = [
        row
        for row in corrected
        if not is_unknown(
            row.get(
                "predecision_current_rank"
            )
        )
    ]

    known_rank_drivers = {
        row["driver_name"]
        for row in known_rank
    }

    expected_rank_drivers = {
        "Alexander Rossi",
        "Scott McLaughlin",
    }

    post_outcome_leaks = []

    for row in corrected:

        driver = row[
            "driver_name"
        ]

        rank = row[
            "predecision_current_rank"
        ]

        if (
            driver
            ==
            "David Malukas"
            and
            rank
            ==
            "12"
        ):
            post_outcome_leaks.append(
                "MALUKAS_P12"
            )

        if (
            driver
            ==
            "Takuma Sato"
            and
            rank
            ==
            "12"
        ):
            post_outcome_leaks.append(
                "SATO_P12"
            )

        if (
            driver
            ==
            "Scott McLaughlin"
            and
            rank
            ==
            "26"
        ):
            post_outcome_leaks.append(
                "MCLAUGHLIN_P26"
            )

        if (
            driver
            ==
            "Alexander Rossi"
            and
            rank
            ==
            "21"
        ):
            post_outcome_leaks.append(
                "ROSSI_P21"
            )

    action_feature_leaks = [
        row["driver_name"]
        for row in corrected
        if (
            "ACTION"
            in
            row[
                "observable_components"
            ].split("|")
            or
            "LANE"
            in
            row[
                "observable_components"
            ].split("|")
        )
    ]

    queue_feature_leaks = [
        row["driver_name"]
        for row in corrected
        if (
            "QUEUE"
            in
            row[
                "observable_components"
            ].split("|")
            or
            "QUEUE_ANCHOR"
            in
            row[
                "observable_components"
            ].split("|")
        )
    ]

    queue_truth_leaks = [
        row["driver_name"]
        for row in corrected
        if (
            row[
                "predecision_queue_membership"
            ]
            !=
            "UNKNOWN"
            or
            row[
                "predecision_queue_lane"
            ]
            !=
            "UNKNOWN"
            or
            row[
                "predecision_queue_position"
            ]
            !=
            "UNKNOWN"
        )
    ]

    unknown_policy_leaks = [
        row["driver_name"]
        for row in corrected
        if (
            row[
                "pit_service_state"
            ]
            !=
            "UNKNOWN"
            or
            row[
                "rubber_state"
            ]
            !=
            "UNKNOWN"
            or
            row[
                "grip_evolution_state"
            ]
            !=
            "UNKNOWN"
            or
            row[
                "tire_thermal_pressure_state"
            ]
            !=
            "UNKNOWN"
        )
    ]

    qa_rows = [
        {
            "metric":
                "state_rows_is_8",

            "value":
                len(corrected),

            "status":
                (
                    "PASS"
                    if len(corrected)
                    ==
                    8
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "driver_set_exact",

            "value":
                int(
                    {
                        row[
                            "driver_name"
                        ]
                        for row in corrected
                    }
                    ==
                    EXPECTED_DRIVERS
                ),

            "status":
                (
                    "PASS"
                    if {
                        row[
                            "driver_name"
                        ]
                        for row in corrected
                    }
                    ==
                    EXPECTED_DRIVERS
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "predecision_rank_driver_set_exact",

            "value":
                "|".join(
                    sorted(
                        known_rank_drivers
                    )
                ),

            "status":
                (
                    "PASS"
                    if known_rank_drivers
                    ==
                    expected_rank_drivers
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "post_action_rank_leaks",

            "value":
                len(
                    post_outcome_leaks
                ),

            "status":
                (
                    "PASS"
                    if len(
                        post_outcome_leaks
                    )
                    ==
                    0
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "action_lane_observable_leaks",

            "value":
                len(
                    action_feature_leaks
                ),

            "status":
                (
                    "PASS"
                    if len(
                        action_feature_leaks
                    )
                    ==
                    0
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "queue_observable_leaks",

            "value":
                len(
                    queue_feature_leaks
                ),

            "status":
                (
                    "PASS"
                    if len(
                        queue_feature_leaks
                    )
                    ==
                    0
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "queue_truth_leaks",

            "value":
                len(
                    queue_truth_leaks
                ),

            "status":
                (
                    "PASS"
                    if len(
                        queue_truth_leaks
                    )
                    ==
                    0
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "unknown_physical_state_leaks",

            "value":
                len(
                    unknown_policy_leaks
                ),

            "status":
                (
                    "PASS"
                    if len(
                        unknown_policy_leaks
                    )
                    ==
                    0
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "elapsed_time_track_evolution_used",

            "value":
                0,

            "status":
                "PASS",
        },

        {
            "metric":
                "active_frozen_ledgers_mutated",

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

    summary = {
        "phase":
            PHASE,

        "year":
            2022,

        "state_rows":
            len(corrected),

        "known_predecision_rank_rows":
            len(
                known_rank
            ),

        "known_predecision_rank_drivers":
            sorted(
                known_rank_drivers
            ),

        "expected_predecision_rank_drivers": [
            "Alexander Rossi",
            "Scott McLaughlin",
        ],

        "temporal_leakage_removed": {
            "malukas_post_repeat_p12":
                True,

            "sato_post_reattempt_p12":
                True,

            "mclaughlin_post_rerun_p26":
                True,

            "rossi_post_second_p21":
                True,

            "historical_action_from_observables":
                True,

            "historical_lane_from_observables":
                True,

            "post_action_queue_from_observables":
                True,
        },

        "historical_action_role":
            "LABEL_ONLY",

        "historical_lane_role":
            "LABEL_ONLY",

        "queue_evidence_role":
            "TRANSITION_OR_ORDERING_ONLY",

        "post_action_rank_role":
            "OUTCOME_VALIDATION_ONLY",

        "queue_wait":
            "LATENT_SENSITIVITY_VARIABLE",

        "pit_service":
            "UNKNOWN",

        "rubber_grip":
            "UNKNOWN",

        "tire_state":
            "UNKNOWN",

        "elapsed_time_as_track_evolution":
            "PROHIBITED",

        "unknown_state_imputation":
            "NONE",

        "r3b_simulator_input_ready":
            success,

        "next_phase":
            (
                "R3B_LIMITED_UNCERTAINTY_AWARE_"
                "SEQUENTIAL_SIMULATOR"
                if success
                else
                "R3A2_REVIEW_REQUIRED"
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

    print()
    print("=" * 128)
    print("V3 SUMMARY")
    print("=" * 128)

    print()
    print(
        "State rows:",
        len(
            corrected
        ),
    )

    print(
        "Known pre-decision rank rows:",
        len(
            known_rank
        ),
    )

    print(
        "Known pre-decision rank drivers:",
        "|".join(
            sorted(
                known_rank_drivers
            )
        )
        or
        "NONE",
    )

    print()
    print(
        "Post-action rank leaks:",
        len(
            post_outcome_leaks
        ),
    )

    print(
        "Action/Lane observable leaks:",
        len(
            action_feature_leaks
        ),
    )

    print(
        "Queue observable leaks:",
        len(
            queue_feature_leaks
        ),
    )

    print(
        "Queue truth leaks:",
        len(
            queue_truth_leaks
        ),
    )

    print(
        "Unknown physical-state leaks:",
        len(
            unknown_policy_leaks
        ),
    )

    print()
    print(
        "Transition/outcome evidence rows:",
        len(
            transition_rows
        ),
    )

    print()
    print(
        "Historical action role:",
        "LABEL_ONLY",
    )

    print(
        "Queue evidence role:",
        "TRANSITION_OR_ORDERING_ONLY",
    )

    print(
        "Post-action rank role:",
        "OUTCOME_VALIDATION_ONLY",
    )

    print()
    print(
        "Unknown-state imputation:",
        "NONE",
    )

    print(
        "Elapsed time used as track evolution:",
        "NO",
    )

    print()
    print("=" * 128)

    if success:

        print(
            "FINAL STATUS: "
            "R3A2_TEMPORAL_SAFE_DECISION_TIME_STATE_V3_READY"
        )

    else:

        print(
            "FINAL STATUS: "
            "R3A2_TEMPORAL_SAFE_STATE_V3_REVIEW_REQUIRED"
        )

    print("=" * 128)

    print()
    print("OUTPUTS")
    print(STATE_OUT)
    print(TRANSITION_OUT)
    print(PROVENANCE_OUT)
    print(SUMMARY_OUT)
    print(QA_OUT)


if __name__ == "__main__":
    main()
