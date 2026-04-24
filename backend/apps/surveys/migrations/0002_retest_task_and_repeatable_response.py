from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0002_academic_hierarchy"),
        ("surveys", "0001_initial"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="questionnaireresponse",
            name="uniq_response_questionnaire_student",
        ),
        migrations.CreateModel(
            name="QuestionnaireRetestTask",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("reason", models.CharField(blank=True, max_length=240)),
                ("due_date", models.DateField(blank=True, null=True)),
                (
                    "status",
                    models.CharField(
                        choices=[("pending", "待完成"), ("completed", "已完成"), ("canceled", "已取消")],
                        default="pending",
                        max_length=16,
                    ),
                ),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="created_retest_tasks",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "questionnaire",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="retest_tasks",
                        to="surveys.questionnaire",
                    ),
                ),
                (
                    "student",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="questionnaire_retest_tasks",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "复测任务",
                "verbose_name_plural": "复测任务",
                "ordering": ["-id"],
            },
        ),
    ]
