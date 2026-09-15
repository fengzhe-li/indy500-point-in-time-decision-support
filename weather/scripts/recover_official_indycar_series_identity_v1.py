from pathlib import Path
from html.parser import HTMLParser

import csv
import json
import re


# ============================================================
# PHASE
# ============================================================

PHASE = "R1E.2"


# ============================================================
# EXISTING OFFICIAL PAGE HTML
# ============================================================

HTML_DIR = Path(
    "weather/evidence/rescue/"
    "official_results_api_contract"
)

YEARS = [
    2020,
    2021,
    2022,
    2023,
    2024,
]


# ============================================================
# OUTPUT
# ============================================================

OUTPUT_DIR = Path(
    "weather/output"
)

OUTPUT_FILE = (
    OUTPUT_DIR
    / "official_indycar_series_identity_v1.csv"
)


# ============================================================
# TARGET INPUT IDs
# ============================================================

TARGET_IDS = [
    "hdnSeries",
    "hdnSeriesName",
    "hdnYear",
    "hdnEvent",
    "hdnSession",
    "hdnActiveTab",
]


# ============================================================
# HTML PARSER
# ============================================================

class InputParser(HTMLParser):

    def __init__(self):

        super().__init__()

        self.inputs = []

    def handle_starttag(
        self,
        tag,
        attrs,
    ):

        if tag.lower() != "input":
            return

        attrs_dict = dict(
            attrs
        )

        element_id = attrs_dict.get(
            "id"
        )

        if not element_id:
            return

        self.inputs.append(
            attrs_dict
        )


# ============================================================
# FILE RESOLUTION
# ============================================================

def find_year_html(
    year,
):

    expected = (
        HTML_DIR
        /
        f"{year}_day1_results_page.html"
    )

    if expected.exists():

        return expected

    candidates = sorted(
        HTML_DIR.glob(
            f"{year}*.html"
        )
    )

    if candidates:

        return candidates[
            0
        ]

    return None


# ============================================================
# FALLBACK REGEX
# ============================================================

def regex_extract_input(
    html,
    target_id,
):

    patterns = [
        rf'<input[^>]*id=["\']{re.escape(target_id)}["\'][^>]*>',
        rf'<input[^>]*id={re.escape(target_id)}[^>]*>',
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            html,
            flags=re.IGNORECASE,
        )

        if not match:
            continue

        tag = match.group(
            0
        )

        value_match = re.search(
            r'value\s*=\s*["\']([^"\']*)["\']',
            tag,
            flags=re.IGNORECASE,
        )

        if value_match:

            return value_match.group(
                1
            )

        value_match = re.search(
            r'value\s*=\s*([^\s>]+)',
            tag,
            flags=re.IGNORECASE,
        )

        if value_match:

            return (
                value_match.group(
                    1
                )
                .strip(
                    "\"'"
                )
            )

    return ""


# ============================================================
# MAIN
# ============================================================

def main():

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print()
    print("=" * 110)
    print(
        "R1E.2 — OFFICIAL INDYCAR SERIES "
        "IDENTITY RECOVERY V1"
    )
    print("=" * 110)

    rows = []

    all_series_ids = set()
    all_series_names = set()

    for year in YEARS:

        print()
        print("=" * 90)
        print(
            f"YEAR {year}"
        )
        print("=" * 90)

        path = find_year_html(
            year
        )

        if path is None:

            print(
                "HTML FILE NOT FOUND"
            )

            rows.append(
                {
                    "year":
                        year,

                    "html_path":
                        "",

                    "hdnSeries":
                        "",

                    "hdnSeriesName":
                        "",

                    "hdnYear":
                        "",

                    "hdnEvent":
                        "",

                    "hdnSession":
                        "",

                    "hdnActiveTab":
                        "",

                    "status":
                        "HTML_NOT_FOUND",
                }
            )

            continue

        print(
            "HTML:",
            path,
        )

        html = path.read_text(
            encoding="utf-8",
            errors="replace",
        )

        parser = InputParser()

        try:

            parser.feed(
                html
            )

        except Exception as exc:

            print(
                "HTML PARSER WARNING:",
                exc,
            )

        values = {}

        # ----------------------------------------------------
        # First use proper parsed INPUT attributes
        # ----------------------------------------------------

        for target_id in TARGET_IDS:

            value = ""

            for attrs in (
                parser.inputs
            ):

                current_id = (
                    attrs.get(
                        "id",
                        ""
                    )
                    .strip()
                )

                if (
                    current_id.lower()
                    != target_id.lower()
                ):

                    continue

                value = (
                    attrs.get(
                        "value",
                        ""
                    )
                    .strip()
                )

                break

            # ------------------------------------------------
            # Regex fallback
            # ------------------------------------------------

            if not value:

                value = regex_extract_input(
                    html,
                    target_id,
                )

            values[
                target_id
            ] = value

        # ----------------------------------------------------
        # Print recovered values
        # ----------------------------------------------------

        for target_id in TARGET_IDS:

            print(
                f"{target_id}: "
                f"{values.get(target_id, '')!r}"
            )

        series_id = values.get(
            "hdnSeries",
            ""
        )

        series_name = values.get(
            "hdnSeriesName",
            ""
        )

        if series_id:

            all_series_ids.add(
                series_id
            )

        if series_name:

            all_series_names.add(
                series_name
            )

        status = (
            "SERIES_ID_FOUND"
            if series_id
            else "SERIES_ID_NOT_FOUND"
        )

        rows.append(
            {
                "year":
                    year,

                "html_path":
                    str(
                        path
                    ),

                "hdnSeries":
                    series_id,

                "hdnSeriesName":
                    series_name,

                "hdnYear":
                    values.get(
                        "hdnYear",
                        ""
                    ),

                "hdnEvent":
                    values.get(
                        "hdnEvent",
                        ""
                    ),

                "hdnSession":
                    values.get(
                        "hdnSession",
                        ""
                    ),

                "hdnActiveTab":
                    values.get(
                        "hdnActiveTab",
                        ""
                    ),

                "status":
                    status,
            }
        )

    # ========================================================
    # WRITE
    # ========================================================

    fields = [
        "year",
        "html_path",
        "hdnSeries",
        "hdnSeriesName",
        "hdnYear",
        "hdnEvent",
        "hdnSession",
        "hdnActiveTab",
        "status",
    ]

    with OUTPUT_FILE.open(
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

    # ========================================================
    # FINAL SUMMARY
    # ========================================================

    successful_years = [
        row[
            "year"
        ]
        for row in rows
        if row[
            "hdnSeries"
        ]
    ]

    print()
    print("=" * 110)
    print(
        "SERIES IDENTITY SUMMARY"
    )
    print("=" * 110)

    print()
    print(
        "Years with series ID:",
        successful_years,
    )

    print(
        "Unique series IDs:"
    )

    for value in sorted(
        all_series_ids
    ):

        print(
            "  ",
            value,
        )

    print(
        "Unique series names:"
    )

    for value in sorted(
        all_series_names
    ):

        print(
            "  ",
            value,
        )

    print()
    print(
        "PREVIOUS WRONG SERIES ID:"
    )

    print(
        "  09341e09-3216-4f89-a45f-db697d72ee13"
    )

    print()

    if (
        len(
            successful_years
        )
        == 5
        and
        len(
            all_series_ids
        )
        >= 1
    ):

        print(
            "FINAL STATUS: "
            "OFFICIAL_INDYCAR_SERIES_ID_RECOVERED"
        )

    else:

        print(
            "FINAL STATUS: "
            "OFFICIAL_INDYCAR_SERIES_ID_REVIEW_REQUIRED"
        )

    print()
    print(
        "OUTPUT:"
    )

    print(
        OUTPUT_FILE
    )

    print()
    print(
        "NO API CALLS WERE MADE."
    )

    print(
        "NO CANONICAL DATA WAS MODIFIED."
    )


if __name__ == "__main__":
    main()
