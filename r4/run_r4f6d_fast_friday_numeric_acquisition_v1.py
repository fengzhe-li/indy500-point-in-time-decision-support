from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
import csv
import json
import time

ROOT = Path(
    "/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈"
)

OUT = ROOT / "r4/output"
RAW = ROOT / "r4/evidence/fast_friday"

OUT.mkdir(parents=True, exist_ok=True)
RAW.mkdir(parents=True, exist_ok=True)

OUT_MANIFEST = (
    OUT /
    "r4f6d_fast_friday_numeric_acquisition_manifest_v1.csv"
)

OUT_QA = (
    OUT /
    "r4f6d_fast_friday_numeric_acquisition_qa_v1.csv"
)

OUT_REPORT = (
    OUT /
    "r4f6d_fast_friday_numeric_acquisition_report_v1.json"
)


SOURCES = [
    {
        "year": 2020,
        "session": "Practice 3 (Fast Friday)",
        "source_type": "OFFICIAL_RESULTS_HTML",
        "url":
            "https://www.indycar.com/results/ntt-indycar-series/"
            "2020/104th-running-of-the-indianapolis-500/practice-3",
        "filename":
            "2020_fast_friday_practice3_results.html",
        "reference_role":
            "GENERAL_FAST_FRIDAY_NUMERIC_REFERENCE",
    },

    {
        "year": 2021,
        "session": "Practice 5 (Fast Friday)",
        "source_type": "OFFICIAL_RESULTS_HTML",
        "url":
            "https://www.indycar.com/results/ntt-indycar-series/"
            "2021/105th-running-of-the-indianapolis-500/practice-5",
        "filename":
            "2021_fast_friday_practice5_results.html",
        "reference_role":
            "FAST_FRIDAY_SESSION_REFERENCE",
    },

    {
        "year": 2021,
        "session": "Fast Friday Editorial",
        "source_type": "OFFICIAL_EDITORIAL_HTML",
        "url":
            "https://www.indycar.com/News/2021/05/05-21-Practice",
        "filename":
            "2021_fast_friday_official_editorial.html",
        "reference_role":
            "NO_TOW_REFERENCE_EVIDENCE",
    },

    {
        "year": 2022,
        "session": "Practice 5 (Fast Friday)",
        "source_type": "OFFICIAL_RESULTS_HTML",
        "url":
            "https://www.indycar.com/results/ntt-indycar-series/"
            "2022/106th-running-of-the-indianapolis-500/practice-5",
        "filename":
            "2022_fast_friday_practice5_results.html",
        "reference_role":
            "GENERAL_FAST_FRIDAY_NUMERIC_REFERENCE",
    },

    {
        "year": 2023,
        "session": "Practice 5 (Fast Friday)",
        "source_type": "OFFICIAL_RESULTS_HTML",
        "url":
            "https://www.indycar.com/results/ntt-indycar-series/"
            "2023/107th-running-of-the-indianapolis-500/practice-5",
        "filename":
            "2023_fast_friday_practice5_results.html",
        "reference_role":
            "FAST_FRIDAY_SESSION_REFERENCE",
    },

    {
        "year": 2023,
        "session": "Practice 5 (Fast Friday)",
        "source_type": "OFFICIAL_RESULTS_PDF",
        "url":
            "https://www.imscdn.com/INDYCAR/Documents/6200/"
            "2023-05-19/indycar-results-p5.pdf",
        "filename":
            "2023_fast_friday_practice5_results.pdf",
        "reference_role":
            "FOUR_LAP_QUALIFYING_SIM_HIGH_PRIORITY",
    },

    {
        "year": 2023,
        "session": "Fast Friday Editorial",
        "source_type": "OFFICIAL_EDITORIAL_HTML",
        "url":
            "https://www.indycar.com/news/2023/05/05-19-fastfriday",
        "filename":
            "2023_fast_friday_official_editorial.html",
        "reference_role":
            "FOUR_LAP_SIM_CONTEXT_EVIDENCE",
    },

    {
        "year": 2024,
        "session": "Practice 5 (Fast Friday)",
        "source_type": "OFFICIAL_RESULTS_HTML",
        "url":
            "https://www.indycar.com/results/ntt-indycar-series/"
            "2024/108th-running-of-the-indianapolis-500/practice-5",
        "filename":
            "2024_fast_friday_practice5_results.html",
        "reference_role":
            "VALIDATION_FAST_FRIDAY_SESSION_REFERENCE",
    },

    {
        "year": 2024,
        "session": "Practice 5 (Fast Friday)",
        "source_type": "OFFICIAL_RESULTS_PDF",
        "url":
            "https://www.imscdn.com/INDYCAR/Documents/6380/"
            "2024-05-17/indycar-results-p5.pdf",
        "filename":
            "2024_fast_friday_practice5_results.pdf",
        "reference_role":
            "VALIDATION_FOUR_LAP_QUALIFYING_SIM",
    },

    {
        "year": 2024,
        "session": "Fast Friday Editorial",
        "source_type": "OFFICIAL_EDITORIAL_HTML",
        "url":
            "https://www.indycar.com/News/2024/05/"
            "05-17-FastFriday-Report",
        "filename":
            "2024_fast_friday_official_editorial.html",
        "reference_role":
            "VALIDATION_FOUR_LAP_SIM_CONTEXT",
    },
]


def download(url, target):
    req = Request(
        url,
        headers={
            "User-Agent":
                "Mozilla/5.0 "
                "(Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 Chrome/153 Safari/537.36"
        },
    )

    try:
        with urlopen(
            req,
            timeout=30,
        ) as response:

            data = response.read()

            content_type = (
                response.headers.get(
                    "Content-Type",
                    ""
                )
            )

            status = getattr(
                response,
                "status",
                200,
            )

        target.write_bytes(
            data
        )

        return {
            "status":
                "DOWNLOADED",

            "http_status":
                status,

            "bytes":
                len(
                    data
                ),

            "content_type":
                content_type,

            "error":
                "",
        }

    except HTTPError as e:

        return {
            "status":
                "HTTP_ERROR",

            "http_status":
                e.code,

            "bytes":
                0,

            "content_type":
                "",

            "error":
                str(
                    e
                ),
        }

    except URLError as e:

        return {
            "status":
                "URL_ERROR",

            "http_status":
                "",

            "bytes":
                0,

            "content_type":
                "",

            "error":
                str(
                    e
                ),
        }

    except Exception as e:

        return {
            "status":
                "ERROR",

            "http_status":
                "",

            "bytes":
                0,

            "content_type":
                "",

            "error":
                repr(
                    e
                ),
        }


manifest = []

print("=" * 126)
print("R4F6D — FAST FRIDAY DRIVER-LEVEL NUMERIC ACQUISITION")
print("=" * 126)

for i, source in enumerate(
    SOURCES,
    start=1,
):

    target = RAW / source[
        "filename"
    ]

    print()
    print(
        f"[{i}/{len(SOURCES)}] "
        f"{source['year']} | "
        f"{source['source_type']}"
    )

    print(
        source[
            "url"
        ]
    )

    result = download(
        source[
            "url"
        ],
        target,
    )

    print(
        f"status={result['status']} | "
        f"http={result['http_status']} | "
        f"bytes={result['bytes']}"
    )

    manifest.append({
        "year":
            source[
                "year"
            ],

        "session":
            source[
                "session"
            ],

        "source_type":
            source[
                "source_type"
            ],

        "reference_role":
            source[
                "reference_role"
            ],

        "url":
            source[
                "url"
            ],

        "local_file":
            str(
                target.relative_to(
                    ROOT
                )
            ),

        "download_status":
            result[
                "status"
            ],

        "http_status":
            result[
                "http_status"
            ],

        "bytes":
            result[
                "bytes"
            ],

        "content_type":
            result[
                "content_type"
            ],

        "error":
            result[
                "error"
            ],
    })

    time.sleep(
        0.5
    )


with OUT_MANIFEST.open(
    "w",
    encoding="utf-8",
    newline="",
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=list(
            manifest[0].keys()
        )
    )

    writer.writeheader()
    writer.writerows(
        manifest
    )


downloaded = [
    r
    for r in manifest
    if r[
        "download_status"
    ] == "DOWNLOADED"
]


by_year = {}

for year in [
    2020,
    2021,
    2022,
    2023,
    2024,
]:

    rows = [
        r
        for r in manifest
        if r[
            "year"
        ] == year
    ]

    ok = [
        r
        for r in rows
        if r[
            "download_status"
        ] == "DOWNLOADED"
    ]

    by_year[
        year
    ] = {
        "sources":
            len(
                rows
            ),

        "downloaded":
            len(
                ok
            ),

        "pdf_downloaded":
            sum(
                r[
                    "source_type"
                ]
                ==
                "OFFICIAL_RESULTS_PDF"
                and
                r[
                    "download_status"
                ]
                ==
                "DOWNLOADED"
                for r in rows
            ),

        "html_downloaded":
            sum(
                r[
                    "source_type"
                ].endswith(
                    "HTML"
                )
                and
                r[
                    "download_status"
                ]
                ==
                "DOWNLOADED"
                for r in rows
            ),
    }


qa_rows = [
    {
        "metric":
            "manifest_sources",

        "value":
            len(
                manifest
            ),

        "expected":
            10,

        "status":
            (
                "PASS"
                if len(
                    manifest
                ) == 10
                else "FAIL"
            ),
    },

    {
        "metric":
            "at_least_one_source_downloaded",

        "value":
            len(
                downloaded
            ),

        "expected":
            ">0",

        "status":
            (
                "PASS"
                if downloaded
                else "FAIL"
            ),
    },

    {
        "metric":
            "2024_preserved_as_validation",

        "value":
            all(
                (
                    r[
                        "year"
                    ] != 2024
                    or
                    "VALIDATION"
                    in r[
                        "reference_role"
                    ]
                )
                for r in manifest
            ),

        "expected":
            True,

        "status":
            (
                "PASS"
                if all(
                    (
                        r[
                            "year"
                        ] != 2024
                        or
                        "VALIDATION"
                        in r[
                            "reference_role"
                        ]
                    )
                    for r in manifest
                )
                else "FAIL"
            ),
    },

    {
        "metric":
            "raw_acquisition_only_no_model_fit",

        "value":
            True,

        "expected":
            True,

        "status":
            "PASS",
    },
]


with OUT_QA.open(
    "w",
    encoding="utf-8",
    newline="",
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=[
            "metric",
            "value",
            "expected",
            "status",
        ]
    )

    writer.writeheader()
    writer.writerows(
        qa_rows
    )


report = {
    "phase":
        "R4F6D",

    "status":
        "R4F6D_FAST_FRIDAY_NUMERIC_ACQUISITION_COMPLETE",

    "sources_attempted":
        len(
            manifest
        ),

    "sources_downloaded":
        len(
            downloaded
        ),

    "year_status":
        by_year,

    "reference_hierarchy": [
        "FOUR_LAP_QUALIFYING_SIM",
        "NO_TOW_SINGLE_LAP",
        "GENERAL_FAST_FRIDAY_BEST_SPEED",
    ],

    "important_constraint":
        (
            "Acquisition does not imply semantic usability. "
            "Downloaded assets must be parsed and classified "
            "before entry-reference construction."
        ),

    "next_phase":
        (
            "Inspect downloaded HTML/PDF assets and extract "
            "driver-level qualifying-like Fast Friday metrics "
            "into a canonical reference panel."
        ),
}


OUT_REPORT.write_text(
    json.dumps(
        report,
        indent=2,
        ensure_ascii=False,
    ),
    encoding="utf-8",
)


print()
print("=" * 126)
print("DOWNLOAD SUMMARY")
print("=" * 126)

print(
    f"Sources attempted: "
    f"{len(manifest)}"
)

print(
    f"Downloaded: "
    f"{len(downloaded)}"
)

print()
print("YEAR STATUS")

for year in sorted(
    by_year
):

    r = by_year[
        year
    ]

    print(
        f"{year} | "
        f"sources={r['sources']} | "
        f"downloaded={r['downloaded']} | "
        f"html={r['html_downloaded']} | "
        f"pdf={r['pdf_downloaded']}"
    )


print()
print("=" * 126)
print("FAILED SOURCES")
print("=" * 126)

failed = [
    r
    for r in manifest
    if r[
        "download_status"
    ]
    !=
    "DOWNLOADED"
]

if not failed:

    print(
        "NONE"
    )

else:

    for r in failed:

        print(
            f"{r['year']} | "
            f"{r['source_type']} | "
            f"{r['download_status']} | "
            f"{r['error']}"
        )

        print(
            f"    {r['url']}"
        )


fails = [
    r
    for r in qa_rows
    if r[
        "status"
    ] == "FAIL"
]

print()
print(
    f"QA: "
    f"{len(qa_rows)-len(fails)}/"
    f"{len(qa_rows)} PASS"
)

if fails:
    raise SystemExit(1)


print()
print("OUTPUTS")
print(
    OUT_MANIFEST.relative_to(ROOT)
)
print(
    OUT_QA.relative_to(ROOT)
)
print(
    OUT_REPORT.relative_to(ROOT)
)

print()
print(
    "R4F6D_FAST_FRIDAY_NUMERIC_ACQUISITION_COMPLETE"
)
