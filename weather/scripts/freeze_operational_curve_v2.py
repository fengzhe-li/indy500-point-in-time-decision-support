from pathlib import Path
import hashlib
import json
import pandas as pd

ROOT = Path("weather/output/operational_curve_v2")
FREEZE_DIR = ROOT / "freeze"
FREEZE_DIR.mkdir(parents=True, exist_ok=True)

CURVE = ROOT / "operational_performance_curve_v2.csv"
ANCHORS = ROOT / "operational_validated_anchors_v2.csv"
META = ROOT / "operational_curve_metadata_v2.json"
QA = ROOT / "operational_curve_qa_v2.csv"
ANCHOR_QA = ROOT / "operational_anchor_identity_qa_v2.csv"

PLOTS = [
    ROOT / "operational_expected_speed_change_v2.png",
    ROOT / "operational_probability_improvement_v2.png",
    ROOT / "operational_predictive_interval_v2.png",
]

MANIFEST_JSON = FREEZE_DIR / "operational_curve_v2_freeze_manifest.json"
HASH_CSV = FREEZE_DIR / "operational_curve_v2_hashes.csv"
FREEZE_QA_CSV = FREEZE_DIR / "operational_curve_v2_freeze_qa.csv"
SUMMARY_TXT = FREEZE_DIR / "operational_curve_v2_freeze_summary.txt"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def check(condition, name, detail):
    return {
        "check": name,
        "pass": bool(condition),
        "detail": str(detail),
    }


def main():
    required_files = [
        CURVE,
        ANCHORS,
        META,
        QA,
        ANCHOR_QA,
        *PLOTS,
    ]

    missing = [str(p) for p in required_files if not p.exists()]
    if missing:
        raise RuntimeError(
            "Missing required operational files:\n"
            + "\n".join(missing)
        )

    curve = pd.read_csv(CURVE)
    anchors = pd.read_csv(ANCHORS)
    qa = pd.read_csv(QA)
    anchor_qa = pd.read_csv(ANCHOR_QA)

    with open(META, "r", encoding="utf-8") as f:
        meta = json.load(f)

    expected_anchor_horizons = {15, 30, 60, 90, 120}
    expected_scenarios = {"cooling", "neutral", "warming"}

    qa_rows = []

    qa_rows.append(
        check(
            len(curve) == 321,
            "curve_row_count",
            f"{len(curve)} / 321",
        )
    )

    qa_rows.append(
        check(
            set(curve["scenario"]) == expected_scenarios,
            "scenario_set",
            sorted(set(curve["scenario"])),
        )
    )

    qa_rows.append(
        check(
            curve["horizon_min"].max() == 120,
            "max_horizon_120",
            curve["horizon_min"].max(),
        )
    )

    qa_rows.append(
        check(
            curve["horizon_min"].min() == 0,
            "min_horizon_0",
            curve["horizon_min"].min(),
        )
    )

    calibrated = curve[
        curve["support_status"] == "CALIBRATED_ANCHOR"
    ]

    qa_rows.append(
        check(
            set(calibrated["horizon_min"]) == expected_anchor_horizons,
            "calibrated_anchor_horizons",
            sorted(set(calibrated["horizon_min"])),
        )
    )

    qa_rows.append(
        check(
            len(calibrated) == 15,
            "calibrated_anchor_count",
            len(calibrated),
        )
    )

    interpolated = curve[
        curve["support_status"] == "INTERPOLATED_OPERATIONAL"
    ]

    qa_rows.append(
        check(
            not interpolated[
                "independently_calibrated_horizon"
            ].astype(bool).any(),
            "intermediate_not_independently_calibrated",
            int(
                interpolated[
                    "independently_calibrated_horizon"
                ].astype(bool).sum()
            ),
        )
    )

    zero_rows = curve[curve["horizon_min"] == 0]

    qa_rows.append(
        check(
            len(zero_rows) == 3,
            "zero_boundary_count",
            len(zero_rows),
        )
    )

    qa_rows.append(
        check(
            set(zero_rows["support_status"])
            == {"CURRENT_STATE_BOUNDARY"},
            "zero_boundary_status",
            sorted(set(zero_rows["support_status"])),
        )
    )

    qa_rows.append(
        check(
            not curve["extrapolated"].astype(bool).any(),
            "no_extrapolation",
            int(curve["extrapolated"].astype(bool).sum()),
        )
    )

    qa_rows.append(
        check(
            qa["pass"].astype(bool).all(),
            "upstream_curve_qa_all_pass",
            f"{int(qa['pass'].astype(bool).sum())}/{len(qa)}",
        )
    )

    qa_rows.append(
        check(
            anchor_qa["pass"].astype(bool).all(),
            "anchor_identity_qa_all_pass",
            f"{int(anchor_qa['pass'].astype(bool).sum())}/{len(anchor_qa)}",
        )
    )

    qa_rows.append(
        check(
            meta.get("queue_wait_prediction") is False,
            "queue_prediction_disabled",
            meta.get("queue_wait_prediction"),
        )
    )

    qa_rows.append(
        check(
            meta.get("best_wait_recommendation") is False,
            "best_wait_disabled",
            meta.get("best_wait_recommendation"),
        )
    )

    qa_rows.append(
        check(
            meta.get("strategy_recommendation") is False,
            "strategy_recommendation_disabled",
            meta.get("strategy_recommendation"),
        )
    )

    qa_df = pd.DataFrame(qa_rows)
    qa_df.to_csv(FREEZE_QA_CSV, index=False)

    if not qa_df["pass"].all():
        print(qa_df.to_string(index=False))
        raise RuntimeError("Operational freeze QA failed.")

    hashed_files = required_files + [FREEZE_QA_CSV]

    hash_rows = []
    for p in hashed_files:
        hash_rows.append({
            "file": str(p),
            "sha256": sha256_file(p),
        })

    hash_df = pd.DataFrame(hash_rows)
    hash_df.to_csv(HASH_CSV, index=False)

    manifest = {
        "freeze_version": "OPERATIONAL_CURVE_V2",
        "status": "FROZEN",
        "role": (
            "Derived operational presentation layer over frozen FINAL_V2 outputs"
        ),
        "scientific_core_modified": False,
        "source": str(
            Path(
                "weather/output/v2_future_track/"
                "v2a_operational_scenario_outlook_v1.csv"
            )
        ),
        "validated_anchor_horizons_min": [15, 30, 60, 90, 120],
        "continuous_operational_range_min": [15, 120],
        "visualization_resolution_min": 1,
        "zero_minute_policy": (
            "CURRENT_STATE_BOUNDARY only; not an independently calibrated horizon"
        ),
        "intermediate_minute_policy": (
            "piecewise-linear operational interpolation between calibrated anchors"
        ),
        "above_120_policy": "unsupported and not generated",
        "queue_wait_prediction": False,
        "best_wait_recommendation": False,
        "strategy_recommendation": False,
        "supported_question": (
            "If another on-track opportunity occurs at h minutes from now, "
            "what physical-performance outlook is implied?"
        ),
        "unsupported_questions": [
            "When exactly will the next attempt become available?",
            "Will another attempt definitely occur?",
            "What is the optimal wait time?",
            "Should the team automatically withdraw the current result?",
        ],
        "scenarios": ["cooling", "neutral", "warming"],
        "curve_rows": int(len(curve)),
        "anchor_rows": int(len(anchors)),
        "qa_passed": int(qa_df["pass"].sum()),
        "qa_total": int(len(qa_df)),
        "artifact_hashes": {
            row["file"]: row["sha256"]
            for row in hash_rows
        },
    }

    with open(MANIFEST_JSON, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    manifest_hash = sha256_file(MANIFEST_JSON)

    summary = f"""
OPERATIONAL_CURVE_V2 FREEZE SUMMARY
================================================================================

STATUS
--------------------------------------------------------------------------------
OPERATIONAL_CURVE_V2_FROZEN

ROLE
--------------------------------------------------------------------------------
Derived operational presentation layer over frozen FINAL_V2 outputs.
No scientific model was refitted or modified.

SUPPORTED HORIZONS
--------------------------------------------------------------------------------
Validated/calibrated anchors:
15, 30, 60, 90, 120 minutes

Continuous operational visualization:
15–120 minutes at 1-minute resolution

0 minutes:
CURRENT_STATE_BOUNDARY only

>120 minutes:
NOT GENERATED / UNSUPPORTED

INTERPOLATION POLICY
--------------------------------------------------------------------------------
Intermediate minutes are piecewise-linear operational interpolation between
calibrated anchor horizons.

Intermediate values are NOT independently calibrated forecast horizons.

DECISION BOUNDARY
--------------------------------------------------------------------------------
Queue wait prediction: NO
Best-wait recommendation: NO
Automatic strategy recommendation: NO

Supported question:
"If another on-track opportunity occurs at h minutes from now,
what physical-performance outlook is implied?"

SCENARIOS
--------------------------------------------------------------------------------
cooling
neutral
warming

QA
--------------------------------------------------------------------------------
{int(qa_df["pass"].sum())} PASS | 0 FAIL

Curve rows: {len(curve)}
Anchor rows: {len(anchors)}

ANCHOR IDENTITY
--------------------------------------------------------------------------------
{int(anchor_qa["pass"].astype(bool).sum())}/{len(anchor_qa)} PASS

MANIFEST
--------------------------------------------------------------------------------
{MANIFEST_JSON}

MANIFEST SHA256
--------------------------------------------------------------------------------
{manifest_hash}

IMPORTANT
--------------------------------------------------------------------------------
This freeze does not alter FINAL_V2 scientific evidence, V2-A, V2-B, V2-C,
V2-D or V2-E. It freezes only the derived operational visualization layer.
""".strip()

    SUMMARY_TXT.write_text(summary + "\n", encoding="utf-8")

    print("=" * 92)
    print("OPERATIONAL_CURVE_V2 — FREEZE")
    print("=" * 92)

    print("\nQA")
    print(qa_df.to_string(index=False))

    print("\nHASHED ARTIFACTS")
    print(hash_df.to_string(index=False))

    print("\nMANIFEST SHA256")
    print(manifest_hash)

    print("\nOUTPUTS")
    print(FREEZE_QA_CSV)
    print(HASH_CSV)
    print(MANIFEST_JSON)
    print(SUMMARY_TXT)

    print("\nOPERATIONAL_CURVE_V2_FROZEN")


if __name__ == "__main__":
    main()
