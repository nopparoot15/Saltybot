# saltybot/run_with_migration.py (เฉพาะส่วนตั้งค่า SSL แก้/แทนฟังก์ชัน run_migration)
import os, sys, asyncio, asyncpg, pathlib, ssl, traceback
from urllib.parse import urlparse, parse_qs

ROOT = pathlib.Path(__file__).resolve().parents[1]
SQL_FILE = ROOT / "migrations" / "0001_init.sql"

def _normalize_dsn(raw: str) -> str:
    if raw.startswith("postgres://"):
        raw = "postgresql://" + raw[len("postgres://"):]
    return raw

def _ssl_context_from_url(dsn: str) -> ssl.SSLContext:
    """
    รองรับพฤติกรรมแบบ libpq:
    - sslmode=require | prefer | allow  => บังคับ TLS แต่ 'ไม่ตรวจ cert'
    - sslmode=verify-ca | verify-full   => ตรวจ cert (default)
    นอกจากนี้ ถ้ามี ENV PGSSL_DISABLE_VERIFY=1 จะบังคับปิดตรวจ cert
    """
    ctx = ssl.create_default_context()
    url = urlparse(dsn)
    q = parse_qs(url.query or "")
    sslmode = (q.get("sslmode", ["verify-full"])[0] or "verify-full").lower()

    force_disable = os.getenv("PGSSL_DISABLE_VERIFY") == "1"
    if force_disable or sslmode in ("require", "prefer", "allow"):
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        print("[MIGRATE] ⚠️ SSL verify disabled (mode: {})".format(
            "ENV" if force_disable else sslmode
        ))
    else:
        # verify-ca / verify-full
        ctx.check_hostname = True
        ctx.verify_mode = ssl.CERT_REQUIRED
        print(f"[MIGRATE] 🔒 SSL verify enabled (mode: {sslmode})")

    return ctx

async def run_migration(dsn: str):
    if not SQL_FILE.exists():
        print(f"[MIGRATE] ❌ SQL not found: {SQL_FILE}", file=sys.stderr)
        sys.exit(1)

    sql = SQL_FILE.read_text(encoding="utf-8")
    print(f"[MIGRATE] Running {SQL_FILE.name} ({len(sql)} bytes)")

    ssl_ctx = _ssl_context_from_url(dsn)
    conn = await asyncpg.connect(dsn, ssl=ssl_ctx)
    try:
        await conn.execute(sql)
        print("[MIGRATE] ✅ Done")
    finally:
        await conn.close()
