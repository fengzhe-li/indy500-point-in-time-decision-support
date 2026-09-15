from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

import csv
import hashlib
import html
import json
import re
import time


# ============================================================
# PHASE
# ============================================================

PHASE = "R1G.4"

POLICY_VERSION = (
    "2022_OFFICIAL_EDITORIAL_CHRONOLOGY_CANDIDATE_MINING_V1"
)


# ============================================================
# INPUT
# ============================================================

RESULT_ROWS = Path(
    "weather/output/"
    "official_day1_results_attempt_rows_v1.csv"
)


# ============================================================
# OFFICIAL SOURCE SET
#
# Deliberately small and targeted.
# No broad web crawl.
# ============================================================

SOURCES = [
    {
        "source_id":
            "INDYCAR_2022_DAY1_RECAP",

        "url":
            "https://www.indycar.com/news/"
            "2022/05/05-21-day1-quals",

        "source_class":
            "INDYCAR_OFFICIAL_EDITORIAL",
    },

    {
        "source_id":
            "INDYCAR_2022_SATO_BUZZ",

        "url":
            "https://www.indycar.com/news/"
            "2022/05/05-21-buzz",

        "source_class":
            "INDYCAR_OFFICIAL_EDITORIAL",
    },

    {
        "source_id":
            "INDYCAR_2022_GANASSI",

        "url":
            "https://www.indycar.com/news/"
            "2022/05/05-21-ganassi",

        "source_class":
            "INDYCAR_OFFICIAL_EDITORIAL",
    },

    {
        "source_id":
            "INDYCAR_2022_QUALS_CHANGE",

        "url":
            "https://www.indycar.com/News/"
            "2022/05/05-20-QualsChange",

        "source_class":
            "INDYCAR_OFFICIAL_EDITORIAL",
    },

    {
        "source_id":
            "INDYCAR_2022_QUALFORMAT",

        "url":
            "https://www.indycar.com/news/"
            "2022/05/05-20-qualformat",

        "source_class":
            "INDYCAR_OFFICIAL_EDITORIAL",
    },

    {
        "source_id":
            "INDYCAR_2022_MORNING_PRACTICE",

        "url":
            "https://www.indycar.com/news/"
            "2022/05/05-21-morningpractice",

        "source_class":
            "INDYCAR_OFFICIAL_EDITORIAL",
    },
]


# ============================================================
# OUTPUT
# ============================================================

EVIDENCE_DIR = Path(
    "weather/evidence/rescue/"
    "official_2022_editorial_chronology"
)

RAW_HTML_DIR = (
    EVIDENCE_DIR
    / "raw_html"
)

TEXT_DIR = (
    EVIDENCE_DIR
    / "article_text"
)

OUTPUT_DIR = Path(
    "weather/output"
)

SOURCE_AUDIT_CSV = (
    OUTPUT_DIR
    / "chronology_rescue_2022_editorial_source_audit_v1.csv"
)

CANDIDATE_CSV = (
    OUTPUT_DIR
    / "chronology_rescue_2022_editorial_candidates_v1.csv"
)

ENTITY_MATCH_CSV = (
    OUTPUT_DIR
    / "chronology_rescue_2022_editorial_entity_matches_v1.csv"
)

QA_CSV = (
    OUTPUT_DIR
    / "chronology_rescue_2022_editorial_candidate_mining_v1_qa.csv"
)


# ============================================================
# NETWORK
# ============================================================

USER_AGENT = (
    "Mozilla/5.0 "
    "(compatible; Indy500HistoricalEvidenceResearch/1.0)"
)

TIMEOUT = 30
DELAY = 0.7


# ============================================================
# KEYWORD GROUPS
# ============================================================

EXPLICIT_TIME_PATTERNS = [
    r"\b\d{1,2}:\d{2}\s*(?:a\.?m\.?|p\.?m\.?)\b",
    r"\b\d{1,2}\s*(?:a\.?m\.?|p\.?m\.?)\b",
]

RELATIVE_TIME_TERMS = [
    "first 15 minutes",
    "first fifteen minutes",
    "90 minutes",
    "last hour",
    "final hour",
    "final minutes",
    "last minutes",
    "minutes remaining",
    "hour remaining",
    "shortly after",
    "shortly before",
    "later",
    "earlier",
    "after",
    "before",
    "next",
    "then",
    "followed",
    "following",
]

INTERRUPTION_TERMS = [
    "rain",
    "lightning",
    "interrupted",
    "delay",
    "delayed",
    "resumed",
    "resume",
    "restart",
    "restarted",
    "stopped",
    "halted",
    "cut short",
    "red flag",
]

ATTEMPT_TERMS = [
    "attempt",
    "attempts",
    "qualifying run",
    "qualification",
    "requalify",
    "requalified",
    "second attempt",
    "another attempt",
    "next driver",
    "next qualifying run",
]

ACTION_TERMS = [
    "withdraw",
    "withdrawn",
    "withdrew",
    "priority",
    "lane 1",
    "lane 2",
    "lane",
    "bumped",
    "waved off",
    "failed attempt",
    "invalidated",
    "penalized",
]

SESSION_TERMS = [
    "qualifying",
    "session",
    "first rain",
    "track temperature",
    "weather",
]


# ============================================================
# KNOWN 2022 CAR / DRIVER MAP
# ============================================================

KNOWN_DRIVERS = {
    "Rinus VeeKay": "21",
    "Pato O'Ward": "5",
    "Pato O’Ward": "5",
    "Felix Rosenqvist": "7",
    "Takuma Sato": "51",
    "Marco Andretti": "98",
    "Scott McLaughlin": "3",
    "Alexander Rossi": "27",
    "Helio Castroneves": "06",
    "Sage Karam": "24",
    "Josef Newgarden": "2",
    "David Malukas": "18",
    "Alex Palou": "10",
    "Tony Kanaan": "1",
    "Jimmie Johnson": "48",
    "Marcus Ericsson": "8",
    "Scott Dixon": "9",
    "Will Power": "12",
    "Romain Grosjean": "28",
}


# ============================================================
# HELPERS
# ============================================================

def read_csv(path):

    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as handle:

        return list(
            csv.DictReader(
                handle
            )
        )


def write_csv(
    path,
    rows,
    fields,
):

    with path.open(
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as handle:

        writer = csv.DictWriter(
            handle,
            fieldnames=fields,
        )

        writer.writeheader()
        writer.writerows(rows)


def sha256_bytes(data):

    return hashlib.sha256(
        data
    ).hexdigest()


def normalize_space(text):

    return re.sub(
        r"\s+",
        " ",
        text,
    ).strip()


def normalize_car(value):

    text = str(
        value or ""
    ).strip()

    if not text:
        return ""

    try:
        return str(
            int(
                float(
                    text
                )
            )
        )

    except Exception:
        return (
            text.lstrip("0")
            or "0"
        )


def fetch(url):

    request = Request(
        url,
        headers={
            "User-Agent":
                USER_AGENT,

            "Accept":
                "text/html,application/xhtml+xml,*/*;q=0.8",
        },
    )

    try:

        with urlopen(
            request,
            timeout=TIMEOUT,
        ) as response:

            body = response.read()

            return {
                "ok":
                    True,

                "status":
                    getattr(
                        response,
                        "status",
                        200,
                    ),

                "final_url":
                    response.geturl(),

                "content_type":
                    response.headers.get(
                        "Content-Type",
                        "",
                    ),

                "body":
                    body,

                "error":
                    "",
            }

    except HTTPError as exc:

        return {
            "ok":
                False,

            "status":
                exc.code,

            "final_url":
                url,

            "content_type":
                "",

            "body":
                b"",

            "error":
                f"HTTPError: {exc}",
        }

    except URLError as exc:

        return {
            "ok":
                False,

            "status":
                "",

            "final_url":
                url,

            "content_type":
                "",

            "body":
                b"",

            "error":
                f"URLError: {exc}",
        }

    except Exception as exc:

        return {
            "ok":
                False,

            "status":
                "",

            "final_url":
                url,

            "content_type":
                "",

            "body":
                b"",

            "error":
                (
                    f"{type(exc).__name__}: "
                    f"{exc}"
                ),
        }


def decode_html(body):

    for encoding in [
        "utf-8",
        "utf-8-sig",
        "latin-1",
    ]:

        try:

            return body.decode(
                encoding
            )

        except Exception:
            pass

    return body.decode(
        "utf-8",
        errors="replace",
    )


def html_to_text(source):

    # Remove script/style/noscript.
    source = re.sub(
        r"<script\b[^>]*>.*?</script>",
        " ",
        source,
        flags=(
            re.IGNORECASE
            | re.DOTALL
        ),
    )

    source = re.sub(
        r"<style\b[^>]*>.*?</style>",
        " ",
        source,
        flags=(
            re.IGNORECASE
            | re.DOTALL
        ),
    )

    source = re.sub(
        r"<noscript\b[^>]*>.*?</noscript>",
        " ",
        source,
        flags=(
            re.IGNORECASE
            | re.DOTALL
        ),
    )

    # Add line breaks around paragraph-ish tags.
    source = re.sub(
        r"</?(?:p|div|article|section|li|h1|h2|h3|br)\b[^>]*>",
        "\n",
        source,
        flags=re.IGNORECASE,
    )

    source = re.sub(
        r"<[^>]+>",
        " ",
        source,
    )

    source = html.unescape(
        source
    )

    lines = []

    for line in source.splitlines():

        line = normalize_space(
            line
        )

        if not line:
            continue

        lines.append(
            line
        )

    return "\n".join(
        lines
    )


def split_sentences(text):

    # Good enough for evidence discovery.
    chunks = re.split(
        r"(?<=[.!?])\s+(?=[A-Z0-9“\"'])",
        normalize_space(
            text.replace(
                "\n",
                " "
            )
        ),
    )

    return [
        normalize_space(
            chunk
        )
        for chunk in chunks
        if len(
            normalize_space(
                chunk
            )
        ) >= 20
    ]


def find_terms(
    sentence,
    terms,
):

    lower = sentence.lower()

    return [
        term
        for term in terms
        if term.lower() in lower
    ]


def find_explicit_times(
    sentence,
):

    matches = []

    for pattern in (
        EXPLICIT_TIME_PATTERNS
    ):

        for match in re.finditer(
            pattern,
            sentence,
            flags=re.IGNORECASE,
        ):

            value = normalize_space(
                match.group(0)
            )

            if value not in matches:
                matches.append(
                    value
                )

    return matches


def detect_drivers(
    sentence,
):

    detected = []

    lower = sentence.lower()

    for name, car in (
        KNOWN_DRIVERS.items()
    ):

        if name.lower() in lower:

            pair = (
                name,
                normalize_car(
                    car
                ),
            )

            if pair not in detected:

                detected.append(
                    pair
                )

    return detected


def find_speed_values(
    sentence,
):

    values = []

    for match in re.finditer(
        r"\b(\d{3}\.\d{3})\s*(?:mph)?\b",
        sentence,
        flags=re.IGNORECASE,
    ):

        value = match.group(
            1
        )

        if value not in values:
            values.append(
                value
            )

    return values


def match_result_rows(
    results,
    driver_pairs,
    speeds,
):

    matches = []

    for driver_name, car in (
        driver_pairs
    ):

        car_norm = normalize_car(
            car
        )

        candidates = [
            row
            for row in results
            if (
                str(
                    row.get(
                        "year",
                        "",
                    )
                ).strip()
                == "2022"
                and
                normalize_car(
                    row.get(
                        "car_number"
                    )
                )
                == car_norm
            )
        ]

        if speeds:

            speed_candidates = [
                row
                for row in candidates
                if str(
                    row.get(
                        "speed_avg_mph",
                        "",
                    )
                ).strip()
                in speeds
            ]

            if speed_candidates:
                candidates = (
                    speed_candidates
                )

        for row in candidates:

            key = (
                car_norm,
                str(
                    row.get(
                        "speed_avg_mph",
                        "",
                    )
                ).strip(),
                str(
                    row.get(
                        "result_row",
                        "",
                    )
                ).strip(),
            )

            if key not in [
                (
                    existing[
                        "car_number"
                    ],
                    existing[
                        "speed_mph"
                    ],
                    existing[
                        "result_row"
                    ],
                )
                for existing in matches
            ]:

                matches.append({
                    "driver_name":
                        driver_name,

                    "car_number":
                        car_norm,

                    "speed_mph":
                        str(
                            row.get(
                                "speed_avg_mph",
                                "",
                            )
                        ).strip(),

                    "result_row":
                        str(
                            row.get(
                                "result_row",
                                "",
                            )
                        ).strip(),

                    "result_status":
                        str(
                            row.get(
                                "status",
                                "",
                            )
                        ).strip(),

                    "source_file":
                        str(
                            row.get(
                                "source_file",
                                "",
                            )
                        ).strip(),

                    "source_line_number":
                        str(
                            row.get(
                                "source_line_number",
                                "",
                            )
                        ).strip(),
                })

    return matches


def classify_candidate(
    explicit_times,
    relative_terms,
    interruption_terms,
    attempt_terms,
    action_terms,
    driver_pairs,
):

    classes = []

    if explicit_times:
        classes.append(
            "EXPLICIT_CLOCK_TIME_MENTION"
        )

    if relative_terms:
        classes.append(
            "RELATIVE_TIME_OR_ORDERING_LANGUAGE"
        )

    if interruption_terms:
        classes.append(
            "SESSION_INTERRUPTION_OR_WEATHER"
        )

    if attempt_terms:
        classes.append(
            "ATTEMPT_OR_RUN_LANGUAGE"
        )

    if action_terms:
        classes.append(
            "ACTION_OR_LANE_LANGUAGE"
        )

    if driver_pairs:
        classes.append(
            "DRIVER_SPECIFIC"
        )

    return classes


# ============================================================
# MAIN
# ============================================================

def main():

    RAW_HTML_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    TEXT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print()
    print("=" * 120)
    print(
        "R1G.4 — 2022 OFFICIAL EDITORIAL "
        "CHRONOLOGY CANDIDATE MINING V1"
    )
    print("=" * 120)

    if not RESULT_ROWS.exists():

        print(
            "MISSING INPUT:",
            RESULT_ROWS,
        )

        print(
            "FINAL STATUS: "
            "2022_EDITORIAL_MINING_INPUT_MISSING"
        )

        return

    result_rows = read_csv(
        RESULT_ROWS
    )

    results_2022 = [
        row
        for row in result_rows
        if str(
            row.get(
                "year",
                "",
            )
        ).strip()
        == "2022"
    ]

    print()
    print(
        "2022 OFFICIAL RESULTS ROWS:",
        len(
            results_2022
        ),
    )

    source_rows = []
    candidate_rows = []
    entity_rows = []

    fetched_sources = 0

    candidate_id = 0

    for source in SOURCES:

        print()
        print("=" * 120)
        print(
            source[
                "source_id"
            ]
        )
        print("=" * 120)

        print(
            "URL:",
            source[
                "url"
            ],
        )

        result = fetch(
            source[
                "url"
            ]
        )

        print(
            "STATUS:",
            result[
                "status"
            ],
        )

        if not result[
            "ok"
        ]:

            print(
                "ERROR:",
                result[
                    "error"
                ],
            )

            source_rows.append({
                "source_id":
                    source[
                        "source_id"
                    ],

                "url":
                    source[
                        "url"
                    ],

                "source_class":
                    source[
                        "source_class"
                    ],

                "fetch_ok":
                    False,

                "status_code":
                    result[
                        "status"
                    ],

                "final_url":
                    result[
                        "final_url"
                    ],

                "bytes":
                    0,

                "sha256":
                    "",

                "sentence_count":
                    0,

                "candidate_count":
                    0,

                "error":
                    result[
                        "error"
                    ],
            })

            continue

        fetched_sources += 1

        body = result[
            "body"
        ]

        source_hash = sha256_bytes(
            body
        )

        html_path = (
            RAW_HTML_DIR
            / (
                source[
                    "source_id"
                ]
                + ".html"
            )
        )

        html_path.write_bytes(
            body
        )

        html_text = decode_html(
            body
        )

        article_text = html_to_text(
            html_text
        )

        text_path = (
            TEXT_DIR
            / (
                source[
                    "source_id"
                ]
                + ".txt"
            )
        )

        text_path.write_text(
            article_text,
            encoding="utf-8",
        )

        sentences = split_sentences(
            article_text
        )

        source_candidate_count = 0

        for sentence_index, sentence in enumerate(
            sentences,
            start=1,
        ):

            explicit_times = (
                find_explicit_times(
                    sentence
                )
            )

            relative_terms = (
                find_terms(
                    sentence,
                    RELATIVE_TIME_TERMS,
                )
            )

            interruption_terms = (
                find_terms(
                    sentence,
                    INTERRUPTION_TERMS,
                )
            )

            attempt_terms = (
                find_terms(
                    sentence,
                    ATTEMPT_TERMS,
                )
            )

            action_terms = (
                find_terms(
                    sentence,
                    ACTION_TERMS,
                )
            )

            session_terms = (
                find_terms(
                    sentence,
                    SESSION_TERMS,
                )
            )

            driver_pairs = (
                detect_drivers(
                    sentence
                )
            )

            speeds = (
                find_speed_values(
                    sentence
                )
            )

            # ------------------------------------------------
            # Candidate gate
            #
            # Must contain at least one chronology/action clue.
            # Mere mention of driver or speed is not enough.
            # ------------------------------------------------

            chronology_signal = (
                explicit_times
                or relative_terms
                or interruption_terms
                or attempt_terms
                or action_terms
            )

            if not chronology_signal:
                continue

            # Avoid obvious navigation/legal junk.
            lower_sentence = (
                sentence.lower()
            )

            junk_terms = [
                "privacy policy",
                "cookie policy",
                "terms of use",
                "subscribe",
                "sign up",
                "copyright",
            ]

            if any(
                junk
                in lower_sentence
                for junk in junk_terms
            ):
                continue

            candidate_id += 1
            source_candidate_count += 1

            classes = classify_candidate(
                explicit_times,
                relative_terms,
                interruption_terms,
                attempt_terms,
                action_terms,
                driver_pairs,
            )

            matched_results = (
                match_result_rows(
                    results_2022,
                    driver_pairs,
                    speeds,
                )
            )

            # ------------------------------------------------
            # Evidence quality classification
            #
            # IMPORTANT:
            # This is discovery quality, not chronology
            # promotion.
            # ------------------------------------------------

            if (
                driver_pairs
                and
                (
                    explicit_times
                    or relative_terms
                )
                and
                attempt_terms
            ):

                review_priority = (
                    "HIGH"
                )

            elif (
                driver_pairs
                and
                (
                    action_terms
                    or attempt_terms
                )
            ):

                review_priority = (
                    "HIGH"
                )

            elif interruption_terms:

                review_priority = (
                    "MEDIUM"
                )

            elif action_terms:

                review_priority = (
                    "MEDIUM"
                )

            else:

                review_priority = (
                    "LOW"
                )

            candidate_key = (
                f"R1G4-C{candidate_id:04d}"
            )

            candidate_rows.append({
                "candidate_id":
                    candidate_key,

                "source_id":
                    source[
                        "source_id"
                    ],

                "source_class":
                    source[
                        "source_class"
                    ],

                "source_url":
                    source[
                        "url"
                    ],

                "sentence_index":
                    sentence_index,

                "sentence":
                    sentence,

                "candidate_classes":
                    json.dumps(
                        classes,
                        ensure_ascii=False,
                    ),

                "explicit_clock_times":
                    json.dumps(
                        explicit_times,
                        ensure_ascii=False,
                    ),

                "relative_time_terms":
                    json.dumps(
                        relative_terms,
                        ensure_ascii=False,
                    ),

                "interruption_terms":
                    json.dumps(
                        interruption_terms,
                        ensure_ascii=False,
                    ),

                "attempt_terms":
                    json.dumps(
                        attempt_terms,
                        ensure_ascii=False,
                    ),

                "action_terms":
                    json.dumps(
                        action_terms,
                        ensure_ascii=False,
                    ),

                "session_terms":
                    json.dumps(
                        session_terms,
                        ensure_ascii=False,
                    ),

                "drivers_detected":
                    json.dumps(
                        [
                            {
                                "driver":
                                    name,

                                "car":
                                    car,
                            }
                            for name, car
                            in driver_pairs
                        ],
                        ensure_ascii=False,
                    ),

                "speeds_detected_mph":
                    json.dumps(
                        speeds,
                        ensure_ascii=False,
                    ),

                "matched_result_row_count":
                    len(
                        matched_results
                    ),

                "review_priority":
                    review_priority,

                "normalized_time_lower_utc":
                    "",

                "normalized_time_upper_utc":
                    "",

                "normalized_ordering_relation":
                    "",

                "promotion_status":
                    "CANDIDATE_ONLY",

                "chronology_promoted":
                    False,

                "notes":
                    (
                        "Discovery candidate only. "
                        "No vague language converted "
                        "to timestamp automatically."
                    ),
            })

            for match in matched_results:

                entity_rows.append({
                    "candidate_id":
                        candidate_key,

                    "source_id":
                        source[
                            "source_id"
                        ],

                    "driver_name":
                        match[
                            "driver_name"
                        ],

                    "car_number":
                        match[
                            "car_number"
                        ],

                    "speed_mph":
                        match[
                            "speed_mph"
                        ],

                    "official_result_row":
                        match[
                            "result_row"
                        ],

                    "official_result_status":
                        match[
                            "result_status"
                        ],

                    "official_result_source_file":
                        match[
                            "source_file"
                        ],

                    "official_result_source_line":
                        match[
                            "source_line_number"
                        ],

                    "match_semantic":
                        (
                            "EDITORIAL_ENTITY_TO_"
                            "OFFICIAL_RESULT_CANDIDATE"
                        ),

                    "chronology_promoted":
                        False,
                })

        source_rows.append({
            "source_id":
                source[
                    "source_id"
                ],

            "url":
                source[
                    "url"
                ],

            "source_class":
                source[
                    "source_class"
                ],

            "fetch_ok":
                True,

            "status_code":
                result[
                    "status"
                ],

            "final_url":
                result[
                    "final_url"
                ],

            "bytes":
                len(
                    body
                ),

            "sha256":
                source_hash,

            "sentence_count":
                len(
                    sentences
                ),

            "candidate_count":
                source_candidate_count,

            "error":
                "",
        })

        print(
            "SENTENCES:",
            len(
                sentences
            ),
        )

        print(
            "CANDIDATES:",
            source_candidate_count,
        )

        time.sleep(
            DELAY
        )

    # ========================================================
    # WRITE
    # ========================================================

    write_csv(
        SOURCE_AUDIT_CSV,
        source_rows,
        [
            "source_id",
            "url",
            "source_class",
            "fetch_ok",
            "status_code",
            "final_url",
            "bytes",
            "sha256",
            "sentence_count",
            "candidate_count",
            "error",
        ],
    )

    write_csv(
        CANDIDATE_CSV,
        candidate_rows,
        [
            "candidate_id",
            "source_id",
            "source_class",
            "source_url",
            "sentence_index",
            "sentence",
            "candidate_classes",
            "explicit_clock_times",
            "relative_time_terms",
            "interruption_terms",
            "attempt_terms",
            "action_terms",
            "session_terms",
            "drivers_detected",
            "speeds_detected_mph",
            "matched_result_row_count",
            "review_priority",
            "normalized_time_lower_utc",
            "normalized_time_upper_utc",
            "normalized_ordering_relation",
            "promotion_status",
            "chronology_promoted",
            "notes",
        ],
    )

    write_csv(
        ENTITY_MATCH_CSV,
        entity_rows,
        [
            "candidate_id",
            "source_id",
            "driver_name",
            "car_number",
            "speed_mph",
            "official_result_row",
            "official_result_status",
            "official_result_source_file",
            "official_result_source_line",
            "match_semantic",
            "chronology_promoted",
        ],
    )

    # ========================================================
    # SUMMARY COUNTS
    # ========================================================

    high_priority = [
        row
        for row in candidate_rows
        if row[
            "review_priority"
        ] == "HIGH"
    ]

    medium_priority = [
        row
        for row in candidate_rows
        if row[
            "review_priority"
        ] == "MEDIUM"
    ]

    explicit_time_candidates = [
        row
        for row in candidate_rows
        if row[
            "explicit_clock_times"
        ] != "[]"
    ]

    interruption_candidates = [
        row
        for row in candidate_rows
        if row[
            "interruption_terms"
        ] != "[]"
    ]

    action_candidates = [
        row
        for row in candidate_rows
        if row[
            "action_terms"
        ] != "[]"
    ]

    matched_candidates = [
        row
        for row in candidate_rows
        if int(
            row[
                "matched_result_row_count"
            ]
        ) > 0
    ]

    # ========================================================
    # QA
    # ========================================================

    qa_rows = [
        {
            "metric":
                "official_sources_targeted",

            "value":
                len(
                    SOURCES
                ),

            "status":
                "INFO",
        },

        {
            "metric":
                "official_sources_fetched",

            "value":
                fetched_sources,

            "status":
                (
                    "PASS"
                    if fetched_sources
                    == len(
                        SOURCES
                    )
                    else "REVIEW"
                ),
        },

        {
            "metric":
                "candidate_sentences",

            "value":
                len(
                    candidate_rows
                ),

            "status":
                (
                    "PASS"
                    if candidate_rows
                    else "REVIEW"
                ),
        },

        {
            "metric":
                "high_priority_candidates",

            "value":
                len(
                    high_priority
                ),

            "status":
                "INFO",
        },

        {
            "metric":
                "explicit_clock_time_candidates",

            "value":
                len(
                    explicit_time_candidates
                ),

            "status":
                "INFO",
        },

        {
            "metric":
                "session_interruption_candidates",

            "value":
                len(
                    interruption_candidates
                ),

            "status":
                "INFO",
        },

        {
            "metric":
                "action_or_lane_candidates",

            "value":
                len(
                    action_candidates
                ),

            "status":
                "INFO",
        },

        {
            "metric":
                "candidates_matched_to_result_rows",

            "value":
                len(
                    matched_candidates
                ),

            "status":
                "INFO",
        },

        {
            "metric":
                "chronology_candidates_auto_promoted",

            "value":
                0,

            "status":
                "PASS",
        },

        {
            "metric":
                "vague_relative_time_auto_normalized",

            "value":
                0,

            "status":
                "PASS",
        },

        {
            "metric":
                "article_publication_time_used_as_attempt_time",

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
                "canonical_data_mutated",

            "value":
                0,

            "status":
                "PASS",
        },
    ]

    write_csv(
        QA_CSV,
        qa_rows,
        [
            "metric",
            "value",
            "status",
        ],
    )

    # ========================================================
    # PRINT HIGH PRIORITY
    # ========================================================

    print()
    print("=" * 120)
    print(
        "HIGH-PRIORITY CANDIDATES"
    )
    print("=" * 120)

    if not high_priority:

        print(
            "NONE"
        )

    else:

        for row in high_priority:

            print()
            print(
                row[
                    "candidate_id"
                ],
                "|",
                row[
                    "source_id"
                ],
            )

            print(
                "  sentence:",
                row[
                    "sentence"
                ],
            )

            print(
                "  times:",
                row[
                    "explicit_clock_times"
                ],
            )

            print(
                "  relative:",
                row[
                    "relative_time_terms"
                ],
            )

            print(
                "  attempts:",
                row[
                    "attempt_terms"
                ],
            )

            print(
                "  actions:",
                row[
                    "action_terms"
                ],
            )

            print(
                "  drivers:",
                row[
                    "drivers_detected"
                ],
            )

            print(
                "  speeds:",
                row[
                    "speeds_detected_mph"
                ],
            )

            print(
                "  matched result rows:",
                row[
                    "matched_result_row_count"
                ],
            )

    # ========================================================
    # INTERRUPTION PREVIEW
    # ========================================================

    print()
    print("=" * 120)
    print(
        "SESSION INTERRUPTION CANDIDATES"
    )
    print("=" * 120)

    for row in interruption_candidates[:40]:

        print()
        print(
            row[
                "candidate_id"
            ],
            "|",
            row[
                "source_id"
            ],
        )

        print(
            row[
                "sentence"
            ],
        )

    # ========================================================
    # ACTION PREVIEW
    # ========================================================

    print()
    print("=" * 120)
    print(
        "ACTION / LANE CANDIDATES"
    )
    print("=" * 120)

    for row in action_candidates[:40]:

        print()
        print(
            row[
                "candidate_id"
            ],
            "|",
            row[
                "source_id"
            ],
        )

        print(
            row[
                "sentence"
            ],
        )

    # ========================================================
    # FINAL
    # ========================================================

    print()
    print("=" * 120)
    print(
        "R1G.4 SUMMARY"
    )
    print("=" * 120)

    print()
    print(
        "Official sources fetched:",
        fetched_sources,
        "/",
        len(
            SOURCES
        ),
    )

    print(
        "Candidate sentences:",
        len(
            candidate_rows
        ),
    )

    print(
        "High-priority candidates:",
        len(
            high_priority
        ),
    )

    print(
        "Explicit-clock candidates:",
        len(
            explicit_time_candidates
        ),
    )

    print(
        "Interruption candidates:",
        len(
            interruption_candidates
        ),
    )

    print(
        "Action/lane candidates:",
        len(
            action_candidates
        ),
    )

    print(
        "Candidates matched to official result rows:",
        len(
            matched_candidates
        ),
    )

    print()
    print(
        "No candidate was automatically "
        "promoted to chronology truth."
    )

    print(
        "No vague relative-time expression "
        "was converted into a timestamp."
    )

    print(
        "No publication time was used "
        "as an attempt time."
    )

    print(
        "No canonical data was modified."
    )

    print()
    print("=" * 120)

    if (
        fetched_sources > 0
        and
        candidate_rows
    ):

        print(
            "FINAL STATUS: "
            "2022_OFFICIAL_EDITORIAL_CHRONOLOGY_"
            "CANDIDATES_MINED"
        )

    else:

        print(
            "FINAL STATUS: "
            "2022_OFFICIAL_EDITORIAL_CHRONOLOGY_"
            "MINING_REVIEW_REQUIRED"
        )

    print("=" * 120)

    print()
    print(
        "OUTPUTS"
    )

    print(
        SOURCE_AUDIT_CSV
    )

    print(
        CANDIDATE_CSV
    )

    print(
        ENTITY_MATCH_CSV
    )

    print(
        QA_CSV
    )

    print(
        EVIDENCE_DIR
    )


if __name__ == "__main__":
    main()
