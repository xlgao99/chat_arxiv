from __future__ import annotations

from dataclasses import dataclass

from .arxiv_client import ArxivPaper


@dataclass(frozen=True)
class FilterResult:
    paper: ArxivPaper
    score: int
    matched_keywords: list[str]


def _norm(s: str) -> str:
    return (s or "").lower()


def score_paper(paper: ArxivPaper, keywords: list[str]) -> FilterResult:
    hay = _norm(paper.title) + "\n" + _norm(paper.summary)
    matched: list[str] = []
    score = 0
    for kw in keywords:
        k = _norm(kw).strip()
        if not k:
            continue
        if k in hay:
            matched.append(kw)
            score += 1
    # 去重且保留原顺序
    seen = set()
    matched_unique = []
    for m in matched:
        if m not in seen:
            matched_unique.append(m)
            seen.add(m)
    return FilterResult(paper=paper, score=score, matched_keywords=matched_unique)


def filter_papers(
    papers: list[ArxivPaper], keywords: list[str], min_score: int = 1
) -> list[FilterResult]:
    results: list[FilterResult] = []
    for p in papers:
        r = score_paper(p, keywords)
        if r.score >= min_score:
            results.append(r)
    # score desc, updated desc
    results.sort(key=lambda x: (x.score, x.paper.updated), reverse=True)
    return results

