from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import json
import logging
from pathlib import Path
from typing import Any

from django.conf import settings

from .models import AssessmentResult
#就是在真实运行的网站中，读取那个训练好的模型，并根据学生刚做完的心理测评问卷算出一个风险等级
logger = logging.getLogger(__name__)
# 这个文件定义了    评估结果的风险预测逻辑。它包含了一个ModelResult数据类，用于表示模型的预测结果，包括预测的   风险等级、模型版本和置信度。
# 主要函数是predict_risk，它接受平均分、各维度分数和学生个人资料作为输入，尝试加载预训练的风险预测模型进行推断。
# 如果模型不可用或推断失败，则会使用一个简单的占位符函数predict_with_placeholder来根据规则进行风险预测。
# 文件还包含了一些辅助函数，用于处理输入数据、构建模型输入特征，以及管理模型加载和缓存。
# 这些功能共同支持了评估结果的风险预测过程，使得系统能够根据学生的评估数据提供风险等级的预测。

@dataclass(frozen=True)
class ModelResult:
    predicted_risk_level: str
    model_version: str
    confidence: float

# 这个函数是一个占位符的风险预测函数，根据平均分和各维度分数的简单规则来预测风险等级。
# 它会根据平均分和维度分数的阈值来判断风险等级是低风险、中风险还是高风险。
# 这种简单的规则可以作为模型不可用时的备用方案，确保系统仍然能够提供基本的风险预测功能。

# 这就是上面提到的“笨”方法。如果 AI 模型不可用，它会根据测评的平均分或各个维度的最高分来死板地判断：
# 平均分 >= 3.5 或 任意维度得分 >= 4.0 ➔ 高风险 (HIGH)
# 平均分 >= 2.5 或 任意维度得分 >= 3.0 ➔ 中风险 (MEDIUM)
# 其他 ➔ 低风险 (LOW)
def predict_with_placeholder(avg_score: float, dim_scores: dict[str, float]) -> ModelResult:
    risk = AssessmentResult.RiskLevel.LOW
    if avg_score >= 3.5 or any(v >= 4.0 for v in dim_scores.values()):
        risk = AssessmentResult.RiskLevel.HIGH
    elif avg_score >= 2.5 or any(v >= 3.0 for v in dim_scores.values()):
        risk = AssessmentResult.RiskLevel.MEDIUM
    return ModelResult(predicted_risk_level=risk, model_version="placeholder_v1", confidence=0.5)

#DEFAULT_FEATURES 定义了模型输入特征的默认列表，包括年龄、绩点、学业压力、工作压力、学习满意度、睡眠质量、饮食习惯、焦虑信号、抑郁信号、恐慌信号、社交支持、同伴压力、经济压力、家庭精神疾病史和自杀意念等。
# 这些特征是模型进行风险预测时所需要的输入数据字段。
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

# 维度别名映射，用于从评估结果的维度分数中提取特定维度的分数。
# 每个维度可能对应多个别名，这些别名会被尝试读取并计算平均值作为该维度的最终分数。例如，"anxiety"维度可能对应"anxiety"、"phobic"、"paranoid"和"hostility"等别名，这些别名的分数会被平均后作为"anxiety"维度的分数输入到模型中。这种设计允许模型适应不同问卷或评估工具中可能使用的不同术语来表示相同的心理健康维度。
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

# 下面是一些辅助函数，用于处理输入数据、构建模型输入特征，以及管理模型加载和缓存。这些函数包括：
# - _to_float_or_none: 将输入值转换为浮点数，如果输入无效则返回None。
# - _to_binary_flag: 将输入值转换为二元标志（0.0或1.0），适用于布尔类型的输入。
# - _clamp: 将输入值限制在指定的范围内。
# - _normalize_gender: 将输入的性别值标准化为"male"、"female"、"unknown"或"other"。     
# - _invert_symptom_score: 将症状分数进行反转，适用于某些维度的分数需要反向处理的情况。
# - _mean_available: 计算一组值的平均值，忽略其中的None值。
# - _read_dim: 从维度分数字典中读取指定维度的分数，考虑到可能存在多个别名，并计算这些别名分数的平均值。
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

# build_payload_from_assessment_scores函数用于从评估结果的平均分、各维度分数和学生个人资料中构建模型输入特征的字典。
# 它会根据预定义的维度别名映射来提取和处理相关维度的分数，并将这些分数转换为适合模型输入的格式。            数据“翻译”与清洗
# 例如，它会将某些维度的分数进行反转处理，或者将布尔类型的个人资料字段转换为二元标志。最终返回一个包含所有模型输入特征的字典，用于后续的风险预测。
# 因为学生做完问卷后，数据库里存的是“SCL-90”、“抑郁量表”等各种五花八门的维度得分，以及学生的个人信息（年龄、性别、绩点）。但是，机器学习模型只认固定格式的“特征（Features）”。
# 维度映射 (DIMENSION_ALIASES)：它把不同问卷里叫法不同的维度统一起来。比如问卷里可能叫 phobic（恐惧）或 hostility（敌对），它都会统统折算到 anxiety（焦虑）这个大类里。
# 分值反转与归一化 (_invert_symptom_score, _normalize_gender 等)：将一些反向计分的题目或者文本格式的性别（M/F/Male/Female）统一转换成模型能看懂的标准化数字。
# 最终，它会拼装出一个包含 16 个核心特征（如 age, cgpa, sleep_quality, anxiety_signal 等）的标准字典 payload。
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
# 模型加载与缓存
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

# 这是供其他模块（比如问卷提交接口）调用的最终函数。它的工作流程非常严谨：
# 它首先尝试去加载真正的机器学习模型。
# 如果模型加载成功，就把学生数据喂给模型，算出预测结果（_predict_with_loaded_model）。
# 兜底机制（Fallback）：如果系统配置没有开启 ML 模型，或者模型文件丢失、出错了，它不会让系统崩溃，而是立刻切换到 predict_with_placeholder（一个基于固定规则的“笨”方法）来给出结果。
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
