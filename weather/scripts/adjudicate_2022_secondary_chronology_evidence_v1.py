from pathlib import Path
import csv


# ============================================================
# INPUTS
# ============================================================

CANDIDATES = Path(
    "weather/output/"
    "chronology_rescue_2022_secondary_editorial_candidates_v1.csv"
)

RESULT_MATCHES = Path(
    "weather/output/"
    "chronology_rescue_2022_result_to_canonical_attempt_matches_v2.csv"
)

WEATHER_WINDOWS = Path(
    "weather/output/"
    "chronology_rescue_2022_weather_interruption_windows_v1.csv"
)


# ============================================================
# OUTPUTS
# ============================================================

OUTPUT_DIR = Path("weather/output")

ADJUDICATED_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_secondary_adjudicated_evidence_v1.csv"
)

ACTION_LANE_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_action_lane_evidence_v1.csv"
)

ORDERING_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_secondary_ordering_edges_v1.csv"
)

REJECTED_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_secondary_rejected_candidates_v1.csv"
)

QA_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_secondary_adjudicated_evidence_v1_qa.csv"
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
    t = txt(v)

    if not t:
        return ""

    try:
        return str(int(float(t)))
    except Exception:
        return t.lstrip("0") or "0"


def speed_close(a, b, tol=0.002):
    try:
        return abs(
            float(txt(a))
            -
            float(txt(b))
        ) <= tol
    except Exception:
        return False


def find_result(
    rows,
    car,
    speed=None,
    status=None,
):
    matches = []

    for row in rows:

        if norm_car(
            row.get("car_number")
        ) != norm_car(car):
            continue

        if speed is not None:

            if not speed_close(
                row.get("official_speed_mph"),
                speed,
            ):
                continue

        if status is not None:

            if txt(
                row.get("official_status")
            ) != status:
                continue

        matches.append(row)

    return matches


def candidate_by_id(rows, candidate_id):
    matches = [
        row
        for row in rows
        if txt(
            row.get("candidate_id")
        ) == candidate_id
    ]

    return (
        matches[0]
        if len(matches) == 1
        else None
    )


def contains_all(text, terms):
    lower = txt(text).lower()

    return all(
        term.lower() in lower
        for term in terms
    )


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
        "R1G.19 — 2022 SECONDARY EDITORIAL "
        "EVIDENCE ADJUDICATION V1"
    )
    print("=" * 120)

    inputs = [
        CANDIDATES,
        RESULT_MATCHES,
        WEATHER_WINDOWS,
    ]

    missing = []

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
            "2022_SECONDARY_EVIDENCE_ADJUDICATION_INPUT_MISSING"
        )
        return

    candidates = read_csv(CANDIDATES)
    results = read_csv(RESULT_MATCHES)
    weather = read_csv(WEATHER_WINDOWS)

    print()
    print(
        "SECONDARY CANDIDATES:",
        len(candidates),
    )

    print(
        "RESULT LINKS:",
        len(results),
    )

    # ========================================================
    # REQUIRED CANONICAL RESULT LINKS
    # ========================================================

    mcl_first = find_result(
        results,
        car="3",
        speed="231.543",
        status="Withdrawn",
    )

    mcl_second = find_result(
        results,
        car="3",
        speed="230.154",
    )

    rossi_first = find_result(
        results,
        car="27",
        speed="231.341",
        status="Withdrawn",
    )

    rossi_second = find_result(
        results,
        car="27",
        speed="230.812",
    )

    print()
    print("=" * 120)
    print("CANONICAL TARGET CHECK")
    print("=" * 120)

    print(
        "McLaughlin 231.543 Withdrawn:",
        len(mcl_first),
    )

    print(
        "McLaughlin 230.154:",
        len(mcl_second),
    )

    print(
        "Rossi 231.341 Withdrawn:",
        len(rossi_first),
    )

    print(
        "Rossi 230.812:",
        len(rossi_second),
    )

    if not all([
        len(mcl_first) == 1,
        len(mcl_second) == 1,
        len(rossi_first) == 1,
        len(rossi_second) == 1,
    ]):

        print()
        print(
            "FINAL STATUS: "
            "2022_SECONDARY_EVIDENCE_CANONICAL_TARGET_REVIEW_REQUIRED"
        )
        return

    # ========================================================
    # REQUIRED SECONDARY CANDIDATES
    # ========================================================

    karam_candidate = candidate_by_id(
        candidates,
        "R1G18-C0015",
    )

    mcl_candidate = candidate_by_id(
        candidates,
        "R1G18-C0016",
    )

    rossi_nbc = candidate_by_id(
        candidates,
        "R1G18-C0029",
    )

    rossi_race = candidate_by_id(
        candidates,
        "R1G18-C0020",
    )

    print()
    print("=" * 120)
    print("CANDIDATE VERIFICATION")
    print("=" * 120)

    checks = {
        "KARAM_RESTART":
            (
                karam_candidate is not None
                and
                contains_all(
                    karam_candidate.get(
                        "candidate_sentence"
                    ),
                    [
                        "track re-opened",
                        "sage karam",
                        "unable to improve",
                    ],
                )
            ),

        "MCLAUGHLIN_LANE1":
            (
                mcl_candidate is not None
                and
                contains_all(
                    mcl_candidate.get(
                        "candidate_sentence"
                    ),
                    [
                        "scott mclaughlin",
                        "gave his 15th place time",
                        "lane 1",
                    ],
                )
            ),

        "ROSSI_NBC_SECOND_ATTEMPT":
            (
                rossi_nbc is not None
                and
                contains_all(
                    rossi_nbc.get(
                        "candidate_sentence"
                    ),
                    [
                        "rossi",
                        "attempted to improve",
                        "later",
                    ],
                )
            ),

        "ROSSI_RACE_SECOND_RUN":
            (
                rossi_race is not None
                and
                contains_all(
                    rossi_race.get(
                        "candidate_sentence"
                    ),
                    [
                        "rossi",
                        "first run",
                        "second run",
                    ],
                )
            ),
    }

    for key, value in checks.items():
        print(
            key,
            ":",
            "PASS" if value else "FAIL",
        )

    if not all(checks.values()):

        print()
        print(
            "FINAL STATUS: "
            "2022_SECONDARY_EVIDENCE_CANDIDATE_VERIFICATION_FAILED"
        )
        return

    # ========================================================
    # ADJUDICATED EVIDENCE
    # ========================================================

    adjudicated = []

    # --------------------------------------------------------
    # McLaughlin — direct historical Lane 1 evidence
    # --------------------------------------------------------

    adjudicated.append({
        "evidence_id":
            "R1G19-MCLAUGHLIN-LANE1",

        "year":
            "2022",

        "driver_name":
            "Scott McLaughlin",

        "car_number":
            "3",

        "subject_attempt_id":
            txt(
                mcl_first[0].get(
                    "attempt_id"
                )
            ),

        "related_attempt_id":
            txt(
                mcl_second[0].get(
                    "attempt_id"
                )
            ),

        "evidence_type":
            "ACTION_LANE",

        "action":
            "WITHDRAW_EXISTING_RESULT_AND_USE_LANE1",

        "lane":
            "LANE_1",

        "relation":
            "FIRST_ATTEMPT_WITHDRAWN_BEFORE_RERUN",

        "time_lower_utc":
            "",

        "time_upper_utc":
            "",

        "source_id":
            txt(
                mcl_candidate.get(
                    "source_id"
                )
            ),

        "source_name":
            txt(
                mcl_candidate.get(
                    "source_name"
                )
            ),

        "source_class":
            "REPUTABLE_SECONDARY_EDITORIAL",

        "source_candidate_id":
            "R1G18-C0016",

        "evidence_quality":
            "DIRECT_SECONDARY_NARRATIVE",

        "promotion_status":
            "PROMOTED",

        "notes":
            (
                "Direct secondary narrative states McLaughlin "
                "gave up his existing P15 time to move to the "
                "front of the Lane 1 queue. Lane use is not "
                "inferred from Withdrawn status."
            ),
    })

    # --------------------------------------------------------
    # Rossi — first run -> second run
    # --------------------------------------------------------

    adjudicated.append({
        "evidence_id":
            "R1G19-ROSSI-FIRST-SECOND",

        "year":
            "2022",

        "driver_name":
            "Alexander Rossi",

        "car_number":
            "27",

        "subject_attempt_id":
            txt(
                rossi_first[0].get(
                    "attempt_id"
                )
            ),

        "related_attempt_id":
            txt(
                rossi_second[0].get(
                    "attempt_id"
                )
            ),

        "evidence_type":
            "ORDERING",

        "action":
            "SECOND_ATTEMPT",

        "lane":
            "UNKNOWN",

        "relation":
            "FIRST_ATTEMPT_BEFORE_SECOND_ATTEMPT",

        "time_lower_utc":
            "",

        "time_upper_utc":
            "",

        "source_id":
            (
                txt(
                    rossi_nbc.get(
                        "source_id"
                    )
                )
                + "|"
                +
                txt(
                    rossi_race.get(
                        "source_id"
                    )
                )
            ),

        "source_name":
            "NBC Sports|The Race",

        "source_class":
            "REPUTABLE_SECONDARY_EDITORIAL",

        "source_candidate_id":
            "R1G18-C0029|R1G18-C0020",

        "evidence_quality":
            "CORROBORATED_SECONDARY_NARRATIVE",

        "promotion_status":
            "PROMOTED",

        "notes":
            (
                "NBC states Rossi attempted to improve later and "
                "fell from P17 to P21; The Race explicitly contrasts "
                "his first run with his second run. Official Results "
                "identify the unique 231.341 Withdrawn and 230.812 "
                "complete runs. No wall-clock time or lane is inferred."
            ),
    })

    # --------------------------------------------------------
    # Karam — event-level only, intentionally no attempt_id
    # --------------------------------------------------------

    adjudicated.append({
        "evidence_id":
            "R1G19-KARAM-POST-RESTART-EVENT",

        "year":
            "2022",

        "driver_name":
            "Sage Karam",

        "car_number":
            "24",

        "subject_attempt_id":
            "",

        "related_attempt_id":
            "",

        "evidence_type":
            "EVENT_ORDERING",

        "action":
            "POST_RESTART_ATTEMPT_EVENT",

        "lane":
            "UNKNOWN",

        "relation":
            "FIRST_WEATHER_HOLD_LIFTED_BEFORE_KARAM_ATTEMPT_EVENT",

        "time_lower_utc":
            "2022-05-21T19:34:00Z",

        "time_upper_utc":
            "",

        "source_id":
            txt(
                karam_candidate.get(
                    "source_id"
                )
            ),

        "source_name":
            txt(
                karam_candidate.get(
                    "source_name"
                )
            ),

        "source_class":
            "REPUTABLE_SECONDARY_EDITORIAL",

        "source_candidate_id":
            "R1G18-C0015",

        "evidence_quality":
            "DIRECT_SECONDARY_EVENT_NARRATIVE",

        "promotion_status":
            "PROMOTED_EVENT_ONLY",

        "notes":
            (
                "The Race states that when the track reopened, "
                "Karam was unable to improve. This proves a "
                "post-restart Karam attempt event, but current "
                "evidence does not uniquely identify which Karam "
                "canonical result row corresponds to that event."
            ),
    })

    # ========================================================
    # ACTION / LANE TABLE
    # ========================================================

    action_lane_rows = [
        row
        for row in adjudicated
        if row[
            "evidence_type"
        ] == "ACTION_LANE"
    ]

    # ========================================================
    # ORDERING EDGES
    # ========================================================

    ordering_rows = [
        {
            "edge_id":
                "R1G19-EDGE-ROSSI-1-2",

            "from_attempt_id":
                txt(
                    rossi_first[0].get(
                        "attempt_id"
                    )
                ),

            "relation":
                "BEFORE",

            "to_attempt_id":
                txt(
                    rossi_second[0].get(
                        "attempt_id"
                    )
                ),

            "from_event":
                "",

            "to_event":
                "",

            "source_authority":
                "REPUTABLE_SECONDARY_EDITORIAL",

            "constraint_class":
                "ORDERING_ONLY",

            "notes":
                (
                    "Corroborated Rossi first-run to second-run "
                    "ordering. No wall-clock time inferred."
                ),
        },

        {
            "edge_id":
                "R1G19-EDGE-KARAM-RESTART",

            "from_attempt_id":
                "",

            "relation":
                "BEFORE",

            "to_attempt_id":
                "",

            "from_event":
                "FIRST_WEATHER_HOLD_LIFTED",

            "to_event":
                "KARAM_POST_RESTART_ATTEMPT_EVENT",

            "source_authority":
                "REPUTABLE_SECONDARY_EDITORIAL",

            "constraint_class":
                "ORDERING_ONLY",

            "notes":
                (
                    "Karam event remains event-level because "
                    "specific canonical Karam attempt is unresolved."
                ),
        },
    ]

    # ========================================================
    # REJECT FALSE POSITIVES
    # ========================================================

    false_positive_ids = {
        "R1G18-C0005",
        "R1G18-C0006",
        "R1G18-C0007",
        "R1G18-C0008",
        "R1G18-C0009",
        "R1G18-C0010",
        "R1G18-C0011",
        "R1G18-C0012",
        "R1G18-C0013",
        "R1G18-C0014",
    }

    rejected = []

    for candidate in candidates:

        cid = txt(
            candidate.get(
                "candidate_id"
            )
        )

        if cid not in false_positive_ids:
            continue

        rejected.append({
            "candidate_id":
                cid,

            "driver_name":
                txt(
                    candidate.get(
                        "driver_name"
                    )
                ),

            "source_id":
                txt(
                    candidate.get(
                        "source_id"
                    )
                ),

            "candidate_sentence":
                txt(
                    candidate.get(
                        "candidate_sentence"
                    )
                ),

            "rejection_reason":
                "CONTEXT_JOIN_FALSE_POSITIVE",

            "promotion_status":
                "REJECTED",

            "notes":
                (
                    "Driver name occurs in an adjacent final-grid "
                    "listing, while the later generic statement about "
                    "'a handful of second-runs' does not identify this "
                    "driver individually. No driver-specific chronology "
                    "may be inferred."
                ),
        })

    # ========================================================
    # PRINT
    # ========================================================

    print()
    print("=" * 120)
    print("PROMOTED SECONDARY EVIDENCE")
    print("=" * 120)

    for row in adjudicated:

        print()
        print(
            row[
                "evidence_id"
            ]
        )

        print(
            "  driver:",
            row[
                "driver_name"
            ],
        )

        print(
            "  type:",
            row[
                "evidence_type"
            ],
        )

        print(
            "  action:",
            row[
                "action"
            ],
        )

        print(
            "  lane:",
            row[
                "lane"
            ],
        )

        print(
            "  relation:",
            row[
                "relation"
            ],
        )

        print(
            "  subject attempt:",
            row[
                "subject_attempt_id"
            ],
        )

        print(
            "  related attempt:",
            row[
                "related_attempt_id"
            ],
        )

    print()
    print("=" * 120)
    print("REJECTED CONTEXT-JOIN FALSE POSITIVES")
    print("=" * 120)

    print(
        "Rejected candidates:",
        len(rejected),
    )

    for row in rejected:

        print(
            " ",
            row[
                "candidate_id"
            ],
            "|",
            row[
                "driver_name"
            ],
        )

    # ========================================================
    # WRITE
    # ========================================================

    adjudicated_fields = [
        "evidence_id",
        "year",
        "driver_name",
        "car_number",
        "subject_attempt_id",
        "related_attempt_id",
        "evidence_type",
        "action",
        "lane",
        "relation",
        "time_lower_utc",
        "time_upper_utc",
        "source_id",
        "source_name",
        "source_class",
        "source_candidate_id",
        "evidence_quality",
        "promotion_status",
        "notes",
    ]

    write_csv(
        ADJUDICATED_OUT,
        adjudicated,
        adjudicated_fields,
    )

    write_csv(
        ACTION_LANE_OUT,
        action_lane_rows,
        adjudicated_fields,
    )

    write_csv(
        ORDERING_OUT,
        ordering_rows,
        [
            "edge_id",
            "from_attempt_id",
            "relation",
            "to_attempt_id",
            "from_event",
            "to_event",
            "source_authority",
            "constraint_class",
            "notes",
        ],
    )

    write_csv(
        REJECTED_OUT,
        rejected,
        [
            "candidate_id",
            "driver_name",
            "source_id",
            "candidate_sentence",
            "rejection_reason",
            "promotion_status",
            "notes",
        ],
    )

    # ========================================================
    # QA
    # ========================================================

    lane1_rows = [
        row
        for row in action_lane_rows
        if row[
            "lane"
        ] == "LANE_1"
    ]

    rossi_edges = [
        row
        for row in ordering_rows
        if row[
            "edge_id"
        ] == "R1G19-EDGE-ROSSI-1-2"
    ]

    karam_attempt_id_promotions = [
        row
        for row in adjudicated
        if (
            row[
                "driver_name"
            ] == "Sage Karam"
            and
            (
                row[
                    "subject_attempt_id"
                ]
                or
                row[
                    "related_attempt_id"
                ]
            )
        )
    ]

    qa = [
        {
            "metric":
                "promoted_secondary_evidence_rows",
            "value":
                len(adjudicated),
            "status":
                (
                    "PASS"
                    if len(adjudicated) == 3
                    else "FAIL"
                ),
        },
        {
            "metric":
                "mclaughlin_lane1_rows",
            "value":
                len(lane1_rows),
            "status":
                (
                    "PASS"
                    if len(lane1_rows) == 1
                    else "FAIL"
                ),
        },
        {
            "metric":
                "rossi_ordering_edges",
            "value":
                len(rossi_edges),
            "status":
                (
                    "PASS"
                    if len(rossi_edges) == 1
                    else "FAIL"
                ),
        },
        {
            "metric":
                "karam_specific_attempt_promotions",
            "value":
                len(karam_attempt_id_promotions),
            "status":
                (
                    "PASS"
                    if len(karam_attempt_id_promotions) == 0
                    else "FAIL"
                ),
        },
        {
            "metric":
                "context_join_false_positives_rejected",
            "value":
                len(rejected),
            "status":
                (
                    "PASS"
                    if len(rejected) == 10
                    else "REVIEW"
                ),
        },
        {
            "metric":
                "lane_inferred_from_withdrawn_status",
            "value":
                0,
            "status":
                "PASS",
        },
        {
            "metric":
                "queue_position_inferred",
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
        qa,
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
    print("FINAL SUMMARY")
    print("=" * 120)

    print()
    print(
        "Promoted secondary evidence rows:",
        len(adjudicated),
    )

    print(
        "Historical Lane 1 evidence rows:",
        len(lane1_rows),
    )

    print(
        "New Rossi ordering edges:",
        len(rossi_edges),
    )

    print(
        "Karam specific attempt promotions:",
        len(karam_attempt_id_promotions),
    )

    print(
        "Context-join false positives rejected:",
        len(rejected),
    )

    print()
    print(
        "McLaughlin Lane 1 is supported by direct "
        "secondary narrative, not inferred from Withdrawn."
    )

    print(
        "Rossi first-to-second attempt ordering is promoted "
        "without inventing a timestamp or lane."
    )

    print(
        "Karam remains event-level only."
    )

    print(
        "No queue position or queue wait was inferred."
    )

    print(
        "No canonical data was modified."
    )

    print()
    print("=" * 120)

    if (
        len(adjudicated) == 3
        and
        len(lane1_rows) == 1
        and
        len(rossi_edges) == 1
        and
        len(karam_attempt_id_promotions) == 0
    ):

        print(
            "FINAL STATUS: "
            "2022_SECONDARY_CHRONOLOGY_EVIDENCE_ADJUDICATED"
        )

    else:

        print(
            "FINAL STATUS: "
            "2022_SECONDARY_CHRONOLOGY_EVIDENCE_REVIEW_REQUIRED"
        )

    print("=" * 120)

    print()
    print("OUTPUTS")
    print(ADJUDICATED_OUT)
    print(ACTION_LANE_OUT)
    print(ORDERING_OUT)
    print(REJECTED_OUT)
    print(QA_OUT)


if __name__ == "__main__":
    main()
