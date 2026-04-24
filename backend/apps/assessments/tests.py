from __future__ import annotations

from unittest import mock

from django.test import SimpleTestCase, override_settings

from .models import AssessmentResult
from .predictor import (
    build_payload_from_assessment_scores,
    predict_risk,
    reset_predictor_cache,
)


class PredictorTests(SimpleTestCase):
    def tearDown(self):
        reset_predictor_cache()
        super().tearDown()

    @override_settings(RISK_MODEL_ENABLED=False)
    def test_predict_risk_fallbacks_to_placeholder_when_model_disabled(self):
        reset_predictor_cache()
        result = predict_risk(avg_score=3.6, dim_scores={"anxiety": 2.0})
        self.assertEqual(result.model_version, "placeholder_v1")
        self.assertEqual(result.predicted_risk_level, AssessmentResult.RiskLevel.HIGH)

    def test_build_payload_from_assessment_scores_generates_expected_bridged_fields(self):
        payload = build_payload_from_assessment_scores(
            avg_score=3.2,
            dim_scores={
                "anxiety": 3.8,
                "depression": 2.9,
                "sleep": 4.1,
                "social": 2.5,
            },
            student_profile={
                "age": "21",
                "gender": "F",
                "cgpa": "3.4",
                "family_history_mental_illness": "no",
                "suicidal_ideation": "0",
            },
        )
        self.assertEqual(payload["age"], 21.0)
        self.assertEqual(payload["gender"], "female")
        self.assertEqual(payload["cgpa"], 3.4)
        self.assertAlmostEqual(payload["study_satisfaction"], 2.8)
        self.assertAlmostEqual(payload["sleep_quality"], 1.9)
        self.assertEqual(payload["anxiety_signal"], 1.0)
        self.assertEqual(payload["depression_signal"], 0.0)
        self.assertAlmostEqual(payload["peer_pressure"], 2.5)
        self.assertAlmostEqual(payload["social_support"], 3.5)
        self.assertEqual(payload["family_history_mental_illness"], 0.0)
        self.assertEqual(payload["suicidal_ideation"], 0.0)

    def test_predict_risk_uses_model_bundle_when_available(self):
        class FakeModel:
            classes_ = ["low", "medium", "high"]

            def predict(self, _x):
                return ["high"]

            def predict_proba(self, _x):
                return [[0.01, 0.08, 0.91]]

        class FakePandas:
            @staticmethod
            def DataFrame(rows, columns=None):
                return {"rows": rows, "columns": columns}

        fake_bundle = {
            "pd": FakePandas(),
            "model": FakeModel(),
            "feature_columns": [
                "age",
                "cgpa",
                "academic_pressure",
                "work_pressure",
                "study_satisfaction",
                "sleep_quality",
                "dietary_habits",
                "anxiety_signal",
                "depression_signal",
                "panic_signal",
                "social_support",
                "peer_pressure",
                "financial_stress",
                "family_history_mental_illness",
                "suicidal_ideation",
                "gender",
            ],
            "model_version": "unit_model_v1",
        }

        with mock.patch("apps.assessments.predictor._load_model_bundle", return_value=fake_bundle):
            result = predict_risk(
                avg_score=3.1,
                dim_scores={"anxiety": 3.5, "depression": 3.2, "sleep": 2.8},
            )
        self.assertEqual(result.model_version, "unit_model_v1")
        self.assertEqual(result.predicted_risk_level, AssessmentResult.RiskLevel.HIGH)
        self.assertAlmostEqual(result.confidence, 0.91)
