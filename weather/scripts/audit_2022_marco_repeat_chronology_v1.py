from pathlib import Path
import csv
import re


CANONICAL = Path("data/canonical/v1/attempts.csv")

RESULT_V3 = Path(
    "weather/output/"
    "chronology_rescue_2022_result_to_canonical_attempt_matches_v3.csv"
)

CHRONOLOGY_V6 = Path(
    "weather/output/"
    "unified_attempt_chronology_constraint_ledger_v6.csv"
)

ACTION_V4 = Path(
    "weather/output/"
    "unified_attempt_action_lane_ledger_v4.csv"
)

EVIDENCE_ROOTS = [
    Path("weather/evidence/rescue"),
    Path("weather/output"),
]

OUT = Path(
    "weather/output/"
    "chronology_rescue_2022_marco_repeat_chronology_audit_v1.csv"
)

HITS_OUT = Path(
    "weather/output/"
    "chronology_rescue_2022_marco_repeat_evidence_hits_v1.csv"
)

QA_OUT = Path(
    "weather/output/"
    "chronology_rescue_2022_marco_repeat_chronology_audit_v1_qa.csv"
)


def txt(v):
    return "" if v is None else str(v).strip()


def read_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path, rows, fields):
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def first(row, names):
    for name in names:
        value = txt(row.get(name))
        if value:
            return value
    return ""


def driver(row):
    return first(row, ["driver_name", "driver", "driver_full_name"])


def speed(row):
    return first(
        row,
        [
            "four_lap_average_speed_mph",
            "average_speed_mph",
            "speed_mph",
        ],
    )


def attempt_index(row):
    return first(row, ["car_attempt_index", "attempt_index"])


def official_status(row):
    return first(row, ["official_status", "status"])


def norm(s):
    return re.sub(r"\s+", " ", txt(s)).strip()


def read_text(path):
    try:
        return path.read_text(
            encoding="utf-8",
            errors="replace",
        )
    except Exception:
        return ""


def split_units(raw):
    raw = re.sub(r"(?is)<[^>]+>", " ", raw)
    raw = re.sub(r"\s+", " ", raw)

    parts = re.split(
        r"(?<=[.!?])\s+",
        raw,
    )

    return [
        norm(p)
        for p in parts
        if norm(p)
    ]


def row_mentions(row, ids):
    values = {
        txt(row.get("attempt_id")),
        txt(row.get("subject_attempt_id")),
        txt(row.get("related_attempt_id")),
    }
    return bool(values & ids)


def main():
    print()
    print("=" * 115)
    print("R1G.28A — 2022 MARCO ANDRETTI REPEAT-ATTEMPT CHRONOLOGY AUDIT")
    print("=" * 115)

    required = [
        CANONICAL,
        RESULT_V3,
        CHRONOLOGY_V6,
        ACTION_V4,
    ]

    for path in required:
        print(
            f"{path}: "
            f"{'PRESENT' if path.exists() else 'MISSING'}"
        )

    if not all(p.exists() for p in required):
        print()
        print("FINAL STATUS: MARCO_REPEAT_AUDIT_INPUT_MISSING")
        return

    canonical = read_csv(CANONICAL)
    result_v3 = read_csv(RESULT_V3)
    chronology = read_csv(CHRONOLOGY_V6)
    action = read_csv(ACTION_V4)

    result_ids_2022 = {
        txt(r.get("attempt_id"))
        for r in result_v3
        if txt(r.get("attempt_id"))
    }

    canonical_by_id = {
        txt(r.get("attempt_id")): r
        for r in canonical
        if txt(r.get("attempt_id"))
    }

    result_by_id = {
        txt(r.get("attempt_id")): r
        for r in result_v3
        if txt(r.get("attempt_id"))
    }

    marco_ids = []

    for aid in result_ids_2022:
        row = canonical_by_id.get(aid, {})
        if driver(row) == "Marco Andretti":
            marco_ids.append(aid)

    marco_ids = sorted(
        marco_ids,
        key=lambda aid: (
            attempt_index(canonical_by_id.get(aid, {})) or "99",
            aid,
        ),
    )

    marco_set = set(marco_ids)

    print()
    print("=" * 115)
    print("CANONICAL MARCO ATTEMPTS")
    print("=" * 115)

    audit_rows = []

    for aid in marco_ids:
        c = canonical_by_id.get(aid, {})
        r = result_by_id.get(aid, {})

        item = {
            "attempt_id": aid,
            "driver_name": driver(c),
            "car_number": first(c, ["car_number", "car_no", "car"]),
            "car_attempt_index": attempt_index(c),
            "speed_mph": speed(c),
            "canonical_status": first(c, ["result_status", "status"]),
            "official_status": official_status(r),
        }

        audit_rows.append(item)

        print()
        print(
            aid,
            "| index",
            repr(item["car_attempt_index"]),
            "| speed",
            repr(item["speed_mph"]),
            "| canonical",
            repr(item["canonical_status"]),
            "| official",
            repr(item["official_status"]),
        )

    chrono_hits = [
        row
        for row in chronology
        if row_mentions(row, marco_set)
        or txt(row.get("driver_name")) == "Marco Andretti"
    ]

    action_hits = [
        row
        for row in action
        if row_mentions(row, marco_set)
        or txt(row.get("driver_name")) == "Marco Andretti"
    ]

    print()
    print("=" * 115)
    print("EXISTING ACTIVE LEDGER STATE")
    print("=" * 115)

    print()
    print("Chronology V6 Marco hits:", len(chrono_hits))

    for i, row in enumerate(chrono_hits, start=1):
        print()
        print(f"CHRONOLOGY ROW {i}")
        print(" attempt_id:", repr(txt(row.get("attempt_id"))))
        print(" relation:", repr(txt(row.get("ordering_relation"))))
        print(" related_attempt_id:", repr(txt(row.get("related_attempt_id"))))
        print(" chronology_usable:", repr(txt(row.get("chronology_usable"))))
        print(" action:", repr(txt(row.get("action"))))
        print(" lane:", repr(txt(row.get("lane"))))
        print(" evidence_id:", repr(txt(row.get("evidence_id"))))
        print(" source_title:", repr(txt(row.get("source_title"))))
        print(" evidence_summary:", repr(txt(row.get("evidence_summary"))))

    print()
    print("Action V4 Marco hits:", len(action_hits))

    for i, row in enumerate(action_hits, start=1):
        print()
        print(f"ACTION ROW {i}")
        print(" subject:", repr(txt(row.get("subject_attempt_id"))))
        print(" related:", repr(txt(row.get("related_attempt_id"))))
        print(" action:", repr(txt(row.get("action"))))
        print(" lane:", repr(txt(row.get("lane"))))
        print(" source:", repr(txt(row.get("source_name"))))

    print()
    print("=" * 115)
    print("LOCAL EVIDENCE SCAN")
    print("=" * 115)

    keywords = [
        "marco andretti",
        "226.108",
        "230.345",
    ]

    semantic_terms = [
        "second attempt",
        "second run",
        "another attempt",
        "another run",
        "retry",
        "re-qual",
        "requal",
        "went back",
        "returned",
        "improved",
        "retired",
        "withdrawn",
        "qualifying run",
    ]

    hit_rows = []
    seen = set()

    for root in EVIDENCE_ROOTS:
        if not root.exists():
            continue

        for path in root.rglob("*"):
            if not path.is_file():
                continue

            if path.suffix.lower() not in {
                ".txt",
                ".md",
                ".csv",
                ".json",
                ".html",
                ".htm",
            }:
                continue

            if "marco_repeat_evidence_hits_v1" in path.name:
                continue

            raw = read_text(path)
            low = raw.lower()

            if not any(k in low for k in keywords):
                continue

            for unit in split_units(raw):
                u = unit.lower()

                if "marco andretti" not in u and "andretti, marco" not in u:
                    continue

                speed_hits = [
                    s
                    for s in ["226.108", "230.345"]
                    if s in unit
                ]

                term_hits = [
                    t
                    for t in semantic_terms
                    if t in u
                ]

                if not speed_hits and not term_hits:
                    continue

                key = (
                    str(path),
                    unit[:500],
                )

                if key in seen:
                    continue

                seen.add(key)

                hit_rows.append({
                    "source_path": str(path),
                    "speed_hits": "|".join(speed_hits),
                    "semantic_hits": "|".join(term_hits),
                    "text": unit[:1800],
                })

    print()
    print("Evidence hits:", len(hit_rows))

    for i, row in enumerate(hit_rows, start=1):
        print()
        print("-" * 115)
        print(f"HIT {i}")
        print(row["source_path"])
        print("speeds:", row["speed_hits"] or "NONE")
        print("semantics:", row["semantic_hits"] or "NONE")
        print(row["text"])

    covered_ids = {
        txt(row.get("attempt_id"))
        for row in chronology
        if (
            txt(row.get("attempt_id")) in marco_set
            and
            txt(row.get("chronology_usable")).lower() == "true"
        )
    }

    missing_ids = sorted(
        marco_set - covered_ids
    )

    write_csv(
        OUT,
        audit_rows,
        [
            "attempt_id",
            "driver_name",
            "car_number",
            "car_attempt_index",
            "speed_mph",
            "canonical_status",
            "official_status",
        ],
    )

    write_csv(
        HITS_OUT,
        hit_rows,
        [
            "source_path",
            "speed_hits",
            "semantic_hits",
            "text",
        ],
    )

    qa_rows = [
        {
            "metric": "marco_attempt_count",
            "value": len(marco_ids),
            "status": "PASS" if len(marco_ids) == 2 else "REVIEW",
        },
        {
            "metric": "chronology_covered_count",
            "value": len(covered_ids),
            "status": "PASS",
        },
        {
            "metric": "chronology_missing_count",
            "value": len(missing_ids),
            "status": "PASS",
        },
        {
            "metric": "action_rows",
            "value": len(action_hits),
            "status": "PASS",
        },
        {
            "metric": "ledger_mutation",
            "value": 0,
            "status": "PASS",
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
    print("=" * 115)
    print("AUDIT SUMMARY")
    print("=" * 115)

    print()
    print("Marco canonical attempts:", len(marco_ids))
    print("Chronology-covered Marco attempts:", len(covered_ids))
    print("Missing Marco attempt IDs:", "|".join(missing_ids) or "NONE")
    print("Existing Marco action rows:", len(action_hits))
    print("Local evidence hits:", len(hit_rows))

    print()
    print(
        "FINAL STATUS: "
        "MARCO_REPEAT_CHRONOLOGY_RECONNAISSANCE_COMPLETE"
    )

    print()
    print("OUTPUTS")
    print(OUT)
    print(HITS_OUT)
    print(QA_OUT)


if __name__ == "__main__":
    main()
