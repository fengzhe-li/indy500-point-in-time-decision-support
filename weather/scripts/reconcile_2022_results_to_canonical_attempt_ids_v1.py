from pathlib import Path
import csv
import json
import math


PHASE = "R1G.12"

CANONICAL_ATTEMPTS = Path(
    "data/canonical/v1/attempts.csv"
)

OFFICIAL_RESULTS = Path(
    "weather/output/"
    "official_day1_results_attempt_rows_v1.csv"
)

CHRONOLOGY_EVIDENCE = Path(
    "weather/output/"
    "chronology_rescue_2022_adjudicated_evidence_v5.csv"
)

OUTPUT_DIR = Path(
    "weather/output"
)

MATCH_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_result_to_canonical_attempt_matches_v1.csv"
)

EVIDENCE_LINK_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_evidence_with_attempt_ids_v1.csv"
)

UNRESOLVED_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_unresolved_attempt_links_v1.csv"
)

QA_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_result_to_canonical_attempt_matches_v1_qa.csv"
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
        w = csv.DictWriter(
            f,
            fieldnames=fields,
        )
        w.writeheader()
        w.writerows(rows)


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


def norm_status(v):
    t = txt(v).upper().replace("-", " ").replace("_", " ")

    while "  " in t:
        t = t.replace("  ", " ")

    return t


def to_float(v):
    t = txt(v)

    if not t:
        return None

    try:
        return float(t)
    except Exception:
        return None


def speed_close(a, b, tol=0.0015):
    fa = to_float(a)
    fb = to_float(b)

    if fa is None or fb is None:
        return False

    return abs(fa - fb) <= tol


def is_2022_session(row):
    sid = txt(row.get("session_id"))

    if "2022" in sid:
        return True

    year = txt(row.get("year"))

    return year == "2022"


def canonical_speed(row):
    for field in [
        "four_lap_average_speed_mph",
        "speed_avg_mph",
        "average_speed_mph",
    ]:
        value = txt(row.get(field))

        if value:
            return value

    return ""


def result_speed(row):
    return txt(
        row.get(
            "speed_avg_mph"
        )
    )


def result_driver(row):
    for field in [
        "driver_name",
        "driver_name_pdf",
    ]:
        value = txt(row.get(field))

        if value:
            return value

    return ""


def canonical_status(row):
    return norm_status(
        row.get(
            "result_status"
        )
    )


def official_status(row):
    return norm_status(
        row.get(
            "status"
        )
    )


def match_score(
    result_row,
    canonical_row,
):
    score = 0
    reasons = []

    r_car = norm_car(
        result_row.get(
            "car_number"
        )
    )

    c_car = norm_car(
        canonical_row.get(
            "car_number"
        )
    )

    if r_car != c_car:
        return -999, ["CAR_MISMATCH"]

    score += 10
    reasons.append("CAR_MATCH")

    r_speed = result_speed(
        result_row
    )

    c_speed = canonical_speed(
        canonical_row
    )

    if r_speed and c_speed:
        if speed_close(
            r_speed,
            c_speed,
        ):
            score += 20
            reasons.append(
                "SPEED_MATCH"
            )
        else:
            score -= 20
            reasons.append(
                "SPEED_MISMATCH"
            )

    elif (
        not r_speed
        and
        not c_speed
    ):
        score += 5
        reasons.append(
            "BOTH_SPEED_EMPTY"
        )

    r_status = official_status(
        result_row
    )

    c_status = canonical_status(
        canonical_row
    )

    if r_status and c_status:
        if r_status == c_status:
            score += 10
            reasons.append(
                "STATUS_MATCH"
            )
        else:
            score -= 3
            reasons.append(
                "STATUS_DIFFER"
            )

    elif not r_status:
        reasons.append(
            "OFFICIAL_STATUS_EMPTY"
        )

    elif not c_status:
        reasons.append(
            "CANONICAL_STATUS_EMPTY"
        )

    return score, reasons


def main():

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print()
    print("=" * 120)
    print(
        "R1G.12 — 2022 RESULTS TO CANONICAL "
        "ATTEMPT-ID RECONCILIATION V1"
    )
    print("=" * 120)

    for path in [
        CANONICAL_ATTEMPTS,
        OFFICIAL_RESULTS,
        CHRONOLOGY_EVIDENCE,
    ]:
        print(
            f"{path}: "
            f"{'PRESENT' if path.exists() else 'MISSING'}"
        )

    if not all(
        path.exists()
        for path in [
            CANONICAL_ATTEMPTS,
            OFFICIAL_RESULTS,
            CHRONOLOGY_EVIDENCE,
        ]
    ):
        print(
            "FINAL STATUS: "
            "2022_CANONICAL_RECONCILIATION_INPUT_MISSING"
        )
        return

    canonical = read_csv(
        CANONICAL_ATTEMPTS
    )

    results = read_csv(
        OFFICIAL_RESULTS
    )

    evidence = read_csv(
        CHRONOLOGY_EVIDENCE
    )

    canonical_2022 = [
        r
        for r in canonical
        if is_2022_session(r)
    ]

    results_2022 = [
        r
        for r in results
        if txt(
            r.get("year")
        ) == "2022"
    ]

    print()
    print(
        "CANONICAL 2022 ATTEMPTS:",
        len(canonical_2022),
    )

    print(
        "OFFICIAL 2022 RESULT ROWS:",
        len(results_2022),
    )

    print(
        "CHRONOLOGY EVIDENCE V5 ROWS:",
        len(evidence),
    )

    # ========================================================
    # RESULT -> CANONICAL MATCH
    # ========================================================

    match_rows = []
    unresolved = []

    for result in results_2022:

        candidates = []

        for can in canonical_2022:

            score, reasons = match_score(
                result,
                can,
            )

            if score <= -900:
                continue

            candidates.append({
                "canonical":
                    can,

                "score":
                    score,

                "reasons":
                    reasons,
            })

        candidates.sort(
            key=lambda x: (
                -x["score"],
                txt(
                    x["canonical"].get(
                        "attempt_id"
                    )
                ),
            )
        )

        best = (
            candidates[0]
            if candidates
            else None
        )

        second = (
            candidates[1]
            if len(candidates) > 1
            else None
        )

        unique_best = False

        if best is not None:

            if (
                best["score"] >= 20
                and
                (
                    second is None
                    or
                    best["score"]
                    >
                    second["score"]
                )
            ):
                unique_best = True

        result_row_num = txt(
            result.get(
                "result_row"
            )
        )

        if unique_best:

            can = best[
                "canonical"
            ]

            match_rows.append({
                "year":
                    2022,

                "official_result_row":
                    result_row_num,

                "car_number":
                    norm_car(
                        result.get(
                            "car_number"
                        )
                    ),

                "driver_name":
                    result_driver(
                        result
                    ),

                "official_speed_mph":
                    result_speed(
                        result
                    ),

                "official_status":
                    txt(
                        result.get(
                            "status"
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
                    canonical_speed(
                        can
                    ),

                "canonical_result_status":
                    txt(
                        can.get(
                            "result_status"
                        )
                    ),

                "match_score":
                    best[
                        "score"
                    ],

                "match_reasons":
                    json.dumps(
                        best[
                            "reasons"
                        ],
                        ensure_ascii=False,
                    ),

                "match_status":
                    "UNIQUE_MATCH",

                "canonical_promoted":
                    False,
            })

        else:

            unresolved.append({
                "year":
                    2022,

                "official_result_row":
                    result_row_num,

                "car_number":
                    norm_car(
                        result.get(
                            "car_number"
                        )
                    ),

                "driver_name":
                    result_driver(
                        result
                    ),

                "official_speed_mph":
                    result_speed(
                        result
                    ),

                "official_status":
                    txt(
                        result.get(
                            "status"
                        )
                    ),

                "best_score":
                    (
                        best[
                            "score"
                        ]
                        if best
                        else ""
                    ),

                "best_attempt_id":
                    (
                        txt(
                            best[
                                "canonical"
                            ].get(
                                "attempt_id"
                            )
                        )
                        if best
                        else ""
                    ),

                "second_score":
                    (
                        second[
                            "score"
                        ]
                        if second
                        else ""
                    ),

                "reason":
                    (
                        "AMBIGUOUS_OR_WEAK_MATCH"
                        if best
                        else "NO_CANDIDATE"
                    ),
            })

    print()
    print("=" * 120)
    print(
        "RESULT MATCH SUMMARY"
    )
    print("=" * 120)

    print(
        "Unique matches:",
        len(match_rows),
    )

    print(
        "Unresolved:",
        len(unresolved),
    )

    # ========================================================
    # LOOKUP FOR EVIDENCE LINKING
    # ========================================================

    result_lookup = {
        txt(
            r.get(
                "official_result_row"
            )
        ):
        r
        for r in match_rows
    }

    evidence_linked = []

    for row in evidence:

        out = dict(
            row
        )

        result_row_num = txt(
            row.get(
                "official_result_row"
            )
        )

        linked_attempt_id = ""
        link_status = ""

        if result_row_num:

            match = result_lookup.get(
                result_row_num
            )

            if match:

                linked_attempt_id = txt(
                    match.get(
                        "attempt_id"
                    )
                )

                link_status = (
                    "LINKED_BY_UNIQUE_RESULT_MATCH"
                )

            else:

                link_status = (
                    "RESULT_ROW_UNRESOLVED"
                )

        else:

            link_status = (
                "SESSION_LEVEL_OR_NO_RESULT_ROW"
            )

        out[
            "attempt_id"
        ] = linked_attempt_id

        out[
            "attempt_link_status"
        ] = link_status

        evidence_linked.append(
            out
        )

    # ========================================================
    # PRINT KEY TARGETS
    # ========================================================

    print()
    print("=" * 120)
    print(
        "KEY 2022 CHRONOLOGY TARGET LINKS"
    )
    print("=" * 120)

    key_targets = [
        ("21", "233.655"),
        ("5", "233.037"),
        ("7", "232.775"),
        ("51", "232.196"),
        ("51", "231.708"),
        ("3", "231.543"),
        ("3", "230.154"),
        ("2", "231.580"),
    ]

    for car, speed in key_targets:

        rows = [
            r
            for r in match_rows
            if (
                r[
                    "car_number"
                ] == car
                and
                (
                    speed == ""
                    or
                    speed_close(
                        r[
                            "official_speed_mph"
                        ],
                        speed,
                    )
                )
            )
        ]

        print()
        print(
            f"CAR {car} SPEED {speed}"
        )

        print(
            "  matches:",
            len(rows),
        )

        for r in rows:

            print(
                "  attempt_id:",
                r[
                    "attempt_id"
                ],
            )

            print(
                "  car_attempt_index:",
                r[
                    "car_attempt_index"
                ],
            )

            print(
                "  official row:",
                r[
                    "official_result_row"
                ],
            )

    newg_no_attempt = [
        r
        for r in match_rows
        if (
            r[
                "car_number"
            ] == "2"
            and
            norm_status(
                r[
                    "official_status"
                ]
            )
            == "NO ATTEMPT"
        )
    ]

    print()
    print(
        "NEWGARDEN NO ATTEMPT LINKS:",
        len(
            newg_no_attempt
        ),
    )

    for r in newg_no_attempt:
        print(
            "  attempt_id:",
            r[
                "attempt_id"
            ],
        )

    # ========================================================
    # WRITE
    # ========================================================

    write_csv(
        MATCH_OUT,
        match_rows,
        [
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
            "match_score",
            "match_reasons",
            "match_status",
            "canonical_promoted",
        ],
    )

    evidence_fields = (
        list(
            evidence[0].keys()
        )
        + [
            "attempt_id",
            "attempt_link_status",
        ]
    )

    write_csv(
        EVIDENCE_LINK_OUT,
        evidence_linked,
        evidence_fields,
    )

    write_csv(
        UNRESOLVED_OUT,
        unresolved,
        [
            "year",
            "official_result_row",
            "car_number",
            "driver_name",
            "official_speed_mph",
            "official_status",
            "best_score",
            "best_attempt_id",
            "second_score",
            "reason",
        ],
    )

    # ========================================================
    # QA
    # ========================================================

    evidence_attempt_rows = [
        r
        for r in evidence_linked
        if txt(
            r.get(
                "car_number"
            )
        )
    ]

    evidence_linked_rows = [
        r
        for r in evidence_attempt_rows
        if txt(
            r.get(
                "attempt_id"
            )
        )
    ]

    duplicate_attempt_links = {}

    for r in match_rows:

        aid = r[
            "attempt_id"
        ]

        duplicate_attempt_links[
            aid
        ] = (
            duplicate_attempt_links.get(
                aid,
                0,
            )
            + 1
        )

    duplicate_attempt_count = sum(
        1
        for count
        in duplicate_attempt_links.values()
        if count > 1
    )

    qa_rows = [
        {
            "metric":
                "canonical_2022_attempts",

            "value":
                len(
                    canonical_2022
                ),

            "status":
                "INFO",
        },

        {
            "metric":
                "official_2022_result_rows",

            "value":
                len(
                    results_2022
                ),

            "status":
                "INFO",
        },

        {
            "metric":
                "unique_result_to_attempt_matches",

            "value":
                len(
                    match_rows
                ),

            "status":
                (
                    "PASS"
                    if len(
                        match_rows
                    ) > 0
                    else "FAIL"
                ),
        },

        {
            "metric":
                "unresolved_result_rows",

            "value":
                len(
                    unresolved
                ),

            "status":
                "INFO",
        },

        {
            "metric":
                "attempt_level_evidence_rows",

            "value":
                len(
                    evidence_attempt_rows
                ),

            "status":
                "INFO",
        },

        {
            "metric":
                "attempt_level_evidence_linked",

            "value":
                len(
                    evidence_linked_rows
                ),

            "status":
                (
                    "PASS"
                    if len(
                        evidence_linked_rows
                    ) > 0
                    else "REVIEW"
                ),
        },

        {
            "metric":
                "canonical_attempt_ids_with_multiple_result_rows",

            "value":
                duplicate_attempt_count,

            "status":
                (
                    "PASS"
                    if duplicate_attempt_count
                    == 0
                    else "REVIEW"
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
        qa_rows,
        [
            "metric",
            "value",
            "status",
        ],
    )

    # ========================================================
    # FINAL
    # ========================================================

    print()
    print("=" * 120)
    print(
        "EVIDENCE LINK SUMMARY"
    )
    print("=" * 120)

    print()
    print(
        "Attempt-level evidence rows:",
        len(
            evidence_attempt_rows
        ),
    )

    print(
        "Attempt-level evidence linked:",
        len(
            evidence_linked_rows
        ),
    )

    print(
        "Duplicate canonical attempt links:",
        duplicate_attempt_count,
    )

    print()
    print(
        "No result-row ordering was used "
        "as chronology."
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
        len(
            match_rows
        ) > 0
        and
        len(
            evidence_linked_rows
        ) > 0
    ):

        print(
            "FINAL STATUS: "
            "2022_RESULTS_CANONICAL_ATTEMPT_RECONCILIATION_COMPLETE"
        )

    else:

        print(
            "FINAL STATUS: "
            "2022_RESULTS_CANONICAL_ATTEMPT_RECONCILIATION_REVIEW_REQUIRED"
        )

    print("=" * 120)

    print()
    print("OUTPUTS")
    print(MATCH_OUT)
    print(EVIDENCE_LINK_OUT)
    print(UNRESOLVED_OUT)
    print(QA_OUT)


if __name__ == "__main__":
    main()
