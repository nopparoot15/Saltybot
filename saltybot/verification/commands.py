import re, io, discord
from discord.ext import commands
from saltybot.config import VERIFY_CHANNEL_ID, APPROVAL_CHANNEL_ID, LOG_CHANNEL_ID, BIRTHDAY_CHANNEL_ID, HIDE_BIRTHDAY_ON_IDCARD
from saltybot.constants import (
    ROLE_ID_TO_GIVE, GENDER_ROLE_IDS_ALL, AGE_ROLE_IDS_ALL, ROLE_AGE_UNDISCLOSED
)
from saltybot.permissions import bot_can_edit_member_and_role
from saltybot.utils.text import INVALID_CHARS, contains_emoji, canon_full
from saltybot.utils.discord_helpers import base_display_name, discord_names_set
from saltybot.utils.admin_notify import notify_admin
from saltybot.verification.views import PersistentVerificationView
from saltybot.verification.embeds import copy_embed_fields, mask_birthday_field_for_idcard
from saltybot.verification.indexer import find_latest_approval_message, set_or_add_field, latest_verification_embed_for
from saltybot.verification.refresh import refresh_age_single
from saltybot.verification.age import resolve_age_role_id, is_age_undisclosed
from saltybot.verification.gender import resolve_gender_role_id
from saltybot.verification.birthday import parse_birthday, age_from_birthday
from saltybot.verification.state import pending_clear

async def setup(bot: commands.Bot):
    @bot.command(name="verify_embed")
    @commands.has_permissions(administrator=True)
    async def verify_embed(ctx):
        channel = ctx.guild.get_channel(VERIFY_CHANNEL_ID)
        if not channel: await ctx.send("❌ VERIFY_CHANNEL_ID not found."); return
        embed = discord.Embed(title="📌 Welcome / ยินดีต้อนรับ",
                              description="Click the button below to verify your identity.\nกดปุ่มด้านล่างเพื่อยืนยันตัวตนของคุณ",
                              color=discord.Color.blue())
        embed.set_footer(text="Verification System / ระบบยืนยันตัวตนโดย Bot")
        await channel.send(embed=embed, view=PersistentVerificationView())
        await ctx.send(f"✅ Verification embed sent to {channel.mention}")

    @bot.command(name="idcard", aliases=["userinfo"])
    async def idcard(ctx, *, who: str=None):
        # self or admin to view others
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

        channel = ctx.guild.get_channel(APPROVAL_CHANNEL_ID)
        if not channel: await ctx.send("❌ APPROVAL_CHANNEL_ID not found."); return

        async for message in channel.history(limit=200):
            if (message.author == bot.user and message.embeds and message.mentions and member in message.mentions):
                e0 = message.embeds[0]
                e = copy_embed_fields(e0)
                e.title = "🪪 ID Card / บัตรยืนยันตัวตน"
                mask_birthday_field_for_idcard(e)
                await ctx.send(embed=e)
                return
        await ctx.send("❌ No verification info found for this user.")

    @bot.command(name="refresh_age")
    @commands.has_permissions(administrator=True)
    async def refresh_age_cmd(ctx, member: discord.Member):
        ok, info = await refresh_age_single(ctx.guild, member)
        if ok: await ctx.send(f"✅ อัปเดตยศอายุของ {member.mention} แล้ว ({info})")
        else:  await ctx.send(f"❌ ไม่สำเร็จ: {info}")

    @bot.command(name="refresh_age_all")
    @commands.has_permissions(administrator=True)
    async def refresh_age_all(ctx):
        await ctx.send("⏳ กำลังรีเฟรชอายุทั้งเซิร์ฟเวอร์...")
        changed = 0
        for m in ctx.guild.members:
            ok, _ = await refresh_age_single(ctx.guild, m)
            if ok: changed += 1
        await ctx.send(f"✅ เสร็จสิ้น • Changed≈{changed}")

    CLEAR_ALIASES = {"clear","reset","remove","none","no","x","-","—","ลบ","เอาออก","ไม่ใช้","ไม่ใส่","ไม่ต้อง"}

    @bot.command(name="setnick", aliases=["nick","ชื่อเล่น","ปรับชื่อเล่น"])
    @commands.has_permissions(manage_nicknames=True)
    async def setnick(ctx, member: discord.Member, *, nickname: str):
        ok, msg = bot_can_edit_member_and_role(ctx, member, None)
        if not ok: await ctx.send(msg); return

        def want_clear(s: str): 
            return (s.strip()=="") or (s.strip().lower() in CLEAR_ALIASES)

        if want_clear(nickname):
            base = base_display_name(member)
            try:
                await member.edit(nick=base, reason="Admin: clear form nickname")
                await ctx.send(f"✅ เอาวงเล็บชื่อเล่นออกแล้ว → `{base}` (เป้าหมาย: {member.mention})")
            except: await ctx.send("❌ บอทไม่มีสิทธิ์พอในการแก้ชื่อคนนี้"); return
            msg = await find_latest_approval_message(ctx.guild, member)
            if msg:
                e = msg.embeds[0]
                set_or_add_field(e, ("nickname","ชื่อเล่น"), "Nickname / ชื่อเล่น", "ไม่ระบุ")
                try: await msg.edit(embed=e)
                except: pass
            return

        if len(nickname) < 2 or len(nickname) > 10 or any(ch.isdigit() for ch in nickname) or any(c in INVALID_CHARS for c in nickname) or contains_emoji(nickname):
            await ctx.send("❌ ชื่อเล่นไม่ถูกต้อง (ตัวอักษร 2–10, ห้ามตัวเลข/สัญลักษณ์/อีโมจิ)"); return
        if canon_full(nickname) in discord_names_set(member, canon_full):
            await ctx.send("❌ ชื่อเล่นต้องต่างจากชื่อในดิสคอร์ดของเป้าหมายจริง ๆ"); return
        base = base_display_name(member)
        new_nick = f"{base} ({nickname})" if len(f"{base} ({nickname})")<=32 else nickname[:32]
        try:
            await member.edit(nick=new_nick, reason=f"Admin: set form nickname → {nickname}")
            await ctx.send(f"✅ ตั้งชื่อเป็น `{new_nick}` ให้ {member.mention}")
        except: await ctx.send("❌ แก้ชื่อไม่สำเร็จ"); return

        msg = await find_latest_approval_message(ctx.guild, member)
        if msg:
            e = msg.embeds[0]
            set_or_add_field(e, ("nickname","ชื่อเล่น"), "Nickname / ชื่อเล่น", nickname)
            try: await msg.edit(embed=e)
            except: pass

    @bot.command(name="setgender", aliases=["gender","เพศ","ปรับเพศ"])
    @commands.has_permissions(manage_roles=True)
    async def setgender(ctx, member: discord.Member, *, gender_text: str=""):
        rid = resolve_gender_role_id(gender_text)
        role = ctx.guild.get_role(rid)
        if not role: await ctx.send("❌ ไม่พบ role เพศที่แมปไว้"); return
        ok, msg = bot_can_edit_member_and_role(ctx, member, role)
        if not ok: await ctx.send(msg); return
        if not ctx.guild.me.guild_permissions.manage_roles:
            await ctx.send("❌ บอทไม่มีสิทธิ์ Manage Roles"); return
        to_remove = [r for r in member.roles if r.id in GENDER_ROLE_IDS_ALL and r.id != role.id]
        try:
            if to_remove: await member.remove_roles(*to_remove, reason="Admin: set gender")
            if role not in member.roles: await member.add_roles(role, reason="Admin: set gender")
        except: await ctx.send("❌ ปรับยศเพศไม่สำเร็จ"); return
        await ctx.send(f"✅ ตั้งเพศของ {member.mention} เป็น **{role.name}**")
        msg = await find_latest_approval_message(ctx.guild, member)
        if msg:
            e = msg.embeds[0]
            set_or_add_field(e, ("gender","เพศ"), "Gender / เพศ", role.name)
            try: await msg.edit(embed=e)
            except: pass

    @bot.command(name="setage", aliases=["age","อายุ","ปรับอายุ"])
    @commands.has_permissions(manage_roles=True)
    async def setage(ctx, member: discord.Member, *, age_text: str):
        if age_text.strip().lower() in {"", *CLEAR_ALIASES}: age_text = "ไม่ระบุ"
        rid = resolve_age_role_id(age_text)
        if not rid: await ctx.send("❌ อายุไม่ถูกต้อง (เลข 0–200 หรือ 'ไม่ระบุ')"); return
        role = ctx.guild.get_role(rid)
        if not role: await ctx.send("❌ ไม่พบ role อายุที่แมปไว้"); return
        ok, msg = bot_can_edit_member_and_role(ctx, member, role)
        if not ok: await ctx.send(msg); return
        if not ctx.guild.me.guild_permissions.manage_roles:
            await ctx.send("❌ บอทไม่มีสิทธิ์ Manage Roles"); return
        to_remove = [r for r in member.roles if r.id in AGE_ROLE_IDS_ALL and r.id != role.id]
        try:
            if to_remove: await member.remove_roles(*to_remove, reason="Admin: set age")
            if role not in member.roles: await member.add_roles(role, reason="Admin: set age")
        except: await ctx.send("❌ ปรับยศอายุไม่สำเร็จ"); return
        await ctx.send(f"✅ ตั้งอายุของ {member.mention} เป็น **{role.name}**")
        msg = await find_latest_approval_message(ctx.guild, member)
        if msg:
            e = msg.embeds[0]
            disp_age = "ไม่ระบุ" if role.id == ROLE_AGE_UNDISCLOSED else (re.search(r"\d{1,3}", age_text).group(0) if re.search(r"\d{1,3}", age_text) else age_text.strip())
            set_or_add_field(e, ("age","อายุ"), "Age / อายุ", disp_age)
            try: await msg.edit(embed=e)
            except: pass

    @bot.command(name="setbirthday", aliases=["birthday","วันเกิด","ปรับวันเกิด"])
    @commands.has_permissions(manage_roles=True)
    async def setbirthday(ctx, member: discord.Member, *, birthday_text: str=""):
        from saltybot.constants import AGE_ROLE_IDS_ALL
        want_clear = birthday_text.strip().lower() in {"", *CLEAR_ALIASES}
        msg = await find_latest_approval_message(ctx.guild, member)
        if want_clear:
            if msg:
                e = msg.embeds[0]; set_or_add_field(e, ("birthday","วันเกิด"), "Birthday / วันเกิด", "ไม่ระบุ")
                try: await msg.edit(embed=e)
                except: pass
            await ctx.send(f"✅ ลบวันเกิดของ {member.mention} แล้ว"); return

        bdt = parse_birthday(birthday_text)
        if not bdt: await ctx.send("❌ รูปแบบวันเกิดไม่ถูกต้อง (dd/mm/yyyy)"); return

        if msg:
            e = msg.embeds[0]; set_or_add_field(e, ("birthday","วันเกิด"), "Birthday / วันเกิด", birthday_text)
            try: await msg.edit(embed=e)
            except: pass

        years = age_from_birthday(bdt)
        rid = resolve_age_role_id(str(years)); role = ctx.guild.get_role(rid) if rid else None
        if not role: await ctx.send(f"⚠️ อายุ {years} ปี ไม่มี role ที่แมปไว้"); return
        ok, ms = bot_can_edit_member_and_role(ctx, member, role)
        if not ok: await ctx.send(ms); return
        try:
            to_remove = [r for r in member.roles if r.id in AGE_ROLE_IDS_ALL and r.id != role.id]
            if to_remove: await member.remove_roles(*to_remove, reason="Admin: set birthday")
            if role not in member.roles: await member.add_roles(role, reason="Admin: set birthday (age calculated)")
        except: await ctx.send("❌ ปรับยศอายุไม่สำเร็จ"); return
        await ctx.send(f"✅ ตั้งวันเกิด **{birthday_text}** → อายุ **{years}** ปี และตั้งยศ **{role.name}** ให้ {member.mention}")

    @bot.command(name="reverify", aliases=["บังคับยืนยันใหม่","forceverify"])
    @commands.has_permissions(manage_roles=True)
    async def reverify(ctx, member: discord.Member):
        ok, msg_txt = bot_can_edit_member_and_role(ctx, member)
        if not ok: await ctx.send(msg_txt); return

        to_remove = [r for r in member.roles if r.id in {ROLE_ID_TO_GIVE, *GENDER_ROLE_IDS_ALL, *AGE_ROLE_IDS_ALL}]
        if to_remove:
            try: await member.remove_roles(*to_remove, reason="Force re-verification")
            except: await ctx.send("❌ ไม่มีสิทธิ์ถอดยศของสมาชิกคนนี้"); return

        try:
            base = base_display_name(member)
            await member.edit(nick=base, reason="Force re-verification (reset nickname)")
        except: pass

        msg = await find_latest_approval_message(ctx.guild, member)
        if msg:
            try: await msg.delete()
            except: pass

        pending_clear(member.id)
        try:
            await member.send(f"ℹ️ คุณถูกขอให้ยืนยันตัวตนใหม่ในเซิร์ฟเวอร์ **{ctx.guild.name}**\nกรุณาไปที่ห้อง <#{VERIFY_CHANNEL_ID}> แล้วกดปุ่ม **Verify Identity**")
        except: await ctx.send("⚠️ ส่ง DM แจ้งผู้ใช้ไม่ได้")

        await ctx.send(f"✅ สั่งให้ {member.mention} ยืนยันตัวตนใหม่แล้ว (roles cleared + embed removed)")
        await notify_admin(ctx.guild, f"{member.mention} ถูกสั่งให้ยืนยันตัวตนใหม่โดย {ctx.author.mention}")
