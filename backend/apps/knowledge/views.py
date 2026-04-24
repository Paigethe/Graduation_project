from django.db import models
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.permissions import IsCollegeAdminOrSysAdmin, IsStudent

from .models import KnowledgeArticle, KnowledgeCategory, KnowledgeFavorite
from .serializers import (
    KnowledgeArticleCreateSerializer,
    KnowledgeArticleSerializer,
    KnowledgeCategorySerializer,
)


class KnowledgeCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = KnowledgeCategory.objects.all().order_by("id")
    serializer_class = KnowledgeCategorySerializer
    permission_classes = [IsAuthenticated]


class KnowledgeArticleViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = KnowledgeArticle.objects.select_related("category", "target_college", "created_by")
        if getattr(user, "is_sys_admin", False):
            return qs
        if getattr(user, "is_college_admin", False) and getattr(user, "college", None):
            return qs.filter(
                (models.Q(is_published=True) & (models.Q(target_college__isnull=True) | models.Q(target_college=user.college)))
                | models.Q(created_by=user)
            )
        if getattr(user, "college", None):
            return qs.filter(is_published=True).filter(
                models.Q(target_college__isnull=True) | models.Q(target_college=user.college)
            )
        return qs.filter(is_published=True, target_college__isnull=True)

    def get_serializer_class(self):
        if self.action == "create":
            return KnowledgeArticleCreateSerializer
        return KnowledgeArticleSerializer

    def get_permissions(self):
        if self.action == "create":
            return [IsAuthenticated(), IsCollegeAdminOrSysAdmin()]
        if self.action in {"favorite", "unfavorite"}:
            return [IsAuthenticated(), IsStudent()]
        return super().get_permissions()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        article = serializer.save()
        return Response(
            KnowledgeArticleSerializer(article, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"])
    def favorite(self, request, pk=None):
        article = self.get_object()
        KnowledgeFavorite.objects.get_or_create(user=request.user, article=article)
        return Response({"ok": True})

    @action(detail=True, methods=["post"])
    def unfavorite(self, request, pk=None):
        article = self.get_object()
        KnowledgeFavorite.objects.filter(user=request.user, article=article).delete()
        return Response({"ok": True})
