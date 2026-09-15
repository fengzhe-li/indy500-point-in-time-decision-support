from pathlib import Path
import hashlib
import json

import numpy as np
import pandas as pd


# ============================================================
# INPUTS
# ============================================================

ATTEMPTS_FILE = Path(
    "data/canonical/v1/attempts.csv"
)

PERFORMANCE_TIMING_FILE = Path(
    "weather/output/performance_grade_attempt_timing.csv"
)

PERFORMANCE_TIMING_2024_FILE = Path(
    "weather/output/performance_grade_attempt_timing_2024_supported.csv"
)

UNCERTAINTY_ROWS_FILE = Path(
    "weather/output/repeat_performance_uncertainty_rows_v1.csv"
)

QUEUE_EVIDENCE_FILE = Path(
    "weather/output/queue_wait_evidence_inventory_v1.csv"
)

RUN_DURATION_FILE = Path(
    "weather/output/queue_wait_run_duration_reference_v1.csv"
)

QUEUE_POLICY_FILE = Path(
    "weather/output/queue_wait_uncertainty_policy_v1.csv"
)

MC_RESULTS_FILE = Path(
    "weather/output/retain_withdraw_monte_carlo_scenario_results_v1.csv"
)

MC_DRAW_SUMMARY_FILE = Path(
    "weather/output/retain_withdraw_monte_carlo_draw_summary_v1.csv"
)

TARGET_COMPACT_FILE = Path(
    "weather/output/retain_withdraw_target_aware_compact_v1.csv"
)

LOYO_PROFILE_FILE = Path(
    "weather/output/target_aware_loyo_profiles_v1.csv"
)

ROBUSTNESS_ENVELOPE_FILE = Path(
    "weather/output/decision_robustness_envelope_v1.csv"
)

FINAL_PROFILE_FILE = Path(
    "weather/output/final_integrated_decision_profiles_v1.csv"
)

FINAL_METADATA_FILE = Path(
    "weather/output/final_integrated_decision_metadata_v1.csv"
)

FINAL_QA_FILE = Path(
    "weather/output/final_integrated_decision_output_v1_qa.csv"
)


# ============================================================
# OPTIONAL PHASE REPORT / QA INPUTS
# ============================================================

PHASE_QA_FILES = {
    "PHASE_5B5A":
        Path(
            "weather/output/"
            "repeat_performance_uncertainty_v1_qa.csv"
        ),

    "PHASE_6A":
        Path(
            "weather/output/"
            "queue_wait_uncertainty_design_v1_qa.csv"
        ),

    "PHASE_6B":
        Path(
            "weather/output/"
            "queue_wait_sensitivity_scenarios_v1_qa.csv"
        ),

    "PHASE_6C":
        Path(
            "weather/output/"
            "retain_withdraw_monte_carlo_v1_qa.csv"
        ),

    "PHASE_6D":
        Path(
            "weather/output/"
            "retain_withdraw_decision_semantics_v1_qa.csv"
        ),

    "PHASE_6E":
        Path(
            "weather/output/"
            "retain_withdraw_target_aware_profiles_v1_qa.csv"
        ),

    "PHASE_7A":
        Path(
            "weather/output/"
            "target_aware_cross_year_robustness_v1_qa.csv"
        ),

    "PHASE_7B":
        Path(
            "weather/output/"
            "decision_robustness_envelope_v1_qa.csv"
        ),

    "PHASE_8A":
        Path(
            "weather/output/"
            "final_integrated_decision_output_v1_qa.csv"
        ),
}


# ============================================================
# OUTPUTS
# ============================================================

GLOBAL_AUDIT_FILE = Path(
    "weather/output/"
    "global_pipeline_consistency_audit_v1.csv"
)

GLOBAL_HASH_FILE = Path(
    "weather/output/"
    "global_pipeline_policy_hash_inventory_v1.csv"
)

GLOBAL_PHASE_STATUS_FILE = Path(
    "weather/output/"
    "global_pipeline_phase_status_v1.csv"
)

GLOBAL_QA_FILE = Path(
    "weather/output/"
    "global_pipeline_consistency_v1_qa.csv"
)

GLOBAL_REPORT_FILE = Path(
    "weather/output/"
    "global_pipeline_consistency_v1.md"
)


# ============================================================
# EXPECTED INVARIANTS
# ============================================================

EXPECTED = {
    "canonical_attempts":
        329,

    "performance_timing_total":
        136,

    "repeat_uncertainty_rows":
        39,

    "normal_rows":
        35,

    "recovery_rows":
        4,

    "direct_queue_wait_pairs":
        0,

    "complete_run_duration_rows":
        260,

    "mc_scenarios":
        120,

    "draws_per_scenario":
        100000,

    "total_mc_draws":
        12000000,

    "target_compact_rows":
        480,

    "loyo_profile_rows":
        24,

    "robustness_envelope_rows":
        480,

    "final_profile_rows":
        480,
}


POLICY_VERSION = (
    "GLOBAL_PIPELINE_CONSISTENCY_AUDIT_V1"
)


# ============================================================
# HELPERS
# ============================================================

def read_required(path):

    if not path.exists():

        raise FileNotFoundError(
            f"Missing required file: {path}"
        )

    return pd.read_csv(
        path,
        low_memory=False,
    )


def read_optional(path):

    if not path.exists():
        return None

    return pd.read_csv(
        path,
        low_memory=False,
    )


def numeric(series):

    return pd.to_numeric(
        series,
        errors="coerce",
    )


def as_bool(series):

    return (
        series
        .astype(str)
        .str.strip()
        .str.lower()
        .isin(
            [
                "true",
                "1",
                "yes",
            ]
        )
    )


def stable_hash(payload):

    text = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )

    return hashlib.sha256(
        text.encode("utf-8")
    ).hexdigest()


def extract_policy_hashes(
    df,
    source_name,
):

    hash_columns = [
        col
        for col in df.columns
        if (
            "policy_hash"
            in col.lower()
            or
            col.lower()
            == "final_policy_hash"
        )
    ]

    rows = []

    for col in hash_columns:

        values = (
            df[
                col
            ]
            .dropna()
            .astype(str)
            .unique()
            .tolist()
        )

        for value in values:

            rows.append(
                {
                    "source_name":
                        source_name,

                    "hash_column":
                        col,

                    "policy_hash":
                        value,
                }
            )

    return rows


def qa_all_pass(
    df,
):

    if (
        "status"
        not in df.columns
    ):

        return False

    status = (
        df[
            "status"
        ]
        .astype(str)
        .str.upper()
    )

    hard_rows = df[
        status.isin(
            [
                "PASS",
                "FAIL",
            ]
        )
    ]

    if len(
        hard_rows
    ) == 0:

        return False

    return (
        hard_rows[
            "status"
        ]
        .astype(str)
        .str.upper()
        .eq(
            "PASS"
        )
        .all()
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 100)
    print(
        "PHASE 8B — GLOBAL PIPELINE "
        "CONSISTENCY / PROVENANCE AUDIT V1"
    )
    print("=" * 100)

    # ========================================================
    # Load required files
    # ========================================================

    attempts = read_required(
        ATTEMPTS_FILE
    )

    perf_a = read_required(
        PERFORMANCE_TIMING_FILE
    )

    perf_b = read_required(
        PERFORMANCE_TIMING_2024_FILE
    )

    uncertainty = read_required(
        UNCERTAINTY_ROWS_FILE
    )

    queue_evidence = read_required(
        QUEUE_EVIDENCE_FILE
    )

    run_duration = read_required(
        RUN_DURATION_FILE
    )

    queue_policy = read_required(
        QUEUE_POLICY_FILE
    )

    mc = read_required(
        MC_RESULTS_FILE
    )

    mc_draws = read_required(
        MC_DRAW_SUMMARY_FILE
    )

    target_compact = read_required(
        TARGET_COMPACT_FILE
    )

    loyo = read_required(
        LOYO_PROFILE_FILE
    )

    robustness = read_required(
        ROBUSTNESS_ENVELOPE_FILE
    )

    final_profiles = read_required(
        FINAL_PROFILE_FILE
    )

    final_metadata = read_required(
        FINAL_METADATA_FILE
    )

    final_qa = read_required(
        FINAL_QA_FILE
    )

    # ========================================================
    # Canonical attempts
    # ========================================================

    canonical_attempts = len(
        attempts
    )

    # ========================================================
    # Performance timing
    # ========================================================

    if (
        "attempt_id"
        not in perf_a.columns
        or
        "attempt_id"
        not in perf_b.columns
    ):

        raise RuntimeError(
            "attempt_id missing from performance timing."
        )

    perf_combined = pd.concat(
        [
            perf_a[
                [
                    "attempt_id"
                ]
            ],
            perf_b[
                [
                    "attempt_id"
                ]
            ],
        ],
        ignore_index=True,
    )

    performance_timing_total = (
        perf_combined[
            "attempt_id"
        ]
        .drop_duplicates()
        .shape[0]
    )

    # ========================================================
    # Repeat uncertainty
    # ========================================================

    if (
        "diagnostic_recovery_like"
        not in uncertainty.columns
    ):

        raise RuntimeError(
            "diagnostic_recovery_like missing."
        )

    uncertainty = uncertainty.copy()

    uncertainty[
        "_recovery"
    ] = as_bool(
        uncertainty[
            "diagnostic_recovery_like"
        ]
    )

    repeat_uncertainty_rows = len(
        uncertainty
    )

    normal_rows = int(
        (
            ~uncertainty[
                "_recovery"
            ]
        ).sum()
    )

    recovery_rows = int(
        uncertainty[
            "_recovery"
        ].sum()
    )

    # ========================================================
    # Queue direct-wait evidence
    # ========================================================

    direct_queue_wait_pairs = 0

    if (
        "usable_as_direct_queue_wait"
        in queue_evidence.columns
    ):

        direct_queue_wait_pairs = int(
            as_bool(
                queue_evidence[
                    "usable_as_direct_queue_wait"
                ]
            ).sum()
        )

    # ========================================================
    # Complete run duration rows
    # ========================================================

    all_run = run_duration[
        run_duration[
            "scope"
        ].astype(str)
        == "ALL_COMPLETE_FOUR_LAP_ATTEMPTS"
    ]

    if len(
        all_run
    ) != 1:

        raise RuntimeError(
            "Expected exactly one ALL_COMPLETE_FOUR_LAP_ATTEMPTS row."
        )

    complete_run_duration_rows = int(
        float(
            all_run.iloc[0][
                "rows"
            ]
        )
    )

    # ========================================================
    # Monte Carlo invariants
    # ========================================================

    mc_scenarios = len(
        mc
    )

    if (
        "monte_carlo_draws"
        not in mc.columns
    ):

        raise RuntimeError(
            "monte_carlo_draws missing from MC results."
        )

    unique_draw_counts = (
        numeric(
            mc[
                "monte_carlo_draws"
            ]
        )
        .dropna()
        .unique()
    )

    if len(
        unique_draw_counts
    ) != 1:

        raise RuntimeError(
            "Expected one draws-per-scenario value."
        )

    draws_per_scenario = int(
        unique_draw_counts[0]
    )

    total_mc_draws = int(
        mc_scenarios
        * draws_per_scenario
    )

    # ========================================================
    # Final row counts
    # ========================================================

    target_compact_rows = len(
        target_compact
    )

    loyo_profile_rows = len(
        loyo
    )

    robustness_envelope_rows = len(
        robustness
    )

    final_profile_rows = len(
        final_profiles
    )

    # ========================================================
    # Recommendation boundaries
    # ========================================================

    if (
        "recommendation_enabled"
        not in final_profiles.columns
    ):

        raise RuntimeError(
            "recommendation_enabled missing from final profiles."
        )

    if (
        "recommendation"
        not in final_profiles.columns
    ):

        raise RuntimeError(
            "recommendation missing from final profiles."
        )

    final_recommendation_enabled_count = int(
        as_bool(
            final_profiles[
                "recommendation_enabled"
            ]
        ).sum()
    )

    final_not_issued_count = int(
        (
            final_profiles[
                "recommendation"
            ]
            .astype(str)
            == "NOT_ISSUED"
        ).sum()
    )

    # ========================================================
    # Historical claim boundaries
    # ========================================================

    queue_wait_historical_claim_present = False

    claim_columns = [
        col
        for col in final_profiles.columns
        if "queue_wait" in col.lower()
    ]

    queue_wait_claim_diagnostic_rows = []

    for col in claim_columns:

        values = (
            final_profiles[
                col
            ]
            .astype(str)
            .str.upper()
        )

        positive_phrase = values.str.contains(
            "HISTORICAL_QUEUE_WAIT_ESTIMATE",
            na=False,
        )

        explicit_negation = (
            values.str.contains(
                "NOT_HISTORICAL_QUEUE_WAIT_ESTIMATE",
                na=False,
            )
            |
            values.str.contains(
                "NO_HISTORICAL_QUEUE_WAIT",
                na=False,
            )
        )

        positive_claim = (
            positive_phrase
            &
            ~explicit_negation
        )

        if positive_claim.any():

            queue_wait_historical_claim_present = True

            offending_values = (
                values[
                    positive_claim
                ]
                .drop_duplicates()
                .tolist()
            )

            for offending_value in offending_values:

                queue_wait_claim_diagnostic_rows.append(
                    {
                        "column":
                            col,

                        "value":
                            offending_value,
                    }
                )

    leaderboard_historical_claim_present = False

    leaderboard_columns = [
        col
        for col in final_profiles.columns
        if "leaderboard" in col.lower()
    ]

    for col in leaderboard_columns:

        values = (
            final_profiles[
                col
            ]
            .astype(str)
            .str.upper()
        )

        if (
            values.str.contains(
                "ASSUMED",
                na=False,
            ).any()
            and
            not values.str.contains(
                "NO_HISTORICAL_LEADERBOARD",
                na=False,
            ).all()
        ):

            leaderboard_historical_claim_present = True

    # ========================================================
    # Queue policy semantic checks
    # ========================================================

    queue_lookup = {
        str(row["component"]):
            str(row["status"])
        for _, row
        in queue_policy.iterrows()
    }

    queue_policy_direct_wait_unobserved = (
        queue_lookup.get(
            "DIRECT_QUEUE_WAIT"
        )
        == "UNOBSERVED"
    )

    queue_policy_position_unobserved = (
        queue_lookup.get(
            "QUEUE_POSITION"
        )
        == "UNOBSERVED"
    )

    queue_policy_2024_cutoff_exact = (
        queue_lookup.get(
            "SESSION_CUTOFF_2024"
        )
        == "EXACT_SUPPORTED"
    )

    # ========================================================
    # Final metadata consistency
    # ========================================================

    metadata_lookup = {
        str(row["metadata_key"]):
            str(row["metadata_value"])
        for _, row
        in final_metadata.iterrows()
    }

    metadata_profile_rows_match = (
        int(
            float(
                metadata_lookup[
                    "profile_rows"
                ]
            )
        )
        == final_profile_rows
    )

    metadata_normal_rows_match = (
        int(
            float(
                metadata_lookup[
                    "normal_empirical_rows"
                ]
            )
        )
        == normal_rows
    )

    metadata_recovery_rows_match = (
        int(
            float(
                metadata_lookup[
                    "recovery_like_empirical_rows"
                ]
            )
        )
        == recovery_rows
    )

    metadata_recommendation_disabled = (
        metadata_lookup[
            "recommendation_enabled"
        ].lower()
        == "false"
    )

    # ========================================================
    # Phase QA status audit
    # ========================================================

    phase_status_rows = []

    all_phase_qas_pass = True

    for phase_name, path in (
        PHASE_QA_FILES.items()
    ):

        if not path.exists():

            phase_status_rows.append(
                {
                    "phase":
                        phase_name,

                    "qa_file":
                        str(
                            path
                        ),

                    "file_exists":
                        False,

                    "all_hard_checks_pass":
                        False,
                }
            )

            all_phase_qas_pass = False
            continue

        qa_df = pd.read_csv(
            path,
            low_memory=False,
        )

        passed = qa_all_pass(
            qa_df
        )

        phase_status_rows.append(
            {
                "phase":
                    phase_name,

                "qa_file":
                    str(
                        path
                    ),

                "file_exists":
                    True,

                "all_hard_checks_pass":
                    passed,
            }
        )

        if not passed:

            all_phase_qas_pass = False

    phase_status = pd.DataFrame(
        phase_status_rows
    )

    # ========================================================
    # Policy hash inventory
    # ========================================================

    hash_rows = []

    hash_sources = {
        "UNCERTAINTY":
            uncertainty,

        "QUEUE_EVIDENCE":
            queue_evidence,

        "RUN_DURATION":
            run_duration,

        "QUEUE_POLICY":
            queue_policy,

        "MC":
            mc,

        "MC_DRAW_SUMMARY":
            mc_draws,

        "TARGET_COMPACT":
            target_compact,

        "LOYO":
            loyo,

        "ROBUSTNESS":
            robustness,

        "FINAL":
            final_profiles,
    }

    for source_name, frame in (
        hash_sources.items()
    ):

        hash_rows.extend(
            extract_policy_hashes(
                frame,
                source_name,
            )
        )

    hash_inventory = pd.DataFrame(
        hash_rows
    )

    all_required_sources_have_hash = True

    for source_name in hash_sources.keys():

        if (
            hash_inventory.empty
            or
            source_name
            not in set(
                hash_inventory[
                    "source_name"
                ].astype(str)
            )
        ):

            all_required_sources_have_hash = False
            break

    # ========================================================
    # Audit rows
    # ========================================================

    actuals = {
        "canonical_attempts":
            canonical_attempts,

        "performance_timing_total":
            performance_timing_total,

        "repeat_uncertainty_rows":
            repeat_uncertainty_rows,

        "normal_rows":
            normal_rows,

        "recovery_rows":
            recovery_rows,

        "direct_queue_wait_pairs":
            direct_queue_wait_pairs,

        "complete_run_duration_rows":
            complete_run_duration_rows,

        "mc_scenarios":
            mc_scenarios,

        "draws_per_scenario":
            draws_per_scenario,

        "total_mc_draws":
            total_mc_draws,

        "target_compact_rows":
            target_compact_rows,

        "loyo_profile_rows":
            loyo_profile_rows,

        "robustness_envelope_rows":
            robustness_envelope_rows,

        "final_profile_rows":
            final_profile_rows,
    }

    audit_rows = []

    for metric, expected_value in (
        EXPECTED.items()
    ):

        actual_value = actuals[
            metric
        ]

        passed = (
            actual_value
            == expected_value
        )

        audit_rows.append(
            {
                "metric":
                    metric,

                "expected_value":
                    expected_value,

                "actual_value":
                    actual_value,

                "status":
                    (
                        "PASS"
                        if passed
                        else "FAIL"
                    ),
            }
        )

    audit = pd.DataFrame(
        audit_rows
    )

    # ========================================================
    # Cross-layer QA
    # ========================================================

    checks = {
        "all_expected_numeric_invariants_pass":
            (
                audit[
                    "status"
                ]
                == "PASS"
            ).all(),

        "final_recommendation_enabled_count_zero":
            final_recommendation_enabled_count
            == 0,

        "all_final_recommendations_not_issued":
            final_not_issued_count
            == final_profile_rows,

        "no_queue_wait_historical_claim":
            not queue_wait_historical_claim_present,

        "no_leaderboard_historical_claim":
            not leaderboard_historical_claim_present,

        "queue_policy_direct_wait_unobserved":
            queue_policy_direct_wait_unobserved,

        "queue_policy_position_unobserved":
            queue_policy_position_unobserved,

        "queue_policy_2024_cutoff_exact":
            queue_policy_2024_cutoff_exact,

        "metadata_profile_rows_match":
            metadata_profile_rows_match,

        "metadata_normal_rows_match":
            metadata_normal_rows_match,

        "metadata_recovery_rows_match":
            metadata_recovery_rows_match,

        "metadata_recommendation_disabled":
            metadata_recommendation_disabled,

        "all_phase_qas_pass":
            all_phase_qas_pass,

        "all_required_sources_have_policy_hash":
            all_required_sources_have_hash,

        "final_phase8a_qa_pass":
            qa_all_pass(
                final_qa
            ),
    }

    # ========================================================
    # Policy hash
    # ========================================================

    policy_payload = {
        "phase":
            "8B",

        "policy_version":
            POLICY_VERSION,

        "expected_invariants":
            EXPECTED,

        "phase_qas":
            sorted(
                PHASE_QA_FILES.keys()
            ),

        "recommendation_enabled":
            False,

        "historical_queue_wait_claim":
            False,

        "historical_leaderboard_claim":
            False,
    }

    global_policy_hash = stable_hash(
        policy_payload
    )

    audit[
        "global_policy_hash"
    ] = global_policy_hash

    phase_status[
        "global_policy_hash"
    ] = global_policy_hash

    if not hash_inventory.empty:

        hash_inventory[
            "global_policy_hash"
        ] = global_policy_hash

    # ========================================================
    # QA rows
    # ========================================================

    qa_rows = []

    for metric, passed in (
        checks.items()
    ):

        qa_rows.append(
            {
                "metric":
                    metric,

                "value":
                    int(
                        bool(
                            passed
                        )
                    ),

                "status":
                    (
                        "PASS"
                        if passed
                        else "FAIL"
                    ),
            }
        )

    qa_rows.extend(
        [
            {
                "metric":
                    "numeric_invariant_rows",

                "value":
                    len(
                        audit
                    ),

                "status":
                    "INFO",
            },

            {
                "metric":
                    "phase_qa_files_audited",

                "value":
                    len(
                        phase_status
                    ),

                "status":
                    "INFO",
            },

            {
                "metric":
                    "policy_hash_inventory_rows",

                "value":
                    len(
                        hash_inventory
                    ),

                "status":
                    "INFO",
            },

            {
                "metric":
                    "global_policy_hash",

                "value":
                    global_policy_hash,

                "status":
                    "INFO",
            },
        ]
    )

    qa = pd.DataFrame(
        qa_rows
    )

    all_pass = all(
        checks.values()
    )

    # ========================================================
    # PRINT
    # ========================================================

    print()
    print("GLOBAL NUMERIC INVARIANTS")
    print("-" * 120)

    print(
        audit[
            [
                "metric",
                "expected_value",
                "actual_value",
                "status",
            ]
        ]
        .to_string(
            index=False
        )
    )

    print()
    print("PHASE QA STATUS")
    print("-" * 140)

    print(
        phase_status[
            [
                "phase",
                "file_exists",
                "all_hard_checks_pass",
                "qa_file",
            ]
        ]
        .to_string(
            index=False
        )
    )

    print()
    print("FINAL DECISION BOUNDARIES")
    print("-" * 120)

    print(
        "Recommendation-enabled rows:",
        final_recommendation_enabled_count,
    )

    print(
        "NOT_ISSUED rows:",
        final_not_issued_count,
        "/",
        final_profile_rows,
    )

    print(
        "Queue-wait historical claim present:",
        queue_wait_historical_claim_present,
    )

    print(
        "Leaderboard historical claim present:",
        leaderboard_historical_claim_present,
    )

    print(
        "Direct queue wait policy:",
        queue_lookup.get(
            "DIRECT_QUEUE_WAIT"
        ),
    )

    print(
        "Queue position policy:",
        queue_lookup.get(
            "QUEUE_POSITION"
        ),
    )

    print(
        "2024 cutoff policy:",
        queue_lookup.get(
            "SESSION_CUTOFF_2024"
        ),
    )

    print()
    print("POLICY HASH INVENTORY")
    print("-" * 120)

    if hash_inventory.empty:

        print(
            "No policy hashes found."
        )

    else:

        print(
            hash_inventory[
                [
                    "source_name",
                    "hash_column",
                    "policy_hash",
                ]
            ]
            .sort_values(
                [
                    "source_name",
                    "hash_column",
                ]
            )
            .to_string(
                index=False
            )
        )

    print()
    print("GLOBAL QA")
    print("-" * 130)

    print(
        qa.to_string(
            index=False
        )
    )

    # ========================================================
    # WRITE
    # ========================================================

    GLOBAL_AUDIT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    audit.to_csv(
        GLOBAL_AUDIT_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    hash_inventory.to_csv(
        GLOBAL_HASH_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    phase_status.to_csv(
        GLOBAL_PHASE_STATUS_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    qa.to_csv(
        GLOBAL_QA_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    # ========================================================
    # REPORT
    # ========================================================

    report = []

    report.append(
        "# Global Pipeline Consistency Audit V1"
    )

    report.append("")

    report.append(
        f"Policy version: `{POLICY_VERSION}`"
    )

    report.append(
        f"Global policy hash: `{global_policy_hash}`"
    )

    report.append("")

    report.append(
        "## Purpose"
    )

    report.append("")

    report.append(
        "Verify cross-phase row counts, frozen evidence boundaries, "
        "recommendation restrictions, QA status, and policy-hash presence."
    )

    report.append("")

    report.append(
        "## Numeric invariants"
    )

    report.append("")

    for _, row in (
        audit.iterrows()
    ):

        report.append(
            f"- `{row['metric']}`: "
            f"expected `{row['expected_value']}`, "
            f"actual `{row['actual_value']}`, "
            f"status `{row['status']}`"
        )

    report.append("")

    report.append(
        "## Decision boundary"
    )

    report.append("")

    report.append(
        f"- Recommendation-enabled final rows: "
        f"`{final_recommendation_enabled_count}`"
    )

    report.append(
        f"- Final rows marked NOT_ISSUED: "
        f"`{final_not_issued_count}/{final_profile_rows}`"
    )

    report.append(
        f"- Historical queue-wait claim present: "
        f"`{queue_wait_historical_claim_present}`"
    )

    report.append(
        f"- Historical leaderboard claim present: "
        f"`{leaderboard_historical_claim_present}`"
    )

    report.append("")

    report.append(
        "## Evidence boundary"
    )

    report.append("")

    report.append(
        f"- Direct queue wait: "
        f"`{queue_lookup.get('DIRECT_QUEUE_WAIT')}`"
    )

    report.append(
        f"- Exact queue position: "
        f"`{queue_lookup.get('QUEUE_POSITION')}`"
    )

    report.append(
        f"- 2024 session cutoff: "
        f"`{queue_lookup.get('SESSION_CUTOFF_2024')}`"
    )

    report.append("")

    report.append(
        "## Phase QA"
    )

    report.append("")

    report.append(
        f"All audited phase QA files pass: "
        f"`{all_phase_qas_pass}`"
    )

    report.append("")

    report.append(
        "## Status"
    )

    report.append("")

    if all_pass:

        report.append(
            "**GLOBAL_PIPELINE_CONSISTENCY_FROZEN**"
        )

    else:

        report.append(
            "**REVIEW_REQUIRED**"
        )

    GLOBAL_REPORT_FILE.write_text(
        "\n".join(
            report
        ),
        encoding="utf-8",
    )

    # ========================================================
    # FINAL
    # ========================================================

    print()
    print("=" * 100)

    if all_pass:

        print(
            "FINAL STATUS: "
            "GLOBAL_PIPELINE_CONSISTENCY_FROZEN"
        )

    else:

        print(
            "FINAL STATUS: REVIEW_REQUIRED"
        )

    print("=" * 100)

    print()
    print(
        "NO MODEL WAS RETRAINED."
    )

    print(
        "NO DATASET ROWS WERE MUTATED."
    )

    print(
        "NO HISTORICAL QUEUE WAIT OR "
        "LEADERBOARD STATE WAS INVENTED."
    )

    print(
        "NO RETAIN/WITHDRAW RECOMMENDATION "
        "WAS ENABLED."
    )

    print()
    print("OUTPUTS")

    print(
        GLOBAL_AUDIT_FILE
    )

    print(
        GLOBAL_HASH_FILE
    )

    print(
        GLOBAL_PHASE_STATUS_FILE
    )

    print(
        GLOBAL_QA_FILE
    )

    print(
        GLOBAL_REPORT_FILE
    )


if __name__ == "__main__":
    main()
