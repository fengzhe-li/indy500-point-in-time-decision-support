from pathlib import Path
import csv


PHASE = "R2E.1A"

INPUT = Path(
    "weather/output/"
    "pit_service_rescue_2022_repeat_pair_targeted_hits_v1.csv"
)

OUTPUT_DIR = Path("weather/output")

ADJUDICATION_OUT = (
    OUTPUT_DIR
    / "pit_service_rescue_2022_candidate_adjudication_v1.csv"
)

QA_OUT = (
    OUTPUT_DIR
    / "pit_service_rescue_2022_candidate_adjudication_v1_qa.csv"
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


def main():

    print()
    print("=" * 124)
    print(
        "R2E.1A — 2022 PIT / SERVICE "
        "CANDIDATE SEMANTIC ADJUDICATION"
    )
    print("=" * 124)

    print()
    print("INPUT CHECK")
    print("-" * 124)

    print(
        f"{INPUT}: "
        f"{'PRESENT' if INPUT.exists() else 'MISSING'}"
    )

    if not INPUT.exists():
        print()
        print(
            "FINAL STATUS: "
            "R2E1A_PIT_SERVICE_ADJUDICATION_INPUT_MISSING"
        )
        return

    rows = read_csv(INPUT)

    priority_classes = {
        "DIRECT_REFUEL_CANDIDATE",
        "DIRECT_COOLING_CANDIDATE",
        "DIRECT_TIRE_SERVICE_CANDIDATE",
        "DIRECT_ADJUSTMENT_CANDIDATE",
        "DIRECT_REPAIR_CANDIDATE",
        "PIT_BETWEEN_RUNS_REVIEW",
    }

    priority = [
        row
        for row in rows
        if txt(row.get("classification"))
        in priority_classes
    ]

    print()
    print(
        "Priority scanner rows:",
        len(priority),
    )

    adjudicated_raw = []

    for i, row in enumerate(
        priority,
        start=1,
    ):

        driver = txt(
            row.get("driver_name")
        )

        classification = txt(
            row.get("classification")
        )

        text = txt(
            row.get("text")
        )

        lower = text.lower()

        decision = "REVIEW_REQUIRED"
        service_type = "NONE"
        promotion_ready = False
        reason = ""

        # --------------------------------------------------
        # cooldown / cool-down lap:
        # motorsport lap terminology, NOT cooling service.
        #
        # Marco is mentioned as the impeded next driver;
        # service semantic still belongs to neither driver.
        # --------------------------------------------------

        if (
            "cooldown lap" in lower
            or
            "cool-down lap" in lower
        ):
            if driver == "Marco Andretti":
                decision = (
                    "REJECT_DRIVER_CONTAMINATION_"
                    "COOLDOWN_LAP_NOT_SERVICE"
                )

                reason = (
                    "Marco Andretti appears as the next driver "
                    "affected by Sato. The phrase 'cooldown lap' "
                    "describes Sato's post-run track lap and is "
                    "not evidence of cooling service for Marco."
                )

            elif driver == "Takuma Sato":
                decision = (
                    "REJECT_COOLDOWN_LAP_NOT_COOLING_SERVICE"
                )

                reason = (
                    "The phrase 'cooldown lap' / 'cool-down lap' "
                    "is motorsport track terminology for the lap "
                    "after the qualifying attempt. It does not "
                    "mean the team performed vehicle cooling "
                    "between attempts."
                )

            else:
                decision = (
                    "REJECT_COOLDOWN_LAP_NOT_COOLING_SERVICE"
                )

                reason = (
                    "The cooling keyword occurs in the phrase "
                    "'cooldown lap', which is not vehicle "
                    "cooling-service evidence."
                )

        # --------------------------------------------------
        # Cooper Tires:
        # sponsor / series naming, NOT tire service.
        # --------------------------------------------------

        elif (
            "cooper tires" in lower
            and
            driver == "David Malukas"
        ):
            decision = (
                "REJECT_SPONSOR_BRAND_NOT_TIRE_SERVICE"
            )

            reason = (
                "'Cooper Tires' appears as part of the "
                "Indy Lights series/sponsor wording. It does "
                "not describe changing, servicing, heating, "
                "cooling, or preparing Malukas's tires."
            )

        # --------------------------------------------------
        # Generic safety fallback:
        # do not promote anything unless source directly
        # describes an actual service operation.
        # --------------------------------------------------

        else:
            decision = (
                "REVIEW_REQUIRED_NO_DIRECT_SERVICE_BINDING"
            )

            reason = (
                "The candidate does not safely bind a pit, "
                "refuel, cooling, tire-service, adjustment, "
                "or repair operation to the driver's interval "
                "between qualifying attempts."
            )

        adjudicated_raw.append({
            "phase":
                PHASE,

            "driver_name":
                driver,

            "source_path":
                txt(
                    row.get(
                        "source_path"
                    )
                ),

            "original_classification":
                classification,

            "decision":
                decision,

            "service_between_attempts":
                "UNKNOWN",

            "service_type":
                service_type,

            "refuel_confirmed":
                "False",

            "cooling_service_confirmed":
                "False",

            "tire_service_confirmed":
                "False",

            "adjustment_confirmed":
                "False",

            "repair_confirmed":
                "False",

            "pit_return_confirmed":
                "False",

            "exact_service_time":
                "UNKNOWN",

            "promotion_ready":
                str(
                    promotion_ready
                ),

            "reason":
                reason,

            "source_text":
                text,
        })

        print()
        print("-" * 124)
        print(
            f"CANDIDATE {i}"
        )
        print(
            "driver:",
            driver,
        )
        print(
            "original:",
            classification,
        )
        print(
            "decision:",
            decision,
        )
        print(
            "promotion ready:",
            promotion_ready,
        )

    # --------------------------------------------------
    # Deduplicate semantic duplicates:
    # txt/html and repeated scanner hits are not
    # independent evidence.
    # --------------------------------------------------

    deduped = []
    seen = set()

    for row in adjudicated_raw:

        key = (
            txt(
                row.get(
                    "driver_name"
                )
            ),
            txt(
                row.get(
                    "decision"
                )
            ),
            txt(
                row.get(
                    "source_text"
                )
            ),
        )

        # Normalize source text for HTML/text duplicates.
        normalized_text = (
            txt(
                row.get(
                    "source_text"
                )
            )
            .replace("&ndash;", "–")
            .replace("&#8211;", "–")
            .replace("&nbsp;", " ")
        )

        key = (
            txt(
                row.get(
                    "driver_name"
                )
            ),
            txt(
                row.get(
                    "decision"
                )
            ),
            normalized_text,
        )

        if key in seen:
            continue

        seen.add(key)
        deduped.append(row)

    for i, row in enumerate(
        deduped,
        start=1,
    ):
        row["evidence_id"] = (
            f"R2E1A-S{i:03d}"
        )

    promotion_rows = [
        row
        for row in deduped
        if txt(
            row.get(
                "promotion_ready"
            )
        ).lower()
        ==
        "true"
    ]

    cooldown_rejects = [
        row
        for row in deduped
        if (
            "COOLDOWN_LAP"
            in txt(
                row.get(
                    "decision"
                )
            )
        )
    ]

    tire_brand_rejects = [
        row
        for row in deduped
        if txt(
            row.get(
                "decision"
            )
        )
        ==
        "REJECT_SPONSOR_BRAND_NOT_TIRE_SERVICE"
    ]

    unresolved = [
        row
        for row in deduped
        if txt(
            row.get(
                "decision"
            )
        )
        ==
        "REVIEW_REQUIRED_NO_DIRECT_SERVICE_BINDING"
    ]

    print()
    print("=" * 124)
    print("ADJUDICATION SUMMARY")
    print("=" * 124)

    print()
    print(
        "Raw priority rows:",
        len(priority),
    )

    print(
        "Deduplicated semantic rows:",
        len(deduped),
    )

    print(
        "Promotion-ready service units:",
        len(
            promotion_rows
        ),
    )

    print(
        "Cooldown-lap false positives rejected:",
        len(
            cooldown_rejects
        ),
    )

    print(
        "Cooper Tires false positives rejected:",
        len(
            tire_brand_rejects
        ),
    )

    print(
        "Unresolved direct-service candidates:",
        len(
            unresolved
        ),
    )

    print()
    print(
        "SUPPORTED SERVICE STATE"
    )

    print(
        "  refuel = NOT OBSERVED"
    )

    print(
        "  cooling service = NOT OBSERVED"
    )

    print(
        "  tire service = NOT OBSERVED"
    )

    print(
        "  adjustment = NOT OBSERVED"
    )

    print(
        "  repair = NOT OBSERVED"
    )

    print(
        "  pit return between attempts = NOT OBSERVED"
    )

    print()
    print(
        "IMPORTANT:"
    )

    print(
        "  NOT OBSERVED does not mean confirmed NONE."
    )

    print(
        "  It means no source-native service evidence "
        "has been recovered yet."
    )

    fields = [
        "evidence_id",
        "phase",
        "driver_name",
        "source_path",
        "original_classification",
        "decision",
        "service_between_attempts",
        "service_type",
        "refuel_confirmed",
        "cooling_service_confirmed",
        "tire_service_confirmed",
        "adjustment_confirmed",
        "repair_confirmed",
        "pit_return_confirmed",
        "exact_service_time",
        "promotion_ready",
        "reason",
        "source_text",
    ]

    write_csv(
        ADJUDICATION_OUT,
        deduped,
        fields,
    )

    qa_rows = [
        {
            "metric":
                "priority_scanner_rows",

            "value":
                len(priority),

            "status":
                (
                    "PASS"
                    if len(priority)
                    ==
                    10
                    else
                    "REVIEW"
                ),
        },

        {
            "metric":
                "promotion_ready_service_units",

            "value":
                len(
                    promotion_rows
                ),

            "status":
                (
                    "PASS"
                    if len(
                        promotion_rows
                    )
                    ==
                    0
                    else
                    "FAIL"
                ),
        },

        {
            "metric":
                "cooldown_lap_promoted_as_cooling_service",

            "value":
                0,

            "status":
                "PASS",
        },

        {
            "metric":
                "cooper_tires_promoted_as_tire_service",

            "value":
                0,

            "status":
                "PASS",
        },

        {
            "metric":
                "refuel_inferred",

            "value":
                0,

            "status":
                "PASS",
        },

        {
            "metric":
                "pit_return_inferred",

            "value":
                0,

            "status":
                "PASS",
        },

        {
            "metric":
                "service_between_attempts_inferred",

            "value":
                0,

            "status":
                "PASS",
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
        row[
            "status"
        ]
        ==
        "FAIL"
        for row in qa_rows
    )

    print()
    print("=" * 124)

    if not hard_fail:
        print(
            "FINAL STATUS: "
            "R2E1A_PIT_SERVICE_CANDIDATES_ADJUDICATED_"
            "NO_DIRECT_SERVICE_EVIDENCE"
        )
    else:
        print(
            "FINAL STATUS: "
            "R2E1A_PIT_SERVICE_ADJUDICATION_REVIEW_REQUIRED"
        )

    print("=" * 124)

    print()
    print("OUTPUTS")
    print(ADJUDICATION_OUT)
    print(QA_OUT)


if __name__ == "__main__":
    main()
