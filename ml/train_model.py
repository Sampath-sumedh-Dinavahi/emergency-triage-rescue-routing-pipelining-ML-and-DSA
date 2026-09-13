"""Train and select the Phase 2 road-impact regression model.

The model intentionally uses event-held-out validation.  Roads from a single
disaster are spatially related, so putting roads from the same event in both a
training and validation split would make the reported error overly optimistic.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


TARGET_COLUMN = "road_impact_score"
GROUP_COLUMN = "event_id"

# These are the Phase 1 spatial-overlap label components.  They must never be
# passed to the model because they would reveal the answer it is meant to learn.
LEAKAGE_COLUMNS = {
    TARGET_COLUMN,
    "fraction_inside_polygon",
    "road_inside_polygon",
}

FEATURE_COLUMNS = [
    "disaster_type",
    "alert_level_ordinal",
    "severity",
    "distance_to_center_km",
    "distance_to_boundary_km",
    "road_length_m",
    "road_type",
]
CATEGORICAL_FEATURES = ["disaster_type", "road_type"]
NUMERIC_FEATURES = [
    feature for feature in FEATURE_COLUMNS if feature not in CATEGORICAL_FEATURES
]

DEFAULT_DATA_PATH = Path(__file__).with_name("training_data.csv")
DEFAULT_MODEL_PATH = Path(__file__).with_name("model.joblib")
DEFAULT_INFO_PATH = Path(__file__).with_name("model_info.json")


def load_training_data(data_path: str | Path = DEFAULT_DATA_PATH) -> pd.DataFrame:
    """Load and validate the Phase 1 CSV without changing its labels."""
    data_path = Path(data_path)
    data = pd.read_csv(data_path, dtype={GROUP_COLUMN: str})

    required_columns = {GROUP_COLUMN, TARGET_COLUMN, *FEATURE_COLUMNS}
    missing_columns = required_columns.difference(data.columns)
    if missing_columns:
        raise ValueError(f"Training CSV is missing columns: {sorted(missing_columns)}")

    required_values = [GROUP_COLUMN, TARGET_COLUMN, *FEATURE_COLUMNS]
    missing_values = data[required_values].isna().sum()
    if missing_values[TARGET_COLUMN] or missing_values[GROUP_COLUMN]:
        raise ValueError("Training CSV has a missing target or event_id.")

    target = pd.to_numeric(data[TARGET_COLUMN], errors="raise")
    if not np.isfinite(target).all() or not target.between(0, 1).all():
        raise ValueError("road_impact_score must contain finite values in [0, 1].")
    if data[GROUP_COLUMN].nunique() < 2:
        raise ValueError("At least two unique disaster events are required for GroupKFold.")

    return data


def build_preprocessor() -> ColumnTransformer:
    """Create the shared preprocessing used by every candidate model."""
    numeric_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )
    categorical_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("one_hot", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
        ]
    )
    return ColumnTransformer(
        transformers=[
            ("numeric", numeric_pipeline, NUMERIC_FEATURES),
            ("categorical", categorical_pipeline, CATEGORICAL_FEATURES),
        ],
        remainder="drop",
    )


def build_candidate_models() -> dict[str, Any]:
    """Return the Phase 2 candidates plus a mean-prediction baseline."""
    return {
        "Dummy (Mean Baseline)": DummyRegressor(strategy="mean"),
        "Linear Regression": LinearRegression(),
        "Random Forest Regressor": RandomForestRegressor(
            n_estimators=100,
            max_depth=8,
            min_samples_leaf=2,
            random_state=42,
            n_jobs=-1,
        ),
        "Gradient Boosting Regressor": GradientBoostingRegressor(
            n_estimators=100,
            learning_rate=0.05,
            max_depth=2,
            min_samples_leaf=2,
            random_state=42,
        ),
    }


def build_pipeline(estimator: Any) -> Pipeline:
    return Pipeline(
        steps=[("preprocessor", build_preprocessor()), ("model", estimator)]
    )


def build_group_splits(groups: pd.Series, max_splits: int = 5) -> tuple[int, list[tuple[np.ndarray, np.ndarray]]]:
    """Build event-disjoint folds, reducing K only when the dataset requires it."""
    unique_event_count = groups.nunique()
    if unique_event_count < 2:
        raise ValueError("GroupKFold needs at least two unique event IDs.")

    # The plan specifies K=5.  The current Phase 1 dataset has four events, so
    # K=4 is the only valid event-held-out evaluation without inventing data.
    n_splits = min(max_splits, unique_event_count)
    splitter = GroupKFold(n_splits=n_splits)
    indices = np.arange(len(groups))
    splits = list(splitter.split(indices, groups=groups))

    for train_indices, validation_indices in splits:
        train_events = set(groups.iloc[train_indices])
        validation_events = set(groups.iloc[validation_indices])
        if train_events.intersection(validation_events):
            raise RuntimeError("GroupKFold produced event leakage.")

    return n_splits, splits


def dataset_statistics(data: pd.DataFrame) -> dict[str, Any]:
    """Summarize the actual CSV for model metadata and reproducibility."""
    target = data[TARGET_COLUMN].astype(float)
    missing = {column: int(count) for column, count in data.isna().sum().items()}
    unique_counts = {column: int(data[column].nunique(dropna=False)) for column in data.columns}
    constant = [column for column, count in unique_counts.items() if count <= 1]
    near_constant = [
        column
        for column in FEATURE_COLUMNS
        if data[column].value_counts(dropna=False, normalize=True).iloc[0] >= 0.99
    ]

    return {
        "row_count": int(len(data)),
        "unique_event_count": int(data[GROUP_COLUMN].nunique()),
        "disaster_type_distribution": {
            str(name): int(count)
            for name, count in data["disaster_type"].value_counts().items()
        },
        "samples_per_event": {
            str(event_id): int(count)
            for event_id, count in data[GROUP_COLUMN].value_counts().sort_index().items()
        },
        "target_distribution": {
            "min": float(target.min()),
            "max": float(target.max()),
            "mean": float(target.mean()),
            "std": float(target.std(ddof=0)),
            "zero_count": int((target == 0).sum()),
            "one_count": int((target == 1).sum()),
            "quantiles": {
                "p25": float(target.quantile(0.25)),
                "p50": float(target.quantile(0.50)),
                "p75": float(target.quantile(0.75)),
            },
        },
        "missing_values": missing,
        "unique_value_counts": unique_counts,
        "constant_columns": constant,
        "near_constant_features": near_constant,
        # build_dataset.py records -1 only for point-only proxy-label events.
        "proxy_label_row_count": int((data["distance_to_boundary_km"] == -1).sum()),
    }


def train_and_select(
    data_path: str | Path = DEFAULT_DATA_PATH,
    model_path: str | Path = DEFAULT_MODEL_PATH,
    info_path: str | Path = DEFAULT_INFO_PATH,
) -> dict[str, Any]:
    """Evaluate all candidates, then fit and save the lowest-RMSE model."""
    data = load_training_data(data_path)
    features = data[FEATURE_COLUMNS].copy()
    target = data[TARGET_COLUMN].astype(float)
    groups = data[GROUP_COLUMN]
    n_splits, splits = build_group_splits(groups)

    metrics: dict[str, dict[str, float | list[float]]] = {}
    candidates = build_candidate_models()
    for model_name, estimator in candidates.items():
        fold_rmse: list[float] = []
        for train_indices, validation_indices in splits:
            pipeline = build_pipeline(clone(estimator))
            pipeline.fit(features.iloc[train_indices], target.iloc[train_indices])
            predictions = pipeline.predict(features.iloc[validation_indices])
            fold_rmse.append(
                float(np.sqrt(mean_squared_error(target.iloc[validation_indices], predictions)))
            )
        metrics[model_name] = {
            "fold_rmse": fold_rmse,
            "mean_rmse": float(np.mean(fold_rmse)),
            "std_rmse": float(np.std(fold_rmse)),
        }

    selected_model = min(metrics, key=lambda name: float(metrics[name]["mean_rmse"]))
    final_pipeline = build_pipeline(clone(candidates[selected_model]))
    final_pipeline.fit(features, target)

    model_path = Path(model_path)
    info_path = Path(info_path)
    model_path.parent.mkdir(parents=True, exist_ok=True)
    info_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(final_pipeline, model_path)

    info: dict[str, Any] = {
        "selected_model": selected_model,
        "primary_metric": "RMSE",
        "metrics": metrics,
        "feature_information": {
            "raw_feature_columns": FEATURE_COLUMNS,
            "numeric_features": NUMERIC_FEATURES,
            "categorical_features": CATEGORICAL_FEATURES,
            "transformed_feature_columns": final_pipeline.named_steps[
                "preprocessor"
            ].get_feature_names_out().tolist(),
            "excluded_columns": sorted(LEAKAGE_COLUMNS | {GROUP_COLUMN}),
            "target_column": TARGET_COLUMN,
            "leakage_check_passed": not set(FEATURE_COLUMNS).intersection(LEAKAGE_COLUMNS),
        },
        "training_metadata": {
            "trained_at_utc": datetime.now(timezone.utc).isoformat(),
            "data_file": str(Path(data_path).name),
            "grouping_column": GROUP_COLUMN,
            "cross_validation": "GroupKFold",
            "requested_splits": 5,
            "actual_splits": n_splits,
            "random_state": 42,
            "target_definition": (
                "road length inside the GDACS affected polygon divided by total road "
                "length; point-only events use the documented weak proxy label"
            ),
            "dataset_statistics": dataset_statistics(data),
        },
    }
    with info_path.open("w", encoding="utf-8") as file:
        json.dump(info, file, indent=2, allow_nan=False)

    return info


def main() -> None:
    parser = argparse.ArgumentParser(description="Train Phase 2 road-impact models.")
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA_PATH)
    parser.add_argument("--model-out", type=Path, default=DEFAULT_MODEL_PATH)
    parser.add_argument("--info-out", type=Path, default=DEFAULT_INFO_PATH)
    args = parser.parse_args()

    info = train_and_select(args.data, args.model_out, args.info_out)
    print(json.dumps(info, indent=2))


if __name__ == "__main__":
    main()
