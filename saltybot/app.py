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

# ---------- Intents ----------
intents = discord.Intents.default()
intents.message_content = True   # ต้องเปิดเพื่ออ่านคำสั่งข้อความ
intents.guilds = True
intents.members = True           # ใช้กับ role/nickname และ modal interactions

# ---------- Bot ----------
bot = commands.Bot(command_prefix="$", intents=intents)

# (ถ้าคุณมี help เดิม จะถอดของ lib ออกก่อน)
try:
    bot.remove_command("help")
except Exception:
    pass

# ---------- โหลดคอมมานด์ & วิวจากโมดูลของเรา ----------
def _register_features():
    # ลงทะเบียนคำสั่งแบบฟังก์ชัน (ไม่ใช้ extension system เพื่อลดความสับซ้อน)
    from saltybot.verification.commands import register_commands
    register_commands(bot)

    # เพิ่ม persistent view สำหรับปุ่ม Verify
    from saltybot.verification.views import VerificationView
    bot.add_view(VerificationView())  # ทำให้ปุ่มบนข้อความเก่ากดได้หลังรีสตาร์ท

@bot.event
async def on_ready():
    log.info("✅ Logged in as %s (ID: %s)", bot.user, bot.user.id)
    # ตรงนี้ safe เพราะ add_view เรียกซ้ำจะไม่มีผลข้างเคียงที่ไม่ดี
    try:
        from saltybot.verification.views import VerificationView
        bot.add_view(VerificationView())
    except Exception as e:
        log.exception("add_view failed: %s", e)

def main():
    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        log.error("Environment variable DISCORD_BOT_TOKEN is not set.")
        raise SystemExit(1)

    # ลงทะเบียนคำสั่ง/วิวก่อน run
    _register_features()

    # รันบอท
    bot.run(token)

if __name__ == "__main__":
    main()
