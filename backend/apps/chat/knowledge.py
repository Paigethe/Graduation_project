from django.db import models

from apps.knowledge.models import KnowledgeArticle


def suggest_articles(query: str, limit: int = 2):
    if not query:
        return []
    qs = KnowledgeArticle.objects.filter(is_published=True)
    qs = qs.filter(
        models.Q(title__icontains=query)
        | models.Q(summary__icontains=query)
        | models.Q(content__icontains=query)
    )
    return list(qs.order_by("-id").values("id", "title", "summary")[:limit])
