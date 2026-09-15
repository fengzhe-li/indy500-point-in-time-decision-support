from pathlib import Path
import json
import re
import pandas as pd

ROOT = Path("/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈")

SRC = (
    ROOT /
    "r6_regime_extension/evidence/official_api_v2"
)

OUT = (
    ROOT /
    "r6_regime_extension/output"
)

OUT.mkdir(
    parents=True,
    exist_ok=True
)

TARGET_SESSION_IDS = {
    2018: 5320,
    2019: 5565,
    2025: 6656,
    2026: 6835,
}

# ============================================================
# recursive helpers
# ============================================================

def walk(obj, path="root"):

    rows = []

    if isinstance(obj, dict):

        for k, v in obj.items():

            child = f"{path}.{k}"

            rows.append({
                "path": child,
                "key": str(k),
                "value_type": type(v).__name__,
                "value":
                    str(v)
                    if not isinstance(v, (dict, list))
                    else "",
            })

            rows.extend(
                walk(
                    v,
                    child
                )
            )

    elif isinstance(obj, list):

        for i, v in enumerate(obj):

            child = f"{path}[{i}]"

            rows.extend(
                walk(
                    v,
                    child
                )
            )

    return rows


def looks_reportish(text):

    s = str(text).lower()

    tokens = [
        "report",
        "result",
        "section",
        "pdf",
        "download",
        "summary",
        "box",
        "lap",
        "url",
        "href",
        "file",
        "document",
    ]

    return any(
        t in s
        for t in tokens
    )


def extract_urls(text):

    if not isinstance(
        text,
        str
    ):
        return []

    urls = re.findall(
        r'https?://[^\s"\'<>]+',
        text
    )

    relative = re.findall(
        r'(?:"|\')([^"\']+\.pdf(?:\?[^"\']*)?)(?:"|\')',
        text,
        flags=re.I
    )

    return urls + relative


# ============================================================
# inspect each target raw JSON
# ============================================================

all_inventory = []
all_candidates = []

for year, sid in TARGET_SESSION_IDS.items():

    p = (
        SRC /
        f"{year}_session_{sid}_raw.json"
    )

    print("\n" + "=" * 150)
    print(
        "YEAR",
        year,
        "SESSION",
        sid
    )
    print("=" * 150)

    if not p.exists():

        print(
            "MISSING:",
            p.relative_to(ROOT)
        )

        continue

    with open(
        p,
        "r",
        encoding="utf-8"
    ) as f:
        obj = json.load(f)

    if isinstance(
        obj,
        dict
    ):

        print(
            "TOP-LEVEL KEYS:"
        )

        for k in sorted(
            obj.keys()
        ):
            print(
                " ",
                k,
                "->",
                type(
                    obj[k]
                ).__name__
            )

    inventory = pd.DataFrame(
        walk(obj)
    )

    inventory["year"] = year
    inventory["session_id"] = sid

    all_inventory.append(
        inventory
    )

    # --------------------------------------------------------
    # report-ish key / path / value candidates
    # --------------------------------------------------------

    mask = (
        inventory["path"]
        .astype(str)
        .apply(
            looks_reportish
        )
        |
        inventory["key"]
        .astype(str)
        .apply(
            looks_reportish
        )
        |
        inventory["value"]
        .astype(str)
        .apply(
            looks_reportish
        )
    )

    cand = inventory[
        mask
    ].copy()

    print(
        "\nREPORT-LIKE FIELDS:"
    )

    if cand.empty:

        print(
            "NONE FOUND"
        )

    else:

        print(
            cand[
                [
                    "path",
                    "key",
                    "value_type",
                    "value",
                ]
            ]
            .head(200)
            .to_string(
                index=False
            )
        )

    cand["year"] = year
    cand["session_id"] = sid

    all_candidates.append(
        cand
    )

    # --------------------------------------------------------
    # literal URLs anywhere in raw JSON text
    # --------------------------------------------------------

    raw_text = p.read_text(
        encoding="utf-8",
        errors="ignore"
    )

    urls = sorted(
        set(
            extract_urls(
                raw_text
            )
        )
    )

    print(
        "\nURL/PDF CANDIDATES:"
    )

    if not urls:

        print(
            "NONE FOUND"
        )

    else:

        for u in urls:
            print(u)

# ============================================================
# save
# ============================================================

if all_inventory:

    inventory_df = pd.concat(
        all_inventory,
        ignore_index=True
    )

else:

    inventory_df = pd.DataFrame()

if all_candidates:

    candidate_df = pd.concat(
        all_candidates,
        ignore_index=True
    )

else:

    candidate_df = pd.DataFrame()

INV_OUT = (
    OUT /
    "official_session_json_field_inventory_v1.csv"
)

CAND_OUT = (
    OUT /
    "official_session_report_field_candidates_v1.csv"
)

inventory_df.to_csv(
    INV_OUT,
    index=False
)

candidate_df.to_csv(
    CAND_OUT,
    index=False
)

print("\n" + "=" * 150)
print("FINAL")
print("=" * 150)

print(
    "inventory rows =",
    len(inventory_df)
)

print(
    "report-like candidate rows =",
    len(candidate_df)
)

print("\nOUTPUTS:")
print(
    INV_OUT.relative_to(ROOT)
)
print(
    CAND_OUT.relative_to(ROOT)
)

print(
    "\nR6_OFFICIAL_REPORT_LINK_DISCOVERY_V1_COMPLETE"
)
