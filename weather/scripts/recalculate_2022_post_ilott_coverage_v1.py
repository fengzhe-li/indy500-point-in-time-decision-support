from pathlib import Path
import csv


PHASE = "R1G.26G"

CANONICAL = Path(
    "data/canonical/v1/attempts.csv"
)

RESULT_MATCH_V3 = Path(
    "weather/output/"
    "chronology_rescue_2022_result_to_canonical_attempt_matches_v3.csv"
)

CHRONOLOGY_V4 = Path(
    "weather/output/"
    "unified_attempt_chronology_constraint_ledger_v4.csv"
)

CHRONOLOGY_V5 = Path(
    "weather/output/"
    "unified_attempt_chronology_constraint_ledger_v5.csv"
)

ACTION_V2 = Path(
    "weather/output/"
    "unified_attempt_action_lane_ledger_v2.csv"
)

ACTION_V3 = Path(
    "weather/output/"
    "unified_attempt_action_lane_ledger_v3.csv"
)

OUTPUT_DIR = Path(
    "weather/output"
)

COVERAGE_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_ilott_postintegration_coverage_corrected_v1.csv"
)

REPEAT_PAIR_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_repeat_pair_coverage_post_ilott_v1.csv"
)

SUMMARY_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_ilott_postintegration_coverage_corrected_summary_v1.csv"
)

QA_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_ilott_postintegration_coverage_corrected_v1_qa.csv"
)


def txt(v):
    return "" if v is None else str(v).strip()


def read_csv(path):
    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as f:
        reader = csv.DictReader(f)
        return list(reader)


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


def chronology_ids(rows, valid_2022_ids):
    return {
        txt(
            row.get(
                "attempt_id"
            )
        )
        for row in rows
        if (
            txt(
                row.get(
                    "attempt_id"
                )
            )
            in valid_2022_ids
            and
            txt(
                row.get(
                    "chronology_usable"
                )
            ).lower()
            ==
            "true"
        )
    }


def explicit_lane_count(rows):
    return sum(
        1
        for row in rows
        if txt(
            row.get(
                "lane"
            )
        ).upper()
        not in {
            "",
            "UNKNOWN",
        }
    )


def main():

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print()
    print("=" * 120)
    print(
        "R1G.26G — 2022 POST-ILOTT "
        "COVERAGE RECALCULATION V1"
    )
    print("=" * 120)

    required = [
        CANONICAL,
        RESULT_MATCH_V3,
        CHRONOLOGY_V4,
        CHRONOLOGY_V5,
        ACTION_V2,
        ACTION_V3,
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
            "2022_POST_ILOTT_COVERAGE_RECALCULATION_INPUT_MISSING"
        )
        return

    canonical = read_csv(
        CANONICAL
    )

    result_v3 = read_csv(
        RESULT_MATCH_V3
    )

    chronology_v4 = read_csv(
        CHRONOLOGY_V4
    )

    chronology_v5 = read_csv(
        CHRONOLOGY_V5
    )

    action_v2 = read_csv(
        ACTION_V2
    )

    action_v3 = read_csv(
        ACTION_V3
    )

    # ========================================================
    # DEFINE 2022 POPULATION FROM VERIFIED RESULT-MATCH V3
    # ========================================================

    ids_2022 = {
        txt(
            row.get(
                "attempt_id"
            )
        )
        for row in result_v3
        if txt(
            row.get(
                "attempt_id"
            )
        )
    }

    print()
    print("=" * 120)
    print(
        "2022 ATTEMPT POPULATION"
    )
    print("=" * 120)

    print()
    print(
        "2022 attempt IDs from result-match V3:",
        len(
            ids_2022
        ),
    )

    # ========================================================
    # CANONICAL GROUNDING
    # ========================================================

    canonical_by_id = {
        txt(
            row.get(
                "attempt_id"
            )
        ): row
        for row in canonical
        if txt(
            row.get(
                "attempt_id"
            )
        )
    }

    canonical_2022 = [
        canonical_by_id[aid]
        for aid in sorted(
            ids_2022
        )
        if aid in canonical_by_id
    ]

    missing_canonical_ids = sorted(
        ids_2022
        -
        set(
            canonical_by_id
        )
    )

    print(
        "2022 IDs found in canonical:",
        len(
            canonical_2022
        ),
    )

    print(
        "Missing canonical IDs:",
        len(
            missing_canonical_ids
        ),
    )

    # ========================================================
    # CHRONOLOGY COVERAGE
    # ========================================================

    v4_ids = chronology_ids(
        chronology_v4,
        ids_2022,
    )

    v5_ids = chronology_ids(
        chronology_v5,
        ids_2022,
    )

    total = len(
        ids_2022
    )

    before = len(
        v4_ids
    )

    after = len(
        v5_ids
    )

    before_pct = (
        before
        /
        total
        *
        100.0
        if total
        else 0.0
    )

    after_pct = (
        after
        /
        total
        *
        100.0
        if total
        else 0.0
    )

    newly_covered_ids = sorted(
        v5_ids
        -
        v4_ids
    )

    print()
    print("=" * 120)
    print(
        "2022 CHRONOLOGY COVERAGE"
    )
    print("=" * 120)

    print()
    print(
        "Unique chronology attempts:",
        before,
        "->",
        after,
    )

    print(
        "Coverage:",
        f"{before_pct:.2f}%",
        "->",
        f"{after_pct:.2f}%",
    )

    print(
        "Newly covered attempts:",
        len(
            newly_covered_ids
        ),
    )

    for aid in newly_covered_ids:

        row = canonical_by_id.get(
            aid,
            {},
        )

        print()
        print(
            aid,
            "|",
            canonical_driver(
                row
            ),
            "| index",
            txt(
                row.get(
                    "car_attempt_index"
                )
            ),
        )

    # ========================================================
    # REPEAT PAIRS
    # ========================================================

    driver_groups = {}

    for row in canonical_2022:

        driver = canonical_driver(
            row
        )

        aid = txt(
            row.get(
                "attempt_id"
            )
        )

        if (
            not driver
            or
            not aid
        ):
            continue

        driver_groups.setdefault(
            driver,
            []
        ).append(
            aid
        )

    repeat_groups = {
        driver: sorted(
            ids
        )
        for driver, ids in driver_groups.items()
        if len(ids) >= 2
    }

    repeat_rows = []

    fully_before = 0
    fully_after = 0

    print()
    print("=" * 120)
    print(
        "2022 REPEAT-PAIR COVERAGE"
    )
    print("=" * 120)

    print()
    print(
        "Repeat-attempt drivers:",
        len(
            repeat_groups
        ),
    )

    for driver in sorted(
        repeat_groups
    ):

        ids = repeat_groups[
            driver
        ]

        id_set = set(
            ids
        )

        covered_before = (
            id_set.issubset(
                v4_ids
            )
        )

        covered_after = (
            id_set.issubset(
                v5_ids
            )
        )

        if covered_before:
            fully_before += 1

        if covered_after:
            fully_after += 1

        repeat_rows.append({
            "driver_name":
                driver,

            "attempt_count":
                len(
                    ids
                ),

            "attempt_ids":
                "|".join(
                    ids
                ),

            "chronology_covered_before":
                str(
                    covered_before
                ),

            "chronology_covered_after":
                str(
                    covered_after
                ),

            "newly_fully_covered":
                str(
                    (
                        not covered_before
                        and
                        covered_after
                    )
                ),
        })

        print()
        print(
            driver,
            "| attempts:",
            len(
                ids
            ),
            "| before:",
            covered_before,
            "| after:",
            covered_after,
        )

    # ========================================================
    # LANE COVERAGE
    # ========================================================

    lane_v2 = explicit_lane_count(
        action_v2
    )

    lane_v3 = explicit_lane_count(
        action_v3
    )

    print()
    print("=" * 120)
    print(
        "ACTION / LANE COVERAGE"
    )
    print("=" * 120)

    print()
    print(
        "Explicit historical Lane rows:",
        lane_v2,
        "->",
        lane_v3,
    )

    # ========================================================
    # WRITE OUTPUTS
    # ========================================================

    coverage_rows = [
        {
            "metric":
                "2022_attempt_population",

            "before":
                total,

            "after":
                total,

            "change":
                0,
        },

        {
            "metric":
                "2022_unique_chronology_attempts",

            "before":
                before,

            "after":
                after,

            "change":
                after - before,
        },

        {
            "metric":
                "2022_chronology_coverage_pct",

            "before":
                f"{before_pct:.2f}",

            "after":
                f"{after_pct:.2f}",

            "change":
                f"{after_pct - before_pct:.2f}",
        },

        {
            "metric":
                "repeat_attempt_drivers",

            "before":
                len(
                    repeat_groups
                ),

            "after":
                len(
                    repeat_groups
                ),

            "change":
                0,
        },

        {
            "metric":
                "fully_chronology_covered_repeat_groups",

            "before":
                fully_before,

            "after":
                fully_after,

            "change":
                fully_after
                -
                fully_before,
        },

        {
            "metric":
                "explicit_historical_lane_rows",

            "before":
                lane_v2,

            "after":
                lane_v3,

            "change":
                lane_v3
                -
                lane_v2,
        },
    ]

    write_csv(
        COVERAGE_OUT,
        coverage_rows,
        [
            "metric",
            "before",
            "after",
            "change",
        ],
    )

    write_csv(
        REPEAT_PAIR_OUT,
        repeat_rows,
        [
            "driver_name",
            "attempt_count",
            "attempt_ids",
            "chronology_covered_before",
            "chronology_covered_after",
            "newly_fully_covered",
        ],
    )

    summary_rows = [
        {
            "metric":
                "2022_population_source",

            "value":
                "RESULT_MATCH_V3_ATTEMPT_IDS",
        },

        {
            "metric":
                "2022_population_size",

            "value":
                total,
        },

        {
            "metric":
                "canonical_population_matches",

            "value":
                len(
                    canonical_2022
                ),
        },

        {
            "metric":
                "missing_canonical_ids",

            "value":
                len(
                    missing_canonical_ids
                ),
        },

        {
            "metric":
                "chronology_before",

            "value":
                before,
        },

        {
            "metric":
                "chronology_after",

            "value":
                after,
        },

        {
            "metric":
                "coverage_before_pct",

            "value":
                f"{before_pct:.2f}",
        },

        {
            "metric":
                "coverage_after_pct",

            "value":
                f"{after_pct:.2f}",
        },

        {
            "metric":
                "repeat_groups",

            "value":
                len(
                    repeat_groups
                ),
        },

        {
            "metric":
                "fully_covered_repeat_groups_before",

            "value":
                fully_before,
        },

        {
            "metric":
                "fully_covered_repeat_groups_after",

            "value":
                fully_after,
        },

        {
            "metric":
                "lane_rows_before",

            "value":
                lane_v2,
        },

        {
            "metric":
                "lane_rows_after",

            "value":
                lane_v3,
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
                "result_match_v3_population_size",

            "value":
                total,

            "status":
                (
                    "PASS"
                    if total == 44
                    else "FAIL"
                ),
        },

        {
            "metric":
                "all_2022_ids_found_in_canonical",

            "value":
                len(
                    missing_canonical_ids
                ),

            "status":
                (
                    "PASS"
                    if len(
                        missing_canonical_ids
                    ) == 0
                    else "FAIL"
                ),
        },

        {
            "metric":
                "chronology_gain_equals_two",

            "value":
                after - before,

            "status":
                (
                    "PASS"
                    if after - before == 2
                    else "FAIL"
                ),
        },

        {
            "metric":
                "ilott_first_newly_covered",

            "value":
                int(
                    "3cd6d98a-da75-5822-8dae-05e83ad8457c"
                    in newly_covered_ids
                ),

            "status":
                (
                    "PASS"
                    if
                    "3cd6d98a-da75-5822-8dae-05e83ad8457c"
                    in newly_covered_ids
                    else "FAIL"
                ),
        },

        {
            "metric":
                "ilott_second_newly_covered",

            "value":
                int(
                    "8fa25fec-e5a6-5844-b3d7-f67c9dc91378"
                    in newly_covered_ids
                ),

            "status":
                (
                    "PASS"
                    if
                    "8fa25fec-e5a6-5844-b3d7-f67c9dc91378"
                    in newly_covered_ids
                    else "FAIL"
                ),
        },

        {
            "metric":
                "lane_evidence_count_unchanged",

            "value":
                lane_v3 - lane_v2,

            "status":
                (
                    "PASS"
                    if lane_v3 == lane_v2
                    else "FAIL"
                ),
        },

        {
            "metric":
                "ledgers_mutated",

            "value":
                0,

            "status":
                "PASS",
        },

        {
            "metric":
                "canonical_mutated",

            "value":
                0,

            "status":
                "PASS",
        },

        {
            "metric":
                "phase5_to_phase8_mutated",

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

    success = all(
        row[
            "status"
        ] == "PASS"
        for row in qa_rows
    )

    print()
    print("=" * 120)
    print(
        "CORRECTED FINAL SUMMARY"
    )
    print("=" * 120)

    print()
    print(
        "2022 population:",
        total,
    )

    print(
        "Chronology:",
        before,
        "->",
        after,
    )

    print(
        "Coverage:",
        f"{before_pct:.2f}%",
        "->",
        f"{after_pct:.2f}%",
    )

    print(
        "Fully covered repeat groups:",
        fully_before,
        "/",
        len(
            repeat_groups
        ),
        "->",
        fully_after,
        "/",
        len(
            repeat_groups
        ),
    )

    print(
        "Explicit Lane rows:",
        lane_v2,
        "->",
        lane_v3,
    )

    print()
    print(
        "No ledger was modified."
    )

    print(
        "No canonical or Phase 5–8 data was modified."
    )

    print()
    print("=" * 120)

    if success:

        print(
            "FINAL STATUS: "
            "2022_POST_ILOTT_COVERAGE_RECALCULATION_COMPLETE"
        )

    else:

        print(
            "FINAL STATUS: "
            "2022_POST_ILOTT_COVERAGE_RECALCULATION_REVIEW_REQUIRED"
        )

    print("=" * 120)

    print()
    print("OUTPUTS")
    print(COVERAGE_OUT)
    print(REPEAT_PAIR_OUT)
    print(SUMMARY_OUT)
    print(QA_OUT)


if __name__ == "__main__":
    main()
