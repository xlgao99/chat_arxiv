from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from .arxiv_client import fetch_recent
from .config import load_config, validate_config
from .deepseek_client import DeepSeekClient
from .filtering import filter_papers
from .mailer import SmtpMailer
from .renderer import RenderItem, render_email
from .state_store import StateStore
from .summarizer import Summarizer


def _safe_zoneinfo(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name)
    except Exception:  # noqa: BLE001
        return ZoneInfo("UTC")


def main() -> int:
    cfg = load_config()
    validate_config(cfg)

    print("[config] loaded:", {k: v for k, v in asdict(cfg).items() if k not in {"smtp_pass", "deepseek_api_key"}})

    papers = fetch_recent(
        categories=cfg.arxiv_categories,
        keywords=cfg.keywords,
        since_hours=cfg.since_hours,
        max_results=cfg.limit,
    )
    
    print(f"[arxiv] fetched {len(papers)} entries in last {cfg.since_hours}h (limit={cfg.limit})")

    filtered = filter_papers(papers, cfg.keywords, min_score=1)
    print(f"[filter] matched {len(filtered)} entries (min_score=1)")

    state = StateStore(cfg.state_path)

    to_process = []
    for r in filtered:
        p = r.paper
        updated_iso = p.updated.isoformat()
        if state.should_send(p.arxiv_id, updated_iso, cfg.resend_on_update):
            to_process.append(r)
    print(
        f"[state] to_send {len(to_process)} / {len(filtered)} (resend_on_update={cfg.resend_on_update})"
    )

    summaries: dict[str, str] = {}
    failed: list[str] = []
    if cfg.deepseek_api_key and to_process:
        client = DeepSeekClient(
            api_key=cfg.deepseek_api_key,
            base_url=cfg.deepseek_base_url,
            model=cfg.deepseek_model,
            timeout_s=cfg.deepseek_timeout_s,
            max_retries=cfg.deepseek_max_retries,
        )
        summarizer = Summarizer(client)
        for idx, r in enumerate(to_process, 1):
            p = r.paper
            print(f"[deepseek] summarizing {idx}/{len(to_process)}: {p.arxiv_id}")
            try:
                summaries[p.arxiv_id] = summarizer.summarize_one(
                    paper=p, matched_keywords=r.matched_keywords
                )
            except Exception as e:  # noqa: BLE001
                failed.append(f"{p.arxiv_id} {p.title} ({type(e).__name__}: {e})")
    else:
        if not cfg.deepseek_api_key:
            print("[deepseek] DEEPSEEK_API_KEY not set; skip summarization")

    tz = _safe_zoneinfo(cfg.timezone)
    date_local = datetime.now(timezone.utc).astimezone(tz).strftime("%Y-%m-%d")

    items: list[RenderItem] = []
    for r in to_process:
        p = r.paper
        items.append(
            RenderItem(
                title=p.title,
                arxiv_id=p.arxiv_id,
                link_abs=p.link_abs,
                authors=p.authors,
                categories=p.categories,
                updated_iso=p.updated.isoformat(),
                matched_keywords=r.matched_keywords,
                abstract=p.summary,
                summary_md=summaries.get(p.arxiv_id),
                score=r.score,
            )
        )

    rendered = render_email(
        subject_prefix=cfg.mail_subject_prefix,
        date_local=date_local,
        items=items,
        failed=failed,
    )

    if cfg.dry_run:
        print("[dry_run] enabled: will NOT send email, will NOT update state.")
        print("\n" + "=" * 80 + "\n")
        print(rendered.text)
        print("\n" + "=" * 80 + "\n")
        print(f"[dry_run] html_size={len(rendered.html)} bytes")
        return 0

    mailer = SmtpMailer(
        host=cfg.smtp_host or "",
        port=cfg.smtp_port,
        username=cfg.smtp_user or "",
        password=cfg.smtp_pass or "",
        use_ssl=cfg.smtp_use_ssl,
        starttls=cfg.smtp_starttls,
        timeout_s=30,
        max_retries=3,
    )
    mailer.send(
        mail_from=cfg.mail_from or "",
        mail_to=cfg.mail_to,
        subject=rendered.subject,
        text=rendered.text,
        html=rendered.html,
    )
    print(f"[mail] sent to {len(cfg.mail_to)} recipient(s)")

    # update state only after mail successfully sent
    for r in to_process:
        p = r.paper
        state.mark_sent(p.arxiv_id, p.updated.isoformat())
    state.save()
    print("[state] saved:", cfg.state_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

