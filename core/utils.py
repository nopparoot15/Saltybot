\
import re, io, unicodedata
from datetime import datetime, timezone, timedelta
from typing import Iterable, Optional
import discord

from .config import (
    ADMIN_NOTIFY_CHANNEL_ID, APPROVAL_CHANNEL_ID, TH_TZ,
    ROLE_MALE, ROLE_FEMALE, ROLE_LGBT, ROLE_GENDER_UNDISCLOSED,
    ROLE_AGE_UNDISCLOSED,
    AGE_ROLE_IDS_ALL, GENDER_ROLE_IDS_ALL,
    MIN_ACCOUNT_AGE_DAYS_HIGH, MIN_ACCOUNT_AGE_DAYS_MED,
)

INVALID_CHARS = set("=+*/@#$%^&*()<>?|{}[]\"'\\~`")

EMOJI_RE = re.compile(
    r"["
    r"\U0001F300-\U0001F5FF"
    r"\U0001F600-\U0001F64F"
    r"\U0001F680-\U0001F6FF"
    r"\U0001F700-\U0001F77F"
    r"\U0001F780-\U0001F7FF"
    r"\U0001F900-\U0001F9FF"
    r"\U0001FA00-\U0001FA6F"
    r"\U0001FA70-\U0001FAFF"
    r"\u2600-\u26FF"
    r"\u2700-\u27BF"
    r"]"
    r"|[\u200d\uFE0F]"
    r"|[\U0001F1E6-\U0001F1FF]{2}"
)
def contains_emoji(s: str) -> bool:
    return bool(EMOJI_RE.search(s or ""))

_ZERO_WIDTH_RE = re.compile(r"[\u200B-\u200F\u202A-\u202E\u2060-\u206F\uFEFF]")
_CONFUSABLES_MAP = str.maketrans({
    "А":"A","В":"B","Е":"E","К":"K","М":"M","Н":"H","О":"O","Р":"P","С":"S","Т":"T","У":"Y","Х":"X",
    "а":"a","в":"b","е":"e","к":"k","м":"m","н":"h","о":"o","р":"p","с":"c","т":"t","у":"y","х":"x",
    "Α":"A","Β":"B","Ε":"E","Ζ":"Z","Η":"H","Ι":"I","Κ":"K","Μ":"M","Ν":"N","Ο":"O","Ρ":"P","Τ":"T","Υ":"Y","Χ":"X",
    "α":"a","β":"b","ε":"e","ι":"i","κ":"k","ν":"n","ο":"o","ρ":"p","τ":"t","υ":"y","χ":"x",
})
_LEET_MAP = str.maketrans({
    "0":"o","1":"l","3":"e","4":"a","5":"s","7":"t","8":"b","9":"g","2":"z","6":"g",
    "@":"a","$":"s","+":"t"
})
def _strip_combining(s: str) -> str:
    return "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
def _letters_only(s: str) -> str:
    return "".join(ch for ch in s if unicodedata.category(ch).startswith("L"))
def _collapse_runs(s: str) -> str:
    if not s: return s
    out=[s[0]]
    for ch in s[1:]:
        if ch!=out[-1]: out.append(ch)
    return "".join(out)
def canon_name(s: str) -> str:
    if not s: return ""
    s = unicodedata.normalize("NFKC", s)
    s = _ZERO_WIDTH_RE.sub("", s)
    s = EMOJI_RE.sub("", s)
    s = s.translate(_CONFUSABLES_MAP)
    s = s.translate(_LEET_MAP)
    s = unicodedata.normalize("NFKD", s)
    s = _strip_combining(s)
    s = _letters_only(s)
    s = s.casefold()
    s = _collapse_runs(s)
    return s

def base_display_name(member: discord.Member | discord.User) -> str:
    base = (
        getattr(member, "nick", None)
        or getattr(member, "global_name", None)
        or getattr(member, "display_name", None)
        or getattr(member, "name", None)
        or ""
    ).strip()
    return re.sub(r"\s*\(.*?\)\s*$", "", base).strip()

def discord_names_set(member: discord.Member | discord.User) -> set[str]:
    names = filter(None, {
        getattr(member, "nick", ""),
        getattr(member, "global_name", ""),
        getattr(member, "display_name", ""),
        getattr(member, "name", ""),
        base_display_name(member),
    })
    return {canon_name(x) for x in names if x}

# Gender aliases
def _norm_gender(s: str) -> str:
    s = (s or "").strip().lower()
    s = re.sub(r'[\s\.\-_\/\\]+', '', s)
    return s

_MALE_ALIASES_RAW = {"ชาย","ผู้ชาย","male","man","boy","m","เขา","หนุ่ม","ชายแท้","ช"}
_FEMALE_ALIASES_RAW = {"หญิง","ผู้หญิง","female","woman","girl","f","สาว","หญ","ห"}
_LGBT_ALIASES_RAW = {"lgbt","lgbtq","lgbtq+","nonbinary","non-binary","nb","enby","trans","genderqueer","bigender","agender","genderfluid","queer","อื่น","เพศทางเลือก"}
_GENDER_UNDISCLOSED_ALIASES_RAW = {"ไม่ระบุ","ไม่บอก","ไม่อยากเปิดเผย","prefernottosay","undisclosed","unknown","private","secret","na","n/a","-"}

MALE_ALIASES   = {_norm_gender(x) for x in _MALE_ALIASES_RAW}
FEMALE_ALIASES = {_norm_gender(x) for x in _FEMALE_ALIASES_RAW}
LGBT_ALIASES   = {_norm_gender(x) for x in _LGBT_ALIASES_RAW}
GENDER_UNDISCLOSED_ALIASES = {_norm_gender(x) for x in _GENDER_UNDISCLOSED_ALIASES_RAW}

MALE_PREFIXES   = {_norm_gender(x) for x in ["ช","ชา","ชาย","ผู้ช","เพศช","m","ma","man"]}
FEMALE_PREFIXES = {_norm_gender(x) for x in ["ห","หญ","หญิ","หญิง","ผู้ห","เพศห","f","fe","woman"]}

def resolve_gender_role_id(text: str) -> int:
    from .config import ROLE_MALE, ROLE_FEMALE, ROLE_LGBT, ROLE_GENDER_UNDISCLOSED
    t = _norm_gender(text)
    if t in MALE_ALIASES or any(t.startswith(p) for p in MALE_PREFIXES):
        return ROLE_MALE
    if t in FEMALE_ALIASES or any(t.startswith(p) for p in FEMALE_PREFIXES):
        return ROLE_FEMALE
    if t in LGBT_ALIASES:
        return ROLE_LGBT
    if t in GENDER_UNDISCLOSED_ALIASES:
        return ROLE_GENDER_UNDISCLOSED
    return ROLE_GENDER_UNDISCLOSED

# Age handling
def _norm_simple(s: str) -> str:
    return re.sub(r'[\s\.\-_\/\\]+', '', (s or '').strip().lower())
_AGE_UNDISCLOSED_ALIASES_RAW = {"ไม่ระบุ","ไม่บอก","prefernottosay","undisclosed","unknown","private","na","n/a","x","-","—"}
AGE_UNDISCLOSED_ALIASES = {_norm_simple(x) for x in _AGE_UNDISCLOSED_ALIASES_RAW}

def is_age_undisclosed(text: str) -> bool:
    t = _norm_simple(text)
    return (t == "") or (t in AGE_UNDISCLOSED_ALIASES)

def resolve_age_role_id(age_text: str) -> int | None:
    from .config import (
        ROLE_0_12, ROLE_13_15, ROLE_16_18, ROLE_19_21, ROLE_22_24, ROLE_25_29, ROLE_30_34,
        ROLE_35_39, ROLE_40_44, ROLE_45_49, ROLE_50_54, ROLE_55_59, ROLE_60_64, ROLE_65_UP,
        ROLE_AGE_UNDISCLOSED
    )
    if is_age_undisclosed(age_text):
        return ROLE_AGE_UNDISCLOSED
    try:
        age = int((age_text or "").strip())
    except ValueError:
        return None
    slots = [
        ((0, 12), ROLE_0_12),
        ((13, 15), ROLE_13_15),
        ((16, 18), ROLE_16_18),
        ((19, 21), ROLE_19_21),
        ((22, 24), ROLE_22_24),
        ((25, 29), ROLE_25_29),
        ((30, 34), ROLE_30_34),
        ((35, 39), ROLE_35_39),
        ((40, 44), ROLE_40_44),
        ((45, 49), ROLE_45_49),
        ((50, 54), ROLE_50_54),
        ((55, 59), ROLE_55_59),
        ((60, 64), ROLE_60_64),
        ((65, 200), ROLE_65_UP),
    ]
    for (lo, hi), rid in slots:
        if lo <= age <= hi and rid > 0:
            return rid
    return None

# Birthday helpers
_BDAY_RE = re.compile(r"^\s*(\d{1,2})[\/\.\-](\d{1,2})[\/\.\-](\d{4})\s*$")
def parse_birthday(text: str) -> datetime | None:
    if not text: return None
    m = _BDAY_RE.match(text)
    if not m: return None
    d, mth, y = map(int, m.groups())
    try:
        dt = datetime(y, mth, d, 0, 0, tzinfo=TH_TZ)
    except ValueError:
        return None
    now = datetime.now(TH_TZ)
    if dt > now: return None
    if y < 1900 or y > now.year: return None
    return dt

def _years_between(a: datetime, b: datetime) -> int:
    years = b.year - a.year
    if (b.month, b.day) < (a.month, a.day):
        years -= 1
    return max(years, 0)

def age_from_birthday(bday: datetime, now_local: datetime | None = None) -> int:
    now_local = now_local or datetime.now(TH_TZ)
    return _years_between(bday, now_local)

# Admin notify
async def notify_admin(guild: discord.Guild, text: str):
    try:
        ch = guild.get_channel(ADMIN_NOTIFY_CHANNEL_ID) or guild.get_channel(APPROVAL_CHANNEL_ID)
        if ch:
            await ch.send(f"🔔 **Admin Notice:** {text}")
    except Exception:
        pass

# Risk
from datetime import timezone as _dt_timezone
def assess_account_risk_age_only(user: discord.User) -> tuple[int | None, str, list[str]]:
    try:
        created_at = user.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=_dt_timezone.utc)
        now = datetime.now(_dt_timezone.utc)
        age_days = (now - created_at).days
    except Exception:
        return None, "UNKNOWN", ["cannot compute account age"]

    reasons = []
    if age_days < MIN_ACCOUNT_AGE_DAYS_HIGH:
        reasons.append(f"age<{MIN_ACCOUNT_AGE_DAYS_HIGH}d")
        return age_days, "HIGH", reasons
    if age_days < MIN_ACCOUNT_AGE_DAYS_MED:
        reasons.append(f"age<{MIN_ACCOUNT_AGE_DAYS_MED}d")
        return age_days, "MED", reasons
    return age_days, "LOW", reasons

def build_account_check_field(user: discord.User) -> tuple[str, str, str, int | None]:
    age_days, risk, reasons = assess_account_risk_age_only(user)
    icon = "⚠️" if risk == "HIGH" else ("🟧" if risk == "MED" else ("🟩" if risk == "LOW" else "❔"))
    age_txt = "—" if age_days is None else f"{age_days} days"
    reason_txt = f" • Reasons: {', '.join(reasons)}" if reasons else ""
    name = "🛡️ Account Check"
    value = f"Account age: {age_txt} • Risk: {risk} {icon}{reason_txt}"
    return name, value, risk, age_days
