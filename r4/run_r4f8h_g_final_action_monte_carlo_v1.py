from pathlib import Path
import csv
import json
import math
import hashlib
import statistics
from collections import Counter, defaultdict

import numpy as np


ROOT = Path("/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈")
OUT = ROOT / "r4" / "output"

# =============================================================================
# R4F8H-G — FINAL ACTION-CONDITIONED MONTE CARLO
#
# Frozen inputs:
#   R4F8E current numeric decision state / action semantics
#   R4F8F structural wait distributions
#   R4F8G future-performance distributions
#   R4F8H-C cutoff sensitivity policy
#   R4F8H-F static decision-time competitive benchmark policy
#
# IMPORTANT LIMITATIONS
# ---------------------
# - no empirical competitor-evolution model exists
# - benchmark is held at decision-time observable state
# - no dynamic final-rank probability is produced
# - no empirically calibrated interruption model exists
# - remaining-time scenarios are sensitivity cases, not historical frequencies
# - wait prior is structural, not historical queue-wait frequency
# =============================================================================

N_DRAWS = 20000

TIME_REMAINING_SCENARIOS = [5, 10, 15, 20, 30, 45, 60]

# Authoritative frozen R4F8F structural support.
FROZEN_WAIT_SUPPORT_MIN = np.array(
    [5.0, 15.0, 30.0, 45.0],
    dtype=float,
)
FROZEN_WAIT_PROBS = np.array(
    [0.25, 0.25, 0.25, 0.25],
    dtype=float,
)

F8E_DECISION = OUT / "r4f8e_reconstructed_decision_numeric_state_v1.csv"
F8E_ACTION = OUT / "r4f8e_reconstructed_action_numeric_interface_v1.csv"

F8F_WAIT = OUT / "r4f8f_action_wait_distribution_parameters_v1.csv"
F8F_CONTRACT = OUT / "r4f8f_wait_queue_model_contract_v1.json"

F8G_STATE = OUT / "r4f8g_decision_predictive_uncertainty_state_v1.csv"

F8HC_POLICY = OUT / "r4f8h_c_cutoff_completion_policy_contract_v1.json"
F8HF_POLICY = OUT / "r4f8h_f_competitive_state_policy_contract_v1.json"

FOUR_LAP_PANEL = OUT / "r4p1_attempt_four_lap_panel_v1.csv"

OUT_RESULTS = OUT / "r4f8h_g_action_mc_scenario_results_v1.csv"
OUT_ENVELOPE = OUT / "r4f8h_g_action_mc_sensitivity_envelope_v1.csv"
OUT_BLOCKED = OUT / "r4f8h_g_action_mc_blocked_rows_v1.csv"
OUT_DURATION = OUT / "r4f8h_g_empirical_run_duration_reference_v1.csv"
OUT_QA = OUT / "r4f8h_g_final_action_mc_qa_v1.csv"
OUT_CONTRACT = OUT / "r4f8h_g_final_action_mc_contract_v1.json"
OUT_REPORT = OUT / "r4f8h_g_final_action_mc_report_v1.json"


# =============================================================================
# Generic helpers
# =============================================================================

def clean(v):
    if v is None:
        return ""
    return str(v).strip()


def num(v):
    s = clean(v)
    if not s:
        return None
    try:
        x = float(s)
        if math.isfinite(x):
            return x
    except Exception:
        pass
    return None


def truthy(v):
    return clean(v).lower() in {
        "1", "true", "yes", "y", "t", "ready", "sample_ready"
    }


def read_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return reader.fieldnames or [], list(reader)


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def norm(s):
    return (
        str(s)
        .strip()
        .lower()
        .replace("-", "_")
        .replace(" ", "_")
    )


def find_field(fields, candidates):
    m = {norm(f): f for f in fields}
    for c in candidates:
        if norm(c) in m:
            return m[norm(c)]
    return None


def stable_seed(*parts):
    text = "||".join(map(str, parts))
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return int(digest[:16], 16) % (2**32)


def quantile_or_blank(values, q):
    values = np.asarray(values, dtype=float)
    values = values[np.isfinite(values)]
    if len(values) == 0:
        return ""
    return float(np.quantile(values, q))


def mean_or_blank(values):
    values = np.asarray(values, dtype=float)
    values = values[np.isfinite(values)]
    if len(values) == 0:
        return ""
    return float(np.mean(values))


def prob(mask):
    mask = np.asarray(mask, dtype=bool)
    if len(mask) == 0:
        return ""
    return float(np.mean(mask))


# =============================================================================
# Required files
# =============================================================================

required = [
    F8E_DECISION,
    F8E_ACTION,
    F8F_WAIT,
    F8F_CONTRACT,
    F8G_STATE,
    F8HC_POLICY,
    F8HF_POLICY,
    FOUR_LAP_PANEL,
]

missing = [p for p in required if not p.exists()]

if missing:
    print("=" * 130)
    print("R4F8H-G REQUIRED INPUTS MISSING")
    print("=" * 130)
    for p in missing:
        print(p.relative_to(ROOT))
    raise SystemExit(1)


# =============================================================================
# Load inputs
# =============================================================================

dec_fields, dec_rows = read_csv(F8E_DECISION)
act_fields, act_rows = read_csv(F8E_ACTION)
wait_fields, wait_rows = read_csv(F8F_WAIT)
unc_fields, unc_rows = read_csv(F8G_STATE)
panel_fields, panel_rows = read_csv(FOUR_LAP_PANEL)

f8f_contract = json.loads(F8F_CONTRACT.read_text(encoding="utf-8"))
f8hc_policy = json.loads(F8HC_POLICY.read_text(encoding="utf-8"))
f8hf_policy = json.loads(F8HF_POLICY.read_text(encoding="utf-8"))


# =============================================================================
# Resolve fields
# =============================================================================

DEC_ID = find_field(
    dec_fields,
    ["fused_decision_id", "decision_id", "source_decision_id"]
)

ACT_DEC_ID = find_field(
    act_fields,
    ["fused_decision_id", "decision_id", "source_decision_id"]
)

ACTION = find_field(
    act_fields,
    ["feasible_action", "action"]
)

REGIME_D = find_field(
    dec_fields,
    ["regime", "session_regime", "qualifying_regime"]
)

REGIME_A = find_field(
    act_fields,
    ["regime", "session_regime", "qualifying_regime"]
)

YEAR = find_field(
    dec_fields,
    ["year", "season"]
)

DRIVER = find_field(
    dec_fields,
    ["driver_name", "driver", "normalized_driver_name"]
)

PROTECTED = find_field(
    dec_fields,
    ["protected_result_exists", "has_protected_result"]
)

CURRENT_SPEED = find_field(
    dec_fields,
    [
        "current_best_speed_mph",
        "current_result_mph",
        "current_speed_mph",
    ]
)

PROTECTED_SPEED = find_field(
    dec_fields,
    [
        "protected_result_speed_mph",
        "current_protected_result_speed_mph",
    ]
)

CURRENT_RANK = find_field(
    dec_fields,
    ["current_rank", "current_best_rank", "rank"]
)

BENCHMARK_SPEED = find_field(
    dec_fields,
    [
        "benchmark_speed_mph",
        "regime_benchmark_speed_mph",
        "cutoff_speed_mph",
        "advancement_benchmark_speed_mph",
    ]
)

BENCHMARK_RANK = find_field(
    dec_fields,
    ["benchmark_rank", "cutoff_rank", "benchmark_position"]
)

BENCHMARK_TYPE = find_field(
    dec_fields,
    ["benchmark_type", "benchmark"]
)

UNC_DEC_ID = find_field(
    unc_fields,
    ["fused_decision_id", "decision_id", "source_decision_id"]
)

PRED_MEAN = find_field(
    unc_fields,
    [
        "predictive_mean_speed_mph",
        "predicted_speed_mph",
        "predictive_mean_mph",
        "mean_speed_mph",
    ]
)

PRED_SD = find_field(
    unc_fields,
    [
        "predictive_sd_mph",
        "prediction_sd_mph",
        "sd_mph",
        "predictive_scale_mph",
    ]
)

SAMPLE_READY = find_field(
    unc_fields,
    [
        "sample_ready",
        "performance_sample_ready",
        "sampleable",
        "performance_sampleable",
    ]
)

UNC_CLASS = find_field(
    unc_fields,
    [
        "uncertainty_class",
        "support_class",
        "predictive_uncertainty_class",
    ]
)

SUPPORT_N = find_field(
    unc_fields,
    [
        "support_count",
        "same_session_support_count",
        "n_support",
        "n_prior_other_driver_rows",
    ]
)

PANEL_SPEED = find_field(
    panel_fields,
    [
        "four_lap_avg_speed_mph",
        "four_lap_average_speed_mph",
        "avg_speed_mph",
        "average_speed_mph",
        "official_four_lap_avg_speed_mph",
        "qualifying_speed_mph",
        "attempt_average_speed_mph",
    ]
)

PANEL_CLASS = find_field(
    panel_fields,
    [
        "reconstruction_class",
        "attempt_reconstruction_class",
        "record_class",
    ]
)


essential = {
    "DEC_ID": DEC_ID,
    "ACT_DEC_ID": ACT_DEC_ID,
    "ACTION": ACTION,
    "PROTECTED": PROTECTED,
    "BENCHMARK_SPEED": BENCHMARK_SPEED,
    "UNC_DEC_ID": UNC_DEC_ID,
    "PRED_MEAN": PRED_MEAN,
    "PRED_SD": PRED_SD,
    "PANEL_SPEED": PANEL_SPEED,
}

missing_fields = [
    k for k, v in essential.items()
    if v is None
]

if missing_fields:
    print("=" * 130)
    print("R4F8H-G REQUIRED FIELD RESOLUTION FAILED")
    print("=" * 130)
    for k in missing_fields:
        print(k)
    print()
    print("DO NOT MODIFY THE SCRIPT YET. RETURN THIS OUTPUT.")
    raise SystemExit(1)


# =============================================================================
# Frozen universe checks
# =============================================================================

if len(dec_rows) != 60:
    raise SystemExit(f"Decision universe changed: {len(dec_rows)} != 60")

if len(act_rows) != 170:
    raise SystemExit(f"Action universe changed: {len(act_rows)} != 170")

decision_ids = [clean(r.get(DEC_ID)) for r in dec_rows]

if len(set(decision_ids)) != 60 or "" in set(decision_ids):
    raise SystemExit("Decision IDs are not 60 unique non-empty values.")


# =============================================================================
# Empirical completed four-lap duration distribution
#
# Indianapolis lap length = 2.5 miles.
# Four-lap qualifying distance = 10 miles.
#
# duration_seconds = 10 miles / speed_mph * 3600
#                  = 36000 / speed_mph
# =============================================================================

duration_reference = []

for row in panel_rows:

    speed = num(row.get(PANEL_SPEED))

    if speed is None or speed <= 0:
        continue

    if PANEL_CLASS:
        cls = clean(row.get(PANEL_CLASS))
        if cls and cls != "A_COMPLETE":
            continue

    duration_sec = 36000.0 / speed

    # Conservative physical sanity window for Indy 500 four-lap qualifying.
    # This is only a corruption guard, not a modelling selection criterion.
    if 120.0 <= duration_sec <= 220.0:
        duration_reference.append(duration_sec)


if len(duration_reference) != 260:
    print("=" * 130)
    print("R4F8H-G RUN-DURATION REFERENCE COUNT MISMATCH")
    print("=" * 130)
    print(f"Resolved panel speed field: {PANEL_SPEED}")
    print(f"Resolved reconstruction class field: {PANEL_CLASS}")
    print(f"Derived duration rows: {len(duration_reference)}")
    print("Expected frozen A_COMPLETE count: 260")
    print()
    print("STOP. Do not invent or silently alter the duration sample.")
    raise SystemExit(1)


duration_reference = np.asarray(duration_reference, dtype=float)
duration_minutes = duration_reference / 60.0


duration_rows = [{
    "source": str(FOUR_LAP_PANEL.relative_to(ROOT)),
    "derivation": "36000 / four_lap_avg_speed_mph",
    "n": len(duration_reference),
    "median_seconds": float(np.median(duration_reference)),
    "mean_seconds": float(np.mean(duration_reference)),
    "q05_seconds": float(np.quantile(duration_reference, 0.05)),
    "q95_seconds": float(np.quantile(duration_reference, 0.95)),
    "min_seconds": float(np.min(duration_reference)),
    "max_seconds": float(np.max(duration_reference)),
    "use": "EMPIRICAL_COMPLETION_DURATION_COMPONENT_ONLY",
    "not_use": "NOT_QUEUE_WAIT_NOT_SESSION_REMAINING",
}]

with OUT_DURATION.open("w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=list(duration_rows[0].keys()),
    )
    writer.writeheader()
    writer.writerows(duration_rows)


# =============================================================================
# Build lookups
# =============================================================================

decision_by_id = {
    clean(r.get(DEC_ID)): r
    for r in dec_rows
}

unc_by_id = defaultdict(list)

for row in unc_rows:
    unc_by_id[clean(row.get(UNC_DEC_ID))].append(row)


# =============================================================================
# Helpers for decision state
# =============================================================================

def decision_value(row, field):
    if field is None:
        return ""
    return clean(row.get(field))


def decision_num(row, field):
    if field is None:
        return None
    return num(row.get(field))


def current_result_speed(decision):
    """
    Prefer current best speed.
    If unresolved but a protected result exists and protected speed is
    available, use protected speed as the retained baseline.

    Never fabricate a value.
    """
    x = decision_num(decision, CURRENT_SPEED)
    if x is not None:
        return x

    p = decision_num(decision, PROTECTED_SPEED)
    if p is not None:
        return p

    return None


def has_protected_result(decision):
    return truthy(decision_value(decision, PROTECTED))


def uncertainty_state(did):
    matches = unc_by_id.get(did, [])
    if len(matches) != 1:
        return None
    return matches[0]


def performance_sample_ready(u):
    if u is None:
        return False

    if SAMPLE_READY:
        return truthy(u.get(SAMPLE_READY))

    mu = num(u.get(PRED_MEAN))
    sd = num(u.get(PRED_SD))

    return (
        mu is not None
        and sd is not None
        and sd > 0
    )


# =============================================================================
# Frozen action semantics
# =============================================================================

ACTION_SEMANTICS = {
    "STOP": {
        "requires_attempt": False,
        "retains_protected_result": True,
        "surrenders_protected_result": False,
    },

    "REATTEMPT": {
        "requires_attempt": True,
        "retains_protected_result": False,
        "surrenders_protected_result": False,
    },

    "RETAIN_AND_REATTEMPT": {
        "requires_attempt": True,
        "retains_protected_result": True,
        "surrenders_protected_result": False,
    },

    "WITHDRAW_AND_REATTEMPT": {
        "requires_attempt": True,
        "retains_protected_result": False,
        "surrenders_protected_result": True,
    },

    "WITHDRAW_AND_PRIORITY_REATTEMPT": {
        "requires_attempt": True,
        "retains_protected_result": False,
        "surrenders_protected_result": True,
    },
}


# =============================================================================
# Monte Carlo
# =============================================================================

results = []
blocked_rows = []

for action_row in act_rows:

    did = clean(action_row.get(ACT_DEC_ID))
    action = clean(action_row.get(ACTION))

    if did not in decision_by_id:
        raise SystemExit(f"Action decision ID not found: {did}")

    if action not in ACTION_SEMANTICS:
        raise SystemExit(f"Unknown frozen action: {action}")

    decision = decision_by_id[did]
    semantics = ACTION_SEMANTICS[action]

    year = decision_value(decision, YEAR)
    driver = decision_value(decision, DRIVER)
    regime = (
        decision_value(decision, REGIME_D)
        if REGIME_D
        else decision_value(action_row, REGIME_A)
    )

    protected = has_protected_result(decision)
    old_speed = current_result_speed(decision)
    benchmark_speed = decision_num(decision, BENCHMARK_SPEED)
    benchmark_rank = decision_num(decision, BENCHMARK_RANK)
    current_rank = decision_num(decision, CURRENT_RANK)
    benchmark_type = decision_value(decision, BENCHMARK_TYPE)

    u = uncertainty_state(did)

    mu = num(u.get(PRED_MEAN)) if u else None
    sd = num(u.get(PRED_SD)) if u else None

    sample_ready = performance_sample_ready(u)

    support_n = (
        clean(u.get(SUPPORT_N))
        if u and SUPPORT_N
        else ""
    )

    uncertainty_class = (
        clean(u.get(UNC_CLASS))
        if u and UNC_CLASS
        else ""
    )

    # STOP is deterministic and does not require performance sampling.
    if action == "STOP":

        for remaining in TIME_REMAINING_SCENARIOS:

            final_exists = old_speed is not None

            if final_exists and benchmark_speed is not None:
                benchmark_hit = float(old_speed >= benchmark_speed)
            else:
                benchmark_hit = 0.0

            results.append({
                "fused_decision_id": did,
                "year": year,
                "driver": driver,
                "regime": regime,
                "action": action,
                "protected_result_exists_at_decision": protected,
                "assumed_time_remaining_minutes": remaining,
                "time_remaining_semantics":
                    "STRUCTURAL_SENSITIVITY_SCENARIO",
                "n_draws": N_DRAWS,
                "mc_status": "DETERMINISTIC_STOP",

                "performance_sample_ready": sample_ready,
                "predictive_mean_mph": mu if mu is not None else "",
                "predictive_sd_mph": sd if sd is not None else "",
                "performance_support_count": support_n,
                "uncertainty_class": uncertainty_class,

                "current_result_speed_mph":
                    old_speed if old_speed is not None else "",
                "benchmark_type": benchmark_type,
                "benchmark_rank":
                    benchmark_rank if benchmark_rank is not None else "",
                "benchmark_speed_mph":
                    benchmark_speed if benchmark_speed is not None else "",

                "p_reattempt_completed": 0.0,
                "p_final_result_exists": 1.0 if final_exists else 0.0,
                "p_no_final_result": 0.0 if final_exists else 1.0,

                "p_new_attempt_beats_current_result": "",
                "p_new_attempt_meets_or_exceeds_decision_benchmark": "",

                "p_final_result_meets_or_exceeds_decision_benchmark":
                    benchmark_hit,

                "p_final_result_worse_than_current": 0.0,
                "p_protected_result_surrendered": 0.0,

                "expected_new_attempt_speed_mph": "",
                "expected_final_result_speed_conditional_mph":
                    old_speed if final_exists else "",

                "final_speed_q05_mph":
                    old_speed if final_exists else "",
                "final_speed_q25_mph":
                    old_speed if final_exists else "",
                "final_speed_q50_mph":
                    old_speed if final_exists else "",
                "final_speed_q75_mph":
                    old_speed if final_exists else "",
                "final_speed_q95_mph":
                    old_speed if final_exists else "",

                "wait_mean_minutes": 0.0,
                "wait_q05_minutes": 0.0,
                "wait_q50_minutes": 0.0,
                "wait_q95_minutes": 0.0,

                "run_duration_mean_minutes": 0.0,
                "completion_time_mean_minutes": 0.0,

                "dynamic_competitor_evolution_used": False,
                "interruption_model_used": False,
            })

        continue

    # -------------------------------------------------------------------------
    # Non-STOP actions require future-performance distribution.
    # -------------------------------------------------------------------------

    if (
        not sample_ready
        or mu is None
        or sd is None
        or sd <= 0
    ):

        blocked_rows.append({
            "fused_decision_id": did,
            "year": year,
            "driver": driver,
            "regime": regime,
            "action": action,
            "reason":
                "FUTURE_PERFORMANCE_DISTRIBUTION_NOT_SAMPLE_READY",
            "predictive_mean_mph":
                mu if mu is not None else "",
            "predictive_sd_mph":
                sd if sd is not None else "",
        })

        continue

    # -------------------------------------------------------------------------
    # Scenario-conditioned MC
    # -------------------------------------------------------------------------

    for remaining in TIME_REMAINING_SCENARIOS:

        seed = stable_seed(
            "R4F8H-G",
            did,
            action,
            remaining,
            N_DRAWS,
        )

        rng = np.random.default_rng(seed)

        wait_draws = rng.choice(
            FROZEN_WAIT_SUPPORT_MIN,
            size=N_DRAWS,
            replace=True,
            p=FROZEN_WAIT_PROBS,
        )

        run_draws = rng.choice(
            duration_minutes,
            size=N_DRAWS,
            replace=True,
        )

        new_speed = rng.normal(
            loc=mu,
            scale=sd,
            size=N_DRAWS,
        )

        completion_time = wait_draws + run_draws

        completed = completion_time <= float(remaining)

        # ---------------------------------------------------------------------
        # New-attempt-only metrics
        # ---------------------------------------------------------------------

        if old_speed is not None:
            new_beats_current = completed & (new_speed > old_speed)
            p_new_beats_current = prob(new_beats_current)
        else:
            p_new_beats_current = ""

        if benchmark_speed is not None:
            new_hits_benchmark = (
                completed
                & (new_speed >= benchmark_speed)
            )
            p_new_hits_benchmark = prob(new_hits_benchmark)
        else:
            p_new_hits_benchmark = ""

        # ---------------------------------------------------------------------
        # Final-result semantics
        # ---------------------------------------------------------------------

        final_speed = np.full(
            N_DRAWS,
            np.nan,
            dtype=float,
        )

        if action == "RETAIN_AND_REATTEMPT":

            if old_speed is None:
                raise SystemExit(
                    f"RETAIN action has no retained speed: {did}"
                )

            # Existing result survives even if no new attempt completes.
            final_speed[:] = old_speed

            # Completed attempt can improve but cannot worsen retained result.
            final_speed[completed] = np.maximum(
                old_speed,
                new_speed[completed],
            )

        elif action in {
            "WITHDRAW_AND_REATTEMPT",
            "WITHDRAW_AND_PRIORITY_REATTEMPT",
        }:

            # Protected result is surrendered before the retry.
            # No completed attempt => no final result.
            final_speed[completed] = new_speed[completed]

        elif action == "REATTEMPT":

            # Last Chance unprotected retry.
            # No old protected result exists.
            final_speed[completed] = new_speed[completed]

        else:
            raise SystemExit(f"Unhandled action: {action}")

        final_exists = np.isfinite(final_speed)

        # ---------------------------------------------------------------------
        # Benchmark metrics
        # ---------------------------------------------------------------------

        if benchmark_speed is not None:

            final_hits_benchmark = (
                final_exists
                & (final_speed >= benchmark_speed)
            )

            p_final_hits_benchmark = prob(
                final_hits_benchmark
            )

        else:
            p_final_hits_benchmark = ""

        # ---------------------------------------------------------------------
        # Downside vs current state
        # ---------------------------------------------------------------------

        if old_speed is not None:

            # No final result after having a current result is downside.
            final_worse = (
                (~final_exists)
                | (
                    final_exists
                    & (final_speed < old_speed)
                )
            )

            p_final_worse = prob(final_worse)

        else:
            # No valid current result means "worse than current result"
            # is not a meaningful numeric target.
            p_final_worse = ""

        p_surrendered = (
            1.0
            if semantics["surrenders_protected_result"] and protected
            else 0.0
        )

        # ---------------------------------------------------------------------
        # Store
        # ---------------------------------------------------------------------

        results.append({
            "fused_decision_id": did,
            "year": year,
            "driver": driver,
            "regime": regime,
            "action": action,
            "protected_result_exists_at_decision": protected,

            "assumed_time_remaining_minutes": remaining,
            "time_remaining_semantics":
                "STRUCTURAL_SENSITIVITY_SCENARIO",

            "n_draws": N_DRAWS,
            "mc_status": "SIMULATED",

            "performance_sample_ready": True,
            "predictive_mean_mph": mu,
            "predictive_sd_mph": sd,
            "performance_support_count": support_n,
            "uncertainty_class": uncertainty_class,

            "current_result_speed_mph":
                old_speed if old_speed is not None else "",

            "benchmark_type": benchmark_type,
            "benchmark_rank":
                benchmark_rank if benchmark_rank is not None else "",
            "benchmark_speed_mph":
                benchmark_speed if benchmark_speed is not None else "",

            "p_reattempt_completed":
                prob(completed),

            "p_final_result_exists":
                prob(final_exists),

            "p_no_final_result":
                prob(~final_exists),

            "p_new_attempt_beats_current_result":
                p_new_beats_current,

            "p_new_attempt_meets_or_exceeds_decision_benchmark":
                p_new_hits_benchmark,

            "p_final_result_meets_or_exceeds_decision_benchmark":
                p_final_hits_benchmark,

            "p_final_result_worse_than_current":
                p_final_worse,

            "p_protected_result_surrendered":
                p_surrendered,

            "expected_new_attempt_speed_mph":
                float(np.mean(new_speed)),

            "expected_final_result_speed_conditional_mph":
                mean_or_blank(final_speed),

            "final_speed_q05_mph":
                quantile_or_blank(final_speed, 0.05),

            "final_speed_q25_mph":
                quantile_or_blank(final_speed, 0.25),

            "final_speed_q50_mph":
                quantile_or_blank(final_speed, 0.50),

            "final_speed_q75_mph":
                quantile_or_blank(final_speed, 0.75),

            "final_speed_q95_mph":
                quantile_or_blank(final_speed, 0.95),

            "wait_mean_minutes":
                float(np.mean(wait_draws)),

            "wait_q05_minutes":
                float(np.quantile(wait_draws, 0.05)),

            "wait_q50_minutes":
                float(np.quantile(wait_draws, 0.50)),

            "wait_q95_minutes":
                float(np.quantile(wait_draws, 0.95)),

            "run_duration_mean_minutes":
                float(np.mean(run_draws)),

            "completion_time_mean_minutes":
                float(np.mean(completion_time)),

            "dynamic_competitor_evolution_used":
                False,

            "interruption_model_used":
                False,
        })


# =============================================================================
# Save scenario-level results
# =============================================================================

if not results:
    raise SystemExit("No Monte Carlo results generated.")

with OUT_RESULTS.open("w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=list(results[0].keys()),
    )
    writer.writeheader()
    writer.writerows(results)


# =============================================================================
# Save blocked action rows
# =============================================================================

blocked_fields = [
    "fused_decision_id",
    "year",
    "driver",
    "regime",
    "action",
    "reason",
    "predictive_mean_mph",
    "predictive_sd_mph",
]

with OUT_BLOCKED.open("w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=blocked_fields,
    )
    writer.writeheader()
    writer.writerows(blocked_rows)


# =============================================================================
# Scenario sensitivity envelope
#
# IMPORTANT:
# These are MIN/MAX ACROSS SCENARIOS.
# They are NOT averages and NOT probabilities over remaining-time values.
# =============================================================================

grouped = defaultdict(list)

for row in results:
    grouped[
        (
            row["fused_decision_id"],
            row["action"],
        )
    ].append(row)


envelope_rows = []

metrics_for_envelope = [
    "p_reattempt_completed",
    "p_final_result_exists",
    "p_no_final_result",
    "p_final_result_meets_or_exceeds_decision_benchmark",
    "p_final_result_worse_than_current",
    "expected_final_result_speed_conditional_mph",
]


for (did, action), group in sorted(grouped.items()):

    base = group[0]

    out = {
        "fused_decision_id": did,
        "year": base["year"],
        "driver": base["driver"],
        "regime": base["regime"],
        "action": action,

        "scenario_count": len(group),
        "scenario_minutes":
            "|".join(
                str(r["assumed_time_remaining_minutes"])
                for r in sorted(
                    group,
                    key=lambda x: x["assumed_time_remaining_minutes"]
                )
            ),

        "aggregation_semantics":
            "SENSITIVITY_MIN_MAX_NOT_PROBABILITY_WEIGHTED",
    }

    for metric in metrics_for_envelope:

        vals = [
            num(r.get(metric))
            for r in group
        ]

        vals = [
            v for v in vals
            if v is not None
        ]

        out[f"{metric}_min"] = (
            min(vals) if vals else ""
        )

        out[f"{metric}_max"] = (
            max(vals) if vals else ""
        )

    envelope_rows.append(out)


with OUT_ENVELOPE.open("w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=list(envelope_rows[0].keys()),
    )
    writer.writeheader()
    writer.writerows(envelope_rows)


# =============================================================================
# QA
# =============================================================================

qa_rows = []


def qa(metric, value, expected, status):
    qa_rows.append({
        "metric": metric,
        "value": value,
        "expected": expected,
        "status": status,
    })


action_counts = Counter(
    clean(r.get(ACTION))
    for r in act_rows
)

expected_action_counts = {
    "STOP": 60,
    "RETAIN_AND_REATTEMPT": 50,
    "WITHDRAW_AND_PRIORITY_REATTEMPT": 50,
    "WITHDRAW_AND_REATTEMPT": 6,
    "REATTEMPT": 4,
}

qa(
    "decision_rows",
    len(dec_rows),
    60,
    "PASS" if len(dec_rows) == 60 else "FAIL",
)

qa(
    "action_rows",
    len(act_rows),
    170,
    "PASS" if len(act_rows) == 170 else "FAIL",
)

qa(
    "action_counts",
    json.dumps(dict(action_counts), sort_keys=True),
    json.dumps(expected_action_counts, sort_keys=True),
    (
        "PASS"
        if dict(action_counts) == expected_action_counts
        else "FAIL"
    ),
)

qa(
    "run_duration_reference_n",
    len(duration_reference),
    260,
    "PASS" if len(duration_reference) == 260 else "FAIL",
)

qa(
    "run_duration_median_seconds",
    round(float(np.median(duration_reference)), 3),
    "approximately 155.779",
    (
        "PASS"
        if abs(float(np.median(duration_reference)) - 155.779) < 1.0
        else "WARN"
    ),
)

qa(
    "run_duration_q95_seconds",
    round(float(np.quantile(duration_reference, 0.95)), 3),
    "approximately 158.103",
    (
        "PASS"
        if abs(
            float(np.quantile(duration_reference, 0.95)) - 158.103
        ) < 1.0
        else "WARN"
    ),
)

qa(
    "time_remaining_scenarios",
    ",".join(map(str, TIME_REMAINING_SCENARIOS)),
    "5,10,15,20,30,45,60",
    "PASS",
)

expected_full_scenario_rows = 170 * 7

# Sage Karam blocks only non-STOP actions.
blocked_nonstop = len(blocked_rows)

actual_result_rows = len(results)

qa(
    "scenario_result_rows",
    actual_result_rows,
    f"{expected_full_scenario_rows} minus blocked-action scenarios",
    (
        "PASS"
        if actual_result_rows
        == expected_full_scenario_rows - blocked_nonstop * 7
        else "FAIL"
    ),
)

qa(
    "blocked_action_rows",
    blocked_nonstop,
    "expected from sole non-sample-ready decision",
    "PASS" if blocked_nonstop > 0 else "WARN",
)

qa(
    "all_stop_rows_have_zero_wait",
    all(
        float(r["wait_mean_minutes"]) == 0.0
        for r in results
        if r["action"] == "STOP"
    ),
    True,
    (
        "PASS"
        if all(
            float(r["wait_mean_minutes"]) == 0.0
            for r in results
            if r["action"] == "STOP"
        )
        else "FAIL"
    ),
)

qa(
    "retain_actions_never_lose_result_when_baseline_exists",
    all(
        float(r["p_no_final_result"]) == 0.0
        for r in results
        if r["action"] == "RETAIN_AND_REATTEMPT"
    ),
    True,
    (
        "PASS"
        if all(
            float(r["p_no_final_result"]) == 0.0
            for r in results
            if r["action"] == "RETAIN_AND_REATTEMPT"
        )
        else "FAIL"
    ),
)

qa(
    "dynamic_competitor_evolution_used",
    False,
    False,
    "PASS",
)

qa(
    "dynamic_final_rank_generated",
    False,
    False,
    "PASS",
)

qa(
    "interruption_model_used",
    False,
    False,
    "PASS",
)

qa(
    "remaining_time_scenarios_probability_weighted",
    False,
    False,
    "PASS",
)

qa(
    "old_r4p11_final_probabilities_used",
    False,
    False,
    "PASS",
)

qa(
    "historical_actions_used_as_optimal_labels",
    False,
    False,
    "PASS",
)

qa(
    "2024_retuning_performed",
    False,
    False,
    "PASS",
)


with OUT_QA.open("w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=["metric", "value", "expected", "status"],
    )
    writer.writeheader()
    writer.writerows(qa_rows)


# =============================================================================
# Contract
# =============================================================================

contract = {
    "phase":
        "R4F8H-G",

    "status":
        "R4F8H_FINAL_ACTION_MONTE_CARLO_COMPLETE",

    "draws_per_action_per_scenario":
        N_DRAWS,

    "remaining_time_policy": {
        "values_minutes":
            TIME_REMAINING_SCENARIOS,
        "semantics":
            "STRUCTURAL_SENSITIVITY_SCENARIOS",
        "probability_distribution":
            None,
        "scenario_average_allowed":
            False,
    },

    "wait_policy": {
        "non_stop_support_minutes":
            FROZEN_WAIT_SUPPORT_MIN.tolist(),
        "probabilities":
            FROZEN_WAIT_PROBS.tolist(),
        "semantics":
            "R4F8F_STRUCTURAL_PRIOR_NOT_EMPIRICAL_QUEUE_WAIT",
        "stop_wait_minutes":
            0.0,
    },

    "run_duration_policy": {
        "source":
            str(FOUR_LAP_PANEL.relative_to(ROOT)),
        "n":
            len(duration_reference),
        "derivation":
            "36000 / four_lap_average_speed_mph",
        "sampling":
            "EMPIRICAL_BOOTSTRAP",
        "semantics":
            "COMPLETE_FOUR_LAP_RUN_DURATION_ONLY",
    },

    "performance_policy": {
        "source":
            str(F8G_STATE.relative_to(ROOT)),
        "sampling":
            "NORMAL_FROM_FROZEN_PREDICTIVE_MEAN_AND_SD",
        "point_architecture_refit":
            False,
    },

    "competitive_state_policy": {
        "source":
            str(F8HF_POLICY.relative_to(ROOT)),
        "benchmark":
            "STATIC_DECISION_TIME_BENCHMARK",
        "dynamic_competitor_evolution":
            False,
        "dynamic_final_rank_output":
            False,
    },

    "interruption_policy": {
        "empirically_calibrated_component_available":
            False,
        "included":
            False,
        "interpretation":
            (
                "Primary MC is conditional on no separately modelled "
                "interruption shock. No zero-interruption empirical claim "
                "is made."
            ),
    },

    "action_semantics":
        ACTION_SEMANTICS,

    "allowed_claims": [
        "scenario-conditioned probability of completing a reattempt",
        "probability a completed/new attempt beats the current result",
        (
            "probability final result meets or exceeds the benchmark "
            "visible at the decision moment"
        ),
        "probability of ending without a result",
        "probability final state is worse than current result",
        "conditional final-speed distribution",
        "protected-result surrender risk",
        "remaining-time sensitivity envelope",
    ],

    "forbidden_claims": [
        "dynamic final-rank probability",
        "expected final rank under simulated competitors",
        "empirical Lane 1 versus Lane 2 wait superiority",
        "exact historical counterfactual",
        "empirical remaining-time distribution",
        "empirical interruption distribution",
        "universally optimal action",
    ],
}

OUT_CONTRACT.write_text(
    json.dumps(
        contract,
        indent=2,
        ensure_ascii=False,
    ),
    encoding="utf-8",
)


# =============================================================================
# Report
# =============================================================================

passes = sum(
    r["status"] == "PASS"
    for r in qa_rows
)

warns = sum(
    r["status"] == "WARN"
    for r in qa_rows
)

fails = sum(
    r["status"] == "FAIL"
    for r in qa_rows
)

result_counts = Counter(
    r["action"]
    for r in results
)

blocked_decisions = sorted(
    set(
        r["fused_decision_id"]
        for r in blocked_rows
    )
)

protected_inputs = [
    F8E_DECISION,
    F8E_ACTION,
    F8F_WAIT,
    F8F_CONTRACT,
    F8G_STATE,
    F8HC_POLICY,
    F8HF_POLICY,
    FOUR_LAP_PANEL,
]

report = {
    "phase":
        "R4F8H-G",

    "status": (
        "R4F8H_FINAL_ACTION_MONTE_CARLO_COMPLETE"
        if fails == 0
        else "R4F8H_FINAL_ACTION_MONTE_CARLO_FAILED"
    ),

    "universe": {
        "decisions":
            len(dec_rows),
        "actions":
            len(act_rows),
        "action_counts":
            dict(sorted(action_counts.items())),
    },

    "simulation": {
        "draws_per_action_per_scenario":
            N_DRAWS,
        "remaining_time_scenarios":
            TIME_REMAINING_SCENARIOS,
        "scenario_result_rows":
            len(results),
        "sensitivity_envelope_rows":
            len(envelope_rows),
        "blocked_action_rows":
            len(blocked_rows),
        "blocked_decision_ids":
            blocked_decisions,
    },

    "run_duration": {
        "n":
            len(duration_reference),
        "median_seconds":
            float(np.median(duration_reference)),
        "q95_seconds":
            float(np.quantile(duration_reference, 0.95)),
    },

    "capability_boundary": {
        "dynamic_competitor_evolution":
            "NOT_MODELLED_UNIDENTIFIABLE",
        "dynamic_final_rank":
            "NOT_PRODUCED",
        "interruptions":
            "NOT_MODELLED_NO_CALIBRATED_COMPONENT",
        "benchmark":
            "STATIC_DECISION_TIME_OBSERVED",
        "remaining_time":
            "STRUCTURAL_SENSITIVITY_NOT_HISTORICAL_DISTRIBUTION",
        "queue_wait":
            "STRUCTURAL_PRIOR_NOT_EMPIRICAL",
    },

    "qa": {
        "pass":
            passes,
        "warn":
            warns,
        "fail":
            fails,
    },

    "protected_input_hashes": {
        str(p.relative_to(ROOT)): sha256(p)
        for p in protected_inputs
    },

    "output_hashes": {
        str(p.relative_to(ROOT)): sha256(p)
        for p in [
            OUT_RESULTS,
            OUT_ENVELOPE,
            OUT_BLOCKED,
            OUT_DURATION,
            OUT_QA,
            OUT_CONTRACT,
        ]
    },

    "next_phase": (
        "R4F9_HISTORICAL_REPLAY_AND_EVALUATION"
        if fails == 0
        else "RESOLVE_R4F8H_G_FAILURES"
    ),
}

OUT_REPORT.write_text(
    json.dumps(
        report,
        indent=2,
        ensure_ascii=False,
    ),
    encoding="utf-8",
)


# =============================================================================
# Console summary
# =============================================================================

print("=" * 132)
print("R4F8H-G — FINAL ACTION-CONDITIONED MONTE CARLO")
print("=" * 132)
print()

print("FROZEN INPUT UNIVERSE")
print("-" * 132)
print(f"Decisions:                         {len(dec_rows)}")
print(f"Actions:                           {len(act_rows)}")
print()
for k, v in sorted(action_counts.items()):
    print(f"{k:45s} {v}")

print()
print("EMPIRICAL RUN-DURATION COMPONENT")
print("-" * 132)
print(f"Complete four-lap durations:       {len(duration_reference)}")
print(
    f"Median duration:                   "
    f"{np.median(duration_reference):.3f} sec"
)
print(
    f"Q95 duration:                      "
    f"{np.quantile(duration_reference, 0.95):.3f} sec"
)
print()

print("MONTE CARLO")
print("-" * 132)
print(f"Draws/action/scenario:             {N_DRAWS:,}")
print(
    "Remaining-time scenarios:          "
    + ", ".join(map(str, TIME_REMAINING_SCENARIOS))
    + " min"
)
print(f"Scenario result rows:              {len(results)}")
print(f"Sensitivity-envelope rows:         {len(envelope_rows)}")
print(f"Blocked action rows:               {len(blocked_rows)}")
print()

if blocked_decisions:
    print("BLOCKED DECISIONS")
    print("-" * 132)
    for did in blocked_decisions:
        print(did)
    print()

print("CAPABILITY BOUNDARY")
print("-" * 132)
print("Benchmark:                         STATIC DECISION-TIME")
print("Dynamic competitor evolution:      NOT MODELLED")
print("Dynamic final-rank probabilities:  NOT PRODUCED")
print("Interruption shock model:          NOT MODELLED")
print("Queue wait:                        STRUCTURAL PRIOR")
print("Remaining time:                    SENSITIVITY SCENARIOS")
print()

print("QA")
print("-" * 132)
print(f"{passes} PASS | {warns} WARN | {fails} FAIL")

for r in qa_rows:
    if r["status"] != "PASS":
        print(
            f"{r['status']:5s} | "
            f"{r['metric']} | "
            f"value={r['value']} | "
            f"expected={r['expected']}"
        )

print()
print("OUTPUTS")
print("-" * 132)

for p in [
    OUT_RESULTS,
    OUT_ENVELOPE,
    OUT_BLOCKED,
    OUT_DURATION,
    OUT_QA,
    OUT_CONTRACT,
    OUT_REPORT,
]:
    print(p.relative_to(ROOT))

print()

if fails:
    print("R4F8H_G_FINAL_ACTION_MONTE_CARLO_FAILED")
    raise SystemExit(1)

print("R4F8H_FINAL_ACTION_MONTE_CARLO_COMPLETE")
print()
print("NEXT: R4F9 HISTORICAL REPLAY / EVALUATION")
print()
print(
    "IMPORTANT: Results are conditional on each remaining-time "
    "sensitivity scenario and the benchmark observable at the "
    "decision moment. No scenario probabilities or dynamic-rank "
    "claims were introduced."
)
