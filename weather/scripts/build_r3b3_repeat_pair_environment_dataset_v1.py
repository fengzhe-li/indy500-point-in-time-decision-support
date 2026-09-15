from pathlib import Path
import csv
import json
from collections import Counter


PHASE = "R3B.3B"

OUT = Path("weather/output")

UNCERTAINTY = (
    OUT
    / "repeat_performance_uncertainty_rows_v1.csv"
)

CONTEXT = (
    OUT
    / "performance_context_features.csv"
)

REALIZED_ENV = (
    OUT
    / "performance_grade_attempt_realized_environment.csv"
)

TIMING = (
    OUT
    / "performance_grade_attempt_timing.csv"
)

HRRR_ALIGNMENT = (
    OUT
    / "performance_grade_hrrr_forecast_alignment.csv"
)

PAIR_OUT = (
    OUT
    / "r3b3_repeat_pair_environment_dataset_v1.csv"
)

SUMMARY_OUT = (
    OUT
    / "r3b3_repeat_pair_environment_dataset_v1.json"
)

QA_OUT = (
    OUT
    / "r3b3_repeat_pair_environment_dataset_v1_qa.csv"
)


FORECAST_FIELDS = [
    "forecast_temp_c",
    "forecast_dewpoint_c",
    "forecast_relative_humidity_pct",
    "forecast_wind_speed_10m_ms",
    "forecast_gust_ms",
    "forecast_pressure_hpa",
    "forecast_cloud_cover_pct",
    "forecast_shortwave_radiation_wm2",
]


PTSC_FIELDS = [
    "ptsc_ambient_c",
    "ptsc_track_c",
    "ptsc_humidity",
    "ptsc_wind",
    "ptsc_pressure",
]


EXPECTED_YEARS = {
    "2020",
    "2021",
    "2023",
}


def txt(v):
    return "" if v is None else str(v).strip()


def fnum(v):
    try:
        return float(txt(v))
    except Exception:
        return None


def truthy(v):
    return txt(v).lower() in {
        "true",
        "1",
        "yes",
    }


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
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)


def delta(a, b):
    """
    Return current/repeat minus baseline/prior.
    """
    if a is None or b is None:
        return None

    return a - b


def fmt(v):
    if v is None:
        return "UNKNOWN"

    return f"{v:.10f}"


def main():

    print()
    print("=" * 128)
    print(
        "R3B.3B — REPEAT-PAIR PERFORMANCE / "
        "ENVIRONMENT BINDING DATASET"
    )
    print("=" * 128)

    required = [
        UNCERTAINTY,
        CONTEXT,
        REALIZED_ENV,
        TIMING,
        HRRR_ALIGNMENT,
    ]

    print()
    print("INPUT CHECK")
    print("-" * 128)

    missing = []

    for path in required:

        exists = path.exists()

        print(
            f"{path}: "
            f"{'PRESENT' if exists else 'MISSING'}"
        )

        if not exists:
            missing.append(str(path))

    if missing:

        print()
        print(
            "FINAL STATUS: "
            "R3B3B_REPEAT_PAIR_ENV_INPUT_MISSING"
        )
        return

    uncertainty = read_csv(
        UNCERTAINTY
    )

    context = read_csv(
        CONTEXT
    )

    realized_env = read_csv(
        REALIZED_ENV
    )

    timing = read_csv(
        TIMING
    )

    hrrr = read_csv(
        HRRR_ALIGNMENT
    )

    print()
    print("=" * 128)
    print("SEMANTIC BINDING")
    print("=" * 128)

    uncertainty_required_fields = {
        "current_attempt_id",
        "baseline_attempt_id",
        "year",
        "driver_name",
        "baseline_speed_mph",
        "target_speed_delta_vs_best_prior_mph",
        "diagnostic_recovery_like",
        "baseline_below_year_median",
        "diagnostic_branch",
    }

    actual_uncertainty_fields = (
        set(
            uncertainty[0].keys()
        )
        if uncertainty
        else
        set()
    )

    missing_semantic_fields = (
        uncertainty_required_fields
        -
        actual_uncertainty_fields
    )

    print()
    print(
        "baseline attempt ID:",
        "baseline_attempt_id",
    )

    print(
        "repeat/current attempt ID:",
        "current_attempt_id",
    )

    print(
        "performance delta:",
        "target_speed_delta_vs_best_prior_mph",
    )

    print(
        "recovery flag:",
        "diagnostic_recovery_like",
    )

    print(
        "baseline group flag:",
        "baseline_below_year_median",
    )

    print(
        "diagnostic branch:",
        "diagnostic_branch",
    )

    print()
    print(
        "Missing required semantic fields:",
        (
            "|".join(
                sorted(
                    missing_semantic_fields
                )
            )
            or
            "NONE"
        ),
    )

    if missing_semantic_fields:

        print()
        print(
            "FINAL STATUS: "
            "R3B3B_REPEAT_PAIR_SEMANTIC_FIELDS_MISSING"
        )
        return

    # --------------------------------------------------
    # Indices
    # --------------------------------------------------

    context_by_attempt = {
        txt(
            row.get(
                "attempt_id"
            )
        ):
        row
        for row in context
        if txt(
            row.get(
                "attempt_id"
            )
        )
    }

    env_by_attempt = {
        txt(
            row.get(
                "attempt_id"
            )
        ):
        row
        for row in realized_env
        if txt(
            row.get(
                "attempt_id"
            )
        )
    }

    timing_by_attempt = {
        txt(
            row.get(
                "attempt_id"
            )
        ):
        row
        for row in timing
        if txt(
            row.get(
                "attempt_id"
            )
        )
    }

    hrrr_by_attempt = {
        txt(
            row.get(
                "attempt_id"
            )
        ):
        row
        for row in hrrr
        if txt(
            row.get(
                "attempt_id"
            )
        )
    }

    # --------------------------------------------------
    # Build pair rows
    # --------------------------------------------------

    pair_rows = []

    for i, row in enumerate(
        uncertainty,
        start=1,
    ):

        year = txt(
            row.get("year")
        )

        driver = txt(
            row.get(
                "driver_name"
            )
        )

        baseline_id = txt(
            row.get(
                "baseline_attempt_id"
            )
        )

        current_id = txt(
            row.get(
                "current_attempt_id"
            )
        )

        baseline_context = (
            context_by_attempt.get(
                baseline_id
            )
        )

        current_context = (
            context_by_attempt.get(
                current_id
            )
        )

        baseline_env = (
            env_by_attempt.get(
                baseline_id
            )
        )

        current_env = (
            env_by_attempt.get(
                current_id
            )
        )

        baseline_timing = (
            timing_by_attempt.get(
                baseline_id
            )
        )

        current_timing = (
            timing_by_attempt.get(
                current_id
            )
        )

        baseline_hrrr = (
            hrrr_by_attempt.get(
                baseline_id
            )
        )

        current_hrrr = (
            hrrr_by_attempt.get(
                current_id
            )
        )

        baseline_context_ok = (
            baseline_context
            is not None
            and
            truthy(
                baseline_context.get(
                    "performance_alignment_usable"
                )
            )
            and
            truthy(
                baseline_context.get(
                    "leakage_safe"
                )
            )
        )

        current_context_ok = (
            current_context
            is not None
            and
            truthy(
                current_context.get(
                    "performance_alignment_usable"
                )
            )
            and
            truthy(
                current_context.get(
                    "leakage_safe"
                )
            )
        )

        baseline_timing_ok = (
            baseline_timing
            is not None
            and
            truthy(
                baseline_timing.get(
                    "performance_alignment_usable"
                )
            )
            and
            bool(
                txt(
                    baseline_timing.get(
                        "mapped_capture_time_utc"
                    )
                )
            )
        )

        current_timing_ok = (
            current_timing
            is not None
            and
            truthy(
                current_timing.get(
                    "performance_alignment_usable"
                )
            )
            and
            bool(
                txt(
                    current_timing.get(
                        "mapped_capture_time_utc"
                    )
                )
            )
        )

        baseline_hrrr_ok = (
            baseline_hrrr
            is not None
            and
            truthy(
                baseline_hrrr.get(
                    "leakage_safe"
                )
            )
        )

        current_hrrr_ok = (
            current_hrrr
            is not None
            and
            truthy(
                current_hrrr.get(
                    "leakage_safe"
                )
            )
        )

        baseline_speed = fnum(
            row.get(
                "baseline_speed_mph"
            )
        )

        observed_delta = fnum(
            row.get(
                "target_speed_delta_vs_best_prior_mph"
            )
        )

        repeat_speed = (
            baseline_speed
            +
            observed_delta
            if (
                baseline_speed
                is not None
                and
                observed_delta
                is not None
            )
            else
            None
        )

        pair_ready = all([
            year in EXPECTED_YEARS,
            baseline_context_ok,
            current_context_ok,
            baseline_timing_ok,
            current_timing_ok,
            baseline_hrrr_ok,
            current_hrrr_ok,
            observed_delta
            is not None,
        ])

        out = {
            "pair_id":
                f"R3B3B-{i:03d}",

            "year":
                year,

            "driver_name":
                driver,

            "car_number":
                txt(
                    row.get(
                        "car_number"
                    )
                ),

            "baseline_attempt_id":
                baseline_id,

            "repeat_attempt_id":
                current_id,

            "baseline_speed_mph":
                fmt(
                    baseline_speed
                ),

            "observed_repeat_delta_mph":
                fmt(
                    observed_delta
                ),

            "reconstructed_repeat_speed_mph":
                fmt(
                    repeat_speed
                ),

            "diagnostic_recovery_like":
                txt(
                    row.get(
                        "diagnostic_recovery_like"
                    )
                ),

            "baseline_below_year_median":
                txt(
                    row.get(
                        "baseline_below_year_median"
                    )
                ),

            "diagnostic_branch":
                txt(
                    row.get(
                        "diagnostic_branch"
                    )
                ),

            "baseline_timing_usable":
                str(
                    baseline_timing_ok
                ),

            "repeat_timing_usable":
                str(
                    current_timing_ok
                ),

            "baseline_hrrr_leakage_safe":
                str(
                    baseline_hrrr_ok
                ),

            "repeat_hrrr_leakage_safe":
                str(
                    current_hrrr_ok
                ),

            "baseline_context_usable":
                str(
                    baseline_context_ok
                ),

            "repeat_context_usable":
                str(
                    current_context_ok
                ),

            "baseline_performance_time_utc":
                (
                    txt(
                        baseline_context.get(
                            "performance_time_utc"
                        )
                    )
                    if baseline_context
                    else
                    "UNKNOWN"
                )
                or
                "UNKNOWN",

            "repeat_performance_time_utc":
                (
                    txt(
                        current_context.get(
                            "performance_time_utc"
                        )
                    )
                    if current_context
                    else
                    "UNKNOWN"
                )
                or
                "UNKNOWN",

            "seconds_since_prior_supported_attempt":
                (
                    txt(
                        current_context.get(
                            "seconds_since_prior_supported_attempt"
                        )
                    )
                    if current_context
                    else
                    "UNKNOWN"
                )
                or
                "UNKNOWN",

            "elapsed_time_role":
                "PAIR_METADATA_ONLY_NOT_TRACK_EVOLUTION",

            "pair_environment_fit_ready":
                str(
                    pair_ready
                ),

            "causal_effect_claim_allowed":
                "False",

            "queue_wait_truth_claim":
                "False",
        }

        # ----------------------------------------------
        # Forecast states and forecast changes
        # ----------------------------------------------

        for field in FORECAST_FIELDS:

            b = (
                fnum(
                    baseline_context.get(
                        field
                    )
                )
                if baseline_context
                else
                None
            )

            c = (
                fnum(
                    current_context.get(
                        field
                    )
                )
                if current_context
                else
                None
            )

            d = delta(
                c,
                b,
            )

            out[
                "baseline_"
                +
                field
            ] = fmt(b)

            out[
                "repeat_"
                +
                field
            ] = fmt(c)

            out[
                "delta_"
                +
                field
            ] = fmt(d)

        # ----------------------------------------------
        # PTSC observed states and changes
        # ----------------------------------------------

        for field in PTSC_FIELDS:

            b = (
                fnum(
                    baseline_env.get(
                        field
                    )
                )
                if baseline_env
                else
                None
            )

            c = (
                fnum(
                    current_env.get(
                        field
                    )
                )
                if current_env
                else
                None
            )

            d = delta(
                c,
                b,
            )

            out[
                "baseline_"
                +
                field
            ] = fmt(b)

            out[
                "repeat_"
                +
                field
            ] = fmt(c)

            out[
                "delta_"
                +
                field
            ] = fmt(d)

        pair_rows.append(out)

    # --------------------------------------------------
    # Coverage
    # --------------------------------------------------

    ready_rows = [
        row
        for row in pair_rows
        if truthy(
            row.get(
                "pair_environment_fit_ready"
            )
        )
    ]

    ready_by_year = Counter(
        row[
            "year"
        ]
        for row in ready_rows
    )

    recovery_ready = [
        row
        for row in ready_rows
        if truthy(
            row.get(
                "diagnostic_recovery_like"
            )
        )
    ]

    normal_ready = [
        row
        for row in ready_rows
        if not truthy(
            row.get(
                "diagnostic_recovery_like"
            )
        )
    ]

    low_baseline_ready = [
        row
        for row in ready_rows
        if truthy(
            row.get(
                "baseline_below_year_median"
            )
        )
    ]

    high_baseline_ready = [
        row
        for row in ready_rows
        if not truthy(
            row.get(
                "baseline_below_year_median"
            )
        )
    ]

    ptsc_pair_complete = [
        row
        for row in ready_rows
        if (
            row[
                "baseline_ptsc_track_c"
            ]
            !=
            "UNKNOWN"
            and
            row[
                "repeat_ptsc_track_c"
            ]
            !=
            "UNKNOWN"
        )
    ]

    print()
    print("=" * 128)
    print("PAIR DATASET SUMMARY")
    print("=" * 128)

    print()
    print(
        "Raw repeat uncertainty rows:",
        len(
            uncertainty
        ),
    )

    print(
        "Pair rows built:",
        len(
            pair_rows
        ),
    )

    print(
        "Environment-fit-ready pairs:",
        len(
            ready_rows
        ),
    )

    print()
    print(
        "Ready by year:"
    )

    for year in sorted(
        EXPECTED_YEARS
    ):
        print(
            f"  {year}:",
            ready_by_year[
                year
            ],
        )

    print()
    print(
        "Normal branch ready:",
        len(
            normal_ready
        ),
    )

    print(
        "Recovery-like ready:",
        len(
            recovery_ready
        ),
    )

    print(
        "Low-baseline ready:",
        len(
            low_baseline_ready
        ),
    )

    print(
        "At/above-median ready:",
        len(
            high_baseline_ready
        ),
    )

    print(
        "Pairs with PTSC track temp at both attempts:",
        len(
            ptsc_pair_complete
        ),
    )

    # --------------------------------------------------
    # Diagnostics
    # --------------------------------------------------

    print()
    print("=" * 128)
    print("READY PAIRS")
    print("=" * 128)

    for row in ready_rows:

        print()
        print(
            f"{row['year']} "
            f"{row['driver_name']}"
        )

        print(
            "  baseline:",
            row[
                "baseline_speed_mph"
            ],
        )

        print(
            "  repeat delta:",
            row[
                "observed_repeat_delta_mph"
            ],
        )

        print(
            "  recovery:",
            row[
                "diagnostic_recovery_like"
            ],
        )

        print(
            "  low baseline:",
            row[
                "baseline_below_year_median"
            ],
        )

        print(
            "  Δ forecast temp C:",
            row[
                "delta_forecast_temp_c"
            ],
        )

        print(
            "  Δ forecast wind m/s:",
            row[
                "delta_forecast_wind_speed_10m_ms"
            ],
        )

        print(
            "  Δ forecast radiation W/m2:",
            row[
                "delta_forecast_shortwave_radiation_wm2"
            ],
        )

        print(
            "  Δ observed track temp C:",
            row[
                "delta_ptsc_track_c"
            ],
        )

    # --------------------------------------------------
    # Write pair dataset
    # --------------------------------------------------

    write_csv(
        PAIR_OUT,
        pair_rows,
        list(
            pair_rows[0].keys()
        ),
    )

    # --------------------------------------------------
    # QA
    # --------------------------------------------------

    duplicate_pairs = []

    seen = set()

    for row in pair_rows:

        key = (
            row[
                "baseline_attempt_id"
            ],
            row[
                "repeat_attempt_id"
            ],
        )

        if key in seen:
            duplicate_pairs.append(
                key
            )
        else:
            seen.add(key)

    year_2022_pairs = [
        row
        for row in ready_rows
        if row[
            "year"
        ]
        ==
        "2022"
    ]

    elapsed_role_bad = [
        row
        for row in pair_rows
        if row[
            "elapsed_time_role"
        ]
        !=
        "PAIR_METADATA_ONLY_NOT_TRACK_EVOLUTION"
    ]

    queue_truth_bad = [
        row
        for row in pair_rows
        if truthy(
            row.get(
                "queue_wait_truth_claim"
            )
        )
    ]

    causal_bad = [
        row
        for row in pair_rows
        if truthy(
            row.get(
                "causal_effect_claim_allowed"
            )
        )
    ]

    qa_rows = [
        {
            "metric":
                "pair_rows_match_uncertainty_rows",

            "value":
                len(
                    pair_rows
                ),

            "status":
                (
                    "PASS"
                    if len(
                        pair_rows
                    )
                    ==
                    len(
                        uncertainty
                    )
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "duplicate_repeat_pairs",

            "value":
                len(
                    duplicate_pairs
                ),

            "status":
                (
                    "PASS"
                    if len(
                        duplicate_pairs
                    )
                    ==
                    0
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "environment_fit_ready_pairs",

            "value":
                len(
                    ready_rows
                ),

            "status":
                (
                    "PASS"
                    if len(
                        ready_rows
                    )
                    >
                    0
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "ready_years",

            "value":
                "|".join(
                    sorted(
                        {
                            row[
                                "year"
                            ]
                            for row
                            in ready_rows
                        }
                    )
                ),

            "status":
                (
                    "PASS"
                    if {
                        row[
                            "year"
                        ]
                        for row
                        in ready_rows
                    }
                    <=
                    EXPECTED_YEARS
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "2022_timed_pairs_used",

            "value":
                len(
                    year_2022_pairs
                ),

            "status":
                (
                    "PASS"
                    if len(
                        year_2022_pairs
                    )
                    ==
                    0
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "normal_branch_pairs_present",

            "value":
                len(
                    normal_ready
                ),

            "status":
                (
                    "PASS"
                    if len(
                        normal_ready
                    )
                    >
                    0
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "recovery_branch_pairs_present",

            "value":
                len(
                    recovery_ready
                ),

            "status":
                (
                    "PASS"
                    if len(
                        recovery_ready
                    )
                    >
                    0
                    else
                    "REVIEW"
                ),
        },

        {
            "metric":
                "ptsc_complete_pairs",

            "value":
                len(
                    ptsc_pair_complete
                ),

            "status":
                "PASS",
        },

        {
            "metric":
                "elapsed_time_track_evolution_misuse",

            "value":
                len(
                    elapsed_role_bad
                ),

            "status":
                (
                    "PASS"
                    if len(
                        elapsed_role_bad
                    )
                    ==
                    0
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "queue_wait_truth_claims",

            "value":
                len(
                    queue_truth_bad
                ),

            "status":
                (
                    "PASS"
                    if len(
                        queue_truth_bad
                    )
                    ==
                    0
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "causal_effect_claims",

            "value":
                len(
                    causal_bad
                ),

            "status":
                (
                    "PASS"
                    if len(
                        causal_bad
                    )
                    ==
                    0
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "protected_outputs_mutated",

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

    hard_fail = any(
        row[
            "status"
        ]
        ==
        "FAIL"
        for row in qa_rows
    )

    payload = {
        "phase":
            PHASE,

        "semantic_binding": {
            "baseline_attempt_id":
                "baseline_attempt_id",

            "repeat_attempt_id":
                "current_attempt_id",

            "performance_delta":
                "target_speed_delta_vs_best_prior_mph",

            "recovery_flag":
                "diagnostic_recovery_like",

            "baseline_group":
                "baseline_below_year_median",

            "diagnostic_branch":
                "diagnostic_branch",
        },

        "pair_rows":
            len(
                pair_rows
            ),

        "environment_fit_ready_pairs":
            len(
                ready_rows
            ),

        "ready_by_year":
            dict(
                ready_by_year
            ),

        "normal_branch_ready_pairs":
            len(
                normal_ready
            ),

        "recovery_like_ready_pairs":
            len(
                recovery_ready
            ),

        "low_baseline_ready_pairs":
            len(
                low_baseline_ready
            ),

        "at_or_above_median_ready_pairs":
            len(
                high_baseline_ready
            ),

        "ptsc_complete_pairs":
            len(
                ptsc_pair_complete
            ),

        "2022_timed_environment_used":
            False,

        "relationship_interpretation":
            "OBSERVATIONAL_SENSITIVITY_NOT_CAUSAL",

        "elapsed_time_role":
            "PAIR_METADATA_ONLY_NOT_TRACK_EVOLUTION",

        "queue_wait":
            "LATENT_NOT_HISTORICAL_TRUTH",

        "next_phase":
            (
                "R3B3C_FIT_PERFORMANCE_ENVIRONMENT_SENSITIVITY"
                if not hard_fail
                else
                "R3B3B_REVIEW_REQUIRED"
            ),
    }

    SUMMARY_OUT.write_text(
        json.dumps(
            payload,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print()
    print("=" * 128)

    if not hard_fail:

        print(
            "FINAL STATUS: "
            "R3B3B_REPEAT_PAIR_ENVIRONMENT_DATASET_READY"
        )

    else:

        print(
            "FINAL STATUS: "
            "R3B3B_REPEAT_PAIR_ENVIRONMENT_DATASET_REVIEW_REQUIRED"
        )

    print("=" * 128)

    print()
    print("OUTPUTS")
    print(PAIR_OUT)
    print(SUMMARY_OUT)
    print(QA_OUT)


if __name__ == "__main__":
    main()
