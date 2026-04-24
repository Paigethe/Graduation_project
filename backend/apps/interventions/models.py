from django.conf import settings
from django.db import models


class InterventionPlan(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "草稿"
        SENT = "sent", "已推送"
        IN_PROGRESS = "in_progress", "进行中"
        DONE = "done", "已完成"

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="intervention_plans"
    )
    counselor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="created_plans"
    )
    assessment = models.ForeignKey(
        "assessments.AssessmentResult", on_delete=models.SET_NULL, null=True, blank=True
    )
    knowledge_article = models.ForeignKey(
        "knowledge.KnowledgeArticle",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="intervention_plans",
    )
    title = models.CharField(max_length=120, default="干预建议")
    content = models.TextField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.IN_PROGRESS)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "干预建议"
        verbose_name_plural = "干预建议"
        ordering = ["-id"]
