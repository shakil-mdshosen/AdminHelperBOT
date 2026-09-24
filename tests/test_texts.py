"""texts.toml: the single place for Bangla text."""

import ast
import re
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from adminhelperbot import timeutil
from adminhelperbot.bot import AdminHelperBot
from adminhelperbot.config import Config
from adminhelperbot.texts import DEFAULT_TEXTS_FILE, Texts, TextsError
from adminhelperbot.timeutil import UTC

from .fakewiki import FakeAPI, FakeWiki

PKG = Path(__file__).parent.parent / "adminhelperbot"
BANGLA = re.compile(r"[ঀ-৿]")
DEFAULT = DEFAULT_TEXTS_FILE.read_text(encoding="utf-8")


def write(tmp_path, text):
    p = tmp_path / "texts.toml"
    p.write_text(text, encoding="utf-8")
    return str(p)


def test_no_bangla_strings_in_code():
    """Every Bangla string the bot uses must come from texts.toml.

    Docstrings/comments may show examples; the only allowed literals are the
    Bangla digits and the Bangla Unicode range used in regular expressions.
    """
    allowed = {"০১২৩৪৫৬৭৮৯", "[0-9০-৯]", r"[0-9০-৯\n|]+"}
    offenders = []
    for path in PKG.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        docstrings = {id(n.body[0].value) for n in ast.walk(tree)
                      if isinstance(n, (ast.Module, ast.FunctionDef, ast.ClassDef))
                      and n.body and isinstance(n.body[0], ast.Expr)
                      and isinstance(n.body[0].value, ast.Constant)}
        for node in ast.walk(tree):
            if (isinstance(node, ast.Constant) and isinstance(node.value, str)
                    and id(node) not in docstrings and BANGLA.search(node.value)
                    and node.value not in allowed
                    and not re.fullmatch(r"\(\?<!\[ঀ-৿A-Za-z\]\)", node.value)):
                offenders.append(f"{path.name}:{node.lineno}: {node.value!r}")
    assert offenders == []


def test_default_file_is_valid():
    Texts.load()


def test_custom_texts_change_what_the_bot_writes(tmp_path):
    custom = (DEFAULT
              .replace('done_line = "$actors কর্তৃক {{করা হয়েছে}} '
                       '<small>(স্বয়ংক্রিয় বার্তা)</small> --~~~~"',
                       'done_line = ":{{করা হয়েছে}} — $actors বাধা দিয়েছেন। (বট) --~~~~"')
              .replace('tz_label = "ইউটিসি"', 'tz_label = "UTC"')
              .replace("(স্বয়ংক্রিয় সম্পাদনা)", "[বট]"))
    now = datetime(2026, 9, 23, 13, 0, tzinfo=UTC)
    text = ("== বাধা ==\n{{vandal|X}} [[User:R|R]] 12:00, 23 September 2026 (UTC)\n")
    wiki = FakeWiki("উইকিপিডিয়া:প্রশাসকদের আলোচনাসভা", text, now)
    wiki.block("X", "Admin A", now - timedelta(minutes=30))
    cfg = Config(state_file=str(tmp_path / "s.json"), username="b", password="p",
                 texts_file=write(tmp_path, custom))
    cfg.texts = Texts.load(cfg.texts_file)
    timeutil.configure(cfg.texts)
    try:
        bot = AdminHelperBot(cfg, FakeAPI(wiki), FakeAPI(wiki, meta=True))
        bot.setup()
        bot.run_once()
    finally:
        timeutil.configure(Texts.load())
    assert ":{{করা হয়েছে}} — Admin A বাধা দিয়েছেন। (বট) --~~~~\n{{subst:সহঅ}}" in wiki.text
    summary = wiki.edits[0]["summary"]
    assert summary.endswith("[বট]") and "(২৩ সেপ্টেম্বর ২০২৬, ১২:৩০ (UTC))" in summary


def test_config_load_uses_texts_file(tmp_path):
    custom = DEFAULT.replace('page_title = "উইকিপিডিয়া:প্রশাসকদের আলোচনাসভা"',
                             'page_title = "উইকিপিডিয়া:পরীক্ষা"')
    cfg_file = tmp_path / "c.json"
    cfg_file.write_text('{"texts_file": "%s"}' % write(tmp_path, custom), encoding="utf-8")
    try:
        cfg = Config.load(str(cfg_file))
        assert cfg.texts.get("wiki.page_title") == "উইকিপিডিয়া:পরীক্ষা"
    finally:
        timeutil.configure(Texts.load())


@pytest.mark.parametrize("change, message", [
    (("$actors কর্তৃক", "$actor কর্তৃক"), "page.done_line: unknown placeholder $actor"),
    (('stale_subject_one = "অস্থায়ী অ্যাকাউন্ট"\n', ""), "missing [page] stale_subject_one"),
    (('"নভেম্বর", "ডিসেম্বর"]', '"নভেম্বর"]'), "exactly 12 names"),
    (("tz_label = \"ইউটিসি\"", "tz_label = 5"), "[datetime] tz_label: expected str"),
    (("done_line = \"$actors", "done_line = \"১০$ $actors"), "write $$ for a literal $"),
])
def test_mistakes_are_reported_clearly(tmp_path, change, message):
    old, new = change
    assert old in DEFAULT
    with pytest.raises(TextsError) as exc:
        Texts.load(write(tmp_path, DEFAULT.replace(old, new, 1)))
    assert message in str(exc.value)


def test_toml_syntax_error_is_reported(tmp_path):
    with pytest.raises(TextsError, match="TOML syntax error"):
        Texts.load(write(tmp_path, DEFAULT.replace('page_title = "', 'page_title = ', 1)))


def test_repo_config_json_is_complete_and_loaded_by_default():
    """config.json at the repository root lists every setting and is read
    automatically; it must never hold credentials."""
    import json
    from dataclasses import fields
    path = PKG.parent / "config.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    keys = {k for k in data if not k.startswith("_")}
    expected = {f.name for f in fields(Config)} - {"texts", "source", "username", "password"}
    assert keys == expected
    cfg = Config.load()
    assert cfg.source == str(path.resolve())
    assert cfg.state_file == str(PKG.parent.resolve() / "state.json")


def test_comment_keys_ignored_and_unknown_keys_rejected(tmp_path):
    ok = tmp_path / "ok.json"
    ok.write_text('{"_note": "x", "done_grace_minutes": 7}', encoding="utf-8")
    assert Config.load(str(ok)).done_grace_minutes == 7
    bad = tmp_path / "bad.json"
    bad.write_text('{"done_grace_minutse": 7}', encoding="utf-8")
    with pytest.raises(ValueError, match="done_grace_minutse"):
        Config.load(str(bad))
