from pathlib import Path
from urllib.parse import quote, urlparse, urlunparse
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

PHASE = "R1E.6"

TARGETS = {
    2020: "5771",
    2021: "5838",
    2022: "6033",
    2023: "6202",
    2024: "6382",
}


# ============================================================
# INPUT / OUTPUT
# ============================================================

RAW_JSON_DIR = Path(
    "weather/evidence/rescue/"
    "official_day1_session_details/raw_api"
)

OUTPUT_DIR = Path(
    "weather/evidence/rescue/"
    "official_day1_session_details/reports_v2"
)

CSV_OUTPUT = Path(
    "weather/output/"
    "official_day1_session_report_download_v2.csv"
)

QA_OUTPUT = Path(
    "weather/output/"
    "official_day1_session_report_download_v2_qa.csv"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

CSV_OUTPUT.parent.mkdir(
    parents=True,
    exist_ok=True,
)


# ============================================================
# NETWORK
# ============================================================

USER_AGENT = (
    "Mozilla/5.0 "
    "(compatible; Indy500HistoricalEvidenceResearch/1.0)"
)

TIMEOUT = 30
DELAY = 0.5


# ============================================================
# HELPERS
# ============================================================

def sha256_bytes(data):

    return hashlib.sha256(
        data
    ).hexdigest()


def safe_text(value):

    if value is None:
        return ""

    return str(
        value
    ).strip()


def sanitize_filename(value):

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


def encode_path(path):

    return quote(
        path,
        safe="/()_-."
    )


def build_candidate_urls(raw_path):

    raw_path = raw_path.lstrip(
        "/"
    )

    encoded_path = encode_path(
        raw_path
    )

    return [
        (
            "HTTP_WWW_FRONTEND_STYLE",
            "http://www.imscdn.com/"
            + encoded_path,
        ),

        (
            "HTTPS_BARE_HOST",
            "https://imscdn.com/"
            + encoded_path,
        ),

        (
            "HTTPS_WWW",
            "https://www.imscdn.com/"
            + encoded_path,
        ),
    ]


def fetch(url):

    request = Request(
        url,
        headers={
            "User-Agent":
                USER_AGENT,

            "Accept":
                "application/pdf,*/*;q=0.8",

            "Referer":
                "https://www.indycar.com/",
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

                "status":
                    getattr(
                        response,
                        "status",
                        200,
                    ),

                "final_url":
                    response.geturl(),

                "content_type":
                    response.headers.get(
                        "Content-Type",
                        "",
                    ),

                "body":
                    body,

                "elapsed":
                    time.time()
                    - started,

                "error":
                    "",
            }

    except HTTPError as exc:

        return {
            "ok":
                False,

            "status":
                exc.code,

            "final_url":
                url,

            "content_type":
                "",

            "body":
                b"",

            "elapsed":
                time.time()
                - started,

            "error":
                f"HTTPError: {exc}",
        }

    except URLError as exc:

        return {
            "ok":
                False,

            "status":
                "",

            "final_url":
                url,

            "content_type":
                "",

            "body":
                b"",

            "elapsed":
                time.time()
                - started,

            "error":
                f"URLError: {exc}",
        }

    except Exception as exc:

        return {
            "ok":
                False,

            "status":
                "",

            "final_url":
                url,

            "content_type":
                "",

            "body":
                b"",

            "elapsed":
                time.time()
                - started,

            "error":
                (
                    f"{type(exc).__name__}: "
                    f"{exc}"
                ),
        }


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

    print()
    print("=" * 110)
    print(
        "R1E.6 — OFFICIAL DAY 1 "
        "SESSION REPORT DOWNLOAD V2"
    )
    print("=" * 110)

    rows = []

    total_reports = 0
    downloaded_reports = 0
    pdf_valid_reports = 0
    years_with_success = set()

    for year, session_id in (
        TARGETS.items()
    ):

        path = (
            RAW_JSON_DIR
            /
            f"{year}_{session_id}_session_details.json"
        )

        print()
        print("=" * 110)
        print(
            f"YEAR {year}"
        )
        print("=" * 110)

        print(
            "SOURCE JSON:",
            path,
        )

        if not path.exists():

            print(
                "MISSING SOURCE JSON"
            )

            continue

        detail = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

        reports = detail.get(
            "SessionReports"
        )

        if not isinstance(
            reports,
            list,
        ):

            reports = []

        print(
            "REPORT COUNT:",
            len(
                reports
            ),
        )

        for index, report in enumerate(
            reports,
            start=1,
        ):

            total_reports += 1

            document_type = safe_text(
                report.get(
                    "DocumentType"
                )
            )

            raw_url = safe_text(
                report.get(
                    "Url"
                )
            )

            document_id = safe_text(
                report.get(
                    "DocumentID"
                )
            )

            print()
            print(
                f"REPORT {index:02d}"
            )

            print(
                "TYPE:",
                document_type,
            )

            print(
                "RAW PATH:",
                raw_url,
            )

            candidates = (
                build_candidate_urls(
                    raw_url
                )
            )

            success = False

            selected_strategy = ""
            selected_url = ""
            final_url = ""
            status = ""
            content_type = ""
            byte_count = 0
            sha256 = ""
            local_path = ""
            pdf_magic = False
            error_chain = []

            for strategy, url in (
                candidates
            ):

                print(
                    "  TRY:",
                    strategy,
                )

                print(
                    "     ",
                    url,
                )

                result = fetch(
                    url
                )

                print(
                    "     STATUS:",
                    result[
                        "status"
                    ],
                )

                if not result[
                    "ok"
                ]:

                    print(
                        "     FAIL:",
                        result[
                            "error"
                        ],
                    )

                    error_chain.append(
                        (
                            strategy
                            + ": "
                            + result[
                                "error"
                            ]
                        )
                    )

                    time.sleep(
                        DELAY
                    )

                    continue

                body = result[
                    "body"
                ]

                pdf_magic = (
                    body.startswith(
                        b"%PDF-"
                    )
                )

                print(
                    "     CONTENT-TYPE:",
                    result[
                        "content_type"
                    ],
                )

                print(
                    "     BYTES:",
                    len(
                        body
                    ),
                )

                print(
                    "     PDF MAGIC:",
                    pdf_magic,
                )

                if not pdf_magic:

                    error_chain.append(
                        (
                            strategy
                            + ": "
                            + "response not PDF"
                        )
                    )

                    time.sleep(
                        DELAY
                    )

                    continue

                selected_strategy = (
                    strategy
                )

                selected_url = (
                    url
                )

                final_url = result[
                    "final_url"
                ]

                status = result[
                    "status"
                ]

                content_type = result[
                    "content_type"
                ]

                byte_count = len(
                    body
                )

                sha256 = sha256_bytes(
                    body
                )

                filename = (
                    f"{year}_"
                    f"{session_id}_"
                    f"{index:02d}_"
                    f"{sanitize_filename(document_type)}"
                    f".pdf"
                )

                destination = (
                    OUTPUT_DIR
                    / filename
                )

                destination.write_bytes(
                    body
                )

                local_path = str(
                    destination
                )

                success = True

                downloaded_reports += 1
                pdf_valid_reports += 1
                years_with_success.add(
                    year
                )

                print(
                    "     DOWNLOAD: PASS"
                )

                print(
                    "     LOCAL:",
                    local_path,
                )

                break

            rows.append(
                {
                    "year":
                        year,

                    "session_id":
                        session_id,

                    "report_index":
                        index,

                    "document_id":
                        document_id,

                    "document_type":
                        document_type,

                    "raw_path":
                        raw_url,

                    "downloaded":
                        success,

                    "selected_strategy":
                        selected_strategy,

                    "selected_url":
                        selected_url,

                    "final_url":
                        final_url,

                    "status_code":
                        status,

                    "content_type":
                        content_type,

                    "bytes":
                        byte_count,

                    "pdf_magic":
                        pdf_magic,

                    "sha256":
                        sha256,

                    "local_path":
                        local_path,

                    "errors":
                        " || ".join(
                            error_chain
                        ),
                }
            )

    # ========================================================
    # CSV
    # ========================================================

    fields = [
        "year",
        "session_id",
        "report_index",
        "document_id",
        "document_type",
        "raw_path",
        "downloaded",
        "selected_strategy",
        "selected_url",
        "final_url",
        "status_code",
        "content_type",
        "bytes",
        "pdf_magic",
        "sha256",
        "local_path",
        "errors",
    ]

    write_csv(
        CSV_OUTPUT,
        rows,
        fields,
    )

    # ========================================================
    # QA
    # ========================================================

    qa_rows = [
        {
            "metric":
                "report_inventory_expected",

            "value":
                total_reports,

            "status":
                "INFO",
        },

        {
            "metric":
                "downloaded_report_files",

            "value":
                downloaded_reports,

            "status":
                (
                    "PASS"
                    if downloaded_reports
                    > 0
                    else "REVIEW"
                ),
        },

        {
            "metric":
                "valid_pdf_magic_files",

            "value":
                pdf_valid_reports,

            "status":
                (
                    "PASS"
                    if pdf_valid_reports
                    ==
                    downloaded_reports
                    else "FAIL"
                ),
        },

        {
            "metric":
                "years_with_successful_download",

            "value":
                ",".join(
                    str(
                        y
                    )
                    for y in sorted(
                        years_with_success
                    )
                ),

            "status":
                (
                    "PASS"
                    if len(
                        years_with_success
                    )
                    == 5
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
    ]

    write_csv(
        QA_OUTPUT,
        qa_rows,
        [
            "metric",
            "value",
            "status",
        ],
    )

    # ========================================================
    # SUMMARY
    # ========================================================

    print()
    print("=" * 110)
    print(
        "SUMMARY"
    )
    print("=" * 110)

    print()
    print(
        "Total official reports:",
        total_reports,
    )

    print(
        "Downloaded PDF files:",
        downloaded_reports,
    )

    print(
        "Valid PDF magic files:",
        pdf_valid_reports,
    )

    print(
        "Years with successful download:",
        sorted(
            years_with_success
        ),
    )

    print()
    print(
        "DOWNLOAD RESULTS"
    )
    print("-" * 140)

    for row in rows:

        print(
            f"{row['year']} | "
            f"{row['document_type']:<20} | "
            f"downloaded={row['downloaded']} | "
            f"strategy={row['selected_strategy']} | "
            f"bytes={row['bytes']}"
        )

    print()
    print(
        "QA"
    )
    print("-" * 110)

    for row in qa_rows:

        print(
            f"{row['metric']}: "
            f"{row['value']} "
            f"[{row['status']}]"
        )

    print()
    print("=" * 110)

    if (
        downloaded_reports
        == total_reports
        and
        total_reports
        > 0
    ):

        print(
            "FINAL STATUS: "
            "OFFICIAL_DAY1_REPORT_DOWNLOAD_COMPLETE"
        )

    elif downloaded_reports > 0:

        print(
            "FINAL STATUS: "
            "OFFICIAL_DAY1_REPORT_DOWNLOAD_PARTIAL"
        )

    else:

        print(
            "FINAL STATUS: "
            "OFFICIAL_DAY1_REPORT_DOWNLOAD_REVIEW_REQUIRED"
        )

    print("=" * 110)

    print()
    print(
        "NO CANONICAL DATA WAS MODIFIED."
    )

    print()
    print(
        "OUTPUT:"
    )

    print(
        CSV_OUTPUT
    )

    print(
        QA_OUTPUT
    )

    print(
        OUTPUT_DIR
    )


if __name__ == "__main__":
    main()
