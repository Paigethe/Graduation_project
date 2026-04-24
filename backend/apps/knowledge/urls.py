from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import KnowledgeArticleViewSet, KnowledgeCategoryViewSet

router = DefaultRouter()
router.register(r"knowledge/categories", KnowledgeCategoryViewSet, basename="knowledge-category")
router.register(r"knowledge/articles", KnowledgeArticleViewSet, basename="knowledge-article")

urlpatterns = [
    path("", include(router.urls)),
]

