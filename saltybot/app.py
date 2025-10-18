# saltybot/app.py
import os
import asyncio
import logging
from typing import Optional

import discord
from discord.ext import commands

# ---------- logging พื้นฐาน ----------
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
log = logging.getLogger("saltybot.app")

# ---------- DB pool ----------
from .db import init_pool, close_pool

# ---------- ส่วน verify (commands + views + daemons) ----------
# รองรับทั้งชื่อที่คุณตั้งไว้ (ในโค้ดเก่า) และชื่อที่ผมเสนอ
try:
    # ถ้าเคยแยกเป็นโมดูลตามที่ออกแบบ
    from .verification.commands import setup as setup_verification_commands
except Exception as e:
    setup_verification_commands = None
    log.warning("cannot import setup_verification_commands: %r", e)

PersistentVerificationView = None
VerificationView = None
try:
    from .verification.views import PersistentVerificationView as _PVV
    PersistentVerificationView = _PVV
except Exception:
    try:
        # โค้ดเดิมคุณใช้ชื่อ VerificationView
        from .verification.views import VerificationView as _VV
        VerificationView = _VV
    except Exception as e:
        log.warning("cannot import VerificationView/PersistentVerificationView: %r", e)

# daemons (อาจมีหรือยังไม่แยก ถ้าไม่มีจะข้าม)
start_age_refresh_daemon = None
start_birthday_daemon = None
try:
    from .verification.daemons import start_age_refresh_daemon as _start_age_refresh_daemon
    start_age_refresh_daemon = _start_age_refresh_daemon
except Exception:
    pass

try:
    from .verification.daemons import start_birthday_daemon as _start_birthday_daemon
    start_birthday_daemon = _start_birthday_daemon
except Exception:
    pass


# ========== Discord Bot ==========
def build_intents() -> discord.Intents:
    intents = discord.Intents.default()
    intents.message_content = True          # ใช้จริงอยู่แล้วในโปรเจกต์
    intents.guilds = True
    intents.members = True                  # ต้องเปิดที่ Developer Portal ด้วย
    return intents


def build_bot() -> commands.Bot:
    prefix = os.getenv("BOT_PREFIX", "$")
    return commands.Bot(command_prefix=prefix, intents=build_intents())


bot = build_bot()


@bot.event
async def on_ready():
    log.info("✅ Logged in as %s (%s)", bot.user, bot.user.id if bot.user else "-")
    # เพิ่ม persistent view สำหรับปุ่ม Verify
    try:
        if PersistentVerificationView is not None:
            bot.add_view(PersistentVerificationView())
            log.info("PersistentVerificationView added")
        elif VerificationView is not None:
            bot.add_view(VerificationView())
            log.info("VerificationView added (fallback)")
        else:
            log.warning("No verification view available to add")
    except Exception as e:
        log.exception("add_view failed: %r", e)

    # สตาร์ท daemons ถ้ามีให้เรียก
    # ใช้ flag กันซ้ำเมื่อ Discord reconnect
    if start_age_refresh_daemon and not getattr(bot, "_age_refresh_started", False):
        try:
            start_age_refresh_daemon(bot)  # ภายในควรทำ create_task เอง
            bot._age_refresh_started = True
            log.info("Age refresh daemon started")
        except Exception:
            log.exception("start_age_refresh_daemon failed")

    if start_birthday_daemon and not getattr(bot, "_birthday_started", False):
        try:
            start_birthday_daemon(bot)
            bot._birthday_started = True
            log.info("Birthday daemon started")
        except Exception:
            log.exception("start_birthday_daemon failed")


@bot.event
async def setup_hook():
    """
    เรียกก่อน on_ready: ใช้เตรียมระบบภายใน เช่น DB และโหลดคำสั่งของ verify
    """
    # เปิด DB pool ไว้ก่อน
    await init_pool()
    log.info("DB pool initialized")

    # โหลดชุดคำสั่ง verification (prefix/slash แล้วแต่ที่คุณทำในโมดูล)
    if setup_verification_commands:
        try:
            await setup_verification_commands(bot)
            log.info("verification commands loaded")
        except Exception:
            log.exception("setup_verification_commands failed")


async def _shutdown():
    """
    ปิดทุกอย่างอย่างนุ่มนวลตอนโปรเซสกำลังจะลง
    """
    try:
        await close_pool()
        log.info("DB pool closed")
    except Exception:
        log.exception("close_pool failed")

    # รอให้ Discord ปิด connection
    try:
        await bot.close()
    except Exception:
        pass


async def _runner():
    """
    ตัวรันหลัก: เปิดบอท + จัดการ shutdown
    """
    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        raise RuntimeError("DISCORD_BOT_TOKEN is not set")

    # จัดการสัญญาณ (ถ้าอยู่บน Linux container)
    stop_event = asyncio.Event()

    def _handle_signal():
        stop_event.set()

    try:
        import signal
        loop = asyncio.get_running_loop()
        for s in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(s, _handle_signal)
            except NotImplementedError:
                # บางแพลตฟอร์ม (เช่น Windows/บาง container) อาจใช้ไม่ได้
                pass
    except Exception:
        pass

    # สตาร์ทบอทใน task แยก เพื่อให้เรารอ stop_event ได้
    bot_task = asyncio.create_task(bot.start(token))

    # รอจนกว่าจะโดนสั่งหยุด
    await stop_event.wait()

    # ปิดงาน
    log.info("Shutting down...")
    try:
        # discord.py จะยุติเองเมื่อ bot.close()
        await _shutdown()
    finally:
        # กันไม่ให้ค้าง
        try:
            await asyncio.wait_for(bot_task, timeout=10)
        except Exception:
            bot_task.cancel()


def main():
    asyncio.run(_runner())


if __name__ == "__main__":
    main()
