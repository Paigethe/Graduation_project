from django.conf import settings
from django.db import models

from apps.accounts.models import College


class KnowledgeCategory(models.Model):
    name = models.CharField(max_length=64, unique=True)

    class Meta:
        verbose_name = "知识分类"
        verbose_name_plural = "知识分类"

    def __str__(self) -> str:
        return self.name


class KnowledgeArticle(models.Model):
    category = models.ForeignKey(
        KnowledgeCategory, on_delete=models.SET_NULL, null=True, blank=True
    )
    title = models.CharField(max_length=120)
    summary = models.CharField(max_length=240, blank=True)
    content = models.TextField()
    document = models.FileField(upload_to="knowledge_docs/", null=True, blank=True)
    is_published = models.BooleanField(default=True)
    target_college = models.ForeignKey(
        College, on_delete=models.SET_NULL, null=True, blank=True
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "知识文章"
        verbose_name_plural = "知识文章"
        ordering = ["-id"]

    def __str__(self) -> str:
        return self.title


class KnowledgeFavorite(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    article = models.ForeignKey(KnowledgeArticle, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "知识收藏"
        verbose_name_plural = "知识收藏"
        constraints = [
            models.UniqueConstraint(fields=["user", "article"], name="uniq_fav_user_article")
        ]
