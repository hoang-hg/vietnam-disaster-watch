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
  r"rung\s*chấn\s*(?:dư\s*luận|thị\s*trường|sân\s*cỏ)(?!\w)",
  r"chấn\s*động\s*(?:dư\s*luận|showbiz|làng\s*giải\s*trí|mạng)(?!\w)",
  r"(?<!\w)động\s*đất\s*(?:thị\s*trường|giá|chứng\s*khoán|bất\s*động\s*sản)(?!\w)",
  r"lũ\s*(?:lượt|fan|like|view|đơn\s*hàng|người\s*về)(?!\w)",
  r"cơn\s*địa\s*chấn", r"cơn\s*lốc\s*(?:đường\s*biên|màu\s*cam|sân\s*cỏ)",
  
  # General Metaphors
  r"bão\s*(?:chấn\s*thương|bệnh\s*tật|sa\s*thải)(?!\w)",
  r"làn\s*sóng\s*(?:covid|dịch\s*bệnh|đầu\s*tư|nhập\s*cư|tẩy\s*chay)(?!\w)",
  r"cơn\s*sốt\s*(?:đất|giá|vé)(?!\w)",
  r"đóng\s*băng\s*(?:thị\s*trường|tài\s*khoản|quan\s*hệ)(?!\w)",
  r"ngập\s*(?:tràn|trong)\s*(?:hạnh\s*phúc|tiếng\s*cười|quà|bình\s*luận|sắc\s*màu)(?!\w)",

  # Non-disaster Context (Construction, Policy, Traffic, Science, Agri)
  r"(?<!\w)quy\s*hoạch(?!\w)", r"(?<!\w)phê\s*duyệt(?!\w)", r"(?<!\w)dự\s*án(?!\w)",
  r"khởi\s*công", r"khánh\s*thành", r"nghiệm\s*thu", r"đấu\s*thầu",
  r"bãi\s*đỗ\s*xe", r"biệt\s*thự", r"chung\s*cư", r"khu\s*đô\s*thị",
  r"tai\s*nạn\s*giao\s*thông", r"va\s*chạm\s*xe", r"xe\s*tải", r"xe\s*container", r"xe\s*khách",
  r"đường\s*cao\s*tốc", r"ùn\s*tắc", 
  r"ứng\s*dụng\s*ai", r"trí\s*tuệ\s*nhân\s*tạo", r"công\s*nghệ", r"chuyển\s*đổi\s*số",
  r"hội\s*thảo", r"hội\s*nghị", r"diễn\s*đàn", r"nghiên\s*cứu",
  # Agricultural / Seasonal (without disaster warning context)
  r"vụ\s*tết", r"hoa\s*cúc", r"thối\s*rễ", r"được\s*mùa", r"mất\s*mùa", 
  r"giá\s*nông\s*sản", r"xuất\s*khẩu",
  # Post-disaster / Charity (Recovery actions, not warnings)
  r"xây\s*dựng\s*nhà\s*cho", r"trao\s*tặng", r"quyên\s*góp", r"ủng\s*hộ",
  r"khắc\s*phục\s*hậu\s*quả", r"thăm\s*hỏi", r"chia\s*sẻ\s*khó\s*khăn"
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
    
    # Water Level / Surge (m)
    m = re.search(r"(?:mực\s*nước|nước\s*dâng|độ\s*cao).*?(\d+(?:[.,]\d+)?)\s*m", t)
    if m: metrics["water_level_m"] = _to_float(m.group(1))
    
    # Duration (days)
    m = re.search(r"(?:trong|kéo\s*dài|đợt)\s*(?:khoảng\s*)?(\d+)\s*ngày", t)
    if m: metrics["duration_days"] = _to_float(m.group(1))

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

def extract_risk_level(text: str, disaster_type: str, title: str = "") -> int:
    """Determine risk level (1-5).
    Priority:
    1. Direct mention in TITLE (High confidence).
    2. Direct mention in TEXT.
    3. Inference based on disaster type & keywords.
    """
    # Quick fix: allow search in combined text if needed, but let's be explicit
    # Search in Title first
    if title:
        t_title = title.lower()
        # "rủi ro ... cấp X" in title
        m_title = re.search(r"rủi\s*ro\s*(?:thiên\s*tai\s*)?(?:cấp|mức|độ)\s*(\d)", t_title)
        if m_title:
             try:
                val = int(m_title.group(1))
                if 1 <= val <= 5: return val
             except: pass
        
        # "báo động 3" in title
        m2_title = re.search(r"báo\s*động\s*(\d|I|II|III)", t_title)
        if m2_title:
            val_str = m2_title.group(1).upper()
            if val_str in ("3", "III"): return 3 # High priority warnings
            if val_str in ("2", "II"): return 2

    t = text.lower()
    levels = []
    
    # "rủi ro thiên tai cấp X" in text
    m = re.search(r"rủi\s*ro\s*(?:thiên\s*tai\s*)?(?:cấp|mức|độ)\s*(\d)", t)
    if m:
        try:
            val = int(m.group(1))
            if 1 <= val <= 5:
                levels.append(val)
        except: pass

    # "báo động X" in text
    m2 = re.search(r"báo\s*động\s*(\d|I|II|III)", t)
    if m2:
        val_str = m2.group(1).upper()
        if val_str == "1" or val_str == "I": levels.append(1)
        elif val_str == "2" or val_str == "II": levels.append(2)
        elif val_str == "3" or val_str == "III": levels.append(3)

    if levels:
        return max(levels)

    # 2. Detailed Inference using Regulations (Decision 18/2021/QD-TTg)
    # Context-based pattern matching (per User Request to add filtering for specific articles)
    # Explicitly check for patterns like "Bão cấp 12 tại Biển Đông" -> Risk 3
    from . import risk_lookup
    storm_risk = risk_lookup.check_storm_risk(text + " " + title)
    if storm_risk > 0:
        return storm_risk

    # 3. Explicit Keyword Mapping (Fallback)
    # from . import risk_mapping
    # prov = extract_province(text)
    # metrics = extract_disaster_metrics(text)
    # reg_risk = risk_mapping.calculate_risk_from_metrics(prov, disaster_type, metrics)
    # if reg_risk > 0: return reg_risk

    # 3. Heuristic Fallbacks (explicit keywords only)
    # User Request: If not strictly following regulation (missing data), default to Level 1.

    # === STORM / TROPICAL DEPRESSION (Bão / ATNĐ) ===
    if disaster_type == "storm":
        # Check for Super Storm explicitly (Always High Risk)
        if "siêu bão" in t: return 5
        
        # ATNĐ / Tropical Depression -> Risk 3 (Article 42.1.a)
        # Even if no wind level is parsed, "áp thấp nhiệt đới" itself implies Risk 3.
        if "áp thấp nhiệt đới" in t or "atnđ" in t:
            return 3

        # Helper to extract max level mentioned
        lv_matches = re.findall(r"cấp\s*(\d{1,2})", t)
        parsed_lvs = [int(v) for v in lv_matches if v.isdigit()]
        max_lv = max(parsed_lvs) if parsed_lvs else 0
        
        # High Intensity Keywords that clearly map to high risk even without location
        if max_lv >= 16: return 5
        if max_lv >= 12: return 4
        # Level 8-11 -> Usually Risk 3, but User requested Default 1 if not strictly proven by Regulation (Region Map)
        # We rely on risk_mapping for the strict Region+Wind rules.
        # If we are here, we missed the strict check.
        # User Update: Default to 0 (No Display) if not strict.
        return 0

    # Mưa lớn / Lũ lụt: cấp 1-4
    if disaster_type == "flood_landslide":
        # Check Flood specific high-risk (Article 45) - Historic levels
        flood_risk = risk_lookup.check_flood_risk(text + " " + title)
        if flood_risk > 0: return flood_risk
        
        # Check Flash Flood / Landslide specific risk (Article 46)
        ff_risk = risk_lookup.check_flash_flood_risk(text + " " + title)
        if ff_risk > 0: return ff_risk

        # Check explicit Article 44 rules (Rain/Duration/Terrain)
        rain_risk = risk_lookup.check_rain_risk(text + " " + title)
        if rain_risk > 0: return rain_risk
        
        if "lũ quét" in t: return 0 # Flash flood is dangerous but start 1 if no location context matched
        # "Báo động 3" is a strict technical term in Flood regulation implying High Risk.
        if "báo động 3" in t or "báo động iii" in t: return 3
        if "lịch sử" in t or "kỷ lục" in t: return 4
        return 0

    # Nắng nóng / Hạn hán: cấp 1
    if disaster_type == "heat_drought":
        heat_risk = risk_lookup.check_heat_risk(text + " " + title)
        if heat_risk > 0: return heat_risk

        # Check Drought specific risk (Article 48)
        drought_risk = risk_lookup.check_drought_risk(text + " " + title)
        if drought_risk > 0: return drought_risk
        
        # Check Saline Intrusion risk (Article 49)
        saline_risk = risk_lookup.check_saline_risk(text + " " + title)
        if saline_risk > 0: return saline_risk

        if "đặc biệt gay gắt" in t: return 1 # Could be 2/3 but default 1 if region missing
        return 0

    # Lốc, sét, mưa đá/khác: cấp 1-2 (Article 52) / Rét hại (Article 53)
    if disaster_type == "extreme_other":
        ext_risk = risk_lookup.check_extreme_other_risk(text + " " + title)
        if ext_risk > 0: return ext_risk
        
        cold_risk = risk_lookup.check_cold_risk(text + " " + title)
        if cold_risk > 0: return cold_risk
        return 0

    # Gió mạnh trên biển / Sương mù (Article 50, 51)
    if disaster_type == "wind_fog":
        w_risk = risk_lookup.check_strong_wind_risk(text + " " + title)
        if w_risk > 0: return w_risk
        f_risk = risk_lookup.check_fog_risk(text + " " + title)
        if f_risk > 0: return f_risk
        return 0
    
    # Nước dâng
    if disaster_type == "storm_surge":
        surge_risk = risk_lookup.check_surge_risk(text + " " + title)
        if surge_risk > 0: return surge_risk
        return 0
        
    # Động đất / Sóng thần (Articles 55, 56)
    if disaster_type == "quake_tsunami":
        # Tsunami check
        tsu_risk = risk_lookup.check_tsunami_risk(text + " " + title)
        if tsu_risk > 0: return tsu_risk

        # Earthquake check
        quake_risk = risk_lookup.check_quake_risk(text + " " + title)
        if quake_risk > 0: return quake_risk

        if "sóng thần" in t: return 5
        return 0

    # Cháy rừng (Article 54)
    if disaster_type == "wildfire":
        fire_risk = risk_lookup.check_wildfire_risk(text + " " + title)
        if fire_risk > 0: return fire_risk
        
        if "cấp 5" in t or "cực kỳ nguy hiểm" in t: return 5
        if "cấp 4" in t or "nguy hiểm" in t: return 4
        return 1

    return 1 # Default lowest risk
