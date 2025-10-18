# saltybot/verification/views.py
from __future__ import annotations

import io
import re
import asyncio
from datetime import datetime, timezone, timedelta, date
from typing import Optional

import discord
from discord.ext import commands

# ---------- project imports ----------
# IDs/roles/channels config
from ..constants import (
    VERIFY_CHANNEL_ID,
    APPROVAL_CHANNEL_ID,
    LOG_CHANNEL_ID,
    ADMIN_NOTIFY_CHANNEL_ID,
    ROLE_ID_TO_GIVE,
    ROLE_MALE, ROLE_FEMALE, ROLE_LGBT, ROLE_GENDER_UNDISCLOSED,
    ROLE_0_12, ROLE_13_15, ROLE_16_18, ROLE_19_21, ROLE_22_24,
    ROLE_25_29, ROLE_30_34, ROLE_35_39, ROLE_40_44, ROLE_45_49,
    ROLE_50_54, ROLE_55_59, ROLE_60_64, ROLE_65_UP, ROLE_AGE_UNDISCLOSED,
)

# utils
from ..utils.text import INVALID_CHARS, contains_emoji, canon_full
from ..utils.discord_helpers import base_display_name, discord_names_set
from ..utils.admin_notify import notify_admin

# verification domain helpers
from .birthday import parse_birthday, age_from_birthday
from .age import resolve_age_role_id, is_age_undisclosed
from .gender import resolve_gender_role_id

# persistence (PostgreSQL via asyncpg)
from ..repo import (
    upsert_user, set_last_msg_id, get_user,
    record_decision, mark_approved, mark_rejected,
)

# embeds builder (ถ้าคุณมีแยกไฟล์ไว้), ถ้าไม่มีให้ใช้ build_embed_local ด้านล่างแทน
try:
    from .embeds import build_verification_embed  # (user avatar thumb + fields)
except Exception:
    build_verification_embed = None


# ========== CONFIG ==========
TZ_BKK = timezone(timedelta(hours=7))
ACCOUNT_RISK_ENABLED = True
MIN_ACCOUNT_AGE_DAYS_HIGH = 3
MIN_ACCOUNT_AGE_DAYS_MED = 7

HIDE_BIRTHDAY_ON_IDCARD = True
BIRTHDAY_HIDDEN_TEXT = "ไม่แสดง"

# ========== SMALL HELPERS ==========
def now_bkk() -> datetime:
    return datetime.now(TZ_BKK)

def years_between(a: datetime, b: datetime) -> int:
    y = b.year - a.year
    if (b.month, b.day) < (a.month, a.day):
        y -= 1
    return max(y, 0)

def parse_local_sent_at_ddmmyyyy_hhmm(s: str) -> Optional[datetime]:
    try:
        dt = datetime.strptime(s.strip(), "%d/%m/%Y %H:%M")
        return dt.replace(tzinfo=TZ_BKK)
    except Exception:
        return None

def _age_role_ids_all() -> list[int]:
    return [rid for rid in [
        ROLE_0_12, ROLE_13_15, ROLE_16_18, ROLE_19_21, ROLE_22_24,
        ROLE_25_29, ROLE_30_34, ROLE_35_39, ROLE_40_44, ROLE_45_49,
        ROLE_50_54, ROLE_55_59, ROLE_60_64, ROLE_65_UP, ROLE_AGE_UNDISCLOSED
    ] if rid and rid > 0]

def _gender_role_ids_all() -> list[int]:
    return [ROLE_MALE, ROLE_FEMALE, ROLE_LGBT, ROLE_GENDER_UNDISCLOSED]

def _assess_account_risk_age_only(user: discord.User) -> tuple[Optional[int], str]:
    """
    LOW/MED/HIGH ตามอายุบัญชี Discord (วัน)
    """
    try:
        created_at = user.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        age_days = (datetime.now(timezone.utc) - created_at).days
    except Exception:
        return None, "UNKNOWN"
    if age_days < MIN_ACCOUNT_AGE_DAYS_HIGH:
        return age_days, "HIGH"
    if age_days < MIN_ACCOUNT_AGE_DAYS_MED:
        return age_days, "MED"
    return age_days, "LOW"

async def apply_roles_safely(guild: discord.Guild, member: discord.Member, *, add: list[discord.Role], remove: list[discord.Role], reason: str) -> tuple[bool, str]:
    """
    บังคับลำดับยศก่อน add/remove และ no-op guard
    """
    me = guild.me
    if not me:
        return False, "no-bot"
    if me.top_role <= member.top_role or member.id == guild.owner_id:
        return False, "hierarchy-member"

    for r in list(add) + list(remove):
        if r and me.top_role <= r:
            return False, f"hierarchy-role:{r.id}"

    # no-op guard
    add = [r for r in add if r and r not in member.roles]
    remove = [r for r in remove if r in member.roles]

    # throttle เบา ๆ กัน rate-limit
    if remove:
        await member.remove_roles(*remove, reason=reason)
        await asyncio.sleep(0.2)
    if add:
        await member.add_roles(*add, reason=reason)
        await asyncio.sleep(0.2)
    return True, "ok"


# ========== EMBED FALLBACK ==========
def build_embed_local(user: discord.User, *, nickname: str, age_text: str, gender_text: str, birthday_text: str) -> discord.Embed:
    e = discord.Embed(title="📋 Verification Request / คำขอยืนยันตัวตน", color=discord.Color.orange())
    thumb_url = user.display_avatar.with_static_format("png").with_size(128).url
    e.set_thumbnail(url=thumb_url)
    e.add_field(name="Nickname / ชื่อเล่น", value=nickname or "ไม่ระบุ", inline=False)
    e.add_field(name="Age / อายุ", value=age_text or "ไม่ระบุ", inline=False)
    e.add_field(name="Gender / เพศ", value=gender_text or "ไม่ระบุ", inline=False)
    e.add_field(name="Birthday / วันเกิด", value=birthday_text or "ไม่ระบุ", inline=False)

    if ACCOUNT_RISK_ENABLED:
        age_days, risk = _assess_account_risk_age_only(user)
        icon = "⚠️" if risk == "HIGH" else ("🟧" if risk == "MED" else ("🟩" if risk == "LOW" else "❔"))
        age_txt = "—" if age_days is None else f"{age_days} days"
        e.add_field(name="🛡️ Account Check", value=f"Account age: {age_txt} • Risk: {risk} {icon}", inline=False)

    sent = now_bkk()
    e.add_field(name="📅 Sent at", value=sent.strftime("%d/%m/%Y %H:%M"), inline=False)
    e.set_footer(text=f"User ID: {user.id}")
    return e


# ========== MODAL ==========
class VerificationForm(discord.ui.Modal, title="Verify Identity / ยืนยันตัวตน"):
    name = discord.ui.TextInput(
        label="Nickname / ชื่อเล่น (ปล่อยว่าง = ไม่ระบุ)",
        placeholder="ตัวอักษร 2–10 (เว้นว่างได้)",
        style=discord.TextStyle.short,
        min_length=0, max_length=10, required=False,
    )
    age = discord.ui.TextInput(
        label="Age / อายุ (ปล่อยว่าง = ไม่ระบุ)",
        placeholder="เช่น 21",
        style=discord.TextStyle.short,
        min_length=0, max_length=16, required=False,
    )
    gender = discord.ui.TextInput(
        label="Gender / เพศ (ปล่อยว่าง = ไม่ระบุ)",
        placeholder="เช่น ชาย / หญิง / LGBT",
        style=discord.TextStyle.short,
        min_length=0, required=False,
    )
    birthday = discord.ui.TextInput(
        label="Birthday / วันเกิด (ไม่บังคับ, dd/mm/yyyy)",
        placeholder="เช่น 12/09/2003",
        style=discord.TextStyle.short,
        min_length=0, max_length=10, required=False,
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            if not interaction.response.is_done():
                await interaction.response.defer(ephemeral=True)

            # ถ้ามียศยืนยันแล้ว ห้ามส่งซ้ำ
            member = interaction.guild.get_member(interaction.user.id) or await interaction.guild.fetch_member(interaction.user.id)
            if member and any(r.id == ROLE_ID_TO_GIVE for r in member.roles):
                await interaction.followup.send(
                    "✅ คุณได้รับการยืนยันตัวตนแล้ว หากคิดว่าเป็นความผิดพลาด กรุณาติดต่อผู้ดูแล",
                    ephemeral=True,
                )
                return

            # Validate age
            age_raw = (self.age.value or "").strip()
            if not (age_raw == "" or re.fullmatch(r"\d{1,3}", age_raw) or is_age_undisclosed(age_raw)):
                await interaction.followup.send(
                    "❌ รูปแบบอายุไม่ถูกต้อง • ใส่เป็นตัวเลข 1–3 หลัก เช่น 21 • หรือเว้นว่าง/พิมพ์เพื่อ “ไม่ระบุ”",
                    ephemeral=True,
                )
                return

            # Validate nickname (optional)
            nick = (self.name.value or "").strip()
            if nick:
                if len(nick) < 2 or len(nick) > 10 or any(ch.isdigit() for ch in nick) or any(c in INVALID_CHARS for c in nick) or contains_emoji(nick):
                    await interaction.followup.send(
                        "❌ Nickname invalid (ต้องเป็นตัวอักษร 2–10 ตัว และห้ามตัวเลข/สัญลักษณ์/อีโมจิ)\nหากไม่ต้องการตั้งชื่อเล่น เว้นว่างได้",
                        ephemeral=True,
                    )
                    return
                if canon_full(nick) in discord_names_set(interaction.user):
                    await interaction.followup.send(
                        "❌ ชื่อเล่นต้องต่างจากชื่อในดิสคอร์ดของคุณจริง ๆ • ถ้าไม่ต้องการตั้งชื่อเล่น เว้นว่างได้",
                        ephemeral=True,
                    )
                    return

            # Validate gender (text-only if provided)
            gender_raw = (self.gender.value or "")
            if gender_raw.strip():
                if any(ch.isdigit() for ch in gender_raw) or any(c in INVALID_CHARS for c in gender_raw) or contains_emoji(gender_raw):
                    await interaction.followup.send("❌ Gender invalid. Text only.", ephemeral=True)
                    return

            # Validate birthday (optional)
            birthday_raw = (self.birthday.value or "").strip()
            bday_dt = None
            if birthday_raw:
                bday_dt = parse_birthday(birthday_raw)
                if not bday_dt:
                    await interaction.followup.send(
                        "❌ รูปแบบวันเกิดไม่ถูกต้อง (ใช้ dd/mm/yyyy เช่น 05/11/2004) • อนุญาต / - .",
                        ephemeral=True,
                    )
                    return
                # guard อายุ 0–120
                years = age_from_birthday(bday_dt)
                if not (0 <= years <= 120):
                    await interaction.followup.send("❌ วันเกิดไม่สมเหตุสมผล (อายุควรอยู่ระหว่าง 0–120 ปี)", ephemeral=True)
                    return

            # สร้าง embed และส่งเข้าห้องอนุมัติ
            channel = interaction.guild.get_channel(APPROVAL_CHANNEL_ID)
            if not channel:
                await notify_admin(interaction.guild, "ไม่พบห้อง APPROVAL_CHANNEL_ID")
                await interaction.followup.send("⚠️ ระบบขัดข้อง: ไม่พบห้องอนุมัติ แจ้งแอดมินเรียบร้อย", ephemeral=True)
                return

            display_nick = nick or "ไม่ระบุ"
            display_age = age_raw or "ไม่ระบุ"
            display_gender = gender_raw.strip() or "ไม่ระบุ"
            display_birthday = birthday_raw or "ไม่ระบุ"

            if build_verification_embed:
                embed = build_verification_embed(
                    interaction.user,
                    nickname=display_nick,
                    age_text=display_age,
                    gender_text=display_gender,
                    birthday_text=display_birthday,
                    account_risk_enabled=ACCOUNT_RISK_ENABLED,
                    hide_birthday_on_idcard=HIDE_BIRTHDAY_ON_IDCARD,
                )
            else:
                embed = build_embed_local(
                    interaction.user,
                    nickname=display_nick,
                    age_text=display_age,
                    gender_text=display_gender,
                    birthday_text=display_birthday,
                )

            # view สำหรับแอดมินกดอนุมัติ/ปฏิเสธ
            view = ApproveRejectView(
                user=interaction.user,
                gender_text=gender_raw,
                age_text=age_raw if age_raw else "ไม่ระบุ",
                birthday_text=birthday_raw,
            )

            msg = await channel.send(
                content=interaction.user.mention,
                embed=embed,
                view=view,
                allowed_mentions=discord.AllowedMentions(everyone=False, roles=False, users=True),
            )

            # บันทึกลง DB เป็น truth source
            await upsert_user(
                guild_id=interaction.guild.id,
                user_id=interaction.user.id,
                nickname=nick or None,
                gender_raw=gender_raw or None,
                birthday=bday_dt.date() if bday_dt else None,
                age_raw=age_raw or None,
                sent_at=now_bkk().astimezone(timezone.utc),
                last_msg_id=msg.id,
            )
            await set_last_msg_id(interaction.guild.id, interaction.user.id, msg.id)

            await interaction.followup.send(
                "✅ ส่งคำขอยืนยันตัวตนแล้ว กรุณารอการอนุมัติจากแอดมิน",
                ephemeral=True,
            )
        except Exception as e:
            await notify_admin(interaction.guild, f"เกิดข้อผิดพลาดตอนส่งแบบฟอร์มของ {interaction.user.mention}: {e!r}")
            try:
                await interaction.followup.send("❌ ระบบขัดข้อง กรุณาลองใหม่ภายหลัง", ephemeral=True)
            except Exception:
                pass


# ========== VERIFY BUTTON VIEW ==========
class VerificationView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Verify Identity / ยืนยันตัวตน", style=discord.ButtonStyle.success, emoji="✅", custom_id="verify_button")
    async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        member = interaction.guild.get_member(interaction.user.id) or await interaction.guild.fetch_member(interaction.user.id)
        if member and any(r.id == ROLE_ID_TO_GIVE for r in member.roles):
            await interaction.response.send_message(
                "✅ คุณได้รับการยืนยันตัวตนแล้ว • หากคิดว่าเป็นความผิดพลาด กรุณาติดต่อผู้ดูแล",
                ephemeral=True,
            )
            return
        await interaction.response.send_modal(VerificationForm())


# สำหรับ add_view แบบ persistent หลังบอทรีสตาร์ท
class PersistentVerificationView(VerificationView):
    pass


# ========== APPROVE / REJECT VIEW ==========
class ApproveRejectView(discord.ui.View):
    def __init__(self, user: discord.User, gender_text: str, age_text: str, birthday_text: str = ""):
        super().__init__(timeout=None)
        self.user = user
        self.gender_text = (gender_text or "").strip()
        self.age_text = (age_text or "").strip()
        self.birthday_text = (birthday_text or "").strip()

    @discord.ui.button(label="✅ Approve / อนุมัติ", style=discord.ButtonStyle.success, custom_id="approve_button")
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            if not interaction.response.is_done():
                await interaction.response.defer()

            # idempotent: กันกดซ้ำ
            ok_record = await record_decision(
                message_id=interaction.message.id,
                guild_id=interaction.guild.id,
                user_id=self.user.id,
                actor_id=interaction.user.id,
                decision="approve",
            )
            if not ok_record:
                # ตัดสินใจไปแล้ว: ปิดปุ่มเฉย ๆ
                await _finalize_buttons(interaction, decided="approve")
                return

            # จัด role
            member = interaction.guild.get_member(self.user.id) or await interaction.guild.fetch_member(self.user.id)
            general_role = interaction.guild.get_role(ROLE_ID_TO_GIVE)
            gender_role = interaction.guild.get_role(resolve_gender_role_id(self.gender_text))

            # คิดยศอายุจากวันเกิดก่อน, ไม่มีค่อย fallback ตัวเลขอายุ
            age_role = None
            if self.birthday_text:
                bday_dt = parse_birthday(self.birthday_text)
                if bday_dt:
                    years = age_from_birthday(bday_dt)
                    if 0 <= years <= 120:
                        age_role = interaction.guild.get_role(resolve_age_role_id(str(years)))

            if age_role is None:
                age_role_id = resolve_age_role_id(self.age_text)
                age_role = interaction.guild.get_role(age_role_id) if age_role_id else None

            if not (member and general_role and gender_role):
                await interaction.followup.send("❌ Member หรือ Role ที่จำเป็นหายไป", ephemeral=True)
                await notify_admin(interaction.guild, "อนุมัติไม่สำเร็จ: ไม่พบ member/role")
                return

            # enforce single gender/age role
            gender_ids = set(_gender_role_ids_all())
            age_ids = set(_age_role_ids_all())

            to_remove_gender = [r for r in member.roles if r.id in gender_ids and (gender_role is None or r.id != gender_role.id)]
            to_remove_age = []
            if age_role:
                to_remove_age = [r for r in member.roles if r.id in age_ids and r.id != age_role.id]

            roles_to_add = []
            if general_role and general_role not in member.roles: roles_to_add.append(general_role)
            if gender_role and gender_role not in member.roles: roles_to_add.append(gender_role)
            if age_role and age_role not in member.roles: roles_to_add.append(age_role)

            ok, info = await apply_roles_safely(
                interaction.guild, member,
                add=roles_to_add,
                remove=[*to_remove_gender, *to_remove_age],
                reason="Verified",
            )
            if not ok:
                await interaction.followup.send(f"❌ ตั้งยศไม่สำเร็จ: {info}", ephemeral=True)
                return

            # mark DB
            await mark_approved(interaction.guild.id, self.user.id)

            await _finalize_buttons(interaction, decided="approve")

        except Exception as e:
            await notify_admin(interaction.guild, f"Approve error: {e!r}")
            try:
                await _finalize_buttons(interaction, decided="approve")
            except Exception:
                pass

    @discord.ui.button(label="❌ Reject / ปฏิเสธ", style=discord.ButtonStyle.danger, custom_id="reject_button")
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            if not interaction.response.is_done():
                await interaction.response.defer()

            ok_record = await record_decision(
                message_id=interaction.message.id,
                guild_id=interaction.guild.id,
                user_id=self.user.id,
                actor_id=interaction.user.id,
                decision="reject",
            )
            if not ok_record:
                await _finalize_buttons(interaction, decided="reject")
                return

            # DM แจ้งผู้ใช้
            try:
                await self.user.send(
                    "❌ Your verification was rejected. Please contact admin.\n"
                    "❌ การยืนยันตัวตนของคุณไม่ผ่าน กรุณาติดต่อแอดมิน"
                )
            except Exception:
                await interaction.followup.send("⚠️ ไม่สามารถส่ง DM แจ้งผู้ใช้ได้", ephemeral=True)

            await mark_rejected(interaction.guild.id, self.user.id)
            await _finalize_buttons(interaction, decided="reject")

        except Exception as e:
            await notify_admin(interaction.guild, f"Reject error: {e!r}")
            try:
                await _finalize_buttons(interaction, decided="reject")
            except Exception:
                pass


# ========== INTERNAL: finalize message buttons ==========
async def _finalize_buttons(interaction: discord.Interaction, *, decided: str):
    for child in interaction.message.components[0].children if interaction.message and interaction.message.components else []:
        if getattr(child, "custom_id", None) == "approve_button":
            child.disabled = True
            # label ไม่แก้ได้หลังส่งแล้วใน discord.py ผ่าน object เดิม
        if getattr(child, "custom_id", None) == "reject_button":
            child.disabled = True

    # แก้ footer แสดงผู้ตัดสินใจ + เวลา
    try:
        msg = interaction.message
        if msg and msg.embeds:
            e = msg.embeds[0]
            actor = getattr(interaction.user, "display_name", None) or interaction.user.name
            stamp = now_bkk().strftime("%d/%m/%Y %H:%M")
            orig = e.footer.text or ""
            tag = "Approved" if decided == "approve" else "Rejected"
            footer = f"{orig} • {tag} by {actor} • {stamp}" if orig else f"{tag} by {actor} • {stamp}"
            e.set_footer(text=footer)
            await msg.edit(embed=e, view=None)  # ปิดปุ่มทิ้ง
        else:
            await interaction.message.edit(view=None)
    except discord.NotFound:
        pass
