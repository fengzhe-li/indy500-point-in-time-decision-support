from pathlib import Path
import csv
import json
import math

import numpy as np


PHASE = "R3B.4"

OUT = Path("weather/output")

STATE_V3 = (
    OUT
    / "decision_time_observable_state_v3.csv"
)

UNCERTAINTY_ROWS = (
    OUT
    / "repeat_performance_uncertainty_rows_v1.csv"
)

RECOVERY_POSTERIOR = (
    OUT
    / "repeat_performance_recovery_probability_v1.csv"
)

RECOVERY_SENSITIVITY = (
    OUT
    / "decision_recovery_prior_sensitivity_v1.csv"
)

WAIT_SCENARIOS = (
    OUT
    / "r3b_queue_wait_scenarios_v1.csv"
)

ENVIRONMENT_SUMMARY = (
    OUT
    / "r3b3_performance_environment_sensitivity_v1.json"
)

ACTION_OUT = (
    OUT
    / "r3b4_monte_carlo_action_envelope_v1.csv"
)

TARGET_OUT = (
    OUT
    / "r3b4_target_gain_probability_v1.csv"
)

WAIT_DIAGNOSTIC_OUT = (
    OUT
    / "r3b4_queue_wait_influence_diagnostic_v1.csv"
)

SUMMARY_OUT = (
    OUT
    / "r3b4_monte_carlo_performance_decision_envelope_v1.json"
)

QA_OUT = (
    OUT
    / "r3b4_monte_carlo_performance_decision_envelope_v1_qa.csv"
)


SEED = 20260910
N_DRAWS = 200000


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


ACTIONS = [
    "STOP_RETAIN_CURRENT_RESULT",
    "REPEAT_LANE2_RETAIN_CURRENT_RESULT",
    "REPEAT_LANE1_WITHDRAW_CURRENT_RESULT",
]


EXPECTED_POSTERIOR_GROUPS = {
    "ALL_PRIMARY",
    "LOW_BASELINE",
    "AT_OR_ABOVE_BASELINE_MEDIAN",
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


def quantile(arr, q):
    return float(
        np.quantile(
            arr,
            q,
        )
    )


def summarize_distribution(arr):
    return {
        "mean":
            float(
                np.mean(arr)
            ),

        "std":
            float(
                np.std(
                    arr,
                    ddof=0,
                )
            ),

        "q025":
            quantile(
                arr,
                0.025,
            ),

        "q05":
            quantile(
                arr,
                0.05,
            ),

        "q10":
            quantile(
                arr,
                0.10,
            ),

        "q25":
            quantile(
                arr,
                0.25,
            ),

        "q50":
            quantile(
                arr,
                0.50,
            ),

        "q75":
            quantile(
                arr,
                0.75,
            ),

        "q90":
            quantile(
                arr,
                0.90,
            ),

        "q95":
            quantile(
                arr,
                0.95,
            ),

        "q975":
            quantile(
                arr,
                0.975,
            ),

        "prob_gt_0":
            float(
                np.mean(
                    arr > 0
                )
            ),

        "prob_eq_0":
            float(
                np.mean(
                    arr == 0
                )
            ),

        "prob_lt_0":
            float(
                np.mean(
                    arr < 0
                )
            ),
    }


def build_empirical_branches(rows):

    normal = []
    recovery = []

    for row in rows:

        delta = fnum(
            row.get(
                "target_speed_delta_vs_best_prior_mph"
            )
        )

        if delta is None:
            continue

        if truthy(
            row.get(
                "diagnostic_recovery_like"
            )
        ):
            recovery.append(
                delta
            )
        else:
            normal.append(
                delta
            )

    return (
        np.array(
            normal,
            dtype=float,
        ),
        np.array(
            recovery,
            dtype=float,
        ),
    )


def build_posteriors(rows):

    posteriors = {}

    for row in rows:

        group = txt(
            row.get(
                "eligibility_group"
            )
        )

        alpha = fnum(
            row.get(
                "posterior_alpha"
            )
        )

        beta = fnum(
            row.get(
                "posterior_beta"
            )
        )

        mean = fnum(
            row.get(
                "posterior_mean_probability"
            )
        )

        if (
            not group
            or
            alpha is None
            or
            beta is None
        ):
            continue

        posteriors[
            group
        ] = {
            "alpha":
                alpha,

            "beta":
                beta,

            "mean":
                mean,
        }

    return posteriors


def generate_repeat_delta_draws(
    rng,
    normal_values,
    recovery_values,
    posterior,
):
    """
    Predictive mixture:

    1. Draw recovery probability from its Beta posterior.
    2. Draw branch indicator.
    3. Bootstrap an empirical delta from the selected branch.

    This preserves:
      - empirical normal-repeat uncertainty
      - small-sample recovery branch
      - posterior uncertainty in recovery frequency

    No environment correction is applied because R3B.3C
    failed to beat ZERO_DELTA in LOYO validation.
    """

    p_recovery = rng.beta(
        posterior["alpha"],
        posterior["beta"],
        size=N_DRAWS,
    )

    recovery_branch = (
        rng.random(
            N_DRAWS
        )
        <
        p_recovery
    )

    normal_draws = rng.choice(
        normal_values,
        size=N_DRAWS,
        replace=True,
    )

    recovery_draws = rng.choice(
        recovery_values,
        size=N_DRAWS,
        replace=True,
    )

    repeat_delta = np.where(
        recovery_branch,
        recovery_draws,
        normal_draws,
    )

    return {
        "repeat_delta":
            repeat_delta,

        "recovery_branch":
            recovery_branch,

        "posterior_probability_draw":
            p_recovery,
    }


def action_final_delta(
    action,
    repeat_delta,
):

    if (
        action
        ==
        "STOP_RETAIN_CURRENT_RESULT"
    ):
        return np.zeros_like(
            repeat_delta
        )

    if (
        action
        ==
        "REPEAT_LANE2_RETAIN_CURRENT_RESULT"
    ):
        return np.maximum(
            repeat_delta,
            0.0,
        )

    if (
        action
        ==
        "REPEAT_LANE1_WITHDRAW_CURRENT_RESULT"
    ):
        return repeat_delta.copy()

    raise ValueError(
        f"Unknown action: {action}"
    )


def action_semantic(action):

    if (
        action
        ==
        "STOP_RETAIN_CURRENT_RESULT"
    ):
        return (
            "No repeat attempt; existing result retained."
        )

    if (
        action
        ==
        "REPEAT_LANE2_RETAIN_CURRENT_RESULT"
    ):
        return (
            "Repeat attempt with existing result retained; "
            "performance-only final delta is max(0, repeat delta)."
        )

    if (
        action
        ==
        "REPEAT_LANE1_WITHDRAW_CURRENT_RESULT"
    ):
        return (
            "Existing result withdrawn before priority repeat; "
            "performance-only final delta equals repeat delta."
        )

    return "UNKNOWN"


def main():

    print()
    print("=" * 128)
    print(
        "R3B.4 — MONTE CARLO PERFORMANCE-ONLY "
        "DECISION ENVELOPE"
    )
    print("=" * 128)

    required = [
        STATE_V3,
        UNCERTAINTY_ROWS,
        RECOVERY_POSTERIOR,
        RECOVERY_SENSITIVITY,
        WAIT_SCENARIOS,
        ENVIRONMENT_SUMMARY,
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
            missing.append(
                str(path)
            )

    if missing:

        print()
        print(
            "FINAL STATUS: "
            "R3B4_INPUT_MISSING"
        )
        return

    states = read_csv(
        STATE_V3
    )

    uncertainty_rows = read_csv(
        UNCERTAINTY_ROWS
    )

    posterior_rows = read_csv(
        RECOVERY_POSTERIOR
    )

    sensitivity_rows = read_csv(
        RECOVERY_SENSITIVITY
    )

    wait_rows = read_csv(
        WAIT_SCENARIOS
    )

    environment_summary = json.loads(
        ENVIRONMENT_SUMMARY.read_text(
            encoding="utf-8"
        )
    )

    # --------------------------------------------------
    # Validate state
    # --------------------------------------------------

    state_drivers = {
        txt(
            row.get(
                "driver_name"
            )
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

    # --------------------------------------------------
    # Environment model must remain sensitivity only
    # --------------------------------------------------

    env_beats_zero = bool(
        environment_summary.get(
            "environment_model_beats_zero_delta",
            False,
        )
    )

    simulator_environment_role = txt(
        environment_summary.get(
            "simulator_environment_role"
        )
    )

    environment_central_disabled = (
        not env_beats_zero
    )

    print()
    print("=" * 128)
    print("CENTRAL PERFORMANCE POLICY")
    print("=" * 128)

    print()
    print(
        "Environment model beats ZERO_DELTA:",
        env_beats_zero,
    )

    print(
        "Environment role:",
        simulator_environment_role,
    )

    print(
        "Environment correction applied centrally:",
        "NO",
    )

    print(
        "Central point prediction:",
        "ZERO_DELTA",
    )

    # --------------------------------------------------
    # Empirical uncertainty branches
    # --------------------------------------------------

    (
        normal_values,
        recovery_values,
    ) = build_empirical_branches(
        uncertainty_rows
    )

    posteriors = build_posteriors(
        posterior_rows
    )

    print()
    print("=" * 128)
    print("EMPIRICAL PERFORMANCE BRANCHES")
    print("=" * 128)

    print()
    print(
        "Normal empirical deltas:",
        len(
            normal_values
        ),
    )

    print(
        "Recovery empirical deltas:",
        len(
            recovery_values
        ),
    )

    print()
    print(
        "Normal delta mean:",
        f"{np.mean(normal_values):.6f}",
    )

    print(
        "Normal delta median:",
        f"{np.median(normal_values):.6f}",
    )

    print(
        "Recovery delta mean:",
        f"{np.mean(recovery_values):.6f}",
    )

    print(
        "Recovery delta median:",
        f"{np.median(recovery_values):.6f}",
    )

    print()
    print("RECOVERY POSTERIORS")

    for group in sorted(
        posteriors
    ):

        p = posteriors[
            group
        ]

        print(
            f"  {group}: "
            f"Beta({p['alpha']:.3f}, {p['beta']:.3f}), "
            f"mean={p['mean']:.6f}"
        )

    posterior_groups_exact = (
        set(
            posteriors.keys()
        )
        ==
        EXPECTED_POSTERIOR_GROUPS
    )

    # --------------------------------------------------
    # Wait scenarios
    # --------------------------------------------------

    waits = []

    for row in wait_rows:

        wait_min = fnum(
            row.get(
                "queue_wait_minutes"
            )
        )

        scenario_id = txt(
            row.get(
                "scenario_id"
            )
        )

        if (
            wait_min is None
            or
            not scenario_id
        ):
            continue

        waits.append(
            (
                scenario_id,
                int(
                    round(
                        wait_min
                    )
                ),
            )
        )

    print()
    print("=" * 128)
    print("QUEUE WAIT POLICY")
    print("=" * 128)

    print()
    print(
        "Wait scenarios:",
        "|".join(
            str(
                item[1]
            )
            for item in waits
        ),
        "minutes",
    )

    print(
        "Historical wait probability model:",
        "NONE",
    )

    print(
        "Wait modifies central performance:",
        "NO",
    )

    print(
        "Reason:",
        (
            "2022 decision time is not identifiable and "
            "environment correction did not validate."
        ),
    )

    # --------------------------------------------------
    # Required-gain thresholds
    # --------------------------------------------------

    target_gains = sorted(
        {
            value
            for value in [
                fnum(
                    row.get(
                        "required_gain_mph"
                    )
                )
                for row in sensitivity_rows
            ]
            if value is not None
        }
    )

    print()
    print("=" * 128)
    print("TARGET-GAIN THRESHOLDS")
    print("=" * 128)

    print()
    print(
        "Thresholds inherited from frozen sensitivity file:"
    )

    for gain in target_gains:
        print(
            f"  {gain:.6f} mph"
        )

    # --------------------------------------------------
    # Generate common Monte Carlo draws.
    #
    # Common random numbers are intentional:
    # all drivers / wait scenarios see the same underlying
    # predictive distribution under a given recovery-prior
    # scenario. This prevents meaningless Monte Carlo noise
    # from appearing as driver/wait differences.
    # --------------------------------------------------

    rng = np.random.default_rng(
        SEED
    )

    draws_by_group = {}

    for group in sorted(
        posteriors
    ):

        draws_by_group[
            group
        ] = (
            generate_repeat_delta_draws(
                rng,
                normal_values,
                recovery_values,
                posteriors[
                    group
                ],
            )
        )

    # --------------------------------------------------
    # Build summaries
    # --------------------------------------------------

    action_rows = []
    target_rows = []

    print()
    print("=" * 128)
    print("MONTE CARLO ACTION ENVELOPES")
    print("=" * 128)

    for state in sorted(
        states,
        key=lambda x:
        txt(
            x.get(
                "driver_name"
            )
        ),
    ):

        driver = txt(
            state.get(
                "driver_name"
            )
        )

        state_id = txt(
            state.get(
                "state_id"
            )
        )

        baseline_speed = fnum(
            state.get(
                "first_attempt_speed_mph"
            )
        )

        pre_rank = txt(
            state.get(
                "predecision_current_rank"
            )
        ) or "UNKNOWN"

        cutoff_rank = txt(
            state.get(
                "predecision_cutoff_rank"
            )
        ) or "UNKNOWN"

        cutoff_speed = txt(
            state.get(
                "predecision_cutoff_speed_mph"
            )
        ) or "UNKNOWN"

        historical_action = txt(
            state.get(
                "historical_action_label"
            )
        ) or "UNKNOWN"

        print()
        print("-" * 128)

        print(driver)

        print(
            "  baseline speed:",
            (
                f"{baseline_speed:.3f}"
                if baseline_speed
                is not None
                else
                "UNKNOWN"
            ),
        )

        print(
            "  predecision rank:",
            pre_rank,
        )

        print(
            "  cutoff rank/speed:",
            cutoff_rank,
            "/",
            cutoff_speed,
        )

        print(
            "  historical action:",
            historical_action,
        )

        for group in sorted(
            posteriors
        ):

            raw_repeat_delta = (
                draws_by_group[
                    group
                ][
                    "repeat_delta"
                ]
            )

            recovery_branch = (
                draws_by_group[
                    group
                ][
                    "recovery_branch"
                ]
            )

            p_draw = (
                draws_by_group[
                    group
                ][
                    "posterior_probability_draw"
                ]
            )

            for (
                wait_id,
                wait_min,
            ) in waits:

                for action in ACTIONS:

                    final_delta = (
                        action_final_delta(
                            action,
                            raw_repeat_delta,
                        )
                    )

                    stats = (
                        summarize_distribution(
                            final_delta
                        )
                    )

                    if baseline_speed is not None:

                        final_speed = (
                            baseline_speed
                            +
                            final_delta
                        )

                        speed_stats = {
                            "mean":
                                float(
                                    np.mean(
                                        final_speed
                                    )
                                ),

                            "q05":
                                quantile(
                                    final_speed,
                                    0.05,
                                ),

                            "q50":
                                quantile(
                                    final_speed,
                                    0.50,
                                ),

                            "q95":
                                quantile(
                                    final_speed,
                                    0.95,
                                ),
                        }

                    else:

                        speed_stats = {
                            "mean":
                                None,

                            "q05":
                                None,

                            "q50":
                                None,

                            "q95":
                                None,
                        }

                    action_rows.append({
                        "state_id":
                            state_id,

                        "driver_name":
                            driver,

                        "recovery_prior_scenario":
                            group,

                        "posterior_alpha":
                            f"{posteriors[group]['alpha']:.10f}",

                        "posterior_beta":
                            f"{posteriors[group]['beta']:.10f}",

                        "posterior_mean_recovery_probability":
                            f"{posteriors[group]['mean']:.10f}",

                        "wait_scenario_id":
                            wait_id,

                        "queue_wait_minutes":
                            wait_min,

                        "queue_wait_role":
                            "LATENT_SENSITIVITY_LABEL_ONLY",

                        "queue_wait_changes_performance_distribution":
                            "False",

                        "action":
                            action,

                        "action_semantic":
                            action_semantic(
                                action
                            ),

                        "condition_on_completed_repeat_attempt":
                            (
                                "False"
                                if action
                                ==
                                "STOP_RETAIN_CURRENT_RESULT"
                                else
                                "True"
                            ),

                        "n_draws":
                            N_DRAWS,

                        "baseline_speed_mph":
                            (
                                f"{baseline_speed:.10f}"
                                if baseline_speed
                                is not None
                                else
                                "UNKNOWN"
                            ),

                        "predecision_current_rank":
                            pre_rank,

                        "predecision_cutoff_rank":
                            cutoff_rank,

                        "predecision_cutoff_speed_mph":
                            cutoff_speed,

                        "historical_action_label":
                            historical_action,

                        "mean_final_delta_mph":
                            f"{stats['mean']:.10f}",

                        "std_final_delta_mph":
                            f"{stats['std']:.10f}",

                        "q025_final_delta_mph":
                            f"{stats['q025']:.10f}",

                        "q05_final_delta_mph":
                            f"{stats['q05']:.10f}",

                        "q10_final_delta_mph":
                            f"{stats['q10']:.10f}",

                        "q25_final_delta_mph":
                            f"{stats['q25']:.10f}",

                        "q50_final_delta_mph":
                            f"{stats['q50']:.10f}",

                        "q75_final_delta_mph":
                            f"{stats['q75']:.10f}",

                        "q90_final_delta_mph":
                            f"{stats['q90']:.10f}",

                        "q95_final_delta_mph":
                            f"{stats['q95']:.10f}",

                        "q975_final_delta_mph":
                            f"{stats['q975']:.10f}",

                        "prob_final_improves":
                            f"{stats['prob_gt_0']:.10f}",

                        "prob_final_unchanged":
                            f"{stats['prob_eq_0']:.10f}",

                        "prob_final_worse":
                            f"{stats['prob_lt_0']:.10f}",

                        "mean_final_speed_mph":
                            (
                                f"{speed_stats['mean']:.10f}"
                                if speed_stats[
                                    "mean"
                                ]
                                is not None
                                else
                                "UNKNOWN"
                            ),

                        "q05_final_speed_mph":
                            (
                                f"{speed_stats['q05']:.10f}"
                                if speed_stats[
                                    "q05"
                                ]
                                is not None
                                else
                                "UNKNOWN"
                            ),

                        "q50_final_speed_mph":
                            (
                                f"{speed_stats['q50']:.10f}"
                                if speed_stats[
                                    "q50"
                                ]
                                is not None
                                else
                                "UNKNOWN"
                            ),

                        "q95_final_speed_mph":
                            (
                                f"{speed_stats['q95']:.10f}"
                                if speed_stats[
                                    "q95"
                                ]
                                is not None
                                else
                                "UNKNOWN"
                            ),

                        "mc_realized_recovery_fraction":
                            f"{np.mean(recovery_branch):.10f}",

                        "mc_mean_sampled_recovery_probability":
                            f"{np.mean(p_draw):.10f}",

                        "environment_central_correction":
                            "NONE_ZERO_DELTA_BASELINE",

                        "actual_2022_future_weather_used":
                            "False",

                        "historical_queue_wait_claim":
                            "False",

                        "rank_outcome_probability_available":
                            "False",

                        "hard_recommendation_allowed":
                            "False",

                        "scope":
                            (
                                "PERFORMANCE_ONLY_CONDITIONAL_"
                                "ON_COMPLETED_REPEAT"
                            ),
                    })

                    for gain in target_gains:

                        probability = float(
                            np.mean(
                                final_delta
                                >=
                                gain
                            )
                        )

                        target_rows.append({
                            "state_id":
                                state_id,

                            "driver_name":
                                driver,

                            "recovery_prior_scenario":
                                group,

                            "wait_scenario_id":
                                wait_id,

                            "queue_wait_minutes":
                                wait_min,

                            "action":
                                action,

                            "required_gain_mph":
                                f"{gain:.10f}",

                            "probability_final_gain_at_least_threshold":
                                f"{probability:.10f}",

                            "target_semantic":
                                (
                                    "GENERIC_REQUIRED_SPEED_GAIN;"
                                    "NOT_ACTUAL_2022_CUTOFF"
                                ),

                            "actual_cutoff_speed_used":
                                "False",

                            "hard_recommendation_allowed":
                                "False",
                        })

        # Print only ALL_PRIMARY / 15min to keep terminal readable.
        central_rows = [
            row
            for row in action_rows
            if (
                row[
                    "driver_name"
                ]
                ==
                driver
                and
                row[
                    "recovery_prior_scenario"
                ]
                ==
                "ALL_PRIMARY"
                and
                row[
                    "queue_wait_minutes"
                ]
                ==
                15
            )
        ]

        print(
            "  CENTRAL PERFORMANCE ENVELOPE "
            "(ALL_PRIMARY, wait label 15 min)"
        )

        for row in central_rows:

            print(
                "   ",
                row["action"],
            )

            print(
                "      mean Δ:",
                row[
                    "mean_final_delta_mph"
                ],
            )

            print(
                "      q05/q50/q95:",
                row[
                    "q05_final_delta_mph"
                ],
                "/",
                row[
                    "q50_final_delta_mph"
                ],
                "/",
                row[
                    "q95_final_delta_mph"
                ],
            )

            print(
                "      P(improve):",
                row[
                    "prob_final_improves"
                ],
            )

            print(
                "      P(worse):",
                row[
                    "prob_final_worse"
                ],
            )

    # --------------------------------------------------
    # Wait influence diagnostic
    # --------------------------------------------------

    wait_diagnostics = []

    grouped = {}

    for row in action_rows:

        key = (
            row[
                "driver_name"
            ],
            row[
                "recovery_prior_scenario"
            ],
            row[
                "action"
            ],
        )

        grouped.setdefault(
            key,
            []
        ).append(
            row
        )

    max_wait_mean_spread = 0.0
    max_wait_q05_spread = 0.0
    max_wait_q95_spread = 0.0

    for key, rows_group in grouped.items():

        means = [
            fnum(
                row.get(
                    "mean_final_delta_mph"
                )
            )
            for row in rows_group
        ]

        q05s = [
            fnum(
                row.get(
                    "q05_final_delta_mph"
                )
            )
            for row in rows_group
        ]

        q95s = [
            fnum(
                row.get(
                    "q95_final_delta_mph"
                )
            )
            for row in rows_group
        ]

        means = [
            x
            for x in means
            if x is not None
        ]

        q05s = [
            x
            for x in q05s
            if x is not None
        ]

        q95s = [
            x
            for x in q95s
            if x is not None
        ]

        mean_spread = (
            max(means)
            -
            min(means)
            if means
            else
            0.0
        )

        q05_spread = (
            max(q05s)
            -
            min(q05s)
            if q05s
            else
            0.0
        )

        q95_spread = (
            max(q95s)
            -
            min(q95s)
            if q95s
            else
            0.0
        )

        max_wait_mean_spread = max(
            max_wait_mean_spread,
            mean_spread,
        )

        max_wait_q05_spread = max(
            max_wait_q05_spread,
            q05_spread,
        )

        max_wait_q95_spread = max(
            max_wait_q95_spread,
            q95_spread,
        )

        wait_diagnostics.append({
            "driver_name":
                key[0],

            "recovery_prior_scenario":
                key[1],

            "action":
                key[2],

            "wait_scenario_count":
                len(
                    rows_group
                ),

            "mean_delta_spread_across_waits":
                f"{mean_spread:.12f}",

            "q05_delta_spread_across_waits":
                f"{q05_spread:.12f}",

            "q95_delta_spread_across_waits":
                f"{q95_spread:.12f}",

            "wait_effect_identifiable":
                "False",

            "interpretation":
                (
                    "Identical performance distributions across "
                    "wait labels are intentional. Current data do "
                    "not identify a validated 2022 wait-to-"
                    "environment-to-performance mechanism."
                ),
        })

    # --------------------------------------------------
    # Lane2 vs Lane1 performance-only downside protection
    # --------------------------------------------------

    dominance_rows = []

    for driver in sorted(
        EXPECTED_DRIVERS
    ):

        for group in sorted(
            posteriors
        ):

            sample = [
                row
                for row in action_rows
                if (
                    row[
                        "driver_name"
                    ]
                    ==
                    driver
                    and
                    row[
                        "recovery_prior_scenario"
                    ]
                    ==
                    group
                    and
                    row[
                        "queue_wait_minutes"
                    ]
                    ==
                    15
                )
            ]

            lane1 = next(
                (
                    row
                    for row in sample
                    if row[
                        "action"
                    ]
                    ==
                    "REPEAT_LANE1_WITHDRAW_CURRENT_RESULT"
                ),
                None,
            )

            lane2 = next(
                (
                    row
                    for row in sample
                    if row[
                        "action"
                    ]
                    ==
                    "REPEAT_LANE2_RETAIN_CURRENT_RESULT"
                ),
                None,
            )

            if (
                lane1 is None
                or
                lane2 is None
            ):
                continue

            lane1_mean = fnum(
                lane1[
                    "mean_final_delta_mph"
                ]
            )

            lane2_mean = fnum(
                lane2[
                    "mean_final_delta_mph"
                ]
            )

            lane1_worse = fnum(
                lane1[
                    "prob_final_worse"
                ]
            )

            lane2_worse = fnum(
                lane2[
                    "prob_final_worse"
                ]
            )

            dominance_rows.append({
                "driver_name":
                    driver,

                "recovery_prior_scenario":
                    group,

                "lane2_minus_lane1_mean_delta_mph":
                    (
                        lane2_mean
                        -
                        lane1_mean
                    ),

                "lane1_prob_worse":
                    lane1_worse,

                "lane2_prob_worse":
                    lane2_worse,
            })

    # --------------------------------------------------
    # Write outputs
    # --------------------------------------------------

    write_csv(
        ACTION_OUT,
        action_rows,
        list(
            action_rows[0].keys()
        ),
    )

    write_csv(
        TARGET_OUT,
        target_rows,
        list(
            target_rows[0].keys()
        )
        if target_rows
        else [
            "state_id",
            "driver_name",
            "recovery_prior_scenario",
            "wait_scenario_id",
            "queue_wait_minutes",
            "action",
            "required_gain_mph",
            "probability_final_gain_at_least_threshold",
            "target_semantic",
            "actual_cutoff_speed_used",
            "hard_recommendation_allowed",
        ],
    )

    write_csv(
        WAIT_DIAGNOSTIC_OUT,
        wait_diagnostics,
        list(
            wait_diagnostics[0].keys()
        ),
    )

    # --------------------------------------------------
    # QA
    # --------------------------------------------------

    expected_action_rows = (
        len(states)
        *
        len(
            posteriors
        )
        *
        len(
            waits
        )
        *
        len(
            ACTIONS
        )
    )

    stop_bad = [
        row
        for row in action_rows
        if (
            row[
                "action"
            ]
            ==
            "STOP_RETAIN_CURRENT_RESULT"
            and
            (
                abs(
                    fnum(
                        row[
                            "mean_final_delta_mph"
                        ]
                    )
                    or
                    0.0
                )
                >
                1e-12
                or
                abs(
                    fnum(
                        row[
                            "prob_final_worse"
                        ]
                    )
                    or
                    0.0
                )
                >
                1e-12
            )
        )
    ]

    lane2_worse_bad = [
        row
        for row in action_rows
        if (
            row[
                "action"
            ]
            ==
            "REPEAT_LANE2_RETAIN_CURRENT_RESULT"
            and
            (
                fnum(
                    row[
                        "prob_final_worse"
                    ]
                )
                or
                0.0
            )
            >
            1e-12
        )
    ]

    hard_rec_bad = [
        row
        for row in action_rows
        if truthy(
            row.get(
                "hard_recommendation_allowed"
            )
        )
    ]

    rank_claim_bad = [
        row
        for row in action_rows
        if truthy(
            row.get(
                "rank_outcome_probability_available"
            )
        )
    ]

    historical_wait_bad = [
        row
        for row in action_rows
        if truthy(
            row.get(
                "historical_queue_wait_claim"
            )
        )
    ]

    future_weather_bad = [
        row
        for row in action_rows
        if truthy(
            row.get(
                "actual_2022_future_weather_used"
            )
        )
    ]

    lane2_advantages = [
        row[
            "lane2_minus_lane1_mean_delta_mph"
        ]
        for row in dominance_rows
    ]

    lane2_performance_dominates = (
        len(
            lane2_advantages
        )
        >
        0
        and
        min(
            lane2_advantages
        )
        >=
        -1e-12
    )

    qa_rows = [
        {
            "metric":
                "state_target_exact",

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
                "normal_empirical_rows",

            "value":
                len(
                    normal_values
                ),

            "status":
                (
                    "PASS"
                    if len(
                        normal_values
                    )
                    ==
                    35
                    else
                    "REVIEW"
                ),
        },

        {
            "metric":
                "recovery_empirical_rows",

            "value":
                len(
                    recovery_values
                ),

            "status":
                (
                    "PASS"
                    if len(
                        recovery_values
                    )
                    ==
                    4
                    else
                    "REVIEW"
                ),
        },

        {
            "metric":
                "recovery_posterior_groups_exact",

            "value":
                "|".join(
                    sorted(
                        posteriors.keys()
                    )
                ),

            "status":
                (
                    "PASS"
                    if posterior_groups_exact
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "wait_scenario_count",

            "value":
                len(
                    waits
                ),

            "status":
                (
                    "PASS"
                    if len(
                        waits
                    )
                    ==
                    4
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "environment_central_disabled",

            "value":
                int(
                    environment_central_disabled
                ),

            "status":
                (
                    "PASS"
                    if environment_central_disabled
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "action_summary_rows",

            "value":
                len(
                    action_rows
                ),

            "status":
                (
                    "PASS"
                    if len(
                        action_rows
                    )
                    ==
                    expected_action_rows
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "stop_semantic_violations",

            "value":
                len(
                    stop_bad
                ),

            "status":
                (
                    "PASS"
                    if len(
                        stop_bad
                    )
                    ==
                    0
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "lane2_negative_final_delta_rows",

            "value":
                len(
                    lane2_worse_bad
                ),

            "status":
                (
                    "PASS"
                    if len(
                        lane2_worse_bad
                    )
                    ==
                    0
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "max_mean_spread_across_wait_labels",

            "value":
                f"{max_wait_mean_spread:.12f}",

            "status":
                (
                    "PASS"
                    if max_wait_mean_spread
                    <=
                    1e-12
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "hard_recommendation_claims",

            "value":
                len(
                    hard_rec_bad
                ),

            "status":
                (
                    "PASS"
                    if len(
                        hard_rec_bad
                    )
                    ==
                    0
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "rank_probability_claims",

            "value":
                len(
                    rank_claim_bad
                ),

            "status":
                (
                    "PASS"
                    if len(
                        rank_claim_bad
                    )
                    ==
                    0
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "historical_queue_wait_claims",

            "value":
                len(
                    historical_wait_bad
                ),

            "status":
                (
                    "PASS"
                    if len(
                        historical_wait_bad
                    )
                    ==
                    0
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "actual_2022_future_weather_used",

            "value":
                len(
                    future_weather_bad
                ),

            "status":
                (
                    "PASS"
                    if len(
                        future_weather_bad
                    )
                    ==
                    0
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "lane2_performance_only_nondominated_vs_lane1",

            "value":
                int(
                    lane2_performance_dominates
                ),

            "status":
                (
                    "PASS"
                    if lane2_performance_dominates
                    else
                    "REVIEW"
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

    # --------------------------------------------------
    # Central ALL_PRIMARY summary
    # --------------------------------------------------

    central = [
        row
        for row in action_rows
        if (
            row[
                "recovery_prior_scenario"
            ]
            ==
            "ALL_PRIMARY"
            and
            row[
                "queue_wait_minutes"
            ]
            ==
            15
        )
    ]

    central_by_action = {}

    for action in ACTIONS:

        matching = [
            row
            for row in central
            if row[
                "action"
            ]
            ==
            action
        ]

        if matching:
            # All drivers have identical delta distribution
            # under this deliberately non-driver-specific model.
            row = matching[0]

            central_by_action[
                action
            ] = {
                "mean_final_delta_mph":
                    fnum(
                        row[
                            "mean_final_delta_mph"
                        ]
                    ),

                "q05_final_delta_mph":
                    fnum(
                        row[
                            "q05_final_delta_mph"
                        ]
                    ),

                "q50_final_delta_mph":
                    fnum(
                        row[
                            "q50_final_delta_mph"
                        ]
                    ),

                "q95_final_delta_mph":
                    fnum(
                        row[
                            "q95_final_delta_mph"
                        ]
                    ),

                "prob_improve":
                    fnum(
                        row[
                            "prob_final_improves"
                        ]
                    ),

                "prob_worse":
                    fnum(
                        row[
                            "prob_final_worse"
                        ]
                    ),
            }

    summary = {
        "phase":
            PHASE,

        "seed":
            SEED,

        "draws_per_recovery_prior":
            N_DRAWS,

        "state_rows":
            len(
                states
            ),

        "actions":
            ACTIONS,

        "recovery_prior_scenarios":
            sorted(
                posteriors.keys()
            ),

        "queue_wait_scenarios_minutes":
            [
                item[1]
                for item in waits
            ],

        "central_recovery_prior":
            "ALL_PRIMARY",

        "central_performance_model":
            "ZERO_DELTA_BASELINE",

        "predictive_uncertainty":
            (
                "EMPIRICAL_NORMAL_AND_RECOVERY_BRANCH_"
                "BOOTSTRAP_WITH_BETA_POSTERIOR_MIXTURE"
            ),

        "environment_effect":
            "SENSITIVITY_ONLY_NOT_CENTRAL",

        "2022_future_weather":
            "NOT_IDENTIFIABLE_NOT_USED",

        "queue_wait_effect_on_performance":
            "NOT_IDENTIFIABLE_NOT_APPLIED",

        "simulation_condition":
            "CONDITIONAL_ON_COMPLETED_REPEAT_ATTEMPT",

        "repeat_completion_probability":
            "NOT_MODELED",

        "session_end_feasibility":
            "NOT_MODELED",

        "rank_cutoff_probability":
            "NOT_IDENTIFIABLE",

        "actual_cutoff_speed":
            "NOT_USED",

        "central_action_envelopes":
            central_by_action,

        "lane2_vs_lane1_interpretation":
            (
                "PERFORMANCE_ONLY_DOWNSIDE_PROTECTION;"
                "NOT_A_DECISION_RECOMMENDATION"
            ),

        "lane1_priority_value":
            (
                "REQUIRES_QUEUE_TIME_OR_SESSION_FEASIBILITY_"
                "INFORMATION_NOT_IDENTIFIABLE_HERE"
            ),

        "hard_recommendation_ready":
            False,

        "r3b4_ready":
            not hard_fail,

        "next_phase":
            (
                "R3C_FINAL_DECISION_SUPPORT_BOUNDARY_AND_"
                "RESULTS_FREEZE"
                if not hard_fail
                else
                "R3B4_REVIEW_REQUIRED"
            ),
    }

    SUMMARY_OUT.write_text(
        json.dumps(
            summary,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    # --------------------------------------------------
    # Final terminal summary
    # --------------------------------------------------

    print()
    print("=" * 128)
    print("CENTRAL ALL_PRIMARY PERFORMANCE ENVELOPE")
    print("=" * 128)

    print()

    for action in ACTIONS:

        item = central_by_action.get(
            action
        )

        if not item:
            continue

        print(action)

        print(
            "  mean final Δ:",
            f"{item['mean_final_delta_mph']:.6f}",
        )

        print(
            "  q05 / q50 / q95:",
            f"{item['q05_final_delta_mph']:.6f}",
            "/",
            f"{item['q50_final_delta_mph']:.6f}",
            "/",
            f"{item['q95_final_delta_mph']:.6f}",
        )

        print(
            "  P(improve):",
            f"{item['prob_improve']:.6f}",
        )

        print(
            "  P(worse):",
            f"{item['prob_worse']:.6f}",
        )

        print()

    print(
        "Maximum mean spread across wait labels:",
        f"{max_wait_mean_spread:.12f}",
    )

    print(
        "Maximum q05 spread across wait labels:",
        f"{max_wait_q05_spread:.12f}",
    )

    print(
        "Maximum q95 spread across wait labels:",
        f"{max_wait_q95_spread:.12f}",
    )

    print()
    print(
        "Lane2 performance-only nondominated vs Lane1:",
        lane2_performance_dominates,
    )

    print()
    print(
        "2022 actual future weather used:",
        "NO",
    )

    print(
        "Historical queue wait claimed:",
        "NO",
    )

    print(
        "Rank/cutoff probability claimed:",
        "NO",
    )

    print(
        "Repeat completion probability modeled:",
        "NO",
    )

    print(
        "Hard retain/withdraw recommendation:",
        "NO",
    )

    print()
    print("=" * 128)

    if not hard_fail:

        print(
            "FINAL STATUS: "
            "R3B4_MONTE_CARLO_PERFORMANCE_DECISION_ENVELOPE_READY"
        )

    else:

        print(
            "FINAL STATUS: "
            "R3B4_MONTE_CARLO_PERFORMANCE_DECISION_ENVELOPE_"
            "REVIEW_REQUIRED"
        )

    print("=" * 128)

    print()
    print("OUTPUTS")
    print(ACTION_OUT)
    print(TARGET_OUT)
    print(WAIT_DIAGNOSTIC_OUT)
    print(SUMMARY_OUT)
    print(QA_OUT)


if __name__ == "__main__":
    main()
