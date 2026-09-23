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


# Month names as MediaWiki (bn) prints them, plus common spelling variants.
_MONTHS_BN = {
    1: ["জানুয়ারি", "জানুয়ারী"],
    2: ["ফেব্রুয়ারি", "ফেব্রুয়ারী"],
    3: ["মার্চ"],
    4: ["এপ্রিল"],
    5: ["মে"],
    6: ["জুন"],
    7: ["জুলাই"],
    8: ["আগস্ট", "আগষ্ট"],
    9: ["সেপ্টেম্বর"],
    10: ["অক্টোবর"],
    11: ["নভেম্বর"],
    12: ["ডিসেম্বর"],
}
_MONTHS_EN = {
    1: ["January", "Jan"], 2: ["February", "Feb"], 3: ["March", "Mar"],
    4: ["April", "Apr"], 5: ["May"], 6: ["June", "Jun"], 7: ["July", "Jul"],
    8: ["August", "Aug"], 9: ["September", "Sep", "Sept"],
    10: ["October", "Oct"], 11: ["November", "Nov"], 12: ["December", "Dec"],
}

_MONTH_LOOKUP = {}
for _n, _names in list(_MONTHS_BN.items()) + list(_MONTHS_EN.items()):
    for _name in _names:
        _MONTH_LOOKUP[nfc(_name).lower()] = _n

_MONTH_ALT = "|".join(
    sorted((re.escape(k) for k in _MONTH_LOOKUP), key=len, reverse=True)
)
_D = "[0-9০-৯]"

# "০৫:৪৮, ২৩ সেপ্টেম্বর ২০২৬ (ইউটিসি)"  /  "05:48, 23 September 2026 (UTC)"
SIGNATURE_TS_RE = re.compile(
    rf"({_D}{{1,2}}):({_D}{{2}}),\s*({_D}{{1,2}})\s+({_MONTH_ALT})\s+({_D}{{4}})"
    rf"\s*\((?:ইউটিসি|UTC|ইউ\.টি\.সি)\)",
    re.IGNORECASE,
)


def parse_signature_timestamps(text: str) -> List[datetime]:
    """Return every signature timestamp found in *text* (in order)."""
    out = []
    for m in SIGNATURE_TS_RE.finditer(nfc(text)):
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


def format_bn_datetime(dt: datetime, tz_offset_minutes: int = 0,
                       tz_label: str = "ইউটিসি") -> str:
    """'২৩ সেপ্টেম্বর ২০২৬, ০৫:৪৮ (ইউটিসি)' in the requested timezone."""
    local = dt.astimezone(UTC) + timedelta(minutes=tz_offset_minutes)
    month = _MONTHS_BN[local.month][0]
    text = f"{local.day} {month} {local.year}, {local.hour:02d}:{local.minute:02d}"
    return f"{to_bn_digits(text)} ({tz_label})"


def format_bn_duration(delta: timedelta) -> str:
    """Human-readable Bangla duration, e.g. '৩ দিন ২ ঘণ্টা ৫ মিনিট'."""
    total = int(delta.total_seconds() // 60)
    days, rem = divmod(total, 1440)
    hours, minutes = divmod(rem, 60)
    parts = []
    if days:
        parts.append(f"{days} দিন")
    if hours:
        parts.append(f"{hours} ঘণ্টা")
    if minutes or not parts:
        parts.append(f"{minutes} মিনিট")
    return to_bn_digits(" ".join(parts))
