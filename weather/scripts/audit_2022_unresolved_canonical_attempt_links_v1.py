from pathlib import Path
import csv


CANONICAL = Path(
    "data/canonical/v1/attempts.csv"
)

UNRESOLVED = Path(
    "weather/output/"
    "chronology_rescue_2022_unresolved_attempt_links_v1.csv"
)


def read_csv(path):
    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as f:
        return list(csv.DictReader(f))


def txt(v):
    return "" if v is None else str(v).strip()


def norm_car(v):
    t = txt(v)

    if not t:
        return ""

    try:
        return str(int(float(t)))
    except Exception:
        return t.lstrip("0") or "0"


def is_2022(row):
    if txt(row.get("year")) == "2022":
        return True

    if "2022" in txt(
        row.get("session_id")
    ):
        return True

    return False


def show_fields(row):

    preferred = [
        "attempt_id",
        "attempt_key",
        "session_id",
        "car_number",
        "driver_name",
        "car_attempt_index",
        "four_lap_average_speed_mph",
        "result_status",
        "attempt_class",
        "attempt_source_class",
        "official_result_row",
        "canonical_source_class",
        "source_report_lap_index",
        "laps_complete",
        "result_counted_at_session_end",
    ]

    printed = set()

    for field in preferred:

        if field in row:

            print(
                f"    {field}: "
                f"{repr(txt(row.get(field)))}"
            )

            printed.add(field)

    extras = []

    for key, value in row.items():

        if key in printed:
            continue

        value = txt(value)

        if not value:
            continue

        lower = key.lower()

        if any(
            token in lower
            for token in [
                "status",
                "attempt",
                "result",
                "speed",
                "lap",
                "class",
                "source",
            ]
        ):

            extras.append(
                (
                    key,
                    value,
                )
            )

    if extras:

        print(
            "    additional relevant fields:"
        )

        for key, value in extras:

            print(
                f"      {key}: "
                f"{repr(value)}"
            )


def main():

    print()
    print("=" * 120)
    print(
        "R1G.13 — 2022 UNRESOLVED "
        "CANONICAL ATTEMPT LINK AUDIT V1"
    )
    print("=" * 120)

    for path in [
        CANONICAL,
        UNRESOLVED,
    ]:

        print(
            f"{path}: "
            f"{'PRESENT' if path.exists() else 'MISSING'}"
        )

    if (
        not CANONICAL.exists()
        or
        not UNRESOLVED.exists()
    ):

        print()
        print(
            "FINAL STATUS: "
            "2022_UNRESOLVED_LINK_AUDIT_INPUT_MISSING"
        )

        return

    canonical = read_csv(
        CANONICAL
    )

    unresolved = read_csv(
        UNRESOLVED
    )

    canonical_2022 = [
        row
        for row in canonical
        if is_2022(row)
    ]

    print()
    print(
        "CANONICAL 2022 ROWS:",
        len(canonical_2022),
    )

    print(
        "UNRESOLVED OFFICIAL ROWS:",
        len(unresolved),
    )

    print()
    print("=" * 120)
    print(
        "UNRESOLVED ROW DETAIL"
    )
    print("=" * 120)

    for i, u in enumerate(
        unresolved,
        start=1,
    ):

        car = norm_car(
            u.get("car_number")
        )

        print()
        print("#" * 120)
        print(
            f"UNRESOLVED {i}"
        )
        print("#" * 120)

        print(
            "official_result_row:",
            repr(
                txt(
                    u.get(
                        "official_result_row"
                    )
                )
            ),
        )

        print(
            "car:",
            repr(car),
        )

        print(
            "driver:",
            repr(
                txt(
                    u.get(
                        "driver_name"
                    )
                )
            ),
        )

        print(
            "official_speed:",
            repr(
                txt(
                    u.get(
                        "official_speed_mph"
                    )
                )
            ),
        )

        print(
            "official_status:",
            repr(
                txt(
                    u.get(
                        "official_status"
                    )
                )
            ),
        )

        print(
            "best_score:",
            repr(
                txt(
                    u.get(
                        "best_score"
                    )
                )
            ),
        )

        print(
            "best_attempt_id:",
            repr(
                txt(
                    u.get(
                        "best_attempt_id"
                    )
                )
            ),
        )

        print(
            "second_score:",
            repr(
                txt(
                    u.get(
                        "second_score"
                    )
                )
            ),
        )

        print(
            "reason:",
            repr(
                txt(
                    u.get(
                        "reason"
                    )
                )
            ),
        )

        same_car = [
            row
            for row in canonical_2022
            if norm_car(
                row.get(
                    "car_number"
                )
            ) == car
        ]

        same_car.sort(
            key=lambda row: (
                int(
                    txt(
                        row.get(
                            "car_attempt_index"
                        )
                    )
                    or 999
                ),
                txt(
                    row.get(
                        "attempt_id"
                    )
                ),
            )
        )

        print()
        print(
            "CANONICAL SAME-CAR CANDIDATES:",
            len(same_car),
        )

        for j, row in enumerate(
            same_car,
            start=1,
        ):

            print()
            print(
                f"  CANDIDATE {j}"
            )

            show_fields(
                row
            )

    # ========================================================
    # SPECIAL NEWGARDEN CHECK
    # ========================================================

    print()
    print("=" * 120)
    print(
        "NEWGARDEN SPECIAL CHECK"
    )
    print("=" * 120)

    newg_unresolved = [
        row
        for row in unresolved
        if (
            norm_car(
                row.get(
                    "car_number"
                )
            ) == "2"
            and
            txt(
                row.get(
                    "official_status"
                )
            ).lower()
            == "no attempt"
        )
    ]

    newg_canonical = [
        row
        for row in canonical_2022
        if norm_car(
            row.get(
                "car_number"
            )
        ) == "2"
    ]

    print()
    print(
        "Unresolved Newgarden No Attempt rows:",
        len(newg_unresolved),
    )

    print(
        "Canonical Newgarden attempts:",
        len(newg_canonical),
    )

    for row in sorted(
        newg_canonical,
        key=lambda r: (
            int(
                txt(
                    r.get(
                        "car_attempt_index"
                    )
                )
                or 999
            )
        ),
    ):

        print()
        show_fields(
            row
        )

    print()
    print("=" * 120)

    if len(unresolved) == 4:

        print(
            "FINAL STATUS: "
            "2022_UNRESOLVED_CANONICAL_LINKS_AUDITED"
        )

    else:

        print(
            "FINAL STATUS: "
            "2022_UNRESOLVED_CANONICAL_LINK_AUDIT_REVIEW_REQUIRED"
        )

    print("=" * 120)


if __name__ == "__main__":
    main()
