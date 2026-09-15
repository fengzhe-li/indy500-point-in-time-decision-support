from pathlib import Path
from urllib.parse import urlencode, urljoin, urlparse
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

PHASE = "R1E.5"
POLICY_VERSION = (
    "OFFICIAL_DAY1_SESSION_DETAILS_AND_REPORTS_V1"
)


# ============================================================
# OFFICIAL API
# ============================================================

BASE_URL = "https://www.indycar.com"

SESSION_DETAILS_ENDPOINT = (
    BASE_URL
    + "/api/results/EventsSessionDetails"
)


# ============================================================
# TARGET SESSIONS
# ============================================================

TARGETS = {
    2020: {
        "event_id": 5286,
        "event_name": (
            "104th Running of the Indianapolis 500"
        ),
        "session_id": "5771",
        "session_name_expected": (
            "Qualifications (Day 1)"
        ),
    },

    2021: {
        "event_id": 5365,
        "event_name": (
            "105th Running of the Indianapolis 500"
        ),
        "session_id": "5838",
        "session_name_expected": (
            "Qualifications - Day 1"
        ),
    },

    2022: {
        "event_id": 5374,
        "event_name": (
            "106th Running of the Indianapolis 500"
        ),
        "session_id": "6033",
        "session_name_expected": (
            "Qualifications - Day 1"
        ),
    },

    2023: {
        "event_id": 5431,
        "event_name": (
            "107th Running of the Indianapolis 500"
        ),
        "session_id": "6202",
        "session_name_expected": (
            "Qualifications - Day 1"
        ),
    },

    2024: {
        "event_id": 5465,
        "event_name": (
            "108th Running of the Indianapolis 500"
        ),
        "session_id": "6382",
        "session_name_expected": (
            "Qualifications - Day 1"
        ),
    },
}


# ============================================================
# OUTPUT PATHS
# ============================================================

OUTPUT_DIR = Path(
    "weather/output"
)

EVIDENCE_DIR = Path(
    "weather/evidence/rescue/"
    "official_day1_session_details"
)

RAW_JSON_DIR = (
    EVIDENCE_DIR
    / "raw_api"
)

REPORT_DIR = (
    EVIDENCE_DIR
    / "reports"
)

SESSION_AUDIT_FILE = (
    OUTPUT_DIR
    / "official_day1_session_detail_audit_v1.csv"
)

FIELD_INVENTORY_FILE = (
    OUTPUT_DIR
    / "official_day1_session_field_inventory_v1.csv"
)

REPORT_INVENTORY_FILE = (
    OUTPUT_DIR
    / "official_day1_session_report_inventory_v1.csv"
)

FETCH_AUDIT_FILE = (
    OUTPUT_DIR
    / "official_day1_session_report_fetch_audit_v1.csv"
)

QA_FILE = (
    OUTPUT_DIR
    / "official_day1_session_details_and_reports_v1_qa.csv"
)

REPORT_FILE = (
    OUTPUT_DIR
    / "official_day1_session_details_and_reports_v1.md"
)


# ============================================================
# NETWORK
# ============================================================

USER_AGENT = (
    "Mozilla/5.0 "
    "(compatible; Indy500HistoricalEvidenceResearch/1.0)"
)

TIMEOUT = 30
DELAY = 0.8


# ============================================================
# HELPERS
# ============================================================

def fetch(url):

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
                    "text/html,"
                    "*/*;q=0.8"
                ),
        },
    )

    started = time.time()

    try:

        with urlopen(
            request,
            timeout=TIMEOUT,
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


def decode(body):

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


def sha256_bytes(body):

    return hashlib.sha256(
        body
    ).hexdigest()


def first_value(
    obj,
    keys,
):

    if not isinstance(
        obj,
        dict,
    ):

        return None

    for key in keys:

        if key in obj:

            value = obj[
                key
            ]

            if value is not None:

                return value

    return None


def safe_text(value):

    if value is None:
        return ""

    return str(
        value
    ).strip()


def safe_json_preview(
    value,
    limit=1200,
):

    try:

        text = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
        )

    except Exception:

        text = repr(
            value
        )

    return text[:limit]


def report_full_url(
    report,
):

    raw = safe_text(
        first_value(
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

    if not raw:
        return ""

    # Already absolute.
    if raw.startswith(
        (
            "https://",
            "http://",
        )
    ):

        return raw

    # Official frontend uses imscdn.com + t.Url
    return urljoin(
        "https://www.imscdn.com/",
        raw.lstrip(
            "/"
        ),
    )


def sanitize_filename(
    value,
):

    value = re.sub(
        r"[^A-Za-z0-9._-]+",
        "_",
        safe_text(
            value
        ),
    )

    return (
        value.strip(
            "._"
        )
        or "UNKNOWN"
    )


def choose_extension(
    url,
    content_type,
):

    path_suffix = Path(
        urlparse(
            url
        ).path
    ).suffix

    if path_suffix:

        return path_suffix

    lower_ct = safe_text(
        content_type
    ).lower()

    if "pdf" in lower_ct:
        return ".pdf"

    if "json" in lower_ct:
        return ".json"

    if "html" in lower_ct:
        return ".html"

    if "text" in lower_ct:
        return ".txt"

    return ".bin"


def normalize_reports(
    detail,
):

    reports = first_value(
        detail,
        [
            "SessionReports",
            "sessionReports",
            "Reports",
            "reports",
        ],
    )

    if isinstance(
        reports,
        list,
    ):

        return reports

    return []


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


# ============================================================
# MAIN
# ============================================================

def main():

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    RAW_JSON_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    REPORT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print()
    print("=" * 110)
    print(
        "R1E.5 — OFFICIAL DAY 1 SESSION "
        "DETAILS + SESSIONREPORTS RECOVERY V1"
    )
    print("=" * 110)

    session_rows = []
    field_rows = []
    report_rows = []
    fetch_rows = []

    successful_session_calls = 0
    years_with_reports = []
    downloaded_report_count = 0

    # ========================================================
    # LOOP
    # ========================================================

    for year, target in (
        TARGETS.items()
    ):

        session_id = target[
            "session_id"
        ]

        query = urlencode(
            {
                "id":
                    session_id,
            }
        )

        url = (
            SESSION_DETAILS_ENDPOINT
            + "?"
            + query
        )

        print()
        print("=" * 110)
        print(
            f"YEAR {year}"
        )
        print("=" * 110)

        print(
            "SESSION ID:",
            session_id,
        )

        print(
            "REQUEST:",
            url,
        )

        result = fetch(
            url
        )

        fetch_rows.append(
            {
                "year":
                    year,

                "request_type":
                    "SESSION_DETAIL",

                "request_url":
                    url,

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

        print(
            "STATUS:",
            result[
                "status_code"
            ],
        )

        print(
            "CONTENT-TYPE:",
            result[
                "content_type"
            ],
        )

        if not result[
            "ok"
        ]:

            print(
                "ERROR:",
                result[
                    "error"
                ],
            )

            continue

        successful_session_calls += 1

        text = decode(
            result[
                "body"
            ]
        )

        try:

            detail = json.loads(
                text
            )

        except Exception as exc:

            print(
                "JSON PARSE ERROR:",
                exc,
            )

            print(
                "RAW PREVIEW:",
                text[:5000],
            )

            continue

        raw_path = (
            RAW_JSON_DIR
            /
            f"{year}_{session_id}_session_details.json"
        )

        raw_path.write_text(
            json.dumps(
                detail,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )

        if not isinstance(
            detail,
            dict,
        ):

            print(
                "DETAIL IS NOT AN OBJECT:"
            )

            print(
                repr(
                    detail
                )[:5000]
            )

            continue

        print()
        print(
            "TOP-LEVEL KEYS:"
        )

        for key in detail.keys():

            print(
                "  -",
                key,
            )

        event_name = safe_text(
            first_value(
                detail,
                [
                    "EventName",
                    "eventName",
                ],
            )
        )

        session_name = safe_text(
            first_value(
                detail,
                [
                    "SessionName",
                    "sessionName",
                ],
            )
        )

        session_type = safe_text(
            first_value(
                detail,
                [
                    "SessionType",
                    "sessionType",
                ],
            )
        )

        session_date = safe_text(
            first_value(
                detail,
                [
                    "SessionDateFormatted",
                    "SessionDate",
                    "sessionDateFormatted",
                    "sessionDate",
                    "Date",
                ],
            )
        )

        records = first_value(
            detail,
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

        reports = normalize_reports(
            detail
        )

        if reports:

            years_with_reports.append(
                year
            )

        print()
        print(
            "SESSION SUMMARY"
        )
        print("-" * 110)

        print(
            "EventName:",
            event_name,
        )

        print(
            "SessionName:",
            session_name,
        )

        print(
            "SessionType:",
            session_type,
        )

        print(
            "SessionDate:",
            session_date,
        )

        print(
            "Record count:",
            len(
                records
            ),
        )

        print(
            "SessionReports count:",
            len(
                reports
            ),
        )

        session_rows.append(
            {
                "year":
                    year,

                "event_id_expected":
                    target[
                        "event_id"
                    ],

                "event_name_expected":
                    target[
                        "event_name"
                    ],

                "session_id":
                    session_id,

                "session_name_expected":
                    target[
                        "session_name_expected"
                    ],

                "event_name_returned":
                    event_name,

                "session_name_returned":
                    session_name,

                "session_type":
                    session_type,

                "session_date":
                    session_date,

                "record_count":
                    len(
                        records
                    ),

                "session_report_count":
                    len(
                        reports
                    ),

                "raw_json_path":
                    str(
                        raw_path
                    ),

                "session_call_ok":
                    True,
            }
        )

        # ====================================================
        # FIELD INVENTORY
        # ====================================================

        for key, value in (
            detail.items()
        ):

            if value is None:

                value_type = "null"
                count = ""

            elif isinstance(
                value,
                list,
            ):

                value_type = "list"
                count = len(
                    value
                )

            elif isinstance(
                value,
                dict,
            ):

                value_type = "dict"
                count = len(
                    value
                )

            else:

                value_type = type(
                    value
                ).__name__
                count = ""

            field_rows.append(
                {
                    "year":
                        year,

                    "session_id":
                        session_id,

                    "field_name":
                        key,

                    "value_type":
                        value_type,

                    "item_count":
                        count,

                    "value_preview":
                        safe_json_preview(
                            value
                        ),
                }
            )

        # ====================================================
        # REPORT INVENTORY
        # ====================================================

        print()
        print(
            "SESSION REPORTS"
        )
        print("-" * 140)

        if not reports:

            print(
                "NONE"
            )

        for report_index, report in enumerate(
            reports,
            start=1,
        ):

            if not isinstance(
                report,
                dict,
            ):

                print(
                    f"{report_index:02d} | "
                    f"NON-DICT | "
                    f"{repr(report)[:1000]}"
                )

                continue

            document_type = safe_text(
                first_value(
                    report,
                    [
                        "DocumentType",
                        "documentType",
                        "Type",
                        "type",
                    ],
                )
            )

            raw_url = safe_text(
                first_value(
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

            full_url = report_full_url(
                report
            )

            print()
            print(
                f"{report_index:02d} | "
                f"DocumentType={document_type!r}"
            )

            print(
                "     RAW URL:",
                raw_url,
            )

            print(
                "     FULL URL:",
                full_url,
            )

            print(
                "     RAW REPORT OBJECT:",
                json.dumps(
                    report,
                    ensure_ascii=False,
                    sort_keys=True,
                )[:3000],
            )

            downloaded = False
            local_path = ""
            status_code = ""
            content_type = ""
            byte_count = ""
            sha256 = ""
            error = ""

            if full_url:

                time.sleep(
                    DELAY
                )

                report_result = fetch(
                    full_url
                )

                status_code = (
                    report_result[
                        "status_code"
                    ]
                )

                content_type = (
                    report_result[
                        "content_type"
                    ]
                )

                byte_count = len(
                    report_result[
                        "body"
                    ]
                )

                error = (
                    report_result[
                        "error"
                    ]
                )

                if report_result[
                    "body"
                ]:

                    sha256 = sha256_bytes(
                        report_result[
                            "body"
                        ]
                    )

                fetch_rows.append(
                    {
                        "year":
                            year,

                        "request_type":
                            "SESSION_REPORT",

                        "request_url":
                            full_url,

                        "ok":
                            report_result[
                                "ok"
                            ],

                        "status_code":
                            status_code,

                        "content_type":
                            content_type,

                        "bytes":
                            byte_count,

                        "sha256":
                            sha256,

                        "error":
                            error,
                    }
                )

                if report_result[
                    "ok"
                ]:

                    extension = choose_extension(
                        report_result[
                            "final_url"
                        ],
                        content_type,
                    )

                    filename = (
                        f"{year}_"
                        f"{session_id}_"
                        f"{report_index:02d}_"
                        f"{sanitize_filename(document_type)}"
                        f"{extension}"
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

                    downloaded = True
                    local_path = str(
                        destination
                    )

                    downloaded_report_count += 1

                    print(
                        "     DOWNLOAD: PASS"
                    )

                    print(
                        "     CONTENT-TYPE:",
                        content_type,
                    )

                    print(
                        "     BYTES:",
                        byte_count,
                    )

                    print(
                        "     LOCAL:",
                        local_path,
                    )

                else:

                    print(
                        "     DOWNLOAD: FAIL"
                    )

                    print(
                        "     ERROR:",
                        error,
                    )

            report_rows.append(
                {
                    "year":
                        year,

                    "event_id":
                        target[
                            "event_id"
                        ],

                    "session_id":
                        session_id,

                    "session_name":
                        session_name,

                    "report_index":
                        report_index,

                    "document_type":
                        document_type,

                    "raw_url":
                        raw_url,

                    "full_url":
                        full_url,

                    "downloaded":
                        downloaded,

                    "status_code":
                        status_code,

                    "content_type":
                        content_type,

                    "bytes":
                        byte_count,

                    "sha256":
                        sha256,

                    "local_path":
                        local_path,

                    "raw_report_object":
                        json.dumps(
                            report,
                            ensure_ascii=False,
                            sort_keys=True,
                        ),

                    "error":
                        error,
                }
            )

        time.sleep(
            DELAY
        )

    # ========================================================
    # WRITE OUTPUTS
    # ========================================================

    write_csv(
        SESSION_AUDIT_FILE,
        session_rows,
        [
            "year",
            "event_id_expected",
            "event_name_expected",
            "session_id",
            "session_name_expected",
            "event_name_returned",
            "session_name_returned",
            "session_type",
            "session_date",
            "record_count",
            "session_report_count",
            "raw_json_path",
            "session_call_ok",
        ],
    )

    write_csv(
        FIELD_INVENTORY_FILE,
        field_rows,
        [
            "year",
            "session_id",
            "field_name",
            "value_type",
            "item_count",
            "value_preview",
        ],
    )

    write_csv(
        REPORT_INVENTORY_FILE,
        report_rows,
        [
            "year",
            "event_id",
            "session_id",
            "session_name",
            "report_index",
            "document_type",
            "raw_url",
            "full_url",
            "downloaded",
            "status_code",
            "content_type",
            "bytes",
            "sha256",
            "local_path",
            "raw_report_object",
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

    unique_years_with_reports = sorted(
        set(
            years_with_reports
        )
    )

    session_names_ok = sum(
        1
        for row in session_rows
        if (
            "qual"
            in row[
                "session_name_returned"
            ].lower()
            and
            "day 1"
            in row[
                "session_name_returned"
            ].lower()
        )
    )

    session_type_q_count = sum(
        1
        for row in session_rows
        if row[
            "session_type"
        ].upper()
        == "Q"
    )

    policy_payload = {
        "phase":
            PHASE,

        "policy_version":
            POLICY_VERSION,

        "targets":
            TARGETS,

        "endpoint":
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
                "target_sessions_expected",

            "value":
                5,

            "status":
                "INFO",
        },

        {
            "metric":
                "successful_session_detail_calls",

            "value":
                successful_session_calls,

            "status":
                (
                    "PASS"
                    if successful_session_calls
                    == 5
                    else "FAIL"
                ),
        },

        {
            "metric":
                "day1_session_names_confirmed",

            "value":
                session_names_ok,

            "status":
                (
                    "PASS"
                    if session_names_ok
                    == 5
                    else "REVIEW"
                ),
        },

        {
            "metric":
                "session_type_q_count",

            "value":
                session_type_q_count,

            "status":
                (
                    "PASS"
                    if session_type_q_count
                    == 5
                    else "REVIEW"
                ),
        },

        {
            "metric":
                "years_with_session_reports",

            "value":
                ",".join(
                    str(
                        year
                    )
                    for year in unique_years_with_reports
                ),

            "status":
                (
                    "PASS"
                    if len(
                        unique_years_with_reports
                    )
                    > 0
                    else "REVIEW"
                ),
        },

        {
            "metric":
                "session_report_inventory_rows",

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
                downloaded_report_count,

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
    # REPORT
    # ========================================================

    md = []

    md.append(
        "# R1E.5 — Official Day 1 Session Details "
        "and SessionReports Recovery"
    )

    md.append("")

    md.append(
        f"Policy hash: `{policy_hash}`"
    )

    md.append("")

    md.append(
        "## Summary"
    )

    md.append("")

    md.append(
        f"- Successful Day 1 session detail calls: "
        f"`{successful_session_calls}/5`"
    )

    md.append(
        f"- Years with SessionReports: "
        f"`{unique_years_with_reports}`"
    )

    md.append(
        f"- Report inventory rows: "
        f"`{len(report_rows)}`"
    )

    md.append(
        f"- Downloaded report files: "
        f"`{downloaded_report_count}`"
    )

    md.append("")

    md.append(
        "No canonical data was modified."
    )

    md.append(
        "No queue wait was inferred."
    )

    md.append(
        "No historical leaderboard state was reconstructed."
    )

    REPORT_FILE.write_text(
        "\n".join(
            md
        ),
        encoding="utf-8",
    )

    # ========================================================
    # FINAL PRINT
    # ========================================================

    print()
    print("=" * 110)
    print(
        "R1E.5 SUMMARY"
    )
    print("=" * 110)

    print()
    print(
        "Successful session detail calls:",
        successful_session_calls,
        "/ 5",
    )

    print(
        "Years with SessionReports:",
        unique_years_with_reports,
    )

    print(
        "Report inventory rows:",
        len(
            report_rows
        ),
    )

    print(
        "Downloaded report files:",
        downloaded_report_count,
    )

    print()
    print(
        "REPORT TYPES BY YEAR"
    )
    print("-" * 120)

    for year in TARGETS:

        types = [
            row[
                "document_type"
            ]
            for row in report_rows
            if row[
                "year"
            ]
            == year
        ]

        print(
            year,
            "→",
            types,
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

    print()
    print("=" * 110)

    if (
        successful_session_calls
        == 5
        and
        len(
            report_rows
        )
        > 0
    ):

        print(
            "FINAL STATUS: "
            "OFFICIAL_DAY1_SESSION_REPORTS_RECOVERED"
        )

    elif (
        successful_session_calls
        == 5
    ):

        print(
            "FINAL STATUS: "
            "OFFICIAL_DAY1_SESSION_DETAILS_RECOVERED_NO_REPORTS"
        )

    else:

        print(
            "FINAL STATUS: "
            "OFFICIAL_DAY1_SESSION_DETAILS_REVIEW_REQUIRED"
        )

    print("=" * 110)

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
        SESSION_AUDIT_FILE
    )

    print(
        FIELD_INVENTORY_FILE
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
