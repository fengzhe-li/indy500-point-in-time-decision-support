from pathlib import Path
import csv
import json
import urllib.request
import urllib.parse

ROOT = Path(
    "/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈"
)

OUT = ROOT / "r4/output"
OUT.mkdir(parents=True, exist_ok=True)

EVIDENCE = (
    ROOT /
    "weather/evidence/last_chance_official"
)

REPORT_DIR = (
    EVIDENCE /
    "session_reports"
)
REPORT_DIR.mkdir(
    parents=True,
    exist_ok=True
)

SESSIONS = {
    2021: 5847,
    2023: 6205,
    2024: 6385,
}

OUT_RECORDS = (
    OUT /
    "r4lc3_last_chance_official_records_v1.csv"
)

OUT_FIELDS = (
    OUT /
    "r4lc3_last_chance_record_field_inventory_v1.csv"
)

OUT_REPORTS = (
    OUT /
    "r4lc3_last_chance_session_reports_v1.csv"
)

OUT_QA = (
    OUT /
    "r4lc3_last_chance_ingestion_qa_v1.csv"
)

OUT_SUMMARY = (
    OUT /
    "r4lc3_last_chance_ingestion_report_v1.json"
)


def fetch(url):
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

            return {
                "status":
                    response.status,

                "content_type":
                    response.headers.get(
                        "Content-Type",
                        ""
                    ),

                "body":
                    body,

                "final_url":
                    response.geturl(),

                "error":
                    "",
            }

    except Exception as exc:

        return {
            "status":
                None,

            "content_type":
                "",

            "body":
                b"",

            "final_url":
                "",

            "error":
                repr(exc),
        }


def fetch_json(url):
    result = fetch(
        url
    )

    data = None

    if result["body"]:

        try:
            data = json.loads(
                result["body"].decode(
                    "utf-8",
                    errors="ignore"
                )
            )
        except Exception:
            pass

    result["json"] = data

    return result


def clean(v):
    if v is None:
        return ""

    if isinstance(
        v,
        (dict, list)
    ):
        return json.dumps(
            v,
            ensure_ascii=False,
            default=str
        )

    return str(v).strip()


def candidate_report_urls(relative_url):

    rel = (
        relative_url
        .strip()
        .lstrip("/")
    )

    return [
        (
            "https://www.indycar.com/-/media/Files/"
            + rel
        ),
        (
            "https://www.indycar.com/-/media/"
            + rel
        ),
        (
            "https://www.indycar.com/"
            + rel
        ),
    ]


print("=" * 118)
print("R4LC3 — OFFICIAL LAST CHANCE RECORD + REPORT INGESTION")
print("=" * 118)

record_rows = []
field_rows = []
report_rows = []
qa_rows = []


for year, session_id in SESSIONS.items():

    print()
    print("=" * 118)
    print(
        f"YEAR {year} | SESSION {session_id}"
    )
    print("=" * 118)

    params = urllib.parse.urlencode({
        "id":
            session_id
    })

    api_url = (
        "https://www.indycar.com"
        "/api/results/EventsSessionDetails?"
        + params
    )

    response = fetch_json(
        api_url
    )

    data = response[
        "json"
    ]

    print(
        f"API HTTP={response['status']} | "
        f"bytes={len(response['body'])} | "
        f"json={isinstance(data, dict)}"
    )

    qa_rows.append({
        "metric":
            f"{year}_session_json",

        "value":
            isinstance(
                data,
                dict
            ),

        "expected":
            True,

        "status":
            (
                "PASS"
                if isinstance(
                    data,
                    dict
                )
                else "FAIL"
            ),
    })

    if not isinstance(
        data,
        dict
    ):
        continue


    # =========================================================================
    # 1. Records
    # =========================================================================

    records = data.get(
        "records",
        []
    )

    if not isinstance(
        records,
        list
    ):
        records = []

    print()
    print(
        f"RECORD COUNT: {len(records)}"
    )

    all_fields = sorted(
        {
            key
            for record in records
            if isinstance(
                record,
                dict
            )
            for key in record.keys()
        }
    )

    print()
    print("RECORD FIELD INVENTORY")

    for field in all_fields:
        print(
            f"  {field}"
        )

        nonempty = sum(
            1
            for r in records
            if (
                isinstance(
                    r,
                    dict
                )
                and r.get(field)
                not in [
                    None,
                    "",
                    [],
                    {},
                ]
            )
        )

        field_rows.append({
            "year":
                year,

            "session_id":
                session_id,

            "field":
                field,

            "nonempty_rows":
                nonempty,

            "total_rows":
                len(records),
        })


    print()
    print("FULL RECORD ROWS")

    for idx, record in enumerate(
        records,
        start=1
    ):

        if not isinstance(
            record,
            dict
        ):
            continue

        car = clean(
            record.get(
                "CarNumber"
            )
        )

        first = clean(
            record.get(
                "FirstName"
            )
        )

        last = clean(
            record.get(
                "LastName"
            )
        )

        driver = (
            f"{first} {last}"
        ).strip()

        speed = clean(
            record.get(
                "SpeedAvg"
            )
        )

        finish = clean(
            record.get(
                "PositionFinish"
            )
        )

        elapsed = clean(
            record.get(
                "ElapsedTime"
            )
        )

        print()
        print(
            f"ROW {idx} | "
            f"car={car or '-'} | "
            f"driver={driver or '-'} | "
            f"finish={finish or '-'} | "
            f"speed={speed or '-'} | "
            f"elapsed={elapsed or '-'}"
        )

        print(
            json.dumps(
                record,
                indent=2,
                ensure_ascii=False,
                default=str
            )
        )

        flat = {
            "year":
                year,

            "session_id":
                session_id,

            "record_index":
                idx,
        }

        for key, value in record.items():

            flat[
                key
            ] = clean(
                value
            )

        record_rows.append(
            flat
        )


    qa_rows.append({
        "metric":
            f"{year}_records_nonempty",

        "value":
            len(records),

        "expected":
            ">0",

        "status":
            (
                "PASS"
                if records
                else "FAIL"
            ),
    })


    # =========================================================================
    # 2. Session Reports
    # =========================================================================

    reports = data.get(
        "SessionReports",
        []
    )

    if not isinstance(
        reports,
        list
    ):
        reports = []

    print()
    print(
        f"SESSION REPORT COUNT: "
        f"{len(reports)}"
    )

    for idx, report in enumerate(
        reports,
        start=1
    ):

        if not isinstance(
            report,
            dict
        ):
            continue

        name = clean(
            report.get(
                "Name"
            )
        )

        doc_type = clean(
            report.get(
                "DocumentType"
            )
        )

        rel_url = clean(
            report.get(
                "Url"
            )
        )

        document_id = clean(
            report.get(
                "DocumentID"
            )
        )

        print()
        print(
            f"REPORT {idx} | "
            f"name={name} | "
            f"type={doc_type}"
        )

        print(
            json.dumps(
                report,
                indent=2,
                ensure_ascii=False,
                default=str
            )
        )

        download_status = None
        download_url = ""
        final_url = ""
        saved_path = ""
        download_bytes = 0
        error = ""

        if rel_url:

            for candidate in candidate_report_urls(
                rel_url
            ):

                result = fetch(
                    candidate
                )

                content_type = (
                    result[
                        "content_type"
                    ].lower()
                )

                looks_pdf = (
                    result[
                        "body"
                    ].startswith(
                        b"%PDF"
                    )
                    or
                    "application/pdf"
                    in content_type
                )

                if (
                    result["status"] == 200
                    and looks_pdf
                ):

                    download_status = 200
                    download_url = candidate
                    final_url = (
                        result[
                            "final_url"
                        ]
                    )

                    download_bytes = len(
                        result[
                            "body"
                        ]
                    )

                    safe_name = (
                        f"{year}_"
                        f"{session_id}_"
                        f"{idx}_"
                        f"{doc_type or name or 'report'}"
                        ".pdf"
                    )

                    safe_name = (
                        safe_name
                        .replace(
                            " ",
                            "_"
                        )
                        .replace(
                            "/",
                            "_"
                        )
                    )

                    path = (
                        REPORT_DIR /
                        safe_name
                    )

                    path.write_bytes(
                        result[
                            "body"
                        ]
                    )

                    saved_path = str(
                        path.relative_to(
                            ROOT
                        )
                    )

                    break

                error = (
                    result[
                        "error"
                    ]
                    or
                    f"HTTP={result['status']} "
                    f"type={result['content_type']} "
                    f"bytes={len(result['body'])}"
                )


        report_rows.append({
            "year":
                year,

            "session_id":
                session_id,

            "report_index":
                idx,

            "document_id":
                document_id,

            "name":
                name,

            "document_type":
                doc_type,

            "relative_url":
                rel_url,

            "download_status":
                download_status,

            "download_url":
                download_url,

            "final_url":
                final_url,

            "download_bytes":
                download_bytes,

            "saved_path":
                saved_path,

            "error":
                error,
        })


    if reports:

        downloaded = sum(
            1
            for r in report_rows
            if (
                r["year"] == year
                and r[
                    "download_status"
                ] == 200
            )
        )

        qa_rows.append({
            "metric":
                f"{year}_report_downloads",

            "value":
                downloaded,

            "expected":
                f">0 of {len(reports)}",

            "status":
                (
                    "PASS"
                    if downloaded > 0
                    else "WARN"
                ),
        })

    else:

        qa_rows.append({
            "metric":
                f"{year}_session_reports_available",

            "value":
                0,

            "expected":
                "0 allowed",

            "status":
                "PASS",
        })


# =============================================================================
# 3. Dynamic record-column union
# =============================================================================

record_field_union = sorted(
    {
        key
        for row in record_rows
        for key in row.keys()
    }
)

with OUT_RECORDS.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=record_field_union,
        extrasaction="ignore"
    )

    writer.writeheader()
    writer.writerows(
        record_rows
    )


with OUT_FIELDS.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    fields = [
        "year",
        "session_id",
        "field",
        "nonempty_rows",
        "total_rows",
    ]

    writer = csv.DictWriter(
        f,
        fieldnames=fields
    )

    writer.writeheader()
    writer.writerows(
        field_rows
    )


with OUT_REPORTS.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    fields = [
        "year",
        "session_id",
        "report_index",
        "document_id",
        "name",
        "document_type",
        "relative_url",
        "download_status",
        "download_url",
        "final_url",
        "download_bytes",
        "saved_path",
        "error",
    ]

    writer = csv.DictWriter(
        f,
        fieldnames=fields
    )

    writer.writeheader()
    writer.writerows(
        report_rows
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


summary = {
    "phase":
        "R4LC3",

    "status":
        "R4LC3_OFFICIAL_LAST_CHANCE_RECORD_REPORT_INGESTION_READY",

    "sessions":
        SESSIONS,

    "record_counts": {
        str(year):
            sum(
                1
                for r in record_rows
                if r["year"] == year
            )
        for year in SESSIONS
    },

    "report_counts": {
        str(year):
            sum(
                1
                for r in report_rows
                if r["year"] == year
            )
        for year in SESSIONS
    },

    "downloaded_report_counts": {
        str(year):
            sum(
                1
                for r in report_rows
                if (
                    r["year"] == year
                    and
                    r[
                        "download_status"
                    ] == 200
                )
            )
        for year in SESSIONS
    },
}


OUT_SUMMARY.write_text(
    json.dumps(
        summary,
        indent=2,
        ensure_ascii=False
    ),
    encoding="utf-8"
)


# =============================================================================
# 4. Console summary
# =============================================================================

print()
print("=" * 118)
print("R4LC3 YEAR SUMMARY")
print("=" * 118)

for year in SESSIONS:

    n_records = sum(
        1
        for r in record_rows
        if r["year"] == year
    )

    n_reports = sum(
        1
        for r in report_rows
        if r["year"] == year
    )

    n_downloaded = sum(
        1
        for r in report_rows
        if (
            r["year"] == year
            and
            r["download_status"] == 200
        )
    )

    print(
        f"{year} | "
        f"records={n_records} | "
        f"reports={n_reports} | "
        f"downloaded={n_downloaded}"
    )


print()
print("=" * 118)
print("REPORT DOWNLOAD SUMMARY")
print("=" * 118)

if not report_rows:

    print(
        "NO SESSION REPORTS PRESENT"
    )

else:

    for row in report_rows:

        print(
            f"{row['year']} | "
            f"{row['name']} | "
            f"{row['document_type']} | "
            f"HTTP={row['download_status']} | "
            f"bytes={row['download_bytes']} | "
            f"path={row['saved_path'] or '-'}"
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
    OUT_RECORDS.relative_to(ROOT)
)
print(
    OUT_FIELDS.relative_to(ROOT)
)
print(
    OUT_REPORTS.relative_to(ROOT)
)
print(
    OUT_QA.relative_to(ROOT)
)
print(
    OUT_SUMMARY.relative_to(ROOT)
)

print()
print(
    "R4LC3_OFFICIAL_LAST_CHANCE_RECORD_REPORT_INGESTION_READY"
)
