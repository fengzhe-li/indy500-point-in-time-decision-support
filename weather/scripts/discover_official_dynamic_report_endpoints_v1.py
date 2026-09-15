from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse, unquote
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

PHASE = "R1C"
POLICY_VERSION = "OFFICIAL_DYNAMIC_REPORT_ENDPOINT_DISCOVERY_V1"


# ============================================================
# OUTPUTS
# ============================================================

OUTPUT_DIR = Path("weather/output")
EVIDENCE_DIR = Path(
    "weather/evidence/rescue/official_dynamic_resources"
)

PAGE_AUDIT_FILE = OUTPUT_DIR / (
    "official_dynamic_page_audit_v1.csv"
)

SCRIPT_INVENTORY_FILE = OUTPUT_DIR / (
    "official_dynamic_script_inventory_v1.csv"
)

ENDPOINT_CANDIDATE_FILE = OUTPUT_DIR / (
    "official_dynamic_endpoint_candidates_v1.csv"
)

INLINE_DATA_FILE = OUTPUT_DIR / (
    "official_dynamic_inline_data_candidates_v1.csv"
)

QA_FILE = OUTPUT_DIR / (
    "official_dynamic_endpoint_discovery_v1_qa.csv"
)

REPORT_FILE = OUTPUT_DIR / (
    "official_dynamic_endpoint_discovery_v1.md"
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

ALLOWED_HOST_PATTERNS = [
    "indycar.com",
    ".indycar.com",
]


# ============================================================
# SEARCH TERMS
# ============================================================

DYNAMIC_TERMS = [
    "fetch(",
    "xmlhttprequest",
    "axios",
    "$.ajax",
    "$.get",
    "$.post",
    "/api/",
    "api/",
    "graphql",
    "sitecore",
    "report",
    "reports",
    "detailedreport",
    "detailreport",
    "sessionreport",
    "summaryreport",
    "officiatingreport",
    "sessionid",
    "session_id",
    "eventid",
    "event_id",
    "raceid",
    "race_id",
    "championshipid",
    "championship_id",
    "leaderboard",
    "timing",
    "scoring",
    "classification",
    "results",
    "qualification",
    "qualifying",
    "ajax",
    "json",
]

HIGH_VALUE_TERMS = [
    "sessionreport",
    "detailedreport",
    "detailreport",
    "officiatingreport",
    "leaderboard",
    "timing",
    "scoring",
    "sessionid",
    "eventid",
    "/api/",
    "graphql",
    "qualification",
]

ENDPOINT_PATTERNS = [
    r'https?://[A-Za-z0-9._~:/?#\[\]@!$&()*+,;=%-]+',
    r'["\']([^"\']*/api/[^"\']+)["\']',
    r'["\']([^"\']*(?:report|reports|timing|leaderboard|scoring|classification)[^"\']*)["\']',
    r'["\']([^"\']*(?:sessionId|eventId|raceId|championshipId)[^"\']*)["\']',
]

INLINE_JSON_PATTERNS = [
    r'__NEXT_DATA__',
    r'application/json',
    r'window\.__',
    r'initialState',
    r'initialData',
    r'pageData',
    r'sessionId',
    r'eventId',
    r'raceId',
]


# ============================================================
# PARSER
# ============================================================

class ScriptParser(HTMLParser):

    def __init__(self):

        super().__init__()

        self.script_srcs = []
        self.inline_scripts = []

        self._inside_script = False
        self._current_script_src = None
        self._current_script_chunks = []

    def handle_starttag(
        self,
        tag,
        attrs,
    ):

        if tag != "script":
            return

        self._inside_script = True

        attrs_dict = dict(
            attrs
        )

        self._current_script_src = attrs_dict.get(
            "src"
        )

        self._current_script_chunks = []

        if self._current_script_src:

            self.script_srcs.append(
                self._current_script_src
            )

    def handle_data(
        self,
        data,
    ):

        if not self._inside_script:
            return

        if self._current_script_src is None:

            self._current_script_chunks.append(
                data
            )

    def handle_endtag(
        self,
        tag,
    ):

        if tag != "script":
            return

        if (
            self._inside_script
            and
            self._current_script_src is None
        ):

            text = "".join(
                self._current_script_chunks
            ).strip()

            if text:

                self.inline_scripts.append(
                    text
                )

        self._inside_script = False
        self._current_script_src = None
        self._current_script_chunks = []


# ============================================================
# HELPERS
# ============================================================

def allowed_host(
    url,
):

    try:

        host = (
            urlparse(
                url
            ).hostname
            or ""
        ).lower()

    except Exception:

        return False

    return (
        host == "indycar.com"
        or
        host.endswith(
            ".indycar.com"
        )
    )


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
                    "text/html,"
                    "application/xhtml+xml,"
                    "application/javascript,"
                    "text/javascript,"
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


def normalize_url(
    raw,
    base_url,
):

    if not raw:
        return None

    raw = (
        str(raw)
        .strip()
        .strip("\"'")
    )

    if not raw:
        return None

    if raw.startswith(
        (
            "javascript:",
            "mailto:",
            "tel:",
            "#",
        )
    ):

        return None

    try:

        return urljoin(
            base_url,
            raw,
        )

    except Exception:

        return None


def find_term_hits(
    text,
    terms,
):

    lower = (
        text
        .lower()
    )

    return [
        term
        for term in terms
        if term.lower() in lower
    ]


def extract_endpoints(
    text,
    base_url,
):

    candidates = []

    for pattern in ENDPOINT_PATTERNS:

        try:

            matches = re.findall(
                pattern,
                text,
                flags=re.IGNORECASE,
            )

        except Exception:

            matches = []

        for match in matches:

            if isinstance(
                match,
                tuple,
            ):

                match = next(
                    (
                        item
                        for item in match
                        if item
                    ),
                    "",
                )

            if not match:
                continue

            normalized = normalize_url(
                match,
                base_url,
            )

            if not normalized:
                continue

            candidates.append(
                normalized
            )

    return candidates


def endpoint_score(
    url,
    context,
):

    combined = (
        unquote(
            str(url)
        )
        + " "
        + str(
            context
        )
    ).lower()

    score = 0

    weights = {
        "/api/":
            10,

        "graphql":
            10,

        "sessionreport":
            10,

        "session-report":
            10,

        "detailedreport":
            10,

        "detailreport":
            10,

        "report":
            5,

        "leaderboard":
            9,

        "timing":
            9,

        "scoring":
            9,

        "classification":
            7,

        "sessionid":
            7,

        "eventid":
            7,

        "raceid":
            6,

        "results":
            3,

        "qualifying":
            3,

        "qualification":
            3,

        ".json":
            8,
    }

    for term, weight in (
        weights.items()
    ):

        if term in combined:

            score += weight

    return score


def extract_context(
    text,
    needle,
    radius=250,
):

    lower = text.lower()
    target = needle.lower()

    idx = lower.find(
        target
    )

    if idx < 0:

        return ""

    start = max(
        0,
        idx - radius,
    )

    end = min(
        len(
            text
        ),
        idx
        + len(
            needle
        )
        + radius,
    )

    return (
        text[
            start:end
        ]
        .replace(
            "\n",
            " ",
        )
        .replace(
            "\r",
            " ",
        )
    )


def sha256_bytes(
    body,
):

    return hashlib.sha256(
        body
    ).hexdigest()


def safe_script_name(
    year,
    index,
    url,
):

    parsed = urlparse(
        url
    )

    name = Path(
        parsed.path
    ).name

    if not name:

        name = (
            f"script_{index}.js"
        )

    name = re.sub(
        r"[^A-Za-z0-9._-]+",
        "_",
        name,
    )

    if not name.lower().endswith(
        ".js"
    ):

        name += ".js"

    return (
        f"{year}_{index:03d}_{name}"
    )


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
        "PHASE R1C — OFFICIAL DYNAMIC REPORT / "
        "TIMING ENDPOINT DISCOVERY V1"
    )
    print("=" * 100)

    page_rows = []
    script_rows = []
    endpoint_rows = []
    inline_rows = []

    # ========================================================
    # PAGE FETCH + INLINE AUDIT
    # ========================================================

    for year, seed_url in (
        SEED_URLS.items()
    ):

        print()
        print(
            f"FETCHING RESULT PAGE: "
            f"{year} {seed_url}"
        )

        result = fetch_url(
            seed_url
        )

        page_rows.append(
            {
                "year":
                    year,

                "session_date":
                    TARGET_DATES[
                        year
                    ],

                "requested_url":
                    seed_url,

                "ok":
                    result[
                        "ok"
                    ],

                "status_code":
                    result[
                        "status_code"
                    ],

                "final_url":
                    result[
                        "final_url"
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

            time.sleep(
                REQUEST_DELAY_SECONDS
            )

            continue

        html = decode_text(
            result[
                "body"
            ]
        )

        parser = ScriptParser()

        try:

            parser.feed(
                html
            )

        except Exception:

            pass

        # ----------------------------------------------------
        # Inline scripts / embedded data
        # ----------------------------------------------------

        for inline_index, inline_script in enumerate(
            parser.inline_scripts,
            start=1,
        ):

            hits = find_term_hits(
                inline_script,
                DYNAMIC_TERMS,
            )

            inline_json_hits = find_term_hits(
                inline_script,
                INLINE_JSON_PATTERNS,
            )

            if not hits and not inline_json_hits:
                continue

            snippets = []

            for term in (
                sorted(
                    set(
                        hits
                        +
                        inline_json_hits
                    )
                )[:12]
            ):

                snippet = extract_context(
                    inline_script,
                    term,
                )

                if snippet:

                    snippets.append(
                        snippet
                    )

            inline_rows.append(
                {
                    "year":
                        year,

                    "inline_script_index":
                        inline_index,

                    "dynamic_term_hits":
                        ";".join(
                            sorted(
                                set(
                                    hits
                                )
                            )
                        ),

                    "inline_data_hits":
                        ";".join(
                            sorted(
                                set(
                                    inline_json_hits
                                )
                            )
                        ),

                    "sample_context":
                        " || ".join(
                            snippets[:8]
                        ),
                }
            )

            # -----------------------------------------------
            # Endpoints inside inline scripts
            # -----------------------------------------------

            for endpoint in extract_endpoints(
                inline_script,
                result[
                    "final_url"
                ],
            ):

                context_hits = find_term_hits(
                    endpoint,
                    DYNAMIC_TERMS,
                )

                score = endpoint_score(
                    endpoint,
                    inline_script,
                )

                endpoint_rows.append(
                    {
                        "year":
                            year,

                        "source_type":
                            "INLINE_SCRIPT",

                        "source_url":
                            result[
                                "final_url"
                            ],

                        "candidate_url":
                            endpoint,

                        "host":
                            (
                                urlparse(
                                    endpoint
                                ).hostname
                                or ""
                            ),

                        "official_indycar_host":
                            allowed_host(
                                endpoint
                            ),

                        "priority_score":
                            score,

                        "keyword_hits":
                            ";".join(
                                sorted(
                                    set(
                                        context_hits
                                    )
                                )
                            ),

                        "manual_review_status":
                            "UNREVIEWED",
                    }
                )

        # ----------------------------------------------------
        # Endpoints directly in HTML source
        # ----------------------------------------------------

        html_endpoints = extract_endpoints(
            html,
            result[
                "final_url"
            ],
        )

        for endpoint in html_endpoints:

            hits = find_term_hits(
                endpoint,
                DYNAMIC_TERMS,
            )

            score = endpoint_score(
                endpoint,
                html,
            )

            endpoint_rows.append(
                {
                    "year":
                        year,

                    "source_type":
                        "HTML_SOURCE",

                    "source_url":
                        result[
                            "final_url"
                        ],

                    "candidate_url":
                        endpoint,

                    "host":
                        (
                            urlparse(
                                endpoint
                            ).hostname
                            or ""
                        ),

                    "official_indycar_host":
                        allowed_host(
                            endpoint
                        ),

                    "priority_score":
                        score,

                    "keyword_hits":
                        ";".join(
                            sorted(
                                set(
                                    hits
                                )
                            )
                        ),

                    "manual_review_status":
                        "UNREVIEWED",
                }
            )

        # ----------------------------------------------------
        # External scripts
        # ----------------------------------------------------

        unique_script_urls = []

        seen_scripts = set()

        for raw_src in (
            parser.script_srcs
        ):

            script_url = normalize_url(
                raw_src,
                result[
                    "final_url"
                ],
            )

            if not script_url:
                continue

            if script_url in seen_scripts:
                continue

            seen_scripts.add(
                script_url
            )

            unique_script_urls.append(
                script_url
            )

        print(
            "External scripts:",
            len(
                unique_script_urls
            )
        )

        for script_index, script_url in enumerate(
            unique_script_urls,
            start=1,
        ):

            # Only fetch official IndyCar-host scripts
            if not allowed_host(
                script_url
            ):

                script_rows.append(
                    {
                        "year":
                            year,

                        "script_url":
                            script_url,

                        "official_indycar_host":
                            False,

                        "fetch_attempted":
                            False,

                        "ok":
                            "",

                        "status_code":
                            "",

                        "content_type":
                            "",

                        "bytes":
                            "",

                        "sha256":
                            "",

                        "local_path":
                            "",

                        "dynamic_term_hits":
                            "",

                        "high_value_term_hits":
                            "",

                        "error":
                            "",
                    }
                )

                continue

            print(
                f"  SCRIPT [{script_index}/"
                f"{len(unique_script_urls)}] "
                f"{script_url}"
            )

            script_result = fetch_url(
                script_url
            )

            script_text = ""

            local_path = ""

            dynamic_hits = []
            high_hits = []

            if script_result[
                "ok"
            ]:

                script_text = decode_text(
                    script_result[
                        "body"
                    ]
                )

                dynamic_hits = find_term_hits(
                    script_text,
                    DYNAMIC_TERMS,
                )

                high_hits = find_term_hits(
                    script_text,
                    HIGH_VALUE_TERMS,
                )

                filename = safe_script_name(
                    year,
                    script_index,
                    script_result[
                        "final_url"
                    ],
                )

                destination = (
                    EVIDENCE_DIR
                    /
                    filename
                )

                destination.write_bytes(
                    script_result[
                        "body"
                    ]
                )

                local_path = str(
                    destination
                )

                # -------------------------------------------
                # Extract endpoint candidates from JS
                # -------------------------------------------

                for endpoint in extract_endpoints(
                    script_text,
                    script_result[
                        "final_url"
                    ],
                ):

                    endpoint_hits = find_term_hits(
                        endpoint,
                        DYNAMIC_TERMS,
                    )

                    score = endpoint_score(
                        endpoint,
                        script_text,
                    )

                    endpoint_rows.append(
                        {
                            "year":
                                year,

                            "source_type":
                                "EXTERNAL_SCRIPT",

                            "source_url":
                                script_result[
                                    "final_url"
                                ],

                            "candidate_url":
                                endpoint,

                            "host":
                                (
                                    urlparse(
                                        endpoint
                                    ).hostname
                                    or ""
                                ),

                            "official_indycar_host":
                                allowed_host(
                                    endpoint
                                ),

                            "priority_score":
                                score,

                            "keyword_hits":
                                ";".join(
                                    sorted(
                                        set(
                                            endpoint_hits
                                        )
                                    )
                                ),

                            "manual_review_status":
                                "UNREVIEWED",
                        }
                    )

            script_rows.append(
                {
                    "year":
                        year,

                    "script_url":
                        script_url,

                    "official_indycar_host":
                        True,

                    "fetch_attempted":
                        True,

                    "ok":
                        script_result[
                            "ok"
                        ],

                    "status_code":
                        script_result[
                            "status_code"
                        ],

                    "content_type":
                        script_result[
                            "content_type"
                        ],

                    "bytes":
                        len(
                            script_result[
                                "body"
                            ]
                        ),

                    "sha256":
                        (
                            sha256_bytes(
                                script_result[
                                    "body"
                                ]
                            )
                            if script_result[
                                "body"
                            ]
                            else ""
                        ),

                    "local_path":
                        local_path,

                    "dynamic_term_hits":
                        ";".join(
                            sorted(
                                set(
                                    dynamic_hits
                                )
                            )
                        ),

                    "high_value_term_hits":
                        ";".join(
                            sorted(
                                set(
                                    high_hits
                                )
                            )
                        ),

                    "error":
                        script_result[
                            "error"
                        ],
                }
            )

            time.sleep(
                REQUEST_DELAY_SECONDS
            )

        time.sleep(
            REQUEST_DELAY_SECONDS
        )

    # ========================================================
    # DEDUP ENDPOINTS
    # ========================================================

    dedup = {}

    for row in endpoint_rows:

        candidate_url = (
            row[
                "candidate_url"
            ]
            .strip()
        )

        if not candidate_url:
            continue

        # Prevent obvious HTML fragments from surviving.
        bad_fragments = [
            "<div",
            "</div",
            "<span",
            "</span",
            "<p>",
            "</p>",
            "<section",
            "</section",
        ]

        lower_url = (
            candidate_url
            .lower()
        )

        if any(
            fragment
            in lower_url
            for fragment
            in bad_fragments
        ):
            continue

        key = (
            row[
                "year"
            ],
            candidate_url,
        )

        if key not in dedup:

            dedup[
                key
            ] = row

        else:

            existing = dedup[
                key
            ]

            if (
                row[
                    "priority_score"
                ]
                >
                existing[
                    "priority_score"
                ]
            ):

                dedup[
                    key
                ] = row

    endpoint_rows = list(
        dedup.values()
    )

    endpoint_rows.sort(
        key=lambda row: (
            row[
                "year"
            ],
            -int(
                row[
                    "priority_score"
                ]
            ),
            row[
                "candidate_url"
            ],
        )
    )

    # ========================================================
    # WRITE CSVs
    # ========================================================

    page_fields = [
        "year",
        "session_date",
        "requested_url",
        "ok",
        "status_code",
        "final_url",
        "content_type",
        "bytes",
        "sha256",
        "error",
    ]

    with PAGE_AUDIT_FILE.open(
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as handle:

        writer = csv.DictWriter(
            handle,
            fieldnames=page_fields,
        )

        writer.writeheader()
        writer.writerows(
            page_rows
        )

    script_fields = [
        "year",
        "script_url",
        "official_indycar_host",
        "fetch_attempted",
        "ok",
        "status_code",
        "content_type",
        "bytes",
        "sha256",
        "local_path",
        "dynamic_term_hits",
        "high_value_term_hits",
        "error",
    ]

    with SCRIPT_INVENTORY_FILE.open(
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as handle:

        writer = csv.DictWriter(
            handle,
            fieldnames=script_fields,
        )

        writer.writeheader()
        writer.writerows(
            script_rows
        )

    endpoint_fields = [
        "year",
        "source_type",
        "source_url",
        "candidate_url",
        "host",
        "official_indycar_host",
        "priority_score",
        "keyword_hits",
        "manual_review_status",
    ]

    with ENDPOINT_CANDIDATE_FILE.open(
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as handle:

        writer = csv.DictWriter(
            handle,
            fieldnames=endpoint_fields,
        )

        writer.writeheader()
        writer.writerows(
            endpoint_rows
        )

    inline_fields = [
        "year",
        "inline_script_index",
        "dynamic_term_hits",
        "inline_data_hits",
        "sample_context",
    ]

    with INLINE_DATA_FILE.open(
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as handle:

        writer = csv.DictWriter(
            handle,
            fieldnames=inline_fields,
        )

        writer.writeheader()
        writer.writerows(
            inline_rows
        )

    # ========================================================
    # QA
    # ========================================================

    successful_pages = sum(
        1
        for row in page_rows
        if row[
            "ok"
        ]
    )

    official_scripts_attempted = sum(
        1
        for row in script_rows
        if row[
            "fetch_attempted"
        ]
        is True
    )

    successful_scripts = sum(
        1
        for row in script_rows
        if row[
            "ok"
        ]
        is True
    )

    scripts_with_high_value_hits = sum(
        1
        for row in script_rows
        if row[
            "high_value_term_hits"
        ]
    )

    high_value_endpoints = sum(
        1
        for row in endpoint_rows
        if int(
            row[
                "priority_score"
            ]
        ) >= 15
    )

    api_like_endpoints = sum(
        1
        for row in endpoint_rows
        if (
            "/api/"
            in row[
                "candidate_url"
            ].lower()
            or
            "graphql"
            in row[
                "candidate_url"
            ].lower()
            or
            ".json"
            in row[
                "candidate_url"
            ].lower()
        )
    )

    years_with_endpoint_candidates = sorted(
        {
            row[
                "year"
            ]
            for row in endpoint_rows
        }
    )

    policy_payload = {
        "phase":
            PHASE,

        "policy_version":
            POLICY_VERSION,

        "target_dates":
            TARGET_DATES,

        "seed_urls":
            SEED_URLS,

        "allowed_hosts":
            ALLOWED_HOST_PATTERNS,

        "canonical_mutation":
            False,

        "script_execution":
            False,

        "dynamic_resource_discovery_only":
            True,
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
                "seed_pages_expected_5",

            "value":
                len(
                    page_rows
                ),

            "status":
                (
                    "PASS"
                    if len(
                        page_rows
                    )
                    == 5
                    else "FAIL"
                ),
        },

        {
            "metric":
                "successful_seed_pages",

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
                "official_scripts_fetch_attempted",

            "value":
                official_scripts_attempted,

            "status":
                "INFO",
        },

        {
            "metric":
                "successful_official_script_fetches",

            "value":
                successful_scripts,

            "status":
                (
                    "PASS"
                    if (
                        official_scripts_attempted
                        == 0
                        or
                        successful_scripts
                        > 0
                    )
                    else "REVIEW"
                ),
        },

        {
            "metric":
                "scripts_with_high_value_hits",

            "value":
                scripts_with_high_value_hits,

            "status":
                "INFO",
        },

        {
            "metric":
                "inline_data_candidate_rows",

            "value":
                len(
                    inline_rows
                ),

            "status":
                "INFO",
        },

        {
            "metric":
                "endpoint_candidate_rows",

            "value":
                len(
                    endpoint_rows
                ),

            "status":
                (
                    "PASS"
                    if len(
                        endpoint_rows
                    )
                    > 0
                    else "REVIEW"
                ),
        },

        {
            "metric":
                "high_value_endpoint_candidates_score_ge_15",

            "value":
                high_value_endpoints,

            "status":
                "INFO",
        },

        {
            "metric":
                "api_json_graphql_candidates",

            "value":
                api_like_endpoints,

            "status":
                "INFO",
        },

        {
            "metric":
                "years_with_endpoint_candidates",

            "value":
                ",".join(
                    str(
                        year
                    )
                    for year in years_with_endpoint_candidates
                ),

            "status":
                (
                    "PASS"
                    if len(
                        years_with_endpoint_candidates
                    )
                    >= 3
                    else "REVIEW"
                ),
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
                "scripts_executed",

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
    # REPORT
    # ========================================================

    report = []

    report.append(
        "# Phase R1C — Official Dynamic Report / "
        "Timing Endpoint Discovery"
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
        "Inspect official INDYCAR result-page HTML, "
        "inline scripts, and official JavaScript resources "
        "for dynamic report, timing, scoring, leaderboard, "
        "session, and API endpoint traces."
    )

    report.append("")

    report.append(
        "No JavaScript was executed."
    )

    report.append(
        "No canonical data was modified."
    )

    report.append("")

    report.append(
        "## Summary"
    )

    report.append("")

    report.append(
        f"- Successful result pages: `{successful_pages}/5`"
    )

    report.append(
        f"- Official scripts attempted: "
        f"`{official_scripts_attempted}`"
    )

    report.append(
        f"- Successful script fetches: "
        f"`{successful_scripts}`"
    )

    report.append(
        f"- Scripts with high-value terminology: "
        f"`{scripts_with_high_value_hits}`"
    )

    report.append(
        f"- Inline-data candidates: "
        f"`{len(inline_rows)}`"
    )

    report.append(
        f"- Endpoint candidates: "
        f"`{len(endpoint_rows)}`"
    )

    report.append(
        f"- High-value endpoint candidates: "
        f"`{high_value_endpoints}`"
    )

    report.append(
        f"- API/JSON/GraphQL-like candidates: "
        f"`{api_like_endpoints}`"
    )

    report.append("")

    report.append(
        "## Interpretation"
    )

    report.append("")

    report.append(
        "Candidate strings are discovery evidence only. "
        "They are not automatically treated as working APIs "
        "or historical timing/report sources."
    )

    report.append("")

    report.append(
        "Any endpoint that appears promising should be tested "
        "individually in a later evidence-rescue phase."
    )

    REPORT_FILE.write_text(
        "\n".join(
            report
        ),
        encoding="utf-8",
    )

    # ========================================================
    # PRINT
    # ========================================================

    print()
    print("DYNAMIC DISCOVERY SUMMARY")
    print("-" * 120)

    print(
        "Successful pages:",
        successful_pages,
        "/ 5",
    )

    print(
        "Official scripts attempted:",
        official_scripts_attempted,
    )

    print(
        "Successful script fetches:",
        successful_scripts,
    )

    print(
        "Scripts with high-value hits:",
        scripts_with_high_value_hits,
    )

    print(
        "Inline data candidates:",
        len(
            inline_rows
        ),
    )

    print(
        "Endpoint candidates:",
        len(
            endpoint_rows
        ),
    )

    print(
        "High-value endpoint candidates:",
        high_value_endpoints,
    )

    print(
        "API/JSON/GraphQL-like candidates:",
        api_like_endpoints,
    )

    print()
    print("TOP 60 ENDPOINT CANDIDATES")
    print("-" * 180)

    for row in endpoint_rows[:60]:

        print(
            f"{row['year']} | "
            f"score={row['priority_score']:>3} | "
            f"{row['source_type']:<16} | "
            f"{row['candidate_url']}"
        )

        if row[
            "keyword_hits"
        ]:

            print(
                "    keywords:",
                row[
                    "keyword_hits"
                ],
            )

    print()
    print("SCRIPTS WITH HIGH-VALUE TERMS")
    print("-" * 180)

    for row in script_rows:

        if not row[
            "high_value_term_hits"
        ]:
            continue

        print(
            f"{row['year']} | "
            f"{row['script_url']}"
        )

        print(
            "    high-value:",
            row[
                "high_value_term_hits"
            ]
        )

        print(
            "    local:",
            row[
                "local_path"
            ]
        )

    print()
    print("INLINE DATA CANDIDATES")
    print("-" * 160)

    for row in inline_rows[:40]:

        print(
            f"{row['year']} | "
            f"inline #{row['inline_script_index']} | "
            f"dynamic={row['dynamic_term_hits']} | "
            f"data={row['inline_data_hits']}"
        )

        if row[
            "sample_context"
        ]:

            print(
                "    context:",
                row[
                    "sample_context"
                ][:1200]
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

    print()
    print("=" * 100)

    if (
        successful_pages
        == 5
        and
        len(
            endpoint_rows
        )
        > 0
    ):

        print(
            "FINAL STATUS: "
            "OFFICIAL_DYNAMIC_ENDPOINT_DISCOVERY_READY_FOR_REVIEW"
        )

    else:

        print(
            "FINAL STATUS: "
            "OFFICIAL_DYNAMIC_ENDPOINT_DISCOVERY_REVIEW_REQUIRED"
        )

    print("=" * 100)

    print()
    print(
        "NO JAVASCRIPT WAS EXECUTED."
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
        PAGE_AUDIT_FILE
    )

    print(
        SCRIPT_INVENTORY_FILE
    )

    print(
        ENDPOINT_CANDIDATE_FILE
    )

    print(
        INLINE_DATA_FILE
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
