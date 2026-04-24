from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import AssessmentResultViewSet, RiskAlertViewSet

router = DefaultRouter()
router.register(r"assessments/results", AssessmentResultViewSet, basename="assessment-result")
router.register(r"assessments/alerts", RiskAlertViewSet, basename="risk-alert")

urlpatterns = [
    path("", include(router.urls)),
]

