from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from apps.accounts.models import College

User = get_user_model()


class AiStreamEndpointTests(APITestCase):
    def setUp(self):
        college = College.objects.create(name="AI 测试学院")
        self.student = User.objects.create_user(
            username="ai_stream_student",
            password="123456",
            role=User.Role.STUDENT,
            college=college,
        )
        self.client.force_authenticate(self.student)

    def test_ai_stream_accepts_text_event_stream_header(self):
        resp = self.client.post(
            "/api/chat/conversations/ai/stream/",
            {"content": "最近有点焦虑"},
            format="json",
            HTTP_ACCEPT="text/event-stream",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn("text/event-stream", resp["Content-Type"])
