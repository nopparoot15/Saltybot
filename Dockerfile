FROM python:3.11-slim

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# แยกชั้น requirements ให้ cache ได้
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# คัดโค้ดจริง
COPY saltybot/ saltybot/
COPY migrations/ migrations/

# รันบอท (คุณใช้ run_with_migration ก็ได้ ถ้ามีไฟล์)
CMD ["python", "-m", "saltybot.run_with_migration"]
# หรือถ้าไม่มีไฟล์นั้น:
# CMD ["python", "-m", "saltybot.app"]
