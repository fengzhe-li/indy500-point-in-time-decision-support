from pathlib import Path
from urllib.parse import urlencode, urljoin
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

import csv
import hashlib
import json
import re
import time


# ============================================================
# PHASE
# ============================================================

PHASE = "R1E"
POLICY_VERSION = "OFFICIAL_INDY500_DAY1_SESSION_REPORT_RECOVERY_V1"


# ============================================================
# OFFICIAL RESULTS API
# ============================================================

BASE_URL = "https://www.indycar.com"

EVENTS_BY_YEAR_ENDPOINT = (
    BASE_URL
    + "/api/results/EventsByYearSeries"
)

SESSION_DETAILS_ENDPOINT = (
    BASE_URL
    + "/api/results/EventsSessionDetails"
)

# Recovered directly from the official INDYCAR Results frontend.
SERIES_ID = "09341e09-3216-4f89-a45f-db697d72ee13"


# ============================================================
# TARGETS
# ============================================================

TARGET_DATES = {
    2020: "2020-08-15",
    2021: "2021-05-22",
    2022: "2022-05-21",
    2023: "2023-05-20",
    2024: "2024-05-18",
}


# ============================================================
# OUTPUT PATHS
# ============================================================

OUTPUT_DIR = Path(
    "weather/output"
)

EVIDENCE_DIR = Path(
    "weather/evidence/rescue/"
    "official_indy500_day1_sessions"
)

RAW_API_DIR = (
    EVIDENCE_DIR
    / "raw_api"
)

REPORT_DIR = (
    EVIDENCE_DIR
    / "reports"
)

EVENT_INVENTORY_FILE = (
    OUTPUT_DIR
    / "official_indy500_event_inventory_v1.csv"
)

SESSION_INVENTORY_FILE = (
    OUTPUT_DIR
    / "official_indy500_session_inventory_v1.csv"
)

DAY1_SESSION_FILE = (
    OUTPUT_DIR
    / "official_indy500_day1_session_candidates_v1.csv"
)

REPORT_INVENTORY_FILE = (
    OUTPUT_DIR
    / "official_indy500_day1_report_inventory_v1.csv"
)

FETCH_AUDIT_FILE = (
    OUTPUT_DIR
    / "official_indy500_day1_api_fetch_audit_v1.csv"
)

QA_FILE = (
    OUTPUT_DIR
    / "official_indy500_day1_session_report_recovery_v1_qa.csv"
)

REPORT_FILE = (
    OUTPUT_DIR
    / "official_indy500_day1_session_report_recovery_v1.md"
)


# ============================================================
# NETWORK
# ============================================================

USER_AGENT = (
    "Mozilla/5.0 "
    "(compatible; Indy500HistoricalEvidenceResearch/1.0)"
)

REQUEST_TIMEOUT_SECONDS = 30
REQUEST_DELAY_SECONDS = 0.8


# ============================================================
# HELPERS
# ============================================================

def fetch_url(
    url,
):

    request = Request(
        url,
        headers={
            "User-Agent":
                USER_AGENT,

            "Accept":
                (
                    "application/json,"
                    "application/pdf,"
                    "text/plain,"
                    "*/*;q=0.8"
                ),
        },
    )

    started = time.time()

    try:

        with urlopen(
            request,
            timeout=REQUEST_TIMEOUT_SECONDS,
        ) as response:

            body = response.read()

            return {
                "ok":
                    True,

                "status_code":
                    getattr(
                        response,
                        "status",
                        200,
                    ),

                "content_type":
                    response.headers.get(
                        "Content-Type",
                        "",
                    ),

                "final_url":
                    response.geturl(),

                "body":
                    body,

                "elapsed_seconds":
                    time.time()
                    - started,

                "error":
                    "",
            }

    except HTTPError as exc:

        return {
            "ok":
                False,

            "status_code":
                exc.code,

            "content_type":
                "",

            "final_url":
                url,

            "body":
                b"",

            "elapsed_seconds":
                time.time()
                - started,

            "error":
                f"HTTPError: {exc}",
        }

    except URLError as exc:

        return {
            "ok":
                False,

            "status_code":
                None,

            "content_type":
                "",

            "final_url":
                url,

            "body":
                b"",

            "elapsed_seconds":
                time.time()
                - started,

            "error":
                f"URLError: {exc}",
        }

    except Exception as exc:

        return {
            "ok":
                False,

            "status_code":
                None,

            "content_type":
                "",

            "final_url":
                url,

            "body":
                b"",

            "elapsed_seconds":
                time.time()
                - started,

            "error":
                (
                    f"{type(exc).__name__}: "
                    f"{exc}"
                ),
        }


def decode_text(
    body,
):

    for encoding in [
        "utf-8",
        "utf-8-sig",
        "latin-1",
    ]:

        try:

            return body.decode(
                encoding
            )

        except Exception:
            pass

    return body.decode(
        "utf-8",
        errors="replace",
    )


def parse_json(
    body,
    source_label,
):

    text = decode_text(
        body
    )

    try:

        return json.loads(
            text
        )

    except Exception as exc:

        raise RuntimeError(
            f"Could not parse JSON from "
            f"{source_label}: {exc}\n"
            f"First 1000 chars:\n"
            f"{text[:1000]}"
        )


def sha256_bytes(
    body,
):

    return hashlib.sha256(
        body
    ).hexdigest()


def json_safe_write(
    path,
    data,
):

    path.write_text(
        json.dumps(
            data,
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
        ),
        encoding="utf-8",
    )


def first_present(
    mapping,
    keys,
):

    if not isinstance(
        mapping,
        dict,
    ):

        return None

    for key in keys:

        if key in mapping:

            value = mapping[
                key
            ]

            if value is not None:

                return value

    return None


def text_value(
    value,
):

    if value is None:
        return ""

    return str(
        value
    ).strip()


def normalize_date_text(
    value,
):

    value = text_value(
        value
    )

    if not value:
        return ""

    match = re.search(
        r"(\d{4})-(\d{2})-(\d{2})",
        value,
    )

    if match:

        return match.group(
            0
        )

    return value


def is_indy500_event(
    event_name,
):

    lower = (
        text_value(
            event_name
        )
        .lower()
    )

    return (
        "indianapolis"
        in lower
        and
        "500"
        in lower
    )


def is_day1_qualifying_name(
    session_name,
):

    lower = (
        text_value(
            session_name
        )
        .lower()
    )

    qualifying = (
        "qual"
        in lower
    )

    day1 = (
        "day 1"
        in lower
        or
        "day-1"
        in lower
        or
        "day one"
        in lower
        or
        "saturday"
        in lower
    )

    return (
        qualifying
        and
        day1
    )


def report_url_from_item(
    report,
):

    raw_url = text_value(
        first_present(
            report,
            [
                "Url",
                "URL",
                "url",
                "DocumentUrl",
                "DocumentURL",
            ],
        )
    )

    if not raw_url:
        return ""

    if raw_url.startswith(
        (
            "http://",
            "https://",
        )
    ):

        return raw_url

    return urljoin(
        "https://www.imscdn.com/",
        raw_url.lstrip(
            "/"
        ),
    )


def safe_filename(
    year,
    session_id,
    report_index,
    report_type,
    url,
    content_type,
):

    url_name = Path(
        url.split(
            "?"
        )[0]
    ).name

    if not url_name:

        url_name = (
            f"report_{report_index}"
        )

    url_name = re.sub(
        r"[^A-Za-z0-9._-]+",
        "_",
        url_name,
    )

    report_type_safe = re.sub(
        r"[^A-Za-z0-9._-]+",
        "_",
        text_value(
            report_type
        ),
    )

    if not report_type_safe:

        report_type_safe = (
            "UNKNOWN"
        )

    lower_ct = (
        text_value(
            content_type
        )
        .lower()
    )

    if (
        "pdf"
        in lower_ct
        and
        not url_name.lower().endswith(
            ".pdf"
        )
    ):

        url_name += ".pdf"

    return (
        f"{year}_"
        f"{session_id}_"
        f"{report_index:02d}_"
        f"{report_type_safe}_"
        f"{url_name}"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    RAW_API_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    REPORT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print()
    print("=" * 100)
    print(
        "PHASE R1E — OFFICIAL INDY 500 "
        "DAY 1 SESSION / REPORT RECOVERY V1"
    )
    print("=" * 100)

    print()
    print(
        "Official series ID:",
        SERIES_ID,
    )

    event_rows = []
    session_rows = []
    day1_rows = []
    report_rows = []
    fetch_rows = []

    # ========================================================
    # YEAR LOOP
    # ========================================================

    for year, target_date in (
        TARGET_DATES.items()
    ):

        print()
        print("=" * 90)
        print(
            f"YEAR {year}"
        )
        print("=" * 90)

        # ----------------------------------------------------
        # EventsByYearSeries
        # ----------------------------------------------------

        events_query = urlencode(
            {
                "year":
                    year,

                "id":
                    SERIES_ID,
            }
        )

        events_url = (
            EVENTS_BY_YEAR_ENDPOINT
            + "?"
            + events_query
        )

        print()
        print(
            "FETCH EVENTS:",
            events_url,
        )

        result = fetch_url(
            events_url
        )

        fetch_rows.append(
            {
                "year":
                    year,

                "request_type":
                    "EVENTS_BY_YEAR_SERIES",

                "request_url":
                    events_url,

                "ok":
                    result[
                        "ok"
                    ],

                "status_code":
                    result[
                        "status_code"
                    ],

                "content_type":
                    result[
                        "content_type"
                    ],

                "bytes":
                    len(
                        result[
                            "body"
                        ]
                    ),

                "sha256":
                    (
                        sha256_bytes(
                            result[
                                "body"
                            ]
                        )
                        if result[
                            "body"
                        ]
                        else ""
                    ),

                "error":
                    result[
                        "error"
                    ],
            }
        )

        if not result[
            "ok"
        ]:

            print(
                "FAILED:",
                result[
                    "error"
                ],
            )

            continue

        events_data = parse_json(
            result[
                "body"
            ],
            events_url,
        )

        events_raw_path = (
            RAW_API_DIR
            / f"{year}_events_by_year_series.json"
        )

        json_safe_write(
            events_raw_path,
            events_data,
        )

        if isinstance(
            events_data,
            dict,
        ):

            # Defensive support in case the API wraps the list.
            possible_lists = [
                events_data.get(
                    "Events"
                ),
                events_data.get(
                    "events"
                ),
                events_data.get(
                    "Data"
                ),
                events_data.get(
                    "data"
                ),
            ]

            events_list = next(
                (
                    item
                    for item in possible_lists
                    if isinstance(
                        item,
                        list,
                    )
                ),
                None,
            )

            if events_list is None:

                raise RuntimeError(
                    f"{year}: Events API returned "
                    f"unexpected object keys: "
                    f"{list(events_data.keys())}"
                )

        elif isinstance(
            events_data,
            list,
        ):

            events_list = (
                events_data
            )

        else:

            raise RuntimeError(
                f"{year}: unexpected Events API "
                f"type {type(events_data).__name__}"
            )

        print(
            "Events returned:",
            len(
                events_list
            ),
        )

        indy_events = []

        # ----------------------------------------------------
        # Event inventory
        # ----------------------------------------------------

        for event_index, event in enumerate(
            events_list,
            start=1,
        ):

            if not isinstance(
                event,
                dict,
            ):
                continue

            event_name = text_value(
                first_present(
                    event,
                    [
                        "EventName",
                        "eventName",
                        "Name",
                        "name",
                    ],
                )
            )

            event_id = text_value(
                first_present(
                    event,
                    [
                        "EventID",
                        "EventId",
                        "eventID",
                        "eventId",
                        "ID",
                        "Id",
                        "id",
                    ],
                )
            )

            sessions = first_present(
                event,
                [
                    "Sessions",
                    "sessions",
                    "EventSessions",
                    "eventSessions",
                ],
            )

            if not isinstance(
                sessions,
                list,
            ):

                sessions = []

            indy500_flag = is_indy500_event(
                event_name
            )

            event_rows.append(
                {
                    "year":
                        year,

                    "event_index":
                        event_index,

                    "event_id":
                        event_id,

                    "event_name":
                        event_name,

                    "session_count":
                        len(
                            sessions
                        ),

                    "is_indianapolis_500":
                        indy500_flag,

                    "raw_api_path":
                        str(
                            events_raw_path
                        ),
                }
            )

            if indy500_flag:

                indy_events.append(
                    event
                )

        print(
            "Indianapolis 500 event candidates:",
            len(
                indy_events
            ),
        )

        for indy_index, event in enumerate(
            indy_events,
            start=1,
        ):

            event_name = text_value(
                first_present(
                    event,
                    [
                        "EventName",
                        "eventName",
                        "Name",
                        "name",
                    ],
                )
            )

            event_id = text_value(
                first_present(
                    event,
                    [
                        "EventID",
                        "EventId",
                        "eventID",
                        "eventId",
                        "ID",
                        "Id",
                        "id",
                    ],
                )
            )

            sessions = first_present(
                event,
                [
                    "Sessions",
                    "sessions",
                    "EventSessions",
                    "eventSessions",
                ],
            )

            if not isinstance(
                sessions,
                list,
            ):

                sessions = []

            print()
            print(
                f"INDY EVENT {indy_index}: "
                f"{event_name}"
            )

            print(
                "Event ID:",
                event_id,
            )

            print(
                "Sessions:",
                len(
                    sessions
                ),
            )

            # =================================================
            # SESSION LOOP
            # =================================================

            for session_index, session in enumerate(
                sessions,
                start=1,
            ):

                if not isinstance(
                    session,
                    dict,
                ):
                    continue

                session_id = text_value(
                    first_present(
                        session,
                        [
                            "EventsSessionID",
                            "EventsSessionId",
                            "eventsSessionID",
                            "eventsSessionId",
                            "SessionID",
                            "SessionId",
                            "sessionID",
                            "sessionId",
                            "ID",
                            "Id",
                            "id",
                        ],
                    )
                )

                session_name = text_value(
                    first_present(
                        session,
                        [
                            "SessionName",
                            "sessionName",
                            "Name",
                            "name",
                        ],
                    )
                )

                session_date_raw = text_value(
                    first_present(
                        session,
                        [
                            "SessionDate",
                            "SessionDateFormatted",
                            "sessionDate",
                            "Date",
                            "date",
                        ],
                    )
                )

                session_date_normalized = (
                    normalize_date_text(
                        session_date_raw
                    )
                )

                name_candidate = (
                    is_day1_qualifying_name(
                        session_name
                    )
                )

                date_candidate = (
                    target_date
                    in session_date_normalized
                    if session_date_normalized
                    else False
                )

                qualifying_candidate = (
                    "qual"
                    in session_name.lower()
                )

                session_rows.append(
                    {
                        "year":
                            year,

                        "target_date":
                            target_date,

                        "event_id":
                            event_id,

                        "event_name":
                            event_name,

                        "session_index":
                            session_index,

                        "events_session_id":
                            session_id,

                        "session_name":
                            session_name,

                        "session_date_raw":
                            session_date_raw,

                        "session_date_normalized":
                            session_date_normalized,

                        "name_matches_day1_qualifying":
                            name_candidate,

                        "date_matches_target":
                            date_candidate,

                        "qualifying_name_candidate":
                            qualifying_candidate,
                    }
                )

                print(
                    f"  SESSION {session_index:02d} | "
                    f"{session_id} | "
                    f"{session_name} | "
                    f"{session_date_raw}"
                )

                # ---------------------------------------------
                # Query plausible qualifying sessions.
                #
                # We intentionally do not require exact Day-1
                # naming because historical naming may vary.
                # ---------------------------------------------

                if not (
                    qualifying_candidate
                    or
                    name_candidate
                    or
                    date_candidate
                ):

                    continue

                if not session_id:

                    continue

                detail_query = urlencode(
                    {
                        "id":
                            session_id,
                    }
                )

                detail_url = (
                    SESSION_DETAILS_ENDPOINT
                    + "?"
                    + detail_query
                )

                time.sleep(
                    REQUEST_DELAY_SECONDS
                )

                detail_result = fetch_url(
                    detail_url
                )

                fetch_rows.append(
                    {
                        "year":
                            year,

                        "request_type":
                            "EVENTS_SESSION_DETAILS",

                        "request_url":
                            detail_url,

                        "ok":
                            detail_result[
                                "ok"
                            ],

                        "status_code":
                            detail_result[
                                "status_code"
                            ],

                        "content_type":
                            detail_result[
                                "content_type"
                            ],

                        "bytes":
                            len(
                                detail_result[
                                    "body"
                                ]
                            ),

                        "sha256":
                            (
                                sha256_bytes(
                                    detail_result[
                                        "body"
                                    ]
                                )
                                if detail_result[
                                    "body"
                                ]
                                else ""
                            ),

                        "error":
                            detail_result[
                                "error"
                            ],
                    }
                )

                if not detail_result[
                    "ok"
                ]:

                    print(
                        "      DETAIL FAILED:",
                        detail_result[
                            "error"
                        ],
                    )

                    continue

                detail_data = parse_json(
                    detail_result[
                        "body"
                    ],
                    detail_url,
                )

                detail_raw_path = (
                    RAW_API_DIR
                    /
                    f"{year}_{session_id}_session_details.json"
                )

                json_safe_write(
                    detail_raw_path,
                    detail_data,
                )

                if not isinstance(
                    detail_data,
                    dict,
                ):

                    continue

                detail_name = text_value(
                    first_present(
                        detail_data,
                        [
                            "SessionName",
                            "sessionName",
                        ],
                    )
                )

                detail_date = text_value(
                    first_present(
                        detail_data,
                        [
                            "SessionDate",
                            "SessionDateFormatted",
                            "sessionDate",
                            "Date",
                        ],
                    )
                )

                detail_type = text_value(
                    first_present(
                        detail_data,
                        [
                            "SessionType",
                            "sessionType",
                        ],
                    )
                )

                detail_event = text_value(
                    first_present(
                        detail_data,
                        [
                            "EventName",
                            "eventName",
                        ],
                    )
                )

                detail_date_norm = (
                    normalize_date_text(
                        detail_date
                    )
                )

                detail_day1_name = (
                    is_day1_qualifying_name(
                        detail_name
                    )
                )

                detail_date_match = (
                    target_date
                    in detail_date_norm
                    if detail_date_norm
                    else False
                )

                # SessionType == Q is strong official semantic.
                detail_qual_type = (
                    detail_type.upper()
                    == "Q"
                )

                # Candidate if official detail says Q and either
                # the name/day or date points to target session.
                final_day1_candidate = (
                    detail_qual_type
                    and
                    (
                        detail_day1_name
                        or
                        detail_date_match
                        or
                        name_candidate
                    )
                )

                records = first_present(
                    detail_data,
                    [
                        "records",
                        "Records",
                    ],
                )

                if not isinstance(
                    records,
                    list,
                ):

                    records = []

                session_reports = first_present(
                    detail_data,
                    [
                        "SessionReports",
                        "sessionReports",
                    ],
                )

                if not isinstance(
                    session_reports,
                    list,
                ):

                    session_reports = []

                day1_rows.append(
                    {
                        "year":
                            year,

                        "target_date":
                            target_date,

                        "event_id":
                            event_id,

                        "event_name":
                            detail_event
                            or event_name,

                        "events_session_id":
                            session_id,

                        "session_name":
                            detail_name
                            or session_name,

                        "session_type":
                            detail_type,

                        "session_date":
                            detail_date,

                        "record_count":
                            len(
                                records
                            ),

                        "session_report_count":
                            len(
                                session_reports
                            ),

                        "is_target_day1_candidate":
                            final_day1_candidate,

                        "raw_api_path":
                            str(
                                detail_raw_path
                            ),
                    }
                )

                print(
                    "      DETAIL:",
                    detail_type,
                    "|",
                    detail_name,
                    "|",
                    detail_date,
                    "| records=",
                    len(
                        records
                    ),
                    "| reports=",
                    len(
                        session_reports
                    ),
                    "| TARGET=",
                    final_day1_candidate,
                )

                # ---------------------------------------------
                # Preserve report metadata.
                #
                # Download reports only for target Day-1
                # qualifying candidates.
                # ---------------------------------------------

                for report_index, report in enumerate(
                    session_reports,
                    start=1,
                ):

                    if not isinstance(
                        report,
                        dict,
                    ):
                        continue

                    document_type = text_value(
                        first_present(
                            report,
                            [
                                "DocumentType",
                                "documentType",
                                "Type",
                                "type",
                            ],
                        )
                    )

                    raw_report_url = text_value(
                        first_present(
                            report,
                            [
                                "Url",
                                "URL",
                                "url",
                                "DocumentUrl",
                                "DocumentURL",
                            ],
                        )
                    )

                    full_report_url = (
                        report_url_from_item(
                            report
                        )
                    )

                    report_downloaded = False
                    report_local_path = ""
                    report_status_code = ""
                    report_content_type = ""
                    report_bytes = ""
                    report_sha256 = ""
                    report_error = ""

                    if (
                        final_day1_candidate
                        and
                        full_report_url
                    ):

                        time.sleep(
                            REQUEST_DELAY_SECONDS
                        )

                        report_result = fetch_url(
                            full_report_url
                        )

                        report_status_code = (
                            report_result[
                                "status_code"
                            ]
                        )

                        report_content_type = (
                            report_result[
                                "content_type"
                            ]
                        )

                        report_bytes = len(
                            report_result[
                                "body"
                            ]
                        )

                        report_error = (
                            report_result[
                                "error"
                            ]
                        )

                        if report_result[
                            "body"
                        ]:

                            report_sha256 = (
                                sha256_bytes(
                                    report_result[
                                        "body"
                                    ]
                                )
                            )

                        fetch_rows.append(
                            {
                                "year":
                                    year,

                                "request_type":
                                    "SESSION_REPORT",

                                "request_url":
                                    full_report_url,

                                "ok":
                                    report_result[
                                        "ok"
                                    ],

                                "status_code":
                                    report_status_code,

                                "content_type":
                                    report_content_type,

                                "bytes":
                                    report_bytes,

                                "sha256":
                                    report_sha256,

                                "error":
                                    report_error,
                            }
                        )

                        if report_result[
                            "ok"
                        ]:

                            filename = safe_filename(
                                year=year,
                                session_id=session_id,
                                report_index=report_index,
                                report_type=document_type,
                                url=report_result[
                                    "final_url"
                                ],
                                content_type=report_content_type,
                            )

                            destination = (
                                REPORT_DIR
                                / filename
                            )

                            destination.write_bytes(
                                report_result[
                                    "body"
                                ]
                            )

                            report_downloaded = True

                            report_local_path = str(
                                destination
                            )

                    report_rows.append(
                        {
                            "year":
                                year,

                            "target_date":
                                target_date,

                            "event_id":
                                event_id,

                            "events_session_id":
                                session_id,

                            "session_name":
                                detail_name
                                or session_name,

                            "is_target_day1_candidate":
                                final_day1_candidate,

                            "report_index":
                                report_index,

                            "document_type":
                                document_type,

                            "raw_report_url":
                                raw_report_url,

                            "full_report_url":
                                full_report_url,

                            "downloaded":
                                report_downloaded,

                            "status_code":
                                report_status_code,

                            "content_type":
                                report_content_type,

                            "bytes":
                                report_bytes,

                            "sha256":
                                report_sha256,

                            "local_path":
                                report_local_path,

                            "error":
                                report_error,
                        }
                    )

    # ========================================================
    # WRITE CSVs
    # ========================================================

    def write_csv(
        path,
        rows,
        fields,
    ):

        with path.open(
            "w",
            newline="",
            encoding="utf-8-sig",
        ) as handle:

            writer = csv.DictWriter(
                handle,
                fieldnames=fields,
            )

            writer.writeheader()

            writer.writerows(
                rows
            )

    write_csv(
        EVENT_INVENTORY_FILE,
        event_rows,
        [
            "year",
            "event_index",
            "event_id",
            "event_name",
            "session_count",
            "is_indianapolis_500",
            "raw_api_path",
        ],
    )

    write_csv(
        SESSION_INVENTORY_FILE,
        session_rows,
        [
            "year",
            "target_date",
            "event_id",
            "event_name",
            "session_index",
            "events_session_id",
            "session_name",
            "session_date_raw",
            "session_date_normalized",
            "name_matches_day1_qualifying",
            "date_matches_target",
            "qualifying_name_candidate",
        ],
    )

    write_csv(
        DAY1_SESSION_FILE,
        day1_rows,
        [
            "year",
            "target_date",
            "event_id",
            "event_name",
            "events_session_id",
            "session_name",
            "session_type",
            "session_date",
            "record_count",
            "session_report_count",
            "is_target_day1_candidate",
            "raw_api_path",
        ],
    )

    write_csv(
        REPORT_INVENTORY_FILE,
        report_rows,
        [
            "year",
            "target_date",
            "event_id",
            "events_session_id",
            "session_name",
            "is_target_day1_candidate",
            "report_index",
            "document_type",
            "raw_report_url",
            "full_report_url",
            "downloaded",
            "status_code",
            "content_type",
            "bytes",
            "sha256",
            "local_path",
            "error",
        ],
    )

    write_csv(
        FETCH_AUDIT_FILE,
        fetch_rows,
        [
            "year",
            "request_type",
            "request_url",
            "ok",
            "status_code",
            "content_type",
            "bytes",
            "sha256",
            "error",
        ],
    )

    # ========================================================
    # QA
    # ========================================================

    indy_event_years = sorted(
        {
            row[
                "year"
            ]
            for row in event_rows
            if row[
                "is_indianapolis_500"
            ]
        }
    )

    target_day1_rows = [
        row
        for row in day1_rows
        if row[
            "is_target_day1_candidate"
        ]
    ]

    target_day1_years = sorted(
        {
            row[
                "year"
            ]
            for row in target_day1_rows
        }
    )

    target_with_reports = [
        row
        for row in target_day1_rows
        if int(
            row[
                "session_report_count"
            ]
        )
        > 0
    ]

    downloaded_reports = [
        row
        for row in report_rows
        if row[
            "downloaded"
        ]
    ]

    successful_event_api = sum(
        1
        for row in fetch_rows
        if (
            row[
                "request_type"
            ]
            == "EVENTS_BY_YEAR_SERIES"
            and
            row[
                "ok"
            ]
        )
    )

    successful_session_api = sum(
        1
        for row in fetch_rows
        if (
            row[
                "request_type"
            ]
            == "EVENTS_SESSION_DETAILS"
            and
            row[
                "ok"
            ]
        )
    )

    policy_payload = {
        "phase":
            PHASE,

        "policy_version":
            POLICY_VERSION,

        "series_id":
            SERIES_ID,

        "target_dates":
            TARGET_DATES,

        "events_endpoint":
            EVENTS_BY_YEAR_ENDPOINT,

        "session_details_endpoint":
            SESSION_DETAILS_ENDPOINT,

        "canonical_mutation":
            False,

        "queue_inference":
            False,

        "leaderboard_reconstruction":
            False,
    }

    policy_hash = hashlib.sha256(
        json.dumps(
            policy_payload,
            sort_keys=True,
            separators=(",", ":"),
        ).encode(
            "utf-8"
        )
    ).hexdigest()

    qa_rows = [
        {
            "metric":
                "target_years_expected",

            "value":
                5,

            "status":
                "INFO",
        },

        {
            "metric":
                "successful_events_api_years",

            "value":
                successful_event_api,

            "status":
                (
                    "PASS"
                    if successful_event_api
                    == 5
                    else "REVIEW"
                ),
        },

        {
            "metric":
                "indy500_event_years",

            "value":
                ",".join(
                    str(
                        year
                    )
                    for year in indy_event_years
                ),

            "status":
                (
                    "PASS"
                    if set(
                        indy_event_years
                    )
                    == set(
                        TARGET_DATES.keys()
                    )
                    else "REVIEW"
                ),
        },

        {
            "metric":
                "session_inventory_rows",

            "value":
                len(
                    session_rows
                ),

            "status":
                "INFO",
        },

        {
            "metric":
                "successful_session_detail_calls",

            "value":
                successful_session_api,

            "status":
                (
                    "PASS"
                    if successful_session_api
                    > 0
                    else "REVIEW"
                ),
        },

        {
            "metric":
                "target_day1_candidate_rows",

            "value":
                len(
                    target_day1_rows
                ),

            "status":
                (
                    "PASS"
                    if len(
                        target_day1_rows
                    )
                    > 0
                    else "REVIEW"
                ),
        },

        {
            "metric":
                "target_day1_years",

            "value":
                ",".join(
                    str(
                        year
                    )
                    for year in target_day1_years
                ),

            "status":
                (
                    "PASS"
                    if len(
                        target_day1_years
                    )
                    >= 3
                    else "REVIEW"
                ),
        },

        {
            "metric":
                "target_sessions_with_reports",

            "value":
                len(
                    target_with_reports
                ),

            "status":
                "INFO",
        },

        {
            "metric":
                "report_inventory_rows",

            "value":
                len(
                    report_rows
                ),

            "status":
                "INFO",
        },

        {
            "metric":
                "downloaded_report_files",

            "value":
                len(
                    downloaded_reports
                ),

            "status":
                "INFO",
        },

        {
            "metric":
                "canonical_data_mutated",

            "value":
                0,

            "status":
                "PASS",
        },

        {
            "metric":
                "queue_wait_inferred",

            "value":
                0,

            "status":
                "PASS",
        },

        {
            "metric":
                "leaderboard_state_invented",

            "value":
                0,

            "status":
                "PASS",
        },

        {
            "metric":
                "policy_hash",

            "value":
                policy_hash,

            "status":
                "INFO",
        },
    ]

    write_csv(
        QA_FILE,
        qa_rows,
        [
            "metric",
            "value",
            "status",
        ],
    )

    # ========================================================
    # PRINT
    # ========================================================

    print()
    print("=" * 100)
    print(
        "OFFICIAL SESSION RECOVERY SUMMARY"
    )
    print("=" * 100)

    print()
    print(
        "Years with official Indy 500 event:",
        indy_event_years,
    )

    print(
        "Target Day-1 candidate years:",
        target_day1_years,
    )

    print(
        "Target Day-1 session rows:",
        len(
            target_day1_rows
        ),
    )

    print(
        "Target sessions with SessionReports:",
        len(
            target_with_reports
        ),
    )

    print(
        "Downloaded report files:",
        len(
            downloaded_reports
        ),
    )

    print()
    print(
        "TARGET DAY-1 SESSION CANDIDATES"
    )
    print("-" * 150)

    for row in target_day1_rows:

        print(
            f"{row['year']} | "
            f"{row['events_session_id']} | "
            f"type={row['session_type']} | "
            f"{row['session_name']} | "
            f"{row['session_date']} | "
            f"records={row['record_count']} | "
            f"reports={row['session_report_count']}"
        )

    print()
    print(
        "OFFICIAL SESSION REPORTS"
    )
    print("-" * 170)

    target_report_rows = [
        row
        for row in report_rows
        if row[
            "is_target_day1_candidate"
        ]
    ]

    if not target_report_rows:

        print(
            "NO TARGET DAY-1 SESSION REPORTS "
            "RETURNED BY THE API."
        )

    else:

        for row in target_report_rows:

            print(
                f"{row['year']} | "
                f"{row['document_type']:<28} | "
                f"downloaded={row['downloaded']} | "
                f"{row['full_report_url']}"
            )

            if row[
                "local_path"
            ]:

                print(
                    "    local:",
                    row[
                        "local_path"
                    ],
                )

    print()
    print(
        "QA"
    )
    print("-" * 120)

    for row in qa_rows:

        print(
            f"{row['metric']}: "
            f"{row['value']} "
            f"[{row['status']}]"
        )

    # ========================================================
    # REPORT
    # ========================================================

    report = []

    report.append(
        "# Phase R1E — Official Indy 500 "
        "Day 1 Session / Report Recovery"
    )

    report.append("")

    report.append(
        f"Policy hash: `{policy_hash}`"
    )

    report.append("")

    report.append(
        "## Recovered API chain"
    )

    report.append("")

    report.append(
        "`EventsByYearSeries(year, series_id)` "
        "→ Indy 500 event "
        "→ Sessions / EventsSessionID "
        "→ `EventsSessionDetails(id)` "
        "→ SessionReports."
    )

    report.append("")

    report.append(
        f"- Years with Indy 500 event: "
        f"`{indy_event_years}`"
    )

    report.append(
        f"- Target Day-1 candidate years: "
        f"`{target_day1_years}`"
    )

    report.append(
        f"- Target Day-1 session rows: "
        f"`{len(target_day1_rows)}`"
    )

    report.append(
        f"- Target sessions with reports: "
        f"`{len(target_with_reports)}`"
    )

    report.append(
        f"- Downloaded official report files: "
        f"`{len(downloaded_reports)}`"
    )

    report.append("")

    report.append(
        "No queue wait was inferred."
    )

    report.append(
        "No historical leaderboard state was reconstructed."
    )

    report.append(
        "No canonical data was modified."
    )

    REPORT_FILE.write_text(
        "\n".join(
            report
        ),
        encoding="utf-8",
    )

    # ========================================================
    # FINAL STATUS
    # ========================================================

    print()
    print("=" * 100)

    if (
        successful_event_api
        == 5
        and
        len(
            target_day1_rows
        )
        > 0
    ):

        print(
            "FINAL STATUS: "
            "OFFICIAL_INDY500_DAY1_SESSION_CHAIN_RECOVERED"
        )

    else:

        print(
            "FINAL STATUS: "
            "OFFICIAL_INDY500_DAY1_SESSION_CHAIN_REVIEW_REQUIRED"
        )

    print("=" * 100)

    print()
    print(
        "NO CANONICAL DATA WAS MODIFIED."
    )

    print(
        "NO QUEUE WAIT WAS INFERRED."
    )

    print(
        "NO LEADERBOARD STATE WAS INVENTED."
    )

    print()
    print(
        "OUTPUTS"
    )

    print(
        EVENT_INVENTORY_FILE
    )

    print(
        SESSION_INVENTORY_FILE
    )

    print(
        DAY1_SESSION_FILE
    )

    print(
        REPORT_INVENTORY_FILE
    )

    print(
        FETCH_AUDIT_FILE
    )

    print(
        QA_FILE
    )

    print(
        REPORT_FILE
    )

    print(
        EVIDENCE_DIR
    )


if __name__ == "__main__":
    main()
