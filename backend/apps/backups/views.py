import json
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.serializers.json import DjangoJSONEncoder
from django.http import FileResponse
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from apps.accounts.permissions import IsCollegeAdminOrSysAdmin

from apps.assessments.models import AssessmentResult
from apps.interventions.models import InterventionPlan
from apps.surveys.models import Questionnaire, QuestionnaireResponse

User = get_user_model()


def _backup_dir() -> Path:
    base = Path(__file__).resolve().parents[3]  # 02-系统实现代码/
    out = base / "storage" / "backups"
    out.mkdir(parents=True, exist_ok=True)
    return out


class ExportBackupView(APIView):
    permission_classes = [IsAuthenticated, IsCollegeAdminOrSysAdmin]

    def post(self, request):
        user = request.user
        college_id = request.data.get("college_id")
        scope = "college"

        if getattr(user, "is_college_admin", False):
            if not user.college_id:
                return Response({"detail": "当前账号未绑定学院"}, status=status.HTTP_400_BAD_REQUEST)
            college_id = user.college_id
        else:
            if not college_id:
                # sys admin can export all colleges if college_id not provided
                scope = "all"

        if scope == "all":
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

        if scope == "all":
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
                "college_id": int(college_id) if scope != "all" and college_id else None,
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
        if scope == "all":
            out_path = _backup_dir() / f"all_colleges_backup_{ts}.json"
        else:
            out_path = _backup_dir() / f"college_{college_id}_backup_{ts}.json"
        out_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, cls=DjangoJSONEncoder),
            encoding="utf-8",
        )

        return Response({"ok": True, "file": str(out_path), "meta": payload["meta"]})


class DownloadBackupView(APIView):
    permission_classes = [IsAuthenticated, IsCollegeAdminOrSysAdmin]

    def get(self, request):
        name = request.query_params.get("name")
        if not name:
            return Response({"detail": "name 必填"}, status=status.HTTP_400_BAD_REQUEST)
        path = _backup_dir() / name
        if not path.exists() or not path.is_file():
            return Response({"detail": "文件不存在"}, status=status.HTTP_404_NOT_FOUND)
        user = request.user
        if getattr(user, "is_college_admin", False):
            if not user.college_id:
                return Response({"detail": "当前账号未绑定学院"}, status=status.HTTP_400_BAD_REQUEST)
            if f"college_{user.college_id}_" not in path.name:
                return Response({"detail": "无权限"}, status=status.HTTP_403_FORBIDDEN)
        return FileResponse(open(path, "rb"), as_attachment=True, filename=path.name)
