from pathlib import Path

import csv
import json
import re
import shutil
import subprocess


# ============================================================
# PHASE
# ============================================================

PHASE = "R1F"


# ============================================================
# INPUT
# ============================================================

PDF_DIR = Path(
    "weather/evidence/rescue/"
    "official_day1_session_details/reports_v2"
)


# ============================================================
# OUTPUT
# ============================================================

TEXT_DIR = Path(
    "weather/evidence/rescue/"
    "official_day1_session_details/report_text_v1"
)

OUTPUT_DIR = Path(
    "weather/output"
)

FILE_AUDIT_CSV = (
    OUTPUT_DIR
    / "official_day1_report_text_file_audit_v1.csv"
)

TERM_HITS_CSV = (
    OUTPUT_DIR
    / "official_day1_report_text_term_hits_v1.csv"
)

SUMMARY_CSV = (
    OUTPUT_DIR
    / "official_day1_report_text_summary_v1.csv"
)

QA_CSV = (
    OUTPUT_DIR
    / "official_day1_report_text_audit_v1_qa.csv"
)


# ============================================================
# SEARCH TERMS
# ============================================================

SEARCH_TERMS = [
    "lane 1",
    "lane 2",
    "lane",
    "priority",
    "withdraw",
    "withdrew",
    "withdrawn",
    "queue",
    "line",
    "attempt",
    "requalify",
    "re-qualify",
    "requalification",
    "time",
    "timestamp",
    "position",
    "rank",
    "bump",
    "cutoff",
    "pit",
    "service",
    "refuel",
    "fuel",
    "cool",
    "cooling",
    "waved",
    "waved off",
    "canceled",
    "cancelled",
    "invalidated",
    "penalty",
]


# ============================================================
# HELPERS
# ============================================================

def parse_filename(path):

    # Expected:
    # 2022_6033_01_Results.pdf

    match = re.match(
        r"(?P<year>\d{4})_"
        r"(?P<session>\d+)_"
        r"(?P<index>\d+)_"
        r"(?P<report>.+)\.pdf$",
        path.name,
    )

    if not match:

        return {
            "year": "",
            "session_id": "",
            "report_index": "",
            "report_type": "",
        }

    return {
        "year":
            match.group(
                "year"
            ),

        "session_id":
            match.group(
                "session"
            ),

        "report_index":
            match.group(
                "index"
            ),

        "report_type":
            match.group(
                "report"
            ).replace(
                "_",
                " "
            ),
    }


def normalize_whitespace(text):

    text = text.replace(
        "\r\n",
        "\n",
    )

    text = text.replace(
        "\r",
        "\n",
    )

    return text


def context_window(
    lines,
    line_index,
    before=2,
    after=2,
):

    start = max(
        0,
        line_index - before,
    )

    end = min(
        len(lines),
        line_index + after + 1,
    )

    selected = []

    for idx in range(
        start,
        end,
    ):

        selected.append(
            f"{idx + 1}: "
            f"{lines[idx]}"
        )

    return " || ".join(
        selected
    )


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

    TEXT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print()
    print("=" * 110)

    print(
        "R1F — OFFICIAL DAY 1 REPORT "
        "TEXT CONTENT AUDIT V1"
    )

    print("=" * 110)

    # --------------------------------------------------------
    # Tool check
    # --------------------------------------------------------

    pdftotext = shutil.which(
        "pdftotext"
    )

    print()
    print(
        "PDFTOTEXT:",
        pdftotext,
    )

    if not pdftotext:

        print()
        print(
            "FINAL STATUS: "
            "PDFTOTEXT_NOT_AVAILABLE"
        )

        return

    pdf_files = sorted(
        PDF_DIR.glob(
            "*.pdf"
        )
    )

    print(
        "PDF FILE COUNT:",
        len(
            pdf_files
        ),
    )

    file_rows = []
    hit_rows = []

    # ========================================================
    # FILE LOOP
    # ========================================================

    for pdf_index, pdf_path in enumerate(
        pdf_files,
        start=1,
    ):

        meta = parse_filename(
            pdf_path
        )

        print()
        print("=" * 110)

        print(
            f"FILE {pdf_index:02d}/{len(pdf_files)}"
        )

        print("=" * 110)

        print(
            "PDF:",
            pdf_path
        )

        text_path = (
            TEXT_DIR
            /
            (
                pdf_path.stem
                + ".txt"
            )
        )

        # ----------------------------------------------------
        # Extract text
        # ----------------------------------------------------

        process = subprocess.run(
            [
                pdftotext,
                "-layout",
                str(
                    pdf_path
                ),
                str(
                    text_path
                ),
            ],
            capture_output=True,
            text=True,
        )

        extract_ok = (
            process.returncode
            == 0
            and
            text_path.exists()
        )

        if extract_ok:

            text = text_path.read_text(
                encoding="utf-8",
                errors="replace",
            )

            text = normalize_whitespace(
                text
            )

        else:

            text = ""

        lines = text.splitlines()

        nonempty_lines = [
            line
            for line in lines
            if line.strip()
        ]

        char_count = len(
            text
        )

        print(
            "EXTRACT OK:",
            extract_ok,
        )

        print(
            "CHAR COUNT:",
            char_count,
        )

        print(
            "NONEMPTY LINES:",
            len(
                nonempty_lines
            ),
        )

        # ----------------------------------------------------
        # Search terms
        # ----------------------------------------------------

        file_term_counts = {}

        for term in SEARCH_TERMS:

            pattern = re.compile(
                re.escape(
                    term
                ),
                flags=re.IGNORECASE,
            )

            count = 0

            for line_index, line in enumerate(
                lines
            ):

                matches = list(
                    pattern.finditer(
                        line
                    )
                )

                if not matches:

                    continue

                count += len(
                    matches
                )

                hit_rows.append(
                    {
                        "year":
                            meta[
                                "year"
                            ],

                        "session_id":
                            meta[
                                "session_id"
                            ],

                        "report_index":
                            meta[
                                "report_index"
                            ],

                        "report_type":
                            meta[
                                "report_type"
                            ],

                        "pdf_path":
                            str(
                                pdf_path
                            ),

                        "text_path":
                            str(
                                text_path
                            ),

                        "term":
                            term,

                        "line_number":
                            line_index
                            + 1,

                        "line_text":
                            line.strip(),

                        "context":
                            context_window(
                                lines,
                                line_index,
                            ),
                    }
                )

            file_term_counts[
                term
            ] = count

        total_hits = sum(
            file_term_counts.values()
        )

        print(
            "TOTAL TERM HITS:",
            total_hits,
        )

        interesting_terms = [
            term
            for term, count
            in file_term_counts.items()
            if count > 0
        ]

        print(
            "TERMS FOUND:",
            interesting_terms,
        )

        file_rows.append(
            {
                "year":
                    meta[
                        "year"
                    ],

                "session_id":
                    meta[
                        "session_id"
                    ],

                "report_index":
                    meta[
                        "report_index"
                    ],

                "report_type":
                    meta[
                        "report_type"
                    ],

                "pdf_path":
                    str(
                        pdf_path
                    ),

                "text_path":
                    str(
                        text_path
                    ),

                "extract_ok":
                    extract_ok,

                "pdftotext_returncode":
                    process.returncode,

                "char_count":
                    char_count,

                "nonempty_line_count":
                    len(
                        nonempty_lines
                    ),

                "total_term_hits":
                    total_hits,

                "terms_found":
                    json.dumps(
                        interesting_terms,
                        ensure_ascii=False,
                    ),

                "stderr":
                    process.stderr.strip(),
            }
        )

    # ========================================================
    # WRITE FILE AUDIT
    # ========================================================

    write_csv(
        FILE_AUDIT_CSV,
        file_rows,
        [
            "year",
            "session_id",
            "report_index",
            "report_type",
            "pdf_path",
            "text_path",
            "extract_ok",
            "pdftotext_returncode",
            "char_count",
            "nonempty_line_count",
            "total_term_hits",
            "terms_found",
            "stderr",
        ],
    )

    # ========================================================
    # WRITE HITS
    # ========================================================

    write_csv(
        TERM_HITS_CSV,
        hit_rows,
        [
            "year",
            "session_id",
            "report_index",
            "report_type",
            "pdf_path",
            "text_path",
            "term",
            "line_number",
            "line_text",
            "context",
        ],
    )

    # ========================================================
    # SUMMARY BY YEAR / TERM
    # ========================================================

    summary_rows = []

    years = sorted(
        {
            row[
                "year"
            ]
            for row in file_rows
            if row[
                "year"
            ]
        }
    )

    for year in years:

        for term in SEARCH_TERMS:

            year_hits = [
                row
                for row in hit_rows
                if (
                    row[
                        "year"
                    ]
                    == year
                    and
                    row[
                        "term"
                    ]
                    == term
                )
            ]

            summary_rows.append(
                {
                    "year":
                        year,

                    "term":
                        term,

                    "hit_count":
                        len(
                            year_hits
                        ),

                    "files_with_hits":
                        len(
                            {
                                row[
                                    "pdf_path"
                                ]
                                for row
                                in year_hits
                            }
                        ),
                }
            )

    write_csv(
        SUMMARY_CSV,
        summary_rows,
        [
            "year",
            "term",
            "hit_count",
            "files_with_hits",
        ],
    )

    # ========================================================
    # QA
    # ========================================================

    successful_extracts = sum(
        1
        for row in file_rows
        if row[
            "extract_ok"
        ]
    )

    nonempty_extracts = sum(
        1
        for row in file_rows
        if (
            row[
                "extract_ok"
            ]
            and
            int(
                row[
                    "char_count"
                ]
            )
            > 0
        )
    )

    qa_rows = [
        {
            "metric":
                "pdf_files_expected",

            "value":
                17,

            "status":
                (
                    "PASS"
                    if len(
                        pdf_files
                    )
                    == 17
                    else "REVIEW"
                ),
        },

        {
            "metric":
                "successful_text_extractions",

            "value":
                successful_extracts,

            "status":
                (
                    "PASS"
                    if successful_extracts
                    == len(
                        pdf_files
                    )
                    else "REVIEW"
                ),
        },

        {
            "metric":
                "nonempty_text_extractions",

            "value":
                nonempty_extracts,

            "status":
                (
                    "PASS"
                    if nonempty_extracts
                    == len(
                        pdf_files
                    )
                    else "REVIEW"
                ),
        },

        {
            "metric":
                "term_hit_rows",

            "value":
                len(
                    hit_rows
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
                "ocr_used",

            "value":
                0,

            "status":
                "PASS",
        },
    ]

    write_csv(
        QA_CSV,
        qa_rows,
        [
            "metric",
            "value",
            "status",
        ],
    )

    # ========================================================
    # PRINT SUMMARY
    # ========================================================

    print()
    print("=" * 110)

    print(
        "TERM HIT SUMMARY"
    )

    print("=" * 110)

    for year in years:

        print()
        print(
            f"YEAR {year}"
        )

        year_summary = [
            row
            for row in summary_rows
            if (
                row[
                    "year"
                ]
                == year
                and
                row[
                    "hit_count"
                ]
                > 0
            )
        ]

        for row in year_summary:

            print(
                f"  {row['term']:<18} "
                f"hits={row['hit_count']:<4} "
                f"files={row['files_with_hits']}"
            )

    # --------------------------------------------------------
    # Print high-value hit previews
    # --------------------------------------------------------

    HIGH_VALUE_TERMS = [
        "lane 1",
        "lane 2",
        "priority",
        "withdraw",
        "withdrew",
        "withdrawn",
        "queue",
        "attempt",
        "requalify",
        "re-qualify",
        "canceled",
        "cancelled",
        "invalidated",
        "penalty",
        "bump",
        "cutoff",
        "pit",
        "service",
    ]

    high_value_hits = [
        row
        for row in hit_rows
        if row[
            "term"
        ]
        in HIGH_VALUE_TERMS
    ]

    print()
    print("=" * 110)

    print(
        "HIGH-VALUE HIT PREVIEW"
    )

    print("=" * 110)

    if not high_value_hits:

        print(
            "NONE"
        )

    else:

        for row in high_value_hits[:120]:

            print()

            print(
                f"{row['year']} | "
                f"{row['report_type']} | "
                f"{row['term']} | "
                f"line {row['line_number']}"
            )

            print(
                row[
                    "context"
                ]
            )

    # ========================================================
    # QA PRINT
    # ========================================================

    print()
    print("=" * 110)

    print(
        "QA"
    )

    print("=" * 110)

    for row in qa_rows:

        print(
            f"{row['metric']}: "
            f"{row['value']} "
            f"[{row['status']}]"
        )

    print()
    print("=" * 110)

    if (
        len(
            pdf_files
        )
        == 17
        and
        successful_extracts
        == 17
        and
        nonempty_extracts
        == 17
    ):

        print(
            "FINAL STATUS: "
            "OFFICIAL_DAY1_REPORT_TEXT_AUDIT_COMPLETE"
        )

    else:

        print(
            "FINAL STATUS: "
            "OFFICIAL_DAY1_REPORT_TEXT_AUDIT_REVIEW_REQUIRED"
        )

    print("=" * 110)

    print()
    print(
        "NO OCR WAS USED."
    )

    print(
        "NO CANONICAL DATA WAS MODIFIED."
    )

    print()
    print(
        "OUTPUTS"
    )

    print(
        FILE_AUDIT_CSV
    )

    print(
        TERM_HITS_CSV
    )

    print(
        SUMMARY_CSV
    )

    print(
        QA_CSV
    )

    print(
        TEXT_DIR
    )


if __name__ == "__main__":
    main()
