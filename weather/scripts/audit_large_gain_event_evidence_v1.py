from pathlib import Path
import hashlib
import json

import numpy as np
import pandas as pd


# ============================================================
# INPUTS
# ============================================================

REGIME_FILE = Path(
    "weather/output/repeat_delta_regime_row_diagnostics_v1.csv"
)

DELTA_CONTEXT_FILE = Path(
    "weather/output/attempt_performance_repeat_delta_context_v1.csv"
)

PERFORMANCE_CONTEXT_FILE = Path(
    "weather/output/performance_context_features.csv"
)

ATTEMPTS_FILE = Path(
    "data/canonical/v1/attempts.csv"
)

LAPS_FILE = Path(
    "data/canonical/v1/attempt_laps.csv"
)


# ============================================================
# OPTIONAL INPUT
# ============================================================

SECTIONS_FILE = Path(
    "data/canonical/v1/attempt_sections.csv"
)


# ============================================================
# OUTPUTS
# ============================================================

EVENT_AUDIT_FILE = Path(
    "weather/output/large_gain_event_evidence_audit_v1.csv"
)

LAP_AUDIT_FILE = Path(
    "weather/output/large_gain_event_lap_audit_v1.csv"
)

SECTION_AUDIT_FILE = Path(
    "weather/output/large_gain_event_section_audit_v1.csv"
)

QA_FILE = Path(
    "weather/output/large_gain_event_evidence_audit_qa_v1.csv"
)

REPORT_FILE = Path(
    "weather/output/large_gain_event_evidence_audit_v1.md"
)


# ============================================================
# DESIGN
# ============================================================

EXPECTED_LARGE_GAIN_ROWS = 4

POLICY_VERSION = (
    "LARGE_GAIN_EVENT_EVIDENCE_AUDIT_V1"
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


def first_existing(columns, candidates):

    for candidate in candidates:
        if candidate in columns:
            return candidate

    return None


def clean_value(value):

    if pd.isna(value):
        return None

    if isinstance(
        value,
        (
            np.integer,
            np.floating,
        )
    ):
        return value.item()

    return value


def get_scalar(
    row,
    candidates,
):

    for col in candidates:

        if col in row.index:
            value = row[col]

            if pd.notna(value):
                return value

    return np.nan


def serialize_selected(
    row,
    columns,
):

    payload = {}

    for col in columns:

        if col in row.index:
            payload[col] = clean_value(
                row[col]
            )

    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        default=str,
    )


# ============================================================
# ATTEMPT FIELD GROUPS
# ============================================================

ATTEMPT_FIELDS = [
    "attempt_id",
    "session_id",
    "entry_key",
    "car_number",
    "driver_name",
    "car_attempt_index",
    "attempt_class",
    "result_status",
    "result_counted_at_session_end",
    "four_lap_total_seconds",
    "four_lap_average_speed_mph",
    "fuel_strategy",
    "start_time_utc",
    "start_time_quality",
    "start_time_basis",
    "source_id",
    "source_locator",
]

PERFORMANCE_CONTEXT_FIELDS = [
    "attempt_id",
    "session_id",
    "car_number",
    "driver_name",
    "car_attempt_index",
    "performance_time_utc",
    "four_lap_total_seconds",
    "four_lap_average_speed_mph",
    "attempt_class",
    "result_status",
    "result_counted_at_session_end",
    "prior_supported_attempt_count",
    "prior_supported_attempt_average_speed_mph",
    "best_prior_supported_average_speed_mph",
    "seconds_since_prior_supported_attempt",
    "timing_class",
    "timing_basis",
    "performance_alignment_usable",
    "decision_state_usable",
]


# ============================================================
# MAIN
# ============================================================

def main():

    regime = read_required(
        REGIME_FILE
    )

    delta_context = read_required(
        DELTA_CONTEXT_FILE
    )

    performance = read_required(
        PERFORMANCE_CONTEXT_FILE
    )

    attempts = read_required(
        ATTEMPTS_FILE
    )

    laps = read_required(
        LAPS_FILE
    )

    sections = read_optional(
        SECTIONS_FILE
    )

    print()
    print("=" * 100)
    print(
        "PHASE 5B-4 — LARGE-GAIN "
        "EVENT EVIDENCE AUDIT"
    )
    print("=" * 100)

    # ========================================================
    # Identify diagnostic large-gain rows
    # ========================================================

    if (
        "diagnostic_large_gain"
        not in regime.columns
    ):
        raise RuntimeError(
            "diagnostic_large_gain missing from regime file."
        )

    large_mask = (
        regime[
            "diagnostic_large_gain"
        ]
        .astype(str)
        .str.lower()
        .isin(
            [
                "true",
                "1",
                "yes",
            ]
        )
    )

    large = regime[
        large_mask
    ].copy()

    if len(
        large
    ) != EXPECTED_LARGE_GAIN_ROWS:

        raise RuntimeError(
            f"Expected {EXPECTED_LARGE_GAIN_ROWS} large-gain rows, "
            f"got {len(large)}"
        )

    print()
    print(
        "Diagnostic large-gain rows:",
        len(large)
    )

    # ========================================================
    # Validate IDs
    # ========================================================

    required_regime = [
        "current_attempt_id",
        "baseline_attempt_id",
        "year",
        "car_number",
        "driver_name",
        "baseline_speed_mph",
        "target_speed_delta_vs_best_prior_mph",
    ]

    missing = [
        col
        for col in required_regime
        if col not in large.columns
    ]

    if missing:
        raise RuntimeError(
            "Missing regime columns: "
            + ", ".join(missing)
        )

    if (
        attempts[
            "attempt_id"
        ].duplicated().any()
    ):
        raise RuntimeError(
            "Duplicate attempt_id in attempts.csv"
        )

    if (
        performance[
            "attempt_id"
        ].duplicated().any()
    ):
        raise RuntimeError(
            "Duplicate attempt_id in performance context."
        )

    attempt_index = (
        attempts
        .set_index(
            "attempt_id",
            drop=False,
        )
    )

    performance_index = (
        performance
        .set_index(
            "attempt_id",
            drop=False,
        )
    )

    # ========================================================
    # Lap schema reconnaissance
    # ========================================================

    lap_number_col = first_existing(
        laps.columns,
        [
            "lap_number",
            "qualifying_lap_number",
            "lap_index",
        ],
    )

    lap_speed_col = first_existing(
        laps.columns,
        [
            "lap_speed_mph",
            "average_speed_mph",
            "speed_mph",
            "lap_average_speed_mph",
        ],
    )

    lap_time_col = first_existing(
        laps.columns,
        [
            "lap_time_seconds",
            "elapsed_seconds",
            "lap_elapsed_seconds",
            "time_seconds",
        ],
    )

    source_lap_col = first_existing(
        laps.columns,
        [
            "source_report_lap_index",
            "source_lap_index",
        ],
    )

    print()
    print("LAP SCHEMA")
    print("-" * 80)

    print(
        "lap number column:",
        lap_number_col
    )

    print(
        "lap speed column:",
        lap_speed_col
    )

    print(
        "lap time column:",
        lap_time_col
    )

    print(
        "source lap column:",
        source_lap_col
    )

    # ========================================================
    # Event audit
    # ========================================================

    event_rows = []
    lap_rows = []
    section_rows = []

    all_referenced_ids = set()

    for _, large_row in (
        large.iterrows()
    ):

        current_id = str(
            large_row[
                "current_attempt_id"
            ]
        )

        baseline_id = str(
            large_row[
                "baseline_attempt_id"
            ]
        )

        all_referenced_ids.add(
            current_id
        )

        all_referenced_ids.add(
            baseline_id
        )

        if (
            current_id
            not in attempt_index.index
        ):
            raise RuntimeError(
                f"Current attempt missing canonical attempt: {current_id}"
            )

        if (
            baseline_id
            not in attempt_index.index
        ):
            raise RuntimeError(
                f"Baseline attempt missing canonical attempt: {baseline_id}"
            )

        current_attempt = (
            attempt_index.loc[
                current_id
            ]
        )

        baseline_attempt = (
            attempt_index.loc[
                baseline_id
            ]
        )

        if isinstance(
            current_attempt,
            pd.DataFrame,
        ):
            current_attempt = (
                current_attempt.iloc[0]
            )

        if isinstance(
            baseline_attempt,
            pd.DataFrame,
        ):
            baseline_attempt = (
                baseline_attempt.iloc[0]
            )

        current_perf = (
            performance_index.loc[
                current_id
            ]
            if current_id
            in performance_index.index
            else None
        )

        baseline_perf = (
            performance_index.loc[
                baseline_id
            ]
            if baseline_id
            in performance_index.index
            else None
        )

        if isinstance(
            current_perf,
            pd.DataFrame,
        ):
            current_perf = (
                current_perf.iloc[0]
            )

        if isinstance(
            baseline_perf,
            pd.DataFrame,
        ):
            baseline_perf = (
                baseline_perf.iloc[0]
            )

        # ====================================================
        # Lap extraction
        # ====================================================

        baseline_laps = laps[
            laps[
                "attempt_id"
            ].astype(str)
            == baseline_id
        ].copy()

        current_laps = laps[
            laps[
                "attempt_id"
            ].astype(str)
            == current_id
        ].copy()

        if (
            lap_number_col
            is not None
        ):

            baseline_laps[
                "_lap_order"
            ] = numeric(
                baseline_laps[
                    lap_number_col
                ]
            )

            current_laps[
                "_lap_order"
            ] = numeric(
                current_laps[
                    lap_number_col
                ]
            )

        else:

            baseline_laps[
                "_lap_order"
            ] = np.arange(
                1,
                len(
                    baseline_laps
                ) + 1,
            )

            current_laps[
                "_lap_order"
            ] = np.arange(
                1,
                len(
                    current_laps
                ) + 1,
            )

        baseline_laps = (
            baseline_laps
            .sort_values(
                "_lap_order"
            )
        )

        current_laps = (
            current_laps
            .sort_values(
                "_lap_order"
            )
        )

        # ====================================================
        # Per-lap audit
        # ====================================================

        lap_keys = sorted(
            set(
                baseline_laps[
                    "_lap_order"
                ].dropna()
            )
            |
            set(
                current_laps[
                    "_lap_order"
                ].dropna()
            )
        )

        lap_gain_values = []

        for lap_key in lap_keys:

            b = baseline_laps[
                baseline_laps[
                    "_lap_order"
                ]
                == lap_key
            ]

            c = current_laps[
                current_laps[
                    "_lap_order"
                ]
                == lap_key
            ]

            b_row = (
                b.iloc[0]
                if len(b)
                else None
            )

            c_row = (
                c.iloc[0]
                if len(c)
                else None
            )

            baseline_lap_speed = (
                numeric(
                    pd.Series(
                        [
                            b_row[
                                lap_speed_col
                            ]
                        ]
                    )
                ).iloc[0]
                if (
                    b_row is not None
                    and lap_speed_col
                    is not None
                )
                else np.nan
            )

            current_lap_speed = (
                numeric(
                    pd.Series(
                        [
                            c_row[
                                lap_speed_col
                            ]
                        ]
                    )
                ).iloc[0]
                if (
                    c_row is not None
                    and lap_speed_col
                    is not None
                )
                else np.nan
            )

            lap_speed_delta = (
                current_lap_speed
                - baseline_lap_speed
                if (
                    pd.notna(
                        current_lap_speed
                    )
                    and pd.notna(
                        baseline_lap_speed
                    )
                )
                else np.nan
            )

            if pd.notna(
                lap_speed_delta
            ):
                lap_gain_values.append(
                    float(
                        lap_speed_delta
                    )
                )

            baseline_lap_time = (
                get_scalar(
                    b_row,
                    [
                        lap_time_col
                    ],
                )
                if (
                    b_row is not None
                    and lap_time_col
                    is not None
                )
                else np.nan
            )

            current_lap_time = (
                get_scalar(
                    c_row,
                    [
                        lap_time_col
                    ],
                )
                if (
                    c_row is not None
                    and lap_time_col
                    is not None
                )
                else np.nan
            )

            lap_rows.append(
                {
                    "year":
                        int(
                            large_row[
                                "year"
                            ]
                        ),

                    "car_number":
                        large_row[
                            "car_number"
                        ],

                    "driver_name":
                        large_row[
                            "driver_name"
                        ],

                    "baseline_attempt_id":
                        baseline_id,

                    "current_attempt_id":
                        current_id,

                    "lap_order":
                        lap_key,

                    "baseline_lap_speed_mph":
                        baseline_lap_speed,

                    "current_lap_speed_mph":
                        current_lap_speed,

                    "lap_speed_delta_mph":
                        lap_speed_delta,

                    "baseline_lap_time_seconds":
                        baseline_lap_time,

                    "current_lap_time_seconds":
                        current_lap_time,

                    "baseline_source_report_lap_index":
                        (
                            b_row[
                                source_lap_col
                            ]
                            if (
                                b_row is not None
                                and source_lap_col
                                is not None
                            )
                            else np.nan
                        ),

                    "current_source_report_lap_index":
                        (
                            c_row[
                                source_lap_col
                            ]
                            if (
                                c_row is not None
                                and source_lap_col
                                is not None
                            )
                            else np.nan
                        ),
                }
            )

        # ====================================================
        # Improvement morphology
        # ====================================================

        lap_gain_values = [
            value
            for value
            in lap_gain_values
            if np.isfinite(
                value
            )
        ]

        lap_gain_count = len(
            lap_gain_values
        )

        positive_lap_gain_count = sum(
            value > 0
            for value
            in lap_gain_values
        )

        negative_lap_gain_count = sum(
            value < 0
            for value
            in lap_gain_values
        )

        if lap_gain_count:

            mean_lap_gain = float(
                np.mean(
                    lap_gain_values
                )
            )

            min_lap_gain = float(
                np.min(
                    lap_gain_values
                )
            )

            max_lap_gain = float(
                np.max(
                    lap_gain_values
                )
            )

            lap_gain_std = float(
                np.std(
                    lap_gain_values,
                    ddof=1,
                )
            ) if lap_gain_count > 1 else 0.0

        else:

            mean_lap_gain = np.nan
            min_lap_gain = np.nan
            max_lap_gain = np.nan
            lap_gain_std = np.nan

        if (
            lap_gain_count >= 3
            and positive_lap_gain_count
            == lap_gain_count
        ):

            morphology = (
                "BROAD_BASED_ALL_AVAILABLE_LAPS_FASTER"
            )

        elif (
            lap_gain_count >= 3
            and positive_lap_gain_count
            >= lap_gain_count - 1
        ):

            morphology = (
                "MOSTLY_BROAD_BASED_IMPROVEMENT"
            )

        elif (
            lap_gain_count >= 2
            and max_lap_gain
            > 2.0
            * max(
                abs(
                    mean_lap_gain
                ),
                0.05,
            )
        ):

            morphology = (
                "POSSIBLE_SINGLE_LAP_DOMINATED_IMPROVEMENT"
            )

        elif lap_gain_count:

            morphology = (
                "MIXED_LAP_PATTERN"
            )

        else:

            morphology = (
                "LAP_SPEED_EVIDENCE_UNAVAILABLE"
            )

        # ====================================================
        # Canonical/performance semantics
        # ====================================================

        baseline_status = get_scalar(
            baseline_attempt,
            [
                "result_status",
            ],
        )

        current_status = get_scalar(
            current_attempt,
            [
                "result_status",
            ],
        )

        baseline_class = get_scalar(
            baseline_attempt,
            [
                "attempt_class",
            ],
        )

        current_class = get_scalar(
            current_attempt,
            [
                "attempt_class",
            ],
        )

        baseline_counted = get_scalar(
            baseline_attempt,
            [
                "result_counted_at_session_end",
            ],
        )

        current_counted = get_scalar(
            current_attempt,
            [
                "result_counted_at_session_end",
            ],
        )

        baseline_speed = float(
            large_row[
                "baseline_speed_mph"
            ]
        )

        delta_speed = float(
            large_row[
                "target_speed_delta_vs_best_prior_mph"
            ]
        )

        current_speed = (
            baseline_speed
            + delta_speed
        )

        # ====================================================
        # Evidence flags
        # ====================================================

        baseline_status_suspicious = (
            str(
                baseline_status
            ).upper()
            not in [
                "VALID_RETAINED",
                "VALID_SUPERSEDED",
                "NAN",
                "NONE",
            ]
        )

        baseline_class_suspicious = (
            str(
                baseline_class
            ).upper()
            in [
                "PARTIAL",
                "FAILED",
                "RETIRED",
                "SECTION_ONLY",
                "C_SECTION_ONLY",
            ]
        )

        broad_based = (
            morphology
            in [
                "BROAD_BASED_ALL_AVAILABLE_LAPS_FASTER",
                "MOSTLY_BROAD_BASED_IMPROVEMENT",
            ]
        )

        baseline_below_year_median = bool(
            large_row.get(
                "baseline_below_year_median",
                False,
            )
        )

        if (
            broad_based
            and baseline_below_year_median
            and not baseline_status_suspicious
        ):

            preliminary_interpretation = (
                "CONSISTENT_WITH_LOW_BASELINE_RECOVERY"
            )

        elif baseline_status_suspicious:

            preliminary_interpretation = (
                "BASELINE_STATUS_MAY_EXPLAIN_LARGE_GAIN"
            )

        elif morphology == (
            "POSSIBLE_SINGLE_LAP_DOMINATED_IMPROVEMENT"
        ):

            preliminary_interpretation = (
                "LARGE_GAIN_MAY_BE_LAP_PATTERN_SPECIFIC"
            )

        else:

            preliminary_interpretation = (
                "MECHANISM_NOT_RESOLVED"
            )

        event_rows.append(
            {
                "year":
                    int(
                        large_row[
                            "year"
                        ]
                    ),

                "car_number":
                    large_row[
                        "car_number"
                    ],

                "driver_name":
                    large_row[
                        "driver_name"
                    ],

                "baseline_attempt_id":
                    baseline_id,

                "current_attempt_id":
                    current_id,

                "baseline_speed_mph":
                    baseline_speed,

                "current_speed_mph":
                    current_speed,

                "delta_speed_mph":
                    delta_speed,

                "baseline_below_year_median":
                    baseline_below_year_median,

                "seconds_since_baseline_attempt":
                    clean_value(
                        large_row.get(
                            "seconds_since_baseline_attempt",
                            np.nan,
                        )
                    ),

                "baseline_result_status":
                    clean_value(
                        baseline_status
                    ),

                "current_result_status":
                    clean_value(
                        current_status
                    ),

                "baseline_attempt_class":
                    clean_value(
                        baseline_class
                    ),

                "current_attempt_class":
                    clean_value(
                        current_class
                    ),

                "baseline_result_counted_at_session_end":
                    clean_value(
                        baseline_counted
                    ),

                "current_result_counted_at_session_end":
                    clean_value(
                        current_counted
                    ),

                "baseline_status_suspicious":
                    bool(
                        baseline_status_suspicious
                    ),

                "baseline_class_suspicious":
                    bool(
                        baseline_class_suspicious
                    ),

                "baseline_lap_rows":
                    len(
                        baseline_laps
                    ),

                "current_lap_rows":
                    len(
                        current_laps
                    ),

                "comparable_lap_speed_rows":
                    lap_gain_count,

                "positive_lap_gain_count":
                    positive_lap_gain_count,

                "negative_lap_gain_count":
                    negative_lap_gain_count,

                "mean_lap_speed_gain_mph":
                    mean_lap_gain,

                "min_lap_speed_gain_mph":
                    min_lap_gain,

                "max_lap_speed_gain_mph":
                    max_lap_gain,

                "std_lap_speed_gain_mph":
                    lap_gain_std,

                "lap_improvement_morphology":
                    morphology,

                "preliminary_evidence_interpretation":
                    preliminary_interpretation,

                "baseline_attempt_metadata_json":
                    serialize_selected(
                        baseline_attempt,
                        ATTEMPT_FIELDS,
                    ),

                "current_attempt_metadata_json":
                    serialize_selected(
                        current_attempt,
                        ATTEMPT_FIELDS,
                    ),

                "baseline_performance_context_json":
                    (
                        serialize_selected(
                            baseline_perf,
                            PERFORMANCE_CONTEXT_FIELDS,
                        )
                        if baseline_perf
                        is not None
                        else None
                    ),

                "current_performance_context_json":
                    (
                        serialize_selected(
                            current_perf,
                            PERFORMANCE_CONTEXT_FIELDS,
                        )
                        if current_perf
                        is not None
                        else None
                    ),

                "policy_version":
                    POLICY_VERSION,
            }
        )

        # ====================================================
        # Optional section audit
        # ====================================================

        if (
            sections is not None
            and "attempt_id"
            in sections.columns
        ):

            relevant_sections = sections[
                sections[
                    "attempt_id"
                ]
                .astype(str)
                .isin(
                    [
                        baseline_id,
                        current_id,
                    ]
                )
            ].copy()

            for _, sec in (
                relevant_sections.iterrows()
            ):

                section_rows.append(
                    {
                        "year":
                            int(
                                large_row[
                                    "year"
                                ]
                            ),

                        "car_number":
                            large_row[
                                "car_number"
                            ],

                        "driver_name":
                            large_row[
                                "driver_name"
                            ],

                        "attempt_role":
                            (
                                "BASELINE"
                                if str(
                                    sec[
                                        "attempt_id"
                                    ]
                                )
                                == baseline_id
                                else "CURRENT"
                            ),

                        "attempt_id":
                            sec[
                                "attempt_id"
                            ],

                        "section_record_json":
                            json.dumps(
                                {
                                    col:
                                        clean_value(
                                            sec[col]
                                        )
                                    for col
                                    in sections.columns
                                    if col
                                    != "attempt_id"
                                },
                                ensure_ascii=False,
                                sort_keys=True,
                                default=str,
                            ),
                    }
                )

    event_audit = pd.DataFrame(
        event_rows
    )

    lap_audit = pd.DataFrame(
        lap_rows
    )

    section_audit = pd.DataFrame(
        section_rows
    )

    # ========================================================
    # Cross-event diagnosis
    # ========================================================

    all_below_year_median = bool(
        event_audit[
            "baseline_below_year_median"
        ].all()
    )

    broad_based_count = int(
        event_audit[
            "lap_improvement_morphology"
        ]
        .isin(
            [
                "BROAD_BASED_ALL_AVAILABLE_LAPS_FASTER",
                "MOSTLY_BROAD_BASED_IMPROVEMENT",
            ]
        )
        .sum()
    )

    suspicious_status_count = int(
        event_audit[
            "baseline_status_suspicious"
        ].sum()
    )

    suspicious_class_count = int(
        event_audit[
            "baseline_class_suspicious"
        ].sum()
    )

    unresolved_count = int(
        (
            event_audit[
                "preliminary_evidence_interpretation"
            ]
            == "MECHANISM_NOT_RESOLVED"
        ).sum()
    )

    # ========================================================
    # QA
    # ========================================================

    checks = {
        "large_gain_event_rows_equal_4":
            len(
                event_audit
            )
            == 4,

        "baseline_attempt_ids_unique":
            not event_audit[
                "baseline_attempt_id"
            ].isna().any(),

        "current_attempt_ids_unique":
            not event_audit[
                "current_attempt_id"
            ].duplicated().any(),

        "all_current_attempts_found_canonical":
            all(
                str(x)
                in attempt_index.index
                for x
                in event_audit[
                    "current_attempt_id"
                ]
            ),

        "all_baseline_attempts_found_canonical":
            all(
                str(x)
                in attempt_index.index
                for x
                in event_audit[
                    "baseline_attempt_id"
                ]
            ),

        "all_delta_values_positive":
            (
                numeric(
                    event_audit[
                        "delta_speed_mph"
                    ]
                )
                > 0
            ).all(),

        "all_large_gain_baselines_below_year_median":
            all_below_year_median,

        "lap_audit_materialized":
            len(
                lap_audit
            )
            > 0,

        "event_interpretations_present":
            event_audit[
                "preliminary_evidence_interpretation"
            ].notna().all(),
    }

    policy_payload = {
        "phase":
            "5B-4",

        "policy_version":
            POLICY_VERSION,

        "event_count":
            len(
                event_audit
            ),

        "event_attempt_ids":
            sorted(
                event_audit[
                    "current_attempt_id"
                ]
                .astype(str)
                .tolist()
            ),

        "baseline_attempt_ids":
            sorted(
                event_audit[
                    "baseline_attempt_id"
                ]
                .astype(str)
                .tolist()
            ),
    }

    policy_hash = stable_hash(
        policy_payload
    )

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
                    "broad_based_improvement_events",

                "value":
                    broad_based_count,

                "status":
                    "INFO",
            },

            {
                "metric":
                    "baseline_status_suspicious_events",

                "value":
                    suspicious_status_count,

                "status":
                    "INFO",
            },

            {
                "metric":
                    "baseline_class_suspicious_events",

                "value":
                    suspicious_class_count,

                "status":
                    "INFO",
            },

            {
                "metric":
                    "unresolved_mechanism_events",

                "value":
                    unresolved_count,

                "status":
                    "INFO",
            },

            {
                "metric":
                    "lap_speed_column",

                "value":
                    (
                        lap_speed_col
                        if lap_speed_col
                        is not None
                        else "UNAVAILABLE"
                    ),

                "status":
                    "INFO",
            },

            {
                "metric":
                    "section_file_available",

                "value":
                    int(
                        sections is not None
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
    print("LARGE-GAIN EVENT SUMMARY")
    print("-" * 180)

    print(
        event_audit[
            [
                "year",
                "car_number",
                "driver_name",
                "baseline_speed_mph",
                "current_speed_mph",
                "delta_speed_mph",
                "baseline_result_status",
                "current_result_status",
                "baseline_attempt_class",
                "current_attempt_class",
                "comparable_lap_speed_rows",
                "positive_lap_gain_count",
                "negative_lap_gain_count",
                "mean_lap_speed_gain_mph",
                "lap_improvement_morphology",
                "preliminary_evidence_interpretation",
            ]
        ]
        .sort_values(
            "delta_speed_mph",
            ascending=False,
        )
        .to_string(
            index=False
        )
    )

    print()
    print("PER-LAP DIFFERENCES")
    print("-" * 160)

    if lap_audit.empty:

        print(
            "No lap evidence available."
        )

    else:

        print(
            lap_audit[
                [
                    "year",
                    "car_number",
                    "driver_name",
                    "baseline_attempt_id",
                    "current_attempt_id",
                    "lap_order",
                    "baseline_lap_speed_mph",
                    "current_lap_speed_mph",
                    "lap_speed_delta_mph",
                ]
            ]
            .sort_values(
                [
                    "year",
                    "car_number",
                    "lap_order",
                ]
            )
            .to_string(
                index=False
            )
        )

    print()
    print("CROSS-EVENT EVIDENCE")
    print("-" * 100)

    print(
        "All four baselines below year median:",
        all_below_year_median
    )

    print(
        "Broad-based improvement events:",
        broad_based_count,
        "/ 4"
    )

    print(
        "Suspicious baseline-status events:",
        suspicious_status_count,
        "/ 4"
    )

    print(
        "Suspicious baseline-class events:",
        suspicious_class_count,
        "/ 4"
    )

    print(
        "Unresolved mechanism events:",
        unresolved_count,
        "/ 4"
    )

    print()
    print("QA")
    print("-" * 120)

    print(
        qa.to_string(
            index=False
        )
    )

    # ========================================================
    # WRITE
    # ========================================================

    EVENT_AUDIT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    event_audit[
        "policy_hash"
    ] = policy_hash

    lap_audit[
        "policy_hash"
    ] = policy_hash

    if not section_audit.empty:
        section_audit[
            "policy_hash"
        ] = policy_hash

    event_audit.to_csv(
        EVENT_AUDIT_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    lap_audit.to_csv(
        LAP_AUDIT_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    section_audit.to_csv(
        SECTION_AUDIT_FILE,
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
        "# Large-Gain Event Evidence Audit V1"
    )

    report.append("")

    report.append(
        f"Events audited: `{len(event_audit)}`"
    )

    report.append("")

    report.append(
        "## Evidence questions"
    )

    report.append("")

    report.append(
        "- Was the baseline attempt canonically abnormal?"
    )

    report.append(
        "- Did improvement occur broadly across laps?"
    )

    report.append(
        "- Was the baseline already unusually slow relative to its year?"
    )

    report.append(
        "- Is the event consistent with recovery rather than ordinary weather-driven variation?"
    )

    report.append("")

    report.append(
        "## Cross-event results"
    )

    report.append("")

    report.append(
        f"- All baselines below year median: "
        f"`{all_below_year_median}`"
    )

    report.append(
        f"- Broad-based improvement events: "
        f"`{broad_based_count}/4`"
    )

    report.append(
        f"- Suspicious baseline-status events: "
        f"`{suspicious_status_count}/4`"
    )

    report.append(
        f"- Suspicious baseline-class events: "
        f"`{suspicious_class_count}/4`"
    )

    report.append(
        f"- Mechanism unresolved events: "
        f"`{unresolved_count}/4`"
    )

    report.append("")

    report.append(
        "## Interpretation boundary"
    )

    report.append("")

    report.append(
        "- No event was relabeled."
    )

    report.append(
        "- No recovery classifier was trained."
    )

    report.append(
        "- No row was removed from the frozen repeat-delta layer."
    )

    report.append(
        "- Preliminary interpretations are evidence diagnostics only."
    )

    report.append(
        "- Weather causality is not inferred from these comparisons."
    )

    report.append("")

    report.append(
        "## Status"
    )

    report.append("")

    if all_pass:

        report.append(
            "**LARGE_GAIN_EVENT_EVIDENCE_AUDIT_COMPLETE**"
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
            "LARGE_GAIN_EVENT_EVIDENCE_AUDIT_COMPLETE"
        )

    else:

        print(
            "FINAL STATUS: REVIEW_REQUIRED"
        )

    print("=" * 100)

    print()
    print(
        "NO EVENT LABEL WAS FROZEN."
    )

    print(
        "NO RECOVERY CLASSIFIER WAS TRAINED."
    )

    print(
        "NO DATA ROW WAS REMOVED."
    )

    print()
    print("OUTPUTS")

    print(
        EVENT_AUDIT_FILE
    )

    print(
        LAP_AUDIT_FILE
    )

    print(
        SECTION_AUDIT_FILE
    )

    print(
        QA_FILE
    )

    print(
        REPORT_FILE
    )


if __name__ == "__main__":
    main()
