from __future__ import annotations
from typing import Protocol, Optional, Tuple
from .pool import get_pool

class MemberRepo(Protocol):
    async def upsert_member(self, guild_id:int, user_id:int, *, nickname:str|None, age_text:str|None,
                            gender_text:str|None, birthday_text:str|None) -> None: ...

class VerifyRepo(Protocol):
    async def insert_request(self, guild_id:int, user_id:int, channel_id:int, message_id:int|None,
                             nickname:str, age_text:str, gender_text:str, birthday_text:str,
                             account_age_days:int|None, account_risk:str|None) -> int: ...
    async def set_request_status(self, guild_id:int, message_id:int, status:str, decided_by:int) -> None: ...

class ApprovalIndexRepo(Protocol):
    async def set_latest(self, guild_id:int, user_id:int, channel_id:int, message_id:int) -> None: ...
    async def get_latest(self, guild_id:int, user_id:int) -> Optional[tuple[int,int]]: ...

class AgeRefreshRepo(Protocol):
    async def already_ran(self, guild_id:int, tag:str) -> bool: ...
    async def mark_ran(self, guild_id:int, tag:str) -> None: ...

class HBDRepo(Protocol):
    async def already_sent(self, guild_id:int, user_id:int, date_local:str) -> bool: ...
    async def mark_sent(self, guild_id:int, user_id:int, date_local:str, message_id:int|None) -> None: ...

# Implementations
class PgMemberRepo:
    async def upsert_member(self, guild_id:int, user_id:int, **kw) -> None:
        q = ("""
        INSERT INTO members (guild_id,user_id,nickname,age_text,gender_text,birthday_text)
        VALUES ($1,$2,$3,$4,$5,$6)
        ON CONFLICT (guild_id,user_id)
        DO UPDATE SET nickname=EXCLUDED.nickname,
                      age_text=EXCLUDED.age_text,
                      gender_text=EXCLUDED.gender_text,
                      birthday_text=EXCLUDED.birthday_text,
                      updated_at=now();
        """)
        pool = await get_pool()
        async with pool.acquire() as con:
            await con.execute(q, guild_id, user_id, kw.get('nickname'), kw.get('age_text'), kw.get('gender_text'), kw.get('birthday_text'))

class PgVerifyRepo:
    async def insert_request(self, guild_id:int, user_id:int, channel_id:int, message_id:int|None,
                             nickname:str, age_text:str, gender_text:str, birthday_text:str,
                             account_age_days:int|None, account_risk:str|None) -> int:
        q = ("""
        INSERT INTO verification_requests
          (guild_id,user_id,channel_id,message_id,nickname,age_text,gender_text,birthday_text,account_age_days,account_risk)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)
        RETURNING id;
        """)
        pool = await get_pool()
        async with pool.acquire() as con:
            return await con.fetchval(q, guild_id, user_id, channel_id, message_id, nickname, age_text, gender_text, birthday_text, account_age_days, account_risk)

    async def set_request_status(self, guild_id:int, message_id:int, status:str, decided_by:int) -> None:
        q = ("""
        UPDATE verification_requests SET status=$1, decided_by=$2, decided_at=now()
        WHERE guild_id=$3 AND message_id=$4 AND status='SUBMITTED'
        """)
        pool = await get_pool()
        async with pool.acquire() as con:
            await con.execute(q, status, decided_by, guild_id, message_id)

class PgApprovalIndexRepo:
    async def set_latest(self, guild_id:int, user_id:int, channel_id:int, message_id:int) -> None:
        q = ("""
        INSERT INTO approval_index (guild_id,user_id,channel_id,message_id)
        VALUES ($1,$2,$3,$4)
        ON CONFLICT (guild_id,user_id) DO UPDATE SET channel_id=EXCLUDED.channel_id, message_id=EXCLUDED.message_id, created_at=now();
        """)
        pool = await get_pool()
        async with pool.acquire() as con:
            await con.execute(q, guild_id, user_id, channel_id, message_id)

    async def get_latest(self, guild_id:int, user_id:int):
        q = "SELECT channel_id, message_id FROM approval_index WHERE guild_id=$1 AND user_id=$2"
        pool = await get_pool()
        async with pool.acquire() as con:
            row = await con.fetchrow(q, guild_id, user_id)
            return (row['channel_id'], row['message_id']) if row else None

class PgAgeRefreshRepo:
    async def already_ran(self, guild_id:int, tag:str) -> bool:
        q = "SELECT 1 FROM age_refresh_runs WHERE guild_id=$1 AND tag=$2"
        pool = await get_pool()
        async with pool.acquire() as con:
            return (await con.fetchrow(q, guild_id, tag)) is not None
    async def mark_ran(self, guild_id:int, tag:str) -> None:
        q = "INSERT INTO age_refresh_runs (guild_id, tag) VALUES ($1,$2) ON CONFLICT DO NOTHING"
        pool = await get_pool()
        async with pool.acquire() as con:
            await con.execute(q, guild_id, tag)

class PgHBDRepo:
    async def already_sent(self, guild_id:int, user_id:int, date_local:str) -> bool:
        q = "SELECT 1 FROM hbd_sent WHERE guild_id=$1 AND user_id=$2 AND date_local=$3"
        pool = await get_pool()
        async with pool.acquire() as con:
            return (await con.fetchrow(q, guild_id, user_id, date_local)) is not None
    async def mark_sent(self, guild_id:int, user_id:int, date_local:str, message_id:int|None) -> None:
        q = "INSERT INTO hbd_sent (guild_id,user_id,date_local,message_id) VALUES ($1,$2,$3,$4) ON CONFLICT DO NOTHING"
        pool = await get_pool()
        async with pool.acquire() as con:
            await con.execute(q, guild_id, user_id, date_local, message_id)
