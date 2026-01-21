from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterable
import urllib.parse

import feedparser
import requests


@dataclass(frozen=True)
class ArxivPaper:
    arxiv_id: str
    title: str
    summary: str
    authors: list[tuple[str, str]]
    categories: list[str]
    published: datetime
    updated: datetime
    link_abs: str
    link_pdf: str | None


def _parse_arxiv_datetime(value: str) -> datetime:
    # arXiv Atom: 2007-10-10T10:10:10Z
    dt = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    return dt.replace(tzinfo=timezone.utc)


def _extract_arxiv_id(entry_id: str) -> str:
    # entry.id like: http://arxiv.org/abs/2501.01234v2
    # keep full id including version so we can detect update; but state uses base id too.
    parsed = urllib.parse.urlparse(entry_id)
    path = parsed.path.strip("/")
    # abs/xxxx.yyyyyvN
    if "/" in path:
        path = path.split("/", 1)[1]
    return path


def build_query(categories: Iterable[str], keywords: Iterable[str]) -> str:
    cats = [c.strip() for c in categories if c and c.strip()]
    if not cats:
        raise ValueError("categories 不能为空")
    # (cat:cs.AI OR cat:cs.LG OR cat:stat.ML)
    parts = [f"cat:{c}" for c in cats]
    if keywords:
        parts.append(f"ti:{' AND'.join(keywords)}")
    query = " OR ".join(parts)
    return f"({query})"


def fetch_recent(
    categories: list[str],
    keywords: list[str] = ['Data Selection'],
    since_hours: int = 24,
    max_results: int = 50,
    session: requests.Session | None = None,
) -> list[ArxivPaper]:
    """
    Fetch recent papers sorted by lastUpdatedDate, then filter by updated >= now - since_hours.
    """
    q = build_query(categories, keywords)
    params = {
        "search_query": q,
        "start": 0,
        "max_results": int(max_results),
        "sortBy": "lastUpdatedDate", # relevance
        "sortOrder": "descending",
    }
    url = "http://export.arxiv.org/api/query?" + urllib.parse.urlencode(params)

    sess = session or requests.Session()
    resp = sess.get(url, timeout=30)
    resp.raise_for_status()

    feed = feedparser.parse(resp.text)
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=int(since_hours * 7))

    papers: list[ArxivPaper] = []
    for entry in feed.entries:
        updated = _parse_arxiv_datetime(entry.updated)
        if updated < cutoff:
            # feed is sorted desc by updated, we can stop early
            break

        published = _parse_arxiv_datetime(entry.published)
        arxiv_id = _extract_arxiv_id(entry.id)
        title = " ".join((entry.title or "").split())
        summary = " ".join((entry.summary or "").split())
        #breakpoint()
        authors = [(a.name, a.get('arxiv_affiliation', '未提供')) for a in getattr(entry, "authors", []) if getattr(a, "name", None)]
        categories = [t.term for t in getattr(entry, "tags", []) if getattr(t, "term", None)]

        link_abs = None
        link_pdf = None
        for link in getattr(entry, "links", []) or []:
            href = getattr(link, "href", None)
            rel = getattr(link, "rel", None)
            typ = getattr(link, "type", None)
            if rel == "alternate" and href and href.startswith("http"):
                link_abs = href
            # pdf link tends to have type application/pdf or title "pdf"
            if href and "pdf" in href and (typ == "application/pdf" or href.endswith(".pdf")):
                link_pdf = href
        if link_abs is None:
            # fallback from id
            link_abs = entry.id.replace("http://", "https://").replace("/abs/", "/abs/")

        papers.append(
            ArxivPaper(
                arxiv_id=arxiv_id,
                title=title,
                summary=summary,
                authors=authors,
                categories=categories,
                published=published,
                updated=updated,
                link_abs=link_abs,
                link_pdf=link_pdf,
            )
        )
    return papers

if __name__ == "__main__":
    papers = fetch_recent(categories=["cs.AI", "cs.LG", "stat.ML"], keywords=['Data Selection'],
                           max_results=10)
    #breakpoint()
    print(papers)
