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

#   这个文件定义了两个视图集：AssessmentResultViewSet和RiskAlertViewSet，分别用于处理评估结果和风险预警的API请求。
# 风险预警的API请求在获取查询集时会调用ensure_dormant_high_risk_alerts函数，确保系统中所有处于休眠状态的高风险预警都被激活。两个视图集都使用了IsAuthenticated权限类，要求用户必须登录才能访问这些API端点。
# AssessmentResultViewSet提供了列表和详情视图，允许用户查看评估结果。
# RiskAlertViewSet提供了列表视图和一个自定义的操作acknowledge，允许用户查看风险预警并标记为已知晓。
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
# 根据用户的角色和权限，过滤评估结果的查询集。系统管理员可以查看所有评估结果，学生只能查看自己的评估结果，学院管理员可以查看所属学院学生的评估结果，辅导员可以查看自己负责学生的评估结果。其他用户没有权限查看任何评估结果。
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

# 这个视图集提供了一个自定义的操作acknowledge，允许用户标记评估结果相关的风险预警为已知晓。学生没有权限执行此操作。
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
