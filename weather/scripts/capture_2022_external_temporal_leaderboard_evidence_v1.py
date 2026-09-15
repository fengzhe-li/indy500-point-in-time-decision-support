from pathlib import Path
import csv


PHASE = "R2C.2"

RESULT_V3 = Path(
    "weather/output/"
    "chronology_rescue_2022_result_to_canonical_attempt_matches_v3.csv"
)

CHRONOLOGY_V10 = Path(
    "weather/output/"
    "unified_attempt_chronology_constraint_ledger_v10.csv"
)

ACTION_V8 = Path(
    "weather/output/"
    "unified_attempt_action_lane_ledger_v8.csv"
)

ADJUDICATION_R2C1A = Path(
    "weather/output/"
    "leaderboard_rescue_2022_candidate_adjudication_v1.csv"
)

OUTPUT_DIR = Path("weather/output")

EVIDENCE_OUT = (
    OUTPUT_DIR
    / "leaderboard_rescue_2022_external_temporal_evidence_v1.csv"
)

QA_OUT = (
    OUTPUT_DIR
    / "leaderboard_rescue_2022_external_temporal_evidence_v1_qa.csv"
)


ROSSI_FIRST = "1e2facfd-2c67-5b5a-9556-04ef28eeb0d8"
ROSSI_SECOND = "b3147013-0fda-5982-bea1-85788019ef89"

MALUKAS_FIRST = "619575d3-e7eb-5cce-886f-0a8485b98eba"
MALUKAS_SECOND = "85c917fa-1c7a-52cb-a47f-468b4bdae9a5"

SATO_FIRST = "3f221659-74ff-5901-97dc-08071a734690"
SATO_SECOND = "21e8c99e-b04c-516d-85a8-ccfbaed7ff46"


AUTOSPORT_URL = (
    "https://www.autosport.com/indycar/news/"
    "indy-500-sato-grosjean-johnson-into-top-12-fight-"
    "p13-33-set/10308540/"
)

THERACE_URL = (
    "https://www.the-race.com/indycar/"
    "everything-that-happened-in-tense-first-indy-500-qualifying/"
)


# Keep quotes short and source-native.
ROSSI_QUOTE = (
    "dropping himself from 15th to 21st"
)

MALUKAS_QUOTE = (
    "Rookie Malukas improved, and got the Coyne with HMD car into 12th"
)

SATO_QUOTE = (
    "claimed 12th"
)

THERACE_SATO_QUOTE = (
    "good enough for 12th, bumping his star rookie team-mate David Malukas"
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


def chronology_present(rows, attempt_id):
    return any(
        txt(row.get("attempt_id")) == attempt_id
        and
        txt(row.get("chronology_usable")).lower() == "true"
        for row in rows
    )


def result_present(rows, attempt_id):
    return any(
        txt(row.get("attempt_id")) == attempt_id
        for row in rows
    )


def main():

    print()
    print("=" * 120)
    print(
        "R2C.2 — 2022 EXTERNAL TEMPORAL RANK / "
        "TOP-12 CUTOFF EVIDENCE CAPTURE"
    )
    print("=" * 120)

    required = [
        RESULT_V3,
        CHRONOLOGY_V10,
        ACTION_V8,
        ADJUDICATION_R2C1A,
    ]

    print()
    print("INPUT CHECK")
    print("-" * 120)

    for path in required:
        print(
            f"{path}: "
            f"{'PRESENT' if path.exists() else 'MISSING'}"
        )

    if not all(path.exists() for path in required):
        print()
        print(
            "FINAL STATUS: "
            "R2C2_EXTERNAL_LEADERBOARD_CAPTURE_INPUT_MISSING"
        )
        return

    result_v3 = read_csv(RESULT_V3)
    chronology = read_csv(CHRONOLOGY_V10)
    action = read_csv(ACTION_V8)
    adjudication = read_csv(ADJUDICATION_R2C1A)

    ids = [
        ROSSI_FIRST,
        ROSSI_SECOND,
        MALUKAS_FIRST,
        MALUKAS_SECOND,
        SATO_FIRST,
        SATO_SECOND,
    ]

    result_grounding = {
        aid: result_present(
            result_v3,
            aid,
        )
        for aid in ids
    }

    chronology_grounding = {
        aid: chronology_present(
            chronology,
            aid,
        )
        for aid in ids
    }

    rossi_lane1 = any(
        txt(row.get("driver_name")) == "Alexander Rossi"
        and
        txt(row.get("subject_attempt_id")) == ROSSI_SECOND
        and
        txt(row.get("related_attempt_id")) == ROSSI_FIRST
        and
        txt(row.get("lane")) == "LANE_1"
        for row in action
    )

    mclaughlin_anchor_ready = any(
        txt(row.get("driver_name")) == "Scott McLaughlin"
        and
        txt(row.get("promotion_ready")).lower() == "true"
        and
        txt(row.get("supported_rank_before")) == "15"
        and
        txt(row.get("supported_rank_after")) == "26"
        for row in adjudication
    )

    print()
    print("=" * 120)
    print("GROUNDING")
    print("=" * 120)

    print()

    for aid in ids:
        print(
            aid,
            "| result V3:",
            result_grounding[aid],
            "| chronology V10:",
            chronology_grounding[aid],
        )

    print()
    print(
        "Rossi Lane 1 already in V8:",
        rossi_lane1,
    )

    print(
        "McLaughlin 15->26 R2C1A anchor ready:",
        mclaughlin_anchor_ready,
    )

    all_attempts_grounded = all(
        result_grounding.values()
    )

    all_chronology_grounded = all(
        chronology_grounding.values()
    )

    promotion_ready = all([
        all_attempts_grounded,
        all_chronology_grounded,
        rossi_lane1,
        mclaughlin_anchor_ready,
    ])

    print()
    print("=" * 120)
    print("EXTERNAL SOURCE ADJUDICATION")
    print("=" * 120)

    print()
    print("ROSSI")
    print("  source: Autosport")
    print("  quote:", repr(ROSSI_QUOTE))
    print("  pre-action rank: 15")
    print("  post-second-run rank: 21")
    print("  lane: LANE_1")
    print("  time quality: ORDERING_ONLY")

    print()
    print("MALUKAS")
    print("  source: Autosport")
    print("  quote:", repr(MALUKAS_QUOTE))
    print("  supported provisional rank after repeat: 12")
    print("  Top-12 state: INSIDE")
    print("  exact timestamp: UNKNOWN")

    print()
    print("SATO / MALUKAS CUTOFF TRANSITION")
    print("  source 1: Autosport")
    print("  Sato quote:", repr(SATO_QUOTE))
    print("  source 2: The Race")
    print("  corroboration:", repr(THERACE_SATO_QUOTE))
    print("  Sato rank after run: 12")
    print("  Malukas state after Sato run: OUTSIDE_TOP_12")
    print("  implied Malukas rank bound: >=13")
    print("  exact P13 speed at that moment: UNKNOWN")
    print("  exact timestamp: UNKNOWN")

    print()
    print(
        "Promotion ready:",
        promotion_ready,
    )

    evidence_rows = [
        {
            "evidence_id":
                "R2C2-ROSSI-RANK-TRANSITION",

            "phase":
                PHASE,

            "driver_name":
                "Alexander Rossi",

            "subject_attempt_id":
                ROSSI_SECOND,

            "related_attempt_id":
                ROSSI_FIRST,

            "source_name":
                "Autosport",

            "source_class":
                "REPUTABLE_SECONDARY_EDITORIAL",

            "source_url":
                AUTOSPORT_URL,

            "source_quote":
                ROSSI_QUOTE,

            "state_semantic":
                "PRE_ACTION_TO_POST_RUN_RANK_TRANSITION",

            "rank_before":
                "15",

            "rank_after":
                "21",

            "top12_state_before":
                "OUTSIDE",

            "top12_state_after":
                "OUTSIDE",

            "cutoff_rank":
                "12",

            "cutoff_speed_mph":
                "UNKNOWN",

            "time_quality":
                "ORDERING_ONLY",

            "exact_timestamp":
                "UNKNOWN",

            "promotion_ready":
                str(promotion_ready),

            "notes":
                (
                    "Autosport directly describes Rossi dropping "
                    "from 15th to 21st on his second run. V8 "
                    "independently binds that second run to Lane 1. "
                    "No exact timestamp or live cutoff speed inferred."
                ),
        },

        {
            "evidence_id":
                "R2C2-MALUKAS-PROVISIONAL-P12",

            "phase":
                PHASE,

            "driver_name":
                "David Malukas",

            "subject_attempt_id":
                MALUKAS_SECOND,

            "related_attempt_id":
                MALUKAS_FIRST,

            "source_name":
                "Autosport",

            "source_class":
                "REPUTABLE_SECONDARY_EDITORIAL",

            "source_url":
                AUTOSPORT_URL,

            "source_quote":
                MALUKAS_QUOTE,

            "state_semantic":
                "POST_REPEAT_PROVISIONAL_TOP12_STATE",

            "rank_before":
                "UNKNOWN",

            "rank_after":
                "12",

            "top12_state_before":
                "UNKNOWN",

            "top12_state_after":
                "INSIDE",

            "cutoff_rank":
                "12",

            "cutoff_speed_mph":
                "UNKNOWN",

            "time_quality":
                "ORDERING_ONLY",

            "exact_timestamp":
                "UNKNOWN",

            "promotion_ready":
                str(promotion_ready),

            "notes":
                (
                    "Autosport explicitly states Malukas improved "
                    "and moved into 12th. This is a provisional "
                    "Top-12 state before Sato's subsequent run."
                ),
        },

        {
            "evidence_id":
                "R2C2-SATO-P12-BUMPS-MALUKAS",

            "phase":
                PHASE,

            "driver_name":
                "Takuma Sato",

            "subject_attempt_id":
                SATO_SECOND,

            "related_attempt_id":
                SATO_FIRST,

            "source_name":
                "Autosport + The Race",

            "source_class":
                "REPUTABLE_SECONDARY_EDITORIAL_CORROBORATED",

            "source_url":
                AUTOSPORT_URL
                +
                " | "
                +
                THERACE_URL,

            "source_quote":
                (
                    SATO_QUOTE
                    +
                    " | "
                    +
                    THERACE_SATO_QUOTE
                ),

            "state_semantic":
                "SATO_TO_P12_DISPLACES_MALUKAS_FROM_TOP12",

            "rank_before":
                "UNKNOWN",

            "rank_after":
                "12",

            "top12_state_before":
                "UNKNOWN",

            "top12_state_after":
                "INSIDE",

            "cutoff_rank":
                "12",

            "cutoff_speed_mph":
                "UNKNOWN",

            "time_quality":
                "ORDERING_ONLY",

            "exact_timestamp":
                "UNKNOWN",

            "promotion_ready":
                str(promotion_ready),

            "notes":
                (
                    "Autosport and The Race independently support "
                    "Sato reaching 12th and displacing Malukas. "
                    "This establishes an ordered Top-12 cutoff "
                    "transition but not a complete leaderboard."
                ),
        },

        {
            "evidence_id":
                "R2C2-MALUKAS-DISPLACED-BY-SATO",

            "phase":
                PHASE,

            "driver_name":
                "David Malukas",

            "subject_attempt_id":
                MALUKAS_SECOND,

            "related_attempt_id":
                SATO_SECOND,

            "source_name":
                "Autosport + The Race",

            "source_class":
                "REPUTABLE_SECONDARY_EDITORIAL_CORROBORATED",

            "source_url":
                AUTOSPORT_URL
                +
                " | "
                +
                THERACE_URL,

            "source_quote":
                THERACE_SATO_QUOTE,

            "state_semantic":
                "PROVISIONAL_P12_THEN_DISPLACED_OUTSIDE_TOP12",

            "rank_before":
                "12",

            "rank_after":
                ">=13",

            "top12_state_before":
                "INSIDE",

            "top12_state_after":
                "OUTSIDE",

            "cutoff_rank":
                "12",

            "cutoff_speed_mph":
                "UNKNOWN",

            "time_quality":
                "ORDERING_ONLY",

            "exact_timestamp":
                "UNKNOWN",

            "promotion_ready":
                str(promotion_ready),

            "notes":
                (
                    "Malukas was explicitly placed 12th before "
                    "Sato's later run displaced him. Post-Sato "
                    "rank is conservatively stored as >=13 rather "
                    "than inventing an exact contemporaneous P13."
                ),
        },
    ]

    fields = [
        "evidence_id",
        "phase",
        "driver_name",
        "subject_attempt_id",
        "related_attempt_id",
        "source_name",
        "source_class",
        "source_url",
        "source_quote",
        "state_semantic",
        "rank_before",
        "rank_after",
        "top12_state_before",
        "top12_state_after",
        "cutoff_rank",
        "cutoff_speed_mph",
        "time_quality",
        "exact_timestamp",
        "promotion_ready",
        "notes",
    ]

    write_csv(
        EVIDENCE_OUT,
        evidence_rows,
        fields,
    )

    qa_rows = [
        {
            "metric": "all_attempt_ids_in_result_v3",
            "value": int(all_attempts_grounded),
            "status": "PASS" if all_attempts_grounded else "FAIL",
        },
        {
            "metric": "all_attempt_ids_in_chronology_v10",
            "value": int(all_chronology_grounded),
            "status": "PASS" if all_chronology_grounded else "FAIL",
        },
        {
            "metric": "rossi_lane1_v8_grounded",
            "value": int(rossi_lane1),
            "status": "PASS" if rossi_lane1 else "FAIL",
        },
        {
            "metric": "mclaughlin_r2c1a_anchor_grounded",
            "value": int(mclaughlin_anchor_ready),
            "status": "PASS" if mclaughlin_anchor_ready else "FAIL",
        },
        {
            "metric": "rossi_rank_transition_captured",
            "value": 1,
            "status": "PASS",
        },
        {
            "metric": "malukas_provisional_p12_captured",
            "value": 1,
            "status": "PASS",
        },
        {
            "metric": "sato_p12_displacement_captured",
            "value": 1,
            "status": "PASS",
        },
        {
            "metric": "exact_live_cutoff_speed_inferred",
            "value": 0,
            "status": "PASS",
        },
        {
            "metric": "exact_timestamp_inferred",
            "value": 0,
            "status": "PASS",
        },
        {
            "metric": "complete_live_leaderboard_claimed",
            "value": 0,
            "status": "PASS",
        },
        {
            "metric": "ledger_mutation",
            "value": 0,
            "status": "PASS",
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

    if promotion_ready:
        print(
            "FINAL STATUS: "
            "R2C2_EXTERNAL_TEMPORAL_LEADERBOARD_EVIDENCE_PROMOTION_READY"
        )
    else:
        print(
            "FINAL STATUS: "
            "R2C2_EXTERNAL_TEMPORAL_LEADERBOARD_EVIDENCE_REVIEW_REQUIRED"
        )

    print("=" * 120)

    print()
    print("OUTPUTS")
    print(EVIDENCE_OUT)
    print(QA_OUT)


if __name__ == "__main__":
    main()
