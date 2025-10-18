# saltybot/run_with_migration.py
import os, asyncio, asyncpg, pathlib, sys

SQL_PATH = pathlib.Path(__file__).resolve().parents[1] / "migrations" / "0001_init.sql"

async def main():
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        print("❌ DATABASE_URL not set", file=sys.stderr)
        sys.exit(1)

    if SQL_PATH.exists():
        sql = SQL_PATH.read_text("utf-8")
        conn = await asyncpg.connect(dsn)
        try:
            await conn.execute(sql)
            print("✅ Migration applied successfully")
        finally:
            await conn.close()
    else:
        print(f"⚠️ Migration file not found: {SQL_PATH}")

    # เรียก app._runner() โดยตรงแทน main()
    from saltybot.app import _runner
    await _runner()

if __name__ == "__main__":
    asyncio.run(main())
