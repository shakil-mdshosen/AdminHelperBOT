"""Bot configuration. Every value can be overridden from a JSON file."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, fields
from typing import List, Optional


@dataclass
class Config:
    # --- Wiki -------------------------------------------------------------
    api_url: str = "https://bn.wikipedia.org/w/api.php"
    meta_api_url: str = "https://meta.wikimedia.org/w/api.php"
    page_title: str = "উইকিপিডিয়া:প্রশাসকদের আলোচনাসভা"
    user_agent: str = (
        "AdminHelperBot/1.0 (https://github.com/shakil-mdshosen/AdminHelperBOT) "
        "python-requests"
    )
    # Credentials normally come from the environment (BotPassword).
    username: Optional[str] = None
    password: Optional[str] = None
    # "bot" once the account has the bot flag; "user" while testing.
    assert_mode: str = "bot"
    maxlag: int = 5

    # --- Timing (minutes / hours) -------------------------------------------
    check_interval_minutes: int = 5
    done_grace_minutes: int = 10
    stale_no_action_hours: int = 72
    stale_inactivity_hours: int = 60
    # A block/lock made this long *before* the report was posted still counts
    # as the answer to it (e.g. an admin acted while the report was typed).
    action_before_report_tolerance_minutes: int = 60
    count_partial_blocks: bool = True
    max_edits_per_run: int = 25

    # --- Output text --------------------------------------------------------
    done_template: str = "করা হয়েছে"
    archive_template: str = "সহঅ"
    reply_indent: str = ""
    automated_note: str = "<small>(স্বয়ংক্রিয় বট বার্তা)</small>"
    stale_add_archive_template: bool = False
    # Timezone used when writing LAST EDIT DATE TIME (bnwiki signatures: UTC).
    display_tz_offset_minutes: int = 0
    display_tz_label: str = "ইউটিসি"
    summary_suffix: str = "(স্বয়ংক্রিয় সম্পাদনা)"

    # --- Detection ----------------------------------------------------------
    # Templates that already close a request (redirects are added at runtime).
    resolved_templates: List[str] = field(default_factory=lambda: [
        "করা হয়েছে", "করা হয়নি", "সম্পন্ন", "সম্পন্ন হয়েছে", "হয়েছে",
        "done", "not done", "notdone", "already done", "alreadydone",
        "resolved", "সমাধান হয়েছে", "stale", "বাসি", "withdrawn", "প্রত্যাহার",
        "সহঅ", "archive top", "atop", "closed rfc top", "archive-top",
    ])
    # Plain-text phrases that also mark a request as closed.
    resolved_phrases: List[str] = field(default_factory=lambda: [
        "বাধা দেওয়ার প্রয়োজন নেই",
    ])
    # Templates whose first positional parameter is a reported account.
    report_templates: List[str] = field(default_factory=lambda: [
        "userlinks", "user", "user5", "user-multi", "vandal", "ipvandal",
        "userlinks-min", "user-uaa", "checkuser", "checkip", "iplinks",
        "ip", "ব্যবহারকারী", "ব্যবহারকারী সংযোগ", "ব্যবহারকারী লিংক",
        "ব্যবহারকারী লিঙ্ক", "ধ্বংসপ্রবণতা", "ধ্বংসপ্রবণ", "অস্থায়ী অ্যাকাউন্ট",
        "ta", "tempuser", "temp user", "temporary account",
    ])
    # A section is only treated as a block request when one of these words
    # appears in its heading or first comment, or a report template is used.
    require_block_keywords: bool = True
    block_keywords: List[str] = field(default_factory=lambda: [
        "বাধা", "ব্লক", "block", "লক", "lock", "ধ্বংসপ্রবণ", "ধ্বংসাত্মক",
        "ভ্যান্ডাল", "ভাণ্ডাল", "vandal", "স্প্যাম", "spam", "সকপাপেট",
        "sock", "অস্থায়ী অ্যাকাউন্ট", "অবরুদ্ধ", "নিষেধাজ্ঞা", "lta",
    ])
    # MediaWiki temporary account name pattern on Wikimedia wikis: ~2025-12345-67
    temp_account_regex: str = r"~\d{4}-\d+(?:-\d+)*"

    # --- Safety -------------------------------------------------------------
    # If set, the bot only edits while this page contains one of run_page_ok.
    run_page: Optional[str] = None
    run_page_ok: List[str] = field(default_factory=lambda: ["চালু", "true", "on"])
    state_file: str = "state.json"
    dry_run: bool = False

    @classmethod
    def load(cls, path: Optional[str] = None) -> "Config":
        cfg = cls()
        if path:
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
            known = {f.name for f in fields(cls)}
            unknown = set(data) - known
            if unknown:
                raise ValueError(f"Unknown config keys: {sorted(unknown)}")
            for key, value in data.items():
                setattr(cfg, key, value)
        cfg.username = os.environ.get("ADMINHELPERBOT_USERNAME", cfg.username)
        cfg.password = os.environ.get("ADMINHELPERBOT_PASSWORD", cfg.password)
        return cfg
