from saltybot.config import ADMIN_NOTIFY_CHANNEL_ID, APPROVAL_CHANNEL_ID

async def notify_admin(guild, text: str):
    try:
        ch = guild.get_channel(ADMIN_NOTIFY_CHANNEL_ID) or guild.get_channel(APPROVAL_CHANNEL_ID)
        if ch:
            await ch.send(f"🔔 **Admin Notice:** {text}")
    except Exception:
        pass
