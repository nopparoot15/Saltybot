import re
from datetime import datetime, timezone, timedelta
from typing import Optional
from config import (ROLE_MALE, ROLE_FEMALE, ROLE_LGBT, ROLE_GENDER_UNDISCLOSED,
                    ROLE_AGE_UNDISCLOSED, TZ)
from utils.text import contains_emoji

def _norm(s: str) -> str:
    return re.sub(r'[\s\.\-_\/\\]+', '', (s or '').strip().lower())

MALE_ALIASES = {_norm(x) for x in ["ช","ชา","ชาย","ผู้ชาย","เพศชาย","ผช","male","man","boy","m","masculine","he","him","男","男性","おとこ","だんせい"]}
FEMALE_ALIASES = {_norm(x) for x in ["ห","หญิง","ผู้หญิง","เพศหญิง","ผญ","female","woman","girl","f","feminine","she","her","女","女性","おんな","じょせい"]}
LGBT_ALIASES = {_norm(x) for x in ["lgbt","lgbtq","lgbtq+","nonbinary","enby","trans","queer","อื่น","เพศทางเลือก","สาวสอง","ทอม","ดี้","ไบ"]}
UNDISCLOSED_ALIASES = {_norm(x) for x in ["ไม่ระบุ","ไม่บอก","ไม่สะดวก","prefernottosay","undisclosed","unspecified","unknown","private","secret","n/a","na","none","-","—"]}

def resolve_gender_role_id(text: str) -> int:
    t = _norm(text)
    if t in MALE_ALIASES: return ROLE_MALE
    if t in FEMALE_ALIASES: return ROLE_FEMALE
    if t in LGBT_ALIASES: return ROLE_LGBT
    return ROLE_GENDER_UNDISCLOSED

def is_age_undisclosed(text: str) -> bool:
    t = _norm(text)
    return (t == "") or (t in UNDISCLOSED_ALIASES)

def resolve_age_role_id(age_text: str) -> Optional[int]:
    if is_age_undisclosed(age_text): return ROLE_AGE_UNDISCLOSED
    try:
        age = int((age_text or "").strip())
    except ValueError:
        return None
    slots = [
        ((0, 12), 1402907371696558131),
        ((13, 15), 1344232758129594379),
        ((16, 18), 1344232891093090377),
        ((19, 21), 1344232979647565924),
        ((22, 24), 1344233048593403955),
        ((25, 29), 1418703710137094357),
        ((30, 34), 1418703702843457576),
        ((35, 39), 1418703707100545075),
        ((40, 44), 1418703944711929917),
        ((45, 49), 1418703955176718396),
        ((50, 54), 1418704062592843948),
        ((55, 59), 1418704067194261615),
        ((60, 64), 1418704072617496666),
        ((65, 200), 1418704076119736390),
    ]
    for (lo, hi), rid in slots:
        if lo <= age <= hi:
            return rid
    return None

_BDAY_RE = re.compile(r"^\s*(\d{1,2})[\/\.\-](\d{1,2})[\/\.\-](\d{4})\s*$")

def parse_birthday(text: str):
    if not text: return None
    m = _BDAY_RE.match(text)
    if not m: return None
    d, mth, y = map(int, m.groups())
    try:
        dt = datetime(y, mth, d, 0, 0, tzinfo=TZ)
    except ValueError:
        return None
    now = datetime.now(TZ)
    if dt > now: return None
    if y < 1900 or y > now.year: return None
    return dt

def years_between(a: datetime, b: datetime) -> int:
    years = b.year - a.year
    if (b.month, b.day) < (a.month, a.day):
        years -= 1
    return max(years, 0)

def age_from_birthday(bday, now_local=None) -> int:
    from config import TZ
    now_local = now_local or datetime.now(TZ)
    return years_between(bday, now_local)
