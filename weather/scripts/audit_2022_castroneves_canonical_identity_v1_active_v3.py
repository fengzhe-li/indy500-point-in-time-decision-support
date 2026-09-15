from pathlib import Path
import csv
from collections import Counter


# ============================================================
# PHASE
# ============================================================

PHASE = "R1G.25A"


# ============================================================
# INPUTS
# ============================================================

CANONICAL = Path(
    "data/canonical/v1/attempts.csv"
)

RESULT_MATCHES = Path(
    "weather/output/"
    "chronology_rescue_2022_result_to_canonical_attempt_matches_v3.csv"
)

EVIDENCE = Path(
    "weather/output/"
    "chronology_rescue_2022_castroneves_repeat_pair_evidence_v1.csv"
)


# ============================================================
# OUTPUTS
# ============================================================

OUTPUT_DIR = Path(
    "weather/output"
)

AUDIT_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_castroneves_canonical_identity_audit_v1.csv"
)

QA_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_castroneves_canonical_identity_audit_v1_qa.csv"
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
    value = txt(v)

    if not value:
        return ""

    try:
        return str(
            int(
                float(value)
            )
        )
    except Exception:
        return value.lstrip("0") or "0"


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
        txt(
            row.get("year")
        ) == "2022"
        or
        "2022" in txt(
            row.get("session_id")
        )
    )


def first_existing(row, names):
    for name in names:
        value = txt(
            row.get(name)
        )

        if value:
            return value

    return ""


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
        "R1G.25A — 2022 HELIO CASTRONEVES "
        "CANONICAL IDENTITY DISAMBIGUATION V1"
    )
    print("=" * 120)

    required = [
        CANONICAL,
        RESULT_MATCHES,
        EVIDENCE,
    ]

    missing = []

    print()
    print("INPUT CHECK")
    print("-" * 120)

    for path in required:

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
            "CASTRONEVES_CANONICAL_IDENTITY_INPUT_MISSING"
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
    # ALL CASTRONEVES CANONICAL OBJECTS
    # ========================================================

    castroneves_canonical = [
        row
        for row in canonical
        if (
            is_2022(row)
            and
            norm_car(
                row.get(
                    "car_number"
                )
            ) == "6"
        )
    ]

    castroneves_results = [
        row
        for row in results
        if norm_car(
            row.get(
                "car_number"
            )
        ) == "6"
    ]

    result_by_attempt = {
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

    print()
    print("=" * 120)
    print(
        "ALL CASTRONEVES CANONICAL OBJECTS"
    )
    print("=" * 120)

    print()
    print(
        "Canonical objects:",
        len(
            castroneves_canonical
        ),
    )

    audit_rows = []

    for i, row in enumerate(
        castroneves_canonical,
        start=1,
    ):

        attempt_id = txt(
            row.get(
                "attempt_id"
            )
        )

        linked_result = result_by_attempt.get(
            attempt_id,
            {},
        )

        canonical_speed = first_existing(
            row,
            [
                "four_lap_average_speed_mph",
                "average_speed_mph",
                "speed_mph",
            ],
        )

        official_speed = txt(
            linked_result.get(
                "official_speed_mph"
            )
        )

        official_status = txt(
            linked_result.get(
                "official_status"
            )
        )

        print()
        print(
            f"OBJECT {i}"
        )

        print(
            "  attempt_id:",
            attempt_id,
        )

        print(
            "  car_attempt_index:",
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
                canonical_speed
            ),
        )

        print(
            "  attempt_class:",
            repr(
                txt(
                    row.get(
                        "attempt_class"
                    )
                )
            ),
        )

        print(
            "  result_status:",
            repr(
                txt(
                    row.get(
                        "result_status"
                    )
                )
            ),
        )

        print(
            "  source locator:",
            repr(
                first_existing(
                    row,
                    [
                        "source_native_locator",
                        "source_locator",
                        "locator",
                    ],
                )
            ),
        )

        print(
            "  linked official result:",
            "YES"
            if linked_result
            else "NO",
        )

        print(
            "  official result row:",
            repr(
                txt(
                    linked_result.get(
                        "official_result_row"
                    )
                )
            ),
        )

        print(
            "  official speed:",
            repr(
                official_speed
            ),
        )

        print(
            "  official status:",
            repr(
                official_status
            ),
        )

        audit_rows.append({
            "attempt_id":
                attempt_id,

            "car_attempt_index":
                txt(
                    row.get(
                        "car_attempt_index"
                    )
                ),

            "canonical_speed_mph":
                canonical_speed,

            "attempt_class":
                txt(
                    row.get(
                        "attempt_class"
                    )
                ),

            "result_status":
                txt(
                    row.get(
                        "result_status"
                    )
                ),

            "source_native_locator":
                first_existing(
                    row,
                    [
                        "source_native_locator",
                        "source_locator",
                        "locator",
                    ],
                ),

            "has_official_result_link":
                bool(
                    linked_result
                ),

            "official_result_row":
                txt(
                    linked_result.get(
                        "official_result_row"
                    )
                ),

            "official_speed_mph":
                official_speed,

            "official_status":
                official_status,
        })

    # ========================================================
    # EXACT RESULT-LINKED SPEED TARGETS
    # ========================================================

    first_speed_matches = [
        row
        for row in castroneves_results
        if speed_close(
            row.get(
                "official_speed_mph"
            ),
            "225.482",
        )
    ]

    second_speed_matches = [
        row
        for row in castroneves_results
        if speed_close(
            row.get(
                "official_speed_mph"
            ),
            "229.630",
        )
    ]

    print()
    print("=" * 120)
    print(
        "OFFICIAL SPEED-LINK IDENTITY CHECK"
    )
    print("=" * 120)

    print()
    print(
        "225.482 result-linked objects:",
        len(
            first_speed_matches
        ),
    )

    for row in first_speed_matches:

        print(
            "  attempt_id:",
            txt(
                row.get(
                    "attempt_id"
                )
            ),
        )

        print(
            "  status:",
            repr(
                txt(
                    row.get(
                        "official_status"
                    )
                )
            ),
        )

    print()
    print(
        "229.630 result-linked objects:",
        len(
            second_speed_matches
        ),
    )

    for row in second_speed_matches:

        print(
            "  attempt_id:",
            txt(
                row.get(
                    "attempt_id"
                )
            ),
        )

        print(
            "  status:",
            repr(
                txt(
                    row.get(
                        "official_status"
                    )
                )
            ),
        )

    first_id = (
        txt(
            first_speed_matches[0].get(
                "attempt_id"
            )
        )
        if len(
            first_speed_matches
        ) == 1
        else ""
    )

    second_id = (
        txt(
            second_speed_matches[0].get(
                "attempt_id"
            )
        )
        if len(
            second_speed_matches
        ) == 1
        else ""
    )

    # ========================================================
    # WHY ARE THERE TWO INDEX=1 OBJECTS?
    # ========================================================

    index1_rows = [
        row
        for row in castroneves_canonical
        if txt(
            row.get(
                "car_attempt_index"
            )
        ) == "1"
    ]

    print()
    print("=" * 120)
    print(
        "DUPLICATE INDEX=1 DIAGNOSTIC"
    )
    print("=" * 120)

    print()
    print(
        "index=1 canonical objects:",
        len(
            index1_rows
        ),
    )

    class_counts = Counter(
        txt(
            row.get(
                "attempt_class"
            )
        )
        or
        "UNKNOWN"
        for row in index1_rows
    )

    print(
        "index=1 classes:",
        dict(
            class_counts
        ),
    )

    for row in index1_rows:

        aid = txt(
            row.get(
                "attempt_id"
            )
        )

        linked = result_by_attempt.get(
            aid,
            {},
        )

        print()
        print(
            "attempt_id:",
            aid,
        )

        print(
            "  class:",
            repr(
                txt(
                    row.get(
                        "attempt_class"
                    )
                )
            ),
        )

        print(
            "  canonical speed:",
            repr(
                first_existing(
                    row,
                    [
                        "four_lap_average_speed_mph",
                        "average_speed_mph",
                        "speed_mph",
                    ],
                )
            ),
        )

        print(
            "  official link:",
            "YES"
            if linked
            else "NO",
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

        print(
            "  locator:",
            repr(
                first_existing(
                    row,
                    [
                        "source_native_locator",
                        "source_locator",
                        "locator",
                    ],
                )
            ),
        )

    # ========================================================
    # EVIDENCE CHECK
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
        "FIRST-RUN NARRATIVE EVIDENCE"
    )
    print("=" * 120)

    print()
    print(
        "Direct first-run bail-out evidence rows:",
        len(
            first_run_evidence
        ),
    )

    for row in first_run_evidence:

        print()
        print(
            "source:",
            txt(
                row.get(
                    "source_name"
                )
            ),
        )

        print(
            txt(
                row.get(
                    "sentence"
                )
            )
        )

    # ========================================================
    # ADJUDICATION READINESS
    #
    # Critical distinction:
    #
    # We DO NOT require car_attempt_index=1 to be globally
    # unique anymore.
    #
    # We require:
    #   1) one unique official-linked 225.482 object;
    #   2) one unique official-linked 229.630 object;
    #   3) direct narrative explicitly says "first run";
    #   4) exact linked objects are distinct.
    #
    # This still does NOT use official result-row position as
    # chronology.
    #
    # ========================================================

    unique_speed_identity = (
        len(
            first_speed_matches
        ) == 1
        and
        len(
            second_speed_matches
        ) == 1
        and
        first_id
        and
        second_id
        and
        first_id != second_id
    )

    narrative_first_run = (
        len(
            first_run_evidence
        ) >= 1
    )

    # The presence of a duplicate canonical index=1 object
    # remains documented. We do not silently delete, merge,
    # or relabel it.
    duplicate_index1_documented = (
        len(
            index1_rows
        ) >= 2
    )

    print()
    print("=" * 120)
    print(
        "IDENTITY ADJUDICATION READINESS"
    )
    print("=" * 120)

    print()
    print(
        "Unique official-linked 225.482 identity:",
        (
            "YES"
            if len(
                first_speed_matches
            ) == 1
            else "NO"
        ),
    )

    print(
        "Unique official-linked 229.630 identity:",
        (
            "YES"
            if len(
                second_speed_matches
            ) == 1
            else "NO"
        ),
    )

    print(
        "Distinct attempt IDs:",
        (
            "YES"
            if (
                first_id
                and
                second_id
                and
                first_id != second_id
            )
            else "NO"
        ),
    )

    print(
        "Direct 'first run' narrative:",
        (
            "YES"
            if narrative_first_run
            else "NO"
        ),
    )

    print(
        "Duplicate canonical index=1 documented:",
        (
            "YES"
            if duplicate_index1_documented
            else "NO"
        ),
    )

    # Conservative readiness:
    #
    # We are ready for a SECOND adjudication step only if
    # exact result-linked identities are unique and the
    # narrative is direct.
    #
    # No promotion occurs here.
    #
    adjudication_ready = (
        unique_speed_identity
        and
        narrative_first_run
    )

    # ========================================================
    # WRITE
    # ========================================================

    write_csv(
        AUDIT_OUT,
        audit_rows,
        [
            "attempt_id",
            "car_attempt_index",
            "canonical_speed_mph",
            "attempt_class",
            "result_status",
            "source_native_locator",
            "has_official_result_link",
            "official_result_row",
            "official_speed_mph",
            "official_status",
        ],
    )

    qa_rows = [
        {
            "metric":
                "castroneves_canonical_objects",

            "value":
                len(
                    castroneves_canonical
                ),

            "status":
                "INFO",
        },

        {
            "metric":
                "index1_object_count",

            "value":
                len(
                    index1_rows
                ),

            "status":
                "INFO",
        },

        {
            "metric":
                "unique_225482_result_link",

            "value":
                len(
                    first_speed_matches
                ),

            "status":
                (
                    "PASS"
                    if len(
                        first_speed_matches
                    ) == 1
                    else "FAIL"
                ),
        },

        {
            "metric":
                "unique_229630_result_link",

            "value":
                len(
                    second_speed_matches
                ),

            "status":
                (
                    "PASS"
                    if len(
                        second_speed_matches
                    ) == 1
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
                    if narrative_first_run
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
                "result_row_order_used_as_chronology",

            "value":
                0,

            "status":
                "PASS",
        },

        {
            "metric":
                "duplicate_index1_silently_merged",

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
    # FINAL
    # ========================================================

    print()
    print("=" * 120)
    print(
        "FINAL SUMMARY"
    )
    print("=" * 120)

    print()
    print(
        "Castroneves canonical objects:",
        len(
            castroneves_canonical
        ),
    )

    print(
        "Canonical objects marked index=1:",
        len(
            index1_rows
        ),
    )

    print()
    print(
        "Official-linked 225.482 attempt_id:",
        first_id
        or
        "UNRESOLVED",
    )

    print(
        "Official-linked 229.630 attempt_id:",
        second_id
        or
        "UNRESOLVED",
    )

    print()
    print(
        "Direct first-run bail-out evidence:",
        (
            "PRESENT"
            if narrative_first_run
            else "ABSENT"
        ),
    )

    print(
        "Adjudication ready:",
        adjudication_ready,
    )

    print()
    print(
        "No action was promoted in this audit."
    )

    print(
        "The duplicate car_attempt_index=1 condition "
        "was documented rather than silently resolved."
    )

    print(
        "No result-row ordering was used as chronology."
    )

    print(
        "No canonical data was modified."
    )

    print()
    print("=" * 120)

    if adjudication_ready:

        print(
            "FINAL STATUS: "
            "CASTRONEVES_FIRST_RUN_IDENTITY_ADJUDICATION_READY"
        )

    else:

        print(
            "FINAL STATUS: "
            "CASTRONEVES_FIRST_RUN_IDENTITY_REMAINS_AMBIGUOUS"
        )

    print("=" * 120)

    print()
    print("OUTPUTS")
    print(AUDIT_OUT)
    print(QA_OUT)


if __name__ == "__main__":
    main()
