from discord.ext import commands

def bot_can_edit_member_and_role(ctx: commands.Context, member, role=None):
    bot_me = ctx.guild.me
    if not bot_me:
        return False, "❌ ไม่พบสถานะของบอทในกิลด์"
    if bot_me.top_role <= member.top_role or member.id == ctx.guild.owner_id:
        return False, "❌ บอทไม่มีลำดับยศสูงพอที่จะจัดการสมาชิกคนนี้"
    if role and bot_me.top_role <= role:
        return False, f"❌ บอทไม่มีลำดับยศสูงพอที่จะจัดการยศ: {role.name}"
    return True, ""
