FROM python:3.11-slim

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# libpq/psql ต้องใช้ package เพิ่ม
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl gnupg postgresql-client \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY saltybot/ saltybot/
COPY migrations/ migrations/

# ใช้ psql รันไฟล์ แล้วสตาร์ทบอท
# เติม ?sslmode=require ถ้า DATABASE_URL ของ Railway ไม่มีพารามฯ นี้
CMD ["bash", "-lc", "psql \"${DATABASE_URL}?sslmode=require\" -v ON_ERROR_STOP=1 -f migrations/0001_init.sql && python -m saltybot.app"]
