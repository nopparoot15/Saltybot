import io, discord
from config import HIDE_BIRTHDAY_ON_IDCARD, BIRTHDAY_HIDDEN_TEXT

def copy_embed_fields(src: discord.Embed) -> discord.Embed:
    e = discord.Embed()
    if src.title: e.title = src.title
    if src.description: e.description = src.description
    if getattr(src, "color", None) is not None: e.color = src.color
    if getattr(src, "author", None):
        name = getattr(src.author, "name", None)
        icon = getattr(src.author, "icon_url", None)
        url = getattr(src.author, "url", None)
        if name or icon or url:
            e.set_author(name=name or None, icon_url=icon or None, url=url or None)
    if getattr(src, "footer", None):
        text = getattr(src.footer, "text", None)
        icon = getattr(src.footer, "icon_url", None)
        if text or icon:
            e.set_footer(text=text or None, icon_url=icon or None)
    if src.image and src.image.url:
        e.set_image(url=src.image.url)
    if src.thumbnail and src.thumbnail.url:
        e.set_thumbnail(url=src.thumbnail.url)
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

async def build_avatar_attachment(user: discord.User):
    try:
        try:
            asset = user.display_avatar.with_format("webp").with_size(512)
            data = await asset.read()
            filename = f"avatar_{user.id}.webp"
        except Exception:
            asset = user.display_avatar.with_static_format("png").with_size(512)
            data = await asset.read()
            filename = f"avatar_{user.id}.png"
        f = discord.File(io.BytesIO(data), filename=filename)
        return f, filename
    except Exception:
        return None, None
