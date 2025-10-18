# Discord Verify Bot — Modular PG Architecture (v1)

Modular Discord verification bot with Postgres persistence, persistent views, and clean layering.

## Quick start

1. **Install deps**
   ```bash
   python -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Prepare Postgres**
   - Set `DATABASE_URL` (e.g., `postgresql://user:pass@host:5432/db`)
   - Apply schema:
     ```bash
     psql "$DATABASE_URL" -f db/schema.sql
     ```

3. **Configure**
   - Edit `config.py` (IDs/timezone). Or set via env vars.

4. **Run**
   ```bash
   python bot.py
   ```

## Layout

```
discord-verify-bot/
├─ bot.py
├─ config.py
├─ db/
│  ├─ schema.sql
│  ├─ pool.py
│  └─ repo.py
├─ domain/
│  └─ models.py
├─ services/
│  ├─ verification_service.py
│  ├─ age_service.py
│  └─ hbd_service.py
├─ ui/
│  ├─ views.py
│  └─ messages.py
├─ commands/
│  ├─ verify_embed.py
│  ├─ idcard.py
│  ├─ admin.py
│  └─ help.py
├─ tasks/
│  ├─ age_refresh_daemon.py
│  └─ birthday_daemon.py
└─ utils/
   ├─ text.py
   ├─ time.py
   ├─ validators.py
   ├─ locks.py
   └─ auth.py
```

> This is a **reference implementation** extracted from your current codebase and split into modules.
