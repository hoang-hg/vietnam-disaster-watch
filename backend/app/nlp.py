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
  r"cháy\s*(?:nhà|nhà\s*dân|chung\s*cư|căn\s*hộ|biệt\s*thự)",
  r"cháy\s*(?:kho|kho\s*hàng|nhà\s*kho|xưởng|nhà\s*xưởng)",
  r"cháy\s*(?:xe|ô\s*tô|xe\s*máy|xe\s*tải|container)",
  r"cháy\s*(?:quán|cửa\s*hàng|siêu\s*thị|chợ|trung\s*tâm\s*thương\s*mại)",
  r"cháy\s*(?:nổ|điện|chập\s*điện|ga|gas|bếp\s*gas)",
  r"hỏa\s*hoạn\s*(?:tại|ở)\s*(?:khu|kho|nhà|xưởng)",
  
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
  r"(?:V-League|Ngoại\s*hạng\s*Anh|World\s*Cup|SEA\s*Games)"
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
    Negative patterns act as hard veto UNLESS risk_lookup.assess() confirms real hazard.
    """
    # 1. Stage A: Candidate Detection (Broad)
    sig = compute_disaster_signals(text)
    
    # Must have at least some signal (hazard pattern or metrics)
    if sig["hazard_score"] == 0 and not sig["metrics"]:
        return False

    # 2. Stage B: Confirmation Layer (Strict) via risk_lookup
    # Check if we can strictly assess a risk level (Evidence-first)
    risk = risk_lookup.assess(text, prefer_declared=True)
    
    # If risk_lookup confirms a real hazard (level > 0), accept it
    # This OVERRIDES negative patterns (exception to hard veto)
    if risk["overall_level"] > 0:
        return True
    
    # 3. Hard Veto: Negative patterns
    # If risk_lookup says NO hazard (level = 0) AND we hit negative pattern -> REJECT
    # This prevents metaphorical/non-disaster content from passing
    if sig["negative_hit"]:
        return False
        
    # If risk is 0 and no negative hit, still reject (not confident enough)
    # logic: "Nếu risk_lookup ra 0 ... không nên đưa vào đã xác nhận"
    return False

def diagnose(text: str) -> dict:
    sig = compute_disaster_signals(text)
    reason = f"Score {sig['score']:.1f} < 3.0"
    if sig["negative_hit"]: reason = "Negative keyword match"
    elif sig.get("rule_matches"): reason = f"Matched rules: {sig['rule_matches']}" # Actually valid?
    elif sig["hazard_score"] < 1: reason = "No disaster keywords"
    elif sig["context_score"] < 1: reason = "No context keywords"
    
    return {"score": sig["score"], "signals": sig, "reason": reason}

def title_contains_disaster_keyword(title: str) -> bool:
    t = (title or "").lower()
    for kw in SOURCE_DISASTER_KEYWORDS:
        if kw.lower() in t: return True
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

def classify_disaster(text: str) -> str:
    """Classify the text into a single disaster type string."""
    sig = compute_disaster_signals(text)
    matches = sig.get("rule_matches", [])
    if matches:
        return matches[0]
    return "other"
