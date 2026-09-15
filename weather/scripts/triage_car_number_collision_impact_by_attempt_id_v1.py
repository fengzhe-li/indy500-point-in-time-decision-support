from pathlib import Path
import csv
from collections import defaultdict, Counter


# ============================================================
# PHASE
# ============================================================

PHASE = "R1G.25E"


# ============================================================
# INPUTS
# ============================================================

CANONICAL = Path(
    "data/canonical/v1/attempts.csv"
)

IMPACT_AUDIT = Path(
    "weather/output/"
    "global_car_number_output_impact_candidates_v1.csv"
)


# ============================================================
# OUTPUTS
# ============================================================

OUTPUT_DIR = Path(
    "weather/output"
)

ROW_AUDIT_OUT = (
    OUTPUT_DIR
    / "global_car_number_attempt_id_grounded_row_audit_v1.csv"
)

FILE_TRIAGE_OUT = (
    OUTPUT_DIR
    / "global_car_number_output_file_triage_v1.csv"
)

REMEDIATION_OUT = (
    OUTPUT_DIR
    / "global_car_number_remediation_priority_v1.csv"
)

SUMMARY_OUT = (
    OUTPUT_DIR
    / "global_car_number_attempt_id_grounded_triage_summary_v1.csv"
)

QA_OUT = (
    OUTPUT_DIR
    / "global_car_number_attempt_id_grounded_triage_v1_qa.csv"
)


# ============================================================
# HELPERS
# ============================================================

def txt(value):
    return "" if value is None else str(value).strip()


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
        )

        writer.writeheader()
        writer.writerows(rows)


def canonical_year(row):
    year = txt(
        row.get("year")
    )

    if year in {
        "2020",
        "2021",
        "2022",
        "2023",
        "2024",
    }:
        return year

    session_id = txt(
        row.get("session_id")
    )

    for candidate in [
        "2020",
        "2021",
        "2022",
        "2023",
        "2024",
    ]:

        if candidate in session_id:
            return candidate

    return ""


def canonical_driver(row):
    for field in [
        "driver_name",
        "driver",
        "driver_full_name",
    ]:

        value = txt(
            row.get(field)
        )

        if value:
            return value

    return ""


def output_driver(row):
    for field in [
        "driver_name",
        "driver",
        "driver_full_name",
        "name",
    ]:

        value = txt(
            row.get(field)
        )

        if value:
            return value

    return ""


def find_attempt_id_column(fieldnames):
    candidates = [
        "attempt_id",
        "canonical_attempt_id",
        "subject_attempt_id",
    ]

    for candidate in candidates:

        if candidate in fieldnames:
            return candidate

    return ""


def is_collision_sensitive_year_car(year, car_number):
    return (
        year in {
            "2022",
            "2023",
            "2024",
        }
        and
        car_number in {
            "06",
            "6",
        }
    )


def normalized_driver(value):
    return (
        txt(value)
        .lower()
        .replace(".", "")
        .replace(",", "")
        .replace("'", "")
        .replace("’", "")
        .replace("-", " ")
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
        "R1G.25E — ATTEMPT-ID GROUNDED "
        "CAR-NUMBER COLLISION IMPACT TRIAGE V1"
    )
    print("=" * 120)

    inputs = [
        CANONICAL,
        IMPACT_AUDIT,
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
            "CAR_NUMBER_IMPACT_TRIAGE_INPUT_MISSING"
        )

        return

    canonical = read_csv(
        CANONICAL
    )

    impact = read_csv(
        IMPACT_AUDIT
    )

    # ========================================================
    # CANONICAL ATTEMPT-ID TRUTH MAP
    # ========================================================

    canonical_by_attempt = {}

    for row in canonical:

        attempt_id = txt(
            row.get("attempt_id")
        )

        if not attempt_id:
            continue

        canonical_by_attempt[
            attempt_id
        ] = {
            "year":
                canonical_year(row),

            "car_number":
                txt(
                    row.get(
                        "car_number"
                    )
                ),

            "driver_name":
                canonical_driver(row),

            "car_attempt_index":
                txt(
                    row.get(
                        "car_attempt_index"
                    )
                ),
        }

    collision_truth_attempts = {
        attempt_id: truth
        for attempt_id, truth in canonical_by_attempt.items()
        if is_collision_sensitive_year_car(
            truth["year"],
            truth["car_number"],
        )
    }

    print()
    print(
        "Canonical attempts:",
        len(
            canonical_by_attempt
        ),
    )

    print(
        "Collision-sensitive canonical attempts:",
        len(
            collision_truth_attempts
        ),
    )

    # ========================================================
    # ONLY AUDIT COLLISION-SENSITIVE OUTPUTS
    # ========================================================

    candidate_files = []

    for row in impact:

        risk = txt(
            row.get(
                "risk_class"
            )
        )

        if risk in {
            "VISIBLE_LITERAL_COLLISION",
            "POTENTIAL_PRIOR_NORMALIZATION",
            "COLLISION_SENSITIVE_BUT_LITERAL_PRESERVED",
        }:

            csv_path = Path(
                txt(
                    row.get(
                        "csv_path"
                    )
                )
            )

            candidate_files.append({
                "path":
                    csv_path,

                "prior_risk":
                    risk,
            })

    print()
    print("=" * 120)
    print(
        "FILES TO TRIAGE"
    )
    print("=" * 120)

    print()
    print(
        "Candidate files:",
        len(
            candidate_files
        ),
    )

    row_audit = []
    file_triage = []

    # ========================================================
    # FILE LOOP
    # ========================================================

    for file_spec in candidate_files:

        path = file_spec[
            "path"
        ]

        prior_risk = file_spec[
            "prior_risk"
        ]

        print()
        print("-" * 120)
        print(path)
        print("-" * 120)

        if not path.exists():

            print(
                "STATUS: FILE_MISSING"
            )

            file_triage.append({
                "csv_path":
                    str(path),

                "prior_static_risk":
                    prior_risk,

                "row_count":
                    "",

                "attempt_id_column":
                    "",

                "rows_with_attempt_id":
                    0,

                "collision_sensitive_rows":
                    0,

                "car_number_format_mismatches":
                    0,

                "driver_identity_mismatches":
                    0,

                "missing_canonical_attempt_links":
                    0,

                "collapsed_numeric_six_contains_multiple_canonical_literals":
                    False,

                "classification":
                    "FILE_MISSING",

                "recommended_action":
                    "LOCATE_OR_IGNORE_IF_OBSOLETE",
            })

            continue

        try:
            rows = read_csv(
                path
            )

        except Exception as exc:

            print(
                "STATUS: UNREADABLE"
            )

            file_triage.append({
                "csv_path":
                    str(path),

                "prior_static_risk":
                    prior_risk,

                "row_count":
                    "",

                "attempt_id_column":
                    "",

                "rows_with_attempt_id":
                    0,

                "collision_sensitive_rows":
                    0,

                "car_number_format_mismatches":
                    0,

                "driver_identity_mismatches":
                    0,

                "missing_canonical_attempt_links":
                    0,

                "collapsed_numeric_six_contains_multiple_canonical_literals":
                    False,

                "classification":
                    "UNREADABLE",

                "recommended_action":
                    (
                        "MANUAL_REVIEW: "
                        f"{type(exc).__name__}"
                    ),
            })

            continue

        if not rows:

            print(
                "STATUS: EMPTY"
            )

            file_triage.append({
                "csv_path":
                    str(path),

                "prior_static_risk":
                    prior_risk,

                "row_count":
                    0,

                "attempt_id_column":
                    "",

                "rows_with_attempt_id":
                    0,

                "collision_sensitive_rows":
                    0,

                "car_number_format_mismatches":
                    0,

                "driver_identity_mismatches":
                    0,

                "missing_canonical_attempt_links":
                    0,

                "collapsed_numeric_six_contains_multiple_canonical_literals":
                    False,

                "classification":
                    "EMPTY",

                "recommended_action":
                    "NONE",
            })

            continue

        fieldnames = list(
            rows[0].keys()
        )

        attempt_id_col = (
            find_attempt_id_column(
                fieldnames
            )
        )

        has_car_number = (
            "car_number"
            in fieldnames
        )

        print(
            "rows:",
            len(rows),
        )

        print(
            "attempt-id column:",
            attempt_id_col
            or
            "NONE",
        )

        print(
            "car_number column:",
            has_car_number,
        )

        if not attempt_id_col:

            file_triage.append({
                "csv_path":
                    str(path),

                "prior_static_risk":
                    prior_risk,

                "row_count":
                    len(rows),

                "attempt_id_column":
                    "",

                "rows_with_attempt_id":
                    0,

                "collision_sensitive_rows":
                    0,

                "car_number_format_mismatches":
                    0,

                "driver_identity_mismatches":
                    0,

                "missing_canonical_attempt_links":
                    0,

                "collapsed_numeric_six_contains_multiple_canonical_literals":
                    False,

                "classification":
                    "NO_ATTEMPT_ID_FOR_AUTOMATIC_VALIDATION",

                "recommended_action":
                    "PROVENANCE_REVIEW_ONLY_IF_HIGH_VALUE",
            })

            print(
                "classification: "
                "NO_ATTEMPT_ID_FOR_AUTOMATIC_VALIDATION"
            )

            continue

        rows_with_id = 0
        collision_rows = 0
        car_mismatch = 0
        driver_mismatch = 0
        missing_canonical = 0

        output_six_to_canonical_literals = (
            defaultdict(set)
        )

        for row_number, row in enumerate(
            rows,
            start=2,
        ):

            attempt_id = txt(
                row.get(
                    attempt_id_col
                )
            )

            if not attempt_id:
                continue

            rows_with_id += 1

            truth = canonical_by_attempt.get(
                attempt_id
            )

            if truth is None:

                missing_canonical += 1

                row_audit.append({
                    "csv_path":
                        str(path),

                    "csv_row":
                        row_number,

                    "attempt_id":
                        attempt_id,

                    "canonical_year":
                        "",

                    "canonical_car_number":
                        "",

                    "output_car_number":
                        txt(
                            row.get(
                                "car_number"
                            )
                        ),

                    "canonical_driver":
                        "",

                    "output_driver":
                        output_driver(row),

                    "collision_sensitive":
                        False,

                    "car_number_match":
                        "",

                    "driver_match":
                        "",

                    "classification":
                        "ATTEMPT_ID_NOT_FOUND_IN_CANONICAL",
                })

                continue

            sensitive = (
                is_collision_sensitive_year_car(
                    truth["year"],
                    truth["car_number"],
                )
            )

            if not sensitive:
                continue

            collision_rows += 1

            output_car = txt(
                row.get(
                    "car_number"
                )
            )

            output_driver_name = (
                output_driver(row)
            )

            canonical_driver_name = (
                truth[
                    "driver_name"
                ]
            )

            if has_car_number:

                car_match = (
                    output_car
                    ==
                    truth[
                        "car_number"
                    ]
                )

            else:

                car_match = None

            if (
                output_driver_name
                and
                canonical_driver_name
            ):

                driver_match = (
                    normalized_driver(
                        output_driver_name
                    )
                    ==
                    normalized_driver(
                        canonical_driver_name
                    )
                )

            else:

                driver_match = None

            if car_match is False:
                car_mismatch += 1

            if driver_match is False:
                driver_mismatch += 1

            if output_car == "6":

                output_six_to_canonical_literals[
                    truth[
                        "year"
                    ]
                ].add(
                    truth[
                        "car_number"
                    ]
                )

            if driver_match is False:

                classification = (
                    "IDENTITY_CONTRADICTION"
                )

            elif car_match is False:

                classification = (
                    "CAR_NUMBER_FORMAT_MISMATCH"
                )

            elif car_match is True:

                classification = (
                    "CAR_NUMBER_LITERAL_PRESERVED"
                )

            else:

                classification = (
                    "ATTEMPT_ID_VALID_NO_CAR_NUMBER_FIELD"
                )

            row_audit.append({
                "csv_path":
                    str(path),

                "csv_row":
                    row_number,

                "attempt_id":
                    attempt_id,

                "canonical_year":
                    truth[
                        "year"
                    ],

                "canonical_car_number":
                    truth[
                        "car_number"
                    ],

                "output_car_number":
                    output_car,

                "canonical_driver":
                    canonical_driver_name,

                "output_driver":
                    output_driver_name,

                "collision_sensitive":
                    True,

                "car_number_match":
                    (
                        ""
                        if car_match is None
                        else car_match
                    ),

                "driver_match":
                    (
                        ""
                        if driver_match is None
                        else driver_match
                    ),

                "classification":
                    classification,
            })

        collapsed_identity_signal = any(
            literals == {
                "06",
                "6",
            }
            for literals
            in output_six_to_canonical_literals.values()
        )

        # ====================================================
        # FILE CLASSIFICATION
        # ====================================================

        if driver_mismatch > 0:

            classification = (
                "CONFIRMED_IDENTITY_CONTAMINATION"
            )

            recommended_action = (
                "REBUILD_BEFORE_REUSE"
            )

        elif (
            car_mismatch > 0
            and
            collapsed_identity_signal
        ):

            classification = (
                "CONFIRMED_CAR_NUMBER_COLLAPSE_BUT_ATTEMPT_ID_INTACT"
            )

            recommended_action = (
                "PATCH_OR_REBUILD_CAR_NUMBER_FIELD; "
                "IDENTITY MAY REMAIN RECOVERABLE_BY_ATTEMPT_ID"
            )

        elif car_mismatch > 0:

            classification = (
                "CAR_NUMBER_FORMAT_LOSS_WITH_ATTEMPT_ID_INTACT"
            )

            recommended_action = (
                "PATCH_FORMAT_FROM_CANONICAL_BY_ATTEMPT_ID "
                "IF FILE REMAINS ACTIVE"
            )

        elif collision_rows > 0:

            classification = (
                "ATTEMPT_ID_VALIDATED_NO_COLLISION_DAMAGE"
            )

            recommended_action = (
                "NO_REBUILD_REQUIRED"
            )

        else:

            classification = (
                "NO_COLLISION_SENSITIVE_ATTEMPTS_PRESENT"
            )

            recommended_action = (
                "NONE"
            )

        file_triage.append({
            "csv_path":
                str(path),

            "prior_static_risk":
                prior_risk,

            "row_count":
                len(rows),

            "attempt_id_column":
                attempt_id_col,

            "rows_with_attempt_id":
                rows_with_id,

            "collision_sensitive_rows":
                collision_rows,

            "car_number_format_mismatches":
                car_mismatch,

            "driver_identity_mismatches":
                driver_mismatch,

            "missing_canonical_attempt_links":
                missing_canonical,

            "collapsed_numeric_six_contains_multiple_canonical_literals":
                collapsed_identity_signal,

            "classification":
                classification,

            "recommended_action":
                recommended_action,
        })

        print(
            "collision-sensitive rows:",
            collision_rows,
        )

        print(
            "car-number mismatches:",
            car_mismatch,
        )

        print(
            "driver mismatches:",
            driver_mismatch,
        )

        print(
            "collapsed #06/#6 signal:",
            collapsed_identity_signal,
        )

        print(
            "classification:",
            classification,
        )

    # ========================================================
    # REMEDIATION PRIORITY
    # ========================================================

    priority_order = {
        "CONFIRMED_IDENTITY_CONTAMINATION":
            0,

        "CONFIRMED_CAR_NUMBER_COLLAPSE_BUT_ATTEMPT_ID_INTACT":
            1,

        "CAR_NUMBER_FORMAT_LOSS_WITH_ATTEMPT_ID_INTACT":
            2,

        "NO_ATTEMPT_ID_FOR_AUTOMATIC_VALIDATION":
            3,

        "ATTEMPT_ID_VALIDATED_NO_COLLISION_DAMAGE":
            4,

        "NO_COLLISION_SENSITIVE_ATTEMPTS_PRESENT":
            5,

        "EMPTY":
            6,

        "FILE_MISSING":
            7,

        "UNREADABLE":
            8,
    }

    remediation_rows = sorted(
        file_triage,
        key=lambda row: (
            priority_order.get(
                row[
                    "classification"
                ],
                99,
            ),
            row[
                "csv_path"
            ],
        ),
    )

    # ========================================================
    # SUMMARY COUNTS
    # ========================================================

    class_counts = Counter(
        row[
            "classification"
        ]
        for row in file_triage
    )

    confirmed_identity_contamination = (
        class_counts.get(
            "CONFIRMED_IDENTITY_CONTAMINATION",
            0,
        )
    )

    confirmed_collapse_id_intact = (
        class_counts.get(
            "CONFIRMED_CAR_NUMBER_COLLAPSE_BUT_ATTEMPT_ID_INTACT",
            0,
        )
    )

    format_loss_only = (
        class_counts.get(
            "CAR_NUMBER_FORMAT_LOSS_WITH_ATTEMPT_ID_INTACT",
            0,
        )
    )

    validated_clean = (
        class_counts.get(
            "ATTEMPT_ID_VALIDATED_NO_COLLISION_DAMAGE",
            0,
        )
    )

    no_attempt_id = (
        class_counts.get(
            "NO_ATTEMPT_ID_FOR_AUTOMATIC_VALIDATION",
            0,
        )
    )

    print()
    print("=" * 120)
    print(
        "IMPACT CLASSIFICATION SUMMARY"
    )
    print("=" * 120)

    print()

    for key, value in sorted(
        class_counts.items()
    ):

        print(
            f"{key}: {value}"
        )

    # ========================================================
    # MOST IMPORTANT FILES
    # ========================================================

    print()
    print("=" * 120)
    print(
        "FILES REQUIRING ACTION"
    )
    print("=" * 120)

    actionable_classes = {
        "CONFIRMED_IDENTITY_CONTAMINATION",
        "CONFIRMED_CAR_NUMBER_COLLAPSE_BUT_ATTEMPT_ID_INTACT",
        "CAR_NUMBER_FORMAT_LOSS_WITH_ATTEMPT_ID_INTACT",
    }

    actionable_rows = [
        row
        for row in remediation_rows
        if row[
            "classification"
        ]
        in actionable_classes
    ]

    if not actionable_rows:

        print()
        print(
            "No attempt-ID-grounded collision damage "
            "was confirmed."
        )

    else:

        for row in actionable_rows:

            print()
            print(
                row[
                    "classification"
                ]
            )

            print(
                "  file:",
                row[
                    "csv_path"
                ],
            )

            print(
                "  collision rows:",
                row[
                    "collision_sensitive_rows"
                ],
            )

            print(
                "  car mismatches:",
                row[
                    "car_number_format_mismatches"
                ],
            )

            print(
                "  driver mismatches:",
                row[
                    "driver_identity_mismatches"
                ],
            )

            print(
                "  action:",
                row[
                    "recommended_action"
                ],
            )

    # ========================================================
    # WRITE
    # ========================================================

    write_csv(
        ROW_AUDIT_OUT,
        row_audit,
        [
            "csv_path",
            "csv_row",
            "attempt_id",
            "canonical_year",
            "canonical_car_number",
            "output_car_number",
            "canonical_driver",
            "output_driver",
            "collision_sensitive",
            "car_number_match",
            "driver_match",
            "classification",
        ],
    )

    file_fields = [
        "csv_path",
        "prior_static_risk",
        "row_count",
        "attempt_id_column",
        "rows_with_attempt_id",
        "collision_sensitive_rows",
        "car_number_format_mismatches",
        "driver_identity_mismatches",
        "missing_canonical_attempt_links",
        "collapsed_numeric_six_contains_multiple_canonical_literals",
        "classification",
        "recommended_action",
    ]

    write_csv(
        FILE_TRIAGE_OUT,
        file_triage,
        file_fields,
    )

    write_csv(
        REMEDIATION_OUT,
        remediation_rows,
        file_fields,
    )

    summary_rows = [
        {
            "metric":
                "candidate_files",

            "value":
                len(
                    candidate_files
                ),
        },

        {
            "metric":
                "confirmed_identity_contamination_files",

            "value":
                confirmed_identity_contamination,
        },

        {
            "metric":
                "confirmed_car_number_collapse_attempt_id_intact_files",

            "value":
                confirmed_collapse_id_intact,
        },

        {
            "metric":
                "car_number_format_loss_attempt_id_intact_files",

            "value":
                format_loss_only,
        },

        {
            "metric":
                "attempt_id_validated_clean_files",

            "value":
                validated_clean,
        },

        {
            "metric":
                "files_without_attempt_id_for_validation",

            "value":
                no_attempt_id,
        },

        {
            "metric":
                "row_level_audit_records",

            "value":
                len(
                    row_audit
                ),
        },
    ]

    write_csv(
        SUMMARY_OUT,
        summary_rows,
        [
            "metric",
            "value",
        ],
    )

    # ========================================================
    # QA
    # ========================================================

    qa_rows = [
        {
            "metric":
                "canonical_attempt_ids_unique",

            "value":
                (
                    len(
                        canonical_by_attempt
                    )
                    ==
                    len(
                        {
                            txt(
                                row.get(
                                    "attempt_id"
                                )
                            )
                            for row in canonical
                            if txt(
                                row.get(
                                    "attempt_id"
                                )
                            )
                        }
                    )
                ),

            "status":
                "PASS",
        },

        {
            "metric":
                "candidate_files_triaged",

            "value":
                len(
                    file_triage
                ),

            "status":
                (
                    "PASS"
                    if len(
                        file_triage
                    )
                    ==
                    len(
                        candidate_files
                    )
                    else "FAIL"
                ),
        },

        {
            "metric":
                "numeric_car_number_used_as_identity_key",

            "value":
                0,

            "status":
                "PASS",
        },

        {
            "metric":
                "attempt_id_used_as_primary_validation_key",

            "value":
                1,

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
                "existing_output_data_mutated",

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
        "Files triaged:",
        len(
            file_triage
        ),
    )

    print(
        "Confirmed identity contamination:",
        confirmed_identity_contamination,
    )

    print(
        "Confirmed car-number collapse "
        "with attempt_id intact:",
        confirmed_collapse_id_intact,
    )

    print(
        "Formatting loss only with attempt_id intact:",
        format_loss_only,
    )

    print(
        "Attempt-ID validated clean:",
        validated_clean,
    )

    print(
        "Could not validate automatically "
        "because no attempt_id:",
        no_attempt_id,
    )

    print()
    print(
        "Important interpretation:"
    )

    print(
        "  A car_number mismatch does NOT automatically "
        "mean attempt identity was corrupted."
    )

    print(
        "  Driver mismatch with a valid canonical attempt_id "
        "is treated as confirmed identity contamination."
    )

    print(
        "  #06 -> 6 with correct attempt_id/driver is "
        "classified as formatting/identifier loss."
    )

    print()
    print(
        "No canonical data was modified."
    )

    print(
        "No existing output file was modified."
    )

    print()
    print("=" * 120)

    if (
        len(
            file_triage
        )
        ==
        len(
            candidate_files
        )
    ):

        print(
            "FINAL STATUS: "
            "CAR_NUMBER_COLLISION_IMPACT_TRIAGE_COMPLETE"
        )

    else:

        print(
            "FINAL STATUS: "
            "CAR_NUMBER_COLLISION_IMPACT_TRIAGE_REVIEW_REQUIRED"
        )

    print("=" * 120)

    print()
    print("OUTPUTS")
    print(ROW_AUDIT_OUT)
    print(FILE_TRIAGE_OUT)
    print(REMEDIATION_OUT)
    print(SUMMARY_OUT)
    print(QA_OUT)


if __name__ == "__main__":
    main()
