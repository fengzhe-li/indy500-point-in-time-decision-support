from pathlib import Path
from datetime import datetime, timezone, timedelta
from collections import defaultdict
import csv
import json
import math
import statistics

ROOT = Path(
    "/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈"
)

OUT = ROOT / "r4/output"
OUT.mkdir(parents=True, exist_ok=True)

RESIDUAL_PATH = (
    OUT /
    "r4f4_cross_car_residual_observations_v1.csv"
)

PTSC_PATH = (
    ROOT /
    "weather/evidence/ptsc/"
    "indy500_day1_track_temp_2020_2024_time_normalized.csv"
)

OUT_TARGET = (
    OUT /
    "r4f5a_offline_repeat_latent_window_target_v1.csv"
)

OUT_SUMMARY = (
    OUT /
    "r4f5a_offline_repeat_latent_window_summary_v1.csv"
)

OUT_QA = (
    OUT /
    "r4f5a_offline_repeat_latent_window_qa_v1.csv"
)

OUT_REPORT = (
    OUT /
    "r4f5a_offline_repeat_latent_window_report_v1.json"
)


# =============================================================================
# Offline window target policy
# =============================================================================

HALF_WIDTH_MINUTES = 30

MIN_DISTINCT_CARS = 1

GRID_STEP_MINUTES = 5


def clean(v):
    if v is None:
        return ""
    return str(v).strip()


def num(v):
    s = clean(v)

    if not s:
        return None

    if s.upper() in {
        "UNKNOWN",
        "NONE",
        "NA",
        "NAN",
    }:
        return None

    try:
        x = float(s)

        if math.isfinite(x):
            return x

    except Exception:
        pass

    return None


def integer(v):
    x = num(v)

    if x is None:
        return None

    return int(x)


def parse_dt(v):
    s = clean(v)

    if not s:
        return None

    if s.upper() == "UNKNOWN":
        return None

    if s.endswith("Z"):
        s = s[:-1] + "+00:00"

    try:
        dt = datetime.fromisoformat(s)

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


for path in [
    RESIDUAL_PATH,
    PTSC_PATH,
]:

    if not path.exists():
        raise SystemExit(
            f"MISSING INPUT: {path}"
        )


residual_raw = read_csv(
    RESIDUAL_PATH
)

ptsc_raw = read_csv(
    PTSC_PATH
)


print("=" * 124)
print("R4F5A — OFFLINE REPEAT-BASED LATENT PERFORMANCE WINDOW TARGET")
print("=" * 124)

print(
    f"Residual rows: {len(residual_raw)}"
)

print(
    f"PTSC rows: {len(ptsc_raw)}"
)


# =============================================================================
# Parse repeat residuals
# =============================================================================

residuals = []

for r in residual_raw:

    year = integer(
        r.get(
            "year"
        )
    )

    dt = parse_dt(
        r.get(
            "attempt_time_utc"
        )
    )

    residual = num(
        r.get(
            "residual_vs_first_run_mph"
        )
    )

    car = clean(
        r.get(
            "car_number"
        )
    )

    if (
        year is None
        or
        dt is None
        or
        residual is None
        or
        not car
    ):
        continue

    residuals.append({
        "year":
            year,

        "time":
            dt,

        "car_number":
            car,

        "residual":
            residual,
    })


# =============================================================================
# PTSC session time bounds
#
# We use the observed PTSC coverage to define a stable historical session grid.
# =============================================================================

ptsc_by_year = defaultdict(list)

for r in ptsc_raw:

    year = integer(
        r.get(
            "year"
        )
    )

    dt = parse_dt(
        r.get(
            "utc_datetime"
        )
    )

    if (
        year is None
        or
        dt is None
    ):
        continue

    ptsc_by_year[
        year
    ].append(
        dt
    )


for year in ptsc_by_year:
    ptsc_by_year[
        year
    ].sort()


# =============================================================================
# Build regular 5-minute offline time grid
# =============================================================================

grid_rows = []

for year in sorted(
    ptsc_by_year
):

    start = min(
        ptsc_by_year[
            year
        ]
    )

    end = max(
        ptsc_by_year[
            year
        ]
    )

    t = start

    while t <= end:

        lower = (
            t
            -
            timedelta(
                minutes=HALF_WIDTH_MINUTES
            )
        )

        upper = (
            t
            +
            timedelta(
                minutes=HALF_WIDTH_MINUTES
            )
        )

        nearby = [
            r
            for r in residuals
            if (
                r[
                    "year"
                ] == year
                and
                lower
                <= r[
                    "time"
                ]
                <= upper
            )
        ]


        # One latest/closest vote per car.
        by_car = {}

        for r in nearby:

            distance = abs(
                (
                    r[
                        "time"
                    ]
                    -
                    t
                ).total_seconds()
            )

            existing = by_car.get(
                r[
                    "car_number"
                ]
            )

            if (
                existing is None
                or
                distance
                <
                existing[
                    "distance"
                ]
            ):

                by_car[
                    r[
                        "car_number"
                    ]
                ] = {
                    "distance":
                        distance,

                    "residual":
                        r[
                            "residual"
                        ],

                    "time":
                        r[
                            "time"
                        ],
                }


        values = [
            x[
                "residual"
            ]
            for x in by_car.values()
        ]


        if values:

            median_residual = statistics.median(
                values
            )

            mean_residual = statistics.mean(
                values
            )

            improve_fraction = (
                sum(
                    v > 0
                    for v in values
                )
                /
                len(
                    values
                )
            )

            # Robust sign-style window target.
            if median_residual > 0.10:

                window_class = (
                    "BETTER_THAN_REFERENCE"
                )

            elif median_residual < -0.10:

                window_class = (
                    "WORSE_THAN_REFERENCE"
                )

            else:

                window_class = (
                    "NEUTRAL"
                )

        else:

            median_residual = None
            mean_residual = None
            improve_fraction = None
            window_class = (
                "NO_REPEAT_EVIDENCE"
            )


        grid_rows.append({
            "year":
                year,

            "grid_time_utc":
                t.isoformat(),

            "half_width_minutes":
                HALF_WIDTH_MINUTES,

            "distinct_repeat_cars":
                len(
                    values
                ),

            "median_repeat_residual_mph":
                (
                    f"{median_residual:.6f}"
                    if median_residual is not None
                    else ""
                ),

            "mean_repeat_residual_mph":
                (
                    f"{mean_residual:.6f}"
                    if mean_residual is not None
                    else ""
                ),

            "repeat_improve_fraction":
                (
                    f"{improve_fraction:.6f}"
                    if improve_fraction is not None
                    else ""
                ),

            "offline_window_class":
                window_class,

            "target_available":
                len(
                    values
                )
                >=
                MIN_DISTINCT_CARS,

            "target_role":
                (
                    "OFFLINE_HISTORICAL_WINDOW_TARGET"
                    if len(
                        values
                    )
                    >=
                    MIN_DISTINCT_CARS
                    else
                    "NO_REPEAT_TARGET"
                ),

            "important_constraint":
                (
                    "OFFLINE TARGET ONLY; "
                    "NOT A DECISION-TIME FEATURE"
                ),
        })


        t += timedelta(
            minutes=GRID_STEP_MINUTES
        )


# =============================================================================
# Summary
# =============================================================================

summary_rows = []

for year in sorted(
    {
        r[
            "year"
        ]
        for r in grid_rows
    }
):

    subset = [
        r
        for r in grid_rows
        if r[
            "year"
        ] == year
    ]

    available = [
        r
        for r in subset
        if r[
            "target_available"
        ]
    ]

    class_counts = defaultdict(int)

    for r in available:
        class_counts[
            r[
                "offline_window_class"
            ]
        ] += 1


    summary_rows.append({
        "year":
            year,

        "grid_rows":
            len(
                subset
            ),

        "target_available_rows":
            len(
                available
            ),

        "coverage_fraction":
            (
                len(
                    available
                )
                /
                len(
                    subset
                )
                if subset
                else 0.0
            ),

        "better_rows":
            class_counts[
                "BETTER_THAN_REFERENCE"
            ],

        "neutral_rows":
            class_counts[
                "NEUTRAL"
            ],

        "worse_rows":
            class_counts[
                "WORSE_THAN_REFERENCE"
            ],

        "max_distinct_repeat_cars":
            max(
                (
                    integer(
                        r[
                            "distinct_repeat_cars"
                        ]
                    )
                    or 0
                    for r in subset
                ),
                default=0,
            ),
    })


# =============================================================================
# QA
# =============================================================================

future_role_errors = [
    r
    for r in grid_rows
    if (
        r[
            "target_available"
        ]
        and
        r[
            "important_constraint"
        ]
        !=
        "OFFLINE TARGET ONLY; NOT A DECISION-TIME FEATURE"
    )
]


qa_rows = [
    {
        "metric":
            "parsed_repeat_residuals",

        "value":
            len(
                residuals
            ),

        "expected":
            40,

        "status":
            (
                "PASS"
                if len(
                    residuals
                ) == 40
                else "WARN"
            ),
    },

    {
        "metric":
            "offline_grid_rows",

        "value":
            len(
                grid_rows
            ),

        "expected":
            ">0",

        "status":
            (
                "PASS"
                if grid_rows
                else "FAIL"
            ),
    },

    {
        "metric":
            "offline_target_rows",

        "value":
            sum(
                bool(
                    r[
                        "target_available"
                    ]
                )
                for r in grid_rows
            ),

        "expected":
            ">0",

        "status":
            (
                "PASS"
                if any(
                    r[
                        "target_available"
                    ]
                    for r in grid_rows
                )
                else "FAIL"
            ),
    },

    {
        "metric":
            "offline_target_never_marked_as_decision_feature",

        "value":
            len(
                future_role_errors
            ),

        "expected":
            0,

        "status":
            (
                "PASS"
                if not future_role_errors
                else "FAIL"
            ),
    },
]


# =============================================================================
# Save
# =============================================================================

with OUT_TARGET.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=list(
            grid_rows[0].keys()
        )
    )

    writer.writeheader()
    writer.writerows(
        grid_rows
    )


with OUT_SUMMARY.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=list(
            summary_rows[0].keys()
        )
    )

    writer.writeheader()
    writer.writerows(
        summary_rows
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
        "R4F5A",

    "status":
        "R4F5A_OFFLINE_REPEAT_LATENT_WINDOW_TARGET_READY",

    "repeat_residuals":
        len(
            residuals
        ),

    "grid_step_minutes":
        GRID_STEP_MINUTES,

    "smoothing_half_width_minutes":
        HALF_WIDTH_MINUTES,

    "target_rows":
        sum(
            bool(
                r[
                    "target_available"
                ]
            )
            for r in grid_rows
        ),

    "methodology": [
        (
            "Complete historical repeat residuals are allowed "
            "because this phase constructs an OFFLINE target."
        ),

        (
            "The target is not used as a decision-time input."
        ),

        (
            "One car contributes at most one closest repeat "
            "residual to each time-grid estimate."
        ),

        (
            "This is a first sparse target layer. "
            "Fast Friday and first-run hierarchical priors "
            "may be added later through partial pooling."
        ),
    ],

    "next_phase":
        (
            "Evaluate whether repeat-only target density is "
            "sufficient. If sparse, add pre-session / first-run "
            "hierarchical normalization to obtain a denser "
            "latent performance-window target."
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
print("=" * 124)
print("OFFLINE WINDOW TARGET COVERAGE")
print("=" * 124)

total_target = sum(
    bool(
        r[
            "target_available"
        ]
    )
    for r in grid_rows
)

print(
    f"Grid rows: "
    f"{len(grid_rows)}"
)

print(
    f"Target rows: "
    f"{total_target}"
)

print(
    f"Coverage: "
    f"{total_target / len(grid_rows):.3f}"
    if grid_rows
    else
    "Coverage: 0"
)


print()
print("=" * 124)
print("YEAR TARGET COVERAGE")
print("=" * 124)

for r in summary_rows:

    print(
        f"{r['year']} | "
        f"grid={r['grid_rows']:3d} | "
        f"target={r['target_available_rows']:3d} | "
        f"coverage={r['coverage_fraction']:.3f} | "
        f"better={r['better_rows']:3d} | "
        f"neutral={r['neutral_rows']:3d} | "
        f"worse={r['worse_rows']:3d} | "
        f"max_cars={r['max_distinct_repeat_cars']}"
    )


print()
print("=" * 124)
print("TARGET DENSITY INTERPRETATION")
print("=" * 124)

coverage = (
    total_target
    /
    len(
        grid_rows
    )
    if grid_rows
    else 0.0
)

if coverage >= 0.50:

    print(
        "Repeat-only target density is reasonably broad."
    )

    print(
        "Proceed to latent-window estimation with "
        "repeat evidence as a major target source."
    )

elif coverage >= 0.20:

    print(
        "Repeat-only target density is usable but sparse."
    )

    print(
        "Proceed with partial pooling and add "
        "pre-session / first-run reference evidence."
    )

else:

    print(
        "Repeat-only target density is too sparse "
        "to define the full-session latent window alone."
    )

    print(
        "Use repeat residuals as high-value anchors, "
        "then densify with pre-session / first-run "
        "hierarchical reference evidence."
    )


fails = [
    r
    for r in qa_rows
    if r[
        "status"
    ] == "FAIL"
]

warns = [
    r
    for r in qa_rows
    if r[
        "status"
    ] == "WARN"
]

print()
print(
    f"QA: "
    f"{len(qa_rows)-len(fails)-len(warns)} PASS | "
    f"{len(warns)} WARN | "
    f"{len(fails)} FAIL"
)

if fails:
    raise SystemExit(1)


print()
print("OUTPUTS")
print(
    OUT_TARGET.relative_to(ROOT)
)
print(
    OUT_SUMMARY.relative_to(ROOT)
)
print(
    OUT_QA.relative_to(ROOT)
)
print(
    OUT_REPORT.relative_to(ROOT)
)

print()
print(
    "R4F5A_OFFLINE_REPEAT_LATENT_WINDOW_TARGET_READY"
)
