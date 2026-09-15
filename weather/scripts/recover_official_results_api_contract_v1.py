from pathlib import Path
from urllib.parse import urlparse
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

PHASE = "R1D"
POLICY_VERSION = "OFFICIAL_RESULTS_API_CONTRACT_RECOVERY_V1"


# ============================================================
# INPUT / OUTPUT
# ============================================================

OUTPUT_DIR = Path("weather/output")
EVIDENCE_DIR = Path(
    "weather/evidence/rescue/official_results_api_contract"
)

BUNDLE_PATH = Path(
    "weather/evidence/rescue/"
    "official_dynamic_resources/2020_002_bundle.js"
)

CONTRACT_FILE = OUTPUT_DIR / (
    "official_results_api_contract_candidates_v1.csv"
)

PAGE_IDENTIFIER_FILE = OUTPUT_DIR / (
    "official_results_page_identifiers_v1.csv"
)

BUNDLE_CONTEXT_FILE = OUTPUT_DIR / (
    "official_results_api_bundle_context_v1.csv"
)

QA_FILE = OUTPUT_DIR / (
    "official_results_api_contract_recovery_v1_qa.csv"
)

REPORT_FILE = OUTPUT_DIR / (
    "official_results_api_contract_recovery_v1.md"
)


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

SEED_URLS = {
    2020: (
        "https://www.indycar.com/results/ntt-indycar-series/"
        "2020/104th-running-of-the-indianapolis-500/"
        "qualifications---day-1"
    ),

    2021: (
        "https://www.indycar.com/results/ntt-indycar-series/"
        "2021/105th-running-of-the-indianapolis-500/"
        "qualifications---day-1"
    ),

    2022: (
        "https://www.indycar.com/results/ntt-indycar-series/"
        "2022/106th-running-of-the-indianapolis-500/"
        "qualifications---day-1"
    ),

    2023: (
        "https://www.indycar.com/results/ntt-indycar-series/"
        "2023/107th-running-of-the-indianapolis-500/"
        "qualifications---day-1"
    ),

    2024: (
        "https://www.indycar.com/results/ntt-indycar-series/"
        "2024/108th-running-of-the-indianapolis-500/"
        "qualifications---day-1"
    ),
}


# ============================================================
# NETWORK
# ============================================================

USER_AGENT = (
    "Mozilla/5.0 "
    "(compatible; Indy500HistoricalEvidenceResearch/1.0)"
)

REQUEST_TIMEOUT_SECONDS = 30
REQUEST_DELAY_SECONDS = 1.0


# ============================================================
# TARGET API / JS TERMS
# ============================================================

API_TERMS = [
    "EventsSessionDetails",
    "EventsByYearSeries",
    "SeasonDropDown",
    "DriversByYear",
    "DriverEventDetails",
    "DriverYearDetails",
    "YearPointSummary",
    "YearsBySeries",
]

JS_TERMS = [
    "UpdateSession",
    "SeasonSessions",
    "EventsSessionID",
    "SessionReports",
    "DriverSessions",
    "SessionId",
    "EventID",
    "data-eventid",
]

IDENTIFIER_PATTERNS = {
    "data-eventid": [
        r'data-eventid\s*=\s*["\']([^"\']+)["\']',
        r'data-event-id\s*=\s*["\']([^"\']+)["\']',
    ],

    "eventid": [
        r'eventid\s*=\s*["\']?([A-Za-z0-9_-]+)',
        r'eventID\s*[:=]\s*["\']?([A-Za-z0-9_-]+)',
        r'EventID\s*[:=]\s*["\']?([A-Za-z0-9_-]+)',
    ],

    "events_session_id": [
        r'EventsSessionID\s*[:=]\s*["\']?([A-Za-z0-9_-]+)',
        r'eventsSessionID\s*[:=]\s*["\']?([A-Za-z0-9_-]+)',
        r'eventsSessionId\s*[:=]\s*["\']?([A-Za-z0-9_-]+)',
    ],

    "session_id": [
        r'SessionId\s*[:=]\s*["\']?([A-Za-z0-9_-]+)',
        r'sessionId\s*[:=]\s*["\']?([A-Za-z0-9_-]+)',
        r'sessionid\s*=\s*["\']?([A-Za-z0-9_-]+)',
    ],
}


# ============================================================
# HELPERS
# ============================================================

def fetch_url(url):

    request = Request(
        url,
        headers={
            "User-Agent":
                USER_AGENT,

            "Accept":
                (
                    "text/html,"
                    "application/xhtml+xml,"
                    "application/json,"
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
                    time.time() - started,

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
                time.time() - started,

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
                time.time() - started,

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
                time.time() - started,

            "error":
                (
                    f"{type(exc).__name__}: "
                    f"{exc}"
                ),
        }


def decode_text(body):

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


def context_windows(
    text,
    term,
    radius=1200,
    max_hits=20,
):

    lower = text.lower()
    target = term.lower()

    rows = []

    start_search = 0

    while True:

        idx = lower.find(
            target,
            start_search,
        )

        if idx < 0:
            break

        start = max(
            0,
            idx - radius,
        )

        end = min(
            len(text),
            idx
            + len(term)
            + radius,
        )

        context = text[
            start:end
        ]

        context = (
            context
            .replace(
                "\r",
                " "
            )
            .replace(
                "\n",
                " "
            )
        )

        rows.append(
            {
                "offset":
                    idx,

                "context":
                    context,
            }
        )

        if len(rows) >= max_hits:
            break

        start_search = (
            idx
            + len(term)
        )

    return rows


def extract_url_like_api_strings(text):

    patterns = [
        r'["\']([^"\']*/api/results/[^"\']+)["\']',
        r'["\']([^"\']*EventsSessionDetails[^"\']*)["\']',
        r'["\']([^"\']*EventsByYearSeries[^"\']*)["\']',
    ]

    values = []

    for pattern in patterns:

        for match in re.findall(
            pattern,
            text,
            flags=re.IGNORECASE,
        ):

            value = str(
                match
            ).strip()

            if value:
                values.append(
                    value
                )

    return sorted(
        set(
            values
        )
    )


def clean_identifier(value):

    if value is None:
        return None

    value = (
        str(value)
        .strip()
        .strip("\"'")
    )

    if not value:
        return None

    if len(value) > 120:
        return None

    return value


# ============================================================
# MAIN
# ============================================================

def main():

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    EVIDENCE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print()
    print("=" * 100)
    print(
        "PHASE R1D — OFFICIAL RESULTS "
        "API CONTRACT RECOVERY V1"
    )
    print("=" * 100)

    # ========================================================
    # BUNDLE
    # ========================================================

    if not BUNDLE_PATH.exists():

        raise FileNotFoundError(
            f"Missing bundle: {BUNDLE_PATH}"
        )

    bundle_bytes = BUNDLE_PATH.read_bytes()

    bundle_text = decode_text(
        bundle_bytes
    )

    print()
    print(
        "Bundle:",
        BUNDLE_PATH,
    )

    print(
        "Bundle bytes:",
        len(
            bundle_bytes
        ),
    )

    print(
        "Bundle SHA-256:",
        hashlib.sha256(
            bundle_bytes
        ).hexdigest(),
    )

    # ========================================================
    # EXACT BUNDLE CONTEXT
    # ========================================================

    bundle_context_rows = []

    for term in (
        API_TERMS
        +
        JS_TERMS
    ):

        windows = context_windows(
            bundle_text,
            term,
        )

        for hit_index, window in enumerate(
            windows,
            start=1,
        ):

            bundle_context_rows.append(
                {
                    "term":
                        term,

                    "hit_index":
                        hit_index,

                    "offset":
                        window[
                            "offset"
                        ],

                    "context":
                        window[
                            "context"
                        ],
                }
            )

    # ========================================================
    # API CONTRACT STRINGS
    # ========================================================

    api_strings = extract_url_like_api_strings(
        bundle_text
    )

    contract_rows = []

    for value in api_strings:

        lower = value.lower()

        if "eventssessiondetails" in lower:

            endpoint_type = (
                "EVENTS_SESSION_DETAILS"
            )

        elif "eventsbyyearseries" in lower:

            endpoint_type = (
                "EVENTS_BY_YEAR_SERIES"
            )

        else:

            endpoint_type = (
                "OTHER_RESULTS_API"
            )

        contract_rows.append(
            {
                "endpoint_type":
                    endpoint_type,

                "raw_api_string":
                    value,

                "contains_id_parameter":
                    (
                        "id="
                        in lower
                    ),

                "contains_year_parameter":
                    (
                        "year="
                        in lower
                    ),

                "contains_series_parameter":
                    (
                        "series="
                        in lower
                    ),

                "source":
                    str(
                        BUNDLE_PATH
                    ),

                "manual_review_status":
                    "UNREVIEWED",
            }
        )

    # ========================================================
    # PAGE IDENTIFIER RECOVERY
    # ========================================================

    identifier_rows = []
    successful_pages = 0

    for year, url in (
        SEED_URLS.items()
    ):

        print()
        print(
            f"FETCHING {year}: "
            f"{url}"
        )

        result = fetch_url(
            url
        )

        if not result[
            "ok"
        ]:

            identifier_rows.append(
                {
                    "year":
                        year,

                    "session_date":
                        TARGET_DATES[
                            year
                        ],

                    "identifier_type":
                        "PAGE_FETCH_FAILURE",

                    "identifier_value":
                        "",

                    "source_url":
                        url,

                    "context":
                        result[
                            "error"
                        ],

                    "manual_review_status":
                        "UNREVIEWED",
                }
            )

            time.sleep(
                REQUEST_DELAY_SECONDS
            )

            continue

        successful_pages += 1

        html = decode_text(
            result[
                "body"
            ]
        )

        # ----------------------------------------------------
        # Preserve page HTML for audit
        # ----------------------------------------------------

        html_path = (
            EVIDENCE_DIR
            /
            f"{year}_day1_results_page.html"
        )

        html_path.write_bytes(
            result[
                "body"
            ]
        )

        # ----------------------------------------------------
        # Explicit identifier regex
        # ----------------------------------------------------

        year_hit_count = 0

        for (
            identifier_type,
            patterns,
        ) in IDENTIFIER_PATTERNS.items():

            seen_values = set()

            for pattern in patterns:

                matches = re.finditer(
                    pattern,
                    html,
                    flags=re.IGNORECASE,
                )

                for match in matches:

                    value = clean_identifier(
                        match.group(
                            1
                        )
                    )

                    if not value:
                        continue

                    if value in seen_values:
                        continue

                    seen_values.add(
                        value
                    )

                    start = max(
                        0,
                        match.start()
                        - 350,
                    )

                    end = min(
                        len(
                            html
                        ),
                        match.end()
                        + 500,
                    )

                    context = (
                        html[
                            start:end
                        ]
                        .replace(
                            "\r",
                            " "
                        )
                        .replace(
                            "\n",
                            " "
                        )
                    )

                    identifier_rows.append(
                        {
                            "year":
                                year,

                            "session_date":
                                TARGET_DATES[
                                    year
                                ],

                            "identifier_type":
                                identifier_type,

                            "identifier_value":
                                value,

                            "source_url":
                                result[
                                    "final_url"
                                ],

                            "context":
                                context,

                            "manual_review_status":
                                "UNREVIEWED",
                        }
                    )

                    year_hit_count += 1

        # ----------------------------------------------------
        # Semantic page contexts even when no identifier regex
        # ----------------------------------------------------

        for semantic_term in [
            "EventsSessionID",
            "SessionReports",
            "SeasonSessions",
            "data-eventid",
            "SessionId",
            "EventID",
        ]:

            for window in context_windows(
                html,
                semantic_term,
                radius=600,
                max_hits=10,
            ):

                identifier_rows.append(
                    {
                        "year":
                            year,

                        "session_date":
                            TARGET_DATES[
                                year
                            ],

                        "identifier_type":
                            (
                                "SEMANTIC_CONTEXT_"
                                + semantic_term.upper()
                            ),

                        "identifier_value":
                            "",

                        "source_url":
                            result[
                                "final_url"
                            ],

                        "context":
                            window[
                                "context"
                            ],

                        "manual_review_status":
                            "UNREVIEWED",
                    }
                )

        print(
            "  identifier hits:",
            year_hit_count,
        )

        time.sleep(
            REQUEST_DELAY_SECONDS
        )

    # ========================================================
    # WRITE OUTPUTS
    # ========================================================

    with CONTRACT_FILE.open(
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as handle:

        fields = [
            "endpoint_type",
            "raw_api_string",
            "contains_id_parameter",
            "contains_year_parameter",
            "contains_series_parameter",
            "source",
            "manual_review_status",
        ]

        writer = csv.DictWriter(
            handle,
            fieldnames=fields,
        )

        writer.writeheader()
        writer.writerows(
            contract_rows
        )

    with PAGE_IDENTIFIER_FILE.open(
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as handle:

        fields = [
            "year",
            "session_date",
            "identifier_type",
            "identifier_value",
            "source_url",
            "context",
            "manual_review_status",
        ]

        writer = csv.DictWriter(
            handle,
            fieldnames=fields,
        )

        writer.writeheader()
        writer.writerows(
            identifier_rows
        )

    with BUNDLE_CONTEXT_FILE.open(
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as handle:

        fields = [
            "term",
            "hit_index",
            "offset",
            "context",
        ]

        writer = csv.DictWriter(
            handle,
            fieldnames=fields,
        )

        writer.writeheader()
        writer.writerows(
            bundle_context_rows
        )

    # ========================================================
    # SUMMARY COUNTS
    # ========================================================

    concrete_identifiers = [
        row
        for row in identifier_rows
        if (
            row[
                "identifier_value"
            ]
            and
            not row[
                "identifier_type"
            ].startswith(
                "SEMANTIC_CONTEXT_"
            )
        )
    ]

    years_with_concrete_ids = sorted(
        {
            row[
                "year"
            ]
            for row in concrete_identifiers
        }
    )

    events_session_contracts = [
        row
        for row in contract_rows
        if row[
            "endpoint_type"
        ]
        == "EVENTS_SESSION_DETAILS"
    ]

    # ========================================================
    # QA
    # ========================================================

    policy_payload = {
        "phase":
            PHASE,

        "policy_version":
            POLICY_VERSION,

        "target_dates":
            TARGET_DATES,

        "seed_urls":
            SEED_URLS,

        "bundle_path":
            str(
                BUNDLE_PATH
            ),

        "api_call_execution":
            False,

        "canonical_mutation":
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
                "bundle_exists",

            "value":
                int(
                    BUNDLE_PATH.exists()
                ),

            "status":
                "PASS",
        },

        {
            "metric":
                "seed_pages_successful",

            "value":
                successful_pages,

            "status":
                (
                    "PASS"
                    if successful_pages
                    == 5
                    else "FAIL"
                ),
        },

        {
            "metric":
                "bundle_context_rows",

            "value":
                len(
                    bundle_context_rows
                ),

            "status":
                (
                    "PASS"
                    if len(
                        bundle_context_rows
                    )
                    > 0
                    else "FAIL"
                ),
        },

        {
            "metric":
                "api_contract_rows",

            "value":
                len(
                    contract_rows
                ),

            "status":
                (
                    "PASS"
                    if len(
                        contract_rows
                    )
                    > 0
                    else "REVIEW"
                ),
        },

        {
            "metric":
                "events_session_details_contract_found",

            "value":
                len(
                    events_session_contracts
                ),

            "status":
                (
                    "PASS"
                    if len(
                        events_session_contracts
                    )
                    > 0
                    else "REVIEW"
                ),
        },

        {
            "metric":
                "concrete_page_identifier_rows",

            "value":
                len(
                    concrete_identifiers
                ),

            "status":
                "INFO",
        },

        {
            "metric":
                "years_with_concrete_identifiers",

            "value":
                ",".join(
                    str(year)
                    for year in years_with_concrete_ids
                ),

            "status":
                (
                    "PASS"
                    if len(
                        years_with_concrete_ids
                    )
                    >= 3
                    else "REVIEW"
                ),
        },

        {
            "metric":
                "api_calls_executed",

            "value":
                0,

            "status":
                "PASS",
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
                "policy_hash",

            "value":
                policy_hash,

            "status":
                "INFO",
        },
    ]

    with QA_FILE.open(
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as handle:

        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "metric",
                "value",
                "status",
            ],
        )

        writer.writeheader()
        writer.writerows(
            qa_rows
        )

    # ========================================================
    # PRINT
    # ========================================================

    print()
    print("API CONTRACT STRINGS")
    print("-" * 150)

    for row in contract_rows:

        print(
            f"{row['endpoint_type']:<28} | "
            f"id={row['contains_id_parameter']} | "
            f"year={row['contains_year_parameter']} | "
            f"series={row['contains_series_parameter']} | "
            f"{row['raw_api_string']}"
        )

    print()
    print("BUNDLE CONTRACT CONTEXT")
    print("-" * 160)

    priority_terms = [
        "EventsSessionDetails",
        "UpdateSession",
        "SeasonSessions",
        "EventsSessionID",
        "SessionReports",
        "DriverSessions",
        "SessionId",
        "EventID",
    ]

    shown = 0

    for term in priority_terms:

        matching = [
            row
            for row in bundle_context_rows
            if row[
                "term"
            ]
            == term
        ]

        for row in matching[:5]:

            print()
            print(
                f"TERM: {term} "
                f"| hit={row['hit_index']} "
                f"| offset={row['offset']}"
            )

            print(
                row[
                    "context"
                ][:3500]
            )

            shown += 1

    print()
    print("CONCRETE PAGE IDENTIFIERS")
    print("-" * 160)

    if not concrete_identifiers:

        print(
            "NO CONCRETE IDENTIFIERS FOUND "
            "IN STATIC PAGE HTML."
        )

    else:

        for row in concrete_identifiers:

            print(
                f"{row['year']} | "
                f"{row['identifier_type']:<24} | "
                f"{row['identifier_value']}"
            )

            print(
                "    ",
                row[
                    "context"
                ][:1000]
            )

    print()
    print("QA")
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
        "# Phase R1D — Official Results API Contract Recovery"
    )

    report.append("")

    report.append(
        f"Policy hash: `{policy_hash}`"
    )

    report.append("")

    report.append(
        "## Purpose"
    )

    report.append("")

    report.append(
        "Recover the exact INDYCAR results-page API contract "
        "and identify grounded event/session identifiers before "
        "making any API calls."
    )

    report.append("")

    report.append(
        f"- API contract candidates: `{len(contract_rows)}`"
    )

    report.append(
        f"- EventsSessionDetails contracts: "
        f"`{len(events_session_contracts)}`"
    )

    report.append(
        f"- Concrete static-page identifiers: "
        f"`{len(concrete_identifiers)}`"
    )

    report.append(
        f"- Years with concrete identifiers: "
        f"`{years_with_concrete_ids}`"
    )

    report.append("")

    report.append(
        "No results API was invoked in this phase."
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
    # FINAL
    # ========================================================

    print()
    print("=" * 100)

    if (
        len(
            events_session_contracts
        )
        > 0
    ):

        print(
            "FINAL STATUS: "
            "OFFICIAL_RESULTS_API_CONTRACT_RECOVERED"
        )

    else:

        print(
            "FINAL STATUS: "
            "OFFICIAL_RESULTS_API_CONTRACT_REVIEW_REQUIRED"
        )

    print("=" * 100)

    print()
    print(
        "NO RESULTS API CALL WAS EXECUTED."
    )

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
    print("OUTPUTS")

    print(
        CONTRACT_FILE
    )

    print(
        PAGE_IDENTIFIER_FILE
    )

    print(
        BUNDLE_CONTEXT_FILE
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
