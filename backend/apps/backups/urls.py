from django.urls import path

from .views import DownloadBackupView, ExportBackupView

urlpatterns = [
    path("backups/export/", ExportBackupView.as_view(), name="backup-export"),
    path("backups/download/", DownloadBackupView.as_view(), name="backup-download"),
]

