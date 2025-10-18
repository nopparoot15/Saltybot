# saltybot/constants.py
import os

# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------
def _int(name: str, default: int | None = None) -> int:
    """อ่าน ENV เป็น int; ถ้าไม่ตั้งไว้และไม่มีค่า default จะยก Exception ชัดๆ"""
    val = os.getenv(name)
    if val is None or val == "":
        if default is None:
            raise RuntimeError(f"ENV {name} not set and no default in constants.py")
        return int(default)
    return int(val)


# ------------------------------------------------------------
# CHANNEL IDS  (ตั้งผ่าน ENV ได้ทั้งหมด)
# ------------------------------------------------------------
VERIFY_CHANNEL_ID          = _int("SALTY_VERIFY_CHANNEL_ID",          1402889712888447037)
APPROVAL_CHANNEL_ID        = _int("SALTY_APPROVAL_CHANNEL_ID",        1402889786712395859)
LOG_CHANNEL_ID             = _int("SALTY_LOG_CHANNEL_ID",             1418941833819590699)
ADMIN_NOTIFY_CHANNEL_ID    = _int("SALTY_ADMIN_NOTIFY_CHANNEL_ID",    1418941833819590699)
BIRTHDAY_CHANNEL_ID        = _int("SALTY_BIRTHDAY_CHANNEL_ID",        1323069987845312554)

# ------------------------------------------------------------
# ROLE IDS
# ------------------------------------------------------------
# role หลังยืนยันตัวตนสำเร็จ
ROLE_ID_TO_GIVE            = _int("SALTY_ROLE_VERIFIED_ID",           1321268883088211981)

# gender roles
ROLE_MALE                  = _int("SALTY_ROLE_MALE_ID",               1321268883025559689)
ROLE_FEMALE                = _int("SALTY_ROLE_FEMALE_ID",             1321268883025559688)
ROLE_LGBT                  = _int("SALTY_ROLE_LGBT_ID",               1321268883025559687)
ROLE_GENDER_UNDISCLOSED    = _int("SALTY_ROLE_GENDER_UNDISCLOSED_ID", 1419046348023398421)

# age roles
ROLE_0_12                  = _int("SALTY_ROLE_0_12_ID",               1402907371696558131)
ROLE_13_15                 = _int("SALTY_ROLE_13_15_ID",              1344232758129594379)
ROLE_16_18                 = _int("SALTY_ROLE_16_18_ID",              1344232891093090377)
ROLE_19_21                 = _int("SALTY_ROLE_19_21_ID",              1344232979647565924)
ROLE_22_24                 = _int("SALTY_ROLE_22_24_ID",              1344233048593403955)
ROLE_25_29                 = _int("SALTY_ROLE_25_29_ID",              1418703710137094357)
ROLE_30_34                 = _int("SALTY_ROLE_30_34_ID",              1418703702843457576)
ROLE_35_39                 = _int("SALTY_ROLE_35_39_ID",              1418703707100545075)
ROLE_40_44                 = _int("SALTY_ROLE_40_44_ID",              1418703944711929917)
ROLE_45_49                 = _int("SALTY_ROLE_45_49_ID",              1418703955176718396)
ROLE_50_54                 = _int("SALTY_ROLE_50_54_ID",              1418704062592843948)
ROLE_55_59                 = _int("SALTY_ROLE_55_59_ID",              1418704067194261615)
ROLE_60_64                 = _int("SALTY_ROLE_60_64_ID",              1418704072617496666)
ROLE_65_UP                 = _int("SALTY_ROLE_65_UP_ID",              1418704076119736390)
ROLE_AGE_UNDISCLOSED       = _int("SALTY_ROLE_AGE_UNDISCLOSED_ID",    1419045340576747663)

# ------------------------------------------------------------
# FEATURE FLAGS / CONFIG (ค่าเริ่มต้นปรับได้จาก ENV)
# ------------------------------------------------------------
APPEND_FORM_NAME_TO_NICK   = os.getenv("SALTY_APPEND_FORM_NAME_TO_NICK", "false").lower() == "true"

# Auto refresh (สำหรับ daemon refresh อายุ ถ้าใช้งาน)
AUTO_REFRESH_ENABLED       = os.getenv("SALTY_AUTO_REFRESH_ENABLED", "true").lower() == "true"
REFRESH_TZ_HOURS_OFFSET    = int(os.getenv("SALTY_REFRESH_TZ_HOURS_OFFSET", "7"))
REFRESH_FREQUENCY          = os.getenv("SALTY_REFRESH_FREQUENCY", "YEARLY")  # YEARLY | MONTHLY | WEEKLY | DAILY
REFRESH_AT_HOUR            = int(os.getenv("SALTY_REFRESH_AT_HOUR", "6"))
REFRESH_AT_MINUTE          = int(os.getenv("SALTY_REFRESH_AT_MINUTE", "0"))
REFRESH_AT_DAY             = int(os.getenv("SALTY_REFRESH_AT_DAY", "1"))     # ใช้กับ MONTHLY/YEARLY
REFRESH_AT_MONTH           = int(os.getenv("SALTY_REFRESH_AT_MONTH", "1"))   # ใช้กับ YEARLY
REFRESH_AT_WEEKDAY         = int(os.getenv("SALTY_REFRESH_AT_WEEKDAY", "0")) # ใช้กับ WEEKLY (0=Mon..6=Sun)

# Account age risk
ACCOUNT_RISK_ENABLED       = os.getenv("SALTY_ACCOUNT_RISK_ENABLED", "true").lower() == "true"
MIN_ACCOUNT_AGE_DAYS_HIGH  = int(os.getenv("SALTY_MIN_ACCOUNT_AGE_DAYS_HIGH", "3"))
MIN_ACCOUNT_AGE_DAYS_MED   = int(os.getenv("SALTY_MIN_ACCOUNT_AGE_DAYS_MED", "7"))

# Birthday notify
HBD_NOTIFY_ENABLED         = os.getenv("SALTY_HBD_NOTIFY_ENABLED", "true").lower() == "true"
HBD_NOTIFY_HOUR            = int(os.getenv("SALTY_HBD_NOTIFY_HOUR", "9"))
HBD_NOTIFY_MINUTE          = int(os.getenv("SALTY_HBD_NOTIFY_MINUTE", "0"))

# Privacy
HIDE_BIRTHDAY_ON_IDCARD    = os.getenv("SALTY_HIDE_BIRTHDAY_ON_IDCARD", "true").lower() == "true"
BIRTHDAY_HIDDEN_TEXT       = os.getenv("SALTY_BIRTHDAY_HIDDEN_TEXT", "ไม่แสดง")

# ------------------------------------------------------------
# Derived role sets (โมดูล verification import ไปใช้)
# ------------------------------------------------------------
GENDER_ROLE_IDS_ALL = [
    ROLE_MALE,
    ROLE_FEMALE,
    ROLE_LGBT,
    ROLE_GENDER_UNDISCLOSED,
]

AGE_ROLE_IDS_ALL = [
    ROLE_0_12, ROLE_13_15, ROLE_16_18, ROLE_19_21, ROLE_22_24,
    ROLE_25_29, ROLE_30_34, ROLE_35_39, ROLE_40_44, ROLE_45_49,
    ROLE_50_54, ROLE_55_59, ROLE_60_64, ROLE_65_UP, ROLE_AGE_UNDISCLOSED,
]
