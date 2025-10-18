import discord
from utils.validators import resolve_age_role_id, age_from_birthday

class AgeService:
    async def sync_age_role_from_birthday(self, guild: discord.Guild, member: discord.Member, bday_dt):
        years = age_from_birthday(bday_dt)
        rid = resolve_age_role_id(str(years))
        role = guild.get_role(rid) if rid else None
        if not role:
            return False, "no mapped role"
        to_remove = [r for r in member.roles if r.id != role.id and r.name and 'ปี' in r.name]  # heuristic; adjust to AGE_ROLE_IDS_ALL if imported
        try:
            if to_remove:
                await member.remove_roles(*to_remove, reason=f"Birthday update → now {years}")
            if role not in member.roles:
                await member.add_roles(role, reason=f"Birthday update → now {years}")
            return True, role.name
        except discord.Forbidden:
            return False, "forbidden"
        except discord.HTTPException:
            return False, "http"
