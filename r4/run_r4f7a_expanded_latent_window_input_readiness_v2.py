from pathlib import Path
from collections import Counter
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

REFERENCE_PATH = (
    OUT /
    "r4f6k_expanded_fast_friday_canonical_panel_v1.csv"
)

OUT_ROWS = (
    OUT /
    "r4f7a_v2_expanded_latent_window_input_readiness_rows.csv"
)

OUT_YEAR = (
    OUT /
    "r4f7a_v2_expanded_latent_window_input_readiness_by_year.csv"
)

OUT_COMPARE = (
    OUT /
    "r4f7a_v2_reference_expansion_gain_by_year.csv"
)

OUT_QA = (
    OUT /
    "r4f7a_v2_expanded_latent_window_input_readiness_qa.csv"
)

OUT_REPORT = (
    OUT /
    "r4f7a_v2_expanded_latent_window_input_readiness_report.json"
)


PRIMARY_STATUSES = {
    "VALID_RETAINED",
    "VALID_SUPERSEDED",
    "WITHDRAWN",
}

OLD_READY = {
    2020: 0,
    2021: 3,
    2022: 0,
    2023: 17,
    2024: 6,
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


def read_csv(path):
    with path.open(
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as f:

        return list(
            csv.DictReader(f)
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


for path in [
    ATTEMPT_PATH,
    REFERENCE_PATH,
]:

    if not path.exists():

        raise SystemExit(
            f"MISSING INPUT: {path}"
        )


attempts = read_csv(
    ATTEMPT_PATH
)

references = read_csv(
    REFERENCE_PATH
)


print("=" * 138)
print("R4F7A-v2 — EXPANDED LATENT WINDOW INPUT READINESS")
print("=" * 138)

print(
    f"Attempt rows: {len(attempts)}"
)

print(
    f"Expanded Fast Friday reference rows: "
    f"{len(references)}"
)


# =============================================================================
# Reference map
# =============================================================================

reference_map = {}

for r in references:

    year = year_int(
        r.get("year")
    )

    key = clean(
        r.get(
            "driver_key"
        )
    )

    speed = num(
        r.get(
            "reference_speed_mph"
        )
    )

    if (
        year is None
        or
        not key
        or
        speed is None
    ):
        continue

    reference_map[
        (
            year,
            key,
        )
    ] = {
        "speed":
            speed,

        "type":
            clean(
                r.get(
                    "reference_type"
                )
            ),

        "model_role":
            clean(
                r.get(
                    "model_role"
                )
            ),

        "car_number":
            clean(
                r.get(
                    "car_number"
                )
            ),
    }


# =============================================================================
# Readiness rows
# =============================================================================

rows = []


for r in attempts:

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

    point_time = bool(
        clean(
            r.get(
                "time_point_utc"
            )
        )
    )

    env_align = truthy(
        r.get(
            "environment_alignment_usable"
        )
    )

    ptsc = truthy(
        r.get(
            "ptsc_track_temp_available"
        )
    )

    hrrr = truthy(
        r.get(
            "hrrr_leakage_safe_available"
        )
    )

    ref = reference_map.get(
        (
            year,
            key,
        )
    )


    strict_performance = (
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


    observed_ready = (
        strict_performance
        and
        ref is not None
        and
        point_time
        and
        env_align
        and
        ptsc
    )


    forecast_ready = (
        observed_ready
        and
        hrrr
    )


    if year in {
        2020,
        2021,
        2023,
    }:

        dataset_role = (
            "CORE_DEVELOPMENT"
        )

    elif year == 2022:

        dataset_role = (
            "DEGRADED_CHRONOLOGY_VALIDATION"
        )

    elif year == 2024:

        dataset_role = (
            "VALIDATION_ONLY"
        )

    else:

        dataset_role = (
            "OTHER"
        )


    rows.append({
        "year":
            year,

        "attempt_id":
            clean(
                r.get(
                    "attempt_id"
                )
            ),

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

        "result_status":
            status,

        "strict_performance_eligible":
            strict_performance,

        "reference_available":
            ref is not None,

        "reference_speed_mph":
            (
                ref[
                    "speed"
                ]
                if ref
                else ""
            ),

        "reference_type":
            (
                ref[
                    "type"
                ]
                if ref
                else ""
            ),

        "point_time_available":
            point_time,

        "environment_alignment_usable":
            env_align,

        "ptsc_track_temp_available":
            ptsc,

        "hrrr_leakage_safe_available":
            hrrr,

        "observed_latent_ready":
            observed_ready,

        "forecast_latent_ready":
            forecast_ready,

        "dataset_role":
            dataset_role,
    })


# =============================================================================
# Year summary
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
        for r in rows
        if r[
            "year"
        ] == year
    ]

    strict = [
        r
        for r in subset
        if r[
            "strict_performance_eligible"
        ]
    ]

    with_ref = [
        r
        for r in strict
        if r[
            "reference_available"
        ]
    ]

    observed = [
        r
        for r in subset
        if r[
            "observed_latent_ready"
        ]
    ]

    forecast = [
        r
        for r in subset
        if r[
            "forecast_latent_ready"
        ]
    ]


    year_rows.append({
        "year":
            year,

        "all_attempt_rows":
            len(
                subset
            ),

        "strict_performance_rows":
            len(
                strict
            ),

        "strict_with_reference":
            len(
                with_ref
            ),

        "strict_with_point_time":
            sum(
                r[
                    "point_time_available"
                ]
                for r in strict
            ),

        "strict_with_ptsc":
            sum(
                r[
                    "ptsc_track_temp_available"
                ]
                for r in strict
            ),

        "strict_with_hrrr":
            sum(
                r[
                    "hrrr_leakage_safe_available"
                ]
                for r in strict
            ),

        "observed_latent_ready":
            len(
                observed
            ),

        "forecast_latent_ready":
            len(
                forecast
            ),

        "dataset_role":
            (
                subset[
                    0
                ][
                    "dataset_role"
                ]
                if subset
                else ""
            ),
    })


# =============================================================================
# Gain versus pre-expansion audit
# =============================================================================

compare_rows = []


for r in year_rows:

    year = r[
        "year"
    ]

    old = OLD_READY.get(
        year,
        0
    )

    new = r[
        "observed_latent_ready"
    ]

    compare_rows.append({
        "year":
            year,

        "old_observed_ready":
            old,

        "new_observed_ready":
            new,

        "absolute_gain":
            new - old,

        "gain_multiple":
            (
                new / old
                if old > 0
                else ""
            ),

        "dataset_role":
            r[
                "dataset_role"
            ],
    })


# =============================================================================
# Core development totals
# =============================================================================

core_years = {
    2020,
    2021,
    2023,
}

old_core = sum(
    OLD_READY[
        year
    ]
    for year in core_years
)

new_core = sum(
    r[
        "observed_latent_ready"
    ]
    for r in year_rows
    if r[
        "year"
    ] in core_years
)

new_core_forecast = sum(
    r[
        "forecast_latent_ready"
    ]
    for r in year_rows
    if r[
        "year"
    ] in core_years
)


# =============================================================================
# Missing components after expansion
# =============================================================================

missing = Counter()

for r in rows:

    if not r[
        "strict_performance_eligible"
    ]:
        continue

    if not r[
        "reference_available"
    ]:

        missing[
            "NO_REFERENCE"
        ] += 1

    if not r[
        "point_time_available"
    ]:

        missing[
            "NO_POINT_TIME"
        ] += 1

    if not r[
        "environment_alignment_usable"
    ]:

        missing[
            "NO_ENV_ALIGNMENT"
        ] += 1

    if not r[
        "ptsc_track_temp_available"
    ]:

        missing[
            "NO_PTSC"
        ] += 1

    if not r[
        "hrrr_leakage_safe_available"
    ]:

        missing[
            "NO_HRRR"
        ] += 1


# =============================================================================
# Reference type distribution
# =============================================================================

core_reference_types = Counter(
    r[
        "reference_type"
    ]
    for r in rows
    if (
        r[
            "observed_latent_ready"
        ]
        and
        r[
            "year"
        ] in core_years
    )
)

validation_reference_types = Counter(
    r[
        "reference_type"
    ]
    for r in rows
    if (
        r[
            "observed_latent_ready"
        ]
        and
        r[
            "year"
        ] == 2024
    )
)


# =============================================================================
# QA
# =============================================================================

ref_year_counts = Counter(
    year_int(
        r.get("year")
    )
    for r in references
)


qa_rows = [
    {
        "metric":
            "attempt_rows",
        "value":
            len(attempts),
        "expected":
            329,
        "status":
            (
                "PASS"
                if len(attempts) == 329
                else "FAIL"
            ),
    },

    {
        "metric":
            "2020_reference_entries",
        "value":
            ref_year_counts[2020],
        "expected":
            33,
        "status":
            (
                "PASS"
                if ref_year_counts[2020] == 33
                else "FAIL"
            ),
    },

    {
        "metric":
            "2021_reference_entries",
        "value":
            ref_year_counts[2021],
        "expected":
            35,
        "status":
            (
                "PASS"
                if ref_year_counts[2021] == 35
                else "FAIL"
            ),
    },

    {
        "metric":
            "2022_role_degraded",
        "value":
            all(
                clean(
                    r.get(
                        "model_role"
                    )
                )
                ==
                "DEGRADED_CHRONOLOGY_VALIDATION"
                for r in references
                if year_int(
                    r.get("year")
                ) == 2022
            ),
        "expected":
            True,
        "status":
            (
                "PASS"
                if all(
                    clean(
                        r.get(
                            "model_role"
                        )
                    )
                    ==
                    "DEGRADED_CHRONOLOGY_VALIDATION"
                    for r in references
                    if year_int(
                        r.get("year")
                    ) == 2022
                )
                else "FAIL"
            ),
    },

    {
        "metric":
            "2024_validation_only",
        "value":
            all(
                clean(
                    r.get(
                        "model_role"
                    )
                )
                ==
                "VALIDATION_ONLY"
                for r in references
                if year_int(
                    r.get("year")
                ) == 2024
            ),
        "expected":
            True,
        "status":
            (
                "PASS"
                if all(
                    clean(
                        r.get(
                            "model_role"
                        )
                    )
                    ==
                    "VALIDATION_ONLY"
                    for r in references
                    if year_int(
                        r.get("year")
                    ) == 2024
                )
                else "FAIL"
            ),
    },

    {
        "metric":
            "core_development_rows_increased",
        "value":
            new_core,
        "expected":
            f">{old_core}",
        "status":
            (
                "PASS"
                if new_core > old_core
                else "FAIL"
            ),
    },

    {
        "metric":
            "audit_only_no_model_fit",
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

with OUT_ROWS.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=list(
            rows[0].keys()
        )
    )

    writer.writeheader()
    writer.writerows(
        rows
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


with OUT_COMPARE.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=list(
            compare_rows[0].keys()
        )
    )

    writer.writeheader()
    writer.writerows(
        compare_rows
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
        "R4F7A_V2",

    "status":
        "R4F7A_V2_EXPANDED_LATENT_READINESS_READY",

    "old_core_development_ready":
        old_core,

    "new_core_development_ready":
        new_core,

    "new_core_forecast_ready":
        new_core_forecast,

    "core_growth_multiple":
        (
            new_core / old_core
            if old_core > 0
            else None
        ),

    "year_summary":
        year_rows,

    "gain_by_year":
        compare_rows,

    "remaining_missing_components":
        dict(
            missing
        ),

    "core_reference_type_distribution":
        dict(
            core_reference_types
        ),

    "validation_reference_type_distribution":
        dict(
            validation_reference_types
        ),

    "important_boundary":
        (
            "This readiness audit does not fit the latent-window model. "
            "2024 remains validation-only and 2022 remains degraded "
            "chronology validation."
        ),

    "next_phase":
        (
            "If core development readiness is materially expanded, "
            "freeze the R4F7 model interface and begin hierarchical "
            "entry-reference + thermal + latent-window development."
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
print("EXPANDED LATENT-WINDOW READINESS BY YEAR")
print("=" * 138)

for r in year_rows:

    print(
        f"{r['year']} | "
        f"strict={r['strict_performance_rows']:3d} | "
        f"+ref={r['strict_with_reference']:3d} | "
        f"+time={r['strict_with_point_time']:3d} | "
        f"+PTSC={r['strict_with_ptsc']:3d} | "
        f"+HRRR={r['strict_with_hrrr']:3d} | "
        f"OBS_READY={r['observed_latent_ready']:3d} | "
        f"FCST_READY={r['forecast_latent_ready']:3d} | "
        f"{r['dataset_role']}"
    )


print()
print("=" * 138)
print("READINESS GAIN FROM FAST FRIDAY EXPANSION")
print("=" * 138)

for r in compare_rows:

    multiple = (
        f"{r['gain_multiple']:.2f}x"
        if r[
            "gain_multiple"
        ] != ""
        else "-"
    )

    print(
        f"{r['year']} | "
        f"old={r['old_observed_ready']:3d} | "
        f"new={r['new_observed_ready']:3d} | "
        f"gain=+{r['absolute_gain']:3d} | "
        f"multiple={multiple}"
    )


print()
print("=" * 138)
print("CORE DEVELOPMENT TOTAL")
print("=" * 138)

print(
    f"Old core observed-ready: "
    f"{old_core}"
)

print(
    f"New core observed-ready: "
    f"{new_core}"
)

print(
    f"New core forecast-ready: "
    f"{new_core_forecast}"
)

print(
    f"Growth multiple: "
    f"{new_core / old_core:.2f}x"
)


print()
print("=" * 138)
print("CORE REFERENCE TYPE DISTRIBUTION")
print("=" * 138)

for key, value in sorted(
    core_reference_types.items()
):

    print(
        f"{key:36s} | "
        f"{value}"
    )


print()
print("=" * 138)
print("REMAINING MISSING COMPONENTS")
print("=" * 138)

for key, value in sorted(
    missing.items(),
    key=lambda x: (
        -x[1],
        x[0],
    )
):

    print(
        f"{key:36s} | "
        f"{value}"
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

    for r in fails:

        print(
            f"FAIL | "
            f"{r['metric']} | "
            f"value={r['value']} | "
            f"expected={r['expected']}"
        )

    raise SystemExit(1)


print()
print("OUTPUTS")
print(
    OUT_ROWS.relative_to(ROOT)
)
print(
    OUT_YEAR.relative_to(ROOT)
)
print(
    OUT_COMPARE.relative_to(ROOT)
)
print(
    OUT_QA.relative_to(ROOT)
)
print(
    OUT_REPORT.relative_to(ROOT)
)

print()
print(
    "R4F7A_V2_EXPANDED_LATENT_READINESS_READY"
)
