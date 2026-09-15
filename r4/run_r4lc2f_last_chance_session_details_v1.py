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
    "r4lc2f_last_chance_session_registry_v1.csv"
)

OUT_DETAILS = (
    OUT /
    "r4lc2f_last_chance_session_details_summary_v1.csv"
)

OUT_QA = (
    OUT /
    "r4lc2f_last_chance_session_details_qa_v1.csv"
)

OUT_REPORT = (
    OUT /
    "r4lc2f_last_chance_session_details_report_v1.json"
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


def target_session_name(name):
    low = (
        name
        or ""
    ).lower()

    return (
        "last chance" in low
        or
        "last row" in low
    )


print("=" * 116)
print("R4LC2F — LAST CHANCE SESSION DETAILS")
print("=" * 116)

session_rows = []
detail_rows = []
qa_rows = []


# =============================================================================
# 1. For each year, get drivers
# =============================================================================

for year, event_id in EVENTS.items():

    print()
    print(
        "=" * 116
    )
    print(
        f"YEAR {year} | EVENT {event_id}"
    )
    print(
        "=" * 116
    )

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

    driver_raw = (
        EVIDENCE /
        f"{year}_drivers_by_year.json"
    )

    if driver_response["body"]:

        driver_raw.write_bytes(
            driver_response["body"]
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


    # =========================================================================
    # 2. Probe drivers until we obtain an Indy 500 EventSessionList
    # =========================================================================

    target_sessions = []
    usable_driver_count = 0

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
            continue

        sessions = data.get(
            "EventSessionList"
        )

        if not isinstance(
            sessions,
            list
        ):
            continue

        if not sessions:
            continue

        usable_driver_count += 1

        print()
        print(
            f"Using driver: "
            f"{driver_name or driver_id}"
        )

        print(
            f"Event sessions returned: "
            f"{len(sessions)}"
        )

        event_raw = (
            EVIDENCE /
            f"{year}_driver_event_details_{driver_id}.json"
        )

        event_raw.write_text(
            json.dumps(
                data,
                indent=2,
                ensure_ascii=False
            ),
            encoding="utf-8"
        )

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

            is_target = target_session_name(
                session_name
            )

            row = {
                "year":
                    year,

                "event_id":
                    event_id,

                "driver_id_used":
                    driver_id,

                "driver_name_used":
                    driver_name,

                "session_id":
                    session_id,

                "session_name":
                    session_name,

                "target_last_chance":
                    is_target,
            }

            session_rows.append(
                row
            )

            print(
                f"  session_id={session_id or '-'} | "
                f"{session_name or '-'} | "
                f"target={is_target}"
            )

            if is_target:
                target_sessions.append(
                    row
                )

        # Session list is event-level metadata.
        # Once we have one valid complete list, stop probing drivers.
        break


    print()
    print(
        f"Usable driver event objects: "
        f"{usable_driver_count}"
    )

    print(
        f"Target Last Chance/Last Row sessions: "
        f"{len(target_sessions)}"
    )

    qa_rows.append({
        "metric":
            f"{year}_event_session_list_found",

        "value":
            usable_driver_count,

        "expected":
            ">0",

        "status":
            (
                "PASS"
                if usable_driver_count > 0
                else "FAIL"
            ),
    })

    qa_rows.append({
        "metric":
            f"{year}_target_session_found",

        "value":
            len(target_sessions),

        "expected":
            ">0",

        "status":
            (
                "PASS"
                if target_sessions
                else "FAIL"
            ),
    })


    # =========================================================================
    # 3. Fetch official EventsSessionDetails for target sessions
    # =========================================================================

    seen_session_ids = set()

    for target in target_sessions:

        session_id = target[
            "session_id"
        ]

        if (
            not session_id
            or session_id in seen_session_ids
        ):
            continue

        seen_session_ids.add(
            session_id
        )

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
            f"{year}_last_chance_session_{session_id}.json"
        )

        if details_response["body"]:

            raw_path.write_bytes(
                details_response["body"]
            )

        print()
        print(
            f"SESSION DETAILS {year}"
        )

        print(
            f"  session_id={session_id}"
        )

        print(
            f"  HTTP={details_response['status']}"
        )

        print(
            f"  bytes={len(details_response['body'])}"
        )

        print(
            f"  json={details_data is not None}"
        )

        if isinstance(
            details_data,
            dict
        ):

            keys = sorted(
                details_data.keys()
            )

            print(
                "  top-level keys:"
            )

            for key in keys:

                v = details_data.get(
                    key
                )

                if isinstance(
                    v,
                    list
                ):
                    descriptor = (
                        f"LIST[{len(v)}]"
                    )

                elif isinstance(
                    v,
                    dict
                ):
                    descriptor = (
                        f"DICT[{len(v)}]"
                    )

                else:
                    text = str(
                        v
                    )

                    if len(text) > 100:
                        text = (
                            text[:97]
                            + "..."
                        )

                    descriptor = (
                        f"{type(v).__name__}: "
                        f"{text}"
                    )

                print(
                    f"    {key}: "
                    f"{descriptor}"
                )

            session_name = value(
                details_data,
                [
                    "SessionName",
                    "sessionName",
                ]
            )

            session_type = value(
                details_data,
                [
                    "SessionType",
                    "sessionType",
                ]
            )

            event_name = value(
                details_data,
                [
                    "EventName",
                    "eventName",
                ]
            )

            result_container_keys = []

            for key, v in details_data.items():

                if isinstance(
                    v,
                    list
                ):

                    low = key.lower()

                    if any(
                        token in low
                        for token in [
                            "result",
                            "driver",
                            "qual",
                            "entry",
                            "position",
                            "lap",
                        ]
                    ):
                        result_container_keys.append(
                            f"{key}[{len(v)}]"
                        )

            detail_rows.append({
                "year":
                    year,

                "event_id":
                    event_id,

                "session_id":
                    session_id,

                "event_name":
                    event_name,

                "session_name":
                    session_name,

                "session_type":
                    session_type,

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

                "top_level_key_count":
                    len(
                        details_data
                    ),

                "top_level_keys":
                    ";".join(
                        keys
                    ),

                "result_container_keys":
                    ";".join(
                        result_container_keys
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
                    f"{year}_session_details_json",

                "value":
                    True,

                "expected":
                    True,

                "status":
                    "PASS",
            })

        else:

            qa_rows.append({
                "metric":
                    f"{year}_session_details_json",

                "value":
                    False,

                "expected":
                    True,

                "status":
                    "FAIL",
            })


# =============================================================================
# 4. De-duplicate session registry
# =============================================================================

unique_sessions = []

seen = set()

for row in session_rows:

    key = (
        row["year"],
        row["session_id"],
        row["session_name"],
    )

    if key in seen:
        continue

    seen.add(
        key
    )

    unique_sessions.append(
        row
    )


# =============================================================================
# 5. Write outputs
# =============================================================================

with OUT_SESSIONS.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    fields = [
        "year",
        "event_id",
        "driver_id_used",
        "driver_name_used",
        "session_id",
        "session_name",
        "target_last_chance",
    ]

    writer = csv.DictWriter(
        f,
        fieldnames=fields
    )

    writer.writeheader()
    writer.writerows(
        unique_sessions
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
        "event_name",
        "session_name",
        "session_type",
        "http_status",
        "bytes",
        "top_level_key_count",
        "top_level_keys",
        "result_container_keys",
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


target_registry = [
    row
    for row in unique_sessions
    if row["target_last_chance"]
]


report = {
    "phase":
        "R4LC2F",

    "status":
        "R4LC2F_LAST_CHANCE_SESSION_DETAILS_READY",

    "event_ids":
        EVENTS,

    "target_session_count":
        len(
            target_registry
        ),

    "session_details_count":
        len(
            detail_rows
        ),

    "research_purpose":
        (
            "Resolve Last Row / Last Chance session IDs "
            "through official DriverEventDetails metadata "
            "and retrieve official EventsSessionDetails JSON."
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
# 6. Console summary
# =============================================================================

print()
print("=" * 116)
print("TARGET SESSION REGISTRY")
print("=" * 116)

for row in target_registry:

    print(
        f"{row['year']} | "
        f"event={row['event_id']} | "
        f"session_id={row['session_id']} | "
        f"{row['session_name']}"
    )


print()
print("=" * 116)
print("SESSION DETAILS SUMMARY")
print("=" * 116)

for row in detail_rows:

    print(
        f"{row['year']} | "
        f"session_id={row['session_id']} | "
        f"type={row['session_type']} | "
        f"bytes={row['bytes']} | "
        f"containers={row['result_container_keys'] or '-'}"
    )

    print(
        f"  keys="
        f"{row['top_level_keys']}"
    )


fails = [
    row
    for row in qa_rows
    if row["status"] == "FAIL"
]

warns = [
    row
    for row in qa_rows
    if row["status"] == "WARN"
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

    for row in fails:

        print(
            f"{row['metric']} | "
            f"value={row['value']} | "
            f"expected={row['expected']}"
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
    OUT_QA.relative_to(ROOT)
)
print(
    OUT_REPORT.relative_to(ROOT)
)

print()
print(
    "R4LC2F_LAST_CHANCE_SESSION_DETAILS_READY"
)
