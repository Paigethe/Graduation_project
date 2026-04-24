from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from apps.accounts.models import College
from apps.assessments.models import AssessmentResult
from apps.surveys.models import Questionnaire, QuestionnaireTemplate

User = get_user_model()


class QuestionnaireSubmitValidationTests(APITestCase):
    def setUp(self):
        self.college = College.objects.create(name="测试学院")
        self.student = User.objects.create_user(
            username="submit_student",
            password="123456",
            role=User.Role.STUDENT,
            college=self.college,
        )
        self.template = QuestionnaireTemplate.objects.create(
            name="提交校验模板",
            scale_type=QuestionnaireTemplate.ScaleType.CUSTOM,
            questions=[
                {"id": 1, "text": "Q1", "dimension": "anxiety", "weight": 1, "min": 1, "max": 5},
                {"id": 2, "text": "Q2", "dimension": "depression", "weight": 1, "min": 1, "max": 5},
            ],
        )
        self.questionnaire = Questionnaire.objects.create(
            template=self.template,
            title="提交校验问卷",
            is_active=True,
            target_college=self.college,
        )
        self.client.force_authenticate(self.student)

    def test_submit_rejects_missing_answers(self):
        resp = self.client.post(
            f"/api/surveys/questionnaires/{self.questionnaire.id}/submit/",
            {"answers": {"1": 5}},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("missing_question_ids", resp.data)

    def test_submit_rejects_out_of_range_answers(self):
        resp = self.client.post(
            f"/api/surveys/questionnaires/{self.questionnaire.id}/submit/",
            {"answers": {"1": 999, "2": 3}},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("1", resp.data)

    def test_submit_accepts_complete_answers_and_creates_assessment(self):
        resp = self.client.post(
            f"/api/surveys/questionnaires/{self.questionnaire.id}/submit/",
            {"answers": {"1": 5, "2": 3}},
            format="json",
        )
        self.assertEqual(resp.status_code, 201)
        assessment_id = resp.data.get("assessment_id")
        self.assertTrue(assessment_id)
        assessment = AssessmentResult.objects.get(id=assessment_id)
        self.assertAlmostEqual(float(assessment.avg_score), 4.0)
