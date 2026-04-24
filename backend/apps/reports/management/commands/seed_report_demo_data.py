from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import College
from apps.assessments.models import RiskAlert
from apps.assessments.services import create_assessment_for_response
from apps.interventions.models import InterventionPlan
from apps.surveys.models import (
    Questionnaire,
    QuestionnaireResponse,
    QuestionnaireRetestTask,
    QuestionnaireTemplate,
)

User = get_user_model()

MARKER = "[报表演示202603-202604]"
QUESTIONNAIRE_TITLE = f"{MARKER} 月报模拟问卷"


@dataclass(frozen=True)
class Scenario:
    student: User
    submitted_at: datetime
    base_score: float
    dim_overrides: dict[str, float]
    create_plan: bool = False
    plan_status: str = InterventionPlan.Status.IN_PROGRESS
    plan_offset_days: int = 2
    plan_title: str = "月报演示干预建议"
    retest_created_at: datetime | None = None
    retest_completed_at: datetime | None = None
    retest_due_date: datetime | None = None
    followup_submitted_at: datetime | None = None
    followup_base_score: float | None = None
    followup_dim_overrides: dict[str, float] | None = None


def _aware(year: int, month: int, day: int, hour: int = 9, minute: int = 0) -> datetime:
    return timezone.make_aware(datetime(year, month, day, hour, minute, 0))


def _set_model_dates(instance, **values):
    instance.__class__.objects.filter(pk=instance.pk).update(**values)
    for key, value in values.items():
        setattr(instance, key, value)


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _build_answers(questions: list[dict], *, base_score: float, dim_overrides: dict[str, float]) -> dict[str, float]:
    answers: dict[str, float] = {}
    for index, question in enumerate(questions):
        qid = str(question.get("id"))
        dimension = str(question.get("dimension") or "overall")
        q_min = float(question.get("min", 1))
        q_max = float(question.get("max", 5))
        score = float(dim_overrides.get(dimension, base_score))
        score += ((index % 3) - 1) * 0.12
        answers[qid] = round(_clamp(score, q_min, q_max), 2)
    return answers


def _create_response_with_assessment(
    *,
    questionnaire: Questionnaire,
    student: User,
    submitted_at: datetime,
    answers: dict[str, float],
):
    response = QuestionnaireResponse.objects.create(
        questionnaire=questionnaire,
        student=student,
        answers=answers,
    )
    _set_model_dates(response, submitted_at=submitted_at)

    assessment = create_assessment_for_response(response)
    _set_model_dates(assessment, created_at=submitted_at + timedelta(minutes=2))
    RiskAlert.objects.filter(assessment=assessment).update(created_at=submitted_at + timedelta(minutes=4))
    return response, assessment


class Command(BaseCommand):
    help = "为学院月报生成 2026-03 至 2026-04 的演示模拟数据（独立问卷，不污染原始业务问卷）"

    def add_arguments(self, parser):
        parser.add_argument("--college-id", type=int, default=1, help="学院 ID，默认 1")
        parser.add_argument("--template-id", type=int, default=2, help="问卷模板 ID，默认 2（SCL-90 模拟）")
        parser.add_argument("--students", type=int, default=12, help="参与演示的学生数，默认 12")

    @transaction.atomic
    def handle(self, *args, **options):
        college_id = int(options["college_id"])
        template_id = int(options["template_id"])
        student_count = max(int(options["students"]), 8)

        college = College.objects.filter(id=college_id).first()
        if not college:
            raise CommandError(f"学院不存在：{college_id}")

        template = QuestionnaireTemplate.objects.filter(id=template_id).first()
        if not template:
            raise CommandError(f"问卷模板不存在：{template_id}")
        questions = template.questions or []
        if not questions:
            raise CommandError("模板题目为空，无法生成演示数据")

        students = list(
            User.objects.filter(role=User.Role.STUDENT, college_id=college.id)
            .order_by("id")[:student_count]
        )
        if len(students) < 8:
            raise CommandError("该学院学生数量不足，至少需要 8 名学生用于演示数据")

        counselor = (
            User.objects.filter(role=User.Role.COUNSELOR, college_id=college.id)
            .order_by("id")
            .first()
        )
        if not counselor:
            raise CommandError("该学院没有可用辅导员，无法生成干预与复测演示数据")

        questionnaire, created = Questionnaire.objects.get_or_create(
            title=f"{QUESTIONNAIRE_TITLE}（{college.name}）",
            defaults={
                "template": template,
                "description": f"{MARKER} 面向月报演示的模拟问卷",
                "is_active": False,
                "target_college": college,
                "created_by": counselor,
            },
        )
        if not created:
            QuestionnaireResponse.objects.filter(questionnaire=questionnaire).delete()
            QuestionnaireRetestTask.objects.filter(
                questionnaire=questionnaire,
                reason__contains=MARKER,
            ).delete()
            InterventionPlan.objects.filter(
                student__college_id=college.id,
                title__startswith=MARKER,
            ).delete()

        scenarios = [
            Scenario(
                student=students[0],
                submitted_at=_aware(2026, 3, 5, 10, 20),
                base_score=3.0,
                dim_overrides={"anxiety": 4.4, "somatization": 4.0, "interpersonal": 3.8},
                create_plan=True,
                plan_status=InterventionPlan.Status.IN_PROGRESS,
                plan_title="睡眠与焦虑联合干预",
                retest_created_at=_aware(2026, 3, 18, 9, 0),
                retest_completed_at=_aware(2026, 4, 6, 11, 0),
                retest_due_date=_aware(2026, 4, 10).date(),
                followup_submitted_at=_aware(2026, 4, 6, 14, 30),
                followup_base_score=2.0,
                followup_dim_overrides={"anxiety": 2.2, "somatization": 1.9, "interpersonal": 2.0},
            ),
            Scenario(
                student=students[1],
                submitted_at=_aware(2026, 3, 6, 15, 10),
                base_score=3.1,
                dim_overrides={"depression": 4.3, "psychoticism": 3.9, "additional": 4.0},
                create_plan=True,
                plan_status=InterventionPlan.Status.SENT,
                plan_title="情绪低落重点跟进",
                retest_created_at=_aware(2026, 3, 20, 9, 30),
                retest_completed_at=_aware(2026, 4, 9, 10, 0),
                retest_due_date=_aware(2026, 4, 12).date(),
                followup_submitted_at=_aware(2026, 4, 9, 13, 0),
                followup_base_score=2.5,
                followup_dim_overrides={"depression": 2.9, "psychoticism": 2.5, "additional": 2.7},
            ),
            Scenario(
                student=students[2],
                submitted_at=_aware(2026, 3, 8, 9, 15),
                base_score=3.2,
                dim_overrides={"compulsive": 4.2, "hostility": 4.0, "paranoid": 3.8},
                create_plan=True,
                plan_status=InterventionPlan.Status.DONE,
                plan_title="强迫与敌意维度干预",
                retest_created_at=_aware(2026, 3, 22, 8, 30),
                retest_completed_at=_aware(2026, 4, 12, 9, 30),
                retest_due_date=_aware(2026, 4, 15).date(),
                followup_submitted_at=_aware(2026, 4, 12, 14, 30),
                followup_base_score=1.9,
                followup_dim_overrides={"compulsive": 2.1, "hostility": 2.0, "paranoid": 1.8},
            ),
            Scenario(
                student=students[3],
                submitted_at=_aware(2026, 3, 10, 11, 0),
                base_score=2.6,
                dim_overrides={"anxiety": 3.2, "phobic": 3.0, "additional": 3.1},
                create_plan=True,
                plan_status=InterventionPlan.Status.IN_PROGRESS,
                plan_title="一般焦虑跟进",
            ),
            Scenario(
                student=students[4],
                submitted_at=_aware(2026, 3, 12, 13, 20),
                base_score=2.7,
                dim_overrides={"depression": 3.4, "interpersonal": 3.2},
                create_plan=True,
                plan_status=InterventionPlan.Status.SENT,
                plan_title="抑郁与人际支持建议",
            ),
            Scenario(
                student=students[5],
                submitted_at=_aware(2026, 3, 15, 9, 40),
                base_score=2.8,
                dim_overrides={"hostility": 3.4, "paranoid": 3.3},
                create_plan=False,
            ),
            Scenario(
                student=students[6],
                submitted_at=_aware(2026, 3, 18, 10, 10),
                base_score=2.0,
                dim_overrides={"additional": 2.3, "somatization": 2.1},
                create_plan=False,
            ),
            Scenario(
                student=students[7],
                submitted_at=_aware(2026, 3, 22, 16, 0),
                base_score=1.8,
                dim_overrides={"interpersonal": 2.2},
                create_plan=False,
            ),
            Scenario(
                student=students[8],
                submitted_at=_aware(2026, 4, 3, 10, 0),
                base_score=2.9,
                dim_overrides={"anxiety": 3.2, "compulsive": 3.0},
                create_plan=False,
            ),
            Scenario(
                student=students[9],
                submitted_at=_aware(2026, 4, 5, 15, 30),
                base_score=2.1,
                dim_overrides={"somatization": 2.4},
                create_plan=False,
            ),
            Scenario(
                student=students[10],
                submitted_at=_aware(2026, 4, 7, 11, 30),
                base_score=2.6,
                dim_overrides={"depression": 3.1, "additional": 3.0},
                create_plan=True,
                plan_status=InterventionPlan.Status.IN_PROGRESS,
                plan_title="四月情绪风险跟踪",
            ),
            Scenario(
                student=students[11],
                submitted_at=_aware(2026, 4, 9, 9, 20),
                base_score=1.9,
                dim_overrides={"phobic": 2.2},
                create_plan=False,
            ),
        ]

        created_responses = 0
        created_assessments = 0
        created_plans = 0
        created_retests = 0

        for scenario in scenarios:
            answers = _build_answers(
                questions,
                base_score=scenario.base_score,
                dim_overrides=scenario.dim_overrides,
            )
            _response, assessment = _create_response_with_assessment(
                questionnaire=questionnaire,
                student=scenario.student,
                submitted_at=scenario.submitted_at,
                answers=answers,
            )
            created_responses += 1
            created_assessments += 1

            if scenario.create_plan:
                plan_created_at = scenario.submitted_at + timedelta(days=scenario.plan_offset_days)
                plan = InterventionPlan.objects.create(
                    student=scenario.student,
                    counselor=counselor,
                    assessment=assessment,
                    title=f"{MARKER} {scenario.plan_title}",
                    content=(
                        f"{MARKER} 根据近期测评结果，建议围绕"
                        f"{'、'.join(sorted(scenario.dim_overrides.keys())[:3])}维度进行跟踪与干预。"
                    ),
                    status=scenario.plan_status,
                )
                _set_model_dates(
                    plan,
                    created_at=plan_created_at,
                    updated_at=plan_created_at + timedelta(days=2),
                )
                created_plans += 1

            if scenario.retest_created_at and scenario.followup_submitted_at:
                task = QuestionnaireRetestTask.objects.create(
                    questionnaire=questionnaire,
                    student=scenario.student,
                    created_by=counselor,
                    reason=f"{MARKER} 高风险学生复测任务",
                    due_date=scenario.retest_due_date,
                    status=QuestionnaireRetestTask.Status.COMPLETED,
                    completed_at=scenario.retest_completed_at,
                )
                _set_model_dates(
                    task,
                    created_at=scenario.retest_created_at,
                    updated_at=(scenario.retest_completed_at or scenario.retest_created_at),
                    completed_at=(scenario.retest_completed_at or scenario.retest_created_at),
                )
                created_retests += 1

                followup_answers = _build_answers(
                    questions,
                    base_score=float(scenario.followup_base_score or scenario.base_score),
                    dim_overrides=scenario.followup_dim_overrides or {},
                )
                _create_response_with_assessment(
                    questionnaire=questionnaire,
                    student=scenario.student,
                    submitted_at=scenario.followup_submitted_at,
                    answers=followup_answers,
                )
                created_responses += 1
                created_assessments += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"已生成报表演示数据：学院={college.name}，问卷={questionnaire.title}，"
                f"responses={created_responses}，assessments={created_assessments}，"
                f"plans={created_plans}，retests={created_retests}"
            )
        )
