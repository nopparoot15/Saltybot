import os
import sys
import logging
import discord
from discord.ext import commands

# ---------- Logging ----------
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    stream=sys.stdout,
)
log = logging.getLogger("saltybot")

# ---------- Intents (ต้องเป็น discord.Intents ไม่ใช่ ...) ----------
intents = discord.Intents.default()
# ต้องเปิดใน Discord Developer Portal ด้วย ถ้าจะใช้สองอันนี้
intents.message_content = True   # อ่านข้อความเพื่อโต้ตอบคำสั่ง prefix ได้
intents.members = True           # ถ้าบอทต้องอ่านรายชื่อสมาชิก
intents.guilds = True

# ---------- Bot ----------
bot = commands.Bot(
    command_prefix=os.getenv("COMMAND_PREFIX", "$"),
    intents=intents,
    help_command=None,  # ปิด help เริ่มต้น ถ้าคุณมีของตัวเอง
)

@bot.event
async def on_ready():
    log.info("✅ Logged in as %s (ID: %s)", bot.user, bot.user.id)
    # ตั้งสถานะบอท (ตามใจชอบ)
    await bot.change_presence(activity=discord.Game(name=os.getenv("BOT_STATUS", "online")))

# ตัวอย่างคำสั่งง่าย ๆ (ลบได้)
@bot.command(name="ping")
async def ping(ctx: commands.Context):
    await ctx.reply("pong")

def _load_extensions():
    """
    ถ้าคุณมี cogs/extensions อยู่ที่ saltybot/cogs/
    ให้วนโหลดอัตโนมัติ (ไม่มีก็ไม่เป็นไร)
    """
    try:
        import pkgutil
        import importlib

        package = "saltybot.cogs"
        try:
            importlib.import_module(package)
        except ModuleNotFoundError:
            # ไม่มีโฟลเดอร์ cogs ก็ข้ามไป
            return

        for mod in pkgutil.iter_modules(importlib.import_module(package).__path__):
            name = f"{package}.{mod.name}"
            try:
                bot.load_extension(name)
                log.info("Loaded extension: %s", name)
            except Exception as e:
                log.exception("Failed to load extension %s: %s", name, e)
    except Exception as e:
        log.exception("Extension loading error: %s", e)

def main():
    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        log.error("Environment variable DISCORD_BOT_TOKEN is not set.")
        raise SystemExit(1)

    _load_extensions()
    # หมายเหตุ: ถ้าใช้ discord.py 2.x ไม่ควรทำ bot.run ใน asyncio loop อื่น
    bot.run(token)

if __name__ == "__main__":
    main()
