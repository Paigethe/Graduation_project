import json
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.core.serializers.json import DjangoJSONEncoder
from django.utils import timezone

from apps.assessments.models import AssessmentResult
from apps.interventions.models import InterventionPlan
from apps.surveys.models import Questionnaire, QuestionnaireResponse


def _backup_dir() -> Path:
    base = Path(__file__).resolve().parents[5]  # 02-系统实现代码/
    out = base / "storage" / "backups"
    out.mkdir(parents=True, exist_ok=True)
    return out


class Command(BaseCommand):
    help = "Export backup data for a college or all colleges."

    def add_arguments(self, parser):
        parser.add_argument("--college-id", type=int, default=None, help="College ID to export")
        parser.add_argument("--all", action="store_true", help="Export all colleges")

    def handle(self, *args, **options):
        college_id = options.get("college_id")
        export_all = options.get("all") or not college_id
        scope = "all" if export_all else "college"

        User = get_user_model()

        if export_all:
            students = list(
                User.objects.filter(role=User.Role.STUDENT)
                .values("id", "username", "real_name", "student_no", "college_id")
                .order_by("id")
            )
        else:
            students = list(
                User.objects.filter(role=User.Role.STUDENT, college_id=college_id)
                .values("id", "username", "real_name", "student_no", "college_id")
                .order_by("id")
            )
        student_ids = [s["id"] for s in students]

        if export_all:
            questionnaires = list(
                Questionnaire.objects.all()
                .values(
                    "id",
                    "title",
                    "description",
                    "is_active",
                    "start_at",
                    "end_at",
                    "template_id",
                    "target_college_id",
                    "created_at",
                )
                .order_by("id")
            )
        else:
            questionnaires = list(
                Questionnaire.objects.filter(target_college_id=college_id)
                .values(
                    "id",
                    "title",
                    "description",
                    "is_active",
                    "start_at",
                    "end_at",
                    "template_id",
                    "target_college_id",
                    "created_at",
                )
                .order_by("id")
            )

        responses = list(
            QuestionnaireResponse.objects.filter(student_id__in=student_ids)
            .values("id", "questionnaire_id", "student_id", "answers", "submitted_at")
            .order_by("id")
        )
        response_ids = [r["id"] for r in responses]

        assessments = list(
            AssessmentResult.objects.filter(response_id__in=response_ids)
            .values(
                "id",
                "response_id",
                "total_score",
                "avg_score",
                "dimension_scores",
                "risk_level",
                "predicted_risk_level",
                "created_at",
            )
            .order_by("id")
        )
        plans = list(
            InterventionPlan.objects.filter(student_id__in=student_ids)
            .values(
                "id",
                "student_id",
                "counselor_id",
                "assessment_id",
                "title",
                "content",
                "status",
                "created_at",
                "updated_at",
            )
            .order_by("id")
        )

        payload = {
            "meta": {
                "exported_at": timezone.now().isoformat(),
                "college_id": None if export_all else int(college_id),
                "scope": scope,
                "counts": {
                    "students": len(students),
                    "questionnaires": len(questionnaires),
                    "responses": len(responses),
                    "assessments": len(assessments),
                    "interventions": len(plans),
                },
            },
            "students": students,
            "questionnaires": questionnaires,
            "responses": responses,
            "assessments": assessments,
            "interventions": plans,
        }

        ts = timezone.now().strftime("%Y%m%d_%H%M%S")
        if export_all:
            out_path = _backup_dir() / f"all_colleges_backup_{ts}.json"
        else:
            out_path = _backup_dir() / f"college_{college_id}_backup_{ts}.json"

        out_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, cls=DjangoJSONEncoder),
            encoding="utf-8",
        )

        self.stdout.write(self.style.SUCCESS(f"Backup exported: {out_path}"))
