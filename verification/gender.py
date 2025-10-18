from .aliases import MALE_ALIASES, FEMALE_ALIASES, LGBT_ALIASES, GENDER_UNDISCLOSED_ALIASES, MALE_PREFIXES, FEMALE_PREFIXES, norm_gender
from saltybot.constants import ROLE_MALE, ROLE_FEMALE, ROLE_LGBT, ROLE_GENDER_UNDISCLOSED

def resolve_gender_role_id(text: str) -> int:
    t = norm_gender(text)
    if t in MALE_ALIASES or any(t.startswith(p) for p in MALE_PREFIXES):
        return ROLE_MALE
    if t in FEMALE_ALIASES or any(t.startswith(p) for p in FEMALE_PREFIXES):
        return ROLE_FEMALE
    if t in LGBT_ALIASES:
        return ROLE_LGBT
    if t in GENDER_UNDISCLOSED_ALIASES:
        return ROLE_GENDER_UNDISCLOSED
    return ROLE_GENDER_UNDISCLOSED
