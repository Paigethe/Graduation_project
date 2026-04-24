import time

from django.db import OperationalError


class AuditLogMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.path.startswith("/api/"):
            return self.get_response(request)

        start = time.monotonic()
        response = self.get_response(request)
        duration_ms = int((time.monotonic() - start) * 1000)

        try:
            from .models import AuditLog

            user = getattr(request, "user", None)
            if user is not None and getattr(user, "is_authenticated", False):
                user_id = user.id
            else:
                user_id = None

            AuditLog.objects.create(
                user_id=user_id,
                method=request.method,
                path=request.path,
                status_code=getattr(response, "status_code", 0) or 0,
                duration_ms=duration_ms,
                ip=str(request.META.get("REMOTE_ADDR", ""))[:45],
                user_agent=str(request.META.get("HTTP_USER_AGENT", ""))[:300],
            )
        except OperationalError:
            # Database not ready/migrated yet; avoid breaking requests
            pass
        except Exception:
            pass

        return response

