"""Run the phase-2 experiments one at a time, with cached intermediate results.

Usage (from ids-fisel-pfi/):
    .venv/bin/python run_experiments.py rank            # FI and PFI rankings, 5 seeds
    .venv/bin/python run_experiments.py ksweep --seeds 42
    .venv/bin/python run_experiments.py ksweep          # 5 seeds
    .venv/bin/python run_experiments.py single
    .venv/bin/python run_experiments.py leaky
    .venv/bin/python run_experiments.py stack
    .venv/bin/python run_experiments.py dedup
    .venv/bin/python run_experiments.py tables
    .venv/bin/python run_experiments.py figures
    .venv/bin/python run_experiments.py all
    .venv/bin/python run_experiments.py timing          # quick runtime estimate

Every run is cached as JSON in results/cache/runs/ and every ranking as CSV in
results/cache/rankings/. A cached config is never re-run unless --force.
Timed fits run serially in this process (models use n_jobs=1).
"""

import argparse
import json
import sys
import time
import warnings
from functools import lru_cache

import pandas as pd
from sklearn.exceptions import ConvergenceWarning

from src import config, data, evaluate, models, selection

CACHE_DIR = config.RESULTS_DIR / "cache"
RUNS_DIR = CACHE_DIR / "runs"
RANK_DIR = CACHE_DIR / "rankings"
METHODS = ("FI", "PFI")
K_ALL = "all"
K8 = 8

FORCE = False


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


# ---------------------------------------------------------------- data

@lru_cache(maxsize=2)
def get_data(dedup: bool):
    return data.load_dataset(dedup=dedup)


@lru_cache(maxsize=12)
def get_split(seed: int, dedup: bool) -> data.Split:
    X, y = get_data(dedup)
    return data.split(X, y, seed)


# ---------------------------------------------------------------- rankings

def get_ranking(method: str, seed: int, dedup: bool = False) -> pd.DataFrame:
    path = RANK_DIR / f"{method}_seed{seed}_dedup{int(dedup)}.csv"
    meta_path = path.with_suffix(".json")
    if path.exists() and not FORCE:
        return pd.read_csv(path)
    s = get_split(seed, dedup)
    log(f"ranking {method} seed={seed} dedup={dedup}")
    if method == "FI":
        df = selection.rank_fi(s.X_fit, s.y_fit, seed)
    elif method == "PFI":
        df = selection.rank_pfi(s.X_fit, s.y_fit, s.X_val, s.y_val, seed)
    else:
        raise ValueError(method)
    RANK_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    meta_path.write_text(json.dumps({"ranking_time_s": df.attrs["ranking_time_s"]}))
    log(f"  done in {df.attrs['ranking_time_s']:.1f}s")
    return df


def ranking_time(method: str, seed: int, dedup: bool = False) -> float:
    path = RANK_DIR / f"{method}_seed{seed}_dedup{int(dedup)}.json"
    return json.loads(path.read_text())["ranking_time_s"]


# ---------------------------------------------------------------- runs

def run_key(model, method, k, seed, dedup, variant, stack_method) -> str:
    if k == K_ALL:
        method = "ALL"  # selection method is irrelevant with all features
    return f"{model}_{method}_k{k}_seed{seed}_dedup{int(dedup)}_{variant}_{stack_method}"


def _lr_iterations(fitted) -> int | None:
    """Largest n_iter_ of any fitted LogisticRegression inside the object."""
    lrs = []
    if isinstance(fitted, dict):
        lrs = [fitted["lr"]]
    else:
        est = fitted.named_steps["model"]
        if hasattr(est, "named_estimators_"):
            lrs = [est.named_estimators_["lr"]]
        elif est.__class__.__name__ == "LogisticRegression":
            lrs = [est]
    if not lrs:
        return None
    return int(max(int(lr.n_iter_.max()) for lr in lrs))


def run(model="SEL", method="FI", k=K8, seed=config.MAIN_SEED, dedup=False,
        variant="clean", stack_method="predict") -> dict:
    """Run one config (or load it from cache) and return its result record."""
    key = run_key(model, method, k, seed, dedup, variant, stack_method)
    path = RUNS_DIR / f"{key}.json"
    if path.exists() and not FORCE:
        return json.loads(path.read_text())

    s = get_split(seed, dedup)
    if k == K_ALL:
        indices, features = None, list(s.X_train.columns)
        method_out = "ALL"
    else:
        ranking = get_ranking(method, seed, dedup)
        indices = ranking["column_index"].iloc[:k].tolist()
        features = ranking["feature"].iloc[:k].tolist()
        method_out = method

    log(f"run {key}")
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", ConvergenceWarning)
        if variant == "leaky":
            res = models.fit_leaky_sel(s.X_train, s.y_train, s.X_test, s.y_test, indices, seed)
            rec = evaluate.compute_metrics(s.y_test, res.y_pred)
            rec["train_time_s"] = res.train_time_s
            rec["predict_time_s"] = res.predict_time_s
            rec["size_bytes"] = evaluate.pipeline_size_bytes(res.pipeline)
            fitted = res.pipeline
        else:
            est = (models.make_sel(seed, stack_method) if model == "SEL"
                   else models.make_single(model, seed))
            pipe = models.make_pipeline(est, indices)
            rec = evaluate.fit_and_evaluate(pipe, s.X_train, s.y_train, s.X_test, s.y_test)
            fitted = pipe
    n_conv = sum(issubclass(w.category, ConvergenceWarning) for w in caught)

    rec.update(
        key=key, model=model, method=method_out, k=k,
        n_features=len(features), features=features, seed=seed, dedup=dedup,
        variant=variant, stack_method=stack_method,
        lr_max_iter_used=_lr_iterations(fitted), convergence_warnings=n_conv,
        n_train=len(s.y_train), n_test=len(s.y_test),
    )
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rec, indent=1))
    log(f"  F1-macro={rec['f1_macro']:.2f}  train={rec['train_time_s']:.1f}s  "
        f"size={rec['size_bytes'] / 1e6:.2f}MB  conv_warn={n_conv}")
    return rec


# ---------------------------------------------------------------- experiments

K_GRID = config.K_VALUES + [K_ALL]


def exp_rank(seeds):
    for seed in seeds:
        for m in METHODS:
            get_ranking(m, seed)


def exp_ksweep(seeds):
    for seed in seeds:
        for k in K_GRID:
            for m in (METHODS if k != K_ALL else ("FI",)):
                run("SEL", m, k, seed)


def exp_single(seeds):
    for seed in seeds:
        for name in models.SINGLE_MODELS:
            run(name, "FI", K_ALL, seed)
            for m in METHODS:
                run(name, m, K8, seed)


def exp_leaky(seeds):
    for seed in seeds:
        run("SEL", "FI", K_ALL, seed, variant="leaky")
        for m in METHODS:
            run("SEL", m, K8, seed, variant="leaky")


def exp_stack(seeds):
    for seed in seeds:
        for k in (K_ALL, K8):
            run("SEL", "FI", k, seed, stack_method="predict_proba")


def exp_dedup(seeds):
    for seed in seeds:
        run("SEL", "FI", K_ALL, seed, dedup=True)
        for m in METHODS:
            run("SEL", m, K8, seed, dedup=True)


def exp_timing():
    """Time one all-features SEL fit and one k=8 SEL fit (not cached)."""
    s = get_split(config.MAIN_SEED, False)
    t = time.perf_counter()
    rk = get_ranking("FI", config.MAIN_SEED)
    log(f"FI ranking: {time.perf_counter() - t:.1f}s")
    t = time.perf_counter()
    get_ranking("PFI", config.MAIN_SEED)
    log(f"PFI ranking: {time.perf_counter() - t:.1f}s")
    for k in (K_ALL, K8):
        idx = None if k == K_ALL else rk["column_index"].iloc[:k].tolist()
        pipe = models.make_pipeline(models.make_sel(config.MAIN_SEED), idx)
        t = time.perf_counter()
        pipe.fit(s.X_train, s.y_train)
        log(f"SEL fit k={k}: {time.perf_counter() - t:.1f}s")


def main(argv=None):
    global FORCE
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("command", choices=["rank", "ksweep", "single", "leaky", "stack", "dedup",
                                       "tables", "figures", "all", "timing"])
    p.add_argument("--seeds", type=int, nargs="+", default=config.SEEDS)
    p.add_argument("--force", action="store_true", help="ignore the cache")
    a = p.parse_args(argv)
    FORCE = a.force
    seeds = a.seeds

    t0 = time.perf_counter()
    cmd = a.command
    if cmd == "timing":
        exp_timing()
    if cmd in ("rank", "all"):
        exp_rank(seeds)
    if cmd in ("ksweep", "all"):
        exp_ksweep(seeds)
    if cmd in ("single", "all"):
        exp_single(seeds)
    if cmd in ("leaky", "all"):
        exp_leaky(seeds)
    if cmd in ("stack", "all"):
        exp_stack(seeds)
    if cmd in ("dedup", "all"):
        exp_dedup(seeds)
    if cmd in ("tables", "all"):
        from src import tables
        tables.build_all()
    if cmd in ("figures", "all"):
        from src import figures
        figures.build_all()
    log(f"finished '{cmd}' in {time.perf_counter() - t0:.0f}s")


if __name__ == "__main__":
    sys.exit(main())
