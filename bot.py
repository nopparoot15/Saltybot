import asyncio, discord
from discord.ext import commands
from config import DISCORD_BOT_TOKEN
from ui.views import VerificationView, ApproveRejectPersistent

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="$", intents=intents)

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    bot.add_view(VerificationView())
    bot.add_view(ApproveRejectPersistent())

async def load_cogs():
    await bot.load_extension("commands.verify_embed")
    await bot.load_extension("commands.idcard")
    await bot.load_extension("commands.admin")
    await bot.load_extension("commands.help")

async def main():
    async with bot:
        await load_cogs()
        await bot.start(DISCORD_BOT_TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
