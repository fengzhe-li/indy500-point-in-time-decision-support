from pathlib import Path
import csv
import json
import re
import urllib.request
import urllib.parse

ROOT = Path(
    "/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈"
)

OUT = ROOT / "r4/output"
OUT.mkdir(parents=True, exist_ok=True)

EVIDENCE = (
    ROOT /
    "weather/evidence/last_chance_official"
)

EVIDENCE.mkdir(
    parents=True,
    exist_ok=True
)

YEARS = [
    2021,
    2023,
    2024,
]

HTML_FILES = {
    2021:
        EVIDENCE /
        "2021_last_chance_official_page.html",

    2023:
        EVIDENCE /
        "2023_last_chance_official_page.html",

    2024:
        EVIDENCE /
        "2024_last_chance_official_page.html",
}

OUT_EVENTS = (
    OUT /
    "r4lc2d_indy500_event_session_registry_v1.csv"
)

OUT_QA = (
    OUT /
    "r4lc2d_indy500_event_session_registry_qa_v1.csv"
)

OUT_REPORT = (
    OUT /
    "r4lc2d_indy500_event_session_registry_report_v1.json"
)


def fetch_json(url):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent":
                "Mozilla/5.0"
        }
    )

    try:
        with urllib.request.urlopen(
            req,
            timeout=30
        ) as response:

            body = response.read()

            text = body.decode(
                "utf-8",
                errors="ignore"
            )

            try:
                data = json.loads(
                    text
                )
            except Exception:
                data = None

            return {
                "status":
                    response.status,

                "content_type":
                    response.headers.get(
                        "Content-Type",
                        ""
                    ),

                "body":
                    body,

                "text":
                    text,

                "json":
                    data,

                "final_url":
                    response.geturl(),

                "error":
                    "",
            }

    except Exception as exc:
        return {
            "status":
                None,

            "content_type":
                "",

            "body":
                b"",

            "text":
                "",

            "json":
                None,

            "final_url":
                "",

            "error":
                repr(exc),
        }


def extract_hidden_value(html, field_id):
    patterns = [
        (
            r'<input[^>]+id=["\']'
            + re.escape(field_id)
            + r'["\'][^>]+value=["\']([^"\']+)["\']'
        ),
        (
            r'<input[^>]+value=["\']([^"\']+)["\'][^>]+id=["\']'
            + re.escape(field_id)
            + r'["\']'
        ),
    ]

    for pattern in patterns:

        m = re.search(
            pattern,
            html,
            flags=re.IGNORECASE
        )

        if m:
            return m.group(1).strip()

    return ""


def normalize_text(v):
    if v is None:
        return ""

    return str(v).strip()


def recursively_find_sessions(obj):
    found = []

    def walk(value, path="root"):

        if isinstance(
            value,
            dict
        ):

            keys_lower = {
                str(k).lower():
                    k
                for k in value.keys()
            }

            session_name_key = None
            session_id_key = None

            for candidate in [
                "sessionname",
                "session_name",
                "name",
            ]:
                if candidate in keys_lower:
                    session_name_key = (
                        keys_lower[candidate]
                    )
                    break

            for candidate in [
                "sessionid",
                "eventssessionid",
                "eventssessionsid",
                "session_id",
                "id",
            ]:
                if candidate in keys_lower:
                    session_id_key = (
                        keys_lower[candidate]
                    )
                    break

            if session_name_key:

                name = normalize_text(
                    value.get(
                        session_name_key
                    )
                )

                low = name.lower()

                if any(
                    token in low
                    for token in [
                        "last chance",
                        "last row",
                        "qualification",
                        "qualifying",
                    ]
                ):

                    found.append({
                        "path":
                            path,

                        "session_name":
                            name,

                        "session_id":
                            normalize_text(
                                value.get(
                                    session_id_key
                                )
                                if session_id_key
                                else ""
                            ),

                        "object":
                            value,
                    })

            for k, v in value.items():
                walk(
                    v,
                    f"{path}.{k}"
                )

        elif isinstance(
            value,
            list
        ):

            for i, v in enumerate(
                value
            ):
                walk(
                    v,
                    f"{path}[{i}]"
                )

    walk(
        obj
    )

    unique = []

    seen = set()

    for item in found:

        key = (
            item["session_name"],
            item["session_id"],
            item["path"],
        )

        if key not in seen:
            seen.add(
                key
            )
            unique.append(
                item
            )

    return unique


def recursively_find_indy500_events(obj):
    found = []

    def walk(value, path="root"):

        if isinstance(
            value,
            dict
        ):

            for k, v in value.items():

                if isinstance(
                    v,
                    str
                ):

                    low = v.lower()

                    if (
                        "indianapolis 500"
                        in low
                        or
                        "indy 500"
                        in low
                    ):

                        found.append({
                            "path":
                                path,

                            "matched_key":
                                k,

                            "matched_value":
                                v,

                            "object":
                                value,
                        })

                walk(
                    v,
                    f"{path}.{k}"
                )

        elif isinstance(
            value,
            list
        ):

            for i, v in enumerate(
                value
            ):
                walk(
                    v,
                    f"{path}[{i}]"
                )

    walk(
        obj
    )

    unique = []

    seen = set()

    for item in found:

        serialized = json.dumps(
            item["object"],
            sort_keys=True,
            default=str
        )

        if serialized not in seen:
            seen.add(
                serialized
            )
            unique.append(
                item
            )

    return unique


def find_event_id(obj):
    if not isinstance(
        obj,
        dict
    ):
        return ""

    candidates = [
        "EventID",
        "EventId",
        "eventID",
        "eventId",
        "event_id",
        "ID",
        "Id",
        "id",
    ]

    for key in candidates:

        if key in obj:

            value = normalize_text(
                obj.get(
                    key
                )
            )

            if value:
                return value

    return ""


registry_rows = []
qa_rows = []

series_ids = {}


print("=" * 116)
print("R4LC2D — INDY 500 EVENT + LAST CHANCE SESSION API PROBE")
print("=" * 116)


# =============================================================================
# 1. Resolve series ID from each saved official page
# =============================================================================

for year in YEARS:

    path = HTML_FILES[
        year
    ]

    if not path.exists():
        raise SystemExit(
            f"MISSING HTML: {path}"
        )

    html = path.read_text(
        encoding="utf-8",
        errors="ignore"
    )

    series_id = extract_hidden_value(
        html,
        "hdnSeries"
    )

    series_ids[
        year
    ] = series_id

    print()
    print(
        f"{year} series_id = "
        f"{series_id or 'UNRESOLVED'}"
    )


# =============================================================================
# 2. Query official EventsByYearSeries API
# =============================================================================

for year in YEARS:

    series_id = series_ids[
        year
    ]

    if not series_id:

        qa_rows.append({
            "metric":
                f"{year}_series_id_resolved",

            "value":
                False,

            "expected":
                True,

            "status":
                "FAIL",
        })

        continue

    qa_rows.append({
        "metric":
            f"{year}_series_id_resolved",

        "value":
            True,

        "expected":
            True,

        "status":
            "PASS",
    })

    params = urllib.parse.urlencode({
        "year":
            year,

        "id":
            series_id,
    })

    url = (
        "https://www.indycar.com"
        "/api/results/EventsByYearSeries?"
        + params
    )

    print()
    print(
        f"QUERY {year}: "
        f"{url}"
    )

    response = fetch_json(
        url
    )

    raw_path = (
        EVIDENCE /
        f"{year}_events_by_year_series.json"
    )

    if response["body"]:

        raw_path.write_bytes(
            response["body"]
        )

    print(
        f"HTTP={response['status']} | "
        f"bytes={len(response['body'])} | "
        f"json={response['json'] is not None}"
    )

    qa_rows.append({
        "metric":
            f"{year}_events_api_http_200",

        "value":
            response["status"],

        "expected":
            200,

        "status":
            (
                "PASS"
                if response["status"] == 200
                else "FAIL"
            ),
    })

    qa_rows.append({
        "metric":
            f"{year}_events_api_json",

        "value":
            response["json"] is not None,

        "expected":
            True,

        "status":
            (
                "PASS"
                if response["json"] is not None
                else "FAIL"
            ),
    })

    data = response[
        "json"
    ]

    if data is None:
        continue

    events = recursively_find_indy500_events(
        data
    )

    print(
        f"Indy 500 event candidates: "
        f"{len(events)}"
    )

    qa_rows.append({
        "metric":
            f"{year}_indy500_event_found",

        "value":
            len(events),

        "expected":
            ">0",

        "status":
            (
                "PASS"
                if events
                else "FAIL"
            ),
    })

    for idx, event in enumerate(
        events,
        start=1
    ):

        event_obj = event[
            "object"
        ]

        event_id = find_event_id(
            event_obj
        )

        event_path = (
            EVIDENCE /
            f"{year}_indy500_event_candidate_{idx}.json"
        )

        event_path.write_text(
            json.dumps(
                event_obj,
                indent=2,
                ensure_ascii=False,
                default=str
            ),
            encoding="utf-8"
        )

        sessions = recursively_find_sessions(
            event_obj
        )

        if not sessions:

            registry_rows.append({
                "year":
                    year,

                "series_id":
                    series_id,

                "event_id":
                    event_id,

                "event_match":
                    event[
                        "matched_value"
                    ],

                "event_object_path":
                    event[
                        "path"
                    ],

                "session_name":
                    "",

                "session_id":
                    "",

                "session_object_path":
                    "",

                "target_session":
                    False,

                "source":
                    "OFFICIAL_INDYCAR_RESULTS_API",
            })

        for session in sessions:

            low = (
                session[
                    "session_name"
                ].lower()
            )

            target = (
                "last chance" in low
                or
                "last row" in low
            )

            registry_rows.append({
                "year":
                    year,

                "series_id":
                    series_id,

                "event_id":
                    event_id,

                "event_match":
                    event[
                        "matched_value"
                    ],

                "event_object_path":
                    event[
                        "path"
                    ],

                "session_name":
                    session[
                        "session_name"
                    ],

                "session_id":
                    session[
                        "session_id"
                    ],

                "session_object_path":
                    session[
                        "path"
                    ],

                "target_session":
                    target,

                "source":
                    "OFFICIAL_INDYCAR_RESULTS_API",
            })


# =============================================================================
# 3. Save registry
# =============================================================================

fields = [
    "year",
    "series_id",
    "event_id",
    "event_match",
    "event_object_path",
    "session_name",
    "session_id",
    "session_object_path",
    "target_session",
    "source",
]

with OUT_EVENTS.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=fields
    )

    writer.writeheader()
    writer.writerows(
        registry_rows
    )


# =============================================================================
# 4. Target-session QA
# =============================================================================

for year in YEARS:

    targets = [
        r
        for r in registry_rows
        if (
            r["year"] == year
            and r["target_session"]
        )
    ]

    qa_rows.append({
        "metric":
            f"{year}_last_chance_session_found",

        "value":
            len(targets),

        "expected":
            ">0",

        "status":
            (
                "PASS"
                if targets
                else "WARN"
            ),
    })


with OUT_QA.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    fields_qa = [
        "metric",
        "value",
        "expected",
        "status",
    ]

    writer = csv.DictWriter(
        f,
        fieldnames=fields_qa
    )

    writer.writeheader()
    writer.writerows(
        qa_rows
    )


target_rows = [
    r
    for r in registry_rows
    if r["target_session"]
]


report = {
    "phase":
        "R4LC2D",

    "status":
        "R4LC2D_EVENT_SESSION_API_PROBE_READY",

    "years":
        YEARS,

    "series_ids":
        series_ids,

    "registry_rows":
        len(registry_rows),

    "target_last_chance_rows":
        len(target_rows),

    "purpose":
        (
            "Use the official INDYCAR Results API to resolve "
            "Indianapolis 500 event IDs and Last Chance / Last Row "
            "session identifiers before attempting detailed report ingestion."
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
# 5. Console
# =============================================================================

print()
print("=" * 116)
print("INDY 500 EVENT / SESSION REGISTRY")
print("=" * 116)

if not registry_rows:

    print(
        "NO REGISTRY ROWS"
    )

else:

    for r in registry_rows:

        print(
            f"{r['year']} | "
            f"event_id={r['event_id'] or '-'} | "
            f"session={r['session_name'] or '-'} | "
            f"session_id={r['session_id'] or '-'} | "
            f"target={r['target_session']}"
        )


print()
print("=" * 116)
print("TARGET LAST CHANCE / LAST ROW SESSIONS")
print("=" * 116)

if not target_rows:

    print(
        "NO TARGET SESSION DIRECTLY EXPOSED "
        "BY EventsByYearSeries"
    )

else:

    for r in target_rows:

        print(
            f"{r['year']} | "
            f"event_id={r['event_id']} | "
            f"session={r['session_name']} | "
            f"session_id={r['session_id']}"
        )


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

    print()
    print(
        "FAILED QA"
    )

    for r in fails:

        print(
            f"{r['metric']} | "
            f"value={r['value']} | "
            f"expected={r['expected']}"
        )

    raise SystemExit(1)


print()
print("OUTPUTS")
print(
    OUT_EVENTS.relative_to(ROOT)
)
print(
    OUT_QA.relative_to(ROOT)
)
print(
    OUT_REPORT.relative_to(ROOT)
)

print()
print(
    "R4LC2D_EVENT_SESSION_API_PROBE_READY"
)
