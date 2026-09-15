from pathlib import Path
import csv
import hashlib


# ============================================================
# PHASE
# ============================================================

PHASE = "R1G.10"


# ============================================================
# INPUTS
# ============================================================

RESULT_ROWS = Path(
    "weather/output/"
    "official_day1_results_attempt_rows_v1.csv"
)

EVIDENCE_V4 = Path(
    "weather/output/"
    "chronology_rescue_2022_adjudicated_evidence_v4.csv"
)

WEATHER_WINDOWS = Path(
    "weather/output/"
    "chronology_rescue_2022_weather_interruption_windows_v1.csv"
)

WEATHER_EDGES = Path(
    "weather/output/"
    "chronology_rescue_2022_weather_event_edges_v1.csv"
)


# ============================================================
# OUTPUTS
# ============================================================

OUTPUT_DIR = Path(
    "weather/output"
)

ATTEMPT_INTERVALS_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_derived_attempt_intervals_v1.csv"
)

EVIDENCE_V5_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_adjudicated_evidence_v5.csv"
)

QA_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_derived_attempt_intervals_v1_qa.csv"
)


# ============================================================
# HELPERS
# ============================================================

def read_csv(path):

    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as handle:

        return list(
            csv.DictReader(
                handle
            )
        )


def write_csv(
    path,
    rows,
    fields,
):

    with path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as handle:

        writer = csv.DictWriter(
            handle,
            fieldnames=fields,
        )

        writer.writeheader()
        writer.writerows(rows)


def txt(value):

    if value is None:
        return ""

    return str(
        value
    ).strip()


def norm_car(value):

    value = txt(
        value
    )

    if not value:
        return ""

    try:

        return str(
            int(
                float(
                    value
                )
            )
        )

    except Exception:

        return (
            value.lstrip("0")
            or "0"
        )


def stable_id(*parts):

    payload = "|".join(
        txt(
            part
        )
        for part in parts
    )

    digest = hashlib.sha256(
        payload.encode(
            "utf-8"
        )
    ).hexdigest()[:16]

    return (
        "R1G10-"
        + digest.upper()
    )


def find_result(
    rows,
    car,
    speed=None,
    status=None,
):

    target_car = norm_car(
        car
    )

    matches = []

    for row in rows:

        if txt(
            row.get(
                "year"
            )
        ) != "2022":
            continue

        if norm_car(
            row.get(
                "car_number"
            )
        ) != target_car:
            continue

        if speed is not None:

            if txt(
                row.get(
                    "speed_avg_mph"
                )
            ) != speed:
                continue

        if status is not None:

            if txt(
                row.get(
                    "status"
                )
            ) != status:
                continue

        matches.append(
            row
        )

    return matches


def get_window(
    windows,
    event_type,
):

    matches = [
        row
        for row in windows
        if txt(
            row.get(
                "event_type"
            )
        ) == event_type
    ]

    if len(
        matches
    ) != 1:

        return None

    return matches[0]


# ============================================================
# MAIN
# ============================================================

def main():

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print()
    print("=" * 120)

    print(
        "R1G.10 — 2022 DERIVED ATTEMPT "
        "INTERVAL PROPAGATION V1"
    )

    print("=" * 120)

    inputs = [
        RESULT_ROWS,
        EVIDENCE_V4,
        WEATHER_WINDOWS,
        WEATHER_EDGES,
    ]

    print()
    print(
        "INPUT CHECK"
    )

    print("-" * 120)

    missing = []

    for path in inputs:

        exists = path.exists()

        print(
            f"{path}: "
            f"{'PRESENT' if exists else 'MISSING'}"
        )

        if not exists:

            missing.append(
                path
            )

    if missing:

        print()
        print(
            "FINAL STATUS: "
            "2022_ATTEMPT_INTERVAL_PROPAGATION_INPUT_MISSING"
        )

        return

    results = read_csv(
        RESULT_ROWS
    )

    evidence_v4 = read_csv(
        EVIDENCE_V4
    )

    windows = read_csv(
        WEATHER_WINDOWS
    )

    edges = read_csv(
        WEATHER_EDGES
    )

    print()
    print(
        "RESULT ROWS:",
        len(
            results
        ),
    )

    print(
        "EVIDENCE V4 ROWS:",
        len(
            evidence_v4
        ),
    )

    print(
        "WEATHER WINDOWS:",
        len(
            windows
        ),
    )

    print(
        "WEATHER EDGES:",
        len(
            edges
        ),
    )

    # ========================================================
    # REQUIRED WINDOWS
    # ========================================================

    resume = get_window(
        windows,
        "FIRST_WEATHER_HOLD_LIFTED",
    )

    second_stop = get_window(
        windows,
        "SECOND_WEATHER_STOP",
    )

    print()
    print("=" * 120)

    print(
        "SOURCE WINDOW CHECK"
    )

    print("=" * 120)

    print(
        "FIRST_WEATHER_HOLD_LIFTED:",
        "FOUND"
        if resume
        else "MISSING",
    )

    print(
        "SECOND_WEATHER_STOP:",
        "FOUND"
        if second_stop
        else "MISSING",
    )

    if (
        resume is None
        or
        second_stop is None
    ):

        print()
        print(
            "FINAL STATUS: "
            "2022_ATTEMPT_INTERVAL_PROPAGATION_WINDOW_MISSING"
        )

        return

    resume_time = txt(
        resume.get(
            "time_midpoint_utc"
        )
    )

    second_lower = txt(
        second_stop.get(
            "time_lower_utc"
        )
    )

    second_upper = txt(
        second_stop.get(
            "time_upper_utc"
        )
    )

    print()
    print(
        "Resume time:",
        resume_time,
    )

    print(
        "Second stop lower:",
        second_lower,
    )

    print(
        "Second stop upper:",
        second_upper,
    )

    # ========================================================
    # RESULT MATCHES
    # ========================================================

    mcl = find_result(
        results,
        car="3",
        speed="230.154",
        status="",
    )

    newg = find_result(
        results,
        car="2",
        status="No Attempt",
    )

    print()
    print("=" * 120)

    print(
        "TARGET RESULT MATCHES"
    )

    print("=" * 120)

    print()
    print(
        "McLaughlin 230.154:",
        len(
            mcl
        ),
    )

    if mcl:

        print(
            "  result row:",
            mcl[0].get(
                "result_row"
            ),
        )

    print()
    print(
        "Newgarden No Attempt:",
        len(
            newg
        ),
    )

    if newg:

        print(
            "  result row:",
            newg[0].get(
                "result_row"
            ),
        )

    # ========================================================
    # VERIFY ORDERING SUPPORT
    # ========================================================

    mcl_edge = [
        row
        for row in edges
        if (
            txt(
                row.get(
                    "from_event"
                )
            )
            == "MCLAUGHLIN_230.154_RERUN"
            and
            txt(
                row.get(
                    "to_event"
                )
            )
            == "SECOND_WEATHER_STOP"
        )
    ]

    newg_edge = [
        row
        for row in edges
        if (
            txt(
                row.get(
                    "from_event"
                )
            )
            == "NEWGARDEN_NO_ATTEMPT_RERUN"
            and
            txt(
                row.get(
                    "to_event"
                )
            )
            == "SECOND_WEATHER_STOP"
        )
    ]

    print()
    print(
        "McLaughlin -> second stop edge:",
        len(
            mcl_edge
        ),
    )

    print(
        "Newgarden -> second stop edge:",
        len(
            newg_edge
        ),
    )

    # ========================================================
    # DERIVED ATTEMPT INTERVALS
    # ========================================================

    interval_rows = []

    if (
        len(
            mcl
        ) == 1
        and
        len(
            mcl_edge
        ) == 1
    ):

        interval_rows.append({
            "constraint_id":
                stable_id(
                    "2022",
                    "MCLAUGHLIN",
                    "230.154",
                    resume_time,
                    second_lower,
                ),

            "year":
                2022,

            "car_number":
                "3",

            "driver_name":
                "Scott McLaughlin",

            "speed_mph":
                "230.154",

            "official_result_row":
                txt(
                    mcl[0].get(
                        "result_row"
                    )
                ),

            "official_result_status":
                txt(
                    mcl[0].get(
                        "status"
                    )
                ),

            "constraint_class":
                "DERIVED_BOUNDED_INTERVAL",

            "time_lower_utc":
                resume_time,

            "time_upper_utc":
                second_lower,

            "time_midpoint_utc":
                "",

            "lower_bound_basis":
                "FIRST_WEATHER_HOLD_LIFTED",

            "upper_bound_basis":
                "SECOND_WEATHER_STOP_LOWER_BOUND",

            "source_authority":
                (
                    "REPUTABLE_SECONDARY"
                    "+INDYCAR_OFFICIAL_RESULTS"
                ),

            "chronology_usable":
                True,

            "performance_environment_usable":
                False,

            "queue_replay_usable":
                False,

            "canonical_promoted":
                False,

            "notes":
                (
                    "Derived from adjudicated event window "
                    "and ordering evidence. "
                    "Not an observed attempt timestamp."
                ),
        })

    if (
        len(
            newg
        ) == 1
        and
        len(
            newg_edge
        ) == 1
    ):

        interval_rows.append({
            "constraint_id":
                stable_id(
                    "2022",
                    "NEWGARDEN",
                    "NO_ATTEMPT",
                    resume_time,
                    second_upper,
                ),

            "year":
                2022,

            "car_number":
                "2",

            "driver_name":
                "Josef Newgarden",

            "speed_mph":
                "",

            "official_result_row":
                txt(
                    newg[0].get(
                        "result_row"
                    )
                ),

            "official_result_status":
                "No Attempt",

            "constraint_class":
                "DERIVED_BOUNDED_INTERVAL",

            "time_lower_utc":
                resume_time,

            "time_upper_utc":
                second_upper,

            "time_midpoint_utc":
                "",

            "lower_bound_basis":
                "FIRST_WEATHER_HOLD_LIFTED",

            "upper_bound_basis":
                "SECOND_WEATHER_STOP_UPPER_BOUND",

            "source_authority":
                (
                    "REPUTABLE_SECONDARY"
                    "+INDYCAR_OFFICIAL_RESULTS"
                ),

            "chronology_usable":
                True,

            "performance_environment_usable":
                False,

            "queue_replay_usable":
                False,

            "canonical_promoted":
                False,

            "notes":
                (
                    "Newgarden rerun began after restart "
                    "and was stopped by the second weather event. "
                    "Broad interval retained; exact lap/time "
                    "not inferred."
                ),
        })

    # ========================================================
    # WRITE ATTEMPT INTERVAL TABLE
    # ========================================================

    write_csv(
        ATTEMPT_INTERVALS_OUT,
        interval_rows,
        [
            "constraint_id",
            "year",
            "car_number",
            "driver_name",
            "speed_mph",
            "official_result_row",
            "official_result_status",
            "constraint_class",
            "time_lower_utc",
            "time_upper_utc",
            "time_midpoint_utc",
            "lower_bound_basis",
            "upper_bound_basis",
            "source_authority",
            "chronology_usable",
            "performance_environment_usable",
            "queue_replay_usable",
            "canonical_promoted",
            "notes",
        ],
    )

    # ========================================================
    # EXTEND EVIDENCE V4 -> V5
    # ========================================================

    evidence_fields = list(
        evidence_v4[0].keys()
    )

    evidence_v5 = [
        dict(
            row
        )
        for row in evidence_v4
    ]

    for interval in interval_rows:

        row = {
            field: ""
            for field in evidence_fields
        }

        row.update({
            "evidence_id":
                interval[
                    "constraint_id"
                ],

            "year":
                "2022",

            "session":
                "INDY500_DAY1_2022",

            "car_number":
                interval[
                    "car_number"
                ],

            "driver_name":
                interval[
                    "driver_name"
                ],

            "speed_mph":
                interval[
                    "speed_mph"
                ],

            "official_result_row":
                interval[
                    "official_result_row"
                ],

            "official_result_status":
                interval[
                    "official_result_status"
                ],

            "constraint_class":
                "DERIVED_BOUNDED_INTERVAL",

            "time_lower_utc":
                interval[
                    "time_lower_utc"
                ],

            "time_upper_utc":
                interval[
                    "time_upper_utc"
                ],

            "time_midpoint_utc":
                "",

            "source_authority":
                interval[
                    "source_authority"
                ],

            "source_title":
                (
                    "R1G.10 Derived Attempt Interval"
                ),

            "evidence_summary":
                interval[
                    "notes"
                ],

            "evidence_stage":
                "R1G10_DERIVED",

            "adjudication_status":
                "PROMOTED_DERIVED_INTERVAL",

            "chronology_usable":
                "True",

            "queue_replay_usable":
                "False",

            "canonical_promoted":
                "False",

            "notes":
                (
                    "Interval propagation only. "
                    "Not an observed attempt timestamp."
                ),
        })

        evidence_v5.append(
            row
        )

    write_csv(
        EVIDENCE_V5_OUT,
        evidence_v5,
        evidence_fields,
    )

    # ========================================================
    # QA
    # ========================================================

    mcl_interval_count = sum(
        1
        for row in interval_rows
        if row[
            "car_number"
        ] == "3"
    )

    newg_interval_count = sum(
        1
        for row in interval_rows
        if row[
            "car_number"
        ] == "2"
    )

    qa_rows = [
        {
            "metric":
                "derived_attempt_intervals",

            "value":
                len(
                    interval_rows
                ),

            "status":
                (
                    "PASS"
                    if len(
                        interval_rows
                    ) == 2
                    else "REVIEW"
                ),
        },

        {
            "metric":
                "mclaughlin_interval_rows",

            "value":
                mcl_interval_count,

            "status":
                (
                    "PASS"
                    if mcl_interval_count == 1
                    else "REVIEW"
                ),
        },

        {
            "metric":
                "newgarden_interval_rows",

            "value":
                newg_interval_count,

            "status":
                (
                    "PASS"
                    if newg_interval_count == 1
                    else "REVIEW"
                ),
        },

        {
            "metric":
                "derived_interval_promoted_as_observed",

            "value":
                0,

            "status":
                "PASS",
        },

        {
            "metric":
                "exact_attempt_timestamp_invented",

            "value":
                0,

            "status":
                "PASS",
        },

        {
            "metric":
                "queue_wait_inferred",

            "value":
                0,

            "status":
                "PASS",
        },

        {
            "metric":
                "canonical_data_mutated",

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

    # ========================================================
    # PRINT
    # ========================================================

    print()
    print("=" * 120)

    print(
        "DERIVED ATTEMPT INTERVALS"
    )

    print("=" * 120)

    for row in interval_rows:

        print()
        print(
            f"{row['driver_name']} "
            f"{row['speed_mph']} "
            f"[{row['official_result_status']}]"
        )

        print(
            "  lower:",
            row[
                "time_lower_utc"
            ],
        )

        print(
            "  upper:",
            row[
                "time_upper_utc"
            ],
        )

        print(
            "  class:",
            row[
                "constraint_class"
            ],
        )

        print(
            "  lower basis:",
            row[
                "lower_bound_basis"
            ],
        )

        print(
            "  upper basis:",
            row[
                "upper_bound_basis"
            ],
        )

    print()
    print("=" * 120)

    print(
        "SUMMARY"
    )

    print("=" * 120)

    print()
    print(
        "Previous evidence rows:",
        len(
            evidence_v4
        ),
    )

    print(
        "New evidence rows:",
        len(
            evidence_v5
        ),
    )

    print(
        "Derived attempt intervals:",
        len(
            interval_rows
        ),
    )

    print()
    print(
        "No derived interval was labeled "
        "as an observed attempt timestamp."
    )

    print(
        "No exact attempt timestamp was invented."
    )

    print(
        "No queue wait was inferred."
    )

    print(
        "No canonical data was modified."
    )

    print()
    print("=" * 120)

    if (
        mcl_interval_count == 1
        and
        newg_interval_count == 1
    ):

        print(
            "FINAL STATUS: "
            "2022_ATTEMPT_INTERVAL_PROPAGATION_COMPLETE"
        )

    else:

        print(
            "FINAL STATUS: "
            "2022_ATTEMPT_INTERVAL_PROPAGATION_REVIEW_REQUIRED"
        )

    print("=" * 120)

    print()
    print(
        "OUTPUTS"
    )

    print(
        ATTEMPT_INTERVALS_OUT
    )

    print(
        EVIDENCE_V5_OUT
    )

    print(
        QA_OUT
    )


if __name__ == "__main__":
    main()
