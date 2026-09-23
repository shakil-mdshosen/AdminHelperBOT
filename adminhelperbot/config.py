"""Bot configuration.

The settings live in config.json at the repository root, which is read
automatically (another file can be given with -c). Keys starting with "_" are
comments. Defaults below apply to anything the file leaves out.

All Bangla text (page messages, edit summaries, template names, keywords …)
lives in texts.toml, not here; see texts.py.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Optional

from . import timeutil
from .texts import Texts, default_texts

DEFAULT_CONFIG_FILE = Path(__file__).resolve().parent.parent / "config.json"


@dataclass
class Config:
    # --- Wiki -------------------------------------------------------------
    api_url: str = "https://bn.wikipedia.org/w/api.php"
    meta_api_url: str = "https://meta.wikimedia.org/w/api.php"
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
    # A request already marked {{করা হয়েছে}}/{{করা হয়নি}} but not archived gets
    # {{subst:সহঅ}} this long after its last comment.
    archive_grace_minutes: int = 10
    stale_no_action_hours: int = 72
    stale_inactivity_hours: int = 60
    # A block/lock made this long *before* the report was posted still counts
    # as the answer to it (e.g. an admin acted while the report was typed).
    action_before_report_tolerance_minutes: int = 60
    count_partial_blocks: bool = True
    max_edits_per_run: int = 25

    # --- Behaviour ----------------------------------------------------------
    archive_decided_requests: bool = True
    stale_add_archive_template: bool = True
    reply_indent: str = ""
    # Timezone offset used when writing times (label is in texts.toml).
    display_tz_offset_minutes: int = 0
    require_block_keywords: bool = True
    # MediaWiki temporary account name pattern on Wikimedia wikis: ~2025-12345-67
    temp_account_regex: str = r"~\d{4}-\d+(?:-\d+)*"

    # --- Files & safety -----------------------------------------------------
    texts_file: Optional[str] = None      # None = adminhelperbot/texts.toml
    # If set, the bot only edits while this page contains a word from
    # [wiki] run_page_ok in texts.toml.
    run_page: Optional[str] = None
    state_file: str = "state.json"
    dry_run: bool = False

    texts: Texts = field(default_factory=default_texts, repr=False)
    source: Optional[str] = None          # the config file that was read

    @classmethod
    def load(cls, path: Optional[str] = None) -> "Config":
        """Read *path*, or config.json at the repository root if it exists."""
        cfg = cls()
        if path is None and DEFAULT_CONFIG_FILE.exists():
            path = str(DEFAULT_CONFIG_FILE)
        cfg.source = path
        if path:
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
            data = {k: v for k, v in data.items() if not k.startswith("_")}
            known = {f.name for f in fields(cls)} - {"texts", "source"}
            unknown = set(data) - known
            if unknown:
                raise ValueError(f"Unknown config keys: {sorted(unknown)}")
            for key, value in data.items():
                setattr(cfg, key, value)
            # Relative file names are relative to the config file's folder.
            base = Path(path).resolve().parent
            for key in ("state_file", "texts_file"):
                value = getattr(cfg, key)
                if value and not Path(value).is_absolute():
                    setattr(cfg, key, str(base / value))
        cfg.username = os.environ.get("ADMINHELPERBOT_USERNAME", cfg.username)
        cfg.password = os.environ.get("ADMINHELPERBOT_PASSWORD", cfg.password)
        if cfg.texts_file:
            cfg.texts = Texts.load(cfg.texts_file)
        timeutil.configure(cfg.texts)
        return cfg
