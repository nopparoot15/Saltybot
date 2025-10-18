import asyncio
_locks: dict[int, asyncio.Lock] = {}

class message_lock:
    def __init__(self, msg_id:int):
        self._lock = _locks.setdefault(msg_id, asyncio.Lock())
    async def __aenter__(self):
        await self._lock.acquire()
        return self
    async def __aexit__(self, exc_type, exc, tb):
        self._lock.release()
