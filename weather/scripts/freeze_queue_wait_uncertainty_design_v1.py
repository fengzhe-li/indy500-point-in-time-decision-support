from pathlib import Path
import hashlib
import json
import re

import numpy as np
import pandas as pd


# ============================================================
# INPUTS
# ============================================================

CHRONOLOGY_EVENTS_FILE = Path(
    "data/canonical/v1/chronology_events.csv"
)

CHRONOLOGY_CONSTRAINTS_FILE = Path(
    "data/canonical/v1/chronology_constraints.csv"
)

ATTEMPTS_FILE = Path(
    "data/canonical/v1/attempts.csv"
)

QUALIFYING_EVENTS_FILE = Path(
    "data/canonical/v1/qualifying_events.csv"
)

PERFORMANCE_TIMING_FILE = Path(
    "weather/output/performance_grade_attempt_timing.csv"
)

PERFORMANCE_TIMING_2024_FILE = Path(
    "weather/output/performance_grade_attempt_timing_2024_supported.csv"
)

PERFORMANCE_DISTRIBUTION_FILE = Path(
    "weather/output/repeat_performance_empirical_distributions_v1.csv"
)

RECOVERY_PROBABILITY_FILE = Path(
    "weather/output/repeat_performance_recovery_probability_v1.csv"
)


# ============================================================
# OUTPUTS
# ============================================================

EVIDENCE_INVENTORY_FILE = Path(
    "weather/output/queue_wait_evidence_inventory_v1.csv"
)

THROUGHPUT_PROXY_FILE = Path(
    "weather/output/queue_wait_throughput_proxy_v1.csv"
)

SESSION_BOUNDARY_FILE = Path(
    "weather/output/queue_wait_session_boundary_audit_v1.csv"
)

RUN_DURATION_FILE = Path(
    "weather/output/queue_wait_run_duration_reference_v1.csv"
)

POLICY_FILE = Path(
    "weather/output/queue_wait_uncertainty_policy_v1.csv"
)

QA_FILE = Path(
    "weather/output/queue_wait_uncertainty_design_v1_qa.csv"
)

REPORT_FILE = Path(
    "weather/output/queue_wait_uncertainty_design_v1.md"
)


# ============================================================
# DESIGN
# ============================================================

POLICY_ID = (
    "QUEUE_WAIT_UNCERTAINTY_POLICY_V1"
)

POLICY_VERSION = (
    "QUEUE_WAIT_UNCERTAINTY_DESIGN_FREEZE_V1"
)

SUPPORTED_PERFORMANCE_YEARS = [
    2020,
    2021,
    2023,
    2024,
]

EXPECTED_2024_CUTOFF_UTC = (
    pd.Timestamp(
        "2024-05-18T21:50:00Z"
    )
)

DIRECT_QUEUE_KEYWORDS = [
    "QUEUE",
    "LANE",
    "REQUEUE",
    "RE-QUEUE",
    "WITHDRAW",
    "WITHDRAWAL",
]

RANDOM_SEED = 500


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


def parse_utc(series):

    return pd.to_datetime(
        series,
        utc=True,
        errors="coerce",
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


def infer_year_from_values(
    df,
):

    candidates = [
        "year",
        "session_id",
        "event_id",
        "attempt_id",
        "source_locator",
    ]

    output = pd.Series(
        np.nan,
        index=df.index,
        dtype=float,
    )

    for col in candidates:

        if col not in df.columns:
            continue

        if col == "year":

            parsed = numeric(
                df[col]
            )

        else:

            parsed = pd.to_numeric(
                df[col]
                .astype(str)
                .str.extract(
                    r"(20(?:20|21|22|23|24))",
                    expand=False,
                ),
                errors="coerce",
            )

        output = output.fillna(
            parsed
        )

    return output


def first_existing(
    columns,
    candidates,
):

    for candidate in candidates:

        if candidate in columns:
            return candidate

    return None


def bool_from_any(series):

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
                "y",
            ]
        )
    )


def summary_row(
    scope,
    values,
):

    x = pd.Series(
        numeric(
            pd.Series(values)
        )
    ).dropna()

    if len(x) == 0:

        return {
            "scope":
                scope,

            "rows":
                0,

            "mean_seconds":
                np.nan,

            "median_seconds":
                np.nan,

            "q10_seconds":
                np.nan,

            "q25_seconds":
                np.nan,

            "q75_seconds":
                np.nan,

            "q90_seconds":
                np.nan,

            "q95_seconds":
                np.nan,

            "min_seconds":
                np.nan,

            "max_seconds":
                np.nan,
        }

    return {
        "scope":
            scope,

        "rows":
            int(
                len(x)
            ),

        "mean_seconds":
            float(
                x.mean()
            ),

        "median_seconds":
            float(
                x.median()
            ),

        "q10_seconds":
            float(
                x.quantile(
                    0.10
                )
            ),

        "q25_seconds":
            float(
                x.quantile(
                    0.25
                )
            ),

        "q75_seconds":
            float(
                x.quantile(
                    0.75
                )
            ),

        "q90_seconds":
            float(
                x.quantile(
                    0.90
                )
            ),

        "q95_seconds":
            float(
                x.quantile(
                    0.95
                )
            ),

        "min_seconds":
            float(
                x.min()
            ),

        "max_seconds":
            float(
                x.max()
            ),
    }


# ============================================================
# MAIN
# ============================================================

def main():

    chronology = read_required(
        CHRONOLOGY_EVENTS_FILE
    )

    constraints = read_required(
        CHRONOLOGY_CONSTRAINTS_FILE
    )

    attempts = read_required(
        ATTEMPTS_FILE
    )

    qualifying = read_required(
        QUALIFYING_EVENTS_FILE
    )

    perf_old = read_required(
        PERFORMANCE_TIMING_FILE
    )

    perf_2024 = read_required(
        PERFORMANCE_TIMING_2024_FILE
    )

    performance_distribution = (
        read_required(
            PERFORMANCE_DISTRIBUTION_FILE
        )
    )

    recovery_probability = (
        read_required(
            RECOVERY_PROBABILITY_FILE
        )
    )

    print()
    print("=" * 100)
    print(
        "PHASE 6A — QUEUE / WAIT "
        "UNCERTAINTY DESIGN FREEZE V1"
    )
    print("=" * 100)

    print()
    print(
        "Chronology events:",
        len(
            chronology
        )
    )

    print(
        "Chronology constraints:",
        len(
            constraints
        )
    )

    print(
        "Canonical attempts:",
        len(
            attempts
        )
    )

    # ========================================================
    # Normalize chronology
    # ========================================================

    chronology = chronology.copy()

    chronology[
        "_year"
    ] = infer_year_from_values(
        chronology
    )

    event_type_col = first_existing(
        chronology.columns,
        [
            "event_type",
            "chronology_event_type",
            "type",
        ],
    )

    quality_col = first_existing(
        chronology.columns,
        [
            "time_quality",
            "event_time_quality",
            "quality",
        ],
    )

    basis_col = first_existing(
        chronology.columns,
        [
            "time_basis",
            "event_time_basis",
            "basis",
        ],
    )

    event_time_col = first_existing(
        chronology.columns,
        [
            "event_time_utc",
            "time_utc",
            "timestamp_utc",
        ],
    )

    lower_col = first_existing(
        chronology.columns,
        [
            "event_time_lower_utc",
            "lower_time_utc",
            "time_lower_utc",
        ],
    )

    upper_col = first_existing(
        chronology.columns,
        [
            "event_time_upper_utc",
            "upper_time_utc",
            "time_upper_utc",
        ],
    )

    if event_type_col is None:
        raise RuntimeError(
            "No chronology event-type field found."
        )

    # ========================================================
    # Evidence inventory
    # ========================================================

    evidence_rows = []

    chronology[
        "_event_type"
    ] = (
        chronology[
            event_type_col
        ]
        .astype(str)
        .str.upper()
    )

    chronology[
        "_direct_queue_keyword"
    ] = chronology[
        "_event_type"
    ].apply(
        lambda value:
            any(
                keyword
                in value
                for keyword
                in DIRECT_QUEUE_KEYWORDS
            )
    )

    for (
        event_type,
        group,
    ) in chronology.groupby(
        "_event_type",
        dropna=False,
    ):

        direct_queue = bool(
            group[
                "_direct_queue_keyword"
            ].any()
        )

        nonnull_event_time = (
            int(
                group[
                    event_time_col
                ].notna().sum()
            )
            if event_time_col
            else 0
        )

        evidence_rows.append(
            {
                "evidence_layer":
                    (
                        "DIRECT_QUEUE_CANDIDATE"
                        if direct_queue
                        else "CHRONOLOGY_OTHER"
                    ),

                "evidence_type":
                    str(
                        event_type
                    ),

                "rows":
                    len(
                        group
                    ),

                "nonnull_event_time_rows":
                    nonnull_event_time,

                "direct_queue_semantics_candidate":
                    direct_queue,

                "usable_as_direct_queue_wait":
                    False,

                "allowed_use":
                    (
                        "MANUAL_REVIEW_ONLY"
                        if direct_queue
                        else "CHRONOLOGY_CONTEXT_ONLY"
                    ),

                "forbidden_use":
                    (
                        "DO_NOT_CONVERT_TO_QUEUE_WAIT_WITHOUT_"
                        "QUEUE_ENTRY_AND_RUN_START_PAIR"
                    ),
            }
        )

    # --------------------------------------------------------
    # Chronology constraints evidence
    # --------------------------------------------------------

    constraint_type_col = first_existing(
        constraints.columns,
        [
            "constraint_type",
            "anchor_type",
            "event_type",
            "constraint_class",
        ],
    )

    if constraint_type_col is not None:

        for (
            constraint_type,
            group,
        ) in constraints.groupby(
            constraint_type_col,
            dropna=False,
        ):

            label = str(
                constraint_type
            ).upper()

            direct_candidate = any(
                keyword in label
                for keyword
                in DIRECT_QUEUE_KEYWORDS
            )

            evidence_rows.append(
                {
                    "evidence_layer":
                        "CHRONOLOGY_CONSTRAINT",

                    "evidence_type":
                        label,

                    "rows":
                        len(
                            group
                        ),

                    "nonnull_event_time_rows":
                        np.nan,

                    "direct_queue_semantics_candidate":
                        direct_candidate,

                    "usable_as_direct_queue_wait":
                        False,

                    "allowed_use":
                        "BOUND_OR_ORDERING_CONTEXT_ONLY",

                    "forbidden_use":
                        (
                            "DO_NOT_EQUATE_CONSTRAINT_TIME_"
                            "WITH_QUEUE_WAIT"
                        ),
                }
            )

    # --------------------------------------------------------
    # Performance timing evidence
    # --------------------------------------------------------

    evidence_rows.append(
        {
            "evidence_layer":
                "PERFORMANCE_GRADE_TIMING",

            "evidence_type":
                "SEQUENCE_MATCH_2020_2021_2023",

            "rows":
                len(
                    perf_old
                ),

            "nonnull_event_time_rows":
                np.nan,

            "direct_queue_semantics_candidate":
                False,

            "usable_as_direct_queue_wait":
                False,

            "allowed_use":
                "ATTEMPT_THROUGHPUT_PROXY_ONLY",

            "forbidden_use":
                (
                    "NOT_EXACT_RUN_START;"
                    "NOT_QUEUE_ENTRY;"
                    "NOT_QUEUE_WAIT"
                ),
        }
    )

    evidence_rows.append(
        {
            "evidence_layer":
                "PERFORMANCE_GRADE_TIMING",

            "evidence_type":
                "SUPPORTED_2024_SUBSET",

            "rows":
                len(
                    perf_2024
                ),

            "nonnull_event_time_rows":
                np.nan,

            "direct_queue_semantics_candidate":
                False,

            "usable_as_direct_queue_wait":
                False,

            "allowed_use":
                "ATTEMPT_THROUGHPUT_PROXY_ONLY",

            "forbidden_use":
                (
                    "NOT_EXACT_RUN_START;"
                    "NOT_QUEUE_ENTRY;"
                    "NOT_QUEUE_WAIT"
                ),
        }
    )

    evidence_inventory = pd.DataFrame(
        evidence_rows
    )

    # ========================================================
    # Direct queue evidence audit
    # ========================================================

    direct_candidates = chronology[
        chronology[
            "_direct_queue_keyword"
        ]
    ].copy()

    # Direct wait would require, at minimum:
    #
    # same identifiable attempt +
    # queue-entry timestamp +
    # compatible run-start timestamp.
    #
    # We intentionally do NOT infer either side.
    #
    direct_queue_wait_pairs = 0

    # ========================================================
    # Performance timing throughput proxy
    # ========================================================

    def normalize_perf(
        frame,
        source_label,
    ):

        out = frame.copy()

        time_col = first_existing(
            out.columns,
            [
                "mapped_capture_time_utc",
                "performance_time_utc",
                "capture_time_utc",
                "time_utc",
            ],
        )

        if time_col is None:
            raise RuntimeError(
                f"No performance timing column in {source_label}"
            )

        out[
            "_time"
        ] = parse_utc(
            out[
                time_col
            ]
        )

        out[
            "_year"
        ] = infer_year_from_values(
            out
        )

        out[
            "_source"
        ] = source_label

        if (
            "attempt_id"
            not in out.columns
        ):

            raise RuntimeError(
                f"attempt_id missing in {source_label}"
            )

        keep = [
            "attempt_id",
            "_time",
            "_year",
            "_source",
        ]

        if "session_id" in out.columns:
            keep.append(
                "session_id"
            )

        if "car_number" in out.columns:
            keep.append(
                "car_number"
            )

        return out[
            keep
        ].copy()

    perf_a = normalize_perf(
        perf_old,
        "PERFORMANCE_GRADE_2020_2021_2023",
    )

    perf_b = normalize_perf(
        perf_2024,
        "PERFORMANCE_GRADE_2024_SUPPORTED",
    )

    perf = pd.concat(
        [
            perf_a,
            perf_b,
        ],
        ignore_index=True,
    )

    perf = perf[
        perf[
            "_time"
        ].notna()
    ].copy()

    perf[
        "_year"
    ] = numeric(
        perf[
            "_year"
        ]
    )

    perf = (
        perf
        .sort_values(
            [
                "_year",
                "_time",
                "attempt_id",
            ]
        )
        .reset_index(
            drop=True
        )
    )

    # --------------------------------------------------------
    # Adjacent supported-attempt capture/event spacing.
    #
    # IMPORTANT:
    # this is a throughput proxy only.
    # --------------------------------------------------------

    spacing_rows = []

    for year, group in (
        perf.groupby(
            "_year",
            dropna=True,
        )
    ):

        group = (
            group
            .sort_values(
                "_time"
            )
            .reset_index(
                drop=True
            )
        )

        prior_time = None
        prior_attempt = None

        for _, row in (
            group.iterrows()
        ):

            if prior_time is not None:

                spacing_seconds = (
                    row[
                        "_time"
                    ]
                    - prior_time
                ).total_seconds()

                if spacing_seconds >= 0:

                    spacing_rows.append(
                        {
                            "year":
                                int(
                                    year
                                ),

                            "prior_attempt_id":
                                prior_attempt,

                            "current_attempt_id":
                                row[
                                    "attempt_id"
                                ],

                            "prior_time_utc":
                                prior_time.isoformat(),

                            "current_time_utc":
                                row[
                                    "_time"
                                ].isoformat(),

                            "spacing_seconds":
                                float(
                                    spacing_seconds
                                ),

                            "proxy_type":
                                (
                                    "SUPPORTED_ATTEMPT_"
                                    "TIMESTAMP_SPACING"
                                ),

                            "queue_wait_usable":
                                False,

                            "interpretation":
                                (
                                    "SYSTEM_THROUGHPUT_PROXY_ONLY;"
                                    "NOT_QUEUE_WAIT"
                                ),
                        }
                    )

            prior_time = row[
                "_time"
            ]

            prior_attempt = row[
                "attempt_id"
            ]

    spacing = pd.DataFrame(
        spacing_rows
    )

    # --------------------------------------------------------
    # Proxy summary rows
    # --------------------------------------------------------

    proxy_summary_rows = []

    if not spacing.empty:

        proxy_summary_rows.append(
            summary_row(
                "ALL_SUPPORTED_YEARS",
                spacing[
                    "spacing_seconds"
                ],
            )
        )

        for year, group in (
            spacing.groupby(
                "year"
            )
        ):

            proxy_summary_rows.append(
                summary_row(
                    f"YEAR_{int(year)}",
                    group[
                        "spacing_seconds"
                    ],
                )
            )

    throughput_summary = pd.DataFrame(
        proxy_summary_rows
    )

    if not throughput_summary.empty:

        throughput_summary[
            "proxy_type"
        ] = (
            "SUPPORTED_ATTEMPT_TIMESTAMP_SPACING"
        )

        throughput_summary[
            "queue_wait_usable"
        ] = False

        throughput_summary[
            "interpretation"
        ] = (
            "DESCRIPTIVE_THROUGHPUT_ONLY_NOT_QUEUE_WAIT"
        )

    # ========================================================
    # Run-duration reference
    # ========================================================

    total_seconds_col = first_existing(
        attempts.columns,
        [
            "four_lap_total_seconds",
            "total_seconds",
        ],
    )

    avg_speed_col = first_existing(
        attempts.columns,
        [
            "four_lap_average_speed_mph",
            "average_speed_mph",
        ],
    )

    if total_seconds_col is None:
        raise RuntimeError(
            "No four-lap total-seconds field found."
        )

    attempts = attempts.copy()

    attempts[
        "_year"
    ] = infer_year_from_values(
        attempts
    )

    attempts[
        "_run_seconds"
    ] = numeric(
        attempts[
            total_seconds_col
        ]
    )

    complete_run = attempts[
        attempts[
            "_run_seconds"
        ].notna()
        &
        (
            attempts[
                "_run_seconds"
            ] > 0
        )
    ].copy()

    run_duration_rows = []

    run_duration_rows.append(
        summary_row(
            "ALL_COMPLETE_FOUR_LAP_ATTEMPTS",
            complete_run[
                "_run_seconds"
            ],
        )
    )

    for year, group in (
        complete_run.groupby(
            "_year",
            dropna=True,
        )
    ):

        run_duration_rows.append(
            summary_row(
                f"YEAR_{int(year)}",
                group[
                    "_run_seconds"
                ],
            )
        )

    run_duration_reference = pd.DataFrame(
        run_duration_rows
    )

    run_duration_reference[
        "semantic_role"
    ] = (
        "TIMED_RUN_DURATION_REFERENCE"
    )

    run_duration_reference[
        "queue_wait_component"
    ] = False

    run_duration_reference[
        "cutoff_feasibility_component"
    ] = True

    run_duration_reference[
        "interpretation"
    ] = (
        "RUN_TIME_IS_ONLY_ONE_COMPONENT_OF_"
        "WITHDRAW_TO_COMPLETION_TIME"
    )

    # ========================================================
    # Session-boundary audit
    # ========================================================

    boundary_rows = []

    session_boundary_mask = (
        chronology[
            "_event_type"
        ].str.contains(
            "SESSION_BOUNDARY",
            na=False,
        )
    )

    chronology_boundaries = chronology[
        session_boundary_mask
    ].copy()

    for _, row in (
        chronology_boundaries.iterrows()
    ):

        event_time = (
            pd.to_datetime(
                row[
                    event_time_col
                ],
                utc=True,
                errors="coerce",
            )
            if event_time_col
            else pd.NaT
        )

        boundary_rows.append(
            {
                "year":
                    (
                        int(
                            row[
                                "_year"
                            ]
                        )
                        if pd.notna(
                            row[
                                "_year"
                            ]
                        )
                        else np.nan
                    ),

                "boundary_source":
                    "CHRONOLOGY_EVENT",

                "event_type":
                    row[
                        event_type_col
                    ],

                "event_time_utc":
                    (
                        event_time.isoformat()
                        if pd.notna(
                            event_time
                        )
                        else None
                    ),

                "time_quality":
                    (
                        row[
                            quality_col
                        ]
                        if quality_col
                        else None
                    ),

                "time_basis":
                    (
                        row[
                            basis_col
                        ]
                        if basis_col
                        else None
                    ),

                "usable_for_hard_cutoff":
                    bool(
                        pd.notna(
                            event_time
                        )
                        and (
                            str(
                                row[
                                    quality_col
                                ]
                            ).upper()
                            == "EXACT_OBSERVED"
                            if quality_col
                            else False
                        )
                    ),

                "interpretation":
                    (
                        "SESSION_BOUNDARY_EVIDENCE"
                    ),
            }
        )

    # --------------------------------------------------------
    # qualifying_events scheduled/actual boundaries
    # --------------------------------------------------------

    q_year = infer_year_from_values(
        qualifying
    )

    start_candidates = [
        "actual_start_time_utc",
        "scheduled_start_time_utc",
        "scheduled_start_utc",
        "start_time_utc",
    ]

    end_candidates = [
        "actual_end_time_utc",
        "scheduled_end_time_utc",
        "scheduled_end_utc",
        "end_time_utc",
    ]

    q_start_col = first_existing(
        qualifying.columns,
        start_candidates,
    )

    q_end_col = first_existing(
        qualifying.columns,
        end_candidates,
    )

    for idx, row in (
        qualifying.iterrows()
    ):

        year_value = q_year.loc[
            idx
        ]

        if q_start_col:

            start_value = pd.to_datetime(
                row[
                    q_start_col
                ],
                utc=True,
                errors="coerce",
            )

            if pd.notna(
                start_value
            ):

                boundary_rows.append(
                    {
                        "year":
                            (
                                int(
                                    year_value
                                )
                                if pd.notna(
                                    year_value
                                )
                                else np.nan
                            ),

                        "boundary_source":
                            "QUALIFYING_EVENTS",

                        "event_type":
                            "SESSION_START_REFERENCE",

                        "event_time_utc":
                            start_value.isoformat(),

                        "time_quality":
                            (
                                "SCHEMA_REFERENCE"
                            ),

                        "time_basis":
                            q_start_col,

                        "usable_for_hard_cutoff":
                            False,

                        "interpretation":
                            (
                                "SCHEDULED_OR_SCHEMA_REFERENCE;"
                                "NOT_AUTOMATICALLY_EXACT"
                            ),
                    }
                )

        if q_end_col:

            end_value = pd.to_datetime(
                row[
                    q_end_col
                ],
                utc=True,
                errors="coerce",
            )

            if pd.notna(
                end_value
            ):

                boundary_rows.append(
                    {
                        "year":
                            (
                                int(
                                    year_value
                                )
                                if pd.notna(
                                    year_value
                                )
                                else np.nan
                            ),

                        "boundary_source":
                            "QUALIFYING_EVENTS",

                        "event_type":
                            "SESSION_END_REFERENCE",

                        "event_time_utc":
                            end_value.isoformat(),

                        "time_quality":
                            (
                                "SCHEMA_REFERENCE"
                            ),

                        "time_basis":
                            q_end_col,

                        "usable_for_hard_cutoff":
                            False,

                        "interpretation":
                            (
                                "SCHEDULED_OR_SCHEMA_REFERENCE;"
                                "NOT_AUTOMATICALLY_EXACT"
                            ),
                    }
                )

    session_boundaries = pd.DataFrame(
        boundary_rows
    )

    # ========================================================
    # 2024 exact cutoff check
    # ========================================================

    exact_2024_cutoff_found = False

    if not session_boundaries.empty:

        sb = session_boundaries.copy()

        sb[
            "_time"
        ] = pd.to_datetime(
            sb[
                "event_time_utc"
            ],
            utc=True,
            errors="coerce",
        )

        candidate = sb[
            (
                numeric(
                    sb[
                        "year"
                    ]
                )
                == 2024
            )
            &
            (
                sb[
                    "usable_for_hard_cutoff"
                ]
                == True
            )
        ]

        exact_2024_cutoff_found = bool(
            (
                candidate[
                    "_time"
                ]
                == EXPECTED_2024_CUTOFF_UTC
            ).any()
        )

    # ========================================================
    # Policy freeze
    # ========================================================

    policy_rows = [
        {
            "policy_id":
                POLICY_ID,

            "component":
                "DIRECT_QUEUE_WAIT",

            "status":
                "UNOBSERVED",

            "allowed_representation":
                "LATENT_UNCERTAINTY_ONLY",

            "source":
                "NONE_SUFFICIENT",

            "modeling_rule":
                (
                    "DO_NOT_ESTIMATE_DIRECT_QUEUE_WAIT_"
                    "FROM_RECORDER_CAPTURE_TIMESTAMPS"
                ),

            "simulation_use":
                (
                    "SCENARIO_OR_LATENT_MODEL_ONLY"
                ),
        },

        {
            "policy_id":
                POLICY_ID,

            "component":
                "QUEUE_POSITION",

            "status":
                "UNOBSERVED",

            "allowed_representation":
                "LATENT_STATE",

            "source":
                "NO_COMPLETE_HISTORICAL_LANE_STATE",

            "modeling_rule":
                (
                    "DO_NOT_RECONSTRUCT_EXACT_LANE1_LANE2_"
                    "QUEUE_STATE"
                ),

            "simulation_use":
                (
                    "SENSITIVITY_SCENARIO_ONLY"
                ),
        },

        {
            "policy_id":
                POLICY_ID,

            "component":
                "ATTEMPT_THROUGHPUT",

            "status":
                "PARTIALLY_OBSERVED",

            "allowed_representation":
                "DESCRIPTIVE_PROXY",

            "source":
                (
                    "PERFORMANCE_GRADE_SUPPORTED_"
                    "ATTEMPT_TIMESTAMPS"
                ),

            "modeling_rule":
                (
                    "ADJACENT_SUPPORTED_TIMESTAMP_SPACING_"
                    "IS_NOT_QUEUE_WAIT"
                ),

            "simulation_use":
                (
                    "CALIBRATION_SANITY_CHECK_ONLY"
                ),
        },

        {
            "policy_id":
                POLICY_ID,

            "component":
                "TIMED_RUN_DURATION",

            "status":
                "OBSERVED_SUPPORTED",

            "allowed_representation":
                "EMPIRICAL_DISTRIBUTION",

            "source":
                "CANONICAL_COMPLETE_FOUR_LAP_ATTEMPTS",

            "modeling_rule":
                (
                    "MAY_SAMPLE_OR_USE_EMPIRICAL_QUANTILES_"
                    "FOR_RUN_DURATION"
                ),

            "simulation_use":
                (
                    "WITHDRAW_TO_COMPLETION_TIME_COMPONENT"
                ),
        },

        {
            "policy_id":
                POLICY_ID,

            "component":
                "STAGING_AND_RELEASE_OVERHEAD",

            "status":
                "UNOBSERVED_SEPARATELY",

            "allowed_representation":
                "LATENT_UNCERTAINTY",

            "source":
                "NO_SEPARATE_RELIABLE_MEASUREMENT",

            "modeling_rule":
                (
                    "DO_NOT_SET_TO_ZERO_AS_FACT;"
                    "HANDLE_IN_WAIT_SCENARIO"
                ),

            "simulation_use":
                (
                    "INCLUDED_IN_LATENT_WAIT_COMPONENT"
                ),
        },

        {
            "policy_id":
                POLICY_ID,

            "component":
                "SESSION_CUTOFF_2024",

            "status":
                (
                    "EXACT_SUPPORTED"
                    if exact_2024_cutoff_found
                    else "REVIEW_REQUIRED"
                ),

            "allowed_representation":
                "HARD_BOUNDARY",

            "source":
                "OFFICIAL_SESSION_BOUNDARY_EVIDENCE",

            "modeling_rule":
                (
                    "2024_CUTOFF_21_50_UTC_MAY_BE_USED_"
                    "AS_HARD_COMPLETION_BOUNDARY"
                ),

            "simulation_use":
                "CUTOFF_FEASIBILITY",
        },

        {
            "policy_id":
                POLICY_ID,

            "component":
                "SESSION_CUTOFF_OTHER_YEARS",

            "status":
                "NOT_FROZEN_EXACT",

            "allowed_representation":
                "NO_HARD_BOUNDARY_UNTIL_VERIFIED",

            "source":
                "INCOMPLETE_BOUNDARY_EVIDENCE",

            "modeling_rule":
                (
                    "DO_NOT_INVENT_EXACT_SESSION_END"
                ),

            "simulation_use":
                (
                    "EXCLUDE_FROM_HARD_CUTOFF_VALIDATION_"
                    "UNTIL_VERIFIED"
                ),
        },

        {
            "policy_id":
                POLICY_ID,

            "component":
                "RETAIN_ACTION",

            "status":
                "DETERMINISTIC_CURRENT_RESULT",

            "allowed_representation":
                "CURRENT_RETAINED_SPEED",

            "source":
                "DECISION_STATE_INPUT",

            "modeling_rule":
                (
                    "RETAIN_PRESERVES_CURRENT_RESULT;"
                    "NO_QUEUE_WAIT"
                ),

            "simulation_use":
                "BASELINE_ACTION",
        },

        {
            "policy_id":
                POLICY_ID,

            "component":
                "WITHDRAW_ACTION",

            "status":
                "PROBABILISTIC",

            "allowed_representation":
                (
                    "WAIT_UNCERTAINTY_PLUS_"
                    "PERFORMANCE_UNCERTAINTY"
                ),

            "source":
                (
                    "QUEUE_SCENARIO_PLUS_"
                    "REPEAT_PERFORMANCE_UNCERTAINTY"
                ),

            "modeling_rule":
                (
                    "WITHDRAW_FORFEITS_CURRENT_RESULT_"
                    "BEFORE_NEW_ATTEMPT_OUTCOME"
                ),

            "simulation_use":
                (
                    "MONTE_CARLO_BRANCH"
                ),
        },

        {
            "policy_id":
                POLICY_ID,

            "component":
                "NO_COMPLETED_RERUN_BEFORE_CUTOFF",

            "status":
                "EXPLICIT_FAILURE_STATE",

            "allowed_representation":
                "SIMULATION_OUTCOME",

            "source":
                "SESSION_CUTOFF_COMPARISON",

            "modeling_rule":
                (
                    "IF_WITHDRAW_TO_COMPLETION_TIME_EXCEEDS_"
                    "CUTOFF_NEW_RESULT_IS_UNAVAILABLE"
                ),

            "simulation_use":
                (
                    "MANDATORY_DOWNSIDE_BRANCH"
                ),
        },
    ]

    policy = pd.DataFrame(
        policy_rows
    )

    # ========================================================
    # Performance layer consistency
    # ========================================================

    distribution_scopes = set(
        performance_distribution[
            "distribution_scope"
        ].astype(str)
    )

    performance_uncertainty_ready = (
        "NORMAL_DIAGNOSTIC"
        in distribution_scopes
        and
        "RECOVERY_LIKE_DIAGNOSTIC"
        in distribution_scopes
    )

    recovery_groups = set(
        recovery_probability[
            "eligibility_group"
        ].astype(str)
    )

    recovery_probability_ready = (
        "LOW_BASELINE"
        in recovery_groups
        and
        "AT_OR_ABOVE_BASELINE_MEDIAN"
        in recovery_groups
    )

    # ========================================================
    # QA
    # ========================================================

    direct_queue_candidate_rows = int(
        chronology[
            "_direct_queue_keyword"
        ].sum()
    )

    complete_run_rows = len(
        complete_run
    )

    supported_timing_rows = len(
        perf
    )

    spacing_count = len(
        spacing
    )

    checks = {
        "chronology_input_nonempty":
            len(
                chronology
            )
            > 0,

        "attempts_input_nonempty":
            len(
                attempts
            )
            > 0,

        "performance_timing_nonempty":
            supported_timing_rows
            > 0,

        "throughput_spacing_materialized":
            spacing_count
            > 0,

        "complete_run_duration_reference_nonempty":
            complete_run_rows
            > 0,

        "direct_queue_wait_pairs_equal_zero":
            direct_queue_wait_pairs
            == 0,

        "throughput_proxy_not_marked_queue_wait":
            (
                bool(
                    (
                        spacing[
                            "queue_wait_usable"
                        ]
                        == False
                    ).all()
                )
                if not spacing.empty
                else False
            ),

        "policy_direct_queue_status_unobserved":
            (
                policy.loc[
                    policy[
                        "component"
                    ]
                    == "DIRECT_QUEUE_WAIT",
                    "status",
                ].iloc[0]
                == "UNOBSERVED"
            ),

        "policy_queue_position_unobserved":
            (
                policy.loc[
                    policy[
                        "component"
                    ]
                    == "QUEUE_POSITION",
                    "status",
                ].iloc[0]
                == "UNOBSERVED"
            ),

        "2024_exact_cutoff_found":
            exact_2024_cutoff_found,

        "performance_uncertainty_ready":
            performance_uncertainty_ready,

        "recovery_probability_ready":
            recovery_probability_ready,
    }

    # ========================================================
    # Policy hash
    # ========================================================

    hash_payload = {
        "phase":
            "6A",

        "policy_id":
            POLICY_ID,

        "policy_version":
            POLICY_VERSION,

        "direct_queue_wait_pairs":
            direct_queue_wait_pairs,

        "supported_timing_rows":
            supported_timing_rows,

        "throughput_spacing_rows":
            spacing_count,

        "complete_run_rows":
            complete_run_rows,

        "exact_2024_cutoff_found":
            exact_2024_cutoff_found,

        "policy_components":
            policy[
                "component"
            ].tolist(),
    }

    policy_hash = stable_hash(
        hash_payload
    )

    evidence_inventory[
        "policy_hash"
    ] = policy_hash

    spacing[
        "policy_hash"
    ] = policy_hash

    if not throughput_summary.empty:

        throughput_summary[
            "policy_hash"
        ] = policy_hash

    session_boundaries[
        "policy_hash"
    ] = policy_hash

    run_duration_reference[
        "policy_hash"
    ] = policy_hash

    policy[
        "policy_hash"
    ] = policy_hash

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
                    "chronology_rows",

                "value":
                    len(
                        chronology
                    ),

                "status":
                    "INFO",
            },

            {
                "metric":
                    "direct_queue_keyword_candidate_rows",

                "value":
                    direct_queue_candidate_rows,

                "status":
                    "INFO",
            },

            {
                "metric":
                    "direct_queue_wait_pairs",

                "value":
                    direct_queue_wait_pairs,

                "status":
                    "INFO",
            },

            {
                "metric":
                    "supported_performance_timing_rows",

                "value":
                    supported_timing_rows,

                "status":
                    "INFO",
            },

            {
                "metric":
                    "throughput_spacing_rows",

                "value":
                    spacing_count,

                "status":
                    "INFO",
            },

            {
                "metric":
                    "complete_four_lap_duration_rows",

                "value":
                    complete_run_rows,

                "status":
                    "INFO",
            },

            {
                "metric":
                    "2024_exact_cutoff_utc",

                "value":
                    (
                        EXPECTED_2024_CUTOFF_UTC
                        .isoformat()
                        if exact_2024_cutoff_found
                        else "NOT_CONFIRMED"
                    ),

                "status":
                    "INFO",
            },

            {
                "metric":
                    "policy_hash",

                "value":
                    policy_hash,

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
    print("DIRECT QUEUE EVIDENCE")
    print("-" * 120)

    print(
        "Chronology rows with queue/lane/requeue/"
        "withdraw keywords:",
        direct_queue_candidate_rows,
    )

    print(
        "Defensible direct queue-wait pairs:",
        direct_queue_wait_pairs,
    )

    print()
    print(
        "IMPORTANT: zero direct wait pairs does NOT mean "
        "queue wait was zero."
    )

    print(
        "It means queue wait is not directly recoverable "
        "from the frozen historical evidence."
    )

    print()
    print("THROUGHPUT PROXY SUMMARY")
    print("-" * 140)

    if throughput_summary.empty:

        print(
            "No throughput proxy materialized."
        )

    else:

        print(
            throughput_summary.to_string(
                index=False
            )
        )

    print()
    print(
        "SEMANTIC WARNING: these are adjacent supported "
        "attempt timestamp spacings, NOT queue waits."
    )

    print()
    print("TIMED-RUN DURATION REFERENCE")
    print("-" * 140)

    print(
        run_duration_reference.to_string(
            index=False
        )
    )

    print()
    print("SESSION BOUNDARY AUDIT")
    print("-" * 160)

    if session_boundaries.empty:

        print(
            "No session-boundary evidence."
        )

    else:

        print(
            session_boundaries.to_string(
                index=False
            )
        )

    print()
    print("QUEUE / WAIT POLICY")
    print("-" * 180)

    print(
        policy[
            [
                "component",
                "status",
                "allowed_representation",
                "source",
                "modeling_rule",
                "simulation_use",
            ]
        ]
        .to_string(
            index=False
        )
    )

    print()
    print("QA")
    print("-" * 130)

    print(
        qa.to_string(
            index=False
        )
    )

    # ========================================================
    # WRITE
    # ========================================================

    EVIDENCE_INVENTORY_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    evidence_inventory.to_csv(
        EVIDENCE_INVENTORY_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    # Write detailed spacing rows, not just summary.
    spacing.to_csv(
        THROUGHPUT_PROXY_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    session_boundaries.to_csv(
        SESSION_BOUNDARY_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    run_duration_reference.to_csv(
        RUN_DURATION_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    policy.to_csv(
        POLICY_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    qa.to_csv(
        QA_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    # ========================================================
    # REPORT
    # ========================================================

    report = []

    report.append(
        "# Queue / Wait Uncertainty Design V1"
    )

    report.append("")

    report.append(
        f"Policy ID: `{POLICY_ID}`"
    )

    report.append(
        f"Policy hash: `{policy_hash}`"
    )

    report.append("")

    report.append(
        "## Central evidence conclusion"
    )

    report.append("")

    report.append(
        "Historical evidence does not support direct "
        "reconstruction of individual queue waiting time."
    )

    report.append("")

    report.append(
        f"Defensible direct queue-wait pairs: "
        f"`{direct_queue_wait_pairs}`"
    )

    report.append("")

    report.append(
        "Supported attempt timestamps may be used only as "
        "a system-throughput sanity-check proxy. "
        "They must not be interpreted as queue-entry times "
        "or individual queue waits."
    )

    report.append("")

    report.append(
        "## Timed-run duration"
    )

    report.append("")

    report.append(
        f"Complete four-lap duration rows: "
        f"`{complete_run_rows}`"
    )

    report.append("")

    report.append(
        "Timed-run duration is empirically supported and may "
        "be used as one component of withdraw-to-completion time."
    )

    report.append("")

    report.append(
        "## Session cutoff"
    )

    report.append("")

    report.append(
        f"2024 exact 21:50 UTC cutoff confirmed: "
        f"`{exact_2024_cutoff_found}`"
    )

    report.append("")

    report.append(
        "Other years must not receive invented hard cutoff times "
        "until equivalent evidence is verified."
    )

    report.append("")

    report.append(
        "## Simulator policy"
    )

    report.append("")

    report.append(
        "Retain is the deterministic current-result branch."
    )

    report.append(
        "Withdraw is a probabilistic branch combining latent "
        "wait uncertainty, timed-run duration, cutoff risk, "
        "and frozen repeat-performance uncertainty."
    )

    report.append("")

    report.append(
        "If the simulated withdraw-to-completion time exceeds "
        "the session cutoff, the simulator must represent an "
        "explicit no-completed-rerun outcome."
    )

    report.append("")

    report.append(
        "## Forbidden inference"
    )

    report.append("")

    report.append(
        "- Recorder capture timestamp is not queue entry."
    )

    report.append(
        "- Attempt timestamp spacing is not queue waiting time."
    )

    report.append(
        "- Inter-attempt gap is not queue waiting time."
    )

    report.append(
        "- Missing lane state must not be reconstructed as fact."
    )

    report.append(
        "- Unknown staging overhead must not silently be set to zero."
    )

    report.append("")

    report.append(
        "## Next phase"
    )

    report.append("")

    report.append(
        "Phase 6B should parameterize explicit queue/wait "
        "sensitivity scenarios for Monte Carlo simulation. "
        "Those scenarios must remain labeled assumptions rather "
        "than historical observations."
    )

    report.append("")

    report.append(
        "## Status"
    )

    report.append("")

    if all_pass:

        report.append(
            "**QUEUE_WAIT_UNCERTAINTY_DESIGN_FROZEN**"
        )

    else:

        report.append(
            "**REVIEW_REQUIRED**"
        )

    REPORT_FILE.write_text(
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
            "QUEUE_WAIT_UNCERTAINTY_DESIGN_FROZEN"
        )

    else:

        print(
            "FINAL STATUS: REVIEW_REQUIRED"
        )

    print("=" * 100)

    print()
    print(
        "NO HISTORICAL QUEUE WAIT WAS INVENTED."
    )

    print(
        "NO THROUGHPUT PROXY WAS RELABELED AS QUEUE WAIT."
    )

    print(
        "NO MONTE CARLO SIMULATOR WAS BUILT YET."
    )

    print()
    print("OUTPUTS")

    print(
        EVIDENCE_INVENTORY_FILE
    )

    print(
        THROUGHPUT_PROXY_FILE
    )

    print(
        SESSION_BOUNDARY_FILE
    )

    print(
        RUN_DURATION_FILE
    )

    print(
        POLICY_FILE
    )

    print(
        QA_FILE
    )

    print(
        REPORT_FILE
    )


if __name__ == "__main__":
    main()
