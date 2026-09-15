from pathlib import Path
import argparse
import json
import math
import re
from datetime import timezone

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


# ============================================================
# Project paths
# ============================================================

ROOT = Path(
    "/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈"
)

R5 = ROOT / "r5_2/manual"

BETA_BOOTSTRAP = (
    R5 /
    "probabilistic_physics_coefficient_bootstrap_v1.csv"
)

PERFORMANCE_RESIDUALS = (
    R5 /
    "probabilistic_physics_loyo_residuals_v1.csv"
)

CORE_JSON = (
    R5 /
    "probabilistic_physics_core_v1.json"
)

CORE_MANIFEST = (
    R5 /
    "CORE_REGIME_2020_2024_V1_FROZEN_MANIFEST.json"
)


# ============================================================
# Frozen future-track model V3
# ============================================================

TRACK_WAIT_COEF = 0.76443035
TRACK_CURRENT_TEMP_INTERACTION = -0.08667773
TRACK_AMBIENT_DELTA_COEF = 1.68976762

# Frozen LOYO horizon uncertainty
TRACK_HORIZON_SD = {
    0:   0.0,
    15:  1.4565,
    30:  1.9506,
    45:  2.2746,
    60:  2.6001,
    90:  3.21385,
    120: 3.44328,
    150: 3.77118,
    180: 3.87011,
}

MAX_DEFAULT_HORIZON_MIN = 120
DEFAULT_STEP_MIN = 1
DEFAULT_DRAWS = 20000
DEFAULT_SEED = 20260913


# ============================================================
# Helpers
# ============================================================

def parse_timestamp(value):

    ts = pd.Timestamp(
        value
    )

    if ts.tzinfo is None:

        raise ValueError(
            f"Timestamp must contain timezone/UTC offset: {value}"
        )

    return ts.tz_convert(
        "UTC"
    )


def detect_column(
    df,
    preferred,
    contains=None,
):

    for c in preferred:

        if c in df.columns:
            return c

    if contains:

        candidates = []

        for c in df.columns:

            s = str(
                c
            ).lower()

            if all(
                token.lower() in s
                for token in contains
            ):

                candidates.append(
                    c
                )

        if candidates:

            return candidates[0]

    return None


def interpolate_horizon_sd(
    wait_minutes
):

    x = np.array(
        sorted(
            TRACK_HORIZON_SD.keys()
        ),
        dtype=float
    )

    y = np.array(
        [
            TRACK_HORIZON_SD[
                int(v)
            ]
            for v in x
        ],
        dtype=float
    )

    return float(
        np.interp(
            wait_minutes,
            x,
            y
        )
    )


def find_standardized_track_residual_file():

    candidates = list(
        R5.glob(
            "*standardized*residual*.csv"
        )
    )

    candidates += list(
        R5.glob(
            "*future*state*residual*.csv"
        )
    )

    candidates += list(
        R5.glob(
            "*track*residual*.csv"
        )
    )

    # deduplicate
    seen = set()
    unique = []

    for p in candidates:

        rp = str(
            p.resolve()
        )

        if rp not in seen:

            seen.add(
                rp
            )

            unique.append(
                p
            )

    for p in unique:

        try:

            df = pd.read_csv(
                p,
                low_memory=False
            )

        except Exception:

            continue

        numeric_candidates = []

        for c in df.columns:

            s = str(
                c
            ).lower()

            if (
                "standard" in s
                and
                "resid" in s
            ):

                vals = pd.to_numeric(
                    df[c],
                    errors="coerce"
                )

                if vals.notna().sum() >= 10:

                    numeric_candidates.append(
                        c
                    )

        if numeric_candidates:

            return (
                p,
                numeric_candidates[0],
                df
            )

    return (
        None,
        None,
        None
    )


def load_track_standardized_residuals():

    path, col, df = (
        find_standardized_track_residual_file()
    )

    if path is None:

        # Conservative fallback:
        # Gaussian standardized residual.
        # This is only used if frozen empirical residual file
        # cannot be discovered.
        return {
            "mode":
                "GAUSSIAN_STANDARDIZED_FALLBACK",

            "path":
                None,

            "values":
                None,
        }

    values = pd.to_numeric(
        df[col],
        errors="coerce"
    ).dropna().to_numpy(
        dtype=float
    )

    return {
        "mode":
            "EMPIRICAL_STANDARDIZED",

        "path":
            path,

        "column":
            col,

        "values":
            values,
    }


def load_performance_residuals():

    df = pd.read_csv(
        PERFORMANCE_RESIDUALS,
        low_memory=False
    )

    preferred = [
        "residual_mph",
        "loyo_residual_mph",
        "residual",
        "error_mph",
        "error",
    ]

    col = detect_column(
        df,
        preferred
    )

    if col is None:

        # Find numeric residual-like column
        for c in df.columns:

            s = str(
                c
            ).lower()

            if (
                "resid" in s
                or
                "error" in s
            ):

                vals = pd.to_numeric(
                    df[c],
                    errors="coerce"
                )

                if vals.notna().sum() >= 10:

                    col = c
                    break

    if col is None:

        raise RuntimeError(
            "Could not detect performance residual column in "
            f"{PERFORMANCE_RESIDUALS}"
        )

    residuals = pd.to_numeric(
        df[col],
        errors="coerce"
    ).dropna().to_numpy(
        dtype=float
    )

    if len(
        residuals
    ) < 10:

        raise RuntimeError(
            "Too few usable LOYO residuals."
        )

    median = np.median(
        residuals
    )

    magnitudes = np.abs(
        residuals
        -
        median
    )

    return {
        "column":
            col,

        "raw":
            residuals,

        "median":
            float(
                median
            ),

        "magnitudes":
            magnitudes,
    }


def load_beta_bootstrap():

    df = pd.read_csv(
        BETA_BOOTSTRAP,
        low_memory=False
    )

    track_col = detect_column(
        df,
        [
            "beta_track",
            "beta_track_mph_per_c",
            "track_beta",
        ],
        contains=[
            "track"
        ]
    )

    ambient_col = detect_column(
        df,
        [
            "beta_ambient",
            "beta_ambient_mph_per_c",
            "ambient_beta",
            "beta_air",
        ],
        contains=[
            "ambient"
        ]
    )

    if track_col is None:

        # stronger heuristic
        for c in df.columns:

            s = str(
                c
            ).lower()

            if (
                "beta" in s
                and
                "track" in s
            ):

                track_col = c
                break

    if ambient_col is None:

        for c in df.columns:

            s = str(
                c
            ).lower()

            if (
                "beta" in s
                and
                (
                    "ambient" in s
                    or
                    "air" in s
                )
            ):

                ambient_col = c
                break

    if (
        track_col is None
        or
        ambient_col is None
    ):

        raise RuntimeError(
            "Could not detect beta columns in "
            f"{BETA_BOOTSTRAP}"
        )

    beta_track = pd.to_numeric(
        df[
            track_col
        ],
        errors="coerce"
    )

    beta_ambient = pd.to_numeric(
        df[
            ambient_col
        ],
        errors="coerce"
    )

    valid = (
        beta_track.notna()
        &
        beta_ambient.notna()
    )

    out = pd.DataFrame({
        "beta_track":
            beta_track[
                valid
            ].to_numpy(),

        "beta_ambient":
            beta_ambient[
                valid
            ].to_numpy(),
    })

    if len(
        out
    ) < 100:

        raise RuntimeError(
            "Too few valid coefficient bootstrap rows."
        )

    return out


# ============================================================
# Forecast
# ============================================================

def load_forecast(
    path,
    current_time_utc,
    current_ambient_c,
):

    df = pd.read_csv(
        path,
        low_memory=False
    )

    time_col = detect_column(
        df,
        [
            "timestamp_utc",
            "datetime_utc",
            "valid_time_utc",
            "time_utc",
            "timestamp",
            "datetime",
        ]
    )

    ambient_col = detect_column(
        df,
        [
            "ambient_c",
            "air_temp_c",
            "temperature_c",
            "temp_c",
            "forecast_ambient_c",
            "forecast_air_temp_c",
        ]
    )

    if time_col is None:

        raise RuntimeError(
            "Forecast CSV needs a timestamp column such as "
            "timestamp_utc or datetime_utc."
        )

    if ambient_col is None:

        raise RuntimeError(
            "Forecast CSV needs ambient temperature in Celsius, "
            "for example ambient_c."
        )

    timestamps = pd.to_datetime(
        df[
            time_col
        ],
        utc=True,
        errors="coerce"
    )

    ambient = pd.to_numeric(
        df[
            ambient_col
        ],
        errors="coerce"
    )

    forecast = pd.DataFrame({
        "timestamp_utc":
            timestamps,

        "ambient_c":
            ambient,
    })

    forecast = forecast[
        forecast[
            "timestamp_utc"
        ].notna()
        &
        forecast[
            "ambient_c"
        ].notna()
    ].copy()

    forecast = (
        forecast
        .drop_duplicates(
            subset=[
                "timestamp_utc"
            ]
        )
        .sort_values(
            "timestamp_utc"
        )
        .reset_index(
            drop=True
        )
    )

    # Force current observed state as t=0 anchor.
    anchor = pd.DataFrame({
        "timestamp_utc": [
            current_time_utc
        ],

        "ambient_c": [
            current_ambient_c
        ],
    })

    forecast = pd.concat(
        [
            forecast,
            anchor,
        ],
        ignore_index=True
    )

    forecast = (
        forecast
        .sort_values(
            "timestamp_utc"
        )
        .drop_duplicates(
            subset=[
                "timestamp_utc"
            ],
            keep="last"
        )
        .reset_index(
            drop=True
        )
    )

    future = forecast[
        forecast[
            "timestamp_utc"
        ]
        >=
        current_time_utc
    ].copy()

    if future.empty:

        raise RuntimeError(
            "Forecast has no coverage at or after current time."
        )

    return future


def forecast_ambient_at(
    forecast,
    target_times,
):

    x = (
        forecast[
            "timestamp_utc"
        ]
        .astype(
            "int64"
        )
        .to_numpy(
            dtype=np.int64
        )
    )

    y = (
        forecast[
            "ambient_c"
        ]
        .to_numpy(
            dtype=float
        )
    )

    tx = (
        pd.DatetimeIndex(
            target_times
        )
        .astype(
            "int64"
        )
        .to_numpy(
            dtype=np.int64
        )
    )

    return np.interp(
        tx,
        x,
        y
    )


# ============================================================
# Simulation
# ============================================================

def simulate_curve(
    current_speed_mph,
    current_track_c,
    current_ambient_c,
    current_time_utc,
    session_end_utc,
    forecast,
    requested_horizon_min,
    step_min,
    draws,
    seed,
):

    rng = np.random.default_rng(
        seed
    )

    session_remaining_min = (
        (
            session_end_utc
            -
            current_time_utc
        ).total_seconds()
        /
        60.0
    )

    if session_remaining_min <= 0:

        raise ValueError(
            "Session has already ended."
        )

    forecast_end = forecast[
        "timestamp_utc"
    ].max()

    forecast_remaining_min = (
        (
            forecast_end
            -
            current_time_utc
        ).total_seconds()
        /
        60.0
    )

    actual_horizon_min = min(
        float(
            requested_horizon_min
        ),
        float(
            session_remaining_min
        ),
        float(
            forecast_remaining_min
        ),
    )

    if actual_horizon_min <= 0:

        raise RuntimeError(
            "No usable future forecast horizon."
        )

    waits = np.arange(
        0.0,
        actual_horizon_min + 1e-9,
        float(
            step_min
        )
    )

    # Always include exact horizon endpoint
    if (
        len(
            waits
        ) == 0
        or
        waits[-1]
        <
        actual_horizon_min
        -
        1e-9
    ):

        waits = np.append(
            waits,
            actual_horizon_min
        )

    target_times = [
        current_time_utc
        +
        pd.Timedelta(
            minutes=float(
                w
            )
        )
        for w in waits
    ]

    ambient_future = forecast_ambient_at(
        forecast,
        target_times,
    )

    delta_ambient = (
        ambient_future
        -
        float(
            current_ambient_c
        )
    )

    beta_boot = load_beta_bootstrap()

    beta_idx = rng.integers(
        0,
        len(
            beta_boot
        ),
        size=draws
    )

    beta_track_draw = (
        beta_boot[
            "beta_track"
        ]
        .to_numpy(
            dtype=float
        )[
            beta_idx
        ]
    )

    beta_ambient_draw = (
        beta_boot[
            "beta_ambient"
        ]
        .to_numpy(
            dtype=float
        )[
            beta_idx
        ]
    )

    performance_resid = (
        load_performance_residuals()
    )

    magnitudes = (
        performance_resid[
            "magnitudes"
        ]
    )

    mag_idx = rng.integers(
        0,
        len(
            magnitudes
        ),
        size=draws
    )

    signs = rng.choice(
        np.array(
            [
                -1.0,
                1.0
            ]
        ),
        size=draws
    )

    # Frozen core uses symmetric empirical residual magnitude.
    perf_noise = (
        magnitudes[
            mag_idx
        ]
        *
        signs
    )

    track_resid_info = (
        load_track_standardized_residuals()
    )

    rows = []

    for (
        wait_min,
        target_time,
        future_ambient_c,
        d_ambient
    ) in zip(
        waits,
        target_times,
        ambient_future,
        delta_ambient,
    ):

        h = (
            float(
                wait_min
            )
            /
            60.0
        )

        mean_delta_track = (
            TRACK_WAIT_COEF
            *
            h
            +
            TRACK_CURRENT_TEMP_INTERACTION
            *
            h
            *
            (
                float(
                    current_track_c
                )
                -
                40.0
            )
            +
            TRACK_AMBIENT_DELTA_COEF
            *
            float(
                d_ambient
            )
        )

        track_sd = (
            interpolate_horizon_sd(
                float(
                    wait_min
                )
            )
        )

        if wait_min == 0:

            track_noise = np.zeros(
                draws,
                dtype=float
            )

        elif (
            track_resid_info[
                "mode"
            ]
            ==
            "EMPIRICAL_STANDARDIZED"
        ):

            std_values = track_resid_info[
                "values"
            ]

            idx = rng.integers(
                0,
                len(
                    std_values
                ),
                size=draws
            )

            track_noise = (
                std_values[
                    idx
                ]
                *
                track_sd
            )

        else:

            track_noise = (
                rng.normal(
                    0.0,
                    1.0,
                    size=draws
                )
                *
                track_sd
            )

        delta_track_draw = (
            mean_delta_track
            +
            track_noise
        )

        physical_delta_speed = (
            beta_track_draw
            *
            delta_track_draw
            +
            beta_ambient_draw
            *
            float(
                d_ambient
            )
        )

        total_delta_speed = (
            physical_delta_speed
            +
            perf_noise
        )

        expected_physical_delta = float(
            np.mean(
                physical_delta_speed
            )
        )

        total_median = float(
            np.median(
                total_delta_speed
            )
        )

        q05 = float(
            np.quantile(
                total_delta_speed,
                0.05
            )
        )

        q10 = float(
            np.quantile(
                total_delta_speed,
                0.10
            )
        )

        q90 = float(
            np.quantile(
                total_delta_speed,
                0.90
            )
        )

        q95 = float(
            np.quantile(
                total_delta_speed,
                0.95
            )
        )

        p_improve = float(
            np.mean(
                total_delta_speed
                >
                0.0
            )
        )

        rows.append({
            "wait_minutes":
                float(
                    wait_min
                ),

            "target_time_utc":
                target_time,

            "forecast_ambient_c":
                float(
                    future_ambient_c
                ),

            "delta_ambient_c":
                float(
                    d_ambient
                ),

            "expected_delta_track_c":
                float(
                    mean_delta_track
                ),

            "track_uncertainty_sd_c":
                float(
                    track_sd
                ),

            "expected_physical_delta_speed_mph":
                expected_physical_delta,

            "median_total_delta_speed_mph":
                total_median,

            "q10_delta_speed_mph":
                q10,

            "q90_delta_speed_mph":
                q90,

            "q05_delta_speed_mph":
                q05,

            "q95_delta_speed_mph":
                q95,

            "p_improve":
                p_improve,

            "expected_future_speed_mph":
                float(
                    current_speed_mph
                    +
                    expected_physical_delta
                ),

            "median_future_speed_mph":
                float(
                    current_speed_mph
                    +
                    total_median
                ),
        })

    curve = pd.DataFrame(
        rows
    )

    metadata = {
        "requested_max_horizon_minutes":
            float(
                requested_horizon_min
            ),

        "actual_horizon_minutes":
            float(
                actual_horizon_min
            ),

        "session_remaining_minutes":
            float(
                session_remaining_min
            ),

        "forecast_remaining_minutes":
            float(
                forecast_remaining_min
            ),

        "step_minutes":
            float(
                step_min
            ),

        "monte_carlo_draws":
            int(
                draws
            ),

        "track_residual_mode":
            track_resid_info[
                "mode"
            ],

        "track_residual_source":
            (
                str(
                    track_resid_info[
                        "path"
                    ].relative_to(
                        ROOT
                    )
                )
                if track_resid_info.get(
                    "path"
                )
                is not None
                else None
            ),

        "performance_residual_column":
            performance_resid[
                "column"
            ],

        "physics_core":
            "R5_2_FROZEN_2020_2024",

        "queue_wait_prediction":
            False,

        "strategy_recommendation":
            False,

        "interpretation":
            (
                "Each x-axis position is a hypothetical opportunity "
                "to make a future qualifying attempt. The model does "
                "not predict when a car will actually reach the front "
                "of the queue."
            ),
    }

    return (
        curve,
        metadata
    )


# ============================================================
# Plot
# ============================================================

def plot_performance_curve(
    curve,
    output_path,
):

    x = curve[
        "wait_minutes"
    ].to_numpy(
        dtype=float
    )

    mean = curve[
        "expected_physical_delta_speed_mph"
    ].to_numpy(
        dtype=float
    )

    q10 = curve[
        "q10_delta_speed_mph"
    ].to_numpy(
        dtype=float
    )

    q90 = curve[
        "q90_delta_speed_mph"
    ].to_numpy(
        dtype=float
    )

    q05 = curve[
        "q05_delta_speed_mph"
    ].to_numpy(
        dtype=float
    )

    q95 = curve[
        "q95_delta_speed_mph"
    ].to_numpy(
        dtype=float
    )

    fig, ax = plt.subplots(
        figsize=(
            11,
            6.5
        )
    )

    ax.fill_between(
        x,
        q05,
        q95,
        alpha=0.12,
        label="90% uncertainty"
    )

    ax.fill_between(
        x,
        q10,
        q90,
        alpha=0.20,
        label="80% uncertainty"
    )

    ax.plot(
        x,
        mean,
        linewidth=2.2,
        label="Expected physical Δspeed"
    )

    ax.axhline(
        0.0,
        linewidth=1.0,
        linestyle="--"
    )

    ax.set_xlabel(
        "Minutes from now"
    )

    ax.set_ylabel(
        "Change in four-lap average speed (mph)"
    )

    ax.set_title(
        "Indy 500 Qualifying Performance Outlook"
    )

    ax.legend()

    ax.grid(
        alpha=0.20
    )

    fig.tight_layout()

    fig.savefig(
        output_path,
        dpi=180
    )

    plt.close(
        fig
    )


def plot_probability_curve(
    curve,
    output_path,
):

    x = curve[
        "wait_minutes"
    ].to_numpy(
        dtype=float
    )

    p = curve[
        "p_improve"
    ].to_numpy(
        dtype=float
    )

    fig, ax = plt.subplots(
        figsize=(
            11,
            4.8
        )
    )

    ax.plot(
        x,
        p,
        linewidth=2.2
    )

    ax.axhline(
        0.5,
        linewidth=1.0,
        linestyle="--"
    )

    ax.set_ylim(
        0.0,
        1.0
    )

    ax.set_xlabel(
        "Minutes from now"
    )

    ax.set_ylabel(
        "P(improve)"
    )

    ax.set_title(
        "Probability of Improving Current Official Result"
    )

    ax.grid(
        alpha=0.20
    )

    fig.tight_layout()

    fig.savefig(
        output_path,
        dpi=180
    )

    plt.close(
        fig
    )


# ============================================================
# Main CLI
# ============================================================

def main():

    parser = argparse.ArgumentParser(
        description=(
            "Production-style probabilistic inference layer for "
            "Indy 500 qualifying performance outlook."
        )
    )

    parser.add_argument(
        "--current-speed",
        type=float,
        required=True,
        help="Current official four-lap average speed in mph."
    )

    parser.add_argument(
        "--current-track-c",
        type=float,
        required=True,
        help="Current observed track temperature in Celsius."
    )

    parser.add_argument(
        "--current-ambient-c",
        type=float,
        required=True,
        help="Current observed ambient temperature in Celsius."
    )

    parser.add_argument(
        "--current-time",
        type=str,
        required=True,
        help=(
            "Current timestamp with timezone offset, "
            "e.g. 2025-05-17T15:00:00-04:00"
        )
    )

    parser.add_argument(
        "--session-end",
        type=str,
        required=True,
        help=(
            "Session-end timestamp with timezone offset."
        )
    )

    parser.add_argument(
        "--forecast",
        type=Path,
        required=True,
        help=(
            "CSV containing timestamp_utc/datetime_utc "
            "and ambient_c."
        )
    )

    parser.add_argument(
        "--max-horizon-min",
        type=float,
        default=MAX_DEFAULT_HORIZON_MIN,
        help="Maximum inference horizon. Default = 120 min."
    )

    parser.add_argument(
        "--step-min",
        type=float,
        default=DEFAULT_STEP_MIN,
        help="Curve resolution in minutes. Default = 1."
    )

    parser.add_argument(
        "--draws",
        type=int,
        default=DEFAULT_DRAWS,
        help="Monte Carlo draws per horizon point."
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=DEFAULT_SEED,
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=(
            ROOT /
            "r6_regime_extension/output/"
            "production_inference_v1"
        ),
    )

    args = parser.parse_args()

    # --------------------------------------------------------
    # Frozen-input presence gate
    # --------------------------------------------------------

    required_files = [
        BETA_BOOTSTRAP,
        PERFORMANCE_RESIDUALS,
        CORE_JSON,
        CORE_MANIFEST,
        args.forecast,
    ]

    missing = [
        str(
            p
        )
        for p in required_files
        if not p.exists()
    ]

    if missing:

        raise FileNotFoundError(
            "Missing required inference inputs:\n"
            +
            "\n".join(
                missing
            )
        )

    current_time_utc = parse_timestamp(
        args.current_time
    )

    session_end_utc = parse_timestamp(
        args.session_end
    )

    forecast = load_forecast(
        args.forecast,
        current_time_utc,
        args.current_ambient_c,
    )

    curve, metadata = simulate_curve(
        current_speed_mph=args.current_speed,
        current_track_c=args.current_track_c,
        current_ambient_c=args.current_ambient_c,
        current_time_utc=current_time_utc,
        session_end_utc=session_end_utc,
        forecast=forecast,
        requested_horizon_min=args.max_horizon_min,
        step_min=args.step_min,
        draws=args.draws,
        seed=args.seed,
    )

    outdir = args.output_dir

    outdir.mkdir(
        parents=True,
        exist_ok=True
    )

    curve_out = (
        outdir /
        "qualifying_performance_outlook_curve_v1.csv"
    )

    performance_plot = (
        outdir /
        "qualifying_performance_outlook_curve_v1.png"
    )

    probability_plot = (
        outdir /
        "qualifying_probability_of_improvement_v1.png"
    )

    metadata_out = (
        outdir /
        "qualifying_inference_metadata_v1.json"
    )

    curve.to_csv(
        curve_out,
        index=False
    )

    plot_performance_curve(
        curve,
        performance_plot
    )

    plot_probability_curve(
        curve,
        probability_plot
    )

    metadata.update({
        "current_speed_mph":
            float(
                args.current_speed
            ),

        "current_track_c":
            float(
                args.current_track_c
            ),

        "current_ambient_c":
            float(
                args.current_ambient_c
            ),

        "current_time_utc":
            str(
                current_time_utc
            ),

        "session_end_utc":
            str(
                session_end_utc
            ),

        "forecast_file":
            str(
                args.forecast
            ),
    })

    metadata_out.write_text(
        json.dumps(
            metadata,
            indent=2
        ),
        encoding="utf-8"
    )

    # --------------------------------------------------------
    # Console summary
    # --------------------------------------------------------

    print(
        "=" * 160
    )

    print(
        "PRODUCTION INFERENCE V1"
    )

    print(
        "=" * 160
    )

    print(
        "Physics core:",
        metadata[
            "physics_core"
        ]
    )

    print(
        "Queue-wait prediction:",
        metadata[
            "queue_wait_prediction"
        ]
    )

    print(
        "Strategy recommendation:",
        metadata[
            "strategy_recommendation"
        ]
    )

    print(
        "Requested max horizon:",
        metadata[
            "requested_max_horizon_minutes"
        ],
        "min"
    )

    print(
        "Actual horizon:",
        round(
            metadata[
                "actual_horizon_minutes"
            ],
            3
        ),
        "min"
    )

    print(
        "Session remaining:",
        round(
            metadata[
                "session_remaining_minutes"
            ],
            3
        ),
        "min"
    )

    print(
        "Forecast remaining:",
        round(
            metadata[
                "forecast_remaining_minutes"
            ],
            3
        ),
        "min"
    )

    print(
        "Curve points:",
        len(
            curve
        )
    )

    print(
        "\nSELECTED HORIZON SNAPSHOTS"
    )

    print(
        "-" * 160
    )

    selected = [
        0,
        15,
        30,
        45,
        60,
        90,
        120,
    ]

    snapshots = []

    for target in selected:

        if target > curve[
            "wait_minutes"
        ].max():
            continue

        idx = (
            curve[
                "wait_minutes"
            ]
            -
            target
        ).abs().idxmin()

        snapshots.append(
            curve.loc[
                idx
            ]
        )

    snapshot_df = pd.DataFrame(
        snapshots
    )

    print(
        snapshot_df[
            [
                "wait_minutes",
                "expected_delta_track_c",
                "delta_ambient_c",
                "expected_physical_delta_speed_mph",
                "q10_delta_speed_mph",
                "q90_delta_speed_mph",
                "q05_delta_speed_mph",
                "q95_delta_speed_mph",
                "p_improve",
            ]
        ].to_string(
            index=False
        )
    )

    best_idx = curve[
        "expected_physical_delta_speed_mph"
    ].idxmax()

    best = curve.loc[
        best_idx
    ]

    print(
        "\nMAX EXPECTED PHYSICAL ΔSPEED POINT"
    )

    print(
        "-" * 160
    )

    print(
        "wait_minutes =",
        round(
            float(
                best[
                    "wait_minutes"
                ]
            ),
            3
        )
    )

    print(
        "expected_delta_speed_mph =",
        round(
            float(
                best[
                    "expected_physical_delta_speed_mph"
                ]
            ),
            6
        )
    )

    print(
        "p_improve =",
        round(
            float(
                best[
                    "p_improve"
                ]
            ),
            6
        )
    )

    print(
        "\nOUTPUTS"
    )

    print(
        "-" * 160
    )

    for p in [
        curve_out,
        performance_plot,
        probability_plot,
        metadata_out,
    ]:

        print(
            p.relative_to(
                ROOT
            )
        )

    print(
        "\nR6_PRODUCTION_INFERENCE_V1_COMPLETE"
    )


if __name__ == "__main__":

    main()
