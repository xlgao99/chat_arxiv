from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .arxiv_client import ArxivPaper
from .deepseek_client import DeepSeekClient


@dataclass(frozen=True)
class PaperSummary:
    arxiv_id: str
    title: str
    summary_text: str


SYSTEM_PROMPT = """你是一位严谨的科研助理，擅长快速阅读论文摘要并产出结构化中文总结。
要求：信息准确，不夸大；当摘要没有提供细节时要明确说明。输出使用 Markdown。"""

def _format_authors(authors: object) -> str:
    """
    arXiv 解析出来的 authors 目前是 list[tuple[name, affiliation]]。
    这里做一次兜底，避免在 prompt 拼接时因 tuple 导致 join TypeError。
    """
    if not authors:
        return "(未知)"
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
        return ", ".join(parts) if parts else "(未知)"
    return str(authors).strip() or "(未知)"


def build_user_prompt(p: ArxivPaper, matched_keywords: Iterable[str]) -> str:
    kws = ", ".join(matched_keywords) if matched_keywords else "(无)"
    return f"""请基于以下论文信息生成结构化中文总结：

【标题】
{p.title}

【作者】
{_format_authors(p.authors)}

【分类】
{", ".join(p.categories) if p.categories else "(未知)"}

【arXiv】
{p.link_abs}

【更新时间(UTC)】
{p.updated.isoformat()}

【关键词命中】
{kws}

【摘要】
{p.summary}

输出格式（必须包含这些小标题）：
1) 一句话结论
2) 核心贡献（3-5条）
3) 方法要点（3-5条）
4) 实验与结果（若摘要未给出，写“摘要未提供细节”）
5) 与强化学习/后训练/对齐的关联（1-3条）
6) 局限与开放问题（1-3条）
"""


class Summarizer:
    def __init__(self, client: DeepSeekClient) -> None:
        self.client = client

    def summarize_one(self, paper: ArxivPaper, matched_keywords: list[str]) -> str:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(paper, matched_keywords)},
        ]
        resp = self.client.chat(messages=messages, temperature=0.2)
        return resp.content

