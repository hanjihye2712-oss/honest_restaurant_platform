"""
ai.admin_utils
==============
AI 앱 어드민 공통 유틸리티.
SentimentResultAdmin, ReviewClassificationResultAdmin 등에서 공유한다.
"""

from django.utils.html import format_html

DEFAULT_BADGE = ("#e9ecef", "#495057")


def badge(bg: str, color: str, label: str, weight: str = "600") -> str:
    return format_html(
        '<span style="background:{};color:{};padding:3px 10px;'
        'border-radius:999px;font-size:12px;font-weight:{};">{}</span>',
        bg, color, weight, label,
    )


def status_badge(status: str, style_map: dict) -> str:
    bg, color, label = style_map.get(status, (*DEFAULT_BADGE, status))
    return badge(bg, color, label)


def score_bar(score: float | None, label: str | None) -> str:
    if score is None:
        return "—"
    pct   = int(score * 100)
    color = "#28a745" if label == "긍정" else "#dc3545"
    return format_html(
        '<div style="display:flex;align-items:center;gap:8px;">'
        '<div style="width:120px;background:#e9ecef;border-radius:4px;height:10px;">'
        '<div style="width:{}%;background:{};border-radius:4px;height:10px;"></div>'
        '</div>'
        '<span style="font-size:13px;font-weight:600;">{:.1f}%</span>'
        '</div>',
        pct, color, score * 100,
    )
