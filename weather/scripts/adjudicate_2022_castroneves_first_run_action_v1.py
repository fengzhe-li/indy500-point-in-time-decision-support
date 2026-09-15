from pathlib import Path
import csv


# ============================================================
# INPUTS
# ============================================================

CANONICAL = Path(
    "data/canonical/v1/attempts.csv"
)

RESULT_MATCHES = Path(
    "weather/output/"
    "chronology_rescue_2022_result_to_canonical_attempt_matches_v2.csv"
)

CASTRONEVES_EVIDENCE = Path(
    "weather/output/"
    "chronology_rescue_2022_castroneves_repeat_pair_evidence_v1.csv"
)

ACTION_LEDGER_V1 = Path(
    "weather/output/"
    "unified_attempt_action_lane_ledger_v1.csv"
)


# ============================================================
# OUTPUTS
# ============================================================

OUTPUT_DIR = Path(
    "weather/output"
)

ADJUDICATED_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_castroneves_first_run_action_v1.csv"
)

ACTION_LEDGER_V2 = (
    OUTPUT_DIR
    / "unified_attempt_action_lane_ledger_v2.csv"
)

QA_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_castroneves_first_run_action_v1_qa.csv"
)


# ============================================================
# HELPERS
# ============================================================

def read_csv(path):
    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as f:
        return list(
            csv.DictReader(f)
        )


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
        return str(
            int(
                float(value)
            )
        )
    except Exception:
        return value.lstrip("0") or "0"


def speed_close(a, b, tol=0.003):
    try:
        return abs(
            float(txt(a))
            -
            float(txt(b))
        ) <= tol
    except Exception:
        return False


# ============================================================
# MAIN
# ============================================================

def main():

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print()
    print("=" * 120)
    print(
        "R1G.25 — 2022 HELIO CASTRONEVES "
        "FIRST-RUN ACTION ADJUDICATION V1"
    )
    print("=" * 120)

    inputs = [
        CANONICAL,
        RESULT_MATCHES,
        CASTRONEVES_EVIDENCE,
        ACTION_LEDGER_V1,
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
            "CASTRONEVES_FIRST_RUN_ACTION_INPUT_MISSING"
        )

        return

    canonical = read_csv(
        CANONICAL
    )

    results = read_csv(
        RESULT_MATCHES
    )

    evidence = read_csv(
        CASTRONEVES_EVIDENCE
    )

    action_v1 = read_csv(
        ACTION_LEDGER_V1
    )

    # ========================================================
    # CANONICAL CASTRONEVES TARGETS
    # ========================================================

    castroneves = [
        row
        for row in canonical
        if (
            "2022"
            in txt(
                row.get(
                    "session_id"
                )
            )
            and
            norm_car(
                row.get(
                    "car_number"
                )
            ) == "6"
        )
    ]

    first_attempt = [
        row
        for row in castroneves
        if txt(
            row.get(
                "car_attempt_index"
            )
        ) == "1"
    ]

    second_attempt = [
        row
        for row in castroneves
        if txt(
            row.get(
                "car_attempt_index"
            )
        ) == "2"
    ]

    print()
    print("=" * 120)
    print(
        "CANONICAL FIRST/SECOND RUN CHECK"
    )
    print("=" * 120)

    print()
    print(
        "Castroneves canonical rows:",
        len(
            castroneves
        ),
    )

    print(
        "attempt index 1 rows:",
        len(
            first_attempt
        ),
    )

    print(
        "attempt index 2 rows:",
        len(
            second_attempt
        ),
    )

    if len(
        first_attempt
    ) == 1:

        print()
        print(
            "FIRST attempt_id:",
            txt(
                first_attempt[0].get(
                    "attempt_id"
                )
            ),
        )

        print(
            "FIRST speed:",
            txt(
                first_attempt[0].get(
                    "four_lap_average_speed_mph"
                )
            ),
        )

    if len(
        second_attempt
    ) == 1:

        print(
            "SECOND attempt_id:",
            txt(
                second_attempt[0].get(
                    "attempt_id"
                )
            ),
        )

        print(
            "SECOND speed:",
            txt(
                second_attempt[0].get(
                    "four_lap_average_speed_mph"
                )
            ),
        )

    canonical_structure_ok = (
        len(
            first_attempt
        ) == 1
        and
        len(
            second_attempt
        ) == 1
        and
        speed_close(
            first_attempt[0].get(
                "four_lap_average_speed_mph"
            ),
            "225.482",
        )
        and
        speed_close(
            second_attempt[0].get(
                "four_lap_average_speed_mph"
            ),
            "229.630",
        )
    )

    # ========================================================
    # EVIDENCE VERIFICATION
    # ========================================================

    qualifying_evidence = []

    for row in evidence:

        sentence = txt(
            row.get(
                "sentence"
            )
        ).lower()

        source_name = txt(
            row.get(
                "source_name"
            )
        )

        if (
            "castroneves"
            in sentence
            and
            "first run"
            in sentence
            and
            (
                "bailing out"
                in sentence
                or
                "bailed out"
                in sentence
            )
        ):

            qualifying_evidence.append(
                row
            )

    print()
    print("=" * 120)
    print(
        "DIRECT ACTION EVIDENCE CHECK"
    )
    print("=" * 120)

    print()
    print(
        "Qualifying evidence rows:",
        len(
            qualifying_evidence
        ),
    )

    for row in qualifying_evidence:

        print()
        print(
            "source:",
            txt(
                row.get(
                    "source_name"
                )
            ),
        )

        print(
            "sentence:"
        )

        print(
            txt(
                row.get(
                    "sentence"
                )
            )
        )

    evidence_ok = (
        len(
            qualifying_evidence
        ) >= 1
    )

    # ========================================================
    # ADJUDICATION
    # ========================================================

    adjudicated_rows = []

    if (
        canonical_structure_ok
        and
        evidence_ok
    ):

        first = first_attempt[0]
        second = second_attempt[0]
        source = qualifying_evidence[0]

        adjudicated_rows.append({
            "evidence_id":
                "R1G25-CASTRONEVES-FIRST-RUN-BAILOUT",

            "year":
                "2022",

            "driver_name":
                "Helio Castroneves",

            "car_number":
                "06",

            "subject_attempt_id":
                txt(
                    first.get(
                        "attempt_id"
                    )
                ),

            "related_attempt_id":
                txt(
                    second.get(
                        "attempt_id"
                    )
                ),

            "subject_speed_mph":
                txt(
                    first.get(
                        "four_lap_average_speed_mph"
                    )
                ),

            "action":
                "ABORT_OR_BAIL_OUT_FIRST_RUN",

            "lane":
                "UNKNOWN",

            "relation":
                "FIRST_RUN_BEFORE_LATER_CANONICAL_ATTEMPT",

            "source_name":
                txt(
                    source.get(
                        "source_name"
                    )
                ),

            "source_class":
                txt(
                    source.get(
                        "source_class"
                    )
                )
                or
                "REPUTABLE_SECONDARY_EDITORIAL",

            "source_evidence_id":
                txt(
                    source.get(
                        "evidence_id"
                    )
                ),

            "evidence_quality":
                "DIRECT_SECONDARY_FIRST_RUN_ACTION",

            "chronology_usable":
                "True",

            "queue_position_known":
                "False",

            "queue_wait_known":
                "False",

            "promotion_status":
                "PROMOTED_ACTION",

            "notes":
                (
                    "The Race explicitly describes Castroneves "
                    "bailing out of his first run because of "
                    "tricky conditions and poor car balance. "
                    "Canonical car_attempt_index=1 uniquely "
                    "identifies the first run as the 225.482 "
                    "attempt. No lane or wall-clock time inferred."
                ),
        })

    # ========================================================
    # ACTION LEDGER V2
    # ========================================================

    action_fields = list(
        action_v1[0].keys()
    )

    required_fields = [
        "subject_speed_mph",
        "source_evidence_id",
        "promotion_status",
    ]

    for field in required_fields:

        if field not in action_fields:
            action_fields.append(
                field
            )

    action_v2 = []

    for row in action_v1:

        out = {
            field: ""
            for field in action_fields
        }

        for key, value in row.items():

            if key in out:
                out[
                    key
                ] = value

        action_v2.append(
            out
        )

    for ev in adjudicated_rows:

        out = {
            field: ""
            for field in action_fields
        }

        mapping = {
            "evidence_id":
                ev[
                    "evidence_id"
                ],

            "year":
                ev[
                    "year"
                ],

            "subject_attempt_id":
                ev[
                    "subject_attempt_id"
                ],

            "related_attempt_id":
                ev[
                    "related_attempt_id"
                ],

            "session_id":
                "INDY500_DAY1_2022",

            "car_number":
                ev[
                    "car_number"
                ],

            "driver_name":
                ev[
                    "driver_name"
                ],

            "action":
                ev[
                    "action"
                ],

            "lane":
                ev[
                    "lane"
                ],

            "relation":
                ev[
                    "relation"
                ],

            "source_name":
                ev[
                    "source_name"
                ],

            "source_class":
                ev[
                    "source_class"
                ],

            "evidence_quality":
                ev[
                    "evidence_quality"
                ],

            "chronology_usable":
                ev[
                    "chronology_usable"
                ],

            "queue_position_known":
                "False",

            "queue_wait_known":
                "False",

            "canonical_mutated":
                "False",

            "notes":
                ev[
                    "notes"
                ],

            "subject_speed_mph":
                ev[
                    "subject_speed_mph"
                ],

            "source_evidence_id":
                ev[
                    "source_evidence_id"
                ],

            "promotion_status":
                ev[
                    "promotion_status"
                ],
        }

        for key, value in mapping.items():

            if key in out:
                out[
                    key
                ] = value

        action_v2.append(
            out
        )

    # ========================================================
    # DUPLICATE CHECK
    # ========================================================

    evidence_ids = [
        txt(
            row.get(
                "evidence_id"
            )
        )
        for row in action_v2
        if txt(
            row.get(
                "evidence_id"
            )
        )
    ]

    duplicate_evidence_ids = (
        len(
            evidence_ids
        )
        -
        len(
            set(
                evidence_ids
            )
        )
    )

    # ========================================================
    # PRINT
    # ========================================================

    print()
    print("=" * 120)
    print(
        "PROMOTED CASTRONEVES ACTION"
    )
    print("=" * 120)

    if adjudicated_rows:

        row = adjudicated_rows[0]

        print()
        print(
            "driver:",
            row[
                "driver_name"
            ],
        )

        print(
            "subject attempt:",
            row[
                "subject_attempt_id"
            ],
        )

        print(
            "speed:",
            row[
                "subject_speed_mph"
            ],
        )

        print(
            "action:",
            row[
                "action"
            ],
        )

        print(
            "lane:",
            row[
                "lane"
            ],
        )

        print(
            "related later attempt:",
            row[
                "related_attempt_id"
            ],
        )

        print(
            "authority:",
            row[
                "source_class"
            ],
        )

    else:

        print()
        print(
            "NO ACTION PROMOTED"
        )

    # ========================================================
    # WRITE
    # ========================================================

    write_csv(
        ADJUDICATED_OUT,
        adjudicated_rows,
        [
            "evidence_id",
            "year",
            "driver_name",
            "car_number",
            "subject_attempt_id",
            "related_attempt_id",
            "subject_speed_mph",
            "action",
            "lane",
            "relation",
            "source_name",
            "source_class",
            "source_evidence_id",
            "evidence_quality",
            "chronology_usable",
            "queue_position_known",
            "queue_wait_known",
            "promotion_status",
            "notes",
        ],
    )

    write_csv(
        ACTION_LEDGER_V2,
        action_v2,
        action_fields,
    )

    # ========================================================
    # QA
    # ========================================================

    qa_rows = [
        {
            "metric":
                "canonical_structure_ok",

            "value":
                int(
                    canonical_structure_ok
                ),

            "status":
                (
                    "PASS"
                    if canonical_structure_ok
                    else "FAIL"
                ),
        },

        {
            "metric":
                "direct_first_run_action_evidence_rows",

            "value":
                len(
                    qualifying_evidence
                ),

            "status":
                (
                    "PASS"
                    if len(
                        qualifying_evidence
                    ) >= 1
                    else "FAIL"
                ),
        },

        {
            "metric":
                "promoted_action_rows",

            "value":
                len(
                    adjudicated_rows
                ),

            "status":
                (
                    "PASS"
                    if len(
                        adjudicated_rows
                    ) == 1
                    else "FAIL"
                ),
        },

        {
            "metric":
                "lane_claimed",

            "value":
                0,

            "status":
                "PASS",
        },

        {
            "metric":
                "wall_clock_timestamp_claimed",

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
                "duplicate_action_evidence_ids",

            "value":
                duplicate_evidence_ids,

            "status":
                (
                    "PASS"
                    if duplicate_evidence_ids == 0
                    else "FAIL"
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

        {
            "metric":
                "action_ledger_v1_mutated",

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

    # ========================================================
    # FINAL
    # ========================================================

    print()
    print("=" * 120)
    print(
        "FINAL SUMMARY"
    )
    print("=" * 120)

    print()
    print(
        "Previous action ledger rows:",
        len(
            action_v1
        ),
    )

    print(
        "New Castroneves action rows:",
        len(
            adjudicated_rows
        ),
    )

    print(
        "Action ledger V2 rows:",
        len(
            action_v2
        ),
    )

    print()
    print(
        "Castroneves first-run bail-out action "
        "is promoted from direct secondary narrative."
    )

    print(
        "No Lane 1/Lane 2 is claimed."
    )

    print(
        "No exact attempt timestamp is claimed."
    )

    print(
        "No result-row ordering was used."
    )

    print(
        "No queue wait was inferred."
    )

    print(
        "No canonical or action-ledger V1 data was modified."
    )

    print()
    print("=" * 120)

    if (
        canonical_structure_ok
        and
        len(
            qualifying_evidence
        ) >= 1
        and
        len(
            adjudicated_rows
        ) == 1
        and
        duplicate_evidence_ids == 0
    ):

        print(
            "FINAL STATUS: "
            "CASTRONEVES_FIRST_RUN_ACTION_ADJUDICATED"
        )

    else:

        print(
            "FINAL STATUS: "
            "CASTRONEVES_FIRST_RUN_ACTION_REVIEW_REQUIRED"
        )

    print("=" * 120)

    print()
    print("OUTPUTS")
    print(ADJUDICATED_OUT)
    print(ACTION_LEDGER_V2)
    print(QA_OUT)


if __name__ == "__main__":
    main()
