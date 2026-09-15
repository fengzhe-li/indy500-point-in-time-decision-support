from pathlib import Path
import json
import math

import numpy as np
import pandas as pd

ROOT = Path(
    "/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈"
)

DATA = (
    ROOT /
    "r6_regime_extension/output/"
    "r6_repeat_ptsc_linkage_v1/"
    "r6_repeat_transitions_primary_physics_v1.csv"
)

OUT = (
    ROOT /
    "r6_regime_extension/output/"
    "r6_regime_physics_comparison_v1"
)

OUT.mkdir(
    parents=True,
    exist_ok=True
)

# ============================================================
# Frozen Regime B coefficients
# DO NOT REFIT / MODIFY
# ============================================================

BETA_B_TRACK = -0.03482533
BETA_B_AMBIENT = +0.18239338

BOOTSTRAP_DRAWS = 5000
RNG_SEED = 20260913

HUBER_K = 1.345
IRLS_MAX_ITER = 200
IRLS_TOL = 1e-10


# ============================================================
# Helpers
# ============================================================

def design_matrix(df):

    return df[
        [
            "delta_track_c",
            "delta_ambient_c",
        ]
    ].to_numpy(
        dtype=float
    )


def response_vector(df):

    return df[
        "delta_speed_mph"
    ].to_numpy(
        dtype=float
    )


def ols_no_intercept(
    X,
    y
):

    beta, *_ = np.linalg.lstsq(
        X,
        y,
        rcond=None
    )

    return beta


def robust_scale_mad(
    residuals
):

    residuals = np.asarray(
        residuals,
        dtype=float
    )

    med = np.median(
        residuals
    )

    mad = np.median(
        np.abs(
            residuals - med
        )
    )

    scale = (
        1.4826 * mad
    )

    if (
        not np.isfinite(
            scale
        )
        or
        scale < 1e-9
    ):

        rms = np.sqrt(
            np.mean(
                residuals ** 2
            )
        )

        if (
            not np.isfinite(
                rms
            )
            or
            rms < 1e-9
        ):

            return 1.0

        return float(
            rms
        )

    return float(
        scale
    )


def huber_weights(
    residuals,
    scale,
    k=HUBER_K
):

    u = (
        residuals
        /
        max(
            scale,
            1e-12
        )
    )

    abs_u = np.abs(
        u
    )

    w = np.ones_like(
        abs_u
    )

    mask = (
        abs_u > k
    )

    w[
        mask
    ] = (
        k
        /
        abs_u[
            mask
        ]
    )

    return w


def huber_no_intercept(
    X,
    y
):

    beta = ols_no_intercept(
        X,
        y
    )

    for _ in range(
        IRLS_MAX_ITER
    ):

        residuals = (
            y
            -
            X @ beta
        )

        scale = robust_scale_mad(
            residuals
        )

        w = huber_weights(
            residuals,
            scale
        )

        sqrt_w = np.sqrt(
            w
        )

        Xw = (
            X
            *
            sqrt_w[:, None]
        )

        yw = (
            y
            *
            sqrt_w
        )

        beta_new, *_ = np.linalg.lstsq(
            Xw,
            yw,
            rcond=None
        )

        if np.max(
            np.abs(
                beta_new
                -
                beta
            )
        ) < IRLS_TOL:

            beta = beta_new
            break

        beta = beta_new

    return beta


def metrics(
    X,
    y,
    beta
):

    pred = (
        X @ beta
    )

    residual = (
        y - pred
    )

    return {
        "mae_mph":
            float(
                np.mean(
                    np.abs(
                        residual
                    )
                )
            ),

        "rmse_mph":
            float(
                np.sqrt(
                    np.mean(
                        residual ** 2
                    )
                )
            ),

        "median_abs_error_mph":
            float(
                np.median(
                    np.abs(
                        residual
                    )
                )
            ),

        "residual_median_mph":
            float(
                np.median(
                    residual
                )
            ),
    }


def predictor_diagnostics(
    X
):

    track = X[:, 0]
    ambient = X[:, 1]

    if (
        np.std(
            track
        ) > 0
        and
        np.std(
            ambient
        ) > 0
    ):

        corr = float(
            np.corrcoef(
                track,
                ambient
            )[0, 1]
        )

    else:

        corr = np.nan

    singular_values = np.linalg.svd(
        X,
        compute_uv=False
    )

    if (
        len(
            singular_values
        ) >= 2
        and
        singular_values[-1] > 0
    ):

        condition_number = float(
            singular_values[0]
            /
            singular_values[-1]
        )

    else:

        condition_number = np.inf

    return {
        "delta_track_ambient_correlation":
            corr,

        "design_condition_number":
            condition_number,
    }


def percentile_interval(
    values,
    central
):

    values = np.asarray(
        values,
        dtype=float
    )

    values = values[
        np.isfinite(
            values
        )
    ]

    alpha = (
        100.0 - central
    ) / 2.0

    return (
        float(
            np.percentile(
                values,
                alpha
            )
        ),
        float(
            np.percentile(
                values,
                100.0 - alpha
            )
        ),
    )


# ============================================================
# Load
# ============================================================

df = pd.read_csv(
    DATA,
    low_memory=False
)

required = [
    "year",
    "regime_code",
    "car_number",
    "driver_name",
    "delta_track_c",
    "delta_ambient_c",
    "delta_speed_mph",
]

missing = [
    c
    for c in required
    if c not in df.columns
]

if missing:

    raise RuntimeError(
        "Missing required columns: "
        +
        ", ".join(
            missing
        )
    )

for c in [
    "delta_track_c",
    "delta_ambient_c",
    "delta_speed_mph",
]:

    df[c] = pd.to_numeric(
        df[c],
        errors="coerce"
    )

df = df[
    df[
        [
            "delta_track_c",
            "delta_ambient_c",
            "delta_speed_mph",
        ]
    ]
    .notna()
    .all(
        axis=1
    )
].copy()

df[
    "car_cluster"
] = (
    df[
        "year"
    ].astype(str)
    +
    "_"
    +
    df[
        "car_number"
    ].astype(str)
)


# ============================================================
# Fit A and C
# ============================================================

coefficient_rows = []
diagnostic_rows = []
residual_rows = []

point_estimates = {}

for regime in [
    "A",
    "C",
]:

    g = df[
        df[
            "regime_code"
        ]
        == regime
    ].copy()

    if g.empty:

        raise RuntimeError(
            f"No rows for regime {regime}"
        )

    X = design_matrix(
        g
    )

    y = response_vector(
        g
    )

    beta_ols = ols_no_intercept(
        X,
        y
    )

    beta_huber = huber_no_intercept(
        X,
        y
    )

    point_estimates[
        regime
    ] = beta_huber.copy()

    ols_metrics = metrics(
        X,
        y,
        beta_ols
    )

    huber_metrics = metrics(
        X,
        y,
        beta_huber
    )

    predictor_diag = predictor_diagnostics(
        X
    )

    for model_name, beta, met in [
        (
            "OLS_NO_INTERCEPT",
            beta_ols,
            ols_metrics,
        ),
        (
            "HUBER_IRLS_NO_INTERCEPT",
            beta_huber,
            huber_metrics,
        ),
    ]:

        coefficient_rows.append({
            "regime_code":
                regime,

            "year":
                int(
                    g[
                        "year"
                    ].iloc[0]
                ),

            "model":
                model_name,

            "n_transitions":
                len(
                    g
                ),

            "n_car_clusters":
                g[
                    "car_cluster"
                ].nunique(),

            "beta_track_mph_per_c":
                float(
                    beta[0]
                ),

            "beta_ambient_mph_per_c":
                float(
                    beta[1]
                ),

            **met,
        })

    diagnostic_rows.append({
        "regime_code":
            regime,

        "year":
            int(
                g[
                    "year"
                ].iloc[0]
            ),

        "n_transitions":
            len(
                g
            ),

        "n_car_clusters":
            g[
                "car_cluster"
            ].nunique(),

        **predictor_diag,

        "delta_track_sd_c":
            float(
                g[
                    "delta_track_c"
                ].std(
                    ddof=1
                )
            ),

        "delta_ambient_sd_c":
            float(
                g[
                    "delta_ambient_c"
                ].std(
                    ddof=1
                )
            ),

        "delta_speed_sd_mph":
            float(
                g[
                    "delta_speed_mph"
                ].std(
                    ddof=1
                )
            ),
    })

    prediction = (
        X @ beta_huber
    )

    residual = (
        y - prediction
    )

    temp = g[
        [
            "year",
            "regime_code",
            "car_number",
            "driver_name",
            "from_source_rank",
            "to_source_rank",
            "delta_track_c",
            "delta_ambient_c",
            "delta_speed_mph",
        ]
    ].copy()

    temp[
        "predicted_delta_speed_mph"
    ] = prediction

    temp[
        "residual_mph"
    ] = residual

    residual_rows.append(
        temp
    )


coefficients = pd.DataFrame(
    coefficient_rows
)

diagnostics = pd.DataFrame(
    diagnostic_rows
)

residuals = pd.concat(
    residual_rows,
    ignore_index=True
)


# ============================================================
# Add frozen B reference
# ============================================================

b_reference = pd.DataFrame([
    {
        "regime_code":
            "B",

        "year":
            "2020-2024",

        "model":
            "FROZEN_R5_2_ROBUST_CORE",

        "n_transitions":
            41,

        "n_car_clusters":
            np.nan,

        "beta_track_mph_per_c":
            BETA_B_TRACK,

        "beta_ambient_mph_per_c":
            BETA_B_AMBIENT,

        "mae_mph":
            np.nan,

        "rmse_mph":
            np.nan,

        "median_abs_error_mph":
            0.3106,

        "residual_median_mph":
            np.nan,
    }
])

coefficients_with_b = pd.concat(
    [
        coefficients,
        b_reference,
    ],
    ignore_index=True
)


# ============================================================
# Cluster bootstrap
# ============================================================

rng = np.random.default_rng(
    RNG_SEED
)

bootstrap_rows = []

for regime in [
    "A",
    "C",
]:

    g = df[
        df[
            "regime_code"
        ]
        == regime
    ].copy()

    clusters = sorted(
        g[
            "car_cluster"
        ].unique()
    )

    if len(
        clusters
    ) < 2:

        raise RuntimeError(
            f"Too few clusters for {regime}"
        )

    cluster_frames = {
        cluster:
            g[
                g[
                    "car_cluster"
                ]
                ==
                cluster
            ].copy()

        for cluster in clusters
    }

    successful = 0
    attempts = 0

    while (
        successful
        <
        BOOTSTRAP_DRAWS
        and
        attempts
        <
        BOOTSTRAP_DRAWS
        * 20
    ):

        attempts += 1

        sampled_clusters = rng.choice(
            clusters,
            size=len(
                clusters
            ),
            replace=True
        )

        pieces = []

        for boot_cluster_index, cluster in enumerate(
            sampled_clusters
        ):

            part = cluster_frames[
                cluster
            ].copy()

            # duplicated sampled clusters must remain duplicated
            # as observations in the bootstrap dataset
            part[
                "_bootstrap_cluster_copy"
            ] = boot_cluster_index

            pieces.append(
                part
            )

        boot = pd.concat(
            pieces,
            ignore_index=True
        )

        Xb = design_matrix(
            boot
        )

        yb = response_vector(
            boot
        )

        if (
            np.linalg.matrix_rank(
                Xb
            )
            < 2
        ):

            continue

        try:

            beta = huber_no_intercept(
                Xb,
                yb
            )

        except Exception:

            continue

        if not np.all(
            np.isfinite(
                beta
            )
        ):

            continue

        bootstrap_rows.append({
            "regime_code":
                regime,

            "draw":
                successful + 1,

            "beta_track_mph_per_c":
                float(
                    beta[0]
                ),

            "beta_ambient_mph_per_c":
                float(
                    beta[1]
                ),
        })

        successful += 1

    if successful < BOOTSTRAP_DRAWS:

        raise RuntimeError(
            f"{regime}: only {successful} successful bootstrap draws"
        )


bootstrap = pd.DataFrame(
    bootstrap_rows
)


# ============================================================
# Bootstrap interval summary
# ============================================================

interval_rows = []

for regime in [
    "A",
    "C",
]:

    b = bootstrap[
        bootstrap[
            "regime_code"
        ]
        == regime
    ]

    point = point_estimates[
        regime
    ]

    for coef_index, coef_name in [
        (
            0,
            "beta_track_mph_per_c",
        ),
        (
            1,
            "beta_ambient_mph_per_c",
        ),
    ]:

        values = b[
            coef_name
        ].to_numpy(
            dtype=float
        )

        lo80, hi80 = percentile_interval(
            values,
            80
        )

        lo90, hi90 = percentile_interval(
            values,
            90
        )

        interval_rows.append({
            "regime_code":
                regime,

            "coefficient":
                coef_name,

            "point_estimate":
                float(
                    point[
                        coef_index
                    ]
                ),

            "bootstrap_draws":
                len(
                    values
                ),

            "p10":
                lo80,

            "p90":
                hi80,

            "p05":
                lo90,

            "p95":
                hi90,

            "bootstrap_median":
                float(
                    np.median(
                        values
                    )
                ),
        })


intervals = pd.DataFrame(
    interval_rows
)


# ============================================================
# Compare A/C against frozen B
# ============================================================

comparison_rows = []

for regime in [
    "A",
    "C",
]:

    b = bootstrap[
        bootstrap[
            "regime_code"
        ]
        == regime
    ].copy()

    for coef_name, frozen_value in [
        (
            "beta_track_mph_per_c",
            BETA_B_TRACK,
        ),
        (
            "beta_ambient_mph_per_c",
            BETA_B_AMBIENT,
        ),
    ]:

        differences = (
            b[
                coef_name
            ].to_numpy(
                dtype=float
            )
            -
            frozen_value
        )

        lo80, hi80 = percentile_interval(
            differences,
            80
        )

        lo90, hi90 = percentile_interval(
            differences,
            90
        )

        comparison_rows.append({
            "comparison":
                f"{regime}_MINUS_B",

            "coefficient":
                coef_name,

            "regime_point_estimate":
                float(
                    point_estimates[
                        regime
                    ][
                        0
                        if coef_name
                        ==
                        "beta_track_mph_per_c"
                        else 1
                    ]
                ),

            "frozen_B_value":
                frozen_value,

            "point_difference":
                float(
                    point_estimates[
                        regime
                    ][
                        0
                        if coef_name
                        ==
                        "beta_track_mph_per_c"
                        else 1
                    ]
                    -
                    frozen_value
                ),

            "difference_80_lo":
                lo80,

            "difference_80_hi":
                hi80,

            "difference_90_lo":
                lo90,

            "difference_90_hi":
                hi90,

            "fraction_draws_above_B":
                float(
                    np.mean(
                        b[
                            coef_name
                        ].to_numpy(
                            dtype=float
                        )
                        >
                        frozen_value
                    )
                ),
        })


# A minus C direct comparison using paired bootstrap draw numbers.
a_boot = (
    bootstrap[
        bootstrap[
            "regime_code"
        ]
        == "A"
    ]
    .sort_values(
        "draw"
    )
)

c_boot = (
    bootstrap[
        bootstrap[
            "regime_code"
        ]
        == "C"
    ]
    .sort_values(
        "draw"
    )
)

for coef_name in [
    "beta_track_mph_per_c",
    "beta_ambient_mph_per_c",
]:

    diffs = (
        a_boot[
            coef_name
        ].to_numpy(
            dtype=float
        )
        -
        c_boot[
            coef_name
        ].to_numpy(
            dtype=float
        )
    )

    lo80, hi80 = percentile_interval(
        diffs,
        80
    )

    lo90, hi90 = percentile_interval(
        diffs,
        90
    )

    comparison_rows.append({
        "comparison":
            "A_MINUS_C",

        "coefficient":
            coef_name,

        "regime_point_estimate":
            np.nan,

        "frozen_B_value":
            np.nan,

        "point_difference":
            float(
                point_estimates[
                    "A"
                ][
                    0
                    if coef_name
                    ==
                    "beta_track_mph_per_c"
                    else 1
                ]
                -
                point_estimates[
                    "C"
                ][
                    0
                    if coef_name
                    ==
                    "beta_track_mph_per_c"
                    else 1
                ]
            ),

        "difference_80_lo":
            lo80,

        "difference_80_hi":
            hi80,

        "difference_90_lo":
            lo90,

        "difference_90_hi":
            hi90,

        "fraction_draws_above_B":
            np.nan,
    })


comparisons = pd.DataFrame(
    comparison_rows
)


# ============================================================
# Invariance QA
# ============================================================

invariance_rows = []

for regime in [
    "A",
    "B",
    "C",
]:

    if regime == "A":

        beta = point_estimates[
            "A"
        ]

    elif regime == "B":

        beta = np.array([
            BETA_B_TRACK,
            BETA_B_AMBIENT,
        ])

    else:

        beta = point_estimates[
            "C"
        ]

    zero_prediction = float(
        np.array([
            0.0,
            0.0,
        ])
        @
        beta
    )

    invariance_rows.append({
        "regime_code":
            regime,

        "delta_track_c":
            0.0,

        "delta_ambient_c":
            0.0,

        "predicted_delta_speed_mph":
            zero_prediction,

        "invariance_pass":
            abs(
                zero_prediction
            )
            <
            1e-12,
    })


invariance = pd.DataFrame(
    invariance_rows
)


# ============================================================
# Machine-readable report
# ============================================================

report = {
    "status":
        "R6_REGIME_PHYSICS_COMPARISON_V1_COMPLETE",

    "primary_model":
        "HUBER_IRLS_NO_INTERCEPT",

    "sensitivity_model":
        "OLS_NO_INTERCEPT",

    "predictors": [
        "delta_track_c",
        "delta_ambient_c",
    ],

    "target":
        "delta_speed_mph",

    "bootstrap": {
        "type":
            "CAR_CLUSTER_BOOTSTRAP",

        "draws":
            BOOTSTRAP_DRAWS,

        "seed":
            RNG_SEED,
    },

    "frozen_regime_B": {
        "beta_track_mph_per_c":
            BETA_B_TRACK,

        "beta_ambient_mph_per_c":
            BETA_B_AMBIENT,

        "modified":
            False,
    },

    "limitations": [
        "Regime A direct repeat evidence is 2019 only.",
        "Regime A has a small sample and strong delta-track/delta-ambient collinearity.",
        "Regime C direct repeat evidence is 2025 only.",
        "2026 contributes no same-day initial-round repeat transitions because of the qualifying format.",
        "Bootstrap intervals describe empirical sampling uncertainty and are not proof of regulation-caused coefficient differences.",
    ],
}

REPORT_OUT = (
    OUT /
    "r6_regime_physics_comparison_report_v1.json"
)

REPORT_OUT.write_text(
    json.dumps(
        report,
        indent=2
    ),
    encoding="utf-8"
)


# ============================================================
# Save
# ============================================================

COEF_OUT = (
    OUT /
    "r6_regime_physics_coefficients_v1.csv"
)

BOOT_OUT = (
    OUT /
    "r6_regime_physics_cluster_bootstrap_v1.csv"
)

INTERVAL_OUT = (
    OUT /
    "r6_regime_physics_bootstrap_intervals_v1.csv"
)

COMPARE_OUT = (
    OUT /
    "r6_regime_physics_comparison_to_frozen_B_v1.csv"
)

DIAG_OUT = (
    OUT /
    "r6_regime_physics_diagnostics_v1.csv"
)

RESID_OUT = (
    OUT /
    "r6_regime_physics_residuals_v1.csv"
)

INVARIANCE_OUT = (
    OUT /
    "r6_regime_physics_zero_state_invariance_v1.csv"
)

coefficients_with_b.to_csv(
    COEF_OUT,
    index=False
)

bootstrap.to_csv(
    BOOT_OUT,
    index=False
)

intervals.to_csv(
    INTERVAL_OUT,
    index=False
)

comparisons.to_csv(
    COMPARE_OUT,
    index=False
)

diagnostics.to_csv(
    DIAG_OUT,
    index=False
)

residuals.to_csv(
    RESID_OUT,
    index=False
)

invariance.to_csv(
    INVARIANCE_OUT,
    index=False
)


# ============================================================
# Console
# ============================================================

print(
    "=" * 170
)
print(
    "PART 1 — REGIME COEFFICIENTS"
)
print(
    "=" * 170
)

print(
    coefficients_with_b[
        [
            "regime_code",
            "year",
            "model",
            "n_transitions",
            "n_car_clusters",
            "beta_track_mph_per_c",
            "beta_ambient_mph_per_c",
            "mae_mph",
            "rmse_mph",
            "median_abs_error_mph",
        ]
    ]
    .to_string(
        index=False
    )
)


print(
    "\n" + "=" * 170
)
print(
    "PART 2 — IDENTIFIABILITY DIAGNOSTICS"
)
print(
    "=" * 170
)

print(
    diagnostics.to_string(
        index=False
    )
)


print(
    "\n" + "=" * 170
)
print(
    "PART 3 — CLUSTER BOOTSTRAP INTERVALS"
)
print(
    "=" * 170
)

print(
    intervals.to_string(
        index=False
    )
)


print(
    "\n" + "=" * 170
)
print(
    "PART 4 — COMPARISON TO FROZEN B"
)
print(
    "=" * 170
)

print(
    comparisons.to_string(
        index=False
    )
)


print(
    "\n" + "=" * 170
)
print(
    "PART 5 — ZERO-STATE INVARIANCE"
)
print(
    "=" * 170
)

print(
    invariance.to_string(
        index=False
    )
)


print(
    "\nOUTPUTS:"
)

for p in [
    COEF_OUT,
    BOOT_OUT,
    INTERVAL_OUT,
    COMPARE_OUT,
    DIAG_OUT,
    RESID_OUT,
    INVARIANCE_OUT,
    REPORT_OUT,
]:

    print(
        p.relative_to(
            ROOT
        )
    )

print(
    "\nR6_REGIME_PHYSICS_COMPARISON_V1_COMPLETE"
)
