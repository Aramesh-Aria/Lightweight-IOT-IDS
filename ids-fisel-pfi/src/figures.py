"""Phase-2 figures (PNG, dpi=200) built from results/tables and the run cache."""

import json

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from . import config, plot_style as ps
from .tables import PAPER_TABLE6_SEL, PAPER_TABLE9, RUNS_DIR

T = config.TABLES_DIR
F = config.FIGURES_DIR
K_LABELS = [str(k) for k in config.K_VALUES] + ["all"]
K_TICKS = [str(k) for k in config.K_VALUES] + ["All (42)"]
SHORT = {"Information gathering": "Info. gathering"}


def _kpos(k_series):
    return k_series.astype(str).map({k: i for i, k in enumerate(K_LABELS)}).to_numpy()


def _k_axis(ax):
    ax.set_xticks(range(len(K_LABELS)), K_TICKS)
    ax.set_xlabel("Number of selected features (k)")
    ax.grid(axis="x", visible=False)


def _bar_ends(ax):
    """Small rounded look is not native in matplotlib; keep thin bars with a surface edge."""
    for p in ax.patches:
        p.set_edgecolor(ps.PAPER)
        p.set_linewidth(1.0)


# ---------------------------------------------------------------- 1. rankings

def fig_rankings(top=20):
    fig, axes = plt.subplots(1, 2, figsize=(10, 5.6))
    for ax, m in zip(axes, ("FI", "PFI")):
        t = pd.read_csv(T / f"{m.lower()}_ranking.csv").head(top).iloc[::-1]
        y = np.arange(len(t))
        xerr = t["importance_std"] if m == "PFI" else None
        ax.barh(y, t["importance"], height=0.66, color=ps.METHOD_COLORS[m],
                xerr=xerr, error_kw={"ecolor": ps.INK_2, "elinewidth": 1, "capsize": 2})
        _bar_ends(ax)
        ax.set_yticks(y, t["feature"])
        for lbl, in_paper in zip(ax.get_yticklabels(), t["in_paper_top8"]):
            if in_paper:
                lbl.set_fontweight("bold")
                lbl.set_color(ps.INK)
        ax.axhline(len(t) - 8 - 0.5, color=ps.ALERT, lw=1, ls=(0, (4, 3)))
        ax.text(ax.get_xlim()[1], len(t) - 8 - 0.35, "top 8 above", color=ps.ALERT,
                ha="right", va="bottom", fontsize=8)
        ax.grid(axis="y", visible=False)
        if m == "FI":
            ax.set_title("FI: ExtraTrees entropy importance")
            ax.set_xlabel("Importance (mean impurity decrease)")
        else:
            ax.set_title("PFI: permutation importance on validation")
            ax.set_xlabel("Mean drop in macro-F1 (±1 std, 10 repeats)")
    fig.text(0.01, -0.01, "Seed 42, ranking fit on the fit split. Bold names: the 8 features "
             "selected by the main paper.", color=ps.MUTED, fontsize=8)
    fig.tight_layout()
    ps.save(fig, F / "importance_ranking_fi_pfi.png")


# ---------------------------------------------------------------- 2. F1 vs k

def fig_f1_vs_k():
    a = pd.read_csv(T / "ksweep_5seeds.csv")
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    for m in ("FI", "PFI"):
        d = a[a["method"] == m]
        x = _kpos(d["k"])
        mu, sd = d["f1_macro_mean"].to_numpy(), d["f1_macro_std"].to_numpy()
        c = ps.METHOD_COLORS[m]
        ax.fill_between(x, mu - sd, mu + sd, color=c, alpha=0.16, lw=0)
        ax.plot(x, mu, color=c, marker="o", markersize=6, markeredgecolor=ps.PAPER,
                markeredgewidth=1.5, label=f"{m}-SEL (mean ± std, 5 seeds)")
        ax.annotate(f"{m}-SEL", (x[4], mu[4]), textcoords="offset points",
                    xytext=(0, -15 if m == "FI" else 9), color=ps.INK_2, fontsize=8.5, ha="center")
    px = [_kpos(pd.Series(["8"]))[0], _kpos(pd.Series(["all"]))[0]]
    py = [PAPER_TABLE9[8]["f1_macro"], PAPER_TABLE9["all"]["f1_macro"]]
    ax.scatter(px, py, marker="D", s=40, color=ps.ALERT, zorder=5, edgecolor=ps.PAPER,
               label="Main paper, Table 9 (FI-SEL)")
    _k_axis(ax)
    ax.set_ylabel("Macro-F1 (%)")
    ax.set_title("Macro-F1 of SEL by number of features")
    ax.legend(loc="lower right")
    fig.tight_layout()
    ps.save(fig, F / "f1_macro_vs_k.png")


# ---------------------------------------------------------------- 3. per-class recall

def fig_per_class_recall():
    d = pd.read_csv(T / "per_class_k8.csv")
    d = d[d["k"].astype(str) == "8"]
    classes = config.CLASS_ORDER
    x = np.arange(len(classes))
    w = 0.36
    fig, ax = plt.subplots(figsize=(7.6, 4.2))
    mi = classes.index("MITM")
    ax.axvspan(mi - 0.5, mi + 0.5, color=ps.SOFT_ORANGE, zorder=0)
    for i, m in enumerate(("FI", "PFI")):
        s = d[d["method"] == m].set_index("class").loc[classes]
        bars = ax.bar(x + (i - 0.5) * w, s["recall_mean"], w * 0.94, yerr=s["recall_std"],
                      color=ps.METHOD_COLORS[m], label=f"{m}-SEL, k=8",
                      error_kw={"ecolor": ps.INK_2, "elinewidth": 1, "capsize": 2})
        ax.bar_label(bars, fmt="%.1f", fontsize=7, color=ps.INK_2, padding=2)
    ax.scatter([mi - w / 2], [PAPER_TABLE6_SEL["MITM"][1]], marker="D", s=40, color=ps.ALERT,
               zorder=5, edgecolor=ps.PAPER, label="Main paper, MITM recall (all features)")
    _bar_ends(ax)
    ax.set_xticks(x, [SHORT.get(c, c) for c in classes])
    ax.get_xticklabels()[mi].set_color(ps.ALERT)
    ax.get_xticklabels()[mi].set_fontweight("bold")
    ax.grid(axis="x", visible=False)
    ax.set_ylim(0, 112)
    ax.set_ylabel("Recall (%)")
    ax.set_title("Per-class recall of SEL at k=8 (mean ± std, 5 seeds)")
    ax.legend(loc="upper center", ncols=3, bbox_to_anchor=(0.5, -0.1))
    fig.tight_layout()
    ps.save(fig, F / "per_class_recall_k8.png")


# ---------------------------------------------------------------- 4. confusion

def fig_confusion():
    fig, axes = plt.subplots(1, 2, figsize=(10.4, 4.6))
    labels = [SHORT.get(c, c) for c in config.CLASS_ORDER]
    for ax, m in zip(axes, ("FI", "PFI")):
        key = f"SEL_{m}_k8_seed{config.MAIN_SEED}_dedup0_clean_predict"
        cm = np.array(json.loads((RUNS_DIR / f"{key}.json").read_text())["confusion_matrix"])
        pct = 100 * cm / cm.sum(axis=1, keepdims=True)
        ax.imshow(pct, cmap=ps.SEQ_CMAP, vmin=0, vmax=100)
        for i in range(len(labels)):
            for j in range(len(labels)):
                ax.text(j, i, f"{pct[i, j]:.1f}\n({cm[i, j]})", ha="center", va="center",
                        fontsize=6.8, color=ps.PAPER if pct[i, j] > 55 else ps.INK)
        ax.set_xticks(range(len(labels)), labels, rotation=30, ha="right")
        ax.set_yticks(range(len(labels)), labels)
        ax.grid(False)
        for s in ax.spines.values():
            s.set_visible(False)
        ax.set_xlabel("Predicted class")
        ax.set_ylabel("True class")
        ax.set_title(f"{m}-SEL, k=8")
    fig.text(0.01, -0.02, "Seed 42 test split. Cells: share of the true class (%) and row count.",
             color=ps.MUTED, fontsize=8)
    fig.tight_layout()
    ps.save(fig, F / "confusion_matrix_k8.png")


# ---------------------------------------------------------------- 5. cost vs k

def fig_cost_vs_k():
    a = pd.read_csv(T / "ksweep_5seeds.csv")
    specs = [("train_time_s", "Training time (s)", 1),
             ("predict_time_s", "Prediction time on test (s)", 1),
             ("size_bytes", "Pipeline size, joblib (MB)", 1e-6)]
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.8))
    for ax, (col, title, scale) in zip(axes, specs):
        for m in ("FI", "PFI"):
            d = a[a["method"] == m]
            x = _kpos(d["k"])
            mu = d[f"{col}_mean"].to_numpy() * scale
            sd = d[f"{col}_std"].to_numpy() * scale
            c = ps.METHOD_COLORS[m]
            ax.fill_between(x, mu - sd, mu + sd, color=c, alpha=0.16, lw=0)
            ax.plot(x, mu, color=c, marker="o", markeredgecolor=ps.PAPER,
                    markeredgewidth=1.5, label=f"{m}-SEL")
        _k_axis(ax)
        ax.set_title(title)
        ax.set_ylim(bottom=0)
    axes[0].legend(loc="upper left")
    fig.text(0.01, -0.03, "Mean ± std over 5 seeds, MacBook Air M4, models with n_jobs=1.",
             color=ps.MUTED, fontsize=8)
    fig.tight_layout()
    ps.save(fig, F / "cost_vs_k.png")


# ---------------------------------------------------------------- 6. leaky vs clean

def fig_leaky_vs_clean():
    d = pd.read_csv(T / "leaky_vs_clean.csv")
    d["k"] = d["k"].astype(str)
    groups = [("ALL", "all", "All features"), ("FI", "8", "FI, k=8"), ("PFI", "8", "PFI, k=8")]
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    w = 0.36
    for ax, (col, title) in zip(axes, [("f1_macro", "Macro-F1 (%)"), ("mitm_recall", "MITM recall (%)")]):
        x = np.arange(len(groups))
        for i, (variant, color, name) in enumerate(
                [("clean", ps.NEUTRAL, "Leakage-free (cross-validated meta-learner)"),
                 ("leaky", ps.ALERT, "Possible leakage, Algorithm 1 reading")]):
            vals = [d[(d["variant"] == variant) & (d["method"] == m) & (d["k"] == k)].iloc[0]
                    for m, k, _ in groups]
            bars = ax.bar(x + (i - 0.5) * w, [v[f"{col}_mean"] for v in vals], w * 0.94,
                          yerr=[v[f"{col}_std"] for v in vals], color=color, label=name,
                          error_kw={"ecolor": ps.INK_2, "elinewidth": 1, "capsize": 2})
            ax.bar_label(bars, fmt="%.1f", fontsize=7.5, color=ps.INK_2, padding=2)
        if col == "f1_macro":
            ax.scatter([-w / 2, 1 - w / 2], [PAPER_TABLE9["all"]["f1_macro"], PAPER_TABLE9[8]["f1_macro"]],
                       marker="D", s=40, color=ps.INK, zorder=5, edgecolor=ps.PAPER,
                       label="Main paper (F1: Table 9, MITM recall: Table 6)")
        else:
            ax.scatter([-w / 2], [PAPER_TABLE6_SEL["MITM"][1]], marker="D", s=40, color=ps.INK,
                       zorder=5, edgecolor=ps.PAPER)
        _bar_ends(ax)
        ax.set_xticks(x, [g[2] for g in groups])
        ax.grid(axis="x", visible=False)
        ax.set_ylim(0, 112)
        ax.set_title(title)
    h, lab = axes[0].get_legend_handles_labels()
    fig.legend(h, lab, loc="lower center", ncols=3, bbox_to_anchor=(0.5, -0.06))
    fig.text(0.01, 1.0, "SEL with and without the possible leakage of Algorithm 1 (mean ± std, 5 seeds)",
             fontweight="bold", fontsize=11, color=ps.INK)
    fig.tight_layout(rect=(0, 0.04, 1, 0.96))
    ps.save(fig, F / "leaky_vs_clean.png")


def build_all():
    ps.apply()
    F.mkdir(parents=True, exist_ok=True)
    fig_rankings()
    fig_f1_vs_k()
    fig_per_class_recall()
    fig_confusion()
    fig_cost_vs_k()
    fig_leaky_vs_clean()
    print("figures written to", F)
