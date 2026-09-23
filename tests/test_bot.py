"""End-to-end runs of the bot against the in-memory fake wiki."""

from datetime import datetime, timedelta
from pathlib import Path

import pytest

from adminhelperbot.bot import AdminHelperBot, insert_reply
from adminhelperbot.config import Config
from adminhelperbot.parser import split_sections
from adminhelperbot.timeutil import UTC

from .fakewiki import FakeAPI, FakeWiki

SAMPLE = (Path(__file__).parent / "sample_noticeboard.txt").read_text(encoding="utf-8")
PAGE = "উইকিপিডিয়া:প্রশাসকদের আলোচনাসভা"
NOW = datetime(2026, 9, 23, 13, 0, tzinfo=UTC)


@pytest.fixture
def wiki():
    w = FakeWiki(PAGE, SAMPLE, NOW)
    # Keep the sample's temp accounts "active" unless a test says otherwise.
    for name in ("~2026-10001-01", "~2026-20002-02", "~2026-30003-03"):
        w.contribs[name] = NOW - timedelta(hours=1)
    return w


def make_bot(wiki, tmp_path, **overrides):
    cfg = Config(state_file=str(tmp_path / "state.json"), username="AdminHelperBot",
                 password="x", **overrides)
    bot = AdminHelperBot(cfg, FakeAPI(wiki), FakeAPI(wiki, meta=True))
    bot.setup()
    return bot


def section_text(text, title):
    return next(s.text for s in split_sections(text) if s.title == title)


def test_nothing_to_do_makes_no_edit(wiki, tmp_path):
    bot = make_bot(wiki, tmp_path)
    bot.run_once()
    assert wiki.edits == []


def test_local_block_marked_done_after_ten_minutes(wiki, tmp_path):
    act = datetime(2026, 9, 23, 12, 52, tzinfo=UTC)
    wiki.block("Vandal Account", "Admin A", act)
    bot = make_bot(wiki, tmp_path)

    wiki.clock = act + timedelta(minutes=9, seconds=59)
    due = bot.run_once()
    assert wiki.edits == [] and due == act + timedelta(minutes=10)

    wiki.clock = act + timedelta(minutes=10)
    bot.run_once()
    assert len(wiki.edits) == 1
    sec = section_text(wiki.text, "ব্যবহারকারী বাধাদানের অনুরোধ")
    assert sec.endswith(
        "Admin A কর্তৃক {{করা হয়েছে}} <small>(স্বয়ংক্রিয় বট বার্তা)</small> --~~~~\n"
        "{{subst:সহঅ}}\n\n")
    e = wiki.edits[0]
    assert e["summary"].startswith("/* ব্যবহারকারী বাধাদানের অনুরোধ */ বট:")
    assert "Vandal Account-কে প্রশাসক Admin A স্থানীয়ভাবে বাধা দিয়েছেন" in e["summary"]
    assert "(স্বয়ংক্রিয় সম্পাদনা)" in e["summary"]
    assert len(e["summary"]) <= 500
    assert e["bot"] == "1" and e["assert"] == "bot" and e["nocreate"] == "1"

    # Second run: the request now carries {{করা হয়েছে}} -> no duplicate edit.
    wiki.clock += timedelta(minutes=5)
    bot.run_once()
    assert len(wiki.edits) == 1


def test_only_the_target_section_changes(wiki, tmp_path):
    act = NOW - timedelta(hours=1)
    wiki.block("Vandal Account", "Admin A", act)
    before = wiki.text
    make_bot(wiki, tmp_path).run_once()
    old = split_sections(before)
    new = split_sections(wiki.text)
    assert before[:old[0].start] == wiki.text[:new[0].start]
    for o, n in zip(old, new):
        if o.title != "ব্যবহারকারী বাধাদানের অনুরোধ":
            assert o.text == n.text


def test_global_lock_and_temp_account_steward_names(wiki, tmp_path):
    t1 = datetime(2026, 9, 23, 11, 30, tzinfo=UTC)
    t2 = datetime(2026, 9, 23, 11, 45, tzinfo=UTC)
    wiki.lock("Cross Wiki Spammer", "Steward One", t1)
    wiki.gblock("~2026-20002-02", "Steward Two", t2)
    bot = make_bot(wiki, tmp_path)
    bot.run_once()
    assert len(wiki.edits) == 1
    sec = section_text(wiki.text, "বৈশ্বিকভাবে লক হওয়া অ্যাকাউন্ট")
    assert "Steward One ও Steward Two কর্তৃক {{করা হয়েছে}}" in sec
    s = wiki.edits[0]["summary"]
    assert "স্টুয়ার্ড Steward One বৈশ্বিকভাবে লক করেছেন" in s
    assert "স্টুয়ার্ড Steward Two বৈশ্বিকভাবে বাধা দিয়েছেন" in s


def test_stale_temp_account(wiki, tmp_path):
    # Reported 20 Sep 10:00; last edit 20 Sep 09:15 -> stale at 23 Sep 10:00.
    wiki.contribs["~2026-10001-01"] = datetime(2026, 9, 20, 9, 15, tzinfo=UTC)
    wiki.clock = datetime(2026, 9, 23, 9, 59, 59, tzinfo=UTC)
    bot = make_bot(wiki, tmp_path)
    due = bot.run_once()
    assert wiki.edits == [] and due == datetime(2026, 9, 23, 10, 0, tzinfo=UTC)
    wiki.clock = datetime(2026, 9, 23, 10, 0, tzinfo=UTC)
    bot.run_once()
    assert len(wiki.edits) == 1
    sec = section_text(wiki.text, "অস্থায়ী অ্যাকাউন্ট ~2026-10001-01 কে বাধাদান")
    assert ("বাধা দেওয়ার প্রয়োজন নেই, অস্থায়ী অ্যাকাউন্ট থেকে সর্বশেষ সম্পাদনা "
            "২০ সেপ্টেম্বর ২০২৬, ০৯:১৫ (ইউটিসি) টায় হয়েছে। "
            "<small>(স্বয়ংক্রিয় বট বার্তা)</small> --~~~~\n{{subst:সহঅ}}\n") in sec
    s = wiki.edits[0]["summary"]
    assert "অপ্রয়োজনীয়" in s and "~2026-10001-01" in s and len(s) <= 500
    assert "{{সহঅ}}" in s
    # Idempotent.
    wiki.clock += timedelta(minutes=5)
    bot.run_once()
    assert len(wiki.edits) == 1


def test_edit_conflict_is_retried_on_fresh_text(wiki, tmp_path, monkeypatch):
    monkeypatch.setattr("adminhelperbot.bot.time.sleep", lambda s: None)
    wiki.block("Vandal Account", "Admin A", NOW - timedelta(hours=1))
    wiki.conflict_next_edit = True
    make_bot(wiki, tmp_path).run_once()
    assert len(wiki.edits) == 1


def test_admin_marks_done_during_grace_period(wiki, tmp_path):
    """Admin writes {{Done}} but forgets {{subst:সহঅ}}: bot adds only that."""
    act = NOW - timedelta(minutes=5)
    wiki.block("Vandal Account", "Admin A", act)
    bot = make_bot(wiki, tmp_path)
    bot.run_once()
    wiki.text = wiki.text.replace(
        ":দেখছি।", ":{{Done}} দেখছি।")         # an admin closes it using a redirect
    wiki.clock = act + timedelta(minutes=15)
    bot.run_once()
    assert len(wiki.edits) == 1
    sec = section_text(wiki.text, "ব্যবহারকারী বাধাদানের অনুরোধ")
    assert sec.endswith("(ইউটিসি)\n{{subst:সহঅ}}\n\n")
    assert "কর্তৃক {{করা হয়েছে}}" not in sec


def test_dry_run_never_edits(wiki, tmp_path):
    wiki.block("Vandal Account", "Admin A", NOW - timedelta(hours=1))
    wiki.contribs["~2026-10001-01"] = datetime(2026, 9, 1, tzinfo=UTC)
    bot = make_bot(wiki, tmp_path, dry_run=True)
    bot.run_once()
    assert wiki.edits == []


def test_run_page_switch(wiki, tmp_path):
    wiki.block("Vandal Account", "Admin A", NOW - timedelta(hours=1))
    make_bot(wiki, tmp_path, run_page="ব্যবহারকারী:AdminHelperBot/চালু").run_once()
    assert wiki.edits == []     # page missing -> bot stays off


def test_several_requests_in_one_run(wiki, tmp_path):
    wiki.block("Vandal Account", "Admin A", NOW - timedelta(hours=1))
    wiki.block("~2026-30003-03", "Admin B", NOW - timedelta(minutes=30))
    make_bot(wiki, tmp_path).run_once()
    assert len(wiki.edits) == 2
    assert "Admin B কর্তৃক {{করা হয়েছে}}" in section_text(wiki.text, "~2026-30003-03")


def test_learned_archive_marker(wiki, tmp_path):
    bot = make_bot(wiki, tmp_path)
    assert "সংগ্রহশালাভুক্তির জন্য প্রস্তুত" in bot.parser.archive_phrases
    assert "done" in bot.parser.decision_templates          # redirect of করা হয়েছে
    assert "কহ" in bot.parser.decision_templates
    assert "সমাধান হওয়া" in bot.parser.archive_templates    # redirect of সহঅ


def test_insert_reply_last_section_without_newline():
    text = "== a ==\nfoo\n== b ==\nbar"
    secs = split_sections(text)
    assert insert_reply(text, secs[1], "R") == "== a ==\nfoo\n== b ==\nbar\nR\n"
    assert insert_reply(text, secs[0], "R") == "== a ==\nfoo\nR\n== b ==\nbar"


def test_loop_wakes_right_when_due(wiki, tmp_path, monkeypatch):
    """Checks run every 5 min, but a due request is handled within seconds."""
    act = NOW + timedelta(minutes=1)            # admin blocks at 13:01
    wiki.block("Vandal Account", "Admin A", act)
    wakeups = []

    class Stop(Exception):
        pass

    def fake_sleep(seconds):
        wakeups.append(wiki.clock)
        wiki.clock += timedelta(seconds=seconds)
        if len(wakeups) > 6:
            raise Stop

    monkeypatch.setattr("adminhelperbot.bot.time.sleep", fake_sleep)
    bot = make_bot(wiki, tmp_path)
    with pytest.raises(Stop):
        bot.loop()
    edit_times = [e["basetimestamp"] for e in wiki.edits]
    assert len(edit_times) == 1
    # due at 13:11:00 -> the bot wakes at 13:11:05 and saves then
    assert wiki.rev_ts == act + timedelta(minutes=10, seconds=5)
    # first wake-ups follow the regular 5-minute rhythm
    assert wakeups[0] == NOW and wakeups[1] == NOW + timedelta(minutes=5)


# ------------------------------------------------ decided but not archived
DECIDED = ("== পুরোনো অনুরোধ ==\n{{vandal|X}} বাধা দিন। [[User:R|R]] "
           "10:00, 23 September 2026 (UTC)\n"
           ":{{করা হয়নি}} প্রয়োজন নেই। [[User:Admin B|Admin B]] "
           "12:40, 23 September 2026 (UTC)\n")


def decided_wiki(text=DECIDED):
    return FakeWiki(PAGE, "{{/শীর্ষ}}\n\n" + text, NOW)


def test_decided_request_gets_only_archive_template(tmp_path):
    w = decided_wiki()
    bot = make_bot(w, tmp_path)
    w.clock = datetime(2026, 9, 23, 12, 49, 59, tzinfo=UTC)   # last comment 12:40
    assert bot.run_once() == datetime(2026, 9, 23, 12, 50, tzinfo=UTC)
    assert w.edits == []
    w.clock = datetime(2026, 9, 23, 12, 50, tzinfo=UTC)
    bot.run_once()
    assert len(w.edits) == 1
    assert w.text.endswith("(UTC)\n{{subst:সহঅ}}\n")
    assert w.edits[0]["summary"] == (
        "/* পুরোনো অনুরোধ */ বট: অনুরোধটি আগেই {{করা হয়নি}} দিয়ে চিহ্নিত করা হয়েছে, "
        "কিন্তু সংগ্রহশালাভুক্তির টেমপ্লেট যোগ করা হয়নি; শেষ মন্তব্যের ১০ মিনিট পরেও "
        "কেউ যোগ না করায় স্বয়ংক্রিয়ভাবে {{সহঅ}} যোগ করা হলো। (স্বয়ংক্রিয় সম্পাদনা)")
    w.clock += timedelta(minutes=5)          # the literal {{subst:সহঅ}} counts too
    bot.run_once()
    assert len(w.edits) == 1


def test_later_comment_restarts_archive_wait(tmp_path):
    w = decided_wiki(DECIDED + "::ধন্যবাদ। [[User:R|R]] 12:55, 23 September 2026 (UTC)\n")
    w.clock = datetime(2026, 9, 23, 13, 4, tzinfo=UTC)
    assert make_bot(w, tmp_path).run_once() == datetime(2026, 9, 23, 13, 5, tzinfo=UTC)
    assert w.edits == []


def test_unsigned_decision_waits_from_first_seen(tmp_path):
    text = DECIDED.replace(":{{করা হয়নি}} প্রয়োজন নেই। [[User:Admin B|Admin B]] "
                           "12:40, 23 September 2026 (UTC)", "{{done}}")
    w = decided_wiki(text)                   # only the 10:00 signature, before {{done}}
    bot = make_bot(w, tmp_path)
    bot.run_once()                           # first seen at 13:00
    w.clock = NOW + timedelta(minutes=9, seconds=59)
    bot.run_once()
    assert w.edits == []
    w.clock = NOW + timedelta(minutes=10)
    bot.run_once()
    assert len(w.edits) == 1


def test_already_archived_and_doing_are_not_touched(tmp_path):
    archived = DECIDED + ("<!--x-->{{সমাধান হওয়া অনুচ্ছেদ|1=—[[User:Admin B|Admin B]] "
                          "12:41, 23 September 2026 (UTC)|t=20260923124100}}<!--y-->\n")
    doing = ("== চলমান ==\n{{vandal|Y}} বাধা দিন। [[User:R|R]] 10:00, 23 September 2026 (UTC)\n"
             ":{{Doing}} [[User:Admin B|Admin B]] 10:05, 23 September 2026 (UTC)\n")
    commented = ("== মন্তব্যে ==\n{{vandal|Z}} বাধা দিন। [[User:R|R]] 10:00, 23 September 2026 (UTC)\n"
                 "<!-- {{done}} -->\n")
    w = decided_wiki(archived + doing + commented)
    bot = make_bot(w, tmp_path)
    w.clock = NOW + timedelta(hours=5)
    bot.run_once()
    assert w.edits == []


def test_archiving_decided_requests_can_be_turned_off(tmp_path):
    w = decided_wiki()
    make_bot(w, tmp_path, archive_decided_requests=False).run_once()
    assert w.edits == []
