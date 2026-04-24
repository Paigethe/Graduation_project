from rest_framework import serializers

from apps.accounts.serializers import CollegeSerializer, UserMeSerializer

from .models import KnowledgeArticle, KnowledgeCategory, KnowledgeFavorite


class KnowledgeCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = KnowledgeCategory
        fields = ["id", "name"]


class KnowledgeArticleSerializer(serializers.ModelSerializer):
    category = KnowledgeCategorySerializer(read_only=True)
    target_college = CollegeSerializer(read_only=True)
    created_by = UserMeSerializer(read_only=True)
    is_favorited = serializers.SerializerMethodField()
    document_url = serializers.SerializerMethodField()

    class Meta:
        model = KnowledgeArticle
        fields = [
            "id",
            "title",
            "summary",
            "content",
            "document",
            "document_url",
            "category",
            "is_published",
            "target_college",
            "created_by",
            "created_at",
            "updated_at",
            "is_favorited",
        ]

    def get_is_favorited(self, obj: KnowledgeArticle) -> bool:
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return False
        return KnowledgeFavorite.objects.filter(user=user, article=obj).exists()

    def get_document_url(self, obj: KnowledgeArticle) -> str | None:
        if not obj.document:
            return None
        request = self.context.get("request")
        try:
            url = obj.document.url
        except Exception:
            return None
        if request:
            return request.build_absolute_uri(url)
        return url


class KnowledgeArticleCreateSerializer(serializers.ModelSerializer):
    category_id = serializers.IntegerField(required=False, allow_null=True, write_only=True)
    target_college_id = serializers.IntegerField(required=False, allow_null=True, write_only=True)
    document = serializers.FileField(required=False, allow_null=True)

    class Meta:
        model = KnowledgeArticle
        fields = [
            "id",
            "title",
            "summary",
            "content",
            "document",
            "is_published",
            "category_id",
            "target_college_id",
        ]

    def create(self, validated_data):
        category_id = validated_data.pop("category_id", None)
        target_college_id = validated_data.pop("target_college_id", None)
        request = self.context["request"]
        user = request.user

        category = None
        if category_id:
            category = KnowledgeCategory.objects.filter(id=category_id).first()

        target_college = None
        if getattr(user, "is_college_admin", False):
            target_college = user.college
        elif target_college_id:
            from apps.accounts.models import College

            target_college = College.objects.filter(id=target_college_id).first()

        return KnowledgeArticle.objects.create(
            **validated_data,
            category=category,
            target_college=target_college,
            created_by=user,
        )
