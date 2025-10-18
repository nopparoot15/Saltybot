"""
Verification domain package for Saltybot.
Exports the public API (commands setup, views, and resolvers).
"""

from .commands import setup as setup_verification_commands
from .views import PersistentVerificationView, VerificationForm, ApproveRejectView
from .age import resolve_age_role_id, is_age_undisclosed
from .gender import resolve_gender_role_id
from .birthday import parse_birthday, age_from_birthday

__all__ = [
    "setup_verification_commands",
    "PersistentVerificationView",
    "VerificationForm",
    "ApproveRejectView",
    "resolve_age_role_id",
    "is_age_undisclosed",
    "resolve_gender_role_id",
    "parse_birthday",
    "age_from_birthday",
]
