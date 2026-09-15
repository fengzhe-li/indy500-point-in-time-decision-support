from pathlib import Path
import csv
from collections import Counter


PHASE = "R3A.1B"

DECISION_STATE = Path(
    "weather/output/"
    "contemporaneous_decision_state_evidence_ledger_v2.csv"
)

QUEUE = Path(
    "weather/output/"
    "queue_requeue_evidence_ledger_v1.csv"
)

STATE_V2 = Path(
    "weather/output/"
    "decision_time_observable_state_v2.csv"
)

OUTPUT_DIR = Path("weather/output")

AUDIT_OUT = (
    OUTPUT_DIR
    / "decision_time_state_v2_temporal_admissibility_audit_v1.csv"
)

QA_OUT = (
    OUTPUT_DIR
    / "decision_time_state_v2_temporal_admissibility_audit_v1_qa.csv"
)


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


def classify_decision_row(row):

    stage = txt(
        row.get("state_stage")
    ).upper()

    semantic = txt(
        row.get("source_semantic")
    ).upper()

    combined = (
        stage
        +
        " "
        +
        semantic
    )

    # Explicitly before the historical action.
    if (
        "PRE_ACTION"
        in combined
        or
        "BEFORE_LANE1_ACTION"
        in combined
        or
        "BEFORE_SECOND"
        in combined
    ):
        return (
            "PRE_DECISION_ADMISSIBLE",
            (
                "Source semantic explicitly places this "
                "state before the historical action/repeat."
            ),
        )

    # Anything explicitly produced after the repeat/rerun
    # is future information for a pre-repeat decision state.
    future_terms = [
        "POST_REPEAT",
        "POST_REATTEMPT",
        "POST_RERUN",
        "POST_SECOND",
        "POST_SATO",
        "DISPLACED",
        "LATER_TEMPORAL",
        "AFTER_REPEAT",
        "AFTER_RERUN",
    ]

    if any(
        term in combined
        for term in future_terms
    ):
        return (
            "POST_ACTION_NOT_ADMISSIBLE",
            (
                "Evidence describes a state reached after "
                "the repeat/rerun action and therefore cannot "
                "be an input to the earlier decision."
            ),
        )

    # An existing result can be admissible if the wording
    # is clearly pre-action, otherwise do not guess.
    if "EXISTING_RESULT" in combined:
        return (
            "REVIEW_REQUIRED",
            (
                "Existing-result evidence may be pre-decision "
                "but lacks an explicit temporal qualifier under "
                "the generic rule."
            ),
        )

    return (
        "REVIEW_REQUIRED",
        (
            "Temporal relationship to the decision point is "
            "not explicit enough for automatic promotion."
        ),
    )


def classify_queue_row(row):

    family = txt(
        row.get("evidence_family")
    ).upper()

    semantic = txt(
        row.get("state_semantic")
    ).upper()

    combined = (
        family
        +
        " "
        +
        semantic
    )

    # Explicitly after withdrawal/action.
    if (
        "AFTER_WITHDRAWING"
        in combined
        or
        "AFTER_WITHDRAW"
        in combined
    ):
        return (
            "TRANSITION_EVIDENCE_ONLY",
            (
                "Queue state occurs after the driver chose "
                "to withdraw the existing result. It is an "
                "action consequence, not a pre-action input."
            ),
        )

    # Run-order evidence is not queue state.
    if (
        "RETAKE_RUN_ORDER"
        in combined
        or
        "RELATIVE_RUN_ORDER"
        in combined
        or
        "FIRST_RETAKE_RUN"
        in combined
        or
        "_BEFORE_"
        in combined
    ):
        return (
            "ORDERING_EVIDENCE_ONLY",
            (
                "Evidence supports run ordering only; it does "
                "not establish a pre-decision queue state."
            ),
        )

    # 'Put in line for repeat' is evidence after the team
    # has already entered the repeat process.
    if (
        "PUT_IN_LINE"
        in combined
        or
        "FOR_REPEAT_RUN"
        in combined
        or
        "FOR_REATTEMPT"
        in combined
    ):
        return (
            "TRANSITION_EVIDENCE_ONLY",
            (
                "Generic line membership belongs to the repeat/"
                "reattempt process after action commitment, not "
                "to the state before choosing the action."
            ),
        )

    return (
        "REVIEW_REQUIRED",
        (
            "Queue evidence cannot be proven to exist before "
            "the historical decision point."
        ),
    )


def main():

    print()
    print("=" * 124)
    print(
        "R3A.1B — DECISION-TIME STATE V2 "
        "TEMPORAL ADMISSIBILITY AUDIT"
    )
    print("=" * 124)

    required = [
        DECISION_STATE,
        QUEUE,
        STATE_V2,
    ]

    print()
    print("INPUT CHECK")
    print("-" * 124)

    for path in required:
        print(
            f"{path}: "
            f"{'PRESENT' if path.exists() else 'MISSING'}"
        )

    if not all(
        path.exists()
        for path in required
    ):
        print()
        print(
            "FINAL STATUS: "
            "R3A1B_TEMPORAL_AUDIT_INPUT_MISSING"
        )
        return

    decision_rows = read_csv(
        DECISION_STATE
    )

    queue_rows = read_csv(
        QUEUE
    )

    state_rows = read_csv(
        STATE_V2
    )

    audit = []

    print()
    print("=" * 124)
    print("DECISION-STATE TEMPORAL CLASSIFICATION")
    print("=" * 124)

    for row in decision_rows:

        classification, reason = (
            classify_decision_row(
                row
            )
        )

        out = {
            "domain":
                "DECISION_STATE",

            "evidence_id":
                txt(
                    row.get("state_id")
                ),

            "driver_name":
                txt(
                    row.get("driver_name")
                ),

            "subject_attempt_id":
                txt(
                    row.get(
                        "subject_attempt_id"
                    )
                ),

            "related_attempt_id":
                txt(
                    row.get(
                        "related_attempt_id"
                    )
                ),

            "stage_or_family":
                txt(
                    row.get("state_stage")
                ),

            "semantic":
                txt(
                    row.get(
                        "source_semantic"
                    )
                ),

            "rank":
                txt(
                    row.get("rank")
                ),

            "cutoff_rank":
                txt(
                    row.get("cutoff_rank")
                ),

            "classification":
                classification,

            "pre_decision_feature_allowed":
                str(
                    classification
                    ==
                    "PRE_DECISION_ADMISSIBLE"
                ),

            "reason":
                reason,
        }

        audit.append(out)

        print()
        print("-" * 124)

        print(
            out["driver_name"],
            out["evidence_id"],
        )

        print(
            "  stage:",
            out["stage_or_family"],
        )

        print(
            "  semantic:",
            out["semantic"],
        )

        print(
            "  rank:",
            out["rank"]
            or
            "UNKNOWN",
        )

        print(
            "  classification:",
            classification,
        )

        print(
            "  allowed as pre-decision feature:",
            out[
                "pre_decision_feature_allowed"
            ],
        )

    print()
    print("=" * 124)
    print("QUEUE TEMPORAL CLASSIFICATION")
    print("=" * 124)

    for row in queue_rows:

        classification, reason = (
            classify_queue_row(
                row
            )
        )

        out = {
            "domain":
                "QUEUE",

            "evidence_id":
                txt(
                    row.get(
                        "queue_state_id"
                    )
                ),

            "driver_name":
                txt(
                    row.get("driver_name")
                ),

            "subject_attempt_id":
                txt(
                    row.get(
                        "subject_attempt_id"
                    )
                ),

            "related_attempt_id":
                txt(
                    row.get(
                        "related_attempt_id"
                    )
                ),

            "stage_or_family":
                txt(
                    row.get(
                        "evidence_family"
                    )
                ),

            "semantic":
                txt(
                    row.get(
                        "state_semantic"
                    )
                ),

            "rank":
                txt(
                    row.get(
                        "existing_rank"
                    )
                ),

            "cutoff_rank":
                "",

            "classification":
                classification,

            "pre_decision_feature_allowed":
                "False",

            "reason":
                reason,
        }

        audit.append(out)

        print()
        print("-" * 124)

        print(
            out["driver_name"],
            out["evidence_id"],
        )

        print(
            "  family:",
            out["stage_or_family"],
        )

        print(
            "  semantic:",
            out["semantic"],
        )

        print(
            "  classification:",
            classification,
        )

        print(
            "  allowed as pre-decision feature:",
            "False",
        )

    write_csv(
        AUDIT_OUT,
        audit,
        [
            "domain",
            "evidence_id",
            "driver_name",
            "subject_attempt_id",
            "related_attempt_id",
            "stage_or_family",
            "semantic",
            "rank",
            "cutoff_rank",
            "classification",
            "pre_decision_feature_allowed",
            "reason",
        ],
    )

    counts = Counter(
        row["classification"]
        for row in audit
    )

    admissible = [
        row
        for row in audit
        if row[
            "classification"
        ]
        ==
        "PRE_DECISION_ADMISSIBLE"
    ]

    future = [
        row
        for row in audit
        if row[
            "classification"
        ]
        ==
        "POST_ACTION_NOT_ADMISSIBLE"
    ]

    transition = [
        row
        for row in audit
        if row[
            "classification"
        ]
        ==
        "TRANSITION_EVIDENCE_ONLY"
    ]

    ordering = [
        row
        for row in audit
        if row[
            "classification"
        ]
        ==
        "ORDERING_EVIDENCE_ONLY"
    ]

    review = [
        row
        for row in audit
        if row[
            "classification"
        ]
        ==
        "REVIEW_REQUIRED"
    ]

    # Check current V2 for known conceptual leakage:
    # action/lane are labels, not pre-decision observables.
    action_in_observable = []

    queue_in_observable = []

    for row in state_rows:

        components = txt(
            row.get(
                "observable_components"
            )
        ).split("|")

        if (
            "ACTION" in components
            or
            "LANE" in components
        ):
            action_in_observable.append(
                txt(
                    row.get(
                        "driver_name"
                    )
                )
            )

        if "QUEUE_ANCHOR" in components:
            queue_in_observable.append(
                txt(
                    row.get(
                        "driver_name"
                    )
                )
            )

    print()
    print("=" * 124)
    print("AUDIT SUMMARY")
    print("=" * 124)

    print()
    print(
        "Decision-state rows:",
        len(
            decision_rows
        ),
    )

    print(
        "Queue rows:",
        len(
            queue_rows
        ),
    )

    print()
    print(
        "PRE_DECISION_ADMISSIBLE:",
        len(admissible),
    )

    print(
        "POST_ACTION_NOT_ADMISSIBLE:",
        len(future),
    )

    print(
        "TRANSITION_EVIDENCE_ONLY:",
        len(transition),
    )

    print(
        "ORDERING_EVIDENCE_ONLY:",
        len(ordering),
    )

    print(
        "REVIEW_REQUIRED:",
        len(review),
    )

    print()
    print(
        "Current V2 states counting ACTION/LANE "
        "as observable:",
        len(
            action_in_observable
        ),
    )

    print(
        "Drivers:",
        "|".join(
            action_in_observable
        )
        or
        "NONE",
    )

    print()
    print(
        "Current V2 states counting QUEUE_ANCHOR "
        "as observable:",
        len(
            queue_in_observable
        ),
    )

    print(
        "Drivers:",
        "|".join(
            queue_in_observable
        )
        or
        "NONE",
    )

    print()
    print("INTERPRETATION")
    print()

    print(
        "  Historical action and chosen lane are labels/"
        "transition metadata, not pre-decision state features."
    )

    print(
        "  Post-repeat ranks/cutoffs are outcomes, not "
        "pre-repeat observable features."
    )

    print(
        "  Queue evidence recovered here is transition/order "
        "evidence unless independently proven pre-decision."
    )

    print(
        "  Unknown pre-decision states must remain UNKNOWN."
    )

    qa_rows = [
        {
            "metric":
                "decision_rows_audited",

            "value":
                len(
                    decision_rows
                ),

            "status":
                (
                    "PASS"
                    if len(
                        decision_rows
                    )
                    ==
                    7
                    else
                    "REVIEW"
                ),
        },

        {
            "metric":
                "queue_rows_audited",

            "value":
                len(
                    queue_rows
                ),

            "status":
                (
                    "PASS"
                    if len(
                        queue_rows
                    )
                    ==
                    5
                    else
                    "REVIEW"
                ),
        },

        {
            "metric":
                "temporal_classification_complete",

            "value":
                len(
                    audit
                ),

            "status":
                (
                    "PASS"
                    if len(
                        audit
                    )
                    ==
                    len(
                        decision_rows
                    )
                    +
                    len(
                        queue_rows
                    )
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "action_lane_currently_used_as_observable",

            "value":
                len(
                    action_in_observable
                ),

            "status":
                (
                    "EXPECTED_FIX_REQUIRED"
                    if len(
                        action_in_observable
                    )
                    >
                    0
                    else
                    "PASS"
                ),
        },

        {
            "metric":
                "queue_currently_used_as_observable",

            "value":
                len(
                    queue_in_observable
                ),

            "status":
                (
                    "EXPECTED_FIX_REQUIRED"
                    if len(
                        queue_in_observable
                    )
                    >
                    0
                    else
                    "PASS"
                ),
        },

        {
            "metric":
                "active_ledger_mutation",

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

    hard_fail = any(
        row["status"]
        ==
        "FAIL"
        for row in qa_rows
    )

    print()
    print("=" * 124)

    if not hard_fail:

        print(
            "FINAL STATUS: "
            "R3A1B_TEMPORAL_ADMISSIBILITY_AUDIT_COMPLETE_"
            "STATE_V2_CORRECTION_REQUIRED"
        )

    else:

        print(
            "FINAL STATUS: "
            "R3A1B_TEMPORAL_ADMISSIBILITY_AUDIT_FAILED"
        )

    print("=" * 124)

    print()
    print("OUTPUTS")
    print(AUDIT_OUT)
    print(QA_OUT)


if __name__ == "__main__":
    main()
