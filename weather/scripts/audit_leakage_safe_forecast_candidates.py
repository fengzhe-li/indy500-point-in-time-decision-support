from pathlib import Path
import pandas as pd
import numpy as np


SNAPSHOTS_FILE = Path(
    "data/canonical/v1/forecast_snapshots.csv"
)

POLICY_FILE = Path(
    "weather/output/hrrr_forecast_availability_policy.csv"
)

PERF_2020_2023_FILE = Path(
    "weather/output/performance_grade_attempt_timing.csv"
)

PERF_2024_FILE = Path(
    "weather/output/performance_grade_attempt_timing_2024_supported.csv"
)

OUTPUT_FILE = Path(
    "weather/output/"
    "hrrr_leakage_safe_forecast_candidate_audit.csv"
)

SUMMARY_FILE = Path(
    "weather/output/"
    "hrrr_leakage_safe_forecast_candidate_audit_summary.csv"
)


LAGS = [60, 90, 120]

PRIMARY_LAG = 90


def parse_utc(series):
    return pd.to_datetime(
        series,
        utc=True,
        errors="coerce",
    )


def load_required(path):
    if not path.exists():
        raise FileNotFoundError(
            f"Missing required file: {path}"
        )

    return pd.read_csv(
        path,
        low_memory=False,
    )


def build_timing():
    old = load_required(
        PERF_2020_2023_FILE
    )

    new = load_required(
        PERF_2024_FILE
    )

    old = old.copy()
    new = new.copy()

    old[
        "performance_timing_source"
    ] = "PERFORMANCE_GRADE_2020_2021_2023"

    new[
        "performance_timing_source"
    ] = "PERFORMANCE_GRADE_2024_SUPPORTED"

    combined = pd.concat(
        [
            old,
            new,
        ],
        ignore_index=True,
        sort=False,
    )

    if len(combined) != 136:
        raise RuntimeError(
            f"Expected 136 performance timing rows, "
            f"got {len(combined)}"
        )

    if combined[
        "attempt_id"
    ].duplicated().any():
        raise RuntimeError(
            "Duplicate attempt_id in combined timing."
        )

    combined[
        "_decision_time"
    ] = parse_utc(
        combined[
            "mapped_capture_time_utc"
        ]
    )

    if combined[
        "_decision_time"
    ].isna().any():
        raise RuntimeError(
            "Unparseable mapped_capture_time_utc."
        )

    return combined


def build_snapshots():
    snapshots = load_required(
        SNAPSHOTS_FILE
    )

    policy = load_required(
        POLICY_FILE
    )

    if len(snapshots) != 259:
        raise RuntimeError(
            f"Expected 259 forecast snapshots, "
            f"got {len(snapshots)}"
        )

    if len(policy) != 259:
        raise RuntimeError(
            f"Expected 259 policy rows, "
            f"got {len(policy)}"
        )

    keep_policy = [
        "forecast_snapshot_id",
        "availability_policy_id",
        "availability_policy_hash",
    ]

    missing_policy = [
        c
        for c in keep_policy
        if c not in policy.columns
    ]

    if missing_policy:
        raise RuntimeError(
            "Missing policy columns: "
            + ", ".join(
                missing_policy
            )
        )

    merged = snapshots.merge(
        policy[
            keep_policy
        ],
        on="forecast_snapshot_id",
        how="left",
        validate="one_to_one",
    )

    if merged[
        "availability_policy_id"
    ].isna().any():
        raise RuntimeError(
            "Snapshot without availability policy."
        )

    merged[
        "_issue_time"
    ] = parse_utc(
        merged[
            "issue_time_utc"
        ]
    )

    merged[
        "_valid_time"
    ] = parse_utc(
        merged[
            "valid_start_utc"
        ]
    )

    if merged[
        "_issue_time"
    ].isna().any():
        raise RuntimeError(
            "Unparseable issue_time_utc."
        )

    if merged[
        "_valid_time"
    ].isna().any():
        raise RuntimeError(
            "Unparseable valid_start_utc."
        )

    return merged


def analyze_one(
    timing_row,
    snapshots,
    lag_minutes,
):
    session_id = timing_row[
        "session_id"
    ]

    target = timing_row[
        "_decision_time"
    ]

    s = snapshots[
        snapshots[
            "session_id"
        ].astype(str)
        == str(session_id)
    ].copy()

    s[
        "_policy_available"
    ] = (
        s[
            "_issue_time"
        ]
        + pd.to_timedelta(
            lag_minutes,
            unit="m",
        )
    )

    eligible = s[
        s[
            "_policy_available"
        ]
        <= target
    ].copy()

    base = {
        "attempt_id":
            timing_row[
                "attempt_id"
            ],
        "session_id":
            session_id,
        "car_number":
            timing_row.get(
                "car_number",
                np.nan,
            ),
        "driver_name":
            timing_row.get(
                "driver_name",
                np.nan,
            ),
        "car_attempt_index":
            timing_row.get(
                "car_attempt_index",
                np.nan,
            ),
        "performance_time_utc":
            target.strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            ),
        "availability_lag_minutes":
            lag_minutes,
        "eligible_snapshot_count":
            len(eligible),
    }

    if eligible.empty:
        base.update(
            {
                "has_any_eligible_snapshot":
                    False,
                "nearest_snapshot_id":
                    None,
                "nearest_issue_time_utc":
                    None,
                "nearest_valid_time_utc":
                    None,
                "nearest_forecast_lead_hours":
                    np.nan,
                "nearest_valid_offset_minutes":
                    np.nan,
                "nearest_valid_relation":
                    "NO_ELIGIBLE_SNAPSHOT",
                "latest_available_issue_time_utc":
                    None,
                "latest_available_issue_age_minutes":
                    np.nan,
                "same_cycle_bracket_available":
                    False,
                "same_cycle_before_snapshot_id":
                    None,
                "same_cycle_after_snapshot_id":
                    None,
                "same_cycle_before_valid_offset_minutes":
                    np.nan,
                "same_cycle_after_valid_offset_minutes":
                    np.nan,
            }
        )

        return base

    eligible[
        "_valid_offset_minutes"
    ] = (
        eligible[
            "_valid_time"
        ]
        - target
    ).dt.total_seconds() / 60.0

    eligible[
        "_abs_valid_offset_minutes"
    ] = eligible[
        "_valid_offset_minutes"
    ].abs()

    nearest = (
        eligible
        .sort_values(
            [
                "_abs_valid_offset_minutes",
                "_issue_time",
                "forecast_lead_hours",
            ],
            ascending=[
                True,
                False,
                True,
            ],
        )
        .iloc[0]
    )

    offset = float(
        nearest[
            "_valid_offset_minutes"
        ]
    )

    if abs(
        offset
    ) < 1e-9:
        relation = (
            "EXACT_VALID_TIME"
        )
    elif offset < 0:
        relation = (
            "VALID_TIME_BEFORE_TARGET"
        )
    else:
        relation = (
            "VALID_TIME_AFTER_TARGET"
        )

    latest_issue = (
        eligible[
            "_issue_time"
        ].max()
    )

    latest_issue_age = (
        target
        - latest_issue
    ).total_seconds() / 60.0

    # --------------------------------------------------------
    # Same-cycle bracket test
    #
    # Restrict to the latest issue cycle that is already
    # available under the requested lag.
    # --------------------------------------------------------

    latest_cycle = eligible[
        eligible[
            "_issue_time"
        ]
        == latest_issue
    ].copy()

    before = latest_cycle[
        latest_cycle[
            "_valid_time"
        ]
        <= target
    ].copy()

    after = latest_cycle[
        latest_cycle[
            "_valid_time"
        ]
        >= target
    ].copy()

    bracket_available = (
        not before.empty
        and not after.empty
    )

    before_id = None
    after_id = None
    before_offset = np.nan
    after_offset = np.nan

    if bracket_available:
        b = (
            before
            .sort_values(
                "_valid_time"
            )
            .iloc[-1]
        )

        a = (
            after
            .sort_values(
                "_valid_time"
            )
            .iloc[0]
        )

        before_id = b[
            "forecast_snapshot_id"
        ]

        after_id = a[
            "forecast_snapshot_id"
        ]

        before_offset = (
            b[
                "_valid_time"
            ]
            - target
        ).total_seconds() / 60.0

        after_offset = (
            a[
                "_valid_time"
            ]
            - target
        ).total_seconds() / 60.0

    base.update(
        {
            "has_any_eligible_snapshot":
                True,

            "nearest_snapshot_id":
                nearest[
                    "forecast_snapshot_id"
                ],

            "nearest_issue_time_utc":
                nearest[
                    "_issue_time"
                ].strftime(
                    "%Y-%m-%dT%H:%M:%SZ"
                ),

            "nearest_valid_time_utc":
                nearest[
                    "_valid_time"
                ].strftime(
                    "%Y-%m-%dT%H:%M:%SZ"
                ),

            "nearest_forecast_lead_hours":
                nearest[
                    "forecast_lead_hours"
                ],

            "nearest_valid_offset_minutes":
                offset,

            "nearest_valid_relation":
                relation,

            "latest_available_issue_time_utc":
                latest_issue.strftime(
                    "%Y-%m-%dT%H:%M:%SZ"
                ),

            "latest_available_issue_age_minutes":
                latest_issue_age,

            "same_cycle_bracket_available":
                bracket_available,

            "same_cycle_before_snapshot_id":
                before_id,

            "same_cycle_after_snapshot_id":
                after_id,

            "same_cycle_before_valid_offset_minutes":
                before_offset,

            "same_cycle_after_valid_offset_minutes":
                after_offset,
        }
    )

    return base


def main():

    timing = build_timing()
    snapshots = build_snapshots()

    print()
    print("=" * 100)
    print(
        "PHASE 4C-2 — LEAKAGE-SAFE "
        "FORECAST CANDIDATE AUDIT"
    )
    print("=" * 100)

    print()
    print(
        "Performance-time candidates:",
        len(timing)
    )

    print(
        "Forecast snapshots:",
        len(snapshots)
    )

    rows = []

    for lag in LAGS:

        for _, timing_row in (
            timing.iterrows()
        ):

            rows.append(
                analyze_one(
                    timing_row,
                    snapshots,
                    lag,
                )
            )

    audit = pd.DataFrame(
        rows
    )

    expected_rows = (
        len(timing)
        * len(LAGS)
    )

    if len(audit) != expected_rows:
        raise RuntimeError(
            f"Expected {expected_rows} audit rows, "
            f"got {len(audit)}"
        )

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    summary_rows = []

    for lag in LAGS:

        g = audit[
            audit[
                "availability_lag_minutes"
            ]
            == lag
        ].copy()

        eligible = g[
            g[
                "has_any_eligible_snapshot"
            ]
        ].copy()

        offsets = pd.to_numeric(
            eligible[
                "nearest_valid_offset_minutes"
            ],
            errors="coerce",
        )

        summary_rows.append(
            {
                "availability_lag_minutes":
                    lag,

                "decision_rows":
                    len(g),

                "rows_with_any_eligible_snapshot":
                    int(
                        g[
                            "has_any_eligible_snapshot"
                        ].sum()
                    ),

                "coverage_pct":
                    (
                        g[
                            "has_any_eligible_snapshot"
                        ].mean()
                        * 100.0
                    ),

                "same_cycle_bracket_rows":
                    int(
                        g[
                            "same_cycle_bracket_available"
                        ].sum()
                    ),

                "same_cycle_bracket_pct":
                    (
                        g[
                            "same_cycle_bracket_available"
                        ].mean()
                        * 100.0
                    ),

                "nearest_exact_valid_rows":
                    int(
                        (
                            g[
                                "nearest_valid_relation"
                            ]
                            == "EXACT_VALID_TIME"
                        ).sum()
                    ),

                "nearest_before_rows":
                    int(
                        (
                            g[
                                "nearest_valid_relation"
                            ]
                            == "VALID_TIME_BEFORE_TARGET"
                        ).sum()
                    ),

                "nearest_after_rows":
                    int(
                        (
                            g[
                                "nearest_valid_relation"
                            ]
                            == "VALID_TIME_AFTER_TARGET"
                        ).sum()
                    ),

                "nearest_abs_offset_median_minutes":
                    (
                        float(
                            offsets.abs().median()
                        )
                        if not offsets.empty
                        else np.nan
                    ),

                "nearest_abs_offset_max_minutes":
                    (
                        float(
                            offsets.abs().max()
                        )
                        if not offsets.empty
                        else np.nan
                    ),
            }
        )

    summary = pd.DataFrame(
        summary_rows
    )

    # --------------------------------------------------------
    # Primary-lag detailed diagnostics
    # --------------------------------------------------------

    primary = audit[
        audit[
            "availability_lag_minutes"
        ]
        == PRIMARY_LAG
    ].copy()

    print()
    print("SUMMARY BY AVAILABILITY LAG")
    print("-" * 100)

    print(
        summary.to_string(
            index=False
        )
    )

    print()
    print(
        f"PRIMARY POLICY ({PRIMARY_LAG} MIN) "
        "BY SESSION"
    )
    print("-" * 100)

    session_summary = (
        primary
        .groupby(
            "session_id",
            dropna=False,
        )
        .agg(
            decision_rows=(
                "attempt_id",
                "size",
            ),

            eligible_rows=(
                "has_any_eligible_snapshot",
                "sum",
            ),

            bracket_rows=(
                "same_cycle_bracket_available",
                "sum",
            ),
        )
        .reset_index()
    )

    session_summary[
        "eligible_pct"
    ] = (
        session_summary[
            "eligible_rows"
        ]
        / session_summary[
            "decision_rows"
        ]
        * 100.0
    )

    session_summary[
        "bracket_pct"
    ] = (
        session_summary[
            "bracket_rows"
        ]
        / session_summary[
            "decision_rows"
        ]
        * 100.0
    )

    print(
        session_summary.to_string(
            index=False
        )
    )

    print()
    print(
        "PRIMARY POLICY — NEAREST VALID RELATION"
    )
    print("-" * 70)

    print(
        primary[
            "nearest_valid_relation"
        ]
        .value_counts(
            dropna=False
        )
        .to_string()
    )

    print()
    print(
        "PRIMARY POLICY — VALID OFFSET SUMMARY"
    )
    print("-" * 70)

    valid_offsets = pd.to_numeric(
        primary[
            "nearest_valid_offset_minutes"
        ],
        errors="coerce",
    ).dropna()

    if valid_offsets.empty:
        print(
            "No eligible offsets."
        )
    else:
        print(
            valid_offsets.describe().to_string()
        )

        print()
        print(
            "Absolute offset:"
        )

        print(
            valid_offsets
            .abs()
            .describe()
            .to_string()
        )

    print()
    print(
        "PRIMARY POLICY — SAME-CYCLE BRACKET"
    )
    print("-" * 70)

    print(
        primary[
            "same_cycle_bracket_available"
        ]
        .value_counts(
            dropna=False
        )
        .to_string()
    )

    no_eligible = primary[
        ~primary[
            "has_any_eligible_snapshot"
        ]
    ].copy()

    if not no_eligible.empty:

        print()
        print(
            "PRIMARY POLICY — NO ELIGIBLE SNAPSHOT ROWS"
        )
        print("-" * 100)

        print(
            no_eligible[
                [
                    "session_id",
                    "car_number",
                    "driver_name",
                    "car_attempt_index",
                    "performance_time_utc",
                ]
            ]
            .to_string(
                index=False
            )
        )

    print()
    print(
        "PRIMARY POLICY — SAMPLE CANDIDATES"
    )
    print("-" * 120)

    print(
        primary[
            [
                "session_id",
                "car_number",
                "driver_name",
                "car_attempt_index",
                "performance_time_utc",
                "eligible_snapshot_count",
                "nearest_issue_time_utc",
                "nearest_valid_time_utc",
                "nearest_forecast_lead_hours",
                "nearest_valid_offset_minutes",
                "nearest_valid_relation",
                "latest_available_issue_age_minutes",
                "same_cycle_bracket_available",
            ]
        ]
        .head(30)
        .to_string(
            index=False
        )
    )

    # --------------------------------------------------------
    # QA
    # --------------------------------------------------------

    print()
    print("QA")
    print("-" * 100)

    checks = {
        "audit_rows_equal_136_x_3":
            len(audit) == 408,

        "primary_rows_equal_136":
            len(primary) == 136,

        "all_primary_decision_times_nonnull":
            primary[
                "performance_time_utc"
            ].notna().all(),

        "primary_lag_present":
            (
                primary[
                    "availability_lag_minutes"
                ]
                == 90
            ).all(),
    }

    all_pass = True

    for name, passed in (
        checks.items()
    ):

        status = (
            "PASS"
            if passed
            else "FAIL"
        )

        print(
            f"{status:4}  {name}"
        )

        if not passed:
            all_pass = False

    # --------------------------------------------------------
    # Output
    # --------------------------------------------------------

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    audit.to_csv(
        OUTPUT_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    summary.to_csv(
        SUMMARY_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    print()
    print("=" * 100)

    if all_pass:
        print(
            "FINAL STATUS: "
            "FORECAST_CANDIDATE_AUDIT_READY"
        )
    else:
        print(
            "FINAL STATUS: REVIEW_REQUIRED"
        )

    print("=" * 100)

    print()
    print(
        "NO FINAL FORECAST SELECTION WAS MATERIALIZED."
    )

    print()
    print("OUTPUTS")

    print(
        OUTPUT_FILE
    )

    print(
        SUMMARY_FILE
    )


if __name__ == "__main__":
    main()
