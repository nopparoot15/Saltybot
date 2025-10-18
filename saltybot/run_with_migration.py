import os, asyncio, pathlib, sys
import asyncpg

SQL_PATH = pathlib.Path(__file__).resolve().parents[1] / "migrations" / "0001_init.sql"

async def _run_migration(dsn: str):
    sql = SQL_PATH.read_text("utf-8")
    conn = await asyncpg.connect(dsn)
    try:
        await conn.execute(sql)
    finally:
        await conn.close()

async def main():
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        print("DATABASE_URL not set", file=sys.stderr)
        sys.exit(1)
    if not SQL_PATH.exists():
        print(f"Migration file not found: {SQL_PATH}", file=sys.stderr)
        sys.exit(1)

    # run migration (idempotent SQL ช่วยให้รันซ้ำได้)
    await _run_migration(dsn)

    # start bot
    from saltybot.app import main as start_bot
    await start_bot()

if __name__ == "__main__":
    asyncio.run(main())
