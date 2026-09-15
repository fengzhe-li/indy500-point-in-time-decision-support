from pathlib import Path
from collections import Counter
import csv
import json

ROOT = Path(
    "/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈"
)

OUT = ROOT / "r4/output"
OUT.mkdir(parents=True, exist_ok=True)

DAY1_PATH = (
    OUT /
    "r4f1_day1_fused_interface_v1.csv"
)

LC_PATH = (
    OUT /
    "r4lc5e_last_chance_fused_interface_v2.csv"
)

SCHEMA_PATH = (
    OUT /
    "r4lc5e_fused_decision_schema_contract_v2.json"
)

OUT_DATASET = (
    OUT /
    "r4f2_canonical_fused_decision_dataset_v2.csv"
)

OUT_SUMMARY = (
    OUT /
    "r4f2_canonical_fused_decision_summary_v2.csv"
)

OUT_QA = (
    OUT /
    "r4f2_canonical_fused_decision_qa_v2.csv"
)

OUT_REPORT = (
    OUT /
    "r4f2_canonical_fused_decision_report_v2.json"
)


TRAIN_YEARS = {
    2020,
    2021,
    2023,
}

VALIDATION_YEARS = {
    2022,
    2024,
}


ACTIONS = {
    "STOP",
    "REATTEMPT",
    "RETAIN_AND_REATTEMPT",
    "WITHDRAW_AND_REATTEMPT",
    "WITHDRAW_AND_PRIORITY_REATTEMPT",
}

UNRESOLVED_ACTION = (
    "REATTEMPT_SEMANTICS_UNRESOLVED"
)


def clean(v):
    if v is None:
        return ""
    return str(v).strip()


def truth(v):
    return clean(v).lower() in {
        "true",
        "1",
        "yes",
    }


def integer(v):
    s = clean(v)

    if not s:
        return None

    try:
        return int(float(s))

    except Exception:
        return None


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
    DAY1_PATH,
    LC_PATH,
    SCHEMA_PATH,
]:

    if not path.exists():

        raise SystemExit(
            f"MISSING INPUT: {path}"
        )


day1_rows = read_csv(
    DAY1_PATH
)

lc_rows = read_csv(
    LC_PATH
)

schema = json.loads(
    SCHEMA_PATH.read_text(
        encoding="utf-8"
    )
)


print("=" * 124)
print("R4F2-v2 — CANONICAL FUSED DECISION DATASET CONTRACT CORRECTION")
print("=" * 124)

print(
    f"Day1 rows: {len(day1_rows)}"
)

print(
    f"Last Chance rows: {len(lc_rows)}"
)

print(
    f"Frozen schema: "
    f"{schema.get('schema_name')}"
)


# =============================================================================
# Eligibility logic
# =============================================================================

def derive_eligibility(
    *,
    year,
    observed_action,
    action_quality,
    state_numeric_complete,
    decision_time_available,
    upstream_safe_for_policy_fit,
):
    """
    Distinguish:
      1. historical action evidence
      2. usable decision state
      3. counterfactual model input eligibility
      4. validation-only status

    Historical action is NEVER treated as hard optimality truth.
    """

    validation_only = (
        year in VALIDATION_YEARS
    )

    action_resolved = (
        observed_action in ACTIONS
    )

    unresolved_reattempt = (
        observed_action
        == UNRESOLVED_ACTION
    )

    # Historical behaviour can still be useful even when it is not
    # suitable for fitting the final counterfactual model.
    action_evidence_eligible = (
        action_resolved
        and
        (
            clean(
                action_quality
            ).upper()
            in {
                "HIGH",
                "EXACT",
                "PAIR_EXACT",
            }
            or
            upstream_safe_for_policy_fit
        )
    )

    # Decision-state eligibility means the historical decision point has
    # enough observable numeric context to be reconstructed.
    decision_state_eligible = (
        bool(
            state_numeric_complete
        )
        and
        bool(
            decision_time_available
        )
    )

    # Final model-input eligibility is deliberately stricter.
    #
    # Validation years are NEVER allowed into fitting.
    # Resolved historical action is not required because the final model
    # is counterfactual / simulation-based, not behaviour cloning.
    counterfactual_model_input_eligible = (
        year in TRAIN_YEARS
        and
        decision_state_eligible
        and
        not validation_only
    )

    return {
        "validation_only":
            validation_only,

        "action_resolved":
            action_resolved,

        "unresolved_reattempt":
            unresolved_reattempt,

        "action_evidence_eligible":
            action_evidence_eligible,

        "decision_state_eligible":
            decision_state_eligible,

        "counterfactual_model_input_eligible":
            counterfactual_model_input_eligible,
    }


rows = []


# =============================================================================
# DAY1
# =============================================================================

for r in day1_rows:

    year = integer(
        r.get("year")
    )

    observed = clean(
        r.get(
            "observed_action_unified"
        )
    )

    upstream_safe = truth(
        r.get(
            "safe_for_policy_fit"
        )
    )

    state_numeric = truth(
        r.get(
            "state_numeric_complete"
        )
    )

    decision_time = clean(
        r.get(
            "decision_time_utc"
        )
    )

    eligibility = derive_eligibility(
        year=year,
        observed_action=observed,
        action_quality=clean(
            r.get(
                "observed_action_quality"
            )
        ),
        state_numeric_complete=state_numeric,
        decision_time_available=bool(
            decision_time
        ),
        upstream_safe_for_policy_fit=upstream_safe,
    )

    if eligibility[
        "validation_only"
    ]:

        dataset_role = (
            "VALIDATION_ONLY"
        )

    elif eligibility[
        "counterfactual_model_input_eligible"
    ]:

        dataset_role = (
            "COUNTERFACTUAL_MODEL_INPUT"
        )

    elif eligibility[
        "action_evidence_eligible"
    ]:

        dataset_role = (
            "ACTION_EVIDENCE_ONLY"
        )

    elif eligibility[
        "unresolved_reattempt"
    ]:

        dataset_role = (
            "STRUCTURAL_REATTEMPT_EVIDENCE"
        )

    else:

        dataset_role = (
            "HISTORICAL_STATE_EVIDENCE"
        )


    row = {
        "decision_id":
            clean(
                r.get("decision_id")
            ),

        "year":
            year,

        "session_regime":
            "DAY1",

        "car_number":
            clean(
                r.get("car_number")
            ),

        "driver_name":
            clean(
                r.get("driver_name")
            ),

        "decision_stage":
            clean(
                r.get("decision_stage")
            ),

        "source_attempt_id":
            clean(
                r.get("source_attempt_id")
            ),

        "current_result_mph":
            clean(
                r.get(
                    "current_result_mph"
                )
            ),

        "current_rank":
            clean(
                r.get("current_rank")
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
            clean(
                r.get(
                    "benchmark_speed_mph"
                )
            ),

        "margin_to_benchmark_mph":
            clean(
                r.get(
                    "margin_to_benchmark_mph"
                )
            ),

        "qualification_state":
            clean(
                r.get(
                    "qualification_state"
                )
            ),

        "has_protected_result":
            clean(
                r.get(
                    "has_protected_result"
                )
            ),

        "feasible_action_set":
            clean(
                r.get(
                    "feasible_action_set"
                )
            ),

        "action_mask_STOP":
            clean(
                r.get(
                    "action_mask_STOP"
                )
            ),

        "action_mask_REATTEMPT":
            clean(
                r.get(
                    "action_mask_REATTEMPT"
                )
            ),

        "action_mask_RETAIN_AND_REATTEMPT":
            clean(
                r.get(
                    "action_mask_RETAIN_AND_REATTEMPT"
                )
            ),

        "action_mask_WITHDRAW_AND_REATTEMPT":
            clean(
                r.get(
                    "action_mask_WITHDRAW_AND_REATTEMPT"
                )
            ),

        "action_mask_WITHDRAW_AND_PRIORITY_REATTEMPT":
            clean(
                r.get(
                    "action_mask_WITHDRAW_AND_PRIORITY_REATTEMPT"
                )
            ),

        "observed_action":
            observed,

        "action_resolved":
            eligibility[
                "action_resolved"
            ],

        "action_evidence_quality":
            clean(
                r.get(
                    "observed_action_quality"
                )
            ),

        "decision_time_utc":
            decision_time,

        "time_quality":
            clean(
                r.get(
                    "time_quality"
                )
            ),

        "state_numeric_complete":
            state_numeric,

        "thermal_state_available":
            truth(
                r.get(
                    "thermal_state_available"
                )
            ),

        "performance_uncertainty_available":
            truth(
                r.get(
                    "performance_uncertainty_available"
                )
            ),

        "wait_model_available":
            truth(
                r.get(
                    "wait_model_available"
                )
            ),

        "shared_feature_link_status":
            clean(
                r.get(
                    "shared_feature_link_status"
                )
            ),

        # ---------------------------------------------------------------------
        # Corrected eligibility contract
        # ---------------------------------------------------------------------

        "upstream_safe_for_policy_fit":
            upstream_safe,

        "action_evidence_eligible":
            eligibility[
                "action_evidence_eligible"
            ],

        "decision_state_eligible":
            eligibility[
                "decision_state_eligible"
            ],

        "counterfactual_model_input_eligible":
            eligibility[
                "counterfactual_model_input_eligible"
            ],

        "validation_only":
            eligibility[
                "validation_only"
            ],

        "dataset_role":
            dataset_role,

        "hard_optimality_truth":
            False,

        "source_interface":
            "R4F1_DAY1",
    }

    rows.append(
        row
    )


# =============================================================================
# LAST CHANCE
# =============================================================================

for r in lc_rows:

    year = integer(
        r.get("year")
    )

    observed = clean(
        r.get(
            "observed_action_unified"
        )
    )

    upstream_safe = truth(
        r.get(
            "safe_for_policy_fit"
        )
    )

    current_numeric = bool(
        clean(
            r.get(
                "current_result_mph"
            )
        )
    )

    benchmark_numeric = bool(
        clean(
            r.get(
                "benchmark_speed_mph"
            )
        )
    )

    state_numeric = (
        current_numeric
        and
        benchmark_numeric
    )

    decision_time = clean(
        r.get(
            "exact_timestamp"
        )
    )

    eligibility = derive_eligibility(
        year=year,
        observed_action=observed,
        action_quality=clean(
            r.get(
                "action_quality"
            )
        ),
        state_numeric_complete=state_numeric,
        decision_time_available=bool(
            decision_time
        ),
        upstream_safe_for_policy_fit=upstream_safe,
    )

    if eligibility[
        "validation_only"
    ]:

        dataset_role = (
            "VALIDATION_ONLY"
        )

    elif eligibility[
        "counterfactual_model_input_eligible"
    ]:

        dataset_role = (
            "COUNTERFACTUAL_MODEL_INPUT"
        )

    elif eligibility[
        "action_evidence_eligible"
    ]:

        dataset_role = (
            "ACTION_EVIDENCE_ONLY"
        )

    else:

        dataset_role = (
            "HISTORICAL_REPLAY_OR_STATE_EVIDENCE"
        )


    row = {
        "decision_id":
            clean(
                r.get("decision_id")
            ),

        "year":
            year,

        "session_regime":
            "LAST_CHANCE",

        "car_number":
            clean(
                r.get("car_number")
            ),

        "driver_name":
            clean(
                r.get("driver_name")
            ),

        "decision_stage":
            clean(
                r.get("decision_stage")
            ),

        "source_attempt_id":
            "",

        "current_result_mph":
            clean(
                r.get(
                    "current_result_mph"
                )
            ),

        "current_rank":
            clean(
                r.get("current_rank")
            ),

        "benchmark_type":
            clean(
                r.get(
                    "benchmark_type"
                )
            ),

        "benchmark_rank":
            "",

        "benchmark_speed_mph":
            clean(
                r.get(
                    "benchmark_speed_mph"
                )
            ),

        "margin_to_benchmark_mph":
            clean(
                r.get(
                    "margin_to_benchmark_mph"
                )
            ),

        "qualification_state":
            clean(
                r.get(
                    "qualification_state"
                )
            ),

        "has_protected_result":
            clean(
                r.get(
                    "has_protected_result"
                )
            ),

        "feasible_action_set":
            clean(
                r.get(
                    "feasible_action_set"
                )
            ),

        "action_mask_STOP":
            clean(
                r.get(
                    "action_mask_STOP"
                )
            ),

        "action_mask_REATTEMPT":
            clean(
                r.get(
                    "action_mask_REATTEMPT"
                )
            ),

        "action_mask_RETAIN_AND_REATTEMPT":
            clean(
                r.get(
                    "action_mask_RETAIN_AND_REATTEMPT"
                )
            ),

        "action_mask_WITHDRAW_AND_REATTEMPT":
            clean(
                r.get(
                    "action_mask_WITHDRAW_AND_REATTEMPT"
                )
            ),

        "action_mask_WITHDRAW_AND_PRIORITY_REATTEMPT":
            clean(
                r.get(
                    "action_mask_WITHDRAW_AND_PRIORITY_REATTEMPT"
                )
            ),

        "observed_action":
            observed,

        "action_resolved":
            eligibility[
                "action_resolved"
            ],

        "action_evidence_quality":
            clean(
                r.get(
                    "action_quality"
                )
            ),

        "decision_time_utc":
            decision_time,

        "time_quality":
            clean(
                r.get(
                    "time_quality"
                )
            ),

        "state_numeric_complete":
            state_numeric,

        "thermal_state_available":
            truth(
                r.get(
                    "thermal_state_available"
                )
            ),

        "performance_uncertainty_available":
            truth(
                r.get(
                    "performance_uncertainty_available"
                )
            ),

        "wait_model_available":
            truth(
                r.get(
                    "wait_model_available"
                )
            ),

        "shared_feature_link_status":
            clean(
                r.get(
                    "shared_feature_link_status"
                )
            ),

        # ---------------------------------------------------------------------
        # Corrected eligibility contract
        # ---------------------------------------------------------------------

        "upstream_safe_for_policy_fit":
            upstream_safe,

        "action_evidence_eligible":
            eligibility[
                "action_evidence_eligible"
            ],

        "decision_state_eligible":
            eligibility[
                "decision_state_eligible"
            ],

        "counterfactual_model_input_eligible":
            eligibility[
                "counterfactual_model_input_eligible"
            ],

        "validation_only":
            eligibility[
                "validation_only"
            ],

        "dataset_role":
            dataset_role,

        "hard_optimality_truth":
            False,

        "source_interface":
            "R4LC5E_V2",
    }

    rows.append(
        row
    )


# =============================================================================
# QA
# =============================================================================

ids = [
    r[
        "decision_id"
    ]
    for r in rows
]

duplicate_ids = [
    decision_id
    for decision_id, count
    in Counter(ids).items()
    if count > 1
]


validation_model_leak = [
    r
    for r in rows
    if (
        r[
            "validation_only"
        ]
        and
        r[
            "counterfactual_model_input_eligible"
        ]
    )
]


validation_action_fit_leak = [
    r
    for r in rows
    if (
        r[
            "validation_only"
        ]
        and
        r[
            "year"
        ] not in VALIDATION_YEARS
    )
]


hard_truth_rows = [
    r
    for r in rows
    if r[
        "hard_optimality_truth"
    ]
]


invalid_actions = [
    r
    for r in rows
    if (
        r[
            "observed_action"
        ]
        not in ACTIONS
        and
        r[
            "observed_action"
        ]
        != UNRESOLVED_ACTION
    )
]


bad_counterfactual_rows = [
    r
    for r in rows
    if (
        r[
            "counterfactual_model_input_eligible"
        ]
        and
        not r[
            "decision_state_eligible"
        ]
    )
]


qa_rows = [
    {
        "metric":
            "all_rows_preserved",

        "value":
            len(rows),

        "expected":
            len(day1_rows)
            + len(lc_rows),

        "status":
            (
                "PASS"
                if len(rows)
                ==
                len(day1_rows)
                + len(lc_rows)
                else "FAIL"
            ),
    },

    {
        "metric":
            "decision_ids_unique",

        "value":
            len(
                duplicate_ids
            ),

        "expected":
            0,

        "status":
            (
                "PASS"
                if not duplicate_ids
                else "FAIL"
            ),
    },

    {
        "metric":
            "validation_counterfactual_model_leakage",

        "value":
            len(
                validation_model_leak
            ),

        "expected":
            0,

        "status":
            (
                "PASS"
                if not validation_model_leak
                else "FAIL"
            ),
    },

    {
        "metric":
            "validation_year_flags_consistent",

        "value":
            len(
                validation_action_fit_leak
            ),

        "expected":
            0,

        "status":
            (
                "PASS"
                if not validation_action_fit_leak
                else "FAIL"
            ),
    },

    {
        "metric":
            "counterfactual_input_requires_decision_state",

        "value":
            len(
                bad_counterfactual_rows
            ),

        "expected":
            0,

        "status":
            (
                "PASS"
                if not bad_counterfactual_rows
                else "FAIL"
            ),
    },

    {
        "metric":
            "no_hard_optimality_truth",

        "value":
            len(
                hard_truth_rows
            ),

        "expected":
            0,

        "status":
            (
                "PASS"
                if not hard_truth_rows
                else "FAIL"
            ),
    },

    {
        "metric":
            "only_valid_or_explicitly_unresolved_actions",

        "value":
            len(
                invalid_actions
            ),

        "expected":
            0,

        "status":
            (
                "PASS"
                if not invalid_actions
                else "FAIL"
            ),
    },

    {
        "metric":
            "both_regimes_present",

        "value":
            ";".join(
                sorted(
                    {
                        r[
                            "session_regime"
                        ]
                        for r in rows
                    }
                )
            ),

        "expected":
            "DAY1;LAST_CHANCE",

        "status":
            (
                "PASS"
                if {
                    r[
                        "session_regime"
                    ]
                    for r in rows
                }
                ==
                {
                    "DAY1",
                    "LAST_CHANCE",
                }
                else "FAIL"
            ),
    },
]


# =============================================================================
# Summary
# =============================================================================

summary_rows = []

for regime in [
    "DAY1",
    "LAST_CHANCE",
]:

    years = sorted(
        {
            r[
                "year"
            ]
            for r in rows
            if r[
                "session_regime"
            ] == regime
        }
    )

    for year in years:

        subset = [
            r
            for r in rows
            if (
                r[
                    "session_regime"
                ] == regime
                and
                r[
                    "year"
                ] == year
            )
        ]

        actions = Counter(
            r[
                "observed_action"
            ]
            for r in subset
        )

        roles = Counter(
            r[
                "dataset_role"
            ]
            for r in subset
        )

        summary_rows.append({
            "session_regime":
                regime,

            "year":
                year,

            "rows":
                len(subset),

            "validation_rows":
                sum(
                    bool(
                        r[
                            "validation_only"
                        ]
                    )
                    for r in subset
                ),

            "action_evidence_rows":
                sum(
                    bool(
                        r[
                            "action_evidence_eligible"
                        ]
                    )
                    for r in subset
                ),

            "decision_state_rows":
                sum(
                    bool(
                        r[
                            "decision_state_eligible"
                        ]
                    )
                    for r in subset
                ),

            "counterfactual_model_input_rows":
                sum(
                    bool(
                        r[
                            "counterfactual_model_input_eligible"
                        ]
                    )
                    for r in subset
                ),

            "STOP":
                actions.get(
                    "STOP",
                    0
                ),

            "REATTEMPT":
                actions.get(
                    "REATTEMPT",
                    0
                ),

            "RETAIN_AND_REATTEMPT":
                actions.get(
                    "RETAIN_AND_REATTEMPT",
                    0
                ),

            "WITHDRAW_AND_REATTEMPT":
                actions.get(
                    "WITHDRAW_AND_REATTEMPT",
                    0
                ),

            "WITHDRAW_AND_PRIORITY_REATTEMPT":
                actions.get(
                    "WITHDRAW_AND_PRIORITY_REATTEMPT",
                    0
                ),

            "UNRESOLVED":
                actions.get(
                    UNRESOLVED_ACTION,
                    0
                ),

            "roles":
                ";".join(
                    f"{k}:{v}"
                    for k, v
                    in sorted(
                        roles.items()
                    )
                ),
        })


# =============================================================================
# Save
# =============================================================================

with OUT_DATASET.open(
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
        "R4F2_V2",

    "status":
        "R4F2_V2_CANONICAL_FUSED_DECISION_CONTRACT_CORRECTED",

    "schema_name":
        schema.get(
            "schema_name"
        ),

    "rows":
        len(rows),

    "day1_rows":
        len(day1_rows),

    "last_chance_rows":
        len(lc_rows),

    "validation_years":
        sorted(
            VALIDATION_YEARS
        ),

    "action_evidence_rows":
        sum(
            bool(
                r[
                    "action_evidence_eligible"
                ]
            )
            for r in rows
        ),

    "decision_state_rows":
        sum(
            bool(
                r[
                    "decision_state_eligible"
                ]
            )
            for r in rows
        ),

    "counterfactual_model_input_rows":
        sum(
            bool(
                r[
                    "counterfactual_model_input_eligible"
                ]
            )
            for r in rows
        ),

    "corrections": [
        (
            "Validation-year rows can never enter "
            "counterfactual model fitting."
        ),

        (
            "The previous safe_for_policy_fit concept is "
            "retained only as upstream audit evidence."
        ),

        (
            "Historical action evidence, decision-state "
            "eligibility and counterfactual-model eligibility "
            "are now separate fields."
        ),

        (
            "Historical observed actions are never treated "
            "as hard optimality truth."
        ),
    ],

    "next_phase":
        (
            "Freeze corrected Fused decision dataset, then "
            "build probabilistic counterfactual decision engines."
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
print("CORRECTED FUSED DATASET SUMMARY")
print("=" * 124)

print(
    f"Rows: {len(rows)}"
)

print(
    f"Day1: {len(day1_rows)}"
)

print(
    f"Last Chance: {len(lc_rows)}"
)

print(
    "Action-evidence eligible: "
    f"{sum(bool(r['action_evidence_eligible']) for r in rows)}"
)

print(
    "Decision-state eligible: "
    f"{sum(bool(r['decision_state_eligible']) for r in rows)}"
)

print(
    "Counterfactual-model eligible: "
    f"{sum(bool(r['counterfactual_model_input_eligible']) for r in rows)}"
)

print(
    "Validation rows: "
    f"{sum(bool(r['validation_only']) for r in rows)}"
)


print()
print("=" * 124)
print("REGIME / YEAR ELIGIBILITY")
print("=" * 124)

for r in summary_rows:

    print(
        f"{r['session_regime']:12s} | "
        f"{r['year']} | "
        f"rows={r['rows']:3d} | "
        f"validation={r['validation_rows']:3d} | "
        f"action_ev={r['action_evidence_rows']:3d} | "
        f"state={r['decision_state_rows']:3d} | "
        f"model={r['counterfactual_model_input_rows']:3d}"
    )


print()
print("=" * 124)
print("VALIDATION LEAKAGE CHECK")
print("=" * 124)

for year in sorted(
    VALIDATION_YEARS
):

    subset = [
        r
        for r in rows
        if r[
            "year"
        ] == year
    ]

    print(
        f"{year} | "
        f"rows={len(subset)} | "
        f"counterfactual_model_input="
        f"{sum(bool(r['counterfactual_model_input_eligible']) for r in subset)}"
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
    f"{len(qa_rows)-len(fails)}/"
    f"{len(qa_rows)} PASS"
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
    OUT_DATASET.relative_to(ROOT)
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
    "R4F2_V2_CANONICAL_FUSED_DECISION_CONTRACT_CORRECTED"
)
