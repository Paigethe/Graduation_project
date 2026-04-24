from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Iterator
import json
import logging

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings

logger = logging.getLogger(__name__)


# OpenAI-compatible model endpoint settings.
AI_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "").strip()
AI_BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", "https://media.apiport.cc.cd/v1").strip()
AI_MODEL = os.environ.get("DEEPSEEK_MODEL", "grok-4.1-fast").strip()

HIGH_RISK_KEYWORDS = [
    "自杀",
    "轻生",
    "想死",
    "不想活",
    "结束生命",
    "割腕",
    "跳楼",
]


@dataclass(frozen=True)
class AiResult:
    answer: str
    risk_level: str  # low/medium/high
    hit_high_risk: bool
    model_version: str = "rules_v1"
    source: str = "rules"


def _get_fernet() -> Fernet | None:
    key = getattr(settings, "MESSAGE_ENCRYPTION_KEY", "").strip()
    if not key:
        return None
    try:
        return Fernet(key.encode("utf-8"))
    except Exception:
        return None


def encrypt_text(plain: str) -> str:
    f = _get_fernet()
    if not f:
        return plain
    return f.encrypt(plain.encode("utf-8")).decode("utf-8")


def decrypt_text(ciphertext: str) -> str:
    f = _get_fernet()
    if not f:
        return ciphertext
    try:
        return f.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        return ""


def _fmt_num(value: float) -> str:
    try:
        return f"{float(value):.2f}"
    except Exception:
        return "0.00"


def _student_context(student) -> str:
    from apps.assessments.models import AssessmentResult, RiskAlert
    from apps.interventions.models import InterventionPlan

    college_name = getattr(getattr(student, "college", None), "name", None) or "未知学院"
    student_no = (getattr(student, "student_no", "") or "").strip() or "未填写"
    real_name = (getattr(student, "real_name", "") or "").strip() or student.username

    lines = [
        f"- 学生账号: {student.username}",
        f"- 学生姓名: {real_name}",
        f"- 学号: {student_no}",
        f"- 学院: {college_name}",
    ]

    recent = list(
        AssessmentResult.objects.select_related("response__questionnaire")
        .filter(response__student=student)
        .order_by("-created_at")[:3]
    )
    if recent:
        lines.append("- 近期问卷评估结果(最近3条):")
        for idx, item in enumerate(recent, start=1):
            questionnaire = getattr(getattr(item.response, "questionnaire", None), "title", "未知问卷")
            dims = item.dimension_scores or {}
            top_dims = sorted(dims.items(), key=lambda x: float(x[1] or 0), reverse=True)[:3]
            top_text = ", ".join(f"{k}:{_fmt_num(v)}" for k, v in top_dims) if top_dims else "无"
            lines.append(
                f"  {idx}) 问卷={questionnaire}; 平均分={_fmt_num(item.avg_score)}; "
                f"风险={item.risk_level}; 预测={item.predicted_risk_level}; 维度Top={top_text}"
            )
    else:
        lines.append("- 近期问卷评估结果: 暂无")

    unack_count = RiskAlert.objects.filter(student=student, is_acknowledged=False).count()
    plan_count = InterventionPlan.objects.filter(student=student).count()
    lines.append(f"- 未确认预警数: {unack_count}")
    lines.append(f"- 历史干预计划数: {plan_count}")
    return "\n".join(lines)


def _system_prompt(student, *, is_first_turn: bool) -> str:
    context = _student_context(student)
    first_turn_note = (
        "这是该学生在当前会话中的首次交互，请先用1-2句话确认你已理解其背景，再给出建议。"
        if is_first_turn
        else "请基于以下背景延续本次会话，不要重复冗长背景。"
    )
    return (
        "你是高校心理健康系统中的AI心理支持助手。"
        "你的目标是提供支持性、非诊断性的建议，语气温和、结构清晰。\n"
        "如果用户表达明显自伤/自杀意图，请优先进行安全提醒，建议立即联系线下老师/家人/急救资源，"
        "并避免提供任何伤害细节。\n"
        "回答尽量用中文，控制在3-6条要点，给出可执行的小步骤。\n\n"
        f"{first_turn_note}\n\n"
        "以下是该学生的背景信息和近期问卷结果：\n"
        f"{context}"
    )


def _risk_by_keyword(text: str) -> tuple[str, bool]:
    hit_high = any(k in text for k in HIGH_RISK_KEYWORDS)
    if hit_high:
        return "high", True
    if any(k in text for k in ["焦虑", "紧张", "慌", "压力", "失眠", "睡不着", "情绪低落"]):
        return "medium", False
    return "low", False


def detect_risk(text: str) -> tuple[str, bool]:
    return _risk_by_keyword(text)


def _fallback_reply(message: str, *, hit_high_risk: bool) -> str:
    text = (message or "").strip()
    if hit_high_risk:
        return (
            "我听到你现在非常痛苦。你并不需要一个人扛着。\n"
            "如果你有立即伤害自己的冲动，请优先联系身边可信任的人/老师，或拨打当地紧急电话获得即时帮助。\n"
            "如果方便，你也可以告诉我：你现在安全吗？身边有人吗？"
        )

    if not text:
        return "我在。你可以和我说说你现在最困扰的一件事是什么？"

    if any(k in text for k in ["焦虑", "紧张", "慌", "压力"]):
        return (
            "你提到的感受很常见，先做一个60秒的放松：\n"
            "1) 吸气4秒-屏息2秒-呼气6秒，重复5轮；\n"
            "2) 把注意力放到脚底触感，提醒自己此刻安全。\n"
            "如果你愿意，说说最近压力最大的来源是什么？"
        )

    if any(k in text for k in ["失眠", "睡不着", "睡眠"]):
        return (
            "关于睡眠，建议先做三个小调整：\n"
            "1) 固定起床时间；\n"
            "2) 睡前1小时减少强光和短视频刺激；\n"
            "3) 躺床20分钟无睡意就起身放松，困了再回床。\n"
            "你一般几点入睡、几点起床？"
        )

    return "我明白了。你希望我先从情绪、学业、人际，还是睡眠作息来帮你梳理？"


def fallback_reply(message: str, *, hit_high_risk: bool) -> str:
    return _fallback_reply(message, hit_high_risk=hit_high_risk)


def _build_deepseek_messages(*, student, conversation, user_input: str) -> list[dict[str, str]]:
    history_qs = conversation.messages.order_by("id")
    history = []
    for msg in history_qs:
        content = decrypt_text(msg.content_ciphertext).strip()
        if not content:
            continue
        if msg.sender_kind == "ai":
            role = "assistant"
        elif msg.sender_kind == "user":
            role = "user"
        else:
            # Ignore system/internal messages for AI conversation context
            continue
        history.append({"role": role, "content": content})

    # Keep context window short and stable.
    history = history[-12:]
    if not history or history[-1]["role"] != "user":
        history.append({"role": "user", "content": user_input})

    is_first_turn = conversation.messages.filter(sender_kind="ai").count() == 0
    system = {"role": "system", "content": _system_prompt(student, is_first_turn=is_first_turn)}
    return [system, *history]


def build_model_messages(*, student, conversation, user_input: str) -> list[dict[str, str]]:
    return _build_deepseek_messages(student=student, conversation=conversation, user_input=user_input)


def _call_deepseek(messages: list[dict[str, str]]) -> str | None:
    try:
        from openai import OpenAI
    except Exception:
        return None

    if not AI_API_KEY:
        return None

    try:
        client = OpenAI(api_key=AI_API_KEY, base_url=AI_BASE_URL)
        resp = client.chat.completions.create(
            model=AI_MODEL,
            messages=messages,
            stream=False,
            temperature=0.6,
        )
        text = (resp.choices[0].message.content or "").strip()
        if text:
            return text
    except Exception as exc:
        # Some OpenAI-compatible gateways may return SSE for non-stream calls.
        logger.warning("OpenAI client non-stream call failed, fallback to raw SSE: %s", exc)

    return _call_deepseek_raw_sse(messages)


def _extract_delta_text(payload: dict) -> str | None:
    try:
        choices = payload.get("choices") or []
        if not choices:
            return None
        delta = choices[0].get("delta") or {}
        text = delta.get("content")
        if text is None:
            return None
        return str(text)
    except Exception:
        return None


def _call_deepseek_raw_sse(messages: list[dict[str, str]]) -> str | None:
    if not AI_API_KEY:
        return None

    try:
        import httpx
    except Exception as exc:
        logger.warning("httpx unavailable for raw SSE fallback: %s", exc)
        return None

    url = f"{AI_BASE_URL.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {AI_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
    }
    payload = {
        "model": AI_MODEL,
        "messages": messages,
        "temperature": 0.6,
        "stream": True,
    }

    parts: list[str] = []
    try:
        with httpx.stream("POST", url, headers=headers, json=payload, timeout=90) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                if not line:
                    continue
                raw = line.decode("utf-8") if isinstance(line, (bytes, bytearray)) else str(line)
                if not raw.startswith("data:"):
                    continue
                data = raw[5:].strip()
                if not data or data == "[DONE]":
                    continue
                try:
                    obj = json.loads(data)
                except Exception:
                    continue
                text = _extract_delta_text(obj)
                if text:
                    parts.append(text)
    except Exception as exc:
        logger.warning("Raw SSE fallback failed: %s", exc)
        return None

    result = "".join(parts).strip()
    return result or None


def stream_model_reply(messages: list[dict[str, str]]) -> Iterator[str]:
    try:
        from openai import OpenAI
    except Exception:
        return

    if not AI_API_KEY:
        return

    yielded = False
    try:
        client = OpenAI(api_key=AI_API_KEY, base_url=AI_BASE_URL)
        stream = client.chat.completions.create(
            model=AI_MODEL,
            messages=messages,
            stream=True,
            temperature=0.6,
        )
        for chunk in stream:
            choices = getattr(chunk, "choices", None) or []
            if not choices:
                continue
            delta = getattr(choices[0], "delta", None)
            text = getattr(delta, "content", None) if delta else None
            if text:
                yielded = True
                yield str(text)
        if yielded:
            return
    except Exception as exc:
        logger.warning("OpenAI client stream failed, fallback to raw SSE: %s", exc)

    # Fallback for OpenAI-compatible gateways that only support raw SSE well.
    try:
        import httpx
    except Exception as exc:
        logger.warning("httpx unavailable for stream fallback: %s", exc)
        return

    url = f"{AI_BASE_URL.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {AI_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
    }
    payload = {
        "model": AI_MODEL,
        "messages": messages,
        "temperature": 0.6,
        "stream": True,
    }
    try:
        with httpx.stream("POST", url, headers=headers, json=payload, timeout=90) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                if not line:
                    continue
                raw = line.decode("utf-8") if isinstance(line, (bytes, bytearray)) else str(line)
                if not raw.startswith("data:"):
                    continue
                data = raw[5:].strip()
                if not data or data == "[DONE]":
                    continue
                try:
                    obj = json.loads(data)
                except Exception:
                    continue
                text = _extract_delta_text(obj)
                if text:
                    yield text
    except Exception as exc:
        logger.warning("Raw SSE stream fallback failed: %s", exc)
        return


def append_high_risk_notice(ai_text: str, *, hit_high_risk: bool) -> str:
    if not hit_high_risk:
        return ai_text
    if "紧急" in ai_text or "立即" in ai_text:
        return ai_text
    return ai_text + "\n\n如果你现在有立即伤害自己的冲动，请立刻联系身边可信任的人、老师或当地紧急电话。"


def ai_reply(message: str, *, student=None, conversation=None) -> AiResult:
    text = (message or "").strip()
    risk_level, hit_high = detect_risk(text)

    ai_text = None
    if student is not None and conversation is not None:
        messages = build_model_messages(student=student, conversation=conversation, user_input=text)
        ai_text = _call_deepseek(messages)

    if not ai_text:
        ai_text = fallback_reply(text, hit_high_risk=hit_high)
        return AiResult(
            answer=ai_text,
            risk_level=risk_level,
            hit_high_risk=hit_high,
            model_version="rules_fallback_v1",
            source="rules_fallback",
        )

    ai_text = append_high_risk_notice(ai_text, hit_high_risk=hit_high)

    return AiResult(
        answer=ai_text,
        risk_level=risk_level,
        hit_high_risk=hit_high,
        model_version=AI_MODEL,
        source="openai_compat",
    )
