from pathlib import Path
from datetime import datetime, timedelta, timezone
import math

import numpy as np
import pandas as pd


# ============================================================
# INPUT FILES
# ============================================================

TRACK_COEF_FILE = Path(
    "weather/output/v2_future_track/"
    "v2a_full_sample_track_model_coefficients_v1.csv"
)

TRACK_RESID_FILE = Path(
    "weather/output/v2_future_track/"
    "future_track_residuals_v1.csv"
)

PERF_BOOT_FILE = Path(
    "r5_2/manual/"
    "probabilistic_physics_coefficient_bootstrap_v1.csv"
)

PERF_RESID_FILE = Path(
    "r5_2/manual/"
    "probabilistic_physics_loyo_residuals_v1.csv"
)

OUTPUT_DIR = Path(
    "weather/output/v2_future_track"
)

OUTPUT_FILE = (
    OUTPUT_DIR
    / "v2a_operational_scenario_outlook_v1.csv"
)

SUMMARY_FILE = (
    OUTPUT_DIR
    / "v2a_operational_scenario_outlook_v1.txt"
)


# ============================================================
# SETTINGS
# ============================================================

N_MC = 50000
RANDOM_SEED = 20260914

HORIZONS = [
    15,
    30,
    60,
    90,
    120,
]

# Demonstration current state only.
CURRENT_TRACK_C = 40.0
CURRENT_AMBIENT_C = 24.0

# Example UTC time near Indy qualifying midday.
CURRENT_UTC = datetime(
    2025,
    5,
    17,
    16,
    0,
    tzinfo=timezone.utc,
)

IMS_LAT = 39.7950
IMS_LON = -86.2348


# ============================================================
# AMBIENT SCENARIOS
#
# Change at 120 min.
# Intermediate horizons are linearly interpolated.
# ============================================================

SCENARIOS = {
    "cooling": -2.0,
    "neutral": 0.0,
    "warming": +2.0,
}


# ============================================================
# SOLAR GEOMETRY
# NOAA-style approximate elevation
# ============================================================

def solar_elevation_deg(dt_utc, lat_deg, lon_deg):

    dt_utc = dt_utc.astimezone(
        timezone.utc
    )

    day_of_year = dt_utc.timetuple().tm_yday

    hour = (
        dt_utc.hour
        + dt_utc.minute / 60.0
        + dt_utc.second / 3600.0
    )

    gamma = (
        2.0
        * math.pi
        / 365.0
        * (
            day_of_year
            - 1
            + (hour - 12.0) / 24.0
        )
    )

    eqtime = 229.18 * (
        0.000075
        + 0.001868 * math.cos(gamma)
        - 0.032077 * math.sin(gamma)
        - 0.014615 * math.cos(2 * gamma)
        - 0.040849 * math.sin(2 * gamma)
    )

    decl = (
        0.006918
        - 0.399912 * math.cos(gamma)
        + 0.070257 * math.sin(gamma)
        - 0.006758 * math.cos(2 * gamma)
        + 0.000907 * math.sin(2 * gamma)
        - 0.002697 * math.cos(3 * gamma)
        + 0.00148 * math.sin(3 * gamma)
    )

    time_offset = (
        eqtime
        + 4.0 * lon_deg
    )

    true_solar_time = (
        hour * 60.0
        + time_offset
    )

    hour_angle_deg = (
        true_solar_time / 4.0
        - 180.0
    )

    lat = math.radians(
        lat_deg
    )

    ha = math.radians(
        hour_angle_deg
    )

    cos_zenith = (
        math.sin(lat)
        * math.sin(decl)
        +
        math.cos(lat)
        * math.cos(decl)
        * math.cos(ha)
    )

    cos_zenith = min(
        1.0,
        max(-1.0, cos_zenith)
    )

    zenith = math.acos(
        cos_zenith
    )

    return (
        90.0
        - math.degrees(
            zenith
        )
    )


def symmetrized_draws(
    values,
    n,
    rng,
):

    values = np.asarray(
        values,
        dtype=float,
    )

    values = values[
        np.isfinite(values)
    ]

    mag = rng.choice(
        np.abs(values),
        size=n,
        replace=True,
    )

    sign = rng.choice(
        [-1.0, 1.0],
        size=n,
        replace=True,
    )

    return mag * sign


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 80)
    print(
        "INDY 500 V2-A OPERATIONAL SCENARIO OUTLOOK"
    )
    print("=" * 80)

    rng = np.random.default_rng(
        RANDOM_SEED
    )

    track_coef = pd.read_csv(
        TRACK_COEF_FILE
    )

    track_resid = pd.read_csv(
        TRACK_RESID_FILE
    )

    perf_boot = pd.read_csv(
        PERF_BOOT_FILE
    )

    perf_resid = pd.read_csv(
        PERF_RESID_FILE
    )

    # --------------------------------------------------------
    # Paired coefficient bootstrap
    # --------------------------------------------------------

    boot = (
        perf_boot[
            [
                "beta_track_temp",
                "beta_ambient_temp",
            ]
        ]
        .dropna()
        .reset_index(drop=True)
    )

    # --------------------------------------------------------
    # Performance residual
    # --------------------------------------------------------

    perf_resid_values = (
        perf_resid[
            "residual_loyo_centered"
        ]
        .dropna()
        .to_numpy()
    )

    # --------------------------------------------------------
    # Track residual pools
    # --------------------------------------------------------

    tr = track_resid[
        track_resid["model"]
        == "M2b_mean_solar"
    ].copy()

    track_pools = {}

    for h in HORIZONS:

        track_pools[h] = (
            tr.loc[
                tr["horizon_min"] == h,
                "residual_c",
            ]
            .dropna()
            .to_numpy()
        )

    thermal_gap = (
        CURRENT_TRACK_C
        - CURRENT_AMBIENT_C
    )

    current_solar = solar_elevation_deg(
        CURRENT_UTC,
        IMS_LAT,
        IMS_LON,
    )

    rows = []

    for scenario_name, delta120 in (
        SCENARIOS.items()
    ):

        for horizon in HORIZONS:

            # ----------------------------------------------
            # Ambient trajectory
            # ----------------------------------------------

            delta_ambient = (
                delta120
                * horizon
                / 120.0
            )

            future_ambient = (
                CURRENT_AMBIENT_C
                + delta_ambient
            )

            future_time = (
                CURRENT_UTC
                + timedelta(
                    minutes=horizon
                )
            )

            future_solar = (
                solar_elevation_deg(
                    future_time,
                    IMS_LAT,
                    IMS_LON,
                )
            )

            mean_solar = (
                current_solar
                + future_solar
            ) / 2.0

            # ----------------------------------------------
            # Horizon-specific track point model
            # ----------------------------------------------

            c = track_coef[
                track_coef[
                    "horizon_min"
                ]
                == horizon
            ].iloc[0]

            point_delta_track = (
                c["intercept_c"]
                +
                c[
                    "beta_delta_ambient_temp_c"
                ]
                * delta_ambient
                +
                c[
                    "beta_thermal_gap_0_c"
                ]
                * thermal_gap
                +
                c[
                    "beta_solar_elevation_mean_deg"
                ]
                * mean_solar
            )

            # ----------------------------------------------
            # Track uncertainty
            # ----------------------------------------------

            track_noise = (
                symmetrized_draws(
                    track_pools[horizon],
                    N_MC,
                    rng,
                )
            )

            delta_track_draw = (
                point_delta_track
                + track_noise
            )

            # ----------------------------------------------
            # Paired bootstrap coefficients
            # ----------------------------------------------

            ids = rng.integers(
                0,
                len(boot),
                size=N_MC,
            )

            beta_track = (
                boot[
                    "beta_track_temp"
                ]
                .to_numpy()[ids]
            )

            beta_ambient = (
                boot[
                    "beta_ambient_temp"
                ]
                .to_numpy()[ids]
            )

            # ----------------------------------------------
            # Performance uncertainty
            # ----------------------------------------------

            perf_noise = (
                symmetrized_draws(
                    perf_resid_values,
                    N_MC,
                    rng,
                )
            )

            # ----------------------------------------------
            # Final Δspeed distribution
            # ----------------------------------------------

            dv = (
                beta_track
                * delta_track_draw
                +
                beta_ambient
                * delta_ambient
                +
                perf_noise
            )

            rows.append(
                {
                    "scenario":
                        scenario_name,

                    "horizon_min":
                        horizon,

                    "current_track_c":
                        CURRENT_TRACK_C,

                    "current_ambient_c":
                        CURRENT_AMBIENT_C,

                    "future_ambient_c":
                        future_ambient,

                    "delta_ambient_c":
                        delta_ambient,

                    "thermal_gap_0_c":
                        thermal_gap,

                    "solar_elevation_0_deg":
                        current_solar,

                    "future_solar_elevation_deg":
                        future_solar,

                    "solar_elevation_mean_deg":
                        mean_solar,

                    "expected_delta_track_c":
                        point_delta_track,

                    "expected_future_track_c":
                        (
                            CURRENT_TRACK_C
                            + point_delta_track
                        ),

                    "expected_delta_speed_mph":
                        np.mean(dv),

                    "median_delta_speed_mph":
                        np.median(dv),

                    "p_improve":
                        np.mean(
                            dv > 0
                        ),

                    "lower_80_mph":
                        np.quantile(
                            dv,
                            0.10,
                        ),

                    "upper_80_mph":
                        np.quantile(
                            dv,
                            0.90,
                        ),

                    "lower_90_mph":
                        np.quantile(
                            dv,
                            0.05,
                        ),

                    "upper_90_mph":
                        np.quantile(
                            dv,
                            0.95,
                        ),

                    "mc_sd_mph":
                        np.std(
                            dv,
                            ddof=1,
                        ),

                    "n_mc":
                        N_MC,
                }
            )

    out = pd.DataFrame(
        rows
    )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    out.to_csv(
        OUTPUT_FILE,
        index=False,
    )

    # ========================================================
    # SUMMARY
    # ========================================================

    display_cols = [
        "scenario",
        "horizon_min",
        "delta_ambient_c",
        "expected_delta_track_c",
        "expected_delta_speed_mph",
        "p_improve",
        "lower_80_mph",
        "upper_80_mph",
        "lower_90_mph",
        "upper_90_mph",
    ]

    lines = []

    def add(x=""):
        lines.append(
            str(x)
        )

    add("=" * 80)
    add(
        "INDY 500 V2-A OPERATIONAL SCENARIO OUTLOOK"
    )
    add("=" * 80)

    add()
    add("CURRENT STATE")
    add(
        f"UTC time: {CURRENT_UTC.isoformat()}"
    )
    add(
        f"track temperature: "
        f"{CURRENT_TRACK_C:.2f} C"
    )
    add(
        f"ambient temperature: "
        f"{CURRENT_AMBIENT_C:.2f} C"
    )
    add(
        f"thermal gap: "
        f"{thermal_gap:.2f} C"
    )
    add(
        f"solar elevation: "
        f"{current_solar:.2f} deg"
    )

    for scenario in SCENARIOS:

        add()
        add("=" * 80)
        add(
            f"SCENARIO: {scenario.upper()}"
        )
        add("=" * 80)
        add()

        d = out[
            out["scenario"]
            == scenario
        ][display_cols]

        add(
            d.round(4)
            .to_string(
                index=False
            )
        )

    add()
    add("=" * 80)
    add("INTERPRETATION CONTRACT")
    add("=" * 80)

    add()
    add(
        "h is a scenario axis: "
        "'if another on-track opportunity occurs h minutes from now'."
    )

    add(
        "This model does not predict queue waiting time "
        "or probability that another attempt becomes available."
    )

    add(
        "Ambient trajectories in this demonstration are explicit scenarios, "
        "not weather forecasts."
    )

    add(
        "P(improve) is physical-performance probability conditional on "
        "the stated future opportunity and environmental scenario."
    )

    add(
        "It is not a retain/withdraw recommendation."
    )

    summary = "\n".join(
        lines
    )

    SUMMARY_FILE.write_text(
        summary,
        encoding="utf-8",
    )

    print()
    print(summary)

    print()
    print("OUTPUT")
    print(OUTPUT_FILE)
    print(SUMMARY_FILE)
    print()
    print("DONE")


if __name__ == "__main__":
    main()
