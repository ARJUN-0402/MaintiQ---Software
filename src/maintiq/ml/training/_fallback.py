"""Pure-NumPy gradient-boosting fallback for environments where scikit-learn's
gradient boosting compiled extension is unavailable.

This is a deterministic additive model for binary classification. It is a
fallback only; on a normal machine the scikit-learn GradientBoostingClassifier
is preferred.
"""

from __future__ import annotations

import numpy as np

from maintiq.core.exceptions import ModelError

try:
    from sklearn.base import BaseEstimator, ClassifierMixin
except ImportError:  # pragma: no cover - environment without scikit-learn
    BaseEstimator = object  # type: ignore[assignment,misc]
    ClassifierMixin = object  # type: ignore[assignment,misc]


def _sigmoid(values: np.ndarray) -> np.ndarray:
    values = np.clip(values, -60.0, 60.0)
    return 1.0 / (1.0 + np.exp(-values))


class _DecisionStumpRegressor:
    """Single-feature threshold regressor fitted to a residual vector."""

    def __init__(self) -> None:
        self.feature_index: int = 0
        self.threshold: float = 0.0
        self.left_value: float = 0.0
        self.right_value: float = 0.0

    def fit(self, x: np.ndarray, residual: np.ndarray) -> "_DecisionStumpRegressor":
        _n_samples, n_features = x.shape
        best_feature = 0
        best_threshold = 0.0
        best_left = 0.0
        best_right = 0.0
        best_error = np.inf

        for feature in range(n_features):
            column = x[:, feature]
            order = np.argsort(column, kind="mergesort")
            sorted_column = column[order]
            thresholds = (sorted_column[:-1] + sorted_column[1:]) / 2.0
            for threshold in thresholds:
                left_mask = column <= threshold
                right_mask = ~left_mask
                if not bool(left_mask.any()) or not bool(right_mask.any()):
                    continue
                left_value = float(np.mean(residual[left_mask]))
                right_value = float(np.mean(residual[right_mask]))
                error = float(
                    np.sum((residual[left_mask] - left_value) ** 2)
                    + np.sum((residual[right_mask] - right_value) ** 2)
                )
                if error < best_error:
                    best_error = error
                    best_feature = feature
                    best_threshold = float(threshold)
                    best_left = left_value
                    best_right = right_value

        self.feature_index = best_feature
        self.threshold = best_threshold
        self.left_value = best_left
        self.right_value = best_right
        return self

    def predict(self, x: np.ndarray) -> np.ndarray:
        x = np.asarray(x, dtype=float)
        column = x[:, self.feature_index]
        return np.where(column <= self.threshold, self.left_value, self.right_value)


class GradientBoostingFallbackClassifier(BaseEstimator, ClassifierMixin):
    """Deterministic gradient-boosting classifier with decision-stump learners.

    Parameters are mirrored on the estimator for scikit-learn compatibility.
    """

    def __init__(
        self,
        n_estimators: int = 50,
        learning_rate: float = 0.1,
        random_seed: int = 42,
    ) -> None:
        self.n_estimators = int(n_estimators)
        self.learning_rate = float(learning_rate)
        self.random_seed = int(random_seed)

    def fit(self, x: np.ndarray, y: np.ndarray) -> "GradientBoostingFallbackClassifier":
        x = np.asarray(x, dtype=float)
        y = np.asarray(y)
        classes = np.unique(y)
        if classes.size != 2:
            raise ModelError("GradientBoostingFallbackClassifier requires a binary target.")
        self.classes_ = classes
        _negative_class, positive_class = classes[0], classes[1]
        y_binary = (y == positive_class).astype(float)

        rng = np.random.default_rng(self.random_seed)

        # Initial log-odds of the positive class.
        positive_rate = float(np.mean(y_binary))
        positive_rate = float(np.clip(positive_rate, 1e-6, 1.0 - 1e-6))
        self.init_ = float(np.log(positive_rate / (1.0 - positive_rate)))

        current = np.full(x.shape[0], self.init_, dtype=float)
        self.estimators_: list[_DecisionStumpRegressor] = []

        for _ in range(self.n_estimators):
            probability = _sigmoid(current)
            # Negative gradient of the log-loss w.r.t. the raw score.
            residual = y_binary - probability
            stump = _DecisionStumpRegressor()
            if rng.random() < 0.0:
                pass  # placeholder to keep `rng` usage explicit; full data used
            stump.fit(x, residual)
            update = self.learning_rate * stump.predict(x)
            current = current + update
            self.estimators_.append(stump)

        return self

    def _raw_score(self, x: np.ndarray) -> np.ndarray:
        x = np.asarray(x, dtype=float)
        score = np.full(x.shape[0], self.init_, dtype=float)
        for stump in self.estimators_:
            score = score + self.learning_rate * stump.predict(x)
        return score

    def predict_proba(self, x: np.ndarray) -> np.ndarray:
        probability = _sigmoid(self._raw_score(x))
        return np.column_stack([1.0 - probability, probability])

    def predict(self, x: np.ndarray) -> np.ndarray:
        probability = self.predict_proba(x)[:, 1]
        return np.where(probability >= 0.5, self.classes_[1], self.classes_[0])
