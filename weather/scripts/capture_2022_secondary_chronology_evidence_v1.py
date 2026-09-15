from pathlib import Path
from html.parser import HTMLParser
import csv
import hashlib
import re
import time
import urllib.request
import urllib.error


PHASE = "R1G.18"

EVIDENCE_DIR = Path(
    "weather/evidence/rescue/"
    "secondary_2022_high_priority_chronology"
)

RAW_DIR = EVIDENCE_DIR / "raw_html"
TEXT_DIR = EVIDENCE_DIR / "article_text"

OUTPUT_DIR = Path("weather/output")

CANDIDATES_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_secondary_editorial_candidates_v1.csv"
)

SOURCE_MANIFEST_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_secondary_source_manifest_v1.csv"
)

QA_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_secondary_editorial_candidates_v1_qa.csv"
)


SOURCES = [
    {
        "source_id": "THE_RACE_2022_DAY1",
        "source_name": "The Race",
        "source_class": "REPUTABLE_SECONDARY_EDITORIAL",
        "url": (
            "https://www.the-race.com/indycar/"
            "everything-that-happened-in-tense-first-indy-500-qualifying/"
        ),
    },
    {
        "source_id": "RACER_2022_DAY1",
        "source_name": "RACER",
        "source_class": "REPUTABLE_SECONDARY_EDITORIAL",
        "url": (
            "https://racer.com/2022/05/21/"
            "veekay-leads-saturday-indy-500-qualifying/"
        ),
    },
    {
        "source_id": "NBC_2022_DAY1",
        "source_name": "NBC Sports",
        "source_class": "REPUTABLE_SECONDARY_EDITORIAL",
        "url": (
            "https://www.nbcsports.com/motor-sports/news/"
            "indy-500-qualifying-opening-day-rinus-veekay-pato-oward-"
            "jimmie-johnson-chip-ganassi-racing-team-penske-andretti-autosport"
        ),
    },
]


TARGETS = {
    "Alexander Rossi": [
        "rossi",
        "alexander rossi",
    ],
    "Sage Karam": [
        "karam",
        "sage karam",
    ],
    "Marco Andretti": [
        "marco andretti",
        "andretti",
    ],
    "Helio Castroneves": [
        "castroneves",
        "helio",
        "hélio",
    ],
    "Takuma Sato": [
        "sato",
        "takuma sato",
    ],
    "Colton Herta": [
        "herta",
        "colton herta",
    ],
    "Stefan Wilson": [
        "stefan wilson",
        "wilson",
    ],
    "David Malukas": [
        "malukas",
        "david malukas",
    ],
    "Callum Ilott": [
        "ilott",
        "callum ilott",
    ],
    "Scott McLaughlin": [
        "mclaughlin",
        "scott mclaughlin",
    ],
    "Josef Newgarden": [
        "newgarden",
        "josef newgarden",
    ],
}


ACTION_PATTERNS = {
    "WITHDRAW_EXISTING_RESULT": [
        r"\bwithdrew\b",
        r"\bwithdrawn\b",
        r"\bpulling his speed\b",
        r"\bpulled his speed\b",
        r"\bgave his .* time\b",
        r"\bgave up\b",
        r"\bsurrendered\b",
    ],
    "SECOND_ATTEMPT": [
        r"\bsecond attempt\b",
        r"\bsecond qualifying attempt\b",
        r"\bsecond run\b",
        r"\bsecond-runs\b",
        r"\bsecond shot\b",
        r"\bran again\b",
        r"\brun again\b",
        r"\bwent again\b",
        r"\battempted to improve\b",
        r"\battempting to improve\b",
    ],
    "LANE_1": [
        r"\blane 1\b",
        r"\blane one\b",
    ],
    "LANE_2": [
        r"\blane 2\b",
        r"\blane two\b",
    ],
    "AFTER_RESTART": [
        r"\btrack re-opened\b",
        r"\btrack reopened\b",
        r"\bafter .* delay\b",
        r"\bdelay was resolved\b",
        r"\bresumed\b",
    ],
    "WEATHER_STOP": [
        r"\brain hit\b",
        r"\brain fell\b",
        r"\bheavier rain\b",
        r"\blightning\b",
        r"\bweather warning\b",
        r"\bcaution\b",
        r"\brain delay\b",
        r"\bdelayed\b",
    ],
    "IMPROVED": [
        r"\bimproved\b",
        r"\bimprove\b",
        r"\bproduced 19th\b",
    ],
    "FAILED_TO_IMPROVE": [
        r"\bunable to improve\b",
        r"\bfailed to improve\b",
        r"\bwent much slower\b",
        r"\btime wasn.t there\b",
        r"\bfell from\b",
        r"\bdropped\b",
        r"\btumbled\b",
    ],
    "ABORTED_OR_BAILED": [
        r"\bbailing out\b",
        r"\bbailed out\b",
        r"\baborted\b",
    ],
    "NO_QUALIFYING_RUN": [
        r"\bnot getting on track\b",
        r"\bunable to start a qualifying run\b",
        r"\bwasn.t seen again\b",
        r"\bwas not seen again\b",
    ],
    "ENGINE_CHANGE": [
        r"\bchange .* engine\b",
        r"\bchanged his engine\b",
        r"\bengine change\b",
    ],
}


class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag.lower() in {
            "script",
            "style",
            "noscript",
            "svg",
        }:
            self.skip_depth += 1

    def handle_endtag(self, tag):
        if (
            tag.lower()
            in {
                "script",
                "style",
                "noscript",
                "svg",
            }
            and self.skip_depth > 0
        ):
            self.skip_depth -= 1

    def handle_data(self, data):
        if self.skip_depth == 0:
            value = re.sub(
                r"\s+",
                " ",
                data,
            ).strip()

            if value:
                self.parts.append(value)

    def get_text(self):
        return "\n".join(
            self.parts
        )


def sha256_bytes(data):
    return hashlib.sha256(
        data
    ).hexdigest()


def sha256_file(path):
    h = hashlib.sha256()

    with path.open("rb") as f:
        while True:
            chunk = f.read(
                1024 * 1024
            )

            if not chunk:
                break

            h.update(chunk)

    return h.hexdigest()


def fetch(url):
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 "
                "Chrome/152 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9",
        },
    )

    with urllib.request.urlopen(
        request,
        timeout=30,
    ) as response:
        return response.read()


def html_to_text(raw):
    html = raw.decode(
        "utf-8",
        errors="replace",
    )

    parser = TextExtractor()
    parser.feed(html)

    text = parser.get_text()

    text = re.sub(
        r"[ \t]+",
        " ",
        text,
    )

    text = re.sub(
        r"\n{3,}",
        "\n\n",
        text,
    )

    return text.strip()


def split_sentences(text):
    normalized = re.sub(
        r"\s+",
        " ",
        text,
    )

    chunks = re.split(
        r"(?<=[.!?])\s+",
        normalized,
    )

    return [
        x.strip()
        for x in chunks
        if x.strip()
    ]


def detect_targets(sentence):
    lower = sentence.lower()

    found = []

    for driver, variants in TARGETS.items():
        if any(
            variant.lower() in lower
            for variant in variants
        ):
            found.append(driver)

    return sorted(
        set(found)
    )


def detect_actions(sentence):
    found = []

    for label, patterns in ACTION_PATTERNS.items():
        if any(
            re.search(
                pattern,
                sentence,
                flags=re.IGNORECASE,
            )
            for pattern in patterns
        ):
            found.append(label)

    return found


def candidate_score(actions):
    weights = {
        "WITHDRAW_EXISTING_RESULT": 6,
        "SECOND_ATTEMPT": 5,
        "LANE_1": 10,
        "LANE_2": 10,
        "AFTER_RESTART": 5,
        "WEATHER_STOP": 4,
        "IMPROVED": 3,
        "FAILED_TO_IMPROVE": 4,
        "ABORTED_OR_BAILED": 5,
        "NO_QUALIFYING_RUN": 5,
        "ENGINE_CHANGE": 3,
    }

    return sum(
        weights.get(
            action,
            0,
        )
        for action in set(actions)
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


def main():

    EVIDENCE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    RAW_DIR.mkdir(
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
        "R1G.18 — 2022 SECONDARY EDITORIAL "
        "CHRONOLOGY EVIDENCE CAPTURE V1"
    )
    print("=" * 120)

    manifest = []
    candidates = []

    candidate_number = 1

    for source in SOURCES:

        print()
        print("-" * 120)
        print(
            source[
                "source_id"
            ]
        )
        print("-" * 120)

        raw_path = (
            RAW_DIR
            / f"{source['source_id']}.html"
        )

        text_path = (
            TEXT_DIR
            / f"{source['source_id']}.txt"
        )

        fetch_status = "FAILED"
        error = ""
        raw = b""
        text = ""

        try:

            raw = fetch(
                source[
                    "url"
                ]
            )

            raw_path.write_bytes(
                raw
            )

            text = html_to_text(
                raw
            )

            text_path.write_text(
                text,
                encoding="utf-8",
            )

            fetch_status = "SUCCESS"

            print(
                "FETCH: SUCCESS"
            )

            print(
                "HTML bytes:",
                len(raw),
            )

            print(
                "Text chars:",
                len(text),
            )

        except Exception as exc:

            error = (
                f"{type(exc).__name__}: "
                f"{exc}"
            )

            print(
                "FETCH: FAILED"
            )

            print(
                "ERROR:",
                error,
            )

        manifest.append({
            "source_id":
                source[
                    "source_id"
                ],

            "source_name":
                source[
                    "source_name"
                ],

            "source_class":
                source[
                    "source_class"
                ],

            "url":
                source[
                    "url"
                ],

            "fetch_status":
                fetch_status,

            "raw_html_path":
                str(raw_path)
                if raw_path.exists()
                else "",

            "article_text_path":
                str(text_path)
                if text_path.exists()
                else "",

            "raw_sha256":
                sha256_file(
                    raw_path
                )
                if raw_path.exists()
                else "",

            "text_sha256":
                sha256_file(
                    text_path
                )
                if text_path.exists()
                else "",

            "error":
                error,
        })

        if fetch_status != "SUCCESS":
            continue

        sentences = split_sentences(
            text
        )

        for sentence_index, sentence in enumerate(
            sentences,
            start=1,
        ):

            drivers = detect_targets(
                sentence
            )

            if not drivers:
                continue

            actions = detect_actions(
                sentence
            )

            if not actions:
                continue

            score = candidate_score(
                actions
            )

            if score >= 12:
                priority = "HIGH"
            elif score >= 6:
                priority = "MEDIUM"
            else:
                priority = "LOW"

            for driver in drivers:

                candidates.append({
                    "candidate_id":
                        f"R1G18-C{candidate_number:04d}",

                    "source_id":
                        source[
                            "source_id"
                        ],

                    "source_name":
                        source[
                            "source_name"
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

                    "driver_name":
                        driver,

                    "detected_actions":
                        "|".join(
                            actions
                        ),

                    "candidate_score":
                        score,

                    "candidate_priority":
                        priority,

                    "candidate_sentence":
                        sentence,

                    "promotion_status":
                        "REVIEW_REQUIRED",

                    "chronology_promoted":
                        "False",

                    "lane_promoted":
                        "False",

                    "queue_wait_inferred":
                        "False",

                    "canonical_mutated":
                        "False",

                    "notes":
                        (
                            "Secondary editorial discovery "
                            "candidate only."
                        ),
                })

                candidate_number += 1

        time.sleep(
            0.5
        )

    candidates.sort(
        key=lambda row: (
            {
                "HIGH": 0,
                "MEDIUM": 1,
                "LOW": 2,
            }.get(
                row[
                    "candidate_priority"
                ],
                9,
            ),
            -int(
                row[
                    "candidate_score"
                ]
            ),
            row[
                "driver_name"
            ],
            row[
                "source_id"
            ],
        )
    )

    print()
    print("=" * 120)
    print(
        "CAPTURE SUMMARY"
    )
    print("=" * 120)

    successful = sum(
        1
        for row in manifest
        if row[
            "fetch_status"
        ] == "SUCCESS"
    )

    print()
    print(
        "Sources requested:",
        len(
            SOURCES
        ),
    )

    print(
        "Sources captured:",
        successful,
    )

    print(
        "Candidates:",
        len(
            candidates
        ),
    )

    high = [
        row
        for row in candidates
        if row[
            "candidate_priority"
        ] == "HIGH"
    ]

    medium = [
        row
        for row in candidates
        if row[
            "candidate_priority"
        ] == "MEDIUM"
    ]

    print(
        "High-value candidates:",
        len(
            high
        ),
    )

    print(
        "Medium-value candidates:",
        len(
            medium
        ),
    )

    print()
    print("=" * 120)
    print(
        "TOP SECONDARY CANDIDATES"
    )
    print("=" * 120)

    for row in (
        high
        +
        medium
    )[:50]:

        print()
        print(
            row[
                "candidate_id"
            ],
            "|",
            row[
                "candidate_priority"
            ],
            "| score=",
            row[
                "candidate_score"
            ],
        )

        print(
            "driver:",
            row[
                "driver_name"
            ],
        )

        print(
            "source:",
            row[
                "source_name"
            ],
        )

        print(
            "actions:",
            row[
                "detected_actions"
            ],
        )

        print(
            "sentence:"
        )

        print(
            row[
                "candidate_sentence"
            ]
        )

    candidate_fields = [
        "candidate_id",
        "source_id",
        "source_name",
        "source_class",
        "source_url",
        "sentence_index",
        "driver_name",
        "detected_actions",
        "candidate_score",
        "candidate_priority",
        "candidate_sentence",
        "promotion_status",
        "chronology_promoted",
        "lane_promoted",
        "queue_wait_inferred",
        "canonical_mutated",
        "notes",
    ]

    write_csv(
        CANDIDATES_OUT,
        candidates,
        candidate_fields,
    )

    write_csv(
        SOURCE_MANIFEST_OUT,
        manifest,
        [
            "source_id",
            "source_name",
            "source_class",
            "url",
            "fetch_status",
            "raw_html_path",
            "article_text_path",
            "raw_sha256",
            "text_sha256",
            "error",
        ],
    )

    duplicate_candidate_ids = (
        len(candidates)
        -
        len({
            row[
                "candidate_id"
            ]
            for row in candidates
        })
    )

    qa = [
        {
            "metric":
                "sources_requested",
            "value":
                len(
                    SOURCES
                ),
            "status":
                "INFO",
        },
        {
            "metric":
                "sources_captured",
            "value":
                successful,
            "status":
                (
                    "PASS"
                    if successful > 0
                    else "FAIL"
                ),
        },
        {
            "metric":
                "candidate_rows",
            "value":
                len(
                    candidates
                ),
            "status":
                "INFO",
        },
        {
            "metric":
                "high_value_candidates",
            "value":
                len(
                    high
                ),
            "status":
                "INFO",
        },
        {
            "metric":
                "duplicate_candidate_ids",
            "value":
                duplicate_candidate_ids,
            "status":
                (
                    "PASS"
                    if duplicate_candidate_ids == 0
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

    print()
    print("=" * 120)
    print(
        "FINAL SUMMARY"
    )
    print("=" * 120)

    print()
    print(
        "No candidate was promoted automatically."
    )

    print(
        "Secondary source authority remains "
        "separate from INDYCAR official evidence."
    )

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

    if (
        successful > 0
        and
        duplicate_candidate_ids == 0
    ):

        print(
            "FINAL STATUS: "
            "2022_SECONDARY_EDITORIAL_EVIDENCE_CAPTURE_COMPLETE"
        )

    else:

        print(
            "FINAL STATUS: "
            "2022_SECONDARY_EDITORIAL_EVIDENCE_CAPTURE_REVIEW_REQUIRED"
        )

    print("=" * 120)

    print()
    print("OUTPUTS")
    print(CANDIDATES_OUT)
    print(SOURCE_MANIFEST_OUT)
    print(QA_OUT)


if __name__ == "__main__":
    main()
