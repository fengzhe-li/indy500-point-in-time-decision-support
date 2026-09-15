from pathlib import Path
import csv
import json


# ============================================================
# PHASE
# ============================================================

PHASE = "R1G.5"


# ============================================================
# INPUTS
# ============================================================

RESULT_ROWS = Path(
    "weather/output/"
    "official_day1_results_attempt_rows_v1.csv"
)

EDITORIAL_CANDIDATES = Path(
    "weather/output/"
    "chronology_rescue_2022_editorial_candidates_v1.csv"
)

R1G3_EVIDENCE = Path(
    "weather/output/"
    "chronology_rescue_2022_official_evidence_v1.csv"
)


# ============================================================
# OUTPUTS
# ============================================================

OUTPUT_DIR = Path(
    "weather/output"
)

AUDIT_CSV = (
    OUTPUT_DIR
    / "chronology_rescue_2022_editorial_promotion_audit_v1.csv"
)

RESULT_CONTEXT_CSV = (
    OUTPUT_DIR
    / "chronology_rescue_2022_sato_marco_result_context_v1.csv"
)

QA_CSV = (
    OUTPUT_DIR
    / "chronology_rescue_2022_editorial_promotion_audit_v1_qa.csv"
)


# ============================================================
# TARGET CANDIDATES
# ============================================================

TARGET_CANDIDATES = [
    "R1G4-C0011",  # Sato forced to second attempt
    "R1G4-C0012",  # Sato first attempt -> next driver Marco
    "R1G4-C0023",  # Sato run -> next driver begins run
    "R1G4-C0024",  # Sato/Marco invalidation wording
    "R1G4-C0002",  # two interruptions, total 2h14, cut short
    "R1G4-C0015",  # first rain arrived
    "R1G4-C0048",  # official 11am session start
]


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
        "R1G.5 — 2022 EDITORIAL CHRONOLOGY "
        "PROMOTION-CANDIDATE AUDIT V1"
    )
    print("=" * 120)

    inputs = [
        RESULT_ROWS,
        EDITORIAL_CANDIDATES,
        R1G3_EVIDENCE,
    ]

    print()
    print("INPUT CHECK")
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
            "2022_EDITORIAL_PROMOTION_AUDIT_INPUT_MISSING"
        )
        return

    result_rows = read_csv(
        RESULT_ROWS
    )

    candidates = read_csv(
        EDITORIAL_CANDIDATES
    )

    r1g3 = read_csv(
        R1G3_EVIDENCE
    )

    results_2022 = [
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
        "2022 RESULT ROWS:",
        len(
            results_2022
        ),
    )

    print(
        "EDITORIAL CANDIDATES:",
        len(
            candidates
        ),
    )

    print(
        "EXISTING R1G.3 EVIDENCE:",
        len(
            r1g3
        ),
    )

    # ========================================================
    # TARGET CANDIDATE AUDIT
    # ========================================================

    audit_rows = []

    print()
    print("=" * 120)
    print(
        "TARGET EDITORIAL CANDIDATES"
    )
    print("=" * 120)

    for candidate_id in TARGET_CANDIDATES:

        matches = [
            row
            for row in candidates
            if txt(
                row.get(
                    "candidate_id"
                )
            ) == candidate_id
        ]

        print()
        print("-" * 120)
        print(
            candidate_id
        )
        print("-" * 120)

        print(
            "MATCH COUNT:",
            len(
                matches
            ),
        )

        if len(
            matches
        ) != 1:

            audit_rows.append({
                "candidate_id":
                    candidate_id,

                "found":
                    False,

                "source_id":
                    "",

                "sentence":
                    "",

                "review_class":
                    "UNRESOLVED",

                "proposed_constraint":
                    "",

                "automatic_promotion":
                    False,

                "notes":
                    "Candidate missing or non-unique.",
            })

            continue

        row = matches[0]

        sentence = txt(
            row.get(
                "sentence"
            )
        )

        print(
            "SOURCE:",
            row.get(
                "source_id"
            ),
        )

        print(
            "SENTENCE:"
        )

        print(
            sentence
        )

        print(
            "TIMES:",
            row.get(
                "explicit_clock_times"
            ),
        )

        print(
            "RELATIVE:",
            row.get(
                "relative_time_terms"
            ),
        )

        print(
            "ATTEMPTS:",
            row.get(
                "attempt_terms"
            ),
        )

        print(
            "ACTIONS:",
            row.get(
                "action_terms"
            ),
        )

        # ----------------------------------------------------
        # Conservative proposed semantics
        # ----------------------------------------------------

        if candidate_id == "R1G4-C0011":

            review_class = (
                "ATTEMPT_ORDERING_CANDIDATE"
            )

            proposed = (
                "SATO_232.196_FAILED_ATTEMPT "
                "< SATO_SECOND_ATTEMPT"
            )

            notes = (
                "Potential new same-car ordering constraint. "
                "Must identify the second attempt uniquely "
                "from official Results evidence before promotion."
            )

        elif candidate_id in {
            "R1G4-C0012",
            "R1G4-C0023",
            "R1G4-C0024",
        }:

            review_class = (
                "SATO_MARCO_ORDERING_SUPPORT"
            )

            proposed = (
                "SATO_232.196_FAILED_ATTEMPT "
                "< MARCO_NEXT_QUALIFYING_ATTEMPT"
            )

            notes = (
                "Supports existing R1G.3 ordering. "
                "Do not select a specific Marco result row "
                "until his rows are audited."
            )

        elif candidate_id == "R1G4-C0002":

            review_class = (
                "SESSION_INTERRUPTION_AGGREGATE"
            )

            proposed = (
                "TWO_WEATHER_INTERRUPTION_PERIODS;"
                "TOTAL_INTERRUPTION_DURATION=134_MINUTES;"
                "SESSION_CUT_SHORT_BY=60_MINUTES"
            )

            notes = (
                "Session-level evidence only. "
                "No individual interruption start/end time."
            )

        elif candidate_id == "R1G4-C0015":

            review_class = (
                "INTERRUPTION_ORDERING_ONLY"
            )

            proposed = (
                "FIRST_RAIN_AFTER_INITIAL_DRY_RUNNING"
            )

            notes = (
                "No clock time in sentence. "
                "Do not normalize to a timestamp."
            )

        elif candidate_id == "R1G4-C0048":

            review_class = (
                "SESSION_BOUNDARY_SUPPORT"
            )

            proposed = (
                "SESSION_START_2022-05-21T15:00:00Z"
            )

            notes = (
                "Official 11:00 ET session-start support. "
                "Not an attempt timestamp."
            )

        else:

            review_class = (
                "REVIEW"
            )

            proposed = ""

            notes = ""

        audit_rows.append({
            "candidate_id":
                candidate_id,

            "found":
                True,

            "source_id":
                txt(
                    row.get(
                        "source_id"
                    )
                ),

            "sentence":
                sentence,

            "review_class":
                review_class,

            "proposed_constraint":
                proposed,

            "automatic_promotion":
                False,

            "notes":
                notes,
        })

    # ========================================================
    # SATO / MARCO RESULT CONTEXT
    # ========================================================

    print()
    print("=" * 120)
    print(
        "SATO / MARCO OFFICIAL RESULT CONTEXT"
    )
    print("=" * 120)

    target_cars = {
        "51":
            "Takuma Sato",

        "98":
            "Marco Andretti",
    }

    result_context_rows = []

    for car, expected_driver in (
        target_cars.items()
    ):

        rows = [
            row
            for row in results_2022
            if normalize_car(
                row.get(
                    "car_number"
                )
            ) == normalize_car(
                car
            )
        ]

        print()
        print(
            f"CAR {car} | "
            f"{expected_driver} | "
            f"rows={len(rows)}"
        )

        for row in rows:

            print(
                "  "
                f"result_row={txt(row.get('result_row')):<3} | "
                f"speed={txt(row.get('speed_avg_mph')):<8} | "
                f"elapsed={txt(row.get('elapsed_time')):<12} | "
                f"status={txt(row.get('status'))!r}"
            )

            result_context_rows.append({
                "year":
                    2022,

                "car_number":
                    normalize_car(
                        car
                    ),

                "expected_driver":
                    expected_driver,

                "driver_name_pdf":
                    txt(
                        row.get(
                            "driver_name_pdf"
                        )
                    ),

                "result_row":
                    txt(
                        row.get(
                            "result_row"
                        )
                    ),

                "speed_avg_mph":
                    txt(
                        row.get(
                            "speed_avg_mph"
                        )
                    ),

                "elapsed_time":
                    txt(
                        row.get(
                            "elapsed_time"
                        )
                    ),

                "status":
                    txt(
                        row.get(
                            "status"
                        )
                    ),

                "source_file":
                    txt(
                        row.get(
                            "source_file"
                        )
                    ),

                "source_line_number":
                    txt(
                        row.get(
                            "source_line_number"
                        )
                    ),

                "chronology_assigned":
                    False,
            })

    # ========================================================
    # EXISTING R1G3 DUPLICATE/SUPPORT CHECK
    # ========================================================

    print()
    print("=" * 120)
    print(
        "EXISTING R1G.3 ORDERING EVIDENCE"
    )
    print("=" * 120)

    existing_ordering = [
        row
        for row in r1g3
        if txt(
            row.get(
                "constraint_class"
            )
        ) == "ORDERING_ONLY"
    ]

    for row in existing_ordering:

        print()
        print(
            "EVIDENCE ID:",
            row.get(
                "evidence_id"
            ),
        )

        print(
            "CAR:",
            row.get(
                "car_number"
            ),
        )

        print(
            "SPEED:",
            row.get(
                "speed_mph"
            ),
        )

        print(
            "RELATION:",
            row.get(
                "ordering_relation"
            ),
        )

    # ========================================================
    # WRITE
    # ========================================================

    write_csv(
        AUDIT_CSV,
        audit_rows,
        [
            "candidate_id",
            "found",
            "source_id",
            "sentence",
            "review_class",
            "proposed_constraint",
            "automatic_promotion",
            "notes",
        ],
    )

    write_csv(
        RESULT_CONTEXT_CSV,
        result_context_rows,
        [
            "year",
            "car_number",
            "expected_driver",
            "driver_name_pdf",
            "result_row",
            "speed_avg_mph",
            "elapsed_time",
            "status",
            "source_file",
            "source_line_number",
            "chronology_assigned",
        ],
    )

    # ========================================================
    # QA
    # ========================================================

    target_found = sum(
        1
        for row in audit_rows
        if row[
            "found"
        ]
    )

    sato_rows = [
        row
        for row in result_context_rows
        if row[
            "car_number"
        ] == "51"
    ]

    marco_rows = [
        row
        for row in result_context_rows
        if row[
            "car_number"
        ] == "98"
    ]

    sato_failed_232196 = [
        row
        for row in sato_rows
        if (
            row[
                "speed_avg_mph"
            ] == "232.196"
            and
            row[
                "status"
            ] == "Failed Attempt"
        )
    ]

    sato_231708 = [
        row
        for row in sato_rows
        if row[
            "speed_avg_mph"
        ] == "231.708"
    ]

    qa_rows = [
        {
            "metric":
                "target_candidates_expected",

            "value":
                len(
                    TARGET_CANDIDATES
                ),

            "status":
                "INFO",
        },

        {
            "metric":
                "target_candidates_found",

            "value":
                target_found,

            "status":
                (
                    "PASS"
                    if target_found
                    == len(
                        TARGET_CANDIDATES
                    )
                    else "REVIEW"
                ),
        },

        {
            "metric":
                "sato_result_rows",

            "value":
                len(
                    sato_rows
                ),

            "status":
                "INFO",
        },

        {
            "metric":
                "marco_result_rows",

            "value":
                len(
                    marco_rows
                ),

            "status":
                "INFO",
        },

        {
            "metric":
                "sato_232196_failed_unique",

            "value":
                len(
                    sato_failed_232196
                ),

            "status":
                (
                    "PASS"
                    if len(
                        sato_failed_232196
                    )
                    == 1
                    else "REVIEW"
                ),
        },

        {
            "metric":
                "sato_231708_unique",

            "value":
                len(
                    sato_231708
                ),

            "status":
                (
                    "PASS"
                    if len(
                        sato_231708
                    )
                    == 1
                    else "REVIEW"
                ),
        },

        {
            "metric":
                "chronology_auto_promoted",

            "value":
                0,

            "status":
                "PASS",
        },

        {
            "metric":
                "marco_specific_attempt_guessed",

            "value":
                0,

            "status":
                "PASS",
        },

        {
            "metric":
                "interruption_windows_invented",

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
        QA_CSV,
        qa_rows,
        [
            "metric",
            "value",
            "status",
        ],
    )

    # ========================================================
    # SUMMARY
    # ========================================================

    print()
    print("=" * 120)
    print(
        "R1G.5 SUMMARY"
    )
    print("=" * 120)

    print()
    print(
        "Target candidates found:",
        target_found,
        "/",
        len(
            TARGET_CANDIDATES
        ),
    )

    print(
        "Sato result rows:",
        len(
            sato_rows
        ),
    )

    print(
        "Marco result rows:",
        len(
            marco_rows
        ),
    )

    print(
        "Unique Sato 232.196 Failed Attempt:",
        len(
            sato_failed_232196
        ),
    )

    print(
        "Unique Sato 231.708 row:",
        len(
            sato_231708
        ),
    )

    print()
    print(
        "IMPORTANT:"
    )

    print(
        "No candidate was promoted automatically."
    )

    print(
        "No specific Marco attempt was selected "
        "from multiple result rows."
    )

    print(
        "No aggregate rain-delay duration was "
        "converted into invented interruption windows."
    )

    print(
        "No canonical data was modified."
    )

    print()
    print("=" * 120)

    if (
        target_found
        == len(
            TARGET_CANDIDATES
        )
        and
        len(
            sato_failed_232196
        )
        == 1
        and
        len(
            sato_231708
        )
        == 1
    ):

        print(
            "FINAL STATUS: "
            "2022_EDITORIAL_PROMOTION_CANDIDATES_AUDITED"
        )

    else:

        print(
            "FINAL STATUS: "
            "2022_EDITORIAL_PROMOTION_AUDIT_REVIEW_REQUIRED"
        )

    print("=" * 120)

    print()
    print("OUTPUTS")

    print(
        AUDIT_CSV
    )

    print(
        RESULT_CONTEXT_CSV
    )

    print(
        QA_CSV
    )


if __name__ == "__main__":
    main()
