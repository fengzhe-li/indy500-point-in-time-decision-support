from pathlib import Path
import csv
import re


# ============================================================
# PHASE
# ============================================================

PHASE = "R1G.25I"


# ============================================================
# PATHS
# ============================================================

SCRIPT_ROOT = Path(
    "weather/scripts"
)

OUTPUT_DIR = Path(
    "weather/output"
)

V1_NAME = (
    "chronology_rescue_2022_result_to_canonical_attempt_matches_v1.csv"
)

V2_NAME = (
    "chronology_rescue_2022_result_to_canonical_attempt_matches_v2.csv"
)

V3_NAME = (
    "chronology_rescue_2022_result_to_canonical_attempt_matches_v3.csv"
)


# ============================================================
# OUTPUTS
# ============================================================

DEPENDENCY_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_result_match_v3_dependency_audit_v1.csv"
)

SWITCH_LIST_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_result_match_v3_active_switch_candidates_v1.csv"
)

SUMMARY_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_result_match_v3_dependency_summary_v1.csv"
)

QA_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_result_match_v3_dependency_audit_v1_qa.csv"
)


# ============================================================
# HELPERS
# ============================================================

def txt(v):
    return "" if v is None else str(v).strip()


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


def safe_read(path):
    try:
        return path.read_text(
            encoding="utf-8",
            errors="replace",
        )
    except Exception:
        return ""


def line_numbers_for_token(text, token):
    lines = []

    for i, line in enumerate(
        text.splitlines(),
        start=1,
    ):

        if token in line:
            lines.append(i)

    return lines


def classify_script(path, source, refs):
    """
    Conservative classification.

    We preserve historical provenance scripts.

    Only scripts that appear to be ongoing rescue/integration
    consumers of V2 are candidates to switch to V3.
    """

    name = path.name.lower()

    # --------------------------------------------------------
    # Scripts created specifically to diagnose / repair V1/V2
    # must continue referencing old versions.
    # --------------------------------------------------------

    audit_preserve_tokens = [
        "forensic",
        "schema",
        "repair_2022_result_match_car_number",
        "result_match_v3_adoption",
        "global_car_number",
        "castroneves_car06",
    ]

    if any(
        token in name
        for token in audit_preserve_tokens
    ):

        return (
            "AUDIT_SCRIPT_PRESERVE",
            (
                "Script intentionally compares or audits legacy "
                "result-match versions; do not rewrite provenance."
            ),
        )

    # --------------------------------------------------------
    # Original reconciliation / construction scripts
    # --------------------------------------------------------

    construction_tokens = [
        "reconcile_2022_results_to_canonical",
        "resolve_2022_chronology_only",
        "parse_official_day1",
    ]

    if any(
        token in name
        for token in construction_tokens
    ):

        return (
            "LEGACY_PRESERVE",
            (
                "Historical construction/reconciliation stage. "
                "Preserve original dependency for reproducibility."
            ),
        )

    # --------------------------------------------------------
    # Earlier completed rescue stages should not be silently
    # rewritten after the fact.
    # --------------------------------------------------------

    legacy_tokens = [
        "build_2022_targeted",
        "mine_2022_official",
        "adjudicate_2022_secondary",
        "derive_2022_attempt_intervals",
        "promote_2022_mclaughlin",
        "audit_2022_chronology_coverage",
        "audit_2022_chronology_action_coverage",
        "audit_2022_editorial",
        "audit_2022_unresolved",
    ]

    if any(
        token in name
        for token in legacy_tokens
    ):

        return (
            "LEGACY_PRESERVE",
            (
                "Completed historical rescue stage. "
                "Keep its original V2-era provenance."
            ),
        )

    # --------------------------------------------------------
    # Current / future rescue consumers:
    #
    # If these reference V2, future reuse should switch to V3.
    # --------------------------------------------------------

    active_tokens = [
        "castroneves",
        "karam",
        "action",
        "chronology",
        "rescue",
        "coverage",
        "priority",
        "integrate",
        "adjudicate",
    ]

    if (
        V2_NAME in refs
        and
        any(
            token in name
            for token in active_tokens
        )
    ):

        return (
            "ACTIVE_RESCUE_SWITCH_TO_V3",
            (
                "Future execution should consume repaired V3. "
                "Do not alter historical outputs already produced."
            ),
        )

    if V3_NAME in refs:

        return (
            "V3_ALREADY_USED",
            "Script already references repaired V3.",
        )

    return (
        "REVIEW",
        (
            "Dependency found but role is not safely classified "
            "by conservative rules."
        ),
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
        "R1G.25I — 2022 RESULT-MATCH "
        "V2 DEPENDENCY / V3 ADOPTION AUDIT V1"
    )
    print("=" * 120)

    print()
    print("INPUT CHECK")
    print("-" * 120)

    print(
        f"{SCRIPT_ROOT}: "
        f"{'PRESENT' if SCRIPT_ROOT.exists() else 'MISSING'}"
    )

    v3_path = (
        OUTPUT_DIR
        / V3_NAME
    )

    print(
        f"{v3_path}: "
        f"{'PRESENT' if v3_path.exists() else 'MISSING'}"
    )

    if (
        not SCRIPT_ROOT.exists()
        or
        not v3_path.exists()
    ):

        print()
        print(
            "FINAL STATUS: "
            "RESULT_MATCH_V3_DEPENDENCY_AUDIT_INPUT_MISSING"
        )

        return

    scripts = sorted(
        SCRIPT_ROOT.rglob(
            "*.py"
        )
    )

    dependency_rows = []

    # ========================================================
    # SCAN
    # ========================================================

    for path in scripts:

        source = safe_read(
            path
        )

        if not source:
            continue

        refs = []

        for version, filename in [
            ("V1", V1_NAME),
            ("V2", V2_NAME),
            ("V3", V3_NAME),
        ]:

            if filename in source:

                refs.append(
                    filename
                )

                lines = line_numbers_for_token(
                    source,
                    filename,
                )

                dependency_rows.append({
                    "script_path":
                        str(path),

                    "script_name":
                        path.name,

                    "referenced_version":
                        version,

                    "referenced_filename":
                        filename,

                    "line_numbers":
                        "|".join(
                            str(x)
                            for x in lines
                        ),

                    "classification":
                        "",

                    "recommended_action":
                        "",

                    "notes":
                        "",
                })

        if not refs:
            continue

        classification, notes = (
            classify_script(
                path,
                source,
                refs,
            )
        )

        for row in dependency_rows:

            if (
                row[
                    "script_path"
                ]
                ==
                str(path)
                and
                not row[
                    "classification"
                ]
            ):

                row[
                    "classification"
                ] = classification

                if (
                    classification
                    ==
                    "ACTIVE_RESCUE_SWITCH_TO_V3"
                ):

                    row[
                        "recommended_action"
                    ] = (
                        "SWITCH_FUTURE_EXECUTION_TO_V3"
                    )

                elif classification in {
                    "LEGACY_PRESERVE",
                    "AUDIT_SCRIPT_PRESERVE",
                }:

                    row[
                        "recommended_action"
                    ] = (
                        "PRESERVE_EXISTING_REFERENCE"
                    )

                elif classification == "V3_ALREADY_USED":

                    row[
                        "recommended_action"
                    ] = "NONE"

                else:

                    row[
                        "recommended_action"
                    ] = "MANUAL_REVIEW"

                row[
                    "notes"
                ] = notes

    # ========================================================
    # PRINT
    # ========================================================

    print()
    print("=" * 120)
    print(
        "DEPENDENCY INVENTORY"
    )
    print("=" * 120)

    print()
    print(
        "Python scripts scanned:",
        len(
            scripts
        ),
    )

    scripts_with_refs = sorted(
        {
            row[
                "script_path"
            ]
            for row in dependency_rows
        }
    )

    print(
        "Scripts referencing V1/V2/V3:",
        len(
            scripts_with_refs
        ),
    )

    for script in scripts_with_refs:

        rows = [
            row
            for row in dependency_rows
            if row[
                "script_path"
            ] == script
        ]

        print()
        print(script)

        print(
            "  refs:",
            "|".join(
                sorted(
                    {
                        row[
                            "referenced_version"
                        ]
                        for row in rows
                    }
                )
            ),
        )

        print(
            "  classification:",
            rows[0][
                "classification"
            ],
        )

        print(
            "  action:",
            rows[0][
                "recommended_action"
            ],
        )

    # ========================================================
    # SWITCH LIST
    # ========================================================

    switch_scripts = sorted(
        {
            row[
                "script_path"
            ]
            for row in dependency_rows
            if row[
                "classification"
            ]
            ==
            "ACTIVE_RESCUE_SWITCH_TO_V3"
            and
            row[
                "referenced_version"
            ]
            ==
            "V2"
        }
    )

    switch_rows = []

    for script in switch_scripts:

        rows = [
            row
            for row in dependency_rows
            if row[
                "script_path"
            ] == script
        ]

        switch_rows.append({
            "script_path":
                script,

            "current_reference":
                V2_NAME,

            "future_reference":
                V3_NAME,

            "policy":
                "FUTURE_EXECUTION_ONLY",

            "historical_outputs_rebuild_required":
                "False",

            "notes":
                (
                    "Switch only before future reuse. "
                    "Do not regenerate already accepted historical "
                    "outputs solely for this literal-format repair."
                ),
        })

    print()
    print("=" * 120)
    print(
        "ACTIVE V3 SWITCH CANDIDATES"
    )
    print("=" * 120)

    print()
    print(
        "Switch candidates:",
        len(
            switch_rows
        ),
    )

    for row in switch_rows:

        print()
        print(
            row[
                "script_path"
            ]
        )

        print(
            "  V2 -> V3"
        )

        print(
            "  historical rebuild:",
            row[
                "historical_outputs_rebuild_required"
            ],
        )

    # ========================================================
    # COUNTS
    # ========================================================

    class_counts = {}

    for script in scripts_with_refs:

        rows = [
            row
            for row in dependency_rows
            if row[
                "script_path"
            ] == script
        ]

        classification = (
            rows[0][
                "classification"
            ]
        )

        class_counts[
            classification
        ] = (
            class_counts.get(
                classification,
                0,
            )
            + 1
        )

    v1_ref_scripts = {
        row[
            "script_path"
        ]
        for row in dependency_rows
        if row[
            "referenced_version"
        ] == "V1"
    }

    v2_ref_scripts = {
        row[
            "script_path"
        ]
        for row in dependency_rows
        if row[
            "referenced_version"
        ] == "V2"
    }

    v3_ref_scripts = {
        row[
            "script_path"
        ]
        for row in dependency_rows
        if row[
            "referenced_version"
        ] == "V3"
    }

    # ========================================================
    # WRITE
    # ========================================================

    write_csv(
        DEPENDENCY_OUT,
        dependency_rows,
        [
            "script_path",
            "script_name",
            "referenced_version",
            "referenced_filename",
            "line_numbers",
            "classification",
            "recommended_action",
            "notes",
        ],
    )

    write_csv(
        SWITCH_LIST_OUT,
        switch_rows,
        [
            "script_path",
            "current_reference",
            "future_reference",
            "policy",
            "historical_outputs_rebuild_required",
            "notes",
        ],
    )

    summary_rows = [
        {
            "metric":
                "scripts_scanned",

            "value":
                len(
                    scripts
                ),
        },

        {
            "metric":
                "scripts_with_result_match_refs",

            "value":
                len(
                    scripts_with_refs
                ),
        },

        {
            "metric":
                "v1_reference_scripts",

            "value":
                len(
                    v1_ref_scripts
                ),
        },

        {
            "metric":
                "v2_reference_scripts",

            "value":
                len(
                    v2_ref_scripts
                ),
        },

        {
            "metric":
                "v3_reference_scripts",

            "value":
                len(
                    v3_ref_scripts
                ),
        },

        {
            "metric":
                "active_switch_candidates",

            "value":
                len(
                    switch_rows
                ),
        },
    ]

    for key, value in sorted(
        class_counts.items()
    ):

        summary_rows.append({
            "metric":
                (
                    "classification_"
                    + key.lower()
                ),

            "value":
                value,
        })

    write_csv(
        SUMMARY_OUT,
        summary_rows,
        [
            "metric",
            "value",
        ],
    )

    # ========================================================
    # QA
    # ========================================================

    qa_rows = [
        {
            "metric":
                "v3_exists",

            "value":
                int(
                    v3_path.exists()
                ),

            "status":
                (
                    "PASS"
                    if v3_path.exists()
                    else "FAIL"
                ),
        },

        {
            "metric":
                "scripts_scanned",

            "value":
                len(
                    scripts
                ),

            "status":
                (
                    "PASS"
                    if scripts
                    else "FAIL"
                ),
        },

        {
            "metric":
                "source_scripts_modified",

            "value":
                0,

            "status":
                "PASS",
        },

        {
            "metric":
                "historical_outputs_regenerated",

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
        "V1-reference scripts:",
        len(
            v1_ref_scripts
        ),
    )

    print(
        "V2-reference scripts:",
        len(
            v2_ref_scripts
        ),
    )

    print(
        "V3-reference scripts:",
        len(
            v3_ref_scripts
        ),
    )

    print(
        "Active future-switch candidates:",
        len(
            switch_rows
        ),
    )

    print()
    print(
        "Policy:"
    )

    print(
        "  Preserve historical V1/V2 references "
        "for reproducibility."
    )

    print(
        "  Switch only future active rescue execution "
        "to repaired V3."
    )

    print(
        "  Do not regenerate Phase 5–8."
    )

    print()
    print(
        "No source script was modified."
    )

    print(
        "No historical output was regenerated."
    )

    print(
        "No canonical data was modified."
    )

    print()
    print("=" * 120)
    print(
        "FINAL STATUS: "
        "RESULT_MATCH_V3_ADOPTION_DEPENDENCY_AUDIT_COMPLETE"
    )
    print("=" * 120)

    print()
    print("OUTPUTS")
    print(DEPENDENCY_OUT)
    print(SWITCH_LIST_OUT)
    print(SUMMARY_OUT)
    print(QA_OUT)


if __name__ == "__main__":
    main()
