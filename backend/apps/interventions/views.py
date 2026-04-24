from django.contrib.auth import get_user_model
from rest_framework import mixins, status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.assignment_utils import counselor_student_ids
from apps.accounts.permissions import IsCounselorOrSysAdmin

from .models import InterventionPlan
from .serializers import InterventionPlanCreateSerializer, InterventionPlanSerializer

User = get_user_model()


class InterventionPlanViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = InterventionPlan.objects.select_related(
            "student",
            "counselor",
            "assessment",
            "knowledge_article",
            "knowledge_article__category",
            "knowledge_article__target_college",
            "knowledge_article__created_by",
        ).order_by("-id")
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

    def get_serializer_class(self):
        if self.action == "create":
            return InterventionPlanCreateSerializer
        return InterventionPlanSerializer

    def get_permissions(self):
        if self.action in {"update", "partial_update"}:
            return [IsAuthenticated(), IsCounselorOrSysAdmin()]
        return super().get_permissions()

    def create(self, request, *args, **kwargs):
        if not getattr(request.user, "is_counselor", False):
            return Response({"detail": "仅咨询教师可创建干预建议"}, status=status.HTTP_403_FORBIDDEN)
        serializer = self.get_serializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        plan = serializer.save()
        return Response(InterventionPlanSerializer(plan).data, status=status.HTTP_201_CREATED)
