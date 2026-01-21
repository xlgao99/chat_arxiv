from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Any

import yaml


def _getenv_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    raw = raw.strip().lower()
    return raw in {"1", "true", "yes", "y", "on"}


def _getenv_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return int(raw)


def _getenv_str(name: str, default: str | None = None) -> str | None:
    raw = os.getenv(name)
    if raw is None:
        return default
    raw = raw.strip()
    return raw if raw != "" else default


@dataclass(frozen=True)
class Config:
    # arXiv
    arxiv_categories: list[str]
    since_hours: int
    limit: int
    keywords: list[str]

    # State
    state_path: str
    state_backend: str  # repo | cache (for future)
    resend_on_update: bool

    # DeepSeek
    deepseek_api_key: str | None
    deepseek_base_url: str
    deepseek_model: str
    deepseek_timeout_s: int
    deepseek_max_retries: int

    # Mail
    dry_run: bool
    smtp_host: str | None
    smtp_port: int
    smtp_user: str | None
    smtp_pass: str | None
    smtp_use_ssl: bool
    smtp_starttls: bool
    mail_from: str | None
    mail_to: list[str]

    # Rendering
    mail_subject_prefix: str
    timezone: str


DEFAULT_KEYWORDS = [
    # RL / optimization
    "reinforcement learning",
    "policy optimization",
    #"ppo",
    #"q-learning",
    #"actor-critic",
    "rl",
    # post-training / alignment
    "post-training",
    "alignment",
    "rlhf",
    "preference optimization",
    #"dpo",
    #"ipo",
    #"kto",
    #"rlaif",
    #"reward model",
    #"sft",
    #"instruction tuning",
    # extras
    "llm",
    "language model",
    "agent",
]


def load_config(config_path: str = "config.yaml") -> Config:
    file_cfg: dict[str, Any] = {}
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            file_cfg = yaml.safe_load(f) or {}

    arxiv_cfg = file_cfg.get("arxiv", {})
    state_cfg = file_cfg.get("state", {})
    deepseek_cfg = file_cfg.get("deepseek", {})
    mail_cfg = file_cfg.get("mail", {})
    render_cfg = file_cfg.get("render", {})

    categories = (
        _getenv_str("ARXIV_CATEGORIES")
        or ",".join(arxiv_cfg.get("categories", ["cs.AI", "cs.LG", "stat.ML"]))
    )
    arxiv_categories = [c.strip() for c in categories.split(",") if c.strip()]

    keywords_raw = _getenv_str("KEYWORDS")
    if keywords_raw:
        keywords = [k.strip() for k in keywords_raw.split(",") if k.strip()]
    else:
        keywords = arxiv_cfg.get("keywords") or DEFAULT_KEYWORDS

    mail_to_raw = _getenv_str("MAIL_TO") or ",".join(mail_cfg.get("to", []))
    mail_to = [x.strip() for x in mail_to_raw.split(",") if x.strip()]

    return Config(
        arxiv_categories=arxiv_categories,
        since_hours=_getenv_int("SINCE_HOURS", int(arxiv_cfg.get("since_hours", 24))),
        limit=_getenv_int("LIMIT", int(arxiv_cfg.get("limit", 50))),
        keywords=keywords,
        state_path=_getenv_str("STATE_PATH", state_cfg.get("path", "data/state.json"))
        or "data/state.json",
        state_backend=_getenv_str("STATE_BACKEND", state_cfg.get("backend", "repo"))
        or "repo",
        resend_on_update=_getenv_bool(
            "RESEND_ON_UPDATE", bool(state_cfg.get("resend_on_update", False))
        ),
        deepseek_api_key=_getenv_str("DEEPSEEK_API_KEY", deepseek_cfg.get("api_key")),
        deepseek_base_url=_getenv_str(
            "DEEPSEEK_BASE_URL", deepseek_cfg.get("base_url", "https://api.deepseek.com")
        )
        or "https://api.deepseek.com",
        deepseek_model=_getenv_str(
            "DEEPSEEK_MODEL", deepseek_cfg.get("model", "deepseek-chat")
        )
        or "deepseek-chat",
        deepseek_timeout_s=_getenv_int(
            "DEEPSEEK_TIMEOUT_S", int(deepseek_cfg.get("timeout_s", 60))
        ),
        deepseek_max_retries=_getenv_int(
            "DEEPSEEK_MAX_RETRIES", int(deepseek_cfg.get("max_retries", 3))
        ),
        dry_run=_getenv_bool("DRY_RUN", bool(mail_cfg.get("dry_run", False))),
        smtp_host=_getenv_str("SMTP_HOST", mail_cfg.get("smtp_host")),
        smtp_port=_getenv_int("SMTP_PORT", int(mail_cfg.get("smtp_port", 587))),
        smtp_user=_getenv_str("SMTP_USER", mail_cfg.get("smtp_user")),
        smtp_pass=_getenv_str("SMTP_PASS", mail_cfg.get("smtp_pass")),
        smtp_use_ssl=_getenv_bool("SMTP_USE_SSL", bool(mail_cfg.get("use_ssl", False))),
        smtp_starttls=_getenv_bool(
            "SMTP_STARTTLS", bool(mail_cfg.get("starttls", True))
        ),
        mail_from=_getenv_str("MAIL_FROM", mail_cfg.get("from")),
        mail_to=mail_to,
        mail_subject_prefix=_getenv_str(
            "MAIL_SUBJECT_PREFIX", render_cfg.get("subject_prefix", "[arXiv日报]")
        )
        or "[arXiv日报]",
        timezone=_getenv_str("TIMEZONE", render_cfg.get("timezone", "Asia/Shanghai"))
        or "Asia/Shanghai",
    )


def validate_config(cfg: Config) -> None:
    if not cfg.arxiv_categories:
        raise ValueError("ARXIV_CATEGORIES 不能为空")
    if cfg.since_hours <= 0:
        raise ValueError("SINCE_HOURS 必须 > 0")
    if cfg.limit <= 0:
        raise ValueError("LIMIT 必须 > 0")
    if not cfg.keywords:
        raise ValueError("关键词列表不能为空（KEYWORDS 或 config.yaml）")
    if not cfg.dry_run:
        missing = []
        if not cfg.smtp_host:
            missing.append("SMTP_HOST")
        if not cfg.smtp_port:
            missing.append("SMTP_PORT")
        if not cfg.smtp_user:
            missing.append("SMTP_USER")
        if not cfg.smtp_pass:
            missing.append("SMTP_PASS")
        if not cfg.mail_from:
            missing.append("MAIL_FROM")
        if not cfg.mail_to:
            missing.append("MAIL_TO")
        if missing:
            raise ValueError(f"非 DRY_RUN 模式缺少配置: {', '.join(missing)}")
    if cfg.deepseek_api_key is None:
        # 允许 DRY_RUN 先跑通抓取/渲染，但会跳过总结或用降级策略
        return

