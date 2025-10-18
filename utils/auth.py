def is_moderator(member) -> bool:
    p = member.guild_permissions
    return p.administrator or p.manage_roles
