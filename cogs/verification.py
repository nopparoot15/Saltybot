\
from discord.ext import commands
import discord
from datetime import datetime, timedelta, timezone
import re

from core.config import (
    VERIFY_CHANNEL_ID, APPROVAL_CHANNEL_ID, ROLE_ID_TO_GIVE, TH_TZ,
    GENDER_ROLE_IDS_ALL, AGE_ROLE_IDS_ALL
)
from core.utils import (
    INVALID_CHARS, contains_emoji, canon_name, discord_names_set,
    resolve_gender_role_id, resolve_age_role_id, is_age_undisclosed,
    notify_admin, parse_birthday, age_from_birthday, build_account_check_field,
)

pending_verifications: set[int] = set()

class VerificationForm(discord.ui.Modal, title="Verify Identity / ยืนยันตัวตน"):
    def __init__(self):
        super().__init__(timeout=None)
        self.name = discord.ui.TextInput(
            label="Nickname / ชื่อเล่น (ปล่อยว่าง = ไม่ระบุ)",
            placeholder="ตัวอักษร 2–10 (เว้นว่างได้)",
            style=discord.TextStyle.short, min_length=0, max_length=10, required=False
        )
        self.age = discord.ui.TextInput(
            label="Age / อายุ (ปล่อยว่าง = ไม่ระบุ)",
            placeholder='เช่น 21', style=discord.TextStyle.short, min_length=0, max_length=16, required=False
        )
        self.gender = discord.ui.TextInput(
            label="Gender / เพศ (ปล่อยว่าง = ไม่ระบุ)",
            placeholder='เช่น ชาย / หญิง / LGBT', style=discord.TextStyle.short, min_length=0, required=False
        )
        self.birthday = discord.ui.TextInput(
            label="Birthday / วันเกิด (ไม่บังคับ, dd/mm/yyyy)",
            placeholder="เช่น 12/09/2003", style=discord.TextStyle.short, min_length=0, max_length=10, required=False
        )
        # must add children
        for child in (self.name, self.age, self.gender, self.birthday):
            self.add_item(child)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            if not interaction.response.is_done():
                await interaction.response.defer(ephemeral=True)

            member = interaction.guild.get_member(interaction.user.id) or await interaction.guild.fetch_member(interaction.user.id)
            if member and any(r.id == ROLE_ID_TO_GIVE for r in member.roles):
                await interaction.followup.send(
                    "✅ คุณได้รับการยืนยันแล้ว ไม่ต้องส่งซ้ำ\nหากคิดว่าเป็นความผิดพลาด กรุณาติดต่อผู้ดูแล", ephemeral=True
                ); return

            if interaction.user.id in pending_verifications:
                await interaction.followup.send("❗ ส่งคำขอไปแล้ว กรุณารอแอดมินตรวจ", ephemeral=True); return

            # validate age
            age_raw = (self.age.value or "").strip()
            if not (age_raw == "" or re.fullmatch(r"\d{1,3}", age_raw) or is_age_undisclosed(age_raw)):
                await interaction.followup.send("❌ รูปแบบอายุไม่ถูกต้อง (ตัวเลข 1–3 หลัก หรือเว้นว่างเพื่อไม่ระบุ)", ephemeral=True); return

            # validate nickname
            nick = (self.name.value or "").strip()
            if nick:
                if len(nick) < 2 or len(nick) > 10 or any(ch.isdigit() for ch in nick) or any(c in INVALID_CHARS for c in nick) or contains_emoji(nick):
                    await interaction.followup.send("❌ Nickname ต้องเป็นตัวอักษร 2–10 ตัว และห้ามตัวเลข/สัญลักษณ์/อีโมจิ", ephemeral=True); return
                if canon_name(nick) in discord_names_set(interaction.user):
                    await interaction.followup.send("❌ ชื่อเล่นต้องต่างจากชื่อในดิสคอร์ดของคุณจริง ๆ", ephemeral=True); return

            gender_raw = (self.gender.value or "")
            if gender_raw.strip():
                if any(ch.isdigit() for ch in gender_raw) or any(c in INVALID_CHARS for c in gender_raw) or contains_emoji(gender_raw):
                    await interaction.followup.send("❌ Gender invalid. Text only.", ephemeral=True); return

            birthday_raw = (self.birthday.value or "").strip()
            bday_dt = None
            if birthday_raw:
                bday_dt = parse_birthday(birthday_raw)
                if not bday_dt:
                    await interaction.followup.send("❌ วันเกิดไม่ถูกต้อง (dd/mm/yyyy เช่น 05/11/2004)", ephemeral=True); return

            pending_verifications.add(interaction.user.id)

            display_nick = nick if nick else "ไม่ระบุ"
            display_age = (age_raw if age_raw else "ไม่ระบุ")
            display_gender = (gender_raw.strip() if gender_raw.strip() else "ไม่ระบุ")
            display_birthday = birthday_raw if birthday_raw else "ไม่ระบุ"

            embed = discord.Embed(title="📋 Verification Request / คำขอยืนยันตัวตน", color=discord.Color.orange())
            thumb_url = interaction.user.display_avatar.with_static_format("png").with_size(128).url
            embed.set_thumbnail(url=thumb_url)
            embed.add_field(name="Nickname / ชื่อเล่น", value=display_nick, inline=False)
            embed.add_field(name="Age / อายุ", value=display_age, inline=False)
            embed.add_field(name="Gender / เพศ", value=display_gender, inline=False)
            embed.add_field(name="Birthday / วันเกิด", value=display_birthday, inline=False)

            name, value, risk, age_days = build_account_check_field(interaction.user)
            embed.add_field(name=name, value=value, inline=False)
            if risk == "HIGH":
                await notify_admin(interaction.guild, f"{interaction.user.mention} ความเสี่ยงสูงจากอายุบัญชี ({age_days} วัน)")

            now = datetime.now(TH_TZ)
            embed.add_field(name="📅 Sent at", value=now.strftime("%d/%m/%Y %H:%M"), inline=False)
            embed.set_footer(text=f"User ID: {interaction.user.id}")

            channel = interaction.guild.get_channel(APPROVAL_CHANNEL_ID)
            if not channel:
                await notify_admin(interaction.guild, "ไม่พบห้อง APPROVAL_CHANNEL_ID")
                await interaction.followup.send("⚠️ ระบบขัดข้อง: ไม่พบห้องอนุมัติ แจ้งแอดมินเรียบร้อย", ephemeral=True); return

            view = ApproveRejectView(
                user=interaction.user,
                gender_text=gender_raw,
                age_text=age_raw if age_raw else "ไม่ระบุ",
                form_name=nick,
                birthday_text=birthday_raw
            )
            await channel.send(
                content=interaction.user.mention,
                embed=embed,
                view=view,
                allowed_mentions=discord.AllowedMentions(everyone=False, roles=False, users=True),
            )

            await interaction.followup.send("✅ ส่งคำขอแล้ว กรุณารอการอนุมัติจากแอดมิน", ephemeral=True)

        except Exception as e:
            pending_verifications.discard(interaction.user.id)
            await notify_admin(interaction.guild, f"เกิดข้อผิดพลาดตอนส่งแบบฟอร์มของ {interaction.user.mention}: {e!r}")
            try:
                await interaction.followup.send("❌ ระบบขัดข้อง กรุณาลองใหม่ภายหลัง", ephemeral=True)
            except Exception:
                pass

class VerificationView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Verify Identity / ยืนยันตัวตน", style=discord.ButtonStyle.success, emoji="✅", custom_id="verify_button")
    async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        member = interaction.guild.get_member(interaction.user.id) or await interaction.guild.fetch_member(interaction.user.id)
        if member and any(r.id == ROLE_ID_TO_GIVE for r in member.roles):
            await interaction.response.send_message("✅ คุณได้รับการยืนยันแล้ว ไม่ต้องกดอีกครั้ง", ephemeral=True); return
        await interaction.response.send_modal(VerificationForm())

class ApproveRejectView(discord.ui.View):
    def __init__(self, user: discord.User, gender_text: str, age_text: str, form_name: str, birthday_text: str = ""):
        super().__init__(timeout=None)
        self.user = user
        self.gender_text = (gender_text or "").strip()
        self.age_text = (age_text or "").strip()
        self.form_name = (form_name or "").strip()
        self.birthday_text = (birthday_text or "").strip()

    @discord.ui.button(label="✅ Approve / อนุมัติ", style=discord.ButtonStyle.success, custom_id="approve_button")
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            if not interaction.response.is_done():
                await interaction.response.defer()

            member = interaction.guild.get_member(self.user.id) or await interaction.guild.fetch_member(self.user.id)
            general_role = interaction.guild.get_role(ROLE_ID_TO_GIVE)
            gender_role = interaction.guild.get_role(resolve_gender_role_id(self.gender_text))

            age_role = None
            if self.birthday_text:
                bday_dt = parse_birthday(self.birthday_text)
                if bday_dt:
                    years = age_from_birthday(bday_dt)
                    age_role_id = resolve_age_role_id(str(years))
                    age_role = interaction.guild.get_role(age_role_id) if age_role_id else None
            if age_role is None:
                age_role_id = resolve_age_role_id(self.age_text)
                age_role = interaction.guild.get_role(age_role_id) if age_role_id else None

            if not (member and general_role and gender_role):
                await interaction.followup.send("❌ Member or role not found.", ephemeral=True)
                await notify_admin(interaction.guild, "อนุมัติไม่สำเร็จ: ไม่พบ member/role"); return

            # enforce one gender role
            try:
                to_remove_gender = [r for r in member.roles if r.id in GENDER_ROLE_IDS_ALL and (gender_role is None or r.id != gender_role.id)]
                if to_remove_gender:
                    await member.remove_roles(*to_remove_gender, reason="Verification: enforce single gender role")
            except discord.Forbidden:
                await interaction.followup.send("❌ ไม่มีสิทธิ์ถอดยศเพศเดิม", ephemeral=True); return

            # enforce one age role (only if new exists)
            if age_role:
                try:
                    to_remove_age = [r for r in member.roles if r.id in AGE_ROLE_IDS_ALL and r.id != age_role.id]
                    if to_remove_age:
                        await member.remove_roles(*to_remove_age, reason="Verification: enforce single age role")
                except discord.Forbidden:
                    await interaction.followup.send("❌ ไม่มีสิทธิ์ถอดยศอายุเดิม", ephemeral=True); return

            roles_to_add = []
            if general_role and general_role not in member.roles: roles_to_add.append(general_role)
            if gender_role and gender_role not in member.roles: roles_to_add.append(gender_role)
            if age_role and age_role not in member.roles: roles_to_add.append(age_role)

            if roles_to_add:
                try:
                    await member.add_roles(*roles_to_add, reason="Verified")
                except discord.Forbidden:
                    await interaction.followup.send("❌ Missing permissions to add roles.", ephemeral=True)
                    await notify_admin(interaction.guild, f"บอทให้ยศไม่สำเร็จที่ {member.mention}"); return

            pending_verifications.discard(self.user.id)
        except Exception as e:
            await notify_admin(interaction.guild, f"Approve error: {e!r}")
        finally:
            for child in self.children:
                if getattr(child, "custom_id", None) == "approve_button":
                    child.label = "✅ Approved / อนุมัติแล้ว"
                    child.style = discord.ButtonStyle.success
                elif getattr(child, "custom_id", None) == "reject_button":
                    child.style = discord.ButtonStyle.secondary
                child.disabled = True

            try:
                msg = interaction.message
                if msg and msg.embeds:
                    e = msg.embeds[0]
                    actor = getattr(interaction.user, "display_name", None) or interaction.user.name
                    stamp = datetime.now(TH_TZ).strftime("%d/%m/%Y %H:%M")
                    orig = e.footer.text or ""
                    footer = f"{orig} • Approved by {actor} • {stamp}" if orig else f"Approved by {actor} • {stamp}"
                    e.set_footer(text=footer)
                    await msg.edit(embed=e, view=self)
                else:
                    await interaction.message.edit(view=self)
            except discord.NotFound:
                pass

    @discord.ui.button(label="❌ Reject / ปฏิเสธ", style=discord.ButtonStyle.danger, custom_id="reject_button")
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            if not interaction.response.is_done():
                await interaction.response.defer()
            pending_verifications.discard(self.user.id)
            try:
                await self.user.send("❌ การยืนยันตัวตนของคุณไม่ผ่าน กรุณาติดต่อแอดมิน")
            except Exception:
                await interaction.followup.send("⚠️ ไม่สามารถส่ง DM แจ้งผู้ใช้ได้", ephemeral=True)
        except Exception as e:
            await notify_admin(interaction.guild, f"Reject error: {e!r}")
        finally:
            for child in self.children:
                if getattr(child, "custom_id", None) == "reject_button":
                    child.label = "❌ Rejected / ปฏิเสธแล้ว"
                    child.style = discord.ButtonStyle.danger
                elif getattr(child, "custom_id", None) == "approve_button":
                    child.style = discord.ButtonStyle.secondary
                child.disabled = True
            try:
                msg = interaction.message
                if msg and msg.embeds:
                    e = msg.embeds[0]
                    actor = getattr(interaction.user, "display_name", None) or interaction.user.name
                    stamp = datetime.now(TH_TZ).strftime("%d/%m/%Y %H:%M")
                    orig = e.footer.text or ""
                    footer = f"{orig} • Rejected by {actor} • {stamp}" if orig else f"Rejected by {actor} • {stamp}"
                    e.set_footer(text=footer)
                    await msg.edit(embed=e, view=self)
                else:
                    await interaction.message.edit(view=self)
            except discord.NotFound:
                pass

# ---- Cog ----
class VerificationCog(commands.Cog, name="Verification"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="verify_embed")
    @commands.has_permissions(administrator=True)
    async def verify_embed(self, ctx: commands.Context):
        channel = ctx.guild.get_channel(VERIFY_CHANNEL_ID)
        if not channel:
            await ctx.send("❌ VERIFY_CHANNEL_ID not found."); return
        embed = discord.Embed(
            title="📌 Welcome / ยินดีต้อนรับ",
            description="Click the button below to verify your identity.\nกดปุ่มด้านล่างเพื่อยืนยันตัวตนของคุณ",
            color=discord.Color.blue()
        )
        embed.set_footer(text="Verification System / ระบบยืนยันตัวตนโดย Bot")
        await channel.send(embed=embed, view=VerificationView())
        await ctx.send(f"✅ Verification embed sent to {channel.mention}")

async def setup(bot: commands.Bot):
    # persistent view
    bot.add_view(VerificationView())
    await bot.add_cog(VerificationCog(bot), override=True)
