from pathlib import Path
import re
import pandas as pd
import numpy as np

ROOT = Path("/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈")

SRC = (
    ROOT /
    "r6_regime_extension/output/attempt_pdf_parse/"
    "official_results_all_layout_lines_v1.csv"
)

OUT = (
    ROOT /
    "r6_regime_extension/output/regime_attempt_inventory_v3"
)

OUT.mkdir(
    parents=True,
    exist_ok=True
)

df = pd.read_csv(
    SRC,
    low_memory=False
)

# ============================================================
# Strict official-results row parser
# ============================================================
#
# Expected structure:
#
# rank car driver-name C/E/T
# lap1 lap2 lap3 lap4
# total-time
# optional avg-speed
# optional tail/status
#
# Important:
# Some "No Attempt" rows have no average-speed value.
# ============================================================

ROW_RE = re.compile(
    r"^\s*"
    r"(?P<rank>\d+)\s+"
    r"(?P<car>[A-Za-z0-9]+)\s+"
    r"(?P<driver>.+?)\s+"
    r"(?P<cet>[A-Z]/[A-Z]/[A-Z])\s+"
    r"(?P<lap1>\d+\.\d{4})\s+"
    r"(?P<lap2>\d+\.\d{4})\s+"
    r"(?P<lap3>\d+\.\d{4})\s+"
    r"(?P<lap4>\d+\.\d{4})\s+"
    r"(?P<total>\d{2}:\d{2}\.\d{4})"
    r"(?:\s+(?P<speed>\d+\.\d{3}))?"
    r"(?P<tail>.*)$"
)

KNOWN_STATUSES = [
    "Failed Attempt",
    "No Attempt",
    "On Bubble",
    "Waved Off",
    "Withdrawn",
    "Retired",
    "Bumped",
]

def clean_driver(s):
    return re.sub(
        r"\s+",
        " ",
        str(s)
    ).strip()


def extract_status(tail):

    tail = str(tail).strip()

    for status in KNOWN_STATUSES:
        if status.lower() in tail.lower():
            return status

    return "VALID_OR_UNLABELED"


records = []

for _, row in df.iterrows():

    year = int(row["year"])
    line_no = int(row["line_no"])
    text = str(row["raw_line"]).strip()

    m = ROW_RE.match(
        text
    )

    if not m:
        continue

    x = m.groupdict()

    speed = (
        float(x["speed"])
        if x["speed"] is not None
        else np.nan
    )

    rec = {
        "year": year,
        "source_line_no": line_no,
        "source_rank": int(
            x["rank"]
        ),
        "car_number": x["car"],
        "driver_name": clean_driver(
            x["driver"]
        ),
        "cet": x["cet"],
        "lap1_s": float(
            x["lap1"]
        ),
        "lap2_s": float(
            x["lap2"]
        ),
        "lap3_s": float(
            x["lap3"]
        ),
        "lap4_s": float(
            x["lap4"]
        ),
        "total_time": x["total"],
        "average_speed_mph": speed,
        "status": extract_status(
            x["tail"]
        ),
        "tail_raw": x["tail"].strip(),
        "raw_line": text,
    }

    records.append(
        rec
    )

attempts = pd.DataFrame(
    records
)

if attempts.empty:
    raise RuntimeError(
        "No official result rows parsed"
    )

# ============================================================
# Strict timed-lap logic
# ============================================================

LAPS = [
    "lap1_s",
    "lap2_s",
    "lap3_s",
    "lap4_s",
]

attempts["timed_lap_count"] = (
    attempts[LAPS]
    .gt(0)
    .sum(axis=1)
)

attempts["complete_four_lap"] = (
    attempts[
        "timed_lap_count"
    ]
    == 4
)

attempts["partial_attempt"] = (
    attempts[
        "timed_lap_count"
    ]
    .between(
        1,
        3
    )
)

attempts["zero_lap"] = (
    attempts[
        "timed_lap_count"
    ]
    == 0
)

# ============================================================
# Normalized identities
# ============================================================

attempts["car_key"] = (
    attempts[
        "car_number"
    ]
    .astype(str)
    .str.upper()
    .str.strip()
)

attempts["driver_key"] = (
    attempts[
        "driver_name"
    ]
    .astype(str)
    .str.lower()
    .str.replace(
        r"[^a-z0-9]+",
        "",
        regex=True
    )
)

attempts["entrant_key"] = (
    attempts[
        "driver_key"
    ]
    + "__"
    + attempts[
        "car_key"
    ]
)

# ============================================================
# Occurrence / repeat information
# ============================================================

attempts[
    "record_index_for_entrant"
] = (
    attempts
    .groupby(
        [
            "year",
            "entrant_key"
        ],
        sort=False
    )
    .cumcount()
    + 1
)

attempts[
    "records_for_entrant"
] = (
    attempts
    .groupby(
        [
            "year",
            "entrant_key"
        ]
    )[
        "entrant_key"
    ]
    .transform(
        "size"
    )
)

complete_counts = (
    attempts[
        attempts[
            "complete_four_lap"
        ]
    ]
    .groupby(
        [
            "year",
            "entrant_key"
        ]
    )
    .size()
    .rename(
        "complete_attempts_for_entrant"
    )
    .reset_index()
)

attempts = attempts.merge(
    complete_counts,
    on=[
        "year",
        "entrant_key"
    ],
    how="left"
)

attempts[
    "complete_attempts_for_entrant"
] = (
    attempts[
        "complete_attempts_for_entrant"
    ]
    .fillna(0)
    .astype(int)
)

attempts[
    "has_repeat_complete_attempt"
] = (
    attempts[
        "complete_attempts_for_entrant"
    ]
    >= 2
)

# ============================================================
# Chronology semantics
# ============================================================

attempts[
    "chronology_verified"
] = False

attempts[
    "source_order_semantics"
] = (
    "RESULT_REPORT_ORDER_NOT_VERIFIED_CHRONOLOGY"
)

# ============================================================
# QA expected totals
# ============================================================

EXPECTED = {
    2018: 48,
    2019: 73,
    2025: 73,
    2026: 33,
}

qa_rows = []

for year, expected in EXPECTED.items():

    g = attempts[
        attempts[
            "year"
        ]
        == year
    ]

    ranks = sorted(
        g[
            "source_rank"
        ]
        .dropna()
        .astype(int)
        .tolist()
    )

    expected_ranks = list(
        range(
            1,
            expected + 1
        )
    )

    missing_ranks = sorted(
        set(
            expected_ranks
        )
        - set(
            ranks
        )
    )

    duplicate_ranks = (
        g[
            "source_rank"
        ]
        .value_counts()
    )

    duplicate_ranks = (
        duplicate_ranks[
            duplicate_ranks > 1
        ]
        .index
        .astype(int)
        .tolist()
    )

    qa_rows.append({
        "year":
            year,

        "expected_rows":
            expected,

        "parsed_rows":
            len(g),

        "row_count_pass":
            len(g)
            == expected,

        "rank_1_to_n_pass":
            ranks
            == expected_ranks,

        "missing_ranks":
            ",".join(
                map(
                    str,
                    missing_ranks
                )
            ),

        "duplicate_ranks":
            ",".join(
                map(
                    str,
                    duplicate_ranks
                )
            ),
    })

qa = pd.DataFrame(
    qa_rows
)

# ============================================================
# Summary
# ============================================================

summary_rows = []

for year, g in attempts.groupby(
    "year"
):

    complete = g[
        g[
            "complete_four_lap"
        ]
    ].copy()

    complete_counts_y = (
        complete
        .groupby(
            "entrant_key"
        )
        .size()
    )

    repeat_complete = (
        complete_counts_y[
            complete_counts_y
            >= 2
        ]
    )

    potential_transitions = int(
        sum(
            n - 1
            for n
            in repeat_complete
        )
    )

    summary_rows.append({
        "year":
            int(year),

        "official_result_rows":
            len(g),

        "unique_driver_car":
            g[
                "entrant_key"
            ].nunique(),

        "complete_four_lap_attempts":
            int(
                g[
                    "complete_four_lap"
                ]
                .sum()
            ),

        "partial_attempts":
            int(
                g[
                    "partial_attempt"
                ]
                .sum()
            ),

        "zero_lap_records":
            int(
                g[
                    "zero_lap"
                ]
                .sum()
            ),

        "driver_cars_with_multiple_records":
            int(
                (
                    g.groupby(
                        "entrant_key"
                    )
                    .size()
                    >= 2
                )
                .sum()
            ),

        "driver_cars_with_2plus_complete_attempts":
            len(
                repeat_complete
            ),

        "potential_complete_repeat_transitions":
            potential_transitions,

        "chronology_verified":
            False,
    })

summary = pd.DataFrame(
    summary_rows
).sort_values(
    "year"
)

# ============================================================
# Repeat candidate inventory
# ============================================================

repeat_keys = (
    attempts[
        attempts[
            "complete_four_lap"
        ]
    ]
    .groupby(
        [
            "year",
            "entrant_key"
        ]
    )
    .size()
)

repeat_keys = (
    repeat_keys[
        repeat_keys
        >= 2
    ]
    .reset_index()[
        [
            "year",
            "entrant_key"
        ]
    ]
)

repeat_inventory = attempts.merge(
    repeat_keys,
    on=[
        "year",
        "entrant_key"
    ],
    how="inner"
)

repeat_inventory = (
    repeat_inventory
    .sort_values(
        [
            "year",
            "driver_name",
            "car_number",
            "source_rank",
        ]
    )
)

# ============================================================
# Status summary
# ============================================================

status_summary = (
    attempts
    .groupby(
        [
            "year",
            "status"
        ]
    )
    .size()
    .reset_index(
        name="records"
    )
)

# ============================================================
# Diagnostics for unparsed rank-like lines
# ============================================================

parsed_pairs = set(
    zip(
        attempts["year"],
        attempts["source_line_no"]
    )
)

unparsed_rows = []

for _, row in df.iterrows():

    year = int(
        row["year"]
    )

    line_no = int(
        row["line_no"]
    )

    if (
        year,
        line_no
    ) in parsed_pairs:
        continue

    text = str(
        row["raw_line"]
    ).strip()

    if re.match(
        r"^\s*\d+\s+",
        text
    ):

        unparsed_rows.append({
            "year":
                year,

            "line_no":
                line_no,

            "raw_line":
                text,
        })

unparsed = pd.DataFrame(
    unparsed_rows
)

# ============================================================
# Save
# ============================================================

ATTEMPT_OUT = (
    OUT /
    "regime_official_attempt_inventory_v3.csv"
)

SUMMARY_OUT = (
    OUT /
    "regime_official_attempt_inventory_summary_v3.csv"
)

REPEAT_OUT = (
    OUT /
    "regime_official_repeat_candidates_v3.csv"
)

STATUS_OUT = (
    OUT /
    "regime_official_status_summary_v3.csv"
)

QA_OUT = (
    OUT /
    "regime_official_attempt_parse_qa_v3.csv"
)

UNPARSED_OUT = (
    OUT /
    "regime_unparsed_rank_like_lines_v3.csv"
)

attempts.to_csv(
    ATTEMPT_OUT,
    index=False
)

summary.to_csv(
    SUMMARY_OUT,
    index=False
)

repeat_inventory.to_csv(
    REPEAT_OUT,
    index=False
)

status_summary.to_csv(
    STATUS_OUT,
    index=False
)

qa.to_csv(
    QA_OUT,
    index=False
)

unparsed.to_csv(
    UNPARSED_OUT,
    index=False
)

# ============================================================
# Console
# ============================================================

print("=" * 150)
print("PART 1 — STRICT PARSE QA V3")
print("=" * 150)

print(
    qa.to_string(
        index=False
    )
)

print("\n" + "=" * 150)
print("PART 2 — STRICT ATTEMPT INVENTORY SUMMARY V3")
print("=" * 150)

print(
    summary.to_string(
        index=False
    )
)

print("\n" + "=" * 150)
print("PART 3 — UNPARSED RANK-LIKE LINES")
print("=" * 150)

if unparsed.empty:

    print(
        "NONE"
    )

else:

    print(
        unparsed.to_string(
            index=False
        )
    )

print("\n" + "=" * 150)
print("PART 4 — COMPLETE REPEAT CANDIDATES")
print("=" * 150)

if repeat_inventory.empty:

    print(
        "NO COMPLETE REPEAT CANDIDATES"
    )

else:

    cols = [
        "year",
        "source_rank",
        "car_number",
        "driver_name",
        "lap1_s",
        "lap2_s",
        "lap3_s",
        "lap4_s",
        "average_speed_mph",
        "status",
        "complete_attempts_for_entrant",
    ]

    print(
        repeat_inventory[
            cols
        ]
        .to_string(
            index=False
        )
    )

print("\nOUTPUTS:")
print(
    ATTEMPT_OUT.relative_to(
        ROOT
    )
)
print(
    SUMMARY_OUT.relative_to(
        ROOT
    )
)
print(
    REPEAT_OUT.relative_to(
        ROOT
    )
)
print(
    STATUS_OUT.relative_to(
        ROOT
    )
)
print(
    QA_OUT.relative_to(
        ROOT
    )
)
print(
    UNPARSED_OUT.relative_to(
        ROOT
    )
)

print(
    "\nR6_REGIME_ATTEMPT_INVENTORY_V3_COMPLETE"
)
