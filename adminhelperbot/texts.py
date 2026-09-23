"""Loads every Bangla text the bot uses from one TOML file (texts.toml)."""

from __future__ import annotations

import tomllib
from pathlib import Path
from string import Template
from typing import Any, Dict, Optional

DEFAULT_TEXTS_FILE = Path(__file__).with_name("texts.toml")

# Placeholders each text may use. Anything else is reported at startup.
PLACEHOLDERS: Dict[str, set] = {
    "page.done_line": {"actors"},
    "page.stale_line": {"subject", "last_edit"},
    "page.stale_line_no_edits": {"subject"},
    "summary.done": {"details", "grace"},
    "summary.action_local_block": {"account", "actor", "when"},
    "summary.action_local_partial_block": {"account", "actor", "when"},
    "summary.action_global_lock": {"account", "actor", "when"},
    "summary.action_global_block": {"account", "actor", "when"},
    "summary.when": {"time"},
    "summary.stale": {"details", "archive_note"},
    "summary.stale_details": {"no_action_hours", "inactivity_hours", "accounts",
                              "last_edit_info"},
    "summary.stale_last_edit_info": {"last_edit"},
    "summary.archive_only": {"details", "grace"},
    "datetime.format": {"day", "month", "year", "hour", "minute", "tz"},
}


class TextsError(ValueError):
    pass


class Texts:
    """Read-only access to texts.toml: texts.get("page.done_line")."""

    def __init__(self, data: Dict[str, Any], source: str = "texts.toml"):
        self.data = data
        self.source = source
        self._validate()

    @classmethod
    def load(cls, path: Optional[str] = None) -> "Texts":
        path = Path(path) if path else DEFAULT_TEXTS_FILE
        try:
            with open(path, "rb") as fh:
                data = tomllib.load(fh)
        except tomllib.TOMLDecodeError as exc:
            raise TextsError(f"{path}: TOML syntax error: {exc}") from exc
        return cls(data, str(path))

    def get(self, key: str) -> Any:
        section, _, name = key.partition(".")
        try:
            return self.data[section][name]
        except KeyError:
            raise TextsError(f"{self.source}: missing [{section}] {name}") from None

    def render(self, key: str, **values: Any) -> str:
        """Fill $placeholders of text *key*."""
        return Template(self.get(key)).substitute(
            {k: str(v) for k, v in values.items()})

    # ------------------------------------------------------------------
    def _validate(self) -> None:
        default = tomllib.loads(DEFAULT_TEXTS_FILE.read_text(encoding="utf-8"))
        problems = []
        for section, entries in default.items():
            for name, value in entries.items():
                key = f"{section}.{name}"
                try:
                    mine = self.get(key)
                except TextsError as exc:
                    problems.append(str(exc))
                    continue
                if type(mine) is not type(value):
                    problems.append(f"[{section}] {name}: expected {type(value).__name__}")
        for key, allowed in PLACEHOLDERS.items():
            try:
                tpl = Template(self.get(key))
                tpl.substitute({name: "x" for name in allowed})
            except TextsError:
                continue    # already reported
            except KeyError as exc:
                problems.append(f"{key}: unknown placeholder ${exc.args[0]} "
                                f"(allowed: {', '.join('$' + a for a in sorted(allowed))})")
            except ValueError as exc:
                problems.append(f"{key}: {exc} (write $$ for a literal $)")
        if len(self.get("datetime.months")) != 12:
            problems.append("[datetime] months: exactly 12 names are needed")
        if problems:
            raise TextsError(f"Problems in {self.source}:\n  " + "\n  ".join(problems))


_default: Optional[Texts] = None


def default_texts() -> Texts:
    global _default
    if _default is None:
        _default = Texts.load()
    return _default
