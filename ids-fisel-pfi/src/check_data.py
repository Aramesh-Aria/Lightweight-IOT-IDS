"""Sanity checks for the data module. Run: python -m src.check_data"""

import numpy as np
import pandas as pd

from . import config
from .data import load_dataset, split


def main() -> None:
    X, y = load_dataset()

    # Features
    assert X.shape[1] == config.N_FEATURES, f"expected 42 features, got {X.shape[1]}"
    for col in (config.BINARY_LABEL_COLUMN, config.TYPE_COLUMN, *config.DROP_COLUMNS):
        assert col not in X.columns, f"{col} must not be in X"
    assert X.isna().sum().sum() == 0, "missing values found"
    constant = sorted(X.columns[X.nunique() == 1])
    assert constant == sorted(config.CONSTANT_COLUMNS), f"constant columns differ: {constant}"
    print(f"X shape: {X.shape}; constant columns: {len(constant)}")

    # Class counts vs Table 3 of the main paper
    counts = y.value_counts()
    for cls, expected in config.EXPECTED_CLASS_COUNTS.items():
        assert counts[cls] == expected, f"{cls}: {counts[cls]} != {expected}"
    assert set(counts.index) == set(config.CLASS_ORDER)

    # Stratification for every seed
    full_prop = counts / len(y)
    max_dev = 0.0
    for seed in config.SEEDS:
        s = split(X, y, seed)
        assert len(s.X_train) == len(s.X_fit) + len(s.X_val)
        assert s.X_train.index.sort_values().equals(
            s.X_fit.index.append(s.X_val.index).sort_values()
        )
        assert s.X_train.index.intersection(s.X_test.index).empty
        for part in (s.y_fit, s.y_val, s.y_train, s.y_test):
            dev = (part.value_counts(normalize=True) - full_prop).abs().max()
            max_dev = max(max_dev, dev)
    assert max_dev < 1e-3, f"split not stratified, max deviation {max_dev}"
    print(f"Stratification OK for seeds {config.SEEDS}; max proportion deviation {max_dev:.2e}")

    # Table with seed 42 split
    s = split(X, y, config.MAIN_SEED)
    X_d, y_d = load_dataset(dedup=True)
    print(f"Rows: {len(X)}; after dedup: {len(X_d)} (removed {len(X) - len(X_d)})")

    table = pd.DataFrame(
        {
            "paper_table3": pd.Series(config.EXPECTED_CLASS_COUNTS),
            "full": counts,
            "proportion": full_prop.round(5),
            "train": s.y_train.value_counts(),
            "fit": s.y_fit.value_counts(),
            "val": s.y_val.value_counts(),
            "test": s.y_test.value_counts(),
            "full_dedup": y_d.value_counts(),
        }
    ).reindex(config.CLASS_ORDER)
    table.index.name = "class"
    table.loc["Total"] = table.sum(numeric_only=True)
    table.loc["Total", "proportion"] = 1.0
    int_cols = [c for c in table.columns if c != "proportion"]
    table[int_cols] = table[int_cols].astype(np.int64)

    config.TABLES_DIR.mkdir(parents=True, exist_ok=True)
    out = config.TABLES_DIR / "class_counts.csv"
    table.to_csv(out)
    print(table.to_string())
    print(f"Saved {out}")
    print("All checks passed.")


if __name__ == "__main__":
    main()
