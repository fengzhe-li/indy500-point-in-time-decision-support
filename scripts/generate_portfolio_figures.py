#!/usr/bin/env python3
"""Generate the curated GitHub figure set from frozen project artefacts.

This script does not fit or modify any scientific model. It copies frozen
publication plots under semantic names and creates explanatory diagrams and
diagnostic summaries from verified FINAL_V2/R6 outputs.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

os.environ.setdefault("MPLBACKEND", "Agg")
os.environ.setdefault("MPLCONFIGDIR", "/tmp/indy500-matplotlib")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "figures" / "portfolio"

BG = "#0b1118"
PANEL = "#141e29"
INK = "#edf4f7"
MUTED = "#9bb0bd"
CYAN = "#45c7d8"
ORANGE = "#ff9f43"
GREEN = "#65d6a6"
RED = "#f26d6d"
GRID = "#2b3b49"


def esc(text: object) -> str:
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def svg_start(title: str, subtitle: str = "") -> list[str]:
    lines = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="900" viewBox="0 0 1600 900">',
        '<defs><marker id="a" markerWidth="10" markerHeight="10" refX="8" refY="5" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#45c7d8"/></marker></defs>',
        f'<rect width="1600" height="900" fill="{BG}"/>',
        f'<text x="80" y="85" fill="{INK}" font-family="Arial" font-size="42" font-weight="700">{esc(title)}</text>',
    ]
    if subtitle:
        lines.append(f'<text x="80" y="125" fill="{MUTED}" font-family="Arial" font-size="21">{esc(subtitle)}</text>')
    return lines


def card(lines: list[str], x: int, y: int, w: int, h: int, title: str, body: list[str], *, accent: str = CYAN, dashed: bool = False) -> None:
    dash = ' stroke-dasharray="12 9"' if dashed else ""
    lines.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="18" fill="{PANEL}" stroke="{accent}" stroke-width="3"{dash}/>')
    lines.append(f'<text x="{x+28}" y="{y+42}" fill="{accent}" font-family="Arial" font-size="23" font-weight="700">{esc(title)}</text>')
    for i, text in enumerate(body):
        lines.append(f'<text x="{x+28}" y="{y+80+i*31}" fill="{INK if i == 0 else MUTED}" font-family="Arial" font-size="19">{esc(text)}</text>')


def arrow(lines: list[str], x1: int, y1: int, x2: int, y2: int) -> None:
    lines.append(f'<path d="M{x1} {y1} L{x2} {y2}" stroke="{CYAN}" stroke-width="3" fill="none" marker-end="url(#a)"/>')


def write_svg(name: str, lines: list[str]) -> None:
    lines.append('</svg>')
    (OUT / name).write_text("\n".join(lines), encoding="utf-8")


def identifiability() -> None:
    l = svg_start("Identifiability drove the architecture", "The missing opportunity process is exposed, not guessed.")
    card(l, 510, 160, 580, 110, "ORIGINAL DECISION", ["retain result or withdraw for priority", "queue, time, weather, performance and downside interact"], accent=ORANGE)
    arrow(l, 800, 270, 800, 330)
    card(l, 510, 330, 580, 100, "HISTORICAL IDENTIFIABILITY AUDIT", ["Which quantities are consistently observable across seasons?"], accent=CYAN)
    arrow(l, 650, 430, 380, 510); arrow(l, 950, 430, 1220, 510)
    card(l, 90, 510, 580, 170, "OPPORTUNITY PROCESS  P(H | Q)", ["NOT RELIABLY IDENTIFIABLE", "lane state • queue entry • withdrawal • requeue • intent", "kept outside the statistical model"], accent=RED, dashed=True)
    card(l, 930, 510, 580, 170, "PERFORMANCE PROCESS  p(Δv | H = h)", ["IDENTIFIABLE CONDITIONALLY", "same-car repeats • physical state • frozen evidence", "h is supplied as a scenario, not predicted"], accent=GREEN)
    arrow(l, 1220, 680, 1220, 745); arrow(l, 380, 680, 380, 745)
    card(l, 120, 745, 520, 95, "LIVE EXTERNAL CONTEXT", ["queue • leaderboard • remaining time"], accent=ORANGE, dashed=True)
    card(l, 960, 745, 520, 95, "FINAL_V2 OUTLOOK", ["distribution of four-lap speed change"], accent=GREEN)
    arrow(l, 640, 792, 760, 792); arrow(l, 960, 792, 840, 792)
    l.append(f'<rect x="700" y="735" width="200" height="115" rx="58" fill="{CYAN}"/><text x="800" y="780" text-anchor="middle" fill="{BG}" font-family="Arial" font-size="21" font-weight="700">HUMAN</text><text x="800" y="813" text-anchor="middle" fill="{BG}" font-family="Arial" font-size="21" font-weight="700">PIT WALL</text>')
    write_svg("identifiability-system-boundary.svg", l)


def pipeline() -> None:
    l = svg_start("Evidence-to-decision-support pipeline", "Each gate preserves source authority, chronology and scientific role.")
    items = [
        ("HISTORICAL SOURCES", "official results • timing • PTSC • weather"),
        ("AUTHORITY + PROVENANCE", "field-level lineage and source class"),
        ("ATTEMPT RECONSTRUCTION", "four-lap identity and chronology"),
        ("ELIGIBILITY + QUARANTINE", "reject unresolved joins and leakage"),
        ("FROZEN TRANSITIONS", "41 same-car evidence units"),
        ("TWO MODEL LAYERS", "physical response + future track state"),
        ("MONTE CARLO", "three uncertainty sources propagated"),
        ("VALIDATION + DIAGNOSTICS", "LOYO • 2025 external • sections • wind"),
        ("OPERATIONAL PRESENTATION", "five anchors + labelled interpolation"),
        ("HUMAN DECISION CONTEXT", "live queue and competitive state remain external"),
    ]
    for i, (a, b) in enumerate(items):
        col, row = i % 5, i // 5
        x, y = 55 + col * 307, 185 + row * 315
        accent = GREEN if i in (4, 5, 6) else ORANGE if i in (8, 9) else CYAN
        card(l, x, y, 265, 155, a, [b], accent=accent)
        if col < 4:
            arrow(l, x + 265, y + 78, x + 300, y + 78)
    arrow(l, 1380, 340, 1380, 450)
    l.append(f'<path d="M1380 450 L115 450 L115 500" stroke="{CYAN}" stroke-width="3" fill="none" marker-end="url(#a)"/>')
    write_svg("evidence-engineering-pipeline.svg", l)


def evidence_products() -> None:
    l = svg_start("Evidence products, not one homogeneous dataset", "Verified counts branch into different scientific roles.")
    card(l, 100, 190, 420, 150, "OBSERVED TRACK STATE", ["168 temperature observations", "2020–2024 structured PTSC evidence"], accent=CYAN)
    card(l, 590, 190, 420, 150, "QUALIFYING PERFORMANCE", ["41 evidence-qualified transitions", "same-car, complete four-lap attempts"], accent=GREEN)
    card(l, 1080, 190, 420, 150, "EXTERNAL REGIME", ["15 eligible 2025 cases", "held outside frozen 2020–2024 core"], accent=ORANGE)
    arrow(l, 310, 340, 500, 470); arrow(l, 800, 340, 800, 470); arrow(l, 1290, 340, 1100, 470)
    card(l, 350, 470, 420, 165, "FUTURE-STATE INTERFACE", ["656 current–future pairs", "15 / 30 / 60 / 90 / 120 min", "predicts physical state, not opportunity"], accent=CYAN)
    card(l, 830, 470, 420, 165, "RESPONSE INTERFACE", ["39 / 41 section-linked", "9 dependent sections per linked transition", "diagnostic evidence, no sample inflation"], accent=GREEN)
    arrow(l, 560, 635, 690, 735); arrow(l, 1040, 635, 910, 735)
    card(l, 565, 735, 470, 100, "CONDITIONAL PREDICTIVE DISTRIBUTION", ["p(Δv | H = h) with explicit uncertainty"], accent=ORANGE)
    write_svg("evidence-products-and-attrition.svg", l)


def hierarchy() -> None:
    l = svg_start("Evidence hierarchy and quarantine", "Numerical availability alone does not establish modelling eligibility.")
    tiers = [
        ("PRIMARY MODELLING EVIDENCE", "Complete official four-lap attempts", GREEN, 180),
        ("SECONDARY MECHANISM EVIDENCE", "Section and trap measures from completed attempts", CYAN, 330),
        ("RECONSTRUCTION-ONLY EVIDENCE", "Partial laps, waved-off runs and incomplete traces", ORANGE, 480),
        ("QUARANTINED", "Unresolved identity, chronology or environmental linkage", RED, 630),
    ]
    for title, body, color, y in tiers:
        w = 1250 - (y - 180) // 2
        x = (1600 - w) // 2
        card(l, x, y, w, 110, title, [body], accent=color, dashed=color == RED)
    write_svg("evidence-hierarchy.svg", l)


def same_car() -> None:
    l = svg_start("Why same-car transitions are the modelling unit", "Differencing reduces persistent car/driver/configuration variation without erasing latent run state.")
    card(l, 100, 210, 620, 230, "RETAINED DESIGN", ["CAR A • ATTEMPT 1  →  CAR A • ATTEMPT 2", "Δ four-lap speed", "Δ track temperature + Δ ambient temperature", "persistent identity is held closer to constant"], accent=GREEN)
    card(l, 880, 210, 620, 230, "REJECTED COMPARISON", ["CAR A  →  CAR B  →  CAR C", "car, driver, setup and preparation all change", "cross-car order can confound environment", "not used as the core response design"], accent=RED, dashed=True)
    card(l, 300, 570, 1000, 175, "WHAT DIFFERENCING DOES NOT REMOVE", ["tyre preparation • setup changes • execution • wind exposure • latent vehicle state", "These remain in empirical attempt-level residual uncertainty."], accent=ORANGE)
    write_svg("same-car-transition-design.svg", l)


def physical_model() -> None:
    l = svg_start("Frozen physical-response model", "Verified FINAL_V2 coefficients; zero intercept preserves the physical contribution boundary.")
    card(l, 100, 250, 390, 125, "Δ TRACK TEMPERATURE", ["βtrack = −0.034825 mph / °C"], accent=CYAN)
    card(l, 100, 500, 390, 125, "Δ AMBIENT TEMPERATURE", ["βambient = +0.182393 mph / °C"], accent=CYAN)
    arrow(l, 490, 312, 680, 410); arrow(l, 490, 562, 680, 465)
    card(l, 680, 350, 500, 180, "ZERO-INTERCEPT RESPONSE", ["Δvphysical = βtrack ΔTtrack + βambient ΔTambient", "paired bootstrap preserves coefficient dependence", "41 same-car transitions"], accent=GREEN)
    arrow(l, 1180, 440, 1350, 440)
    card(l, 1350, 365, 190, 150, "OUTPUT", ["Δvphysical", "not realised total Δv"], accent=ORANGE)
    card(l, 420, 700, 760, 100, "INVARIANCE", ["ΔTtrack = 0 and ΔTambient = 0  ⇒  modelled physical contribution = 0"], accent=GREEN)
    write_svg("frozen-physical-response.svg", l)


def future_track() -> None:
    l = svg_start("Future track state is modelled separately", "Future track temperature is not treated as future ambient temperature.")
    inputs = ["current track temperature", "current ambient temperature", "track − ambient thermal gap", "future ambient trajectory", "mean solar elevation", "horizon h"]
    for i, text in enumerate(inputs):
        y = 170 + i * 105
        card(l, 90, y, 470, 75, text.upper(), [""], accent=CYAN)
        arrow(l, 560, y + 38, 760, 440)
    card(l, 760, 315, 500, 250, "M2b HORIZON-SPECIFIC MODEL", ["one fitted model per scientific anchor", "future ambient change + thermal gap + solar state", "finite-sample conformal residual calibration", "leave-one-year-out selection"], accent=GREEN)
    arrow(l, 1260, 440, 1370, 440)
    card(l, 1370, 350, 170, 180, "OUTPUT", ["distribution of", "ΔTtrack(h)"], accent=ORANGE)
    write_svg("future-track-state-model.svg", l)


def uncertainty() -> None:
    l = svg_start("Three propagated uncertainty sources", "The empirical attempt-level residual dominates predictive width.")
    sources = [
        ("PHYSICAL COEFFICIENTS", "5,000 paired bootstrap draws", CYAN),
        ("FUTURE TRACK STATE", "horizon-specific calibrated residuals", GREEN),
        ("UNEXPLAINED PERFORMANCE", "symmetrized out-of-year residuals", ORANGE),
    ]
    for i, (title, body, color) in enumerate(sources):
        x = 70 + i * 510
        card(l, x, 210, 440, 150, title, [body], accent=color)
        arrow(l, x + 220, 360, 800, 520)
    l.append(f'<circle cx="800" cy="570" r="105" fill="{PANEL}" stroke="{CYAN}" stroke-width="4"/><text x="800" y="560" text-anchor="middle" fill="{INK}" font-family="Arial" font-size="26" font-weight="700">MONTE CARLO</text><text x="800" y="600" text-anchor="middle" fill="{MUTED}" font-family="Arial" font-size="19">joint propagation</text>')
    arrow(l, 800, 675, 800, 735)
    card(l, 470, 735, 660, 100, "PREDICTIVE OUTPUT", ["E[Δv] • median • 80% / 90% intervals • P(Δv > 0)"], accent=GREEN)
    write_svg("three-source-uncertainty.svg", l)


def horizons() -> None:
    l = svg_start("Scientific support versus operational display", "Five calibrated anchors; intermediate minutes are labelled presentation interpolation.")
    x0, x1, y = 160, 1450, 420
    l.append(f'<line x1="{x0}" y1="{y}" x2="{x1}" y2="{y}" stroke="{GRID}" stroke-width="12" stroke-linecap="round"/>')
    for h in [0, 15, 30, 60, 90, 120]:
        x = x0 + (x1 - x0) * h / 120
        color = ORANGE if h == 0 else GREEN
        r = 19 if h == 0 else 24
        l.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{color}"/><text x="{x}" y="{y-52}" text-anchor="middle" fill="{INK}" font-family="Arial" font-size="25" font-weight="700">{h}</text>')
        label = "CURRENT_STATE_BOUNDARY" if h == 0 else "CALIBRATED_ANCHOR"
        l.append(f'<text x="{x}" y="{y+70}" text-anchor="middle" fill="{color}" font-family="Arial" font-size="15" font-weight="700">{label}</text>')
    l.append(f'<rect x="315" y="575" width="1050" height="95" rx="16" fill="{PANEL}" stroke="{CYAN}" stroke-width="2" stroke-dasharray="10 8"/><text x="840" y="615" text-anchor="middle" fill="{CYAN}" font-family="Arial" font-size="21" font-weight="700">INTERPOLATED_OPERATIONAL</text><text x="840" y="646" text-anchor="middle" fill="{MUTED}" font-family="Arial" font-size="18">1-minute display resolution does not create new calibration evidence</text>')
    write_svg("calibrated-horizon-boundary.svg", l)


def timeline() -> None:
    l = svg_start("Technical regime and operational applicability", "Coefficient compatibility and qualifying-format applicability are separate questions.")
    items = [
        ("2018–2019", "PRE-AEROSCREEN", "2019: 10 direct transitions", CYAN),
        ("2020–2024", "FROZEN REFERENCE ERA", "41 transitions • FINAL_V2", GREEN),
        ("2025", "AEROSCREEN + HYBRID", "23 direct physics transitions • 15 external cases", ORANGE),
        ("2026", "FORMAT BOUNDARY", "structurally no same-day initial-round repeats", RED),
    ]
    for i, (year, title, body, color) in enumerate(items):
        x = 70 + i * 385
        card(l, x, 300, 345, 230, year, [title, body], accent=color, dashed=color == RED)
        if i < 3:
            arrow(l, x + 345, 415, x + 375, 415)
    card(l, 270, 650, 1060, 100, "INTERPRETATION", ["Directionally compatible evidence across regimes; coefficient invariance is not established."], accent=ORANGE)
    write_svg("technical-regime-timeline.svg", l)


def freeze() -> None:
    l = svg_start("Freeze and reproducibility discipline", "Later evidence is evaluated externally and cannot silently alter FINAL_V2.")
    card(l, 100, 230, 400, 180, "DATASET FREEZE", ["41 same-car transitions", "provenance + eligibility gates", "quarantined evidence remains separate"], accent=GREEN)
    card(l, 600, 230, 400, 180, "MODEL FREEZE", ["FINAL_V2 scientific anchors", "SHA-256 manifests", "deterministic Monte Carlo inputs"], accent=GREEN)
    card(l, 1100, 230, 400, 180, "EXTERNAL EVIDENCE", ["2025 held out", "R6 regime extension", "no silent pooling into training"], accent=ORANGE)
    arrow(l, 500, 320, 600, 320); arrow(l, 1000, 320, 1100, 320)
    card(l, 350, 590, 900, 145, "REPRODUCIBLE PRESENTATION LAYER", ["semantic figure generator • link/claim tests • frozen-output verification", "presentation code reads frozen artefacts; it does not refit the model"], accent=CYAN)
    write_svg("freeze-and-reproducibility.svg", l)


def style_axes(ax: plt.Axes) -> None:
    ax.set_facecolor(PANEL)
    for spine in ax.spines.values():
        spine.set_color(GRID)
    ax.tick_params(colors=MUTED)
    ax.xaxis.label.set_color(MUTED); ax.yaxis.label.set_color(MUTED)
    ax.title.set_color(INK)
    ax.grid(axis="y", color=GRID, alpha=.65)


def savefig(fig: plt.Figure, name: str) -> None:
    fig.patch.set_facecolor(BG)
    fig.savefig(OUT / name, dpi=180, bbox_inches="tight", facecolor=BG)
    plt.close(fig)


def section_plot() -> None:
    df = pd.read_csv(ROOT / "weather/output/v2b_section_mechanism/v2b_transition_section_mechanism_metrics_v1.csv")
    thresholds = [0, .1, .2, .5]
    means, ns = [], []
    for threshold in thresholds:
        subset = df[df["delta_four_lap_average_speed_mph"].abs() >= threshold]
        means.append(subset["direction_coherence"].mean())
        ns.append(len(subset))
    fig, ax = plt.subplots(figsize=(10.5, 5.8))
    style_axes(ax)
    bars = ax.bar(range(4), means, color=[CYAN, CYAN, GREEN, GREEN], width=.62)
    ax.set_ylim(0, 1.05); ax.set_ylabel("Mean section-direction coherence")
    ax.set_xticks(range(4), ["All", "|Δv| ≥ 0.10", "|Δv| ≥ 0.20", "|Δv| ≥ 0.50"])
    ax.set_title("Section evidence supports a spatially coherent mechanism", loc="left", fontsize=17, fontweight="bold", color=INK)
    for b, n, value in zip(bars, ns, means):
        ax.text(b.get_x()+b.get_width()/2, value+.035, f"{value:.3f}\nn={n}", ha="center", color=INK, fontsize=10)
    ax.text(0, -.20, "39 / 41 frozen transitions linked; nine sections per transition are dependent diagnostics, not 351 training rows.", transform=ax.transAxes, color=MUTED, fontsize=10)
    savefig(fig, "section-mechanism-coherence.png")


def wind_plot() -> None:
    labels = ["Δ wind speed", "Δ gust", "Wind-vector change", "Mean wind speed", "Mean gust"]
    values = [-.031890, .199002, .208751, .028497, .060187]
    fig, ax = plt.subplots(figsize=(10.5, 5.8)); style_axes(ax)
    y = np.arange(len(labels)); colors = [RED if abs(v) < .1 else ORANGE for v in values]
    ax.barh(y, values, color=colors); ax.axvline(0, color=MUTED, lw=1)
    ax.set_yticks(y, labels); ax.invert_yaxis(); ax.set_xlim(-.25, .25)
    ax.set_xlabel("Partial Spearman ρ controlling |Δ speed|")
    ax.set_title("Historical wind proxies were not stable enough for production", loc="left", fontsize=17, fontweight="bold", color=INK)
    for yi, v in zip(y, values):
        ax.text(v + (.008 if v >= 0 else -.008), yi, f"{v:+.3f}", va="center", ha="left" if v >= 0 else "right", color=INK)
    ax.text(0, -.18, "Wind remains physically relevant; fixed-point/gridded historical proxies do not justify a deterministic production term.", transform=ax.transAxes, color=MUTED, fontsize=10)
    savefig(fig, "wind-residual-diagnostic.png")


def regime_plot() -> None:
    coeff = pd.read_csv(ROOT / "r6_regime_extension/output/r6_regime_physics_comparison_v1/r6_regime_physics_coefficients_v1.csv")
    boot = pd.read_csv(ROOT / "r6_regime_extension/output/r6_regime_physics_comparison_v1/r6_regime_physics_bootstrap_intervals_v1.csv")
    h = coeff[coeff["model"].isin(["HUBER_IRLS_NO_INTERCEPT", "FROZEN_R5_2_ROBUST_CORE"])].copy()
    order = ["A", "B", "C"]
    names = ["2019\npre-Aeroscreen\nn=10", "2020–24\nfrozen reference\nn=41", "2025\nhybrid\nn=23"]
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 5.6))
    for ax, column, title in zip(axes, ["beta_track_mph_per_c", "beta_ambient_mph_per_c"], ["Track-temperature coefficient", "Ambient-temperature coefficient"]):
        style_axes(ax)
        for i, regime in enumerate(order):
            row = h[h.regime_code == regime].iloc[0]
            val = row[column]
            bname = "beta_track_mph_per_c" if "track" in column else "beta_ambient_mph_per_c"
            interval = boot[(boot.regime_code == regime) & (boot.coefficient == bname)]
            if interval.empty:
                ax.scatter(i, val, s=85, color=GREEN, zorder=3)
                ax.text(i, val, "  frozen point", color=MUTED, va="center", fontsize=9)
            else:
                lo, hi = interval.iloc[0][["p05", "p95"]]
                ax.errorbar(i, val, yerr=[[val-lo], [hi-val]], fmt="o", color=CYAN if regime == "A" else ORANGE, capsize=7, lw=2.2)
        ax.axhline(0, color=MUTED, lw=1); ax.set_xticks(range(3), names); ax.set_title(title, loc="left", fontsize=15, fontweight="bold", color=INK); ax.set_ylabel("mph / °C")
    fig.suptitle("Regime evidence is directionally compatible, not proof of invariant coefficients", color=INK, fontsize=18, fontweight="bold", x=.05, ha="left")
    fig.text(.05, -.03, "90% cluster-bootstrap intervals shown for 2019 and 2025; the frozen 2020–2024 reference is plotted as a point only.", color=MUTED, fontsize=10)
    savefig(fig, "regime-coefficient-comparison.png")


def copy_frozen_plots() -> None:
    mapping = {
        "figures/figure4_future_track_model_selection.png": "future-track-model-selection.png",
        "figures/figure6_uncertainty_ablation.png": "uncertainty-source-ablation.png",
        "figures/figure7_v2e_120min_stress_test.png": "scenario-stress-test-120min.png",
        "figures/figure8_external_2025_validation.png": "external-validation-2025.png",
        "figures/figure8_external_2025_supported_120min.png": "external-validation-2025-supported.png",
        "figures/figure9a_operational_performance_curve.png": "operational-performance-outlook.png",
        "figures/figure9b_probability_improvement_curve.png": "operational-probability-outlook.png",
    }
    for src, dst in mapping.items():
        shutil.copy2(ROOT / src, OUT / dst)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for fn in [identifiability, pipeline, evidence_products, hierarchy, same_car, physical_model, future_track, uncertainty, horizons, timeline, freeze, section_plot, wind_plot, regime_plot, copy_frozen_plots]:
        fn()
    print(f"Generated {len(list(OUT.iterdir()))} curated figures in {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
