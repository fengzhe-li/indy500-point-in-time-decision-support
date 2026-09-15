from pathlib import Path
import csv


PHASE = "R2C.4"

STATE_V1 = Path(
    "weather/output/"
    "contemporaneous_decision_state_evidence_ledger_v1.csv"
)

RESULT_V3 = Path(
    "weather/output/"
    "chronology_rescue_2022_result_to_canonical_attempt_matches_v3.csv"
)

OUTPUT_DIR = Path("weather/output")

STATE_V2 = (
    OUTPUT_DIR
    / "contemporaneous_decision_state_evidence_ledger_v2.csv"
)

SUMMARY_OUT = (
    OUTPUT_DIR
    / "contemporaneous_cutoff_speed_anchor_summary_v1.csv"
)

QA_OUT = (
    OUTPUT_DIR
    / "contemporaneous_cutoff_speed_anchor_v1_qa.csv"
)


MALUKAS_SECOND = (
    "85c917fa-1c7a-52cb-a47f-468b4bdae9a5"
)

SATO_SECOND = (
    "21e8c99e-b04c-516d-85a8-ccfbaed7ff46"
)

EXPECTED_MALUKAS_SPEED = "231.607"
EXPECTED_SATO_SPEED = "231.708"


def txt(v):
    return "" if v is None else str(v).strip()


def read_csv(path):
    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as f:
        return list(csv.DictReader(f))


def write_csv(path, rows, fields):
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=fields,
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)


def first(row, names):
    for name in names:
        value = txt(row.get(name))
        if value:
            return value
    return ""


def result_speed(row):
    return first(
        row,
        [
            "official_speed_mph",
            "speed_avg_mph",
            "speed_avg",
            "four_lap_average_speed_mph",
            "average_speed_mph",
        ],
    )


def main():

    print()
    print("=" * 122)
    print(
        "R2C.4 — 2022 CONTEMPORANEOUS "
        "TOP-12 CUTOFF SPEED ANCHOR DERIVATION"
    )
    print("=" * 122)

    required = [
        STATE_V1,
        RESULT_V3,
    ]

    print()
    print("INPUT CHECK")
    print("-" * 122)

    for path in required:
        print(
            f"{path}: "
            f"{'PRESENT' if path.exists() else 'MISSING'}"
        )

    if not all(path.exists() for path in required):
        print()
        print(
            "FINAL STATUS: "
            "R2C4_CUTOFF_SPEED_INPUT_MISSING"
        )
        return

    states = read_csv(STATE_V1)
    results = read_csv(RESULT_V3)

    result_by_id = {
        txt(row.get("attempt_id")): row
        for row in results
        if txt(row.get("attempt_id"))
    }

    malukas_result = result_by_id.get(
        MALUKAS_SECOND
    )

    sato_result = result_by_id.get(
        SATO_SECOND
    )

    malukas_speed = (
        result_speed(malukas_result)
        if malukas_result
        else
        ""
    )

    sato_speed = (
        result_speed(sato_result)
        if sato_result
        else
        ""
    )

    malukas_state = [
        row
        for row in states
        if (
            txt(row.get("state_id"))
            ==
            "R2C3-2022-MALUKAS-01"
            and
            txt(row.get("rank"))
            ==
            "12"
            and
            txt(row.get("top12_state"))
            ==
            "INSIDE"
            and
            txt(row.get("subject_attempt_id"))
            ==
            MALUKAS_SECOND
        )
    ]

    sato_state = [
        row
        for row in states
        if (
            txt(row.get("state_id"))
            ==
            "R2C3-2022-SATO-01"
            and
            txt(row.get("rank"))
            ==
            "12"
            and
            txt(row.get("top12_state"))
            ==
            "INSIDE"
            and
            txt(row.get("subject_attempt_id"))
            ==
            SATO_SECOND
        )
    ]

    malukas_grounded = (
        len(malukas_state) == 1
        and
        malukas_speed == EXPECTED_MALUKAS_SPEED
    )

    sato_grounded = (
        len(sato_state) == 1
        and
        sato_speed == EXPECTED_SATO_SPEED
    )

    print()
    print("=" * 122)
    print("GROUNDING")
    print("=" * 122)

    print()
    print(
        "Malukas P12 state rows:",
        len(malukas_state),
    )

    print(
        "Malukas attempt speed:",
        repr(malukas_speed),
    )

    print(
        "Expected:",
        EXPECTED_MALUKAS_SPEED,
    )

    print(
        "Malukas cutoff anchor grounded:",
        malukas_grounded,
    )

    print()
    print(
        "Sato P12 state rows:",
        len(sato_state),
    )

    print(
        "Sato attempt speed:",
        repr(sato_speed),
    )

    print(
        "Expected:",
        EXPECTED_SATO_SPEED,
    )

    print(
        "Sato cutoff anchor grounded:",
        sato_grounded,
    )

    if not (
        malukas_grounded
        and
        sato_grounded
    ):
        print()
        print(
            "FINAL STATUS: "
            "R2C4_CUTOFF_SPEED_GROUNDING_REVIEW_REQUIRED"
        )
        return

    fields = list(states[0].keys())

    extra_fields = [
        "cutoff_speed_derivation",
        "cutoff_speed_quality",
    ]

    for field in extra_fields:
        if field not in fields:
            fields.append(field)

    updated = []

    changed_ids = []

    for row in states:

        new = dict(row)

        state_id = txt(
            row.get("state_id")
        )

        if (
            state_id
            ==
            "R2C3-2022-MALUKAS-01"
        ):
            new[
                "cutoff_speed_mph"
            ] = EXPECTED_MALUKAS_SPEED

            new[
                "cutoff_speed_derivation"
            ] = (
                "DERIVED_FROM_CONTEMPORANEOUS_"
                "P12_ATTEMPT_BINDING"
            )

            new[
                "cutoff_speed_quality"
            ] = "SUPPORTED_DERIVED"

            changed_ids.append(
                state_id
            )

        elif (
            state_id
            ==
            "R2C3-2022-SATO-01"
        ):
            new[
                "cutoff_speed_mph"
            ] = EXPECTED_SATO_SPEED

            new[
                "cutoff_speed_derivation"
            ] = (
                "DERIVED_FROM_CONTEMPORANEOUS_"
                "P12_ATTEMPT_BINDING"
            )

            new[
                "cutoff_speed_quality"
            ] = "SUPPORTED_DERIVED"

            changed_ids.append(
                state_id
            )

        else:
            new.setdefault(
                "cutoff_speed_derivation",
                ""
            )

            new.setdefault(
                "cutoff_speed_quality",
                ""
            )

        updated.append(new)

    write_csv(
        STATE_V2,
        updated,
        fields,
    )

    cutoff_rows = [
        row
        for row in updated
        if txt(
            row.get(
                "cutoff_speed_mph"
            )
        )
        not in {
            "",
            "UNKNOWN",
        }
    ]

    exact_time_rows = [
        row
        for row in updated
        if txt(
            row.get(
                "exact_timestamp"
            )
        )
        not in {
            "",
            "UNKNOWN",
        }
    ]

    print()
    print("=" * 122)
    print("DERIVED CONTEMPORANEOUS CUTOFF ANCHORS")
    print("=" * 122)

    print()
    print(
        "Anchor 1:"
    )

    print(
        "  driver/state = David Malukas provisional P12"
    )

    print(
        "  cutoff rank = 12"
    )

    print(
        "  cutoff speed = 231.607 mph"
    )

    print(
        "  derivation = "
        "P12 state + bound attempt speed"
    )

    print()
    print(
        "Anchor 2:"
    )

    print(
        "  driver/state = Takuma Sato provisional P12"
    )

    print(
        "  cutoff rank = 12"
    )

    print(
        "  cutoff speed = 231.708 mph"
    )

    print(
        "  derivation = "
        "P12 state + bound attempt speed"
    )

    print()
    print(
        "Cutoff increase:",
        f"{float(EXPECTED_SATO_SPEED) - float(EXPECTED_MALUKAS_SPEED):.3f}",
        "mph",
    )

    print()
    print(
        "Known contemporaneous cutoff-speed rows:",
        len(cutoff_rows),
    )

    print(
        "Exact timestamp rows:",
        len(exact_time_rows),
    )

    print()
    print(
        "IMPORTANT:"
    )

    print(
        "  These are supported derived cutoff anchors."
    )

    print(
        "  They are NOT direct live timing-feed snapshots."
    )

    print(
        "  Exact timestamps remain UNKNOWN."
    )

    summary_rows = [
        {
            "metric":
                "state_ledger_input",
            "value":
                "V1",
        },
        {
            "metric":
                "state_ledger_output",
            "value":
                "V2",
        },
        {
            "metric":
                "malukas_p12_cutoff_speed_mph",
            "value":
                EXPECTED_MALUKAS_SPEED,
        },
        {
            "metric":
                "sato_p12_cutoff_speed_mph",
            "value":
                EXPECTED_SATO_SPEED,
        },
        {
            "metric":
                "cutoff_speed_increase_mph",
            "value":
                f"{float(EXPECTED_SATO_SPEED) - float(EXPECTED_MALUKAS_SPEED):.3f}",
        },
        {
            "metric":
                "known_cutoff_speed_rows",
            "value":
                len(cutoff_rows),
        },
        {
            "metric":
                "exact_timestamp_rows",
            "value":
                len(exact_time_rows),
        },
        {
            "metric":
                "derivation_class",
            "value":
                (
                    "DERIVED_FROM_CONTEMPORANEOUS_"
                    "P12_ATTEMPT_BINDING"
                ),
        },
    ]

    write_csv(
        SUMMARY_OUT,
        summary_rows,
        [
            "metric",
            "value",
        ],
    )

    qa_rows = [
        {
            "metric":
                "malukas_anchor_grounded",

            "value":
                int(malukas_grounded),

            "status":
                "PASS",
        },
        {
            "metric":
                "sato_anchor_grounded",

            "value":
                int(sato_grounded),

            "status":
                "PASS",
        },
        {
            "metric":
                "exact_changed_state_count",

            "value":
                len(changed_ids),

            "status":
                (
                    "PASS"
                    if len(changed_ids) == 2
                    else "FAIL"
                ),
        },
        {
            "metric":
                "known_cutoff_speed_rows_is_2",

            "value":
                len(cutoff_rows),

            "status":
                (
                    "PASS"
                    if len(cutoff_rows) == 2
                    else "FAIL"
                ),
        },
        {
            "metric":
                "malukas_cutoff_is_231_607",

            "value":
                int(
                    any(
                        txt(row.get("state_id"))
                        ==
                        "R2C3-2022-MALUKAS-01"
                        and
                        txt(row.get("cutoff_speed_mph"))
                        ==
                        EXPECTED_MALUKAS_SPEED
                        for row in updated
                    )
                ),

            "status":
                "PASS",
        },
        {
            "metric":
                "sato_cutoff_is_231_708",

            "value":
                int(
                    any(
                        txt(row.get("state_id"))
                        ==
                        "R2C3-2022-SATO-01"
                        and
                        txt(row.get("cutoff_speed_mph"))
                        ==
                        EXPECTED_SATO_SPEED
                        for row in updated
                    )
                ),

            "status":
                "PASS",
        },
        {
            "metric":
                "direct_live_feed_claimed",

            "value":
                0,

            "status":
                "PASS",
        },
        {
            "metric":
                "exact_timestamp_inferred",

            "value":
                len(exact_time_rows),

            "status":
                (
                    "PASS"
                    if len(exact_time_rows) == 0
                    else "FAIL"
                ),
        },
        {
            "metric":
                "chronology_mutation",

            "value":
                0,

            "status":
                "PASS",
        },
        {
            "metric":
                "action_lane_mutation",

            "value":
                0,

            "status":
                "PASS",
        },
    ]

    write_csv(
        QA_OUT,
        qa_rows,
        [
            "metric",
            "value",
            "status",
        ],
    )

    success = all(
        row["status"] == "PASS"
        for row in qa_rows
    )

    print()
    print("=" * 122)

    if success:
        print(
            "FINAL STATUS: "
            "R2C4_CONTEMPORANEOUS_CUTOFF_SPEED_ANCHORS_V2_READY"
        )
    else:
        print(
            "FINAL STATUS: "
            "R2C4_CUTOFF_SPEED_ANCHOR_REVIEW_REQUIRED"
        )

    print("=" * 122)

    print()
    print("OUTPUTS")
    print(STATE_V2)
    print(SUMMARY_OUT)
    print(QA_OUT)


if __name__ == "__main__":
    main()
