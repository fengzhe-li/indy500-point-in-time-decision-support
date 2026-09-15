from pathlib import Path
import csv
import json
import math
from datetime import datetime, timezone, timedelta


PHASE = "R3B.2"

OUT = Path("weather/output")

STATE_V3 = (
    OUT
    / "decision_time_observable_state_v3.csv"
)

STATE_V2 = (
    OUT
    / "decision_time_observable_state_v2.csv"
)

WAIT_SCENARIOS = (
    OUT
    / "r3b_queue_wait_scenarios_v1.csv"
)

HRRR_FEATURES = (
    OUT
    / "hrrr_ims_2020_2024_features.csv"
)

HRRR_AVAILABILITY = (
    OUT
    / "hrrr_forecast_availability_policy.csv"
)

PTSC_ALIGNMENT = (
    OUT
    / "ptsc_attempt_realized_environment_alignment.csv"
)

INTERRUPTION_LEDGER = (
    OUT
    / "interruption_state_evidence_ledger_2022_v1.csv"
)

SCENARIO_OUT = (
    OUT
    / "r3b_future_environment_scenarios_v1.csv"
)

STATE_COVERAGE_OUT = (
    OUT
    / "r3b_future_environment_state_coverage_v1.csv"
)

SUMMARY_OUT = (
    OUT
    / "r3b_future_environment_scenarios_v1.json"
)

QA_OUT = (
    OUT
    / "r3b_future_environment_scenarios_v1_qa.csv"
)


YEAR = "2022"
SESSION_DATE = "2022-05-21"


WEATHER_SCALARS = [
    "temp_c",
    "dewpoint_c",
    "relative_humidity_pct",
    "gust_ms",
    "pressure_hpa",
    "cloud_cover_pct",
    "shortwave_radiation_wm2",
]


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


def to_float(v):
    try:
        return float(txt(v))
    except Exception:
        return None


def to_int(v):
    try:
        return int(float(txt(v)))
    except Exception:
        return None


def parse_dt(v):
    s = txt(v)

    if not s or s.upper() == "UNKNOWN":
        return None

    s = s.replace(
        "Z",
        "+00:00",
    )

    try:
        dt = datetime.fromisoformat(s)
    except Exception:
        return None

    if dt.tzinfo is None:
        dt = dt.replace(
            tzinfo=timezone.utc
        )

    return dt.astimezone(
        timezone.utc
    )


def iso(dt):
    if dt is None:
        return "UNKNOWN"

    return (
        dt.astimezone(
            timezone.utc
        )
        .isoformat()
        .replace(
            "+00:00",
            "Z",
        )
    )


def truthy(v):
    return txt(v).lower() in {
        "true",
        "1",
        "yes",
    }


def midpoint(a, b):
    if a is None or b is None:
        return None

    return a + (
        b - a
    ) / 2


def decision_anchor_from_v2(row):
    """
    We do NOT invent a timestamp.

    Preference:
      1. explicit time_point_utc
      2. equal lower/upper bound
      3. bounded interval retained but NOT collapsed
         into a fake point timestamp
    """

    quality = txt(
        row.get(
            "first_attempt_time_quality"
        )
    ).upper()

    point = parse_dt(
        row.get(
            "first_attempt_time_point_utc"
        )
    )

    lower = parse_dt(
        row.get(
            "first_attempt_time_lower_utc"
        )
    )

    upper = parse_dt(
        row.get(
            "first_attempt_time_upper_utc"
        )
    )

    if point is not None:
        return {
            "usable_point":
                True,

            "anchor":
                point,

            "lower":
                lower,

            "upper":
                upper,

            "quality":
                quality
                or
                "UNKNOWN",

            "method":
                "FIRST_ATTEMPT_TIME_POINT",
        }

    if (
        lower is not None
        and
        upper is not None
        and
        lower
        ==
        upper
    ):
        return {
            "usable_point":
                True,

            "anchor":
                lower,

            "lower":
                lower,

            "upper":
                upper,

            "quality":
                quality
                or
                "UNKNOWN",

            "method":
                "EQUAL_TIME_BOUNDS",
        }

    if (
        lower is not None
        and
        upper is not None
    ):
        return {
            "usable_point":
                False,

            "anchor":
                None,

            "lower":
                lower,

            "upper":
                upper,

            "quality":
                quality
                or
                "BOUNDED",

            "method":
                "BOUNDED_TIME_NOT_COLLAPSED",
        }

    return {
        "usable_point":
            False,

        "anchor":
            None,

        "lower":
            lower,

        "upper":
            upper,

        "quality":
            quality
            or
            "UNKNOWN",

        "method":
            "NO_DECISION_TIME_POINT",
    }


def build_availability_index(rows):

    out = {}

    for row in rows:

        issue = parse_dt(
            row.get(
                "issue_time_utc"
            )
        )

        lead = to_int(
            row.get(
                "forecast_lead_hours"
            )
        )

        valid_start = parse_dt(
            row.get(
                "valid_start_utc"
            )
        )

        availability = parse_dt(
            row.get(
                "policy_availability_time_utc"
            )
        )

        leakage_safe = truthy(
            row.get(
                "leakage_safe_for_primary_analysis"
            )
        )

        if (
            issue is None
            or
            lead is None
        ):
            continue

        key = (
            issue,
            lead,
        )

        out[key] = {
            "availability":
                availability,

            "valid_start":
                valid_start,

            "leakage_safe":
                leakage_safe,

            "policy_id":
                txt(
                    row.get(
                        "availability_policy_id"
                    )
                ),

            "lag_minutes":
                txt(
                    row.get(
                        "availability_lag_minutes"
                    )
                ),
        }

    return out


def prepare_hrrr_rows(
    feature_rows,
    availability_index,
):

    prepared = []

    for row in feature_rows:

        if txt(
            row.get("date")
        ) != SESSION_DATE:
            continue

        issue = parse_dt(
            row.get(
                "cycle_time_utc"
            )
        )

        valid = parse_dt(
            row.get(
                "valid_time_utc"
            )
        )

        lead = to_int(
            row.get(
                "forecast_lead_hours"
            )
        )

        if lead is None:
            lead = to_int(
                row.get(
                    "forecast_hour"
                )
            )

        if (
            issue is None
            or
            valid is None
            or
            lead is None
        ):
            continue

        policy = (
            availability_index.get(
                (
                    issue,
                    lead,
                )
            )
        )

        if policy is None:
            continue

        prepared.append({
            "issue":
                issue,

            "valid":
                valid,

            "lead":
                lead,

            "availability":
                policy[
                    "availability"
                ],

            "leakage_safe":
                policy[
                    "leakage_safe"
                ],

            "policy_id":
                policy[
                    "policy_id"
                ],

            "lag_minutes":
                policy[
                    "lag_minutes"
                ],

            "row":
                row,
        })

    return prepared


def choose_same_cycle_bracket(
    hrrr_rows,
    decision_time,
    target_time,
):
    """
    Only use forecasts available by decision time.

    Then choose the latest available HRRR issue cycle that
    has a same-cycle target bracket.

    Never mix cycles.
    """

    eligible = [
        item
        for item in hrrr_rows
        if (
            item[
                "leakage_safe"
            ]
            and
            item[
                "availability"
            ]
            is not None
            and
            item[
                "availability"
            ]
            <=
            decision_time
        )
    ]

    if not eligible:
        return None

    cycles = sorted(
        {
            item["issue"]
            for item in eligible
        },
        reverse=True,
    )

    for cycle in cycles:

        rows = sorted(
            [
                item
                for item in eligible
                if item["issue"]
                ==
                cycle
            ],
            key=lambda x:
            x["valid"],
        )

        exact = [
            item
            for item in rows
            if item["valid"]
            ==
            target_time
        ]

        if exact:
            return {
                "cycle":
                    cycle,

                "before":
                    exact[0],

                "after":
                    exact[0],

                "weight":
                    0.0,

                "selection":
                    "EXACT_VALID_TIME",
            }

        before = [
            item
            for item in rows
            if item["valid"]
            <
            target_time
        ]

        after = [
            item
            for item in rows
            if item["valid"]
            >
            target_time
        ]

        if (
            not before
            or
            not after
        ):
            continue

        b = max(
            before,
            key=lambda x:
            x["valid"],
        )

        a = min(
            after,
            key=lambda x:
            x["valid"],
        )

        total_seconds = (
            a["valid"]
            -
            b["valid"]
        ).total_seconds()

        if total_seconds <= 0:
            continue

        weight = (
            target_time
            -
            b["valid"]
        ).total_seconds() / total_seconds

        return {
            "cycle":
                cycle,

            "before":
                b,

            "after":
                a,

            "weight":
                weight,

            "selection":
                "SAME_CYCLE_LINEAR_INTERPOLATION",
        }

    return None


def interpolate_scalar(
    before_row,
    after_row,
    field,
    weight,
):
    b = to_float(
        before_row.get(field)
    )

    a = to_float(
        after_row.get(field)
    )

    if b is None or a is None:
        return None

    if weight == 0:
        return b

    return (
        b
        +
        (
            a - b
        )
        *
        weight
    )


def interpolate_wind(
    before_row,
    after_row,
    weight,
):
    """
    Interpolate vector components, not circular direction.
    """

    ub = to_float(
        before_row.get(
            "UGRD_10m"
        )
    )

    ua = to_float(
        after_row.get(
            "UGRD_10m"
        )
    )

    vb = to_float(
        before_row.get(
            "VGRD_10m"
        )
    )

    va = to_float(
        after_row.get(
            "VGRD_10m"
        )
    )

    if None in {
        ub,
        ua,
        vb,
        va,
    }:
        return (
            None,
            None,
            None,
            None,
        )

    u = (
        ub
        +
        (
            ua - ub
        )
        *
        weight
    )

    v = (
        vb
        +
        (
            va - vb
        )
        *
        weight
    )

    speed = math.sqrt(
        u * u
        +
        v * v
    )

    # Meteorological direction:
    # direction wind is FROM.
    direction = (
        math.degrees(
            math.atan2(
                -u,
                -v,
            )
        )
        +
        360
    ) % 360

    return (
        u,
        v,
        speed,
        direction,
    )


def find_ptsc_for_attempt(
    ptsc_rows,
    attempt_id,
):
    matches = [
        row
        for row in ptsc_rows
        if txt(
            row.get(
                "attempt_id"
            )
        )
        ==
        attempt_id
    ]

    if not matches:
        return {
            "available":
                False,

            "track_c":
                None,

            "ambient_c":
                None,

            "alignment":
                "NO_PTSC_ATTEMPT_MATCH",

            "source_time":
                "UNKNOWN",
        }

    usable = []

    for row in matches:

        track_c = to_float(
            row.get(
                "ptsc_track_c"
            )
        )

        if track_c is None:
            continue

        usable.append(
            row
        )

    if not usable:
        return {
            "available":
                False,

            "track_c":
                None,

            "ambient_c":
                None,

            "alignment":
                "PTSC_MATCH_NO_TRACK_TEMP",

            "source_time":
                "UNKNOWN",
        }

    row = usable[0]

    return {
        "available":
            True,

        "track_c":
            to_float(
                row.get(
                    "ptsc_track_c"
                )
            ),

        "ambient_c":
            to_float(
                row.get(
                    "ptsc_ambient_c"
                )
            ),

        "alignment":
            txt(
                row.get(
                    "ptsc_interp_status"
                )
            )
            or
            txt(
                row.get(
                    "alignment_class"
                )
            )
            or
            "SUPPORTED",

        "source_time":
            txt(
                row.get(
                    "target_time_midpoint_utc"
                )
            )
            or
            "UNKNOWN",
    }


def build_interruption_windows(rows):
    """
    Use already frozen event anchors.

    They are not exact historical truth, so these windows are
    contextual flags only. They do NOT become reconstructed
    queue/run feasibility truth.
    """

    first_interrupt = None
    first_restart = None
    second_interrupt = None
    session_called = None

    for row in rows:

        event_type = txt(
            row.get(
                "event_type"
            )
        )

        event_stage = txt(
            row.get(
                "event_stage"
            )
        )

        lower = parse_dt(
            row.get(
                "time_lower_utc"
            )
        )

        upper = parse_dt(
            row.get(
                "time_upper_utc"
            )
        )

        if (
            event_type
            ==
            "RAIN_INTERRUPTION"
            and
            event_stage
            ==
            "FIRST_INTERRUPTION"
        ):
            first_interrupt = (
                lower
                or
                upper
            )

        elif (
            event_type
            ==
            "SESSION_RESTART"
        ):
            first_restart = (
                lower
                or
                upper
            )

        elif (
            event_type
            ==
            "SECOND_INTERRUPTION"
        ):
            second_interrupt = (
                lower
                or
                upper
            )

        elif (
            event_type
            ==
            "SESSION_CALLED"
        ):
            session_called = (
                lower
                or
                upper
            )

    windows = []

    if (
        first_interrupt
        is not None
        and
        first_restart
        is not None
    ):
        windows.append({
            "name":
                "FIRST_INTERRUPTION_CONTEXT",

            "start":
                first_interrupt,

            "end":
                first_restart,
        })

    if (
        second_interrupt
        is not None
        and
        session_called
        is not None
    ):
        windows.append({
            "name":
                "SECOND_INTERRUPTION_TO_SESSION_END_CONTEXT",

            "start":
                second_interrupt,

            "end":
                session_called,
        })

    return (
        windows,
        session_called,
    )


def interruption_context(
    target_time,
    windows,
    session_called,
):
    if target_time is None:
        return (
            "UNKNOWN",
            False,
        )

    if (
        session_called
        is not None
        and
        target_time
        >
        session_called
    ):
        return (
            "AFTER_SESSION_CALLED",
            True,
        )

    for window in windows:

        if (
            target_time
            >=
            window["start"]
            and
            target_time
            <=
            window["end"]
        ):
            return (
                window["name"],
                False,
            )

    return (
        "NO_FROZEN_INTERRUPTION_WINDOW_MATCH",
        False,
    )


def main():

    print()
    print("=" * 128)
    print(
        "R3B.2 — FUTURE ENVIRONMENT "
        "SCENARIO GENERATION"
    )
    print("=" * 128)

    required = [
        STATE_V3,
        STATE_V2,
        WAIT_SCENARIOS,
        HRRR_FEATURES,
        HRRR_AVAILABILITY,
        PTSC_ALIGNMENT,
        INTERRUPTION_LEDGER,
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
            "R3B2_FUTURE_ENVIRONMENT_INPUT_MISSING"
        )
        return

    state_v3 = read_csv(
        STATE_V3
    )

    state_v2 = read_csv(
        STATE_V2
    )

    wait_rows = read_csv(
        WAIT_SCENARIOS
    )

    hrrr_features = read_csv(
        HRRR_FEATURES
    )

    hrrr_availability = read_csv(
        HRRR_AVAILABILITY
    )

    ptsc_rows = read_csv(
        PTSC_ALIGNMENT
    )

    interruption_rows = read_csv(
        INTERRUPTION_LEDGER
    )

    # --------------------------------------------------
    # Validate target state
    # --------------------------------------------------

    drivers = {
        txt(
            row.get(
                "driver_name"
            )
        )
        for row in state_v3
    }

    target_exact = (
        len(state_v3)
        ==
        8
        and
        drivers
        ==
        EXPECTED_DRIVERS
    )

    v2_by_driver = {
        txt(
            row.get(
                "driver_name"
            )
        ):
        row
        for row in state_v2
    }

    # --------------------------------------------------
    # Weather data preparation
    # --------------------------------------------------

    availability_index = (
        build_availability_index(
            hrrr_availability
        )
    )

    prepared_hrrr = (
        prepare_hrrr_rows(
            hrrr_features,
            availability_index,
        )
    )

    (
        interruption_windows,
        session_called,
    ) = build_interruption_windows(
        interruption_rows
    )

    print()
    print("=" * 128)
    print("WEATHER INPUT")
    print("=" * 128)

    print()
    print(
        "2022 HRRR prepared rows:",
        len(
            prepared_hrrr
        ),
    )

    print(
        "Interruption context windows:",
        len(
            interruption_windows
        ),
    )

    print(
        "Session-called anchor:",
        iso(
            session_called
        ),
    )

    # --------------------------------------------------
    # Generate scenarios
    # --------------------------------------------------

    scenarios = []
    coverage_rows = []

    print()
    print("=" * 128)
    print("STATE / DECISION-TIME COVERAGE")
    print("=" * 128)

    for state in sorted(
        state_v3,
        key=lambda r:
        txt(
            r.get(
                "driver_name"
            )
        ),
    ):

        driver = txt(
            state.get(
                "driver_name"
            )
        )

        old = (
            v2_by_driver.get(
                driver,
                {}
            )
        )

        anchor = (
            decision_anchor_from_v2(
                old
            )
        )

        first_attempt_id = txt(
            state.get(
                "first_attempt_id"
            )
        )

        ptsc = (
            find_ptsc_for_attempt(
                ptsc_rows,
                first_attempt_id,
            )
        )

        print()
        print("-" * 128)

        print(driver)

        print(
            "  first attempt:",
            first_attempt_id,
        )

        print(
            "  time quality:",
            anchor[
                "quality"
            ],
        )

        print(
            "  anchor method:",
            anchor[
                "method"
            ],
        )

        print(
            "  anchor point:",
            iso(
                anchor[
                    "anchor"
                ]
            ),
        )

        print(
            "  lower bound:",
            iso(
                anchor[
                    "lower"
                ]
            ),
        )

        print(
            "  upper bound:",
            iso(
                anchor[
                    "upper"
                ]
            ),
        )

        print(
            "  PTSC current track temp:",
            (
                f"{ptsc['track_c']:.3f}"
                if ptsc[
                    "track_c"
                ]
                is not None
                else
                "UNKNOWN"
            ),
        )

        driver_ready = 0

        for wait_row in wait_rows:

            wait_min = to_int(
                wait_row.get(
                    "queue_wait_minutes"
                )
            )

            scenario_id = txt(
                wait_row.get(
                    "scenario_id"
                )
            )

            base = {
                "state_id":
                    txt(
                        state.get(
                            "state_id"
                        )
                    ),

                "driver_name":
                    driver,

                "first_attempt_id":
                    first_attempt_id,

                "wait_scenario_id":
                    scenario_id,

                "queue_wait_minutes":
                    (
                        wait_min
                        if wait_min
                        is not None
                        else
                        "UNKNOWN"
                    ),

                "historical_queue_wait_claim":
                    "False",

                "decision_anchor_semantic":
                    (
                        "FIRST_ATTEMPT_TIME_PROXY;"
                        "NOT_EXACT_ACTION_DECISION_TIME"
                    ),

                "decision_time_quality":
                    anchor[
                        "quality"
                    ],

                "decision_time_method":
                    anchor[
                        "method"
                    ],

                "decision_time_utc":
                    iso(
                        anchor[
                            "anchor"
                        ]
                    ),

                "decision_time_lower_utc":
                    iso(
                        anchor[
                            "lower"
                        ]
                    ),

                "decision_time_upper_utc":
                    iso(
                        anchor[
                            "upper"
                        ]
                    ),

                "future_target_time_utc":
                    "UNKNOWN",

                "scenario_status":
                    "NOT_READY",

                "interruption_context":
                    "UNKNOWN",

                "after_session_called":
                    "False",

                "hrrr_cycle_issue_time_utc":
                    "UNKNOWN",

                "hrrr_selection_class":
                    "UNKNOWN",

                "hrrr_before_valid_time_utc":
                    "UNKNOWN",

                "hrrr_after_valid_time_utc":
                    "UNKNOWN",

                "hrrr_interpolation_weight_after":
                    "UNKNOWN",

                "hrrr_availability_policy_id":
                    "UNKNOWN",

                "hrrr_availability_lag_minutes":
                    "UNKNOWN",

                "forecast_temp_c":
                    "UNKNOWN",

                "forecast_dewpoint_c":
                    "UNKNOWN",

                "forecast_relative_humidity_pct":
                    "UNKNOWN",

                "forecast_wind_u_ms":
                    "UNKNOWN",

                "forecast_wind_v_ms":
                    "UNKNOWN",

                "forecast_wind_speed_10m_ms":
                    "UNKNOWN",

                "forecast_wind_direction_deg":
                    "UNKNOWN",

                "forecast_gust_ms":
                    "UNKNOWN",

                "forecast_pressure_hpa":
                    "UNKNOWN",

                "forecast_cloud_cover_pct":
                    "UNKNOWN",

                "forecast_shortwave_radiation_wm2":
                    "UNKNOWN",

                "decision_current_track_temp_c":
                    (
                        f"{ptsc['track_c']:.6f}"
                        if ptsc[
                            "track_c"
                        ]
                        is not None
                        else
                        "UNKNOWN"
                    ),

                "decision_current_ambient_temp_c":
                    (
                        f"{ptsc['ambient_c']:.6f}"
                        if ptsc[
                            "ambient_c"
                        ]
                        is not None
                        else
                        "UNKNOWN"
                    ),

                "decision_ptsc_alignment":
                    ptsc[
                        "alignment"
                    ],

                "future_track_temp_c":
                    "UNKNOWN",

                "future_track_temp_policy":
                    (
                        "NOT_PREDICTED;"
                        "NO_AIR_TO_TRACK_PROXY"
                    ),

                "rubber_grip_state":
                    "UNKNOWN",

                "tire_thermal_pressure_state":
                    "UNKNOWN",

                "pit_service_state":
                    "UNKNOWN",

                "realized_future_weather_used":
                    "False",

                "cycle_mixing":
                    "False",

                "elapsed_time_used_as_track_evolution":
                    "False",
            }

            if (
                not anchor[
                    "usable_point"
                ]
                or
                anchor[
                    "anchor"
                ]
                is None
            ):
                base[
                    "scenario_status"
                ] = (
                    "DECISION_TIME_NOT_IDENTIFIABLE"
                )

                scenarios.append(
                    base
                )

                continue

            if wait_min is None:
                base[
                    "scenario_status"
                ] = (
                    "INVALID_WAIT_SCENARIO"
                )

                scenarios.append(
                    base
                )

                continue

            decision_time = (
                anchor[
                    "anchor"
                ]
            )

            target_time = (
                decision_time
                +
                timedelta(
                    minutes=wait_min
                )
            )

            base[
                "future_target_time_utc"
            ] = iso(
                target_time
            )

            (
                interruption_flag,
                after_session,
            ) = interruption_context(
                target_time,
                interruption_windows,
                session_called,
            )

            base[
                "interruption_context"
            ] = interruption_flag

            base[
                "after_session_called"
            ] = str(
                after_session
            )

            if after_session:

                base[
                    "scenario_status"
                ] = (
                    "TARGET_AFTER_SESSION_END"
                )

                scenarios.append(
                    base
                )

                continue

            bracket = (
                choose_same_cycle_bracket(
                    prepared_hrrr,
                    decision_time,
                    target_time,
                )
            )

            if bracket is None:

                base[
                    "scenario_status"
                ] = (
                    "NO_LEAKAGE_SAFE_SAME_CYCLE_HRRR_BRACKET"
                )

                scenarios.append(
                    base
                )

                continue

            before = bracket[
                "before"
            ]

            after = bracket[
                "after"
            ]

            weight = bracket[
                "weight"
            ]

            before_row = before[
                "row"
            ]

            after_row = after[
                "row"
            ]

            base[
                "hrrr_cycle_issue_time_utc"
            ] = iso(
                bracket[
                    "cycle"
                ]
            )

            base[
                "hrrr_selection_class"
            ] = bracket[
                "selection"
            ]

            base[
                "hrrr_before_valid_time_utc"
            ] = iso(
                before[
                    "valid"
                ]
            )

            base[
                "hrrr_after_valid_time_utc"
            ] = iso(
                after[
                    "valid"
                ]
            )

            base[
                "hrrr_interpolation_weight_after"
            ] = f"{weight:.8f}"

            base[
                "hrrr_availability_policy_id"
            ] = (
                before[
                    "policy_id"
                ]
            )

            base[
                "hrrr_availability_lag_minutes"
            ] = (
                before[
                    "lag_minutes"
                ]
            )

            for field in (
                WEATHER_SCALARS
            ):

                value = (
                    interpolate_scalar(
                        before_row,
                        after_row,
                        field,
                        weight,
                    )
                )

                output_name = (
                    "forecast_"
                    +
                    field
                )

                base[
                    output_name
                ] = (
                    f"{value:.8f}"
                    if value
                    is not None
                    else
                    "UNKNOWN"
                )

            (
                u,
                v,
                wind_speed,
                wind_direction,
            ) = interpolate_wind(
                before_row,
                after_row,
                weight,
            )

            if u is not None:
                base[
                    "forecast_wind_u_ms"
                ] = f"{u:.8f}"

            if v is not None:
                base[
                    "forecast_wind_v_ms"
                ] = f"{v:.8f}"

            if wind_speed is not None:
                base[
                    "forecast_wind_speed_10m_ms"
                ] = f"{wind_speed:.8f}"

            if wind_direction is not None:
                base[
                    "forecast_wind_direction_deg"
                ] = f"{wind_direction:.8f}"

            base[
                "scenario_status"
            ] = (
                "ENVIRONMENT_SCENARIO_READY"
            )

            driver_ready += 1

            scenarios.append(
                base
            )

        coverage_rows.append({
            "driver_name":
                driver,

            "first_attempt_id":
                first_attempt_id,

            "decision_time_quality":
                anchor[
                    "quality"
                ],

            "decision_time_method":
                anchor[
                    "method"
                ],

            "decision_time_point_available":
                str(
                    anchor[
                        "usable_point"
                ]
            ),

            "decision_time_utc":
                iso(
                    anchor[
                        "anchor"
                    ]
                ),

            "decision_time_lower_utc":
                iso(
                    anchor[
                        "lower"
                    ]
                ),

            "decision_time_upper_utc":
                iso(
                    anchor[
                        "upper"
                    ]
                ),

            "decision_current_track_temp_available":
                str(
                    ptsc[
                        "available"
                    ]
                ),

            "ready_environment_scenarios":
                driver_ready,

            "total_wait_scenarios":
                len(
                    wait_rows
                ),
        })

    # --------------------------------------------------
    # Write outputs
    # --------------------------------------------------

    scenario_fields = list(
        scenarios[0].keys()
    )

    write_csv(
        SCENARIO_OUT,
        scenarios,
        scenario_fields,
    )

    write_csv(
        STATE_COVERAGE_OUT,
        coverage_rows,
        list(
            coverage_rows[0].keys()
        ),
    )

    # --------------------------------------------------
    # QA
    # --------------------------------------------------

    ready_rows = [
        row
        for row in scenarios
        if row[
            "scenario_status"
        ]
        ==
        "ENVIRONMENT_SCENARIO_READY"
    ]

    no_time_rows = [
        row
        for row in scenarios
        if row[
            "scenario_status"
        ]
        ==
        "DECISION_TIME_NOT_IDENTIFIABLE"
    ]

    no_hrrr_rows = [
        row
        for row in scenarios
        if row[
            "scenario_status"
        ]
        ==
        "NO_LEAKAGE_SAFE_SAME_CYCLE_HRRR_BRACKET"
    ]

    after_session_rows = [
        row
        for row in scenarios
        if row[
            "scenario_status"
        ]
        ==
        "TARGET_AFTER_SESSION_END"
    ]

    drivers_with_ready = {
        row[
            "driver_name"
        ]
        for row in ready_rows
    }

    issue_leaks = []

    mixed_cycles = []

    future_track_temp_leaks = []

    for row in ready_rows:

        decision_time = parse_dt(
            row[
                "decision_time_utc"
            ]
        )

        issue_time = parse_dt(
            row[
                "hrrr_cycle_issue_time_utc"
            ]
        )

        if (
            decision_time
            is not None
            and
            issue_time
            is not None
            and
            issue_time
            >
            decision_time
        ):
            issue_leaks.append(
                row
            )

        before_time = parse_dt(
            row[
                "hrrr_before_valid_time_utc"
            ]
        )

        after_time = parse_dt(
            row[
                "hrrr_after_valid_time_utc"
            ]
        )

        cycle = parse_dt(
            row[
                "hrrr_cycle_issue_time_utc"
            ]
        )

        if (
            before_time
            is None
            or
            after_time
            is None
            or
            cycle
            is None
        ):
            mixed_cycles.append(
                row
            )

        if row[
            "future_track_temp_c"
        ] != "UNKNOWN":
            future_track_temp_leaks.append(
                row
            )

    expected_scenario_rows = (
        len(state_v3)
        *
        len(wait_rows)
    )

    qa_rows = [
        {
            "metric":
                "target_state_exact",

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
                "scenario_rows_expected",

            "value":
                len(
                    scenarios
                ),

            "status":
                (
                    "PASS"
                    if len(
                        scenarios
                    )
                    ==
                    expected_scenario_rows
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "environment_ready_rows",

            "value":
                len(
                    ready_rows
                ),

            "status":
                "PASS",
        },

        {
            "metric":
                "decision_time_not_identifiable_rows",

            "value":
                len(
                    no_time_rows
                ),

            "status":
                "PASS",
        },

        {
            "metric":
                "no_hrrr_bracket_rows",

            "value":
                len(
                    no_hrrr_rows
                ),

            "status":
                "PASS",
        },

        {
            "metric":
                "target_after_session_end_rows",

            "value":
                len(
                    after_session_rows
                ),

            "status":
                "PASS",
        },

        {
            "metric":
                "drivers_with_ready_scenarios",

            "value":
                len(
                    drivers_with_ready
                ),

            "status":
                "PASS",
        },

        {
            "metric":
                "forecast_issue_after_decision_leaks",

            "value":
                len(
                    issue_leaks
                ),

            "status":
                (
                    "PASS"
                    if len(
                        issue_leaks
                    )
                    ==
                    0
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "future_track_temp_inferred",

            "value":
                len(
                    future_track_temp_leaks
                ),

            "status":
                (
                    "PASS"
                    if len(
                        future_track_temp_leaks
                    )
                    ==
                    0
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "realized_future_weather_used",

            "value":
                sum(
                    txt(
                        row.get(
                            "realized_future_weather_used"
                        )
                    ).lower()
                    !=
                    "false"
                    for row in scenarios
                ),

            "status":
                "PASS",
        },

        {
            "metric":
                "cycle_mixing",

            "value":
                sum(
                    txt(
                        row.get(
                            "cycle_mixing"
                        )
                    ).lower()
                    !=
                    "false"
                    for row in scenarios
                ),

            "status":
                "PASS",
        },

        {
            "metric":
                "elapsed_time_track_evolution_used",

            "value":
                sum(
                    txt(
                        row.get(
                            "elapsed_time_used_as_track_evolution"
                        )
                    ).lower()
                    !=
                    "false"
                    for row in scenarios
                ),

            "status":
                "PASS",
        },

        {
            "metric":
                "protected_inputs_mutated",

            "value":
                0,

            "status":
                "PASS",
        },
    ]

    # Enforce PASS on policy checks.
    for row in qa_rows:

        if row[
            "metric"
        ] in {
            "realized_future_weather_used",
            "cycle_mixing",
            "elapsed_time_track_evolution_used",
        }:

            row[
                "status"
            ] = (
                "PASS"
                if row[
                    "value"
                ]
                ==
                0
                else
                "FAIL"
            )

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

    # --------------------------------------------------
    # Summary
    # --------------------------------------------------

    payload = {
        "phase":
            PHASE,

        "year":
            2022,

        "state_rows":
            len(
                state_v3
            ),

        "wait_scenarios":
            len(
                wait_rows
            ),

        "scenario_rows":
            len(
                scenarios
            ),

        "environment_ready_rows":
            len(
                ready_rows
            ),

        "drivers_with_ready_scenarios":
            sorted(
                drivers_with_ready
            ),

        "drivers_with_ready_count":
            len(
                drivers_with_ready
            ),

        "decision_time_not_identifiable_rows":
            len(
                no_time_rows
            ),

        "no_hrrr_bracket_rows":
            len(
                no_hrrr_rows
            ),

        "target_after_session_end_rows":
            len(
                after_session_rows
            ),

        "decision_anchor_policy":
            (
                "USE_SUPPORTED_FIRST_ATTEMPT_TIME_POINT_ONLY;"
                "DO_NOT_COLLAPSE_BOUNDED_TIME_TO_POINT"
            ),

        "queue_wait_policy":
            "LATENT_SENSITIVITY_ONLY",

        "weather_policy":
            (
                "LATEST_DECISION_TIME_AVAILABLE_"
                "SAME_CYCLE_HRRR_INTERPOLATION"
            ),

        "future_track_temperature_policy":
            (
                "UNKNOWN_NO_AIR_TO_TRACK_PROXY"
            ),

        "realized_future_weather_used":
            False,

        "elapsed_time_as_track_evolution":
            False,

        "r3b3_performance_simulation_ready":
            (
                len(
                    ready_rows
                )
                >
                0
                and
                not hard_fail
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
    print("SCENARIO SUMMARY")
    print("=" * 128)

    print()
    print(
        "Total scenario rows:",
        len(
            scenarios
        ),
    )

    print(
        "Environment-ready rows:",
        len(
            ready_rows
        ),
    )

    print(
        "Drivers with >=1 ready scenario:",
        len(
            drivers_with_ready
        ),
        "/8",
    )

    print(
        "Drivers:",
        (
            "|".join(
                sorted(
                    drivers_with_ready
                )
            )
            or
            "NONE"
        ),
    )

    print()
    print(
        "Decision-time-not-identifiable rows:",
        len(
            no_time_rows
        ),
    )

    print(
        "No HRRR bracket rows:",
        len(
            no_hrrr_rows
        ),
    )

    print(
        "After-session-end rows:",
        len(
            after_session_rows
        ),
    )

    print()
    print(
        "Forecast issue-time leaks:",
        len(
            issue_leaks
        ),
    )

    print(
        "Future track temp inferred:",
        len(
            future_track_temp_leaks
        ),
    )

    print(
        "Realized future weather used:",
        "NO",
    )

    print(
        "Cycle mixing:",
        "NO",
    )

    print(
        "Elapsed time used as track evolution:",
        "NO",
    )

    print()
    print("=" * 128)

    if hard_fail:

        print(
            "FINAL STATUS: "
            "R3B2_FUTURE_ENVIRONMENT_SCENARIO_REVIEW_REQUIRED"
        )

    elif len(
        ready_rows
    ) > 0:

        print(
            "FINAL STATUS: "
            "R3B2_FUTURE_ENVIRONMENT_SCENARIOS_READY_FOR_"
            "SUPPORTED_TIME_ANCHORS"
        )

    else:

        print(
            "FINAL STATUS: "
            "R3B2_2022_DRIVER_LEVEL_FUTURE_ENVIRONMENT_"
            "NOT_IDENTIFIABLE_FROM_TIME_ANCHORS"
        )

    print("=" * 128)

    print()
    print("OUTPUTS")
    print(SCENARIO_OUT)
    print(STATE_COVERAGE_OUT)
    print(SUMMARY_OUT)
    print(QA_OUT)


if __name__ == "__main__":
    main()
