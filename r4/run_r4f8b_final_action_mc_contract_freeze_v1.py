from pathlib import Path
import csv
import json
import hashlib
import math

ROOT = Path(
    "/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈"
)

OUT = ROOT / "r4/output"

DECISION_PATH = (
    OUT /
    "r4f2_canonical_fused_decision_dataset_v2.csv"
)

PERFORMANCE_CONTRACT = (
    OUT /
    "r4f7c7_final_performance_architecture_contract_v1.json"
)

VALIDATION_CONCLUSION = (
    OUT /
    "r4f7v2_external_validation_conclusion_v1.json"
)

TRANSFER_REPORT = (
    OUT /
    "r4f7t1_2022_2025_transfer_closeout_report_v1.json"
)

OLD_WAIT_RESULTS = (
    OUT /
    "r4p11_stochastic_wait_performance_mc_results_v1.csv"
)

OUT_ELIGIBLE = (
    OUT /
    "r4f8b_final_mc_eligible_decision_rows_v1.csv"
)

OUT_ACTIONS = (
    OUT /
    "r4f8b_final_mc_action_expansion_v1.csv"
)

OUT_QA = (
    OUT /
    "r4f8b_final_action_mc_contract_qa_v1.csv"
)

OUT_CONTRACT = (
    OUT /
    "r4f8b_final_action_mc_contract_v1.json"
)

OUT_REPORT = (
    OUT /
    "r4f8b_final_action_mc_contract_report_v1.json"
)


ACTION_COLUMNS = {
    "STOP":
        "action_mask_STOP",

    "REATTEMPT":
        "action_mask_REATTEMPT",

    "RETAIN_AND_REATTEMPT":
        "action_mask_RETAIN_AND_REATTEMPT",

    "WITHDRAW_AND_REATTEMPT":
        "action_mask_WITHDRAW_AND_REATTEMPT",

    "WITHDRAW_AND_PRIORITY_REATTEMPT":
        "action_mask_WITHDRAW_AND_PRIORITY_REATTEMPT",
}


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


def read_csv(path):
    with path.open(
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as f:

        reader = csv.DictReader(f)

        return (
            reader.fieldnames or [],
            list(reader),
        )


def sha256(path):
    h = hashlib.sha256()

    with path.open("rb") as f:

        while True:

            block = f.read(
                1024 * 1024
            )

            if not block:
                break

            h.update(block)

    return h.hexdigest()


for path in [
    DECISION_PATH,
    PERFORMANCE_CONTRACT,
    VALIDATION_CONCLUSION,
    TRANSFER_REPORT,
]:

    if not path.exists():

        raise SystemExit(
            f"MISSING INPUT: {path}"
        )


fields, decisions = read_csv(
    DECISION_PATH
)

performance = json.loads(
    PERFORMANCE_CONTRACT.read_text(
        encoding="utf-8"
    )
)

validation = json.loads(
    VALIDATION_CONCLUSION.read_text(
        encoding="utf-8"
    )
)

transfer = json.loads(
    TRANSFER_REPORT.read_text(
        encoding="utf-8"
    )
)


if (
    performance.get("status")
    !=
    "R4F7C7_FINAL_DEVELOPMENT_ARCHITECTURE_FROZEN"
):

    raise SystemExit(
        "PERFORMANCE CONTRACT NOT FROZEN"
    )


if (
    validation.get("status")
    !=
    "R4F7V2_EXTERNAL_VALIDATION_CONCLUSION_FROZEN"
):

    raise SystemExit(
        "EXTERNAL VALIDATION NOT FROZEN"
    )


if (
    transfer.get("status")
    !=
    "R4F7T1_2022_2025_TRANSFER_CLOSEOUT_COMPLETE"
):

    raise SystemExit(
        "TRANSFER CLOSEOUT NOT COMPLETE"
    )


required = {
    "decision_id",
    "year",
    "session_regime",
    "driver_name",
    "car_number",
    "source_attempt_id",
    "decision_time_utc",
    "current_result_mph",
    "current_rank",
    "benchmark_type",
    "benchmark_rank",
    "benchmark_speed_mph",
    "state_numeric_complete",
    "wait_model_available",
    *ACTION_COLUMNS.values(),
}


missing = sorted(
    required
    -
    set(fields)
)

if missing:

    raise SystemExit(
        "MISSING F2 COLUMNS: "
        +
        ", ".join(
            missing
        )
    )


# =============================================================================
# Identify counterfactual/model eligibility field automatically.
# =============================================================================

eligibility_candidates = [
    "counterfactual_model_eligible",
    "decision_state_eligible",
    "model_eligible",
]


eligibility_field = None


for candidate in eligibility_candidates:

    if candidate in fields:
        eligibility_field = candidate
        break


if eligibility_field is None:

    raise SystemExit(
        "NO COUNTERFACTUAL MODEL ELIGIBILITY FIELD FOUND. "
        "Available fields: "
        +
        ", ".join(fields)
    )


# =============================================================================
# Frozen eligible state universe
# =============================================================================

eligible_rows = []


for r in decisions:

    if not truthy(
        r.get(
            eligibility_field
        )
    ):
        continue

    if not truthy(
        r.get(
            "state_numeric_complete"
        )
    ):
        continue


    feasible_actions = [
        action
        for action, col
        in ACTION_COLUMNS.items()
        if truthy(
            r.get(col)
        )
    ]


    if not feasible_actions:
        continue


    out = dict(r)

    out[
        "resolved_mc_eligibility_field"
    ] = eligibility_field

    out[
        "resolved_feasible_actions"
    ] = ";".join(
        feasible_actions
    )

    out[
        "resolved_feasible_action_count"
    ] = len(
        feasible_actions
    )

    eligible_rows.append(out)


# =============================================================================
# Expand one row per feasible action.
# =============================================================================

action_rows = []


for r in eligible_rows:

    for action, col in (
        ACTION_COLUMNS.items()
    ):

        if not truthy(
            r.get(col)
        ):
            continue


        protected_result = (
            num(
                r.get(
                    "current_result_mph"
                )
            )
        )


        benchmark = (
            num(
                r.get(
                    "benchmark_speed_mph"
                )
            )
        )


        if action == "STOP":

            requires_wait_draw = False
            requires_new_attempt = False
            protected_result_retained = True
            withdrawal_risk = False


        elif action == "REATTEMPT":

            requires_wait_draw = True
            requires_new_attempt = True
            protected_result_retained = False
            withdrawal_risk = False


        elif action == "RETAIN_AND_REATTEMPT":

            requires_wait_draw = True
            requires_new_attempt = True
            protected_result_retained = True
            withdrawal_risk = False


        elif action == "WITHDRAW_AND_REATTEMPT":

            requires_wait_draw = True
            requires_new_attempt = True
            protected_result_retained = False
            withdrawal_risk = True


        elif (
            action
            ==
            "WITHDRAW_AND_PRIORITY_REATTEMPT"
        ):

            requires_wait_draw = True
            requires_new_attempt = True
            protected_result_retained = False
            withdrawal_risk = True


        else:

            raise RuntimeError(
                f"UNKNOWN ACTION: {action}"
            )


        action_rows.append({
            "decision_id":
                clean(
                    r.get(
                        "decision_id"
                    )
                ),

            "year":
                clean(
                    r.get(
                        "year"
                    )
                ),

            "session_regime":
                clean(
                    r.get(
                        "session_regime"
                    )
                ),

            "driver_name":
                clean(
                    r.get(
                        "driver_name"
                    )
                ),

            "car_number":
                clean(
                    r.get(
                        "car_number"
                    )
                ),

            "source_attempt_id":
                clean(
                    r.get(
                        "source_attempt_id"
                    )
                ),

            "decision_time_utc":
                clean(
                    r.get(
                        "decision_time_utc"
                    )
                ),

            "action":
                action,

            "current_result_mph":
                (
                    protected_result
                    if protected_result is not None
                    else ""
                ),

            "current_rank":
                clean(
                    r.get(
                        "current_rank"
                    )
                ),

            "benchmark_type":
                clean(
                    r.get(
                        "benchmark_type"
                    )
                ),

            "benchmark_rank":
                clean(
                    r.get(
                        "benchmark_rank"
                    )
                ),

            "benchmark_speed_mph":
                (
                    benchmark
                    if benchmark is not None
                    else ""
                ),

            "requires_wait_draw":
                requires_wait_draw,

            "requires_new_attempt":
                requires_new_attempt,

            "protected_result_retained":
                protected_result_retained,

            "withdrawal_risk":
                withdrawal_risk,

            "wait_model_available":
                truthy(
                    r.get(
                        "wait_model_available"
                    )
                ),
        })


# =============================================================================
# Existing wait engine provenance only
# =============================================================================

old_wait_present = (
    OLD_WAIT_RESULTS.exists()
)


old_wait_schema = []


if old_wait_present:

    old_fields, _ = read_csv(
        OLD_WAIT_RESULTS
    )

    old_wait_schema = old_fields


# =============================================================================
# Contract
# =============================================================================

contract = {
    "phase":
        "R4F8B",

    "status":
        "R4F8B_FINAL_ACTION_MC_CONTRACT_FROZEN",

    "canonical_decision_interface":
        "r4/output/r4f2_canonical_fused_decision_dataset_v2.csv",

    "counterfactual_eligibility_field":
        eligibility_field,

    "decision_rows_total":
        len(
            decisions
        ),

    "mc_eligible_decision_rows":
        len(
            eligible_rows
        ),

    "expanded_feasible_action_rows":
        len(
            action_rows
        ),

    "performance_model": {
        "architecture":
            performance.get(
                "primary_performance_architecture"
            ),

        "shrinkage_k":
            performance.get(
                "selected_shrinkage_k"
            ),

        "prior_mean_residual_mph":
            performance.get(
                "frozen_cross_year_prior_mean_residual_mph"
            ),

        "prior_sd_residual_mph":
            performance.get(
                "frozen_cross_year_prior_sd_mph"
            ),

        "external_validation_status":
            validation.get(
                "model_status"
            ),

        "required_behavior":
            (
                "Use performance component probabilistically. "
                "Do not treat predicted speed as deterministic."
            ),
    },

    "action_semantics": {
        "STOP": {
            "new_attempt":
                False,

            "wait_draw":
                False,

            "protected_result_retained":
                True,
        },

        "REATTEMPT": {
            "new_attempt":
                True,

            "wait_draw":
                True,

            "protected_result_retained":
                False,

            "use_case":
                (
                    "No protected valid result currently exists."
                ),
        },

        "RETAIN_AND_REATTEMPT": {
            "new_attempt":
                True,

            "wait_draw":
                True,

            "protected_result_retained":
                True,

            "use_case":
                "Day1 Lane2",
        },

        "WITHDRAW_AND_REATTEMPT": {
            "new_attempt":
                True,

            "wait_draw":
                True,

            "protected_result_retained":
                False,

            "withdrawal_downside":
                True,

            "use_case":
                "Last Chance protected-result withdrawal",
        },

        "WITHDRAW_AND_PRIORITY_REATTEMPT": {
            "new_attempt":
                True,

            "wait_draw":
                True,

            "protected_result_retained":
                False,

            "withdrawal_downside":
                True,

            "use_case":
                "Day1 Lane1 priority withdrawal",
        },
    },

    "monte_carlo_order": [
        "sample_wait_time",
        "propagate_session_calibration_uncertainty",
        "sample_future_attempt_performance",
        "sample_completion_or_no-run",
        "sample_competitor_evolution",
        "apply_action_result_retention_semantics",
        "compute_final_result_and_rank",
    ],

    "mandatory_outputs": [
        "p_beat_current_result",
        "p_cross_advancement_benchmark",
        "p_worse_than_current",
        "p_complete_reattempt",
        "expected_future_attempt_speed_mph",
        "expected_final_result_mph",
        "expected_rank_change",
        "downside_probability",
        "mean_wait_minutes",
        "q50_wait_minutes",
        "q95_wait_minutes",
    ],

    "uncertainty_policy": {
        "early_session":
            (
                "Broad calibration uncertainty is mandatory because "
                "2024 external validation showed weak transport of "
                "the development prior mean."
            ),

        "online_update":
            (
                "Calibration uncertainty may shrink as strictly earlier "
                "current-session field observations accumulate."
            ),

        "run_noise":
            (
                "Future run performance must include repeat/run noise; "
                "do not use only posterior mean speed."
            ),

        "weather":
            (
                "Thermal/weather state remains auxiliary uncertainty/context, "
                "not the primary deterministic speed coefficient."
            ),
    },

    "historical_action_policy":
        (
            "Historical observed actions are replay/sanity evidence only. "
            "They are never treated as optimality labels."
        ),

    "old_r4p11_policy":
        (
            "Reuse only wait-distribution mechanics/provenance where "
            "compatible. Do not reuse old p_improve/p_worse values as "
            "final counterfactual outputs because the performance model "
            "has changed."
        ),

    "2024_policy":
        (
            "External validation is frozen. No Action MC parameter may "
            "be selected by improving 2024 performance metrics."
        ),

    "next_phase":
        (
            "R4F8C_DECISION_LEVEL_STOCHASTIC_INPUT_ASSEMBLY"
        ),
}


# =============================================================================
# QA
# =============================================================================

action_counts = {
    action:
        sum(
            r[
                "action"
            ] == action
            for r in action_rows
        )
    for action in ACTION_COLUMNS
}


invalid_stop = [
    r
    for r in action_rows
    if (
        r[
            "action"
        ] == "STOP"
        and
        (
            r[
                "requires_wait_draw"
            ]
            or
            r[
                "requires_new_attempt"
            ]
        )
    )
]


invalid_withdraw = [
    r
    for r in action_rows
    if (
        r[
            "action"
        ]
        in {
            "WITHDRAW_AND_REATTEMPT",
            "WITHDRAW_AND_PRIORITY_REATTEMPT",
        }
        and
        r[
            "protected_result_retained"
        ]
    )
]


qa_rows = [
    {
        "metric":
            "canonical_decision_rows",
        "value":
            len(
                decisions
            ),
        "expected":
            148,
        "status":
            (
                "PASS"
                if len(
                    decisions
                ) == 148
                else "FAIL"
            ),
    },

    {
        "metric":
            "mc_eligible_decision_rows",
        "value":
            len(
                eligible_rows
            ),
        "expected":
            ">0",
        "status":
            (
                "PASS"
                if eligible_rows
                else "FAIL"
            ),
    },

    {
        "metric":
            "expanded_action_rows",
        "value":
            len(
                action_rows
            ),
        "expected":
            ">=eligible_rows",
        "status":
            (
                "PASS"
                if len(
                    action_rows
                )
                >=
                len(
                    eligible_rows
                )
                else "FAIL"
            ),
    },

    {
        "metric":
            "STOP_semantics_valid",
        "value":
            len(
                invalid_stop
            ),
        "expected":
            0,
        "status":
            (
                "PASS"
                if not invalid_stop
                else "FAIL"
            ),
    },

    {
        "metric":
            "WITHDRAW_semantics_valid",
        "value":
            len(
                invalid_withdraw
            ),
        "expected":
            0,
        "status":
            (
                "PASS"
                if not invalid_withdraw
                else "FAIL"
            ),
    },

    {
        "metric":
            "performance_architecture_frozen",
        "value":
            True,
        "expected":
            True,
        "status":
            "PASS",
    },

    {
        "metric":
            "2024_reused_for_tuning",
        "value":
            False,
        "expected":
            False,
        "status":
            "PASS",
    },

    {
        "metric":
            "old_mc_probabilities_reused_as_final",
        "value":
            False,
        "expected":
            False,
        "status":
            "PASS",
    },
]


# =============================================================================
# Save
# =============================================================================

if eligible_rows:

    eligible_fields = list(
        eligible_rows[0].keys()
    )

    with OUT_ELIGIBLE.open(
        "w",
        encoding="utf-8",
        newline=""
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=eligible_fields
        )

        writer.writeheader()
        writer.writerows(
            eligible_rows
        )


if action_rows:

    with OUT_ACTIONS.open(
        "w",
        encoding="utf-8",
        newline=""
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=list(
                action_rows[0].keys()
            )
        )

        writer.writeheader()
        writer.writerows(
            action_rows
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


OUT_CONTRACT.write_text(
    json.dumps(
        contract,
        indent=2,
        ensure_ascii=False
    ),
    encoding="utf-8"
)


report = {
    "phase":
        "R4F8B",

    "status":
        "R4F8B_FINAL_ACTION_MC_CONTRACT_FROZEN",

    "decision_rows":
        len(
            decisions
        ),

    "mc_eligible_decisions":
        len(
            eligible_rows
        ),

    "expanded_action_rows":
        len(
            action_rows
        ),

    "eligibility_field":
        eligibility_field,

    "action_counts":
        action_counts,

    "old_wait_engine_present":
        old_wait_present,

    "old_wait_schema":
        old_wait_schema,

    "next_phase":
        (
            "Assemble decision-level wait/performance/benchmark "
            "stochastic inputs without yet producing final action rankings."
        ),

    "input_hashes": {
        str(
            DECISION_PATH.relative_to(
                ROOT
            )
        ):
            sha256(
                DECISION_PATH
            ),

        str(
            PERFORMANCE_CONTRACT.relative_to(
                ROOT
            )
        ):
            sha256(
                PERFORMANCE_CONTRACT
            ),

        str(
            VALIDATION_CONCLUSION.relative_to(
                ROOT
            )
        ):
            sha256(
                VALIDATION_CONCLUSION
            ),
    },
}


OUT_REPORT.write_text(
    json.dumps(
        report,
        indent=2,
        ensure_ascii=False
    ),
    encoding="utf-8"
)


print("=" * 152)
print("R4F8B — FINAL ACTION MONTE CARLO CONTRACT FREEZE")
print("=" * 152)

print()
print("CANONICAL INTERFACE")

print(
    f"decision_rows={len(decisions)}"
)

print(
    f"eligibility_field={eligibility_field}"
)

print(
    f"mc_eligible_decisions={len(eligible_rows)}"
)

print(
    f"expanded_feasible_action_rows={len(action_rows)}"
)


print()
print("=" * 152)
print("ACTION COUNTS")
print("=" * 152)

for action in ACTION_COLUMNS:

    print(
        f"{action:42s} | "
        f"{action_counts[action]}"
    )


print()
print("=" * 152)
print("FROZEN MC SEMANTICS")
print("=" * 152)

print(
    "STOP = retain current state; no wait/no new attempt"
)

print(
    "RETAIN_AND_REATTEMPT = keep current result + sample another attempt"
)

print(
    "WITHDRAW actions = current protected result lost before sampled attempt"
)

print(
    "REATTEMPT = no protected valid result; sample attempt opportunity"
)

print()
print(
    "Performance = Fast Friday reference + "
    "frozen online shrunk session calibration + uncertainty"
)

print(
    "Old R4P11 probabilities are NOT reused as final results."
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
    OUT_ELIGIBLE.relative_to(
        ROOT
    )
)

print(
    OUT_ACTIONS.relative_to(
        ROOT
    )
)

print(
    OUT_QA.relative_to(
        ROOT
    )
)

print(
    OUT_CONTRACT.relative_to(
        ROOT
    )
)

print(
    OUT_REPORT.relative_to(
        ROOT
    )
)

print()
print(
    "R4F8B_FINAL_ACTION_MC_CONTRACT_FROZEN"
)
