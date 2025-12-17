import re
from datetime import datetime
from dateutil import parser as dtparser

# 1) Phân loại thiên tai theo từ khóa (rule-based)
DISASTER_RULES = [
    ("earthquake", [r"\bđộng\s*đất\b", r"\brung\s*chấn\b", r"\bdự\s*chấn\b", r"\bnứt\s*đất\b", r"\bđứt\s*gãy\b"]),
    ("tsunami", [r"\bsóng\s*thần\b", r"\bcảnh\s*báo\s*sóng\s*thần\b"]),
    ("landslide", [r"\bsạt\s*lở\b", r"\blở\s*đất\b", r"\btrượt\s*đất\b", r"\btaluy\b", r"\bsạt\s*taluy\b", r"\bsạt\s*lở\s*bờ\b", r"\bsụt\s*lún\b"]),
    ("flood", [r"\bmưa\s*lũ\b", r"\blũ\b", r"\blụt\b", r"\bngập\s*lụt\b", r"\bngập\s*sâu\b", r"\blũ\s*quét\b", r"\blũ\s*ống\b", r"\btriều\s*cường\b", r"\bnước\s*dâng\b"]),
    ("storm", [r"\bbão\b", r"\bbão\s*số\b", r"\bsiêu\s*bão\b", r"\báp\s*thấp\b", r"\bATNĐ\b", r"\báp\s*thấp\s*nhiệt\s*đới\b"]),
    ("wind_hail", [r"\bgió\s*mạnh\b", r"\bgió\s*giật\b", r"\bdông\s*lốc\b", r"\blốc\b", r"\blốc\s*xoáy\b", r"\bvòi\s*rồng\b", r"\bmưa\s*đá\b", r"\bgiông\s*sét\b", r"\bsét\b"]),
    ("wildfire", [r"\bcháy\s*rừng\b", r"\bnguy\s*cơ\s*cháy\s*rừng\b"]),
    ("extreme_weather", [r"\bnắng\s*nóng\b", r"\bnắng\s*nóng\s*gay\s*gắt\b", r"\bhạn\s*hán\b", r"\bkhô\s*hạn\b", r"\brét\s*đậm\b", r"\brét\s*hại\b", r"\bbăng\s*giá\b", r"\bxâm\s*nhập\s*mặn\b"]),
]

RE_DEATHS = re.compile(r"(\d+)\s*(?:người\s*)?(?:chết|tử|tử\s*vong|mất\s*mạng)|(?:chết|tử|tử\s*vong|mất\s*mạng).*?(\d+)\s*người", re.IGNORECASE)
RE_MISSING = re.compile(r"(\d+)\s*(?:người\s*)?(?:mất\s*tích|biến\s*mất)|(?:mất\s*tích|biến\s*mất).*?(\d+)\s*người", re.IGNORECASE)
RE_INJURED = re.compile(r"(\d+)\s*(?:người\s*)?(?:bị\s*thương|thương\s*tích)|(?:bị\s*thương|thương\s*tích).*?(\d+)\s*người", re.IGNORECASE)
RE_DAMAGE = re.compile(r"(\d+(?:[.,]\d+)?)\s*(?:tỉ|tỷ)\s*đồng|thiệt\s*hại.*?(\d+(?:[.,]\d+)?)\s*(?:tỉ|tỷ)", re.IGNORECASE)

RE_AGENCY = re.compile(r"(Cục\s+Quản\s+lý\s+đê\s+điều.*?PCTT|Ban\s+Chỉ\s+đạo.*?PCTT|Trung\s+tâm\s+Dự\s+báo.*?KTTV|Viện\s+Vật\s+lý\s+Địa\s+cầu|Trung\s+tâm\s+báo\s+tin\s+động\s+đất.*?sóng\s+thần)", re.IGNORECASE)

PROVINCES = [
    # Tên chính thức đầu tiên để return
    "Hà Nội", "TP.HCM", "Thành phố Hồ Chí Minh", "Đà Nẵng", "Huế", "Thừa Thiên Huế",
    "Nghệ An", "Hà Tĩnh", "Quảng Bình", "Quảng Trị", "Quảng Nam", "Quảng Ngãi", 
    "Bình Định", "Phú Yên", "Khánh Hòa", "Ninh Thuận", "Bình Thuận",
    "Gia Lai", "Kon Tum", "Đắk Lắk", "Đắk Nông", "Lâm Đồng", 
    "Lào Cai", "Yên Bái", "Sơn La", "Điện Biên", "Lai Châu",
    "Thanh Hóa", "Quảng Ninh", "Hải Phòng", "Hải Dương", 
    "Bắc Giang", "Bắc Ninh", "Thái Nguyên", "Cao Bằng", "Lạng Sơn",
    "Bình Dương", "Đồng Nai", "Bà Rịa - Vũng Tàu", "Vũng Tàu",
    "Long An", "Tiền Giang", "Bến Tre", "Trà Vinh", "Sóc Trăng", "Cà Mau",
]

def _to_int(num_str: str) -> int:
    s = num_str.replace(".", "").replace(",", "")
    try:
        return int(s)
    except ValueError:
        return 0

def _to_float(num_str: str) -> float:
    s = num_str.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return 0.0

def classify_disaster(text: str) -> str:
    t = text.lower()
    for label, patterns in DISASTER_RULES:
        for p in patterns:
            if re.search(p, t, flags=re.IGNORECASE):
                return label
    return "unknown"

def extract_province(text: str) -> str:
    text_lower = text.lower()
    for prov in PROVINCES:
        prov_lower = prov.lower()
        if prov_lower in text_lower:
            if prov == "Thành phố Hồ Chí Minh":
                return "TP.HCM"
            if prov == "Thừa Thiên Huế":
                return "Huế"
            return prov
    return "unknown"

def extract_impacts(text: str) -> dict:
    deaths = missing = injured = None
    damage = None

    m = RE_DEATHS.search(text)
    if m:
        num_str = m.group(1) or m.group(2) or "0"
        deaths = _to_int(num_str)
        if deaths == 0:
            deaths = None
    
    m = RE_MISSING.search(text)
    if m:
        num_str = m.group(1) or m.group(2) or "0"
        missing = _to_int(num_str)
        if missing == 0:
            missing = None
    
    m = RE_INJURED.search(text)
    if m:
        num_str = m.group(1) or m.group(2) or "0"
        injured = _to_int(num_str)
        if injured == 0:
            injured = None

    m = RE_DAMAGE.search(text)
    if m:
        damage_str = m.group(1) or m.group(2) or "0"
        damage = _to_float(damage_str)
        if damage == 0:
            damage = None

    agency = None
    m = RE_AGENCY.search(text)
    if m:
        agency = m.group(1)

    return {
        "deaths": deaths,
        "missing": missing,
        "injured": injured,
        "damage_billion_vnd": damage,
        "agency": agency,
    }

def extract_event_time(published_at: datetime, text: str) -> datetime | None:
    candidates = []
    for m in re.finditer(r"(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})", text):
        candidates.append(m.group(1))
    for c in candidates[:3]:
        try:
            dt = dtparser.parse(c, dayfirst=True)
            if dt.year == 1900:
                dt = dt.replace(year=published_at.year)
            return dt
        except Exception:
            continue
    return None

def summarize(text: str, max_len: int = 220) -> str:
    # Remove HTML tags
    cleaned = re.sub(r"<[^>]+>", "", text)
    # Normalize whitespace
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    # Limit length
    if len(cleaned) <= max_len:
        return cleaned
    return cleaned[:max_len].rsplit(" ", 1)[0] + "…"
