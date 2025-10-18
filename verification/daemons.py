import asyncio
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from saltybot.config import (
    AUTO_REFRESH_ENABLED, REFRESH_TZ, REFRESH_FREQUENCY,
    REFRESH_AT_HOUR, REFRESH_AT_MINUTE, REFRESH_AT_DAY, REFRESH_AT_MONTH, REFRESH_AT_WEEKDAY,
    LOG_CHANNEL_ID, HBD_NOTIFY_ENABLED, HBD_NOTIFY_HOUR, HBD_NOTIFY_MINUTE
)
from saltybot.utils.timez import now_bkk
from .refresh import refresh_age_single
from .birthday import parse_birthday, age_from_birthday
from saltybot.constants import AGE_ROLE_IDS_ALL
from saltybot.config import BIRTHDAY_CHANNEL_ID, HBD_MESSAGES
from .indexer import find_embed_field, latest_verification_embed_for

def _refresh_period_tag(now_local: datetime, freq: str) -> str:
    if freq == "YEARLY":  return f"[AGE-REFRESH] {now_local.year}"
    if freq == "MONTHLY": return f"[AGE-REFRESH] {now_local.year}-{now_local.month:02d}"
    if freq == "WEEKLY":
        iso = now_local.isocalendar()
        return f"[AGE-REFRESH] {iso.year}-W{iso.week:02d}"
    if freq == "DAILY":   return f"[AGE-REFRESH] {now_local.date().isoformat()}"
    return f"[AGE-REFRESH] {now_local.year}-{now_local.month:02d}"

async def _already_ran_this_period(log_ch, tz: ZoneInfo, freq: str) -> bool:
    now = datetime.now(tz)
    tag = _refresh_period_tag(now, freq)
    async for m in log_ch.history(limit=200):
        if m.author == m.guild.me and m.content and tag in m.content:
            return True
    return False

def _last_day_of_month(year: int, month: int) -> int:
    if month == 12:
        n = datetime(year+1, 1, 1, tzinfo=REFRESH_TZ)
    else:
        n = datetime(year, month+1, 1, tzinfo=REFRESH_TZ)
    return (n - timedelta(days=1)).day

def _compute_next_run_local(now_local: datetime) -> datetime:
    h, mi = REFRESH_AT_HOUR, REFRESH_AT_MINUTE
    f = REFRESH_FREQUENCY.upper()
    if f == "YEARLY":
        y = now_local.year; m = max(1, min(12, REFRESH_AT_MONTH))
        d = max(1, min(_last_day_of_month(y, m), REFRESH_AT_DAY))
        t = datetime(y, m, d, h, mi, tzinfo=REFRESH_TZ)
        if now_local >= t: t = datetime(y+1, m, max(1, min(_last_day_of_month(y+1,m), REFRESH_AT_DAY)), h, mi, tzinfo=REFRESH_TZ)
        return t
    if f == "MONTHLY":
        y, m = now_local.year, now_local.month
        d = max(1, min(_last_day_of_month(y, m), REFRESH_AT_DAY))
        t = datetime(y, m, d, h, mi, tzinfo=REFRESH_TZ)
        if now_local >= t:
            if m == 12: y+=1; m=1
            else: m+=1
            d = max(1, min(_last_day_of_month(y, m), REFRESH_AT_DAY))
            t = datetime(y, m, d, h, mi, tzinfo=REFRESH_TZ)
        return t
    if f == "WEEKLY":
        weekday = max(0, min(6, REFRESH_AT_WEEKDAY))
        days_ahead = (weekday - now_local.weekday()) % 7
        t = (now_local + timedelta(days=days_ahead)).replace(hour=h, minute=mi, second=0, microsecond=0)
        if now_local >= t: t = t + timedelta(days=7)
        return t
    # DAILY
    t = now_local.replace(hour=h, minute=mi, second=0, microsecond=0)
    if now_local >= t: t = t + timedelta(days=1)
    return t

def start_age_refresh_daemon(bot):
    async def runner():
        await bot.wait_until_ready()
        while not bot.is_closed():
            now_utc = datetime.now(tz=ZoneInfo("UTC"))
            now_local = now_utc.astimezone(REFRESH_TZ)
            target_local = _compute_next_run_local(now_local)
            target_utc = target_local.astimezone(ZoneInfo("UTC"))
            sleep_sec = max(1, int((target_utc - now_utc).total_seconds()))
            await asyncio.sleep(sleep_sec)
            for guild in bot.guilds:
                log_ch = guild.get_channel(LOG_CHANNEL_ID)
                if not log_ch: continue
                if await _already_ran_this_period(log_ch, REFRESH_TZ, REFRESH_FREQUENCY):
                    continue
                changed = 0; errors = 0; total = 0
                for m in guild.members:
                    ok, _ = await refresh_age_single(guild, m)
                    total += 1
                    if ok: changed += 1
                await log_ch.send(_refresh_period_tag(datetime.now(REFRESH_TZ), REFRESH_FREQUENCY) + f" • Members: {total} • Changed≈{changed} • Errors≈{errors}\n✅ DONE")
    bot.loop.create_task(runner())

def start_birthday_daemon(bot):
    async def runner():
        await bot.wait_until_ready()
        while not bot.is_closed():
            now_utc = datetime.now(tz=ZoneInfo("UTC"))
            now_local = now_utc.astimezone(REFRESH_TZ)
            target_local = now_local.replace(hour=HBD_NOTIFY_HOUR, minute=HBD_NOTIFY_MINUTE, second=0, microsecond=0)
            if now_local >= target_local: target_local = target_local + timedelta(days=1)
            target_utc = target_local.astimezone(ZoneInfo("UTC"))
            await asyncio.sleep(max(1, int((target_utc - now_utc).total_seconds())))
            for guild in bot.guilds:
                await _send_hbd_today(guild)
    bot.loop.create_task(runner())

async def _send_hbd_today(guild):
    tz = REFRESH_TZ
    today0 = datetime.now(tz).replace(hour=0, minute=0, second=0, microsecond=0)
    today_md = (today0.month, today0.day)
    hbd_ch = guild.get_channel(BIRTHDAY_CHANNEL_ID)
    log_ch = guild.get_channel(LOG_CHANNEL_ID)
    if not hbd_ch or not log_ch: return

    for member in guild.members:
        embed = await latest_verification_embed_for(member)
        if not embed: continue
        btxt = find_embed_field(embed, "birthday", "วันเกิด")
        if not btxt: continue
        bdt = parse_birthday(str(btxt))
        if not bdt: continue
        if (bdt.month, bdt.day) != today_md: continue
        # sync role from birthday
        years = age_from_birthday(bdt)
        # (สั้น ๆ: ปล่อยให้ refresh daemon จัดเต็ม; ที่นี่โพสต์อวยพร)
        idx = ((member.id or 0) + today0.year) % len(HBD_MESSAGES)
        template = HBD_MESSAGES[idx]
        try:
            await hbd_ch.send(template.format(mention=member.mention))
        except Exception:
            if log_ch: await log_ch.send(f"❌ HBD ส่งไม่สำเร็จสำหรับ {member.mention}")
