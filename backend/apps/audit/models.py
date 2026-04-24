from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    method = models.CharField(max_length=10)
    path = models.CharField(max_length=200)
    status_code = models.IntegerField(default=0)
    duration_ms = models.IntegerField(default=0)
    ip = models.CharField(max_length=45, blank=True)
    user_agent = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "审计日志"
        verbose_name_plural = "审计日志"
        ordering = ["-id"]

