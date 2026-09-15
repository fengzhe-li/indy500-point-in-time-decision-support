from pathlib import Path
import hashlib
import json

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


ROOT = Path(".")

OUTDIR = Path(
    "weather/output/v2_future_track"
)

SCENARIO_FILE = (
    OUTDIR
    / "v2a_operational_scenario_outlook_v1.csv"
)

TRACK_COEF_FILE = (
    OUTDIR
    / "v2a_full_sample_track_model_coefficients_v1.csv"
)

INTEGRATION_FILE = (
    OUTDIR
    / "v2a_performance_mc_integration_v1.csv"
)

CONFORMAL_FILE = (
    OUTDIR
    / "future_track_conformal_calibration_v1.csv"
)

PERF_BOOT_FILE = Path(
    "r5_2/manual/"
    "probabilistic_physics_coefficient_bootstrap_v1.csv"
)

PERF_RESID_FILE = Path(
    "r5_2/manual/"
    "probabilistic_physics_loyo_residuals_v1.csv"
)

TRACK_RESID_FILE = (
    OUTDIR
    / "future_track_residuals_v1.csv"
)

MANIFEST_FILE = (
    OUTDIR
    / "v2a_freeze_manifest_v1.json"
)

FINAL_TABLE_FILE = (
    OUTDIR
    / "v2a_final_results_table_v1.csv"
)

FIGURE_FILE = (
    OUTDIR
    / "v2a_final_scenario_outlook_v1.png"
)

SUMMARY_FILE = (
    OUTDIR
    / "v2a_freeze_summary_v1.txt"
)


def sha256_file(path):

    h = hashlib.sha256()

    with open(path, "rb") as f:

        for chunk in iter(
            lambda: f.read(1024 * 1024),
            b"",
        ):
            h.update(chunk)

    return h.hexdigest()


def main():

    print("=" * 80)
    print(
        "INDY 500 V2-A FINAL FREEZE"
    )
    print("=" * 80)

    required = [
        SCENARIO_FILE,
        TRACK_COEF_FILE,
        INTEGRATION_FILE,
        CONFORMAL_FILE,
        PERF_BOOT_FILE,
        PERF_RESID_FILE,
        TRACK_RESID_FILE,
    ]

    for p in required:
        if not p.exists():
            raise FileNotFoundError(
                f"Missing required artifact: {p}"
            )

    scenario = pd.read_csv(
        SCENARIO_FILE
    )

    conformal = pd.read_csv(
        CONFORMAL_FILE
    )

    integration = pd.read_csv(
        INTEGRATION_FILE
    )

    track_coef = pd.read_csv(
        TRACK_COEF_FILE
    )

    # ========================================================
    # FINAL RESULTS TABLE
    # ========================================================

    final_cols = [
        "scenario",
        "horizon_min",
        "current_track_c",
        "current_ambient_c",
        "future_ambient_c",
        "delta_ambient_c",
        "thermal_gap_0_c",
        "solar_elevation_mean_deg",
        "expected_delta_track_c",
        "expected_future_track_c",
        "expected_delta_speed_mph",
        "median_delta_speed_mph",
        "p_improve",
        "lower_80_mph",
        "upper_80_mph",
        "lower_90_mph",
        "upper_90_mph",
        "mc_sd_mph",
        "n_mc",
    ]

    final_table = (
        scenario[
            final_cols
        ]
        .sort_values(
            [
                "scenario",
                "horizon_min",
            ]
        )
        .reset_index(drop=True)
    )

    final_table.to_csv(
        FINAL_TABLE_FILE,
        index=False,
    )

    # ========================================================
    # CALIBRATION SUMMARY
    # ========================================================

    c = conformal[
        conformal["model"]
        == "M2b_mean_solar"
    ].copy()

    coverage80 = np.mean(
        (
            c["actual"] >= c["lower80"]
        )
        &
        (
            c["actual"] <= c["upper80"]
        )
    )

    coverage90 = np.mean(
        (
            c["actual"] >= c["lower90"]
        )
        &
        (
            c["actual"] <= c["upper90"]
        )
    )

    # 2022 coverage
    c22 = c[
        c["held_out_year"] == 2022
    ]

    coverage80_2022 = np.mean(
        (
            c22["actual"] >= c22["lower80"]
        )
        &
        (
            c22["actual"] <= c22["upper80"]
        )
    )

    coverage90_2022 = np.mean(
        (
            c22["actual"] >= c22["lower90"]
        )
        &
        (
            c22["actual"] <= c22["upper90"]
        )
    )

    # ========================================================
    # INTEGRATION WIDTH SUMMARY
    # ========================================================

    integration = integration.copy()

    integration["width80"] = (
        integration["upper_80_mph"]
        - integration["lower_80_mph"]
    )

    integration["width90"] = (
        integration["upper_90_mph"]
        - integration["lower_90_mph"]
    )

    width_by_horizon = (
        integration.groupby(
            "horizon_min"
        )
        .agg(
            mean_width80_mph=(
                "width80",
                "mean",
            ),
            mean_width90_mph=(
                "width90",
                "mean",
            ),
        )
        .reset_index()
    )

    # ========================================================
    # FIGURE
    # ========================================================

    fig, ax = plt.subplots(
        figsize=(10, 6)
    )

    for scenario_name in [
        "cooling",
        "neutral",
        "warming",
    ]:

        d = (
            scenario[
                scenario["scenario"]
                == scenario_name
            ]
            .sort_values(
                "horizon_min"
            )
        )

        line, = ax.plot(
            d["horizon_min"],
            d[
                "expected_delta_speed_mph"
            ],
            marker="o",
            label=scenario_name.capitalize(),
        )

        ax.fill_between(
            d["horizon_min"],
            d["lower_80_mph"],
            d["upper_80_mph"],
            alpha=0.12,
            color=line.get_color(),
        )

    ax.axhline(
        0,
        linewidth=1,
    )

    ax.set_xlabel(
        "Future on-track opportunity horizon (min)"
    )

    ax.set_ylabel(
        "Expected four-lap speed change (mph)"
    )

    ax.set_title(
        "Indy 500 V2-A Conditional Performance Outlook"
    )

    ax.legend(
        title="Ambient scenario"
    )

    ax.grid(
        alpha=0.2
    )

    fig.tight_layout()

    fig.savefig(
        FIGURE_FILE,
        dpi=220,
        bbox_inches="tight",
    )

    plt.close(fig)

    # ========================================================
    # HASHES
    # ========================================================

    artifact_hashes = {}

    for p in required + [
        FINAL_TABLE_FILE,
        FIGURE_FILE,
    ]:

        artifact_hashes[
            str(p)
        ] = sha256_file(p)

    # ========================================================
    # MANIFEST
    # ========================================================

    manifest = {

        "project":
            "Indy 500 qualifying decision support",

        "version":
            "V2-A",

        "status":
            "FROZEN",

        "freeze_scope":
            "future physical-state and conditional performance outlook",

        "research_question":
            (
                "If another on-track opportunity occurs h minutes "
                "from now, what distribution of four-lap qualifying "
                "performance change should be expected relative to "
                "the current official result?"
            ),

        "opportunity_horizons_min":
            [15, 30, 60, 90, 120],

        "future_track_model": {

            "name":
                "M2b_mean_solar",

            "structure":
                "horizon-specific linear models",

            "features": [
                "future ambient temperature change",
                "current track-minus-ambient thermal gap",
                "mean solar elevation over interval",
            ],

            "rejected_features": [
                "current track heating/cooling rate",
                "delta solar elevation",
            ],

            "validation":
                "leave-one-year-out",

            "production_refit":
                "full 2020-2024 PTSC sample after model selection",

            "conditional_semantics":
                (
                    "future ambient change must come from "
                    "forecast or explicit scenario"
                ),
        },

        "future_track_uncertainty": {

            "method":
                (
                    "horizon-specific finite-sample "
                    "absolute-residual conformal calibration"
                ),

            "observed_coverage80":
                float(coverage80),

            "observed_coverage90":
                float(coverage90),

            "known_regime_shift_year":
                2022,

            "coverage80_2022":
                float(coverage80_2022),

            "coverage90_2022":
                float(coverage90_2022),
        },

        "performance_model": {

            "formula":
                (
                    "delta_v = beta_track * delta_track_temp "
                    "+ beta_ambient * delta_ambient_temp "
                    "+ epsilon"
                ),

            "coefficient_uncertainty":
                (
                    "5000 paired bootstrap coefficient draws; "
                    "joint coefficient dependence preserved"
                ),

            "performance_residual_uncertainty":
                (
                    "symmetrized magnitude of centered "
                    "leave-one-year-out residuals"
                ),

            "performance_core_frozen":
                True,
        },

        "monte_carlo": {

            "components": [
                "future track-state uncertainty",
                "paired coefficient uncertainty",
                "empirical performance residual uncertainty",
            ],

            "outputs": [
                "expected delta speed",
                "median delta speed",
                "P(delta speed > 0)",
                "80% prediction interval",
                "90% prediction interval",
            ],
        },

        "decision_semantics": {

            "h_is_scenario_axis":
                True,

            "predicts_queue_wait":
                False,

            "predicts_attempt_availability":
                False,

            "is_retain_withdraw_recommendation":
                False,

            "interpretation":
                (
                    "conditional physical-performance outlook "
                    "given a future on-track opportunity"
                ),
        },

        "known_limitations": [
            (
                "2022 exhibits strong year-level thermal-regime "
                "shift and substantial conformal under-coverage."
            ),
            (
                "Current retrospective future-track evaluation "
                "uses realized future ambient change and therefore "
                "does not constitute end-to-end weather-forecast validation."
            ),
            (
                "Mean solar elevation is a deterministic geometry proxy, "
                "not measured irradiance, cloud or shade exposure."
            ),
            (
                "Public historical data do not reliably identify "
                "queue waiting time or future attempt availability."
            ),
        ],

        "artifact_hashes_sha256":
            artifact_hashes,
    }

    with open(
        MANIFEST_FILE,
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            manifest,
            f,
            indent=2,
            ensure_ascii=False,
        )

    # Manifest hash itself
    manifest_hash = sha256_file(
        MANIFEST_FILE
    )

    # ========================================================
    # HUMAN-READABLE SUMMARY
    # ========================================================

    lines = []

    def add(x=""):
        lines.append(str(x))

    add("=" * 80)
    add(
        "INDY 500 V2-A FINAL FREEZE SUMMARY"
    )
    add("=" * 80)

    add()
    add("STATUS: FROZEN")

    add()
    add("CORE QUESTION")
    add(
        "If another on-track opportunity occurs h minutes from now, "
        "what distribution of four-lap performance change should be expected?"
    )

    add()
    add("FUTURE TRACK POINT MODEL")
    add(
        "Horizon-specific M2b_mean_solar"
    )
    add(
        "Inputs: delta ambient, current thermal gap, mean solar elevation"
    )
    add(
        "Rejected: current thermal rate, delta solar elevation"
    )

    add()
    add("UNCERTAINTY CALIBRATION")
    add(
        f"80% nominal -> {coverage80:.4f} observed"
    )
    add(
        f"90% nominal -> {coverage90:.4f} observed"
    )

    add()
    add("2022 LIMITATION")
    add(
        f"80% coverage: {coverage80_2022:.4f}"
    )
    add(
        f"90% coverage: {coverage90_2022:.4f}"
    )

    add()
    add("FINAL PERFORMANCE UNCERTAINTY WIDTH")
    add(
        width_by_horizon
        .round(4)
        .to_string(index=False)
    )

    add()
    add("SCENARIO OUTLOOK")
    add(
        final_table[
            [
                "scenario",
                "horizon_min",
                "expected_delta_track_c",
                "expected_delta_speed_mph",
                "p_improve",
                "lower_80_mph",
                "upper_80_mph",
            ]
        ]
        .round(4)
        .to_string(index=False)
    )

    add()
    add("INTERPRETATION")
    add(
        "h is a future-opportunity scenario axis, not a predicted queue wait."
    )
    add(
        "The model estimates physical performance conditional on "
        "another opportunity occurring."
    )
    add(
        "It does not recommend retain vs withdraw."
    )

    add()
    add("FREEZE MANIFEST")
    add(str(MANIFEST_FILE))
    add(
        f"SHA256: {manifest_hash}"
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
    print("=" * 80)
    print("FINAL ARTIFACTS")
    print("=" * 80)

    print(MANIFEST_FILE)
    print(FINAL_TABLE_FILE)
    print(FIGURE_FILE)
    print(SUMMARY_FILE)

    print()
    print("DONE — V2-A FROZEN")


if __name__ == "__main__":
    main()
