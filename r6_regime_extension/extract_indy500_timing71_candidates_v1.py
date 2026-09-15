from pathlib import Path
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import json
import re
import requests
import pandas as pd

ROOT = Path("/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈")

OUT = (
    ROOT /
    "r6_regime_extension/output/timing71_indy500_candidates_v1"
)

EVIDENCE = (
    ROOT /
    "r6_regime_extension/evidence/timing71_indy500_v1"
)

OUT.mkdir(
    parents=True,
    exist_ok=True
)

EVIDENCE.mkdir(
    parents=True,
    exist_ok=True
)

BASE = "https://archive.timing71.org"

session = requests.Session()

session.headers.update({
    "User-Agent": "Mozilla/5.0"
})

# ============================================================
# Load complete replay catalogue
# ============================================================

print("=" * 160)
print("PART 1 — LOAD TIMING71 REPLAY CATALOGUE")
print("=" * 160)

r = session.get(
    BASE + "/replays",
    timeout=120
)

print(
    "HTTP",
    r.status_code,
    "bytes",
    len(r.content)
)

r.raise_for_status()

catalogue = r.json()

print(
    "catalogue records =",
    len(catalogue)
)

RAW_OUT = (
    OUT /
    "timing71_full_replay_catalogue_snapshot_v1.json"
)

RAW_OUT.write_text(
    json.dumps(
        catalogue,
        indent=2,
        ensure_ascii=False
    ),
    encoding="utf-8"
)

# ============================================================
# Flatten relevant metadata
# ============================================================

rows = []

indy_tz = ZoneInfo(
    "America/Indiana/Indianapolis"
)

for i, item in enumerate(
    catalogue
):

    description = str(
        item.get(
            "description",
            ""
        )
    )

    series = str(
        item.get(
            "series",
            ""
        )
    )

    filename = str(
        item.get(
            "filename",
            ""
        )
    )

    analysis_filename = str(
        item.get(
            "analysisFilename",
            ""
        )
    )

    combined = " ".join([
        description,
        series,
        filename,
        analysis_filename,
    ])

    low = combined.lower()

    start_time = item.get(
        "startTime"
    )

    start_utc = None
    start_indy = None

    if start_time is not None:

        try:

            ts = float(
                start_time
            )

            dt_utc = datetime.fromtimestamp(
                ts,
                tz=timezone.utc
            )

            dt_indy = dt_utc.astimezone(
                indy_tz
            )

            start_utc = dt_utc.isoformat()
            start_indy = dt_indy.isoformat()

        except Exception:
            pass

    rows.append({
        "catalogue_index":
            i,

        "id":
            item.get(
                "id"
            ),

        "series":
            series,

        "description":
            description,

        "startTime":
            start_time,

        "start_utc":
            start_utc,

        "start_indianapolis":
            start_indy,

        "filename":
            filename,

        "analysisFilename":
            analysis_filename,

        "indy_keyword":
            (
                "indy" in low
                or "indianapolis" in low
            ),

        "qual_keyword":
            (
                "qual" in low
            ),

        "500_keyword":
            (
                "500" in low
            ),
    })

df = pd.DataFrame(
    rows
)

# ============================================================
# Indianapolis 500 qualifying candidates
# ============================================================

mask = (
    (
        df["series"]
        .str.lower()
        .eq("indycar")
    )
    &
    (
        df["description"]
        .str.contains(
            r"Indianapolis.*500|500.*Indianapolis",
            case=False,
            regex=True,
            na=False
        )
        |
        df["filename"]
        .str.contains(
            r"Indianapolis.*500|500.*Indianapolis",
            case=False,
            regex=True,
            na=False
        )
    )
    &
    (
        df["description"]
        .str.contains(
            r"Qual",
            case=False,
            regex=True,
            na=False
        )
        |
        df["filename"]
        .str.contains(
            r"Qual",
            case=False,
            regex=True,
            na=False
        )
    )
)

indy_qual = df[
    mask
].copy()

# Also retain all IndyCar Indianapolis 500 records
all_indy500_mask = (
    df["series"]
    .str.lower()
    .eq("indycar")
    &
    (
        df["description"]
        .str.contains(
            r"Indianapolis.*500|500.*Indianapolis",
            case=False,
            regex=True,
            na=False
        )
        |
        df["filename"]
        .str.contains(
            r"Indianapolis.*500|500.*Indianapolis",
            case=False,
            regex=True,
            na=False
        )
    )
)

all_indy500 = df[
    all_indy500_mask
].copy()

# ============================================================
# Infer season/year
# ============================================================

YEAR_RE = re.compile(
    r"\b(2018|2019|2020|2021|2022|2023|2024|2025|2026)\b"
)

ORDINAL_TO_YEAR = {
    "102nd": 2018,
    "103rd": 2019,
    "104th": 2020,
    "105th": 2021,
    "106th": 2022,
    "107th": 2023,
    "108th": 2024,
    "109th": 2025,
    "110th": 2026,
}

def infer_year(row):

    text = " ".join([
        str(
            row.get(
                "description",
                ""
            )
        ),
        str(
            row.get(
                "filename",
                ""
            )
        ),
    ])

    for ordinal, year in ORDINAL_TO_YEAR.items():

        if ordinal.lower() in text.lower():
            return year

    m = YEAR_RE.search(
        text
    )

    if m:
        return int(
            m.group(1)
        )

    start = row.get(
        "start_utc"
    )

    if pd.notna(start):

        try:
            return int(
                str(start)[:4]
            )
        except Exception:
            pass

    return None


if not indy_qual.empty:

    indy_qual["inferred_year"] = (
        indy_qual.apply(
            infer_year,
            axis=1
        )
    )


if not all_indy500.empty:

    all_indy500[
        "inferred_year"
    ] = (
        all_indy500.apply(
            infer_year,
            axis=1
        )
    )

# ============================================================
# Save catalogues
# ============================================================

ALL_INDY_OUT = (
    OUT /
    "timing71_all_indy500_records_v1.csv"
)

QUAL_OUT = (
    OUT /
    "timing71_indy500_qualifying_candidates_v1.csv"
)

all_indy500.to_csv(
    ALL_INDY_OUT,
    index=False
)

indy_qual.to_csv(
    QUAL_OUT,
    index=False
)

# ============================================================
# Print target-year candidates
# ============================================================

print("\n" + "=" * 160)
print("PART 2 — ALL INDY 500 QUALIFYING CANDIDATES")
print("=" * 160)

if indy_qual.empty:

    print(
        "NO INDY 500 QUALIFYING CANDIDATES"
    )

else:

    cols = [
        "catalogue_index",
        "inferred_year",
        "id",
        "description",
        "startTime",
        "start_utc",
        "start_indianapolis",
        "filename",
        "analysisFilename",
    ]

    print(
        indy_qual[
            cols
        ]
        .sort_values(
            [
                "inferred_year",
                "catalogue_index"
            ]
        )
        .to_string(
            index=False
        )
    )

print("\n" + "=" * 160)
print("PART 3 — TARGET YEARS 2018 / 2019 / 2025")
print("=" * 160)

target = indy_qual[
    indy_qual[
        "inferred_year"
    ]
    .isin([
        2018,
        2019,
        2025
    ])
].copy()

if target.empty:

    print(
        "NO TARGET-YEAR QUALIFYING REPLAYS"
    )

else:

    print(
        target[
            [
                "inferred_year",
                "id",
                "description",
                "startTime",
                "start_utc",
                "start_indianapolis",
                "filename",
                "analysisFilename",
            ]
        ]
        .sort_values(
            [
                "inferred_year",
                "catalogue_index"
            ]
        )
        .to_string(
            index=False
        )
    )

# ============================================================
# Download analysis JSON for target qualifying candidates
# ============================================================

download_rows = []

print("\n" + "=" * 160)
print("PART 4 — TARGET ANALYSIS JSON DOWNLOAD")
print("=" * 160)

for _, row in target.iterrows():

    year = int(
        row["inferred_year"]
    )

    replay_id = row[
        "id"
    ]

    description = str(
        row[
            "description"
        ]
    )

    analysis_url = str(
        row.get(
            "analysisFilename",
            ""
        )
    )

    candidates = []

    if (
        analysis_url
        and analysis_url.lower()
        not in {
            "nan",
            "none",
            ""
        }
    ):

        candidates.append(
            (
                "analysisFilename",
                analysis_url
            )
        )

    if replay_id:

        candidates.append(
            (
                "api_analysis",
                f"{BASE}/analysis/{replay_id}"
            )
        )

    success = False

    for source_type, url in candidates:

        try:

            rr = session.get(
                url,
                timeout=120
            )

            print(
                year,
                replay_id,
                source_type,
                "HTTP",
                rr.status_code,
                "bytes",
                len(
                    rr.content
                )
            )

            if rr.status_code != 200:
                continue

            try:

                payload = rr.json()

            except Exception:
                continue

            safe_desc = re.sub(
                r"[^A-Za-z0-9]+",
                "_",
                description
            ).strip(
                "_"
            )[:80]

            dest = (
                EVIDENCE /
                f"{year}_{safe_desc}_{replay_id}_analysis.json"
            )

            dest.write_text(
                json.dumps(
                    payload,
                    indent=2,
                    ensure_ascii=False
                ),
                encoding="utf-8"
            )

            download_rows.append({
                "year":
                    year,

                "id":
                    replay_id,

                "description":
                    description,

                "source_type":
                    source_type,

                "url":
                    url,

                "status":
                    "DOWNLOADED",

                "local_file":
                    str(
                        dest.relative_to(
                            ROOT
                        )
                    ),
            })

            success = True

            break

        except Exception as e:

            print(
                year,
                replay_id,
                source_type,
                "ERROR",
                repr(e)
            )

    if not success:

        download_rows.append({
            "year":
                year,

            "id":
                replay_id,

            "description":
                description,

            "source_type":
                None,

            "url":
                None,

            "status":
                "FAILED",

            "local_file":
                None,
        })

downloads = pd.DataFrame(
    download_rows
)

DOWNLOAD_OUT = (
    OUT /
    "timing71_target_analysis_download_manifest_v1.csv"
)

downloads.to_csv(
    DOWNLOAD_OUT,
    index=False
)

# ============================================================
# Analysis JSON structural audit
# ============================================================

print("\n" + "=" * 160)
print("PART 5 — ANALYSIS JSON STRUCTURE")
print("=" * 160)

structure_rows = []
key_hits = []

SEARCH_TERMS = [
    "time",
    "elapsed",
    "session",
    "lap",
    "driver",
    "car",
    "timestamp",
    "clock",
    "speed",
]

for record in download_rows:

    local_file = record.get(
        "local_file"
    )

    if not local_file:
        continue

    path = ROOT / local_file

    payload = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    year = record[
        "year"
    ]

    replay_id = record[
        "id"
    ]

    if isinstance(
        payload,
        dict
    ):

        top_type = "dict"

        top_keys = " | ".join(
            map(
                str,
                payload.keys()
            )
        )

        top_len = len(
            payload
        )

    elif isinstance(
        payload,
        list
    ):

        top_type = "list"
        top_keys = ""
        top_len = len(
            payload
        )

    else:

        top_type = type(
            payload
        ).__name__

        top_keys = ""
        top_len = None

    structure_rows.append({
        "year":
            year,

        "id":
            replay_id,

        "top_type":
            top_type,

        "top_len":
            top_len,

        "top_keys":
            top_keys,
    })

    def walk(
        obj,
        path_str="$",
        depth=0
    ):

        if depth > 8:
            return

        if isinstance(
            obj,
            dict
        ):

            for key, value in obj.items():

                key_low = str(
                    key
                ).lower()

                if any(
                    term in key_low
                    for term in SEARCH_TERMS
                ):

                    preview = str(
                        value
                    )

                    if len(
                        preview
                    ) > 400:

                        preview = (
                            preview[:400]
                            + "..."
                        )

                    key_hits.append({
                        "year":
                            year,

                        "id":
                            replay_id,

                        "json_path":
                            f"{path_str}.{key}",

                        "key":
                            key,

                        "value_preview":
                            preview,
                    })

                walk(
                    value,
                    f"{path_str}.{key}",
                    depth + 1
                )

        elif isinstance(
            obj,
            list
        ):

            for i, value in enumerate(
                obj[:100]
            ):

                walk(
                    value,
                    f"{path_str}[{i}]",
                    depth + 1
                )

    walk(
        payload
    )

structure = pd.DataFrame(
    structure_rows
)

hits = pd.DataFrame(
    key_hits
)

STRUCTURE_OUT = (
    OUT /
    "timing71_target_analysis_structure_v1.csv"
)

HITS_OUT = (
    OUT /
    "timing71_target_analysis_time_lap_key_hits_v1.csv"
)

structure.to_csv(
    STRUCTURE_OUT,
    index=False
)

hits.to_csv(
    HITS_OUT,
    index=False
)

if structure.empty:

    print(
        "NO ANALYSIS JSON DOWNLOADED"
    )

else:

    print(
        structure.to_string(
            index=False
        )
    )

print("\n" + "=" * 160)
print("PART 6 — TIME / LAP / SESSION KEY HITS")
print("=" * 160)

if hits.empty:

    print(
        "NONE"
    )

else:

    print(
        hits[
            [
                "year",
                "id",
                "json_path",
                "key",
                "value_preview",
            ]
        ]
        .head(300)
        .to_string(
            index=False
        )
    )

print("\nOUTPUTS:")

for p in [
    RAW_OUT,
    ALL_INDY_OUT,
    QUAL_OUT,
    DOWNLOAD_OUT,
    STRUCTURE_OUT,
    HITS_OUT,
]:

    print(
        p.relative_to(
            ROOT
        )
    )

print(
    "\nR6_TIMING71_INDY500_CANDIDATES_V1_COMPLETE"
)
