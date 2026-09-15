from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

import csv
import hashlib
import json
import re
import time


PHASE = "R1B"
POLICY_VERSION = "OFFICIAL_REPORT_ENDPOINT_EXTRACTION_V1"

OUTPUT_DIR = Path("weather/output")
DOWNLOAD_DIR = Path("weather/evidence/rescue/official_reports")

CANDIDATE_OUTPUT = OUTPUT_DIR / (
    "official_report_endpoint_candidates_v1.csv"
)

FETCH_OUTPUT = OUTPUT_DIR / (
    "official_report_endpoint_fetch_audit_v1.csv"
)

QA_OUTPUT = OUTPUT_DIR / (
    "official_report_endpoint_extraction_v1_qa.csv"
)

SUMMARY_OUTPUT = OUTPUT_DIR / (
    "official_report_endpoint_extraction_v1.md"
)


TARGET_DATES = {
    2020: "2020-08-15",
    2021: "2021-05-22",
    2022: "2022-05-21",
    2023: "2023-05-20",
    2024: "2024-05-18",
}


SEED_URLS = {
    2020: [
        "https://www.indycar.com/results/ntt-indycar-series/2020/104th-running-of-the-indianapolis-500/qualifications---day-1",
    ],

    2021: [
        "https://www.indycar.com/results/ntt-indycar-series/2021/105th-running-of-the-indianapolis-500/qualifications---day-1",
    ],

    2022: [
        "https://www.indycar.com/results/ntt-indycar-series/2022/106th-running-of-the-indianapolis-500/qualifications---day-1",
    ],

    2023: [
        "https://www.indycar.com/results/ntt-indycar-series/2023/107th-running-of-the-indianapolis-500/qualifications---day-1",
    ],

    2024: [
        "https://www.indycar.com/results/ntt-indycar-series/2024/108th-running-of-the-indianapolis-500/qualifications---day-1",
    ],
}


USER_AGENT = (
    "Mozilla/5.0 "
    "(compatible; Indy500HistoricalEvidenceResearch/1.0)"
)

REQUEST_TIMEOUT_SECONDS = 25
REQUEST_DELAY_SECONDS = 1.2


REPORT_TERMS = [
    "detailed report",
    "detailed reports",
    "session report",
    "session reports",
    "summary report",
    "summary reports",
    "final report",
    "final reports",
    "officiating report",
    "officiating reports",
    "timing",
    "scoring",
    "classification",
    "qualifying",
    "qualification",
    "results",
]


URL_TERMS = [
    "report",
    "reports",
    "timing",
    "scoring",
    "session",
    "result",
    "qualification",
    "qualifying",
    "classification",
    "pdf",
    "json",
    "api",
]


class AnchorParser(HTMLParser):

    def __init__(self):

        super().__init__()

        self.current_href = None
        self.current_text = []

        self.anchors = []
        self.scripts = []

    def handle_starttag(self, tag, attrs):

        attrs_dict = dict(attrs)

        if tag == "a":

            self.current_href = attrs_dict.get(
                "href"
            )

            self.current_text = []

        elif tag == "script":

            src = attrs_dict.get(
                "src"
            )

            if src:
                self.scripts.append(
                    src
                )

    def handle_data(self, data):

        if self.current_href is not None:

            cleaned = (
                data
                .strip()
            )

            if cleaned:
                self.current_text.append(
                    cleaned
                )

    def handle_endtag(self, tag):

        if (
            tag == "a"
            and
            self.current_href is not None
        ):

            text = " ".join(
                self.current_text
            ).strip()

            self.anchors.append(
                (
                    self.current_href,
                    text,
                )
            )

            self.current_href = None
            self.current_text = []


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
                    "application/pdf,"
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


def normalize_url(
    href,
    base_url,
):

    if not href:
        return None

    href = (
        str(href)
        .strip()
    )

    if href.startswith(
        (
            "#",
            "javascript:",
            "mailto:",
            "tel:",
        )
    ):
        return None

    try:

        return urljoin(
            base_url,
            href,
        )

    except Exception:

        return None


def official_host(url):

    host = (
        urlparse(url)
        .hostname
        or ""
    ).lower()

    return (
        host == "indycar.com"
        or
        host.endswith(
            ".indycar.com"
        )
    )


def relevant_anchor(
    text,
    url,
):

    combined = (
        str(text)
        + " "
        + str(url)
    ).lower()

    return any(
        term in combined
        for term in (
            REPORT_TERMS
            +
            URL_TERMS
        )
    )


def classify_candidate(
    text,
    url,
):

    lower = (
        str(text)
        + " "
        + str(url)
    ).lower()

    if ".pdf" in lower:
        return "PDF"

    if ".json" in lower:
        return "JSON"

    if "api" in lower:
        return "API_CANDIDATE"

    if (
        "detailed report"
        in lower
        or
        "detail-report"
        in lower
        or
        "detail_reports"
        in lower
    ):
        return "DETAILED_REPORT"

    if "session report" in lower:
        return "SESSION_REPORT"

    if "summary report" in lower:
        return "SUMMARY_REPORT"

    if "officiating" in lower:
        return "OFFICIATING_REPORT"

    if "timing" in lower:
        return "TIMING_CANDIDATE"

    if "scoring" in lower:
        return "SCORING_CANDIDATE"

    if "classification" in lower:
        return "CLASSIFICATION_CANDIDATE"

    if "result" in lower:
        return "RESULTS_CANDIDATE"

    return "OTHER_RELEVANT"


def score_candidate(
    text,
    url,
    candidate_type,
):

    combined = (
        str(text)
        + " "
        + str(url)
    ).lower()

    score = 0

    weights = {
        "detailed report":
            8,

        "session report":
            8,

        "timing":
            8,

        "scoring":
            8,

        "classification":
            6,

        ".pdf":
            7,

        ".json":
            8,

        "api":
            7,

        "qualifying":
            3,

        "qualification":
            3,

        "officiating":
            4,

        "summary report":
            3,

        "result":
            2,
    }

    for term, weight in (
        weights.items()
    ):

        if term in combined:
            score += weight

    if candidate_type in {
        "PDF",
        "JSON",
        "API_CANDIDATE",
        "DETAILED_REPORT",
        "SESSION_REPORT",
        "TIMING_CANDIDATE",
        "SCORING_CANDIDATE",
    }:
        score += 5

    return score


def safe_filename(
    year,
    index,
    url,
    content_type,
):

    parsed = urlparse(
        url
    )

    name = Path(
        parsed.path
    ).name

    if not name:

        name = (
            f"resource_{index}"
        )

    name = re.sub(
        r"[^A-Za-z0-9._-]+",
        "_",
        name,
    )

    lower_ct = (
        content_type
        .lower()
    )

    if (
        "pdf"
        in lower_ct
        and
        not name.lower().endswith(
            ".pdf"
        )
    ):
        name += ".pdf"

    elif (
        "json"
        in lower_ct
        and
        not name.lower().endswith(
            ".json"
        )
    ):
        name += ".json"

    elif (
        "html"
        in lower_ct
        and
        not name.lower().endswith(
            (
                ".html",
                ".htm",
            )
        )
    ):
        name += ".html"

    return (
        f"{year}_{index:03d}_{name}"
    )


def main():

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    DOWNLOAD_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print()
    print("=" * 100)
    print(
        "PHASE R1B — OFFICIAL REPORT "
        "ENDPOINT EXTRACTION V1"
    )
    print("=" * 100)

    candidate_rows = []
    seed_fetch_rows = []

    # ========================================================
    # EXTRACT REAL ANCHORS
    # ========================================================

    for year, urls in (
        SEED_URLS.items()
    ):

        for seed_url in urls:

            print()
            print(
                f"FETCHING SEED: "
                f"{year} {seed_url}"
            )

            result = fetch_url(
                seed_url
            )

            seed_fetch_rows.append(
                {
                    "year":
                        year,

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

            parser = AnchorParser()

            parser.feed(
                html
            )

            seen = set()

            for href, anchor_text in (
                parser.anchors
            ):

                url = normalize_url(
                    href,
                    result[
                        "final_url"
                    ],
                )

                if not url:
                    continue

                if not relevant_anchor(
                    anchor_text,
                    url,
                ):
                    continue

                key = (
                    url,
                    anchor_text,
                )

                if key in seen:
                    continue

                seen.add(
                    key
                )

                candidate_type = (
                    classify_candidate(
                        anchor_text,
                        url,
                    )
                )

                score = score_candidate(
                    anchor_text,
                    url,
                    candidate_type,
                )

                candidate_rows.append(
                    {
                        "year":
                            year,

                        "session_date":
                            TARGET_DATES[
                                year
                            ],

                        "seed_url":
                            seed_url,

                        "anchor_text":
                            anchor_text,

                        "candidate_url":
                            url,

                        "host":
                            (
                                urlparse(url)
                                .hostname
                                or ""
                            ),

                        "official_indycar_host":
                            official_host(
                                url
                            ),

                        "candidate_type":
                            candidate_type,

                        "priority_score":
                            score,

                        "manual_review_status":
                            "UNREVIEWED",
                    }
                )

            time.sleep(
                REQUEST_DELAY_SECONDS
            )

    # ========================================================
    # DEDUP
    # ========================================================

    dedup = {}

    for row in candidate_rows:

        key = (
            row[
                "year"
            ],
            row[
                "candidate_url"
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

    candidate_rows = list(
        dedup.values()
    )

    candidate_rows.sort(
        key=lambda row: (
            row[
                "year"
            ],
            -row[
                "priority_score"
            ],
            row[
                "candidate_url"
            ],
        )
    )

    # ========================================================
    # FETCH HIGH-VALUE CANDIDATES
    # ========================================================

    endpoint_fetch_rows = []

    fetchable = [
        row
        for row in candidate_rows
        if (
            row[
                "official_indycar_host"
            ]
            and
            row[
                "priority_score"
            ]
            >= 8
        )
    ]

    print()
    print(
        "HIGH-VALUE ENDPOINTS TO FETCH:",
        len(
            fetchable
        )
    )

    for index, row in enumerate(
        fetchable,
        start=1,
    ):

        print(
            f"[{index}/{len(fetchable)}] "
            f"{row['year']} "
            f"{row['candidate_type']} "
            f"{row['candidate_url']}"
        )

        result = fetch_url(
            row[
                "candidate_url"
            ]
        )

        local_path = ""

        if result[
            "ok"
        ]:

            filename = safe_filename(
                year=row[
                    "year"
                ],
                index=index,
                url=result[
                    "final_url"
                ],
                content_type=result[
                    "content_type"
                ],
            )

            destination = (
                DOWNLOAD_DIR
                /
                filename
            )

            destination.write_bytes(
                result[
                    "body"
                ]
            )

            local_path = str(
                destination
            )

        endpoint_fetch_rows.append(
            {
                "year":
                    row[
                        "year"
                    ],

                "candidate_type":
                    row[
                        "candidate_type"
                    ],

                "priority_score":
                    row[
                        "priority_score"
                    ],

                "anchor_text":
                    row[
                        "anchor_text"
                    ],

                "requested_url":
                    row[
                        "candidate_url"
                    ],

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
                        hashlib.sha256(
                            result[
                                "body"
                            ]
                        ).hexdigest()
                        if result[
                            "body"
                        ]
                        else ""
                    ),

                "local_path":
                    local_path,

                "error":
                    result[
                        "error"
                    ],
            }
        )

        time.sleep(
            REQUEST_DELAY_SECONDS
        )

    # ========================================================
    # WRITE OUTPUTS
    # ========================================================

    candidate_fields = [
        "year",
        "session_date",
        "seed_url",
        "anchor_text",
        "candidate_url",
        "host",
        "official_indycar_host",
        "candidate_type",
        "priority_score",
        "manual_review_status",
    ]

    with CANDIDATE_OUTPUT.open(
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as handle:

        writer = csv.DictWriter(
            handle,
            fieldnames=candidate_fields,
        )

        writer.writeheader()

        writer.writerows(
            candidate_rows
        )

    fetch_fields = [
        "year",
        "candidate_type",
        "priority_score",
        "anchor_text",
        "requested_url",
        "ok",
        "status_code",
        "final_url",
        "content_type",
        "bytes",
        "sha256",
        "local_path",
        "error",
    ]

    with FETCH_OUTPUT.open(
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
            endpoint_fetch_rows
        )

    # ========================================================
    # QA
    # ========================================================

    successful_seed_fetches = sum(
        1
        for row in seed_fetch_rows
        if row[
            "ok"
        ]
    )

    successful_endpoint_fetches = sum(
        1
        for row in endpoint_fetch_rows
        if row[
            "ok"
        ]
    )

    downloaded_files = sum(
        1
        for row in endpoint_fetch_rows
        if row[
            "local_path"
        ]
    )

    candidate_types = sorted(
        {
            row[
                "candidate_type"
            ]
            for row in candidate_rows
        }
    )

    years_with_candidates = sorted(
        {
            row[
                "year"
            ]
            for row in candidate_rows
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

        "download_directory":
            str(
                DOWNLOAD_DIR
            ),

        "canonical_mutation":
            False,

        "discovery_then_fetch":
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
                    seed_fetch_rows
                ),

            "status":
                (
                    "PASS"
                    if len(
                        seed_fetch_rows
                    )
                    == 5
                    else "FAIL"
                ),
        },

        {
            "metric":
                "all_seed_pages_fetch_success",

            "value":
                successful_seed_fetches,

            "status":
                (
                    "PASS"
                    if successful_seed_fetches
                    == 5
                    else "FAIL"
                ),
        },

        {
            "metric":
                "candidate_rows",

            "value":
                len(
                    candidate_rows
                ),

            "status":
                (
                    "PASS"
                    if len(
                        candidate_rows
                    )
                    > 0
                    else "FAIL"
                ),
        },

        {
            "metric":
                "years_with_candidates",

            "value":
                ",".join(
                    str(
                        year
                    )
                    for year in years_with_candidates
                ),

            "status":
                (
                    "PASS"
                    if set(
                        years_with_candidates
                    )
                    == set(
                        TARGET_DATES.keys()
                    )
                    else "REVIEW"
                ),
        },

        {
            "metric":
                "high_value_endpoint_fetches_attempted",

            "value":
                len(
                    endpoint_fetch_rows
                ),

            "status":
                "INFO",
        },

        {
            "metric":
                "successful_endpoint_fetches",

            "value":
                successful_endpoint_fetches,

            "status":
                (
                    "PASS"
                    if successful_endpoint_fetches
                    > 0
                    else "REVIEW"
                ),
        },

        {
            "metric":
                "downloaded_files",

            "value":
                downloaded_files,

            "status":
                "INFO",
        },

        {
            "metric":
                "candidate_types",

            "value":
                ";".join(
                    candidate_types
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
                "policy_hash",

            "value":
                policy_hash,

            "status":
                "INFO",
        },
    ]

    with QA_OUTPUT.open(
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

    report = []

    report.append(
        "# Phase R1B — Official Report Endpoint Extraction"
    )

    report.append("")

    report.append(
        f"Policy hash: `{policy_hash}`"
    )

    report.append("")

    report.append(
        "## Result"
    )

    report.append("")

    report.append(
        f"- Candidate endpoints: `{len(candidate_rows)}`"
    )

    report.append(
        f"- High-value fetches attempted: `{len(endpoint_fetch_rows)}`"
    )

    report.append(
        f"- Successful endpoint fetches: `{successful_endpoint_fetches}`"
    )

    report.append(
        f"- Downloaded evidence files: `{downloaded_files}`"
    )

    report.append(
        f"- Years represented: `{years_with_candidates}`"
    )

    report.append("")

    report.append(
        "## Important boundary"
    )

    report.append("")

    report.append(
        "Downloaded files are evidence candidates only. "
        "No historical action, queue, lane, timing, or leaderboard "
        "fact is accepted automatically."
    )

    report.append("")

    report.append(
        "No canonical dataset was modified."
    )

    SUMMARY_OUTPUT.write_text(
        "\n".join(
            report
        ),
        encoding="utf-8",
    )

    # ========================================================
    # PRINT
    # ========================================================

    print()
    print("REAL REPORT/LINK CANDIDATES")
    print("-" * 160)

    for row in candidate_rows[:80]:

        print(
            f"{row['year']} | "
            f"score={row['priority_score']:>2} | "
            f"{row['candidate_type']:<25} | "
            f"{row['anchor_text'][:55]:<55} | "
            f"{row['candidate_url']}"
        )

    print()
    print("ENDPOINT FETCH SUMMARY")
    print("-" * 120)

    print(
        "Candidate endpoints:",
        len(
            candidate_rows
        )
    )

    print(
        "High-value fetches attempted:",
        len(
            endpoint_fetch_rows
        )
    )

    print(
        "Successful endpoint fetches:",
        successful_endpoint_fetches
    )

    print(
        "Downloaded files:",
        downloaded_files
    )

    print()
    print("DOWNLOADED HIGH-VALUE FILES")
    print("-" * 160)

    for row in endpoint_fetch_rows:

        if not row[
            "local_path"
        ]:
            continue

        print(
            f"{row['year']} | "
            f"{row['candidate_type']:<25} | "
            f"{row['content_type']:<35} | "
            f"{row['local_path']}"
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
        successful_seed_fetches
        == 5
        and
        len(
            candidate_rows
        )
        > 0
    ):

        print(
            "FINAL STATUS: "
            "OFFICIAL_REPORT_ENDPOINTS_READY_FOR_CONTENT_AUDIT"
        )

    else:

        print(
            "FINAL STATUS: "
            "OFFICIAL_REPORT_ENDPOINTS_REVIEW_REQUIRED"
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
    print("OUTPUTS")

    print(
        CANDIDATE_OUTPUT
    )

    print(
        FETCH_OUTPUT
    )

    print(
        QA_OUTPUT
    )

    print(
        SUMMARY_OUTPUT
    )

    print(
        DOWNLOAD_DIR
    )


if __name__ == "__main__":
    main()
