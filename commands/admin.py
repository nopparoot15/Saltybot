from discord.ext import commands
import discord
from config import ROLE_ID_TO_GIVE, GENDER_ROLE_IDS_ALL, AGE_ROLE_IDS_ALL
from utils.auth import is_moderator

class AdminCog(commands.Cog):
    def __init__(self, bot): self.bot = bot

    @commands.command(name="reverify")
    @commands.has_permissions(manage_roles=True)
    async def reverify(self, ctx: commands.Context, member: discord.Member):
        to_remove = [r for r in member.roles if r.id in {ROLE_ID_TO_GIVE, *GENDER_ROLE_IDS_ALL, *AGE_ROLE_IDS_ALL}]
        if to_remove:
            await member.remove_roles(*to_remove, reason="Force re-verification")
        await ctx.send(f"✅ สั่งให้ {member.mention} ยืนยันตัวตนใหม่แล้ว (roles cleared)")

async def setup(bot):
    await bot.add_cog(AdminCog(bot))
