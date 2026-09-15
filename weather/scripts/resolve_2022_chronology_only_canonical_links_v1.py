from pathlib import Path
import csv
import re


CANONICAL = Path(
    "data/canonical/v1/attempts.csv"
)

MATCH_V1 = Path(
    "weather/output/"
    "chronology_rescue_2022_result_to_canonical_attempt_matches_v1.csv"
)

UNRESOLVED_V1 = Path(
    "weather/output/"
    "chronology_rescue_2022_unresolved_attempt_links_v1.csv"
)

EVIDENCE_V5 = Path(
    "weather/output/"
    "chronology_rescue_2022_evidence_with_attempt_ids_v1.csv"
)

OUTPUT_DIR = Path(
    "weather/output"
)

MATCH_V2 = (
    OUTPUT_DIR
    / "chronology_rescue_2022_result_to_canonical_attempt_matches_v2.csv"
)

RESOLUTION_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_chronology_only_link_resolution_v1.csv"
)

EVIDENCE_V2 = (
    OUTPUT_DIR
    / "chronology_rescue_2022_evidence_with_attempt_ids_v2.csv"
)

QA_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_chronology_only_link_resolution_v1_qa.csv"
)


def read_csv(path):
    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as f:
        return list(csv.DictReader(f))


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
        return str(int(float(t)))
    except Exception:
        return t.lstrip("0") or "0"


def is_2022(row):
    return (
        txt(row.get("year")) == "2022"
        or
        "2022" in txt(row.get("session_id"))
    )


def locator_index(locator):
    m = re.fullmatch(
        r"records\[(\d+)\]",
        txt(locator),
    )

    if not m:
        return None

    return int(
        m.group(1)
    )


def main():

    print()
    print("=" * 120)
    print(
        "R1G.14 — 2022 CHRONOLOGY-ONLY "
        "CANONICAL LINK RESOLUTION V1"
    )
    print("=" * 120)

    inputs = [
        CANONICAL,
        MATCH_V1,
        UNRESOLVED_V1,
        EVIDENCE_V5,
    ]

    missing = []

    for path in inputs:

        exists = path.exists()

        print(
            f"{path}: "
            f"{'PRESENT' if exists else 'MISSING'}"
        )

        if not exists:
            missing.append(path)

    if missing:

        print()
        print(
            "FINAL STATUS: "
            "2022_CHRONOLOGY_ONLY_LINK_RESOLUTION_INPUT_MISSING"
        )

        return

    canonical = read_csv(
        CANONICAL
    )

    match_v1 = read_csv(
        MATCH_V1
    )

    unresolved = read_csv(
        UNRESOLVED_V1
    )

    evidence = read_csv(
        EVIDENCE_V5
    )

    canonical_2022 = [
        row
        for row in canonical
        if is_2022(row)
    ]

    print()
    print(
        "CANONICAL 2022 ROWS:",
        len(canonical_2022),
    )

    print(
        "EXISTING UNIQUE MATCHES:",
        len(match_v1),
    )

    print(
        "UNRESOLVED ROWS:",
        len(unresolved),
    )

    # ========================================================
    # BUILD LOCATOR LOOKUP
    # ========================================================

    locator_lookup = {}

    for row in canonical_2022:

        locator = txt(
            row.get(
                "source_native_locator"
            )
        )

        if not locator:
            continue

        locator_lookup.setdefault(
            locator,
            []
        ).append(
            row
        )

    # ========================================================
    # RESOLVE UNRESOLVED ROWS
    # ========================================================

    resolutions = []

    still_unresolved = []

    for u in unresolved:

        result_row = txt(
            u.get(
                "official_result_row"
            )
        )

        car = norm_car(
            u.get(
                "car_number"
            )
        )

        expected_locator = (
            f"records[{result_row}]"
        )

        candidates = locator_lookup.get(
            expected_locator,
            []
        )

        candidates = [
            row
            for row in candidates
            if norm_car(
                row.get(
                    "car_number"
                )
            ) == car
        ]

        if len(candidates) == 1:

            can = candidates[0]

            attempt_class = txt(
                can.get(
                    "attempt_class"
                )
            )

            # Require chronology-only object for this rescue rule.
            if attempt_class == "D_CHRONOLOGY_ONLY":

                resolutions.append({
                    "year":
                        "2022",

                    "official_result_row":
                        result_row,

                    "car_number":
                        car,

                    "driver_name":
                        txt(
                            u.get(
                                "driver_name"
                            )
                        ),

                    "official_speed_mph":
                        txt(
                            u.get(
                                "official_speed_mph"
                            )
                        ),

                    "official_status":
                        txt(
                            u.get(
                                "official_status"
                            )
                        ),

                    "attempt_id":
                        txt(
                            can.get(
                                "attempt_id"
                            )
                        ),

                    "attempt_key":
                        txt(
                            can.get(
                                "attempt_key"
                            )
                        ),

                    "car_attempt_index":
                        txt(
                            can.get(
                                "car_attempt_index"
                            )
                        ),

                    "canonical_speed_mph":
                        txt(
                            can.get(
                                "four_lap_average_speed_mph"
                            )
                        ),

                    "canonical_result_status":
                        txt(
                            can.get(
                                "result_status"
                            )
                        ),

                    "attempt_class":
                        attempt_class,

                    "source_native_locator":
                        txt(
                            can.get(
                                "source_native_locator"
                            )
                        ),

                    "match_method":
                        "SOURCE_NATIVE_LOCATOR_IDENTITY",

                    "match_status":
                        "UNIQUE_MATCH",

                    "chronology_order_inferred":
                        "False",

                    "canonical_promoted":
                        "False",

                    "notes":
                        (
                            "Identity reconciliation via exact "
                            "source_native_locator records[N] "
                            "correspondence. Result-row ordering "
                            "was NOT interpreted as chronology."
                        ),
                })

                continue

        still_unresolved.append(
            u
        )

    # ========================================================
    # PRINT RESOLUTIONS
    # ========================================================

    print()
    print("=" * 120)
    print(
        "CHRONOLOGY-ONLY LINK RESOLUTIONS"
    )
    print("=" * 120)

    for r in resolutions:

        print()
        print(
            "official row:",
            r[
                "official_result_row"
            ],
        )

        print(
            "car:",
            r[
                "car_number"
            ],
        )

        print(
            "driver:",
            r[
                "driver_name"
            ],
        )

        print(
            "status:",
            repr(
                r[
                    "official_status"
                ]
            ),
        )

        print(
            "attempt_id:",
            r[
                "attempt_id"
            ],
        )

        print(
            "attempt_class:",
            r[
                "attempt_class"
            ],
        )

        print(
            "locator:",
            r[
                "source_native_locator"
            ],
        )

    print()
    print(
        "Resolved:",
        len(resolutions),
    )

    print(
        "Still unresolved:",
        len(still_unresolved),
    )

    # ========================================================
    # BUILD MATCH V2
    # ========================================================

    match_fields = list(
        match_v1[0].keys()
    )

    match_v2 = [
        dict(row)
        for row in match_v1
    ]

    for r in resolutions:

        row = {
            field: ""
            for field in match_fields
        }

        row.update({
            "year":
                "2022",

            "official_result_row":
                r[
                    "official_result_row"
                ],

            "car_number":
                r[
                    "car_number"
                ],

            "driver_name":
                r[
                    "driver_name"
                ],

            "official_speed_mph":
                r[
                    "official_speed_mph"
                ],

            "official_status":
                r[
                    "official_status"
                ],

            "attempt_id":
                r[
                    "attempt_id"
                ],

            "attempt_key":
                r[
                    "attempt_key"
                ],

            "car_attempt_index":
                r[
                    "car_attempt_index"
                ],

            "canonical_speed_mph":
                r[
                    "canonical_speed_mph"
                ],

            "canonical_result_status":
                r[
                    "canonical_result_status"
                ],

            "match_score":
                "",

            "match_reasons":
                (
                    '["SOURCE_NATIVE_LOCATOR_IDENTITY",'
                    '"D_CHRONOLOGY_ONLY"]'
                ),

            "match_status":
                "UNIQUE_MATCH",

            "canonical_promoted":
                "False",
        })

        match_v2.append(
            row
        )

    # ========================================================
    # DUPLICATE CHECK
    # ========================================================

    by_result_row = {}

    by_attempt_id = {}

    for row in match_v2:

        rr = txt(
            row.get(
                "official_result_row"
            )
        )

        aid = txt(
            row.get(
                "attempt_id"
            )
        )

        if rr:

            by_result_row[
                rr
            ] = (
                by_result_row.get(
                    rr,
                    0,
                )
                + 1
            )

        if aid:

            by_attempt_id[
                aid
            ] = (
                by_attempt_id.get(
                    aid,
                    0,
                )
                + 1
            )

    duplicate_result_rows = [
        k
        for k, v in by_result_row.items()
        if v > 1
    ]

    duplicate_attempt_ids = [
        k
        for k, v in by_attempt_id.items()
        if v > 1
    ]

    # ========================================================
    # UPDATE EVIDENCE LINK
    # ========================================================

    result_to_attempt = {
        txt(
            row.get(
                "official_result_row"
            )
        ):
        txt(
            row.get(
                "attempt_id"
            )
        )
        for row in match_v2
        if txt(
            row.get(
                "official_result_row"
            )
        )
    }

    evidence_v2 = []

    for original in evidence:

        row = dict(
            original
        )

        result_row = txt(
            row.get(
                "official_result_row"
            )
        )

        old_attempt_id = txt(
            row.get(
                "attempt_id"
            )
        )

        if (
            result_row
            and
            not old_attempt_id
            and
            result_row in result_to_attempt
        ):

            row[
                "attempt_id"
            ] = result_to_attempt[
                result_row
            ]

            row[
                "attempt_link_status"
            ] = (
                "LINKED_BY_SOURCE_NATIVE_LOCATOR_IDENTITY"
            )

        evidence_v2.append(
            row
        )

    # ========================================================
    # NEWGARDEN CHECK
    # ========================================================

    newgarden_no_attempt = [
        r
        for r in resolutions
        if (
            r[
                "car_number"
            ] == "2"
            and
            r[
                "official_status"
            ] == "No Attempt"
        )
    ]

    print()
    print("=" * 120)
    print(
        "NEWGARDEN NO ATTEMPT RESOLUTION"
    )
    print("=" * 120)

    print(
        "matches:",
        len(
            newgarden_no_attempt
        ),
    )

    for r in newgarden_no_attempt:

        print(
            "attempt_id:",
            r[
                "attempt_id"
            ],
        )

        print(
            "locator:",
            r[
                "source_native_locator"
            ],
        )

        print(
            "class:",
            r[
                "attempt_class"
            ],
        )

    # ========================================================
    # WRITE OUTPUTS
    # ========================================================

    resolution_fields = [
        "year",
        "official_result_row",
        "car_number",
        "driver_name",
        "official_speed_mph",
        "official_status",
        "attempt_id",
        "attempt_key",
        "car_attempt_index",
        "canonical_speed_mph",
        "canonical_result_status",
        "attempt_class",
        "source_native_locator",
        "match_method",
        "match_status",
        "chronology_order_inferred",
        "canonical_promoted",
        "notes",
    ]

    write_csv(
        RESOLUTION_OUT,
        resolutions,
        resolution_fields,
    )

    match_v2.sort(
        key=lambda r: int(
            txt(
                r.get(
                    "official_result_row"
                )
            )
            or 9999
        )
    )

    write_csv(
        MATCH_V2,
        match_v2,
        match_fields,
    )

    evidence_fields = list(
        evidence_v2[0].keys()
    )

    write_csv(
        EVIDENCE_V2,
        evidence_v2,
        evidence_fields,
    )

    # ========================================================
    # QA
    # ========================================================

    attempt_level_evidence = [
        r
        for r in evidence_v2
        if txt(
            r.get(
                "car_number"
            )
        )
    ]

    linked_attempt_level = [
        r
        for r in attempt_level_evidence
        if txt(
            r.get(
                "attempt_id"
            )
        )
    ]

    qa = [
        {
            "metric":
                "previous_unique_matches",
            "value":
                len(match_v1),
            "status":
                "INFO",
        },

        {
            "metric":
                "chronology_only_resolutions",
            "value":
                len(resolutions),
            "status":
                (
                    "PASS"
                    if len(resolutions) == 4
                    else "REVIEW"
                ),
        },

        {
            "metric":
                "final_result_to_attempt_matches",
            "value":
                len(match_v2),
            "status":
                (
                    "PASS"
                    if len(match_v2) == 44
                    else "REVIEW"
                ),
        },

        {
            "metric":
                "still_unresolved",
            "value":
                len(still_unresolved),
            "status":
                (
                    "PASS"
                    if len(still_unresolved) == 0
                    else "REVIEW"
                ),
        },

        {
            "metric":
                "newgarden_no_attempt_linked",
            "value":
                len(newgarden_no_attempt),
            "status":
                (
                    "PASS"
                    if len(newgarden_no_attempt) == 1
                    else "REVIEW"
                ),
        },

        {
            "metric":
                "attempt_level_evidence_rows",
            "value":
                len(attempt_level_evidence),
            "status":
                "INFO",
        },

        {
            "metric":
                "attempt_level_evidence_linked",
            "value":
                len(linked_attempt_level),
            "status":
                (
                    "PASS"
                    if (
                        len(linked_attempt_level)
                        ==
                        len(attempt_level_evidence)
                    )
                    else "REVIEW"
                ),
        },

        {
            "metric":
                "duplicate_result_rows",
            "value":
                len(duplicate_result_rows),
            "status":
                (
                    "PASS"
                    if not duplicate_result_rows
                    else "FAIL"
                ),
        },

        {
            "metric":
                "duplicate_attempt_ids",
            "value":
                len(duplicate_attempt_ids),
            "status":
                (
                    "PASS"
                    if not duplicate_attempt_ids
                    else "FAIL"
                ),
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
        QA_OUT,
        qa,
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
        "FINAL LINK SUMMARY"
    )
    print("=" * 120)

    print()
    print(
        "Previous result links:",
        len(match_v1),
    )

    print(
        "New chronology-only links:",
        len(resolutions),
    )

    print(
        "Final result links:",
        len(match_v2),
    )

    print(
        "Still unresolved:",
        len(still_unresolved),
    )

    print(
        "Attempt-level evidence rows:",
        len(attempt_level_evidence),
    )

    print(
        "Attempt-level evidence linked:",
        len(linked_attempt_level),
    )

    print(
        "Duplicate result rows:",
        len(duplicate_result_rows),
    )

    print(
        "Duplicate attempt IDs:",
        len(duplicate_attempt_ids),
    )

    print()
    print(
        "Result-row number was used only as "
        "source-native identity locator."
    )

    print(
        "Result-row ordering was NOT used as chronology."
    )

    print(
        "No canonical data was modified."
    )

    print(
        "No queue wait was inferred."
    )

    print()
    print("=" * 120)

    if (
        len(resolutions) == 4
        and
        len(match_v2) == 44
        and
        len(still_unresolved) == 0
        and
        not duplicate_result_rows
        and
        not duplicate_attempt_ids
        and
        len(newgarden_no_attempt) == 1
    ):

        print(
            "FINAL STATUS: "
            "2022_RESULTS_CANONICAL_RECONCILIATION_44_OF_44"
        )

    else:

        print(
            "FINAL STATUS: "
            "2022_CHRONOLOGY_ONLY_LINK_RESOLUTION_REVIEW_REQUIRED"
        )

    print("=" * 120)

    print()
    print("OUTPUTS")
    print(RESOLUTION_OUT)
    print(MATCH_V2)
    print(EVIDENCE_V2)
    print(QA_OUT)


if __name__ == "__main__":
    main()
