# ids-fisel-pfi

این پوشه کد بازپیاده‌سازی روش FI-SEL مقاله‌ی Abdulkareem و همکاران (۲۰۲۴) را نگه می‌دارد. این روش برای تشخیص نفوذ سبک‌وزن در IoT روی دیتاست Edge-IIoTset (نسخه‌ی ML) به کار می‌رود. کد روش FI را با PFI، MI و PCA مقایسه می‌کند و دو نسخه‌ی بدون نشت و دارای نشت SEL را می‌سنجد. منطق اصلی در `src/` قرار دارد و نتایج در `results/` ذخیره می‌شوند.

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

```bash
.venv/bin/python -m src.check_data      # data sanity checks -> results/tables/class_counts.csv
.venv/bin/python run_experiments.py timing    # quick runtime estimate
.venv/bin/python run_experiments.py all       # every phase-2 experiment, tables and figures (~45 min)
```

Each experiment also runs alone: `rank`, `ksweep`, `single`, `leaky`, `stack`,
`dedup`, `tables`, `figures`. Use `--seeds 42` for one seed and `--force` to
ignore the cache in `results/cache/` (git-ignored).

## Layout

```
data/              dataset (git-ignored)
src/config.py      paths, seeds, k values, dropped columns, class mapping
src/data.py        load_dataset(dedup), split(X, y, seed)
src/check_data.py  sanity checks for the data module
src/selection.py   rank_fi, rank_pfi (ExtraTrees entropy; permutation importance)
src/models.py      SEL, single models, pipeline, fit_leaky_sel (Algorithm 1 reading)
src/evaluate.py    metrics, timing, joblib pipeline size
src/tables.py      CSV tables from the cache
src/figures.py     figures (dpi=200)
src/plot_style.py  shared figure style (palette, Instrument Sans)
run_experiments.py experiment runner with cache
notebooks/         walkthrough notebook
results/tables/    CSV tables
results/figures/   figures
```
