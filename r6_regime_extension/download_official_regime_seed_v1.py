from pathlib import Path
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
import json

ROOT = Path("/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈")
OUT = ROOT / "r6_regime_extension/evidence/official_results"
OUT.mkdir(parents=True, exist_ok=True)

SOURCES = {
    2018: {
        "url":
        "https://www.indycar.com/results/ntt-indycar-series/2018/102nd-running-of-the-indianapolis-500/qualifications---day-1",

        "session":
        "Qualifications - Day 1",

        "technical_regime":
        "UNIVERSAL_AERO_PRE_AEROSCREEN",

        "qualifying_format_regime":
        "DAY1_REPEAT_ATTEMPTS_ALLOWED",
    },

    2019: {
        "url":
        "https://www.indycar.com/results/ntt-indycar-series/2019/103rd-running-of-the-indianapolis-500/qualifications---day-1",

        "session":
        "Qualifications - Day 1",

        "technical_regime":
        "UNIVERSAL_AERO_PRE_AEROSCREEN",

        "qualifying_format_regime":
        "DAY1_REPEAT_ATTEMPTS_ALLOWED",
    },

    2025: {
        "url":
        "https://www.indycar.com/results/ntt-indycar-series/2025/109th-running-of-the-indianapolis-500/qualifications---day-1",

        "session":
        "Qualifications - Day 1",

        "technical_regime":
        "AEROSCREEN_HYBRID",

        "qualifying_format_regime":
        "DAY1_REPEAT_ATTEMPTS_ALLOWED",
    },

    2026: {
        "url":
        "https://www.indycar.com/results/ntt-indycar-series/2026/110th-running-of-the-indianapolis-500/combined-qualifying",

        "session":
        "Combined Qualifying",

        "technical_regime":
        "AEROSCREEN_HYBRID",

        "qualifying_format_regime":
        "RAIN_COMPRESSED_INITIAL_ONE_ATTEMPT",
    },
}

HEADERS = {
    "User-Agent":
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 Chrome/153 Safari/537.36"
}

def normalize_columns(df):
    cols = []

    for c in df.columns:
        if isinstance(c, tuple):
            c = " ".join(
                str(x)
                for x in c
                if str(x) != "nan"
            )

        c = str(c).strip()
        c = re.sub(r"\s+", " ", c)
        cols.append(c)

    df = df.copy()
    df.columns = cols

    return df


def score_qual_table(df):
    cols = [
        c.lower()
        for c in df.columns
    ]

    score = 0

    wanted = [
        "driver",
        "lap 1",
        "lap 2",
        "lap 3",
        "lap 4",
        "average speed",
    ]

    for token in wanted:
        if any(
            token in c
            for c in cols
        ):
            score += 1

    return score


def find_best_table(url):

    html = requests.get(
        url,
        headers=HEADERS,
        timeout=30
    )

    html.raise_for_status()

    raw_html = html.text

    tables = pd.read_html(
        raw_html
    )

    candidates = []

    for i, t in enumerate(tables):
        t = normalize_columns(t)

        candidates.append({
            "index": i,
            "score": score_qual_table(t),
            "rows": len(t),
            "cols": len(t.columns),
            "table": t,
        })

    candidates.sort(
        key=lambda x: (
            x["score"],
            x["rows"]
        ),
        reverse=True
    )

    return raw_html, candidates


manifest = []
canonical_rows = []

for year, meta in SOURCES.items():

    print("=" * 120)
    print("YEAR", year)
    print("=" * 120)

    try:
        html, candidates = find_best_table(
            meta["url"]
        )

    except Exception as e:
        print("DOWNLOAD/PARSE ERROR:", e)

        manifest.append({
            "year": year,
            "url": meta["url"],
            "status": "ERROR",
            "error": str(e),
        })

        continue

    html_file = (
        OUT /
        f"{year}_official_results_page.html"
    )

    html_file.write_text(
        html,
        encoding="utf-8"
    )

    print(
        "HTML saved:",
        html_file.relative_to(ROOT)
    )

    print("\nTOP TABLE CANDIDATES:")

    for c in candidates[:5]:
        print(
            "index=",
            c["index"],
            "score=",
            c["score"],
            "rows=",
            c["rows"],
            "cols=",
            c["cols"],
        )

        print(
            list(c["table"].columns)
        )

    if not candidates:
        manifest.append({
            "year": year,
            "url": meta["url"],
            "status": "NO_TABLES",
        })
        continue

    best = candidates[0]

    best_df = best["table"].copy()

    raw_csv = (
        OUT /
        f"{year}_official_best_table_raw.csv"
    )

    best_df.to_csv(
        raw_csv,
        index=False
    )

    print(
        "\nBEST TABLE:",
        raw_csv.relative_to(ROOT)
    )

    print(
        best_df.head(10)
        .to_string(index=False)
    )

    # --------------------------------------------------------
    # Canonicalize obvious final four-lap result columns
    # --------------------------------------------------------

    colmap = {}

    for c in best_df.columns:

        cl = c.lower()

        if cl == "rank":
            colmap["rank"] = c

        elif cl in [
            "no.",
            "no",
            "car",
            "car no."
        ]:
            colmap["car_number"] = c

        elif "driver" in cl:
            colmap["driver_name"] = c

        elif "team" in cl:
            colmap["team_name"] = c

        elif "lap 1 time" in cl:
            colmap["lap1_time_s"] = c

        elif "lap 2 time" in cl:
            colmap["lap2_time_s"] = c

        elif "lap 3 time" in cl:
            colmap["lap3_time_s"] = c

        elif "lap 4 time" in cl:
            colmap["lap4_time_s"] = c

        elif "total time" in cl:
            colmap["total_time"] = c

        elif "average speed" in cl:
            colmap["four_lap_average_speed_mph"] = c

    print("\nCOLUMN MAP:")
    print(colmap)

    required = [
        "driver_name",
        "lap1_time_s",
        "lap2_time_s",
        "lap3_time_s",
        "lap4_time_s",
        "four_lap_average_speed_mph",
    ]

    missing = [
        x
        for x in required
        if x not in colmap
    ]

    if missing:

        print(
            "CANONICALIZATION PARTIAL; missing:",
            missing
        )

        manifest.append({
            "year": year,
            "url": meta["url"],
            "status": "TABLE_FOUND_PARTIAL",
            "table_index": best["index"],
            "table_score": best["score"],
            "rows": len(best_df),
            "missing_required":
                "|".join(missing),
        })

        continue

    canon = pd.DataFrame()

    canon["year"] = year
    canon["session"] = meta["session"]

    canon["technical_regime"] = (
        meta["technical_regime"]
    )

    canon[
        "qualifying_format_regime"
    ] = meta[
        "qualifying_format_regime"
    ]

    for dst, src in colmap.items():
        canon[dst] = best_df[src]

    # numeric cleanup
    numeric_cols = [
        "rank",
        "lap1_time_s",
        "lap2_time_s",
        "lap3_time_s",
        "lap4_time_s",
        "four_lap_average_speed_mph",
    ]

    for c in numeric_cols:
        if c in canon.columns:
            canon[c] = pd.to_numeric(
                canon[c],
                errors="coerce"
            )

    if "car_number" in canon.columns:
        canon["car_number"] = (
            canon["car_number"]
            .astype(str)
            .str.strip()
        )

    canon["source_url"] = meta["url"]

    canon[
        "source_semantics"
    ] = (
        "official displayed qualifying result; "
        "not assumed to represent all attempts"
    )

    canon[
        "safe_as_repeat_attempt_inventory"
    ] = False

    canon[
        "safe_as_final_four_lap_result"
    ] = True

    canonical_rows.append(
        canon
    )

    canon_file = (
        OUT /
        f"{year}_official_final_four_lap_results_v1.csv"
    )

    canon.to_csv(
        canon_file,
        index=False
    )

    print(
        "\nCANONICAL ROWS =",
        len(canon)
    )

    print(
        canon[
            [
                c
                for c in [
                    "rank",
                    "car_number",
                    "driver_name",
                    "lap1_time_s",
                    "lap2_time_s",
                    "lap3_time_s",
                    "lap4_time_s",
                    "four_lap_average_speed_mph",
                ]
                if c in canon.columns
            ]
        ]
        .head(10)
        .to_string(index=False)
    )

    manifest.append({
        "year": year,
        "url": meta["url"],
        "status": "CANONICALIZED",
        "table_index": best["index"],
        "table_score": best["score"],
        "rows": len(canon),
        "technical_regime":
            meta["technical_regime"],
        "qualifying_format_regime":
            meta[
                "qualifying_format_regime"
            ],
    })

# ============================================================
# combined output
# ============================================================

if canonical_rows:

    combined = pd.concat(
        canonical_rows,
        ignore_index=True,
        sort=False
    )

else:
    combined = pd.DataFrame()

combined_file = (
    OUT /
    "regime_extension_official_final_results_v1.csv"
)

combined.to_csv(
    combined_file,
    index=False
)

manifest_df = pd.DataFrame(
    manifest
)

manifest_file = (
    OUT /
    "official_result_download_manifest_v1.csv"
)

manifest_df.to_csv(
    manifest_file,
    index=False
)

print("\n" + "=" * 120)
print("FINAL SUMMARY")
print("=" * 120)

print(
    manifest_df.to_string(
        index=False
    )
)

if not combined.empty:

    print("\nROWS BY YEAR:")

    print(
        combined.groupby("year")
        .size()
        .to_string()
    )

print("\nOUTPUTS:")
print(
    combined_file.relative_to(ROOT)
)
print(
    manifest_file.relative_to(ROOT)
)

print(
    "\nR6_OFFICIAL_REGIME_SEED_V1_COMPLETE"
)
