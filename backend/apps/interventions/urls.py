from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import InterventionPlanViewSet

router = DefaultRouter()
router.register(r"interventions/plans", InterventionPlanViewSet, basename="intervention-plan")

urlpatterns = [
    path("", include(router.urls)),
]

