"""Decide what to do with one request. Pure functions: easy to test."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from .config import Config
from .parser import RequestInfo
from .status import AccountStatus, ActionEvent

DONE = "done"
STALE = "stale"
WAIT = "wait"
SKIP = "skip"


@dataclass
class Decision:
    kind: str
    reason: str = ""
    due: Optional[datetime] = None            # when DONE/STALE becomes allowed
    chosen: Dict[str, ActionEvent] = field(default_factory=dict)
    last_edit: Optional[datetime] = None
    stale_accounts: List[str] = field(default_factory=list)
    pending: Optional[str] = None             # DONE or STALE while waiting


def _sort_key(ev: ActionEvent):
    return (ev.timestamp is None, ev.timestamp or datetime.max)


def evaluate(info: RequestInfo, statuses: Dict[str, AccountStatus],
             now: datetime, cfg: Config,
             first_seen: Optional[datetime] = None) -> Decision:
    if info.is_resolved:
        return Decision(SKIP, f"already closed ({info.resolved_reason})")
    if info.report_time is None:
        return Decision(SKIP, "no signature timestamp found")
    if not info.accounts:
        return Decision(SKIP, "no reported account found")
    if cfg.require_block_keywords and not info.looks_like_block_request:
        return Decision(SKIP, "does not look like a block request")

    threshold = info.report_time - timedelta(
        minutes=cfg.action_before_report_tolerance_minutes)

    chosen: Dict[str, ActionEvent] = {}
    any_action = False
    for acc in info.accounts:
        st = statuses.get(acc.name)
        actions = [a for a in (st.actions if st else [])
                   if cfg.count_partial_blocks or not a.partial]
        if actions:
            any_action = True
        responsive = [a for a in actions
                      if a.timestamp is None or a.timestamp >= threshold]
        if responsive:
            chosen[acc.name] = sorted(responsive, key=_sort_key)[0]

    # ---- 1. every reported account was blocked / locked -> done ----------
    if len(chosen) == len(info.accounts):
        known = [ev.timestamp for ev in chosen.values() if ev.timestamp]
        base = [info.report_time] + known
        if len(known) < len(chosen):
            # Hidden log entry: count the grace period from when we first saw it.
            base.append(first_seen or now)
        due = max(base) + timedelta(minutes=cfg.done_grace_minutes)
        if now >= due:
            return Decision(DONE, "all reported accounts actioned", due, chosen)
        return Decision(WAIT, "waiting for admins to mark as done", due, chosen,
                        pending=DONE)

    # ---- 2. temporary accounts nobody acted on -> stale -----------------
    if not any_action and all(a.is_temp for a in info.accounts):
        edits = []
        for acc in info.accounts:
            st = statuses.get(acc.name)
            if st is None or not st.last_edit_checked:
                return Decision(SKIP, f"last edit of {acc.name} unknown")
            if st.last_edit:
                edits.append(st.last_edit)
        last_edit = max(edits) if edits else None
        due = info.report_time + timedelta(hours=cfg.stale_no_action_hours)
        if last_edit:
            due = max(due, last_edit + timedelta(hours=cfg.stale_inactivity_hours))
        names = [a.name for a in info.accounts]
        if now >= due:
            return Decision(STALE, "no action and temporary account inactive",
                            due, last_edit=last_edit, stale_accounts=names)
        return Decision(WAIT, "stale timers running", due, last_edit=last_edit,
                        stale_accounts=names, pending=STALE)

    if chosen:
        return Decision(SKIP, "only some reported accounts actioned")
    if any_action:
        return Decision(SKIP, "accounts were blocked long before the report")
    return Decision(SKIP, "no action yet (registered account: no stale rule)")
