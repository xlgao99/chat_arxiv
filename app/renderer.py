from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from html import escape


@dataclass(frozen=True)
class RenderItem:
    title: str
    arxiv_id: str
    link_abs: str
    authors: list[tuple[str, str]]
    categories: list[str]
    updated_iso: str
    matched_keywords: list[str]
    abstract: str
    summary_md: str | None
    score: int


@dataclass(frozen=True)
class RenderedEmail:
    subject: str
    text: str
    html: str


def _shorten(text: str, n: int = 900) -> str:
    t = " ".join((text or "").split())
    return t if len(t) <= n else (t[: n - 1] + "…")

def _format_authors(authors: object) -> str:
    """
    统一把 authors 格式化为可读字符串。
    兼容两种形态：
    - list[tuple[name, affiliation]]
    - list[str]
    """
    if not authors:
        return ""
    if isinstance(authors, list):
        parts: list[str] = []
        for a in authors:
            if isinstance(a, tuple) and len(a) >= 1:
                name = str(a[0]).strip()
                aff = str(a[1]).strip() if len(a) >= 2 and a[1] is not None else ""
                if name and aff:
                    parts.append(f"{name} ({aff})")
                elif name:
                    parts.append(name)
            else:
                s = str(a).strip()
                if s:
                    parts.append(s)
        return ", ".join(parts)
    return str(authors)


def render_email(
    subject_prefix: str,
    date_local: str,
    items: list[RenderItem],
    failed: list[str] | None = None,
) -> RenderedEmail:
    failed = failed or []
    subject = f"{subject_prefix} {date_local}（{len(items)}篇）"

    # Text
    lines: list[str] = []
    lines.append(subject)
    lines.append("")
    if not items:
        lines.append("今天没有命中关键词的论文。")
    for i, it in enumerate(items, 1):
        lines.append(f"{i}. {it.title}")
        lines.append(f"   arXiv: {it.arxiv_id}")
        lines.append(f"   Link: {it.link_abs}")
        if it.authors:
            lines.append(f"   Authors: {_format_authors(it.authors)}")
        if it.categories:
            lines.append(f"   Categories: {', '.join(it.categories)}")
        if it.matched_keywords:
            lines.append(f"   Matched: {', '.join(it.matched_keywords)} (score={it.score})")
        lines.append(f"   Updated: {it.updated_iso}")
        lines.append("   Abstract:")
        lines.append(f"   {_shorten(it.abstract, 600)}")
        if it.summary_md:
            lines.append("   Summary:")
            # keep indentation
            for ln in it.summary_md.splitlines():
                lines.append(f"   {ln}")
        else:
            lines.append("   Summary: (未生成/跳过)")
        lines.append("")
    if failed:
        lines.append("未总结成功的条目：")
        for x in failed:
            lines.append(f"- {x}")
        lines.append("")
    text_body = "\n".join(lines).strip() + "\n"

    # HTML (minimal, self-contained)
    html_parts: list[str] = []
    html_parts.append("<!doctype html>")
    html_parts.append("<html><head><meta charset='utf-8' />")
    html_parts.append("<meta name='viewport' content='width=device-width, initial-scale=1' />")
    html_parts.append("<title>" + escape(subject) + "</title>")
    html_parts.append("</head><body style='font-family: -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, Helvetica, Arial, sans-serif; line-height:1.5;'>")
    html_parts.append(f"<h2 style='margin:0 0 12px 0;'>{escape(subject)}</h2>")

    if not items:
        html_parts.append("<p>今天没有命中关键词的论文。</p>")

    for i, it in enumerate(items, 1):
        html_parts.append("<div style='border:1px solid #e5e7eb; border-radius:10px; padding:14px; margin:12px 0;'>")
        html_parts.append(
            f"<div style='font-size:16px; font-weight:700; margin-bottom:6px;'>{i}. "
            f"<a href='{escape(it.link_abs)}' style='text-decoration:none;'>{escape(it.title)}</a>"
            f"</div>"
        )
        meta = []
        meta.append(f"<b>arXiv</b>: {escape(it.arxiv_id)}")
        if it.authors:
            meta.append(f"<b>Authors</b>: {escape(_format_authors(it.authors))}")
        if it.categories:
            meta.append(f"<b>Categories</b>: {escape(', '.join(it.categories))}")
        meta.append(f"<b>Updated</b>: {escape(it.updated_iso)}")
        if it.matched_keywords:
            meta.append(
                f"<b>Matched</b>: {escape(', '.join(it.matched_keywords))} (score={it.score})"
            )
        html_parts.append("<div style='color:#374151; font-size:13px;'>" + "<br/>".join(meta) + "</div>")
        html_parts.append("<hr style='border:none; border-top:1px solid #eee; margin:10px 0;'/>")
        html_parts.append("<div style='font-size:13px; color:#111827;'><b>Abstract</b></div>")
        html_parts.append("<div style='font-size:13px; color:#111827; white-space:pre-wrap;'>" + escape(_shorten(it.abstract, 900)) + "</div>")
        html_parts.append("<div style='height:10px;'></div>")
        html_parts.append("<div style='font-size:13px; color:#111827;'><b>Summary</b></div>")
        if it.summary_md:
            # keep markdown as pre-wrap plain text (most mail clients render safely)
            html_parts.append("<div style='font-size:13px; color:#111827; white-space:pre-wrap;'>" + escape(it.summary_md) + "</div>")
        else:
            html_parts.append("<div style='font-size:13px; color:#6b7280;'>未生成/跳过</div>")
        html_parts.append("</div>")

    if failed:
        html_parts.append("<h3 style='margin-top:18px;'>未总结成功的条目</h3>")
        html_parts.append("<ul>")
        for x in failed:
            html_parts.append("<li>" + escape(x) + "</li>")
        html_parts.append("</ul>")

    html_parts.append("<p style='color:#6b7280; font-size:12px;'>此邮件由 GitHub Actions 自动生成。</p>")
    html_parts.append("</body></html>")

    return RenderedEmail(subject=subject, text=text_body, html="\n".join(html_parts))


def local_date_string(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d")

