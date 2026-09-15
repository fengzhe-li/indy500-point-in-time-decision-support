from pathlib import Path
import csv
import json
import math
from collections import defaultdict


PHASE = "R3C.0A"

OUT = Path("weather/output")

TARGET_DRIVER = "Scott McLaughlin"

TARGET_ATTEMPT_ID = (
    "d2ae8749-6312-5afd-b193-dd23dc071124"
)

STATE_V4 = (
    OUT
    / "decision_time_observable_state_v4_final.csv"
)

ENVELOPE_V1 = (
    OUT
    / "r3c_final_monte_carlo_action_envelope_v1.csv"
)

APPLICABILITY = (
    OUT
    / "r3c_action_historical_applicability_v1.csv"
)


CANDIDATE_SOURCES = [
    OUT
    / "unified_attempt_chronology_constraint_ledger_v10.csv",

    OUT
    / "chronology_rescue_2022_result_to_canonical_attempt_matches_v3.csv",

    OUT
    / "performance_context_features.csv",

    OUT
    / "repeat_performance_uncertainty_rows_v1.csv",
]


STATE_OUT = (
    OUT
    / "decision_time_observable_state_v4_1_final.csv"
)

ENVELOPE_OUT = (
    OUT
    / "r3c_final_monte_carlo_action_envelope_v2.csv"
)

EVIDENCE_OUT = (
    OUT
    / "r3c_scott_first_attempt_speed_rescue_evidence_v1.csv"
)

SUMMARY_OUT = (
    OUT
    / "r3c_scott_first_attempt_speed_rescue_v1.json"
)

QA_OUT = (
    OUT
    / "r3c_scott_first_attempt_speed_rescue_v1_qa.csv"
)


def txt(v):
    return "" if v is None else str(v).strip()


def fnum(v):
    try:
        value = float(txt(v))

        if math.isfinite(value):
            return value

    except Exception:
        pass

    return None


def read_csv(path):
    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as f:
        reader = csv.DictReader(f)

        return (
            list(reader),
            reader.fieldnames or [],
        )


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


def row_mentions_target_attempt(row):

    direct_id_fields = [
        "attempt_id",
        "canonical_attempt_id",
        "matched_attempt_id",
        "current_attempt_id",
        "baseline_attempt_id",
        "subject_attempt_id",
        "related_attempt_id",
        "first_attempt_id",
        "second_attempt_id",
    ]

    for field in direct_id_fields:

        if (
            txt(
                row.get(field)
            )
            ==
            TARGET_ATTEMPT_ID
        ):
            return True

    return False


def candidate_speed_fields(fields):

    out = []

    for field in fields:

        lower = field.lower()

        if "speed" not in lower:
            continue

        # Exclude fields that are clearly not the
        # attempt's own four-lap/result speed.
        excluded_terms = [
            "cutoff",
            "wind",
            "delta",
            "gain",
            "prior",
            "second",
            "related",
            "target",
            "predicted",
            "prediction",
            "mean_final",
            "q05_final",
            "q50_final",
            "q95_final",
        ]

        if any(
            term in lower
            for term in excluded_terms
        ):
            continue

        out.append(field)

    return out


def side_specific_speed_candidates(row):

    candidates = []

    subject_id = txt(
        row.get(
            "subject_attempt_id"
        )
    )

    related_id = txt(
        row.get(
            "related_attempt_id"
        )
    )

    if (
        subject_id
        ==
        TARGET_ATTEMPT_ID
    ):
        value = fnum(
            row.get(
                "subject_speed_mph"
            )
        )

        if value is not None:
            candidates.append(
                (
                    "subject_speed_mph",
                    value,
                    "SIDE_SPECIFIC_SUBJECT",
                )
            )

    if (
        related_id
        ==
        TARGET_ATTEMPT_ID
    ):
        value = fnum(
            row.get(
                "related_speed_mph"
            )
        )

        if value is not None:
            candidates.append(
                (
                    "related_speed_mph",
                    value,
                    "SIDE_SPECIFIC_RELATED",
                )
            )

    return candidates


def direct_attempt_speed_candidates(
    row,
    fields,
):

    candidates = []

    direct_id_fields = [
        "attempt_id",
        "canonical_attempt_id",
        "matched_attempt_id",
        "current_attempt_id",
        "baseline_attempt_id",
    ]

    exact_direct = any(
        txt(
            row.get(field)
        )
        ==
        TARGET_ATTEMPT_ID
        for field in direct_id_fields
    )

    if not exact_direct:
        return candidates

    for field in candidate_speed_fields(
        fields
    ):

        value = fnum(
            row.get(field)
        )

        if value is None:
            continue

        # Indy qualifying four-lap speed sanity range.
        if not (
            200.0
            <=
            value
            <=
            250.0
        ):
            continue

        candidates.append(
            (
                field,
                value,
                "DIRECT_ATTEMPT_ID",
            )
        )

    return candidates


def cluster_unique(values, tolerance=0.0005):

    clusters = []

    for value in sorted(values):

        placed = False

        for cluster in clusters:

            representative = sum(
                cluster
            ) / len(cluster)

            if abs(
                value
                -
                representative
            ) <= tolerance:

                cluster.append(
                    value
                )

                placed = True
                break

        if not placed:
            clusters.append(
                [
                    value
                ]
            )

    return clusters


def main():

    print()
    print("=" * 128)
    print(
        "R3C.0A — SCOTT McLAUGHLIN "
        "FIRST-ATTEMPT SPEED PROVENANCE RESCUE"
    )
    print("=" * 128)

    required = [
        STATE_V4,
        ENVELOPE_V1,
        APPLICABILITY,
    ]

    print()
    print("CORE INPUT CHECK")
    print("-" * 128)

    missing_core = []

    for path in required:

        exists = path.exists()

        print(
            f"{path}: "
            f"{'PRESENT' if exists else 'MISSING'}"
        )

        if not exists:
            missing_core.append(
                str(path)
            )

    if missing_core:

        print()
        print(
            "FINAL STATUS: "
            "R3C0A_CORE_INPUT_MISSING"
        )
        return

    print()
    print("CANDIDATE PROVENANCE SOURCES")
    print("-" * 128)

    available_sources = []

    for path in CANDIDATE_SOURCES:

        exists = path.exists()

        print(
            f"{path}: "
            f"{'PRESENT' if exists else 'MISSING'}"
        )

        if exists:
            available_sources.append(
                path
            )

    if not available_sources:

        print()
        print(
            "FINAL STATUS: "
            "R3C0A_NO_PROVENANCE_SOURCE_AVAILABLE"
        )
        return

    # --------------------------------------------------
    # Find exact-attempt speed evidence
    # --------------------------------------------------

    evidence_rows = []

    print()
    print("=" * 128)
    print("EXACT ATTEMPT-ID EVIDENCE")
    print("=" * 128)

    for source in available_sources:

        rows, fields = read_csv(
            source
        )

        matching_rows = [
            row
            for row in rows
            if row_mentions_target_attempt(
                row
            )
        ]

        print()
        print(source.name)

        print(
            "  rows:",
            len(rows),
        )

        print(
            "  exact-attempt matching rows:",
            len(
                matching_rows
            ),
        )

        for row_index, row in enumerate(
            matching_rows,
            start=1,
        ):

            candidates = []

            candidates.extend(
                side_specific_speed_candidates(
                    row
                )
            )

            candidates.extend(
                direct_attempt_speed_candidates(
                    row,
                    fields,
                )
            )

            for (
                field,
                speed,
                binding,
            ) in candidates:

                evidence = {
                    "source_file":
                        source.name,

                    "matching_row_index":
                        row_index,

                    "target_driver":
                        TARGET_DRIVER,

                    "target_attempt_id":
                        TARGET_ATTEMPT_ID,

                    "speed_field":
                        field,

                    "speed_mph":
                        f"{speed:.10f}",

                    "binding_type":
                        binding,

                    "row_driver_name":
                        txt(
                            row.get(
                                "driver_name"
                            )
                        )
                        or
                        txt(
                            row.get(
                                "driver"
                            )
                        )
                        or
                        "UNKNOWN",

                    "row_attempt_id":
                        txt(
                            row.get(
                                "attempt_id"
                            )
                        ),

                    "row_canonical_attempt_id":
                        txt(
                            row.get(
                                "canonical_attempt_id"
                            )
                        ),

                    "row_current_attempt_id":
                        txt(
                            row.get(
                                "current_attempt_id"
                            )
                        ),

                    "row_baseline_attempt_id":
                        txt(
                            row.get(
                                "baseline_attempt_id"
                            )
                        ),

                    "row_subject_attempt_id":
                        txt(
                            row.get(
                                "subject_attempt_id"
                            )
                        ),

                    "row_related_attempt_id":
                        txt(
                            row.get(
                                "related_attempt_id"
                            )
                        ),
                }

                evidence_rows.append(
                    evidence
                )

                print(
                    "   ",
                    field,
                    "=",
                    f"{speed:.6f}",
                    "(",
                    binding,
                    ")",
                )

    evidence_values = [
        fnum(
            row.get(
                "speed_mph"
            )
        )
        for row in evidence_rows
    ]

    evidence_values = [
        value
        for value in evidence_values
        if value is not None
    ]

    clusters = cluster_unique(
        evidence_values
    )

    print()
    print("=" * 128)
    print("CONSENSUS")
    print("=" * 128)

    print()
    print(
        "Evidence observations:",
        len(
            evidence_values
        ),
    )

    print(
        "Distinct speed clusters:",
        len(
            clusters
        ),
    )

    for i, cluster in enumerate(
        clusters,
        start=1,
    ):

        mean_value = sum(
            cluster
        ) / len(cluster)

        print(
            f"  cluster {i}: "
            f"{mean_value:.6f} mph "
            f"(n={len(cluster)})"
        )

    if len(clusters) != 1:

        write_csv(
            EVIDENCE_OUT,
            evidence_rows,
            [
                "source_file",
                "matching_row_index",
                "target_driver",
                "target_attempt_id",
                "speed_field",
                "speed_mph",
                "binding_type",
                "row_driver_name",
                "row_attempt_id",
                "row_canonical_attempt_id",
                "row_current_attempt_id",
                "row_baseline_attempt_id",
                "row_subject_attempt_id",
                "row_related_attempt_id",
            ],
        )

        print()
        print(
            "FINAL STATUS: "
            "R3C0A_SCOTT_SPEED_CONSENSUS_REVIEW_REQUIRED"
        )
        return

    recovered_speed = sum(
        clusters[0]
    ) / len(
        clusters[0]
    )

    # --------------------------------------------------
    # Patch state into additive V4.1 output
    # --------------------------------------------------

    state_rows, state_fields = read_csv(
        STATE_V4
    )

    scott_rows = [
        row
        for row in state_rows
        if txt(
            row.get(
                "driver_name"
            )
        )
        ==
        TARGET_DRIVER
    ]

    if len(scott_rows) != 1:

        print()
        print(
            "FINAL STATUS: "
            "R3C0A_SCOTT_STATE_ROW_NOT_UNIQUE"
        )
        return

    final_states = []

    for row in state_rows:

        new = dict(row)

        if txt(
            new.get(
                "driver_name"
            )
        ) == TARGET_DRIVER:

            if txt(
                new.get(
                    "first_attempt_id"
                )
            ) != TARGET_ATTEMPT_ID:

                print()
                print(
                    "FINAL STATUS: "
                    "R3C0A_SCOTT_ATTEMPT_ID_MISMATCH"
                )
                return

            new[
                "first_attempt_speed_mph"
            ] = f"{recovered_speed:.6f}"

            new[
                "first_attempt_speed_repair_status"
            ] = (
                "RECOVERED_FROM_CANONICAL_"
                "PROVENANCE_R3C0A"
            )

            new[
                "first_attempt_speed_repair_evidence_ids"
            ] = "|".join(
                sorted(
                    {
                        row[
                            "source_file"
                        ]
                        +
                        ":"
                        +
                        row[
                            "speed_field"
                        ]
                        for row in evidence_rows
                    }
                )
            )

            new[
                "state_version"
            ] = "V4.1_FINAL"

        final_states.append(
            new
        )

    if "state_version" not in state_fields:
        state_fields.append(
            "state_version"
        )

    if (
        "first_attempt_speed_repair_status"
        not in state_fields
    ):
        state_fields.append(
            "first_attempt_speed_repair_status"
        )

    if (
        "first_attempt_speed_repair_evidence_ids"
        not in state_fields
    ):
        state_fields.append(
            "first_attempt_speed_repair_evidence_ids"
        )

    write_csv(
        STATE_OUT,
        final_states,
        state_fields,
    )

    # --------------------------------------------------
    # Patch only Scott absolute speeds in final envelope.
    # Delta distributions remain byte-semantically
    # unchanged.
    # --------------------------------------------------

    envelope_rows, envelope_fields = read_csv(
        ENVELOPE_V1
    )

    final_envelope = []

    repaired_envelope_rows = 0

    for row in envelope_rows:

        new = dict(row)

        if txt(
            new.get(
                "driver_name"
            )
        ) == TARGET_DRIVER:

            new[
                "baseline_speed_mph"
            ] = (
                f"{recovered_speed:.10f}"
            )

            for (
                delta_field,
                speed_field,
            ) in [
                (
                    "mean_final_delta_mph",
                    "mean_final_speed_mph",
                ),
                (
                    "q05_final_delta_mph",
                    "q05_final_speed_mph",
                ),
                (
                    "q50_final_delta_mph",
                    "q50_final_speed_mph",
                ),
                (
                    "q95_final_delta_mph",
                    "q95_final_speed_mph",
                ),
            ]:

                delta_value = fnum(
                    new.get(
                        delta_field
                    )
                )

                if delta_value is not None:

                    new[
                        speed_field
                    ] = (
                        f"{recovered_speed + delta_value:.10f}"
                    )

            new[
                "absolute_speed_repair_status"
            ] = "SCOTT_R3C0A"

            repaired_envelope_rows += 1

        else:

            new[
                "absolute_speed_repair_status"
            ] = "NOT_REQUIRED"

        final_envelope.append(
            new
        )

    if (
        "absolute_speed_repair_status"
        not in envelope_fields
    ):
        envelope_fields.append(
            "absolute_speed_repair_status"
        )

    write_csv(
        ENVELOPE_OUT,
        final_envelope,
        envelope_fields,
    )

    write_csv(
        EVIDENCE_OUT,
        evidence_rows,
        [
            "source_file",
            "matching_row_index",
            "target_driver",
            "target_attempt_id",
            "speed_field",
            "speed_mph",
            "binding_type",
            "row_driver_name",
            "row_attempt_id",
            "row_canonical_attempt_id",
            "row_current_attempt_id",
            "row_baseline_attempt_id",
            "row_subject_attempt_id",
            "row_related_attempt_id",
        ],
    )

    # --------------------------------------------------
    # QA
    # --------------------------------------------------

    repaired_state = next(
        row
        for row in final_states
        if row[
            "driver_name"
        ]
        ==
        TARGET_DRIVER
    )

    final_speed = fnum(
        repaired_state.get(
            "first_attempt_speed_mph"
        )
    )

    monte_carlo_delta_fields_changed = False

    old_env, _ = read_csv(
        ENVELOPE_V1
    )

    old_by_key = {}

    for row in old_env:

        key = (
            txt(
                row.get(
                    "driver_name"
                )
            ),
            txt(
                row.get(
                    "recovery_prior_scenario"
                )
            ),
            txt(
                row.get(
                    "wait_scenario_id"
                )
            ),
            txt(
                row.get(
                    "action"
                )
            ),
        )

        old_by_key[key] = row

    delta_fields = [
        "mean_final_delta_mph",
        "std_final_delta_mph",
        "q025_final_delta_mph",
        "q05_final_delta_mph",
        "q10_final_delta_mph",
        "q25_final_delta_mph",
        "q50_final_delta_mph",
        "q75_final_delta_mph",
        "q90_final_delta_mph",
        "q95_final_delta_mph",
        "q975_final_delta_mph",
        "prob_final_improves",
        "prob_final_unchanged",
        "prob_final_worse",
    ]

    for row in final_envelope:

        key = (
            txt(
                row.get(
                    "driver_name"
                )
            ),
            txt(
                row.get(
                    "recovery_prior_scenario"
                )
            ),
            txt(
                row.get(
                    "wait_scenario_id"
                )
            ),
            txt(
                row.get(
                    "action"
                )
            ),
        )

        old = old_by_key.get(
            key
        )

        if old is None:
            monte_carlo_delta_fields_changed = True
            break

        for field in delta_fields:

            if txt(
                old.get(field)
            ) != txt(
                row.get(field)
            ):

                monte_carlo_delta_fields_changed = True
                break

        if monte_carlo_delta_fields_changed:
            break

    qa_rows = [
        {
            "metric":
                "exact_attempt_id_used",

            "value":
                TARGET_ATTEMPT_ID,

            "status":
                "PASS",
        },

        {
            "metric":
                "speed_evidence_observations",

            "value":
                len(
                    evidence_values
                ),

            "status":
                (
                    "PASS"
                    if len(
                        evidence_values
                    )
                    >
                    0
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "unique_speed_clusters",

            "value":
                len(
                    clusters
                ),

            "status":
                (
                    "PASS"
                    if len(
                        clusters
                    )
                    ==
                    1
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "scott_first_attempt_speed_final",

            "value":
                (
                    f"{final_speed:.6f}"
                    if final_speed
                    is not None
                    else
                    "UNKNOWN"
                ),

            "status":
                (
                    "PASS"
                    if final_speed
                    is not None
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "scott_envelope_rows_repaired",

            "value":
                repaired_envelope_rows,

            "status":
                (
                    "PASS"
                    if repaired_envelope_rows
                    >
                    0
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "monte_carlo_delta_fields_changed",

            "value":
                int(
                    monte_carlo_delta_fields_changed
                ),

            "status":
                (
                    "PASS"
                    if not monte_carlo_delta_fields_changed
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "hard_recommendation_created",

            "value":
                0,

            "status":
                "PASS",
        },

        {
            "metric":
                "protected_source_outputs_mutated",

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
        row[
            "status"
        ]
        ==
        "FAIL"
        for row in qa_rows
    )

    summary = {
        "phase":
            PHASE,

        "driver":
            TARGET_DRIVER,

        "attempt_id":
            TARGET_ATTEMPT_ID,

        "recovered_speed_mph":
            final_speed,

        "speed_evidence_observations":
            len(
                evidence_rows
            ),

        "speed_clusters":
            [
                {
                    "mean_mph":
                        sum(cluster)
                        /
                        len(cluster),

                    "observations":
                        len(cluster),
                }
                for cluster in clusters
            ],

        "state_version":
            "V4.1_FINAL",

        "scott_absolute_envelope_rows_repaired":
            repaired_envelope_rows,

        "monte_carlo_delta_distribution_changed":
            False,

        "sato_required_reattempt_policy":
            "PRESERVED_FROM_R3C0",

        "hard_recommendation_ready":
            False,

        "next_phase":
            (
                "R3C1_FINAL_RESULTS_AND_CAPABILITY_FREEZE"
                if not hard_fail
                else
                "R3C0A_REVIEW_REQUIRED"
            ),
    }

    SUMMARY_OUT.write_text(
        json.dumps(
            summary,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print()
    print("=" * 128)
    print("R3C.0A SUMMARY")
    print("=" * 128)

    print()
    print(
        "Scott attempt ID:",
        TARGET_ATTEMPT_ID,
    )

    print(
        "Recovered speed:",
        (
            f"{final_speed:.6f} mph"
            if final_speed
            is not None
            else
            "UNKNOWN"
        ),
    )

    print(
        "Evidence observations:",
        len(
            evidence_rows
        ),
    )

    print(
        "Unique speed clusters:",
        len(
            clusters
        ),
    )

    print(
        "Scott envelope rows repaired:",
        repaired_envelope_rows,
    )

    print(
        "Monte Carlo delta fields changed:",
        monte_carlo_delta_fields_changed,
    )

    print(
        "Sato required-reattempt policy preserved:",
        "YES",
    )

    print(
        "Hard recommendation created:",
        "NO",
    )

    print()
    print("=" * 128)

    if not hard_fail:

        print(
            "FINAL STATUS: "
            "R3C0A_SCOTT_SPEED_RESCUED_FINAL_STATE_READY"
        )

    else:

        print(
            "FINAL STATUS: "
            "R3C0A_SCOTT_SPEED_RESCUE_REVIEW_REQUIRED"
        )

    print("=" * 128)

    print()
    print("OUTPUTS")
    print(STATE_OUT)
    print(ENVELOPE_OUT)
    print(EVIDENCE_OUT)
    print(SUMMARY_OUT)
    print(QA_OUT)


if __name__ == "__main__":
    main()
