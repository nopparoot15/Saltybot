from typing import Optional, Literal
from datetime import date, datetime, timezone
from .db import pool

# ---------- USERS ----------
async def upsert_user(
    guild_id: int, user_id: int, *,
    nickname: Optional[str], gender_raw: Optional[str],
    birthday: Optional[date], age_raw: Optional[str],
    sent_at: Optional[datetime], last_msg_id: Optional[int]
):
    sql = """
    insert into users(guild_id,user_id,nickname,gender_raw,birthday,age_raw,sent_at,last_msg_id)
    values($1,$2,$3,$4,$5,$6,$7,$8)
    on conflict (guild_id,user_id)
    do update set
      nickname=$3, gender_raw=$4, birthday=$5, age_raw=$6, sent_at=$7, last_msg_id=$8
    """
    await pool().execute(sql, guild_id, user_id, nickname, gender_raw, birthday, age_raw, sent_at, last_msg_id)

async def get_user(guild_id: int, user_id: int) -> Optional[dict]:
    sql = "select * from users where guild_id=$1 and user_id=$2"
    row = await pool().fetchrow(sql, guild_id, user_id)
    return dict(row) if row else None

async def mark_approved(guild_id: int, user_id: int):
    sql = "update users set approved_at=now(), rejected_at=null where guild_id=$1 and user_id=$2"
    await pool().execute(sql, guild_id, user_id)

async def mark_rejected(guild_id: int, user_id: int):
    sql = "update users set rejected_at=now(), approved_at=null where guild_id=$1 and user_id=$2"
    await pool().execute(sql, guild_id, user_id)

async def set_last_msg_id(guild_id: int, user_id: int, msg_id: int):
    sql = "update users set last_msg_id=$3 where guild_id=$1 and user_id=$2"
    await pool().execute(sql, guild_id, user_id, msg_id)

# ---------- DECISIONS (idempotency) ----------
async def record_decision(message_id: int, guild_id: int, user_id: int, actor_id: int, decision: Literal['approve','reject']) -> bool:
    """
    คืน True ถ้าบันทึกสำเร็จ (ยังไม่เคยตัดสินใจ), False ถ้า message_id เคยถูกตัดสินใจไปแล้ว
    """
    try:
        sql = "insert into decisions(message_id,guild_id,user_id,actor_id,decision) values($1,$2,$3,$4,$5)"
        await pool().execute(sql, message_id, guild_id, user_id, actor_id, decision)
        return True
    except Exception:
        # unique violation → เคยตัดสินใจแล้ว
        return False

# ---------- HBD ----------
async def hbd_already_sent(guild_id: int, user_id: int, date_utc: date) -> bool:
    sql = "select 1 from hbd_sent where guild_id=$1 and user_id=$2 and date_utc=$3"
    row = await pool().fetchrow(sql, guild_id, user_id, date_utc)
    return bool(row)

async def mark_hbd_sent(guild_id: int, user_id: int, date_utc: date):
    sql = "insert into hbd_sent(guild_id,user_id,date_utc) values($1,$2,$3) on conflict do nothing"
    await pool().execute(sql, guild_id, user_id, date_utc)
