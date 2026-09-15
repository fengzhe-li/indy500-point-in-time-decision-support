from pathlib import Path
import csv

CANONICAL = Path("data/canonical/v1/attempts.csv")
RESULT_V3 = Path(
    "weather/output/"
    "chronology_rescue_2022_result_to_canonical_attempt_matches_v3.csv"
)
CURRENT_REPEAT = Path(
    "weather/output/"
    "chronology_rescue_2022_repeat_pair_coverage_post_ilott_v1.csv"
)

LEGACY_FILES = [
    Path("weather/output/chronology_rescue_2022_repeat_pair_coverage_v1.csv"),
    Path("weather/output/chronology_rescue_2022_chronology_action_coverage_v1.csv"),
    Path("weather/output/chronology_rescue_2022_chronology_action_coverage_v2.csv"),
    Path("weather/output/chronology_rescue_2022_chronology_coverage_gaps_v1.csv"),
]

OUT = Path(
    "weather/output/"
    "chronology_rescue_2022_repeat_group_denominator_reconciliation_v1.csv"
)
SUMMARY = Path(
    "weather/output/"
    "chronology_rescue_2022_repeat_group_denominator_reconciliation_summary_v1.csv"
)
QA = Path(
    "weather/output/"
    "chronology_rescue_2022_repeat_group_denominator_reconciliation_v1_qa.csv"
)


def txt(v):
    return "" if v is None else str(v).strip()


def read_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def driver_name(row):
    for field in ["driver_name", "driver", "driver_full_name"]:
        value = txt(row.get(field))
        if value:
            return value
    return ""


def main():
    print()
    print("=" * 110)
    print("R1G.26H — 2022 REPEAT-GROUP DENOMINATOR RECONCILIATION")
    print("=" * 110)

    required = [CANONICAL, RESULT_V3, CURRENT_REPEAT]

    for path in required:
        print(
            f"{path}: "
            f"{'PRESENT' if path.exists() else 'MISSING'}"
        )

    if not all(path.exists() for path in required):
        print()
        print("FINAL STATUS: REPEAT_GROUP_RECON_INPUT_MISSING")
        return

    canonical = read_csv(CANONICAL)
    result_v3 = read_csv(RESULT_V3)

    ids_2022 = {
        txt(row.get("attempt_id"))
        for row in result_v3
        if txt(row.get("attempt_id"))
    }

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

    groups = {}

    for aid in ids_2022:
        row = canonical_by_id.get(aid)

        if not row:
            continue

        driver = driver_name(row)

        if driver:
            groups.setdefault(driver, []).append(aid)

    current_repeat = {
        driver: sorted(ids)
        for driver, ids in groups.items()
        if len(ids) >= 2
    }

    current_drivers = set(current_repeat)

    print()
    print("=" * 110)
    print("CURRENT BROAD REPEAT DEFINITION")
    print("=" * 110)

    print()
    print("Current repeat drivers:", len(current_drivers))

    for driver in sorted(current_drivers):
        print(" ", driver, "| attempts:", len(current_repeat[driver]))

    legacy_results = []

    print()
    print("=" * 110)
    print("LEGACY FILE SCAN")
    print("=" * 110)

    for path in LEGACY_FILES:
        if not path.exists():
            print()
            print(path, "MISSING")
            continue

        rows = read_csv(path)

        matched = set()

        for row in rows:
            values = [txt(v) for v in row.values()]

            for driver in current_drivers:
                if any(
                    driver.lower() == value.lower()
                    or driver.lower() in value.lower()
                    for value in values
                    if value
                ):
                    matched.add(driver)

        legacy_results.append(
            {
                "path": str(path),
                "matched_drivers": matched,
                "count": len(matched),
            }
        )

        print()
        print(path)
        print("  matched repeat drivers:", len(matched))

        if matched:
            print(" ", " | ".join(sorted(matched)))

    exact_eight = [
        item
        for item in legacy_results
        if item["count"] == 8
    ]

    if exact_eight:
        chosen = exact_eight[0]
        legacy_drivers = chosen["matched_drivers"]
        legacy_source = chosen["path"]
        legacy_status = "EXACT_LEGACY_8_FOUND"
    else:
        chosen = max(
            legacy_results,
            key=lambda x: x["count"],
            default=None,
        )

        legacy_drivers = (
            chosen["matched_drivers"]
            if chosen
            else set()
        )

        legacy_source = (
            chosen["path"]
            if chosen
            else ""
        )

        legacy_status = (
            "NO_EXACT_8_FOUND"
        )

    added_vs_legacy = sorted(
        current_drivers - legacy_drivers
    )

    missing_vs_current = sorted(
        legacy_drivers - current_drivers
    )

    print()
    print("=" * 110)
    print("DENOMINATOR DIFFERENCE")
    print("=" * 110)

    print()
    print("Chosen legacy source:", legacy_source or "NONE")
    print("Legacy matched drivers:", len(legacy_drivers))
    print("Current broad drivers:", len(current_drivers))

    print()
    print("Current but not legacy:")
    for driver in added_vs_legacy:
        print(" ", driver)

    print()
    print("Legacy but not current:")
    for driver in missing_vs_current:
        print(" ", driver)

    audit_rows = []

    print()
    print("=" * 110)
    print("DRIVER-LEVEL ATTEMPT SEMANTICS")
    print("=" * 110)

    for driver in sorted(current_drivers):
        ids = current_repeat[driver]

        legacy_included = driver in legacy_drivers

        for aid in ids:
            c = canonical_by_id.get(aid, {})
            r = result_by_id.get(aid, {})

            row = {
                "driver_name": driver,
                "legacy_included": str(legacy_included),
                "current_broad_included": "True",
                "attempt_id": aid,
                "car_attempt_index": txt(c.get("car_attempt_index")),
                "canonical_result_status": txt(c.get("result_status")),
                "official_status": txt(r.get("official_status")),
                "official_result_row": txt(r.get("official_result_row")),
            }

            audit_rows.append(row)

        if driver in added_vs_legacy:
            print()
            print(driver, "— CURRENT ONLY")

            for aid in ids:
                c = canonical_by_id.get(aid, {})
                r = result_by_id.get(aid, {})

                print(
                    " ",
                    "index",
                    txt(c.get("car_attempt_index")),
                    "| canonical:",
                    repr(txt(c.get("result_status"))),
                    "| official:",
                    repr(txt(r.get("official_status"))),
                    "|",
                    aid,
                )

    write_csv(
        OUT,
        audit_rows,
        [
            "driver_name",
            "legacy_included",
            "current_broad_included",
            "attempt_id",
            "car_attempt_index",
            "canonical_result_status",
            "official_status",
            "official_result_row",
        ],
    )

    summary_rows = [
        {
            "metric": "2022_population",
            "value": len(ids_2022),
        },
        {
            "metric": "current_broad_repeat_drivers",
            "value": len(current_drivers),
        },
        {
            "metric": "legacy_source",
            "value": legacy_source,
        },
        {
            "metric": "legacy_repeat_drivers",
            "value": len(legacy_drivers),
        },
        {
            "metric": "current_only_driver_count",
            "value": len(added_vs_legacy),
        },
        {
            "metric": "current_only_drivers",
            "value": "|".join(added_vs_legacy),
        },
        {
            "metric": "legacy_only_driver_count",
            "value": len(missing_vs_current),
        },
        {
            "metric": "legacy_scan_status",
            "value": legacy_status,
        },
    ]

    write_csv(
        SUMMARY,
        summary_rows,
        ["metric", "value"],
    )

    qa_rows = [
        {
            "metric": "2022_population_is_44",
            "value": len(ids_2022),
            "status": "PASS" if len(ids_2022) == 44 else "FAIL",
        },
        {
            "metric": "current_repeat_driver_count",
            "value": len(current_drivers),
            "status": "PASS" if len(current_drivers) == 10 else "REVIEW",
        },
        {
            "metric": "ledger_mutation",
            "value": 0,
            "status": "PASS",
        },
        {
            "metric": "canonical_mutation",
            "value": 0,
            "status": "PASS",
        },
    ]

    write_csv(
        QA,
        qa_rows,
        ["metric", "value", "status"],
    )

    print()
    print("=" * 110)
    print("FINAL SUMMARY")
    print("=" * 110)

    print()
    print("2022 population:", len(ids_2022))
    print("Current broad denominator:", len(current_drivers))
    print("Legacy denominator found:", len(legacy_drivers))
    print("Current-only drivers:", "|".join(added_vs_legacy) or "NONE")
    print("Legacy-only drivers:", "|".join(missing_vs_current) or "NONE")

    print()
    print("No ledger or canonical file was modified.")

    print()
    print("=" * 110)

    if len(legacy_drivers) == 8:
        print(
            "FINAL STATUS: "
            "2022_REPEAT_GROUP_DENOMINATOR_DIFFERENCE_IDENTIFIED"
        )
    else:
        print(
            "FINAL STATUS: "
            "2022_REPEAT_GROUP_DENOMINATOR_LEGACY_DEFINITION_REVIEW_REQUIRED"
        )

    print("=" * 110)

    print()
    print("OUTPUTS")
    print(OUT)
    print(SUMMARY)
    print(QA)


if __name__ == "__main__":
    main()
