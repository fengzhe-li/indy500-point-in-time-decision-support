from pathlib import Path
from collections import Counter
import csv
import json


ROOT = Path(
    "/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈"
)

OUT = ROOT / "r4/output"

INPUT = (
    OUT /
    "r4f7a_latent_window_input_readiness_rows_v1.csv"
)

OUT_YEAR = (
    OUT /
    "r4f7a_b_latent_readiness_ceiling_by_year_v1.csv"
)

OUT_ROWS = (
    OUT /
    "r4f7a_b_latent_readiness_ceiling_rows_v1.csv"
)

OUT_QA = (
    OUT /
    "r4f7a_b_latent_readiness_ceiling_qa_v1.csv"
)

OUT_REPORT = (
    OUT /
    "r4f7a_b_latent_readiness_ceiling_report_v1.json"
)


def clean(v):
    if v is None:
        return ""
    return str(v).strip()


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


if not INPUT.exists():
    raise SystemExit(
        f"MISSING INPUT: {INPUT}"
    )


raw = read_csv(
    INPUT
)


print("=" * 136)
print("R4F7A-B — LATENT READINESS BOTTLENECK CEILING AUDIT")
print("=" * 136)

print(
    f"Input rows: {len(raw)}"
)


rows = []

for r in raw:

    try:
        year = int(
            float(
                clean(
                    r.get("year")
                )
            )
        )
    except Exception:
        continue


    strict = truthy(
        r.get(
            "strict_performance_eligible"
        )
    )

    ref = truthy(
        r.get(
            "fast_friday_reference_available"
        )
    )

    point = truthy(
        r.get(
            "time_point_available"
        )
    )

    env = truthy(
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


    # Current observed model readiness.
    current_ready = (
        strict
        and
        ref
        and
        point
        and
        env
        and
        ptsc
    )


    current_forecast_ready = (
        current_ready
        and
        hrrr
    )


    # -------------------------------------------------------------------------
    # Counterfactual ceilings.
    #
    # These are NOT imputed observations.
    # They answer:
    # "If this one missing component became available, how many rows
    # would otherwise already satisfy everything?"
    # -------------------------------------------------------------------------

    ready_except_reference = (
        strict
        and
        point
        and
        env
        and
        ptsc
    )


    forecast_ready_except_reference = (
        ready_except_reference
        and
        hrrr
    )


    ready_except_point_time = (
        strict
        and
        ref
        and
        env
        and
        ptsc
    )


    ready_except_ptsc = (
        strict
        and
        ref
        and
        point
        and
        env
    )


    ready_except_env_alignment = (
        strict
        and
        ref
        and
        point
        and
        ptsc
    )


    forecast_ready_except_hrrr = (
        current_ready
    )


    structural_nonreference_ready = (
        strict
        and
        point
        and
        env
        and
        ptsc
        and
        hrrr
    )


    missing = []

    if strict:

        if not ref:
            missing.append(
                "REFERENCE"
            )

        if not point:
            missing.append(
                "POINT_TIME"
            )

        if not env:
            missing.append(
                "ENV_ALIGNMENT"
            )

        if not ptsc:
            missing.append(
                "PTSC"
            )

        if not hrrr:
            missing.append(
                "HRRR"
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
            clean(
                r.get(
                    "driver_name"
                )
            ),

        "strict_performance":
            strict,

        "current_ready":
            current_ready,

        "current_forecast_ready":
            current_forecast_ready,

        "ready_except_reference":
            ready_except_reference,

        "forecast_ready_except_reference":
            forecast_ready_except_reference,

        "ready_except_point_time":
            ready_except_point_time,

        "ready_except_ptsc":
            ready_except_ptsc,

        "ready_except_env_alignment":
            ready_except_env_alignment,

        "forecast_ready_except_hrrr":
            forecast_ready_except_hrrr,

        "structural_nonreference_ready":
            structural_nonreference_ready,

        "missing_components":
            ";".join(
                missing
            ),

        "missing_component_count":
            len(
                missing
            ),
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
        for r in rows
        if r[
            "year"
        ] == year
    ]

    strict = [
        r
        for r in subset
        if r[
            "strict_performance"
        ]
    ]

    current = sum(
        r[
            "current_ready"
        ]
        for r in strict
    )

    current_fcst = sum(
        r[
            "current_forecast_ready"
        ]
        for r in strict
    )

    full_reference_ceiling = sum(
        r[
            "ready_except_reference"
        ]
        for r in strict
    )

    full_reference_forecast_ceiling = sum(
        r[
            "forecast_ready_except_reference"
        ]
        for r in strict
    )

    full_point_ceiling = sum(
        r[
            "ready_except_point_time"
        ]
        for r in strict
    )

    full_ptsc_ceiling = sum(
        r[
            "ready_except_ptsc"
        ]
        for r in strict
    )

    full_env_ceiling = sum(
        r[
            "ready_except_env_alignment"
        ]
        for r in strict
    )


    reference_unlock = (
        full_reference_ceiling
        -
        current
    )

    point_unlock = (
        full_point_ceiling
        -
        current
    )

    ptsc_unlock = (
        full_ptsc_ceiling
        -
        current
    )

    env_unlock = (
        full_env_ceiling
        -
        current
    )


    single_missing = Counter()

    for r in strict:

        if (
            r[
                "missing_component_count"
            ] == 1
        ):

            single_missing[
                r[
                    "missing_components"
                ]
            ] += 1


    year_rows.append({
        "year":
            year,

        "strict_rows":
            len(
                strict
            ),

        "current_observed_ready":
            current,

        "current_forecast_ready":
            current_fcst,

        "ceiling_if_reference_complete":
            full_reference_ceiling,

        "forecast_ceiling_if_reference_complete":
            full_reference_forecast_ceiling,

        "increment_if_reference_complete":
            reference_unlock,

        "ceiling_if_point_time_complete":
            full_point_ceiling,

        "increment_if_point_time_complete":
            point_unlock,

        "ceiling_if_ptsc_complete":
            full_ptsc_ceiling,

        "increment_if_ptsc_complete":
            ptsc_unlock,

        "ceiling_if_env_alignment_complete":
            full_env_ceiling,

        "increment_if_env_alignment_complete":
            env_unlock,

        "only_reference_missing":
            single_missing[
                "REFERENCE"
            ],

        "only_point_time_missing":
            single_missing[
                "POINT_TIME"
            ],

        "only_ptsc_missing":
            single_missing[
                "PTSC"
            ],

        "only_env_alignment_missing":
            single_missing[
                "ENV_ALIGNMENT"
            ],

        "only_hrrr_missing":
            single_missing[
                "HRRR"
            ],
    })


qa_rows = [
    {
        "metric":
            "input_rows",
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
            "current_ready_reproduced",
        "value":
            sum(
                r[
                    "current_ready"
                ]
                for r in rows
            ),
        "expected":
            26,
        "status":
            (
                "PASS"
                if sum(
                    r[
                        "current_ready"
                    ]
                    for r in rows
                ) == 26
                else "FAIL"
            ),
    },

    {
        "metric":
            "audit_only_no_imputation",
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
        "R4F7A_B",

    "status":
        "R4F7A_B_LATENT_READINESS_CEILING_READY",

    "year_ceiling":
        year_rows,

    "interpretation":
        (
            "Ceilings are counterfactual readiness counts only. "
            "No missing values are imputed and no model is fitted."
        ),

    "purpose":
        (
            "Identify which missing input component has the "
            "highest marginal value before hierarchical "
            "latent-window implementation."
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


print()
print("=" * 136)
print("LATENT READINESS CEILING BY YEAR")
print("=" * 136)

for r in year_rows:

    print(
        f"{r['year']} | "
        f"strict={r['strict_rows']:3d} | "
        f"current={r['current_observed_ready']:3d} | "
        f"REF_CEIL={r['ceiling_if_reference_complete']:3d} "
        f"(+{r['increment_if_reference_complete']:3d}) | "
        f"TIME_CEIL={r['ceiling_if_point_time_complete']:3d} "
        f"(+{r['increment_if_point_time_complete']:3d}) | "
        f"PTSC_CEIL={r['ceiling_if_ptsc_complete']:3d} "
        f"(+{r['increment_if_ptsc_complete']:3d}) | "
        f"ENV_CEIL={r['ceiling_if_env_alignment_complete']:3d} "
        f"(+{r['increment_if_env_alignment_complete']:3d})"
    )


print()
print("=" * 136)
print("SINGLE-MISSING BOTTLENECKS")
print("=" * 136)

for r in year_rows:

    print(
        f"{r['year']} | "
        f"reference_only={r['only_reference_missing']:3d} | "
        f"time_only={r['only_point_time_missing']:3d} | "
        f"ptsc_only={r['only_ptsc_missing']:3d} | "
        f"env_only={r['only_env_alignment_missing']:3d} | "
        f"hrrr_only={r['only_hrrr_missing']:3d}"
    )


print()
print("=" * 136)
print("FORECAST CEILING AFTER REFERENCE COMPLETION")
print("=" * 136)

for r in year_rows:

    print(
        f"{r['year']} | "
        f"current_forecast={r['current_forecast_ready']:3d} | "
        f"after_full_reference="
        f"{r['forecast_ceiling_if_reference_complete']:3d}"
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
    "R4F7A_B_LATENT_READINESS_CEILING_READY"
)
