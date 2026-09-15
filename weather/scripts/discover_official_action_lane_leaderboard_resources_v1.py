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

PHASE = "R1A"
POLICY_VERSION = "OFFICIAL_ACTION_LANE_LEADERBOARD_RESOURCE_DISCOVERY_V1"


# ============================================================
# REPOSITORY ROOTS
# ============================================================

EVIDENCE_ROOTS = [
    Path("weather/evidence"),
]

SCRIPT_ROOTS = [
    Path("weather/scripts"),
]

OUTPUT_DIR = Path("weather/output")


# ============================================================
# OUTPUTS
# ============================================================

OFFICIAL_RESOURCE_FILE = OUTPUT_DIR / (
    "official_action_lane_leaderboard_resource_candidates_v1.csv"
)

LOCAL_EVIDENCE_FILE = OUTPUT_DIR / (
    "official_action_lane_leaderboard_local_evidence_hits_v1.csv"
)

FETCH_AUDIT_FILE = OUTPUT_DIR / (
    "official_action_lane_leaderboard_fetch_audit_v1.csv"
)

SUMMARY_FILE = OUTPUT_DIR / (
    "official_action_lane_leaderboard_resource_discovery_v1.md"
)

QA_FILE = OUTPUT_DIR / (
    "official_action_lane_leaderboard_resource_discovery_v1_qa.csv"
)


# ============================================================
# TARGET DATES
# ============================================================

TARGET_DATES = {
    2020: "2020-08-15",
    2021: "2021-05-22",
    2022: "2022-05-21",
    2023: "2023-05-20",
    2024: "2024-05-18",
}


# ============================================================
# OFFICIAL SEED URLS
#
# These are reconnaissance seeds only.
# A failed candidate URL is recorded, not treated as evidence.
# ============================================================

SEED_URLS = {
    2020: [
        "https://www.indycar.com/results/ntt-indycar-series/2020/104th-running-of-the-indianapolis-500/qualifications---day-1",
        "https://www.indycar.com/schedule/2020/indianapolis-500",
    ],

    2021: [
        "https://www.indycar.com/results/ntt-indycar-series/2021/105th-running-of-the-indianapolis-500/qualifications---day-1",
        "https://www.indycar.com/schedule/2021/indianapolis-500",
    ],

    2022: [
        "https://www.indycar.com/results/ntt-indycar-series/2022/106th-running-of-the-indianapolis-500/qualifications---day-1",
        "https://www.indycar.com/schedule/2022/indianapolis-500",
    ],

    2023: [
        "https://www.indycar.com/results/ntt-indycar-series/2023/107th-running-of-the-indianapolis-500/qualifications---day-1",
        "https://www.indycar.com/schedule/2023/indianapolis-500",
    ],

    2024: [
        "https://www.indycar.com/results/ntt-indycar-series/2024/108th-running-of-the-indianapolis-500/qualifications---day-1",
        "https://www.indycar.com/schedule/2024/indianapolis-500",
    ],
}


# ============================================================
# KEYWORDS
# ============================================================

HIGH_VALUE_KEYWORDS = [
    "lane 1",
    "lane 2",
    "priority lane",
    "second lane",
    "withdraw",
    "withdrawn",
    "withdrawal",
    "requalify",
    "re-qualified",
    "requalified",
    "requeue",
    "re-queue",
    "queue",
    "line",
    "back in line",
    "leaderboard",
    "live timing",
    "timing and scoring",
    "timing & scoring",
    "race control",
    "racecontrol",
    "session report",
    "detailed report",
    "qualifying report",
    "qualification report",
    "results report",
    "event stream",
    "session id",
    "sessionid",
    "timing",
    "scoring",
    "classification",
    "position",
    "rank",
    "bump",
    "bump line",
    "top 12",
    "fast nine",
    "last chance",
]

RESOURCE_KEYWORDS = [
    "timing",
    "scoring",
    "leaderboard",
    "result",
    "results",
    "report",
    "reports",
    "session",
    "qualification",
    "qualifying",
    "racecontrol",
    "race-control",
    "live",
    "classification",
    "entry",
    "entries",
    "standings",
    "position",
    "lane",
    "queue",
    "withdraw",
    "indy500",
    "indy-500",
]

VALUABLE_EXTENSIONS = [
    ".pdf",
    ".json",
    ".csv",
    ".xml",
    ".txt",
    ".js",
]

URL_PATTERNS = [
    r'https?://[^\s"\'<>]+',
    r'["\']([^"\']+\.(?:pdf|json|csv|xml|txt|js)(?:\?[^"\']*)?)["\']',
    r'["\']([^"\']*(?:api|timing|leaderboard|racecontrol|session|results|reports)[^"\']*)["\']',
]

LOCAL_FILE_EXTENSIONS = {
    ".csv",
    ".txt",
    ".md",
    ".json",
    ".xml",
    ".html",
    ".htm",
    ".js",
    ".py",
}


# ============================================================
# NETWORK
# ============================================================

USER_AGENT = (
    "Mozilla/5.0 "
    "(compatible; Indy500HistoricalEvidenceResearch/1.0; "
    "academic-resource-discovery)"
)

REQUEST_TIMEOUT_SECONDS = 25
REQUEST_DELAY_SECONDS = 1.5

ALLOWED_HOST_SUFFIXES = [
    "indycar.com",
    ".indycar.com",
]


# ============================================================
# HTML PARSER
# ============================================================

class LinkParser(HTMLParser):

    def __init__(self):
        super().__init__()
        self.links = []
        self.scripts = []
        self.frames = []
        self.text_chunks = []

    def handle_starttag(self, tag, attrs):

        attrs_dict = dict(attrs)

        if tag == "a":

            href = attrs_dict.get("href")

            if href:
                self.links.append(href)

        elif tag == "script":

            src = attrs_dict.get("src")

            if src:
                self.scripts.append(src)

        elif tag in {
            "iframe",
            "frame",
        }:

            src = attrs_dict.get("src")

            if src:
                self.frames.append(src)

        elif tag == "link":

            href = attrs_dict.get("href")

            if href:
                self.links.append(href)

    def handle_data(self, data):

        cleaned = (
            data
            .strip()
        )

        if cleaned:
            self.text_chunks.append(
                cleaned
            )


# ============================================================
# HELPERS
# ============================================================

def normalize_url(
    candidate,
    base_url,
):

    if candidate is None:
        return None

    candidate = (
        str(candidate)
        .strip()
        .strip("\"'")
    )

    if not candidate:
        return None

    if candidate.startswith(
        (
            "javascript:",
            "mailto:",
            "tel:",
            "#",
        )
    ):
        return None

    try:

        url = urljoin(
            base_url,
            candidate,
        )

        return url

    except Exception:

        return None


def allowed_official_url(
    url,
):

    try:

        host = (
            urlparse(url)
            .hostname
            or ""
        ).lower()

    except Exception:

        return False

    return any(
        host == suffix.lstrip(".")
        or host.endswith(suffix)
        for suffix in ALLOWED_HOST_SUFFIXES
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

            status = getattr(
                response,
                "status",
                200,
            )

            content_type = (
                response
                .headers
                .get(
                    "Content-Type",
                    "",
                )
            )

            final_url = response.geturl()

            elapsed = (
                time.time()
                - started
            )

            return {
                "ok":
                    True,

                "status_code":
                    status,

                "content_type":
                    content_type,

                "final_url":
                    final_url,

                "body":
                    body,

                "elapsed_seconds":
                    elapsed,

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


def decode_body(
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


def keyword_hits(
    text,
    keywords,
):

    lower = (
        text
        .lower()
    )

    return [
        keyword
        for keyword in keywords
        if keyword.lower() in lower
    ]


def classify_resource(
    url,
):

    lower = (
        unquote(url)
        .lower()
    )

    path = (
        urlparse(lower)
        .path
    )

    suffix = (
        Path(path)
        .suffix
        .lower()
    )

    if suffix == ".pdf":
        return "PDF"

    if suffix == ".json":
        return "JSON"

    if suffix == ".csv":
        return "CSV"

    if suffix == ".xml":
        return "XML"

    if suffix == ".js":
        return "JAVASCRIPT"

    if "racecontrol" in lower:
        return "RACECONTROL_CANDIDATE"

    if "leaderboard" in lower:
        return "LEADERBOARD_CANDIDATE"

    if "timing" in lower:
        return "TIMING_CANDIDATE"

    if "report" in lower:
        return "REPORT_CANDIDATE"

    if "session" in lower:
        return "SESSION_CANDIDATE"

    if "result" in lower:
        return "RESULTS_CANDIDATE"

    if "live" in lower:
        return "LIVE_CANDIDATE"

    return "OTHER"


def score_resource(
    url,
    keyword_list,
    resource_type,
):

    score = 0

    lower = (
        unquote(url)
        .lower()
    )

    high_weight_terms = {
        "timing":
            5,

        "scoring":
            5,

        "leaderboard":
            6,

        "racecontrol":
            7,

        "session":
            3,

        "report":
            3,

        "results":
            2,

        "qualification":
            2,

        "qualifying":
            2,

        "lane":
            4,

        "queue":
            5,

        "withdraw":
            5,

        ".json":
            6,

        ".csv":
            5,

        ".xml":
            5,

        ".pdf":
            4,
    }

    for term, weight in (
        high_weight_terms.items()
    ):

        if term in lower:
            score += weight

    score += (
        len(keyword_list)
        * 2
    )

    if resource_type in {
        "JSON",
        "CSV",
        "XML",
        "RACECONTROL_CANDIDATE",
        "LEADERBOARD_CANDIDATE",
        "TIMING_CANDIDATE",
    }:
        score += 5

    return score


def sha256_bytes(
    content,
):

    return hashlib.sha256(
        content
    ).hexdigest()


def safe_read_text(
    path,
):

    try:

        return path.read_text(
            encoding="utf-8"
        )

    except UnicodeDecodeError:

        try:

            return path.read_text(
                encoding="latin-1"
            )

        except Exception:

            return None

    except Exception:

        return None


def infer_year_from_text(
    text,
):

    found = []

    for year in TARGET_DATES:

        if str(year) in text:
            found.append(year)

    if len(found) == 1:
        return found[0]

    return None


# ============================================================
# LOCAL SCAN
# ============================================================

def scan_local_assets():

    rows = []

    roots = (
        EVIDENCE_ROOTS
        +
        SCRIPT_ROOTS
    )

    for root in roots:

        if not root.exists():
            continue

        for path in root.rglob("*"):

            if not path.is_file():
                continue

            if (
                path.suffix.lower()
                not in LOCAL_FILE_EXTENSIONS
            ):
                continue

            text = safe_read_text(
                path
            )

            if text is None:
                continue

            hits = keyword_hits(
                text,
                HIGH_VALUE_KEYWORDS,
            )

            resource_hits = keyword_hits(
                text,
                RESOURCE_KEYWORDS,
            )

            if not hits and not resource_hits:
                continue

            year = infer_year_from_text(
                (
                    str(path)
                    + "\n"
                    + text[:10000]
                )
            )

            snippets = []

            lower = text.lower()

            for keyword in (
                hits[:10]
            ):

                idx = lower.find(
                    keyword.lower()
                )

                if idx < 0:
                    continue

                start = max(
                    0,
                    idx - 180,
                )

                end = min(
                    len(text),
                    idx + 300,
                )

                snippet = (
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

                snippets.append(
                    snippet
                )

            rows.append(
                {
                    "year":
                        year
                        if year is not None
                        else "",

                    "local_path":
                        str(path),

                    "file_type":
                        path.suffix.lower(),

                    "high_value_keyword_hits":
                        ";".join(
                            sorted(
                                set(
                                    hits
                                )
                            )
                        ),

                    "resource_keyword_hits":
                        ";".join(
                            sorted(
                                set(
                                    resource_hits
                                )
                            )
                        ),

                    "sample_context":
                        " || ".join(
                            snippets[:5]
                        ),

                    "manual_review_status":
                        "UNREVIEWED",
                }
            )

    return rows


# ============================================================
# WEB RESOURCE DISCOVERY
# ============================================================

def discover_page_resources(
    year,
    seed_url,
    html_text,
):

    parser = LinkParser()

    try:

        parser.feed(
            html_text
        )

    except Exception:
        pass

    candidates = []

    raw_candidates = (
        parser.links
        +
        parser.scripts
        +
        parser.frames
    )

    for pattern in URL_PATTERNS:

        try:

            matches = re.findall(
                pattern,
                html_text,
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

            if match:
                raw_candidates.append(
                    match
                )

    seen = set()

    for raw_candidate in raw_candidates:

        url = normalize_url(
            raw_candidate,
            seed_url,
        )

        if not url:
            continue

        if url in seen:
            continue

        seen.add(
            url
        )

        decoded = (
            unquote(url)
        )

        hits = keyword_hits(
            decoded,
            RESOURCE_KEYWORDS,
        )

        path = (
            urlparse(url)
            .path
            .lower()
        )

        extension_hit = any(
            path.endswith(
                ext
            )
            for ext in VALUABLE_EXTENSIONS
        )

        resource_type = (
            classify_resource(
                url
            )
        )

        if (
            not hits
            and
            not extension_hit
            and
            resource_type == "OTHER"
        ):
            continue

        official = (
            allowed_official_url(
                url
            )
        )

        score = score_resource(
            url,
            hits,
            resource_type,
        )

        candidates.append(
            {
                "year":
                    year,

                "session_date":
                    TARGET_DATES[
                        year
                    ],

                "seed_url":
                    seed_url,

                "discovered_url":
                    url,

                "host":
                    (
                        urlparse(url)
                        .hostname
                        or ""
                    ),

                "resource_type":
                    resource_type,

                "resource_keywords":
                    ";".join(
                        sorted(
                            set(
                                hits
                            )
                        )
                    ),

                "official_indycar_host":
                    official,

                "priority_score":
                    score,

                "source_of_discovery":
                    "HTML_LINK_OR_SOURCE",

                "manual_review_status":
                    "UNREVIEWED",

                "notes":
                    "",
            }
        )

    # --------------------------------------------------------
    # Also preserve direct textual evidence that the seed page
    # itself mentions high-value terms.
    # --------------------------------------------------------

    page_hits = keyword_hits(
        "\n".join(
            parser.text_chunks
        ),
        HIGH_VALUE_KEYWORDS,
    )

    if page_hits:

        candidates.append(
            {
                "year":
                    year,

                "session_date":
                    TARGET_DATES[
                        year
                    ],

                "seed_url":
                    seed_url,

                "discovered_url":
                    seed_url,

                "host":
                    (
                        urlparse(seed_url)
                        .hostname
                        or ""
                    ),

                "resource_type":
                    "SEED_PAGE_TEXT_HIT",

                "resource_keywords":
                    ";".join(
                        sorted(
                            set(
                                page_hits
                            )
                        )
                    ),

                "official_indycar_host":
                    True,

                "priority_score":
                    (
                        10
                        +
                        len(
                            page_hits
                        )
                    ),

                "source_of_discovery":
                    "VISIBLE_PAGE_TEXT",

                "manual_review_status":
                    "UNREVIEWED",

                "notes":
                    (
                        "Seed page itself contains "
                        "high-value action/lane/"
                        "leaderboard terminology."
                    ),
            }
        )

    return candidates


# ============================================================
# MAIN
# ============================================================

def main():

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print()
    print("=" * 100)
    print(
        "PHASE R1A — OFFICIAL ACTION / LANE / "
        "LEADERBOARD RESOURCE DISCOVERY V1"
    )
    print("=" * 100)

    # ========================================================
    # 1. LOCAL ASSET SCAN
    # ========================================================

    print()
    print(
        "STEP 1 — SCANNING EXISTING LOCAL ASSETS"
    )
    print("-" * 100)

    local_rows = scan_local_assets()

    print(
        "Local candidate files:",
        len(
            local_rows
        )
    )

    # ========================================================
    # 2. LIMITED OFFICIAL FETCH
    # ========================================================

    print()
    print(
        "STEP 2 — LIMITED OFFICIAL INDYCAR RESOURCE DISCOVERY"
    )
    print("-" * 100)

    fetch_rows = []
    resource_rows = []

    seed_count = sum(
        len(
            urls
        )
        for urls in SEED_URLS.values()
    )

    fetch_index = 0

    for year, urls in (
        SEED_URLS.items()
    ):

        for seed_url in urls:

            fetch_index += 1

            print(
                f"[{fetch_index}/{seed_count}] "
                f"{year} "
                f"{seed_url}"
            )

            result = fetch_url(
                seed_url
            )

            body_sha = (
                sha256_bytes(
                    result[
                        "body"
                    ]
                )
                if result[
                    "body"
                ]
                else ""
            )

            fetch_rows.append(
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
                        body_sha,

                    "elapsed_seconds":
                        round(
                            result[
                                "elapsed_seconds"
                            ],
                            3,
                        ),

                    "error":
                        result[
                            "error"
                        ],
                }
            )

            if result[
                "ok"
            ]:

                text = decode_body(
                    result[
                        "body"
                    ]
                )

                discovered = (
                    discover_page_resources(
                        year=year,
                        seed_url=result[
                            "final_url"
                        ],
                        html_text=text,
                    )
                )

                resource_rows.extend(
                    discovered
                )

            time.sleep(
                REQUEST_DELAY_SECONDS
            )

    # ========================================================
    # DEDUP RESOURCE ROWS
    # ========================================================

    dedup = {}

    for row in resource_rows:

        key = (
            row[
                "year"
            ],
            row[
                "discovered_url"
            ],
            row[
                "resource_type"
            ],
        )

        if key not in dedup:

            dedup[
                key
            ] = row

        else:

            existing = dedup[
                key
            ]

            merged_keywords = set(
                filter(
                    None,
                    existing[
                        "resource_keywords"
                    ].split(
                        ";"
                    ),
                )
            )

            merged_keywords.update(
                filter(
                    None,
                    row[
                        "resource_keywords"
                    ].split(
                        ";"
                    ),
                )
            )

            existing[
                "resource_keywords"
            ] = ";".join(
                sorted(
                    merged_keywords
                )
            )

            existing[
                "priority_score"
            ] = max(
                existing[
                    "priority_score"
                ],
                row[
                    "priority_score"
                ],
            )

    resource_rows = list(
        dedup.values()
    )

    resource_rows.sort(
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
                "discovered_url"
            ],
        )
    )

    # ========================================================
    # WRITE CSVs
    # ========================================================

    local_fields = [
        "year",
        "local_path",
        "file_type",
        "high_value_keyword_hits",
        "resource_keyword_hits",
        "sample_context",
        "manual_review_status",
    ]

    with LOCAL_EVIDENCE_FILE.open(
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as handle:

        writer = csv.DictWriter(
            handle,
            fieldnames=local_fields,
        )

        writer.writeheader()

        writer.writerows(
            local_rows
        )

    resource_fields = [
        "year",
        "session_date",
        "seed_url",
        "discovered_url",
        "host",
        "resource_type",
        "resource_keywords",
        "official_indycar_host",
        "priority_score",
        "source_of_discovery",
        "manual_review_status",
        "notes",
    ]

    with OFFICIAL_RESOURCE_FILE.open(
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as handle:

        writer = csv.DictWriter(
            handle,
            fieldnames=resource_fields,
        )

        writer.writeheader()

        writer.writerows(
            resource_rows
        )

    fetch_fields = [
        "year",
        "session_date",
        "requested_url",
        "ok",
        "status_code",
        "final_url",
        "content_type",
        "bytes",
        "sha256",
        "elapsed_seconds",
        "error",
    ]

    with FETCH_AUDIT_FILE.open(
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as handle:

        writer = csv.DictWriter(
            handle,
            fieldnames=fetch_fields,
        )

        writer.writeheader()

        writer.writerows(
            fetch_rows
        )

    # ========================================================
    # QA
    # ========================================================

    successful_fetches = sum(
        1
        for row in fetch_rows
        if row[
            "ok"
        ]
    )

    failed_fetches = (
        len(
            fetch_rows
        )
        -
        successful_fetches
    )

    official_resource_count = sum(
        1
        for row in resource_rows
        if row[
            "official_indycar_host"
        ]
    )

    high_priority_count = sum(
        1
        for row in resource_rows
        if int(
            row[
                "priority_score"
            ]
        ) >= 10
    )

    structured_count = sum(
        1
        for row in resource_rows
        if row[
            "resource_type"
        ]
        in {
            "PDF",
            "JSON",
            "CSV",
            "XML",
            "RACECONTROL_CANDIDATE",
            "LEADERBOARD_CANDIDATE",
            "TIMING_CANDIDATE",
        }
    )

    years_with_success = sorted(
        {
            row[
                "year"
            ]
            for row in fetch_rows
            if row[
                "ok"
            ]
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
            ALLOWED_HOST_SUFFIXES,

        "request_delay_seconds":
            REQUEST_DELAY_SECONDS,

        "discovery_only":
            True,

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
                "seed_urls_total",

            "value":
                len(
                    fetch_rows
                ),

            "status":
                "INFO",
        },

        {
            "metric":
                "successful_fetches",

            "value":
                successful_fetches,

            "status":
                (
                    "PASS"
                    if successful_fetches > 0
                    else "FAIL"
                ),
        },

        {
            "metric":
                "failed_fetches",

            "value":
                failed_fetches,

            "status":
                "INFO",
        },

        {
            "metric":
                "years_with_successful_official_fetch",

            "value":
                ",".join(
                    str(
                        year
                    )
                    for year in years_with_success
                ),

            "status":
                (
                    "PASS"
                    if len(
                        years_with_success
                    ) >= 3
                    else "REVIEW"
                ),
        },

        {
            "metric":
                "local_candidate_files",

            "value":
                len(
                    local_rows
                ),

            "status":
                "INFO",
        },

        {
            "metric":
                "discovered_resource_candidates",

            "value":
                len(
                    resource_rows
                ),

            "status":
                (
                    "PASS"
                    if len(
                        resource_rows
                    ) > 0
                    else "FAIL"
                ),
        },

        {
            "metric":
                "official_host_candidates",

            "value":
                official_resource_count,

            "status":
                "INFO",
        },

        {
            "metric":
                "high_priority_candidates_score_ge_10",

            "value":
                high_priority_count,

            "status":
                "INFO",
        },

        {
            "metric":
                "structured_or_timing_candidates",

            "value":
                structured_count,

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
    # SUMMARY
    # ========================================================

    top_candidates = sorted(
        resource_rows,
        key=lambda row: (
            -int(
                row[
                    "priority_score"
                ]
            ),
            row[
                "year"
            ],
        ),
    )[:50]

    report = []

    report.append(
        "# Phase R1A — Official Action / Lane / "
        "Leaderboard Resource Discovery"
    )

    report.append("")

    report.append(
        f"Policy hash: `{policy_hash}`"
    )

    report.append("")

    report.append(
        "## Scope"
    )

    report.append("")

    report.append(
        "Discovery-only reconnaissance for official "
        "INDYCAR resources associated with Indianapolis "
        "500 Day 1 qualifying, 2020–2024."
    )

    report.append("")

    report.append(
        "No canonical data, chronology, HRRR data, "
        "model, simulator, or queue-wait estimate was modified."
    )

    report.append("")

    report.append(
        "## Fetch summary"
    )

    report.append("")

    report.append(
        f"- Seed URLs checked: `{len(fetch_rows)}`"
    )

    report.append(
        f"- Successful official fetches: `{successful_fetches}`"
    )

    report.append(
        f"- Failed seed fetches: `{failed_fetches}`"
    )

    report.append(
        f"- Years with successful official fetch: "
        f"`{years_with_success}`"
    )

    report.append("")

    report.append(
        "## Existing repository evidence"
    )

    report.append("")

    report.append(
        f"- Local candidate files: `{len(local_rows)}`"
    )

    report.append("")

    report.append(
        "## Discovered resources"
    )

    report.append("")

    report.append(
        f"- Total resource candidates: `{len(resource_rows)}`"
    )

    report.append(
        f"- Official INDYCAR-host candidates: "
        f"`{official_resource_count}`"
    )

    report.append(
        f"- High-priority candidates: `{high_priority_count}`"
    )

    report.append(
        f"- Structured/timing candidates: `{structured_count}`"
    )

    report.append("")

    report.append(
        "## Highest-priority candidates"
    )

    report.append("")

    for row in top_candidates:

        report.append(
            f"- {row['year']} | "
            f"score={row['priority_score']} | "
            f"{row['resource_type']} | "
            f"{row['discovered_url']} | "
            f"keywords={row['resource_keywords']}"
        )

    report.append("")

    report.append(
        "## Interpretation"
    )

    report.append("")

    report.append(
        "A discovered URL is only a candidate resource. "
        "It is not automatically accepted as historical evidence."
    )

    report.append("")

    report.append(
        "The next phase should manually review the highest-value "
        "official resources and only then decide whether to fetch "
        "specific PDFs, JSON feeds, reports, or archived timing assets."
    )

    report.append("")

    report.append(
        "## Final status"
    )

    report.append("")

    if (
        successful_fetches > 0
        and
        len(
            resource_rows
        ) > 0
    ):

        report.append(
            "**OFFICIAL_RESOURCE_DISCOVERY_READY_FOR_REVIEW**"
        )

    else:

        report.append(
            "**OFFICIAL_RESOURCE_DISCOVERY_REVIEW_REQUIRED**"
        )

    SUMMARY_FILE.write_text(
        "\n".join(
            report
        ),
        encoding="utf-8",
    )

    # ========================================================
    # PRINT
    # ========================================================

    print()
    print(
        "RESOURCE DISCOVERY SUMMARY"
    )
    print("-" * 100)

    print(
        "Seed URLs:",
        len(
            fetch_rows
        )
    )

    print(
        "Successful fetches:",
        successful_fetches
    )

    print(
        "Failed fetches:",
        failed_fetches
    )

    print(
        "Local candidate files:",
        len(
            local_rows
        )
    )

    print(
        "Resource candidates:",
        len(
            resource_rows
        )
    )

    print(
        "High-priority candidates:",
        high_priority_count
    )

    print(
        "Structured/timing candidates:",
        structured_count
    )

    print()
    print(
        "TOP 30 RESOURCE CANDIDATES"
    )
    print("-" * 140)

    for row in top_candidates[:30]:

        print(
            f"{row['year']} | "
            f"score={row['priority_score']:>2} | "
            f"{row['resource_type']:<24} | "
            f"{row['discovered_url']}"
        )

        if row[
            "resource_keywords"
        ]:

            print(
                "    keywords:",
                row[
                    "resource_keywords"
                ]
            )

    print()
    print(
        "QA"
    )
    print("-" * 100)

    for row in qa_rows:

        print(
            f"{row['metric']}: "
            f"{row['value']} "
            f"[{row['status']}]"
        )

    print()
    print("=" * 100)

    if (
        successful_fetches > 0
        and
        len(
            resource_rows
        ) > 0
    ):

        print(
            "FINAL STATUS: "
            "OFFICIAL_RESOURCE_DISCOVERY_READY_FOR_REVIEW"
        )

    else:

        print(
            "FINAL STATUS: "
            "OFFICIAL_RESOURCE_DISCOVERY_REVIEW_REQUIRED"
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

    print(
        "NO MODEL OR SIMULATOR WAS BUILT."
    )

    print()
    print(
        "OUTPUTS"
    )

    print(
        OFFICIAL_RESOURCE_FILE
    )

    print(
        LOCAL_EVIDENCE_FILE
    )

    print(
        FETCH_AUDIT_FILE
    )

    print(
        QA_FILE
    )

    print(
        SUMMARY_FILE
    )


if __name__ == "__main__":
    main()
