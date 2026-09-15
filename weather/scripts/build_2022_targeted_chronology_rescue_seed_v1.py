from pathlib import Path
import csv
import json


# ============================================================
# PHASE
# ============================================================

PHASE = "R1G.3"


# ============================================================
# INPUT
# ============================================================

RESULT_ROWS = Path(
    "weather/output/"
    "official_day1_results_attempt_rows_v1.csv"
)


# ============================================================
# OUTPUT
# ============================================================

OUTPUT_DIR = Path(
    "weather/output"
)

EVIDENCE_CSV = (
    OUTPUT_DIR
    / "chronology_rescue_2022_official_evidence_v1.csv"
)

MATCH_CSV = (
    OUTPUT_DIR
    / "chronology_rescue_2022_result_row_matches_v1.csv"
)

QA_CSV = (
    OUTPUT_DIR
    / "chronology_rescue_2022_official_evidence_v1_qa.csv"
)


# ============================================================
# OFFICIAL SOURCES
# ============================================================

SOURCE_DAY1_RECAP = (
    "https://www.indycar.com/news/"
    "2022/05/05-21-day1-quals"
)

SOURCE_SATO_BUZZ = (
    "https://www.indycar.com/news/"
    "2022/05/05-21-buzz"
)

SOURCE_SCHEDULE = (
    "https://www.indycar.com/News/"
    "2022/05/05-20-QualsChange"
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
        newline="",
        encoding="utf-8-sig",
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


def normalize_car(value):

    text = txt(
        value
    )

    if not text:
        return ""

    try:

        return str(
            int(
                float(
                    text
                )
            )
        )

    except Exception:

        return (
            text.lstrip("0")
            or "0"
        )


def find_result_row(
    rows,
    car_number,
    speed,
    status=None,
):

    car_target = normalize_car(
        car_number
    )

    speed_target = txt(
        speed
    )

    candidates = []

    for row in rows:

        if txt(
            row.get(
                "year"
            )
        ) != "2022":

            continue

        if normalize_car(
            row.get(
                "car_number"
            )
        ) != car_target:

            continue

        if txt(
            row.get(
                "speed_avg_mph"
            )
        ) != speed_target:

            continue

        if status is not None:

            if txt(
                row.get(
                    "status"
                )
            ).lower() != txt(
                status
            ).lower():

                continue

        candidates.append(
            row
        )

    return candidates


def evidence_row(
    evidence_id,
    car_number,
    driver_name,
    speed_mph,
    result_row,
    result_status,
    constraint_class,
    lower_utc,
    upper_utc,
    related_car,
    relation,
    source_url,
    source_title,
    evidence_summary,
):

    midpoint = ""

    if (
        lower_utc
        == "2022-05-21T15:00:00Z"
        and
        upper_utc
        == "2022-05-21T15:15:00Z"
    ):

        midpoint = (
            "2022-05-21T15:07:30Z"
        )

    return {
        "evidence_id":
            evidence_id,

        "year":
            2022,

        "session":
            "INDY500_DAY1_2022",

        "car_number":
            normalize_car(
                car_number
            ),

        "driver_name":
            driver_name,

        "speed_mph":
            speed_mph,

        "official_result_row":
            result_row,

        "official_result_status":
            result_status,

        "constraint_class":
            constraint_class,

        "time_lower_utc":
            lower_utc,

        "time_upper_utc":
            upper_utc,

        "time_midpoint_utc":
            midpoint,

        "related_car_number":
            normalize_car(
                related_car
            )
            if related_car
            else "",

        "ordering_relation":
            relation,

        "source_authority":
            "INDYCAR_OFFICIAL_EDITORIAL",

        "source_url":
            source_url,

        "source_title":
            source_title,

        "evidence_summary":
            evidence_summary,

        "chronology_usable":
            True,

        "queue_replay_usable":
            False,

        "exact_run_start":
            False,

        "canonical_promoted":
            False,

        "notes":
            (
                "Additive rescue evidence only. "
                "No canonical mutation."
            ),
    }


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
        "R1G.3 — 2022 TARGETED OFFICIAL "
        "CHRONOLOGY RESCUE SEED V1"
    )

    print("=" * 120)

    if not RESULT_ROWS.exists():

        print(
            "MISSING INPUT:",
            RESULT_ROWS,
        )

        print(
            "FINAL STATUS: "
            "2022_CHRONOLOGY_RESCUE_INPUT_MISSING"
        )

        return

    result_rows = read_csv(
        RESULT_ROWS
    )

    rows_2022 = [
        row
        for row in result_rows
        if txt(
            row.get(
                "year"
            )
        ) == "2022"
    ]

    print()
    print(
        "2022 OFFICIAL RESULT ROWS:",
        len(
            rows_2022
        ),
    )

    # ========================================================
    # MATCH THREE FIRST-15-MINUTE ATTEMPTS
    # ========================================================

    targets = [
        {
            "car":
                "21",

            "driver":
                "Rinus VeeKay",

            "speed":
                "233.655",
        },

        {
            "car":
                "5",

            "driver":
                "Pato O'Ward",

            "speed":
                "233.037",
        },

        {
            "car":
                "7",

            "driver":
                "Felix Rosenqvist",

            "speed":
                "232.775",
        },
    ]

    match_rows = []
    evidence_rows = []

    for target in targets:

        matches = find_result_row(
            rows_2022,
            target[
                "car"
            ],
            target[
                "speed"
            ],
        )

        print()
        print(
            f"FIRST-15 TARGET "
            f"{target['driver']} "
            f"CAR {target['car']} "
            f"{target['speed']} mph"
        )

        print(
            "MATCH COUNT:",
            len(
                matches
            ),
        )

        if len(
            matches
        ) != 1:

            continue

        match = matches[0]

        print(
            "RESULT ROW:",
            match[
                "result_row"
            ],
        )

        print(
            "STATUS:",
            repr(
                match[
                    "status"
                ]
            ),
        )

        match_rows.append({
            "year":
                2022,

            "match_type":
                "FIRST_15_MINUTES",

            "car_number":
                normalize_car(
                    target[
                        "car"
                    ]
                ),

            "driver_name":
                target[
                    "driver"
                ],

            "speed_mph":
                target[
                    "speed"
                ],

            "official_result_row":
                match[
                    "result_row"
                ],

            "official_status":
                match[
                    "status"
                ],

            "source_file":
                match[
                    "source_file"
                ],

            "source_line_number":
                match[
                    "source_line_number"
                ],
        })

        evidence_rows.append(
            evidence_row(
                evidence_id=(
                    "R1G3-2022-"
                    + normalize_car(
                        target[
                            "car"
                        ]
                    )
                    + "-FIRST15"
                ),

                car_number=
                    target[
                        "car"
                    ],

                driver_name=
                    target[
                        "driver"
                    ],

                speed_mph=
                    target[
                        "speed"
                    ],

                result_row=
                    match[
                        "result_row"
                    ],

                result_status=
                    match[
                        "status"
                    ],

                constraint_class=
                    "BOUNDED_INTERVAL",

                lower_utc=
                    "2022-05-21T15:00:00Z",

                upper_utc=
                    "2022-05-21T15:15:00Z",

                related_car="",

                relation="",

                source_url=
                    SOURCE_DAY1_RECAP,

                source_title=(
                    "VeeKay Fastest at 233.6; "
                    "Chevy, Ganassi Flex on "
                    "Qualifying Day 1"
                ),

                evidence_summary=(
                    "INDYCAR states VeeKay, "
                    "O'Ward and Rosenqvist "
                    "made their qualifying "
                    "attempts within the first "
                    "15 minutes of the session. "
                    "Official session start was "
                    "11:00 ET."
                ),
            )
        )

    # ========================================================
    # SATO FAILED ATTEMPT
    # ========================================================

    sato_matches = find_result_row(
        rows_2022,
        "51",
        "232.196",
        "Failed Attempt",
    )

    print()
    print("=" * 120)
    print(
        "SATO 232.196 FAILED ATTEMPT"
    )
    print("=" * 120)

    print(
        "MATCH COUNT:",
        len(
            sato_matches
        ),
    )

    if len(
        sato_matches
    ) == 1:

        sato = (
            sato_matches[0]
        )

        print(
            "RESULT ROW:",
            sato[
                "result_row"
            ],
        )

        print(
            "STATUS:",
            sato[
                "status"
            ],
        )

        match_rows.append({
            "year":
                2022,

            "match_type":
                "SATO_BEFORE_ANDRETTI",

            "car_number":
                "51",

            "driver_name":
                "Takuma Sato",

            "speed_mph":
                "232.196",

            "official_result_row":
                sato[
                    "result_row"
                ],

            "official_status":
                sato[
                    "status"
                ],

            "source_file":
                sato[
                    "source_file"
                ],

            "source_line_number":
                sato[
                    "source_line_number"
                ],
        })

        evidence_rows.append(
            evidence_row(
                evidence_id=(
                    "R1G3-2022-51-"
                    "BEFORE-MARCO"
                ),

                car_number=
                    "51",

                driver_name=
                    "Takuma Sato",

                speed_mph=
                    "232.196",

                result_row=
                    sato[
                        "result_row"
                    ],

                result_status=
                    sato[
                        "status"
                    ],

                constraint_class=
                    "ORDERING_ONLY",

                lower_utc="",

                upper_utc="",

                related_car=
                    "98",

                relation=(
                    "THIS_ATTEMPT_BEFORE_"
                    "MARCO_ANDRETTI_ATTEMPT"
                ),

                source_url=
                    SOURCE_SATO_BUZZ,

                source_title=(
                    "Paddock Buzz: Sato "
                    "Sneaks into Fast 12 "
                    "after Eventful Day"
                ),

                evidence_summary=(
                    "INDYCAR states Sato's "
                    "232.196 mph run was "
                    "followed by Marco Andretti "
                    "beginning the next qualifying "
                    "run; Sato was penalized for "
                    "impeding Andretti."
                ),
            )
        )

    # ========================================================
    # SESSION-BOUNDARY SUPPORT RECORD
    #
    # Not attempt-level evidence; preserved only as support.
    # ========================================================

    evidence_rows.append({
        "evidence_id":
            "R1G3-2022-SESSION-START",

        "year":
            2022,

        "session":
            "INDY500_DAY1_2022",

        "car_number":
            "",

        "driver_name":
            "",

        "speed_mph":
            "",

        "official_result_row":
            "",

        "official_result_status":
            "",

        "constraint_class":
            "SESSION_BOUNDARY",

        "time_lower_utc":
            "2022-05-21T15:00:00Z",

        "time_upper_utc":
            "2022-05-21T15:00:00Z",

        "time_midpoint_utc":
            "2022-05-21T15:00:00Z",

        "related_car_number":
            "",

        "ordering_relation":
            "",

        "source_authority":
            "INDYCAR_OFFICIAL_EDITORIAL",

        "source_url":
            SOURCE_SCHEDULE,

        "source_title":
            (
                "Start of Indy Qualifying "
                "Moved Up Saturday Due to Forecast"
            ),

        "evidence_summary":
            (
                "Official revised schedule sets "
                "Day 1 qualifying start at "
                "11:00 ET on 21 May 2022."
            ),

        "chronology_usable":
            True,

        "queue_replay_usable":
            False,

        "exact_run_start":
            False,

        "canonical_promoted":
            False,

        "notes":
            (
                "Session boundary only; "
                "not an attempt timestamp."
            ),
    })

    # ========================================================
    # WRITE OUTPUTS
    # ========================================================

    write_csv(
        EVIDENCE_CSV,
        evidence_rows,
        [
            "evidence_id",
            "year",
            "session",
            "car_number",
            "driver_name",
            "speed_mph",
            "official_result_row",
            "official_result_status",
            "constraint_class",
            "time_lower_utc",
            "time_upper_utc",
            "time_midpoint_utc",
            "related_car_number",
            "ordering_relation",
            "source_authority",
            "source_url",
            "source_title",
            "evidence_summary",
            "chronology_usable",
            "queue_replay_usable",
            "exact_run_start",
            "canonical_promoted",
            "notes",
        ],
    )

    write_csv(
        MATCH_CSV,
        match_rows,
        [
            "year",
            "match_type",
            "car_number",
            "driver_name",
            "speed_mph",
            "official_result_row",
            "official_status",
            "source_file",
            "source_line_number",
        ],
    )

    # ========================================================
    # QA
    # ========================================================

    first15_count = sum(
        1
        for row in evidence_rows
        if row[
            "constraint_class"
        ] == "BOUNDED_INTERVAL"
    )

    ordering_count = sum(
        1
        for row in evidence_rows
        if row[
            "constraint_class"
        ] == "ORDERING_ONLY"
    )

    attempt_level_count = sum(
        1
        for row in evidence_rows
        if row[
            "car_number"
        ]
    )

    qa_rows = [
        {
            "metric":
                "official_result_rows_2022",

            "value":
                len(
                    rows_2022
                ),

            "status":
                (
                    "PASS"
                    if len(
                        rows_2022
                    )
                    == 44
                    else "REVIEW"
                ),
        },

        {
            "metric":
                "first_15_minute_attempt_matches",

            "value":
                first15_count,

            "status":
                (
                    "PASS"
                    if first15_count
                    == 3
                    else "REVIEW"
                ),
        },

        {
            "metric":
                "ordering_only_attempt_constraints",

            "value":
                ordering_count,

            "status":
                (
                    "PASS"
                    if ordering_count
                    >= 1
                    else "REVIEW"
                ),
        },

        {
            "metric":
                "attempt_level_chronology_constraints",

            "value":
                attempt_level_count,

            "status":
                (
                    "PASS"
                    if attempt_level_count
                    >= 4
                    else "REVIEW"
                ),
        },

        {
            "metric":
                "exact_attempt_timestamps_claimed",

            "value":
                0,

            "status":
                "PASS",
        },

        {
            "metric":
                "result_row_order_used_as_chronology",

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

        {
            "metric":
                "queue_wait_inferred",

            "value":
                0,

            "status":
                "PASS",
        },
    ]

    write_csv(
        QA_CSV,
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
        "2022 RESCUED CHRONOLOGY EVIDENCE"
    )
    print("=" * 120)

    for row in evidence_rows:

        print()
        print(
            row[
                "evidence_id"
            ]
        )

        print(
            "  class:",
            row[
                "constraint_class"
            ],
        )

        print(
            "  car:",
            row[
                "car_number"
            ],
        )

        print(
            "  driver:",
            row[
                "driver_name"
            ],
        )

        print(
            "  speed:",
            row[
                "speed_mph"
            ],
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
            "  relation:",
            row[
                "ordering_relation"
            ],
        )

    print()
    print("=" * 120)

    print(
        "SUMMARY"
    )

    print("=" * 120)

    print(
        "First-15-minute bounded attempts:",
        first15_count,
    )

    print(
        "Ordering-only attempt constraints:",
        ordering_count,
    )

    print(
        "Total attempt-level rescued constraints:",
        attempt_level_count,
    )

    print()
    print(
        "No exact attempt timestamp was claimed."
    )

    print(
        "No result-row ordering was used "
        "as chronology."
    )

    print(
        "No canonical data was modified."
    )

    print()
    print("=" * 120)

    if (
        first15_count == 3
        and
        ordering_count >= 1
    ):

        print(
            "FINAL STATUS: "
            "2022_TARGETED_CHRONOLOGY_RESCUE_SEEDED"
        )

    else:

        print(
            "FINAL STATUS: "
            "2022_TARGETED_CHRONOLOGY_RESCUE_REVIEW_REQUIRED"
        )

    print("=" * 120)

    print()
    print(
        "OUTPUTS"
    )

    print(
        EVIDENCE_CSV
    )

    print(
        MATCH_CSV
    )

    print(
        QA_CSV
    )


if __name__ == "__main__":
    main()
