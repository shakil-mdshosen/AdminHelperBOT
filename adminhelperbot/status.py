"""Look up what happened to reported accounts (blocks, locks, last edit)."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Iterable, List, Optional

from .api import APIError, MediaWikiAPI
from .parser import Account, normalize_username
from .timeutil import parse_api_ts

log = logging.getLogger(__name__)

LOCAL_BLOCK = "local_block"
GLOBAL_BLOCK = "global_block"
GLOBAL_LOCK = "global_lock"


@dataclass
class ActionEvent:
    kind: str                       # LOCAL_BLOCK / GLOBAL_BLOCK / GLOBAL_LOCK
    actor: Optional[str]            # admin / steward username (None = unknown)
    timestamp: Optional[datetime]   # None when the log is hidden
    expiry: Optional[str] = None
    partial: bool = False


@dataclass
class AccountStatus:
    name: str
    actions: List[ActionEvent] = field(default_factory=list)
    last_edit: Optional[datetime] = None
    last_edit_checked: bool = False


def _chunks(items: List[str], size: int = 50):
    for i in range(0, len(items), size):
        yield items[i:i + size]


class StatusChecker:
    def __init__(self, api: MediaWikiAPI, meta_api: MediaWikiAPI):
        self.api = api
        self.meta = meta_api

    def fetch(self, accounts: Iterable[Account]) -> Dict[str, AccountStatus]:
        accounts = list({a.name: a for a in accounts}.values())
        result = {a.name: AccountStatus(a.name) for a in accounts}
        users = [a.name for a in accounts if not a.is_ip]
        ips = [a.name for a in accounts if a.is_ip]

        self._local_blocks(users, ips, result)
        self._global_blocks(users + ips, result)
        for name in users:
            self._global_lock(name, result[name])
        for a in accounts:
            if a.is_temp:
                self._last_edit(result[a.name])
        return result

    # ------------------------------------------------------------------
    def _local_blocks(self, users: List[str], ips: List[str],
                      result: Dict[str, AccountStatus]) -> None:
        prop = "id|user|by|timestamp|expiry|flags"
        for chunk in _chunks(users):
            data = self.api.get(action="query", list="blocks", bkusers="|".join(chunk),
                                bkprop=prop, bklimit="max")
            for b in data["query"]["blocks"]:
                name = normalize_username(b.get("user", ""))
                if name in result and not b.get("automatic"):
                    result[name].actions.append(self._block_event(b))
        for ip in ips:
            data = self.api.get(action="query", list="blocks", bkip=ip,
                                bkprop=prop, bklimit="max")
            for b in data["query"]["blocks"]:
                if not b.get("automatic"):
                    result[ip].actions.append(self._block_event(b))

    @staticmethod
    def _block_event(b: dict) -> ActionEvent:
        return ActionEvent(
            kind=LOCAL_BLOCK, actor=b.get("by"),
            timestamp=parse_api_ts(b["timestamp"]) if b.get("timestamp") else None,
            expiry=b.get("expiry"), partial=bool(b.get("partial")),
        )

    def _global_blocks(self, names: List[str],
                       result: Dict[str, AccountStatus]) -> None:
        for chunk in _chunks(names):
            try:
                data = self.api.get(action="query", list="globalblocks",
                                    bgtargets="|".join(chunk),
                                    bgprop="id|address|target|by|timestamp|expiry|range",
                                    bglimit="max")
            except APIError as exc:
                log.warning("globalblocks lookup failed: %s", exc)
                continue
            for b in data["query"].get("globalblocks", []):
                target = normalize_username(b.get("target") or b.get("address") or "")
                if target in result:
                    result[target].actions.append(ActionEvent(
                        kind=GLOBAL_BLOCK, actor=b.get("by"),
                        timestamp=parse_api_ts(b["timestamp"]) if b.get("timestamp") else None,
                        expiry=b.get("expiry"),
                    ))

    def _global_lock(self, name: str, status: AccountStatus) -> None:
        data = self.api.get(action="query", meta="globaluserinfo", guiuser=name)
        info = data["query"].get("globaluserinfo", {})
        if info.get("missing") or not info.get("locked"):
            return
        actor, ts = None, None
        try:
            logs = self.meta.get(action="query", list="logevents", letype="globalauth",
                                 letitle=f"User:{name}@global", lelimit="20",
                                 leprop="user|timestamp|details|type")
            for entry in logs["query"]["logevents"]:   # newest first
                if _is_lock_entry(entry):
                    actor = entry.get("user")
                    ts = parse_api_ts(entry["timestamp"]) if entry.get("timestamp") else None
                    break
        except APIError as exc:
            log.warning("global lock log lookup failed for %s: %s", name, exc)
        status.actions.append(ActionEvent(kind=GLOBAL_LOCK, actor=actor, timestamp=ts))

    def _last_edit(self, status: AccountStatus) -> None:
        data = self.api.get(action="query", list="usercontribs", ucuser=status.name,
                            uclimit="1", ucprop="timestamp")
        contribs = data["query"].get("usercontribs", [])
        status.last_edit = parse_api_ts(contribs[0]["timestamp"]) if contribs else None
        status.last_edit_checked = True


def _is_lock_entry(entry: dict) -> bool:
    """True if a globalauth log entry locked the account."""
    if entry.get("action") not in (None, "setstatus", "lock", "lockandhid"):
        return False
    if entry.get("action") in ("lock", "lockandhid"):
        return True
    params = entry.get("params") or {}
    added = params.get("added")
    if isinstance(added, list):
        return "locked" in added
    # Legacy format: {"0": "locked", "1": "(none)"}
    return str(params.get("0", "")).find("locked") != -1
