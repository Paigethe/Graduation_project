from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.assignment_utils import counselor_student_ids, is_student_assigned_to_counselor
from apps.accounts.permissions import (
    IsCounselor,
    IsCollegeAdminOrSysAdmin,
    IsStudent,
    IsSysAdmin,
)

from .models import Questionnaire, QuestionnaireResponse, QuestionnaireRetestTask, QuestionnaireTemplate
from .serializers import (
    QuestionnaireCreateSerializer,
    QuestionnaireResponseSerializer,
    QuestionnaireRetestTaskCreateSerializer,
    QuestionnaireRetestTaskSerializer,
    QuestionnaireSerializer,
    QuestionnaireTemplateCreateSerializer,
    QuestionnaireTemplateSerializer,
    SubmitResponseSerializer,
)

User = get_user_model()


class QuestionnaireTemplateViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet
):
    queryset = QuestionnaireTemplate.objects.all().order_by("-id")
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == "create":
            return QuestionnaireTemplateCreateSerializer
        return QuestionnaireTemplateSerializer

    def get_permissions(self):
        if self.action == "create":
            return [IsAuthenticated(), IsSysAdmin()]
        return super().get_permissions()


class QuestionnaireViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = Questionnaire.objects.select_related("template", "target_college", "created_by")

        now = timezone.now()
        active_window = models.Q(start_at__isnull=True) | models.Q(start_at__lte=now)
        active_window &= models.Q(end_at__isnull=True) | models.Q(end_at__gte=now)

        if getattr(user, "is_sys_admin", False):
            return qs

        if getattr(user, "is_student", False):
            if getattr(user, "college", None):
                return qs.filter(is_active=True).filter(active_window).filter(
                    models.Q(target_college__isnull=True) | models.Q(target_college=user.college)
                )
            return qs.filter(is_active=True).filter(active_window).filter(target_college__isnull=True)

        # counselor / college_admin: default show questionnaires in same college or global
        if getattr(user, "college", None):
            return qs.filter(models.Q(target_college__isnull=True) | models.Q(target_college=user.college))
        return qs.filter(target_college__isnull=True)

    def get_serializer_class(self):
        if self.action == "create":
            return QuestionnaireCreateSerializer
        return QuestionnaireSerializer

    def get_permissions(self):
        if self.action == "create":
            return [IsAuthenticated(), IsCollegeAdminOrSysAdmin()]
        if self.action == "submit":
            return [IsAuthenticated(), IsStudent()]
        return super().get_permissions()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        questionnaire = serializer.save()
        return Response(
            QuestionnaireSerializer(questionnaire, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        questionnaire = self.get_object()
        payload = SubmitResponseSerializer(data=request.data, context={"questionnaire": questionnaire})
        payload.is_valid(raise_exception=True)

        pending_task = (
            QuestionnaireRetestTask.objects.filter(
                questionnaire=questionnaire,
                student=request.user,
                status=QuestionnaireRetestTask.Status.PENDING,
            )
            .order_by("id")
            .first()
        )
        has_submitted = QuestionnaireResponse.objects.filter(
            questionnaire=questionnaire,
            student=request.user,
        ).exists()
        if has_submitted and not pending_task:
            return Response({"detail": "已提交过该问卷"}, status=status.HTTP_400_BAD_REQUEST)

        response_obj = QuestionnaireResponse.objects.create(
            questionnaire=questionnaire,
            student=request.user,
            answers=payload.validated_data["answers"],
        )

        # Create assessment result immediately
        from apps.assessments.services import create_assessment_for_response

        assessment = create_assessment_for_response(response_obj)
        if pending_task:
            pending_task.status = QuestionnaireRetestTask.Status.COMPLETED
            pending_task.completed_at = timezone.now()
            pending_task.save(update_fields=["status", "completed_at", "updated_at"])
        return Response(
            {
                "response": QuestionnaireResponseSerializer(response_obj).data,
                "assessment_id": assessment.id,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["get"])
    def stats(self, request, pk=None):
        questionnaire = self.get_object()
        responses_qs = QuestionnaireResponse.objects.filter(questionnaire=questionnaire)
        submitted_count = responses_qs.values("student_id").distinct().count()

        total_students = 0
        if questionnaire.target_college_id:
            student_qs = User.objects.filter(role=User.Role.STUDENT, college_id=questionnaire.target_college_id)
        else:
            student_qs = User.objects.filter(role=User.Role.STUDENT)
        total_students = student_qs.count()

        submitted_ids = list(responses_qs.values_list("student_id", flat=True).distinct())
        pending_students = list(
            student_qs.exclude(id__in=submitted_ids)
            .values("id", "username", "real_name", "student_no", "college_id", "college__name")
            .order_by("id")
        )

        # Score/risk distribution from assessments
        from apps.assessments.models import AssessmentResult

        assess_qs = AssessmentResult.objects.filter(response__questionnaire=questionnaire)
        risk_dist = {row["risk_level"]: row["c"] for row in assess_qs.values("risk_level").annotate(c=models.Count("id"))}

        buckets = {"0-1": 0, "1-2": 0, "2-3": 0, "3-4": 0, "4-5": 0}
        for avg in assess_qs.values_list("avg_score", flat=True):
            try:
                v = float(avg or 0)
            except Exception:
                v = 0.0
            if v < 1:
                buckets["0-1"] += 1
            elif v < 2:
                buckets["1-2"] += 1
            elif v < 3:
                buckets["2-3"] += 1
            elif v < 4:
                buckets["3-4"] += 1
            else:
                buckets["4-5"] += 1

        return Response(
            {
                "questionnaire_id": questionnaire.id,
                "total_students": total_students,
                "submitted_count": submitted_count,
                "responses_count": responses_qs.count(),
                "pending_count": max(total_students - submitted_count, 0),
                "submitted_rate": (submitted_count / total_students) if total_students else 0.0,
                "pending_students": pending_students,
                "risk_distribution": {
                    "low": int(risk_dist.get("low", 0)),
                    "medium": int(risk_dist.get("medium", 0)),
                    "high": int(risk_dist.get("high", 0)),
                },
                "score_distribution": buckets,
            }
        )


class QuestionnaireRetestTaskViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = QuestionnaireRetestTask.objects.select_related(
            "questionnaire",
            "questionnaire__template",
            "questionnaire__target_college",
            "questionnaire__created_by",
            "student",
            "student__college",
            "student__major",
            "student__class_group",
            "student__class_group__major",
            "created_by",
        ).order_by("-id")
        if getattr(user, "is_sys_admin", False):
            return qs
        if getattr(user, "is_student", False):
            return qs.filter(student=user)
        if getattr(user, "is_college_admin", False) and getattr(user, "college_id", None):
            return qs.filter(student__college_id=user.college_id)
        if getattr(user, "is_counselor", False):
            return qs.filter(student_id__in=counselor_student_ids(user))
        return qs.none()

    def get_serializer_class(self):
        if self.action == "create":
            return QuestionnaireRetestTaskCreateSerializer
        return QuestionnaireRetestTaskSerializer

    def get_permissions(self):
        if self.action == "create":
            return [IsAuthenticated(), IsCounselor()]
        return super().get_permissions()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        student = serializer.validated_data["student"]
        questionnaire = serializer.validated_data["questionnaire"]

        if not is_student_assigned_to_counselor(counselor=request.user, student=student):
            return Response({"detail": "该学生未分配给当前咨询教师"}, status=status.HTTP_400_BAD_REQUEST)
        if questionnaire.target_college_id and student.college_id != questionnaire.target_college_id:
            return Response({"detail": "问卷与学生学院不匹配"}, status=status.HTTP_400_BAD_REQUEST)

        obj = serializer.save()
        return Response(
            QuestionnaireRetestTaskSerializer(obj, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )
