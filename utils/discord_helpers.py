import re

def base_display_name(member) -> str:
    base = (
        getattr(member, "nick", None)
        or getattr(member, "global_name", None)
        or getattr(member, "display_name", None)
        or getattr(member, "name", None)
        or ""
    ).strip()
    return re.sub(r"\s*\(.*?\)\s*$", "", base).strip()

def discord_names_set(member, canon_full) -> set[str]:
    names = filter(None, {
        getattr(member, "nick", ""),
        getattr(member, "global_name", ""),
        getattr(member, "display_name", ""),
        getattr(member, "name", ""),
        base_display_name(member),
    })
    return {canon_full(x) for x in names if x}
