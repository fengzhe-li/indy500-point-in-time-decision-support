from pathlib import Path
import csv
import json
import re

ROOT = Path(
    "/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈"
)

OUT = ROOT / "r4/output"
OUT.mkdir(parents=True, exist_ok=True)

BUNDLE = (
    ROOT /
    "weather/evidence/last_chance_official/"
    "indycar_v2_bundle.js"
)

OUT_ENDPOINTS = (
    OUT /
    "r4lc2e_results_api_endpoints_v1.csv"
)

OUT_CONTEXT = (
    OUT /
    "r4lc2e_results_api_endpoint_context_v1.csv"
)

OUT_QA = (
    OUT /
    "r4lc2e_results_api_endpoint_qa_v1.csv"
)

OUT_REPORT = (
    OUT /
    "r4lc2e_results_api_endpoint_report_v1.json"
)


if not BUNDLE.exists():
    raise SystemExit(
        f"MISSING BUNDLE: {BUNDLE}"
    )


text = BUNDLE.read_text(
    encoding="utf-8",
    errors="ignore"
)


# =============================================================================
# 1. Extract explicit /api/results/... fragments
# =============================================================================

patterns = [
    r'/api/results/[A-Za-z0-9_./?=&%-]+',
    r'api/results/[A-Za-z0-9_./?=&%-]+',
]

hits = []

for pattern in patterns:

    for m in re.finditer(
        pattern,
        text,
        flags=re.IGNORECASE
    ):

        raw = m.group(0)

        if not raw.startswith("/"):
            raw = "/" + raw

        # Trim common JS concatenation artifacts.
        raw = raw.rstrip(
            ".,;:)]}"
        )

        hits.append({
            "position":
                m.start(),

            "endpoint_fragment":
                raw,
        })


# =============================================================================
# 2. Normalize to endpoint base name
# =============================================================================

endpoint_map = {}

for hit in hits:

    fragment = hit[
        "endpoint_fragment"
    ]

    base = fragment.split(
        "?"
    )[0]

    # Stop if extraction swallowed an operator.
    base = re.split(
        r'["\' +]',
        base
    )[0]

    if not base.lower().startswith(
        "/api/results/"
    ):
        continue

    endpoint_map.setdefault(
        base,
        []
    ).append(
        hit["position"]
    )


endpoint_rows = []

for endpoint in sorted(
    endpoint_map
):

    low = endpoint.lower()

    if any(
        token in low
        for token in [
            "session",
            "event",
            "race",
            "result",
            "report",
            "detail",
        ]
    ):
        priority = "HIGH"
    else:
        priority = "NORMAL"

    endpoint_rows.append({
        "endpoint":
            endpoint,

        "occurrences":
            len(
                endpoint_map[
                    endpoint
                ]
            ),

        "first_position":
            min(
                endpoint_map[
                    endpoint
                ]
            ),

        "priority_for_session_discovery":
            priority,
    })


# =============================================================================
# 3. Save useful context around every Results endpoint
# =============================================================================

context_rows = []

seen_context = set()

for endpoint, positions in endpoint_map.items():

    for position in positions:

        start = max(
            0,
            position - 500
        )

        end = min(
            len(text),
            position + 1100
        )

        context = (
            text[start:end]
            .replace("\n", " ")
            .replace("\r", " ")
        )

        key = (
            endpoint,
            context
        )

        if key in seen_context:
            continue

        seen_context.add(
            key
        )

        # Pull parameter-looking names from nearby JS.
        params = sorted(
            set(
                re.findall(
                    r'(?:eventID|eventId|EventID|'
                    r'sessionID|sessionId|SessionID|'
                    r'year|series|id|driverID|raceID)',
                    context
                )
            )
        )

        context_rows.append({
            "endpoint":
                endpoint,

            "position":
                position,

            "parameter_tokens":
                ";".join(
                    params
                ),

            "context":
                context,
        })


# =============================================================================
# 4. QA
# =============================================================================

known_expected = {
    "/api/results/YearsBySeries",
    "/api/results/DriversByYear",
    "/api/results/EventsByYearSeries",
    "/api/results/DriverEventDetails",
    "/api/results/YearPointSummary",
}

found = {
    r["endpoint"]
    for r in endpoint_rows
}

known_found = sorted(
    known_expected
    & found
)

session_like = [
    r
    for r in endpoint_rows
    if any(
        token in r["endpoint"].lower()
        for token in [
            "session",
            "event",
            "detail",
            "report",
        ]
    )
]


qa_rows = [
    {
        "metric":
            "bundle_nonempty",

        "value":
            len(text),

        "expected":
            ">10000",

        "status":
            (
                "PASS"
                if len(text) > 10000
                else "FAIL"
            ),
    },

    {
        "metric":
            "results_endpoints_found",

        "value":
            len(endpoint_rows),

        "expected":
            ">0",

        "status":
            (
                "PASS"
                if endpoint_rows
                else "FAIL"
            ),
    },

    {
        "metric":
            "known_results_endpoints_recovered",

        "value":
            len(known_found),

        "expected":
            ">=3",

        "status":
            (
                "PASS"
                if len(known_found) >= 3
                else "FAIL"
            ),
    },

    {
        "metric":
            "session_or_event_related_endpoint_found",

        "value":
            len(session_like),

        "expected":
            ">0",

        "status":
            (
                "PASS"
                if session_like
                else "WARN"
            ),
    },
]


# =============================================================================
# 5. Write outputs
# =============================================================================

with OUT_ENDPOINTS.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    fields = [
        "endpoint",
        "occurrences",
        "first_position",
        "priority_for_session_discovery",
    ]

    writer = csv.DictWriter(
        f,
        fieldnames=fields
    )

    writer.writeheader()
    writer.writerows(
        endpoint_rows
    )


with OUT_CONTEXT.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    fields = [
        "endpoint",
        "position",
        "parameter_tokens",
        "context",
    ]

    writer = csv.DictWriter(
        f,
        fieldnames=fields
    )

    writer.writeheader()
    writer.writerows(
        context_rows
    )


with OUT_QA.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    fields = [
        "metric",
        "value",
        "expected",
        "status",
    ]

    writer = csv.DictWriter(
        f,
        fieldnames=fields
    )

    writer.writeheader()
    writer.writerows(
        qa_rows
    )


report = {
    "phase":
        "R4LC2E",

    "status":
        "R4LC2E_RESULTS_API_ENDPOINT_MAP_READY",

    "bundle_characters":
        len(text),

    "endpoint_count":
        len(endpoint_rows),

    "known_expected_endpoints":
        sorted(
            known_expected
        ),

    "known_recovered_endpoints":
        known_found,

    "session_event_candidates":
        [
            r["endpoint"]
            for r in session_like
        ],

    "purpose":
        (
            "Recover exact INDYCAR Results API endpoint names "
            "from the site's own JavaScript bundle before probing "
            "event/session/report resources."
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
# 6. Console
# =============================================================================

print("=" * 116)
print("R4LC2E — INDYCAR RESULTS API ENDPOINT MAP")
print("=" * 116)

print()
print("ALL RESULTS API ENDPOINTS")

for row in endpoint_rows:

    print(
        f"{row['priority_for_session_discovery']:6s} | "
        f"{row['occurrences']:3d} | "
        f"{row['endpoint']}"
    )


print()
print("=" * 116)
print("HIGH-PRIORITY SESSION / EVENT ENDPOINTS")
print("=" * 116)

if not session_like:

    print(
        "NO SESSION/EVENT-LIKE ENDPOINT FOUND"
    )

else:

    for row in session_like:

        print(
            row["endpoint"]
        )


print()
print("=" * 116)
print("CONTEXT FOR HIGH-PRIORITY ENDPOINTS")
print("=" * 116)

high_names = {
    r["endpoint"]
    for r in session_like
}

shown = 0

for row in context_rows:

    if row["endpoint"] not in high_names:
        continue

    print()
    print(
        f"[{row['endpoint']}]"
    )

    print(
        "PARAMETERS:",
        row["parameter_tokens"]
        or "-"
    )

    print(
        row["context"]
    )

    shown += 1

    if shown >= 20:
        break


fails = [
    r
    for r in qa_rows
    if r["status"] == "FAIL"
]

warns = [
    r
    for r in qa_rows
    if r["status"] == "WARN"
]

print()
print(
    f"QA: "
    f"{len(qa_rows)-len(fails)-len(warns)} PASS | "
    f"{len(warns)} WARN | "
    f"{len(fails)} FAIL"
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
    OUT_ENDPOINTS.relative_to(ROOT)
)
print(
    OUT_CONTEXT.relative_to(ROOT)
)
print(
    OUT_QA.relative_to(ROOT)
)
print(
    OUT_REPORT.relative_to(ROOT)
)

print()
print(
    "R4LC2E_RESULTS_API_ENDPOINT_MAP_READY"
)
