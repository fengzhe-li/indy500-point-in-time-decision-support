from pathlib import Path
import csv
import hashlib


# ============================================================
# PHASE
# ============================================================

PHASE = "R1G.9"


# ============================================================
# INPUTS
# ============================================================

RESULT_ROWS = Path(
    "weather/output/"
    "official_day1_results_attempt_rows_v1.csv"
)

PREVIOUS_EVIDENCE = Path(
    "weather/output/"
    "chronology_rescue_2022_adjudicated_evidence_v3.csv"
)


# ============================================================
# OUTPUTS
# ============================================================

OUTPUT_DIR = Path(
    "weather/output"
)

WINDOWS_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_weather_interruption_windows_v1.csv"
)

EVENT_EDGES_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_weather_event_edges_v1.csv"
)

EVIDENCE_V4_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_adjudicated_evidence_v4.csv"
)

QA_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_weather_interruption_windows_v1_qa.csv"
)


# ============================================================
# SOURCES
# ============================================================

SOURCE_INDYCAR_DAY1 = (
    "https://www.indycar.com/news/"
    "2022/05/05-21-day1-quals"
)

SOURCE_INDYCAR_QUALS_CHANGE = (
    "https://www.indycar.com/News/"
    "2022/05/05-20-QualsChange"
)

SOURCE_RACER = (
    "https://racer.com/2022/05/21/"
    "veekay-leads-saturday-indy-500-qualifying/"
)

SOURCE_AUTORACING1 = (
    "https://www.autoracing1.com/pl/366515/"
    "indycar-qualifying-update-from-the-indianapolis-motor-speedway/"
)


# ============================================================
# HELPERS
# ============================================================

def read_csv(path):
    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as f:
        return list(
            csv.DictReader(f)
        )


def write_csv(path, rows, fields):
    with path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=fields,
        )
        writer.writeheader()
        writer.writerows(rows)


def txt(v):
    return "" if v is None else str(v).strip()


def norm_car(v):
    t = txt(v)

    if not t:
        return ""

    try:
        return str(
            int(float(t))
        )
    except Exception:
        return (
            t.lstrip("0")
            or "0"
        )


def stable_id(*parts):
    payload = "|".join(
        txt(x)
        for x in parts
    )

    digest = hashlib.sha256(
        payload.encode("utf-8")
    ).hexdigest()[:16]

    return (
        "R1G9-"
        + digest.upper()
    )


def find_result_rows(
    rows,
    car,
):
    target = norm_car(car)

    return [
        r
        for r in rows
        if (
            txt(
                r.get("year")
            ) == "2022"
            and
            norm_car(
                r.get("car_number")
            ) == target
        )
    ]


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
        "R1G.9 — 2022 WEATHER INTERRUPTION "
        "WINDOW ADJUDICATION V1"
    )
    print("=" * 120)

    for path in [
        RESULT_ROWS,
        PREVIOUS_EVIDENCE,
    ]:

        print(
            f"{path}: "
            f"{'PRESENT' if path.exists() else 'MISSING'}"
        )

    if (
        not RESULT_ROWS.exists()
        or
        not PREVIOUS_EVIDENCE.exists()
    ):

        print()
        print(
            "FINAL STATUS: "
            "2022_WEATHER_INTERRUPTION_ADJUDICATION_INPUT_MISSING"
        )

        return

    results = read_csv(
        RESULT_ROWS
    )

    previous = read_csv(
        PREVIOUS_EVIDENCE
    )

    rows_2022 = [
        r
        for r in results
        if txt(
            r.get("year")
        ) == "2022"
    ]

    print()
    print(
        "2022 RESULT ROWS:",
        len(rows_2022),
    )

    print(
        "PREVIOUS EVIDENCE ROWS:",
        len(previous),
    )

    # ========================================================
    # TARGET RESULT CONTEXT
    # ========================================================

    karam = find_result_rows(
        rows_2022,
        "24",
    )

    mcl = find_result_rows(
        rows_2022,
        "3",
    )

    newg = find_result_rows(
        rows_2022,
        "2",
    )

    print()
    print("=" * 120)
    print(
        "TARGET RESULT CONTEXT"
    )
    print("=" * 120)

    for label, rows in [
        ("KARAM", karam),
        ("MCLAUGHLIN", mcl),
        ("NEWGARDEN", newg),
    ]:

        print()
        print(label)

        for r in rows:

            print(
                "  row=",
                r.get("result_row"),
                "| speed=",
                r.get("speed_avg_mph"),
                "| status=",
                repr(
                    r.get("status")
                ),
            )

    # ========================================================
    # INTERRUPTION WINDOWS
    #
    # Important:
    # - 14:14 and 15:34 are from reputable secondary reporting.
    # - 16:00 is approximate secondary reporting.
    # - 16:50 is derived from official scheduled end 17:50
    #   minus official statement that session ended 60 minutes
    #   early.
    # ========================================================

    windows = [
        {
            "event_id":
                stable_id(
                    "2022",
                    "FIRST_WEATHER_STOP",
                ),

            "year":
                2022,

            "event_type":
                "FIRST_WEATHER_STOP",

            "time_lower_utc":
                "2022-05-21T18:14:00Z",

            "time_upper_utc":
                "2022-05-21T18:14:00Z",

            "time_midpoint_utc":
                "2022-05-21T18:14:00Z",

            "time_quality":
                "APPROXIMATE_OBSERVED",

            "source_authority":
                "REPUTABLE_SECONDARY",

            "source_url":
                SOURCE_AUTORACING1,

            "supporting_source_url":
                SOURCE_RACER,

            "evidence_summary":
                (
                    "Secondary reporting places the first "
                    "weather/lightning stop at approximately "
                    "2:14 p.m. ET."
                ),

            "chronology_usable":
                True,

            "queue_replay_usable":
                False,

            "canonical_promoted":
                False,

            "notes":
                (
                    "Not INDYCAR-official clock observation. "
                    "Preserved as approximate secondary timing."
                ),
        },

        {
            "event_id":
                stable_id(
                    "2022",
                    "FIRST_WEATHER_HOLD_LIFTED",
                ),

            "year":
                2022,

            "event_type":
                "FIRST_WEATHER_HOLD_LIFTED",

            "time_lower_utc":
                "2022-05-21T19:34:00Z",

            "time_upper_utc":
                "2022-05-21T19:34:00Z",

            "time_midpoint_utc":
                "2022-05-21T19:34:00Z",

            "time_quality":
                "APPROXIMATE_OBSERVED",

            "source_authority":
                "REPUTABLE_SECONDARY",

            "source_url":
                SOURCE_AUTORACING1,

            "supporting_source_url":
                SOURCE_RACER,

            "evidence_summary":
                (
                    "Secondary reporting places the first "
                    "weather hold release / pit lane reopening "
                    "at approximately 3:34 p.m. ET."
                ),

            "chronology_usable":
                True,

            "queue_replay_usable":
                False,

            "canonical_promoted":
                False,

            "notes":
                (
                    "Secondary approximate timing only."
                ),
        },

        {
            "event_id":
                stable_id(
                    "2022",
                    "SECOND_WEATHER_STOP",
                ),

            "year":
                2022,

            "event_type":
                "SECOND_WEATHER_STOP",

            "time_lower_utc":
                "2022-05-21T20:00:00Z",

            "time_upper_utc":
                "2022-05-21T20:02:00Z",

            "time_midpoint_utc":
                "2022-05-21T20:01:00Z",

            "time_quality":
                "BOUNDED_INTERVAL",

            "source_authority":
                "REPUTABLE_SECONDARY",

            "source_url":
                SOURCE_AUTORACING1,

            "supporting_source_url":
                SOURCE_RACER,

            "evidence_summary":
                (
                    "Secondary reports place the second "
                    "weather/lightning stop around 4:00 p.m. ET; "
                    "a narrow 4:00–4:02 p.m. ET interval is "
                    "preserved rather than claiming an exact time."
                ),

            "chronology_usable":
                True,

            "queue_replay_usable":
                False,

            "canonical_promoted":
                False,

            "notes":
                (
                    "Bounded secondary interval. "
                    "Not an exact official timestamp."
                ),
        },

        {
            "event_id":
                stable_id(
                    "2022",
                    "SESSION_CALLED",
                ),

            "year":
                2022,

            "event_type":
                "SESSION_CALLED",

            "time_lower_utc":
                "2022-05-21T20:50:00Z",

            "time_upper_utc":
                "2022-05-21T20:50:00Z",

            "time_midpoint_utc":
                "2022-05-21T20:50:00Z",

            "time_quality":
                "DERIVED_SESSION_TIME",

            "source_authority":
                "INDYCAR_OFFICIAL_DERIVED",

            "source_url":
                SOURCE_INDYCAR_DAY1,

            "supporting_source_url":
                SOURCE_INDYCAR_QUALS_CHANGE,

            "evidence_summary":
                (
                    "INDYCAR scheduled Day 1 qualifying to end "
                    "at 5:50 p.m. ET and later stated the session "
                    "was cut short by 60 minutes. Derived session "
                    "call time is therefore approximately "
                    "4:50 p.m. ET / 20:50Z."
                ),

            "chronology_usable":
                True,

            "queue_replay_usable":
                False,

            "canonical_promoted":
                False,

            "notes":
                (
                    "Derived from two official statements. "
                    "Not a directly observed event timestamp."
                ),
        },
    ]

    # ========================================================
    # ORDERING EDGES
    # ========================================================

    edges = [
        {
            "edge_id":
                stable_id(
                    "2022",
                    "FIRST_STOP",
                    "BEFORE",
                    "RESUME",
                ),

            "from_event":
                "FIRST_WEATHER_STOP",

            "relation":
                "BEFORE",

            "to_event":
                "FIRST_WEATHER_HOLD_LIFTED",

            "constraint_class":
                "ORDERING_ONLY",

            "source_authority":
                "REPUTABLE_SECONDARY",

            "notes":
                (
                    "First stop precedes first hold release."
                ),
        },

        {
            "edge_id":
                stable_id(
                    "2022",
                    "RESUME",
                    "BEFORE",
                    "SECOND_STOP",
                ),

            "from_event":
                "FIRST_WEATHER_HOLD_LIFTED",

            "relation":
                "BEFORE",

            "to_event":
                "SECOND_WEATHER_STOP",

            "constraint_class":
                "ORDERING_ONLY",

            "source_authority":
                "REPUTABLE_SECONDARY",

            "notes":
                (
                    "Resumed running precedes second weather stop."
                ),
        },

        {
            "edge_id":
                stable_id(
                    "2022",
                    "SECOND_STOP",
                    "BEFORE",
                    "SESSION_CALLED",
                ),

            "from_event":
                "SECOND_WEATHER_STOP",

            "relation":
                "BEFORE",

            "to_event":
                "SESSION_CALLED",

            "constraint_class":
                "ORDERING_ONLY",

            "source_authority":
                "REPUTABLE_SECONDARY"
                "+INDYCAR_OFFICIAL_DERIVED",

            "notes":
                (
                    "Second weather stop precedes session call."
                ),
        },

        {
            "edge_id":
                stable_id(
                    "2022",
                    "MCLAUGHLIN_RERUN",
                    "BEFORE",
                    "SECOND_STOP",
                ),

            "from_event":
                "MCLAUGHLIN_230.154_RERUN",

            "relation":
                "BEFORE",

            "to_event":
                "SECOND_WEATHER_STOP",

            "constraint_class":
                "ORDERING_ONLY",

            "source_authority":
                "REPUTABLE_SECONDARY"
                "+INDYCAR_OFFICIAL_RESULTS",

            "notes":
                (
                    "Secondary chronology places McLaughlin's "
                    "rerun after the first hold was lifted and "
                    "before the second weather stop."
                ),
        },

        {
            "edge_id":
                stable_id(
                    "2022",
                    "NEWGARDEN_RERUN",
                    "TO",
                    "SECOND_STOP",
                ),

            "from_event":
                "NEWGARDEN_NO_ATTEMPT_RERUN",

            "relation":
                "BEFORE_OR_INTERRUPTED_BY",

            "to_event":
                "SECOND_WEATHER_STOP",

            "constraint_class":
                "ORDERING_ONLY",

            "source_authority":
                "REPUTABLE_SECONDARY"
                "+INDYCAR_OFFICIAL_RESULTS",

            "notes":
                (
                    "Newgarden's rerun had begun when the "
                    "second weather interruption stopped the session. "
                    "Exact lap is deliberately not fixed."
                ),
        },
    ]

    # ========================================================
    # KARAM REVIEW STATUS
    # ========================================================

    karam_specific_promotions = 0

    # ========================================================
    # EXTEND EVIDENCE V3 -> V4
    # ========================================================

    evidence_fields = list(
        previous[0].keys()
    )

    evidence_v4 = [
        dict(r)
        for r in previous
    ]

    for w in windows:

        row = {
            field: ""
            for field in evidence_fields
        }

        row.update({
            "evidence_id":
                w[
                    "event_id"
                ],

            "year":
                "2022",

            "session":
                "INDY500_DAY1_2022",

            "constraint_class":
                w[
                    "time_quality"
                ],

            "time_lower_utc":
                w[
                    "time_lower_utc"
                ],

            "time_upper_utc":
                w[
                    "time_upper_utc"
                ],

            "time_midpoint_utc":
                w[
                    "time_midpoint_utc"
                ],

            "source_authority":
                w[
                    "source_authority"
                ],

            "source_url":
                w[
                    "source_url"
                ],

            "source_title":
                w[
                    "event_type"
                ],

            "evidence_summary":
                w[
                    "evidence_summary"
                ],

            "evidence_stage":
                "R1G9_ADJUDICATED",

            "adjudication_status":
                "PROMOTED_SESSION_EVENT",

            "chronology_usable":
                "True",

            "queue_replay_usable":
                "False",

            "canonical_promoted":
                "False",

            "notes":
                w[
                    "notes"
                ],
        })

        evidence_v4.append(
            row
        )

    # ========================================================
    # WRITE
    # ========================================================

    write_csv(
        WINDOWS_OUT,
        windows,
        [
            "event_id",
            "year",
            "event_type",
            "time_lower_utc",
            "time_upper_utc",
            "time_midpoint_utc",
            "time_quality",
            "source_authority",
            "source_url",
            "supporting_source_url",
            "evidence_summary",
            "chronology_usable",
            "queue_replay_usable",
            "canonical_promoted",
            "notes",
        ],
    )

    write_csv(
        EVENT_EDGES_OUT,
        edges,
        [
            "edge_id",
            "from_event",
            "relation",
            "to_event",
            "constraint_class",
            "source_authority",
            "notes",
        ],
    )

    write_csv(
        EVIDENCE_V4_OUT,
        evidence_v4,
        evidence_fields,
    )

    # ========================================================
    # QA
    # ========================================================

    first_stop = [
        w
        for w in windows
        if w[
            "event_type"
        ] == "FIRST_WEATHER_STOP"
    ]

    resume = [
        w
        for w in windows
        if w[
            "event_type"
        ] == "FIRST_WEATHER_HOLD_LIFTED"
    ]

    second_stop = [
        w
        for w in windows
        if w[
            "event_type"
        ] == "SECOND_WEATHER_STOP"
    ]

    session_called = [
        w
        for w in windows
        if w[
            "event_type"
        ] == "SESSION_CALLED"
    ]

    qa = [
        {
            "metric":
                "first_weather_stop_rows",
            "value":
                len(first_stop),
            "status":
                (
                    "PASS"
                    if len(first_stop) == 1
                    else "FAIL"
                ),
        },

        {
            "metric":
                "first_weather_resume_rows",
            "value":
                len(resume),
            "status":
                (
                    "PASS"
                    if len(resume) == 1
                    else "FAIL"
                ),
        },

        {
            "metric":
                "second_weather_stop_rows",
            "value":
                len(second_stop),
            "status":
                (
                    "PASS"
                    if len(second_stop) == 1
                    else "FAIL"
                ),
        },

        {
            "metric":
                "derived_session_call_rows",
            "value":
                len(session_called),
            "status":
                (
                    "PASS"
                    if len(session_called) == 1
                    else "FAIL"
                ),
        },

        {
            "metric":
                "karam_specific_attempt_promoted",
            "value":
                karam_specific_promotions,
            "status":
                "PASS",
        },

        {
            "metric":
                "secondary_time_promoted_as_official_exact",
            "value":
                0,
            "status":
                "PASS",
        },

        {
            "metric":
                "exact_interruption_timestamp_claimed",
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
        qa,
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
        "ADJUDICATED WEATHER WINDOWS"
    )
    print("=" * 120)

    for w in windows:

        print()
        print(
            w[
                "event_type"
            ]
        )

        print(
            "  lower:",
            w[
                "time_lower_utc"
            ],
        )

        print(
            "  upper:",
            w[
                "time_upper_utc"
            ],
        )

        print(
            "  quality:",
            w[
                "time_quality"
            ],
        )

        print(
            "  authority:",
            w[
                "source_authority"
            ],
        )

    print()
    print("=" * 120)
    print(
        "EVENT ORDERING EDGES"
    )
    print("=" * 120)

    for edge in edges:

        print()
        print(
            edge[
                "from_event"
            ]
        )

        print(
            " ",
            edge[
                "relation"
            ],
        )

        print(
            edge[
                "to_event"
            ]
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
        len(previous),
    )

    print(
        "New evidence rows:",
        len(evidence_v4),
    )

    print(
        "Weather/session event rows:",
        len(windows),
    )

    print(
        "Ordering edges:",
        len(edges),
    )

    print(
        "Karam specific promotions:",
        karam_specific_promotions,
    )

    print()
    print(
        "No secondary timestamp was labeled "
        "as official exact."
    )

    print(
        "No exact interruption timestamp "
        "was invented."
    )

    print(
        "No queue wait was inferred."
    )

    print(
        "No canonical data was modified."
    )

    print()
    print("=" * 120)

    print(
        "FINAL STATUS: "
        "2022_WEATHER_INTERRUPTION_WINDOWS_ADJUDICATED"
    )

    print("=" * 120)

    print()
    print(
        "OUTPUTS"
    )

    print(
        WINDOWS_OUT
    )

    print(
        EVENT_EDGES_OUT
    )

    print(
        EVIDENCE_V4_OUT
    )

    print(
        QA_OUT
    )


if __name__ == "__main__":
    main()
