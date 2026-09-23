"""Time helpers: Bangla digits, wiki signature timestamps, formatting.

All datetimes handled by the bot are timezone-aware UTC.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timedelta, timezone
from typing import List, Optional

UTC = timezone.utc

_BN_DIGITS = "০১২৩৪৫৬৭৮৯"
_TO_ASCII = str.maketrans(_BN_DIGITS, "0123456789")
_TO_BN = str.maketrans("0123456789", _BN_DIGITS)


def nfc(text: str) -> str:
    """Normalise Bangla text.

    'য়' can be typed as one code point (U+09DF) or as য + nukta; NFC always
    yields the decomposed form, so every comparison goes through this.
    """
    return unicodedata.normalize("NFC", text)


def to_ascii_digits(text: str) -> str:
    return text.translate(_TO_ASCII)


def to_bn_digits(text: str) -> str:
    return text.translate(_TO_BN)


_MONTHS_EN = {
    1: ["January", "Jan"], 2: ["February", "Feb"], 3: ["March", "Mar"],
    4: ["April", "Apr"], 5: ["May"], 6: ["June", "Jun"], 7: ["July", "Jul"],
    8: ["August", "Aug"], 9: ["September", "Sep", "Sept"],
    10: ["October", "Oct"], 11: ["November", "Nov"], 12: ["December", "Dec"],
}
_D = "[0-9০-৯]"

# Filled by configure() from texts.toml ([datetime]).
_texts = None
_MONTH_LOOKUP: dict = {}
SIGNATURE_TS_RE: re.Pattern = re.compile(r"(?!)")


def configure(texts) -> None:
    """Build the signature regex and date format from a Texts object."""
    global _texts, _MONTH_LOOKUP, SIGNATURE_TS_RE
    _texts = texts
    lookup = {}
    for n, names in _MONTHS_EN.items():
        for name in names:
            lookup[name.lower()] = n
    for n, name in enumerate(texts.get("datetime.months"), start=1):
        lookup[nfc(name).lower()] = n
    for name, n in texts.get("datetime.month_variants").items():
        lookup[nfc(name).lower()] = int(n)
    _MONTH_LOOKUP = lookup
    months = "|".join(sorted((re.escape(k) for k in lookup), key=len, reverse=True))
    tz = "|".join(re.escape(nfc(t)) for t in texts.get("datetime.signature_tz_labels"))
    # "০৫:৪৮, ২৩ সেপ্টেম্বর ২০২৬ (ইউটিসি)"  /  "05:48, 23 September 2026 (UTC)"
    SIGNATURE_TS_RE = re.compile(
        rf"({_D}{{1,2}}):({_D}{{2}}),\s*({_D}{{1,2}})\s+({months})\s+({_D}{{4}})"
        rf"\s*\((?:{tz})\)",
        re.IGNORECASE,
    )


def signature_re() -> re.Pattern:
    return SIGNATURE_TS_RE


def parse_signature_timestamps(text: str) -> List[datetime]:
    """Return every signature timestamp found in *text* (in order)."""
    out = []
    for m in signature_re().finditer(nfc(text)):
        dt = _match_to_dt(m)
        if dt is not None:
            out.append(dt)
    return out


def _match_to_dt(m: re.Match) -> Optional[datetime]:
    hh, mm, dd, mon, yyyy = m.groups()
    month = _MONTH_LOOKUP.get(nfc(mon).lower())
    if month is None:
        return None
    try:
        return datetime(
            int(to_ascii_digits(yyyy)), month, int(to_ascii_digits(dd)),
            int(to_ascii_digits(hh)), int(to_ascii_digits(mm)), tzinfo=UTC,
        )
    except ValueError:
        return None


def parse_api_ts(value: str) -> datetime:
    """Parse an ISO-8601 timestamp returned by the MediaWiki API."""
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)


def format_bn_datetime(dt: datetime, tz_offset_minutes: int = 0) -> str:
    """'২৩ সেপ্টেম্বর ২০২৬, ০৫:৪৮ (ইউটিসি)' using [datetime] from texts.toml."""
    local = dt.astimezone(UTC) + timedelta(minutes=tz_offset_minutes)
    text = _texts.render(
        "datetime.format", day=local.day,
        month=_texts.get("datetime.months")[local.month - 1],
        year=local.year, hour=f"{local.hour:02d}", minute=f"{local.minute:02d}",
        tz="\0TZ\0")
    # Only the numbers become Bangla digits, not the timezone label.
    return to_bn_digits(text).replace("\0TZ\0", _texts.get("datetime.tz_label"))


def _configure_default() -> None:
    from .texts import default_texts
    configure(default_texts())


_configure_default()
