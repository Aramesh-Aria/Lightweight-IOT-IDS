"""Build the phase-2 and phase-3 CSV tables from the cached runs and rankings.

Phase-3 tables go to new files; the phase-2 tables filter on variant="clean"
and methods FI/PFI so the phase-3 runs never change them.

All metrics are percentages. "mean" and "std" are over the 5 seeds
(config.SEEDS); std uses ddof=1.
"""

import json

import numpy as np
import pandas as pd

from . import config

CACHE_DIR = config.RESULTS_DIR / "cache"
RUNS_DIR = CACHE_DIR / "runs"
RANK_DIR = CACHE_DIR / "rankings"
T = config.TABLES_DIR

METRICS = [
    "accuracy", "precision_macro", "recall_macro", "f1_macro",
    "precision_weighted", "recall_weighted", "f1_weighted",
    "train_time_s", "predict_time_s", "size_bytes",
]

# Main paper, Table 9 (FI-SEL, all features vs 8 features)
PAPER_TABLE9 = {
    "all": {"accuracy": 89.05, "precision_macro": 90.94, "recall_macro": 79.53,
            "f1_macro": 82.00, "train_time_s": 37.23, "predict_time_s": 0.28},
    8: {"accuracy": 87.37, "precision_macro": 90.65, "recall_macro": 77.73,
        "f1_macro": 80.88, "train_time_s": 16.18, "predict_time_s": 0.10},
}
# Main paper, Table 5 (all features)
PAPER_TABLE5 = {
    "DT": (73.43, 60.85, 63.13, 60.38),
    "LR": (60.43, 67.26, 52.60, 55.64),
    "NB": (53.53, 64.88, 44.64, 46.72),
    "SEL": (89.05, 90.94, 79.53, 82.00),
}
# Main paper, Table 6, heterogeneous SEL (all features): precision, recall, F1
PAPER_TABLE6_SEL = {
    "Normal": (94.69, 94.22, 94.45),
    "DDoS": (91.46, 91.60, 91.53),
    "Information gathering": (91.10, 91.73, 91.41),
    "MITM": (100.00, 29.22, 45.22),
    "Injection": (84.26, 83.20, 83.78),
    "Malware": (84.12, 87.13, 85.60),
}


def load_runs() -> pd.DataFrame:
    rows = [json.loads(p.read_text()) for p in sorted(RUNS_DIR.glob("*.json"))]
    df = pd.DataFrame(rows)
    df["k"] = df["k"].astype(str)
    return df


def _select(df, **kw):
    m = pd.Series(True, index=df.index)
    for c, v in kw.items():
        m &= df[c] == v
    return df[m]


def _agg(df, by):
    g = df.groupby(by, sort=False)[METRICS]
    out = g.mean().add_suffix("_mean").join(g.std(ddof=1).add_suffix("_std"))
    out["n_seeds"] = g.size()
    cols = [c for m in METRICS for c in (f"{m}_mean", f"{m}_std")] + ["n_seeds"]
    return out[cols].reset_index()


def _k_sort(df):
    order = {str(k): i for i, k in enumerate(config.K_VALUES)} | {"all": 99}
    return df.assign(_o=df["k"].map(order)).sort_values(["_o"]).drop(columns="_o")


def _sweep_rows(runs, seeds=None, methods=("FI", "PFI")):
    """Main SEL (clean, predict, no dedup); the k=all row is shared by all methods."""
    base = _select(runs, model="SEL", variant="clean", stack_method="predict", dedup=False)
    if seeds is not None:
        base = base[base["seed"].isin(seeds)]
    parts = []
    for m in methods:
        sub = base[(base["method"] == m) | (base["method"] == "ALL")].copy()
        sub["method"] = m
        parts.append(sub)
    return pd.concat(parts, ignore_index=True)


# ---------------------------------------------------------------- tables

def ranking_tables():
    out = {}
    for m in ("FI", "PFI"):
        main = pd.read_csv(RANK_DIR / f"{m}_seed{config.MAIN_SEED}_dedup0.csv")
        allseeds = []
        for s in config.SEEDS:
            r = pd.read_csv(RANK_DIR / f"{m}_seed{s}_dedup0.csv")[["feature", "rank", "importance"]]
            allseeds.append(r.assign(seed=s))
        a = pd.concat(allseeds)
        stats = a.groupby("feature").agg(
            importance_mean_5seeds=("importance", "mean"),
            importance_std_5seeds=("importance", lambda x: x.std(ddof=1)),
            rank_mean_5seeds=("rank", "mean"),
            times_in_top8=("rank", lambda x: int((x <= 8).sum())),
        )
        t = main.merge(stats, left_on="feature", right_index=True)
        t["positive_importance"] = t["importance"] > 0
        t["in_paper_top8"] = t["feature"].isin(config.PAPER_TOP8)
        t["constant_column"] = t["feature"].isin(config.CONSTANT_COLUMNS)
        name = "fi_ranking.csv" if m == "FI" else "pfi_ranking.csv"
        t.to_csv(T / name, index=False)
        out[m] = t
    return out


def ksweep_tables(runs):
    s42 = _sweep_rows(runs, [config.MAIN_SEED])
    cols = ["method", "k", "n_features"] + METRICS + ["lr_max_iter_used", "convergence_warnings", "features"]
    s42 = _k_sort(s42[cols].copy())
    s42["features"] = s42["features"].map(lambda f: ";".join(f) if len(f) < config.N_FEATURES else "all")
    s42 = s42.sort_values(["method"], kind="stable")
    s42.to_csv(T / "ksweep_seed42.csv", index=False)

    five = _sweep_rows(runs, config.SEEDS)
    agg = _agg(five, ["method", "k"])
    agg = _k_sort(agg).sort_values(["method"], kind="stable")
    agg.to_csv(T / "ksweep_5seeds.csv", index=False)
    return s42, agg


def single_models_table(runs):
    base = _select(runs, variant="clean", stack_method="predict", dedup=False)
    base = base[base["k"].isin(["all", "8"]) & base["seed"].isin(config.SEEDS)]
    base = base[base["method"].isin(["ALL", "FI", "PFI"])]  # MI/PCA rows are phase 3
    agg = _agg(base, ["model", "method", "k"])
    order = {"DT": 0, "LR": 1, "NB": 2, "SEL": 3}
    agg = agg.assign(_o=agg["model"].map(order)).sort_values(["_o", "k", "method"]).drop(columns="_o")
    for i, name in enumerate(["accuracy", "precision_macro", "recall_macro", "f1_macro"]):
        agg[f"paper_{name}"] = [
            PAPER_TABLE5[mdl][i] if k == "all" else np.nan
            for mdl, k in zip(agg["model"], agg["k"])
        ]
    agg.to_csv(T / "single_models.csv", index=False)
    return agg


def per_class_table(runs):
    base = _sweep_rows(runs, config.SEEDS)
    base = base[base["k"].isin(["8", "all"])]
    rows = []
    for (m, k), g in base.groupby(["method", "k"], sort=False):
        for c in config.CLASS_ORDER:
            vals = {met: [r[c][met] for r in g["per_class"]] for met in ("precision", "recall", "f1")}
            s42 = g[g["seed"] == config.MAIN_SEED]["per_class"].iloc[0][c]
            row = {"method": m, "k": k, "class": c, "support": s42["support"]}
            for met, v in vals.items():
                row[f"{met}_seed42"] = s42[met]
                row[f"{met}_mean"] = float(np.mean(v))
                row[f"{met}_std"] = float(np.std(v, ddof=1))
            pp = PAPER_TABLE6_SEL[c] if k == "all" else (np.nan,) * 3
            row["paper_precision"], row["paper_recall"], row["paper_f1"] = pp
            rows.append(row)
    df = pd.DataFrame(rows)
    df = df.assign(_k=df["k"].map({"8": 0, "all": 1})).sort_values(["_k", "method"], kind="stable").drop(columns="_k")
    df.to_csv(T / "per_class_k8.csv", index=False)
    return df


def leaky_table(runs):
    base = _select(runs, model="SEL", stack_method="predict", dedup=False)
    base = base[base["k"].isin(["all", "8"]) & base["seed"].isin(config.SEEDS)]
    base = base[base["method"].isin(["ALL", "FI", "PFI"]) & base["variant"].isin(["clean", "leaky"])]
    agg = _agg(base, ["variant", "method", "k"])
    mitm = base.assign(mitm_recall=base["per_class"].map(lambda p: p["MITM"]["recall"]))
    mr = mitm.groupby(["variant", "method", "k"])["mitm_recall"].agg(["mean", "std"])
    mr.columns = ["mitm_recall_mean", "mitm_recall_std"]
    agg = agg.merge(mr, left_on=["variant", "method", "k"], right_index=True)
    agg = agg.sort_values(["method", "k", "variant"]).reset_index(drop=True)
    agg.to_csv(T / "leaky_vs_clean.csv", index=False)
    return agg


def stack_method_table(runs):
    base = _select(runs, model="SEL", variant="clean", dedup=False)
    base = base[base["k"].isin(["all", "8"]) & base["method"].isin(["ALL", "FI"])]
    agg = _agg(base, ["stack_method", "method", "k"])
    agg = agg.sort_values(["k", "stack_method"]).reset_index(drop=True)
    agg.to_csv(T / "stack_method_comparison.csv", index=False)
    return agg


def _test_rows_seen_in_train(seed):
    """Share of test rows whose exact (features, class) row also appears in train."""
    from . import data
    X, y = data.load_dataset()
    s = data.split(X, y, seed)
    tr = pd.util.hash_pandas_object(s.X_train.assign(c=s.y_train), index=False)
    te = pd.util.hash_pandas_object(s.X_test.assign(c=s.y_test), index=False)
    mitm = (s.y_test == "MITM").to_numpy()
    seen = te.isin(set(tr)).to_numpy()
    return 100 * seen.mean(), 100 * seen[mitm].mean()


def dedup_table(runs):
    base = _select(runs, model="SEL", variant="clean", stack_method="predict")
    base = base[base["k"].isin(["all", "8"]) & base["seed"].isin(config.SEEDS)]
    base = base[base["method"].isin(["ALL", "FI", "PFI"])]
    base = base.assign(mitm_recall=base["per_class"].map(lambda p: p["MITM"]["recall"]),
                       mitm_support=base["per_class"].map(lambda p: p["MITM"]["support"]))
    agg = _agg(base, ["dedup", "method", "k"])
    extra = base.groupby(["dedup", "method", "k"]).agg(
        mitm_recall_mean=("mitm_recall", "mean"),
        mitm_recall_std=("mitm_recall", lambda x: x.std(ddof=1)),
        mitm_test_support=("mitm_support", "mean"),
        n_test=("n_test", "mean"),
    )
    agg = agg.merge(extra, left_on=["dedup", "method", "k"], right_index=True)
    seen_all, seen_mitm = _test_rows_seen_in_train(config.MAIN_SEED)
    agg["test_rows_seen_in_train_pct_seed42"] = np.where(agg["dedup"], 0.0, seen_all)
    agg["mitm_test_rows_seen_in_train_pct_seed42"] = np.where(agg["dedup"], 0.0, seen_mitm)
    agg = agg.sort_values(["method", "k", "dedup"]).reset_index(drop=True)
    agg.to_csv(T / "dedup_sensitivity.csv", index=False)
    return agg


def paper_vs_ours(runs):
    runs = runs[runs["variant"].isin(["clean", "leaky"])]
    base = _select(runs, model="SEL", stack_method="predict", dedup=False, method="ALL")
    base = pd.concat([base, _select(runs, model="SEL", stack_method="predict", dedup=False, method="FI", k="8")])
    rows = []
    for variant in ("clean", "leaky"):
        v = base[base["variant"] == variant]
        for k in ("all", "8"):
            g = v[v["k"] == k]
            g42 = g[g["seed"] == config.MAIN_SEED].iloc[0]
            pk = "all" if k == "all" else 8
            for met, pval in PAPER_TABLE9[pk].items():
                rows.append({
                    "variant": variant, "k": k, "metric": met, "paper": pval,
                    "ours_seed42": g42[met], "ours_mean_5seeds": g[met].mean(),
                    "ours_std_5seeds": g[met].std(ddof=1),
                })
    df = pd.DataFrame(rows)
    df["diff_mean_minus_paper"] = df["ours_mean_5seeds"] - df["paper"]

    # Ratios k=8 / all features (comparable across hardware, Q21)
    ratio_rows = []
    for variant in ("clean", "leaky"):
        for met in ("train_time_s", "predict_time_s", "f1_macro", "accuracy"):
            p = PAPER_TABLE9[8][met] / PAPER_TABLE9["all"][met]
            d = df[(df["variant"] == variant) & (df["metric"] == met)].set_index("k")
            ratio_rows.append({
                "variant": variant, "k": "8/all", "metric": f"ratio_{met}", "paper": p,
                "ours_seed42": d.loc["8", "ours_seed42"] / d.loc["all", "ours_seed42"],
                "ours_mean_5seeds": d.loc["8", "ours_mean_5seeds"] / d.loc["all", "ours_mean_5seeds"],
                "ours_std_5seeds": np.nan, "diff_mean_minus_paper": np.nan,
            })
        sz = base[(base["variant"] == variant)].groupby("k")["size_bytes"].mean()
        ratio_rows.append({
            "variant": variant, "k": "8/all", "metric": "ratio_size_bytes", "paper": np.nan,
            "ours_seed42": np.nan, "ours_mean_5seeds": sz["8"] / sz["all"],
            "ours_std_5seeds": np.nan, "diff_mean_minus_paper": np.nan,
        })
    df = pd.concat([df, pd.DataFrame(ratio_rows)], ignore_index=True)
    df.to_csv(T / "paper_vs_ours.csv", index=False)
    return df


# ---------------------------------------------------------------- phase 3

ALL_METHODS = ("FI", "PFI", "MI", "PCA")
FOCUS_CLASSES = ("MITM", "Malware", "DDoS")


def _ranking_time_mean(method):
    if method == "PCA":
        return np.nan  # PCA fit time is inside train_time_s
    ts = [json.loads((RANK_DIR / f"{method}_seed{s}_dedup0.json").read_text())["ranking_time_s"]
          for s in config.SEEDS]
    return float(np.mean(ts))


def mi_ranking_table():
    main = pd.read_csv(RANK_DIR / f"MI_seed{config.MAIN_SEED}_dedup0.csv")
    a = pd.concat([pd.read_csv(RANK_DIR / f"MI_seed{s}_dedup0.csv").assign(seed=s) for s in config.SEEDS])
    stats = a.groupby("feature").agg(
        importance_mean_5seeds=("importance", "mean"),
        importance_std_5seeds=("importance", lambda x: x.std(ddof=1)),
        rank_mean_5seeds=("rank", "mean"),
        times_in_top8=("rank", lambda x: int((x <= 8).sum())),
    )
    t = main.merge(stats, left_on="feature", right_index=True)
    t["in_paper_top8"] = t["feature"].isin(config.PAPER_TOP8)
    t["constant_column"] = t["feature"].isin(config.CONSTANT_COLUMNS)
    t.to_csv(T / "mi_ranking.csv", index=False)
    return t


def ksweep_all_methods_tables(runs):
    """FI, PFI, MI and PCA side by side (new files; phase-2 tables unchanged)."""
    s42 = _sweep_rows(runs, [config.MAIN_SEED], ALL_METHODS)
    cols = ["method", "k", "n_features", "accuracy", "precision_macro", "recall_macro", "f1_macro",
            "train_time_s", "predict_time_s", "size_bytes", "features"]
    s42 = _k_sort(s42[cols].copy())
    s42["features"] = s42["features"].map(lambda f: ";".join(f) if len(f) < config.N_FEATURES else "all")
    s42 = s42.assign(_m=s42["method"].map({m: i for i, m in enumerate(ALL_METHODS)}))
    s42 = s42.sort_values("_m", kind="stable").drop(columns="_m")
    s42.to_csv(T / "ksweep_all_methods_seed42.csv", index=False)

    five = _sweep_rows(runs, config.SEEDS, ALL_METHODS)
    five = five.assign(mitm_recall=five["per_class"].map(lambda p: p["MITM"]["recall"]))
    agg = _agg(five, ["method", "k"])
    mr = five.groupby(["method", "k"])["mitm_recall"].agg(
        mitm_recall_mean="mean", mitm_recall_std=lambda x: x.std(ddof=1))
    agg = agg.merge(mr, left_on=["method", "k"], right_index=True)
    agg["ranking_time_s_mean"] = [np.nan if k == "all" else _ranking_time_mean(m)
                                  for m, k in zip(agg["method"], agg["k"])]
    agg = _k_sort(agg)
    agg = agg.assign(_m=agg["method"].map({m: i for i, m in enumerate(ALL_METHODS)}))
    agg = agg.sort_values("_m", kind="stable").drop(columns="_m")
    agg.to_csv(T / "ksweep_all_methods_5seeds.csv", index=False)
    return s42, agg


def _with_class_metrics(df):
    df = df.copy()
    for c in FOCUS_CLASSES:
        for met in ("precision", "recall", "f1"):
            df[f"{c}_{met}"] = df["per_class"].map(lambda p, c=c, met=met: p[c][met])
    return df


def class_weight_table(runs):
    """Balanced vs unweighted SEL, FI/PFI k=8, 5 seeds."""
    base = _select(runs, model="SEL", stack_method="predict", dedup=False, k="8")
    base = base[base["variant"].isin(["unweighted_ref", "balanced"]) & base["method"].isin(["FI", "PFI"])]
    base = _with_class_metrics(base)
    focus = [f"{c}_{m}" for c in FOCUS_CLASSES for m in ("precision", "recall", "f1")]
    cols = ["accuracy", "f1_macro", "precision_macro", "recall_macro"] + focus + ["train_time_s"]
    g = base.groupby(["method", "variant"], sort=False)[cols]
    out = g.mean().add_suffix("_mean").join(g.std(ddof=1).add_suffix("_std"))
    out = out[[c for m in cols for c in (f"{m}_mean", f"{m}_std")]]
    preds = base.groupby(["method", "variant"])["ambiguous_vector_pred"].agg(
        lambda x: ";".join(f"{k}:{v}" for k, v in x.value_counts().items()))
    out["ambiguous_vector_pred_counts"] = preds
    out["n_seeds"] = g.size()
    out = out.reset_index()
    out = out.assign(_v=out["variant"].map({"unweighted_ref": 0, "balanced": 1}))
    out = out.sort_values(["method", "_v"]).drop(columns="_v")
    out.to_csv(T / "class_weight_comparison.csv", index=False)

    rows = []
    for (m, v), grp in base.groupby(["method", "variant"]):
        for c in config.CLASS_ORDER:
            row = {"method": m, "variant": v, "class": c}
            for met in ("precision", "recall", "f1"):
                vals = [p[c][met] for p in grp["per_class"]]
                row[f"{met}_mean"], row[f"{met}_std"] = float(np.mean(vals)), float(np.std(vals, ddof=1))
            rows.append(row)
    pd.DataFrame(rows).to_csv(T / "class_weight_per_class.csv", index=False)
    return out


def optional_extensions_table(runs):
    """SMOTE and homogeneous SEL against the unweighted reference (FI/PFI, k=8)."""
    base = _select(runs, stack_method="predict", dedup=False, k="8")
    base = base[base["variant"].isin(["unweighted_ref", "smote", "homogeneous"])
                & base["method"].isin(["FI", "PFI"])]
    if base.empty:
        return None
    base = _with_class_metrics(base)
    cols = ["accuracy", "f1_macro", "MITM_recall", "MITM_precision", "Malware_precision",
            "DDoS_recall", "train_time_s", "predict_time_s", "size_bytes"]
    g = base.groupby(["model", "variant", "method"], sort=False)[cols]
    out = g.mean().add_suffix("_mean").join(g.std(ddof=1).add_suffix("_std"))
    out = out[[c for m in cols for c in (f"{m}_mean", f"{m}_std")]]
    out["ambiguous_vector_pred_counts"] = base.groupby(["model", "variant", "method"])[
        "ambiguous_vector_pred"].agg(lambda x: ";".join(f"{k}:{v}" for k, v in x.value_counts().items()))
    out["n_seeds"] = g.size()
    out = out.reset_index()
    out = out.assign(_v=out["variant"].map({"unweighted_ref": 0, "smote": 1, "homogeneous": 2}))
    out = out.sort_values(["method", "_v"]).drop(columns="_v")
    out.to_csv(T / "optional_extensions.csv", index=False)
    return out


def pca_variance_table():
    """Cumulative explained variance of PCA on MinMax-scaled X_train (seed 42)."""
    from sklearn.decomposition import PCA
    from sklearn.preprocessing import MinMaxScaler
    from . import data
    X, y = data.load_dataset()
    s = data.split(X, y, config.MAIN_SEED)
    p = PCA(random_state=config.MAIN_SEED).fit(MinMaxScaler().fit_transform(s.X_train))
    cum = 100 * np.cumsum(p.explained_variance_ratio_)
    df = pd.DataFrame({"k": config.K_VALUES, "cumulative_explained_variance_pct": [cum[k - 1] for k in config.K_VALUES]})
    df.to_csv(T / "pca_explained_variance.csv", index=False)
    return df


def build_phase3(runs):
    pca_variance_table()
    mi_ranking_table()
    ksweep_all_methods_tables(runs)
    class_weight_table(runs)
    optional_extensions_table(runs)


def build_all():
    T.mkdir(parents=True, exist_ok=True)
    runs = load_runs()
    ranking_tables()
    ksweep_tables(runs)
    single_models_table(runs)
    per_class_table(runs)
    leaky_table(runs)
    stack_method_table(runs)
    dedup_table(runs)
    paper_vs_ours(runs)
    if (RANK_DIR / f"MI_seed{config.SEEDS[-1]}_dedup0.csv").exists():
        build_phase3(runs)
    print("tables written to", T)
