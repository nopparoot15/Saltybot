from discord.ext import commands
import discord

_SHORT_DESC = {
    "help": "แสดงรายการคำสั่งทั้งหมด หรือรายละเอียดของคำสั่งที่ระบุ",
    "verify_embed": "ส่ง Embed ปุ่มยืนยันตัวตนไปยังห้อง VERIFY_CHANNEL_ID",
    "idcard": "ดู ID Card ของตัวเอง; ดูของคนอื่นได้เฉพาะแอดมิน",
    "reverify": "บังคับให้สมาชิกยืนยันตัวตนใหม่ (ลบ roles)",
}

_ADMIN_COMMANDS = {"verify_embed", "reverify"}

def _fmt_cmd_list(prefix: str, names: list[str]) -> str:
    lines = []
    for n in names:
        desc = _SHORT_DESC.get(n, "-")
        lines.append(f"• **{prefix}{n}** — {desc}")
    return "\n".join(lines) if lines else "—"

class HelpCog(commands.Cog):
    def __init__(self, bot): self.bot = bot

    @commands.command(name="help", aliases=["commands","คำสั่ง","วิธีใช้"])
    async def help(self, ctx: commands.Context, *, command_name: str = None):
        prefix = ctx.prefix or "$"
        if command_name:
            cmd = self.bot.get_command(command_name.lower())
            if not cmd:
                await ctx.send(f"❌ ไม่พบคำสั่งชื่อ `{command_name}`"); return
            name = cmd.name
            desc_short = _SHORT_DESC.get(name, cmd.help or "-")
            embed = discord.Embed(title=f"ℹ️ วิธีใช้คำสั่ง: {prefix}{name}", description=desc_short, color=discord.Color.blurple())
            await ctx.send(embed=embed); return

        all_cmds = {c.name for c in self.bot.commands if not c.hidden}
        general = sorted(all_cmds - _ADMIN_COMMANDS | {"help"})
        admin = sorted(all_cmds & _ADMIN_COMMANDS)
        embed = discord.Embed(title="📜 รายการคำสั่งทั้งหมด", description=f"พิมพ์ `{prefix}help <คำสั่ง>` เพื่อดูวิธีใช้แบบละเอียด", color=discord.Color.green())
        embed.add_field(name="ทั่วไป", value=_fmt_cmd_list(prefix, general), inline=False)
        embed.add_field(name="สำหรับผู้ดูแล", value=_fmt_cmd_list(prefix, admin), inline=False)
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(HelpCog(bot))
