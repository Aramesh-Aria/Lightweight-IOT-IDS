"""Model factories: SEL, single models, and the possibly-leaky SEL of Algorithm 1.
Phase 3 adds class_weight, PCA, SMOTE and a homogeneous SEL (HSEL).

Every model sits inside Pipeline(MinMaxScaler -> ColumnSelector(top-k) -> model).
MinMaxScaler outputs an ndarray, so ColumnSelector selects by integer index.
The selector lives in this module so joblib can pickle the pipeline.

Timed fits use n_jobs=1 everywhere, so train and predict times are comparable.
"""

import time
from dataclasses import dataclass

import numpy as np
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.decomposition import PCA
from sklearn.ensemble import StackingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.naive_bayes import GaussianNB
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder, MinMaxScaler
from sklearn.tree import DecisionTreeClassifier

SINGLE_MODELS = ("DT", "LR", "NB")


class ColumnSelector(BaseEstimator, TransformerMixin):
    """Keep the given column indices (None keeps all columns)."""

    def __init__(self, indices=None):
        self.indices = indices

    def fit(self, X, y=None):
        return self

    def transform(self, X):
        if self.indices is None:
            return X
        return np.asarray(X)[:, list(self.indices)]


def make_lr(class_weight=None) -> LogisticRegression:
    # Q34: only max_iter is changed from the scikit-learn defaults.
    # class_weight is set only in the phase-3 class_weight experiment.
    return LogisticRegression(max_iter=1000, class_weight=class_weight)


def make_dt(seed: int, class_weight=None, max_depth=None) -> DecisionTreeClassifier:
    return DecisionTreeClassifier(random_state=seed, class_weight=class_weight, max_depth=max_depth)


def make_nb() -> GaussianNB:
    return GaussianNB()


def make_sel(seed: int, stack_method: str = "predict", class_weight=None) -> StackingClassifier:
    """SEL: NB + LR base learners, DT meta-learner, passthrough features.

    stack_method="predict" is the main setting (Q42, Table 10 of the paper:
    the meta-learner receives predicted labels). "predict_proba" is a side
    comparison. The meta-learner is trained on 5-fold cross-validated
    predictions of the training data, so this is the leakage-free variant.

    class_weight (phase 3) is passed to LR and DT; GaussianNB has no such
    parameter and stays unweighted.
    """
    return StackingClassifier(
        estimators=[("nb", make_nb()), ("lr", make_lr(class_weight))],
        final_estimator=make_dt(seed, class_weight),
        passthrough=True,
        stack_method=stack_method,
        n_jobs=1,
    )


HSEL_DEPTHS = (4, 8, 16)


def make_hsel(seed: int) -> StackingClassifier:
    """Homogeneous SEL (optional, phase 3): three DTs of depth 4, 8 and 16 as
    base learners, the same DT meta-learner, passthrough, predicted labels."""
    return StackingClassifier(
        estimators=[(f"dt{d}", make_dt(seed, max_depth=d)) for d in HSEL_DEPTHS],
        final_estimator=make_dt(seed),
        passthrough=True,
        stack_method="predict",
        n_jobs=1,
    )


def make_single(name: str, seed: int):
    if name == "DT":
        return make_dt(seed)
    if name == "LR":
        return make_lr()
    if name == "NB":
        return make_nb()
    raise ValueError(f"Unknown model: {name}")


def make_pipeline(model, indices=None, pca_components=None, smote_seed=None, seed=0):
    """MinMaxScaler -> ColumnSelector (or PCA) -> [SMOTE] -> model.

    pca_components=k puts PCA(n_components=k) after the scaler in place of the
    selector (phase 3). smote_seed adds SMOTE before the model; imblearn's
    Pipeline applies it only in fit, so only training rows are resampled.
    """
    reduce = (("pca", PCA(n_components=pca_components, random_state=seed))
              if pca_components is not None else ("select", ColumnSelector(indices)))
    steps = [("scaler", MinMaxScaler()), reduce]
    if smote_seed is None:
        return Pipeline(steps + [("model", model)])
    from imblearn.over_sampling import SMOTE
    from imblearn.pipeline import Pipeline as ImbPipeline
    return ImbPipeline(steps + [("smote", SMOTE(random_state=smote_seed)), ("model", model)])


@dataclass
class LeakyResult:
    """Output of fit_leaky_sel. y_pred is on the same test rows the meta-learner saw."""

    y_pred: np.ndarray
    train_time_s: float
    predict_time_s: float
    pipeline: object  # dict of fitted parts, used only for the size measurement


def fit_leaky_sel(X_train, y_train, X_test, y_test, indices, seed: int) -> LeakyResult:
    """Our reading of Algorithm 1 of the main paper (possible leakage, Q41).

    Algorithm 1 (p. 5): base learners are trained on S1 (train) and predict S2
    (test) to get WL; the ensemble dataset D' = F u WL is built; the
    meta-learner is trained on D' and tested on S2. Read literally, the
    meta-learner is trained and scored on the test rows. Section text on p. 4
    instead says predictions are added to the training data, so the leakage is
    only possible, not certain. This function measures the possible effect of
    leakage under Algorithm 1.

    Base learner outputs are predicted labels (stack_method="predict"), encoded
    with LabelEncoder (sorted class names), the same encoding StackingClassifier
    uses internally.
    """
    encoder = LabelEncoder().fit(y_train)
    ytr = encoder.transform(y_train)
    yte = encoder.transform(y_test)

    t0 = time.perf_counter()
    scaler = MinMaxScaler().fit(X_train)
    selector = ColumnSelector(indices)
    Xtr = selector.transform(scaler.transform(X_train))
    Xte = selector.transform(scaler.transform(X_test))

    nb = make_nb().fit(Xtr, ytr)
    lr = make_lr().fit(Xtr, ytr)
    # Base-learning step: predictions WL on the test set S2.
    wl = np.column_stack([nb.predict(Xte), lr.predict(Xte)])
    # Meta-learning step: D' = F u WL, built from the test rows.
    d_prime = np.hstack([wl, Xte])
    meta = make_dt(seed).fit(d_prime, yte)
    train_time = time.perf_counter() - t0

    t1 = time.perf_counter()
    y_pred = meta.predict(d_prime)
    predict_time = time.perf_counter() - t1

    parts = {"scaler": scaler, "select": selector, "nb": nb, "lr": lr, "meta": meta}
    return LeakyResult(
        y_pred=encoder.inverse_transform(y_pred),
        train_time_s=train_time,
        predict_time_s=predict_time,
        pipeline=parts,
    )
