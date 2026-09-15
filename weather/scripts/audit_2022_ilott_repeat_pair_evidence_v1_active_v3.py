from pathlib import Path
import csv
import re
from collections import defaultdict


# ============================================================
# PHASE
# ============================================================

PHASE = "R1G.26"


# ============================================================
# INPUTS
# ============================================================

CANONICAL = Path(
    "data/canonical/v1/attempts.csv"
)

RESULT_MATCH_V3 = Path(
    "weather/output/"
    "chronology_rescue_2022_result_to_canonical_attempt_matches_v3.csv"
)

SECONDARY_CANDIDATES = Path(
    "weather/output/"
    "chronology_rescue_2022_secondary_editorial_candidates_v1.csv"
)

R2A_REGISTRY = Path(
    "weather/output/"
    "official_lane_queue_live_resource_registry_v1.csv"
)

R2A_COVERAGE = Path(
    "weather/output/"
    "official_lane_queue_live_year_coverage_v1.csv"
)


# ============================================================
# EVIDENCE DIRECTORIES
# ============================================================

EVIDENCE_DIRS = [
    Path(
        "weather/evidence/rescue/"
        "official_2022_editorial_chronology"
    ),
    Path(
        "weather/evidence/rescue/"
        "secondary_2022_high_priority_chronology"
    ),
    Path(
        "weather/evidence/rescue/"
        "official_lane_queue_live_resources"
    ),
]


# ============================================================
# OUTPUTS
# ============================================================

OUTPUT_DIR = Path(
    "weather/output"
)

EVIDENCE_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_ilott_repeat_pair_evidence_v1.csv"
)

LOCAL_FILE_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_ilott_local_text_hits_v1.csv"
)

AUDIT_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_ilott_repeat_pair_audit_v1.csv"
)

QA_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_ilott_repeat_pair_audit_v1_qa.csv"
)


# ============================================================
# TARGET
# ============================================================

TARGET_DRIVER = "Callum Ilott"

TARGET_NAME_TOKENS = [
    "callum ilott",
    "ilott",
]


ACTION_TERMS = [
    "first run",
    "first attempt",
    "second run",
    "second attempt",
    "another run",
    "another attempt",
    "ran again",
    "run again",
    "went again",
    "went back out",
    "back out",
    "rerun",
    "re-run",
    "requalified",
    "re-qualified",
    "returned",
    "later run",
    "later attempt",
    "improve",
    "improved",
    "improvement",
    "unable to improve",
    "failed to improve",
    "withdrew",
    "withdrawn",
    "withdraw",
    "gave up",
    "gave up his time",
    "gave up the time",
    "gave up their time",
    "surrendered",
    "bail",
    "bailed",
    "abort",
    "aborted",
    "lane 1",
    "lane one",
    "lane 2",
    "lane two",
    "priority lane",
    "priority queue",
    "queue",
    "queued",
    "requeue",
    "re-queue",
    "pit lane",
    "pit",
    "cool",
    "cooling",
    "fuel",
    "refuel",
    "service",
]


# ============================================================
# HELPERS
# ============================================================

def txt(v):
    return "" if v is None else str(v).strip()


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


def is_2022(row):
    year = txt(
        row.get("year")
    )

    if year == "2022":
        return True

    session_id = txt(
        row.get("session_id")
    )

    return "2022" in session_id


def canonical_driver(row):
    for field in [
        "driver_name",
        "driver",
        "driver_full_name",
    ]:
        value = txt(
            row.get(field)
        )

        if value:
            return value

    return ""


def canonical_speed(row):
    for field in [
        "four_lap_average_speed_mph",
        "average_speed_mph",
        "speed_mph",
    ]:
        value = txt(
            row.get(field)
        )

        if value:
            return value

    return ""


def normalize_name(value):
    raw = txt(value)

    if not raw:
        return ""

    if "," in raw:
        parts = [
            part.strip()
            for part in raw.split(",")
            if part.strip()
        ]

        if len(parts) == 2:
            raw = (
                parts[1]
                + " "
                + parts[0]
            )

    return " ".join(
        raw.lower()
        .replace(".", "")
        .replace("'", "")
        .replace("’", "")
        .replace("-", " ")
        .split()
    )


def is_ilott_name(value):
    return (
        normalize_name(value)
        ==
        normalize_name(
            TARGET_DRIVER
        )
    )


def speed_variants(value):
    raw = txt(value)

    if not raw:
        return []

    variants = {
        raw,
    }

    try:
        num = float(raw)

        variants.add(
            f"{num:.3f}"
        )

        variants.add(
            f"{num:.2f}"
        )

        variants.add(
            f"{num:.1f}"
        )

    except Exception:
        pass

    return sorted(
        variants
    )


def split_sentences(text):
    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return [
        part.strip()
        for part in re.split(
            r"(?<=[.!?])\s+",
            text,
        )
        if part.strip()
    ]


def contains_target(text):
    lower = txt(text).lower()

    return any(
        token in lower
        for token in TARGET_NAME_TOKENS
    )


def matched_action_terms(text):
    lower = txt(text).lower()

    return [
        term
        for term in ACTION_TERMS
        if term in lower
    ]


def safe_read_text(path):
    try:
        return path.read_text(
            encoding="utf-8",
            errors="replace",
        )
    except Exception:
        return ""


def source_class_for_path(path):
    lower = str(path).lower()

    if (
        "official_2022_editorial_chronology"
        in lower
    ):
        return "INDYCAR_OFFICIAL_EDITORIAL"

    if (
        "secondary_2022_high_priority_chronology"
        in lower
    ):
        return "REPUTABLE_SECONDARY_EDITORIAL"

    if (
        "official_lane_queue_live_resources"
        in lower
    ):
        return "R2A_RESOURCE_RECON_EVIDENCE"

    return "LOCAL_EVIDENCE"


def textual_file(path):
    return (
        path.suffix.lower()
        in {
            ".txt",
            ".md",
            ".json",
            ".html",
            ".htm",
            ".csv",
        }
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
        "R1G.26 — 2022 CALLUM ILOTT "
        "REPEAT-PAIR TARGETED EVIDENCE AUDIT V1 / ACTIVE V3"
    )
    print("=" * 120)

    # ========================================================
    # INPUT CHECK
    # ========================================================

    required = [
        CANONICAL,
        RESULT_MATCH_V3,
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

    print(
        f"{SECONDARY_CANDIDATES}: "
        f"{'PRESENT' if SECONDARY_CANDIDATES.exists() else 'MISSING_OPTIONAL'}"
    )

    print(
        f"{R2A_REGISTRY}: "
        f"{'PRESENT' if R2A_REGISTRY.exists() else 'MISSING_OPTIONAL'}"
    )

    print(
        f"{R2A_COVERAGE}: "
        f"{'PRESENT' if R2A_COVERAGE.exists() else 'MISSING_OPTIONAL'}"
    )

    for path in EVIDENCE_DIRS:

        print(
            f"{path}: "
            f"{'PRESENT' if path.exists() else 'MISSING_OPTIONAL'}"
        )

    if missing:

        print()
        print(
            "FINAL STATUS: "
            "ILOTT_REPEAT_PAIR_AUDIT_INPUT_MISSING"
        )
        return

    canonical = read_csv(
        CANONICAL
    )

    result_v3 = read_csv(
        RESULT_MATCH_V3
    )

    # ========================================================
    # DISCOVER ILOTT CANONICAL OBJECTS
    # ========================================================

    ilott_canonical = [
        row
        for row in canonical
        if (
            is_2022(row)
            and
            is_ilott_name(
                canonical_driver(row)
            )
        )
    ]

    ilott_canonical = sorted(
        ilott_canonical,
        key=lambda row: (
            int(
                txt(
                    row.get(
                        "car_attempt_index"
                    )
                )
                or "999"
            ),
            txt(
                row.get(
                    "attempt_id"
                )
            ),
        ),
    )

    ilott_ids = {
        txt(
            row.get(
                "attempt_id"
            )
        )
        for row in ilott_canonical
        if txt(
            row.get(
                "attempt_id"
            )
        )
    }

    result_by_id = {
        txt(
            row.get(
                "attempt_id"
            )
        ): row
        for row in result_v3
        if txt(
            row.get(
                "attempt_id"
            )
        )
    }

    print()
    print("=" * 120)
    print(
        "ILOTT CANONICAL TARGETS"
    )
    print("=" * 120)

    print()
    print(
        "Canonical Ilott objects:",
        len(
            ilott_canonical
        ),
    )

    speeds = []

    for row in ilott_canonical:

        aid = txt(
            row.get(
                "attempt_id"
            )
        )

        speed = canonical_speed(
            row
        )

        if speed:
            speeds.append(speed)

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
            "  car_number:",
            repr(
                txt(
                    row.get(
                        "car_number"
                    )
                )
            ),
        )

        print(
            "  attempt_index:",
            repr(
                txt(
                    row.get(
                        "car_attempt_index"
                    )
                )
            ),
        )

        print(
            "  speed:",
            repr(
                speed
            ),
        )

        print(
            "  attempt_class:",
            repr(
                txt(
                    row.get(
                        "attempt_class"
                    )
                )
            ),
        )

        print(
            "  canonical result status:",
            repr(
                txt(
                    row.get(
                        "result_status"
                    )
                )
            ),
        )

        print(
            "  V3 official row:",
            repr(
                txt(
                    linked.get(
                        "official_result_row"
                    )
                )
            ),
        )

        print(
            "  V3 official speed:",
            repr(
                txt(
                    linked.get(
                        "official_speed_mph"
                    )
                )
            ),
        )

        print(
            "  V3 official status:",
            repr(
                txt(
                    linked.get(
                        "official_status"
                    )
                )
            ),
        )

    # ========================================================
    # RESULT-MATCH V3 SANITY
    # ========================================================

    ilott_v3_rows = [
        row
        for row in result_v3
        if txt(
            row.get(
                "attempt_id"
            )
        ) in ilott_ids
    ]

    print()
    print("=" * 120)
    print(
        "RESULT-MATCH V3 ILOTT CHECK"
    )
    print("=" * 120)

    print()
    print(
        "Ilott canonical attempt IDs:",
        len(
            ilott_ids
        ),
    )

    print(
        "Ilott V3 linked rows:",
        len(
            ilott_v3_rows
        ),
    )

    for row in ilott_v3_rows:

        print()
        print(
            "attempt_id:",
            txt(
                row.get(
                    "attempt_id"
                )
            ),
        )

        print(
            "  car_number:",
            repr(
                txt(
                    row.get(
                        "car_number"
                    )
                )
            ),
        )

        print(
            "  driver:",
            txt(
                row.get(
                    "driver_name"
                )
            ),
        )

        print(
            "  official speed:",
            repr(
                txt(
                    row.get(
                        "official_speed_mph"
                    )
                )
            ),
        )

        print(
            "  official status:",
            repr(
                txt(
                    row.get(
                        "official_status"
                    )
                )
            ),
        )

    # ========================================================
    # BUILD SPEED SEARCH VARIANTS
    # ========================================================

    speed_tokens = []

    for speed in speeds:

        speed_tokens.extend(
            speed_variants(
                speed
            )
        )

    speed_tokens = sorted(
        set(
            speed_tokens
        )
    )

    print()
    print(
        "Canonical speed search tokens:",
        "|".join(
            speed_tokens
        )
        if speed_tokens
        else "NONE",
    )

    # ========================================================
    # EXISTING SECONDARY CANDIDATE CSV
    # ========================================================

    evidence_rows = []

    if SECONDARY_CANDIDATES.exists():

        candidate_rows = read_csv(
            SECONDARY_CANDIDATES
        )

        ilott_candidates = []

        for row in candidate_rows:

            joined = " ".join(
                txt(value)
                for value in row.values()
            )

            if contains_target(
                joined
            ):

                ilott_candidates.append(
                    row
                )

        print()
        print("=" * 120)
        print(
            "EXISTING SECONDARY CANDIDATES"
        )
        print("=" * 120)

        print()
        print(
            "Existing Ilott candidate rows:",
            len(
                ilott_candidates
            ),
        )

        for row in ilott_candidates:

            joined = " ".join(
                txt(value)
                for value in row.values()
            )

            actions = matched_action_terms(
                joined
            )

            exact_speed_hits = [
                token
                for token in speed_tokens
                if token
                and token in joined
            ]

            print()
            print(
                "candidate_id:",
                txt(
                    row.get(
                        "candidate_id"
                    )
                ),
            )

            print(
                "source:",
                txt(
                    row.get(
                        "source_name"
                    )
                ),
            )

            sentence = (
                txt(
                    row.get(
                        "candidate_sentence"
                    )
                )
                or
                txt(
                    row.get(
                        "sentence"
                    )
                )
            )

            print(
                sentence
            )

            print(
                "actions:",
                "|".join(actions)
                if actions
                else "NONE",
            )

            print(
                "exact speed hits:",
                "|".join(
                    exact_speed_hits
                )
                if exact_speed_hits
                else "NONE",
            )

            evidence_rows.append({
                "evidence_id":
                    (
                        txt(
                            row.get(
                                "candidate_id"
                            )
                        )
                        or
                        "EXISTING_SECONDARY"
                    ),

                "source_type":
                    "EXISTING_SECONDARY_CANDIDATE",

                "source_class":
                    txt(
                        row.get(
                            "source_class"
                        )
                    )
                    or
                    "REPUTABLE_SECONDARY_EDITORIAL",

                "source_name":
                    txt(
                        row.get(
                            "source_name"
                        )
                    ),

                "source_path":
                    "",

                "sentence_index":
                    "",

                "sentence":
                    sentence,

                "context":
                    joined,

                "action_terms":
                    "|".join(
                        actions
                    ),

                "exact_speed_hits":
                    "|".join(
                        exact_speed_hits
                    ),

                "mentions_first_run":
                    str(
                        (
                            "first run"
                            in joined.lower()
                        )
                        or
                        (
                            "first attempt"
                            in joined.lower()
                        )
                    ),

                "mentions_second_run":
                    str(
                        any(
                            phrase
                            in joined.lower()
                            for phrase in [
                                "second run",
                                "second attempt",
                                "ran again",
                                "run again",
                                "another run",
                                "another attempt",
                                "rerun",
                                "re-run",
                            ]
                        )
                    ),

                "mentions_withdraw":
                    str(
                        any(
                            phrase
                            in joined.lower()
                            for phrase in [
                                "withdraw",
                                "withdrew",
                                "withdrawn",
                                "gave up",
                                "surrendered",
                            ]
                        )
                    ),

                "mentions_lane1":
                    str(
                        any(
                            phrase
                            in joined.lower()
                            for phrase in [
                                "lane 1",
                                "lane one",
                                "priority lane",
                                "priority queue",
                            ]
                        )
                    ),

                "mentions_lane2":
                    str(
                        any(
                            phrase
                            in joined.lower()
                            for phrase in [
                                "lane 2",
                                "lane two",
                            ]
                        )
                    ),

                "mentions_queue":
                    str(
                        "queue"
                        in joined.lower()
                    ),

                "promotion_status":
                    "REVIEW_REQUIRED",

                "notes":
                    (
                        "Discovery/audit only. "
                        "No chronology or action promoted."
                    ),
            })

    # ========================================================
    # LOCAL TEXT SCAN
    # ========================================================

    local_hits = []

    files_scanned = 0

    hit_counter = 1

    for root in EVIDENCE_DIRS:

        if not root.exists():
            continue

        for path in sorted(
            root.rglob("*")
        ):

            if (
                not path.is_file()
                or
                not textual_file(path)
            ):
                continue

            files_scanned += 1

            text = safe_read_text(
                path
            )

            if not text:
                continue

            sentences = split_sentences(
                text
            )

            for idx, sentence in enumerate(
                sentences
            ):

                if not contains_target(
                    sentence
                ):
                    continue

                start = max(
                    0,
                    idx - 2,
                )

                end = min(
                    len(sentences),
                    idx + 3,
                )

                context = " ".join(
                    sentences[
                        start:end
                    ]
                )

                actions = matched_action_terms(
                    context
                )

                exact_speed_hits = [
                    token
                    for token in speed_tokens
                    if (
                        token
                        and
                        token
                        in context
                    )
                ]

                source_class = (
                    source_class_for_path(
                        path
                    )
                )

                hit_id = (
                    f"R1G26-L{hit_counter:04d}"
                )

                local_hits.append({
                    "hit_id":
                        hit_id,

                    "source_class":
                        source_class,

                    "source_path":
                        str(path),

                    "sentence_index":
                        idx + 1,

                    "sentence":
                        sentence,

                    "context":
                        context,

                    "action_terms":
                        "|".join(
                            actions
                        ),

                    "exact_speed_hits":
                        "|".join(
                            exact_speed_hits
                        ),
                })

                evidence_rows.append({
                    "evidence_id":
                        hit_id,

                    "source_type":
                        "LOCAL_TEXT_HIT",

                    "source_class":
                        source_class,

                    "source_name":
                        path.name,

                    "source_path":
                        str(path),

                    "sentence_index":
                        idx + 1,

                    "sentence":
                        sentence,

                    "context":
                        context,

                    "action_terms":
                        "|".join(
                            actions
                        ),

                    "exact_speed_hits":
                        "|".join(
                            exact_speed_hits
                        ),

                    "mentions_first_run":
                        str(
                            (
                                "first run"
                                in context.lower()
                            )
                            or
                            (
                                "first attempt"
                                in context.lower()
                            )
                        ),

                    "mentions_second_run":
                        str(
                            any(
                                phrase
                                in context.lower()
                                for phrase in [
                                    "second run",
                                    "second attempt",
                                    "ran again",
                                    "run again",
                                    "another run",
                                    "another attempt",
                                    "rerun",
                                    "re-run",
                                ]
                            )
                        ),

                    "mentions_withdraw":
                        str(
                            any(
                                phrase
                                in context.lower()
                                for phrase in [
                                    "withdraw",
                                    "withdrew",
                                    "withdrawn",
                                    "gave up",
                                    "surrendered",
                                ]
                            )
                        ),

                    "mentions_lane1":
                        str(
                            any(
                                phrase
                                in context.lower()
                                for phrase in [
                                    "lane 1",
                                    "lane one",
                                    "priority lane",
                                    "priority queue",
                                ]
                            )
                        ),

                    "mentions_lane2":
                        str(
                            any(
                                phrase
                                in context.lower()
                                for phrase in [
                                    "lane 2",
                                    "lane two",
                                ]
                            )
                        ),

                    "mentions_queue":
                        str(
                            "queue"
                            in context.lower()
                        ),

                    "promotion_status":
                        "REVIEW_REQUIRED",

                    "notes":
                        (
                            "Local evidence discovery only. "
                            "No automatic promotion."
                        ),
                })

                hit_counter += 1

    print()
    print("=" * 120)
    print(
        "LOCAL EVIDENCE SCAN"
    )
    print("=" * 120)

    print()
    print(
        "Text-like files scanned:",
        files_scanned,
    )

    print(
        "Ilott local hits:",
        len(
            local_hits
        ),
    )

    for row in local_hits:

        print()
        print(
            row[
                "hit_id"
            ],
            "|",
            row[
                "source_class"
            ],
        )

        print(
            row[
                "source_path"
            ]
        )

        print(
            "actions:",
            row[
                "action_terms"
            ]
            or
            "NONE",
        )

        print(
            "exact speed hits:",
            row[
                "exact_speed_hits"
            ]
            or
            "NONE",
        )

        print(
            "sentence:"
        )

        print(
            row[
                "sentence"
            ]
        )

    # ========================================================
    # R2A RESOURCE CONTEXT
    # ========================================================

    r2a_2022_rows = []

    if R2A_COVERAGE.exists():

        coverage_rows = read_csv(
            R2A_COVERAGE
        )

        for row in coverage_rows:

            joined = " ".join(
                txt(value)
                for value in row.values()
            )

            if "2022" in joined:
                r2a_2022_rows.append(
                    row
                )

    print()
    print("=" * 120)
    print(
        "R2A 2022 RESOURCE CONTEXT"
    )
    print("=" * 120)

    print()
    print(
        "R2A 2022 coverage rows:",
        len(
            r2a_2022_rows
        ),
    )

    for row in r2a_2022_rows:

        print(
            " | ".join(
                txt(value)
                for value in row.values()
                if txt(value)
            )
        )

    # ========================================================
    # READINESS ANALYSIS
    # ========================================================

    exact_speed_evidence = [
        row
        for row in evidence_rows
        if txt(
            row.get(
                "exact_speed_hits"
            )
        )
    ]

    first_run_evidence = [
        row
        for row in evidence_rows
        if txt(
            row.get(
                "mentions_first_run"
            )
        ).lower() == "true"
    ]

    second_run_evidence = [
        row
        for row in evidence_rows
        if txt(
            row.get(
                "mentions_second_run"
            )
        ).lower() == "true"
    ]

    withdraw_evidence = [
        row
        for row in evidence_rows
        if txt(
            row.get(
                "mentions_withdraw"
            )
        ).lower() == "true"
    ]

    lane1_evidence = [
        row
        for row in evidence_rows
        if txt(
            row.get(
                "mentions_lane1"
            )
        ).lower() == "true"
    ]

    lane2_evidence = [
        row
        for row in evidence_rows
        if txt(
            row.get(
                "mentions_lane2"
            )
        ).lower() == "true"
    ]

    queue_evidence = [
        row
        for row in evidence_rows
        if txt(
            row.get(
                "mentions_queue"
            )
        ).lower() == "true"
    ]

    direct_repeat_ordering_candidates = [
        row
        for row in evidence_rows
        if (
            txt(
                row.get(
                    "mentions_first_run"
                )
            ).lower()
            ==
            "true"
            and
            txt(
                row.get(
                    "mentions_second_run"
                )
            ).lower()
            ==
            "true"
        )
    ]

    # Strong enough to move to adjudication if ANY:
    #
    # 1. exact speed + meaningful action/order language
    # 2. explicit first/second ordering
    # 3. direct historical Lane 1/2 statement
    #
    adjudication_candidates = []

    for row in evidence_rows:

        actions = txt(
            row.get(
                "action_terms"
            )
        )

        speed_hit = txt(
            row.get(
                "exact_speed_hits"
            )
        )

        first_second = (
            txt(
                row.get(
                    "mentions_first_run"
                )
            ).lower()
            ==
            "true"
            and
            txt(
                row.get(
                    "mentions_second_run"
                )
            ).lower()
            ==
            "true"
        )

        lane_direct = (
            txt(
                row.get(
                    "mentions_lane1"
                )
            ).lower()
            ==
            "true"
            or
            txt(
                row.get(
                    "mentions_lane2"
                )
            ).lower()
            ==
            "true"
        )

        if (
            (
                speed_hit
                and
                actions
            )
            or
            first_second
            or
            lane_direct
        ):

            adjudication_candidates.append(
                row
            )

    # ========================================================
    # PRINT READINESS
    # ========================================================

    print()
    print("=" * 120)
    print(
        "PROMOTION / ADJUDICATION READINESS"
    )
    print("=" * 120)

    print()
    print(
        "Total evidence rows:",
        len(
            evidence_rows
        ),
    )

    print(
        "Exact-speed evidence rows:",
        len(
            exact_speed_evidence
        ),
    )

    print(
        "First-run evidence rows:",
        len(
            first_run_evidence
        ),
    )

    print(
        "Second-run/rerun evidence rows:",
        len(
            second_run_evidence
        ),
    )

    print(
        "Withdraw/give-up evidence rows:",
        len(
            withdraw_evidence
        ),
    )

    print(
        "Lane 1 evidence rows:",
        len(
            lane1_evidence
        ),
    )

    print(
        "Lane 2 evidence rows:",
        len(
            lane2_evidence
        ),
    )

    print(
        "Queue-language evidence rows:",
        len(
            queue_evidence
        ),
    )

    print(
        "Direct first+second ordering candidates:",
        len(
            direct_repeat_ordering_candidates
        ),
    )

    print(
        "Adjudication candidates:",
        len(
            adjudication_candidates
        ),
    )

    if adjudication_candidates:

        final_status = (
            "ILOTT_REPEAT_PAIR_ADJUDICATION_READY"
        )

    elif evidence_rows:

        final_status = (
            "ILOTT_EVIDENCE_FOUND_BUT_NOT_ADJUDICATION_READY"
        )

    else:

        final_status = (
            "ILOTT_LOCAL_EVIDENCE_INSUFFICIENT"
        )

    # ========================================================
    # AUDIT TABLE
    # ========================================================

    audit_rows = [
        {
            "metric":
                "canonical_ilott_objects",

            "value":
                len(
                    ilott_canonical
                ),
        },

        {
            "metric":
                "canonical_ilott_attempt_ids",

            "value":
                len(
                    ilott_ids
                ),
        },

        {
            "metric":
                "v3_linked_rows",

            "value":
                len(
                    ilott_v3_rows
                ),
        },

        {
            "metric":
                "text_files_scanned",

            "value":
                files_scanned,
        },

        {
            "metric":
                "local_text_hits",

            "value":
                len(
                    local_hits
                ),
        },

        {
            "metric":
                "total_evidence_rows",

            "value":
                len(
                    evidence_rows
                ),
        },

        {
            "metric":
                "exact_speed_evidence_rows",

            "value":
                len(
                    exact_speed_evidence
                ),
        },

        {
            "metric":
                "first_run_evidence_rows",

            "value":
                len(
                    first_run_evidence
                ),
        },

        {
            "metric":
                "second_run_evidence_rows",

            "value":
                len(
                    second_run_evidence
                ),
        },

        {
            "metric":
                "withdraw_evidence_rows",

            "value":
                len(
                    withdraw_evidence
                ),
        },

        {
            "metric":
                "lane1_evidence_rows",

            "value":
                len(
                    lane1_evidence
                ),
        },

        {
            "metric":
                "lane2_evidence_rows",

            "value":
                len(
                    lane2_evidence
                ),
        },

        {
            "metric":
                "queue_evidence_rows",

            "value":
                len(
                    queue_evidence
                ),
        },

        {
            "metric":
                "adjudication_candidates",

            "value":
                len(
                    adjudication_candidates
                ),
        },

        {
            "metric":
                "final_status",

            "value":
                final_status,
        },
    ]

    # ========================================================
    # WRITE
    # ========================================================

    evidence_fields = [
        "evidence_id",
        "source_type",
        "source_class",
        "source_name",
        "source_path",
        "sentence_index",
        "sentence",
        "context",
        "action_terms",
        "exact_speed_hits",
        "mentions_first_run",
        "mentions_second_run",
        "mentions_withdraw",
        "mentions_lane1",
        "mentions_lane2",
        "mentions_queue",
        "promotion_status",
        "notes",
    ]

    write_csv(
        EVIDENCE_OUT,
        evidence_rows,
        evidence_fields,
    )

    write_csv(
        LOCAL_FILE_OUT,
        local_hits,
        [
            "hit_id",
            "source_class",
            "source_path",
            "sentence_index",
            "sentence",
            "context",
            "action_terms",
            "exact_speed_hits",
        ],
    )

    write_csv(
        AUDIT_OUT,
        audit_rows,
        [
            "metric",
            "value",
        ],
    )

    qa_rows = [
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
                "result_match_v2_used",

            "value":
                0,

            "status":
                "PASS",
        },

        {
            "metric":
                "identity_filtered_by_car_number",

            "value":
                0,

            "status":
                "PASS",
        },

        {
            "metric":
                "canonical_ilott_objects_found",

            "value":
                len(
                    ilott_canonical
                ),

            "status":
                (
                    "PASS"
                    if len(
                        ilott_canonical
                    ) >= 2
                    else "REVIEW"
                ),
        },

        {
            "metric":
                "all_canonical_attempts_linked_in_v3",

            "value":
                (
                    len(
                        ilott_v3_rows
                    )
                    ==
                    len(
                        ilott_ids
                    )
                ),

            "status":
                (
                    "PASS"
                    if len(
                        ilott_v3_rows
                    )
                    ==
                    len(
                        ilott_ids
                    )
                    else "FAIL"
                ),
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
                "result_row_order_used_as_chronology",

            "value":
                0,

            "status":
                "PASS",
        },

        {
            "metric":
                "withdrawn_status_used_as_lane1",

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

    # ========================================================
    # FINAL SUMMARY
    # ========================================================

    print()
    print("=" * 120)
    print(
        "FINAL SUMMARY"
    )
    print("=" * 120)

    print()
    print(
        "Ilott canonical objects:",
        len(
            ilott_canonical
        ),
    )

    print(
        "Ilott V3 linked rows:",
        len(
            ilott_v3_rows
        ),
    )

    print(
        "Evidence rows:",
        len(
            evidence_rows
        ),
    )

    print(
        "Adjudication candidates:",
        len(
            adjudication_candidates
        ),
    )

    print()
    print(
        "R2A official lane/queue/live reconnaissance "
        "is treated as architecture/resource context only."
    )

    print(
        "No historical Lane 1/Lane 2 is inferred from R2A."
    )

    print(
        "No Results row ordering is used as chronology."
    )

    print(
        "No Withdrawn status is treated as Lane 1."
    )

    print(
        "No queue wait is inferred."
    )

    print(
        "No canonical or Phase 5–8 data was modified."
    )

    print()
    print("=" * 120)
    print(
        "FINAL STATUS:",
        final_status,
    )
    print("=" * 120)

    print()
    print("OUTPUTS")
    print(EVIDENCE_OUT)
    print(LOCAL_FILE_OUT)
    print(AUDIT_OUT)
    print(QA_OUT)


if __name__ == "__main__":
    main()
