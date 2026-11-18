"""Feature ranking: FI (ExtraTrees entropy importance) and PFI (permutation importance).

Both methods see MinMax-scaled data. The scaler is fit on X_fit only, and both
rankings are computed from X_fit (PFI is then evaluated on X_val), so FI and
PFI are compared on equal terms.

Ties (for example the 8 constant columns, which always score 0) are broken by
the original column order, using a stable sort, so top-k is reproducible.
"""

import time

import numpy as np
import pandas as pd
from sklearn.ensemble import ExtraTreesClassifier
from sklearn.inspection import permutation_importance
from sklearn.preprocessing import MinMaxScaler

PFI_N_REPEATS = 10
PFI_SCORING = "f1_macro"


def _scale(X_fit: pd.DataFrame, *others: pd.DataFrame):
    scaler = MinMaxScaler().fit(X_fit)
    return [scaler.transform(X_fit)] + [scaler.transform(X) for X in others]


def _make_extratrees(seed: int) -> ExtraTreesClassifier:
    return ExtraTreesClassifier(criterion="entropy", random_state=seed, n_jobs=-1)


def _ranking_frame(columns, mean, std=None) -> pd.DataFrame:
    """Sort by importance (descending), ties broken by column order."""
    order = np.argsort(-np.asarray(mean), kind="stable")
    df = pd.DataFrame(
        {
            "rank": np.arange(1, len(order) + 1),
            "feature": np.asarray(columns)[order],
            "column_index": order,
            "importance": np.asarray(mean)[order],
        }
    )
    if std is not None:
        df["importance_std"] = np.asarray(std)[order]
    return df


def rank_fi(X_fit: pd.DataFrame, y_fit: pd.Series, seed: int) -> pd.DataFrame:
    """FI ranking from ExtraTrees(criterion='entropy').feature_importances_."""
    t0 = time.perf_counter()
    (Xf,) = _scale(X_fit)
    et = _make_extratrees(seed).fit(Xf, y_fit)
    df = _ranking_frame(X_fit.columns, et.feature_importances_)
    df.attrs["ranking_time_s"] = time.perf_counter() - t0
    return df


def rank_pfi(
    X_fit: pd.DataFrame,
    y_fit: pd.Series,
    X_val: pd.DataFrame,
    y_val: pd.Series,
    seed: int,
) -> pd.DataFrame:
    """PFI ranking: ExtraTrees fit on X_fit, permutation importance on X_val.

    Importance is the mean drop in macro-F1 over n_repeats=10 shuffles; the
    standard deviation of that drop is returned too.
    """
    t0 = time.perf_counter()
    Xf, Xv = _scale(X_fit, X_val)
    et = _make_extratrees(seed).fit(Xf, y_fit)
    result = permutation_importance(
        et,
        Xv,
        y_val,
        scoring=PFI_SCORING,
        n_repeats=PFI_N_REPEATS,
        random_state=seed,
        n_jobs=-1,
    )
    df = _ranking_frame(X_fit.columns, result.importances_mean, result.importances_std)
    df.attrs["ranking_time_s"] = time.perf_counter() - t0
    return df
