from pathlib import Path
import hashlib
import json
import pandas as pd


# ============================================================
# INPUT / OUTPUT
# ============================================================

SNAPSHOTS_FILE = Path(
    "data/canonical/v1/forecast_snapshots.csv"
)

OUTPUT_FILE = Path(
    "weather/output/"
    "hrrr_forecast_availability_policy.csv"
)

QA_FILE = Path(
    "weather/output/"
    "hrrr_forecast_availability_policy_qa.csv"
)

REPORT_FILE = Path(
    "weather/output/"
    "hrrr_forecast_availability_policy.md"
)


# ============================================================
# FROZEN POLICY
# ============================================================

PRIMARY_LAG_MINUTES = 90

SENSITIVITY_LAGS_MINUTES = [
    60,
    90,
    120,
]

POLICY_ID = (
    "HRRR_CONSERVATIVE_FIXED_LAG_V1"
)

POLICY_CLASS = (
    "POLICY_CONSERVATIVE_FIXED_LAG"
)

AVAILABILITY_TIME_QUALITY = (
    "POLICY_DERIVED_CONSERVATIVE"
)

AVAILABILITY_OBSERVED = False

LEAKAGE_SAFE_FOR_PRIMARY_ANALYSIS = True


# ============================================================
# HELPERS
# ============================================================

def sha256_text(value):
    return hashlib.sha256(
        value.encode("utf-8")
    ).hexdigest()


def parse_utc(series):
    return pd.to_datetime(
        series,
        utc=True,
        errors="coerce",
    )


def iso_utc(series):
    return (
        series
        .dt.strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
    )


# ============================================================
# MAIN
# ============================================================

def main():

    if not SNAPSHOTS_FILE.exists():
        raise FileNotFoundError(
            f"Missing file: {SNAPSHOTS_FILE}"
        )

    snapshots = pd.read_csv(
        SNAPSHOTS_FILE,
        low_memory=False,
    )

    print()
    print("=" * 100)
    print(
        "PHASE 4C-1 — HRRR FORECAST "
        "AVAILABILITY POLICY MATERIALIZATION"
    )
    print("=" * 100)

    print()
    print(
        "Input snapshots:",
        len(snapshots)
    )

    # --------------------------------------------------------
    # Required schema
    # --------------------------------------------------------

    required = [
        "forecast_snapshot_id",
        "session_id",
        "issue_time_utc",
        "availability_time_utc",
        "availability_time_quality",
        "valid_start_utc",
        "valid_end_utc",
        "forecast_lead_hours",
    ]

    missing = [
        c
        for c in required
        if c not in snapshots.columns
    ]

    if missing:
        raise RuntimeError(
            "Missing required columns: "
            + ", ".join(missing)
        )

    if len(snapshots) != 259:
        raise RuntimeError(
            f"Expected 259 snapshots, got {len(snapshots)}"
        )

    if (
        snapshots[
            "forecast_snapshot_id"
        ]
        .duplicated()
        .any()
    ):
        raise RuntimeError(
            "Duplicate forecast_snapshot_id found."
        )

    # --------------------------------------------------------
    # Validate canonical availability remains unresolved
    # --------------------------------------------------------

    canonical_avail_nonnull = (
        snapshots[
            "availability_time_utc"
        ]
        .notna()
        .sum()
    )

    print()
    print(
        "Canonical availability_time_utc non-null:",
        f"{canonical_avail_nonnull}/{len(snapshots)}",
    )

    print(
        "Canonical availability_time_quality:"
    )

    print(
        snapshots[
            "availability_time_quality"
        ]
        .value_counts(
            dropna=False
        )
        .to_string()
    )

    if canonical_avail_nonnull != 0:
        raise RuntimeError(
            "Canonical availability timestamps are no longer "
            "fully unresolved. Review before applying policy."
        )

    unexpected_quality = (
        snapshots[
            "availability_time_quality"
        ]
        .dropna()
        .astype(str)
        .loc[
            lambda s:
            s != "UNKNOWN"
        ]
    )

    if not unexpected_quality.empty:
        raise RuntimeError(
            "Found non-UNKNOWN canonical availability quality. "
            "Review before applying policy."
        )

    # --------------------------------------------------------
    # Parse times
    # --------------------------------------------------------

    issue = parse_utc(
        snapshots[
            "issue_time_utc"
        ]
    )

    valid_start = parse_utc(
        snapshots[
            "valid_start_utc"
        ]
    )

    valid_end = parse_utc(
        snapshots[
            "valid_end_utc"
        ]
    )

    if issue.isna().any():
        raise RuntimeError(
            "Unparseable issue_time_utc found."
        )

    if valid_start.isna().any():
        raise RuntimeError(
            "Unparseable valid_start_utc found."
        )

    if valid_end.isna().any():
        raise RuntimeError(
            "Unparseable valid_end_utc found."
        )

    # --------------------------------------------------------
    # Materialize PRIMARY policy only
    # --------------------------------------------------------

    policy_availability = (
        issue
        + pd.to_timedelta(
            PRIMARY_LAG_MINUTES,
            unit="m",
        )
    )

    output = pd.DataFrame(
        {
            "forecast_snapshot_id":
                snapshots[
                    "forecast_snapshot_id"
                ],

            "session_id":
                snapshots[
                    "session_id"
                ],

            "issue_time_utc":
                iso_utc(
                    issue
                ),

            "forecast_lead_hours":
                snapshots[
                    "forecast_lead_hours"
                ],

            "valid_start_utc":
                iso_utc(
                    valid_start
                ),

            "valid_end_utc":
                iso_utc(
                    valid_end
                ),

            "policy_availability_time_utc":
                iso_utc(
                    policy_availability
                ),

            "availability_policy_id":
                POLICY_ID,

            "availability_policy_class":
                POLICY_CLASS,

            "availability_lag_minutes":
                PRIMARY_LAG_MINUTES,

            "availability_time_quality":
                AVAILABILITY_TIME_QUALITY,

            "availability_observed":
                AVAILABILITY_OBSERVED,

            "leakage_safe_for_primary_analysis":
                LEAKAGE_SAFE_FOR_PRIMARY_ANALYSIS,
        }
    )

    # --------------------------------------------------------
    # Explicit lineage / semantics
    # --------------------------------------------------------

    policy_definition = {
        "policy_id":
            POLICY_ID,

        "primary_lag_minutes":
            PRIMARY_LAG_MINUTES,

        "sensitivity_lags_minutes":
            SENSITIVITY_LAGS_MINUTES,

        "availability_expression":
            (
                "policy_availability_time_utc "
                "= issue_time_utc + 90 minutes"
            ),

        "semantics":
            (
                "Conservative modeling policy. "
                "Not an observed NOAA publication timestamp."
            ),

        "canonical_mutation":
            False,

        "forecast_selection_rule":
            (
                "A snapshot is eligible only when "
                "policy_availability_time_utc <= "
                "decision_state_time_utc."
            ),
    }

    policy_json = json.dumps(
        policy_definition,
        sort_keys=True,
        separators=(
            ",",
            ":",
        ),
    )

    policy_hash = sha256_text(
        policy_json
    )

    output[
        "availability_policy_hash"
    ] = policy_hash

    output[
        "policy_semantic_note"
    ] = (
        "Derived conservative availability envelope; "
        "does not claim historical observed publication time. "
        "Primary lag 90 min. Sensitivity analysis should test "
        "60 and 120 min."
    )

    # --------------------------------------------------------
    # QA
    # --------------------------------------------------------

    if len(output) != 259:
        raise RuntimeError(
            "Unexpected output row count."
        )

    if (
        output[
            "forecast_snapshot_id"
        ]
        .duplicated()
        .any()
    ):
        raise RuntimeError(
            "Duplicate snapshot in policy output."
        )

    if (
        output[
            "policy_availability_time_utc"
        ]
        .isna()
        .any()
    ):
        raise RuntimeError(
            "Missing policy availability time."
        )

    lag_check = (
        parse_utc(
            output[
                "policy_availability_time_utc"
            ]
        )
        - parse_utc(
            output[
                "issue_time_utc"
            ]
        )
    ).dt.total_seconds() / 60.0

    lag_mismatch = (
        (
            lag_check
            - PRIMARY_LAG_MINUTES
        )
        .abs()
        > 1e-9
    )

    if lag_mismatch.any():
        raise RuntimeError(
            "Availability lag invariant failed."
        )

    # Issue/lead consistency check:
    # valid_start should normally equal issue + lead.
    expected_valid = (
        issue
        + pd.to_timedelta(
            pd.to_numeric(
                snapshots[
                    "forecast_lead_hours"
                ],
                errors="coerce",
            ),
            unit="h",
        )
    )

    valid_delta_seconds = (
        valid_start
        - expected_valid
    ).dt.total_seconds().abs()

    lead_valid_consistent = (
        valid_delta_seconds
        .fillna(float("inf"))
        <= 1.0
    )

    # Policy time can be AFTER valid time for f00/f01.
    # That is allowed and intentional.
    availability_after_valid = (
        policy_availability
        > valid_start
    )

    qa_rows = [
        {
            "metric":
                "input_snapshots",
            "value":
                len(snapshots),
            "status":
                "PASS",
        },
        {
            "metric":
                "canonical_availability_nonnull",
            "value":
                int(
                    canonical_avail_nonnull
                ),
            "status":
                (
                    "PASS"
                    if canonical_avail_nonnull == 0
                    else "FAIL"
                ),
        },
        {
            "metric":
                "policy_availability_nonnull",
            "value":
                int(
                    output[
                        "policy_availability_time_utc"
                    ]
                    .notna()
                    .sum()
                ),
            "status":
                (
                    "PASS"
                    if output[
                        "policy_availability_time_utc"
                    ]
                    .notna()
                    .all()
                    else "FAIL"
                ),
        },
        {
            "metric":
                "fixed_lag_invariant_rows",
            "value":
                int(
                    (
                        ~lag_mismatch
                    ).sum()
                ),
            "status":
                (
                    "PASS"
                    if not lag_mismatch.any()
                    else "FAIL"
                ),
        },
        {
            "metric":
                "issue_plus_lead_matches_valid_start_rows",
            "value":
                int(
                    lead_valid_consistent.sum()
                ),
            "status":
                (
                    "PASS"
                    if lead_valid_consistent.all()
                    else "REVIEW"
                ),
        },
        {
            "metric":
                "availability_after_valid_start_rows",
            "value":
                int(
                    availability_after_valid.sum()
                ),
            "status":
                "INFO",
        },
        {
            "metric":
                "primary_lag_minutes",
            "value":
                PRIMARY_LAG_MINUTES,
            "status":
                "POLICY",
        },
    ]

    qa = pd.DataFrame(
        qa_rows
    )

    # --------------------------------------------------------
    # Coverage diagnostics by session / lead
    # --------------------------------------------------------

    print()
    print("POLICY")
    print("-" * 70)

    print(
        "Policy ID:",
        POLICY_ID,
    )

    print(
        "Primary lag:",
        f"{PRIMARY_LAG_MINUTES} minutes",
    )

    print(
        "Sensitivity lags:",
        SENSITIVITY_LAGS_MINUTES,
    )

    print(
        "Policy hash:",
        policy_hash,
    )

    print()
    print(
        "IMPORTANT: policy availability is NOT an "
        "observed historical publication timestamp."
    )

    print()
    print("ROWS BY SESSION")
    print("-" * 70)

    print(
        output[
            "session_id"
        ]
        .value_counts()
        .sort_index()
        .to_string()
    )

    print()
    print("ROWS BY FORECAST LEAD")
    print("-" * 70)

    print(
        output[
            "forecast_lead_hours"
        ]
        .value_counts()
        .sort_index()
        .to_string()
    )

    print()
    print("SAMPLE POLICY ROWS")
    print("-" * 100)

    print(
        output[
            [
                "session_id",
                "issue_time_utc",
                "forecast_lead_hours",
                "valid_start_utc",
                "policy_availability_time_utc",
                "availability_lag_minutes",
                "availability_time_quality",
            ]
        ]
        .head(20)
        .to_string(
            index=False
        )
    )

    print()
    print("QA")
    print("-" * 100)

    print(
        qa.to_string(
            index=False
        )
    )

    # --------------------------------------------------------
    # Write outputs
    # --------------------------------------------------------

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output.to_csv(
        OUTPUT_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    qa.to_csv(
        QA_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    report = []

    report.append(
        "# HRRR Forecast Availability Policy"
    )

    report.append("")

    report.append(
        f"Policy ID: `{POLICY_ID}`"
    )

    report.append("")

    report.append(
        "## Primary rule"
    )

    report.append("")

    report.append(
        f"`policy_availability_time_utc = "
        f"issue_time_utc + {PRIMARY_LAG_MINUTES} minutes`"
    )

    report.append("")

    report.append(
        "This is a conservative modeling policy, not an "
        "observed historical NOAA publication timestamp."
    )

    report.append("")

    report.append(
        "A forecast snapshot is eligible for a decision "
        "only when its policy availability time is less "
        "than or equal to the decision-state timestamp."
    )

    report.append("")

    report.append(
        "## Leakage policy"
    )

    report.append("")

    report.append(
        "- `issue_time_utc` alone must not be used as "
        "forecast availability."
    )

    report.append(
        "- Canonical `availability_time_utc` remains "
        "unchanged and unresolved."
    )

    report.append(
        "- The policy layer is derived and separate from "
        "canonical weather provenance."
    )

    report.append(
        "- Primary analysis uses a 90-minute conservative lag."
    )

    report.append(
        "- Sensitivity analysis should repeat forecast joins "
        "with 60-minute and 120-minute lags."
    )

    report.append("")

    report.append(
        "## Policy hash"
    )

    report.append("")

    report.append(
        f"`{policy_hash}`"
    )

    report.append("")

    report.append(
        "## Readiness"
    )

    report.append("")

    if (
        len(output) == 259
        and not lag_mismatch.any()
        and output[
            "policy_availability_time_utc"
        ].notna().all()
    ):

        report.append(
            "**READY_FOR_LEAKAGE_SAFE_FORECAST_SELECTION**"
        )

        ready = True

    else:

        report.append(
            "**REVIEW_REQUIRED**"
        )

        ready = False

    REPORT_FILE.write_text(
        "\n".join(
            report
        ),
        encoding="utf-8",
    )

    print()
    print("=" * 100)

    if ready:
        print(
            "FINAL STATUS: "
            "READY_FOR_LEAKAGE_SAFE_FORECAST_SELECTION"
        )
    else:
        print(
            "FINAL STATUS: REVIEW_REQUIRED"
        )

    print("=" * 100)

    print()
    print("OUTPUTS")

    print(
        OUTPUT_FILE
    )

    print(
        QA_FILE
    )

    print(
        REPORT_FILE
    )


if __name__ == "__main__":
    main()
