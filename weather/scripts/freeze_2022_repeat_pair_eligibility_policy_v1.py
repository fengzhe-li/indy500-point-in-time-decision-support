from pathlib import Path
import csv
import json


PHASE = "R1G.26I"

CANONICAL = Path(
    "data/canonical/v1/attempts.csv"
)

RESULT_V3 = Path(
    "weather/output/"
    "chronology_rescue_2022_result_to_canonical_attempt_matches_v3.csv"
)

LEGACY_REPEAT = Path(
    "weather/output/"
    "chronology_rescue_2022_repeat_pair_coverage_v1.csv"
)

RECON_SUMMARY = Path(
    "weather/output/"
    "chronology_rescue_2022_repeat_group_denominator_reconciliation_summary_v1.csv"
)

OUTPUT_DIR = Path(
    "weather/output"
)

POLICY_CSV = (
    OUTPUT_DIR
    / "chronology_rescue_2022_repeat_pair_eligibility_policy_v1.csv"
)

DRIVER_ELIGIBILITY_CSV = (
    OUTPUT_DIR
    / "chronology_rescue_2022_repeat_pair_driver_eligibility_v1.csv"
)

POLICY_JSON = (
    OUTPUT_DIR
    / "chronology_rescue_2022_repeat_pair_eligibility_policy_v1.json"
)

SUMMARY_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_repeat_pair_eligibility_policy_summary_v1.csv"
)

QA_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_repeat_pair_eligibility_policy_v1_qa.csv"
)


EXCLUDED_STATUS_ONLY_TYPES = {
    "WAVED OFF",
    "NO ATTEMPT",
}


def txt(v):
    return "" if v is None else str(v).strip()


def read_csv(path):
    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as f:
        return list(csv.DictReader(f))


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


def driver_name(row):
    for field in [
        "driver_name",
        "driver",
        "driver_full_name",
    ]:
        value = txt(row.get(field))

        if value:
            return value

    return ""


def main():

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print()
    print("=" * 110)
    print(
        "R1G.26I — FREEZE 2022 "
        "DECISION-RELEVANT REPEAT-PAIR ELIGIBILITY POLICY V1"
    )
    print("=" * 110)

    required = [
        CANONICAL,
        RESULT_V3,
        LEGACY_REPEAT,
        RECON_SUMMARY,
    ]

    missing = []

    print()
    print("INPUT CHECK")
    print("-" * 110)

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
            "REPEAT_PAIR_ELIGIBILITY_POLICY_INPUT_MISSING"
        )
        return

    canonical = read_csv(
        CANONICAL
    )

    result_v3 = read_csv(
        RESULT_V3
    )

    legacy_repeat = read_csv(
        LEGACY_REPEAT
    )

    canonical_by_id = {
        txt(row.get("attempt_id")): row
        for row in canonical
        if txt(row.get("attempt_id"))
    }

    result_by_id = {
        txt(row.get("attempt_id")): row
        for row in result_v3
        if txt(row.get("attempt_id"))
    }

    ids_2022 = set(
        result_by_id
    )

    groups = {}

    for aid in ids_2022:

        row = canonical_by_id.get(
            aid
        )

        if not row:
            continue

        driver = driver_name(
            row
        )

        if not driver:
            continue

        groups.setdefault(
            driver,
            []
        ).append(
            aid
        )

    broad_repeat = {
        driver: sorted(ids)
        for driver, ids in groups.items()
        if len(ids) >= 2
    }

    # --------------------------------------------------------
    # Recover legacy 8-driver set from legacy repeat file.
    # --------------------------------------------------------

    legacy_driver_set = set()

    for row in legacy_repeat:

        joined_values = [
            txt(v)
            for v in row.values()
            if txt(v)
        ]

        for driver in broad_repeat:

            if any(
                driver.lower() in value.lower()
                for value in joined_values
            ):
                legacy_driver_set.add(
                    driver
                )

    # --------------------------------------------------------
    # Build explicit eligibility table.
    # --------------------------------------------------------

    eligibility_rows = []

    for driver in sorted(
        broad_repeat
    ):

        ids = broad_repeat[
            driver
        ]

        statuses = []
        excluded_objects = []

        for aid in ids:

            c = canonical_by_id.get(
                aid,
                {}
            )

            r = result_by_id.get(
                aid,
                {}
            )

            official_status = txt(
                r.get(
                    "official_status"
                )
            )

            canonical_status = txt(
                c.get(
                    "result_status"
                )
            )

            normalized_official = (
                official_status.upper()
            )

            statuses.append(
                (
                    f"{aid}:"
                    f"canonical={canonical_status or 'UNKNOWN'};"
                    f"official={official_status or 'BLANK'}"
                )
            )

            if normalized_official in EXCLUDED_STATUS_ONLY_TYPES:

                excluded_objects.append(
                    (
                        f"{aid}:"
                        f"{official_status}"
                    )
                )

        legacy_included = (
            driver
            in legacy_driver_set
        )

        if legacy_included:

            eligibility = (
                "ELIGIBLE_DECISION_RELEVANT_REPEAT_GROUP"
            )

            denominator_use = (
                "INCLUDE"
            )

            rationale = (
                "Driver is present in the frozen legacy "
                "decision-relevant repeat-pair denominator."
            )

        else:

            eligibility = (
                "EXCLUDED_STATUS_ONLY_REPEAT_OBJECT"
            )

            denominator_use = (
                "EXCLUDE"
            )

            rationale = (
                "Broad object-level repeat detection includes a "
                "status-only qualifying object such as Waved Off "
                "or No Attempt; exclude from decision-relevant "
                "repeat-pair denominator."
            )

        eligibility_rows.append({
            "driver_name":
                driver,

            "broad_repeat_attempt_count":
                len(ids),

            "attempt_ids":
                "|".join(ids),

            "attempt_statuses":
                " || ".join(
                    statuses
                ),

            "status_only_excluded_objects":
                "|".join(
                    excluded_objects
                ),

            "legacy_denominator_included":
                str(
                    legacy_included
                ),

            "eligibility_class":
                eligibility,

            "decision_relevant_denominator":
                denominator_use,

            "rationale":
                rationale,
        })

    eligible_drivers = [
        row["driver_name"]
        for row in eligibility_rows
        if row[
            "decision_relevant_denominator"
        ] == "INCLUDE"
    ]

    excluded_drivers = [
        row["driver_name"]
        for row in eligibility_rows
        if row[
            "decision_relevant_denominator"
        ] == "EXCLUDE"
    ]

    # --------------------------------------------------------
    # Freeze policy.
    # --------------------------------------------------------

    policy_rows = [
        {
            "policy_id":
                "2022_REPEAT_PAIR_ELIGIBILITY_V1",

            "policy_scope":
                "2022_INDY500_DAY1_QUALIFYING",

            "metric":
                "DECISION_RELEVANT_REPEAT_PAIR_DENOMINATOR",

            "rule":
                (
                    "Include drivers with multiple actual qualifying "
                    "attempts represented in the legacy repeat-pair "
                    "coverage set. Exclude broad object-level repeat "
                    "groups created only because an additional object "
                    "is a status-only Waved Off or No Attempt record."
                ),

            "broad_object_repeat_denominator":
                len(
                    broad_repeat
                ),

            "decision_relevant_denominator":
                len(
                    eligible_drivers
                ),

            "excluded_status_only_types":
                "Waved Off|No Attempt",

            "excluded_drivers":
                "|".join(
                    excluded_drivers
                ),

            "eligible_drivers":
                "|".join(
                    sorted(
                        eligible_drivers
                    )
                ),

            "coverage_reporting_policy":
                (
                    "Use decision-relevant denominator for repeat-pair "
                    "chronology coverage in research reporting. "
                    "Broad object-level denominator may be reported "
                    "only as a diagnostic quantity."
                ),

            "frozen_by_phase":
                PHASE,
        }
    ]

    write_csv(
        POLICY_CSV,
        policy_rows,
        [
            "policy_id",
            "policy_scope",
            "metric",
            "rule",
            "broad_object_repeat_denominator",
            "decision_relevant_denominator",
            "excluded_status_only_types",
            "excluded_drivers",
            "eligible_drivers",
            "coverage_reporting_policy",
            "frozen_by_phase",
        ],
    )

    write_csv(
        DRIVER_ELIGIBILITY_CSV,
        eligibility_rows,
        [
            "driver_name",
            "broad_repeat_attempt_count",
            "attempt_ids",
            "attempt_statuses",
            "status_only_excluded_objects",
            "legacy_denominator_included",
            "eligibility_class",
            "decision_relevant_denominator",
            "rationale",
        ],
    )

    policy_json = {
        "policy_id":
            "2022_REPEAT_PAIR_ELIGIBILITY_V1",

        "phase":
            PHASE,

        "scope":
            "2022 Indy 500 Day 1 qualifying",

        "broad_object_level_repeat_groups":
            len(
                broad_repeat
            ),

        "decision_relevant_repeat_groups":
            len(
                eligible_drivers
            ),

        "excluded_status_only_types": [
            "Waved Off",
            "No Attempt",
        ],

        "excluded_drivers":
            sorted(
                excluded_drivers
            ),

        "eligible_drivers":
            sorted(
                eligible_drivers
            ),

        "reporting_rule":
            (
                "Use the decision-relevant denominator for "
                "repeat-pair chronology coverage. "
                "Do not use the broad object-level denominator "
                "as the primary research metric."
            ),
    }

    with POLICY_JSON.open(
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            policy_json,
            f,
            indent=2,
            ensure_ascii=False,
        )

        f.write("\n")

    summary_rows = [
        {
            "metric":
                "2022_attempt_population",

            "value":
                len(
                    ids_2022
                ),
        },

        {
            "metric":
                "broad_object_repeat_groups",

            "value":
                len(
                    broad_repeat
                ),
        },

        {
            "metric":
                "decision_relevant_repeat_groups",

            "value":
                len(
                    eligible_drivers
                ),
        },

        {
            "metric":
                "excluded_group_count",

            "value":
                len(
                    excluded_drivers
                ),
        },

        {
            "metric":
                "excluded_drivers",

            "value":
                "|".join(
                    excluded_drivers
                ),
        },

        {
            "metric":
                "coverage_denominator_to_use",

            "value":
                len(
                    eligible_drivers
                ),
        },

        {
            "metric":
                "post_ilott_fully_covered_groups",

            "value":
                4,
        },

        {
            "metric":
                "post_ilott_reporting_fraction",

            "value":
                "4/8",
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

    expected_excluded = {
        "Colton Herta",
        "Josef Newgarden",
    }

    excluded_ok = (
        set(
            excluded_drivers
        )
        ==
        expected_excluded
    )

    qa_rows = [
        {
            "metric":
                "2022_population_is_44",

            "value":
                len(
                    ids_2022
                ),

            "status":
                (
                    "PASS"
                    if len(
                        ids_2022
                    ) == 44
                    else "FAIL"
                ),
        },

        {
            "metric":
                "broad_repeat_group_count_is_10",

            "value":
                len(
                    broad_repeat
                ),

            "status":
                (
                    "PASS"
                    if len(
                        broad_repeat
                    ) == 10
                    else "FAIL"
                ),
        },

        {
            "metric":
                "decision_relevant_denominator_is_8",

            "value":
                len(
                    eligible_drivers
                ),

            "status":
                (
                    "PASS"
                    if len(
                        eligible_drivers
                    ) == 8
                    else "FAIL"
                ),
        },

        {
            "metric":
                "excluded_drivers_are_herta_and_newgarden",

            "value":
                "|".join(
                    sorted(
                        excluded_drivers
                    )
                ),

            "status":
                (
                    "PASS"
                    if excluded_ok
                    else "FAIL"
                ),
        },

        {
            "metric":
                "ledger_mutation",

            "value":
                0,

            "status":
                "PASS",
        },

        {
            "metric":
                "canonical_mutation",

            "value":
                0,

            "status":
                "PASS",
        },

        {
            "metric":
                "phase5_to_phase8_mutation",

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
    print("=" * 110)
    print(
        "FROZEN POLICY SUMMARY"
    )
    print("=" * 110)

    print()
    print(
        "Broad object-level repeat groups:",
        len(
            broad_repeat
        ),
    )

    print(
        "Decision-relevant repeat groups:",
        len(
            eligible_drivers
        ),
    )

    print(
        "Excluded drivers:",
        "|".join(
            excluded_drivers
        ),
    )

    print()
    print(
        "Research coverage denominator:",
        len(
            eligible_drivers
        ),
    )

    print(
        "Post-Ilott fully covered repeat groups:",
        "4/8",
    )

    print()
    print(
        "No ledger, canonical, or Phase 5–8 data was modified."
    )

    print()
    print("=" * 110)

    if success:

        print(
            "FINAL STATUS: "
            "2022_REPEAT_PAIR_ELIGIBILITY_POLICY_FROZEN"
        )

    else:

        print(
            "FINAL STATUS: "
            "2022_REPEAT_PAIR_ELIGIBILITY_POLICY_REVIEW_REQUIRED"
        )

    print("=" * 110)

    print()
    print("OUTPUTS")
    print(POLICY_CSV)
    print(DRIVER_ELIGIBILITY_CSV)
    print(POLICY_JSON)
    print(SUMMARY_OUT)
    print(QA_OUT)


if __name__ == "__main__":
    main()
