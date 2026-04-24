from django.contrib.auth import get_user_model
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone

from apps.accounts.assignment_utils import counselor_student_ids

from .models import AssessmentResult, RiskAlert
from .services import ensure_dormant_high_risk_alerts
from .serializers import AssessmentResultSerializer, RiskAlertSerializer

User = get_user_model()


class AssessmentResultViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = AssessmentResultSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = (
            AssessmentResult.objects.select_related(
                "response",
                "response__student",
                "response__questionnaire",
                "response__questionnaire__template",
                "response__questionnaire__target_college",
            )
            .all()
            .order_by("-id")
        )

        if getattr(user, "is_sys_admin", False):
            return qs
        if getattr(user, "is_student", False):
            return qs.filter(response__student=user)
        if getattr(user, "is_college_admin", False) and getattr(user, "college_id", None):
            return qs.filter(response__student__college_id=user.college_id)
        if getattr(user, "is_counselor", False):
            student_ids = counselor_student_ids(user)
            return qs.filter(response__student_id__in=student_ids)
        return qs.none()


class RiskAlertViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = RiskAlertSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        ensure_dormant_high_risk_alerts()
        qs = RiskAlert.objects.select_related("student", "assessment").all().order_by("-id")
        if getattr(user, "is_sys_admin", False):
            return qs
        if getattr(user, "is_student", False):
            return qs.filter(student=user)
        if getattr(user, "is_college_admin", False) and getattr(user, "college_id", None):
            return qs.filter(student__college_id=user.college_id)
        if getattr(user, "is_counselor", False):
            student_ids = counselor_student_ids(user)
            return qs.filter(student_id__in=student_ids)
        return qs.none()

    @action(detail=True, methods=["post"])
    def acknowledge(self, request, pk=None):
        alert = self.get_object()
        if getattr(request.user, "is_student", False):
            return Response({"detail": "无权限"}, status=status.HTTP_403_FORBIDDEN)
        alert.is_acknowledged = True
        alert.acknowledged_by = request.user
        alert.acknowledged_at = timezone.now()
        alert.save(update_fields=["is_acknowledged", "acknowledged_by", "acknowledged_at"])
        return Response({"ok": True})
