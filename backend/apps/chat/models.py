from django.conf import settings
from django.db import models


class Conversation(models.Model):
    class Kind(models.TextChoices):
        AI = "ai", "AI自助"
        HUMAN = "human", "人工咨询"

    kind = models.CharField(max_length=16, choices=Kind.choices)
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="conversations_as_student"
    )
    counselor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="conversations_as_counselor",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "会话"
        verbose_name_plural = "会话"
        ordering = ["-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["kind", "student", "counselor"], name="uniq_conversation_kind_pair"
            )
        ]


class Message(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )  # AI message sender is null
    sender_kind = models.CharField(max_length=16, default="user")  # user / ai
    content_ciphertext = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "消息"
        verbose_name_plural = "消息"
        ordering = ["id"]
