from __future__ import annotations

from dataclasses import dataclass
import json
import time
from typing import Any

import requests


@dataclass(frozen=True)
class DeepSeekResponse:
    content: str
    raw: dict[str, Any]


class DeepSeekClient:
    """
    DeepSeek 提供 OpenAI 兼容接口，默认走:
      POST {base_url}/v1/chat/completions
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.deepseek.com",
        model: str = "deepseek-chat",
        timeout_s: int = 60,
        max_retries: int = 3,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_s = timeout_s
        self.max_retries = max_retries
        self._session = requests.Session()

    def chat(self, messages: list[dict[str, str]], temperature: float = 0.2) -> DeepSeekResponse:
        url = f"{self.base_url}/v1/chat/completions"
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        last_err: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                resp = self._session.post(
                    url, headers=headers, data=json.dumps(payload), timeout=self.timeout_s
                )
                if resp.status_code >= 500:
                    raise requests.HTTPError(
                        f"DeepSeek 5xx: {resp.status_code} {resp.text[:2000]}",
                        response=resp,
                    )
                resp.raise_for_status()
                raw = resp.json()
                content = (
                    raw.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "")
                    .strip()
                )
                return DeepSeekResponse(content=content, raw=raw)
            except Exception as e:  # noqa: BLE001
                last_err = e
                if attempt == self.max_retries:
                    break
                # 指数退避 + 抖动
                sleep_s = min(8.0, 0.8 * (2 ** (attempt - 1))) + (0.05 * attempt)
                time.sleep(sleep_s)
        assert last_err is not None
        raise last_err

if __name__ == "__main__":
    client = DeepSeekClient(api_key='sk-243e0a6960e74681aaae62aaeabc15b3')
    messages = [
        {"role": "user", "content": "who r y?"}
    ]
    print(client.chat(messages=messages))
