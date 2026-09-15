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
    "weather/output/performance_grade_attempt_timing.csv"
)

QA_FILE = Path(
    "weather/output/performance_grade_attempt_timing_qa.csv"
)

TARGET_SESSIONS = [
    "INDY500_DAY1_2020",
    "INDY500_DAY1_2021",
    "INDY500_DAY1_2023",
]

CALIBRATION_REFERENCE = (
    "2021_54_OF_54_EXACT_SEQUENCE_REPRODUCTION"
)


def normalize_car(value):
    if pd.isna(value):
        return None

    s = str(value).strip()

    if re.fullmatch(r"\d+\.0", s):
        s = s[:-2]

    if s.isdigit():
        return str(int(s))

    return s


def extract_capture_car(row):
    raw = row.get("event_payload_json")

    if pd.isna(raw):
        return None

    try:
        outer = json.loads(raw)
    except Exception:
        return None

    payload = outer.get(
        "capture_source_payload"
    )

    if payload is None:
        return None

    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except Exception:
            return None

    if not isinstance(payload, dict):
        return None

    return normalize_car(
        payload.get("currentQualifier")
    )


def build_sequence_matches(
    attempts,
    events,
    session_id,
):
    a = attempts[
        attempts["session_id"] == session_id
    ].copy()

    e = events[
        (events["session_id"] == session_id)
        & (events["event_type"] == "ATTEMPT_START")
    ].copy()

    rows = []

    for car, ca_all in a.groupby("_car"):

        ce = e[
            e["_capture_car"] == car
        ].copy()

        ca = ca_all[
            ca_all["car_attempt_index"].notna()
        ].copy()

        ca[
            "car_attempt_index"
        ] = ca[
            "car_attempt_index"
        ].astype(int)

        ca = ca.sort_values(
            "car_attempt_index"
        )

        ce = ce.sort_values(
            "_event_time"
        )

        indexed_values = (
            ca["car_attempt_index"]
            .tolist()
        )

        expected = list(
            range(
                1,
                len(indexed_values) + 1
            )
        )

        canonical_rows = len(ca_all)
        indexed_rows = len(ca)
        capture_rows = len(ce)

        exact_match = (
            canonical_rows == indexed_rows
            and indexed_rows == capture_rows
            and indexed_rows > 0
            and indexed_values == expected
        )

        if not exact_match:
            continue

        for (
            (_, attempt_row),
            (_, event_row),
        ) in zip(
            ca.iterrows(),
            ce.iterrows(),
        ):
            rows.append(
                {
                    "attempt_id":
                        attempt_row[
                            "attempt_id"
                        ],
                    "session_id":
                        session_id,
                    "entry_key":
                        attempt_row.get(
                            "entry_key",
                            None,
                        ),
                    "attempt_key":
                        attempt_row.get(
                            "attempt_key",
                            None,
                        ),
                    "car_number":
                        attempt_row.get(
                            "car_number",
                            None,
                        ),
                    "driver_name":
                        attempt_row.get(
                            "driver_name",
                            None,
                        ),
                    "car_attempt_index":
                        attempt_row[
                            "car_attempt_index"
                        ],
                    "mapped_capture_event_id":
                        event_row[
                            "chronology_event_id"
                        ],
                    "mapped_capture_time_utc":
                        event_row[
                            "event_time_utc"
                        ],
                    "timing_class":
                        "PERFORMANCE_GRADE_SEQUENCE_MATCH",
                    "timing_basis":
                        "WITHIN_CAR_SEQUENCE_COUNT_MATCH",
                    "calibration_status":
                        "VALIDATED_RULE",
                    "calibration_reference":
                        CALIBRATION_REFERENCE,
                    "performance_alignment_usable":
                        True,
                    "chronology_usable":
                        False,
                    "queue_replay_usable":
                        False,
                    "time_semantic_note":
                        (
                            "Recorder capture mapped to canonical "
                            "attempt by exact within-car count and "
                            "sequence agreement. Suitable only for "
                            "performance-grade approximate environmental "
                            "alignment; not a timed-run start and not "
                            "valid for chronology or queue replay."
                        ),
                }
            )

    return rows


def validate_2021_against_existing_links(
    result,
    events,
):
    predicted = result[
        result["session_id"]
        == "INDY500_DAY1_2021"
    ].copy()

    existing = events[
        (events["session_id"] == "INDY500_DAY1_2021")
        & (
            events["event_type"]
            == "ATTEMPT_START"
        )
        & events["attempt_id"].notna()
    ][
        [
            "attempt_id",
            "chronology_event_id",
            "event_time_utc",
        ]
    ].copy()

    existing = existing.rename(
        columns={
            "chronology_event_id":
                "existing_event_id",
            "event_time_utc":
                "existing_time_utc",
        }
    )

    check = predicted.merge(
        existing,
        on="attempt_id",
        how="outer",
        indicator=True,
    )

    check["event_id_match"] = (
        check["mapped_capture_event_id"]
        == check["existing_event_id"]
    )

    check["time_match"] = (
        check["mapped_capture_time_utc"]
        == check["existing_time_utc"]
    )

    mismatches = check[
        (check["_merge"] != "both")
        | (
            ~check[
                "event_id_match"
            ].fillna(False)
        )
        | (
            ~check[
                "time_match"
            ].fillna(False)
        )
    ]

    return {
        "predicted_rows":
            len(predicted),
        "existing_rows":
            len(existing),
        "mismatch_rows":
            len(mismatches),
        "pass":
            (
                len(predicted) == 54
                and len(existing) == 54
                and len(mismatches) == 0
            ),
    }


def main():

    for file in [
        ATTEMPTS_FILE,
        EVENTS_FILE,
    ]:
        if not file.exists():
            raise FileNotFoundError(
                f"Missing file: {file}"
            )

    attempts = pd.read_csv(
        ATTEMPTS_FILE
    )

    events = pd.read_csv(
        EVENTS_FILE
    )

    attempts["_car"] = attempts[
        "car_number"
    ].apply(normalize_car)

    events["_capture_car"] = events.apply(
        extract_capture_car,
        axis=1,
    )

    events["_event_time"] = pd.to_datetime(
        events["event_time_utc"],
        utc=True,
        errors="coerce",
    )

    all_rows = []

    for session_id in TARGET_SESSIONS:
        all_rows.extend(
            build_sequence_matches(
                attempts,
                events,
                session_id,
            )
        )

    result = pd.DataFrame(
        all_rows
    )

    if result.empty:
        raise RuntimeError(
            "No performance-grade timing rows created."
        )

    if result["attempt_id"].duplicated().any():
        dupes = result[
            result["attempt_id"].duplicated(
                keep=False
            )
        ]

        raise RuntimeError(
            "Duplicate attempt_id in output:\n"
            + dupes.to_string(index=False)
        )

    calibration = (
        validate_2021_against_existing_links(
            result,
            events,
        )
    )

    if not calibration["pass"]:
        raise RuntimeError(
            "2021 calibration failed: "
            f"{calibration}"
        )

    qa_rows = []

    for session_id in TARGET_SESSIONS:

        canonical_rows = len(
            attempts[
                attempts["session_id"]
                == session_id
            ]
        )

        output_rows = len(
            result[
                result["session_id"]
                == session_id
            ]
        )

        coverage = (
            100.0
            * output_rows
            / canonical_rows
            if canonical_rows
            else 0.0
        )

        qa_rows.append(
            {
                "session_id":
                    session_id,
                "canonical_attempts":
                    canonical_rows,
                "performance_grade_timed_attempts":
                    output_rows,
                "coverage_pct":
                    coverage,
            }
        )

    qa = pd.DataFrame(
        qa_rows
    )

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    result = result.sort_values(
        [
            "session_id",
            "mapped_capture_time_utc",
            "car_number",
            "car_attempt_index",
        ]
    ).reset_index(drop=True)

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

    print()
    print("=" * 90)
    print(
        "PERFORMANCE-GRADE ATTEMPT TIMING "
        "MATERIALIZATION"
    )
    print("=" * 90)

    print()
    print(
        "Total rows:",
        len(result)
    )

    print()
    print("ROWS BY SESSION")
    print("-" * 40)

    print(
        result.groupby(
            "session_id"
        )
        .size()
        .to_string()
    )

    print()
    print("COVERAGE")
    print("-" * 40)

    print(
        qa.to_string(
            index=False
        )
    )

    print()
    print("2021 CALIBRATION")
    print("-" * 40)

    print(
        "Predicted rows:",
        calibration[
            "predicted_rows"
        ]
    )

    print(
        "Existing reliable links:",
        calibration[
            "existing_rows"
        ]
    )

    print(
        "Mismatches:",
        calibration[
            "mismatch_rows"
        ]
    )

    if calibration["pass"]:
        print(
            "PASS: sequence rule reproduces "
            "2021 reliable links 54/54 exactly."
        )

    print()
    print("SEMANTIC POLICY")
    print("-" * 40)

    print(
        "timing_class = "
        "PERFORMANCE_GRADE_SEQUENCE_MATCH"
    )

    print(
        "performance_alignment_usable = True"
    )

    print(
        "chronology_usable = False"
    )

    print(
        "queue_replay_usable = False"
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