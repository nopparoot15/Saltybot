from discord.ext import commands
import discord
from config import VERIFY_CHANNEL_ID
from ui.views import VerificationView

class VerifyEmbedCog(commands.Cog):
    def __init__(self, bot): self.bot = bot

    @commands.command(name="verify_embed")
    @commands.has_permissions(administrator=True)
    async def verify_embed(self, ctx: commands.Context):
        ch = ctx.guild.get_channel(VERIFY_CHANNEL_ID)
        if not ch: return await ctx.send("❌ VERIFY_CHANNEL_ID not found.")
        embed = discord.Embed(
            title="📌 Welcome / ยินดีต้อนรับ",
            description="Click the button below to verify your identity.\nกดปุ่มด้านล่างเพื่อยืนยันตัวตนของคุณ",
            color=discord.Color.blue()
        )
        await ch.send(embed=embed, view=VerificationView())
        await ctx.send(f"✅ Verification embed sent to {ch.mention}")

async def setup(bot):
    await bot.add_cog(VerifyEmbedCog(bot))
