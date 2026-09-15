from pathlib import Path
import csv
import hashlib


RESULT_ROWS = Path(
    "weather/output/"
    "official_day1_results_attempt_rows_v1.csv"
)

PREVIOUS_EVIDENCE = Path(
    "weather/output/"
    "chronology_rescue_2022_adjudicated_evidence_v2.csv"
)

OUTPUT_DIR = Path("weather/output")

EVIDENCE_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_adjudicated_evidence_v3.csv"
)

EDGES_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_ordering_edges_v3.csv"
)

QA_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_adjudicated_evidence_v3_qa.csv"
)


def read_csv(path):
    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as f:
        return list(csv.DictReader(f))


def write_csv(path, rows, fields):
    with path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as f:
        w = csv.DictWriter(
            f,
            fieldnames=fields,
        )
        w.writeheader()
        w.writerows(rows)


def txt(v):
    return "" if v is None else str(v).strip()


def norm_car(v):
    t = txt(v)
    if not t:
        return ""
    try:
        return str(int(float(t)))
    except Exception:
        return t.lstrip("0") or "0"


def sid(*parts):
    payload = "|".join(
        txt(x)
        for x in parts
    )
    return (
        "R1G8-"
        + hashlib.sha256(
            payload.encode("utf-8")
        ).hexdigest()[:16].upper()
    )


def find_rows(
    rows,
    car,
):
    target = norm_car(car)

    return [
        r
        for r in rows
        if (
            txt(r.get("year"))
            == "2022"
            and
            norm_car(
                r.get("car_number")
            )
            == target
        )
    ]


def main():

    print()
    print("=" * 120)
    print(
        "R1G.8 — 2022 McLAUGHLIN / NEWGARDEN "
        "CHRONOLOGY PROMOTION V3"
    )
    print("=" * 120)

    for path in [
        RESULT_ROWS,
        PREVIOUS_EVIDENCE,
    ]:
        print(
            path,
            ":",
            "PRESENT"
            if path.exists()
            else "MISSING",
        )

    if (
        not RESULT_ROWS.exists()
        or
        not PREVIOUS_EVIDENCE.exists()
    ):
        print(
            "FINAL STATUS: "
            "2022_MCL_NEWG_PROMOTION_INPUT_MISSING"
        )
        return

    results = read_csv(
        RESULT_ROWS
    )

    previous = read_csv(
        PREVIOUS_EVIDENCE
    )

    mcl = find_rows(
        results,
        "3",
    )

    newg = find_rows(
        results,
        "2",
    )

    karam = find_rows(
        results,
        "24",
    )

    print()
    print("=" * 120)
    print("McLAUGHLIN RESULT CONTEXT")
    print("=" * 120)

    for r in mcl:
        print(
            "row=",
            r.get("result_row"),
            "| speed=",
            r.get("speed_avg_mph"),
            "| status=",
            repr(
                r.get("status")
            ),
        )

    print()
    print("=" * 120)
    print("NEWGARDEN RESULT CONTEXT")
    print("=" * 120)

    for r in newg:
        print(
            "row=",
            r.get("result_row"),
            "| speed=",
            r.get("speed_avg_mph"),
            "| status=",
            repr(
                r.get("status")
            ),
        )

    print()
    print("=" * 120)
    print("KARAM RESULT CONTEXT — REVIEW ONLY")
    print("=" * 120)

    for r in karam:
        print(
            "row=",
            r.get("result_row"),
            "| speed=",
            r.get("speed_avg_mph"),
            "| status=",
            repr(
                r.get("status")
            ),
        )

    mcl_withdrawn = [
        r for r in mcl
        if (
            txt(r.get("speed_avg_mph"))
            == "231.543"
            and
            txt(r.get("status"))
            == "Withdrawn"
        )
    ]

    mcl_rerun = [
        r for r in mcl
        if (
            txt(r.get("speed_avg_mph"))
            == "230.154"
            and
            txt(r.get("status"))
            == ""
        )
    ]

    newg_original = [
        r for r in newg
        if (
            txt(r.get("speed_avg_mph"))
            == "231.580"
            and
            txt(r.get("status"))
            == ""
        )
    ]

    newg_no_attempt = [
        r for r in newg
        if (
            txt(r.get("status"))
            == "No Attempt"
        )
    ]

    print()
    print(
        "McLaughlin 231.543 Withdrawn unique:",
        len(mcl_withdrawn),
    )

    print(
        "McLaughlin 230.154 rerun unique:",
        len(mcl_rerun),
    )

    print(
        "Newgarden 231.580 original unique:",
        len(newg_original),
    )

    print(
        "Newgarden No Attempt unique:",
        len(newg_no_attempt),
    )

    can_promote_mcl = (
        len(mcl_withdrawn) == 1
        and
        len(mcl_rerun) == 1
    )

    can_promote_newg = (
        len(newg_original) == 1
        and
        len(newg_no_attempt) == 1
    )

    fields = list(
        previous[0].keys()
    )

    evidence = [
        dict(r)
        for r in previous
    ]

    edges = []

    if can_promote_mcl:

        eid = sid(
            "2022",
            "3",
            "231.543",
            "BEFORE",
            "3",
            "230.154",
        )

        row = {
            field: ""
            for field in fields
        }

        row.update({
            "evidence_id":
                eid,

            "year":
                "2022",

            "session":
                "INDY500_DAY1_2022",

            "car_number":
                "3",

            "driver_name":
                "Scott McLaughlin",

            "speed_mph":
                "231.543",

            "official_result_row":
                txt(
                    mcl_withdrawn[0].get(
                        "result_row"
                    )
                ),

            "official_result_status":
                "Withdrawn",

            "constraint_class":
                "ORDERING_ONLY",

            "related_car_number":
                "3",

            "related_speed_mph":
                "230.154",

            "ordering_relation":
                (
                    "MCLAUGHLIN_231.543_WITHDRAWN_"
                    "BEFORE_MCLAUGHLIN_230.154_RERUN"
                ),

            "source_authority":
                (
                    "INDYCAR_OFFICIAL_RESULTS"
                    "+REPUTABLE_SECONDARY"
                ),

            "source_title":
                (
                    "The Race / NBC Sports "
                    "2022 Day 1 qualifying reports"
                ),

            "evidence_summary":
                (
                    "Reports state McLaughlin surrendered "
                    "his 15th-place 231.543 result to enter "
                    "Lane 1 and subsequently reran at "
                    "230.154, dropping to 26th."
                ),

            "evidence_stage":
                "R1G8_ADJUDICATED",

            "adjudication_status":
                "PROMOTED",

            "chronology_usable":
                "True",

            "queue_replay_usable":
                "False",

            "canonical_promoted":
                "False",

            "notes":
                (
                    "Ordering and driver-specific Lane 1 "
                    "historical event supported. "
                    "No queue wait inferred."
                ),
        })

        evidence.append(
            row
        )

        edges.append({
            "edge_id":
                eid,

            "from":
                "MCLAUGHLIN_231.543_WITHDRAWN",

            "relation":
                "BEFORE",

            "to":
                "MCLAUGHLIN_230.154_RERUN",

            "constraint_class":
                "ORDERING_ONLY",

            "notes":
                (
                    "Secondary reporting plus "
                    "official Results."
                ),
        })

    if can_promote_newg:

        eid = sid(
            "2022",
            "2",
            "231.580",
            "BEFORE",
            "2",
            "NO_ATTEMPT",
        )

        row = {
            field: ""
            for field in fields
        }

        row.update({
            "evidence_id":
                eid,

            "year":
                "2022",

            "session":
                "INDY500_DAY1_2022",

            "car_number":
                "2",

            "driver_name":
                "Josef Newgarden",

            "speed_mph":
                "231.580",

            "official_result_row":
                txt(
                    newg_original[0].get(
                        "result_row"
                    )
                ),

            "official_result_status":
                "",

            "constraint_class":
                "ORDERING_ONLY",

            "related_car_number":
                "2",

            "related_speed_mph":
                "",

            "ordering_relation":
                (
                    "NEWGARDEN_231.580_ORIGINAL_"
                    "BEFORE_NEWGARDEN_NO_ATTEMPT_RERUN"
                ),

            "source_authority":
                (
                    "INDYCAR_OFFICIAL_RESULTS"
                    "+REPUTABLE_SECONDARY"
                ),

            "source_title":
                (
                    "The Race / NBC Sports "
                    "2022 Day 1 qualifying reports"
                ),

            "evidence_summary":
                (
                    "Reports state Newgarden withdrew "
                    "his original 14th-place result for "
                    "a rerun; weather caution occurred "
                    "after the rerun had begun and the "
                    "original result was ultimately retained."
                ),

            "evidence_stage":
                "R1G8_ADJUDICATED",

            "adjudication_status":
                "PROMOTED",

            "chronology_usable":
                "True",

            "queue_replay_usable":
                "False",

            "canonical_promoted":
                "False",

            "notes":
                (
                    "No exact lap of interruption fixed "
                    "because secondary descriptions differ."
                ),
        })

        evidence.append(
            row
        )

        edges.append({
            "edge_id":
                eid,

            "from":
                "NEWGARDEN_231.580_ORIGINAL",

            "relation":
                "BEFORE",

            "to":
                "NEWGARDEN_NO_ATTEMPT_RERUN",

            "constraint_class":
                "ORDERING_ONLY",

            "notes":
                (
                    "Rerun began before second "
                    "weather interruption."
                ),
        })

        eid2 = sid(
            "2022",
            "NEWGARDEN_RERUN",
            "BEFORE",
            "SECOND_WEATHER_STOP",
        )

        edges.append({
            "edge_id":
                eid2,

            "from":
                "NEWGARDEN_NO_ATTEMPT_RERUN",

            "relation":
                "BEFORE_OR_INTERRUPTED_BY",

            "to":
                "SECOND_WEATHER_STOP",

            "constraint_class":
                "ORDERING_ONLY",

            "notes":
                (
                    "Rerun had begun when weather "
                    "caution stopped qualifying. "
                    "Exact lap not fixed."
                ),
        })

    # ========================================================
    # KARAM — deliberately unresolved
    # ========================================================

    karam_promotions = 0

    write_csv(
        EVIDENCE_OUT,
        evidence,
        fields,
    )

    write_csv(
        EDGES_OUT,
        edges,
        [
            "edge_id",
            "from",
            "relation",
            "to",
            "constraint_class",
            "notes",
        ],
    )

    qa = [
        {
            "metric":
                "mclaughlin_ordering_promoted",
            "value":
                int(
                    can_promote_mcl
                ),
            "status":
                (
                    "PASS"
                    if can_promote_mcl
                    else "REVIEW"
                ),
        },
        {
            "metric":
                "newgarden_ordering_promoted",
            "value":
                int(
                    can_promote_newg
                ),
            "status":
                (
                    "PASS"
                    if can_promote_newg
                    else "REVIEW"
                ),
        },
        {
            "metric":
                "karam_specific_attempt_promoted",
            "value":
                karam_promotions,
            "status":
                "PASS",
        },
        {
            "metric":
                "exact_weather_stop_timestamp_invented",
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
        "PROMOTED ORDERING EDGES"
    )
    print("=" * 120)

    for edge in edges:
        print()
        print(
            edge["from"]
        )
        print(
            " ",
            edge["relation"],
        )
        print(
            edge["to"]
        )

    print()
    print("=" * 120)
    print("SUMMARY")
    print("=" * 120)

    print(
        "Previous evidence rows:",
        len(
            previous
        ),
    )

    print(
        "New evidence rows:",
        len(
            evidence
        ),
    )

    print(
        "New ordering edges:",
        len(
            edges
        ),
    )

    print(
        "Karam specific promotions:",
        karam_promotions,
    )

    print()
    print(
        "No exact interruption timestamp "
        "was invented."
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
        can_promote_mcl
        and
        can_promote_newg
        and
        karam_promotions == 0
    ):

        print(
            "FINAL STATUS: "
            "2022_MCLAUGHLIN_NEWGARDEN_"
            "CHRONOLOGY_PROMOTED"
        )

    else:

        print(
            "FINAL STATUS: "
            "2022_MCLAUGHLIN_NEWGARDEN_"
            "PROMOTION_REVIEW_REQUIRED"
        )

    print("=" * 120)

    print()
    print("OUTPUTS")
    print(EVIDENCE_OUT)
    print(EDGES_OUT)
    print(QA_OUT)


if __name__ == "__main__":
    main()
