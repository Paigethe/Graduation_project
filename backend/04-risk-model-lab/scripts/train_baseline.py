#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
)
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from sklearn.preprocessing import StandardScaler


LABEL_ORDER = ["low", "medium", "high"]
LABEL_TO_ID = {"low": 0, "medium": 1, "high": 2}


def model_factory(name: str, seed: int):
    name = name.lower().strip()
    if name == "logreg":
        return LogisticRegression(
            max_iter=2000,
            class_weight="balanced",
            random_state=seed,
        )
    if name == "rf":
        return RandomForestClassifier(
            n_estimators=500,
            random_state=seed,
            n_jobs=-1,
            class_weight="balanced_subsample",
            min_samples_leaf=2,
        )
    if name == "mlp":
        return MLPClassifier(
            hidden_layer_sizes=(128, 64),
            max_iter=300,
            random_state=seed,
            early_stopping=True,
            n_iter_no_change=15,
        )
    raise ValueError(f"Unsupported model: {name}")


def load_split(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Missing file: {path}")
    df = pd.read_csv(path)
    if "y_risk" not in df.columns:
        raise ValueError(f"Missing y_risk column in {path}")
    return df


def build_feature_lists(df: pd.DataFrame) -> tuple[list[str], list[str]]:
    block = {"source_dataset", "source_row_id", "y_risk", "y_risk_id"}
    categorical = []
    if "gender" in df.columns:
        categorical.append("gender")
    numeric = [c for c in df.columns if c not in block.union(categorical)]
    return numeric, categorical


def make_preprocessor(
    numeric_features: list[str], categorical_features: list[str], scale_numeric: bool
) -> ColumnTransformer:
    transformers = []
    if numeric_features:
        num_steps = [("imputer", SimpleImputer(strategy="median"))]
        if scale_numeric:
            num_steps.append(("scaler", StandardScaler()))
        transformers.append(
            (
                "num",
                Pipeline(steps=num_steps),
                numeric_features,
            )
        )
    if categorical_features:
        transformers.append(
            (
                "cat",
                Pipeline(
                    steps=[
                        ("imputer", SimpleImputer(strategy="most_frequent")),
                        ("ohe", OneHotEncoder(handle_unknown="ignore")),
                    ]
                ),
                categorical_features,
            )
        )
    return ColumnTransformer(transformers=transformers, remainder="drop")


def evaluate(model: Pipeline, x: pd.DataFrame, y: pd.Series) -> dict:
    pred = model.predict(x)
    cm = confusion_matrix(y, pred, labels=LABEL_ORDER)
    report = classification_report(y, pred, labels=LABEL_ORDER, output_dict=True, zero_division=0)
    return {
        "accuracy": float(accuracy_score(y, pred)),
        "balanced_accuracy": float(balanced_accuracy_score(y, pred)),
        "macro_f1": float(f1_score(y, pred, average="macro")),
        "weighted_f1": float(f1_score(y, pred, average="weighted")),
        "confusion_matrix": cm.tolist(),
        "labels": LABEL_ORDER,
        "classification_report": report,
    }


def write_confusion_csv(confusion: list[list[int]], labels: list[str], out_path: Path):
    rows = []
    for i, actual in enumerate(labels):
        for j, predicted in enumerate(labels):
            rows.append(
                {
                    "actual": actual,
                    "predicted": predicted,
                    "count": int(confusion[i][j]),
                }
            )
    pd.DataFrame(rows).to_csv(out_path, index=False)


def main():
    parser = argparse.ArgumentParser(description="Train baseline risk classifier from prepared train/val/test splits.")
    parser.add_argument("--data-dir", default="outputs", help="Directory containing train.csv / val.csv / test.csv")
    parser.add_argument("--run-dir", default="outputs/training_runs", help="Directory to store model artifacts and metrics")
    parser.add_argument("--model", default="rf", choices=["rf", "logreg", "mlp"], help="Model type")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    data_dir = Path(args.data_dir).resolve()
    run_base = Path(args.run_dir).resolve()
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    run_dir = run_base / f"{args.model}_{ts}"
    run_dir.mkdir(parents=True, exist_ok=True)

    train_df = load_split(data_dir / "train.csv")
    val_df = load_split(data_dir / "val.csv")
    test_df = load_split(data_dir / "test.csv")

    num_cols, cat_cols = build_feature_lists(train_df)
    feature_cols = num_cols + cat_cols
    x_train = train_df[feature_cols]
    y_train = train_df["y_risk"].astype(str)
    x_val = val_df[feature_cols]
    y_val = val_df["y_risk"].astype(str)
    x_test = test_df[feature_cols]
    y_test = test_df["y_risk"].astype(str)

    scale_numeric = args.model in {"logreg", "mlp"}
    preprocessor = make_preprocessor(num_cols, cat_cols, scale_numeric=scale_numeric)
    estimator = model_factory(args.model, args.seed)
    pipeline = Pipeline(
        steps=[
            ("preprocess", preprocessor),
            ("model", estimator),
        ]
    )

    print(f"[train] model={args.model}, train_rows={len(x_train)}, features={len(feature_cols)}")
    pipeline.fit(x_train, y_train)

    val_metrics = evaluate(pipeline, x_val, y_val)
    test_metrics = evaluate(pipeline, x_test, y_test)

    model_path = run_dir / "model.joblib"
    metrics_path = run_dir / "metrics.json"
    meta_path = run_dir / "model_meta.json"
    pred_path = run_dir / "test_predictions.csv"
    val_cm_path = run_dir / "confusion_val.csv"
    test_cm_path = run_dir / "confusion_test.csv"

    joblib.dump(pipeline, model_path)
    write_confusion_csv(val_metrics["confusion_matrix"], LABEL_ORDER, val_cm_path)
    write_confusion_csv(test_metrics["confusion_matrix"], LABEL_ORDER, test_cm_path)

    test_pred = pipeline.predict(x_test)
    pd.DataFrame(
        {
            "y_true": y_test.values,
            "y_pred": test_pred,
        }
    ).to_csv(pred_path, index=False)

    metrics_payload = {
        "model": args.model,
        "seed": args.seed,
        "train_rows": int(len(train_df)),
        "val_rows": int(len(val_df)),
        "test_rows": int(len(test_df)),
        "features": feature_cols,
        "numeric_features": num_cols,
        "categorical_features": cat_cols,
        "scale_numeric": scale_numeric,
        "val": val_metrics,
        "test": test_metrics,
    }
    metrics_path.write_text(json.dumps(metrics_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    meta_payload = {
        "model_name": f"{args.model}_baseline",
        "model_version": f"{args.model}_baseline_{ts}",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "label_order": LABEL_ORDER,
        "label_to_id": LABEL_TO_ID,
        "features": feature_cols,
        "notes": [
            "Baseline classifier trained from public Kaggle merged dataset.",
            "Use for engineering validation, not as final longitudinal evidence.",
        ],
        "artifacts": {
            "model": str(model_path),
            "metrics": str(metrics_path),
            "test_predictions": str(pred_path),
            "confusion_val": str(val_cm_path),
            "confusion_test": str(test_cm_path),
        },
    }
    meta_path.write_text(json.dumps(meta_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n=== Training Complete ===")
    print(f"run_dir        : {run_dir}")
    print(f"val_accuracy   : {val_metrics['accuracy']:.4f}")
    print(f"val_macro_f1   : {val_metrics['macro_f1']:.4f}")
    print(f"test_accuracy  : {test_metrics['accuracy']:.4f}")
    print(f"test_macro_f1  : {test_metrics['macro_f1']:.4f}")
    print(f"metrics_json   : {metrics_path}")
    print(f"model_meta_json: {meta_path}")


if __name__ == "__main__":
    main()
