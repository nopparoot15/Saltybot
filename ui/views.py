import discord
from utils.auth import is_moderator
from utils.locks import message_lock
from utils.validators import parse_birthday, age_from_birthday
from utils.time import now_local
from db.repo import PgVerifyRepo, PgMemberRepo, PgApprovalIndexRepo
from services.verification_service import VerificationService
from config import APPROVAL_CHANNEL_ID, ROLE_ID_TO_GIVE, TZ

verify_service = VerificationService(PgVerifyRepo(), PgMemberRepo(), PgApprovalIndexRepo())

def _find_embed_field(embed: discord.Embed, *keys: str):
    keys_low = [k.lower() for k in keys]
    for f in embed.fields:
        name = (f.name or "").lower()
        if any(k in name for k in keys_low):
            return f.value
    return None

class VerificationView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Verify Identity / ยืนยันตัวตน", style=discord.ButtonStyle.success, emoji="✅", custom_id="verify_button")
    async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("ฟอร์มยืนยัน (modal) ยังไม่ถูกย้ายในตัวอย่างนี้ — นำ logic เดิมของคุณมาใส่ที่นี่ได้เลย", ephemeral=True)

class ApproveRejectPersistent(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="✅ Approve / อนุมัติ", style=discord.ButtonStyle.success, custom_id="approve_button")
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_moderator(interaction.user):
            await interaction.response.send_message("❌ เฉพาะผู้ดูแลเท่านั้น", ephemeral=True); return
        if not interaction.response.is_done():
            await interaction.response.defer()

        msg = interaction.message
        if not msg or not msg.embeds or not msg.mentions:
            await interaction.followup.send("❌ ข้อความไม่อยู่ในรูปแบบที่รองรับ", ephemeral=True); return

        async with message_lock(msg.id):
            target_user = msg.mentions[0]
            e = msg.embeds[0]
            gender_text   = _find_embed_field(e, "gender", "เพศ") or ""
            age_text      = _find_embed_field(e, "age", "อายุ") or "ไม่ระบุ"
            birthday_text = _find_embed_field(e, "birthday", "วันเกิด") or ""

            member = interaction.guild.get_member(target_user.id) or await interaction.guild.fetch_member(target_user.id)
            await verify_service.apply_roles_on_approve(interaction.guild, member, gender_text=gender_text, age_text=age_text, birthday_text=birthday_text)

            # mark DB
            await PgVerifyRepo().set_request_status(interaction.guild.id, msg.id, "APPROVED", interaction.user.id)

            # disable buttons + footer
            for child in self.children:
                if getattr(child, "custom_id", None) == "approve_button":
                    child.label = "✅ Approved / อนุมัติแล้ว"; child.style = discord.ButtonStyle.success
                elif getattr(child, "custom_id", None) == "reject_button":
                    child.style = discord.ButtonStyle.secondary
                child.disabled = True

            actor = getattr(interaction.user, "display_name", None) or interaction.user.name
            stamp = now_local().strftime("%d/%m/%Y %H:%M")
            orig = e.footer.text or ""
            e.set_footer(text=(f"{orig} • Approved by {actor} • {stamp}" if orig else f"Approved by {actor} • {stamp}"))
            await msg.edit(embed=e, view=self)

    @discord.ui.button(label="❌ Reject / ปฏิเสธ", style=discord.ButtonStyle.danger, custom_id="reject_button")
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_moderator(interaction.user):
            await interaction.response.send_message("❌ เฉพาะผู้ดูแลเท่านั้น", ephemeral=True); return
        if not interaction.response.is_done():
            await interaction.response.defer()

        msg = interaction.message
        if msg:
            await PgVerifyRepo().set_request_status(interaction.guild.id, msg.id, "REJECTED", interaction.user.id)

        # Disable
        for child in self.children:
            if getattr(child, "custom_id", None) == "reject_button":
                child.label = "❌ Rejected / ปฏิเสธแล้ว"; child.style = discord.ButtonStyle.danger
            elif getattr(child, "custom_id", None) == "approve_button":
                child.style = discord.ButtonStyle.secondary
            child.disabled = True

        try:
            e = msg.embeds[0]
            actor = getattr(interaction.user, "display_name", None) or interaction.user.name
            stamp = now_local().strftime("%d/%m/%Y %H:%M")
            orig = e.footer.text or ""
            e.set_footer(text=(f"{orig} • Rejected by {actor} • {stamp}" if orig else f"Rejected by {actor} • {stamp}"))
            await msg.edit(embed=e, view=self)
        except Exception:
            pass
