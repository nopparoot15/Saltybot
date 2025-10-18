from datetime import datetime
from config import TZ

def now_local():
    return datetime.now(TZ)
