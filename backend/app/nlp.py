import re
import unicodedata
from typing import List
from datetime import datetime
from dateutil import parser as dtparser
from .sources import DISASTER_KEYWORDS as SOURCE_DISASTER_KEYWORDS
from . import risk_lookup

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

# Pre-compute compiled regexes for Provinces and Regions
PROVINCE_REGEXES = []

def _compile_prov_regex(names):
    # Helper to build regex with word boundaries and flexible whitespace
    parts = []
    for n in names:
        # Escape characters, then replace escaped space with \s+
        esc = re.escape(n).replace(r"\ ", r"\s+")
        parts.append(esc)
    pattern = "|".join(parts)
    return re.compile(rf"(?<!\w)({pattern})(?!\w)", re.IGNORECASE)

for name, variants in PROVINCE_MAPPING.items():
    PROVINCE_REGEXES.append({
        "name": name,
        "type": "province",
        "re_acc": _compile_prov_regex(variants),
        "re_no": _compile_prov_regex([risk_lookup.strip_accents(v) for v in variants])
    })

for reg in PROVINCE_REGIONS:
    PROVINCE_REGEXES.append({
        "name": reg,
        "type": "region",
        "re_acc": _compile_prov_regex([reg]),
        "re_no": _compile_prov_regex([risk_lookup.strip_accents(reg)])
    })
# DISASTER RULES & PATTERNS
# -----------------------------------------------------------------------------

DISASTER_RULES = [
  # 1) Bão & áp thấp nhiệt đới
  ("storm", [
    r"(?<!\w)bão(?!\w)", r"bão\s*số\s*\d+",
    r"siêu\s*bão", r"hoàn\s*lưu\s*bão", r"tâm\s*bão",
    r"đổ\s*bộ", r"đi\s*vào\s*biển\s*đông", r"tiến\s*vào\s*biển\s*đông",
    r"suy\s*yếu", r"mạnh\s*lên", r"tăng\s*cấp",
    r"áp\s*thấp\s*nhiệt\s*đới", r"(?<!\w)ATNĐ(?!\w)", r"vùng\s*áp\s*thấp",
    r"xoáy\s*thuận\s*nhiệt\s*đới", r"nhiễu\s*động\s*nhiệt\s*đới",
    r"gió\s*mạnh\s*cấp\s*\d+", r"gió\s*giật\s*cấp\s*\d+",
    r"cấp\s*độ\s*rủi\s*ro\s*thiên\s*tai", r"biển\s*động",
    r"áp\s*suất\s*trung\s*tâm", r"vùng\s*gió\s*mạnh", r"gió\s*giật",
  ]),

  # 2) Lũ, Ngập lụt, Sạt lở, Sụt lún (Grouped as flood_landslide)
  ("flood_landslide", [
    # Mưa lớn (driver)
    r"mưa\s*lớn", r"mưa\s*to", r"mưa\s*rất\s*to", r"mưa\s*cực\s*lớn",
    r"mưa\s*đặc\s*biệt\s*lớn", r"mưa\s*diện\s*rộng", r"mưa\s*kéo\s*dài",
    r"mưa\s*kỷ\s*lục", r"mưa\s*cực\s*đoan", r"mưa\s*như\s*trút",
    # Lũ / Ngập
    r"(?<!\w)lũ(?!\w)(?!\s*lượt)", r"(?<!\w)lụt(?!\w)", r"lũ\s*lụt", r"lũ\s*lớn", r"lũ\s*lịch\s*sử", r"lũ\s*dâng",
    r"(?<!\w)ngập(?!\w)(?!\s*đầu\s*tư)(?!\s*tràn)(?!\s*trong)", r"ngập\s*lụt", r"ngập\s*úng", r"ngập\s*sâu",
    r"ngập\s*cục\s*bộ", r"nước\s*lên\s*nhanh", r"mực\s*nước\s*dâng", r"đỉnh\s*lũ",
    r"báo\s*động\s*(?:1|2|3|I|II|III)", r"vượt\s*báo\s*động",
    r"vỡ\s*đê", r"vỡ\s*kè", r"tràn\s*đê", r"tràn\s*bờ", r"vỡ\s*đập", r"sự\s*cố\s*đập", r"xả\s*lũ",
    # Lũ quét / Lũ ống
    r"lũ\s*quét", r"lũ\s*ống", r"nước\s*lũ\s*cuốn\s*trôi",
    # Sạt lở / Sụt lún
    r"sạt\s*lở", r"sạt\s*lở\s*đất", r"lở\s*đất", r"trượt\s*đất", r"trượt\s*lở",
    r"sạt\s*taluy", r"taluy", r"sạt\s*lở\s*bờ\s*sông", r"sạt\s*lở\s*bờ\s*biển",
    r"sụt\s*lún", r"hố\s*tử\s*thần", r"hố\s*sụt", r"nứt\s*đất", r"sụp\s*đường", r"sụp\s*lún"
  ]),

  # 3) Nắng nóng, Hạn hán, Xâm nhập mặn
  ("heat_drought", [
    # Nắng nóng
    r"nắng\s*nóng", r"nắng\s*nóng\s*gay\s*gắt", r"nắng\s*nóng\s*đặc\s*biệt",
    r"nhiệt\s*độ\s*kỷ\s*lục", r"oi\s*bức", r"nhiệt\s*độ\s*cao",
    # Hạn hán
    r"hạn\s*hán", r"khô\s*hạn", r"thiếu\s*nước", r"cạn\s*kiệt",
    r"khát\s*nước", r"nứt\s*nẻ", r"đất\s*khô\s*nứt", "cạn\s*hồ",
    # Mặn
    r"xâm\s*nhập\s*mặn", r"nhiễm\s*mặn", r"độ\s*mặn", r"mặn\s*xâm\s*nhập",
    r"hạn\s*mặn", r"(?<!\w)ppt(?!\w)", r"(?<!\w)g/l(?!\w)"
  ]),

  # 4) Gió mạnh, Sương mù (trên biển và đất liền)
  ("wind_fog", [
    # Gió
    r"gió\s*mạnh", r"gió\s*giật", r"gió\s*mùa", r"gió\s*cấp",
    r"biển\s*động", r"sóng\s*lớn", r"sóng\s*cao", r"cấm\s*biển",
    # Sương mù
    r"sương\s*mù", r"sương\s*mù\s*dày\s*đặc", r"mù\s*dày\s*đặc",
    r"tầm\s*nhìn\s*hạn\s*chế", r"giảm\s*tầm\s*nhìn"
  ]),

  # 5) Nước dâng, Triều cường
  ("storm_surge", [
    r"triều\s*cường", r"nước\s*dâng", r"nước\s*dâng\s*do\s*bão", r"nước\s*biển\s*dâng",
    r"đỉnh\s*triều", r"ngập\s*do\s*triều", r"sóng\s*lớn\s*đánh\s*tràn"
  ]),

  # 6) Thời tiết cực đoan khác (Lốc, Sét, Mưa đá, Rét)
  ("extreme_other", [
    # Dông lốc
    r"dông", r"dông\s*lốc", r"lốc", r"lốc\s*xoáy", r"vòi\s*rồng", r"tố\s*lốc",
    # Mưa đá, Sét
    r"mưa\s*đá", r"sét", r"giông\s*sét", r"sét\s*đánh",
    # Rét, Băng giá
    r"rét\s*đậm", r"rét\s*hại", r"không\s*khí\s*lạnh", r"sương\s*muối", r"băng\s*giá"
  ]),

  # 7) Cháy rừng
  ("wildfire", [
    r"cháy\s*rừng", r"nguy\s*cơ\s*cháy\s*rừng", r"cấp\s*dự\s*báo\s*cháy\s*rừng",
    r"PCCCR", r"cháy\s*thực\s*bì", r"bùng\s*phát\s*cháy"
  ]),

  # 8) Động đất, Sóng thần
  ("quake_tsunami", [
    r"động\s*đất", r"rung\s*chấn", r"dư\s*chấn",
    r"nứt\s*đất", r"đứt\s*gãy", r"nứt\s*nhà",
    r"sóng\s*thần", r"cảnh\s*báo\s*sóng\s*thần", r"tsunami",
    r"richter", r"chấn\s*tiêu", r"tâm\s*chấn"
  ])
]

DISASTER_CONTEXT = [
  r"cảnh\s*báo", r"khuyến\s*cáo", r"cảnh\s*báo\s*sớm",
  r"cấp\s*độ\s*rủi\s*ro", r"rủi\s*ro\s*thiên\s*tai",
  r"sơ\s*tán", r"di\s*dời", r"cứu\s*hộ", r"cứu\s*nạn",
  r"thiệt\s*hại", r"thương\s*vong", r"mất\s*tích", r"bị\s*thương",
  r"chia\s*cắt", r"cô\s*lập", r"mất\s*điện", r"mất\s*liên\s*lạc"
]

DISASTER_NEGATIVE = [
  # Bão (Metaphorical usage)
  r"bão\s*giá", r"cơn\s*bão\s*(?:dư\s*luận|truyền\s*thông|tin\s*giả|mạng)(?!\w)",
  r"bão\s*sale", r"bão\s*like", r"bão\s*scandal", r"cơn\s*bão\s*tài\s*chính",
  r"bão\s*sao\s*kê", r"bão\s*(?:chấn\s*thương|bệnh\s*tật|sa\s*thải)(?!\w)",
  r"(?<!thiên\s)bão\s*lòng", r"dông\s*bão\s*(?:cuộc\s*đời|tình\s*cảm|nội\s*tâm)",
  
  # Động đất / Lũ (Metaphorical)
  r"rung\s*chấn\s*(?:dư\s*luận|thị\s*trường|sân\s*cỏ)(?!\w)",
  r"chấn\s*động\s*(?:dư\s*luận|showbiz|làng\s*giải\s*trí|mạng)(?!\w)",
  r"(?<!\w)động\s*đất\s*(?:thị\s*trường|giá|chứng\s*khoán|bất\s*động\s*sản)(?!\w)",
  r"địa\s*chấn\s*(?:showbiz|làng\s*giải\s*trí|V-pop|V-League)",
  r"lũ\s*(?:lượt|fan|like|view|đơn\s*hàng|người\s*về)(?!\w)",
  r"cơn\s*lốc\s*(?:đường\s*biên|màu\s*cam|sân\s*cỏ|chuyển\s*nhượng)",
  
  # Sóng/Nước (Metaphorical)
  r"sóng\s*gió\s*(?:cuộc\s*đời|hôn\s*nhân|tình\s*cảm)",
  r"làn\s*sóng\s*(?:covid|dịch\s*bệnh|đầu\s*tư|nhập\s*cư|tẩy\s*chay|sa\s*thải)(?!\w)",
  r"ngập\s*(?:tràn|trong)\s*(?:hạnh\s*phúc|tiếng\s*cười|quà|bình\s*luận|sắc\s*màu|niềm\s*vui)(?!\w)",
  
  # Nhiệt/Lạnh (Metaphorical)  
  r"cơn\s*sốt\s*(?:đất|giá|vé|mua\s*sắm)(?!\w)",
  r"đóng\s*băng\s*(?:thị\s*trường|tài\s*khoản|quan\s*hệ|hợp\s*đồng)(?!\w)",
  r"nóng\s*(?:bỏng\s*)?(?:showbiz|sân\s*cỏ|thị\s*trường|tranh\s*cãi)",
  
  # Fire - Non-disaster contexts (Phân biệt cháy rừng vs cháy thường)
  # Cháy nhà/kho/xưởng/xe (không phải thiên tai tự nhiên)
  r"cháy\s*(?:nhà|nhà\s*dân|chung\s*cư|căn\s*hộ|biệt\s*thự|khu\s*công\s*nghiệp|công\s*ty|doanh\s*nghiệp)",
  r"cháy\s*(?:kho|kho\s*hàng|nhà\s*kho|xưởng|nhà\s*xưởng|văn\s*phòng)",
  r"cháy\s*(?:xe|ô\s*tô|xe\s*máy|xe\s*tải|container)",
  r"cháy\s*(?:quán|cửa\s*hàng|siêu\s*thị|chợ|trung\s*tâm\s*thương\s*mại)",
  r"cháy\s*(?:nổ|điện|chập\s*điện|ga|gas|bếp\s*gas)",
  r"hỏa\s*hoạn\s*(?:tại|ở)\s*(?:khu|kho|nhà|xưởng|công\s*ty)",
  
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
  r"khắc\s*phục\s*hậu\s*quả", r"thăm\s*hỏi", r"chia\s*sẻ\s*khó\s*khăn",
  
  # Entertainment/Sports specific
  r"scandal", r"drama", r"tin\s*đồn", r"ồn\s*ào",
  r"(?:V-League|Ngoại\s*hạng\s*Anh|World\s*Cup|SEA\s*Games)",
  
  # Crime / Economy / Policy (Veto for disaster watch)
  r"bắt\s*(?:giữ|tạm\s*giữ|ngay|đối\s*tượng|ghe|thuyền|xe|đất)",
  r"tăng\s*(?:lương|giá|trưởng)", r"đề\s*xuất\s*(?:tăng|giảm|xây|dùng)",
  r"hợp\s*nhất", r"bổ\s*nhiệm", r"phó\s*chủ\s*tịch", r"bộ\s*nội\s*vụ",
  r"lừa\s*đảo", r"sập\s*bẫy", r"chiếm\s*đoạt", r"hóa\s*đơn", r"chứng\s*từ",
  r"vượt\s*biển(?!\s*động)", r"xuất\s*nhập\s*cảnh", r"người\s*trung\s*quốc",
  r"quả\s*bom", r"vật\s*nổ", r"thuốc\s*nổ",
  r"nhân\s*lực", r"công\s*bố\s*khu\s*đất", r"đối\s*ứng", r"metro",
  r"bệnh\s*viện", r"cứu\s*thương(?!\s*do\s*thiên\s*tai)", r"tông\s*xe", r"va\s*chạm",
  r"giáng\s*sinh", r"noel", r"từ\s*thiện", r"ủng\s*hộ", r"trao\s*tặng"
]

# Removed old compiled patterns
POLLUTION_TERMS = [r"ô\s*nhiễm", r"AQI", r"PM2\.5", r"bụi\s*mịn"]

# Pre-compute unaccented patterns for matching against t0 (canonical text)
DISASTER_RULES_NO_ACCENT = []
for label, pats in DISASTER_RULES:
    nops = [risk_lookup.strip_accents(p) for p in pats]
    DISASTER_RULES_NO_ACCENT.append((label, nops))

DISASTER_CONTEXT_NO_ACCENT = [risk_lookup.strip_accents(p) for p in DISASTER_CONTEXT]
DISASTER_NEGATIVE_NO_ACCENT = [risk_lookup.strip_accents(p) for p in DISASTER_NEGATIVE]

# Build impact extraction patterns with named groups and qualifier support
def _build_impact_patterns():
    """
    Build regex patterns for extracting impact metrics with:
    - Named groups for clarity
    - Qualifier support (ít nhất, khoảng, hơn, etc.)
    """
    patterns = {}
    
    # Build number pattern (digits or text numbers)
    numword_patterns = [re.escape(k) for k in NUMBER_WORDS.keys()]
    numword_patterns.sort(key=lambda s: -len(s))
    numword_pattern = "|".join(numword_patterns)
    
    # Qualifiers that modify the count - using unnamed group to avoid collision
    qualifier_pattern = r"(ít\s*nhất|tối\s*thiểu|ít|hơn|trên|khoảng|gần|tối\s*đa|dưới|không\s*dưới|không\s*quá)?"
    
    for impact_type, keywords in IMPACT_KEYWORDS.items():
        keyword_patterns = [re.escape(kw) for kw in keywords]
        keyword_pattern = "|".join(keyword_patterns)
        
        if impact_type in ("deaths", "missing", "injured"):
            # Two separate patterns to avoid named group collision
            # Pattern 1: [qualifier] NUMBER người KEYWORD
            pattern1 = rf"{qualifier_pattern}\s*(?P<num>(?:\d+|{numword_pattern}))\s*(?:người\s*)?(?:{keyword_pattern})"
            # Pattern 2: KEYWORD [qualifier] NUMBER người
            pattern2 = rf"(?:{keyword_pattern})\s*{qualifier_pattern}\s*(?P<num>(?:\d+|{numword_pattern}))\s*(?:người)?"
            
            patterns[impact_type] = [
                re.compile(pattern1, re.IGNORECASE),
                re.compile(pattern2, re.IGNORECASE)
            ]
            
        elif impact_type == "damage":
            # Pattern for financial damage
            # Pattern 1: KEYWORD [qualifier] NUMBER tỉ/triệu đồng
            pattern1 = rf"(?:{keyword_pattern})\s*{qualifier_pattern}\s*(?:ước\s*tính\s*)?(?P<num>(?:\d+|{numword_pattern}))\s*(?P<unit>tỉ|tỷ|triệu)\s*(?:đồng)?"
            # Pattern 2: [qualifier] NUMBER tỉ/triệu đồng
            pattern2 = rf"{qualifier_pattern}\s*(?P<num>(?:\d+|{numword_pattern}))\s*(?P<unit>tỉ|tỷ|triệu)\s*đồng"
            
            patterns["damage"] = [
                re.compile(pattern1, re.IGNORECASE),
                re.compile(pattern2, re.IGNORECASE)
            ]
            
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

# Helper functions removed (using risk_lookup)

# -----------------------------------------------------------------------------
# CORE LOGIC
# -----------------------------------------------------------------------------

def extract_provinces(text: str) -> List[dict]:
    """
    Extract multiple provinces/regions with location info.
    Returns list of dicts: {name, type, span, match}
    Matches against both t (accented) and t0 (unaccented).
    """
    matches = []
    t, t0 = risk_lookup.canon(text or "")
    
    for item in PROVINCE_REGEXES:
        found = None
        # Try Accented
        m = item["re_acc"].search(t)
        if m:
            found = m
        else:
            # Try Unaccented
            m = item["re_no"].search(t0)
            if m:
                found = m
        
        if found:
            matches.append({
                "name": item["name"],  # The normalized name
                "type": item["type"],
                "span": found.span(),
                "match": found.group(0)
            })
            
    # Sort by position
    matches.sort(key=lambda x: x["span"][0])
    return matches

def extract_province(text: str) -> str:
    """Legacy wrapper: returns the Single Best province found.
    Prioritizes specific Province over Region.
    """
    all_hits = extract_provinces(text)
    
    # 1. Return first specific province
    for h in all_hits:
        if h["type"] == "province":
            return h["name"]
            
    # 2. Return first region
    for h in all_hits:
        if h["type"] == "region":
            return h["name"]
            
    return "unknown"

def extract_disaster_metrics(text: str) -> dict:
    metrics = {}
    
    # 1. Rainfall (mm)
    val = risk_lookup.extract_max_mm(text)
    if val: metrics["rainfall_mm"] = val
    
    # 2. Temperature (C)
    val = risk_lookup.extract_max_temp(text)
    if val: metrics["temperature_c"] = val
    
    # 3. Salinity (per mille)
    val = risk_lookup.extract_max_salinity(text)
    if val: metrics["salinity_per_mille"] = val
    
    # 4. Wind (Beaufort) - includes conversion from km/h, m/s
    val = risk_lookup.extract_beaufort_max(text)
    if val: metrics["wind_level"] = val
    
    # 5. Water Level (m)
    val = risk_lookup.extract_water_level(text)
    if val: metrics["water_level_m"] = val
    
    # 6. Duration (days)
    val = risk_lookup.extract_duration_days_count(text)
    if val > 0: metrics["duration_days"] = float(val)
    
    # 7. Earthquake (Magnitude)
    val = risk_lookup.extract_quake_mag(text)
    if val: metrics["earthquake_magnitude"] = val

    return metrics

def compute_disaster_signals(text: str) -> dict:
    # 1. Standardize Normalization using risk_lookup.canon
    # t: normalized, lowercase, accents preserved
    # t0: normalized, lowercase, accents stripped, punctuation removed
    t, t0 = risk_lookup.canon(text or "")

    rule_matches = []
    # Check Rules (Iterate both accented and unaccented)
    for i, (label, patterns) in enumerate(DISASTER_RULES):
        matched = False
        # Match Accented on t
        for p in patterns:
            if re.search(p, t, re.IGNORECASE):
                matched = True
                break
        # Match Unaccented on t0 (if not already matched)
        if not matched:
            _, patterns_no = DISASTER_RULES_NO_ACCENT[i]
            for p in patterns_no:
                if re.search(p, t0, re.IGNORECASE):
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

    # Province Extraction (Enhanced)
    prov_hits = extract_provinces(text)
    specific_prov_found = any(h["type"] == "province" for h in prov_hits)
    
    # Determine best display name
    best_prov = "unknown"
    # 1. First specific
    for h in prov_hits:
        if h["type"] == "province":
            best_prov = h["name"]; break
    # 2. If no specific, use region
    if best_prov == "unknown":
        for h in prov_hits:
            if h["type"] == "region":
                best_prov = h["name"]; break
    
    # Only score if specific province found (reduce false positives from general regional news)
    province_score = WEIGHT_PROVINCE if specific_prov_found else 0.0

    # Source keywords match
    ambiguous = {"cảnh báo", "dự báo", "bản tin", "khuyến cáo"}
    non_ambiguous_hits = []
    for kw in SOURCE_DISASTER_KEYWORDS:
        kl = kw.lower()
        if kl in t:
            if kl not in ambiguous:
                non_ambiguous_hits.append(kl)
    source_score = float(len(non_ambiguous_hits)) * WEIGHT_SOURCE

    score = rule_score + impact_score + agency_score + source_score + province_score

    # Context Matches
    context_hits = []
    # Check each context pattern (Match either accented or unaccented)
    for i, p_str in enumerate(DISASTER_CONTEXT):
        matched = False
        if re.search(p_str, t, re.IGNORECASE): matched = True
        else:
            p_no = DISASTER_CONTEXT_NO_ACCENT[i]
            if re.search(p_no, t0, re.IGNORECASE): matched = True
        
        if matched: context_hits.append(p_str)
        
    for pt in POLLUTION_TERMS:
        if re.search(pt, t, re.IGNORECASE): context_hits.append(pt)
    context_score = len(context_hits)

    # Negative Matches
    negative_hit = False
    for i, p_str in enumerate(DISASTER_NEGATIVE):
        if re.search(p_str, t, re.IGNORECASE): 
            negative_hit = True
            break
        p_no = DISASTER_NEGATIVE_NO_ACCENT[i]
        if re.search(p_no, t0, re.IGNORECASE):
            negative_hit = True
            break
    
    # Extra check: if heavily sports related
    SPORTS_TERMS = ["bóng đá", "v-league", "ngoại hạng anh", "cầu thủ", "ghi bàn"]
    if not negative_hit:
        sc = sum(1 for w in SPORTS_TERMS if w in t)
        if sc >= 2 and hazard_score < 2:
            if "địa chấn" in t or "cơn lốc" in t: negative_hit = True
            # Check unaccented too
            if "dia chan" in t0 or "con loc" in t0: negative_hit = True

    metrics = extract_disaster_metrics(t)

    return {
        "rule_matches": rule_matches,
        "impact_hits": impact_hits,
        "agency": agency_match,
        "province": best_prov if best_prov != "unknown" else None,
        "score": score,
        "hazard_score": hazard_score,
        "context_score": context_score,
        "negative_hit": negative_hit,
        "metrics": metrics
    }

def contains_disaster_keywords(text: str) -> bool:
    """
    Two-stage verification with hard veto on negative patterns.
    """
    # 1. Stage A: Candidate Detection (Broad)
    sig = compute_disaster_signals(text)
    
    # Must have at least some signal (hazard pattern or metrics)
    if sig["hazard_score"] == 0 and not sig["metrics"]:
        return False

    # 2. Hard Veto: Negative patterns
    # This prevents metaphorical/non-disaster content from passing
    if sig["negative_hit"]:
        return False
        
    # Accept if it passes the score threshold (Stage A)
    # logic: if it has hazards or metrics and no negative hits, it's likely valid.
    return sig["hazard_score"] > 0 or len(sig["metrics"]) > 0

def diagnose(text: str) -> dict:
    sig = compute_disaster_signals(text)
    reason = f"Score {sig['score']:.1f} < 3.0"
    if sig["negative_hit"]: reason = "Negative keyword match"
    elif sig.get("rule_matches"): reason = f"Matched rules: {sig['rule_matches']}" # Actually valid?
    elif sig["hazard_score"] < 1: reason = "No disaster keywords"
    elif sig["context_score"] < 1: reason = "No context keywords"
    
    return {"score": sig["score"], "signals": sig, "reason": reason}

def title_contains_disaster_keyword(title: str) -> bool:
    """
    Stricter title check using regex word boundaries and negative veto.
    """
    if not title: return False
    t = title.lower()
    
    # Negative veto first
    for p in DISASTER_NEGATIVE:
        if re.search(p, t, re.IGNORECASE):
            return False
            
    # Positive check
    for kw in SOURCE_DISASTER_KEYWORDS:
        # Use regex to ensure word boundary for short keywords
        kl = kw.lower()
        if len(kl) <= 4:
            pattern = rf"(?<!\w){re.escape(kl)}(?!\w)"
            if re.search(pattern, t, re.IGNORECASE):
                return True
        else:
            if kl in t:
                return True
    return False

def extract_impacts(text: str) -> dict:
    """
    Extract impact metrics from text with qualifier support.
    Returns structured data: {"deaths": {"value": 12, "qualifier": "ít nhất"}, ...}
    """
    def _extract_with_qualifier(pattern_list, text, converter_fn):
        """Helper to extract number and qualifier from named groups, trying multiple patterns"""
        for pattern in pattern_list:
            m = pattern.search(text)
            if not m:
                continue
                
            # Get the matched number (now always 'num')
            num_str = m.group('num')
            if not num_str:
                continue
                
            value = converter_fn(num_str)
            if value == 0:
                continue
                
            # Get qualifier (group 1 is the unnamed qualifier group)
            qual = m.group(1) if m.lastindex and m.lastindex >= 1 and m.group(1) else None
            if qual:
                qual = qual.strip().lower()
                
            return {"value": value, "qualifier": qual}
        
        return None
    
    def _extract_damage(pattern_list, text):
        """Special handler for damage extraction with unit"""
        for pattern in pattern_list:
            m = pattern.search(text)
            if not m:
                continue
                
            # Get number and unit (now consistently named)
            num_str = m.group('num')
            unit = m.group('unit')
            
            if not num_str or not unit:
                continue
                
            value = _to_float(num_str)
            if value == 0:
                continue
                
            # Convert to billion VND
            unit = unit.lower()
            if 'triệu' in unit or 'trieu' in unit:
                value = value / 1000  # Convert million to billion
                
            # Get qualifier (group 1 is the unnamed qualifier group)
            qual = m.group(1) if m.lastindex and m.lastindex >= 1 and m.group(1) else None
            if qual:
                qual = qual.strip().lower()
                
            return {"value": value, "qualifier": qual}
        
        return None
    
    # Extract each impact type
    deaths = _extract_with_qualifier(IMPACT_PATTERNS["deaths"], text, _to_int)
    missing = _extract_with_qualifier(IMPACT_PATTERNS["missing"], text, _to_int)
    injured = _extract_with_qualifier(IMPACT_PATTERNS["injured"], text, _to_int)
    damage = _extract_damage(IMPACT_PATTERNS["damage"], text)
    
    # Extract agency
    agency = None
    m = RE_AGENCY.search(text)
    if m: 
        agency = m.group(1)
    
    # Extract metrics (using risk_lookup)
    metrics = extract_disaster_metrics(text)
    
    return {
        "deaths": deaths,
        "missing": missing,
        "injured": injured,
        "damage_billion_vnd": damage,
        "agency": agency,
        **metrics
    }

def extract_event_time(published_at: datetime, text: str) -> datetime | None:
    """
    Extract event time from text.
    Supports:
    - Absolute dates: dd/mm/yyyy, dd-mm-yyyy
    - Vietnamese date format: ngày dd tháng mm
    - Relative time: hôm nay, đêm qua, rạng sáng, etc.
    """
    from datetime import timedelta
    
    t = text.lower()
    
    # 1. Try relative time expressions first (most common in Vietnamese news)
    
    # "hôm nay" / "chiều nay" / "sáng nay" / "trưa nay" / "tối nay"
    if re.search(r"\b(hôm\s*nay|chiều\s*nay|sáng\s*nay|trưa\s*nay|tối\s*nay)\b", t):
        return published_at.replace(hour=12, minute=0, second=0, microsecond=0)
    
    # "đêm qua" / "tối qua"
    if re.search(r"\b(đêm\s*qua|tối\s*qua)\b", t):
        yesterday = published_at - timedelta(days=1)
        return yesterday.replace(hour=22, minute=0, second=0, microsecond=0)
    
    # "rạng sáng" / "sáng sớm" (early morning of current day)
    if re.search(r"\b(rạng\s*sáng|sáng\s*sớm)\b", t):
        # Check if context suggests yesterday or today
        if re.search(r"(đêm\s*qua|hôm\s*qua).*?(rạng\s*sáng|sáng\s*sớm)", t):
            # "đêm qua rạng sáng" → yesterday night to today early morning
            today = published_at.replace(hour=5, minute=0, second=0, microsecond=0)
            return today
        else:
            # Just "rạng sáng" → current day early morning
            return published_at.replace(hour=5, minute=0, second=0, microsecond=0)
    
    # "hôm qua" / "ngày hôm qua"
    if re.search(r"\b(hôm\s*qua|ngày\s*hôm\s*qua)\b", t):
        yesterday = published_at - timedelta(days=1)
        return yesterday.replace(hour=12, minute=0, second=0, microsecond=0)
    
    # "2 ngày trước" / "3 ngày trước"
    m = re.search(r"(\d+)\s*ngày\s*(?:trước|qua)", t)
    if m:
        days_ago = int(m.group(1))
        past_date = published_at - timedelta(days=days_ago)
        return past_date.replace(hour=12, minute=0, second=0, microsecond=0)
    
    # "tuần trước" / "tuần qua"
    if re.search(r"\b(tuần\s*(?:trước|qua))\b", t):
        last_week = published_at - timedelta(days=7)
        return last_week.replace(hour=12, minute=0, second=0, microsecond=0)
    
    # 2. Try Vietnamese date format: "ngày 15 tháng 12" or "15 tháng 12"
    m = re.search(r"(?:ngày\s*)?(\d{1,2})\s*tháng\s*(\d{1,2})(?:\s*năm\s*(\d{4}))?", t)
    if m:
        day = int(m.group(1))
        month = int(m.group(2))
        year = int(m.group(3)) if m.group(3) else published_at.year
        
        try:
            return datetime(year, month, day, 12, 0, 0)
        except ValueError:
            pass  # Invalid date, continue to next method
    
    # 3. Try absolute date formats: dd/mm/yyyy, dd-mm-yyyy
    candidates = []
    for m in re.finditer(r"(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})", text):
        candidates.append(m.group(1))
    
    for c in candidates[:3]:
        try:
            dt = dtparser.parse(c, dayfirst=True)
            if dt.year == 1900: 
                dt = dt.replace(year=published_at.year)
            return dt
        except: 
            continue
    
    return None

def classify_disaster(text: str, title: str = "") -> dict:
    """
    Classify disaster type by selecting hazard with highest risk level.
    Returns:
    {
        "primary_type": str,      # Hazard type with max risk
        "primary_level": int,     # Risk level of primary hazard
        "all_hazards": [          # Full list of detected hazards
            {"type": str, "level": int},
            ...
        ]
    }
    """
    # Get signals first
    sig = compute_disaster_signals(text)
    
    # If no hazard detected, return unknown
    if not sig["rule_matches"]:
        return {
            "primary_type": "unknown",
            "primary_level": 0,
            "all_hazards": []
        }
    
    # Use risk_lookup.assess() to get detailed hazard levels
    combined_text = f"{title}\n{text}" if title else text
    assessment = risk_lookup.assess(combined_text, prefer_declared=True)
    
    # Build hazard list with levels
    hazard_levels = []
    
    if assessment["hazards"]:
        # Group hazards by disaster type mapping
        # risk_lookup returns granular hazards (e.g., "storm", "rain", "flood")
        # We need to map them to our 8 groups
        
        HAZARD_TYPE_MAPPING = {
            # risk_lookup key -> nlp.py disaster group
            "storm": "storm",
            "surge": "storm_surge",
            "rain": "flood_landslide",
            "flood": "flood_landslide",
            "flash_flood": "flood_landslide",
            "heat": "heat_drought",
            "drought": "heat_drought",
            "saline": "heat_drought",
            "strong_wind_sea": "wind_fog",
            "fog": "wind_fog",
            "extreme_other": "extreme_other",
            "cold": "extreme_other",
            "wildfire": "wildfire",
            "earthquake": "quake_tsunami",
            "quake": "quake_tsunami",
            "tsunami": "quake_tsunami"
        }
        
        # Aggregate by disaster group
        group_levels = {}
        for h in assessment["hazards"]:
            hazard_key = h["hazard"]
            level = h["level"]
            
            # Map to disaster group
            group = HAZARD_TYPE_MAPPING.get(hazard_key, hazard_key)
            
            # Take max level for each group
            if group not in group_levels or level > group_levels[group]:
                group_levels[group] = level
        
        # Convert to list
        for group, level in group_levels.items():
            hazard_levels.append({"type": group, "level": level})
    
    # If risk_lookup didn't find levels, use rule_matches with default level
    if not hazard_levels:
        for hazard_type in sig["rule_matches"]:
            hazard_levels.append({"type": hazard_type, "level": 1})
    
    # Sort by level (descending), then by type name for stability
    hazard_levels.sort(key=lambda x: (-x["level"], x["type"]))
    
    # Select primary (highest level)
    primary = hazard_levels[0] if hazard_levels else {"type": "unknown", "level": 0}
    
    return {
        "primary_type": primary["type"],
        "primary_level": primary["level"],
        "all_hazards": hazard_levels
    }

def detect_flood_station(text: str) -> dict:
    """
    Detect flood monitoring station mentions in text using flood_zones.json.
    Returns:
    {
        "has_station": bool,           # Whether any station was detected
        "stations": [                   # List of detected stations
            {
                "name": str,            # Station name
                "river": str,           # River name
                "province": str,        # Province
                "region": int,          # Flood region (1-4) per Decision 18
                "confidence": float     # Match confidence (0-1)
            }
        ],
        "primary_region": int | None   # Most confident region (for risk calc)
    }
    """
    from . import risk_lookup
    
    # Get FLOOD_ZONES_DATA from risk_lookup
    # It's already loaded there
    if not hasattr(risk_lookup, 'FLOOD_ZONES_DATA') or not risk_lookup.FLOOD_ZONES_DATA:
        return {"has_station": False, "stations": [], "primary_region": None}
    
    t, t0 = risk_lookup.canon(text)
    stations_found = []
    
    # Search through all regions
    for region_key, stations_list in risk_lookup.FLOOD_ZONES_DATA.items():
        # Extract region number (khu_vuc_1 -> 1)
        region_num = int(region_key.replace("khu_vuc_", ""))
        
        for station_info in stations_list:
            station_name = station_info.get("ten_tram")
            river_name = station_info.get("ten_song")
            province = station_info.get("tinh")
            
            confidence = 0.0
            match_reasons = []
            
            # Match station name (highest confidence)
            if station_name:
                station_t0 = risk_lookup.strip_accents(station_name).lower()
                if station_t0 in t0:
                    confidence = 0.9
                    match_reasons.append("station_name")
            
            # Match river + province (medium confidence)
            if river_name and province and confidence < 0.9:
                river_t0 = risk_lookup.strip_accents(river_name).lower()
                prov_t0 = risk_lookup.strip_accents(province).lower()
                
                if river_t0 in t0 and prov_t0 in t0:
                    confidence = 0.7
                    match_reasons.append("river_province")
            
            # Add to results if confident enough
            if confidence >= 0.7:
                stations_found.append({
                    "name": station_name or f"Trạm {river_name}",
                    "river": river_name,
                    "province": province,
                    "region": region_num,
                    "confidence": confidence,
                    "match_reasons": match_reasons
                })
    
    # Sort by confidence
    stations_found.sort(key=lambda x: -x["confidence"])
    
    # Determine primary region (highest confidence)
    primary_region = stations_found[0]["region"] if stations_found else None
    
    return {
        "has_station": len(stations_found) > 0,
        "stations": stations_found,
        "primary_region": primary_region
    }


def summarize(text: str, max_len: int = 220) -> str:
    cleaned = re.sub(r"<[^>]+>", "", text)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if len(cleaned) <= max_len: return cleaned
    return cleaned[:max_len].rsplit(" ", 1)[0] + "…"

def classify_disaster(text: str) -> str:
    """Classify the text into a single disaster type string.
    Prioritizes more specific detections.
    """
    sig = compute_disaster_signals(text)
    matches = sig.get("rule_matches", [])
    if not matches:
        return "other"
    
    # Prioritize certain categories if multiple match
    prio = ["quake_tsunami", "flood_landslide", "storm", "wildfire", "heat_drought", "wind_fog", "extreme_other", "storm_surge"]
    for p in prio:
        if p in matches:
            return p
            
    return matches[0]
