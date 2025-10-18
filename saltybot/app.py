import os
import discord
from discord.ext import commands
from saltybot.config import BOT_PREFIX, AUTO_REFRESH_ENABLED, HBD_NOTIFY_ENABLED
from saltybot.verification.daemons import start_age_refresh_daemon, start_birthday_daemon

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix=BOT_PREFIX, intents=intents)

# --- load cogs/commands for verification ---
from saltybot.verification.commands import setup as setup_verification_commands
from saltybot.verification.views import PersistentVerificationView

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    bot.add_view(PersistentVerificationView())  # keep buttons alive
    if AUTO_REFRESH_ENABLED and not getattr(bot, "_age_refresh_daemon_started", False):
        start_age_refresh_daemon(bot)
        bot._age_refresh_daemon_started = True
    if HBD_NOTIFY_ENABLED and not getattr(bot, "_birthday_daemon_started", False):
        start_birthday_daemon(bot)
        bot._birthday_daemon_started = True

async def setup_bot():
    await setup_verification_commands(bot)

def run():
    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        raise RuntimeError("Missing DISCORD_BOT_TOKEN")
    bot.loop.create_task(setup_bot())
    bot.run(token)

if __name__ == "__main__":
    run()
