"""Bangla text written to the page and edit summaries."""

from __future__ import annotations

from typing import List

import mwparserfromhell

from .config import Config
from .logic import Decision
from .status import GLOBAL_BLOCK, GLOBAL_LOCK, LOCAL_BLOCK, ActionEvent
from .timeutil import format_bn_datetime, to_bn_digits

SUMMARY_LIMIT = 490   # MediaWiki cuts summaries at 500 characters


def join_bn(items: List[str]) -> str:
    """'ক', 'ক ও খ', 'ক, খ ও গ'."""
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + " ও " + items[-1]


def _actor(ev: ActionEvent) -> str:
    if ev.actor:
        return ev.actor
    return "প্রশাসক" if ev.kind == LOCAL_BLOCK else "স্টুয়ার্ড"


def actors_of(decision: Decision) -> List[str]:
    seen, out = set(), []
    for ev in decision.chosen.values():
        name = _actor(ev)
        if name not in seen:
            seen.add(name)
            out.append(name)
    return out


def done_text(decision: Decision, cfg: Config) -> str:
    note = f" {cfg.automated_note}" if cfg.automated_note else ""
    return (f"{cfg.reply_indent}{join_bn(actors_of(decision))} কর্তৃক "
            f"{{{{{cfg.done_template}}}}}{note} --~~~~\n"
            f"{{{{subst:{cfg.archive_template}}}}}")


def stale_text(decision: Decision, cfg: Config) -> str:
    note = f" {cfg.automated_note}" if cfg.automated_note else ""
    subject = ("অস্থায়ী অ্যাকাউন্টগুলো" if len(decision.stale_accounts) > 1
               else "অস্থায়ী অ্যাকাউন্ট")
    if decision.last_edit:
        when = format_bn_datetime(decision.last_edit, cfg.display_tz_offset_minutes,
                                  cfg.display_tz_label)
        line = (f"বাধা দেওয়ার প্রয়োজন নেই, {subject} থেকে সর্বশেষ সম্পাদনা "
                f"{when} টায় হয়েছে।")
    else:
        line = f"বাধা দেওয়ার প্রয়োজন নেই, {subject} থেকে কোনো সম্পাদনা হয়নি।"
    text = f"{cfg.reply_indent}{line}{note} --~~~~"
    if cfg.stale_add_archive_template:
        text += f"\n{{{{subst:{cfg.archive_template}}}}}"
    return text


def _section_link(title: str) -> str:
    plain = mwparserfromhell.parse(title).strip_code().strip()
    return f"/* {plain} */ " if plain else ""


def _describe(name: str, ev: ActionEvent, cfg: Config) -> str:
    who = _actor(ev)
    when = ""
    if ev.timestamp:
        when = " (" + format_bn_datetime(ev.timestamp, cfg.display_tz_offset_minutes,
                                         cfg.display_tz_label) + ")"
    if ev.kind == GLOBAL_LOCK:
        return f"{name} অ্যাকাউন্টটি স্টুয়ার্ড {who} বৈশ্বিকভাবে লক করেছেন{when}"
    if ev.kind == GLOBAL_BLOCK:
        return f"{name}-কে স্টুয়ার্ড {who} বৈশ্বিকভাবে বাধা দিয়েছেন{when}"
    kind = "আংশিক বাধা" if ev.partial else "বাধা"
    return f"{name}-কে প্রশাসক {who} স্থানীয়ভাবে {kind} দিয়েছেন{when}"


def _fit(summary: str, core: str, details: str, tail: str) -> str:
    if len(summary) <= SUMMARY_LIMIT:
        return summary
    room = SUMMARY_LIMIT - len(core) - len(tail) - 1
    return core + (details[:max(room, 0)] + "…" if room > 0 else "") + tail


def done_summary(title: str, decision: Decision, cfg: Config) -> str:
    details = "; ".join(_describe(n, ev, cfg) for n, ev in decision.chosen.items())
    grace = to_bn_digits(str(cfg.done_grace_minutes))
    core = (f"{_section_link(title)}বট: অনুরোধটি সম্পন্ন হিসেবে চিহ্নিত ও "
            f"সংগ্রহশালাভুক্তির জন্য প্রস্তুত করা হলো — ")
    tail = (f"। পদক্ষেপ নেওয়ার {grace} মিনিট পরেও কেউ চিহ্নিত না করায় "
            f"স্বয়ংক্রিয়ভাবে {{{{{cfg.done_template}}}}} ও "
            f"{{{{{cfg.archive_template}}}}} যোগ করা হয়েছে। {cfg.summary_suffix}")
    return _fit(core + details + tail, core, details, tail)


def stale_summary(title: str, decision: Decision, cfg: Config) -> str:
    names = join_bn(decision.stale_accounts)
    no_action = to_bn_digits(str(cfg.stale_no_action_hours))
    inactive = to_bn_digits(str(cfg.stale_inactivity_hours))
    core = f"{_section_link(title)}বট: অনুরোধটি অপ্রয়োজনীয় হিসেবে চিহ্নিত — "
    if decision.last_edit:
        last = "সর্বশেষ সম্পাদনা: " + format_bn_datetime(
            decision.last_edit, cfg.display_tz_offset_minutes, cfg.display_tz_label)
    else:
        last = "অ্যাকাউন্টটি থেকে কোনো সম্পাদনা নেই"
    details = (f"রিপোর্ট করার {no_action} ঘণ্টার মধ্যে অস্থায়ী অ্যাকাউন্ট {names}-এর "
               f"বিরুদ্ধে কোনো প্রশাসক বা স্টুয়ার্ড পদক্ষেপ নেননি এবং গত {inactive} "
               f"ঘণ্টায় কোনো সম্পাদনা হয়নি ({last})")
    tail = f"। {cfg.summary_suffix}"
    return _fit(core + details + tail, core, details, tail)
