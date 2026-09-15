from pathlib import Path
import pandas as pd

ROOT = Path("/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈")
OUT = ROOT / "r6_regime_extension/output"
OUT.mkdir(parents=True, exist_ok=True)

TARGET_YEARS = [2018, 2019, 2025, 2026]

SKIP_DIRS = {
    ".git",
    "__pycache__",
    ".venv",
    "venv",
}

interesting_name_tokens = [
    "attempt",
    "qual",
    "result",
    "timing",
    "chronology",
    "weather",
    "track",
    "ptsc",
    "hrrr",
    "indy",
    "day1",
    "fast",
    "friday",
]

def should_skip(path):
    return any(part in SKIP_DIRS for part in path.parts)

def filename_relevance(path):
    n = path.name.lower()
    return any(tok in n for tok in interesting_name_tokens)

def detect_year_columns(df):
    found = []

    for c in df.columns:
        cl = str(c).lower()

        if (
            cl == "year"
            or "year" in cl
            or "date" in cl
            or "time" in cl
            or "session" in cl
        ):
            found.append(c)

    return found

def scan_csv(path):

    try:
        df = pd.read_csv(
            path,
            nrows=5000,
            low_memory=False
        )

    except Exception as e:

        return [{
            "path": str(path.relative_to(ROOT)),
            "file_type": "csv",
            "status": "READ_ERROR",
            "error": str(e),
        }]

    year_cols = detect_year_columns(df)

    year_hits = {
        y: False
        for y in TARGET_YEARS
    }

    year_counts = {
        y: 0
        for y in TARGET_YEARS
    }

    # --------------------------------------------------------
    # First inspect likely year/date/time columns
    # --------------------------------------------------------

    for c in year_cols:

        s = df[c].astype(str)

        for y in TARGET_YEARS:

            mask = s.str.contains(
                str(y),
                regex=False,
                na=False
            )

            if mask.any():

                year_hits[y] = True
                year_counts[y] += int(
                    mask.sum()
                )

    # --------------------------------------------------------
    # Fallback:
    # inspect whole dataframe only for relevant filenames
    # --------------------------------------------------------

    if (
        filename_relevance(path)
        and not any(year_hits.values())
    ):

        text = df.astype(str)

        for y in TARGET_YEARS:

            total_count = 0

            for c in text.columns:

                total_count += int(
                    text[c]
                    .str.contains(
                        str(y),
                        regex=False,
                        na=False
                    )
                    .sum()
                )

            if total_count > 0:

                year_hits[y] = True
                year_counts[y] = total_count

    # --------------------------------------------------------
    # Signals
    # --------------------------------------------------------

    likely_attempt_cols = [
        c
        for c in df.columns
        if any(
            tok in str(c).lower()
            for tok in [
                "attempt",
                "speed",
                "lap",
                "driver",
                "car",
                "run",
                "qual",
            ]
        )
    ]

    likely_time_cols = [
        c
        for c in df.columns
        if any(
            tok in str(c).lower()
            for tok in [
                "time",
                "timestamp",
                "datetime",
                "utc",
                "local",
            ]
        )
    ]

    likely_weather_cols = [
        c
        for c in df.columns
        if any(
            tok in str(c).lower()
            for tok in [
                "track_c",
                "track_temp",
                "ambient",
                "temp",
                "wind",
                "gust",
                "humidity",
                "pressure",
                "shortwave",
                "cloud",
                "density",
            ]
        )
    ]

    return [{
        "path":
            str(path.relative_to(ROOT)),

        "file_type":
            "csv",

        "status":
            "OK",

        "rows_sampled":
            len(df),

        "total_columns":
            len(df.columns),

        "filename_relevant":
            filename_relevance(path),

        "year_columns":
            "|".join(
                map(str, year_cols)
            ),

        "attempt_like_columns":
            "|".join(
                map(str, likely_attempt_cols)
            ),

        "time_like_columns":
            "|".join(
                map(str, likely_time_cols)
            ),

        "weather_like_columns":
            "|".join(
                map(str, likely_weather_cols)
            ),

        **{
            f"has_{y}":
                year_hits[y]
            for y in TARGET_YEARS
        },

        **{
            f"hits_{y}":
                year_counts[y]
            for y in TARGET_YEARS
        },
    }]

# ============================================================
# scan repo
# ============================================================

all_rows = []

for path in ROOT.rglob("*"):

    if should_skip(path):
        continue

    if not path.is_file():
        continue

    if path.suffix.lower() == ".csv":

        all_rows.extend(
            scan_csv(path)
        )

audit = pd.DataFrame(all_rows)

OUTFILE = (
    OUT /
    "existing_regime_asset_audit_v1.csv"
)

audit.to_csv(
    OUTFILE,
    index=False
)

# ============================================================
# report
# ============================================================

print("=" * 150)
print("PART 1 — EXISTING REGIME ASSET AUDIT")
print("=" * 150)

print(
    "CSV FILES SCANNED =",
    len(audit)
)

for year in TARGET_YEARS:

    col = f"has_{year}"

    if col not in audit.columns:
        continue

    hits = audit[
        audit[col].fillna(False)
    ].copy()

    print("\nYEAR:", year)

    print(
        "FILES WITH YEAR EVIDENCE =",
        len(hits)
    )

    if not hits.empty:

        show = [
            "path",
            "rows_sampled",
            "attempt_like_columns",
            "time_like_columns",
            "weather_like_columns",
            f"hits_{year}",
        ]

        show = [
            c
            for c in show
            if c in hits.columns
        ]

        print(
            hits[show]
            .sort_values(
                f"hits_{year}",
                ascending=False
            )
            .head(30)
            .to_string(index=False)
        )

print(
    "\n"
    + "=" * 150
)

print(
    "PART 2 — HIGH-VALUE CANDIDATE FILES"
)

print(
    "=" * 150
)

candidate_mask = pd.Series(
    False,
    index=audit.index
)

for year in TARGET_YEARS:

    col = f"has_{year}"

    if col in audit.columns:

        candidate_mask |= (
            audit[col]
            .fillna(False)
        )

candidates = audit[
    candidate_mask
].copy()

if not candidates.empty:

    candidates[
        "attempt_signal"
    ] = (
        candidates[
            "attempt_like_columns"
        ]
        .fillna("")
        .str.len()
        > 0
    )

    candidates[
        "time_signal"
    ] = (
        candidates[
            "time_like_columns"
        ]
        .fillna("")
        .str.len()
        > 0
    )

    candidates[
        "weather_signal"
    ] = (
        candidates[
            "weather_like_columns"
        ]
        .fillna("")
        .str.len()
        > 0
    )

    candidates[
        "signal_score"
    ] = (
        candidates[
            "attempt_signal"
        ].astype(int)
        +
        candidates[
            "time_signal"
        ].astype(int)
        +
        candidates[
            "weather_signal"
        ].astype(int)
    )

    show = [
        "path",
        "signal_score",
        "attempt_signal",
        "time_signal",
        "weather_signal",
        "has_2018",
        "has_2019",
        "has_2025",
        "has_2026",
    ]

    show = [
        c
        for c in show
        if c in candidates.columns
    ]

    print(
        candidates[show]
        .sort_values(
            [
                "signal_score",
                "path"
            ],
            ascending=[
                False,
                True
            ]
        )
        .head(50)
        .to_string(index=False)
    )

else:

    print(
        "NO EXISTING TARGET-YEAR CSV ASSETS FOUND"
    )

print("\nOUTPUT:")
print(
    OUTFILE.relative_to(ROOT)
)

print(
    "\nR6_EXISTING_REGIME_ASSET_AUDIT_V1_COMPLETE"
)
