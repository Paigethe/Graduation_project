from __future__ import annotations

import json
import sys
from pathlib import Path

import fitz

PAGE_WIDTH = 595
PAGE_HEIGHT = 842
MARGIN_X = 42
TOP_Y = 804
BOTTOM_Y = 40
CONTENT_WIDTH = PAGE_WIDTH - MARGIN_X * 2

HEADING_FONT_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Songti.ttc",
    "/System/Library/Fonts/STHeiti Medium.ttc",
    "/System/Library/Fonts/STHeiti Light.ttc",
]
BODY_FONT_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Songti.ttc",
    "/System/Library/Fonts/STHeiti Light.ttc",
    "/System/Library/Fonts/STHeiti Medium.ttc",
]


def choose_font(candidates: list[str]) -> str:
    for item in candidates:
        if Path(item).exists():
            return item
    raise FileNotFoundError(f"No font available from: {candidates}")


HEADING_FONT_PATH = choose_font(HEADING_FONT_CANDIDATES)
BODY_FONT_PATH = choose_font(BODY_FONT_CANDIDATES)
HEADING_FONT = fitz.Font(fontfile=HEADING_FONT_PATH)
BODY_FONT = fitz.Font(fontfile=BODY_FONT_PATH)


def color(hex_color: str) -> tuple[float, float, float]:
    raw = str(hex_color or "").strip().lstrip("#")
    if len(raw) != 6:
        return (0.0, 0.0, 0.0)
    return tuple(int(raw[index:index + 2], 16) / 255 for index in (0, 2, 4))


def wrap_text(text: str, *, font: fitz.Font, font_size: float, max_width: float) -> list[str]:
    raw = str(text or "")
    if not raw:
        return [""]
    lines: list[str] = []
    for paragraph in raw.splitlines() or [""]:
        if not paragraph:
            lines.append("")
            continue
        current = ""
        for char in paragraph:
            candidate = current + char
            if current and font.text_length(candidate, fontsize=font_size) > max_width:
                lines.append(current)
                current = char
            else:
                current = candidate
        if current:
            lines.append(current)
    return lines or [""]


def insert_text(
    page: fitz.Page,
    x: float,
    y: float,
    text: str,
    *,
    fontname: str,
    fontsize: float,
    fill: str,
):
    page.insert_text(
        fitz.Point(x, y),
        str(text),
        fontname=fontname,
        fontsize=fontsize,
        color=color(fill),
        overlay=True,
    )


def draw_rect(
    page: fitz.Page,
    x: float,
    y: float,
    width: float,
    height: float,
    *,
    fill: str | None = None,
    stroke: str | None = None,
    radius: float | None = None,
    width_pt: float = 1.0,
):
    rect = fitz.Rect(x, y, x + width, y + height)
    kwargs = {}
    if fill:
        kwargs["fill"] = color(fill)
    if stroke:
        kwargs["color"] = color(stroke)
    if radius and radius > 0 and hasattr(page, "draw_round_rect"):
        page.draw_round_rect(rect, radius, **kwargs, width=width_pt, overlay=True)
        return
    page.draw_rect(rect, **kwargs, width=width_pt, overlay=True)


def section_palette(title: str) -> dict[str, str]:
    mapping = {
        "风险分布": {"fill": "EFF6FF", "accent": "2563EB", "border": "BFDBFE", "text": "1D4ED8"},
        "预警趋势": {"fill": "FFF7ED", "accent": "F97316", "border": "FED7AA", "text": "C2410C"},
        "干预效果": {"fill": "ECFEFF", "accent": "0F766E", "border": "A5F3FC", "text": "115E59"},
        "问卷提交": {"fill": "F8FAFC", "accent": "475569", "border": "CBD5E1", "text": "334155"},
        "复测改善": {"fill": "F0FDF4", "accent": "16A34A", "border": "BBF7D0", "text": "15803D"},
    }
    return mapping.get(title, {"fill": "F8FAFC", "accent": "334155", "border": "E2E8F0", "text": "0F172A"})


def section_index_label(index: int) -> str:
    labels = ["一", "二", "三", "四", "五", "六", "七", "八", "九", "十"]
    if 1 <= index <= len(labels):
        return labels[index - 1]
    return str(index)


class PdfCanvas:
    def __init__(self, meta: dict, summary: dict):
        self.meta = meta
        self.summary = summary
        self.doc = fitz.open()
        self.page_no = 0
        self.page = None
        self.cursor_y = TOP_Y

    def new_page(self, *, first: bool):
        self.page_no += 1
        self.page = self.doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
        self.page.insert_font(fontname="heading", fontfile=HEADING_FONT_PATH)
        self.page.insert_font(fontname="body", fontfile=BODY_FONT_PATH)

        draw_rect(self.page, 0, 0, PAGE_WIDTH, PAGE_HEIGHT, fill="F8FAFC")
        draw_rect(self.page, 16, 16, PAGE_WIDTH - 32, PAGE_HEIGHT - 32, fill="FFFFFF", radius=18)

        if first:
            draw_rect(self.page, MARGIN_X, 62, CONTENT_WIDTH, 80, fill="1E3A8A", radius=16)
            insert_text(self.page, MARGIN_X + 18, 112, "学生心理健康分析报告", fontname="heading", fontsize=26, fill="FFFFFF")

            draw_rect(self.page, MARGIN_X, 156, CONTENT_WIDTH, 84, fill="F8FAFC", stroke="DBEAFE", radius=12, width_pt=1.0)
            meta_lines = [
                f"学院：{self.meta.get('college_name') or self.meta.get('college_id')}",
                f"统计周期：{self.meta.get('period_label') or '—'}",
                f"生成时间：{str(self.meta.get('created_at') or '').replace('T', ' ')[:19]}",
                f"包含指标：{'、'.join(self.summary.get('metrics') or []) or '—'}",
            ]
            y = 184
            for line in meta_lines:
                insert_text(self.page, MARGIN_X + 18, y, line, fontname="body", fontsize=10.5, fill="334155")
                y += 18
            self.cursor_y = 276
        else:
            insert_text(self.page, MARGIN_X, 66, "学生心理健康分析报告", fontname="heading", fontsize=15, fill="0F172A")
            insert_text(self.page, MARGIN_X, 88, str(self.meta.get("period_label") or ""), fontname="body", fontsize=9.5, fill="64748B")
            self.page.draw_line(fitz.Point(MARGIN_X, 102), fitz.Point(MARGIN_X + CONTENT_WIDTH, 102), color=color("E2E8F0"), width=1)
            self.cursor_y = 132

    def ensure_space(self, height: float):
        if self.page is None:
            self.new_page(first=True)
            return
        if self.cursor_y + height > PAGE_HEIGHT - BOTTOM_Y:
            self.new_page(first=False)

    def draw_summary_cards(self, cards: list[dict[str, str]]):
        if not cards:
            return
        self.ensure_space(40)
        insert_text(self.page, MARGIN_X, self.cursor_y, "摘要概览", fontname="heading", fontsize=16, fill="0F172A")
        self.cursor_y += 18

        card_gap = 14
        card_width = (CONTENT_WIDTH - card_gap) / 2
        card_height = 92
        row_gap = 14
        for index in range(0, len(cards), 2):
            row_cards = cards[index:index + 2]
            self.ensure_space(card_height + row_gap + 10)
            row_top = self.cursor_y + 8
            for col, card in enumerate(row_cards):
                x = MARGIN_X + col * (card_width + card_gap)
                y = row_top
                draw_rect(self.page, x, y, card_width, card_height, fill="FFFFFF", stroke="DBEAFE", radius=12, width_pt=1.0)
                draw_rect(self.page, x, y, card_width, 6, fill="2563EB", radius=12)
                insert_text(self.page, x + 14, y + 26, card["title"], fontname="heading", fontsize=10, fill="64748B")
                insert_text(self.page, x + 14, y + 54, card["value"], fontname="heading", fontsize=18, fill="0F172A")
                hint_lines = wrap_text(card["hint"], font=BODY_FONT, font_size=9, max_width=card_width - 28)
                hint_y = y + 74
                for hint in hint_lines[:2]:
                    insert_text(self.page, x + 14, hint_y, hint, fontname="body", fontsize=8.6, fill="64748B")
                    hint_y += 12
            self.cursor_y = row_top + card_height + row_gap
        self.cursor_y += 4

    def draw_section(self, title: str, lines: list[str], index: int):
        palette = section_palette(title)
        wrapped_lines: list[str] = []
        for line in lines:
            wrapped_lines.extend(wrap_text(line, font=BODY_FONT, font_size=10.5, max_width=CONTENT_WIDTH - 42))
        line_height = 17
        block_height = 56 + len(wrapped_lines) * line_height + 14
        self.ensure_space(block_height + 14)

        x = MARGIN_X
        y = self.cursor_y
        draw_rect(self.page, x, y, CONTENT_WIDTH, block_height, fill="FFFFFF", stroke=palette["border"], radius=14, width_pt=1.0)
        draw_rect(self.page, x, y, CONTENT_WIDTH, 42, fill=palette["fill"], radius=14)
        draw_rect(self.page, x, y, 8, 42, fill=palette["accent"], radius=14)
        insert_text(self.page, x + 18, y + 28, f"{section_index_label(index)}、{title}", fontname="heading", fontsize=13.5, fill=palette["text"])

        text_y = y + 62
        for line in wrapped_lines:
            insert_text(self.page, x + 18, text_y, line, fontname="body", fontsize=10.5, fill="1F2937")
            text_y += line_height

        self.cursor_y = y + block_height + 14

    def finish(self):
        total_pages = len(self.doc)
        for page_index in range(total_pages):
            page = self.doc[page_index]
            insert_text(page, PAGE_WIDTH - 88, PAGE_HEIGHT - 24, f"第 {page_index + 1} / {total_pages} 页", fontname="body", fontsize=9, fill="94A3B8")


def summary_cards(summary: dict) -> list[dict[str, str]]:
    cards: list[dict[str, str]] = []
    assessments = summary.get("assessments") or {}
    alerts = summary.get("alerts") or {}
    interventions = summary.get("interventions") or {}
    questionnaires = summary.get("questionnaires") or {}
    retest = summary.get("retest") or {}

    if assessments:
        cards.append({"title": "评估样本", "value": f"{assessments.get('count', 0)} 份", "hint": f"平均分 {float(assessments.get('avg_score') or 0):.2f}"})
        cards.append({"title": "高风险占比", "value": f"{float((assessments.get('risk_distribution') or {}).get('high_ratio') or 0):.2f}%", "hint": "基于当前统计周期"})
    if alerts:
        cards.append({"title": "预警总数", "value": f"{alerts.get('count', 0)} 条", "hint": f"高风险未处理 {alerts.get('high_unack_count', 0)} 条"})
    if interventions:
        cards.append({"title": "干预介入率", "value": f"{float(interventions.get('intervention_rate') or 0):.2f}%", "hint": f"辅导员介入率 {float(interventions.get('counselor_involved_rate') or 0):.2f}%"})
    if questionnaires:
        cards.append({"title": "问卷提交", "value": f"{questionnaires.get('responses_count', 0)} 次", "hint": f"统计范围内问卷 {questionnaires.get('questionnaires_count', 0)} 份"})
    if retest:
        cards.append({"title": "复测改善率", "value": f"{float(retest.get('improvement_rate') or 0):.2f}%", "hint": f"恢复为安全 {retest.get('improved_to_safe_count', 0)} 人"})
    return cards


def main():
    if len(sys.argv) != 3:
        raise SystemExit("Usage: pdf_fitz_renderer.py <input.json> <output.pdf>")
    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])
    payload = json.loads(input_path.read_text(encoding="utf-8"))

    meta = payload.get("meta") or {}
    summary = payload.get("summary") or {}
    sections = payload.get("sections") or []

    canvas = PdfCanvas(meta=meta, summary=summary)
    canvas.new_page(first=True)
    canvas.draw_summary_cards(summary_cards(summary))
    for index, item in enumerate(sections, start=1):
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "")
        lines = [str(line) for line in (item.get("lines") or [])]
        if not title:
            continue
        canvas.draw_section(title, lines, index)
    canvas.finish()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.doc.save(output_path, garbage=4, deflate=True)


if __name__ == "__main__":
    main()
