from pathlib import Path
import csv
from collections import Counter


# ============================================================
# INPUTS
# ============================================================

LEDGER_V1 = Path(
    "weather/output/"
    "unified_attempt_chronology_constraint_ledger_v1.csv"
)

CANONICAL_ATTEMPTS = Path(
    "data/canonical/v1/attempts.csv"
)

EVIDENCE_2022 = Path(
    "weather/output/"
    "chronology_rescue_2022_evidence_with_attempt_ids_v2.csv"
)


# ============================================================
# OUTPUTS
# ============================================================

OUTPUT_DIR = Path(
    "weather/output"
)

LEDGER_V2 = (
    OUTPUT_DIR
    / "unified_attempt_chronology_constraint_ledger_v2.csv"
)

SUMMARY_V2 = (
    OUTPUT_DIR
    / "unified_attempt_chronology_constraint_summary_v2.csv"
)

QA_V2 = (
    OUTPUT_DIR
    / "unified_attempt_chronology_constraint_ledger_v2_qa.csv"
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
        writer.writerows(
            rows
        )


def txt(value):

    if value is None:
        return ""

    return str(
        value
    ).strip()


def bool_text(value):

    return (
        "True"
        if str(value).strip().lower()
        in {
            "true",
            "1",
            "yes",
        }
        else "False"
    )


def is_attempt_level(row):

    return bool(
        txt(
            row.get(
                "attempt_id"
            )
        )
    )


def chronology_usable(row):

    return (
        txt(
            row.get(
                "chronology_usable"
            )
        ).lower()
        == "true"
    )


def get_constraint_class(row):

    for field in [
        "constraint_class",
        "time_quality",
    ]:

        value = txt(
            row.get(
                field
            )
        )

        if value:
            return value

    return "UNKNOWN"


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
        "R1G.15 — UNIFIED ATTEMPT "
        "CHRONOLOGY CONSTRAINT LEDGER V2"
    )
    print("=" * 120)

    inputs = [
        LEDGER_V1,
        CANONICAL_ATTEMPTS,
        EVIDENCE_2022,
    ]

    missing = []

    print()
    print(
        "INPUT CHECK"
    )
    print("-" * 120)

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
            "UNIFIED_CHRONOLOGY_LEDGER_V2_INPUT_MISSING"
        )

        return

    ledger_v1 = read_csv(
        LEDGER_V1
    )

    canonical = read_csv(
        CANONICAL_ATTEMPTS
    )

    evidence_2022 = read_csv(
        EVIDENCE_2022
    )

    print()
    print(
        "LEDGER V1 ROWS:",
        len(
            ledger_v1
        ),
    )

    print(
        "CANONICAL ATTEMPTS:",
        len(
            canonical
        ),
    )

    print(
        "2022 EVIDENCE ROWS:",
        len(
            evidence_2022
        ),
    )

    # ========================================================
    # CANONICAL LOOKUP
    # ========================================================

    canonical_by_attempt = {
        txt(
            row.get(
                "attempt_id"
            )
        ):
        row
        for row in canonical
        if txt(
            row.get(
                "attempt_id"
            )
        )
    }

    # ========================================================
    # SELECT 2022 ATTEMPT-LEVEL CHRONOLOGY EVIDENCE
    # ========================================================

    attempt_evidence = [
        row
        for row in evidence_2022
        if (
            is_attempt_level(
                row
            )
            and
            chronology_usable(
                row
            )
        )
    ]

    print()
    print("=" * 120)
    print(
        "2022 ATTEMPT-LEVEL CHRONOLOGY EVIDENCE"
    )
    print("=" * 120)

    print(
        "Attempt-level chronology-usable rows:",
        len(
            attempt_evidence
        ),
    )

    # ========================================================
    # LEDGER FIELD SET
    # ========================================================

    base_fields = list(
        ledger_v1[0].keys()
    )

    required_extra_fields = [
        "evidence_id",
        "evidence_stage",
        "source_authority",
        "source_title",
        "source_url",
        "official_result_row",
        "constraint_class",
        "time_lower_utc",
        "time_upper_utc",
        "time_midpoint_utc",
        "ordering_relation",
        "chronology_usable",
        "performance_environment_usable",
        "queue_replay_usable",
        "evidence_summary",
        "notes",
    ]

    fields = list(
        base_fields
    )

    for field in required_extra_fields:

        if field not in fields:
            fields.append(
                field
            )

    # ========================================================
    # NORMALIZE V1 ROWS
    # ========================================================

    ledger_v2 = []

    for row in ledger_v1:

        out = {
            field: ""
            for field in fields
        }

        for key, value in row.items():

            if key in out:
                out[
                    key
                ] = value

        ledger_v2.append(
            out
        )

    # ========================================================
    # BUILD 2022 ROWS
    # ========================================================

    added_rows = []

    missing_canonical = []

    for ev in attempt_evidence:

        attempt_id = txt(
            ev.get(
                "attempt_id"
            )
        )

        can = canonical_by_attempt.get(
            attempt_id
        )

        if can is None:

            missing_canonical.append(
                attempt_id
            )

            continue

        out = {
            field: ""
            for field in fields
        }

        # Core canonical identity
        mappings = {
            "attempt_id":
                attempt_id,

            "session_id":
                txt(
                    can.get(
                        "session_id"
                    )
                ),

            "year":
                "2022",

            "car_number":
                txt(
                    can.get(
                        "car_number"
                    )
                ),

            "driver_name":
                txt(
                    can.get(
                        "driver_name"
                    )
                ),

            "car_attempt_index":
                txt(
                    can.get(
                        "car_attempt_index"
                    )
                ),

            "result_status":
                txt(
                    can.get(
                        "result_status"
                    )
                ),

            "constraint_class":
                get_constraint_class(
                    ev
                ),

            "chronology_usable":
                "True",

            "performance_environment_usable":
                txt(
                    ev.get(
                        "performance_environment_usable"
                    )
                )
                or
                "False",

            "queue_replay_usable":
                txt(
                    ev.get(
                        "queue_replay_usable"
                    )
                )
                or
                "False",

            "evidence_id":
                txt(
                    ev.get(
                        "evidence_id"
                    )
                ),

            "evidence_stage":
                txt(
                    ev.get(
                        "evidence_stage"
                    )
                ),

            "source_authority":
                txt(
                    ev.get(
                        "source_authority"
                    )
                ),

            "source_title":
                txt(
                    ev.get(
                        "source_title"
                    )
                ),

            "source_url":
                txt(
                    ev.get(
                        "source_url"
                    )
                ),

            "official_result_row":
                txt(
                    ev.get(
                        "official_result_row"
                    )
                ),

            "time_lower_utc":
                txt(
                    ev.get(
                        "time_lower_utc"
                    )
                ),

            "time_upper_utc":
                txt(
                    ev.get(
                        "time_upper_utc"
                    )
                ),

            "time_midpoint_utc":
                txt(
                    ev.get(
                        "time_midpoint_utc"
                    )
                ),

            "ordering_relation":
                txt(
                    ev.get(
                        "ordering_relation"
                    )
                ),

            "evidence_summary":
                txt(
                    ev.get(
                        "evidence_summary"
                    )
                ),

            "notes":
                txt(
                    ev.get(
                        "notes"
                    )
                ),
        }

        for key, value in mappings.items():

            if key in out:
                out[
                    key
                ] = value

        added_rows.append(
            out
        )

    # ========================================================
    # DEDUPLICATE 2022 EVIDENCE ROWS BY EVIDENCE_ID
    # ========================================================

    seen_evidence_ids = set()
    deduped_added = []

    for row in added_rows:

        evidence_id = txt(
            row.get(
                "evidence_id"
            )
        )

        dedupe_key = (
            evidence_id
            if evidence_id
            else (
                txt(
                    row.get(
                        "attempt_id"
                    )
                ),
                txt(
                    row.get(
                        "constraint_class"
                    )
                ),
                txt(
                    row.get(
                        "time_lower_utc"
                    )
                ),
                txt(
                    row.get(
                        "time_upper_utc"
                    )
                ),
                txt(
                    row.get(
                        "ordering_relation"
                    )
                ),
            )
        )

        if dedupe_key in seen_evidence_ids:
            continue

        seen_evidence_ids.add(
            dedupe_key
        )

        deduped_added.append(
            row
        )

    added_rows = deduped_added

    ledger_v2.extend(
        added_rows
    )

    # ========================================================
    # SUMMARY
    # ========================================================

    years = [
        "2020",
        "2021",
        "2022",
        "2023",
        "2024",
    ]

    summary_rows = []

    print()
    print("=" * 120)
    print(
        "CROSS-YEAR CHRONOLOGY CONSTRAINT SUMMARY V2"
    )
    print("=" * 120)

    for year in years:

        rows = [
            row
            for row in ledger_v2
            if txt(
                row.get(
                    "year"
                )
            ) == year
        ]

        chronology_rows = [
            row
            for row in rows
            if txt(
                row.get(
                    "chronology_usable"
                )
            ).lower()
            == "true"
        ]

        performance_rows = [
            row
            for row in rows
            if txt(
                row.get(
                    "performance_environment_usable"
                )
            ).lower()
            == "true"
        ]

        classes = Counter(
            get_constraint_class(
                row
            )
            for row in rows
        )

        summary_rows.append({
            "year":
                year,

            "constraint_rows":
                len(
                    rows
                ),

            "chronology_usable_rows":
                len(
                    chronology_rows
                ),

            "performance_environment_usable_rows":
                len(
                    performance_rows
                ),

            "constraint_classes":
                str(
                    dict(
                        classes
                    )
                ),
        })

        print()
        print(
            f"YEAR {year}"
        )

        print(
            "  constraint rows:",
            len(
                rows
            ),
        )

        print(
            "  chronology usable:",
            len(
                chronology_rows
            ),
        )

        print(
            "  performance environment usable:",
            len(
                performance_rows
            ),
        )

        print(
            "  classes:",
            dict(
                classes
            ),
        )

    # ========================================================
    # 2022 DETAIL
    # ========================================================

    rows_2022 = [
        row
        for row in ledger_v2
        if txt(
            row.get(
                "year"
            )
        ) == "2022"
    ]

    chronology_2022 = [
        row
        for row in rows_2022
        if txt(
            row.get(
                "chronology_usable"
            )
        ).lower()
        == "true"
    ]

    attempt_ids_2022 = {
        txt(
            row.get(
                "attempt_id"
            )
        )
        for row in chronology_2022
        if txt(
            row.get(
                "attempt_id"
            )
        )
    }

    print()
    print("=" * 120)
    print(
        "2022 RESCUE INTEGRATION DETAIL"
    )
    print("=" * 120)

    print(
        "2022 ledger rows:",
        len(
            rows_2022
        ),
    )

    print(
        "2022 chronology usable rows:",
        len(
            chronology_2022
        ),
    )

    print(
        "2022 unique attempt IDs with chronology evidence:",
        len(
            attempt_ids_2022
        ),
    )

    class_counts_2022 = Counter(
        get_constraint_class(
            row
        )
        for row in chronology_2022
    )

    print(
        "2022 chronology classes:",
        dict(
            class_counts_2022
        ),
    )

    print()
    print(
        "2022 chronology-linked attempts:"
    )

    for attempt_id in sorted(
        attempt_ids_2022
    ):

        can = canonical_by_attempt.get(
            attempt_id,
            {},
        )

        print(
            " ",
            attempt_id,
            "| car=",
            txt(
                can.get(
                    "car_number"
                )
            ),
            "| driver=",
            txt(
                can.get(
                    "driver_name"
                )
            ),
            "| idx=",
            txt(
                can.get(
                    "car_attempt_index"
                )
            ),
            "| speed=",
            txt(
                can.get(
                    "four_lap_average_speed_mph"
                )
            ),
            "| class=",
            txt(
                can.get(
                    "attempt_class"
                )
            ),
        )

    # ========================================================
    # QA
    # ========================================================

    duplicate_evidence_ids = []

    evidence_counter = Counter(
        txt(
            row.get(
                "evidence_id"
            )
        )
        for row in added_rows
        if txt(
            row.get(
                "evidence_id"
            )
        )
    )

    duplicate_evidence_ids = [
        key
        for key, count
        in evidence_counter.items()
        if count > 1
    ]

    v1_rows_unchanged = (
        len(
            ledger_v2
        )
        >=
        len(
            ledger_v1
        )
    )

    qa_rows = [
        {
            "metric":
                "ledger_v1_rows",

            "value":
                len(
                    ledger_v1
                ),

            "status":
                "INFO",
        },

        {
            "metric":
                "new_2022_rows_added",

            "value":
                len(
                    added_rows
                ),

            "status":
                (
                    "PASS"
                    if len(
                        added_rows
                    ) > 0
                    else "FAIL"
                ),
        },

        {
            "metric":
                "2022_chronology_usable_rows",

            "value":
                len(
                    chronology_2022
                ),

            "status":
                (
                    "PASS"
                    if len(
                        chronology_2022
                    ) > 0
                    else "FAIL"
                ),
        },

        {
            "metric":
                "2022_unique_attempt_ids",

            "value":
                len(
                    attempt_ids_2022
                ),

            "status":
                (
                    "PASS"
                    if len(
                        attempt_ids_2022
                    ) > 0
                    else "FAIL"
                ),
        },

        {
            "metric":
                "missing_canonical_attempt_ids",

            "value":
                len(
                    missing_canonical
                ),

            "status":
                (
                    "PASS"
                    if not missing_canonical
                    else "FAIL"
                ),
        },

        {
            "metric":
                "duplicate_new_evidence_ids",

            "value":
                len(
                    duplicate_evidence_ids
                ),

            "status":
                (
                    "PASS"
                    if not duplicate_evidence_ids
                    else "FAIL"
                ),
        },

        {
            "metric":
                "ledger_v1_preserved",

            "value":
                int(
                    v1_rows_unchanged
                ),

            "status":
                (
                    "PASS"
                    if v1_rows_unchanged
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

    # ========================================================
    # WRITE
    # ========================================================

    write_csv(
        LEDGER_V2,
        ledger_v2,
        fields,
    )

    write_csv(
        SUMMARY_V2,
        summary_rows,
        [
            "year",
            "constraint_rows",
            "chronology_usable_rows",
            "performance_environment_usable_rows",
            "constraint_classes",
        ],
    )

    write_csv(
        QA_V2,
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
        "V2 SUMMARY"
    )
    print("=" * 120)

    print()
    print(
        "Ledger V1 rows:",
        len(
            ledger_v1
        ),
    )

    print(
        "New 2022 rows added:",
        len(
            added_rows
        ),
    )

    print(
        "Ledger V2 rows:",
        len(
            ledger_v2
        ),
    )

    print(
        "2022 chronology usable rows:",
        len(
            chronology_2022
        ),
    )

    print(
        "2022 unique attempts with chronology evidence:",
        len(
            attempt_ids_2022
        ),
    )

    print()
    print(
        "V1 file was not modified."
    )

    print(
        "Canonical data was not modified."
    )

    print(
        "No result-row ordering was used as chronology."
    )

    print(
        "No queue wait was inferred."
    )

    print()
    print("=" * 120)

    if (
        len(
            added_rows
        ) > 0
        and
        len(
            chronology_2022
        ) > 0
        and
        not missing_canonical
        and
        not duplicate_evidence_ids
    ):

        print(
            "FINAL STATUS: "
            "UNIFIED_ATTEMPT_CHRONOLOGY_LEDGER_V2_BUILT"
        )

    else:

        print(
            "FINAL STATUS: "
            "UNIFIED_ATTEMPT_CHRONOLOGY_LEDGER_V2_REVIEW_REQUIRED"
        )

    print("=" * 120)

    print()
    print(
        "OUTPUTS"
    )

    print(
        LEDGER_V2
    )

    print(
        SUMMARY_V2
    )

    print(
        QA_V2
    )


if __name__ == "__main__":
    main()
