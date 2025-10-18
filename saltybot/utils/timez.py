from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

def years_between(a: datetime, b: datetime) -> int:
    years = b.year - a.year
    if (b.month, b.day) < (a.month, a.day):
        years -= 1
    return max(years, 0)

def now_bkk():
    return datetime.now(ZoneInfo("Asia/Bangkok"))

def parse_local_dt_ddmmyyyy_hhmm(s: str):
    try:
        from zoneinfo import ZoneInfo
        dt = datetime.strptime(s.strip(), "%d/%m/%Y %H:%M")
        return dt.replace(tzinfo=ZoneInfo("Asia/Bangkok"))
    except Exception:
        return None
