# ids-fisel-pfi

این پوشه کد بازپیاده‌سازی روش FI-SEL مقاله‌ی Abdulkareem و همکاران (۲۰۲۴) را نگه می‌دارد. این روش برای تشخیص نفوذ سبک‌وزن در IoT روی دیتاست Edge-IIoTset (نسخه‌ی ML) به کار می‌رود. کد روش FI را با PFI، MI و PCA مقایسه می‌کند و دو نسخه‌ی بدون نشت و دارای نشت SEL را می‌سنجد. اثر `class_weight="balanced"`، SMOTE و SEL همگن هم سنجیده می‌شود. منطق اصلی در `src/` قرار دارد و نتایج در `results/` ذخیره می‌شوند. خلاصه‌ی فارسی همه‌ی نتایج در `results/SUMMARY.md` آمده است.

## Setup

Requires Python 3.11.9 (pyenv). The dataset is not in the repository; download
`ML-EdgeIIoT-dataset.csv` from
https://www.kaggle.com/datasets/mohamedamineferrag/edgeiiotset-cyber-security-dataset-of-iot-iiot
and place it in `data/`.

```bash
~/.pyenv/versions/3.11.9/bin/python -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m ipykernel install --user --name ids-fisel-pfi
```

## Run

All commands run from `ids-fisel-pfi/`. Times are wall-clock on a MacBook Air M4
with an empty cache; a cached run is skipped, so a second call takes seconds.

| Command | What it does | Time |
|---|---|---|
| `.venv/bin/python -m src.check_data` | data sanity checks, `class_counts.csv` | ~10 s |
| `.venv/bin/python run_experiments.py timing` | one-off runtime estimate | ~2 min |
| `.venv/bin/python run_experiments.py rank` | FI and PFI rankings, 5 seeds | ~8 min |
| `.venv/bin/python run_experiments.py ksweep` | FI-SEL and PFI-SEL k-sweep, 5 seeds | ~11 min |
| `.venv/bin/python run_experiments.py single` | DT, LR, NB alone (all features, k=8) | ~1 min |
| `.venv/bin/python run_experiments.py leaky` | SEL under the Algorithm 1 reading (possible leakage) | ~1 min |
| `.venv/bin/python run_experiments.py stack` | `predict` vs `predict_proba` meta-features | ~2 min |
| `.venv/bin/python run_experiments.py dedup` | duplicates removed before the split | ~9 min |
| `.venv/bin/python run_experiments.py mipca` | MI-SEL and PCA-SEL k-sweep, 5 seeds | ~8 min |
| `.venv/bin/python run_experiments.py balanced` | `class_weight="balanced"` on LR and DT, FI/PFI k=8 | ~2 min |
| `.venv/bin/python run_experiments.py smote` | optional: SMOTE on training data only | ~3 min |
| `.venv/bin/python run_experiments.py hsel` | optional: homogeneous SEL (three DTs) | ~30 s |
| `.venv/bin/python run_experiments.py ambiguous` | ambiguous vector tables | ~10 s |
| `.venv/bin/python run_experiments.py tables` | every CSV table from the cache | ~15 s |
| `.venv/bin/python run_experiments.py figures` | every figure from the tables | ~15 s |
| `.venv/bin/python -m src.summary` | rebuild `results/SUMMARY.md` from the tables | ~2 s |
| `.venv/bin/python run_experiments.py phase3` | all phase-3 steps, then tables, figures and `SUMMARY.md` | ~14 min |
| `.venv/bin/python run_experiments.py all` | everything above (phase 2 and phase 3) | ~47 min |

Use `--seeds 42` for one seed and `--force` to ignore the cache in
`results/cache/` (git-ignored). The console log of the full run is kept in
`results/run_log.txt`.

The notebook `notebooks/demo.ipynb` is a short walkthrough (load data, class
counts, FI and PFI for seed 42, SEL at k=8, metrics, saved figures). It uses
only `src/` and runs in about 2 minutes:

```bash
.venv/bin/jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.kernel_name=ids-fisel-pfi notebooks/demo.ipynb
```

## Output files

`results/tables/` (all metrics in percent; `_mean`/`_std` are over 5 seeds):

| File | Content |
|---|---|
| `class_counts.csv` | rows per class vs Table 3 of the paper |
| `fi_ranking.csv`, `pfi_ranking.csv`, `mi_ranking.csv` | rankings for seed 42 with 5-seed statistics |
| `ksweep_seed42.csv`, `ksweep_5seeds.csv` | FI-SEL and PFI-SEL k-sweep |
| `ksweep_all_methods_seed42.csv`, `ksweep_all_methods_5seeds.csv` | FI, PFI, MI and PCA k-sweep side by side |
| `per_class_k8.csv` | per-class metrics at k=8 and all features |
| `single_models.csv` | DT, LR, NB and SEL vs Table 5 |
| `leaky_vs_clean.csv` | leakage-free vs possibly leaky SEL |
| `stack_method_comparison.csv` | `predict` vs `predict_proba` |
| `dedup_sensitivity.csv` | duplicates kept vs removed |
| `paper_vs_ours.csv` | Table 9 vs our runs, with k=8/all ratios |
| `class_weight_comparison.csv`, `class_weight_per_class.csv` | balanced vs unweighted SEL at k=8 |
| `optional_extensions.csv` | SMOTE and homogeneous SEL at k=8 |
| `pca_explained_variance.csv` | cumulative PCA explained variance per k (seed 42) |
| `ambiguous_vector.csv` | the main ambiguous vector per class, MITM recall ceiling |
| `ambiguous_vectors_summary.csv` | all multi-class vectors, recall ceiling per class |
| `ambiguous_vector_top8.csv` | the same vector in the FI and PFI top-8 feature spaces (seed 42) |

`results/figures/` (PNG, dpi=200): `importance_ranking_fi_pfi.png`,
`f1_macro_vs_k.png`, `per_class_recall_k8.png`, `confusion_matrix_k8.png`,
`cost_vs_k.png`, `leaky_vs_clean.png`, `methods_vs_k.png`, `class_weight_k8.png`.

## Layout

```
data/              dataset (git-ignored)
src/config.py      paths, seeds, k values, dropped columns, class mapping
src/data.py        load_dataset(dedup), split(X, y, seed)
src/check_data.py  sanity checks for the data module
src/selection.py   rank_fi, rank_pfi, rank_mi
src/models.py      SEL (optionally class-weighted), HSEL, single models,
                   pipeline (selector or PCA, optional SMOTE), fit_leaky_sel
src/ambiguity.py   ambiguous vector tables
src/evaluate.py    metrics, timing, joblib pipeline size
src/tables.py      CSV tables from the cache
src/figures.py     figures (dpi=200)
src/plot_style.py  shared figure style (palette, Instrument Sans)
src/summary.py     results/SUMMARY.md from the tables
run_experiments.py experiment runner with cache
notebooks/demo.ipynb  walkthrough notebook
results/tables/    CSV tables
results/figures/   figures
results/SUMMARY.md Persian summary of all results
```
