from django.conf import settings
from django.db import models

from apps.accounts.models import College
#这是问卷模板模型
#QuestionnaireTemplate用于创建和管理问卷模板
class QuestionnaireTemplate(models.Model):
    class ScaleType(models.TextChoices):
        SCL90_SAMPLE = "scl90_sample", "SCL-90（示例）"
        SAS_SAMPLE = "sas_sample", "SAS（示例）"
        SDS_SAMPLE = "sds_sample", "SDS（示例）"
        CUSTOM = "custom", "自定义"

    name = models.CharField(max_length=100, unique=True)
    scale_type = models.CharField(max_length=32, choices=ScaleType.choices, default=ScaleType.CUSTOM)
    description = models.CharField(max_length=240, blank=True)
    # questions: [{id,text,dimension,weight,min,max}, ...]
    questions = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "问卷模板"
        verbose_name_plural = "问卷模板"

    def __str__(self) -> str:
        return self.name

#这是问卷模型
class Questionnaire(models.Model):
    template = models.ForeignKey(QuestionnaireTemplate, on_delete=models.PROTECT)
    title = models.CharField(max_length=120)
    description = models.CharField(max_length=240, blank=True)
    is_active = models.BooleanField(default=True)
    target_college = models.ForeignKey(College, null=True, blank=True, on_delete=models.SET_NULL)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    start_at = models.DateTimeField(null=True, blank=True)
    end_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "问卷"
        verbose_name_plural = "问卷"
        ordering = ["-id"]

    def __str__(self) -> str:
        return self.title

#这是问卷作答模型
class QuestionnaireResponse(models.Model):
    questionnaire = models.ForeignKey(Questionnaire, on_delete=models.CASCADE, related_name="responses")
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="questionnaire_responses")
    answers = models.JSONField(default=dict)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "问卷作答"
        verbose_name_plural = "问卷作答"
        ordering = ["-id"]

#这是问卷复测任务模型
class QuestionnaireRetestTask(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "待完成"
        COMPLETED = "completed", "已完成"
        CANCELED = "canceled", "已取消"

    questionnaire = models.ForeignKey(Questionnaire, on_delete=models.CASCADE, related_name="retest_tasks")
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="questionnaire_retest_tasks",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_retest_tasks",
    )
    reason = models.CharField(max_length=240, blank=True)
    due_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "复测任务"
        verbose_name_plural = "复测任务"
        ordering = ["-id"]
