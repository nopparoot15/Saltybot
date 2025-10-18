import re
from datetime import datetime
from zoneinfo import ZoneInfo
from saltybot.utils.timez import years_between

_BDAY_RE = re.compile(r"^\s*(\d{1,2})[\/\.\-](\d{1,2})[\/\.\-](\d{4})\s*$")

def parse_birthday(text: str) -> datetime | None:
    if not text: return None
    m = _BDAY_RE.match(text)
    if not m: return None
    d, mth, y = map(int, m.groups())
    try:
        dt = datetime(y, mth, d, 0, 0, tzinfo=ZoneInfo("Asia/Bangkok"))
    except ValueError:
        return None
    now = datetime.now(ZoneInfo("Asia/Bangkok"))
    if dt > now or y < 1900 or y > now.year: return None
    return dt

def age_from_birthday(bday: datetime, now_local: datetime | None = None) -> int:
    now_local = now_local or datetime.now(ZoneInfo("Asia/Bangkok"))
    return years_between(bday, now_local)
