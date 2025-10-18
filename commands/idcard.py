from discord.ext import commands
import discord
from config import APPROVAL_CHANNEL_ID, HIDE_BIRTHDAY_ON_IDCARD
from ui.messages import copy_embed_fields, mask_birthday_field_for_idcard

class IDCardCog(commands.Cog):
    def __init__(self, bot): self.bot = bot

    @commands.command(name="idcard")
    async def idcard(self, ctx: commands.Context, *, who: str = None):
        member = None
        if ctx.message.mentions:
            member = ctx.message.mentions[0]
        elif who:
            try:
                member = await commands.MemberConverter().convert(ctx, who)
            except commands.BadArgument:
                member = None
        if member is None:
            member = ctx.author

        if member.id != ctx.author.id and not ctx.author.guild_permissions.administrator:
            await ctx.send("❌ คุณสามารถดูบัตรของ **ตัวเอง** ได้เท่านั้น"); return

        ch = ctx.guild.get_channel(APPROVAL_CHANNEL_ID)
        if not ch: return await ctx.send("❌ APPROVAL_CHANNEL_ID not found.")

        async for m in ch.history(limit=200):
            if (m.author == self.bot.user and m.embeds and m.mentions and member in m.mentions):
                src = m.embeds[0]
                e = copy_embed_fields(src)
                e.title = "🪪 ID Card / บัตรยืนยันตัวตน"
                mask_birthday_field_for_idcard(e)
                return await ctx.send(embed=e)

        await ctx.send("❌ No verification info found for this user.")

async def setup(bot):
    await bot.add_cog(IDCardCog(bot))
