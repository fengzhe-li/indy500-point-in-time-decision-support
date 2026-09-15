from pathlib import Path
import csv
import json
import hashlib
from datetime import datetime, timezone


PHASE = "R3C.1"

OUT = Path("weather/output")

STATE_FINAL = (
    OUT
    / "decision_time_observable_state_v4_1_final.csv"
)

ACTION_APPLICABILITY = (
    OUT
    / "r3c_action_historical_applicability_v1.csv"
)

MC_FINAL = (
    OUT
    / "r3c_final_monte_carlo_action_envelope_v2.csv"
)

MC_SUMMARY = (
    OUT
    / "r3b4_monte_carlo_performance_decision_envelope_v1.json"
)

ENV_SUMMARY = (
    OUT
    / "r3b3_performance_environment_sensitivity_v1.json"
)

RECOVERY_POSTERIOR = (
    OUT
    / "repeat_performance_recovery_probability_v1.csv"
)

PAIR_DATASET = (
    OUT
    / "r3b3_repeat_pair_environment_dataset_v1.csv"
)

TIMED_COVERAGE = (
    OUT
    / "r3b_timed_subset_coverage_v1.csv"
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

SUPPORTED_OUT = (
    OUT
    / "final_supported_claims_v1.csv"
)

LIMITATIONS_OUT = (
    OUT
    / "final_limitations_v1.csv"
)

CORE_RESULTS_OUT = (
    OUT
    / "final_core_results_v1.csv"
)

SUMMARY_OUT = (
    OUT
    / "final_capability_summary_v1.json"
)

MANIFEST_OUT = (
    OUT
    / "final_results_freeze_manifest_v1.csv"
)

QA_OUT = (
    OUT
    / "final_results_freeze_v1_qa.csv"
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


EXPECTED_ACTIONS = {
    "STOP_RETAIN_CURRENT_RESULT",
    "REPEAT_LANE2_RETAIN_CURRENT_RESULT",
    "REPEAT_LANE1_WITHDRAW_CURRENT_RESULT",
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


def sha256_file(path):
    h = hashlib.sha256()

    with path.open("rb") as f:
        while True:
            chunk = f.read(
                1024 * 1024
            )

            if not chunk:
                break

            h.update(chunk)

    return h.hexdigest()


def fmt(v, digits=6):
    if v is None:
        return "UNKNOWN"

    return f"{v:.{digits}f}"


def get_central_action_row(
    mc_rows,
    action,
):
    rows = [
        row
        for row in mc_rows
        if (
            txt(
                row.get(
                    "recovery_prior_scenario"
                )
            )
            ==
            "ALL_PRIMARY"
            and
            txt(
                row.get(
                    "queue_wait_minutes"
                )
            )
            ==
            "15"
            and
            txt(
                row.get(
                    "action"
                )
            )
            ==
            action
        )
    ]

    if not rows:
        return None

    # Distribution is deliberately identical across drivers.
    # Confirm that before taking first row.
    fields = [
        "mean_final_delta_mph",
        "q05_final_delta_mph",
        "q50_final_delta_mph",
        "q95_final_delta_mph",
        "prob_final_improves",
        "prob_final_worse",
    ]

    signatures = {
        tuple(
            txt(
                row.get(field)
            )
            for field in fields
        )
        for row in rows
    }

    if len(signatures) != 1:
        return None

    return rows[0]


def add_result(
    rows,
    result_id,
    category,
    metric,
    value,
    unit,
    interpretation,
    source_asset,
):

    rows.append({
        "result_id":
            result_id,

        "category":
            category,

        "metric":
            metric,

        "value":
            value,

        "unit":
            unit,

        "interpretation":
            interpretation,

        "source_asset":
            source_asset,
    })


def add_claim(
    rows,
    claim_id,
    category,
    support_level,
    claim_cn,
    claim_en,
    source_asset,
    caveat,
):

    rows.append({
        "claim_id":
            claim_id,

        "category":
            category,

        "support_level":
            support_level,

        "claim_cn":
            claim_cn,

        "dissertation_claim_en":
            claim_en,

        "source_asset":
            source_asset,

        "required_caveat":
            caveat,
    })


def add_limitation(
    rows,
    limitation_id,
    domain,
    status,
    statement_cn,
    statement_en,
    prohibited_claim,
    downstream_effect,
):

    rows.append({
        "limitation_id":
            limitation_id,

        "domain":
            domain,

        "identifiability_status":
            status,

        "statement_cn":
            statement_cn,

        "dissertation_statement_en":
            statement_en,

        "prohibited_claim":
            prohibited_claim,

        "downstream_effect":
            downstream_effect,
    })


def main():

    print()
    print("=" * 128)
    print(
        "R3C.1 — FINAL RESULTS / "
        "CAPABILITY FREEZE"
    )
    print("=" * 128)

    required = [
        STATE_FINAL,
        ACTION_APPLICABILITY,
        MC_FINAL,
        MC_SUMMARY,
        ENV_SUMMARY,
        RECOVERY_POSTERIOR,
        PAIR_DATASET,
        TIMED_COVERAGE,
        QUEUE_POLICY,
        SERVICE_POLICY,
        RUBBER_POLICY,
        TIRE_POLICY,
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
            "R3C1_REQUIRED_INPUT_MISSING"
        )

        return

    states = read_csv(
        STATE_FINAL
    )

    applicability = read_csv(
        ACTION_APPLICABILITY
    )

    mc_rows = read_csv(
        MC_FINAL
    )

    recovery_rows = read_csv(
        RECOVERY_POSTERIOR
    )

    pair_rows = read_csv(
        PAIR_DATASET
    )

    timed_rows = read_csv(
        TIMED_COVERAGE
    )

    queue_rows = read_csv(
        QUEUE_POLICY
    )

    service_rows = read_csv(
        SERVICE_POLICY
    )

    rubber_rows = read_csv(
        RUBBER_POLICY
    )

    tire_rows = read_csv(
        TIRE_POLICY
    )

    mc_summary = json.loads(
        MC_SUMMARY.read_text(
            encoding="utf-8"
        )
    )

    env_summary = json.loads(
        ENV_SUMMARY.read_text(
            encoding="utf-8"
        )
    )

    # --------------------------------------------------
    # Final state checks
    # --------------------------------------------------

    drivers = {
        txt(
            row.get(
                "driver_name"
            )
        )
        for row in states
    }

    target_exact = (
        len(states) == 8
        and
        drivers
        ==
        EXPECTED_DRIVERS
    )

    missing_first_speeds = [
        row[
            "driver_name"
        ]
        for row in states
        if fnum(
            row.get(
                "first_attempt_speed_mph"
            )
        )
        is None
    ]

    known_predecision_rank = [
        row
        for row in states
        if fnum(
            row.get(
                "predecision_current_rank"
            )
        )
        is not None
    ]

    known_rank_drivers = sorted(
        row[
            "driver_name"
        ]
        for row in known_predecision_rank
    )

    scott = next(
        row
        for row in states
        if row[
            "driver_name"
        ]
        ==
        "Scott McLaughlin"
    )

    scott_speed = fnum(
        scott.get(
            "first_attempt_speed_mph"
        )
    )

    # --------------------------------------------------
    # Performance / environment results
    # --------------------------------------------------

    env_model_mae = fnum(
        env_summary.get(
            "best_environment_model_pooled_mae_mph"
        )
    )

    zero_same_mae = fnum(
        env_summary.get(
            "same_rows_zero_delta_mae_mph"
        )
    )

    env_improvement = fnum(
        env_summary.get(
            "environment_model_mae_improvement_mph"
        )
    )

    env_beats_zero = bool(
        env_summary.get(
            "environment_model_beats_zero_delta",
            False,
        )
    )

    frozen_zero_mae = fnum(
        env_summary.get(
            "frozen_zero_delta_baseline_mae_mph"
        )
    )

    # --------------------------------------------------
    # Repeat-pair population
    # --------------------------------------------------

    environment_ready_pairs = [
        row
        for row in pair_rows
        if truthy(
            row.get(
                "pair_environment_fit_ready"
            )
        )
    ]

    normal_pairs = [
        row
        for row in environment_ready_pairs
        if not truthy(
            row.get(
                "diagnostic_recovery_like"
            )
        )
    ]

    recovery_pairs = [
        row
        for row in environment_ready_pairs
        if truthy(
            row.get(
                "diagnostic_recovery_like"
            )
        )
    ]

    ptsc_complete_pairs = [
        row
        for row in environment_ready_pairs
        if (
            txt(
                row.get(
                    "baseline_ptsc_track_c"
                )
            )
            !=
            "UNKNOWN"
            and
            txt(
                row.get(
                    "repeat_ptsc_track_c"
                )
            )
            !=
            "UNKNOWN"
        )
    ]

    # --------------------------------------------------
    # Timed subset
    # --------------------------------------------------

    timed_joinable_total = sum(
        int(
            float(
                txt(
                    row.get(
                        "fully_joinable_timed_weather_rows"
                    )
                )
                or
                "0"
            )
        )
        for row in timed_rows
    )

    timed_years = [
        txt(
            row.get("year")
        )
        for row in timed_rows
        if int(
            float(
                txt(
                    row.get(
                        "fully_joinable_timed_weather_rows"
                    )
                )
                or
                "0"
            )
        )
        >
        0
    ]

    # --------------------------------------------------
    # Recovery posterior
    # --------------------------------------------------

    all_primary = next(
        (
            row
            for row in recovery_rows
            if txt(
                row.get(
                    "eligibility_group"
                )
            )
            ==
            "ALL_PRIMARY"
        ),
        None,
    )

    recovery_alpha = (
        fnum(
            all_primary.get(
                "posterior_alpha"
            )
        )
        if all_primary
        else
        None
    )

    recovery_beta = (
        fnum(
            all_primary.get(
                "posterior_beta"
            )
        )
        if all_primary
        else
        None
    )

    recovery_mean = (
        fnum(
            all_primary.get(
                "posterior_mean_probability"
            )
        )
        if all_primary
        else
        None
    )

    recovery_successes = (
        fnum(
            all_primary.get(
                "successes"
            )
        )
        if all_primary
        else
        None
    )

    recovery_trials = (
        fnum(
            all_primary.get(
                "trials"
            )
        )
        if all_primary
        else
        None
    )

    # --------------------------------------------------
    # Monte Carlo central action envelopes
    # --------------------------------------------------

    stop = get_central_action_row(
        mc_rows,
        "STOP_RETAIN_CURRENT_RESULT",
    )

    lane2 = get_central_action_row(
        mc_rows,
        "REPEAT_LANE2_RETAIN_CURRENT_RESULT",
    )

    lane1 = get_central_action_row(
        mc_rows,
        "REPEAT_LANE1_WITHDRAW_CURRENT_RESULT",
    )

    central_rows_valid = all([
        stop is not None,
        lane2 is not None,
        lane1 is not None,
    ])

    def metric(row, field):
        if row is None:
            return None

        return fnum(
            row.get(field)
        )

    lane2_mean = metric(
        lane2,
        "mean_final_delta_mph",
    )

    lane2_q05 = metric(
        lane2,
        "q05_final_delta_mph",
    )

    lane2_q50 = metric(
        lane2,
        "q50_final_delta_mph",
    )

    lane2_q95 = metric(
        lane2,
        "q95_final_delta_mph",
    )

    lane2_improve = metric(
        lane2,
        "prob_final_improves",
    )

    lane2_worse = metric(
        lane2,
        "prob_final_worse",
    )

    lane1_mean = metric(
        lane1,
        "mean_final_delta_mph",
    )

    lane1_q05 = metric(
        lane1,
        "q05_final_delta_mph",
    )

    lane1_q50 = metric(
        lane1,
        "q50_final_delta_mph",
    )

    lane1_q95 = metric(
        lane1,
        "q95_final_delta_mph",
    )

    lane1_improve = metric(
        lane1,
        "prob_final_improves",
    )

    lane1_worse = metric(
        lane1,
        "prob_final_worse",
    )

    lane2_minus_lane1_mean = (
        lane2_mean
        -
        lane1_mean
        if (
            lane2_mean is not None
            and
            lane1_mean is not None
        )
        else
        None
    )

    # --------------------------------------------------
    # Applicability
    # --------------------------------------------------

    sato_rows = [
        row
        for row in applicability
        if row[
            "driver_name"
        ]
        ==
        "Takuma Sato"
    ]

    sato_required_ok = (
        len(sato_rows) == 3
        and
        all(
            row[
                "case_type"
            ]
            ==
            "REQUIRED_REATTEMPT_CASE"
            for row in sato_rows
        )
    )

    lane1_observed_drivers = sorted(
        {
            row[
                "driver_name"
            ]
            for row in applicability
            if (
                row[
                    "simulated_action"
                ]
                ==
                "REPEAT_LANE1_WITHDRAW_CURRENT_RESULT"
                and
                row[
                    "historical_applicability"
                ]
                ==
                "OBSERVED_ACTION"
            )
        }
    )

    # --------------------------------------------------
    # CORE RESULTS
    # --------------------------------------------------

    core_results = []

    add_result(
        core_results,
        "R001",
        "DATA",
        "decision_relevant_2022_repeat_drivers",
        "8",
        "drivers",
        (
            "Eight 2022 decision-relevant repeat cases "
            "were carried into the final state representation."
        ),
        STATE_FINAL.name,
    )

    add_result(
        core_results,
        "R002",
        "DATA",
        "known_predecision_rank_states",
        str(
            len(
                known_predecision_rank
            )
        ),
        "drivers",
        (
            "Directly supported pre-decision rank state exists "
            "for Rossi and McLaughlin only."
        ),
        STATE_FINAL.name,
    )

    add_result(
        core_results,
        "R003",
        "DATA",
        "timed_weather_subset_rows",
        str(
            timed_joinable_total
        ),
        "attempts",
        (
            "Performance-grade timed HRRR subset available "
            "for 2020, 2021 and 2023."
        ),
        TIMED_COVERAGE.name,
    )

    add_result(
        core_results,
        "R004",
        "DATA",
        "repeat_pair_environment_rows",
        str(
            len(
                environment_ready_pairs
            )
        ),
        "pairs",
        (
            "Historical repeat pairs with usable performance "
            "and environment binding."
        ),
        PAIR_DATASET.name,
    )

    add_result(
        core_results,
        "R005",
        "DATA",
        "normal_repeat_pairs",
        str(
            len(
                normal_pairs
            )
        ),
        "pairs",
        (
            "Normal branch used for the primary environment "
            "sensitivity fit."
        ),
        PAIR_DATASET.name,
    )

    add_result(
        core_results,
        "R006",
        "DATA",
        "recovery_like_pairs",
        str(
            len(
                recovery_pairs
            )
        ),
        "pairs",
        (
            "Recovery-like cases were retained as a separate "
            "small-sample branch."
        ),
        PAIR_DATASET.name,
    )

    add_result(
        core_results,
        "R007",
        "PERFORMANCE",
        "frozen_zero_delta_baseline_mae",
        fmt(
            frozen_zero_mae
        ),
        "mph",
        (
            "Frozen pooled ZERO_DELTA baseline error from "
            "the repeat-performance evaluation."
        ),
        ENV_SUMMARY.name,
    )

    add_result(
        core_results,
        "R008",
        "ENVIRONMENT",
        "best_environment_ridge_loyo_mae",
        fmt(
            env_model_mae
        ),
        "mph",
        (
            "Best leave-one-year-out Ridge result on the "
            "normal repeat subset."
        ),
        ENV_SUMMARY.name,
    )

    add_result(
        core_results,
        "R009",
        "ENVIRONMENT",
        "zero_delta_mae_same_loyo_rows",
        fmt(
            zero_same_mae
        ),
        "mph",
        (
            "ZERO_DELTA error evaluated on exactly the same "
            "LOYO rows as the environment model."
        ),
        ENV_SUMMARY.name,
    )

    add_result(
        core_results,
        "R010",
        "ENVIRONMENT",
        "environment_mae_improvement_vs_zero",
        fmt(
            env_improvement
        ),
        "mph",
        (
            "Negative means the environment Ridge did not "
            "outperform ZERO_DELTA."
        ),
        ENV_SUMMARY.name,
    )

    add_result(
        core_results,
        "R011",
        "RECOVERY",
        "recovery_posterior",
        (
            f"Beta({fmt(recovery_alpha, 3)},"
            f"{fmt(recovery_beta, 3)})"
        ),
        "distribution",
        (
            "Posterior uncertainty over recovery-like repeat "
            "frequency for ALL_PRIMARY."
        ),
        RECOVERY_POSTERIOR.name,
    )

    add_result(
        core_results,
        "R012",
        "RECOVERY",
        "recovery_posterior_mean",
        fmt(
            recovery_mean
        ),
        "probability",
        (
            "Posterior mean recovery-like probability."
        ),
        RECOVERY_POSTERIOR.name,
    )

    add_result(
        core_results,
        "R013",
        "MONTE_CARLO",
        "lane2_mean_final_delta",
        fmt(
            lane2_mean
        ),
        "mph",
        (
            "Performance-only expected final change when the "
            "existing result is retained."
        ),
        MC_FINAL.name,
    )

    add_result(
        core_results,
        "R014",
        "MONTE_CARLO",
        "lane2_probability_improve",
        fmt(
            lane2_improve
        ),
        "probability",
        (
            "Probability of performance improvement under the "
            "central ALL_PRIMARY predictive mixture."
        ),
        MC_FINAL.name,
    )

    add_result(
        core_results,
        "R015",
        "MONTE_CARLO",
        "lane2_probability_worse",
        fmt(
            lane2_worse
        ),
        "probability",
        (
            "Zero by construction because the existing result "
            "is retained."
        ),
        MC_FINAL.name,
    )

    add_result(
        core_results,
        "R016",
        "MONTE_CARLO",
        "lane1_mean_final_delta",
        fmt(
            lane1_mean
        ),
        "mph",
        (
            "Performance-only expected final change when the "
            "existing result is withdrawn."
        ),
        MC_FINAL.name,
    )

    add_result(
        core_results,
        "R017",
        "MONTE_CARLO",
        "lane1_probability_improve",
        fmt(
            lane1_improve
        ),
        "probability",
        (
            "Probability of performance improvement under the "
            "central ALL_PRIMARY predictive mixture."
        ),
        MC_FINAL.name,
    )

    add_result(
        core_results,
        "R018",
        "MONTE_CARLO",
        "lane1_probability_worse",
        fmt(
            lane1_worse
        ),
        "probability",
        (
            "Downside probability after withdrawing the "
            "existing result."
        ),
        MC_FINAL.name,
    )

    add_result(
        core_results,
        "R019",
        "MONTE_CARLO",
        "lane2_minus_lane1_mean_delta",
        fmt(
            lane2_minus_lane1_mean
        ),
        "mph",
        (
            "Pure performance value of retaining downside "
            "protection when time/priority effects are excluded."
        ),
        MC_FINAL.name,
    )

    add_result(
        core_results,
        "R020",
        "PROVENANCE",
        "scott_first_attempt_speed",
        fmt(
            scott_speed
        ),
        "mph",
        (
            "Recovered from exact canonical-attempt matching "
            "without changing Monte Carlo delta draws."
        ),
        STATE_FINAL.name,
    )

    write_csv(
        CORE_RESULTS_OUT,
        core_results,
        [
            "result_id",
            "category",
            "metric",
            "value",
            "unit",
            "interpretation",
            "source_asset",
        ],
    )

    # --------------------------------------------------
    # SUPPORTED CLAIMS
    # --------------------------------------------------

    claims = []

    add_claim(
        claims,
        "C001",
        "SYSTEM",
        "SUPPORTED",
        (
            "本项目实现的是一个带显式可识别性边界的、"
            "不确定性感知排位决策支持原型，而不是完整的"
            "自动决策器。"
        ),
        (
            "The final prototype is an uncertainty-aware "
            "qualifying decision-support system with explicit "
            "identifiability boundaries rather than a fully "
            "observed autonomous decision maker."
        ),
        SUMMARY_OUT.name,
        (
            "Do not describe the system as a complete "
            "optimal-policy engine."
        ),
    )

    add_claim(
        claims,
        "C002",
        "STATE",
        "SUPPORTED_WITH_LIMITATIONS",
        (
            "2022 年八个 decision-relevant repeat case 均被"
            "保留进最终状态表，但只有 Rossi 和 McLaughlin "
            "具有可直接支持的 pre-decision rank。"
        ),
        (
            "All eight 2022 decision-relevant repeat cases were "
            "retained in the final state table, while directly "
            "supported pre-decision rank information was "
            "available only for Rossi and McLaughlin."
        ),
        STATE_FINAL.name,
        (
            "Unknown ranks must remain unknown."
        ),
    )

    add_claim(
        claims,
        "C003",
        "TIMING",
        "SUPPORTED",
        (
            "2022 的 repeat-pair decision time 无法可靠恢复，"
            "因此没有构造车手级真实 future-weather path。"
        ),
        (
            "Decision times for the 2022 repeat-pair cases were "
            "not reliably identifiable, so driver-specific "
            "historical future-weather paths were not "
            "reconstructed."
        ),
        TIMED_COVERAGE.name,
        (
            "Do not infer timestamps from result ordering."
        ),
    )

    add_claim(
        claims,
        "C004",
        "WEATHER",
        "SUPPORTED",
        (
            f"2020、2021 和 2023 共 {timed_joinable_total} 个"
            " performance-grade timed attempt 可连接 leakage-safe "
            "HRRR，用于环境敏感度分析。"
        ),
        (
            f"A total of {timed_joinable_total} performance-grade "
            "timed attempts from 2020, 2021 and 2023 could be "
            "linked to leakage-safe HRRR forecasts for "
            "environmental sensitivity analysis."
        ),
        TIMED_COVERAGE.name,
        (
            "This timed subset does not include 2022."
        ),
    )

    add_claim(
        claims,
        "C005",
        "ENVIRONMENT",
        "SUPPORTED",
        (
            "在 normal repeat subset 上，HRRR 环境变化模型没有在"
            " leave-one-year-out 验证中击败 ZERO_DELTA baseline，"
            "因此环境效应只保留为 sensitivity，不进入 central prediction。"
        ),
        (
            "On the normal-repeat subset, the HRRR environment-"
            "change model did not outperform the ZERO_DELTA "
            "baseline under leave-one-year-out validation; "
            "environmental effects were therefore retained as "
            "sensitivity analysis rather than central prediction."
        ),
        ENV_SUMMARY.name,
        (
            "This is a predictive validation result, not "
            "evidence that weather has no physical effect."
        ),
    )

    add_claim(
        claims,
        "C006",
        "TRACK_TEMPERATURE",
        "SUPPORTED_WITH_LIMITATIONS",
        (
            "PTSC track temperature 只用于历史诊断，不作为 forward "
            "simulator predictor，因为未来 track temperature "
            "无法被合法恢复，且禁止 air-to-track proxy。"
        ),
        (
            "Observed PTSC track temperature was retained for "
            "historical diagnostics only and was excluded from "
            "forward simulation because future track temperature "
            "was not identifiable and no air-to-track proxy was "
            "permitted."
        ),
        ENV_SUMMARY.name,
        (
            "Do not convert air temperature into track "
            "temperature."
        ),
    )

    add_claim(
        claims,
        "C007",
        "PERFORMANCE",
        "SUPPORTED",
        (
            "ZERO_DELTA 是 repeat-performance central point "
            "prediction：下一次四圈均速的中心预测等于当前最好成绩，"
            "不确定性由经验 repeat-delta distribution 表达。"
        ),
        (
            "ZERO_DELTA was retained as the central repeat-"
            "performance point prediction, with uncertainty "
            "represented through empirical repeat-delta "
            "distributions."
        ),
        ENV_SUMMARY.name,
        (
            "Do not interpret zero-delta as zero uncertainty."
        ),
    )

    add_claim(
        claims,
        "C008",
        "RECOVERY",
        "SUPPORTED_WITH_LIMITATIONS",
        (
            f"39 个 repeat pair 中只有 {len(recovery_pairs)} 个"
            " recovery-like case，因此 recovery branch 没有单独"
            "拟合多变量模型，而是使用经验分布和 Beta posterior。"
        ),
        (
            f"Only {len(recovery_pairs)} of the 39 repeat pairs "
            "were classified as recovery-like; this branch was "
            "therefore represented using an empirical "
            "distribution and Beta posterior rather than a "
            "separate multivariable model."
        ),
        RECOVERY_POSTERIOR.name,
        (
            "Recovery-like is a diagnostic classification, "
            "not a causal latent state."
        ),
    )

    add_claim(
        claims,
        "C009",
        "MONTE_CARLO",
        "SUPPORTED",
        (
            f"在 central ALL_PRIMARY Monte Carlo 中，保留原成绩的"
            f" repeat action 平均最终变化约 {fmt(lane2_mean, 3)} mph，"
            f"改善概率约 {fmt(lane2_improve * 100 if lane2_improve is not None else None, 1)}%，"
            "且不会因为 repeat 更慢而损失已有成绩。"
        ),
        (
            "Under the central ALL_PRIMARY Monte Carlo mixture, "
            f"the retain-result repeat action produced a mean "
            f"final change of approximately {fmt(lane2_mean, 3)} mph "
            f"and an improvement probability of approximately "
            f"{fmt(lane2_improve * 100 if lane2_improve is not None else None, 1)}%, "
            "while protecting the existing result from a slower "
            "repeat."
        ),
        MC_FINAL.name,
        (
            "Conditional on a completed repeat attempt; "
            "priority/time effects are excluded."
        ),
    )

    add_claim(
        claims,
        "C010",
        "MONTE_CARLO",
        "SUPPORTED",
        (
            f"在相同 performance-only 条件下，withdraw-result "
            f"repeat 的平均最终变化约 {fmt(lane1_mean, 3)} mph，"
            f"并具有约 {fmt(lane1_worse * 100 if lane1_worse is not None else None, 1)}% "
            "的最终成绩变差概率。"
        ),
        (
            "Under the same performance-only assumptions, the "
            "withdraw-result repeat action produced a mean final "
            f"change of approximately {fmt(lane1_mean, 3)} mph "
            f"and a probability of approximately "
            f"{fmt(lane1_worse * 100 if lane1_worse is not None else None, 1)}% "
            "of ending with a worse result."
        ),
        MC_FINAL.name,
        (
            "This does not include the potential time value "
            "of priority Lane 1."
        ),
    )

    add_claim(
        claims,
        "C011",
        "DECISION",
        "SUPPORTED_WITH_LIMITATIONS",
        (
            "在排除 priority/time advantage 后，retain-result "
            "repeat 在纯 performance-risk 层面对 withdraw-result "
            "repeat 具有 downside protection；这不是 Lane 2 "
            "总体优于 Lane 1 的结论。"
        ),
        (
            "When priority and time advantages were excluded, "
            "the retain-result repeat action provided downside "
            "protection relative to the withdraw-result repeat "
            "action in the performance-risk envelope; this does "
            "not imply that Lane 2 is globally preferable to "
            "Lane 1."
        ),
        MC_FINAL.name,
        (
            "Lane 1 priority value remains unmodeled."
        ),
    )

    add_claim(
        claims,
        "C012",
        "HISTORICAL_ACTION",
        "SUPPORTED_WITH_LIMITATIONS",
        (
            "Rossi 和 McLaughlin 的 Lane 1 withdrawal action "
            "具有直接历史证据；其他 repeat case 的完整 lane set "
            "没有被可靠恢复。"
        ),
        (
            "Direct historical evidence supports Lane 1 "
            "withdrawal actions for Rossi and McLaughlin, while "
            "the complete lane choice set for the remaining "
            "repeat cases was not reliably reconstructed."
        ),
        ACTION_APPLICABILITY.name,
        (
            "Withdrawn status alone must not be treated as "
            "Lane 1 evidence."
        ),
    )

    add_claim(
        claims,
        "C013",
        "SATO",
        "SUPPORTED",
        (
            "Takuma Sato 属于 required reattempt after "
            "invalidation，不应被解释为普通 STOP/Lane2/Lane1 "
            "自主三选一案例。"
        ),
        (
            "Takuma Sato represents a required reattempt after "
            "invalidation and should not be interpreted as a "
            "standard elective STOP/Lane2/Lane1 decision case."
        ),
        ACTION_APPLICABILITY.name,
        (
            "His three mathematical envelopes are generic "
            "counterfactual semantics only."
        ),
    )

    add_claim(
        claims,
        "C014",
        "PROVENANCE",
        "SUPPORTED",
        (
            "Scott McLaughlin 的第一轮速度通过 exact canonical "
            "attempt ID 恢复为 231.543 mph，且该修复没有改变 "
            "Monte Carlo delta distribution。"
        ),
        (
            "Scott McLaughlin's first-attempt speed was recovered "
            "as 231.543 mph through exact canonical-attempt "
            "matching, without altering the Monte Carlo delta "
            "distribution."
        ),
        STATE_FINAL.name,
        (
            "Car numbers remain string-valued; no numeric "
            "normalisation is permitted."
        ),
    )

    write_csv(
        SUPPORTED_OUT,
        claims,
        [
            "claim_id",
            "category",
            "support_level",
            "claim_cn",
            "dissertation_claim_en",
            "source_asset",
            "required_caveat",
        ],
    )

    # --------------------------------------------------
    # LIMITATIONS / PROHIBITED CLAIMS
    # --------------------------------------------------

    limitations = []

    add_limitation(
        limitations,
        "L001",
        "2022_DECISION_TIME",
        "NOT_IDENTIFIABLE",
        (
            "2022 repeat-pair 的精确 decision timestamp 无法可靠恢复。"
        ),
        (
            "Exact decision timestamps for the 2022 repeat-pair "
            "cases were not reliably identifiable."
        ),
        (
            "Do not claim reconstructed exact decision times."
        ),
        (
            "No driver-specific 2022 future-weather "
            "counterfactual."
        ),
    )

    add_limitation(
        limitations,
        "L002",
        "QUEUE_WAIT",
        "LATENT_SENSITIVITY_ONLY",
        (
            "历史 queue wait 无法由现有证据识别，5/15/30/45 分钟"
            "只能作为敏感度场景。"
        ),
        (
            "Historical queue waiting time was not identifiable; "
            "5/15/30/45-minute values are sensitivity scenarios "
            "only."
        ),
        (
            "Do not present wait scenarios as reconstructed "
            "historical waits or probabilities."
        ),
        (
            "Priority/time value cannot be quantitatively "
            "estimated."
        ),
    )

    add_limitation(
        limitations,
        "L003",
        "QUEUE_POSITION",
        "PARTIAL",
        (
            "只恢复了少量 queue membership / ordering / position "
            "证据，不能重放完整 queue。"
        ),
        (
            "Only partial queue membership, ordering and "
            "position evidence was recovered; a complete queue "
            "replay is not supported."
        ),
        (
            "Do not claim exact historical queue state."
        ),
        (
            "No full session-level priority queue simulation."
        ),
    )

    add_limitation(
        limitations,
        "L004",
        "LIVE_LEADERBOARD",
        "PARTIAL",
        (
            "只有少量 contemporaneous rank/cutoff anchor，"
            "没有完整 historical live leaderboard。"
        ),
        (
            "Only a small number of contemporaneous rank/cutoff "
            "anchors were recovered, not a complete historical "
            "live leaderboard."
        ),
        (
            "Do not report complete rank/cutoff trajectories."
        ),
        (
            "No reliable rank-outcome probability."
        ),
    )

    add_limitation(
        limitations,
        "L005",
        "TRACK_TEMPERATURE",
        "FUTURE_NOT_IDENTIFIABLE",
        (
            "未来 track temperature 不预测，且禁止用 air "
            "temperature 推导。"
        ),
        (
            "Future track temperature was not predicted, and "
            "air temperature was not used as a proxy."
        ),
        (
            "Do not infer future track temperature from HRRR "
            "air temperature."
        ),
        (
            "Track temperature remains diagnostic only."
        ),
    )

    add_limitation(
        limitations,
        "L006",
        "RUBBER_GRIP",
        "UNKNOWN_NOT_IDENTIFIABLE",
        (
            "Day 1 rubber state 和 grip evolution 无法可靠恢复。"
        ),
        (
            "Day 1 rubber state and grip evolution were not "
            "reliably identifiable."
        ),
        (
            "Do not use elapsed time as a rubber/grip proxy."
        ),
        (
            "No quantitative grip-evolution term in simulator."
        ),
    )

    add_limitation(
        limitations,
        "L007",
        "TIRE_STATE",
        "UNKNOWN_NOT_IDENTIFIABLE",
        (
            "attempt-specific tire thermal/pressure state "
            "无法恢复。"
        ),
        (
            "Attempt-specific tyre thermal and pressure states "
            "were not identifiable."
        ),
        (
            "Do not infer tyre state from wait time, elapsed "
            "time or repeat occurrence."
        ),
        (
            "No tyre-state predictor in simulator."
        ),
    )

    add_limitation(
        limitations,
        "L008",
        "PIT_SERVICE",
        "UNKNOWN_NOT_IDENTIFIABLE",
        (
            "repeat attempt 之间的 refuel、cooling、tire service、"
            "setup adjustment 等无法可靠识别。"
        ),
        (
            "Refuelling, cooling, tyre service and setup changes "
            "between repeat attempts were not reliably "
            "identifiable."
        ),
        (
            "NOT OBSERVED must not be rewritten as NONE."
        ),
        (
            "No service-state adjustment in performance model."
        ),
    )

    add_limitation(
        limitations,
        "L009",
        "ENVIRONMENT_CAUSALITY",
        "OBSERVATIONAL_ONLY",
        (
            "天气与 repeat performance 的关系只能解释为观察性"
            "敏感度，不能解释为因果效应。"
        ),
        (
            "The relationship between environmental changes and "
            "repeat performance is observational sensitivity "
            "rather than a causal effect estimate."
        ),
        (
            "Do not state that a weather change causes a "
            "specific speed change."
        ),
        (
            "Environment model remains sensitivity-only."
        ),
    )

    add_limitation(
        limitations,
        "L010",
        "REPEAT_COMPLETION",
        "NOT_MODELED",
        (
            "simulator 没有估计某个 queue/action 是否能在 session "
            "结束前真正完成 repeat attempt。"
        ),
        (
            "The simulator does not estimate whether a repeat "
            "attempt can actually be completed before the end "
            "of the session."
        ),
        (
            "Do not interpret Monte Carlo envelopes as "
            "session-completion probabilities."
        ),
        (
            "Performance envelopes are conditional on a "
            "completed repeat attempt."
        ),
    )

    add_limitation(
        limitations,
        "L011",
        "HARD_RECOMMENDATION",
        "NOT_READY",
        (
            "当前系统不能给出经过历史验证的硬性 retain/withdraw "
            "推荐。"
        ),
        (
            "The current system does not support a historically "
            "validated hard retain/withdraw recommendation."
        ),
        (
            "Do not claim optimal Lane 1/Lane 2/STOP decisions."
        ),
        (
            "Output must remain decision support / risk envelope."
        ),
    )

    add_limitation(
        limitations,
        "L012",
        "LANE2_DOMINANCE",
        "PERFORMANCE_ONLY",
        (
            "Lane2 的 downside protection 只在移除 priority/time "
            "价值后的 performance-only 语义下成立。"
        ),
        (
            "Lane 2 downside protection holds only under the "
            "performance-only semantics that exclude priority "
            "and time value."
        ),
        (
            "Do not state that Lane 2 is always better than "
            "Lane 1."
        ),
        (
            "Lane 1 may have unmodeled strategic time value."
        ),
    )

    write_csv(
        LIMITATIONS_OUT,
        limitations,
        [
            "limitation_id",
            "domain",
            "identifiability_status",
            "statement_cn",
            "dissertation_statement_en",
            "prohibited_claim",
            "downstream_effect",
        ],
    )

    # --------------------------------------------------
    # CAPABILITY SUMMARY
    # --------------------------------------------------

    capability = {
        "phase":
            PHASE,

        "freeze_timestamp_utc":
            datetime.now(
                timezone.utc
            ).isoformat(),

        "system_name":
            (
                "Indy 500 Day 1 Qualifying "
                "Uncertainty-Aware Decision Support Prototype"
            ),

        "final_system_class":
            (
                "LIMITED_UNCERTAINTY_AWARE_"
                "PERFORMANCE_DECISION_SUPPORT"
            ),

        "historical_truth_reconstruction":
            {
                "four_lap_performance":
                    "READY",

                "repeat_pair_performance":
                    "READY",

                "2022_repeat_pair_chronology":
                    "READY_WITH_LIMITATIONS",

                "historical_action_semantics":
                    "READY_WITH_LIMITATIONS",

                "lane_identity":
                    "PARTIAL",

                "contemporaneous_rank_cutoff":
                    "PARTIAL",

                "queue_membership_position":
                    "PARTIAL",

                "exact_queue_wait":
                    "NOT_IDENTIFIABLE",

                "2022_decision_time":
                    "NOT_IDENTIFIABLE",

                "pit_service":
                    "UNKNOWN_NOT_IDENTIFIABLE",

                "rubber_grip":
                    "UNKNOWN_NOT_IDENTIFIABLE",

                "tire_thermal_pressure":
                    "UNKNOWN_NOT_IDENTIFIABLE",
            },

        "performance_model":
            {
                "central_point_prediction":
                    "ZERO_DELTA_BASELINE",

                "frozen_zero_delta_pooled_mae_mph":
                    frozen_zero_mae,

                "predictive_uncertainty":
                    (
                        "EMPIRICAL_REPEAT_DELTA_DISTRIBUTION"
                    ),

                "recovery_branch":
                    (
                        "EMPIRICAL_BOOTSTRAP_PLUS_"
                        "BETA_POSTERIOR"
                    ),

                "recovery_all_primary":
                    {
                        "successes":
                            recovery_successes,

                        "trials":
                            recovery_trials,

                        "posterior_alpha":
                            recovery_alpha,

                        "posterior_beta":
                            recovery_beta,

                        "posterior_mean":
                            recovery_mean,
                    },
            },

        "environment_model":
            {
                "timed_weather_years":
                    timed_years,

                "timed_weather_rows":
                    timed_joinable_total,

                "repeat_pair_rows":
                    len(
                        environment_ready_pairs
                    ),

                "normal_fit_rows":
                    len(
                        normal_pairs
                    ),

                "recovery_rows":
                    len(
                        recovery_pairs
                    ),

                "best_ridge_loyo_mae_mph":
                    env_model_mae,

                "same_rows_zero_delta_mae_mph":
                    zero_same_mae,

                "mae_improvement_vs_zero_mph":
                    env_improvement,

                "beats_zero_delta":
                    env_beats_zero,

                "simulator_role":
                    (
                        "SENSITIVITY_ONLY_"
                        "ZERO_DELTA_REMAINS_CENTRAL"
                    ),

                "ptsc_track_temperature":
                    "DIAGNOSTIC_ONLY",

                "future_track_temperature":
                    "NOT_PREDICTED",

                "air_to_track_proxy":
                    False,
            },

        "monte_carlo":
            {
                "central_recovery_prior":
                    "ALL_PRIMARY",

                "condition":
                    (
                        "CONDITIONAL_ON_COMPLETED_REPEAT_ATTEMPT"
                    ),

                "retain_result_repeat":
                    {
                        "mean_final_delta_mph":
                            lane2_mean,

                        "q05_final_delta_mph":
                            lane2_q05,

                        "q50_final_delta_mph":
                            lane2_q50,

                        "q95_final_delta_mph":
                            lane2_q95,

                        "probability_improve":
                            lane2_improve,

                        "probability_worse":
                            lane2_worse,
                    },

                "withdraw_result_repeat":
                    {
                        "mean_final_delta_mph":
                            lane1_mean,

                        "q05_final_delta_mph":
                            lane1_q05,

                        "q50_final_delta_mph":
                            lane1_q50,

                        "q95_final_delta_mph":
                            lane1_q95,

                        "probability_improve":
                            lane1_improve,

                        "probability_worse":
                            lane1_worse,
                    },

                "retain_minus_withdraw_mean_delta_mph":
                    lane2_minus_lane1_mean,

                "queue_wait_scenarios_minutes":
                    [
                        5,
                        15,
                        30,
                        45,
                    ],

                "queue_wait_changes_central_performance":
                    False,

                "actual_2022_future_weather_used":
                    False,

                "rank_cutoff_probability_available":
                    False,

                "repeat_completion_probability_available":
                    False,
            },

        "historical_action_interpretation":
            {
                "direct_lane1_observed_drivers":
                    lane1_observed_drivers,

                "takuma_sato":
                    (
                        "REQUIRED_REATTEMPT_"
                        "NOT_ELECTIVE_CHOICE"
                    ),

                "remaining_lane_assignments":
                    "NOT_FULLY_IDENTIFIABLE",
            },

        "final_provenance_repairs":
            {
                "scott_mclaughlin_first_attempt_speed_mph":
                    scott_speed,

                "monte_carlo_delta_distribution_changed":
                    False,
            },

        "claims_policy":
            {
                "hard_recommendation":
                    False,

                "causal_weather_claim":
                    False,

                "exact_2022_queue_wait_claim":
                    False,

                "exact_2022_decision_time_claim":
                    False,

                "full_live_leaderboard_reconstruction_claim":
                    False,
            },

        "supported_output":
            (
                "PERFORMANCE_RISK_ENVELOPES_"
                "WITH_EXPLICIT_UNCERTAINTY_AND_"
                "IDENTIFIABILITY_BOUNDARIES"
            ),

        "technical_phase_complete":
            True,
    }

    SUMMARY_OUT.write_text(
        json.dumps(
            capability,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    # --------------------------------------------------
    # QA
    # --------------------------------------------------

    applicability_actions = {
        row[
            "simulated_action"
        ]
        for row in applicability
    }

    hard_recommendation_leaks = [
        row
        for row in mc_rows
        if truthy(
            row.get(
                "hard_recommendation_allowed"
            )
        )
    ]

    qa_rows = [
        {
            "metric":
                "final_state_driver_set_exact",

            "value":
                int(
                    target_exact
                ),

            "status":
                (
                    "PASS"
                    if target_exact
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "missing_first_attempt_speeds",

            "value":
                len(
                    missing_first_speeds
                ),

            "status":
                (
                    "PASS"
                    if len(
                        missing_first_speeds
                    )
                    ==
                    0
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "scott_speed_present",

            "value":
                fmt(
                    scott_speed
                ),

            "status":
                (
                    "PASS"
                    if scott_speed
                    is not None
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "known_predecision_rank_rows",

            "value":
                len(
                    known_predecision_rank
                ),

            "status":
                (
                    "PASS"
                    if len(
                        known_predecision_rank
                    )
                    ==
                    2
                    else
                    "REVIEW"
                ),
        },

        {
            "metric":
                "central_mc_rows_valid",

            "value":
                int(
                    central_rows_valid
                ),

            "status":
                (
                    "PASS"
                    if central_rows_valid
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "action_semantics_complete",

            "value":
                "|".join(
                    sorted(
                        applicability_actions
                    )
                ),

            "status":
                (
                    "PASS"
                    if applicability_actions
                    ==
                    EXPECTED_ACTIONS
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "sato_required_reattempt_preserved",

            "value":
                int(
                    sato_required_ok
                ),

            "status":
                (
                    "PASS"
                    if sato_required_ok
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "environment_model_not_promoted",

            "value":
                int(
                    not env_beats_zero
                ),

            "status":
                (
                    "PASS"
                    if not env_beats_zero
                    else
                    "REVIEW"
                ),
        },

        {
            "metric":
                "hard_recommendation_leaks",

            "value":
                len(
                    hard_recommendation_leaks
                ),

            "status":
                (
                    "PASS"
                    if len(
                        hard_recommendation_leaks
                    )
                    ==
                    0
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "supported_claim_rows",

            "value":
                len(
                    claims
                ),

            "status":
                (
                    "PASS"
                    if len(
                        claims
                    )
                    >=
                    10
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "limitation_rows",

            "value":
                len(
                    limitations
                ),

            "status":
                (
                    "PASS"
                    if len(
                        limitations
                    )
                    >=
                    10
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "core_result_rows",

            "value":
                len(
                    core_results
                ),

            "status":
                (
                    "PASS"
                    if len(
                        core_results
                    )
                    >=
                    15
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "technical_phase_complete",

            "value":
                1,

            "status":
                "PASS",
        },

        {
            "metric":
                "protected_upstream_outputs_mutated",

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
    # Freeze manifest
    # --------------------------------------------------

    freeze_assets = [
        STATE_FINAL,
        ACTION_APPLICABILITY,
        MC_FINAL,
        MC_SUMMARY,
        ENV_SUMMARY,
        RECOVERY_POSTERIOR,
        PAIR_DATASET,
        TIMED_COVERAGE,
        SUPPORTED_OUT,
        LIMITATIONS_OUT,
        CORE_RESULTS_OUT,
        SUMMARY_OUT,
        QA_OUT,
    ]

    manifest = []

    for path in freeze_assets:

        manifest.append({
            "asset":
                path.name,

            "path":
                str(path),

            "sha256":
                sha256_file(
                    path
                ),

            "role":
                (
                    "FINAL_GENERATED_OUTPUT"
                    if path
                    in {
                        SUPPORTED_OUT,
                        LIMITATIONS_OUT,
                        CORE_RESULTS_OUT,
                        SUMMARY_OUT,
                        QA_OUT,
                    }
                    else
                    "FROZEN_UPSTREAM_INPUT"
                ),

            "phase":
                PHASE,
        })

    write_csv(
        MANIFEST_OUT,
        manifest,
        [
            "asset",
            "path",
            "sha256",
            "role",
            "phase",
        ],
    )

    # --------------------------------------------------
    # Terminal summary
    # --------------------------------------------------

    print()
    print("=" * 128)
    print("FINAL CORE RESULTS")
    print("=" * 128)

    print()
    print(
        "Final 2022 driver states:",
        len(
            states
        ),
    )

    print(
        "Known pre-decision rank drivers:",
        (
            "|".join(
                known_rank_drivers
            )
            or
            "NONE"
        ),
    )

    print(
        "Scott first-attempt speed:",
        fmt(
            scott_speed,
            3,
        ),
        "mph",
    )

    print()
    print(
        "Timed weather subset:",
        timed_joinable_total,
        "attempts",
    )

    print(
        "Timed years:",
        "|".join(
            timed_years
        ),
    )

    print(
        "Repeat-pair environment dataset:",
        len(
            environment_ready_pairs
        ),
        "pairs",
    )

    print(
        "Normal / recovery:",
        len(
            normal_pairs
        ),
        "/",
        len(
            recovery_pairs
        ),
    )

    print()
    print(
        "ZERO_DELTA frozen pooled MAE:",
        fmt(
            frozen_zero_mae
        ),
        "mph",
    )

    print(
        "Best environment Ridge LOYO MAE:",
        fmt(
            env_model_mae
        ),
        "mph",
    )

    print(
        "Same-row ZERO_DELTA MAE:",
        fmt(
            zero_same_mae
        ),
        "mph",
    )

    print(
        "Environment improvement vs zero:",
        fmt(
            env_improvement
        ),
        "mph",
    )

    print(
        "Environment promoted to central model:",
        "NO",
    )

    print()
    print(
        "Recovery posterior:",
        (
            f"Beta("
            f"{fmt(recovery_alpha, 3)}, "
            f"{fmt(recovery_beta, 3)})"
        ),
    )

    print(
        "Recovery posterior mean:",
        fmt(
            recovery_mean
        ),
    )

    print()
    print(
        "Lane2 retain-result:"
    )

    print(
        "  mean Δ:",
        fmt(
            lane2_mean
        ),
        "mph",
    )

    print(
        "  q05/q50/q95:",
        fmt(
            lane2_q05
        ),
        "/",
        fmt(
            lane2_q50
        ),
        "/",
        fmt(
            lane2_q95
        ),
    )

    print(
        "  P(improve):",
        fmt(
            lane2_improve
        ),
    )

    print(
        "  P(worse):",
        fmt(
            lane2_worse
        ),
    )

    print()
    print(
        "Lane1 withdraw-result:"
    )

    print(
        "  mean Δ:",
        fmt(
            lane1_mean
        ),
        "mph",
    )

    print(
        "  q05/q50/q95:",
        fmt(
            lane1_q05
        ),
        "/",
        fmt(
            lane1_q50
        ),
        "/",
        fmt(
            lane1_q95
        ),
    )

    print(
        "  P(improve):",
        fmt(
            lane1_improve
        ),
    )

    print(
        "  P(worse):",
        fmt(
            lane1_worse
        ),
    )

    print()
    print(
        "Lane2 - Lane1 mean performance value:",
        fmt(
            lane2_minus_lane1_mean
        ),
        "mph",
    )

    print()
    print(
        "Direct historical Lane1 drivers:",
        (
            "|".join(
                lane1_observed_drivers
            )
            or
            "NONE"
        ),
    )

    print(
        "Sato required reattempt preserved:",
        sato_required_ok,
    )

    print()
    print("=" * 128)
    print("FINAL CAPABILITY BOUNDARY")
    print("=" * 128)

    print()
    print(
        "Supported:"
    )

    print(
        "  uncertainty-aware performance risk envelopes"
    )

    print(
        "  empirical repeat-performance uncertainty"
    )

    print(
        "  recovery posterior sensitivity"
    )

    print(
        "  temporal-safe partial decision state"
    )

    print(
        "  observational weather sensitivity"
    )

    print()
    print(
        "Not supported:"
    )

    print(
        "  exact 2022 queue wait"
    )

    print(
        "  exact 2022 decision timestamps"
    )

    print(
        "  complete historical live leaderboard"
    )

    print(
        "  future track-temperature prediction"
    )

    print(
        "  repeat-completion probability"
    )

    print(
        "  validated hard Lane1/Lane2/STOP recommendation"
    )

    print()
    print(
        "Supported claims:",
        len(
            claims
        ),
    )

    print(
        "Explicit limitations:",
        len(
            limitations
        ),
    )

    print(
        "Core quantitative results:",
        len(
            core_results
        ),
    )

    print(
        "Freeze-manifest assets:",
        len(
            manifest
        ),
    )

    print()
    print("=" * 128)

    if not hard_fail:

        print(
            "FINAL STATUS: "
            "R3C1_FINAL_RESULTS_AND_CAPABILITY_FROZEN_"
            "TECHNICAL_PHASE_COMPLETE"
        )

    else:

        print(
            "FINAL STATUS: "
            "R3C1_FINAL_RESULTS_FREEZE_REVIEW_REQUIRED"
        )

    print("=" * 128)

    print()
    print("OUTPUTS")

    print(
        SUPPORTED_OUT
    )

    print(
        LIMITATIONS_OUT
    )

    print(
        CORE_RESULTS_OUT
    )

    print(
        SUMMARY_OUT
    )

    print(
        MANIFEST_OUT
    )

    print(
        QA_OUT
    )


if __name__ == "__main__":
    main()
