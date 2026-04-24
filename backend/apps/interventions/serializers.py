from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.accounts.assignment_utils import is_student_assigned_to_counselor
from apps.accounts.serializers import UserMeSerializer
from apps.knowledge.models import KnowledgeArticle
from apps.knowledge.serializers import KnowledgeArticleSerializer

from .models import InterventionPlan

User = get_user_model()


class InterventionPlanMutationMixin:
    knowledge_article_id = serializers.IntegerField(required=False, allow_null=True, write_only=True)

    def validate_knowledge_article_id(self, value: int | None) -> int | None:
        if value in {None, ""}:
            return None
        article = KnowledgeArticle.objects.filter(id=value, is_published=True).first()
        if not article:
            raise serializers.ValidationError("无效的知识卡片")
        return value

    def _pop_knowledge_article(self, validated_data):
        article_id = validated_data.pop("knowledge_article_id", serializers.empty)
        if article_id is serializers.empty:
            return serializers.empty
        if article_id is None:
            return None
        return KnowledgeArticle.objects.get(id=article_id)


class InterventionPlanSerializer(InterventionPlanMutationMixin, serializers.ModelSerializer):
    knowledge_article_id = serializers.IntegerField(required=False, allow_null=True, write_only=True)
    student = UserMeSerializer(read_only=True)
    counselor = UserMeSerializer(read_only=True)
    knowledge_article = KnowledgeArticleSerializer(read_only=True)

    class Meta:
        model = InterventionPlan
        fields = [
            "id",
            "title",
            "content",
            "status",
            "created_at",
            "updated_at",
            "student",
            "counselor",
            "assessment",
            "knowledge_article",
            "knowledge_article_id",
        ]

    def update(self, instance, validated_data):
        article = self._pop_knowledge_article(validated_data)
        if article is not serializers.empty:
            instance.knowledge_article = article
        return super().update(instance, validated_data)


class InterventionPlanCreateSerializer(InterventionPlanMutationMixin, serializers.ModelSerializer):
    student_id = serializers.IntegerField(write_only=True)
    knowledge_article_id = serializers.IntegerField(required=False, allow_null=True, write_only=True)

    class Meta:
        model = InterventionPlan
        fields = ["id", "student_id", "assessment", "title", "content", "status", "knowledge_article_id"]

    def validate_student_id(self, value: int) -> int:
        user = self.context["request"].user
        student = User.objects.filter(id=value, role=User.Role.STUDENT).first()
        if not student:
            raise serializers.ValidationError("无效的学生")
        if getattr(user, "is_counselor", False):
            if not is_student_assigned_to_counselor(counselor=user, student=student):
                raise serializers.ValidationError("该学生未分配给当前咨询教师")
        return value

    def create(self, validated_data):
        user = self.context["request"].user
        student = User.objects.get(id=validated_data.pop("student_id"))
        article = self._pop_knowledge_article(validated_data)
        if "status" not in validated_data:
            validated_data["status"] = InterventionPlan.Status.IN_PROGRESS
        return InterventionPlan.objects.create(
            student=student,
            counselor=user,
            knowledge_article=None if article is serializers.empty else article,
            **validated_data,
        )
