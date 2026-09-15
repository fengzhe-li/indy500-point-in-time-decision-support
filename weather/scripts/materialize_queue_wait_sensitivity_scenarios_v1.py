from pathlib import Path
import hashlib
import json

import numpy as np
import pandas as pd


# ============================================================
# INPUTS
# ============================================================

RUN_DURATION_FILE = Path(
    "weather/output/queue_wait_run_duration_reference_v1.csv"
)

QUEUE_POLICY_FILE = Path(
    "weather/output/queue_wait_uncertainty_policy_v1.csv"
)

SESSION_BOUNDARY_FILE = Path(
    "weather/output/queue_wait_session_boundary_audit_v1.csv"
)


# ============================================================
# OUTPUTS
# ============================================================

WAIT_SCENARIO_FILE = Path(
    "weather/output/queue_wait_sensitivity_scenarios_v1.csv"
)

CUTOFF_GRID_FILE = Path(
    "weather/output/queue_wait_cutoff_feasibility_grid_v1.csv"
)

LATEST_WITHDRAW_FILE = Path(
    "weather/output/queue_wait_latest_withdraw_reference_v1.csv"
)

QA_FILE = Path(
    "weather/output/queue_wait_sensitivity_scenarios_v1_qa.csv"
)

REPORT_FILE = Path(
    "weather/output/queue_wait_sensitivity_scenarios_v1.md"
)


# ============================================================
# FROZEN DESIGN
# ============================================================

POLICY_VERSION = (
    "QUEUE_WAIT_SENSITIVITY_SCENARIOS_V1"
)

EXPECTED_2024_CUTOFF_UTC = pd.Timestamp(
    "2024-05-18T21:50:00Z"
)

# ------------------------------------------------------------
# Explicit scenario assumptions.
#
# These are NOT historical queue-wait estimates.
# They are sensitivity cases for the latent pre-run delay:
#
# withdraw
# -> queue
# -> staging
# -> release
# -> timed run begins
# ------------------------------------------------------------

WAIT_SCENARIOS_MINUTES = [
    5,
    15,
    30,
    45,
]

# ------------------------------------------------------------
# Decision-time sensitivity grid.
#
# Also assumptions / analysis grid, not reconstructed
# historical decision timestamps.
# ------------------------------------------------------------

TIME_REMAINING_GRID_MINUTES = [
    5,
    10,
    15,
    20,
    30,
    45,
    60,
    90,
    120,
]

RUN_DURATION_QUANTILES = [
    ("MEDIAN", "median_seconds"),
    ("Q90", "q90_seconds"),
    ("Q95", "q95_seconds"),
    ("MAX_OBSERVED", "max_seconds"),
]


# ============================================================
# HELPERS
# ============================================================

def read_required(path):

    if not path.exists():
        raise FileNotFoundError(
            f"Missing required file: {path}"
        )

    return pd.read_csv(
        path,
        low_memory=False,
    )


def numeric(series):

    return pd.to_numeric(
        series,
        errors="coerce",
    )


def stable_hash(payload):

    text = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )

    return hashlib.sha256(
        text.encode("utf-8")
    ).hexdigest()


def parse_bool(value):

    return str(
        value
    ).strip().lower() in [
        "true",
        "1",
        "yes",
    ]


# ============================================================
# MAIN
# ============================================================

def main():

    run_reference = read_required(
        RUN_DURATION_FILE
    )

    queue_policy = read_required(
        QUEUE_POLICY_FILE
    )

    boundaries = read_required(
        SESSION_BOUNDARY_FILE
    )

    print()
    print("=" * 100)
    print(
        "PHASE 6B — QUEUE / WAIT "
        "SENSITIVITY SCENARIO MATERIALIZATION V1"
    )
    print("=" * 100)

    # ========================================================
    # Validate Phase 6A policy
    # ========================================================

    required_policy_components = {
        "DIRECT_QUEUE_WAIT":
            "UNOBSERVED",

        "QUEUE_POSITION":
            "UNOBSERVED",

        "TIMED_RUN_DURATION":
            "OBSERVED_SUPPORTED",

        "STAGING_AND_RELEASE_OVERHEAD":
            "UNOBSERVED_SEPARATELY",

        "SESSION_CUTOFF_2024":
            "EXACT_SUPPORTED",

        "WITHDRAW_ACTION":
            "PROBABILISTIC",

        "NO_COMPLETED_RERUN_BEFORE_CUTOFF":
            "EXPLICIT_FAILURE_STATE",
    }

    actual_policy = {
        str(row["component"]):
            str(row["status"])
        for _, row
        in queue_policy.iterrows()
    }

    for component, expected_status in (
        required_policy_components.items()
    ):

        actual_status = actual_policy.get(
            component
        )

        if actual_status != expected_status:

            raise RuntimeError(
                f"Queue policy mismatch for {component}: "
                f"expected {expected_status}, "
                f"got {actual_status}"
            )

    # ========================================================
    # Resolve complete-run duration reference
    # ========================================================

    all_run = run_reference[
        run_reference[
            "scope"
        ]
        == "ALL_COMPLETE_FOUR_LAP_ATTEMPTS"
    ].copy()

    if len(all_run) != 1:

        raise RuntimeError(
            "Expected exactly one all-run duration reference row."
        )

    run_row = all_run.iloc[0]

    run_duration_values = {}

    for label, column in (
        RUN_DURATION_QUANTILES
    ):

        if column not in run_row.index:

            raise RuntimeError(
                f"Missing run-duration field: {column}"
            )

        value = float(
            numeric(
                pd.Series(
                    [
                        run_row[
                            column
                        ]
                    ]
                )
            ).iloc[0]
        )

        if not np.isfinite(
            value
        ):

            raise RuntimeError(
                f"Invalid run-duration value: {column}"
            )

        run_duration_values[
            label
        ] = value

    median_run_seconds = (
        run_duration_values[
            "MEDIAN"
        ]
    )

    q95_run_seconds = (
        run_duration_values[
            "Q95"
        ]
    )

    # ========================================================
    # Verify 2024 hard cutoff
    # ========================================================

    boundaries = boundaries.copy()

    boundaries[
        "_time"
    ] = pd.to_datetime(
        boundaries[
            "event_time_utc"
        ],
        utc=True,
        errors="coerce",
    )

    hard_mask = (
        numeric(
            boundaries[
                "year"
            ]
        )
        == 2024
    )

    if (
        "usable_for_hard_cutoff"
        in boundaries.columns
    ):

        hard_mask = (
            hard_mask
            &
            boundaries[
                "usable_for_hard_cutoff"
            ]
            .apply(
                parse_bool
            )
        )

    cutoff_candidates = boundaries[
        hard_mask
    ].copy()

    exact_cutoff_found = bool(
        (
            cutoff_candidates[
                "_time"
            ]
            == EXPECTED_2024_CUTOFF_UTC
        ).any()
    )

    if not exact_cutoff_found:

        raise RuntimeError(
            "2024 exact 21:50 UTC cutoff not confirmed."
        )

    # ========================================================
    # Policy hash
    # ========================================================

    policy_payload = {
        "phase":
            "6B",

        "policy_version":
            POLICY_VERSION,

        "wait_scenarios_minutes":
            WAIT_SCENARIOS_MINUTES,

        "time_remaining_grid_minutes":
            TIME_REMAINING_GRID_MINUTES,

        "run_duration_quantiles":
            RUN_DURATION_QUANTILES,

        "2024_cutoff_utc":
            EXPECTED_2024_CUTOFF_UTC.isoformat(),

        "semantic_definition":
            (
                "latent_pre_run_delay = "
                "withdraw_to_timed_run_start; "
                "includes queue + staging + release"
            ),
    }

    policy_hash = stable_hash(
        policy_payload
    )

    # ========================================================
    # Materialize wait scenarios
    # ========================================================

    scenario_rows = []

    for scenario_index, wait_minutes in enumerate(
        WAIT_SCENARIOS_MINUTES,
        start=1,
    ):

        wait_seconds = float(
            wait_minutes
            * 60
        )

        scenario_rows.append(
            {
                "scenario_id":
                    f"WAIT_{wait_minutes:02d}MIN",

                "scenario_order":
                    scenario_index,

                "latent_pre_run_delay_minutes":
                    float(
                        wait_minutes
                    ),

                "latent_pre_run_delay_seconds":
                    wait_seconds,

                "scenario_source":
                    "EXPLICIT_SENSITIVITY_ASSUMPTION",

                "historically_observed_queue_wait":
                    False,

                "scenario_semantics":
                    (
                        "WITHDRAW_TO_TIMED_RUN_START;"
                        "INCLUDES_QUEUE_STAGING_RELEASE"
                    ),

                "queue_wait_claim":
                    "NONE",

                "allowed_use":
                    (
                        "OUTER_SENSITIVITY_SCENARIO_FOR_"
                        "MONTE_CARLO"
                    ),

                "forbidden_use":
                    (
                        "DO_NOT_REPORT_AS_ESTIMATED_"
                        "HISTORICAL_QUEUE_WAIT"
                    ),

                "median_run_duration_seconds":
                    median_run_seconds,

                "q95_run_duration_seconds":
                    q95_run_seconds,

                "median_withdraw_to_completion_seconds":
                    (
                        wait_seconds
                        + median_run_seconds
                    ),

                "q95_withdraw_to_completion_seconds":
                    (
                        wait_seconds
                        + q95_run_seconds
                    ),

                "median_withdraw_to_completion_minutes":
                    (
                        wait_seconds
                        + median_run_seconds
                    )
                    / 60.0,

                "q95_withdraw_to_completion_minutes":
                    (
                        wait_seconds
                        + q95_run_seconds
                    )
                    / 60.0,

                "policy_hash":
                    policy_hash,
            }
        )

    scenarios = pd.DataFrame(
        scenario_rows
    )

    # ========================================================
    # Latest withdraw references for 2024
    #
    # These are mathematical references conditional on the
    # sensitivity scenario — not claims about actual strategy.
    # ========================================================

    latest_rows = []

    for _, scenario in (
        scenarios.iterrows()
    ):

        wait_seconds = float(
            scenario[
                "latent_pre_run_delay_seconds"
            ]
        )

        for (
            run_label,
            run_seconds,
        ) in run_duration_values.items():

            completion_seconds = (
                wait_seconds
                + run_seconds
            )

            latest_withdraw = (
                EXPECTED_2024_CUTOFF_UTC
                - pd.to_timedelta(
                    completion_seconds,
                    unit="s",
                )
            )

            latest_rows.append(
                {
                    "year":
                        2024,

                    "scenario_id":
                        scenario[
                            "scenario_id"
                        ],

                    "latent_pre_run_delay_minutes":
                        scenario[
                            "latent_pre_run_delay_minutes"
                        ],

                    "run_duration_reference":
                        run_label,

                    "run_duration_seconds":
                        run_seconds,

                    "withdraw_to_completion_seconds":
                        completion_seconds,

                    "withdraw_to_completion_minutes":
                        completion_seconds
                        / 60.0,

                    "session_cutoff_utc":
                        EXPECTED_2024_CUTOFF_UTC
                        .isoformat(),

                    "latest_withdraw_time_utc":
                        latest_withdraw
                        .isoformat(),

                    "interpretation":
                        (
                            "CONDITIONAL_LATEST_WITHDRAW_REFERENCE;"
                            "NOT_HISTORICAL_DECISION_TIME"
                        ),

                    "policy_hash":
                        policy_hash,
                }
            )

    latest_withdraw = pd.DataFrame(
        latest_rows
    )

    # ========================================================
    # Cutoff feasibility grid
    #
    # Deterministic outer sensitivity:
    #
    # feasible if:
    #
    # time remaining >= assumed latent wait + run duration
    #
    # We calculate multiple run-duration references.
    # ========================================================

    cutoff_rows = []

    for time_remaining_minutes in (
        TIME_REMAINING_GRID_MINUTES
    ):

        available_seconds = float(
            time_remaining_minutes
            * 60
        )

        decision_time = (
            EXPECTED_2024_CUTOFF_UTC
            - pd.to_timedelta(
                time_remaining_minutes,
                unit="m",
            )
        )

        for _, scenario in (
            scenarios.iterrows()
        ):

            wait_seconds = float(
                scenario[
                    "latent_pre_run_delay_seconds"
                ]
            )

            for (
                run_label,
                run_seconds,
            ) in run_duration_values.items():

                required_seconds = (
                    wait_seconds
                    + run_seconds
                )

                margin_seconds = (
                    available_seconds
                    - required_seconds
                )

                feasible = (
                    margin_seconds >= 0
                )

                cutoff_rows.append(
                    {
                        "year":
                            2024,

                        "decision_time_utc":
                            decision_time
                            .isoformat(),

                        "time_remaining_minutes":
                            float(
                                time_remaining_minutes
                            ),

                        "scenario_id":
                            scenario[
                                "scenario_id"
                            ],

                        "latent_pre_run_delay_minutes":
                            scenario[
                                "latent_pre_run_delay_minutes"
                            ],

                        "run_duration_reference":
                            run_label,

                        "run_duration_seconds":
                            run_seconds,

                        "required_withdraw_to_completion_seconds":
                            required_seconds,

                        "required_withdraw_to_completion_minutes":
                            required_seconds
                            / 60.0,

                        "cutoff_margin_seconds":
                            margin_seconds,

                        "cutoff_margin_minutes":
                            margin_seconds
                            / 60.0,

                        "completion_before_cutoff":
                            bool(
                                feasible
                            ),

                        "failure_state_if_not_feasible":
                            (
                                "NO_COMPLETED_RERUN_BEFORE_CUTOFF"
                                if not feasible
                                else "NONE"
                            ),

                        "session_cutoff_utc":
                            EXPECTED_2024_CUTOFF_UTC
                            .isoformat(),

                        "historical_queue_wait_claim":
                            False,

                        "policy_hash":
                            policy_hash,
                    }
                )

    cutoff_grid = pd.DataFrame(
        cutoff_rows
    )

    # ========================================================
    # Compact scenario summary
    # ========================================================

    scenario_print = scenarios[
        [
            "scenario_id",
            "latent_pre_run_delay_minutes",
            "median_withdraw_to_completion_minutes",
            "q95_withdraw_to_completion_minutes",
        ]
    ].copy()

    # ========================================================
    # Critical time remaining by scenario
    # ========================================================

    critical_rows = []

    for _, scenario in (
        scenarios.iterrows()
    ):

        wait_seconds = float(
            scenario[
                "latent_pre_run_delay_seconds"
            ]
        )

        critical_rows.append(
            {
                "scenario_id":
                    scenario[
                        "scenario_id"
                    ],

                "wait_minutes":
                    scenario[
                        "latent_pre_run_delay_minutes"
                    ],

                "minimum_time_remaining_for_median_run_minutes":
                    (
                        wait_seconds
                        + median_run_seconds
                    )
                    / 60.0,

                "minimum_time_remaining_for_q95_run_minutes":
                    (
                        wait_seconds
                        + q95_run_seconds
                    )
                    / 60.0,
            }
        )

    critical = pd.DataFrame(
        critical_rows
    )

    # ========================================================
    # QA
    # ========================================================

    expected_grid_rows = (
        len(
            WAIT_SCENARIOS_MINUTES
        )
        * len(
            TIME_REMAINING_GRID_MINUTES
        )
        * len(
            RUN_DURATION_QUANTILES
        )
    )

    expected_latest_rows = (
        len(
            WAIT_SCENARIOS_MINUTES
        )
        * len(
            RUN_DURATION_QUANTILES
        )
    )

    checks = {
        "queue_policy_phase6a_compatible":
            True,

        "2024_exact_cutoff_confirmed":
            exact_cutoff_found,

        "wait_scenario_count_equal_4":
            len(
                scenarios
            )
            == 4,

        "all_wait_scenarios_marked_assumptions":
            (
                scenarios[
                    "scenario_source"
                ]
                == "EXPLICIT_SENSITIVITY_ASSUMPTION"
            ).all(),

        "no_wait_scenario_marked_historically_observed":
            (
                scenarios[
                    "historically_observed_queue_wait"
                ]
                == False
            ).all(),

        "median_run_duration_positive":
            median_run_seconds
            > 0,

        "q95_run_duration_ge_median":
            q95_run_seconds
            >= median_run_seconds,

        "cutoff_grid_rows_match_expected":
            len(
                cutoff_grid
            )
            == expected_grid_rows,

        "latest_withdraw_rows_match_expected":
            len(
                latest_withdraw
            )
            == expected_latest_rows,

        "all_infeasible_rows_have_failure_state":
            (
                cutoff_grid.loc[
                    ~cutoff_grid[
                        "completion_before_cutoff"
                    ],
                    "failure_state_if_not_feasible",
                ]
                == "NO_COMPLETED_RERUN_BEFORE_CUTOFF"
            ).all(),

        "all_feasible_rows_have_no_failure_state":
            (
                cutoff_grid.loc[
                    cutoff_grid[
                        "completion_before_cutoff"
                    ],
                    "failure_state_if_not_feasible",
                ]
                == "NONE"
            ).all(),

        "all_policy_hashes_present":
            (
                scenarios[
                    "policy_hash"
                ].notna().all()
                and
                cutoff_grid[
                    "policy_hash"
                ].notna().all()
                and
                latest_withdraw[
                    "policy_hash"
                ].notna().all()
            ),
    }

    qa_rows = []

    for (
        metric,
        passed,
    ) in checks.items():

        qa_rows.append(
            {
                "metric":
                    metric,

                "value":
                    int(
                        bool(
                            passed
                        )
                    ),

                "status":
                    (
                        "PASS"
                        if passed
                        else "FAIL"
                    ),
            }
        )

    qa_rows.extend(
        [
            {
                "metric":
                    "median_run_duration_seconds",

                "value":
                    median_run_seconds,

                "status":
                    "INFO",
            },

            {
                "metric":
                    "q95_run_duration_seconds",

                "value":
                    q95_run_seconds,

                "status":
                    "INFO",
            },

            {
                "metric":
                    "wait_scenarios_minutes",

                "value":
                    ",".join(
                        str(x)
                        for x
                        in WAIT_SCENARIOS_MINUTES
                    ),

                "status":
                    "INFO",
            },

            {
                "metric":
                    "time_remaining_grid_minutes",

                "value":
                    ",".join(
                        str(x)
                        for x
                        in TIME_REMAINING_GRID_MINUTES
                    ),

                "status":
                    "INFO",
            },

            {
                "metric":
                    "cutoff_grid_rows",

                "value":
                    len(
                        cutoff_grid
                    ),

                "status":
                    "INFO",
            },

            {
                "metric":
                    "latest_withdraw_rows",

                "value":
                    len(
                        latest_withdraw
                    ),

                "status":
                    "INFO",
            },

            {
                "metric":
                    "policy_hash",

                "value":
                    policy_hash,

                "status":
                    "INFO",
            },
        ]
    )

    qa = pd.DataFrame(
        qa_rows
    )

    all_pass = all(
        checks.values()
    )

    # ========================================================
    # PRINT
    # ========================================================

    print()
    print("WAIT SENSITIVITY SCENARIOS")
    print("-" * 120)

    print(
        scenario_print.to_string(
            index=False
        )
    )

    print()
    print(
        "IMPORTANT: wait values are scenario assumptions, "
        "not historical queue-wait estimates."
    )

    print()
    print("CRITICAL TIME REMAINING")
    print("-" * 120)

    print(
        critical.to_string(
            index=False
        )
    )

    print()
    print("2024 LATEST WITHDRAW REFERENCES")
    print("-" * 150)

    print(
        latest_withdraw[
            [
                "scenario_id",
                "run_duration_reference",
                "withdraw_to_completion_minutes",
                "latest_withdraw_time_utc",
            ]
        ]
        .to_string(
            index=False
        )
    )

    print()
    print("CUTOFF FEASIBILITY — Q95 RUN DURATION")
    print("-" * 150)

    q95_grid = cutoff_grid[
        cutoff_grid[
            "run_duration_reference"
        ]
        == "Q95"
    ].copy()

    q95_print = q95_grid[
        [
            "time_remaining_minutes",
            "scenario_id",
            "required_withdraw_to_completion_minutes",
            "cutoff_margin_minutes",
            "completion_before_cutoff",
            "failure_state_if_not_feasible",
        ]
    ].copy()

    print(
        q95_print.to_string(
            index=False
        )
    )

    print()
    print("QA")
    print("-" * 130)

    print(
        qa.to_string(
            index=False
        )
    )

    # ========================================================
    # WRITE
    # ========================================================

    WAIT_SCENARIO_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    scenarios.to_csv(
        WAIT_SCENARIO_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    cutoff_grid.to_csv(
        CUTOFF_GRID_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    latest_withdraw.to_csv(
        LATEST_WITHDRAW_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    qa.to_csv(
        QA_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    # ========================================================
    # REPORT
    # ========================================================

    report = []

    report.append(
        "# Queue / Wait Sensitivity Scenarios V1"
    )

    report.append("")

    report.append(
        f"Policy version: `{POLICY_VERSION}`"
    )

    report.append(
        f"Policy hash: `{policy_hash}`"
    )

    report.append("")

    report.append(
        "## Central rule"
    )

    report.append("")

    report.append(
        "Historical individual queue waiting time is unobserved."
    )

    report.append(
        "Therefore V1 does not fit or claim a historical "
        "queue-wait distribution."
    )

    report.append("")

    report.append(
        "Instead, the simulator will sweep explicit latent "
        "pre-run-delay scenarios."
    )

    report.append("")

    report.append(
        "## Wait scenarios"
    )

    report.append("")

    for minutes in WAIT_SCENARIOS_MINUTES:

        report.append(
            f"- `{minutes} minutes`"
        )

    report.append("")

    report.append(
        "Each scenario represents the time from withdrawal "
        "until the timed run begins and therefore includes "
        "queue, staging, and release overhead."
    )

    report.append("")

    report.append(
        "These values are assumptions for sensitivity analysis, "
        "not historical estimates."
    )

    report.append("")

    report.append(
        "## Timed-run duration"
    )

    report.append("")

    report.append(
        f"- Median complete four-lap run: "
        f"`{median_run_seconds:.3f} s`"
    )

    report.append(
        f"- Q95 complete four-lap run: "
        f"`{q95_run_seconds:.3f} s`"
    )

    report.append("")

    report.append(
        "Withdraw-to-completion time is defined as "
        "latent pre-run delay plus timed-run duration."
    )

    report.append("")

    report.append(
        "## Cutoff"
    )

    report.append("")

    report.append(
        "2024 uses the exact supported session cutoff "
        "`2024-05-18 21:50 UTC`."
    )

    report.append("")

    report.append(
        "If required withdraw-to-completion time exceeds "
        "time remaining, the branch becomes the explicit "
        "`NO_COMPLETED_RERUN_BEFORE_CUTOFF` outcome."
    )

    report.append("")

    report.append(
        "## Important boundary"
    )

    report.append("")

    report.append(
        "- No queue position is inferred."
    )

    report.append(
        "- No queue wait is estimated from attempt spacing."
    )

    report.append(
        "- No stochastic queue distribution is fitted."
    )

    report.append(
        "- No Monte Carlo performance draw is made yet."
    )

    report.append(
        "- Latest-withdraw timestamps are conditional "
        "scenario references, not reconstructed historical decisions."
    )

    report.append("")

    report.append(
        "## Next phase"
    )

    report.append("")

    report.append(
        "Phase 6C may combine these wait scenarios with "
        "the frozen repeat-performance empirical uncertainty "
        "to build the first retain/withdraw Monte Carlo engine."
    )

    report.append("")

    report.append(
        "## Status"
    )

    report.append("")

    if all_pass:

        report.append(
            "**QUEUE_WAIT_SENSITIVITY_SCENARIOS_READY**"
        )

    else:

        report.append(
            "**REVIEW_REQUIRED**"
        )

    REPORT_FILE.write_text(
        "\n".join(
            report
        ),
        encoding="utf-8",
    )

    # ========================================================
    # FINAL
    # ========================================================

    print()
    print("=" * 100)

    if all_pass:

        print(
            "FINAL STATUS: "
            "QUEUE_WAIT_SENSITIVITY_SCENARIOS_READY"
        )

    else:

        print(
            "FINAL STATUS: REVIEW_REQUIRED"
        )

    print("=" * 100)

    print()
    print(
        "NO QUEUE-WAIT DISTRIBUTION WAS FITTED."
    )

    print(
        "WAIT VALUES REMAIN EXPLICIT "
        "SENSITIVITY ASSUMPTIONS."
    )

    print(
        "NO RETAIN/WITHDRAW MONTE CARLO "
        "WAS RUN YET."
    )

    print()
    print("OUTPUTS")

    print(
        WAIT_SCENARIO_FILE
    )

    print(
        CUTOFF_GRID_FILE
    )

    print(
        LATEST_WITHDRAW_FILE
    )

    print(
        QA_FILE
    )

    print(
        REPORT_FILE
    )


if __name__ == "__main__":
    main()
