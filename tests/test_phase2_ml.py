"""Phase 2 checks for training, event grouping, artifacts, and prediction."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from ml.predictor import RoadImpactPredictor
from ml.train_model import (
    FEATURE_COLUMNS,
    GROUP_COLUMN,
    LEAKAGE_COLUMNS,
    TARGET_COLUMN,
    build_group_splits,
    load_training_data,
    train_and_select,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = PROJECT_ROOT / "ml" / "training_data.csv"


class Phase2ModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.data = load_training_data(DATA_PATH)
        cls.temp_directory = tempfile.TemporaryDirectory()
        temp_path = Path(cls.temp_directory.name)
        cls.model_path = temp_path / "model.joblib"
        cls.info_path = temp_path / "model_info.json"
        cls.info = train_and_select(DATA_PATH, cls.model_path, cls.info_path)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temp_directory.cleanup()

    def test_group_kfold_keeps_events_disjoint(self) -> None:
        n_splits, splits = build_group_splits(self.data[GROUP_COLUMN])
        self.assertEqual(n_splits, min(5, self.data[GROUP_COLUMN].nunique()))
        for train_indices, validation_indices in splits:
            train_events = set(self.data.iloc[train_indices][GROUP_COLUMN])
            validation_events = set(self.data.iloc[validation_indices][GROUP_COLUMN])
            self.assertFalse(train_events.intersection(validation_events))

    def test_all_models_report_rmse_and_selected_model_is_saved(self) -> None:
        expected_models = {
            "Dummy (Mean Baseline)",
            "Linear Regression",
            "Random Forest Regressor",
            "Gradient Boosting Regressor",
        }
        self.assertEqual(set(self.info["metrics"]), expected_models)
        for metric in self.info["metrics"].values():
            self.assertTrue(np.isfinite(metric["mean_rmse"]))
            self.assertEqual(
                len(metric["fold_rmse"]),
                self.info["training_metadata"]["actual_splits"],
            )
        self.assertIn(self.info["selected_model"], expected_models)
        self.assertTrue(self.model_path.is_file())

    def test_model_info_is_valid_and_excludes_leakage_features(self) -> None:
        with self.info_path.open(encoding="utf-8") as file:
            saved_info = json.load(file)
        self.assertEqual(saved_info["selected_model"], self.info["selected_model"])
        raw_features = saved_info["feature_information"]["raw_feature_columns"]
        self.assertEqual(raw_features, FEATURE_COLUMNS)
        self.assertFalse(set(raw_features).intersection(LEAKAGE_COLUMNS | {TARGET_COLUMN}))
        self.assertTrue(saved_info["feature_information"]["leakage_check_passed"])

    def test_predictor_returns_scores_within_bounds(self) -> None:
        predictor = RoadImpactPredictor(self.model_path)
        records = self.data[FEATURE_COLUMNS].head(3).to_dict(orient="records")
        scores = predictor.predict(records)
        self.assertEqual(len(scores), 3)
        self.assertTrue(np.all(scores >= 0.0))
        self.assertTrue(np.all(scores <= 1.0))


if __name__ == "__main__":
    unittest.main()
