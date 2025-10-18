from dataclasses import dataclass
from typing import Optional

@dataclass
class VerificationPayload:
    guild_id: int
    user_id: int
    nickname: str
    age_text: str
    gender_text: str
    birthday_text: str
    account_age_days: Optional[int]
    account_risk: Optional[str]
