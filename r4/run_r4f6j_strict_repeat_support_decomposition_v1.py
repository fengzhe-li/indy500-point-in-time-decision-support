from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime, timezone
import csv
import json
import math
import re
import statistics
import unicodedata

ROOT = Path(
    "/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈"
)

OUT = ROOT / "r4/output"

ATTEMPT_PATH = (
    OUT /
    "r4p1_attempt_four_lap_panel_v1.csv"
)

REFERENCE_PATH = (
    OUT /
    "r4f6g_canonical_fast_friday_reference_panel_v2.csv"
)

OUT_PAIRS = (
    OUT /
    "r4f6j_strict_repeat_support_pairs_v1.csv"
)

OUT_YEAR = (
    OUT /
    "r4f6j_strict_repeat_support_by_year_v1.csv"
)

OUT_REASON = (
    OUT /
    "r4f6j_strict_repeat_support_loss_reasons_v1.csv"
)

OUT_QA = (
    OUT /
    "r4f6j_strict_repeat_support_qa_v1.csv"
)

OUT_REPORT = (
    OUT /
    "r4f6j_strict_repeat_support_report_v1.json"
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


def driver_key(name):
    value = unicodedata.normalize(
        "NFKD",
        clean(name)
    )

    value = "".join(
        ch
        for ch in value
        if not unicodedata.combining(ch)
    )

    value = value.lower()

    value = re.sub(
        r"[^a-z0-9]+",
        " ",
        value
    )

    return re.sub(
        r"\s+",
        " ",
        value
    ).strip()


def read_csv(path):
    with path.open(
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as f:

        return list(
            csv.DictReader(f)
        )


def interval_width_minutes(
    lower,
    upper,
):
    if (
        lower is None
        or
        upper is None
    ):
        return None

    seconds = (
        upper - lower
    ).total_seconds()

    if seconds < 0:
        return None

    return (
        seconds
        /
        60.0
    )


for path in [
    ATTEMPT_PATH,
    REFERENCE_PATH,
]:

    if not path.exists():

        raise SystemExit(
            f"MISSING INPUT: {path}"
        )


attempt_raw = read_csv(
    ATTEMPT_PATH
)

reference_raw = read_csv(
    REFERENCE_PATH
)


print("=" * 138)
print("R4F6J — STRICT REPEAT SUPPORT DECOMPOSITION")
print("=" * 138)

print(
    f"Attempts: {len(attempt_raw)}"
)

print(
    f"Canonical Fast Friday refs: "
    f"{len(reference_raw)}"
)


# =============================================================================
# Reference availability
# =============================================================================

reference_keys = set()

reference_type = {}

for r in reference_raw:

    year = year_int(
        r.get("year")
    )

    key = clean(
        r.get(
            "driver_key"
        )
    )

    if (
        year is None
        or
        not key
    ):
        continue

    identity = (
        year,
        key,
    )

    reference_keys.add(
        identity
    )

    reference_type[
        identity
    ] = clean(
        r.get(
            "reference_type"
        )
    )


# =============================================================================
# Parse attempts
# =============================================================================

attempts = []

for r in attempt_raw:

    year = year_int(
        r.get("year")
    )

    name = clean(
        r.get(
            "driver_name"
        )
    )

    key = driver_key(
        name
    )

    speed = num(
        r.get(
            "four_lap_average_speed_mph"
        )
    )

    status = clean(
        r.get(
            "result_status"
        )
    )

    complete = truthy(
        r.get(
            "complete_performance_record"
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

    chronology_usable = truthy(
        r.get(
            "chronology_usable"
        )
    )

    time_quality = clean(
        r.get(
            "canonical_event_time_quality"
        )
    )

    time_evidence_class = clean(
        r.get(
            "time_evidence_class"
        )
    )

    primary = (
        year is not None
        and
        bool(name)
        and
        speed is not None
        and
        complete
        and
        status in PRIMARY_STATUSES
    )

    attempts.append({
        "year":
            year,

        "driver_name":
            name,

        "driver_key":
            key,

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

        "speed":
            speed,

        "status":
            status,

        "complete":
            complete,

        "primary":
            primary,

        "point":
            point,

        "lower":
            lower,

        "upper":
            upper,

        "canonical_start":
            canonical_start,

        "chronology_usable":
            chronology_usable,

        "time_quality":
            time_quality,

        "time_evidence_class":
            time_evidence_class,

        "reference_available":
            (
                (
                    year,
                    key,
                )
                in reference_keys
            ),

        "reference_type":
            reference_type.get(
                (
                    year,
                    key,
                ),
                "",
            ),

        "interval_width_minutes":
            interval_width_minutes(
                lower,
                upper,
            ),
    })


# =============================================================================
# Build repeat pairs under several nested eligibility definitions.
#
# Start from all complete performance observations, then progressively apply:
#
# A complete-performance
# B primary status
# C Fast Friday reference
# D point-time both sides
# E interval-time availability
# =============================================================================

complete_by_entry = defaultdict(
    list
)

for r in attempts:

    if not (
        r[
            "year"
        ] is not None
        and
        r[
            "driver_name"
        ]
        and
        r[
            "speed"
        ]
        is not None
        and
        r[
            "complete"
        ]
    ):
        continue

    complete_by_entry[
        (
            r[
                "year"
            ],
            r[
                "driver_key"
            ],
        )
    ].append(
        r
    )


pair_rows = []


for entry, rows in complete_by_entry.items():

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

        both_primary = (
            first[
                "primary"
            ]
            and
            repeat[
                "primary"
            ]
        )

        both_reference = (
            first[
                "reference_available"
            ]
            and
            repeat[
                "reference_available"
            ]
        )

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


        loss_reasons = []

        if not both_primary:
            loss_reasons.append(
                "NON_PRIMARY_STATUS"
            )

        if not both_reference:
            loss_reasons.append(
                "NO_FAST_FRIDAY_REFERENCE"
            )

        if not both_point:
            loss_reasons.append(
                "NO_POINT_TIME_BOTH_SIDES"
            )

        if not both_interval:
            loss_reasons.append(
                "NO_INTERVAL_TIME_BOTH_SIDES"
            )


        pair_rows.append({
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

            "first_status":
                first[
                    "status"
                ],

            "repeat_status":
                repeat[
                    "status"
                ],

            "first_speed_mph":
                first[
                    "speed"
                ],

            "repeat_speed_mph":
                repeat[
                    "speed"
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

            "reference_available":
                both_reference,

            "reference_type":
                first[
                    "reference_type"
                ],

            "both_primary_status":
                both_primary,

            "both_point_time":
                both_point,

            "both_interval_time":
                both_interval,

            "both_any_temporal":
                both_any_temporal,

            "first_point_utc":
                (
                    first[
                        "point"
                    ].isoformat()
                    if first[
                        "point"
                    ]
                    is not None
                    else ""
                ),

            "repeat_point_utc":
                (
                    repeat[
                        "point"
                    ].isoformat()
                    if repeat[
                        "point"
                    ]
                    is not None
                    else ""
                ),

            "first_lower_utc":
                (
                    first[
                        "lower"
                    ].isoformat()
                    if first[
                        "lower"
                    ]
                    is not None
                    else ""
                ),

            "first_upper_utc":
                (
                    first[
                        "upper"
                    ].isoformat()
                    if first[
                        "upper"
                    ]
                    is not None
                    else ""
                ),

            "repeat_lower_utc":
                (
                    repeat[
                        "lower"
                    ].isoformat()
                    if repeat[
                        "lower"
                    ]
                    is not None
                    else ""
                ),

            "repeat_upper_utc":
                (
                    repeat[
                        "upper"
                    ].isoformat()
                    if repeat[
                        "upper"
                    ]
                    is not None
                    else ""
                ),

            "first_interval_width_min":
                (
                    first[
                        "interval_width_minutes"
                    ]
                    if first[
                        "interval_width_minutes"
                    ]
                    is not None
                    else ""
                ),

            "repeat_interval_width_min":
                (
                    repeat[
                        "interval_width_minutes"
                    ]
                    if repeat[
                        "interval_width_minutes"
                    ]
                    is not None
                    else ""
                ),

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

            "first_chronology_usable":
                first[
                    "chronology_usable"
                ],

            "repeat_chronology_usable":
                repeat[
                    "chronology_usable"
                ],

            "loss_reasons":
                ";".join(
                    loss_reasons
                ),
        })


# =============================================================================
# Year decomposition
# =============================================================================

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
        for r in pair_rows
        if r[
            "year"
        ] == year
    ]


    primary = [
        r
        for r in subset
        if r[
            "both_primary_status"
        ]
    ]

    primary_ref = [
        r
        for r in primary
        if r[
            "reference_available"
        ]
    ]

    primary_ref_point = [
        r
        for r in primary_ref
        if r[
            "both_point_time"
        ]
    ]

    primary_ref_interval = [
        r
        for r in primary_ref
        if r[
            "both_interval_time"
        ]
    ]

    primary_ref_any = [
        r
        for r in primary_ref
        if r[
            "both_any_temporal"
        ]
    ]


    year_rows.append({
        "year":
            year,

        "all_complete_repeat_pairs":
            len(
                subset
            ),

        "primary_status_pairs":
            len(
                primary
            ),

        "primary_plus_reference_pairs":
            len(
                primary_ref
            ),

        "primary_ref_point_time_pairs":
            len(
                primary_ref_point
            ),

        "primary_ref_interval_time_pairs":
            len(
                primary_ref_interval
            ),

        "primary_ref_any_temporal_pairs":
            len(
                primary_ref_any
            ),
    })


# =============================================================================
# Loss reason counts
# =============================================================================

reason_counter = Counter()

for r in pair_rows:

    reasons = [
        x
        for x in r[
            "loss_reasons"
        ].split(";")
        if x
    ]

    for reason in reasons:
        reason_counter[
            reason
        ] += 1


reason_rows = [
    {
        "reason":
            reason,

        "pair_count":
            count,
    }
    for reason, count
    in sorted(
        reason_counter.items()
    )
]


# =============================================================================
# Narrow interval audit
#
# This does NOT promote interval midpoint into a point timestamp.
# It only measures whether interval-based validation may be worthwhile.
# =============================================================================

for year in [
    2020,
    2021,
    2022,
    2023,
    2024,
]:

    candidates = [
        r
        for r in pair_rows
        if (
            r[
                "year"
            ] == year
            and
            r[
                "both_primary_status"
            ]
            and
            r[
                "reference_available"
            ]
            and
            r[
                "both_interval_time"
            ]
        )
    ]

    widths = []

    for r in candidates:

        for field in [
            "first_interval_width_min",
            "repeat_interval_width_min",
        ]:

            value = num(
                r.get(field)
            )

            if value is not None:
                widths.append(
                    value
                )


    if widths:

        print()
        print(
            f"{year} INTERVAL WIDTHS | "
            f"n_values={len(widths)} | "
            f"median={statistics.median(widths):.3f} min | "
            f"max={max(widths):.3f} min"
        )


# =============================================================================
# QA
# =============================================================================

qa_rows = [
    {
        "metric":
            "attempt_rows",
        "value":
            len(attempt_raw),
        "expected":
            329,
        "status":
            (
                "PASS"
                if len(attempt_raw) == 329
                else "FAIL"
            ),
    },

    {
        "metric":
            "reference_rows",
        "value":
            len(reference_raw),
        "expected":
            71,
        "status":
            (
                "PASS"
                if len(reference_raw) == 71
                else "FAIL"
            ),
    },

    {
        "metric":
            "repeat_pairs_found",
        "value":
            len(pair_rows),
        "expected":
            ">0",
        "status":
            (
                "PASS"
                if pair_rows
                else "FAIL"
            ),
    },

    {
        "metric":
            "car_numbers_never_integer_normalized",
        "value":
            True,
        "expected":
            True,
        "status":
            "PASS",
    },

    {
        "metric":
            "interval_midpoints_not_used_as_observed_points",
        "value":
            True,
        "expected":
            True,
        "status":
            "PASS",
    },

    {
        "metric":
            "no_model_fit_performed",
        "value":
            True,
        "expected":
            True,
        "status":
            "PASS",
    },
]


# =============================================================================
# Save
# =============================================================================

with OUT_PAIRS.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=list(
            pair_rows[0].keys()
        )
        if pair_rows
        else [
            "year",
            "driver_name",
        ]
    )

    writer.writeheader()
    writer.writerows(
        pair_rows
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


with OUT_REASON.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=[
            "reason",
            "pair_count",
        ]
    )

    writer.writeheader()
    writer.writerows(
        reason_rows
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
        "R4F6J",

    "status":
        "R4F6J_STRICT_REPEAT_SUPPORT_DECOMPOSITION_READY",

    "year_support":
        year_rows,

    "loss_reasons":
        reason_rows,

    "interpretation_rule":
        (
            "Do not classify the local residual-window heuristic "
            "as successful or failed when strict same-support "
            "evaluation is based on approximately one pair."
        ),

    "next_phase_rule":
        (
            "If narrow interval chronology materially expands strict "
            "support, evaluate an interval-aware offline structural test. "
            "Otherwise freeze the heuristic as inconclusive and proceed "
            "to the hierarchical thermal + latent-window model."
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


# =============================================================================
# Console
# =============================================================================

print()
print("=" * 138)
print("STRICT REPEAT SUPPORT BY YEAR")
print("=" * 138)

for r in year_rows:

    print(
        f"{r['year']} | "
        f"all_complete={r['all_complete_repeat_pairs']:2d} | "
        f"primary={r['primary_status_pairs']:2d} | "
        f"+reference={r['primary_plus_reference_pairs']:2d} | "
        f"+point_time={r['primary_ref_point_time_pairs']:2d} | "
        f"+interval_time={r['primary_ref_interval_time_pairs']:2d} | "
        f"+any_temporal={r['primary_ref_any_temporal_pairs']:2d}"
    )


print()
print("=" * 138)
print("SUPPORT LOSS REASONS")
print("=" * 138)

for r in reason_rows:

    print(
        f"{r['reason']:32s} | "
        f"{r['pair_count']}"
    )


print()
print("=" * 138)
print("STRICT PRIMARY+REFERENCE PAIRS")
print("=" * 138)

strict_ref_pairs = [
    r
    for r in pair_rows
    if (
        r[
            "both_primary_status"
        ]
        and
        r[
            "reference_available"
        ]
    )
]

if not strict_ref_pairs:

    print("NONE")

else:

    for r in strict_ref_pairs:

        print(
            f"{r['year']} | "
            f"{r['driver_name']:24s} | "
            f"{r['first_attempt_id']} -> "
            f"{r['repeat_attempt_id']} | "
            f"delta={r['repeat_delta_mph']:+.3f} | "
            f"point={r['both_point_time']} | "
            f"interval={r['both_interval_time']} | "
            f"ref={r['reference_type']}"
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
print("OUTPUTS")
print(
    OUT_PAIRS.relative_to(ROOT)
)
print(
    OUT_YEAR.relative_to(ROOT)
)
print(
    OUT_REASON.relative_to(ROOT)
)
print(
    OUT_QA.relative_to(ROOT)
)
print(
    OUT_REPORT.relative_to(ROOT)
)

print()
print(
    "R4F6J_STRICT_REPEAT_SUPPORT_DECOMPOSITION_READY"
)
