from pathlib import Path
import csv
import json
import urllib.parse
import urllib.request

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

SERIES_ID = (
    "b856a4f1-e85c-4fac-8c36-fd58d962227a"
)

EVENTS = {
    2021: 5365,
    2023: 5431,
    2024: 5465,
}

OUT_SESSIONS = (
    OUT /
    "r4lc2f_last_chance_session_registry_v2.csv"
)

OUT_DETAILS = (
    OUT /
    "r4lc2f_last_chance_session_details_summary_v2.csv"
)

OUT_DRIVER_PROBES = (
    OUT /
    "r4lc2f_driver_event_probe_summary_v2.csv"
)

OUT_QA = (
    OUT /
    "r4lc2f_last_chance_session_details_qa_v2.csv"
)

OUT_REPORT = (
    OUT /
    "r4lc2f_last_chance_session_details_report_v2.json"
)


def fetch_json(url):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0"
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

                "body":
                    body,

                "text":
                    text,

                "json":
                    data,

                "error":
                    "",
            }

    except Exception as exc:

        return {
            "status":
                None,

            "body":
                b"",

            "text":
                "",

            "json":
                None,

            "error":
                repr(exc),
        }


def value(obj, candidates):
    if not isinstance(
        obj,
        dict
    ):
        return ""

    for key in candidates:

        if key in obj:

            v = obj.get(
                key
            )

            if v is not None:
                return str(
                    v
                ).strip()

    return ""


def is_target_session(name):
    low = (
        name
        or ""
    ).lower()

    return (
        "last chance" in low
        or
        "last row" in low
    )


print("=" * 118)
print("R4LC2F-v2 — EVENT-WIDE LAST CHANCE SESSION DISCOVERY")
print("=" * 118)

session_rows = []
detail_rows = []
driver_probe_rows = []
qa_rows = []


# =============================================================================
# 1. Scan ALL drivers for each Indy 500 event
# =============================================================================

for year, event_id in EVENTS.items():

    print()
    print("=" * 118)
    print(
        f"YEAR {year} | EVENT {event_id}"
    )
    print("=" * 118)

    params = urllib.parse.urlencode({
        "year":
            year,

        "id":
            SERIES_ID,
    })

    drivers_url = (
        "https://www.indycar.com"
        "/api/results/DriversByYear?"
        + params
    )

    driver_response = fetch_json(
        drivers_url
    )

    drivers = (
        driver_response["json"]
        if isinstance(
            driver_response["json"],
            list
        )
        else []
    )

    print(
        f"Drivers API | "
        f"HTTP={driver_response['status']} | "
        f"drivers={len(drivers)}"
    )

    qa_rows.append({
        "metric":
            f"{year}_drivers_api",

        "value":
            len(drivers),

        "expected":
            ">0",

        "status":
            (
                "PASS"
                if drivers
                else "FAIL"
            ),
    })

    session_union = {}
    successful_driver_objects = 0


    # =========================================================================
    # 2. Probe every driver and union all session lists
    # =========================================================================

    for driver in drivers:

        driver_id = value(
            driver,
            [
                "DriverOverrideID",
                "DriverOverrideId",
                "DriverID",
                "DriverId",
                "driverID",
                "driverId",
                "id",
            ]
        )

        first_name = value(
            driver,
            [
                "FirstName",
                "firstName",
            ]
        )

        last_name = value(
            driver,
            [
                "LastName",
                "lastName",
            ]
        )

        driver_name = (
            f"{first_name} {last_name}"
        ).strip()

        if not driver_id:
            continue

        params = urllib.parse.urlencode({
            "driverID":
                driver_id,

            "eventID":
                event_id,
        })

        url = (
            "https://www.indycar.com"
            "/api/results/DriverEventDetails?"
            + params
        )

        response = fetch_json(
            url
        )

        data = response[
            "json"
        ]

        if not isinstance(
            data,
            dict
        ):
            driver_probe_rows.append({
                "year":
                    year,

                "event_id":
                    event_id,

                "driver_id":
                    driver_id,

                "driver_name":
                    driver_name,

                "http_status":
                    response["status"],

                "session_count":
                    0,

                "target_session_count":
                    0,

                "status":
                    "NO_EVENT_OBJECT",
            })

            continue

        sessions = data.get(
            "EventSessionList"
        )

        if not isinstance(
            sessions,
            list
        ):
            sessions = []

        if sessions:
            successful_driver_objects += 1

        target_count = 0

        for session in sessions:

            session_name = value(
                session,
                [
                    "SessionName",
                    "sessionName",
                    "Name",
                    "name",
                ]
            )

            session_id = value(
                session,
                [
                    "SessionId",
                    "SessionID",
                    "EventsSessionID",
                    "EventsSessionsID",
                    "sessionId",
                    "id",
                ]
            )

            if not session_id:
                continue

            target = is_target_session(
                session_name
            )

            if target:
                target_count += 1

            key = (
                session_id,
                session_name,
            )

            if key not in session_union:

                session_union[key] = {
                    "year":
                        year,

                    "event_id":
                        event_id,

                    "session_id":
                        session_id,

                    "session_name":
                        session_name,

                    "target_last_chance":
                        target,

                    "first_driver_id_seen":
                        driver_id,

                    "first_driver_name_seen":
                        driver_name,

                    "drivers_exposing_session":
                        set(),
                }

            session_union[
                key
            ][
                "drivers_exposing_session"
            ].add(
                driver_name
                or driver_id
            )

        driver_probe_rows.append({
            "year":
                year,

            "event_id":
                event_id,

            "driver_id":
                driver_id,

            "driver_name":
                driver_name,

            "http_status":
                response["status"],

            "session_count":
                len(sessions),

            "target_session_count":
                target_count,

            "status":
                (
                    "TARGET_SESSION_FOUND"
                    if target_count > 0
                    else
                    "EVENT_OBJECT_NO_TARGET"
                    if sessions
                    else
                    "NO_SESSIONS"
                ),
        })


    # =========================================================================
    # 3. Print union and collect
    # =========================================================================

    year_sessions = []

    for key in sorted(
        session_union,
        key=lambda x: (
            x[1],
            x[0]
        )
    ):

        item = session_union[
            key
        ]

        row = {
            "year":
                item["year"],

            "event_id":
                item["event_id"],

            "session_id":
                item["session_id"],

            "session_name":
                item["session_name"],

            "target_last_chance":
                item["target_last_chance"],

            "first_driver_id_seen":
                item[
                    "first_driver_id_seen"
                ],

            "first_driver_name_seen":
                item[
                    "first_driver_name_seen"
                ],

            "drivers_exposing_session":
                ";".join(
                    sorted(
                        item[
                            "drivers_exposing_session"
                        ]
                    )
                ),

            "drivers_exposing_count":
                len(
                    item[
                        "drivers_exposing_session"
                    ]
                ),
        }

        session_rows.append(
            row
        )

        year_sessions.append(
            row
        )

    targets = [
        r
        for r in year_sessions
        if r[
            "target_last_chance"
        ]
    ]

    print()
    print(
        f"Successful driver event objects: "
        f"{successful_driver_objects}"
    )

    print(
        f"Unique event sessions across all drivers: "
        f"{len(year_sessions)}"
    )

    print()
    print("EVENT-WIDE SESSION UNION")

    for row in year_sessions:

        print(
            f"  session_id="
            f"{row['session_id']:6s} | "
            f"{row['session_name'] or '-':35s} | "
            f"drivers={row['drivers_exposing_count']:2d} | "
            f"target={row['target_last_chance']}"
        )

    print()
    print(
        f"Target Last Chance/Last Row sessions: "
        f"{len(targets)}"
    )

    for row in targets:

        print(
            f"  TARGET | "
            f"session_id={row['session_id']} | "
            f"{row['session_name']} | "
            f"seen via {row['drivers_exposing_count']} drivers"
        )

    qa_rows.append({
        "metric":
            f"{year}_driver_event_objects_found",

        "value":
            successful_driver_objects,

        "expected":
            ">0",

        "status":
            (
                "PASS"
                if successful_driver_objects > 0
                else "FAIL"
            ),
    })

    qa_rows.append({
        "metric":
            f"{year}_event_wide_session_union_nonempty",

        "value":
            len(year_sessions),

        "expected":
            ">0",

        "status":
            (
                "PASS"
                if year_sessions
                else "FAIL"
            ),
    })

    qa_rows.append({
        "metric":
            f"{year}_target_session_found",

        "value":
            len(targets),

        "expected":
            ">0",

        "status":
            (
                "PASS"
                if targets
                else "FAIL"
            ),
    })


    # =========================================================================
    # 4. Fetch EventsSessionDetails for each target session
    # =========================================================================

    for target in targets:

        session_id = target[
            "session_id"
        ]

        params = urllib.parse.urlencode({
            "id":
                session_id
        })

        details_url = (
            "https://www.indycar.com"
            "/api/results/EventsSessionDetails?"
            + params
        )

        details_response = fetch_json(
            details_url
        )

        details_data = details_response[
            "json"
        ]

        raw_path = (
            EVIDENCE /
            f"{year}_last_chance_session_{session_id}_v2.json"
        )

        if details_response["body"]:

            raw_path.write_bytes(
                details_response[
                    "body"
                ]
            )

        print()
        print(
            f"SESSION DETAILS | "
            f"{year} | "
            f"id={session_id}"
        )

        print(
            f"  HTTP="
            f"{details_response['status']} | "
            f"bytes="
            f"{len(details_response['body'])} | "
            f"json="
            f"{details_data is not None}"
        )

        if not isinstance(
            details_data,
            dict
        ):

            qa_rows.append({
                "metric":
                    f"{year}_session_{session_id}_details_json",

                "value":
                    False,

                "expected":
                    True,

                "status":
                    "FAIL",
            })

            continue

        keys = sorted(
            details_data.keys()
        )

        list_containers = []

        for key, v in details_data.items():

            if isinstance(
                v,
                list
            ):

                list_containers.append(
                    f"{key}[{len(v)}]"
                )

        print(
            "  TOP-LEVEL KEYS:"
        )

        for key in keys:

            v = details_data[
                key
            ]

            if isinstance(
                v,
                list
            ):

                print(
                    f"    {key}: "
                    f"LIST[{len(v)}]"
                )

            elif isinstance(
                v,
                dict
            ):

                print(
                    f"    {key}: "
                    f"DICT[{len(v)}]"
                )

            else:

                txt = str(
                    v
                )

                if len(txt) > 120:
                    txt = (
                        txt[:117]
                        + "..."
                    )

                print(
                    f"    {key}: "
                    f"{txt}"
                )

        # Show first row of every list container.
        print(
            "  LIST CONTAINER SAMPLES:"
        )

        for key, v in details_data.items():

            if (
                isinstance(
                    v,
                    list
                )
                and v
            ):

                sample = v[
                    0
                ]

                sample_text = json.dumps(
                    sample,
                    ensure_ascii=False,
                    default=str
                )

                if len(
                    sample_text
                ) > 500:

                    sample_text = (
                        sample_text[:497]
                        + "..."
                    )

                print(
                    f"    {key}[0] = "
                    f"{sample_text}"
                )

        detail_rows.append({
            "year":
                year,

            "event_id":
                event_id,

            "session_id":
                session_id,

            "session_name":
                value(
                    details_data,
                    [
                        "SessionName",
                        "sessionName",
                    ]
                ),

            "session_type":
                value(
                    details_data,
                    [
                        "SessionType",
                        "sessionType",
                    ]
                ),

            "event_name":
                value(
                    details_data,
                    [
                        "EventName",
                        "eventName",
                    ]
                ),

            "http_status":
                details_response[
                    "status"
                ],

            "bytes":
                len(
                    details_response[
                        "body"
                    ]
                ),

            "top_level_keys":
                ";".join(
                    keys
                ),

            "list_containers":
                ";".join(
                    list_containers
                ),

            "raw_json_path":
                str(
                    raw_path.relative_to(
                        ROOT
                    )
                ),
        })

        qa_rows.append({
            "metric":
                f"{year}_session_{session_id}_details_json",

            "value":
                True,

            "expected":
                True,

            "status":
                "PASS",
        })


# =============================================================================
# 5. Save CSV outputs
# =============================================================================

with OUT_SESSIONS.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    fields = [
        "year",
        "event_id",
        "session_id",
        "session_name",
        "target_last_chance",
        "first_driver_id_seen",
        "first_driver_name_seen",
        "drivers_exposing_session",
        "drivers_exposing_count",
    ]

    writer = csv.DictWriter(
        f,
        fieldnames=fields
    )

    writer.writeheader()
    writer.writerows(
        session_rows
    )


with OUT_DETAILS.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    fields = [
        "year",
        "event_id",
        "session_id",
        "session_name",
        "session_type",
        "event_name",
        "http_status",
        "bytes",
        "top_level_keys",
        "list_containers",
        "raw_json_path",
    ]

    writer = csv.DictWriter(
        f,
        fieldnames=fields
    )

    writer.writeheader()
    writer.writerows(
        detail_rows
    )


with OUT_DRIVER_PROBES.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    fields = [
        "year",
        "event_id",
        "driver_id",
        "driver_name",
        "http_status",
        "session_count",
        "target_session_count",
        "status",
    ]

    writer = csv.DictWriter(
        f,
        fieldnames=fields
    )

    writer.writeheader()
    writer.writerows(
        driver_probe_rows
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


target_rows = [
    r
    for r in session_rows
    if r[
        "target_last_chance"
    ]
]


report = {
    "phase":
        "R4LC2F_V2",

    "status":
        "R4LC2F_V2_EVENT_WIDE_LAST_CHANCE_SESSION_DISCOVERY_READY",

    "years":
        list(
            EVENTS.keys()
        ),

    "event_ids":
        EVENTS,

    "driver_probe_rows":
        len(
            driver_probe_rows
        ),

    "unique_session_rows":
        len(
            session_rows
        ),

    "target_session_rows":
        len(
            target_rows
        ),

    "session_details_rows":
        len(
            detail_rows
        ),

    "important_fix":
        (
            "DriverEventDetails exposes driver-specific session "
            "participation rather than a guaranteed event-wide "
            "session list. Version 2 unions sessions across all "
            "drivers before identifying Last Row / Last Chance."
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
# 6. Final console
# =============================================================================

print()
print("=" * 118)
print("FINAL TARGET SESSION REGISTRY")
print("=" * 118)

for row in target_rows:

    print(
        f"{row['year']} | "
        f"event={row['event_id']} | "
        f"session_id={row['session_id']} | "
        f"{row['session_name']} | "
        f"drivers_exposing="
        f"{row['drivers_exposing_count']}"
    )


print()
print("=" * 118)
print("FINAL SESSION DETAILS SUMMARY")
print("=" * 118)

for row in detail_rows:

    print(
        f"{row['year']} | "
        f"session_id={row['session_id']} | "
        f"type={row['session_type']} | "
        f"bytes={row['bytes']} | "
        f"lists={row['list_containers']}"
    )

    print(
        f"  keys="
        f"{row['top_level_keys']}"
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
    print("FAILED QA")

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
    OUT_SESSIONS.relative_to(ROOT)
)
print(
    OUT_DETAILS.relative_to(ROOT)
)
print(
    OUT_DRIVER_PROBES.relative_to(ROOT)
)
print(
    OUT_QA.relative_to(ROOT)
)
print(
    OUT_REPORT.relative_to(ROOT)
)

print()
print(
    "R4LC2F_V2_EVENT_WIDE_LAST_CHANCE_SESSION_DISCOVERY_READY"
)
