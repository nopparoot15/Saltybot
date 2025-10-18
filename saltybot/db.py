import os, asyncpg, asyncio

_pool: asyncpg.Pool | None = None

async def init_pool():
    global _pool
    if _pool:  # already
        return _pool
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL is not set")
    _pool = await asyncpg.create_pool(dsn, min_size=1, max_size=5, command_timeout=60)
    return _pool

async def close_pool():
    global _pool
    if _pool:
        await _pool.close()
        _pool = None

def pool():
    if not _pool:
        raise RuntimeError("DB pool not initialized")
    return _pool
