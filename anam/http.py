"""عميل HTTP بسيط ومجاني مبني على مكتبة بايثون القياسية فقط.

- لا تبعيات خارجية.
- إعادة محاولة تلقائية مع تراجع تدريجي (backoff).
- دعم GITHUB_TOKEN الاختياري (مجاني) لرفع حدود الطلبات.
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from typing import Any, Optional

USER_AGENT = "ANAM/1.0 (+https://github.com/Wynm/ANAM)"


class HttpError(Exception):
    pass


def get_json(url: str, token: Optional[str] = None, retries: int = 3,
             timeout: int = 20) -> Any:
    headers = {"User-Agent": USER_AGENT, "Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return _request(url, headers, retries, timeout, as_json=True)


def get_text(url: str, token: Optional[str] = None, retries: int = 3,
             timeout: int = 20) -> str:
    headers = {"User-Agent": USER_AGENT, "Accept": "*/*"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return _request(url, headers, retries, timeout, as_json=False)


def _request(url: str, headers: dict[str, str], retries: int,
             timeout: int, as_json: bool) -> Any:
    last_err: Optional[Exception] = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = resp.read().decode("utf-8", errors="replace")
                return json.loads(body) if as_json else body
        except urllib.error.HTTPError as e:
            last_err = e
            if e.code in (403, 429):  # rate limit — انتظر ثم أعد المحاولة
                time.sleep(2.0 * (attempt + 1))
                continue
            if 500 <= e.code < 600:
                time.sleep(1.5 * (attempt + 1))
                continue
            raise HttpError(f"HTTP {e.code} عند طلب {url}") from e
        except Exception as e:  # شبكة / مهلة / JSON غير صالح
            last_err = e
            time.sleep(1.0 * (attempt + 1))
    raise HttpError(f"فشل طلب {url} بعد {retries} محاولات: {last_err}")


def github_token(env_name: str = "GITHUB_TOKEN") -> Optional[str]:
    return os.environ.get(env_name) or None
