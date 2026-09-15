from pathlib import Path
import csv


ROOT = Path(".")

EXCLUDE_PARTS = {
    ".git",
    "__pycache__",
    "node_modules",
    ".venv",
    "venv",
}

INTERESTING_FIELDS = {
    "attempt_id",
    "attempt_key",
    "year",
    "session_id",
    "car_number",
    "driver_name",
    "car_attempt_index",
    "four_lap_average_speed_mph",
    "speed_avg_mph",
    "average_speed_mph",
    "result_status",
    "status",
}


def excluded(path):
    return any(
        part in EXCLUDE_PARTS
        for part in path.parts
    )


def inspect_csv(path):

    try:
        with path.open(
            "r",
            encoding="utf-8-sig",
            errors="replace",
            newline="",
        ) as f:

            reader = csv.DictReader(f)

            fields = (
                reader.fieldnames
                or []
            )

            rows_sample = []

            for i, row in enumerate(reader):
                rows_sample.append(row)

                if i >= 499:
                    break

        return fields, rows_sample

    except Exception:
        return [], []


def has_2022(rows):

    for row in rows:

        for field in [
            "year",
            "Year",
            "season_year",
        ]:

            if str(
                row.get(field, "")
            ).strip() == "2022":

                return True

        for field in [
            "session_id",
            "attempt_key",
        ]:

            if "2022" in str(
                row.get(field, "")
            ):

                return True

    return False


def main():

    candidates = []

    for path in ROOT.rglob("*.csv"):

        if excluded(path):
            continue

        fields, sample = inspect_csv(
            path
        )

        if not fields:
            continue

        lower_fields = {
            field.lower()
            for field in fields
        }

        if "attempt_id" not in lower_fields:
            continue

        matched = sorted(
            field
            for field in fields
            if field.lower()
            in INTERESTING_FIELDS
        )

        score = 0

        if "attempt_id" in lower_fields:
            score += 5

        if "car_number" in lower_fields:
            score += 3

        if (
            "four_lap_average_speed_mph"
            in lower_fields
        ):
            score += 5

        if "speed_avg_mph" in lower_fields:
            score += 4

        if "car_attempt_index" in lower_fields:
            score += 3

        if "year" in lower_fields:
            score += 2

        if "session_id" in lower_fields:
            score += 2

        year_2022 = has_2022(
            sample
        )

        if year_2022:
            score += 5

        candidates.append({
            "score":
                score,

            "path":
                str(path),

            "field_count":
                len(fields),

            "has_2022_in_first_500_rows":
                year_2022,

            "interesting_fields":
                matched,
        })

    candidates.sort(
        key=lambda x: (
            -x["score"],
            x["path"],
        )
    )

    print()
    print("=" * 120)
    print(
        "R1G.11 — CANONICAL ATTEMPT TABLE DISCOVERY"
    )
    print("=" * 120)

    print()
    print(
        "CANDIDATE TABLES:",
        len(candidates),
    )

    for index, item in enumerate(
        candidates[:30],
        start=1,
    ):

        print()
        print(
            f"#{index} SCORE={item['score']}"
        )

        print(
            "PATH:",
            item["path"],
        )

        print(
            "HAS 2022:",
            item[
                "has_2022_in_first_500_rows"
            ],
        )

        print(
            "FIELDS:",
            item[
                "interesting_fields"
            ],
        )

    print()
    print("=" * 120)

    strong = [
        item
        for item in candidates
        if (
            item[
                "has_2022_in_first_500_rows"
            ]
            and
            item["score"] >= 15
        )
    ]

    print(
        "STRONG 2022 ATTEMPT TABLE CANDIDATES:",
        len(strong),
    )

    for item in strong:
        print(
            item["path"]
        )

    print()
    print("=" * 120)

    if strong:

        print(
            "FINAL STATUS: "
            "CANONICAL_ATTEMPT_TABLE_CANDIDATES_FOUND"
        )

    else:

        print(
            "FINAL STATUS: "
            "CANONICAL_ATTEMPT_TABLE_DISCOVERY_REVIEW_REQUIRED"
        )

    print("=" * 120)


if __name__ == "__main__":
    main()
