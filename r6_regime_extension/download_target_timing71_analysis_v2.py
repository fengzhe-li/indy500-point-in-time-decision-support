from pathlib import Path
import json
import re
import requests
import pandas as pd

ROOT = Path("/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈")

SRC = (
    ROOT /
    "r6_regime_extension/output/timing71_indy500_candidates_v1/"
    "timing71_indy500_qualifying_candidates_v1.csv"
)

OUT = (
    ROOT /
    "r6_regime_extension/output/timing71_target_analysis_v2"
)

EVIDENCE = (
    ROOT /
    "r6_regime_extension/evidence/timing71_indy500_v2"
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

df = pd.read_csv(
    SRC,
    low_memory=False
)

# ============================================================
# Strictly select only Day 1 / first-day qualifying sessions
# ============================================================
#
# 2018:
#   May 19 = Day 1
#   May 20 = second qualifying day / Fast 9
#
# 2019:
#   May 18 = Day 1
#   May 19 = second qualifying day
#
# 2025:
#   explicit "Qualifications - Day One"
# ============================================================

df["start_utc_dt"] = pd.to_datetime(
    df["start_utc"],
    errors="coerce",
    utc=True
)

target_mask = (
    (
        (df["inferred_year"] == 2018)
        &
        (df["start_utc_dt"].dt.date.astype(str) == "2018-05-19")
    )
    |
    (
        (df["inferred_year"] == 2019)
        &
        (df["start_utc_dt"].dt.date.astype(str) == "2019-05-18")
    )
    |
    (
        (df["inferred_year"] == 2025)
        &
        (
            df["description"]
            .astype(str)
            .str.contains(
                "Day One",
                case=False,
                regex=False
            )
        )
    )
)

target = (
    df[target_mask]
    .copy()
    .sort_values(
        [
            "inferred_year",
            "start_utc_dt",
            "catalogue_index",
        ]
    )
)

print("=" * 160)
print("PART 1 — STRICT DAY 1 TARGET REPLAYS")
print("=" * 160)

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
    target[
        cols
    ].to_string(
        index=False
    )
)

# ============================================================
# Sanity counts
# ============================================================

print("\n" + "=" * 160)
print("PART 2 — TARGET COUNTS")
print("=" * 160)

print(
    target.groupby(
        "inferred_year"
    )
    .size()
    .reset_index(
        name="replay_fragments"
    )
    .to_string(
        index=False
    )
)

# ============================================================
# Download analysis JSON
# ============================================================

manifest_rows = []

print("\n" + "=" * 160)
print("PART 3 — ANALYSIS JSON DOWNLOAD")
print("=" * 160)

for _, row in target.iterrows():

    year = int(
        row["inferred_year"]
    )

    replay_id = str(
        row["id"]
    )

    description = str(
        row["description"]
    )

    analysis_url = str(
        row["analysisFilename"]
    )

    candidate_urls = []

    if (
        analysis_url
        and analysis_url.lower()
        not in {
            "",
            "nan",
            "none",
        }
    ):
        candidate_urls.append(
            (
                "analysisFilename",
                analysis_url
            )
        )

    candidate_urls.append(
        (
            "archive_analysis_endpoint",
            f"{BASE}/analysis/{replay_id}"
        )
    )

    success = False

    for source_type, url in candidate_urls:

        try:

            r = session.get(
                url,
                timeout=120
            )

            print(
                year,
                replay_id,
                source_type,
                "HTTP",
                r.status_code,
                "bytes",
                len(r.content)
            )

            if r.status_code != 200:
                continue

            try:
                payload = r.json()
            except Exception as e:
                print(
                    " JSON ERROR",
                    repr(e)
                )
                continue

            safe_id = (
                replay_id
                .replace(
                    ":",
                    "_"
                )
            )

            dest = (
                EVIDENCE /
                f"{year}_{safe_id}_analysis.json"
            )

            dest.write_text(
                json.dumps(
                    payload,
                    indent=2,
                    ensure_ascii=False
                ),
                encoding="utf-8"
            )

            manifest_rows.append({
                "year":
                    year,

                "catalogue_index":
                    row["catalogue_index"],

                "id":
                    replay_id,

                "description":
                    description,

                "startTime":
                    row["startTime"],

                "start_utc":
                    row["start_utc"],

                "start_indianapolis":
                    row["start_indianapolis"],

                "source_type":
                    source_type,

                "source_url":
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

        manifest_rows.append({
            "year":
                year,

            "catalogue_index":
                row["catalogue_index"],

            "id":
                replay_id,

            "description":
                description,

            "startTime":
                row["startTime"],

            "start_utc":
                row["start_utc"],

            "start_indianapolis":
                row["start_indianapolis"],

            "source_type":
                None,

            "source_url":
                None,

            "status":
                "FAILED",

            "local_file":
                None,
        })

manifest = pd.DataFrame(
    manifest_rows
)

MANIFEST_OUT = (
    OUT /
    "timing71_day1_analysis_download_manifest_v2.csv"
)

manifest.to_csv(
    MANIFEST_OUT,
    index=False
)

# ============================================================
# Structural audit
# ============================================================

structure_rows = []
key_rows = []

SEARCH_TERMS = [
    "time",
    "elapsed",
    "session",
    "lap",
    "driver",
    "car",
    "speed",
    "timestamp",
    "clock",
    "running",
    "position",
]

print("\n" + "=" * 160)
print("PART 4 — ANALYSIS JSON STRUCTURE")
print("=" * 160)

for _, row in manifest[
    manifest["status"] == "DOWNLOADED"
].iterrows():

    year = int(
        row["year"]
    )

    replay_id = str(
        row["id"]
    )

    path = (
        ROOT /
        row["local_file"]
    )

    payload = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    if isinstance(
        payload,
        dict
    ):

        top_type = "dict"
        top_len = len(
            payload
        )

        top_keys = " | ".join(
            map(
                str,
                payload.keys()
            )
        )

    elif isinstance(
        payload,
        list
    ):

        top_type = "list"
        top_len = len(
            payload
        )

        top_keys = ""

    else:

        top_type = type(
            payload
        ).__name__

        top_len = None
        top_keys = ""

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

    # --------------------------------------------------------
    # Recursive key scan
    # --------------------------------------------------------

    def walk(
        obj,
        path_str="$",
        depth=0
    ):

        if depth > 10:
            return

        if isinstance(
            obj,
            dict
        ):

            for key, value in obj.items():

                key_str = str(
                    key
                )

                low = key_str.lower()

                if any(
                    term in low
                    for term in SEARCH_TERMS
                ):

                    preview = str(
                        value
                    )

                    if len(preview) > 500:
                        preview = (
                            preview[:500]
                            + "..."
                        )

                    key_rows.append({
                        "year":
                            year,

                        "id":
                            replay_id,

                        "json_path":
                            f"{path_str}.{key_str}",

                        "key":
                            key_str,

                        "value_preview":
                            preview,
                    })

                walk(
                    value,
                    f"{path_str}.{key_str}",
                    depth + 1
                )

        elif isinstance(
            obj,
            list
        ):

            for i, value in enumerate(
                obj[:250]
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

keys = pd.DataFrame(
    key_rows
)

STRUCTURE_OUT = (
    OUT /
    "timing71_day1_analysis_structure_v2.csv"
)

KEY_OUT = (
    OUT /
    "timing71_day1_analysis_key_hits_v2.csv"
)

structure.to_csv(
    STRUCTURE_OUT,
    index=False
)

keys.to_csv(
    KEY_OUT,
    index=False
)

if structure.empty:

    print(
        "NO JSON DOWNLOADED"
    )

else:

    print(
        structure.to_string(
            index=False
        )
    )

# ============================================================
# High-value key hits
# ============================================================

print("\n" + "=" * 160)
print("PART 5 — TIME / SESSION / LAP KEY HITS")
print("=" * 160)

if keys.empty:

    print(
        "NONE"
    )

else:

    high_value = keys[
        keys["key"]
        .astype(str)
        .str.lower()
        .str.contains(
            r"time|elapsed|session|lap|timestamp|clock",
            regex=True
        )
    ]

    print(
        high_value[
            [
                "year",
                "id",
                "json_path",
                "key",
                "value_preview",
            ]
        ]
        .head(400)
        .to_string(
            index=False
        )
    )

# ============================================================
# Download replay ZIPs too
# ============================================================

print("\n" + "=" * 160)
print("PART 6 — RAW REPLAY ZIP DOWNLOAD")
print("=" * 160)

zip_manifest = []

for _, row in target.iterrows():

    year = int(
        row["inferred_year"]
    )

    replay_id = str(
        row["id"]
    )

    url = str(
        row["filename"]
    )

    safe_id = replay_id.replace(
        ":",
        "_"
    )

    dest = (
        EVIDENCE /
        f"{year}_{safe_id}_replay.zip"
    )

    try:

        r = session.get(
            url,
            timeout=180
        )

        print(
            year,
            replay_id,
            "HTTP",
            r.status_code,
            "bytes",
            len(r.content)
        )

        if r.status_code == 200:

            dest.write_bytes(
                r.content
            )

            status = "DOWNLOADED"

            local_file = str(
                dest.relative_to(
                    ROOT
                )
            )

        else:

            status = "FAILED"
            local_file = None

    except Exception as e:

        print(
            year,
            replay_id,
            "ERROR",
            repr(e)
        )

        status = "FAILED"
        local_file = None

    zip_manifest.append({
        "year":
            year,

        "id":
            replay_id,

        "url":
            url,

        "status":
            status,

        "local_file":
            local_file,
    })

zip_df = pd.DataFrame(
    zip_manifest
)

ZIP_MANIFEST_OUT = (
    OUT /
    "timing71_day1_replay_zip_manifest_v2.csv"
)

zip_df.to_csv(
    ZIP_MANIFEST_OUT,
    index=False
)

print("\nOUTPUTS:")

for p in [
    MANIFEST_OUT,
    STRUCTURE_OUT,
    KEY_OUT,
    ZIP_MANIFEST_OUT,
]:

    print(
        p.relative_to(
            ROOT
        )
    )

print(
    "\nR6_TIMING71_DAY1_ANALYSIS_V2_COMPLETE"
)
