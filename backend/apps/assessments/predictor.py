from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import json
import logging
from pathlib import Path
from typing import Any

from django.conf import settings

from .models import AssessmentResult

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ModelResult:
    predicted_risk_level: str
    model_version: str
    confidence: float


def predict_with_placeholder(avg_score: float, dim_scores: dict[str, float]) -> ModelResult:
    # Placeholder: mirror rule-based risk.
    risk = AssessmentResult.RiskLevel.LOW
    if avg_score >= 3.5 or any(v >= 4.0 for v in dim_scores.values()):
        risk = AssessmentResult.RiskLevel.HIGH
    elif avg_score >= 2.5 or any(v >= 3.0 for v in dim_scores.values()):
        risk = AssessmentResult.RiskLevel.MEDIUM
    return ModelResult(predicted_risk_level=risk, model_version="placeholder_v1", confidence=0.5)


DEFAULT_FEATURES = [
    "age",
    "cgpa",
    "academic_pressure",
    "work_pressure",
    "study_satisfaction",
    "sleep_quality",
    "dietary_habits",
    "anxiety_signal",
    "depression_signal",
    "panic_signal",
    "social_support",
    "peer_pressure",
    "financial_stress",
    "family_history_mental_illness",
    "suicidal_ideation",
    "gender",
]


DIMENSION_ALIASES = {
    "anxiety": ["anxiety", "phobic", "paranoid", "hostility"],
    "depression": ["depression", "additional", "psychoticism"],
    "sleep": ["sleep"],
    "social": ["social", "interpersonal"],
    "somatic": ["somatic", "somatization"],
    "academic_pressure": ["academic_pressure", "study", "study_load"],
    "work_pressure": ["work_pressure", "work"],
    "financial_stress": ["financial_stress", "finance", "economic"],
}


def _to_float_or_none(value: Any) -> float | None:
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    try:
        return float(s)
    except Exception:
        return None


def _to_binary_flag(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    s = str(value).strip().lower()
    if s in {"1", "true", "yes", "y"}:
        return 1.0
    if s in {"0", "false", "no", "n"}:
        return 0.0
    f = _to_float_or_none(value)
    if f is None:
        return None
    return 1.0 if f >= 0.5 else 0.0


def _clamp(value: float | None, lo: float, hi: float) -> float | None:
    if value is None:
        return None
    return max(lo, min(hi, float(value)))


def _normalize_gender(value: Any) -> str:
    if value is None:
        return "unknown"
    s = str(value).strip().lower()
    if s in {"male", "m", "man"}:
        return "male"
    if s in {"female", "f", "woman"}:
        return "female"
    if s in {"unknown", ""}:
        return "unknown"
    return "other"


def _invert_symptom_score(value: float | None, low: float = 1.0, high: float = 5.0) -> float | None:
    if value is None:
        return None
    v = _clamp(value, low, high)
    if v is None:
        return None
    return low + high - v


def _mean_available(values: list[float | None]) -> float | None:
    existing = [float(v) for v in values if v is not None]
    if not existing:
        return None
    return sum(existing) / len(existing)


def _read_dim(dim_scores: dict[str, Any], alias_key: str) -> float | None:
    aliases = DIMENSION_ALIASES.get(alias_key, [alias_key])
    values: list[float | None] = []
    for key in aliases:
        values.append(_to_float_or_none(dim_scores.get(key)))
    return _mean_available(values)


def build_payload_from_assessment_scores(
    *,
    avg_score: float,
    dim_scores: dict[str, Any],
    student_profile: dict[str, Any] | None = None,
) -> dict[str, Any]:
    profile = student_profile or {}
    avg = _clamp(_to_float_or_none(avg_score), 1.0, 5.0)
    anxiety = _clamp(_read_dim(dim_scores, "anxiety"), 1.0, 5.0)
    depression = _clamp(_read_dim(dim_scores, "depression"), 1.0, 5.0)
    sleep_symptom = _clamp(_read_dim(dim_scores, "sleep"), 1.0, 5.0)
    social_symptom = _clamp(_read_dim(dim_scores, "social"), 1.0, 5.0)
    somatic = _clamp(_read_dim(dim_scores, "somatic"), 1.0, 5.0)
    academic_pressure = _clamp(_read_dim(dim_scores, "academic_pressure"), 1.0, 5.0)
    work_pressure = _clamp(_read_dim(dim_scores, "work_pressure"), 1.0, 5.0)
    financial_stress = _clamp(_read_dim(dim_scores, "financial_stress"), 1.0, 5.0)

    # Fallback when questionnaire does not expose these dimensions.
    if academic_pressure is None:
        academic_pressure = avg
    if work_pressure is None:
        work_pressure = avg if avg is not None and avg >= 3.0 else None
    if financial_stress is None:
        financial_stress = avg

    return {
        "age": _to_float_or_none(profile.get("age")),
        "gender": _normalize_gender(profile.get("gender")),
        "cgpa": _to_float_or_none(profile.get("cgpa")),
        "academic_pressure": academic_pressure,
        "work_pressure": work_pressure,
        "study_satisfaction": _invert_symptom_score(avg),
        "sleep_quality": _invert_symptom_score(sleep_symptom),
        "dietary_habits": _invert_symptom_score(somatic) if somatic is not None else None,
        "anxiety_signal": 1.0 if anxiety is not None and anxiety >= 3.0 else (0.0 if anxiety is not None else None),
        "depression_signal": (
            1.0 if depression is not None and depression >= 3.0 else (0.0 if depression is not None else None)
        ),
        "panic_signal": (
            1.0
            if anxiety is not None and depression is not None and anxiety >= 4.0 and depression >= 4.0
            else (0.0 if anxiety is not None or depression is not None else None)
        ),
        "social_support": _invert_symptom_score(social_symptom),
        "peer_pressure": social_symptom,
        "financial_stress": financial_stress,
        "family_history_mental_illness": _to_binary_flag(profile.get("family_history_mental_illness")),
        "suicidal_ideation": _to_binary_flag(profile.get("suicidal_ideation")),
    }


@lru_cache(maxsize=1)
def _load_model_bundle() -> dict[str, Any] | None:
    if not getattr(settings, "RISK_MODEL_ENABLED", False):
        return None

    model_path = Path(str(getattr(settings, "RISK_MODEL_PATH", ""))).resolve()
    if not model_path.exists():
        logger.warning("Risk model file not found: %s", model_path)
        return None

    try:
        import joblib
        import pandas as pd
    except Exception as exc:
        logger.warning("Risk model runtime dependencies unavailable: %s", exc)
        return None

    meta_path = Path(str(getattr(settings, "RISK_MODEL_META_PATH", ""))).resolve()
    meta: dict[str, Any] = {}
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.warning("Failed to read risk model meta (%s): %s", meta_path, exc)

    try:
        model = joblib.load(model_path)
    except Exception as exc:
        logger.warning("Failed to load risk model (%s): %s", model_path, exc)
        return None

    features = meta.get("features")
    feature_columns = [str(x) for x in features] if isinstance(features, list) and features else list(DEFAULT_FEATURES)
    model_version = str(meta.get("model_version") or getattr(settings, "RISK_MODEL_VERSION", "risk_model_bridge_v1"))

    return {
        "model": model,
        "pd": pd,
        "feature_columns": feature_columns,
        "model_version": model_version,
    }


def _predict_with_loaded_model(
    bundle: dict[str, Any],
    *,
    avg_score: float,
    dim_scores: dict[str, float],
    student_profile: dict[str, Any] | None = None,
) -> ModelResult:
    pd = bundle["pd"]
    model = bundle["model"]
    feature_columns: list[str] = bundle["feature_columns"]
    model_version = str(bundle["model_version"])

    payload = build_payload_from_assessment_scores(
        avg_score=avg_score,
        dim_scores=dim_scores,
        student_profile=student_profile,
    )
    row = {k: payload.get(k) for k in feature_columns}
    x = pd.DataFrame([row], columns=feature_columns)

    label = str(model.predict(x)[0])
    confidence = 0.5
    if hasattr(model, "predict_proba"):
        try:
            proba = model.predict_proba(x)[0]
            classes = list(getattr(model, "classes_", []))
            if classes and len(classes) == len(proba):
                prob_by_label = {str(c): float(p) for c, p in zip(classes, proba)}
                confidence = float(prob_by_label.get(label, max(prob_by_label.values())))
            else:
                confidence = float(max(proba))
        except Exception:
            confidence = 0.5

    if label not in {
        AssessmentResult.RiskLevel.LOW,
        AssessmentResult.RiskLevel.MEDIUM,
        AssessmentResult.RiskLevel.HIGH,
    }:
        label = AssessmentResult.RiskLevel.MEDIUM
    return ModelResult(predicted_risk_level=label, model_version=model_version, confidence=confidence)


def reset_predictor_cache():
    _load_model_bundle.cache_clear()


def predict_risk(
    avg_score: float,
    dim_scores: dict[str, float],
    *,
    student_profile: dict[str, Any] | None = None,
) -> ModelResult:
    bundle = _load_model_bundle()
    if bundle is None:
        return predict_with_placeholder(avg_score, dim_scores)
    try:
        return _predict_with_loaded_model(
            bundle,
            avg_score=avg_score,
            dim_scores=dim_scores,
            student_profile=student_profile,
        )
    except Exception as exc:
        logger.warning("Risk model inference failed, fallback to placeholder: %s", exc)
        return predict_with_placeholder(avg_score, dim_scores)
