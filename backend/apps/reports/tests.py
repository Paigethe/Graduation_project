from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from apps.accounts.models import College

User = get_user_model()


class MonthlyReportMetricsTests(APITestCase):
    def setUp(self):
        self.college = College.objects.create(name="测试学院")
        self.college_admin = User.objects.create_user(
            username="college_admin_report",
            password="123456",
            role=User.Role.COLLEGE_ADMIN,
            college=self.college,
        )
        self.client.force_authenticate(self.college_admin)

    def test_monthly_report_only_returns_selected_sections(self):
        resp = self.client.post(
            "/api/reports/monthly/",
            {
                "month_start": "2026-02",
                "month_end": "2026-03",
                "metrics": ["风险分布"],
                "format": "json",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        summary = resp.data["summary"]
        self.assertEqual(summary["metrics"], ["风险分布"])
        self.assertIn("assessments", summary)
        self.assertIn("comparisons", summary)
        self.assertNotIn("alerts", summary)
        self.assertNotIn("interventions", summary)
        self.assertNotIn("questionnaires", summary)
        self.assertNotIn("retest", summary)

    def test_monthly_report_rejects_empty_metrics(self):
        resp = self.client.post(
            "/api/reports/monthly/",
            {
                "month_start": "2026-02",
                "month_end": "2026-03",
                "metrics": [],
                "format": "json",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("至少选择一个", str(resp.data))
