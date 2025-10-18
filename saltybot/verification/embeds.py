import discord
from saltybot.config import HIDE_BIRTHDAY_ON_IDCARD, BIRTHDAY_HIDDEN_TEXT

def copy_embed_fields(src: discord.Embed) -> discord.Embed:
    e = discord.Embed()
    e.title = src.title or discord.Embed.Empty
    e.description = src.description or discord.Embed.Empty
    if getattr(src, "color", None) is not None:
        e.color = src.color
    if getattr(src, "author", None):
        e.set_author(name=getattr(src.author, "name", None), icon_url=getattr(src.author, "icon_url", None), url=getattr(src.author, "url", None))
    if getattr(src, "footer", None):
        e.set_footer(text=getattr(src.footer, "text", None), icon_url=getattr(src.footer, "icon_url", None))
    if src.image and src.image.url: e.set_image(url=src.image.url)
    if src.thumbnail and src.thumbnail.url: e.set_thumbnail(url=src.thumbnail.url)
    for f in src.fields:
        e.add_field(name=f.name, value=f.value, inline=f.inline)
    return e

def mask_birthday_field_for_idcard(e: discord.Embed):
    try:
        for i, f in enumerate(e.fields):
            nm = (f.name or "").lower()
            if ("birthday" in nm) or ("วันเกิด" in nm):
                if HIDE_BIRTHDAY_ON_IDCARD:
                    e.set_field_at(i, name=f.name, value=BIRTHDAY_HIDDEN_TEXT, inline=False)
                break
    except Exception:
        pass
