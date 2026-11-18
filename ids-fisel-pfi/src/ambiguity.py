"""Ambiguous vectors: feature vectors that appear with more than one class.

Computed on the full dataset (duplicates kept, as in the main run), over all
42 features, at class level. The main ambiguous vector is the multi-class
vector with the most MITM rows (821 MITM rows, Q44).

In this dataset the main ambiguous vector is the all-zero vector (every one
of the 42 features is 0).

The "recall ceiling" of a class assumes every row of a given vector gets one
prediction: if the vector goes to its majority class, rows of the other
classes on that vector cannot be recalled. The ceiling refers to the
42-feature space; with k selected features more rows can collapse onto the
same projected vector, so the k=8 ceiling can only be lower or equal.
"""

import pandas as pd

from . import config


def vector_class_counts(X: pd.DataFrame, y: pd.Series) -> pd.DataFrame:
    """One row per distinct feature vector, one column per class (row counts)."""
    vid = pd.util.hash_pandas_object(X, index=False)
    counts = pd.crosstab(vid.to_numpy(), y.to_numpy())
    for c in config.CLASS_ORDER:
        if c not in counts:
            counts[c] = 0
    counts = counts[config.CLASS_ORDER]
    counts.index.name = "vector_hash"
    return counts


def main_ambiguous_vector(X: pd.DataFrame, y: pd.Series) -> pd.DataFrame:
    """The multi-class vector with the most MITM rows, as a 1-row DataFrame."""
    vid = pd.util.hash_pandas_object(X, index=False)
    counts = vector_class_counts(X, y)
    multi = counts[(counts > 0).sum(axis=1) > 1]
    h = multi["MITM"].idxmax()
    return X[(vid == h).to_numpy()].iloc[[0]].reset_index(drop=True)


def ambiguous_vector_table(X: pd.DataFrame, y: pd.Series) -> pd.DataFrame:
    """Q44 table: per-class rows of the main ambiguous vector and the MITM ceiling."""
    counts = vector_class_counts(X, y)
    multi = counts[(counts > 0).sum(axis=1) > 1]
    v = multi.loc[multi["MITM"].idxmax()]
    class_totals = y.value_counts()
    majority = v.idxmax()
    rows = []
    for c in config.CLASS_ORDER:
        rows.append({
            "class": c,
            "rows_on_vector": int(v[c]),
            "class_total_rows": int(class_totals[c]),
            "share_of_class_pct": 100 * v[c] / class_totals[c],
            "share_of_vector_pct": 100 * v[c] / v.sum(),
            "is_vector_majority": c == majority,
            # recall ceiling of class c if this vector is predicted as its majority class
            "recall_ceiling_if_vector_to_majority_pct":
                100 * (class_totals[c] - (0 if c == majority else v[c])) / class_totals[c],
            # best precision of class c if the whole vector is predicted as c
            # (all other rows assumed correct)
            "precision_ceiling_if_vector_to_class_pct":
                100 * class_totals[c] / (class_totals[c] + v.sum() - v[c]),
        })
    df = pd.DataFrame(rows)
    df.loc[len(df)] = {
        "class": "Total", "rows_on_vector": int(v.sum()), "class_total_rows": int(len(y)),
        "share_of_class_pct": 100 * v.sum() / len(y), "share_of_vector_pct": 100.0,
        "is_vector_majority": False, "recall_ceiling_if_vector_to_majority_pct": float("nan"),
        "precision_ceiling_if_vector_to_class_pct": float("nan"),
    }
    return df


def ambiguous_summary_table(X: pd.DataFrame, y: pd.Series) -> pd.DataFrame:
    """All multi-class vectors: per class rows involved and recall ceiling
    under majority assignment (each vector predicted as its majority class)."""
    counts = vector_class_counts(X, y)
    multi = counts[(counts > 0).sum(axis=1) > 1]
    majority = multi.idxmax(axis=1)
    class_totals = y.value_counts()
    rows = []
    for c in config.CLASS_ORDER:
        on_multi = int(multi[c].sum())
        lost = int(multi.loc[majority != c, c].sum())
        n_vec = int((multi[c] > 0).sum())
        rows.append({
            "class": c,
            "class_total_rows": int(class_totals[c]),
            "n_multiclass_vectors_with_class": n_vec,
            "rows_on_multiclass_vectors": on_multi,
            "share_of_class_on_multiclass_pct": 100 * on_multi / class_totals[c],
            "rows_lost_under_majority": lost,
            "recall_ceiling_majority_pct": 100 * (class_totals[c] - lost) / class_totals[c],
        })
    df = pd.DataFrame(rows)
    lost_all = int(df["rows_lost_under_majority"].sum())
    df.loc[len(df)] = {
        "class": "Total", "class_total_rows": int(len(y)),
        "n_multiclass_vectors_with_class": int(len(multi)),
        "rows_on_multiclass_vectors": int(multi.to_numpy().sum()),
        "share_of_class_on_multiclass_pct": 100 * multi.to_numpy().sum() / len(y),
        "rows_lost_under_majority": lost_all,
        # for the total row: accuracy ceiling
        "recall_ceiling_majority_pct": 100 * (len(y) - lost_all) / len(y),
    }
    return df


def projected_vector_table(X: pd.DataFrame, y: pd.Series, columns) -> pd.DataFrame:
    """Rows per class that share the main ambiguous vector after keeping only
    `columns` (for example the FI top 8). Shows how the vector grows in a
    reduced feature space."""
    v = main_ambiguous_vector(X, y)[list(columns)].iloc[0]
    hit = (X[list(columns)] == v).all(axis=1).to_numpy()
    full = (X == main_ambiguous_vector(X, y).iloc[0]).all(axis=1).to_numpy()
    totals = y.value_counts()
    rows = []
    for c in config.CLASS_ORDER:
        m = (y == c).to_numpy()
        rows.append({"class": c, "rows_on_vector_42": int((full & m).sum()),
                     "rows_on_vector_projected": int((hit & m).sum()),
                     "class_total_rows": int(totals[c])})
    df = pd.DataFrame(rows)
    df.loc[len(df)] = {"class": "Total", "rows_on_vector_42": int(full.sum()),
                       "rows_on_vector_projected": int(hit.sum()), "class_total_rows": int(len(y))}
    return df
