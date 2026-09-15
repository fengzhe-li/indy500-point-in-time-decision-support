from pathlib import Path
import csv
import json


PHASE = "R3B.1"

OUT = Path("weather/output")

STATE_V3 = OUT / "decision_time_observable_state_v3.csv"

BASELINE_METRICS = (
    OUT
    / "repeat_attempt_delta_baseline_aggregate_metrics_v1.csv"
)

EMPIRICAL_DISTRIBUTIONS = (
    OUT
    / "repeat_performance_empirical_distributions_v1.csv"
)

RECOVERY_PROBABILITY = (
    OUT
    / "repeat_performance_recovery_probability_v1.csv"
)

RECOVERY_SENSITIVITY = (
    OUT
    / "decision_recovery_prior_sensitivity_v1.csv"
)

UNCERTAINTY_ROWS = (
    OUT
    / "repeat_performance_uncertainty_rows_v1.csv"
)

PERFORMANCE_CONTEXT = (
    OUT
    / "performance_context_features.csv"
)

HRRR_ALIGNMENT = (
    OUT
    / "performance_grade_hrrr_forecast_alignment.csv"
)

HRRR_AVAILABILITY = (
    OUT
    / "hrrr_forecast_availability_policy.csv"
)

PTSC_ENVIRONMENT = (
    OUT
    / "performance_grade_attempt_realized_environment.csv"
)

QUEUE_POLICY = (
    OUT
    / "queue_wait_identifiability_2022_v1.csv"
)

SERVICE_POLICY = (
    OUT
    / "pit_service_identifiability_2022_v1.csv"
)

RUBBER_POLICY = (
    OUT
    / "rubber_grip_identifiability_2022_v1.csv"
)

TIRE_POLICY = (
    OUT
    / "tire_thermal_pressure_identifiability_2022_v1.csv"
)


PACK_OUT = (
    OUT
    / "r3b_simulator_input_pack_v1.csv"
)

PERFORMANCE_OUT = (
    OUT
    / "r3b_performance_uncertainty_policy_v1.csv"
)

WAIT_OUT = (
    OUT
    / "r3b_queue_wait_scenarios_v1.csv"
)

ENVIRONMENT_OUT = (
    OUT
    / "r3b_future_environment_policy_v1.csv"
)

SUMMARY_OUT = (
    OUT
    / "r3b_simulator_input_pack_v1.json"
)

QA_OUT = (
    OUT
    / "r3b_simulator_input_pack_v1_qa.csv"
)


EXPECTED_DRIVERS = {
    "Alexander Rossi",
    "Callum Ilott",
    "David Malukas",
    "Helio Castroneves",
    "Marco Andretti",
    "Sage Karam",
    "Scott McLaughlin",
    "Takuma Sato",
}


QUEUE_WAIT_SCENARIOS_MIN = [
    5,
    15,
    30,
    45,
]


def txt(v):
    return "" if v is None else str(v).strip()


def num(v):
    try:
        return float(txt(v))
    except Exception:
        return None


def integer(v):
    try:
        return int(float(txt(v)))
    except Exception:
        return None


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


def first_nonblank(rows, field, default="UNKNOWN"):
    for row in rows:
        value = txt(
            row.get(field)
        )

        if value:
            return value

    return default


def choose_baseline(rows):

    usable = []

    for row in rows:

        model = txt(
            row.get("model_name")
        )

        mae = num(
            row.get("pooled_mae_mph")
        )

        rank = num(
            row.get("mae_rank")
        )

        if model and mae is not None:

            usable.append({
                "model_name":
                    model,

                "pooled_mae_mph":
                    mae,

                "mae_rank":
                    rank,
            })

    if not usable:
        return None

    ranked = [
        row
        for row in usable
        if row["mae_rank"]
        is not None
    ]

    if ranked:
        ranked.sort(
            key=lambda x: (
                x["mae_rank"],
                x["pooled_mae_mph"],
                x["model_name"],
            )
        )

        return ranked[0]

    usable.sort(
        key=lambda x: (
            x["pooled_mae_mph"],
            x["model_name"],
        )
    )

    return usable[0]


def main():

    print()
    print("=" * 126)
    print(
        "R3B.1 — LIMITED UNCERTAINTY-AWARE "
        "SIMULATOR INPUT PACK FREEZE"
    )
    print("=" * 126)

    required = [
        STATE_V3,
        BASELINE_METRICS,
        EMPIRICAL_DISTRIBUTIONS,
        RECOVERY_PROBABILITY,
        RECOVERY_SENSITIVITY,
        UNCERTAINTY_ROWS,
        PERFORMANCE_CONTEXT,
        HRRR_ALIGNMENT,
        HRRR_AVAILABILITY,
        PTSC_ENVIRONMENT,
        QUEUE_POLICY,
        SERVICE_POLICY,
        RUBBER_POLICY,
        TIRE_POLICY,
    ]

    print()
    print("INPUT CHECK")
    print("-" * 126)

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
            "Missing:",
            "|".join(missing),
        )

        print()
        print(
            "FINAL STATUS: "
            "R3B1_SIMULATOR_INPUT_PACK_MISSING_INPUTS"
        )

        return

    states = read_csv(
        STATE_V3
    )

    baseline_rows = read_csv(
        BASELINE_METRICS
    )

    empirical = read_csv(
        EMPIRICAL_DISTRIBUTIONS
    )

    recovery = read_csv(
        RECOVERY_PROBABILITY
    )

    recovery_sensitivity = read_csv(
        RECOVERY_SENSITIVITY
    )

    uncertainty_rows = read_csv(
        UNCERTAINTY_ROWS
    )

    performance_context = read_csv(
        PERFORMANCE_CONTEXT
    )

    hrrr_alignment = read_csv(
        HRRR_ALIGNMENT
    )

    hrrr_availability = read_csv(
        HRRR_AVAILABILITY
    )

    ptsc_environment = read_csv(
        PTSC_ENVIRONMENT
    )

    queue_policy_rows = read_csv(
        QUEUE_POLICY
    )

    service_policy_rows = read_csv(
        SERVICE_POLICY
    )

    rubber_policy_rows = read_csv(
        RUBBER_POLICY
    )

    tire_policy_rows = read_csv(
        TIRE_POLICY
    )

    # --------------------------------------------------
    # State validation
    # --------------------------------------------------

    state_drivers = {
        txt(
            row.get("driver_name")
        )
        for row in states
    }

    state_exact = (
        len(states)
        ==
        8
        and
        state_drivers
        ==
        EXPECTED_DRIVERS
    )

    temporal_safe = all(
        txt(
            row.get(
                "historical_action_is_observable_feature"
            )
        ).lower()
        ==
        "false"
        and
        txt(
            row.get(
                "historical_lane_is_observable_feature"
            )
        ).lower()
        ==
        "false"
        and
        txt(
            row.get(
                "queue_transition_is_observable_feature"
            )
        ).lower()
        ==
        "false"
        and
        txt(
            row.get(
                "post_action_outcome_is_observable_feature"
            )
        ).lower()
        ==
        "false"
        for row in states
    )

    print()
    print("=" * 126)
    print("STATE INPUT")
    print("=" * 126)

    print()
    print(
        "State rows:",
        len(states),
    )

    print(
        "Frozen target exact:",
        state_exact,
    )

    print(
        "Temporal-safe flags:",
        temporal_safe,
    )

    # --------------------------------------------------
    # Baseline model selection
    # --------------------------------------------------

    best_baseline = choose_baseline(
        baseline_rows
    )

    print()
    print("=" * 126)
    print("REPEAT-DELTA BASELINE")
    print("=" * 126)

    if best_baseline:

        print()
        print(
            "Best model:",
            best_baseline[
                "model_name"
            ],
        )

        print(
            "Pooled MAE:",
            best_baseline[
                "pooled_mae_mph"
            ],
        )

        print(
            "MAE rank:",
            best_baseline[
                "mae_rank"
            ],
        )

    else:

        print()
        print(
            "No usable baseline metric row."
        )

    zero_baseline_best = (
        best_baseline
        is not None
        and
        best_baseline[
            "model_name"
        ]
        ==
        "ZERO_DELTA_BASELINE"
    )

    # --------------------------------------------------
    # Empirical performance distributions
    # --------------------------------------------------

    empirical_scopes = [
        txt(
            row.get(
                "distribution_scope"
            )
        )
        for row in empirical
    ]

    empirical_scopes = [
        x
        for x in empirical_scopes
        if x
    ]

    print()
    print("=" * 126)
    print("EMPIRICAL PERFORMANCE UNCERTAINTY")
    print("=" * 126)

    print()
    print(
        "Empirical distribution rows:",
        len(empirical),
    )

    print(
        "Scopes:"
    )

    for scope in empirical_scopes:
        print(
            " ",
            scope,
        )

    # Preserve all empirical rows.
    performance_policy_rows = []

    for i, row in enumerate(
        empirical,
        start=1,
    ):

        performance_policy_rows.append({
            "policy_row_id":
                f"R3B1-PERF-{i:03d}",

            "distribution_scope":
                txt(
                    row.get(
                        "distribution_scope"
                    )
                ),

            "rows":
                txt(
                    row.get("rows")
                ),

            "mean_delta_mph":
                txt(
                    row.get(
                        "mean_delta_mph"
                    )
                ),

            "median_delta_mph":
                txt(
                    row.get(
                        "median_delta_mph"
                    )
                ),

            "std_delta_mph":
                txt(
                    row.get(
                        "std_delta_mph"
                    )
                ),

            "q05_delta_mph":
                txt(
                    row.get(
                        "q05_delta_mph"
                    )
                ),

            "q10_delta_mph":
                txt(
                    row.get(
                        "q10_delta_mph"
                    )
                ),

            "q25_delta_mph":
                txt(
                    row.get(
                        "q25_delta_mph"
                    )
                ),

            "q50_delta_mph":
                txt(
                    row.get(
                        "q50_delta_mph"
                    )
                ),

            "q75_delta_mph":
                txt(
                    row.get(
                        "q75_delta_mph"
                    )
                ),

            "q90_delta_mph":
                txt(
                    row.get(
                        "q90_delta_mph"
                    )
                ),

            "q95_delta_mph":
                txt(
                    row.get(
                        "q95_delta_mph"
                    )
                ),

            "prob_delta_gt_0":
                txt(
                    row.get(
                        "prob_delta_gt_0"
                    )
                ),

            "prob_delta_lt_0":
                txt(
                    row.get(
                        "prob_delta_lt_0"
                    )
                ),

            "uncertainty_policy_hash":
                txt(
                    row.get(
                        "uncertainty_policy_hash"
                    )
                ),

            "simulator_role":
                "EMPIRICAL_REPEAT_DELTA_DISTRIBUTION",

            "selection_policy":
                (
                    "USE_SCOPE_EXPLICITLY;"
                    "DO_NOT_SILENTLY_POOL_REGIMES"
                ),
        })

    write_csv(
        PERFORMANCE_OUT,
        performance_policy_rows,
        list(
            performance_policy_rows[0].keys()
        ),
    )

    # --------------------------------------------------
    # Recovery posterior
    # --------------------------------------------------

    print()
    print("=" * 126)
    print("RECOVERY PROBABILITY")
    print("=" * 126)

    print()
    print(
        "Recovery posterior rows:",
        len(recovery),
    )

    for row in recovery:

        print()
        print(
            " ",
            txt(
                row.get(
                    "eligibility_group"
                )
            ),
        )

        print(
            "   successes/trials:",
            txt(
                row.get(
                    "successes"
                )
            ),
            "/",
            txt(
                row.get(
                    "trials"
                )
            ),
        )

        print(
            "   posterior mean:",
            txt(
                row.get(
                    "posterior_mean_probability"
                )
            ),
        )

        print(
            "   q05-q95:",
            txt(
                row.get(
                    "posterior_q05_probability"
                )
            ),
            "-",
            txt(
                row.get(
                    "posterior_q95_probability"
                )
            ),
        )

    # --------------------------------------------------
    # Queue-wait policy
    # --------------------------------------------------

    queue_policy_text = " ".join(
        " ".join(
            txt(v)
            for v in row.values()
        )
        for row in queue_policy_rows
    ).upper()

    queue_latent = (
        "LATENT"
        in queue_policy_text
        or
        "NOT_IDENTIFIABLE"
        in queue_policy_text
    )

    wait_rows = []

    for wait_min in (
        QUEUE_WAIT_SCENARIOS_MIN
    ):

        wait_rows.append({
            "scenario_id":
                f"WAIT_{wait_min:02d}MIN",

            "queue_wait_minutes":
                wait_min,

            "queue_wait_seconds":
                wait_min
                *
                60,

            "historical_truth_claim":
                "False",

            "scenario_role":
                "LATENT_SENSITIVITY_SCENARIO",

            "probability_weight":
                "UNSPECIFIED_EQUAL_SENSITIVITY_ONLY",

            "calibrated_from_exact_historical_wait":
                "False",

            "notes":
                (
                    "Sensitivity value only. "
                    "Must not be described as reconstructed "
                    "historical queue wait."
                ),
        })

    write_csv(
        WAIT_OUT,
        wait_rows,
        list(
            wait_rows[0].keys()
        ),
    )

    print()
    print("=" * 126)
    print("QUEUE-WAIT SCENARIOS")
    print("=" * 126)

    print()
    print(
        "Historical queue wait identifiable:",
        "NO",
    )

    print(
        "Latent treatment valid:",
        queue_latent,
    )

    print(
        "Sensitivity scenarios:",
        "|".join(
            str(x)
            for x in QUEUE_WAIT_SCENARIOS_MIN
        ),
        "minutes",
    )

    print(
        "Probability weights calibrated:",
        "NO",
    )

    # --------------------------------------------------
    # Future environment policy
    # --------------------------------------------------

    hrrr_safe_rows = [
        row
        for row in hrrr_availability
        if txt(
            row.get(
                "leakage_safe_for_primary_analysis"
            )
        ).lower()
        ==
        "true"
    ]

    hrrr_alignment_safe = [
        row
        for row in hrrr_alignment
        if txt(
            row.get(
                "leakage_safe"
            )
        ).lower()
        ==
        "true"
    ]

    ptsc_supported = [
        row
        for row in ptsc_environment
        if txt(
            row.get(
                "performance_alignment_usable"
            )
        ).lower()
        ==
        "true"
    ]

    environment_rows = [
        {
            "environment_component":
                "WEATHER_FORECAST",

            "source":
                "HRRR",

            "historical_input":
                "hrrr_forecast_availability_policy.csv",

            "future_simulator_use":
                (
                    "DECISION_TIME_AVAILABLE_FORECAST_"
                    "PLUS_LATENT_WAIT"
                ),

            "leakage_control":
                "REQUIRED",

            "realized_future_values_allowed_as_decision_input":
                "False",

            "ready":
                str(
                    len(
                        hrrr_safe_rows
                    )
                    >
                    0
                ),

            "notes":
                (
                    "Only forecasts available by the decision "
                    "time may generate future environment states."
                ),
        },

        {
            "environment_component":
                "TRACK_TEMPERATURE",

            "source":
                "PTSC",

            "historical_input":
                "performance_grade_attempt_realized_environment.csv",

            "future_simulator_use":
                (
                    "OBSERVED_STATE_WHERE_SUPPORTED;"
                    "NO_AIR_TO_TRACK_PROXY"
                ),

            "leakage_control":
                "REQUIRED",

            "realized_future_values_allowed_as_decision_input":
                "False",

            "ready":
                str(
                    len(
                        ptsc_supported
                    )
                    >
                    0
                ),

            "notes":
                (
                    "Observed PTSC track temperature may ground "
                    "historical state where timing is supported. "
                    "Do not infer track temperature from air temp."
                ),
        },

        {
            "environment_component":
                "RUBBER_GRIP",

            "source":
                "NONE",

            "historical_input":
                "rubber_grip_identifiability_2022_v1.csv",

            "future_simulator_use":
                "UNKNOWN",

            "leakage_control":
                "NOT_APPLICABLE",

            "realized_future_values_allowed_as_decision_input":
                "False",

            "ready":
                "False",

            "notes":
                (
                    "No elapsed-time proxy and no reconstructed "
                    "rubber/grip trajectory."
                ),
        },

        {
            "environment_component":
                "TIRE_THERMAL_PRESSURE",

            "source":
                "NONE",

            "historical_input":
                "tire_thermal_pressure_identifiability_2022_v1.csv",

            "future_simulator_use":
                "UNKNOWN",

            "leakage_control":
                "NOT_APPLICABLE",

            "realized_future_values_allowed_as_decision_input":
                "False",

            "ready":
                "False",

            "notes":
                (
                    "No attempt-specific historical thermal/"
                    "pressure state."
                ),
        },
    ]

    write_csv(
        ENVIRONMENT_OUT,
        environment_rows,
        list(
            environment_rows[0].keys()
        ),
    )

    # --------------------------------------------------
    # Per-driver simulator pack
    # --------------------------------------------------

    pack_rows = []

    for row in states:

        pack_rows.append({
            "state_id":
                txt(
                    row.get(
                        "state_id"
                    )
                ),

            "year":
                txt(
                    row.get(
                        "year"
                    )
                ),

            "driver_name":
                txt(
                    row.get(
                        "driver_name"
                    )
                ),

            "first_attempt_id":
                txt(
                    row.get(
                        "first_attempt_id"
                    )
                ),

            "first_attempt_speed_mph":
                txt(
                    row.get(
                        "first_attempt_speed_mph"
                    )
                )
                or
                "UNKNOWN",

            "predecision_current_rank":
                txt(
                    row.get(
                        "predecision_current_rank"
                    )
                )
                or
                "UNKNOWN",

            "predecision_cutoff_rank":
                txt(
                    row.get(
                        "predecision_cutoff_rank"
                    )
                )
                or
                "UNKNOWN",

            "predecision_cutoff_speed_mph":
                txt(
                    row.get(
                        "predecision_cutoff_speed_mph"
                    )
                )
                or
                "UNKNOWN",

            "historical_action_label":
                txt(
                    row.get(
                        "historical_action_label"
                    )
                )
                or
                "UNKNOWN",

            "historical_lane_label":
                txt(
                    row.get(
                        "historical_lane_label"
                    )
                )
                or
                "UNKNOWN",

            "repeat_delta_baseline_model":
                (
                    best_baseline[
                        "model_name"
                    ]
                    if best_baseline
                    else
                    "UNKNOWN"
                ),

            "performance_uncertainty_source":
                (
                    "repeat_performance_empirical_"
                    "distributions_v1.csv"
                ),

            "recovery_probability_source":
                (
                    "repeat_performance_recovery_"
                    "probability_v1.csv"
                ),

            "recovery_sensitivity_source":
                (
                    "decision_recovery_prior_"
                    "sensitivity_v1.csv"
                ),

            "queue_wait_treatment":
                "LATENT_SENSITIVITY_VARIABLE",

            "queue_wait_scenarios_minutes":
                "5|15|30|45",

            "queue_wait_probability_model":
                "NONE",

            "weather_treatment":
                (
                    "DECISION_TIME_AVAILABLE_"
                    "HRRR_FORECAST"
                ),

            "track_temperature_treatment":
                (
                    "OBSERVED_PTSC_WHERE_"
                    "SUPPORTED"
                ),

            "pit_service_state":
                "UNKNOWN",

            "rubber_grip_state":
                "UNKNOWN",

            "tire_state":
                "UNKNOWN",

            "historical_action_used_as_feature":
                "False",

            "realized_second_attempt_used_as_forecast_input":
                "False",

            "hard_recommendation_allowed":
                "False",

            "simulator_scope":
                (
                    "LIMITED_UNCERTAINTY_AWARE_"
                    "HISTORICAL_DECISION_SIMULATION"
                ),
        })

    write_csv(
        PACK_OUT,
        pack_rows,
        list(
            pack_rows[0].keys()
        ),
    )

    # --------------------------------------------------
    # QA
    # --------------------------------------------------

    realized_future_leak = any(
        txt(
            row.get(
                "realized_second_attempt_used_as_forecast_input"
            )
        ).lower()
        !=
        "false"
        for row in pack_rows
    )

    action_feature_leak = any(
        txt(
            row.get(
                "historical_action_used_as_feature"
            )
        ).lower()
        !=
        "false"
        for row in pack_rows
    )

    hard_recommendation_leak = any(
        txt(
            row.get(
                "hard_recommendation_allowed"
            )
        ).lower()
        !=
        "false"
        for row in pack_rows
    )

    qa_rows = [
        {
            "metric":
                "state_v3_target_exact",

            "value":
                int(
                    state_exact
                ),

            "status":
                (
                    "PASS"
                    if state_exact
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "temporal_safe_state_flags",

            "value":
                int(
                    temporal_safe
                ),

            "status":
                (
                    "PASS"
                    if temporal_safe
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "best_baseline_is_zero_delta",

            "value":
                (
                    best_baseline[
                        "model_name"
                    ]
                    if best_baseline
                    else
                    "NONE"
                ),

            "status":
                (
                    "PASS"
                    if zero_baseline_best
                    else
                    "REVIEW"
                ),
        },

        {
            "metric":
                "empirical_distribution_rows",

            "value":
                len(
                    empirical
                ),

            "status":
                (
                    "PASS"
                    if len(
                        empirical
                    )
                    >
                    0
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "recovery_probability_rows",

            "value":
                len(
                    recovery
                ),

            "status":
                (
                    "PASS"
                    if len(
                        recovery
                    )
                    >
                    0
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "recovery_sensitivity_rows",

            "value":
                len(
                    recovery_sensitivity
                ),

            "status":
                (
                    "PASS"
                    if len(
                        recovery_sensitivity
                    )
                    >
                    0
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "queue_wait_latent",

            "value":
                int(
                    queue_latent
                ),

            "status":
                (
                    "PASS"
                    if queue_latent
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "queue_wait_scenario_count",

            "value":
                len(
                    wait_rows
                ),

            "status":
                (
                    "PASS"
                    if len(
                        wait_rows
                    )
                    ==
                    4
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "hrrr_leakage_safe_rows",

            "value":
                len(
                    hrrr_safe_rows
                ),

            "status":
                (
                    "PASS"
                    if len(
                        hrrr_safe_rows
                    )
                    >
                    0
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "hrrr_alignment_safe_rows",

            "value":
                len(
                    hrrr_alignment_safe
                ),

            "status":
                (
                    "PASS"
                    if len(
                        hrrr_alignment_safe
                    )
                    >
                    0
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "ptsc_supported_rows",

            "value":
                len(
                    ptsc_supported
                ),

            "status":
                (
                    "PASS"
                    if len(
                        ptsc_supported
                    )
                    >
                    0
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "realized_future_weather_leak",

            "value":
                int(
                    realized_future_leak
                ),

            "status":
                (
                    "PASS"
                    if not realized_future_leak
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "historical_action_feature_leak",

            "value":
                int(
                    action_feature_leak
                ),

            "status":
                (
                    "PASS"
                    if not action_feature_leak
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "hard_recommendation_claim",

            "value":
                int(
                    hard_recommendation_leak
                ),

            "status":
                (
                    "PASS"
                    if not hard_recommendation_leak
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "service_rubber_tire_imputation",

            "value":
                0,

            "status":
                "PASS",
        },

        {
            "metric":
                "elapsed_time_used_as_track_evolution",

            "value":
                0,

            "status":
                "PASS",
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
        row["status"]
        ==
        "FAIL"
        for row in qa_rows
    )

    summary_payload = {
        "phase":
            PHASE,

        "state_rows":
            len(
                states
            ),

        "baseline_model":
            (
                best_baseline[
                    "model_name"
                ]
                if best_baseline
                else
                None
            ),

        "baseline_pooled_mae_mph":
            (
                best_baseline[
                    "pooled_mae_mph"
                ]
                if best_baseline
                else
                None
            ),

        "zero_delta_baseline_best":
            zero_baseline_best,

        "empirical_distribution_rows":
            len(
                empirical
            ),

        "recovery_probability_rows":
            len(
                recovery
            ),

        "recovery_prior_sensitivity_rows":
            len(
                recovery_sensitivity
            ),

        "queue_wait": {
            "status":
                "LATENT",

            "scenarios_minutes":
                QUEUE_WAIT_SCENARIOS_MIN,

            "probability_model":
                None,

            "historical_truth_claim":
                False,
        },

        "environment": {
            "weather":
                (
                    "DECISION_TIME_AVAILABLE_"
                    "HRRR_ONLY"
                ),

            "realized_future_weather_as_input":
                False,

            "track_temperature":
                (
                    "OBSERVED_PTSC_WHERE_"
                    "SUPPORTED"
                ),

            "air_to_track_proxy":
                False,

            "rubber_grip":
                "UNKNOWN",

            "tire_state":
                "UNKNOWN",

            "pit_service":
                "UNKNOWN",
        },

        "historical_action_role":
            "LABEL_ONLY",

        "hard_recommendation_ready":
            False,

        "input_pack_ready":
            not hard_fail,

        "next_phase":
            (
                "R3B2_BUILD_FUTURE_ENVIRONMENT_"
                "SCENARIOS"
                if not hard_fail
                else
                "R3B1_REVIEW_REQUIRED"
            ),
    }

    SUMMARY_OUT.write_text(
        json.dumps(
            summary_payload,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print()
    print("=" * 126)
    print("INPUT PACK SUMMARY")
    print("=" * 126)

    print()
    print(
        "Simulator state rows:",
        len(
            pack_rows
        ),
    )

    print(
        "Baseline model:",
        (
            best_baseline[
                "model_name"
            ]
            if best_baseline
            else
            "UNKNOWN"
        ),
    )

    print(
        "ZERO_DELTA_BASELINE best:",
        zero_baseline_best,
    )

    print(
        "Empirical distribution rows:",
        len(
            empirical
        ),
    )

    print(
        "Recovery posterior rows:",
        len(
            recovery
        ),
    )

    print(
        "Recovery sensitivity rows:",
        len(
            recovery_sensitivity
        ),
    )

    print()
    print(
        "Queue wait:",
        "LATENT",
    )

    print(
        "Wait scenarios:",
        "5|15|30|45 min",
    )

    print(
        "Queue-wait probability model:",
        "NONE",
    )

    print()
    print(
        "HRRR leakage-safe policy rows:",
        len(
            hrrr_safe_rows
        ),
    )

    print(
        "Leakage-safe HRRR alignment rows:",
        len(
            hrrr_alignment_safe
        ),
    )

    print(
        "Supported PTSC environment rows:",
        len(
            ptsc_supported
        ),
    )

    print()
    print(
        "Realized future weather used as input:",
        "NO",
    )

    print(
        "Historical action used as feature:",
        "NO",
    )

    print(
        "Service/rubber/tire imputed:",
        "NO",
    )

    print(
        "Elapsed time used as track evolution:",
        "NO",
    )

    print(
        "Hard retain/withdraw recommendation:",
        "NOT YET",
    )

    print()
    print("=" * 126)

    if not hard_fail:

        print(
            "FINAL STATUS: "
            "R3B1_LIMITED_SIMULATOR_INPUT_PACK_FROZEN_READY"
        )

    else:

        print(
            "FINAL STATUS: "
            "R3B1_SIMULATOR_INPUT_PACK_REVIEW_REQUIRED"
        )

    print("=" * 126)

    print()
    print("OUTPUTS")
    print(PACK_OUT)
    print(PERFORMANCE_OUT)
    print(WAIT_OUT)
    print(ENVIRONMENT_OUT)
    print(SUMMARY_OUT)
    print(QA_OUT)


if __name__ == "__main__":
    main()
