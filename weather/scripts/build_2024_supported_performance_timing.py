from pathlib import Path
import json
import re
import pandas as pd


ATTEMPTS_FILE = Path(
    "data/canonical/v1/attempts.csv"
)

EVENTS_FILE = Path(
    "data/canonical/v1/chronology_events.csv"
)

OUTPUT_FILE = Path(
    "weather/output/"
    "performance_grade_attempt_timing_2024_supported.csv"
)

QA_FILE = Path(
    "weather/output/"
    "performance_grade_attempt_timing_2024_supported_qa.csv"
)

SESSION = "INDY500_DAY1_2024"

STRICT_SEQUENCE_CARS = {
    "7",
    "12",
}

SINGLETON_CARS = {
    "3",
    "4",
    "11",
    "60",
}


def normalize_car(value):
    if pd.isna(value):
        return None

    s = str(value).strip()

    if re.fullmatch(r"\d+\.0", s):
        s = s[:-2]

    if s.isdigit():
        return str(int(s))

    return s


def extract_capture_car(raw):
    if pd.isna(raw):
        return None

    try:
        outer = json.loads(raw)
    except Exception:
        return None

    payload = outer.get(
        "capture_source_payload"
    )

    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except Exception:
            payload = None

    if not isinstance(payload, dict):
        return None

    return normalize_car(
        payload.get("currentQualifier")
    )


def main():

    if not ATTEMPTS_FILE.exists():
        raise FileNotFoundError(
            f"Missing file: {ATTEMPTS_FILE}"
        )

    if not EVENTS_FILE.exists():
        raise FileNotFoundError(
            f"Missing file: {EVENTS_FILE}"
        )

    attempts = pd.read_csv(
        ATTEMPTS_FILE
    )

    events = pd.read_csv(
        EVENTS_FILE
    )

    a = attempts[
        attempts["session_id"].astype(str)
        == SESSION
    ].copy()

    q = events[
        (events["session_id"].astype(str) == SESSION)
        & (
            events["event_type"]
            == "QUALIFIER_CAPTURE"
        )
    ].copy()

    a["_car"] = a[
        "car_number"
    ].apply(normalize_car)

    q["_car"] = q[
        "event_payload_json"
    ].apply(extract_capture_car)

    q["_time"] = pd.to_datetime(
        q["event_time_utc"],
        utc=True,
        errors="coerce",
    )

    if len(a) != 77:
        raise RuntimeError(
            f"Expected 77 canonical 2024 attempts, got {len(a)}"
        )

    if len(q) != 97:
        raise RuntimeError(
            f"Expected 97 QUALIFIER_CAPTURE rows, got {len(q)}"
        )

    rows = []

    # =========================================================
    # 1. Existing constrained sequence links
    #    car 7 -> 2
    #    car 12 -> 1
    # =========================================================

    for car in sorted(
        STRICT_SEQUENCE_CARS,
        key=int,
    ):

        ca = a[
            a["_car"] == car
        ].copy()

        cq = q[
            q["_car"] == car
        ].copy()

        ca = ca[
            ca["car_attempt_index"].notna()
        ].copy()

        ca[
            "car_attempt_index"
        ] = ca[
            "car_attempt_index"
        ].astype(int)

        ca = ca.sort_values(
            "car_attempt_index"
        )

        cq = cq.sort_values(
            "_time"
        )

        if len(ca) != len(cq):
            raise RuntimeError(
                f"Strict car {car}: count mismatch "
                f"canonical={len(ca)}, captures={len(cq)}"
            )

        expected_indices = list(
            range(
                1,
                len(ca) + 1
            )
        )

        actual_indices = (
            ca[
                "car_attempt_index"
            ]
            .tolist()
        )

        if actual_indices != expected_indices:
            raise RuntimeError(
                f"Strict car {car}: "
                f"indices={actual_indices}, "
                f"expected={expected_indices}"
            )

        for (
            (_, attempt_row),
            (_, capture_row),
        ) in zip(
            ca.iterrows(),
            cq.iterrows(),
        ):

            if pd.isna(
                capture_row[
                    "attempt_id"
                ]
            ):
                raise RuntimeError(
                    f"Strict car {car}: "
                    "expected existing capture link missing."
                )

            if str(
                capture_row[
                    "attempt_id"
                ]
            ) != str(
                attempt_row[
                    "attempt_id"
                ]
            ):
                raise RuntimeError(
                    f"Strict car {car}: "
                    "existing attempt link disagrees "
                    "with sequence order."
                )

            rows.append(
                {
                    "attempt_id":
                        attempt_row[
                            "attempt_id"
                        ],
                    "session_id":
                        SESSION,
                    "entry_key":
                        attempt_row.get(
                            "entry_key"
                        ),
                    "attempt_key":
                        attempt_row.get(
                            "attempt_key"
                        ),
                    "car_number":
                        attempt_row.get(
                            "car_number"
                        ),
                    "driver_name":
                        attempt_row.get(
                            "driver_name"
                        ),
                    "car_attempt_index":
                        attempt_row[
                            "car_attempt_index"
                        ],
                    "mapped_capture_event_id":
                        capture_row[
                            "chronology_event_id"
                        ],
                    "mapped_capture_time_utc":
                        capture_row[
                            "event_time_utc"
                        ],
                    "timing_class":
                        (
                            "EXISTING_CONSTRAINED_"
                            "SEQUENCE_LINK"
                        ),
                    "timing_basis":
                        (
                            "EXISTING_2024_"
                            "CONSTRAINED_CAPTURE_LINK"
                        ),
                    "mapping_support":
                        (
                            "EXISTING_CONSTRAINED_LINK_"
                            "WITH_KNOWN_ATTEMPT_ORDINAL"
                        ),
                    "performance_alignment_usable":
                        True,
                    "chronology_usable":
                        False,
                    "queue_replay_usable":
                        False,
                    "time_semantic_note":
                        (
                            "Existing constrained 2024 "
                            "Timing71 capture link. "
                            "Recorder capture is suitable "
                            "for approximate performance "
                            "environment alignment only; "
                            "it is not an exact timed-run start."
                        ),
                }
            )

    # =========================================================
    # 2. Singleton unique same-car 1:1 mappings
    # =========================================================

    for car in sorted(
        SINGLETON_CARS,
        key=int,
    ):

        ca = a[
            a["_car"] == car
        ].copy()

        cq = q[
            q["_car"] == car
        ].copy()

        if len(ca) != 1:
            raise RuntimeError(
                f"Singleton car {car}: "
                f"expected 1 canonical row, got {len(ca)}"
            )

        if len(cq) != 1:
            raise RuntimeError(
                f"Singleton car {car}: "
                f"expected 1 capture, got {len(cq)}"
            )

        attempt_row = ca.iloc[0]
        capture_row = cq.iloc[0]

        if pd.notna(
            capture_row[
                "attempt_id"
            ]
        ):
            raise RuntimeError(
                f"Singleton car {car}: "
                "capture unexpectedly already linked."
            )

        rows.append(
            {
                "attempt_id":
                    attempt_row[
                        "attempt_id"
                    ],
                "session_id":
                    SESSION,
                "entry_key":
                    attempt_row.get(
                        "entry_key"
                    ),
                "attempt_key":
                    attempt_row.get(
                        "attempt_key"
                    ),
                "car_number":
                    attempt_row.get(
                        "car_number"
                    ),
                "driver_name":
                    attempt_row.get(
                        "driver_name"
                    ),
                "car_attempt_index":
                    attempt_row.get(
                        "car_attempt_index"
                    ),
                "mapped_capture_event_id":
                    capture_row[
                        "chronology_event_id"
                    ],
                "mapped_capture_time_utc":
                    capture_row[
                        "event_time_utc"
                    ],
                "timing_class":
                    (
                        "UNIQUE_SINGLETON_"
                        "CAPTURE_MATCH"
                    ),
                "timing_basis":
                    (
                        "ONE_CANONICAL_ONE_CAPTURE_"
                        "SAME_CAR"
                    ),
                "mapping_support":
                    (
                        "UNIQUE_1_TO_1_SAME_CAR_"
                        "NO_ORDINAL_AMBIGUITY"
                    ),
                "performance_alignment_usable":
                    True,
                "chronology_usable":
                    False,
                "queue_replay_usable":
                    False,
                "time_semantic_note":
                    (
                        "Unique same-car 1:1 mapping "
                        "between one canonical attempt "
                        "and one qualifier capture. "
                        "No within-car ordinal ambiguity exists. "
                        "Recorder capture is still only an "
                        "approximate performance timestamp."
                    ),
            }
        )

    result = pd.DataFrame(
        rows
    )

    # =========================================================
    # Assertions
    # =========================================================

    if len(result) != 7:
        raise RuntimeError(
            f"Expected exactly 7 supported 2024 rows, "
            f"got {len(result)}"
        )

    if result[
        "attempt_id"
    ].duplicated().any():
        raise RuntimeError(
            "Duplicate attempt_id in output."
        )

    if result[
        "mapped_capture_event_id"
    ].duplicated().any():
        raise RuntimeError(
            "Duplicate capture event in output."
        )

    class_counts = (
        result[
            "timing_class"
        ]
        .value_counts()
        .to_dict()
    )

    if (
        class_counts.get(
            "EXISTING_CONSTRAINED_SEQUENCE_LINK",
            0,
        )
        != 3
    ):
        raise RuntimeError(
            "Expected 3 existing constrained sequence links."
        )

    if (
        class_counts.get(
            "UNIQUE_SINGLETON_CAPTURE_MATCH",
            0,
        )
        != 4
    ):
        raise RuntimeError(
            "Expected 4 singleton capture matches."
        )

    # =========================================================
    # Save
    # =========================================================

    result = result.sort_values(
        "mapped_capture_time_utc"
    ).reset_index(
        drop=True
    )

    qa = pd.DataFrame(
        [
            {
                "metric":
                    "total_supported_rows",
                "value":
                    len(result),
            },
            {
                "metric":
                    "existing_constrained_sequence_links",
                "value":
                    int(
                        (
                            result[
                                "timing_class"
                            ]
                            == (
                                "EXISTING_CONSTRAINED_"
                                "SEQUENCE_LINK"
                            )
                        ).sum()
                    ),
            },
            {
                "metric":
                    "unique_singleton_capture_matches",
                "value":
                    int(
                        (
                            result[
                                "timing_class"
                            ]
                            == (
                                "UNIQUE_SINGLETON_"
                                "CAPTURE_MATCH"
                            )
                        ).sum()
                    ),
            },
            {
                "metric":
                    "chronology_usable_rows",
                "value":
                    int(
                        result[
                            "chronology_usable"
                        ].sum()
                    ),
            },
            {
                "metric":
                    "queue_replay_usable_rows",
                "value":
                    int(
                        result[
                            "queue_replay_usable"
                        ].sum()
                    ),
            },
        ]
    )

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    result.to_csv(
        OUTPUT_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    qa.to_csv(
        QA_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    # =========================================================
    # Print report
    # =========================================================

    print()
    print("=" * 90)
    print(
        "2024 SUPPORTED PERFORMANCE-GRADE "
        "TIMING MATERIALIZATION"
    )
    print("=" * 90)

    print()
    print(
        "Total rows:",
        len(result)
    )

    print()
    print("TIMING CLASS COUNTS")
    print("-" * 40)

    print(
        result[
            "timing_class"
        ]
        .value_counts()
        .to_string()
    )

    print()
    print("ROWS")
    print("-" * 40)

    print(
        result[
            [
                "car_number",
                "driver_name",
                "car_attempt_index",
                "mapped_capture_time_utc",
                "timing_class",
                "mapping_support",
            ]
        ].to_string(
            index=False
        )
    )

    print()
    print("SEMANTIC POLICY")
    print("-" * 40)

    print(
        "performance_alignment_usable = True"
    )

    print(
        "chronology_usable = False"
    )

    print(
        "queue_replay_usable = False"
    )

    print(
        "Unresolved multi-attempt count-match "
        "cars remain unresolved."
    )

    print()
    print("=" * 90)
    print("OUTPUT")
    print("=" * 90)

    print(
        OUTPUT_FILE
    )

    print(
        QA_FILE
    )


if __name__ == "__main__":
    main()
