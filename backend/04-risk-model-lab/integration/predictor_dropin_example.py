"""
Drop-in example for replacing placeholder predictor in:
02-系统实现代码/backend/apps/assessments/predictor.py

This file is intentionally outside the main project for safe iteration.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from django.conf import settings

# If copied into main project, adjust import path to where adapter is placed.
from .django_predictor_adapter import RiskPredictorAdapter


@dataclass(frozen=True)
class ModelResult:
    predicted_risk_level: str
    model_version: str
    confidence: float


@lru_cache(maxsize=1)
def _adapter() -> RiskPredictorAdapter:
    model_path = Path(getattr(settings, "RISK_MODEL_PATH", "storage/models/risk/model.joblib")).resolve()
    meta_path = Path(
        getattr(settings, "RISK_MODEL_META_PATH", "storage/models/risk/model_meta.json")
    ).resolve()
    return RiskPredictorAdapter(model_path=model_path, meta_path=meta_path)


def _extract_confidence(probabilities: dict[str, float], label: str) -> float:
    if not probabilities:
        return 0.0
    if label in probabilities:
        return float(probabilities[label])
    return max(float(v) for v in probabilities.values())


def predict_risk(
    avg_score: float,
    dim_scores: dict[str, float],
    *,
    student_profile: dict[str, Any] | None = None,
) -> ModelResult:
    """
    Bridge current assessment inputs to exported baseline model.
    """
    result = _adapter().predict_from_assessment_scores(
        avg_score=avg_score,
        dim_scores=dim_scores,
        student_profile=student_profile,
    )
    label = str(result.get("label", "low"))
    probabilities = result.get("probabilities", {}) or {}
    confidence = _extract_confidence(probabilities, label)
    return ModelResult(
        predicted_risk_level=label,
        model_version="baseline_bridge_v1",
        confidence=confidence,
    )
