from pathlib import Path
import csv


CANONICAL = Path(
    "data/canonical/v1/attempts.csv"
)

RESULT_MATCHES = Path(
    "weather/output/"
    "chronology_rescue_2022_result_to_canonical_attempt_matches_v2.csv"
)

WEATHER_WINDOWS = Path(
    "weather/output/"
    "chronology_rescue_2022_weather_interruption_windows_v1.csv"
)

KARAM_AUDIT_V1 = Path(
    "weather/output/"
    "chronology_rescue_2022_karam_attempt_identity_audit_v1.csv"
)

OUTPUT_DIR = Path(
    "weather/output"
)

EVIDENCE_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_karam_racer_two_event_evidence_v1.csv"
)

ADJUDICATION_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_karam_two_event_adjudication_v1.csv"
)

ORDERING_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_karam_two_event_ordering_edges_v1.csv"
)

QA_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_karam_two_event_adjudication_v1_qa.csv"
)


RACER_URL = (
    "https://racer.com/2022/05/21/"
    "veekay-leads-saturday-indy-500-qualifying/"
)


def read_csv(path):
    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as f:
        return list(csv.DictReader(f))


def write_csv(path, rows, fields):
    with path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=fields,
        )
        writer.writeheader()
        writer.writerows(rows)


def txt(v):
    return "" if v is None else str(v).strip()


def norm_car(v):
    value = txt(v)

    try:
        return str(int(float(value)))
    except Exception:
        return value.lstrip("0") or "0"


def speed_close(a, b, tol=0.003):
    try:
        return abs(
            float(txt(a)) - float(txt(b))
        ) <= tol
    except Exception:
        return False


def main():

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print()
    print("=" * 120)
    print(
        "R1G.23 — 2022 SAGE KARAM "
        "TWO-EVENT CHRONOLOGY ADJUDICATION V1"
    )
    print("=" * 120)

    inputs = [
        CANONICAL,
        RESULT_MATCHES,
        WEATHER_WINDOWS,
        KARAM_AUDIT_V1,
    ]

    missing = []

    print()
    print("INPUT CHECK")
    print("-" * 120)

    for path in inputs:

        exists = path.exists()

        print(
            f"{path}: "
            f"{'PRESENT' if exists else 'MISSING'}"
        )

        if not exists:
            missing.append(path)

    if missing:
        print()
        print(
            "FINAL STATUS: "
            "KARAM_TWO_EVENT_ADJUDICATION_INPUT_MISSING"
        )
        return

    canonical = read_csv(CANONICAL)
    results = read_csv(RESULT_MATCHES)
    weather = read_csv(WEATHER_WINDOWS)

    karam_results = [
        row
        for row in results
        if norm_car(
            row.get("car_number")
        ) == "24"
    ]

    karam_229905 = [
        row
        for row in karam_results
        if speed_close(
            row.get("official_speed_mph"),
            "229.905",
        )
    ]

    karam_230464 = [
        row
        for row in karam_results
        if speed_close(
            row.get("official_speed_mph"),
            "230.464",
        )
    ]

    karam_no_attempt = [
        row
        for row in karam_results
        if txt(
            row.get("official_status")
        ) == "No Attempt"
    ]

    structure_ok = all([
        len(karam_229905) == 1,
        len(karam_230464) == 1,
        len(karam_no_attempt) == 1,
    ])

    print()
    print("=" * 120)
    print("KARAM RESULT STRUCTURE")
    print("=" * 120)

    print(
        "229.905:",
        len(karam_229905),
    )

    print(
        "230.464:",
        len(karam_230464),
    )

    print(
        "No Attempt:",
        len(karam_no_attempt),
    )

    if not structure_ok:
        print()
        print(
            "FINAL STATUS: "
            "KARAM_TWO_EVENT_RESULT_STRUCTURE_REVIEW_REQUIRED"
        )
        return

    aid_229905 = txt(
        karam_229905[0].get("attempt_id")
    )

    aid_230464 = txt(
        karam_230464[0].get("attempt_id")
    )

    aid_no_attempt = txt(
        karam_no_attempt[0].get("attempt_id")
    )

    # ========================================================
    # RACER EVIDENCE
    # ========================================================

    evidence_rows = [
        {
            "evidence_id":
                "R1G23-RACER-KARAM-FIRST-STOP",

            "driver_name":
                "Sage Karam",

            "car_number":
                "24",

            "event":
                "KARAM_ATTEMPT_DURING_FIRST_WEATHER_STOP",

            "relation":
                "ATTEMPT_ACTIVE_AT_OR_IMMEDIATELY_BEFORE_FIRST_WEATHER_STOP",

            "source_name":
                "RACER",

            "source_class":
                "REPUTABLE_SECONDARY_EDITORIAL",

            "source_url":
                RACER_URL,

            "evidence_summary":
                (
                    "RACER reports the first qualifying stoppage "
                    "occurred while Sage Karam was attempting to "
                    "improve his qualifying position."
                ),

            "specific_attempt_id":
                "",

            "specific_speed_mph":
                "",

            "promotion_status":
                "EVENT_LEVEL_ONLY",
        },

        {
            "evidence_id":
                "R1G23-RACER-KARAM-POST-RESTART",

            "driver_name":
                "Sage Karam",

            "car_number":
                "24",

            "event":
                "KARAM_ATTEMPT_AFTER_FIRST_WEATHER_HOLD",

            "relation":
                "FIRST_WEATHER_HOLD_LIFTED_BEFORE_KARAM_RERUN",

            "source_name":
                "RACER",

            "source_class":
                "REPUTABLE_SECONDARY_EDITORIAL",

            "source_url":
                RACER_URL,

            "evidence_summary":
                (
                    "RACER reports that after the approximately "
                    "hour-long first weather delay was resolved, "
                    "Karam ran again before McLaughlin and before "
                    "the heavier second rain."
                ),

            "specific_attempt_id":
                "",

            "specific_speed_mph":
                "",

            "promotion_status":
                "EVENT_LEVEL_ONLY",
        },
    ]

    # ========================================================
    # LOGICAL ADJUDICATION
    #
    # Important:
    # The RACER evidence proves two distinct event positions,
    # but does not itself label either event with a speed.
    #
    # Official status 'Withdrawn' proves result status only;
    # it does not prove wall-clock placement.
    #
    # Therefore:
    # - two-event chronology is promotable;
    # - speed-to-event identity is NOT promotable yet.
    # ========================================================

    adjudication_rows = [
        {
            "check":
                "racer_proves_pre_first_stop_karam_event",

            "result":
                "YES",

            "promotion":
                "PROMOTE_EVENT_ORDERING",

            "notes":
                (
                    "A Karam improvement attempt was underway "
                    "when the first weather stoppage occurred."
                ),
        },

        {
            "check":
                "racer_proves_post_restart_karam_event",

            "result":
                "YES",

            "promotion":
                "PROMOTE_EVENT_ORDERING",

            "notes":
                (
                    "RACER explicitly says Karam ran again "
                    "after the first weather delay."
                ),
        },

        {
            "check":
                "racer_proves_two_distinct_karam_attempt_events",

            "result":
                "YES",

            "promotion":
                "PROMOTE_EVENT_ORDERING",

            "notes":
                (
                    "The pre-stop attempt and post-restart rerun "
                    "are distinct events."
                ),
        },

        {
            "check":
                "229_905_can_be_uniquely_assigned_to_pre_stop_event",

            "result":
                "NO",

            "promotion":
                "DO_NOT_PROMOTE_IDENTITY",

            "notes":
                (
                    "No source currently co-identifies 229.905 "
                    "with the pre-stop event."
                ),
        },

        {
            "check":
                "230_464_can_be_uniquely_assigned_to_post_restart_event",

            "result":
                "NO",

            "promotion":
                "DO_NOT_PROMOTE_IDENTITY",

            "notes":
                (
                    "No source currently co-identifies 230.464 "
                    "with the post-restart event."
                ),
        },

        {
            "check":
                "no_attempt_can_be_uniquely_assigned_to_weather_event",

            "result":
                "NO",

            "promotion":
                "DO_NOT_PROMOTE_IDENTITY",

            "notes":
                (
                    "No source currently ties the No Attempt row "
                    "to one specific weather interruption."
                ),
        },
    ]

    # ========================================================
    # ORDERING EDGES — EVENT LEVEL ONLY
    # ========================================================

    ordering_rows = [
        {
            "edge_id":
                "R1G23-EDGE-KARAM-EVENT-A-FIRST-STOP",

            "from_event":
                "KARAM_PRE_FIRST_STOP_ATTEMPT_EVENT",

            "relation":
                "BEFORE_OR_INTERRUPTED_BY",

            "to_event":
                "FIRST_WEATHER_STOP",

            "from_attempt_id":
                "",

            "to_attempt_id":
                "",

            "constraint_class":
                "ORDERING_ONLY",

            "source_authority":
                "REPUTABLE_SECONDARY_EDITORIAL",

            "notes":
                (
                    "RACER reports first stoppage occurred while "
                    "Karam was attempting to improve."
                ),
        },

        {
            "edge_id":
                "R1G23-EDGE-FIRST-RESUME-KARAM-EVENT-B",

            "from_event":
                "FIRST_WEATHER_HOLD_LIFTED",

            "relation":
                "BEFORE",

            "to_event":
                "KARAM_POST_RESTART_ATTEMPT_EVENT",

            "from_attempt_id":
                "",

            "to_attempt_id":
                "",

            "constraint_class":
                "ORDERING_ONLY",

            "source_authority":
                "REPUTABLE_SECONDARY_EDITORIAL",

            "notes":
                (
                    "RACER reports Karam ran again after "
                    "the first weather delay was resolved."
                ),
        },

        {
            "edge_id":
                "R1G23-EDGE-KARAM-EVENT-B-MCLAUGHLIN",

            "from_event":
                "KARAM_POST_RESTART_ATTEMPT_EVENT",

            "relation":
                "BEFORE",

            "to_event":
                "MCLAUGHLIN_POST_RESTART_RERUN",

            "from_attempt_id":
                "",

            "to_attempt_id":
                "43d9c081-67f5-5d6f-8b48-9db0ac683a6c",

            "constraint_class":
                "ORDERING_ONLY",

            "source_authority":
                "REPUTABLE_SECONDARY_EDITORIAL",

            "notes":
                (
                    "RACER states Karam ran again, as did "
                    "McLaughlin, before heavier rain."
                ),
        },

        {
            "edge_id":
                "R1G23-EDGE-KARAM-EVENT-B-SECOND-STOP",

            "from_event":
                "KARAM_POST_RESTART_ATTEMPT_EVENT",

            "relation":
                "BEFORE",

            "to_event":
                "SECOND_WEATHER_STOP",

            "from_attempt_id":
                "",

            "to_attempt_id":
                "",

            "constraint_class":
                "ORDERING_ONLY",

            "source_authority":
                "REPUTABLE_SECONDARY_EDITORIAL",

            "notes":
                (
                    "RACER places Karam's post-restart run "
                    "before the heavier second rain."
                ),
        },
    ]

    # ========================================================
    # PRINT
    # ========================================================

    print()
    print("=" * 120)
    print("RACER TWO-EVENT FINDING")
    print("=" * 120)

    print()
    print(
        "Event A:"
    )
    print(
        "  Karam was attempting to improve "
        "when FIRST_WEATHER_STOP occurred."
    )

    print()
    print(
        "Event B:"
    )
    print(
        "  After FIRST_WEATHER_HOLD_LIFTED, "
        "Karam ran again before McLaughlin "
        "and before SECOND_WEATHER_STOP."
    )

    print()
    print(
        "These are two distinct Karam attempt events."
    )

    print()
    print("=" * 120)
    print("IDENTITY DECISION")
    print("=" * 120)

    print()
    print(
        "229.905 attempt_id:",
        aid_229905,
    )

    print(
        "230.464 attempt_id:",
        aid_230464,
    )

    print(
        "No Attempt attempt_id:",
        aid_no_attempt,
    )

    print()
    print(
        "Pre-stop event -> exact speed identity:",
        "UNRESOLVED",
    )

    print(
        "Post-restart event -> exact speed identity:",
        "UNRESOLVED",
    )

    print(
        "No Attempt -> exact weather event identity:",
        "UNRESOLVED",
    )

    print()
    print(
        "Therefore event chronology is promotable, "
        "but canonical attempt identity is not."
    )

    # ========================================================
    # WRITE
    # ========================================================

    write_csv(
        EVIDENCE_OUT,
        evidence_rows,
        [
            "evidence_id",
            "driver_name",
            "car_number",
            "event",
            "relation",
            "source_name",
            "source_class",
            "source_url",
            "evidence_summary",
            "specific_attempt_id",
            "specific_speed_mph",
            "promotion_status",
        ],
    )

    write_csv(
        ADJUDICATION_OUT,
        adjudication_rows,
        [
            "check",
            "result",
            "promotion",
            "notes",
        ],
    )

    write_csv(
        ORDERING_OUT,
        ordering_rows,
        [
            "edge_id",
            "from_event",
            "relation",
            "to_event",
            "from_attempt_id",
            "to_attempt_id",
            "constraint_class",
            "source_authority",
            "notes",
        ],
    )

    qa_rows = [
        {
            "metric":
                "karam_result_structure_unique",

            "value":
                int(structure_ok),

            "status":
                "PASS"
                if structure_ok
                else "FAIL",
        },

        {
            "metric":
                "racer_event_rows",

            "value":
                len(evidence_rows),

            "status":
                "PASS"
                if len(evidence_rows) == 2
                else "FAIL",
        },

        {
            "metric":
                "event_ordering_edges",

            "value":
                len(ordering_rows),

            "status":
                "PASS"
                if len(ordering_rows) == 4
                else "FAIL",
        },

        {
            "metric":
                "canonical_attempt_identity_promotions",

            "value":
                0,

            "status":
                "PASS",
        },

        {
            "metric":
                "withdrawn_status_used_as_timing",

            "value":
                0,

            "status":
                "PASS",
        },

        {
            "metric":
                "result_row_order_used_as_chronology",

            "value":
                0,

            "status":
                "PASS",
        },

        {
            "metric":
                "queue_wait_inferred",

            "value":
                0,

            "status":
                "PASS",
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
        QA_OUT,
        qa_rows,
        [
            "metric",
            "value",
            "status",
        ],
    )

    print()
    print("=" * 120)
    print("FINAL SUMMARY")
    print("=" * 120)

    print()
    print(
        "Karam distinct attempt events recovered:",
        2,
    )

    print(
        "New event-ordering edges:",
        len(ordering_rows),
    )

    print(
        "Canonical speed/event identity promotions:",
        0,
    )

    print()
    print(
        "RACER improves Karam chronology substantially, "
        "but still does not justify assigning 229.905 or "
        "230.464 to a specific weather-side event."
    )

    print(
        "No queue wait was inferred."
    )

    print(
        "No canonical data was modified."
    )

    print()
    print("=" * 120)
    print(
        "FINAL STATUS: "
        "KARAM_TWO_EVENT_CHRONOLOGY_PROMOTED_IDENTITY_UNRESOLVED"
    )
    print("=" * 120)

    print()
    print("OUTPUTS")
    print(EVIDENCE_OUT)
    print(ADJUDICATION_OUT)
    print(ORDERING_OUT)
    print(QA_OUT)


if __name__ == "__main__":
    main()
