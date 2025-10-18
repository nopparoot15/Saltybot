import os, sys, asyncio, asyncpg, pathlib, ssl, traceback

ROOT = pathlib.Path(__file__).resolve().parents[1]
SQL_FILE = ROOT / "migrations" / "0001_init.sql"

def _normalize_dsn(raw: str) -> str:
    # asyncpg ต้องใช้ postgresql://
    if raw.startswith("postgres://"):
        raw = "postgresql://" + raw[len("postgres://"):]
    return raw

async def run_migration(dsn: str):
    if not SQL_FILE.exists():
        print(f"[MIGRATE] ❌ SQL not found: {SQL_FILE}", file=sys.stderr)
        sys.exit(1)

    sql = SQL_FILE.read_text(encoding="utf-8")
    print(f"[MIGRATE] Running {SQL_FILE.name} ({len(sql)} bytes)")

    # Railway ต้อง SSL; ถ้าคุณอยากตรวจเข้ม ให้ใช้ค่า default
    # ถ้าติดใบรับรอง ให้ตั้ง PGSSL_DISABLE_VERIFY=1 ใน Railway
    ssl_ctx = ssl.create_default_context()
    if os.getenv("PGSSL_DISABLE_VERIFY") == "1":
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE
        print("[MIGRATE] ⚠️ SSL verify disabled")

    conn = await asyncpg.connect(dsn, ssl=ssl_ctx)
    try:
        await conn.execute(sql)
        print("[MIGRATE] ✅ Done")
    finally:
        await conn.close()

async def start_bot():
    # ให้ app.py มีฟังก์ชัน main() ที่ทำ bot.run(...)
    from saltybot.app import main
    await main()

async def main():
    dsn_raw = os.getenv("DATABASE_URL")
    if not dsn_raw:
        print("❌ DATABASE_URL is not set", file=sys.stderr)
        sys.exit(1)

    dsn = _normalize_dsn(dsn_raw)
    print("[BOOT] DSN scheme OK (postgresql://...).")

    try:
        await run_migration(dsn)
    except Exception:
        print("[MIGRATE] ❌ Failed:\n" + traceback.format_exc(), file=sys.stderr)
        sys.exit(1)

    try:
        await start_bot()
    except Exception:
        print("[BOT] ❌ Failed to start:\n" + traceback.format_exc(), file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
