"""Metrics, timing and pipeline size.

Macro averages are the main metrics (Q27); weighted averages go to the appendix.
All metrics are in percent. labels=CLASS_ORDER fixes the order of per-class
results and of the confusion matrix; zero_division=0 covers classes a model
never predicts.
"""

import os
import tempfile
import time

import joblib
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    precision_recall_fscore_support,
)

from . import config


def compute_metrics(y_true, y_pred) -> dict:
    labels = config.CLASS_ORDER
    out = {"accuracy": 100 * accuracy_score(y_true, y_pred)}
    for avg in ("macro", "weighted"):
        p, r, f, _ = precision_recall_fscore_support(
            y_true, y_pred, labels=labels, average=avg, zero_division=0
        )
        out[f"precision_{avg}"] = 100 * p
        out[f"recall_{avg}"] = 100 * r
        out[f"f1_{avg}"] = 100 * f
    p, r, f, s = precision_recall_fscore_support(
        y_true, y_pred, labels=labels, average=None, zero_division=0
    )
    out["per_class"] = {
        c: {"precision": 100 * p[i], "recall": 100 * r[i], "f1": 100 * f[i], "support": int(s[i])}
        for i, c in enumerate(labels)
    }
    out["confusion_matrix"] = confusion_matrix(y_true, y_pred, labels=labels).tolist()
    return out


def pipeline_size_bytes(obj) -> int:
    """Size of the joblib dump of the whole fitted pipeline."""
    fd, path = tempfile.mkstemp(suffix=".joblib")
    os.close(fd)
    try:
        joblib.dump(obj, path)
        return os.path.getsize(path)
    finally:
        os.remove(path)


def fit_and_evaluate(pipeline, X_train, y_train, X_test, y_test) -> dict:
    """Fit, time train and predict with perf_counter, score and measure size."""
    t0 = time.perf_counter()
    pipeline.fit(X_train, y_train)
    train_time = time.perf_counter() - t0

    t1 = time.perf_counter()
    y_pred = pipeline.predict(X_test)
    predict_time = time.perf_counter() - t1

    result = compute_metrics(y_test, y_pred)
    result["train_time_s"] = train_time
    result["predict_time_s"] = predict_time
    result["size_bytes"] = pipeline_size_bytes(pipeline)
    return result
