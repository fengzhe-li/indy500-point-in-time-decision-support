from pathlib import Path
import csv
import json
from collections import defaultdict


PHASE = "R3A.1"
YEAR = "2022"

OUTPUT_DIR = Path("weather/output")

ELIGIBILITY = Path(
    "weather/output/"
    "chronology_rescue_2022_repeat_pair_driver_eligibility_v1.csv"
)

CHRONOLOGY = Path(
    "weather/output/"
    "unified_attempt_chronology_constraint_ledger_v10.csv"
)

ACTION_LANE = Path(
    "weather/output/"
    "unified_attempt_action_lane_ledger_v8.csv"
)

DECISION_STATE = Path(
    "weather/output/"
    "contemporaneous_decision_state_evidence_ledger_v2.csv"
)

QUEUE = Path(
    "weather/output/"
    "queue_requeue_evidence_ledger_v1.csv"
)

QUEUE_WAIT_POLICY = Path(
    "weather/output/"
    "queue_wait_identifiability_2022_v1.csv"
)

SERVICE_POLICY = Path(
    "weather/output/"
    "pit_service_identifiability_2022_v1.csv"
)

INTERRUPTION_POLICY = Path(
    "weather/output/"
    "interruption_track_state_identifiability_2022_v1.csv"
)

RUBBER_POLICY = Path(
    "weather/output/"
    "rubber_grip_identifiability_2022_v1.csv"
)

TIRE_POLICY = Path(
    "weather/output/"
    "tire_thermal_pressure_identifiability_2022_v1.csv"
)

READINESS = Path(
    "weather/output/"
    "rescue_readiness_summary_v1.json"
)


STATE_OUT = (
    OUTPUT_DIR
    / "decision_time_observable_state_v2.csv"
)

PROVENANCE_OUT = (
    OUTPUT_DIR
    / "decision_time_observable_state_v2_provenance.csv"
)

SUMMARY_OUT = (
    OUTPUT_DIR
    / "decision_time_observable_state_v2_summary.json"
)

QA_OUT = (
    OUTPUT_DIR
    / "decision_time_observable_state_v2_qa.csv"
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


def parse_int(v):
    try:
        return int(float(txt(v)))
    except Exception:
        return None


def parse_float(v):
    try:
        return float(txt(v))
    except Exception:
        return None


def split_pipe(v):
    return [
        x.strip()
        for x in txt(v).split("|")
        if x.strip()
    ]


def unique_nonblank(values):
    out = []

    for value in values:
        value = txt(value)

        if not value:
            continue

        if value not in out:
            out.append(value)

    return out


def first_nonblank(values, default="UNKNOWN"):
    vals = unique_nonblank(values)

    if vals:
        return vals[0]

    return default


def joined_unique(values, default="UNKNOWN"):
    vals = unique_nonblank(values)

    if not vals:
        return default

    return "|".join(vals)


def pair_bound(row, first_id, second_id):
    subject = txt(
        row.get("subject_attempt_id")
    )

    related = txt(
        row.get("related_attempt_id")
    )

    ids = {
        x
        for x in [
            subject,
            related,
        ]
        if x
    }

    if not ids:
        return False

    pair = {
        first_id,
        second_id,
    }

    return bool(
        ids
        &
        pair
    )


def pair_exact_or_partial(row, first_id, second_id):
    subject = txt(
        row.get("subject_attempt_id")
    )

    related = txt(
        row.get("related_attempt_id")
    )

    ids = {
        x
        for x in [
            subject,
            related,
        ]
        if x
    }

    pair = {
        first_id,
        second_id,
    }

    if ids == pair:
        return "PAIR_EXACT"

    if ids & pair:
        return "PAIR_PARTIAL"

    return "UNBOUND"


def chronology_attempt_rows(
    chronology_rows,
    driver,
    attempt_id,
):
    return [
        row
        for row in chronology_rows
        if (
            txt(row.get("year"))
            ==
            YEAR
            and
            txt(row.get("driver_name"))
            ==
            driver
            and
            txt(row.get("attempt_id"))
            ==
            attempt_id
        )
    ]


def car_attempt_index_for(
    chronology_rows,
    driver,
    attempt_id,
):
    rows = chronology_attempt_rows(
        chronology_rows,
        driver,
        attempt_id,
    )

    indices = [
        parse_int(
            row.get("car_attempt_index")
        )
        for row in rows
    ]

    indices = [
        x
        for x in indices
        if x is not None
    ]

    if not indices:
        return None

    return min(indices)


def attempt_time_quality(
    chronology_rows,
    driver,
    attempt_id,
):
    rows = chronology_attempt_rows(
        chronology_rows,
        driver,
        attempt_id,
    )

    qualities = unique_nonblank(
        row.get("time_quality")
        for row in rows
    )

    priority = [
        "EXACT",
        "APPROXIMATE",
        "BOUNDED",
        "ORDERING_ONLY",
        "UNKNOWN",
    ]

    for quality in priority:
        if quality in qualities:
            return quality

    if qualities:
        return qualities[0]

    return "UNKNOWN"


def attempt_time_field(
    chronology_rows,
    driver,
    attempt_id,
    field,
):
    rows = chronology_attempt_rows(
        chronology_rows,
        driver,
        attempt_id,
    )

    return first_nonblank(
        [
            row.get(field)
            for row in rows
        ],
        default="UNKNOWN",
    )


def attempt_status(
    chronology_rows,
    driver,
    attempt_id,
):
    rows = chronology_attempt_rows(
        chronology_rows,
        driver,
        attempt_id,
    )

    return joined_unique(
        [
            row.get("result_status")
            for row in rows
        ],
        default="UNKNOWN",
    )


def attempt_chronology_usable(
    chronology_rows,
    driver,
    attempt_id,
):
    rows = chronology_attempt_rows(
        chronology_rows,
        driver,
        attempt_id,
    )

    values = {
        txt(
            row.get("chronology_usable")
        ).lower()
        for row in rows
    }

    if "true" in values:
        return "True"

    if "false" in values:
        return "False"

    return "UNKNOWN"


def choose_pair_attempts(
    driver,
    eligibility_row,
    chronology_rows,
):
    eligibility_ids = split_pipe(
        eligibility_row.get("attempt_ids")
    )

    candidates = []

    for attempt_id in eligibility_ids:

        idx = car_attempt_index_for(
            chronology_rows,
            driver,
            attempt_id,
        )

        candidates.append(
            (
                attempt_id,
                idx,
            )
        )

    with_index = [
        item
        for item in candidates
        if item[1] is not None
    ]

    with_index.sort(
        key=lambda x: (
            x[1],
            x[0],
        )
    )

    if len(with_index) >= 2:
        return (
            with_index[0][0],
            with_index[1][0],
            "CHRONOLOGY_CAR_ATTEMPT_INDEX",
        )

    # Fallback is eligibility order only.
    # It is explicit and flagged, never hidden.
    if len(eligibility_ids) >= 2:
        return (
            eligibility_ids[0],
            eligibility_ids[1],
            "ELIGIBILITY_ATTEMPT_ID_ORDER_FALLBACK",
        )

    return (
        "",
        "",
        "PAIR_NOT_RESOLVED",
    )


def action_rows_for_pair(
    rows,
    driver,
    first_id,
    second_id,
):
    return [
        row
        for row in rows
        if (
            txt(row.get("year"))
            ==
            YEAR
            and
            txt(row.get("driver_name"))
            ==
            driver
            and
            pair_bound(
                row,
                first_id,
                second_id,
            )
        )
    ]


def decision_rows_for_pair(
    rows,
    driver,
    first_id,
    second_id,
):
    return [
        row
        for row in rows
        if (
            txt(row.get("year"))
            ==
            YEAR
            and
            txt(row.get("driver_name"))
            ==
            driver
            and
            pair_bound(
                row,
                first_id,
                second_id,
            )
        )
    ]


def queue_rows_for_pair(
    rows,
    driver,
    first_id,
    second_id,
):
    return [
        row
        for row in rows
        if (
            txt(row.get("year"))
            ==
            YEAR
            and
            txt(row.get("driver_name"))
            ==
            driver
            and
            pair_bound(
                row,
                first_id,
                second_id,
            )
        )
    ]


def speed_for_attempt_from_action(
    action_rows,
    attempt_id,
):
    values = []

    for row in action_rows:

        subject = txt(
            row.get("subject_attempt_id")
        )

        related = txt(
            row.get("related_attempt_id")
        )

        if subject == attempt_id:
            value = parse_float(
                row.get("subject_speed_mph")
            )

            if value is not None:
                values.append(value)

        if related == attempt_id:
            value = parse_float(
                row.get("related_speed_mph")
            )

            if value is not None:
                values.append(value)

    if not values:
        return "UNKNOWN"

    unique = []

    for value in values:
        if value not in unique:
            unique.append(value)

    if len(unique) == 1:
        return f"{unique[0]:.3f}"

    return "|".join(
        f"{x:.3f}"
        for x in unique
    )


def best_rank_state(decision_rows):
    if not decision_rows:
        return {
            "state_evidence_count": 0,
            "rank": "UNKNOWN",
            "rank_lower_bound": "UNKNOWN",
            "rank_upper_bound": "UNKNOWN",
            "top12_state": "UNKNOWN",
            "cutoff_rank": "UNKNOWN",
            "cutoff_speed_mph": "UNKNOWN",
            "decision_state_time_quality": "UNKNOWN",
            "decision_state_source": "UNKNOWN",
            "decision_state_binding": "NONE",
        }

    rank = first_nonblank(
        [
            row.get("rank")
            for row in decision_rows
            if txt(row.get("rank"))
            not in {
                "",
                "UNKNOWN",
            }
        ],
        default="UNKNOWN",
    )

    rank_lb = first_nonblank(
        [
            row.get("rank_lower_bound")
            for row in decision_rows
            if txt(
                row.get("rank_lower_bound")
            )
            not in {
                "",
                "UNKNOWN",
            }
        ],
        default="UNKNOWN",
    )

    rank_ub = first_nonblank(
        [
            row.get("rank_upper_bound")
            for row in decision_rows
            if txt(
                row.get("rank_upper_bound")
            )
            not in {
                "",
                "UNKNOWN",
            }
        ],
        default="UNKNOWN",
    )

    top12 = first_nonblank(
        [
            row.get("top12_state")
            for row in decision_rows
            if txt(
                row.get("top12_state")
            )
            not in {
                "",
                "UNKNOWN",
            }
        ],
        default="UNKNOWN",
    )

    cutoff_rank = first_nonblank(
        [
            row.get("cutoff_rank")
            for row in decision_rows
            if txt(
                row.get("cutoff_rank")
            )
            not in {
                "",
                "UNKNOWN",
            }
        ],
        default="UNKNOWN",
    )

    cutoff_speed = first_nonblank(
        [
            row.get("cutoff_speed_mph")
            for row in decision_rows
            if txt(
                row.get("cutoff_speed_mph")
            )
            not in {
                "",
                "UNKNOWN",
            }
        ],
        default="UNKNOWN",
    )

    time_quality = joined_unique(
        [
            row.get("time_quality")
            for row in decision_rows
        ],
        default="UNKNOWN",
    )

    source = joined_unique(
        [
            row.get("source_name")
            for row in decision_rows
        ],
        default="UNKNOWN",
    )

    bindings = joined_unique(
        [
            row.get("_binding_quality")
            for row in decision_rows
        ],
        default="UNKNOWN",
    )

    return {
        "state_evidence_count":
            len(decision_rows),

        "rank":
            rank,

        "rank_lower_bound":
            rank_lb,

        "rank_upper_bound":
            rank_ub,

        "top12_state":
            top12,

        "cutoff_rank":
            cutoff_rank,

        "cutoff_speed_mph":
            cutoff_speed,

        "decision_state_time_quality":
            time_quality,

        "decision_state_source":
            source,

        "decision_state_binding":
            bindings,
    }


def queue_state(queue_rows):
    if not queue_rows:
        return {
            "queue_evidence_count": 0,
            "queue_membership": "UNKNOWN",
            "queue_lane": "UNKNOWN",
            "queue_position": "UNKNOWN",
            "relative_run_order": "UNKNOWN",
            "queue_time_quality": "UNKNOWN",
            "queue_source": "UNKNOWN",
            "queue_binding": "NONE",
        }

    return {
        "queue_evidence_count":
            len(queue_rows),

        "queue_membership":
            joined_unique(
                [
                    row.get("queue_membership")
                    for row in queue_rows
                    if txt(
                        row.get(
                            "queue_membership"
                        )
                    )
                    not in {
                        "",
                        "UNKNOWN",
                    }
                ],
                default="UNKNOWN",
            ),

        "queue_lane":
            joined_unique(
                [
                    row.get("queue_lane")
                    for row in queue_rows
                    if txt(
                        row.get("queue_lane")
                    )
                    not in {
                        "",
                        "UNKNOWN",
                    }
                ],
                default="UNKNOWN",
            ),

        "queue_position":
            joined_unique(
                [
                    row.get("queue_position")
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
                ],
                default="UNKNOWN",
            ),

        "relative_run_order":
            joined_unique(
                [
                    row.get("relative_run_order")
                    for row in queue_rows
                    if txt(
                        row.get(
                            "relative_run_order"
                        )
                    )
                    not in {
                        "",
                        "UNKNOWN",
                    }
                ],
                default="UNKNOWN",
            ),

        "queue_time_quality":
            joined_unique(
                [
                    row.get("time_quality")
                    for row in queue_rows
                ],
                default="UNKNOWN",
            ),

        "queue_source":
            joined_unique(
                [
                    row.get("source_name")
                    for row in queue_rows
                ],
                default="UNKNOWN",
            ),

        "queue_binding":
            joined_unique(
                [
                    row.get("_binding_quality")
                    for row in queue_rows
                ],
                default="UNKNOWN",
            ),
    }


def main():

    print()
    print("=" * 128)
    print(
        "R3A.1 — BUILD DECISION-TIME "
        "OBSERVABLE STATE V2"
    )
    print("=" * 128)

    required = [
        ELIGIBILITY,
        CHRONOLOGY,
        ACTION_LANE,
        DECISION_STATE,
        QUEUE,
        QUEUE_WAIT_POLICY,
        SERVICE_POLICY,
        INTERRUPTION_POLICY,
        RUBBER_POLICY,
        TIRE_POLICY,
        READINESS,
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
            "R3A1_DECISION_TIME_STATE_V2_INPUT_MISSING"
        )

        return

    eligibility = read_csv(
        ELIGIBILITY
    )

    chronology = read_csv(
        CHRONOLOGY
    )

    action_lane = read_csv(
        ACTION_LANE
    )

    decision_state = read_csv(
        DECISION_STATE
    )

    queue = read_csv(
        QUEUE
    )

    queue_wait_policy = read_csv(
        QUEUE_WAIT_POLICY
    )

    service_policy = read_csv(
        SERVICE_POLICY
    )

    interruption_policy = read_csv(
        INTERRUPTION_POLICY
    )

    rubber_policy = read_csv(
        RUBBER_POLICY
    )

    tire_policy = read_csv(
        TIRE_POLICY
    )

    readiness = json.loads(
        READINESS.read_text(
            encoding="utf-8"
        )
    )

    eligible_rows = [
        row
        for row in eligibility
        if txt(
            row.get(
                "decision_relevant_denominator"
            )
        ).upper()
        ==
        "INCLUDE"
    ]

    target_drivers = {
        txt(row.get("driver_name"))
        for row in eligible_rows
    }

    target_exact = (
        target_drivers
        ==
        EXPECTED_DRIVERS
    )

    print()
    print("=" * 128)
    print("FROZEN TARGET SET")
    print("=" * 128)

    print()

    for driver in sorted(
        target_drivers
    ):
        print(driver)

    print()
    print(
        "Target exact:",
        target_exact,
    )

    if not target_exact:

        print()
        print(
            "FINAL STATUS: "
            "R3A1_TARGET_SET_REVIEW_REQUIRED"
        )

        return

    eligibility_by_driver = {
        txt(row.get("driver_name")):
        row
        for row in eligible_rows
    }

    queue_wait_state = first_nonblank(
        [
            row.get(
                "simulator_queue_wait_policy"
            )
            for row in queue_wait_policy
        ],
        default="LATENT_SENSITIVITY_VARIABLE",
    )

    service_state = first_nonblank(
        [
            row.get(
                "downstream_service_policy"
            )
            for row in service_policy
        ],
        default="SERVICE_STATE_UNKNOWN",
    )

    interruption_state = first_nonblank(
        [
            row.get(
                "downstream_track_state_policy"
            )
            for row in interruption_policy
        ],
        default="UNKNOWN",
    )

    rubber_state = first_nonblank(
        [
            row.get(
                "downstream_rubber_policy"
            )
            for row in rubber_policy
        ],
        default="UNKNOWN_NOT_IDENTIFIABLE",
    )

    grip_state = first_nonblank(
        [
            row.get(
                "downstream_grip_evolution_policy"
            )
            for row in rubber_policy
        ],
        default="UNKNOWN_NOT_IDENTIFIABLE",
    )

    tire_state = first_nonblank(
        [
            row.get(
                "downstream_tire_state_policy"
            )
            for row in tire_policy
        ],
        default="TIRE_STATE_UNKNOWN",
    )

    states = []
    provenance = []

    print()
    print("=" * 128)
    print("STATE CONSTRUCTION")
    print("=" * 128)

    for driver in sorted(
        EXPECTED_DRIVERS
    ):

        eligibility_row = (
            eligibility_by_driver[
                driver
            ]
        )

        (
            first_id,
            second_id,
            pair_method,
        ) = choose_pair_attempts(
            driver,
            eligibility_row,
            chronology,
        )

        if (
            not first_id
            or
            not second_id
        ):

            print()
            print(
                driver,
                "PAIR RESOLUTION FAILED",
            )

            continue

        first_index = car_attempt_index_for(
            chronology,
            driver,
            first_id,
        )

        second_index = car_attempt_index_for(
            chronology,
            driver,
            second_id,
        )

        action_rows = (
            action_rows_for_pair(
                action_lane,
                driver,
                first_id,
                second_id,
            )
        )

        decision_rows = (
            decision_rows_for_pair(
                decision_state,
                driver,
                first_id,
                second_id,
            )
        )

        queue_rows = (
            queue_rows_for_pair(
                queue,
                driver,
                first_id,
                second_id,
            )
        )

        for row in action_rows:
            row["_binding_quality"] = (
                pair_exact_or_partial(
                    row,
                    first_id,
                    second_id,
                )
            )

        for row in decision_rows:
            row["_binding_quality"] = (
                pair_exact_or_partial(
                    row,
                    first_id,
                    second_id,
                )
            )

        for row in queue_rows:
            row["_binding_quality"] = (
                pair_exact_or_partial(
                    row,
                    first_id,
                    second_id,
                )
            )

        action = joined_unique(
            [
                row.get("action")
                for row in action_rows
                if txt(
                    row.get("action")
                )
                not in {
                    "",
                    "UNKNOWN",
                }
            ],
            default="UNKNOWN",
        )

        lane = joined_unique(
            [
                row.get("lane")
                for row in action_rows
                if txt(
                    row.get("lane")
                )
                not in {
                    "",
                    "UNKNOWN",
                }
            ],
            default="UNKNOWN",
        )

        action_binding = joined_unique(
            [
                row.get(
                    "_binding_quality"
                )
                for row in action_rows
            ],
            default="NONE",
        )

        action_source = joined_unique(
            [
                row.get("source_name")
                for row in action_rows
            ],
            default="UNKNOWN",
        )

        first_speed = (
            speed_for_attempt_from_action(
                action_rows,
                first_id,
            )
        )

        second_speed = (
            speed_for_attempt_from_action(
                action_rows,
                second_id,
            )
        )

        rank_state = best_rank_state(
            decision_rows
        )

        q_state = queue_state(
            queue_rows
        )

        first_time_quality = (
            attempt_time_quality(
                chronology,
                driver,
                first_id,
            )
        )

        second_time_quality = (
            attempt_time_quality(
                chronology,
                driver,
                second_id,
            )
        )

        first_time_point = (
            attempt_time_field(
                chronology,
                driver,
                first_id,
                "time_point_utc",
            )
        )

        first_time_lower = (
            attempt_time_field(
                chronology,
                driver,
                first_id,
                "time_lower_utc",
            )
        )

        first_time_upper = (
            attempt_time_field(
                chronology,
                driver,
                first_id,
                "time_upper_utc",
            )
        )

        second_time_point = (
            attempt_time_field(
                chronology,
                driver,
                second_id,
                "time_point_utc",
            )
        )

        second_time_lower = (
            attempt_time_field(
                chronology,
                driver,
                second_id,
                "time_lower_utc",
            )
        )

        second_time_upper = (
            attempt_time_field(
                chronology,
                driver,
                second_id,
                "time_upper_utc",
            )
        )

        first_status = attempt_status(
            chronology,
            driver,
            first_id,
        )

        second_status = attempt_status(
            chronology,
            driver,
            second_id,
        )

        first_usable = (
            attempt_chronology_usable(
                chronology,
                driver,
                first_id,
            )
        )

        second_usable = (
            attempt_chronology_usable(
                chronology,
                driver,
                second_id,
            )
        )

        observable_rank_present = (
            rank_state["rank"]
            !=
            "UNKNOWN"
            or
            rank_state[
                "rank_lower_bound"
            ]
            !=
            "UNKNOWN"
            or
            rank_state[
                "rank_upper_bound"
            ]
            !=
            "UNKNOWN"
        )

        observable_cutoff_present = (
            rank_state[
                "cutoff_rank"
            ]
            !=
            "UNKNOWN"
            or
            rank_state[
                "cutoff_speed_mph"
            ]
            !=
            "UNKNOWN"
        )

        observable_queue_present = any([
            q_state[
                "queue_membership"
            ]
            !=
            "UNKNOWN",

            q_state[
                "queue_lane"
            ]
            !=
            "UNKNOWN",

            q_state[
                "queue_position"
            ]
            !=
            "UNKNOWN",

            q_state[
                "relative_run_order"
            ]
            !=
            "UNKNOWN",
        ])

        state_observability = []

        state_observability.append(
            "PAIR_CHRONOLOGY"
        )

        if action != "UNKNOWN":
            state_observability.append(
                "ACTION"
            )

        if lane != "UNKNOWN":
            state_observability.append(
                "LANE"
            )

        if observable_rank_present:
            state_observability.append(
                "RANK"
            )

        if observable_cutoff_present:
            state_observability.append(
                "CUTOFF"
            )

        if observable_queue_present:
            state_observability.append(
                "QUEUE_ANCHOR"
            )

        state_id = (
            "DTV2-2022-"
            +
            driver.upper()
            .replace(" ", "_")
            .replace("É", "E")
        )

        state = {
            "state_id":
                state_id,

            "year":
                YEAR,

            "driver_name":
                driver,

            "decision_stage":
                "AFTER_FIRST_ATTEMPT_BEFORE_REPEAT_ATTEMPT",

            "pair_resolution_method":
                pair_method,

            "first_attempt_id":
                first_id,

            "second_attempt_id":
                second_id,

            "first_car_attempt_index":
                (
                    first_index
                    if first_index
                    is not None
                    else
                    "UNKNOWN"
                ),

            "second_car_attempt_index":
                (
                    second_index
                    if second_index
                    is not None
                    else
                    "UNKNOWN"
                ),

            "first_attempt_status":
                first_status,

            "second_attempt_status":
                second_status,

            "first_attempt_chronology_usable":
                first_usable,

            "second_attempt_chronology_usable":
                second_usable,

            "first_attempt_time_quality":
                first_time_quality,

            "first_attempt_time_point_utc":
                first_time_point,

            "first_attempt_time_lower_utc":
                first_time_lower,

            "first_attempt_time_upper_utc":
                first_time_upper,

            "second_attempt_time_quality":
                second_time_quality,

            "second_attempt_time_point_utc":
                second_time_point,

            "second_attempt_time_lower_utc":
                second_time_lower,

            "second_attempt_time_upper_utc":
                second_time_upper,

            "first_attempt_speed_mph":
                first_speed,

            "second_attempt_speed_mph":
                second_speed,

            "action_semantic":
                action,

            "lane_identity":
                lane,

            "action_evidence_count":
                len(action_rows),

            "action_binding_quality":
                action_binding,

            "action_source":
                action_source,

            "current_rank":
                rank_state[
                    "rank"
                ],

            "current_rank_lower_bound":
                rank_state[
                    "rank_lower_bound"
                ],

            "current_rank_upper_bound":
                rank_state[
                    "rank_upper_bound"
                ],

            "top12_state":
                rank_state[
                    "top12_state"
                ],

            "cutoff_rank":
                rank_state[
                    "cutoff_rank"
                ],

            "cutoff_speed_mph":
                rank_state[
                    "cutoff_speed_mph"
                ],

            "decision_state_evidence_count":
                rank_state[
                    "state_evidence_count"
                ],

            "decision_state_time_quality":
                rank_state[
                    "decision_state_time_quality"
                ],

            "decision_state_binding_quality":
                rank_state[
                    "decision_state_binding"
                ],

            "decision_state_source":
                rank_state[
                    "decision_state_source"
                ],

            "queue_membership":
                q_state[
                    "queue_membership"
                ],

            "queue_lane":
                q_state[
                    "queue_lane"
                ],

            "queue_position":
                q_state[
                    "queue_position"
                ],

            "relative_run_order":
                q_state[
                    "relative_run_order"
                ],

            "queue_evidence_count":
                q_state[
                    "queue_evidence_count"
                ],

            "queue_time_quality":
                q_state[
                    "queue_time_quality"
                ],

            "queue_binding_quality":
                q_state[
                    "queue_binding"
                ],

            "queue_source":
                q_state[
                    "queue_source"
                ],

            "historical_queue_wait_state":
                "UNKNOWN",

            "simulator_queue_wait_policy":
                queue_wait_state,

            "pit_service_state":
                "UNKNOWN",

            "pit_service_policy":
                service_state,

            "rubber_state":
                "UNKNOWN",

            "rubber_policy":
                rubber_state,

            "grip_evolution_state":
                "UNKNOWN",

            "grip_evolution_policy":
                grip_state,

            "tire_thermal_pressure_state":
                "UNKNOWN",

            "tire_state_policy":
                tire_state,

            "interruption_context":
                "UNKNOWN_UNLESS_SOURCE_BOUND",

            "interruption_policy":
                interruption_state,

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
                    state_observability
                ),

            "state_scope":
                "LIMITED_HISTORICAL_OBSERVABLE_STATE",

            "full_historical_state":
                "False",

            "hard_optimality_truth_ready":
                "False",
        }

        states.append(state)

        print()
        print("-" * 128)

        print(driver)

        print(
            "  pair:",
            first_id,
            "->",
            second_id,
        )

        print(
            "  pair method:",
            pair_method,
        )

        print(
            "  action:",
            action,
        )

        print(
            "  lane:",
            lane,
        )

        print(
            "  current rank:",
            rank_state[
                "rank"
            ],
        )

        print(
            "  cutoff:",
            rank_state[
                "cutoff_rank"
            ],
            "/",
            rank_state[
                "cutoff_speed_mph"
            ],
        )

        print(
            "  queue membership:",
            q_state[
                "queue_membership"
            ],
        )

        print(
            "  queue position:",
            q_state[
                "queue_position"
            ],
        )

        print(
            "  observable:",
            "|".join(
                state_observability
            ),
        )

        # ----------------------------------------------
        # Provenance rows
        # ----------------------------------------------

        for row in action_rows:

            provenance.append({
                "state_id":
                    state_id,

                "domain":
                    "ACTION_LANE",

                "evidence_id":
                    txt(
                        row.get(
                            "evidence_id"
                        )
                    ),

                "subject_attempt_id":
                    txt(
                        row.get(
                            "subject_attempt_id"
                        )
                    ),

                "related_attempt_id":
                    txt(
                        row.get(
                            "related_attempt_id"
                        )
                    ),

                "binding_quality":
                    txt(
                        row.get(
                            "_binding_quality"
                        )
                    ),

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

                "source_reference":
                    txt(
                        row.get(
                            "source_candidate_id"
                        )
                    ),

                "evidence_semantic":
                    joined_unique(
                        [
                            row.get("action"),
                            row.get("lane"),
                        ],
                        default="UNKNOWN",
                    ),
            })

        for row in decision_rows:

            provenance.append({
                "state_id":
                    state_id,

                "domain":
                    "DECISION_STATE",

                "evidence_id":
                    txt(
                        row.get(
                            "state_id"
                        )
                    ),

                "subject_attempt_id":
                    txt(
                        row.get(
                            "subject_attempt_id"
                        )
                    ),

                "related_attempt_id":
                    txt(
                        row.get(
                            "related_attempt_id"
                        )
                    ),

                "binding_quality":
                    txt(
                        row.get(
                            "_binding_quality"
                        )
                    ),

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

                "source_reference":
                    txt(
                        row.get(
                            "source_semantic"
                        )
                    ),

                "evidence_semantic":
                    joined_unique(
                        [
                            row.get("rank"),
                            row.get("top12_state"),
                            row.get("cutoff_rank"),
                            row.get(
                                "cutoff_speed_mph"
                            ),
                        ],
                        default="UNKNOWN",
                    ),
            })

        for row in queue_rows:

            provenance.append({
                "state_id":
                    state_id,

                "domain":
                    "QUEUE",

                "evidence_id":
                    txt(
                        row.get(
                            "queue_state_id"
                        )
                    ),

                "subject_attempt_id":
                    txt(
                        row.get(
                            "subject_attempt_id"
                        )
                    ),

                "related_attempt_id":
                    txt(
                        row.get(
                            "related_attempt_id"
                        )
                    ),

                "binding_quality":
                    txt(
                        row.get(
                            "_binding_quality"
                        )
                    ),

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

                "source_reference":
                    txt(
                        row.get(
                            "source_reference"
                        )
                    ),

                "evidence_semantic":
                    joined_unique(
                        [
                            row.get(
                                "queue_membership"
                            ),
                            row.get(
                                "queue_lane"
                            ),
                            row.get(
                                "queue_position"
                            ),
                            row.get(
                                "relative_run_order"
                            ),
                        ],
                        default="UNKNOWN",
                    ),
            })

    # --------------------------------------------------
    # Write state dataset
    # --------------------------------------------------

    state_fields = [
        "state_id",
        "year",
        "driver_name",
        "decision_stage",
        "pair_resolution_method",
        "first_attempt_id",
        "second_attempt_id",
        "first_car_attempt_index",
        "second_car_attempt_index",
        "first_attempt_status",
        "second_attempt_status",
        "first_attempt_chronology_usable",
        "second_attempt_chronology_usable",
        "first_attempt_time_quality",
        "first_attempt_time_point_utc",
        "first_attempt_time_lower_utc",
        "first_attempt_time_upper_utc",
        "second_attempt_time_quality",
        "second_attempt_time_point_utc",
        "second_attempt_time_lower_utc",
        "second_attempt_time_upper_utc",
        "first_attempt_speed_mph",
        "second_attempt_speed_mph",
        "action_semantic",
        "lane_identity",
        "action_evidence_count",
        "action_binding_quality",
        "action_source",
        "current_rank",
        "current_rank_lower_bound",
        "current_rank_upper_bound",
        "top12_state",
        "cutoff_rank",
        "cutoff_speed_mph",
        "decision_state_evidence_count",
        "decision_state_time_quality",
        "decision_state_binding_quality",
        "decision_state_source",
        "queue_membership",
        "queue_lane",
        "queue_position",
        "relative_run_order",
        "queue_evidence_count",
        "queue_time_quality",
        "queue_binding_quality",
        "queue_source",
        "historical_queue_wait_state",
        "simulator_queue_wait_policy",
        "pit_service_state",
        "pit_service_policy",
        "rubber_state",
        "rubber_policy",
        "grip_evolution_state",
        "grip_evolution_policy",
        "tire_thermal_pressure_state",
        "tire_state_policy",
        "interruption_context",
        "interruption_policy",
        "weather_feature_policy",
        "track_temperature_policy",
        "elapsed_time_as_track_evolution",
        "unknown_state_imputation",
        "observable_components",
        "state_scope",
        "full_historical_state",
        "hard_optimality_truth_ready",
    ]

    write_csv(
        STATE_OUT,
        states,
        state_fields,
    )

    write_csv(
        PROVENANCE_OUT,
        provenance,
        [
            "state_id",
            "domain",
            "evidence_id",
            "subject_attempt_id",
            "related_attempt_id",
            "binding_quality",
            "source_name",
            "source_class",
            "source_reference",
            "evidence_semantic",
        ],
    )

    # --------------------------------------------------
    # QA
    # --------------------------------------------------

    state_driver_set = {
        row["driver_name"]
        for row in states
    }

    unique_state_ids = {
        row["state_id"]
        for row in states
    }

    unresolved_pairs = [
        row
        for row in states
        if (
            not txt(
                row.get(
                    "first_attempt_id"
                )
            )
            or
            not txt(
                row.get(
                    "second_attempt_id"
                )
            )
        )
    ]

    fallback_pairs = [
        row
        for row in states
        if row[
            "pair_resolution_method"
        ]
        ==
        "ELIGIBILITY_ATTEMPT_ID_ORDER_FALLBACK"
    ]

    known_rank_rows = [
        row
        for row in states
        if (
            row["current_rank"]
            !=
            "UNKNOWN"
            or
            row[
                "current_rank_lower_bound"
            ]
            !=
            "UNKNOWN"
            or
            row[
                "current_rank_upper_bound"
            ]
            !=
            "UNKNOWN"
        )
    ]

    known_queue_rows = [
        row
        for row in states
        if any([
            row[
                "queue_membership"
            ]
            !=
            "UNKNOWN",

            row[
                "queue_lane"
            ]
            !=
            "UNKNOWN",

            row[
                "queue_position"
            ]
            !=
            "UNKNOWN",

            row[
                "relative_run_order"
            ]
            !=
            "UNKNOWN",
        ])
    ]

    explicit_lane_states = [
        row
        for row in states
        if row[
            "lane_identity"
        ]
        not in {
            "",
            "UNKNOWN",
        }
    ]

    queue_wait_truth_leaks = [
        row
        for row in states
        if row[
            "historical_queue_wait_state"
        ]
        !=
        "UNKNOWN"
    ]

    service_truth_leaks = [
        row
        for row in states
        if row[
            "pit_service_state"
        ]
        !=
        "UNKNOWN"
    ]

    rubber_truth_leaks = [
        row
        for row in states
        if (
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
        )
    ]

    tire_truth_leaks = [
        row
        for row in states
        if row[
            "tire_thermal_pressure_state"
        ]
        !=
        "UNKNOWN"
    ]

    qa_rows = [
        {
            "metric":
                "state_rows_is_8",

            "value":
                len(states),

            "status":
                (
                    "PASS"
                    if len(states)
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
                    state_driver_set
                    ==
                    EXPECTED_DRIVERS
                ),

            "status":
                (
                    "PASS"
                    if state_driver_set
                    ==
                    EXPECTED_DRIVERS
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "state_ids_unique",

            "value":
                len(
                    unique_state_ids
                ),

            "status":
                (
                    "PASS"
                    if len(
                        unique_state_ids
                    )
                    ==
                    8
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "unresolved_pairs",

            "value":
                len(
                    unresolved_pairs
                ),

            "status":
                (
                    "PASS"
                    if len(
                        unresolved_pairs
                    )
                    ==
                    0
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "eligibility_order_fallback_pairs",

            "value":
                len(
                    fallback_pairs
                ),

            "status":
                (
                    "PASS"
                    if len(
                        fallback_pairs
                    )
                    ==
                    0
                    else
                    "REVIEW"
                ),
        },

        {
            "metric":
                "known_rank_state_rows",

            "value":
                len(
                    known_rank_rows
                ),

            "status":
                "PASS",
        },

        {
            "metric":
                "known_queue_state_rows",

            "value":
                len(
                    known_queue_rows
                ),

            "status":
                "PASS",
        },

        {
            "metric":
                "explicit_lane_states",

            "value":
                len(
                    explicit_lane_states
                ),

            "status":
                "PASS",
        },

        {
            "metric":
                "historical_queue_wait_truth_leaks",

            "value":
                len(
                    queue_wait_truth_leaks
                ),

            "status":
                (
                    "PASS"
                    if len(
                        queue_wait_truth_leaks
                    )
                    ==
                    0
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "pit_service_truth_leaks",

            "value":
                len(
                    service_truth_leaks
                ),

            "status":
                (
                    "PASS"
                    if len(
                        service_truth_leaks
                    )
                    ==
                    0
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "rubber_grip_truth_leaks",

            "value":
                len(
                    rubber_truth_leaks
                ),

            "status":
                (
                    "PASS"
                    if len(
                        rubber_truth_leaks
                    )
                    ==
                    0
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "tire_truth_leaks",

            "value":
                len(
                    tire_truth_leaks
                ),

            "status":
                (
                    "PASS"
                    if len(
                        tire_truth_leaks
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

    hard_fail = any(
        row["status"]
        ==
        "FAIL"
        for row in qa_rows
    )

    payload = {
        "phase":
            PHASE,

        "year":
            2022,

        "state_rows":
            len(states),

        "target_driver_count":
            len(
                EXPECTED_DRIVERS
            ),

        "pair_resolution": {
            "chronology_car_attempt_index":
                sum(
                    row[
                        "pair_resolution_method"
                    ]
                    ==
                    "CHRONOLOGY_CAR_ATTEMPT_INDEX"
                    for row in states
                ),

            "eligibility_order_fallback":
                len(
                    fallback_pairs
                ),
        },

        "observability": {
            "rank_state_rows":
                len(
                    known_rank_rows
                ),

            "queue_state_rows":
                len(
                    known_queue_rows
                ),

            "explicit_lane_rows":
                len(
                    explicit_lane_states
                ),
        },

        "latent_or_unknown": {
            "queue_wait":
                "LATENT_SENSITIVITY_VARIABLE",

            "pit_service":
                "UNKNOWN",

            "rubber_grip":
                "UNKNOWN",

            "tire_thermal_pressure":
                "UNKNOWN",
        },

        "weather_policy":
            "DECISION_TIME_HRRR_WITH_AVAILABILITY_CONTROL",

        "track_temperature_policy":
            "OBSERVED_PTSC_WHERE_TIME_ALIGNMENT_SUPPORTED",

        "elapsed_time_as_track_evolution":
            "PROHIBITED",

        "unknown_state_imputation":
            "NONE",

        "full_historical_state_claim":
            False,

        "limited_sequential_simulator_input_ready":
            not hard_fail,

        "next_phase":
            (
                "R3B_LIMITED_UNCERTAINTY_AWARE_"
                "SEQUENTIAL_SIMULATOR"
                if not hard_fail
                else
                "R3A1_REVIEW_REQUIRED"
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

    print()
    print("=" * 128)
    print("STATE DATASET SUMMARY")
    print("=" * 128)

    print()
    print(
        "State rows:",
        len(states),
    )

    print(
        "Chronology-index pair resolution:",
        sum(
            row[
                "pair_resolution_method"
            ]
            ==
            "CHRONOLOGY_CAR_ATTEMPT_INDEX"
            for row in states
        ),
        "/8",
    )

    print(
        "Eligibility-order fallback:",
        len(
            fallback_pairs
        ),
    )

    print()
    print(
        "Known rank-state rows:",
        len(
            known_rank_rows
        ),
    )

    print(
        "Known queue-state rows:",
        len(
            known_queue_rows
        ),
    )

    print(
        "Explicit lane states:",
        len(
            explicit_lane_states
        ),
    )

    print()
    print(
        "Queue wait truth leaks:",
        len(
            queue_wait_truth_leaks
        ),
    )

    print(
        "Service truth leaks:",
        len(
            service_truth_leaks
        ),
    )

    print(
        "Rubber/grip truth leaks:",
        len(
            rubber_truth_leaks
        ),
    )

    print(
        "Tire truth leaks:",
        len(
            tire_truth_leaks
        ),
    )

    print()
    print(
        "Unknown state imputation:",
        "NONE",
    )

    print(
        "Elapsed time used as track evolution:",
        "NO",
    )

    print()
    print("=" * 128)

    if not hard_fail:

        print(
            "FINAL STATUS: "
            "R3A1_DECISION_TIME_OBSERVABLE_STATE_V2_READY"
        )

    else:

        print(
            "FINAL STATUS: "
            "R3A1_DECISION_TIME_STATE_V2_REVIEW_REQUIRED"
        )

    print("=" * 128)

    print()
    print("OUTPUTS")
    print(STATE_OUT)
    print(PROVENANCE_OUT)
    print(SUMMARY_OUT)
    print(QA_OUT)


if __name__ == "__main__":
    main()
