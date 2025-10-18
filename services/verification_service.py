import discord
from typing import Optional
from config import ROLE_ID_TO_GIVE, AGE_ROLE_IDS_ALL, GENDER_ROLE_IDS_ALL, TZ
from db.repo import VerifyRepo, MemberRepo, ApprovalIndexRepo
from utils.validators import resolve_gender_role_id, resolve_age_role_id, parse_birthday, age_from_birthday

class VerificationService:
    def __init__(self, verify_repo: VerifyRepo, member_repo: MemberRepo, approval_repo: ApprovalIndexRepo):
        self.verify_repo = verify_repo
        self.member_repo = member_repo
        self.approval_repo = approval_repo

    async def record_submission(self, *, guild: discord.Guild, user: discord.User, channel_id:int, message_id:int|None,
                                nickname:str, age_text:str, gender_text:str, birthday_text:str,
                                account_age_days:int|None, account_risk:str|None):
        await self.verify_repo.insert_request(guild.id, user.id, channel_id, message_id, nickname, age_text, gender_text, birthday_text, account_age_days, account_risk)
        if message_id:
            await self.approval_repo.set_latest(guild.id, user.id, channel_id, message_id)
        await self.member_repo.upsert_member(guild.id, user.id, nickname=nickname, age_text=age_text, gender_text=gender_text, birthday_text=birthday_text)

    async def apply_roles_on_approve(self, guild: discord.Guild, member: discord.Member, *, gender_text:str, age_text:str, birthday_text:str):
        general_role = guild.get_role(ROLE_ID_TO_GIVE)
        gender_role  = guild.get_role(resolve_gender_role_id(gender_text))

        age_role = None
        if birthday_text:
            bdt = parse_birthday(birthday_text)
            if bdt:
                years = age_from_birthday(bdt)
                rid = resolve_age_role_id(str(years))
                age_role = guild.get_role(rid) if rid else None
        if age_role is None:
            rid = resolve_age_role_id(age_text)
            age_role = guild.get_role(rid) if rid else None

        # enforce single gender
        to_remove_gender = [r for r in member.roles if r.id in GENDER_ROLE_IDS_ALL and (gender_role is None or r.id != gender_role.id)]
        if to_remove_gender:
            await member.remove_roles(*to_remove_gender, reason="Verification: enforce single gender role")
        # enforce single age
        if age_role:
            to_remove_age = [r for r in member.roles if r.id in AGE_ROLE_IDS_ALL and r.id != age_role.id]
            if to_remove_age:
                await member.remove_roles(*to_remove_age, reason="Verification: enforce single age role")

        roles_to_add = []
        if general_role and general_role not in member.roles: roles_to_add.append(general_role)
        if gender_role and gender_role not in member.roles: roles_to_add.append(gender_role)
        if age_role and age_role not in member.roles: roles_to_add.append(age_role)
        if roles_to_add:
            await member.add_roles(*roles_to_add, reason="Verified")
