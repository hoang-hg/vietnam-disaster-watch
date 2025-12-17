import re
import unicodedata
from typing import List
from datetime import datetime
from dateutil import parser as dtparser
from .sources import DISASTER_KEYWORDS as SOURCE_DISASTER_KEYWORDS

# -----------------------------------------------------------------------------
# CONSTANTS & CONFIG
# -----------------------------------------------------------------------------

# Impact keywords
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

# Boilerplate tokens
BOILERPLATE_TOKENS = [
    r"\bvideo\b", r"\bảnh\b", r"\bclip\b", r"\bphóng\s*sự\b", r"\btrực\s*tiếp\b",
    r"\blive\b", r"\bhtv\b", r"\bphoto\b", r"\bupdate\b"
]

NUMBER_WORDS = {
    "không": 0, "một": 1, "mốt": 1, "1": 1, "hai": 2, "2": 2, "ba": 3, "3": 3,
    "bốn": 4, "tư": 4, "4": 4, "năm": 5, "5": 5, "sáu": 6, "6": 6, "bảy": 7, "7": 7,
    "tám": 8, "8": 8, "chín": 9, "9": 9, "mười": 10, "10": 10,
    "vài": 3, "hàng chục": 20, "một trăm": 100, "hai trăm": 200, "ba trăm": 300, 
    "năm trăm": 500, "nghìn": 1000, "một nghìn": 1000,
}

# -----------------------------------------------------------------------------
# 34 PROVINCES MAPPING (NEW SAU SAP NHAP)
# Format: New_Name -> List of Old_Names to match in text
# -----------------------------------------------------------------------------
PROVINCE_MAPPING = {
    "Thủ đô Hà Nội": ["Hà Nội", "Ha Noi", "HN"],
    "Cao Bằng": ["Cao Bằng"],
    "Tuyên Quang": ["Tuyên Quang", "Hà Giang"],
    "Lào Cai": ["Lào Cai", "Yên Bái"],
    "Điện Biên": ["Điện Biên"],
    "Lai Châu": ["Lai Châu"],
    "Sơn La": ["Sơn La"],
    "Thái Nguyên": ["Thái Nguyên", "Bắc Kạn"],
    "Lạng Sơn": ["Lạng Sơn"],
    "Quảng Ninh": ["Quảng Ninh"],
    "Phú Thọ": ["Phú Thọ", "Vĩnh Phúc", "Hòa Bình"],
    "Bắc Ninh": ["Bắc Ninh", "Bắc Giang"],
    "Hải Phòng": ["Hải Phòng", "Hải Dương"],
    "Hưng Yên": ["Hưng Yên", "Thái Bình"],
    "Ninh Bình": ["Ninh Bình", "Hà Nam", "Nam Định"],
    "Thanh Hóa": ["Thanh Hóa"],
    "Nghệ An": ["Nghệ An"],
    "Hà Tĩnh": ["Hà Tĩnh"],
    "Quảng Trị": ["Quảng Trị", "Quảng Bình"],
    "Huế": ["Huế", "Thừa Thiên Huế", "Thừa Thiên - Huế"],
    "Đà Nẵng": ["Đà Nẵng", "Quảng Nam"],
    "Quảng Ngãi": ["Quảng Ngãi", "Kon Tum"],
    "Khánh Hòa": ["Khánh Hòa", "Ninh Thuận"],
    "Gia Lai": ["Gia Lai", "Bình Định"],
    "Đắk Lắk": ["Đắk Lắk", "Phú Yên"],
    "Lâm Đồng": ["Lâm Đồng", "Đắk Nông", "Binh Thuận", "Bình Thuận"],
    "Tây Ninh": ["Tây Ninh", "Long An"],
    "Đồng Nai": ["Đồng Nai", "Bình Phước"],
    "Thành phố Hồ Chí Minh": ["Hồ Chí Minh", "TP.HCM", "TPHCM", "Sài Gòn", "Bà Rịa", "Vũng Tàu", "Bình Dương"],
    "Vĩnh Long": ["Vĩnh Long", "Bến Tre", "Trà Vinh"],
    "Đồng Tháp": ["Đồng Tháp", "Tiền Giang"],
    "An Giang": ["An Giang", "Kiên Giang"],
    "Cần Thơ": ["Cần Thơ", "Sóc Trăng", "Hậu Giang"],
    "Cà Mau": ["Cà Mau", "Bạc Liêu"],
}

# List of valid (new) province names
PROVINCES = list(PROVINCE_MAPPING.keys())

PROVINCE_REGIONS = [
    "Biển Đông", "Nam Trung Bộ", "Bắc Bộ", "Miền Trung", "Miền Bắc", "Miền Nam", "Tây Nguyên", "Trung Bộ", "Nam Bộ"
]

# -----------------------------------------------------------------------------
# DISASTER RULES & PATTERNS
# -----------------------------------------------------------------------------

DISASTER_RULES = [
  # 1) Bão & áp thấp nhiệt đới
  ("storm", [
    # Original
    r"(?<!\w)bão(?!\w)", r"bão\s*số\s*\d+",
    r"siêu\s*bão", r"hoàn\s*lưu\s*bão", r"tâm\s*bão",
    r"đổ\s*bộ", r"đi\s*vào\s*biển\s*đông", r"tiến\s*vào\s*biển\s*đông",
    r"suy\s*yếu", r"mạnh\s*lên", r"tăng\s*cấp",
    r"áp\s*thấp\s*nhiệt\s*đới", r"\bATNĐ\b", r"vùng\s*áp\s*thấp",
    r"xoáy\s*thuận\s*nhiệt\s*đới", r"nhiễu\s*động\s*nhiệt\s*đới",
    r"gió\s*mạnh\s*cấp\s*\d+", r"gió\s*giật\s*cấp\s*\d+",
    r"cấp\s*độ\s*rủi\s*ro\s*thiên\s*tai", r"biển\s*động",
    # User added
    r"áp\s*suất\s*trung\s*tâm", r"vùng\s*gió\s*mạnh", r"gió\s*giật", r"hoàn\s*lưu"
  ]),

  # 2) Mưa lớn & lũ lụt (kèm ngập, lũ quét, sạt lở/sụt lún do mưa lũ/dòng chảy)
  ("flood_landslide", [
    # Mưa lớn (Original + User)
    r"mưa\s*lớn", r"mưa\s*to", r"mưa\s*rất\s*to", r"mưa\s*cực\s*lớn",
    r"mưa\s*đặc\s*biệt\s*lớn", r"mưa\s*diện\s*rộng", r"mưa\s*kéo\s*dài",
    r"mưa\s*kỷ\s*lục", r"mưa\s*cực\s*đoan", r"mưa\s*như\s*trút",
    r"lượng\s*mưa", r"mm/24\s*giờ",
    # Cơ chế (Original)
    r"dải\s*hội\s*tụ\s*nhiệt\s*đới", r"rãnh\s*áp\s*thấp", r"gió\s*mùa",

    # Lũ / Ngập (Original + User)
    r"lũ(?!\s*lượt)", r"lụt", r"lũ\s*lụt",
    r"ngập(?!\s*đầu\s*tư)", r"ngập\s*lụt", r"ngập\s*úng", r"ngập\s*sâu",
    r"ngập\s*cục\s*bộ",
    r"nước\s*lên\s*nhanh", r"mực\s*nước\s*dâng", r"đỉnh\s*lũ",
    r"báo\s*động\s*(?:1|2|3|I|II|III)", r"vượt\s*báo\s*động",
    r"lũ\s*lịch\s*sử", r"lũ\s*bất\s*thường", r"lũ\s*đặc\s*biệt\s*lớn",

    # Lũ quét / Lũ ống
    r"lũ\s*quét", r"lũ\s*ống", r"nước\s*lũ\s*cuốn\s*trôi",

    # Sự cố đê/đập/xả lũ
    r"vỡ\s*đê", r"vỡ\s*kè", r"tràn\s*đê", r"tràn\s*bờ",
    r"vỡ\s*đập", r"sự\s*cố\s*đập", r"sự\s*cố\s*hồ\s*chứa",
    r"xả\s*lũ", r"xả\s*tràn", r"mở\s*cửa\s*xả", r"tràn\s*đập",

    # Sạt lở / Sụt lún (Original + User)
    r"sạt\s*lở", r"sạt\s*lở\s*đất", r"lở\s*đất", r"trượt\s*đất", r"trượt\s*lở",
    r"sạt\s*lở\s*bờ\s*sông", r"sạt\s*lở\s*bờ\s*biển", r"sạt\s*taluy",
    r"sụt\s*lún", r"hố\s*tử\s*thần", r"hố\s*sụt", r"nứt\s*đất"
  ]),

  # 3) Nắng nóng, hạn hán, xâm nhập mặn (kèm sạt lở/sụt lún do hạn)
  ("heat_drought", [
    # Nắng nóng
    r"nắng\s*nóng", r"nắng\s*nóng\s*gay\s*gắt", r"nắng\s*nóng\s*đặc\s*biệt",
    r"nhiệt\s*độ\s*(?:cao|tăng|kỷ\s*lục)", r"oi\s*bức", r"nhiệt\s*độ\s*không\s*khí\s*cao\s*nhất",
    # Hạn hán / Thiếu nước
    r"hạn\s*hán", r"khô\s*hạn", r"thiếu\s*nước", r"cạn\s*kiệt",
    r"khát\s*nước", r"nứt\s*nẻ", r"đất\s*khô\s*nứt",
    r"mực\s*nước\s*hồ\s*chứa\s*(?:giảm|xuống\s*thấp)", r"cạn\s*hồ",
    # Xâm nhập mặn
    r"xâm\s*nhập\s*mặn", r"nhiễm\s*mặn", r"mặn\s*xâm\s*nhập",
    r"độ\s*mặn", r"ranh\s*mặn", r"nước\s*mặn\s*xâm\s*nhập",
    r"hạn\s*mặn",
    # User added units/terms for salt
    r"(?<!\w)ppt(?!\w)", r"(?<!\w)g/l(?!\w)",
    # Hệ quả địa chất do hạn
    r"sạt\s*lở\s*do\s*hạn", r"sụt\s*lún\s*do\s*hạn"
  ]),

  # 4) Gió mạnh & sương mù (biển + đất liền)
  ("wind_fog", [
    # Gió mạnh
    r"gió\s*mạnh", r"gió\s*giật", r"gió\s*giật\s*mạnh",
    r"gió\s*cấp\s*\d+", r"gió\s*giật\s*cấp\s*\d+",
    r"biển\s*động", r"biển\s*động\s*mạnh", r"sóng\s*lớn", r"sóng\s*cao",
    # Sương mù
    r"sương\s*mù", r"sương\s*mù\s*dày\s*đặc", r"mù\s*dày\s*đặc",
    r"tầm\s*nhìn\s*hạn\s*chế", r"giảm\s*tầm\s*nhìn"
  ]),

  # 5) Nước dâng (ven bờ & đảo)
  ("storm_surge", [
    r"nước\s*dâng", r"nước\s*dâng\s*do\s*bão", r"nước\s*biển\s*dâng",
    r"mực\s*nước\s*biển\s*dâng", r"dâng\s*cao", r"đỉnh\s*triều",
    r"triều\s*cường", r"ngập\s*do\s*triều", r"sóng\s*lớn", r"biển\s*động",
    r"xâm\s*thực\s*bờ\s*biển", r"xói\s*lở\s*bờ\s*biển"
  ]),

  # 6) Hiện tượng thời tiết cực đoan khác: lốc, sét, mưa đá, rét hại, sương muối
  ("extreme_other", [
    # Lốc
    r"lốc(?!\s*xoáy\s*thị\s*trường)", r"dông\s*lốc", r"giông\s*lốc",
    r"lốc\s*xoáy", r"tố\s*lốc", r"vòi\s*rồng",
    # Sét
    r"sét", r"sét\s*đánh", r"giông\s*sét", r"dông\s*sét",
    # Mưa đá
    r"mưa\s*đá", r"hạt\s*băng", r"mưa\s*rào\s*kèm\s*dông",
    # Rét
    r"rét\s*hại", r"rét\s*đậm", r"không\s*khí\s*lạnh", r"không\s*khí\s*lạnh\s*tăng\s*cường",
    r"băng\s*giá",
    # Sương muối
    r"sương\s*muối"
  ]),

  # 7) Cháy rừng tự nhiên
  ("wildfire", [
    r"cháy\s*rừng", r"cháy\s*rừng\s*tự\s*nhiên", r"cháy\s*thực\s*bì",
    r"bùng\s*phát\s*cháy", r"đám\s*cháy", r"nguy\s*cơ\s*cháy\s*rừng",
    r"cấp\s*dự\s*báo\s*cháy\s*rừng", r"cấp\s*cháy\s*rừng",
    r"PCCCR", r"điểm\s*nóng", r"khói\s*mù", r"thiêu\s*rụi"
  ]),

  # 8-10) Động đất & sóng thần
  ("quake_tsunami", [
    # Động đất
    r"động\s*đất", r"rung\s*chấn", r"dư\s*chấn", r"tâm\s*chấn",
    r"đứt\s*gãy\s*địa\s*chất", # stricter than just "đứt gãy"
    r"nứt\s*đất\s*do\s*động\s*đất", # stricter
    r"(?:độ\s*lớn|cường\s*độ)\s*\d+(?:[.,]\d+)?\s*richter",
    r"\d+(?:[.,]\d+)?\s*(?:độ\s*richter|richter)",
    r"\bM\s*\d+(?:[.,]\d+)?\b", r"(?:magnitude|mag)\s*\d+(?:[.,]\d+)?",
    r"\bM\s*=?\s*\d+(?:[.,]\d+)?", # User specific
    r"chấn\s*tiêu", r"độ\s*sâu\s*chấn\s*tiêu",
    # Sóng thần
    r"sóng\s*thần", r"cảnh\s*báo\s*sóng\s*thần", r"báo\s*động\s*sóng\s*thần", r"\btsunami\b"
  ]),
]

DISASTER_CONTEXT = [
  r"cảnh\s*báo", r"khuyến\s*cáo", r"cảnh\s*báo\s*sớm",
  r"cấp\s*độ\s*rủi\s*ro", r"rủi\s*ro\s*thiên\s*tai",
  r"sơ\s*tán", r"di\s*dời", r"cứu\s*hộ", r"cứu\s*nạn",
  r"thiệt\s*hại", r"thương\s*vong", r"mất\s*tích", r"bị\s*thương",
  r"chia\s*cắt", r"cô\s*lập", r"mất\s*điện", r"mất\s*liên\s*lạc"
]

DISASTER_NEGATIVE = [
  # Bão
  r"bão\s*giá", r"cơn\s*bão\s*(?:dư\s*luận|truyền\s*thông|tin\s*giả|mạng)(?!\w)",
  r"bão\s*sale", r"bão\s*like", r"bão\s*scandal", r"cơn\s*bão\s*tài\s*chính",
  r"bão\s*sao\s*kê",
  
  # Động đất / Lũ
  r"rung\s*chấn\s*(?:dư\s*luận|thị\s*trường)(?!\w)",
  r"chấn\s*động\s*(?:dư\s*luận|showbiz|làng\s*giải\s*trí|mạng)(?!\w)",
  r"(?<!\w)động\s*đất\s*(?:thị\s*trường|giá|chứng\s*khoán|bất\s*động\s*sản)(?!\w)",
  r"lũ\s*(?:lượt|fan|like|view|đơn\s*hàng)(?!\w)",
  r"cơn\s*địa\s*chấn\s*sân\s*cỏ", r"cơn\s*lốc\s*(?:đường\s*biên|màu\s*cam)",
  
  # General Metaphors
  r"bão\s*(?:chấn\s*thương|bệnh\s*tật|sa\s*thải)(?!\w)",
  r"làn\s*sóng\s*(?:covid|dịch\s*bệnh|đầu\s*tư|nhập\s*cư|tẩy\s*chay)(?!\w)",
  r"cơn\s*sốt\s*(?:đất|giá|vé)(?!\w)",
  r"đóng\s*băng\s*(?:thị\s*trường|tài\s*khoản|quan\s*hệ)(?!\w)",
  r"ngập\s*(?:tràn|trong)\s*(?:hạnh\s*phúc|tiếng\s*cười|quà|bình\s*luận)(?!\w)",

  # Non-disaster Context (Construction, Policy, Traffic)
  r"(?<!\w)quy\s*hoạch(?!\w)", r"(?<!\w)phê\s*duyệt(?!\w)",
  r"(?<!\w)khởi\s*công(?!\w)", r"(?<!\w)khánh\s*thành(?!\w)",
  r"(?<!\w)nghiệm\s*thu(?!\w)", r"(?<!\w)đấu\s*thầu(?!\w)",
  r"(?<!\w)tai\s*nạn\s*giao\s*thông(?!\w)", r"(?<!\w)va\s*chạm\s*xe(?!\w)",
  r"(?<!\w)xe\s*tải(?!\w)", r"(?<!\w)xe\s*container(?!\w)", r"(?<!\w)xe\s*khách(?!\w)",
  r"(?<!\w)đường\s*cao\s*tốc(?!\w)"
]

DISASTER_CONTEXT_PATTERNS = [re.compile(p, re.IGNORECASE) for p in DISASTER_CONTEXT]
DISASTER_NEGATIVE_PATTERNS = [re.compile(p, re.IGNORECASE) for p in DISASTER_NEGATIVE]
POLLUTION_TERMS = [r"ô\s*nhiễm", r"AQI", r"PM2\.5", r"bụi\s*mịn"]

# build regex patterns function
def _build_impact_patterns():
    patterns = {}
    numword_patterns = [re.escape(k) for k in NUMBER_WORDS.keys()]
    numword_patterns.sort(key=lambda s: -len(s))
    numword_pattern = "|".join(numword_patterns)
    number_group = rf"(\d+|(?:{numword_pattern}))"

    for impact_type, keywords in IMPACT_KEYWORDS.items():
        keyword_patterns = [re.escape(kw) for kw in keywords]
        keyword_pattern = "|".join(keyword_patterns)
        if impact_type in ("deaths", "missing", "injured"):
            patterns[impact_type] = re.compile(
               rf"{number_group}\s*(?:người\s*)?(?:{keyword_pattern})|(?:{keyword_pattern})\s*(?:khoảng\s*)?{number_group}\s*(?:người)?",
               re.IGNORECASE
            )
        elif impact_type == "damage":
            patterns["damage"] = re.compile(
                rf"(?:{keyword_pattern})\s*(?:khoảng\s*)?(?:ước\s*tính\s*)?{number_group}\s*(?:tỉ|tỷ|triệu)\s*(?:đồng)?|{number_group}\s*(?:tỉ|tỷ|triệu)\s*đồng",
                re.IGNORECASE
            )
    return patterns

IMPACT_PATTERNS = _build_impact_patterns()
RE_AGENCY = re.compile(r"(Tổng\s+cục\s+KTTV|Cục\s+Quản\s+lý\s+đê\s+điều|Ban\s+Chỉ\s+đạo.*?PCTT|Trung\s+tâm\s+Dự\s+báo.*?KTTV|Viện\s+Vật\s+lý\s+Địa\s+cầu|Tổng\s+cục\s+Lâm\s+nghiệp|Trung\s+tâm\s+báo\s+tin\s+động\s+đất)", re.IGNORECASE)

WEIGHT_RULE = 3.0
WEIGHT_IMPACT = 3.5
WEIGHT_AGENCY = 2.0
WEIGHT_SOURCE = 1.0
WEIGHT_PROVINCE = 0.5


def _to_int(num_str: str) -> int:
    if not num_str: return 0
    s = str(num_str).strip().lower()
    if re.match(r"^\d+$", s): return int(s)
    if s in NUMBER_WORDS: return int(NUMBER_WORDS[s])
    s2 = s.replace(".", "").replace(",", "")
    if s2.isdigit(): return int(s2)
    return 0

def _to_float(num_str: str) -> float:
    if not num_str: return 0.0
    s = str(num_str).strip().lower()
    if s in NUMBER_WORDS: return float(NUMBER_WORDS[s])
    try:
        if "," in s and "." in s:
            return float(s.replace(".", "").replace(",", "."))
        if "," in s: return float(s.replace(",", "."))
        if "." in s:
            parts = s.rsplit(".", 1)
            if len(parts) == 2 and len(parts[1]) == 3:
                return float(s.replace(".", ""))
            return float(s)
        return float(s)
    except: return 0.0

def _sanitize_text_for_match(s: str) -> str:
    if not s: return s
    out = s
    for tok in BOILERPLATE_TOKENS:
        out = re.sub(tok, " ", out, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", out).strip()

def _strip_accents(s: str) -> str:
    if not s: return s
    nkfd = unicodedata.normalize("NFD", s)
    return "".join([c for c in nkfd if not unicodedata.combining(c)])

# -----------------------------------------------------------------------------
# CORE LOGIC
# -----------------------------------------------------------------------------

def extract_province(text: str) -> str:
    """Identify which of the 34 NEW provinces the text refers to.
    Matches against all components of a new province.
    """
    text_lower = text.lower()
    
    # Priority check: specific phrases that map to new units?
    # Iterate through NEW provinces
    for new_prov, components in PROVINCE_MAPPING.items():
        # strict match for components
        for comp in components:
            if comp.lower() in text_lower:
                return new_prov
    
    # Check regions
    for region in PROVINCE_REGIONS:
        if region.lower() in text_lower:
            return region
            
    return "unknown"

def extract_disaster_metrics(text: str) -> dict:
    metrics = {}
    t = text
    # Rain
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*mm", t)
    if m: metrics["rainfall_mm"] = _to_float(m.group(1))
    
    # Temp
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*°\s*C", t, re.IGNORECASE)
    if m: metrics["temperature_c"] = _to_float(m.group(1))
    
    # Salt
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*‰", t)
    if m: metrics["salinity_per_mille"] = _to_float(m.group(1))

    # Wind
    m = re.search(r"cấp\s*(\d{1,2})", t)
    if m: metrics["wind_level"] = int(m.group(1))
    m = re.search(r"giật\s*cấp\s*(\d{1,2})", t)
    if m: metrics["wind_gust"] = int(m.group(1))
    
    # Quake
    m = re.search(r"M\s*=?\s*(\d+(?:[.,]\d+)?)", t, re.IGNORECASE)
    if m: metrics["earthquake_magnitude"] = _to_float(m.group(1))
    else:
        m2 = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:độ|richter)", t, re.IGNORECASE)
        if m2 and ("động đất" in t.lower() or "rung chấn" in t.lower()):
            metrics["earthquake_magnitude"] = _to_float(m2.group(1))
            
    return {k: v for k, v in metrics.items() if v is not None}

def compute_disaster_signals(text: str) -> dict:
    t_raw = (text or "").strip()
    t_sanit = _sanitize_text_for_match(t_raw)
    t = re.sub(r"\s+", " ", t_sanit).lower()
    t_unaccent = _strip_accents(t)

    rule_matches = []
    for label, patterns in DISASTER_RULES:
        matched = False
        for p in (patterns if isinstance(patterns, list) else []): # fix robust
            if re.search(p, t, flags=re.IGNORECASE) or re.search(p, t_unaccent, flags=re.IGNORECASE):
                matched = True
                break
        if matched:
            rule_matches.append(label)

    hazard_score = len(set(rule_matches))
    rule_score = WEIGHT_RULE if hazard_score else 0.0

    impact_hits = []
    for k, klist in IMPACT_KEYWORDS.items():
        for kw in klist:
            if kw.lower() in t:
                impact_hits.append((k, kw))
                break
    impact_score = WEIGHT_IMPACT if impact_hits else 0.0

    agency_match = bool(RE_AGENCY.search(t))
    agency_score = WEIGHT_AGENCY if agency_match else 0.0

    prov = extract_province(t)
    province_found = prov != "unknown"
    province_score = 0.5 if province_found else 0.0

    # Source keywords match
    ambiguous = {"cảnh báo", "dự báo", "bản tin", "khuyến cáo"}
    non_ambiguous_hits = []
    source_hits = []
    for kw in SOURCE_DISASTER_KEYWORDS:
        kl = kw.lower()
        if kl in t:
            source_hits.append(kl)
            if kl not in ambiguous:
                non_ambiguous_hits.append(kl)
    source_score = float(len(non_ambiguous_hits)) * WEIGHT_SOURCE

    score = rule_score + impact_score + agency_score + source_score + province_score

    # context matches (include pollution terms)
    context_hits = []
    for p in DISASTER_CONTEXT_PATTERNS:
        if p.search(t): context_hits.append(p.pattern)
    for pt in POLLUTION_TERMS:
        if re.search(pt, t, flags=re.IGNORECASE): context_hits.append(pt)
    context_score = len(context_hits)

    # negative patterns
    negative_hit = False
    for p in DISASTER_NEGATIVE_PATTERNS:
        if p.search(t): negative_hit = True; break
    
    # Extra check: if heavily sports related, assume negative unless very strong disaster rules
    SPORTS_TERMS = ["bóng đá", "v-league", "ngoại hạng anh", "cầu thủ", "ghi bàn"]
    if not negative_hit:
        sc = sum(1 for w in SPORTS_TERMS if w in t)
        if sc >= 2 and hazard_score < 2:
            if "địa chấn" in t or "cơn lốc" in t: negative_hit = True

    metrics = extract_disaster_metrics(t)

    return {
        "rule_matches": rule_matches,
        "impact_hits": impact_hits,
        "agency": agency_match,
        "province": prov if province_found else None,
        "score": score,
        "hazard_score": hazard_score,
        "context_score": context_score,
        "negative_hit": negative_hit,
        "metrics": metrics
    }

def contains_disaster_keywords(text: str) -> bool:
    sig = compute_disaster_signals(text)
    if sig["negative_hit"]: return False
    if sig["hazard_score"] >= 1 and sig["context_score"] >= 1: return True
    if "quake_tsunami" in sig["rule_matches"]: return True
    return sig["score"] >= 3.0

def diagnose(text: str) -> dict:
    sig = compute_disaster_signals(text)
    return {"score": sig["score"], "signals": sig}

def title_contains_disaster_keyword(title: str) -> bool:
    t = (title or "").lower()
    for kw in SOURCE_DISASTER_KEYWORDS:
        if kw.lower() in t: return True
    return False

def extract_impacts(text: str) -> dict:
    # Use global IMPACT_PATTERNS
    deaths = missing = injured = damage = None
    
    m = IMPACT_PATTERNS["deaths"].search(text)
    if m: deaths = _to_int(m.group(1) or m.group(2))
    
    m = IMPACT_PATTERNS["missing"].search(text)
    if m: missing = _to_int(m.group(1) or m.group(2))

    m = IMPACT_PATTERNS["injured"].search(text)
    if m: injured = _to_int(m.group(1) or m.group(2))

    m = IMPACT_PATTERNS["damage"].search(text)
    if m: damage = _to_float(m.group(1) or m.group(2))

    agency = None
    m = RE_AGENCY.search(text)
    if m: agency = m.group(1)

    metrics = extract_disaster_metrics(text)
    return {
        "deaths": deaths, "missing": missing, "injured": injured,
        "damage_billion_vnd": damage,
        "agency": agency,
        **metrics
    }

def extract_event_time(published_at: datetime, text: str) -> datetime | None:
    candidates = []
    for m in re.finditer(r"(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})", text):
        candidates.append(m.group(1))
    for c in candidates[:3]:
        try:
            dt = dtparser.parse(c, dayfirst=True)
            if dt.year == 1900: dt = dt.replace(year=published_at.year)
            return dt
        except: continue
    return None

def summarize(text: str, max_len: int = 220) -> str:
    cleaned = re.sub(r"<[^>]+>", "", text)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if len(cleaned) <= max_len: return cleaned
    return cleaned[:max_len].rsplit(" ", 1)[0] + "…"

def extract_risk_level(text: str, disaster_type: str) -> int:
    """Determine risk level (1-5) based on text rules or default mappings.
    Updated with logic from Decision 18/2021/QD-TTg for Storms/Tropical Depressions.
    """
    t = text.lower()
    
    # 1. Explicit mention in text (High Priority)
    # Patterns: "rủi ro thiên tai cấp 3", "rủi ro cấp 4", "báo động 3"
    
    levels = []
    
    # "rủi ro thiên tai cấp X"
    m = re.search(r"rủi\s*ro\s*(?:thiên\s*tai\s*)?(?:cấp|mức|độ)\s*(\d)", t)
    if m:
        try:
            val = int(m.group(1))
            if 1 <= val <= 5:
                levels.append(val)
        except: pass

    # "báo động X" (often maps to flood risk)
    m2 = re.search(r"báo\s*động\s*(\d|I|II|III)", t)
    if m2:
        val_str = m2.group(1).upper()
        if val_str == "1" or val_str == "I": levels.append(1)
        elif val_str == "2" or val_str == "II": levels.append(2)
        elif val_str == "3" or val_str == "III": levels.append(3)

    if levels:
        return max(levels)

    # 2. Detailed Rules based on Disaster Type

    # === STORM / TROPICAL DEPRESSION (Bão / ATNĐ) ===
    if disaster_type == "storm":
        # Helper to extract max level mentioned
        # Matches: "cấp 12", "cấp 8-9", "mạnh cấp 10"
        lv_matches = re.findall(r"cấp\s*(\d{1,2})", t)
        parsed_lvs = []
        for v in lv_matches:
            try:
                parsed_lvs.append(int(v))
            except: pass
        
        max_lv = max(parsed_lvs) if parsed_lvs else 0
        
        # Check for "ATNĐ" or "Áp thấp nhiệt đới" implies base level if no explicit level
        is_atnd = "áp thấp nhiệt đới" in t or "atnđ" in t
        if is_atnd and max_lv == 0:
            max_lv = 7 # Treat as < 8

        # Check for Super Storm explicitly
        if "siêu bão" in t:
            max_lv = max(max_lv, 16)

        # Region Detection
        regions = set()
        
        # Sea
        if re.search(r"biển\s*đông|trường\s*sa|hoàng\s*sa", t):
            regions.add("sea")
        # Coastal
        if re.search(r"ven\s*bờ|vùng\s*biển|cửa\s*biển", t):
            regions.add("coastal")
        # Land - South (Nam Bộ)
        if re.search(r"nam\s*bộ|miền\s*tây|đồng\s*bằng\s*sông\s*cửu\s*long|cà\s*mau|kiên\s*giang|bạc\s*liêu|sóc\s*trăng|trà\s*vinh|bến\s*tre|tiền\s*giang|vĩnh\s*long|cần\s*thơ|hậu\s*giang|đồng\s*tháp|an\s*giang|long\s*an|bình\s*phước|bình\s*dương|đồng\s*nai|tây\s*ninh|bà\s*rịa|\bvũng\s*tàu\b|tp\.hcm|hồ\s*chí\s*minh", t):
            regions.add("south")
        # Land - Highlands (Tây Nguyên)
        if re.search(r"tây\s*nguyên|kon\s*tum|gia\s*lai|đắk\s*lắk|đắk\s*nông|lâm\s*đồng", t):
            regions.add("highlands")
        # Land - S.Central (Nam Trung Bộ)
        if re.search(r"nam\s*trung\s*bộ|đà\s*nẵng|quảng\s*nam|quảng\s*ngãi|bình\s*định|phú\s*yên|khánh\s*hòa|ninh\s*thuận|bình\s*thuận", t):
            regions.add("s_central")
        # Land - C.Central (Trung Trung Bộ - loosely defined or overlapping) / N.Central (Bắc Trung Bộ)
        # Grouping Central for simplicity if needed, but rules distinguish specific sets.
        if re.search(r"bắc\s*trung\s*bộ|thanh\s*hóa|nghệ\s*an|hà\s*tĩnh|quảng\s*bình|quảng\s*trị|thừa\s*thiên\s*huế", t):
            regions.add("n_central")
        # Land - North (Northern Delta, NE, NW, Viet Bac)
        if re.search(r"bắc\s*bộ|đồng\s*bằng\s*sông\s*hồng|hà\s*nội|hải\s*phòng|quảng\s*ninh|hải\s*dương|hưng\s*yên|thái\s*bình|hà\s*nam|nam\s*định|ninh\s*bình|vĩnh\s*phúc|bắc\s*ninh", t):
            regions.add("delta_north")
        if re.search(r"đông\s*bắc|hà\s*giang|cao\s*bằng|bắc\s*kạn|lạng\s*sơn|tuyên\s*quang|thái\s*nguyên|phú\s*thọ|bắc\s*giang", t):
            regions.add("ne_north")
        if re.search(r"tây\s*bắc|việt\s*bắc|hòa\s*bình|sơn\s*la|điện\s*biên|lai\s*châu|lào\s*cai|yên\s*bái", t):
            regions.add("nw_north")

        # Global flag for "land" if specific regions not caught but "đất liền" mentioned
        any_land = len(regions.difference({"sea", "coastal"})) > 0 or "đất liền" in t

        # --- LEVEL 5 RULES ---
        # 1. Storm Lv 12-13 on Land South
        if (12 <= max_lv <= 13) and "south" in regions:
            return 5
        # 2. Storm Lv 14-15 on Land NW, Viet Bac, S.Central, Highlands, South
        if (14 <= max_lv <= 15) and ({"nw_north", "s_central", "highlands", "south"}.intersection(regions)):
            return 5
        # 3. Super Storm >= Lv 16 on Coastal, Land (All)
        if max_lv >= 16 and (any_land or "coastal" in regions):
            return 5

        # --- LEVEL 4 RULES ---
        # 1. Storm Lv 10-11 on Land South
        if (10 <= max_lv <= 11) and "south" in regions:
            return 4
        # 2. Storm Lv 12-13 on Coastal, Land NW, Viet Bac, NE, RR Delta, NC, CC, SC, Highlands
        # (Basically Land NOT South)
        target_regions_lv4_2 = {"coastal", "nw_north", "ne_north", "delta_north", "n_central", "s_central", "highlands"}
        if (12 <= max_lv <= 13) and (target_regions_lv4_2.intersection(regions) or (any_land and "south" not in regions)):
            return 4
        # 3. Storm Lv 14-15 on Coastal, Land NE, RR Delta, NC, CC (subset of North/Central)
        target_regions_lv4_3 = {"coastal", "ne_north", "delta_north", "n_central"}
        if (14 <= max_lv <= 15) and (target_regions_lv4_3.intersection(regions)):
            return 4
        # 4. Storm >= Lv 14 on East Sea
        if max_lv >= 14 and "sea" in regions:
            return 4

        # --- LEVEL 3 RULES (Default for Storm/ATNĐ) ---
        # Technically "ATNĐ, Storm Lv 8-9" anywhere, Storm Lv 10-11 except South, Storm Lv 12-13 Sea only.
        # But since we check 5 and 4 first, anything else falling through is likely 3 if it's a storm.
        
        # Explicit checks for upgrading FROM lower levels (if default was 1, but storms start at 3 per reg):
        # 1. ATNĐ, Storm Lv 8-9 (Anywhere) -> 3
        # 2. Storm Lv 10-11 (Anywhere NOT South, i.e. Sea, Coastal, North/Central/Highlands) -> 3
        # 3. Storm Lv 12-13 (East Sea) -> 3
        
        # So essentially, if it's a storm/ATNĐ, the regulatory minimum is Level 3 (except maybe weak lows, but "Áp thấp nhiệt đới" starts at 3).
        return 3

    # === OTHER DISASTERS (Existing Logic) ===

    # Mưa lớn / Lũ lụt: cấp 1-4
    if disaster_type == "flood_landslide":
        if "lũ quét" in t or "sạt lở" in t: return 3 # Flash floods are high risk
        if "lịch sử" in t or "kỷ lục" in t: return 4
        if "báo động 3" in t or "báo động III" in t: return 3
        return 1 # Default rain/flood starts at 1

    # Nắng nóng / Hạn hán: cấp 1
    if disaster_type == "heat_drought":
        if "đặc biệt gay gắt" in t: return 3
        if "gay gắt" in t: return 2
        return 1

    # Lốc, sét, mưa đá/khác: cấp 1-2
    if disaster_type in ("wind_fog", "extreme_other"):
        if "diện rộng" in t or "thiệt hại nặng" in t: return 2
        return 1
    
    # Nước dâng
    if disaster_type == "storm_surge":
        if "nghiêm trọng" in t or "cao kỷ lục" in t: return 3
        return 1
        
    # Động đất / Sóng thần: 
    if disaster_type == "quake_tsunami":
        if "sóng thần" in t: return 5
        # > 6.5 -> risk high (heuristic)
        if re.search(r"(?:[6-9]\.\d|10\.)\s*độ", t):
            return 3
        return 1

    # Cháy rừng
    if disaster_type == "wildfire":
        if "cấp 5" in t or "cực kỳ nguy hiểm" in t: return 5
        if "cấp 4" in t or "nguy hiểm" in t: return 4
        return 1

    return 1 # Default lowest risk
