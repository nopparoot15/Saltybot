import discord
from saltybot.constants import AGE_ROLE_IDS_ALL, ROLE_AGE_UNDISCLOSED
from saltybot.utils.timez import years_between, now_bkk, parse_local_dt_ddmmyyyy_hhmm
from .indexer import find_embed_field, latest_verification_embed_for
from .birthday import parse_birthday, age_from_birthday
from .age import resolve_age_role_id, is_age_undisclosed

async def refresh_age_single(guild: discord.Guild, member: discord.Member):
    embed = await latest_verification_embed_for(member)
    if not embed:
        return False, "no-embed"
    # 1) use birthday if present
    btxt = find_embed_field(embed, "birthday", "วันเกิด")
    if btxt:
        bdt = parse_birthday(str(btxt))
        if bdt:
            years = age_from_birthday(bdt)
            return await _apply_age_role(member, years, reason=f"Refresh (birthday) → {years}")
    # 2) fallback age + sent at
    age_text = find_embed_field(embed, "age", "อายุ")
    sent_text = find_embed_field(embed, "sent at")
    if not age_text or not sent_text:
        return False, "missing-age-or-sent"
    if is_age_undisclosed(str(age_text)):
        return await _apply_age_role(member, None, undisclosed=True, reason="Refresh → undisclosed")
    try:
        old_age = int(str(age_text).strip())
    except ValueError:
        return False, "age-not-int"
    sent_dt = parse_local_dt_ddmmyyyy_hhmm(sent_text)
    if not sent_dt:
        return False, "bad-sent-at"
    added = years_between(sent_dt, now_bkk())
    new_age = max(old_age + added, 0)
    return await _apply_age_role(member, new_age, reason=f"Refresh → now {new_age}")

async def _apply_age_role(member: discord.Member, years: int | None, *, undisclosed=False, reason=""):
    from saltybot.constants import AGE_ROLE_IDS_ALL, ROLE_AGE_UNDISCLOSED
    guild = member.guild
    if undisclosed:
        new_role = guild.get_role(ROLE_AGE_UNDISCLOSED)
    else:
        role_id = resolve_age_role_id(str(years))
        new_role = guild.get_role(role_id) if role_id else None

    to_remove = [r for r in member.roles if r.id in AGE_ROLE_IDS_ALL and (new_role is None or r.id != new_role.id)]
    try:
        if to_remove:
            await member.remove_roles(*to_remove, reason=reason)
        if new_role and new_role not in member.roles:
            await member.add_roles(new_role, reason=reason)
    except discord.Forbidden:
        return False, "forbidden"
    except discord.HTTPException:
        return False, "http"
    return True, new_role.name if new_role else "-"
