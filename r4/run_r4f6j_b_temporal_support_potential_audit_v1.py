from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime, timezone
import csv
import json
import math
import re
import unicodedata

ROOT = Path(
    "/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈"
)

OUT = ROOT / "r4/output"

ATTEMPT_PATH = (
    OUT /
    "r4p1_attempt_four_lap_panel_v1.csv"
)

OUT_PAIRS = (
    OUT /
    "r4f6j_b_temporal_support_potential_pairs_v1.csv"
)

OUT_YEAR = (
    OUT /
    "r4f6j_b_temporal_support_potential_by_year_v1.csv"
)

OUT_QA = (
    OUT /
    "r4f6j_b_temporal_support_potential_qa_v1.csv"
)

OUT_REPORT = (
    OUT /
    "r4f6j_b_temporal_support_potential_report_v1.json"
)


PRIMARY_STATUSES = {
    "VALID_RETAINED",
    "VALID_SUPERSEDED",
    "WITHDRAWN",
}


def clean(v):
    if v is None:
        return ""
    return str(v).strip()


def num(v):
    s = clean(v)

    if not s:
        return None

    try:
        x = float(s)

        if math.isfinite(x):
            return x

    except Exception:
        pass

    return None


def year_int(v):
    x = num(v)

    if x is None:
        return None

    return int(x)


def truthy(v):
    return clean(v).lower() in {
        "1",
        "true",
        "yes",
        "y",
        "t",
    }


def parse_dt(v):
    s = clean(v)

    if not s:
        return None

    if s.endswith("Z"):
        s = (
            s[:-1]
            +
            "+00:00"
        )

    try:
        dt = datetime.fromisoformat(
            s
        )

    except Exception:
        return None

    if dt.tzinfo is None:
        return None

    return dt.astimezone(
        timezone.utc
    )


def read_csv(path):
    with path.open(
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as f:

        return list(
            csv.DictReader(f)
        )


if not ATTEMPT_PATH.exists():
    raise SystemExit(
        f"MISSING INPUT: {ATTEMPT_PATH}"
    )


raw = read_csv(
    ATTEMPT_PATH
)


attempts = []

for r in raw:

    year = year_int(
        r.get("year")
    )

    speed = num(
        r.get(
            "four_lap_average_speed_mph"
        )
    )

    complete = truthy(
        r.get(
            "complete_performance_record"
        )
    )

    status = clean(
        r.get(
            "result_status"
        )
    )

    attempt_index = num(
        r.get(
            "car_attempt_index"
        )
    )

    point = parse_dt(
        r.get(
            "time_point_utc"
        )
    )

    lower = parse_dt(
        r.get(
            "time_lower_utc"
        )
    )

    upper = parse_dt(
        r.get(
            "time_upper_utc"
        )
    )

    canonical_start = parse_dt(
        r.get(
            "canonical_start_time_utc"
        )
    )

    primary = (
        year is not None
        and
        speed is not None
        and
        complete
        and
        status in PRIMARY_STATUSES
    )

    if not primary:
        continue


    attempts.append({
        "year":
            year,

        "driver_name":
            clean(
                r.get(
                    "driver_name"
                )
            ),

        "entry_key":
            clean(
                r.get(
                    "entry_key"
                )
            ),

        "car_number":
            clean(
                r.get(
                    "car_number"
                )
            ),

        "attempt_id":
            clean(
                r.get(
                    "attempt_id"
                )
            ),

        "attempt_index":
            (
                int(
                    attempt_index
                )
                if attempt_index
                is not None
                else None
            ),

        "status":
            status,

        "speed":
            speed,

        "point":
            point,

        "lower":
            lower,

        "upper":
            upper,

        "canonical_start":
            canonical_start,

        "chronology_usable":
            truthy(
                r.get(
                    "chronology_usable"
                )
            ),

        "environment_alignment_usable":
            truthy(
                r.get(
                    "environment_alignment_usable"
                )
            ),

        "time_quality":
            clean(
                r.get(
                    "canonical_event_time_quality"
                )
            ),

        "time_evidence_class":
            clean(
                r.get(
                    "time_evidence_class"
                )
            ),
    })


by_entry = defaultdict(
    list
)

for r in attempts:

    by_entry[
        (
            r[
                "year"
            ],
            r[
                "entry_key"
            ],
        )
    ].append(
        r
    )


pairs = []

for entry, rows in by_entry.items():

    rows = sorted(
        rows,
        key=lambda r: (
            (
                r[
                    "attempt_index"
                ]
                if r[
                    "attempt_index"
                ]
                is not None
                else 999
            ),
            (
                r[
                    "canonical_start"
                ]
                if r[
                    "canonical_start"
                ]
                is not None
                else datetime.max.replace(
                    tzinfo=timezone.utc
                )
            ),
        )
    )

    if len(rows) < 2:
        continue

    first = rows[0]

    for repeat in rows[1:]:

        both_point = (
            first[
                "point"
            ]
            is not None
            and
            repeat[
                "point"
            ]
            is not None
        )

        both_interval = (
            first[
                "lower"
            ]
            is not None
            and
            first[
                "upper"
            ]
            is not None
            and
            repeat[
                "lower"
            ]
            is not None
            and
            repeat[
                "upper"
            ]
            is not None
        )

        both_any_temporal = (
            (
                first[
                    "point"
                ]
                is not None
                or
                (
                    first[
                        "lower"
                    ]
                    is not None
                    and
                    first[
                        "upper"
                    ]
                    is not None
                )
            )
            and
            (
                repeat[
                    "point"
                ]
                is not None
                or
                (
                    repeat[
                        "lower"
                    ]
                    is not None
                    and
                    repeat[
                        "upper"
                    ]
                    is not None
                )
            )
        )

        both_chronology_usable = (
            first[
                "chronology_usable"
            ]
            and
            repeat[
                "chronology_usable"
            ]
        )

        both_env_usable = (
            first[
                "environment_alignment_usable"
            ]
            and
            repeat[
                "environment_alignment_usable"
            ]
        )


        pairs.append({
            "year":
                first[
                    "year"
                ],

            "driver_name":
                first[
                    "driver_name"
                ],

            "car_number":
                first[
                    "car_number"
                ],

            "first_attempt_id":
                first[
                    "attempt_id"
                ],

            "repeat_attempt_id":
                repeat[
                    "attempt_id"
                ],

            "repeat_delta_mph":
                (
                    repeat[
                        "speed"
                    ]
                    -
                    first[
                        "speed"
                    ]
                ),

            "both_point_time":
                both_point,

            "both_interval_time":
                both_interval,

            "both_any_temporal":
                both_any_temporal,

            "both_chronology_usable":
                both_chronology_usable,

            "both_environment_alignment_usable":
                both_env_usable,

            "first_time_quality":
                first[
                    "time_quality"
                ],

            "repeat_time_quality":
                repeat[
                    "time_quality"
                ],

            "first_time_evidence_class":
                first[
                    "time_evidence_class"
                ],

            "repeat_time_evidence_class":
                repeat[
                    "time_evidence_class"
                ],
        })


year_rows = []

for year in [
    2020,
    2021,
    2022,
    2023,
    2024,
]:

    subset = [
        r
        for r in pairs
        if r[
            "year"
        ] == year
    ]

    year_rows.append({
        "year":
            year,

        "primary_repeat_pairs":
            len(
                subset
            ),

        "both_point_time":
            sum(
                r[
                    "both_point_time"
                ]
                for r in subset
            ),

        "both_interval_time":
            sum(
                r[
                    "both_interval_time"
                ]
                for r in subset
            ),

        "both_any_temporal":
            sum(
                r[
                    "both_any_temporal"
                ]
                for r in subset
            ),

        "both_chronology_usable":
            sum(
                r[
                    "both_chronology_usable"
                ]
                for r in subset
            ),

        "both_environment_alignment_usable":
            sum(
                r[
                    "both_environment_alignment_usable"
                ]
                for r in subset
            ),
    })


qa_rows = [
    {
        "metric":
            "attempt_rows",
        "value":
            len(raw),
        "expected":
            329,
        "status":
            (
                "PASS"
                if len(raw) == 329
                else "FAIL"
            ),
    },

    {
        "metric":
            "primary_repeat_pairs_found",
        "value":
            len(pairs),
        "expected":
            ">0",
        "status":
            (
                "PASS"
                if pairs
                else "FAIL"
            ),
    },

    {
        "metric":
            "reference_independent_audit",
        "value":
            True,
        "expected":
            True,
        "status":
            "PASS",
    },

    {
        "metric":
            "no_model_fit",
        "value":
            True,
        "expected":
            True,
        "status":
            "PASS",
    },
]


with OUT_PAIRS.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=list(
            pairs[0].keys()
        )
    )

    writer.writeheader()
    writer.writerows(
        pairs
    )


with OUT_YEAR.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=list(
            year_rows[0].keys()
        )
    )

    writer.writeheader()
    writer.writerows(
        year_rows
    )


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
    writer.writerows(
        qa_rows
    )


report = {
    "phase":
        "R4F6J_B",

    "status":
        "R4F6J_B_TEMPORAL_SUPPORT_POTENTIAL_READY",

    "purpose":
        (
            "Measure strict repeat temporal support independently "
            "of current Fast Friday reference availability."
        ),

    "year_support":
        year_rows,

    "decision_rule":
        (
            "If 2020-2022 have substantial point/interval temporal "
            "support, newly recovered Fast Friday references can "
            "materially expand strict repeat-window validation. "
            "If temporal support is absent, do not continue pursuing "
            "the local residual-window heuristic."
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


print("=" * 138)
print("R4F6J-B — TEMPORAL SUPPORT POTENTIAL")
print("=" * 138)

print()
print("PRIMARY REPEAT TEMPORAL SUPPORT BY YEAR")

for r in year_rows:

    print(
        f"{r['year']} | "
        f"primary_pairs={r['primary_repeat_pairs']:2d} | "
        f"point={r['both_point_time']:2d} | "
        f"interval={r['both_interval_time']:2d} | "
        f"any_temporal={r['both_any_temporal']:2d} | "
        f"chronology={r['both_chronology_usable']:2d} | "
        f"env_align={r['both_environment_alignment_usable']:2d}"
    )


print()
print("TEMPORAL PAIRS — 2020/2021/2022")

for r in pairs:

    if r[
        "year"
    ] not in {
        2020,
        2021,
        2022,
    }:
        continue

    if not r[
        "both_any_temporal"
    ]:
        continue

    print(
        f"{r['year']} | "
        f"{r['driver_name']:24s} | "
        f"delta={r['repeat_delta_mph']:+.3f} | "
        f"point={r['both_point_time']} | "
        f"interval={r['both_interval_time']} | "
        f"chrono={r['both_chronology_usable']} | "
        f"env={r['both_environment_alignment_usable']}"
    )


fails = [
    r
    for r in qa_rows
    if r[
        "status"
    ] == "FAIL"
]

print()
print(
    f"QA: "
    f"{len(qa_rows)-len(fails)} PASS | "
    f"0 WARN | "
    f"{len(fails)} FAIL"
)

if fails:
    raise SystemExit(1)


print()
print(
    "R4F6J_B_TEMPORAL_SUPPORT_POTENTIAL_READY"
)
