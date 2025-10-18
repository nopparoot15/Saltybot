import re, io, discord
from datetime import datetime
from zoneinfo import ZoneInfo
from saltybot.config import (
    APPROVAL_CHANNEL_ID, ACCOUNT_RISK_ENABLED, REFRESH_TZ, VERIFY_CHANNEL_ID,
    APPEND_FORM_NAME_TO_NICK
)
from saltybot.constants import ROLE_ID_TO_GIVE, GENDER_ROLE_IDS_ALL, AGE_ROLE_IDS_ALL
from saltybot.utils.text import INVALID_CHARS, contains_emoji, canon_full
from saltybot.utils.discord_helpers import base_display_name, discord_names_set
from saltybot.utils.admin_notify import notify_admin
from .state import pending_is_blocked, pending_set, pending_clear, mark_msg_decided
from .gender import resolve_gender_role_id
from .age import resolve_age_role_id, is_age_undisclosed
from .birthday import parse_birthday, age_from_birthday

def _build_parenthesized_nick(member: discord.Member, form_name: str) -> str:
    base = base_display_name(member)
    real = (form_name or "").strip()
    cand = f"{base} ({real})".strip()
    if len(cand) <= 32: return cand
    max_base = 32 - (len(real) + 3)
    if max_base > 1:
        cand = f"{base[:max_base].rstrip()} ({real})"
        if len(cand) <= 32: return cand
    return real[:32]

def account_risk_age_only(user: discord.User):
    try:
        created_at = user.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=ZoneInfo("UTC"))
        now = datetime.now(ZoneInfo("UTC"))
        age_days = (now - created_at).days
    except Exception:
        return None, "UNKNOWN", ["cannot compute account age"]
    from saltybot.config import MIN_ACCOUNT_AGE_DAYS_HIGH, MIN_ACCOUNT_AGE_DAYS_MED
    reasons = []
    if age_days < MIN_ACCOUNT_AGE_DAYS_HIGH:
        reasons.append(f"age<{MIN_ACCOUNT_AGE_DAYS_HIGH}d"); return age_days, "HIGH", reasons
    if age_days < MIN_ACCOUNT_AGE_DAYS_MED:
        reasons.append(f"age<{MIN_ACCOUNT_AGE_DAYS_MED}d"); return age_days, "MED", reasons
    return age_days, "LOW", reasons

def build_account_check_field(user: discord.User):
    age_days, risk, reasons = account_risk_age_only(user)
    icon = "⚠️" if risk == "HIGH" else ("🟧" if risk == "MED" else ("🟩" if risk == "LOW" else "❔"))
    age_txt = "—" if age_days is None else f"{age_days} days"
    reason_txt = f" • Reasons: {', '.join(reasons)}" if reasons else ""
    name = "🛡️ Account Check"
    value = f"Account age: {age_txt} • Risk: {risk} {icon}{reason_txt}"
    return name, value, risk, age_days

class VerificationForm(discord.ui.Modal, title="Verify Identity / ยืนยันตัวตน"):
    name = discord.ui.TextInput(label="Nickname / ชื่อเล่น (ปล่อยว่าง = ไม่ระบุ)", placeholder="ตัวอักษร 2–10 (เว้นว่างได้)", style=discord.TextStyle.short, min_length=0, max_length=10, required=False)
    age = discord.ui.TextInput(label="Age / อายุ (ปล่อยว่าง = ไม่ระบุ)", placeholder="เช่น 21", style=discord.TextStyle.short, min_length=0, max_length=16, required=False)
    gender = discord.ui.TextInput(label="Gender / เพศ (ปล่อยว่าง = ไม่ระบุ)", placeholder="เช่น ชาย / หญิง / LGBT", style=discord.TextStyle.short, min_length=0, required=False)
    birthday = discord.ui.TextInput(label="Birthday / วันเกิด (ไม่บังคับ, dd/mm/yyyy)", placeholder="เช่น 12/09/2003", style=discord.TextStyle.short, min_length=0, max_length=10, required=False)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            if not interaction.response.is_done():
                await interaction.response.defer(ephemeral=True)

            member = interaction.guild.get_member(interaction.user.id) or await interaction.guild.fetch_member(interaction.user.id)

            if member and any(r.id == ROLE_ID_TO_GIVE for r in member.roles):
                await interaction.followup.send("✅ คุณได้รับการยืนยันตัวตนแล้ว หากคิดว่าผิดพลาด ติดต่อผู้ดูแล", ephemeral=True); return

            if pending_is_blocked(interaction.user.id):
                await interaction.followup.send("❗ คุณได้ส่งคำขอไปแล้ว กรุณารอแอดมินตรวจสอบ", ephemeral=True); return

            # validate age
            age_raw = (self.age.value or "").strip()
            if not (age_raw == "" or re.fullmatch(r"\d{1,3}", age_raw) or is_age_undisclosed(age_raw)):
                await interaction.followup.send("❌ รูปแบบอายุไม่ถูกต้อง (ตัวเลข 1–3 หลัก หรือเว้นว่าง=ไม่ระบุ)", ephemeral=True); return

            # validate nickname
            nick = (self.name.value or "").strip()
            if nick:
                if len(nick) < 2 or len(nick) > 10 or any(ch.isdigit() for ch in nick) or contains_emoji(nick) or any(c in INVALID_CHARS for c in nick):
                    await interaction.followup.send("❌ Nickname invalid (2–10 ตัวอักษร, ห้ามตัวเลข/สัญลักษณ์/อีโมจิ)", ephemeral=True); return
                if canon_full(nick) in discord_names_set(interaction.user, canon_full):
                    await interaction.followup.send("❌ ชื่อเล่นต้องต่างจากชื่อดิสคอร์ดจริง ๆ", ephemeral=True); return

            gender_raw = (self.gender.value or "")
            if gender_raw.strip():
                if not is_age_undisclosed(gender_raw):  # ใช้เกณฑ์ “ข้อความล้วน”
                    if any(ch.isdigit() for ch in gender_raw) or contains_emoji(gender_raw) or any(c in INVALID_CHARS for c in gender_raw):
                        await interaction.followup.send("❌ Gender invalid. Text only.", ephemeral=True); return

            birthday_raw = (self.birthday.value or "").strip()
            bday_dt = parse_birthday(birthday_raw) if birthday_raw else None
            if birthday_raw and not bday_dt:
                await interaction.followup.send("❌ วันเกิดไม่ถูกต้อง (dd/mm/yyyy)", ephemeral=True); return

            pending_set(interaction.user.id)

            embed = discord.Embed(title="📋 Verification Request / คำขอยืนยันตัวตน", color=discord.Color.orange())
            embed.set_thumbnail(url=interaction.user.display_avatar.with_static_format("png").with_size(128).url)
            embed.add_field(name="Nickname / ชื่อเล่น", value=(nick or "ไม่ระบุ"), inline=False)
            embed.add_field(name="Age / อายุ", value=(age_raw or "ไม่ระบุ"), inline=False)
            embed.add_field(name="Gender / เพศ", value=(gender_raw.strip() or "ไม่ระบุ"), inline=False)
            embed.add_field(name="Birthday / วันเกิด", value=(birthday_raw or "ไม่ระบุ"), inline=False)

            if ACCOUNT_RISK_ENABLED:
                name, value, risk, age_days = build_account_check_field(interaction.user)
                embed.add_field(name=name, value=value, inline=False)
                if risk == "HIGH":
                    await notify_admin(interaction.guild, f"{interaction.user.mention} ความเสี่ยงสูงจากอายุบัญชี ({age_days} วัน)")

            now = datetime.now(REFRESH_TZ)
            embed.add_field(name="📅 Sent at", value=now.strftime("%d/%m/%Y %H:%M"), inline=False)
            embed.set_footer(text=f"User ID: {interaction.user.id}")

            channel = interaction.guild.get_channel(APPROVAL_CHANNEL_ID)
            if not channel:
                await notify_admin(interaction.guild, "ไม่พบห้อง APPROVAL_CHANNEL_ID")
                await interaction.followup.send("⚠️ ระบบขัดข้อง: ไม่พบห้องอนุมัติ", ephemeral=True); pending_set(interaction.user.id); return

            view = ApproveRejectView(user=interaction.user, gender_text=gender_raw, age_text=(age_raw or "ไม่ระบุ"), form_name=nick, birthday_text=birthday_raw)
            await channel.send(content=interaction.user.mention, embed=embed, view=view, allowed_mentions=discord.AllowedMentions(everyone=False, roles=False, users=True))

            await interaction.followup.send("✅ ส่งคำขอยืนยันตัวตนแล้ว กรุณารอแอดมิน", ephemeral=True)
        except Exception as e:
            pending_clear(interaction.user.id)
            await notify_admin(interaction.guild, f"เกิดข้อผิดพลาดตอนส่งแบบฟอร์มของ {interaction.user.mention}: {e!r}")
            try: await interaction.followup.send("❌ ระบบขัดข้อง กรุณาลองใหม่ภายหลัง", ephemeral=True)
            except: pass

class PersistentVerificationView(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)

    @discord.ui.button(label="Verify Identity / ยืนยันตัวตน", style=discord.ButtonStyle.success, emoji="✅", custom_id="verify_button")
    async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        member = interaction.guild.get_member(interaction.user.id) or await interaction.guild.fetch_member(interaction.user.id)
        if member and any(r.id == ROLE_ID_TO_GIVE for r in member.roles):
            await interaction.response.send_message("✅ คุณได้รับการยืนยันแล้ว", ephemeral=True); return
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
        msg = interaction.message
        if not msg or not mark_msg_decided(msg.id):
            await interaction.response.send_message("⏳ คำขอนี้ถูกตัดสินไปแล้ว", ephemeral=True); return
        try:
            if not interaction.response.is_done(): await interaction.response.defer()
            member = interaction.guild.get_member(self.user.id) or await interaction.guild.fetch_member(self.user.id)
            general_role = interaction.guild.get_role(ROLE_ID_TO_GIVE)
            from .gender import resolve_gender_role_id
            from .age import resolve_age_role_id
            gender_role = interaction.guild.get_role(resolve_gender_role_id(self.gender_text))

            age_role = None
            if self.birthday_text:
                bdt = parse_birthday(self.birthday_text)
                if bdt:
                    years = age_from_birthday(bdt)
                    age_role = interaction.guild.get_role(resolve_age_role_id(str(years)))
            if age_role is None:
                rid = resolve_age_role_id(self.age_text)
                age_role = interaction.guild.get_role(rid) if rid else None

            if not (member and general_role and gender_role):
                await interaction.followup.send("❌ Member or role not found.", ephemeral=True); return

            # enforce single gender
            to_remove_gender = [r for r in member.roles if r.id in GENDER_ROLE_IDS_ALL and (gender_role is None or r.id != gender_role.id)]
            if to_remove_gender: await member.remove_roles(*to_remove_gender, reason="Verification: enforce single gender role")

            # enforce single age
            if age_role:
                to_remove_age = [r for r in member.roles if r.id in AGE_ROLE_IDS_ALL and r.id != age_role.id]
                if to_remove_age: await member.remove_roles(*to_remove_age, reason="Verification: enforce single age role")

            roles_to_add = []
            if general_role and general_role not in member.roles: roles_to_add.append(general_role)
            if gender_role and gender_role not in member.roles: roles_to_add.append(gender_role)
            if age_role and age_role not in member.roles: roles_to_add.append(age_role)
            if roles_to_add: await member.add_roles(*roles_to_add, reason="Verified")

            # nickname (manual mode default False)
            if APPEND_FORM_NAME_TO_NICK and self.form_name:
                try:
                    new_nick = _build_parenthesized_nick(member, self.form_name)
                    await member.edit(nick=new_nick, reason=f"Verified: form nickname → {self.form_name}")
                except Exception: pass

        except Exception as e:
            await notify_admin(interaction.guild, f"Approve error: {e!r}")
        finally:
            pending_clear(self.user.id)
            for child in self.children:
                if getattr(child, "custom_id", None) == "approve_button":
                    child.label = "✅ Approved / อนุมัติแล้ว"; child.style = discord.ButtonStyle.success
                elif getattr(child, "custom_id", None) == "reject_button":
                    child.style = discord.ButtonStyle.secondary
                child.disabled = True
            try:
                e = msg.embeds[0] if msg and msg.embeds else None
                actor = getattr(interaction.user, "display_name", None) or interaction.user.name
                stamp = datetime.now(REFRESH_TZ).strftime("%d/%m/%Y %H:%M")
                if e:
                    orig = e.footer.text or ""
                    footer = f"{orig} • Approved by {actor} • {stamp}" if orig else f"Approved by {actor} • {stamp}"
                    e.set_footer(text=footer)
                    await msg.edit(embed=e, view=self)
                else:
                    await interaction.message.edit(view=self)
            except: pass

    @discord.ui.button(label="❌ Reject / ปฏิเสธ", style=discord.ButtonStyle.danger, custom_id="reject_button")
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        msg = interaction.message
        if not msg or not mark_msg_decided(msg.id):
            await interaction.response.send_message("⏳ คำขอนี้ถูกตัดสินไปแล้ว", ephemeral=True); return
        try:
            if not interaction.response.is_done(): await interaction.response.defer()
            pending_clear(self.user.id)
            try:
                await self.user.send("❌ การยืนยันตัวตนของคุณไม่ผ่าน กรุณาติดต่อแอดมิน")
            except Exception:
                await interaction.followup.send("⚠️ ไม่สามารถส่ง DM แจ้งผู้ใช้ได้", ephemeral=True)
        except Exception as e:
            await notify_admin(interaction.guild, f"Reject error: {e!r}")
        finally:
            for child in self.children:
                if getattr(child, "custom_id", None) == "reject_button":
                    child.label = "❌ Rejected / ปฏิเสธแล้ว"; child.style = discord.ButtonStyle.danger
                elif getattr(child, "custom_id", None) == "approve_button":
                    child.style = discord.ButtonStyle.secondary
                child.disabled = True
            try:
                e = msg.embeds[0] if msg and msg.embeds else None
                actor = getattr(interaction.user, "display_name", None) or interaction.user.name
                stamp = datetime.now(REFRESH_TZ).strftime("%d/%m/%Y %H:%M")
                if e:
                    orig = e.footer.text or ""
                    footer = f"{orig} • Rejected by {actor} • {stamp}" if orig else f"Rejected by {actor} • {stamp}"
                    e.set_footer(text=footer)
                    await msg.edit(embed=e, view=self)
                else:
                    await interaction.message.edit(view=self)
            except: pass
