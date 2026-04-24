from __future__ import annotations

from datetime import timedelta
from typing import Any

from django.contrib.auth import get_user_model
from django.conf import settings
from django.db.models import OuterRef, Subquery
from django.db import transaction
from django.utils import timezone

from apps.surveys.models import QuestionnaireResponse

from .models import AssessmentResult, RiskAlert
from .predictor import predict_risk

User = get_user_model()
LONG_UNLOGIN_ALERT_PREFIX = "长期未登录预警"


def _to_float(value: Any) -> float:
    try:
        return float(value)
    except Exception:
        return 0.0


def _to_float_default(value: Any, default: float) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _extract_student_profile(answers: dict[str, Any]) -> dict[str, Any] | None:
    canonical_map = {
        "age": "age",
        "gender": "gender",
        "cgpa": "cgpa",
        "family_history_mental_illness": "family_history_mental_illness",
        "suicidal_ideation": "suicidal_ideation",
        "familyHistoryMentalIllness": "family_history_mental_illness",
        "suicidalIdeation": "suicidal_ideation",
    }
    profile: dict[str, Any] = {}
    for raw_key, canonical in canonical_map.items():
        if raw_key in answers and canonical not in profile:
            profile[canonical] = answers.get(raw_key)
    return profile or None


def compute_assessment(response_obj: QuestionnaireResponse) -> dict[str, Any]:
    questions = response_obj.questionnaire.template.questions or []
    answers = response_obj.answers or {}

    total = 0.0
    total_weight = 0.0
    dim_total: dict[str, float] = {}
    dim_weight: dict[str, float] = {}

    for q in questions:
        qid = str(q.get("id", ""))
        if not qid:
            continue
        weight = _to_float(q.get("weight", 1.0)) or 1.0
        dimension = str(q.get("dimension") or "overall")

        # answers may use str/int keys
        raw_value = answers.get(qid, answers.get(int(qid) if qid.isdigit() else qid, 0))
        value = _to_float(raw_value)
        q_min = _to_float_default(q.get("min", 1.0), 1.0)
        q_max = _to_float_default(q.get("max", 5.0), 5.0)
        if q_max < q_min:
            q_min, q_max = q_max, q_min
        value = min(max(value, q_min), q_max)

        total += value * weight
        total_weight += weight

        dim_total[dimension] = dim_total.get(dimension, 0.0) + value * weight
        dim_weight[dimension] = dim_weight.get(dimension, 0.0) + weight

    avg = total / total_weight if total_weight > 0 else 0.0
    dim_scores = {
        dim: (dim_total[dim] / dim_weight[dim] if dim_weight[dim] > 0 else 0.0)
        for dim in dim_total
    }

    # Risk thresholds (demo, tunable)
    risk = AssessmentResult.RiskLevel.LOW
    if avg >= 3.5 or any(v >= 4.0 for v in dim_scores.values()):
        risk = AssessmentResult.RiskLevel.HIGH
    elif avg >= 2.5 or any(v >= 3.0 for v in dim_scores.values()):
        risk = AssessmentResult.RiskLevel.MEDIUM

    # Placeholder model prediction (replace with real model later)
    student_profile = _extract_student_profile(answers if isinstance(answers, dict) else {})
    model_result = predict_risk(avg, dim_scores, student_profile=student_profile)
    predicted = model_result.predicted_risk_level

    return {
        "total_score": total,
        "avg_score": avg,
        "dimension_scores": dim_scores,
        "risk_level": risk,
        "predicted_risk_level": predicted,
        "model_meta": {
            "model_version": model_result.model_version,
            "confidence": model_result.confidence,
        },
    }


@transaction.atomic
def create_assessment_for_response(response_obj: QuestionnaireResponse) -> AssessmentResult:
    payload = compute_assessment(response_obj)
    assessment = AssessmentResult.objects.create(response=response_obj, **payload)

    if assessment.risk_level in {AssessmentResult.RiskLevel.MEDIUM, AssessmentResult.RiskLevel.HIGH}:
        message = "系统检测到需要关注的心理风险，请咨询教师及时跟进。"
        RiskAlert.objects.create(
            student=response_obj.student,
            assessment=assessment,
            level=assessment.risk_level,
            message=message,
        )
    return assessment


def ensure_dormant_high_risk_alerts() -> int:
    threshold_days = int(getattr(settings, "DORMANT_RISK_DAYS", 14) or 14)
    threshold = timezone.now() - timedelta(days=max(threshold_days, 1))

    latest_qs = AssessmentResult.objects.filter(
        response__student_id=OuterRef("pk")
    ).order_by("-id")
    latest_assessment_id = Subquery(latest_qs.values("id")[:1])
    latest_risk = Subquery(latest_qs.values("risk_level")[:1])
    latest_pred = Subquery(latest_qs.values("predicted_risk_level")[:1])

    students = (
        User.objects.filter(role=User.Role.STUDENT)
        .annotate(_latest_assessment_id=latest_assessment_id, _latest_risk=latest_risk, _latest_pred=latest_pred)
        .exclude(_latest_assessment_id__isnull=True)
    )

    created = 0
    for student in students:
        latest_risk_level = str(getattr(student, "_latest_risk", "") or "")
        latest_pred_level = str(getattr(student, "_latest_pred", "") or "")
        if latest_risk_level != AssessmentResult.RiskLevel.HIGH and latest_pred_level != AssessmentResult.RiskLevel.HIGH:
            continue

        last_login = getattr(student, "last_login", None)
        if last_login and last_login >= threshold:
            continue

        if RiskAlert.objects.filter(
            student=student,
            is_acknowledged=False,
            message__startswith=LONG_UNLOGIN_ALERT_PREFIX,
        ).exists():
            continue

        days = threshold_days
        if last_login:
            try:
                days = max((timezone.now() - last_login).days, 0)
            except Exception:
                days = threshold_days
        login_part = "从未登录" if last_login is None else f"已连续 {days} 天未登录"
        RiskAlert.objects.create(
            student=student,
            assessment_id=getattr(student, "_latest_assessment_id", None),
            level=AssessmentResult.RiskLevel.HIGH,
            message=f"{LONG_UNLOGIN_ALERT_PREFIX}：高风险学生 {login_part}，请咨询教师尽快跟进。",
        )
        created += 1

    return created
