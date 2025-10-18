import re
def _norm_gender(s: str) -> str:
    s = (s or "").strip().lower()
    return re.sub(r'[\s\.\-_\/\\]+', '', s)

MALE_ALIASES = {_norm_gender(x) for x in {
    "ชาย","ผู้ชาย","เพศชาย","ช","ชา","ผช","ชายแท้","หนุ่ม",
    "male","man","boy","m","masculine","he","him",
    "男","男性","おとこ","だんせい","남","남자","남성",
}}
FEMALE_ALIASES = {_norm_gender(x) for x in {
    "หญิง","ผู้หญิง","เพศหญิง","ห","หญ","ผญ","สาว","ญ",
    "female","woman","girl","f","feminine","she","her",
    "女","女性","おんな","じょせい","여","여자","여성",
}}
LGBT_ALIASES = {_norm_gender(x) for x in {
    "lgbt","lgbtq","lgbtq+","nonbinary","non-binary","nb","enby",
    "trans","genderqueer","bigender","agender","genderfluid","queer","other",
    "เกย์","เลสเบี้ยน","ไบ","แพน","เพศทางเลือก","สาวสอง","ทอม","ดี้",
}}
GENDER_UNDISCLOSED_ALIASES = {_norm_gender(x) for x in {
    "ไม่ระบุ","ไม่อยากเปิดเผย","ไม่สะดวก","ไม่บอก",
    "prefer not to say","undisclosed","unspecified","unknown","private","secret","n/a","na","none","—","-",
}}

MALE_PREFIXES = {_norm_gender(x) for x in ["ช","ชา","ชาย","ผู้ช","เพศช","m","ma","man","男","おとこ","だん","남"]}
FEMALE_PREFIXES = {_norm_gender(x) for x in ["ห","หญ","หญิ","หญิง","ผู้ห","เพศห","f","fe","fem","woman","女","おんな","じょ","여"]}

def norm_gender(s: str) -> str:
    return _norm_gender(s)
