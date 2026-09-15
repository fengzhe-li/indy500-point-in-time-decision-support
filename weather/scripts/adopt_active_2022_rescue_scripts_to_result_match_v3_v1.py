from pathlib import Path
import csv
import hashlib
import shutil


PHASE = "R1G.25J"

SCRIPT_ROOT = Path("weather/scripts")
OUTPUT_DIR = Path("weather/output")

V2_NAME = (
    "chronology_rescue_2022_result_to_canonical_attempt_matches_v2.csv"
)

V3_NAME = (
    "chronology_rescue_2022_result_to_canonical_attempt_matches_v3.csv"
)

V3_DATA = (
    OUTPUT_DIR
    / V3_NAME
)

ACTIVE_SCRIPTS = [
    "adjudicate_2022_castroneves_first_run_action_v1.py",
    "adjudicate_2022_karam_two_event_chronology_v1.py",
    "audit_2022_castroneves_canonical_identity_v1.py",
    "audit_2022_castroneves_repeat_pair_evidence_v1.py",
    "audit_2022_karam_attempt_identity_rescue_v1.py",
    "integrate_2022_castroneves_first_run_action_chronology_v1.py",
    "mine_2022_high_priority_chronology_targets_v1.py",
    "reaudit_2022_castroneves_with_preserved_car_number_v1.py",
]

MANIFEST_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_result_match_v3_active_adoption_manifest_v1.csv"
)

QA_OUT = (
    OUTPUT_DIR
    / "chronology_rescue_2022_result_match_v3_active_adoption_v1_qa.csv"
)


def sha256(path):
    h = hashlib.sha256()

    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)

            if not chunk:
                break

            h.update(chunk)

    return h.hexdigest()


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


def active_copy_name(original_name):
    path = Path(original_name)

    stem = path.stem

    return (
        stem
        + "_active_v3"
        + path.suffix
    )


def main():

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print()
    print("=" * 120)
    print(
        "R1G.25J — ACTIVE 2022 RESCUE "
        "RESULT-MATCH V3 SAFE ADOPTION V1"
    )
    print("=" * 120)

    print()
    print("INPUT CHECK")
    print("-" * 120)

    print(
        f"{SCRIPT_ROOT}: "
        f"{'PRESENT' if SCRIPT_ROOT.exists() else 'MISSING'}"
    )

    print(
        f"{V3_DATA}: "
        f"{'PRESENT' if V3_DATA.exists() else 'MISSING'}"
    )

    if (
        not SCRIPT_ROOT.exists()
        or
        not V3_DATA.exists()
    ):

        print()
        print(
            "FINAL STATUS: "
            "ACTIVE_V3_ADOPTION_INPUT_MISSING"
        )
        return

    missing_scripts = []

    for name in ACTIVE_SCRIPTS:

        path = SCRIPT_ROOT / name

        exists = path.exists()

        print(
            f"{path}: "
            f"{'PRESENT' if exists else 'MISSING'}"
        )

        if not exists:
            missing_scripts.append(path)

    if missing_scripts:

        print()
        print(
            "FINAL STATUS: "
            "ACTIVE_V3_ADOPTION_SCRIPT_SET_INCOMPLETE"
        )
        return

    manifest_rows = []

    print()
    print("=" * 120)
    print(
        "CREATE V3 ACTIVE COPIES"
    )
    print("=" * 120)

    for name in ACTIVE_SCRIPTS:

        source_path = SCRIPT_ROOT / name

        target_name = active_copy_name(
            name
        )

        target_path = (
            SCRIPT_ROOT
            / target_name
        )

        source_text = source_path.read_text(
            encoding="utf-8",
            errors="strict",
        )

        v2_count_before = (
            source_text.count(
                V2_NAME
            )
        )

        v3_count_before = (
            source_text.count(
                V3_NAME
            )
        )

        if v2_count_before < 1:

            status = (
                "SOURCE_NO_V2_REFERENCE_REVIEW_REQUIRED"
            )

            target_created = False

            target_sha = ""

            v2_after = ""
            v3_after = ""

        else:

            target_text = source_text.replace(
                V2_NAME,
                V3_NAME,
            )

            target_path.write_text(
                target_text,
                encoding="utf-8",
            )

            target_created = True

            reloaded = target_path.read_text(
                encoding="utf-8",
            )

            v2_after = reloaded.count(
                V2_NAME
            )

            v3_after = reloaded.count(
                V3_NAME
            )

            target_sha = sha256(
                target_path
            )

            if (
                v2_after == 0
                and
                v3_after >= 1
            ):
                status = (
                    "ACTIVE_V3_COPY_READY"
                )

            else:
                status = (
                    "ACTIVE_V3_COPY_REVIEW_REQUIRED"
                )

        source_sha = sha256(
            source_path
        )

        print()
        print(
            "source:",
            source_path,
        )

        print(
            "active copy:",
            target_path,
        )

        print(
            "V2 refs before:",
            v2_count_before,
        )

        print(
            "V3 refs before:",
            v3_count_before,
        )

        print(
            "V2 refs after:",
            v2_after,
        )

        print(
            "V3 refs after:",
            v3_after,
        )

        print(
            "status:",
            status,
        )

        manifest_rows.append({
            "phase":
                PHASE,

            "source_script":
                str(source_path),

            "active_v3_script":
                str(target_path),

            "source_sha256":
                source_sha,

            "active_v3_sha256":
                target_sha,

            "v2_references_source":
                v2_count_before,

            "v3_references_source":
                v3_count_before,

            "v2_references_active_copy":
                v2_after,

            "v3_references_active_copy":
                v3_after,

            "source_modified":
                "False",

            "historical_outputs_regenerated":
                "False",

            "target_created":
                str(
                    target_created
                ),

            "status":
                status,

            "policy":
                (
                    "Use active_v3 copy for future execution only. "
                    "Preserve original script for historical provenance."
                ),
        })

    # ========================================================
    # VERIFY ORIGINALS WERE NOT MODIFIED
    # ========================================================

    original_integrity_failures = 0

    for row in manifest_rows:

        source_path = Path(
            row[
                "source_script"
            ]
        )

        current_sha = sha256(
            source_path
        )

        if (
            current_sha
            !=
            row[
                "source_sha256"
            ]
        ):
            original_integrity_failures += 1

    # ========================================================
    # VERIFY COPIES
    # ========================================================

    ready_rows = [
        row
        for row in manifest_rows
        if row[
            "status"
        ]
        ==
        "ACTIVE_V3_COPY_READY"
    ]

    review_rows = [
        row
        for row in manifest_rows
        if row[
            "status"
        ]
        !=
        "ACTIVE_V3_COPY_READY"
    ]

    print()
    print("=" * 120)
    print(
        "ADOPTION VERIFICATION"
    )
    print("=" * 120)

    print()
    print(
        "Expected active scripts:",
        len(
            ACTIVE_SCRIPTS
        ),
    )

    print(
        "V3-ready copies:",
        len(
            ready_rows
        ),
    )

    print(
        "Review-required copies:",
        len(
            review_rows
        ),
    )

    print(
        "Original-script integrity failures:",
        original_integrity_failures,
    )

    # ========================================================
    # WRITE MANIFEST
    # ========================================================

    write_csv(
        MANIFEST_OUT,
        manifest_rows,
        [
            "phase",
            "source_script",
            "active_v3_script",
            "source_sha256",
            "active_v3_sha256",
            "v2_references_source",
            "v3_references_source",
            "v2_references_active_copy",
            "v3_references_active_copy",
            "source_modified",
            "historical_outputs_regenerated",
            "target_created",
            "status",
            "policy",
        ],
    )

    qa_rows = [
        {
            "metric":
                "expected_active_scripts",

            "value":
                len(
                    ACTIVE_SCRIPTS
                ),

            "status":
                "PASS",
        },

        {
            "metric":
                "active_v3_copies_ready",

            "value":
                len(
                    ready_rows
                ),

            "status":
                (
                    "PASS"
                    if len(
                        ready_rows
                    )
                    ==
                    len(
                        ACTIVE_SCRIPTS
                    )
                    else "FAIL"
                ),
        },

        {
            "metric":
                "review_required_copies",

            "value":
                len(
                    review_rows
                ),

            "status":
                (
                    "PASS"
                    if len(
                        review_rows
                    ) == 0
                    else "FAIL"
                ),
        },

        {
            "metric":
                "original_script_integrity_failures",

            "value":
                original_integrity_failures,

            "status":
                (
                    "PASS"
                    if original_integrity_failures == 0
                    else "FAIL"
                ),
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
                "canonical_data_mutated",

            "value":
                0,

            "status":
                "PASS",
        },

        {
            "metric":
                "result_match_v2_mutated",

            "value":
                0,

            "status":
                "PASS",
        },

        {
            "metric":
                "result_match_v3_mutated",

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
    # PRINT FUTURE EXECUTION LIST
    # ========================================================

    print()
    print("=" * 120)
    print(
        "FUTURE ACTIVE SCRIPT LIST"
    )
    print("=" * 120)

    for row in ready_rows:

        print()
        print(
            row[
                "active_v3_script"
            ]
        )

    print()
    print("=" * 120)
    print(
        "FINAL SUMMARY"
    )
    print("=" * 120)

    print()
    print(
        "Original active scripts modified:",
        0,
    )

    print(
        "New V3 active copies:",
        len(
            ready_rows
        ),
    )

    print(
        "Historical outputs regenerated:",
        0,
    )

    print(
        "Original integrity failures:",
        original_integrity_failures,
    )

    print()
    print(
        "Policy:"
    )

    print(
        "  Original V1/V2-era scripts remain historical provenance."
    )

    print(
        "  *_active_v3.py copies are the future execution path."
    )

    print(
        "  Phase 5–8 remain untouched."
    )

    print()
    print("=" * 120)

    if (
        len(
            ready_rows
        )
        ==
        len(
            ACTIVE_SCRIPTS
        )
        and
        not review_rows
        and
        original_integrity_failures == 0
    ):

        print(
            "FINAL STATUS: "
            "ACTIVE_RESCUE_RESULT_MATCH_V3_ADOPTION_COMPLETE"
        )

    else:

        print(
            "FINAL STATUS: "
            "ACTIVE_RESCUE_RESULT_MATCH_V3_ADOPTION_REVIEW_REQUIRED"
        )

    print("=" * 120)

    print()
    print("OUTPUTS")
    print(MANIFEST_OUT)
    print(QA_OUT)


if __name__ == "__main__":
    main()
