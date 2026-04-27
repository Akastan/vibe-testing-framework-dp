"""
Generátor grafů pro Vibe Testing Framework v12.

Výstup je organizován do tří složek podle výzkumných otázek:
  * charts_rq1/  — závislost kvality testů na úrovni kontextu (1 křivka = průměr 3 LLM)
  * charts_rq2/  — závislost strukturálního pokrytí na úrovni kontextu (1 křivka = průměr 3 LLM)
  * charts_rq3/  — mezimodelové srovnání (3 křivky, jedna per LLM)

Všechny grafy jsou v "labeled" verzi (s tituly, popisky os, legendou, číselnými anotacemi).
"""
import json
from pathlib import Path
from collections import defaultdict, Counter
from statistics import mean, stdev

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

# ─── CONFIG ─────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
RQ1_DIR = BASE_DIR / "v12/charts_rq1"
RQ2_DIR = BASE_DIR / "v12/charts_rq2"
RQ3_DIR = BASE_DIR / "v12/charts_rq3"
for d in (RQ1_DIR, RQ2_DIR, RQ3_DIR):
    d.mkdir(exist_ok=True)

# Barvy
COLOR_DEEPSEEK = "#4C72B0"
COLOR_GEMINI = "#DD8452"
COLOR_MISTRAL = "#55A467"
COLOR_DEEPSEEK_V4 = "#8172B2"
COLOR_CLAUDE = "#C44E52"
COLOR_AVG = "#333333"  # tmavě šedá pro cross-model průměr

LEVEL_COLORS = ["#4C72B0", "#DD8452", "#55A467", "#C44E52", "#8172B2"]
HEATMAP_CMAP = "RdYlGn"
DIVERGING_CMAP = "RdBu_r"
SEQUENTIAL_CMAP = "viridis"

DPI = 140
FIGSIZE_SMALL = (6, 4)
FIGSIZE_MED = (8, 5)
FIGSIZE_WIDE = (10, 5)
FIGSIZE_TALL = (8, 6)
FIGSIZE_SQUARE = (6, 6)

FILES = {
    "deepseek-chat": "v12/outputs_v12_deepseek-chat/results/experiment_diplomka_v12_20260415_165515.json",
    #"gemini-3.1-flash-lite-preview": "v12/outputs_v12_gemini/results/experiment_diplomka_v12_20260416_073106.json",
    "deepseek-v4-flash": "v12/outputs_v12_deepseek-V4/results/experiment_diplomka_v12_20260426_220445.json",
    "mistral-large-2512": "v12/outputs_v12_mistral/results/experiment_diplomka_v12_20260415_220449.json",
    "claude-haiku-4-5-20251001": "v12/outputs_v12_claude/results/experiment_diplomka_v12_20260424_160040.json",
}

LEVELS = ["L0", "L1", "L2", "L3", "L4"]
LLMS = list(FILES.keys())
LLM_SHORT = {
    "deepseek-chat": "DeepSeek-chat",
    #"gemini-3.1-flash-lite-preview": "Gemini",
    "deepseek-v4-flash": "DeepSeek-V4",
    "mistral-large-2512": "Mistral",
    "claude-haiku-4-5-20251001": "Claude Haiku"
}
LLM_COLORS = {
    "deepseek-chat": COLOR_DEEPSEEK,
    #"gemini-3.1-flash-lite-preview": COLOR_GEMINI,
    "mistral-large-2512": COLOR_MISTRAL,
    "deepseek-v4-flash": COLOR_DEEPSEEK_V4,
    "claude-haiku-4-5-20251001": COLOR_CLAUDE,
}

# Code coverage z analytických reportů
COVERAGE = {
    "deepseek-chat": {
        "L0": {"total": 68.15, "crud": 39.28, "main": 70.61},
        "L1": {"total": 74.45, "crud": 56.43, "main": 69.66},
        "L2": {"total": 73.70, "crud": 54.83, "main": 69.19},
        "L3": {"total": 73.12, "crud": 53.75, "main": 68.64},
        "L4": {"total": 73.50, "crud": 53.18, "main": 70.68},
    },
    #"gemini-3.1-flash-lite-preview": {
    #    "L0": {"total": 62.32, "crud": 28.32, "main": 65.04},
    #    "L1": {"total": 68.46, "crud": 40.93, "main": 69.53},
    #    "L2": {"total": 68.74, "crud": 41.40, "main": 69.87},
    #    "L3": {"total": 67.89, "crud": 40.05, "main": 68.71},
    #    "L4": {"total": 65.87, "crud": 35.45, "main": 67.83},
    #},
    "mistral-large-2512": {
        "L0": {"total": 66.86, "crud": 36.64, "main": 69.66},
        "L1": {"total": 66.54, "crud": 37.21, "main": 67.83},
        "L2": {"total": 67.99, "crud": 39.17, "main": 70.21},
        "L3": {"total": 67.05, "crud": 37.14, "main": 69.64},
        "L4": {"total": 67.77, "crud": 39.59, "main": 68.91},
    },
    "deepseek-v4-flash": {
        "L0": {"total": 70.90, "crud": 45.37, "main": 72.04},
        "L1": {"total": 71.97, "crud": 48.84, "main": 71.16},
        "L2": {"total": 69.61, "crud": 44.70, "main": 68.51},
        "L3": {"total": 71.89, "crud": 49.56, "main": 69.93},
        "L4": {"total": 68.64, "crud": 43.67, "main": 66.53},
    },
    "claude-haiku-4-5-20251001": {
        "L0": {"total": 67.97, "crud": 40.72, "main": 68.10},
        "L1": {"total": 65.63, "crud": 35.86, "main": 66.47},
        "L2": {"total": 65.71, "crud": 35.60, "main": 67.08},
        "L3": {"total": 66.18, "crud": 36.07, "main": 68.10},
        "L4": {"total": 66.98, "crud": 38.04, "main": 68.23},
    },
}


# ─── DATA LOADING & EXTRACTION ──────────────────────────────────────────────
def load_runs():
    all_runs = []
    for llm, fname in FILES.items():
        with open(BASE_DIR / fname, encoding="utf-8") as fh:
            data = json.load(fh)
        for run in data:
            all_runs.append(extract(run))
    return all_runs


def extract(run):
    m = run["metrics"]
    slim = run.get("token_usage_slim", {})
    tu = run.get("token_usage", {})
    per_phase = tu.get("per_phase", {})
    dist = m["test_type_distribution"]["distribution"]

    def _pct(k):
        v = dist.get(k, 0)
        return v.get("pct", 0) if isinstance(v, dict) else 0

    def _cnt(k):
        v = dist.get(k, 0)
        return v.get("count", 0) if isinstance(v, dict) else 0

    llm = run["llm"]
    lvl = run["level"]
    return {
        "llm": llm,
        "level": lvl,
        "run_id": run["run_id"],
        "validity_pct": m["test_validity"]["validity_rate_pct"],
        "tests_passed": m["test_validity"]["tests_passed"],
        "tests_failed": m["test_validity"]["tests_failed"],
        "tests_errors": m["test_validity"]["tests_errors"],
        "total_executed": m["test_validity"]["total_executed"],
        "assertion_depth": m["assertion_depth"]["assertion_depth"],
        "total_assertions": m["assertion_depth"]["total_assertions"],
        "response_validation_pct": m["response_validation"]["response_validation_pct"],
        "happy_pct": _pct("happy_path"),
        "error_pct": _pct("error"),
        "edge_pct": _pct("edge_case"),
        "happy_cnt": _cnt("happy_path"),
        "error_cnt": _cnt("error"),
        "edge_cnt": _cnt("edge_case"),
        "diversity_count": m["status_code_diversity"]["diversity_count"],
        "status_code_dist": m["status_code_diversity"].get("code_distribution", {}),
        "endpoint_coverage_pct": m["endpoint_coverage"]["endpoint_coverage_pct"],
        "covered_endpoints": m["endpoint_coverage"]["covered_endpoints"],
        "uncovered_endpoints": m["endpoint_coverage"]["uncovered_endpoints"],
        "avg_test_lines": m["avg_test_length"]["avg_lines"],
        "adherence_pct": m["plan_adherence"]["adherence_pct"],
        "stale_count": m["stale_tests"]["stale_count"],
        "stale_names": m["stale_tests"].get("stale_names", []),
        "iterations": run["iterations_used"],
        "elapsed_s": run["elapsed_seconds"],
        "all_passed": run["all_tests_passed"],
        "early_stopped": run["early_stopped"],
        "cost_usd": slim.get("cost_total_usd", 0),
        "total_tokens": slim.get("total_tokens", 0),
        "prompt_tokens": slim.get("prompt_tokens", 0),
        "completion_tokens": slim.get("completion_tokens", 0),
        "cached_tokens": slim.get("cached_tokens", 0),
        "token_efficiency": m["token_efficiency"]["score"],
        "compression_savings_pct": run["compression"]["savings_pct"],
        "context_tokens": run["compression"]["compressed_est_tokens"],
        "phase_planning": per_phase.get("planning", {}).get("total_tokens", 0),
        "phase_generation": per_phase.get("generation", {}).get("total_tokens", 0),
        "phase_repair": per_phase.get("repair", {}).get("total_tokens", 0),
        "failure_cats": run["diagnostics"]["failure_taxonomy"].get("categories", {}),
        "total_failures": run["diagnostics"]["failure_taxonomy"].get("total_failures", 0),
        "code_cov_total": COVERAGE[llm][lvl]["total"],
        "code_cov_crud": COVERAGE[llm][lvl]["crud"],
        "code_cov_main": COVERAGE[llm][lvl]["main"],
    }


# ─── HELPERS ────────────────────────────────────────────────────────────────
def model_level_matrix(runs, key):
    """Returns dict[llm][level] = mean over 5 runs."""
    groups = defaultdict(list)
    for r in runs:
        groups[(r["llm"], r["level"])].append(r[key])
    return {llm: {lvl: mean(groups[(llm, lvl)]) for lvl in LEVELS} for llm in LLMS}


def level_cross_avg(runs, key):
    """Average ACROSS all 3 models by level — used for RQ1/RQ2 single-curve charts."""
    m = model_level_matrix(runs, key)
    return {lvl: mean(m[llm][lvl] for llm in LLMS) for lvl in LEVELS}


def level_cross_std(runs, key):
    """Standard deviation across models per level — for error bars on RQ1/RQ2."""
    m = model_level_matrix(runs, key)
    return {lvl: stdev([m[llm][lvl] for llm in LLMS]) for lvl in LEVELS}


def save_fig(fig, filename, out_dir):
    fig.tight_layout()
    fig.savefig(out_dir / filename, dpi=DPI, bbox_inches="tight")
    plt.close(fig)


def decorate_chart(ax, title="", xlabel="", ylabel="", legend=True):
    if title:
        ax.set_title(title, fontsize=11, pad=10)
    if xlabel:
        ax.set_xlabel(xlabel, fontsize=10)
    if ylabel:
        ax.set_ylabel(ylabel, fontsize=10)
    if legend and ax.get_legend_handles_labels()[0]:
        ax.legend(fontsize=8, frameon=True, framealpha=0.9)
    ax.grid(True, linestyle="--", linewidth=0.4, alpha=0.5)


# ═══════════════════════════════════════════════════════════════════════════
# RQ1 — Validita, kvalita a testovací strategie (1 křivka = průměr 3 LLM)
# ═══════════════════════════════════════════════════════════════════════════

def rq1_01_line_validity(runs):
    """Validity vs kontext — jedna křivka (avg 3 LLM) + error band."""
    avg = level_cross_avg(runs, "validity_pct")
    std = level_cross_std(runs, "validity_pct")
    fig, ax = plt.subplots(figsize=FIGSIZE_MED)
    x = np.arange(len(LEVELS))
    ys = [avg[l] for l in LEVELS]
    stds = [std[l] for l in LEVELS]
    ax.plot(x, ys, marker="o", linewidth=2.5, color=COLOR_AVG, label="Průměr 3 LLM")
    ax.fill_between(x, [y - s for y, s in zip(ys, stds)], [y + s for y, s in zip(ys, stds)],
                    alpha=0.18, color=COLOR_AVG, label="± 1σ")
    for i, v in enumerate(ys):
        ax.text(i, v + 0.4, f"{v:.1f}", ha="center", fontsize=9)
    ax.set_xticks(x); ax.set_xticklabels(LEVELS)
    decorate_chart(ax, "RQ1 — Validity Rate vs. úroveň kontextu",
                   "Úroveň kontextu", "Validity (%)")
    save_fig(fig, "01_line_validity.png", RQ1_DIR)


def rq1_02_line_assertion_depth(runs):
    avg = level_cross_avg(runs, "assertion_depth")
    std = level_cross_std(runs, "assertion_depth")
    fig, ax = plt.subplots(figsize=FIGSIZE_MED)
    x = np.arange(len(LEVELS))
    ys = [avg[l] for l in LEVELS]
    stds = [std[l] for l in LEVELS]
    ax.plot(x, ys, marker="o", linewidth=2.5, color=COLOR_AVG)
    ax.fill_between(x, [y - s for y, s in zip(ys, stds)], [y + s for y, s in zip(ys, stds)],
                    alpha=0.18, color=COLOR_AVG)
    for i, v in enumerate(ys):
        ax.text(i, v + 0.05, f"{v:.2f}", ha="center", fontsize=9)
    ax.set_xticks(x); ax.set_xticklabels(LEVELS)
    decorate_chart(ax, "RQ1 — Assertion Depth vs. úroveň kontextu",
                   "Úroveň kontextu", "Počet asercí na test", legend=False)
    save_fig(fig, "02_line_assertion_depth.png", RQ1_DIR)


def rq1_03_line_response_validation(runs):
    avg = level_cross_avg(runs, "response_validation_pct")
    std = level_cross_std(runs, "response_validation_pct")
    fig, ax = plt.subplots(figsize=FIGSIZE_MED)
    x = np.arange(len(LEVELS))
    ys = [avg[l] for l in LEVELS]
    stds = [std[l] for l in LEVELS]
    ax.plot(x, ys, marker="o", linewidth=2.5, color=COLOR_AVG)
    ax.fill_between(x, [y - s for y, s in zip(ys, stds)], [y + s for y, s in zip(ys, stds)],
                    alpha=0.18, color=COLOR_AVG)
    for i, v in enumerate(ys):
        ax.text(i, v + 1.2, f"{v:.1f}", ha="center", fontsize=9)
    ax.set_xticks(x); ax.set_xticklabels(LEVELS)
    decorate_chart(ax, "RQ1 — Response Validation vs. úroveň kontextu",
                   "Úroveň kontextu", "Response Validation (%)", legend=False)
    save_fig(fig, "03_line_response_validation.png", RQ1_DIR)


def rq1_04_line_diversity(runs):
    avg = level_cross_avg(runs, "diversity_count")
    std = level_cross_std(runs, "diversity_count")
    fig, ax = plt.subplots(figsize=FIGSIZE_MED)
    x = np.arange(len(LEVELS))
    ys = [avg[l] for l in LEVELS]
    stds = [std[l] for l in LEVELS]
    ax.plot(x, ys, marker="o", linewidth=2.5, color=COLOR_AVG)
    ax.fill_between(x, [y - s for y, s in zip(ys, stds)], [y + s for y, s in zip(ys, stds)],
                    alpha=0.18, color=COLOR_AVG)
    for i, v in enumerate(ys):
        ax.text(i, v + 0.1, f"{v:.2f}", ha="center", fontsize=9)
    ax.set_xticks(x); ax.set_xticklabels(LEVELS)
    decorate_chart(ax, "RQ1 — Status Code Diversity vs. úroveň kontextu",
                   "Úroveň kontextu", "Počet unikátních status kódů", legend=False)
    save_fig(fig, "04_line_status_diversity.png", RQ1_DIR)


def rq1_05_bar_validity(runs):
    avg = level_cross_avg(runs, "validity_pct")
    fig, ax = plt.subplots(figsize=FIGSIZE_MED)
    x = np.arange(len(LEVELS))
    ys = [avg[l] for l in LEVELS]
    bars = ax.bar(x, ys, color=LEVEL_COLORS, edgecolor="black", linewidth=0.5, alpha=0.85)
    for b, v in zip(bars, ys):
        ax.text(b.get_x() + b.get_width()/2, v + 0.4, f"{v:.1f}", ha="center", fontsize=9)
    ax.set_xticks(x); ax.set_xticklabels(LEVELS); ax.set_ylim(0, 105)
    decorate_chart(ax, "RQ1 — Validity Rate (sloupcový graf)",
                   "Úroveň kontextu", "Validity (%)", legend=False)
    save_fig(fig, "05_bar_validity.png", RQ1_DIR)


def rq1_06_bar_assertion_depth(runs):
    avg = level_cross_avg(runs, "assertion_depth")
    fig, ax = plt.subplots(figsize=FIGSIZE_MED)
    x = np.arange(len(LEVELS))
    ys = [avg[l] for l in LEVELS]
    bars = ax.bar(x, ys, color=LEVEL_COLORS, edgecolor="black", linewidth=0.5, alpha=0.85)
    for b, v in zip(bars, ys):
        ax.text(b.get_x() + b.get_width()/2, v + 0.04, f"{v:.2f}", ha="center", fontsize=9)
    ax.set_xticks(x); ax.set_xticklabels(LEVELS)
    decorate_chart(ax, "RQ1 — Assertion Depth (sloupcový graf)",
                   "Úroveň kontextu", "Počet asercí na test", legend=False)
    save_fig(fig, "06_bar_assertion_depth.png", RQ1_DIR)


def rq1_07_bar_response_validation(runs):
    avg = level_cross_avg(runs, "response_validation_pct")
    fig, ax = plt.subplots(figsize=FIGSIZE_MED)
    x = np.arange(len(LEVELS))
    ys = [avg[l] for l in LEVELS]
    bars = ax.bar(x, ys, color=LEVEL_COLORS, edgecolor="black", linewidth=0.5, alpha=0.85)
    for b, v in zip(bars, ys):
        ax.text(b.get_x() + b.get_width()/2, v + 1, f"{v:.1f}", ha="center", fontsize=9)
    ax.set_xticks(x); ax.set_xticklabels(LEVELS); ax.set_ylim(0, 100)
    decorate_chart(ax, "RQ1 — Response Validation (sloupcový graf)",
                   "Úroveň kontextu", "Response Validation (%)", legend=False)
    save_fig(fig, "07_bar_response_validation.png", RQ1_DIR)


def rq1_08_bar_diversity(runs):
    avg = level_cross_avg(runs, "diversity_count")
    fig, ax = plt.subplots(figsize=FIGSIZE_MED)
    x = np.arange(len(LEVELS))
    ys = [avg[l] for l in LEVELS]
    bars = ax.bar(x, ys, color=LEVEL_COLORS, edgecolor="black", linewidth=0.5, alpha=0.85)
    for b, v in zip(bars, ys):
        ax.text(b.get_x() + b.get_width()/2, v + 0.1, f"{v:.2f}", ha="center", fontsize=9)
    ax.set_xticks(x); ax.set_xticklabels(LEVELS)
    decorate_chart(ax, "RQ1 — Status Code Diversity (sloupcový graf)",
                   "Úroveň kontextu", "Počet unikátních status kódů", legend=False)
    save_fig(fig, "08_bar_status_diversity.png", RQ1_DIR)


def rq1_09_box_validity(runs):
    """Boxplot — rozptyl validity per úroveň (všech 15 runů: 3 LLM × 5 runů)."""
    data = [[r["validity_pct"] for r in runs if r["level"] == lvl] for lvl in LEVELS]
    fig, ax = plt.subplots(figsize=FIGSIZE_MED)
    bp = ax.boxplot(data, tick_labels=LEVELS, patch_artist=True, widths=0.5)
    for patch, col in zip(bp["boxes"], LEVEL_COLORS):
        patch.set_facecolor(col); patch.set_alpha(0.6)
    for med in bp["medians"]:
        med.set_color("black"); med.set_linewidth(1.5)
    decorate_chart(ax, "RQ1 — Validity (boxplot, n=15 / úroveň)",
                   "Úroveň kontextu", "Validity (%)", legend=False)
    save_fig(fig, "09_box_validity.png", RQ1_DIR)


def rq1_10_box_assertion_depth(runs):
    data = [[r["assertion_depth"] for r in runs if r["level"] == lvl] for lvl in LEVELS]
    fig, ax = plt.subplots(figsize=FIGSIZE_MED)
    bp = ax.boxplot(data, tick_labels=LEVELS, patch_artist=True, widths=0.5)
    for patch, col in zip(bp["boxes"], LEVEL_COLORS):
        patch.set_facecolor(col); patch.set_alpha(0.6)
    for med in bp["medians"]:
        med.set_color("black"); med.set_linewidth(1.5)
    decorate_chart(ax, "RQ1 — Assertion Depth (boxplot, n=15 / úroveň)",
                   "Úroveň kontextu", "Assertion Depth", legend=False)
    save_fig(fig, "10_box_assertion_depth.png", RQ1_DIR)


def rq1_11_box_response_validation(runs):
    data = [[r["response_validation_pct"] for r in runs if r["level"] == lvl] for lvl in LEVELS]
    fig, ax = plt.subplots(figsize=FIGSIZE_MED)
    bp = ax.boxplot(data, tick_labels=LEVELS, patch_artist=True, widths=0.5)
    for patch, col in zip(bp["boxes"], LEVEL_COLORS):
        patch.set_facecolor(col); patch.set_alpha(0.6)
    for med in bp["medians"]:
        med.set_color("black"); med.set_linewidth(1.5)
    decorate_chart(ax, "RQ1 — Response Validation (boxplot, n=15 / úroveň)",
                   "Úroveň kontextu", "Response Validation (%)", legend=False)
    save_fig(fig, "11_box_response_validation.png", RQ1_DIR)


def rq1_12_violin_validity(runs):
    data = [[r["validity_pct"] for r in runs if r["level"] == lvl] for lvl in LEVELS]
    fig, ax = plt.subplots(figsize=FIGSIZE_MED)
    parts = ax.violinplot(data, showmeans=True, showmedians=True)
    for pc, col in zip(parts["bodies"], LEVEL_COLORS):
        pc.set_facecolor(col); pc.set_alpha(0.55)
    ax.set_xticks(range(1, len(LEVELS) + 1)); ax.set_xticklabels(LEVELS)
    decorate_chart(ax, "RQ1 — Violin plot Validity napříč úrovněmi",
                   "Úroveň kontextu", "Validity (%)", legend=False)
    save_fig(fig, "12_violin_validity.png", RQ1_DIR)


def rq1_13_violin_assertion_depth(runs):
    data = [[r["assertion_depth"] for r in runs if r["level"] == lvl] for lvl in LEVELS]
    fig, ax = plt.subplots(figsize=FIGSIZE_MED)
    parts = ax.violinplot(data, showmeans=True, showmedians=True)
    for pc, col in zip(parts["bodies"], LEVEL_COLORS):
        pc.set_facecolor(col); pc.set_alpha(0.55)
    ax.set_xticks(range(1, len(LEVELS) + 1)); ax.set_xticklabels(LEVELS)
    decorate_chart(ax, "RQ1 — Violin plot Assertion Depth napříč úrovněmi",
                   "Úroveň kontextu", "Assertion Depth", legend=False)
    save_fig(fig, "13_violin_assertion_depth.png", RQ1_DIR)


def rq1_14_hist_validity(runs):
    vals = [r["validity_pct"] for r in runs]
    fig, ax = plt.subplots(figsize=FIGSIZE_MED)
    ax.hist(vals, bins=15, color=COLOR_AVG, edgecolor="black", alpha=0.75)
    decorate_chart(ax, f"RQ1 — Histogram Validity (všech n={len(vals)} runů)",
                   "Validity (%)", "Počet runů", legend=False)
    save_fig(fig, "14_hist_validity.png", RQ1_DIR)


def rq1_15_hist_assertion_depth(runs):
    vals = [r["assertion_depth"] for r in runs]
    fig, ax = plt.subplots(figsize=FIGSIZE_MED)
    ax.hist(vals, bins=15, color=COLOR_AVG, edgecolor="black", alpha=0.75)
    decorate_chart(ax, f"RQ1 — Histogram Assertion Depth (n={len(vals)} runů)",
                   "Assertion Depth", "Počet runů", legend=False)
    save_fig(fig, "15_hist_assertion_depth.png", RQ1_DIR)


def rq1_16_hist_response_validation(runs):
    vals = [r["response_validation_pct"] for r in runs]
    fig, ax = plt.subplots(figsize=FIGSIZE_MED)
    ax.hist(vals, bins=15, color=COLOR_AVG, edgecolor="black", alpha=0.75)
    decorate_chart(ax, f"RQ1 — Histogram Response Validation (n={len(vals)} runů)",
                   "Response Validation (%)", "Počet runů", legend=False)
    save_fig(fig, "16_hist_response_validation.png", RQ1_DIR)


def rq1_17_stacked_area_test_types(runs):
    """Stacked area — vývoj distribuce happy/error/edge (cross-model avg)."""
    h = [level_cross_avg(runs, "happy_pct")[lvl] for lvl in LEVELS]
    e = [level_cross_avg(runs, "error_pct")[lvl] for lvl in LEVELS]
    d = [level_cross_avg(runs, "edge_pct")[lvl] for lvl in LEVELS]
    fig, ax = plt.subplots(figsize=FIGSIZE_MED)
    x = np.arange(len(LEVELS))
    ax.stackplot(x, h, e, d, labels=["happy_path", "error", "edge_case"],
                 colors=["#55A467", "#C44E52", "#DD8452"], alpha=0.85)
    ax.set_xticks(x); ax.set_xticklabels(LEVELS); ax.set_ylim(0, 100)
    decorate_chart(ax, "RQ1 — Distribuce typů testů napříč úrovněmi (stacked area)",
                   "Úroveň kontextu", "Podíl (%)")
    save_fig(fig, "17_stacked_area_test_types.png", RQ1_DIR)


def rq1_18_stacked_bar_test_types(runs):
    h = [level_cross_avg(runs, "happy_pct")[lvl] for lvl in LEVELS]
    e = [level_cross_avg(runs, "error_pct")[lvl] for lvl in LEVELS]
    d = [level_cross_avg(runs, "edge_pct")[lvl] for lvl in LEVELS]
    fig, ax = plt.subplots(figsize=FIGSIZE_MED)
    x = np.arange(len(LEVELS))
    ax.bar(x, h, color="#55A467", label="happy_path")
    ax.bar(x, e, bottom=h, color="#C44E52", label="error")
    ax.bar(x, d, bottom=[hi + ei for hi, ei in zip(h, e)], color="#DD8452", label="edge_case")
    for i, (hi, ei, di) in enumerate(zip(h, e, d)):
        ax.text(i, hi/2, f"{hi:.0f}", ha="center", fontsize=8, color="white", weight="bold")
        ax.text(i, hi + ei/2, f"{ei:.0f}", ha="center", fontsize=8, color="white", weight="bold")
        if di > 3:
            ax.text(i, hi + ei + di/2, f"{di:.0f}", ha="center", fontsize=8, color="white", weight="bold")
    ax.set_xticks(x); ax.set_xticklabels(LEVELS); ax.set_ylim(0, 100)
    decorate_chart(ax, "RQ1 — Distribuce typů testů (stacked bar)",
                   "Úroveň kontextu", "Podíl (%)")
    save_fig(fig, "18_stacked_bar_test_types.png", RQ1_DIR)


def rq1_19_pie_test_types_per_level(runs):
    """5× koláč — distribuce testů per úroveň."""
    for lvl in LEVELS:
        vals = {
            "happy_path": mean(r["happy_pct"] for r in runs if r["level"] == lvl),
            "error":      mean(r["error_pct"] for r in runs if r["level"] == lvl),
            "edge_case":  mean(r["edge_pct"] for r in runs if r["level"] == lvl),
        }
        fig, ax = plt.subplots(figsize=FIGSIZE_SQUARE)
        sizes = list(vals.values())
        colors = ["#55A467", "#C44E52", "#DD8452"]
        ax.pie(sizes, labels=list(vals.keys()), autopct="%1.1f%%",
               colors=colors, wedgeprops=dict(width=0.55, edgecolor="white"))
        ax.set_title(f"RQ1 — Distribuce typů testů na úrovni {lvl}", fontsize=11)
        save_fig(fig, f"19_pie_test_types_{lvl}.png", RQ1_DIR)


def rq1_20_status_code_distribution(runs):
    counter = Counter()
    for r in runs:
        for code, cnt in r["status_code_dist"].items():
            counter[str(code)] += cnt
    codes = sorted(counter.keys(), key=lambda c: int(c))
    vals = [counter[c] for c in codes]
    cmap = plt.cm.tab20(np.linspace(0, 1, len(codes)))
    fig, ax = plt.subplots(figsize=FIGSIZE_WIDE)
    bars = ax.bar(codes, vals, color=cmap, edgecolor="black", linewidth=0.5)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width()/2, v + max(vals)*0.01, str(v),
                ha="center", fontsize=8)
    decorate_chart(ax, "RQ1 — Distribuce HTTP status kódů napříč všemi runy",
                   "Status kód", "Celkový počet výskytů", legend=False)
    save_fig(fig, "20_bar_status_code_distribution.png", RQ1_DIR)


def rq1_21_pie_status_codes(runs):
    counter = Counter()
    for r in runs:
        for code, cnt in r["status_code_dist"].items():
            counter[str(code)] += cnt
    top = counter.most_common(10)
    labels = [c for c, _ in top]
    vals = [v for _, v in top]
    colors = plt.cm.tab20(np.linspace(0, 1, len(top)))
    fig, ax = plt.subplots(figsize=FIGSIZE_SQUARE)
    ax.pie(vals, labels=labels, autopct="%1.1f%%", colors=colors,
           wedgeprops=dict(width=0.55, edgecolor="white"))
    ax.set_title("RQ1 — Top 10 HTTP status kódů (koláč)", fontsize=11)
    save_fig(fig, "21_pie_status_codes.png", RQ1_DIR)


def rq1_22_status_codes_per_level_heatmap(runs):
    """Heatmapa — distribuce status kódů per úroveň."""
    codes_per_lvl = defaultdict(lambda: Counter())
    for r in runs:
        for code, cnt in r["status_code_dist"].items():
            codes_per_lvl[r["level"]][str(code)] += cnt
    all_codes = sorted({c for lvl in LEVELS for c in codes_per_lvl[lvl]}, key=lambda c: int(c))
    M = np.array([[codes_per_lvl[lvl][c] for lvl in LEVELS] for c in all_codes])
    fig, ax = plt.subplots(figsize=(7, max(5, len(all_codes) * 0.35)))
    im = ax.imshow(M, cmap=SEQUENTIAL_CMAP, aspect="auto")
    ax.set_xticks(range(len(LEVELS))); ax.set_xticklabels(LEVELS)
    ax.set_yticks(range(len(all_codes))); ax.set_yticklabels(all_codes, fontsize=8)
    for i in range(M.shape[0]):
        for j in range(M.shape[1]):
            if M[i, j] > 0:
                c = "white" if M[i, j] < M.max() * 0.5 else "black"
                ax.text(j, i, str(M[i, j]), ha="center", va="center", fontsize=7, color=c)
    fig.colorbar(im, ax=ax, shrink=0.6, label="Počet výskytů")
    ax.set_title("RQ1 — Status kódy × úroveň (heatmapa)", fontsize=11)
    ax.set_xlabel("Úroveň kontextu"); ax.set_ylabel("Status kód")
    save_fig(fig, "22_heatmap_status_codes_per_level.png", RQ1_DIR)


def rq1_23_multi_line_all_quality_metrics(runs):
    """Multi-line — všechny 4 RQ1 metriky normalizované na 0-100 %."""
    metrics = [
        ("Validity (%)", "validity_pct", 100),
        ("Assertion Depth", "assertion_depth", 4),
        ("Response Validation (%)", "response_validation_pct", 100),
        ("Status Diversity", "diversity_count", 20),
    ]
    fig, ax = plt.subplots(figsize=FIGSIZE_WIDE)
    x = np.arange(len(LEVELS))
    cmap = plt.cm.tab10
    for i, (name, key, maxv) in enumerate(metrics):
        ys = [level_cross_avg(runs, key)[lvl] / maxv * 100 for lvl in LEVELS]
        ax.plot(x, ys, marker="o", linewidth=2, color=cmap(i), label=name)
    ax.set_xticks(x); ax.set_xticklabels(LEVELS); ax.set_ylim(0, 105)
    decorate_chart(ax, "RQ1 — Všechny metriky kvality (normalizováno na 0-100 %)",
                   "Úroveň kontextu", "Hodnota (% maxima)")
    save_fig(fig, "23_line_all_quality_metrics.png", RQ1_DIR)


def rq1_24_scatter_assertion_vs_validity(runs):
    """Scatter — všechny runy (75 bodů) obarvené podle úrovně."""
    fig, ax = plt.subplots(figsize=FIGSIZE_MED)
    for i, lvl in enumerate(LEVELS):
        xs = [r["assertion_depth"] for r in runs if r["level"] == lvl]
        ys = [r["validity_pct"] for r in runs if r["level"] == lvl]
        ax.scatter(xs, ys, color=LEVEL_COLORS[i], label=lvl, s=60, alpha=0.75,
                   edgecolors="white", linewidth=0.8)
    decorate_chart(ax, "RQ1 — Validity × Assertion Depth (bodový graf, 75 runů)",
                   "Assertion Depth", "Validity (%)")
    save_fig(fig, "24_scatter_assertion_vs_validity.png", RQ1_DIR)


def rq1_25_scatter_response_vs_validity(runs):
    fig, ax = plt.subplots(figsize=FIGSIZE_MED)
    for i, lvl in enumerate(LEVELS):
        xs = [r["response_validation_pct"] for r in runs if r["level"] == lvl]
        ys = [r["validity_pct"] for r in runs if r["level"] == lvl]
        ax.scatter(xs, ys, color=LEVEL_COLORS[i], label=lvl, s=60, alpha=0.75,
                   edgecolors="white", linewidth=0.8)
    decorate_chart(ax, "RQ1 — Validity × Response Validation (bodový graf)",
                   "Response Validation (%)", "Validity (%)")
    save_fig(fig, "25_scatter_response_vs_validity.png", RQ1_DIR)


def rq1_26_radar_levels(runs):
    """Radar chart — profil každé úrovně na RQ1 metrikách."""
    metrics = [
        ("Validity", "validity_pct", 100),
        ("Assert D.", "assertion_depth", 4),
        ("Resp Val.", "response_validation_pct", 100),
        ("Diversity", "diversity_count", 20),
        ("Happy %", "happy_pct", 100),
        ("Error %", "error_pct", 100),
    ]
    angles = np.linspace(0, 2 * np.pi, len(metrics), endpoint=False).tolist()
    angles += angles[:1]
    fig, ax = plt.subplots(figsize=FIGSIZE_SQUARE, subplot_kw=dict(polar=True))
    for i, lvl in enumerate(LEVELS):
        vals = [level_cross_avg(runs, key)[lvl] / maxv * 100 for _, key, maxv in metrics]
        vals += vals[:1]
        ax.plot(angles, vals, color=LEVEL_COLORS[i], linewidth=2, label=lvl)
        ax.fill(angles, vals, color=LEVEL_COLORS[i], alpha=0.1)
    ax.set_xticks(angles[:-1]); ax.set_xticklabels([m[0] for m in metrics])
    ax.set_title("RQ1 — Radar profil úrovní kontextu (kvalitativní metriky)", pad=20)
    ax.legend(loc="upper right", bbox_to_anchor=(1.25, 1.1), fontsize=8)
    ax.set_ylim(0, 100)
    save_fig(fig, "26_radar_levels.png", RQ1_DIR)


def rq1_27_parallel_coords(runs):
    metrics = [
        ("Validity", "validity_pct", 100),
        ("AssertD", "assertion_depth", 4),
        ("RespVal", "response_validation_pct", 100),
        ("Diversity", "diversity_count", 20),
        ("Happy%", "happy_pct", 100),
        ("Error%", "error_pct", 100),
    ]
    fig, ax = plt.subplots(figsize=FIGSIZE_WIDE)
    x = np.arange(len(metrics))
    for i, lvl in enumerate(LEVELS):
        ys = [level_cross_avg(runs, key)[lvl] / maxv * 100 for _, key, maxv in metrics]
        ax.plot(x, ys, marker="o", linewidth=2, color=LEVEL_COLORS[i], label=lvl, alpha=0.85)
    ax.set_xticks(x); ax.set_xticklabels([m[0] for m in metrics])
    decorate_chart(ax, "RQ1 — Parallel coordinates (kvalitativní metriky)",
                   "", "Hodnota (% maxima)")
    save_fig(fig, "27_parallel_coords_rq1.png", RQ1_DIR)


def rq1_28_bar_stale_tests(runs):
    avg = level_cross_avg(runs, "stale_count")
    fig, ax = plt.subplots(figsize=FIGSIZE_MED)
    x = np.arange(len(LEVELS))
    ys = [avg[l] for l in LEVELS]
    bars = ax.bar(x, ys, color=LEVEL_COLORS, edgecolor="black", linewidth=0.5, alpha=0.85)
    for b, v in zip(bars, ys):
        ax.text(b.get_x() + b.get_width()/2, v + 0.08, f"{v:.2f}", ha="center", fontsize=9)
    ax.set_xticks(x); ax.set_xticklabels(LEVELS)
    decorate_chart(ax, "RQ1 — Průměrný počet stale (neopravitelných) testů na run",
                   "Úroveň kontextu", "Počet stale testů", legend=False)
    save_fig(fig, "28_bar_stale_tests.png", RQ1_DIR)


def rq1_29_line_stale_tests(runs):
    avg = level_cross_avg(runs, "stale_count")
    std = level_cross_std(runs, "stale_count")
    fig, ax = plt.subplots(figsize=FIGSIZE_MED)
    x = np.arange(len(LEVELS))
    ys = [avg[l] for l in LEVELS]
    stds = [std[l] for l in LEVELS]
    ax.plot(x, ys, marker="o", linewidth=2.5, color=COLOR_AVG)
    ax.fill_between(x, [y - s for y, s in zip(ys, stds)], [y + s for y, s in zip(ys, stds)],
                    alpha=0.18, color=COLOR_AVG)
    for i, v in enumerate(ys):
        ax.text(i, v + 0.08, f"{v:.2f}", ha="center", fontsize=9)
    ax.set_xticks(x); ax.set_xticklabels(LEVELS)
    decorate_chart(ax, "RQ1 — Stale testy vs. úroveň kontextu",
                   "Úroveň kontextu", "Počet stale testů (ø)", legend=False)
    save_fig(fig, "29_line_stale_tests.png", RQ1_DIR)


def rq1_30_pie_overall_test_types(runs):
    h = sum(r["happy_cnt"] for r in runs)
    e = sum(r["error_cnt"] for r in runs)
    d = sum(r["edge_cnt"] for r in runs)
    vals = [h, e, d]
    labels = ["happy_path", "error", "edge_case"]
    colors = ["#55A467", "#C44E52", "#DD8452"]
    fig, ax = plt.subplots(figsize=FIGSIZE_SQUARE)
    ax.pie(vals, labels=labels, autopct="%1.1f%%", colors=colors,
           wedgeprops=dict(width=0.45, edgecolor="white"), startangle=90)
    ax.set_title(f"RQ1 — Celková distribuce typů testů (n={sum(vals)})", fontsize=11)
    save_fig(fig, "30_donut_overall_test_types.png", RQ1_DIR)


# ═══════════════════════════════════════════════════════════════════════════
# RQ2 — Strukturální pokrytí (1 křivka = průměr 3 LLM)
# ═══════════════════════════════════════════════════════════════════════════

def rq2_01_line_endpoint_coverage(runs):
    avg = level_cross_avg(runs, "endpoint_coverage_pct")
    std = level_cross_std(runs, "endpoint_coverage_pct")
    fig, ax = plt.subplots(figsize=FIGSIZE_MED)
    x = np.arange(len(LEVELS))
    ys = [avg[l] for l in LEVELS]
    stds = [std[l] for l in LEVELS]
    ax.plot(x, ys, marker="o", linewidth=2.5, color=COLOR_AVG, label="Průměr 3 LLM")
    ax.fill_between(x, [y - s for y, s in zip(ys, stds)], [y + s for y, s in zip(ys, stds)],
                    alpha=0.18, color=COLOR_AVG, label="± 1σ")
    for i, v in enumerate(ys):
        ax.text(i, v + 0.3, f"{v:.1f}", ha="center", fontsize=9)
    ax.set_xticks(x); ax.set_xticklabels(LEVELS)
    decorate_chart(ax, "RQ2 — Endpoint Coverage vs. úroveň kontextu",
                   "Úroveň kontextu", "Endpoint Coverage (%)")
    save_fig(fig, "01_line_endpoint_coverage.png", RQ2_DIR)


def rq2_02_line_total_code_coverage(runs):
    avg = level_cross_avg(runs, "code_cov_total")
    std = level_cross_std(runs, "code_cov_total")
    fig, ax = plt.subplots(figsize=FIGSIZE_MED)
    x = np.arange(len(LEVELS))
    ys = [avg[l] for l in LEVELS]
    stds = [std[l] for l in LEVELS]
    ax.plot(x, ys, marker="o", linewidth=2.5, color=COLOR_AVG, label="Průměr 3 LLM")
    ax.fill_between(x, [y - s for y, s in zip(ys, stds)], [y + s for y, s in zip(ys, stds)],
                    alpha=0.18, color=COLOR_AVG, label="± 1σ")
    for i, v in enumerate(ys):
        ax.text(i, v + 0.3, f"{v:.1f}", ha="center", fontsize=9)
    ax.set_xticks(x); ax.set_xticklabels(LEVELS)
    decorate_chart(ax, "RQ2 — Total Code Coverage vs. úroveň kontextu",
                   "Úroveň kontextu", "Code Coverage (%)")
    save_fig(fig, "02_line_total_code_coverage.png", RQ2_DIR)


def rq2_03_line_crud_coverage(runs):
    avg = level_cross_avg(runs, "code_cov_crud")
    std = level_cross_std(runs, "code_cov_crud")
    fig, ax = plt.subplots(figsize=FIGSIZE_MED)
    x = np.arange(len(LEVELS))
    ys = [avg[l] for l in LEVELS]
    stds = [std[l] for l in LEVELS]
    ax.plot(x, ys, marker="o", linewidth=2.5, color=COLOR_AVG, label="Průměr 3 LLM")
    ax.fill_between(x, [y - s for y, s in zip(ys, stds)], [y + s for y, s in zip(ys, stds)],
                    alpha=0.18, color=COLOR_AVG, label="± 1σ")
    for i, v in enumerate(ys):
        ax.text(i, v + 0.5, f"{v:.1f}", ha="center", fontsize=9)
    ax.set_xticks(x); ax.set_xticklabels(LEVELS)
    decorate_chart(ax, "RQ2 — crud.py Coverage vs. úroveň kontextu",
                   "Úroveň kontextu", "crud.py Coverage (%)")
    save_fig(fig, "03_line_crud_coverage.png", RQ2_DIR)


def rq2_04_line_main_coverage(runs):
    avg = level_cross_avg(runs, "code_cov_main")
    std = level_cross_std(runs, "code_cov_main")
    fig, ax = plt.subplots(figsize=FIGSIZE_MED)
    x = np.arange(len(LEVELS))
    ys = [avg[l] for l in LEVELS]
    stds = [std[l] for l in LEVELS]
    ax.plot(x, ys, marker="o", linewidth=2.5, color=COLOR_AVG)
    ax.fill_between(x, [y - s for y, s in zip(ys, stds)], [y + s for y, s in zip(ys, stds)],
                    alpha=0.18, color=COLOR_AVG)
    for i, v in enumerate(ys):
        ax.text(i, v + 0.15, f"{v:.1f}", ha="center", fontsize=9)
    ax.set_xticks(x); ax.set_xticklabels(LEVELS)
    decorate_chart(ax, "RQ2 — main.py Coverage vs. úroveň kontextu",
                   "Úroveň kontextu", "main.py Coverage (%)", legend=False)
    save_fig(fig, "04_line_main_coverage.png", RQ2_DIR)


def rq2_05_bar_endpoint_coverage(runs):
    avg = level_cross_avg(runs, "endpoint_coverage_pct")
    fig, ax = plt.subplots(figsize=FIGSIZE_MED)
    x = np.arange(len(LEVELS))
    ys = [avg[l] for l in LEVELS]
    bars = ax.bar(x, ys, color=LEVEL_COLORS, edgecolor="black", linewidth=0.5, alpha=0.85)
    for b, v in zip(bars, ys):
        ax.text(b.get_x() + b.get_width()/2, v + 0.3, f"{v:.1f}", ha="center", fontsize=9)
    ax.set_xticks(x); ax.set_xticklabels(LEVELS); ax.set_ylim(0, 50)
    decorate_chart(ax, "RQ2 — Endpoint Coverage (sloupcový graf)",
                   "Úroveň kontextu", "Endpoint Coverage (%)", legend=False)
    save_fig(fig, "05_bar_endpoint_coverage.png", RQ2_DIR)


def rq2_06_bar_total_coverage(runs):
    avg = level_cross_avg(runs, "code_cov_total")
    fig, ax = plt.subplots(figsize=FIGSIZE_MED)
    x = np.arange(len(LEVELS))
    ys = [avg[l] for l in LEVELS]
    bars = ax.bar(x, ys, color=LEVEL_COLORS, edgecolor="black", linewidth=0.5, alpha=0.85)
    for b, v in zip(bars, ys):
        ax.text(b.get_x() + b.get_width()/2, v + 0.3, f"{v:.1f}", ha="center", fontsize=9)
    ax.set_xticks(x); ax.set_xticklabels(LEVELS); ax.set_ylim(0, 80)
    decorate_chart(ax, "RQ2 — Total Code Coverage (sloupcový graf)",
                   "Úroveň kontextu", "Code Coverage (%)", legend=False)
    save_fig(fig, "06_bar_total_coverage.png", RQ2_DIR)


def rq2_07_bar_crud_coverage(runs):
    avg = level_cross_avg(runs, "code_cov_crud")
    fig, ax = plt.subplots(figsize=FIGSIZE_MED)
    x = np.arange(len(LEVELS))
    ys = [avg[l] for l in LEVELS]
    bars = ax.bar(x, ys, color=LEVEL_COLORS, edgecolor="black", linewidth=0.5, alpha=0.85)
    for b, v in zip(bars, ys):
        ax.text(b.get_x() + b.get_width()/2, v + 0.4, f"{v:.1f}", ha="center", fontsize=9)
    ax.set_xticks(x); ax.set_xticklabels(LEVELS); ax.set_ylim(0, 60)
    decorate_chart(ax, "RQ2 — crud.py Coverage (sloupcový graf)",
                   "Úroveň kontextu", "crud.py Coverage (%)", legend=False)
    save_fig(fig, "07_bar_crud_coverage.png", RQ2_DIR)


def rq2_08_box_endpoint_coverage(runs):
    data = [[r["endpoint_coverage_pct"] for r in runs if r["level"] == lvl] for lvl in LEVELS]
    fig, ax = plt.subplots(figsize=FIGSIZE_MED)
    bp = ax.boxplot(data, tick_labels=LEVELS, patch_artist=True, widths=0.5)
    for patch, col in zip(bp["boxes"], LEVEL_COLORS):
        patch.set_facecolor(col); patch.set_alpha(0.6)
    for med in bp["medians"]:
        med.set_color("black"); med.set_linewidth(1.5)
    decorate_chart(ax, "RQ2 — Endpoint Coverage (boxplot, n=15 / úroveň)",
                   "Úroveň kontextu", "Endpoint Coverage (%)", legend=False)
    save_fig(fig, "08_box_endpoint_coverage.png", RQ2_DIR)


def rq2_09_violin_endpoint_coverage(runs):
    data = [[r["endpoint_coverage_pct"] for r in runs if r["level"] == lvl] for lvl in LEVELS]
    fig, ax = plt.subplots(figsize=FIGSIZE_MED)
    parts = ax.violinplot(data, showmeans=True, showmedians=True)
    for pc, col in zip(parts["bodies"], LEVEL_COLORS):
        pc.set_facecolor(col); pc.set_alpha(0.55)
    ax.set_xticks(range(1, len(LEVELS) + 1)); ax.set_xticklabels(LEVELS)
    decorate_chart(ax, "RQ2 — Violin plot Endpoint Coverage napříč úrovněmi",
                   "Úroveň kontextu", "Endpoint Coverage (%)", legend=False)
    save_fig(fig, "09_violin_endpoint_coverage.png", RQ2_DIR)


def rq2_10_hist_endpoint_coverage(runs):
    vals = [r["endpoint_coverage_pct"] for r in runs]
    fig, ax = plt.subplots(figsize=FIGSIZE_MED)
    ax.hist(vals, bins=15, color=COLOR_AVG, edgecolor="black", alpha=0.75)
    decorate_chart(ax, f"RQ2 — Histogram Endpoint Coverage (n={len(vals)} runů)",
                   "Endpoint Coverage (%)", "Počet runů", legend=False)
    save_fig(fig, "10_hist_endpoint_coverage.png", RQ2_DIR)


def rq2_11_hist_crud_coverage(runs):
    vals = [r["code_cov_crud"] for r in runs]
    fig, ax = plt.subplots(figsize=FIGSIZE_MED)
    ax.hist(vals, bins=15, color=COLOR_AVG, edgecolor="black", alpha=0.75)
    decorate_chart(ax, f"RQ2 — Histogram crud.py Coverage (n={len(vals)} runů)",
                   "crud.py Coverage (%)", "Počet runů", legend=False)
    save_fig(fig, "11_hist_crud_coverage.png", RQ2_DIR)


def rq2_12_combined_coverage_layers(runs):
    """Tři křivky vedle sebe — total, crud.py, endpoint coverage."""
    fig, ax = plt.subplots(figsize=FIGSIZE_WIDE)
    x = np.arange(len(LEVELS))
    metrics = [
        ("Total Code Cov.", "code_cov_total", "#4C72B0"),
        ("crud.py Cov.", "code_cov_crud", "#C44E52"),
        ("main.py Cov.", "code_cov_main", "#55A467"),
        ("Endpoint Cov.", "endpoint_coverage_pct", "#DD8452"),
    ]
    for name, key, color in metrics:
        ys = [level_cross_avg(runs, key)[lvl] for lvl in LEVELS]
        ax.plot(x, ys, marker="o", linewidth=2, color=color, label=name)
        for i, v in enumerate(ys):
            ax.text(i, v + 1, f"{v:.1f}", ha="center", fontsize=7, color=color)
    ax.set_xticks(x); ax.set_xticklabels(LEVELS)
    decorate_chart(ax, "RQ2 — Všechny coverage metriky vs. úroveň kontextu",
                   "Úroveň kontextu", "Coverage (%)")
    save_fig(fig, "12_line_all_coverage.png", RQ2_DIR)


def rq2_13_delta_from_baseline(runs):
    """Δ vs. L0 — jak moc každá metrika roste s kontextem."""
    fig, ax = plt.subplots(figsize=FIGSIZE_WIDE)
    x = np.arange(len(LEVELS))
    metrics = [
        ("Endpoint Cov.", "endpoint_coverage_pct", "#DD8452"),
        ("Total Code Cov.", "code_cov_total", "#4C72B0"),
        ("crud.py Cov.", "code_cov_crud", "#C44E52"),
        ("main.py Cov.", "code_cov_main", "#55A467"),
    ]
    for name, key, color in metrics:
        avg = level_cross_avg(runs, key)
        baseline = avg["L0"]
        ys = [avg[lvl] - baseline for lvl in LEVELS]
        ax.plot(x, ys, marker="o", linewidth=2, color=color, label=name)
    ax.axhline(0, color="black", linestyle="--", linewidth=0.8, alpha=0.5)
    ax.set_xticks(x); ax.set_xticklabels(LEVELS)
    decorate_chart(ax, "RQ2 — Δ coverage vs. L0 (o kolik roste každá metrika)",
                   "Úroveň kontextu", "Δ Coverage (pp vs. L0)")
    save_fig(fig, "13_line_delta_from_baseline.png", RQ2_DIR)


def rq2_14_scatter_endpoint_vs_crud(runs):
    """Scatter — 75 runů, obarvené podle úrovně."""
    fig, ax = plt.subplots(figsize=FIGSIZE_MED)
    for i, lvl in enumerate(LEVELS):
        xs = [r["endpoint_coverage_pct"] for r in runs if r["level"] == lvl]
        ys = [r["code_cov_crud"] for r in runs if r["level"] == lvl]
        ax.scatter(xs, ys, color=LEVEL_COLORS[i], label=lvl, s=60, alpha=0.75,
                   edgecolors="white", linewidth=0.8)
    decorate_chart(ax, "RQ2 — Endpoint Coverage × crud.py Coverage (75 runů)",
                   "Endpoint Coverage (%)", "crud.py Coverage (%)")
    save_fig(fig, "14_scatter_endpoint_vs_crud.png", RQ2_DIR)


def rq2_15_scatter_total_vs_crud(runs):
    fig, ax = plt.subplots(figsize=FIGSIZE_MED)
    for i, lvl in enumerate(LEVELS):
        xs = [r["code_cov_total"] for r in runs if r["level"] == lvl]
        ys = [r["code_cov_crud"] for r in runs if r["level"] == lvl]
        ax.scatter(xs, ys, color=LEVEL_COLORS[i], label=lvl, s=60, alpha=0.75,
                   edgecolors="white", linewidth=0.8)
    decorate_chart(ax, "RQ2 — Total Coverage × crud.py Coverage",
                   "Total Coverage (%)", "crud.py Coverage (%)")
    save_fig(fig, "15_scatter_total_vs_crud.png", RQ2_DIR)


def rq2_16_stacked_bar_coverage_layers(runs):
    """Stacked bar — 100% barů, rozpad na 'co pokryju' vs 'co ignoruju'."""
    avg = level_cross_avg(runs, "endpoint_coverage_pct")
    fig, ax = plt.subplots(figsize=FIGSIZE_MED)
    x = np.arange(len(LEVELS))
    covered = [avg[l] for l in LEVELS]
    uncovered = [100 - c for c in covered]
    ax.bar(x, covered, color="#55A467", label="Pokryté endpointy", alpha=0.85)
    ax.bar(x, uncovered, bottom=covered, color="#C44E52", label="Nepokryté endpointy", alpha=0.55)
    for i, v in enumerate(covered):
        ax.text(i, v/2, f"{v:.1f}%", ha="center", fontsize=9, color="white", weight="bold")
    ax.set_xticks(x); ax.set_xticklabels(LEVELS); ax.set_ylim(0, 100)
    decorate_chart(ax, "RQ2 — Pokryté vs. nepokryté endpointy (stacked)",
                   "Úroveň kontextu", "Podíl (%)")
    save_fig(fig, "16_stacked_bar_covered_uncovered.png", RQ2_DIR)


def rq2_17_radar_coverage(runs):
    metrics = [
        ("Endpoint Cov", "endpoint_coverage_pct", 50),
        ("Total Code", "code_cov_total", 80),
        ("crud.py", "code_cov_crud", 60),
        ("main.py", "code_cov_main", 80),
    ]
    angles = np.linspace(0, 2 * np.pi, len(metrics), endpoint=False).tolist()
    angles += angles[:1]
    fig, ax = plt.subplots(figsize=FIGSIZE_SQUARE, subplot_kw=dict(polar=True))
    for i, lvl in enumerate(LEVELS):
        vals = [level_cross_avg(runs, key)[lvl] / maxv * 100 for _, key, maxv in metrics]
        vals += vals[:1]
        ax.plot(angles, vals, color=LEVEL_COLORS[i], linewidth=2, label=lvl)
        ax.fill(angles, vals, color=LEVEL_COLORS[i], alpha=0.1)
    ax.set_xticks(angles[:-1]); ax.set_xticklabels([m[0] for m in metrics])
    ax.set_title("RQ2 — Radar profil úrovní (coverage metriky)", pad=20)
    ax.legend(loc="upper right", bbox_to_anchor=(1.25, 1.1), fontsize=8)
    ax.set_ylim(0, 100)
    save_fig(fig, "17_radar_coverage.png", RQ2_DIR)


def rq2_18_area_coverage_growth(runs):
    """Area chart — růst crud.py coverage vs. L0 baseline."""
    avg = level_cross_avg(runs, "code_cov_crud")
    baseline = avg["L0"]
    fig, ax = plt.subplots(figsize=FIGSIZE_MED)
    x = np.arange(len(LEVELS))
    ys = [avg[l] for l in LEVELS]
    ax.fill_between(x, baseline, ys, where=[y >= baseline for y in ys],
                    alpha=0.35, color="#55A467", label="Zisk vs. L0")
    ax.plot(x, ys, marker="o", linewidth=2.5, color=COLOR_AVG, label="crud.py coverage")
    ax.axhline(baseline, color="black", linestyle="--", linewidth=1, label=f"L0 baseline ({baseline:.1f}%)")
    for i, v in enumerate(ys):
        ax.text(i, v + 0.5, f"{v:.1f}", ha="center", fontsize=9)
    ax.set_xticks(x); ax.set_xticklabels(LEVELS)
    decorate_chart(ax, "RQ2 — Zisk crud.py coverage oproti L0 baseline",
                   "Úroveň kontextu", "crud.py Coverage (%)")
    save_fig(fig, "18_area_crud_growth.png", RQ2_DIR)


def rq2_19_heatmap_coverage_per_level(runs):
    """Heatmapa coverage metrik × úrovní."""
    metrics = [
        ("Endpoint Cov.", "endpoint_coverage_pct"),
        ("Total Code", "code_cov_total"),
        ("crud.py", "code_cov_crud"),
        ("main.py", "code_cov_main"),
    ]
    M = np.array([[level_cross_avg(runs, key)[lvl] for lvl in LEVELS] for _, key in metrics])
    fig, ax = plt.subplots(figsize=FIGSIZE_WIDE)
    im = ax.imshow(M, cmap=HEATMAP_CMAP, aspect="auto")
    ax.set_xticks(range(len(LEVELS))); ax.set_xticklabels(LEVELS)
    ax.set_yticks(range(len(metrics))); ax.set_yticklabels([m[0] for m in metrics])
    for i in range(M.shape[0]):
        for j in range(M.shape[1]):
            ax.text(j, i, f"{M[i,j]:.1f}", ha="center", va="center", fontsize=10)
    fig.colorbar(im, ax=ax, shrink=0.6, label="Coverage (%)")
    ax.set_title("RQ2 — Heatmapa coverage metrik × úroveň", fontsize=11)
    ax.set_xlabel("Úroveň kontextu"); ax.set_ylabel("Metrika")
    save_fig(fig, "19_heatmap_coverage_per_level.png", RQ2_DIR)


def rq2_20_hypothesis_falsification(runs):
    """Speciální graf — ukazuje, že skok je na L1, ne na L2 (falsifikace hypotézy)."""
    avg = level_cross_avg(runs, "code_cov_crud")
    fig, ax = plt.subplots(figsize=FIGSIZE_WIDE)
    x = np.arange(len(LEVELS))
    ys = [avg[l] for l in LEVELS]
    colors = [LEVEL_COLORS[0], "#C44E52", "#4C72B0", "#8172B2", "#55A467"]
    bars = ax.bar(x, ys, color=colors, edgecolor="black", linewidth=0.5, alpha=0.85)
    for b, v in zip(bars, ys):
        ax.text(b.get_x() + b.get_width()/2, v + 0.5, f"{v:.1f}", ha="center", fontsize=9)
    # Annotate deltas
    for i in range(1, len(ys)):
        delta = ys[i] - ys[i-1]
        ax.annotate(f"Δ {delta:+.2f} pp",
                    xy=((x[i-1] + x[i]) / 2, max(ys[i-1], ys[i]) + 2),
                    ha="center", fontsize=8,
                    color="darkgreen" if delta > 2 else ("red" if delta < 0 else "gray"))
    ax.set_xticks(x); ax.set_xticklabels(LEVELS); ax.set_ylim(0, 55)
    decorate_chart(ax, "RQ2 — Δ crud.py coverage mezi úrovněmi (skok je na L1!)",
                   "Úroveň kontextu", "crud.py Coverage (%)", legend=False)
    save_fig(fig, "20_bar_delta_annotations.png", RQ2_DIR)


def rq2_21_scatter_with_regression(runs):
    """Scatter endpoint cov vs context tokens (kolik tokenů = kolik EP)."""
    fig, ax = plt.subplots(figsize=FIGSIZE_MED)
    for i, lvl in enumerate(LEVELS):
        xs = [r["context_tokens"] for r in runs if r["level"] == lvl]
        ys = [r["endpoint_coverage_pct"] for r in runs if r["level"] == lvl]
        ax.scatter(xs, ys, color=LEVEL_COLORS[i], label=lvl, s=60, alpha=0.75,
                   edgecolors="white", linewidth=0.8)
    # Linear fit
    all_x = [r["context_tokens"] for r in runs]
    all_y = [r["endpoint_coverage_pct"] for r in runs]
    if len(set(all_x)) > 1:
        z = np.polyfit(all_x, all_y, 1)
        xs_line = np.linspace(min(all_x), max(all_x), 100)
        ax.plot(xs_line, np.polyval(z, xs_line), "--", color="black", linewidth=1,
                label=f"Trend (slope={z[0]:.2e})", alpha=0.7)
    decorate_chart(ax, "RQ2 — Endpoint Coverage vs. velikost kontextu",
                   "Kontext (tokeny po kompresi)", "Endpoint Coverage (%)")
    save_fig(fig, "21_scatter_context_vs_ep_coverage.png", RQ2_DIR)


def rq2_22_saturation_curve(runs):
    """Vizuální porovnání — endpoint vs code coverage jako 'růst na úrovních'."""
    ep = level_cross_avg(runs, "endpoint_coverage_pct")
    code = level_cross_avg(runs, "code_cov_total")
    crud = level_cross_avg(runs, "code_cov_crud")
    fig, ax = plt.subplots(figsize=FIGSIZE_WIDE)
    x = np.arange(len(LEVELS))
    # Normalize all to L0 = 100
    ep_norm = [ep[l] / ep["L0"] * 100 for l in LEVELS]
    code_norm = [code[l] / code["L0"] * 100 for l in LEVELS]
    crud_norm = [crud[l] / crud["L0"] * 100 for l in LEVELS]
    ax.plot(x, ep_norm, marker="o", linewidth=2, color="#DD8452", label="Endpoint Coverage")
    ax.plot(x, code_norm, marker="s", linewidth=2, color="#4C72B0", label="Total Code Coverage")
    ax.plot(x, crud_norm, marker="^", linewidth=2, color="#C44E52", label="crud.py Coverage")
    ax.axhline(100, color="black", linestyle="--", linewidth=0.8, alpha=0.4)
    ax.set_xticks(x); ax.set_xticklabels(LEVELS)
    decorate_chart(ax, "RQ2 — Relativní růst coverage metrik (L0 = 100 %)",
                   "Úroveň kontextu", "Relativní hodnota (% L0)")
    save_fig(fig, "22_line_relative_growth.png", RQ2_DIR)


def rq2_23_donut_crud_coverage(runs):
    """Donut — průměrné pokrytí crud.py na L2 (kde je peak)."""
    for lvl in LEVELS:
        avg_crud = level_cross_avg(runs, "code_cov_crud")[lvl]
        uncovered = 100 - avg_crud
        fig, ax = plt.subplots(figsize=FIGSIZE_SQUARE)
        ax.pie([avg_crud, uncovered], labels=["Pokryto", "Nepokryto"],
               autopct="%1.1f%%", colors=["#55A467", "#C44E52"],
               wedgeprops=dict(width=0.45, edgecolor="white"), startangle=90)
        ax.set_title(f"RQ2 — crud.py Coverage na úrovni {lvl}", fontsize=11)
        save_fig(fig, f"23_donut_crud_{lvl}.png", RQ2_DIR)


def rq2_24_dual_axis_ep_vs_code(runs):
    """Dual axis — EP coverage (levá osa) vs. crud.py (pravá osa)."""
    ep = level_cross_avg(runs, "endpoint_coverage_pct")
    crud = level_cross_avg(runs, "code_cov_crud")
    fig, ax1 = plt.subplots(figsize=FIGSIZE_MED)
    x = np.arange(len(LEVELS))
    ax1.plot(x, [ep[l] for l in LEVELS], marker="o", linewidth=2.5, color="#DD8452",
             label="Endpoint Coverage")
    ax1.set_ylabel("Endpoint Coverage (%)", color="#DD8452", fontsize=10)
    ax1.tick_params(axis="y", labelcolor="#DD8452")
    ax1.set_xticks(x); ax1.set_xticklabels(LEVELS)
    ax1.set_ylim(0, 50)
    ax2 = ax1.twinx()
    ax2.plot(x, [crud[l] for l in LEVELS], marker="s", linewidth=2.5, color="#C44E52",
             label="crud.py Coverage")
    ax2.set_ylabel("crud.py Coverage (%)", color="#C44E52", fontsize=10)
    ax2.tick_params(axis="y", labelcolor="#C44E52")
    ax2.set_ylim(0, 60)
    ax1.set_xlabel("Úroveň kontextu", fontsize=10)
    ax1.set_title("RQ2 — Endpoint Coverage vs. crud.py Coverage (dvě osy)", fontsize=11)
    ax1.grid(True, linestyle="--", linewidth=0.4, alpha=0.5)
    fig.tight_layout()
    fig.savefig(RQ2_DIR / "24_dual_axis_ep_vs_crud.png", dpi=DPI, bbox_inches="tight")
    plt.close(fig)


def rq2_25_multi_line_all_coverage(runs):
    """Normalizovaný multi-line všech coverage metrik na jedné škále."""
    metrics = [
        ("Endpoint Cov (% z 50)", "endpoint_coverage_pct", 50),
        ("Total Code Cov", "code_cov_total", 100),
        ("crud.py Cov (% z 60)", "code_cov_crud", 60),
        ("main.py Cov", "code_cov_main", 100),
    ]
    fig, ax = plt.subplots(figsize=FIGSIZE_WIDE)
    x = np.arange(len(LEVELS))
    cmap = plt.cm.tab10
    for i, (name, key, maxv) in enumerate(metrics):
        ys = [level_cross_avg(runs, key)[lvl] / maxv * 100 for lvl in LEVELS]
        ax.plot(x, ys, marker="o", linewidth=2, color=cmap(i), label=name)
    ax.set_xticks(x); ax.set_xticklabels(LEVELS); ax.set_ylim(0, 100)
    decorate_chart(ax, "RQ2 — Všechny coverage metriky (normalizováno 0-100 %)",
                   "Úroveň kontextu", "Hodnota (% max)")
    save_fig(fig, "25_line_all_coverage_normalized.png", RQ2_DIR)


# ═══════════════════════════════════════════════════════════════════════════
# RQ3 — Mezimodelové porovnání (3 křivky, jedna per LLM)
# ═══════════════════════════════════════════════════════════════════════════

def _three_line_chart(runs, key, title, ylabel, fname, y_lim=None, annotate=True):
    """Generická pomocná funkce pro RQ3 multi-line grafy (3 modely)."""
    m = model_level_matrix(runs, key)
    fig, ax = plt.subplots(figsize=FIGSIZE_MED)
    x = np.arange(len(LEVELS))
    for llm in LLMS:
        ys = [m[llm][lvl] for lvl in LEVELS]
        ax.plot(x, ys, marker="o", linewidth=2, color=LLM_COLORS[llm], label=LLM_SHORT[llm])
        if annotate:
            for i, v in enumerate(ys):
                ax.text(i, v, f"{v:.1f}", ha="center", va="bottom", fontsize=7, color=LLM_COLORS[llm])
    ax.set_xticks(x); ax.set_xticklabels(LEVELS)
    if y_lim:
        ax.set_ylim(*y_lim)
    decorate_chart(ax, title, "Úroveň kontextu", ylabel)
    save_fig(fig, fname, RQ3_DIR)


def rq3_01_line_validity(runs):
    _three_line_chart(runs, "validity_pct",
                      "RQ3 — Validity Rate per model",
                      "Validity (%)",
                      "01_line_validity.png", y_lim=(75, 102))


def rq3_02_line_assertion_depth(runs):
    _three_line_chart(runs, "assertion_depth",
                      "RQ3 — Assertion Depth per model",
                      "Assertion Depth",
                      "02_line_assertion_depth.png")


def rq3_03_line_response_validation(runs):
    _three_line_chart(runs, "response_validation_pct",
                      "RQ3 — Response Validation per model",
                      "Response Validation (%)",
                      "03_line_response_validation.png")


def rq3_04_line_endpoint_coverage(runs):
    _three_line_chart(runs, "endpoint_coverage_pct",
                      "RQ3 — Endpoint Coverage per model",
                      "Endpoint Coverage (%)",
                      "04_line_endpoint_coverage.png")


def rq3_05_line_total_code_coverage(runs):
    _three_line_chart(runs, "code_cov_total",
                      "RQ3 — Total Code Coverage per model",
                      "Code Coverage (%)",
                      "05_line_total_coverage.png")


def rq3_06_line_crud_coverage(runs):
    _three_line_chart(runs, "code_cov_crud",
                      "RQ3 — crud.py Coverage per model",
                      "crud.py Coverage (%)",
                      "06_line_crud_coverage.png")


def rq3_07_line_cost(runs):
    _three_line_chart(runs, "cost_usd",
                      "RQ3 — Cena na run per model",
                      "Cena (USD)",
                      "07_line_cost.png")


def rq3_08_line_stale_tests(runs):
    _three_line_chart(runs, "stale_count",
                      "RQ3 — Stale testy per model",
                      "Počet stale testů (ø)",
                      "08_line_stale_tests.png")


def rq3_09_line_diversity(runs):
    _three_line_chart(runs, "diversity_count",
                      "RQ3 — Status Code Diversity per model",
                      "Unikátní status kódy",
                      "09_line_diversity.png")


def rq3_10_line_iterations(runs):
    _three_line_chart(runs, "iterations",
                      "RQ3 — Repair iterace per model",
                      "Počet iterací",
                      "10_line_iterations.png")


def rq3_11_line_tokens(runs):
    _three_line_chart(runs, "total_tokens",
                      "RQ3 — Celkové tokeny per model",
                      "Tokeny",
                      "11_line_tokens.png")


def rq3_12_bar_validity_grouped(runs):
    m = model_level_matrix(runs, "validity_pct")
    fig, ax = plt.subplots(figsize=FIGSIZE_WIDE)
    x = np.arange(len(LEVELS)); w = 0.25
    for i, llm in enumerate(LLMS):
        ys = [m[llm][lvl] for lvl in LEVELS]
        bars = ax.bar(x + (i - 1) * w, ys, w, color=LLM_COLORS[llm], label=LLM_SHORT[llm])
        for b, v in zip(bars, ys):
            ax.text(b.get_x() + b.get_width()/2, v + 0.4, f"{v:.1f}",
                    ha="center", fontsize=7)
    ax.set_xticks(x); ax.set_xticklabels(LEVELS); ax.set_ylim(0, 105)
    decorate_chart(ax, "RQ3 — Validity — grupovaný sloupcový graf",
                   "Úroveň kontextu", "Validity (%)")
    save_fig(fig, "12_bar_validity_grouped.png", RQ3_DIR)


def rq3_13_bar_cost_grouped(runs):
    m = model_level_matrix(runs, "cost_usd")
    fig, ax = plt.subplots(figsize=FIGSIZE_WIDE)
    x = np.arange(len(LEVELS)); w = 0.25
    for i, llm in enumerate(LLMS):
        ys = [m[llm][lvl] for lvl in LEVELS]
        bars = ax.bar(x + (i - 1) * w, ys, w, color=LLM_COLORS[llm], label=LLM_SHORT[llm])
        for b, v in zip(bars, ys):
            ax.text(b.get_x() + b.get_width()/2, v + 0.001, f"{v:.3f}",
                    ha="center", fontsize=6, rotation=45)
    ax.set_xticks(x); ax.set_xticklabels(LEVELS)
    decorate_chart(ax, "RQ3 — Cena na run per model a úroveň",
                   "Úroveň kontextu", "Cena (USD)")
    save_fig(fig, "13_bar_cost_grouped.png", RQ3_DIR)


def rq3_14_bar_endpoint_coverage_grouped(runs):
    m = model_level_matrix(runs, "endpoint_coverage_pct")
    fig, ax = plt.subplots(figsize=FIGSIZE_WIDE)
    x = np.arange(len(LEVELS)); w = 0.25
    for i, llm in enumerate(LLMS):
        ys = [m[llm][lvl] for lvl in LEVELS]
        bars = ax.bar(x + (i - 1) * w, ys, w, color=LLM_COLORS[llm], label=LLM_SHORT[llm])
        for b, v in zip(bars, ys):
            ax.text(b.get_x() + b.get_width()/2, v + 0.3, f"{v:.1f}",
                    ha="center", fontsize=7)
    ax.set_xticks(x); ax.set_xticklabels(LEVELS); ax.set_ylim(0, 55)
    decorate_chart(ax, "RQ3 — Endpoint Coverage — grupovaný sloupcový graf",
                   "Úroveň kontextu", "Endpoint Coverage (%)")
    save_fig(fig, "14_bar_endpoint_coverage_grouped.png", RQ3_DIR)


def rq3_15_bar_crud_coverage_grouped(runs):
    m = model_level_matrix(runs, "code_cov_crud")
    fig, ax = plt.subplots(figsize=FIGSIZE_WIDE)
    x = np.arange(len(LEVELS)); w = 0.25
    for i, llm in enumerate(LLMS):
        ys = [m[llm][lvl] for lvl in LEVELS]
        bars = ax.bar(x + (i - 1) * w, ys, w, color=LLM_COLORS[llm], label=LLM_SHORT[llm])
        for b, v in zip(bars, ys):
            ax.text(b.get_x() + b.get_width()/2, v + 0.4, f"{v:.1f}",
                    ha="center", fontsize=7)
    ax.set_xticks(x); ax.set_xticklabels(LEVELS); ax.set_ylim(0, 65)
    decorate_chart(ax, "RQ3 — crud.py Coverage — grupovaný sloupcový graf",
                   "Úroveň kontextu", "crud.py Coverage (%)")
    save_fig(fig, "15_bar_crud_coverage_grouped.png", RQ3_DIR)


def rq3_16_heatmap_validity(runs):
    m = model_level_matrix(runs, "validity_pct")
    M = np.array([[m[llm][lvl] for lvl in LEVELS] for llm in LLMS])
    fig, ax = plt.subplots(figsize=FIGSIZE_MED)
    im = ax.imshow(M, cmap=HEATMAP_CMAP, aspect="auto", vmin=75, vmax=100)
    ax.set_xticks(range(len(LEVELS))); ax.set_xticklabels(LEVELS)
    ax.set_yticks(range(len(LLMS))); ax.set_yticklabels([LLM_SHORT[l] for l in LLMS])
    for i in range(M.shape[0]):
        for j in range(M.shape[1]):
            ax.text(j, i, f"{M[i,j]:.1f}", ha="center", va="center", fontsize=10)
    fig.colorbar(im, ax=ax, shrink=0.7, label="Validity (%)")
    ax.set_title("RQ3 — Heatmapa Validity (model × úroveň)", fontsize=11)
    save_fig(fig, "16_heatmap_validity.png", RQ3_DIR)


def rq3_17_heatmap_ep_coverage(runs):
    m = model_level_matrix(runs, "endpoint_coverage_pct")
    M = np.array([[m[llm][lvl] for lvl in LEVELS] for llm in LLMS])
    fig, ax = plt.subplots(figsize=FIGSIZE_MED)
    im = ax.imshow(M, cmap=SEQUENTIAL_CMAP, aspect="auto")
    ax.set_xticks(range(len(LEVELS))); ax.set_xticklabels(LEVELS)
    ax.set_yticks(range(len(LLMS))); ax.set_yticklabels([LLM_SHORT[l] for l in LLMS])
    for i in range(M.shape[0]):
        for j in range(M.shape[1]):
            c = "white" if M[i, j] < 35 else "black"
            ax.text(j, i, f"{M[i,j]:.1f}", ha="center", va="center", fontsize=10, color=c)
    fig.colorbar(im, ax=ax, shrink=0.7, label="EP Coverage (%)")
    ax.set_title("RQ3 — Heatmapa Endpoint Coverage (model × úroveň)", fontsize=11)
    save_fig(fig, "17_heatmap_ep_coverage.png", RQ3_DIR)


def rq3_18_heatmap_crud_coverage(runs):
    M = np.array([[COVERAGE[llm][lvl]["crud"] for lvl in LEVELS] for llm in LLMS])
    fig, ax = plt.subplots(figsize=FIGSIZE_MED)
    im = ax.imshow(M, cmap=HEATMAP_CMAP, aspect="auto", vmin=25, vmax=60)
    ax.set_xticks(range(len(LEVELS))); ax.set_xticklabels(LEVELS)
    ax.set_yticks(range(len(LLMS))); ax.set_yticklabels([LLM_SHORT[l] for l in LLMS])
    for i in range(M.shape[0]):
        for j in range(M.shape[1]):
            ax.text(j, i, f"{M[i,j]:.1f}", ha="center", va="center", fontsize=10)
    fig.colorbar(im, ax=ax, shrink=0.7, label="crud.py Coverage (%)")
    ax.set_title("RQ3 — Heatmapa crud.py Coverage (model × úroveň)", fontsize=11)
    save_fig(fig, "18_heatmap_crud_coverage.png", RQ3_DIR)


def rq3_19_heatmap_delta_validity(runs):
    """Δ validity každého modelu vs L0 baseline."""
    m = model_level_matrix(runs, "validity_pct")
    M = np.array([[m[llm][lvl] - m[llm]["L0"] for lvl in LEVELS] for llm in LLMS])
    fig, ax = plt.subplots(figsize=FIGSIZE_MED)
    vmax = max(abs(M.min()), abs(M.max()))
    im = ax.imshow(M, cmap=DIVERGING_CMAP, aspect="auto", vmin=-vmax, vmax=vmax)
    ax.set_xticks(range(len(LEVELS))); ax.set_xticklabels(LEVELS)
    ax.set_yticks(range(len(LLMS))); ax.set_yticklabels([LLM_SHORT[l] for l in LLMS])
    for i in range(M.shape[0]):
        for j in range(M.shape[1]):
            ax.text(j, i, f"{M[i,j]:+.1f}", ha="center", va="center", fontsize=10)
    fig.colorbar(im, ax=ax, shrink=0.7, label="Δ validity vs. L0 (pp)")
    ax.set_title("RQ3 — Δ Validity per model (vs. vlastní L0)", fontsize=11)
    save_fig(fig, "19_heatmap_delta_validity.png", RQ3_DIR)


def rq3_20_box_validity_by_model(runs):
    data = [[r["validity_pct"] for r in runs if r["llm"] == llm] for llm in LLMS]
    fig, ax = plt.subplots(figsize=FIGSIZE_MED)
    bp = ax.boxplot(data, tick_labels=[LLM_SHORT[l] for l in LLMS], patch_artist=True, widths=0.5)
    for patch, llm in zip(bp["boxes"], LLMS):
        patch.set_facecolor(LLM_COLORS[llm]); patch.set_alpha(0.6)
    for med in bp["medians"]:
        med.set_color("black"); med.set_linewidth(1.5)
    decorate_chart(ax, "RQ3 — Validity distribuce per model (n=25 / model)",
                   "Model", "Validity (%)", legend=False)
    save_fig(fig, "20_box_validity_by_model.png", RQ3_DIR)


def rq3_21_box_cost_by_model(runs):
    data = [[r["cost_usd"] for r in runs if r["llm"] == llm] for llm in LLMS]
    fig, ax = plt.subplots(figsize=FIGSIZE_MED)
    bp = ax.boxplot(data, tick_labels=[LLM_SHORT[l] for l in LLMS], patch_artist=True, widths=0.5)
    for patch, llm in zip(bp["boxes"], LLMS):
        patch.set_facecolor(LLM_COLORS[llm]); patch.set_alpha(0.6)
    for med in bp["medians"]:
        med.set_color("black"); med.set_linewidth(1.5)
    decorate_chart(ax, "RQ3 — Cena distribuce per model",
                   "Model", "Cena (USD)", legend=False)
    save_fig(fig, "21_box_cost_by_model.png", RQ3_DIR)


def rq3_22_box_ep_coverage_by_model(runs):
    data = [[r["endpoint_coverage_pct"] for r in runs if r["llm"] == llm] for llm in LLMS]
    fig, ax = plt.subplots(figsize=FIGSIZE_MED)
    bp = ax.boxplot(data, tick_labels=[LLM_SHORT[l] for l in LLMS], patch_artist=True, widths=0.5)
    for patch, llm in zip(bp["boxes"], LLMS):
        patch.set_facecolor(LLM_COLORS[llm]); patch.set_alpha(0.6)
    for med in bp["medians"]:
        med.set_color("black"); med.set_linewidth(1.5)
    decorate_chart(ax, "RQ3 — EP Coverage distribuce per model",
                   "Model", "Endpoint Coverage (%)", legend=False)
    save_fig(fig, "22_box_ep_coverage_by_model.png", RQ3_DIR)


def rq3_23_violin_validity_per_model(runs):
    data = [[r["validity_pct"] for r in runs if r["llm"] == llm] for llm in LLMS]
    fig, ax = plt.subplots(figsize=FIGSIZE_MED)
    parts = ax.violinplot(data, showmeans=True, showmedians=True)
    for pc, llm in zip(parts["bodies"], LLMS):
        pc.set_facecolor(LLM_COLORS[llm]); pc.set_alpha(0.55)
    ax.set_xticks(range(1, len(LLMS) + 1))
    ax.set_xticklabels([LLM_SHORT[l] for l in LLMS])
    decorate_chart(ax, "RQ3 — Violin plot Validity per model",
                   "Model", "Validity (%)", legend=False)
    save_fig(fig, "23_violin_validity_by_model.png", RQ3_DIR)


def rq3_24_radar_models(runs):
    metrics = [
        ("Validity", "validity_pct", 100),
        ("EP Cov", "endpoint_coverage_pct", 50),
        ("Code Cov", "code_cov_total", 100),
        ("CRUD Cov", "code_cov_crud", 60),
        ("Assert D.", "assertion_depth", 4),
        ("Resp Val", "response_validation_pct", 100),
    ]
    angles = np.linspace(0, 2 * np.pi, len(metrics), endpoint=False).tolist()
    angles += angles[:1]
    fig, ax = plt.subplots(figsize=FIGSIZE_SQUARE, subplot_kw=dict(polar=True))
    for llm in LLMS:
        vals = []
        for _, key, maxv in metrics:
            avg = mean(r[key] for r in runs if r["llm"] == llm)
            vals.append(avg / maxv * 100)
        vals += vals[:1]
        ax.plot(angles, vals, color=LLM_COLORS[llm], linewidth=2, label=LLM_SHORT[llm])
        ax.fill(angles, vals, color=LLM_COLORS[llm], alpha=0.12)
    ax.set_xticks(angles[:-1]); ax.set_xticklabels([m[0] for m in metrics])
    ax.set_title("RQ3 — Radar profil modelů (normalizováno)", pad=20)
    ax.legend(loc="upper right", bbox_to_anchor=(1.25, 1.1), fontsize=8)
    ax.set_ylim(0, 100)
    save_fig(fig, "24_radar_models.png", RQ3_DIR)


def rq3_25_parallel_coords_models(runs):
    metrics = [
        ("Validity", "validity_pct", 100),
        ("EPCov", "endpoint_coverage_pct", 50),
        ("CodeCov", "code_cov_total", 100),
        ("CRUD", "code_cov_crud", 60),
        ("AssertD", "assertion_depth", 4),
        ("RespVal", "response_validation_pct", 100),
    ]
    fig, ax = plt.subplots(figsize=FIGSIZE_WIDE)
    x = np.arange(len(metrics))
    for llm in LLMS:
        ys = [mean(r[key] for r in runs if r["llm"] == llm) / maxv * 100
              for _, key, maxv in metrics]
        ax.plot(x, ys, marker="o", linewidth=2, color=LLM_COLORS[llm],
                label=LLM_SHORT[llm], alpha=0.85)
    ax.set_xticks(x); ax.set_xticklabels([m[0] for m in metrics])
    decorate_chart(ax, "RQ3 — Parallel coordinates — 3 modely",
                   "", "Hodnota (% max)")
    save_fig(fig, "25_parallel_coords_models.png", RQ3_DIR)


def rq3_26_scatter_cost_vs_validity(runs):
    fig, ax = plt.subplots(figsize=FIGSIZE_MED)
    for llm in LLMS:
        xs = [r["cost_usd"] for r in runs if r["llm"] == llm]
        ys = [r["validity_pct"] for r in runs if r["llm"] == llm]
        ax.scatter(xs, ys, color=LLM_COLORS[llm], label=LLM_SHORT[llm],
                   s=60, alpha=0.75, edgecolors="white", linewidth=0.8)
    decorate_chart(ax, "RQ3 — Cena × Validity (75 runů)",
                   "Cena na run (USD)", "Validity (%)")
    save_fig(fig, "26_scatter_cost_vs_validity.png", RQ3_DIR)


def rq3_27_scatter_ep_vs_validity(runs):
    fig, ax = plt.subplots(figsize=FIGSIZE_MED)
    for llm in LLMS:
        xs = [r["endpoint_coverage_pct"] for r in runs if r["llm"] == llm]
        ys = [r["validity_pct"] for r in runs if r["llm"] == llm]
        ax.scatter(xs, ys, color=LLM_COLORS[llm], label=LLM_SHORT[llm],
                   s=60, alpha=0.75, edgecolors="white", linewidth=0.8)
    decorate_chart(ax, "RQ3 — Endpoint Coverage × Validity",
                   "Endpoint Coverage (%)", "Validity (%)")
    save_fig(fig, "27_scatter_ep_vs_validity.png", RQ3_DIR)


def rq3_28_scatter_tokens_vs_validity(runs):
    fig, ax = plt.subplots(figsize=FIGSIZE_MED)
    for llm in LLMS:
        xs = [r["total_tokens"] for r in runs if r["llm"] == llm]
        ys = [r["validity_pct"] for r in runs if r["llm"] == llm]
        ax.scatter(xs, ys, color=LLM_COLORS[llm], label=LLM_SHORT[llm],
                   s=60, alpha=0.75, edgecolors="white", linewidth=0.8)
    decorate_chart(ax, "RQ3 — Tokeny × Validity",
                   "Celkové tokeny", "Validity (%)")
    save_fig(fig, "28_scatter_tokens_vs_validity.png", RQ3_DIR)


def rq3_29_bubble_model_profile(runs):
    """Bubble — každý model = jeden bod (x=EP cov, y=validity, size=1/cost)."""
    fig, ax = plt.subplots(figsize=FIGSIZE_MED)
    for llm in LLMS:
        x = mean(r["endpoint_coverage_pct"] for r in runs if r["llm"] == llm)
        y = mean(r["validity_pct"] for r in runs if r["llm"] == llm)
        cost = mean(r["cost_usd"] for r in runs if r["llm"] == llm)
        size = 1 / cost * 200
        ax.scatter(x, y, s=size, color=LLM_COLORS[llm], label=LLM_SHORT[llm],
                   alpha=0.6, edgecolors="white", linewidth=1.5)
        ax.annotate(f"{LLM_SHORT[llm]}\n(${cost:.4f})", (x, y), fontsize=8,
                    xytext=(8, 8), textcoords="offset points")
    decorate_chart(ax, "RQ3 — Bubble profil modelů (velikost = 1/cena)",
                   "Endpoint Coverage (%)", "Validity (%)")
    save_fig(fig, "29_bubble_model_profile.png", RQ3_DIR)


def rq3_30_bar_100pct_runs(runs):
    """Sloupcový — počet 100% runů per model × úroveň."""
    counts = {llm: {lvl: 0 for lvl in LEVELS} for llm in LLMS}
    for r in runs:
        if r["all_passed"]:
            counts[r["llm"]][r["level"]] += 1
    fig, ax = plt.subplots(figsize=FIGSIZE_WIDE)
    x = np.arange(len(LEVELS)); w = 0.25
    for i, llm in enumerate(LLMS):
        ys = [counts[llm][lvl] for lvl in LEVELS]
        bars = ax.bar(x + (i - 1) * w, ys, w, color=LLM_COLORS[llm], label=LLM_SHORT[llm])
        for b, v in zip(bars, ys):
            ax.text(b.get_x() + b.get_width()/2, v + 0.05, str(v), ha="center", fontsize=8)
    ax.set_xticks(x); ax.set_xticklabels(LEVELS); ax.set_ylim(0, 5.5)
    decorate_chart(ax, "RQ3 — Počet 100% úspěšných runů (z 5) per model × úroveň",
                   "Úroveň kontextu", "Počet 100% runů")
    save_fig(fig, "30_bar_100pct_runs.png", RQ3_DIR)


def rq3_31_heatmap_runwise_validity(runs):
    """15 runů × 5 úrovní — zrnitá heatmapa pro detailní pohled."""
    rows_labels = []
    M = []
    for llm in LLMS:
        for rid in range(1, 6):
            row = []
            for lvl in LEVELS:
                vals = [r["validity_pct"] for r in runs
                        if r["llm"] == llm and r["level"] == lvl and r["run_id"] == rid]
                row.append(vals[0] if vals else np.nan)
            M.append(row)
            rows_labels.append(f"{LLM_SHORT[llm]}-r{rid}")
    M = np.array(M)
    fig, ax = plt.subplots(figsize=(7, 9))
    im = ax.imshow(M, cmap=HEATMAP_CMAP, aspect="auto", vmin=55, vmax=100)
    ax.set_xticks(range(len(LEVELS))); ax.set_xticklabels(LEVELS)
    ax.set_yticks(range(len(rows_labels))); ax.set_yticklabels(rows_labels, fontsize=7)
    for i in range(M.shape[0]):
        for j in range(M.shape[1]):
            if not np.isnan(M[i, j]):
                c = "white" if M[i, j] < 75 else "black"
                ax.text(j, i, f"{M[i,j]:.0f}", ha="center", va="center", fontsize=7, color=c)
    fig.colorbar(im, ax=ax, shrink=0.5, label="Validity (%)")
    ax.set_title("RQ3 — Per-run heatmapa validity (15 runů × 5 úrovní)", fontsize=11)
    save_fig(fig, "31_heatmap_runwise_validity.png", RQ3_DIR)


def rq3_32_convergence_divergence(runs):
    """Rozpětí validity mezi modely (konvergence napříč úrovněmi)."""
    m = model_level_matrix(runs, "validity_pct")
    spreads = []
    for lvl in LEVELS:
        vals = [m[llm][lvl] for llm in LLMS]
        spreads.append(max(vals) - min(vals))
    fig, ax = plt.subplots(figsize=FIGSIZE_MED)
    x = np.arange(len(LEVELS))
    bars = ax.bar(x, spreads, color=LEVEL_COLORS, edgecolor="black", linewidth=0.5, alpha=0.85)
    for b, v in zip(bars, spreads):
        ax.text(b.get_x() + b.get_width()/2, v + 0.2, f"{v:.2f}",
                ha="center", fontsize=9)
    ax.set_xticks(x); ax.set_xticklabels(LEVELS)
    decorate_chart(ax, "RQ3 — Rozpětí validity mezi modely (konvergence)",
                   "Úroveň kontextu", "Max−Min rozpětí (pp)", legend=False)
    save_fig(fig, "32_bar_convergence_spread.png", RQ3_DIR)


def rq3_33_std_per_level(runs):
    """Std validity per úroveň — jak moc se modely rozcházejí."""
    m = model_level_matrix(runs, "validity_pct")
    stds = [stdev([m[llm][lvl] for llm in LLMS]) for lvl in LEVELS]
    fig, ax = plt.subplots(figsize=FIGSIZE_MED)
    x = np.arange(len(LEVELS))
    ax.plot(x, stds, marker="o", linewidth=2.5, color="#C44E52")
    ax.fill_between(x, 0, stds, alpha=0.2, color="#C44E52")
    for i, v in enumerate(stds):
        ax.text(i, v + 0.2, f"{v:.2f}", ha="center", fontsize=9)
    ax.set_xticks(x); ax.set_xticklabels(LEVELS)
    decorate_chart(ax, "RQ3 — Divergence modelů (σ validity per úroveň)",
                   "Úroveň kontextu", "σ validity (pp)", legend=False)
    save_fig(fig, "33_line_std_per_level.png", RQ3_DIR)


def rq3_34_pie_test_types_per_model(runs):
    for llm in LLMS:
        vals = {
            "happy_path": mean(r["happy_pct"] for r in runs if r["llm"] == llm),
            "error":      mean(r["error_pct"] for r in runs if r["llm"] == llm),
            "edge_case":  mean(r["edge_pct"] for r in runs if r["llm"] == llm),
        }
        fig, ax = plt.subplots(figsize=FIGSIZE_SQUARE)
        colors = ["#55A467", "#C44E52", "#DD8452"]
        ax.pie(list(vals.values()), labels=list(vals.keys()), autopct="%1.1f%%",
               colors=colors, wedgeprops=dict(width=0.55, edgecolor="white"))
        ax.set_title(f"RQ3 — Distribuce typů testů — {LLM_SHORT[llm]}", fontsize=11)
        save_fig(fig, f"34_pie_test_types_{LLM_SHORT[llm]}.png", RQ3_DIR)


def rq3_35_stacked_bar_tokens_by_phase(runs):
    """Stacked tokens per fáze, 3 subploty (jeden per model)."""
    plan = model_level_matrix(runs, "phase_planning")
    gen = model_level_matrix(runs, "phase_generation")
    rep = model_level_matrix(runs, "phase_repair")
    fig, axs = plt.subplots(1, 3, figsize=(14, 5), sharey=True)
    for ax, llm in zip(axs, LLMS):
        x = np.arange(len(LEVELS))
        p = [plan[llm][l] for l in LEVELS]
        g = [gen[llm][l] for l in LEVELS]
        r = [rep[llm][l] for l in LEVELS]
        ax.bar(x, p, color="#4C72B0", label="planning")
        ax.bar(x, g, bottom=p, color="#DD8452", label="generation")
        ax.bar(x, r, bottom=[a + b for a, b in zip(p, g)], color="#C44E52", label="repair")
        ax.set_xticks(x); ax.set_xticklabels(LEVELS)
        ax.set_title(LLM_SHORT[llm])
        ax.grid(True, linestyle="--", linewidth=0.4, alpha=0.5)
    axs[0].set_ylabel("Tokeny")
    axs[-1].legend(fontsize=8)
    fig.suptitle("RQ3 — Rozložení tokenů do fází per model", fontsize=11)
    save_fig(fig, "35_stacked_tokens_phase_per_model.png", RQ3_DIR)


def rq3_36_bar_cost_totals(runs):
    """Sloupcový — celkové náklady na všech 25 runů per model."""
    totals = {llm: sum(r["cost_usd"] for r in runs if r["llm"] == llm) for llm in LLMS}
    fig, ax = plt.subplots(figsize=FIGSIZE_MED)
    x = np.arange(len(LLMS))
    ys = [totals[llm] for llm in LLMS]
    bars = ax.bar(x, ys, color=[LLM_COLORS[l] for l in LLMS],
                  edgecolor="black", linewidth=0.5, alpha=0.85)
    for b, v in zip(bars, ys):
        ax.text(b.get_x() + b.get_width()/2, v + 0.02, f"${v:.4f}", ha="center", fontsize=10)
    ax.set_xticks(x); ax.set_xticklabels([LLM_SHORT[l] for l in LLMS])
    decorate_chart(ax, "RQ3 — Celkové náklady na 25 runů per model",
                   "Model", "Celková cena (USD)", legend=False)
    save_fig(fig, "36_bar_total_cost.png", RQ3_DIR)


def rq3_37_line_validity_with_range(runs):
    """Multi-line validity s vyznačeným rozpětím mezi nejlepším a nejhorším LLM."""
    m = model_level_matrix(runs, "validity_pct")
    fig, ax = plt.subplots(figsize=FIGSIZE_MED)
    x = np.arange(len(LEVELS))
    mins = [min(m[llm][lvl] for llm in LLMS) for lvl in LEVELS]
    maxs = [max(m[llm][lvl] for llm in LLMS) for lvl in LEVELS]
    ax.fill_between(x, mins, maxs, alpha=0.15, color="gray", label="Rozpětí min–max")
    for llm in LLMS:
        ys = [m[llm][lvl] for lvl in LEVELS]
        ax.plot(x, ys, marker="o", linewidth=2, color=LLM_COLORS[llm], label=LLM_SHORT[llm])
    ax.set_xticks(x); ax.set_xticklabels(LEVELS)
    decorate_chart(ax, "RQ3 — Validity per model s vyznačeným rozpětím",
                   "Úroveň kontextu", "Validity (%)")
    save_fig(fig, "37_line_validity_with_range.png", RQ3_DIR)


def rq3_38_scatter_assertion_vs_response(runs):
    """Assertion × Response — per model."""
    fig, ax = plt.subplots(figsize=FIGSIZE_MED)
    for llm in LLMS:
        xs = [r["assertion_depth"] for r in runs if r["llm"] == llm]
        ys = [r["response_validation_pct"] for r in runs if r["llm"] == llm]
        ax.scatter(xs, ys, color=LLM_COLORS[llm], label=LLM_SHORT[llm],
                   s=60, alpha=0.75, edgecolors="white", linewidth=0.8)
    decorate_chart(ax, "RQ3 — Assertion Depth × Response Validation",
                   "Assertion Depth", "Response Validation (%)")
    save_fig(fig, "38_scatter_assertion_vs_response.png", RQ3_DIR)


def rq3_39_multi_heatmap_all_metrics(runs):
    """4× heatmapa vedle sebe — validity, EP cov, crud cov, cena."""
    fig, axs = plt.subplots(1, 4, figsize=(16, 4))
    metrics = [
        ("Validity (%)", "validity_pct", HEATMAP_CMAP, None),
        ("EP Cov (%)", "endpoint_coverage_pct", SEQUENTIAL_CMAP, None),
        ("crud.py (%)", "code_cov_crud", HEATMAP_CMAP, None),
        ("Cena (USD)", "cost_usd", "Reds", None),
    ]
    for ax, (name, key, cmap, _) in zip(axs, metrics):
        m = model_level_matrix(runs, key)
        M = np.array([[m[llm][lvl] for lvl in LEVELS] for llm in LLMS])
        im = ax.imshow(M, cmap=cmap, aspect="auto")
        ax.set_xticks(range(len(LEVELS))); ax.set_xticklabels(LEVELS)
        ax.set_yticks(range(len(LLMS))); ax.set_yticklabels([LLM_SHORT[l] for l in LLMS], fontsize=8)
        for i in range(M.shape[0]):
            for j in range(M.shape[1]):
                val = M[i, j]
                txt = f"{val:.3f}" if key == "cost_usd" else f"{val:.1f}"
                ax.text(j, i, txt, ha="center", va="center", fontsize=7)
        ax.set_title(name, fontsize=10)
        fig.colorbar(im, ax=ax, shrink=0.7)
    fig.suptitle("RQ3 — Multi-heatmapa: 4 metriky × 3 modely × 5 úrovní", fontsize=11)
    save_fig(fig, "39_multi_heatmap_all.png", RQ3_DIR)


def rq3_40_scatter_matrix(runs):
    """Scatter matrix — 4 hlavní metriky × 3 modely."""
    keys = ["validity_pct", "endpoint_coverage_pct", "assertion_depth", "response_validation_pct"]
    labels = ["Validity", "EP Cov", "Assert D", "Resp Val"]
    fig, axs = plt.subplots(len(keys), len(keys), figsize=(11, 11))
    for i, k1 in enumerate(keys):
        for j, k2 in enumerate(keys):
            ax = axs[i, j]
            if i == j:
                for llm in LLMS:
                    vals = [r[k1] for r in runs if r["llm"] == llm]
                    ax.hist(vals, bins=8, color=LLM_COLORS[llm], alpha=0.55, edgecolor="white")
            else:
                for llm in LLMS:
                    xs = [r[k2] for r in runs if r["llm"] == llm]
                    ys = [r[k1] for r in runs if r["llm"] == llm]
                    ax.scatter(xs, ys, color=LLM_COLORS[llm], s=15, alpha=0.6,
                               edgecolors="white", linewidth=0.3)
            if i == len(keys) - 1:
                ax.set_xlabel(labels[j], fontsize=8)
            if j == 0:
                ax.set_ylabel(labels[i], fontsize=8)
            ax.tick_params(labelsize=6)
    fig.suptitle("RQ3 — Scatter matrix 4×4 (3 modely, 75 runů)", fontsize=12)
    save_fig(fig, "40_scatter_matrix.png", RQ3_DIR)


def rq3_41_bubble_validity_ep_cost(runs):
    """Bubble — všechny 75 runů."""
    fig, ax = plt.subplots(figsize=FIGSIZE_WIDE)
    for llm in LLMS:
        xs = [r["validity_pct"] for r in runs if r["llm"] == llm]
        ys = [r["endpoint_coverage_pct"] for r in runs if r["llm"] == llm]
        ss = [r["cost_usd"] * 10000 for r in runs if r["llm"] == llm]
        ax.scatter(xs, ys, s=ss, color=LLM_COLORS[llm], label=LLM_SHORT[llm],
                   alpha=0.5, edgecolors="white", linewidth=0.8)
    decorate_chart(ax, "RQ3 — Bubble: Validity × EP Coverage × Cena (velikost)",
                   "Validity (%)", "Endpoint Coverage (%)")
    save_fig(fig, "41_bubble_validity_ep_cost.png", RQ3_DIR)


# ─── MAIN ────────────────────────────────────────────────────────────────────
def main():
    runs = load_runs()
    print(f"Loaded {len(runs)} runs total")

    builders = {
        "RQ1": [
            rq1_01_line_validity, rq1_02_line_assertion_depth,
            rq1_03_line_response_validation, rq1_04_line_diversity,
            rq1_05_bar_validity, rq1_06_bar_assertion_depth,
            rq1_07_bar_response_validation, rq1_08_bar_diversity,
            rq1_09_box_validity, rq1_10_box_assertion_depth,
            rq1_11_box_response_validation, rq1_12_violin_validity,
            rq1_13_violin_assertion_depth, rq1_14_hist_validity,
            rq1_15_hist_assertion_depth, rq1_16_hist_response_validation,
            rq1_17_stacked_area_test_types, rq1_18_stacked_bar_test_types,
            rq1_19_pie_test_types_per_level, rq1_20_status_code_distribution,
            rq1_21_pie_status_codes, rq1_22_status_codes_per_level_heatmap,
            rq1_23_multi_line_all_quality_metrics, rq1_24_scatter_assertion_vs_validity,
            rq1_25_scatter_response_vs_validity, rq1_26_radar_levels,
            rq1_27_parallel_coords, rq1_28_bar_stale_tests,
            rq1_29_line_stale_tests, rq1_30_pie_overall_test_types,
        ],
        "RQ2": [
            rq2_01_line_endpoint_coverage, rq2_02_line_total_code_coverage,
            rq2_03_line_crud_coverage, rq2_04_line_main_coverage,
            rq2_05_bar_endpoint_coverage, rq2_06_bar_total_coverage,
            rq2_07_bar_crud_coverage, rq2_08_box_endpoint_coverage,
            rq2_09_violin_endpoint_coverage, rq2_10_hist_endpoint_coverage,
            rq2_11_hist_crud_coverage, rq2_12_combined_coverage_layers,
            rq2_13_delta_from_baseline, rq2_14_scatter_endpoint_vs_crud,
            rq2_15_scatter_total_vs_crud, rq2_16_stacked_bar_coverage_layers,
            rq2_17_radar_coverage, rq2_18_area_coverage_growth,
            rq2_19_heatmap_coverage_per_level, rq2_20_hypothesis_falsification,
            rq2_21_scatter_with_regression, rq2_22_saturation_curve,
            rq2_23_donut_crud_coverage, rq2_24_dual_axis_ep_vs_code,
            rq2_25_multi_line_all_coverage,
        ],
        "RQ3": [
            rq3_01_line_validity, rq3_02_line_assertion_depth,
            rq3_03_line_response_validation, rq3_04_line_endpoint_coverage,
            rq3_05_line_total_code_coverage, rq3_06_line_crud_coverage,
            rq3_07_line_cost, rq3_08_line_stale_tests,
            rq3_09_line_diversity, rq3_10_line_iterations,
            rq3_11_line_tokens, rq3_12_bar_validity_grouped,
            rq3_13_bar_cost_grouped, rq3_14_bar_endpoint_coverage_grouped,
            rq3_15_bar_crud_coverage_grouped, rq3_16_heatmap_validity,
            rq3_17_heatmap_ep_coverage, rq3_18_heatmap_crud_coverage,
            rq3_19_heatmap_delta_validity, rq3_20_box_validity_by_model,
            rq3_21_box_cost_by_model, rq3_22_box_ep_coverage_by_model,
            rq3_23_violin_validity_per_model, rq3_24_radar_models,
            rq3_25_parallel_coords_models, rq3_26_scatter_cost_vs_validity,
            rq3_27_scatter_ep_vs_validity, rq3_28_scatter_tokens_vs_validity,
            rq3_29_bubble_model_profile, rq3_30_bar_100pct_runs,
            rq3_31_heatmap_runwise_validity, rq3_32_convergence_divergence,
            rq3_33_std_per_level, rq3_34_pie_test_types_per_model,
            rq3_35_stacked_bar_tokens_by_phase, rq3_36_bar_cost_totals,
            rq3_37_line_validity_with_range, rq3_38_scatter_assertion_vs_response,
            rq3_39_multi_heatmap_all_metrics, rq3_40_scatter_matrix,
            rq3_41_bubble_validity_ep_cost,
        ],
    }

    for rq_name, funcs in builders.items():
        print(f"\n=== {rq_name} ({len(funcs)} buildrů) ===")
        for i, b in enumerate(funcs, 1):
            try:
                b(runs)
                print(f"  [{i:>2}/{len(funcs)}] OK: {b.__name__}")
            except Exception as e:
                print(f"  [{i:>2}/{len(funcs)}] FAIL: {b.__name__} -> {e}")

    print("\n=== Souhrn ===")
    for d, name in [(RQ1_DIR, "RQ1"), (RQ2_DIR, "RQ2"), (RQ3_DIR, "RQ3")]:
        n = len(list(d.glob("*.png")))
        print(f"  {name}: {n} grafů v {d.name}/")


if __name__ == "__main__":
    main()