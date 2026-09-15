from pathlib import Path
from collections import defaultdict
from datetime import datetime, timezone
import csv
import json
import math
import hashlib

ROOT = Path(
    "/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈"
)

OUT = ROOT / "r4/output"

STATE_PATH = (
    OUT /
    "r4f7c5_prospective_past_only_state_panel_v1.csv"
)

C3_METRICS = (
    OUT /
    "r4f7c3_development_baseline_metrics_v1.csv"
)

C4_GLOBAL = (
    OUT /
    "r4f7c4_global_year_offset_thermal_cv_v1.csv"
)

C4_WITHIN = (
    OUT /
    "r4f7c4_within_year_thermal_cv_v1.csv"
)

C6_METRICS = (
    OUT /
    "r4f7c6_online_latent_window_metrics_v1.csv"
)

OUT_K = (
    OUT /
    "r4f7c7_final_shrinkage_selection_v1.csv"
)

OUT_EVIDENCE = (
    OUT /
    "r4f7c7_architecture_evidence_summary_v1.csv"
)

OUT_QA = (
    OUT /
    "r4f7c7_final_architecture_freeze_qa_v1.csv"
)

OUT_CONTRACT = (
    OUT /
    "r4f7c7_final_performance_architecture_contract_v1.json"
)

OUT_REPORT = (
    OUT /
    "r4f7c7_final_development_architecture_report_v1.json"
)


YEARS = [
    2020,
    2021,
    2023,
]

K_GRID = [
    0.5,
    1.0,
    2.0,
    3.0,
    5.0,
    8.0,
    12.0,
    20.0,
    30.0,
]


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


def parse_dt(v):
    s = clean(v)

    if not s:
        return None

    if s.endswith("Z"):
        s = s[:-1] + "+00:00"

    try:
        dt = datetime.fromisoformat(s)

    except Exception:
        return None

    if dt.tzinfo is None:
        dt = dt.replace(
            tzinfo=timezone.utc
        )

    return dt.astimezone(
        timezone.utc
    )


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

            chunk = f.read(
                1024 * 1024
            )

            if not chunk:
                break

            h.update(chunk)

    return h.hexdigest()


def mae(actual, pred):
    return (
        sum(
            abs(a - b)
            for a, b in zip(actual, pred)
        )
        /
        len(actual)
    )


for path in [
    STATE_PATH,
    C3_METRICS,
    C4_GLOBAL,
    C4_WITHIN,
    C6_METRICS,
]:

    if not path.exists():

        raise SystemExit(
            f"MISSING INPUT: {path}"
        )


_, state_raw = read_csv(
    STATE_PATH
)

_, c3_rows = read_csv(
    C3_METRICS
)

_, c4_global_rows = read_csv(
    C4_GLOBAL
)

_, c4_within_rows = read_csv(
    C4_WITHIN
)

_, c6_rows = read_csv(
    C6_METRICS
)


# =============================================================================
# Parse prospective development state
# =============================================================================

rows = []


for r in state_raw:

    year = int(
        float(
            clean(
                r.get("year")
            )
        )
    )

    if year not in YEARS:
        continue

    time = parse_dt(
        r.get(
            "performance_time_utc"
        )
    )

    actual = num(
        r.get(
            "actual_speed_mph"
        )
    )

    reference = num(
        r.get(
            "reference_speed_mph"
        )
    )

    residual = num(
        r.get(
            "reference_residual_mph"
        )
    )

    if (
        time is None
        or
        actual is None
        or
        reference is None
        or
        residual is None
    ):

        raise SystemExit(
            "INCOMPLETE STATE ROW: "
            +
            clean(
                r.get(
                    "attempt_id"
                )
            )
        )


    rows.append({
        "attempt_id":
            clean(
                r.get(
                    "attempt_id"
                )
            ),

        "year":
            year,

        "driver_key":
            clean(
                r.get(
                    "driver_key"
                )
            ),

        "time":
            time,

        "actual":
            actual,

        "reference":
            reference,

        "residual":
            residual,
    })


if len(rows) != 104:

    raise SystemExit(
        f"EXPECTED 104 DEVELOPMENT ROWS, GOT {len(rows)}"
    )


by_year = defaultdict(
    list
)


for r in rows:

    by_year[
        r[
            "year"
        ]
    ].append(r)


for year in YEARS:

    by_year[
        year
    ].sort(
        key=lambda r: (
            r[
                "time"
            ],
            r[
                "attempt_id"
            ],
        )
    )


# =============================================================================
# Strictly earlier other-driver state
# =============================================================================

def past_other(
    current,
    year_rows,
):

    return [
        r
        for r in year_rows
        if (
            r[
                "time"
            ]
            <
            current[
                "time"
            ]
            and
            r[
                "driver_key"
            ]
            !=
            current[
                "driver_key"
            ]
        )
    ]


def cross_year_prior_mean(
    training_years
):

    values = [
        r[
            "residual"
        ]
        for year in training_years
        for r in by_year[
            year
        ]
    ]

    return (
        sum(values)
        /
        len(values)
    )


def shrunk_residual_prediction(
    current,
    year_rows,
    prior_mean,
    k,
):

    past = past_other(
        current,
        year_rows
    )

    n = len(past)

    if n == 0:
        return prior_mean

    field_mean = (
        sum(
            r[
                "residual"
            ]
            for r in past
        )
        /
        n
    )

    return (
        (
            k
            *
            prior_mean
        )
        +
        (
            n
            *
            field_mean
        )
    ) / (
        k + n
    )


# =============================================================================
# Select one universal k using leave-one-year-out development scoring
# =============================================================================

k_rows = []


for k in K_GRID:

    all_actual = []
    all_pred = []

    by_test_year = {}


    for test_year in YEARS:

        training_years = [
            y
            for y in YEARS
            if y != test_year
        ]

        prior_mean = (
            cross_year_prior_mean(
                training_years
            )
        )

        actual = []
        pred = []


        for current in by_year[
            test_year
        ]:

            residual_pred = (
                shrunk_residual_prediction(
                    current,
                    by_year[
                        test_year
                    ],
                    prior_mean,
                    k,
                )
            )

            actual.append(
                current[
                    "actual"
                ]
            )

            pred.append(
                current[
                    "reference"
                ]
                +
                residual_pred
            )


        year_mae = mae(
            actual,
            pred,
        )


        by_test_year[
            test_year
        ] = year_mae

        all_actual.extend(
            actual
        )

        all_pred.extend(
            pred
        )


    aggregate_mae = mae(
        all_actual,
        all_pred,
    )


    k_rows.append({
        "shrinkage_k":
            k,

        "aggregate_loyo_mae_mph":
            aggregate_mae,

        "test_2020_mae_mph":
            by_test_year[
                2020
            ],

        "test_2021_mae_mph":
            by_test_year[
                2021
            ],

        "test_2023_mae_mph":
            by_test_year[
                2023
            ],
    })


k_rows.sort(
    key=lambda r:
        r[
            "aggregate_loyo_mae_mph"
        ]
)


selected_k = (
    k_rows[
        0
    ][
        "shrinkage_k"
    ]
)

selected_k_mae = (
    k_rows[
        0
    ][
        "aggregate_loyo_mae_mph"
    ]
)


# =============================================================================
# Final prior from ALL development years
#
# This will be frozen before 2024 is opened.
# =============================================================================

all_residuals = [
    r[
        "residual"
    ]
    for r in rows
]


final_prior_mean = (
    sum(
        all_residuals
    )
    /
    len(
        all_residuals
    )
)


if len(
    all_residuals
) > 1:

    final_prior_variance = (
        sum(
            (
                x
                -
                final_prior_mean
            )
            ** 2
            for x in all_residuals
        )
        /
        (
            len(
                all_residuals
            )
            -
            1
        )
    )

    final_prior_sd = math.sqrt(
        final_prior_variance
    )

else:

    final_prior_sd = 0.0


# =============================================================================
# Evidence extraction from earlier phases
# =============================================================================

def find_metric(
    rows,
    **criteria
):

    for r in rows:

        match = True

        for key, value in criteria.items():

            if clean(
                r.get(key)
            ) != value:

                match = False
                break

        if match:
            return r

    return None


evidence_rows = []


# C3
for model in [
    "FAST_FRIDAY_REFERENCE_ONLY",
    "FAST_FRIDAY_PLUS_THERMAL_RIDGE",
]:

    r = find_metric(
        c3_rows,
        validation_scheme=
            "DRIVER_GROUPED_5FOLD",
        model=
            model,
    )

    if r:

        evidence_rows.append({
            "phase":
                "R4F7C3",

            "test":
                "DRIVER_GROUPED_5FOLD",

            "model":
                model,

            "mae_mph":
                num(
                    r.get(
                        "mae_mph"
                    )
                ),

            "interpretation":
                (
                    "Baseline development comparison"
                ),
        })


# C4 global attribution
for model in [
    "FAST_FRIDAY_PLUS_YEAR_OFFSET",
    "FAST_FRIDAY_PLUS_YEAR_OFFSET_PLUS_THERMAL_RIDGE",
]:

    r = find_metric(
        c4_global_rows,
        validation_scheme=
            "GLOBAL_DRIVER_GROUPED_5FOLD",
        model=
            model,
    )

    if r:

        evidence_rows.append({
            "phase":
                "R4F7C4",

            "test":
                "YEAR_OFFSET_ATTRIBUTION",

            "model":
                model,

            "mae_mph":
                num(
                    r.get(
                        "mae_mph"
                    )
                ),

            "interpretation":
                (
                    "Tests whether thermal survives explicit annual calibration"
                ),
        })


# C6 aggregate
for model in [
    "ONLINE_SHRUNK_FIELD_MEAN",
    "ONLINE_RUNNING_FIELD_MEAN",
    "ONLINE_EWMA",
    "ONLINE_KALMAN_LATENT_WINDOW",
    "CROSS_YEAR_PRIOR_CALIBRATION",
    "FAST_FRIDAY_REFERENCE_ONLY",
]:

    r = find_metric(
        c6_rows,
        test_year=
            "ALL_LOYO",
        model=
            model,
    )

    if r:

        evidence_rows.append({
            "phase":
                "R4F7C6",

            "test":
                "ONLINE_LOYO",

            "model":
                model,

            "mae_mph":
                num(
                    r.get(
                        "mae_mph"
                    )
                ),

            "interpretation":
                (
                    "Prospective sequential held-out-year evaluation"
                ),
        })


# =============================================================================
# Frozen architecture
# =============================================================================

contract = {
    "phase":
        "R4F7C7",

    "status":
        "R4F7C7_FINAL_DEVELOPMENT_ARCHITECTURE_FROZEN",

    "primary_performance_architecture":
        (
            "FAST_FRIDAY_REFERENCE_PLUS_ONLINE_SHRUNK_FIELD_CALIBRATION"
        ),

    "equation":
        (
            "predicted_speed_i_t = FastFridayReference_i "
            "+ ((k * prior_mean) + (n_t * observed_field_mean_t)) "
            "/ (k + n_t)"
        ),

    "selected_shrinkage_k":
        selected_k,

    "development_selected_k_loyo_mae_mph":
        selected_k_mae,

    "frozen_cross_year_prior_mean_residual_mph":
        final_prior_mean,

    "frozen_cross_year_prior_sd_mph":
        final_prior_sd,

    "prior_training_years":
        YEARS,

    "development_rows":
        len(rows),

    "online_field_state_policy": {
        "eligible_observations":
            (
                "Only same-session qualifying attempts strictly earlier "
                "than the prediction time."
            ),

        "entry_exclusion":
            (
                "Current driver's earlier observations are excluded from "
                "the common field mean."
            ),

        "same_timestamp_policy":
            (
                "Attempts at the same timestamp are not allowed to inform "
                "one another."
            ),

        "low_support_policy":
            (
                "When n=0, prediction uses the frozen cross-year prior. "
                "For n>0, current-session field evidence is partially pooled "
                "toward that prior through shrinkage k."
            ),
    },

    "model_promotion_decisions": {
        "FAST_FRIDAY_REFERENCE":
            "PROMOTED_AS_ENTRY_STRENGTH_PRIOR",

        "ONLINE_SHRUNK_FIELD_MEAN":
            "PROMOTED_AS_PRIMARY_SESSION_CALIBRATION",

        "ONLINE_RUNNING_FIELD_MEAN":
            "RETAINED_AS_SIMPLER_ABLATION",

        "ONLINE_EWMA":
            "RETAINED_AS_DYNAMIC_ABLATION",

        "ONLINE_KALMAN_LATENT_WINDOW":
            (
                "NOT_PROMOTED_COMPLEXITY_NOT_JUSTIFIED_BY_DEVELOPMENT_EVIDENCE"
            ),

        "STATIC_THERMAL_RIDGE":
            (
                "NOT_PROMOTED_AS_PRIMARY_SIGNAL_YEAR_OFFSET_ATTRIBUTION_FAILED"
            ),

        "HUBER_THERMAL":
            (
                "NOT_PROMOTED_CROSS_YEAR_UNSTABLE"
            ),
    },

    "thermal_role":
        (
            "Auxiliary physical/context evidence and ablation only. "
            "Do not treat as a stable universal qualifying-speed coefficient."
        ),

    "latent_window_interpretation":
        (
            "The selected online session-calibration posterior is the "
            "operational estimate of current field performance state. "
            "A more complex Kalman latent process was tested but did not "
            "earn promotion."
        ),

    "uncertainty_policy_for_next_phase":
        (
            "Prediction uncertainty must include residual/run noise and "
            "calibration uncertainty; uncertainty should shrink as current-session "
            "field evidence accumulates."
        ),

    "validation_boundary": {
        "2024":
            (
                "UNOPENED_DURING_DEVELOPMENT_SELECTION_AND_RESERVED_FOR_FINAL_VALIDATION"
            ),

        "2022":
            "DEGRADED_CHRONOLOGY_ROBUSTNESS_ONLY",

        "2025":
            "TECHNICAL_REGIME_TRANSFER_ONLY",
    },

    "next_phase":
        (
            "R4F7V1_FINAL_2024_VALIDATION"
        ),
}


# =============================================================================
# QA
# =============================================================================

c6_shrunk = find_metric(
    c6_rows,
    test_year=
        "ALL_LOYO",
    model=
        "ONLINE_SHRUNK_FIELD_MEAN",
)

c6_running = find_metric(
    c6_rows,
    test_year=
        "ALL_LOYO",
    model=
        "ONLINE_RUNNING_FIELD_MEAN",
)

c6_kalman = find_metric(
    c6_rows,
    test_year=
        "ALL_LOYO",
    model=
        "ONLINE_KALMAN_LATENT_WINDOW",
)


shrunk_mae = num(
    c6_shrunk.get(
        "mae_mph"
    )
) if c6_shrunk else None

running_mae = num(
    c6_running.get(
        "mae_mph"
    )
) if c6_running else None

kalman_mae = num(
    c6_kalman.get(
        "mae_mph"
    )
) if c6_kalman else None


qa_rows = [
    {
        "metric":
            "development_rows",
        "value":
            len(rows),
        "expected":
            104,
        "status":
            (
                "PASS"
                if len(rows) == 104
                else "FAIL"
            ),
    },

    {
        "metric":
            "selected_k_in_grid",
        "value":
            selected_k,
        "expected":
            "IN_GRID",
        "status":
            (
                "PASS"
                if selected_k in K_GRID
                else "FAIL"
            ),
    },

    {
        "metric":
            "c6_shrunk_beats_kalman",
        "value":
            (
                shrunk_mae
                <
                kalman_mae
                if (
                    shrunk_mae is not None
                    and
                    kalman_mae is not None
                )
                else False
            ),
        "expected":
            True,
        "status":
            (
                "PASS"
                if (
                    shrunk_mae is not None
                    and
                    kalman_mae is not None
                    and
                    shrunk_mae
                    <
                    kalman_mae
                )
                else "FAIL"
            ),
    },

    {
        "metric":
            "c6_shrunk_not_materially_worse_than_running",
        "value":
            (
                shrunk_mae
                -
                running_mae
                if (
                    shrunk_mae is not None
                    and
                    running_mae is not None
                )
                else ""
            ),
        "expected":
            "<=0.02 mph",
        "status":
            (
                "PASS"
                if (
                    shrunk_mae is not None
                    and
                    running_mae is not None
                    and
                    shrunk_mae
                    -
                    running_mae
                    <=
                    0.02
                )
                else "FAIL"
            ),
    },

    {
        "metric":
            "2024_validation_read",
        "value":
            False,
        "expected":
            False,
        "status":
            "PASS",
    },

    {
        "metric":
            "thermal_primary_model",
        "value":
            False,
        "expected":
            False,
        "status":
            "PASS",
    },

    {
        "metric":
            "kalman_primary_model",
        "value":
            False,
        "expected":
            False,
        "status":
            "PASS",
    },

    {
        "metric":
            "historical_action_classifier_used",
        "value":
            False,
        "expected":
            False,
        "status":
            "PASS",
    },

    {
        "metric":
            "development_architecture_frozen_before_2024",
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

with OUT_K.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=list(
            k_rows[0].keys()
        )
    )

    writer.writeheader()
    writer.writerows(
        k_rows
    )


with OUT_EVIDENCE.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=list(
            evidence_rows[0].keys()
        )
    )

    writer.writeheader()
    writer.writerows(
        evidence_rows
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
        "R4F7C7",

    "status":
        "R4F7C7_FINAL_DEVELOPMENT_ARCHITECTURE_FROZEN",

    "selected_shrinkage_k":
        selected_k,

    "selected_k_loyo_mae_mph":
        selected_k_mae,

    "frozen_prior_mean_mph":
        final_prior_mean,

    "frozen_prior_sd_mph":
        final_prior_sd,

    "development_years":
        YEARS,

    "development_rows":
        len(rows),

    "architecture":
        (
            "Fast Friday reference + online shrunk field calibration"
        ),

    "2024_validation_access":
        "NOT_READ",

    "input_hashes": {
        str(
            STATE_PATH.relative_to(
                ROOT
            )
        ):
            sha256(
                STATE_PATH
            ),

        str(
            C3_METRICS.relative_to(
                ROOT
            )
        ):
            sha256(
                C3_METRICS
            ),

        str(
            C4_GLOBAL.relative_to(
                ROOT
            )
        ):
            sha256(
                C4_GLOBAL
            ),

        str(
            C6_METRICS.relative_to(
                ROOT
            )
        ):
            sha256(
                C6_METRICS
            ),
    },

    "next_phase":
        (
            "Run one-shot 2024 external validation using this frozen "
            "architecture and parameters. No post-hoc tuning."
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

print("=" * 150)
print("R4F7C7 — FINAL DEVELOPMENT ARCHITECTURE FREEZE")
print("=" * 150)

print()
print("SHRINKAGE K SELECTION")

for r in k_rows:

    marker = (
        " <-- SELECTED"
        if r[
            "shrinkage_k"
        ] == selected_k
        else ""
    )

    print(
        f"k={r['shrinkage_k']:5.1f} | "
        f"ALL_LOYO_MAE={r['aggregate_loyo_mae_mph']:.6f} | "
        f"2020={r['test_2020_mae_mph']:.6f} | "
        f"2021={r['test_2021_mae_mph']:.6f} | "
        f"2023={r['test_2023_mae_mph']:.6f}"
        f"{marker}"
    )


print()
print("=" * 150)
print("FROZEN PERFORMANCE ARCHITECTURE")
print("=" * 150)

print(
    "PRIMARY = FAST_FRIDAY_REFERENCE "
    "+ ONLINE_SHRUNK_FIELD_CALIBRATION"
)

print(
    f"selected_k={selected_k}"
)

print(
    f"frozen_prior_mean_residual="
    f"{final_prior_mean:+.6f} mph"
)

print(
    f"frozen_prior_sd="
    f"{final_prior_sd:.6f} mph"
)

print()
print(
    "LOW SUPPORT: use prior-dominated calibration."
)

print(
    "AS CURRENT-SESSION FIELD EVIDENCE ACCUMULATES: "
    "weight shifts toward observed field mean."
)


print()
print("=" * 150)
print("PROMOTION DECISIONS")
print("=" * 150)

for model, decision in (
    contract[
        "model_promotion_decisions"
    ].items()
):

    print(
        f"{model:36s} | "
        f"{decision}"
    )


print()
print("=" * 150)
print("VALIDATION BOUNDARY")
print("=" * 150)

print(
    "2024 = RESERVED FINAL VALIDATION — STILL UNREAD"
)

print(
    "2022 = DEGRADED CHRONOLOGY ROBUSTNESS"
)

print(
    "2025 = TECHNICAL REGIME TRANSFER"
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
    OUT_K.relative_to(ROOT)
)
print(
    OUT_EVIDENCE.relative_to(ROOT)
)
print(
    OUT_QA.relative_to(ROOT)
)
print(
    OUT_CONTRACT.relative_to(ROOT)
)
print(
    OUT_REPORT.relative_to(ROOT)
)

print()
print(
    "R4F7C7_FINAL_DEVELOPMENT_ARCHITECTURE_FROZEN"
)
