from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import QuestionnaireRetestTaskViewSet, QuestionnaireTemplateViewSet, QuestionnaireViewSet

router = DefaultRouter()
router.register(r"surveys/templates", QuestionnaireTemplateViewSet, basename="survey-template")
router.register(r"surveys/questionnaires", QuestionnaireViewSet, basename="survey-questionnaire")
router.register(r"surveys/retest-tasks", QuestionnaireRetestTaskViewSet, basename="survey-retest-task")

urlpatterns = [
    path("", include(router.urls)),
]
