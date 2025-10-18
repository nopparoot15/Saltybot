import discord
from saltybot.config import APPROVAL_CHANNEL_ID

async def find_latest_approval_message(guild: discord.Guild, member: discord.Member):
    ch = guild.get_channel(APPROVAL_CHANNEL_ID)
    if not ch: return None
    async for m in ch.history(limit=1000):
        if m.author == guild.me and m.embeds and member in m.mentions:
            return m
    return None

async def latest_verification_embed_for(member: discord.Member):
    msg = await find_latest_approval_message(member.guild, member)
    return msg.embeds[0] if msg and msg.embeds else None

def find_embed_field(embed: discord.Embed, *keys: str):
    keys = [k.lower() for k in keys]
    for f in embed.fields:
        name = (f.name or "").lower()
        if any(k in name for k in keys):
            return f.value
    return None

def set_or_add_field(embed: discord.Embed, name_keys: tuple[str, ...], display_name: str, value: str):
    name_keys_low = tuple(k.lower() for k in name_keys)
    for i, f in enumerate(embed.fields):
        nm = (f.name or "").lower()
        if any(k in nm for k in name_keys_low):
            embed.set_field_at(i, name=display_name, value=value, inline=False)
            return
    embed.add_field(name=display_name, value=value, inline=False)
