import json

from django.contrib.auth import get_user_model
from django.http import StreamingHttpResponse
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import BaseRenderer
from rest_framework.response import Response

from apps.accounts.assignment_utils import (
    first_assigned_counselor_for_student,
    is_student_assigned_to_counselor,
)

from .models import Conversation, Message
from .serializers import AiChatSerializer, ConversationSerializer, MessageSerializer, SendMessageSerializer
from .knowledge import suggest_articles
from .utils import (
    AI_MODEL,
    ai_reply,
    append_high_risk_notice,
    build_model_messages,
    detect_risk,
    encrypt_text,
    fallback_reply,
    stream_model_reply,
)

User = get_user_model()


class EventStreamRenderer(BaseRenderer):
    media_type = "text/event-stream"
    format = "event-stream"
    charset = "utf-8"
    render_style = "binary"

    def render(self, data, accepted_media_type=None, renderer_context=None):
        return data


class ConversationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ConversationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = Conversation.objects.all().order_by("-updated_at", "-id")
        if getattr(user, "is_sys_admin", False):
            return qs
        if getattr(user, "is_student", False):
            return qs.filter(student=user)
        if getattr(user, "is_counselor", False):
            return qs.filter(counselor=user)
        if getattr(user, "is_college_admin", False) and getattr(user, "college_id", None):
            return qs.filter(student__college_id=user.college_id)
        return qs.none()

    def _check_access(self, conv: Conversation, user: User) -> bool:
        if getattr(user, "is_sys_admin", False):
            return True
        if getattr(user, "is_student", False):
            return conv.student_id == user.id
        if getattr(user, "is_counselor", False):
            return conv.counselor_id == user.id
        if getattr(user, "is_college_admin", False) and getattr(user, "college_id", None):
            return conv.student.college_id == user.college_id
        return False

    @action(detail=True, methods=["get", "post"])
    def messages(self, request, pk=None):
        conv = self.get_object()
        if not self._check_access(conv, request.user):
            return Response({"detail": "无权限"}, status=status.HTTP_403_FORBIDDEN)

        if request.method.lower() == "get":
            qs = Message.objects.filter(conversation=conv).select_related("sender").order_by("id")
            return Response(MessageSerializer(qs, many=True).data)

        payload = SendMessageSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        msg = Message.objects.create(
            conversation=conv,
            sender=request.user,
            sender_kind="user",
            content_ciphertext=encrypt_text(payload.validated_data["content"]),
        )
        conv.save(update_fields=["updated_at"])
        return Response(MessageSerializer(msg).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def read(self, request, pk=None):
        conv = self.get_object()
        if not self._check_access(conv, request.user):
            return Response({"detail": "无权限"}, status=status.HTTP_403_FORBIDDEN)

        now = timezone.now()
        qs = Message.objects.filter(conversation=conv, read_at__isnull=True).exclude(sender=request.user)
        updated = qs.update(read_at=now)
        return Response({"ok": True, "count": updated, "read_at": now})

    @action(detail=False, methods=["post"], url_path="human/start")
    def start_human(self, request):
        user = request.user
        counselor_id = request.data.get("counselor_id")
        student_id = request.data.get("student_id")

        if getattr(user, "is_student", False):
            if counselor_id:
                counselor = User.objects.filter(id=counselor_id, role=User.Role.COUNSELOR).first()
                if not counselor:
                    return Response({"detail": "无效的咨询教师"}, status=status.HTTP_400_BAD_REQUEST)
                if not is_student_assigned_to_counselor(counselor=counselor, student=user):
                    return Response({"detail": "该教师未分配给你"}, status=status.HTTP_400_BAD_REQUEST)
            else:
                counselor = first_assigned_counselor_for_student(user)
                if not counselor:
                    return Response({"detail": "未找到分配的咨询教师"}, status=status.HTTP_400_BAD_REQUEST)
            conv, _created = Conversation.objects.get_or_create(
                kind=Conversation.Kind.HUMAN, student=user, counselor=counselor
            )
            return Response(ConversationSerializer(conv).data)

        if getattr(user, "is_counselor", False):
            if not student_id:
                return Response({"detail": "student_id 必填"}, status=status.HTTP_400_BAD_REQUEST)
            student = User.objects.filter(id=student_id, role=User.Role.STUDENT).first()
            if not student:
                return Response({"detail": "无效的学生"}, status=status.HTTP_400_BAD_REQUEST)
            if not is_student_assigned_to_counselor(counselor=user, student=student):
                return Response({"detail": "该学生未分配给当前咨询教师"}, status=status.HTTP_400_BAD_REQUEST)
            conv, _created = Conversation.objects.get_or_create(
                kind=Conversation.Kind.HUMAN, student=student, counselor=user
            )
            return Response(ConversationSerializer(conv).data)

        return Response({"detail": "无权限"}, status=status.HTTP_403_FORBIDDEN)

    @action(detail=False, methods=["post"], url_path="ai")
    def ai_chat(self, request):
        user = request.user
        if not getattr(user, "is_student", False):
            return Response({"detail": "仅学生可使用 AI 自助"}, status=status.HTTP_403_FORBIDDEN)

        payload = AiChatSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        content = payload.validated_data["content"]

        conv, _created = Conversation.objects.get_or_create(
            kind=Conversation.Kind.AI, student=user, counselor=None
        )
        user_msg = Message.objects.create(
            conversation=conv,
            sender=user,
            sender_kind="user",
            content_ciphertext=encrypt_text(content),
        )

        ai = ai_reply(content, student=user, conversation=conv)
        recommendations = []
        if not ai.hit_high_risk:
            recommendations = suggest_articles(content)
        ai_msg = Message.objects.create(
            conversation=conv,
            sender=None,
            sender_kind="ai",
            content_ciphertext=encrypt_text(ai.answer),
        )
        conv.save(update_fields=["updated_at"])

        handoff_required = False
        handoff_conv = None
        handoff_error = None

        if ai.hit_high_risk:
            from apps.assessments.models import AssessmentResult, RiskAlert

            handoff_required = True
            RiskAlert.objects.create(
                student=user,
                assessment=None,
                level=AssessmentResult.RiskLevel.HIGH,
                message="AI 对话触发高风险关键词，已生成预警并尝试转接人工咨询。",
            )

            # Try handoff to assigned counselor
            counselor = first_assigned_counselor_for_student(user)
            if counselor:
                handoff_conv, _created = Conversation.objects.get_or_create(
                    kind=Conversation.Kind.HUMAN, student=user, counselor=counselor
                )
                Message.objects.create(
                    conversation=handoff_conv,
                    sender=None,
                    sender_kind="system",
                    content_ciphertext=encrypt_text("AI 对话触发高风险，已自动转接人工咨询。"),
                )
                handoff_conv.save(update_fields=["updated_at"])
            else:
                handoff_error = "未找到分配的咨询教师，无法自动转接。"

        return Response(
            {
                "conversation": ConversationSerializer(conv).data,
                "user_message": MessageSerializer(user_msg).data,
                "ai_message": MessageSerializer(ai_msg).data,
                "risk_level": ai.risk_level,
                "ai_meta": {
                    "model_version": ai.model_version,
                    "source": ai.source,
                },
                "recommendations": recommendations,
                "handoff_required": handoff_required,
                "handoff_conversation": ConversationSerializer(handoff_conv).data if handoff_conv else None,
                "handoff_error": handoff_error,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(
        detail=False,
        methods=["post"],
        url_path="ai/stream",
        renderer_classes=[EventStreamRenderer],
    )
    def ai_chat_stream(self, request):
        user = request.user
        if not getattr(user, "is_student", False):
            return Response({"detail": "仅学生可使用 AI 自助"}, status=status.HTTP_403_FORBIDDEN)

        payload = AiChatSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        content = payload.validated_data["content"]

        conv, _created = Conversation.objects.get_or_create(
            kind=Conversation.Kind.AI, student=user, counselor=None
        )
        user_msg = Message.objects.create(
            conversation=conv,
            sender=user,
            sender_kind="user",
            content_ciphertext=encrypt_text(content),
        )

        def sse(event: str, data: dict) -> str:
            return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False, default=str)}\n\n"

        def event_stream():
            risk_level, hit_high_risk = detect_risk(content)
            ai_text_parts: list[str] = []
            model_source = "rules_fallback"
            model_version = "rules_fallback_v1"

            try:
                messages = build_model_messages(student=user, conversation=conv, user_input=content)
                for delta in stream_model_reply(messages):
                    ai_text_parts.append(delta)
                    yield sse("delta", {"content": delta})

                ai_text = "".join(ai_text_parts).strip()
                if not ai_text:
                    ai_text = fallback_reply(content, hit_high_risk=hit_high_risk)
                else:
                    model_source = "openai_compat"
                    model_version = AI_MODEL
                    ai_text = append_high_risk_notice(ai_text, hit_high_risk=hit_high_risk)

                recommendations = []
                if not hit_high_risk:
                    recommendations = suggest_articles(content)

                ai_msg = Message.objects.create(
                    conversation=conv,
                    sender=None,
                    sender_kind="ai",
                    content_ciphertext=encrypt_text(ai_text),
                )
                conv.save(update_fields=["updated_at"])

                handoff_required = False
                handoff_conv = None
                handoff_error = None

                if hit_high_risk:
                    from apps.assessments.models import AssessmentResult, RiskAlert

                    handoff_required = True
                    RiskAlert.objects.create(
                        student=user,
                        assessment=None,
                        level=AssessmentResult.RiskLevel.HIGH,
                        message="AI 对话触发高风险关键词，已生成预警并尝试转接人工咨询。",
                    )

                    counselor = first_assigned_counselor_for_student(user)
                    if counselor:
                        handoff_conv, _created = Conversation.objects.get_or_create(
                            kind=Conversation.Kind.HUMAN, student=user, counselor=counselor
                        )
                        Message.objects.create(
                            conversation=handoff_conv,
                            sender=None,
                            sender_kind="system",
                            content_ciphertext=encrypt_text("AI 对话触发高风险，已自动转接人工咨询。"),
                        )
                        handoff_conv.save(update_fields=["updated_at"])
                    else:
                        handoff_error = "未找到分配的咨询教师，无法自动转接。"

                yield sse(
                    "done",
                    {
                        "conversation": ConversationSerializer(conv).data,
                        "user_message": MessageSerializer(user_msg).data,
                        "ai_message": MessageSerializer(ai_msg).data,
                        "risk_level": risk_level,
                        "ai_meta": {
                            "model_version": model_version,
                            "source": model_source,
                        },
                        "recommendations": recommendations,
                        "handoff_required": handoff_required,
                        "handoff_conversation": ConversationSerializer(handoff_conv).data if handoff_conv else None,
                        "handoff_error": handoff_error,
                    },
                )
            except Exception as exc:
                yield sse("error", {"detail": f"流式响应失败: {str(exc)}"})

        response = StreamingHttpResponse(event_stream(), content_type="text/event-stream; charset=utf-8")
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        return response
