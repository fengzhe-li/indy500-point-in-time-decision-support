from pathlib import Path
import pandas as pd

ROOTS = [
    Path("weather"),
    Path("data"),
    Path("r5"),
    Path("r5_2"),
]

OUT = Path(
    "weather/output/v2c_wind_diagnostic/"
    "v2c_wind_artifact_discovery_v1.txt"
)

KEYWORDS = [
    "wind",
    "gust",
    "weather",
    "metar",
    "asos",
    "noaa",
    "iem",
    "observation",
    "ambient",
]

lines = []

def add(x=""):
    lines.append(str(x))


add("=" * 100)
add("INDY 500 V2-C WIND EVIDENCE DISCOVERY")
add("=" * 100)

found = []

for root in ROOTS:

    if not root.exists():
        continue

    for p in root.rglob("*"):

        if not p.is_file():
            continue

        low = str(p).lower()

        if any(
            k in low
            for k in KEYWORDS
        ):
            found.append(p)


add()
add("CANDIDATE FILES")
add("-" * 100)

for p in sorted(
    set(found),
    key=lambda x: str(x)
):

    add(str(p))

    if p.suffix.lower() == ".csv":

        try:
            df = pd.read_csv(
                p,
                nrows=5
            )

            wind_cols = [
                c for c in df.columns
                if any(
                    k in str(c).lower()
                    for k in [
                        "wind",
                        "gust",
                        "speed",
                        "direction",
                        "time",
                        "year",
                        "attempt",
                    ]
                )
            ]

            add(
                f"  columns of interest: {wind_cols}"
            )

        except Exception as e:

            add(
                f"  [could not inspect CSV: {e}]"
            )


# ------------------------------------------------------------------
# Also scan CSV headers even when filename itself does not mention wind.
# ------------------------------------------------------------------

add()
add("=" * 100)
add("CSV FILES WITH WIND/GUST COLUMNS")
add("=" * 100)

header_hits = []

for root in ROOTS:

    if not root.exists():
        continue

    for p in root.rglob("*.csv"):

        try:
            df = pd.read_csv(
                p,
                nrows=3
            )
        except Exception:
            continue

        cols = list(df.columns)

        wind_cols = [
            c for c in cols
            if (
                "wind" in str(c).lower()
                or
                "gust" in str(c).lower()
            )
        ]

        if wind_cols:

            header_hits.append(
                (
                    str(p),
                    df.shape[1],
                    cols,
                    wind_cols,
                )
            )


for path, ncols, cols, wind_cols in sorted(
    header_hits,
    key=lambda x: x[0]
):

    add()
    add(path)
    add(
        f"  total columns: {ncols}"
    )
    add(
        f"  wind/gust columns: {wind_cols}"
    )

    context_cols = [
        c for c in cols
        if any(
            k in str(c).lower()
            for k in [
                "year",
                "time",
                "date",
                "attempt",
                "session",
                "source",
                "station",
                "latitude",
                "longitude",
                "wind",
                "gust",
            ]
        )
    ]

    add(
        f"  context columns: {context_cols}"
    )


summary = "\n".join(lines)

OUT.write_text(
    summary,
    encoding="utf-8"
)

print(summary)

print()
print("=" * 100)
print("OUTPUT")
print("=" * 100)
print(OUT)
print()
print("DONE")
