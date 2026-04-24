import html
import json
import os
import re
import shutil
import subprocess
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Avg, Count
from django.http import FileResponse
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsCollegeAdminOrSysAdmin, IsSysAdmin


DIMENSION_LABELS = {
    "overall": "总体",
    "anxiety": "焦虑",
    "depression": "抑郁",
    "somatization": "躯体化",
    "interpersonal": "人际敏感",
    "compulsive": "强迫症状",
    "hostility": "敌对",
    "paranoid": "偏执",
    "psychoticism": "精神病性",
    "sleep": "睡眠",
    "stress": "压力",
    "phobic": "恐怖",
    "additional": "附加项",
    "obsession": "强迫症状",
    "obsessional": "强迫症状",
    "phobic_anxiety": "恐怖",
}

REPORT_METRIC_RISK_DISTRIBUTION = "风险分布"
REPORT_METRIC_INTERVENTION_EFFECT = "干预效果"
REPORT_METRIC_ALERT_TREND = "预警趋势"
REPORT_METRIC_QUESTIONNAIRE_SUBMISSION = "问卷提交"
REPORT_METRIC_RETEST_IMPROVEMENT = "复测改善"
REPORT_METRICS = (
    REPORT_METRIC_RISK_DISTRIBUTION,
    REPORT_METRIC_INTERVENTION_EFFECT,
    REPORT_METRIC_ALERT_TREND,
    REPORT_METRIC_QUESTIONNAIRE_SUBMISSION,
    REPORT_METRIC_RETEST_IMPROVEMENT,
)


def _report_dir() -> Path:
    base = Path(__file__).resolve().parents[3]
    out = base / "storage" / "reports"
    out.mkdir(parents=True, exist_ok=True)
    return out


def _parse_month(value: str):
    match = re.fullmatch(r"(\d{4})-(\d{2})", str(value or "").strip())
    if not match:
        return None
    year = int(match.group(1))
    month = int(match.group(2))
    if month < 1 or month > 12:
        return None
    return year, month


def _month_to_bounds(value: str):
    parsed = _parse_month(value)
    if not parsed:
        return None
    year, month = parsed
    start = timezone.make_aware(datetime(year, month, 1, 0, 0, 0))
    if month == 12:
        end = timezone.make_aware(datetime(year + 1, 1, 1, 0, 0, 0))
    else:
        end = timezone.make_aware(datetime(year, month + 1, 1, 0, 0, 0))
    return start, end


def _month_index(value: str) -> int | None:
    parsed = _parse_month(value)
    if not parsed:
        return None
    year, month = parsed
    return year * 12 + (month - 1)


def _index_to_month(value: int) -> str:
    year = value // 12
    month = value % 12 + 1
    return f"{year:04d}-{month:02d}"


def _normalize_period(month: str | None, month_start: str | None, month_end: str | None, month_range):
    start_value = month_start or month
    end_value = month_end or month
    if isinstance(month_range, (list, tuple)) and len(month_range) == 2:
        start_value = start_value or month_range[0]
        end_value = end_value or month_range[1]

    if not start_value or not end_value:
        return None

    start_idx = _month_index(str(start_value))
    end_idx = _month_index(str(end_value))
    if start_idx is None or end_idx is None or start_idx > end_idx:
        return None

    normalized_start = _index_to_month(start_idx)
    normalized_end = _index_to_month(end_idx)
    start_bounds = _month_to_bounds(normalized_start)
    end_bounds = _month_to_bounds(normalized_end)
    if not start_bounds or not end_bounds:
        return None
    start_dt = start_bounds[0]
    end_dt = end_bounds[1]
    month_count = end_idx - start_idx + 1
    return normalized_start, normalized_end, start_dt, end_dt, month_count


def _month_label(value: str) -> str:
    parsed = _parse_month(value)
    if not parsed:
        return value
    year, month = parsed
    return f"{year}年{month:02d}月"


def _period_label(start_month: str, end_month: str) -> str:
    if start_month == end_month:
        return _month_label(start_month)
    return f"{_month_label(start_month)} 至 {_month_label(end_month)}"


def _percent(part: int, total: int) -> float:
    if not total:
        return 0.0
    return round(part / total * 100, 2)


def _format_percent(value: float | None) -> str:
    if value is None:
        return "—"
    return f"{value:.2f}%"


def _normalize_metrics(raw_metrics) -> tuple[list[str], list[str]]:
    if raw_metrics is None:
        return list(REPORT_METRICS), []

    if not isinstance(raw_metrics, (list, tuple)):
        raw_metrics = [raw_metrics]

    normalized: list[str] = []
    invalid: list[str] = []
    for item in raw_metrics:
        label = str(item or "").strip()
        if not label:
            continue
        if label in REPORT_METRICS:
            if label not in normalized:
                normalized.append(label)
            continue
        invalid.append(label)
    return normalized, invalid


def _percent_change(current: int, previous: int) -> float | None:
    if previous == 0:
        return None
    return round((current - previous) / previous * 100, 2)


def _wrap_text(text: str, width: int = 34) -> list[str]:
    raw = str(text or "")
    if not raw:
        return [""]
    lines: list[str] = []
    for paragraph in raw.splitlines() or [""]:
        if not paragraph:
            lines.append("")
            continue
        current = ""
        current_width = 0
        for char in paragraph:
            char_width = 2 if ord(char) > 127 else 1
            if current and current_width + char_width > width:
                lines.append(current)
                current = char
                current_width = char_width
            else:
                current += char
                current_width += char_width
        if current:
            lines.append(current)
    return lines or [""]


def _pdf_hex_text(text: str) -> str:
    return text.encode("utf-16-be").hex().upper()


def _hex_to_rgb(color: str) -> tuple[float, float, float]:
    raw = str(color or "").strip().lstrip("#")
    if len(raw) != 6:
        return 0.0, 0.0, 0.0
    try:
        return tuple(int(raw[index:index + 2], 16) / 255 for index in (0, 2, 4))
    except Exception:
        return 0.0, 0.0, 0.0


def _pdf_rect(
    x: float,
    y: float,
    width: float,
    height: float,
    *,
    fill: str | None = None,
    stroke: str | None = None,
    line_width: float = 1.0,
) -> str:
    parts: list[str] = []
    if fill:
        r, g, b = _hex_to_rgb(fill)
        parts.append(f"{r:.3f} {g:.3f} {b:.3f} rg")
    if stroke:
        r, g, b = _hex_to_rgb(stroke)
        parts.append(f"{r:.3f} {g:.3f} {b:.3f} RG")
        parts.append(f"{line_width:.2f} w")
    parts.append(f"{x:.2f} {y:.2f} {width:.2f} {height:.2f} re")
    if fill and stroke:
        parts.append("B")
    elif fill:
        parts.append("f")
    elif stroke:
        parts.append("S")
    return "\n".join(parts) + "\n"


def _pdf_text(text: str, x: float, y: float, *, size: float = 11, color: str = "111827") -> str:
    r, g, b = _hex_to_rgb(color)
    return (
        f"BT /F1 {size:.2f} Tf "
        f"{r:.3f} {g:.3f} {b:.3f} rg "
        f"1 0 0 1 {x:.2f} {y:.2f} Tm "
        f"<{_pdf_hex_text(text)}> Tj ET\n"
    )


def _build_pdf_pages(page_contents: list[str]) -> bytes:
    objects: list[bytes] = []
    page_refs: list[int] = []
    content_refs: list[int] = []

    catalog_obj = 1
    pages_obj = 2
    font_obj = 3
    cid_font_obj = 4
    descriptor_obj = 5
    next_obj = 6

    for _content in page_contents:
        page_refs.append(next_obj)
        content_refs.append(next_obj + 1)
        next_obj += 2

    kids = " ".join(f"{ref} 0 R" for ref in page_refs)
    objects.append(f"{catalog_obj} 0 obj << /Type /Catalog /Pages {pages_obj} 0 R >> endobj\n".encode("utf-8"))
    objects.append(
        f"{pages_obj} 0 obj << /Type /Pages /Kids [{kids}] /Count {len(page_refs)} >> endobj\n".encode("utf-8")
    )
    objects.append(
        (
            f"{font_obj} 0 obj << /Type /Font /Subtype /Type0 /BaseFont /STSong-Light "
            f"/Encoding /UniGB-UCS2-H /DescendantFonts [{cid_font_obj} 0 R] >> endobj\n"
        ).encode("utf-8")
    )
    objects.append(
        (
            f"{cid_font_obj} 0 obj << /Type /Font /Subtype /CIDFontType0 /BaseFont /STSong-Light "
            f"/CIDSystemInfo << /Registry (Adobe) /Ordering (GB1) /Supplement 4 >> "
            f"/FontDescriptor {descriptor_obj} 0 R /DW 1000 >> endobj\n"
        ).encode("utf-8")
    )
    objects.append(
        (
            f"{descriptor_obj} 0 obj << /Type /FontDescriptor /FontName /STSong-Light "
            f"/Flags 4 /Ascent 880 /Descent -120 /CapHeight 700 /ItalicAngle 0 /StemV 80 >> endobj\n"
        ).encode("utf-8")
    )

    for index, content_text in enumerate(page_contents):
        page_obj = page_refs[index]
        content_obj = content_refs[index]
        content = content_text.encode("utf-8")
        objects.append(
            (
                f"{page_obj} 0 obj << /Type /Page /Parent {pages_obj} 0 R "
                f"/MediaBox [0 0 595 842] /Resources << /Font << /F1 {font_obj} 0 R >> >> "
                f"/Contents {content_obj} 0 R >> endobj\n"
            ).encode("utf-8")
        )
        objects.append(
            f"{content_obj} 0 obj << /Length {len(content)} >> stream\n".encode("utf-8")
            + content
            + b"endstream endobj\n"
        )

    header = b"%PDF-1.4\n%\xe4\xe2\xe3\xcf\n"
    offsets = []
    current = len(header)
    for obj in objects:
        offsets.append(current)
        current += len(obj)
    xref_offset = current

    xref = [b"xref\n", f"0 {len(objects) + 1}\n".encode("utf-8"), b"0000000000 65535 f \n"]
    for offset in offsets:
        xref.append(f"{offset:010d} 00000 n \n".encode("utf-8"))

    trailer = (
        b"trailer << /Size "
        + str(len(objects) + 1).encode("utf-8")
        + b" /Root 1 0 R >>\nstartxref\n"
        + str(xref_offset).encode("utf-8")
        + b"\n%%EOF\n"
    )
    return header + b"".join(objects) + b"".join(xref) + trailer


def _build_cjk_pdf(lines: list[str]) -> bytes:
    wrapped: list[str] = []
    for line in lines:
        wrapped.extend(_wrap_text(line))
    if not wrapped:
        wrapped = [""]

    page_line_capacity = 36
    page_chunks = [
        wrapped[index:index + page_line_capacity]
        for index in range(0, len(wrapped), page_line_capacity)
    ]

    page_contents: list[str] = []
    for index, chunk in enumerate(page_chunks):
        y = 790
        content_lines = []
        for line in chunk:
            content_lines.append(
                f"BT /F1 11 Tf 48 {y} Td <{_pdf_hex_text(line)}> Tj ET"
            )
            y -= 20
        page_contents.append("\n".join(content_lines) + "\n")

    return _build_pdf_pages(page_contents)


def _extend_wrapped(lines: list[str], text: str, *, width: int = 52, indent: str = ""):
    wrapped = _wrap_text(text, width=width)
    if not wrapped:
        lines.append(indent)
        return
    for index, part in enumerate(wrapped):
        prefix = indent if index == 0 else (" " * len(indent))
        lines.append(f"{prefix}{part}")


def _build_report_text_lines(*, meta: dict, summary: dict, sections: list[tuple[str, list[str]]]) -> list[str]:
    lines: list[str] = [
        "学生心理健康分析报告",
        "=" * 30,
        f"学院：{meta.get('college_name') or meta.get('college_id')}",
        f"统计周期：{meta.get('period_label') or '—'}",
        f"生成时间：{str(meta.get('created_at') or '').replace('T', ' ')[:19]}",
        f"包含指标：{'、'.join(summary.get('metrics') or []) or '—'}",
        "",
    ]

    snapshot_items: list[str] = []
    assessments = summary.get("assessments") or {}
    alerts = summary.get("alerts") or {}
    interventions = summary.get("interventions") or {}
    questionnaires = summary.get("questionnaires") or {}
    retest = summary.get("retest") or {}

    if assessments:
        snapshot_items.append(f"评估样本 {assessments.get('count', 0)} 份")
        snapshot_items.append(
            f"高风险占比 {_format_percent((assessments.get('risk_distribution') or {}).get('high_ratio'))}"
        )
    if alerts:
        snapshot_items.append(f"预警总数 {alerts.get('count', 0)} 条")
        snapshot_items.append(f"高风险未处理 {alerts.get('high_unack_count', 0)} 条")
    if interventions:
        snapshot_items.append(f"干预介入率 {_format_percent(interventions.get('intervention_rate'))}")
        snapshot_items.append(f"辅导员介入率 {_format_percent(interventions.get('counselor_involved_rate'))}")
    if questionnaires:
        snapshot_items.append(f"问卷数 {questionnaires.get('questionnaires_count', 0)} 份")
        snapshot_items.append(f"作答数 {questionnaires.get('responses_count', 0)} 次")
    if retest:
        snapshot_items.append(f"复测完成 {retest.get('completed_task_count', 0)} 条")
        snapshot_items.append(f"改善率 {_format_percent(retest.get('improvement_rate'))}")

    if snapshot_items:
        lines.append("摘要")
        lines.append("-" * 30)
        for item in snapshot_items:
            _extend_wrapped(lines, f"- {item}", width=52)
        lines.append("")

    for index, (title, section_lines) in enumerate(sections, start=1):
        lines.append(f"{_section_index_label(index)}、{title}")
        lines.append("-" * 30)
        for item in section_lines:
            _extend_wrapped(lines, item, width=52)
        if index < len(sections):
            lines.append("")

    return lines


def _summary_cards_from_summary(summary: dict) -> list[dict[str, str]]:
    cards: list[dict[str, str]] = []
    assessments = summary.get("assessments") or {}
    alerts = summary.get("alerts") or {}
    interventions = summary.get("interventions") or {}
    questionnaires = summary.get("questionnaires") or {}
    retest = summary.get("retest") or {}

    if assessments:
        cards.append(
            {
                "title": "评估样本",
                "value": f"{assessments.get('count', 0)} 份",
                "hint": f"平均分 {float(assessments.get('avg_score') or 0):.2f}",
            }
        )
        cards.append(
            {
                "title": "高风险占比",
                "value": _format_percent((assessments.get("risk_distribution") or {}).get("high_ratio")),
                "hint": "基于当前统计周期",
            }
        )
    if alerts:
        cards.append(
            {
                "title": "预警总数",
                "value": f"{alerts.get('count', 0)} 条",
                "hint": f"高风险未处理 {alerts.get('high_unack_count', 0)} 条",
            }
        )
    if interventions:
        cards.append(
            {
                "title": "干预介入率",
                "value": _format_percent(interventions.get("intervention_rate")),
                "hint": f"辅导员介入率 {_format_percent(interventions.get('counselor_involved_rate'))}",
            }
        )
    if questionnaires:
        cards.append(
            {
                "title": "问卷提交",
                "value": f"{questionnaires.get('responses_count', 0)} 次",
                "hint": f"统计范围内问卷 {questionnaires.get('questionnaires_count', 0)} 份",
            }
        )
    if retest:
        cards.append(
            {
                "title": "复测改善率",
                "value": _format_percent(retest.get("improvement_rate")),
                "hint": f"恢复为安全 {retest.get('improved_to_safe_count', 0)} 人",
            }
        )

    return cards


def _render_report_html(*, meta: dict, summary: dict, sections: list[tuple[str, list[str]]]) -> str:
    cards = _summary_cards_from_summary(summary)

    card_html = []
    for card in cards:
        card_html.append(
            f"""
            <section class="summary-card">
              <div class="summary-card__title">{html.escape(card['title'])}</div>
              <div class="summary-card__value">{html.escape(card['value'])}</div>
              <div class="summary-card__hint">{html.escape(card['hint'])}</div>
            </section>
            """
        )

    section_html = []
    for index, (title, lines) in enumerate(sections, start=1):
        palette = _section_palette(title)
        items = "".join(
            f"<li>{html.escape(str(line))}</li>"
            for line in lines
        )
        section_html.append(
            f"""
            <section class="report-section" style="--accent: #{palette['accent']}; --fill: #{palette['fill']}; --border: #{palette['border']}; --text: #{palette['text']};">
              <div class="report-section__header">{_section_index_label(index)}、{html.escape(title)}</div>
              <ol class="report-section__list">{items}</ol>
            </section>
            """
        )

    metrics_text = "、".join(summary.get("metrics") or []) or "—"
    period_text = html.escape(str(meta.get("period_label") or "—"))
    college_text = html.escape(str(meta.get("college_name") or meta.get("college_id") or "—"))
    created_text = html.escape(str(meta.get("created_at") or "").replace("T", " ")[:19])

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <title>学生心理健康分析报告</title>
  <style>
    @page {{
      size: A4;
      margin: 20mm 16mm 18mm 16mm;
    }}
    body {{
      font-family: "Songti SC", "PingFang SC", "Hiragino Sans GB", serif;
      color: #0f172a;
      background: #f8fafc;
      font-size: 11pt;
      line-height: 1.65;
      margin: 0;
    }}
    .page {{
      background: #ffffff;
    }}
    .hero {{
      background: linear-gradient(135deg, #1e3a8a 0%, #334155 100%);
      color: #ffffff;
      border-radius: 16px;
      padding: 20px 24px;
      margin-bottom: 18px;
    }}
    .hero__title {{
      font-size: 22pt;
      font-weight: 700;
      margin: 0 0 8px 0;
    }}
    .hero__meta {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px 18px;
      font-size: 10pt;
      opacity: 0.95;
    }}
    .panel {{
      background: #f8fafc;
      border: 1px solid #dbeafe;
      border-radius: 14px;
      padding: 16px 18px;
      margin-bottom: 18px;
    }}
    .panel__title {{
      font-size: 14pt;
      font-weight: 700;
      margin: 0 0 12px 0;
      color: #0f172a;
    }}
    .summary-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 14px;
    }}
    .summary-card {{
      background: #ffffff;
      border: 1px solid #dbeafe;
      border-radius: 12px;
      padding: 14px 16px;
      box-shadow: inset 0 4px 0 #2563eb;
      min-height: 88px;
    }}
    .summary-card__title {{
      font-size: 9pt;
      color: #64748b;
      margin-bottom: 8px;
      font-weight: 700;
      letter-spacing: 0.04em;
    }}
    .summary-card__value {{
      font-size: 18pt;
      color: #0f172a;
      font-weight: 700;
      margin-bottom: 6px;
    }}
    .summary-card__hint {{
      font-size: 9pt;
      color: #64748b;
    }}
    .report-section {{
      border: 1px solid var(--border);
      background: #ffffff;
      border-radius: 14px;
      margin-bottom: 16px;
      overflow: hidden;
      break-inside: avoid;
      page-break-inside: avoid;
    }}
    .report-section__header {{
      background: var(--fill);
      color: var(--text);
      border-left: 8px solid var(--accent);
      font-size: 14pt;
      font-weight: 700;
      padding: 12px 16px;
    }}
    .report-section__list {{
      margin: 0;
      padding: 14px 20px 16px 34px;
    }}
    .report-section__list li {{
      margin: 0 0 6px 0;
    }}
    .footer-note {{
      margin-top: 10px;
      font-size: 8.5pt;
      color: #94a3b8;
      text-align: right;
    }}
  </style>
</head>
<body>
  <main class="page">
    <section class="hero">
      <h1 class="hero__title">学生心理健康分析报告</h1>
      <div class="hero__meta">
        <div>学院：{college_text}</div>
        <div>统计周期：{period_text}</div>
        <div>生成时间：{created_text}</div>
        <div>包含指标：{html.escape(metrics_text)}</div>
      </div>
    </section>

    <section class="panel">
      <h2 class="panel__title">摘要概览</h2>
      <div class="summary-grid">
        {''.join(card_html)}
      </div>
    </section>

    {''.join(section_html)}

    <div class="footer-note">学生心理健康分析与管理系统 · 自动生成</div>
  </main>
</body>
</html>
"""


def _section_palette(title: str) -> dict[str, str]:
    mapping = {
        REPORT_METRIC_RISK_DISTRIBUTION: {"fill": "EFF6FF", "accent": "2563EB", "border": "BFDBFE", "text": "1D4ED8"},
        REPORT_METRIC_ALERT_TREND: {"fill": "FFF7ED", "accent": "F97316", "border": "FED7AA", "text": "C2410C"},
        REPORT_METRIC_INTERVENTION_EFFECT: {"fill": "ECFEFF", "accent": "0F766E", "border": "A5F3FC", "text": "115E59"},
        REPORT_METRIC_QUESTIONNAIRE_SUBMISSION: {"fill": "F8FAFC", "accent": "475569", "border": "CBD5E1", "text": "334155"},
        REPORT_METRIC_RETEST_IMPROVEMENT: {"fill": "F0FDF4", "accent": "16A34A", "border": "BBF7D0", "text": "15803D"},
    }
    return mapping.get(title, {"fill": "F8FAFC", "accent": "334155", "border": "E2E8F0", "text": "0F172A"})


def _build_html_pdf(*, meta: dict, summary: dict, sections: list[tuple[str, list[str]]]) -> bytes | None:
    soffice = shutil.which("soffice")
    if not soffice:
        return None

    html_text = _render_report_html(meta=meta, summary=summary, sections=sections)
    try:
        with tempfile.TemporaryDirectory(prefix="psycare_report_html_") as tmpdir:
            tmp_path = Path(tmpdir)
            html_path = tmp_path / "report.html"
            pdf_path = tmp_path / "report.pdf"
            html_path.write_text(html_text, encoding="utf-8")

            result = subprocess.run(
                [
                    soffice,
                    "--headless",
                    "--nologo",
                    "--nolockcheck",
                    "--nodefault",
                    "--convert-to",
                    "pdf",
                    "--outdir",
                    str(tmp_path),
                    str(html_path),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            if result.returncode != 0 or not pdf_path.exists():
                return None
            return pdf_path.read_bytes()
    except Exception:
        return None


def _fitz_python_executable() -> str | None:
    candidates = [
        "/opt/homebrew/bin/python3",
        "/usr/local/bin/python3",
        "/usr/bin/python3",
    ]
    for candidate in candidates:
        if not Path(candidate).exists():
            continue
        try:
            result = subprocess.run(
                [candidate, "-c", "import fitz"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            if result.returncode == 0:
                return candidate
        except Exception:
            continue
    return None


def _build_fitz_pdf_via_subprocess(*, meta: dict, summary: dict, sections: list[tuple[str, list[str]]]) -> bytes | None:
    python_bin = _fitz_python_executable()
    script_path = Path(__file__).resolve().parent / "pdf_fitz_renderer.py"
    if not python_bin or not script_path.exists():
        return None

    payload = {
        "meta": meta,
        "summary": summary,
        "sections": [{"title": title, "lines": lines} for title, lines in sections],
    }
    try:
        with tempfile.TemporaryDirectory(prefix="psycare_report_fitz_") as tmpdir:
            tmp_path = Path(tmpdir)
            json_path = tmp_path / "payload.json"
            pdf_path = tmp_path / "report.pdf"
            json_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

            result = subprocess.run(
                [python_bin, str(script_path), str(json_path), str(pdf_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            if result.returncode != 0 or not pdf_path.exists():
                return None
            return pdf_path.read_bytes()
    except Exception:
        return None


def _build_styled_report_pdf(*, meta: dict, summary: dict, sections: list[tuple[str, list[str]]]) -> bytes:
    page_width = 595
    page_height = 842
    margin_x = 42
    top_y = 804
    bottom_y = 46
    content_width = page_width - margin_x * 2
    page_buffers: list[list[str]] = []
    current_page: list[str] | None = None
    cursor_y = top_y

    def begin_page(*, first: bool):
        nonlocal current_page, cursor_y
        current_page = []
        page_buffers.append(current_page)
        if first:
            current_page.append(_pdf_rect(margin_x, 730, content_width, 74, fill="1E3A8A"))
            current_page.append(_pdf_rect(margin_x, 654, content_width, 62, fill="EFF6FF", stroke="BFDBFE", line_width=0.8))
            current_page.append(_pdf_text("学生心理健康分析报告", margin_x + 18, 776, size=22, color="FFFFFF"))
            current_page.append(
                _pdf_text(
                    f"学院：{meta.get('college_name') or meta.get('college_id')}    统计周期：{meta.get('period_label') or '—'}",
                    margin_x + 18,
                    692,
                    size=11,
                    color="0F172A",
                )
            )
            current_page.append(
                _pdf_text(
                    f"生成时间：{str(meta.get('created_at') or '').replace('T', ' ')[:19]}    包含指标：{'、'.join(summary.get('metrics') or []) or '—'}",
                    margin_x + 18,
                    672,
                    size=10,
                    color="334155",
                )
            )
            cursor_y = 628
        else:
            current_page.append(_pdf_text("学生心理健康分析报告", margin_x, 800, size=14, color="0F172A"))
            current_page.append(
                _pdf_text(
                    str(meta.get("period_label") or ""),
                    margin_x,
                    782,
                    size=9.5,
                    color="64748B",
                )
            )
            current_page.append(_pdf_rect(margin_x, 770, content_width, 1.2, fill="E2E8F0"))
            cursor_y = 748

    def ensure_space(height: float):
        nonlocal cursor_y
        if current_page is None:
            begin_page(first=True)
            return
        if cursor_y - height < bottom_y:
            begin_page(first=False)

    def add_summary_cards(cards: list[dict[str, str]]):
        nonlocal cursor_y
        if not cards:
            return
        ensure_space(36)
        current_page.append(_pdf_text("摘要概览", margin_x, cursor_y, size=15, color="0F172A"))
        cursor_y -= 22

        card_gap = 14
        card_width = (content_width - card_gap) / 2
        card_height = 82
        row_gap = 12
        for index in range(0, len(cards), 2):
            row_cards = cards[index:index + 2]
            ensure_space(card_height + row_gap)
            row_top = cursor_y
            for col, card in enumerate(row_cards):
                x = margin_x + col * (card_width + card_gap)
                y = row_top - card_height
                current_page.append(_pdf_rect(x, y, card_width, card_height, fill="FFFFFF", stroke="E2E8F0", line_width=0.8))
                current_page.append(_pdf_rect(x, y + card_height - 6, card_width, 6, fill="2563EB"))
                current_page.append(_pdf_text(card["title"], x + 16, y + card_height - 24, size=10, color="64748B"))
                current_page.append(_pdf_text(card["value"], x + 16, y + card_height - 50, size=18, color="0F172A"))
                hint_lines = _wrap_text(card["hint"], width=22)
                hint_y = y + 14
                for hint_index, hint in enumerate(hint_lines[:2]):
                    current_page.append(_pdf_text(hint, x + 16, hint_y - hint_index * 12, size=8.5, color="64748B"))
            cursor_y = row_top - card_height - row_gap

        cursor_y -= 4

    def add_section(title: str, lines: list[str], index: int):
        nonlocal cursor_y
        palette = _section_palette(title)
        wrapped_lines: list[str] = []
        for line in lines:
            parts = _wrap_text(line, width=46)
            if parts:
                wrapped_lines.extend(parts)
            else:
                wrapped_lines.append("")
        body_line_height = 16
        block_height = 48 + len(wrapped_lines) * body_line_height + 20
        ensure_space(block_height + 12)

        block_top = cursor_y
        block_bottom = block_top - block_height
        current_page.append(
            _pdf_rect(margin_x, block_bottom, content_width, block_height, fill="FFFFFF", stroke=palette["border"], line_width=0.9)
        )
        current_page.append(_pdf_rect(margin_x, block_top - 38, content_width, 38, fill=palette["fill"]))
        current_page.append(_pdf_rect(margin_x, block_top - 38, 8, 38, fill=palette["accent"]))
        current_page.append(_pdf_text(f"{_section_index_label(index)}、{title}", margin_x + 18, block_top - 24, size=13, color=palette["text"]))

        line_y = block_top - 60
        for line in wrapped_lines:
            current_page.append(_pdf_text(line, margin_x + 18, line_y, size=10.5, color="1F2937"))
            line_y -= body_line_height
        cursor_y = block_bottom - 12

    begin_page(first=True)
    add_summary_cards(_summary_cards_from_summary(summary))
    for index, (title, section_lines) in enumerate(sections, start=1):
        add_section(title, section_lines, index)

    total_pages = len(page_buffers)
    page_contents: list[str] = []
    for page_index, page in enumerate(page_buffers, start=1):
        page.append(_pdf_text(f"第 {page_index} / {total_pages} 页", 500, 24, size=9, color="94A3B8"))
        page_contents.append("".join(page))

    return _build_pdf_pages(page_contents)


def _build_text_pdf(lines: list[str]) -> bytes | None:
    content = "\n".join(str(line or "") for line in lines).strip() + "\n"
    try:
        with tempfile.TemporaryDirectory(prefix="psycare_report_") as tmpdir:
            tmp_path = Path(tmpdir)
            txt_path = tmp_path / "report.txt"
            pdf_path = tmp_path / "report.pdf"
            txt_path.write_text(content, encoding="utf-8")

            env = os.environ.copy()
            env.setdefault("LANG", "zh_CN.UTF8")
            env.setdefault("CHARSET", "utf-8")
            env.setdefault("LC_CTYPE", "zh_CN.UTF8")

            result = subprocess.run(
                [
                    "/usr/sbin/cupsfilter",
                    "-m",
                    "application/pdf",
                    "-t",
                    "学生心理健康分析报告",
                    "-o",
                    "cpi=10",
                    "-o",
                    "lpi=6",
                    "-o",
                    "page-left=54",
                    "-o",
                    "page-right=54",
                    "-o",
                    "page-top=54",
                    "-o",
                    "page-bottom=54",
                    str(txt_path),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                env=env,
            )
            if result.returncode != 0:
                return None

            pdf_bytes = result.stdout
            if not pdf_bytes:
                if pdf_path.exists():
                    pdf_bytes = pdf_path.read_bytes()
            return pdf_bytes or None
    except Exception:
        return None


def _build_report_pdf(*, meta: dict, summary: dict, sections: list[tuple[str, list[str]]], lines: list[str]) -> bytes:
    try:
        return _build_styled_report_pdf(meta=meta, summary=summary, sections=sections)
    except Exception:
        pdf_bytes = _build_text_pdf(lines)
        if pdf_bytes:
            return pdf_bytes
        return _build_cjk_pdf(lines)


def _dimension_label(key: str) -> str:
    return DIMENSION_LABELS.get(key, key)


def _latest_plan_by_student(queryset):
    latest = {}
    for plan in queryset.order_by("student_id", "-updated_at", "-id"):
        latest.setdefault(plan.student_id, plan)
    return latest


def _section_index_label(index: int) -> str:
    labels = ["一", "二", "三", "四", "五", "六", "七", "八", "九", "十"]
    if 1 <= index <= len(labels):
        return labels[index - 1]
    return str(index)


class MonthlyReportView(APIView):
    permission_classes = [IsAuthenticated, IsCollegeAdminOrSysAdmin]

    def post(self, request):
        user = request.user
        normalized = _normalize_period(
            month=str(request.data.get("month") or "").strip() or None,
            month_start=str(request.data.get("month_start") or "").strip() or None,
            month_end=str(request.data.get("month_end") or "").strip() or None,
            month_range=request.data.get("month_range"),
        )
        if not normalized:
            return Response(
                {"detail": "统计月份格式应为 YYYY-MM，范围需满足开始月份不晚于结束月份"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        start_month, end_month, start, end, month_count = normalized
        metrics, invalid_metrics = _normalize_metrics(request.data.get("metrics"))
        if invalid_metrics:
            return Response(
                {"detail": f"存在无效指标：{', '.join(invalid_metrics)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not metrics:
            return Response(
                {"detail": "请至少选择一个报表指标"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        out_format = str(request.data.get("format") or "json").lower().strip()

        college_id = request.data.get("college_id")
        if getattr(user, "is_college_admin", False):
            if not user.college_id:
                return Response({"detail": "当前账号未绑定学院"}, status=status.HTTP_400_BAD_REQUEST)
            college_id = user.college_id
        elif not college_id:
            return Response({"detail": "college_id 必填"}, status=status.HTTP_400_BAD_REQUEST)

        from apps.accounts.models import College
        from apps.assessments.models import AssessmentResult, RiskAlert
        from apps.interventions.models import InterventionPlan
        from apps.surveys.models import Questionnaire, QuestionnaireResponse, QuestionnaireRetestTask

        college = College.objects.filter(id=college_id).first()
        if not college:
            return Response({"detail": "学院不存在"}, status=status.HTTP_404_NOT_FOUND)

        assess_qs = AssessmentResult.objects.filter(
            created_at__gte=start,
            created_at__lt=end,
            response__student__college_id=college_id,
        ).select_related("response", "response__student", "response__questionnaire")
        alert_qs = RiskAlert.objects.filter(
            created_at__gte=start,
            created_at__lt=end,
            student__college_id=college_id,
        )
        plan_qs = InterventionPlan.objects.filter(
            created_at__gte=start,
            created_at__lt=end,
            student__college_id=college_id,
        ).select_related("student", "counselor", "assessment")
        plan_until_end_qs = InterventionPlan.objects.filter(
            created_at__lt=end,
            student__college_id=college_id,
        ).select_related("student", "counselor", "assessment")
        resp_qs = QuestionnaireResponse.objects.filter(
            submitted_at__gte=start,
            submitted_at__lt=end,
            student__college_id=college_id,
        )
        q_qs = Questionnaire.objects.filter(target_college_id=college_id)
        retest_qs = QuestionnaireRetestTask.objects.filter(
            completed_at__gte=start,
            completed_at__lt=end,
            status=QuestionnaireRetestTask.Status.COMPLETED,
            student__college_id=college_id,
        ).select_related("student", "questionnaire")

        assess_count = assess_qs.count()
        risk_dist = {row["risk_level"]: int(row["c"]) for row in assess_qs.values("risk_level").annotate(c=Count("id"))}
        low_count = int(risk_dist.get("low", 0))
        medium_count = int(risk_dist.get("medium", 0))
        high_count = int(risk_dist.get("high", 0))

        dim_agg: dict[str, dict[str, float]] = {}
        for assessment in assess_qs:
            for key, value in (assessment.dimension_scores or {}).items():
                bucket = dim_agg.setdefault(key, {"sum": 0.0, "count": 0})
                bucket["sum"] += float(value or 0)
                bucket["count"] += 1
        top_dimensions = sorted(
            [
                {
                    "key": key,
                    "name": _dimension_label(key),
                    "avg_score": round(bucket["sum"] / bucket["count"], 2) if bucket["count"] else 0.0,
                    "sample_count": int(bucket["count"]),
                }
                for key, bucket in dim_agg.items()
            ],
            key=lambda item: item["avg_score"],
            reverse=True,
        )[:3]

        high_risk_student_ids = set(
            assess_qs.filter(risk_level="high").values_list("response__student_id", flat=True).distinct()
        )
        latest_plan_by_student = _latest_plan_by_student(plan_until_end_qs.filter(student_id__in=high_risk_student_ids))
        intervention_status_counts = {"draft": 0, "sent": 0, "in_progress": 0, "done": 0}
        counselor_involved_count = 0
        for plan in latest_plan_by_student.values():
            intervention_status_counts[plan.status] = intervention_status_counts.get(plan.status, 0) + 1
            if plan.counselor_id:
                counselor_involved_count += 1

        retest_completed_count = retest_qs.count()
        baseline_high_retest_count = 0
        improved_count = 0
        improved_to_safe_count = 0
        for task in retest_qs:
            baseline = (
                AssessmentResult.objects.filter(
                    response__student=task.student,
                    response__questionnaire=task.questionnaire,
                    created_at__lt=task.created_at,
                )
                .order_by("-created_at")
                .first()
            )
            if not baseline or baseline.risk_level != AssessmentResult.RiskLevel.HIGH:
                continue
            baseline_high_retest_count += 1
            retest_result = (
                AssessmentResult.objects.filter(
                    response__student=task.student,
                    response__questionnaire=task.questionnaire,
                    created_at__gte=task.created_at,
                )
                .order_by("created_at")
                .first()
            )
            if not retest_result:
                continue
            if retest_result.risk_level in {AssessmentResult.RiskLevel.MEDIUM, AssessmentResult.RiskLevel.LOW}:
                improved_count += 1
            if retest_result.risk_level == AssessmentResult.RiskLevel.LOW:
                improved_to_safe_count += 1

        previous_start_idx = _month_index(start_month) - month_count
        previous_end_idx = _month_index(start_month) - 1
        previous_assess_count = 0
        previous_high_count = 0
        previous_alert_count = 0
        previous_high_unack_count = 0
        previous_period_label = None
        if previous_start_idx is not None and previous_end_idx is not None:
            previous_start_month = _index_to_month(previous_start_idx)
            previous_end_month = _index_to_month(previous_end_idx)
            previous_bounds = _normalize_period(None, previous_start_month, previous_end_month, None)
            if previous_bounds:
                _, _, previous_start, previous_end, _ = previous_bounds
                previous_period_label = _period_label(previous_start_month, previous_end_month)
                previous_assess_qs = AssessmentResult.objects.filter(
                    created_at__gte=previous_start,
                    created_at__lt=previous_end,
                    response__student__college_id=college_id,
                )
                previous_assess_count = previous_assess_qs.count()
                previous_high_count = previous_assess_qs.filter(risk_level="high").count()
                previous_alert_qs = RiskAlert.objects.filter(
                    created_at__gte=previous_start,
                    created_at__lt=previous_end,
                    student__college_id=college_id,
                )
                previous_alert_count = previous_alert_qs.count()
                previous_high_unack_count = previous_alert_qs.filter(
                    level="high",
                    is_acknowledged=False,
                ).count()

        by_status = {row["status"]: int(row["c"]) for row in plan_qs.values("status").annotate(c=Count("id"))}

        summary = {
            "metrics": metrics,
            "period": {
                "month_start": start_month,
                "month_end": end_month,
                "label": _period_label(start_month, end_month),
                "month_count": month_count,
            },
        }
        if REPORT_METRIC_RISK_DISTRIBUTION in metrics:
            summary["assessments"] = {
                "count": assess_count,
                "avg_score": round(float(assess_qs.aggregate(v=Avg("avg_score"))["v"] or 0.0), 2),
                "risk_distribution": {
                    "low": low_count,
                    "medium": medium_count,
                    "high": high_count,
                    "low_ratio": _percent(low_count, assess_count),
                    "medium_ratio": _percent(medium_count, assess_count),
                    "high_ratio": _percent(high_count, assess_count),
                },
                "top_dimensions": top_dimensions,
            }
            summary["comparisons"] = {
                "previous_period_label": previous_period_label,
                "assessment_change_pct": _percent_change(assess_count, previous_assess_count),
                "high_risk_change_pct": _percent_change(high_count, previous_high_count),
            }

        if REPORT_METRIC_ALERT_TREND in metrics:
            current_alert_count = alert_qs.count()
            current_unack_count = alert_qs.filter(is_acknowledged=False).count()
            current_high_unack_count = alert_qs.filter(level="high", is_acknowledged=False).count()
            summary["alerts"] = {
                "count": current_alert_count,
                "unack_count": current_unack_count,
                "high_unack_count": current_high_unack_count,
                "trend": {
                    "previous_period_label": previous_period_label,
                    "alert_change_pct": _percent_change(current_alert_count, previous_alert_count),
                    "high_unack_change_pct": _percent_change(
                        current_high_unack_count,
                        previous_high_unack_count,
                    ),
                },
            }

        if REPORT_METRIC_INTERVENTION_EFFECT in metrics:
            summary["interventions"] = {
                "count": plan_qs.count(),
                "by_status": {key: int(value) for key, value in by_status.items()},
                "done_count": plan_qs.filter(status="done").count(),
                "high_risk_student_count": len(high_risk_student_ids),
                "intervened_high_risk_student_count": len(latest_plan_by_student),
                "intervention_rate": _percent(len(latest_plan_by_student), len(high_risk_student_ids)),
                "counselor_involved_count": counselor_involved_count,
                "counselor_involved_rate": _percent(counselor_involved_count, len(high_risk_student_ids)),
                "feedback_status_distribution": {
                    "draft": intervention_status_counts.get("draft", 0),
                    "sent": intervention_status_counts.get("sent", 0),
                    "in_progress": intervention_status_counts.get("in_progress", 0),
                    "done": intervention_status_counts.get("done", 0),
                    "no_intervention": max(len(high_risk_student_ids) - len(latest_plan_by_student), 0),
                },
            }

        if REPORT_METRIC_QUESTIONNAIRE_SUBMISSION in metrics:
            summary["questionnaires"] = {
                "responses_count": resp_qs.count(),
                "questionnaires_count": q_qs.count(),
            }

        if REPORT_METRIC_RETEST_IMPROVEMENT in metrics:
            summary["retest"] = {
                "completed_task_count": retest_completed_count,
                "baseline_high_risk_count": baseline_high_retest_count,
                "improved_count": improved_count,
                "improved_to_safe_count": improved_to_safe_count,
                "improvement_rate": _percent(improved_to_safe_count, baseline_high_retest_count),
            }

        created_at = timezone.now().isoformat()
        meta = {
            "college_id": int(college_id),
            "college_name": college.name,
            "month": start_month if start_month == end_month else None,
            "month_start": start_month,
            "month_end": end_month,
            "period_label": _period_label(start_month, end_month),
            "created_at": created_at,
        }

        timestamp = timezone.now().strftime("%Y%m%d_%H%M%S_%f")
        file_period = (
            start_month.replace("-", "")
            if start_month == end_month
            else f"{start_month.replace('-', '')}_{end_month.replace('-', '')}"
        )
        name = f"college_{college_id}_monthly_{file_period}_{timestamp}.json"
        out_path = _report_dir() / name
        out_path.write_text(
            json.dumps({"meta": meta, "summary": summary}, ensure_ascii=False, indent=2, cls=DjangoJSONEncoder),
            encoding="utf-8",
        )

        pdf_name = None
        if out_format == "pdf":
            pdf_name = name.replace(".json", ".pdf")
            pdf_path = _report_dir() / pdf_name
            sections: list[tuple[str, list[str]]] = []

            if REPORT_METRIC_RISK_DISTRIBUTION in metrics and "assessments" in summary:
                assessments = summary["assessments"]
                risk_distribution = assessments["risk_distribution"]
                risk_lines = [
                    f"1. 评估样本数：{assessments['count']} 份，平均分：{assessments['avg_score']:.2f}",
                    (
                        f"2. 风险等级分布：低风险 {risk_distribution['low']} 人（{_format_percent(risk_distribution['low_ratio'])}），"
                        f"中风险 {risk_distribution['medium']} 人（{_format_percent(risk_distribution['medium_ratio'])}），"
                        f"高风险 {risk_distribution['high']} 人（{_format_percent(risk_distribution['high_ratio'])}）"
                    ),
                ]
                if assessments["top_dimensions"]:
                    for index, item in enumerate(assessments["top_dimensions"], start=1):
                        risk_lines.append(
                            f"{index + 2}. 维度表现 Top{index}：{item['name']}，平均 {item['avg_score']:.2f} 分，涉及 {item['sample_count']} 份评估"
                        )
                else:
                    risk_lines.append("3. 维度表现前三：暂无维度统计数据。")

                comparison = summary.get("comparisons") or {}
                if comparison.get("previous_period_label"):
                    assessment_change = comparison.get("assessment_change_pct")
                    high_risk_change = comparison.get("high_risk_change_pct")
                    risk_lines.append(
                        f"{len(risk_lines) + 1}. 与上一统计周期（{comparison['previous_period_label']}）相比："
                        f"评估样本变化 { _format_percent(assessment_change) if assessment_change is not None else '基期为 0，暂不计算' }，"
                        f"高风险人数变化 { _format_percent(high_risk_change) if high_risk_change is not None else '基期为 0，暂不计算' }"
                    )
                sections.append((REPORT_METRIC_RISK_DISTRIBUTION, risk_lines))

            if REPORT_METRIC_ALERT_TREND in metrics and "alerts" in summary:
                alerts = summary["alerts"]
                alert_lines = [
                    f"1. 预警总数：{alerts['count']} 条",
                    f"2. 未处理预警：{alerts['unack_count']} 条",
                    f"3. 高风险未处理预警：{alerts['high_unack_count']} 条",
                ]
                trend = alerts.get("trend") or {}
                if trend.get("previous_period_label"):
                    alert_change = trend.get("alert_change_pct")
                    high_unack_change = trend.get("high_unack_change_pct")
                    alert_lines.append(
                        f"4. 与上一统计周期（{trend['previous_period_label']}）相比："
                        f"预警总数变化 { _format_percent(alert_change) if alert_change is not None else '基期为 0，暂不计算' }，"
                        f"高风险未处理预警变化 { _format_percent(high_unack_change) if high_unack_change is not None else '基期为 0，暂不计算' }"
                    )
                sections.append((REPORT_METRIC_ALERT_TREND, alert_lines))

            if REPORT_METRIC_INTERVENTION_EFFECT in metrics and "interventions" in summary:
                interventions = summary["interventions"]
                sections.append(
                    (
                        REPORT_METRIC_INTERVENTION_EFFECT,
                        [
                            f"1. 高风险学生人数：{interventions['high_risk_student_count']} 人",
                            (
                                f"2. 已被干预介入：{interventions['intervened_high_risk_student_count']} 人，"
                                f"介入率 {_format_percent(interventions['intervention_rate'])}"
                            ),
                            (
                                f"3. 辅导员已介入人数：{interventions['counselor_involved_count']} 人，"
                                f"介入覆盖率 {_format_percent(interventions['counselor_involved_rate'])}"
                            ),
                            (
                                f"4. 干预进度：进行中 {interventions['feedback_status_distribution']['in_progress']} 人，"
                                f"已完成 {interventions['feedback_status_distribution']['done']} 人，"
                                f"已推送 {interventions['feedback_status_distribution']['sent']} 人，"
                                f"未介入 {interventions['feedback_status_distribution']['no_intervention']} 人"
                            ),
                        ],
                    )
                )

            if REPORT_METRIC_QUESTIONNAIRE_SUBMISSION in metrics and "questionnaires" in summary:
                questionnaires = summary["questionnaires"]
                sections.append(
                    (
                        REPORT_METRIC_QUESTIONNAIRE_SUBMISSION,
                        [
                            f"1. 统计范围内问卷数：{questionnaires['questionnaires_count']} 份",
                            f"2. 统计范围内作答数：{questionnaires['responses_count']} 次",
                        ],
                    )
                )

            if REPORT_METRIC_RETEST_IMPROVEMENT in metrics and "retest" in summary:
                retest = summary["retest"]
                sections.append(
                    (
                        REPORT_METRIC_RETEST_IMPROVEMENT,
                        [
                            f"1. 已完成复测任务：{retest['completed_task_count']} 条",
                            f"2. 基线为高风险的复测人数：{retest['baseline_high_risk_count']} 人",
                            f"3. 风险下降人数：{retest['improved_count']} 人",
                            f"4. 恢复为安全人数：{retest['improved_to_safe_count']} 人",
                            f"5. 改善率：{_format_percent(retest['improvement_rate'])}",
                        ],
                    )
                )

            lines = _build_report_text_lines(meta=meta, summary=summary, sections=sections)
            pdf_path.write_bytes(
                _build_report_pdf(meta=meta, summary=summary, sections=sections, lines=lines)
            )

        return Response({"name": name, "pdf_name": pdf_name, "meta": meta, "summary": summary})


class ListReportsView(APIView):
    permission_classes = [IsAuthenticated, IsCollegeAdminOrSysAdmin]

    def get(self, request):
        user = request.user
        college_id = request.query_params.get("college_id")
        if getattr(user, "is_college_admin", False):
            if not user.college_id:
                return Response({"detail": "当前账号未绑定学院"}, status=status.HTTP_400_BAD_REQUEST)
            college_id = str(user.college_id)

        results = []
        for path in sorted(_report_dir().glob("*.json"), reverse=True):
            if college_id and f"college_{college_id}_" not in path.name:
                continue
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
                meta = raw.get("meta") or {}
                summary = raw.get("summary") or {}
                pdf_path = path.with_suffix(".pdf")
                results.append(
                    {
                        "name": path.name,
                        "pdf_name": pdf_path.name if pdf_path.exists() else None,
                        "meta": meta,
                        "summary": summary,
                    }
                )
            except Exception:
                continue

        results.sort(key=lambda item: str((item.get("meta") or {}).get("created_at") or item["name"]), reverse=True)
        return Response({"results": results})


class DownloadReportView(APIView):
    permission_classes = [IsAuthenticated, IsCollegeAdminOrSysAdmin]

    def get(self, request):
        user = request.user
        name = request.query_params.get("name")
        if not name:
            return Response({"detail": "name 必填"}, status=status.HTTP_400_BAD_REQUEST)
        path = _report_dir() / str(name)
        if not path.exists() or not path.is_file():
            return Response({"detail": "文件不存在"}, status=status.HTTP_404_NOT_FOUND)

        if getattr(user, "is_college_admin", False) and user.college_id:
            if f"college_{user.college_id}_" not in path.name:
                return Response({"detail": "无权限"}, status=status.HTTP_403_FORBIDDEN)

        return FileResponse(open(path, "rb"), as_attachment=True, filename=path.name)


class CollegeRiskOverviewView(APIView):
    permission_classes = [IsAuthenticated, IsSysAdmin]

    def get(self, request):
        days = int(str(request.query_params.get("days") or "90"))
        days = max(7, min(days, 365))
        since = timezone.now() - timedelta(days=days)

        from apps.accounts.models import College
        from apps.assessments.models import AssessmentResult, RiskAlert
        from apps.interventions.models import InterventionPlan

        colleges = list(College.objects.all().order_by("id"))
        ids = [college.id for college in colleges]
        if not ids:
            return Response({"days": days, "since": since.isoformat(), "items": []})

        assess_qs = AssessmentResult.objects.filter(
            created_at__gte=since,
            response__student__college_id__in=ids,
        )
        assess_total = {
            row["response__student__college_id"]: int(row["c"])
            for row in assess_qs.values("response__student__college_id").annotate(c=Count("id"))
        }
        assess_high = {
            row["response__student__college_id"]: int(row["c"])
            for row in assess_qs.filter(risk_level="high")
            .values("response__student__college_id")
            .annotate(c=Count("id"))
        }
        alert_unack = {
            row["student__college_id"]: int(row["c"])
            for row in RiskAlert.objects.filter(
                created_at__gte=since,
                student__college_id__in=ids,
                is_acknowledged=False,
            )
            .values("student__college_id")
            .annotate(c=Count("id"))
        }
        plan_open = {
            row["student__college_id"]: int(row["c"])
            for row in InterventionPlan.objects.filter(
                created_at__gte=since,
                student__college_id__in=ids,
            )
            .exclude(status="done")
            .values("student__college_id")
            .annotate(c=Count("id"))
        }

        items = []
        for college in colleges:
            total = int(assess_total.get(college.id, 0))
            high = int(assess_high.get(college.id, 0))
            high_rate = (high / total) if total else 0.0
            items.append(
                {
                    "college_id": college.id,
                    "college_name": college.name,
                    "assessments_count": total,
                    "high_risk_count": high,
                    "high_risk_rate": round(high_rate, 4),
                    "unack_alert_count": int(alert_unack.get(college.id, 0)),
                    "open_intervention_count": int(plan_open.get(college.id, 0)),
                }
            )

        items.sort(key=lambda item: (-item["high_risk_rate"], -item["high_risk_count"], item["college_id"]))
        return Response({"days": days, "since": since.isoformat(), "items": items})
