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
        "tốc mái", "ngập nhà", "cuốn trôi", "sạt lở đường", "đứt đường", "nứt mặt đường",
        "chia cắt", "cô lập", "sập cầu", "mất điện", "mất nước", "mất sóng"
    ],
    "disruption": [
        "sơ tán", "di dời", "tạm sơ tán", "phong tỏa", "cấm đường", 
        "cấm lưu thông", "đóng cửa trường", "cho học sinh nghỉ",
        "ngừng cấp điện", "cắt điện", "mất điện diện rộng", "tê liệt giao thông",
        "cấm biển", "dừng hoạt động", "tàu thuyền không ra khơi"
    ],
    "agriculture": [
        "hoa màu", "lúa", "ruộng", "diện tích lúa", "ha lúa", "mất trắng",
        "gia súc", "gia cầm", "trâu bò", "lợn gà", "vật nuôi",
        "ao nuôi", "tôm cá", "thủy sản", "lồng bè", "lồng nuôi"
    ],
    "marine": [
        "chìm tàu", "đắm tàu", "lật tàu", "trôi dạt", "mất tín hiệu", 
        "gặp nạn trên biển", "tàu cá", "ngư dân"
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
    # Miền Bắc
    "Hà Nội": ["Hà Nội", "HN", "Ha Noi"],
    "Hà Giang": ["Hà Giang"],
    "Cao Bằng": ["Cao Bằng"],
    "Bắc Kạn": ["Bắc Kạn"],
    "Tuyên Quang": ["Tuyên Quang"],
    "Lào Cai": ["Lào Cai"],
    "Điện Biên": ["Điện Biên"],
    "Lai Châu": ["Lai Châu"],
    "Sơn La": ["Sơn La"],
    "Yên Bái": ["Yên Bái"],
    "Hòa Bình": ["Hòa Bình"],
    "Thái Nguyên": ["Thái Nguyên"],
    "Lạng Sơn": ["Lạng Sơn"],
    "Quảng Ninh": ["Quảng Ninh"],
    "Bắc Giang": ["Bắc Giang"],
    "Phú Thọ": ["Phú Thọ"],
    "Vĩnh Phúc": ["Vĩnh Phúc"],
    "Bắc Ninh": ["Bắc Ninh"],
    "Hải Dương": ["Hải Dương"],
    "Hải Phòng": ["Hải Phòng"],
    "Hưng Yên": ["Hưng Yên"],
    "Thái Bình": ["Thái Bình"],
    "Hà Nam": ["Hà Nam"],
    "Nam Định": ["Nam Định"],
    "Ninh Bình": ["Ninh Bình"],
    # Miền Trung
    "Thanh Hóa": ["Thanh Hóa"],
    "Nghệ An": ["Nghệ An"],
    "Hà Tĩnh": ["Hà Tĩnh"],
    "Quảng Bình": ["Quảng Bình"],
    "Quảng Trị": ["Quảng Trị"],
    "Thừa Thiên Huế": ["Thừa Thiên Huế", "Huế", "TT-Huế", "T.T.Huế"],
    "Đà Nẵng": ["Đà Nẵng"],
    "Quảng Nam": ["Quảng Nam"],
    "Quảng Ngãi": ["Quảng Ngãi"],
    "Bình Định": ["Bình Định"],
    "Phú Yên": ["Phú Yên"],
    "Khánh Hòa": ["Khánh Hòa"],
    "Ninh Thuận": ["Ninh Thuận"],
    "Bình Thuận": ["Bình Thuận"],
    # Tây Nguyên
    "Kon Tum": ["Kon Tum"],
    "Gia Lai": ["Gia Lai"],
    "Đắk Lắk": ["Đắk Lắk", "Dak Lak"],
    "Đắk Nông": ["Đắk Nông", "Dak Nong"],
    "Lâm Đồng": ["Lâm Đồng"],
    # Miền Nam
    "TP Hồ Chí Minh": ["Hồ Chí Minh", "TP.HCM", "TPHCM", "Sài Gòn"],
    "Bình Phước": ["Bình Phước"],
    "Tây Ninh": ["Tây Ninh"],
    "Bình Dương": ["Bình Dương"],
    "Đồng Nai": ["Đồng Nai"],
    "Bà Rịa - Vũng Tàu": ["Bà Rịa", "Vũng Tàu", "BR-VT", "BRVT"],
    "Long An": ["Long An"],
    "Tiền Giang": ["Tiền Giang"],
    "Bến Tre": ["Bến Tre"],
    "Trà Vinh": ["Trà Vinh"],
    "Vĩnh Long": ["Vĩnh Long"],
    "Đồng Tháp": ["Đồng Tháp"],
    "An Giang": ["An Giang"],
    "Kiên Giang": ["Kiên Giang"],
    "Cần Thơ": ["Cần Thơ"],
    "Hậu Giang": ["Hậu Giang"],
    "Sóc Trăng": ["Sóc Trăng"],
    "Bạc Liêu": ["Bạc Liêu"],
    "Cà Mau": ["Cà Mau"],
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
    # Bão (loại trừ: đi bão, bão giá, bão mạng, bão lòng, cơn bão số... khi nói về giá cả)
    r"(?<!\w)(?<!đi\s)(?<!dự\s)bão(?!\sgiá)(?!\smạng)(?!\slòng)(?!\stài\s)(?!\stín\s)(?!\w)",
    r"bão\s*số\s*\d+",
    r"siêu\s*bão", r"hoàn\s*lưu\s*bão", r"tâm\s*bão",
    r"đổ\s*bộ", r"đi\s*vào\s*biển\s*đông", r"tiến\s*vào\s*biển\s*đông",
    # Áp thấp (loại trừ: huyết áp thấp, cao áp thấp)
    r"(?<!huyết\s)áp\s*thấp\s*nhiệt\s*đới",
    r"(?<!huyết\s)(?<!cao\s)áp\s*thấp(?!\w)",
    r"(?<!\w)ATNĐ(?!\w)", r"vùng\s*áp\s*thấp",
    r"xoáy\s*thuận\s*nhiệt\s*đới", r"nhiễu\s*động\s*nhiệt\s*đới",
    r"gió\s*mạnh\s*cấp\s*\d+", r"gió\s*giật\s*cấp\s*\d+",
    r"cấp\s*độ\s*rủi\s*ro\s*thiên\s*tai",
  ]),

  # 2) Lũ, Ngập lụt, Sạt lở, Sụt lún (Grouped as flood_landslide)
  ("flood_landslide", [
    # Mưa lớn (driver)
    r"mưa\s*lớn", r"mưa\s*to", r"mưa\s*rất\s*to", r"mưa\s*cực\s*lớn",
    r"mưa\s*đặc\s*biệt\s*lớn", r"mưa\s*diện\s*rộng", r"mưa\s*kéo\s*dài",
    r"mưa\s*kỷ\s*lục", r"mưa\s*cực\s*đoan", r"mưa\s*như\s*trút",
    # Lũ / Ngập (Strict boundaries)
    r"(?<!\w)lũ(?!\w)(?!\s*lượt)(?!\s*khách)",
    r"(?<!\w)lụt(?!\w)", r"lũ\s*lụt", r"lũ\s*lớn", r"lũ\s*lịch\s*sử", r"lũ\s*dâng",
    r"(?<!\w)ngập(?!\w)(?!\s*đầu\s*tư)(?!\s*tràn)(?!\s*trong)(?!\s*ngụa)(?!\s*mặn)",
    r"ngập\s*lụt", r"ngập\s*úng", r"ngập\s*sâu",
    r"ngập\s*cục\s*bộ", r"nước\s*lên\s*nhanh", r"mực\s*nước\s*dâng", r"đỉnh\s*lũ",
    r"báo\s*động\s*(?:1|2|3|I|II|III)", r"vượt\s*báo\s*động",
    r"vỡ\s*đê", r"vỡ\s*kè", r"tràn\s*đê", r"tràn\s*bờ", r"vỡ\s*đập", r"sự\s*cố\s*đập", r"xả\s*lũ",
    # Lũ quét / Lũ ống
    r"lũ\s*quét", r"lũ\s*ống", r"nước\s*lũ\s*cuốn\s*trôi",
    # Sạt lở / Sụt lún (Loại trừ: đất đai, bất động sản, vận chuyển đất)
    r"(?<!\w)sạt(?!\w)", r"sạt\s*lở(?!\s*giá)", r"sạt\s*lở\s*đất", r"lở\s*đất", r"trượt\s*đất", r"trượt\s*lở",
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
    r"khát\s*nước", r"nứt\s*nẻ", r"đất\s*khô\s*nứt", r"cạn\s*hồ",
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
    r"(?<!\w)dông(?!\w)", r"dông\s*lốc", r"(?<!\w)lốc(?!\w)", r"lốc\s*xoáy", r"vòi\s*rồng", r"tố\s*lốc",
    # Mưa đá, Sét
    r"mưa\s*đá", r"(?<!\w)sét(?!\w)", r"giông\s*sét", r"sét\s*đánh",
    # Rét, Băng giá
    r"rét\s*đậm", r"rét\s*hại", r"không\s*khí\s*lạnh", r"sương\s*muối", r"băng\s*giá"
  ]),

  # 7) Cháy rừng
  # 7) Cháy rừng
  # 7) Cháy rừng
  ("wildfire", [
    # Explicitly wildfire only
    r"cháy\s*rừng", r"nguy\s*cơ\s*cháy\s*rừng", r"cấp\s*dự\s*báo\s*cháy\s*rừng",
    r"PCCCR", r"cháy\s*thực\s*bì", r"rừng\s*phòng\s*hộ", r"rừng\s*sản\s*xuất", 
    r"đám\s*cháy\s*rừng", r"lửa\s*rừng"
  ]),

  # 8) Động đất, Sóng thần
  ("quake_tsunami", [
    r"động\s*đất", r"rung\s*chấn", r"dư\s*chấn",
    r"nứt\s*đất", r"đứt\s*gãy", r"nứt\s*nhà",
    r"sóng\s*thần", r"cảnh\s*báo\s*sóng\s*thần", r"tsunami",
    r"richter", r"chấn\s*tiêu", r"tâm\s*chấn",
    r"độ\s*lớn", r"magnitude", r"Mw", r"ML"
  ])
]

DISASTER_CONTEXT = [
  r"cảnh\s*báo", r"khuyến\s*cáo", r"cảnh\s*báo\s*sớm",
  r"cấp\s*độ\s*rủi\s*ro", r"rủi\s*ro\s*thiên\s*tai",
  r"sơ\s*tán", r"di\s*dời", r"cứu\s*hộ", r"cứu\s*nạn",
  r"thiệt\s*hại", r"thương\s*vong", r"mất\s*tích", r"bị\s*thương",
  r"chia\s*cắt", r"cô\s*lập", r"mất\s*điện", r"mất\s*liên\s*lạc",
  # Official Sources
  r"trung\s*tâm\s*dự\s*báo", r"đài\s*khí\s*tượng", r"thủy\s*văn",
  r"ban\s*chỉ\s*huy", r"ban\s*chỉ\s*đạo", r"phòng\s*chống\s*thiên\s*tai", 
  r"sở\s*nn&ptnt", r"bộ\s*nông\s*nghiệp", r"ubnd",
  r"tin\s*bão", r"tin\s*áp\s*thấp", r"công\s*điện", r"khẩn\s*cấp",
  # Recovery / Relief (Moved from Negatives to Positive Context)
  r"khắc\s*phục", r"hỗ\s*trợ", r"cứu\s*trợ", r"ủng\s*hộ",
  r"thăm\s*hỏi", r"chia\s*sẻ", r"quyên\s*góp", r"tiếp\s*nhận",
  r"sửa\s*chữa", r"khôi\s*phục", r"tái\s*thiết", r"bồi\s*thường",
  r"bảo\s*hiểm", r"trợ\s*cấp", r"phân\s*bổ", r"nguồn\s*vốn",
  r"bệnh\s*viện", r"điều\s*trị", r"bác\s*sĩ", r"cấp\s*cứu"
]

# RECOVERY Keywords for Event Stage Classification
RECOVERY_KEYWORDS = [
    r"khắc\s*phục", r"hỗ\s*trợ", r"cứu\s*trợ", r"ủng\s*hộ",
    r"thăm\s*hỏi", r"chia\s*sẻ", r"quyên\s*góp", r"tiếp\s*nhận",
    r"sửa\s*chữa", r"khôi\s*phục", r"tái\s*thiết", r"bồi\s*thường",
    r"bảo\s*hiểm", r"trợ\s*cấp", r"phân\s*bổ", r"nguồn\s*vốn" 
]

# 1. HARD NEGATIVE: Absolute Veto (Metaphors, Sports, Showbiz, Accidents)
HARD_NEGATIVE = [
  # Bão (Metaphorical)
  r"bão\s*giá", r"cơn\s*bão\s*(?:dư\s*luận|truyền\s*thông|tin\s*giả|mạng)(?!\w)",
  r"bão\s*sale", r"bão\s*like", r"bão\s*scandal", r"cơn\s*bão\s*tài\s*chính",
  r"bão\s*sao\s*kê", r"bão\s*(?:chấn\s*thương|sa\s*thải)(?!\w)",
  r"(?<!thiên\s)bão\s*lòng", r"dông\s*bão\s*(?:cuộc\s*đời|tình\s*cảm|nội\s*tâm)",
  r"siêu\s*bão\s*(?:giảm\s*giá|khuyến\s*mãi|hàng\s*hiệu)", 
  
  # Động đất / Lũ / Sóng (Metaphorical)
  r"rung\s*chấn\s*(?:dư\s*luận|thị\s*trường|sân\s*cỏ)",
  r"chấn\s*động\s*(?:dư\s*luận|showbiz|làng\s*giải\s*trí)",
  r"địa\s*chấn\s*(?:showbiz|làng\s*giải\s*trí|V-pop|V-League)",
  
  # === ADDED NOISE FILTERS ===
  # Economy / Real Estate
  r"bất\s*động\s*sản", r"cơn\s*sốt\s*đất", r"sốt\s*đất", r"đất\s*nền", r"chung\s*cư",
  r"dự\s*án\s*nhà\s*ở", r"shophouse", r"biệt\s*thự", r"đấu\s*giá\s*đất",
  r"lãi\s*suất", r"tín\s*dụng", r"ngân\s*hàng", r"tỉ\s*giá", r"VN-Index", r"chứng\s*khoán", r"cổ\s*phiếu",
  r"giá\s*(?:vàng|heo|cà\s*phê|lúa|xăng|dầu|trái\s*cây)", r"tăng\s*giá", r"giảm\s*giá", r"hạ\s*nhiệt\s*(?:giá|thị\s*trường)",
  r"xuất\s*khẩu", r"nhập\s*khẩu", r"GDP", r"tăng\s*trưởng\s*kinh\s*tế",

  # Traffic Accidents (Distinguish from Disaster)
  r"tai\s*nạn\s*giao\s*thông", r"va\s*chạm\s*xe", r"tông\s*xe", r"tông\s*chết",
  r"xe\s*tải", r"xe\s*khách", r"xe\s*đầu\s*kéo", r"xe\s*container", r"xe\s*buýt",
  r"(?<!thiên\s)tai\s*nạn\s*liên\s*hoàn", r"vi\s*phạm\s*nồng\s*độ\s*cồn",

  # Sports
  r"bóng\s*đá", r"cầu\s*thủ", r"đội\s*tuyển", r"World\s*Cup", r"V-League", r"Sea\s*Games",
  r"AFF\s*Cup", r"huấn\s*luyện\s*viên", r"bàn\s*thắng", r"ghi\s*bàn", r"vô\s*địch",
  r"huy\s*chương", r"HCV", r"HCB", r"HCD",

  # Showbiz / Events
  r"showbiz", r"hoa\s*hậu", r"người\s*mẫu", r"ca\s*sĩ", r"diễn\s*viên", r"liveshow",
  r"scandal", r"drama", r"sao\s*Việt", r"khánh\s*thành", r"khai\s*trương", r"kỷ\s*niệm\s*ngày",
  
  r"buôn\s*lậu", r"ma\s*túy", r"đánh\s*bạc", r"cờ\s*bạc", r"lừa\s*đảo", r"khởi\s*tố", r"bắt\s*giữ",
  r"án\s*mạng", r"giết\s*người", r"cướp\s*giật", r"trộm\s*cắp", r"cát\s*tặc", r"khai\s*thác\s*cát",
  r"súng", r"bắn", r"nổ\s*súng", r"hung\s*thủ", r"nghi\s*phạm", r"điều\s*tra\s*vụ",

  # Fire / Explosion (Urban/Industrial - Not Forest)
  r"cháy\s*(?:nhà|xưởng|xe|công\s*ty|chợ|cửa\s*hàng|quán|chung\s*cư|tàu|ca\s*nô|chùa|đền|miếu|nhà\s*thờ)",
  r"lửa\s*ngùn\s*ngụt",  # Urban fire, not wildfire
  r"hỏa\s*hoạn\s*(?!rừng)", r"bà\s*hỏa", r"chập\s*điện", r"nổ\s*bình\s*gas",
  r"bom\s*mìn", r"vật\s*liệu\s*nổ", r"thuốc\s*nổ", r"đạn\s*pháo", r"chiến\s*tranh", r"thời\s*chiến",

  # Pollution / Environment (Not Disaster)
  r"bụi\s*mịn", r"ô\s*nhiễm\s*không\s*khí", r"chất\s*lượng\s*không\s*khí", r"AQI",
  r"quan\s*trắc\s*môi\s*trường", r"rác\s*thải",

  # Construction / Labor Accidents
  r"giàn\s*giáo", r"sập\s*giàn\s*giáo", r"tai\s*nạn\s*lao\s*động", r"an\s*toàn\s*lao\s*động",
  r"công\s*trình\s*xây\s*dựng", r"thicông",

  # Extended Traffic Noise
  r"xe\s*cứu\s*thương", r"biển\s*số\s*xe", r"đấu\s*giá\s*biển\s*số",
  r"đăng\s*kiểm", r"giấy\s*phép", r"phạt\s*nguội",
  
  # Other Misc
  r"tặng\s*quà", r"trao\s*quà", r"từ\s*thiện", r"hiến\s*máu", # Filter out pure charity events if not linked to active disaster keywords strongly

  # Administrative / Legal / Political (Non-disaster)
  r"giấy\s*chứng\s*nhận", r"sổ\s*đỏ", r"quyền\s*sử\s*dụng\s*đất", r"giao\s*đất", r"chuyển\s*nhượng",
  r"công\s*chức", r"viên\s*chức", r"biên\s*chế", r"thẩm\s*quyền", r"hành\s*chính",
  r"quốc\s*phòng\s*toàn\s*dân", r"an\s*ninh\s*quốc\s*phòng", r"quân\s*sự",
  r"vụ\s*án", r"tranh\s*chấp", r"khiếu\s*nại", r"tố\s*cáo", r"điều\s*tra\s*viên", r"bị\s*can",
  
  # Education
  r"đại\s*học", r"cao\s*đẳng", r"tuyển\s*sinh", r"đào\s*tạo", r"giáo\s*dục", r"học\s*bổng",
  r"tốt\s*nghiệp", r"thạc\s*sĩ", r"tiến\s*sĩ",
  
  # Finance / Banking (Specific)
  r"vốn\s*điều\s*lệ", r"tăng\s*vốn", r"cổ\s*đông", r"lợi\s*nhuận", r"doanh\s*thu",
  r"ADB", r"WB", r"IMF", r"ODA", # International banks often in economic news
  
  # Health / Lifestyle
  r"ung\s*thư", r"tế\s*bào", r"tiểu\s*đường", r"huyết\s*áp", r"đột\s*quỵ",
  r"dinh\s*dưỡng", r"thực\s*phẩm", r"món\s*ăn", r"đặc\s*sản", r"giảm\s*cân", r"làm\s*đẹp",
  r"ngăn\s*ngừa\s*bệnh", r"sức\s*khỏe\s*sinh\s*sản",

  # Tech / Internet / Misc
  r"Google", r"Facebook", r"Youtube", r"TikTok", r"Zalo\s*Pay", r"tính\s*năng", r"cập\s*nhật",
  r"tra\s*từ", r"từ\s*điển", r"bài\s*hát", r"ca\s*khúc", r"MV", r"triệu\s*view", r"top\s*trending",
  
  # Metaphors (Reinforced)
  r"bão\s*tố\s*cuộc\s*đời", r"sóng\s*gió\s*cuộc\s*đời", r"bão\s*tố\s*tình\s*yêu",
  r"bão\s*lòng",
  
  # Transport / Aviation / Urban Traffic
  r"sân\s*bay", r"cảng\s*hàng\s*không", r"máy\s*bay", r"Boeing", r"Airbus", r"vé\s*máy\s*bay",
  r"kẹt\s*xe", r"ùn\s*tắc", r"giao\s*thông\s*đô\s*thị",



  r"lũ\s*(?:lượt|fan|like|view|đơn\s*hàng)",
  r"cơn\s*lốc\s*(?:đường\s*biên|màu\s*cam|sân\s*cỏ|chuyển\s*nhượng)",
  r"sóng\s*gió\s*(?:cuộc\s*đời|hôn\s*nhân)",
  r"làn\s*sóng\s*(?:covid|dịch\s*bệnh|đầu\s*tư|tẩy\s*chay|sa\s*thải)",
  r"đóng\s*băng\s*(?:thị\s*trường|tài\s*khoản|quan\s*hệ)",
  r"cơn\s*sốt\s*(?:đất|giá|vé)",
  r"không\s*khí\s*lạnh\s*(?:nhạt|lùng|giá)", 

  # Thể thao
  r"(?:đi|về)\s*bão", r"ăn\s*mừng", r"cổ\s*vũ", r"xuống\s*đường",
  r"bóng\s*đá", r"U\d+", r"đội\s*tuyển", r"SEA\s*Games", r"AFF\s*Cup",
  r"vô\s*địch", r"huy\s*chương", r"bàn\s*thắng", r"ghi\s*bàn", r"HLV", r"sân\s*cỏ",
  r"tỉ\s*số", r"chung\s*kết", r"ngược\s*dòng"
]

# 2. SOFT NEGATIVE: Potential False Positive (Politics, Admin, Economy)
# Can be overridden if HAZARD SCORE is high enough.
SOFT_NEGATIVE = [
  r"đại\s*hội", r"bầu\s*cử", r"ứng\s*cử", r"đại\s*biểu", r"quốc\s*hội",
  r"mặt\s*trận\s*tổ\s*quốc", r"MTTQ", r"ủy\s*ban", r"kiểm\s*tra", r"giám\s*sát",
  r"thăng\s*quân\s*hàm", r"bổ\s*nhiệm", r"kỷ\s*luật", r"nghị\s*quyết",
  r"thủ\s*tướng", r"bộ\s*trưởng", r"lãnh\s*đạo",
  r"khởi\s*công", r"khánh\s*thành", r"nghiệm\s*thu", 
  r"an\s*ninh\s*mạng", r"chuyển\s*đổi\s*số", r"công\s*nghệ", r"startup",
  r"giải\s*thưởng", r"vinh\s*danh",
  # Tai nạn (Soft Negative - pass if caused by storm/flood)
  r"tai\s*nạn\s*giao\s*thông", r"xe\s*tải", r"xe\s*container", r"xe\s*khách",
  # Fire non-wildfire
  r"cháy\s*(?:nhà|xe|kho|xưởng|chung\s*cư|công\s*ty|chợ|siêu\s*thị|tàu\s*cá|quán)",
  r"hỏa\s*hoạn\s*(?:tại|ở)\s*(?:khu|kho|nhà|xưởng)"
]

# Combined Negative List for backward compatibility (used in NO_ACCENT generation)
DISASTER_NEGATIVE = HARD_NEGATIVE + SOFT_NEGATIVE

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
    Extract multiple provinces/regions with location info using finditer.
    Returns list of dicts: {name, type, span, match}
    Matches against both t (accented) and t0 (unaccented).
    """
    matches = []
    t, t0 = risk_lookup.canon(text or "")
    
    for item in PROVINCE_REGEXES:
        # Try Accented first
        found_iter = list(item["re_acc"].finditer(t))
        if not found_iter:
             # Try Unaccented if no accented match found for this regex
             found_iter = list(item["re_no"].finditer(t0))
        
        for m in found_iter:
            matches.append({
                "name": item["name"],  # The normalized name
                "type": item["type"],
                "span": m.span(),
                "match": m.group(0)
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
    t, t0 = risk_lookup.canon(text or "")

    rule_matches = []
    # Check Rules (Iterate both accented and unaccented)
    for i, (label, patterns) in enumerate(DISASTER_RULES):
        matched = False
        # Match Accented on t
        for p in patterns:
            if re.search(p, t, re.IGNORECASE):
                matched = True; break
        # Disable Unaccented Check to prevent False Positives (bao -> bão, lu -> lũ)
        # if not matched:
        #     _, patterns_no = DISASTER_RULES_NO_ACCENT[i]
        #     for p in patterns_no:
        #         if re.search(p, t0, re.IGNORECASE):
        #             matched = True; break
        if matched: rule_matches.append(label)

    hazard_score = len(set(rule_matches))
    rule_score = WEIGHT_RULE if hazard_score else 0.0

    impact_hits = []
    for k, klist in IMPACT_KEYWORDS.items():
        for kw in klist:
            if kw.lower() in t:
                impact_hits.append((k, kw)); break
    impact_score = WEIGHT_IMPACT if impact_hits else 0.0

    agency_match = bool(RE_AGENCY.search(t))
    agency_score = WEIGHT_AGENCY if agency_match else 0.0

    # Province Extraction (Enhanced)
    prov_hits = extract_provinces(text)
    specific_prov_found = any(h["type"] == "province" for h in prov_hits)
    
    best_prov = "unknown"
    for h in prov_hits:
        if h["type"] == "province": best_prov = h["name"]; break
    if best_prov == "unknown":
        for h in prov_hits:
            if h["type"] == "region": best_prov = h["name"]; break
    
    province_score = WEIGHT_PROVINCE if specific_prov_found else 0.0

    # Source keywords match
    ambiguous = {"cảnh báo", "dự báo", "bản tin", "khuyến cáo"}
    non_ambiguous_hits = []
    for kw in SOURCE_DISASTER_KEYWORDS:
        kl = kw.lower()
        if kl in t and kl not in ambiguous:
            non_ambiguous_hits.append(kl)
    source_score = float(len(non_ambiguous_hits)) * WEIGHT_SOURCE

    score = rule_score + impact_score + agency_score + source_score + province_score

    # Context Matches
    context_hits = []
    for i, p_str in enumerate(DISASTER_CONTEXT):
        matched = False
        if re.search(p_str, t, re.IGNORECASE): matched = True
        # Disable Unaccented Check for Context
        # else:
        #     p_no = DISASTER_CONTEXT_NO_ACCENT[i]
        #     if re.search(p_no, t0, re.IGNORECASE): matched = True
        if matched: context_hits.append(p_str)
        
    for pt in POLLUTION_TERMS:
        if re.search(pt, t, re.IGNORECASE): context_hits.append(pt)
    context_score = len(context_hits)

    # NEGATIVE CHECKS (Split)
    hard_negative = False
    for p in HARD_NEGATIVE:
        if re.search(p, t, re.IGNORECASE): 
            hard_negative = True; break
            
    soft_negative = False
    if not hard_negative:
        for p in SOFT_NEGATIVE:
            if re.search(p, t, re.IGNORECASE):
                soft_negative = True; break

    metrics = extract_disaster_metrics(t)

    return {
        "rule_matches": rule_matches,
        "impact_hits": impact_hits,
        "agency": agency_match,
        "province": best_prov if best_prov != "unknown" else None,
        "score": score,
        "hazard_score": hazard_score,
        "context_score": context_score,
        "hard_negative": hard_negative,
        "soft_negative": soft_negative,
        "metrics": metrics
    }

def determine_event_stage(text: str) -> str:
    """Classify event stage: WARNING, IMPACT, or RECOVERY"""
    t_lower = text.lower()
    
    # 1. Recovery
    for kw in RECOVERY_KEYWORDS:
        if re.search(kw, t_lower): return "RECOVERY"
        
    # 2. Warning / Forecast
    warning_sig = [
        r"dự\s*báo", r"cảnh\s*báo", r"tin\s*bão", r"áp\s*thấp", 
        r"công\s*điện", r"khẩn\s*cấp", r"nguy\s*cơ", r"chủ\s*động"
    ]
    for kw in warning_sig:
        if re.search(kw, t_lower): return "WARNING"
        
    # 3. Default to IMPACT (Actual event happening)
    return "IMPACT"


def contains_disaster_keywords(text: str, trusted_source: bool = False) -> bool:
    """
    Advanced Logic v2:
    - Hard Veto: Metaphors/Sports -> Immediate FAIL.
    - Soft Veto: Politics/Accidents -> Fail unless Hazard Score >= 1 AND Score >= 3.0.
    - Trusted: Pass if Hazard >= 1 OR Score >= 3.0.
    - Untrusted: 
        - Hazard == 0 -> Fail (unless metrics+context strong? No, kept strict).
        - Hazard >= 1 -> Needs Score >= 3.0 OR (Impact/Metric/Context/Province).
    """
    sig = compute_disaster_signals(text)
    
    # 1. Absolute Veto
    if sig["hard_negative"]:
        return False
        
    # 2. Mandatory Hazard Check (Keep strict for now to avoid pure noise)
    if sig["hazard_score"] == 0:
        if not sig["metrics"]: 
            return False
        
    # 3. Decision Logic
    
    if sig["soft_negative"]:
        # Soft Neg present (e.g. "Thủ tướng", "Tai nạn", "Khánh thành")
        # Require stronger signal to override (e.g. "Bão" + "Lũ" -> Hazard=2, or very high context).
        # T030 (Khánh thành dự án ngập) had Hazard=1, Score=4.0. We want to Reject it.
        # So we raise threshold: Need Hazard >= 2 OR Score >= 7.0
        if sig["hazard_score"] < 2 and sig["score"] < 7.0:
            return False
        # Else pass (Override)
        return True
    
    else:
        # No Negative Hit
        # Pass if High Score
        if sig["score"] >= 3.0:
            return True
            
        # Trusted source
        if trusted_source and sig["hazard_score"] > 0:
            return True
        
        # Untrusted + Low Score (< 3.0):
        # Need corroboration
        has_evidence = (
            sig["impact_hits"] or 
            sig["metrics"] or 
            sig["province"] or 
            sig["context_score"] > 0 or
            sig["agency"]
        )
        if sig["hazard_score"] > 0 and has_evidence:
            return True
        elif sig["hazard_score"] >= 2: # Multiple hazard keywords -> likely true
             return True
            
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
    Classify disaster type based on rule matches.
    Simplified version: No complex risk level assessment (User Request).
    """
    # Combine text for better signal detection
    full_text = f"{title}\n{text}" if title else text
    sig = compute_disaster_signals(full_text)
    
    matches = list(set(sig["rule_matches"])) # Deduplicate
    
    if not matches:
        return {
            "primary_type": "unknown",
            "primary_level": 0,
            "all_hazards": []
        }
    
    # Simple Priority for Primary Type
    PRIO = [
        "quake_tsunami", 
        "storm", "storm_surge",
        "flood_landslide", 
        "wildfire", 
        "heat_drought", 
        "wind_fog", 
        "extreme_other"
    ]
    
    # Build list
    all_hazards = [{"type": m, "level": 1} for m in matches] # Default Level 1
    
    # Sort by Priority
    all_hazards.sort(key=lambda h: PRIO.index(h["type"]) if h["type"] in PRIO else 99)
    
    return {
        "primary_type": all_hazards[0]["type"],
        "primary_level": 1,
        "all_hazards": all_hazards
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


