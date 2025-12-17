import re
from datetime import datetime
from dateutil import parser as dtparser

# Impact keywords for better extraction
IMPACT_KEYWORDS = {
    "deaths": [
        "chết", "tử vong", "tử nạn", "thiệt mạng", "thương vong", 
        "thi thể", "chết đuối", "đuối nước", "ngạt nước", "vùi lấp", "chôn vùi", "mắc kẹt"
    ],
    "missing": [
        "mất tích", "chưa tìm thấy", "mất liên lạc", "không liên lạc được",
        "chưa xác định tung tích", "không rõ tung tích", "bị cuốn trôi",
        "đang tìm kiếm", "cứu nạn", "cứu hộ"
    ],
    "injured": [
        "bị thương", "bị thương nặng", "bị thương nhẹ", "chấn thương",
        "đa chấn thương", "nhập viện", "cấp cứu", "điều trị",
        "chuyển viện", "sơ cứu"
    ],
    "damage": [
        "thiệt hại", "tổn thất", "hư hỏng", "hư hại", "tàn phá",
        "ước tính thiệt hại", "thiệt hại về tài sản", "sập nhà", "đổ sập",
        "tốc mái", "ngập nhà", "cuốn trôi", "sạt lở đường", "đứt đường",
        "chia cắt", "cô lập", "sập cầu", "mất điện", "mất nước", "mất sóng"
    ]
}

# Map common Vietnamese number words to integers (approximate where needed)
NUMBER_WORDS = {
    "không": 0,
    "một": 1, "mốt": 1, "1": 1,
    "hai": 2, "2": 2,
    "ba": 3, "3": 3,
    "bốn": 4, "tư": 4, "4": 4,
    "năm": 5, "5": 5,
    "sáu": 6, "6": 6,
    "bảy": 7, "7": 7,
    "tám": 8, "8": 8,
    "chín": 9, "9": 9,
    "mười": 10, "10": 10,
    "vài": 3,
    "hàng chục": 20,
    "hàng trăm": 200,
}

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

# Build regex patterns from keywords
def _build_impact_patterns():
    patterns = {}
    # build a pattern for numeric words as well as digits
    numword_patterns = [re.escape(k) for k in NUMBER_WORDS.keys()]
    # sort so multi-word tokens come first
    numword_patterns.sort(key=lambda s: -len(s))
    numword_pattern = "|".join(numword_patterns)
    number_group = rf"(\d+|(?:{numword_pattern}))"

    for impact_type, keywords in IMPACT_KEYWORDS.items():
        keyword_patterns = [re.escape(kw) for kw in keywords]
        keyword_pattern = "|".join(keyword_patterns)

        if impact_type in ("deaths", "missing", "injured"):
            patterns[impact_type] = re.compile(
                rf"{number_group}\s*(?:người\s*)?(?:{keyword_pattern})|(?:{keyword_pattern})\s*(?:khoảng\s*)?{number_group}\s*(?:người)?",
                re.IGNORECASE,
            )
        elif impact_type == "damage":
            patterns["damage"] = re.compile(
                rf"(?:{keyword_pattern})\s*(?:khoảng\s*)?(?:ước\s*tính\s*)?{number_group}\s*(?:tỉ|tỷ|triệu)\s*(?:đồng)?|{number_group}\s*(?:tỉ|tỷ|triệu)\s*đồng",
                re.IGNORECASE,
            )

    return patterns

IMPACT_PATTERNS = _build_impact_patterns()

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
    """Extract impact numbers using keyword-based patterns."""
    deaths = missing = injured = None
    damage = None

    m = IMPACT_PATTERNS["deaths"].search(text)
    if m:
        num_str = m.group(1) or m.group(2) or "0"
        deaths = _to_int(num_str)
        if deaths == 0:
            deaths = None
    
    m = IMPACT_PATTERNS["missing"].search(text)
    if m:
        num_str = m.group(1) or m.group(2) or "0"
        missing = _to_int(num_str)
        if missing == 0:
            missing = None
    
    m = IMPACT_PATTERNS["injured"].search(text)
    if m:
        num_str = m.group(1) or m.group(2) or "0"
        injured = _to_int(num_str)
        if injured == 0:
            injured = None

    m = IMPACT_PATTERNS["damage"].search(text)
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
