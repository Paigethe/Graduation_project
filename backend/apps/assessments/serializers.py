from rest_framework import serializers

from apps.accounts.serializers import UserMeSerializer
from apps.surveys.serializers import QuestionnaireSerializer

from .models import AssessmentResult, RiskAlert


class AssessmentResultSerializer(serializers.ModelSerializer):
    student = serializers.SerializerMethodField()
    questionnaire = serializers.SerializerMethodField()

    class Meta:
        model = AssessmentResult
        fields = [
            "id",
            "total_score",
            "avg_score",
            "dimension_scores",
            "risk_level",
            "predicted_risk_level",
            "model_meta",
            "created_at",
            "student",
            "questionnaire",
        ]

    def get_student(self, obj: AssessmentResult):
        return UserMeSerializer(obj.response.student).data

    def get_questionnaire(self, obj: AssessmentResult):
        return QuestionnaireSerializer(obj.response.questionnaire).data


class RiskAlertSerializer(serializers.ModelSerializer):
    student = UserMeSerializer(read_only=True)

    class Meta:
        model = RiskAlert
        fields = [
            "id",
            "student",
            "level",
            "message",
            "created_at",
            "is_acknowledged",
            "acknowledged_by",
            "acknowledged_at",
        ]
