import re
from saltybot.constants import (
    ROLE_0_12, ROLE_13_15, ROLE_16_18, ROLE_19_21, ROLE_22_24,
    ROLE_25_29, ROLE_30_34, ROLE_35_39, ROLE_40_44, ROLE_45_49,
    ROLE_50_54, ROLE_55_59, ROLE_60_64, ROLE_65_UP, ROLE_AGE_UNDISCLOSED
)
def _norm_simple(s: str) -> str:
    return re.sub(r'[\s\.\-_\/\\]+', '', (s or '').strip().lower())

AGE_UNDISCLOSED_ALIASES = {_norm_simple(x) for x in {
    "ไม่ระบุ","ไม่บอก","ไม่เปิดเผย","ไม่สะดวกกรอก","ไม่สะดวก","ไม่ต้องการระบุ","ปกปิด",
    "prefer not to say","undisclosed","unspecified","unknown","private","secret","n/a","na","none","x","-","—"
}}

def is_age_undisclosed(text: str) -> bool:
    t = _norm_simple(text)
    return (t == "") or (t in AGE_UNDISCLOSED_ALIASES)

def resolve_age_role_id(age_text: str) -> int | None:
    if is_age_undisclosed(age_text):
        return ROLE_AGE_UNDISCLOSED
    try:
        age = int((age_text or "").strip())
    except ValueError:
        return None
    slots = [
        ((0,12), ROLE_0_12), ((13,15), ROLE_13_15), ((16,18), ROLE_16_18),
        ((19,21), ROLE_19_21), ((22,24), ROLE_22_24), ((25,29), ROLE_25_29),
        ((30,34), ROLE_30_34), ((35,39), ROLE_35_39), ((40,44), ROLE_40_44),
        ((45,49), ROLE_45_49), ((50,54), ROLE_50_54), ((55,59), ROLE_55_59),
        ((60,64), ROLE_60_64), ((65,200), ROLE_65_UP),
    ]
    for (lo, hi), rid in slots:
        if lo <= age <= hi and rid > 0:
            return rid
    return None
