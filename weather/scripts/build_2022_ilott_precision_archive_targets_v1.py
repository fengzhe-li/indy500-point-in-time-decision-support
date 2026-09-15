from pathlib import Path
import csv
import re


PHASE = "R1G.26C"

ARCHIVE_TARGETS = Path(
    "weather/output/"
    "official_lane_queue_live_archive_targets_v1.csv"
)

R2A_REGISTRY = Path(
    "weather/output/"
    "official_lane_queue_live_resource_registry_v1.csv"
)

ILOTT_EVIDENCE = Path(
    "weather/output/"
    "chronology_rescue_2022_ilott_paragraph_local_adjudication_v1.csv"
)

CANONICAL = Path(
    "data/canonical/v1/attempts.csv"
)

RESULT_MATCH_V3 = Path(
    "weather/output/"
    "chronology_rescue_2022_result_to_canonical_attempt_matches_v3.csv"
)

OUTPUT_DIR = Path(
    "weather/output"
)

TARGET_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_ilott_precision_archive_targets_v1.csv"
)

LOCAL_MATCH_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_ilott_archive_target_local_matches_v1.csv"
)

SUMMARY_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_ilott_precision_archive_targets_summary_v1.csv"
)

QA_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_ilott_precision_archive_targets_v1_qa.csv"
)


SEARCH_QUERIES = [
    "Callum Ilott 230.212",
    "Callum Ilott 230.961",
    "Callum Ilott retired qualifying",
    "Callum Ilott second run",
    "Callum Ilott second attempt",
    "Callum Ilott another run",
    "Callum Ilott another attempt",
    "Callum Ilott rerun",
    "Callum Ilott re-run",
    "Callum Ilott late improver",
    "Callum Ilott May 21 2022 qualifying",
    "Callum Ilott Indianapolis 500 qualifying May 21 2022",
    "Juncos Hollinger Ilott qualifying second run",
    "Juncos Hollinger Ilott qualifying rerun",
    "Callum Ilott qualifying retired 230.212",
    "Callum Ilott qualifying 230.961",
]


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
        )
        writer.writeheader()
        writer.writerows(rows)


def normalize(s):
    return re.sub(
        r"\s+",
        " ",
        txt(s).lower(),
    ).strip()


def contains_ilott(text):
    lower = normalize(text)

    return (
        "callum ilott" in lower
        or
        re.search(r"\bilott\b", lower)
        is not None
    )


def contains_2022(text):
    return "2022" in normalize(text)


def contains_any(text, terms):
    lower = normalize(text)

    return any(
        term.lower() in lower
        for term in terms
    )


def main():

    print()
    print("=" * 120)
    print(
        "R1G.26C — 2022 CALLUM ILOTT "
        "PRECISION ARCHIVE TARGET BUILD V1"
    )
    print("=" * 120)

    required = [
        ILOTT_EVIDENCE,
        CANONICAL,
        RESULT_MATCH_V3,
    ]

    optional = [
        ARCHIVE_TARGETS,
        R2A_REGISTRY,
    ]

    missing = []

    print()
    print("INPUT CHECK")
    print("-" * 120)

    for path in required:
        exists = path.exists()

        print(
            f"{path}: "
            f"{'PRESENT' if exists else 'MISSING'}"
        )

        if not exists:
            missing.append(path)

    for path in optional:
        print(
            f"{path}: "
            f"{'PRESENT' if path.exists() else 'MISSING_OPTIONAL'}"
        )

    if missing:
        print()
        print(
            "FINAL STATUS: "
            "ILOTT_PRECISION_ARCHIVE_TARGET_INPUT_MISSING"
        )
        return

    canonical = read_csv(
        CANONICAL
    )

    result_v3 = read_csv(
        RESULT_MATCH_V3
    )

    ilott_evidence = read_csv(
        ILOTT_EVIDENCE
    )

    # ========================================================
    # CANONICAL TARGETS
    # ========================================================

    ilott_attempts = [
        row
        for row in canonical
        if (
            txt(
                row.get("year")
            ) == "2022"
            and
            txt(
                row.get("driver_name")
            ) == "Callum Ilott"
        )
    ]

    ilott_attempts = sorted(
        ilott_attempts,
        key=lambda row: int(
            txt(
                row.get(
                    "car_attempt_index"
                )
            )
            or "999"
        ),
    )

    result_by_id = {
        txt(
            row.get("attempt_id")
        ): row
        for row in result_v3
        if txt(
            row.get("attempt_id")
        )
    }

    print()
    print("=" * 120)
    print(
        "ILOTT ATTEMPT TARGETS"
    )
    print("=" * 120)

    for row in ilott_attempts:

        aid = txt(
            row.get(
                "attempt_id"
            )
        )

        linked = result_by_id.get(
            aid,
            {},
        )

        print()
        print(
            "attempt_id:",
            aid,
        )

        print(
            "  index:",
            txt(
                row.get(
                    "car_attempt_index"
                )
            ),
        )

        print(
            "  canonical speed:",
            txt(
                row.get(
                    "four_lap_average_speed_mph"
                )
            ),
        )

        print(
            "  official row:",
            txt(
                linked.get(
                    "official_result_row"
                )
            ),
        )

        print(
            "  official status:",
            repr(
                txt(
                    linked.get(
                        "official_status"
                    )
                )
            ),
        )

    # ========================================================
    # BUILD QUERY TARGETS
    # ========================================================

    target_rows = []

    for i, query in enumerate(
        SEARCH_QUERIES,
        start=1,
    ):

        target_rows.append({
            "target_id":
                f"R1G26C-Q{i:03d}",

            "target_type":
                "PRECISION_WEB_ARCHIVE_QUERY",

            "query":
                query,

            "driver":
                "Callum Ilott",

            "year":
                "2022",

            "priority":
                (
                    "HIGH"
                    if any(
                        token in query
                        for token in [
                            "230.212",
                            "230.961",
                            "second run",
                            "second attempt",
                            "rerun",
                            "retired",
                        ]
                    )
                    else "MEDIUM"
                ),

            "goal":
                (
                    "Recover direct evidence for repeat-attempt "
                    "ordering/action semantics without inferring "
                    "Lane or queue state."
                ),

            "promotion_policy":
                (
                    "Discovery only. Requires separate adjudication."
                ),
        })

    # ========================================================
    # CROSS-CHECK R2A ARCHIVE TARGETS
    # ========================================================

    local_matches = []

    if ARCHIVE_TARGETS.exists():

        archive_rows = read_csv(
            ARCHIVE_TARGETS
        )

        for i, row in enumerate(
            archive_rows,
            start=1,
        ):

            joined = " | ".join(
                txt(v)
                for v in row.values()
            )

            score = 0
            reasons = []

            if contains_ilott(
                joined
            ):
                score += 5
                reasons.append(
                    "DIRECT_ILOTT"
                )

            if contains_2022(
                joined
            ):
                score += 2
                reasons.append(
                    "YEAR_2022"
                )

            if contains_any(
                joined,
                [
                    "qualifying",
                    "qualification",
                    "day 1",
                    "day1",
                    "session 6033",
                    "6033",
                ],
            ):
                score += 2
                reasons.append(
                    "DAY1_QUALIFYING_CONTEXT"
                )

            if contains_any(
                joined,
                [
                    "leaderboard",
                    "timing",
                    "scoring",
                    "qualification_order",
                    "archive",
                    "wayback",
                ],
            ):
                score += 1
                reasons.append(
                    "ARCHIVE_OR_TIMING_RELEVANCE"
                )

            if score > 0:

                local_matches.append({
                    "source":
                        "R2A_ARCHIVE_TARGETS",

                    "source_row":
                        i,

                    "score":
                        score,

                    "reasons":
                        "|".join(
                            reasons
                        ),

                    "row_text":
                        joined,
                })

    # ========================================================
    # CROSS-CHECK R2A REGISTRY
    # ========================================================

    if R2A_REGISTRY.exists():

        registry_rows = read_csv(
            R2A_REGISTRY
        )

        for i, row in enumerate(
            registry_rows,
            start=1,
        ):

            joined = " | ".join(
                txt(v)
                for v in row.values()
            )

            score = 0
            reasons = []

            if contains_ilott(
                joined
            ):
                score += 5
                reasons.append(
                    "DIRECT_ILOTT"
                )

            if contains_2022(
                joined
            ):
                score += 2
                reasons.append(
                    "YEAR_2022"
                )

            if contains_any(
                joined,
                [
                    "qualification_order",
                    "leaderboard",
                    "timing",
                    "scoring",
                    "session",
                ],
            ):
                score += 1
                reasons.append(
                    "RESOURCE_RELEVANCE"
                )

            if score > 0:

                local_matches.append({
                    "source":
                        "R2A_RESOURCE_REGISTRY",

                    "source_row":
                        i,

                    "score":
                        score,

                    "reasons":
                        "|".join(
                            reasons
                        ),

                    "row_text":
                        joined,
                })

    local_matches = sorted(
        local_matches,
        key=lambda row: (
            -int(
                row["score"]
            ),
            row["source"],
            row["source_row"],
        ),
    )

    # ========================================================
    # KNOWN EVIDENCE BASELINE
    # ========================================================

    late_rows = [
        row
        for row in ilott_evidence
        if txt(
            row.get(
                "classification"
            )
        )
        ==
        "DIRECT_LATE_IMPROVEMENT_ONLY"
    ]

    direct_repeat_rows = [
        row
        for row in ilott_evidence
        if txt(
            row.get(
                "repeat_promotable"
            )
        )
        ==
        "True"
    ]

    direct_action_rows = [
        row
        for row in ilott_evidence
        if txt(
            row.get(
                "action_promotable"
            )
        )
        ==
        "True"
    ]

    direct_lane_rows = [
        row
        for row in ilott_evidence
        if txt(
            row.get(
                "lane_promotable"
            )
        )
        ==
        "True"
    ]

    # ========================================================
    # PRINT
    # ========================================================

    print()
    print("=" * 120)
    print(
        "PRECISION ARCHIVE QUERIES"
    )
    print("=" * 120)

    for row in target_rows:

        print()
        print(
            row[
                "target_id"
            ],
            "|",
            row[
                "priority"
            ],
        )

        print(
            row[
                "query"
            ]
        )

    print()
    print("=" * 120)
    print(
        "R2A LOCAL ARCHIVE / RESOURCE MATCHES"
    )
    print("=" * 120)

    print()
    print(
        "Matches:",
        len(
            local_matches
        ),
    )

    for row in local_matches[:30]:

        print()
        print(
            row[
                "source"
            ],
            "| score",
            row[
                "score"
            ],
            "|",
            row[
                "reasons"
            ],
        )

        print(
            row[
                "row_text"
            ]
        )

    # ========================================================
    # WRITE
    # ========================================================

    write_csv(
        TARGET_OUT,
        target_rows,
        [
            "target_id",
            "target_type",
            "query",
            "driver",
            "year",
            "priority",
            "goal",
            "promotion_policy",
        ],
    )

    write_csv(
        LOCAL_MATCH_OUT,
        local_matches,
        [
            "source",
            "source_row",
            "score",
            "reasons",
            "row_text",
        ],
    )

    summary_rows = [
        {
            "metric":
                "canonical_ilott_attempts",

            "value":
                len(
                    ilott_attempts
                ),
        },

        {
            "metric":
                "precision_queries",

            "value":
                len(
                    target_rows
                ),
        },

        {
            "metric":
                "r2a_local_matches",

            "value":
                len(
                    local_matches
                ),
        },

        {
            "metric":
                "known_late_improvement_evidence",

            "value":
                len(
                    late_rows
                ),
        },

        {
            "metric":
                "known_direct_repeat_evidence",

            "value":
                len(
                    direct_repeat_rows
                ),
        },

        {
            "metric":
                "known_direct_action_evidence",

            "value":
                len(
                    direct_action_rows
                ),
        },

        {
            "metric":
                "known_direct_lane_evidence",

            "value":
                len(
                    direct_lane_rows
                ),
        },

        {
            "metric":
                "recommended_next_stage",

            "value":
                "PRECISION_ARCHIVE_RETRIEVAL",
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
                "car_number_used_as_identity_key",

            "value":
                0,

            "status":
                "PASS",
        },

        {
            "metric":
                "result_match_v3_used",

            "value":
                1,

            "status":
                "PASS",
        },

        {
            "metric":
                "automatic_promotions",

            "value":
                0,

            "status":
                "PASS",
        },

        {
            "metric":
                "lane_inference_from_retired",

            "value":
                0,

            "status":
                "PASS",
        },

        {
            "metric":
                "queue_wait_inference",

            "value":
                0,

            "status":
                "PASS",
        },

        {
            "metric":
                "results_row_order_used_as_chronology",

            "value":
                0,

            "status":
                "PASS",
        },

        {
            "metric":
                "canonical_mutated",

            "value":
                0,

            "status":
                "PASS",
        },

        {
            "metric":
                "phase5_to_phase8_mutated",

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
    print(
        "FINAL SUMMARY"
    )
    print("=" * 120)

    print()
    print(
        "Precision archive queries:",
        len(
            target_rows
        ),
    )

    print(
        "R2A local archive/resource matches:",
        len(
            local_matches
        ),
    )

    print(
        "Known late-improvement evidence:",
        len(
            late_rows
        ),
    )

    print(
        "Known direct repeat evidence:",
        len(
            direct_repeat_rows
        ),
    )

    print(
        "Known direct action evidence:",
        len(
            direct_action_rows
        ),
    )

    print(
        "Known direct lane evidence:",
        len(
            direct_lane_rows
        ),
    )

    print()
    print(
        "No evidence was promoted."
    )

    print(
        "No canonical or Phase 5–8 data was modified."
    )

    print()
    print("=" * 120)
    print(
        "FINAL STATUS: "
        "ILOTT_PRECISION_ARCHIVE_TARGETS_READY"
    )
    print("=" * 120)

    print()
    print("OUTPUTS")
    print(TARGET_OUT)
    print(LOCAL_MATCH_OUT)
    print(SUMMARY_OUT)
    print(QA_OUT)


if __name__ == "__main__":
    main()
