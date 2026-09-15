from pathlib import Path
import csv
import re
from collections import defaultdict


# ============================================================
# PHASE
# ============================================================

PHASE = "R1G.22"


# ============================================================
# INPUTS
# ============================================================

CANONICAL = Path(
    "data/canonical/v1/attempts.csv"
)

RESULT_MATCHES = Path(
    "weather/output/"
    "chronology_rescue_2022_result_to_canonical_attempt_matches_v3.csv"
)

ADJUDICATED_SECONDARY = Path(
    "weather/output/"
    "chronology_rescue_2022_secondary_adjudicated_evidence_v1.csv"
)

SECONDARY_CANDIDATES = Path(
    "weather/output/"
    "chronology_rescue_2022_secondary_editorial_candidates_v1.csv"
)

WEATHER_WINDOWS = Path(
    "weather/output/"
    "chronology_rescue_2022_weather_interruption_windows_v1.csv"
)

THE_RACE_TEXT = Path(
    "weather/evidence/rescue/"
    "secondary_2022_high_priority_chronology/"
    "article_text/THE_RACE_2022_DAY1.txt"
)

NBC_TEXT = Path(
    "weather/evidence/rescue/"
    "secondary_2022_high_priority_chronology/"
    "article_text/NBC_2022_DAY1.txt"
)


# ============================================================
# OUTPUTS
# ============================================================

OUTPUT_DIR = Path(
    "weather/output"
)

AUDIT_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_karam_attempt_identity_audit_v1.csv"
)

EVIDENCE_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_karam_identity_evidence_v1.csv"
)

PROMOTION_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_karam_identity_promotion_candidate_v1.csv"
)

QA_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_karam_attempt_identity_audit_v1_qa.csv"
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

    if not value:
        return ""

    try:
        return str(
            int(
                float(value)
            )
        )
    except Exception:
        return value.lstrip("0") or "0"


def is_2022(row):
    return (
        txt(
            row.get("year")
        ) == "2022"
        or
        "2022" in txt(
            row.get("session_id")
        )
    )


def speed_close(a, b, tol=0.003):
    try:
        return abs(
            float(txt(a))
            -
            float(txt(b))
        ) <= tol
    except Exception:
        return False


def split_sentences(text):
    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return [
        x.strip()
        for x in re.split(
            r"(?<=[.!?])\s+",
            text,
        )
        if x.strip()
    ]


def karam_context_sentences(text, radius=1):
    sentences = split_sentences(
        text
    )

    hits = []

    for i, sentence in enumerate(
        sentences
    ):

        if (
            "karam" not in sentence.lower()
            and
            "sage" not in sentence.lower()
        ):
            continue

        start = max(
            0,
            i - radius,
        )

        end = min(
            len(sentences),
            i + radius + 1,
        )

        context = " ".join(
            sentences[
                start:end
            ]
        )

        hits.append({
            "sentence_index":
                i + 1,

            "sentence":
                sentence,

            "context":
                context,
        })

    return hits


def contains_any(text, phrases):
    lower = txt(text).lower()

    return any(
        phrase.lower() in lower
        for phrase in phrases
    )


def contains_all(text, phrases):
    lower = txt(text).lower()

    return all(
        phrase.lower() in lower
        for phrase in phrases
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
        "R1G.22 — 2022 SAGE KARAM "
        "ATTEMPT IDENTITY RESCUE V1"
    )
    print("=" * 120)

    required_inputs = [
        CANONICAL,
        RESULT_MATCHES,
        ADJUDICATED_SECONDARY,
        SECONDARY_CANDIDATES,
        WEATHER_WINDOWS,
    ]

    missing = []

    print()
    print("INPUT CHECK")
    print("-" * 120)

    for path in required_inputs:

        exists = path.exists()

        print(
            f"{path}: "
            f"{'PRESENT' if exists else 'MISSING'}"
        )

        if not exists:
            missing.append(
                path
            )

    print(
        f"{THE_RACE_TEXT}: "
        f"{'PRESENT' if THE_RACE_TEXT.exists() else 'MISSING_OPTIONAL'}"
    )

    print(
        f"{NBC_TEXT}: "
        f"{'PRESENT' if NBC_TEXT.exists() else 'MISSING_OPTIONAL'}"
    )

    if missing:

        print()
        print(
            "FINAL STATUS: "
            "KARAM_ATTEMPT_IDENTITY_RESCUE_INPUT_MISSING"
        )
        return

    canonical = read_csv(
        CANONICAL
    )

    results = read_csv(
        RESULT_MATCHES
    )

    adjudicated = read_csv(
        ADJUDICATED_SECONDARY
    )

    candidates = read_csv(
        SECONDARY_CANDIDATES
    )

    weather = read_csv(
        WEATHER_WINDOWS
    )

    # ========================================================
    # KARAM CANONICAL OBJECTS
    # ========================================================

    canonical_karam = [
        row
        for row in canonical
        if (
            is_2022(row)
            and
            norm_car(
                row.get(
                    "car_number"
                )
            ) == "24"
        )
    ]

    result_karam = [
        row
        for row in results
        if norm_car(
            row.get(
                "car_number"
            )
        ) == "24"
    ]

    print()
    print("=" * 120)
    print(
        "KARAM CANONICAL / OFFICIAL RESULT OBJECTS"
    )
    print("=" * 120)

    print()
    print(
        "Canonical Karam objects:",
        len(
            canonical_karam
        ),
    )

    for row in canonical_karam:

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
            "  index:",
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
                txt(
                    row.get(
                        "four_lap_average_speed_mph"
                    )
                )
            ),
        )

        print(
            "  class:",
            txt(
                row.get(
                    "attempt_class"
                )
            ),
        )

        print(
            "  canonical status:",
            txt(
                row.get(
                    "result_status"
                )
            ),
        )

        print(
            "  locator:",
            txt(
                row.get(
                    "source_native_locator"
                )
            ),
        )

    print()
    print(
        "Official result-linked Karam rows:",
        len(
            result_karam
        ),
    )

    for row in result_karam:

        print()
        print(
            "official row:",
            txt(
                row.get(
                    "official_result_row"
                )
            ),
        )

        print(
            "  attempt_id:",
            txt(
                row.get(
                    "attempt_id"
                )
            ),
        )

        print(
            "  speed:",
            repr(
                txt(
                    row.get(
                        "official_speed_mph"
                    )
                )
            ),
        )

        print(
            "  status:",
            repr(
                txt(
                    row.get(
                        "official_status"
                    )
                )
            ),
        )

    # ========================================================
    # IDENTIFY THE THREE EXPECTED KARAM OBJECTS
    # ========================================================

    karam_229905 = [
        row
        for row in result_karam
        if speed_close(
            row.get(
                "official_speed_mph"
            ),
            "229.905",
        )
    ]

    karam_230464 = [
        row
        for row in result_karam
        if speed_close(
            row.get(
                "official_speed_mph"
            ),
            "230.464",
        )
    ]

    karam_no_attempt = [
        row
        for row in result_karam
        if txt(
            row.get(
                "official_status"
            )
        ) == "No Attempt"
    ]

    print()
    print("=" * 120)
    print(
        "EXPECTED KARAM TARGET CHECK"
    )
    print("=" * 120)

    print(
        "229.905 rows:",
        len(
            karam_229905
        ),
    )

    print(
        "230.464 rows:",
        len(
            karam_230464
        ),
    )

    print(
        "No Attempt rows:",
        len(
            karam_no_attempt
        ),
    )

    target_structure_ok = all([
        len(
            karam_229905
        ) == 1,
        len(
            karam_230464
        ) == 1,
        len(
            karam_no_attempt
        ) == 1,
    ])

    # ========================================================
    # EXISTING PROMOTED KARAM EVENT
    # ========================================================

    promoted_karam_events = [
        row
        for row in adjudicated
        if txt(
            row.get(
                "evidence_id"
            )
        ) == "R1G19-KARAM-POST-RESTART-EVENT"
    ]

    print()
    print("=" * 120)
    print(
        "EXISTING KARAM POST-RESTART EVENT"
    )
    print("=" * 120)

    print()
    print(
        "Promoted event rows:",
        len(
            promoted_karam_events
        ),
    )

    for row in promoted_karam_events:

        print(
            "relation:",
            txt(
                row.get(
                    "relation"
                )
            ),
        )

        print(
            "lower bound:",
            txt(
                row.get(
                    "time_lower_utc"
                )
            ),
        )

        print(
            "subject attempt:",
            repr(
                txt(
                    row.get(
                        "subject_attempt_id"
                    )
                )
            ),
        )

        print(
            "promotion:",
            txt(
                row.get(
                    "promotion_status"
                )
            ),
        )

    # ========================================================
    # WEATHER WINDOWS
    # ========================================================

    print()
    print("=" * 120)
    print(
        "WEATHER EVENT CONTEXT"
    )
    print("=" * 120)

    relevant_weather = []

    for row in weather:

        joined = " ".join(
            txt(value)
            for value in row.values()
        )

        if contains_any(
            joined,
            [
                "FIRST_WEATHER_STOP",
                "FIRST_WEATHER_HOLD_LIFTED",
                "SECOND_WEATHER_STOP",
                "SESSION_CALLED",
            ],
        ):

            relevant_weather.append(
                row
            )

    for row in relevant_weather:

        values = [
            txt(v)
            for v in row.values()
            if txt(v)
        ]

        print(
            " | ".join(
                values
            )
        )

    # ========================================================
    # LOCAL SECONDARY TEXT MINING
    # ========================================================

    evidence_rows = []

    def add_text_evidence(
        source_id,
        source_name,
        path,
    ):

        if not path.exists():
            return

        text = path.read_text(
            encoding="utf-8",
            errors="replace",
        )

        contexts = karam_context_sentences(
            text,
            radius=1,
        )

        for context in contexts:

            blob = context[
                "context"
            ]

            speeds = re.findall(
                r"\b(?:229\.905|230\.464)\b",
                blob,
            )

            evidence_rows.append({
                "source_id":
                    source_id,

                "source_name":
                    source_name,

                "source_class":
                    "REPUTABLE_SECONDARY_EDITORIAL",

                "sentence_index":
                    context[
                        "sentence_index"
                    ],

                "sentence":
                    context[
                        "sentence"
                    ],

                "context":
                    blob,

                "mentions_229_905":
                    "229.905"
                    in blob,

                "mentions_230_464":
                    "230.464"
                    in blob,

                "mentions_no_attempt":
                    contains_any(
                        blob,
                        [
                            "no attempt",
                            "did not complete",
                            "unable to complete",
                            "aborted",
                            "stopped",
                        ],
                    ),

                "mentions_track_reopened":
                    contains_any(
                        blob,
                        [
                            "track re-opened",
                            "track reopened",
                            "resumed",
                            "restarted",
                            "after the delay",
                        ],
                    ),

                "mentions_first_weather_stop":
                    contains_any(
                        blob,
                        [
                            "rain hit",
                            "rain fell",
                            "first rain",
                            "first delay",
                            "weather delay",
                        ],
                    ),

                "mentions_second_weather_stop":
                    contains_any(
                        blob,
                        [
                            "lightning struck",
                            "heavier rain",
                            "second delay",
                            "second stoppage",
                        ],
                    ),

                "mentions_improve":
                    contains_any(
                        blob,
                        [
                            "improve",
                            "improved",
                            "unable to improve",
                        ],
                    ),

                "explicit_speed_tokens":
                    "|".join(
                        speeds
                    ),

                "identity_promotion":
                    "False",

                "notes":
                    (
                        "Context discovery only. "
                        "No attempt identity promoted automatically."
                    ),
            })

    add_text_evidence(
        "THE_RACE_2022_DAY1",
        "The Race",
        THE_RACE_TEXT,
    )

    add_text_evidence(
        "NBC_2022_DAY1",
        "NBC Sports",
        NBC_TEXT,
    )

    # ========================================================
    # EXISTING CANDIDATE CSV KARAM ROWS
    # ========================================================

    karam_candidates = [
        row
        for row in candidates
        if txt(
            row.get(
                "driver_name"
            )
        ) == "Sage Karam"
    ]

    print()
    print("=" * 120)
    print(
        "KARAM SECONDARY CANDIDATES"
    )
    print("=" * 120)

    print()
    print(
        "Candidate rows:",
        len(
            karam_candidates
        ),
    )

    for row in karam_candidates:

        print()
        print(
            txt(
                row.get(
                    "candidate_id"
                )
            ),
            "|",
            txt(
                row.get(
                    "source_name"
                )
            ),
        )

        print(
            txt(
                row.get(
                    "candidate_sentence"
                )
            )
        )

    # ========================================================
    # EVIDENCE DISCRIMINATORS
    # ========================================================

    direct_post_restart_230464 = [
        row
        for row in evidence_rows
        if (
            row[
                "mentions_230_464"
            ]
            and
            row[
                "mentions_track_reopened"
            ]
        )
    ]

    direct_post_restart_229905 = [
        row
        for row in evidence_rows
        if (
            row[
                "mentions_229_905"
            ]
            and
            row[
                "mentions_track_reopened"
            ]
        )
    ]

    direct_no_attempt_weather = [
        row
        for row in evidence_rows
        if (
            row[
                "mentions_no_attempt"
            ]
            and
            row[
                "mentions_first_weather_stop"
            ]
        )
    ]

    print()
    print("=" * 120)
    print(
        "IDENTITY DISCRIMINATOR CHECK"
    )
    print("=" * 120)

    print()
    print(
        "Explicit post-restart + 230.464 contexts:",
        len(
            direct_post_restart_230464
        ),
    )

    print(
        "Explicit post-restart + 229.905 contexts:",
        len(
            direct_post_restart_229905
        ),
    )

    print(
        "Explicit No Attempt + first-weather-stop contexts:",
        len(
            direct_no_attempt_weather
        ),
    )

    # ========================================================
    # PROMOTION POLICY
    # ========================================================
    #
    # We only allow exact canonical identity promotion when:
    #
    # 1. the canonical target structure is unique;
    # 2. the existing Karam post-restart event exists;
    # 3. a reputable source context explicitly mentions
    #    BOTH the post-restart situation and one exact speed.
    #
    # Generic "unable to improve after restart" is NOT enough
    # to choose between 229.905 / 230.464 / No Attempt.
    #
    # ========================================================

    promotion_rows = []

    promotion_status = (
        "KARAM_ATTEMPT_IDENTITY_REMAINS_UNRESOLVED"
    )

    if (
        target_structure_ok
        and
        len(
            promoted_karam_events
        ) == 1
        and
        len(
            direct_post_restart_230464
        ) >= 1
        and
        len(
            direct_post_restart_229905
        ) == 0
    ):

        promotion_rows.append({
            "promotion_id":
                "R1G22-KARAM-POST-RESTART-230464",

            "driver_name":
                "Sage Karam",

            "car_number":
                "24",

            "event_id":
                "KARAM_POST_RESTART_ATTEMPT_EVENT",

            "attempt_id":
                txt(
                    karam_230464[0].get(
                        "attempt_id"
                    )
                ),

            "speed_mph":
                "230.464",

            "official_status":
                txt(
                    karam_230464[0].get(
                        "official_status"
                    )
                ),

            "identity_quality":
                "DIRECT_SECONDARY_SPEED_EVENT_MATCH",

            "chronology_relation":
                "FIRST_WEATHER_HOLD_LIFTED_BEFORE_ATTEMPT",

            "time_lower_utc":
                "2022-05-21T19:34:00Z",

            "promotion_ready":
                "True",

            "canonical_mutated":
                "False",

            "notes":
                (
                    "Promotion candidate only. "
                    "Exact speed and post-restart context "
                    "are co-mentioned by reputable secondary evidence."
                ),
        })

        promotion_status = (
            "KARAM_ATTEMPT_IDENTITY_PROMOTION_READY"
        )

    elif (
        target_structure_ok
        and
        len(
            promoted_karam_events
        ) == 1
        and
        len(
            direct_post_restart_229905
        ) >= 1
        and
        len(
            direct_post_restart_230464
        ) == 0
    ):

        promotion_rows.append({
            "promotion_id":
                "R1G22-KARAM-POST-RESTART-229905",

            "driver_name":
                "Sage Karam",

            "car_number":
                "24",

            "event_id":
                "KARAM_POST_RESTART_ATTEMPT_EVENT",

            "attempt_id":
                txt(
                    karam_229905[0].get(
                        "attempt_id"
                    )
                ),

            "speed_mph":
                "229.905",

            "official_status":
                txt(
                    karam_229905[0].get(
                        "official_status"
                    )
                ),

            "identity_quality":
                "DIRECT_SECONDARY_SPEED_EVENT_MATCH",

            "chronology_relation":
                "FIRST_WEATHER_HOLD_LIFTED_BEFORE_ATTEMPT",

            "time_lower_utc":
                "2022-05-21T19:34:00Z",

            "promotion_ready":
                "True",

            "canonical_mutated":
                "False",

            "notes":
                (
                    "Promotion candidate only. "
                    "Exact speed and post-restart context "
                    "are co-mentioned by reputable secondary evidence."
                ),
        })

        promotion_status = (
            "KARAM_ATTEMPT_IDENTITY_PROMOTION_READY"
        )

    # ========================================================
    # AUDIT TABLE
    # ========================================================

    audit_rows = [
        {
            "check":
                "canonical_karam_objects",

            "value":
                len(
                    canonical_karam
                ),

            "interpretation":
                "Expected three canonical Karam objects.",
        },

        {
            "check":
                "unique_229_905",

            "value":
                len(
                    karam_229905
                ),

            "interpretation":
                "Unique Karam 229.905 official result link.",
        },

        {
            "check":
                "unique_230_464",

            "value":
                len(
                    karam_230464
                ),

            "interpretation":
                "Unique Karam 230.464 official result link.",
        },

        {
            "check":
                "unique_no_attempt",

            "value":
                len(
                    karam_no_attempt
                ),

            "interpretation":
                "Unique Karam No Attempt result link.",
        },

        {
            "check":
                "existing_post_restart_event",

            "value":
                len(
                    promoted_karam_events
                ),

            "interpretation":
                (
                    "Existing adjudicated event-level evidence "
                    "without specific attempt identity."
                ),
        },

        {
            "check":
                "direct_post_restart_230464",

            "value":
                len(
                    direct_post_restart_230464
                ),

            "interpretation":
                (
                    "Exact speed 230.464 co-mentioned with "
                    "post-restart context."
                ),
        },

        {
            "check":
                "direct_post_restart_229905",

            "value":
                len(
                    direct_post_restart_229905
                ),

            "interpretation":
                (
                    "Exact speed 229.905 co-mentioned with "
                    "post-restart context."
                ),
        },

        {
            "check":
                "direct_no_attempt_weather",

            "value":
                len(
                    direct_no_attempt_weather
                ),

            "interpretation":
                (
                    "No-Attempt identity explicitly connected "
                    "to first weather stoppage."
                ),
        },

        {
            "check":
                "promotion_candidate_rows",

            "value":
                len(
                    promotion_rows
                ),

            "interpretation":
                promotion_status,
        },
    ]

    # ========================================================
    # WRITE
    # ========================================================

    write_csv(
        AUDIT_OUT,
        audit_rows,
        [
            "check",
            "value",
            "interpretation",
        ],
    )

    write_csv(
        EVIDENCE_OUT,
        evidence_rows,
        [
            "source_id",
            "source_name",
            "source_class",
            "sentence_index",
            "sentence",
            "context",
            "mentions_229_905",
            "mentions_230_464",
            "mentions_no_attempt",
            "mentions_track_reopened",
            "mentions_first_weather_stop",
            "mentions_second_weather_stop",
            "mentions_improve",
            "explicit_speed_tokens",
            "identity_promotion",
            "notes",
        ],
    )

    write_csv(
        PROMOTION_OUT,
        promotion_rows,
        [
            "promotion_id",
            "driver_name",
            "car_number",
            "event_id",
            "attempt_id",
            "speed_mph",
            "official_status",
            "identity_quality",
            "chronology_relation",
            "time_lower_utc",
            "promotion_ready",
            "canonical_mutated",
            "notes",
        ],
    )

    # ========================================================
    # QA
    # ========================================================

    qa_rows = [
        {
            "metric":
                "target_structure_unique",

            "value":
                int(
                    target_structure_ok
                ),

            "status":
                (
                    "PASS"
                    if target_structure_ok
                    else "FAIL"
                ),
        },

        {
            "metric":
                "existing_post_restart_event_rows",

            "value":
                len(
                    promoted_karam_events
                ),

            "status":
                (
                    "PASS"
                    if len(
                        promoted_karam_events
                    ) == 1
                    else "FAIL"
                ),
        },

        {
            "metric":
                "promotion_rows",

            "value":
                len(
                    promotion_rows
                ),

            "status":
                (
                    "PASS"
                    if len(
                        promotion_rows
                    ) <= 1
                    else "FAIL"
                ),
        },

        {
            "metric":
                "generic_post_restart_text_used_as_exact_identity",

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

    # ========================================================
    # FINAL
    # ========================================================

    print()
    print("=" * 120)
    print(
        "FINAL IDENTITY ASSESSMENT"
    )
    print("=" * 120)

    print()
    print(
        "229.905 attempt_id:",
        (
            txt(
                karam_229905[0].get(
                    "attempt_id"
                )
            )
            if len(
                karam_229905
            ) == 1
            else "UNRESOLVED"
        ),
    )

    print(
        "230.464 attempt_id:",
        (
            txt(
                karam_230464[0].get(
                    "attempt_id"
                )
            )
            if len(
                karam_230464
            ) == 1
            else "UNRESOLVED"
        ),
    )

    print(
        "No Attempt attempt_id:",
        (
            txt(
                karam_no_attempt[0].get(
                    "attempt_id"
                )
            )
            if len(
                karam_no_attempt
            ) == 1
            else "UNRESOLVED"
        ),
    )

    print()
    print(
        "Direct post-restart 230.464 evidence:",
        len(
            direct_post_restart_230464
        ),
    )

    print(
        "Direct post-restart 229.905 evidence:",
        len(
            direct_post_restart_229905
        ),
    )

    print(
        "Direct first-weather-stop No Attempt evidence:",
        len(
            direct_no_attempt_weather
        ),
    )

    print()
    print(
        "Promotion candidate rows:",
        len(
            promotion_rows
        ),
    )

    if not promotion_rows:

        print()
        print(
            "Current evidence proves a post-restart "
            "Karam attempt event, but does not yet "
            "uniquely identify the canonical attempt."
        )

        print(
            "No identity is promoted."
        )

    else:

        print()
        print(
            "A unique promotion candidate is supported "
            "by an exact-speed + event-context match."
        )

        for row in promotion_rows:

            print(
                "attempt_id:",
                row[
                    "attempt_id"
                ],
            )

            print(
                "speed:",
                row[
                    "speed_mph"
                ],
            )

    print()
    print(
        "No result-row ordering was used as chronology."
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
        "FINAL STATUS:",
        promotion_status,
    )
    print("=" * 120)

    print()
    print("OUTPUTS")
    print(AUDIT_OUT)
    print(EVIDENCE_OUT)
    print(PROMOTION_OUT)
    print(QA_OUT)


if __name__ == "__main__":
    main()
