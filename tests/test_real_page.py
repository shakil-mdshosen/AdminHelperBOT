"""The bot against a real copy of উইকিপিডিয়া:প্রশাসকদের আলোচনাসভা (Sep 2026).

Every section of the real page is checked: what the bot understands from it
and what it writes (or does not write) in realistic situations.
"""

from datetime import datetime, timedelta
from pathlib import Path

import pytest

from adminhelperbot.bot import AdminHelperBot
from adminhelperbot.config import Config
from adminhelperbot.parser import NoticeboardParser, split_sections
from adminhelperbot.timeutil import UTC

from .fakewiki import FakeAPI, FakeWiki

REAL = (Path(__file__).parent / "real_noticeboard.txt").read_text(encoding="utf-8")
PAGE = "উইকিপিডিয়া:প্রশাসকদের আলোচনাসভা"
NOW = datetime(2026, 9, 23, 6, 0, tzinfo=UTC)
# What {{subst:সহঅ}} left on the real page:
REAL_SUBST = ("<!--4fd29918-->{{সমাধান হওয়া অনুচ্ছেদ|1=—[[ব্যবহারকারী:AdminHelperBot|"
              "AdminHelperBot]] ০৬:০০, ২৩ সেপ্টেম্বর ২০২৬ (ইউটিসি)|t=20260923060000}}"
              "<!--e4807be0-->")
TEMP = "~2026-35944-61"
NEPHRO = "[[Nephrozoa]] পাতাটি পুনর্নির্দেশ হিসেবে তৈরি করুন"
# The real page with Nephrozoa (the only "decided but not archived" request)
# already archived, so the other scenarios can be looked at one by one.
BASE = REAL.rstrip("\n") + "\n" + REAL_SUBST + "\n"


def parser():
    c = Config()
    return NoticeboardParser(c.texts, c.temp_account_regex)


@pytest.fixture
def wiki():
    w = FakeWiki(PAGE, BASE, NOW)
    w.subst_output = REAL_SUBST
    w.contribs[TEMP] = NOW - timedelta(hours=2)          # active unless a test says so
    return w


def make_bot(wiki, tmp_path):
    cfg = Config(state_file=str(tmp_path / "state.json"), username="AdminHelperBot",
                 password="x")
    bot = AdminHelperBot(cfg, FakeAPI(wiki), FakeAPI(wiki, meta=True))
    bot.setup()
    return bot


def sections(text):
    return split_sections(text)


def changed_sections(before, after):
    old, new = sections(before), sections(after)
    assert len(old) == len(new)
    return [(o, n) for o, n in zip(old, new) if o.text != n.text]


# ------------------------------------------------------------ understanding
def test_every_real_section_is_understood():
    def state(i):
        return "archived" if i.is_archived else "decided" if i.is_decided else ""
    got = [(i.section.title, state(i), i.looks_like_block_request,
            [a.name for a in i.accounts]) for i in parser().parse(REAL)]
    assert got == [
        ("টেমপ্লেট:Infobox bodybuilder তৈরি", "", False, []),
        ("টেমপ্লেট:Infobox handball biography", "", False, []),
        ("বাধাদানের অনুরোধঃ ~2026-32288-48", "archived", True, ["~2026-32288-48"]),
        ("পুনরায় ফিরিয়ে দেওয়ার জন্য বিনীত ও জোরালো আবেদন", "", False, []),
        ("বাধাদানের অনুরোধ: Swarup Das Official", "", True, ["Swarup Das Official"]),
        ("ব্যবস্থা নিন", "", False, []),
        ("বাধাদানের অনুরোধ [[বিশেষ:অবদান/~2026-35944-61|~2026-35944-61]]", "", True, [TEMP]),
        ("বাধাদানের অনুরোধ", "", True, ["Muriwala Debu"]),
        ("বাধাদানের অনুরোধ", "", True,
         ["Զեմւկո Բանգլադեշվչոտրցևղձճծընէե (ՀաՒարոդիմ)"]),
        ("বাধাদানের অনুরোধ: Integrity2020", "", True, ["Integrity2020"]),
        ("বাধাদানের অনুরোধ: Mr. Souraj ও Mr. Ranju Maity", "", True,
         ["Mr. Souraj", "Mr. Ranju Maity"]),
        ("বীর মুক্তিযোদ্ধা কমান্ডার মোঃ আরজু মিয়া খসড়া নিবন্ধ এবং নির্ভরযোগ্য সূত্র প্রসঙ্গে",
         "", False, []),
        ("নিবন্ধ অপসারণ প্রস্তাবনায় অপব্যবহার সম্পর্কে প্রশাসকদের পর্যালোচনার অনুরোধ",
         "", False, ["Sàádî"]),
        (NEPHRO, "decided", False, []),
    ]


def test_report_times_are_the_reporters_signatures():
    times = {i.section.title: i.report_time for i in parser().parse(REAL)}
    assert times["বাধাদানের অনুরোধ: Swarup Das Official"] == datetime(2026, 6, 15, 21, 16, tzinfo=UTC)
    assert times["বাধাদানের অনুরোধ: Integrity2020"] == datetime(2026, 7, 19, 13, 27, tzinfo=UTC)
    # reporter signed 13:43; a reply is (oddly) dated 11:30 — the report wins
    assert times["[[Nephrozoa]] পাতাটি পুনর্নির্দেশ হিসেবে তৈরি করুন"] == \
        datetime(2026, 8, 18, 13, 43, tzinfo=UTC)


def test_calibration_learns_real_resolved_template(wiki, tmp_path):
    bot = make_bot(wiki, tmp_path)
    assert "সমাধান হওয়া অনুচ্ছেদ" in bot.parser.archive_templates


# ------------------------------------------------------------ behaviour
def test_nothing_actioned_means_no_edits(wiki, tmp_path):
    make_bot(wiki, tmp_path).run_once()
    assert wiki.edits == []


def test_local_block_marked_with_admin_name(wiki, tmp_path):
    act = NOW - timedelta(minutes=10)
    wiki.block("Swarup Das Official", "Ferdous", act)
    make_bot(wiki, tmp_path).run_once()
    assert len(wiki.edits) == 1
    [(old, new)] = changed_sections(BASE, wiki.text)
    assert old.title == "বাধাদানের অনুরোধ: Swarup Das Official"
    assert new.text == old.text.rstrip() + (
        "\nFerdous কর্তৃক {{করা হয়েছে}} <small>(স্বয়ংক্রিয় বার্তা)</small> --~~~~"
        "\n{{subst:সহঅ}}\n\n")
    assert wiki.edits[0]["summary"] == (
        "/* বাধাদানের অনুরোধ: Swarup Das Official */ বট: অনুরোধটি সম্পন্ন হিসেবে চিহ্নিত ও "
        "সংগ্রহশালাভুক্তির জন্য প্রস্তুত করা হলো — Swarup Das Official-কে প্রশাসক Ferdous "
        "স্থানীয়ভাবে বাধা দিয়েছেন (২৩ সেপ্টেম্বর ২০২৬, ০৫:৫০ (ইউটিসি))। পদক্ষেপ নেওয়ার "
        "১০ মিনিট পরেও কেউ চিহ্নিত না করায় স্বয়ংক্রিয়ভাবে {{করা হয়েছে}} ও {{সহঅ}} "
        "যোগ করা হয়েছে। (স্বয়ংক্রিয় সম্পাদনা)")


def test_not_before_ten_minutes(wiki, tmp_path):
    wiki.block("Swarup Das Official", "Ferdous", NOW - timedelta(minutes=9, seconds=59))
    make_bot(wiki, tmp_path).run_once()
    assert wiki.edits == []


def test_heading_names_with_lock_and_block(wiki, tmp_path):
    wiki.lock("Mr. Souraj", "Steward X", NOW - timedelta(hours=1))
    wiki.block("Mr. Ranju Maity", "Yahya", NOW - timedelta(minutes=30))
    make_bot(wiki, tmp_path).run_once()
    [(old, new)] = changed_sections(BASE, wiki.text)
    assert old.title == "বাধাদানের অনুরোধ: Mr. Souraj ও Mr. Ranju Maity"
    assert "\nSteward X ও Yahya কর্তৃক {{করা হয়েছে}}" in new.text
    s = wiki.edits[0]["summary"]
    assert "Mr. Souraj অ্যাকাউন্টটি স্টুয়ার্ড Steward X বৈশ্বিকভাবে লক করেছেন" in s
    assert "Mr. Ranju Maity-কে প্রশাসক Yahya স্থানীয়ভাবে বাধা দিয়েছেন" in s


def test_heading_names_only_half_done_is_left_alone(wiki, tmp_path):
    wiki.lock("Mr. Souraj", "Steward X", NOW - timedelta(hours=1))
    make_bot(wiki, tmp_path).run_once()
    assert wiki.edits == []


def test_heading_names_not_existing_are_ignored(wiki, tmp_path):
    wiki.missing_users = {"Mr. Ranju Maity"}
    wiki.lock("Mr. Souraj", "Steward X", NOW - timedelta(hours=1))
    make_bot(wiki, tmp_path).run_once()
    assert wiki.edits == []


def test_duplicate_titles_edit_the_right_section(wiki, tmp_path):
    wiki.lock("Muriwala Debu", "Steward Y", NOW - timedelta(hours=3))
    make_bot(wiki, tmp_path).run_once()
    [(old, new)] = changed_sections(BASE, wiki.text)
    assert "Muriwala Debu" in old.text                  # not the Armenian one
    assert "Steward Y কর্তৃক {{করা হয়েছে}}" in new.text


def test_stale_real_temp_account(wiki, tmp_path):
    wiki.contribs[TEMP] = datetime(2026, 6, 21, 11, 50, tzinfo=UTC)
    make_bot(wiki, tmp_path).run_once()
    assert len(wiki.edits) == 1
    [(old, new)] = changed_sections(BASE, wiki.text)
    assert old.title.startswith("বাধাদানের অনুরোধ [[বিশেষ:অবদান/~2026-35944-61")
    assert new.text == old.text.rstrip() + (
        "\nবাধা দেওয়ার প্রয়োজন নেই, অস্থায়ী অ্যাকাউন্ট থেকে সর্বশেষ সম্পাদনা "
        "২১ জুন ২০২৬, ১১:৫০ (ইউটিসি) টায় হয়েছে। <small>(স্বয়ংক্রিয় বার্তা)</small> --~~~~"
        "\n{{subst:সহঅ}}\n\n")
    s = wiki.edits[0]["summary"]
    assert s.startswith("/* বাধাদানের অনুরোধ ~2026-35944-61 */ বট: অনুরোধটি অপ্রয়োজনীয়")
    assert "{{সহঅ}}" in s and len(s) <= 500


def test_temp_account_edited_recently_is_not_stale(wiki, tmp_path):
    wiki.contribs[TEMP] = NOW - timedelta(hours=59, minutes=59)
    due = make_bot(wiki, tmp_path).run_once()
    assert wiki.edits == []
    assert due == NOW + timedelta(minutes=1)


def test_non_block_request_untouched_even_if_user_blocked(wiki, tmp_path):
    wiki.block("Sàádî", "Someone", datetime(2026, 8, 11, tzinfo=UTC))
    make_bot(wiki, tmp_path).run_once()
    assert wiki.edits == []


def test_already_resolved_untouched(wiki, tmp_path):
    wiki.block("~2026-32288-48", "Ferdous", datetime(2026, 6, 13, 15, tzinfo=UTC))
    make_bot(wiki, tmp_path).run_once()
    assert wiki.edits == []


def test_block_long_before_report_is_not_the_answer(wiki, tmp_path):
    name = "Զեմւկո Բանգլադեշվչոտրցևղձճծընէե (ՀաՒարոդիմ)"
    wiki.block(name, "Old Admin", datetime(2026, 1, 1, tzinfo=UTC))
    make_bot(wiki, tmp_path).run_once()
    assert wiki.edits == []


def test_everything_at_once_then_idempotent(wiki, tmp_path):
    wiki.block("Swarup Das Official", "Ferdous", NOW - timedelta(hours=1))
    wiki.lock("Muriwala Debu", "Steward Y", NOW - timedelta(hours=1))
    wiki.gblock("Integrity2020", "Steward Z", NOW - timedelta(hours=1))
    wiki.lock("Mr. Souraj", "Steward X", NOW - timedelta(hours=1))
    wiki.lock("Mr. Ranju Maity", "Steward X", NOW - timedelta(hours=1))
    wiki.contribs[TEMP] = datetime(2026, 6, 21, 11, 50, tzinfo=UTC)
    bot = make_bot(wiki, tmp_path)
    bot.run_once()
    assert len(wiki.edits) == 5
    assert len(changed_sections(BASE, wiki.text)) == 5
    assert "Steward X কর্তৃক {{করা হয়েছে}}" in wiki.text     # one name, not "X ও X"
    # Simulate {{subst:সহঅ}} being expanded by MediaWiki on save.
    wiki.text = wiki.text.replace("{{subst:সহঅ}}", REAL_SUBST)
    wiki.clock += timedelta(minutes=5)
    bot.run_once()
    assert len(wiki.edits) == 5


def test_real_nephrozoa_done_but_not_archived(tmp_path):
    """On the real page {{done}} was given (signed 11:30, 18 Aug) but nobody added
    {{subst:সহঅ}}: the bot adds only that, and nothing else anywhere."""
    w = FakeWiki(PAGE, REAL, NOW)
    w.subst_output = REAL_SUBST
    w.contribs[TEMP] = NOW - timedelta(hours=2)
    make_bot(w, tmp_path).run_once()
    assert len(w.edits) == 1
    [(old, new)] = changed_sections(REAL, w.text)
    assert old.title == NEPHRO
    assert new.text == old.text.rstrip() + "\n{{subst:সহঅ}}\n"
    assert w.edits[0]["summary"].startswith(
        "/* Nephrozoa পাতাটি পুনর্নির্দেশ হিসেবে তৈরি করুন */ বট: অনুরোধটি আগেই {{done}} "
        "দিয়ে চিহ্নিত করা হয়েছে")
