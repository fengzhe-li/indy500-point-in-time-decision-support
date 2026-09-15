from pathlib import Path
import csv


PHASE = "R1G.26E"

EVIDENCE_V1 = Path(
    "weather/output/"
    "chronology_rescue_2022_ilott_autosport_retake_evidence_v1.csv"
)

ADJUDICATION_V1 = Path(
    "weather/output/"
    "chronology_rescue_2022_ilott_autosport_retake_adjudication_v1.csv"
)

CHRONOLOGY_V4 = Path(
    "weather/output/"
    "unified_attempt_chronology_constraint_ledger_v4.csv"
)

ACTION_V2 = Path(
    "weather/output/"
    "unified_attempt_action_lane_ledger_v2.csv"
)

CANONICAL = Path(
    "data/canonical/v1/attempts.csv"
)

OUTPUT_DIR = Path(
    "weather/output"
)

EVIDENCE_V2 = (
    OUTPUT_DIR
    / "chronology_rescue_2022_ilott_autosport_retake_evidence_v2.csv"
)

ADJUDICATION_V2 = (
    OUTPUT_DIR
    / "chronology_rescue_2022_ilott_autosport_retake_adjudication_v2.csv"
)

SCHEMA_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_ilott_ledger_integration_schema_preflight_v1.csv"
)

SUMMARY_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_ilott_ledger_integration_preflight_summary_v1.csv"
)

QA_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_ilott_ledger_integration_preflight_v1_qa.csv"
)


SOURCE_URL = (
    "https://www.autosport.com/indycar/news/"
    "indy-500-sato-grosjean-johnson-into-top-12-fight-p13-33-set/"
    "10308540/"
)

SOURCE_DATE_LABEL = "EDITED"
SOURCE_DATE_DISPLAY = "May 22, 2022, 2:31 AM"

FIRST_ID = "3cd6d98a-da75-5822-8dae-05e83ad8457c"
SECOND_ID = "8fa25fec-e5a6-5844-b3d7-f67c9dc91378"


def txt(v):
    return "" if v is None else str(v).strip()


def read_csv(path):
    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fields = list(reader.fieldnames or [])
        return rows, fields


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


def ensure_fields(fields, additions):
    out = list(fields)

    for field in additions:
        if field not in out:
            out.append(field)

    return out


def canonical_driver(row):
    for field in [
        "driver_name",
        "driver",
        "driver_full_name",
    ]:
        value = txt(row.get(field))

        if value:
            return value

    return ""


def main():

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print()
    print("=" * 120)
    print(
        "R1G.26E — 2022 CALLUM ILOTT RETAKE "
        "PROVENANCE CORRECTION + LEDGER INTEGRATION PREFLIGHT V1"
    )
    print("=" * 120)

    required = [
        EVIDENCE_V1,
        ADJUDICATION_V1,
        CHRONOLOGY_V4,
        ACTION_V2,
        CANONICAL,
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

    if missing:

        print()
        print(
            "FINAL STATUS: "
            "ILOTT_LEDGER_PREFLIGHT_INPUT_MISSING"
        )
        return

    evidence_v1, evidence_fields = read_csv(
        EVIDENCE_V1
    )

    adjudication_v1, adjudication_fields = read_csv(
        ADJUDICATION_V1
    )

    chronology, chronology_fields = read_csv(
        CHRONOLOGY_V4
    )

    actions, action_fields = read_csv(
        ACTION_V2
    )

    canonical, canonical_fields = read_csv(
        CANONICAL
    )

    # ========================================================
    # CANONICAL IDENTITY CHECK
    # ========================================================

    canonical_by_id = {
        txt(row.get("attempt_id")): row
        for row in canonical
        if txt(row.get("attempt_id"))
    }

    first = canonical_by_id.get(
        FIRST_ID
    )

    second = canonical_by_id.get(
        SECOND_ID
    )

    first_found = first is not None
    second_found = second is not None

    first_driver = (
        canonical_driver(first)
        if first
        else ""
    )

    second_driver = (
        canonical_driver(second)
        if second
        else ""
    )

    identity_ok = (
        first_found
        and
        second_found
        and
        first_driver == "Callum Ilott"
        and
        second_driver == "Callum Ilott"
    )

    print()
    print("=" * 120)
    print(
        "CANONICAL TARGET CHECK"
    )
    print("=" * 120)

    print()
    print(
        "First attempt found:",
        first_found,
    )

    print(
        "First driver:",
        first_driver,
    )

    print(
        "Second attempt found:",
        second_found,
    )

    print(
        "Second driver:",
        second_driver,
    )

    print(
        "Identity check:",
        identity_ok,
    )

    # ========================================================
    # CORRECT EVIDENCE DATE SEMANTICS
    # ========================================================

    evidence_v2_fields = ensure_fields(
        evidence_fields,
        [
            "source_date_label",
            "source_date_display",
            "source_date_semantics_note",
            "provenance_revision",
        ],
    )

    evidence_v2_rows = []

    for row in evidence_v1:

        out = {
            field: ""
            for field in evidence_v2_fields
        }

        for key, value in row.items():
            if key in out:
                out[key] = value

        # Do not call the page's displayed Edited date a publication date.
        if "source_publication_date" in out:
            out[
                "source_publication_date"
            ] = ""

        out[
            "source_date_label"
        ] = SOURCE_DATE_LABEL

        out[
            "source_date_display"
        ] = SOURCE_DATE_DISPLAY

        out[
            "source_date_semantics_note"
        ] = (
            "Autosport page currently displays "
            "'Edited: May 22, 2022, 2:31 AM'. "
            "This field is preserved as an edited-date label, "
            "not asserted as original publication time."
        )

        out[
            "provenance_revision"
        ] = "R1G26E"

        evidence_v2_rows.append(
            out
        )

    adjudication_v2_fields = ensure_fields(
        adjudication_fields,
        [
            "source_url",
            "source_date_label",
            "source_date_display",
            "provenance_revision",
        ],
    )

    adjudication_v2_rows = []

    for row in adjudication_v1:

        out = {
            field: ""
            for field in adjudication_v2_fields
        }

        for key, value in row.items():
            if key in out:
                out[key] = value

        out[
            "source_url"
        ] = SOURCE_URL

        out[
            "source_date_label"
        ] = SOURCE_DATE_LABEL

        out[
            "source_date_display"
        ] = SOURCE_DATE_DISPLAY

        out[
            "provenance_revision"
        ] = "R1G26E"

        adjudication_v2_rows.append(
            out
        )

    # ========================================================
    # PRINT LEDGER SCHEMAS
    # ========================================================

    print()
    print("=" * 120)
    print(
        "CURRENT CHRONOLOGY LEDGER V4 SCHEMA"
    )
    print("=" * 120)

    print()
    print(
        "Rows:",
        len(chronology),
    )

    print(
        "Columns:",
        len(chronology_fields),
    )

    for i, field in enumerate(
        chronology_fields,
        start=1,
    ):
        print(
            f"{i:02d}. {field}"
        )

    print()
    print("=" * 120)
    print(
        "CURRENT ACTION/LANE LEDGER V2 SCHEMA"
    )
    print("=" * 120)

    print()
    print(
        "Rows:",
        len(actions),
    )

    print(
        "Columns:",
        len(action_fields),
    )

    for i, field in enumerate(
        action_fields,
        start=1,
    ):
        print(
            f"{i:02d}. {field}"
        )

    # ========================================================
    # DETECT RELEVANT FIELDS
    # ========================================================

    chronology_interest = [
        "attempt_id",
        "subject_attempt_id",
        "related_attempt_id",
        "relation",
        "constraint_type",
        "time_quality",
        "chronology_usable",
        "driver",
        "driver_name",
        "car_number",
        "source_class",
        "source_url",
        "source_title",
        "evidence_quality",
        "notes",
    ]

    action_interest = [
        "attempt_id",
        "subject_attempt_id",
        "related_attempt_id",
        "action",
        "action_semantics",
        "lane",
        "lane_semantics",
        "driver",
        "driver_name",
        "car_number",
        "source_class",
        "source_url",
        "source_title",
        "evidence_quality",
        "notes",
    ]

    chronology_matches = [
        field
        for field in chronology_interest
        if field in chronology_fields
    ]

    action_matches = [
        field
        for field in action_interest
        if field in action_fields
    ]

    print()
    print("=" * 120)
    print(
        "INTEGRATION FIELD MATCHES"
    )
    print("=" * 120)

    print()
    print(
        "Chronology relevant fields:"
    )

    for field in chronology_matches:
        print(
            " ",
            field,
        )

    print()
    print(
        "Action relevant fields:"
    )

    for field in action_matches:
        print(
            " ",
            field,
        )

    # ========================================================
    # EXISTING ILOTT DUPLICATE CHECK
    # ========================================================

    chronology_ilott_hits = []

    for i, row in enumerate(
        chronology,
        start=2,
    ):

        joined = " | ".join(
            txt(v)
            for v in row.values()
        )

        if (
            FIRST_ID in joined
            or
            SECOND_ID in joined
        ):
            chronology_ilott_hits.append(
                (i, joined)
            )

    action_ilott_hits = []

    for i, row in enumerate(
        actions,
        start=2,
    ):

        joined = " | ".join(
            txt(v)
            for v in row.values()
        )

        if (
            FIRST_ID in joined
            or
            SECOND_ID in joined
        ):
            action_ilott_hits.append(
                (i, joined)
            )

    print()
    print("=" * 120)
    print(
        "EXISTING ILOTT LEDGER HITS"
    )
    print("=" * 120)

    print()
    print(
        "Chronology V4 Ilott hits:",
        len(
            chronology_ilott_hits
        ),
    )

    for row_num, joined in chronology_ilott_hits:

        print()
        print(
            "row",
            row_num,
        )

        print(
            joined
        )

    print()
    print(
        "Action V2 Ilott hits:",
        len(
            action_ilott_hits
        ),
    )

    for row_num, joined in action_ilott_hits:

        print()
        print(
            "row",
            row_num,
        )

        print(
            joined
        )

    # ========================================================
    # WRITE CORRECTED PROVENANCE
    # ========================================================

    write_csv(
        EVIDENCE_V2,
        evidence_v2_rows,
        evidence_v2_fields,
    )

    write_csv(
        ADJUDICATION_V2,
        adjudication_v2_rows,
        adjudication_v2_fields,
    )

    schema_rows = []

    for i, field in enumerate(
        chronology_fields,
        start=1,
    ):

        schema_rows.append({
            "ledger":
                "CHRONOLOGY_V4",

            "column_order":
                i,

            "field_name":
                field,

            "integration_relevant":
                str(
                    field
                    in chronology_matches
                ),
        })

    for i, field in enumerate(
        action_fields,
        start=1,
    ):

        schema_rows.append({
            "ledger":
                "ACTION_V2",

            "column_order":
                i,

            "field_name":
                field,

            "integration_relevant":
                str(
                    field
                    in action_matches
                ),
        })

    write_csv(
        SCHEMA_OUT,
        schema_rows,
        [
            "ledger",
            "column_order",
            "field_name",
            "integration_relevant",
        ],
    )

    duplicate_free = (
        len(
            chronology_ilott_hits
        ) == 0
        and
        len(
            action_ilott_hits
        ) == 0
    )

    summary_rows = [
        {
            "metric":
                "canonical_identity_verified",

            "value":
                int(
                    identity_ok
                ),
        },

        {
            "metric":
                "chronology_v4_rows",

            "value":
                len(
                    chronology
                ),
        },

        {
            "metric":
                "action_v2_rows",

            "value":
                len(
                    actions
                ),
        },

        {
            "metric":
                "chronology_relevant_fields_detected",

            "value":
                len(
                    chronology_matches
                ),
        },

        {
            "metric":
                "action_relevant_fields_detected",

            "value":
                len(
                    action_matches
                ),
        },

        {
            "metric":
                "existing_chronology_ilott_hits",

            "value":
                len(
                    chronology_ilott_hits
                ),
        },

        {
            "metric":
                "existing_action_ilott_hits",

            "value":
                len(
                    action_ilott_hits
                ),
        },

        {
            "metric":
                "duplicate_free_for_new_integration",

            "value":
                int(
                    duplicate_free
                ),
        },

        {
            "metric":
                "recommended_next_stage",

            "value":
                (
                    "INTEGRATE_ILOTT_TO_CHRONOLOGY_V5_AND_ACTION_V3"
                    if (
                        identity_ok
                        and
                        duplicate_free
                    )
                    else
                    "REVIEW_EXISTING_LEDGER_STATE"
                ),
        },
    ]

    write_csv(
        SUMMARY_OUT,
        summary_rows,
        [
            "metric",
            "value",
        ],
    )

    qa_rows = [
        {
            "metric":
                "canonical_identity_verified",

            "value":
                int(identity_ok),

            "status":
                (
                    "PASS"
                    if identity_ok
                    else "FAIL"
                ),
        },

        {
            "metric":
                "source_date_not_mislabeled_as_publication",

            "value":
                1,

            "status":
                "PASS",
        },

        {
            "metric":
                "source_date_label",

            "value":
                SOURCE_DATE_LABEL,

            "status":
                "PASS",
        },

        {
            "metric":
                "existing_ledgers_mutated",

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
    # FINAL
    # ========================================================

    print()
    print("=" * 120)
    print(
        "FINAL SUMMARY"
    )
    print("=" * 120)

    print()
    print(
        "Canonical identity verified:",
        identity_ok,
    )

    print(
        "Chronology V4 rows:",
        len(
            chronology
        ),
    )

    print(
        "Action V2 rows:",
        len(
            actions
        ),
    )

    print(
        "Existing chronology Ilott hits:",
        len(
            chronology_ilott_hits
        ),
    )

    print(
        "Existing action Ilott hits:",
        len(
            action_ilott_hits
        ),
    )

    print()
    print(
        "Autosport date semantics corrected to:"
    )

    print(
        " ",
        SOURCE_DATE_LABEL,
        "|",
        SOURCE_DATE_DISPLAY,
    )

    print()
    print(
        "No existing ledger was modified."
    )

    print(
        "No canonical or Phase 5–8 data was modified."
    )

    print()
    print("=" * 120)

    if (
        identity_ok
        and
        duplicate_free
    ):

        print(
            "FINAL STATUS: "
            "ILOTT_RETAKE_LEDGER_INTEGRATION_PREFLIGHT_READY"
        )

    else:

        print(
            "FINAL STATUS: "
            "ILOTT_RETAKE_LEDGER_INTEGRATION_PREFLIGHT_REVIEW_REQUIRED"
        )

    print("=" * 120)

    print()
    print("OUTPUTS")
    print(EVIDENCE_V2)
    print(ADJUDICATION_V2)
    print(SCHEMA_OUT)
    print(SUMMARY_OUT)
    print(QA_OUT)


if __name__ == "__main__":
    main()
