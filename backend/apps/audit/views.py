from rest_framework import mixins, viewsets
from rest_framework.permissions import IsAuthenticated

from apps.accounts.permissions import IsSysAdmin

from .models import AuditLog
from .serializers import AuditLogSerializer


class AuditLogViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    queryset = AuditLog.objects.select_related("user").all().order_by("-id")
    serializer_class = AuditLogSerializer
    permission_classes = [IsAuthenticated, IsSysAdmin]

