"""Wikitext parsing for the administrators' noticeboard."""

from __future__ import annotations

import ipaddress
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Iterable, List, Optional, Set, Tuple

import mwparserfromhell

from .timeutil import SIGNATURE_TS_RE, nfc, parse_signature_timestamps

HEADING_RE = re.compile(r"^(={1,6})[ \t]*(.+?)[ \t]*\1[ \t]*$", re.MULTILINE)
# Regions in which headings/templates are not real: comments, nowiki, pre, etc.
_MASK_RE = re.compile(
    r"<!--.*?(?:-->|\Z)"
    r"|<(nowiki|pre|syntaxhighlight|source|code|math)\b[^>]*>.*?(?:</\1\s*>|\Z)",
    re.DOTALL | re.IGNORECASE,
)

USER_NS = ["ব্যবহারকারী", "ব্যবহারকারীর", "user", "ব্যবহারকারিণী", "ব্যবহারকারিনী"]
USER_TALK_NS = ["ব্যবহারকারী আলাপ", "user talk", "ব্যবহারকারীর আলাপ"]
CONTRIB_PREFIX = [
    "বিশেষ:অবদান", "বিশেষ:ব্যবহারকারীর অবদান", "বিশেষ:contributions",
    "special:contributions", "special:contribs", "বিশেষ:অবদানসমূহ",
]


@dataclass
class Section:
    index: int            # 1-based position of the heading on the page
    level: int
    title: str
    start: int            # offset of the heading line in page text
    end: int              # offset where the next heading starts (exclusive)
    text: str             # full text including heading line

    @property
    def body(self) -> str:
        nl = self.text.find("\n")
        return "" if nl == -1 else self.text[nl + 1:]


@dataclass
class Account:
    name: str
    is_temp: bool = False
    is_ip: bool = False


@dataclass
class RequestInfo:
    section: Section
    report_time: Optional[datetime]
    accounts: List[Account] = field(default_factory=list)
    is_resolved: bool = False
    resolved_reason: str = ""
    looks_like_block_request: bool = False

    @property
    def key(self) -> str:
        ts = self.report_time.isoformat() if self.report_time else "?"
        return f"{self.section.title}|{ts}"


def _masked(text: str) -> str:
    """Replace masked regions by spaces, keeping offsets identical."""
    return _MASK_RE.sub(lambda m: re.sub(r"[^\n]", " ", m.group(0)), text)


def split_sections(text: str) -> List[Section]:
    masked = _masked(text)
    heads = list(HEADING_RE.finditer(masked))
    sections = []
    for i, m in enumerate(heads):
        start = m.start()
        end = heads[i + 1].start() if i + 1 < len(heads) else len(text)
        title = text[m.start(2):m.end(2)].strip()
        sections.append(Section(i + 1, len(m.group(1)), title, start, end,
                                text[start:end]))
    return sections


def normalize_username(name: str) -> str:
    name = nfc(name).replace("_", " ").strip()
    name = re.sub(r"\s+", " ", name)
    if name and not _is_ip(name):
        name = name[0].upper() + name[1:]
    return name


def _is_ip(name: str) -> bool:
    try:
        ipaddress.ip_address(name.strip())
        return True
    except ValueError:
        return False


def _tpl_name(tpl) -> str:
    name = nfc(str(tpl.name)).strip()
    name = re.sub(r"^(?:template|টেমপ্লেট|টেম্পলেট)\s*:\s*", "", name, flags=re.I)
    return re.sub(r"[\s_]+", " ", name).lower()


def _first_comment(body: str) -> str:
    """Text of the report itself: everything up to the first signature."""
    m = SIGNATURE_TS_RE.search(nfc(body))
    return nfc(body) if m is None else nfc(body)[:m.end()]


class NoticeboardParser:
    def __init__(self, resolved_templates: Iterable[str],
                 report_templates: Iterable[str],
                 resolved_phrases: Iterable[str],
                 block_keywords: Iterable[str],
                 temp_account_regex: str):
        self.resolved_templates = {self._norm_tpl(t) for t in resolved_templates}
        self.report_templates = {self._norm_tpl(t) for t in report_templates}
        self.resolved_phrases = [nfc(p) for p in resolved_phrases]
        self.block_keywords = [nfc(k).lower() for k in block_keywords]
        self.temp_re = re.compile(rf"(?<![\w~-])({temp_account_regex})(?![\w-])")

    @staticmethod
    def _norm_tpl(name: str) -> str:
        return re.sub(r"[\s_]+", " ", nfc(name)).strip().lower()

    def add_resolved_templates(self, names: Iterable[str]) -> None:
        self.resolved_templates |= {self._norm_tpl(n) for n in names}

    def add_resolved_phrases(self, phrases: Iterable[str]) -> None:
        self.resolved_phrases += [nfc(p) for p in phrases if p.strip()]

    # ------------------------------------------------------------------
    def parse(self, text: str) -> List[RequestInfo]:
        return [self.analyse(sec) for sec in split_sections(text)]

    def analyse(self, sec: Section) -> RequestInfo:
        body = _masked(sec.body)
        times = parse_signature_timestamps(body)
        info = RequestInfo(section=sec, report_time=min(times) if times else None)

        # Raw text on purpose: a marker left inside a comment still means the
        # request was handled, and skipping is the safe side for a bot.
        reason = self._resolved_reason(sec.text)
        if reason:
            info.is_resolved, info.resolved_reason = True, reason

        report_text = _first_comment(body)
        used_report_template, names = self._extract(sec.title, report_text)
        info.accounts = [
            Account(n, is_temp=bool(self.temp_re.fullmatch(n)), is_ip=_is_ip(n))
            for n in names
        ]
        low = nfc(sec.title + "\n" + report_text).lower()
        info.looks_like_block_request = used_report_template or any(
            k in low for k in self.block_keywords
        )
        return info

    def _resolved_reason(self, text: str) -> str:
        code = mwparserfromhell.parse(text)
        for tpl in code.filter_templates(recursive=True):
            if _tpl_name(tpl) in self.resolved_templates:
                return "{{" + str(tpl.name).strip() + "}}"
        norm = nfc(text)
        for phrase in self.resolved_phrases:
            if phrase in norm:
                return phrase
        return ""

    # ------------------------------------------------------------------
    def _extract(self, title: str, report_text: str) -> Tuple[bool, List[str]]:
        """Return (a report template was used, ordered unique account names).

        Names inside report templates always count. Names taken from links or
        from bare temporary-account names are ignored when they belong to the
        person who signed the report (a signature is not a report).
        """
        found: List[Tuple[str, bool]] = []   # (name, from_template)
        used_tpl = False
        signers = self._signers(report_text)

        for part in (title, report_text):
            code = mwparserfromhell.parse(part)
            for tpl in code.filter_templates(recursive=True):
                if _tpl_name(tpl) in self.report_templates and tpl.has("1"):
                    used_tpl = True
                    found.append((str(tpl.get("1").value).strip(), True))
            for link in code.filter_wikilinks(recursive=True):
                target = self._user_from_link(str(link.title))
                if target is not None:
                    found.append((target[1], False))
            for name in self.temp_re.findall(part) + self.temp_re.findall(
                    code.strip_code()):
                found.append((name, False))

        seen: Set[str] = set()
        out = []
        for raw, from_tpl in found:
            name = normalize_username(raw)
            if not name or "{" in name or "|" in name or name in seen:
                continue
            if not from_tpl and name in signers:
                continue
            seen.add(name)
            out.append(name)
        return used_tpl, out

    def _user_from_link(self, target: str) -> Optional[Tuple[str, str]]:
        t = nfc(target).strip().lstrip(":").replace("_", " ")
        t = t.split("#")[0]
        low = t.lower()
        for prefix in CONTRIB_PREFIX:
            prefix = nfc(prefix)
            if low.startswith(prefix + "/"):
                return "contrib", t[len(prefix) + 1:].split("/")[0]
        if ":" not in t:
            return None
        ns, rest = t.split(":", 1)
        ns = re.sub(r"\s+", " ", ns).strip().lower()
        rest = rest.split("/")[0]
        if ns in USER_NS:
            return "user", rest
        if ns in USER_TALK_NS:
            return "talk", rest
        return None

    def _signers(self, text: str) -> Set[str]:
        """Users whose user/talk/contribs link (or bare temporary-account name)
        is the last one on a line before a signature timestamp."""
        signers: Set[str] = set()
        for line in text.split("\n"):
            for m in SIGNATURE_TS_RE.finditer(line):
                before = line[:m.start()]
                last_pos, last_name = -1, None
                for link in mwparserfromhell.parse(before).filter_wikilinks():
                    target = self._user_from_link(str(link.title))
                    if target:
                        pos = before.rfind(str(link))
                        if pos > last_pos:
                            last_pos, last_name = pos, target[1]
                for tm in self.temp_re.finditer(before):
                    if tm.start() > last_pos:
                        last_pos, last_name = tm.start(), tm.group(1)
                if last_name:
                    signers.add(normalize_username(last_name))
        return signers
