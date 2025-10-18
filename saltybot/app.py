import os
from discord.ext import commands

bot = commands.Bot(command_prefix="$", intents=... )  # ตามที่คุณเซ็ต

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")

async def main():
    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        raise RuntimeError("DISCORD_BOT_TOKEN not set")
    # bot.run เป็นบล็อกซิงก์ ให้ใช้ start + wait_closed ถ้าคุณอยาก pure-async
    bot.run(token)
