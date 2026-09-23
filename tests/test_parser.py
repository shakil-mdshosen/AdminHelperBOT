from datetime import datetime
from pathlib import Path

from adminhelperbot.config import Config
from adminhelperbot.parser import NoticeboardParser, split_sections
from adminhelperbot.timeutil import (UTC, format_bn_datetime, nfc,
                                     parse_signature_timestamps)

SAMPLE = (Path(__file__).parent / "sample_noticeboard.txt").read_text(encoding="utf-8")


def make_parser():
    c = Config()
    return NoticeboardParser(c.resolved_templates, c.report_templates,
                             c.resolved_phrases, c.block_keywords, c.temp_account_regex,
                             c.heading_account_regex, c.heading_name_separator_regex)


def by_title(infos):
    return {i.section.title: i for i in infos}


def test_bangla_signature_timestamp():
    ts = parse_signature_timestamps("[[ব্যবহারকারী:A|A]] ০৫:৪৮, ২৩ সেপ্টেম্বর ২০২৬ (ইউটিসি)")
    assert ts == [datetime(2026, 9, 23, 5, 48, tzinfo=UTC)]


def test_english_and_variant_spellings():
    assert parse_signature_timestamps("11:00, 3 February 2026 (UTC)") == [
        datetime(2026, 2, 3, 11, 0, tzinfo=UTC)]
    # precomposed য় (U+09DF) and the ী spelling variant
    text = "০১:০২, ৫ ফেব্রুয়ারী ২০২৬ (ইউটিসি)"
    assert parse_signature_timestamps(text) == [datetime(2026, 2, 5, 1, 2, tzinfo=UTC)]


def test_format_bn_datetime():
    dt = datetime(2026, 9, 23, 5, 8, tzinfo=UTC)
    assert format_bn_datetime(dt) == "২৩ সেপ্টেম্বর ২০২৬, ০৫:০৮ (ইউটিসি)"
    assert format_bn_datetime(dt, 360, "বাংলাদেশ সময়") == \
        "২৩ সেপ্টেম্বর ২০২৬, ১১:০৮ (বাংলাদেশ সময়)"


def test_headings_in_comments_are_ignored():
    titles = [s.title for s in split_sections(SAMPLE)]
    assert "এটি শিরোনাম নয়" not in titles
    assert len(titles) == 6


def test_sections_cover_text_exactly():
    secs = split_sections(SAMPLE)
    assert "".join(s.text for s in secs) == SAMPLE[secs[0].start:]


def test_temp_account_from_contrib_link():
    info = by_title(make_parser().parse(SAMPLE))["অস্থায়ী অ্যাকাউন্ট ~2026-10001-01 কে বাধাদান"]
    assert [a.name for a in info.accounts] == ["~2026-10001-01"]
    assert info.accounts[0].is_temp
    assert info.report_time == datetime(2026, 9, 20, 10, 0, tzinfo=UTC)
    assert info.looks_like_block_request and not info.is_resolved


def test_userlinks_template_and_signers_excluded():
    info = by_title(make_parser().parse(SAMPLE))["ব্যবহারকারী বাধাদানের অনুরোধ"]
    # Reporter Two (signature) and Admin A (a reply) are not reported accounts.
    assert [a.name for a in info.accounts] == ["Vandal Account"]
    assert info.report_time == datetime(2026, 9, 23, 9, 0, tzinfo=UTC)


def test_resolved_detected():
    info = by_title(make_parser().parse(SAMPLE))["ইতিমধ্যে সমাধান হওয়া অনুরোধ"]
    assert info.is_resolved


def test_temp_account_reporter_is_not_reported():
    info = by_title(make_parser().parse(SAMPLE))["বৈশ্বিকভাবে লক হওয়া অ্যাকাউন্ট"]
    assert [a.name for a in info.accounts] == ["Cross Wiki Spammer", "~2026-20002-02"]
    assert info.report_time == datetime(2026, 9, 23, 11, 0, tzinfo=UTC)


def test_non_block_request_not_flagged():
    info = by_title(make_parser().parse(SAMPLE))["পাতা সুরক্ষার অনুরোধ"]
    assert not info.looks_like_block_request


def test_temp_account_in_heading():
    info = by_title(make_parser().parse(SAMPLE))["~2026-30003-03"]
    assert [a.name for a in info.accounts] == ["~2026-30003-03"]


def test_ip_account_and_underscores():
    text = ("== IP বাধা ==\n[[বিশেষ:অবদান/192.0.2.5]] ও [[User:Bad_user]] কে ব্লক করুন। "
            "[[User:R|R]] 01:00, 1 January 2026 (UTC)\n")
    info = make_parser().parse(text)[0]
    assert [(a.name, a.is_ip) for a in info.accounts] == [
        ("192.0.2.5", True), ("Bad user", False)]


def test_later_replies_do_not_add_accounts():
    text = ("== বাধা ==\n{{vandal|X}} [[User:R|R]] 01:00, 1 January 2026 (UTC)\n"
            ":[[User:Someone else]] দেখুন [[User:A|A]] 02:00, 1 January 2026 (UTC)\n")
    info = make_parser().parse(text)[0]
    assert [a.name for a in info.accounts] == ["X"]


def test_marker_in_comment_counts_as_resolved():
    p = make_parser()
    p.add_resolved_phrases(["সংগ্রহশালাভুক্তির জন্য প্রস্তুত"])
    text = ("== বাধা ==\n{{vandal|X}} [[User:R|R]] 01:00, 1 January 2026 (UTC)\n"
            "<!-- সংগ্রহশালাভুক্তির জন্য প্রস্তুত 1767229200 -->\n")
    assert p.parse(text)[0].is_resolved


def test_nfc_keywords():
    assert nfc("অস্থায়ী") == nfc("অস্থায়ী")


def test_keywords_must_start_a_word_and_ignore_markup():
    p = make_parser()
    sig = "[[ব্যবহারকারী:কুউ পুলক|কুউ পুলক]] ১৫:০৩, ৮ জুন ২০২৬ (ইউটিসি)"
    # "লক" inside পুলক / মূলক, "block" inside a URL: not block requests
    assert not p.parse(f"== টেমপ্লেট তৈরি ==\nঅনুরোধ। {sig}\n")[0].looks_like_block_request
    assert not p.parse(f"== x ==\nপ্রচারণামূলক লেখা। {sig}\n")[0].looks_like_block_request
    assert not p.parse("== x ==\n{{ওয়েব উদ্ধৃতি|ইউআরএল=https://e.org/Block.pdf}} "
                       f"{sig}\n")[0].looks_like_block_request
    # real keywords at the start of a word still count, with suffixes
    assert p.parse(f"== বাধাদানের অনুরোধ ==\nx {sig}\n")[0].looks_like_block_request
    assert p.parse(f"== x ==\nঅ্যাকাউন্টটি লক করুন {sig}\n")[0].looks_like_block_request
    assert p.parse(f"== x ==\nPlease block. {sig}\n")[0].looks_like_block_request


def test_heading_name_list():
    p = make_parser()
    sig = "[[User:R|R]] 01:00, 1 January 2026 (UTC)"
    info = p.parse(f"== বাধাদানের অনুরোধ: A, B ও C ==\nx {sig}\n")[0]
    assert [(a.name, a.from_heading_text) for a in info.accounts] == [
        ("A", True), ("B", True), ("C", True)]
    # a name also linked in the body is a confirmed (non-heading) account
    info = p.parse(f"== বাধাদানের অনুরোধ: A ==\n[[বিশেষ:অবদান/A]] {sig}\n")[0]
    assert [(a.name, a.from_heading_text) for a in info.accounts] == [("A", False)]
    # headings without the "অনুরোধ:" form give no plain-text names
    assert make_parser().parse(f"== ব্যবস্থা নিন ==\nx {sig}\n")[0].accounts == []
