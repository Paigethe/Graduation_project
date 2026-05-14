from django.conf import settings
from django.db import models

#本文件定义了两个模型：AssessmentResult和RiskAlert。
# AssessmentResult模型用于存储评估结果，包括总分、平均分、各维度分数、风险等级等信息。
# RiskAlert模型用于存储风险预警信息，包括学生、评估结果、预警等级、消息内容等。这些模型通过Django的ORM系统与数据库进行交互，
# 允许我们方便地创建、查询和管理评估结果和风险预警数据。
class AssessmentResult(models.Model):
    class RiskLevel(models.TextChoices):
        LOW = "low", "低风险"
        MEDIUM = "medium", "中风险"
        HIGH = "high", "高风险"

    response = models.OneToOneField(
        "surveys.QuestionnaireResponse", on_delete=models.CASCADE, related_name="assessment"
    )
    total_score = models.FloatField(default=0)
    avg_score = models.FloatField(default=0)
    dimension_scores = models.JSONField(default=dict)
    risk_level = models.CharField(max_length=16, choices=RiskLevel.choices, default=RiskLevel.LOW)
    predicted_risk_level = models.CharField(
        max_length=16, choices=RiskLevel.choices, default=RiskLevel.LOW
    )
    model_meta = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "评估结果"
        verbose_name_plural = "评估结果"
        ordering = ["-id"]


class RiskAlert(models.Model):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    assessment = models.ForeignKey(
        AssessmentResult, on_delete=models.CASCADE, related_name="alerts", null=True, blank=True
    )
    level = models.CharField(max_length=16, choices=AssessmentResult.RiskLevel.choices)
    message = models.CharField(max_length=240)
    created_at = models.DateTimeField(auto_now_add=True)
    is_acknowledged = models.BooleanField(default=False)
    acknowledged_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="acknowledged_alerts",
    )
    acknowledged_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "风险预警"
        verbose_name_plural = "风险预警"
        ordering = ["-id"]
