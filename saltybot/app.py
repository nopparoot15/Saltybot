import os
import discord
from discord.ext import commands

# ตั้งค่า Intents ให้เป็นของจริง (ห้ามใช้ ... )
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

# อ่าน prefix จาก ENV ได้ด้วย (ไม่มีให้ใช้ $)
bot = commands.Bot(
    command_prefix=os.getenv("COMMAND_PREFIX", "$"),
    intents=intents,
)

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")
    # ถ้ามี Persistent View/Sync commands ใส่เพิ่มตรงนี้ได้
    # bot.add_view(YourPersistentView())

def main():
    token = os.environ["DISCORD_BOT_TOKEN"]
    bot.run(token)

if __name__ == "__main__":
    main()
