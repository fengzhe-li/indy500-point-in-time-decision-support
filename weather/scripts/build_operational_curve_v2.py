from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# ============================================================
# PATHS
# ============================================================

SRC = Path(
    "weather/output/v2_future_track/"
    "v2a_operational_scenario_outlook_v1.csv"
)

OUTDIR = Path(
    "weather/output/operational_curve_v2"
)

OUTDIR.mkdir(parents=True, exist_ok=True)

OUT_CSV = OUTDIR / "operational_performance_curve_v2.csv"
OUT_ANCHORS = OUTDIR / "operational_validated_anchors_v2.csv"
OUT_META = OUTDIR / "operational_curve_metadata_v2.json"

OUT_SPEED_PLOT = OUTDIR / "operational_expected_speed_change_v2.png"
OUT_PROB_PLOT = OUTDIR / "operational_probability_improvement_v2.png"
OUT_PI_PLOT = OUTDIR / "operational_predictive_interval_v2.png"

# ============================================================
# CONTRACT
# ============================================================

ANCHORS = np.array(
    [15, 30, 60, 90, 120],
    dtype=float
)

SCENARIOS = [
    "cooling",
    "neutral",
    "warming",
]

INTERPOLATE_COLUMNS = [
    "future_ambient_c",
    "delta_ambient_c",
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
]

# ============================================================
# HELPERS
# ============================================================

def fail(msg):
    raise RuntimeError(msg)


def load_source():
    if not SRC.exists():
        fail(f"Source file not found: {SRC}")

    df = pd.read_csv(SRC)

    required = {
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
    }

    missing = sorted(required - set(df.columns))

    if missing:
        fail(
            "Missing required columns:\n"
            + "\n".join(missing)
        )

    return df


def validate_source(df):
    problems = []

    for scenario in SCENARIOS:
        sub = df[
            df["scenario"].astype(str).str.lower()
            == scenario
        ].copy()

        got = sorted(
            sub["horizon_min"]
            .astype(float)
            .unique()
            .tolist()
        )

        expected = ANCHORS.tolist()

        if got != expected:
            problems.append(
                f"{scenario}: horizons={got}, expected={expected}"
            )

        if len(sub) != len(ANCHORS):
            problems.append(
                f"{scenario}: rows={len(sub)}, expected=5"
            )

    if problems:
        fail(
            "SOURCE VALIDATION FAILED\n"
            + "\n".join(problems)
        )


def interp_values(anchor_x, anchor_y, grid_x):
    return np.interp(
        grid_x,
        anchor_x,
        anchor_y
    )


def build_scenario_curve(sub):
    sub = (
        sub
        .sort_values("horizon_min")
        .reset_index(drop=True)
    )

    scenario = str(
        sub.loc[0, "scenario"]
    )

    current_track = float(
        sub.loc[0, "current_track_c"]
    )

    current_ambient = float(
        sub.loc[0, "current_ambient_c"]
    )

    thermal_gap = float(
        sub.loc[0, "thermal_gap_0_c"]
    )

    n_mc = int(
        sub["n_mc"].median()
    )

    # --------------------------------------------------------
    # 15–120 minute operational grid
    # --------------------------------------------------------

    minute_grid = np.arange(
        15,
        121,
        1,
        dtype=float
    )

    out = pd.DataFrame({
        "scenario": scenario,
        "horizon_min": minute_grid.astype(int),
        "current_track_c": current_track,
        "current_ambient_c": current_ambient,
        "thermal_gap_0_c": thermal_gap,
        "n_mc_source": n_mc,
    })

    x_anchor = (
        sub["horizon_min"]
        .astype(float)
        .to_numpy()
    )

    for col in INTERPOLATE_COLUMNS:
        y_anchor = (
            sub[col]
            .astype(float)
            .to_numpy()
        )

        out[col] = interp_values(
            x_anchor,
            y_anchor,
            minute_grid
        )

    out["support_status"] = np.where(
        out["horizon_min"].isin(
            ANCHORS.astype(int)
        ),
        "CALIBRATED_ANCHOR",
        "INTERPOLATED_OPERATIONAL",
    )

    out[
        "independently_calibrated_horizon"
    ] = out["horizon_min"].isin(
        ANCHORS.astype(int)
    )

    out["extrapolated"] = False

    # --------------------------------------------------------
    # h = 0 current-state boundary
    #
    # Important:
    # This is NOT a calibrated predictive horizon.
    # We set deterministic physical change to zero,
    # but do NOT fabricate predictive intervals or P(improve).
    # --------------------------------------------------------

    zero = {
        c: np.nan
        for c in out.columns
    }

    zero.update({
        "scenario": scenario,
        "horizon_min": 0,
        "current_track_c": current_track,
        "current_ambient_c": current_ambient,
        "thermal_gap_0_c": thermal_gap,
        "n_mc_source": n_mc,
        "future_ambient_c": current_ambient,
        "delta_ambient_c": 0.0,
        "expected_delta_track_c": 0.0,
        "expected_future_track_c": current_track,
        "expected_delta_speed_mph": 0.0,
        "median_delta_speed_mph": 0.0,
        "support_status": "CURRENT_STATE_BOUNDARY",
        "independently_calibrated_horizon": False,
        "extrapolated": False,
    })

    out = pd.concat(
        [
            pd.DataFrame([zero]),
            out,
        ],
        ignore_index=True
    )

    return out


def validate_curve(curve):
    qa = []

    expected_rows = (
        len(SCENARIOS)
        * 107
    )
    # 0 + 15..120 inclusive = 107 rows per scenario

    qa.append({
        "check": "row_count",
        "pass": len(curve) == expected_rows,
        "detail": f"{len(curve)} / {expected_rows}",
    })

    anchor_rows = curve[
        curve[
            "support_status"
        ] == "CALIBRATED_ANCHOR"
    ]

    qa.append({
        "check": "anchor_count",
        "pass": len(anchor_rows)
        == len(SCENARIOS) * 5,
        "detail": str(len(anchor_rows)),
    })

    intermediate_rows = curve[
        curve[
            "support_status"
        ] == "INTERPOLATED_OPERATIONAL"
    ]

    qa.append({
        "check": "no_intermediate_marked_calibrated",
        "pass": not intermediate_rows[
            "independently_calibrated_horizon"
        ].any(),
        "detail": str(
            intermediate_rows[
                "independently_calibrated_horizon"
            ].sum()
        ),
    })

    qa.append({
        "check": "no_extrapolation",
        "pass": not curve[
            "extrapolated"
        ].fillna(False).any(),
        "detail": "max horizon = "
        + str(
            int(
                curve["horizon_min"].max()
            )
        ),
    })

    probability_rows = curve[
        curve["horizon_min"] >= 15
    ]

    p_ok = (
        (
            probability_rows[
                "p_improve"
            ] >= 0
        )
        &
        (
            probability_rows[
                "p_improve"
            ] <= 1
        )
    ).all()

    qa.append({
        "check": "probability_bounds",
        "pass": bool(p_ok),
        "detail": "P(improve) within [0,1]",
    })

    interval_rows = curve[
        curve["horizon_min"] >= 15
    ].copy()

    order_ok = (
        (
            interval_rows[
                "lower_90_mph"
            ]
            <=
            interval_rows[
                "lower_80_mph"
            ]
        )
        &
        (
            interval_rows[
                "lower_80_mph"
            ]
            <=
            interval_rows[
                "upper_80_mph"
            ]
        )
        &
        (
            interval_rows[
                "upper_80_mph"
            ]
            <=
            interval_rows[
                "upper_90_mph"
            ]
        )
    ).all()

    qa.append({
        "check": "predictive_interval_order",
        "pass": bool(order_ok),
        "detail": "90-low <= 80-low <= 80-high <= 90-high",
    })

    qa_df = pd.DataFrame(qa)

    if not qa_df["pass"].all():
        print("\nQA FAILURE")
        print(
            qa_df.to_string(
                index=False
            )
        )
        fail(
            "Operational curve QA failed."
        )

    return qa_df


def verify_anchor_identity(source, curve):
    checks = []

    for scenario in SCENARIOS:
        src_sub = source[
            source["scenario"].str.lower()
            == scenario
        ]

        out_sub = curve[
            (
                curve["scenario"].str.lower()
                == scenario
            )
            &
            (
                curve["support_status"]
                == "CALIBRATED_ANCHOR"
            )
        ]

        for h in ANCHORS.astype(int):
            s = src_sub[
                src_sub["horizon_min"]
                == h
            ].iloc[0]

            o = out_sub[
                out_sub["horizon_min"]
                == h
            ].iloc[0]

            for col in [
                "expected_delta_speed_mph",
                "median_delta_speed_mph",
                "p_improve",
                "lower_80_mph",
                "upper_80_mph",
                "lower_90_mph",
                "upper_90_mph",
                "expected_delta_track_c",
            ]:
                ok = np.isclose(
                    float(s[col]),
                    float(o[col]),
                    rtol=0,
                    atol=1e-12
                )

                checks.append({
                    "scenario": scenario,
                    "horizon_min": h,
                    "field": col,
                    "pass": bool(ok),
                    "source_value": float(s[col]),
                    "curve_value": float(o[col]),
                })

    checks_df = pd.DataFrame(checks)

    if not checks_df["pass"].all():
        fail(
            "Anchor identity check failed."
        )

    return checks_df


def plot_expected_speed(curve):
    fig, ax = plt.subplots(
        figsize=(10, 6)
    )

    for scenario in SCENARIOS:
        sub = curve[
            (
                curve["scenario"]
                == scenario
            )
            &
            (
                curve["horizon_min"]
                >= 15
            )
        ]

        ax.plot(
            sub["horizon_min"],
            sub[
                "expected_delta_speed_mph"
            ],
            label=scenario.capitalize(),
        )

        anchors = sub[
            sub["support_status"]
            == "CALIBRATED_ANCHOR"
        ]

        ax.scatter(
            anchors["horizon_min"],
            anchors[
                "expected_delta_speed_mph"
            ],
            s=45,
            zorder=5,
        )

    ax.axhline(
        0,
        linewidth=1
    )

    ax.set_xlabel(
        "Future opportunity horizon h (minutes)"
    )

    ax.set_ylabel(
        "Expected four-lap speed change (mph)"
    )

    ax.set_title(
        "Operational Performance Outlook\n"
        "Markers = calibrated horizons; lines = interpolation"
    )

    ax.legend(
        title="Ambient scenario"
    )

    ax.grid(alpha=0.2)

    fig.tight_layout()

    fig.savefig(
        OUT_SPEED_PLOT,
        dpi=180
    )

    plt.close(fig)


def plot_probability(curve):
    fig, ax = plt.subplots(
        figsize=(10, 6)
    )

    for scenario in SCENARIOS:
        sub = curve[
            (
                curve["scenario"]
                == scenario
            )
            &
            (
                curve["horizon_min"]
                >= 15
            )
        ]

        ax.plot(
            sub["horizon_min"],
            sub["p_improve"],
            label=scenario.capitalize(),
        )

        anchors = sub[
            sub["support_status"]
            == "CALIBRATED_ANCHOR"
        ]

        ax.scatter(
            anchors["horizon_min"],
            anchors["p_improve"],
            s=45,
            zorder=5,
        )

    ax.axhline(
        0.5,
        linewidth=1
    )

    ax.set_ylim(
        0,
        1
    )

    ax.set_xlabel(
        "Future opportunity horizon h (minutes)"
    )

    ax.set_ylabel(
        "P(Δspeed > 0)"
    )

    ax.set_title(
        "Operational Probability of Improvement\n"
        "Markers = calibrated horizons; lines = interpolation"
    )

    ax.legend(
        title="Ambient scenario"
    )

    ax.grid(alpha=0.2)

    fig.tight_layout()

    fig.savefig(
        OUT_PROB_PLOT,
        dpi=180
    )

    plt.close(fig)


def plot_predictive_intervals(curve):
    # Neutral scenario only for interval plot,
    # to keep the figure readable.
    sub = curve[
        (
            curve["scenario"]
            == "neutral"
        )
        &
        (
            curve["horizon_min"]
            >= 15
        )
    ].copy()

    x = sub[
        "horizon_min"
    ].to_numpy()

    fig, ax = plt.subplots(
        figsize=(10, 6)
    )

    ax.fill_between(
        x,
        sub[
            "lower_90_mph"
        ].to_numpy(),
        sub[
            "upper_90_mph"
        ].to_numpy(),
        alpha=0.15,
        label="90% predictive interval",
    )

    ax.fill_between(
        x,
        sub[
            "lower_80_mph"
        ].to_numpy(),
        sub[
            "upper_80_mph"
        ].to_numpy(),
        alpha=0.25,
        label="80% predictive interval",
    )

    ax.plot(
        x,
        sub[
            "expected_delta_speed_mph"
        ].to_numpy(),
        linewidth=1.8,
        label="Expected speed change",
    )

    anchors = sub[
        sub["support_status"]
        == "CALIBRATED_ANCHOR"
    ]

    ax.scatter(
        anchors[
            "horizon_min"
        ],
        anchors[
            "expected_delta_speed_mph"
        ],
        s=45,
        zorder=5,
        label="Calibrated anchors",
    )

    ax.axhline(
        0,
        linewidth=1
    )

    ax.set_xlabel(
        "Future opportunity horizon h (minutes)"
    )

    ax.set_ylabel(
        "Four-lap speed change (mph)"
    )

    ax.set_title(
        "Neutral Scenario Predictive Outlook\n"
        "Continuous bands are interpolated between calibrated horizons"
    )

    ax.legend()

    ax.grid(alpha=0.2)

    fig.tight_layout()

    fig.savefig(
        OUT_PI_PLOT,
        dpi=180
    )

    plt.close(fig)


def main():
    print("=" * 90)
    print(
        "OPERATIONAL CURVE V2 — "
        "FINAL_V2 DERIVED PRESENTATION LAYER"
    )
    print("=" * 90)

    source = load_source()

    validate_source(
        source
    )

    print(
        "\nSOURCE VALIDATION: PASS"
    )

    pieces = []

    for scenario in SCENARIOS:
        sub = source[
            source[
                "scenario"
            ].str.lower()
            == scenario
        ].copy()

        pieces.append(
            build_scenario_curve(
                sub
            )
        )

    curve = pd.concat(
        pieces,
        ignore_index=True
    )

    curve = curve[
        [
            "scenario",
            "horizon_min",
            "support_status",
            "independently_calibrated_horizon",
            "extrapolated",
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
            "n_mc_source",
        ]
    ]

    qa = validate_curve(
        curve
    )

    identity = verify_anchor_identity(
        source,
        curve
    )

    anchors = curve[
        curve[
            "support_status"
        ]
        == "CALIBRATED_ANCHOR"
    ].copy()

    curve.to_csv(
        OUT_CSV,
        index=False
    )

    anchors.to_csv(
        OUT_ANCHORS,
        index=False
    )

    qa.to_csv(
        OUTDIR
        / "operational_curve_qa_v2.csv",
        index=False
    )

    identity.to_csv(
        OUTDIR
        / "operational_anchor_identity_qa_v2.csv",
        index=False
    )

    metadata = {
        "version": "operational_curve_v2",
        "source_file": str(SRC),
        "scientific_status": (
            "derived presentation layer; "
            "does not modify frozen FINAL_V2 models"
        ),
        "validated_anchor_horizons_min": [
            15,
            30,
            60,
            90,
            120,
        ],
        "continuous_visualization_range_min": [
            15,
            120,
        ],
        "visualization_resolution_min": 1,
        "zero_minute_status": (
            "current-state conceptual boundary only"
        ),
        "intermediate_horizon_status": (
            "piecewise-linear operational interpolation; "
            "not independently calibrated"
        ),
        "extrapolation_above_120": False,
        "queue_wait_prediction": False,
        "best_wait_recommendation": False,
        "strategy_recommendation": False,
        "supported_question": (
            "If another on-track opportunity occurs at h, "
            "what physical-performance outlook is implied?"
        ),
        "important_boundary": (
            "The curve conditions on opportunity time h. "
            "It does not predict when another attempt will occur "
            "or whether another attempt will occur."
        ),
    }

    with open(
        OUT_META,
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            metadata,
            f,
            indent=2
        )

    plot_expected_speed(
        curve
    )

    plot_probability(
        curve
    )

    plot_predictive_intervals(
        curve
    )

    print(
        "\nQA"
    )

    print(
        qa.to_string(
            index=False
        )
    )

    print(
        "\nANCHOR IDENTITY QA"
    )

    print(
        "PASS:",
        int(
            identity["pass"].sum()
        ),
        "/",
        len(identity)
    )

    print(
        "\nROW COUNTS"
    )

    for scenario in SCENARIOS:
        sub = curve[
            curve[
                "scenario"
            ]
            == scenario
        ]

        print(
            f"{scenario:10s}",
            len(sub),
            "rows"
        )

    print(
        "\nCALIBRATED ANCHORS"
    )

    print(
        anchors[
            [
                "scenario",
                "horizon_min",
                "expected_delta_speed_mph",
                "p_improve",
                "lower_80_mph",
                "upper_80_mph",
                "lower_90_mph",
                "upper_90_mph",
            ]
        ].to_string(
            index=False
        )
    )

    print(
        "\nOUTPUTS"
    )

    for p in [
        OUT_CSV,
        OUT_ANCHORS,
        OUT_META,
        OUTDIR
        / "operational_curve_qa_v2.csv",
        OUTDIR
        / "operational_anchor_identity_qa_v2.csv",
        OUT_SPEED_PLOT,
        OUT_PROB_PLOT,
        OUT_PI_PLOT,
    ]:
        print(p)

    print(
        "\nPOLICY"
    )

    print(
        "0 min             -> CURRENT_STATE_BOUNDARY"
    )

    print(
        "15/30/60/90/120   -> CALIBRATED_ANCHOR"
    )

    print(
        "other 15–120 min   -> INTERPOLATED_OPERATIONAL"
    )

    print(
        ">120 min           -> NOT GENERATED"
    )

    print(
        "best wait          -> NOT COMPUTED"
    )

    print(
        "queue prediction   -> NOT COMPUTED"
    )

    print(
        "\nSTATUS: OPERATIONAL_CURVE_V2_CREATED"
    )


if __name__ == "__main__":
    main()
