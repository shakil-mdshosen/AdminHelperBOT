"""Minimal MediaWiki Action API client (login, maxlag, server clock)."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import requests

from .timeutil import UTC, parse_api_ts

log = logging.getLogger(__name__)


def _retry_after(resp, default: int) -> int:
    try:
        return max(1, int(resp.headers.get("Retry-After", default)))
    except (TypeError, ValueError):
        return default


class APIError(Exception):
    def __init__(self, code: str, info: str, data: Optional[dict] = None):
        super().__init__(f"{code}: {info}")
        self.code, self.info, self.data = code, info, data or {}


class MediaWikiAPI:
    def __init__(self, url: str, user_agent: str, maxlag: int = 5,
                 session: Optional[requests.Session] = None):
        self.url = url
        self.maxlag = maxlag
        self.session = session or requests.Session()
        self.session.headers["User-Agent"] = user_agent
        self.logged_in_as: Optional[str] = None
        self._clock_offset = timedelta(0)   # server time - local time

    # ------------------------------------------------------------------
    def request(self, params: Dict[str, Any], post: bool = False,
                retries: int = 5) -> dict:
        params = {k: v for k, v in params.items() if v is not None}
        params.update(format="json", formatversion="2", curtimestamp="1",
                      errorformat="plaintext")
        if self.maxlag:
            params.setdefault("maxlag", self.maxlag)
        delay = 5
        for attempt in range(1, retries + 1):
            try:
                if post:
                    resp = self.session.post(self.url, data=params, timeout=60)
                else:
                    resp = self.session.get(self.url, params=params, timeout=60)
            except requests.RequestException as exc:
                if attempt == retries:
                    raise
                log.warning("Network error (%s), retrying in %ss", exc, delay)
                time.sleep(delay)
                delay = min(delay * 2, 120)
                continue
            if resp.status_code >= 500 or resp.status_code == 429:
                if attempt == retries:
                    resp.raise_for_status()
                wait = _retry_after(resp, delay)
                log.warning("HTTP %s, retrying in %ss", resp.status_code, wait)
                time.sleep(wait)
                delay = min(delay * 2, 120)
                continue
            resp.raise_for_status()
            data = resp.json()
            if "curtimestamp" in data:
                server = parse_api_ts(data["curtimestamp"])
                self._clock_offset = server - datetime.now(UTC)
            errors = data.get("errors") or []
            if errors:
                code = errors[0].get("code", "unknown")
                info = errors[0].get("text", errors[0].get("*", ""))
                if code == "maxlag" and attempt < retries:
                    wait = _retry_after(resp, 5)
                    log.info("maxlag hit, waiting %ss", wait)
                    time.sleep(wait)
                    continue
                raise APIError(code, info, data)
            return data
        raise APIError("retries-exhausted", "request failed repeatedly")

    def get(self, **params) -> dict:
        return self.request(params)

    def post(self, **params) -> dict:
        return self.request(params, post=True)

    # ------------------------------------------------------------------
    def now(self) -> datetime:
        """Current time according to the wiki server (last response)."""
        return datetime.now(UTC) + self._clock_offset

    def sync_clock(self) -> datetime:
        self.get(action="query", meta="siteinfo", siprop="general")
        return self.now()

    def login(self, username: str, password: str) -> None:
        token = self.get(action="query", meta="tokens",
                         type="login")["query"]["tokens"]["logintoken"]
        data = self.post(action="login", lgname=username, lgpassword=password,
                         lgtoken=token)
        result = data.get("login", {})
        if result.get("result") != "Success":
            raise APIError("login-failed", str(result.get("reason", result)))
        self.logged_in_as = result["lgusername"]
        log.info("Logged in as %s", self.logged_in_as)

    def csrf_token(self) -> str:
        return self.get(action="query", meta="tokens",
                        type="csrf")["query"]["tokens"]["csrftoken"]
