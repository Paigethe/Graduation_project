from django.urls import path

from .views import CollegeRiskOverviewView, DownloadReportView, ListReportsView, MonthlyReportView

urlpatterns = [
    path("reports/list/", ListReportsView.as_view(), name="reports-list"),
    path("reports/monthly/", MonthlyReportView.as_view(), name="reports-monthly"),
    path("reports/college-risk-overview/", CollegeRiskOverviewView.as_view(), name="reports-college-risk-overview"),
    path("reports/download/", DownloadReportView.as_view(), name="reports-download"),
]
