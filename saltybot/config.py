from zoneinfo import ZoneInfo

# === Channels ===
VERIFY_CHANNEL_ID = 1402889712888447037
APPROVAL_CHANNEL_ID = 1402889786712395859
LOG_CHANNEL_ID = 1418941833819590699
ADMIN_NOTIFY_CHANNEL_ID = 1418941833819590699
BIRTHDAY_CHANNEL_ID = 1323069987845312554

# === Bot ===
BOT_PREFIX = "$"

# === Privacy / ID card ===
HIDE_BIRTHDAY_ON_IDCARD = True
BIRTHDAY_HIDDEN_TEXT = "ไม่แสดง"

# === Auto refresh scheduler ===
AUTO_REFRESH_ENABLED = True
REFRESH_TZ = ZoneInfo("Asia/Bangkok")
REFRESH_FREQUENCY = "YEARLY"       # YEARLY | MONTHLY | WEEKLY | DAILY
REFRESH_AT_HOUR = 6
REFRESH_AT_MINUTE = 0
REFRESH_AT_DAY = 1
REFRESH_AT_MONTH = 1
REFRESH_AT_WEEKDAY = 0

# === Account risk (age only) ===
ACCOUNT_RISK_ENABLED = True
MIN_ACCOUNT_AGE_DAYS_HIGH = 3
MIN_ACCOUNT_AGE_DAYS_MED  = 7

# === HBD ===
HBD_NOTIFY_ENABLED = True
HBD_NOTIFY_HOUR = 9
HBD_NOTIFY_MINUTE = 0
HBD_MESSAGES = [
    "🎉🎂 สุขสันต์วันเกิด {mention}! ขอให้ปีนี้มีแต่สิ่งดี ๆ เข้ามา 🥳",
    "✨🎂 HBD {mention}! สุขภาพแข็งแรง สมหวังทุกเรื่องนะ!",
    "🥳🎉 Happy Birthday {mention}! ขอให้รอยยิ้มอยู่กับเธอทั้งปี",
    "🎈🎂 สุขสันต์วันเกิดนะ {mention}! งานปัง เงินปั๊วะ ความสุขล้น ๆ",
    "🍰🎉 HBD {mention}! ขอให้ทุกความพยายามสำเร็จสวยงาม",
    "🌟🎂 Happy Birthday {mention}! ให้วันนี้พิเศษกว่าทุกวัน",
    "🎁🎉 สุขสันต์วันเกิด {mention}! ขอให้สมหวังในสิ่งที่ตั้งใจ",
    "🧁🎈 HBD {mention}! พักผ่อนให้พอ มีแรงลุยต่อทั้งปีนะ",
    "🌈🎂 Happy Birthday {mention}! ขอให้โชคดีและมีแต่เรื่องดี ๆ",
    "💫🎉 สุขสันต์วันเกิด {mention}! ให้ทุกวันเต็มไปด้วยพลังบวก",
]

# === Nick behaviour ===
APPEND_FORM_NAME_TO_NICK = False
