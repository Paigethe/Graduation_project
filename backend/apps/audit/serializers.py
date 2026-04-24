from rest_framework import serializers

from apps.accounts.serializers import UserMeSerializer

from .models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    user = UserMeSerializer(read_only=True)

    class Meta:
        model = AuditLog
        fields = [
            "id",
            "user",
            "method",
            "path",
            "status_code",
            "duration_ms",
            "ip",
            "created_at",
        ]

