# Dockerfile (เร็วและเล็ก)
FROM python:3.11-slim

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# แยกชั้น requirements ให้ cache ได้
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ค่อยคัดโค้ดจริง
COPY saltybot/ saltybot/
COPY migrations/ migrations/

# ไม่ต้องติดตั้ง psql ถ้า migration ทำในโค้ด
CMD ["python", "-m", "saltybot.app"]
