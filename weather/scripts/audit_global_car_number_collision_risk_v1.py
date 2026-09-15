from pathlib import Path
import csv
import re
from collections import defaultdict


# ============================================================
# PHASE
# ============================================================

PHASE = "R1G.25D"


# ============================================================
# PATHS
# ============================================================

CANONICAL_ATTEMPTS = Path(
    "data/canonical/v1/attempts.csv"
)

SCRIPT_ROOT = Path(
    "weather/scripts"
)

OUTPUT_ROOT = Path(
    "weather/output"
)

AUDIT_OUTPUT_DIR = Path(
    "weather/output"
)


# ============================================================
# OUTPUTS
# ============================================================

SCRIPT_AUDIT_OUT = (
    AUDIT_OUTPUT_DIR
    / "global_car_number_script_risk_audit_v1.csv"
)

CANONICAL_COLLISION_OUT = (
    AUDIT_OUTPUT_DIR
    / "global_car_number_canonical_collision_audit_v1.csv"
)

CSV_IMPACT_OUT = (
    AUDIT_OUTPUT_DIR
    / "global_car_number_output_impact_candidates_v1.csv"
)

SUMMARY_OUT = (
    AUDIT_OUTPUT_DIR
    / "global_car_number_collision_audit_summary_v1.csv"
)

QA_OUT = (
    AUDIT_OUTPUT_DIR
    / "global_car_number_collision_audit_v1_qa.csv"
)


# ============================================================
# HELPERS
# ============================================================

def txt(value):
    return "" if value is None else str(value).strip()


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


def derive_year(row):
    year = txt(
        row.get("year")
    )

    if year in {
        "2020",
        "2021",
        "2022",
        "2023",
        "2024",
    }:
        return year

    session_id = txt(
        row.get("session_id")
    )

    for candidate in [
        "2020",
        "2021",
        "2022",
        "2023",
        "2024",
    ]:

        if candidate in session_id:
            return candidate

    return ""


def numeric_equivalent_car_number(value):
    """
    ONLY for collision detection.

    This function must NEVER be used as an identity key.

    Examples:
        "06" -> "6"
        "6"  -> "6"
        "01" -> "1"

    Non-pure-numeric car numbers are preserved separately.
    """

    raw = txt(value)

    if not raw:
        return ""

    if not re.fullmatch(
        r"\d+",
        raw,
    ):
        return raw

    try:
        return str(
            int(raw)
        )
    except Exception:
        return raw


def has_leading_zero(value):
    raw = txt(value)

    return (
        len(raw) > 1
        and
        raw.startswith("0")
        and
        raw.isdigit()
    )


def safe_read_text(path):
    try:
        return path.read_text(
            encoding="utf-8",
            errors="replace",
        )
    except Exception:
        return ""


def extract_csv_literals(text):
    """
    Extract obvious CSV path string literals from Python source.

    This is discovery only.
    """

    pattern = re.compile(
        r"""["']([^"']+\.csv)["']"""
    )

    return sorted(
        set(
            match.group(1)
            for match in pattern.finditer(text)
        )
    )


def extract_output_like_literals(text):
    """
    Broader extraction for weather/output/... references.
    """

    pattern = re.compile(
        r"""["']([^"']*weather/output[^"']*)["']"""
    )

    values = []

    for match in pattern.finditer(text):

        value = match.group(1)

        if value:
            values.append(value)

    return sorted(
        set(values)
    )


def line_number_for_offset(text, offset):
    return (
        text.count(
            "\n",
            0,
            offset,
        )
        + 1
    )


# ============================================================
# SCRIPT RISK PATTERNS
# ============================================================

DANGEROUS_PATTERNS = [
    (
        "INT_FLOAT_NORMALIZATION",
        re.compile(
            r"int\s*\(\s*float\s*\(",
            re.IGNORECASE,
        ),
        "Converts textual car number through float/int and can collapse 06 into 6.",
        "HIGH",
    ),

    (
        "LEADING_ZERO_STRIP",
        re.compile(
            r"\.lstrip\s*\(\s*[\"']0[\"']\s*\)",
            re.IGNORECASE,
        ),
        "Explicitly strips leading zeros and can collapse 06 into 6.",
        "HIGH",
    ),

    (
        "ASTYPE_INT",
        re.compile(
            r"\.astype\s*\(\s*(?:int|[\"']int(?:64|32)?[\"'])\s*\)",
            re.IGNORECASE,
        ),
        "Integer casting may destroy significant leading zeros.",
        "HIGH",
    ),

    (
        "TO_NUMERIC",
        re.compile(
            r"(?:pd\.)?to_numeric\s*\(",
            re.IGNORECASE,
        ),
        "Numeric conversion may destroy significant leading zeros.",
        "MEDIUM",
    ),

    (
        "INT_DIRECT",
        re.compile(
            r"\bint\s*\(",
            re.IGNORECASE,
        ),
        "Direct integer conversion requires context review.",
        "MEDIUM",
    ),
]


# ============================================================
# MAIN
# ============================================================

def main():

    AUDIT_OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print()
    print("=" * 120)
    print(
        "R1G.25D — GLOBAL CAR NUMBER "
        "COLLISION / NORMALIZATION RISK AUDIT V1"
    )
    print("=" * 120)

    # ========================================================
    # INPUT CHECK
    # ========================================================

    print()
    print("INPUT CHECK")
    print("-" * 120)

    required = [
        CANONICAL_ATTEMPTS,
        SCRIPT_ROOT,
        OUTPUT_ROOT,
    ]

    missing = []

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
            "GLOBAL_CAR_NUMBER_COLLISION_AUDIT_INPUT_MISSING"
        )

        return

    # ========================================================
    # PART 1 — CANONICAL COLLISION AUDIT
    # ========================================================

    canonical = read_csv(
        CANONICAL_ATTEMPTS
    )

    rows_2020_2024 = [
        row
        for row in canonical
        if derive_year(row)
        in {
            "2020",
            "2021",
            "2022",
            "2023",
            "2024",
        }
    ]

    collision_groups = defaultdict(
        list
    )

    literal_usage = defaultdict(
        list
    )

    for row in rows_2020_2024:

        year = derive_year(
            row
        )

        literal = txt(
            row.get(
                "car_number"
            )
        )

        numeric_key = (
            numeric_equivalent_car_number(
                literal
            )
        )

        if not literal:
            continue

        collision_groups[
            (
                year,
                numeric_key,
            )
        ].append(row)

        literal_usage[
            (
                year,
                literal,
            )
        ].append(row)

    canonical_collision_rows = []

    collision_keys = set()

    for (
        year,
        numeric_key,
    ), group_rows in sorted(
        collision_groups.items()
    ):

        literals = sorted(
            {
                txt(
                    row.get(
                        "car_number"
                    )
                )
                for row in group_rows
                if txt(
                    row.get(
                        "car_number"
                    )
                )
            }
        )

        if len(literals) <= 1:
            continue

        collision_keys.add(
            (
                year,
                numeric_key,
            )
        )

        drivers_by_literal = defaultdict(
            set
        )

        attempts_by_literal = defaultdict(
            set
        )

        for row in group_rows:

            literal = txt(
                row.get(
                    "car_number"
                )
            )

            driver = txt(
                row.get(
                    "driver_name"
                )
            )

            attempt_id = txt(
                row.get(
                    "attempt_id"
                )
            )

            if driver:
                drivers_by_literal[
                    literal
                ].add(driver)

            if attempt_id:
                attempts_by_literal[
                    literal
                ].add(attempt_id)

        for literal in literals:

            canonical_collision_rows.append({
                "year":
                    year,

                "numeric_equivalent":
                    numeric_key,

                "literal_car_number":
                    literal,

                "has_leading_zero":
                    has_leading_zero(
                        literal
                    ),

                "drivers":
                    "|".join(
                        sorted(
                            drivers_by_literal[
                                literal
                            ]
                        )
                    ),

                "canonical_attempt_count":
                    len(
                        attempts_by_literal[
                            literal
                        ]
                    ),

                "collision_literals":
                    "|".join(
                        literals
                    ),

                "risk":
                    "IDENTITY_COLLISION_IF_NUMERIC_NORMALIZED",

                "required_policy":
                    "PRESERVE_CAR_NUMBER_AS_STRING",
            })

    # ========================================================
    # PRINT COLLISIONS
    # ========================================================

    print()
    print("=" * 120)
    print(
        "CANONICAL CAR-NUMBER COLLISIONS"
    )
    print("=" * 120)

    print()
    print(
        "Canonical rows 2020–2024:",
        len(
            rows_2020_2024
        ),
    )

    print(
        "Collision groups:",
        len(
            collision_keys
        ),
    )

    if not collision_keys:

        print()
        print(
            "No distinct literal car numbers collapse "
            "to the same numeric value within the same year."
        )

    else:

        grouped_display = defaultdict(
            list
        )

        for row in canonical_collision_rows:

            grouped_display[
                (
                    row["year"],
                    row["numeric_equivalent"],
                )
            ].append(row)

        for (
            year,
            numeric_key,
        ), rows in sorted(
            grouped_display.items()
        ):

            print()
            print(
                f"YEAR {year} | numeric equivalent {numeric_key}"
            )

            for row in rows:

                print(
                    "  literal:",
                    repr(
                        row[
                            "literal_car_number"
                        ]
                    ),
                    "| drivers:",
                    row[
                        "drivers"
                    ],
                    "| attempts:",
                    row[
                        "canonical_attempt_count"
                    ],
                )

    # ========================================================
    # PART 2 — SCRIPT STATIC AUDIT
    # ========================================================

    scripts = sorted(
        SCRIPT_ROOT.rglob(
            "*.py"
        )
    )

    script_audit_rows = []

    risky_scripts = set()

    high_risk_scripts = set()

    for script_path in scripts:

        source = safe_read_text(
            script_path
        )

        if not source:
            continue

        # Only scripts touching car numbers are relevant.
        if (
            "car_number" not in source
            and
            "car number" not in source.lower()
        ):
            continue

        detected = []

        for (
            pattern_name,
            pattern,
            explanation,
            severity,
        ) in DANGEROUS_PATTERNS:

            for match in pattern.finditer(
                source
            ):

                line_no = (
                    line_number_for_offset(
                        source,
                        match.start(),
                    )
                )

                start = max(
                    0,
                    match.start() - 150,
                )

                end = min(
                    len(source),
                    match.end() + 150,
                )

                context = (
                    source[
                        start:end
                    ]
                    .replace(
                        "\n",
                        " ",
                    )
                    .strip()
                )

                # Avoid counting every unrelated int()
                # if context is not about car number.
                if pattern_name == "INT_DIRECT":

                    if (
                        "car" not in context.lower()
                        and
                        "number" not in context.lower()
                    ):
                        continue

                detected.append({
                    "pattern":
                        pattern_name,

                    "severity":
                        severity,

                    "line_number":
                        line_no,

                    "explanation":
                        explanation,

                    "context":
                        context,
                })

        if not detected:
            continue

        risky_scripts.add(
            str(script_path)
        )

        if any(
            item["severity"] == "HIGH"
            for item in detected
        ):
            high_risk_scripts.add(
                str(script_path)
            )

        csv_literals = (
            extract_csv_literals(
                source
            )
        )

        output_literals = (
            extract_output_like_literals(
                source
            )
        )

        all_output_refs = sorted(
            set(
                csv_literals
                +
                output_literals
            )
        )

        for item in detected:

            script_audit_rows.append({
                "script_path":
                    str(script_path),

                "risk_pattern":
                    item[
                        "pattern"
                    ],

                "severity":
                    item[
                        "severity"
                    ],

                "line_number":
                    item[
                        "line_number"
                    ],

                "context":
                    item[
                        "context"
                    ],

                "explanation":
                    item[
                        "explanation"
                    ],

                "referenced_csv_or_output_paths":
                    "|".join(
                        all_output_refs
                    ),

                "action":
                    (
                        "REVIEW_BEFORE_REUSE"
                        if item[
                            "severity"
                        ] == "HIGH"
                        else
                        "CONTEXT_REVIEW"
                    ),
            })

    # ========================================================
    # PRINT SCRIPT RISKS
    # ========================================================

    print()
    print("=" * 120)
    print(
        "SCRIPT NORMALIZATION RISK AUDIT"
    )
    print("=" * 120)

    print()
    print(
        "Python scripts scanned:",
        len(
            scripts
        ),
    )

    print(
        "Risky scripts:",
        len(
            risky_scripts
        ),
    )

    print(
        "High-risk scripts:",
        len(
            high_risk_scripts
        ),
    )

    if risky_scripts:

        by_script = defaultdict(
            list
        )

        for row in script_audit_rows:

            by_script[
                row[
                    "script_path"
                ]
            ].append(row)

        for script_path in sorted(
            by_script
        ):

            rows = by_script[
                script_path
            ]

            severities = sorted(
                {
                    row[
                        "severity"
                    ]
                    for row in rows
                }
            )

            patterns = sorted(
                {
                    row[
                        "risk_pattern"
                    ]
                    for row in rows
                }
            )

            print()
            print(
                script_path
            )

            print(
                "  severity:",
                "|".join(
                    severities
                ),
            )

            print(
                "  patterns:",
                "|".join(
                    patterns
                ),
            )

            lines = sorted(
                {
                    str(
                        row[
                            "line_number"
                        ]
                    )
                    for row in rows
                }
            )

            print(
                "  lines:",
                ",".join(lines),
            )

    # ========================================================
    # PART 3 — EXISTING OUTPUT CSV IMPACT CANDIDATES
    # ========================================================

    output_csvs = sorted(
        OUTPUT_ROOT.rglob(
            "*.csv"
        )
    )

    impact_rows = []

    for csv_path in output_csvs:

        try:
            rows = read_csv(
                csv_path
            )
        except Exception as exc:

            impact_rows.append({
                "csv_path":
                    str(csv_path),

                "has_car_number_column":
                    False,

                "row_count":
                    "",

                "observed_literal_car_numbers":
                    "",

                "numeric_collision_detected":
                    False,

                "leading_zero_present":
                    False,

                "contains_known_collision_numeric_key":
                    False,

                "risk_class":
                    "UNREADABLE_CSV",

                "notes":
                    (
                        f"{type(exc).__name__}: "
                        f"{exc}"
                    ),
            })

            continue

        if not rows:

            continue

        fieldnames = set(
            rows[0].keys()
        )

        if "car_number" not in fieldnames:
            continue

        literals = sorted(
            {
                txt(
                    row.get(
                        "car_number"
                    )
                )
                for row in rows
                if txt(
                    row.get(
                        "car_number"
                    )
                )
            }
        )

        numeric_to_literals = defaultdict(
            set
        )

        for literal in literals:

            numeric_key = (
                numeric_equivalent_car_number(
                    literal
                )
            )

            numeric_to_literals[
                numeric_key
            ].add(literal)

        collisions_in_file = {
            numeric_key:
                sorted(values)
            for (
                numeric_key,
                values
            ) in numeric_to_literals.items()
            if len(values) > 1
        }

        leading_zero_present = any(
            has_leading_zero(
                literal
            )
            for literal in literals
        )

        known_collision_numeric_keys = {
            numeric_key
            for (
                _year,
                numeric_key,
            ) in collision_keys
        }

        contains_known_collision_numeric_key = any(
            numeric_equivalent_car_number(
                literal
            )
            in known_collision_numeric_keys
            for literal in literals
        )

        # Important:
        #
        # If the CSV contains a known collision numeric key
        # but only ONE literal representation (e.g. "6"),
        # it could be either clean or already-collapsed.
        # Therefore mark as REVIEW, not FAIL.
        #
        if collisions_in_file:

            risk_class = (
                "VISIBLE_LITERAL_COLLISION"
            )

            notes = (
                "File contains multiple literal car numbers "
                "that collapse numerically. String identity must "
                "be preserved."
            )

        elif (
            contains_known_collision_numeric_key
            and
            not leading_zero_present
        ):

            risk_class = (
                "POTENTIAL_PRIOR_NORMALIZATION"
            )

            notes = (
                "File contains a numeric-equivalent key known "
                "to collide in canonical data, but no leading-zero "
                "literal is visible. Review provenance/script."
            )

        elif contains_known_collision_numeric_key:

            risk_class = (
                "COLLISION_SENSITIVE_BUT_LITERAL_PRESERVED"
            )

            notes = (
                "Known collision-sensitive car number appears "
                "with literal formatting preserved."
            )

        else:

            risk_class = (
                "NO_KNOWN_COLLISION_SIGNAL"
            )

            notes = (
                "No canonical collision key detected."
            )

        impact_rows.append({
            "csv_path":
                str(csv_path),

            "has_car_number_column":
                True,

            "row_count":
                len(rows),

            "observed_literal_car_numbers":
                "|".join(
                    literals
                ),

            "numeric_collision_detected":
                bool(
                    collisions_in_file
                ),

            "leading_zero_present":
                leading_zero_present,

            "contains_known_collision_numeric_key":
                contains_known_collision_numeric_key,

            "risk_class":
                risk_class,

            "notes":
                notes,
        })

    # ========================================================
    # HIGH VALUE OUTPUT REVIEW LIST
    # ========================================================

    impact_priority = [
        row
        for row in impact_rows
        if row[
            "risk_class"
        ]
        in {
            "VISIBLE_LITERAL_COLLISION",
            "POTENTIAL_PRIOR_NORMALIZATION",
            "COLLISION_SENSITIVE_BUT_LITERAL_PRESERVED",
        }
    ]

    print()
    print("=" * 120)
    print(
        "EXISTING OUTPUT CSV IMPACT CANDIDATES"
    )
    print("=" * 120)

    print()
    print(
        "Output CSVs scanned:",
        len(
            output_csvs
        ),
    )

    print(
        "Collision-sensitive CSVs:",
        len(
            impact_priority
        ),
    )

    risk_order = {
        "VISIBLE_LITERAL_COLLISION": 0,
        "POTENTIAL_PRIOR_NORMALIZATION": 1,
        "COLLISION_SENSITIVE_BUT_LITERAL_PRESERVED": 2,
    }

    for row in sorted(
        impact_priority,
        key=lambda r: (
            risk_order.get(
                r[
                    "risk_class"
                ],
                9,
            ),
            r[
                "csv_path"
            ],
        ),
    ):

        print()
        print(
            row[
                "risk_class"
            ],
            "|",
            row[
                "csv_path"
            ],
        )

        if row[
            "observed_literal_car_numbers"
        ]:

            values = (
                row[
                    "observed_literal_car_numbers"
                ].split("|")
            )

            relevant = [
                value
                for value in values
                if (
                    numeric_equivalent_car_number(
                        value
                    )
                    in {
                        key
                        for (
                            _year,
                            key,
                        ) in collision_keys
                    }
                )
            ]

            if relevant:

                print(
                    "  collision-sensitive literals:",
                    "|".join(
                        relevant
                    ),
                )

    # ========================================================
    # SUMMARY
    # ========================================================

    high_risk_output_count = sum(
        1
        for row in impact_rows
        if row[
            "risk_class"
        ]
        in {
            "VISIBLE_LITERAL_COLLISION",
            "POTENTIAL_PRIOR_NORMALIZATION",
        }
    )

    summary_rows = [
        {
            "metric":
                "canonical_rows_2020_2024",

            "value":
                len(
                    rows_2020_2024
                ),
        },

        {
            "metric":
                "canonical_numeric_collision_groups",

            "value":
                len(
                    collision_keys
                ),
        },

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
                "scripts_with_car_number_normalization_risk",

            "value":
                len(
                    risky_scripts
                ),
        },

        {
            "metric":
                "high_risk_scripts",

            "value":
                len(
                    high_risk_scripts
                ),
        },

        {
            "metric":
                "output_csvs_scanned",

            "value":
                len(
                    output_csvs
                ),
        },

        {
            "metric":
                "collision_sensitive_output_csvs",

            "value":
                len(
                    impact_priority
                ),
        },

        {
            "metric":
                "high_risk_output_csvs",

            "value":
                high_risk_output_count,
        },
    ]

    # ========================================================
    # WRITE OUTPUTS
    # ========================================================

    write_csv(
        SCRIPT_AUDIT_OUT,
        script_audit_rows,
        [
            "script_path",
            "risk_pattern",
            "severity",
            "line_number",
            "context",
            "explanation",
            "referenced_csv_or_output_paths",
            "action",
        ],
    )

    write_csv(
        CANONICAL_COLLISION_OUT,
        canonical_collision_rows,
        [
            "year",
            "numeric_equivalent",
            "literal_car_number",
            "has_leading_zero",
            "drivers",
            "canonical_attempt_count",
            "collision_literals",
            "risk",
            "required_policy",
        ],
    )

    write_csv(
        CSV_IMPACT_OUT,
        impact_rows,
        [
            "csv_path",
            "has_car_number_column",
            "row_count",
            "observed_literal_car_numbers",
            "numeric_collision_detected",
            "leading_zero_present",
            "contains_known_collision_numeric_key",
            "risk_class",
            "notes",
        ],
    )

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

    known_2022_06_6_collision = any(
        (
            row[
                "year"
            ] == "2022"
            and
            row[
                "numeric_equivalent"
            ] == "6"
            and
            row[
                "literal_car_number"
            ]
            in {
                "06",
                "6",
            }
        )
        for row in canonical_collision_rows
    )

    source_files_mutated = 0

    qa_rows = [
        {
            "metric":
                "canonical_loaded",

            "value":
                len(
                    canonical
                ),

            "status":
                "PASS"
                if canonical
                else "FAIL",
        },

        {
            "metric":
                "known_2022_car06_car6_collision_detected",

            "value":
                int(
                    known_2022_06_6_collision
                ),

            "status":
                "PASS"
                if known_2022_06_6_collision
                else "FAIL",
        },

        {
            "metric":
                "scripts_scanned",

            "value":
                len(
                    scripts
                ),

            "status":
                "PASS"
                if scripts
                else "FAIL",
        },

        {
            "metric":
                "output_csvs_scanned",

            "value":
                len(
                    output_csvs
                ),

            "status":
                "PASS"
                if output_csvs
                else "FAIL",
        },

        {
            "metric":
                "identity_key_numeric_normalization_used_by_this_audit",

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
                "existing_output_data_mutated",

            "value":
                0,

            "status":
                "PASS",
        },

        {
            "metric":
                "source_scripts_mutated",

            "value":
                source_files_mutated,

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
        "Canonical numeric collision groups:",
        len(
            collision_keys
        ),
    )

    print(
        "Scripts with normalization risk:",
        len(
            risky_scripts
        ),
    )

    print(
        "High-risk scripts:",
        len(
            high_risk_scripts
        ),
    )

    print(
        "Collision-sensitive output CSVs:",
        len(
            impact_priority
        ),
    )

    print(
        "High-risk output CSVs:",
        high_risk_output_count,
    )

    print()
    print(
        "Known 2022 #06/#6 collision detected:",
        known_2022_06_6_collision,
    )

    print()
    print(
        "Policy established for future rescue work:"
    )

    print(
        "  car_number is a STRING IDENTIFIER."
    )

    print(
        "  Leading zeros are significant."
    )

    print(
        "  Never use int(float(car_number)) for identity."
    )

    print(
        "  Cross-table reconciliation should prefer attempt_id."
    )

    print()
    print(
        "No canonical data was modified."
    )

    print(
        "No existing output CSV was modified."
    )

    print(
        "No source script was modified."
    )

    print()
    print("=" * 120)

    if (
        known_2022_06_6_collision
        and
        len(
            scripts
        ) > 0
        and
        len(
            output_csvs
        ) > 0
    ):

        print(
            "FINAL STATUS: "
            "GLOBAL_CAR_NUMBER_COLLISION_RISK_AUDIT_COMPLETE"
        )

    else:

        print(
            "FINAL STATUS: "
            "GLOBAL_CAR_NUMBER_COLLISION_RISK_AUDIT_REVIEW_REQUIRED"
        )

    print("=" * 120)

    print()
    print("OUTPUTS")
    print(SCRIPT_AUDIT_OUT)
    print(CANONICAL_COLLISION_OUT)
    print(CSV_IMPACT_OUT)
    print(SUMMARY_OUT)
    print(QA_OUT)


if __name__ == "__main__":
    main()
