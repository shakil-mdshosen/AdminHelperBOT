"""AdminHelperBot main loop."""

from __future__ import annotations

import json
import logging
import os
import re
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, Optional, Set

import mwparserfromhell

from . import messages
from .api import APIError, MediaWikiAPI
from .config import Config
from .logic import DONE, STALE, WAIT, evaluate
from .parser import NoticeboardParser, Section
from .status import AccountStatus, StatusChecker
from .timeutil import SIGNATURE_TS_RE

log = logging.getLogger(__name__)


@dataclass
class PageRevision:
    text: str
    revid: int
    timestamp: str
    start_timestamp: str


def insert_reply(text: str, section: Section, reply: str) -> str:
    """Append *reply* at the end of *section*, keeping surrounding spacing."""
    chunk = text[section.start:section.end]
    stripped = chunk.rstrip()
    trailing = chunk[len(stripped):]
    if not trailing and section.end < len(text):
        trailing = "\n"
    new_chunk = stripped + "\n" + reply + (trailing if trailing else "\n")
    return text[:section.start] + new_chunk + text[section.end:]


class AdminHelperBot:
    def __init__(self, cfg: Config, api: Optional[MediaWikiAPI] = None,
                 meta_api: Optional[MediaWikiAPI] = None):
        self.cfg = cfg
        self.api = api or MediaWikiAPI(cfg.api_url, cfg.user_agent, cfg.maxlag)
        self.meta = meta_api or MediaWikiAPI(cfg.meta_api_url, cfg.user_agent, cfg.maxlag)
        self.checker = StatusChecker(self.api, self.meta)
        self.parser = NoticeboardParser(cfg.resolved_templates, cfg.report_templates,
                                        cfg.resolved_phrases, cfg.block_keywords,
                                        cfg.temp_account_regex)
        self.state = self._load_state()
        self._dry_handled: Set[str] = set()

    # ------------------------------------------------------------------ setup
    def setup(self) -> None:
        if self.cfg.username and self.cfg.password:
            self.api.login(self.cfg.username, self.cfg.password)
        elif not self.cfg.dry_run:
            raise SystemExit("ADMINHELPERBOT_USERNAME / ADMINHELPERBOT_PASSWORD "
                             "are required unless --dry-run is used.")
        self._calibrate()

    def _calibrate(self) -> None:
        """Learn template redirects and what {{subst:সহঅ}} expands to."""
        names = [self.cfg.done_template, self.cfg.archive_template]
        try:
            data = self.api.get(action="query", redirects="1", prop="redirects",
                                rdlimit="max",
                                titles="|".join(f"Template:{n}" for n in names))
            extra = []
            for page in data["query"].get("pages", []):
                extra.append(page["title"])
                extra += [r["title"] for r in page.get("redirects", [])]
            extra = [re.sub(r"^[^:]+:", "", t) for t in extra]
            self.parser.add_resolved_templates(extra)
            log.info("Resolved-template aliases: %s", ", ".join(extra))
        except APIError as exc:
            log.warning("Could not load template redirects: %s", exc)
        try:
            data = self.api.post(action="parse", title=self.cfg.page_title,
                                 text=f"{{{{subst:{self.cfg.archive_template}}}}}",
                                 contentmodel="wikitext", pst="1", onlypst="1")
            expanded = data["parse"]["text"]
            if isinstance(expanded, dict):
                expanded = expanded.get("*", "")
            self._learn_archive_marker(expanded)
        except (APIError, KeyError) as exc:
            log.warning("Could not expand {{subst:%s}}: %s", self.cfg.archive_template, exc)

    # Templates that can appear inside any comment; never treat them as markers.
    _GENERIC_TEMPLATES = {"small", "u", "ping", "re", "reply to", "replyto", "উত্তর",
                          "বট", "bot", "tl", "nowrap", "font", "color"}

    def _learn_archive_marker(self, expanded: str) -> None:
        code = mwparserfromhell.parse(expanded)
        tpls = [str(t.name).strip() for t in code.filter_templates(recursive=True)]
        tpls = [t for t in tpls if not t.lower().startswith("subst:")
                and t.lower() not in self._GENERIC_TEMPLATES]
        if tpls:
            self.parser.add_resolved_templates(tpls)
        # When the template leaves only text/a comment, remember its longest
        # plain fragment (no links, templates or digits) as a text marker.
        skeleton = SIGNATURE_TS_RE.sub(" ", expanded)
        skeleton = re.sub(r"\[\[.*?\]\]|\{\{.*?\}\}|<!--|-->|<[^>]*>", "\n",
                          skeleton, flags=re.S)
        pieces = [p.strip(" \t-–—:;,.()") for p in re.split(r"[0-9০-৯\n|]+", skeleton)]
        pieces = [p for p in pieces if len(p) >= 12 and not re.search(r"[\[\]{}=:]", p)]
        if pieces:
            marker = max(pieces, key=len)
            self.parser.add_resolved_phrases([marker])
            log.info("Archive marker phrase: %r", marker)
        log.info("{{subst:%s}} expands to: %r (marker templates: %s)",
                 self.cfg.archive_template, expanded, tpls)

    # ------------------------------------------------------------------ state
    def _load_state(self) -> Dict[str, dict]:
        try:
            with open(self.cfg.state_file, encoding="utf-8") as fh:
                return json.load(fh)
        except (OSError, ValueError):
            return {}

    def _save_state(self) -> None:
        tmp = self.cfg.state_file + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(self.state, fh, ensure_ascii=False, indent=1)
        os.replace(tmp, self.cfg.state_file)

    def _first_seen(self, key: str, now: datetime) -> datetime:
        entry = self.state.setdefault(key, {})
        if "first_seen" not in entry:
            entry["first_seen"] = now.isoformat()
        return datetime.fromisoformat(entry["first_seen"])

    # ------------------------------------------------------------------ wiki
    def fetch_page(self) -> PageRevision:
        data = self.api.get(action="query", prop="revisions", titles=self.cfg.page_title,
                            rvprop="ids|timestamp|content", rvslots="main")
        page = data["query"]["pages"][0]
        if page.get("missing"):
            raise APIError("missingtitle", self.cfg.page_title)
        rev = page["revisions"][0]
        return PageRevision(rev["slots"]["main"]["content"], rev["revid"],
                            rev["timestamp"], data["curtimestamp"])

    def run_allowed(self) -> bool:
        if not self.cfg.run_page:
            return True
        data = self.api.get(action="query", prop="revisions", titles=self.cfg.run_page,
                            rvprop="content", rvslots="main")
        page = data["query"]["pages"][0]
        if page.get("missing"):
            return False
        content = page["revisions"][0]["slots"]["main"]["content"].strip().lower()
        return any(ok.lower() in content for ok in self.cfg.run_page_ok)

    def save(self, rev: PageRevision, new_text: str, summary: str) -> bool:
        if self.cfg.dry_run:
            log.info("[DRY RUN] would save with summary: %s", summary)
            return True
        try:
            result = self.api.post(
                action="edit", title=self.cfg.page_title, text=new_text,
                summary=summary, bot="1", nocreate="1", watchlist="nochange",
                baserevid=str(rev.revid), basetimestamp=rev.timestamp,
                starttimestamp=rev.start_timestamp,
                token=self.api.csrf_token(),
                **{"assert": self.cfg.assert_mode},
            )
        except APIError as exc:
            if exc.code == "editconflict":
                log.warning("Edit conflict, will retry with fresh text")
                return False
            raise
        edit = result.get("edit", {})
        if edit.get("result") != "Success":
            raise APIError("edit-failed", str(edit))
        log.info("Saved revision %s", edit.get("newrevid"))
        return True

    # ------------------------------------------------------------------ run
    def run_once(self) -> Optional[datetime]:
        """Process the noticeboard once. Returns the next time a WAIT is due."""
        if not self.run_allowed():
            log.warning("Run page %s does not allow editing; skipping", self.cfg.run_page)
            return None
        statuses: Dict[str, AccountStatus] = {}
        next_due: Optional[datetime] = None
        edits = 0
        conflicts = 0
        while True:
            rev = self.fetch_page()
            now = self.api.now()
            requests_ = [r for r in self.parser.parse(rev.text)
                         if not r.is_resolved and r.accounts and r.report_time]
            missing = [a for r in requests_ for a in r.accounts if a.name not in statuses]
            if missing:
                statuses.update(self.checker.fetch(missing))
                now = self.api.now()

            action: Optional[tuple] = None
            next_due = None
            live_keys = set()
            for info in requests_:
                live_keys.add(info.key)
                first_seen = self.state.get(info.key, {}).get("first_seen")
                decision = evaluate(info, statuses, now, self.cfg,
                                    datetime.fromisoformat(first_seen) if first_seen else None)
                if decision.kind == WAIT and decision.pending == DONE and any(
                        ev.timestamp is None for ev in decision.chosen.values()):
                    self._first_seen(info.key, now)
                log.info("[%s] %s -> %s (%s)%s", info.section.title,
                         ", ".join(a.name for a in info.accounts), decision.kind,
                         decision.reason,
                         f", due {decision.due:%Y-%m-%d %H:%M:%S}Z" if decision.due else "")
                if decision.kind == WAIT and decision.due:
                    next_due = decision.due if next_due is None else min(next_due, decision.due)
                if decision.kind in (DONE, STALE) and action is None \
                        and info.key not in self._dry_handled:
                    action = (info, decision)
            self.state = {k: v for k, v in self.state.items() if k in live_keys}
            self._save_state()

            if action is None or edits >= self.cfg.max_edits_per_run:
                return next_due
            info, decision = action
            if decision.kind == DONE:
                reply = messages.done_text(decision, self.cfg)
                summary = messages.done_summary(info.section.title, decision, self.cfg)
            else:
                reply = messages.stale_text(decision, self.cfg)
                summary = messages.stale_summary(info.section.title, decision, self.cfg)
            new_text = insert_reply(rev.text, info.section, reply)
            log.info("Marking [%s] as %s\n  reply: %s\n  summary: %s",
                     info.section.title, decision.kind, reply.replace("\n", " ⏎ "), summary)
            if self.save(rev, new_text, summary):
                edits += 1
                if self.cfg.dry_run:
                    self._dry_handled.add(info.key)
            else:
                conflicts += 1
                if conflicts > 5:
                    log.error("Too many edit conflicts; giving up this round")
                    return next_due
                time.sleep(3)

    def loop(self) -> None:
        interval = timedelta(minutes=self.cfg.check_interval_minutes)
        while True:
            started = self.api.now()
            try:
                next_due = self.run_once()
            except Exception:   # keep the bot alive; log and try again later
                log.exception("Run failed")
                next_due = None
            next_tick = started + interval
            wake = next_tick
            if next_due is not None and next_due < next_tick:
                wake = next_due + timedelta(seconds=5)   # act right when due
            sleep_for = max(15.0, (wake - self.api.now()).total_seconds())
            log.info("Next check at %s (in %.0fs)",
                     (self.api.now() + timedelta(seconds=sleep_for)).strftime("%H:%M:%S"),
                     sleep_for)
            time.sleep(sleep_for)
