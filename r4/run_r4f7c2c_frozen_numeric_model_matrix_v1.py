from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime, timezone
import csv
import json
import math
import hashlib

ROOT = Path(
    "/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈"
)

OUT = ROOT / "r4/output"

MANIFEST_PATH = (
    OUT /
    "r4f7b_latent_window_training_manifest_v1.csv"
)

ATTEMPT_PATH = (
    OUT /
    "r4p1_attempt_four_lap_panel_v1.csv"
)

HRRR_CONTEXT_PATH = (
    ROOT /
    "weather/output/performance_context_features.csv"
)

PTSC_PATH = (
    ROOT /
    "weather/evidence/ptsc/"
    "indy500_day1_track_temp_2020_2024_time_normalized.csv"
)

OUT_MATRIX = (
    OUT /
    "r4f7c2c_frozen_numeric_model_matrix_v1.csv"
)

OUT_DEVELOPMENT = (
    OUT /
    "r4f7c2c_development_numeric_matrix_v1.csv"
)

OUT_VALIDATION = (
    OUT /
    "r4f7c2c_2024_validation_numeric_matrix_v1.csv"
)

OUT_COVERAGE = (
    OUT /
    "r4f7c2c_numeric_matrix_coverage_v1.csv"
)

OUT_QA = (
    OUT /
    "r4f7c2c_numeric_model_matrix_qa_v1.csv"
)

OUT_CONTRACT = (
    OUT /
    "r4f7c2c_numeric_model_matrix_contract_v1.json"
)

OUT_REPORT = (
    OUT /
    "r4f7c2c_numeric_model_matrix_report_v1.json"
)


CORE_YEARS = {
    2020,
    2021,
    2023,
}

VALIDATION_YEAR = 2024


HRRR_FEATURES = [
    "forecast_temp_c",
    "forecast_dewpoint_c",
    "forecast_relative_humidity_pct",
    "forecast_wind_speed_10m_ms",
    "forecast_wind_direction_deg",
    "forecast_pressure_hpa",
    "forecast_gust_ms",
    "forecast_cloud_cover_pct",
    "forecast_shortwave_radiation_wm2",
]


INITIAL_THERMAL_FEATURES = [
    "ptsc_track_temp_c_past_safe",
    "ptsc_track_temp_slope_c_per_min_past_safe",
    "forecast_temp_c",
    "forecast_relative_humidity_pct",
    "forecast_wind_speed_10m_ms",
    "forecast_pressure_hpa",
    "forecast_gust_ms",
    "forecast_cloud_cover_pct",
    "forecast_shortwave_radiation_wm2",
]


def clean(v):
    if v is None:
        return ""
    return str(v).strip()


def num(v):
    s = clean(v)

    if not s:
        return None

    try:
        x = float(s)

        if math.isfinite(x):
            return x

    except Exception:
        pass

    return None


def truthy(v):
    return clean(v).lower() in {
        "1",
        "true",
        "yes",
        "y",
        "t",
    }


def year_int(v):
    x = num(v)

    if x is None:
        return None

    return int(x)


def parse_dt(v):
    s = clean(v)

    if not s:
        return None

    if s.endswith("Z"):
        s = s[:-1] + "+00:00"

    try:
        dt = datetime.fromisoformat(s)

    except Exception:
        return None

    if dt.tzinfo is None:

        dt = dt.replace(
            tzinfo=timezone.utc
        )

    return dt.astimezone(
        timezone.utc
    )


def iso(dt):
    if dt is None:
        return ""

    return (
        dt.astimezone(
            timezone.utc
        )
        .isoformat()
        .replace(
            "+00:00",
            "Z"
        )
    )


def read_csv(path):
    with path.open(
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as f:

        reader = csv.DictReader(f)

        return (
            reader.fieldnames or [],
            list(reader),
        )


def sha256(path):
    h = hashlib.sha256()

    with path.open("rb") as f:

        while True:

            block = f.read(
                1024 * 1024
            )

            if not block:
                break

            h.update(block)

    return h.hexdigest()


for path in [
    MANIFEST_PATH,
    ATTEMPT_PATH,
    HRRR_CONTEXT_PATH,
    PTSC_PATH,
]:

    if not path.exists():

        raise SystemExit(
            f"MISSING INPUT: {path}"
        )


manifest_fields, manifest = read_csv(
    MANIFEST_PATH
)

attempt_fields, attempts = read_csv(
    ATTEMPT_PATH
)

hrrr_fields, hrrr_rows = read_csv(
    HRRR_CONTEXT_PATH
)

ptsc_fields, ptsc_rows = read_csv(
    PTSC_PATH
)


required_hrrr = {
    "attempt_id",
    "performance_time_utc",
    "selected_issue_time_utc",
    "leakage_safe",
    *HRRR_FEATURES,
}

missing_hrrr_cols = sorted(
    required_hrrr
    -
    set(hrrr_fields)
)

if missing_hrrr_cols:

    raise SystemExit(
        "MISSING HRRR CONTEXT COLUMNS: "
        +
        ", ".join(
            missing_hrrr_cols
        )
    )


required_ptsc = {
    "year",
    "utc_datetime",
    "track_c",
}

missing_ptsc_cols = sorted(
    required_ptsc
    -
    set(ptsc_fields)
)

if missing_ptsc_cols:

    raise SystemExit(
        "MISSING PTSC COLUMNS: "
        +
        ", ".join(
            missing_ptsc_cols
        )
    )


print("=" * 148)
print("R4F7C2C — FROZEN NUMERIC MODEL MATRIX")
print("=" * 148)

print(
    f"Manifest rows: {len(manifest)}"
)

print(
    f"Attempt rows: {len(attempts)}"
)

print(
    f"HRRR context rows: {len(hrrr_rows)}"
)

print(
    f"PTSC rows: {len(ptsc_rows)}"
)


# =============================================================================
# Frozen 110-row universe
# =============================================================================

target_manifest = [
    r
    for r in manifest
    if (
        truthy(
            r.get(
                "model_eligible"
            )
        )
        and
        clean(
            r.get(
                "split_role"
            )
        )
        in {
            "DEVELOPMENT",
            "VALIDATION_ONLY",
        }
    )
]


target_ids = {
    clean(
        r.get(
            "attempt_id"
        )
    )
    for r in target_manifest
}


if len(
    target_ids
) != len(
    target_manifest
):

    raise SystemExit(
        "DUPLICATE ATTEMPT IDs IN FROZEN MANIFEST"
    )


# =============================================================================
# Attempt lookup
# =============================================================================

attempt_map = {}


for r in attempts:

    aid = clean(
        r.get(
            "attempt_id"
        )
    )

    if not aid:
        continue

    if aid in attempt_map:

        raise SystemExit(
            f"DUPLICATE ATTEMPT ID IN P1: {aid}"
        )

    attempt_map[
        aid
    ] = r


# =============================================================================
# HRRR context lookup
#
# Prefer direct attempt_id identity.
# If duplicate attempt IDs somehow exist, require exact performance time.
# =============================================================================

hrrr_by_attempt = defaultdict(
    list
)


for r in hrrr_rows:

    aid = clean(
        r.get(
            "attempt_id"
        )
    )

    if aid:

        hrrr_by_attempt[
            aid
        ].append(
            r
        )


def resolve_hrrr(
    attempt_id,
    attempt_time,
):

    candidates = hrrr_by_attempt.get(
        attempt_id,
        []
    )

    if not candidates:

        return None


    exact = [
        r
        for r in candidates
        if parse_dt(
            r.get(
                "performance_time_utc"
            )
        )
        ==
        attempt_time
    ]


    if len(exact) == 1:

        return exact[0]


    if len(exact) > 1:

        raise RuntimeError(
            f"MULTIPLE EXACT HRRR CONTEXT ROWS: "
            f"{attempt_id}"
        )


    if len(candidates) == 1:

        return candidates[0]


    raise RuntimeError(
        f"AMBIGUOUS HRRR CONTEXT JOIN: "
        f"{attempt_id}"
    )


# =============================================================================
# PTSC canonical timeline
#
# Frozen rule:
#   use latest observation at or before attempt time.
#
# No future observation may be used for current track-temperature level.
# Slope uses the two latest observations both <= attempt time.
# =============================================================================

ptsc_by_year = defaultdict(
    list
)


for r in ptsc_rows:

    year = year_int(
        r.get(
            "year"
        )
    )

    dt = parse_dt(
        r.get(
            "utc_datetime"
        )
    )

    track = num(
        r.get(
            "track_c"
        )
    )


    if (
        year is None
        or
        dt is None
        or
        track is None
    ):
        continue


    ptsc_by_year[
        year
    ].append({
        "time":
            dt,

        "track_c":
            track,

        "row":
            r,
    })


for year in ptsc_by_year:

    ptsc_by_year[
        year
    ].sort(
        key=lambda x:
            x[
                "time"
            ]
    )


def resolve_ptsc(
    year,
    attempt_time,
):

    timeline = ptsc_by_year.get(
        year,
        []
    )


    past = [
        x
        for x in timeline
        if x[
            "time"
        ]
        <= attempt_time
    ]


    if not past:

        return {
            "current":
                None,

            "previous":
                None,

            "age_minutes":
                None,

            "slope":
                None,

            "slope_minutes":
                None,
        }


    current = past[-1]

    previous = (
        past[-2]
        if len(
            past
        ) >= 2
        else None
    )


    age_minutes = (
        (
            attempt_time
            -
            current[
                "time"
            ]
        ).total_seconds()
        /
        60.0
    )


    slope = None
    slope_minutes = None


    if previous is not None:

        slope_minutes = (
            (
                current[
                    "time"
                ]
                -
                previous[
                    "time"
                ]
            ).total_seconds()
            /
            60.0
        )


        if slope_minutes > 0:

            slope = (
                current[
                    "track_c"
                ]
                -
                previous[
                    "track_c"
                ]
            ) / slope_minutes


    return {
        "current":
            current,

        "previous":
            previous,

        "age_minutes":
            age_minutes,

        "slope":
            slope,

        "slope_minutes":
            slope_minutes,
    }


# =============================================================================
# Assemble frozen model matrix
# =============================================================================

matrix = []


for m in target_manifest:

    aid = clean(
        m.get(
            "attempt_id"
        )
    )


    a = attempt_map.get(
        aid
    )

    if a is None:

        raise SystemExit(
            f"TARGET ATTEMPT NOT FOUND IN P1: {aid}"
        )


    year = year_int(
        a.get(
            "year"
        )
    )

    attempt_time = parse_dt(
        a.get(
            "time_point_utc"
        )
    )

    observed_speed = num(
        a.get(
            "four_lap_average_speed_mph"
        )
    )

    reference_speed = num(
        m.get(
            "reference_speed_mph"
        )
    )


    if (
        year is None
        or
        attempt_time is None
        or
        observed_speed is None
        or
        reference_speed is None
    ):

        raise SystemExit(
            f"INCOMPLETE FROZEN TARGET ROW: {aid}"
        )


    h = resolve_hrrr(
        aid,
        attempt_time,
    )


    ptsc = resolve_ptsc(
        year,
        attempt_time,
    )


    hrrr_joined = (
        h is not None
    )


    leakage_safe = (
        truthy(
            h.get(
                "leakage_safe"
            )
        )
        if h
        else False
    )


    selected_issue_time = (
        parse_dt(
            h.get(
                "selected_issue_time_utc"
            )
        )
        if h
        else None
    )


    issue_before_attempt = (
        selected_issue_time is not None
        and
        selected_issue_time
        <=
        attempt_time
    )


    current_ptsc = ptsc[
        "current"
    ]


    ptsc_available = (
        current_ptsc is not None
    )


    ptsc_past_safe = (
        ptsc_available
        and
        current_ptsc[
            "time"
        ]
        <=
        attempt_time
    )


    reference_residual = (
        observed_speed
        -
        reference_speed
    )


    row = {
        "attempt_id":
            aid,

        "year":
            year,

        "driver_name":
            clean(
                m.get(
                    "driver_name"
                )
            ),

        "driver_key":
            clean(
                m.get(
                    "driver_key"
                )
            ),

        "car_number":
            clean(
                m.get(
                    "car_number"
                )
            ),

        "car_attempt_index":
            clean(
                a.get(
                    "car_attempt_index"
                )
            ),

        "split_role":
            clean(
                m.get(
                    "split_role"
                )
            ),

        "dataset_role":
            clean(
                m.get(
                    "dataset_role"
                )
            ),

        "performance_time_utc":
            iso(
                attempt_time
            ),

        # ---------------------------------------------------------------------
        # Primary target
        # ---------------------------------------------------------------------

        "target_four_lap_average_speed_mph":
            observed_speed,

        "fast_friday_reference_mph":
            reference_speed,

        "fast_friday_reference_type":
            clean(
                m.get(
                    "reference_type"
                )
            ),

        "target_reference_residual_mph":
            reference_residual,

        # ---------------------------------------------------------------------
        # PTSC — strictly past-safe
        # ---------------------------------------------------------------------

        "ptsc_track_temp_c_past_safe":
            (
                current_ptsc[
                    "track_c"
                ]
                if current_ptsc
                else ""
            ),

        "ptsc_observation_time_utc":
            (
                iso(
                    current_ptsc[
                        "time"
                    ]
                )
                if current_ptsc
                else ""
            ),

        "ptsc_age_minutes":
            (
                ptsc[
                    "age_minutes"
                ]
                if ptsc[
                    "age_minutes"
                ]
                is not None
                else ""
            ),

        "ptsc_track_temp_slope_c_per_min_past_safe":
            (
                ptsc[
                    "slope"
                ]
                if ptsc[
                    "slope"
                ]
                is not None
                else ""
            ),

        "ptsc_slope_baseline_minutes":
            (
                ptsc[
                    "slope_minutes"
                ]
                if ptsc[
                    "slope_minutes"
                ]
                is not None
                else ""
            ),

        "ptsc_past_safe":
            ptsc_past_safe,

        # ---------------------------------------------------------------------
        # Leakage-safe HRRR context
        # ---------------------------------------------------------------------

        "hrrr_context_joined":
            hrrr_joined,

        "hrrr_leakage_safe":
            leakage_safe,

        "hrrr_selected_issue_time_utc":
            (
                clean(
                    h.get(
                        "selected_issue_time_utc"
                    )
                )
                if h
                else ""
            ),

        "hrrr_selected_issue_age_minutes":
            (
                num(
                    h.get(
                        "selected_issue_age_minutes"
                    )
                )
                if h
                else ""
            ),

        "hrrr_issue_before_attempt":
            issue_before_attempt,

        "hrrr_before_valid_time_utc":
            (
                clean(
                    h.get(
                        "before_valid_time_utc"
                    )
                )
                if h
                else ""
            ),

        "hrrr_after_valid_time_utc":
            (
                clean(
                    h.get(
                        "after_valid_time_utc"
                    )
                )
                if h
                else ""
            ),

        "hrrr_interpolation_weight_after":
            (
                num(
                    h.get(
                        "interpolation_weight_after"
                    )
                )
                if h
                else ""
            ),
    }


    for feature in HRRR_FEATURES:

        row[
            feature
        ] = (
            num(
                h.get(
                    feature
                )
            )
            if h
            else ""
        )


    # Useful circular representation.
    wind_direction = (
        num(
            h.get(
                "forecast_wind_direction_deg"
            )
        )
        if h
        else None
    )


    if wind_direction is not None:

        radians = math.radians(
            wind_direction
        )

        row[
            "forecast_wind_direction_sin"
        ] = math.sin(
            radians
        )

        row[
            "forecast_wind_direction_cos"
        ] = math.cos(
            radians
        )

    else:

        row[
            "forecast_wind_direction_sin"
        ] = ""

        row[
            "forecast_wind_direction_cos"
        ] = ""


    # -------------------------------------------------------------------------
    # Frozen row eligibility for the first model comparison.
    #
    # Do not discard rows just because PTSC is older than an arbitrary
    # threshold yet. Preserve age explicitly and evaluate sensitivity later.
    # -------------------------------------------------------------------------

    required_numeric = [
        row[
            "fast_friday_reference_mph"
        ],

        row[
            "target_four_lap_average_speed_mph"
        ],

        row[
            "ptsc_track_temp_c_past_safe"
        ],

        row[
            "forecast_temp_c"
        ],

        row[
            "forecast_relative_humidity_pct"
        ],

        row[
            "forecast_wind_speed_10m_ms"
        ],

        row[
            "forecast_pressure_hpa"
        ],

        row[
            "forecast_gust_ms"
        ],

        row[
            "forecast_cloud_cover_pct"
        ],

        row[
            "forecast_shortwave_radiation_wm2"
        ],
    ]


    numeric_complete = all(
        num(v) is not None
        for v in required_numeric
    )


    row[
        "initial_model_numeric_complete"
    ] = (
        numeric_complete
        and
        ptsc_past_safe
        and
        leakage_safe
        and
        issue_before_attempt
    )


    matrix.append(
        row
    )


matrix.sort(
    key=lambda r: (
        r[
            "year"
        ],
        r[
            "performance_time_utc"
        ],
        r[
            "driver_key"
        ],
    )
)


development = [
    r
    for r in matrix
    if r[
        "split_role"
    ]
    ==
    "DEVELOPMENT"
]


validation = [
    r
    for r in matrix
    if r[
        "split_role"
    ]
    ==
    "VALIDATION_ONLY"
]


# =============================================================================
# Coverage summary
# =============================================================================

coverage_rows = []


for year in [
    2020,
    2021,
    2023,
    2024,
]:

    subset = [
        r
        for r in matrix
        if r[
            "year"
        ] == year
    ]


    ages = [
        num(
            r[
                "ptsc_age_minutes"
            ]
        )
        for r in subset
    ]

    ages = [
        x
        for x in ages
        if x is not None
    ]


    coverage_rows.append({
        "year":
            year,

        "rows":
            len(
                subset
            ),

        "ptsc_available":
            sum(
                truthy(
                    r[
                        "ptsc_past_safe"
                    ]
                )
                for r in subset
            ),

        "ptsc_age_le_15m":
            sum(
                (
                    num(
                        r[
                            "ptsc_age_minutes"
                        ]
                    )
                    is not None
                )
                and
                (
                    num(
                        r[
                            "ptsc_age_minutes"
                        ]
                    )
                    <= 15
                )
                for r in subset
            ),

        "ptsc_age_le_30m":
            sum(
                (
                    num(
                        r[
                            "ptsc_age_minutes"
                        ]
                    )
                    is not None
                )
                and
                (
                    num(
                        r[
                            "ptsc_age_minutes"
                        ]
                    )
                    <= 30
                )
                for r in subset
            ),

        "ptsc_age_le_60m":
            sum(
                (
                    num(
                        r[
                            "ptsc_age_minutes"
                        ]
                    )
                    is not None
                )
                and
                (
                    num(
                        r[
                            "ptsc_age_minutes"
                        ]
                    )
                    <= 60
                )
                for r in subset
            ),

        "ptsc_median_age_minutes":
            (
                sorted(
                    ages
                )[
                    len(
                        ages
                    )
                    //
                    2
                ]
                if ages
                else ""
            ),

        "hrrr_joined":
            sum(
                truthy(
                    r[
                        "hrrr_context_joined"
                    ]
                )
                for r in subset
            ),

        "hrrr_leakage_safe":
            sum(
                truthy(
                    r[
                        "hrrr_leakage_safe"
                    ]
                )
                for r in subset
            ),

        "hrrr_issue_before_attempt":
            sum(
                truthy(
                    r[
                        "hrrr_issue_before_attempt"
                    ]
                )
                for r in subset
            ),

        "initial_model_numeric_complete":
            sum(
                truthy(
                    r[
                        "initial_model_numeric_complete"
                    ]
                )
                for r in subset
            ),
    })


# =============================================================================
# QA
# =============================================================================

duplicate_matrix_ids = (
    len(
        {
            r[
                "attempt_id"
            ]
            for r in matrix
        }
    )
    !=
    len(
        matrix
    )
)


future_ptsc_rows = [
    r
    for r in matrix
    if (
        clean(
            r[
                "ptsc_observation_time_utc"
            ]
        )
        and
        parse_dt(
            r[
                "ptsc_observation_time_utc"
            ]
        )
        >
        parse_dt(
            r[
                "performance_time_utc"
            ]
        )
    )
]


unsafe_issue_rows = [
    r
    for r in matrix
    if (
        clean(
            r[
                "hrrr_selected_issue_time_utc"
            ]
        )
        and
        parse_dt(
            r[
                "hrrr_selected_issue_time_utc"
            ]
        )
        >
        parse_dt(
            r[
                "performance_time_utc"
            ]
        )
    )
]


qa_rows = [
    {
        "metric":
            "frozen_matrix_rows",
        "value":
            len(
                matrix
            ),
        "expected":
            110,
        "status":
            (
                "PASS"
                if len(
                    matrix
                ) == 110
                else "FAIL"
            ),
    },

    {
        "metric":
            "development_rows",
        "value":
            len(
                development
            ),
        "expected":
            104,
        "status":
            (
                "PASS"
                if len(
                    development
                ) == 104
                else "FAIL"
            ),
    },

    {
        "metric":
            "validation_rows",
        "value":
            len(
                validation
            ),
        "expected":
            6,
        "status":
            (
                "PASS"
                if len(
                    validation
                ) == 6
                else "FAIL"
            ),
    },

    {
        "metric":
            "unique_attempt_ids",
        "value":
            not duplicate_matrix_ids,
        "expected":
            True,
        "status":
            (
                "PASS"
                if not duplicate_matrix_ids
                else "FAIL"
            ),
    },

    {
        "metric":
            "hrrr_join_coverage",
        "value":
            sum(
                truthy(
                    r[
                        "hrrr_context_joined"
                    ]
                )
                for r in matrix
            ),
        "expected":
            110,
        "status":
            (
                "PASS"
                if sum(
                    truthy(
                        r[
                            "hrrr_context_joined"
                        ]
                    )
                    for r in matrix
                ) == 110
                else "FAIL"
            ),
    },

    {
        "metric":
            "hrrr_leakage_safe_rows",
        "value":
            sum(
                truthy(
                    r[
                        "hrrr_leakage_safe"
                    ]
                )
                for r in matrix
            ),
        "expected":
            110,
        "status":
            (
                "PASS"
                if sum(
                    truthy(
                        r[
                            "hrrr_leakage_safe"
                        ]
                    )
                    for r in matrix
                ) == 110
                else "FAIL"
            ),
    },

    {
        "metric":
            "hrrr_issue_never_future",
        "value":
            len(
                unsafe_issue_rows
            ),
        "expected":
            0,
        "status":
            (
                "PASS"
                if not unsafe_issue_rows
                else "FAIL"
            ),
    },

    {
        "metric":
            "ptsc_never_future",
        "value":
            len(
                future_ptsc_rows
            ),
        "expected":
            0,
        "status":
            (
                "PASS"
                if not future_ptsc_rows
                else "FAIL"
            ),
    },

    {
        "metric":
            "ptsc_available_rows",
        "value":
            sum(
                truthy(
                    r[
                        "ptsc_past_safe"
                    ]
                )
                for r in matrix
            ),
        "expected":
            ">=100",
        "status":
            (
                "PASS"
                if sum(
                    truthy(
                        r[
                            "ptsc_past_safe"
                        ]
                    )
                    for r in matrix
                ) >= 100
                else "WARN"
            ),
    },

    {
        "metric":
            "initial_numeric_complete_rows",
        "value":
            sum(
                truthy(
                    r[
                        "initial_model_numeric_complete"
                    ]
                )
                for r in matrix
            ),
        "expected":
            ">=100",
        "status":
            (
                "PASS"
                if sum(
                    truthy(
                        r[
                            "initial_model_numeric_complete"
                        ]
                    )
                    for r in matrix
                ) >= 100
                else "WARN"
            ),
    },

    {
        "metric":
            "matrix_only_no_model_fit",
        "value":
            True,
        "expected":
            True,
        "status":
            "PASS",
    },
]


# =============================================================================
# Save
# =============================================================================

fieldnames = list(
    matrix[0].keys()
)


def write_rows(
    path,
    rows,
):

    with path.open(
        "w",
        encoding="utf-8",
        newline=""
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames
        )

        writer.writeheader()

        writer.writerows(
            rows
        )


write_rows(
    OUT_MATRIX,
    matrix,
)

write_rows(
    OUT_DEVELOPMENT,
    development,
)

write_rows(
    OUT_VALIDATION,
    validation,
)


with OUT_COVERAGE.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=list(
            coverage_rows[0].keys()
        )
    )

    writer.writeheader()

    writer.writerows(
        coverage_rows
    )


with OUT_QA.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=[
            "metric",
            "value",
            "expected",
            "status",
        ]
    )

    writer.writeheader()

    writer.writerows(
        qa_rows
    )


contract = {
    "phase":
        "R4F7C2C",

    "status":
        "R4F7C2C_FROZEN_NUMERIC_MODEL_MATRIX_READY",

    "rows": {
        "all":
            len(
                matrix
            ),

        "development":
            len(
                development
            ),

        "validation":
            len(
                validation
            ),
    },

    "split_policy": {
        "development":
            [
                2020,
                2021,
                2023,
            ],

        "validation_only":
            [
                2024,
            ],

        "2022":
            "DEGRADED_CHRONOLOGY_VALIDATION_NOT_IN_MATRIX",

        "2025":
            "TECHNICAL_REGIME_TRANSFER_NOT_IN_MAIN_MATRIX",
    },

    "target":
        "target_four_lap_average_speed_mph",

    "reference":
        "fast_friday_reference_mph",

    "secondary_target":
        "target_reference_residual_mph",

    "ptsc_join_policy":
        (
            "Same year. Latest PTSC observation with "
            "utc_datetime <= performance_time_utc. "
            "No future PTSC interpolation."
        ),

    "ptsc_slope_policy":
        (
            "Slope computed from the two latest PTSC observations "
            "that both occurred no later than performance time."
        ),

    "hrrr_join_policy":
        (
            "Direct attempt_id join to "
            "weather/output/performance_context_features.csv. "
            "Require leakage_safe=true and selected_issue_time_utc "
            "<= performance_time_utc."
        ),

    "initial_thermal_feature_set":
        INITIAL_THERMAL_FEATURES,

    "wind_direction_policy":
        (
            "Raw direction retained for provenance; "
            "sin/cos transformation provided for modeling."
        ),

    "forbidden_same_attempt_predictor_features":
        [
            "lap1_speed_mph",
            "lap2_speed_mph",
            "lap3_speed_mph",
            "lap4_speed_mph",
            "lap1_to_lap4_delta_mph",
            "lap1_to_lap2_delta_mph",
            "lap2_to_lap3_delta_mph",
            "lap3_to_lap4_delta_mph",
            "four_lap_total_seconds",
        ],

    "important_boundary":
        (
            "Lap/run-shape measurements are outcomes for this attempt "
            "and are not external predictors of the same attempt's "
            "four-lap average speed."
        ),
}


OUT_CONTRACT.write_text(
    json.dumps(
        contract,
        indent=2,
        ensure_ascii=False
    ),
    encoding="utf-8"
)


report = {
    "phase":
        "R4F7C2C",

    "status":
        "R4F7C2C_FROZEN_NUMERIC_MODEL_MATRIX_READY",

    "coverage_by_year":
        coverage_rows,

    "reference_type_distribution":
        dict(
            Counter(
                r[
                    "fast_friday_reference_type"
                ]
                for r in development
            )
        ),

    "matrix_hash":
        sha256(
            OUT_MATRIX
        ),

    "development_hash":
        sha256(
            OUT_DEVELOPMENT
        ),

    "validation_hash":
        sha256(
            OUT_VALIDATION
        ),

    "input_hashes": {
        str(
            MANIFEST_PATH.relative_to(
                ROOT
            )
        ):
            sha256(
                MANIFEST_PATH
            ),

        str(
            ATTEMPT_PATH.relative_to(
                ROOT
            )
        ):
            sha256(
                ATTEMPT_PATH
            ),

        str(
            HRRR_CONTEXT_PATH.relative_to(
                ROOT
            )
        ):
            sha256(
                HRRR_CONTEXT_PATH
            ),

        str(
            PTSC_PATH.relative_to(
                ROOT
            )
        ):
            sha256(
                PTSC_PATH
            ),
    },

    "next_phase":
        (
            "R4F7C3: frozen baseline model comparison using "
            "development years only, with year-held-out diagnostics. "
            "2024 remains untouched during model selection."
        ),
}


OUT_REPORT.write_text(
    json.dumps(
        report,
        indent=2,
        ensure_ascii=False
    ),
    encoding="utf-8"
)


# =============================================================================
# Console
# =============================================================================

print()
print("=" * 148)
print("FROZEN NUMERIC MATRIX")
print("=" * 148)

print(
    f"All rows: {len(matrix)}"
)

print(
    f"Development rows: {len(development)}"
)

print(
    f"2024 validation rows: {len(validation)}"
)


print()
print("=" * 148)
print("WEATHER COVERAGE BY YEAR")
print("=" * 148)

for r in coverage_rows:

    print(
        f"{r['year']} | "
        f"rows={r['rows']:3d} | "
        f"PTSC={r['ptsc_available']:3d} | "
        f"<=15m={r['ptsc_age_le_15m']:3d} | "
        f"<=30m={r['ptsc_age_le_30m']:3d} | "
        f"<=60m={r['ptsc_age_le_60m']:3d} | "
        f"median_age={r['ptsc_median_age_minutes']} | "
        f"HRRR={r['hrrr_joined']:3d} | "
        f"leak_safe={r['hrrr_leakage_safe']:3d} | "
        f"COMPLETE={r['initial_model_numeric_complete']:3d}"
    )


print()
print("=" * 148)
print("REFERENCE RESIDUAL SUMMARY")
print("=" * 148)

for year in [
    2020,
    2021,
    2023,
    2024,
]:

    vals = [
        r[
            "target_reference_residual_mph"
        ]
        for r in matrix
        if r[
            "year"
        ] == year
    ]

    if not vals:
        continue

    vals_sorted = sorted(
        vals
    )

    mean = (
        sum(
            vals
        )
        /
        len(
            vals
        )
    )

    median = vals_sorted[
        len(
            vals_sorted
        )
        //
        2
    ]

    print(
        f"{year} | "
        f"n={len(vals):3d} | "
        f"mean={mean:+.4f} | "
        f"median={median:+.4f} | "
        f"min={min(vals):+.4f} | "
        f"max={max(vals):+.4f}"
    )


print()
print("=" * 148)
print("INITIAL MODEL FEATURE SET")
print("=" * 148)

for feature in INITIAL_THERMAL_FEATURES:

    coverage = sum(
        num(
            r.get(
                feature
            )
        )
        is not None
        for r in matrix
    )

    print(
        f"{feature:54s} | "
        f"{coverage:3d}/110"
    )


fails = [
    r
    for r in qa_rows
    if r[
        "status"
    ] == "FAIL"
]

warns = [
    r
    for r in qa_rows
    if r[
        "status"
    ] == "WARN"
]


print()
print(
    f"QA: "
    f"{len(qa_rows)-len(fails)-len(warns)} PASS | "
    f"{len(warns)} WARN | "
    f"{len(fails)} FAIL"
)

for r in warns:

    print(
        f"WARN | "
        f"{r['metric']} | "
        f"value={r['value']} | "
        f"expected={r['expected']}"
    )


if fails:

    for r in fails:

        print(
            f"FAIL | "
            f"{r['metric']} | "
            f"value={r['value']} | "
            f"expected={r['expected']}"
        )

    raise SystemExit(1)


print()
print("OUTPUTS")
print(
    OUT_MATRIX.relative_to(ROOT)
)
print(
    OUT_DEVELOPMENT.relative_to(ROOT)
)
print(
    OUT_VALIDATION.relative_to(ROOT)
)
print(
    OUT_COVERAGE.relative_to(ROOT)
)
print(
    OUT_QA.relative_to(ROOT)
)
print(
    OUT_CONTRACT.relative_to(ROOT)
)
print(
    OUT_REPORT.relative_to(ROOT)
)

print()
print(
    "R4F7C2C_FROZEN_NUMERIC_MODEL_MATRIX_READY"
)
