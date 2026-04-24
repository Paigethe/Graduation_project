from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.accounts.serializers import UserMeSerializer

from .models import Conversation, Message
from .utils import decrypt_text, encrypt_text

User = get_user_model()


class ConversationSerializer(serializers.ModelSerializer):
    student = UserMeSerializer(read_only=True)
    counselor = UserMeSerializer(read_only=True)
    last_message = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = ["id", "kind", "student", "counselor", "created_at", "updated_at", "last_message"]

    def get_last_message(self, obj: Conversation):
        last = obj.messages.order_by("-id").first()
        if not last:
            return None
        return {
            "id": last.id,
            "sender_kind": last.sender_kind,
            "content": decrypt_text(last.content_ciphertext),
            "created_at": last.created_at,
        }


class MessageSerializer(serializers.ModelSerializer):
    sender = UserMeSerializer(read_only=True)
    content = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = ["id", "sender_kind", "sender", "content", "created_at", "read_at"]

    def get_content(self, obj: Message) -> str:
        return decrypt_text(obj.content_ciphertext)


class SendMessageSerializer(serializers.Serializer):
    content = serializers.CharField(max_length=2000)

    def create_message(self, conversation: Conversation, sender: User, sender_kind: str = "user") -> Message:
        content = self.validated_data["content"]
        return Message.objects.create(
            conversation=conversation,
            sender=sender,
            sender_kind=sender_kind,
            content_ciphertext=encrypt_text(content),
        )


class AiChatSerializer(serializers.Serializer):
    content = serializers.CharField(max_length=2000)

