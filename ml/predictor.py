"""Small, reusable interface for Phase 2 road-impact predictions."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from ml.train_model import DEFAULT_MODEL_PATH, FEATURE_COLUMNS


class RoadImpactPredictor:
    """Load the selected pipeline and predict bounded road-impact scores."""

    def __init__(self, model_path: str | Path = DEFAULT_MODEL_PATH) -> None:
        self.model_path = Path(model_path)
        if not self.model_path.exists():
            raise FileNotFoundError(
                f"Model file not found at {self.model_path}. Run ml/train_model.py first."
            )
        self.model = joblib.load(self.model_path)

    @staticmethod
    def _to_feature_frame(
        features: pd.DataFrame | Mapping[str, object] | Iterable[Mapping[str, object]],
    ) -> pd.DataFrame:
        if isinstance(features, pd.DataFrame):
            frame = features.copy()
        elif isinstance(features, Mapping):
            frame = pd.DataFrame([features])
        else:
            frame = pd.DataFrame(list(features))

        missing = set(FEATURE_COLUMNS).difference(frame.columns)
        if missing:
            raise ValueError(f"Prediction input is missing features: {sorted(missing)}")
        return frame[FEATURE_COLUMNS]

    def predict(
        self,
        features: pd.DataFrame | Mapping[str, object] | Iterable[Mapping[str, object]],
    ) -> np.ndarray:
        """Return one bounded [0, 1] prediction per supplied road segment."""
        frame = self._to_feature_frame(features)
        predictions = self.model.predict(frame)
        return np.clip(np.asarray(predictions, dtype=float), 0.0, 1.0)


def predict(
    features: pd.DataFrame | Mapping[str, object] | Iterable[Mapping[str, object]],
    model_path: str | Path = DEFAULT_MODEL_PATH,
) -> np.ndarray:
    """Convenience function for later live GDACS inference code."""
    return RoadImpactPredictor(model_path).predict(features)
