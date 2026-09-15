from pathlib import Path
import csv


CANONICAL = Path(
    "data/canonical/v1/attempts.csv"
)

RESULT_MATCHES = Path(
    "weather/output/"
    "chronology_rescue_2022_result_to_canonical_attempt_matches_v2.csv"
)

EVIDENCE = Path(
    "weather/output/"
    "chronology_rescue_2022_castroneves_repeat_pair_evidence_v1.csv"
)

OUTPUT_DIR = Path(
    "weather/output"
)

AUDIT_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_castroneves_car06_reaudit_v1.csv"
)

QA_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_castroneves_car06_reaudit_v1_qa.csv"
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


def preserve_car(v):
    """
    Preserve source-significant car number formatting.

    Important:
      '06' != '6'

    Do NOT convert through int/float.
    """
    return txt(v)


def speed_close(a, b, tol=0.003):
    try:
        return abs(
            float(txt(a))
            -
            float(txt(b))
        ) <= tol
    except Exception:
        return False


def is_2022(row):
    return (
        txt(row.get("year")) == "2022"
        or
        "2022" in txt(
            row.get("session_id")
        )
    )


def canonical_speed(row):
    for field in [
        "four_lap_average_speed_mph",
        "average_speed_mph",
        "speed_mph",
    ]:
        value = txt(
            row.get(field)
        )

        if value:
            return value

    return ""


def main():

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print()
    print("=" * 120)
    print(
        "R1G.25B — 2022 CASTRONEVES "
        "CAR-NUMBER-PRESERVING RE-AUDIT V1"
    )
    print("=" * 120)

    inputs = [
        CANONICAL,
        RESULT_MATCHES,
        EVIDENCE,
    ]

    missing = []

    print()
    print("INPUT CHECK")
    print("-" * 120)

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
            "CASTRONEVES_CAR06_REAUDIT_INPUT_MISSING"
        )

        return

    canonical = read_csv(
        CANONICAL
    )

    results = read_csv(
        RESULT_MATCHES
    )

    evidence = read_csv(
        EVIDENCE
    )

    # ========================================================
    # PRESERVE #06 VS #6
    # ========================================================

    castroneves_canonical = [
        row
        for row in canonical
        if (
            is_2022(row)
            and
            preserve_car(
                row.get(
                    "car_number"
                )
            ) == "06"
        )
    ]

    montoya_canonical = [
        row
        for row in canonical
        if (
            is_2022(row)
            and
            preserve_car(
                row.get(
                    "car_number"
                )
            ) == "6"
        )
    ]

    castroneves_results = [
        row
        for row in results
        if preserve_car(
            row.get(
                "car_number"
            )
        ) == "06"
    ]

    montoya_results = [
        row
        for row in results
        if preserve_car(
            row.get(
                "car_number"
            )
        ) == "6"
    ]

    print()
    print("=" * 120)
    print(
        "CAR NUMBER SEPARATION CHECK"
    )
    print("=" * 120)

    print()
    print(
        "#06 Castroneves canonical rows:",
        len(
            castroneves_canonical
        ),
    )

    print(
        "#6 Montoya canonical rows:",
        len(
            montoya_canonical
        ),
    )

    print(
        "#06 Castroneves result rows:",
        len(
            castroneves_results
        ),
    )

    print(
        "#6 Montoya result rows:",
        len(
            montoya_results
        ),
    )

    # ========================================================
    # PRINT CASTRONEVES ONLY
    # ========================================================

    print()
    print("=" * 120)
    print(
        "TRUE #06 CASTRONEVES OBJECTS"
    )
    print("=" * 120)

    audit_rows = []

    result_by_id = {
        txt(
            row.get(
                "attempt_id"
            )
        ): row
        for row in castroneves_results
        if txt(
            row.get(
                "attempt_id"
            )
        )
    }

    for row in castroneves_canonical:

        aid = txt(
            row.get(
                "attempt_id"
            )
        )

        linked = result_by_id.get(
            aid,
            {},
        )

        print()
        print(
            "attempt_id:",
            aid,
        )

        print(
            "  car_number:",
            repr(
                txt(
                    row.get(
                        "car_number"
                    )
                )
            ),
        )

        print(
            "  attempt index:",
            repr(
                txt(
                    row.get(
                        "car_attempt_index"
                    )
                )
            ),
        )

        print(
            "  canonical speed:",
            repr(
                canonical_speed(
                    row
                )
            ),
        )

        print(
            "  attempt class:",
            repr(
                txt(
                    row.get(
                        "attempt_class"
                    )
                )
            ),
        )

        print(
            "  official speed:",
            repr(
                txt(
                    linked.get(
                        "official_speed_mph"
                    )
                )
            ),
        )

        print(
            "  official status:",
            repr(
                txt(
                    linked.get(
                        "official_status"
                    )
                )
            ),
        )

        audit_rows.append({
            "attempt_id":
                aid,

            "car_number":
                txt(
                    row.get(
                        "car_number"
                    )
                ),

            "car_attempt_index":
                txt(
                    row.get(
                        "car_attempt_index"
                    )
                ),

            "canonical_speed_mph":
                canonical_speed(
                    row
                ),

            "attempt_class":
                txt(
                    row.get(
                        "attempt_class"
                    )
                ),

            "official_speed_mph":
                txt(
                    linked.get(
                        "official_speed_mph"
                    )
                ),

            "official_status":
                txt(
                    linked.get(
                        "official_status"
                    )
                ),
        })

    # ========================================================
    # MONToya CONTAMINATION DIAGNOSTIC
    # ========================================================

    print()
    print("=" * 120)
    print(
        "#6 MONTOYA CONTAMINATION CHECK"
    )
    print("=" * 120)

    for row in montoya_canonical:

        print()
        print(
            "Montoya candidate object:"
        )

        print(
            "  attempt_id:",
            txt(
                row.get(
                    "attempt_id"
                )
            ),
        )

        print(
            "  speed:",
            repr(
                canonical_speed(
                    row
                )
            ),
        )

        print(
            "  car_number:",
            repr(
                txt(
                    row.get(
                        "car_number"
                    )
                )
            ),
        )

    # ========================================================
    # EXPECTED CASTRONEVES TARGETS
    # ========================================================

    c225 = [
        row
        for row in castroneves_results
        if speed_close(
            row.get(
                "official_speed_mph"
            ),
            "225.482",
        )
    ]

    c229 = [
        row
        for row in castroneves_results
        if speed_close(
            row.get(
                "official_speed_mph"
            ),
            "229.630",
        )
    ]

    c228 = [
        row
        for row in castroneves_results
        if speed_close(
            row.get(
                "official_speed_mph"
            ),
            "228.622",
        )
    ]

    m228 = [
        row
        for row in montoya_results
        if speed_close(
            row.get(
                "official_speed_mph"
            ),
            "228.622",
        )
    ]

    print()
    print("=" * 120)
    print(
        "SPEED OWNERSHIP CHECK"
    )
    print("=" * 120)

    print()
    print(
        "#06 / 225.482:",
        len(c225),
    )

    print(
        "#06 / 229.630:",
        len(c229),
    )

    print(
        "#06 / 228.622:",
        len(c228),
    )

    print(
        "#6 / 228.622:",
        len(m228),
    )

    # ========================================================
    # DIRECT FIRST-RUN NARRATIVE
    # ========================================================

    first_run_evidence = []

    for row in evidence:

        sentence = txt(
            row.get(
                "sentence"
            )
        ).lower()

        if (
            "castroneves"
            in sentence
            and
            "first run"
            in sentence
            and
            (
                "bailing out"
                in sentence
                or
                "bailed out"
                in sentence
            )
        ):

            first_run_evidence.append(
                row
            )

    print()
    print("=" * 120)
    print(
        "FIRST-RUN ACTION EVIDENCE"
    )
    print("=" * 120)

    print()
    print(
        "Direct first-run evidence rows:",
        len(
            first_run_evidence
        ),
    )

    for row in first_run_evidence:

        print()
        print(
            txt(
                row.get(
                    "sentence"
                )
            )
        )

    # ========================================================
    # READINESS
    # ========================================================

    expected_structure = (
        len(
            castroneves_canonical
        ) == 2
        and
        len(c225) == 1
        and
        len(c229) == 1
        and
        len(c228) == 0
        and
        len(m228) == 1
    )

    # We still remain conservative:
    #
    # first-run narrative identifies "first run".
    # If canonical #06 now contains exactly two objects and
    # the 225.482 object is uniquely identified as the
    # Withdrawn result, the next adjudication can evaluate
    # the first-run action without Montoya contamination.
    #
    adjudication_ready = (
        expected_structure
        and
        len(
            first_run_evidence
        ) >= 1
    )

    print()
    print("=" * 120)
    print(
        "CORRECTED ADJUDICATION READINESS"
    )
    print("=" * 120)

    print()
    print(
        "True #06 structure correct:",
        expected_structure,
    )

    print(
        "Montoya contamination removed:",
        (
            len(c228) == 0
            and
            len(m228) == 1
        ),
    )

    print(
        "Direct first-run narrative present:",
        len(
            first_run_evidence
        ) >= 1,
    )

    print(
        "Adjudication ready:",
        adjudication_ready,
    )

    # ========================================================
    # WRITE
    # ========================================================

    write_csv(
        AUDIT_OUT,
        audit_rows,
        [
            "attempt_id",
            "car_number",
            "car_attempt_index",
            "canonical_speed_mph",
            "attempt_class",
            "official_speed_mph",
            "official_status",
        ],
    )

    qa_rows = [
        {
            "metric":
                "castroneves_car06_canonical_rows",

            "value":
                len(
                    castroneves_canonical
                ),

            "status":
                (
                    "PASS"
                    if len(
                        castroneves_canonical
                    ) == 2
                    else "REVIEW"
                ),
        },

        {
            "metric":
                "montoya_car6_canonical_rows",

            "value":
                len(
                    montoya_canonical
                ),

            "status":
                "INFO",
        },

        {
            "metric":
                "castroneves_228622_rows",

            "value":
                len(c228),

            "status":
                (
                    "PASS"
                    if len(c228) == 0
                    else "FAIL"
                ),
        },

        {
            "metric":
                "montoya_228622_rows",

            "value":
                len(m228),

            "status":
                (
                    "PASS"
                    if len(m228) == 1
                    else "FAIL"
                ),
        },

        {
            "metric":
                "castroneves_225482_unique",

            "value":
                len(c225),

            "status":
                (
                    "PASS"
                    if len(c225) == 1
                    else "FAIL"
                ),
        },

        {
            "metric":
                "castroneves_229630_unique",

            "value":
                len(c229),

            "status":
                (
                    "PASS"
                    if len(c229) == 1
                    else "FAIL"
                ),
        },

        {
            "metric":
                "direct_first_run_narrative",

            "value":
                len(
                    first_run_evidence
                ),

            "status":
                (
                    "PASS"
                    if len(
                        first_run_evidence
                    ) >= 1
                    else "FAIL"
                ),
        },

        {
            "metric":
                "automatic_action_promotions",

            "value":
                0,

            "status":
                "PASS",
        },

        {
            "metric":
                "car_number_integer_normalization_used",

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

    print()
    print("=" * 120)
    print(
        "FINAL SUMMARY"
    )
    print("=" * 120)

    print()
    print(
        "#06 Castroneves canonical rows:",
        len(
            castroneves_canonical
        ),
    )

    print(
        "#6 Montoya canonical rows:",
        len(
            montoya_canonical
        ),
    )

    print()
    print(
        "225.482 belongs to #06:",
        len(c225) == 1,
    )

    print(
        "229.630 belongs to #06:",
        len(c229) == 1,
    )

    print(
        "228.622 belongs to #6, not #06:",
        (
            len(c228) == 0
            and
            len(m228) == 1
        ),
    )

    print()
    print(
        "No action was promoted."
    )

    print(
        "No integer car-number normalization was used."
    )

    print(
        "No result-row ordering was used."
    )

    print(
        "No canonical data was modified."
    )

    print()
    print("=" * 120)

    if adjudication_ready:

        print(
            "FINAL STATUS: "
            "CASTRONEVES_CAR06_IDENTITY_CLEAN_ADJUDICATION_READY"
        )

    else:

        print(
            "FINAL STATUS: "
            "CASTRONEVES_CAR06_IDENTITY_REVIEW_REQUIRED"
        )

    print("=" * 120)

    print()
    print("OUTPUTS")
    print(AUDIT_OUT)
    print(QA_OUT)


if __name__ == "__main__":
    main()
