FROM python:3.11-slim

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=Asia/Bangkok

# ติดตั้ง tzdata ให้เวลาเป็น Asia/Bangkok
RUN apt-get update && apt-get install -y --no-install-recommends tzdata \
    && ln -fs /usr/share/zoneinfo/$TZ /etc/localtime \
    && dpkg-reconfigure -f noninteractive tzdata \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# แยกชั้น requirements ให้ cache ได้
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# คัดโค้ดจริง
COPY saltybot/ saltybot/
COPY migrations/ migrations/

# สร้าง user ไม่รันเป็น root (ปลอดภัยขึ้น)
RUN useradd -m botuser && chown -R botuser:botuser /app
USER botuser

# HEALTHCHECK (optional)
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s CMD python -c "import socket,sys; sys.exit(0)"

# สตาร์ท: migrate แล้วรันบอท (ไฟล์ที่เพิ่ม)
CMD ["python", "-m", "saltybot.run_with_migration"]
