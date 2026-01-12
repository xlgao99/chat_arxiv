from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from typing import Any


@dataclass(frozen=True)
class SeenInfo:
    updated: str  # ISO8601
    sent_at: str  # ISO8601


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: str) -> dict[str, Any]:
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f) or {}


def _save_json(path: str, obj: dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, sort_keys=True)
    os.replace(tmp, path)


def base_arxiv_id(arxiv_id_with_version: str) -> str:
    # 2501.01234v2 -> 2501.01234
    s = arxiv_id_with_version.strip()
    if "v" in s and s.rsplit("v", 1)[-1].isdigit():
        return s.rsplit("v", 1)[0]
    return s


class StateStore:
    """
    JSON state format:
    {
      "sent": {
        "2501.01234": { "updated": "2026-01-12T00:00:00+00:00", "sent_at": "..." }
      },
      "last_run": "..."
    }
    """

    def __init__(self, path: str) -> None:
        self.path = path
        self._state: dict[str, Any] = _load_json(path)
        self._state.setdefault("sent", {})

    def should_send(self, arxiv_id: str, updated_iso: str, resend_on_update: bool) -> bool:
        sent: dict[str, Any] = self._state.get("sent", {})
        bid = base_arxiv_id(arxiv_id)
        info = sent.get(bid)
        if info is None:
            return True
        if not resend_on_update:
            return False
        prev_updated = str(info.get("updated", ""))
        return prev_updated != updated_iso

    def mark_sent(self, arxiv_id: str, updated_iso: str) -> None:
        bid = base_arxiv_id(arxiv_id)
        sent: dict[str, Any] = self._state.setdefault("sent", {})
        sent[bid] = {"updated": updated_iso, "sent_at": _utc_now_iso()}

    def save(self) -> None:
        self._state["last_run"] = _utc_now_iso()
        _save_json(self.path, self._state)

