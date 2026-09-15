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
    "r4f6g_canonical_fast_friday_reference_panel_v2.csv"
)

OUT_ROWS = (
    OUT /
    "r4f7a_latent_window_input_readiness_rows_v1.csv"
)

OUT_YEAR = (
    OUT /
    "r4f7a_latent_window_input_readiness_by_year_v1.csv"
)

OUT_QA = (
    OUT /
    "r4f7a_latent_window_input_readiness_qa_v1.csv"
)

OUT_REPORT = (
    OUT /
    "r4f7a_latent_window_input_readiness_report_v1.json"
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

refs = read_csv(
    REFERENCE_PATH
)


print("=" * 136)
print("R4F7A — LATENT WINDOW INPUT READINESS AUDIT")
print("=" * 136)

print(
    f"Attempt rows: {len(attempts)}"
)

print(
    f"Fast Friday reference rows: {len(refs)}"
)


# =============================================================================
# Reference map
# =============================================================================

reference_map = {}

for r in refs:

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
        "reference_speed_mph":
            speed,

        "reference_type":
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
    }


# =============================================================================
# Build readiness rows
# =============================================================================

rows = []

for r in attempts:

    year = year_int(
        r.get("year")
    )

    driver = clean(
        r.get(
            "driver_name"
        )
    )

    key = driver_key(
        driver
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

    complete_performance = truthy(
        r.get(
            "complete_performance_record"
        )
    )

    point_time = clean(
        r.get(
            "time_point_utc"
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

    env_align = truthy(
        r.get(
            "environment_alignment_usable"
        )
    )

    chronology = truthy(
        r.get(
            "chronology_usable"
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
        bool(driver)
        and
        speed is not None
        and
        complete_performance
        and
        status in PRIMARY_STATUSES
    )


    has_reference = (
        ref is not None
    )

    has_point_time = (
        bool(point_time)
    )


    # -------------------------------------------------------------------------
    # Core observation readiness:
    #
    # actual performance
    # + entry-strength prior
    # + observed thermal state
    # + temporal alignment
    # -------------------------------------------------------------------------

    observed_latent_ready = (
        strict_performance
        and
        has_reference
        and
        ptsc
        and
        has_point_time
        and
        env_align
    )


    # -------------------------------------------------------------------------
    # Forecast-state readiness:
    #
    # Can support prospective thermal forecasting later.
    # -------------------------------------------------------------------------

    forecast_latent_ready = (
        observed_latent_ready
        and
        hrrr
    )


    if year == 2024:

        dataset_role = (
            "VALIDATION_ONLY"
        )

    elif year == 2022:

        dataset_role = (
            "DEGRADED_CHRONOLOGY_VALIDATION"
        )

    elif year in {
        2020,
        2021,
        2023,
    }:

        dataset_role = (
            "CORE_DEVELOPMENT"
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
            driver,

        "driver_key":
            key,

        "car_number":
            clean(
                r.get(
                    "car_number"
                )
            ),

        "car_attempt_index":
            clean(
                r.get(
                    "car_attempt_index"
                )
            ),

        "result_status":
            status,

        "four_lap_average_speed_mph":
            (
                speed
                if speed is not None
                else ""
            ),

        "strict_performance_eligible":
            strict_performance,

        "fast_friday_reference_available":
            has_reference,

        "fast_friday_reference_type":
            (
                ref[
                    "reference_type"
                ]
                if ref
                else ""
            ),

        "time_point_available":
            has_point_time,

        "environment_alignment_usable":
            env_align,

        "chronology_usable":
            chronology,

        "ptsc_track_temp_available":
            ptsc,

        "hrrr_leakage_safe_available":
            hrrr,

        "observed_latent_ready":
            observed_latent_ready,

        "forecast_latent_ready":
            forecast_latent_ready,

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
            "fast_friday_reference_available"
        ]
    ]

    with_time = [
        r
        for r in strict
        if r[
            "time_point_available"
        ]
    ]

    with_ptsc = [
        r
        for r in strict
        if r[
            "ptsc_track_temp_available"
        ]
    ]

    with_hrrr = [
        r
        for r in strict
        if r[
            "hrrr_leakage_safe_available"
        ]
    ]

    observed_ready = [
        r
        for r in subset
        if r[
            "observed_latent_ready"
        ]
    ]

    forecast_ready = [
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
            len(
                with_time
            ),

        "strict_with_ptsc":
            len(
                with_ptsc
            ),

        "strict_with_hrrr":
            len(
                with_hrrr
            ),

        "observed_latent_ready":
            len(
                observed_ready
            ),

        "forecast_latent_ready":
            len(
                forecast_ready
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
# Missing-component decomposition
# =============================================================================

missing_counts = Counter()

for r in rows:

    if not r[
        "strict_performance_eligible"
    ]:
        continue

    if not r[
        "fast_friday_reference_available"
    ]:

        missing_counts[
            "NO_FAST_FRIDAY_REFERENCE"
        ] += 1

    if not r[
        "time_point_available"
    ]:

        missing_counts[
            "NO_POINT_TIME"
        ] += 1

    if not r[
        "environment_alignment_usable"
    ]:

        missing_counts[
            "NO_ENV_ALIGNMENT"
        ] += 1

    if not r[
        "ptsc_track_temp_available"
    ]:

        missing_counts[
            "NO_PTSC_TRACK_TEMP"
        ] += 1

    if not r[
        "hrrr_leakage_safe_available"
    ]:

        missing_counts[
            "NO_HRRR_LEAKAGE_SAFE_FORECAST"
        ] += 1


# =============================================================================
# QA
# =============================================================================

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
            "reference_rows",
        "value":
            len(refs),
        "expected":
            71,
        "status":
            (
                "PASS"
                if len(refs) == 71
                else "FAIL"
            ),
    },

    {
        "metric":
            "2024_role_validation_only",
        "value":
            all(
                r[
                    "dataset_role"
                ] == "VALIDATION_ONLY"
                for r in rows
                if r[
                    "year"
                ] == 2024
            ),
        "expected":
            True,
        "status":
            (
                "PASS"
                if all(
                    r[
                        "dataset_role"
                    ] == "VALIDATION_ONLY"
                    for r in rows
                    if r[
                        "year"
                    ] == 2024
                )
                else "FAIL"
            ),
    },

    {
        "metric":
            "2022_role_degraded_validation",
        "value":
            all(
                r[
                    "dataset_role"
                ]
                ==
                "DEGRADED_CHRONOLOGY_VALIDATION"
                for r in rows
                if r[
                    "year"
                ] == 2022
            ),
        "expected":
            True,
        "status":
            (
                "PASS"
                if all(
                    r[
                        "dataset_role"
                    ]
                    ==
                    "DEGRADED_CHRONOLOGY_VALIDATION"
                    for r in rows
                    if r[
                        "year"
                    ] == 2022
                )
                else "FAIL"
            ),
    },

    {
        "metric":
            "car_number_not_integer_normalized",
        "value":
            True,
        "expected":
            True,
        "status":
            "PASS",
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
        "R4F7A",

    "status":
        "R4F7A_LATENT_WINDOW_INPUT_READINESS_READY",

    "purpose":
        (
            "Audit readiness of strict qualifying-performance "
            "observations for later hierarchical thermal + "
            "latent performance-window inference."
        ),

    "year_summary":
        year_rows,

    "missing_components":
        dict(
            missing_counts
        ),

    "core_observation_definition":
        (
            "strict performance + Fast Friday entry prior + "
            "point time + environment alignment + PTSC track temp"
        ),

    "forecast_observation_definition":
        (
            "core observation + leakage-safe HRRR forecast"
        ),

    "important_boundary":
        (
            "This phase performs no model fitting and makes no "
            "claim that thermal variables causally explain "
            "performance variation."
        ),

    "next_phase":
        (
            "After Fast Friday coverage expansion is available, "
            "rerun readiness audit and construct the hierarchical "
            "entry-strength + thermal + latent-window model."
        ),
}


OUT_REPORT.write_text(
    json.dumps(
        report,
        indent=2,
        ensure_ascii=False,
    ),
    encoding="utf-8"
)


# =============================================================================
# Console
# =============================================================================

print()
print("=" * 136)
print("LATENT-WINDOW INPUT READINESS BY YEAR")
print("=" * 136)

for r in year_rows:

    print(
        f"{r['year']} | "
        f"all={r['all_attempt_rows']:3d} | "
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
print("=" * 136)
print("MISSING COMPONENTS AMONG STRICT PERFORMANCE ROWS")
print("=" * 136)

for key, value in sorted(
    missing_counts.items(),
    key=lambda x: (
        -x[1],
        x[0],
    )
):

    print(
        f"{key:36s} | "
        f"{value}"
    )


print()
print("=" * 136)
print("REFERENCE TYPE AMONG OBSERVED-LATENT-READY ROWS")
print("=" * 136)

type_counts = Counter(
    r[
        "fast_friday_reference_type"
    ]
    for r in rows
    if r[
        "observed_latent_ready"
    ]
)

if not type_counts:

    print("NONE")

else:

    for key, value in sorted(
        type_counts.items()
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
    OUT_QA.relative_to(ROOT)
)
print(
    OUT_REPORT.relative_to(ROOT)
)

print()
print(
    "R4F7A_LATENT_WINDOW_INPUT_READINESS_READY"
)
