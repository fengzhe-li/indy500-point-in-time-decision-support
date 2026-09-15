from pathlib import Path
import csv
import json

ROOT = Path(
    "/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈"
)

OUT = ROOT / "r4/output"
OUT.mkdir(parents=True, exist_ok=True)

OUT_REGISTRY = (
    OUT /
    "r4lc1_last_chance_year_registry_v1.csv"
)

OUT_QA = (
    OUT /
    "r4lc1_last_chance_year_registry_qa_v1.csv"
)

OUT_REPORT = (
    OUT /
    "r4lc1_last_chance_year_registry_report_v1.json"
)


rows = [
    {
        "year": 2020,
        "session_regime": "NONE",
        "last_chance_held": False,
        "session_name": "",
        "entry_count": 33,
        "reason": (
            "Exactly 33 entries; no Last Chance/Last Row session required."
        ),
        "model_role": "DAY1_ONLY",
        "official_source_status": "VERIFIED",
    },
    {
        "year": 2021,
        "session_regime": "LAST_ROW",
        "last_chance_held": True,
        "session_name": "Qualifications - Last Row",
        "entry_count": 35,
        "reason": (
            "More than 33 entries; Last Row qualifying was held."
        ),
        "model_role": "LAST_CHANCE_TRAINING_CANDIDATE",
        "official_source_status": "VERIFIED",
    },
    {
        "year": 2022,
        "session_regime": "NONE",
        "last_chance_held": False,
        "session_name": "",
        "entry_count": 33,
        "reason": (
            "Exactly 33 entries; scheduled Last Chance was not required."
        ),
        "model_role": "DAY1_DEGRADED_VALIDATION_CANDIDATE",
        "official_source_status": "VERIFIED",
    },
    {
        "year": 2023,
        "session_regime": "LAST_CHANCE",
        "last_chance_held": True,
        "session_name": "Qualifications - Last Chance",
        "entry_count": 34,
        "reason": (
            "More than 33 entries; Last Chance qualifying was held."
        ),
        "model_role": "LAST_CHANCE_TRAINING_CANDIDATE",
        "official_source_status": "VERIFIED",
    },
    {
        "year": 2024,
        "session_regime": "LAST_CHANCE",
        "last_chance_held": True,
        "session_name": "Qualifications - Last Chance",
        "entry_count": 34,
        "reason": (
            "More than 33 entries; Last Chance qualifying was held."
        ),
        "model_role": (
            "LAST_CHANCE_TRAINING_OR_"
            "SPARSE_TIMING_VALIDATION_CANDIDATE"
        ),
        "official_source_status": "VERIFIED",
    },
    {
        "year": 2025,
        "session_regime": "LAST_CHANCE",
        "last_chance_held": True,
        "session_name": "Qualifications - Last Chance",
        "entry_count": 34,
        "reason": (
            "More than 33 entries; Last Chance qualifying was held."
        ),
        "model_role": "CROSS_TECHNICAL_REGIME_VALIDATION_CANDIDATE",
        "official_source_status": "VERIFIED",
    },
]


fields = [
    "year",
    "session_regime",
    "last_chance_held",
    "session_name",
    "entry_count",
    "reason",
    "model_role",
    "official_source_status",
]


with OUT_REGISTRY.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=fields
    )

    writer.writeheader()
    writer.writerows(rows)


held_years = [
    r["year"]
    for r in rows
    if r["last_chance_held"]
]

not_held_years = [
    r["year"]
    for r in rows
    if not r["last_chance_held"]
]


qa_rows = [
    {
        "metric": "years_registered",
        "value": len(rows),
        "expected": 6,
        "status": (
            "PASS"
            if len(rows) == 6
            else "FAIL"
        ),
    },
    {
        "metric": "last_chance_held_years",
        "value": ";".join(
            str(y)
            for y in held_years
        ),
        "expected": "2021;2023;2024;2025",
        "status": (
            "PASS"
            if held_years == [
                2021,
                2023,
                2024,
                2025,
            ]
            else "FAIL"
        ),
    },
    {
        "metric": "no_last_chance_years",
        "value": ";".join(
            str(y)
            for y in not_held_years
        ),
        "expected": "2020;2022",
        "status": (
            "PASS"
            if not_held_years == [
                2020,
                2022,
            ]
            else "FAIL"
        ),
    },
    {
        "metric": "all_years_verified",
        "value": all(
            r["official_source_status"] == "VERIFIED"
            for r in rows
        ),
        "expected": True,
        "status": (
            "PASS"
            if all(
                r["official_source_status"] == "VERIFIED"
                for r in rows
            )
            else "FAIL"
        ),
    },
]


with OUT_QA.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=[
            "metric",
            "value",
            "expected",
            "status",
        ]
    )

    writer.writeheader()
    writer.writerows(qa_rows)


report = {
    "phase": "R4LC1",
    "status": (
        "R4LC1_LAST_CHANCE_YEAR_ELIGIBILITY_REGISTRY_READY"
    ),
    "years": {
        "last_chance_or_last_row_held":
            held_years,
        "not_held":
            not_held_years,
    },
    "research_implication": (
        "Last-Chance-only model must not treat 2020 or 2022 "
        "as Last Chance sessions. Core historical Last Chance "
        "domain is 2021, 2023, 2024, with 2025 reserved or "
        "used separately depending cross-regime validation policy."
    ),
}

OUT_REPORT.write_text(
    json.dumps(
        report,
        indent=2,
        ensure_ascii=False
    ),
    encoding="utf-8"
)


print("=" * 108)
print("R4LC1 — LAST CHANCE YEAR ELIGIBILITY REGISTRY")
print("=" * 108)

for r in rows:

    print(
        f"{r['year']} | "
        f"held={str(r['last_chance_held']):5s} | "
        f"regime={r['session_regime']:12s} | "
        f"entries={r['entry_count']} | "
        f"role={r['model_role']}"
    )


failed = [
    r
    for r in qa_rows
    if r["status"] != "PASS"
]

print()
print(
    f"QA: "
    f"{len(qa_rows)-len(failed)}/"
    f"{len(qa_rows)} PASS"
)

if failed:

    print("FAILED QA")

    for r in failed:
        print(
            f"{r['metric']} | "
            f"value={r['value']} | "
            f"expected={r['expected']}"
        )

    raise SystemExit(1)


print()
print("OUTPUTS")
print(OUT_REGISTRY.relative_to(ROOT))
print(OUT_QA.relative_to(ROOT))
print(OUT_REPORT.relative_to(ROOT))

print()
print(
    "R4LC1_LAST_CHANCE_YEAR_ELIGIBILITY_REGISTRY_READY"
)
