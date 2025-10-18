import time
from typing import Dict, Set

PENDING_TTL_SEC = 24 * 3600

_pending_verifications: Dict[int, float] = {}
_decided_messages: Set[int] = set()

def pending_is_blocked(user_id: int) -> bool:
    t = _pending_verifications.get(user_id)
    if not t:
        return False
    if time.time() - t > PENDING_TTL_SEC:
        _pending_verifications.pop(user_id, None)
        return False
    return True

def pending_set(user_id: int) -> None:
    _pending_verifications[user_id] = time.time()

def pending_clear(user_id: int) -> None:
    _pending_verifications.pop(user_id, None)

def mark_msg_decided(message_id: int) -> bool:
    if message_id in _decided_messages:
        return False
    _decided_messages.add(message_id)
    return True
