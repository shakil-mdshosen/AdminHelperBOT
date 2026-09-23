"""Builds what the bot writes on the page and in edit summaries.

No Bangla text lives here: every sentence comes from texts.toml ([page] and
[summary]); this module only fills in the $placeholders.
"""

from __future__ import annotations

from typing import List

import mwparserfromhell

from .config import Config
from .logic import Decision
from .parser import RequestInfo
from .status import GLOBAL_BLOCK, GLOBAL_LOCK, LOCAL_BLOCK, ActionEvent
from .timeutil import format_bn_datetime, to_bn_digits

SUMMARY_LIMIT = 490   # MediaWiki cuts summaries at 500 characters


def join_names(items: List[str], cfg: Config) -> str:
    """'ক', 'ক ও খ', 'ক, খ ও গ' (separators from texts.toml)."""
    if len(items) <= 1:
        return "".join(items)
    t = cfg.texts
    return (t.get("page.list_separator").join(items[:-1])
            + t.get("page.list_last_separator") + items[-1])


def _actor(ev: ActionEvent, cfg: Config) -> str:
    if ev.actor:
        return ev.actor
    return cfg.texts.get("page.unknown_admin" if ev.kind == LOCAL_BLOCK
                         else "page.unknown_steward")


def actors_of(decision: Decision, cfg: Config) -> List[str]:
    seen, out = set(), []
    for ev in decision.chosen.values():
        name = _actor(ev, cfg)
        if name not in seen:
            seen.add(name)
            out.append(name)
    return out


def _time(dt, cfg: Config) -> str:
    return format_bn_datetime(dt, cfg.display_tz_offset_minutes)


def _lines(cfg: Config, *lines: str) -> str:
    return "\n".join(cfg.reply_indent + line if i == 0 else line
                     for i, line in enumerate(lines))


# ------------------------------------------------------------------ page text
def done_text(decision: Decision, cfg: Config) -> str:
    t = cfg.texts
    return _lines(cfg,
                  t.render("page.done_line", actors=join_names(actors_of(decision, cfg), cfg)),
                  t.get("page.archive_line"))


def stale_text(decision: Decision, cfg: Config) -> str:
    t = cfg.texts
    subject = t.get("page.stale_subject_many" if len(decision.stale_accounts) > 1
                    else "page.stale_subject_one")
    if decision.last_edit:
        line = t.render("page.stale_line", subject=subject,
                        last_edit=_time(decision.last_edit, cfg))
    else:
        line = t.render("page.stale_line_no_edits", subject=subject)
    if cfg.stale_add_archive_template:
        return _lines(cfg, line, t.get("page.archive_line"))
    return _lines(cfg, line)


def archive_only_text(cfg: Config) -> str:
    return cfg.texts.get("page.archive_only_line")


# ------------------------------------------------------------------ summaries
def _section_link(title: str) -> str:
    plain = mwparserfromhell.parse(title).strip_code().strip()
    return f"/* {plain} */ " if plain else ""


def _summary(cfg: Config, key: str, title: str, details: str, **values) -> str:
    """Render summary *key*; if too long, shorten only the $details part."""
    t = cfg.texts
    link = _section_link(title)
    full = link + t.render(key, details=details, **values)
    if len(full) <= SUMMARY_LIMIT:
        return full
    room = SUMMARY_LIMIT - len(link + t.render(key, details="", **values)) - 1
    return link + t.render(key, details=details[:max(room, 0)] + "…", **values)


def _describe(name: str, ev: ActionEvent, cfg: Config) -> str:
    t = cfg.texts
    when = t.render("summary.when", time=_time(ev.timestamp, cfg)) if ev.timestamp else ""
    if ev.kind == GLOBAL_LOCK:
        key = "summary.action_global_lock"
    elif ev.kind == GLOBAL_BLOCK:
        key = "summary.action_global_block"
    elif ev.partial:
        key = "summary.action_local_partial_block"
    else:
        key = "summary.action_local_block"
    return t.render(key, account=name, actor=_actor(ev, cfg), when=when)


def done_summary(title: str, decision: Decision, cfg: Config) -> str:
    details = cfg.texts.get("summary.details_separator").join(
        _describe(n, ev, cfg) for n, ev in decision.chosen.items())
    return _summary(cfg, "summary.done", title, details,
                    grace=to_bn_digits(str(cfg.done_grace_minutes)))


def stale_summary(title: str, decision: Decision, cfg: Config) -> str:
    t = cfg.texts
    if decision.last_edit:
        info = t.render("summary.stale_last_edit_info",
                        last_edit=_time(decision.last_edit, cfg))
    else:
        info = t.get("summary.stale_no_edit_info")
    details = t.render(
        "summary.stale_details",
        no_action_hours=to_bn_digits(str(cfg.stale_no_action_hours)),
        inactivity_hours=to_bn_digits(str(cfg.stale_inactivity_hours)),
        accounts=join_names(decision.stale_accounts, cfg), last_edit_info=info)
    note = t.get("summary.stale_archive_note") if cfg.stale_add_archive_template else ""
    return _summary(cfg, "summary.stale", title, details, archive_note=note)


def archive_only_summary(info: RequestInfo, cfg: Config) -> str:
    return _summary(cfg, "summary.archive_only", info.section.title, info.decided_by,
                    grace=to_bn_digits(str(cfg.archive_grace_minutes)))
