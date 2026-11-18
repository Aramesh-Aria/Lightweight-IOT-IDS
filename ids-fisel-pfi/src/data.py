"""Dataset loading and splitting.

Scaling is NOT done here: MinMaxScaler is part of each model pipeline and is
fit on training data only.
"""

from dataclasses import dataclass

import pandas as pd
from sklearn.model_selection import train_test_split

from . import config


@dataclass
class Split:
    """Stratified split. X_train == X_fit + X_val (same rows, same index)."""

    X_fit: pd.DataFrame
    X_val: pd.DataFrame
    X_train: pd.DataFrame
    X_test: pd.DataFrame
    y_fit: pd.Series
    y_val: pd.Series
    y_train: pd.Series
    y_test: pd.Series


def load_raw() -> pd.DataFrame:
    """Read the CSV as-is."""
    return pd.read_csv(config.DATA_FILE, low_memory=False)


def load_dataset(dedup: bool = False) -> tuple[pd.DataFrame, pd.Series]:
    """Return X (42 numeric features) and y (6 classes).

    The 19 paper columns and both label columns are removed from X.
    If dedup is True, rows that are duplicated after the column drop
    (features + attack type) are removed before any split.
    """
    df = load_raw().drop(columns=config.DROP_COLUMNS)
    df = df.drop(columns=[config.BINARY_LABEL_COLUMN])

    if dedup:
        df = df.drop_duplicates().reset_index(drop=True)

    unknown = set(df[config.TYPE_COLUMN].unique()) - set(config.ATTACK_TYPE_TO_CLASS)
    if unknown:
        raise ValueError(f"Unmapped attack types: {sorted(unknown)}")

    y = df[config.TYPE_COLUMN].map(config.ATTACK_TYPE_TO_CLASS).rename("class")
    X = df.drop(columns=[config.TYPE_COLUMN]).astype("float64")
    return X, y


def split(X: pd.DataFrame, y: pd.Series, seed: int) -> Split:
    """80/20 stratified train/test, then 80/20 stratified fit/val inside train."""
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=config.TEST_SIZE, stratify=y, random_state=seed
    )
    X_fit, X_val, y_fit, y_val = train_test_split(
        X_train, y_train, test_size=config.VAL_SIZE, stratify=y_train, random_state=seed
    )
    return Split(
        X_fit=X_fit, X_val=X_val, X_train=X_train, X_test=X_test,
        y_fit=y_fit, y_val=y_val, y_train=y_train, y_test=y_test,
    )
