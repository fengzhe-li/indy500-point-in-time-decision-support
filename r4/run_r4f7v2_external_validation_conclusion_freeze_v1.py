from pathlib import Path
import json
import csv
import hashlib

ROOT = Path(
    "/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈"
)

OUT = ROOT / "r4/output"

DEV_CONTRACT = (
    OUT /
    "r4f7c7_final_performance_architecture_contract_v1.json"
)

VAL_REPORT = (
    OUT /
    "r4f7v1_2024_one_shot_validation_report_v1.json"
)

VAL_METRICS = (
    OUT /
    "r4f7v1_2024_one_shot_validation_metrics_v1.csv"
)

OUT_CONCLUSION = (
    OUT /
    "r4f7v2_external_validation_conclusion_v1.json"
)

OUT_SUMMARY = (
    OUT /
    "r4f7v2_external_validation_summary_v1.csv"
)

OUT_QA = (
    OUT /
    "r4f7v2_external_validation_conclusion_qa_v1.csv"
)


def sha256(path):
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
    DEV_CONTRACT,
    VAL_REPORT,
    VAL_METRICS,
]:

    if not path.exists():
        raise SystemExit(
            f"MISSING INPUT: {path}"
        )


contract = json.loads(
    DEV_CONTRACT.read_text(
        encoding="utf-8"
    )
)

report = json.loads(
    VAL_REPORT.read_text(
        encoding="utf-8"
    )
)

metrics = read_csv(
    VAL_METRICS
)


if (
    contract.get("status")
    !=
    "R4F7C7_FINAL_DEVELOPMENT_ARCHITECTURE_FROZEN"
):

    raise SystemExit(
        "DEVELOPMENT ARCHITECTURE NOT FROZEN"
    )


if (
    report.get("status")
    !=
    "R4F7V1_2024_ONE_SHOT_FINAL_VALIDATION_COMPLETE"
):

    raise SystemExit(
        "2024 ONE-SHOT VALIDATION NOT COMPLETE"
    )


def get_metric(
    model,
    scope,
):

    for r in metrics:

        if (
            r.get("model") == model
            and
            r.get("scope") == scope
        ):

            return {
                "n":
                    int(
                        float(
                            r["n"]
                        )
                    ),

                "mae":
                    float(
                        r["mae_mph"]
                    ),

                "rmse":
                    float(
                        r["rmse_mph"]
                    ),

                "bias":
                    float(
                        r["bias_mph"]
                    ),
            }

    return None


reference_all = get_metric(
    "FAST_FRIDAY_REFERENCE_ONLY",
    "ALL_2024_VALIDATION",
)

primary_all = get_metric(
    "FROZEN_PRIMARY_ONLINE_SHRUNK_FIELD_MEAN",
    "ALL_2024_VALIDATION",
)

prior_all = get_metric(
    "FROZEN_CROSS_YEAR_PRIOR_CALIBRATION",
    "ALL_2024_VALIDATION",
)

reference_ge3 = get_metric(
    "FAST_FRIDAY_REFERENCE_ONLY",
    "PAST_OTHER_GE_3",
)

primary_ge3 = get_metric(
    "FROZEN_PRIMARY_ONLINE_SHRUNK_FIELD_MEAN",
    "PAST_OTHER_GE_3",
)


required_metrics = [
    reference_all,
    primary_all,
    prior_all,
    reference_ge3,
    primary_ge3,
]


if any(
    x is None
    for x in required_metrics
):

    raise SystemExit(
        "EXPECTED VALIDATION METRICS NOT FOUND"
    )


validation_residual = report[
    "actual_2024_reference_residual"
]

prior_mean = report[
    "frozen_parameters"
][
    "prior_mean_residual_mph"
]

prior_shift = (
    validation_residual[
        "mean_mph"
    ]
    -
    prior_mean
)


all6_primary_delta_vs_reference = (
    reference_all["mae"]
    -
    primary_all["mae"]
)

ge3_primary_delta_vs_reference = (
    reference_ge3["mae"]
    -
    primary_ge3["mae"]
)


summary_rows = [
    {
        "scope":
            "ALL_2024",

        "n":
            primary_all["n"],

        "reference_mae_mph":
            reference_all["mae"],

        "primary_mae_mph":
            primary_all["mae"],

        "primary_gain_vs_reference_mph":
            all6_primary_delta_vs_reference,

        "interpretation":
            (
                "PRIMARY_WORSE_THAN_RAW_REFERENCE"
                if all6_primary_delta_vs_reference < 0
                else
                "PRIMARY_BETTER_THAN_RAW_REFERENCE"
            ),
    },

    {
        "scope":
            "PAST_OTHER_GE_3",

        "n":
            primary_ge3["n"],

        "reference_mae_mph":
            reference_ge3["mae"],

        "primary_mae_mph":
            primary_ge3["mae"],

        "primary_gain_vs_reference_mph":
            ge3_primary_delta_vs_reference,

        "interpretation":
            (
                "PRIMARY_BETTER_ON_SMALL_SUPPORTED_SUBSET"
                if ge3_primary_delta_vs_reference > 0
                else
                "PRIMARY_NOT_BETTER_ON_SUPPORTED_SUBSET"
            ),
    },
]


conclusion = {
    "phase":
        "R4F7V2",

    "status":
        "R4F7V2_EXTERNAL_VALIDATION_CONCLUSION_FROZEN",

    "development_architecture":
        (
            "FAST_FRIDAY_REFERENCE_PLUS_ONLINE_SHRUNK_FIELD_CALIBRATION"
        ),

    "frozen_development_parameters": {
        "shrinkage_k":
            contract[
                "selected_shrinkage_k"
            ],

        "prior_mean_residual_mph":
            prior_mean,

        "prior_sd_residual_mph":
            report[
                "frozen_parameters"
            ][
                "prior_sd_residual_mph"
            ],
    },

    "2024_external_validation": {
        "n":
            primary_all["n"],

        "fast_friday_reference_mae_mph":
            reference_all["mae"],

        "primary_online_shrinkage_mae_mph":
            primary_all["mae"],

        "frozen_cross_year_prior_mae_mph":
            prior_all["mae"],

        "primary_gain_vs_reference_mph":
            all6_primary_delta_vs_reference,

        "actual_reference_residual_mean_mph":
            validation_residual[
                "mean_mph"
            ],

        "frozen_development_prior_mean_mph":
            prior_mean,

        "validation_minus_development_prior_shift_mph":
            prior_shift,
    },

    "supported_subset_past_other_ge_3": {
        "n":
            primary_ge3["n"],

        "reference_mae_mph":
            reference_ge3["mae"],

        "primary_mae_mph":
            primary_ge3["mae"],

        "primary_gain_vs_reference_mph":
            ge3_primary_delta_vs_reference,
    },

    "frozen_interpretation": {
        "overall":
            (
                "The frozen online shrinkage model did not outperform "
                "the raw Fast Friday reference across all six strict "
                "2024 external-validation observations."
            ),

        "prior_transport":
            (
                "The development prior mean did not transport cleanly "
                "to 2024. Early-session predictions were vulnerable to "
                "negative transfer when current-session evidence was sparse."
            ),

        "online_evidence":
            (
                "After at least three strictly earlier other-driver "
                "observations, the frozen shrinkage model showed lower "
                "MAE than the raw reference in the small n=3 subset. "
                "This is supportive but not statistically strong evidence."
            ),

        "complexity":
            (
                "No evidence justifies reopening Kalman, Huber, or "
                "static thermal models."
            ),

        "uncertainty":
            (
                "The final decision simulator must represent substantial "
                "early-session calibration uncertainty and reduce that "
                "uncertainty only as current-session evidence accumulates."
            ),
    },

    "prohibited_post_validation_actions": [
        "DO_NOT_RETUNE_SHRINKAGE_K_ON_2024",
        "DO_NOT_RETUNE_PRIOR_MEAN_ON_2024",
        "DO_NOT_SELECT_NEW_FEATURES_USING_2024",
        "DO_NOT_REOPEN_KALMAN_BASED_ON_2024",
        "DO_NOT_DELETE_2024_ROWS_TO_IMPROVE_METRICS",
    ],

    "model_status":
        (
            "DEVELOPMENT_SUPPORTED_EXTERNAL_VALIDATION_MIXED"
        ),

    "performance_model_role":
        (
            "Use as probabilistic entry-strength plus online session-"
            "calibration component inside the decision Monte Carlo, "
            "not as a deterministic speed oracle."
        ),

    "remaining_validation": {
        "2022":
            "DEGRADED_CHRONOLOGY_ROBUSTNESS",

        "2025":
            "TECHNICAL_REGIME_TRANSFER",
    },

    "next_major_engineering_stage":
        (
            "PERFORMANCE_UNCERTAINTY_TO_ACTION_MONTE_CARLO_INTEGRATION"
        ),

    "input_hashes": {
        str(
            DEV_CONTRACT.relative_to(
                ROOT
            )
        ):
            sha256(
                DEV_CONTRACT
            ),

        str(
            VAL_REPORT.relative_to(
                ROOT
            )
        ):
            sha256(
                VAL_REPORT
            ),

        str(
            VAL_METRICS.relative_to(
                ROOT
            )
        ):
            sha256(
                VAL_METRICS
            ),
    },
}


OUT_CONCLUSION.write_text(
    json.dumps(
        conclusion,
        indent=2,
        ensure_ascii=False
    ),
    encoding="utf-8"
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


qa_rows = [
    {
        "metric":
            "2024_validation_n",
        "value":
            primary_all["n"],
        "expected":
            6,
        "status":
            (
                "PASS"
                if primary_all["n"] == 6
                else "FAIL"
            ),
    },

    {
        "metric":
            "frozen_k_unchanged",
        "value":
            contract[
                "selected_shrinkage_k"
            ],
        "expected":
            3.0,
        "status":
            (
                "PASS"
                if float(
                    contract[
                        "selected_shrinkage_k"
                    ]
                ) == 3.0
                else "FAIL"
            ),
    },

    {
        "metric":
            "primary_worse_than_reference_all6_recorded",
        "value":
            all6_primary_delta_vs_reference < 0,
        "expected":
            True,
        "status":
            (
                "PASS"
                if all6_primary_delta_vs_reference < 0
                else "FAIL"
            ),
    },

    {
        "metric":
            "supported_subset_n",
        "value":
            primary_ge3["n"],
        "expected":
            3,
        "status":
            (
                "PASS"
                if primary_ge3["n"] == 3
                else "FAIL"
            ),
    },

    {
        "metric":
            "supported_subset_gain_recorded",
        "value":
            ge3_primary_delta_vs_reference,
        "expected":
            ">0",
        "status":
            (
                "PASS"
                if ge3_primary_delta_vs_reference > 0
                else "WARN"
            ),
    },

    {
        "metric":
            "2024_parameter_refit_performed",
        "value":
            False,
        "expected":
            False,
        "status":
            "PASS",
    },

    {
        "metric":
            "performance_model_interpreted_deterministically",
        "value":
            False,
        "expected":
            False,
        "status":
            "PASS",
    },
]


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


print("=" * 152)
print("R4F7V2 — EXTERNAL VALIDATION CONCLUSION FREEZE")
print("=" * 152)

print()
print("2024 EXTERNAL VALIDATION")

print(
    f"Raw Fast Friday MAE: "
    f"{reference_all['mae']:.6f}"
)

print(
    f"Frozen primary MAE: "
    f"{primary_all['mae']:.6f}"
)

print(
    f"Frozen prior MAE: "
    f"{prior_all['mae']:.6f}"
)

print(
    f"Primary gain vs reference: "
    f"{all6_primary_delta_vs_reference:+.6f}"
)

print()
print("PRIOR TRANSPORT")

print(
    f"Development frozen prior mean: "
    f"{prior_mean:+.6f}"
)

print(
    f"2024 actual residual mean: "
    f"{validation_residual['mean_mph']:+.6f}"
)

print(
    f"2024 - development prior shift: "
    f"{prior_shift:+.6f} mph"
)

print()
print("SUPPORTED SUBSET — PAST OTHER >= 3")

print(
    f"n={primary_ge3['n']}"
)

print(
    f"Raw reference MAE: "
    f"{reference_ge3['mae']:.6f}"
)

print(
    f"Frozen primary MAE: "
    f"{primary_ge3['mae']:.6f}"
)

print(
    f"Primary gain vs reference: "
    f"{ge3_primary_delta_vs_reference:+.6f}"
)

print()
print("FROZEN CONCLUSION")

print(
    "DEVELOPMENT_SUPPORTED_EXTERNAL_VALIDATION_MIXED"
)

print(
    "No post-hoc 2024 retuning permitted."
)

print(
    "Carry broad early-session uncertainty into action Monte Carlo."
)


fails = [
    r
    for r in qa_rows
    if r[
        "status"
    ] == "FAIL"
]

warns = [
    r
    for r in qa_rows
    if r[
        "status"
    ] == "WARN"
]


print()
print(
    f"QA: "
    f"{len(qa_rows)-len(fails)-len(warns)} PASS | "
    f"{len(warns)} WARN | "
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
    OUT_CONCLUSION.relative_to(
        ROOT
    )
)

print(
    OUT_SUMMARY.relative_to(
        ROOT
    )
)

print(
    OUT_QA.relative_to(
        ROOT
    )
)

print()
print(
    "R4F7V2_EXTERNAL_VALIDATION_CONCLUSION_FROZEN"
)
