from pathlib import Path
import hashlib
import json
import datetime

import pandas as pd

ROOT = Path(
    "/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈"
)

R6 = ROOT / "r6_regime_extension"

OUT = (
    R6 /
    "output/"
    "r6_final_freeze_v1"
)

OUT.mkdir(
    parents=True,
    exist_ok=True
)

# ============================================================
# Frozen reference values
# ============================================================

EXPECTED_B_TRACK = -0.03482533
EXPECTED_B_AMBIENT = 0.18239338

# ============================================================
# Required evidence / result files
# ============================================================

FILES = [
    # Official attempt inventory
    R6 /
    "output/regime_attempt_inventory_v3/"
    "regime_official_attempt_inventory_v3.csv",

    # Clean chronology
    R6 /
    "output/timing71_legacy_run_overlap_qa_v1/"
    "legacy_verified_nonoverlap_repeat_transitions_v1.csv",

    R6 /
    "output/timing71_2025_clean_chronology_v1/"
    "timing71_2025_clean_repeat_transitions_v1.csv",

    # Canonical physical state
    R6 /
    "output/r6_ptsc_canonical_v1/"
    "r6_ptsc_2019_2025_canonical_v1.csv",

    # Linked physics transitions
    R6 /
    "output/r6_repeat_ptsc_linkage_v1/"
    "r6_repeat_transitions_primary_physics_v1.csv",

    R6 /
    "output/r6_repeat_ptsc_linkage_v1/"
    "r6_repeat_ptsc_linkage_summary_v1.csv",

    # Regime model
    R6 /
    "output/r6_regime_physics_comparison_v1/"
    "r6_regime_physics_coefficients_v1.csv",

    R6 /
    "output/r6_regime_physics_comparison_v1/"
    "r6_regime_physics_cluster_bootstrap_v1.csv",

    R6 /
    "output/r6_regime_physics_comparison_v1/"
    "r6_regime_physics_bootstrap_intervals_v1.csv",

    R6 /
    "output/r6_regime_physics_comparison_v1/"
    "r6_regime_physics_comparison_to_frozen_B_v1.csv",

    R6 /
    "output/r6_regime_physics_comparison_v1/"
    "r6_regime_physics_diagnostics_v1.csv",

    R6 /
    "output/r6_regime_physics_comparison_v1/"
    "r6_regime_physics_zero_state_invariance_v1.csv",

    R6 /
    "output/r6_regime_physics_comparison_v1/"
    "r6_regime_physics_comparison_report_v1.json",
]

# Frozen R5.2 reference — read only
R5_CORE = (
    ROOT /
    "r5_2/manual/"
    "probabilistic_physics_core_v1.json"
)

R5_MANIFEST = (
    ROOT /
    "r5_2/manual/"
    "CORE_REGIME_2020_2024_V1_FROZEN_MANIFEST.json"
)

FILES.extend([
    R5_CORE,
    R5_MANIFEST,
])

# ============================================================
# Helpers
# ============================================================

def sha256_file(path):

    h = hashlib.sha256()

    with path.open(
        "rb"
    ) as f:

        while True:

            chunk = f.read(
                1024 * 1024
            )

            if not chunk:
                break

            h.update(
                chunk
            )

    return h.hexdigest()


def interval_contains_zero(
    lo,
    hi
):

    return (
        float(lo)
        <= 0.0
        <= float(hi)
    )


# ============================================================
# Presence QA
# ============================================================

missing = [
    str(
        p.relative_to(ROOT)
    )
    for p in FILES
    if not p.exists()
]

if missing:

    raise FileNotFoundError(
        "Missing required freeze inputs:\n"
        +
        "\n".join(
            missing
        )
    )

# ============================================================
# Load final outputs
# ============================================================

physics = pd.read_csv(
    R6 /
    "output/r6_repeat_ptsc_linkage_v1/"
    "r6_repeat_transitions_primary_physics_v1.csv"
)

coef = pd.read_csv(
    R6 /
    "output/r6_regime_physics_comparison_v1/"
    "r6_regime_physics_coefficients_v1.csv"
)

intervals = pd.read_csv(
    R6 /
    "output/r6_regime_physics_comparison_v1/"
    "r6_regime_physics_bootstrap_intervals_v1.csv"
)

comparison = pd.read_csv(
    R6 /
    "output/r6_regime_physics_comparison_v1/"
    "r6_regime_physics_comparison_to_frozen_B_v1.csv"
)

diag = pd.read_csv(
    R6 /
    "output/r6_regime_physics_comparison_v1/"
    "r6_regime_physics_diagnostics_v1.csv"
)

invariance = pd.read_csv(
    R6 /
    "output/r6_regime_physics_comparison_v1/"
    "r6_regime_physics_zero_state_invariance_v1.csv"
)

link_summary = pd.read_csv(
    R6 /
    "output/r6_repeat_ptsc_linkage_v1/"
    "r6_repeat_ptsc_linkage_summary_v1.csv"
)

# ============================================================
# Core QA
# ============================================================

qa_rows = []

# ------------------------------------------------------------
# Sample sizes
# ------------------------------------------------------------

n_a = int(
    (
        physics[
            "regime_code"
        ]
        == "A"
    ).sum()
)

n_c = int(
    (
        physics[
            "regime_code"
        ]
        == "C"
    ).sum()
)

qa_rows.append({
    "check":
        "REGIME_A_PRIMARY_N",

    "expected":
        10,

    "observed":
        n_a,

    "pass":
        n_a == 10,
})

qa_rows.append({
    "check":
        "REGIME_C_PRIMARY_N",

    "expected":
        23,

    "observed":
        n_c,

    "pass":
        n_c == 23,
})

# ------------------------------------------------------------
# Linkage
# ------------------------------------------------------------

row19 = link_summary[
    link_summary[
        "year"
    ] == 2019
].iloc[0]

row25 = link_summary[
    link_summary[
        "year"
    ] == 2025
].iloc[0]

qa_rows.append({
    "check":
        "2019_LINKAGE",

    "expected":
        "10/10",

    "observed":
        (
            f"{int(row19['primary_safe_transitions'])}/"
            f"{int(row19['input_clean_transitions'])}"
        ),

    "pass":
        (
            int(
                row19[
                    "primary_safe_transitions"
                ]
            )
            == 10
            and
            int(
                row19[
                    "input_clean_transitions"
                ]
            )
            == 10
        ),
})

qa_rows.append({
    "check":
        "2025_LINKAGE",

    "expected":
        "23/24",

    "observed":
        (
            f"{int(row25['primary_safe_transitions'])}/"
            f"{int(row25['input_clean_transitions'])}"
        ),

    "pass":
        (
            int(
                row25[
                    "primary_safe_transitions"
                ]
            )
            == 23
            and
            int(
                row25[
                    "input_clean_transitions"
                ]
            )
            == 24
        ),
})

# ------------------------------------------------------------
# Frozen B unchanged
# ------------------------------------------------------------

b = coef[
    coef[
        "regime_code"
    ] == "B"
].iloc[0]

b_track = float(
    b[
        "beta_track_mph_per_c"
    ]
)

b_ambient = float(
    b[
        "beta_ambient_mph_per_c"
    ]
)

qa_rows.append({
    "check":
        "FROZEN_B_TRACK",

    "expected":
        EXPECTED_B_TRACK,

    "observed":
        b_track,

    "pass":
        abs(
            b_track
            -
            EXPECTED_B_TRACK
        )
        < 1e-8,
})

qa_rows.append({
    "check":
        "FROZEN_B_AMBIENT",

    "expected":
        EXPECTED_B_AMBIENT,

    "observed":
        b_ambient,

    "pass":
        abs(
            b_ambient
            -
            EXPECTED_B_AMBIENT
        )
        < 1e-8,
})

# ------------------------------------------------------------
# Zero-state invariance
# ------------------------------------------------------------

for _, r in invariance.iterrows():

    val = float(
        r[
            "predicted_delta_speed_mph"
        ]
    )

    passed = (
        bool(
            r[
                "invariance_pass"
            ]
        )
        and
        abs(
            val
        )
        < 1e-12
    )

    qa_rows.append({
        "check":
            (
                "ZERO_STATE_"
                +
                str(
                    r[
                        "regime_code"
                    ]
                )
            ),

        "expected":
            0.0,

        "observed":
            val,

        "pass":
            passed,
    })

# ------------------------------------------------------------
# Main regime-difference interpretation QA:
# A-B, C-B, A-C 90% intervals must all include zero
# for both coefficients if final wording says
# "no clear evidence of a regime shift".
# ------------------------------------------------------------

for _, r in comparison.iterrows():

    contains_zero = interval_contains_zero(
        r[
            "difference_90_lo"
        ],
        r[
            "difference_90_hi"
        ],
    )

    qa_rows.append({
        "check":
            (
                "90PCT_DIFF_ZERO_INCLUDED_"
                +
                str(
                    r[
                        "comparison"
                    ]
                )
                +
                "_"
                +
                str(
                    r[
                        "coefficient"
                    ]
                )
            ),

        "expected":
            True,

        "observed":
            contains_zero,

        "pass":
            contains_zero,
    })

qa = pd.DataFrame(
    qa_rows
)

if not bool(
    qa[
        "pass"
    ].all()
):

    print(
        qa.to_string(
            index=False
        )
    )

    raise RuntimeError(
        "R6 freeze QA failed."
    )

# ============================================================
# Pull final values
# ============================================================

def coefficient(
    regime,
    model
):

    row = coef[
        (
            coef[
                "regime_code"
            ]
            == regime
        )
        &
        (
            coef[
                "model"
            ]
            == model
        )
    ].iloc[0]

    return {
        "track":
            float(
                row[
                    "beta_track_mph_per_c"
                ]
            ),

        "ambient":
            float(
                row[
                    "beta_ambient_mph_per_c"
                ]
            ),

        "n":
            int(
                row[
                    "n_transitions"
                ]
            ),
    }


a = coefficient(
    "A",
    "HUBER_IRLS_NO_INTERCEPT"
)

c = coefficient(
    "C",
    "HUBER_IRLS_NO_INTERCEPT"
)

diag_a = diag[
    diag[
        "regime_code"
    ] == "A"
].iloc[0]

diag_c = diag[
    diag[
        "regime_code"
    ] == "C"
].iloc[0]

# ============================================================
# Interpretation
# ============================================================

interpretation = {
    "research_question":
        (
            "Does the physical sensitivity of Indianapolis 500 "
            "qualifying performance remain stable across technical "
            "regulation regimes?"
        ),

    "regimes": {
        "A": {
            "label":
                "UNIVERSAL_AERO_KIT_PRE_AEROSCREEN",

            "direct_repeat_year":
                2019,

            "primary_transitions":
                a[
                    "n"
                ],

            "beta_track_mph_per_c":
                a[
                    "track"
                ],

            "beta_ambient_mph_per_c":
                a[
                    "ambient"
                ],

            "delta_track_ambient_correlation":
                float(
                    diag_a[
                        "delta_track_ambient_correlation"
                    ]
                ),

            "evidence_strength":
                "LIMITED_SMALL_SAMPLE_HIGH_COLLINEARITY",
        },

        "B": {
            "label":
                "AEROSCREEN_PRE_HYBRID",

            "years":
                "2020-2024",

            "primary_transitions":
                41,

            "beta_track_mph_per_c":
                EXPECTED_B_TRACK,

            "beta_ambient_mph_per_c":
                EXPECTED_B_AMBIENT,

            "evidence_strength":
                "FROZEN_REFERENCE_CORE",
        },

        "C": {
            "label":
                "AEROSCREEN_HYBRID",

            "direct_repeat_year":
                2025,

            "primary_transitions":
                c[
                    "n"
                ],

            "beta_track_mph_per_c":
                c[
                    "track"
                ],

            "beta_ambient_mph_per_c":
                c[
                    "ambient"
                ],

            "delta_track_ambient_correlation":
                float(
                    diag_c[
                        "delta_track_ambient_correlation"
                    ]
                ),

            "evidence_strength":
                "DIRECT_REPEAT_EVIDENCE",
        },
    },

    "primary_conclusion":
        (
            "Within the recoverable historical evidence, there is "
            "no clear evidence of a regulation-era shift in "
            "physics-conditioned Indianapolis 500 qualifying "
            "sensitivity. The 2025 hybrid-era sample retains the "
            "same directional track-temperature and ambient-temperature "
            "response as the frozen 2020-2024 reference core. "
            "The 2019 pre-Aeroscreen sample is too small and too "
            "collinear for precise regime-level separation."
        ),

    "important_non_claims": [
        (
            "The analysis does not prove that coefficients are "
            "identical across regimes."
        ),
        (
            "The analysis does not establish a causal regulation "
            "effect or causal absence of a regulation effect."
        ),
        (
            "Regime A should not be treated as a precise coefficient "
            "estimate because n=10 and delta-track/delta-ambient "
            "collinearity is high."
        ),
        (
            "2026 contributes no same-day initial-round repeat "
            "transition evidence because of its qualifying format."
        ),
        (
            "The model does not issue withdraw, delete, retain, "
            "or reattempt recommendations."
        ),
    ],

    "zero_state_invariance":
        True,

    "frozen_B_modified":
        False,
}

INTERPRETATION_OUT = (
    OUT /
    "R6_FINAL_INTERPRETATION_V1.json"
)

INTERPRETATION_OUT.write_text(
    json.dumps(
        interpretation,
        indent=2
    ),
    encoding="utf-8"
)

# ============================================================
# README-style final summary
# ============================================================

summary_md = f"""# R6 Regulation-Aware Physics Extension — Frozen V1

## Status

`R6_REGULATION_AWARE_EXTENSION_V1_FROZEN`

The 2020–2024 R5.2 core remains unchanged.

## Scientific question

Does the physical sensitivity of Indianapolis 500 qualifying
performance remain stable across technical regulation regimes?

## Technical regimes

- **A — Universal Aero Kit / pre-Aeroscreen**
  - Direct repeat-physics evidence: 2019
  - Primary transitions: {a['n']}
  - Huber no-intercept beta_track: {a['track']:.8f} mph/°C
  - Huber no-intercept beta_ambient: {a['ambient']:.8f} mph/°C
  - Delta-track / delta-ambient correlation:
    {float(diag_a['delta_track_ambient_correlation']):.6f}
  - Interpretation: limited, small-sample, highly collinear evidence.

- **B — Aeroscreen / pre-hybrid**
  - Frozen R5.2 reference
  - 2020–2024
  - Primary transitions: 41
  - beta_track: {EXPECTED_B_TRACK:.8f} mph/°C
  - beta_ambient: {EXPECTED_B_AMBIENT:.8f} mph/°C
  - This core was not refitted or modified by R6.

- **C — Aeroscreen / hybrid**
  - Direct repeat-physics evidence: 2025
  - Primary transitions: {c['n']}
  - Huber no-intercept beta_track: {c['track']:.8f} mph/°C
  - Huber no-intercept beta_ambient: {c['ambient']:.8f} mph/°C
  - Delta-track / delta-ambient correlation:
    {float(diag_c['delta_track_ambient_correlation']):.6f}

## Chronology status

- 2018: `PARTIAL_SOURCE_COVERAGE`
- 2019: `PASS`
- 2025: `PASS`
- 2026: `STRUCTURALLY_NO_REPEAT_BY_FORMAT`

## Physical linkage

- 2019: 10 / 10 clean transitions safely linked to PTSC.
- 2025: 23 / 24 clean transitions safely linked to PTSC.
- One 2025 Conor Daly transition was excluded because its endpoint
  occurred after the final PTSC observation.
- Long PTSC observation gaps were not extrapolated into the
  primary physics set.

## Main result

Within the recoverable historical evidence, there is no clear
evidence of a regulation-era shift in physics-conditioned
Indianapolis 500 qualifying sensitivity.

The hybrid-era 2025 sample preserves the same directional response
as the frozen 2020–2024 reference:

- higher track temperature conditional on ambient is associated
  with lower qualifying speed;
- the fitted ambient coefficient conditional on track remains
  positive.

All 90% bootstrap intervals for direct A−B, C−B, and A−C
coefficient differences include zero.

This is **not** an equivalence proof and **not** a causal
regulation-effect analysis.

## Identifiability limitation

Regime A has only 10 primary repeat transitions and strong predictor
collinearity:

`corr(delta_track, delta_ambient) =
{float(diag_a['delta_track_ambient_correlation']):.6f}`

Therefore A should be treated as supporting / compatibility evidence,
not a precise independent sensitivity estimate.

Regime C is substantially better conditioned:

`corr(delta_track, delta_ambient) =
{float(diag_c['delta_track_ambient_correlation']):.6f}`

## Physics invariance

For every regime:

`delta_track = 0` and `delta_ambient = 0`
implies
`predicted physical delta_speed = 0`.

PASS.

## Scope

R6 extends the frozen project with regulation-aware evidence.
It does not replace the 2020–2024 probabilistic decision-support core.

The model remains a physical performance-change support layer and
does not recommend DELETE / WITHDRAW / RETAIN / REATTEMPT actions.
"""

README_OUT = (
    OUT /
    "README_R6_FROZEN_V1.md"
)

README_OUT.write_text(
    summary_md,
    encoding="utf-8"
)

# ============================================================
# SHA256 manifest
# ============================================================

manifest_rows = []

hash_targets = (
    FILES
    +
    [
        INTERPRETATION_OUT,
        README_OUT,
    ]
)

for p in hash_targets:

    manifest_rows.append({
        "path":
            str(
                p.relative_to(
                    ROOT
                )
            ),

        "sha256":
            sha256_file(
                p
            ),

        "bytes":
            p.stat().st_size,
    })

manifest = pd.DataFrame(
    manifest_rows
)

MANIFEST_CSV = (
    OUT /
    "R6_FROZEN_MANIFEST_SHA256_V1.csv"
)

manifest.to_csv(
    MANIFEST_CSV,
    index=False
)

MANIFEST_TXT = (
    OUT /
    "R6_FROZEN_MANIFEST_SHA256_V1.txt"
)

MANIFEST_TXT.write_text(
    "\n".join(
        f"{r['sha256']}  {r['path']}"
        for r in manifest_rows
    )
    +
    "\n",
    encoding="utf-8"
)

# ============================================================
# Freeze metadata
# ============================================================

freeze_metadata = {
    "status":
        "R6_REGULATION_AWARE_EXTENSION_V1_FROZEN",

    "created_utc":
        datetime.datetime.now(
            datetime.timezone.utc
        ).isoformat(),

    "r5_2_core_modified":
        False,

    "regime_A_primary_rows":
        n_a,

    "regime_B_reference_rows":
        41,

    "regime_C_primary_rows":
        n_c,

    "all_freeze_qa_passed":
        True,

    "scientific_core_complete":
        True,
}

FREEZE_JSON = (
    OUT /
    "R6_REGULATION_AWARE_EXTENSION_V1_FROZEN.json"
)

FREEZE_JSON.write_text(
    json.dumps(
        freeze_metadata,
        indent=2
    ),
    encoding="utf-8"
)

QA_OUT = (
    OUT /
    "R6_FINAL_FREEZE_QA_V1.csv"
)

qa.to_csv(
    QA_OUT,
    index=False
)

# Add final freeze files to a second manifest,
# so the freeze record hashes itself except for the manifest.
FINAL_FILES = [
    FREEZE_JSON,
    QA_OUT,
    INTERPRETATION_OUT,
    README_OUT,
    MANIFEST_CSV,
    MANIFEST_TXT,
]

FINAL_MANIFEST = (
    OUT /
    "R6_FINAL_ARTIFACT_HASHES_V1.txt"
)

FINAL_MANIFEST.write_text(
    "\n".join(
        f"{sha256_file(p)}  {p.relative_to(ROOT)}"
        for p in FINAL_FILES
    )
    +
    "\n",
    encoding="utf-8"
)

# ============================================================
# Console
# ============================================================

print(
    "=" * 170
)
print(
    "PART 1 — FINAL FREEZE QA"
)
print(
    "=" * 170
)

print(
    qa.to_string(
        index=False
    )
)

print(
    "\n" + "=" * 170
)
print(
    "PART 2 — FINAL REGIME POINT ESTIMATES"
)
print(
    "=" * 170
)

print(
    f"A: beta_track={a['track']:.8f}, "
    f"beta_ambient={a['ambient']:.8f}, "
    f"n={a['n']}"
)

print(
    f"B: beta_track={EXPECTED_B_TRACK:.8f}, "
    f"beta_ambient={EXPECTED_B_AMBIENT:.8f}, "
    "n=41 [FROZEN]"
)

print(
    f"C: beta_track={c['track']:.8f}, "
    f"beta_ambient={c['ambient']:.8f}, "
    f"n={c['n']}"
)

print(
    "\n" + "=" * 170
)
print(
    "PART 3 — FINAL SCIENTIFIC CONCLUSION"
)
print(
    "=" * 170
)

print(
    interpretation[
        "primary_conclusion"
    ]
)

print(
    "\n" + "=" * 170
)
print(
    "PART 4 — FREEZE OUTPUTS"
)
print(
    "=" * 170
)

for p in [
    FREEZE_JSON,
    QA_OUT,
    INTERPRETATION_OUT,
    README_OUT,
    MANIFEST_CSV,
    MANIFEST_TXT,
    FINAL_MANIFEST,
]:

    print(
        p.relative_to(
            ROOT
        )
    )

print(
    "\nR6_REGULATION_AWARE_EXTENSION_V1_FROZEN"
)
